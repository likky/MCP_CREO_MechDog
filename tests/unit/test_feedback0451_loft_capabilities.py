"""BUG-193 & DEV-102: loft/surface_loft runtime_ready, before-job callback preflight, and capabilities clarity."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from creo_mechdog import capabilities, capability_pages, generic_bridge, server


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

    def test_loft_and_panel_reject_before_job_when_callback_not_loaded(self):
        not_loaded = {
            "readiness": "not_loaded",
            "reason": "recorded_application_not_active",
            "next_action": "start_or_register_application_manually",
            "registry_file": "build/blend_callback_protk.dat",
        }
        loft_ops = [
            {
                "op": "sketch",
                "label": "s0",
                "plane": "XY",
                "entities": [{"type": "circle", "name": "c0", "center": [0, 0], "radius": 5}],
            },
            {
                "op": "sketch",
                "label": "s1",
                "plane": "XY",
                "offset": 10,
                "entities": [{"type": "circle", "name": "c1", "center": [0, 0], "radius": 5}],
            },
            {"op": "loft", "label": "l1", "sections": ["s0", "s1"], "mode": "add"},
        ]
        with (
            patch.object(generic_bridge.bridge, "callback_status", return_value=not_loaded),
            patch.object(generic_bridge.bridge, "toolkit_lock") as mock_lock,
        ):
            with self.assertRaises(ValueError) as caught:
                generic_bridge.submit(loft_ops)
            mock_lock.assert_not_called()
        msg = str(caught.exception)
        self.assertIn("BLEND_CALLBACK_SETUP_REQUIRED", msg)
        self.assertIn("before-job preflight", msg)
        self.assertIn("creo_new_loft_part", msg)


if __name__ == "__main__":
    unittest.main()
