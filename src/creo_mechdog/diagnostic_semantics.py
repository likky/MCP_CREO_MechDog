"""DEV-098: interpretation of receipts that carry two different counting channels.

Two 0.33.0 feedback items are about reading a receipt, not about computing
geometry, so they are kept here as pure functions:

* :func:`describe_profile_consistency` compares the analytic ``profile`` block
  of a sketch result with the solved ``native_section`` block. The analytic
  report (``profile_diagnostics``) expands only line/arc/circle/rectangle/
  polyline input; ``b_spline``, ``spline`` and ``ellipse`` are listed under
  ``categories.unsupported`` and set ``analysis="partial"``. Its entity/contour
  counts are therefore a lower bound, and a mismatch with ``native_section`` is
  not evidence that the kernel lost a contour.

* :func:`closure_semantics` separates the three meanings behind a quilt
  ``closure`` block produced by ``ProQuiltVolumeEval`` (native/surface_measure.h):
  a returned volume, a kernel-reported open quilt, and a failed volume
  evaluation. None of them proves topological closure or predicts ``solidify``.

Neither function recomputes geometry, and neither upgrades an unknown into
``True`` or ``False``.
"""

from __future__ import annotations

from typing import Any

#: Pairs of analytic ``profile`` count and the ``native_section`` count that
#: describes the same quantity. ``open_contours`` is only produced by the native
#: block; the analytic report publishes ``open_contour_count``.
COUNT_PAIRS = (
    ("entity_count", "entities"),
    ("contour_count", "contours"),
    ("closed_contour_count", "closed_contours"),
)

PARTIAL_NOTE = (
    "the analytic profile was computed from the supplied coordinates only and "
    "listed unsupported curve entities (for example b_spline), so analysis is "
    "'partial': its entity/contour counts are lower bounds and must not be read "
    "as the kernel section. Use native_section for the solved section, and "
    "creo_measure_surface_group for quilt topology."
)


def _category_count(categories: Any, name: str) -> int | None:
    """Read one category count from either projection of the analyzer report.

    ``analyze_profile`` keeps ``{count, items, truncated}`` per category while
    the public ``profile`` projection keeps the bare count. Both are accepted;
    anything else stays ``None`` instead of being coerced.
    """
    if not isinstance(categories, dict):
        return None
    entry = categories.get(name)
    if isinstance(entry, dict):
        value = entry.get("count")
    else:
        value = entry
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def describe_profile_consistency(profile: Any, native_section: Any = None) -> dict[str, Any]:
    """Classify ``profile`` vs ``native_section`` without inventing a verdict.

    ``consistent`` is ``True``/``False`` only when a complete analytic report
    can be compared field by field with an available native section. A partial
    report, a missing native section or an unavailable one stays ``None`` with a
    ``reason`` that names the missing evidence.
    """
    result: dict[str, Any] = {
        "available": False,
        "consistent": None,
        "analysis": None,
        "reason": None,
        "unsupported_count": None,
        "differences": [],
        "compared": [],
        "scope": "diagnostic only: never rejects or re-grades a delivered sketch",
    }
    if not isinstance(profile, dict):
        result["reason"] = "no analytic profile block"
        return result
    analysis = profile.get("analysis")
    result["analysis"] = analysis if isinstance(analysis, str) else None
    if analysis == "unavailable" or not isinstance(analysis, str):
        result["reason"] = "the analytic profile analysis is unavailable"
        return result
    result["available"] = True
    result["unsupported_count"] = _category_count(profile.get("categories"), "unsupported")
    if analysis != "complete":
        result["reason"] = "analytic_analysis_partial"
        result["note"] = PARTIAL_NOTE
        return result
    if not isinstance(native_section, dict):
        result["reason"] = "no solved native section accompanies this profile"
        return result
    if native_section.get("available") is not True:
        result["reason"] = "the native section is reported unavailable"
        return result
    differences = []
    compared = []
    for analytic_key, native_key in COUNT_PAIRS:
        analytic = profile.get(analytic_key)
        native = native_section.get(native_key)
        if isinstance(analytic, bool) or not isinstance(analytic, int):
            continue
        if isinstance(native, bool) or not isinstance(native, int):
            continue
        entry = {"field": analytic_key, "profile": analytic, "native_section": native}
        compared.append(entry)
        if analytic != native:
            differences.append(entry)
    if not compared:
        result["reason"] = "no shared count to compare"
        return result
    result["compared"] = compared
    result["differences"] = differences
    result["consistent"] = not differences
    if differences:
        result["reason"] = "analytic and native counts disagree on a complete analysis"
    return result


