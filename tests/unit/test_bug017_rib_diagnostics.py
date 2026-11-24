"""BUG-017: per-stage native rib diagnostics, failure receipts, and compact projection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from creo_mechdog import compact_sections, operation_results
from tools.test_direct_loft import Probe

ROOT = Path(__file__).resolve().parents[2]


def _native_source(name: str) -> str:
    return (ROOT / "native" / name).read_text(encoding="utf-8")


def _sample_rib_diagnostics(*, failed_stage: str | None = "rib_regeneration") -> dict:
    return {
        "failed_stage": failed_stage,
        "sketch_id": 82,
        "target_body_id": 52,
        "thickness_mm": 3.0,
        "side": "symmetric",
        "side_opts_value": 1,
        "flip": False,
        "matrlside_value": 1,
        "create_code": 0,
        "create_element_errors": {"total": 0, "truncated": False, "sample": []},
        "feature_id": 84,
        "extract_code": 0,
        "matrlside_set_code": 0,
        "redefine_code": 0,
        "redefine_element_errors": {"total": 0, "truncated": False, "sample": []},
        "status_code": 0,
        "feature_status": 6 if failed_stage else 0,
        "geometry_visit_code": 0,
        "geometry_item_count": 0 if failed_stage else 5,
        "geometry_items_sample": [],
    }


def _sample_feature_errors() -> dict:
    return {
        "api": "ProFeatureStatusGet",
        "code": 6,
        "failed_stage": "rib_regeneration",
        "element_errors": {"total": 0, "truncated": False, "sample": []},
        "section_errors": {
            "available": False,
            "total": 0,
            "truncated": False,
            "sample": [],
            "unavailable_reason": "no section solve ran before this failure",
        },
    }


class Bug017NativeWiringTests(unittest.TestCase):
    def test_generic_rib_records_per_stage_codes_and_inactive_feature_receipt(self) -> None:
        source = _native_source("surfaces.cpp")
        start = source.index("static void generic_rib(const J &op)")
        body = source[start:]
        for marker in (
            '"create_code"',
            '"create_element_errors"',
            '"extract_code"',
            '"matrlside_set_code"',
            '"redefine_code"',
            '"redefine_element_errors"',
            '"status_code"',
            '"feature_status"',
            '"geometry_visit_code"',
            '"geometry_item_count"',
            '"rib_diagnostics"',
            "ProFeatureGeomitemVisit(&f, PRO_TYPE_UNUSED, collect_geom_ids",
            'feature_error_report("ProFeatureStatusGet", (ProError)status, "rib_regeneration")',
            "RIB_DIAG feature_id=",
        ):
            self.assertIn(marker, body)
        self.assertIn("Rib requires an open profile", body)
        self.assertIn("Rib regeneration failed on the requested material side", body)

    def test_std_exception_catch_publishes_top_level_feature_errors(self) -> None:
        generic = _native_source("generic.cpp")
        start = generic.index("} catch (const std::exception &error) {")
        end = generic.index("if (!verify_stages.empty())", start)
        body = generic[start:end]
        self.assertIn('report["feature_errors"] = last_feature_error_report;', body)


class Bug017ProjectionTests(unittest.TestCase):
    def test_failed_rib_preserves_rib_diagnostics_and_feature_errors(self) -> None:
        result = {
            "success": False,
            "toolkit_code": -1,
            "message": "Rib regeneration failed on the requested material side (feature_id=84, feature_status=6)",
            "feature_errors": _sample_feature_errors(),
            "operations": [
                {
                    "op": "rib",
                    "index": 0,
                    "label": "rib",
                    "succeeded": False,
                    "execution_status": "failed",
                    "effect_status": "rolled_back",
                    "feature_id": 84,
                    "rib_diagnostics": _sample_rib_diagnostics(),
                    "feature_errors": _sample_feature_errors(),
                }
            ],
        }
        annotated = operation_results.annotate_native_result(result, readonly=False)
        self.assertEqual(annotated["feature_errors"]["failed_stage"], "rib_regeneration")
        self.assertEqual(annotated["feature_errors"]["code"], 6)
        op = annotated["operations"][0]
        self.assertEqual(op["rib_diagnostics"]["feature_id"], 84)
        self.assertEqual(op["rib_diagnostics"]["feature_status"], 6)
        self.assertEqual(op["rib_diagnostics"]["create_code"], 0)
        self.assertEqual(op["rib_diagnostics"]["redefine_code"], 0)
        self.assertIn("rib_diagnostics", operation_results.FAILED_EVIDENCE_KEYS)
        self.assertIn("rib_diagnostics", compact_sections.OPERATION_KEYS)


class Bug017ProbeHydrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_probe_hydrates_new_full_job_shape_without_result_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = SimpleNamespace(call_tool=AsyncMock())
            report = {"calls": [], "jobs": []}
            probe = Probe(client, report, Path(tmp) / "out.json", 5)
            compact = {
                "job_id": "j1",
                "model_id": "m1",
                "revision": 2,
                "status": "succeeded",
                "result": {
                    "saved_file_reloaded_and_verified": True,
                    "part_file": "p.prt.2",
                },
            }
            full_job = {
                "job_id": "j1",
                "model_id": "m1",
                "revision": 2,
                "status": "succeeded",
                "detail": "full",
                "data": {"operations_result": []},
            }
            full_model = {
                "model_id": "m1",
                "inspection": {"volume_mm3": 55250.0, "features": []},
                "aliases": {"rib": {"feature_id": 139}},
            }
            client.call_tool.side_effect = [
                SimpleNamespace(is_error=False, structured_content={"job_id": "j1"}),
                SimpleNamespace(is_error=False, structured_content=compact),
                SimpleNamespace(is_error=False, structured_content=full_job),
                SimpleNamespace(is_error=False, structured_content=full_model),
            ]
            state = await probe.job("creo_rib", {"label": "rib"}, "rib_case")
            self.assertEqual(state["result"]["inspection"]["volume_mm3"], 55250.0)
            self.assertEqual(state["result"]["aliases"]["rib"]["feature_id"], 139)
            self.assertTrue(state["result"]["saved_file_reloaded_and_verified"])


if __name__ == "__main__":
    unittest.main()
