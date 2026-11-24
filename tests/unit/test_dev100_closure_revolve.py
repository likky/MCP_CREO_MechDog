"""DEV-100 (§4, §5, §8, §9): sketch closure welding, open-end diagnostics, revolve inputs."""

import asyncio
import math
import unittest
from pathlib import Path

import server
from creo_mechdog.endpoint_welding import (
    prepare_endpoint_weld,
    prepare_operations,
    weld_eligibility,
)
from creo_mechdog.schema import validate_operations

ROOT = Path(__file__).resolve().parents[2]


def _gapped_slot_profile(gap_mm: float = 4.33418842e-4) -> list[dict]:
    """Four-segment line-arc-line-arc slot whose line ends miss the arc ends by gap_mm."""
    # Left semicircle centered at (0, 0), radius 5, angles 90..270 -> (0, 5) to (0, -5)
    # Right semicircle centered at (20, 0), radius 5, angles -90..90 -> (20, -5) to (20, 5)
    return [
        {
            "type": "arc",
            "name": "left_arc",
            "center": [0.0, 0.0],
            "radius": 5.0,
            "start_angle": 90.0,
            "end_angle": 270.0,
        },
        {
            "type": "line",
            "name": "bottom",
            "start": [gap_mm, -5.0],
            "end": [20.0 - gap_mm, -5.0],
        },
        {
            "type": "arc",
            "name": "right_arc",
            "center": [20.0, 0.0],
            "radius": 5.0,
            "start_angle": -90.0,
            "end_angle": 90.0,
        },
        {
            "type": "line",
            "name": "top",
            "start": [20.0 - gap_mm, 5.0],
            "end": [gap_mm, 5.0],
        },
    ]


class SketchClosureWeldingTests(unittest.TestCase):
    def test_closure_tolerance_drives_snap_on_multi_gap_arc_line_profile(self):
        entities = _gapped_slot_profile(4.33418842e-4)
        # Default 1e-4 mm cluster scale does not catch a 4.33e-4 mm gap.
        default_receipt = prepare_endpoint_weld(entities, snap=True)
        self.assertFalse(default_receipt["snap"]["applied"])
        self.assertEqual(default_receipt["threshold_source"], "closure_diagnostic_cluster")

        # Explicit closure_tolerance_mm=0.005 catches all four arc-line seams and anchors
        # the line endpoints onto the exact arc endpoints without moving either arc.
        snapped_receipt = prepare_endpoint_weld(entities, snap=True, cluster_tolerance_mm=0.005)
        self.assertTrue(snapped_receipt["snap"]["applied"])
        self.assertEqual(snapped_receipt["threshold_mm"], 0.005)
        self.assertEqual(snapped_receipt["threshold_source"], "closure_tolerance_mm")
        self.assertEqual(len(snapped_receipt["snap"]["pairs"]), 4)
        self.assertEqual(snapped_receipt["snap"]["residual_max_mm"], 0.0)
        self.assertAlmostEqual(snapped_receipt["snap"]["max_shift_mm"], 4.33418842e-4, places=9)

        rewritten = snapped_receipt["_snapped_entities"]
        self.assertEqual(rewritten[0], entities[0])
        self.assertEqual(rewritten[2], entities[2])
        self.assertAlmostEqual(rewritten[1]["start"][0], 0.0, places=12)
        self.assertAlmostEqual(rewritten[1]["end"][0], 20.0, places=12)
        self.assertAlmostEqual(rewritten[3]["start"][0], 20.0, places=12)
        self.assertAlmostEqual(rewritten[3]["end"][0], 0.0, places=12)

    def test_same_plan_validate_operations_admits_snappable_slot_with_closure_tolerance(self):
        plan = [
            {
                "op": "sketch",
                "label": "slot_s",
                "plane": "XY",
                "entities": _gapped_slot_profile(4.33418842e-4),
                "dimensioning": "coordinates",
                "closure_tolerance_mm": 0.005,
                "snap_endpoints": True,
            },
            {
                "op": "extrude",
                "label": "slot_ext",
                "sketch": "slot_s",
                "depth": 5.0,
            },
        ]
        validated = validate_operations(plan)
        prepared = prepare_operations(validated)
        self.assertTrue(prepared[0]["snap_endpoint_receipt"]["snap"]["applied"])
        self.assertEqual(prepared[0]["snap_endpoint_receipt"]["snap"]["residual_max_mm"], 0.0)

    def test_snap_respects_max_endpoint_move_mm_on_open_chain_seams(self):
        entities = _gapped_slot_profile(4.33418842e-4)
        receipt = prepare_endpoint_weld(
            entities, snap=True, max_move_mm=1e-4, cluster_tolerance_mm=0.005
        )
        self.assertFalse(receipt["snap"]["applied"])

    def test_weld_eligibility_uses_explicit_cluster_tolerance(self):
        entities = _gapped_slot_profile(4.33418842e-4)
        default_elig = weld_eligibility(entities)
        self.assertEqual(default_elig["candidate_pairs"], 0)
        widened = weld_eligibility(entities, cluster_tolerance_mm=0.005)
        self.assertEqual(widened["threshold_mm"], 0.005)
        self.assertEqual(widened["candidate_pairs"], 4)

    def test_native_open_end_diagnostics_source_guard(self):
        source = (ROOT / "native" / "generic.cpp").read_text(encoding="utf-8")
        self.assertIn("Nearest open ends:", source)
        self.assertIn('"nearest_point"', source)
        self.assertIn('staged["native_section"] = section;', source)


