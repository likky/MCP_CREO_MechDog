"""DEV-089 T2: assembly constraint offset semantics (BUG-041)."""

import unittest

from creo_mechdog.failure_context import annotate_failed_operation
from creo_mechdog.job_projection import ASSEMBLY_POSE_KEYS, compact_operation
from creo_mechdog.operation_results import enforce_compact_budget
from creo_mechdog.schema import (
    AssembleOp,
    AssemblyConstraint,
    ComponentConstraintsOp,
    validate_operations,
)


def constraint(constraint_type, **overrides):
    row = {
        "type": constraint_type,
        "assembly_reference": {"kind": "surface", "id": 41},
        "component_reference": {"kind": "surface", "id": 42},
    }
    row.update(overrides)
    return row


class AssemblyConstraintOffsetTests(unittest.TestCase):
    def test_offset_on_offsetless_types_is_refused(self):
        for constraint_type in ("mate", "align", "insert", "csys"):
            for offset in (0.001, -12.5, 25):
                with (
                    self.subTest(type=constraint_type, offset=offset),
                    self.assertRaises(ValueError),
                ):
                    AssemblyConstraint.model_validate(constraint(constraint_type, offset=offset))

    def test_zero_offset_stays_accepted(self):
        for constraint_type in ("mate", "align", "insert", "csys"):
            with self.subTest(type=constraint_type):
                checked = AssemblyConstraint.model_validate(constraint(constraint_type, offset=0))
                self.assertEqual(checked.offset, 0)

    def test_offset_types_keep_signed_offsets(self):
        for constraint_type in ("mate_offset", "align_offset"):
            for offset in (0.0, 12.5, -3.25):
                with self.subTest(type=constraint_type, offset=offset):
                    checked = AssemblyConstraint.model_validate(
                        constraint(constraint_type, offset=offset)
                    )
                    self.assertEqual(checked.offset, offset)

    def test_plan_validation_refuses_before_dispatch(self):
        with self.assertRaises(ValueError):
            validate_operations(
                [
                    {
                        "op": "component_constraints",
                        "component": "pin",
                        "constraints": [constraint("mate", offset=25)],
                    }
                ]
            )

    def test_component_constraints_keeps_offset_types(self):
        accepted = ComponentConstraintsOp.model_validate(
            {
                "op": "component_constraints",
                "component": "pin",
                "constraints": [
                    constraint("mate_offset", offset=25),
                    constraint("align_offset", offset=-20),
                ],
            }
        )
        self.assertEqual([row.offset for row in accepted.constraints], [25, -20])


class SemanticRelationshipTests(unittest.TestCase):
    """DEV-089 T5: relationship words map to proven types or are refused."""

    def test_coincident_maps_to_mate_for_faces(self):
        for reference in (
            {"kind": "surface", "id": 41},
            {"kind": "plane", "id": 41},
            {"kind": "datum_plane", "axis": "z"},
        ):
            with self.subTest(reference=reference):
                checked = AssemblyConstraint.model_validate(
                    {
                        "type": "coincident",
                        "assembly_reference": reference,
                        "component_reference": dict(reference),
                    }
                )
                self.assertEqual(checked.type, "mate")

    def test_coincident_on_an_axis_is_refused(self):
        with self.assertRaises(ValueError):
            AssemblyConstraint.model_validate(
                {
                    "type": "coincident",
                    "assembly_reference": {"kind": "axis", "id": 3},
                    "component_reference": {"kind": "axis", "id": 4},
                }
            )

    def test_concentric_maps_to_insert_for_cylindrical_surfaces(self):
        checked = AssemblyConstraint.model_validate(
            {
                "type": "concentric",
                "assembly_reference": {"kind": "surface", "id": 41},
                "component_reference": {"kind": "surface", "id": 42},
            }
        )
        self.assertEqual(checked.type, "insert")

    def test_concentric_rejects_planar_and_axis_references(self):
        for reference in (
            {"kind": "datum_plane", "axis": "z"},
            {"kind": "axis", "id": 3},
        ):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                AssemblyConstraint.model_validate(
                    {
                        "type": "concentric",
                        "assembly_reference": reference,
                        "component_reference": reference,
                    }
                )

    def test_unverified_relationships_are_refused_with_the_gap(self):
        for relationship in ("parallel", "distance"):
            with self.subTest(relationship=relationship), self.assertRaises(ValueError):
                AssemblyConstraint.model_validate(
                    {
                        "type": relationship,
                        "assembly_reference": {"kind": "surface", "id": 41},
                        "component_reference": {"kind": "surface", "id": 42},
                    }
                )

    def test_coincident_with_offset_is_refused_as_mate(self):
        with self.assertRaises(ValueError):
            AssemblyConstraint.model_validate(
                {
                    "type": "coincident",
                    "assembly_reference": {"kind": "surface", "id": 41},
                    "component_reference": {"kind": "surface", "id": 42},
                    "offset": 5,
                }
            )

    def test_plan_normalization_keeps_the_proven_type(self):
        checked = validate_operations(
            [
                {
                    "op": "component_constraints",
                    "component": "pin",
                    "constraints": [
                        {
                            "type": "concentric",
                            "assembly_reference": {"kind": "surface", "id": 41},
                            "component_reference": {"kind": "surface", "id": 42},
                        }
                    ],
                }
            ]
        )[0]
        self.assertEqual(checked["constraints"][0]["type"], "insert")


