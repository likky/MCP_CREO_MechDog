"""DEV-089 T2/T5 live acceptance: measured pose residual, driven follow, reload.

  python tools/test_t2_pose_residual.py --live --confirm-session-usable

Fixture: 60x40x10 base placed at x=+100 in a new assembly, 20x20x10 pin mated
to the base top face with mate_offset=5. The pin must end 5 mm above the face,
follow the base when it is moved, and keep that pose across the job's
save/reload verification.

Cases:
  A  mate_offset=5 measures a 5 mm gap            (residual <= 1e-6)
  B  moving the base to z=+20 moves the pin       (gap still 5 mm)
  C  the pin keeps z=35 right after the follow job   (assembly jobs expose no
     saved_file_reloaded_and_verified, so reload stays unverified)

Writes build/t2_pose_residual.json. No commit, version bump or release.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

TOLERANCE_MM = 1e-6


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


def block(width: float, height: float, depth: float) -> list[dict]:
    return [
        {
            "op": "sketch",
            "label": "profile",
            "plane": "XY",
            "entities": [
                {"type": "rectangle", "name": "box", "min": [0, 0], "max": [width, height]}
            ],
        },
        {"op": "extrude", "label": "solid", "sketch": "profile", "depth": depth},
    ]


def revision_of(generic_bridge, model_id: str) -> int:
    return int(generic_bridge.model_info(model_id).get("revision") or 0)


def section(generic_bridge, model_id: str, name: str) -> list[dict]:
    view = generic_bridge.inspect_model(model_id, detail="full", section=name, limit=200)
    data = view.get("data")
    if isinstance(data, dict) and isinstance(data.get(name), list):
        return data[name]
    return []


def submit(generic_bridge, model_id: str, operations: list[dict]) -> dict:
    accepted = generic_bridge.submit(
        operations, model_id=model_id, expected_revision=revision_of(generic_bridge, model_id)
    )
    return wait(accepted["job_id"])


def transform_of(generic_bridge, assembly_id: str, label: str) -> list[list[float]] | None:
    for component in section(generic_bridge, assembly_id, "components"):
        if label in (component.get("labels") or []):
            transform = component.get("transform")
            if isinstance(transform, list) and len(transform) == 4:
                return transform
    return None


def z_of(transform) -> float:
    return float(transform[3][2])


def run_live(generic_bridge) -> tuple[list[dict], bool]:
    cases: list[dict] = []
    stamp = str(int(time.time()))
    base_job = wait(
        generic_bridge.submit(block(60, 40, 10), model_name="t2_base_" + stamp)["job_id"]
    )
    pin_job = wait(generic_bridge.submit(block(20, 20, 10), model_name="t2_pin_" + stamp)["job_id"])
    cases.append(
        {
            "case": "fixture_parts",
            "pass": base_job.get("status") == pin_job.get("status") == "succeeded",
        }
    )
    if cases[-1]["pass"] is False:
        return cases, False

    assembly = wait(
        generic_bridge.submit([], model_name="t2_asm_" + stamp, model_type="assembly")["job_id"]
    )
    cases.append({"case": "fixture_assembly", "pass": assembly.get("status") == "succeeded"})
    if cases[-1]["pass"] is False:
        return cases, False
    assembly_id = assembly["model_id"]

    placed = submit(
        generic_bridge,
        assembly_id,
        [
            {
                "op": "assemble_component",
                "label": "base",
                "source_model_id": base_job["model_id"],
                "placement": "fixed",
                "translation": [100, 0, 0],
            }
        ],
    )
    cases.append({"case": "fixture_base", "pass": placed.get("status") == "succeeded"})
    if cases[-1]["pass"] is False:
        return cases, False

    pin_faces = section(generic_bridge, pin_job["model_id"], "surfaces")
    bottom = next(
        (
            face
            for face in pin_faces
            if isinstance(face.get("normal"), list)
            and abs(abs(face["normal"][2]) - 1.0) < 1e-6
            and isinstance(face.get("origin"), list)
            and abs(face["origin"][2]) < 1e-6
        ),
        None,
    )
    if bottom is None:
        cases.append({"case": "fixture_pin_bottom", "pass": False})
        return cases, False

    grounded = submit(
        generic_bridge,
        assembly_id,
        [
            {
                "op": "assemble_component",
                "label": "pin",
                "source_model_id": pin_job["model_id"],
                "placement": "constraints",
                "constraints": [
                    {
                        "type": "mate_offset",
                        "offset": 5,
                        "assembly_component": "base",
                        "assembly_reference": {
                            "kind": "geometry_selector",
                            "target": "surface",
                            "coordinate_space": "assembly",
                            "axis": [0.0, 0.0, 1.0],
                            "points_mm": [[130.0, 20.0, 10.0]],
                            "tolerance_mm": 1e-3,
                        },
                        "component_reference": {"kind": "surface", "id": bottom["id"]},
                    }
                ],
            }
        ],
    )
    pin_transform = transform_of(generic_bridge, assembly_id, "pin")
    gap = None if pin_transform is None else z_of(pin_transform) - 10.0
    cases.append(
        {
            "case": "A_offset_pose_residual",
            "job_id": grounded.get("job_id"),
            "status": grounded.get("status"),
            "measured_gap_mm": gap,
            "residual_mm": None if gap is None else abs(gap - 5.0),
            "pass": grounded.get("status") == "succeeded"
            and gap is not None
            and abs(gap - 5.0) <= TOLERANCE_MM,
        }
    )

    moved = submit(
        generic_bridge,
        assembly_id,
        [
            {
                "op": "component_placement",
                "component": "base",
                "translation": [100, 0, 20],
            }
        ],
    )
    followed = transform_of(generic_bridge, assembly_id, "pin")
    follow_gap = None if followed is None else z_of(followed) - 30.0
    cases.append(
        {
            "case": "B_driven_follow",
            "job_id": moved.get("job_id"),
            "status": moved.get("status"),
            "measured_gap_mm": follow_gap,
            "residual_mm": None if follow_gap is None else abs(follow_gap - 5.0),
            "saved_file_reloaded_and_verified": bool(
                (moved.get("validation") or {}).get("saved_file_reloaded_and_verified")
            ),
            "pass": moved.get("status") == "succeeded"
            and follow_gap is not None
            and abs(follow_gap - 5.0) <= TOLERANCE_MM,
        }
    )

    cases.append(
        {
            "case": "C_pose_after_follow",
            "transform_z_mm": None if followed is None else z_of(followed),
            # Assembly jobs do not expose saved_file_reloaded_and_verified, so this
            # is the live-session transform, not a reload proof.
            "reload_verified": False,
            "pass": followed is not None and abs(z_of(followed) - 35.0) <= 1e-3,
        }
    )
    return cases, all(case.get("pass") for case in cases)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-session-usable", action="store_true")
    args = parser.parse_args()
    if not args.live:
        print(json.dumps({"mode": "offline", "cases": ["A", "B", "C"]}))
        return 0
    if not args.confirm_session_usable:
        raise SystemExit("pass --confirm-session-usable after checking the live session")
    from creo_mechdog import generic_bridge

    cases, ok = run_live(generic_bridge)
    report = {"mode": "live", "creo": "12.4.0.0", "cases": cases, "passed": ok}
    target = ROOT / "build" / "t2_pose_residual.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
