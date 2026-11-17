"""BUG-131: job cancellation, the worker stall watchdog and new-assembly exits.

The cancel cases drive the real ``generic_bridge.cancel_job`` against a
temporary data root; only process termination is substituted, so no process is
killed and no Creo/Toolkit boundary is touched. The reconciliation cases call
``reconciliation._actions`` with stopped owners and a patched pending-job read.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bridge
import generic_bridge as general
from creo_mechdog import reconciliation as rec

JOB = "a" * 32
MODEL = "b" * 32


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class JobCancelTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bug131_cancel_")
        self.root = Path(self.temporary.name)
        (self.root / "jobs").mkdir()
        (self.root / "models").mkdir()
        self.original = (bridge.ROOT, bridge.JOBS, general.MODELS)
        bridge.ROOT = self.root
        bridge.JOBS = self.root / "jobs"
        general.MODELS = self.root / "models"

    def tearDown(self):
        bridge.ROOT, bridge.JOBS, general.MODELS = self.original
        self.temporary.cleanup()

    def job(self, status: str, *, started: bool, new: bool = False, **extra) -> Path:
        directory = self.root / "jobs" / JOB
        _write(
            directory / "job.json",
            {
                "job_id": JOB,
                "model_id": MODEL,
                "status": status,
                "worker_started": started,
                "runner_pid": 4321,
                **extra,
            },
        )
        _write(directory / "request.json", {"new": new, "model": {"model_id": MODEL}})
        _write(
            self.root / "models" / MODEL / "model.json",
            {
                "model_id": MODEL,
                "model_name": "bug131_cancel",
                "revision": 0,
                "status": "building" if status != "queued" else "pending",
                "pending_job": JOB,
                "part_file": None,
            },
        )
        return directory

    def model(self) -> dict:
        return _read(self.root / "models" / MODEL / "model.json")

    def test_terminal_job_is_reported_without_killing_anything(self):
        self.job("succeeded", started=True)
        with patch.object(general, "_terminate_process_tree") as kill:
            result = general.cancel_job(JOB)
        self.assertFalse(result["cancelled"])
        self.assertEqual(result["status"], "succeeded")
        kill.assert_not_called()

    def test_cancel_before_worker_releases_the_model(self):
        self.job("queued", started=False)
        with (
            patch.object(
                general, "_terminate_process_tree", return_value={"returncode": 0, "pid": 4321}
            ),
            patch.object(bridge, "clear_channel_claim") as clear,
        ):
            result = general.cancel_job(JOB)
        self.assertTrue(result["cancelled"])
        self.assertEqual(result["status"], "cancelled")
        self.assertFalse(result["geometry_may_have_changed"])
        self.assertEqual(self.model()["status"], "ready")
        self.assertIsNone(self.model()["pending_job"])
        record = _read(self.root / "jobs" / JOB / "job.json")
        self.assertEqual(record["status"], "cancelled")
        self.assertIn("cancel_requested_at", record)
        clear.assert_called_once_with(JOB)

    def test_cancel_of_a_new_model_before_worker_marks_it_failed(self):
        self.job("queued", started=False, new=True)
        with patch.object(general, "_terminate_process_tree", return_value={"returncode": 0}):
            result = general.cancel_job(JOB)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(self.model()["status"], "failed")
        self.assertIsNone(self.model()["pending_job"])

    def test_cancel_after_worker_start_is_unknown_outcome(self):
        self.job("running", started=True)
        with patch.object(
            general, "_terminate_process_tree", return_value={"returncode": 0, "pid": 4321}
        ):
            result = general.cancel_job(JOB)
        self.assertEqual(result["status"], "unknown_outcome")
        self.assertTrue(result["geometry_may_have_changed"])
        self.assertEqual(self.model()["status"], "unknown_outcome")
        self.assertEqual(self.model()["pending_job"], JOB)
        self.assertIn("creo_reconcile_model", " ".join(result["next_steps"]))
        record = _read(self.root / "jobs" / JOB / "job.json")
        self.assertEqual(record["status"], "unknown_outcome")
        self.assertEqual(record["cancellation"]["worker_started"], True)

    def test_unconfirmed_termination_keeps_the_job_running(self):
        self.job("running", started=True)
        with patch.object(
            general,
            "_terminate_process_tree",
            return_value={"attempted": True, "pid": 4321, "returncode": 1, "output": "denied"},
        ):
            result = general.cancel_job(JOB)
        self.assertFalse(result["cancelled"])
        self.assertEqual(result["status"], "running")
        record = _read(self.root / "jobs" / JOB / "job.json")
        self.assertEqual(record["status"], "running")
        self.assertEqual(record["stage"], "cancel_requested")
        self.assertIn("cancel_requested_at", record)

    def test_job_that_finished_during_the_kill_keeps_its_outcome(self):
        directory = self.job("running", started=True)

        def finish(*_args, **_kwargs):
            _write(directory / "job.json", {"job_id": JOB, "status": "succeeded"})
            return {"returncode": 0}

        with patch.object(general, "_terminate_process_tree", side_effect=finish):
            result = general.cancel_job(JOB)
        self.assertFalse(result["cancelled"])
        self.assertEqual(result["status"], "succeeded")

    def test_unknown_job_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown job_id"):
            general.cancel_job(JOB)
        with self.assertRaisesRegex(ValueError, "32-character"):
            general.cancel_job("not-a-job")


class FakeStop:
    """Stands in for threading.Event.wait so the watcher loop is deterministic."""

    def __init__(self, iterations: int):
        self.iterations = iterations
        self.calls = 0

    def wait(self, _timeout):
        self.calls += 1
        return self.calls > self.iterations


class StallWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bug131_stall_")
        self.directory = Path(self.temporary.name)
        (self.directory / "worker.log").write_bytes(b"")
        self.manifest = {"job_id": JOB, "status": "running", "worker_started": True}

    def tearDown(self):
        self.temporary.cleanup()

    def test_budget_defaults_to_600_and_accepts_an_override(self):
        with patch.object(bridge, "config", return_value={}):
            self.assertEqual(general.stall_watchdog_seconds(), 600)
        with patch.object(bridge, "config", return_value={"generic_stall_seconds": 0}):
            self.assertEqual(general.stall_watchdog_seconds(), 0)
        with patch.object(bridge, "config", return_value={"generic_stall_seconds": 45}):
            self.assertEqual(general.stall_watchdog_seconds(), 45)
        with patch.object(bridge, "config", return_value={"generic_stall_seconds": "x"}):
            self.assertEqual(general.stall_watchdog_seconds(), 600)

    def test_missing_pid_reports_without_running_a_command(self):
        result = general._terminate_process_tree(None)
        self.assertFalse(result["attempted"])
        self.assertEqual(result["reason"], "no_runner_pid")

    def test_silent_worker_is_killed_through_its_owner_record(self):
        _write(self.directory / "native_owner.json", {"pid": 9876, "created": 5})
        clock = {"now": 0.0}

        def monotonic():
            clock["now"] += 1.0
            return clock["now"]

        state: dict = {}
        with (
            patch.object(general, "stall_watchdog_seconds", return_value=2),
            patch.object(general.time, "monotonic", side_effect=monotonic),
            patch.object(
                general, "_terminate_process_tree", return_value={"returncode": 0, "pid": 9876}
            ) as kill,
        ):
            general._watch_worker_log(self.directory, FakeStop(5), state)
        self.assertTrue(state["stalled"])
        self.assertEqual(state["budget_seconds"], 2)
        self.assertEqual(state["source"], "generic_stall_seconds")
        self.assertGreaterEqual(state["silent_seconds"], 2)
        kill.assert_called_once_with(9876)

    def test_worker_without_an_owner_record_is_not_killed(self):
        clock = {"now": 0.0}

        def monotonic():
            clock["now"] += 1.0
            return clock["now"]

        state: dict = {}
        with (
            patch.object(general, "stall_watchdog_seconds", return_value=2),
            patch.object(general.time, "monotonic", side_effect=monotonic),
        ):
            general._watch_worker_log(self.directory, FakeStop(5), state)
        self.assertTrue(state["stalled"])
        self.assertFalse(state["termination"]["attempted"])

    def test_finished_worker_returns_its_code(self):
        with (
            patch.object(
                general.subprocess,
                "run",
                return_value=type("Done", (), {"returncode": 0})(),
            ),
            patch.object(bridge, "native_environment", return_value={}),
            patch.object(general, "stall_watchdog_seconds", return_value=600),
        ):
            code = general._run_worker_with_watchdog(
                Path("worker.exe"), self.directory, {"timeout_seconds": 10}, self.manifest, None
            )
        self.assertEqual(code, 0)
        self.assertNotIn("stall_watchdog", self.manifest)

    def test_stalled_watchdog_raises_and_records_evidence(self):
        def stalled(_directory, _stop, state):
            state.update(stalled=True, budget_seconds=2, message="silent")

        with (
            patch.object(
                general.subprocess, "run", return_value=type("Done", (), {"returncode": 0})()
            ),
            patch.object(bridge, "native_environment", return_value={}),
            patch.object(general, "stall_watchdog_seconds", return_value=2),
            patch.object(general, "_watch_worker_log", side_effect=stalled),
        ):
            with self.assertRaises(general.WorkerStalled):
                general._run_worker_with_watchdog(
                    Path("worker.exe"),
                    self.directory,
                    {"timeout_seconds": 10},
                    self.manifest,
                    None,
                )
        self.assertEqual(self.manifest["stall_watchdog"]["budget_seconds"], 2)

    def test_the_runner_uses_the_watchdog(self):
        source = Path(general.__file__).read_text(encoding="utf-8")
        self.assertIn("returncode = _run_worker_with_watchdog(", source)
        self.assertIn("except WorkerStalled as exc:", source)


def snapshot(model: dict, live: dict | None = None) -> dict:
    return {
        "model": model,
        "owners": [{"stopped": True}],
        "baseline": {},
        "candidate": {},
        "live": live,
    }


class NewAssemblyExitTests(unittest.TestCase):
    def test_new_assembly_can_abandon_and_acknowledge(self):
        model = {
            "model_id": MODEL,
            "model_type": "assembly",
            "revision": 0,
            "part_file": None,
            "status": "unknown_outcome",
            "pending_job": JOB,
        }
        with patch.object(rec, "_pending_job_status", return_value="unknown_outcome"):
            actions = rec._actions(snapshot(model), None)
        self.assertTrue(actions["abandon_new"]["available"], actions["abandon_new"])
        self.assertTrue(actions["ack_failure"]["available"], actions["ack_failure"])

    def test_empty_owner_list_does_not_block_an_uncommitted_model(self):
        # BUG-131 live cancel: cancelling before the worker started releases
        # pending_job, so the recovery snapshot can have no job evidence at all.
        model = {
            "model_id": MODEL,
            "model_type": "part",
            "revision": 0,
            "part_file": None,
            "status": "failed",
            "pending_job": None,
        }
        actions = rec._actions(
            {
                "model": model,
                "owners": [],
                "baseline": {},
                "candidate": {},
                "live": None,
            },
            None,
        )
        self.assertTrue(actions["abandon_new"]["available"], actions["abandon_new"])
        self.assertTrue(actions["ack_failure"]["available"], actions["ack_failure"])

    def test_running_pending_job_still_blocks_the_new_assembly_exit(self):
        model = {
            "model_id": MODEL,
            "model_type": "assembly",
            "revision": 0,
            "part_file": None,
            "status": "unknown_outcome",
            "pending_job": JOB,
        }
        with patch.object(rec, "_pending_job_status", return_value="running"):
            actions = rec._actions(snapshot(model), None)
        self.assertFalse(actions["ack_failure"]["available"])
        self.assertIn("pending or recovery job", actions["ack_failure"]["reason"])

    def test_saved_assembly_keeps_the_component_limit(self):
        model = {
            "model_id": MODEL,
            "model_type": "assembly",
            "revision": 3,
            "part_file": "C:\\fixture\\asm.asm.3",
            "status": "failed",
            "pending_job": None,
        }
        actions = rec._actions(snapshot(model), None)
        self.assertFalse(actions["abandon_new"]["available"])
        self.assertIn("Assembly/drawing", actions["abandon_new"]["reason"])
        self.assertFalse(actions["restore_baseline"]["available"])

    def test_part_with_a_terminal_pending_job_is_unchanged(self):
        model = {
            "model_id": MODEL,
            "model_type": "part",
            "revision": 0,
            "part_file": None,
            "status": "unknown_outcome",
            "pending_job": JOB,
        }
        with patch.object(rec, "_pending_job_status", return_value="unknown_outcome"):
            actions = rec._actions(snapshot(model), None)
        self.assertFalse(actions["ack_failure"]["available"])
        self.assertIn("pending or recovery job", actions["ack_failure"]["reason"])


if __name__ == "__main__":
    unittest.main()
