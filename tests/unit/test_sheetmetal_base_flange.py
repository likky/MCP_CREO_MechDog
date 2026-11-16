"""DEV-089 T3: open polyline base-flange admission contract."""

import math
import unittest

from pydantic import ValidationError

from creo_mechdog.schema import SheetmetalBaseFlangeOp
from creo_mechdog.sheetmetal import (
    base_flange_create_problem,
    base_flange_expected_volume,
    base_flange_geometry,
    base_flange_geometry_problem,
    base_flange_names,
    base_flange_section_problem,
    y_factor_from_k,
)


def line(start, end, **overrides):
    entity = {"type": "line", "start": start, "end": end}
    entity.update(overrides)
    return entity


RIGHT_ANGLE = [line([0, 0, 0], [0, 0, 40]), line([0, 0, 40], [30, 0, 40])]


class BaseFlangeSectionTests(unittest.TestCase):
    def test_two_line_right_angle_is_a_candidate(self):
        self.assertIsNone(base_flange_section_problem(RIGHT_ANGLE))

    def test_single_line_stays_a_candidate(self):
        self.assertIsNone(base_flange_section_problem([line([0, 0, 0], [0, 0, 40])]))

    def test_construction_and_centerline_entities_are_ignored(self):
        entities = [
            {"type": "centerline", "start": [0, 0, 0], "end": [0, 0, 40]},
            {**line([0, 0, 0], [0, 0, 40]), "construction": True},
            *RIGHT_ANGLE,
        ]
        self.assertIsNone(base_flange_section_problem(entities))

    def test_more_than_the_first_batch_is_refused(self):
        chain = [
            line([0, 0, 0], [0, 0, 10]),
            line([0, 0, 10], [10, 0, 10]),
            line([10, 0, 10], [10, 0, 20]),
        ]
        self.assertIn("at most 2", base_flange_section_problem(chain))

    def test_non_line_entity_is_refused(self):
        entities = [line([0, 0, 0], [0, 0, 10]), {"type": "arc", "center": [0, 0, 0]}]
        self.assertIn("only straight lines", base_flange_section_problem(entities))

    def test_disconnected_chain_is_refused(self):
        entities = [line([0, 0, 0], [0, 0, 10]), line([0, 0, 11], [10, 0, 11])]
        self.assertIn("not connected", base_flange_section_problem(entities))

    def test_zero_length_segment_is_refused(self):
        entities = [line([0, 0, 0], [0, 0, 0])]
        self.assertIn("zero length", base_flange_section_problem(entities))

    def test_malformed_or_two_dimensional_points_are_refused(self):
        for entity in (
            line([0, 0, 0], [0, 0]),
            line([0, 0, 0], [0, 0, float("nan")]),
            line([0, 0, 0], [0, 0, True]),
        ):
            with self.subTest(entity=entity):
                self.assertIn("finite [x,y,z]", base_flange_section_problem([entity]) or "")

    def test_collinear_fold_back_is_refused(self):
        entities = [line([0, 0, 0], [0, 0, 10]), line([0, 0, 10], [0, 0, 5])]
        self.assertIn("collinear", base_flange_section_problem(entities) or "")

    def test_empty_section_is_refused(self):
        self.assertIn("no drawing entities", base_flange_section_problem([]) or "")


