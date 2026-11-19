"""FEAT-012 batch-2 stage-4 matrix pose math regressions (offline).

Locks the corrected bounding-box invariant used by tools/test_assembly_matrix.py:
the AABB of a rotated box keeps the source box volume ONLY for signed-
permutation (axis-aligned) rotations; the [30,90,60] pose and any genuine
rotation strictly enlarge it. The old driver asserted equality for every
pose, which is mathematically false for the last pose.

R05 (BUG-045/FEAT-012) adds the published row-vector convention: the
``assemble_component`` and ``component_placement`` input branches must state
``p_parent = p_local * rotation_matrix + translation``, and a 17.9-degree
matrix must map an asymmetric point and the basis vectors as
``p_local * R`` — never as a transposed column-vector product.
"""

import math
import unittest

from pydantic import TypeAdapter, ValidationError

from creo_mechdog.schema import (
    ROTATION_CONVENTION,
    ROTATION_FORMULA,
    AssembleOp,
    ComponentPlacementOp,
    Operation,
    validate_operations,
)
from tools.test_assembly_matrix import POSES, is_signed_permutation

Z_ANGLE = 17.9
SOURCE_ID = "a" * 32


def z_rotation(angle=Z_ANGLE, digits=None):
    """Row-vector Z rotation: row 0 is the mapped local X axis."""
    radians = math.radians(angle)
    rotation = [
        [math.cos(radians), math.sin(radians), 0.0],
        [-math.sin(radians), math.cos(radians), 0.0],
        [0.0, 0.0, 1.0],
    ]
    if digits is not None:
        return [[round(value, digits) for value in row] for row in rotation]
    return rotation


def row_vector_map(rotation, translation, point):
    return [sum(point[k] * rotation[k][j] for k in range(3)) + translation[j] for j in range(3)]


def column_vector_map(rotation, translation, point):
    """What a transposed (column-vector) reading would produce; must differ."""
    return [sum(rotation[j][k] * point[k] for k in range(3)) + translation[j] for j in range(3)]


def assemble_operation(rotation_matrix, translation=(0.0, 0.0, 0.0)):
    return {
        "op": "assemble_component",
        "label": "i032",
        "source_model_id": SOURCE_ID,
        "rotation_matrix": rotation_matrix,
        "translation": list(translation),
    }


def placement_operation(rotation_matrix, translation=(0.0, 0.0, 0.0)):
    return {
        "op": "component_placement",
        "component": "i032",
        "rotation_matrix": rotation_matrix,
        "translation": list(translation),
    }


def plan_schema():
    """The execute_plan input: a discriminated union of operations per entry."""
    return TypeAdapter(list[Operation]).json_schema()


def branch_properties(kind):
    schema = plan_schema()
    reference = schema["items"]["discriminator"]["mapping"][kind]
    return schema["$defs"][reference.rsplit("/", 1)[-1]]["properties"]


# Native source sketch is [0,2]x[0,3] extruded 5 deep.
SOURCE_LO = [0.0, 0.0, 0.0]
SOURCE_HI = [2.0, 3.0, 5.0]


def map_point(matrix, point):
    return [sum(v * matrix[k][j] for k, v in enumerate(point)) + matrix[3][j] for j in range(3)]


def expected_box_volume(rotation, translation):
    corners = [
        [x, y, z]
        for x in (SOURCE_LO[0], SOURCE_HI[0])
        for y in (SOURCE_LO[1], SOURCE_HI[1])
        for z in (SOURCE_LO[2], SOURCE_HI[2])
    ]
    transform = [list(row) + [0] for row in rotation] + [list(translation) + [1]]
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for corner in corners:
        mapped = map_point(transform, corner)
        for axis in range(3):
            lo[axis] = min(lo[axis], mapped[axis])
            hi[axis] = max(hi[axis], mapped[axis])
    volume = 1.0
    for axis in range(3):
        volume *= hi[axis] - lo[axis]
    return volume


SOURCE_BOX_VOLUME = (
    (SOURCE_HI[0] - SOURCE_LO[0]) * (SOURCE_HI[1] - SOURCE_LO[1]) * (SOURCE_HI[2] - SOURCE_LO[2])
)


