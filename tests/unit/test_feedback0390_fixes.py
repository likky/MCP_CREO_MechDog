"""Unit tests for 0.39.0 feedback fixes (BUG-175/176/177/178, FEAT-078/079)."""

from __future__ import annotations

import asyncio
import math
import unittest
from pathlib import Path

import server
from creo_mechdog import (
    compact_sections,
    component_changes,
    geometry_selectors,
    model_queries,
    operation_results,
    profile_diagnostics,
    schema,
)

ROOT = Path(__file__).resolve().parents[2]


class Bug176FullCircleAndArcSelectorTests(unittest.TestCase):
    def test_full_circle_validated_only_on_circular_edge_selector(self):
        sel = geometry_selectors.validate_geometry_selector(
            {
                "kind": "geometry_selector",
                "target": "edge",
                "center_mm": [118, 0, 0],
                "radius_mm": 36,
                "axis": [1, 0, 0],
                "full_circle": True,
                "tolerance_mm": 0.1,
            }
        )
        self.assertTrue(sel["full_circle"])

        with self.assertRaisesRegex(ValueError, "boolean"):
            geometry_selectors.validate_geometry_selector(
                {
                    "kind": "geometry_selector",
                    "target": "edge",
                    "center_mm": [0, 0, 0],
                    "radius_mm": 10,
                    "full_circle": "yes",
                    "tolerance_mm": 0.1,
                }
            )

        with self.assertRaisesRegex(ValueError, "center_mm and radius_mm"):
            geometry_selectors.validate_geometry_selector(
                {
                    "kind": "geometry_selector",
                    "target": "edge",
                    "point_mm": [10, 0, 0],
                    "full_circle": True,
                    "tolerance_mm": 0.1,
                }
            )

        with self.assertRaisesRegex(ValueError, "circular edge selector"):
            geometry_selectors.validate_geometry_selector(
                {
                    "kind": "geometry_selector",
                    "target": "surface",
                    "axis": [0, 0, 1],
                    "radius_mm": 10,
                    "full_circle": True,
                    "tolerance_mm": 0.1,
                }
            )

    def test_native_geometry_selector_supports_full_circle_seam_and_point_arc(self):
        src = (ROOT / "native" / "geometry_selectors.cpp").read_text(encoding="utf-8")
        self.assertIn("selector_point_on_arc", src)
        self.assertIn("full_circle_opt_in", src)
        self.assertIn("seam_point_resolved", src)
        self.assertIn("set full_circle:true", src)


class Feat078InspectAreaBboxAndMergedCountsTests(unittest.TestCase):
    def test_inspection_summary_exposes_area_bbox_and_merged_counts(self):
        # Two half-cylinders of one cylinder (z in [0, 50]) + another separate coaxial
        # cylinder (z in [100, 150]) + 2 planes = 6 raw faces -> 4 merged faces (2 cyl groups + 2 planes).
        # Two semicircular arcs of one circle + 1 straight edge = 3 raw edges -> 2 merged edges.
        raw_inspection = {
            "healthy": True,
            "has_solid": True,
            "model_type": "part",
            "volume_mm3": 12345.6,
            "total_surface_area_mm2": 4567.8,
            "bounding_box_mm": {
                "min": [-10.0, -10.0, 0.0],
                "max": [10.0, 10.0, 150.0],
                "size": [20.0, 20.0, 150.0],
            },
            "surfaces": [
                {"id": 1, "type": 34, "normal": [0, 0, 1], "origin": [0, 0, 0]},
                {"id": 2, "type": 34, "normal": [0, 0, 1], "origin": [0, 0, 150]},
                {
                    "id": 3,
                    "type": 36,
                    "axis": [0, 0, 1],
                    "origin": [0, 0, 0],
                    "radius": 10.0,
                    "bbox": [[-10, -10, 0], [10, 0, 50]],
                },
                {
                    "id": 4,
                    "type": 36,
                    "axis": [0, 0, 1],
                    "origin": [0, 0, 0],
                    "radius": 10.0,
                    "bbox": [[-10, 0, 0], [10, 10, 50]],
                },
                {
                    "id": 5,
                    "type": 36,
                    "axis": [0, 0, 1],
                    "origin": [0, 0, 100],
                    "radius": 10.0,
                    "bbox": [[-10, -10, 100], [10, 10, 150]],
                },
            ],
            "edges": [
                {
                    "id": 52,
                    "arc": {
                        "origin": [0, 0, 0],
                        "radius": 10.0,
                        "v1": [1, 0, 0],
                        "v2": [0, 1, 0],
                        "start_angle": 0.0,
                        "end_angle": math.pi,
                    },
                },
                {
                    "id": 53,
                    "arc": {
                        "origin": [0, 0, 0],
                        "radius": 10.0,
                        "v1": [1, 0, 0],
                        "v2": [0, 1, 0],
                        "start_angle": math.pi,
                        "end_angle": 2 * math.pi,
                    },
                },
                {"id": 60, "start": [10, 0, 0], "end": [10, 0, 50]},
            ],
        }
        summary = model_queries.inspection_summary(raw_inspection)
        self.assertEqual(summary["total_surface_area_mm2"], 4567.8)
        self.assertEqual(summary["bounding_box_mm"]["size"], [20.0, 20.0, 150.0])
        self.assertEqual(summary["counts"]["surfaces"], 5)
        self.assertEqual(summary["counts"]["edges"], 3)
        self.assertEqual(summary["merged_counts"]["surfaces"], 4)
        self.assertEqual(summary["merged_counts"]["cylindrical_face_groups"], 2)
        self.assertEqual(summary["merged_counts"]["edges"], 2)
        self.assertEqual(summary["merged_counts"]["circular_edge_groups"], 1)
        self.assertIn("2 half-cylinders", summary["counts_convention"])

    def test_native_inspection_exposes_surface_area_and_outline(self):
        src = (ROOT / "native" / "generic.cpp").read_text(encoding="utf-8")
        self.assertIn("ProSurfaceAreaEval(surface", src)
        self.assertIn("ProSolidOutlineGet((ProSolid)board, outline)", src)
        self.assertIn('"total_surface_area_mm2"', src)
        self.assertIn('"bounding_box_mm"', src)
        self.assertIn('"area_mm2"', src)


