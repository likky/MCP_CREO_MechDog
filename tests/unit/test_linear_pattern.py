"""DEV-089 T6b / BUG-169: linear (direction) pattern admission and receipt contract."""

import unittest
from pathlib import Path

from pydantic import ValidationError

from creo_mechdog.capabilities import REGISTERED_OPERATIONS
from creo_mechdog.operation_results import OUTCOME_OPERATION_KEYS
from creo_mechdog.schema import (
    NON_SOLID_PATTERN_LEADER_OPS,
    LinearPatternOp,
    validate_linear_pattern_leaders,
    validate_operations,
)

ROOT = Path(__file__).resolve().parents[2]


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

    def test_same_plan_sketch_or_datum_leader_is_rejected_before_any_job(self):
        plan = [
            {
                "op": "sketch",
                "label": "sk_hole",
                "plane": "XY",
                "entities": [{"type": "circle", "name": "c1", "center": [0, 0], "radius": 5}],
            },
            payload(leader="sk_hole"),
        ]
        with self.assertRaisesRegex(ValueError, "LINEAR_PATTERN_NON_SOLID_LEADER"):
            validate_operations(plan)

    def test_existing_model_non_solid_alias_leader_is_rejected_case_insensitively(self):
        for op_name in sorted(NON_SOLID_PATTERN_LEADER_OPS):
            with self.subTest(op_name=op_name):
                aliases = {"ref_feat": {"feature_id": 100, "op": op_name}}
                with self.assertRaisesRegex(ValueError, "LINEAR_PATTERN_NON_SOLID_LEADER"):
                    validate_linear_pattern_leaders([payload(leader="REF_FEAT")], aliases)

    def test_solid_alias_and_numeric_leader_pass_python_admission(self):
        aliases = {
            "cut_extrude7": {"feature_id": 3754, "op": "extrude"},
            "grp1": {"feature_id": 4000, "op": "feature_group"},
        }
        validate_linear_pattern_leaders([payload(leader="cut_extrude7")], aliases)
        validate_linear_pattern_leaders([payload(leader="grp1")], aliases)
        validate_linear_pattern_leaders([payload(leader=3754)], aliases)

    def test_compact_outcome_keys_preserve_feature_and_pattern_leader_fields(self):
        from creo_mechdog import job_projection

        for key in (
            "feature_id",
            "leader_id",
            "leader_kind",
            "leader_surface_count",
            "member_count",
        ):
            self.assertIn(key, OUTCOME_OPERATION_KEYS)
        projected = job_projection.compact_operation(
            {
                "op": "linear_pattern",
                "label": "slot_pat",
                "succeeded": True,
                "feature_id": 147,
                "leader_id": 87,
                "leader_kind": "cut",
                "leader_feature_type": 918,
                "leader_surface_count": 12,
                "leader_surface_query_code": 0,
                "group_leader": False,
                "member_count": 3,
                "direction_reference": {"source": "straight_edge", "id": 5},
                "extra_unlisted_field": "dropped",
            }
        )
        self.assertEqual(projected["feature_id"], 147)
        self.assertEqual(projected["leader_id"], 87)
        self.assertEqual(projected["leader_kind"], "cut")
        self.assertEqual(projected["leader_surface_count"], 12)
        self.assertEqual(projected["member_count"], 3)
        self.assertEqual(projected["direction_reference"]["id"], 5)
        self.assertNotIn("extra_unlisted_field", projected)

    def test_native_guards_and_extrude_feature_id_wiring(self):
        linear_cpp = (ROOT / "native/linear_pattern.cpp").read_text(encoding="utf-8")
        generic_cpp = (ROOT / "native/generic.cpp").read_text(encoding="utf-8")
        self.assertIn("LINEAR_PATTERN_NON_SOLID_LEADER", linear_cpp)
        self.assertIn("LINEAR_PATTERN_LEADER_ALIAS_MISMATCH", linear_cpp)
        self.assertIn("leader_kind", linear_cpp)
        self.assertIn("leader_surface_count", linear_cpp)
        self.assertIn("ProFeatureGeomitemVisit", linear_cpp)
        self.assertIn('J details = {{"feature_id", f.id}};', generic_cpp)


if __name__ == "__main__":
    unittest.main()
