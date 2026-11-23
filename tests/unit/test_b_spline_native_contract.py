"""FEAT-066: native wiring for the exact NURBS sketch entity.

These are static contract checks. They cannot prove the Creo kernel accepts
PRO_2D_B_SPLINE; the live Creo 12.4 run owns that evidence. They do guard the
carrier fields and every read-back path that would otherwise treat the entity
as unknown.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / "native"


class BSplineNativeContractTests(unittest.TestCase):
    def test_generic_sketch_writer_uses_pro2dbsplinedef(self):
        source = (NATIVE / "generic.cpp").read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count('type == "b_spline"'), 2)
        self.assertIn("Pro2dBSplinedef", source)
        self.assertIn("spline.type = PRO_2D_B_SPLINE", source)
        for field in (
            "spline.degree",
            "spline.num_knots",
            "spline.params",
            "spline.num_c_points",
            "spline.c_pnts",
        ):
            self.assertIn(field, source)
        self.assertEqual(source.count("add_section_bspline(section, e, project)"), 2)
        for array_field in ("params", "c_pnts", "weights"):
            self.assertIn(f"(ProArray *)&spline.{array_field}", source)
            self.assertIn(f"ProArrayFree((ProArray *)&value.{array_field})", source)

    def test_profile_analysis_handles_b_spline(self):
        source = (NATIVE / "generic.cpp").read_text(encoding="utf-8")
        self.assertIn("def->type == PRO_2D_B_SPLINE", source)
        self.assertIn("bspline->c_pnts[0]", source)
        self.assertIn("bspline->num_c_points - 1", source)

    def test_coordinates_readback_and_deviation_handle_b_spline(self):
        source = (NATIVE / "sketch_coordinates.cpp").read_text(encoding="utf-8")
        self.assertIn('return "b_spline"', source)
        self.assertIn("PRO_2D_B_SPLINE", source)
        self.assertIn('row["control_points_xy"]', source)
        self.assertIn('row["knots"]', source)
        self.assertIn('measurement = "control_points"', source)
        self.assertIn("knot vector or control point count changed", source)

    def test_edit_probe_handles_b_spline_without_offering_rewrites(self):
        source = (NATIVE / "sketch_edit.cpp").read_text(encoding="utf-8")
        self.assertIn('type == "b_spline"', source)
        self.assertIn("PRO_2D_B_SPLINE", source)
        self.assertIn("stored_knots", source)
        self.assertIn("stored_control_points", source)


if __name__ == "__main__":
    unittest.main()
