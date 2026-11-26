"""Cable tray segment demo (fast path: one submission, ~29 s).

Part: 600 x 100 x 50, gauge 1.5, bend radius 1.5
  base -> two 90 deg side walls -> inward top lips
  holes: 7 x D10 vents + 4 x D9 connectors (base), 5 x D8 per wall, 4 x D6 per lip

Usage:
    .\\.venv\\Scripts\\python.exe tools\\demo_cable_tray.py            # 1 plan, ~29 s
    .\\.venv\\Scripts\\python.exe tools\\demo_cable_tray.py --stepwise # 6 plans, ~69 s (slower but shows progress)
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

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

STEPWISE = "--stepwise" in sys.argv
GROUPS_MODE = "--groups" in sys.argv
TWO_MODE = "--two" in sys.argv
EVEN_MODE = "--even" in sys.argv
OUT = _ROOT / "build"
T0 = time.time()

LEN, WID, T, H, LIP = 600.0, 100.0, 1.5, 50.0, 15.0


def wait(job_id, budget=600):
    path = bridge.job_path(job_id) / "job.json"
    manifest = {}
    for _ in range(budget):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("status") not in ("queued", "running"):
            return manifest
        time.sleep(0.5)
    return manifest


def revision_of(model_id):
    info = general.inspect_model(model_id, detail="compact")
    return (info.get("data") or {}).get("revision") or info.get("revision")


def submit(operations, model_id=None, revision=None):
    if model_id is None:
        kwargs = {"model_type": "sheetmetal", "template_name": "mmns_part_sheetmetal_abs.prt"}
    else:
        kwargs = {"model_id": model_id, "expected_revision": revision}
    manifest = general.submit(operations=operations, **kwargs)
    done = wait(manifest["job_id"])
    return manifest.get("model_id"), done


def flange(label, a, b, height):
    return {
        "op": "sheetmetal_flange",
        "label": label,
        "edge": {"kind": "edge_geometry", "endpoints_mm": [a, b], "tolerance_mm": 1e-4},
        "height": height,
        "angle": 90,
        "radius": 1.5,
    }


def cut(label, plane, offset, entities, direction):
    return [
        {
            "op": "sketch",
            "label": label + "_sk",
            "plane": plane,
            "offset": offset,
            "entities": entities,
        },
        {
            "op": "extrude",
            "label": label,
            "sketch": label + "_sk",
            "mode": "cut",
            "depth_type": "through_all",
            "direction": direction,
        },
    ]


vents = [
    {"type": "circle", "name": f"v{i}", "center": [float(x), WID / 2], "radius": 5.0}
    for i, x in enumerate((90, 160, 230, 300, 370, 440, 510))
]
connectors = [
    {"type": "circle", "name": f"c{i}", "center": [cx, cy], "radius": 4.5}
    for i, (cx, cy) in enumerate(
        ((20.0, 25.0), (20.0, 75.0), (LEN - 20.0, 25.0), (LEN - 20.0, 75.0))
    )
]
wall_holes = [
    {"type": "circle", "name": f"w{i}", "center": [float(x), H / 2], "radius": 4.0}
    for i, x in enumerate((100, 200, 300, 400, 500))
]
lip_holes = [
    {"type": "circle", "name": f"l{i}", "center": [float(x), cy], "radius": 3.0}
    for i, (x, cy) in enumerate(
        (
            (100.0, 9.0),
            (230.0, 9.0),
            (370.0, 9.0),
            (500.0, 9.0),
            (100.0, 91.0),
            (230.0, 91.0),
            (370.0, 91.0),
            (500.0, 91.0),
        )
    )
]

plan = [
    {
        "op": "sheetmetal_planar_wall",
        "label": "base_panel",
        "plane": "XY",
        "length": LEN,
        "width": WID,
        "thickness": T,
    },
    flange("wall_a", [0, 0, T], [LEN, 0, T], H),
    flange("wall_b", [LEN, WID, T], [0, WID, T], H),
    flange("lip_a", [LEN, T, H], [0, T, H], LIP),
    flange("lip_b", [0, WID - T, H], [LEN, WID - T, H], LIP),
]
plan += cut("vents", "XY", 0.0, vents, "positive")
plan += cut("conn", "XY", 0.0, connectors, "positive")
plan += cut("wall", "XZ", 0.0, wall_holes, "symmetric")
plan += cut("lip", "XY", H - T, lip_holes, "positive")

# pieces reused by the pacing modes; --even merges the two base-hole cuts so the
# first punch stage finishes sooner.
frame_ops = plan[0:5]
base_merged = cut("base_holes", "XY", 0.0, vents + connectors, "positive")
wall_ops = plan[9:11]
lip_ops = plan[11:13]

# ---------------------------------------------------------------------------
# three speeds: one submission (~31 s) / three groups (~33 s) / per feature (~98 s)
if STEPWISE:
    mode = "step"
elif GROUPS_MODE:
    mode = "groups"
elif TWO_MODE:
    mode = "two"
elif EVEN_MODE:
    mode = "even"
else:
    mode = "one"

GROUPS = {
    "one": [("whole tray", plan)],
    "even": [
        ("1/4 frame: base + walls + lips", frame_ops),
        ("2/4 base holes (11)", base_merged),
        ("3/4 side wall holes (5 per wall)", wall_ops),
        ("4/4 lip holes (4 per lip)", lip_ops),
    ],
    "two": [
        ("frame: base + 2 walls + 2 lips", plan[0:5]),
        ("all holes: base + wall + lip", plan[5:13]),
    ],
    "groups": [
        ("frame: base + walls + lips", plan[0:5]),
        ("base holes: vents + connectors", plan[5:9]),
        ("wall holes + lip holes", plan[9:13]),
    ],
    "step": [
        ("base panel", plan[0:1]),
        ("side wall y=0", plan[1:2]),
        ("side wall y=100", plan[2:3]),
        ("top lip y=0", plan[3:4]),
        ("top lip y=100", plan[4:5]),
        ("vents + connectors", plan[5:9]),
        ("wall holes", plan[9:11]),
        ("lip holes", plan[11:13]),
    ],
}

model_id = None
revision = None
result = {}
for title, operations in GROUPS[mode]:
    started = time.time()
    model_id, done = submit(operations, model_id, revision)
    result = done.get("result") or {}
    ok = done.get("status") == "succeeded"
    revision = done.get("revision")
    volume = (result.get("inspection_summary") or {}).get("volume_mm3")
    print(
        f"[{time.time() - T0:5.1f}s] {'OK  ' if ok else 'FAIL'} {title:<32}"
        f"{time.time() - started:4.1f}s  vol={None if volume is None else round(volume, 2)}"
        + ("" if ok else f"\n     -> {str(done.get('message'))[:300]}"),
        flush=True,
    )
    if not ok:
        raise SystemExit(1)
    if mode == "step":
        time.sleep(0.8)
    elif mode in ("groups", "two", "even"):
        time.sleep(1.2)

if (result.get("preview_file") or "") and Path(result["preview_file"]).is_file():
    shutil.copyfile(result["preview_file"], OUT / "cable_tray.jpg")
    print("preview", OUT / "cable_tray.jpg", flush=True)

info = general.inspect_model(model_id, detail="full")
features = (info.get("data") or {}).get("features") or []
print(f"\n=== {len(features)} features ===", flush=True)
for feature in features:
    if feature.get("name") != "no_name":
        print(
            f"{feature.get('id'):>5} {feature.get('type_name'):<16} {feature.get('name')}",
            flush=True,
        )
print("model_id", model_id, flush=True)
print(f"total {time.time() - T0:.1f}s", flush=True)
