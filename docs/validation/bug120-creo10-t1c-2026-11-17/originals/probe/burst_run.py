"""Run the drive probe and capture frames at the same time.

Launching the burst from a separate shell call loses the short window in which
the dashboard exists: the tool round-trip takes longer than the panel lives.
This script owns both sides so the capture starts before the module is called.

    burst_run.py <outdir> <case-dir> <request.json> <wait> <x> <y> <w> <h>
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(HERE))
from burst import grab  # noqa: E402


def main(argv: list[str]) -> int:
    outdir = Path(argv[1])
    case_dir = Path(argv[2])
    request = Path(argv[3])
    wait = argv[4]
    x, y, w, h = (int(v) for v in argv[5:9])
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("c_*.bmp"):
        old.unlink()

    command = [
        sys.executable,
        str(HERE / "run_drive.py"),
        str(case_dir),
        "--request",
        str(request),
        "--host-dir",
        str(HERE / "host3"),
        "--marker",
        str(HERE / "host3" / "probe_end_marker_v2b.json"),
        "--wait",
        wait,
    ]
    process = subprocess.Popen(
        command, cwd=str(BASE), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    index = 0
    started = time.time()
    while process.poll() is None:
        grab(x, y, w, h, outdir / f"c_{index:04d}.bmp")
        index += 1
        time.sleep(0.04)
    output = process.stdout.read() if process.stdout else ""
    (outdir / "run.log").write_text(output, encoding="utf-8")
    print(f"{index} frames in {time.time() - started:.1f}s, rc={process.returncode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
