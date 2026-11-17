"""FEAT-069/P1: offline expansion of an extrude.region into a derived sketch."""

import unittest
from pathlib import Path

from pydantic import ValidationError

from creo_mechdog.schema import ExtrudeOp, SketchOp, validate_operations
from creo_mechdog.sketch_regions import (
    adapt_region_extrudes,
    entity_endpoints,
    validate_frame,
)

ROOT = Path(__file__).resolve().parents[2]

LEFT = "(0,0|10,0;10,0|10,10;10,10|0,10;0,10|0,0)"
RIGHT = "(10,0|20,0;20,0|20,10;20,10|10,10;10,10|10,0)"
#: The same left loop under the TXT DTM-right frame (u -> -Z, v -> +Y).
LEFT_ARMT = "(0,0|0,-10;0,-10|10,-10;10,-10|10,0;0,0|10,0)"


def line(name, start, end):
    return {"type": "line", "name": name, "start": start, "end": end}


def split_rectangle(label="arm7_s7", **overrides):
    sketch = {
        "op": "sketch",
        "label": label,
        "plane": "YZ",
        "offset": 0,
        "entities": [
            line("bottom_a", [0, 0], [10, 0]),
            line("bottom_b", [10, 0], [20, 0]),
            line("right", [20, 0], [20, 10]),
            line("top_b", [20, 10], [10, 10]),
            line("top_a", [10, 10], [0, 10]),
            line("left", [0, 10], [0, 0]),
            line("mid", [10, 0], [10, 10]),
        ],
    }
    sketch.update(overrides)
    return sketch


def cut(label="cut_left", sketch="arm7_s7", signature=LEFT, **overrides):
    operation = {
        "op": "extrude",
        "label": label,
        "sketch": sketch,
        "region": {"signature_yz_mm": signature, "tolerance_mm": 1e-3},
        "mode": "cut",
        "depth": 3,
    }
    operation.update(overrides)
    return operation