class Feat079RoundMultiSetLocalizationTests(unittest.TestCase):
    def test_compact_and_failure_evidence_preserve_round_failure_keys(self):
        for key in ("failed_reference_index", "failed_reference", "round_failure"):
            self.assertIn(key, compact_sections.OPERATION_KEYS)
            self.assertIn(key, operation_results.FAILED_EVIDENCE_KEYS)

    def test_native_round_failure_probe_contract(self):
        src = (ROOT / "native" / "generic.cpp").read_text(encoding="utf-8")
        self.assertIn("probe_round_references", src)
        self.assertIn('"failed_reference_index"', src)
        self.assertIn('"round_failure"', src)


class Bug177SketchUsabilityAndPlaneDocTests(unittest.TestCase):
    def test_arc_sweep_deg_major_arc_positive_and_negative(self):
        arc_ccw = schema.Arc(
            type="arc", name="a13", center=[0, 0], radius=22.5, start_angle=10.0, sweep_deg=269.8
        )
        self.assertEqual(arc_ccw.dir, 1)
        self.assertAlmostEqual(arc_ccw.end_angle, 279.8)
        dumped = arc_ccw.model_dump()
        self.assertNotIn("sweep_deg", dumped)
        self.assertAlmostEqual(dumped["end_angle"], 279.8)
        self.assertEqual(dumped["dir"], 1)

        arc_cw = schema.Arc(
            type="arc", name="a14", center=[0, 0], radius=22.5, start_angle=10.0, sweep_deg=-269.8
        )
        self.assertEqual(arc_cw.dir, -1)
        self.assertAlmostEqual(arc_cw.end_angle, -259.8)

        with self.assertRaisesRegex(ValueError, "either end_angle or sweep_deg"):
            schema.Arc(
                type="arc",
                name="a15",
                center=[0, 0],
                radius=10,
                start_angle=0,
                end_angle=90,
                sweep_deg=90,
            )

        with self.assertRaisesRegex(ValueError, "conflicts with the sign"):
            schema.Arc(
                type="arc",
                name="a16",
                center=[0, 0],
                radius=10,
                start_angle=0,
                sweep_deg=200,
                dir=-1,
            )

        with self.assertRaisesRegex(ValueError, "0 < \\|sweep_deg\\| < 360"):
            schema.Arc(
                type="arc", name="a17", center=[0, 0], radius=10, start_angle=0, sweep_deg=360
            )

    def test_spline_profile_computes_numerical_area_while_bspline_stays_unsupported(self):
        # 10x5 rectangle whose top edge is an interpolating spline through collinear points.
        entities = [
            {"type": "line", "name": "b", "start": [0, 0], "end": [10, 0]},
            {"type": "line", "name": "r", "start": [10, 0], "end": [10, 5]},
            {"type": "spline", "name": "t", "points": [[10, 5], [7, 5], [3, 5], [0, 5]]},
            {"type": "line", "name": "l", "start": [0, 5], "end": [0, 0]},
        ]
        report = profile_diagnostics.analyze_profile(entities)
        self.assertEqual(report["analysis"], "complete")
        self.assertEqual(report["unsupported_entities"], [])
        self.assertAlmostEqual(report["material_area_mm2"], 50.0, places=4)

        # b_spline remains unsupported per BUG-160.
        bs_report = profile_diagnostics.analyze_profile([{"type": "b_spline", "name": "bs1"}])
        self.assertIsNone(bs_report["material_area_mm2"])
        self.assertEqual(bs_report["unsupported_entities"], ["bs1"])

    def test_plane_frame_table_documented_on_sketch_and_extrude(self):
        sketch_doc = server.creo_create_sketch.__doc__ or ""
        extrude_doc = server.creo_extrude.__doc__ or ""
        self.assertIn("normal=[0, -1, 0]", sketch_doc)
        self.assertIn("u_axis=+X, v_axis=+Z", sketch_doc)
        self.assertIn("XZ: normal=-Y", extrude_doc)

    def test_native_coordinates_rejection_includes_shifted_sample(self):
        src = (ROOT / "native" / "sketch_coordinates.cpp").read_text(encoding="utf-8")
        self.assertIn("shifted_sample=", src)