#: Values of ``closure.volume_state``; the first three mirror the native reasons
#: and the last one is "the block did not say".
VOLUME_STATES = ("available", "open", "failed", "unknown")


def closure_volume_state(closure: Any) -> str:
    """Classify one ``closure`` block by what the native probe reported.

    ``native/surface_measure.h`` sets ``available`` with the measured volume on
    ``PRO_TK_NO_ERROR``, ``reason="quilt_is_open"`` on
    ``PRO_TK_INVALID_TYPE``, and ``reason="quilt_volume_eval_failed"`` for every
    other failure. Only those names are read here; no numeric code is
    reinterpreted.
    """
    if not isinstance(closure, dict):
        return "unknown"
    reason = closure.get("reason")
    if reason == "quilt_is_open":
        return "open"
    if reason == "quilt_volume_eval_failed":
        return "failed"
    if closure.get("available") is True:
        return "available"
    return "unknown"


def closure_semantics(
    closure: Any = None, *, solidify: Any = None, group: Any = None
) -> dict[str, Any]:
    """Describe the three closure questions separately.

    * ``volume_state`` - what ``ProQuiltVolumeEval`` answered (see above);
    * ``topologically_closed`` - only from a ``creo_measure_surface_group``
      receipt's ``boundary_closed``; the volume probe never proves edge pairing;
    * ``solidifiable`` - only from the outcome of an actual ``solidify`` record
      (``effect_status``); the volume probe never predicts it.

    A 3-face shell whose volume query failed (``-62``,
    ``quilt_volume_eval_failed``) and then solidified successfully is a recorded
    observation, not a contradiction; an ``available`` volume on a single fill
    face does not prove a closed shell either.
    """
    state = closure_volume_state(closure)
    topologically_closed = None
    topology_basis = "not_measured"
    if isinstance(group, dict):
        boundary_closed = group.get("boundary_closed")
        if isinstance(boundary_closed, bool):
            topologically_closed = boundary_closed
            topology_basis = "surface_group.boundary_closed"
    solidifiable = None
    solidifiable_basis = "not_run"
    if isinstance(solidify, dict):
        effect = solidify.get("effect_status")
        if effect == "committed":
            solidifiable = True
            solidifiable_basis = "solidify.effect_status"
        elif effect in ("rolled_back", "no_effect"):
            solidifiable = False
            solidifiable_basis = "solidify.effect_status"
    notes = []
    if state == "failed":
        notes.append(
            "the volume query failed; this says nothing about the boundary or about "
            "whether solidify can consume the quilt"
        )
    elif state == "open":
        notes.append("the kernel reported the quilt open to ProQuiltVolumeEval")
    elif state == "available":
        notes.append(
            "a volume was returned; a single fill face can also report a volume, so "
            "this is not proof of a closed shell"
        )
    if topologically_closed is None:
        notes.append(
            "topological closure needs creo_measure_surface_group "
            "(state/boundary_closed, open_edge_records)"
        )
    if solidifiable is None:
        notes.append("solidify was not run, so solidifiability stays unknown")
    return {
        "volume_state": state,
        "volume_query_code": closure.get("query_code") if isinstance(closure, dict) else None,
        "volume_reason": closure.get("reason") if isinstance(closure, dict) else None,
        "topologically_closed": topologically_closed,
        "topologically_closed_basis": topology_basis,
        "solidifiable": solidifiable,
        "solidifiable_basis": solidifiable_basis,
        "notes": notes,
    }
