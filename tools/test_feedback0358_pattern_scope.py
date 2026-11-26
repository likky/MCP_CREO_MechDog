"""BUG-169 & FEAT-075 live Creo acceptance suite (2026-11-23 0.35.8 feedback).

Offline mode prints the planned matrix. ``--live --confirm-session-usable``
executes every positive and negative case against the running Creo session and
writes a structured report to ``build/feedback0358_pattern_scope.json``.

Cases
-----
B169_1_feature_id_and_cut_pattern:
    Verify extrude receipt exposes ``feature_id`` (both full and compact views),
    and ``linear_pattern`` on that cut exposes ``leader_id``, ``leader_kind="cut"``,
    ``leader_surface_count > 0``, ``member_count=3``, analytic ΔV, and reload pass.
B169_2_sketch_alias_rejected_pre_submit:
    Verify ``linear_pattern(leader=<sketch_label>)`` is rejected before job creation
    with ``LINEAR_PATTERN_NON_SOLID_LEADER`` and leaves revision unchanged.
B169_3_sketch_numeric_id_rejected_native:
    Verify ``linear_pattern(leader=<sketch_numeric_id>)`` fails natively before
    ``ProPatternCreate`` with ``LINEAR_PATTERN_NON_SOLID_LEADER`` and
    ``leader_kind="sketch_or_curve"``, rolling back cleanly.
B169_4_protrusion_and_feature_group_pattern:
    Verify ``linear_pattern`` succeeds on both a solid boss protrusion
    (``leader_kind="protrusion"``) and a ``feature_group`` containing sketch+cut
    (``leader_kind="feature_group"``), matching analytic volume and reload.
F075_1_two_body_positive_through_all_scope:
    Two Z-stacked bodies (Z in [0,20] and [30,50]); ``through_all`` positive cut
    scoped to Body A removes exact cylinder volume from Body A only while Body B
    is unchanged.
F075_2_three_body_symmetric_through_all_scope:
    Three Z-stacked bodies (Z in [-40,-20], [-10,10], [20,40]); ``through_all``
    symmetric cut scoped to Body A removes exact cylinder volume from Body A only
    while Body B and Body C stay unchanged.
F075_3_initial_body_minus5778_symmetric_through_all:
    Single-body initial ``-5778`` part cut with ``direction="symmetric"``,
    ``depth_type="through_all"``, ``scope=[-5778]`` (exact §7 feedback repro).
F075_4_unknown_body_through_all_rollback:
    ``through_all`` cut scoped to nonexistent body ``999999`` fails with
    ``F08_SCOPE_RESOLVE_FAILED`` and rolls back revision and volume cleanly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

VOL_TOL = 1e-2  # mm^3 analytic tolerance for cylindrical cuts


def wait_job(job_id: str, timeout: float = 300.0) -> dict:
    terminal = {"succeeded", "failed", "aborted", "cancelled"}
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


def bodies_of(generic_bridge, model_id: str) -> dict[int, dict]:
    records: list[dict] = []
    cursor = None
    while True:
        page = generic_bridge.inspect_model(
            model_id, detail="full", section="bodies", limit=200, cursor=cursor
        )
        data = page.get("data") or {}
        records.extend(data.get("bodies") or [])
        cursor = page.get("next_cursor")
        if not cursor:
            break
    out: dict[int, dict] = {}
    for body in records:
        out[int(body["id"])] = {
            "surface_count": body.get("surface_count"),
            "bbox": body.get("bbox"),
            "state": body.get("state"),
        }
    return out


def submit_new(generic_bridge, model_name: str, operations: list[dict]) -> dict:
    created = generic_bridge.submit(operations, model_name=model_name)
    return wait_job(created["job_id"])


def submit_edit(generic_bridge, model_id: str, operations: list[dict]) -> dict:
    accepted = generic_bridge.submit(
        operations, model_id=model_id, expected_revision=revision_of(generic_bridge, model_id)
    )
    return wait_job(accepted["job_id"])


def op_by_label(job: dict, label: str) -> dict:
    for item in (job.get("result") or {}).get("operations") or []:
        if item.get("label") == label:
            return item
    return {}


def compact_op_by_label(bridge, job: dict, label: str) -> dict:
    compact = bridge.compact_job(job)
    for item in (compact.get("result") or {}).get("operations") or []:
        if item.get("label") == label:
            return item
    return {}


def close_vol(actual: float | None, expected: float) -> bool:
    return actual is not None and abs(actual - expected) <= VOL_TOL


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_commit_and_dirty() -> dict:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        )
        return {"commit": commit, "dirty": dirty}
    except Exception:
        return {"commit": "unknown", "dirty": True}


def run_live(bridge, generic_bridge) -> dict:
    stamp = time.strftime("%H%M%S")
    session = bridge.session_status()
    cases: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Case 1, 2, 3: BUG-169 feature_id echo + solid cut pattern + sketch rejections
    # ------------------------------------------------------------------
    base_job = submit_new(
        generic_bridge,
        f"b169_cut_{stamp}",
        [
            {
                "op": "sketch",
                "label": "base_sk",
                "plane": "XY",
                "entities": [
                    {"type": "rectangle", "name": "base_rect", "min": [0, 0], "max": [120, 40]}
                ],
            },
            {
                "op": "extrude",
                "label": "base_ext",
                "sketch": "base_sk",
                "depth": 10.0,
                "mode": "add",
                "direction": "positive",
            },
        ],
    )
    assert base_job["status"] == "succeeded", f"base_job failed: {base_job.get('message')}"
    m1 = base_job["model_id"]
    base_bodies = bodies_of(generic_bridge, m1)
    initial_body_id = next(iter(base_bodies.keys()))
    v_base = volume_of(generic_bridge, m1)

    cut_job = submit_edit(
        generic_bridge,
        m1,
        [
            {
                "op": "sketch",
                "label": "slot_sk",
                "plane": "XY",
                "entities": [
                    {"type": "rectangle", "name": "slot_r", "min": [15, 15], "max": [25, 25]}
                ],
            },
            {
                "op": "extrude",
                "label": "slot_cut",
                "sketch": "slot_sk",
                "mode": "cut",
                "depth": 20.0,
                "direction": "symmetric",
                "scope": {"kind": "bodies", "body_ids": [initial_body_id]},
            },
        ],
    )
    assert cut_job["status"] == "succeeded", f"cut_job failed: {cut_job.get('message')}"
    from creo_mechdog import inspection_refs

    info_m1 = generic_bridge.model_info(m1)
    aliases_m1 = (
        inspection_refs.load_ref(info_m1["aliases_ref"])
        if info_m1.get("aliases_ref")
        else (info_m1.get("aliases") or {})
    )
    sk_alias_id = int(aliases_m1["slot_sk"]["feature_id"])
    cut_alias_id = int(aliases_m1["slot_cut"]["feature_id"])
    cut_op_full = op_by_label(cut_job, "slot_cut")
    cut_op_compact = compact_op_by_label(bridge, cut_job, "slot_cut")
    sk_op_full = op_by_label(cut_job, "slot_sk")

    pat_job = submit_edit(
        generic_bridge,
        m1,
        [
            {
                "op": "linear_pattern",
                "label": "slot_pat",
                "leader": "slot_cut",
                "direction": [1.0, 0.0, 0.0],
                "spacing": 30.0,
                "count": 3,
            }
        ],
    )
    pat_op_full = op_by_label(pat_job, "slot_pat")
    pat_op_compact = compact_op_by_label(bridge, pat_job, "slot_pat")
    v_after_pat = volume_of(generic_bridge, m1)
    expected_v_pat = 120.0 * 40.0 * 10.0 - 3 * (10.0 * 10.0 * 10.0)
    c1_pass = (
        cut_op_full.get("feature_id") == cut_alias_id
        and cut_op_compact.get("feature_id") == cut_alias_id
        and sk_op_full.get("feature_id") == sk_alias_id
        and cut_alias_id != sk_alias_id
        and pat_job.get("status") == "succeeded"
        and pat_op_full.get("leader_id") == cut_alias_id
        and pat_op_full.get("leader_kind") == "cut"
        and int(pat_op_full.get("leader_surface_count") or 0) > 0
        and pat_op_full.get("member_count") == 3
        and pat_op_compact.get("leader_id") == cut_alias_id
        and pat_op_compact.get("leader_kind") == "cut"
        and int(pat_op_compact.get("leader_surface_count") or 0) > 0
        and pat_op_compact.get("member_count") == 3
        and close_vol(v_after_pat, expected_v_pat)
        and bool((pat_job.get("result") or {}).get("saved_file_reloaded_and_verified"))
    )
    cases["B169_1_feature_id_and_cut_pattern"] = {
        "model_id": m1,
        "base_job_id": base_job["job_id"],
        "cut_job_id": cut_job["job_id"],
        "pattern_job_id": pat_job["job_id"],
        "initial_body_id": initial_body_id,
        "sk_alias_id": sk_alias_id,
        "cut_alias_id": cut_alias_id,
        "cut_op_feature_id_full": cut_op_full.get("feature_id"),
        "cut_op_feature_id_compact": cut_op_compact.get("feature_id"),
        "pattern_op_full": {
            "feature_id": pat_op_full.get("feature_id"),
            "leader_id": pat_op_full.get("leader_id"),
            "leader_kind": pat_op_full.get("leader_kind"),
            "leader_surface_count": pat_op_full.get("leader_surface_count"),
            "member_count": pat_op_full.get("member_count"),
        },
        "pattern_op_compact": {
            "feature_id": pat_op_compact.get("feature_id"),
            "leader_id": pat_op_compact.get("leader_id"),
            "leader_kind": pat_op_compact.get("leader_kind"),
            "leader_surface_count": pat_op_compact.get("leader_surface_count"),
            "member_count": pat_op_compact.get("member_count"),
        },
        "volume_base_mm3": v_base,
        "volume_after_pattern_mm3": v_after_pat,
        "expected_volume_mm3": expected_v_pat,
        "saved_file_reloaded_and_verified": (pat_job.get("result") or {}).get(
            "saved_file_reloaded_and_verified"
        ),
        "pass": c1_pass,
    }

    # Case 2: Python pre-submit rejects sketch alias leader
    rev_before_c2 = revision_of(generic_bridge, m1)
    c2_error = ""
    try:
        generic_bridge.submit(
            [
                {
                    "op": "linear_pattern",
                    "label": "bad_sk_alias_pat",
                    "leader": "slot_sk",
                    "direction": [1.0, 0.0, 0.0],
                    "spacing": 30.0,
                    "count": 2,
                }
            ],
            model_id=m1,
            expected_revision=rev_before_c2,
        )
    except ValueError as exc:
        c2_error = str(exc)
    rev_after_c2 = revision_of(generic_bridge, m1)
    cases["B169_2_sketch_alias_rejected_pre_submit"] = {
        "model_id": m1,
        "error": c2_error,
        "revision_before": rev_before_c2,
        "revision_after": rev_after_c2,
        "pass": "LINEAR_PATTERN_NON_SOLID_LEADER" in c2_error and rev_before_c2 == rev_after_c2,
    }

    # Case 3: Native worker rejects raw numeric sketch ID before ProPatternCreate
    rev_before_c3 = revision_of(generic_bridge, m1)
    vol_before_c3 = volume_of(generic_bridge, m1)
    c3_job = submit_edit(
        generic_bridge,
        m1,
        [
            {
                "op": "linear_pattern",
                "label": "bad_sk_id_pat",
                "leader": sk_alias_id,
                "direction": [1.0, 0.0, 0.0],
                "spacing": 30.0,
                "count": 2,
            }
        ],
    )
    c3_op = op_by_label(c3_job, "bad_sk_id_pat")
    rev_after_c3 = revision_of(generic_bridge, m1)
    vol_after_c3 = volume_of(generic_bridge, m1)
    c3_msg = str(c3_job.get("message") or "")
    cases["B169_3_sketch_numeric_id_rejected_native"] = {
        "model_id": m1,
        "job_id": c3_job["job_id"],
        "status": c3_job.get("status"),
        "message": c3_msg,
        "leader_id": c3_op.get("leader_id"),
        "leader_kind": c3_op.get("leader_kind"),
        "leader_surface_count": c3_op.get("leader_surface_count"),
        "revision_before": rev_before_c3,
        "revision_after": rev_after_c3,
        "volume_before_mm3": vol_before_c3,
        "volume_after_mm3": vol_after_c3,
        "pass": (
            c3_job.get("status") == "failed"
            and "LINEAR_PATTERN_NON_SOLID_LEADER" in c3_msg
            and c3_op.get("leader_kind") == "sketch_or_curve"
            and rev_before_c3 == rev_after_c3
            and close_vol(vol_after_c3, expected_v_pat)
        ),
    }

    # ------------------------------------------------------------------
    # Case 4: BUG-169 boss protrusion + feature_group linear_pattern
    # ------------------------------------------------------------------
    m4_base = submit_new(
        generic_bridge,
        f"b169_grp_{stamp}",
        [
            {
                "op": "sketch",
                "label": "p_sk",
                "plane": "XY",
                "entities": [
                    {"type": "rectangle", "name": "p_rect", "min": [0, 0], "max": [120, 40]}
                ],
            },
            {
                "op": "extrude",
                "label": "p_blk",
                "sketch": "p_sk",
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
                    {"type": "rectangle", "name": "boss_r", "min": [10, 5], "max": [20, 15]}
                ],
            },
            {
                "op": "extrude",
                "label": "boss_ext",
                "sketch": "boss_sk",
                "depth": 8.0,
                "mode": "add",
                "direction": "positive",
            },
        ],
    )
    assert m4_base["status"] == "succeeded", f"m4_base failed: {m4_base.get('message')}"
    m4 = m4_base["model_id"]

    boss_pat = submit_edit(
        generic_bridge,
        m4,
        [
            {
                "op": "linear_pattern",
                "label": "boss_pat",
                "leader": "boss_ext",
                "direction": [1.0, 0.0, 0.0],
                "spacing": 30.0,
                "count": 3,
            }
        ],
    )
    boss_pat_op = op_by_label(boss_pat, "boss_pat")
    v_after_boss = volume_of(generic_bridge, m4)
    expected_v_boss = 120.0 * 40.0 * 10.0 + 3 * (10.0 * 10.0 * 8.0)

    grp_create = submit_edit(
        generic_bridge,
        m4,
        [
            {
                "op": "sketch",
                "label": "g_sk",
                "plane": "XY",
                "entities": [
                    {"type": "rectangle", "name": "g_r", "min": [10, 24], "max": [16, 30]}
                ],
            },
            {
                "op": "extrude",
                "label": "g_cut",
                "sketch": "g_sk",
                "mode": "cut",
                "depth": 20.0,
                "direction": "symmetric",
            },
            {
                "op": "feature_group",
                "label": "g_grp",
                "features": ["g_sk", "g_cut"],
            },
        ],
    )
    assert grp_create["status"] == "succeeded", f"grp_create failed: {grp_create.get('message')}"

    grp_pat = submit_edit(
        generic_bridge,
        m4,
        [
            {
                "op": "linear_pattern",
                "label": "grp_pat",
                "leader": "g_grp",
                "direction": [1.0, 0.0, 0.0],
                "spacing": 30.0,
                "count": 2,
            }
        ],
    )
    grp_pat_op = op_by_label(grp_pat, "grp_pat")
    v_after_grp = volume_of(generic_bridge, m4)
    expected_v_grp = expected_v_boss - 2 * (6.0 * 6.0 * 10.0)
    cases["B169_4_protrusion_and_feature_group_pattern"] = {
        "model_id": m4,
        "boss_pattern_job_id": boss_pat["job_id"],
        "boss_leader_kind": boss_pat_op.get("leader_kind"),
        "boss_leader_surface_count": boss_pat_op.get("leader_surface_count"),
        "boss_member_count": boss_pat_op.get("member_count"),
        "volume_after_boss_mm3": v_after_boss,
        "expected_volume_boss_mm3": expected_v_boss,
        "group_pattern_job_id": grp_pat["job_id"],
        "group_leader_kind": grp_pat_op.get("leader_kind"),
        "group_leader_surface_count": grp_pat_op.get("leader_surface_count"),
        "group_member_count": grp_pat_op.get("member_count"),
        "volume_after_group_mm3": v_after_grp,
        "expected_volume_group_mm3": expected_v_grp,
        "saved_file_reloaded_and_verified": (grp_pat.get("result") or {}).get(
            "saved_file_reloaded_and_verified"
        ),
        "pass": (
            boss_pat.get("status") == "succeeded"
            and boss_pat_op.get("leader_kind") == "protrusion"
            and int(boss_pat_op.get("leader_surface_count") or 0) > 0
            and boss_pat_op.get("member_count") == 3
            and close_vol(v_after_boss, expected_v_boss)
            and bool((boss_pat.get("result") or {}).get("saved_file_reloaded_and_verified"))
            and grp_pat.get("status") == "succeeded"
            and grp_pat_op.get("leader_kind") == "feature_group"
            and int(grp_pat_op.get("leader_surface_count") or 0) > 0
            and grp_pat_op.get("member_count") == 2
            and close_vol(v_after_grp, expected_v_grp)
            and bool((grp_pat.get("result") or {}).get("saved_file_reloaded_and_verified"))
        ),
    }

    # ------------------------------------------------------------------
    # Case 5: FEAT-075 two-body positive through_all + scope
    # ------------------------------------------------------------------
    f1_base = submit_new(
        generic_bridge,
        f"f075_2b_{stamp}",
        [
            {
                "op": "sketch",
                "label": "a_sk",
                "plane": "XY",
                "offset": 0.0,
                "entities": [
                    {"type": "rectangle", "name": "a_r", "min": [-30, -30], "max": [30, 30]}
                ],
            },
            {
                "op": "extrude",
                "label": "body_a",
                "sketch": "a_sk",
                "depth": 20.0,
                "mode": "add",
                "direction": "positive",
            },
            {
                "op": "sketch",
                "label": "b_sk",
                "plane": "XY",
                "offset": 30.0,
                "entities": [
                    {"type": "rectangle", "name": "b_r", "min": [-30, -30], "max": [30, 30]}
                ],
            },
            {
                "op": "extrude",
                "label": "body_b",
                "sketch": "b_sk",
                "depth": 20.0,
                "mode": "add",
                "direction": "positive",
                "new_body": True,
            },
        ],
    )
    assert f1_base["status"] == "succeeded", f"f1_base failed: {f1_base.get('message')}"
    m5 = f1_base["model_id"]
    bodies_m5_before = bodies_of(generic_bridge, m5)
    # Identify Body A (z_max ~ 20) vs Body B (z_min ~ 30)
    body_a_id = next(
        bid for bid, info in bodies_m5_before.items() if abs(info["bbox"][1][2] - 20.0) < 1.0
    )
    body_b_id = next(bid for bid in bodies_m5_before if bid != body_a_id)
    v_m5_before = volume_of(generic_bridge, m5)

    f1_cut = submit_edit(
        generic_bridge,
        m5,
        [
            {
                "op": "sketch",
                "label": "cut_sk",
                "plane": "XY",
                "offset": 0.0,
                "entities": [{"type": "circle", "name": "cut_c", "center": [0, 0], "radius": 10.0}],
            },
            {
                "op": "extrude",
                "label": "cut_ta_pos",
                "sketch": "cut_sk",
                "mode": "cut",
                "depth_type": "through_all",
                "direction": "positive",
                "scope": {"kind": "bodies", "body_ids": [body_a_id]},
            },
        ],
    )
    f1_op = op_by_label(f1_cut, "cut_ta_pos")
    bodies_m5_after = bodies_of(generic_bridge, m5)
    v_m5_after = volume_of(generic_bridge, m5)
    cyl_vol = math.pi * (10.0**2) * 20.0
    expected_v_m5 = 2.0 * (60.0 * 60.0 * 20.0) - cyl_vol
    scope_f1 = f1_op.get("scope_applied") or {}
    cases["F075_1_two_body_positive_through_all_scope"] = {
        "model_id": m5,
        "job_id": f1_cut["job_id"],
        "status": f1_cut.get("status"),
        "body_a_id": body_a_id,
        "body_b_id": body_b_id,
        "scope_applied": scope_f1,
        "body_b_before": bodies_m5_before[body_b_id],
        "body_b_after": bodies_m5_after.get(body_b_id),
        "volume_before_mm3": v_m5_before,
        "volume_after_mm3": v_m5_after,
        "expected_volume_mm3": expected_v_m5,
        "saved_file_reloaded_and_verified": (f1_cut.get("result") or {}).get(
            "saved_file_reloaded_and_verified"
        ),
        "pass": (
            f1_cut.get("status") == "succeeded"
            and scope_f1.get("applied_body_ids") == [body_a_id]
            and scope_f1.get("non_target_bodies_unchanged") is True
            and bodies_m5_after.get(body_b_id) == bodies_m5_before[body_b_id]
            and close_vol(v_m5_after, expected_v_m5)
            and bool((f1_cut.get("result") or {}).get("saved_file_reloaded_and_verified"))
        ),
    }

    # ------------------------------------------------------------------
    # Case 8 (reuses m5): FEAT-075 unknown body ID through_all rollback
    # ------------------------------------------------------------------
    rev_before_f4 = revision_of(generic_bridge, m5)
    f4_cut = submit_edit(
        generic_bridge,
        m5,
        [
            {
                "op": "sketch",
                "label": "bad_scope_sk",
                "plane": "XY",
                "entities": [
                    {"type": "circle", "name": "bad_c", "center": [15, 15], "radius": 3.0}
                ],
            },
            {
                "op": "extrude",
                "label": "bad_scope_cut",
                "sketch": "bad_scope_sk",
                "mode": "cut",
                "depth_type": "through_all",
                "direction": "positive",
                "scope": {"kind": "bodies", "body_ids": [999999]},
            },
        ],
    )
    rev_after_f4 = revision_of(generic_bridge, m5)
    v_after_f4 = volume_of(generic_bridge, m5)
    f4_msg = str(f4_cut.get("message") or "")
    cases["F075_4_unknown_body_through_all_rollback"] = {
        "model_id": m5,
        "job_id": f4_cut["job_id"],
        "status": f4_cut.get("status"),
        "message": f4_msg,
        "revision_before": rev_before_f4,
        "revision_after": rev_after_f4,
        "volume_after_mm3": v_after_f4,
        "expected_volume_mm3": expected_v_m5,
        "pass": (
            f4_cut.get("status") == "failed"
            and "F08_SCOPE_RESOLVE_FAILED" in f4_msg
            and rev_before_f4 == rev_after_f4
            and close_vol(v_after_f4, expected_v_m5)
        ),
    }

    # ------------------------------------------------------------------
    # Case 6: FEAT-075 three-body symmetric through_all + scope
    # ------------------------------------------------------------------
    f2_base = submit_new(
        generic_bridge,
        f"f075_3b_{stamp}",
        [
            {
                "op": "sketch",
                "label": "a_sk",
                "plane": "XY",
                "offset": 0.0,
                "entities": [
                    {"type": "rectangle", "name": "a_r", "min": [-30, -30], "max": [30, 30]}
                ],
            },
            {
                "op": "extrude",
                "label": "body_a",
                "sketch": "a_sk",
                "depth": 20.0,
                "mode": "add",
                "direction": "symmetric",
            },
            {
                "op": "sketch",
                "label": "b_sk",
                "plane": "XY",
                "offset": 20.0,
                "entities": [
                    {"type": "rectangle", "name": "b_r", "min": [-30, -30], "max": [30, 30]}
                ],
            },
            {
                "op": "extrude",
                "label": "body_b",
                "sketch": "b_sk",
                "depth": 20.0,
                "mode": "add",
                "direction": "positive",
                "new_body": True,
            },
            {
                "op": "sketch",
                "label": "c_sk",
                "plane": "XY",
                "offset": -40.0,
                "entities": [
                    {"type": "rectangle", "name": "c_r", "min": [-30, -30], "max": [30, 30]}
                ],
            },
            {
                "op": "extrude",
                "label": "body_c",
                "sketch": "c_sk",
                "depth": 20.0,
                "mode": "add",
                "direction": "positive",
                "new_body": True,
            },
        ],
    )
    assert f2_base["status"] == "succeeded", f"f2_base failed: {f2_base.get('message')}"
    m6 = f2_base["model_id"]
    bodies_m6_before = bodies_of(generic_bridge, m6)
    center_id = next(
        bid
        for bid, info in bodies_m6_before.items()
        if abs(info["bbox"][0][2] - (-10.0)) < 1.0 and abs(info["bbox"][1][2] - 10.0) < 1.0
    )
    other_ids = sorted(bid for bid in bodies_m6_before if bid != center_id)
    v_m6_before = volume_of(generic_bridge, m6)

    f2_cut = submit_edit(
        generic_bridge,
        m6,
        [
            {
                "op": "sketch",
                "label": "sym_sk",
                "plane": "XY",
                "offset": 0.0,
                "entities": [{"type": "circle", "name": "sym_c", "center": [0, 0], "radius": 10.0}],
            },
            {
                "op": "extrude",
                "label": "cut_ta_sym",
                "sketch": "sym_sk",
                "mode": "cut",
                "depth_type": "through_all",
                "direction": "symmetric",
                "scope": {"kind": "bodies", "body_ids": [center_id]},
            },
        ],
    )
    f2_op = op_by_label(f2_cut, "cut_ta_sym")
    bodies_m6_after = bodies_of(generic_bridge, m6)
    v_m6_after = volume_of(generic_bridge, m6)
    expected_v_m6 = 3.0 * (60.0 * 60.0 * 20.0) - cyl_vol
    scope_f2 = f2_op.get("scope_applied") or {}
    others_unchanged = all(bodies_m6_after.get(bid) == bodies_m6_before[bid] for bid in other_ids)
    cases["F075_2_three_body_symmetric_through_all_scope"] = {
        "model_id": m6,
        "job_id": f2_cut["job_id"],
        "status": f2_cut.get("status"),
        "center_body_id": center_id,
        "other_body_ids": other_ids,
        "scope_applied": scope_f2,
        "other_bodies_unchanged": others_unchanged,
        "volume_before_mm3": v_m6_before,
        "volume_after_mm3": v_m6_after,
        "expected_volume_mm3": expected_v_m6,
        "saved_file_reloaded_and_verified": (f2_cut.get("result") or {}).get(
            "saved_file_reloaded_and_verified"
        ),
        "pass": (
            f2_cut.get("status") == "succeeded"
            and scope_f2.get("applied_body_ids") == [center_id]
            and scope_f2.get("non_target_bodies_unchanged") is True
            and others_unchanged
            and close_vol(v_m6_after, expected_v_m6)
            and bool((f2_cut.get("result") or {}).get("saved_file_reloaded_and_verified"))
        ),
    }

    # ------------------------------------------------------------------
    # Case 7: FEAT-075 initial body -5778 symmetric through_all (§7 repro)
    # Use new_loft_part (same seed path as frigate_v4 / BUG-150) which yields
    # initial body id -5778 in Creo 10.
    # ------------------------------------------------------------------
    f3_created = generic_bridge.new_loft_part(
        None,
        None,
        [
            {
                "op": "sketch",
                "label": "init_s0",
                "plane": "XY",
                "offset": -10.0,
                "entities": [
                    {"type": "rectangle", "name": "r0", "min": [-30, -30], "max": [30, 30]}
                ],
            },
            {
                "op": "sketch",
                "label": "init_s1",
                "plane": "XY",
                "offset": 10.0,
                "entities": [
                    {"type": "rectangle", "name": "r1", "min": [-30, -30], "max": [30, 30]}
                ],
            },
        ],
        "init_loft",
        f"f075_init_{stamp}",
        None,
        "straight",
    )
    f3_base = wait_job(f3_created["job_id"])
    assert f3_base["status"] == "succeeded", f"f3_base failed: {f3_base.get('message')}"
    m7 = f3_base["model_id"]
    bodies_m7 = bodies_of(generic_bridge, m7)
    init_id_m7 = next(iter(bodies_m7.keys()))

    f3_cut = submit_edit(
        generic_bridge,
        m7,
        [
            {
                "op": "sketch",
                "label": "s7_sk",
                "plane": "XY",
                "entities": [{"type": "circle", "name": "s7_c", "center": [0, 0], "radius": 10.0}],
            },
            {
                "op": "extrude",
                "label": "s7_cut",
                "sketch": "s7_sk",
                "mode": "cut",
                "depth_type": "through_all",
                "direction": "symmetric",
                "scope": {"kind": "bodies", "body_ids": [init_id_m7]},
            },
        ],
    )
    f3_op = op_by_label(f3_cut, "s7_cut")
    v_m7_after = volume_of(generic_bridge, m7)
    expected_v_m7 = 60.0 * 60.0 * 20.0 - cyl_vol
    scope_f3 = f3_op.get("scope_applied") or {}
    cases["F075_3_initial_body_minus5778_symmetric_through_all"] = {
        "model_id": m7,
        "job_id": f3_cut["job_id"],
        "status": f3_cut.get("status"),
        "initial_body_id": init_id_m7,
        "scope_applied": scope_f3,
        "volume_after_mm3": v_m7_after,
        "expected_volume_mm3": expected_v_m7,
        "saved_file_reloaded_and_verified": (f3_cut.get("result") or {}).get(
            "saved_file_reloaded_and_verified"
        ),
        "pass": (
            f3_cut.get("status") == "succeeded"
            and init_id_m7 == -5778
            and scope_f3.get("applied_body_ids") == [-5778]
            and close_vol(v_m7_after, expected_v_m7)
            and bool((f3_cut.get("result") or {}).get("saved_file_reloaded_and_verified"))
        ),
    }

    all_passed = all(c.get("pass") for c in cases.values())
    return {
        "mode": "live",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": git_commit_and_dirty(),
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
        "B169_1_feature_id_and_cut_pattern",
        "B169_2_sketch_alias_rejected_pre_submit",
        "B169_3_sketch_numeric_id_rejected_native",
        "B169_4_protrusion_and_feature_group_pattern",
        "F075_1_two_body_positive_through_all_scope",
        "F075_2_three_body_symmetric_through_all_scope",
        "F075_3_initial_body_minus5778_symmetric_through_all",
        "F075_4_unknown_body_through_all_rollback",
    ]
    if not args.live:
        print(json.dumps({"mode": "offline", "planned_cases": planned}, indent=2))
        return 0
    if not args.confirm_session_usable:
        raise SystemExit("pass --confirm-session-usable after verifying the live Creo session")

    import bridge
    from creo_mechdog import generic_bridge

    report = run_live(bridge, generic_bridge)
    target = ROOT / "build" / "feedback0358_pattern_scope.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
