"""BUG-144: a full-pass claim must belong to the run that just completed."""

import json
import tempfile
import unittest
import uuid
from pathlib import Path

from creo_mechdog import release_integrity, unit_evidence
from creo_mechdog.source_provenance import local_provenance
from creo_mechdog.unit_report import build_unit_report


class UnitRunStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.report = self.temp / "unit_test_report.json"
        self.provenance = {"source_fingerprint": "a" * 64, "source_status": "complete"}

    def test_completed_run_records_identity_and_success(self):
        run_id = uuid.uuid4().hex
        unit_evidence.start_run(
            self.report, run_id=run_id, version="0.35.5", provenance=self.provenance
        )
        self.assertTrue(unit_evidence.finish_run(self.report, run_id=run_id, success=True))
        state = unit_evidence.load_run(self.report)
        self.assertEqual(state["status"], "completed")
        self.assertTrue(state["success"])
        self.assertEqual(state["run_id"], run_id)
        self.assertEqual(state["source"]["source_fingerprint"], "a" * 64)

    def test_interrupted_run_is_terminal_and_unsuccessful(self):
        run_id = uuid.uuid4().hex
        unit_evidence.start_run(
            self.report, run_id=run_id, version="0.35.5", provenance=self.provenance
        )
        self.assertTrue(
            unit_evidence.interrupt_run(self.report, run_id=run_id, reason="KeyboardInterrupt")
        )
        state = unit_evidence.load_run(self.report)
        self.assertEqual(state["status"], "interrupted")
        self.assertFalse(state["success"])
        self.assertEqual(state["failure"], "KeyboardInterrupt")

    def test_a_finished_run_cannot_overwrite_a_newer_run(self):
        unit_evidence.start_run(
            self.report, run_id="first", version="0.35.5", provenance=self.provenance
        )
        unit_evidence.start_run(
            self.report, run_id="second", version="0.35.5", provenance=self.provenance
        )
        self.assertFalse(unit_evidence.finish_run(self.report, run_id="first", success=True))
        self.assertEqual(unit_evidence.load_run(self.report)["run_id"], "second")

    def test_lock_refuses_a_live_owner_and_is_released(self):
        unit_evidence.acquire(self.report, run_id="first")
        with self.assertRaises(unit_evidence.UnitRunBusy):
            unit_evidence.acquire(self.report, run_id="second")
        unit_evidence.release(self.report, run_id="first")
        unit_evidence.acquire(self.report, run_id="second")
        unit_evidence.release(self.report, run_id="second")

    def test_lock_from_a_dead_process_is_replaced(self):
        lock = unit_evidence.lock_path(self.report)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(json.dumps({"pid": 0, "run_id": "old"}), encoding="utf-8")
        unit_evidence.acquire(self.report, run_id="new")
        self.assertEqual(unit_evidence.load_json(lock)["run_id"], "new")
        unit_evidence.release(self.report, run_id="new")

    def test_atomic_write_leaves_no_partial_temporary_file(self):
        unit_evidence.write_json_atomic(self.report, {"ok": True})
        self.assertTrue(self.report.is_file())
        self.assertFalse(self.report.with_name(self.report.name + ".tmp").exists())


class UnitEvidenceGateTests(unittest.TestCase):
    VERSION = "0.35.5"

    def setUp(self):
        self.temp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.base = self.temp / "checkout"
        (self.base / "docs/validation").mkdir(parents=True)
        (self.base / "version.py").write_text('VERSION = "0.35.5"\n', encoding="utf-8")
        (self.base / f"docs/validation/RELEASE-{self.VERSION}.md").write_text(
            "全量 4299 项通过（6 跳过）。\n", encoding="utf-8"
        )
        self.report = self.temp / "evidence" / "unit_test_report.json"
        self.provenance = local_provenance(self.base)

    def write_round(
        self,
        *,
        run_id: str = "round-1",
        state: str = "completed",
        state_success: bool = True,
        report_success: bool = True,
        tests_run: int = 1,
        version: str = VERSION,
        report_fingerprint: str | None = None,
        write_state: bool = True,
    ) -> str:
        unit_evidence.start_run(
            self.report, run_id=run_id, version=version, provenance=self.provenance
        )
        if state == "completed":
            unit_evidence.finish_run(self.report, run_id=run_id, success=state_success)
        result = unittest.TestResult()
        result.testsRun = tests_run
        if not report_success:
            result.failures.append((unittest.FunctionTestCase(lambda: None), "evidence"))
        document = build_unit_report(
            result,
            timestamp=1.0,
            duration_seconds=0.1,
            provenance=self.provenance,
            run_id=run_id,
        )
        document["version"] = version
        if report_fingerprint is not None:
            document["source"]["source_fingerprint"] = report_fingerprint
        unit_evidence.write_json_atomic(self.report, document)
        if not write_state:
            unit_evidence.run_state_path(self.report).unlink()
        return run_id

    def problems(self, version: str | None = None) -> list[str]:
        return release_integrity._unit_test_claim_problems(
            version or self.VERSION, self.base, self.report
        )

    def test_completed_run_for_the_tested_source_is_accepted(self):
        self.write_round()
        self.assertEqual(self.problems(), [])

    def test_success_report_without_a_run_state_is_refused(self):
        self.write_round(write_state=False)
        self.assertIn("missing or unreadable", " ".join(self.problems()))

    def test_running_round_cannot_reuse_the_previous_success_report(self):
        self.write_round(run_id="previous")
        unit_evidence.start_run(
            self.report, run_id="current", version=self.VERSION, provenance=self.provenance
        )
        problems = " ".join(self.problems())
        self.assertIn("not completed", problems)
        self.assertIn("previous success report is not accepted", problems)

    def test_report_from_another_round_is_refused(self):
        self.write_round(run_id="old")
        unit_evidence.start_run(
            self.report, run_id="new", version=self.VERSION, provenance=self.provenance
        )
        unit_evidence.finish_run(self.report, run_id="new", success=True)
        self.assertIn("does not belong", " ".join(self.problems()))

    def test_report_fingerprint_must_match_the_tested_source(self):
        self.write_round(report_fingerprint="0" * 64)
        self.assertIn("does not match", " ".join(self.problems()))

    def test_failed_current_run_is_refused(self):
        self.write_round(report_success=False, state_success=False)
        self.assertIn("success=False", " ".join(self.problems()))

    def test_report_for_another_version_is_refused(self):
        self.write_round(version="0.35.4")
        self.assertIn("expected", " ".join(self.problems()))

    def test_zero_tests_is_refused(self):
        self.write_round(tests_run=0)
        self.assertIn("tests_run=0", " ".join(self.problems()))

    def test_versions_before_the_gate_keep_the_success_only_check(self):
        (self.base / "docs/validation/RELEASE-0.35.4.md").write_text(
            "全量 4299 项通过。\n", encoding="utf-8"
        )
        self.write_round(version="0.35.4", write_state=False)
        self.assertEqual(self.problems("0.35.4"), [])
