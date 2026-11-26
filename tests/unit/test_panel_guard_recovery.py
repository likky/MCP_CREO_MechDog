"""BUG-120/D4.4: the panel guard has one reachable, evidence-bound exit.

A guard that nothing can lift turns one unproven panel into a permanently dead
Toolkit channel. These tests pin the exit that does exist — a human confirmation
through `creo_reconcile_model` with the current reconcile evidence token — and the
things it must not become: an automatic release after a cancel, a release for a
different model's guard, a release while the panel job is still running, and a
release that also "resolves" the model's own unknown outcome.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import bridge
from creo_mechdog import generic_bridge as general
from creo_mechdog import panel_session_guard
from creo_mechdog import reconciliation as rec
from tests.unit import test_reconciliation as rec_tests

PROFILE = "creo10-bbl-1"
NONCE = "e" * 32


class PanelGuardRecovery(unittest.TestCase):
    # The reconciliation fixture builds one unknown_outcome model with a real job
    # record; these tests only add the session guard on top of it.
    setUp = rec_tests.Reconciliation.setUp
    save_model = rec_tests.Reconciliation.save_model

    def reserve(self, *, model_id=None, job_id=None):
        return panel_session_guard.reserve(
            job_id or self.original,
            nonce=NONCE,
            profile_id=PROFILE,
            mode="candidate",
            model_id=model_id or self.mid,
            root=self.root,
        )

    def inspect(self):
        return rec.inspect(self.mid)

    def confirm(self, *, key="panel_confirmed", confirm=True, revisions=None):
        evidence = self.inspect()
        return rec.apply(
            self.mid,
            "confirm_panel_closed",
            revisions if revisions is not None else evidence["revision"],
            evidence["pending_job"],
            evidence["evidence_token"],
            key,
            confirm_panel_closed=confirm,
        )

    def test_inspect_reports_the_guard_and_the_action_that_releases_it(self):
        self.reserve()
        evidence = self.inspect()
        guard = evidence["panel_session_guard"]
        self.assertEqual(guard["state"], "active")
        self.assertEqual(guard["job_id"], self.original)
        self.assertEqual(guard["profile_id"], PROFILE)
        self.assertTrue(guard["blocks_toolkit"])
        self.assertIn("confirm_panel_closed", guard["release"])
        self.assertTrue(evidence["actions"]["confirm_panel_closed"]["available"])

    def test_without_a_guard_the_action_names_why_there_is_nothing_to_do(self):
        evidence = self.inspect()
        self.assertIsNone(evidence["panel_session_guard"])
        state = evidence["actions"]["confirm_panel_closed"]
        self.assertFalse(state["available"])
        self.assertIn("No resident panel guard", state["reason"])

    def test_a_confirmation_without_the_flag_is_refused(self):
        self.reserve()
        with self.assertRaisesRegex(ValueError, "confirm_panel_closed=true"):
            self.confirm(confirm=False)
        self.assertEqual(panel_session_guard.inspect(self.root)["status"], "active")

    def test_a_preopen_refusal_retires_the_guard_with_the_matching_nonce(self):
        self.reserve()
        result = {
            "success": False,
            "operations": [
                {
                    "op": "surface_loft",
                    "creation_route": "resident_panel",
                    "panel_preopen": {
                        "no_dialog_opened": True,
                        "macro_submitted": False,
                        "phase": "reading_references",
                        "job_id": self.original,
                        "nonce": NONCE,
                    },
                }
            ],
        }
        general._retire_panel_guard_after_result(self.original, result)
        self.assertIsNone(panel_session_guard.inspect(self.root))

    def test_a_preopen_refusal_with_another_nonce_leaves_the_guard(self):
        self.reserve()
        result = {
            "success": False,
            "operations": [
                {
                    "op": "surface_loft",
                    "creation_route": "resident_panel",
                    "panel_preopen": {
                        "no_dialog_opened": True,
                        "macro_submitted": False,
                        "job_id": self.original,
                        "nonce": "f" * 32,
                    },
                }
            ],
        }
        general._retire_panel_guard_after_result(self.original, result)
        self.assertEqual(panel_session_guard.inspect(self.root)["status"], "active")

    def test_a_confirmation_retires_the_guard_and_leaves_the_model_alone(self):
        self.reserve()
        before = (general.model_path(self.mid) / "model.json").read_bytes()
        result = self.confirm()
        self.assertEqual(result["action"], "confirm_panel_closed")
        self.assertEqual(result["panel_session_guard"]["state"], "retired")
        self.assertEqual(result["panel_session_guard"]["job_id"], self.original)
        self.assertTrue(result["model_unchanged"])
        self.assertIsNone(panel_session_guard.inspect(self.root))
        self.assertEqual(before, (general.model_path(self.mid) / "model.json").read_bytes())
        self.assertEqual(result["status"], "unknown_outcome")
        self.assertEqual(result["pending_job"], self.original)

    def test_the_retired_record_keeps_who_confirmed_and_which_guard(self):
        self.reserve()
        self.confirm()
        record = json.loads(
            (self.root / panel_session_guard.GUARD_FILE).read_text(encoding="utf-8")
        )
        self.assertEqual(record["state"], "retired")
        self.assertEqual(record["job_id"], self.original)
        self.assertEqual(record["nonce"], NONCE)
        self.assertEqual(record["profile_id"], PROFILE)
        evidence = record["retire_evidence"]
        self.assertTrue(evidence["operator_confirmed"])
        self.assertTrue(evidence["ui_closed_confirmed"])
        self.assertEqual(evidence["confirmed_via"], "creo_reconcile_model.confirm_panel_closed")
        self.assertEqual(evidence["guard_nonce"], NONCE)

    def test_a_second_confirmation_refuses_instead_of_inventing_work(self):
        self.reserve()
        self.confirm()
        with self.assertRaises(ValueError) as caught:
            self.confirm(key="panel_confirmed_again")
        self.assertIn("No resident panel guard", str(caught.exception))

    def test_another_models_guard_is_not_released_from_here(self):
        self.reserve(model_id="f" * 32)
        evidence = self.inspect()
        state = evidence["actions"]["confirm_panel_closed"]
        self.assertFalse(state["available"])
        self.assertIn("belongs to model", state["reason"])
        with self.assertRaisesRegex(ValueError, "belongs to model"):
            self.confirm()
        self.assertEqual(panel_session_guard.inspect(self.root)["status"], "active")

    def test_a_panel_job_that_is_still_running_cannot_be_confirmed_shut(self):
        self.reserve()
        bridge.write_json(
            bridge.job_path(self.original) / "job.json",
            {
                "job_id": self.original,
                "model_id": self.mid,
                "kind": "generic",
                "status": "running",
                "created_at": bridge.now(),
            },
        )
        state = self.inspect()["actions"]["confirm_panel_closed"]
        self.assertFalse(state["available"])
        self.assertIn("has not reached a terminal status", state["reason"])
        with self.assertRaisesRegex(ValueError, "has not reached a terminal status"):
            self.confirm()

    def test_an_unreadable_guard_is_never_released_by_a_tool(self):
        self.reserve()
        (self.root / panel_session_guard.GUARD_FILE).write_text("{broken", encoding="utf-8")
        evidence = self.inspect()
        self.assertEqual(evidence["panel_session_guard"]["state"], "unknown")
        state = evidence["actions"]["confirm_panel_closed"]
        self.assertFalse(state["available"])
        self.assertIn("cannot be read", state["reason"])
        with self.assertRaisesRegex(ValueError, "cannot be read"):
            self.confirm()
        self.assertEqual(
            (self.root / panel_session_guard.GUARD_FILE).read_text(encoding="utf-8"), "{broken"
        )

    def test_an_expired_token_cannot_confirm(self):
        self.reserve()
        evidence = self.inspect()
        with patch.object(rec.time, "time", return_value=rec.time.time() + rec.TOKEN_SECONDS + 1):
            with self.assertRaisesRegex(ValueError, "missing or expired"):
                rec.apply(
                    self.mid,
                    "confirm_panel_closed",
                    evidence["revision"],
                    evidence["pending_job"],
                    evidence["evidence_token"],
                    "expired_token_case",
                    confirm_panel_closed=True,
                )
        self.assertEqual(panel_session_guard.inspect(self.root)["status"], "active")

    def test_a_stale_revision_is_refused_before_the_guard_is_touched(self):
        self.reserve()
        with self.assertRaisesRegex(ValueError, "Stale expected_revision"):
            self.confirm(revisions=99)
        self.assertEqual(panel_session_guard.inspect(self.root)["status"], "active")

    def test_other_recovery_actions_stay_blocked_while_the_guard_holds(self):
        self.reserve()
        evidence = self.inspect()
        with patch.object(bridge.subprocess, "Popen") as popen:
            with self.assertRaises(panel_session_guard.PanelSessionLocked):
                rec.apply(
                    self.mid,
                    "restore_baseline",
                    evidence["revision"],
                    evidence["pending_job"],
                    evidence["evidence_token"],
                    "blocked_by_guard",
                )
            popen.assert_not_called()
        self.assertEqual(panel_session_guard.inspect(self.root)["status"], "active")

    def test_the_channel_works_again_right_after_the_confirmation(self):
        self.reserve()
        self.confirm()
        with bridge.toolkit_lock(operation="session_status", job_id="f" * 32):
            pass

    def test_a_cancelled_panel_job_does_not_release_its_guard(self):
        self.reserve()
        bridge.write_json(
            bridge.job_path(self.original) / "job.json",
            {
                "job_id": self.original,
                "model_id": self.mid,
                "kind": "generic",
                "status": "cancelled",
                "created_at": bridge.now(),
            },
        )
        self.assertEqual(panel_session_guard.inspect(self.root)["status"], "active")
        self.assertTrue(self.inspect()["actions"]["confirm_panel_closed"]["available"])

    def test_the_published_tool_carries_the_action_and_the_confirmation_flag(self):
        import asyncio

        import server

        tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
        properties = tools["creo_reconcile_model"].input_schema["properties"]
        self.assertIn("confirm_panel_closed", properties)
        actions = properties["action"]["anyOf"][0]["enum"]
        self.assertIn("confirm_panel_closed", actions)

    def test_the_tool_itself_retires_the_guard(self):
        import asyncio

        import server

        self.reserve()
        evidence = self.inspect()
        result = asyncio.run(
            server.creo_reconcile_model(
                model_id=self.mid,
                mode="apply",
                action="confirm_panel_closed",
                expected_revision=evidence["revision"],
                expected_pending_job_id=evidence["pending_job"],
                evidence_token=evidence["evidence_token"],
                idempotency_key="mcp_panel_confirmed",
                confirm_panel_closed=True,
            )
        )
        self.assertEqual(result["panel_session_guard"]["state"], "retired")
        self.assertIsNone(panel_session_guard.inspect(self.root))


if __name__ == "__main__":
    unittest.main()
