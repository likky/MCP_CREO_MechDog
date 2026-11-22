"""BUG-146: a recovery intent that provably never started must be diagnosable.

0.34.0 feedback: a recovery job stayed ``queued``/``intent_persisted`` and every
action reported "cannot be proven stopped", although its disk baseline was
healthy. The proof below never weakens the ordinary identity rules: a recorded
runner or worker, a native file, a live launcher or an unreadable identity keeps
the intent protected.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import bridge
import generic_bridge as general
from creo_mechdog import reconciliation as rec
from tests.unit import test_reconciliation as fixtures

DEAD_PID = 2147483647
STALLED = "c" * 32


class StalledIntent(unittest.TestCase):
    save_model = fixtures.Reconciliation.save_model

    def setUp(self):
        fixtures.Reconciliation.setUp(self)
        self.directory = bridge.job_path(STALLED)
        self.directory.mkdir(parents=True)
        self.created = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
        self.manifest = {
            "job_id": STALLED,
            "recovery_id": STALLED,
            "kind": "reconciliation",
            "model_id": self.mid,
            "status": "queued",
            "action": "restore_baseline",
            "created_at": self.created,
            "stage": "intent_persisted",
            "worker_started": False,
            "revision": self.model["revision"],
            "launched_by": {"pid": DEAD_PID, "created": 5},
        }
        self.reserve()

    def reserve(self, **overrides):
        self.manifest.update(overrides)
        bridge.write_json(self.directory / "job.json", self.manifest, durable=True)
        bridge.write_json(
            self.directory / "request.json",
            {"model": self.model, "action": self.manifest["action"]},
        )
        self.model["recovery_pending"] = STALLED
        self.save_model()

    def inspect(self):
        return rec.inspect(self.mid)

    def test_proven_stalled_intent_names_the_reason_and_unblocks_recovery(self):
        value = self.inspect()
        stalled = value["stalled_recovery"]
        self.assertTrue(stalled["proven"])
        self.assertEqual(stalled["basis"], "launcher_exited")
        self.assertEqual(stalled["grace_seconds"], rec.STALLED_INTENT_SECONDS)
        self.assertEqual(value["recovery_wait"]["state"], "stalled_intent_proven")
        self.assertTrue(value["actions"]["restore_baseline"]["available"])
        self.assertTrue(value["actions"]["abandon_stalled_recovery"]["available"])
        self.assertTrue(value["owners"][0]["stopped"])

    def test_a_live_launcher_keeps_the_intent_protected(self):
        mine = rec.process_identity(os.getpid())
        self.reserve(launched_by=mine)
        value = self.inspect()
        self.assertFalse(value["stalled_recovery"]["proven"])
        self.assertEqual(value["stalled_recovery"]["reason"], "launcher_still_alive")
        self.assertEqual(value["recovery_wait"]["state"], "protected")
        self.assertFalse(value["actions"]["restore_baseline"]["available"])
        self.assertFalse(value["actions"]["abandon_stalled_recovery"]["available"])

    def test_a_reused_pid_counts_as_exited(self):
        with patch.object(
            rec, "process_identity", return_value={"pid": DEAD_PID, "created": 999, "alive": True}
        ):
            value = self.inspect()
        self.assertTrue(value["stalled_recovery"]["proven"])
        self.assertEqual(value["stalled_recovery"]["basis"], "launcher_pid_reused")

    def test_a_runner_that_died_while_waiting_for_the_channel_is_proven(self):
        # Real 2026-11-21 case: the runner took the reservation, advanced to
        # waiting_for_channel, then died with the client; no worker, no native
        # file. That state must be as closable as one that never wrote a runner.
        self.reserve(
            stage="waiting_for_channel",
            status="waiting_for_channel",
            runner_identity={"pid": DEAD_PID, "created": 5},
        )
        value = self.inspect()
        stalled = value["stalled_recovery"]
        self.assertTrue(stalled["proven"])
        self.assertEqual(stalled["basis"], "runner_exited")
        self.assertEqual(stalled["stage"], "waiting_for_channel")
        self.assertEqual(value["recovery_wait"]["state"], "stalled_intent_proven")
        self.assertIn("runner exited", value["recovery_wait"]["reason"])
        self.assertTrue(value["actions"]["abandon_stalled_recovery"]["available"])

    def test_a_live_runner_keeps_the_intent_protected(self):
        self.reserve(stage="waiting_for_channel", runner_identity=rec.process_identity(os.getpid()))
        value = self.inspect()
        self.assertFalse(value["stalled_recovery"]["proven"])
        self.assertEqual(value["stalled_recovery"]["reason"], "runner_still_alive")
        self.assertFalse(value["actions"]["abandon_stalled_recovery"]["available"])
        self.assertIn("runner process is still alive", value["recovery_wait"]["next_step"])

    def test_unreadable_runner_identity_is_never_assumed_stopped(self):
        self.reserve(runner_identity={"pid": DEAD_PID, "created": 5})
        with patch.object(rec, "process_identity", return_value={"pid": DEAD_PID, "alive": None}):
            value = self.inspect()
        self.assertFalse(value["stalled_recovery"]["proven"])
        self.assertEqual(value["stalled_recovery"]["reason"], "runner_identity_unreadable")

    def test_a_stage_after_the_worker_is_never_called_stalled(self):
        self.reserve(stage="executing_feature_plan")
        value = self.inspect()
        self.assertFalse(value["stalled_recovery"]["proven"])
        self.assertEqual(value["stalled_recovery"]["reason"], "stage_advanced")
        self.assertIn("poll creo_get_job", value["recovery_wait"]["next_step"])

    def test_unreadable_launcher_identity_is_never_assumed_stopped(self):
        with patch.object(rec, "process_identity", return_value={"pid": DEAD_PID, "alive": None}):
            value = self.inspect()
        self.assertFalse(value["stalled_recovery"]["proven"])
        self.assertEqual(value["stalled_recovery"]["reason"], "launcher_identity_unreadable")
        self.assertFalse(value["actions"]["restore_baseline"]["available"])

    def test_native_evidence_blocks_the_stalled_proof(self):
        (self.directory / "native_checkpoint.json").write_text("{}", encoding="utf-8")
        value = self.inspect()
        self.assertFalse(value["stalled_recovery"]["proven"])
        self.assertEqual(value["stalled_recovery"]["reason"], "native_checkpoint.json_present")

    def test_a_started_worker_keeps_the_ordinary_identity_rules(self):
        self.reserve(worker_started=True)
        value = self.inspect()
        self.assertFalse(value["stalled_recovery"]["proven"])
        self.assertFalse(value["actions"]["abandon_stalled_recovery"]["available"])

    def test_an_intent_inside_the_startup_window_is_not_proven_stalled(self):
        self.reserve(created_at=datetime.now(timezone.utc).isoformat())
        value = self.inspect()
        self.assertFalse(value["stalled_recovery"]["proven"])
        self.assertEqual(value["stalled_recovery"]["reason"], "within_startup_window")

    def test_pre_feature_intents_without_a_launcher_stay_protected(self):
        self.reserve()
        manifest = dict(self.manifest)
        manifest.pop("launched_by")
        bridge.write_json(self.directory / "job.json", manifest, durable=True)
        value = self.inspect()
        self.assertFalse(value["stalled_recovery"]["proven"])
        self.assertEqual(value["stalled_recovery"]["reason"], "launcher_identity_unavailable")

    def test_apply_closes_only_the_stalled_intent(self):
        before = dict(self.model)
        value = self.inspect()
        result = rec.apply(
            self.mid,
            "abandon_stalled_recovery",
            before["revision"],
            before["pending_job"],
            value["evidence_token"],
            "stalled_fixture_key",
            confirm_stalled_recovery=True,
        )
        self.assertEqual(result["stage"], "intent_abandoned")
        self.assertTrue(result["recovery_pending_released"])
        self.assertTrue(result["model_unchanged"])
        after = bridge.read_json(general.model_path(self.mid) / "model.json")
        self.assertIsNone(after["recovery_pending"])
        self.assertEqual(after["revision"], before["revision"])
        self.assertEqual(after["pending_job"], before["pending_job"])
        self.assertEqual(after["part_file"], before["part_file"])
        self.assertEqual(after["status"], before["status"])
        job = bridge.read_json(self.directory / "job.json")
        self.assertEqual(job["status"], "failed")
        self.assertEqual(job["reason"], "recovery_intent_never_started")
        self.assertTrue(job["recovery_pending_released"])
        again = rec.apply(
            self.mid,
            "abandon_stalled_recovery",
            before["revision"],
            before["pending_job"],
            value["evidence_token"],
            "stalled_fixture_key",
            confirm_stalled_recovery=True,
        )
        self.assertEqual(again["stage"], "intent_abandoned")

    def test_apply_requires_the_explicit_confirmation(self):
        value = self.inspect()
        with self.assertRaises(ValueError):
            rec.apply(
                self.mid,
                "abandon_stalled_recovery",
                self.model["revision"],
                self.model["pending_job"],
                value["evidence_token"],
                "stalled_fixture_key",
            )
        self.assertEqual(
            bridge.read_json(general.model_path(self.mid) / "model.json")["recovery_pending"],
            STALLED,
        )

    def test_a_changed_revision_refuses_the_stalled_intent(self):
        value = self.inspect()
        with self.assertRaises(ValueError):
            rec.apply(
                self.mid,
                "abandon_stalled_recovery",
                self.model["revision"] + 1,
                self.model["pending_job"],
                value["evidence_token"],
                "stalled_fixture_key",
                confirm_stalled_recovery=True,
            )
        self.assertEqual(
            bridge.read_json(general.model_path(self.mid) / "model.json")["recovery_pending"],
            STALLED,
        )


if __name__ == "__main__":
    unittest.main()
