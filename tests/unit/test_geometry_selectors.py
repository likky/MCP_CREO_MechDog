"""DEV-089 T1: frozen geometric anchor selector contract."""

import unittest
from pathlib import Path

from creo_mechdog.geometry_selectors import (
    GEOMETRY_SELECTOR_KIND,
    validate_geometry_selector,
)
from creo_mechdog.schema import ChamferOp, RoundOp, SheetmetalFlangeOp, validate_operations

ROOT = Path(__file__).resolve().parents[2]


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

    def test_single_point_names_one_finite_edge(self):
        # FEAT-068 A0: a TXT midpoint is an anchor, not an endpoint pair.
        selector = {
            "kind": "geometry_selector",
            "target": "edge",
            "point_mm": [0, 0, 20],
            "tolerance_mm": 0.5,
        }
        normalized = validate_geometry_selector(selector)
        self.assertEqual(normalized["point_mm"], [0.0, 0.0, 20.0])
        self.assertNotIn("endpoints_mm", normalized)
        with self.assertRaises(ValueError):
            validate_geometry_selector({**selector, "tolerance_mm": 0})
        with self.assertRaises(ValueError):
            validate_geometry_selector({**selector, "axis": [0, 0, 1]})

    def test_circular_edge_needs_centre_and_radius_together(self):
        selector = {
            "kind": "geometry_selector",
            "target": "edge",
            "center_mm": [0, 0, 10],
            "radius_mm": 5,
            "axis": [0, 0, 1],
            "tolerance_mm": 0.2,
        }
        normalized = validate_geometry_selector(selector)
        self.assertEqual(normalized["center_mm"], [0.0, 0.0, 10.0])
        self.assertEqual(normalized["radius_mm"], 5)
        self.assertEqual(normalized["axis"], [0.0, 0.0, 1.0])
        for bad in (
            {key: value for key, value in selector.items() if key != "radius_mm"},
            {key: value for key, value in selector.items() if key != "center_mm"},
            {**selector, "radius_mm": 0},
            {**selector, "radius_mm": 1001},
            {**selector, "endpoints_mm": [[0, 0, 0], [0, 0, 1]]},
            {**selector, "axis": [0, 0, 2]},
        ):
            with self.subTest(selector=bad), self.assertRaises(ValueError):
                validate_geometry_selector(bad)
        # A point on the circle is an angular filter for split rims, not a
        # second way to name the centre.
        with_point = validate_geometry_selector({**selector, "point_mm": [5, 0, 10]})
        self.assertEqual(with_point["point_mm"], [5.0, 0.0, 10.0])
        self.assertEqual(with_point["center_mm"], [0.0, 0.0, 10.0])

    def test_endpoints_still_accept_an_optional_point_filter(self):
        normalized = validate_geometry_selector(
            edge_selector(point_mm=[0, 0, 20], tolerance_mm=0.5)
        )
        self.assertEqual(normalized["point_mm"], [0.0, 0.0, 20.0])
        self.assertEqual(len(normalized["endpoints_mm"]), 2)

    def test_round_and_flange_accept_single_point_edge_selectors(self):
        selector = {
            "kind": "geometry_selector",
            "target": "edge",
            "point_mm": [0, 0, 20],
            "tolerance_mm": 0.5,
        }
        accepted = RoundOp.model_validate(
            {"op": "round", "label": "r1", "size": 1, "references": [{"edge": selector}]}
        )
        self.assertEqual(accepted.references[0]["edge"]["point_mm"], [0.0, 0.0, 20.0])
        flange = SheetmetalFlangeOp.model_validate(
            {"op": "sheetmetal_flange", "label": "fl1", "edge": selector, "height": 10}
        )
        self.assertEqual(flange.edge["point_mm"], [0.0, 0.0, 20.0])


def coaxial_selector(**overrides):
    selector = surface_selector(axis=[0, 0, 1], radius_mm=27.5, center_mm=[0, 0, 0], coaxial="any")
    selector.update(overrides)
    return selector


class CoaxialSelectorContractTests(unittest.TestCase):
    """BUG-132: coaxial='any' is an explicit insert/concentric relaxation."""

    def test_coaxial_any_is_kept_and_needs_a_cylinder_filter(self):
        normalized = validate_geometry_selector(coaxial_selector())
        self.assertEqual(normalized["coaxial"], "any")
        self.assertEqual(normalized["radius_mm"], 27.5)
        for bad in (
            surface_selector(coaxial="any"),
            coaxial_selector(coaxial="nearest"),
            edge_selector(coaxial="any"),
        ):
            with self.subTest(selector=bad), self.assertRaises(ValueError):
                validate_geometry_selector(bad)

    def test_feature_anchors_refuse_coaxial_any(self):
        with self.assertRaises(ValueError):
            RoundOp.model_validate(
                {
                    "op": "round",
                    "label": "r1",
                    "size": 1,
                    "references": [{"surfaces": [coaxial_selector()]}],
                }
            )
        with self.assertRaises(ValueError):
            ChamferOp.model_validate(
                {
                    "op": "chamfer",
                    "label": "c1",
                    "size": 1,
                    "references": [{"edge": edge_selector()}],
                    "chamfer_type": "distance_angle",
                    "angle_deg": 45,
                    "angle_reference": coaxial_selector(),
                }
            )

    def test_plan_walk_refuses_coaxial_outside_constraints(self):
        with self.assertRaises(ValueError):
            validate_operations(
                [
                    {
                        "op": "round",
                        "label": "r1",
                        "size": 1,
                        "references": [{"surfaces": [coaxial_selector()]}],
                    }
                ]
            )


class BUG132NativeDiagnosisSourceTests(unittest.TestCase):
    """The native refusal text is the user-facing diagnosis; keep it typed."""

    def test_surface_error_lists_ids_with_types_and_type_mismatch(self):
        source = (ROOT / "native" / "geometry_selectors.cpp").read_text(encoding="utf-8")
        self.assertIn("selector_surface_list", source)
        self.assertIn("type_rejected_ids", source)
        self.assertIn("type_rejected_types", source)
        self.assertIn("it is not a surface-type", source)
        self.assertIn("coaxial_any", source)

    def test_constraint_type_message_separates_radius_from_type(self):
        source = (ROOT / "native" / "advanced.cpp").read_text(encoding="utf-8")
        self.assertIn("radius_mm was supplied", source)
        self.assertIn("not a surface-type filter", source)
        self.assertIn("coaxial:'any'", source)


if __name__ == "__main__":
    unittest.main()
