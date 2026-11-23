"""BUG-156/BUG-158 live acceptance: nested assembly insert and budget disclosure.

``nested_assembly``
    A managed assembly (two parts) is inserted into a parent assembly. The job
    must succeed and save/reload, the parent receipt must name
    ``source_model_type="assembly"``, ``source_snapshot=true`` and
    ``component_count=2``, the source assembly file (sha256, revision) must stay
    unchanged, the parent's nested tree must still contain both grandchildren,
    and the parent volume must equal the sum of the two parts.

``budget_disclosure``
    BUG-158: the submission receipt and the job view must publish the job
    timeout and the separate stall watchdog with the files it watches.

Only measured live results decide the cases; a failed or unverified step is
reported, never retried or resubmitted.
"""

from __future__ import annotations

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

from creo_mechdog.paths import SOURCE_PATHS  # noqa: E402
from tools.sheetmetal_live import (  # noqa: E402
    LiveRunner,
    failure_text,
    require_manual_start,
)

ROOT = SOURCE_PATHS.resource_root
PART_A_VOLUME_MM3 = 20.0 * 10.0 * 5.0
PART_B_VOLUME_MM3 = 10.0 * 10.0 * 5.0
VOLUME_TOLERANCE = 0.02


def part_plan(width: float, height: float) -> list:
    return [
        {
            "op": "sketch",
            "label": "profile",
            "plane": "XY",
            "entities": [
                {"type": "rectangle", "name": "body", "min": [0.0, 0.0], "max": [width, height]}
            ],
        },
        {"op": "extrude", "label": "solid", "sketch": "profile", "depth": 5.0},
    ]


def file_sha256(path: str) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


async def job(runner: LiveRunner, key: str, tool: str, arguments: dict) -> tuple[dict, dict, dict]:
    """Submit once, capture the first view (running or terminal), then poll."""
    receipt = await runner.submit(key, tool, arguments)
    first = await runner.call("creo_get_job", {"job_id": receipt["job_id"]})
    if first.get("status") in ("succeeded", "failed"):
        terminal = first
    else:
        terminal = await runner.wait_job(receipt["job_id"], budget=600.0)
    return receipt, first, terminal


def compact_inspection(payload: dict) -> dict:
    inspection = payload.get("inspection")
    return inspection if isinstance(inspection, dict) else {}


def evidence(terminal: dict) -> dict:
    result = terminal.get("result") if isinstance(terminal.get("result"), dict) else {}
    return {
        "job_id": terminal.get("job_id"),
        "job_status": terminal.get("status"),
        "revision": terminal.get("revision"),
        "saved_reload": result.get("saved_file_reloaded_and_verified"),
        "volume_mm3": result.get("volume_mm3"),
        "message": terminal.get("message"),
    }


