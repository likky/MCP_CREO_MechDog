"""0.35.5 feedback / BUG-161: two arcs of one circle submitted to one round.

The reported job named two 180-degree arcs of a single circular rim (ids 116
and 174) in one round; Creo failed regeneration with status 6 and no feature
error detail, while the same round on one arc id succeeded. This run reproduces
a split rim from a revolved tube and checks two cases:

``duplicate_circle_ids``
    Both ids in one round plan are refused before a feature is created; the
    refusal names the circle, lists both ids (centre and radius) and asks to keep
    the smallest id. The model volume must not change.

``single_edge_id``
    The smallest id alone rounds the rim; volume drops and the saved/reloaded
    verification is true.

``selector_edge``
    BUG-155: a geometry_selector that matches one arc must reach the round as an
    edge (not be initialised as a surface and fail with -23).

Only measured geometry decides the case: the split rim comes from the saved
inspection, never from an assumption. A rim Creo reports as one arc records
``split_rim_found=false`` and both cases stay ``not_verified``.
"""

import argparse
import asyncio
import hashlib
import json
import platform
import sys
import time
import uuid
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from tools.test_feedback0270_same_circle import (  # noqa: E402
    HANG_BUDGET_SECONDS,
    ROOT,
    arc_point,
    base_evidence,
    circular_selector,
    create_base,
    message_text,
    revision_of,
    round_on,
    saved_reload,
)

TASK = "BUG-161 / 0.35.5 feedback same-circle duplicate edges"


def duplicate_plan(ids: list[int]) -> list:
    """One round whose reference sets name two separately resolved edges."""
    return [
        {
            "op": "round",
            "label": "round_rim",
            "size": 2.0,
            "references": [{"edge": {"kind": "edge", "id": edge_id}} for edge_id in ids],
        }
    ]


async def submit_round(runner, key: str, base: dict, operations: list) -> dict:
    expected_revision = base["revision"]
    response = await runner.submit(
        f"{key}:round",
        "creo_execute_plan",
        {
            "model_id": base["model_id"],
            "expected_revision": expected_revision,
            "operations": operations,
        },
    )
    terminal = await runner.wait_job(response["job_id"], budget=HANG_BUDGET_SECONDS)
    snapshot = await runner.snapshot(base["model_id"])
    revision = revision_of(terminal, snapshot)
    if isinstance(revision, int):
        base["revision"] = revision
    return {
        "job_id": response["job_id"],
        "job_status": terminal.get("status"),
        "expected_revision_sent": expected_revision,
        "message": message_text(terminal),
        "saved_reload": saved_reload(terminal),
        "revision": revision,
        "volume_mm3": runner.volume(snapshot),
    }


async def run_duplicate(runner, base: dict) -> dict:
    group = base["split_group"]
    ids = sorted(edge["id"] for edge in group["edges"])
    outcome = await submit_round(runner, "duplicate_circle_ids", base, duplicate_plan(ids))
    entry = {
        "case": "duplicate_circle_ids",
        **base_evidence(base),
        "edge_ids": ids,
        **outcome,
    }
    text = entry["message"]
    problems = []
    if entry["job_status"] != "failed":
        problems.append(f"the duplicate round returned {entry['job_status']!r}")
    if "lie on one circle" not in text:
        problems.append("the refusal does not name the duplicated circle")
    if "keep the smallest id" not in text:
        problems.append("the refusal does not ask to keep the smallest id")
    if "ProEdgeInit" in text or "status 6" in text:
        problems.append("the failure is still the opaque Toolkit/regeneration error")
    for edge_id in ids:
        if str(edge_id) not in text:
            problems.append(f"arc id {edge_id} is not listed in the refusal")
    if entry["saved_reload"] is True:
        problems.append("a refused duplicate round reported a saved reload")
    if entry["volume_mm3"] != base["volume_mm3"]:
        problems.append("the refused duplicate round changed the model volume")
    entry["problems"] = problems
    entry["passed"] = not problems
    return runner.case(entry)


async def run_single(runner, base: dict) -> dict:
    group = base["split_group"]
    edge_id = min(edge["id"] for edge in group["edges"])
    outcome = await round_on(runner, "single_edge_id", base, {"kind": "edge", "id": edge_id})
    entry = {
        "case": "single_edge_id",
        **base_evidence(base),
        "edge_id": edge_id,
        **outcome,
    }
    problems = []
    if entry["job_status"] != "succeeded":
        problems.append(f"the single arc id {edge_id} did not round")
    elif entry["saved_reload"] is not True:
        problems.append("the round succeeded without saved_file_reloaded_and_verified")
    volume = entry["volume_mm3"]
    if volume is None:
        problems.append("volume not measurable after the round")
    elif volume >= base["volume_mm3"]:
        problems.append(
            f"volume {volume!r} did not drop below the unrounded {base['volume_mm3']!r}"
        )
    entry["problems"] = problems
    entry["passed"] = not problems
    return runner.case(entry)


