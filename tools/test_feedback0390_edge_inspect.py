"""Live Creo acceptance for 0.39.0 feedback fixes (BUG-176/177/178, FEAT-078/079).

Run after `bridge.py build` with an active Creo session:
    .\\.venv\\Scripts\\python.exe tools\\test_feedback0390_edge_inspect.py
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bridge  # noqa: E402
import generic_bridge as general  # noqa: E402


def wait_job(job_id: str, timeout: float = 300.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = bridge.get_job(job_id)
        if job.get("status") in ("succeeded", "failed", "unknown_outcome", "cancelled"):
            return job
        time.sleep(0.5)
    raise TimeoutError(f"Job {job_id} did not finish within {timeout}s")


def ensure_creo_ready(timeout: float = 120.0) -> dict:
    deadline = time.monotonic() + timeout
    last = {}
    while time.monotonic() < deadline:
        last = bridge.session_status()
        if last.get("connected"):
            return last
        time.sleep(2.0)
    raise TimeoutError(f"Timed out waiting for Creo session_status connected: {last}")


def model_volume(model_id: str) -> float:
    return float(general.inspect_model(model_id, detail="compact")["inspection"]["volume_mm3"])


def submit_and_wait(
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
            f"Job {rec['job_id']} failed unexpectedly: {json.dumps(job, ensure_ascii=False)[:1200]}"
        )
    return job


def main() -> int:
    session = ensure_creo_ready()
    report: dict = {
        "session": {
            "connected": session.get("connected"),
            "creo_release_numeric": session.get("creo_release_numeric"),
            "toolkit_code": session.get("toolkit_code"),
        },
        "scenarios": {},
    }

    # --- S1: BUG-176 (full_circle, seam point_mm, single point_mm on arc) + FEAT-078 (part area/bbox/merged_counts) ---
    cyl_ops = [
        {
            "op": "sketch",
            "label": "sk_cyl",
            "plane": "XY",
            "offset": 0,
            "entities": [{"type": "circle", "name": "c0", "center": [0, 0], "radius": 20}],
        },
        {
            "op": "extrude",
            "label": "ext_cyl",
            "sketch": "sk_cyl",
            "depth": 40,
            "mode": "add",
            "direction": "positive",
        },
    ]
    j_cyl = submit_and_wait(cyl_ops, model_name="fb0390_cyl_s1")
    mid_cyl = j_cyl["model_id"]
    rev_cyl = j_cyl["revision"]
    insp_compact = general.inspect_model(mid_cyl, detail="compact")
    insp_full = general.inspect_model(mid_cyl, detail="full", section="surfaces", limit=50)
    summary = insp_compact["inspection"]

    expected_vol = math.pi * 20.0 * 20.0 * 40.0
    expected_area = 2.0 * math.pi * 20.0 * 40.0 + 2.0 * math.pi * 20.0 * 20.0
    assert abs(summary["volume_mm3"] - expected_vol) < 0.5, summary
    assert abs(summary["total_surface_area_mm2"] - expected_area) < 0.5, summary
    bbox = summary["bounding_box_mm"]
    assert (
        bbox is not None
        and abs(bbox["size"][0] - 40.0) < 0.05
        and abs(bbox["size"][2] - 40.0) < 0.05
    ), bbox
    assert summary["merged_counts"]["cylindrical_face_groups"] == 1, summary["merged_counts"]
    assert summary["merged_counts"]["surfaces"] == 3, summary["merged_counts"]
    assert summary["merged_counts"]["circular_edge_groups"] == 2, summary["merged_counts"]
    surf_areas = [s.get("area_mm2") for s in insp_full["data"]["surfaces"]]
    assert all(isinstance(a, (int, float)) and a > 0 for a in surf_areas), surf_areas
    assert abs(sum(surf_areas) - expected_area) < 0.5, (sum(surf_areas), expected_area)

    # S1a: full_circle: true on top rim (z=40, R=20)
    j_rnd_fc = submit_and_wait(
        [
            {
                "op": "round",
                "label": "rnd_top_fc",
                "size": 2.0,
                "references": [
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "center_mm": [0, 0, 40],
                            "radius_mm": 20,
                            "axis": [0, 0, 1],
                            "full_circle": True,
                            "tolerance_mm": 0.1,
                        }
                    }
                ],
            }
        ],
        model_id=mid_cyl,
        expected_revision=rev_cyl,
    )
    rev_cyl = j_rnd_fc["revision"]
    assert j_rnd_fc["result"]["saved_file_reloaded_and_verified"] is True
    vol_after_fc = model_volume(mid_cyl)
    assert vol_after_fc < expected_vol - 50.0, (vol_after_fc, expected_vol)

    # S1b: seam/extremum point_mm [20, 0, 0] on bottom circular rim (z=0, R=20)
    j_chm_seam = submit_and_wait(
        [
            {
                "op": "chamfer",
                "label": "chm_bot_seam",
                "size": 2.0,
                "references": [
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "center_mm": [0, 0, 0],
                            "radius_mm": 20,
                            "point_mm": [20, 0, 0],
                            "tolerance_mm": 0.1,
                        }
                    }
                ],
            }
        ],
        model_id=mid_cyl,
        expected_revision=rev_cyl,
    )
    rev_cyl = j_chm_seam["revision"]
    assert j_chm_seam["result"]["saved_file_reloaded_and_verified"] is True
    vol_after_seam = model_volume(mid_cyl)
    assert vol_after_seam < vol_after_fc - 100.0, (vol_after_seam, vol_after_fc)

    # S1c: single point_mm [15, 0, 30] (no center_mm/radius_mm!) on a cylinder rim
    j_cyl2 = submit_and_wait(
        [
            {
                "op": "sketch",
                "label": "sk_c2",
                "plane": "XY",
                "offset": 0,
                "entities": [{"type": "circle", "name": "c0", "center": [0, 0], "radius": 15}],
            },
            {
                "op": "extrude",
                "label": "ext_c2",
                "sketch": "sk_c2",
                "depth": 30,
                "mode": "add",
                "direction": "positive",
            },
            {
                "op": "chamfer",
                "label": "chm_pt_arc",
                "size": 1.5,
                "references": [
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "point_mm": [15, 0, 30],
                            "tolerance_mm": 0.1,
                        }
                    }
                ],
            },
        ],
        model_name="fb0390_pt_arc_s1c",
    )
    assert j_cyl2["result"]["saved_file_reloaded_and_verified"] is True
    vol_c2_raw = math.pi * 15.0 * 15.0 * 30.0
    vol_c2_after = model_volume(j_cyl2["model_id"])
    assert vol_c2_after < vol_c2_raw - 50.0

    report["scenarios"]["S1_full_circle_seam_point_arc_and_area_bbox"] = {
        "passed": True,
        "part_model_id": mid_cyl,
        "initial_volume_mm3": summary["volume_mm3"],
        "initial_total_surface_area_mm2": summary["total_surface_area_mm2"],
        "surface_area_sum_mm2": sum(surf_areas),
        "bounding_box_mm": bbox,
        "merged_counts": summary["merged_counts"],
        "after_full_circle_round_volume_mm3": vol_after_fc,
        "after_seam_chamfer_volume_mm3": vol_after_seam,
        "single_point_arc_job_id": j_cyl2["job_id"],
        "single_point_arc_volume_mm3": vol_c2_after,
    }

    # --- S2: FEAT-079 multi-reference round failure localization ---
    # L-shaped stepped block: big step 40x20, tiny 2x2 lip on the right.
    # R10 fits cleanly on top-left edge ([0,0,20]-[0,30,20]), fails on the 2x2 lip ([42,0,2]-[42,30,2]).
    j_step = submit_and_wait(
        [
            {
                "op": "sketch",
                "label": "sk_step",
                "plane": "XZ",
                "offset": 0,
                "entities": [
                    {
                        "type": "polyline",
                        "name": "p",
                        "points": [[0, 0], [42, 0], [42, 2], [40, 2], [40, 20], [0, 20]],
                        "closed": True,
                    }
                ],
            },
            {
                "op": "extrude",
                "label": "ext_step",
                "sketch": "sk_step",
                "depth": 30,
                "mode": "add",
                "direction": "negative",
            },
        ],
        model_name="fb0390_round_loc_s2",
    )
    mid_step = j_step["model_id"]
    rev_step = j_step["revision"]
    vol_step_before = model_volume(mid_step)
    j_rnd_fail = submit_and_wait(
        [
            {
                "op": "chamfer",
                "label": "chm_multi_fail",
                "size": 10.0,
                "references": [
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "endpoints_mm": [[0, 0, 20], [0, 30, 20]],
                            "tolerance_mm": 0.1,
                        }
                    },
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "endpoints_mm": [[42, 0, 2], [42, 30, 2]],
                            "tolerance_mm": 0.1,
                        }
                    },
                ],
            }
        ],
        model_id=mid_step,
        expected_revision=rev_step,
        allow_failure=True,
    )
    assert j_rnd_fail["status"] == "failed", j_rnd_fail
    assert j_rnd_fail["result"].get("rollback_succeeded") is True, j_rnd_fail["result"]
    op0 = j_rnd_fail["result"]["operations"][0]
    assert op0.get("failed_reference_index") == 1, op0
    assert op0.get("round_failure", {}).get("failed_indices") == [1], op0
    insp_step_after = general.inspect_model(mid_step, detail="compact")["inspection"]
    assert abs(insp_step_after["volume_mm3"] - vol_step_before) < 0.01

    report["scenarios"]["S2_multi_set_round_failure_localization"] = {
        "passed": True,
        "job_id": j_rnd_fail["job_id"],
        "failed_reference_index": op0.get("failed_reference_index"),
        "round_failure": op0.get("round_failure"),
        "rollback_succeeded": j_rnd_fail["result"].get("rollback_succeeded"),
    }

    # --- S3: BUG-177 (major arc sweep_deg=270) + BUG-178 (feature_state include_dependencies=true) ---
    j_arc = submit_and_wait(
        [
            {
                "op": "sketch",
                "label": "sk_major",
                "plane": "XY",
                "offset": 0,
                "entities": [
                    {
                        "type": "arc",
                        "name": "a_major",
                        "center": [0, 0],
                        "radius": 20,
                        "start_angle": 0,
                        "sweep_deg": 270,
                    },
                    {"type": "line", "name": "l1", "start": [0, -20], "end": [0, 0]},
                    {"type": "line", "name": "l2", "start": [0, 0], "end": [20, 0]},
                ],
            },
            {
                "op": "extrude",
                "label": "ext_major",
                "sketch": "sk_major",
                "depth": 10,
                "mode": "add",
                "direction": "positive",
            },
        ],
        model_name="fb0390_major_arc_s3",
    )
    mid_arc = j_arc["model_id"]
    rev_arc = j_arc["revision"]
    expected_major_vol = 0.75 * math.pi * 20.0 * 20.0 * 10.0
    vol_major = model_volume(mid_arc)
    assert abs(vol_major - expected_major_vol) < 0.5, (vol_major, expected_major_vol)

    # Add an offset cut (creates a datum plane + sketch + cut), then delete cut+sketch with include_dependencies=true
    j_cut = submit_and_wait(
        [
            {
                "op": "sketch",
                "label": "sk_cut",
                "plane": "XY",
                "offset": 10,
                "entities": [{"type": "rectangle", "name": "r", "min": [-15, 2], "max": [-5, 12]}],
            },
            {
                "op": "extrude",
                "label": "cut_top",
                "sketch": "sk_cut",
                "depth": 5,
                "mode": "cut",
                "direction": "negative",
            },
        ],
        model_id=mid_arc,
        expected_revision=rev_arc,
    )
    rev_arc = j_cut["revision"]
    assert abs(model_volume(mid_arc) - (expected_major_vol - 500.0)) < 0.5

    # First try deleting only sk_cut WITHOUT include_dependencies -> pre-dispatch rejects with suggested_targets!
    suggested_msg = ""
    try:
        general.submit(
            [{"op": "feature_state", "action": "delete", "targets": ["sk_cut"]}],
            model_id=mid_arc,
            expected_revision=rev_arc,
        )
        raise AssertionError("Expected pre-dispatch rejection without include_dependencies")
    except ValueError as exc:
        suggested_msg = str(exc)
        assert "suggested_targets=" in suggested_msg, suggested_msg

    # Now delete sk_cut WITH include_dependencies=true -> auto-includes cut_top (and companion datum) and succeeds!
    j_del_ok = submit_and_wait(
        [
            {
                "op": "feature_state",
                "action": "delete",
                "targets": ["sk_cut"],
                "include_dependencies": True,
            }
        ],
        model_id=mid_arc,
        expected_revision=rev_arc,
    )
    assert j_del_ok["result"]["saved_file_reloaded_and_verified"] is True
    vol_after_del = model_volume(mid_arc)
    assert abs(vol_after_del - expected_major_vol) < 0.5

    report["scenarios"]["S3_major_arc_sweep_and_feature_state_include_deps"] = {
        "passed": True,
        "major_arc_volume_mm3": vol_major,
        "expected_major_vol_mm3": expected_major_vol,
        "suggested_targets_message": suggested_msg,
        "delete_include_deps_job_id": j_del_ok["job_id"],
        "auto_included_dependencies": j_del_ok["result"]["operations"][0].get(
            "auto_included_dependencies"
        ),
        "volume_after_delete_mm3": vol_after_del,
    }

    # --- S4: FEAT-078 assembly area/bbox + BUG-178 component_changes noise ---
    j_asm_new = general.submit([], model_name="fb0390_asm_s4", model_type="assembly")
    j_asm_new = wait_job(j_asm_new["job_id"])
    assert j_asm_new["status"] == "succeeded", j_asm_new
    mid_asm = j_asm_new["model_id"]
    rev_asm = j_asm_new["revision"]

    j_asm1 = submit_and_wait(
        [
            {
                "op": "assemble_component",
                "label": "c1",
                "source_model_id": mid_cyl,
                "translation": [0, 0, 0],
            },
            {
                "op": "assemble_component",
                "label": "c2",
                "source_model_id": mid_cyl,
                "translation": [100, 0, 0],
            },
        ],
        model_id=mid_asm,
        expected_revision=rev_asm,
        model_type="assembly",
    )
    rev_asm = j_asm1["revision"]
    asm_insp = general.inspect_model(mid_asm, detail="compact")["inspection"]
    assert (
        asm_insp["total_surface_area_mm2"] is not None
        and asm_insp["total_surface_area_mm2"] > 10000.0
    ), asm_insp
    asm_bbox = asm_insp["bounding_box_mm"]
    assert asm_bbox is not None and abs(asm_bbox["size"][0] - 140.0) < 0.5, asm_bbox

    # Insert c3; verify c1 and c2 are NOT reported as 'moved'
    j_asm2 = submit_and_wait(
        [
            {
                "op": "assemble_component",
                "label": "c3",
                "source_model_id": mid_cyl,
                "translation": [0, 100, 0],
            }
        ],
        model_id=mid_asm,
        expected_revision=rev_asm,
        model_type="assembly",
    )
    assert j_asm2["result"]["saved_file_reloaded_and_verified"] is True
    comp_changes = j_asm2.get("component_changes") or {}
    ops_reported = [(c.get("label"), c.get("op")) for c in comp_changes.get("changes", [])]
    assert ops_reported == [("c3", "added")], ops_reported

    report["scenarios"]["S4_assembly_area_bbox_and_component_changes"] = {
        "passed": True,
        "assembly_model_id": mid_asm,
        "total_surface_area_mm2": asm_insp["total_surface_area_mm2"],
        "bounding_box_mm": asm_bbox,
        "third_insert_component_changes": comp_changes,
    }

    report["all_passed"] = True
    out_path = ROOT / "build" / "feedback0390_edge_inspect.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
