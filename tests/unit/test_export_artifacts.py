"""BUG-020: export artifacts and Creo log excerpts are reported separately."""

import tempfile
import unittest
from pathlib import Path

from creo_mechdog import export_artifacts


class ExportArtifactsTests(unittest.TestCase):
    def test_step_export_moves_only_this_jobs_logs(self):
        with tempfile.TemporaryDirectory() as raw:
            job = Path(raw)
            output = job / "output"
            output.mkdir()
            (output / "part.stp").write_text("solid", encoding="utf-8")
            (output / "part__out.log.1").write_text("log", encoding="utf-8")
            (output / "caller_notes.txt").write_text("keep", encoding="utf-8")
            result: dict = {"success": True}
            export_artifacts.apply(result, job, [{"op": "export", "format": "step"}])
            self.assertEqual(result["export_artifacts"], ["output/part.stp"])
            self.assertEqual(result["export_diagnostics"], ["output/diagnostics/part__out.log.1"])
            self.assertIn("not modified", result["export_diagnostics_note"])
            self.assertTrue((output / "part.stp").is_file())
            self.assertTrue((output / "caller_notes.txt").is_file())
            self.assertFalse((output / "part__out.log.1").exists())
            self.assertTrue((output / "diagnostics" / "part__out.log.1").is_file())

    def test_non_export_plan_is_a_noop(self):
        with tempfile.TemporaryDirectory() as raw:
            job = Path(raw)
            output = job / "output"
            output.mkdir()
            (output / "part__out.log.1").write_text("log", encoding="utf-8")
            result: dict = {}
            export_artifacts.apply(result, job, [{"op": "extrude", "label": "e1"}])
            self.assertEqual(result, {})
            self.assertTrue((output / "part__out.log.1").is_file())

    def test_failed_export_still_archives_the_log_without_claiming_an_artifact(self):
        with tempfile.TemporaryDirectory() as raw:
            job = Path(raw)
            output = job / "output"
            output.mkdir()
            (output / "part__out.log.2").write_text("log", encoding="utf-8")
            result: dict = {"success": False}
            export_artifacts.apply(result, job, [{"op": "export", "format": "iges"}])
            self.assertNotIn("export_artifacts", result)
            self.assertEqual(result["export_diagnostics"], ["output/diagnostics/part__out.log.2"])

    def test_missing_output_directory_and_non_dict_result_are_safe(self):
        with tempfile.TemporaryDirectory() as raw:
            export_artifacts.apply({}, Path(raw), [{"op": "export", "format": "step"}])
            export_artifacts.apply(None, Path(raw), [{"op": "export", "format": "step"}])
            self.assertEqual(list(Path(raw).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
