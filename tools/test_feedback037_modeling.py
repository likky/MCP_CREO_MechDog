"""0.3.7 remaining native regressions via stdio MCP; no process or failure injection."""

from __future__ import annotations

import argparse
import asyncio
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from creo_mechdog.paths import SOURCE_PATHS

ROOT = SOURCE_PATHS.resource_root
sys.path.insert(0, str(ROOT))

from creo_mechdog import inspection_refs
from tools.dev_check import git_state, source_hash
from tools.mcp_readiness import wait_for_startup
from tools.test_direct_loft import Probe, circle_sections
from tools.test_p1_modeling import box, identity


def close_matrix(actual: list, expected: list) -> None:
    assert len(actual) == len(expected) == 4
    assert all(len(row) == 4 for row in actual + expected)
    assert all(abs(a - b) < 1e-7 for ar, er in zip(actual, expected) for a, b in zip(ar, er)), (
        actual
    )


async def components(probe: Probe) -> None:
    source = await probe.job("creo_execute_plan", {"operations": box()}, "component_source")
    assembly = await probe.job("creo_new_assembly", {}, "assembly")
    placed = await probe.job(
        "creo_assemble_component",
        {
            **identity(assembly),
            "label": "member",
            "source_model_id": source["model_id"],
            "translation": [-30, 20, 0],
            "rotation": [0, 0, 30],
        },
        "initial_placement",
    )
    before = placed["result"]["inspection"]["components"][0]["transform"]
    assert abs(before[3][0] + 30) < 1e-7 and abs(before[3][1] - 20) < 1e-7
    constraints = [
        {
            "type": "align",
            "assembly_reference": {"kind": "datum_plane", "axis": axis},
            "component_reference": {"kind": "datum_plane", "axis": axis},
        }
        for axis in "xyz"
    ]
    solved = await probe.job(
        "creo_component_constraints",
        {
            **identity(placed),
            "component": "member",
            "constraints": constraints,
        },
        "constraints_replace_fixed_pose",
    )
    expected = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    component = solved["result"]["inspection"]["components"][0]
    close_matrix(component["transform"], expected)
    assert component["transform_source"] == "component_to_assembly"
    assert not component["underconstrained"] and not component["packaged"]
    refreshed = await probe.job(
        "creo_refresh_model", {"model_id": solved["model_id"]}, "assembly_reload"
    )
    close_matrix(refreshed["result"]["inspection"]["components"][0]["transform"], expected)
    assert refreshed["revision"] == placed["revision"] + 1


def plane_constraint(relation: str, axis: str, **fields) -> dict:
    return {
        "type": relation,
        "assembly_reference": {"kind": "datum_plane", "axis": axis},
        "component_reference": {"kind": "datum_plane", "axis": axis},
        **fields,
    }


async def constraint_baseline(probe: Probe, *, assert_guard: bool = False) -> None:
    source = await probe.job("creo_execute_plan", {"operations": box()}, "bug036_source")
    for case, first in (
        ("align_control", plane_constraint("align", "z")),
        ("reported_sides", plane_constraint("mate", "z")),
        ("reversed_mate_side", plane_constraint("mate", "z", component_side="red")),
    ):
        assembly = await probe.job("creo_new_assembly", {}, f"{case}_assembly")
        placed = await probe.job(
            "creo_assemble_component",
            {
                **identity(assembly),
                "source_model_id": source["model_id"],
                "label": "member",
                "translation": [-30, 20, 0],
                "rotation": [0, 0, 30],
            },
            f"{case}_fixed",
        )
        result = await probe.job(
            "creo_component_constraints",
            {
                **identity(placed),
                "component": "member",
                "constraints": [
                    first,
                    plane_constraint("align", "y"),
                    plane_constraint("align", "x"),
                ],
            },
            f"{case}_constraints",
            allow_failure=not assert_guard,
            expected_failure=assert_guard and case == "reported_sides",
        )
        if not assert_guard:
            continue
        before = placed["result"]["inspection"]["components"][0]
        if case == "reported_sides":
            failure = result["result"]["failed_operation"]
            assert failure["constraint_reason"] == "placement_mismatch", failure
            assert failure["placement_matches_constraints"] is False, failure
            assert abs(failure["max_distance_error_mm"] - 30) < 1e-7, failure
            assert abs(failure["max_angle_error_deg"] - 180) < 1e-7, failure
            assert result["result"]["rollback_succeeded"] is True
            refreshed = await probe.job(
                "creo_refresh_model", {"model_id": placed["model_id"]}, "bug036_verify_rollback"
            )
            restored = refreshed["result"]["inspection"]["components"][0]
            close_matrix(restored["transform"], before["transform"])
            assert restored["constraints"] == before["constraints"]
            assert refreshed["revision"] == placed["revision"]
            result = await probe.job(
                "creo_execute_plan",
                {
                    **identity(refreshed),
                    "operations": [
                        {
                            "op": "component_constraints",
                            "component": "member",
                            "constraints": [
                                plane_constraint("mate", "z", component_side="red"),
                                plane_constraint("align", "y"),
                                plane_constraint("align", "x"),
                            ],
                        }
                    ],
                },
                "bug036_retry_with_compatible_sides",
            )
        assert result["revision"] == placed["revision"] + 1
        component = result["result"]["inspection"]["components"][0]
        close_matrix(component["transform"], pose_at_z(0))
        assert not component["underconstrained"] and not component["packaged"]
        check_placement_receipt(result, 3)


