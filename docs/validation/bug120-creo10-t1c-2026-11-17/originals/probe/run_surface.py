"""Run the T1-C surface probe under the project's single Toolkit channel.

The probe is an asynchronous Toolkit program, so it takes the same toolkit.lock
the MCP server takes. Nothing here bypasses the lock, starts a second session or
retries a refused request.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\my\MCP_CREO_MechDog")
PROBE = ROOT / "test_runs" / "2026-11-17_t1c_closure" / "probe" / "t1c_surface.exe"

sys.path.insert(0, str(ROOT))
from bridge import native_environment, toolkit_lock  # noqa: E402


def run(case_dir: Path, timeout: int = 300) -> dict:
    case_dir = case_dir.resolve()
    request = json.loads((case_dir / "probe.json").read_text(encoding="utf-8"))
    for stale in ("probe_result.json",):
        (case_dir / stale).unlink(missing_ok=True)
    started = time.time()
    with toolkit_lock(wait_seconds=60, operation=f"t1c_surface:{request.get('request_id', '')}"):
        completed = subprocess.run(
            [str(PROBE), str(case_dir)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(case_dir),
            env=native_environment(),
        )
    result_path = case_dir / "probe_result.json"
    payload = {}
    if result_path.is_file():
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    payload["_process"] = {
        "returncode": completed.returncode,
        "seconds": round(time.time() - started, 2),
        "stdout": completed.stdout[-2000:],
        "stderr": completed.stderr[-2000:],
    }
    return payload


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_surface.py <case-dir>")
        return 2
    payload = run(Path(sys.argv[1]))
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:4000])
    return 0 if payload.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
