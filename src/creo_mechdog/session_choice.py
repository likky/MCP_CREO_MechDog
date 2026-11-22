"""FEAT-072: process-local Creo session selection.

``creo_session_id`` in ``config.json`` is read by ``Settings.load()`` and
``native_environment()`` whenever a worker starts, so editing the file changed
nothing for a running service: the 0.35.2 feedback had to restart the MCP
connector to leave ``selection_required``.

The Toolkit session id is the only address ``ProEngineerConnect`` accepts. Creo
10's ``ProCore.h`` declares ``ProProcessHandle`` as ``PeerIdx``, so a Windows PID
cannot be converted into one and this service cannot enumerate ids by itself
(FEAT-072 keeps ``selection_required`` for unregistered sessions). What it can do
is let a client that already knows an id -- from Creo's own Session Info, or from
an id that worked before -- pin this process without touching ``config.json``.

The override lives in process memory only. It is never written to disk, never
survives a restart and never substitutes for a missing target: an id that no
session answers keeps failing with ``PRO_TK_E_NOT_FOUND`` instead of falling back
(the native worker re-checks ``ProEngineerConnectIdGet``).

Only a fingerprint is ever returned to a caller. The raw id is a connection
handle, and the native side already refuses to persist or return it
(``recovery_session_fingerprint``).
"""

from __future__ import annotations

import hashlib
import threading

MAX_LENGTH = 128
_FINGERPRINT_LENGTH = 16
_CONTROL = "\r\n\0\t"
_OVERRIDE: str | None = None
_LOCK = threading.Lock()


class SelectionError(ValueError):
    """The requested session id cannot be used as a selection."""


def normalize(value: object) -> str:
    """Validate one session id exactly as the native connection expects it."""
    if not isinstance(value, str):
        raise SelectionError("session_id must be a string")
    if not value.strip():
        raise SelectionError("session_id must not be empty")
    if any(character in value for character in _CONTROL):
        raise SelectionError("session_id must not contain control characters")
    if len(value) > MAX_LENGTH:
        raise SelectionError(f"session_id must be at most {MAX_LENGTH} characters")
    return value


def fingerprint(value: str) -> str:
    """Stable short digest so callers can tell selections apart without the id."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:_FINGERPRINT_LENGTH]


def set_override(value: object) -> None:
    """Pin this process to one session id; never touches config.json."""
    global _OVERRIDE
    normalized = normalize(value)
    with _LOCK:
        _OVERRIDE = normalized


def clear_override() -> None:
    global _OVERRIDE
    with _LOCK:
        _OVERRIDE = None


def override() -> str | None:
    with _LOCK:
        return _OVERRIDE


def selected(config: dict) -> str | None:
    """The effective target: the runtime override wins over the configured id."""
    value = override()
    if value:
        return value
    configured = config.get("creo_session_id") if isinstance(config, dict) else None
    return configured or None


def describe(config: dict) -> dict:
    """Which selection applies, without returning the handle itself."""
    override_value = override()
    configured = config.get("creo_session_id") if isinstance(config, dict) else None
    configured = configured or None
    if override_value:
        source = "runtime_override"
        value = override_value
        persistence = "process memory only; config.json is unchanged"
    elif configured:
        source = "config"
        value = configured
        persistence = "config.json (re-read by the next worker start)"
    else:
        source = "none"
        value = None
        persistence = None
    return {
        "source": source,
        "applies_to": "every native worker this service starts, including startup probes",
        "override_active": bool(override_value),
        "configured": bool(configured),
        "session_fingerprint": fingerprint(value) if value else None,
        "scope": "process",
        "persistence": persistence,
        "raw_id_returned": False,
        "note": (
            "A selection is a target, not a fallback: an id no session answers keeps failing "
            "instead of connecting to another Creo"
        ),
    }
