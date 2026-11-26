"""BUG-139 regression coverage: probe budget, success-landing race, phase
progression, admission downgrade, identity attribution and error context."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import bridge
from creo_mechdog import creo_startup
from tests import test_creo_startup as startup_tests

PROBE_TIMEOUT = {
    "connected": False,
    "connection_state": "probe_timeout",
    "toolkit_code": None,
    "message": "probe helper timed out",
}
CONNECTION_FAILED = {
    "connected": False,
    "connection_state": "connection_failed",
    "toolkit_code": -38,
}
SESSION_NOT_FOUND = {
    "connected": False,
    "connection_state": "not_found_or_unreadable",
    "toolkit_code": -4,
    "worker_exit_code": 20,
}


class Bug139StartupFixture(unittest.TestCase):
    """Reuse the FEAT-019 coordinator fixture; each subclass selects a focus."""

    def setUp(self):
        self.fixture = startup_tests.CreoStartupTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.startup = self.fixture.startup
        self.clock = self.fixture.clock

    def drive(self, retry=False, deadline=None):
        self.startup._phase_deadline = None
        self.startup._expired = False
        settings = creo_startup.Settings.load()
        if deadline is None:
            deadline = self.clock.elapsed + 10
        self.startup._attempt_deadline = deadline
        self.startup._drive(settings, retry, deadline)
        return self.startup.status()

    def published_states(self):
        log_path = self.fixture.coordinator / "startup.log"
        if not log_path.is_file():
            return []
        states = []
        for line in log_path.read_text(encoding="utf-8").splitlines():
            marker = "state="
            if marker in line:
                states.append(line.split(marker, 1)[1].split(" ", 1)[0])
        return states

    def capture_publishes(self):
        original = self.startup._publish
        records = []

        def wrapped(state, message, **kwargs):
            result = original(state, message, **kwargs)
            records.append(dict(result))
            return result

        self.startup._publish = wrapped
        return records


# --- Fix 1 + Fix 4: configurable probe timeout and total budget --------------


class Bug139ConfigurableBudget(Bug139StartupFixture):
    def test_probe_timeout_is_wired_from_config_into_probe_calls(self):
        self.fixture.config["creo_probe_timeout_seconds"] = 23
        self.fixture.inventory.return_value = self.fixture.existing()
        self.drive()
        self.fixture.probe.assert_called_once_with(
            connect_timeout_seconds=23, build_worker=False, deadline=10
        )

    def test_default_probe_timeout_is_at_least_ten(self):
        self.fixture.config.pop("creo_probe_timeout_seconds", None)
        self.assertGreaterEqual(creo_startup.Settings.load().probe_timeout, 10)

    def test_invalid_probe_timeout_is_rejected(self):
        for invalid in (0, 61, True, 7.5, "7"):
            with (
                self.subTest(invalid=invalid),
                patch.dict(self.fixture.config, {"creo_probe_timeout_seconds": invalid}),
            ):
                with self.assertRaises(ValueError):
                    creo_startup.Settings.load()

    def test_total_budget_defaults_to_connect_plus_preparation(self):
        self.fixture.config.pop("startup_total_budget_seconds", None)
        self.fixture.config["creo_startup_timeout_seconds"] = 60
        self.assertEqual(
            creo_startup.Settings.load().total_budget,
            60 + creo_startup.PREPARATION_BUDGET,
        )

    def test_total_budget_is_configurable(self):
        self.fixture.config["startup_total_budget_seconds"] = 480
        self.assertEqual(creo_startup.Settings.load().total_budget, 480)

    def test_total_budget_validation_rejects_bad_values(self):
        base = dict(self.fixture.config)
        for invalid in (59, 1801, True, "480", 5):
            with self.subTest(invalid=invalid):
                cfg = dict(base)
                cfg["creo_startup_timeout_seconds"] = 10
                cfg["startup_total_budget_seconds"] = invalid
                with patch.dict(self.fixture.config, cfg, clear=True):
                    with self.assertRaises(ValueError):
                        creo_startup.Settings.load()

    def test_probe_timeout_validation_boundary(self):
        # Config accepts 1..60; bridge.session_status mirrors the same ceiling
        # so the coordinator can raise the per-probe budget above the old 30 s.
        self.fixture.config["creo_probe_timeout_seconds"] = 60
        self.assertEqual(creo_startup.Settings.load().probe_timeout, 60)
        self.fixture.config["creo_probe_timeout_seconds"] = 1
        self.assertEqual(creo_startup.Settings.load().probe_timeout, 1)


# --- Fix 2 + Fix 1 retry: probe landing and probe_timeout retry ---------------


class Bug139ProbeLanding(Bug139StartupFixture):
    def test_not_found_stays_pending_and_keeps_raw_evidence_until_success(self):
        self.fixture.inventory.return_value = self.fixture.existing()

        def second_probe(**kwargs):
            waiting = self.startup.status()
            self.assertEqual(waiting["state"], "waiting_for_connection")
            self.assertEqual(waiting["diagnosis"], "session_not_ready")
            self.assertEqual(waiting["native"], SESSION_NOT_FOUND)
            self.assertEqual(kwargs["deadline"], 10)
            return startup_tests.READY

        probes = iter([lambda **_: SESSION_NOT_FOUND, second_probe])
        self.fixture.probe.side_effect = lambda **kwargs: next(probes)(**kwargs)
        result = self.drive()
        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["probe_attempts"], 2)
        self.assertNotIn("diagnosis", result)
        self.fixture.launch.assert_not_called()

    def test_a_single_lookup_failure_at_deadline_does_not_diagnose_stale_session(self):
        self.fixture.inventory.return_value = self.fixture.existing()

        def last_probe(**kwargs):
            self.clock.elapsed = kwargs["deadline"]
            return SESSION_NOT_FOUND

        self.fixture.probe.side_effect = last_probe
        result = self.drive()
        self.assertEqual(result["state"], "timeout")
        self.assertNotEqual(result.get("diagnosis"), "stale_session_needs_restart")
        self.assertEqual(result["native"], SESSION_NOT_FOUND)
        self.assertEqual(result["probe_attempts"], 1)
        self.fixture.launch.assert_not_called()

    def test_connected_probe_right_before_deadline_lands_ready(self):
        """A probe that succeeds only after the clock passed the deadline must
        still publish ready, not timeout (BUG-139 success-landing race)."""
        self.fixture.inventory.return_value = self.fixture.existing()

        def late_ready(*args, **kwargs):
            # drive() gives a 10 s connect budget; the probe outlasts it.
            self.clock.elapsed = 11
            return startup_tests.READY

        self.fixture.probe.side_effect = late_ready
        state = self.drive()
        self.assertEqual(state["state"], "ready")
        self.assertTrue(state["connected"])
        self.startup.require_ready()

    def test_probe_timeout_retries_within_budget_instead_of_failing_once(self):
        self.fixture.inventory.return_value = self.fixture.existing()
        self.fixture.probe.side_effect = [PROBE_TIMEOUT, PROBE_TIMEOUT, startup_tests.READY]
        state = self.drive()
        self.assertEqual(state["state"], "ready")
        self.assertEqual(self.fixture.probe.call_count, 3)
        self.fixture.launch.assert_not_called()
        # Each retry waited, consuming budget rather than ending the attempt.
        self.assertGreater(self.clock.elapsed, 0.0)

    def test_probe_timeout_exhausting_budget_publishes_timeout_with_context(self):
        self.fixture.inventory.return_value = self.fixture.existing()
        self.fixture.probe.return_value = PROBE_TIMEOUT
        state = self.drive()
        self.assertEqual(state["state"], "timeout")
        self.assertIn("connect_timeout_seconds=7", state["message"])
        self.fixture.launch.assert_not_called()


# --- Fix 3: connecting phase and updated_at refresh --------------------------


class Bug139PhaseProgression(Bug139StartupFixture):
    def test_connecting_phase_is_published_after_native_build(self):
        self.fixture.inventory.return_value = self.fixture.existing()
        self.fixture.probe.return_value = startup_tests.READY
        self.drive()
        states = self.published_states()
        self.assertIn("building_worker", states)
        self.assertIn("connecting", states)
        self.assertIn("ready", states)
        self.assertLess(states.index("building_worker"), states.index("connecting"))
        self.assertLess(states.index("connecting"), states.index("ready"))

    def test_status_after_build_no_longer_reports_building_worker(self):
        self.fixture.inventory.return_value = self.fixture.existing()
        self.fixture.probe.return_value = startup_tests.READY
        state = self.drive()
        self.assertNotIn(state.get("phase"), ("building_worker",))
        self.assertEqual(state["state"], "ready")

    def test_updated_at_refreshes_on_each_probe(self):
        self.fixture.inventory.return_value = self.fixture.existing()
        self.fixture.probe.side_effect = [CONNECTION_FAILED, startup_tests.READY]
        records = self.capture_publishes()
        self.drive()
        waiting = [r for r in records if r.get("state") == "waiting_for_connection"]
        self.assertGreaterEqual(len(waiting), 2)
        stamps = {r["updated_at"] for r in waiting}
        self.assertGreater(len(stamps), 1)


# --- Fix 4: total budget caps preparation before connection ------------------


class Bug139BudgetAccounting(Bug139StartupFixture):
    def test_preparation_phase_is_capped_by_total_budget(self):
        self.fixture.config["creo_startup_timeout_seconds"] = 10
        self.fixture.config["startup_total_budget_seconds"] = 60
        self.fixture.inventory.return_value = self.fixture.existing()

        def slow_build(*args, **kwargs):
            self.clock.elapsed = 61  # past the 60 s total budget

        self.fixture.build.side_effect = slow_build
        state = self.drive(deadline=60)
        self.assertEqual(state["state"], "timeout")
        # Connection was never attempted because preparation exhausted the budget.
        self.fixture.probe.assert_not_called()

    def test_connect_phase_gets_its_own_budget_within_total(self):
        # total budget (190) is larger than connect (10); a slow build that fits
        # in preparation must still leave the connection phase its own deadline.
        self.fixture.config["creo_startup_timeout_seconds"] = 10
        self.fixture.config.pop("startup_total_budget_seconds", None)
        self.fixture.inventory.return_value = self.fixture.existing()
        self.fixture.probe.return_value = startup_tests.READY
        state = self.drive(deadline=10 + creo_startup.PREPARATION_BUDGET)
        self.assertEqual(state["state"], "ready")
        self.fixture.probe.assert_called_once()


# --- Fix 5 + Fix 7: admission downgrade and error context --------------------


class Bug139Admission(Bug139StartupFixture):
    def _make_not_ready(self):
        self.startup._publish(
            "timeout",
            "coordinator snapshot is not ready",
            shared=False,
            native={"toolkit_code": -38},
        )
        self.assertFalse(self.startup.status()["connected"])

    def test_recent_connected_probe_opens_admission(self):
        self._make_not_ready()
        recent = datetime.now(timezone.utc).isoformat()
        with patch.object(
            bridge,
            "channel_health",
            return_value={"connected": True, "checked_at": recent},
        ):
            self.startup.require_ready()  # must not raise

    def test_stale_connected_probe_does_not_open_admission(self):
        self._make_not_ready()
        old = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
        with patch.object(
            bridge,
            "channel_health",
            return_value={"connected": True, "checked_at": old},
        ):
            with self.assertRaises(RuntimeError):
                self.startup.require_ready()

    def test_force_ready_overrides_a_non_ready_snapshot(self):
        self._make_not_ready()
        self.startup.force_ready(enabled=True)
        state = self.startup.status()
        self.assertTrue(state["force_ready"])
        self.assertIsNotNone(state["force_ready_at"])
        self.startup.require_ready()  # operator override opens admission

    def test_force_ready_can_be_cleared(self):
        self._make_not_ready()
        self.startup.force_ready(enabled=True)
        self.startup.require_ready()
        self.startup.force_ready(enabled=False)
        self.assertFalse(self.startup.status()["force_ready"])
        with self.assertRaises(RuntimeError):
            self.startup.require_ready()

    def test_require_ready_error_includes_last_toolkit_code_and_timeout(self):
        self._make_not_ready()
        with self.assertRaises(RuntimeError) as caught:
            self.startup.require_ready()
        message = str(caught.exception)
        self.assertIn("toolkit_code=-38", message)
        self.assertIn("connect_timeout_seconds=7", message)
        self.assertIn("No modeling job was queued", message)


# --- Fix 1 boundary: bridge.session_status mirrors the 1..60 ceiling ---------


class Bug139SessionStatusValidation(unittest.TestCase):
    def test_session_status_rejects_probe_timeout_outside_range(self):
        # Validation short-circuits before any lock/subprocess side effect.
        for invalid in (0, 61, True, 60.5, "60"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    bridge.session_status(invalid)


# --- Fix 6: worker_build_identity attribution and stale-failure cleanup -------


class _Completed:
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout if isinstance(stdout, bytes) else stdout.encode("utf-8")


VALID_BUILD_INFO = {
    "identity_schema": 1,
    "source_digest": "a" * 64,
    "features": {"surface_loft": {"available": True, "state": "supported"}},
}


class Bug139WorkerIdentity(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "build").mkdir()
        (self.tmp / "build" / "creo_worker.exe").write_bytes(b"worker-binary")
        self._root = patch.object(bridge, "ROOT", self.tmp)
        self._root.start()
        self._env = patch.object(
            bridge, "native_environment", return_value={"PATH": "C:\\fixture", "CREO": "Y"}
        )
        self._env.start()
        self._run = patch.object(bridge.subprocess, "run")
        self.run = self._run.start()
        self.addCleanup(self._cleanup)
        bridge._WORKER_IDENTITY_CACHE.clear()

    def _cleanup(self):
        self._run.stop()
        self._env.stop()
        self._root.stop()
        bridge._WORKER_IDENTITY_CACHE.clear()

    def test_verified_identity_carries_observed_at_and_env_fingerprint(self):
        self.run.return_value = _Completed(0, json.dumps(VALID_BUILD_INFO))
        identity = bridge.worker_build_identity()
        self.assertEqual(identity["identity_status"], "verified")
        self.assertIn("observed_at", identity)
        self.assertIn("env_fingerprint", identity)
        self.assertEqual(len(identity["env_fingerprint"]), 16)

    def test_verified_identity_drops_stale_failure_fields(self):
        self.run.return_value = _Completed(3221225781, b"")
        bad = bridge.worker_build_identity()
        self.assertEqual(bad["identity_status"], "invalid_build_info")
        self.assertEqual(bad["worker_exit_code"], 3221225781)
        self.assertIn("observed_at", bad)
        self.assertIn("env_fingerprint", bad)

        self.run.return_value = _Completed(0, json.dumps(VALID_BUILD_INFO))
        good = bridge.worker_build_identity(refresh=True)
        self.assertEqual(good["identity_status"], "verified")
        self.assertNotIn("worker_exit_code", good)
        self.assertNotIn("message", good)
        self.assertNotIn("budget_seconds", good)

    def test_environment_change_reprobes_and_heals_identity(self):
        self.run.return_value = _Completed(3221225781, b"")
        bridge.worker_build_identity()
        calls = self.run.call_count
        bridge.worker_build_identity()  # same env -> cached
        self.assertEqual(self.run.call_count, calls)

        self.run.return_value = _Completed(0, json.dumps(VALID_BUILD_INFO))
        with patch.object(
            bridge, "native_environment", return_value={"PATH": "C:\\fixed", "CREO": "Y"}
        ):
            identity = bridge.worker_build_identity()
        self.assertGreater(self.run.call_count, calls)
        self.assertEqual(identity["identity_status"], "verified")

    def test_env_fingerprint_is_stable_and_discriminates(self):
        a = bridge._env_fingerprint({"PATH": "x", "CREO": "Y"})
        b = bridge._env_fingerprint({"PATH": "x", "CREO": "Y"})
        c = bridge._env_fingerprint({"PATH": "x", "CREO": "Z"})
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(a), 16)

    def test_health_file_carries_identity_attribution_without_stale_failure(self):
        self.run.return_value = _Completed(0, json.dumps(VALID_BUILD_INFO))
        identity = bridge.worker_build_identity()
        recorded = bridge.record_channel_health(
            True, connection_state="connected", worker_build_identity=identity
        )
        wbi = recorded["worker_build_identity"]
        self.assertEqual(wbi["identity_status"], "verified")
        self.assertIn("observed_at", wbi)
        self.assertIn("env_fingerprint", wbi)
        self.assertNotIn("worker_exit_code", wbi)


if __name__ == "__main__":
    unittest.main()
