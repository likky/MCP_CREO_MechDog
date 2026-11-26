"""DEV-089 T6b live acceptance: native direction (linear) pattern.

Offline run prints the planned cases. ``--live`` needs an explicit session
confirmation because it creates models and writes features in the running Creo
session:

  python tools/test_linear_pattern.py
  python tools/test_linear_pattern.py --live --confirm-session-usable

Case A : hole leader at x=10, direction +X, spacing 42, count 2  -> x=10 and 52
Case B : hole leader at x=52, same direction, flip=true          -> x=52 and 10
Case C : a direction that matches no model edge/face must be refused

Every instance is measured from the model's own cylindrical faces, not from the
request, and the pattern receipt's member count is cross-checked.
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


def hole_centers(generic_bridge, model_id: str, radius: float) -> list[list[float]]:
    centers: list[list[float]] = []
    for surface in section(generic_bridge, model_id, "surfaces"):
        if surface.get("type") is None or surface.get("radius") is None:
            continue
        if abs(float(surface["radius"]) - radius) > TOL:
            continue
        axis = surface.get("axis")
        if not isinstance(axis, list) or abs(abs(axis[2]) - 1.0) > TOL:
            continue
        origin = [float(value) for value in surface["origin"]]
        key = (round(origin[0], 6), round(origin[1], 6))
        if all((round(existing[0], 6), round(existing[1], 6)) != key for existing in centers):
            centers.append(origin)
    return sorted(centers, key=lambda point: point[0])


def fixture(generic_bridge, name: str, hole_x: float) -> tuple[str, dict]:
    operations = [
        {
            "op": "sketch",
            "label": "t6b_sk",
            "plane": "XY",
            "entities": [
                {"type": "rectangle", "name": "t6b_rect", "min": [0.0, 0.0], "max": [100.0, 30.0]}
            ],
        },
        {
            "op": "extrude",
            "label": "t6b_blk",
            "sketch": "t6b_sk",
            "depth": 10.0,
            "mode": "add",
            "direction": "positive",
            "depth_type": "blind",
        },
        {
            "op": "sketch",
            "label": "t6b_hole_sk",
            "plane": "XY",
            "entities": [
                {"type": "circle", "name": "t6b_circle", "center": [hole_x, 15.0], "radius": 2.0}
            ],
        },
        {
            "op": "extrude",
            "label": "t6b_hole",
            "sketch": "t6b_hole_sk",
            "depth": 20.0,
            "mode": "cut",
            "direction": "symmetric",
            "depth_type": "blind",
        },
    ]
    created = generic_bridge.submit(operations, model_name=name)
    job = wait(created["job_id"])
    return job.get("model_id") if job.get("status") == "succeeded" else "", job


def near(a: float, b: float) -> bool:
    return abs(a - b) <= TOL


def run_live(generic_bridge) -> tuple[list[dict], bool]:
    cases: list[dict] = []
    stamp = str(int(time.time()))

    for case, hole_x, flip, spacing, expected in (
        ("A_translation", 10.0, False, 42.0, [10.0, 52.0]),
        ("B_flip_reverses", 52.0, True, 42.0, [10.0, 52.0]),
    ):
        model_id, job = fixture(generic_bridge, f"t6b_{case}_{stamp}", hole_x)
        if not model_id:
            cases.append(
                {
                    "case": case,
                    "status": job.get("status"),
                    "message": str(job.get("message"))[:400],
                    "pass": False,
                }
            )
            continue
        before = hole_centers(generic_bridge, model_id, 2.0)
        pattern = submit(
            generic_bridge,
            model_id,
            [
                {
                    "op": "linear_pattern",
                    "label": "t6b_rows",
                    "leader": "t6b_hole",
                    "direction": [1.0, 0.0, 0.0],
                    "spacing": spacing,
                    "count": 2,
                    "flip": flip,
                }
            ],
        )
        after = hole_centers(generic_bridge, model_id, 2.0)
        detail = (pattern.get("result") or {}).get("operations") or []
        entry = detail[0] if detail else {}
        xs = [point[0] for point in after]
        cases.append(
            {
                "case": case,
                "job_id": pattern.get("job_id"),
                "status": pattern.get("status"),
                "message": str(pattern.get("message"))[:400],
                "leader_hole_x": hole_x,
                "holes_before": [point[0] for point in before],
                "holes_after": xs,
                "expected_holes": expected,
                "member_count": entry.get("member_count"),
                "direction_reference": entry.get("direction_reference"),
                "saved_file_reloaded_and_verified": (pattern.get("result") or {}).get(
                    "saved_file_reloaded_and_verified"
                ),
                "pass": pattern.get("status") == "succeeded"
                and len(xs) == len(expected)
                and all(near(a, b) for a, b in zip(xs, expected))
                and entry.get("member_count") == 2,
            }
        )

    # Case C: no model edge or face points along +Y on this fixture? The block
    # has edges along Y, so a genuinely unbound direction is a skew vector.
    model_id, job = fixture(generic_bridge, f"t6b_C_{stamp}", 10.0)
    if model_id:
        skew = [math.sqrt(0.5), 0.0, math.sqrt(0.5)]
        refused = submit(
            generic_bridge,
            model_id,
            [
                {
                    "op": "linear_pattern",
                    "label": "t6b_skew",
                    "leader": "t6b_hole",
                    "direction": skew,
                    "spacing": 20.0,
                    "count": 2,
                }
            ],
        )
        cases.append(
            {
                "case": "C_unbound_direction_refused",
                "job_id": refused.get("job_id"),
                "status": refused.get("status"),
                "message": str(refused.get("message"))[:400],
                "pass": refused.get("status") == "failed",
            }
        )
    else:
        cases.append({"case": "C_unbound_direction_refused", "pass": False})

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
    target = ROOT / "build" / "linear_pattern.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
