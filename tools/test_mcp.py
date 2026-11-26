"""Exercise the real stdio transport. --create also creates a fresh native test part.

--protocol-only stops before the Creo session and modeling checks, so the tool
list and the creo_capabilities contract can be verified on a machine without a
session (BUG-151). --offline runs the same protocol checks against an in-repo
stdio server whose startup coordinator and update checker are patched out, so
dev_check can run this script automatically without launching Creo or touching
the network. The contract expectations live in creo_mechdog.mcp_contract so this
script and tests/unit/test_mcp_contract.py cannot drift apart.
"""

import argparse
import asyncio
import json
import runpy
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from creo_mechdog.mcp_contract import PAGE_LIMIT, capability_contract_problems
from tools.mcp_readiness import wait_for_startup
from version import VERSION

TERMINAL_JOB_STATUSES = ("succeeded", "failed", "unknown_outcome", "cancelled")


@contextmanager
def without_creo(server):
    """Run an offline stdio fixture without starting Creo or reading local setup."""
    fixture = ROOT / "build" / "offline-sdk-fixture"
    with (
        patch.object(server.startup, "start"),
        patch.object(
            server.bridge,
            "config",
            return_value={"creo_root": str(fixture), "vcvars64": str(fixture / "vcvars64.bat")},
        ),
        patch.object(server.bridge, "resolve_license_environment", return_value=(None, {})),
    ):
        yield


def _serve_offline() -> None:
    """Launch the real stdio entry with inert startup and a fixture environment."""
    import server

    with without_creo(server), patch.object(server.updates, "start"):
        runpy.run_path(str(ROOT / "server.py"), run_name="__main__")


def _report_path(create: bool, simple: bool, offline: bool) -> Path:
    if create:
        return ROOT / "build" / ("mcp_simple_test.json" if simple else "mcp_integration_test.json")
    if offline:
        return ROOT / "build" / "mcp_offline_test.json"
    return ROOT / "build" / "mcp_protocol_test.json"


def _write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


async def _read_saved_verified(client: Client, job_id: str, job: dict) -> bool:
    """Return saved_file_reloaded_and_verified from an inline or paged full job view."""
    if "result" in job and isinstance(job["result"], dict):
        return bool(job["result"].get("saved_file_reloaded_and_verified"))
    cursor = None
    for _ in range(64):
        arguments = {
            "job_id": job_id,
            "detail": "full",
            "section": "result_entries",
            "limit": 200,
        }
        if cursor:
            arguments["cursor"] = cursor
        page_reply = await client.call_tool("creo_get_job", arguments)
        assert not page_reply.is_error, page_reply
        page = page_reply.structured_content
        for entry in page.get("entries") or []:
            if (
                isinstance(entry, dict)
                and entry.get("path") == "result.saved_file_reloaded_and_verified"
            ):
                return bool(entry.get("value"))
        if page.get("complete") is True:
            break
        cursor = page.get("next_cursor")
        if not cursor:
            break
    raise AssertionError(
        "full job response carries neither inline result nor "
        "result.saved_file_reloaded_and_verified in section=result_entries"
    )


