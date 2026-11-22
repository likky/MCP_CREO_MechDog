"""BUG-143 offline contract for real result quilt ids and solidify references."""

import unittest
from pathlib import Path

from creo_mechdog.job_projection import compact_operation
from creo_mechdog.operation_results import annotate_native_result, enforce_compact_budget

ROOT = Path(__file__).resolve().parents[2]
SURFACES = ROOT / "native" / "surfaces.cpp"
QUILT_MERGE = ROOT / "native" / "quilt_merge.cpp"


def operation(kind, label, **overrides):
    record = {
        "op": kind,
        "index": 0,
        "label": label,
        "execution_status": "succeeded",
        "effect_status": "committed",
    }
    record.update(overrides)
    return record


def native_result(operations, aliases, quilts=None, *, success=True):
    result = {
        "success": success,
        "operations": operations,
        "aliases": aliases,
        "inspection": {"quilts": quilts or []},
    }
    return annotate_native_result(result, readonly=False)


class QuiltResultProjectionTests(unittest.TestCase):
    def test_merge_uses_measured_result_not_result_feature_ownership(self):
        result = native_result(
            [operation("quilt_merge", "joined", feature_id=199, result_quilt_id=144)],
            {"joined": {"op": "quilt_merge", "feature_id": 199, "quilt_id": 144}},
            [{"quilt_id": 144, "feature_ids": [138]}],
        )
        record = result["operations"][0]
        self.assertEqual(record["quilt_id"], 144)
        self.assertEqual(compact_operation(record)["quilt_id"], 144)
        self.assertEqual(result["aliases"]["joined"]["quilt_id"], 144)

    def test_fill_and_mirror_use_unique_native_feature_membership(self):
        result = native_result(
            [
                operation("surface_fill", "cap", feature_id=177),
                operation("mirror", "mirrored", index=1),
            ],
            {
                "cap": {"op": "surface_fill", "feature_id": 177},
                "mirrored": {"op": "mirror", "feature_id": 150},
            },
            [
                {"quilt_id": 144, "feature_ids": [138], "bbox_mm": [[0, 0, 0], [1, 1, 1]]},
                {"quilt_id": 155, "feature_ids": [150], "bbox_mm": [[0, 0, 0], [1, 1, 1]]},
                {"quilt_id": 196, "feature_ids": [177], "bbox_mm": [[0, 0, 0], [1, 1, 1]]},
            ],
        )
        fill, mirror = result["operations"]
        self.assertEqual(fill["quilt_id"], 196)
        self.assertEqual(mirror["quilt_id"], 155)
        self.assertEqual(result["aliases"]["cap"]["quilt_id"], 196)
        self.assertEqual(result["aliases"]["mirrored"]["quilt_id"], 155)
        self.assertEqual(compact_operation(mirror)["quilt_id"], 155)

    def test_native_fill_receipt_does_not_need_a_python_geometry_guess(self):
        result = native_result(
            [operation("surface_fill", "cap", feature_id=177, quilt_id=196)],
            {"cap": {"op": "surface_fill", "feature_id": 177}},
            quilts=None,
        )
        self.assertEqual(result["operations"][0]["quilt_id"], 196)
        self.assertEqual(result["aliases"]["cap"]["quilt_id"], 196)

    def test_missing_or_multiple_matches_never_fabricate_an_id(self):
        result = native_result(
            [
                operation("mirror", "ambiguous"),
                operation("surface_fill", "missing", index=1, feature_id=177),
            ],
            {
                "ambiguous": {"op": "mirror", "feature_id": 150},
                "missing": {"op": "surface_fill", "feature_id": 177},
            },
            [
                {"quilt_id": 155, "feature_ids": [150]},
                {"quilt_id": 156, "feature_ids": [150]},
                {"quilt_id": 196, "feature_ids": [138], "bbox_mm": [[0, 0, 0], [1, 1, 1]]},
            ],
        )
        for record in result["operations"]:
            self.assertNotIn("quilt_id", record)
            self.assertNotIn("quilt_id", result["aliases"][record["label"]])

    def test_conflicting_merge_evidence_stays_unidentified(self):
        result = native_result(
            [operation("quilt_merge", "joined", feature_id=199, result_quilt_id=144)],
            {"joined": {"op": "quilt_merge", "feature_id": 199, "quilt_id": 155}},
            [{"quilt_id": 144, "feature_ids": [138]}],
        )
        self.assertNotIn("quilt_id", result["operations"][0])

    def test_rolled_back_merge_does_not_gain_a_committed_result_id(self):
        result = native_result(
            [
                operation(
                    "quilt_merge",
                    "joined",
                    feature_id=199,
                    result_quilt_id=144,
                    effect_status="rolled_back",
                )
            ],
            {"joined": {"op": "quilt_merge", "feature_id": 199}},
            [{"quilt_id": 144, "feature_ids": [138]}],
            success=False,
        )
        self.assertNotIn("quilt_id", result["operations"][0])

    def test_budget_trim_keeps_the_result_id(self):
        record = operation("mirror", "mirrored", quilt_id=155, padding="x" * 4000)
        summary = {"result": {"operations": [record]}}
        bounded = enforce_compact_budget(summary, budget=200)
        self.assertEqual(bounded["result"]["operations"][0]["quilt_id"], 155)


