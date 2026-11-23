"""0.35.5 feedback P0: offline contracts for BUG-157/158/159/160.

The duplicate-circle rejection (BUG-161) and the edge-selector target
(BUG-155) are decided inside the native executor, so their input contract is
covered by ``tools/test_feedback0355_selector_round.py`` on a live session.
This module keeps the pure-Python parts: unsupported-area reporting, the
watchdog's log selection, the published budgets and the 1e-6 mm arc join.
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import bridge
import generic_bridge as general
from creo_mechdog import operation_results, submission_receipts
from creo_mechdog.endpoint_welding import (
    ARC_COINCIDENT_TOLERANCE_MM,
    prepare_endpoint_weld,
)
from creo_mechdog.profile_diagnostics import analyze_profile, validate_solid_profile

JOB = "a" * 32
MODEL = "b" * 32


class UnsupportedAreaTests(unittest.TestCase):
    """BUG-160: a partial analysis must not publish a numeric area."""

    def entities(self):
        return [
            {"type": "b_spline", "name": "s1"},
            {"type": "b_spline", "name": "s2"},
        ]

    def test_partial_analysis_reports_a_null_area_with_its_reason(self):
        report = analyze_profile(self.entities())
        self.assertEqual(report["analysis"], "partial")
        self.assertIsNone(report["material_area_mm2"])
        self.assertEqual(report["area_status"], "unavailable_unsupported_entities")
        self.assertEqual(report["unsupported_entities"], ["s1", "s2"])
        self.assertIn("not modelled", report["area_unavailable_reason"])

    def test_complete_analysis_keeps_the_measured_area(self):
        report = analyze_profile(
            [{"type": "rectangle", "name": "r", "min": [0, 0], "max": [10, 5]}]
        )
        self.assertEqual(report["analysis"], "complete")
        self.assertEqual(report["area_status"], "complete")
        self.assertIsNone(report["area_unavailable_reason"])
        self.assertAlmostEqual(report["material_area_mm2"], 50.0)

    def test_projection_keeps_the_null_area_and_status(self):
        summary = operation_results._profile_summary(self.entities(), None)
        self.assertIsNone(summary["material_area_mm2"])
        self.assertEqual(summary["area_status"], "unavailable_unsupported_entities")
        self.assertEqual(summary["unsupported_entities"], ["s1", "s2"])


class FakeStop:
    """Stands in for threading.Event.wait so the watcher loop is deterministic."""

    def __init__(self, iterations: int, on_wait=None):
        self.iterations = iterations
        self.on_wait = on_wait
        self.calls = 0

    def wait(self, _timeout):
        self.calls += 1
        if self.on_wait is not None and self.calls <= self.iterations:
            self.on_wait()
        return self.calls > self.iterations


class WatchdogLogSelectionTests(unittest.TestCase):
    """BUG-157: the native executor's progress lives in native.log."""

    def setUp(self):
        self.enterContext(patch.object(bridge, "config", return_value={}))
        temporary = self.enterContext(tempfile.TemporaryDirectory(prefix="bug157_watch_"))
        self.directory = Path(temporary)
        (self.directory / "worker.log").write_bytes(b"")
        (self.directory / "native.log").write_bytes(b"")

    def clock(self):
        now = {"value": 0.0}

        def monotonic():
            now["value"] += 1.0
            return now["value"]

        return monotonic

    def test_native_log_growth_keeps_the_job_alive(self):
        state: dict = {}

        def grow():
            with (self.directory / "native.log").open("ab") as log:
                log.write(b"PHASE=solve\n")

        with (
            patch.object(general, "stall_watchdog_seconds", return_value=2),
            patch.object(general.time, "monotonic", side_effect=self.clock()),
        ):
            general._watch_worker_log(self.directory, FakeStop(3, grow), state)
        self.assertNotIn("stalled", state)
        self.assertGreater(state["native_log_bytes"], 0)
        self.assertEqual(state["last_growth_source"], "native.log")

    def test_silent_logs_still_stall_and_name_the_native_log(self):
        state: dict = {}
        with (
            patch.object(general, "stall_watchdog_seconds", return_value=2),
            patch.object(general.time, "monotonic", side_effect=self.clock()),
            patch.object(general, "_terminate_process_tree") as kill,
        ):
            general._watch_worker_log(self.directory, FakeStop(5), state)
        self.assertTrue(state["stalled"])
        self.assertEqual(state["source"], "generic_stall_seconds")
        self.assertEqual(state["worker_log_bytes"], 0)
        self.assertEqual(state["native_log_bytes"], 0)
        self.assertIsNone(state["last_growth_source"])
        self.assertIn("Worker and native logs", state["message"])
        kill.assert_called_once()

    def test_a_worker_log_growth_is_still_progress(self):
        state: dict = {}

        def grow():
            with (self.directory / "worker.log").open("ab") as log:
                log.write(b"runner output\n")

        with (
            patch.object(general, "stall_watchdog_seconds", return_value=2),
            patch.object(general.time, "monotonic", side_effect=self.clock()),
        ):
            general._watch_worker_log(self.directory, FakeStop(3, grow), state)
        self.assertNotIn("stalled", state)
        self.assertEqual(state["last_growth_source"], "worker.log")


