"""BUG-130 offline STL evidence summarizer.

Reads a finished job directory only; it never connects to Creo, starts a
worker, retries the export or modifies job/model files. The output is meant to
be attached to the next authorized live run:

    python tools/diagnose_stl_export.py jobs/<job_id> [more job dirs...]

`summarize_stl_job` keeps the original terminal status/message, the worker exit
code, the persisted output bytes, the last native phase, and the new
``STL_*`` instrumentation lines. It never invents a facet count from a
``ProArraySizeGet`` return code.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_STL_STAGE = re.compile(r"^(STL_[A-Z_]+)")
_EXIT_CODE = re.compile(r"Native worker exited (-?\d+) without a result")
_TESS_CODE = re.compile(r"ProPartTessellate\([^\n]*\)=(-?\d+)")
_ARRAY_CODE = re.compile(r"ProArraySizeGet\([^\n]*\)=(-?\d+)")
_OUTER_COUNT = re.compile(r"STL_OUTER_ARRAY_COUNT code=(-?\d+) n=(-?\d+)")
_BAD_INDEX = re.compile(
    r"STL_BAD_INDEX index=(-?\d+) surface_id=(-?\d+) facet=(-?\d+) indices=([^ ]+) n_vertices=(-?\d+)"
)
#: Avoid hashing a multi-hundred-MB source part in an offline diagnostic. The
#: registry-recorded SHA256 is still reported; the actual bytes can be hashed
#: separately when a full identity check is required.
MAX_HASH_BYTES = 16 * 1024 * 1024


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_larger_than(path: Path, limit: int) -> bool:
    try:
        return path.is_file() and path.stat().st_size > limit
    except OSError:
        return False


def _sha256_file(path: Path, limit: int = MAX_HASH_BYTES) -> str | None:
    if not path.is_file():
        return None
    try:
        if path.stat().st_size > limit:
            return None
    except OSError:
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _output_files(job_dir: Path) -> list[dict[str, Any]]:
    output = job_dir / "output"
    if not output.is_dir():
        return []
    files = []
    for path in sorted(output.rglob("*")):
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            size = None
        files.append(
            {
                "path": path.relative_to(job_dir).as_posix(),
                "bytes": size,
                "sha256": _sha256_file(path),
                "zero_bytes": size == 0,
            }
        )
    return files


def _parse_native(log_text: str) -> dict[str, Any]:
    lines = log_text.splitlines()
    phases = [line.split("=", 1)[1] for line in lines if line.startswith("PHASE=")]
    stl_lines = [line for line in lines if _STL_STAGE.match(line)]
    stages = [match.group(1) for line in stl_lines if (match := _STL_STAGE.match(line))]
    outer = _OUTER_COUNT.search(log_text)
    bad = _BAD_INDEX.search(log_text)
    facet_batches = [line for line in stl_lines if line.startswith("STL_FACET_BATCH")]
    return {
        "last_phase": phases[-1] if phases else None,
        "phases": phases[-20:],
        "native_log_lines": len(lines),
        "tessellate_code": int(match.group(1)) if (match := _TESS_CODE.search(log_text)) else None,
        "array_size_code": int(match.group(1)) if (match := _ARRAY_CODE.search(log_text)) else None,
        "outer_count": int(outer.group(2)) if outer else None,
        "outer_array_code": int(outer.group(1)) if outer else None,
        "last_stage": stages[-1] if stages else None,
        "stages": stages[-50:],
        "surface_begin_count": sum(1 for line in stl_lines if line.startswith("STL_SURFACE_BEGIN")),
        "facet_batch_count": len(facet_batches),
        "last_facet_batch": facet_batches[-1] if facet_batches else None,
        "bad_index": (
            {
                "index": int(bad.group(1)),
                "surface_id": int(bad.group(2)),
                "facet": int(bad.group(3)),
                "indices": bad.group(4),
                "n_vertices": int(bad.group(5)),
            }
            if bad
            else None
        ),
        "free_begin": any(line.startswith("STL_TESS_FREE_BEGIN") for line in stl_lines),
        "free_end": any(line.startswith("STL_TESS_FREE_END") for line in stl_lines),
        "stl_lines": stl_lines[-50:],
    }


def summarize_stl_job(job_dir: Path) -> dict[str, Any]:
    """Summarize one persisted STL job. Missing files return empty evidence."""
    job_dir = Path(job_dir)
    manifest = _read_json(job_dir / "job.json")
    request = _read_json(job_dir / "request.json")
    owner = _read_json(job_dir / "native_owner.json")
    log_path = job_dir / "native.log"
    log_bytes = b""
    if log_path.is_file():
        try:
            log_bytes = log_path.read_bytes()
        except OSError:
            log_bytes = b""
    log_text = log_bytes.decode("utf-8", errors="replace")
    message = str(manifest.get("message") or "")
    exit_match = _EXIT_CODE.search(message)
    exit_code = int(exit_match.group(1)) if exit_match else None
    model = request.get("model") if isinstance(request.get("model"), dict) else {}
    part_file = model.get("part_file")
    files = _output_files(job_dir)
    stl_files = [row for row in files if row["path"].lower().endswith(".stl")]
    native = _parse_native(log_text)
    return {
        "job_dir": str(job_dir),
        "job_id": manifest.get("job_id"),
        "kind": manifest.get("kind"),
        "model_id": manifest.get("model_id"),
        "status": manifest.get("status"),
        "message": message,
        "stage": manifest.get("stage"),
        "revision": manifest.get("revision"),
        "readonly": manifest.get("readonly"),
        "started_at": manifest.get("started_at"),
        "finished_at": manifest.get("finished_at"),
        "exit_code": exit_code,
        "exit_code_hex": f"0x{exit_code & 0xFFFFFFFF:08X}" if exit_code is not None else None,
        "worker": owner,
        "worker_process": {
            "pid": owner.get("pid"),
            "created": owner.get("created"),
            "alive": owner.get("alive"),
        },
        # Memory/liveness of Creo itself is a live observation; an offline job
        # directory cannot prove it, so this stays explicitly unavailable.
        "memory_observation": None,
        "native_log": {
            "bytes": len(log_bytes),
            "sha256": _sha256_bytes(log_bytes),
            "tail": log_text[-4000:],
            "tail_after_export": log_text.split("PHASE=export", 1)[-1][-2000:]
            if "PHASE=export" in log_text
            else None,
            **native,
        },
        "output_files": files,
        "stl_files": stl_files,
        "stl_total_bytes": sum(row["bytes"] or 0 for row in stl_files),
        "stl_zero_bytes": bool(stl_files) and all(row["zero_bytes"] for row in stl_files),
        "source": {
            "part_file": part_file,
            "recorded_sha256": model.get("part_sha256"),
            "actual_sha256": _sha256_file(Path(part_file)) if part_file else None,
            "actual_sha256_skipped": bool(
                part_file and _file_larger_than(Path(part_file), MAX_HASH_BYTES)
            ),
        },
        "request_operations": request.get("operations"),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Summarize persisted STL export jobs (offline).")
    parser.add_argument("jobs", nargs="+", help="job directories, e.g. jobs/<job_id>")
    args = parser.parse_args(argv)
    summaries = [summarize_stl_job(Path(item)) for item in args.jobs]
    print(
        json.dumps(summaries if len(summaries) > 1 else summaries[0], ensure_ascii=False, indent=2)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
