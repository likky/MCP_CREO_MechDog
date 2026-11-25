"""Build and run the ASCII STL write benchmark. It never connects Creo."""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from creo_mechdog.build_support import compiler_setup_script, validate_local_path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/native/bench_stl_write.cpp"


def main() -> int:
    settings = json.loads((ROOT / "config.json").read_text(encoding="utf-8-sig"))
    sdk = Path(settings["creo_root"]) / "Common Files/protoolkit/includes"
    directory = ROOT / "build/stl_write_bench"
    directory.mkdir(parents=True, exist_ok=True)
    for path in (sdk, directory, ROOT / "native", SOURCE):
        validate_local_path(str(path), "STL write benchmark path")
    stamp = str(time.time_ns())
    executable = directory / f"bench_{stamp}.exe"
    batch = directory / f"build_{stamp}.cmd"
    batch.write_text(
        "@echo off\n"
        + compiler_setup_script(settings)
        + "\ncl /nologo /std:c++17 /EHsc /O2 /W3 /utf-8 "
        + f'/I "{sdk}" /I "{ROOT / "native"}" '
        + f'/Fo:"{directory / f"bench_{stamp}.obj"}" /Fe:"{executable}" "{SOURCE}"\n'
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
            timeout=180,
            creationflags=flags,
        )
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "build_exit_code": built.returncode,
        "toolkit_calls": "substituted; no Creo connection",
    }
    if built.returncode == 0:
        result = subprocess.run(
            [str(executable)], capture_output=True, timeout=300, creationflags=flags
        )
        report["stdout"] = result.stdout.decode("utf-8", errors="replace")
        report["exit_code"] = result.returncode
        report["success"] = result.returncode == 0
    else:
        report["success"] = False
        report["build_log"] = (directory / "build.log").read_text(
            encoding="utf-8", errors="replace"
        )[-4000:]
    (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
