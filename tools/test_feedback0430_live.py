"""Live Creo 10 acceptance for 0.43.0 feedback batch (BUG-183..185, FEAT-082..083).

Run after `bridge.py build` with an active Creo session:
    .\\.venv\\Scripts\\python.exe tools\\test_feedback0430_live.py
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
    read_only: bool = False,
    allow_failure: bool = False,
) -> dict:
    rec = general.submit(
        ops,
        model_id=model_id,
        model_name=model_name,
        expected_revision=expected_revision,
        readonly=read_only,
    )
    job = wait_job(rec["job_id"])
    if not allow_failure and job.get("status") != "succeeded":
        raise RuntimeError(
            f"Job {job['job_id']} failed unexpectedly: {job.get('message')} | "
            f"{json.dumps(job.get('result', {}).get('failed_operation'), ensure_ascii=False)}"
        )
    return job


def job_revision(job: dict) -> int:
    for container in (job, job.get("result") or {}):
        for key in ("model_revision", "revision"):
            val = container.get(key)
            if isinstance(val, int):
                return val
    return 1


def scenario_s1_bspline_solved_area_and_cut_check() -> dict:
    """BUG-183: native solved_section_area_mm2, b_spline_cut_risk, and symmetric cut check."""
    j1 = run_ops(
        [
            {
                "op": "sketch",
                "label": "sk_plate",
                "plane": "YZ",
                "entities": [{"type": "rectangle", "name": "r1", "min": [0, 0], "max": [40, 40]}],
            },
            {
                "op": "extrude",
                "label": "plate",
                "sketch": "sk_plate",
                "depth": 3.0,
                "mode": "add",
                "direction": "symmetric",
            },
        ],
        model_name=unique_name("s1_bspl_cut"),
    )
    mid = j1["model_id"]
    rev = job_revision(j1)

    # Closed B-spline + 3 lines forming a ~10x10 region (area ~100 mm^2), cut symmetrically through 3 mm plate.
    j2 = run_ops(
        [
            {
                "op": "sketch",
                "label": "sk_cut_bspl",
                "plane": "YZ",
                "entities": [
                    {"type": "line", "name": "l1", "start": [10, 10], "end": [20, 10]},
                    {"type": "line", "name": "l2", "start": [20, 10], "end": [20, 20]},
                    {
                        "type": "b_spline",
                        "name": "sp_top",
                        "degree": 3,
                        "control_points": [[20, 20], [17, 22], [13, 18], [10, 20]],
                    },
                    {"type": "line", "name": "l4", "start": [10, 20], "end": [10, 10]},
                ],
            },
            {
                "op": "extrude",
                "label": "cut_bspl",
                "sketch": "sk_cut_bspl",
                "depth": 3.0,
                "mode": "cut",
                "direction": "symmetric",
            },
        ],
        model_id=mid,
        expected_revision=rev,
    )
    ops2 = j2["result"]["operations"]
    sk_rec, ext_rec = ops2[0], ops2[1]
    sk_area = sk_rec.get("native_section", {}).get("solved_section_area_mm2")
    assert sk_area is not None and 90.0 < sk_area < 110.0, (
        f"Unexpected sketch solved area: {sk_area}"
    )
    assert "b_spline_cut_risk" in sk_rec, "Missing b_spline_cut_risk on closed B-spline sketch"

    ext_area = ext_rec.get("solved_section_area_mm2")
    assert ext_area is not None and abs(ext_area - sk_area) < 1e-3, (
        f"Extrude solved area mismatch: {ext_area}"
    )
    chk = ext_rec.get("cut_volume_check")
    assert isinstance(chk, dict), f"Missing cut_volume_check on symmetric B-spline cut: {ext_rec}"
    assert chk.get("area_source") == "native_solved_section", chk
    assert chk.get("b_spline_cut_risk") is True, chk
    assert j2["result"].get("saved_file_reloaded_and_verified") is True

    # Also verify zero-material cut emits solved_section_area_mm2 in cut_geometry_context.
    j3 = run_ops(
        [
            {
                "op": "sketch",
                "label": "sk_miss",
                "plane": "YZ",
                "entities": [
                    {"type": "line", "name": "m1", "start": [100, 100], "end": [110, 100]},
                    {"type": "line", "name": "m2", "start": [110, 100], "end": [110, 110]},
                    {"type": "line", "name": "m3", "start": [110, 110], "end": [100, 110]},
                    {"type": "line", "name": "m4", "start": [100, 110], "end": [100, 100]},
                ],
            },
            {
                "op": "extrude",
                "label": "cut_miss",
                "sketch": "sk_miss",
                "depth": 3.0,
                "mode": "cut",
                "direction": "symmetric",
            },
        ],
        model_id=mid,
        expected_revision=job_revision(j2),
        allow_failure=True,
    )
    assert j3["status"] == "failed", f"Expected zero-material cut failure, got {j3['status']}"
    ctx = j3["result"]["operations"][1].get("cut_geometry_context", {})
    miss_area = ctx.get("solved_section_area_mm2")
    assert miss_area is not None and abs(miss_area - 100.0) < 0.5, (
        f"Missing/wrong cut_geometry_context solved_section_area_mm2: {ctx}"
    )

    return {
        "status": "passed",
        "model_id": mid,
        "cut_job_id": j2["job_id"],
        "miss_job_id": j3["job_id"],
        "sketch_solved_section_area_mm2": sk_area,
        "cut_volume_check": chk,
        "miss_solved_section_area_mm2": miss_area,
        "saved_file_reloaded_and_verified": j2["result"]["saved_file_reloaded_and_verified"],
    }


def scenario_s2_jpeg_orthographic_and_matrix() -> dict:
    """FEAT-082: right/left/front orthographic views and custom 3x3 view_matrix on thin YZ plate."""
    j1 = run_ops(
        [
            {
                "op": "sketch",
                "label": "sk_yz",
                "plane": "YZ",
                "entities": [{"type": "rectangle", "name": "r1", "min": [0, 0], "max": [60, 40]}],
            },
            {
                "op": "extrude",
                "label": "thin_plate",
                "sketch": "sk_yz",
                "depth": 3.0,
                "mode": "add",
                "direction": "symmetric",
            },
        ],
        model_name=unique_name("s2_yz_views"),
    )
    mid = j1["model_id"]
    s = math.sqrt(0.5)
    custom_mat = [[s, s, 0.0], [-s, s, 0.0], [0.0, 0.0, 1.0]]
    results = {}
    for label, opts in (
        ("right", {"view": "right", "width_px": 1200, "height_px": 900}),
        ("left", {"view": "left", "width_px": 800, "height_px": 600}),
        ("front", {"view": "front", "width_px": 800, "height_px": 600}),
        ("custom_matrix", {"view_matrix": custom_mat, "width_px": 800, "height_px": 600}),
    ):
        j = run_ops(
            [{"op": "export", "format": "jpeg", "jpeg_options": opts}],
            model_id=mid,
            read_only=True,
        )
        op_res = j["result"]["operations"][0]
        prev = op_res["preview"]
        assert prev.get("view_matrix_matches") is True, f"{label} view_matrix_matches false: {prev}"
        assert prev.get("requested_view") == label, f"{label} requested_view mismatch: {prev}"
        file_path = Path(op_res["file"])
        assert file_path.exists() and file_path.stat().st_size > 1000, f"{label} file missing/empty"
        results[label] = {
            "job_id": j["job_id"],
            "file_bytes": file_path.stat().st_size,
            "view_matrix_matches": prev.get("view_matrix_matches"),
        }
    return {"status": "passed", "model_id": mid, "views": results}


def scenario_s3_region_interior_point_live() -> dict:
    """FEAT-083: cut a B-spline bounded sub-region using ONLY interior_point_yz_mm."""
    j1 = run_ops(
        [
            {
                "op": "sketch",
                "label": "sk_base",
                "plane": "YZ",
                "entities": [{"type": "rectangle", "name": "r1", "min": [0, 0], "max": [30, 20]}],
            },
            {"op": "extrude", "label": "base", "sketch": "sk_base", "depth": 5.0, "mode": "add"},
        ],
        model_name=unique_name("s3_reg_pt"),
    )
    mid = j1["model_id"]
    rev = job_revision(j1)
    j2 = run_ops(
        [
            {
                "op": "sketch",
                "label": "sk_multi",
                "plane": "YZ",
                "entities": [
                    {"type": "line", "name": "bot", "start": [5, 2], "end": [25, 2]},
                    {"type": "line", "name": "rgt", "start": [25, 2], "end": [25, 18]},
                    {"type": "line", "name": "top", "start": [25, 18], "end": [5, 18]},
                    {"type": "line", "name": "lft", "start": [5, 18], "end": [5, 2]},
                    {
                        "type": "b_spline",
                        "name": "mid_sp",
                        "degree": 3,
                        "control_points": [[5, 10], [11, 12], [19, 8], [25, 10]],
                    },
                ],
            },
            {
                "op": "extrude",
                "label": "cut_upper",
                "sketch": "sk_multi",
                "depth": 5.0,
                "mode": "cut",
                "region": {"interior_point_yz_mm": [15.0, 15.0]},
            },
        ],
        model_id=mid,
        expected_revision=rev,
    )
    vol_before = 30.0 * 20.0 * 5.0
    vol_after = float(general.inspect_model(mid, detail="compact")["inspection"]["volume_mm3"])
    removed = vol_before - vol_after
    # Upper sub-region is ~20x8 = 160 mm^2 * 5 mm = ~800 mm^3 (symmetric cubic S-curve preserves exact mean y=10)
    assert abs(removed - 800.0) < 2.0, f"Expected ~800 mm^3 removed, got {removed}"
    assert j2["result"].get("saved_file_reloaded_and_verified") is True
    return {
        "status": "passed",
        "model_id": mid,
        "job_id": j2["job_id"],
        "volume_before_mm3": vol_before,
        "volume_after_mm3": vol_after,
        "removed_mm3": removed,
        "saved_file_reloaded_and_verified": j2["result"]["saved_file_reloaded_and_verified"],
    }


def main() -> int:
    report = {"scenarios": {}}
    for name, fn in (
        ("S1_bspline_solved_area_and_cut_check", scenario_s1_bspline_solved_area_and_cut_check),
        ("S2_jpeg_orthographic_and_matrix", scenario_s2_jpeg_orthographic_and_matrix),
        ("S3_region_interior_point_live", scenario_s3_region_interior_point_live),
    ):
        print(f"=== Running {name} ===", flush=True)
        report["scenarios"][name] = fn()
        print(f"=== PASSED {name} ===", flush=True)
    out = ROOT / "build" / "feedback0430_live_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Report written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
