"""DEV-089 T1: frozen geometric anchor selector contract."""

import unittest

from creo_mechdog.geometry_selectors import (
    GEOMETRY_SELECTOR_KIND,
    validate_geometry_selector,
)
from creo_mechdog.schema import RoundOp, SheetmetalFlangeOp, validate_operations


def edge_selector(**overrides):
    selector = {
        "kind": "geometry_selector",
        "target": "edge",
        "endpoints_mm": [[0, 0, 0], [0, 0, 40]],
        "tolerance_mm": 1e-3,
    }
    selector.update(overrides)
    return selector


def surface_selector(**overrides):
    selector = {
        "kind": "geometry_selector",
        "target": "surface",
        "axis": [0, 0, 1],
        "points_mm": [[10, 0, 1]],
        "tolerance_mm": 1e-3,
    }
    selector.update(overrides)
    return selector


class GeometrySelectorContractTests(unittest.TestCase):
    def test_edge_selector_freezes_explicit_space_and_tolerance(self):
        normalized = validate_geometry_selector(edge_selector())
        self.assertEqual(normalized["kind"], GEOMETRY_SELECTOR_KIND)
        self.assertEqual(normalized["target"], "edge")
        self.assertEqual(normalized["coordinate_space"], "model")
        self.assertEqual(normalized["tolerance_mm"], 1e-3)
        self.assertEqual(normalized["axis_tolerance_deg"], 0.5)
        self.assertEqual(normalized["endpoints_mm"], [[0.0, 0.0, 0.0], [0.0, 0.0, 40.0]])

    def test_assembly_space_is_kept_for_occurrence_resolution(self):
        normalized = validate_geometry_selector(edge_selector(coordinate_space="assembly"))
        self.assertEqual(normalized["coordinate_space"], "assembly")

    def test_surface_selector_keeps_joint_filters(self):
        normalized = validate_geometry_selector(
            surface_selector(radius_mm=5, center_mm=[0, 0, 7], axis_tolerance_deg=0.25)
        )
        self.assertEqual(normalized["radius_mm"], 5)
        self.assertEqual(normalized["center_mm"], [0.0, 0.0, 7.0])
        self.assertEqual(normalized["axis_tolerance_deg"], 0.25)

    def test_unknown_key_and_missing_tolerance_are_refused(self):
        for bad in (
            edge_selector(tolerance=1e-3),
            edge_selector(tolerance_mm=0),
            edge_selector(tolerance_mm=-1),
            edge_selector(tolerance_mm=True),
            edge_selector(tolerance_mm=float("nan")),
            edge_selector(tolerance_mm=float("inf")),
            edge_selector(tolerance_mm=1001),
            edge_selector(coordinate_space="part"),
        ):
            with self.subTest(selector=bad), self.assertRaises(ValueError):
                validate_geometry_selector(bad)

    def test_edge_shape_is_endpoints_only(self):
        for bad in (
            edge_selector(endpoints_mm=[[0, 0, 0]]),
            edge_selector(endpoints_mm=[[0, 0, 0], [0, 0, 0]]),
            edge_selector(endpoints_mm=[[0, 0, 0], [0, 0, "40"]]),
            edge_selector(radius_mm=5),
            edge_selector(axis=[0, 0, 1]),
            edge_selector(points_mm=[[0, 0, 0]]),
        ):
            with self.subTest(selector=bad), self.assertRaises(ValueError):
                validate_geometry_selector(bad)

    def test_surface_needs_a_real_filter(self):
        with self.assertRaises(ValueError):
            validate_geometry_selector(
                {"kind": "geometry_selector", "target": "surface", "tolerance_mm": 1e-3}
            )
        with self.assertRaises(ValueError):
            validate_geometry_selector(surface_selector(axis=[0, 0, 2]))
        without_axis = {
            "kind": "geometry_selector",
            "target": "surface",
            "radius_mm": 5,
            "tolerance_mm": 1e-3,
        }
        with self.assertRaises(ValueError):
            validate_geometry_selector(without_axis)
        with self.assertRaises(ValueError):
            validate_geometry_selector(surface_selector(endpoints_mm=[[0, 0, 0], [0, 0, 1]]))
        with self.assertRaises(ValueError):
            validate_geometry_selector(surface_selector(points_mm=[]))
        with self.assertRaises(ValueError):
            validate_geometry_selector(surface_selector(points_mm=[[0, 0, 0]] * 9))

    def test_round_accepts_selector_and_rejects_malformed_one(self):
        accepted = RoundOp.model_validate(
            {
                "op": "round",
                "label": "r1",
                "size": 1,
                "references": [{"edge": edge_selector()}],
            }
        )
        self.assertEqual(accepted.references[0]["edge"]["target"], "edge")
        with self.assertRaises(ValueError):
            RoundOp.model_validate(
                {
                    "op": "round",
                    "label": "r1",
                    "size": 1,
                    "references": [{"edge": edge_selector(tolerance_mm=-1)}],
                }
            )

    def test_plan_normalization_keeps_selector(self):
        validated = validate_operations(
            [
                {
                    "op": "sheetmetal_flange",
                    "label": "fl1",
                    "edge": edge_selector(),
                    "height": 10,
                }
            ]
        )
        self.assertEqual(validated[0]["edge"]["kind"], GEOMETRY_SELECTOR_KIND)
        self.assertEqual(validated[0]["edge"]["coordinate_space"], "model")

    def test_flange_refuses_surface_selector(self):
        with self.assertRaises(ValueError):
            SheetmetalFlangeOp.model_validate(
                {
                    "op": "sheetmetal_flange",
                    "label": "fl1",
                    "edge": surface_selector(),
                    "height": 10,
                }
            )


if __name__ == "__main__":
    unittest.main()
