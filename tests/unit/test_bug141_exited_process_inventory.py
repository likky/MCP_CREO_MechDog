"""BUG-141: only confirmed-exited Creo entries escape identity uncertainty."""

import ctypes
import unittest
from pathlib import Path
from unittest.mock import patch

from creo_mechdog import creo_startup
from tests import test_creo_startup as startup_tests


class Bug141InventoryTests(unittest.TestCase):
    def setUp(self):
        self.settings = creo_startup.Settings(
            Path("C:/Creo/Parametric/bin/parametric.exe"),
            Path("C:/Creo/Parametric/bin/parametric.psf"),
            True,
            120,
            False,
        )

    def inventory_with_failed_session_query(self, identity=None, identity_error=None):
        def first(_snapshot, output):
            output._obj.pid = 18988
            output._obj.name = "xtop.exe"
            return True

        identity_patch = patch.object(creo_startup, "process_identity", return_value=identity)
        if identity_error is not None:
            identity_patch = patch.object(
                creo_startup, "process_identity", side_effect=identity_error
            )
        with (
            patch.object(creo_startup, "_snapshot", return_value=1),
            patch.object(creo_startup, "_first", side_effect=first),
            patch.object(creo_startup, "_next", return_value=False),
            patch.object(creo_startup, "_close"),
            patch.object(creo_startup, "windows_session", return_value=7),
            patch.object(creo_startup, "_session", return_value=False),
            patch.object(creo_startup.ctypes, "get_last_error", return_value=0),
            identity_patch as process_identity,
        ):
            observed = creo_startup.inventory(self.settings)
        return observed, process_identity

    def test_confirmed_exited_entry_is_ignored(self):
        observed, process_identity = self.inventory_with_failed_session_query(identity=None)
        self.assertEqual(observed, {"processes": [], "uncertain": False})
        process_identity.assert_called_once_with(18988)

    def test_active_entry_with_unknown_session_remains_protected(self):
        identity = {"pid": 18988, "created": 10, "image": "C:/Creo/xtop.exe"}
        observed, process_identity = self.inventory_with_failed_session_query(identity=identity)
        self.assertEqual(observed, {"processes": [], "uncertain": True})
        process_identity.assert_called_once_with(18988)

    def test_permission_or_state_query_failure_remains_protected(self):
        for error in (OSError(5, "access denied"), OSError(998, "state unknown")):
            with self.subTest(error=error):
                observed, _ = self.inventory_with_failed_session_query(identity_error=error)
                self.assertEqual(observed, {"processes": [], "uncertain": True})

    def test_process_identity_recognizes_a_nonzero_exit_time(self):
        def times(_handle, _created, exited, _kernel, _user):
            ctypes.cast(exited, ctypes.POINTER(creo_startup.wintypes.FILETIME))[0].dwLowDateTime = 1
            return True

        with (
            patch.object(creo_startup, "_open", return_value=55),
            patch.object(creo_startup, "_image", return_value=True),
            patch.object(creo_startup, "_times", side_effect=times),
            patch.object(creo_startup, "_close") as close,
        ):
            self.assertIsNone(creo_startup.process_identity(18988))
        close.assert_called_once_with(55)


class Bug141StartupProtectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = startup_tests.CreoStartupTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_selected_session_does_not_swallow_inventory_uncertainty(self):
        self.fixture.config["creo_session_id"] = "private-selected-session"
        self.fixture.inventory.return_value = {"processes": [], "uncertain": True}
        state = self.fixture.drive()
        self.assertEqual(state["state"], "selection_required")
        self.fixture.build.assert_not_called()
        self.fixture.probe.assert_not_called()
        self.fixture.launch.assert_not_called()

    def test_selected_session_does_not_swallow_multiple_session_conflict(self):
        self.fixture.config["creo_session_id"] = "private-selected-session"
        self.fixture.inventory.return_value = self.fixture.existing()
        self.fixture.probe.return_value = {
            "connected": False,
            "connection_state": "ambiguous",
            "toolkit_code": -36,
        }
        state = self.fixture.drive()
        self.assertEqual(state["state"], "selection_required")
        self.fixture.launch.assert_not_called()

    def test_force_ready_does_not_swallow_identity_conflict(self):
        self.fixture.inventory.return_value = {"processes": [], "uncertain": True}
        state = self.fixture.drive()
        self.assertEqual(state["state"], "selection_required")
        self.fixture.startup.force_ready(enabled=True)
        with self.assertRaises(RuntimeError):
            self.fixture.startup.require_ready()


if __name__ == "__main__":
    unittest.main()
