"""BUG-120/D5: a panel run is only successful when its exit and product are proven.

The native backend does not produce these fields yet, so these are consumer tests:
they pin what the Python side does with a record that claims success, lacks an exit
observation, reuses a quilt, or reports a claimed tree completion. Fabricating the
producer here would hide exactly the gap the plan leaves open.
"""

from __future__ import annotations

import unittest

from creo_mechdog import panel_receipt


def op(**overrides):
    record = {
        "op": "surface_loft",
        "creation_route": "resident_panel",
        "label": "panel_surface",
        "feature_id": 412,
        "quilt_id": "quilt:new_7",
        "feature_quilt": "quilt:new_7",
        "exit_observation": {
            "method": "bracket",
            "supported": True,
            "closed": True,
            "evidence": {},
        },
        "geometry_check": {
            "verified": True,
            "face_groups": ["group_1"],
            "area_mm2": 800.0,
            "method": "sampled_network_distance",
            "samples": {"count": 120, "max_mm": 0.008},
            "bbox": {
                "xyz_min": [0.0, 0.0, 0.0],
                "xyz_max": [40.0, 20.0, 0.0],
                "source": "prosurface_data_approx",
            },
        },
        "selection_intent": {"mode": "replace_then_toggle", "labels": ["a", "b"]},
        "selection_record": {"labels": ["a", "b"], "references": [{"label": "a"}, {"label": "b"}]},
    }
    record.update(overrides)
    return record


def result(**overrides):
    value = {
        "success": True,
        "saved_file_reloaded_and_verified": True,
        "operations": [op()],
    }
    value.update(overrides)
    return value


INPUTS = [{"op": "surface_loft", "label": "panel_surface", "sections": ["a", "b"]}]
ADMISSION = {
    "profile_id": "creo10-bbl-1",
    "mode": "candidate",
    "release_numeric": 42,
    "host_release_numeric": 42,
    "unverified_bindings": [],
}
PRIOR = {"quilts": [{"id": "quilt:old_3"}]}


def annotate(value, **kwargs):
    kwargs.setdefault("inputs", INPUTS)
    kwargs.setdefault("prior_inspection", PRIOR)
    kwargs.setdefault("admission", ADMISSION)
    return panel_receipt.annotate(value, **kwargs)


class ProvenRun(unittest.TestCase):
    def test_a_proven_run_keeps_success_and_carries_the_receipt(self):
        value = annotate(result())
        receipt = value["panel_receipt"]
        self.assertEqual(receipt["contract"], panel_receipt.CONTRACT)
        self.assertEqual(receipt["status"], "succeeded")
        self.assertEqual(receipt["problems"], [])
        self.assertTrue(value["success"])
        self.assertEqual(value["creation_route"], "resident_panel")
        self.assertEqual(receipt["profile"]["mode"], "candidate")
        self.assertEqual(receipt["quilt_id"], "quilt:new_7")
        self.assertTrue(receipt["geometry_check"]["quilt_is_new"])
        self.assertTrue(receipt["saved_file_reloaded_and_verified"])

    def test_the_bbox_is_marked_approximate_and_not_a_boundary_proof(self):
        receipt = annotate(result())["panel_receipt"]
        bbox = receipt["geometry_check"]["bbox"]
        self.assertTrue(bbox["approximate"])
        self.assertEqual(bbox["source"], "prosurface_data_approx")

    def test_a_measured_bbox_is_not_labelled_approximate(self):
        value = result()
        value["operations"][0]["geometry_check"]["bbox"]["source"] = "measured"
        receipt = annotate(value)["panel_receipt"]
        self.assertFalse(receipt["geometry_check"]["bbox"]["approximate"])

    def test_a_tree_route_result_is_left_untouched(self):
        value = result(operations=[{**op(), "creation_route": "element_tree"}])
        annotate(value, route="element_tree")
        self.assertNotIn("panel_receipt", value)
        self.assertNotIn("creation_route", value)
        self.assertTrue(value["success"])


