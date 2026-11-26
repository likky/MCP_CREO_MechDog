"""BUG-120/D4.3: a panel wait may be silent, but only within its own bounded window.

The decision is tested with a fake clock: a trusted phase may cross the ordinary
stall budget, a repeated or foreign marker never extends anything, the phase window
is measured from the watcher's first sight of the phase, and the job budget is never
moved. One integration test drives the real watchdog with a marker file and a
patched poll interval.
"""

from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from creo_mechdog import generic_bridge as general
from creo_mechdog import panel_wait

NONCE = "d" * 32
PROFILE = "creo10-bbl-1"


def marker(**overrides):
    record = {
        "job_id": "job_a",
        "nonce": NONCE,
        "profile_id": PROFILE,
        "seq": 1,
        "phase": "panel_done_wait",
        "at_epoch_ms": 1700000000000,
    }
    record.update(overrides)
    return record


def tick(state, record, now, *, stall=600, phase=300, deadline=None):
    return panel_wait.tick(
        state,
        record,
        now,
        stall_budget=stall,
        phase_budget=phase,
        job_deadline_at=deadline,
    )


class MarkerParsing(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        self.addCleanup(self._directory.cleanup)

    def write(self, payload):
        path = self.root / panel_wait.WAIT_FILE
        path.write_text(
            payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8"
        )
        return path

    def test_a_complete_marker_is_read(self):
        record = panel_wait.read_marker(self.write(marker()))
        self.assertEqual(record["phase"], "panel_done_wait")

    def test_incomplete_or_wrongly_typed_markers_are_ignored(self):
        payloads = [
            "{not json",
            "[]",
            json.dumps({key: value for key, value in marker().items() if key != "nonce"}),
            json.dumps(marker(seq="3")),
            json.dumps(marker(seq=-1)),
            json.dumps(marker(profile_id="")),
            json.dumps(marker(at_epoch_ms=1.5)),
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                self.assertIsNone(panel_wait.read_marker(self.write(payload)))

    def test_a_missing_marker_is_none(self):
        self.assertIsNone(panel_wait.read_marker(self.root / panel_wait.WAIT_FILE))

    def test_identity_matching_is_strict(self):
        record = marker()
        self.assertTrue(panel_wait.matches(record, job_id="job_a", nonce=NONCE, profile_id=PROFILE))
        for overrides, kwargs in (
            ({"job_id": "job_b"}, {}),
            ({"nonce": "other"}, {}),
            ({"profile_id": "other"}, {}),
        ):
            with self.subTest(overrides=overrides):
                self.assertFalse(
                    panel_wait.matches(
                        marker(**overrides), job_id="job_a", nonce=NONCE, profile_id=PROFILE
                    )
                )


class WaitBudget(unittest.TestCase):
    def test_a_trusted_phase_outlives_the_stall_budget(self):
        state = {}
        start = 1000.0
        verdict = tick(state, marker(), start, stall=10, phase=300)
        self.assertEqual(verdict["action"], "continue")
        # 200 s of silence is far past the 10 s stall budget but inside the phase.
        verdict = tick(state, marker(seq=2), start + 200, stall=10, phase=300)
        self.assertEqual(verdict["action"], "continue")
        self.assertTrue(verdict["evidence"]["phase_limited"])

    def test_the_phase_deadline_is_measured_from_the_first_sight(self):
        state = {}
        start = 1000.0
        tick(state, marker(), start, phase=100)
        verdict = tick(state, marker(seq=2), start + 150, phase=100)
        self.assertEqual(verdict["action"], "terminate")
        self.assertEqual(verdict["reason"], "panel_phase_deadline")
        self.assertEqual(verdict["evidence"]["phase"], "panel_done_wait")

    def test_a_repeated_marker_does_not_restart_the_phase_window(self):
        state = {}
        start = 1000.0
        tick(state, marker(), start, phase=100)
        tick(state, marker(), start + 60, phase=100)
        verdict = tick(state, marker(), start + 130, phase=100)
        self.assertEqual(verdict["action"], "terminate")

    def test_an_old_sequence_number_is_not_progress(self):
        state = {}
        start = 1000.0
        tick(state, marker(seq=5), start, phase=100)
        verdict = tick(state, marker(seq=4), start + 50, phase=100)
        self.assertEqual(verdict["action"], "continue")
        self.assertFalse(verdict["evidence"]["progressed"])
        self.assertEqual(state["last_seq"], 5)

    def test_the_job_budget_caps_the_phase_window(self):
        state = {}
        start = 1000.0
        tick(state, marker(), start, phase=300, deadline=start + 40)
        verdict = tick(state, marker(seq=2), start + 45, phase=300, deadline=start + 40)
        self.assertEqual(verdict["action"], "terminate")
        self.assertEqual(verdict["reason"], "panel_job_deadline")

    def test_an_untrusted_phase_keeps_the_stall_contract(self):
        state = {"last_growth": 1000.0}
        verdict = tick(state, marker(phase="heartbeat"), 1015, stall=10, phase=300)
        self.assertEqual(verdict["action"], "terminate")
        self.assertEqual(verdict["reason"], "stall")

    def test_no_marker_keeps_the_stall_contract(self):
        state = {"last_growth": 1000.0}
        self.assertEqual(tick(state, None, 1005, stall=10)["action"], "continue")
        self.assertEqual(tick(state, None, 1011, stall=10)["reason"], "stall")

    def test_a_phase_that_ends_restarts_the_silence_window(self):
        state = {}
        start = 1000.0
        tick(state, marker(), start, phase=300)
        # Losing the trusted marker is not "silent since before the panel opened":
        # the ordinary window starts now, so the very first tick after the phase
        # cannot kill a worker that had been waiting legitimately.
        verdict = tick(state, marker(phase="heartbeat", seq=2), start + 400, stall=10, phase=300)
        self.assertEqual(verdict["action"], "continue")
        self.assertEqual(state["last_growth"], start + 400)
        verdict = tick(state, None, start + 415, stall=10, phase=300)
        self.assertEqual(verdict["reason"], "stall")

    def test_cycling_through_phases_shares_one_window(self):
        state = {}
        start = 1000.0
        tick(state, marker(phase="panel_open_wait", seq=1), start, phase=100)
        tick(state, marker(phase="panel_select_wait", seq=2), start + 60, phase=100)
        verdict = tick(state, marker(phase="panel_done_wait", seq=3), start + 130, phase=100)
        self.assertEqual(verdict["reason"], "panel_phase_deadline")
        self.assertEqual(verdict["evidence"]["phase"], "panel_done_wait")
        self.assertGreaterEqual(verdict["evidence"]["phase_seconds"], 130)


class WatchdogIntegration(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.directory = Path(self._directory.name)
        self.addCleanup(self._directory.cleanup)
        (self.directory / "worker.log").write_bytes(b"phase one")
        (self.directory / panel_wait.WAIT_FILE).write_text(json.dumps(marker()), encoding="utf-8")
        self.request = {
            "panel_admission": {"profile_id": PROFILE},
            "panel_guard": {"job_id": "job_a", "nonce": NONCE},
        }

    def run_watchdog(self, request, *, poll=0.01, stall=1, phase=60, wait=0.15):
        state: dict = {}
        stop = threading.Event()
        with (
            patch.object(general, "WORKER_POLL_SECONDS", poll),
            patch.object(general, "stall_watchdog_seconds", return_value=stall),
            patch.object(general, "panel_phase_seconds", return_value=phase),
            patch.object(general, "_terminate_process_tree", return_value={"attempted": False}),
        ):
            thread = threading.Thread(
                target=general._watch_worker_log,
                args=(self.directory, stop, state),
                kwargs={"request": request, "job_deadline_at": time.monotonic() + 60},
            )
            thread.start()
            time.sleep(wait)
            stop.set()
            thread.join(timeout=5)
        return state

    def test_a_matching_panel_marker_keeps_the_worker_alive(self):
        state = self.run_watchdog(self.request, stall=1, phase=60)
        self.assertFalse(state.get("stalled"))
        self.assertEqual(state.get("phase"), "panel_done_wait")

    def test_a_short_phase_budget_terminates_with_panel_evidence(self):
        state = self.run_watchdog(self.request, stall=1, phase=0.05, wait=0.25)
        self.assertTrue(state.get("stalled"))
        self.assertEqual(state.get("source"), "generic_panel_phase_seconds")
        self.assertIn("panel_done_wait", str(state.get("wait_evidence")))

    def test_a_foreign_marker_does_not_extend_a_silent_worker(self):
        foreign = {
            "panel_admission": {"profile_id": PROFILE},
            "panel_guard": {"job_id": "job_other", "nonce": NONCE},
        }
        state = self.run_watchdog(foreign, stall=0.05, phase=60, wait=0.3)
        self.assertTrue(state.get("stalled"))
        self.assertEqual(state.get("source"), "generic_stall_seconds")

    def test_a_plain_job_keeps_the_stall_contract(self):
        state = self.run_watchdog({}, stall=0.05, phase=60, wait=0.3)
        self.assertTrue(state.get("stalled"))
        self.assertEqual(state.get("source"), "generic_stall_seconds")
        self.assertNotIn("wait_evidence", state)


if __name__ == "__main__":
    unittest.main()
