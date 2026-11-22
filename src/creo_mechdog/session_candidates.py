"""FEAT-072: read-only Creo session candidates for an ambiguous connection.

0.35.2 feedback: with two Creo groups running, the Toolkit probe returned
``-36`` (``PRO_TK_E_AMBIGUOUS``) and ``creo_startup_status`` answered
``selection_required``, but no tool listed the sessions a client could choose
from, so an unattended client could only ask a human to close one.

What this module may report is bounded by what is actually observable:

* Process evidence comes from ``process_snapshot`` (pid, image, creation time,
  whether the image matches the configured installation, window state).
* A Toolkit session id is *not* observable for a process. Creo 10's
  ``ProCore.h`` declares ``ProProcessHandle`` as ``PeerIdx`` and
  ``ProEngineerConnectIdGet`` only answers for a connection this worker already
  owns, so there is no PID -> session id mapping to publish.
* Window titles, and therefore model names, are deliberately not read.

A candidate is therefore ``identified`` only when the caller already holds the
id and its fingerprint matches recorded evidence; otherwise it is listed with
``identified: false`` and the reason, which is the honest answer instead of a
guessed id. Selection itself is handled by ``session_choice`` (process-local,
no restart) and is always a target, never a fallback.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

PAGE_LIMIT = 24
JOB_BYTES = 2 * 1024 * 1024
CACHE_SECONDS = 20.0
UNIDENTIFIED = (
    "Toolkit exposes a session id only for a connection this worker already owns; "
    "Creo 10 declares ProProcessHandle as PeerIdx, so a Windows PID cannot be "
    "converted into one. Use the id Creo reports (Session Info) or one that worked "
    "before, then select it explicitly"
)
_CACHE: dict[str, tuple[float, dict]] = {}


def recorded_fingerprint(root: Path) -> dict:
    """Fingerprint of the most recent job that recorded a verified connection.

    Only the hash the native side already publishes is read; the raw id is never
    written by the worker, so it cannot leak from here. Status polling repeats
    this call, so the scan is bounded and cached briefly.
    """
    key = str(root)
    cached = _CACHE.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]
    value = _scan(root)
    _CACHE[key] = (time.monotonic(), value)
    return value


def _scan(root: Path) -> dict:
    jobs = root / "jobs"
    if not jobs.is_dir():
        return {"available": False, "reason": "no_job_history"}
    try:
        directories = [path for path in jobs.iterdir() if path.is_dir() and not path.is_symlink()]
        directories.sort(key=lambda path: path.stat().st_mtime_ns, reverse=True)
    except OSError:
        return {"available": False, "reason": "job_directory_unreadable"}
    for directory in directories[:PAGE_LIMIT]:
        manifest = directory / "job.json"
        try:
            if manifest.stat().st_size > JOB_BYTES:
                continue
            value = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        result = value.get("result") if isinstance(value, dict) else None
        if not isinstance(result, dict):
            continue
        fingerprint = result.get("session_fingerprint")
        if isinstance(fingerprint, str) and fingerprint:
            return {
                "available": True,
                "session_fingerprint": fingerprint[:64],
                "job_id": value.get("job_id"),
                "recorded_at": value.get("updated_at") or value.get("created_at"),
                "note": (
                    "Hash recorded by the native worker for the session it connected to. It "
                    "identifies a session but is not accepted as a connect id."
                ),
            }
    return {"available": False, "reason": "no_job_recorded_a_verified_session"}


def build(snapshot: dict, selection: dict, evidence: dict | None = None) -> dict:
    """Describe every observable Creo process and what can be chosen from it."""
    available = bool(snapshot.get("available"))
    rows = snapshot.get("processes") if isinstance(snapshot.get("processes"), list) else []
    candidates = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        windows = row.get("windows") if isinstance(row.get("windows"), dict) else {}
        candidates.append(
            {
                "pid": row.get("pid"),
                "name": row.get("name"),
                "created_at": row.get("created_at"),
                "matches_configured_installation": row.get("matches"),
                "window_state": windows.get("state", "unknown"),
                "visible_hung_window_observed": windows.get("visible_hung_window_observed", False),
                "identified": False,
                "session_id": None,
                "session_id_unknown_reason": UNIDENTIFIED,
            }
        )
    evidence = evidence if isinstance(evidence, dict) else {}
    selected_fingerprint = selection.get("session_fingerprint")
    known = evidence.get("session_fingerprint")
    return {
        "read_only": True,
        "available": available,
        "reason": snapshot.get("reason") if not available else None,
        "observed_at": snapshot.get("observed_at"),
        "count": len(candidates),
        # One Creo session shows up as parametric.exe plus xtop.exe, so the
        # process count is evidence, not a verdict: only toolkit_code=-36 proves
        # that several sessions actually match.
        "ambiguity": {
            "observed": (
                ("multiple_processes" if len(candidates) > 1 else "single_process")
                if candidates
                else "none_observed"
            )
            if available
            else "unknown",
            "proven_by_toolkit": None,
            "note": (
                "A successful probe means no selection is needed; only toolkit_code=-36 "
                "means several sessions match"
            ),
        },
        "uncertain_identity": bool(snapshot.get("uncertain")),
        "identification": {
            "process_to_session_id": "unsupported",
            "basis": (
                "Creo 10 ProCore.h declares ProProcessHandle as PeerIdx; a session id is "
                "available only through an existing Toolkit connection"
            ),
            "window_titles_read": False,
            "window_title_unavailable_reason": (
                "Candidates stay read-only; window titles and model names are not read"
            ),
            "recorded_session_fingerprint": evidence or None,
            "selected_fingerprint_matches_recorded": (
                None if not (selected_fingerprint and known) else selected_fingerprint == known
            ),
        },
        "selection": selection,
        "candidates": candidates,
        "next_step": (
            "If the probe returns toolkit_code=-36, select the intended session with "
            "creo_startup_status(retry=true, session_id=...); the id is validated against that "
            "session and never replaced by another one. Closing the extra Creo remains the "
            "fallback and is never automatic"
            if len(candidates) > 1
            else "No selection is needed for a single observed process; a configured or "
            "selected id that is absent still refuses to fall back to another session"
        ),
    }