class MeasuredGeometry(unittest.TestCase):
    """BUG-120 task 3: verified is a conclusion from facts, not a native flag."""

    def native_geometry(self, **overrides):
        check = {
            "verified": False,
            "quilt_id": 142,
            "feature_id": 136,
            "feature_quilt": 142,
            "quilt_is_new": True,
            "face_groups": [[137]],
            "face_count": 1,
            "area_mm2": 46555189.24528535,
            "closed": False,
            "boundary": {"open_edges": 4, "boundary_edges": 4, "joined_edges": 0},
            "bbox": {
                "xyz_min": [0.0, 0.0, 0.0],
                "xyz_max": [40.0, 20.0, 0.0],
                "source": "surface_data",
            },
            "measured_after_reload": True,
            "method": "quilt_record + surface_group_receipt on the saved reloaded model",
        }
        check.update(overrides)
        return check

    def value(self, **overrides):
        value = result()
        value["operations"][0]["quilt_id"] = 142
        value["operations"][0]["feature_id"] = 136
        value["operations"][0]["feature_quilt"] = 142
        value["operations"][0]["geometry_check"] = self.native_geometry(**overrides)
        return value

    def test_all_measured_facts_make_the_geometry_verified(self):
        receipt = annotate(self.value())["panel_receipt"]
        self.assertTrue(receipt["geometry_check"]["verified"])
        self.assertEqual(receipt["geometry_check"]["status"], "verified")
        self.assertEqual(receipt["geometry_check"]["reasons"], [])
        self.assertEqual(receipt["geometry_check"]["area_mm2"], 46555189.24528535)
        self.assertEqual(receipt["geometry_check"]["boundary"]["open_edges"], 4)
        self.assertTrue(receipt["geometry_check"]["quilt_is_new"])

    def test_a_missing_reload_reading_stays_unverified_with_a_reason(self):
        receipt = annotate(self.value(measured_after_reload=False))["panel_receipt"]
        check = receipt["geometry_check"]
        self.assertFalse(check["verified"])
        self.assertEqual(check["status"], "unverified")
        self.assertIn("after the saved model was reloaded", " ".join(check["reasons"]))
        # A missing reading is not a transaction failure by itself.
        fresh = annotate(self.value(measured_after_reload=False))
        self.assertTrue(fresh["success"])

    def test_an_unassociated_feature_quilt_stays_unverified(self):
        receipt = annotate(self.value(feature_quilt="quilt:old_3"))["panel_receipt"]
        check = receipt["geometry_check"]
        self.assertFalse(check["verified"])
        self.assertIn("feature/quilt association", " ".join(check["reasons"]))

    def test_a_measurement_error_is_reported_not_hidden(self):
        receipt = annotate(self.value(error="surface_group_receipt failed"))["panel_receipt"]
        self.assertFalse(receipt["geometry_check"]["verified"])
        self.assertIn("geometry measurement failed", " ".join(receipt["geometry_check"]["reasons"]))


class PreDialogRefusal(unittest.TestCase):
    """BUG-120 task 2: a refusal before the macro is not an unknown panel run."""

    def test_a_preopen_refusal_is_a_normal_failure(self):
        value = result(success=False, saved_file_reloaded_and_verified=False)
        operation = value["operations"][0]
        operation.pop("exit_observation")
        operation["panel_preopen"] = {
            "no_dialog_opened": True,
            "macro_submitted": False,
            "phase": "reading_references",
            "job_id": "job_1",
            "nonce": "n" * 32,
        }
        annotate(value)
        receipt = value["panel_receipt"]
        self.assertFalse(value["success"])
        self.assertNotIn("panel_execution_unconfirmed", value)
        self.assertTrue(receipt["panel_never_opened"])
        self.assertEqual(receipt["status"], "failed")
        self.assertIsNone(receipt["exit_observation"]["closed"])
        self.assertIn("never opened", receipt["exit_observation"]["reason"])

    def test_a_submitted_macro_does_not_use_the_preopen_claim(self):
        value = result(success=False)
        operation = value["operations"][0]
        operation.pop("exit_observation")
        operation["panel_preopen"] = {
            "no_dialog_opened": False,
            "macro_submitted": True,
            "phase": "macro_submitted",
        }
        annotate(value)
        self.assertFalse(value["panel_receipt"]["panel_never_opened"])
        self.assertTrue(value["panel_execution_unconfirmed"])