async def main(
    create: bool,
    simple: bool,
    classic: bool,
    protocol_only: bool,
    offline: bool = False,
):
    skip_session = protocol_only or offline
    report_path = _report_path(create, simple, offline)
    server_args = (
        [str(ROOT / "tools/test_mcp.py"), "--serve-offline"]
        if offline
        else [str(ROOT / "server.py")]
    )
    params = StdioServerParameters(command=sys.executable, args=server_args, cwd=ROOT)
    report = {
        "transport": "stdio",
        "client_mode": "legacy" if classic else "auto",
        "offline": offline,
    }
    try:
        async with Client(
            params, mode="legacy" if classic else "auto", read_timeout_seconds=60
        ) as client:
            report["protocol_version"] = client.protocol_version
            tools = await client.list_tools()
            report["tools"] = [t.name for t in tools.tools]
            from creo_mechdog.capabilities import UNAVAILABLE_OPERATIONS

            assert not {f"creo_{name}" for name in UNAVAILABLE_OPERATIONS} & set(report["tools"])
            assert {
                "creo_execute_plan",
                "creo_create_sketch",
                "creo_extrude",
                "creo_revolve",
                "creo_hole",
                "creo_dimension_pattern",
                "creo_new_drawing",
                "creo_create_udf",
                "creo_rib",
                "creo_boolean_bodies",
                "creo_new_loft_part",
            } <= set(report["tools"]), report
            assert {
                "creo_list_seeds",
                "creo_install_seed_library",
                "creo_validate_seed",
                "creo_new_airfoil_blade",
                "creo_create_airfoil_section",
                "creo_set_airfoil_parameters",
                "creo_update_sketch_geometry",
                "creo_transform_geometry",
                "creo_set_geometry_transform",
                "creo_group_features",
                "creo_reorder_features",
                "creo_axis_pattern",
            } <= set(report["tools"])
            loft_tool = next(t for t in tools.tools if t.name == "creo_new_loft_part")
            interpolation = loft_tool.input_schema["properties"]["interpolation"]
            assert set(interpolation["enum"]) == {"straight", "smooth"}, interpolation
            assert interpolation["default"] == "straight", interpolation
            assert not {"seed_file", "seed_feature_id"} & set(
                loft_tool.input_schema.get("required", [])
            )
            sections = loft_tool.input_schema["properties"]["sections"]
            assert sections["minItems"] == 2 and sections["maxItems"] == 20, sections
            report["loft_section_count_schema_verified"] = True
            report["loft_interpolation_schema_verified"] = True
            capabilities = await client.call_tool("creo_capabilities", {})
            assert not capabilities.is_error, capabilities
            assert capabilities.structured_content["enabled_tool_count"] == len(report["tools"]), (
                report["tools"]
            )
            assert capabilities.structured_content["tool_count"] == len(report["tools"]), (
                capabilities.structured_content.get("tool_count"),
                len(report["tools"]),
            )
            pages = 0

            async def families_page(cursor):
                nonlocal pages
                pages += 1
                arguments = {"detail": "full", "section": "families", "limit": PAGE_LIMIT}
                if cursor:
                    arguments["cursor"] = cursor
                page = await client.call_tool("creo_capabilities", arguments)
                assert not page.is_error, page
                return page.structured_content

            problems = await capability_contract_problems(
                capabilities.structured_content, families_page
            )
            assert not problems, "creo_capabilities contract drift: " + "; ".join(problems)
            report["capability_contract_verified"] = True
            report["capability_pages"] = pages
            report["server"] = {
                key: capabilities.structured_content[key] for key in ("name", "version")
            }
            assert report["server"] == {"name": "MCP_CREO_MechDog", "version": VERSION}, report[
                "server"
            ]
            environment = await client.call_tool("creo_check_environment", {})
            assert not environment.is_error, environment
            report["environment"] = environment.structured_content
            if offline:
                report["environment_uses_fixture"] = True
            assert "ready_to_build" in report["environment"], report["environment"]
            if skip_session:
                report["session"] = {
                    "checked": False,
                    "reason": "offline" if offline else "protocol_only",
                }
            else:
                assert report["environment"]["ready_to_build"], report["environment"]
                await wait_for_startup(client, report, report_path, budget=180)
                status = await client.call_tool("creo_session_status", {})
                assert not status.is_error, status
                report["session"] = status.structured_content
                assert report["session"]["connected"], report["session"]
            summary = {
                "tool_count": len(report["tools"]),
                "capability_contract_verified": True,
                "capability_pages": pages,
            }
            if not skip_session:
                summary["session_connected"] = report["session"]["connected"]
            print(json.dumps(summary), flush=True)
            invalid = await client.call_tool(
                "creo_create_plate",
                {
                    "length": 80,
                    "width": 60,
                    "thickness": 20,
                    "holes": [{"x": 40, "y": 0, "diameter": 8}],
                },
            )
            assert invalid.is_error, (
                "Invalid geometry must be rejected before submitting a native job"
            )
            report["invalid_geometry_rejected"] = True
            if create:
                assert report["session"].get("connected"), report["session"]
                spec = (
                    {"length": 42, "width": 30, "thickness": 6, "corner_radius": 0, "holes": []}
                    if simple
                    else {
                        "length": 100,
                        "width": 70,
                        "thickness": 12,
                        "corner_radius": 4,
                        "holes": [
                            {"x": x, "y": y, "diameter": 6}
                            for x, y in [(-35, -20), (35, -20), (35, 20), (-35, 20)]
                        ]
                        + [{"x": 0, "y": 0, "diameter": 10}],
                    }
                )
                created = await client.call_tool("creo_create_plate", spec)
                assert not created.is_error, created
                job_id = created.structured_content["job_id"]
                print(f"job_id={job_id}", flush=True)
                stage = None
                for _ in range(150):
                    result = await client.call_tool(
                        "creo_get_job", {"job_id": job_id, "detail": "full"}
                    )
                    assert not result.is_error, result
                    job = result.structured_content
                    state = (job["status"], job.get("stage"))
                    if state != stage:
                        print(f"progress={state}", flush=True)
                        stage = state
                    if job["status"] in TERMINAL_JOB_STATUSES:
                        report["job"] = job
                        break
                    await asyncio.sleep(2)
                else:
                    raise TimeoutError(f"Job is still running: {job_id}; do not submit a duplicate")
                _write_report(report_path, report)
                assert job["status"] == "succeeded", json.dumps(job, ensure_ascii=False, indent=2)
                saved_verified = await _read_saved_verified(client, job_id, job)
                assert saved_verified, json.dumps(job, ensure_ascii=False, indent=2)
                report["saved_file_reloaded_and_verified"] = True
                _write_report(report_path, report)
                print(json.dumps(job, ensure_ascii=False, indent=2), flush=True)
            else:
                _write_report(report_path, report)
    except BaseException:
        # Print the real underlying failure before mcp.Client's TaskGroup wraps
        # it in nested ExceptionGroups (BUG-138 / BUG-151).
        traceback.print_exc(file=sys.stderr)
        raise
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--simple", action="store_true")
    parser.add_argument("--classic", action="store_true")
    parser.add_argument(
        "--protocol-only",
        action="store_true",
        help="Verify the stdio transport, tool list and capabilities contract without a "
        "Creo session (skips ready_to_build, the session probe and every modeling check)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Verify the stdio transport, tool list and capabilities contract against an "
        "isolated in-repo server (patches out Creo startup and update network checks)",
    )
    parser.add_argument("--serve-offline", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve_offline:
        _serve_offline()
        raise SystemExit(0)
    if args.protocol_only and args.create:
        parser.error("--protocol-only cannot be combined with --create")
    if args.offline and (args.create or args.protocol_only):
        parser.error("--offline cannot be combined with --create or --protocol-only")
    asyncio.run(main(args.create, args.simple, args.classic, args.protocol_only, args.offline))
