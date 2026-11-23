"""Unit tests for 0.35.8 feedback fixes (BUG-171, BUG-172, BUG-173, BUG-174)."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import bridge
from creo_mechdog import (
    compact_sections,
    job_pages,
    operation_results,
    schema,
)
from creo_mechdog import (
    reconciliation as rec,
)


class Bug171RecoveryBudgetAndTimeoutTests(unittest.TestCase):
    def test_recovery_budget_scales_by_features_surfaces_edges_and_allows_1800(self):
        small = {"inspection_summary": {"counts": {"edges": 100, "features": 20, "surfaces": 30}}}
        frigate = {
            "inspection_summary": {"counts": {"features": 474, "surfaces": 815, "edges": 2612}}
        }
        huge_edges = {"inspection_summary": {"counts": {"edges": 6428}}}
        with patch.object(bridge, "config", return_value={}):
            self.assertEqual(rec.recovery_phase_seconds(small), 300)
            # 474 features -> 120 + 237 = 357 s (> 300 s default)
            self.assertEqual(rec.recovery_phase_seconds(frigate), 120 + 474 // 2)
            self.assertEqual(rec.recovery_phase_seconds(huge_edges), 120 + 6428 // 15)
            self.assertEqual(rec.recovery_phase_seconds(frigate, budget_seconds=1800), 1800)
        with self.assertRaises(ValueError):
            rec.recovery_phase_seconds(frigate, budget_seconds=1801)

    def test_recovery_wait_reports_terminal_unconfirmed_instead_of_poll_advice(self):
        snapshot = {
            "model": {"model_id": "m" * 32, "recovery_pending": "a" * 32},
            "stalled_recovery": {"proven": False, "reason": "stage_advanced", "stage": "connect"},
        }
        with patch.object(rec, "_job_status", return_value="unknown_outcome"):
            wait = rec._recovery_wait(snapshot)
        self.assertIsNotNone(wait)
        self.assertEqual(wait["state"], "terminal_unconfirmed")
        self.assertEqual(wait["job_status"], "unknown_outcome")
        self.assertIn("Do not poll creo_get_job further", wait["next_step"])
        self.assertIn("restore_baseline", wait["next_step"])
        self.assertIn("abandon_unknown_recovery", wait["next_step"])

    def test_native_surfaces_recovery_phase_timeout_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            bridge.write_json(directory / "request.json", {"recovery_phase_seconds": 90})
            bridge.write_json(
                directory / "native_checkpoint.json",
                {
                    "success": False,
                    "delivery_complete": False,
                    "completion_stage": "recovery_phase_timeout",
                    "phase_budget_seconds": 90.0,
                },
            )
            bridge.write_json(
                directory / "native_result.json",
                {
                    "success": False,
                    "delivery_complete": False,
                    "completion_stage": "recovery_phase_timeout",
                    "failure_phase": "native_worker_started",
                    "phase_budget_seconds": 90.0,
                    "toolkit_code": -1,
                    "message": "Recovery native phase exceeded its budget of 90 s",
                },
            )
            manifest = {"job_id": "b" * 32}
            completed = subprocess.CompletedProcess(["worker"], 31)
            with (
                patch.object(bridge, "build_native", return_value=directory / "worker.exe"),
                patch.object(rec.subprocess, "run", return_value=completed),
            ):
                with self.assertRaisesRegex(
                    RuntimeError, r"recovery_phase_timeout \(90\.0 s\).*verify_mode='identity'"
                ):
                    rec._native(directory, manifest)
            self.assertEqual(
                manifest["result"]["completion_stage"],
                "recovery_phase_timeout",
            )

    def test_native_recovery_deadline_and_restore_baseline_single_inspection_contract(self):
        deadline_src = (bridge.ROOT / "native" / "recovery_deadline.h").read_text(encoding="utf-8")
        generic_src = (bridge.ROOT / "native" / "generic.cpp").read_text(encoding="utf-8")
        self.assertIn('job + L"\\\\native_result.json"', deadline_src)
        self.assertIn('"completion_stage", "recovery_phase_timeout"', deadline_src)
        self.assertIn("phase = std::min(1800.0, std::max(30.0, phase));", generic_src)
        self.assertIn(
            'J after = before;\n    if (action != "restore_baseline") {',
            generic_src,
        )


class Bug172LightweightInspectionAndProgressTests(unittest.TestCase):
    def test_native_inspection_uses_quiet_checks_progress_logs_and_light_helpers(self):
        src = (bridge.ROOT / "native" / "generic.cpp").read_text(encoding="utf-8")
        self.assertIn("static void check_quiet(ProError e, const char *op, int item_id = -1)", src)
        self.assertIn("INSPECT_PROGRESS phase=features", src)
        self.assertIn("INSPECT_PROGRESS phase=surfaces", src)
        self.assertIn("INSPECT_SUMMARY features=%d surfaces=%d edges=%d half_edges=%d", src)
        self.assertIn("INSPECT_LIMIT_EXCEEDED phase=features", src)
        self.assertIn("INSPECT_LIMIT_EXCEEDED phase=surfaces", src)
        self.assertIn("INSPECT_LIMIT_EXCEEDED phase=edges", src)
        self.assertIn("static int find_default_csys_id()", src)
        self.assertIn("static bool model_has_solid()", src)
        self.assertIn("static int active_body_count()", src)
        self.assertIn("static void check_model_health()", src)
        self.assertIn("return selection(find_default_csys_id(), PRO_CSYS);", src)
        self.assertIn("if (!model_has_solid() || new_body)", src)
        self.assertIn("int active = active_body_count();", src)


class Bug173InclinedSketchAnchorAndSolveErrorTests(unittest.TestCase):
    def test_native_sketch_builds_helper_anchor_and_reports_solve_failure_accurately(self):
        generic_src = (bridge.ROOT / "native" / "generic.cpp").read_text(encoding="utf-8")
        solver_src = (bridge.ROOT / "native" / "sketch_solver.cpp").read_text(encoding="utf-8")
        coord_src = (bridge.ROOT / "native" / "sketch_coordinates.cpp").read_text(encoding="utf-8")
        self.assertIn("static int build_helper_anchor_plane(", generic_src)
        self.assertIn("SKETCH_ANCHOR_HELPER=1", generic_src)
        self.assertIn("try_anchor_planes(tier0);", generic_src)
        self.assertIn('{"section_references", last_sketch_reference_info}', generic_src)
        self.assertIn("static J last_sketch_reference_info = nullptr;", coord_src)
        self.assertIn("Coordinate sketch ProSectionSolve failed with code ", solver_src)
        self.assertIn("rescue ProSectionAutodim also failed with code ", solver_src)
        self.assertIn("reference_incomplete=", solver_src)
        self.assertIn("origin_pin_available=", solver_src)


class Bug174ChamferDumpCutRatioAndRunnerDetachTests(unittest.TestCase):
    def test_dump_plan_operations_preserves_chamfer_type_for_revalidation(self):
        raw_d1_d2 = [
            {
                "op": "chamfer",
                "label": "ch_d1d2",
                "chamfer_type": "d1_d2",
                "distance_1": 150.0,
                "distance_2": 120.0,
                "reference_surface": {"kind": "surface", "id": 4311},
                "references": [{"edge": {"kind": "edge", "id": 4532}}],
            },
            {
                "op": "chamfer",
                "label": "ch_ang",
                "chamfer_type": "distance_angle",
                "size": 10.0,
                "angle_deg": 45.0,
                "angle_reference": {"kind": "surface", "id": 4311},
                "references": [{"edge": {"kind": "edge", "id": 4533}}],
            },
        ]
        models = schema.OPERATIONS.validate_python(raw_d1_d2)
        dumped_for_submit = schema.dump_plan_operations(models)
        self.assertEqual(dumped_for_submit[0]["chamfer_type"], "d1_d2")
        self.assertEqual(dumped_for_submit[1]["chamfer_type"], "distance_angle")
        # Re-validating through validate_operations (as general.submit does) must succeed
        # and still strip chamfer_type from the final native payload.
        validated = schema.validate_operations(dumped_for_submit)
        self.assertNotIn("chamfer_type", validated[0])
        self.assertNotIn("chamfer_type", validated[1])
        self.assertEqual(validated[0]["distance_1"], 150.0)
        self.assertEqual(validated[1]["angle_deg"], 45.0)

    def test_cut_volume_check_flags_low_removal_and_accepts_normal_removal(self):
        inputs = [
            {
                "op": "sketch",
                "label": "sk_cut",
                "plane": "XY",
                "entities": [
                    {"type": "rectangle", "name": "r1", "min": [0.0, 0.0], "max": [100.0, 100.0]}
                ],
            },
            {
                "op": "extrude",
                "label": "cut_grazing",
                "sketch": "sk_cut",
                "mode": "cut",
                "depth": 10.0,
                "depth_type": "blind",
            },
            {
                "op": "extrude",
                "label": "cut_full",
                "sketch": "sk_cut",
                "mode": "cut",
                "depth": 10.0,
                "depth_type": "blind",
            },
        ]
        native = {
            "success": True,
            "operations": [
                {"op": "sketch", "index": 0, "label": "sk_cut", "succeeded": True},
                {
                    "op": "extrude",
                    "index": 1,
                    "label": "cut_grazing",
                    "succeeded": True,
                    "material_removed_mm3": 300.0,  # 0.3% of 100,000 mm3
                    "extrude_depth": {
                        "effective_depth_type": "blind",
                        "effective_depth_mm": 10.0,
                        "query_code": 0,
                    },
                },
                {
                    "op": "extrude",
                    "index": 2,
                    "label": "cut_full",
                    "succeeded": True,
                    "material_removed_mm3": 54000.0,  # 54% of 100,000 mm3
                    "extrude_depth": {
                        "effective_depth_type": "blind",
                        "effective_depth_mm": 10.0,
                        "query_code": 0,
                    },
                },
            ],
        }
        annotated = operation_results.annotate_native_result(native, readonly=False, inputs=inputs)
        grazing_check = annotated["operations"][1]["cut_volume_check"]
        self.assertTrue(grazing_check["low_removal_warning"])
        self.assertAlmostEqual(grazing_check["expected_prism_volume_mm3"], 100000.0)
        self.assertAlmostEqual(grazing_check["removal_ratio"], 0.003)

        full_check = annotated["operations"][2]["cut_volume_check"]
        self.assertFalse(full_check["low_removal_warning"])
        self.assertAlmostEqual(full_check["removal_ratio"], 0.54)

    def test_spawn_detached_runner_falls_back_on_winerror_5(self):
        calls = []

        def fake_popen(cmd, **kwargs):
            calls.append(kwargs.get("creationflags"))
            if len(calls) == 1:
                err = PermissionError("Access is denied")
                err.winerror = 5
                raise err
            mock_proc = MagicMock()
            mock_proc.pid = 4321
            return mock_proc

        with patch.object(bridge.os, "name", "nt"):
            proc, detached = bridge.spawn_detached_runner(
                ["python", "bridge.py"], cwd=bridge.ROOT, log_file=None, popen=fake_popen
            )
        self.assertFalse(detached)
        self.assertEqual(proc.pid, 4321)
        self.assertEqual(len(calls), 2)

    def test_compact_and_job_page_keys_include_new_diagnostics(self):
        self.assertIn("cut_volume_check", compact_sections.OPERATION_KEYS)
        self.assertIn("section_references", compact_sections.OPERATION_KEYS)
        self.assertIn("runner_detached_from_job", job_pages._SUMMARY_KEYS)
        self.assertIn("runner_lifecycle_note", job_pages._SUMMARY_KEYS)


if __name__ == "__main__":
    unittest.main()
