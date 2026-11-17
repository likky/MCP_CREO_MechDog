"""BUG-130 offline ASCII STL and per-surface mesh checks with MSVC.

No Toolkit libraries are linked and Creo is never started. Run from the
editable installation:
.venv\\Scripts\\python.exe tools\\test_stl_file_check.py
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone

from creo_mechdog.build_support import compiler_setup_script, validate_local_path
from creo_mechdog.paths import SOURCE_PATHS


def build_and_run(root, settings, directory, name, source, includes):
    executable = directory / f"{name}.exe"
    for path in (directory, root / "native", source, *includes):
        validate_local_path(str(path), "STL check path")
    batch = directory / f"build_{name}.cmd"
    include_flags = " ".join(f'/I "{path}"' for path in includes)
    batch.write_text(
        "@echo off\n"
        + compiler_setup_script(settings)
        + f"\ncl /nologo /std:c++17 /EHsc /W3 /utf-8 {include_flags} "
        + f'/Fo:"{directory / f"{name}.obj"}" /Fe:"{executable}" "{source}"\n'
        + "exit /b %errorlevel%\n",
        encoding="utf-8",
    )
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with (directory / f"build_{name}.log").open("wb") as log:
        built = subprocess.run(
            ["cmd.exe", "/d", "/c", str(batch)],
            cwd=directory,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=120,
            creationflags=flags,
        )
    report = {"build_exit_code": built.returncode, "success": False}
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
    return report


def main() -> int:
    root = SOURCE_PATHS.resource_root
    settings = json.loads((root / "config.json").read_text(encoding="utf-8-sig"))
    directory = root / "build/stl_file_check_test"
    directory.mkdir(parents=True, exist_ok=True)
    file_source = root / "tests/native/test_stl_file_check.cpp"
    mesh_source = root / "tests/native/test_stl_mesh_check.cpp"
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                file_source,
                mesh_source,
                root / "native/stl_file_check.h",
                root / "native/stl_mesh_check.h",
            )
        },
        "toolkit_calls": "none; no Creo connection",
        "file_check": build_and_run(
            root,
            settings,
            directory,
            "stl_file_check_test",
            file_source,
            [root / "native"],
        ),
        "mesh_check": build_and_run(
            root,
            settings,
            directory,
            "stl_mesh_check_test",
            mesh_source,
            [root / "native"],
        ),
    }
    report["success"] = report["file_check"]["success"] and report["mesh_check"]["success"]
    (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
