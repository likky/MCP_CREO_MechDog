"""BUG-120 task 2: compile and run the curve-fit diagnostics without Creo.

Compiles tests/native/test_panel_fit.cpp with the local C++ compiler. The rules
live in native/panel_fit.h and call no Pro* function; the evaluator is supplied by
the caller, so nothing here touches Toolkit or a session. The Toolkit adapter in
native/panel_run.h is compiled only as part of the worker build; whether the
sampling finds a crossing on a real model is a live-run question.

.venv\\Scripts\\python.exe tools\\test_panel_fit.py
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone

from creo_mechdog.build_support import compiler_setup_script, validate_local_path
from creo_mechdog.paths import SOURCE_PATHS


def main() -> int:
    root = SOURCE_PATHS.resource_root
    settings = json.loads((root / "config.json").read_text(encoding="utf-8-sig"))
    directory = root / "build/panel_fit_test"
    directory.mkdir(parents=True, exist_ok=True)
    source = root / "tests/native/test_panel_fit.cpp"
    header = root / "native/panel_fit.h"
    executable = directory / "panel_fit_test.exe"
    for path in (directory, root / "native", source):
        validate_local_path(str(path), "panel fit test path")
    lines = ["@echo off", compiler_setup_script(settings)]
    lines.append(
        f'cl /nologo /std:c++17 /EHsc /W3 /I "{root / "native"}" '
        + f'/Fo:"{directory / "panel_fit_test.obj"}" /Fe:"{executable}" "{source}"'
    )
    lines.append("if errorlevel 1 exit /b %errorlevel%")
    lines.append("exit /b 0")
    batch = directory / "build.cmd"
    batch.write_text("\n".join(lines) + "\n", encoding="utf-8")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with (directory / "build.log").open("wb") as log:
        built = subprocess.run(
            ["cmd.exe", "/d", "/c", str(batch)],
            cwd=directory,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=300,
            creationflags=flags,
        )
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "build_exit_code": built.returncode,
        "compiler_setup": settings["vcvars64"],
        "source_sha256": {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (source, header)
        },
        "toolkit_calls": "none; sampling rules only; no Creo connection",
        "success": False,
    }
    if built.returncode == 0:
        result = subprocess.run(
            [str(executable)], capture_output=True, timeout=60, creationflags=flags
        )
        report["run"] = {
            "exit_code": result.returncode,
            "stdout": result.stdout.decode("utf-8", errors="replace"),
            "stderr": result.stderr.decode("utf-8", errors="replace"),
        }
        report["success"] = result.returncode == 0
    (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
