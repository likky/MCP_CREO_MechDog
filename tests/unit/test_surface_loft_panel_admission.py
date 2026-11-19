"""BUG-120/D1: the resident panel route is admitted on its own declaration.

The tree route keeps its BUG-122 and element-id gates; a panel request must not
inherit them, because the panel backend does not build an element tree at all. The
panel route instead needs its own worker declaration and a certified UI profile, and
a refusal must happen before a job exists and before the Toolkit channel is taken.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bridge
import generic_bridge as general
from creo_mechdog import capabilities, panel_profiles
from tests.unit import test_toolkit_channel as channel_tests

WORKER_SHA = "c95cd7c2655b0799bb8efb6f68e21ac891157af970b42d78c135f53e5326864b"

CANDIDATE_ONLY_COMMANDS = {
    "open_macro": "~ Command `ProCmdFtBndBlend`;",
    "select_command": "~ Command `%MECHDOG_COMMAND%`;",
    "done_macro": "~ Activate `main_dlg_cur` `dashInst0.Done`;",
    "done_command": "ProCmdFtBndBlend",
}


def candidate_only_library(test: unittest.TestCase) -> None:
    """Point the profile library at a candidate-only manifest for this test.

    The shipped library carries a certified Creo 10 profile, so the "no certified
    profile" refusal needs its own library instead of borrowing the repository one.
    """
    directory = tempfile.TemporaryDirectory()
    test.addCleanup(directory.cleanup)
    root = Path(directory.name)
    base = root / "templates" / "panel"
    (base / "certifications").mkdir(parents=True)
    (base / "manifest.json").write_text(
        json.dumps(
            {
                "contract": panel_profiles.CONTRACT,
                "recordings": {},
                "profiles": [
                    {
                        "profile_id": "creo10-bbl-candidate-only",
                        "status": "candidate",
                        "release_numeric": 42,
                        "creo_release": "Creo 10.0.0.0",
                        "commands": dict(CANDIDATE_ONLY_COMMANDS),
                        "digest": panel_profiles.command_digest(CANDIDATE_ONLY_COMMANDS),
                        "certification": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    patcher = patch.object(panel_profiles, "ROOT", root)
    patcher.start()
    test.addCleanup(patcher.stop)


def tree_feature(**extra):
    entry = {
        "available": True,
        "state": "compiled",
        "sdk_requirements": ["PRO_E_BNBLN_CURVES"],
        "missing_sdk_requirements": [],
        "kernel_completion": "unsupported",
        "worker_sha256": WORKER_SHA,
        "release_numeric": 42,
        "job_id": "measured_job",
        "observed_at": "2026-11-13T00:00:00+08:00",
        "evidence": {"release_numeric": 42, "create_code": 0, "extract_code": -18},
    }
    entry.update(extra)
    return entry


def identity(panel=None, **tree):
    features = {"surface_loft": tree_feature(**tree)}
    if panel is not None:
        features["surface_loft_panel"] = panel
    return {
        "identity_status": "verified",
        "identity_source": "worker_self_report",
        "source_digest": "a" * 64,
        "worker_sha256": WORKER_SHA,
        "features": features,
    }


def panel_op():
    return {
        "op": "surface_loft",
        "label": "loft_surface",
        "sections": ["loft_a", "loft_b"],
        "creation_route": "resident_panel",
    }


def tree_op():
    return {"op": "surface_loft", "label": "loft_surface", "sections": ["loft_a", "loft_b"]}


class RouteDetection(unittest.TestCase):
    def test_only_the_panel_field_selects_the_panel_route(self):
        self.assertTrue(capabilities.is_panel_route(panel_op()))
        self.assertFalse(capabilities.is_panel_route(tree_op()))
        self.assertFalse(
            capabilities.is_panel_route({**tree_op(), "creation_route": "element_tree"})
        )
        self.assertFalse(
            capabilities.is_panel_route({"op": "extrude", "creation_route": "resident_panel"})
        )


class TreeGatesDoNotApplyToThePanelRoute(unittest.TestCase):
    def test_missing_element_ids_do_not_refuse_a_panel_request(self):
        without_ids = identity(
            available=False,
            state="bnbln_element_ids_missing",
            sdk_requirements=["PRO_E_BNBLN_CURVES"],
            missing_sdk_requirements=["PRO_E_BNBLN_CURVES"],
        )
        capabilities.require_worker_availability([panel_op()], without_ids)

    def test_the_tree_route_still_refuses_on_the_same_identity(self):
        without_ids = identity(
            available=False,
            state="bnbln_element_ids_missing",
            sdk_requirements=["PRO_E_BNBLN_CURVES"],
            missing_sdk_requirements=["PRO_E_BNBLN_CURVES"],
        )
        with self.assertRaisesRegex(ValueError, "compiled out of the current worker"):
            capabilities.require_worker_availability([tree_op()], without_ids)

    def test_the_measured_kernel_refusal_does_not_apply_to_a_panel_request(self):
        capabilities.require_kernel_completion([panel_op()], identity())

    def test_the_tree_route_keeps_the_measured_kernel_refusal(self):
        with self.assertRaisesRegex(ValueError, "refused before a job"):
            capabilities.require_kernel_completion([tree_op()], identity())


class PanelRouteNeedsItsOwnDeclaration(unittest.TestCase):
    def test_an_undeclared_backend_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            capabilities.require_panel_route(identity())
        text = str(caught.exception)
        self.assertIn("does not declare a surface_loft_panel backend", text)
        self.assertIn("not retried on the element_tree route", text)
        self.assertIn("No native job was queued", text)

    def test_a_declared_but_unavailable_backend_is_refused(self):
        declared = identity(panel={"available": False, "state": "not_implemented"})
        with self.assertRaises(ValueError) as caught:
            capabilities.require_panel_route(declared)
        self.assertIn("state='not_implemented'", str(caught.exception))

    def test_a_declared_backend_still_needs_a_certified_profile(self):
        candidate_only_library(self)
        declared = identity(panel={"available": True, "state": "ready"})
        with self.assertRaisesRegex(ValueError, "no certified UI profile"):
            capabilities.require_panel_route(declared)


class PanelRouteIsDisclosedSeparately(unittest.TestCase):
    def test_routes_report_the_tree_and_the_panel_gate(self):
        candidate_only_library(self)
        families = {"surface_loft": {"available": True, "enabled": True}}
        projected = capabilities.project_worker_availability(families, identity())
        entry = projected["surface_loft"]
        self.assertTrue(entry["available"])
        self.assertTrue(entry["routes"]["element_tree"]["available"])
        panel = entry["routes"]["resident_panel"]
        self.assertFalse(panel["default"])
        self.assertEqual(panel["state"], "not_declared")
        self.assertFalse(panel["runtime_ready"])
        self.assertEqual(panel["profile"]["status"], "uncertified")
        self.assertIn("does not declare a surface_loft_panel backend", panel["reason"])

    def test_a_compiled_backend_without_a_certified_profile_is_not_ready(self):
        candidate_only_library(self)
        families = {"surface_loft": {"available": True, "enabled": True}}
        projected = capabilities.project_worker_availability(
            families, identity(panel={"available": True, "state": "ready"})
        )
        panel = projected["surface_loft"]["routes"]["resident_panel"]
        self.assertTrue(panel["compiled"])
        self.assertFalse(panel["runtime_ready"])
        self.assertIn("no certified panel UI profile", panel["reason"])

    def test_the_tree_route_availability_field_keeps_its_meaning(self):
        families = {"surface_loft": {"available": True, "enabled": True}}
        projected = capabilities.project_worker_availability(
            families, identity(panel={"available": False, "state": "not_implemented"})
        )
        entry = projected["surface_loft"]
        self.assertTrue(entry["available"])
        self.assertEqual(entry["availability"], "available")
        self.assertNotIn("unavailable_reason", entry)
        self.assertFalse(entry["routes"]["resident_panel"]["runtime_ready"])

    def test_a_missing_tree_feature_still_discloses_both_routes(self):
        families = {"surface_loft": {"available": True, "enabled": True}}
        unverified = {"identity_status": "worker_missing"}
        projected = capabilities.project_worker_availability(families, unverified)
        routes = projected["surface_loft"]["routes"]
        self.assertTrue(routes["element_tree"]["default"])
        self.assertIsNone(routes["element_tree"]["available"])
        self.assertEqual(routes["element_tree"]["state"], "not_declared")
        self.assertFalse(routes["resident_panel"]["runtime_ready"])


class PanelRouteDisclosureWithTheCertifiedProfile(unittest.TestCase):
    """D6: the shipped certified profile is disclosed against the host release."""

    def route(self, **identity_overrides):
        families = {"surface_loft": {"available": True, "enabled": True}}
        declared = identity(panel={"available": True, "state": "ready"}, **identity_overrides)
        projected = capabilities.project_worker_availability(families, declared)
        return projected["surface_loft"]["routes"]["resident_panel"]

    def test_a_recorded_release_matching_the_profile_is_ready(self):
        panel = self.route()
        self.assertTrue(panel["compiled"])
        self.assertTrue(panel["runtime_ready"])
        self.assertEqual(panel["profile"]["status"], "certified")
        self.assertEqual(panel["profile"]["profile_id"], "creo10-bbl-candidate-3")
        self.assertEqual(panel["profile"]["release_numeric"], 42)

    def test_an_unrecorded_host_release_is_not_ready(self):
        panel = self.route(release_numeric=None, evidence={})
        self.assertFalse(panel["runtime_ready"])
        self.assertIn("not recorded yet", panel["reason"])

    def test_another_host_release_is_not_ready(self):
        panel = self.route(release_numeric=44)
        self.assertFalse(panel["runtime_ready"])
        self.assertIn("was measured on release_numeric=42", panel["reason"])


class SubmissionRefusesBeforeTheChannel(unittest.TestCase):
    setUp = channel_tests.ToolkitChannel.setUp

    def parsed_identity(self, panel=None):
        features = {
            "surface_loft": {
                "available": True,
                "state": "compiled",
                "sdk_requirements": ["PRO_E_BNBLN_CURVES"],
                "missing_sdk_requirements": [],
            }
        }
        if panel is not None:
            features["surface_loft_panel"] = panel
        parsed = bridge._parse_worker_build_info(
            {"identity_schema": 1, "source_digest": "a" * 64, "features": features}, WORKER_SHA
        )
        self.assertIsNotNone(parsed)
        return parsed

    def test_an_undeclared_panel_backend_is_refused_before_the_lock(self):
        raw = self.parsed_identity()
        with (
            patch.object(bridge, "worker_build_identity", return_value=raw),
            patch.object(bridge, "toolkit_lock") as lock,
        ):
            with self.assertRaisesRegex(ValueError, "surface_loft_panel"):
                general.submit([panel_op()])
            lock.assert_not_called()
        self.assertFalse((self.root / "jobs").exists())

    def test_a_declared_backend_still_needs_a_certified_profile(self):
        candidate_only_library(self)
        raw = self.parsed_identity(panel={"available": True, "state": "ready"})
        with (
            patch.object(bridge, "worker_build_identity", return_value=raw),
            patch.object(bridge, "toolkit_lock") as lock,
        ):
            with self.assertRaisesRegex(ValueError, "no certified UI profile"):
                general.submit([panel_op()])
            lock.assert_not_called()
        self.assertFalse((self.root / "jobs").exists())

    def test_the_worker_identity_keeps_the_panel_declaration(self):
        raw = self.parsed_identity(panel={"available": False, "state": "not_implemented"})
        self.assertEqual(raw["features"]["surface_loft_panel"]["state"], "not_implemented")
        self.assertFalse(raw["features"]["surface_loft_panel"]["available"])

    def test_a_worker_without_the_declaration_projects_only_the_tree_feature(self):
        raw = self.parsed_identity()
        self.assertNotIn("surface_loft_panel", raw["features"])

    def test_a_non_boolean_panel_flag_is_not_a_declaration(self):
        raw = self.parsed_identity(panel={"available": "yes", "state": "ready"})
        self.assertNotIn("surface_loft_panel", raw["features"])

    def test_a_mixed_plan_keeps_the_tree_refusal(self):
        raw = bridge._parse_worker_build_info(
            {
                "identity_schema": 1,
                "source_digest": "a" * 64,
                "features": {
                    "surface_loft": {
                        "available": False,
                        "state": "bnbln_element_ids_missing",
                        "sdk_requirements": ["PRO_E_BNBLN_CURVES"],
                        "missing_sdk_requirements": ["PRO_E_BNBLN_CURVES"],
                    },
                    "surface_loft_panel": {"available": True, "state": "ready"},
                },
            },
            WORKER_SHA,
        )
        with (
            patch.object(bridge, "worker_build_identity", return_value=raw),
            patch.object(bridge, "toolkit_lock") as lock,
        ):
            with self.assertRaisesRegex(ValueError, "compiled out of the current worker"):
                general.submit([panel_op(), {**tree_op(), "label": "loft_tree"}])
            lock.assert_not_called()
        self.assertFalse((self.root / "jobs").exists())


class SecondDirectionGate(unittest.TestCase):
    """BUG-120/D7: a guide request needs a profile that froze the collector switch."""

    def guides(self):
        return [
            {"label": "guide_a", "open_confirmed": True},
            {"label": "guide_b", "open_confirmed": True},
        ]

    def test_guides_need_the_profile_slot(self):
        with self.assertRaisesRegex(ValueError, "second_direction_macro"):
            capabilities.require_panel_directions(
                [{**panel_op(), "guides": self.guides()}],
                {"profile_id": "creo10-bbl-candidate-2", "second_direction_macro": ""},
            )

    def test_a_profile_with_the_slot_admits_guides(self):
        capabilities.require_panel_directions(
            [{**panel_op(), "guides": self.guides()}],
            {"profile_id": "creo10-bbl-candidate-3", "second_direction_macro": "~ Trigger x;"},
        )

    def test_an_empty_guides_array_is_not_a_second_direction(self):
        capabilities.require_panel_directions(
            [{**panel_op(), "guides": []}], {"profile_id": "creo10-bbl-candidate-2"}
        )

    def test_the_gate_ignores_the_element_tree_route(self):
        capabilities.require_panel_directions(
            [{**tree_op(), "guides": self.guides()}], {"profile_id": "creo10-bbl-candidate-2"}
        )


class GuidesAreRefusedBeforeTheChannel(unittest.TestCase):
    setUp = channel_tests.ToolkitChannel.setUp

    def parsed_identity(self):
        parsed = bridge._parse_worker_build_info(
            {
                "identity_schema": 1,
                "source_digest": "a" * 64,
                "features": {
                    "surface_loft": {
                        "available": True,
                        "state": "compiled",
                        "sdk_requirements": ["PRO_E_BNBLN_CURVES"],
                        "missing_sdk_requirements": [],
                    },
                    "surface_loft_panel": {"available": True, "state": "ready"},
                },
            },
            WORKER_SHA,
        )
        self.assertIsNotNone(parsed)
        return parsed

    def test_a_profile_without_the_slot_refuses_guides_before_the_lock(self):
        admission = {
            "profile_id": "creo10-bbl-candidate-2",
            "mode": "certified",
            "open_macro": "~ Command `ProCmdFtBndBlend`;",
            "second_direction_macro": "",
            "select_command": "~ Command `%MECHDOG_COMMAND%`;",
            "done_macro": "~ Activate `main_dlg_cur` `dashInst0.Done`;",
            "done_command": "ProCmdFtBndBlend",
        }
        request = panel_op()
        request["guides"] = [
            {"label": "guide_a", "open_confirmed": True},
            {"label": "guide_b", "open_confirmed": True},
        ]
        with (
            patch.object(bridge, "worker_build_identity", return_value=self.parsed_identity()),
            patch.object(general, "require_panel_route", return_value=admission),
            patch.object(bridge, "toolkit_lock") as lock,
        ):
            with self.assertRaisesRegex(ValueError, "second_direction_macro"):
                general.submit([request])
            lock.assert_not_called()
        self.assertFalse((self.root / "jobs").exists())


if __name__ == "__main__":
    unittest.main()
