"""FEAT-072: session candidates and the process-local selection."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bridge
import creo_startup
import server
from creo_mechdog import session_candidates, session_choice


def _snapshot(processes):
    return {
        "available": True,
        "observed_at": "2026-11-21T13:00:00+00:00",
        "uncertain": False,
        "processes": processes,
    }


def _process(pid, matches=True, state="visible"):
    return {
        "pid": pid,
        "name": "parametric.exe",
        "created_at": "2026-11-21T12:00:00+00:00",
        "matches": matches,
        "windows": {"state": state, "visible_hung_window_observed": False},
    }


class Selection(unittest.TestCase):
    def tearDown(self):
        session_choice.clear_override()

    def test_override_wins_over_config_and_is_never_persisted(self):
        session_choice.set_override("session-a")
        value = session_choice.describe({"creo_session_id": "session-b"})
        self.assertEqual(value["source"], "runtime_override")
        self.assertTrue(value["override_active"])
        self.assertEqual(value["session_fingerprint"], session_choice.fingerprint("session-a"))
        self.assertEqual(value["scope"], "process")
        self.assertIn("config.json is unchanged", value["persistence"])
        self.assertNotIn("session-a", json.dumps(value))
        self.assertEqual(session_choice.selected({"creo_session_id": "session-b"}), "session-a")

    def test_clear_returns_to_the_configured_id(self):
        session_choice.set_override("session-a")
        session_choice.clear_override()
        value = session_choice.describe({"creo_session_id": "session-b"})
        self.assertEqual(value["source"], "config")
        self.assertFalse(value["override_active"])
        self.assertEqual(session_choice.selected({"creo_session_id": "session-b"}), "session-b")
        self.assertEqual(session_choice.describe({})["source"], "none")

    def test_invalid_ids_are_refused_before_any_state_changes(self):
        for value in ("", "   ", "a\nb", "a\0b", "x" * (session_choice.MAX_LENGTH + 1), 7):
            with self.subTest(value=value), self.assertRaises(session_choice.SelectionError):
                session_choice.set_override(value)
        self.assertIsNone(session_choice.override())

    def test_native_environment_carries_the_runtime_selection(self):
        with (
            patch.object(bridge, "config", return_value={"creo_root": "C:/Creo 10.0.0.0"}),
            patch.object(bridge, "resolve_license_environment", return_value=(None, None)),
        ):
            self.assertNotIn("MECHDOG_CREO_SESSION_ID", bridge.native_environment())
            session_choice.set_override("session-a")
            self.assertEqual(bridge.native_environment()["MECHDOG_CREO_SESSION_ID"], "session-a")

    def test_start_requires_an_explicit_retry_and_one_knob_only(self):
        startup = creo_startup.CreoStartup()
        with self.assertRaises(session_choice.SelectionError):
            startup.start(False, "session-a")
        with self.assertRaises(session_choice.SelectionError):
            startup.start(False, clear_session_id=True)
        with self.assertRaises(session_choice.SelectionError):
            startup.start(True, "session-a", clear_session_id=True)
        self.assertIsNone(session_choice.override())

    def test_settings_read_the_effective_selection(self):
        config = {
            "creo_root": "C:/Creo 10.0.0.0",
            "creo_session_id": "",
        }
        with patch.object(bridge, "config", return_value=config):
            self.assertFalse(creo_startup.Settings.load().selected)
            session_choice.set_override("session-a")
            self.assertTrue(creo_startup.Settings.load().selected)


class Candidates(unittest.TestCase):
    def test_two_processes_are_listed_as_unidentified(self):
        value = session_candidates.build(
            _snapshot([_process(11), _process(12, matches=False, state="hidden_only")]),
            session_choice.describe({}),
            {"available": True, "session_fingerprint": "abc"},
        )
        self.assertEqual(value["count"], 2)
        self.assertEqual(value["ambiguity"]["observed"], "multiple_processes")
        self.assertIsNone(value["ambiguity"]["proven_by_toolkit"])
        self.assertEqual(value["identification"]["process_to_session_id"], "unsupported")
        self.assertFalse(value["identification"]["window_titles_read"])
        self.assertTrue(all(not row["identified"] for row in value["candidates"]))
        self.assertTrue(all(row["session_id"] is None for row in value["candidates"]))
        self.assertEqual(value["candidates"][1]["window_state"], "hidden_only")
        self.assertIn("session_id=", value["next_step"])

    def test_a_recorded_fingerprint_does_not_pose_as_a_connect_id(self):
        selection = session_choice.describe({})
        selection["session_fingerprint"] = "abc"
        value = session_candidates.build(
            _snapshot([_process(11)]), selection, {"available": True, "session_fingerprint": "abc"}
        )
        self.assertTrue(value["identification"]["selected_fingerprint_matches_recorded"])
        recorded = value["identification"]["recorded_session_fingerprint"]
        self.assertEqual(recorded["session_fingerprint"], "abc")

    def test_unavailable_inventory_is_reported_not_guessed(self):
        value = session_candidates.build(
            {"available": False, "reason": "inventory_failed_OSError"}, session_choice.describe({})
        )
        self.assertFalse(value["available"])
        self.assertEqual(value["reason"], "inventory_failed_OSError")
        self.assertEqual(value["candidates"], [])
        self.assertEqual(value["ambiguity"]["observed"], "unknown")

    def test_recorded_fingerprint_reads_the_newest_job(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        root = Path(folder)
        for offset, (name, fingerprint) in enumerate((("older", "f" * 64), ("newer", "e" * 64))):
            directory = root / "jobs" / name
            directory.mkdir(parents=True)
            manifest = directory / "job.json"
            manifest.write_text(
                json.dumps({"job_id": name, "result": {"session_fingerprint": fingerprint}}),
                encoding="utf-8",
            )
            stamp = 1_700_000_000 + offset
            os.utime(manifest, (stamp, stamp))
        value = session_candidates.recorded_fingerprint(root)
        self.assertTrue(value["available"])
        self.assertEqual(value["session_fingerprint"], "e" * 64)

    def test_missing_job_history_is_not_an_error(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        value = session_candidates.recorded_fingerprint(Path(folder))
        self.assertFalse(value["available"])
        self.assertEqual(value["reason"], "no_job_history")


class ToolContract(unittest.IsolatedAsyncioTestCase):
    async def test_startup_tool_exposes_selection_without_a_restart(self):
        tools = {tool.name: tool for tool in await server.mcp.list_tools()}
        schema = tools["creo_startup_status"].input_schema["properties"]
        self.assertIn("session_id", schema)
        self.assertIn("clear_session_id", schema)
        with self.assertRaises(ValueError):
            await server.creo_startup_status(force_ready=True, session_id="session-a")

    async def test_reconcile_tool_exposes_the_stalled_intent_action(self):
        tools = {tool.name: tool for tool in await server.mcp.list_tools()}
        schema = tools["creo_reconcile_model"].input_schema["properties"]
        self.assertIn("abandon_stalled_recovery", json.dumps(schema["action"]))
        self.assertIn("confirm_stalled_recovery", schema)


if __name__ == "__main__":
    unittest.main()
