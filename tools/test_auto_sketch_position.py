"""BUG-108 Creo 10 regression for automatic coordinate positioning."""

from __future__ import annotations

import argparse
import json
import math
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bridge  # noqa: E402
from creo_mechdog import generic_bridge as general  # noqa: E402
from tools.test_feedback0358_pattern_scope import git_commit_and_dirty, sha256_file, wait_job  # noqa: E402


def circle(y: float, *, x: float = 0, radius: float = 12, name: str = "pinion") -> dict:
    return {"type": "circle", "name": name, "center": [x, y], "radius": radius}


def sketch(label: str, *entities: dict, **options: object) -> dict:
    return {"op": "sketch", "label": label, "plane": "XY", "entities": list(entities), **options}


def replace(entity: dict, **options: object) -> dict:
    return {"op": "update_sketch_geometry", "sketch": "profile", "entities": [entity], **options}


def verify_cylinder(job: dict, y: float) -> None:
    inspection = job["native"]["inspection"]
    cylinders = [s for s in inspection["surfaces"] if s.get("radius") == 12.0]
    assert cylinders, job["job_id"]
    for surface in cylinders:
        assert math.isclose(surface["origin"][0], 0, abs_tol=1e-9), surface
        assert math.isclose(surface["origin"][1], y, abs_tol=1e-9), surface
    assert math.isclose(inspection["volume_mm3"], math.pi * 12**2 * 4, abs_tol=1e-6)


def verify_auto_coordinates(operation: dict) -> None:
    solver = operation["solver"]
    assert solver["requested"] == "auto" and solver["used"] == "coordinates", solver
    assert solver["selection_reason"] == "unconstrained_coordinate_profile", solver
    deviation = operation["geometry_deviation"]
    assert deviation["enforced"] is True and deviation["accepted_rigid"] is False, deviation
    assert deviation["warning_threshold_mm"] == 1e-5, deviation
    assert deviation["max_deviation_mm"] < 1e-9, deviation
    assert all(stage["available"] for stage in deviation["stages"].values()), deviation


def run(output: Path) -> None:
    session = bridge.session_status(connect_timeout_seconds=15)
    assert session["connected"], session
    report = {
        "session": session,
        "source": git_commit_and_dirty(),
        "worker_sha256": sha256_file(ROOT / "build/creo_worker.exe"),
        "worker_source_digest": (ROOT / "build/source.sha256").read_text().strip(),
        "jobs": {},
    }
    suffix = uuid.uuid4().hex[:7]

    def job(key, ops, prior=None, *, readonly=False, expected_status="succeeded"):
        if prior is None:
            accepted = general.submit(ops, model_name=f"b108_{key}_{suffix}")
        else:
            accepted = general.submit(
                ops,
                model_id=prior["model_id"],
                expected_revision=None if readonly else prior["revision"],
                readonly=readonly,
            )
        job_id = accepted["job_id"]
        terminal = wait_job(job_id)
        native = json.loads((ROOT / "jobs" / job_id / "native_result.json").read_text("utf-8"))
        model = general.model_info(accepted["model_id"])
        row = {
            "job_id": job_id,
            "model_id": accepted["model_id"],
            "input": ops,
            "revision": model["revision"],
            "part_file": model.get("part_file"),
            "status": terminal["status"],
            "message": terminal["message"],
            "native": native,
        }
        report["jobs"][key] = row
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(key, job_id, row["status"], row["message"], flush=True)
        assert row["status"] == expected_status, row["message"]
        if expected_status == "succeeded" and not readonly:
            assert native["saved_file_reloaded_and_verified"] is True
        return row

    created = job(
        "create",
        [
            sketch("profile", circle(-0.092)),
            {"op": "extrude", "label": "pin", "sketch": "profile", "depth": 4},
        ],
    )
    create_op = created["native"]["operations"][0]
    verify_auto_coordinates(create_op)
    verify_cylinder(job("read_create", [], created, readonly=True), -0.092)

    edited = job("replace", [replace(circle(-0.172))], created)
    edit_op = edited["native"]["operations"][0]
    verify_auto_coordinates(edit_op)
    assert edit_op["preserved_feature_id"] == create_op["feature_id"]
    saved = job("save_replace", [{"op": "save"}], edited)
    verify_cylinder(job("read_saved", [], saved, readonly=True), -0.172)
    checkpoint = Path(saved["part_file"])
    digest = sha256_file(checkpoint)

    # The solver snaps these nearly concentric circles together. A tighter
    # requested cap provides a repeatable native rejection witness.
    failed_create = job(
        "reject_create",
        [
            sketch(
                "near_concentric",
                circle(-0.092),
                circle(-0.092 + 4e-10, radius=5, name="inner"),
                geometry_tolerance_mm=1e-14,
            )
        ],
        saved,
        expected_status="failed",
    )
    # A different radius/offset has reproducible binary rounding in the
    # native replacement path. The cap is intentionally below that delta.
    failed_edit = job(
        "reject_replace",
        [
            replace(
                circle(-0.2375193835232428, x=0.1574953741852574, radius=12.789021345876786),
                geometry_tolerance_mm=1e-25,
            )
        ],
        saved,
        expected_status="failed",
    )
    for failure in (failed_create, failed_edit):
        native = failure["native"]
        deviation = native["operations"][0]["geometry_deviation"]
        assert deviation["available"] and deviation["enforced"] and deviation["exceeds_warning"]
        assert deviation["max_deviation_mm"] > deviation["warning_threshold_mm"]
        assert native["failed_operation"]["solver"]["used"] == "coordinates"
        assert native["operations"][0]["effect_status"] == "rolled_back"
        assert native["rollback_succeeded"] is True and failure["revision"] == saved["revision"]
        assert Path(failure["part_file"]) == checkpoint and sha256_file(checkpoint) == digest
        verify_cylinder(failure, -0.172)
    verify_cylinder(job("read_rollback", [], saved, readonly=True), -0.172)

    constrained = job(
        "dimensioned",
        [
            sketch(
                "profile",
                circle(-0.092),
                dimensions=[
                    {
                        "name": "rad",
                        "type": "radius",
                        "refs": [{"entity": "pinion"}],
                        "value": 12,
                    }
                ],
            )
        ],
    )
    route = constrained["native"]["operations"][0]["solver"]
    assert route["requested"] == "auto" and route["used"] == "autodim", route
    assert route["selection_reason"] == "supplied_dimensions_or_constraints", route


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "build/bug108_auto_sketch_position.json"
    )
    args = parser.parse_args()
    run(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