class QuiltNativeSourceTests(unittest.TestCase):
    def test_fill_publishes_only_one_openable_owned_quilt(self):
        source = SURFACES.read_text(encoding="utf-8")
        helper = source[
            source.index("static int verified_feature_quilt") : source.index(
                "static ProSelection solidify_quilt_selection"
            )
        ]
        fill = source[
            source.index("static void generic_fill") : source.index(
                "static void generic_surface_solid"
            )
        ]
        self.assertIn("ids.size() != 1", helper)
        self.assertIn("ProQuiltInit", helper)
        self.assertIn('details["quilt_id"] = quilt_id', fill)
        self.assertIn('remember(op, f, {{"quilt_id", quilt_id}})', fill)
        self.assertIn("stage_operation_result(details)", fill)

    def test_solidify_consumes_recorded_result_ids_without_feature_reverse_visit(self):
        source = SURFACES.read_text(encoding="utf-8")
        helper = source[
            source.index("static ProSelection solidify_quilt_selection") : source.index(
                "static void generic_fill"
            )
        ]
        for marker in (
            'result_op != "quilt_merge"',
            'result_op != "mirror"',
            'result_op != "surface_trim"',
            'result_op == "surface_trim" ? "result_quilt_id" : "quilt_id"',
            "ProQuiltInit",
            "collect_model_quilts",
            "matches.size() == 1",
        ):
            self.assertIn(marker, helper)
        self.assertNotIn("ProFeatureGeomitemVisit", helper)
        self.assertIn('reference.at("kind") != "quilt_feature"', helper)
        self.assertIn("return resolve(reference)", helper)

    def test_merge_native_snapshot_is_the_public_id_source(self):
        source = QUILT_MERGE.read_text(encoding="utf-8")
        self.assertIn('details["result_quilt_id"]', source)
        self.assertIn('remember(op, feature, {{"quilt_id", result_id}})', source)

    def test_mirror_refuses_every_feature_reference_before_create(self):
        # Live 2026-11-21: a solid feature passed as a mirror item hung Creo's
        # main thread inside ProFeatureWithoptionsCreate (330 s and 240 s, then
        # toolkit_code=-38); a surface feature had already killed it with an
        # EXCEPTION_NONCONTINUABLE_EXCEPTION. ProMirror.h lists no PRO_FEATURE
        # item, so both branches refuse before create() and name a route that is
        # a real mirror item.
        source = (ROOT / "native" / "advanced.cpp").read_text(encoding="utf-8")
        mirror = source[
            source.index("static J generic_mirror") : source.index("static J draft_reference_json")
        ]
        guard = mirror[mirror.index('if (kind == "feature")') : mirror.index("bool known = false")]
        for marker in (
            "PRO_E_MIRROR_REF_ITEMS",
            "hangs Creo's main thread",
            "{kind:'quilt',id:N}",
            "{kind:'part'}",
            "Nothing was created or modified",
        ):
            self.assertIn(marker, guard)
        self.assertEqual(guard.count("throw std::runtime_error"), 2)
        self.assertNotIn("++feature_references", mirror)
        # Both refusals precede creation, so no mirror feature can be attempted.
        self.assertGreater(mirror.index("ProFeature f = create(root)"), mirror.index("hangs Creo"))


if __name__ == "__main__":
    unittest.main()
