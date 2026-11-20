"""B2/F11: a zero-material cut publishes reusable geometry evidence.

The native executor owns the measurements. This projection only validates the
reported shape: a missing, malformed or self-contradictory receipt degrades to
an explicit unavailable state and is never backfilled from the request.
"""

import unittest
from pathlib import Path

from creo_mechdog import operation_results
from creo_mechdog.cut_geometry_context import (
    annotate_cut_geometry_context,
    normalize_cut_geometry_context,
)


def context(**overrides):
    """A blind 5 mm XZ cut whose frame, axis and endpoints are recomputable."""
    origin = [0.0, 10.0, 0.0]
    normal = [0.0, -1.0, 0.0]
    axis = [0.0, 1.0, 0.0]
    receipt = {
        "status": "no_material_removed",
        "operation": "extrude",
        "mode": "cut",
        "sketch": "deck_cut",
        "direction": "negative",
        "direction_sign": -1,
        "sketch_frame": {
            "available": True,
            "source": "sketch_alias",
            "reason": None,
            "origin_mm": origin,
            "normal": normal,
            "u_axis": [1.0, 0.0, 0.0],
            "v_axis": [0.0, 0.0, 1.0],
            "surface_id": 42,
            "section_normal_sign": 1,
        },
        "extrude_depth": {
            "source": "feature_tree",
            "query_code": 0,
            "requested_depth_type": "blind",
            "requested_depth_mm": 5.0,
            "effective_depth_type": "blind",
            "effective_depth_mm": 5.0,
            "defaulted_fields": [],
        },
        "depth_interval_mm": {
            "available": True,
            "source": "feature_tree_and_sketch_alias",
            "reason": None,
            "axis": axis,
            "origin_mm": origin,
            "start_offset_mm": 0.0,
            "end_offset_mm": 5.0,
            "start_point_mm": origin,
            "end_point_mm": [0.0, 15.0, 0.0],
            "effective_depth_type": "blind",
            "effective_depth_mm": 5.0,
            "direction_sign": -1,
        },
        "volume_mm3": {
            "before": 1000.0,
            "after": 1000.0,
            "removed": 0.0,
            "zero_material_threshold": 1e-9,
        },
        "note": "derived from the created feature and the sketch frame",
    }
    receipt.update(overrides)
    return receipt