class YFactorConversionTests(unittest.TestCase):
    def test_k_half_maps_to_creo_y_factor(self):
        self.assertAlmostEqual(y_factor_from_k(0.5), 0.7853981634, places=9)

    def test_out_of_range_or_non_numeric_k_is_refused(self):
        for value in (0, -0.1, 1.0001, True, "0.5", float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                y_factor_from_k(value)

    def test_k_matches_the_documented_identity(self):
        for k in (0.33, 0.44, 0.5):
            self.assertAlmostEqual(y_factor_from_k(k), k * math.pi / 2, places=12)


class ReferenceCaseTests(unittest.TestCase):
    """0.24.1 feedback A1 / Arm2: 8 mm and 12 mm legs, t=2, R=0.7366, K=0.5, D2=20.

    The feedback gives the sketch (`x1=0 y1=8 -> 0,0 -> -12,0` on the right datum,
    xdir=(0,0,-1), ydir=(0,1,0)), the sheet values and the reference result
    (envelope `(-10,-2,-2,10,8,12)`, volume `792.323 mm3`). The section must be
    admissible as-is; the volume itself is still an unmet native target, not a
    contract expectation.
    """

    def test_feedback_arm2_section_is_admitted(self):
        chain = [line([0, 0, 8], [0, 0, 0]), line([0, 0, 0], [-12, 0, 0])]
        self.assertIsNone(base_flange_section_problem(chain))

    def test_feedback_arm2_y_factor(self):
        self.assertAlmostEqual(y_factor_from_k(0.5), 0.7853981633974483, places=12)


class ComposedGeometryTests(unittest.TestCase):
    """DEV-089 T3: the composed wall + flange contract (measured live, 2026-11-15)."""

    def test_reference_chain_gives_the_two_legs(self):
        chain = [line([0, 8, 0], [0, 0, 0]), line([0, 0, 0], [-12, 0, 0])]
        geometry = base_flange_geometry(chain)
        self.assertAlmostEqual(geometry["first_leg_mm"], 8.0, places=12)
        self.assertAlmostEqual(geometry["second_leg_mm"], 12.0, places=12)
        self.assertEqual(geometry["bend_angle_deg"], 90.0)

    def test_segments_must_keep_the_drawn_end_to_start_order(self):
        # The section contract (DEV-089 T3) reads the chain in the given order,
        # so a reversed second segment is refused instead of being reordered.
        problem = base_flange_geometry_problem(
            [line([0, 8, 0], [0, 0, 0]), line([-12, 0, 0], [0, 0, 0])]
        )
        self.assertIn("not connected", problem or "")

    def test_non_perpendicular_corner_is_refused(self):
        chain = [line([0, 0, 0], [0, 0, 8]), line([0, 0, 8], [-12, 0, 16])]
        problem = base_flange_geometry_problem(chain)
        self.assertIn("90 degree", problem or "")

    def test_collinear_chain_is_refused_by_the_section_contract(self):
        chain = [line([0, 0, 0], [0, 0, 8]), line([0, 0, 8], [0, 0, 20])]
        self.assertIn("collinear", base_flange_geometry_problem(chain) or "")

    def test_single_line_belongs_to_the_planar_wall(self):
        problem = base_flange_geometry_problem([line([0, 0, 0], [0, 0, 8])])
        self.assertIn("exactly two straight lines", problem or "")

    def test_expected_volume_matches_the_live_probes(self):
        # Job 99e106d2 (plate 8, flange height 12 -> 10 mm free leg) and job
        # d20737db (plate 10, flange height 14 -> 12 mm free leg) both measured
        # 0.0026 mm3 above this bound on Creo 12.4.0.0.
        for first_leg, second_leg, measured in ((8.0, 10.0, 690.1858), (10.0, 12.0, 850.1858)):
            with self.subTest(first_leg=first_leg, second_leg=second_leg):
                bound = base_flange_expected_volume(first_leg, second_leg, 20.0, 2.0, 0.7366)[
                    "total_mm3"
                ]
                self.assertLess(abs(bound - measured), 0.01)

    def test_expected_volume_is_the_straight_pair_minus_the_quarter_annulus(self):
        bound = base_flange_expected_volume(8.0, 12.0, 20.0, 2.0, 0.7366)
        self.assertAlmostEqual(bound["straight_mm3"], 800.0, places=9)
        expected_removed = (1 - math.pi / 4) * ((0.7366 + 2.0) ** 2 - 0.7366**2) * 20.0
        self.assertAlmostEqual(bound["bend_removed_mm3"], expected_removed, places=9)
        self.assertAlmostEqual(bound["total_mm3"], 800.0 - expected_removed, places=9)


class ComposedAdmissionTests(unittest.TestCase):
    """The composed operation owns three feature names and is still a first wall."""

    OPERATION = {"op": "sheetmetal_base_flange", "label": "base", "section": RIGHT_ANGLE}

    def test_three_names_are_declared(self):
        self.assertEqual(base_flange_names(self.OPERATION), ("base", "base_sk", "base_leg2"))

    def test_other_operations_declare_nothing(self):
        self.assertEqual(base_flange_names({"op": "sheetmetal_flange", "label": "x"}), ())

    def test_solid_model_is_refused(self):
        problem = base_flange_create_problem(
            {"model_type": "solid", "inspection_summary": {"has_solid": False}},
            {},
            self.OPERATION,
        )
        self.assertIn("requires an MCP sheetmetal model", problem or "")

    def test_model_with_geometry_is_refused(self):
        problem = base_flange_create_problem(
            {"model_type": "sheetmetal", "inspection_summary": {"has_solid": True}},
            {},
            self.OPERATION,
        )
        self.assertIn("already has geometry", problem or "")

    def test_taken_managed_name_is_refused(self):
        for taken in ("base", "base_sk", "base_leg2"):
            with self.subTest(taken=taken):
                problem = base_flange_create_problem(
                    {"model_type": "sheetmetal", "inspection_summary": {"has_solid": False}},
                    {taken: {"feature_id": 1}},
                    self.OPERATION,
                )
                self.assertIn("already exists", problem or "")

    def test_empty_sheetmetal_model_is_accepted(self):
        self.assertIsNone(
            base_flange_create_problem(
                {"model_type": "sheetmetal", "inspection_summary": {"has_solid": False}},
                {},
                self.OPERATION,
            )
        )


class ComposedSchemaTests(unittest.TestCase):
    """Admission of the composed operation itself, before a job exists."""

    REFERENCE = {
        "op": "sheetmetal_base_flange",
        "label": "t3_leg",
        "section": [line([0, 8, 0], [0, 0, 0]), line([0, 0, 0], [-12, 0, 0])],
        "width": 20.0,
        "thickness": 2.0,
        "radius": 0.7366,
        "k_factor": 0.5,
    }

    def test_reference_operation_is_admitted_with_defaults(self):
        operation = SheetmetalBaseFlangeOp.model_validate(self.REFERENCE)
        self.assertEqual(operation.plane, "XY")
        self.assertEqual(operation.origin, [0.0, 0.0])
        self.assertAlmostEqual(operation.k_factor, 0.5)

    def test_label_must_leave_room_for_both_suffixes(self):
        with self.assertRaises(ValidationError):
            SheetmetalBaseFlangeOp.model_validate({**self.REFERENCE, "label": "x" * 23})
        self.assertEqual(
            SheetmetalBaseFlangeOp.model_validate({**self.REFERENCE, "label": "x" * 22}).label,
            "x" * 22,
        )

    def test_k_factor_must_be_a_fraction(self):
        for value in (0, 1.5, -0.2):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                SheetmetalBaseFlangeOp.model_validate({**self.REFERENCE, "k_factor": value})

    def test_non_perpendicular_corner_is_refused_before_a_job(self):
        with self.assertRaises(ValidationError) as raised:
            SheetmetalBaseFlangeOp.model_validate(
                {
                    **self.REFERENCE,
                    "section": [line([0, 0, 0], [0, 0, 8]), line([0, 0, 8], [-12, 0, 16])],
                }
            )
        self.assertIn("90 degree", str(raised.exception))

    def test_single_line_is_refused_before_a_job(self):
        with self.assertRaises(ValidationError):
            SheetmetalBaseFlangeOp.model_validate(
                {**self.REFERENCE, "section": [line([0, 0, 0], [0, 0, 8])]}
            )

    def test_origin_must_be_one_sketch_point(self):
        with self.assertRaises(ValidationError):
            SheetmetalBaseFlangeOp.model_validate({**self.REFERENCE, "origin": [0.0]})

    def test_width_direction_assertion_is_optional_and_kept_verbatim(self):
        # BUG-129: the assertion says where the width must end up. It must not
        # rotate the first wall: plane/origin keep their existing meaning.
        operation = SheetmetalBaseFlangeOp.model_validate(self.REFERENCE)
        self.assertIsNone(operation.expected_width_direction_world)
        self.assertEqual(operation.width_direction_tolerance_deg, 0.5)
        asserted = SheetmetalBaseFlangeOp.model_validate(
            {
                **self.REFERENCE,
                "plane": "YZ",
                "expected_width_direction_world": [1, 0, 0],
                "width_direction_tolerance_deg": 0.25,
            }
        )
        self.assertEqual(asserted.plane, "YZ")
        self.assertEqual(asserted.origin, [0.0, 0.0])
        self.assertEqual(asserted.expected_width_direction_world, [1.0, 0.0, 0.0])
        self.assertEqual(asserted.width_direction_tolerance_deg, 0.25)

    def test_width_direction_must_be_a_finite_unit_vector(self):
        for value in (
            [0, 0, 0],
            [0, 0, 2],
            [0, 0, 0.5],
            [0, 0],
            [0, 0, "1"],
            [0, 0, float("nan")],
            [0, 0, float("inf")],
            [True, 0, 0],
        ):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                SheetmetalBaseFlangeOp.model_validate(
                    {**self.REFERENCE, "expected_width_direction_world": value}
                )

    def test_width_direction_tolerance_bounds(self):
        for value in (0, -1, 90.1, True):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                SheetmetalBaseFlangeOp.model_validate(
                    {**self.REFERENCE, "width_direction_tolerance_deg": value}
                )

    def test_yz_width_remains_local_v(self):
        # The assertion does not move the width from local v: plane YZ still
        # produces the same sketch origin and the same requested rectangle.
        without = SheetmetalBaseFlangeOp.model_validate(self.REFERENCE)
        with_assertion = SheetmetalBaseFlangeOp.model_validate(
            {**self.REFERENCE, "expected_width_direction_world": [1, 0, 0]}
        )
        for field in ("plane", "origin", "width", "thickness", "radius", "section"):
            self.assertEqual(getattr(with_assertion, field), getattr(without, field))

    def test_old_callers_without_the_assertion_stay_compatible(self):
        operation = SheetmetalBaseFlangeOp.model_validate(self.REFERENCE)
        dumped = operation.model_dump(exclude_none=True)
        self.assertNotIn("expected_width_direction_world", dumped)
        self.assertIn("plane", dumped)


if __name__ == "__main__":
    unittest.main()
