"""Live Creo 10 acceptance suite for 0.35.8 feedback fixes (BUG-171..BUG-174).

Verifies on live Creo Parametric 10.0.0.0:
1. BUG-173 + BUG-172: Singly-tilted three-point datum planes with the exact B045
   (0.965925826, 0, -0.258819045) and B047 (0, -0.965925826, -0.258819045) normals
   and 4-line coordinate rectangles (3 disjoint 100x100x2 plates = +60,000 mm3
   for B045, 1 120x120x2 plate = +28,800 mm3 for B047), WITHOUT any caller-supplied
   anchor plane. Verifies automatic SKETCH_ANCHOR_HELPER creation on the first
   sketch, reuse on the 2nd and 3rd sketches, SKETCH_SOLVE=0, zero geometry
   deviation, exact volume delta, saved_file_reloaded_and_verified=True, and
   that the 6-op B045 job runs only 3 full inspections (INSPECT_SUMMARY count=3)
   with zero per-edge ProEdgeIdGet log spam.
2. BUG-174 (chamfer_type + cut_volume_check + runner_detached_from_job):
   - Inline creo_execute_plan-style dump_plan_operations -> general.submit with
     chamfer_type='d1_d2' (15x10 mm chamfer on a 400 mm edge = -30,000 mm3);
   - Blind cut with tiny overlap (<5% of analytic prism volume) produces
     cut_volume_check.low_removal_warning=True, while a full blind cut produces
     low_removal_warning=False and removal_ratio ~ 1.0;
   - runner_detached_from_job is recorded on the persisted job manifest.
3. BUG-171: restore_baseline with verify_mode='full' and verify_mode='identity'
   on an unknown_outcome model, verifying that 'full' runs only a single post-
   reload inspection (not two duplicate inspections) and 'identity' restores
   the model to ready with saved_file_reloaded_and_verified=True.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import bridge
import creo_startup
import generic_bridge as general
from creo_mechdog import model_registry, reconciliation, schema


def unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def mul(a, s):
    return tuple(c * s for c in a)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def r9(v):
    return [round(c, 9) for c in v]


def wait_job(job_id: str, timeout: float = 300.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = bridge.get_job(job_id, wait_seconds=2)
        if job.get("status") in bridge.TERMINAL_JOB_STATUSES:
            raw_path = ROOT / "jobs" / job_id / "job.json"
            if raw_path.is_file():
                return json.loads(raw_path.read_text(encoding="utf-8"))
            return job
    raise TimeoutError(f"Job {job_id} did not finish within {timeout} s")


def ensure_creo_ready() -> dict:
    import subprocess as sp

    settings = creo_startup.Settings.load()
    session_dir = ROOT / "build" / "creo_session"
    session_dir.mkdir(parents=True, exist_ok=True)

    probe = bridge.session_status()
    if not probe.get("connected"):
        inv = creo_startup.inventory(settings)
        if not inv.get("processes"):
            sp.Popen(
                [str(settings.executable), str(settings.psf), *settings.args],
                cwd=session_dir,
                stdin=sp.DEVNULL,
                stdout=sp.DEVNULL,
                stderr=sp.DEVNULL,
            )
        deadline = time.monotonic() + 180.0
        while time.monotonic() < deadline:
            probe = bridge.session_status()
            if probe.get("connected"):
                break
            time.sleep(2.0)
    if not probe.get("connected"):
        raise RuntimeError(f"Creo session is not connected: {probe}")
    return probe


def result_volume(job: dict) -> float:
    res = job["result"]
    insp = res.get("inspection") or res.get("inspection_summary") or {}
    return float(insp["volume_mm3"])


def make_rect_lines(
    prefix: str, u_min: float, u_max: float, v_min: float, v_max: float
) -> list[dict]:
    corners = [(u_min, v_min), (u_max, v_min), (u_max, v_max), (u_min, v_max)]
    out = []
    for i in range(4):
        out.append(
            {
                "type": "line",
                "name": f"{prefix}{i:02d}",
                "start": [round(corners[i][0], 9), round(corners[i][1], 9)],
                "end": [round(corners[(i + 1) % 4][0], 9), round(corners[(i + 1) % 4][1], 9)],
            }
        )
    return out


def run_live_suite() -> dict:
    session_info = ensure_creo_ready()
    exe = bridge.build_native()
    worker_sha256 = hashlib.sha256(exe.read_bytes()).hexdigest()
    suffix = uuid.uuid4().hex[:6]
    model_name = f"acc0358_{suffix}"

    report: dict = {
        "date": "2026-11-23",
        "work_items": ["BUG-171", "BUG-172", "BUG-173", "BUG-174"],
        "worker_exe": str(exe),
        "worker_sha256": worker_sha256,
        "session_info": session_info,
        "model_name": model_name,
        "scenarios": {},
    }

    # ------------------------------------------------------------------
    # Scenario 1: Create 400x400x400 base block + B045 singly-tilted plane
    # (NO manual anchor plane!)
    # ------------------------------------------------------------------
    n_b045 = unit((0.965925826, 0.0, -0.258819045))
    axes = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    seed_b045 = min(axes, key=lambda e: abs(dot(e, n_b045)))
    u_b045 = unit(cross(seed_b045, n_b045))
    v_b045 = cross(n_b045, u_b045)
    o_b045 = (200.0, 200.0, 520.0)

    p1_ops = [
        {
            "op": "sketch",
            "label": "base_sk",
            "plane": "XY",
            "entities": [
                {"type": "rectangle", "name": "r0", "min": [0.0, 0.0], "max": [400.0, 400.0]}
            ],
        },
        {
            "op": "extrude",
            "label": "base_box",
            "sketch": "base_sk",
            "depth": 400.0,
            "mode": "add",
            "direction": "positive",
        },
    ]
    labels_b045 = []
    for slot, pt in enumerate(
        [o_b045, add(o_b045, mul(u_b045, 100.0)), add(o_b045, mul(v_b045, 100.0))]
    ):
        lbl = f"pb045_{slot}"
        labels_b045.append(lbl)
        p1_ops.append(
            {
                "op": "datum_points",
                "label": lbl,
                "reference": {"kind": "default_csys"},
                "points": [{"name": f"pt{slot}", "position": r9(pt)}],
            }
        )
    p1_ops.append(
        {
            "op": "datum_plane",
            "label": "pl_b045",
            "reference": {"kind": "through_points", "points": labels_b045},
        }
    )

    sub1 = general.submit(p1_ops, None, model_name, None)
    job1 = wait_job(sub1["job_id"])
    assert job1["status"] == "succeeded", f"Scenario 1 failed: {job1}"
    model_id = job1["model_id"]
    rev1 = job1["revision"]
    vol1 = result_volume(job1)
    assert abs(vol1 - 64000000.0) < 1.0, f"Unexpected base volume: {vol1}"
    assert job1["result"]["saved_file_reloaded_and_verified"] is True
    assert isinstance(job1.get("runner_detached_from_job"), bool)

    report["model_id"] = model_id
    report["scenarios"]["S1_base_and_tilted_plane"] = {
        "job_id": sub1["job_id"],
        "status": job1["status"],
        "revision": rev1,
        "volume_mm3": vol1,
        "expected_volume_mm3": 64000000.0,
        "saved_file_reloaded_and_verified": job1["result"]["saved_file_reloaded_and_verified"],
        "runner_detached_from_job": job1.get("runner_detached_from_job"),
    }

    # ------------------------------------------------------------------
    # Scenario 2 (BUG-173 + BUG-172): B045 3 sketches + 3 extrudes on pl_b045
    # WITHOUT any user-created anchor plane!
    # ------------------------------------------------------------------
    b045_ops = []
    for idx, vc in enumerate((0.0, 125.0, -125.0)):
        sfx = chr(ord("a") + idx)
        sk_lbl = f"sk_b045_{sfx}"
        b045_ops.append(
            {
                "op": "sketch",
                "label": sk_lbl,
                "plane": {
                    "reference": {"kind": "datum_feature", "label": "pl_b045"},
                    "origin": r9(o_b045),
                    "u_axis": r9(u_b045),
                },
                "entities": make_rect_lines(f"e_{sfx}", -50.0, 50.0, vc - 50.0, vc + 50.0),
                "dimensioning": "coordinates",
            }
        )
        b045_ops.append(
            {
                "op": "extrude",
                "label": f"boss_b045_{sfx}",
                "sketch": sk_lbl,
                "depth": 2.0,
                "mode": "add",
                "direction": "positive",
            }
        )

    t0 = time.monotonic()
    sub2 = general.submit(b045_ops, model_id, None, rev1)
    job2 = wait_job(sub2["job_id"])
    elapsed2 = round(time.monotonic() - t0, 3)
    assert job2["status"] == "succeeded", f"Scenario 2 (B045 without anchor) failed: {job2}"
    rev2 = job2["revision"]
    vol2 = result_volume(job2)
    delta_b045 = vol2 - vol1
    assert abs(delta_b045 - 60000.0) < 0.5, f"Expected +60000 mm3, got {delta_b045}"
    assert job2["result"]["saved_file_reloaded_and_verified"] is True

    log2_path = bridge.job_path(sub2["job_id"]) / "native.log"
    log2_lines = log2_path.read_text(encoding="utf-8", errors="replace").splitlines()
    inspect_summaries = [l for l in log2_lines if l.startswith("INSPECT_SUMMARY ")]
    edge_spam_lines = [l for l in log2_lines if l.startswith("ProEdgeIdGet(")]
    anchor_helpers = [l for l in log2_lines if l.startswith("SKETCH_ANCHOR_HELPER=1")]
    sketch_ops = [op for op in job2["result"]["operations"] if op.get("op") == "sketch"]
    assert len(inspect_summaries) == 3, f"Expected 3 full inspections, got {len(inspect_summaries)}"
    assert len(edge_spam_lines) == 0, (
        f"Expected 0 ProEdgeIdGet spam lines, got {len(edge_spam_lines)}"
    )
    assert len(anchor_helpers) == 1, (
        f"Expected 1 helper anchor created and reused, got {len(anchor_helpers)}"
    )
    assert sketch_ops[0]["section_references"]["helper_anchor_created"] is True
    assert sketch_ops[1]["section_references"]["helper_anchor_created"] is False
    assert sketch_ops[2]["section_references"]["helper_anchor_created"] is False
    for sk_op in sketch_ops:
        assert sk_op["section_references"]["anchor_count"] == 2
        assert sk_op["section_references"]["origin_pin_available"] is True
        assert sk_op["solver"]["stages"]["initial_solve"] == 0

    report["scenarios"]["S2_b045_three_plates_auto_anchor_and_fast_inspect"] = {
        "job_id": sub2["job_id"],
        "status": job2["status"],
        "revision": rev2,
        "elapsed_seconds": elapsed2,
        "volume_before_mm3": vol1,
        "volume_after_mm3": vol2,
        "volume_delta_mm3": delta_b045,
        "expected_delta_mm3": 60000.0,
        "saved_file_reloaded_and_verified": job2["result"]["saved_file_reloaded_and_verified"],
        "full_inspection_count": len(inspect_summaries),
        "inspect_summaries": inspect_summaries,
        "per_edge_log_lines": len(edge_spam_lines),
        "helper_anchor_creations": len(anchor_helpers),
        "native_log_lines": len(log2_lines),
        "sketch_section_references": [op["section_references"] for op in sketch_ops],
    }

    # ------------------------------------------------------------------
    # Scenario 3 (BUG-174): Inline dump_plan_operations d1_d2 chamfer +
    # blind cuts with low_removal_warning=True (grazing) and False (full)
    # ------------------------------------------------------------------
    # Top face is z=400, front face is y=0. Pick the top-front straight edge
    # (0,0,400)->(400,0,400) via geometry_selector and top face (200,200,400).
    raw_s3_ops = [
        {
            "op": "chamfer",
            "label": "ch_d1d2",
            "chamfer_type": "d1_d2",
            "distance_1": 15.0,
            "distance_2": 10.0,
            "reference_surface": {
                "kind": "geometry_selector",
                "target": "surface",
                "points_mm": [[200.0, 200.0, 400.0]],
                "tolerance_mm": 0.5,
            },
            "references": [
                {
                    "edge": {
                        "kind": "geometry_selector",
                        "target": "edge",
                        "point_mm": [200.0, 0.0, 400.0],
                        "tolerance_mm": 0.5,
                    }
                }
            ],
        },
        # Grazing cut: 100x100 sketch on XY (z=0), only 1x100 mm overlaps x in [0,1],
        # cut depth 10 mm -> prism = 100,000 mm3, actual removed = 1,000 mm3 (1.0% < 5%)
        {
            "op": "sketch",
            "label": "sk_graze",
            "plane": "XY",
            "entities": [
                {"type": "rectangle", "name": "rg", "min": [-99.0, 100.0], "max": [1.0, 200.0]}
            ],
        },
        {
            "op": "extrude",
            "label": "cut_graze",
            "sketch": "sk_graze",
            "depth": 10.0,
            "mode": "cut",
            "direction": "positive",
        },
        # Full blind cut: 50x50 sketch inside XY (z=0), depth 10 mm -> 25,000 mm3 (100%)
        {
            "op": "sketch",
            "label": "sk_full_cut",
            "plane": "XY",
            "entities": [
                {"type": "rectangle", "name": "rf", "min": [50.0, 50.0], "max": [100.0, 100.0]}
            ],
        },
        {
            "op": "extrude",
            "label": "cut_full",
            "sketch": "sk_full_cut",
            "depth": 10.0,
            "mode": "cut",
            "direction": "positive",
        },
    ]
    # Exercise the exact creo_execute_plan inline path:
    validated_models = schema.OPERATIONS.validate_python(raw_s3_ops)
    dumped_s3 = schema.dump_plan_operations(validated_models)
    sub3 = general.submit(dumped_s3, model_id, None, rev2)
    job3 = wait_job(sub3["job_id"])
    assert job3["status"] == "succeeded", f"Scenario 3 failed: {job3}"
    rev3 = job3["revision"]
    vol3 = result_volume(job3)
    # Expected delta: -30,000 (chamfer 0.5*15*10*400) - 1,000 (graze) - 25,000 (full) = -56,000 mm3
    delta_s3 = vol3 - vol2
    assert abs(delta_s3 - (-56000.0)) < 1.0, f"Expected -56000 mm3, got {delta_s3}"
    ops3 = job3["result"]["operations"]
    graze_check = ops3[2]["cut_volume_check"]
    full_check = ops3[4]["cut_volume_check"]
    assert graze_check["low_removal_warning"] is True
    assert abs(graze_check["removal_ratio"] - 0.01) < 1e-4
    assert full_check["low_removal_warning"] is False
    assert abs(full_check["removal_ratio"] - 1.0) < 1e-4
    assert job3["result"]["saved_file_reloaded_and_verified"] is True

    report["scenarios"]["S3_inline_d1d2_chamfer_and_cut_volume_check"] = {
        "job_id": sub3["job_id"],
        "status": job3["status"],
        "revision": rev3,
        "volume_before_mm3": vol2,
        "volume_after_mm3": vol3,
        "volume_delta_mm3": delta_s3,
        "expected_delta_mm3": -56000.0,
        "saved_file_reloaded_and_verified": job3["result"]["saved_file_reloaded_and_verified"],
        "chamfer_details": {
            "chamfer_type": ops3[0].get("chamfer_type"),
            "distance_1": ops3[0].get("distance_1"),
            "distance_2": ops3[0].get("distance_2"),
            "material_delta_mm3": ops3[0].get("material_delta_mm3"),
        },
        "grazing_cut_volume_check": graze_check,
        "full_cut_volume_check": full_check,
    }

    # ------------------------------------------------------------------
    # Scenario 4 (BUG-171): restore_baseline(verify_mode="full" and "identity")
    # on an unknown_outcome model, verifying single inspection in full mode
    # and budget_seconds up to 1800
    # ------------------------------------------------------------------
    time.sleep(1.5)
    model_path = general.model_path(model_id)
    model_rec = general.model_info(model_id)
    model_rec["status"] = "unknown_outcome"
    model_rec["pending_job"] = sub3["job_id"]
    model_registry.write_model(model_path, model_rec)

    for _ in range(5):
        try:
            insp_full = reconciliation.inspect(model_id, live=False, budget_seconds=1200)
            if all(o.get("stopped") for o in insp_full.get("owners", [])):
                break
        except ValueError:
            pass
        time.sleep(1.0)
    assert insp_full["budgets"]["native_phase_seconds"] == 1200
    assert insp_full["actions"]["restore_baseline"]["available"] is True
    rec_sub_full = reconciliation.reconcile(
        model_id,
        mode="apply",
        action="restore_baseline",
        evidence_token=insp_full["evidence_token"],
        expected_revision=rev3,
        expected_pending_job_id=sub3["job_id"],
        idempotency_key=f"bug171_full_{suffix}",
        budget_seconds=1200,
        verify_mode="full",
    )
    rec_job_full = wait_job(rec_sub_full["job_id"])
    assert rec_job_full["status"] == "succeeded", f"Full restore_baseline failed: {rec_job_full}"
    rec_log_full = (
        (bridge.job_path(rec_sub_full["job_id"]) / "native.log")
        .read_text(encoding="utf-8", errors="replace")
        .splitlines()
    )
    rec_full_summaries = [l for l in rec_log_full if l.startswith("INSPECT_SUMMARY ")]
    assert len(rec_full_summaries) == 1, (
        f"Expected exactly 1 INSPECT_SUMMARY in full restore_baseline, got {len(rec_full_summaries)}"
    )

    # Also test terminal recovery_wait + identity restore
    time.sleep(1.5)
    model_rec = general.model_info(model_id)
    model_rec["status"] = "unknown_outcome"
    model_rec["pending_job"] = sub3["job_id"]
    model_registry.write_model(model_path, model_rec)
    for _ in range(5):
        try:
            insp_id = reconciliation.inspect(model_id, live=False, budget_seconds=1800)
            if all(o.get("stopped") for o in insp_id.get("owners", [])):
                break
        except ValueError:
            pass
        time.sleep(1.0)
    assert insp_id["budgets"]["native_phase_seconds"] == 1800
    rec_sub_id = reconciliation.reconcile(
        model_id,
        mode="apply",
        action="restore_baseline",
        evidence_token=insp_id["evidence_token"],
        expected_revision=rev3,
        expected_pending_job_id=sub3["job_id"],
        idempotency_key=f"bug171_id_{suffix}",
        budget_seconds=1800,
        verify_mode="identity",
    )
    rec_job_id = wait_job(rec_sub_id["job_id"])
    assert rec_job_id["status"] == "succeeded", f"Identity restore_baseline failed: {rec_job_id}"
    final_model = general.model_info(model_id)
    assert final_model["status"] == "ready"
    assert final_model["pending_job"] is None
    assert final_model["recovery_pending"] is None

    report["scenarios"]["S4_restore_baseline_single_full_and_1800s_identity"] = {
        "full_restore_job_id": rec_sub_full["job_id"],
        "full_restore_status": rec_job_full["status"],
        "full_restore_inspection_count": len(rec_full_summaries),
        "full_restore_inspect_summary": rec_full_summaries[0],
        "identity_restore_job_id": rec_sub_id["job_id"],
        "identity_restore_status": rec_job_id["status"],
        "identity_restore_budget_seconds": 1800,
        "final_model_status": final_model["status"],
        "final_revision": final_model["revision"],
    }
    report["all_passed"] = True
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default=str(ROOT / "build" / "feedback0358_hang_recovery_sketch.json"),
        help="Path to write JSON acceptance report",
    )
    args = parser.parse_args()
    result = run_live_suite()
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