def pose_at_z(z: float) -> list:
    return [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, z, 1]]


def check_placement_receipt(job: dict, count: int) -> None:
    receipt = job["result"]["operations"][0]["constraint_placement"]
    assert receipt["phase"] == "after_reload", receipt
    assert receipt["measured_count"] == count, receipt
    assert receipt["placement_matches_constraints"] is True, receipt
    assert receipt["max_distance_error_mm"] <= receipt["distance_tolerance_mm"], receipt
    assert receipt["max_angle_error_deg"] <= receipt["angle_tolerance_deg"], receipt


async def constraint_guard(probe: Probe) -> None:
    await constraint_baseline(probe, assert_guard=True)


async def constraint_offsets(probe: Probe) -> None:
    source = await probe.job("creo_execute_plan", {"operations": box()}, "bug036_offset_source")
    assembly = await probe.job("creo_new_assembly", {}, "bug036_offset_assembly")
    for relation in ("align_offset", "mate_offset"):
        component_side = "red" if relation == "mate_offset" else "yellow"
        for offset, assembly_side, moving_side, expected_z, label in (
            (5, "yellow", component_side, 5, "offset_pos"),
            (-5, "yellow", component_side, -5, "offset_neg"),
            (5, "red", "yellow" if component_side == "red" else "red", 5, "red_side"),
        ):
            component_label = f"{relation}_{label}"
            result = await probe.job(
                "creo_assemble_component",
                {
                    **identity(assembly),
                    "source_model_id": source["model_id"],
                    "label": component_label,
                    "placement": "constraints",
                    "constraints": [
                        plane_constraint(
                            relation,
                            "z",
                            offset=offset,
                            assembly_side=assembly_side,
                            component_side=moving_side,
                        ),
                        plane_constraint("align", "x"),
                        plane_constraint("align", "y"),
                    ],
                },
                f"bug036_{relation}_{label}",
            )
            assert result["revision"] == assembly["revision"] + 1
            check_placement_receipt(result, 3)
            member = result["result"]["inspection"]["components"][-1]
            close_matrix(member["transform"], pose_at_z(expected_z))
            assembly = result

    partial = await probe.job(
        "creo_component_constraints",
        {
            **identity(assembly),
            "component": component_label,
            "constraints": [plane_constraint("align_offset", "z", offset=8)],
        },
        "bug036_replace_with_underconstrained_group",
    )
    check_placement_receipt(partial, 1)
    member = partial["result"]["inspection"]["components"][-1]
    assert member["underconstrained"], member
    assert len(member["constraints"]) == 1, member
    transform = member["transform"]
    assert abs(transform[3][2] - 8) < 1e-7, transform
    assert all(
        abs(actual - expected) < 1e-7 for actual, expected in zip(transform[2][:3], (0, 0, 1))
    ), transform
    assert partial["revision"] == assembly["revision"] + 1

    invalid = plane_constraint("align", "z")
    invalid["assembly_reference"] = {"kind": "datum_plane", "id": 2147483647}
    failed = await probe.job(
        "creo_component_constraints",
        {**identity(partial), "component": component_label, "constraints": [invalid]},
        "bug036_invalid_reference",
        expected_failure=True,
    )
    failure = failed["result"]["failed_operation"]
    assert failure["constraint_stage"] == "reference", failure
    assert failure["failed_constraint_index"] == 0, failure
    assert failed["result"]["rollback_succeeded"] is True
    restored = await probe.job(
        "creo_refresh_model", {"model_id": partial["model_id"]}, "bug036_invalid_reference_rollback"
    )
    again = restored["result"]["inspection"]["components"][-1]
    assert again["constraints"] == member["constraints"]
    close_matrix(again["transform"], member["transform"])
    assert restored["revision"] == partial["revision"]


async def seeds(probe: Probe) -> None:
    for interpolation in ("straight", "smooth"):
        result = await probe.job(
            "creo_new_loft_part",
            {
                "sections": circle_sections(),
                "interpolation": interpolation,
                "label": "seed_blend",
            },
            "seed_" + interpolation,
        )
        evidence = result["result"]["seed_load_evidence"]
        assert evidence["status"] == "loaded" and evidence["evidence_persisted"]
        assert evidence["creo_release_numeric"] > 0
        value = await probe.call("creo_validate_seed", {"seed_name": "two_" + interpolation})
        assert value["available"]
        assert value["native_compatibility"]["status"] == "not_verified_for_current_session"
        # The registry keeps a bounded history (newest two by record-name order),
        # so this run's job may legitimately fall outside it; the load proof for
        # this run is the job's own seed_load_evidence above. When present, an
        # observation row for this job must show the loaded status.
        observations = value["native_compatibility"]["observations"]
        assert observations, value
        assert all(
            row["status"] in ("loaded", "load_failed") and row["seed_sha256"]
            for row in observations
        ), observations
        assert all(
            row["status"] == "loaded" for row in observations if row["job_id"] == result["job_id"]
        )
        if interpolation == "straight":
            summary = inspection_refs.summary_of(result["result"])
            assert abs(summary["volume_mm3"] - 4900 * math.pi / 3) < 0.01


