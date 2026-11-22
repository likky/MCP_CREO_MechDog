"""Run input validation tests and save a versioned result for release evidence."""

import sys
import time
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from creo_mechdog import unit_evidence
from creo_mechdog.source_provenance import local_provenance
from creo_mechdog.unit_report import build_unit_report
from version import VERSION


def main() -> int:
    report = unit_evidence.report_path(ROOT)
    run_id = uuid.uuid4().hex
    try:
        unit_evidence.acquire(report, run_id=run_id)
    except unit_evidence.UnitRunBusy as error:
        print(f"Refusing to start: {error}", file=sys.stderr)
        return 3
    try:
        source = local_provenance(ROOT)
        unit_evidence.start_run(report, run_id=run_id, version=VERSION, provenance=source)
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        started = time.monotonic()
        try:
            result = unittest.TextTestRunner(verbosity=2).run(suite)
        except BaseException as error:
            unit_evidence.interrupt_run(report, run_id=run_id, reason=type(error).__name__)
            raise
        unit_evidence.write_json_atomic(
            report,
            build_unit_report(
                result,
                timestamp=time.time(),
                duration_seconds=time.monotonic() - started,
                provenance=source,
                run_id=run_id,
            ),
        )
        unit_evidence.finish_run(report, run_id=run_id, success=result.wasSuccessful())
        return 0 if result.wasSuccessful() else 1
    finally:
        unit_evidence.release(report, run_id=run_id)


if __name__ == "__main__":
    raise SystemExit(main())