def surface_selector(**overrides):
    selector = {
        "kind": "geometry_selector",
        "target": "surface",
        "points_mm": [[10, 0, 1]],
        "tolerance_mm": 0.2,
    }
    selector.update(overrides)
    return selector


class SelectorConstraintTests(unittest.TestCase):
    """FEAT-068 A1: a unique anchor may name a constraint's face pair."""

    def test_coincident_accepts_unique_planar_selector(self):
        checked = AssemblyConstraint.model_validate(
            {
                "type": "coincident",
                "assembly_component": "base",
                "assembly_reference": surface_selector(),
                "component_reference": surface_selector(points_mm=[[0, 5, 1]]),
            }
        )
        self.assertEqual(checked.type, "mate")
        self.assertEqual(checked.component_reference["coordinate_space"], "model")

    def test_coincident_rejects_an_edge_selector(self):
        with self.assertRaises(ValueError):
            AssemblyConstraint.model_validate(
                {
                    "type": "coincident",
                    "assembly_component": "base",
                    "assembly_reference": {
                        "kind": "geometry_selector",
                        "target": "edge",
                        "point_mm": [0, 0, 10],
                        "tolerance_mm": 0.2,
                    },
                    "component_reference": surface_selector(),
                }
            )

    def test_concentric_requires_a_radius_filter(self):
        with self.assertRaises(ValueError):
            AssemblyConstraint.model_validate(
                {
                    "type": "concentric",
                    "assembly_component": "base",
                    "assembly_reference": surface_selector(axis=[0, 0, 1]),
                    "component_reference": surface_selector(
                        axis=[0, 0, 1], radius_mm=5, center_mm=[0, 0, 0]
                    ),
                }
            )

    def test_concentric_accepts_unique_cylinder_selector(self):
        checked = AssemblyConstraint.model_validate(
            {
                "type": "concentric",
                "assembly_component": "base",
                "assembly_reference": surface_selector(
                    axis=[0, 0, 1], radius_mm=5, center_mm=[0, 0, 0]
                ),
                "component_reference": surface_selector(
                    axis=[0, 0, 1], radius_mm=5, center_mm=[0, 0, 10]
                ),
            }
        )
        self.assertEqual(checked.type, "insert")
        self.assertEqual(checked.assembly_reference["radius_mm"], 5)

    def test_selector_plan_keeps_the_mapped_type(self):
        checked = validate_operations(
            [
                {
                    "op": "component_constraints",
                    "component": "pin",
                    "constraints": [
                        {
                            "type": "concentric",
                            "assembly_component": "base",
                            "assembly_reference": surface_selector(
                                axis=[0, 0, 1], radius_mm=5, center_mm=[0, 0, 0]
                            ),
                            "component_reference": surface_selector(
                                axis=[0, 0, 1], radius_mm=5, center_mm=[0, 0, 10]
                            ),
                        }
                    ],
                }
            ]
        )[0]
        self.assertEqual(checked["constraints"][0]["type"], "insert")
        self.assertEqual(
            checked["constraints"][0]["assembly_reference"]["kind"], "geometry_selector"
        )


