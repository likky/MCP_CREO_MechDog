"""FEAT-065: independent offline checks for the original TXT bulb curves."""

from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creo_mechdog.frigate_bulb import (
    audit,
    build_plan,
    evaluate,
    extract_source,
    join_line_bezier,
)

ROOT = Path(__file__).resolve().parents[2]


def bernstein(points: list[list[float]], t: float) -> list[float]:
    """Independent cubic polynomial, not the production de Boor evaluator."""
    return [
        sum(math.comb(3, i) * (1 - t) ** (3 - i) * t**i * p[axis] for i, p in enumerate(points))
        for axis in range(3)
    ]


class FrigateBulbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((ROOT / "examples/frigate_bulb_source.json").read_text("utf-8"))

    def test_source_excerpt_round_trip_and_known_coordinates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.txt"
            path.write_text(self.source["source"]["excerpt"], encoding="utf-8")
            actual = extract_source(path)
        self.assertEqual(actual["geometry"], self.source["geometry"])
        self.assertEqual(actual["geometry"]["tip_m"], [78.094736179, 0, -5.6])
        self.assertEqual(actual["geometry"]["rear_section"]["control_points"][3][1], 1.81325)
        self.assertEqual(actual["source"]["units"], "m")

    def test_line_and_bezier_are_exactly_preserved_on_both_sides_of_join(self):
        geometry = self.source["geometry"]
        for prefix in ("upper", "lower"):
            with self.subTest(prefix=prefix):
                line = geometry[prefix + "_line_m"]
                bend = geometry[prefix + "_bend"]
                curve = join_line_bezier(line, bend)
                reverse = list(reversed(bend["control_points"]))
                for i in range(201):
                    t = i / 200
                    expected_line = [line[1][j] * (1 - t) + line[0][j] * t for j in range(3)]
                    self.assertLess(math.dist(evaluate(curve, t), expected_line), 1e-12)
                    self.assertLess(math.dist(evaluate(curve, 1 + t), bernstein(reverse, t)), 1e-12)
                for t in (math.nextafter(1, 0), 1, math.nextafter(1, 2)):
                    self.assertLess(math.dist(evaluate(curve, t), line[0]), 1e-12)
                self.assertEqual(curve["knots"], [0] * 4 + [1] * 3 + [2] * 4)
                self.assertEqual(len(curve["control_points"]), 7)

    def test_join_refuses_gap_or_non_unit_weights_instead_of_repairing(self):
        geometry = self.source["geometry"]
        bad = copy.deepcopy(geometry["upper_bend"])
        bad["control_points"][-1][2] += 0.001
        with self.assertRaisesRegex(ValueError, "join"):
            join_line_bezier(geometry["upper_line_m"], bad)
        bad = copy.deepcopy(geometry["upper_bend"])
        bad["weights"][1] = 2
        with self.assertRaisesRegex(ValueError, "unit weights"):
            join_line_bezier(geometry["upper_line_m"], bad)

    def test_minimal_plan_is_public_payload_with_one_entity_per_curve(self):
        from creo_mechdog.schema import validate_operations

        plan = build_plan(self.source)
        validate_operations(copy.deepcopy(plan["operations"]))
        sketches = [op for op in plan["operations"] if op["op"] == "sketch"]
        self.assertEqual(len(sketches), 5)
        self.assertTrue(all(len(op["entities"]) == 1 for op in sketches))
        loft = plan["operations"][-1]
        self.assertEqual(loft["guides"], ["bulb_upper", "bulb_side", "bulb_lower"])
        # Creo 12.4 live comparison: the same three-guide network only
        # regenerated with the convergence point last (2026-11-16).
        self.assertEqual(loft["sections"][-1], {"kind": "datum_point_feature", "label": "bulb_tip"})
        self.assertEqual(loft["sections"][:2], ["bulb_rear", "bulb_mid"])
        self.assertEqual(loft["interpolation"], "smooth")
        side = next(op for op in sketches if op["label"] == "bulb_side")
        self.assertEqual(side["offset"], -5600)
        self.assertEqual(len(side["entities"][0]["control_points"]), 5)
        self.assertNotIn("model_id", plan)

    def test_audit_checks_source_geometry_and_plan_not_only_schema(self):
        plan = build_plan(self.source)
        report = audit(self.source, plan)
        self.assertTrue(report["passed"], report)
        self.assertFalse(report["creo_tested"])
        self.assertEqual(len(report["intersections"]), 9)
        self.assertLess(report["max_join_error_mm"], 1e-7)
        self.assertLess(report["max_frame_error_mm"], 1e-7)
        damaged = copy.deepcopy(plan)
        damaged["operations"][0]["entities"][0]["control_points"][0][0] += 1
        failed = audit(self.source, damaged)
        self.assertFalse(failed["passed"])
        self.assertGreater(failed["max_frame_error_mm"], 0.9)

    def test_source_control_point_is_not_a_curve_extremum(self):
        section = self.source["geometry"]["rear_section"]
        self.assertAlmostEqual(evaluate(section, 0.5)[1], 1.8, places=9)
        self.assertAlmostEqual(evaluate(section, 0.5)[2], -5.6, places=9)
        self.assertGreater(max(p[1] for p in section["control_points"]), 1.81)

    def test_original_lower_guide_overshoot_is_preserved(self):
        report = audit(self.source, build_plan(self.source))
        # Independent derivative-root oracle on the original cubic, rounded
        # here to micrometres; the tip is not the maximum X of the guide.
        self.assertAlmostEqual(report["lower_guide_forward_of_tip_mm"], 0.323561, places=5)
        self.assertGreater(report["lower_guide_max_x_mm"], 78094.736179)

    def test_explicit_scale_and_source_immutability(self):
        before = copy.deepcopy(self.source)
        full = build_plan(self.source)
        small = build_plan(self.source, mm_per_m=10)
        for a, b in zip(full["operations"][:-1], small["operations"][:-1]):
            if a["op"] == "sketch":
                self.assertAlmostEqual(a["offset"], b["offset"] * 100)
                for p, q in zip(
                    a["entities"][0]["control_points"], b["entities"][0]["control_points"]
                ):
                    self.assertLess(math.dist(p, [v * 100 for v in q]), 1e-7)
        self.assertTrue(audit(self.source, small, mm_per_m=10)["passed"])
        self.assertEqual(self.source, before)
        for scale in (0, -1, math.nan, math.inf, True):
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                build_plan(self.source, mm_per_m=scale)

    def test_source_intersection_failure_is_reported_without_adjustment(self):
        changed = copy.deepcopy(self.source)
        changed["geometry"]["side"]["control_points"][0][1] += 0.001
        before = copy.deepcopy(changed)
        report = audit(changed, build_plan(changed))
        self.assertFalse(report["passed"])
        self.assertGreater(report["max_intersection_gap_mm"], 0.9)
        self.assertEqual(changed, before)

    def test_small_snapshot_edit_cannot_pass_by_comparing_geometry_with_itself(self):
        changed = copy.deepcopy(self.source)
        changed["geometry"]["rear_section"]["control_points"][2][1] += 1e-6
        report = audit(changed, build_plan(changed))
        self.assertLess(report["max_intersection_gap_mm"], report["network_tolerance_mm"])
        self.assertFalse(report["passed"])

    def test_cli_refuses_different_original_bytes_even_when_geometry_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "excerpt_only.txt"
            path.write_text(self.source["source"]["excerpt"], encoding="utf-8")
            output = folder / "output"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/prepare_frigate_bulb.py"),
                    "--source",
                    str(path),
                    "--output-dir",
                    str(output),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((output / "report.json").read_text("utf-8"))
            self.assertTrue(report["provenance"]["geometry_matches_frozen"])
            self.assertFalse(report["provenance"]["original_file_sha256_matches_frozen"])
            self.assertFalse(report["passed"])


if __name__ == "__main__":
    unittest.main()
