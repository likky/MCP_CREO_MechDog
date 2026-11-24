"""Unit tests for 0.43.0 feedback batch (BUG-183, FEAT-082, BUG-184, FEAT-083, BUG-185)."""

from __future__ import annotations

import inspect
import math
import unittest

from pydantic import ValidationError

import bridge
import server
from creo_mechdog import (
    cut_geometry_context,
    geometry_deviation,
    operation_results,
    schema,
    sketch_regions,
)


class Bug183BsplineCutDiagnosticsTests(unittest.TestCase):
    """BUG-183: solved_section_area_mm2, b_spline_cut_risk, and symmetric/B-spline cut checks."""

    def test_cut_geometry_context_preserves_solved_section_area(self):
        raw = {
            "status": "no_material_removed",
            "operation": "extrude",
            "mode": "cut",
            "direction": "symmetric",
            "direction_sign": 1,
            "volume_mm3": {"before": 1194.94, "after": 1194.94, "removed": 0.0},
            "solved_section_area_mm2": 24.5,
            "native_section": {
                "available": True,
                "b_spline_entities": 1,
                "closed_contours": 1,
                "open_ends": 0,
                "solved_section_area_mm2": 24.5,
            },
        }
        norm = cut_geometry_context.normalize_cut_geometry_context(raw)
        self.assertTrue(norm["available"])
        self.assertAlmostEqual(norm["solved_section_area_mm2"], 24.5)
        self.assertAlmostEqual(norm["native_section"]["solved_section_area_mm2"], 24.5)

    def test_sketch_bspline_cut_risk_and_symmetric_cut_volume_check_fallback(self):
        result = {
            "operations": [
                {
                    "op": "sketch",
                    "label": "arm7_r1b",
                    "succeeded": True,
                    "profile": {
                        "analysis": "partial",
                        "area_status": "unavailable_unsupported_entities",
                        "material_area_mm2": None,
                    },
                    "native_section": {
                        "available": True,
                        "b_spline_entities": 1,
                        "closed_contours": 1,
                        "open_ends": 0,
                        "solved_section_area_mm2": 100.0,
                    },
                },
                {
                    "op": "extrude",
                    "label": "arm7_r1_cut",
                    "succeeded": True,
                    "material_removed_mm3": 9.9,
                    "solved_section_area_mm2": 100.0,
                    "extrude_depth": {
                        "effective_depth_type": "symmetric",
                        "effective_depth_mm": 3.0,
                    },
                    "native_section": {
                        "available": True,
                        "b_spline_entities": 1,
                        "closed_contours": 1,
                        "open_ends": 0,
                        "solved_section_area_mm2": 100.0,
                    },
                },
            ]
        }
        inputs = [
            {"op": "sketch", "label": "arm7_r1b"},
            {
                "op": "extrude",
                "label": "arm7_r1_cut",
                "sketch": "arm7_r1b",
                "mode": "cut",
                "direction": "symmetric",
                "depth": 3.0,
            },
        ]
        operation_results.annotate_cut_volume_check(result, inputs)

        sketch_rec = result["operations"][0]
        self.assertIn("b_spline_cut_risk", sketch_rec)
        self.assertEqual(sketch_rec["b_spline_cut_risk"]["b_spline_entities"], 1)
        self.assertTrue(sketch_rec["b_spline_cut_risk"]["advisory"])

        ext_rec = result["operations"][1]
        self.assertIn("cut_volume_check", ext_rec)
        chk = ext_rec["cut_volume_check"]
        self.assertEqual(chk["area_source"], "native_solved_section")
        self.assertAlmostEqual(chk["solved_section_area_mm2"], 100.0)
        self.assertAlmostEqual(chk["expected_prism_volume_mm3"], 300.0)
        self.assertTrue(chk["low_removal_warning"])
        self.assertTrue(chk["b_spline_cut_risk"])
        self.assertEqual(chk["b_spline_entities"], 1)

        compact = operation_results._status_core(sketch_rec, failed=False)
        self.assertAlmostEqual(compact["native_section"]["solved_section_area_mm2"], 100.0)
        self.assertIn("b_spline_cut_risk", compact)


