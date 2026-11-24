"""BUG-187: explicit sketch v_axis and datum plane flip contract (offline).

The reported failure showed a sketch attached to an offset datum plane silently
turning its v_axis around and reversing every extrusion. These tests pin the
Python-side contract: flip is a boolean on datum_plane, a dictionary sketch
plane may carry v_axis, and an explicitly supplied frame must be orthonormal.
The native frame construction is exercised by the Creo integration test.
"""

import unittest

from creo_mechdog.references import validate_sketch_plane_frame
from creo_mechdog.schema import validate_operations


def plane_op(**overrides) -> dict:
    op = {
        "op": "datum_plane",
        "label": "datum",
        "reference": {"kind": "datum_plane", "axis": "z"},
    }
    op.update(overrides)
    return op


class DatumPlaneFlipTests(unittest.TestCase):
    def test_flip_is_accepted_and_published(self):
        result = validate_operations([plane_op(offset=-30, flip=True)])[0]
        self.assertIs(result["flip"], True)

    def test_flip_defaults_to_false(self):
        result = validate_operations([plane_op(offset=-30)])[0]
        self.assertIs(result["flip"], False)

    def test_flip_must_be_boolean(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations([plane_op(offset=-30, flip="yes")])
        self.assertIn("flip", str(caught.exception))


class SketchFrameTests(unittest.TestCase):
    def frame(self, **overrides) -> dict:
        value = {
            "kind": "plane",
            "reference": {"kind": "datum_plane", "axis": "z"},
            "u_axis": [1, 0, 0],
            "v_axis": [0, 0, 1],
        }
        value.update(overrides)
        return value

    def test_explicit_v_axis_is_accepted(self):
        validate_sketch_plane_frame(self.frame(), "plane")

    def test_zero_v_axis_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            validate_sketch_plane_frame(self.frame(v_axis=[0, 0, 0]), "plane")
        self.assertIn("v_axis", str(caught.exception))

    def test_non_orthogonal_frame_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            validate_sketch_plane_frame(self.frame(v_axis=[1, 0, 1]), "plane")
        self.assertIn("orthogonal", str(caught.exception))

    def test_flip_must_be_boolean(self):
        with self.assertRaises(ValueError) as caught:
            validate_sketch_plane_frame(self.frame(flip=1), "plane")
        self.assertIn("flip", str(caught.exception))

    def test_non_numeric_v_axis_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            validate_sketch_plane_frame(self.frame(v_axis=[0, "z", 1]), "plane")
        self.assertIn("numeric 3D vector", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
