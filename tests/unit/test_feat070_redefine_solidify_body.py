"""Offline tests for FEAT-070: creo_redefine_solidify_body.

These tests never start or connect Creo. They cover:
  * schema validation of the new ``redefine_solidify_body`` operation,
  * native/MCP wiring (source sentinels, same technique as test_f08_contract),
  * admission through ``generic_bridge.submit`` (revision protection, the
    single Toolkit channel, and busy-immediate-reject) with the worker and the
    file system mocked away,
  * projection of the native repair receipt through the shared
    ``operation_results.annotate_native_result`` path.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import bridge
from creo_mechdog import generic_bridge
from creo_mechdog.capabilities import REGISTERED_OPERATIONS, require_available
from creo_mechdog.operation_results import annotate_native_result
from creo_mechdog.schema import validate_operations

REPO = Path(__file__).resolve().parents[2]
GENERIC_CPP = REPO / "native" / "generic.cpp"
SERVER_PY = REPO / "src/creo_mechdog/server.py"
SCHEMA_PY = REPO / "src" / "creo_mechdog" / "schema.py"
CAPABILITIES_PY = REPO / "src" / "creo_mechdog" / "capabilities.py"

OP = "redefine_solidify_body"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SchemaValidationTests(unittest.TestCase):
    def test_minimal_existing_strategy_defaults(self):
        ops = validate_operations([{"op": OP, "feature": 250}])
        self.assertEqual(ops, [{"op": OP, "feature": 250, "body_strategy": "existing"}])

    def test_feature_by_name_accepted(self):
        ops = validate_operations([{"op": OP, "feature": "BOW_BULB_SOLID"}])
        self.assertEqual(ops[0]["feature"], "BOW_BULB_SOLID")
        self.assertEqual(ops[0]["body_strategy"], "existing")

    def test_body_id_strategy_requires_body_id(self):
        with self.assertRaises(Exception):
            validate_operations([{"op": OP, "feature": 250, "body_strategy": "body_id"}])

    def test_body_id_strategy_accepts_positive_id(self):
        ops = validate_operations(
            [{"op": OP, "feature": 250, "body_strategy": "body_id", "body_id": 1}]
        )
        self.assertEqual(ops[0]["body_id"], 1)

    def test_body_id_rejects_negative(self):
        with self.assertRaises(Exception):
            validate_operations(
                [{"op": OP, "feature": 250, "body_strategy": "body_id", "body_id": -3}]
            )

    def test_body_id_only_allowed_with_body_id_strategy(self):
        with self.assertRaises(Exception):
            validate_operations(
                [{"op": OP, "feature": 250, "body_strategy": "existing", "body_id": 1}]
            )
        with self.assertRaises(Exception):
            validate_operations([{"op": OP, "feature": 250, "body_strategy": "new", "body_id": 1}])

    def test_new_strategy_accepted(self):
        ops = validate_operations([{"op": OP, "feature": 250, "body_strategy": "new"}])
        self.assertEqual(ops[0]["body_strategy"], "new")

    def test_unknown_strategy_rejected(self):
        with self.assertRaises(Exception):
            validate_operations([{"op": OP, "feature": 250, "body_strategy": "all"}])

    def test_missing_feature_rejected(self):
        with self.assertRaises(Exception):
            validate_operations([{"op": OP}])

    def test_extra_fields_forbidden(self):
        with self.assertRaises(Exception):
            validate_operations([{"op": OP, "feature": 250, "bogus": True}])

    def test_feature_as_digit_string_accepted(self):
        # BUG-073 convention: a digit-only string is treated as a feature id.
        ops = validate_operations([{"op": OP, "feature": "250"}])
        self.assertEqual(ops[0]["feature"], "250")


class WiringTests(unittest.TestCase):
    def setUp(self):
        self.cpp = _read(GENERIC_CPP)
        self.server = _read(SERVER_PY)
        self.schema = _read(SCHEMA_PY)
        self.cap = _read(CAPABILITIES_PY)

    def test_registered_operation(self):
        self.assertIn(OP, REGISTERED_OPERATIONS)
        self.assertIn(f'"{OP}"', self.cap)

    def test_schema_model_declared_and_unioned(self):
        self.assertIn("class RedefineSolidifyBodyOp", self.schema)
        self.assertIn("RedefineSolidifyBodyOp,", self.schema)

    def test_native_dispatch_present(self):
        self.assertIn(f'kind == "{OP}"', self.cpp)
        self.assertIn("details = generic_redefine_solidify_body(op)", self.cpp)
        self.assertIn("static J generic_redefine_solidify_body(const J &op)", self.cpp)

    def test_native_uses_body_option_apis(self):
        # FEAT-070 must reuse the existing element-tree + body-reference APIs
        # rather than reinventing them.
        for token in (
            "ProFeatureElemtreeExtract",
            "ProFeatureWithoptionsRedefine",
            "ProElementIntegerGet",
            "ProElementIntegerSet",
            "ProElementReferenceGet",
            "ProElementReferenceSet",
            "ProReferenceStatusGet",
            "PRO_REF_INVALID",
            "PRO_E_BODY_USE",
            "PRO_E_BODY_SELECT",
            "PRO_BODY_USE_SELECTED",
            "PRO_BODY_USE_NEW",
            "ProSolidRegenerate",
            "ProFeatureIsIncomplete",
            "require_scopable_body",
        ):
            self.assertIn(token, self.cpp, f"missing native token: {token}")

    def test_native_stages_partial_receipt_on_failure(self):
        # Every failure path must stage a receipt so the failed operation record
        # carries phase / old_body / feature_incomplete before the job rolls back.
        self.assertIn("stage_operation_result", self.cpp)

    def test_server_tool_admitted(self):
        self.assertIn("async def creo_redefine_solidify_body", self.server)
        self.assertIn('op="redefine_solidify_body"', self.server)
        self.assertIn("general.submit", self.server)
        self.assertIn("body_strategy", self.server)


class AdmissionTests(unittest.TestCase):
    """Submit-level admission without Creo: shared revision/busy/channel guards."""

    MODEL_ID = "feat070-model"

    def _noop_lock(self):
        return MagicMock()

    def test_require_available_does_not_reject(self):
        require_available([{"op": OP, "feature": 250, "body_strategy": "new"}])

    @patch("creo_mechdog.generic_bridge.subprocess.Popen")
    @patch("creo_mechdog.generic_bridge.model_path")
    @patch("creo_mechdog.generic_bridge.model_info")
    @patch("creo_mechdog.generic_bridge.bridge.toolkit_lock")
    def test_stale_revision_refused_before_worker(self, lock, model_info, model_path, popen):
        lock.return_value = self._noop_lock()
        model_path.return_value = Path("unused")
        model_info.return_value = {
            "model_id": self.MODEL_ID,
            "revision": 3,
            "status": "ready",
        }
        with self.assertRaises(ValueError) as cm:
            generic_bridge.submit(
                [{"op": OP, "feature": 250}],
                model_id=self.MODEL_ID,
                expected_revision=2,
            )
        self.assertIn("Stale revision", str(cm.exception))
        popen.assert_not_called()
        lock.assert_called_once()

    @patch("creo_mechdog.generic_bridge.subprocess.Popen")
    @patch("creo_mechdog.generic_bridge.model_path")
    @patch("creo_mechdog.generic_bridge.model_info")
    @patch("creo_mechdog.generic_bridge.bridge.toolkit_lock")
    def test_pending_job_rejected_as_busy(self, lock, model_info, model_path, popen):
        lock.return_value = self._noop_lock()
        model_path.return_value = Path("unused")
        model_info.return_value = {
            "model_id": self.MODEL_ID,
            "revision": 1,
            "status": "ready",
            "pending_job": "other-job",
        }
        with self.assertRaises(bridge.ToolkitBusy):
            generic_bridge.submit(
                [{"op": OP, "feature": 250}],
                model_id=self.MODEL_ID,
                expected_revision=1,
            )
        popen.assert_not_called()

    @patch("creo_mechdog.generic_bridge.subprocess.Popen")
    @patch("creo_mechdog.generic_bridge.model_path")
    @patch("creo_mechdog.generic_bridge.model_info")
    @patch("creo_mechdog.generic_bridge.bridge.toolkit_lock")
    def test_busy_channel_rejected_immediately(self, lock, model_info, model_path, popen):
        busy = MagicMock()
        busy.__enter__.side_effect = bridge.ToolkitBusy("channel busy")
        lock.return_value = busy
        model_path.return_value = Path("unused")
        model_info.return_value = {
            "model_id": self.MODEL_ID,
            "revision": 1,
            "status": "ready",
        }
        with self.assertRaises(bridge.ToolkitBusy):
            generic_bridge.submit(
                [{"op": OP, "feature": 250}],
                model_id=self.MODEL_ID,
                expected_revision=1,
            )
        popen.assert_not_called()


class ProjectionTests(unittest.TestCase):
    SUCCESS_RECEIPT = {
        "op": OP,
        "feature_id": 250,
        "feature_name": "BOW_BULB_SOLID",
        "old_body": {
            "use": 2,
            "use_name": "selected",
            "ref_type_int": 28,
            "ref_id": 251,
            "ref_status": "invalid",
            "valid": False,
            "query_code": 0,
        },
        "new_body": {
            "strategy": "existing",
            "use": 2,
            "use_name": "selected",
            "ref_type_int": 28,
            "ref_id": 1,
            "ref_resolved": True,
        },
        "redefine_code": 0,
        "regenerate_code": 0,
        "feature_incomplete": False,
        "body_counts_before": {"objects": 2, "active": 1, "with_material": 1},
        "body_counts_after": {"objects": 2, "active": 1, "with_material": 1},
        "volume_before_mm3": 55087038135.823,
        "volume_after_mm3": 55087038135.823,
    }

    def test_success_receipt_preserved_by_projection(self):
        native = {
            "success": True,
            "saved_file_reloaded_and_verified": True,
            "operations": [dict(self.SUCCESS_RECEIPT)],
        }
        result = annotate_native_result(
            native,
            readonly=False,
            inputs=[{"op": OP, "feature": 250}],
            is_new_model=False,
        )
        self.assertEqual(len(result["operations"]), 1)
        op = result["operations"][0]
        # The repair receipt is the native evidence and must survive projection.
        self.assertEqual(op["old_body"]["ref_status"], "invalid")
        self.assertFalse(op["old_body"]["valid"])
        self.assertEqual(op["new_body"]["strategy"], "existing")
        self.assertTrue(op["new_body"]["ref_resolved"])
        self.assertEqual(op["new_body"]["ref_id"], 1)
        self.assertEqual(op["redefine_code"], 0)
        self.assertEqual(op["regenerate_code"], 0)
        self.assertIs(op["feature_incomplete"], False)
        self.assertEqual(op["body_counts_before"]["with_material"], 1)
        self.assertEqual(op["body_counts_after"]["with_material"], 1)
        # Shared projection fills status fields without dropping the receipt.
        self.assertEqual(op["execution_status"], "succeeded")

    def test_failure_partial_receipt_preserved(self):
        # On failure the native side stages a partial receipt (phase, old_body,
        # feature_incomplete) before throwing; the projection keeps it.
        partial = {
            "op": OP,
            "phase": "regenerate",
            "feature_incomplete": True,
            "old_body": {"ref_status": "invalid", "valid": False},
            "redefine_code": 0,
            "regenerate_code": -1,
        }
        native = {
            "success": False,
            "failed_operation_index": 0,
            "operations": [partial],
        }
        result = annotate_native_result(
            native,
            readonly=False,
            inputs=[{"op": OP, "feature": 250}],
            is_new_model=False,
        )
        op = result["operations"][0]
        self.assertEqual(op["phase"], "regenerate")
        self.assertIs(op["feature_incomplete"], True)
        self.assertEqual(op["regenerate_code"], -1)
        self.assertEqual(op["old_body"]["ref_status"], "invalid")
        self.assertEqual(op["execution_status"], "failed")


if __name__ == "__main__":
    unittest.main()
