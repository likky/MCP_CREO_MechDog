"""Offline audit of the BUG-120 T1-B handoff package; never invokes Creo.

The matrix and its geometry fields are claims until original inspection and job
receipts are supplied. Receipt collection copies only fixed, validated paths.
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

HEX_ID = re.compile(r"[0-9a-f]{32}\Z", re.I)
SNAPSHOT = re.compile(r"inspection-verified-[0-9a-f]+\.json\Z", re.I)
PRT_ROW = re.compile(
    r"\|[^\n]*?\|\s*`(work/[^`]+\.prt\.\d+)`\s*\|\s*([\d,]+)\s*\|\s*`([0-9a-f]{64})`\s*\|\s*`([0-9a-f]{32})`\s*\|",
    re.I,
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def contained(root, relative):
    """Reject links and traversal, including links in parent components."""
    root = root.resolve(strict=True)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe relative path: {relative}")
    path = root / relative
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise ValueError(f"symlink in path: {path}")
    if not path.resolve(strict=False).is_relative_to(root):
        raise ValueError(f"path escapes root: {path}")
    return path


def jsonl(path):
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def select_checks(case, steps):
    request_id = case["request_id"]
    refs = case["requested_geometry_ids"]
    observed = [
        s for s in steps if s.get("request_id") == request_id and s.get("phase") == "select"
    ]
    expected = [
        (
            ref["index"],
            str(ref["owner"]).casefold(),
            ref["geom_id"],
            "PRO_SELECT_OVERRIDE" if i == 0 else "PRO_SELECT_TOGGLE",
            0,
        )
        for i, ref in enumerate(refs)
    ]
    actual = [
        (
            s.get("index"),
            str(s.get("owner", "")).casefold(),
            s.get("geom_id"),
            s.get("selection_action"),
            s.get("error"),
        )
        for s in observed
    ]
    summary = [
        (s.get("index"), s.get("geom_id"), s.get("action"), s.get("error"))
        for s in case.get("selection_log", [])
    ]
    projected = [(s[0], s[2], s[3], s[4]) for s in actual]
    indexes_ok = [r["index"] for r in refs] == list(range(len(refs)))
    count_ok = case.get("requested_sections") == len(refs)
    owners_ok = all(str(r["owner"]).casefold() == str(case["model"]).casefold() for r in refs)
    return {
        "request_id": request_id,
        "expected": expected,
        "observed": actual,
        "requested_indexes_sequential": indexes_ok,
        "requested_sections_match": count_ok,
        "requested_owners_match_model": owners_ok,
        "host_sequence_matches": actual == expected and indexes_ok and count_ok and owners_ok,
        "matrix_selection_matches_host": summary == projected,
    }


def receipt_specs(case):
    model_id = case["adopted_model_id"]
    job_id = case["boundary"]["measure_job"]
    if not HEX_ID.fullmatch(model_id) or not HEX_ID.fullmatch(job_id):
        raise ValueError("invalid model or job ID")
    filename = Path(case["quilt"]["source"].replace("\\", "/")).name
    if not SNAPSHOT.fullmatch(filename):
        raise ValueError("invalid inspection snapshot filename")
    return [Path("models") / model_id / "output" / filename, Path("jobs") / job_id / "job.json"]


def audit(package, output, receipt_root=None):
    package = package.resolve(strict=True)
    output = output.resolve(strict=False)
    if output == package or output.is_relative_to(package):
        raise ValueError("output must be outside the input package")
    report_text = contained(package, Path("T1B_REPORT.md")).read_text(encoding="utf-8-sig")
    matrix = json.loads(
        contained(package, Path("evidence/matrix_summary.json")).read_text(encoding="utf-8-sig")
    )
    rows = {
        row[0]: {
            "bytes": int(row[1].replace(",", "")),
            "sha256": row[2].lower(),
            "model_id": row[3].lower(),
        }
        for row in PRT_ROW.findall(report_text)
    }
    if len(rows) != 6 or len(matrix["cases"]) != 6:
        raise ValueError("expected six PRT table rows and six matrix cases")
    request_ids = [case["request_id"] for case in matrix["cases"]]
    unique_requests = len(set(request_ids)) == 6
    matrix_models = {
        str(case["model"]).casefold(): case["adopted_model_id"].lower() for case in matrix["cases"]
    }
    unique_models = len(matrix_models) == 6
    steps = jsonl(contained(package, Path("probe/host/session_steps.jsonl")))
    prts = []
    for relative, claim in rows.items():
        path = contained(package, Path(relative))
        actual = {"bytes": path.stat().st_size, "sha256": digest(path)} if path.is_file() else None
        model = Path(relative).name.split(".prt.")[0].casefold()
        prts.append(
            {
                "path": relative,
                "claimed": claim,
                "actual": actual,
                "matches": actual == {k: claim[k] for k in ("bytes", "sha256")},
                "adopted_model_id_matches_matrix": matrix_models.get(model) == claim["model_id"],
            }
        )
    cases = []
    receipt_root = receipt_root.resolve(strict=True) if receipt_root else None
    for case in matrix["cases"]:
        checks = select_checks(case, steps)
        receipts = []
        for relative in receipt_specs(case):
            target = (
                contained(output, Path("receipts") / relative)
                if output.exists()
                else output / "receipts" / relative
            )
            source = contained(receipt_root, relative) if receipt_root else None
            if source and source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    if digest(target) != digest(source):
                        raise ValueError(f"existing receipt differs: {target}")
                else:
                    shutil.copyfile(source, target)
            present = bool(source and source.is_file() and target.is_file())
            receipts.append(
                {
                    "relative_path": relative.as_posix(),
                    "present": present,
                    "source": str(source) if present else None,
                    "bytes": target.stat().st_size if present else None,
                    "sha256": digest(target) if present else None,
                    "identity_verification": "not_checked" if present else "not_available",
                }
            )
        cases.append(
            {
                "case": case["case"],
                "model": case["model"],
                **checks,
                "claimed_geometry_checks": case["checks"],
                "bbox_ok": case["checks"].get("bbox_ok"),
                "receipts": receipts,
                "independent_geometry_verified": False,
            }
        )
    manifest = []
    for path in sorted(package.rglob("*")):
        if path.is_file():
            relative = path.relative_to(package)
            contained(package, relative)
            manifest.append(
                {"path": relative.as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}
            )
    result = {
        "scope": "offline package integrity and claim correlation only",
        "prt_table": prts,
        "cases": cases,
        "unique_request_ids": unique_requests,
        "unique_case_models": unique_models,
        "missing_original_receipts": [
            r["relative_path"] for c in cases for r in c["receipts"] if not r["present"]
        ],
        "geometry_claims_independently_verified": False,
    }
    result["integrity_ok"] = (
        unique_requests
        and unique_models
        and all(p["matches"] and p["adopted_model_id_matches_matrix"] for p in prts)
        and all(c["host_sequence_matches"] and c["matrix_selection_matches_host"] for c in cases)
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "package_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    receipt_manifest = [r for c in cases for r in c["receipts"] if r["present"]]
    (output / "receipt_manifest.json").write_text(
        json.dumps(receipt_manifest, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--receipt-root", type=Path, help="Explicit external root with models/ and jobs/ originals"
    )
    args = parser.parse_args()
    result = audit(args.package, args.output, args.receipt_root)
    print(
        json.dumps(
            {
                "prt_matches": sum(x["matches"] for x in result["prt_table"]),
                "host_matches": sum(x["host_sequence_matches"] for x in result["cases"]),
                "integrity_ok": result["integrity_ok"],
                "missing_receipts": len(result["missing_original_receipts"]),
            },
            indent=2,
        )
    )
    if not result["integrity_ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
