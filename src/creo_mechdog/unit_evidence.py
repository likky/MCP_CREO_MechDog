"""Bind a full unit-test report to the run that produced it (BUG-144).

``tools/test_unit.py`` writes the report only after the suite finishes. A
packaging gate that reads the same path can therefore see the previous round's
report while the current round is still running, after a timeout, or after an
interruption. The state file written here names the current run and is replaced
atomically with its terminal status, so an old success report cannot be mistaken
for this round.
"""

from __future__ import annotations

import ctypes
import json
import os
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
REPORT_NAME = "unit_test_report.json"
RUN_STATE_NAME = "unit_test_run.json"
LOCK_NAME = "unit_test_run.lock"
_STILL_ACTIVE = 259
_ERROR_INVALID_PARAMETER = 87


class UnitRunBusy(RuntimeError):
    """Another full unit run holds the evidence lock."""


def report_path(root: Path) -> Path:
    return Path(root) / "build" / REPORT_NAME


def run_state_path(report: Path) -> Path:
    return Path(report).parent / RUN_STATE_NAME


def lock_path(report: Path) -> Path:
    return Path(report).parent / LOCK_NAME


def _now() -> float:
    return time.time()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Publish ``payload`` without ever exposing a partially written file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError:
        return None
    try:
        value = json.loads(text)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def source_identity(provenance: dict[str, Any]) -> dict[str, Any]:
    """The subset both the run state and the report expose for comparison."""
    return {
        key: provenance.get(key)
        for key in (
            "commit",
            "branch",
            "dirty",
            "git_status",
            "source_fingerprint",
            "source_scope",
            "source_status",
            "source_file_count",
        )
    }


def start_run(
    report: Path,
    *,
    run_id: str,
    version: str,
    provenance: dict[str, Any],
    started_at: float | None = None,
) -> dict[str, Any]:
    state = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "status": "running",
        "success": None,
        "version": version,
        "pid": os.getpid(),
        "started_at": _now() if started_at is None else started_at,
        "finished_at": None,
        "source": source_identity(provenance),
    }
    write_json_atomic(run_state_path(report), state)
    return state


def finish_run(report: Path, *, run_id: str, success: bool) -> bool:
    """Mark the run completed; refuses a state that belongs to a newer run."""
    path = run_state_path(report)
    state = load_json(path)
    if state is None or state.get("run_id") != run_id:
        return False
    state.update(status="completed", success=bool(success), finished_at=_now())
    write_json_atomic(path, state)
    return True


def interrupt_run(report: Path, *, run_id: str, reason: str) -> bool:
    path = run_state_path(report)
    state = load_json(path)
    if state is None or state.get("run_id") != run_id:
        return False
    state.update(
        status="interrupted",
        success=False,
        finished_at=_now(),
        failure=reason,
    )
    write_json_atomic(path, state)
    return True


def load_run(report: Path) -> dict[str, Any] | None:
    return load_json(run_state_path(report))


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        query_limited_information = 0x1000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(query_limited_information, False, pid)
        if not handle:
            # ERROR_INVALID_PARAMETER is the only proof the PID is gone; an
            # access-denied answer is conservatively treated as still alive.
            return kernel32.GetLastError() != _ERROR_INVALID_PARAMETER
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True
            return code.value == _STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def acquire(report: Path, *, run_id: str) -> None:
    """Take the evidence lock, replacing a lock left by a dead process."""
    path = lock_path(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(2):
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            owner = load_json(path) or {}
            owner_pid = owner.get("pid")
            stale = attempt == 0 and (not isinstance(owner_pid, int) or not _pid_alive(owner_pid))
            if stale:
                try:
                    path.unlink()
                except OSError:
                    pass
                continue
            raise UnitRunBusy(
                f"another full unit run holds {path.name}"
                f" (pid={owner_pid!r}, run_id={owner.get('run_id')!r})"
            ) from None
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"pid": os.getpid(), "run_id": run_id, "started_at": _now()}, handle)
        return
    raise UnitRunBusy(f"could not acquire {path}")


def release(report: Path, *, run_id: str) -> None:
    """Release only our own lock; a newer run's lock is left untouched."""
    path = lock_path(report)
    owner = load_json(path) or {}
    if owner.get("run_id") != run_id:
        return
    try:
        path.unlink()
    except OSError:
        pass
