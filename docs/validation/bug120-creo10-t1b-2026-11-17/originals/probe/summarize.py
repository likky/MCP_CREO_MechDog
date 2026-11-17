"""Consolidate the T1-B matrix evidence into one machine-checkable table.

Every number below is read from an artifact that already exists on disk - the
probe result of the case, the in-session selection log, the adoption-verified
inspection snapshot and the measure job record - so the report never has to
trust a hand-copied value.

The case table maps a run to the two artifacts an independent reader needs:
  session_dir  - the probe case directory (request + result + steps)
  measure_job  - the creo_measure_surface_group job that produced the boundary

Run:  python probe/summarize.py
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent.parent

CASES = [
    {
        "case": "C3 两曲线（基线）",
        "session_dir": "work/c3_session",
        "measure_job": "7e7b3e91ae154d73939c7c1c47968cae",
        "model_id": "bbe390758d90455a8fb86e0eec39398a",
        "sections": 2,
        "expect_area": 800.0,
        "expect_perimeter": 120.0,
        "expect_bbox": [[0.0, 0.0, 0.0], [20.0, 40.0, 0.0]],
    },
    {
        "case": "A 新模型 + 新 ID",
        "session_dir": "work/a2_session",
        "measure_job": "9fa7d425e17147af9e1cfc4dd8b824e6",
        "model_id": "f65ac145ec544c04939755b55d89fa57",
        "sections": 2,
        "expect_area": 800.0,
        "expect_perimeter": 120.0,
        "expect_bbox": [[0.0, 0.0, 0.0], [20.0, 40.0, 0.0]],
    },
    {
        "case": "B 改视角（旋转 40°）",
        "session_dir": "work/b_session",
        "measure_job": "39d6c5cf4dc2431fad3b8ac29a903c5c",
        "model_id": "03ac1d7d835343778e2e484b872665b0",
        "sections": 2,
        "expect_area": 800.0,
        "expect_perimeter": 120.0,
        "expect_bbox": [[0.0, 0.0, 0.0], [20.0, 40.0, 0.0]],
    },
    {
        "case": "C 三截面",
        "session_dir": "work/c3_3sec",
        "measure_job": "0528917ac5b941068827e768f6a85f11",
        "model_id": "675adfafc2ff475c9714e6f7cde0550b",
        "sections": 3,
        "expect_area": 800.0,
        "expect_perimeter": 120.0,
        "expect_bbox": [[0.0, 0.0, 0.0], [20.0, 40.0, 0.0]],
    },
    {
        "case": "C 五截面",
        "session_dir": "work/c5_5sec",
        "measure_job": "23c4b7d95f9e48068b6f3d10e81a2bf1",
        "model_id": "4e85022c475849a2b0191b90019e8ee9",
        "sections": 5,
        "expect_area": 800.0,
        "expect_perimeter": 120.0,
        "expect_bbox": [[0.0, 0.0, 0.0], [20.0, 40.0, 0.0]],
    },
    {
        "case": "D 平移 + 加长",
        "session_dir": "work/d_session",
        "measure_job": "9cc885608c924eebb7c42d7c6396b8f0",
        "model_id": "5368401f83914d27ba1abe6bc772ffbb",
        "sections": 2,
        "expect_area": 1000.0,
        "expect_perimeter": 140.0,
        "expect_bbox": [[100.0, 30.0, 10.0], [120.0, 80.0, 10.0]],
    },
]

TOL = 0.01


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def session_selections(request_id: str) -> list[dict]:
    """Selection rows written by the in-session probe for this request."""
    rows = []
    log = ROOT / "probe" / "host" / "session_steps.jsonl"
    if not log.exists():
        return rows
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if entry.get("request_id") == request_id and entry.get("phase") == "select":
            rows.append(entry)
    return rows


def verified_quilt(model_id: str):
    pattern = str(REPO / "models" / model_id / "output" / "inspection-verified-*.json")
    for path in sorted(glob.glob(pattern)):
        data = read_json(Path(path))
        if not data:
            continue
        quilts = data.get("quilts") or []
        if quilts:
            return quilts[0], path
    return None, None


def verified_parents(model_id: str, feature_id):
    """Parent feature ids straight from the adoption-verified snapshot.

    The first run predates the probe's reference_parents field, so the snapshot
    is the source of truth whenever the live log has nothing to show.
    """
    pattern = str(REPO / "models" / model_id / "output" / "inspection-verified-*.json")
    for path in sorted(glob.glob(pattern)):
        data = read_json(Path(path))
        if not data:
            continue
        for feature in data.get("features") or []:
            if feature.get("id") == feature_id:
                return feature.get("parent_ids"), path
    return None, None


def measured_group(job_id: str):
    job = read_json(REPO / "jobs" / job_id / "job.json")
    if not job:
        return None
    for operation in job.get("result", {}).get("operations", []):
        group = operation.get("group")
        if group:
            return group
    return None


def bbox_close(actual, expected) -> bool:
    for got_row, want_row in zip(actual, expected):
        for got, want in zip(got_row, want_row):
            if got is None or abs(got - want) > TOL:
                return False
    return True


def main() -> int:
    rows = []
    for case in CASES:
        case_dir = ROOT / case["session_dir"]
        result = read_json(case_dir / "probe_result.json") or {}
        request = read_json(case_dir / "probe.json") or {}
        request_id = result.get("request_id") or request.get("request_id")

        quilt, quilt_source = verified_quilt(case["model_id"])
        group = measured_group(case["measure_job"])

        perimeter = None
        edges = []
        if group:
            edges = group.get("open_edge_records") or []
            lengths = [edge.get("length_mm") for edge in edges]
            if lengths and all(value is not None for value in lengths):
                perimeter = round(sum(lengths), 6)

        created = (result.get("features_created") or [{}])[0]
        parents = (created.get("reference_parents") or {}).get("parents") or []
        parents_source = "probe_live_feature_parents"
        if not parents and created.get("feature_id") is not None:
            parents, parents_file = verified_parents(case["model_id"], created.get("feature_id"))
            parents = parents or []
            parents_source = f"inspection_verified:{parents_file}"
        selections = session_selections(request_id)

        area = quilt.get("area_mm2") if quilt else None
        bbox = quilt.get("bbox_mm") if quilt else None
        bbox_deviation = None
        if bbox:
            bbox_deviation = max(
                abs(got - want)
                for got_row, want_row in zip(bbox, case["expect_bbox"])
                for got, want in zip(got_row, want_row)
            )
        row = {
            "case": case["case"],
            "request_id": request_id,
            "model": result.get("current_model"),
            "adopted_model_id": case["model_id"],
            "requested_sections": case["sections"],
            "requested_geometry_ids": [
                {"index": entry.get("index"), "owner": entry.get("owner"), "geom_id": entry.get("geom_id")}
                for entry in sorted(request.get("curves") or [], key=lambda item: item.get("index", 0))
            ],
            "selection_log": [
                {
                    "index": entry.get("index"),
                    "geom_id": entry.get("geom_id"),
                    "action": entry.get("selection_action"),
                    "error": entry.get("error"),
                }
                for entry in selections
            ],
            "created_feature": {
                "feature_id": created.get("feature_id"),
                "subtype": created.get("subtype"),
                "incomplete": created.get("incomplete"),
                "status": created.get("status"),
                "parent_feature_ids": parents,
                "parent_source": parents_source,
            },
            "quilt": {
                "quilt_id": quilt.get("quilt_id") if quilt else None,
                "area_mm2": area,
                "bbox_mm": bbox,
                "bbox_deviation_mm": bbox_deviation,
                "closed": quilt.get("closed") if quilt else None,
                "face_count": quilt.get("face_count") if quilt else None,
                "source": quilt_source,
            },
            "boundary": {
                "open_edges": group.get("open_edges") if group else None,
                "perimeter_mm": perimeter,
                "edge_lengths_mm": [edge.get("length_mm") for edge in edges],
                "state": group.get("state") if group else None,
                "measure_job": case["measure_job"],
            },
            "checks": {
                "parents_are_the_requested_sketches": parents == [
                    entry.get("feature_id") for entry in sorted(request.get("curves") or [], key=lambda item: item.get("index", 0))
                ],
                "every_selection_accepted": bool(selections) and all(entry.get("error") == 0 for entry in selections),
                "first_override_then_toggle": [entry.get("selection_action") for entry in selections]
                == ["PRO_SELECT_OVERRIDE"] + ["PRO_SELECT_TOGGLE"] * max(len(selections) - 1, 0),
                "area_ok": area is not None and abs(area - case["expect_area"]) <= TOL,
                "perimeter_ok": perimeter is not None and abs(perimeter - case["expect_perimeter"]) <= TOL,
                "bbox_ok": bbox is not None and bbox_close(bbox, case["expect_bbox"]),
                "single_open_quilt": bool(quilt) and quilt.get("face_count") == 1 and quilt.get("closed") is False,
                "feature_complete": created.get("incomplete") is False and created.get("status") == 0,
            },
            "expected": {
                "area_mm2": case["expect_area"],
                "perimeter_mm": case["expect_perimeter"],
                "bbox_mm": case["expect_bbox"],
            },
        }
        rows.append(row)

    output = ROOT / "evidence" / "matrix_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"tolerance_mm": TOL, "cases": rows}, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")

    header = f"{'case':26} {'sect':>4} {'area':>10} {'perim':>8} {'parents':22} {'checks'}"
    print(header)
    print("-" * len(header))
    for row in rows:
        checks = row["checks"]
        flags = "".join(
            [
                "P" if checks["parents_are_the_requested_sketches"] else "p",
                "S" if checks["every_selection_accepted"] else "s",
                "A" if checks["area_ok"] else "a",
                "L" if checks["perimeter_ok"] else "l",
                "B" if checks["bbox_ok"] else "b",
                "Q" if checks["single_open_quilt"] else "q",
                "F" if checks["feature_complete"] else "f",
            ]
        )
        failed = [name for name, ok in checks.items() if not ok]
        print(
            f"{row['case']:26} {row['requested_sections']:>4} "
            f"{row['quilt']['area_mm2'] if row['quilt']['area_mm2'] is not None else float('nan'):>10.4f} "
            f"{row['boundary']['perimeter_mm'] or float('nan'):>8.2f} "
            f"{str(row['created_feature']['parent_feature_ids']):22} {flags}"
            + (f"  <- {','.join(failed)}" if failed else "")
        )
    print(f"\nwritten: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