class CutGeometryProjectionTests(unittest.TestCase):
    def test_blind_cut_keeps_recomputable_origin_normal_and_depth_interval(self):
        entry = normalize_cut_geometry_context(context())
        self.assertTrue(entry["available"])
        self.assertEqual(entry["status"], "no_material_removed")
        self.assertEqual(entry["direction_sign"], -1)
        frame = entry["sketch_frame"]
        self.assertTrue(frame["available"])
        self.assertEqual(frame["origin_mm"], [0.0, 10.0, 0.0])
        self.assertEqual(frame["normal"], [0.0, -1.0, 0.0])
        interval = entry["depth_interval_mm"]
        self.assertTrue(interval["available"])
        self.assertEqual(interval["axis"], [0.0, 1.0, 0.0])
        self.assertEqual(interval["start_offset_mm"], 0.0)
        self.assertEqual(interval["end_offset_mm"], 5.0)
        self.assertEqual(interval["end_point_mm"], [0.0, 15.0, 0.0])
        self.assertEqual(entry["volume_mm3"]["removed"], 0.0)

    def test_missing_receipt_degrades_to_unavailable_without_invented_values(self):
        for block in (None, {}, "no_material_removed", 17):
            with self.subTest(block=block):
                entry = normalize_cut_geometry_context(block)
                self.assertFalse(entry["available"])
                self.assertEqual(entry["reason"], "cut_geometry_context_missing")
                self.assertIsNone(entry["sketch_frame"]["origin_mm"])
                self.assertIsNone(entry["depth_interval_mm"]["effective_depth_mm"])
                self.assertIsNone(entry["volume_mm3"]["before"])

    def test_unexpected_status_is_not_reported_as_a_measured_cut(self):
        entry = normalize_cut_geometry_context(context(status="material_removed"))
        self.assertFalse(entry["available"])
        self.assertEqual(entry["reason"], "unexpected_status")

    def test_unavailable_sketch_frame_keeps_its_reason_and_never_invents_an_origin(self):
        receipt = context(
            sketch_frame={
                "available": False,
                "source": "unavailable",
                "reason": "sketch_alias_unavailable",
            },
            depth_interval_mm={
                "available": False,
                "source": "unavailable",
                "reason": "sketch_frame_unavailable",
            },
        )
        entry = normalize_cut_geometry_context(receipt)
        frame = entry["sketch_frame"]
        self.assertFalse(frame["available"])
        self.assertEqual(frame["reason"], "sketch_alias_unavailable")
        self.assertIsNone(frame["origin_mm"])
        self.assertIsNone(frame["normal"])
        interval = entry["depth_interval_mm"]
        self.assertFalse(interval["available"])
        self.assertEqual(interval["reason"], "sketch_frame_unavailable")
        self.assertIsNone(interval["start_offset_mm"])

    def test_through_all_cut_never_gains_a_finite_depth_interval(self):
        receipt = context()
        receipt["extrude_depth"]["effective_depth_type"] = "through_all"
        receipt["extrude_depth"]["effective_depth_mm"] = None
        receipt["depth_interval_mm"] = {
            "available": False,
            "source": "unavailable",
            "reason": "through_all_has_no_finite_depth",
            "effective_depth_type": "through_all",
        }
        interval = normalize_cut_geometry_context(receipt)["depth_interval_mm"]
        self.assertFalse(interval["available"])
        self.assertEqual(interval["reason"], "through_all_has_no_finite_depth")
        self.assertIsNone(interval["effective_depth_mm"])

    def test_contradictory_axis_is_not_published_as_recomputable(self):
        receipt = context()
        receipt["depth_interval_mm"]["axis"] = [1.0, 0.0, 0.0]
        interval = normalize_cut_geometry_context(receipt)["depth_interval_mm"]
        self.assertFalse(interval["available"])
        self.assertEqual(interval["reason"], "depth_interval_inconsistent")

    def test_interval_span_must_equal_the_effective_depth(self):
        receipt = context()
        receipt["depth_interval_mm"]["end_offset_mm"] = 9.0
        interval = normalize_cut_geometry_context(receipt)["depth_interval_mm"]
        self.assertFalse(interval["available"])
        self.assertEqual(interval["reason"], "depth_interval_inconsistent")

    def test_endpoints_must_follow_the_reported_axis(self):
        receipt = context()
        receipt["depth_interval_mm"]["end_point_mm"] = [0.0, 0.0, 15.0]
        interval = normalize_cut_geometry_context(receipt)["depth_interval_mm"]
        self.assertFalse(interval["available"])
        self.assertEqual(interval["reason"], "depth_interval_inconsistent")

    def test_revolve_cut_keeps_the_frame_without_a_linear_depth(self):
        receipt = context(
            operation="revolve",
            direction="positive",
            direction_sign=1,
            sketch_frame={
                **context()["sketch_frame"],
                "normal": [0.0, 0.0, 1.0],
                "u_axis": [1.0, 0.0, 0.0],
                "v_axis": [0.0, 1.0, 0.0],
            },
            depth_interval_mm={
                "available": False,
                "source": "unavailable",
                "reason": "revolve_cut_has_no_linear_depth",
            },
        )
        entry = normalize_cut_geometry_context(receipt)
        self.assertEqual(entry["operation"], "revolve")
        self.assertEqual(entry["sketch_frame"]["normal"], [0.0, 0.0, 1.0])
        self.assertEqual(entry["depth_interval_mm"]["reason"], "revolve_cut_has_no_linear_depth")

    def test_annotation_normalizes_only_cut_records(self):
        receipt = context()
        receipt["depth_interval_mm"]["axis"] = [1.0, 0.0, 0.0]
        result = {
            "operations": [
                {"op": "sketch", "label": "deck", "succeeded": True},
                {"op": "extrude", "label": "deck_cut", "cut_geometry_context": receipt},
                {"op": "extrude", "label": "boss", "succeeded": True},
            ]
        }
        annotate_cut_geometry_context(result)
        self.assertNotIn("cut_geometry_context", result["operations"][0])
        self.assertFalse(
            result["operations"][1]["cut_geometry_context"]["depth_interval_mm"]["available"]
        )
        self.assertNotIn("cut_geometry_context", result["operations"][2])

    def test_native_result_projection_annotates_failed_cut_records(self):
        result = {
            "success": False,
            "operations": [{"op": "extrude", "index": 1, "label": "deck_cut", "succeeded": False}],
        }
        result["operations"][0]["cut_geometry_context"] = context()
        projected = operation_results.annotate_native_result(result, readonly=False)
        operation = projected["operations"][0]
        self.assertTrue(operation["cut_geometry_context"]["available"])
        self.assertEqual(
            operation["cut_geometry_context"]["sketch_frame"]["normal"], [0.0, -1.0, 0.0]
        )

    def test_compact_polling_and_budget_trim_keep_the_cut_context(self):
        from creo_mechdog import job_projection
        from creo_mechdog.operation_results import enforce_compact_budget

        record = {
            "op": "extrude",
            "index": 1,
            "label": "deck_cut",
            "succeeded": False,
            "execution_status": "failed",
            "effect_status": "rolled_back",
            "cut_geometry_context": context(),
        }
        compact = job_projection.compact_operation(record)
        self.assertIn("cut_geometry_context", compact)
        summary = {
            "status": "failed",
            "message": "Extrude cut removes no material",
            "result": {"operations": [compact]},
        }
        trimmed = enforce_compact_budget(summary, budget=1)
        self.assertIn("cut_geometry_context", trimmed["result"]["operations"][0])


