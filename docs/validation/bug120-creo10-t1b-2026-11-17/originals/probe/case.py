"""One-shot runner for the temporary T1-B probe.

Writes the case request(s), runs the probe under the project's single Toolkit
channel through probe_driver, and prints a compact summary so each matrix case
costs one command instead of several file writes.

  python probe/case.py --dir work/a2_list --probe '{"stage":"list",...}'
  python probe/case.py --dir work/a2_session --probe '{...}' --host '{...}'

--host writes probe/host/probe_request.json, which the in-session probe reads on
its first command invocation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import probe_driver  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="case directory, absolute or relative to test_runs root")
    parser.add_argument("--probe", required=True, help="probe.json payload")
    parser.add_argument("--host", default=None, help="probe/host/probe_request.json payload")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--full", action="store_true", help="print the whole result instead of a summary")
    args = parser.parse_args()

    case_dir = Path(args.dir)
    if not case_dir.is_absolute():
        case_dir = (HERE.parent / case_dir).resolve()
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "probe.json").write_text(
        json.dumps(json.loads(args.probe), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.host:
        host = json.loads(args.host)
        (HERE / "host" / "probe_request.json").write_text(
            json.dumps(host, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    payload = probe_driver.run(case_dir, timeout=args.timeout)
    result = payload["result"]
    summary = {
        "returncode": payload["returncode"],
        "elapsed_seconds": payload["elapsed_seconds"],
        "stderr": payload["stderr"],
        "success": result.get("success"),
        "failure": result.get("failure"),
        "stage": result.get("stage"),
        "current_model": result.get("current_model"),
        "connect_code": result.get("connect_code"),
    }
    for key in ("resolved_count", "selection_recorded", "features_before_count", "panel",
                "references", "curve_features", "features_created", "save_code", "saved_file",
                "erase_code", "session_probe_identity"):
        if key in result:
            summary[key] = result[key]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.full:
        print("--- full result ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
