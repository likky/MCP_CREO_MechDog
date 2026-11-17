"""Drive the temporary T1-B probe under the project's single Toolkit channel.

The probe is an asynchronous Toolkit program, so it must take the same
toolkit.lock the MCP server takes. Nothing here bypasses that lock, launches a
second Creo session or retries a refused request.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\my\MCP_CREO_MechDog")
PROBE = ROOT / "test_runs" / "2026-11-17_t1b_id_driven_blend" / "probe" / "t1b_probe.exe"

sys.path.insert(0, str(ROOT))
from bridge import native_environment, toolkit_lock  # noqa: E402


def run(case_dir: Path, timeout: int = 300) -> dict:
    case_dir = case_dir.resolve()
    request_path = case_dir / "probe.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    for stale in ("probe_result.json", "probe_steps.jsonl"):
        (case_dir / stale).unlink(missing_ok=True)
    started = time.time()
    with toolkit_lock(wait_seconds=30, operation=f"t1b_probe:{request.get('request_id', '')}"):
        completed = subprocess.run(
            [str(PROBE), str(case_dir)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(case_dir),
            env=native_environment(),
        )
    elapsed = round(time.time() - started, 3)
    result_path = case_dir / "probe_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    return {
        "returncode": completed.returncode,
        "elapsed_seconds": elapsed,
        "stdout": completed.stdout.strip()[:4000],
        "stderr": completed.stderr.strip()[:4000],
        "result": result,
    }


if __name__ == "__main__":
    payload = run(Path(sys.argv[1]))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
