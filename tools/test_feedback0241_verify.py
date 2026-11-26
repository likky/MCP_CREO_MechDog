"""DEV-089 live acceptance driver: geometric anchors and symbol-targeted dimensions.

Default run is offline and only prints the planned cases. ``--live`` needs an
explicit session confirmation because it creates models and writes features in
the running Creo session:

  python tools/test_feedback0241_verify.py
  python tools/test_feedback0241_verify.py --live --confirm-session-usable

Live cases (one 50x30x10 block fixture):
  A  round on an edge selected by {kind:'geometry_selector',target:'edge'}
  B  the same selector with far-away endpoints must be refused, not guessed
  C  chamfer whose two faces are selected by surface geometry selectors
  D  set_dimensions by {feature:<owner id>,symbol:<Creo symbol>}
  E  a wrong symbol must be refused

No commit, version bump or release is performed.
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

FIXTURE = [
    {
        "op": "sketch",
        "label": "dev089_sk",
        "plane": "XY",
        "entities": [
            {"type": "rectangle", "name": "dev089_rect", "min": [0.0, 0.0], "max": [50.0, 30.0]}
        ],
    },
    {
        "op": "extrude",
        "label": "dev089_blk",
        "sketch": "dev089_sk",
        "depth": 10.0,
        "mode": "add",
        "direction": "positive",
        "depth_type": "blind",
    },
]


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


def record(cases, name, job, expected):
    status = job.get("status")
    message = str(job.get("message") or "")
    cases.append(
        {
            "case": name,
            "job_id": job.get("job_id"),
            "status": status,
            "expected": expected,
            "message": message[:400],
            "pass": status == expected if isinstance(expected, str) else status in expected,
        }
    )


def run_live(generic_bridge) -> tuple[list[dict], bool]:
    cases: list[dict] = []
    created = generic_bridge.submit(FIXTURE, model_name="dev089_" + str(int(time.time())))
    job = wait(created["job_id"])
    record(cases, "fixture_block", job, "succeeded")
    if job.get("status") != "succeeded":
        return cases, False
    model_id = job["model_id"]

    edges = [
        edge
        for edge in section(generic_bridge, model_id, "edges")
        if isinstance(edge.get("start"), list) and isinstance(edge.get("end"), list)
    ]
    if not edges:
        cases.append({"case": "fixture_edges", "pass": False, "message": "no straight edges"})
        return cases, False
    edge = edges[0]
    selector = {
        "kind": "geometry_selector",
        "target": "edge",
        "endpoints_mm": [edge["start"], edge["end"]],
        "tolerance_mm": 1e-3,
    }
    cases.append({"case": "edge_selector_input", "edge_id": edge.get("id"), "pass": True})

    record(
        cases,
        "A_edge_selector_round",
        submit(
            generic_bridge,
            model_id,
            [
                {
                    "op": "round",
                    "label": "dev089_r1",
                    "size": 2.0,
                    "references": [{"edge": selector}],
                }
            ],
        ),
        "succeeded",
    )

    bad = dict(selector, endpoints_mm=[[1000.0, 0.0, 0.0], [1000.0, 0.0, 10.0]])
    record(
        cases,
        "B_edge_selector_refused",
        submit(
            generic_bridge,
            model_id,
            [{"op": "round", "label": "dev089_r2", "size": 2.0, "references": [{"edge": bad}]}],
        ),
        "failed",
    )

    surfaces = section(generic_bridge, model_id, "surfaces")
    top = next(
        (
            s
            for s in surfaces
            if isinstance(s.get("normal"), list) and abs(s["normal"][2] - 1.0) < 1e-6
        ),
        None,
    )
    side = next(
        (
            s
            for s in surfaces
            if isinstance(s.get("normal"), list) and abs(abs(s["normal"][0]) - 1.0) < 1e-6
        ),
        None,
    )
    if top and side:

        def face(selector_axis, point):
            return {
                "kind": "geometry_selector",
                "target": "surface",
                "axis": selector_axis,
                "points_mm": [point],
                "tolerance_mm": 1e-3,
            }

        record(
            cases,
            "C_surface_selector_chamfer",
            submit(
                generic_bridge,
                model_id,
                [
                    {
                        "op": "chamfer",
                        "label": "dev089_c1",
                        "size": 2.0,
                        "references": [
                            {
                                "surfaces": [
                                    face([0.0, 0.0, 1.0], [25.0, 15.0, 10.0]),
                                    face([1.0, 0.0, 0.0], [50.0, 15.0, 5.0]),
                                ]
                            }
                        ],
                    }
                ],
            ),
            "succeeded",
        )
    else:
        cases.append({"case": "C_surface_selector_chamfer", "pass": False, "message": "no planes"})

    dimensions = section(generic_bridge, model_id, "dimensions")
    depth = next(
        (
            d
            for d in dimensions
            if d.get("symbol")
            and type(d.get("owner_feature_id")) is int
            and abs(float(d.get("value") or 0) - 10.0) < 1e-6
        ),
        None,
    )
    if depth:
        cases.append({"case": "symbol_dimension_input", "symbol": depth["symbol"], "pass": True})
        record(
            cases,
            "D_symbol_dimension_edit",
            submit(
                generic_bridge,
                model_id,
                [
                    {
                        "op": "set_dimensions",
                        "values": [
                            {
                                "feature": depth["owner_feature_id"],
                                "symbol": depth["symbol"],
                                "value": 12.0,
                            }
                        ],
                    }
                ],
            ),
            "succeeded",
        )
        after = next(
            (
                d
                for d in section(generic_bridge, model_id, "dimensions")
                if d.get("id") == depth.get("id")
            ),
            None,
        )
        cases.append(
            {
                "case": "D_symbol_dimension_value",
                "value": (after or {}).get("value"),
                "pass": after is not None and abs(float(after.get("value") or 0) - 12.0) < 1e-6,
            }
        )
        record(
            cases,
            "E_wrong_symbol_refused",
            submit(
                generic_bridge,
                model_id,
                [
                    {
                        "op": "set_dimensions",
                        "values": [
                            {
                                "feature": depth["owner_feature_id"],
                                "symbol": "dev089_no_symbol",
                                "value": 12.0,
                            }
                        ],
                    }
                ],
            ),
            "failed",
        )
    else:
        cases.append({"case": "symbol_dimension_input", "pass": False, "message": "none"})

    return cases, all(case.get("pass") for case in cases)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-session-usable", action="store_true")
    args = parser.parse_args()
    if not args.live:
        print(json.dumps({"mode": "offline", "cases": ["A", "B", "C", "D", "E"]}))
        return 0
    if not args.confirm_session_usable:
        raise SystemExit("pass --confirm-session-usable after checking the live session")
    from creo_mechdog import generic_bridge

    cases, ok = run_live(generic_bridge)
    report = {"mode": "live", "creo": "12.4.0.0", "cases": cases, "passed": ok}
    target = ROOT / "build" / "feedback0241_verify.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
