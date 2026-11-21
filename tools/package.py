"""Build the public MIT source release from an explicit allowlist."""

import argparse
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from creo_mechdog.release_integrity import (
    approved_evidence_files,
    panel_profile_library_files,
    seed_library_files,
    template_library_files,
    validate_asset_paths,
    validate_release_inputs,
    validate_release_records,
    write_sidecar,
)
from version import VERSION

NAME = "MCP_CREO_MechDog"


def source_files(root: Path | None = None):
    root = Path(root) if root is not None else ROOT
    names = (
        "README.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "server.py",
        "bridge.py",
        "creo_startup.py",
        # BUG-127: bridge.py imports this lazily for the desktop retry path.
        "desktop_worker.py",
        "seeds.py",
        "airfoil.py",
        "profile_checks.py",
        "generic_bridge.py",
        "schema.py",
        "version.py",
        "capabilities.py",
        "config.example.json",
        "client-config.example.json",
        "requirements.txt",
        "requirements.lock.txt",
        "requirements-dev.txt",
        "setup.ps1",
        ".gitignore",
        ".gitattributes",
        "AGENTS.md",
        "pyproject.toml",
        ".clang-format",
        ".editorconfig",
        "tools/test_result_delivery.cpp",
        "tools/test_recovery_deadline.cpp",
        "docs/validation/DEV-028-WorkBuddy-report-20261016.txt",
        "docs/validation/track-feedback-2026-10-16/track-modeling-rev2.txt",
        "docs/validation/bug-001-repro-2026-10-16/g0_driver.py",
        "tools/test_callback_payload.cpp",
        "docs/validation/feedback-0.18.4-2026-11-08/originals/surface_loft.local.patch.diff",
    )
    files = [root / name for name in names]
    for directory, extensions in {
        "src/creo_mechdog": {".py"},
        "native": {".cpp", ".hpp", ".h"},
        "tools": {".py"},
        "tests": {".py"},
        "examples": {".json"},
        "docs": {".md", ".json"},
    }.items():
        files.extend(
            p
            for p in (root / directory).rglob("*")
            if p.is_file() and p.suffix in extensions and "__pycache__" not in p.parts
        )
    files.append(root / "native/third_party/LICENSE.nlohmann-json")
    files.extend(
        path
        for path in (root / "tests/native").glob("test_*")
        if path.is_file() and path.suffix in {".cpp", ".h", ".hpp"}
    )
    files.extend(
        p
        for p in (root / ".github").rglob("*")
        if p.is_file() and p.suffix in {".md", ".yml", ".yaml"}
    )
    files.extend(seed_library_files(root))
    # BUG-123: element tree templates ship with their manifest, which is also the
    # allowlist and the digest record checked by validate_release_inputs().
    files.extend(template_library_files(root))
    # BUG-120/D1: resident-panel UI profiles ship the same way; an unreferenced
    # file is not packaged, and a refused library fails before the ZIP exists.
    files.extend(panel_profile_library_files(root))
    # DEV-083 (0.25.0 feedback P2-1): reviewed TXT evidence ships byte-exact from
    # its own manifest instead of widening the `docs` allowlist to every .txt.
    files.extend(approved_evidence_files(root))
    for path in files:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing source file or unexpected symlink: {path}")
    return sorted(set(files))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed-archive",
        type=Path,
        required=True,
        help="Seed library ZIP published with this release; its digest must match the "
        "trusted seed package record",
    )
    parser.add_argument(
        "--stage", type=Path, help="Also copy public files into a new empty upload directory"
    )
    parser.add_argument(
        "--output", type=Path, help="New ZIP path; refuses to overwrite an existing archive"
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        help="Source tree to package (defaults to this checkout; used by isolated tests)",
    )
    parser.add_argument(
        "--unit-report",
        type=Path,
        help="Unit test evidence file; defaults to <source-root>/build/unit_test_report.json",
    )
    args = parser.parse_args()
    source_root = args.source_root.resolve() if args.source_root else ROOT
    unit_report = args.unit_report.resolve() if args.unit_report else None
    seed_archive = args.seed_archive.resolve()
    try:
        summary = validate_release_inputs(source_root, seed_archive)
    except ValueError as error:
        print(f"Source package refused: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    try:
        files = source_files(source_root)
    except ValueError as error:
        print(f"Source package refused: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    # BUG-144: the release record and its unit evidence are checked before the
    # ZIP, sidecar or stage directory exists, so a stale report cannot leave a
    # package that looks complete.
    problems = validate_release_records(VERSION, root=source_root, unit_report=unit_report)
    if problems:
        print("Release record gate rejected this package:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    if args.stage:
        stage = args.stage.resolve()
        if stage == source_root or source_root in stage.parents or stage in source_root.parents:
            raise ValueError("Upload directory must be separate from the working project")
        if stage.exists() and (not stage.is_dir() or any(stage.iterdir())):
            raise ValueError(
                "Upload directory must be new or empty; existing files are never deleted"
            )
        stage.mkdir(parents=True, exist_ok=True)
        for source in files:
            destination = stage / source.relative_to(source_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    archive = (
        args.output.resolve()
        if args.output
        else source_root.parent / f"{NAME}-{VERSION}-source.zip"
    )
    if args.output and archive.exists():
        raise ValueError("Explicit output archive already exists; choose a new path")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for source in files:
            output.write(source, f"{NAME}/" + source.relative_to(source_root).as_posix())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    sidecar = archive.with_suffix(".zip.sha256")
    write_sidecar(sidecar, checksum, archive.name)
    seed_sidecar = seed_archive.with_suffix(".zip.sha256")
    print(f"Public source: {archive}; {len(files)} files; SHA256 {checksum}")
    print(
        f"Seed archive: {summary['seed_archive']}; "
        f"{summary['seed_count']} seeds; SHA256 {summary['seed_archive_sha256']}"
    )
    print("Release assets (upload all four; never a *.zip glob):")
    for path in (archive, sidecar, seed_archive, seed_sidecar):
        print(f"  {path}")
    if args.stage:
        print(f"GitHub upload directory: {args.stage.resolve()}")
    if not seed_sidecar.is_file():
        print(f"ERROR: missing seed checksum sidecar: {seed_sidecar}", file=sys.stderr)
        print(
            "Rebuild the seed archive first: python tools/package_seeds.py --output "
            f'"{seed_archive}"',
            file=sys.stderr,
        )
        return 2
    problems = validate_asset_paths([archive, sidecar, seed_archive, seed_sidecar], VERSION)
    if problems:
        print("Release asset gate rejected this package:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("Release asset gate: four assets present; both sidecars match their ZIP digests")
    # root=source_root lets the source-tree gate (including the BUG-137/BUG-144
    # unit evidence check) run against the tree that built this archive.
    problems = validate_release_records(VERSION, archive, root=source_root, unit_report=unit_report)
    if problems:
        print("Release record gate rejected this package:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(f"Delete {archive} and rebuild it after fixing the records.", file=sys.stderr)
        return 1
    print("Release record gate: POSTCHECK, release record and per-ID states are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
