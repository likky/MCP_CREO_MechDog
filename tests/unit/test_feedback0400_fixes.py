"""Unit tests for 0.40.0 feedback fixes (BUG-179..182, FEAT-080..081)."""

from __future__ import annotations

import math
import unittest
from pathlib import Path

from pydantic import ValidationError

from creo_mechdog import compact_sections, model_queries, operation_results, query_client
from creo_mechdog.schema import ChamferOp, MirrorOp, ShellOp, validate_operations
from creo_mechdog.sketch_region_split import (
    clamped_uniform_knots,
    eval_bspline,
    split_bspline_at,
    split_intersecting_entities,
)
from creo_mechdog.sketch_regions import adapt_region_extrudes

ROOT = Path(__file__).resolve().parents[2]


class Bug179ChamferTests(unittest.TestCase):
    def test_chamfer_propagate_validation(self):
        base = {
            "op": "chamfer",
            "label": "chm1",
            "size": 5.0,
            "references": [{"edge": {"kind": "edge", "id": 12}}],
        }
        op_single = ChamferOp.model_validate({**base, "propagate": "single"})
        self.assertEqual(op_single.propagate, "single")
        op_chain = ChamferOp.model_validate({**base, "propagate": "chain"})
        self.assertEqual(op_chain.propagate, "chain")
        op_default = ChamferOp.model_validate(base)
        self.assertIsNone(op_default.propagate)
        with self.assertRaises(ValidationError):
            ChamferOp.model_validate({**base, "propagate": "all"})

    def test_chamfer_type_description_documents_exclude_true(self):
        desc = ChamferOp.model_fields["chamfer_type"].description or ""
        self.assertIn("exclude=True", desc)
        self.assertIn("dump_plan_operations", desc)

    def test_chamfer_and_round_receipt_keys_in_compact_sections(self):
        for key in (
            "chamfered_edge_length_mm",
            "created_surface_count",
            "created_surface_area_mm2",
            "round_kind",
            "volume_delta_mm3",
            "g2_verification",
            "body_id",
        ):
            self.assertIn(key, compact_sections.OPERATION_KEYS)
        self.assertIn("round_failure", operation_results.FAILED_EVIDENCE_KEYS)


class Feat080ShellMirrorInspectTests(unittest.TestCase):
    def test_shell_body_id_validation(self):
        base = {"op": "shell", "label": "sh1", "thickness": 2.0}
        self.assertIsNone(ShellOp.model_validate(base).body_id)
        self.assertEqual(ShellOp.model_validate({**base, "body_id": -5778}).body_id, -5778)
        self.assertEqual(ShellOp.model_validate({**base, "body_id": 251}).body_id, 251)
        for bad in (0, True, False, "251", 1.5, 2**32):
            with self.assertRaises(ValidationError):
                ShellOp.model_validate({**base, "body_id": bad})

    def test_mirror_feature_ref_error_lists_workarounds(self):
        with self.assertRaises(ValidationError) as ctx:
            MirrorOp.model_validate(
                {
                    "op": "mirror",
                    "label": "m1",
                    "plane": {"kind": "datum_plane", "label": "RIGHT"},
                    "references": [{"kind": "feature", "label": "boss1"}],
                }
            )
        msg = str(ctx.exception)
        self.assertIn("kind:'part'", msg)
        self.assertIn("kind:'quilt'", msg)
        self.assertIn("recreate", msg.lower())

    def test_inspect_page_includes_total_count_and_page_count(self):
        model = {
            "model_id": "m1",
            "model_name": "test_part",
            "model_type": "part",
            "revision": 1,
            "status": "ready",
            "inspection": {
                "edges": [{"id": i, "length_mm": 10.0} for i in range(1, 8)],
                "surfaces": [],
                "features": [],
            },
        }
        p1 = model_queries.inspect_page(model, detail="full", section="edges", limit=3)
        self.assertEqual(p1["total_count"], 7)
        self.assertEqual(p1["page_count"], 3)
        self.assertEqual(p1["returned_count"], 3)
        self.assertFalse(p1["complete"])
        p2 = model_queries.inspect_page(
            model, detail="full", section="edges", limit=3, cursor=p1["next_cursor"]
        )
        self.assertEqual(p2["total_count"], 7)
        self.assertEqual(p2["page_count"], 3)
        p3 = model_queries.inspect_page(
            model, detail="full", section="edges", limit=3, cursor=p2["next_cursor"]
        )
        self.assertEqual(p3["total_count"], 7)
        self.assertEqual(p3["page_count"], 1)
        self.assertTrue(p3["complete"])

    def test_query_client_strips_total_count_and_page_count(self):
        source = (ROOT / "src/creo_mechdog/query_client.py").read_text(encoding="utf-8")
        self.assertIn('"total_count"', source)
        self.assertIn('"page_count"', source)
        self.assertTrue(hasattr(query_client, "read_full_model"))


