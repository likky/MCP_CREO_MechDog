"""DEV-089 T6a / FEAT-071 live acceptance: angle and two-distance chamfers.

Offline run prints the planned cases. ``--live`` needs an explicit session
confirmation because it creates models and writes features in the running Creo
session:

  python tools/test_chamfer_angle.py
  python tools/test_chamfer_angle.py --live --confirm-session-usable

Distance-angle fixture: 50 x 30 x 10 mm block, chamfer the top/front edge
(y=0, z=10) with distance 3 mm and angle 70 deg, taking the angle from the top
face (z=10).

Two-distance fixture: the same block and edge with chamfer_type="d1_d2",
distance_1/distance_2 swapped between two runs and the top face as the explicit
reference_surface. Both legs must appear on the block and the removed material
must match 0.5*d1*d2*50; which face receives D1 is recorded as an observation,
not assumed.

The result is read from the created geometry, not from the request: the new
inclined planar face is located, its bounding box gives the two leg lengths and
its normal gives the dihedral angle. The probe therefore decides whether the
angle and the distance were applied to the reference face the request names.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

TOL = 1e-4
BLOCK = [50.0, 30.0, 10.0]
DISTANCE = 3.0
ANGLE_DEG = 70.0
D1_MM = 2.0
D2_MM = 5.0


def wait(job_id: str, timeout: float = 300.0) -> dict:
    terminal = {"succeeded", "failed", "aborted", "cancelled"}
    deadline = time.time() + timeout
    record: dict = {}
    while time.time() < deadline:
        path = ROOT / "jobs" / job_id / "job.json"
        if path.is_file():
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("status") in terminal:
                return record
        time.sleep(1.0)
    raise SystemExit(f"job {job_id} did not reach a terminal state: {record.get('status')}")


def revision_of(generic_bridge, model_id: str) -> int:
    return int(generic_bridge.model_info(model_id).get("revision") or 0)


def section(generic_bridge, model_id: str, name: str) -> list[dict]:
    view = generic_bridge.inspect_model(model_id, detail="full", section=name, limit=200)
    data = view.get("data")
    if isinstance(data, dict):
        for key in (name, "items", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    if isinstance(data, list):
        return data
    return []


def submit(generic_bridge, model_id: str, operations: list[dict]) -> dict:
    accepted = generic_bridge.submit(
        operations, model_id=model_id, expected_revision=revision_of(generic_bridge, model_id)
    )
    return wait(accepted["job_id"])


def fixture(generic_bridge, name: str) -> tuple[str, dict]:
    operations = [
        {
            "op": "sketch",
            "label": "t6a_sk",
            "plane": "XY",
            "entities": [
                {
                    "type": "rectangle",
                    "name": "t6a_rect",
                    "min": [0.0, 0.0],
                    "max": [BLOCK[0], BLOCK[1]],
                }
            ],
        },
        {
            "op": "extrude",
            "label": "t6a_blk",
            "sketch": "t6a_sk",
            "depth": BLOCK[2],
            "mode": "add",
            "direction": "positive",
            "depth_type": "blind",
        },
    ]
    created = generic_bridge.submit(operations, model_name=name)
    job = wait(created["job_id"])
    return job.get("model_id") if job.get("status") == "succeeded" else "", job


def inclined_faces(generic_bridge, model_id: str) -> list[dict]:
    faces = []
    for surface in section(generic_bridge, model_id, "surfaces"):
        normal = surface.get("normal")
        if not isinstance(normal, list):
            continue
        axis_aligned = (
            any(abs(abs(component) - 1.0) <= 1e-6 for component in normal)
            and sum(abs(component) <= 1e-6 for component in normal) == 2
        )
        if axis_aligned:
            continue
        faces.append(surface)
    return faces


def run_case(generic_bridge, name: str, reference_axis: list[float], reference_point: list[float]):
    cases: list[dict] = []
    model_id, job = fixture(generic_bridge, name)
    if not model_id:
        return (
            [
                {
                    "case": "fixture_block",
                    "status": job.get("status"),
                    "message": str(job.get("message"))[:400],
                    "pass": False,
                }
            ],
            False,
        )
    before_volume = generic_bridge.get_mass_properties(model_id).get("volume_mm3")
    distance_angle = submit(
        generic_bridge,
        model_id,
        [
            {
                "op": "chamfer",
                "label": "t6a_bevel",
                "size": DISTANCE,
                "chamfer_type": "distance_angle",
                "angle_deg": ANGLE_DEG,
                "references": [
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "endpoints_mm": [[0.0, 0.0, BLOCK[2]], [BLOCK[0], 0.0, BLOCK[2]]],
                            "tolerance_mm": 0.001,
                        }
                    }
                ],
                "angle_reference": {
                    "kind": "geometry_selector",
                    "target": "surface",
                    "axis": reference_axis,
                    "points_mm": [reference_point],
                    "tolerance_mm": 0.001,
                },
            }
        ],
    )
    entry = ((distance_angle.get("result") or {}).get("operations") or [{}])[0]
    after_volume = (
        generic_bridge.get_mass_properties(model_id).get("volume_mm3")
        if distance_angle.get("status") == "succeeded"
        else None
    )
    faces = (
        inclined_faces(generic_bridge, model_id)
        if distance_angle.get("status") == "succeeded"
        else []
    )
    measured = []
    for face in faces:
        measured.append(
            {"id": face.get("id"), "normal": face.get("normal"), "bbox": face.get("bbox")}
        )
    passed = False
    detail = {}
    if measured:
        face = measured[0]
        low, high = face["bbox"]
        normal = face["normal"]
        legs = {"y": high[1] - low[1], "z": high[2] - low[2]}
        # Dihedral angle to the face the request named: the chamfer face normal
        # and the reference normal form the same angle as the two planes.
        radians = math.acos(
            max(-1.0, min(1.0, abs(sum(a * b for a, b in zip(normal, reference_axis)))))
        )
        expected_long = DISTANCE * math.tan(math.radians(ANGLE_DEG))
        # The reference face keeps the 3 mm leg; the perpendicular face gets the
        # leg that follows from the angle.
        reference_is_top = abs(reference_axis[2]) > 0.5
        distance_leg = legs["y"] if reference_is_top else legs["z"]
        angle_leg = legs["z"] if reference_is_top else legs["y"]
        removed = None
        if isinstance(before_volume, (int, float)) and isinstance(after_volume, (int, float)):
            removed = float(before_volume) - float(after_volume)
        detail = {
            "reference_axis": reference_axis,
            "distance_leg_mm": distance_leg,
            "angle_leg_mm": angle_leg,
            "expected_distance_leg_mm": DISTANCE,
            "expected_angle_leg_mm": expected_long,
            "dihedral_deg_from_normals": math.degrees(radians),
            "material_removed_mm3": removed,
            "expected_material_removed_mm3": 0.5 * DISTANCE * expected_long * BLOCK[0],
        }
        passed = (
            abs(distance_leg - DISTANCE) <= 1e-3
            and abs(angle_leg - expected_long) <= 1e-2
            and abs(math.degrees(radians) - ANGLE_DEG) <= 1e-2
            and (removed is None or abs(removed - detail["expected_material_removed_mm3"]) <= 1.0)
        )
    cases.append(
        {
            "case": "A_distance_angle_top_reference"
            if abs(reference_axis[2]) > 0.5
            else "B_distance_angle_side_reference",
            "job_id": distance_angle.get("job_id"),
            "status": distance_angle.get("status"),
            "message": str(distance_angle.get("message"))[:600],
            "receipt": {
                "chamfer_type": entry.get("chamfer_type"),
                "angle_deg": entry.get("angle_deg"),
                "size": entry.get("size"),
                "reference_application": entry.get("reference_application"),
            },
            "inclined_faces": measured,
            "detail": detail,
            "saved_file_reloaded_and_verified": (distance_angle.get("result") or {}).get(
                "saved_file_reloaded_and_verified"
            ),
            "pass": passed,
        }
    )
    return cases, passed


def run_two_distance_case(
    generic_bridge, name: str, distance_1: float, distance_2: float
) -> tuple[list[dict], bool]:
    """FEAT-071: both legs must land on the block, D1/D2 assignment recorded."""
    cases: list[dict] = []
    model_id, job = fixture(generic_bridge, name)
    if not model_id:
        return (
            [
                {
                    "case": "fixture_block_two_distance",
                    "status": job.get("status"),
                    "message": str(job.get("message"))[:400],
                    "pass": False,
                }
            ],
            False,
        )
    before_volume = generic_bridge.get_mass_properties(model_id).get("volume_mm3")
    receipt = submit(
        generic_bridge,
        model_id,
        [
            {
                "op": "chamfer",
                "label": "t6b_bevel",
                "chamfer_type": "d1_d2",
                "distance_1": distance_1,
                "distance_2": distance_2,
                "references": [
                    {
                        "edge": {
                            "kind": "geometry_selector",
                            "target": "edge",
                            "endpoints_mm": [[0.0, 0.0, BLOCK[2]], [BLOCK[0], 0.0, BLOCK[2]]],
                            "tolerance_mm": 0.001,
                        }
                    }
                ],
                "reference_surface": {
                    "kind": "geometry_selector",
                    "target": "surface",
                    "axis": [0.0, 0.0, 1.0],
                    "points_mm": [[BLOCK[0] / 2, BLOCK[1] / 2, BLOCK[2]]],
                    "tolerance_mm": 0.001,
                },
            }
        ],
    )
    entry = ((receipt.get("result") or {}).get("operations") or [{}])[0]
    succeeded = receipt.get("status") == "succeeded"
    after_volume = (
        generic_bridge.get_mass_properties(model_id).get("volume_mm3") if succeeded else None
    )
    faces = inclined_faces(generic_bridge, model_id) if succeeded else []
    measured = [
        {"id": face.get("id"), "normal": face.get("normal"), "bbox": face.get("bbox")}
        for face in faces
    ]
    expected_removed = 0.5 * distance_1 * distance_2 * BLOCK[0]
    legs: dict[str, float] = {}
    removed = None
    passed = False
    if measured:
        low, high = measured[0]["bbox"]
        legs = {"y": high[1] - low[1], "z": high[2] - low[2]}
        if isinstance(before_volume, (int, float)) and isinstance(after_volume, (int, float)):
            removed = float(before_volume) - float(after_volume)
        expected_legs = sorted([distance_1, distance_2])
        observed_legs = sorted(legs.values())
        passed = (
            all(abs(a - b) <= 1e-3 for a, b in zip(observed_legs, expected_legs))
            and (removed is None or abs(removed - expected_removed) <= 1.0)
            and (receipt.get("result") or {}).get("saved_file_reloaded_and_verified") is True
        )
    cases.append(
        {
            "case": f"two_distance_d1_{distance_1:g}_d2_{distance_2:g}",
            "job_id": receipt.get("job_id"),
            "status": receipt.get("status"),
            "message": str(receipt.get("message"))[:600],
            "receipt": {
                "chamfer_type": entry.get("chamfer_type"),
                "distance_1": entry.get("distance_1"),
                "distance_2": entry.get("distance_2"),
                "reference_application": entry.get("reference_application"),
            },
            "leg_assignment": {"front_face_y_mm": legs.get("y"), "top_face_z_mm": legs.get("z")},
            "material_removed_mm3": removed,
            "expected_material_removed_mm3": expected_removed,
            "inclined_faces": measured,
            "saved_file_reloaded_and_verified": (receipt.get("result") or {}).get(
                "saved_file_reloaded_and_verified"
            ),
            "pass": passed,
        }
    )
    return cases, passed


def run_live(generic_bridge) -> tuple[list[dict], bool]:
    stamp = str(int(time.time()))
    first, first_ok = run_case(
        generic_bridge,
        f"t6a_top_{stamp}",
        [0.0, 0.0, 1.0],
        [BLOCK[0] / 2, BLOCK[1] / 2, BLOCK[2]],
    )
    second, second_ok = run_case(
        generic_bridge,
        f"t6a_side_{stamp}",
        [0.0, -1.0, 0.0],
        [BLOCK[0] / 2, 0.0, BLOCK[2] / 2],
    )
    third, third_ok = run_two_distance_case(generic_bridge, f"t6b_d1d2_{stamp}", D1_MM, D2_MM)
    fourth, fourth_ok = run_two_distance_case(generic_bridge, f"t6b_d2d1_{stamp}", D2_MM, D1_MM)
    cases = first + second + third + fourth
    return cases, first_ok and second_ok and third_ok and fourth_ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-session-usable", action="store_true")
    args = parser.parse_args()
    if not args.live:
        print(
            json.dumps(
                {
                    "mode": "offline",
                    "cases": [
                        "A_distance_angle",
                        "two_distance_d1_2_d2_5",
                        "two_distance_d1_5_d2_2",
                    ],
                }
            )
        )
        return 0
    if not args.confirm_session_usable:
        raise SystemExit("pass --confirm-session-usable after checking the live session")
    from creo_mechdog import generic_bridge

    cases, ok = run_live(generic_bridge)
    health = ROOT / "build" / "toolkit_health.json"
    host = (
        json.loads(health.read_text(encoding="utf-8")).get("host_release")
        if health.is_file()
        else None
    )
    report = {"mode": "live", "host_release": host, "cases": cases, "passed": ok}
    target = ROOT / "build" / "chamfer_angle.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
