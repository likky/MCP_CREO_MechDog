"""BUG-138: dev_check offline-acceptance gate, isolated from the real scripts.

subprocess.run is mocked throughout so these stay fast and never launch Creo
or the acceptance scripts themselves. The gate still runs in production on
every invocation, including --skip-unit.
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools import dev_check

FIXTURE_STYLES = {
    "schema_version": 1,
    "tool_versions": {"ruff": "fixture"},
    "configuration": {"pyproject.toml": "fixture"},
    "lint": [],
    "unformatted": {},
    "python_files_checked": 1,
    "cpp_files_checked": 0,
    "source_sha256": "fixture",
}

FIRST_SCRIPT = dev_check.OFFLINE_ACCEPTANCE_SCRIPTS[0][0]
SECOND_SCRIPT = dev_check.OFFLINE_ACCEPTANCE_SCRIPTS[1][0]


def _passing_results() -> dict:
    return {name: {"status": "passed"} for name, _ in dev_check.OFFLINE_ACCEPTANCE_SCRIPTS}


class OfflineAcceptanceGate(unittest.TestCase):
    def test_both_scripts_exit_zero_are_reported_passed(self):
        proc = subprocess.CompletedProcess(["x"], 0, "ok\n", "")
        with patch.object(dev_check.subprocess, "run", return_value=proc) as run:
            results = dev_check.run_offline_acceptance(Path("."))
        self.assertEqual(len(run.call_args_list), len(dev_check.OFFLINE_ACCEPTANCE_SCRIPTS))
        for name, _ in dev_check.OFFLINE_ACCEPTANCE_SCRIPTS:
            self.assertEqual(results[name]["status"], "passed")
            self.assertEqual(results[name]["exit_code"], 0)
            self.assertIn("elapsed_seconds", results[name])

    def test_nonzero_exit_is_reported_failed_and_stops_before_later_scripts(self):
        def fake_run(args, **_kwargs):
            return subprocess.CompletedProcess(args, 3, "stdout tail\n", "stderr tail\n")

        with patch.object(dev_check.subprocess, "run", side_effect=fake_run) as run:
            results = dev_check.run_offline_acceptance(Path("."))
        self.assertEqual(len(run.call_args_list), 1)
        self.assertEqual(results[FIRST_SCRIPT]["status"], "failed")
        self.assertEqual(results[FIRST_SCRIPT]["exit_code"], 3)
        self.assertEqual(results[FIRST_SCRIPT]["stdout_tail"], "stdout tail\n")
        self.assertEqual(results[FIRST_SCRIPT]["stderr_tail"], "stderr tail\n")
        self.assertNotIn(SECOND_SCRIPT, results)

    def test_timeout_is_reported_timed_out_and_stops_before_later_scripts(self):
        def fake_run(args, **kwargs):
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])

        with patch.object(dev_check.subprocess, "run", side_effect=fake_run) as run:
            results = dev_check.run_offline_acceptance(Path("."))
        self.assertEqual(len(run.call_args_list), 1)
        self.assertEqual(results[FIRST_SCRIPT]["status"], "timed_out")
        self.assertIn("elapsed_seconds", results[FIRST_SCRIPT])
        self.assertNotIn(SECOND_SCRIPT, results)

    def _run_main(self, argv, offline):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "version.py").write_text('VERSION = "fixture"\n', encoding="utf-8")
            dev_check.save_json(root / dev_check.BASELINE, dict(FIXTURE_STYLES))
            with (
                patch.object(dev_check, "ROOT", root),
                patch.object(dev_check, "git_state", return_value={}),
                patch.object(dev_check, "collect_styles", return_value=dict(FIXTURE_STYLES)),
                patch.object(dev_check, "run_offline_acceptance", offline),
                patch.object(dev_check.subprocess, "run") as unit_run,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                code = dev_check.main(argv)
            report_path = root / "build/development_check.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            return code, report, offline, unit_run

    def test_gate_runs_even_with_skip_unit_when_it_passes(self):
        offline = MagicMock(return_value=_passing_results())
        code, report, offline, unit_run = self._run_main(["--skip-unit"], offline)
        self.assertEqual(code, 0)
        self.assertTrue(report["success"])
        offline.assert_called_once()
        unit_run.assert_not_called()
        self.assertEqual(report["unit_tests"], "not_run")
        self.assertEqual(report["offline_acceptance"], _passing_results())

    def test_skip_unit_still_fails_when_offline_gate_fails(self):
        failing = _passing_results()
        failing[FIRST_SCRIPT] = {
            "status": "failed",
            "exit_code": 1,
            "stderr_tail": "boom",
        }
        offline = MagicMock(return_value=failing)
        code, report, offline, unit_run = self._run_main(["--skip-unit"], offline)
        self.assertEqual(code, 1)
        self.assertFalse(report["success"])
        offline.assert_called_once()
        unit_run.assert_not_called()
        self.assertEqual(report["unit_tests"], "not_run")


if __name__ == "__main__":
    unittest.main()