class Bug181SketchRegionSplitTests(unittest.TestCase):
    def test_boehm_bspline_split_is_exact(self):
        ctrl = [[0.0, 0.0], [5.0, 12.0], [15.0, -6.0], [20.0, 10.0], [30.0, 4.0]]
        degree = 3
        knots = clamped_uniform_knots(len(ctrl), degree)
        u_split = 0.42
        (l_ctrl, l_knots, _), (r_ctrl, r_knots, _) = split_bspline_at(ctrl, degree, knots, u_split)
        # Verify left half matches original on [0, u_split]
        for k in range(11):
            frac = k / 10.0
            p_orig = eval_bspline(ctrl, degree, knots, frac * u_split)
            p_left = eval_bspline(l_ctrl, degree, l_knots, frac)
            self.assertLess(math.dist(p_orig, p_left), 1e-11)
        # Verify right half matches original on [u_split, 1]
        for k in range(11):
            frac = k / 10.0
            p_orig = eval_bspline(ctrl, degree, knots, u_split + frac * (1.0 - u_split))
            p_right = eval_bspline(r_ctrl, degree, r_knots, frac)
            self.assertLess(math.dist(p_orig, p_right), 1e-11)

    def test_bspline_crossing_box_splits_into_three_matchable_regions(self):
        # Outer 30x10 rectangle as 4 lines on YZ plane, crossed by two cubic B-splines
        # at x=10 and x=20 (slightly curved in the middle, crossing y=0 and y=10).
        bs1 = {
            "type": "b_spline",
            "name": "bs1",
            "degree": 3,
            "control_points": [[10.0, -2.0], [11.0, 3.0], [9.0, 7.0], [10.0, 12.0]],
        }
        bs2 = {
            "type": "b_spline",
            "name": "bs2",
            "degree": 3,
            "control_points": [[20.0, -2.0], [21.0, 3.0], [19.0, 7.0], [20.0, 12.0]],
        }
        sketch = {
            "op": "sketch",
            "label": "arm7_s7",
            "plane": "YZ",
            "offset": 0.0,
            "entities": [
                {"type": "line", "name": "bot", "start": [0.0, 0.0], "end": [30.0, 0.0]},
                {"type": "line", "name": "right", "start": [30.0, 0.0], "end": [30.0, 10.0]},
                {"type": "line", "name": "top", "start": [30.0, 10.0], "end": [0.0, 10.0]},
                {"type": "line", "name": "left", "start": [0.0, 10.0], "end": [0.0, 0.0]},
                bs1,
                bs2,
            ],
        }
        pieces, did_split = split_intersecting_entities(sketch["entities"])
        self.assertTrue(did_split)
        # Find exact intersection x-coordinates on y=0 and y=10 from split pieces
        bs1_mid = [
            p
            for p in pieces
            if p["name"].startswith("bs1_s")
            and abs(p["control_points"][0][1] - 0.0) < 1e-3
            and abs(p["control_points"][-1][1] - 10.0) < 1e-3
        ]
        self.assertEqual(len(bs1_mid), 1)
        x1_bot = bs1_mid[0]["control_points"][0][0]
        x1_top = bs1_mid[0]["control_points"][-1][0]
        sig_left = (
            f"(0,0|{x1_bot:.6f},0;{x1_bot:.6f},0|{x1_top:.6f},10;{x1_top:.6f},10|0,10;0,10|0,0)"
        )
        cut_op = {
            "op": "extrude",
            "label": "cut_r0",
            "sketch": "arm7_s7",
            "region": {"signature_yz_mm": sig_left, "tolerance_mm": 0.01},
            "mode": "cut",
            "depth": 3.0,
        }
        adapted, records = adapt_region_extrudes([sketch, cut_op])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["segment_count"], 4)
        # Derived sketch must pass full schema validation!
        validated = validate_operations(adapted)
        self.assertEqual(validated[1]["op"], "sketch")
        self.assertEqual(validated[2]["sketch"], validated[1]["label"])

    def test_mismatch_error_reports_closest_loop_diagnostic(self):
        sketch = {
            "op": "sketch",
            "label": "sk_diag",
            "plane": "YZ",
            "entities": [
                {"type": "line", "name": "l1", "start": [0, 0], "end": [10, 0]},
                {"type": "line", "name": "l2", "start": [10, 0], "end": [10, 10]},
                {"type": "line", "name": "l3", "start": [10, 10], "end": [0, 10]},
                {"type": "line", "name": "l4", "start": [0, 10], "end": [0, 0]},
            ],
        }
        bad_cut = {
            "op": "extrude",
            "label": "cut_bad",
            "sketch": "sk_diag",
            "region": {
                "signature_yz_mm": "(0,0|10,0;10,0|10,12;10,12|0,12;0,12|0,0)",
                "tolerance_mm": 0.001,
            },
            "mode": "cut",
            "depth": 2.0,
        }
        with self.assertRaises(ValueError) as ctx:
            adapt_region_extrudes([sketch, bad_cut])
        msg = str(ctx.exception)
        self.assertIn("closest_loop=", msg)
        self.assertIn("max_endpoint_diff_mm=", msg)
        self.assertIn("detected_loops=", msg)


class Bug182SelectorDiagnosticsSourceTests(unittest.TestCase):
    def test_native_selector_emits_suggested_reference_and_assembly_frame(self):
        sel_src = (ROOT / "native/geometry_selectors.cpp").read_text(encoding="utf-8")
        gen_src = (ROOT / "native/generic.cpp").read_text(encoding="utf-8")
        self.assertIn('"suggested_reference"', sel_src)
        self.assertIn("Closest candidate: {kind:'surface',id:", sel_src)
        self.assertIn('"nearest_coordinate_space"', gen_src)
        self.assertIn('"assembly_origin_mm"', gen_src)
        self.assertIn('"assembly_normal"', gen_src)


if __name__ == "__main__":
    unittest.main()
