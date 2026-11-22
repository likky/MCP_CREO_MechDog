"""Run input validation tests and save a versioned result for release evidence."""

import argparse
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from creo_mechdog.source_provenance import local_provenance, source_file_hashes
from creo_mechdog.unit_report import build_unit_report


def write_report(path: Path, report: dict) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(report, stream, indent=2)
        except BaseException:
            stream.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="New path for this run's release evidence")
    args = parser.parse_args(argv)
    default = ROOT / "build/unit_test_report.json"
    path = args.report.resolve() if args.report else default
    path.parent.mkdir(parents=True, exist_ok=True)
    running = {"status": "running", "success": None, "release_evidence": bool(args.report)}
    if args.report:
        if path == default.resolve():
            parser.error("--report must be separate from build/unit_test_report.json")
        try:
            with path.open("x", encoding="utf-8") as stream:
                json.dump(running, stream)
        except FileExistsError:
            parser.error("--report must name a new file for each run")
    else:
        write_report(path, running)
    source = local_provenance(ROOT)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = build_unit_report(
        result,
        timestamp=time.time(),
        duration_seconds=time.monotonic() - started,
        provenance=source,
    )
    report.update(status="completed", release_evidence=bool(args.report))
    if args.report:
        # Verify the exact files selected before unittest. Re-discovering them
        # would change the scope if Git is unavailable after running the suite.
        before = source["source_sha256"]
        after, errors = source_file_hashes(ROOT, before)
        if source["source_status"] != "complete" or errors or before != after:
            print(
                "Release evidence refused: source files changed or could not be read",
                file=sys.stderr,
            )
            report.update(status="source_changed", success=False)
    write_report(path, report)
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
