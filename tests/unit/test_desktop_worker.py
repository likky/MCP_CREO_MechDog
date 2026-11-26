"""BUG-030 hidden worker launch through the interactive Explorer desktop."""

import contextlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from creo_mechdog import desktop_worker

ROOT = Path(__file__).resolve().parents[2]
COMMAND = [r"C:\repo\build\creo_worker.exe", "status", "2"]


class LauncherScriptTests(unittest.TestCase):
    def test_request_preserves_literals_and_only_allowed_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            cwd = directory / "零件 % ! &"
            command = [*COMMAND, 'arg with "quotes"', "%a% & !"]
            request = desktop_worker._launcher(
                directory,
                command,
                cwd,
                {"PATH": r"C:\工具 % !", "OTHER": "not needed"},
                10.0,
            )
            value = json.loads(request.read_text(encoding="utf-8"))
        self.assertEqual(value["command"], command)
        self.assertEqual(value["cwd"], str(cwd))
        self.assertEqual(value["env"], {"PATH": r"C:\工具 % !"})

    def test_license_environment_that_cannot_be_reproduced_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with self.assertRaisesRegex(desktop_worker.DesktopUnavailable, "license environment"):
                desktop_worker._launcher(
                    directory, COMMAND, directory, {"PTC_D_LICENSE_FILE": "fixture-license"}, 10.0
                )
            self.assertEqual(list(directory.iterdir()), [])

    def test_real_helper_process_preserves_unicode_cwd_argv_and_binary_output(self):
        with tempfile.TemporaryDirectory(prefix="零件 % ! & ") as tmp:
            directory = Path(tmp)
            argument = '螺栓 "%value%" & !'
            command = [
                sys.executable,
                "-c",
                "import json,os,sys; print(json.dumps([os.getcwd(),sys.argv[1],"
                "os.environ['PRO_COMM_MSG_EXE']])); sys.stderr.buffer.write(b'\\xff'); "
                "raise SystemExit(9)",
                argument,
            ]
            request = desktop_worker._launcher(
                directory,
                command,
                directory,
                {"PRO_COMM_MSG_EXE": "工具 & %"},
                time.monotonic() + 30,
            )
            subprocess.run(
                [sys.executable, "-I", desktop_worker.__file__, str(request)],
                cwd=directory,
                check=True,
                timeout=30,
            )
            result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
            stdout = json.loads((directory / "stdout.txt").read_bytes())
            self.assertEqual(result["returncode"], 9)
            self.assertEqual(stdout, [str(directory), argument, "工具 & %"])
            self.assertEqual((directory / "stderr.txt").read_bytes(), b"\xff")


class DesktopRunTests(unittest.TestCase):
    def parent(self):
        (ROOT / ".tmp").mkdir(exist_ok=True)
        target = Path(tempfile.mkdtemp(prefix="desktop_runs_", dir=ROOT / ".tmp"))
        self.addCleanup(shutil.rmtree, target, True)
        return target

    def execute(self, payload: dict):
        shell = Mock()

        def run(exe, params, cwd, verb, show):
            Path(cwd, "stdout.txt").write_bytes(payload["stdout"])
            Path(cwd, "stderr.txt").write_bytes(payload["stderr"])
            Path(cwd, "result.json").write_text(
                json.dumps({"returncode": payload["code"]}), encoding="utf-8"
            )
            return None

        shell.ShellExecute.side_effect = run
        return patch.object(
            desktop_worker, "_explorer_shell", return_value=contextlib.nullcontext(shell)
        )

    def test_result_is_read_back_and_temporary_directory_is_removed(self):
        parent = self.parent()
        payload = {"stdout": b'{"connected":true}', "stderr": b"warn", "code": 0}
        with self.execute(payload):
            result = desktop_worker.run(COMMAND, ROOT / "build", {"PATH": "a"}, 5, parent)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, payload["stdout"])
        self.assertEqual(result.stderr, payload["stderr"])
        self.assertEqual(list(parent.iterdir()), [])

    def test_missing_result_file_times_out_without_claiming_a_result(self):
        parent = self.parent()
        shell = Mock()
        with patch.object(
            desktop_worker, "_explorer_shell", return_value=contextlib.nullcontext(shell)
        ):
            with self.assertRaisesRegex(desktop_worker.DesktopUnavailable, "before timeout"):
                desktop_worker.run(COMMAND, ROOT / "build", {"PATH": "a"}, 0.1, parent)
        shell.ShellExecute.assert_called_once()

    def test_unavailable_desktop_returns_none(self):
        parent = self.parent()
        with patch.object(
            desktop_worker,
            "_explorer_shell",
            side_effect=desktop_worker.DesktopUnavailable("no desktop"),
        ):
            with self.assertRaisesRegex(desktop_worker.DesktopUnavailable, "no desktop"):
                desktop_worker.run(COMMAND, ROOT / "build", {"PATH": "a"}, 1, parent)
        self.assertEqual(list(parent.iterdir()), [])

    def test_non_numeric_exit_code_is_ignored(self):
        parent = self.parent()
        payload = {"stdout": b"", "stderr": b"", "code": "boom"}
        with self.execute(payload):
            with self.assertRaisesRegex(
                desktop_worker.DesktopUnavailable, "invalid process result"
            ):
                desktop_worker.run(COMMAND, ROOT / "build", {"PATH": "a"}, 5, parent)

    def test_cleanup_failure_preserves_the_completed_process(self):
        parent = self.parent()
        payload = {"stdout": b"result", "stderr": b"", "code": 0}
        with (
            self.execute(payload),
            patch.object(desktop_worker.shutil, "rmtree", side_effect=PermissionError),
            self.assertLogs(desktop_worker.__name__, level="WARNING"),
        ):
            result = desktop_worker.run(COMMAND, ROOT / "build", {}, 5, parent)
        self.assertEqual(result.stdout, b"result")

    def test_shell_is_hidden_and_uses_python_with_the_request(self):
        parent = self.parent()
        shell = Mock()
        with patch.object(
            desktop_worker, "_explorer_shell", return_value=contextlib.nullcontext(shell)
        ):
            with self.assertRaises(desktop_worker.DesktopUnavailable):
                desktop_worker.run(COMMAND, ROOT / "build", {"PATH": "a"}, 0.1, parent)
        call = shell.ShellExecute.call_args
        self.assertEqual(call.args[0], sys.executable)
        self.assertEqual(call.args[3:], ("open", 0))
        self.assertIn("request.json", call.args[1])
