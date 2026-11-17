"""BUG-020: keep Creo export log excerpts out of the deliverable directory.

Step/IGES export through the Toolkit writes ``<model>__out.log.N`` next to the
requested ``.stp``/``.igs``. Those files are diagnostic excerpts owned by this
job, not deliverables. Move them to ``output/diagnostics`` and report both
lists on the job result so a caller can tell deliverables from diagnostics.

Only files inside this job's own ``output`` directory whose name contains
``_out.log`` are touched. Exported models and any caller files are left in
place; no file outside ``output`` is read, moved or deleted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

EXPORT_FORMATS = {"step", "stl", "iges", "jpeg", "pdf"}
MODEL_SUFFIXES = {".stp", ".step", ".igs", ".iges", ".stl"}


def _relative(path: Path, directory: Path) -> str:
    try:
        return path.relative_to(directory).as_posix()
    except ValueError:
        return str(path)


def apply(result: dict[str, Any] | None, directory: Path, operations: list[dict]) -> None:
    """Classify this job's export outputs in place; never raises on missing dirs."""
    if not isinstance(result, dict):
        return
    formats = {
        operation.get("format")
        for operation in operations
        if isinstance(operation, dict) and operation.get("op") == "export"
    }
    if not formats & EXPORT_FORMATS:
        return
    output = directory / "output"
    if not output.is_dir():
        return
    diagnostics_dir = output / "diagnostics"
    artifacts: list[str] = []
    diagnostics: list[str] = []
    for entry in sorted(output.iterdir()):
        if not entry.is_file():
            continue
        name = entry.name.lower()
        if "_out.log" in name:
            diagnostics_dir.mkdir(exist_ok=True)
            target = diagnostics_dir / entry.name
            entry.replace(target)
            diagnostics.append(_relative(target, directory))
        elif entry.suffix.lower() in MODEL_SUFFIXES:
            artifacts.append(_relative(entry, directory))
    if artifacts:
        result["export_artifacts"] = artifacts
    if diagnostics:
        result["export_diagnostics"] = diagnostics
        result["export_diagnostics_note"] = (
            "Creo *_out.log.N excerpts were moved to output/diagnostics; the exported "
            "files and any other caller files were not modified."
        )