class BUG132SelectorDiagnosisTests(unittest.TestCase):
    """BUG-132: name the missing field and confine coaxial='any' to insert."""

    def test_assembly_selector_without_component_names_the_missing_field(self):
        with self.assertRaises(ValueError) as caught:
            AssemblyConstraint.model_validate(
                {
                    "type": "mate",
                    "assembly_reference": surface_selector(),
                    "component_reference": {"kind": "surface", "id": 42},
                }
            )
        message = str(caught.exception)
        self.assertIn("assembly_component", message)
        self.assertIn("geometry_selector", message)

    def test_component_selector_may_omit_assembly_component(self):
        checked = AssemblyConstraint.model_validate(
            {
                "type": "mate",
                "assembly_reference": {"kind": "surface", "id": 41},
                "component_reference": surface_selector(points_mm=[[0, 5, 1]]),
            }
        )
        self.assertIsNone(checked.assembly_component)
        self.assertEqual(checked.component_reference["kind"], "geometry_selector")

    def test_coaxial_any_is_kept_on_concentric(self):
        checked = AssemblyConstraint.model_validate(
            {
                "type": "concentric",
                "assembly_component": "base",
                "assembly_reference": surface_selector(
                    axis=[0, 0, 1], radius_mm=27.5, center_mm=[0, 0, 0], coaxial="any"
                ),
                "component_reference": surface_selector(
                    axis=[0, 0, 1], radius_mm=27.5, center_mm=[0, 0, 10], coaxial="any"
                ),
            }
        )
        self.assertEqual(checked.type, "insert")
        self.assertEqual(checked.assembly_reference["coaxial"], "any")
        self.assertEqual(checked.component_reference["coaxial"], "any")

    def test_coaxial_any_is_refused_outside_insert(self):
        for constraint_type in ("mate", "coincident", "align", "csys"):
            with self.subTest(type=constraint_type), self.assertRaises(ValueError):
                AssemblyConstraint.model_validate(
                    {
                        "type": constraint_type,
                        "assembly_component": "base",
                        "assembly_reference": surface_selector(
                            axis=[0, 0, 1],
                            radius_mm=5,
                            center_mm=[0, 0, 0],
                            coaxial="any",
                        ),
                        "component_reference": {"kind": "surface", "id": 42},
                    }
                )


def constraint_row(index):
    return {
        "type": "mate",
        "assembly_reference": {"kind": "surface", "id": 41 + index},
        "component_reference": {"kind": "surface", "id": 42 + index},
    }


class ConstraintGroupBoundaryTests(unittest.TestCase):
    """DEV-092/T4: the 20-item cap bounds one component's whole group, not an assembly."""

    def test_one_component_group_is_capped_at_20(self):
        accepted = ComponentConstraintsOp.model_validate(
            {
                "op": "component_constraints",
                "component": "pin",
                "constraints": [constraint_row(i) for i in range(20)],
            }
        )
        self.assertEqual(len(accepted.constraints), 20)
        with self.assertRaises(ValueError):
            ComponentConstraintsOp.model_validate(
                {
                    "op": "component_constraints",
                    "component": "pin",
                    "constraints": [constraint_row(i) for i in range(21)],
                }
            )

    def test_a_new_component_placement_has_no_20_item_cap(self):
        checked = AssembleOp.model_validate(
            {
                "op": "assemble_component",
                "label": "cyl",
                "source_model_id": "a" * 32,
                "placement": "constraints",
                "constraints": [constraint_row(i) for i in range(22)],
            }
        )
        self.assertEqual(len(checked.constraints), 22)

    def test_22_constraints_across_components_are_separate_groups(self):
        plan = [
            {
                "op": "component_constraints",
                "component": component,
                "constraints": [constraint_row(i) for i in range(11)],
            }
            for component in ("pin_a", "pin_b")
        ]
        admitted = validate_operations(plan)
        self.assertEqual([len(entry["constraints"]) for entry in admitted], [11, 11])

    def test_the_public_fields_state_whole_group_replacement(self):
        description = ComponentConstraintsOp.model_json_schema()["properties"]["constraints"][
            "description"
        ]
        for phrase in ("complete constraint group", "replaces the whole group", "not appended"):
            self.assertIn(phrase, description)


