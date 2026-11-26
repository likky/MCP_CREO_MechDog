"""BUG-151: the ``creo_capabilities`` contract shared by the smoke script and its gate.

``tools/test_mcp.py`` used to assert detail fields directly on the default
response and went stale when FEAT-023 turned ``creo_capabilities`` into a paged
tool: compact became a family index, and the script kept reading the pre-0.4.2
"one call returns the whole document" shape. The expectations now live only
here. The smoke script renders the problems, the unit gate proves the real
payload satisfies them, so a contract change fails loudly in one place instead
of rotting in an unexecuted script.

Nothing here reads the server or the model: the caller supplies one async
``fetch_page`` callback, which keeps the pagination walk itself under test.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

#: A compact family entry is an index. Two hints ride along because a client must
#: see them before choosing a route: ``limits_note`` (DEV-081/F05) and
#: ``runtime_admission`` (FEAT-074, the callback requirement of a direct blend).
FAMILY_INDEX_KEYS = frozenset(
    {"enabled", "tool", "limits_note", "runtime_admission", "runtime_ready"}
)

SECTION = "families"
PAGE_LIMIT = 50
MAX_PAGES = 64

LOFT_FAMILY = "loft_seed"
LOFT_TOOL = "creo_new_loft_part"
LOFT_EXPECTED = {
    "interpolation": ["straight", "smooth"],
    "section_count_input_range": [2, 20],
    "seed_section_count_must_match": True,
}

#: ``fetch_page(cursor)`` returns one ``creo_capabilities`` page:
#: ``detail="full"``, ``section="families"``, ``limit=PAGE_LIMIT``, ``cursor`` omitted on the
#: first call. The structured content of the tool result is what belongs here.
PageFetcher = Callable[[str | None], Awaitable[dict[str, Any]]]


async def capability_contract_problems(
    compact: dict[str, Any], fetch_page: PageFetcher
) -> list[str]:
    """Return every way the compact page and its paged families section disagree.

    An empty list means the response matches the published contract. Problems are
    plain sentences: the smoke script prints them instead of raising ``KeyError``,
    so a drift report names the contract that moved.
    """
    problems = _compact_problems(compact)
    entries, page_problems = await _families_entries(fetch_page)
    problems.extend(page_problems)

    families = compact.get("families") if isinstance(compact, dict) else None
    if isinstance(families, dict) and entries and len(entries) != len(families):
        problems.append(
            f"paged families section has {len(entries)} entries but the compact index "
            f"lists {len(families)}"
        )
    problems.extend(_loft_detail_problems(entries.get(LOFT_FAMILY)))
    return problems


async def fetch_capabilities_section(fetch_page: PageFetcher, section: str) -> dict[str, Any]:
    """Collect every entry of one ``detail="full"`` capabilities section.

    Raises ``RuntimeError`` listing every pagination problem if the walk does
    not complete cleanly, so test scripts never silently read page 1 only.
    """
    entries, problems = await _paged_section_entries(fetch_page, section, allow_empty=True)
    if problems:
        raise RuntimeError(
            f"creo_capabilities section={section!r} pagination failed: " + "; ".join(problems)
        )
    return entries


async def call_capabilities_section(
    call_capabilities: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    section: str,
    *,
    limit: int = PAGE_LIMIT,
) -> dict[str, Any]:
    """Page through one ``detail="full"`` section using a tool-call wrapper."""

    async def _page(cursor: str | None) -> dict[str, Any]:
        arguments: dict[str, Any] = {
            "detail": "full",
            "section": section,
            "limit": limit,
        }
        if cursor:
            arguments["cursor"] = cursor
        return await call_capabilities(arguments)

    return await fetch_capabilities_section(_page, section)


def _compact_problems(compact: dict[str, Any]) -> list[str]:
    if not isinstance(compact, dict):
        return [f"compact page is {type(compact).__name__}, expected an object"]
    problems: list[str] = []
    if compact.get("detail") != "compact":
        problems.append(f"compact page reports detail={compact.get('detail')!r}")
    count = compact.get("enabled_tool_count")
    if type(count) is not int or count <= 0:
        problems.append(f"enabled_tool_count = {count!r}, expected a positive integer")
    tool_count = compact.get("tool_count")
    if type(tool_count) is not int or tool_count <= 0:
        problems.append(f"tool_count = {tool_count!r}, expected a positive integer")
    elif type(count) is int and tool_count != count:
        problems.append(
            f"tool_count = {tool_count!r} disagrees with enabled_tool_count = {count!r}"
        )
    if compact.get("disabled_tools_hidden") is not True:
        problems.append(
            f"disabled_tools_hidden = {compact.get('disabled_tools_hidden')!r}, expected True"
        )
    for key in ("name", "version"):
        value = compact.get(key)
        if not (isinstance(value, str) and value.strip()):
            problems.append(f"compact page is missing {key}")
    families = compact.get("families")
    if not isinstance(families, dict) or not families:
        problems.append("compact page carries no families index")
        return problems
    for name, entry in sorted(families.items()):
        if not isinstance(entry, dict):
            problems.append(f"compact family {name} is {type(entry).__name__}, expected an object")
            continue
        extra = sorted(set(entry) - FAMILY_INDEX_KEYS)
        if extra:
            problems.append(
                f"compact family {name} must stay an index "
                f"(enabled/tool plus limits_note/runtime_admission); found {extra}. "
                f'Read detail fields with detail="full" and section="{SECTION}"'
            )
    loft = families.get(LOFT_FAMILY)
    if not isinstance(loft, dict):
        problems.append(f"compact families index is missing {LOFT_FAMILY}")
    else:
        if loft.get("enabled") is not True:
            problems.append(f"compact {LOFT_FAMILY}.enabled = {loft.get('enabled')!r}")
        if loft.get("tool") != LOFT_TOOL:
            problems.append(
                f"compact {LOFT_FAMILY}.tool = {loft.get('tool')!r}, expected {LOFT_TOOL}"
            )
    return problems


async def _paged_section_entries(
    fetch_page: PageFetcher,
    section: str,
    *,
    allow_empty: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Walk every page of one ``detail="full"`` section; return (key -> value, problems)."""
    entries: dict[str, Any] = {}
    problems: list[str] = []
    cursor: str | None = None
    offset = 0
    for page_number in range(1, MAX_PAGES + 1):
        page = await fetch_page(cursor)
        if not isinstance(page, dict):
            problems.append(
                f"{section} page {page_number} is {type(page).__name__}, expected an object"
            )
            return entries, problems
        if page.get("detail") != "full" or page.get("section") != section:
            problems.append(
                f"{section} page {page_number} reports detail={page.get('detail')!r} "
                f'section={page.get("section")!r}, expected "full"/"{section}"'
            )
        if page.get("offset") != offset:
            problems.append(
                f"{section} page {page_number} starts at offset {page.get('offset')!r}, "
                f"expected {offset}"
            )
        returned = page.get("returned")
        total = page.get("total")
        if (
            allow_empty
            and page_number == 1
            and returned == 0
            and total == 0
            and page.get("complete") is True
        ):
            return entries, problems
        if type(returned) is not int or returned <= 0:
            problems.append(f"{section} page {page_number} returned {returned!r} entries")
            return entries, problems
        for item in page.get("entries") or []:
            if not isinstance(item, dict) or not isinstance(item.get("key"), str):
                problems.append(
                    f"{section} page {page_number} carries an entry without a string key"
                )
                continue
            key = item["key"]
            if key in entries:
                problems.append(f"{section} entry {key} appears more than once while paging")
                continue
            if item.get("oversize"):
                problems.append(
                    f"{section} entry {key} is an oversize marker; the page budget cannot carry it"
                )
                continue
            entries[key] = item.get("value")
        offset += returned
        if page.get("complete") is True:
            if type(total) is int and total != offset:
                problems.append(f"{section} paging stopped after {offset} of {total} entries")
            return entries, problems
        cursor = page.get("next_cursor")
        if not isinstance(cursor, str) or not cursor:
            problems.append(
                f"{section} page {page_number} is incomplete but carries no next_cursor"
            )
            return entries, problems
    problems.append(f"{section} paging did not complete within {MAX_PAGES} pages")
    return entries, problems


async def _families_entries(
    fetch_page: PageFetcher,
) -> tuple[dict[str, Any], list[str]]:
    """Walk every families page; return (name -> full entry, problems)."""
    return await _paged_section_entries(fetch_page, SECTION, allow_empty=False)


def _loft_detail_problems(detail: Any) -> list[str]:
    if detail is None:
        return [f'family {LOFT_FAMILY} is missing from the paged section="{SECTION}" response']
    if not isinstance(detail, dict):
        return [f"paged family {LOFT_FAMILY} is {type(detail).__name__}, expected an object"]
    problems = [
        f"{LOFT_FAMILY}.{key} = {detail.get(key)!r}, expected {expected!r}"
        for key, expected in LOFT_EXPECTED.items()
        if detail.get(key) != expected
    ]
    if detail.get("enabled") is not True:
        problems.append(f"{LOFT_FAMILY}.enabled = {detail.get('enabled')!r}")
    if detail.get("tool") != LOFT_TOOL:
        problems.append(f"{LOFT_FAMILY}.tool = {detail.get('tool')!r}, expected {LOFT_TOOL}")
    return problems