class MatrixPoseMath(unittest.TestCase):
    def test_pose_matrix_stays_11_with_one_non_permutation(self):
        self.assertEqual(len(POSES), 11)
        non_permutations = [
            euler for euler, rotation, _ in POSES if not is_signed_permutation(rotation)
        ]
        self.assertEqual(non_permutations, [[30, 90, 60]])

    def test_signed_permutation_detection(self):
        self.assertTrue(is_signed_permutation([[1, 0, 0], [0, 1, 0], [0, 0, 1]]))
        self.assertTrue(is_signed_permutation([[0, 1, 0], [0, 0, 1], [1, 0, 0]]))
        self.assertTrue(is_signed_permutation([[0, -1, 0], [1, 0, 0], [0, 0, 1]]))
        self.assertTrue(is_signed_permutation([[0, 0, -1], [0, 1, 0], [1, 0, 0]]))
        self.assertFalse(
            is_signed_permutation(
                [[0, 0, -1], [-0.5, 0.8660254037844386, 0], [0.8660254037844386, 0.5, 0]]
            )
        )

    def test_box_volume_invariant_only_for_axis_aligned_poses(self):
        translation = [7, -8, 9, 1]
        for euler, rotation, _ in POSES:
            volume = expected_box_volume(rotation, translation)
            if is_signed_permutation(rotation):
                self.assertAlmostEqual(volume, SOURCE_BOX_VOLUME, places=9, msg=str(euler))
            else:
                # The stage-3 assertion (equality for every pose) fails here:
                # the AABB of a genuinely rotated box is strictly larger.
                self.assertGreater(volume, SOURCE_BOX_VOLUME + 1.0, msg=str(euler))

    def test_translation_does_not_change_box_volume(self):
        for euler, rotation, _ in POSES:
            at_origin = expected_box_volume(rotation, [0, 0, 0, 1])
            translated = expected_box_volume(rotation, [7, -8, 9, 1])
            self.assertAlmostEqual(at_origin, translated, places=9, msg=str(euler))


class RotationContractTest(unittest.TestCase):
    """R05: both assembly branches state the same row-vector formula."""

    def test_both_assembly_branches_state_the_same_formula(self):
        assemble = branch_properties("assemble_component")
        placement = branch_properties("component_placement")
        for field in ("rotation_matrix", "rotation"):
            self.assertEqual(assemble[field]["description"], placement[field]["description"], field)
            self.assertIn(ROTATION_FORMULA, assemble[field]["description"], field)

    def test_the_matrix_description_states_the_gate_and_refuses_repair(self):
        description = branch_properties("assemble_component")["rotation_matrix"]["description"]
        for phrase in (
            "3x3",
            "orthogonal",
            "1e-6",
            "determinant +1",
            "mutually exclusive",
            "never transposed",
        ):
            self.assertIn(phrase, description)

    def test_the_published_convention_name_is_the_row_vector_mapping(self):
        self.assertEqual(ROTATION_CONVENTION, "row_vectors_local_to_parent")
        self.assertIn("p_local", ROTATION_FORMULA)


