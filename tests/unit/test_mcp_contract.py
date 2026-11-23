"""BUG-151: the stdio smoke script's creo_capabilities contract must stay true.

The script itself is not run here (it starts a server and may start Creo). What is
checked is the single source of expectations both sides use: the real payload from
``server._capabilities_payload`` must satisfy ``mcp_contract``, and the four ways
this contract can drift must be reported instead of raising ``KeyError``.
"""

import copy
import unittest
from pathlib import Path

import server
from creo_mechdog.capability_pages import capabilities_response, reset_snapshot
from creo_mechdog.mcp_contract import (
    FAMILY_INDEX_KEYS,
    LOFT_FAMILY,
    PAGE_LIMIT,
    capability_contract_problems,
)

ROOT = Path(__file__).resolve().parents[2]


def payload():
    """Real capabilities payload with a minimal tool list (only counts use it)."""
    tools = [
        {"name": "creo_capabilities", "description": ""},
        {"name": "creo_new_loft_part", "description": ""},
    ]
    return server._capabilities_payload(tools)


def page(source, cursor):
    return capabilities_response(
        lambda: source, detail="full", section="families", limit=PAGE_LIMIT, cursor=cursor
    )


def compact(source):
    return capabilities_response(lambda: source, detail="compact")


class CapabilityContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # capability_pages keeps a process-level snapshot for 600 s; every test
        # needs its own so cursors and payload edits never leak across tests.
        reset_snapshot()
        self.addCleanup(reset_snapshot)
        self.source = payload()

    async def fetch(self, cursor):
        return page(self.source, cursor)

    async def test_real_payload_satisfies_the_smoke_contract(self):
        summary = compact(self.source)
        self.assertEqual(await capability_contract_problems(summary, self.fetch), [])

        first = page(self.source, None)
        self.assertEqual(first["offset"], 0)
        self.assertEqual(first["total"], len(summary["families"]))
        if not first["complete"]:
            # The old script failed exactly because the detailed family is not on
            # the first page; a fix that reads one page only must not pass.
            self.assertNotIn(LOFT_FAMILY, [entry["key"] for entry in first["entries"]])

    async def test_compact_families_stay_an_index(self):
        summary = compact(self.source)
        for name, entry in summary["families"].items():
            self.assertLessEqual(set(entry), FAMILY_INDEX_KEYS, name)
        self.assertEqual(summary["families"][LOFT_FAMILY]["tool"], "creo_new_loft_part")

    async def test_detail_fields_on_the_compact_page_are_reported(self):
        summary = compact(self.source)
        summary["families"][LOFT_FAMILY]["interpolation"] = ["straight", "smooth"]
        problems = await capability_contract_problems(summary, self.fetch)
        self.assertTrue(any("must stay an index" in problem for problem in problems), problems)

    async def test_changed_loft_values_are_reported(self):
        source = copy.deepcopy(self.source)
        source["families"][LOFT_FAMILY]["interpolation"] = ["straight"]

        async def fetch(cursor):
            return page(source, cursor)

        problems = await capability_contract_problems(compact(source), fetch)
        self.assertTrue(any("interpolation" in problem for problem in problems), problems)

    async def test_pagination_that_never_completes_is_reported(self):
        async def stuck(cursor):
            return {
                "detail": "full",
                "section": "families",
                "offset": 0,
                "returned": 1,
                "total": 100,
                "complete": False,
                "next_cursor": "stuck",
                "entries": [{"key": "only", "value": {}}],
            }

        problems = await capability_contract_problems(compact(self.source), stuck)
        self.assertTrue(any("did not complete" in problem for problem in problems), problems[-3:])

    def test_smoke_script_uses_the_shared_contract(self):
        source = (ROOT / "tools/test_mcp.py").read_text(encoding="utf-8")
        self.assertIn("capability_contract_problems", source)
        self.assertNotIn('["families"]["loft_seed"]["interpolation"]', source)


if __name__ == "__main__":
    unittest.main()
