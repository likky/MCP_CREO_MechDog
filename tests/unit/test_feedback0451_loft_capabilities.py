"""BUG-193 & DEV-102: loft/surface_loft runtime_ready, before-job callback preflight, and capabilities clarity."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from creo_mechdog import (
    bridge,
    capabilities,
    capability_pages,
    creo_startup,
    generic_bridge,
    server,
)
from tests.unit import test_toolkit_channel
from tests.unit.test_surface_loft_panel_admission import panel_op


def _creo10_identity() -> dict:
    return {
        "identity_status": "verified",
        "identity_source": "worker_self_report",
        "source_digest": "a" * 64,
        "worker_sha256": "b" * 64,
        "release_numeric": 42,
        "features": {
            "surface_loft": {"available": True, "state": "compiled"},
            "surface_loft_panel": {"available": True, "state": "ready"},
        },
    }


class LoftRuntimeReadinessTests(unittest.TestCase):
    def test_creo10_without_ready_callback_marks_surface_loft_and_loft_not_runtime_ready(self):
        projected = capabilities.project_worker_availability(
            capabilities.families(),
            _creo10_identity(),
            runtime=None,
            callback_runtime={
                "readiness": "not_loaded",
                "reason": "recorded_application_not_active",
            },
        )
        sl = projected["surface_loft"]
        self.assertTrue(sl["enabled"])
        self.assertFalse(sl["runtime_ready"])
        self.assertFalse(sl["routes"]["element_tree"]["runtime_ready"])
        self.assertEqual(
            sl["routes"]["element_tree"]["runtime_admission"]["status"],
            "known_release_extract_unsupported",
        )
        self.assertFalse(sl["routes"]["resident_panel"]["runtime_ready"])
        self.assertEqual(sl["routes"]["resident_panel"]["callback_readiness"], "not_loaded")
        self.assertEqual(sl["runtime_admission"]["status"], "not_ready")

        loft = projected["loft"]
        self.assertTrue(loft["enabled"])
        self.assertFalse(loft["runtime_ready"])
        self.assertEqual(loft["runtime_admission"]["callback_readiness"], "not_loaded")
        self.assertEqual(loft["runtime_admission"]["status"], "requires_ready_callback")

    def test_creo10_with_ready_callback_marks_panel_and_loft_runtime_ready(self):
        projected = capabilities.project_worker_availability(
            capabilities.families(),
            _creo10_identity(),
            runtime=None,
            callback_runtime={"readiness": "ready", "reason": None},
        )
        sl = projected["surface_loft"]
        self.assertTrue(sl["runtime_ready"])
        self.assertFalse(sl["routes"]["element_tree"]["runtime_ready"])
        self.assertTrue(sl["routes"]["resident_panel"]["runtime_ready"])
        self.assertTrue(projected["loft"]["runtime_ready"])
        self.assertEqual(projected["loft"]["runtime_admission"]["status"], "ready")

    def test_compact_capabilities_exposes_runtime_ready_and_unavailable_operations_clarity(self):
        payload = server._capabilities_payload([])
        self.assertIn("registered_but_unavailable_operations", payload)
        self.assertEqual(
            set(payload["registered_but_unavailable_operations"]),
            set(capabilities.UNAVAILABLE_OPERATIONS),
        )
        self.assertIn("operations_note", payload)
        for op in payload["registered_but_unavailable_operations"]:
            self.assertNotIn(op, payload["operations"])
        compact = capability_pages.capabilities_response(lambda: payload, detail="compact")
        self.assertIn("runtime_ready", compact["families"]["loft"])
        self.assertIn("runtime_ready", compact["families"]["surface_loft"])


class LockFreeCallbackAdmission(unittest.TestCase):
    setUp = test_toolkit_channel.ToolkitChannel.setUp

    def prepare(self):
        build = self.root / "build"
        loader = build / "blend_loader" / "generation" / "loader.dll"
        loader.parent.mkdir(parents=True)
        (build / "creo_worker.exe").touch()
        artifacts = {
            "artifact_status": "prepared",
            "registry_file": "fixture.dat",
            "loader_file": str(loader),
            "module_file": "payload.dll",
            "loader_sha256": "loader",
            "dll_sha256": "payload",
            "protocol": 4,
            "contract": "panel",
            "command": "command",
            "resource_root": str(self.root),
            "loader_abi": 2,
        }
        hosts = [{"pid": 20, "created": 116444736000000000, "image": "xtop.exe", "matches": True}]
        self.enterContext(patch.object(bridge, "callback_setup_status", return_value=artifacts))
        self.enterContext(
            patch.object(
                creo_startup, "inventory", return_value={"processes": hosts, "uncertain": False}
            )
        )
        self.enterContext(
            patch.object(bridge, "surface_loft_admission_identity", return_value=_creo10_identity())
        )
        return artifacts, loader.parent / "callback_result.json", hosts

    def test_two_routes_reject_without_probing_locking_or_making_a_job(self):
        artifacts, record, _ = self.prepare()
        ops = [{"op": "loft", "label": "loft_one", "sections": [40, 49]}, panel_op()]
        with (
            patch.object(bridge, "toolkit_lock", side_effect=AssertionError("took Toolkit lock")),
            patch.object(bridge.subprocess, "run", side_effect=AssertionError("started a probe")),
        ):
            for identity, readiness in [
                (None, "not_loaded"),
                ({"terminated": True}, "not_loaded"),
                ({"terminated": False, "dll_sha256": "other"}, "version_mismatch"),
                ({"process_id": 999, "terminated": False}, "unknown"),
            ]:
                if identity is not None:
                    record.write_text(
                        json.dumps(
                            {**artifacts, "process_id": 20, "initialize_code": 0, **identity}
                        )
                    )
                for op in ops:
                    with self.subTest(op=op["op"], identity=identity):
                        with self.assertRaisesRegex(ValueError, "before-job preflight") as caught:
                            generic_bridge.submit([op])
                        self.assertIn(readiness, str(caught.exception))
                        self.assertEqual(
                            "creo_new_loft_part" in str(caught.exception), op["op"] == "loft"
                        )
        self.assertFalse(bridge.JOBS.exists())
        self.assertFalse(generic_bridge.MODELS.exists())

    def test_observation_is_bound_to_lifecycle_deployment_and_target(self):
        artifacts, path, hosts = self.prepare()
        record = {**artifacts, "process_id": 20, "initialize_code": 0, "terminated": False}
        path.write_text(json.dumps(record))
        binding, _ = bridge._callback_context(self.root / "build", artifacts)
        bridge.record_channel_health(
            True, callback_runtime={"binding": binding, "readiness": "ready"}
        )
        self.assertEqual(bridge.callback_admission_status()["readiness"], "ready")
        path.write_text(json.dumps({**record, "terminated": True}))
        self.assertEqual(bridge.callback_admission_status()["readiness"], "not_loaded")
        path.write_text(json.dumps(record))
        current = bridge.callback_admission_status()
        self.assertTrue(current["admit_to_worker"])
        self.assertNotEqual(current["readiness"], "ready")
        with patch.object(bridge, "selected_session", return_value="other"):
            self.assertNotIn("admit_to_worker", bridge.callback_admission_status())
        hosts.append({**hosts[0], "pid": 21})
        self.assertNotIn("admit_to_worker", bridge.callback_admission_status())
        hosts.pop()
        hosts[0]["created"] = 150000000000000000
        self.assertNotIn("admit_to_worker", bridge.callback_admission_status())
        path.write_text("{")
        self.assertEqual(bridge.callback_admission_status()["readiness"], "unknown")
        self.assertEqual(bridge.callback_admission_status({}), {})


if __name__ == "__main__":
    unittest.main()
