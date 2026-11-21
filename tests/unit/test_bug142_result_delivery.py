"""BUG-142: disconnect cannot erase an already persisted execution conclusion."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import bridge
import generic_bridge as general
from creo_mechdog import model_registry
from creo_mechdog.build_support import compiler_setup_script

ROOT = Path(__file__).resolve().parents[2]
CRASH = 0xC0000409


class WorkerWiring(unittest.TestCase):
    def test_worker_sources_compile_as_utf8(self):
        # BUG-142 root cause: without /utf-8 MSVC reads the UTF-8 em dash under
        # the system code page, turning it into an invalid byte in the receipt
        # message; nlohmann's strict dump then threw and the worker aborted.
        bridge = (ROOT / "bridge.py").read_text(encoding="utf-8")
        self.assertEqual(bridge.count("/std:c++17 /utf-8"), 3)

    def test_modeling_exits_use_pre_disconnect_publication(self):
        worker = (ROOT / "native/worker.cpp").read_text(encoding="utf-8")
        include = worker.index('#include "worker_result_delivery.h"')
        alias = worker.index("#define deliver_native_result deliver_worker_result")
        self.assertLess(include, alias)
        for call_site in (
            '#include "generic.cpp"',
            '#include "drawing.cpp"',
            "deliver_native_result(job, plate_result",
        ):
            self.assertLess(alias, worker.index(call_site))
        wrapper = (ROOT / "native/worker_result_delivery.h").read_text(encoding="utf-8")
        self.assertLess(
            wrapper.index('publish_native_json(job + L"\\\\native_result.json"'),
            wrapper.index("return deliver_native_result("),
        )


class NativeResultDeliveryFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name != "nt" or not (ROOT / "config.json").exists():
            raise unittest.SkipTest("local Windows compiler configuration not available")
        cls.temporary = tempfile.TemporaryDirectory(prefix="bug142_native_")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.directory = Path(cls.temporary.name)
        settings = json.loads((ROOT / "config.json").read_text(encoding="utf-8-sig"))
        cls.exe = cls.directory / "bug142_delivery.exe"
        batch = cls.directory / "build.cmd"
        batch.write_text(
            "@echo off\n"
            + compiler_setup_script(settings)
            + f'\ncl /nologo /MD /EHsc /std:c++17 /I"{ROOT / "native"}" '
            + f'"{ROOT / "tests/native/test_bug142_result_delivery.cpp"}" '
            + f'/Fo"{cls.directory / "fixture.obj"}" /Fe"{cls.exe}"\nexit /b %errorlevel%\n',
            encoding="utf-8",
        )
        built = subprocess.run(
            ["cmd.exe", "/d", "/c", str(batch)],
            cwd=cls.directory,
            capture_output=True,
            timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if built.returncode:
            raise AssertionError((built.stdout + built.stderr).decode(errors="replace"))

    def run_case(self, mode: str) -> tuple[subprocess.CompletedProcess, Path]:
        directory = self.directory / mode
        directory.mkdir()
        (directory / "scenario.txt").write_text(mode, encoding="utf-8")
        process = subprocess.run(
            [str(self.exe), "generic", str(directory)],
            capture_output=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return process, directory

    def test_legacy_order_reproduces_missing_result(self):
        process, directory = self.run_case("legacy_crash")
        self.assertEqual(process.returncode & 0xFFFFFFFF, CRASH)
        self.assertFalse((directory / "native_result.json").exists())
        observed = json.loads((directory / "disconnect_observed.json").read_text())
        self.assertTrue(observed["native_checkpoint_exists"])
        self.assertFalse(observed["native_result_exists"])

    def test_abnormal_disconnect_preserves_rollback_fact_and_exit_signal(self):
        process, directory = self.run_case("crash")
        self.assertEqual(process.returncode & 0xFFFFFFFF, CRASH)
        result = json.loads((directory / "native_result.json").read_text())
        self.assertFalse(result["success"])
        self.assertTrue(result["rollback_succeeded"])
        self.assertEqual(result["rollback_code"], 0)
        self.assertEqual(result["rollback_witness"], {"checkpoint": "saved", "verified": True})
        self.assertFalse(result["delivery_complete"])
        self.assertEqual(result["completion_stage"], "before_disconnect")
        self.assertIsNone(result["disconnect_code"])
        observed = json.loads((directory / "disconnect_observed.json").read_text())
        self.assertTrue(observed["native_result_exists"])
        self.assertFalse(observed["delivery_complete"])
        self.assertTrue(observed["rollback_succeeded"])

    def test_disconnect_watchdog_also_leaves_the_pre_result(self):
        process, directory = self.run_case("hang")
        self.assertEqual(process.returncode, 31)
        result = json.loads((directory / "native_result.json").read_text())
        checkpoint = json.loads((directory / "native_checkpoint.json").read_text())
        self.assertTrue(result["rollback_succeeded"])
        self.assertFalse(result["delivery_complete"])
        self.assertEqual(result["completion_stage"], "before_disconnect")
        self.assertEqual(checkpoint["completion_stage"], "disconnect_timeout")

    def test_normal_disconnect_still_publishes_the_original_terminal_status(self):
        for mode, expected_exit, expected_success in (
            ("rollback", 30, False),
            ("success", 0, True),
        ):
            with self.subTest(mode=mode):
                process, directory = self.run_case(mode)
                self.assertEqual(process.returncode, expected_exit)
                result = json.loads((directory / "native_result.json").read_text())
                self.assertEqual(result["success"], expected_success)
                self.assertTrue(result["delivery_complete"])
                self.assertEqual(result["completion_stage"], "result_delivery")
                self.assertEqual(result["disconnect_code"], 0)
                if not expected_success:
                    self.assertTrue(result["rollback_succeeded"])

    def test_strict_dump_on_invalid_utf8_reproduces_the_crash_signature(self):
        # BUG-142 root-cause reproduction: dump(2) with the strict handler throws
        # on a Toolkit-shaped invalid byte after the output file was created, and
        # the uncaught exception exits 0xC0000409. The live failure left exactly
        # this artifact: a 0-byte temporary result.
        process, directory = self.run_case("strict_dump_crash")
        self.assertEqual(process.returncode & 0xFFFFFFFF, CRASH)
        target = directory / "strict_result.json"
        self.assertTrue(target.is_file())
        self.assertEqual(target.stat().st_size, 0)
        self.assertFalse((directory / "native_result.json").exists())

    def test_invalid_utf8_failure_is_published_with_replacement(self):
        process, directory = self.run_case("invalid_utf8")
        self.assertEqual(process.returncode, 30)
        result = json.loads((directory / "native_result.json").read_text(encoding="utf-8"))
        self.assertFalse(result["success"])
        self.assertTrue(result["delivery_complete"])
        self.assertTrue(result["rollback_succeeded"])
        self.assertIn("toolkit text with invalid", result["message"])
        self.assertFalse((directory / "native_result.json.tmp").exists())

    def test_invalid_utf8_success_keeps_the_success_projection(self):
        process, directory = self.run_case("invalid_utf8_complete")
        self.assertEqual(process.returncode, 0)
        result = json.loads((directory / "native_result.json").read_text(encoding="utf-8"))
        self.assertTrue(result["success"])
        self.assertTrue(result["delivery_complete"])


class MissingFactProtection(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="bug142_protection_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "jobs").mkdir()
        (self.root / "models").mkdir()
        stack = ExitStack()
        self.addCleanup(stack.close)
        for obj, name, value in (
            (bridge, "ROOT", self.root),
            (bridge, "JOBS", self.root / "jobs"),
            (general, "MODELS", self.root / "models"),
        ):
            stack.enter_context(patch.object(obj, name, value))
        self.model_id = "d" * 32
        self.job_id = "e" * 32
        model_path = general.model_path(self.model_id)
        (model_path / "output").mkdir(parents=True)
        self.part = model_path / "output" / "part.prt.1"
        self.part.write_bytes(b"fixture part")
        model_registry.write_model(
            model_path,
            {
                "model_id": self.model_id,
                "model_name": "bug142_part",
                "revision": 7,
                "status": "ready",
                "model_type": "part",
                "part_file": str(self.part),
                "output_directory": str(model_path / "output"),
            },
        )
        directory = bridge.job_path(self.job_id)
        (directory / "output").mkdir(parents=True)
        self.directory = directory
        self.request = {
            "new": False,
            "model": {
                "model_id": self.model_id,
                "model_name": "bug142_part",
                "model_type": "part",
                "revision": 7,
            },
            "operations": [],
            "readonly": False,
            "components": {},
        }
        bridge.write_json(directory / "request.json", self.request)
        self.manifest = {
            "job_id": self.job_id,
            "kind": "generic",
            "model_id": self.model_id,
            "status": "queued",
        }
        bridge.write_json(directory / "job.json", self.manifest)

    def run_worker(self, result: dict | None, returncode: int = CRASH) -> tuple[dict, dict]:
        def fake_run(*args, **kwargs):
            if result is not None:
                bridge.write_json(self.directory / "native_result.json", result)
            return subprocess.CompletedProcess([], returncode)

        with (
            patch.object(bridge, "build_native", return_value=self.root / "worker.exe"),
            patch.object(bridge, "native_environment", return_value={}),
            patch.object(bridge, "config", return_value={}),
            patch.object(bridge, "note_native_outcome", return_value=None),
            patch.object(general.subprocess, "run", side_effect=fake_run),
        ):
            general.run_generic_job(self.job_id, copy.deepcopy(self.manifest))
        finished = bridge.read_json(self.directory / "job.json")
        model = model_registry.read_control(general.model_path(self.model_id))
        return finished, model

    def test_missing_result_keeps_unknown_revision_and_reservation(self):
        finished, model = self.run_worker(None)
        self.assertEqual(finished["status"], "unknown_outcome")
        self.assertNotIn("result", finished)
        self.assertEqual(model["revision"], 7)
        self.assertEqual(model["status"], "unknown_outcome")
        self.assertEqual(model["pending_job"], self.job_id)

    def test_incomplete_success_cannot_commit_revision(self):
        result = {
            "success": True,
            "saved_file_reloaded_and_verified": True,
            "part_file": str(self.part),
            "delivery_complete": False,
            "completion_stage": "before_disconnect",
            "disconnect_code": None,
        }
        finished, model = self.run_worker(result)
        self.assertEqual(finished["status"], "unknown_outcome")
        self.assertEqual(model["revision"], 7)
        self.assertEqual(model["pending_job"], self.job_id)


if __name__ == "__main__":
    unittest.main()
