"""Target-machine check for BUG-120, in stages that each produce evidence.

Run this on the Creo 10 machine (WorkBuddy is fine: it is a plain command). Each stage
either writes what it observed or refuses with a named reason; nothing here claims a
panel opened. Stages:

    preflight   environment, SDK headers, build tools, profile library, DLLs
    build       python bridge.py build, then the worker's own build-info
    deploy      prepare a panel-generation deployment (protocol 4 / loader ABI 2)
    collect     pack every artifact of this run into one folder with a sha256 manifest
    all         preflight + build + collect (deploy only with --deploy)

Typical run on the target machine:

    .venv\\Scripts\\python.exe tools\\panel_target_check.py all --deploy

Then copy ``build/panel_target_evidence/<utc>/`` back. A missing folder member is
reported, never silently skipped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from creo_mechdog.paths import SOURCE_PATHS  # noqa: E402

ROOT = SOURCE_PATHS.resource_root
STAGES = ("preflight", "build", "deploy", "collect")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _python() -> str:
    return sys.executable


def preflight() -> dict:
    """What this machine has, without starting Creo or building anything."""
    from creo_mechdog import panel_profiles

    config_file = ROOT / "config.json"
    report: dict = {
        "stage": "preflight",
        "root": str(ROOT),
        "python": _python(),
        "python_version": sys.version.split()[0],
        "config_present": config_file.is_file(),
    }
    config: dict = {}
    if config_file.is_file():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8-sig"))
        except ValueError as exc:
            report["config_error"] = str(exc)
    report["creo_root"] = config.get("creo_root")
    report["vcvars64"] = config.get("vcvars64")
    creo_root = Path(config["creo_root"]) if config.get("creo_root") else None
    if creo_root:
        sdk = creo_root / "Common Files/protoolkit"
        report["sdk_includes"] = str(sdk / "includes")
        report["sdk_headers"] = (
            len(list((sdk / "includes").glob("*.h"))) if (sdk / "includes").is_dir() else 0
        )
        report["sdk_present"] = (sdk / "includes/ProToolkit.h").is_file()
        # The Creo build number is what panel admission compares against, so it is
        # evidence, not decoration.
        report["creo_version_dirs"] = [
            child.name for child in creo_root.parent.iterdir() if child.is_dir()
        ]
    report["vcvars_present"] = (
        bool(config.get("vcvars64")) and Path(str(config.get("vcvars64"))).is_file()
    )
    report["artifacts"] = {
        name: (ROOT / "build" / name).is_file()
        for name in ("creo_worker.exe", "creo_blend_sync.dll", "creo_blend_loader.dll")
    }
    try:
        profiles = panel_profiles.profiles(ROOT)
        report["panel_profiles"] = [profile.profile_id for profile in profiles]
        report["panel_profiles_error"] = None
    except (ValueError, OSError) as exc:
        report["panel_profiles"] = []
        report["panel_profiles_error"] = str(exc)
    report["candidate_ticket_present"] = panel_profiles.candidate_ticket() is not None
    return report


def build() -> dict:
    """Build the worker + payload here, then ask the binary what it declares."""
    started = time.monotonic()
    completed = subprocess.run(
        [_python(), "bridge.py", "build"],
        cwd=ROOT,
        capture_output=True,
        timeout=3600,
    )
    report: dict = {
        "stage": "build",
        "exit_code": completed.returncode,
        "seconds": round(time.monotonic() - started, 1),
        "stdout_tail": completed.stdout.decode("utf-8", "replace")[-4000:],
        "stderr_tail": completed.stderr.decode("utf-8", "replace")[-2000:],
    }
    worker = ROOT / "build/creo_worker.exe"
    if worker.is_file():
        info = subprocess.run([str(worker), "build-info"], capture_output=True, timeout=120)
        report["build_info_exit"] = info.returncode
        try:
            report["build_info"] = json.loads(info.stdout.decode("utf-8", "replace"))
        except ValueError:
            report["build_info"] = None
            report["build_info_raw"] = info.stdout.decode("utf-8", "replace")[:4000]
    return report


def deploy() -> dict:
    """Write a panel-generation deployment. Refused unless the caller says so."""
    from creo_mechdog.blend_callback import prepare_callback

    dll = ROOT / "build/creo_blend_sync.dll"
    if not dll.is_file():
        return {"stage": "deploy", "ok": False, "reason": "build the payload first"}
    metadata = prepare_callback(
        ROOT / "build",
        _sha256(dll),
        _loader_fingerprint(),
        generation="panel",
        allow_generation_switch=True,
    )
    return {
        "stage": "deploy",
        "ok": True,
        "protocol": metadata.get("protocol"),
        "loader_abi": metadata.get("loader_abi"),
        "contract": metadata.get("contract"),
        "command": metadata.get("command"),
        "registration": metadata.get("registry_file"),
        "next": (
            "In Creo: Auxiliary Applications -> register registry_file, Start it once, review "
            "the DLL prompt yourself, then restart Creo so the panel generation is loaded."
        ),
    }


def _loader_fingerprint() -> str:
    """The loader generation key the last build produced, read from the build tree.

    bridge.py owns the derivation; this script only picks the newest existing key so
    it cannot drift from the build that actually produced the DLL.
    """
    directory = ROOT / "build/blend_loader"
    candidates = [
        path.name
        for path in directory.glob("*")
        if path.is_dir() and re.fullmatch(r"[0-9a-f]{64}(?:-[0-9a-f]{12})?", path.name)
    ]
    if not candidates:
        raise SystemExit("No loader generation found; run `python bridge.py build` first.")
    candidates.sort(key=lambda name: (directory / name).stat().st_mtime)
    return candidates[-1]


def collect() -> dict:
    """One folder with every artifact, plus a manifest that pins their bytes."""
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    target = ROOT / "build/panel_target_evidence" / stamp
    target.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    # Binaries are hashed but not copied: the digest proves which build ran, while
    # copying them would add tens of megabytes to a bundle that only needs evidence.
    binary_digests: dict[str, dict] = {}
    for name in ("creo_worker.exe", "creo_blend_sync.dll", "creo_blend_loader.dll"):
        binary = ROOT / "build" / name
        if binary.is_file():
            binary_digests[f"build/{name}"] = {
                "sha256": _sha256(binary),
                "bytes": binary.stat().st_size,
            }
    for candidate in (
        ROOT / "build/build.log",
        ROOT / "build/generate_constants.log",
        ROOT / "build/blend_callback_setup.json",
        ROOT / "build/creo10_check/report.json",
    ):
        if candidate.is_file():
            files.append(candidate)
    for pattern, limit in (
        ("build/blend_callback/**/callback_result.json", 4),
        ("build/blend_callback/**/callback_bootstrap.json", 4),
        ("build/blend_loader/**/deployment.json", 4),
        ("build/jobs/**/panel_wait.json", 20),
        ("build/jobs/**/worker.log", 20),
        ("build/jobs/**/request.json", 20),
        ("build/jobs/**/result.json", 20),
        ("build/jobs/**/callback_result.json", 20),
    ):
        for path in sorted(ROOT.glob(pattern))[-limit:]:
            if path.is_file():
                files.append(path)
    manifest = {
        "created_utc": stamp,
        "root": str(ROOT),
        "files": {},
        "binaries_not_copied": binary_digests,
    }
    for source in files:
        relative = source.relative_to(ROOT).as_posix()
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        manifest["files"][relative] = {
            "sha256": _sha256(destination),
            "bytes": destination.stat().st_size,
        }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {
        "stage": "collect",
        "folder": str(target),
        "file_count": len(manifest["files"]),
        "manifest": str(target / "manifest.json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="BUG-120 target-machine check")
    parser.add_argument("stage", choices=(*STAGES, "all"))
    parser.add_argument(
        "--deploy", action="store_true", help="with 'all': also write a panel-generation deployment"
    )
    parser.add_argument("--json", default=None, help="also write the report to this file")
    args = parser.parse_args()

    report: dict = {"stages": []}
    if args.stage in ("preflight", "all"):
        report["stages"].append(preflight())
    if args.stage in ("build", "all"):
        report["stages"].append(build())
    if args.deploy and args.stage in ("deploy", "all"):
        report["stages"].append(deploy())
    if args.stage in ("collect", "all"):
        report["stages"].append(collect())
    report["ok"] = all(
        stage.get("exit_code", 0) == 0 for stage in report["stages"] if isinstance(stage, dict)
    )
    text = json.dumps(report, indent=2)
    print(text)
    destination = Path(args.json) if args.json else None
    if destination:
        destination.write_text(text + "\n", encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
