"""DEV-089 T2: assembly constraint offset semantics (BUG-041)."""

import unittest

from creo_mechdog.schema import AssemblyConstraint, ComponentConstraintsOp, validate_operations


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


if __name__ == "__main__":
    unittest.main()