async def main_live(output: Path, run_id: str) -> int:
    require_manual_start(ROOT / "config.json")
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT)
    async with Client(params, read_timeout_seconds=300) as client:
        runner = LiveRunner(
            client,
            output,
            "BUG-156/BUG-158 nested assembly and budget disclosure",
            "parent assembly receives a managed subassembly; receipts publish both budgets",
            run_id,
        )
        try:
            await runner.start()
            runner.report["environment_detail"] = await runner.call("creo_check_environment", {})

            part_a_receipt, part_a_first, part_a = await job(
                runner, "part_a", "creo_execute_plan", {"operations": part_plan(20.0, 10.0)}
            )
            part_b_receipt, _, part_b = await job(
                runner, "part_b", "creo_execute_plan", {"operations": part_plan(10.0, 10.0)}
            )
            runner.case(
                {
                    "case": "part_a",
                    **evidence(part_a),
                    "passed": part_a.get("status") == "succeeded",
                }
            )
            runner.case(
                {
                    "case": "part_b",
                    **evidence(part_b),
                    "passed": part_b.get("status") == "succeeded",
                }
            )
            if part_a.get("status") != "succeeded" or part_b.get("status") != "succeeded":
                runner.report["stopped"] = "base parts did not build; nothing else submitted"
                runner.finish()
                print(json.dumps({"report": str(output), "passed": False}, ensure_ascii=False))
                return 1

            # BUG-158: the receipt and the job view must publish the same budgets.
            budget_problems = []
            receipt_budgets = {
                "timeout_seconds": part_a_receipt.get("timeout_seconds"),
                "timeout_source": part_a_receipt.get("timeout_source"),
                "stall_watchdog_seconds": part_a_receipt.get("stall_watchdog_seconds"),
                "stall_watchdog_source": part_a_receipt.get("stall_watchdog_source"),
                "watch_files": part_a_receipt.get("watch_files"),
            }
            view_budgets = part_a_first.get("budgets") or {}
            if not isinstance(receipt_budgets["stall_watchdog_seconds"], int):
                budget_problems.append("receipt has no integer stall_watchdog_seconds")
            if receipt_budgets["watch_files"] != ["worker.log", "native.log"]:
                budget_problems.append(f"receipt watch_files={receipt_budgets['watch_files']!r}")
            if view_budgets.get("job_timeout_seconds") != receipt_budgets["timeout_seconds"]:
                budget_problems.append("job view timeout differs from the receipt")
            if (
                view_budgets.get("stall_watchdog_seconds")
                != receipt_budgets["stall_watchdog_seconds"]
            ):
                budget_problems.append("job view stall budget differs from the receipt")
            runner.case(
                {
                    "case": "budget_disclosure",
                    "receipt": receipt_budgets,
                    "job_view_status": part_a_first.get("status"),
                    "job_view_budgets": view_budgets,
                    "problems": budget_problems,
                    "passed": not budget_problems,
                }
            )

            sub_receipt, _, sub_new = await job(runner, "sub_new", "creo_new_assembly", {})
            sub_id = sub_new["model_id"]
            revision = sub_new["revision"]
            _, _, sub_a1 = await job(
                runner,
                "sub_a1",
                "creo_assemble_component",
                {
                    "model_id": sub_id,
                    "expected_revision": revision,
                    "label": "a1",
                    "source_model_id": part_a["model_id"],
                },
            )
            revision = sub_a1["revision"]
            _, _, sub_a2 = await job(
                runner,
                "sub_a2",
                "creo_assemble_component",
                {
                    "model_id": sub_id,
                    "expected_revision": revision,
                    "label": "a2",
                    "source_model_id": part_b["model_id"],
                },
            )
            sub_before = await runner.call("creo_inspect_model", {"model_id": sub_id})
            sub_file_before = sub_before.get("part_file")
            sub_sha_before = file_sha256(sub_file_before) if sub_file_before else None
            sub_revision = sub_before.get("revision")

            _, _, parent_new = await job(runner, "parent_new", "creo_new_assembly", {})
            parent_id = parent_new["model_id"]
            _, _, parent_insert = await job(
                runner,
                "parent_insert",
                "creo_assemble_component",
                {
                    "model_id": parent_id,
                    "expected_revision": parent_new["revision"],
                    "label": "sub1",
                    "source_model_id": sub_id,
                },
            )
            listed = await runner.call("creo_list_components", {"model_id": parent_id})
            record = None
            for item in listed.get("components") or []:
                if item.get("occurrence_label") == "sub1" or item.get("label") == "sub1":
                    record = item
                    break
            alias = (listed.get("aliases") or {}).get("sub1") or {}
            insert_result = (parent_insert.get("result") or {}).get("operations") or [{}]
            parent_after = await runner.call("creo_inspect_model", {"model_id": parent_id})
            sub_after = await runner.call("creo_inspect_model", {"model_id": sub_id})
            sub_file_after = sub_after.get("part_file")
            sub_sha_after = file_sha256(sub_file_after) if sub_file_after else None
            mass = await runner.call("creo_get_mass_properties", {"model_id": parent_id})

            problems = []
            if parent_insert.get("status") != "succeeded":
                problems.append(f"nested insert job {parent_insert.get('status')!r}")
            if (parent_insert.get("result") or {}).get(
                "saved_file_reloaded_and_verified"
            ) is not True:
                problems.append("parent insert was not saved and reloaded")
            if alias.get("source_model_type") != "assembly":
                problems.append(f"receipt source_model_type={alias.get('source_model_type')!r}")
            if alias.get("source_snapshot") is not True:
                problems.append("receipt does not record source_snapshot=true")
            if alias.get("component_count") != 2:
                problems.append(f"receipt component_count={alias.get('component_count')!r}")
            if record is None:
                problems.append("creo_list_components did not return the sub1 component")
            if sub_sha_before is None or sub_sha_after is None:
                problems.append("source assembly file hash is unavailable")
            elif sub_sha_before != sub_sha_after:
                problems.append("the nested insert rewrote the source assembly file")
            if sub_after.get("revision") != sub_revision:
                problems.append("the nested insert advanced the source assembly revision")
            expected_volume = PART_A_VOLUME_MM3 + PART_B_VOLUME_MM3
            volume = mass.get("volume_mm3")
            if not isinstance(volume, (int, float)):
                problems.append("parent assembly volume is unavailable")
            elif abs(volume - expected_volume) > expected_volume * VOLUME_TOLERANCE:
                problems.append(f"parent volume {volume!r} != {expected_volume!r}")
            runner.case(
                {
                    "case": "nested_assembly",
                    **evidence(parent_insert),
                    "parent_model_id": parent_id,
                    "sub_model_id": sub_id,
                    "sub_component_count": alias.get("component_count"),
                    "receipt_aliases": alias,
                    "operation_receipt": insert_result,
                    "sub_file": sub_file_before,
                    "sub_sha256_before": sub_sha_before,
                    "sub_sha256_after": sub_sha_after,
                    "sub_revision_before": sub_revision,
                    "sub_revision_after": sub_after.get("revision"),
                    "parent_volume_mm3": volume,
                    "expected_parent_volume_mm3": expected_volume,
                    "problems": problems,
                    "passed": not problems,
                }
            )

            # Nested tree: the resident parent must still expose the subassembly
            # and its two children after save/reload.
            tree_problems = []
            try:
                tree = await runner.call(
                    "creo_inspect_session_assembly", {"name": parent_after.get("model_name")}
                )
            except Exception as error:  # noqa: BLE001 - recorded, never retried
                tree = None
                tree_problems.append(f"session tree query failed: {type(error).__name__}: {error}")
            if tree is not None:
                nodes = tree.get("components") or []
                # Creo upper-cases component labels; depth 0 is the root level.
                labels = [
                    (str(item.get("occurrence_label") or "").lower(), item.get("depth"))
                    for item in nodes
                ]
                if not any(label == "sub1" for label, _ in labels):
                    tree_problems.append(f"sub1 missing from the session tree: {labels!r}")
                children = [label for label, depth in labels if depth == 1]
                if sorted(children) != ["a1", "a2"]:
                    tree_problems.append(f"grandchildren in the session tree: {children!r}")
            runner.case(
                {
                    "case": "nested_tree",
                    "model_name": parent_after.get("model_name"),
                    "components": None if tree is None else tree.get("components"),
                    "problems": tree_problems,
                    "passed": not tree_problems,
                }
            )
        except BaseException as error:
            runner.report["stopped"] = f"{type(error).__name__}: {error}"
            runner.finish()
            raise
    summary = runner.finish()
    print(json.dumps(summary, ensure_ascii=False))
    rows = [
        {key: case.get(key) for key in ("case", "job_status", "problems", "passed")}
        for case in runner.report["cases"]
    ]
    print(json.dumps({"passed": runner.report["passed"], "cases": rows}, ensure_ascii=False))
    return 0 if runner.report["passed"] else 1


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
    output = args.output or ROOT / "build" / "feedback0355_nested" / run_id / "report.json"
    if output.exists():
        raise SystemExit(f"refusing to overwrite {output}")
    if args.live:
        if not args.confirm_session_usable:
            print("live runs require --confirm-session-usable", file=sys.stderr)
            return 2
        return asyncio.run(main_live(output, run_id))
    report = {
        "task": "BUG-156/BUG-158 nested assembly and budget disclosure",
        "mode": "offline",
        "native_acceptance": "not_run",
        "plans": {
            "part_a": part_plan(20.0, 10.0),
            "part_b": part_plan(10.0, 10.0),
        },
        "provenance": provenance(),
        "failure_text_helper": failure_text.__module__,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(output), "mode": "offline"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