class Feat082JpegOrthographicAndMatrixTests(unittest.TestCase):
    """FEAT-082: orthographic views (right/left/back/bottom) and custom 3x3 view_matrix."""

    def test_all_orthographic_views_accepted(self):
        for view in ("isometric", "front", "back", "top", "bottom", "left", "right"):
            opts = schema.JpegOptions(view=view, width_px=1200, height_px=900)
            self.assertEqual(opts.view, view)

    def test_valid_custom_view_matrix_accepted(self):
        s = math.sqrt(0.5)
        rot_z45 = [[s, s, 0.0], [-s, s, 0.0], [0.0, 0.0, 1.0]]
        opts = schema.JpegOptions(view_matrix=rot_z45)
        self.assertEqual(len(opts.view_matrix), 3)
        self.assertAlmostEqual(opts.view_matrix[0][0], s)

    def test_invalid_view_matrix_rejected(self):
        # Non-orthonormal
        with self.assertRaises(ValidationError):
            schema.JpegOptions(view_matrix=[[2, 0, 0], [0, 1, 0], [0, 0, 1]])
        # Left-handed reflection (det = -1)
        with self.assertRaises(ValidationError):
            schema.JpegOptions(view_matrix=[[-1, 0, 0], [0, 1, 0], [0, 0, 1]])
        # Wrong shape
        with self.assertRaises(ValidationError):
            schema.JpegOptions(view_matrix=[[1, 0], [0, 1]])
        # Boolean rejected
        with self.assertRaises(ValidationError):
            schema.JpegOptions(view_matrix=[[True, 0, 0], [0, 1, 0], [0, 0, 1]])


class Bug184SketchDisplacementReceiptTests(unittest.TestCase):
    """BUG-184: per-point displacement vectors in geometry_deviation and compact visibility."""

    def test_normalize_preserves_displaced_point_vectors(self):
        raw = {
            "available": True,
            "max_deviation_mm": 0.0455,
            "warning_threshold_mm": 0.001,
            "enforced": False,
            "tolerance_source": "default_autodim",
            "total": 1,
            "sample": [
                {
                    "entity": "chord_1",
                    "kind": "line",
                    "measurement": "endpoints",
                    "deviation_mm": 0.0455,
                    "point": "start",
                    "requested_mm": [-1.1734, -14.3145],
                    "actual_mm": [-1.1563, -14.36],
                    "delta_mm": [0.0171, -0.0455],
                }
            ],
            "truncated": False,
            "stages": {},
        }
        norm = geometry_deviation.normalize_geometry_deviation(raw)
        self.assertTrue(norm["exceeds_warning"])
        item = norm["sample"][0]
        self.assertEqual(item["point"], "start")
        self.assertEqual(item["requested_mm"], [-1.1734, -14.3145])
        self.assertEqual(item["actual_mm"], [-1.1563, -14.36])
        self.assertEqual(item["delta_mm"], [0.0171, -0.0455])

        compact = operation_results._status_core(
            {"op": "sketch", "label": "a7_s5", "geometry_deviation": norm}, failed=False
        )
        gd = compact["geometry_deviation"]
        self.assertEqual(gd["warning_threshold_mm"], 0.001)
        self.assertFalse(gd["enforced"])
        self.assertIn("displaced_sample", gd)
        self.assertEqual(gd["displaced_sample"][0]["entity"], "chord_1")
        self.assertEqual(gd["displaced_sample"][0]["delta_mm"], [0.0171, -0.0455])

    def test_sketch_tool_documents_autodim_enforcement(self):
        for fn in (server.creo_create_sketch, server.creo_update_sketch_geometry):
            sig = inspect.signature(fn)
            ann = sig.parameters["geometry_tolerance_mm"].annotation
            self.assertIn("autodim", str(ann).lower())


