"""BUG-120/D4.4: a panel that may still be open holds the whole Creo session.

The guard is written before the worker that may open UI, survives a stdio restart
because it is a file, and is released only by positive evidence. Dead pids,
expired claims, a cancelled job and ordinary recovery actions never release it.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bridge
import generic_bridge as general
from creo_mechdog import panel_session_guard
from tests.unit import test_toolkit_channel as channel_tests


def panel_op():
    return {
        "op": "surface_loft",
        "label": "panel_surface",
        "sections": ["panel_a", "panel_b"],
        "creation_route": "resident_panel",
    }


class GuardRecord(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        self.addCleanup(self._directory.cleanup)

    def reserve(self, job_id="job_a", **overrides):
        values = {
            "nonce": "nonce_a",
            "profile_id": "creo10-bbl-1",
            "mode": "candidate",
            "model_id": "model_1",
        }
        values.update(overrides)
        return panel_session_guard.reserve(job_id, root=self.root, **values)

    def test_no_guard_means_the_channel_is_free(self):
        self.assertIsNone(panel_session_guard.inspect(self.root))
        panel_session_guard.require_clear(operation="session_status", root=self.root)

    def test_a_reserved_guard_blocks_another_job(self):
        self.reserve()
        with self.assertRaises(panel_session_guard.PanelSessionLocked) as caught:
            panel_session_guard.require_clear(job_id="job_b", operation="submit", root=self.root)
        text = str(caught.exception)
        self.assertIn("job_a", text)
        self.assertIn("creo10-bbl-1", text)
        self.assertIn("No Toolkit call was made", text)
        self.assertEqual(caught.exception.holder.get("job_id"), "job_a")

    def test_the_owning_job_may_use_the_channel(self):
        self.reserve()
        panel_session_guard.require_clear(job_id="job_a", operation="execute_plan", root=self.root)

    def test_local_work_that_never_talks_to_creo_is_exempt(self):
        self.reserve()
        panel_session_guard.require_clear(operation="build_native", root=self.root)

    def test_a_second_reserve_for_the_same_job_is_idempotent(self):
        first = self.reserve()
        second = self.reserve()
        self.assertEqual(first["created_at"], second["created_at"])
        self.assertEqual(second["nonce"], "nonce_a")

    def test_a_second_job_cannot_reserve_beside_the_first(self):
        self.reserve()
        with self.assertRaises(panel_session_guard.PanelSessionLocked):
            self.reserve(job_id="job_b", nonce="nonce_b")

    def test_a_record_is_written_atomically(self):
        self.reserve()
        self.assertFalse((self.root / "panel_session_guard.tmp").exists())
        record = json.loads(
            (self.root / panel_session_guard.GUARD_FILE).read_text(encoding="utf-8")
        )
        self.assertEqual(record["state"], "active")
        self.assertEqual(record["job_id"], "job_a")

    def test_an_unreadable_guard_blocks_instead_of_reading_as_absent(self):
        (self.root / panel_session_guard.GUARD_FILE).write_text("{not json", encoding="utf-8")
        guard = panel_session_guard.inspect(self.root)
        self.assertEqual(guard["status"], "unknown")
        with self.assertRaisesRegex(panel_session_guard.PanelSessionLocked, "cannot be read"):
            panel_session_guard.require_clear(job_id="job_a", operation="submit", root=self.root)
        with self.assertRaises(panel_session_guard.PanelSessionLocked):
            self.reserve()

    def test_a_partial_record_is_unknown_rather_than_partly_trusted(self):
        (self.root / panel_session_guard.GUARD_FILE).write_text(
            json.dumps({"job_id": "job_a"}), encoding="utf-8"
        )
        guard = panel_session_guard.inspect(self.root)
        self.assertEqual(guard["status"], "unknown")
        self.assertIn("nonce", guard["reason"])

    def test_a_dead_pid_does_not_release_the_guard(self):
        self.reserve()
        record = json.loads(
            (self.root / panel_session_guard.GUARD_FILE).read_text(encoding="utf-8")
        )
        record["pid"] = 999999
        (self.root / panel_session_guard.GUARD_FILE).write_text(
            json.dumps(record), encoding="utf-8"
        )
        with self.assertRaises(panel_session_guard.PanelSessionLocked):
            panel_session_guard.require_clear(job_id="job_b", operation="submit", root=self.root)


class GuardRetirement(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        self.addCleanup(self._directory.cleanup)
        panel_session_guard.reserve(
            "job_a",
            nonce="nonce_a",
            profile_id="creo10-bbl-1",
            mode="candidate",
            model_id="model_1",
            root=self.root,
        )

    def test_retiring_without_closing_evidence_is_refused(self):
        for evidence in ({}, {"ui_closed_confirmed": False}, {"pid_dead": True}, None):
            with self.subTest(evidence=evidence):
                with self.assertRaisesRegex(ValueError, "confirmed evidence"):
                    panel_session_guard.retire(
                        "job_a", reason="cancel", evidence=evidence, root=self.root
                    )
        self.assertIsNotNone(panel_session_guard.inspect(self.root))

    def test_only_the_holder_retires_the_guard(self):
        with self.assertRaisesRegex(ValueError, "belongs to job job_a"):
            panel_session_guard.retire(
                "job_b",
                reason="cancel",
                evidence={"ui_closed_confirmed": True},
                root=self.root,
            )

    def test_confirmed_exit_retires_the_guard(self):
        record = panel_session_guard.retire(
            "job_a",
            reason="native panel exit observed",
            evidence={"ui_closed_confirmed": True, "source": "native_exit_observation"},
            root=self.root,
        )
        self.assertEqual(record["state"], "retired")
        self.assertIsNone(panel_session_guard.inspect(self.root))
        panel_session_guard.require_clear(job_id="job_b", operation="submit", root=self.root)

    def test_each_positive_evidence_kind_is_accepted(self):
        for key in panel_session_guard.CLOSING_EVIDENCE:
            with self.subTest(key=key):
                panel_session_guard.reserve(
                    "job_a",
                    nonce="nonce_a",
                    profile_id="creo10-bbl-1",
                    mode="candidate",
                    model_id="model_1",
                    root=self.root,
                )
                panel_session_guard.retire(
                    "job_a", reason="recovery", evidence={key: True}, root=self.root
                )
                self.assertIsNone(panel_session_guard.inspect(self.root))

    def test_a_retired_record_still_names_its_evidence(self):
        panel_session_guard.retire(
            "job_a",
            reason="recovery",
            evidence={"session_ended_confirmed": True},
            root=self.root,
        )
        record = json.loads(
            (self.root / panel_session_guard.GUARD_FILE).read_text(encoding="utf-8")
        )
        self.assertEqual(record["state"], "retired")
        self.assertEqual(record["retire_evidence"], {"session_ended_confirmed": True})


class ToolkitEntriesAreGated(unittest.TestCase):
    setUp = channel_tests.ToolkitChannel.setUp

    def test_every_toolkit_entry_is_refused_for_another_job(self):
        panel_session_guard.reserve(
            "job_a",
            nonce="nonce_a",
            profile_id="creo10-bbl-1",
            mode="candidate",
            model_id="model_1",
            root=self.root,
        )
        for operation in ("submit", "session_status", "callback_status", "execute_plan"):
            with self.subTest(operation=operation):
                with self.assertRaises(panel_session_guard.PanelSessionLocked):
                    with bridge.toolkit_lock(operation=operation, job_id="job_b"):
                        pass
        self.assertFalse((self.root / "toolkit.lock").exists())

    def test_the_owner_and_local_work_still_get_the_channel(self):
        panel_session_guard.reserve(
            "job_a",
            nonce="nonce_a",
            profile_id="creo10-bbl-1",
            mode="candidate",
            model_id="model_1",
            root=self.root,
        )
        with bridge.toolkit_lock(operation="execute_plan", job_id="job_a"):
            pass
        with bridge.toolkit_lock(operation="build_native"):
            pass

    def test_a_panel_submission_reserves_the_guard_before_the_runner(self):
        admission = {"profile_id": "creo10-bbl-1", "mode": "candidate"}
        with (
            patch.object(general, "require_panel_route", return_value=admission),
            patch.object(bridge.subprocess, "Popen") as popen,
        ):
            accepted = general.submit([panel_op()], model_name="panel_model")
            popen.assert_called_once()
        guard = panel_session_guard.inspect(self.root)
        self.assertEqual(guard["job_id"], accepted["job_id"])
        self.assertEqual(guard["profile_id"], "creo10-bbl-1")
        self.assertEqual(guard["mode"], "candidate")
        request = json.loads(
            (self.root / "jobs" / accepted["job_id"] / "request.json").read_text(encoding="utf-8")
        )
        self.assertIn("panel_nonce", request)
        self.assertEqual(request["panel_admission"], admission)

    def test_a_panel_submission_beside_an_open_panel_is_refused_before_the_runner(self):
        panel_session_guard.reserve(
            "job_a",
            nonce="nonce_a",
            profile_id="creo10-bbl-1",
            mode="candidate",
            model_id="model_1",
            root=self.root,
        )
        with (
            patch.object(
                general,
                "require_panel_route",
                return_value={"profile_id": "p", "mode": "candidate"},
            ),
            patch.object(bridge.subprocess, "Popen") as popen,
        ):
            with self.assertRaises(panel_session_guard.PanelSessionLocked):
                general.submit([panel_op()], model_name="panel_model")
            popen.assert_not_called()

    def test_an_ordinary_submission_is_unaffected_without_a_guard(self):
        with patch.object(bridge.subprocess, "Popen") as popen:
            general.submit([], model_name="plain_model")
            popen.assert_called_once()
        self.assertIsNone(panel_session_guard.inspect(self.root))


if __name__ == "__main__":
    unittest.main()
