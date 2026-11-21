"""BUG-045/FEAT-012/BUG-133: exact admission numbers for the reported I032 pose.

The published contract is ``1e-7`` on both layers. That boundary comes from the
2026-11-21 live sweep on Creo 10.0.0.0 / release 42: residuals 4.5e-10, 7.7e-9
and 4.76e-8 placed, while 2.24e-7, 4.89e-7 and 1.13e-6 were rejected by both
``ProAsmcompAssemble`` and ``ProAsmcompPositionSet`` with code -2. The truncated
I032 matrix (residual 2.2408500011117383e-07) is therefore refused before a job
exists, and its numbers stay available for the caller to act on.
"""

import math
import tempfile
import unittest
from pathlib import Path

from creo_mechdog import rotation_admission
from creo_mechdog.rotation_admission import (
    NEAR_ORTHONORMAL_TOLERANCE,
    admission_status,
)
from creo_mechdog.schema import ComponentPlacementOp, validate_operations

ROOT = Path(__file__).resolve().parents[2]

I032 = [[0, 0.307383, -0.951586], [0, 0.951586, 0.307383], [1, 0, 0]]
THIRTY_DEGREES = [
    [0.8660254037844387, 0.5, 0],
    [-0.5, 0.8660254037844387, 0],
    [0, 0, 1],
]
IDENTITY = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


class RotationAdmissionTests(unittest.TestCase):
    def test_truncated_i032_is_refused_at_the_measured_boundary(self):
        status = admission_status(I032)
        self.assertEqual(status["orthogonality_residual"], 2.2408500011117383e-07)
        self.assertEqual(status["determinant_error"], 2.2408500011117383e-07)
        self.assertEqual(status["determinant"], 1.0000002240850001)
        self.assertFalse(status["accepted"])
        self.assertEqual(status["tolerance"], 1e-7)
        self.assertEqual(status["precision"], "invalid")
        self.assertIsNone(status["advice"])
        # The schema refuses it before a job exists, quoting the caller's numbers.
        with self.assertRaises(ValueError) as raised:
            ComponentPlacementOp(op="component_placement", component="comp_a", rotation_matrix=I032)
        self.assertIn("2.24085e-07", str(raised.exception))
        self.assertIn("never repaired", str(raised.exception))

    def test_precise_30_degree_pose_stays_valid(self):
        status = admission_status(THIRTY_DEGREES)
        self.assertTrue(status["accepted"])
        self.assertEqual(status["precision"], "strict")
        self.assertEqual(status["orthogonality_residual"], 0.0)
        self.assertEqual(status["determinant"], 1.0)
        self.assertIsNone(status["advice"])
        operation = ComponentPlacementOp(
            op="component_placement", component="comp_a", rotation_matrix=THIRTY_DEGREES
        )
        self.assertEqual(operation.rotation_matrix, THIRTY_DEGREES)

    def test_the_two_layers_share_the_published_numbers(self):
        header = (ROOT / "native" / "assembly_pose.h").read_text(encoding="utf-8")
        self.assertIn("assembly_rotation_admission", header)
        self.assertIn("return 1e-7;", header)
        self.assertIn("return 1e-9;", header)
        self.assertIn("never repaired", header)
        self.assertIn(
            "ADMISSION_TOLERANCE = 1e-7",
            (ROOT / "src/creo_mechdog/rotation_admission.py").read_text(encoding="utf-8"),
        )
        self.assertEqual(NEAR_ORTHONORMAL_TOLERANCE, 1e-9)

    def test_rejected_matrix_reports_its_numbers_before_any_job(self):
        skew = [row[:] for row in IDENTITY]
        skew[0][1] = 1e-4
        with self.assertRaises(ValueError) as raised:
            validate_operations(
                [
                    {
                        "op": "component_placement",
                        "component": "comp_a",
                        "rotation_matrix": skew,
                    }
                ]
            )
        message = str(raised.exception)
        self.assertIn("max |R*R^T-I| = 0.0001", message)
        self.assertIn("never repaired", message)

        scaled = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        for index in range(3):
            scaled[index][index] = 1 + 4e-8
        with self.assertRaises(ValueError) as raised:
            validate_operations(
                [
                    {
                        "op": "component_placement",
                        "component": "comp_a",
                        "rotation_matrix": scaled,
                    }
                ]
            )
        message = str(raised.exception)
        self.assertIn("determinant must be +1 within 1e-7", message)
        self.assertIn("det = 1.00000012", message)

    def test_a_rejected_pose_creates_no_job_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            jobs = Path(temporary)
            skew = [row[:] for row in IDENTITY]
            skew[2][0] = 1e-3
            with self.assertRaises(ValueError):
                validate_operations(
                    [
                        {
                            "op": "component_placement",
                            "component": "comp_a",
                            "rotation_matrix": skew,
                        }
                    ]
                )
            self.assertEqual(list(jobs.iterdir()), [])

    def test_admission_does_not_repair_the_matrix(self):
        near = [row[:] for row in IDENTITY]
        near[0][0] = 1 + 4e-8
        status = admission_status(near)
        self.assertTrue(status["accepted"])
        self.assertEqual(status["precision"], "near_orthonormal")
        self.assertEqual(near[0][0], 1 + 4e-8)
        self.assertFalse(math.isclose(near[0][0], 1.0, rel_tol=0, abs_tol=1e-8))
        operation = ComponentPlacementOp(
            op="component_placement", component="comp_a", rotation_matrix=near
        )
        self.assertEqual(operation.rotation_matrix[0][0], 1 + 4e-8)


