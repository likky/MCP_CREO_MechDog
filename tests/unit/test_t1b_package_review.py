"""Small synthetic fixtures for the offline T1-B package auditor."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.review_t1b_package import audit, contained


class ReviewT1BPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / "package"
        self.package.mkdir()
        self.output = self.root / "audit"
        self.cases = []
        rows = []
        steps = []
        for i in range(6):
            name = f"t1b_{i}"
            relative = f"work/c{i}/{name}.prt.1"
            path = self.package / relative
            path.parent.mkdir(parents=True)
            content = f"fixture-{i}".encode()
            path.write_bytes(content)
            model_id = f"{i + 1:032x}"
            job_id = f"{i + 11:032x}"
            rows.append(
                f"| case {i} | `{relative}` | {len(content)} | `{hashlib.sha256(content).hexdigest()}` | `{model_id}` |"
            )
            refs = [{"index": j, "owner": name, "geom_id": 40 + j} for j in range(2)]
            request = f"REQ-{i}"
            self.cases.append(
                {
                    "case": name,
                    "model": name,
                    "request_id": request,
                    "adopted_model_id": model_id,
                    "requested_geometry_ids": refs,
                    "requested_sections": 2,
                    "selection_log": [
                        {
                            "index": j,
                            "geom_id": 40 + j,
                            "action": "PRO_SELECT_OVERRIDE" if j == 0 else "PRO_SELECT_TOGGLE",
                            "error": 0,
                        }
                        for j in range(2)
                    ],
                    "checks": {"bbox_ok": i != 3},
                    "quilt": {
                        "source": f"C:/other/models/{model_id}/output/inspection-verified-abcd.json"
                    },
                    "boundary": {"measure_job": job_id},
                }
            )
            steps.extend(
                {
                    "request_id": request,
                    "phase": "select",
                    "index": j,
                    "owner": name.upper(),
                    "geom_id": 40 + j,
                    "selection_action": "PRO_SELECT_OVERRIDE" if j == 0 else "PRO_SELECT_TOGGLE",
                    "error": 0,
                }
                for j in range(2)
            )
        (self.package / "T1B_REPORT.md").write_text("\n".join(rows), encoding="utf-8")
        (self.package / "evidence").mkdir()
        (self.package / "evidence/matrix_summary.json").write_text(
            json.dumps({"cases": self.cases}), encoding="utf-8"
        )
        (self.package / "probe/host").mkdir(parents=True)
        (self.package / "probe/host/session_steps.jsonl").write_text(
            "\n".join(map(json.dumps, steps)), encoding="utf-8"
        )

    def test_hash_logs_false_bbox_and_missing_originals(self):
        result = audit(self.package, self.output)
        self.assertTrue(all(row["matches"] for row in result["prt_table"]))
        self.assertTrue(all(c["host_sequence_matches"] for c in result["cases"]))
        self.assertFalse(result["cases"][3]["bbox_ok"])
        self.assertFalse(result["geometry_claims_independently_verified"])
        self.assertEqual(len(result["missing_original_receipts"]), 12)
        self.assertTrue(result["integrity_ok"])
        self.assertEqual(len(json.loads((self.output / "package_manifest.json").read_text())), 9)

    def test_hash_mismatch_and_wrong_owner_or_order(self):
        (self.package / "work/c0/t1b_0.prt.1").write_bytes(b"changed")
        log = self.package / "probe/host/session_steps.jsonl"
        lines = log.read_text().splitlines()
        first = json.loads(lines[0])
        first["owner"] = "wrong"
        lines[0] = json.dumps(first)
        log.write_text("\n".join(lines))
        result = audit(self.package, self.output)
        self.assertFalse(result["prt_table"][0]["matches"])
        self.assertFalse(result["cases"][0]["host_sequence_matches"])
        self.assertFalse(result["integrity_ok"])

    def test_index_count_id_and_request_mismatch(self):
        self.cases[0]["requested_geometry_ids"][0]["index"] = 1
        self.cases[1]["requested_sections"] = 3
        self.cases[2]["adopted_model_id"] = "f" * 32
        self.cases[3]["request_id"] = self.cases[4]["request_id"]
        (self.package / "evidence/matrix_summary.json").write_text(
            json.dumps({"cases": self.cases})
        )
        result = audit(self.package, self.output)
        self.assertFalse(result["cases"][0]["host_sequence_matches"])
        self.assertFalse(result["cases"][1]["requested_sections_match"])
        self.assertFalse(result["prt_table"][2]["adopted_model_id_matches_matrix"])
        self.assertFalse(result["unique_request_ids"])
        self.assertFalse(result["integrity_ok"])

    def test_receipts_copy_only_fixed_paths_and_reject_escape(self):
        root = self.root / "external"
        root.mkdir()
        model_id = self.cases[0]["adopted_model_id"]
        source = root / "models" / model_id / "output/inspection-verified-abcd.json"
        source.parent.mkdir(parents=True)
        source.write_text('{"claim":"original"}')
        result = audit(self.package, self.output, root)
        self.assertTrue(result["cases"][0]["receipts"][0]["present"])
        self.assertEqual(result["cases"][0]["receipts"][0]["identity_verification"], "not_checked")
        self.assertEqual(
            result["cases"][0]["receipts"][0]["sha256"],
            hashlib.sha256(source.read_bytes()).hexdigest(),
        )
        self.assertFalse(result["cases"][0]["independent_geometry_verified"])
        with self.assertRaises(ValueError):
            contained(root, Path("../escape"))
        with self.assertRaises(ValueError):
            audit(self.package, self.package / "nested")
        source.write_text("changed receipt")
        with self.assertRaises(ValueError):
            audit(self.package, self.output, root)
        self.cases[0]["adopted_model_id"] = "../escape"
        (self.package / "evidence/matrix_summary.json").write_text(
            json.dumps({"cases": self.cases})
        )
        with self.assertRaises(ValueError):
            audit(self.package, self.output, root)


if __name__ == "__main__":
    unittest.main()
