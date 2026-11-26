"""录屏用演示：四壁折弯钣金盒（160x100x2，四边 90 度法兰 + 中心大孔 + 4 个安装孔）。

逐特征提交，每步之间留出停顿，方便录 Creo 画面里的建模过程。
用法：
    .\\.venv\\Scripts\\python.exe tools\\demo_bend_box.py            # 直接跑
    .\\.venv\\Scripts\\python.exe tools\\demo_bend_box.py --fast      # 不暂停
"""

import json
import shutil
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from creo_mechdog import bridge
from creo_mechdog import generic_bridge as general

# Windows 控制台默认 GBK，Ø 等字符会直接抛 UnicodeEncodeError 中断演示。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

FAST = "--fast" in sys.argv
PAUSE = 0.0 if FAST else 1.5
OUT = _ROOT / "build"
T0 = time.time()


def wait(job_id, budget=420):
    path = bridge.job_path(job_id) / "job.json"
    manifest = {}
    for _ in range(budget):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("status") not in ("queued", "running"):
            return manifest
        time.sleep(1)
    return manifest


def revision_of(model_id):
    info = general.inspect_model(model_id, detail="compact")
    return (info.get("data") or {}).get("revision") or info.get("revision")


def step(title, operations, model_id=None, revision=None, model_type="sheetmetal", template=None):
    started = time.time()
    kwargs = {"model_type": model_type}
    if model_id is None:
        kwargs["template_name"] = template or "mmns_part_sheetmetal_abs.prt"
    else:
        kwargs["model_id"] = model_id
        kwargs["expected_revision"] = revision if revision is not None else revision_of(model_id)
    manifest = general.submit(operations=operations, **kwargs)
    done = wait(manifest["job_id"])
    result = done.get("result") or {}
    volume = (result.get("inspection_summary") or {}).get("volume_mm3")
    ok = done.get("status") == "succeeded"
    print(
        f"[{time.time() - T0:5.1f}s] {'OK  ' if ok else 'FAIL'} {title:<22} "
        f"{time.time() - started:4.1f}s  vol={volume if volume is None else round(volume, 2)}"
        + ("" if ok else f"  -> {str(done.get('message'))[:160]}"),
        flush=True,
    )
    if not ok:
        raise SystemExit(f"步骤失败: {title}")
    if PAUSE:
        time.sleep(PAUSE)
    return manifest["model_id"], done.get("revision"), result


def wall_edge(a, b):
    return {
        "op": "sheetmetal_flange",
        "edge": {"kind": "edge_geometry", "endpoints_mm": [a, b], "tolerance_mm": 1e-4},
        "height": 30,
        "angle": 90,
        "radius": 2,
    }


# 1) 基板 160 x 100 x 2
model_id, revision, result = step(
    "base 160x100x2",
    [
        {
            "op": "sheetmetal_planar_wall",
            "label": "base_panel",
            "plane": "XY",
            "length": 160,
            "width": 100,
            "thickness": 2,
        }
    ],
)

# 2) 前后两面墙（长边，互不相邻）
model_id, revision, _ = step(
    "front wall 90",
    [{**wall_edge([0.0, 0.0, 2.0], [160.0, 0.0, 2.0]), "label": "wall_front"}],
    model_id,
    revision,
)
model_id, revision, _ = step(
    "back wall 90",
    [{**wall_edge([160.0, 100.0, 2.0], [0.0, 100.0, 2.0]), "label": "wall_back"}],
    model_id,
    revision,
)

# 3) 左右两面墙（短边，需要斜接才能和已有折弯相邻）
model_id, revision, _ = step(
    "left wall 90 + miter",
    [
        {
            **wall_edge([0.0, 96.0, 2.0], [0.0, 4.0, 2.0]),
            "label": "wall_left",
            "miter_cuts": {"width": 2},
        }
    ],
    model_id,
    revision,
)
model_id, revision, _ = step(
    "right wall 90 + miter",
    [
        {
            **wall_edge([160.0, 4.0, 2.0], [160.0, 96.0, 2.0]),
            "label": "wall_right",
            "miter_cuts": {"width": 2},
        }
    ],
    model_id,
    revision,
)

# 4) 底部中心 Ø40 大孔
model_id, revision, result = step(
    "center hole D40",
    [
        {
            "op": "hole",
            "label": "center_hole",
            "diameter": 40,
            "placement": {"kind": "plane", "axis": "z", "offset": 2},
            "reference1": {"kind": "datum_plane", "axis": "x"},
            "reference2": {"kind": "datum_plane", "axis": "y"},
            "offset1": 80,
            "offset2": 50,
        }
    ],
    model_id,
    revision,
)

# 5) 四个 Ø8 安装孔
mount_holes = []
for name, dx, dy in (("m1", 25, 25), ("m2", 135, 25), ("m3", 135, 75), ("m4", 25, 75)):
    mount_holes.append(
        {
            "op": "hole",
            "label": name,
            "diameter": 8,
            "placement": {"kind": "plane", "axis": "z", "offset": 2},
            "reference1": {"kind": "datum_plane", "axis": "x"},
            "reference2": {"kind": "datum_plane", "axis": "y"},
            "offset1": dx,
            "offset2": dy,
        }
    )
model_id, revision, result = step("4 x D8 holes", mount_holes, model_id, revision)

# 7) 全部展开：固定面取底面（z=0 且跨度最大的平面）
info = general.inspect_model(model_id, detail="full", section="surfaces")
surfaces = (info.get("data") or {}).get("surfaces") or []
base_face = None
for surface in surfaces:
    bbox = surface.get("bbox")
    if not bbox:
        continue
    (x0, y0, z0), (x1, y1, z1) = bbox
    if abs(z0) > 1e-6 or abs(z1) > 1e-6:
        continue
    span = (x1 - x0) * (y1 - y0)
    if base_face is None or span > base_face[0]:
        base_face = (span, surface)
if base_face is None:
    raise SystemExit("找不到作为固定面的底面")
print(f"fixed surface id={base_face[1]['id']} bbox={base_face[1]['bbox']}", flush=True)
model_id, revision, result = step(
    "unbend all",
    [
        {
            "op": "sheetmetal_unbend",
            "label": "unbend_all",
            "fixed_surface": {"kind": "surface", "id": base_face[1]["id"]},
            "references": [],
        }
    ],
    model_id,
    revision,
)

# 6) 结果
info = general.inspect_model(model_id, detail="full")
data = info.get("data") or {}
print("\n=== feature tree ===", flush=True)
for feature in data.get("features") or []:
    if feature.get("type_name") != "datum_plane" or feature.get("name") != "no_name":
        print(
            f"{feature.get('id'):>5}  {feature.get('type_name'):<16} {feature.get('name')}",
            flush=True,
        )
for body in data.get("bodies") or []:
    if body.get("bbox"):
        print("bbox", body["bbox"], flush=True)

manifest = json.loads((_ROOT / "models" / model_id / "model.json").read_text())
print("revision", manifest.get("revision"), flush=True)
print("part_file", manifest.get("part_file"), flush=True)

preview = result.get("preview_file")
if preview and Path(preview).is_file():
    shutil.copyfile(preview, OUT / "demo_bend_box.jpg")
    print("preview", OUT / "demo_bend_box.jpg", flush=True)
print(f"total {time.time() - T0:.1f}s", flush=True)
