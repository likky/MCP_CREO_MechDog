"""BUG-130 Task 1: offline STL evidence and instrumentation regressions."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.diagnose_stl_export import summarize_stl_job  # noqa: E402

FAILED_LOG = """PHASE=connect
STAGE name=connect elapsed_ms=142 since_start_ms=142 ts=1794821538696
connect_creo(&process)=0
STAGE name=connected elapsed_ms=4723 since_start_ms=4866 ts=1794821543419
ProEngineerConnectIdGet(value)=0
FindOwnedModel=0
ProMdlOriginGet(board, origin)=0
ProMdlPrincipalunitsystemGet(board, &us)=0
ProUnitsystemUnitGet(&us, PRO_UNITTYPE_LENGTH, &unit)=0
PHASE=loaded_blend_validation
PHASE=execute_export
PROGRESS index=1 total=1 op=export label=- state=start elapsed_ms=4896 since_start_ms=4896 ts=1794821543449
OPERATION_INDEX=0 INPUT={"format":"stl","op":"export"}
PHASE=export
ProPartTessellate((ProPart)board, 0.05, 0.1, PRO_B_FALSE, &surfaces)=0
ProArraySizeGet((ProArray)surfaces, &n)=0
"""

INSTRUMENTED_LOG = """PHASE=export
STL_EXPORT_BEGIN file=bulb.stl
STL_TESS_BEGIN
STL_TESS_END code=0 ptr=0x1234
STL_OUTER_ARRAY_COUNT code=0 n=2
STL_OUTPUT_OPEN file=bulb.stl ok=1
STL_OUTPUT_HEADER
STL_SURFACE_BEGIN index=0 n_vertices=3 vertices_null=0 n_facets=1 facets_null=0
STL_SURFACE_ID index=0 surface_id=198 code=0
STL_BAD_INDEX index=0 surface_id=198 facet=0 indices=0,1,3 n_vertices=3
STL_TESS_FREE_BEGIN ptr=0x1234
STL_TESS_FREE_END code=0 ptr=0x0
"""


def write_job(
    root: Path,
    job_id: str,
    *,
    status: str,
    message: str,
    log_text: str,
    stl: bytes = b"",
    with_request: bool = True,
) -> Path:
    directory = root / job_id
    directory.mkdir()
    (directory / "job.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
                "kind": "generic",
                "model_id": "c" * 32,
                "status": status,
                "message": message,
                "stage": "executing_feature_plan",
                "readonly": True,
                "revision": 8,
            }
        ),
        encoding="utf-8",
    )
    (directory / "native.log").write_text(log_text, encoding="utf-8")
    if with_request:
        (directory / "request.json").write_text(
            json.dumps(
                {
                    "model": {
                        "part_file": str(root / "bulb.prt.9"),
                        "part_sha256": "f" * 64,
                    },
                    "operations": [{"op": "export", "format": "stl"}],
                }
            ),
            encoding="utf-8",
        )
    output = directory / "output"
    output.mkdir()
    (output / "bulb.stl").write_bytes(stl)
    return directory


class FailureEvidenceTests(unittest.TestCase):
    def test_failure_summary_reports_zero_bytes_exit_code_and_last_phase(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = write_job(
                Path(raw),
                "a" * 32,
                status="unknown_outcome",
                message=(
                    "Native worker exited 3221225477 without a result; inspect Creo before retrying"
                ),
                log_text=FAILED_LOG,
            )
            summary = summarize_stl_job(directory)
        self.assertEqual(summary["status"], "unknown_outcome")
        self.assertEqual(summary["exit_code"], 3221225477)
        self.assertEqual(summary["exit_code_hex"], "0xC0000005")
        self.assertEqual(summary["native_log"]["last_phase"], "export")
        self.assertEqual(summary["native_log"]["tessellate_code"], 0)
        self.assertEqual(summary["native_log"]["array_size_code"], 0)
        self.assertIsNone(summary["native_log"]["outer_count"])
        self.assertTrue(summary["stl_zero_bytes"])
        self.assertEqual(summary["stl_total_bytes"], 0)

    def test_two_failed_logs_share_the_export_tail_but_not_the_full_hash(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            first = write_job(
                root,
                "a" * 32,
                status="unknown_outcome",
                message="Native worker exited 3221225477 without a result",
                log_text=FAILED_LOG,
            )
            second = write_job(
                root,
                "b" * 32,
                status="unknown_outcome",
                message="Native worker exited 3221225477 without a result",
                log_text=FAILED_LOG.replace("1794821538696", "1794824376693"),
            )
            one = summarize_stl_job(first)
            two = summarize_stl_job(second)
        self.assertEqual(
            one["native_log"]["tail_after_export"], two["native_log"]["tail_after_export"]
        )
        self.assertNotEqual(one["native_log"]["sha256"], two["native_log"]["sha256"])

    def test_missing_directory_is_safe(self):
        with tempfile.TemporaryDirectory() as raw:
            summary = summarize_stl_job(Path(raw) / "missing")
        self.assertIsNone(summary["status"])
        self.assertEqual(summary["output_files"], [])
        self.assertFalse(summary["stl_zero_bytes"])


class InstrumentationEvidenceTests(unittest.TestCase):
    def test_instrumented_log_exposes_outer_count_stage_and_bad_index(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = write_job(
                Path(raw),
                "c" * 32,
                status="failed",
                message="Tessellation facet index out of range",
                log_text=INSTRUMENTED_LOG,
            )
            summary = summarize_stl_job(directory)
        native = summary["native_log"]
        self.assertEqual(native["outer_count"], 2)
        self.assertEqual(native["outer_array_code"], 0)
        self.assertIn("STL_BAD_INDEX", native["stages"])
        self.assertEqual(native["last_stage"], "STL_TESS_FREE_END")
        self.assertEqual(native["surface_begin_count"], 1)
        self.assertEqual(
            native["bad_index"],
            {
                "index": 0,
                "surface_id": 198,
                "facet": 0,
                "indices": "0,1,3",
                "n_vertices": 3,
            },
        )
        self.assertTrue(native["free_begin"])
        self.assertTrue(native["free_end"])

    def test_success_summary_lists_a_nonzero_stl(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = write_job(
                Path(raw),
                "d" * 32,
                status="succeeded",
                message="ok",
                log_text="PHASE=export\nSTL_OUTER_ARRAY_COUNT code=0 n=1\n",
                stl=b"solid creo_native\nendsolid creo_native\n",
            )
            summary = summarize_stl_job(directory)
        self.assertFalse(summary["stl_zero_bytes"])
        self.assertEqual(
            summary["stl_total_bytes"], len(b"solid creo_native\nendsolid creo_native\n")
        )
        self.assertEqual(summary["stl_files"][0]["path"], "output/bulb.stl")

    def test_native_source_has_the_diagnostic_markers(self):
        source = (ROOT / "native" / "generic.cpp").read_text(encoding="utf-8")
        for marker in (
            "STL_TESS_BEGIN",
            "STL_TESS_END",
            "STL_OUTER_ARRAY_COUNT",
            "STL_OUTPUT_OPEN",
            "STL_SURFACE_BEGIN",
            "STL_SURFACE_ID",
            "STL_BAD_INDEX",
            "STL_NONFINITE_VERTEX",
            "STL_FACET_BATCH",
            "STL_FILE_FLUSH",
            "STL_FILE_CLOSE",
            "STL_TESS_FREE_BEGIN",
            "STL_TESS_FREE_END",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)


class ArchivedEvidenceTests(unittest.TestCase):
    """Use the persisted jobs when this workspace still has them."""

    @unittest.skipUnless(
        (ROOT / "jobs" / "0f2a588d107343d8905afd6831056df3").is_dir(),
        "archived BUG-130 failure job is not present",
    )
    def test_archived_failure_job_summary(self):
        summary = summarize_stl_job(ROOT / "jobs" / "0f2a588d107343d8905afd6831056df3")
        self.assertEqual(summary["status"], "unknown_outcome")
        self.assertEqual(summary["exit_code"], 3221225477)
        self.assertTrue(summary["stl_zero_bytes"])
        self.assertEqual(summary["native_log"]["last_phase"], "export")

    @unittest.skipUnless(
        (ROOT / "jobs" / "37a35d07991647ada1db2170cc61316d").is_dir(),
        "archived successful STL job is not present",
    )
    def test_archived_success_job_is_nonzero(self):
        summary = summarize_stl_job(ROOT / "jobs" / "37a35d07991647ada1db2170cc61316d")
        self.assertEqual(summary["status"], "succeeded")
        self.assertFalse(summary["stl_zero_bytes"])
        self.assertGreater(summary["stl_total_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