class CutVolumeChangeTests(unittest.TestCase):
    """FEAT-051: the signed volume delta is named, not left to the caller."""

    @staticmethod
    def increased_context():
        """The reported 0.27.0 case: the 'cut' added material and failed."""
        before = 12514487.330518638715
        after = 12514490.389585861936
        return context(
            volume_mm3={
                "before": before,
                "after": after,
                "removed": before - after,
                "zero_material_threshold": abs(before) * 1e-12,
            }
        )

    def test_reported_negative_removal_is_named_material_increased(self):
        entry = normalize_cut_geometry_context(self.increased_context())
        change = entry["volume_change"]
        self.assertEqual(change["kind"], "material_increased")
        self.assertAlmostEqual(change["magnitude_mm3"], 3.059067223221, places=6)
        self.assertLess(change["signed_delta_mm3"], 0)
        self.assertFalse(change["within_zero_material_threshold"])
        self.assertIsNone(change["reason"])
        self.assertIn("3.059067", entry["diagnosis"])
        self.assertIn("increased", entry["diagnosis"])
        # The executor's own wording is preserved for compatibility.
        self.assertEqual(entry["status"], "no_material_removed")

    def test_negative_removal_is_never_reported_as_a_zero_material_no_op(self):
        entry = normalize_cut_geometry_context(self.increased_context())
        self.assertNotEqual(entry["volume_change"]["kind"], "no_material_removed")
        self.assertAlmostEqual(entry["volume_change"]["magnitude_mm3"], 3.059067223221, places=9)
        self.assertGreater(entry["volume_mm3"]["after"], entry["volume_mm3"]["before"])

    def test_normal_removal_is_named_material_removed_without_rewriting_status(self):
        receipt = context(
            volume_mm3={
                "before": 1000.0,
                "after": 812.5,
                "removed": 187.5,
                "zero_material_threshold": 1e-9,
            }
        )
        entry = normalize_cut_geometry_context(receipt)
        change = entry["volume_change"]
        self.assertEqual(change["kind"], "material_removed")
        self.assertEqual(change["magnitude_mm3"], 187.5)
        self.assertEqual(change["signed_delta_mm3"], 187.5)
        self.assertFalse(change["within_zero_material_threshold"])
        self.assertEqual(entry["status"], "no_material_removed")
        self.assertIsNone(entry["diagnosis"])

    def test_zero_delta_stays_inside_the_zero_material_band(self):
        entry = normalize_cut_geometry_context(context())
        change = entry["volume_change"]
        self.assertEqual(change["kind"], "no_material_removed")
        self.assertEqual(change["magnitude_mm3"], 0.0)
        self.assertTrue(change["within_zero_material_threshold"])
        self.assertIsNone(entry["diagnosis"])

    def test_tiny_removal_below_the_threshold_is_not_a_success(self):
        receipt = context(
            volume_mm3={
                "before": 1000.0,
                "after": 1000.0 - 1e-6,
                "removed": 1e-6,
                "zero_material_threshold": 1e-5,
            }
        )
        change = normalize_cut_geometry_context(receipt)["volume_change"]
        self.assertEqual(change["kind"], "no_material_removed")
        self.assertTrue(change["within_zero_material_threshold"])

    def test_missing_volume_reading_is_unmeasurable_and_not_a_success(self):
        for removed in (None, "3.05", True):
            with self.subTest(removed=removed):
                receipt = context(
                    volume_mm3={
                        "before": 1000.0,
                        "after": None,
                        "removed": removed,
                        "zero_material_threshold": 1e-9,
                    }
                )
                change = normalize_cut_geometry_context(receipt)["volume_change"]
                self.assertEqual(change["kind"], "unmeasurable")
                self.assertEqual(change["reason"], "volume_reading_unavailable")
                self.assertIsNone(change["signed_delta_mm3"])
                self.assertIsNone(change["magnitude_mm3"])

    def test_missing_receipt_always_carries_an_unmeasurable_classification(self):
        for block in (None, {}, "no_material_removed", 17):
            with self.subTest(block=block):
                change = normalize_cut_geometry_context(block)["volume_change"]
                self.assertEqual(change["kind"], "unmeasurable")
                self.assertEqual(change["reason"], "cut_geometry_context_missing")
                self.assertIsNone(change["within_zero_material_threshold"])

    def test_material_increase_survives_compact_polling_and_budget_trim(self):
        from creo_mechdog import job_projection
        from creo_mechdog.operation_results import enforce_compact_budget

        record = {
            "op": "extrude",
            "index": 1,
            "label": "deck_cut",
            "succeeded": False,
            "execution_status": "failed",
            "effect_status": "rolled_back",
            "cut_geometry_context": normalize_cut_geometry_context(self.increased_context()),
        }
        compact = job_projection.compact_operation(record)
        self.assertEqual(
            compact["cut_geometry_context"]["volume_change"]["kind"], "material_increased"
        )
        summary = {
            "status": "failed",
            "message": "Extrude cut removes no material",
            "result": {"operations": [compact]},
        }
        trimmed = enforce_compact_budget(summary, budget=1)
        operation = trimmed["result"]["operations"][0]
        self.assertEqual(
            operation["cut_geometry_context"]["volume_change"]["kind"], "material_increased"
        )
        self.assertEqual(operation["effect_status"], "rolled_back")


class NativeCutContextContractTests(unittest.TestCase):
    """The C++ failure path must publish, not merely describe, the geometry."""

    @staticmethod
    def native_source():
        return (Path(__file__).resolve().parents[2] / "native" / "generic.cpp").read_text(
            encoding="utf-8"
        )

    def test_zero_material_branch_stages_a_structured_context(self):
        source = self.native_source()
        start = source.index("static J cut_geometry_context(")
        end = source.index("static bool hole_plane_normal(", start)
        body = source[start:end]
        self.assertIn("cut_geometry_context", body)
        self.assertIn("stage_operation_result", body)
        self.assertIn("depth_interval_mm", body)
        self.assertIn("direction_sign", body)
        self.assertIn("removes no material", body)
        self.assertIn("cut_geometry_context", body.split("removes no material")[1])

    def test_named_plane_normals_keep_the_xz_negative_y_convention(self):
        source = self.native_source()
        start = source.index("static Frame sketch_frame(")
        end = source.index("// Read the actual selected support", start)
        self.assertIn("V{0, -1, 0}", source[start:end])


if __name__ == "__main__":
    unittest.main()