class RowVectorPoseTest(unittest.TestCase):
    """R05: the admitted matrix is applied as p_local * R, never R * p_local."""

    def test_basis_vectors_map_to_the_matrix_rows(self):
        rotation = z_rotation()
        for axis, row in enumerate(rotation):
            point = [0.0, 0.0, 0.0]
            point[axis] = 1.0
            mapped = row_vector_map(rotation, [0.0, 0.0, 0.0], point)
            for actual, expected in zip(mapped, row, strict=True):
                self.assertAlmostEqual(actual, expected, places=12)

    def test_an_asymmetric_point_uses_p_local_times_r(self):
        rotation = z_rotation()
        translation = [1.5, -2.25, 7.0]
        point = [3.0, 4.0, 0.0]
        cosine, sine = math.cos(math.radians(Z_ANGLE)), math.sin(math.radians(Z_ANGLE))
        expected = [
            3 * cosine - 4 * sine + translation[0],
            3 * sine + 4 * cosine + translation[1],
            translation[2],
        ]
        mapped = row_vector_map(rotation, translation, point)
        for actual, value in zip(mapped, expected, strict=True):
            self.assertAlmostEqual(actual, value, places=12)
        transposed = column_vector_map(rotation, translation, point)
        self.assertGreater(abs(mapped[0] - transposed[0]), 1.0)
        self.assertGreater(abs(mapped[1] - transposed[1]), 1.0)

    def test_full_precision_and_six_decimal_poses_are_admitted_unchanged(self):
        for digits in (None, 6):
            rotation = z_rotation(digits=digits)
            for operation, model in (
                (assemble_operation(rotation), AssembleOp),
                (placement_operation(rotation), ComponentPlacementOp),
            ):
                admitted = model(**operation)
                # The echo is the caller's matrix: no repair and no transpose.
                self.assertEqual(admitted.rotation_matrix, rotation)
                self.assertIsNone(admitted.rotation)
                validate_operations([operation])

    def test_rounding_below_the_gate_is_rejected_without_repair(self):
        rotation = z_rotation(digits=4)
        for operation, model in (
            (assemble_operation(rotation), AssembleOp),
            (placement_operation(rotation), ComponentPlacementOp),
        ):
            with self.assertRaises(ValidationError):
                model(**operation)
        with self.assertRaises(ValidationError):
            # Admission rejects before any job exists; nothing is repaired.
            validate_operations([assemble_operation(rotation)])

    def test_explicit_tolerance_admits_a_documented_rounded_pose_unchanged(self):
        rotation = z_rotation(digits=4)
        for operation, model in (
            (assemble_operation(rotation), AssembleOp),
            (placement_operation(rotation), ComponentPlacementOp),
        ):
            operation["rotation_tolerance"] = 1e-3
            admitted = model(**operation)
            # The echo is still the caller's rounded matrix; no repair.
            self.assertEqual(admitted.rotation_matrix, rotation)
            self.assertEqual(admitted.rotation_tolerance, 1e-3)
            validate_operations([operation])

    def test_tolerance_must_be_positive_and_cannot_admit_a_reflection(self):
        with self.assertRaises(ValidationError):
            AssembleOp(**{**assemble_operation(z_rotation()), "rotation_tolerance": 0})
        reflection = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, -1.0]]
        with self.assertRaises(ValidationError):
            AssembleOp(**{**assemble_operation(reflection), "rotation_tolerance": 1.0})

    def test_a_reflection_and_a_second_orientation_are_rejected(self):
        with self.assertRaises(ValidationError):
            AssembleOp(**assemble_operation([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, -1.0]]))
        both = assemble_operation(z_rotation())
        both["rotation"] = [0.0, 0.0, Z_ANGLE]
        with self.assertRaises(ValidationError):
            AssembleOp(**both)
        with self.assertRaises(ValidationError):
            ComponentPlacementOp(**placement_operation([[1.0, 2.0], [3.0, 4.0]]))


#: FEAT-012/T2 threshold case: the six-decimal column matrix whose own row
#: reading gives 9.62666e-7 but whose canonical (transposed) row form gives
#: 1.023309e-6, so only the canonical form can decide the gate.
MARGINAL_COLUMN = [
    [0.965337, -0.258191, 0.038222],
    [0.258661, 0.965936, -0.007826],
    [-0.034899, 0.017442, 0.999239],
]
POINT = [2.0, 3.0, 5.0]
TRANSLATION = [7.0, -8.0, 9.0]
COLUMN_90 = [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]


def column_rotation_map(rotation, point):
    return [sum(rotation[j][k] * point[k] for k in range(3)) for j in range(3)]


def gram_residual(rotation):
    return max(
        abs(sum(rotation[i][k] * rotation[j][k] for k in range(3)) - (1.0 if i == j else 0.0))
        for i in range(3)
        for j in range(3)
    )


