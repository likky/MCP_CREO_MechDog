"""Drive a T1-C run and observe the dashboard from outside the Creo process.

Windows are enumerated before and after the run. Note the Boundary Blend
dashboard is embedded in the main window, so the window list cannot prove the
dashboard closed; it only proves no stray top-level dialog was left behind. The
in-session module writes its own end marker, and the caller still checks the
feature set independently.

Run:  python run_drive.py <case-dir> --request req.json --host-dir <dir> \
        [--select-command MechDogT1CSelectB] [--tail quit] [--wait 30]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\my\MCP_CREO_MechDog")
BASE = ROOT / "test_runs" / "2026-11-17_t1c_closure"
PROBE = BASE / "probe" / "t1c_drive.exe"

sys.path.insert(0, str(ROOT))
from bridge import native_environment, toolkit_lock  # noqa: E402

try:
    import win32gui
    import win32process
except Exception:  # pragma: no cover
    win32gui = None


def creo_pid() -> int | None:
    candidates = [
        (BASE / "probe" / "host3", "probe_identity_v2b.json"),
        (BASE / "probe" / "host2", "probe_identity_v2.json"),
        (BASE.parent / "2026-11-17_t1b_id_driven_blend" / "probe" / "host", "probe_identity.json"),
    ]
    for directory, name in candidates:
        path = directory / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not data.get("terminated", False):
            return data.get("process_id")
    return None


def snapshot() -> dict:
    if win32gui is None:
        return {"available": False}
    pid = creo_pid()
    rows = []

    def callback(hwnd, _):
        try:
            _, owner = win32process.GetWindowThreadProcessId(hwnd)
            title = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            visible = bool(win32gui.IsWindowVisible(hwnd))
        except Exception:
            return True
        if visible and (title or cls):
            rows.append({"hwnd": hwnd, "pid": owner, "title": title, "class": cls})
        return True

    win32gui.EnumWindows(callback, None)
    own = [r for r in rows if pid is not None and r["pid"] == pid]
    return {
        "available": True,
        "creo_pid": pid,
        "creo_window_count": len(own),
        "creo_windows": [{"title": r["title"], "class": r["class"]} for r in own],
        "note": "dashboard is embedded in the main window and is not listed here",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--host-dir", type=Path, required=True)
    parser.add_argument("--marker", type=Path, required=True)
    parser.add_argument("--select-command", default="MechDogT1CSelectB")
    parser.add_argument("--tail", default="none", choices=["none", "quit", "quit_yes"])
    parser.add_argument("--wait", type=int, default=45)
    args = parser.parse_args()

    case_dir = args.case_dir.resolve()
    case_dir.mkdir(parents=True, exist_ok=True)
    host_dir = args.host_dir.resolve()
    payload = json.loads(args.request.read_text(encoding="utf-8"))
    (host_dir / "probe_request_v2b.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    before = snapshot()
    (case_dir / "windows_before.json").write_text(
        json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    request = {
        "request_id": payload.get("request_id"),
        "model": payload.get("model"),
        "curves": payload.get("curves"),
        "wait_seconds": args.wait,
        "select_command": args.select_command,
        "tail": args.tail,
        "marker_path": str(args.marker),
        # The in-process post-run scan is unreliable in this environment; the
        # caller takes the feature inventory with t1c_features.exe instead.
        "post_scan": bool(payload.get("post_scan", False)),
    }
    (case_dir / "probe.json").write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    (case_dir / "probe_result.json").unlink(missing_ok=True)

    started = time.time()
    with toolkit_lock(wait_seconds=60, operation=f"t1c_drive:{request['request_id']}"):
        completed = subprocess.run(
            [str(PROBE), str(case_dir)],
            capture_output=True,
            text=True,
            timeout=args.wait + 120,
            cwd=str(case_dir),
            env=native_environment(),
        )
    after = snapshot()
    (case_dir / "windows_after.json").write_text(
        json.dumps(after, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    result_path = case_dir / "probe_result.json"
    out = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
    out["_process"] = {"returncode": completed.returncode, "seconds": round(time.time() - started, 2)}
    out["windows"] = {"before": before, "after": after}
    print(json.dumps(out, ensure_ascii=False, indent=2)[:6000])
    return 0 if out.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
