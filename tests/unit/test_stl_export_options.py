"""BUG-130 Task 6: explicit STL quality options.

The STL export has always passed 0.05 mm / 0.1 to Creo. This contract makes that
request explicit and validated, without changing the historical call shape.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from creo_mechdog import schema

try:
    import server
except Exception:  # pragma: no cover - surfaced by the sentinels below
    server = None


def export_op(**fields):
    return schema.ExportOp.model_validate({"op": "export", "format": "stl", **fields})


class StlOptionsSchemaTest(unittest.TestCase):
    def test_omitting_options_keeps_the_previous_request(self) -> None:
        operation = schema.ExportOp.model_validate({"op": "export", "format": "stl"})
        self.assertIsNone(operation.stl_options)

    def test_defaults_match_the_historical_quality_request(self) -> None:
        options = export_op(stl_options={}).stl_options
        self.assertAlmostEqual(options.chord_height_mm, 0.05)
        self.assertAlmostEqual(options.angle_control, 0.1)

    def test_accepts_a_valid_request(self) -> None:
        options = export_op(
            stl_options={"chord_height_mm": 0.02, "angle_control": 0.05}
        ).stl_options
        self.assertAlmostEqual(options.chord_height_mm, 0.02)
        self.assertAlmostEqual(options.angle_control, 0.05)

    def test_rejects_values_that_would_not_mean_anything_to_the_sdk(self) -> None:
        bad = (
            {"chord_height_mm": True},
            {"angle_control": False},
            {"chord_height_mm": "0.05"},
            {"chord_height_mm": 0},
            {"chord_height_mm": -0.05},
            {"chord_height_mm": float("nan")},
            {"chord_height_mm": float("inf")},
            {"angle_control": -0.01},
            {"angle_control": 1.01},
            {"angle_control": float("nan")},
            {"angle_control": float("inf")},
            {"chord_height_mm": 0.05, "unexpected": 1},
        )
        for request in bad:
            with self.subTest(request=request):
                with self.assertRaises(Exception):
                    export_op(stl_options=request)

    def test_rejects_options_for_other_formats(self) -> None:
        with self.assertRaises(Exception):
            schema.ExportOp.model_validate(
                {"op": "export", "format": "step", "stl_options": {"chord_height_mm": 0.05}}
            )

    def test_plan_validation_keeps_the_requested_values(self) -> None:
        dumped = schema.validate_operations(
            [
                {
                    "op": "export",
                    "format": "stl",
                    "stl_options": {"chord_height_mm": 0.02, "angle_control": 0.05},
                }
            ]
        )
        self.assertEqual(dumped[0]["stl_options"]["chord_height_mm"], 0.02)
        self.assertEqual(dumped[0]["stl_options"]["angle_control"], 0.05)

    def test_plan_validation_omits_absent_options(self) -> None:
        dumped = schema.validate_operations([{"op": "export", "format": "stl"}])
        self.assertNotIn("stl_options", dumped[0])


class ExportToolPassThroughTest(unittest.TestCase):
    def setUp(self) -> None:
        if server is None:  # pragma: no cover
            self.fail("server import unavailable")

    def submit(self, **kwargs):
        with mock.patch.object(server, "invoke", new_callable=mock.AsyncMock) as invoke:
            invoke.return_value = {"job_id": "fixture"}
            asyncio.run(server.creo_export_model("model", **kwargs))
            return invoke.call_args.args[1]

    def test_default_export_keeps_the_old_operation_shape(self) -> None:
        self.assertEqual(self.submit(), [{"op": "export", "format": "step"}])

    def test_stl_options_are_forwarded(self) -> None:
        operations = self.submit(
            format="stl", stl_options={"chord_height_mm": 0.02, "angle_control": 0.05}
        )
        self.assertEqual(
            operations,
            [
                {
                    "op": "export",
                    "format": "stl",
                    "stl_options": {"chord_height_mm": 0.02, "angle_control": 0.05},
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
