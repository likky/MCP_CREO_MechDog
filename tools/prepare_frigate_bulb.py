"""Prepare the TXT bulb curves offline; this command has no live/Creo mode."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

from creo_mechdog.frigate_bulb import audit, build_plan, extract_source, verify_source_snapshot

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/frigate_bulb_source.json"


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def source_identity() -> dict:
    def git(*args: str) -> str | None:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    files = (
        "src/creo_mechdog/frigate_bulb.py",
        "tools/prepare_frigate_bulb.py",
        "tests/unit/test_frigate_bulb.py",
        "examples/frigate_bulb_source.json",
        "examples/frigate_bulb_minimal.json",
        "src/creo_mechdog/schema.py",
        "src/creo_mechdog/surface_ops.py",
        "src/creo_mechdog/profile_checks.py",
    )
    status = git("status", "--porcelain")
    return {
        "commit": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "dirty": None if status is None else bool(status),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "files_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, help="Original UTF-8 TXT; otherwise use the frozen excerpt/data"
    )
    parser.add_argument(
        "--mm-per-m", type=float, default=1000, help="1000=full size; 10=1:100, always explicit"
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build/frigate_bulb_offline")
    args = parser.parse_args()
    frozen = json.loads(FIXTURE.read_text(encoding="utf-8"))
    source = extract_source(args.source) if args.source else frozen
    plan = build_plan(source, args.mm_per_m)
    report = audit(source, plan, args.mm_per_m)
    geometry_matches = source["geometry"] == frozen["geometry"]
    excerpt_hash = hashlib.sha256(source["source"]["excerpt"].encode("utf-8")).hexdigest()
    provenance_ok = excerpt_hash == source["source"]["excerpt_sha256"]
    snapshot_ok = verify_source_snapshot(frozen)
    file_matches = source["source"]["sha256"] == frozen["source"]["sha256"] if args.source else None
    report["passed"] = (
        report["passed"]
        and geometry_matches
        and provenance_ok
        and snapshot_ok
        and file_matches is not False
    )
    report["provenance"] = {
        "input": "original_txt" if args.source else "frozen_snapshot",
        "original_file_read_this_run": args.source is not None,
        "original_file_sha256_matches_frozen": file_matches,
        "frozen_geometry_reextracted_from_excerpt": snapshot_ok,
        "geometry_matches_frozen": geometry_matches,
        "excerpt_sha256_matches": provenance_ok,
    }
    report["source_identity"] = source_identity()
    report["execution_boundary"] = "No Creo, Toolkit, MCP service or native build was invoked"
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "source_snapshot.json": source,
        "minimal_plan.json": plan,
        "curves_plan.json": {
            "operations": plan["operations"][:-1],
            "assertions": plan["assertions"],
        },
        # This fragment needs the model_id/revision from the curves job; it is
        # intentionally not submitted, and must not be run as a new-part plan.
        "loft_operations.json": {
            "operations": plan["operations"][-1:],
            "assertions": plan["assertions"],
        },
        "report.json": report,
    }
    for name, value in artifacts.items():
        write_json(output / name, value)
    write_json(
        output / "MANIFEST-SHA256.json",
        {
            name: {
                "bytes": (output / name).stat().st_size,
                "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest(),
            }
            for name in artifacts
        },
    )
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "creo_tested": False,
                "report": str(output / "report.json"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
