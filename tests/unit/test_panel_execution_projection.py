"""BUG-120: an unconfirmed panel exit remains visible in bounded job polls."""

import unittest

import bridge


class PanelExecutionProjection(unittest.TestCase):
    def test_unconfirmed_panel_survives_compact_and_empty_sections(self):
        job = {
            "job_id": "a" * 32,
            "status": "unknown_outcome",
            "message": "Panel exit is unconfirmed",
            "result": {
                "success": False,
                "panel_execution_unconfirmed": True,
                "message": "Selection failed before panel exit",
                "rollback_succeeded": False,
                "delivery_complete": True,
            },
        }
        for sections in (None, []):
            with self.subTest(sections=sections):
                result = bridge.compact_job(job, sections=sections)["result"]
                self.assertIs(result["panel_execution_unconfirmed"], True)
                self.assertIs(result["rollback_succeeded"], False)

    def test_absence_stays_absent(self):
        job = {"status": "failed", "result": {"success": False, "message": "Other failure"}}
        self.assertNotIn("panel_execution_unconfirmed", bridge.compact_job(job)["result"])


if __name__ == "__main__":
    unittest.main()