class RegionExpansionTests(unittest.TestCase):
    def test_left_region_copies_exactly_its_four_entities(self):
        result, records = adapt_region_extrudes([split_rectangle(), cut()])
        self.assertEqual([op["op"] for op in result], ["sketch", "sketch", "extrude"])
        derived, extrude = result[1], result[2]
        self.assertRegex(derived["label"], r"^arm7_s7_r[0-9a-f]{8}$")
        self.assertEqual(
            [entity["name"] for entity in derived["entities"]],
            ["bottom_a", "top_a", "left", "mid"],
        )
        self.assertEqual(extrude["sketch"], derived["label"])
        self.assertNotIn("region", extrude)
        # The source keeps every entity; the derivation never edits it.
        self.assertEqual(len(result[0]["entities"]), 7)
        self.assertEqual(records[0]["source_sketch"], "arm7_s7")
        self.assertEqual(records[0]["derived_sketch"], derived["label"])
        self.assertEqual(records[0]["segment_count"], 4)

    def test_right_region_is_a_different_loop(self):
        result, _ = adapt_region_extrudes([split_rectangle(), cut(signature=RIGHT)])
        derived = result[1]
        self.assertEqual(
            [entity["name"] for entity in derived["entities"]],
            ["bottom_b", "right", "top_b", "mid"],
        )

    def test_explicit_txt_frame_maps_local_uv_to_global_yz(self):
        frame = {
            "origin": [1.5, 0, 0],
            "xdir": [0, 0, -1],
            "ydir": [0, 1, 0],
        }
        result, records = adapt_region_extrudes(
            [
                split_rectangle(),
                cut(signature=LEFT_ARMT, region={"signature_yz_mm": LEFT_ARMT, "frame": frame}),
            ]
        )
        self.assertEqual(records[0]["segment_count"], 4)
        self.assertEqual(result[2]["sketch"], result[1]["label"])

    def test_derived_plan_passes_the_public_schema(self):
        result, _ = adapt_region_extrudes([split_rectangle(), cut()])
        validated = validate_operations(result)
        self.assertEqual(validated[1]["op"], "sketch")
        self.assertEqual(validated[2]["sketch"], validated[1]["label"])
        self.assertNotIn("region", validated[2])

    def test_two_extrudes_of_one_region_share_one_derived_sketch(self):
        result, records = adapt_region_extrudes(
            [
                split_rectangle(),
                cut(label="cut_left", signature=LEFT),
                cut(label="cut_left_again", signature=LEFT),
            ]
        )
        self.assertEqual([op["op"] for op in result], ["sketch", "sketch", "extrude", "extrude"])
        self.assertEqual(len(records), 1)
        self.assertEqual(result[2]["sketch"], result[1]["label"])
        self.assertEqual(result[3]["sketch"], result[1]["label"])

    def test_a_signature_that_matches_nothing_is_refused(self):
        with self.assertRaises(ValueError) as raised:
            adapt_region_extrudes(
                [
                    split_rectangle(),
                    cut(signature="(0,0|1,0;1,0|1,1;1,1|0,1;0,1|0,0)"),
                ]
            )
        self.assertIn("matched none", str(raised.exception))

    def test_a_sketch_that_still_needs_dimensions_is_refused(self):
        sketch = split_rectangle(
            dimensions=[
                {
                    "kind": "distance",
                    "references": [
                        {"entity": "bottom_a", "point": "start"},
                        {"entity": "bottom_a", "point": "end"},
                    ],
                    "value": 10,
                }
            ]
        )
        with self.assertRaises(ValueError) as raised:
            adapt_region_extrudes([sketch, cut()])
        self.assertIn("carries dimensions", str(raised.exception))

    def test_a_missing_source_sketch_is_refused(self):
        with self.assertRaises(ValueError) as raised:
            adapt_region_extrudes([cut(sketch="not_there")])
        self.assertIn("not an earlier sketch", str(raised.exception))

    def test_a_source_after_the_extrude_is_not_accepted(self):
        with self.assertRaises(ValueError) as raised:
            adapt_region_extrudes([cut(), split_rectangle()])
        self.assertIn("not an earlier sketch", str(raised.exception))

    def test_a_numeric_source_reference_is_refused(self):
        with self.assertRaises(ValueError) as raised:
            adapt_region_extrudes([split_rectangle(), cut(sketch=12)])
        self.assertIn("does not name its source sketch", str(raised.exception))

    def test_operations_without_a_region_pass_through_unchanged(self):
        plain = {"op": "extrude", "label": "plain", "sketch": "arm7_s7", "depth": 3}
        result, records = adapt_region_extrudes([split_rectangle(), plain])
        self.assertEqual(result[1], plain)
        self.assertEqual(records, [])

    def test_a_dict_surface_extrude_with_a_region_is_refused(self):
        # The dict path reaches the adapter before schema validation, so the
        # adapter itself must keep the solid-only rule.
        with self.assertRaises(ValueError) as raised:
            adapt_region_extrudes([split_rectangle(), cut(mode="surface")])
        self.assertIn("surface extrude", str(raised.exception))

    def test_validated_models_are_expanded_too(self):
        sketch = SketchOp.model_validate(split_rectangle())
        extrude = ExtrudeOp.model_validate(cut())
        result, records = adapt_region_extrudes([sketch, extrude])
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[1], dict)
        self.assertNotIn("region", result[2])
        self.assertEqual(len(records), 1)


