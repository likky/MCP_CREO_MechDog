"""FEAT-023: execute_plan receipts stay bounded without hiding the identity."""

import asyncio
import inspect
import json
import unittest

import server
from creo_mechdog import generic_bridge
from creo_mechdog.submission_receipts import (
    COMPACT_MESSAGE,
    normalize_detail,
    project_receipt,
)

DIGEST = "a" * 64


def manifest(operations=None, **overrides):
    receipt = {
        "job_id": "0123456789abcdef0123456789abcdef",
        "kind": "generic",
        "model_id": "fedcba9876543210fedcba9876543210",
        "model_name": "bracket",
        "status": "queued",
        "revision": 0,
        "readonly": False,
        "readonly_source": "write_plan",
        "operations": operations if operations is not None else [{"op": "sketch", "label": "s1"}],
        "operations_view": "normalized",
        "timeout_seconds": 600,
        "timeout_source": "server",
        "job_directory": "/jobs/0123",
        "output_directory": "/jobs/0123/output",
        "message": "Poll creo_get_job with this job_id; do not resubmit the operation",
    }
    receipt.update(overrides)
    return receipt


class DetailContractTests(unittest.TestCase):
    def test_unknown_detail_is_refused_and_none_means_full(self):
        self.assertEqual(normalize_detail(None), "full")
        self.assertEqual(normalize_detail("full"), "full")
        self.assertEqual(normalize_detail("compact"), "compact")
        for bad in ("", "COMPACT", "brief", 1, True):
            with self.subTest(bad=bad), self.assertRaises(ValueError) as caught:
                normalize_detail(bad)
            self.assertIn("response_detail", str(caught.exception))

    def test_the_submit_entry_point_accepts_the_detail_and_defaults_to_full(self):
        parameter = inspect.signature(generic_bridge.submit).parameters["response_detail"]
        self.assertEqual(parameter.default, "full")

    def test_the_public_tool_exposes_the_detail_with_the_full_default(self):
        tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
        schema = tools["creo_execute_plan"].input_schema["properties"]["response_detail"]
        self.assertEqual(schema["default"], "full")
        self.assertEqual(schema["enum"], ["full", "compact"])


class CompactReceiptTests(unittest.TestCase):
    def test_full_is_the_unchanged_manifest(self):
        receipt = manifest()
        self.assertEqual(project_receipt(receipt), receipt)
        self.assertIn("operations", project_receipt(receipt, "full"))

    def test_compact_keeps_identity_revision_and_status_without_the_operations(self):
        compact = project_receipt(manifest(), "compact")
        self.assertNotIn("operations", compact)
        self.assertNotIn("operations_view", compact)
        for key in ("job_id", "kind", "model_id", "model_name", "status", "revision"):
            with self.subTest(key=key):
                self.assertEqual(compact[key], manifest()[key])
        self.assertEqual(compact["operation_count"], 1)
        self.assertEqual(compact["response_detail"], "compact")
        self.assertEqual(compact["full_operations"], "creo_get_job")
        self.assertEqual(compact["operations_hint"], COMPACT_MESSAGE)
        self.assertEqual(compact["message"], manifest()["message"])

    def test_a_failed_receipt_keeps_its_identity_and_operation_count(self):
        receipt = manifest(status="failed", revision=7, message="native create failed")
        compact = project_receipt(receipt, "compact")
        self.assertEqual(compact["status"], "failed")
        self.assertEqual(compact["revision"], 7)
        self.assertEqual(compact["operation_count"], 1)
        # The failure message is not replaced by the compact pointer.
        self.assertEqual(compact["message"], "native create failed")

    def test_file_inputs_keep_the_path_and_the_digest_that_was_computed(self):
        operations = [
            {
                "op": "import_geometry",
                "label": "imp",
                "file": "C:/in/bracket.stp",
                "file_sha256": DIGEST,
            },
            {"op": "udf", "label": "rib", "file_path": "C:/in/library.gph"},
            {"op": "extrude", "label": "e1"},
        ]
        compact = project_receipt(manifest(operations), "compact")
        self.assertEqual(compact["operation_count"], 3)
        self.assertEqual(len(compact["file_inputs"]), 2)
        imported, udf = compact["file_inputs"]
        self.assertEqual(imported["path"], "C:/in/bracket.stp")
        self.assertEqual(imported["sha256"], DIGEST)
        self.assertEqual(imported["path_field"], "file")
        # A digest the plan never carried is reported absent, not recomputed.
        self.assertEqual(udf["path"], "C:/in/library.gph")
        self.assertIsNone(udf["sha256"])
        self.assertIsNone(udf["sha256_field"])

    def test_region_adaptation_survives_compaction(self):
        receipt = manifest(region_adaptation={"source_label": "deck", "derived_label": "deck_r1"})
        compact = project_receipt(receipt, "compact")
        self.assertEqual(compact["region_adaptation"]["derived_label"], "deck_r1")

    def test_a_large_plan_stays_inside_the_documented_budget(self):
        operations = [
            {
                "op": "round",
                "label": f"r{index}",
                "size": 1.5,
                "references": [{"edge": {"kind": "edge", "id": index + 1}}],
            }
            for index in range(200)
        ]
        receipt = manifest(operations)
        compact = project_receipt(receipt, "compact")
        full_bytes = len(
            json.dumps(receipt, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )
        compact_bytes = len(
            json.dumps(compact, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )
        self.assertEqual(compact["operation_count"], 200)
        self.assertLess(compact_bytes, 32 * 1024)
        self.assertLess(compact_bytes * 10, full_bytes)

    def test_a_receipt_without_an_operation_list_does_not_invent_one(self):
        for operations in (None, "sketch", 17):
            with self.subTest(operations=operations):
                receipt = manifest()
                receipt["operations"] = operations
                compact = project_receipt(receipt, "compact")
                self.assertIsNone(compact["operation_count"])
                self.assertEqual(compact["file_inputs"], [])

    def test_non_dict_input_is_returned_untouched(self):
        self.assertIsNone(project_receipt(None, "compact"))
        self.assertEqual(project_receipt({"operations": []}, "compact")["operation_count"], 0)


if __name__ == "__main__":
    unittest.main()
