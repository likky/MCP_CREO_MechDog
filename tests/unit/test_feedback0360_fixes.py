"""Unit tests for 0.36.0 feedback fixes (BUG-170, BUG-166, FEAT-076, FEAT-077)."""

from __future__ import annotations

import hashlib
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bridge
import creo_startup
import generic_bridge
from creo_mechdog import (
    geometry_selectors,
    model_queries,
    model_registry,
    session_candidates,
)
from creo_mechdog import (
    reconciliation as rec,
)


class Bug170StaleSessionAndForceNewTests(unittest.TestCase):
    def test_stale_session_diagnosis_triggers_on_minus_four_with_alive_process(self):
        native = {
            "connected": False,
            "toolkit_code": -4,
            "connection_state": "not_found_or_unreadable",
            "toolkit_hint": "PRO_TK_BAD_CONTEXT: this worker process has no Toolkit context",
        }
        snapshot = {
            "available": True,
            "processes": [{"pid": 1234, "name": "xtop.exe", "matches": True}],
        }
        diag = creo_startup._stale_session_diagnosis(native, snapshot)
        self.assertIsNotNone(diag)
        self.assertTrue(diag["stale_session_detected"])
        self.assertEqual(diag["diagnosis"], "stale_session_needs_restart")
        self.assertGreaterEqual(len(diag["next_steps"]), 2)
        self.assertIn("Close the existing Creo", diag["next_steps"][0])
        self.assertIn("force_new_session=true", diag["next_steps"][1])

    def test_stale_session_diagnosis_silent_when_connected_or_no_process(self):
        self.assertIsNone(
            creo_startup._stale_session_diagnosis(
                {"connected": True, "toolkit_code": 0},
                {"available": True, "processes": [{"pid": 1, "matches": True}]},
            )
        )
        self.assertIsNone(
            creo_startup._stale_session_diagnosis(
                {"connected": False, "toolkit_code": -4},
                {"available": True, "processes": []},
            )
        )

    def test_force_new_session_argument_guards(self):
        coord = creo_startup.CreoStartup()
        with self.assertRaisesRegex(ValueError, "requires retry=true"):
            coord.start(retry=False, force_new_session=True)
        with self.assertRaisesRegex(ValueError, "cannot be combined"):
            coord.start(retry=True, session_id="abc", force_new_session=True)

    def test_session_candidates_explicitly_marked_diagnostic_only(self):
        built = session_candidates.build(
            {"available": True, "processes": [{"pid": 42, "name": "xtop.exe", "matches": True}]},
            {"source": "default", "session_fingerprint": None},
        )
        self.assertTrue(built["diagnostic_only"])
        self.assertFalse(built["selectable_by_pid"])

    def test_drive_stale_session_without_and_with_force_new_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exe = root / "parametric.exe"
            psf = root / "parametric.psf"
            exe.write_text("", encoding="utf-8")
            psf.write_text("", encoding="utf-8")
            settings = creo_startup.Settings(
                auto_start=True,
                executable=exe,
                psf=psf,
                args=[],
                timeout=1,
                probe_timeout=1,
                total_budget=10,
                selected=False,
            )
            alive_inv = {
                "processes": [
                    {"pid": 9999, "created": 100, "image": str(exe), "matches": True},
                ],
                "uncertain": False,
            }
            bad_probe = {
                "connected": False,
                "toolkit_code": -4,
                "connection_state": "not_found_or_unreadable",
                "toolkit_hint": "PRO_TK_BAD_CONTEXT",
            }
            good_probe = {"connected": True, "toolkit_code": 0}
            fake_now = 100.0

            def advance_clock(timeout: float) -> bool:
                nonlocal fake_now
                fake_now += timeout
                return False

            # BUG-175: only retry waits consume the simulated budget in either scenario.
            with (
                patch.object(creo_startup, "time", wraps=creo_startup.time) as startup_time,
                patch.object(creo_startup, "inventory", return_value=alive_inv),
                patch.object(
                    creo_startup,
                    "process_snapshot",
                    return_value={"available": True, "processes": alive_inv["processes"]},
                ),
                patch.object(bridge, "ROOT", root),
                patch.object(bridge, "toolkit_lock"),
                patch.object(bridge, "build_native", return_value=exe),
            ):
                startup_time.monotonic.side_effect = lambda: fake_now
                for force_new_session in (False, True):
                    with self.subTest(force_new_session=force_new_session):
                        directory = root / ("forced" if force_new_session else "stale")
                        directory.mkdir()
                        coord = creo_startup.CreoStartup(directory=directory)
                        coord._directory = directory
                        with (
                            patch.object(coord._stop, "wait", side_effect=advance_clock),
                            patch.object(
                                bridge,
                                "session_status",
                                return_value=bad_probe,
                                side_effect=[bad_probe, good_probe] if force_new_session else None,
                            ),
                            patch.object(
                                creo_startup,
                                "launch_creo",
                                return_value=creo_startup.DesktopLaunch(),
                            ) as launcher,
                        ):
                            coord._drive(
                                settings,
                                True,
                                fake_now + settings.total_budget,
                                force_new_session=force_new_session,
                            )
                        status = coord.status()
                        if force_new_session:
                            launcher.assert_called_once()
                            self.assertEqual(status["state"], "ready")
                            self.assertTrue(status["connected"])
                            self.assertEqual(status["launch_attempt"], 1)
                        else:
                            launcher.assert_not_called()
                            self.assertEqual(status["state"], "timeout")
                            self.assertTrue(status["stale_session_detected"])
                            self.assertEqual(status["diagnosis"], "stale_session_needs_restart")


