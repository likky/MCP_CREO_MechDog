"""Bounded progress for a resident panel wait (BUG-120/D4.3).

A resident panel job spends time waiting for a human or a replayed command
sequence to finish, and the native worker cannot write to ``worker.log`` while it
waits for that dialog to close. The existing stall watchdog only counts bytes in
``worker.log``, so a legitimate wait looks exactly like a hang.

The worker publishes its wait state to ``panel_wait.json`` in the job directory:

.. code-block:: json

    {"job_id": "...", "nonce": "...", "profile_id": "...", "seq": 4,
     "phase": "panel_done_wait", "at_epoch_ms": 1700000000123}

Rules this module enforces:

- only this job's marker counts: a mismatched ``job_id``, ``nonce`` or profile is
  ignored, never treated as progress;
- only an increasing ``seq`` and a known phase count, so a rewritten identical
  marker, an old marker from a previous run or a bare heartbeat cannot extend a
  wait;
- a trusted wait phase gets a bounded deadline of its own, measured from when this
  watcher first saw that phase (the sidecar cannot extend it), and that deadline is
  never later than the job's own budget;
- anything else keeps the ordinary stall contract.

The decision is a pure function of the marker, the clock and the budgets, so it can
be tested without a worker, a dialog or a real clock.
"""

from __future__ import annotations

import json
from pathlib import Path

WAIT_FILE = "panel_wait.json"

#: Wait phases the native panel backend may publish. A phase outside this set is
#: not a licence to wait: the ordinary stall budget still applies.
TRUSTED_PHASES = ("panel_open_wait", "panel_select_wait", "panel_done_wait", "panel_close_wait")

FIELDS = ("job_id", "nonce", "profile_id", "seq", "phase", "at_epoch_ms")


def read_marker(path: Path) -> dict | None:
    """The marker as written, or ``None`` when it is absent or not trustworthy.

    Every field is checked: a marker that cannot be read completely is ignored
    rather than half-believed.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        record = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(record, dict):
        return None
    for field in FIELDS:
        if field not in record:
            return None
    for field in ("job_id", "nonce", "profile_id", "phase"):
        if not isinstance(record[field], str) or not record[field]:
            return None
    for field in ("seq", "at_epoch_ms"):
        if type(record[field]) is not int or record[field] < 0:
            return None
    return record


def matches(record: dict | None, *, job_id: str, nonce: str | None, profile_id: str | None) -> bool:
    """True only when this marker belongs to the job asking about it."""
    if record is None:
        return False
    if record.get("job_id") != job_id:
        return False
    if nonce and record.get("nonce") != nonce:
        return False
    if profile_id and record.get("profile_id") != profile_id:
        return False
    return True


def tick(
    state: dict,
    record: dict | None,
    now: float,
    *,
    stall_budget: float,
    phase_budget: float,
    job_deadline_at: float | None,
) -> dict:
    """Advance the wait bookkeeping and say whether the worker may keep running.

    ``state`` is the watcher's own dictionary and is updated in place so the caller
    keeps one source of truth. Returns ``{"action": "continue"|"terminate",
    "reason": str|None, "evidence": dict}``.
    """
    phase = state.get("phase")
    last_seq = state.get("last_seq")
    progress = False
    if record is not None and record.get("phase") in TRUSTED_PHASES:
        if record["phase"] != phase:
            # A new phase starts its own bounded window; a repeated marker does not
            # restart it, so a looping writer cannot extend the wait.
            state["phase"] = record["phase"]
            state["phase_started_at"] = now
            phase = record["phase"]
        if last_seq is None or record["seq"] > last_seq:
            state["last_seq"] = record["seq"]
            state["last_progress_at"] = now
            progress = True
    elif record is not None and record.get("phase") not in TRUSTED_PHASES:
        state["phase"] = None
        state["phase_started_at"] = None
        phase = None

    if job_deadline_at is not None and now >= job_deadline_at:
        return {
            "action": "terminate",
            "reason": "panel_job_deadline",
            "evidence": {
                "phase": state.get("phase"),
                "last_seq": state.get("last_seq"),
                "job_deadline_reached": True,
            },
        }
    if phase:
        started = state.get("phase_started_at")
        if started is not None and now - started >= phase_budget:
            return {
                "action": "terminate",
                "reason": "panel_phase_deadline",
                "evidence": {
                    "phase": phase,
                    "phase_seconds": round(now - started),
                    "phase_budget_seconds": round(phase_budget),
                    "last_seq": state.get("last_seq"),
                    "last_progress_at": state.get("last_progress_at"),
                },
            }
        return {
            "action": "continue",
            "reason": None,
            "evidence": {"phase": phase, "progressed": progress, "phase_limited": True},
        }
    silence = now - float(state.get("last_growth", now))
    if silence >= stall_budget:
        return {
            "action": "terminate",
            "reason": "stall",
            "evidence": {
                "silent_seconds": round(silence),
                "stall_budget_seconds": round(stall_budget),
            },
        }
    return {"action": "continue", "reason": None, "evidence": {"progressed": progress}}