class Feat083RegionInteriorPointTests(unittest.TestCase):
    """FEAT-083: curve-aware interior_point_yz_mm region selection."""

    def test_selector_validation(self):
        sel = schema.SketchRegionSelector(interior_point_yz_mm=[5.0, 2.5])
        self.assertEqual(sel.interior_point_yz_mm, [5.0, 2.5])
        self.assertIsNone(sel.signature_yz_mm)

        with self.assertRaises(ValidationError):
            schema.SketchRegionSelector()
        with self.assertRaises(ValidationError):
            schema.SketchRegionSelector(interior_point_yz_mm=[1.0, True])

    def test_interior_point_selects_arc_crescent_sharing_endpoints(self):
        # A chord + two arcs sharing the exact same endpoints (0,0) and (10,0):
        # upper semicircle (y > 0) and lower semicircle (y < 0).
        # signature_yz_mm alone cannot distinguish them, but interior_point_yz_mm can!
        plan = [
            {
                "op": "sketch",
                "label": "crescent_src",
                "plane": "YZ",
                "entities": [
                    {"type": "line", "name": "chord", "start": [0, 0], "end": [10, 0]},
                    {
                        "type": "arc",
                        "name": "upper_arc",
                        "center": [5, 0],
                        "radius": 5,
                        "start_angle": 0,
                        "end_angle": 180,
                        "dir": "ccw",
                    },
                    {
                        "type": "arc",
                        "name": "lower_arc",
                        "center": [5, 0],
                        "radius": 5,
                        "start_angle": 0,
                        "end_angle": 180,
                        "dir": "cw",
                    },
                ],
            },
            {
                "op": "extrude",
                "label": "cut_upper",
                "sketch": "crescent_src",
                "mode": "cut",
                "depth": 3.0,
                "region": {"interior_point_yz_mm": [5.0, 2.5]},
            },
        ]
        adapted, records = sketch_regions.adapt_region_extrudes(plan)
        self.assertEqual(len(records), 1)
        self.assertEqual(sorted(records[0]["entity_names"]), ["chord", "upper_arc"])
        self.assertEqual(records[0]["interior_point_yz_mm"], [5.0, 2.5])

    def test_interior_point_selects_bspline_subregion(self):
        # Rectangle [0,10] x [0,10] split horizontally by a curved B-spline from (0,5) to (10,5).
        plan = [
            {
                "op": "sketch",
                "label": "bspline_src",
                "plane": "YZ",
                "entities": [
                    {"type": "line", "name": "bot", "start": [0, 0], "end": [10, 0]},
                    {"type": "line", "name": "right", "start": [10, 0], "end": [10, 10]},
                    {"type": "line", "name": "top", "start": [10, 10], "end": [0, 10]},
                    {"type": "line", "name": "left", "start": [0, 10], "end": [0, 0]},
                    {
                        "type": "b_spline",
                        "name": "sp_mid",
                        "degree": 3,
                        "control_points": [[0, 5], [3, 7], [7, 3], [10, 5]],
                    },
                ],
            },
            {
                "op": "extrude",
                "label": "cut_top_band",
                "sketch": "bspline_src",
                "mode": "cut",
                "depth": 2.0,
                "region": {"interior_point_yz_mm": [5.0, 8.5]},
            },
        ]
        adapted, records = sketch_regions.adapt_region_extrudes(plan)
        self.assertEqual(len(records), 1)
        names = records[0]["entity_names"]
        self.assertIn("top", names)
        self.assertIn("sp_mid", names)
        self.assertNotIn("bot", names)

    def test_interior_point_outside_raises(self):
        plan = [
            {
                "op": "sketch",
                "label": "box_src",
                "plane": "YZ",
                "entities": [
                    {"type": "line", "name": "l1", "start": [0, 0], "end": [10, 0]},
                    {"type": "line", "name": "l2", "start": [10, 0], "end": [10, 10]},
                    {"type": "line", "name": "l3", "start": [10, 10], "end": [0, 10]},
                    {"type": "line", "name": "l4", "start": [0, 10], "end": [0, 0]},
                ],
            },
            {
                "op": "extrude",
                "label": "cut_out",
                "sketch": "box_src",
                "mode": "cut",
                "depth": 2.0,
                "region": {"interior_point_yz_mm": [50.0, 50.0]},
            },
        ]
        with self.assertRaisesRegex(ValueError, "lies inside none"):
            sketch_regions.adapt_region_extrudes(plan)


class Bug185GetJobSchemaTests(unittest.TestCase):
    """BUG-185: creo_get_job section/cursor require detail=full documented in schema & error."""

    def test_creo_get_job_parameter_descriptions(self):
        sig = inspect.signature(server.creo_get_job)
        self.assertIn('detail="full"', str(sig.parameters["section"].annotation))
        self.assertIn('detail="full"', str(sig.parameters["cursor"].annotation))
        self.assertIn('detail="compact"', str(sig.parameters["sections"].annotation))

    def test_get_job_compact_with_section_error_hint(self):
        with self.assertRaises(ValueError) as ctx:
            bridge.get_job("0" * 32, detail="compact", section="operations_result")
        msg = str(ctx.exception)
        self.assertIn("section/cursor require detail=full", msg)
        self.assertIn("sections=[...]", msg)


if __name__ == "__main__":
    unittest.main()