class Bug178FeatureStateComponentNoiseAndEmptyPlanTests(unittest.TestCase):
    def test_feature_state_op_include_dependencies_validation(self):
        default_op = schema.FeatureStateOp(op="feature_state", action="delete", targets=["cut1"])
        self.assertFalse(default_op.include_dependencies)

        opt_in = schema.FeatureStateOp(
            op="feature_state", action="delete", targets=["cut1"], include_dependencies=True
        )
        self.assertTrue(opt_in.include_dependencies)

        with self.assertRaisesRegex(ValueError, "true or false"):
            schema.FeatureStateOp(
                op="feature_state",
                action="delete",
                targets=["cut1"],
                include_dependencies="yes",  # type: ignore[arg-type]
            )

    def test_component_changes_ignores_floating_point_roundtrip_noise(self):
        tf_before = [
            [0.7617252266526591, 0.0, 0.0, 10.0],
            [0.0, 1.0, 0.0, 20.0],
            [0.0, 0.0, 1.0, 30.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        tf_noise = [
            [0.7617252266526593, 0.0, 0.0, 10.0 + 1e-16],
            [0.0, 1.0, 0.0, 20.0],
            [0.0, 0.0, 1.0, 30.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        tf_real_move = [
            [0.7617252266526591, 0.0, 0.0, 10.001],
            [0.0, 1.0, 0.0, 20.0],
            [0.0, 0.0, 1.0, 30.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        prior_aliases = {"c13": {"op": "assemble_component", "feature_id": 100}}
        result_aliases = {
            "c13": {"op": "assemble_component", "feature_id": 100},
            "c14": {"op": "assemble_component", "feature_id": 101},
        }
        prior_insp = {"components": [{"feature_id": 100, "transform": tf_before}]}
        result_insp_noise = {
            "components": [
                {"feature_id": 100, "transform": tf_noise},
                {"feature_id": 101, "transform": tf_before},
            ]
        }
        summary = component_changes.summarize(
            [{"op": "assemble_component", "label": "c14", "source_model_id": "m1"}],
            job_status="succeeded",
            prior_aliases=prior_aliases,
            prior_inspection=prior_insp,
            result_aliases=result_aliases,
            result_inspection=result_insp_noise,
        )
        assert summary is not None
        self.assertEqual([c["op"] for c in summary["changes"]], ["added"])
        self.assertEqual(summary["changes"][0]["label"], "c14")

        result_insp_moved = {
            "components": [
                {"feature_id": 100, "transform": tf_real_move},
                {"feature_id": 101, "transform": tf_before},
            ]
        }
        summary_moved = component_changes.summarize(
            [{"op": "assemble_component", "label": "c14", "source_model_id": "m1"}],
            job_status="succeeded",
            prior_aliases=prior_aliases,
            prior_inspection=prior_insp,
            result_aliases=result_aliases,
            result_inspection=result_insp_moved,
        )
        assert summary_moved is not None
        ops = {(c["label"], c["op"]) for c in summary_moved["changes"]}
        self.assertIn(("c13", "moved"), ops)
        self.assertIn(("c14", "added"), ops)

    def test_execute_plan_empty_assembly_returns_clear_tool_error(self):
        with self.assertRaisesRegex(ValueError, "creo_new_assembly"):
            asyncio.run(
                server.creo_execute_plan(operations=[], model_name="assem2", model_type="assembly")
            )

        with self.assertRaisesRegex(ValueError, "creo_new_part"):
            asyncio.run(
                server.creo_execute_plan(operations=[], model_name="part2", model_type="part")
            )

    def test_native_feature_state_supports_include_dependencies_and_suggested_targets(self):
        src = (ROOT / "native" / "feature_state.cpp").read_text(encoding="utf-8")
        self.assertIn("include_dependencies", src)
        self.assertIn("suggested_targets", src)
        self.assertIn("auto_included_dependencies", src)


if __name__ == "__main__":
    unittest.main()
