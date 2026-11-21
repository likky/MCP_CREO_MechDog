"""FEAT-071: explicit D1xD2 chamfer contract and native tree wiring."""

from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest import mock

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError

import server
from creo_mechdog.schema import ChamferOp, validate_operations

EDGE = [{"edge": {"kind": "edge", "id": 7}}]
FACE = {"kind": "surface", "id": 12}
NATIVE = Path(__file__).resolve().parents[2] / "native" / "generic.cpp"


def d1_payload(**overrides):
    payload = {
        "op": "chamfer",
        "label": "break_edge",
        "references": EDGE,
        "chamfer_type": "d1_d2",
        "distance_1": 2.0,
        "distance_2": 3.0,
        "reference_surface": FACE,
    }
    payload.update(overrides)
    return payload


class TwoDistanceSchemaTests(unittest.TestCase):
    def test_plan_keeps_both_distances_and_explicit_reference_surface(self):
        self.assertEqual(
            validate_operations([d1_payload()]),
            [
                {
                    "op": "chamfer",
                    "label": "break_edge",
                    "references": EDGE,
                    "distance_1": 2.0,
                    "distance_2": 3.0,
                    "reference_surface": FACE,
                }
            ],
        )

    def test_all_three_d1_d2_inputs_are_required(self):
        for field in ("distance_1", "distance_2", "reference_surface"):
            with self.subTest(field=field):
                payload = d1_payload()
                payload.pop(field)
                with self.assertRaisesRegex(ValidationError, field):
                    ChamferOp.model_validate(payload)

    def test_distances_must_be_positive_finite_and_within_the_shared_limit(self):
        for field in ("distance_1", "distance_2"):
            for value in (0, -1, 100001, float("nan"), float("inf")):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValidationError):
                        ChamferOp.model_validate(d1_payload(**{field: value}))

    def test_d1_d2_rejects_size_alias_and_angle_fields(self):
        for change in (
            {"size": 1.0},
            {"distance": 1.0},
            {"angle_deg": 30.0},
            {"angle_reference": FACE},
        ):
            with self.subTest(change=change):
                with self.assertRaises(ValidationError):
                    ChamferOp.model_validate(d1_payload(**change))

    def test_d1_d2_fields_are_rejected_in_legacy_modes(self):
        for mode in ("equal_distance", "distance_angle"):
            for field, value in (
                ("distance_1", 2.0),
                ("distance_2", 3.0),
                ("reference_surface", FACE),
            ):
                with self.subTest(mode=mode, field=field):
                    payload = {
                        "op": "chamfer",
                        "label": "break_edge",
                        "references": EDGE,
                        "chamfer_type": mode,
                        "size": 1.0,
                        field: value,
                    }
                    if mode == "distance_angle":
                        payload.update(angle_deg=30.0, angle_reference=FACE)
                    with self.assertRaisesRegex(ValidationError, "d1_d2"):
                        ChamferOp.model_validate(payload)

    def test_reference_surface_selector_must_identify_one_surface(self):
        edge_selector = {
            "kind": "geometry_selector",
            "target": "edge",
            "endpoints_mm": [[0, 0, 0], [0, 0, 10]],
            "tolerance_mm": 0.001,
        }
        ambiguous_selector = {
            "kind": "geometry_selector",
            "target": "surface",
            "axis": [0, 0, 1],
            "radius_mm": 5,
            "center_mm": [0, 0, 0],
            "coaxial": "any",
            "tolerance_mm": 0.001,
        }
        for selector in (edge_selector, ambiguous_selector):
            with self.subTest(selector=selector):
                with self.assertRaises(ValidationError):
                    ChamferOp.model_validate(d1_payload(reference_surface=selector))


class StandaloneToolContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(mock.patch.object(server.startup, "require_ready"))

    async def submit(self, **arguments):
        def validated_submit(operations, *_args):
            return {"job_id": "fixture", "operations": validate_operations(operations)}

        with mock.patch.object(server.general, "submit", side_effect=validated_submit) as submit:
            result = await server.creo_chamfer("model", 7, "break_edge", **arguments)
        return result, submit.call_args.args[0]

    async def test_legacy_distance_call_normalizes_to_the_old_size_only_payload(self):
        result, _ = await self.submit(references=EDGE, distance=1.5)
        self.assertEqual(
            result["operations"],
            [{"op": "chamfer", "label": "break_edge", "size": 1.5, "references": EDGE}],
        )

    async def test_d1_d2_standalone_and_plan_normalize_identically(self):
        payload = d1_payload()
        arguments = {key: value for key, value in payload.items() if key not in ("op", "label")}
        result, submitted = await self.submit(**arguments)
        self.assertEqual(result["operations"], validate_operations([payload]))
        self.assertEqual(submitted, [payload])

    async def test_distance_angle_is_forwarded_through_the_same_contract(self):
        result, _ = await self.submit(
            references=EDGE,
            size=2.0,
            chamfer_type="distance_angle",
            angle_deg=70.0,
            angle_reference=FACE,
        )
        self.assertEqual(result["operations"][0]["angle_deg"], 70.0)
        self.assertEqual(result["operations"][0]["angle_reference"], FACE)
        self.assertNotIn("chamfer_type", result["operations"][0])

    async def test_standalone_invalid_d1_d2_is_rejected_before_a_job_result(self):
        with self.assertRaisesRegex(ToolError, "reference_surface"):
            await self.submit(
                references=EDGE,
                chamfer_type="d1_d2",
                distance_1=2.0,
                distance_2=3.0,
            )

    def test_standalone_and_plan_publish_the_new_parameters(self):
        tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
        standalone = tools["creo_chamfer"].input_schema
        for name in (
            "distance",
            "size",
            "chamfer_type",
            "angle_deg",
            "angle_reference",
            "distance_1",
            "distance_2",
            "reference_surface",
        ):
            self.assertIn(name, standalone["properties"])
        self.assertIn("references", standalone["required"])
        self.assertNotIn("distance", standalone["required"])
        plan = tools["creo_execute_plan"].input_schema["$defs"]["ChamferOp"]
        for name in ("distance_1", "distance_2", "reference_surface"):
            self.assertIn(name, plan["properties"])


class NativeTreeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = NATIVE.read_text(encoding="utf-8")
        start = source.index("static J generic_round(")
        end = source.index("static void generic_shell(", start)
        cls.source = source[start:end]

    def test_d1_d2_uses_the_verified_enum_reference_and_two_legs(self):
        for token in (
            "PRO_CHM_D1_X_D2",
            'op.at(angle_chamfer ? "angle_reference" : "reference_surface")',
            "PRO_E_RNDCH_REFERENCE_SURFACE",
            "PRO_E_RNDCH_LEG1",
            "PRO_E_RNDCH_LEG2",
            'op.at("distance_1")',
            'op.at("distance_2")',
            'details["chamfer_type"] = "d1_d2"',
            'details["distance_1"] = op.at("distance_1")',
            'details["distance_2"] = op.at("distance_2")',
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.source)
        self.assertNotIn("PRO_CHAMFER_D1_D2", self.source)

    def test_legacy_native_mappings_remain_present(self):
        for token in (
            "int dimensional_schema = PRO_CHM_D_X_D",
            "dimensional_schema = PRO_CHM_ANG_X_D",
            'real(leg, PRO_E_RNDCH_LEG_VALUE, op.at("size"))',
            'op.at(angle_chamfer ? "angle_deg" : "distance_2")',
            'details["chamfer_type"] = "distance_angle"',
            'details["chamfer_type"] = "equal_distance"',
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.source)


if __name__ == "__main__":
    unittest.main()