class RevolveSketchPointsAndRadiansTests(unittest.TestCase):
    def test_revolve_axis_accepts_sketch_points_and_shorthand(self):
        full = {
            "op": "revolve",
            "label": "rev1",
            "sketch": "s1",
            "axis": {"kind": "sketch_points", "start_mm": [0, 0], "end_mm": [0, 16.285538]},
        }
        shorthand = {
            "op": "revolve",
            "label": "rev1",
            "sketch": "s1",
            "axis": {"start_mm": [0, 0], "end_mm": [0, 16.285538]},
        }
        expected = {
            "kind": "sketch_points",
            "start_mm": [0.0, 0.0],
            "end_mm": [0.0, 16.285538],
        }
        self.assertEqual(validate_operations([full])[0]["axis"], expected)
        self.assertEqual(validate_operations([shorthand])[0]["axis"], expected)

    def test_revolve_axis_rejects_degenerate_or_malformed_sketch_points(self):
        bad_axes = [
            {"start_mm": [0, 0], "end_mm": [0, 0]},
            {"kind": "sketch_points", "start_mm": [0, 0], "end_mm": [0, 1e-9]},
            {"kind": "sketch_points", "start_mm": [0, 0, 0], "end_mm": [0, 10, 0]},
            {"kind": "sketch_points", "start_mm": [True, 0], "end_mm": [0, 10]},
            {"kind": "sketch_points", "start_mm": [float("nan"), 0], "end_mm": [0, 10]},
            {"start_mm": [0, 0], "end_mm": [0, 10], "extra": 1},
        ]
        for axis in bad_axes:
            with self.subTest(axis=axis), self.assertRaises(ValueError):
                validate_operations([{"op": "revolve", "label": "r", "sketch": "s", "axis": axis}])

    def test_revolve_angle_rad_and_full_circle_clamp(self):
        # Reported TXT value: 6.28319 rad = 360.000269 deg -> clamped to 360.0
        clamped = validate_operations(
            [{"op": "revolve", "label": "r1", "sketch": "s1", "angle_rad": 6.28319}]
        )[0]
        self.assertEqual(clamped["angle"], 360.0)
        self.assertNotIn("angle_rad", clamped)
        self.assertAlmostEqual(clamped["angle_clamped_from_deg"], math.degrees(6.28319), places=9)

        # Half turn in radians: no clamp field emitted.
        half = validate_operations(
            [{"op": "revolve", "label": "r2", "sketch": "s1", "angle_rad": math.pi}]
        )[0]
        self.assertAlmostEqual(half["angle"], 180.0, places=12)
        self.assertNotIn("angle_clamped_from_deg", half)

        # Degree value just above 360 within 1e-3 deg also clamps.
        deg_clamp = validate_operations(
            [{"op": "revolve", "label": "r3", "sketch": "s1", "angle": 360.0005}]
        )[0]
        self.assertEqual(deg_clamp["angle"], 360.0)
        self.assertAlmostEqual(deg_clamp["angle_clamped_from_deg"], 360.0005, places=9)

        # Omitting both defaults to 360 deg.
        default_op = validate_operations([{"op": "revolve", "label": "r4", "sketch": "s1"}])[0]
        self.assertEqual(default_op["angle"], 360.0)
        self.assertNotIn("angle_clamped_from_deg", default_op)

    def test_revolve_angle_rejects_excess_and_conflicts(self):
        bad_ops = [
            {"op": "revolve", "label": "r", "sketch": "s", "angle": 360.01},
            {"op": "revolve", "label": "r", "sketch": "s", "angle_rad": 6.3},
            {"op": "revolve", "label": "r", "sketch": "s", "angle": 0},
            {"op": "revolve", "label": "r", "sketch": "s", "angle_rad": -1.0},
            {"op": "revolve", "label": "r", "sketch": "s", "angle": True},
            {"op": "revolve", "label": "r", "sketch": "s", "angle": 180, "angle_rad": math.pi},
        ]
        for op in bad_ops:
            with self.subTest(op=op), self.assertRaises(ValueError):
                validate_operations([op])

    def test_sketch_tolerance_tool_descriptions_document_auto_split(self):
        tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
        for name in ("creo_create_sketch", "creo_update_sketch_geometry"):
            desc = tools[name].input_schema["properties"]["geometry_tolerance_mm"]["description"]
            self.assertIn("autodim", desc)
            self.assertIn("<10", desc)
            self.assertIn(">=10", desc)
            self.assertIn("enforced=true", desc)


if __name__ == "__main__":
    unittest.main()