class AssemblyFailureProjectionTests(unittest.TestCase):
    """DEV-092/T4: the constraint stage reaches the compact polling projection."""

    def test_receipt_keeps_the_input_convention_and_effective_tolerance(self):
        for key in ("rotation_convention", "input_rotation_convention", "rotation_tolerance"):
            self.assertIn(key, ASSEMBLY_POSE_KEYS)
        compact = compact_operation(
            {
                "op": "component_placement",
                "rotation_convention": "row_vectors_local_to_parent",
                "input_rotation_convention": "column",
                "rotation_tolerance": 1e-5,
                "transform": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [7, -8, 9, 1]],
                "unrelated": "dropped",
            }
        )
        self.assertEqual(compact["input_rotation_convention"], "column")
        self.assertEqual(compact["rotation_tolerance"], 1e-5)
        self.assertNotIn("unrelated", compact)

    def test_pre_parse_failure_names_the_index_and_stage(self):
        compact = compact_operation(
            {
                "op": "component_constraints",
                "succeeded": False,
                "failed_operation": {
                    "index": 0,
                    "operation": "component_constraints",
                    "stage": "surface_type",
                    "failed_constraint_index": 3,
                    "failed_constraint_type": "insert",
                    "constraint_stage": "surface_type",
                    "constraint_reason": "constraint_rejected",
                },
            }
        )
        block = compact["failed_operation"]
        self.assertEqual(block["failed_constraint_index"], 3)
        self.assertEqual(block["failed_constraint_type"], "insert")
        self.assertEqual(block["constraint_stage"], "surface_type")
        self.assertEqual(block["constraint_reason"], "constraint_rejected")

    def test_whole_group_solve_failure_reports_no_index(self):
        compact = compact_operation(
            {
                "op": "component_constraints",
                "succeeded": False,
                "failed_operation": {
                    "index": 0,
                    "operation": "component_constraints",
                    "stage": "solve",
                    "failed_constraint_index": None,
                    "failed_constraint_type": "mate",
                    "constraint_stage": "solve",
                    "constraint_reason": "solver_failed",
                },
            }
        )
        block = compact["failed_operation"]
        self.assertIsNone(block["failed_constraint_index"])
        self.assertEqual(block["constraint_reason"], "solver_failed")

    def test_planar_placement_failure_keeps_measured_scalars_in_compact_budget(self):
        failure = {
            "index": 0,
            "operation": "component_constraints",
            "constraint_stage": "after_write",
            "constraint_reason": "placement_mismatch",
            "placement_matches_constraints": False,
            "max_distance_error_mm": 30,
            "max_angle_error_deg": 180,
        }
        result = annotate_failed_operation(
            {"success": False, "failed_operation_index": 0, "failed_operation": failure},
            [{"op": "component_constraints", "component": "pin"}],
        )
        record = compact_operation(
            {
                "op": "component_constraints",
                "index": 0,
                "execution_status": "failed",
                "failed_operation": result["failed_operation"],
                "constraint_placement": {
                    "placement_matches_constraints": False,
                    "residuals": [{"distance_error_mm": 30}] * 100,
                },
            }
        )
        result["operations"] = [record]
        compact = enforce_compact_budget({"result": result}, budget=1500)
        row = compact["result"]["operations"][0]
        self.assertEqual(row["constraint_placement"], {"placement_matches_constraints": False})
        self.assertEqual(row["failed_operation"]["constraint_reason"], "placement_mismatch")
        self.assertIs(row["failed_operation"]["placement_matches_constraints"], False)
        self.assertEqual(row["failed_operation"]["max_distance_error_mm"], 30)
        self.assertEqual(row["failed_operation"]["max_angle_error_deg"], 180)


if __name__ == "__main__":
    unittest.main()