#: BUG-133 synthetic case: a 28-degree Z rotation rounded to six decimals.
#: max |R R^T - I| = 1.1294880000178864e-06, above the measured 1e-7 boundary,
#: so it is refused even though it still describes a proper rotation.
ROUNDED_28 = [
    [0.882948, 0.469472, 0.0],
    [-0.469472, 0.882948, 0.0],
    [0.0, 0.0, 1.0],
]
#: The same pose rounded to seven decimals: max |R R^T - I| = 4.755232e-08,
#: below the boundary, so it is admitted verbatim.
ROUNDED_28_7 = [
    [0.8829476, 0.4694716, 0.0],
    [-0.4694716, 0.8829476, 0.0],
    [0.0, 0.0, 1.0],
]
SOURCE_ID = "a" * 32


def assemble_operation(**overrides):
    return {
        "op": "assemble_component",
        "label": "probe",
        "source_model_id": SOURCE_ID,
        "rotation_matrix": [row[:] for row in ROUNDED_28],
        **overrides,
    }


def placement_operation(**overrides):
    return {
        "op": "component_placement",
        "component": "probe",
        "rotation_matrix": [row[:] for row in ROUNDED_28],
        **overrides,
    }


class ExplicitToleranceTests(unittest.TestCase):
    """BUG-133: one effective tolerance for admission and every native entry."""

    def test_the_rounded_matrix_misses_the_default_gate(self):
        status = admission_status(ROUNDED_28)
        self.assertAlmostEqual(status["orthogonality_residual"], 1.1294880000178864e-06, places=18)
        self.assertFalse(status["accepted"])
        self.assertEqual(status["tolerance"], 1e-7)
        for operation in (assemble_operation(), placement_operation()):
            with self.assertRaises(ValueError):
                validate_operations([operation])

    def test_explicit_tolerance_at_the_ceiling_admits_a_seven_decimal_pose(self):
        for operation in (
            assemble_operation(
                rotation_matrix=[row[:] for row in ROUNDED_28_7], rotation_tolerance=1e-7
            ),
            placement_operation(
                rotation_matrix=[row[:] for row in ROUNDED_28_7], rotation_tolerance=1e-7
            ),
        ):
            admitted = validate_operations([operation])[0]
            # The echo is the caller's matrix: no repair, no transpose.
            self.assertEqual(admitted["rotation_matrix"], ROUNDED_28_7)
            self.assertEqual(admitted["rotation_tolerance"], 1e-7)
        status = admission_status(ROUNDED_28_7, 1e-7)
        self.assertTrue(status["accepted"])
        self.assertEqual(status["precision"], "near_orthonormal")
        self.assertEqual(status["tolerance"], 1e-7)

    def test_a_tolerance_above_the_measured_boundary_is_refused(self):
        for tolerance in (1e-6, 1e-5, 1e-3):
            with self.assertRaises(ValueError) as raised:
                validate_operations([placement_operation(rotation_tolerance=tolerance)])
            self.assertIn("at most 1e-7", str(raised.exception))

    def test_tolerance_below_the_residual_still_refuses(self):
        with self.assertRaises(ValueError):
            validate_operations([placement_operation(rotation_tolerance=1e-7)])

    def test_the_ceiling_keeps_a_reflection_and_a_scale_out(self):
        reflection = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, -1.0]]
        with self.assertRaises(ValueError) as raised:
            validate_operations(
                [
                    {
                        "op": "component_placement",
                        "component": "probe",
                        "rotation_matrix": reflection,
                        "rotation_tolerance": 1.0,
                    }
                ]
            )
        self.assertIn("rotation_tolerance", str(raised.exception))
        scaled = [[1.0002, 0.0, 0.0], [0.0, 1.0002, 0.0], [0.0, 0.0, 1.0002]]
        with self.assertRaises(ValueError):
            validate_operations(
                [
                    {
                        "op": "component_placement",
                        "component": "probe",
                        "rotation_matrix": scaled,
                        "rotation_tolerance": 5e-4,
                    }
                ]
            )
        # The ceiling equals the measured boundary: it cannot be raised.
        self.assertEqual(rotation_admission.MAX_ADMISSION_TOLERANCE, 1e-7)
        with self.assertRaises(ValueError) as raised:
            validate_operations([placement_operation(rotation_tolerance=1e-3)])
        self.assertIn("at most 1e-7", str(raised.exception))

    def test_invalid_tolerances_are_refused_before_any_job(self):
        for tolerance in (True, "1e-5", 0, -1e-5, math.inf, math.nan):
            with self.assertRaises(ValueError, msg=repr(tolerance)):
                validate_operations([placement_operation(rotation_tolerance=tolerance)])

    def test_the_native_helper_reads_the_same_effective_tolerance(self):
        header = (ROOT / "native" / "assembly_pose.h").read_text(encoding="utf-8")
        for phrase in (
            "assembly_max_admission_tolerance",
            "return 1e-7;",
            "rotation_tolerance",
            "assembly_rotation_admission(rotation, tolerance)",
        ):
            self.assertIn(phrase, header)
        self.assertNotIn("std::to_string(admission.orthogonality_residual)", header)


if __name__ == "__main__":
    unittest.main()
