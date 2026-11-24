"""Live Creo 10 acceptance for 0.40.0 feedback fixes (BUG-179..182, FEAT-080..081).

Run after `bridge.py build` with an active Creo session:
    .\\.venv\\Scripts\\python.exe tools\\test_feedback0400_live.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bridge  # noqa: E402
import generic_bridge as general  # noqa: E402
from creo_mechdog.sketch_region_split import split_intersecting_entities  # noqa: E402

RUN_TAG = str(int(time.time()) % 100000)


def unique_name(prefix: str) -> str:
    return f"{prefix}_{RUN_TAG}"[:28]


def wait_job(job_id: str, timeout: float = 300.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = bridge.get_job(job_id)
        if job.get("status") in ("succeeded", "failed", "unknown_outcome", "cancelled"):
            if "result" not in job:
                raw_path = ROOT / "jobs" / job_id / "job.json"
                if raw_path.exists():
                    return json.loads(raw_path.read_text(encoding="utf-8"))
            return job
        time.sleep(0.5)
    raise TimeoutError(f"Job {job_id} did not finish within {timeout}s")


def run_ops(
    ops: list[dict],
    *,
    model_id: str | None = None,
    model_name: str | None = None,
    expected_revision: int | None = None,
    model_type: str = "part",
    allow_failure: bool = False,
) -> dict:
    rec = general.submit(
        ops,
        model_id=model_id,
        model_name=model_name,
        expected_revision=expected_revision,
        model_type=model_type,
    )
    job = wait_job(rec["job_id"])
    if not allow_failure and job.get("status") != "succeeded":
        raise RuntimeError(
            f"Job {job['job_id']} failed unexpectedly: {job.get('message')} | "
            f"{json.dumps(job.get('result', {}).get('failed_operation'), ensure_ascii=False)}"
        )
    return job


def model_volume(model_id: str) -> float:
    return float(general.inspect_model(model_id, detail="compact")["inspection"]["volume_mm3"])


def scenario_s1_chamfer_propagate() -> dict:
    """BUG-179: compare chamfer propagate='single' vs 'chain' + created surface metrics."""

    def make_rounded_box(name: str) -> tuple[str, int, float]:
        j1 = run_ops(
            [
                {
                    "op": "sketch",
                    "label": "sk_box",
                    "plane": "XY",
                    "entities": [
                        {"type": "rectangle", "name": "r1", "min": [0, 0], "max": [100, 60]}
                    ],
                },
                {"op": "extrude", "label": "box", "sketch": "sk_box", "depth": 40, "mode": "add"},
            ],
            model_name=name,
        )
        j2 = run_ops(
            [
                {
                    "op": "round",
                    "label": "v_round",
                    "size": 10,
                    "references": [
                        {
                            "edge": {
                                "kind": "geometry_selector",
                                "target": "edge",
                                "tolerance_mm": 0.1,
                                "endpoints_mm": [[100, 0, 0], [100, 0, 40]],
                            }
                        }
                    ],
                }
            ],
            model_id=j1["model_id"],
            expected_revision=j1["revision"],
        )
        return j1["model_id"], j2["revision"], model_volume(j1["model_id"])

    mid_s, rev_s, vol_s0 = make_rounded_box(unique_name("a40_chm_s"))
    js = run_ops(
        [
            {
                "op": "chamfer",
                "label": "chm_s",
                "size": 3,
                "propagate": "single",
                "references": [
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "tolerance_mm": 0.1,
                            "endpoints_mm": [[0, 0, 40], [90, 0, 40]],
                        }
                    }
                ],
            }
        ],
        model_id=mid_s,
        expected_revision=rev_s,
    )
    op_s = js["result"]["operations"][0]
    assert js["result"]["saved_file_reloaded_and_verified"] is True
    assert op_s["created_surface_count"] >= 1
    assert op_s["created_surface_area_mm2"] > 0
    assert op_s["chamfered_edge_length_mm"] > 85.0

    mid_c, rev_c, vol_c0 = make_rounded_box(unique_name("a40_chm_c"))
    jc = run_ops(
        [
            {
                "op": "chamfer",
                "label": "chm_c",
                "size": 3,
                "propagate": "chain",
                "references": [
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "tolerance_mm": 0.1,
                            "endpoints_mm": [[0, 0, 40], [90, 0, 40]],
                        }
                    }
                ],
            }
        ],
        model_id=mid_c,
        expected_revision=rev_c,
    )
    op_c = jc["result"]["operations"][0]
    assert jc["result"]["saved_file_reloaded_and_verified"] is True
    assert op_c["created_surface_count"] > op_s["created_surface_count"], (op_s, op_c)
    assert abs(op_c["material_delta_mm3"]) > abs(op_s["material_delta_mm3"]) + 150.0, (op_s, op_c)

    return {
        "passed": True,
        "single_job": js["job_id"],
        "single_surface_count": op_s["created_surface_count"],
        "single_chamfered_edge_length_mm": op_s["chamfered_edge_length_mm"],
        "single_delta_mm3": op_s["material_delta_mm3"],
        "chain_job": jc["job_id"],
        "chain_surface_count": op_c["created_surface_count"],
        "chain_chamfered_edge_length_mm": op_c["chamfered_edge_length_mm"],
        "chain_delta_mm3": op_c["material_delta_mm3"],
    }


def scenario_s2_round_g2_concave_and_failure() -> dict:
    """BUG-180 + FEAT-081: G2 curvature verification, concave round_kind, and failure edge_diagnostics."""
    j1 = run_ops(
        [
            {
                "op": "sketch",
                "label": "sk_base",
                "plane": "XY",
                "entities": [{"type": "rectangle", "name": "r1", "min": [0, 0], "max": [100, 80]}],
            },
            {"op": "extrude", "label": "base", "sketch": "sk_base", "depth": 40, "mode": "add"},
        ],
        model_name=unique_name("a40_rnd_g2"),
    )
    mid, rev = j1["model_id"], j1["revision"]

    # G2 convex round on vertical edge (100, 0, 0..40)
    jg2 = run_ops(
        [
            {
                "op": "round",
                "label": "rnd_g2",
                "size": 10,
                "curvature_continuous": True,
                "references": [
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "tolerance_mm": 0.1,
                            "endpoints_mm": [[100, 0, 0], [100, 0, 40]],
                        }
                    }
                ],
            }
        ],
        model_id=mid,
        expected_revision=rev,
    )
    op_g2 = jg2["result"]["operations"][0]
    assert jg2["result"]["saved_file_reloaded_and_verified"] is True
    assert op_g2["round_kind"] == "convex", op_g2
    assert op_g2["volume_delta_mm3"] < 0, op_g2
    g2v = op_g2["g2_verification"]
    assert g2v["verdict"] == "pass", g2v
    assert g2v["native_conic_type"] == 3, g2v
    assert g2v["sampled_points"] > 0, g2v
    assert g2v["max_curvature_gap_inv_mm"] <= g2v["tolerance_inv_mm"], g2v
    rev = jg2["revision"]

    # Add step boss and round concave root edge
    jstep = run_ops(
        [
            {
                "op": "sketch",
                "label": "sk_step",
                "plane": "XY",
                "offset": 40,
                "entities": [{"type": "rectangle", "name": "r2", "min": [0, 0], "max": [40, 80]}],
            },
            {"op": "extrude", "label": "step", "sketch": "sk_step", "depth": 30, "mode": "add"},
            {
                "op": "round",
                "label": "rnd_concave",
                "size": 5,
                "references": [
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "tolerance_mm": 0.1,
                            "endpoints_mm": [[40, 0, 40], [40, 80, 40]],
                        }
                    }
                ],
            },
        ],
        model_id=mid,
        expected_revision=rev,
    )
    op_cc = jstep["result"]["operations"][2]
    assert jstep["result"]["saved_file_reloaded_and_verified"] is True
    assert op_cc["round_kind"] == "concave", op_cc
    assert op_cc["volume_delta_mm3"] > 0, op_cc
    rev = jstep["revision"]

    # Single-edge round failure -> round_failure.edge_diagnostics
    jfail = run_ops(
        [
            {
                "op": "round",
                "label": "rnd_too_big",
                "size": 999,
                "references": [
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "tolerance_mm": 0.1,
                            "endpoints_mm": [[0, 0, 0], [0, 0, 70]],
                        }
                    }
                ],
            }
        ],
        model_id=mid,
        expected_revision=rev,
        allow_failure=True,
    )
    assert jfail["status"] == "failed", jfail
    op_fail = jfail["result"]["operations"][0]
    rf = op_fail.get("round_failure") or {}
    ediags = rf.get("edge_diagnostics") or []
    assert len(ediags) == 1, rf
    assert len(ediags[0].get("adjacent_surfaces") or []) == 2, ediags[0]
    assert "dihedral_angle_deg" in ediags[0], ediags[0]
    assert "start_vertex" in ediags[0] and "end_vertex" in ediags[0], ediags[0]

    return {
        "passed": True,
        "g2_job": jg2["job_id"],
        "g2_verification": g2v,
        "concave_job": jstep["job_id"],
        "concave_round_kind": op_cc["round_kind"],
        "concave_volume_delta_mm3": op_cc["volume_delta_mm3"],
        "failure_job": jfail["job_id"],
        "failure_edge_diagnostic": ediags[0],
    }


def scenario_s3_shell_body_id_and_inspect_total_count() -> dict:
    """FEAT-080: shell only body B in a 2-body part + verify inspect total_count/page_count."""
    j1 = run_ops(
        [
            {
                "op": "sketch",
                "label": "sk_a",
                "plane": "XY",
                "entities": [{"type": "rectangle", "name": "ra", "min": [0, 0], "max": [40, 40]}],
            },
            {"op": "extrude", "label": "body_a", "sketch": "sk_a", "depth": 40, "mode": "add"},
            {
                "op": "sketch",
                "label": "sk_b",
                "plane": "XY",
                "entities": [{"type": "rectangle", "name": "rb", "min": [60, 0], "max": [100, 40]}],
            },
            {
                "op": "extrude",
                "label": "body_b",
                "sketch": "sk_b",
                "depth": 40,
                "mode": "add",
                "new_body": True,
            },
        ],
        model_name=unique_name("a40_shl_b"),
    )
    mid, rev = j1["model_id"], j1["revision"]
    insp = general.inspect_model(mid, detail="compact")["inspection"]
    bodies = general.inspect_model(mid, detail="full", section="bodies")["data"]["bodies"]
    assert len(bodies) == 2, bodies
    # Body B is the second (newly created) body
    body_b_id = bodies[-1]["id"]

    # Check paginated inspect total_count & page_count
    page1 = general.inspect_model(mid, detail="full", section="edges", limit=5)
    assert page1["total_count"] == insp["counts"]["edges"], page1
    assert page1["page_count"] == 5 and page1["returned_count"] == 5, page1

    # Shell ONLY Body B (thickness 2, remove top face at X=80,Y=20,Z=40)
    jsh = run_ops(
        [
            {
                "op": "shell",
                "label": "shell_b",
                "thickness": 2.0,
                "body_id": body_b_id,
                "remove_surfaces": [
                    {
                        "kind": "geometry_selector",
                        "target": "surface",
                        "tolerance_mm": 0.1,
                        "axis": [0, 0, 1],
                        "points_mm": [[80, 20, 40]],
                    }
                ],
            }
        ],
        model_id=mid,
        expected_revision=rev,
    )
    assert jsh["result"]["saved_file_reloaded_and_verified"] is True
    vol_after = model_volume(mid)
    expected_vol = 64000.0 + (64000.0 - 36.0 * 36.0 * 38.0)  # 78752.0 mm^3
    assert abs(vol_after - expected_vol) < 1e-2, (vol_after, expected_vol)
    op_sh = jsh["result"]["operations"][0]
    assert op_sh["body_id"] == body_b_id, op_sh

    return {
        "passed": True,
        "shell_job": jsh["job_id"],
        "body_b_id": body_b_id,
        "volume_after_mm3": vol_after,
        "expected_volume_mm3": expected_vol,
        "inspect_total_count": page1["total_count"],
        "inspect_page_count": page1["page_count"],
    }


def scenario_s4_region_cut_bspline_split() -> dict:
    """BUG-181: cut one sub-region from a multi-region B-spline+line sketch on YZ."""
    bs1 = {
        "type": "b_spline",
        "name": "bs1",
        "degree": 3,
        "control_points": [[10.0, -2.0], [11.0, 3.0], [9.0, 7.0], [10.0, 12.0]],
        "approximation_segments": 12,
    }
    bs2 = {
        "type": "b_spline",
        "name": "bs2",
        "degree": 3,
        "control_points": [[20.0, -2.0], [21.0, 3.0], [19.0, 7.0], [20.0, 12.0]],
        "approximation_segments": 12,
    }
    region_sketch = {
        "op": "sketch",
        "label": "arm7_s7",
        "plane": "YZ",
        "offset": 0.0,
        "entities": [
            {"type": "line", "name": "bot", "start": [0.0, 0.0], "end": [30.0, 0.0]},
            {"type": "line", "name": "right", "start": [30.0, 0.0], "end": [30.0, 10.0]},
            {"type": "line", "name": "top", "start": [30.0, 10.0], "end": [0.0, 10.0]},
            {"type": "line", "name": "left", "start": [0.0, 10.0], "end": [0.0, 0.0]},
            bs1,
            bs2,
        ],
    }
    pieces, did_split = split_intersecting_entities(region_sketch["entities"])
    assert did_split
    bs1_mid = next(
        p
        for p in pieces
        if p["name"].startswith("bs1_s")
        and abs(p["control_points"][0][1] - 0.0) < 1e-3
        and abs(p["control_points"][-1][1] - 10.0) < 1e-3
    )
    x1_bot = bs1_mid["control_points"][0][0]
    x1_top = bs1_mid["control_points"][-1][0]
    sig_left = f"(0,0|{x1_bot:.6f},0;{x1_bot:.6f},0|{x1_top:.6f},10;{x1_top:.6f},10|0,10;0,10|0,0)"

    j1 = run_ops(
        [
            {
                "op": "sketch",
                "label": "sk_blk",
                "plane": "YZ",
                "offset": 0.0,
                "entities": [{"type": "rectangle", "name": "rb", "min": [0, 0], "max": [30, 10]}],
            },
            {"op": "extrude", "label": "blk", "sketch": "sk_blk", "depth": 10.0, "mode": "add"},
        ],
        model_name=unique_name("a40_reg_bs"),
    )
    vol_before = model_volume(j1["model_id"])
    j2 = run_ops(
        [
            region_sketch,
            {
                "op": "extrude",
                "label": "cut_r0",
                "sketch": "arm7_s7",
                "region": {"signature_yz_mm": sig_left, "tolerance_mm": 0.01},
                "mode": "cut",
                "depth": 3.0,
            },
        ],
        model_id=j1["model_id"],
        expected_revision=j1["revision"],
    )
    assert j2["result"]["saved_file_reloaded_and_verified"] is True
    vol_after = model_volume(j1["model_id"])
    removed = vol_before - vol_after
    # Expected ~ 10 * 10 * 3 = 300 mm^3 (curved B-spline shifts area slightly)
    assert 250.0 < removed < 350.0, (vol_before, vol_after, removed)

    return {
        "passed": True,
        "region_cut_job": j2["job_id"],
        "volume_before_mm3": vol_before,
        "volume_after_mm3": vol_after,
        "removed_mm3": removed,
    }


def scenario_s5_assembly_selector_suggested_ref() -> dict:
    """BUG-182: assembly coordinate_space zero-match returns suggested_reference & assembly_origin_mm."""
    j_plate = run_ops(
        [
            {
                "op": "sketch",
                "label": "sk_p",
                "plane": "XY",
                "entities": [{"type": "rectangle", "name": "rp", "min": [0, 0], "max": [40, 40]}],
            },
            {"op": "extrude", "label": "plate", "sketch": "sk_p", "depth": 10, "mode": "add"},
        ],
        model_name=unique_name("a40_plate"),
    )
    plate_id = j_plate["model_id"]

    j_asm = run_ops(
        [
            {
                "op": "assemble_component",
                "label": "plate_1",
                "source_model_id": plate_id,
                "translation": [100.0, 0.0, 0.0],
            }
        ],
        model_name=unique_name("a40_asm"),
        model_type="assembly",
    )
    asm_id, asm_rev = j_asm["model_id"], j_asm["revision"]

    # Deliberately off by 0.254 mm in assembly Z (plane is at Z=10, pass Z=10.254)
    j_fail = run_ops(
        [
            {
                "op": "assemble_component",
                "label": "plate_2",
                "source_model_id": plate_id,
                "placement": "constraints",
                "constraints": [
                    {
                        "type": "mate",
                        "component_reference": {
                            "kind": "geometry_selector",
                            "target": "surface",
                            "tolerance_mm": 0.01,
                            "axis": [0, 0, 1],
                            "points_mm": [[20, 20, 0]],
                        },
                        "assembly_component": "plate_1",
                        "assembly_reference": {
                            "kind": "geometry_selector",
                            "target": "surface",
                            "coordinate_space": "assembly",
                            "tolerance_mm": 0.001,
                            "axis": [0, 0, 1],
                            "points_mm": [[120, 20, 10.254]],
                        },
                    }
                ],
            }
        ],
        model_id=asm_id,
        expected_revision=asm_rev,
        allow_failure=True,
    )
    assert j_fail["status"] == "failed", j_fail
    op_f = j_fail["result"]["operations"][0]
    diag = op_f["geometry_selector_diagnostic"]
    assert diag["requested_coordinate_space"] == "assembly", diag
    assert diag["nearest_coordinate_space"] == "component", diag
    top = diag["nearest_surfaces"][0]
    assert top["suggested_reference"] == {"kind": "surface", "id": top["id"]}, top
    assert "assembly_origin_mm" in top and "assembly_normal" in top, top
    assert "Closest candidate: {kind:'surface',id:" in j_fail.get("message", ""), j_fail.get(
        "message"
    )

    return {
        "passed": True,
        "fail_job": j_fail["job_id"],
        "top_nearest_surface": top,
        "message_excerpt": j_fail.get("message", "")[:260],
    }


def main() -> int:
    st = bridge.session_status()
    if not st.get("connected"):
        raise RuntimeError(f"Creo session not connected: {st}")
    report = {
        "creo_release_numeric": st.get("release_numeric"),
        "scenarios": {},
    }
    for name, fn in [
        ("S1_chamfer_propagate", scenario_s1_chamfer_propagate),
        ("S2_round_g2_concave_failure", scenario_s2_round_g2_concave_and_failure),
        ("S3_shell_body_id_inspect_total", scenario_s3_shell_body_id_and_inspect_total_count),
        ("S4_region_cut_bspline_split", scenario_s4_region_cut_bspline_split),
        ("S5_assembly_selector_suggested_ref", scenario_s5_assembly_selector_suggested_ref),
    ]:
        print(f"Running {name}...", flush=True)
        res = fn()
        report["scenarios"][name] = res
        print(f"  PASS {name}", flush=True)
    out_path = ROOT / "build" / "feedback0400_live_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ALL 5 LIVE SCENARIOS PASSED -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