class ExplicitConventionTest(unittest.TestCase):
    """FEAT-012/T2: a column input is transposed exactly once, before the gate."""

    def test_column_input_maps_the_known_point(self):
        operation = {
            "op": "component_placement",
            "component": "probe",
            "rotation_matrix": [row[:] for row in COLUMN_90],
            "rotation_convention": "column",
            "translation": TRANSLATION,
        }
        admitted = validate_operations([operation])[0]
        # The request keeps the caller's array and convention.
        self.assertEqual(admitted["rotation_matrix"], COLUMN_90)
        self.assertEqual(admitted["rotation_convention"], "column")
        mapped = [
            value + TRANSLATION[index]
            for index, value in enumerate(column_rotation_map(COLUMN_90, POINT))
        ]
        self.assertEqual(mapped, [4.0, -6.0, 14.0])
        # The equivalent row input maps the same point.
        canonical = [[COLUMN_90[j][i] for j in range(3)] for i in range(3)]
        row_mapped = row_vector_map(canonical, TRANSLATION, POINT)
        for actual, expected in zip(row_mapped, mapped, strict=True):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_row_stays_the_default_and_is_not_transposed(self):
        operation = {
            "op": "component_placement",
            "component": "probe",
            "rotation_matrix": [row[:] for row in COLUMN_90],
            "translation": TRANSLATION,
        }
        admitted = validate_operations([operation])[0]
        self.assertIsNone(admitted.get("rotation_convention"))
        mapped = row_vector_map(COLUMN_90, TRANSLATION, POINT)
        self.assertAlmostEqual(mapped[0], 10.0, places=12)
        self.assertAlmostEqual(mapped[1], -10.0, places=12)

    def test_repeated_validation_never_transposes_twice(self):
        operation = {
            "op": "component_placement",
            "component": "probe",
            "rotation_matrix": [row[:] for row in COLUMN_90],
            "rotation_convention": "column",
        }
        first = validate_operations([operation])[0]
        second = validate_operations([first])[0]
        self.assertEqual(second["rotation_matrix"], COLUMN_90)
        self.assertEqual(second["rotation_convention"], "column")

    def test_both_assembly_branches_accept_the_same_column_pose(self):
        for operation, model in (
            (assemble_operation(COLUMN_90), AssembleOp),
            (placement_operation(COLUMN_90), ComponentPlacementOp),
        ):
            operation["rotation_convention"] = "column"
            admitted = model(**operation)
            self.assertEqual(admitted.rotation_matrix, COLUMN_90)
            self.assertEqual(admitted.rotation_convention, "column")

    def test_the_gate_measures_the_canonical_row_form(self):
        self.assertAlmostEqual(gram_residual(MARGINAL_COLUMN), 9.62666e-7, places=13)
        canonical = [[MARGINAL_COLUMN[j][i] for j in range(3)] for i in range(3)]
        self.assertAlmostEqual(gram_residual(canonical), 1.023309e-6, places=13)
        operation = placement_operation(MARGINAL_COLUMN)
        operation["rotation_convention"] = "column"
        with self.assertRaises(ValueError):
            validate_operations([operation])
        # The equivalent row input is refused by the same canonical measurement.
        row_operation = placement_operation(canonical)
        with self.assertRaises(ValueError):
            validate_operations([row_operation])
        for tolerant in (
            {**operation, "rotation_tolerance": 1e-5},
            {**row_operation, "rotation_tolerance": 1e-5},
        ):
            admitted = validate_operations([tolerant])[0]
            self.assertEqual(
                admitted.get("rotation_convention"), tolerant.get("rotation_convention")
            )

    def test_convention_is_refused_where_it_cannot_apply(self):
        euler = {"op": "component_placement", "component": "probe", "rotation": [0, 0, 90]}
        with self.assertRaises(ValueError):
            validate_operations([{**euler, "rotation_convention": "column"}])
        with self.assertRaises(ValueError):
            validate_operations([{**euler, "rotation_tolerance": 1e-5}])
        with self.assertRaises(ValueError):
            validate_operations(
                [{**placement_operation(COLUMN_90), "rotation_convention": "columnar"}]
            )


class FailureContextConventionTest(unittest.TestCase):
    """BUG-133/FEAT-012: the failure echo measures the same gate as the entry."""

    def test_column_failure_echoes_the_input_and_measures_the_row_form(self):
        from creo_mechdog.failure_context import placement_matrix

        operation = {
            "op": "component_placement",
            "component": "probe",
            "rotation_matrix": [row[:] for row in MARGINAL_COLUMN],
            "rotation_convention": "column",
            "translation": TRANSLATION,
        }
        block = placement_matrix(operation)
        # The echo is the caller's own array, not the transposed measurement form.
        self.assertEqual([row[:3] for row in block["input_matrix"][:3]], MARGINAL_COLUMN)
        self.assertEqual(block["matrix_convention"], "column")
        self.assertEqual(block["admission_tolerance"], 1e-6)
        self.assertAlmostEqual(block["orthogonality_residual"], 1.023309e-6, places=13)
        self.assertEqual(block["precision_class"], "invalid")
        tolerant = placement_matrix({**operation, "rotation_tolerance": 1e-5})
        self.assertEqual(tolerant["admission_tolerance"], 1e-5)
        self.assertEqual(tolerant["precision_class"], "near_orthonormal")
        self.assertIn("not repaired", tolerant["precision_advice"])


if __name__ == "__main__":
    unittest.main()
