"""Live Creo acceptance suite for 0.36.0 feedback fixes (BUG-166, FEAT-076, FEAT-077).

Offline mode prints the planned matrix. ``--live --confirm-session-usable`` runs
all 5 cases sequentially against the active Creo session and writes a structured
report to ``build/feedback0360_recovery_preview_edges.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

VOL_TOL = 1e-2


def wait_job(job_id: str, timeout: float = 300.0) -> dict:
    terminal = {"succeeded", "failed", "aborted", "cancelled", "unknown_outcome"}
    deadline = time.time() + timeout
    record: dict = {}
    while time.time() < deadline:
        path = ROOT / "jobs" / job_id / "job.json"
        if path.is_file():
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("status") in terminal:
                return record
        time.sleep(0.5)
    raise SystemExit(f"job {job_id} did not reach a terminal state: {record.get('status')}")


def revision_of(generic_bridge, model_id: str) -> int:
    return int(generic_bridge.model_info(model_id).get("revision") or 0)


def volume_of(generic_bridge, model_id: str) -> float | None:
    view = generic_bridge.inspect_model(model_id, detail="compact")
    vol = (view.get("inspection") or {}).get("volume_mm3")
    return None if vol is None else float(vol)


def submit_new(generic_bridge, model_name: str, operations: list[dict]) -> dict:
    created = generic_bridge.submit(operations, model_name=model_name)
    return wait_job(created["job_id"])


def submit_edit(
    generic_bridge, model_id: str, operations: list[dict], *, readonly: bool = False
) -> dict:
    accepted = generic_bridge.submit(
        operations,
        model_id=model_id,
        expected_revision=None if readonly else revision_of(generic_bridge, model_id),
        readonly=readonly,
    )
    return wait_job(accepted["job_id"])


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_info() -> dict:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        )
        return {"commit": commit, "dirty": dirty}
    except Exception:
        return {"commit": "unknown", "dirty": True}


def run_live(bridge, generic_bridge) -> dict:
    from creo_mechdog import model_registry
    from creo_mechdog import reconciliation as rec

    stamp = time.strftime("%H%M%S")
    session = bridge.session_status()
    cases: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Case 1 (FEAT-077 / Issue E): Part JPEG preview hides datum planes
    # ------------------------------------------------------------------
    m1_job = submit_new(
        generic_bridge,
        f"f077_prev_{stamp}",
        [
            {
                "op": "sketch",
                "label": "blk_sk",
                "plane": "XY",
                "entities": [
                    {"type": "rectangle", "name": "blk_r", "min": [0, 0], "max": [60, 40]}
                ],
            },
            {
                "op": "extrude",
                "label": "blk_ext",
                "sketch": "blk_sk",
                "depth": 20.0,
                "mode": "add",
                "direction": "positive",
            },
        ],
    )
    assert m1_job["status"] == "succeeded", f"m1_job failed: {m1_job.get('message')}"
    m1 = m1_job["model_id"]

    exp_job = submit_edit(
        generic_bridge,
        m1,
        [{"op": "export", "format": "jpeg"}],
        readonly=True,
    )
    exp_res = exp_job.get("result") or {}
    exp_ops = exp_res.get("operations") or []
    exp_op = exp_ops[0] if exp_ops else {}
    # Check datum_display on either the build preview or export preview
    build_preview = (m1_job.get("result") or {}).get("preview") or {}
    exp_preview = exp_op.get("preview") or exp_res.get("preview") or {}
    datum_block = exp_preview.get("datum_display") or build_preview.get("datum_display") or {}
    exp_file = exp_op.get("file") or exp_res.get("export_file") or build_preview.get("file")
    exp_exists = bool(
        exp_file and Path(str(exp_file)).is_file() and Path(str(exp_file)).stat().st_size > 0
    )
    cases["F077_part_preview_hides_datums"] = {
        "model_id": m1,
        "build_job_id": m1_job["job_id"],
        "export_job_id": exp_job["job_id"],
        "export_status": exp_job.get("status"),
        "build_datum_display": build_preview.get("datum_display"),
        "export_datum_display": exp_preview.get("datum_display"),
        "datum_display_checked": datum_block,
        "output_file_verified": exp_exists,
        "pass": (
            exp_job.get("status") == "succeeded"
            and datum_block.get("model_type") == "part"
            and datum_block.get("applicable") is True
            and datum_block.get("attempted") is True
            and datum_block.get("hide_status") == "hidden"
            and datum_block.get("restore_status") == "restored"
            and datum_block.get("config_file_written") is False
            and exp_exists
        ),
    }

    # ------------------------------------------------------------------
    # Case 2 (FEAT-076 / Issue D): inspect_model near filter + feature-scoped edge round
    # ------------------------------------------------------------------
    m2_job = submit_new(
        generic_bridge,
        f"f076_edge_{stamp}",
        [
            {
                "op": "sketch",
                "label": "base_sk",
                "plane": "XY",
                "entities": [
                    {"type": "rectangle", "name": "base_r", "min": [0, 0], "max": [80, 60]}
                ],
            },
            {
                "op": "extrude",
                "label": "base_blk",
                "sketch": "base_sk",
                "depth": 10.0,
                "mode": "add",
                "direction": "positive",
            },
            {
                "op": "sketch",
                "label": "boss_sk",
                "plane": "XY",
                "offset": 10.0,
                "entities": [
                    {"type": "rectangle", "name": "boss_r", "min": [30, 20], "max": [50, 40]}
                ],
            },
            {
                "op": "extrude",
                "label": "top_boss",
                "sketch": "boss_sk",
                "depth": 10.0,
                "mode": "add",
                "direction": "positive",
            },
        ],
    )
    assert m2_job["status"] == "succeeded", f"m2_job failed: {m2_job.get('message')}"
    m2 = m2_job["model_id"]
    v_m2_before = volume_of(generic_bridge, m2)  # 80*60*10 + 20*20*10 = 52000.0

    # Spatial near query for top edge at x=30, y in [20,40], z=20
    near_page = generic_bridge.inspect_model(
        m2, detail="full", section="edges", limit=5, near=[30.0, 30.0, 20.0]
    )
    near_edges = (near_page.get("data") or {}).get("edges") or []
    near_dists = [float(e["distance_mm"]) for e in near_edges]
    near_ok = (
        len(near_edges) == 5
        and near_dists[0] <= 1e-4
        and near_dists == sorted(near_dists)
        and (near_page.get("near_filter") or {}).get("scanned_total", 0) >= 20
    )

    # Round that exact edge using geometry_selector(target="edge", point_mm=..., feature="top_boss")
    round_job = submit_edit(
        generic_bridge,
        m2,
        [
            {
                "op": "round",
                "label": "boss_r2",
                "size": 2.0,
                "references": [
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "point_mm": [30.0, 30.0, 20.0],
                            "feature": "top_boss",
                            "tolerance_mm": 0.5,
                        }
                    }
                ],
            }
        ],
    )
    v_m2_after = volume_of(generic_bridge, m2)
    expected_drop = 20.0 * (2.0**2 - math.pi * (2.0**2) / 4.0)
    expected_v_m2 = 52000.0 - expected_drop
    cases["F076_near_edge_query_and_feature_scoped_round"] = {
        "model_id": m2,
        "round_job_id": round_job["job_id"],
        "near_filter": near_page.get("near_filter"),
        "near_top3": [
            {"id": e.get("id"), "distance_mm": e.get("distance_mm")} for e in near_edges[:3]
        ],
        "near_query_ok": near_ok,
        "round_status": round_job.get("status"),
        "round_message": round_job.get("message"),
        "volume_before_mm3": v_m2_before,
        "volume_after_mm3": v_m2_after,
        "expected_volume_mm3": expected_v_m2,
        "saved_file_reloaded_and_verified": (round_job.get("result") or {}).get(
            "saved_file_reloaded_and_verified"
        ),
        "pass": (
            near_ok
            and round_job.get("status") == "succeeded"
            and v_m2_after is not None
            and abs(v_m2_after - expected_v_m2) <= VOL_TOL
            and bool((round_job.get("result") or {}).get("saved_file_reloaded_and_verified"))
        ),
    }

    # ------------------------------------------------------------------
    # Case 3 (BUG-166 / Issue B1): Cross-session restore_baseline (identity)
    # Simulate an unknown_outcome pending job with a DEAD pre-restart session_fingerprint.
    # ------------------------------------------------------------------
    dead_job_id = uuid.uuid4().hex
    dead_dir = bridge.job_path(dead_job_id)
    dead_dir.mkdir(parents=True, exist_ok=True)
    bridge.write_json(
        dead_dir / "job.json",
        {
            "job_id": dead_job_id,
            "model_id": m1,
            "kind": "generic",
            "status": "unknown_outcome",
            "failure_phase": "native_worker_started",
            "worker_started": True,
            "runner_identity": {"pid": 999997, "created": 1},
        },
    )
    bridge.write_json(dead_dir / "request.json", {"model": {"model_id": m1}})
    bridge.write_json(
        dead_dir / "native_owner.json",
        {
            "pid": 999999,
            "created": 1,
            "session_fingerprint": "dead-pre-restart-session-12345",
        },
    )
    m1_before = generic_bridge.model_info(m1)
    model_registry.write_model(
        generic_bridge.model_path(m1),
        {**m1_before, "status": "unknown_outcome", "pending_job": dead_job_id},
    )
    insp_c3 = rec.inspect(m1, live=False)
    apply_c3 = rec.apply(
        m1,
        "restore_baseline",
        int(m1_before["revision"]),
        dead_job_id,
        insp_c3["evidence_token"],
        f"live-xrestore-{stamp}",
    )
    rec_c3_done = wait_job(apply_c3["job_id"])
    m1_after_c3 = generic_bridge.model_info(m1)
    rec_c3_res = rec_c3_done.get("result") or {}
    cases["B166_1_cross_session_restore_baseline_identity"] = {
        "model_id": m1,
        "recovery_job_id": apply_c3["job_id"],
        "status": rec_c3_done.get("status"),
        "message": rec_c3_done.get("message"),
        "verification": rec_c3_res.get("verification"),
        "saved_file_reloaded_and_verified": rec_c3_res.get("saved_file_reloaded_and_verified"),
        "model_status_after": m1_after_c3.get("status"),
        "revision_after": m1_after_c3.get("revision"),
        "pending_job_after": m1_after_c3.get("pending_job"),
        "recovery_pending_after": m1_after_c3.get("recovery_pending"),
        "pass": (
            rec_c3_done.get("status") == "succeeded"
            and rec_c3_res.get("verification") == "identity"
            and rec_c3_res.get("saved_file_reloaded_and_verified") is True
            and m1_after_c3.get("status") == "ready"
            and m1_after_c3.get("revision") == m1_before["revision"]
            and m1_after_c3.get("pending_job") is None
            and m1_after_c3.get("recovery_pending") is None
        ),
    }

    # ------------------------------------------------------------------
    # Case 4 (BUG-166 / Issue B1): Cross-session abandon_new on rev-0 model
    # ------------------------------------------------------------------
    m_new = uuid.uuid4().hex
    m_new_dir = generic_bridge.model_path(m_new)
    (m_new_dir / "output").mkdir(parents=True, exist_ok=True)
    dead_new_job = uuid.uuid4().hex
    dead_new_dir = bridge.job_path(dead_new_job)
    dead_new_dir.mkdir(parents=True, exist_ok=True)
    bridge.write_json(
        dead_new_dir / "job.json",
        {
            "job_id": dead_new_job,
            "model_id": m_new,
            "kind": "generic",
            "status": "unknown_outcome",
            "worker_started": True,
            "runner_identity": {"pid": 999996, "created": 1},
        },
    )
    bridge.write_json(dead_new_dir / "request.json", {"model": {"model_id": m_new}})
    bridge.write_json(
        dead_new_dir / "native_owner.json",
        {
            "pid": 999998,
            "created": 1,
            "session_fingerprint": "dead-pre-restart-session-99999",
        },
    )
    model_registry.write_model(
        m_new_dir,
        {
            "model_id": m_new,
            "model_name": f"b166_uncom_{stamp}",
            "model_type": "part",
            "status": "unknown_outcome",
            "revision": 0,
            "created_at": bridge.now(),
            "output_directory": str(m_new_dir / "output"),
            "part_file": None,
            "aliases": {},
            "pending_job": dead_new_job,
            "recovery_pending": None,
        },
    )
    insp_c4 = rec.inspect(m_new, live=False)
    apply_c4 = rec.apply(
        m_new,
        "abandon_new",
        0,
        dead_new_job,
        insp_c4["evidence_token"],
        f"live-xabandon-{stamp}",
    )
    rec_c4_done = wait_job(apply_c4["job_id"])
    m_new_after = generic_bridge.model_info(m_new)
    cases["B166_2_cross_session_abandon_new"] = {
        "model_id": m_new,
        "recovery_job_id": apply_c4["job_id"],
        "status": rec_c4_done.get("status"),
        "message": rec_c4_done.get("message"),
        "model_status_after": m_new_after.get("status"),
        "pass": rec_c4_done.get("status") == "succeeded"
        and m_new_after.get("status") == "abandoned",
    }

    # ------------------------------------------------------------------
    # Case 5 (BUG-166 / Issues B2 + C): recovery_pending blocking label +
    # abandon_unknown_recovery + subsequent live edit/save succeeds!
    # ------------------------------------------------------------------
    dead_rec_id = uuid.uuid4().hex
    dead_rec_dir = bridge.job_path(dead_rec_id)
    dead_rec_dir.mkdir(parents=True, exist_ok=True)
    bridge.write_json(
        dead_rec_dir / "job.json",
        {
            "job_id": dead_rec_id,
            "model_id": m1,
            "kind": "reconciliation",
            "idempotency_key": f"dead-rec-{stamp}",
            "status": "unknown_outcome",
            "failure_phase": "native_worker_started",
            "worker_started": True,
            "runner_identity": {"pid": 999995, "created": 1},
        },
    )
    bridge.write_json(
        dead_rec_dir / "native_owner.json",
        {
            "pid": 999994,
            "created": 1,
            "session_fingerprint": "dead-pre-restart-session-88888",
        },
    )
    bridge.write_json(dead_rec_dir / "request.json", {"model": {"model_id": m1}})
    m1_c5 = generic_bridge.model_info(m1)
    model_registry.write_model(
        generic_bridge.model_path(m1),
        {**m1_c5, "status": "ready", "pending_job": None, "recovery_pending": dead_rec_id},
    )
    busy_payload = {}
    try:
        generic_bridge.submit([], model_id=m1, expected_revision=int(m1_c5["revision"]))
    except bridge.ToolkitBusy as exc:
        busy_payload = exc.payload

    insp_c5 = rec.inspect(m1, live=False)
    abandoned = rec.apply(
        m1,
        "abandon_unknown_recovery",
        int(m1_c5["revision"]),
        None,
        insp_c5["evidence_token"],
        f"live-unkrec-{stamp}",
        confirm_unknown_recovery=True,
    )
    # Immediately execute a real live edit (cut a 10x10 through-slot -> -2000 mm^3) to prove unlocked!
    post_edit = submit_edit(
        generic_bridge,
        m1,
        [
            {
                "op": "sketch",
                "label": "unlock_sk",
                "plane": "XY",
                "entities": [
                    {"type": "rectangle", "name": "unlock_r", "min": [25, 15], "max": [35, 25]}
                ],
            },
            {
                "op": "extrude",
                "label": "unlock_cut",
                "sketch": "unlock_sk",
                "mode": "cut",
                "depth_type": "through_all",
                "direction": "positive",
            },
        ],
    )
    v_m1_after = volume_of(generic_bridge, m1)
    expected_v_m1 = 60.0 * 40.0 * 20.0 - 10.0 * 10.0 * 20.0
    cases["B166_3_recovery_pending_blocking_and_abandon_unknown_recovery"] = {
        "model_id": m1,
        "busy_blocking_operation": busy_payload.get("blocking_operation"),
        "busy_blocking_job_id": busy_payload.get("blocking_job_id"),
        "busy_owner_snapshot": busy_payload.get("owner_snapshot"),
        "abandon_result": {
            "status": abandoned.get("status"),
            "recovery_pending": abandoned.get("recovery_pending"),
            "recovery_pending_released": abandoned.get("recovery_pending_released"),
            "disk_state_verified": abandoned.get("disk_state_verified"),
            "baseline_hash_verified": abandoned.get("baseline_hash_verified"),
        },
        "post_unlock_job_id": post_edit["job_id"],
        "post_unlock_status": post_edit.get("status"),
        "volume_after_mm3": v_m1_after,
        "expected_volume_mm3": expected_v_m1,
        "saved_file_reloaded_and_verified": (post_edit.get("result") or {}).get(
            "saved_file_reloaded_and_verified"
        ),
        "pass": (
            busy_payload.get("blocking_operation") == "recovery_pending"
            and busy_payload.get("blocking_job_id") == dead_rec_id
            and (busy_payload.get("owner_snapshot") or {}).get("pending_job") is None
            and abandoned.get("recovery_pending_released") is True
            and abandoned.get("status") == "ready"
            and abandoned.get("disk_state_verified") is False
            and post_edit.get("status") == "succeeded"
            and v_m1_after is not None
            and abs(v_m1_after - expected_v_m1) <= VOL_TOL
            and bool((post_edit.get("result") or {}).get("saved_file_reloaded_and_verified"))
        ),
    }

    all_passed = all(c.get("pass") for c in cases.values())
    return {
        "mode": "live",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": git_info(),
        "worker_sha256": sha256_file(ROOT / "build" / "creo_worker.exe"),
        "creo_release_numeric": session.get("release_numeric"),
        "toolkit_code": session.get("toolkit_code"),
        "passed": all_passed,
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-session-usable", action="store_true")
    args = parser.parse_args()
    planned = [
        "F077_part_preview_hides_datums",
        "F076_near_edge_query_and_feature_scoped_round",
        "B166_1_cross_session_restore_baseline_identity",
        "B166_2_cross_session_abandon_new",
        "B166_3_recovery_pending_blocking_and_abandon_unknown_recovery",
    ]
    if not args.live:
        print(json.dumps({"mode": "offline", "planned_cases": planned}, indent=2))
        return 0
    if not args.confirm_session_usable:
        raise SystemExit("pass --confirm-session-usable after verifying the live Creo session")

    import bridge
    import generic_bridge

    report = run_live(bridge, generic_bridge)
    target = ROOT / "build" / "feedback0360_recovery_preview_edges.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