async def rounds(probe: Probe) -> None:
    for kind, field, value in (("round", "radius", 2), ("chamfer", "distance", 1)):
        for mode in ("tool", "plan_size", "plan_alias"):
            base = await probe.job(
                "creo_execute_plan", {"operations": box()}, f"{kind}_{mode}_base"
            )
            edge = base["result"]["inspection"]["edges"][0]["id"]
            inputs = {
                "label": "finish",
                "references": [{"edge": {"kind": "edge", "id": edge}}],
            }
            size_field = "size" if mode == "plan_size" else field
            if mode != "tool":
                result = await probe.job(
                    "creo_execute_plan",
                    {
                        **identity(base),
                        "operations": [{"op": kind, **inputs, size_field: value}],
                    },
                    f"{kind}_{mode}",
                )
            else:
                result = await probe.job(
                    "creo_" + kind, {**identity(base), **inputs, field: value}, kind + "_tool"
                )
            operation = result["result"]["operations"][-1]
            assert operation["size"] == value
            compact = await probe.call(
                "creo_get_job", {"job_id": result["job_id"], "detail": "compact"}
            )
            assert compact["result"]["operations"][-1]["size"] == value
            fid = result["result"]["aliases"]["finish"]["feature_id"]
            feature = next(f for f in result["result"]["inspection"]["features"] if f["id"] == fid)
            assert any(abs(d["value"] - value) < 1e-7 for d in feature["dimensions"])
            other_alias = "distance" if kind == "round" else "radius"
            for invalid, message in (
                ({"size": value, field: value}, "not both"),
                ({other_alias: value}, "does not accept"),
            ):
                await probe.call(
                    "creo_execute_plan",
                    {
                        **identity(result),
                        "operations": [
                            {"op": kind, **inputs, "label": "invalid_finish", **invalid}
                        ],
                    },
                    expect_error=True,
                )
                error_text = " ".join(
                    item.get("text", "") for item in probe.report["calls"][-1]["raw_error"]
                )
                assert message in error_text, error_text
            unchanged = await probe.job(
                "creo_refresh_model", {"model_id": result["model_id"]}, kind + "_after_conflict"
            )
            assert unchanged["revision"] == result["revision"]
            assert (
                abs(
                    unchanged["result"]["inspection"]["volume_mm3"]
                    - result["result"]["inspection"]["volume_mm3"]
                )
                < 0.01
            )


async def run(args: argparse.Namespace) -> bool:
    fingerprint_files = (
        "bridge.py",
        "src/creo_mechdog/bridge.py",
        "src/creo_mechdog/generic_bridge.py",
        "server.py",
        "src/creo_mechdog/server.py",
        "src/creo_mechdog/schema.py",
        "src/creo_mechdog/seed_compatibility.py",
        "native/advanced.cpp",
        "native/generic.cpp",
        "native/loft_seed.cpp",
        "native/component_transform.h",
        "native/constraint_placement.h",
        "native/assembly_pose.h",
        "tools/test_feedback037_modeling.py",
    )
    report = {
        "work_items": ["BUG-036", "FEAT-030", "BUG-019"],
        "source": git_state(ROOT),
        "source_fingerprints": {name: source_hash(ROOT / name) for name in fingerprint_files},
        "started_at": datetime.now(timezone.utc).isoformat(),
        "calls": [],
        "jobs": [],
        "success": False,
    }
    probe = None
    try:
        async with Client(
            StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT),
            read_timeout_seconds=130,
        ) as client:
            probe = Probe(client, report, args.output, 180)
            if args.retry:
                await probe.call("creo_startup_status", {"retry": True})
            await wait_for_startup(client, report, args.output)
            report["session"] = await probe.call("creo_session_status", {})
            for case in args.cases.split(","):
                await {
                    "components": components,
                    "constraint_baseline": constraint_baseline,
                    "constraint_guard": constraint_guard,
                    "constraint_offsets": constraint_offsets,
                    "seeds": seeds,
                    "rounds": rounds,
                }[case](probe)
            report["success"] = True
    except Exception as error:
        report["error"] = repr(error)
    finally:
        if probe:
            probe.save()
    return report["success"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default="components,seeds,rounds")
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "build/feedback037-modeling.json")
    raise SystemExit(0 if asyncio.run(run(parser.parse_args())) else 1)
