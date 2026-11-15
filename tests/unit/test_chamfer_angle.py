"""DEV-089 T6a: distance-angle chamfer admission contract."""

import unittest

from pydantic import ValidationError

from creo_mechdog.schema import ChamferOp, RoundOp, validate_operations

EDGE = [{"edge": {"kind": "edge", "id": 7}}]
FACE = {"kind": "surface", "id": 12}


def payload(**overrides):
    base = {
        "op": "chamfer",
        "label": "break_edge",
        "size": 2.0,
        "references": EDGE,
        "chamfer_type": "distance_angle",
        "angle_deg": 70.0,
        "angle_reference": FACE,
    }
    base.update(overrides)
    return base


class ChamferAngleContractTests(unittest.TestCase):
    def test_distance_angle_payload_is_kept(self):
        model = ChamferOp.model_validate(payload())
        self.assertEqual(model.chamfer_type, "distance_angle")
        self.assertEqual(model.angle_deg, 70.0)
        self.assertEqual(model.angle_reference, FACE)
        self.assertEqual(model.size, 2.0)

    def test_equal_distance_stays_the_historical_payload(self):
        model = ChamferOp.model_validate(
            {"op": "chamfer", "label": "break_edge", "distance": 1.5, "references": EDGE}
        )
        self.assertEqual(model.chamfer_type, "equal_distance")
        self.assertEqual(model.size, 1.5)
        self.assertIsNone(model.angle_deg)
        self.assertEqual(
            validate_operations(
                [{"op": "chamfer", "label": "break_edge", "size": 1.5, "references": EDGE}]
            ),
            [{"op": "chamfer", "label": "break_edge", "size": 1.5, "references": EDGE}],
        )

    def test_angle_fields_require_the_distance_angle_mode(self):
        for overrides in (
            {"chamfer_type": "equal_distance"},
            {"chamfer_type": "equal_distance", "angle_deg": 30.0},
            {"chamfer_type": "equal_distance", "angle_reference": FACE},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValidationError, "distance_angle"):
                    ChamferOp.model_validate(payload(**overrides))

    def test_distance_angle_requires_angle_and_reference(self):
        missing_angle = payload()
        missing_angle.pop("angle_deg")
        with self.assertRaisesRegex(ValidationError, "angle_deg"):
            ChamferOp.model_validate(missing_angle)
        missing_reference = payload()
        missing_reference.pop("angle_reference")
        with self.assertRaisesRegex(ValidationError, "angle_reference"):
            ChamferOp.model_validate(missing_reference)

    def test_angle_bounds_are_rejected(self):
        for value in (0.0, -10.0, 180.0, 200.0):
            with self.subTest(angle_deg=value):
                with self.assertRaises(ValidationError):
                    ChamferOp.model_validate(payload(angle_deg=value))
        for value in (True, "70", None):
            with self.subTest(angle_deg=value):
                with self.assertRaises(ValidationError):
                    ChamferOp.model_validate(payload(angle_deg=value))

    def test_angle_reference_rejects_a_non_surface_selector(self):
        with self.assertRaisesRegex(ValidationError, "target a surface"):
            ChamferOp.model_validate(
                payload(
                    angle_reference={
                        "kind": "geometry_selector",
                        "target": "edge",
                        "endpoints_mm": [[0, 0, 0], [0, 0, 10]],
                        "tolerance_mm": 0.001,
                    }
                )
            )

    def test_radius_is_not_a_chamfer_field(self):
        with self.assertRaisesRegex(ValidationError, "does not accept 'radius'"):
            ChamferOp.model_validate(payload(radius=2.0))
        with self.assertRaisesRegex(ValidationError, "does not accept 'distance'"):
            RoundOp.model_validate(
                {"op": "round", "label": "r", "distance": 2.0, "references": EDGE}
            )

    def test_plan_validation_normalizes_references(self):
        validated = validate_operations([payload()])
        # chamfer_type is an admission alias: the native payload carries the
        # angle fields and stays byte-identical to the old size-only request
        # when the chamfer is equal-distance.
        self.assertNotIn("chamfer_type", validated[0])
        self.assertEqual(validated[0]["angle_deg"], 70.0)
        self.assertEqual(validated[0]["angle_reference"], FACE)


if __name__ == "__main__":
    unittest.main()
