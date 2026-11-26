"""FEAT-073/T10: bounded serial mass-property reads with per-item receipts."""

import json
import tempfile
import unittest
from collections import Counter
from itertools import count
from pathlib import Path
from unittest.mock import patch

import bridge
from creo_mechdog import capabilities, generic_bridge


def native_reading(**overrides):
    base = {
        "volume_mm3": 6000.0,
        "mass_g": 47.1,
        "density_g_cm3": 7.85,
        "density_source": "request",
        "mass_source": "computed_from_density",
        "center_of_mass_mm": [5.0, 10.0, 15.0],
        "material_assigned": True,
        "mass_unit": "kg",
        "hint": None,
        "volume_query_code": 0,
        "mass_query_code": -1,
        "units_query_code": 0,
    }
    base.update(overrides)
    return base


def fake_clock(values):
    return patch.object(generic_bridge.time, "monotonic", side_effect=values)


class BatchMassPropertiesTest(unittest.TestCase):
    def test_each_model_gets_its_own_job_and_normalized_receipt(self):
        ids = count(1)
        submitted: dict[str, list[dict]] = {}
        workdir = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="feat073-")))

        def submit(operations, **kwargs):
            job_id = f"job{next(ids)}"
            submitted[job_id] = operations
            self.assertTrue(kwargs["readonly"])
            return {"job_id": job_id}

        def job_path(job_id):
            path = workdir / job_id
            path.mkdir(exist_ok=True)
            (path / "job.json").write_text(
                json.dumps(
                    {
                        "status": "succeeded",
                        "revision": 3,
                        "result": {"operations": [{"mass_properties": native_reading()}]},
                    }
                ),
                encoding="utf-8",
            )
            return path

        with (
            patch.object(generic_bridge, "submit", side_effect=submit),
            patch.object(bridge, "job_path", side_effect=job_path),
        ):
            report = generic_bridge.get_mass_properties_batch(["a" * 32, "b" * 32], 7.85)

        self.assertEqual(report["requested"], 2)
        self.assertEqual(report["succeeded"], 2)
        self.assertEqual((report["failed"], report["skipped"]), (0, 0))
        self.assertTrue(report["all_succeeded"])
        self.assertEqual(report["time_budget_seconds"], 180.0)
        first, second = report["items"]
        self.assertNotEqual(first["job_id"], second["job_id"])
        self.assertEqual([first["model_id"], second["model_id"]], ["a" * 32, "b" * 32])
        for item in (first, second):
            self.assertEqual(item["status"], "succeeded")
            self.assertEqual(item["revision"], 3)
            self.assertEqual(item["volume_mm3"], 6000.0)
            self.assertEqual(item["mass_g"], 47.1)
            self.assertEqual(item["density_source"], "request")
            self.assertEqual(item["mass_source"], "computed_from_density")
        self.assertEqual(
            list(submitted.values())[0], [{"op": "mass_properties", "density_g_cm3": 7.85}]
        )

    def test_no_density_keeps_the_what_if_absent_from_every_item(self):
        def receipt(model_id, density, wait_seconds):
            return {"job_id": f"job-{model_id[:2]}", "model_id": model_id, "revision": 1}

        with patch.object(generic_bridge, "_mass_properties_receipt", side_effect=receipt) as call:
            report = generic_bridge.get_mass_properties_batch(["a" * 32, "b" * 32])
        self.assertTrue(report["all_succeeded"])
        self.assertEqual([item.args[1] for item in call.call_args_list], [None, None])

    def test_more_than_the_documented_limit_is_refused_before_any_job(self):
        with patch.object(generic_bridge, "submit") as submit:
            with self.assertRaisesRegex(ValueError, "at most 16 models"):
                generic_bridge.get_mass_properties_batch([f"{index:032x}" for index in range(17)])
        submit.assert_not_called()

    def test_duplicate_ids_are_refused_before_any_job(self):
        model = "a" * 32
        with patch.object(generic_bridge, "submit") as submit:
            with self.assertRaisesRegex(ValueError, "repeats"):
                generic_bridge.get_mass_properties_batch([model, model])
        submit.assert_not_called()

    def test_empty_and_non_string_inputs_are_refused(self):
        for value in ([], [""], [None], "a" * 32):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    generic_bridge.get_mass_properties_batch(value)

    def test_budget_must_stay_inside_the_documented_range(self):
        for value in (9, 601, True, "180"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "time_budget_seconds"):
                    generic_bridge.get_mass_properties_batch(["a" * 32], time_budget_seconds=value)

    def test_invalid_id_fails_only_that_item_and_later_items_still_run(self):
        def receipt(model_id, density, wait_seconds):
            if model_id == "not-a-model":
                raise ValueError("Invalid model_id")
            return {"job_id": f"job-{model_id[:2]}", "model_id": model_id, "revision": 1}

        with patch.object(generic_bridge, "_mass_properties_receipt", side_effect=receipt):
            report = generic_bridge.get_mass_properties_batch(["a" * 32, "not-a-model", "b" * 32])

        self.assertEqual((report["succeeded"], report["failed"], report["skipped"]), (2, 1, 0))
        self.assertFalse(report["all_succeeded"])
        failed = report["items"][1]
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_kind"], "invalid_request")
        self.assertIn("Invalid model_id", failed["error"])
        self.assertIsNone(failed["blocking_job_id"])
        self.assertEqual(report["items"][2]["status"], "succeeded")

    def test_failed_native_query_does_not_cancel_the_next_model(self):
        def receipt(model_id, density, wait_seconds):
            if model_id.startswith("f"):
                raise RuntimeError("Mass properties query failed: job x")
            return {"job_id": "j", "model_id": model_id, "revision": 2}

        with patch.object(generic_bridge, "_mass_properties_receipt", side_effect=receipt):
            report = generic_bridge.get_mass_properties_batch(["f" * 32, "a" * 32])

        self.assertEqual(report["items"][0]["error_kind"], "query_failed")
        self.assertEqual(report["items"][1]["status"], "succeeded")

    def test_busy_channel_stops_new_items_and_names_the_blocking_job(self):
        busy = bridge.ToolkitBusy("Creo Toolkit is busy", holder={"job_id": "blocker"})
        with patch.object(generic_bridge, "_mass_properties_receipt", side_effect=busy):
            report = generic_bridge.get_mass_properties_batch(["a" * 32, "b" * 32])

        self.assertEqual(report["succeeded"], 0)
        self.assertEqual(report["items"][0]["error_kind"], "toolkit_busy")
        self.assertEqual(report["items"][0]["blocking_job_id"], "blocker")
        self.assertEqual(
            report["items"][1],
            {
                "model_id": "b" * 32,
                "status": "skipped",
                "reason": "toolkit_busy",
            },
        )

    def test_item_timeout_skips_the_rest_with_the_same_reason(self):
        timeout = generic_bridge.MassPropertiesTimeout(
            "Mass properties query did not finish: job x"
        )
        with patch.object(generic_bridge, "_mass_properties_receipt", side_effect=timeout):
            report = generic_bridge.get_mass_properties_batch(["a" * 32, "b" * 32])

        self.assertEqual(report["items"][0]["error_kind"], "timeout")
        self.assertEqual(report["items"][1]["reason"], "timeout")
        self.assertEqual(report["skipped"], 1)

    def test_budget_exhausted_before_a_start_marks_the_rest_skipped(self):
        receipts = [{"job_id": "j1", "model_id": "a" * 32, "revision": 1}]
        with (
            patch.object(generic_bridge, "_mass_properties_receipt", side_effect=receipts),
            fake_clock([100.0, 100.5, 111.0, 111.6]),
        ):
            report = generic_bridge.get_mass_properties_batch(
                ["a" * 32, "b" * 32], time_budget_seconds=10
            )

        self.assertEqual(report["items"][0]["status"], "succeeded")
        self.assertEqual(report["items"][1]["reason"], "time_budget_exhausted")
        self.assertEqual(report["elapsed_seconds"], 11.6)
        self.assertFalse(report["all_succeeded"])

    def test_cut_short_wait_is_reported_as_the_budget_that_ended(self):
        timeout = generic_bridge.MassPropertiesTimeout(
            "Mass properties query did not finish: job x"
        )
        with (
            patch.object(generic_bridge, "_mass_properties_receipt", side_effect=timeout) as call,
            fake_clock([100.0, 100.5, 101.0, 101.1]),
        ):
            report = generic_bridge.get_mass_properties_batch(
                ["a" * 32, "b" * 32], time_budget_seconds=10
            )

        # The first item could only wait 9.5 s of its 120 s allowance, so the
        # budget, not the query, ended the wait.
        self.assertAlmostEqual(call.call_args.args[2], 9.5)
        self.assertEqual(report["items"][0]["error_kind"], "timeout")
        self.assertEqual(report["items"][1]["reason"], "time_budget_exhausted")

    def test_summary_counts_every_item_exactly_once(self):
        def receipt(model_id, density, wait_seconds):
            raise ValueError("Invalid model_id")

        with patch.object(generic_bridge, "_mass_properties_receipt", side_effect=receipt):
            report = generic_bridge.get_mass_properties_batch(["a" * 32, "b" * 32, "c" * 32])

        statuses = Counter(item["status"] for item in report["items"])
        self.assertEqual(statuses, Counter({"failed": 3}))
        self.assertEqual(
            (report["requested"], report["succeeded"], report["failed"], report["skipped"]),
            (3, 0, 3, 0),
        )
        self.assertEqual(len(report["items"]), 3)

    def test_capabilities_declare_the_same_bounds_as_the_code(self):
        batch = capabilities.families()["mass_properties"]["batch"]
        self.assertEqual(batch["tool"], "creo_get_mass_properties_batch")
        limits = batch["limits"]
        self.assertEqual(limits["model_ids"], generic_bridge.MASS_PROPERTIES_BATCH_LIMIT)
        budget = limits["time_budget_seconds"]
        self.assertEqual(
            budget["default"], int(generic_bridge.MASS_PROPERTIES_BATCH_BUDGET_SECONDS)
        )
        self.assertEqual(
            budget["min"], int(generic_bridge.MASS_PROPERTIES_BATCH_MIN_BUDGET_SECONDS)
        )
        self.assertEqual(
            budget["max"], int(generic_bridge.MASS_PROPERTIES_BATCH_MAX_BUDGET_SECONDS)
        )


if __name__ == "__main__":
    unittest.main()
