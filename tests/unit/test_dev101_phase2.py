"""DEV-101 Phase 2 offline tests: BUG-189 unknown args, BUG-190 failure diagnostics, FEAT-088 packaged."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp.server.mcpserver.exceptions import ToolError

import bridge
import server
from creo_mechdog.schema import validate_operations


class Bug189UnknownArgumentsTests(unittest.TestCase):
    def test_unknown_argument_with_typo_suggests_close_match(self):
        with self.assertRaises(ToolError) as caught:
            asyncio.run(
                server.mcp.call_tool(
                    "creo_inspect_model",
                    {"model_id": "a" * 32, "sections": "features"},
                )
            )
        msg = str(caught.exception)
        self.assertIn("unknown argument 'sections'", msg)
        self.assertIn("did you mean 'section'?", msg)

    def test_bogus_argument_rejected_on_read_and_modeling_tools(self):
        cases = [
            ("creo_capabilities", {"bogus_field": 1}),
            ("creo_get_job", {"job_id": "abc", "bogus_field": True}),
            (
                "creo_revolve",
                {
                    "model_id": "a" * 32,
                    "expected_revision": 1,
                    "label": "r",
                    "sketch": "s",
                    "bogus_x": 1,
                },
            ),
        ]
        for tool_name, args in cases:
            with self.subTest(tool=tool_name), self.assertRaises(ToolError) as caught:
                asyncio.run(server.mcp.call_tool(tool_name, args))
            self.assertIn("unknown argument", str(caught.exception))

    def test_valid_arguments_still_pass(self):
        res = asyncio.run(server.mcp.call_tool("creo_capabilities", {"detail": "compact"}))
        self.assertFalse(res.is_error)


class Bug190JobFailureDiagnosticsTests(unittest.TestCase):
    def test_failed_job_exposes_stage_path_and_round_summary_in_full_and_compact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job_id = "11112222333344445555666677778888"
            job_dir = root / "jobs" / job_id
            job_dir.mkdir(parents=True)
            native_res = job_dir / "native_result.json"
            native_res.write_text('{"success": false}', encoding="utf-8")
            manifest = {
                "job_id": job_id,
                "kind": "generic",
                "model_id": "a" * 32,
                "status": "failed",
                "stage": "execute_round",
                "created_at": "2026-11-24T12:00:00+00:00",
                "message": "round failed",
                "result": {
                    "success": False,
                    "failed_operation_index": 2,
                    "failed_stage": "execute_round",
                    "failed_operation": {"index": 2, "stage": "execute_round"},
                    "operations": [
                        {"index": 0, "op": "sketch", "succeeded": True},
                        {"index": 1, "op": "extrude", "succeeded": True},
                        {
                            "index": 2,
                            "op": "round",
                            "succeeded": False,
                            "round_failure": {
                                "failed_reference_index": 1,
                                "edge_diagnostics": [
                                    {
                                        "edge_id": 88,
                                        "start_vertex": {"min_adjacent_edge_mm": 1.25},
                                        "end_vertex": {"min_adjacent_edge_mm": 2.5},
                                    }
                                ],
                            },
                        },
                    ],
                },
            }
            (job_dir / "job.json").write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(bridge, "JOBS", root / "jobs"):
                for detail in ("full", "compact"):
                    view = bridge.get_job(job_id, detail=detail)
                    self.assertEqual(view["failed_operation_index"], 2)
                    self.assertEqual(view["failed_stage"], "execute_round")
                    self.assertEqual(view["failure_phase"], "execute_round")
                    self.assertEqual(view["native_result_path"], str(native_res))
                    self.assertEqual(view["round_failure_summary"]["failed_reference_index"], 1)
                    self.assertEqual(
                        view["round_failure_summary"]["edge_min_adjacent_mm"][0][
                            "min_adjacent_edge_mm"
                        ],
                        [1.25, 2.5],
                    )

    def test_succeeded_job_has_no_failure_noise_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job_id = "aaaabbbbccccddddeeeeffff00001111"
            job_dir = root / "jobs" / job_id
            job_dir.mkdir(parents=True)
            (job_dir / "native_result.json").write_text('{"success": true}', encoding="utf-8")
            manifest = {
                "job_id": job_id,
                "kind": "generic",
                "model_id": "a" * 32,
                "status": "succeeded",
                "stage": "verified",
                "created_at": "2026-11-24T12:00:00+00:00",
                "result": {"success": True, "operations": []},
            }
            (job_dir / "job.json").write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(bridge, "JOBS", root / "jobs"):
                for detail in ("full", "compact"):
                    view = bridge.get_job(job_id, detail=detail)
                    self.assertNotIn("failed_operation_index", view)
                    self.assertNotIn("failed_stage", view)
                    self.assertNotIn("native_result_path", view)
                    self.assertNotIn("round_failure_summary", view)


class Feat088PackagedPlacementTests(unittest.TestCase):
    def test_packaged_placement_validates_without_constraints(self):
        op = {
            "op": "assemble_component",
            "label": "inst1",
            "source_model_id": "a" * 32,
            "translation": [10.0, 20.0, 30.0],
            "placement": "packaged",
        }
        validated = validate_operations([op])[0]
        self.assertEqual(validated["placement"], "packaged")

    def test_packaged_placement_rejects_constraints(self):
        op = {
            "op": "assemble_component",
            "label": "inst1",
            "source_model_id": "a" * 32,
            "placement": "packaged",
            "constraints": [
                {
                    "type": "mate",
                    "component_ref": {"kind": "surface", "id": 1},
                    "assembly_ref": {"kind": "surface", "id": 2},
                }
            ],
        }
        with self.assertRaises(ValueError):
            validate_operations([op])


if __name__ == "__main__":
    unittest.main()