class UnprovenRuns(unittest.TestCase):
    def test_a_missing_exit_observation_is_unknown_and_not_successful(self):
        value = result()
        value["operations"][0].pop("exit_observation")
        annotate(value)
        receipt = value["panel_receipt"]
        self.assertFalse(value["success"])
        self.assertTrue(value["panel_execution_unconfirmed"])
        self.assertFalse(value["rollback_succeeded"])
        self.assertIsNone(receipt["exit_observation"]["closed"])
        self.assertFalse(receipt["exit_observation"]["supported"])
        self.assertEqual(receipt["status"], "failed")
        self.assertIn("panel_exit_unconfirmed", str(value["message"]))

    def test_an_unsupported_observer_cannot_report_a_close(self):
        value = result()
        value["operations"][0]["exit_observation"] = {
            "method": "none",
            "supported": False,
            "closed": True,
        }
        annotate(value)
        self.assertIsNone(value["panel_receipt"]["exit_observation"]["closed"])
        self.assertFalse(value["success"])

    def test_a_reused_quilt_is_not_this_runs_product(self):
        value = result()
        value["operations"][0]["quilt_id"] = "quilt:old_3"
        value["operations"][0]["feature_quilt"] = "quilt:old_3"
        annotate(value)
        receipt = value["panel_receipt"]
        self.assertFalse(receipt["geometry_check"]["quilt_is_new"])
        self.assertFalse(value["success"])
        self.assertIn("panel_quilt_not_new", str(receipt["problems"]))

    def test_a_recording_that_disagrees_with_the_request_fails(self):
        value = result()
        value["operations"][0]["selection_record"] = {"labels": ["b", "a"]}
        annotate(value)
        self.assertFalse(value["success"])
        self.assertIn("panel_selection_intent_mismatch", str(value["panel_receipt"]["problems"]))

    def test_an_unresolved_reference_fails(self):
        value = result()
        value["operations"][0]["selection_record"]["references"].append(
            {"label": "c", "missing": True}
        )
        annotate(value)
        self.assertFalse(value["success"])
        self.assertIn("panel_reference_missing", str(value["panel_receipt"]["problems"]))

    def test_multiple_or_empty_face_groups_fail(self):
        for groups in ([], ["group_1", "group_2"]):
            with self.subTest(groups=groups):
                value = result()
                value["operations"][0]["geometry_check"]["face_groups"] = groups
                annotate(value)
                self.assertFalse(value["success"])
                self.assertIn("panel_face_group_invalid", str(value["panel_receipt"]["problems"]))

    def test_a_zero_area_fails(self):
        value = result()
        value["operations"][0]["geometry_check"]["area_mm2"] = 0.0
        annotate(value)
        self.assertFalse(value["success"])
        self.assertIn("panel_area_not_positive", str(value["panel_receipt"]["problems"]))

    def test_a_feature_associated_with_another_quilt_fails(self):
        value = result()
        value["operations"][0]["feature_quilt"] = "quilt:old_3"
        annotate(value)
        self.assertFalse(value["success"])
        self.assertIn("panel_feature_not_associated", str(value["panel_receipt"]["problems"]))

    def test_a_claimed_tree_completion_is_downgraded(self):
        value = result()
        value["operations"][0]["kernel_completion"] = {"state": "supported"}
        annotate(value)
        self.assertEqual(value["operations"][0]["kernel_completion"]["state"], "not_applicable")
        self.assertIn("panel_kernel_completion_claimed", str(value["panel_receipt"]["problems"]))

    def test_an_unknown_prior_state_does_not_claim_the_quilt_is_new(self):
        value = annotate(result(), prior_inspection=None)
        self.assertIsNone(value["panel_receipt"]["geometry_check"]["quilt_is_new"])
        self.assertTrue(value["success"])


if __name__ == "__main__":
    unittest.main()
