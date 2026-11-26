"""BUG-149: a read-only plan must never leave a model that needs recovery.

0.35.6 feedback: a client that exited while a read-only query was still running
left a job at ``unknown_outcome`` with ``termination.reason=no_runner_pid``. The
model kept that job as ``pending_job``, every later request was refused with
"Model has a pending job", ``creo_cancel_job`` reported "already terminal" and
no reconciliation action accepts a reservation nothing could have changed.

A read-only plan is admitted only with inspection operations, so it cannot
change geometry, the revision or the saved file. The cases below hold the code
to that invariant on every exit - delivered, undelivered, timed out, cancelled
and already stuck - and keep the mutating paths exactly as they were.
"""

from __future__ import annotations

import copy
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import bridge
from creo_mechdog import generic_bridge as general
from creo_mechdog import model_registry
from creo_mechdog import reconciliation as rec
from tests.unit import test_reconciliation as fixtures

JOB = "c" * 32
MODEL = "b" * 32
QUERY = {"op": "mass_properties"}


class ReadonlyJobExitTests(unittest.TestCase):
    """Drive the real ``run_generic_job`` against a temporary data root."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="bug149_exit_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "jobs").mkdir()
        (self.root / "models").mkdir()
        stack = ExitStack()
        self.addCleanup(stack.close)
        for obj, name, value in (
            (bridge, "ROOT", self.root),
            (bridge, "JOBS", self.root / "jobs"),
            (general, "MODELS", self.root / "models"),
        ):
            stack.enter_context(patch.object(obj, name, value))
        for name in (
            "apply_terminal_stage",
            "note_native_outcome",
            "record_host_release",
            "record_surface_loft_runtime",
        ):
            stack.enter_context(patch.object(bridge, name, return_value=None))
        stack.enter_context(
            patch.object(bridge, "build_native", return_value=self.root / "worker.exe")
        )
        stack.enter_context(patch.object(bridge, "native_environment", return_value={}))
        stack.enter_context(patch.object(bridge, "config", return_value={}))
        path = general.model_path(MODEL)
        (path / "output").mkdir(parents=True)
        self.part = path / "output" / "queried_part.prt.1"
        self.part.write_bytes(b"committed checkpoint fixture")
        self.model = {
            "model_id": MODEL,
            "model_name": "queried_part",
            "revision": 1,
            "status": "ready",
            "model_type": "part",
            "aliases": {},
            "part_file": str(self.part),
            "output_directory": str(path / "output"),
            "pending_job": JOB,
        }
        model_registry.write_model(path, self.model)
        directory = bridge.job_path(JOB)
        (directory / "output").mkdir(parents=True)
        self.request = {
            "new": False,
            "model": copy.deepcopy(self.model),
            "operations": [QUERY],
            "readonly": True,
            "readonly_source": "request",
            "components": {},
        }
        bridge.write_json(directory / "request.json", self.request)
        self.manifest = {
            "job_id": JOB,
            "kind": "generic",
            "model_id": MODEL,
            "status": "queued",
            "readonly": True,
            "readonly_source": "request",
        }
        bridge.write_json(directory / "job.json", self.manifest)

    def run_job(self, *, result=None, error=None, readonly=True):
        directory = bridge.job_path(JOB)

        def fake_run(*_args, **_kwargs):
            if error is not None:
                raise error
            if result is not None:
                bridge.write_json(directory / "native_result.json", result)
            return subprocess.CompletedProcess([], 0)

        request = {**self.request, "readonly": readonly}
        bridge.write_json(directory / "request.json", request)
        with patch.object(bridge.subprocess, "run", side_effect=fake_run):
            general.run_generic_job(JOB, copy.deepcopy(self.manifest))
        return (
            bridge.read_json(directory / "job.json"),
            bridge.read_json(general.model_path(MODEL) / "model.json"),
        )

    def test_missing_native_result_keeps_the_model_reusable(self):
        manifest, model = self.run_job()
        self.assertEqual(manifest["status"], "unknown_outcome")
        self.assertIn("read-only", manifest["message"])
        self.assertEqual(model["status"], "ready")
        self.assertIsNone(model["pending_job"])
        self.assertEqual(model["revision"], 1)

    def test_unconfirmed_delivery_keeps_the_model_reusable(self):
        manifest, model = self.run_job(
            result={"success": False, "delivery_complete": False, "disconnect_code": 9}
        )
        self.assertEqual(manifest["status"], "unknown_outcome")
        self.assertEqual(model["status"], "ready")
        self.assertIsNone(model["pending_job"])

    def test_timeout_after_the_worker_started_keeps_the_model_reusable(self):
        manifest, model = self.run_job(error=subprocess.TimeoutExpired(cmd="worker", timeout=600))
        self.assertEqual(manifest["status"], "unknown_outcome")
        self.assertTrue(manifest["worker_started"])
        self.assertEqual(model["status"], "ready")
        self.assertIsNone(model["pending_job"])

    def test_the_same_failures_still_lock_a_mutating_job(self):
        # Regression guard: the invariant is about read-only plans only. A
        # mutating plan whose delivery is unconfirmed keeps the reservation.
        manifest, model = self.run_job(
            result={"success": False, "delivery_complete": False, "disconnect_code": 9},
            readonly=False,
        )
        self.assertEqual(manifest["status"], "unknown_outcome")
        self.assertEqual(model["status"], "unknown_outcome")
        self.assertEqual(model["pending_job"], JOB)

    def test_busy_rejection_retires_only_a_readonly_reservation(self):
        directory = bridge.job_path(JOB)
        with (
            patch.object(
                bridge, "toolkit_lock", side_effect=bridge.ToolkitBusy(holder={"operation": "x"})
            ),
            patch.object(general, "_live_job_owners", return_value=[]),
        ):
            general.run_generic_job(JOB, copy.deepcopy(self.manifest))
        manifest = bridge.read_json(directory / "job.json")
        model = bridge.read_json(general.model_path(MODEL) / "model.json")
        self.assertEqual(manifest["status"], "failed")
        self.assertTrue(manifest["readonly_release"]["released"])
        self.assertIsNone(model["pending_job"])
        self.assertEqual(model["status"], "ready")


class ReadonlyCancelTests(unittest.TestCase):
    """``creo_cancel_job`` is the one call that retires the reservation."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="bug149_cancel_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "jobs").mkdir()
        (self.root / "models").mkdir()
        stack = ExitStack()
        self.addCleanup(stack.close)
        for obj, name, value in (
            (bridge, "ROOT", self.root),
            (bridge, "JOBS", self.root / "jobs"),
            (general, "MODELS", self.root / "models"),
        ):
            stack.enter_context(patch.object(obj, name, value))

    def job(self, status: str, *, readonly: bool = True, started: bool = True, **extra) -> Path:
        directory = self.root / "jobs" / JOB
        directory.mkdir(parents=True, exist_ok=True)
        (self.root / "models" / MODEL).mkdir(parents=True, exist_ok=True)
        bridge.write_json(
            directory / "job.json",
            {
                "job_id": JOB,
                "model_id": MODEL,
                "status": status,
                "worker_started": started,
                "readonly": readonly,
                **extra,
            },
        )
        bridge.write_json(directory / "request.json", {"new": False, "readonly": readonly})
        bridge.write_json(
            self.root / "models" / MODEL / "model.json",
            {
                "model_id": MODEL,
                "model_name": "bug149_cancel",
                "revision": 1,
                "status": "ready",
                "pending_job": JOB,
                "part_file": None,
            },
        )
        return directory

    def model(self) -> dict:
        return bridge.read_json(self.root / "models" / MODEL / "model.json")

    def lock_model(self) -> None:
        record = self.model()
        record["status"] = "unknown_outcome"
        bridge.write_json(self.root / "models" / MODEL / "model.json", record)

    def test_running_readonly_job_is_cancelled_without_claiming_a_geometry_change(self):
        self.job("running", runner_pid=4321)
        with patch.object(
            general, "_terminate_process_tree", return_value={"returncode": 0, "pid": 4321}
        ):
            result = general.cancel_job(JOB)
        self.assertTrue(result["cancelled"])
        self.assertEqual(result["status"], "unknown_outcome")
        self.assertFalse(result["geometry_may_have_changed"])
        self.assertTrue(result["readonly_release"]["released"])
        self.assertEqual(self.model()["status"], "ready")
        self.assertIsNone(self.model()["pending_job"])
        record = bridge.read_json(self.root / "jobs" / JOB / "job.json")
        self.assertFalse(record["cancellation"]["geometry_may_have_changed"])
        self.assertTrue(record["cancellation"]["readonly"])

    def test_terminal_readonly_job_retires_the_stuck_reservation(self):
        self.job("unknown_outcome")
        self.lock_model()
        with patch.object(general, "_live_job_owners", return_value=[]):
            result = general.cancel_job(JOB)
        self.assertFalse(result["cancelled"])
        self.assertEqual(result["status"], "unknown_outcome")
        self.assertTrue(result["readonly_release"]["released"])
        self.assertIn("retired", result["message"])
        self.assertEqual(self.model()["status"], "ready")
        self.assertIsNone(self.model()["pending_job"])
        # The job record itself is left alone: only the model reservation moves.
        self.assertEqual(
            bridge.read_json(self.root / "jobs" / JOB / "job.json")["status"], "unknown_outcome"
        )

    def test_a_live_owner_keeps_the_readonly_reservation(self):
        self.job("unknown_outcome")
        self.lock_model()
        live = [{"role": "native_worker", "pid": 99}]
        with patch.object(general, "_live_job_owners", return_value=live):
            result = general.cancel_job(JOB)
        self.assertFalse(result["readonly_release"]["released"])
        self.assertEqual(result["readonly_release"]["reason"], "runner_or_worker_still_alive")
        self.assertEqual(result["readonly_release"]["owners"], live)
        self.assertEqual(self.model()["status"], "unknown_outcome")
        self.assertEqual(self.model()["pending_job"], JOB)

    def test_terminal_mutating_job_is_still_reported_unchanged(self):
        self.job("unknown_outcome", readonly=False)
        self.lock_model()
        result = general.cancel_job(JOB)
        self.assertNotIn("readonly_release", result)
        self.assertEqual(self.model()["status"], "unknown_outcome")
        self.assertEqual(self.model()["pending_job"], JOB)

    def test_a_second_cancel_does_not_claim_a_second_release(self):
        self.job("unknown_outcome")
        self.lock_model()
        with patch.object(general, "_live_job_owners", return_value=[]):
            first = general.cancel_job(JOB)
            second = general.cancel_job(JOB)
        self.assertTrue(first["readonly_release"]["released"])
        self.assertFalse(second["readonly_release"]["released"])
        self.assertEqual(second["readonly_release"]["reason"], "model_does_not_hold_this_job")

    def test_readonly_release_requires_a_model_that_holds_the_job(self):
        self.job("unknown_outcome")
        record = self.model()
        record["pending_job"] = None
        bridge.write_json(self.root / "models" / MODEL / "model.json", record)
        with patch.object(general, "_live_job_owners", return_value=[]):
            result = general.cancel_job(JOB)
        self.assertFalse(result["readonly_release"]["released"])
        self.assertEqual(result["readonly_release"]["reason"], "model_does_not_hold_this_job")
        self.assertNotIn("next_steps", result)


class ReadonlyPendingDiagnostic(unittest.TestCase):
    """``creo_inspect_model`` names the exit an operator cannot guess."""

    save_model = fixtures.Reconciliation.save_model

    def setUp(self):
        fixtures.Reconciliation.setUp(self)
        bridge.write_json(
            bridge.job_path(self.original) / "job.json",
            {
                "job_id": self.original,
                "model_id": self.mid,
                "kind": "generic",
                "status": "unknown_outcome",
                "readonly": True,
                "readonly_source": "request",
                "created_at": bridge.now(),
            },
        )

    def test_a_readonly_pending_job_names_the_one_call_exit(self):
        value = rec.inspect(self.mid)
        block = value["readonly_pending"]
        self.assertEqual(block["job_id"], self.original)
        self.assertEqual(block["job_status"], "unknown_outcome")
        self.assertIn("creo_cancel_job", block["next_step"])
        self.assertIn("read-only", block["reason"])

    def test_a_mutating_pending_job_keeps_the_ordinary_actions(self):
        bridge.write_json(
            bridge.job_path(self.original) / "job.json",
            {"job_id": self.original, "model_id": self.mid, "status": "unknown_outcome"},
        )
        self.assertIsNone(rec.inspect(self.mid)["readonly_pending"])
