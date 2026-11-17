"""BUG-120: a panel receipt cannot certify an unconfirmed operation."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import bridge
import generic_bridge as general
from tests.unit import test_toolkit_channel as channel_tests


class PanelExecutionUnknown(unittest.TestCase):
    setUp = channel_tests.ToolkitChannel.setUp
    submit = channel_tests.ToolkitChannel.submit
    worker = channel_tests.ToolkitChannel.worker
    run_job = channel_tests.ToolkitChannel.run_job

    def run_receipt(self, marker=..., *, success=True, rollback=False, operations=None):
        created = self.submit()
        self.run_job(created)
        before = general.model_info(created["model_id"])
        source = Path(before["part_file"])
        original = source.read_bytes()
        queued = self.submit(model_id=created["model_id"], expected_revision=before["revision"])

        def worker(*args, **kwargs):
            receipt = {
                "success": success,
                "rollback_succeeded": rollback,
                "delivery_complete": True,
                "disconnect_code": 0,
                "saved_file_reloaded_and_verified": True,
                "part_file": before["part_file"],
                "message": "native panel diagnostic",
                "operations": operations
                if operations is not None
                else [{"op": "surface_loft", "status": "succeeded", "label": "blend"}],
            }
            if marker is not ...:
                receipt["panel_execution_unconfirmed"] = marker
            bridge.write_json(bridge.job_path(queued["job_id"]) / "native_result.json", receipt)
            return subprocess.CompletedProcess(args[0], 0)

        with (
            patch.object(bridge, "build_native", return_value=self.root / "worker.exe"),
            patch.object(bridge, "native_environment", return_value={}),
            patch.object(bridge.subprocess, "run", side_effect=worker),
        ):
            bridge.run_job(queued["job_id"])
        after = general.model_info(created["model_id"])
        job = bridge.read_json(bridge.job_path(queued["job_id"]) / "job.json")
        self.assertEqual(source.read_bytes(), original)
        return before, after, queued, job

    def test_exact_true_retains_unknown_reservation_and_native_evidence(self):
        before, after, queued, job = self.run_receipt(True)
        self.assertEqual(job["status"], "unknown_outcome")
        self.assertEqual(after["status"], "unknown_outcome")
        self.assertEqual(after["pending_job"], queued["job_id"])
        self.assertEqual(after["revision"], before["revision"])
        self.assertEqual(after["part_file"], before["part_file"])
        self.assertIn("panel exit", job["message"])
        self.assertIn("operation", job["message"])
        self.assertEqual(job["result"]["message"], "native panel diagnostic")
        self.assertIs(job["result"]["panel_execution_unconfirmed"], True)
        operation = job["result"]["operations"][0]
        self.assertEqual(operation["label"], "blend")
        self.assertEqual(operation["execution_status"], "succeeded")
        self.assertEqual(operation["effect_status"], "unknown")
        self.assertEqual(job["result"]["terminal_effect"]["managed_model"]["effect"], "unknown")
        with self.assertRaises(bridge.ToolkitBusy):
            self.submit(model_id=queued["model_id"], expected_revision=before["revision"])

    def test_false_missing_and_truthy_text_do_not_claim_unknown(self):
        for marker in (False, ..., "true"):
            with self.subTest(marker=marker):
                before, after, _, job = self.run_receipt(marker)
                self.assertEqual(job["status"], "succeeded")
                self.assertEqual(after["status"], "ready")
                self.assertEqual(after["revision"], before["revision"] + 1)
                self.assertIsNone(after["pending_job"])

    def test_large_receipt_pages_preserve_unknown_effects(self):
        operations = [
            {
                "op": "surface_loft",
                "status": "succeeded",
                "label": f"blend_{index}",
                "effect_status": "committed" if index % 2 else "rolled_back",
            }
            for index in range(120)
        ]
        _, _, queued, job = self.run_receipt(True, operations=operations)
        self.assertEqual(len(job["result"]["operations"]), 120)
        self.assertTrue(
            all(
                operation["effect_status"] == "unknown" for operation in job["result"]["operations"]
            )
        )
        cursor = None
        observed = []
        while True:
            page = bridge.get_job(
                queued["job_id"], detail="full", section="operations_result", cursor=cursor
            )
            self.assertEqual(page["status"], "unknown_outcome")
            self.assertEqual(page["operation_result_count"], 120)
            observed.extend(page["data"]["operations_result"])
            cursor = page["next_cursor"]
            if cursor is None:
                break
        self.assertEqual(len(observed), 120)
        self.assertTrue(all(operation["effect_status"] == "unknown" for operation in observed))

    def test_false_success_and_rollback_claim_remain_unknown(self):
        operations = [
            {
                "op": "surface_loft",
                "status": "failed",
                "effect_status": "rolled_back",
                "message": "panel callback ended",
            }
        ]
        before, after, _, job = self.run_receipt(
            True, success=False, rollback=True, operations=operations
        )
        self.assertEqual(job["status"], "unknown_outcome")
        self.assertEqual(after["revision"], before["revision"])
        self.assertEqual(job["result"]["operations"][0]["effect_status"], "unknown")
        self.assertTrue(job["result"]["rollback_succeeded"])
