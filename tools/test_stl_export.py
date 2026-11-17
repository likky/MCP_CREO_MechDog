"""BUG-130 offline official STL export wiring check.

Compiles the adapter test against the installed SDK declarations with
substituted Toolkit calls. It does not connect Creo, build a worker, or export
a real model; the live matrix is a separate authorized run.
Run from the editable installation: .venv\\Scripts\\python.exe tools\\test_stl_export.py
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from creo_mechdog.build_support import compiler_setup_script, validate_local_path
from creo_mechdog.paths import SOURCE_PATHS


def main() -> int:
    root = SOURCE_PATHS.resource_root
    settings = json.loads((root / "config.json").read_text(encoding="utf-8-sig"))
    sdk = Path(settings["creo_root"]) / "Common Files/protoolkit/includes"
    directory = root / "build/stl_export_test"
    directory.mkdir(parents=True, exist_ok=True)
    source = root / "tests/native/test_stl_export.cpp"
    # A crashed assert dialog can keep the previous exe locked; build each run
    # under a unique name so the offline test is repeatable without touching
    # the stuck process.
    stamp = str(time.time_ns())
    executable = directory / f"stl_export_test_{stamp}.exe"
    for path in (sdk, directory, root / "native", source):
        validate_local_path(str(path), "STL export wiring test path")
    batch = directory / f"build_{stamp}.cmd"
    batch.write_text(
        "@echo off\n"
        + compiler_setup_script(settings)
        + f'\ncl /nologo /std:c++17 /EHsc /W3 /utf-8 /I "{sdk}" /I "{root / "native"}" '
        + f'/Fo:"{directory / f"stl_export_test_{stamp}.obj"}" /Fe:"{executable}" "{source}"\n'
        + "exit /b %errorlevel%\n",
        encoding="utf-8",
    )
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with (directory / "build.log").open("wb") as log:
        built = subprocess.run(
            ["cmd.exe", "/d", "/c", str(batch)],
            cwd=directory,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=120,
            creationflags=flags,
        )
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "build_exit_code": built.returncode,
        "sdk_header_sha256": {
            name: hashlib.sha256((sdk / name).read_bytes()).hexdigest()
            for name in ("ProUtil.h", "ProArray.h")
        },
        "source_sha256": {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                source,
                root / "native/stl_export.h",
                root / "native/stl_file_check.h",
            )
        },
        "toolkit_calls": "substituted; no Creo connection",
        "live_matrix": "not run",
        "success": False,
    }
    if built.returncode == 0:
        result = subprocess.run(
            [str(executable)], capture_output=True, timeout=10, creationflags=flags
        )
        report.update(
            exit_code=result.returncode,
            stdout=result.stdout.decode("utf-8", errors="replace"),
            stderr=result.stderr.decode("utf-8", errors="replace"),
            success=result.returncode == 0,
        )
    (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
