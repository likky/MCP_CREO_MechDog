"""Build MANIFEST.sha256 for the T1-C package.

Raw burst frames under work/burst*/ are deliberately excluded: they are debug
output from the failed screen-capture attempt (376 files, ~110 MB) and are kept
only so the failure can be inspected; hashing them would bloat the manifest.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

BASE = Path(__file__).resolve().parent
SKIP_PARTS = {"burst", "burst2", "burst3", "burst4"}
SKIP_FILES = {"MANIFEST.sha256"}


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def main() -> int:
    rows = []
    skipped = 0
    for path in sorted(BASE.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(BASE)
        if path.name in SKIP_FILES:
            continue
        if any(part in SKIP_PARTS for part in relative.parts):
            skipped += 1
            continue
        rows.append(f"{digest(path)} *{relative.as_posix()}")
    (BASE / "MANIFEST.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"{len(rows)} files hashed, {skipped} burst frames skipped")
    print(f"manifest bytes: {(BASE / 'MANIFEST.sha256').stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