class BudgetProjectionTests(unittest.TestCase):
    """BUG-158: the submit receipt, the running job and the terminal job agree."""

    def budgets(self):
        return {
            "timeout_seconds": 1800,
            "timeout_source": "operation_estimate",
            "stall_watchdog_seconds": 600,
            "stall_watchdog_source": "config:generic_stall_seconds",
            "watch_files": ["worker.log", "native.log"],
        }

    def test_submission_receipt_keeps_the_budget_pair(self):
        receipt = {
            "job_id": JOB,
            "kind": "generic",
            "model_id": MODEL,
            "status": "queued",
            "operations": [{"op": "sketch"}],
            **self.budgets(),
        }
        compact = submission_receipts.project_receipt(receipt, "compact")
        self.assertEqual(compact["stall_watchdog_seconds"], 600)
        self.assertEqual(compact["stall_watchdog_source"], "config:generic_stall_seconds")
        self.assertEqual(compact["watch_files"], ["worker.log", "native.log"])
        self.assertEqual(compact["timeout_seconds"], 1800)
        self.assertEqual(compact["timeout_source"], "operation_estimate")

    def test_running_and_terminal_views_keep_the_same_budgets(self):
        root = self.enterContext(tempfile.TemporaryDirectory(prefix="bug158_budgets_"))
        jobs = Path(root)
        self.enterContext(patch.object(bridge, "JOBS", jobs))
        (jobs / JOB).mkdir()
        manifest = {
            "job_id": JOB,
            "kind": "generic",
            "model_id": MODEL,
            "status": "running",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "operations": [],
            **self.budgets(),
            "budgets": {
                "job_timeout_seconds": 1800,
                "timeout_source": "operation_estimate",
                "stall_watchdog_seconds": 600,
                "stall_watchdog_source": "config:generic_stall_seconds",
                "watch_files": ["worker.log", "native.log"],
            },
        }
        bridge.write_json(jobs / JOB / "job.json", manifest)
        running = bridge.get_job(JOB, detail="compact")
        self.assertEqual(
            running["budgets"],
            {
                "job_timeout_seconds": 1800,
                "timeout_source": "operation_estimate",
                "stall_watchdog_seconds": 600,
                "stall_watchdog_source": "config:generic_stall_seconds",
                "watch_files": ["worker.log", "native.log"],
            },
        )
        manifest.update(status="succeeded", revision=2)
        bridge.write_json(jobs / JOB / "job.json", manifest)
        terminal = bridge.get_job(JOB, detail="compact")
        self.assertEqual(terminal["budgets"], running["budgets"])
        self.assertEqual(json.dumps(terminal["budgets"]), json.dumps(running["budgets"]))


class ArcJoinToleranceTests(unittest.TestCase):
    """BUG-159: a 1e-6 mm residual join is already coincident."""

    def arcs(self, gap: float):
        """Two tangent arcs whose join is short by ``gap`` millimetres."""
        return [
            {
                "type": "arc",
                "name": "a1",
                "center": [0.0, 0.0],
                "radius": 5.0,
                "start_angle": 0.0,
                "end_angle": 90.0,
            },
            {
                "type": "arc",
                "name": "a2",
                "center": [0.0, 10.0 + gap],
                "radius": 5.0,
                "start_angle": 270.0,
                "end_angle": 360.0,
            },
        ]

    def test_residual_gaps_are_coincident(self):
        for gap in (3.464e-08, 4.727e-08, 9.9e-07):
            receipt = prepare_endpoint_weld(self.arcs(gap))
            self.assertEqual(receipt["candidate_pairs"], 0, gap)
            self.assertEqual(receipt["refused"], [], gap)
            self.assertEqual(receipt["accepted_pairs"], 0, gap)
        self.assertEqual(ARC_COINCIDENT_TOLERANCE_MM, 1e-6)

    def test_a_gap_above_the_tolerance_is_a_candidate_not_a_weld(self):
        receipt = prepare_endpoint_weld(self.arcs(5e-5))
        self.assertEqual(receipt["candidate_pairs"], 1)
        self.assertEqual(receipt["accepted_pairs"], 0)
        self.assertTrue(receipt["refused"])

    def test_a_kernel_open_gap_is_not_hidden(self):
        receipt = prepare_endpoint_weld(self.arcs(1e-3))
        self.assertEqual(receipt["candidate_pairs"], 0)
        self.assertEqual(receipt["accepted_pairs"], 0)
        self.assertEqual(receipt["welded_pairs"], 0)

    def closed_arcs(self, gap: float):
        """Two semicircles whose endpoints are offset by ``gap`` millimetres."""
        return [
            {
                "type": "arc",
                "name": "c1",
                "center": [0.0, 0.0],
                "radius": 10.0,
                "start_angle": 0.0,
                "end_angle": 180.0,
            },
            {
                "type": "arc",
                "name": "c2",
                "center": [gap, 0.0],
                "radius": 10.0,
                "start_angle": 180.0,
                "end_angle": 360.0,
            },
        ]

    def test_coordinate_admission_accepts_a_residual_arc_chain(self):
        # BUG-159: the 1e-6 mm join is already coincident for arcs, so the
        # coordinate gate must not call it a near-tolerance weld candidate.
        report = validate_solid_profile(self.closed_arcs(5e-7), "coordinates")
        self.assertEqual(report["closed_contour_count"], 1)
        self.assertEqual(report["open_contour_count"], 0)

    def test_coordinate_admission_still_refuses_an_arc_gap_above_the_rule(self):
        with self.assertRaisesRegex(ValueError, "near_tolerance"):
            validate_solid_profile(self.closed_arcs(2e-6), "coordinates")


if __name__ == "__main__":
    unittest.main()
