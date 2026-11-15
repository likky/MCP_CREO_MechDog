"""DEV-089 T6b: linear (direction) pattern admission contract."""

import unittest

from pydantic import ValidationError

from creo_mechdog.capabilities import REGISTERED_OPERATIONS
from creo_mechdog.schema import LinearPatternOp, validate_operations


def payload(**overrides):
    base = {
        "op": "linear_pattern",
        "label": "rows",
        "leader": "hole1",
        "direction": [1.0, 0.0, 0.0],
        "spacing": 42.0,
        "count": 2,
        "flip": False,
    }
    base.update(overrides)
    return base


class LinearPatternContractTests(unittest.TestCase):
    def test_registered_and_round_trips(self):
        self.assertIn("linear_pattern", REGISTERED_OPERATIONS)
        model = LinearPatternOp.model_validate(payload())
        dumped = model.model_dump()
        self.assertEqual(dumped["direction"], [1.0, 0.0, 0.0])
        self.assertEqual(dumped["spacing"], 42.0)
        self.assertEqual(dumped["count"], 2)
        self.assertIs(dumped["flip"], False)
        self.assertEqual(validate_operations([payload()]), [payload()])

    def test_direction_must_be_a_unit_vector(self):
        for direction in ([0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 1.0, 1.0], [1.0, 0.0]):
            with self.subTest(direction=direction):
                with self.assertRaisesRegex(ValidationError, "unit vector|\\[x,y,z\\]"):
                    LinearPatternOp.model_validate(payload(direction=direction))
        with self.assertRaises(ValidationError):
            LinearPatternOp.model_validate(payload(direction=[True, 0.0, 0.0]))
        with self.assertRaises(ValidationError):
            LinearPatternOp.model_validate(payload(direction=[float("nan"), 0.0, 0.0]))

    def test_spacing_and_count_bounds(self):
        for spacing in (0, -1.0, True, float("inf")):
            with self.subTest(spacing=spacing):
                with self.assertRaises(ValidationError):
                    LinearPatternOp.model_validate(payload(spacing=spacing))
        for count in (1, 0, 361, 2.5, True):
            with self.subTest(count=count):
                with self.assertRaises(ValidationError):
                    LinearPatternOp.model_validate(payload(count=count))

    def test_flip_is_boolean_only(self):
        with self.assertRaises(ValidationError):
            LinearPatternOp.model_validate(payload(flip="yes"))

    def test_leader_is_required(self):
        without_leader = payload()
        without_leader.pop("leader")
        with self.assertRaises(ValidationError):
            LinearPatternOp.model_validate(without_leader)


if __name__ == "__main__":
    unittest.main()
