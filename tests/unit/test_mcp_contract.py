"""BUG-151: the stdio smoke script's creo_capabilities contract must stay true.

What is checked here is the single source of expectations both sides use: the
real payload from ``server._capabilities_payload`` must satisfy ``mcp_contract``,
all drift modes must be reported instead of raising ``KeyError``, paged section
readers must collect full sections, and ``tools/*.py`` must not regress to
pre-0.4.2 compact ``creo_capabilities({})`` accesses.
"""

import copy
import re
import unittest
from pathlib import Path

import server
from creo_mechdog.capability_pages import capabilities_response, reset_snapshot
from creo_mechdog.mcp_contract import (
    FAMILY_INDEX_KEYS,
    LOFT_FAMILY,
    PAGE_LIMIT,
    call_capabilities_section,
    capability_contract_problems,
    fetch_capabilities_section,
)
from tools import dev_check

ROOT = Path(__file__).resolve().parents[2]
_COMPACT_DRIFT_PATTERNS = (
    re.compile(r'call[^\n]*"creo_capabilities"\s*,\s*\{\s*\}[^\n]*\["runtime"\]'),
    re.compile(r'call[^\n]*"creo_capabilities"\s*,\s*\{\s*\}[^\n]*\["references"\]'),
    re.compile(r'call[^\n]*"creo_capabilities"\s*,\s*\{\s*\}[^\n]*\["seed_library"\]'),
    re.compile(r'call[^\n]*"creo_capabilities"\s*,\s*\{\s*\}[^\n]*\["verified_evidence"\]'),
    re.compile(r'call[^\n]*"creo_capabilities"\s*,\s*\{\s*\}[^\n]*\.get\(\s*"tools"'),
    re.compile(r'capabilities\["runtime"\]'),
    re.compile(r'capabilities\["references"\]'),
    re.compile(r'capabilities\["seed_library"\]'),
    re.compile(r'capabilities\["verified_evidence"\]'),
    re.compile(r'cap\["runtime"\]'),
    re.compile(r'cap\["seed_library"\]'),
    re.compile(r'capability\["runtime"\]'),
)


def payload():
    """Real capabilities payload with a minimal tool list (only counts use it)."""
    tools = [
        {"name": "creo_capabilities", "description": ""},
        {"name": "creo_new_loft_part", "description": ""},
    ]
    return server._capabilities_payload(tools)


def page(source, cursor, section="families"):
    return capabilities_response(
        lambda: source, detail="full", section=section, limit=PAGE_LIMIT, cursor=cursor
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

    async def test_tool_count_mismatch_is_reported(self):
        summary = compact(self.source)
        summary["tool_count"] = summary["enabled_tool_count"] + 1
        problems = await capability_contract_problems(summary, self.fetch)
        self.assertTrue(any("tool_count" in problem for problem in problems), problems)

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

    async def test_call_capabilities_section_reads_runtime_and_references(self):
        async def call_capabilities(arguments):
            return capabilities_response(lambda: self.source, **arguments)

        runtime = await call_capabilities_section(call_capabilities, "runtime")
        self.assertIn("code_root", runtime)
        self.assertIn("source_changed_since_startup", runtime)

        references = await call_capabilities_section(call_capabilities, "references")
        self.assertIn("by_tool", references)

    async def test_fetch_capabilities_section_raises_on_incomplete_paging(self):
        async def broken(_cursor):
            return {
                "detail": "full",
                "section": "runtime",
                "offset": 0,
                "returned": 1,
                "total": 2,
                "complete": False,
                "entries": [{"key": "code_root", "value": "x"}],
            }

        with self.assertRaises(RuntimeError) as context:
            await fetch_capabilities_section(broken, "runtime")
        self.assertIn("next_cursor", str(context.exception))

    def test_smoke_script_uses_shared_contract_readiness_and_offline_gate(self):
        source = (ROOT / "tools/test_mcp.py").read_text(encoding="utf-8")
        self.assertIn("capability_contract_problems", source)
        self.assertIn("wait_for_startup", source)
        self.assertNotIn('["families"]["loft_seed"]["interpolation"]', source)
        gate_names = {name for name, _ in dev_check.OFFLINE_ACCEPTANCE_SCRIPTS}
        self.assertIn("test_mcp", gate_names)

    def test_tools_scripts_do_not_read_removed_sections_from_compact_capabilities(self):
        violations: list[str] = []
        for path in sorted((ROOT / "tools").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                for pattern in _COMPACT_DRIFT_PATTERNS:
                    if pattern.search(line):
                        violations.append(f"{path.name}:{lineno}: {line.strip()}")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
