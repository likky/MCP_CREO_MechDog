"""BUG-102: serial Creo regression for signed draft and pull reversal."""

from __future__ import annotations

import argparse
import json
import math
import sys
import uuid
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bridge  # noqa: E402
from creo_mechdog import generic_bridge as general  # noqa: E402
from tools.test_feedback0358_pattern_scope import git_commit_and_dirty, sha256_file, wait_job  # noqa: E402

RADIUS = 3.0
HEIGHT = 3.0
ANGLE = 11.0
CYLINDER = [
    {
        "op": "sketch",
        "label": "profile",
        "plane": "XY",
        "entities": [{"type": "circle", "name": "ring", "center": [0, 0], "radius": RADIUS}],
    },
    {"op": "extrude", "label": "boss", "sketch": "profile", "depth": HEIGHT},
]
PULL_AXIS = {
    "op": "datum_axis",
    "label": "pull_axis",
    "references": [{"kind": "datum_plane", "axis": axis} for axis in ("x", "y")],
}


def ring_radius(inspection: dict, z: float) -> float:
    arcs = [
        edge["arc"]
        for edge in inspection["edges"]
        if "arc" in edge and math.isclose(edge["arc"]["origin"][2], z, abs_tol=1e-7)
    ]
    assert arcs, inspection["edges"]
    radius = arcs[0]["radius"]
    for arc in arcs:
        assert math.hypot(*arc["origin"][:2]) < 1e-7, arc
        assert math.isclose(arc["radius"], radius, abs_tol=1e-7), arcs
    return radius


def measure_taper(inspection: dict, before_volume: float) -> dict:
    base = ring_radius(inspection, 0)
    free = ring_radius(inspection, HEIGHT)
    return {
        "neutral_radius_mm": base,
        "free_radius_mm": free,
        "signed_taper_deg": math.degrees(math.atan2(base - free, HEIGHT)),
        "material_delta_mm3": inspection["volume_mm3"] - before_volume,
    }


def verify_geometry(measured: dict, signed_angle: float) -> None:
    free_radius = RADIUS - HEIGHT * math.tan(math.radians(signed_angle))
    delta = math.pi * HEIGHT / 3 * (free_radius - RADIUS) * (free_radius + 2 * RADIUS)
    assert math.isclose(measured["neutral_radius_mm"], RADIUS, abs_tol=1e-7), measured
    assert math.isclose(measured["free_radius_mm"], free_radius, abs_tol=1e-7), measured
    assert math.isclose(measured["signed_taper_deg"], signed_angle, abs_tol=1e-7), measured
    # Creo's mass properties are numerical. Allow 0.01 mm³ around the exact frustum volume.
    assert math.isclose(measured["material_delta_mm3"], delta, abs_tol=0.01), measured


