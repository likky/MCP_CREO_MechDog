"""Bounded attribution of the native worker's last stage (BUG-109).

The 0.11.5 Creo 9 report showed a first-build job stopping after
``PHASE=verify_model`` for about ten minutes with no further log line: one
phase name covered regeneration, inspection, assertions, backup, erase,
reload, comparison and preview, so "still working" and "hung" looked the same
until the 600 s budget expired.

This module reads bounded head and tail windows of ``native.log`` and never
touches the worker. Sub-stages are emitted by ``native/generic.cpp`` as::

    STAGE name=verify_model_save elapsed_ms=41 since_start_ms=1200 ts=1700000000123

``ts`` is the worker's wall clock in epoch milliseconds, so a caller can tell
how long the last sub-stage has been silent. Logs written before this change
have only ``PHASE=`` lines: they keep working and report
``reason="no_stage_timing"`` instead of inventing timings.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

#: Bounded windows keep polling cost independent of log size.
TAIL_BYTES = 8192
HEAD_BYTES = 4096
#: Hard bound on parsed lines even if a log line is extremely long.
MAX_SCAN_LINES = 200
#: B3/F06: the 0.19.0 report measured 3-7.7 MB native logs. This is a
#: reporting threshold only: the reader never truncates or rewrites the
#: worker's log, and terminal errors stay in it. The per-operation PROGRESS
#: line is the bounded "per-feature log summary" that report asked for as an
#: alternative to limiting the log itself.
LOG_SOFT_LIMIT_BYTES = 1 << 20
#: BUG-131/P5-3: a looping operation keeps writing diagnostic lines after its
#: last ``PHASE=`` marker. A 0.26.0 report showed the marker pushed out of the
#: 8 KiB tail, so the poll said ``no_phase_lines`` for over 30 minutes even
#: though the worker had never left ``assemble_component:hom_1``. When the
#: bounded tail holds no marker at all, widen the backward search to this cap
#: instead of reporting the log as empty of stages.
MARKER_SCAN_MAX_BYTES = 1 << 20
#: Hard bound on lines read by the widened scan; the cap keeps one poll cheap
#: even for a 1 MiB window of short diagnostic lines.
MAX_EXTENDED_LINES = 20000
#: Repeated-line evidence is only reported when the same line recurs at least
#: this often; a single diagnostic line is not a spin signature.
DOMINANT_LINE_MIN_COUNT = 3
#: The dominant line is echoed as evidence, not as a log dump.
DOMINANT_LINE_MAX_CHARS = 120

_PHASE = re.compile(r"^PHASE=(.+)$")
_STAGE = re.compile(r"^STAGE\s+(.+)$")
_PROGRESS = re.compile(r"^PROGRESS\s+(.+)$")
_FIELD = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(\S+)")
_PROGRESS_STATES = ("start", "done")


def _empty() -> dict[str, Any]:
    return {
        "readable": False,
        "log_bytes": None,
        "tail_bytes": TAIL_BYTES,
        "truncated": False,
        "log_over_soft_limit": False,
        "stage": None,
        "sub_stage": None,
        "elapsed_ms": None,
        "since_start_ms": None,
        "idle_seconds": None,
        "log_age_seconds": None,
        "stages_seen": 0,
        "marker_scan_bytes": 0,
        "marker_source": None,
        "dominant_tail_line": None,
        "dominant_tail_line_count": 0,
        "connect_timing": {},
        "timing_source": "native_log",
        "reason": None,
        "operation_index": None,
        "operation_total": None,
        "operation_label": None,
        "operation_state": None,
        "progress_elapsed_ms": None,
        "progress_text": None,
    }


def _integer(text: Any) -> int | None:
    if text is None:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _progress_fields(line: str) -> dict[str, Any] | None:
    """Validate one PROGRESS marker; a malformed line never becomes progress."""
    fields = dict(_FIELD.findall(line))
    index = _integer(fields.get("index"))
    total = _integer(fields.get("total"))
    state = fields.get("state")
    op, label = fields.get("op"), fields.get("label")
    if (
        index is None
        or total is None
        or total <= 0
        or not 1 <= index <= total
        or state not in _PROGRESS_STATES
        or not op
        or not label
    ):
        return None
    # The worker writes "-" for operations whose schema has no label. That is
    # an explicit absence, not a value to echo back as if it were measured.
    text_label = op if label == "-" else f"{op}:{label}"
    return {
        "operation_index": index,
        "operation_total": total,
        "operation_label": None if label == "-" else label,
        "operation_state": state,
        "progress_elapsed_ms": _integer(fields.get("elapsed_ms")),
        "progress_text": f"{index}/{total} {text_label} {state}",
    }


def _now_ms(now: datetime | None) -> int:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return int(moment.timestamp() * 1000)


def _read_tail(path: Path, tail_bytes: int) -> tuple[bytes | None, int | None, str | None]:
    """Return ``(tail_bytes_read, total_size, error)`` without raising."""
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return None, None, "native_log_missing"
    except OSError as exc:  # pragma: no cover - platform dependent
        return None, None, f"native_log_unreadable:{type(exc).__name__}"
    try:
        with path.open("rb") as handle:
            start = max(0, size - tail_bytes)
            handle.seek(max(0, start - 1))
            chunk = handle.read(tail_bytes + (1 if start else 0))
            if start:
                previous, chunk = chunk[:1], chunk[1:]
                if previous not in (b"\n", b"\r"):
                    newline = chunk.find(b"\n")
                    chunk = chunk[newline + 1 :] if newline >= 0 else b""
            return chunk, size, None
    except OSError as exc:  # pragma: no cover - platform dependent
        return None, size, f"native_log_unreadable:{type(exc).__name__}"


def _connect_timing(path: Path) -> dict[str, dict[str, int | None]]:
    """Read only complete connect markers in the log head, independently of the tail."""
    try:
        with path.open("rb") as handle:
            raw = handle.read(HEAD_BYTES)
    except OSError:  # pragma: no cover - platform dependent
        return {}
    result: dict[str, dict[str, int | None]] = {}
    head_text = raw.decode("utf-8", errors="replace")
    head_lines = head_text.splitlines()
    if head_text and not head_text.endswith(("\n", "\r")):
        head_lines = head_lines[:-1]
    for line in head_lines:
        staged = _STAGE.match(line)
        if not staged:
            continue
        fields = dict(_FIELD.findall(staged.group(1)))
        name = fields.get("name")
        if name in ("connect", "connected"):
            result[name] = {
                "elapsed_ms": _integer(fields.get("elapsed_ms")),
                "since_start_ms": _integer(fields.get("since_start_ms")),
                "ts": _integer(fields.get("ts")),
            }
    return result


def _verify_timing(stages: Any) -> dict[str, dict[str, int | None]]:
    """Project the job's own ``result.verify_stages`` connect markers.

    These entries carry elapsed/since-start timings but no worker timestamp, so
    ``ts`` stays null and ``idle_seconds`` is never inferred from them.
    """
    if not isinstance(stages, (list, tuple)):
        return {}
    result: dict[str, dict[str, int | None]] = {}
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        name = stage.get("name")
        if name not in ("connect", "connected"):
            continue
        result[name] = {
            "elapsed_ms": _integer(stage.get("elapsed_ms")),
            "since_start_ms": _integer(stage.get("since_start_ms")),
            "ts": None,
        }
    return result


def _decoded_lines(raw: bytes) -> list[str]:
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    # A partially flushed last line must not be read as a completed sub-stage.
    if text and not text.endswith(("\n", "\r")):
        lines = lines[:-1]
    return lines


def _lines(raw: bytes) -> list[str]:
    return _decoded_lines(raw)[-MAX_SCAN_LINES:]


def _window_lines(raw: bytes) -> list[str]:
    """The widened window, still bounded, keeping the newest complete lines."""
    return _decoded_lines(raw)[-MAX_EXTENDED_LINES:]


def _marker_scan(lines: list[str], *, include_progress: bool = True) -> dict[str, Any]:
    """The latest PHASE/PROGRESS/STAGE marker in one ordered line window.

    ``include_progress`` stays False for the widened window: a PROGRESS line
    older than the bounded tail must not be backfilled as current progress, even
    though a PHASE/STAGE marker from the same window is still valid stage
    attribution.
    """
    stage = None
    sub_stage = None
    timing: dict[str, str] = {}
    seen = 0
    progress: dict[str, Any] | None = None
    for line in lines:
        phase = _PHASE.match(line)
        if phase:
            next_stage = phase.group(1).strip()
            if next_stage and next_stage != stage:
                stage = next_stage
                sub_stage = None
                timing = {}
            continue
        progress_match = _PROGRESS.match(line)
        if progress_match:
            parsed = _progress_fields(progress_match.group(1))
            if parsed and include_progress:
                progress = parsed
            continue
        staged = _STAGE.match(line)
        if not staged:
            continue
        seen += 1
        fields = dict(_FIELD.findall(staged.group(1)))
        name = fields.get("name")
        if name:
            sub_stage = name
            timing = fields
    return {
        "stage": stage,
        "sub_stage": sub_stage,
        "timing": timing,
        "stages_seen": seen,
        "progress": progress,
    }


def _has_marker(scan: dict[str, Any]) -> bool:
    return (
        scan["stage"] is not None or scan["sub_stage"] is not None or scan["progress"] is not None
    )


def _dominant_line(lines: list[str]) -> tuple[str | None, int]:
    """The most repeated non-empty line, only when repetition is a real signal.

    A looping operation writes one diagnostic over and over, so the count is
    evidence of a spin rather than a slow rebuild. One-off lines stay unreported
    and the echoed text stays bounded.
    """
    counts = Counter(line.strip() for line in lines if line.strip())
    if not counts:
        return None, 0
    line, count = counts.most_common(1)[0]
    if count < DOMINANT_LINE_MIN_COUNT:
        return None, count
    return line[:DOMINANT_LINE_MAX_CHARS], count


def stall_report(
    directory: Path | str,
    *,
    tail_bytes: int = TAIL_BYTES,
    verify_stages: Any = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Summarise the last phase/sub-stage of ``<directory>/native.log``.

    Returns a bounded, read-only projection. Missing or unreadable logs are
    reported explicitly (``readable=False`` plus ``reason``). When the log is
    truncated and its tail has no sub-stage, ``verify_stages`` from the job's
    own result supplies connect/connected timing instead of reporting
    ``no_stage_timing``; ``timing_source`` names which evidence was used.

    BUG-131/P5-3: when the tail holds no marker at all, the scan widens to
    ``MARKER_SCAN_MAX_BYTES`` before concluding there is no stage, because a
    spinning operation can push its last ``PHASE=`` line out of the tail window.
    ``marker_source`` says which window supplied the answer, ``log_age_seconds``
    says how long the log has been silent, and ``dominant_tail_line`` names a
    line repeated often enough to look like a loop.
    """
    report = _empty()
    report["tail_bytes"] = tail_bytes
    log_path = Path(directory) / "native.log"
    raw, size, error = _read_tail(log_path, tail_bytes)
    report["log_bytes"] = size
    if error:
        report["reason"] = error
        return report
    report["readable"] = True
    report["connect_timing"] = _connect_timing(log_path)
    if size is not None:
        report["truncated"] = size > tail_bytes
        report["log_over_soft_limit"] = size > LOG_SOFT_LIMIT_BYTES
    try:
        report["log_age_seconds"] = round(
            max(0.0, _now_ms(now) / 1000.0 - log_path.stat().st_mtime), 3
        )
    except OSError:  # pragma: no cover - race with log rotation
        report["log_age_seconds"] = None
    fallback = _verify_timing(verify_stages) if report["truncated"] else {}

    tail_lines = _lines(raw or b"")
    report["dominant_tail_line"], report["dominant_tail_line_count"] = _dominant_line(tail_lines)
    report["marker_scan_bytes"] = len(raw or b"")
    scan = _marker_scan(tail_lines)
    if _has_marker(scan):
        report["marker_source"] = "tail"
    else:
        report["marker_source"] = "none"
        if size is not None and size > len(raw or b""):
            widened, _, widened_error = _read_tail(log_path, min(size, MARKER_SCAN_MAX_BYTES))
            if widened and not widened_error:
                report["marker_scan_bytes"] = len(widened)
                widened_scan = _marker_scan(_window_lines(widened), include_progress=False)
                if _has_marker(widened_scan):
                    scan = widened_scan
                    report["marker_source"] = "extended"

    stage = scan["stage"]
    sub_stage = scan["sub_stage"]
    timing = scan["timing"]
    seen = scan["stages_seen"]
    progress = scan["progress"]

    if progress:
        report.update(progress)
    report["stage"] = stage
    report["sub_stage"] = sub_stage
    report["stages_seen"] = seen
    if sub_stage is None:
        if fallback:
            for name, timing in fallback.items():
                report["connect_timing"].setdefault(name, timing)
            if seen == 0:
                report["stages_seen"] = len(fallback)
            report["timing_source"] = "verify_stages"
        report["reason"] = (
            "no_phase_lines"
            if stage is None
            else "no_current_stage_timing"
            if report["connect_timing"]
            else "no_stage_timing"
        )
        return report

    elapsed = _integer(timing.get("elapsed_ms"))
    since_start = _integer(timing.get("since_start_ms"))
    timestamp = _integer(timing.get("ts"))
    report["elapsed_ms"] = elapsed
    report["since_start_ms"] = since_start
    if timestamp is None:
        report["reason"] = "no_stage_timing"
        return report
    report["idle_seconds"] = round(max(0.0, (_now_ms(now) - timestamp) / 1000.0), 3)
    return report
