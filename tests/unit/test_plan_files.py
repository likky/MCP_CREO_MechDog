"""DEV-089 T8: submit a plan from one frozen local JSON file."""

import asyncio
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server
from creo_mechdog import generic_bridge as general
from creo_mechdog import plan_files

OPERATIONS = [
    {
        "op": "extrude",
        "label": "plate",
        "sketch": "profile",
        "depth": 5,
    }
]


class PlanFileLoadingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def write(self, payload, name="plan.json", encoding="utf-8"):
        path = self.root / name
        text = payload if isinstance(payload, str) else json.dumps(payload)
        path.write_bytes(text.encode(encoding) if isinstance(text, str) else text)
        return path

    def test_valid_file_returns_operations_and_identity(self):
        path = self.write(OPERATIONS)
        operations, record = plan_files.load_plan_operations(str(path))
        self.assertEqual(operations, OPERATIONS)
        self.assertEqual(record["bytes"], path.stat().st_size)
        self.assertEqual(record["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(record["resolved_path"], str(path.resolve()))

    def test_utf8_bom_is_accepted(self):
        path = self.write(OPERATIONS, encoding="utf-8-sig")
        operations, _ = plan_files.load_plan_operations(str(path))
        self.assertEqual(operations, OPERATIONS)

    def test_duplicate_keys_are_refused(self):
        path = self.write('[{"op": "extrude", "label": "a", "label": "b"}]')
        with self.assertRaises(ValueError) as raised:
            plan_files.load_plan_operations(str(path))
        self.assertIn("duplicate JSON key", str(raised.exception))

    def test_non_finite_numbers_are_refused(self):
        path = self.write('[{"op": "extrude", "label": "a", "depth": NaN}]')
        with self.assertRaises(ValueError):
            plan_files.load_plan_operations(str(path))

    def test_top_level_must_be_the_operations_array(self):
        for payload in ({"operations": OPERATIONS}, "not json", [1, 2]):
            path = self.write(payload, name="bad.json")
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                plan_files.load_plan_operations(str(path))

    def test_relative_and_non_local_paths_are_refused(self):
        for path in (
            "plan.json",
            r"\\server\share\plan.json",
            r"\\?\C:\plan.json",
            r"\\.\C:\plan.json",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                plan_files.load_plan_operations(path)

    def test_directory_and_missing_file_are_refused(self):
        with self.assertRaises(ValueError):
            plan_files.load_plan_operations(str(self.root))
        with self.assertRaises(ValueError):
            plan_files.load_plan_operations(str(self.root / "missing.json"))

    def test_oversize_file_is_refused(self):
        path = self.write(OPERATIONS)
        with patch.object(plan_files, "MAX_PLAN_FILE_BYTES", 8):
            with self.assertRaises(ValueError) as raised:
                plan_files.load_plan_operations(str(path))
        self.assertIn("limit", str(raised.exception))

    def test_bytes_are_read_once(self):
        path = self.write(OPERATIONS)
        operations, record = plan_files.load_plan_operations(str(path))
        path.write_text("[]", encoding="utf-8")
        self.assertEqual(operations, OPERATIONS)
        self.assertEqual(
            record["sha256"], hashlib.sha256(json.dumps(OPERATIONS).encode()).hexdigest()
        )


class ExecutePlanPlanFileTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_plan_file_reaches_submit_as_the_operations_array(self):
        path = self.root / "plan.json"
        path.write_text(json.dumps(OPERATIONS), encoding="utf-8")
        recorded = []

        def fake_submit(operations, *args, **kwargs):
            recorded.append(operations)
            return {"job_id": "e" * 32}

        with (
            patch.object(general, "submit", side_effect=fake_submit),
            patch.object(server.startup, "require_ready"),
        ):
            result = asyncio.run(server.creo_execute_plan(plan_file=str(path)))
        self.assertEqual(recorded[0], OPERATIONS)
        self.assertEqual(
            result["plan_file"]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest()
        )

    def test_operations_and_plan_file_are_mutually_exclusive(self):
        path = self.root / "plan.json"
        path.write_text(json.dumps(OPERATIONS), encoding="utf-8")
        with self.assertRaises(ValueError):
            asyncio.run(server.creo_execute_plan(operations=[OPERATIONS[0]], plan_file=str(path)))

    def test_missing_both_sources_is_refused(self):
        with self.assertRaises(ValueError):
            asyncio.run(server.creo_execute_plan())


if __name__ == "__main__":
    unittest.main()
