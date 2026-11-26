"""DEV-089 T1 live acceptance: assembly-space (occurrence) geometry selectors.

  python tools/test_t1_occurrence_selector.py --live --confirm-session-usable

The fixture places a 60x40x10 base at x=+100 in the root assembly, then mates a
20x20x10 pin onto the base top face selected by **assembly coordinates**
(130,20,10). If the executor ignored the occurrence placement, that selector
would find nothing in the base's own frame and the job would fail.

Cases:
  A  assembly-space surface selector on the placed sibling   -> succeeded
  B  the same selector 40 mm off the plane                  -> refused
  C  assembly_space on the moving component_reference        -> refused

Writes build/t1_occurrence_selector.json. No commit, version bump or release.
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


def make_part(generic_bridge, name: str, width: float, height: float, depth: float) -> dict:
    accepted = generic_bridge.submit(block(width, height, depth), model_name=name)
    return wait(accepted["job_id"])


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


def surface_selector(point, axis=(0.0, 0.0, 1.0), space="assembly") -> dict:
    return {
        "kind": "geometry_selector",
        "target": "surface",
        "coordinate_space": space,
        "axis": list(axis),
        "points_mm": [list(point)],
        "tolerance_mm": 1e-3,
    }


def run_live(generic_bridge) -> tuple[list[dict], bool]:
    cases: list[dict] = []
    stamp = str(int(time.time()))
    base = make_part(generic_bridge, "t1_base_" + stamp, 60, 40, 10)
    pin = make_part(generic_bridge, "t1_pin_" + stamp, 20, 20, 10)
    for name, job in (("base", base), ("pin", pin)):
        cases.append(
            {
                "case": f"fixture_{name}",
                "job_id": job.get("job_id"),
                "status": job.get("status"),
                "pass": job.get("status") == "succeeded",
            }
        )
    if cases[-1]["pass"] is False or cases[-2]["pass"] is False:
        return cases, False

    created = generic_bridge.submit([], model_name="t1_asm_" + stamp, model_type="assembly")
    assembly_job = wait(created["job_id"])
    cases.append(
        {
            "case": "fixture_assembly",
            "job_id": created["job_id"],
            "status": assembly_job.get("status"),
            "pass": assembly_job.get("status") == "succeeded",
        }
    )
    if assembly_job.get("status") != "succeeded":
        return cases, False
    assembly_id = assembly_job["model_id"]

    placed = submit(
        generic_bridge,
        assembly_id,
        [
            {
                "op": "assemble_component",
                "label": "base",
                "source_model_id": base["model_id"],
                "placement": "fixed",
                "translation": [100, 0, 0],
            }
        ],
    )
    cases.append(
        {
            "case": "fixture_base_at_100",
            "job_id": placed.get("job_id"),
            "status": placed.get("status"),
            "pass": placed.get("status") == "succeeded",
        }
    )
    if placed.get("status") != "succeeded":
        return cases, False

    pin_faces = section(generic_bridge, pin["model_id"], "surfaces")
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
        cases.append({"case": "fixture_pin_bottom_face", "pass": False})
        return cases, False
    cases.append({"case": "fixture_pin_bottom_face", "id": bottom.get("id"), "pass": True})

    grounded = submit(
        generic_bridge,
        assembly_id,
        [
            {
                "op": "assemble_component",
                "label": "pin",
                "source_model_id": pin["model_id"],
                "placement": "constraints",
                "constraints": [
                    {
                        "type": "mate",
                        "assembly_component": "base",
                        "assembly_reference": surface_selector([130.0, 20.0, 10.0]),
                        "component_reference": {"kind": "surface", "id": bottom["id"]},
                    }
                ],
            }
        ],
    )
    cases.append(
        {
            "case": "A_assembly_space_selector_mate",
            "job_id": grounded.get("job_id"),
            "status": grounded.get("status"),
            "message": str(grounded.get("message"))[:300],
            "pass": grounded.get("status") == "succeeded",
        }
    )

    empty = submit(
        generic_bridge,
        assembly_id,
        [
            {
                "op": "assemble_component",
                "label": "pin_bad",
                "source_model_id": pin["model_id"],
                "placement": "constraints",
                "constraints": [
                    {
                        "type": "mate",
                        "assembly_component": "base",
                        "assembly_reference": surface_selector([130.0, 20.0, 50.0]),
                        "component_reference": {"kind": "surface", "id": bottom["id"]},
                    }
                ],
            }
        ],
    )
    cases.append(
        {
            "case": "B_assembly_space_selector_refused",
            "job_id": empty.get("job_id"),
            "status": empty.get("status"),
            "message": str(empty.get("message"))[:300],
            "pass": empty.get("status") == "failed",
        }
    )

    moving = submit(
        generic_bridge,
        assembly_id,
        [
            {
                "op": "assemble_component",
                "label": "pin_moving",
                "source_model_id": pin["model_id"],
                "placement": "constraints",
                "constraints": [
                    {
                        "type": "mate",
                        "assembly_component": "base",
                        "assembly_reference": surface_selector([130.0, 20.0, 10.0]),
                        "component_reference": surface_selector(
                            [110.0, 10.0, 0.0], axis=(0.0, 0.0, -1.0)
                        ),
                    }
                ],
            }
        ],
    )
    cases.append(
        {
            "case": "C_moving_component_assembly_space_refused",
            "job_id": moving.get("job_id"),
            "status": moving.get("status"),
            "message": str(moving.get("message"))[:300],
            "pass": moving.get("status") == "failed",
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
    target = ROOT / "build" / "t1_occurrence_selector.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