class Bug166RecoveryAndBlockingTests(unittest.TestCase):
    def test_adaptive_recovery_phase_budget_scales_for_high_edge_model(self):
        small = {"inspection_summary": {"counts": {"edges": 100}}}
        huge = {"inspection_summary": {"counts": {"edges": 6428}}}
        with patch.object(bridge, "config", return_value={}):
            self.assertEqual(rec.recovery_phase_seconds(small), 300)
            self.assertEqual(rec.recovery_phase_seconds(huge), 120 + 6428 // 15)
            self.assertEqual(rec.recovery_phase_seconds(huge, budget_seconds=720), 720)
        with self.assertRaises(ValueError):
            rec.recovery_phase_seconds(huge, budget_seconds=10)
        with self.assertRaises(ValueError):
            rec.recovery_phase_seconds(huge, budget_seconds=True)  # type: ignore[arg-type]

    def test_recovery_pending_reports_recovery_pending_blocking_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mid = "a" * 32
            rec_id = "b" * 32
            model_dir = root / "models" / mid
            (model_dir / "output").mkdir(parents=True)
            model_registry.write_model(
                model_dir,
                {
                    "model_id": mid,
                    "model_name": "p05_test",
                    "model_type": "part",
                    "status": "ready",
                    "revision": 12,
                    "pending_job": None,
                    "recovery_pending": rec_id,
                    "output_directory": str(model_dir / "output"),
                    "part_file": None,
                },
            )
            with (
                patch.object(bridge, "ROOT", root),
                patch.object(generic_bridge, "MODELS", root / "models"),
            ):
                with self.assertRaises(bridge.ToolkitBusy) as ctx:
                    generic_bridge.submit([], model_id=mid, expected_revision=12)
                payload = ctx.exception.payload
                self.assertEqual(payload["blocking_operation"], "recovery_pending")
                self.assertEqual(payload["blocking_job_id"], rec_id)
                self.assertIsNone(payload["owner_snapshot"]["pending_job"])
                self.assertEqual(payload["owner_snapshot"]["recovery_pending"], rec_id)
                self.assertIn("expected_pending_job_id=null", payload["message"])

    def test_abandon_unknown_recovery_releases_reservation_metadata_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mid = "c" * 32
            rec_id = "d" * 32
            model_dir = root / "models" / mid
            out_dir = model_dir / "output"
            out_dir.mkdir(parents=True)
            part = out_dir / "p05_test.prt.13"
            content = b"fake-creo-part-bytes"
            part.write_bytes(content)
            sha = hashlib.sha256(content).hexdigest()
            model_registry.write_model(
                model_dir,
                {
                    "model_id": mid,
                    "model_name": "p05_test",
                    "model_type": "part",
                    "status": "ready",
                    "revision": 12,
                    "pending_job": None,
                    "recovery_pending": rec_id,
                    "output_directory": str(out_dir),
                    "part_file": str(part),
                    "part_sha256": sha,
                    "inspection": {"volume_mm3": 1000.0},
                },
            )
            job_dir = root / "jobs" / rec_id
            job_dir.mkdir(parents=True)
            bridge.write_json(
                job_dir / "job.json",
                {
                    "job_id": rec_id,
                    "model_id": mid,
                    "kind": "reconciliation",
                    "idempotency_key": "prev-rec-key-0001",
                    "status": "unknown_outcome",
                    "failure_phase": "native_worker_started",
                    "worker_started": True,
                },
            )
            bridge.write_json(
                job_dir / "request.json",
                {"model": {"model_id": mid}},
            )
            with (
                patch.object(bridge, "ROOT", root),
                patch.object(bridge, "JOBS", root / "jobs"),
                patch.object(bridge, "config", return_value={}),
                patch.object(generic_bridge, "MODELS", root / "models"),
                patch.object(rec, "_deployment", return_value={"digest": "fixed"}),
                patch.object(
                    rec,
                    "_owners",
                    return_value={
                        "job_id": rec_id,
                        "stopped": True,
                        "runner": {"recorded": None},
                        "worker": {"recorded": None},
                        "stop_evidence": "no_recorded_owner",
                    },
                ),
            ):
                inspected = rec.inspect(mid, live=False)
                action_state = inspected["actions"]["abandon_unknown_recovery"]
                self.assertTrue(action_state["available"])
                self.assertEqual(action_state["recovery_job_id"], rec_id)
                self.assertEqual(action_state["recovery_job_status"], "unknown_outcome")

                # Refused without confirmation flag
                with self.assertRaisesRegex(ValueError, "confirm_unknown_recovery=true"):
                    rec.apply(
                        mid,
                        "abandon_unknown_recovery",
                        12,
                        None,
                        inspected["evidence_token"],
                        "abandon-key-0001",
                        confirm_unknown_recovery=False,
                    )

                # Succeeds with confirmation flag
                applied = rec.apply(
                    mid,
                    "abandon_unknown_recovery",
                    12,
                    None,
                    inspected["evidence_token"],
                    "abandon-key-0001",
                    confirm_unknown_recovery=True,
                )
                self.assertTrue(applied["recovery_pending_released"])
                self.assertIsNone(applied["recovery_pending"])
                self.assertEqual(applied["status"], "ready")
                self.assertEqual(applied["revision"], 12)
                self.assertFalse(applied["disk_state_verified"])
                self.assertFalse(applied["session_state_verified"])
                self.assertTrue(applied["baseline_hash_verified"])

                # Replay with same idempotency_key returns recorded result
                replayed = rec.apply(
                    mid,
                    "abandon_unknown_recovery",
                    12,
                    None,
                    inspected["evidence_token"],
                    "abandon-key-0001",
                    confirm_unknown_recovery=True,
                )
                self.assertEqual(replayed, applied)

                # Model on disk now has recovery_pending=None and unchanged revision/file
                after_model = generic_bridge.model_info(mid)
                self.assertIsNone(after_model["recovery_pending"])
                self.assertEqual(after_model["status"], "ready")
                self.assertEqual(after_model["revision"], 12)
                self.assertEqual(after_model["part_sha256"], sha)

    def test_cross_session_restore_baseline_and_abandon_new_omit_dead_owner_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mid = "1" * 32
            old_job_id = "2" * 32
            model_dir = root / "models" / mid
            out_dir = model_dir / "output"
            out_dir.mkdir(parents=True)
            model_registry.write_model(
                model_dir,
                {
                    "model_id": mid,
                    "model_name": "new_uncommitted",
                    "model_type": "part",
                    "status": "unknown_outcome",
                    "revision": 0,
                    "pending_job": old_job_id,
                    "recovery_pending": None,
                    "output_directory": str(out_dir),
                    "part_file": None,
                },
            )
            job_dir = root / "jobs" / old_job_id
            job_dir.mkdir(parents=True)
            bridge.write_json(
                job_dir / "job.json",
                {"job_id": old_job_id, "model_id": mid, "status": "unknown_outcome"},
            )
            bridge.write_json(job_dir / "request.json", {"model": {"model_id": mid}})
            with (
                patch.object(bridge, "ROOT", root),
                patch.object(bridge, "JOBS", root / "jobs"),
                patch.object(bridge, "config", return_value={}),
                patch.object(generic_bridge, "MODELS", root / "models"),
                patch.object(rec, "_deployment", return_value={"digest": "fixed"}),
                patch.object(
                    rec,
                    "_owners",
                    return_value={
                        "job_id": old_job_id,
                        "stopped": True,
                        "runner": {"recorded": None},
                        "worker": {
                            "recorded": {"session_fingerprint": "dead-old-creo-session-999"}
                        },
                        "stop_evidence": "exited",
                    },
                ),
                patch.object(rec.subprocess, "Popen") as popen,
                patch.object(bridge, "write_channel_claim"),
            ):
                popen.return_value.pid = 4321
                inspected = rec.inspect(mid, live=False)
                self.assertTrue(inspected["actions"]["abandon_new"]["available"])
                rec_job = rec.apply(
                    mid,
                    "abandon_new",
                    0,
                    old_job_id,
                    inspected["evidence_token"],
                    "cross-sess-abandon-01",
                )
                req = bridge.read_json(root / "jobs" / rec_job["job_id"] / "request.json")
                self.assertNotIn("session_fingerprint", req["reconciliation"])


class Feat076EdgeSelectorAndNearQueryTests(unittest.TestCase):
    def test_edge_geometry_selector_accepts_model_space_feature_filter(self):
        sel = geometry_selectors.validate_geometry_selector(
            {
                "kind": "geometry_selector",
                "target": "edge",
                "point_mm": [92.075, -123.98, 76.332],
                "tolerance_mm": 0.5,
                "feature": "window_cut",
            }
        )
        self.assertEqual(sel["feature"], "window_cut")
        self.assertEqual(sel["target"], "edge")

        with self.assertRaisesRegex(ValueError, "feature"):
            geometry_selectors.validate_geometry_selector(
                {
                    "kind": "geometry_selector",
                    "target": "edge",
                    "point_mm": [0, 0, 0],
                    "tolerance_mm": 0.5,
                    "coordinate_space": "assembly",
                    "feature": "window_cut",
                }
            )

    def test_inspect_page_near_filter_finds_closest_edges_among_6428_edges_in_one_call(self):
        edges = [
            {
                "id": idx + 1,
                "type": 2,
                "start": [float(idx), 0.0, 0.0],
                "end": [float(idx), 10.0, 0.0],
            }
            for idx in range(6427)
        ]
        # Add an arc edge right next to the anchor
        edges.append(
            {
                "id": 9999,
                "type": 3,
                "arc": {
                    "origin": [500.0, 50.0, 0.0],
                    "radius": 10.0,
                    "start_angle": 0.0,
                    "end_angle": math.pi,
                    "v1": [1.0, 0.0, 0.0],
                    "v2": [0.0, 1.0, 0.0],
                },
            }
        )
        model = {
            "model_id": "e" * 32,
            "model_name": "big_wheel",
            "revision": 12,
            "status": "ready",
            "model_type": "part",
            "inspection": {"edges": edges, "surfaces": []},
        }
        page = model_queries.inspect_page(
            model,
            detail="full",
            section="edges",
            limit=3,
            near=[500.0, 60.2, 0.0],
            max_distance_mm=5.0,
        )
        returned = page["data"]["edges"]
        self.assertEqual(len(returned), 1)
        self.assertEqual(returned[0]["id"], 9999)
        self.assertAlmostEqual(returned[0]["distance_mm"], 0.2, places=5)
        self.assertEqual(page["near_filter"]["scanned_total"], 6428)
        self.assertEqual(page["near_filter"]["matched_total"], 1)

        # Anchor near straight edges 100, 101, 99
        page2 = model_queries.inspect_page(
            model, detail="full", section="edges", limit=3, near=[100.1, 5.0, 0.0]
        )
        ids2 = [item["id"] for item in page2["data"]["edges"]]
        self.assertEqual(ids2, [101, 102, 100])
        self.assertAlmostEqual(page2["data"]["edges"][0]["distance_mm"], 0.1, places=5)

    def test_inspect_page_near_rejects_invalid_combinations(self):
        model = {
            "model_id": "f" * 32,
            "model_name": "p",
            "revision": 1,
            "status": "ready",
            "model_type": "part",
            "inspection": {"edges": [], "surfaces": []},
        }
        with self.assertRaisesRegex(ValueError, "detail=full"):
            model_queries.inspect_page(model, detail="compact", near=[0, 0, 0])
        with self.assertRaisesRegex(ValueError, "section=edges or surfaces"):
            model_queries.inspect_page(model, detail="full", section="features", near=[0, 0, 0])
        with self.assertRaisesRegex(ValueError, "requires near"):
            model_queries.inspect_page(model, detail="full", section="edges", max_distance_mm=1.0)


if __name__ == "__main__":
    unittest.main()
