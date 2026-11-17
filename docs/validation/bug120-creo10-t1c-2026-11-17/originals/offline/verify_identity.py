"""T1-C step 1: correlate the T1-B matrix claims with the original receipts.

The handoff audit only proves the 12 receipt files exist; it leaves
identity_verification=not_checked. This script closes that gap without
touching Creo:

  * copies the adoption inspect/apply/item job originals per adopted model
  * checks the measured quilt is the one created by the new feature
    (not "the first quilt in the file")
  * checks the measure job targets that same quilt id on that model
  * checks the apply job reports the reload/unchanged flags and hashes

Parent feature ids are treated only as a dependency set: their array order is
deliberately NOT compared against the request order.

Run:  python verify_identity.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

PACKAGE = Path(r"D:\my\MCP_CREO_MechDog\test_runs\2026-11-17_t1b_id_driven_blend")
REPO = Path(r"D:\my\MCP_CREO_MechDog")
OUT = Path(__file__).resolve().parent
ADOPTION_KINDS = ("adoption_file_inspect", "adoption_file", "adoption_file_item")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def find_jobs(model_id: str) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for job_json in sorted((REPO / "jobs").glob("*/job.json")):
        data = load(job_json)
        if not data or data.get("kind") not in ADOPTION_KINDS:
            continue
        if model_id not in json.dumps(data):
            continue
        kind = data.get("kind")
        # keep the earliest job of each kind: that is the adoption run, later
        # unrelated jobs of the same kind for the same model must not displace it
        if kind not in found:
            found[kind] = job_json.parent
    return found


def copy_job(src_dir: Path, target_dir: Path) -> list[dict]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in ("job.json", "batch.json"):
        source = src_dir / name
        if not source.is_file():
            continue
        target = target_dir / name
        shutil.copyfile(source, target)
        copied.append(
            {
                "file": target.relative_to(OUT).as_posix(),
                "bytes": target.stat().st_size,
                "sha256": digest(target),
                "source": str(source),
            }
        )
    return copied


def measure_targets(job: dict) -> list:
    """Requested references live on the input operations, the group only echoes ids."""
    targets = []
    for operation in job.get("operations") or []:
        for reference in operation.get("references") or []:
            targets.append(reference)
    for operation in job.get("result", {}).get("operations") or []:
        for quilt_id in (operation.get("group") or {}).get("quilt_ids") or []:
            targets.append({"kind": "quilt", "id": quilt_id, "from": "group_echo"})
    return targets


def main() -> int:
    matrix = load(PACKAGE / "evidence" / "matrix_summary.json")
    report = (PACKAGE / "T1B_REPORT.md").read_text(encoding="utf-8-sig")
    cases = matrix["cases"]

    rows = []
    for case in cases:
        model_id = case["adopted_model_id"]
        snapshot_rel = Path(case["quilt"]["source"].replace("\\", "/")).name
        snapshot_path = OUT / "receipts" / "models" / model_id / "output" / snapshot_rel
        snapshot = load(snapshot_path)
        measure_path = OUT / "receipts" / "jobs" / case["boundary"]["measure_job"] / "job.json"
        measure = load(measure_path)

        jobs = find_jobs(model_id)
        copied = {}
        for kind, src in jobs.items():
            copied[kind] = {
                "job_dir": src.name,
                "files": copy_job(src, OUT / "receipts" / "adoption" / model_id / src.name),
            }

        quilts = (snapshot or {}).get("quilts") or []
        target_quilt = next(
            (q for q in quilts if q.get("quilt_id") == case["quilt"]["quilt_id"]), None
        )
        feature_id = case["created_feature"]["feature_id"]
        quilt_feature_ids = (target_quilt or {}).get("feature_ids") or []

        apply_item = None
        apply_job = jobs.get("adoption_file")
        if apply_job:
            data = load(apply_job / "job.json")
            if data and data.get("items"):
                apply_item = data["items"][0]

        targets = measure_targets(measure or {})
        quilt_targets = [t for t in targets if t.get("kind") == "quilt"]
        edges = []
        for operation in (measure or {}).get("result", {}).get("operations", []):
            group = operation.get("group") or {}
            edges.extend(group.get("open_edge_records") or [])

        # Trimmed-boundary extremes straight from the recorded edge endpoints.
        # This is what the 0.12 mm question needs: the quilt bbox is the union of
        # per-surface ProSurfaceDataGet ranges (native/quilt_query.h), not this.
        points = [p for e in edges for p in (e.get("endpoints_mm") or [])]
        lo = [min(p[i] for p in points) for i in range(3)] if points else None
        hi = [max(p[i] for p in points) for i in range(3)] if points else None
        expected_box = case["expected"]["bbox_mm"]
        boundary_exact = bool(points) and all(
            abs(v - expected_box[i][a]) <= 1e-6 for i, row in enumerate((lo, hi)) for a, v in enumerate(row)
        )
        margin = None
        if points and case["quilt"]["bbox_mm"]:
            qbox = case["quilt"]["bbox_mm"]
            margin = {
                "min": [round(qbox[0][i] - lo[i], 6) for i in range(3)],
                "max": [round(qbox[1][i] - hi[i], 6) for i in range(3)],
            }

        input_sha = ((apply_item or {}).get("file") or {}).get("sha256")
        row = {
            "case": case["case"],
            "model": case["model"],
            "adopted_model_id": model_id,
            "snapshot": {
                "file": f"receipts/models/{model_id}/output/{snapshot_rel}",
                "present": snapshot is not None,
                "quilt_count": len(quilts),
                "matrix_quilt_id": case["quilt"]["quilt_id"],
                "quilt_id_found": target_quilt is not None,
                "area_mm2": (target_quilt or {}).get("area_mm2"),
                "bbox_mm": (target_quilt or {}).get("bbox_mm"),
                "quilt_feature_ids": quilt_feature_ids,
                "matrix_created_feature_id": feature_id,
                "quilt_belongs_to_new_feature": feature_id in quilt_feature_ids,
                "picked_by_first_quilt": bool(quilts)
                and quilts[0].get("quilt_id") == case["quilt"]["quilt_id"],
            },
            "measure": {
                "job": case["boundary"]["measure_job"],
                "present": measure is not None,
                "job_model_id": (measure or {}).get("model_id"),
                "job_matches_model": (measure or {}).get("model_id") == model_id,
                "quilt_targets": quilt_targets,
                "targets_matrix_quilt": bool(quilt_targets)
                and all(t.get("id") == case["quilt"]["quilt_id"] for t in quilt_targets),
                "open_edges": len(edges),
                "edge_lengths_mm": [e.get("length_mm") for e in edges],
                "edge_endpoints_mm": [e.get("endpoints_mm") for e in edges],
                "trimmed_min_mm": lo,
                "trimmed_max_mm": hi,
                "trimmed_matches_expected_box": boundary_exact,
                "perimeter_mm": round(sum(e.get("length_mm") or 0 for e in edges), 6)
                if edges
                else None,
            },
            "bbox_question": {
                "quilt_bbox_mm": case["quilt"]["bbox_mm"],
                "trimmed_min_mm": lo,
                "trimmed_max_mm": hi,
                "margin_mm": margin,
                "bbox_source": "union of ProSurfaceDataGet xyz_min/xyz_max per surface "
                "(native/quilt_query.h:57-67)",
                "flat_area_if_margin_were_geometry_mm2": round(
                    ((hi[0] - lo[0]) + margin["max"][0] - margin["min"][0])
                    * ((hi[1] - lo[1]) + margin["max"][1] - margin["min"][1]),
                    6,
                )
                if margin
                else None,
                "measured_area_mm2": case["quilt"]["area_mm2"],
            },
            "adoption": {
                kind: {"job_dir": info["job_dir"], "files": info["files"]}
                for kind, info in copied.items()
            },
            "apply": {
                "job_dir": apply_job.name if apply_job else None,
                "display_name": ((apply_item or {}).get("source") or {}).get("display_name"),
                "display_name_matches_matrix": ((apply_item or {}).get("source") or {}).get(
                    "display_name", ""
                ).casefold()
                == str(case["model"]).casefold(),
                "saved_file_reloaded_and_verified": ((apply_item or {}).get("result") or {}).get(
                    "saved_file_reloaded_and_verified"
                ),
                "source_unchanged": ((apply_item or {}).get("result") or {}).get(
                    "source_unchanged"
                ),
                "window_unchanged": ((apply_item or {}).get("result") or {}).get(
                    "window_unchanged"
                ),
                "inspection_warnings": (apply_item or {}).get("inspection_warnings"),
                "input_sha256": input_sha,
                "input_sha_in_report": bool(input_sha and input_sha in report),
            },
        }
        row["identity_ok"] = all(
            [
                row["snapshot"]["quilt_id_found"],
                row["snapshot"]["quilt_belongs_to_new_feature"],
                row["measure"]["job_matches_model"],
                row["measure"]["targets_matrix_quilt"],
                row["apply"]["display_name_matches_matrix"],
                row["apply"]["saved_file_reloaded_and_verified"] is True,
                row["apply"]["source_unchanged"] is True,
                row["apply"]["input_sha_in_report"],
            ]
        )
        rows.append(row)

    result = {
        "scope": "receipt identity correlation; no geometry recomputation from Creo",
        "note": (
            "parent feature ids are a dependency set only; array order is not treated "
            "as collector order anywhere in this audit"
        ),
        "cases": rows,
        "all_identity_ok": all(r["identity_ok"] for r in rows),
    }
    (OUT / "identity_checks.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"{'case':22} {'quilt':>6} {'newfeat?':>9} {'job→quilt':>10} {'reload':>7} {'unchgd':>7} ok")
    for row in rows:
        print(
            f"{row['case']:22} {row['snapshot']['matrix_quilt_id']:>6} "
            f"{str(row['snapshot']['quilt_belongs_to_new_feature']):>9} "
            f"{str(row['measure']['targets_matrix_quilt']):>10} "
            f"{str(row['apply']['saved_file_reloaded_and_verified']):>7} "
            f"{str(row['apply']['source_unchanged']):>7} {row['identity_ok']}"
        )
    print(f"\nall_identity_ok={result['all_identity_ok']}")
    print(f"written: {OUT / 'identity_checks.json'}")
    return 0 if result["all_identity_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