async def run_selector(runner, base: dict) -> dict:
    """BUG-155: a selector-matched edge id reaches the round as an edge."""
    group = base["split_group"]
    point = arc_point(group["edges"][0]["arc"])
    selector = circular_selector(group["center"], point)
    outcome = await round_on(runner, "selector_edge", base, selector)
    entry = {
        "case": "selector_edge",
        **base_evidence(base),
        "selector": selector,
        **outcome,
    }
    problems = []
    if entry["job_status"] != "succeeded":
        problems.append(f"the selector-matched edge did not round: {entry['job_status']!r}")
    elif "ProEdgeInit" in entry["message"] or "ProSurfaceInit" in entry["message"]:
        problems.append("the selector result was resolved with the wrong geometry type")
    elif entry["saved_reload"] is not True:
        problems.append("the round succeeded without saved_file_reloaded_and_verified")
    volume = entry["volume_mm3"]
    if volume is None:
        problems.append("volume not measurable after the round")
    elif volume >= base["volume_mm3"]:
        problems.append(
            f"volume {volume!r} did not drop below the unrounded {base['volume_mm3']!r}"
        )
    entry["problems"] = problems
    entry["passed"] = not problems
    return runner.case(entry)


def not_verified(runner, case: str, base: dict, reason: str) -> dict:
    entry = {"case": case, **base_evidence(base), "problems": [reason], "passed": False}
    entry["verified"] = False
    return runner.case(entry)


async def main_live(output: Path, run_id: str) -> int:
    from tools.sheetmetal_live import LiveRunner, require_manual_start

    require_manual_start(ROOT / "config.json")
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT)
    async with Client(params, read_timeout_seconds=300) as client:
        runner = LiveRunner(
            client,
            output,
            TASK,
            "a split circular rim is refused when both arc ids reach one round",
            run_id,
        )
        try:
            await runner.start()
            runner.report["hang_budget_seconds"] = HANG_BUDGET_SECONDS
            base = await create_base(runner, "bug161")
            problems = []
            if base["base_status"] != "succeeded":
                problems.append(f"the base tube did not build: {base['base_status']!r}")
            if base["base_saved_reload"] is not True:
                problems.append("the base tube was not saved and reloaded")
            runner.case(
                {
                    "case": "base_split_rim",
                    **base_evidence(base),
                    "split_rim_found": base["split_group"] is not None,
                    "problems": problems,
                    "passed": not problems,
                    "verified": base["split_group"] is not None,
                }
            )
            if base["split_group"] is None:
                reason = "the revolved rim came back as one arc; the duplicate pair cannot be built"
                for case in ("duplicate_circle_ids", "single_edge_id"):
                    not_verified(runner, case, base, reason)
            else:
                await run_duplicate(runner, base)
                await run_single(runner, base)
            selector_base = await create_base(runner, "bug155")
            if selector_base["split_group"] is None:
                not_verified(
                    runner,
                    "selector_edge",
                    selector_base,
                    "the second base model did not report a split rim",
                )
            else:
                await run_selector(runner, selector_base)
        except BaseException as error:
            runner.report["stopped"] = f"{type(error).__name__}: {error}"
            runner.finish()
            raise
    summary = runner.finish()
    print(json.dumps(summary, ensure_ascii=False))
    rows = [
        {
            key: case.get(key)
            for key in ("case", "job_status", "volume_mm3", "verified", "problems", "passed")
        }
        for case in runner.report["cases"]
    ]
    print(json.dumps({"passed": runner.report["passed"], "cases": rows}, ensure_ascii=False))
    return 0 if runner.report["passed"] else 1


def contract() -> dict:
    return {
        "duplicate_circle_ids": {
            "expectation": (
                "failed before feature creation; message says 'lie on one circle', lists both "
                "ids with centre and radius, asks to keep the smallest id; volume unchanged"
            )
        },
        "single_edge_id": {
            "expectation": "succeeded on the smallest id; volume drops; saved reload verified"
        },
        "selector_edge": {
            "expectation": (
                "a point-anchored geometry_selector rounds the matched arc as an edge; "
                "no ProEdgeInit/ProSurfaceInit type error; volume drops; saved reload verified"
            )
        },
    }


def provenance() -> dict:
    from version import VERSION

    return {
        "version": VERSION,
        "environment": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "auto_start_creo": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-session-usable", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    run_id = f"{time.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
    output = args.output or ROOT / "build" / "feedback0355_selector_round" / run_id / "report.json"
    if output.exists():
        raise SystemExit(f"refusing to overwrite {output}")
    if args.live:
        if not args.confirm_session_usable:
            print("live runs require --confirm-session-usable", file=sys.stderr)
            return 2
        return asyncio.run(main_live(output, run_id))
    report = {
        "task": TASK,
        "mode": "offline",
        "native_acceptance": "not_run",
        "contract": contract(),
        "provenance": provenance(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_name("report.sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "contract": report["contract"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