class EntityEndpointTests(unittest.TestCase):
    def test_lines_and_open_polylines_use_their_two_ends(self):
        self.assertEqual(
            entity_endpoints(line("l", [0, 0], [4, 0])),
            ([0, 0], [4, 0]),
        )
        self.assertEqual(
            entity_endpoints({"type": "polyline", "name": "p", "points": [[0, 0], [1, 1], [2, 0]]}),
            ([0, 0], [2, 0]),
        )

    def test_arc_endpoints_follow_the_angles(self):
        first, second = entity_endpoints(
            {
                "type": "arc",
                "name": "a",
                "center": [0, 0],
                "radius": 10,
                "start_angle": 0,
                "end_angle": 90,
            }
        )
        self.assertAlmostEqual(first[0], 10.0)
        self.assertAlmostEqual(first[1], 0.0)
        self.assertAlmostEqual(second[0], 0.0)
        self.assertAlmostEqual(second[1], 10.0)

    def test_a_clamped_b_spline_ends_at_its_end_control_points(self):
        self.assertEqual(
            entity_endpoints(
                {
                    "type": "b_spline",
                    "name": "b",
                    "degree": 2,
                    "control_points": [[0, 0], [5, 5], [10, 0]],
                }
            ),
            ([0, 0], [10, 0]),
        )

    def test_closed_and_construction_shapes_have_no_boundary_endpoints(self):
        for entity in (
            {"type": "circle", "name": "c", "center": [0, 0], "radius": 5},
            {"type": "rectangle", "name": "r", "min": [0, 0], "max": [1, 1]},
            {
                "type": "polyline",
                "name": "closed",
                "points": [[0, 0], [1, 0], [0, 1]],
                "closed": True,
            },
            {"type": "line", "name": "ref", "start": [0, 0], "end": [1, 0], "construction": True},
        ):
            with self.subTest(entity["name"]):
                self.assertIsNone(entity_endpoints(entity))


class FrameValidationTests(unittest.TestCase):
    def test_a_frame_outside_the_yz_plane_is_refused(self):
        with self.assertRaises(ValueError) as raised:
            validate_frame({"origin": [0, 0, 0], "xdir": [1, 0, 0], "ydir": [0, 1, 0]})
        self.assertIn("YZ plane", str(raised.exception))

    def test_non_unit_axes_are_refused(self):
        with self.assertRaises(ValueError) as raised:
            validate_frame({"origin": [0, 0, 0], "xdir": [0, 0, 2], "ydir": [0, 1, 0]})
        self.assertIn("unit vector", str(raised.exception))

    def test_a_named_non_yz_plane_needs_an_explicit_frame(self):
        with self.assertRaises(ValueError) as raised:
            adapt_region_extrudes([split_rectangle(plane="XY"), cut()])
        self.assertIn("explicitly", str(raised.exception))


class ExtrudeRegionSchemaTests(unittest.TestCase):
    BASE = {
        "op": "extrude",
        "label": "cut_left",
        "sketch": "arm7_s7",
        "mode": "cut",
        "depth": 3,
    }

    def test_region_is_optional_and_validated(self):
        operation = ExtrudeOp.model_validate({**self.BASE, "region": {"signature_yz_mm": LEFT}})
        self.assertEqual(operation.region.signature_yz_mm, LEFT)
        self.assertIsNone(ExtrudeOp.model_validate(self.BASE).region)

    def test_an_unparseable_signature_is_refused_before_a_job(self):
        with self.assertRaises(ValidationError) as raised:
            ExtrudeOp.model_validate({**self.BASE, "region": {"signature_yz_mm": "region=3"}})
        self.assertIn("signature", str(raised.exception))

    def test_region_needs_a_label_reference(self):
        with self.assertRaises(ValidationError) as raised:
            ExtrudeOp.model_validate(
                {**self.BASE, "sketch": 7, "region": {"signature_yz_mm": LEFT}}
            )
        self.assertIn("label string", str(raised.exception))

    def test_region_is_not_a_surface_extrude(self):
        with self.assertRaises(ValidationError) as raised:
            ExtrudeOp.model_validate(
                {**self.BASE, "mode": "surface", "region": {"signature_yz_mm": LEFT}}
            )
        self.assertIn("surface extrude", str(raised.exception))


class RegionAdapterWiringTest(unittest.TestCase):
    def test_the_executor_expands_regions_before_admission(self):
        source = (ROOT / "generic_bridge.py").read_text(encoding="utf-8")
        self.assertIn("from creo_mechdog.sketch_regions import adapt_region_extrudes", source)
        call = source.index("adapt_region_extrudes(operations)")
        admission = source.index("operations = validate_operations(operations)", call)
        self.assertGreater(admission, call)
        self.assertIn('manifest["region_adaptation"] = region_adaptation', source)


if __name__ == "__main__":
    unittest.main()