def run(output: Path, baseline: bool) -> None:
    assert not output.exists(), output
    session = bridge.session_status(connect_timeout_seconds=15)
    assert session["connected"] and int(session["release_numeric"]) == 42, session
    report = {
        "session": session,
        "source": git_commit_and_dirty(),
        "worker_sha256": sha256_file(ROOT / "build/creo_worker.exe"),
        "worker_source_digest": (ROOT / "build/source.sha256").read_text().strip(),
        "baseline": baseline,
        "cases": {},
    }
    suffix = uuid.uuid4().hex[:7]
    output.parent.mkdir(parents=True, exist_ok=True)

    def save_report():
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    def job(case, key, ops, prior=None, *, readonly=False):
        if prior is None:
            accepted = general.submit(ops, model_name=f"b102_{case}_{suffix}")
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
        row = {
            "input": ops,
            "job_id": job_id,
            "model_id": accepted["model_id"],
            "revision": general.model_info(accepted["model_id"])["revision"],
            "status": terminal["status"],
            "message": terminal["message"],
            "native": native,
        }
        report["cases"][case][key] = row
        save_report()
        assert row["status"] == "succeeded", row["message"]
        if not readonly:
            assert native["saved_file_reloaded_and_verified"] is True, job_id
        return row

    cases = [
        ("pos_base", ANGLE, False, "surface"),
        ("pos_rev", ANGLE, True, "surface"),
        ("neg_base", -ANGLE, False, "surface"),
        ("neg_rev", -ANGLE, True, "surface"),
    ]
    if not baseline:
        cases.extend(
            [
                ("datum_base", ANGLE, False, "datum_plane"),
                ("datum_rev", ANGLE, True, "datum_plane"),
                ("axis_base", ANGLE, False, "datum_axis"),
                ("axis_rev", ANGLE, True, "datum_axis"),
            ]
        )
    for case, angle, flip, mode in cases:
        use_axis = mode == "datum_axis"
        use_datum_plane = mode == "datum_plane"
        row = report["cases"][case] = {}
        created = job(case, "fixture", [*CYLINDER, PULL_AXIS] if use_axis else CYLINDER)
        before = created["native"]["inspection"]
        sides = [s["id"] for s in before["surfaces"] if s.get("radius") == RADIUS]
        bases = [
            s["id"] for s in before["surfaces"] if s.get("origin") == [0, 0, 0] and "normal" in s
        ]
        assert len(sides) == 2 and len(bases) == 1, before["surfaces"]
        if use_datum_plane:
            xy_planes = [
                p["id"]
                for p in before.get("datum_planes", [])
                if p.get("normal") == [0.0, 0.0, 1.0]
            ]
            assert xy_planes, before.get("datum_planes")
            neutral_ref = {"kind": "datum_plane", "id": xy_planes[0]}
        else:
            neutral_ref = {"kind": "surface", "id": bases[0]}
        draft = {
            "op": "draft",
            "label": "taper",
            "surfaces": [{"kind": "surface", "id": face} for face in sides],
            "neutral_plane": neutral_ref,
            "angle": angle,
        }
        if flip or baseline:
            draft["flip"] = flip
        reference_axis = [0.0, 0.0, 1.0]
        if use_axis:
            draft["pull_direction"] = {"kind": "datum_axis_feature", "label": "pull_axis"}
            axes = created["native"]["operations"][-1]["datum_axes"]
            assert len(axes) == 1 and axes[0]["geometry_known"], axes
            reference_axis = axes[0]["direction"]
            assert math.isclose(abs(reference_axis[2]), 1, abs_tol=1e-9), reference_axis
        drafted = job(case, "draft", [draft], created)
        native = drafted["native"]
        op = native["operations"][0]
        draft_geometry = op["draft_geometry"]
        compact = bridge.get_job(drafted["job_id"], detail="compact")
        full = bridge.get_job(drafted["job_id"], detail="full", section="operations_result")
        assert compact["result"]["operations"][0]["draft_geometry"] == draft_geometry
        assert full["data"]["operations_result"][0]["draft_geometry"] == draft_geometry
        row["after_save"] = measure_taper(native["inspection"], before["volume_mm3"])
        assert math.isclose(
            op["material_delta_mm3"], row["after_save"]["material_delta_mm3"], abs_tol=1e-7
        ), op
        readback = job(
            case, "reload", [{"op": "dump_tree", "feature": "taper"}], drafted, readonly=True
        )
        reload_native = readback["native"]
        tree = ElementTree.parse(reload_native["operations"][0]["file"])
        tree_side = int(tree.findtext(".//PRO_E_DIRECTION_COMPOUND/PRO_E_DIRECTION_FLIP", "0"))
        tree_angle = float(tree.findtext(".//PRO_E_DRAFT_SIDE_1/PRO_E_DRAFT_ANGLE_1", "nan"))
        row["after_reload"] = measure_taper(reload_native["inspection"], before["volume_mm3"])
        row["reloaded_tree"] = {"direction_flip_code": tree_side, "angle_deg": tree_angle}
        save_report()
        print(case, drafted["job_id"], row["after_reload"], draft_geometry, flush=True)

        side = -1 if flip else 1
        if baseline:
            side = -side
            assert draft_geometry["effective_flip"] is True, draft_geometry
        else:
            assert draft_geometry["effective_flip"] is flip and draft_geometry["flip"] is flip
            assert draft_geometry["direction_flip_code"] == side, draft_geometry
            assert draft_geometry["pull_vector"]["vector"] == reference_axis, draft_geometry
            if use_axis:
                assert draft_geometry["applied_pull_vector"] is None, draft_geometry
            else:
                assert draft_geometry["applied_pull_vector"] == [side * v for v in reference_axis]
        assert tree_side == side and tree_angle == angle, row["reloaded_tree"]
        assert draft_geometry["requested_flip"] is flip and draft_geometry["angle_deg"] == angle
        # Both the XY datum plane and explicit datum axis have opposite native pull side to the bottom solid face on Creo 10.
        expected_angle = angle * side * (-1 if (use_axis or use_datum_plane) else 1)
        expected_effect = "removed" if expected_angle > 0 else "added"
        assert compact["result"]["operations"][0]["material_effect"] == expected_effect, compact
        assert full["data"]["operations_result"][0]["material_effect"] == expected_effect, full
        verify_geometry(row["after_save"], expected_angle)
        verify_geometry(row["after_reload"], expected_angle)
        assert readback["revision"] == drafted["revision"] == created["revision"] + 1
    report["success"] = True
    save_report()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    run(args.output, args.baseline)
