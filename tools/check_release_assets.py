"""Check that a GitHub Release carries both ZIPs and both SHA256 sidecars.

DEV-045/C01: 0.11.7 and 0.12.0 shipped only the two ZIPs, so upgrade users had no
sidecar to verify. ``tools/package.py`` and ``tools/package_seeds.py`` already write
``<zip>.sha256``; this gate checks the remote Release instead of regenerating them.

DEV-070: the validation itself lives in ``creo_mechdog.release_integrity`` so the
source packager can gate the same four paths even when they live in two directories.

DEV-097: the Release body (the ``--notes-file`` text shown on the Release page)
must itself name the four assets and tell readers that the source digest lives in
its sidecar; 0.32.0 and 0.33.0 dropped that section, so the digests were only
visible inside the package. The gate fetches the body (or reads ``--body-file``)
and checks it for releases at or after ``BODY_CHECK_ENFORCED_FROM``.
"""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from creo_mechdog.release_download import download, fetch_release_body
from creo_mechdog.release_integrity import (
    body_check_enforced,
    expected_assets,
    read_sidecar,
    validate_asset_paths,
    validate_directory,
    validate_release_body,
    validate_release_records,
)

__all__ = [
    "body_check_enforced",
    "download",
    "expected_assets",
    "fetch_release_body",
    "main",
    "read_sidecar",
    "validate_asset_paths",
    "validate_directory",
    "validate_release_body",
]


def _sidecar_digests(directory: Path, version: str) -> dict[str, str]:
    """Map each shipped ZIP name to the lowercase SHA256 its sidecar records."""
    digests: dict[str, str] = {}
    for name in expected_assets(version):
        if not name.endswith(".sha256"):
            continue
        sidecar = Path(directory) / name
        if not sidecar.is_file():
            continue
        try:
            digest, target = read_sidecar(sidecar)
        except ValueError:
            continue
        digests[target] = digest
    return digests


def _body_problems(asset_dir: Path, version: str, body: str | None) -> tuple[list[str], bool]:
    """Return ``(body problems, whether the body was actually checked)``."""
    if body is None or not body_check_enforced(version):
        return [], False
    return (
        validate_release_body(body, version, _sidecar_digests(asset_dir, version)),
        True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Release tag, for example v0.12.0")
    parser.add_argument(
        "--version",
        help="Release version; defaults to the tag without a leading 'v'",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        help="Verify an existing download directory instead of downloading the Release",
    )
    parser.add_argument(
        "--body-file",
        type=Path,
        help=(
            "Read the Release body from this file instead of fetching it; "
            "used with --dir to verify the body offline"
        ),
    )
    args = parser.parse_args(argv)
    version = args.version or args.tag.removeprefix("v")
    body_checked = False
    if args.dir:
        asset_dir = args.dir.resolve()
        try:
            problems = validate_directory(asset_dir, version)
        except OSError as error:
            print(f"{args.tag}: could not read {args.dir}: {error}", file=sys.stderr)
            return 2
        if not problems:
            problems = validate_release_records(version, asset_dir / expected_assets(version)[0])
        if not problems:
            body = None
            if args.body_file is not None:
                try:
                    body = args.body_file.read_text(encoding="utf-8-sig")
                except OSError as error:
                    print(
                        f"{args.tag}: could not read body file {args.body_file}: {error}",
                        file=sys.stderr,
                    )
                    return 2
            problems, body_checked = _body_problems(asset_dir, version, body)
    else:
        with tempfile.TemporaryDirectory() as temp:
            asset_dir = Path(temp)
            try:
                download(args.tag, asset_dir)
            except (RuntimeError, OSError) as error:
                fallback = ROOT / "build/release-assets" / args.tag
                print(f"{args.tag}: {error}", file=sys.stderr)
                print("The remote Release was not checked.", file=sys.stderr)
                print(
                    "Download the four assets and both sidecars into one directory, then run:",
                    file=sys.stderr,
                )
                print(
                    f"  python tools/check_release_assets.py --tag {args.tag} "
                    f'--version {version} --dir "{fallback}"',
                    file=sys.stderr,
                )
                return 2
            problems = validate_directory(asset_dir, version)
            if not problems:
                problems = validate_release_records(
                    version, asset_dir / expected_assets(version)[0]
                )
            if not problems and body_check_enforced(version):
                try:
                    body = fetch_release_body(args.tag)
                except RuntimeError as error:
                    problems = [f"release body could not be fetched: {error}"]
                else:
                    problems, body_checked = _body_problems(asset_dir, version, body)
    if problems:
        print(f"{args.tag}: release assets are incomplete or inconsistent", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    body_suffix = "; release body self-proof verified" if body_checked else ""
    if args.dir:
        print(
            f"local_verified: four assets present; both sidecars match "
            f"(version {version}){body_suffix}"
        )
    else:
        print(f"{args.tag}: four assets downloaded and verified; both sidecars match{body_suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
