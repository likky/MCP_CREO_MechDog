"""First-wall section contract and sheetmetal result projections.

DEV-051 T03 / BUG-032. `creo_sheetmetal_wall` builds the first wall as a thin
extrusion of the sketch section and then converts that body into a native
sheetmetal wall. The conversion re-drives the body from one driving face, so
only one open straight line has a defined depth/thickness geometry:

    volume = line length x thickness x depth

Any other section (closed contour, arc, spline, multi-entity chain) would be
rebuilt from an arbitrary face: the reported closed rectangle kept the same
volume for depth 1 and depth 30, i.e. the depth was silently dropped. Admission
rejects those sections before the native modelling step, and the native
operation enforces the same rule for cross-job sketch references that Python
cannot inspect.

DEV-053 P08 / BUG-032 / FEAT-014: the depth/thickness frame projection and the
bounded wall-contour (candidate edge) projection live here. Both follow the
same three rules as the operation result projections: values are only ever the
executor's own measurements (never request echoes), a missing record stays
missing, and a record whose numbers cannot be trusted degrades to explicit
unknown while keeping the raw query code.
"""

from __future__ import annotations

import math
from typing import Any

_UNSUPPORTED = (
    "closed contours, arcs, splines and multi-entity chains are not supported for the first wall"
)


def first_wall_section_problem(entities: list[dict[str, Any]]) -> str | None:
    """Return why a section cannot drive a first wall, or None when it can."""
    drawing = [
        entity
        for entity in entities
        if entity.get("type") != "centerline" and not entity.get("construction")
    ]
    if len(drawing) != 1:
        return (
            "sheetmetal_wall needs exactly one open straight line as the first wall section; "
            f"got {len(drawing)} drawing entities ({_UNSUPPORTED})"
        )
    kind = drawing[0].get("type")
    if kind != "line":
        return (
            "sheetmetal_wall needs exactly one open straight line as the first wall section; "
            f"got a {kind!r} entity ({_UNSUPPORTED})"
        )
    return None


# BUG-046 / DEV-051 T04: a solid protrusion that merges into an existing
# sheetmetal body is refused by Creo with a bare ProFeatureWithoptionsCreate -1.
# Live isolation on Creo 12.4.0.0 (2026-10-29) measured the three cases that fix
# the boundary: the same add over the sheet and far away from it both return -1
# with no element errors, the same rectangle as a cut removes 100 mm3, and the
# same add with new_body=true succeeds as a separate solid body (+500 mm3, no
# merge). Adding material to the sheet therefore has to go through the wall or
# flange operations; the solid protrusion path cannot feed the sheetmetal body.
#
# FEAT-014 H05 (2026-11-07, Creo 12.4.0.0) closed the "separate body, then union
# it back" question, so new_body=true is not an attached-material route either:
# a native_planar wall (100x60x1, body 52) plus a new_body 10x10x5 boss (body 116)
# gives two material bodies (6000 / 6500 mm3). Union with the sheetmetal body as
# target (52 <- 116) fails at ProFeatureWithoptionsCreate=-1 with an empty element
# error list and a verified rollback (6500 mm3, 2 bodies, revision unchanged).
# The reverse union (116 <- 52) builds and saves (6400 mm3, one body, reload
# verified), but it absorbs the sheetmetal body: afterwards all 36 edges answer
# ProSmtedgeContourGet=-8 (0 eligible wall contours) and sheetmetal_unbend fails
# with -1 and rolls back. A solid-to-solid union on the same sheetmetal part
# succeeds (6800 mm3), so the boolean feature itself is legal there and the
# failure is specific to the sheetmetal body. Creo 10 has never been tried.
SOLID_ADD_UNSUPPORTED = "SHEETMETAL_SOLID_ADD_UNSUPPORTED"


def solid_add_on_sheetmetal_problem(operations: list[dict[str, Any]]) -> str | None:
    """Return why a plan would add solid material into a sheetmetal body."""
    blocked = [
        operation.get("label")
        for operation in operations
        if operation.get("op") == "extrude"
        and operation.get("mode") == "add"
        and operation.get("thin") is None
        and not operation.get("new_body")
    ]
    if not blocked:
        return None
    labels = ", ".join(str(label) for label in blocked)
    return (
        f"{SOLID_ADD_UNSUPPORTED}: Creo rejects an extrude add that merges solid material "
        "into a sheetmetal body (ProFeatureWithoptionsCreate returns -1, measured on Creo "
        "12.4.0.0 with and without overlap). Add material with sheetmetal_wall or "
        "sheetmetal_flange, or request new_body=true to create a separate solid body "
        "(not fused with the sheetmetal body). On Creo 12.4, union into the sheetmetal body returns -1, and reverse union consumes the sheetmetal body (wall contours -8, unbend fails). Creo 10 is untested for these fusion paths. Cut and surface extrudes are outside "
        "this rule; thin extrude add and revolve add are not blocked here, but their "
        "target body and merge behavior are not verified. "
        f"Blocked operations: {labels}"
    )


# --- P08 depth/thickness frame projection (BUG-032 / FEAT-014 / FEAT-008) ---
#
# Frozen frame semantics (live-anchored, see tools/test_sheetmetal_contract.py):
# depth grows one-sided along the signed sketch normal (direction=positive ->
# +normal, direction=negative -> -normal); thickness is the sheet gauge spread
# centered on the sketch line, in-plane perpendicular to it. wall_contract.echo
# carries the measured frame so a volume-only check can never hide a wrong
# orientation or a swapped depth/thickness pair.

MATERIAL_SIDES = ("opposite_thickness_direction", "along_thickness_direction")
WALL_CONTOUR_STATUSES = ("eligible", "ineligible", "unknown")
# ProSmtedgeContourGet answers these codes (ProSheetmetal.h): PRO_TK_NO_ERROR
# when the edge lies on a green/white wall contour, PRO_TK_BAD_CONTEXT when the
# model is not sheetmetal or the edge is not on a green/white surface, anything
# else is a query failure and stays unknown with its real code preserved.
PRO_TK_NO_ERROR = 0
PRO_TK_BAD_CONTEXT = -8


def _finite_number(value: Any) -> float | None:
    return float(value) if type(value) in (int, float) and math.isfinite(value) else None


def _finite_vector(value: Any, size: int) -> list[float] | None:
    if not isinstance(value, list) or len(value) != size:
        return None
    numbers = [float(item) for item in value if type(item) in (int, float) and math.isfinite(item)]
    return numbers if len(numbers) == size else None


def _unit_vector(value: Any, size: int = 3) -> list[float] | None:
    vector = _finite_vector(value, size)
    if vector is None:
        return None
    norm = math.sqrt(sum(item * item for item in vector))
    return vector if abs(norm - 1) <= 1e-6 else None


def normalize_wall_contract(block: Any) -> dict[str, Any] | None:
    """Validate the frame echo inside a wall_contract record (DEV-053 P08).

    Only the executor's own measurements are kept: a non-unit direction or an
    uninterpretable material side degrades that field to null instead of
    keeping a value of unclear provenance. A missing block stays missing
    (legacy jobs) and is never fabricated from the request.
    """
    if not isinstance(block, dict):
        return None
    entry: dict[str, Any] = {
        "line_length_mm": _finite_number(block.get("line_length_mm")),
        "expected_volume_mm3": _finite_number(block.get("expected_volume_mm3")),
        "measured_volume_mm3": _finite_number(block.get("measured_volume_mm3")),
        "driving_face_id": block.get("driving_face_id")
        if type(block.get("driving_face_id")) is int
        else None,
        "driving_axis": block.get("driving_axis")
        if type(block.get("driving_axis")) is int
        else None,
        "part_thickness_before_mm": _finite_number(block.get("part_thickness_before_mm")),
        "part_thickness_mm": _finite_number(block.get("part_thickness_mm")),
        "part_thickness_synced": block.get("part_thickness_synced")
        if type(block.get("part_thickness_synced")) is bool
        else None,
        "frame": None,
        "wall_face_ids": None,
        "parameter_hint": block.get("parameter_hint")
        if isinstance(block.get("parameter_hint"), str) and block.get("parameter_hint")
        else None,
    }
    frame = block.get("frame")
    if isinstance(frame, dict):
        projected: dict[str, Any] = {
            "sketch_normal": _unit_vector(frame.get("sketch_normal")),
            "sketch_origin": _finite_vector(frame.get("sketch_origin"), 3),
            "depth_direction": _unit_vector(frame.get("depth_direction")),
            "thickness_direction": _unit_vector(frame.get("thickness_direction")),
            "material_side": None,
        }
        side = frame.get("material_side")
        if side in MATERIAL_SIDES:
            projected["material_side"] = side
        entry["frame"] = projected
    face_ids = block.get("wall_face_ids")
    if isinstance(face_ids, list):
        entry["wall_face_ids"] = [item for item in face_ids if type(item) is int]
    return entry


# --- P08 wall-contour (candidate edge) projection (FEAT-014) -----------------
#
# wall_contour_status answers exactly one question: does this edge lie on a
# green/white sheetmetal wall contour, i.e. can it carry a flange attachment at
# all? eligible is NOT a promise that a flange will succeed - the
# adjacent_bend_ends pre-creation rejection and the native geometry checks
# still apply - and the field is deliberately not named "flange_available".
#
# The native inspection keeps its compared `edges` records byte-stable (old
# snapshots must keep reconciling) and reports the bounded query in a separate
# top-level wall_contour_check block keyed by edge id; this projection derives
# the tri-state from the real query codes, joins it onto copies of the edge
# records, and stamps the model revision the check was observed at.


def wall_contour_status_from_code(query_code: Any) -> str | None:
    """Map one real ProSmtedgeContourGet code to the frozen tri-state.

    None means the query never ran for this edge (missing stays missing); any
    non-integer input is malformed and degrades to "unknown" at the projector,
    not here.
    """
    if type(query_code) is not int:
        return None
    if query_code == PRO_TK_NO_ERROR:
        return "eligible"
    if query_code == PRO_TK_BAD_CONTEXT:
        return "ineligible"
    return "unknown"


def project_wall_contour(inspection: Any, revision: Any = None) -> dict[str, Any]:
    """Project the bounded wall-contour check of one inspection snapshot.

    Rules: an edge without a query record gets no status at all; a check record
    whose code is not an integer degrades to status "unknown" while the raw
    value is preserved in wall_contour_query_code; an unknown edge id keeps its
    record but is never joined onto an edge. The summary carries the revision
    the check was observed at (the caller supplies the current model revision -
    the executor does not know it) and null when it is unknown.
    """
    state = inspection if isinstance(inspection, dict) else {}
    check = state.get("wall_contour_check")
    records = check.get("edges") if isinstance(check, dict) else None
    by_edge: dict[Any, dict[str, Any]] = {}
    checked = 0
    counts = {status: 0 for status in WALL_CONTOUR_STATUSES}
    projected_records: list[dict[str, Any]] = []
    if isinstance(records, list):
        for record in records:
            if not isinstance(record, dict):
                continue
            entry = dict(record)
            code = entry.get("wall_contour_query_code")
            if code is None:
                projected_records.append(entry)
                continue
            checked += 1
            status = wall_contour_status_from_code(code)
            if status is None:
                status = "unknown"
            entry["wall_contour_status"] = status
            counts[status] += 1
            projected_records.append(entry)
            if "edge_id" in entry:
                by_edge[entry["edge_id"]] = entry
    edges = []
    for edge in state.get("edges") or []:
        record = dict(edge) if isinstance(edge, dict) else {"raw": edge}
        match = by_edge.get(record.get("id"))
        if match is not None:
            record["wall_contour_query_code"] = match.get("wall_contour_query_code")
            record["wall_contour_status"] = match.get("wall_contour_status")
        edges.append(record)
    summary: dict[str, Any] = {
        "query": "ProSmtedgeContourGet",
        "enabled": check.get("enabled") if isinstance(check, dict) else None,
        "bounded": check.get("bounded") if isinstance(check, dict) else None,
        "budget": check.get("budget") if isinstance(check, dict) else None,
        "revision": revision if type(revision) is int else None,
        "checked_edges": checked,
        "eligible": counts["eligible"],
        "ineligible": counts["ineligible"],
        "unknown": counts["unknown"],
        "meaning": (
            "eligible means the edge lies on a green/white wall contour and can carry a "
            "flange attachment; it does not promise flange creation - adjacent_bend_ends "
            "and native geometry checks still reject at creation time"
        ),
    }
    return {
        "edges": edges,
        "wall_contour_check": summary,
        "wall_contour_records": projected_records,
    }


# --- DEV-089 T3: open polyline base-flange admission ---
#
# The existing first wall is one open straight line (sheetmetal_wall) and the
# attached flange is a candidate that needs a wall to attach to. A bent first
# wall built from an open polyline is a separate native feature, not a
# planar_wall plus flange: the latter only lengthens/shortens an existing wall
# and would not create the first wall's bends.
#
# This batch admits exactly two straight lines meeting at one right angle.
# Longer polylines, arcs, branches and self-overlaps stay refused until a live
# reference tree proves them. The rules are frozen here so admission, the native
# executor and the tests share one definition.

BASE_FLANGE_FIRST_BATCH_MAX_SEGMENTS = 2
BASE_FLANGE_POINT_TOLERANCE_MM = 1e-9


def _base_flange_point(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    point = []
    for item in value:
        if isinstance(item, bool) or type(item) not in (int, float) or not math.isfinite(item):
            return None
        point.append(float(item))
    return point


def _base_flange_distance(first: list[float], second: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(first, second, strict=True)))


def _base_flange_sub(first: list[float], second: list[float]) -> list[float]:
    return [a - b for a, b in zip(first, second, strict=True)]


def _base_flange_cross(first: list[float], second: list[float]) -> list[float]:
    return [
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    ]


def _base_flange_norm(value: list[float]) -> float:
    return math.sqrt(sum(component * component for component in value))


def base_flange_section_problem(
    entities: list[dict[str, Any]], max_segments: int = BASE_FLANGE_FIRST_BATCH_MAX_SEGMENTS
) -> str | None:
    """Return why an open line chain cannot drive a polyline base flange, or None.

    ``None`` means the chain is a candidate for the native feature; it is not a
    promise that the native creation exists or that the geometry is a valid
    sheetmetal treatment.
    """
    drawing = [
        entity
        for entity in entities
        if isinstance(entity, dict)
        and entity.get("type") != "centerline"
        and not entity.get("construction")
    ]
    if not drawing:
        return (
            "sheetmetal_base_flange needs a continuous open chain of straight lines; "
            "the section has no drawing entities"
        )
    if len(drawing) > max_segments:
        return (
            f"sheetmetal_base_flange admits at most {max_segments} straight lines in this "
            f"batch; got {len(drawing)} drawing entities"
        )
    segments: list[tuple[list[float], list[float]]] = []
    for index, entity in enumerate(drawing):
        if entity.get("type") != "line":
            return (
                f"sheetmetal_base_flange entity {index} is {entity.get('type')!r}; only straight "
                "lines are admitted in this batch"
            )
        start = _base_flange_point(entity.get("start"))
        end = _base_flange_point(entity.get("end"))
        if start is None or end is None:
            return (
                f"sheetmetal_base_flange entity {index} needs finite [x,y,z] start and end "
                "points; a two-dimensional or malformed point cannot define the chain"
            )
        if _base_flange_distance(start, end) <= BASE_FLANGE_POINT_TOLERANCE_MM:
            return f"sheetmetal_base_flange entity {index} is zero length"
        segments.append((start, end))
    for index in range(len(segments) - 1):
        gap = _base_flange_distance(segments[index][1], segments[index + 1][0])
        if gap > BASE_FLANGE_POINT_TOLERANCE_MM:
            return (
                f"sheetmetal_base_flange segments {index} and {index + 1} are not connected "
                f"end-to-start (gap {gap:.9g} mm); the chain must be continuous in the given "
                "order and must not branch"
            )
    if len(segments) == 2:
        first, second = segments
        direction = _base_flange_cross(
            _base_flange_sub(first[1], first[0]), _base_flange_sub(second[1], second[0])
        )
        if _base_flange_norm(direction) <= 1e-12:
            # Collinear segments either continue one line or fold back over each
            # other. Neither is a bend, and folding back self-overlaps.
            return (
                "sheetmetal_base_flange segments are collinear; a base flange needs a real "
                "bend and a folded-back chain self-overlaps"
            )
    return None


BASE_FLANGE_BEND_ANGLE_DEG = 90.0
BASE_FLANGE_PERPENDICULAR_TOLERANCE = 1e-6


def base_flange_geometry_problem(entities: list[dict[str, Any]]) -> str | None:
    """Return why an admitted chain cannot be composed into a base flange."""
    problem = base_flange_section_problem(entities)
    if problem is not None:
        return problem
    try:
        base_flange_geometry(entities)
    except ValueError as error:
        return str(error)
    return None


def base_flange_geometry(entities: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive the two legs of the composed base flange from an admitted chain.

    DEV-089 T3 builds the open polyline as two native features: a rectangular
    planar wall for the first leg and a 90 degree flange on that wall's free end
    edge. Only the chain's leg lengths and its 90 degree corner reach the
    features, so a non-perpendicular or discontinuous chain is refused instead
    of being silently reinterpreted.

    The first leg is the wall's rectangle length; the second leg is the length
    of the flange leg measured from the plate's outer face, which is why the
    native flange height is ``second_leg + thickness`` (a flange of height h
    carries h - thickness of free leg for this gauge; measured live on
    Creo 12.4.0.0).
    """
    problem = base_flange_section_problem(entities)
    if problem is not None:
        raise ValueError(problem)
    drawing = [
        entity
        for entity in entities
        if isinstance(entity, dict)
        and entity.get("type") != "centerline"
        and not entity.get("construction")
    ]
    segments: list[tuple[list[float], list[float]]] = []
    for index, entity in enumerate(drawing):
        start = _base_flange_point(entity.get("start"))
        end = _base_flange_point(entity.get("end"))
        if start is None or end is None:
            raise ValueError(
                f"sheetmetal_base_flange entity {index} needs finite [x,y,z] start and end points"
            )
        segments.append((start, end))
    if len(segments) != BASE_FLANGE_FIRST_BATCH_MAX_SEGMENTS:
        raise ValueError(
            "sheetmetal_base_flange composes exactly two straight lines in this batch; "
            f"got {len(segments)}"
        )
    first, second = segments
    shared = first[1]
    if _base_flange_distance(shared, second[0]) > BASE_FLANGE_POINT_TOLERANCE_MM:
        raise ValueError(
            "sheetmetal_base_flange segments 0 and 1 are not connected end-to-start; "
            "the chain must be continuous in the given order and must not branch"
        )
    first_direction = _base_flange_sub(first[0], shared)
    second_direction = _base_flange_sub(second[1], shared)
    scale = _base_flange_norm(first_direction) * _base_flange_norm(second_direction)
    dot = sum(a * b for a, b in zip(first_direction, second_direction, strict=True))
    if scale <= 0 or abs(dot) > BASE_FLANGE_PERPENDICULAR_TOLERANCE * scale:
        raise ValueError(
            "sheetmetal_base_flange composes a 90 degree bend only: the two legs must be "
            "perpendicular (a collinear chain has no bend, another angle has no composed "
            "counterpart in this batch)"
        )
    return {
        "first_leg_mm": _base_flange_distance(*first),
        "second_leg_mm": _base_flange_distance(*second),
        "bend_angle_deg": BASE_FLANGE_BEND_ANGLE_DEG,
        "corner_mm": shared,
    }


def base_flange_expected_volume(
    first_leg_mm: float,
    second_leg_mm: float,
    width_mm: float,
    thickness_mm: float,
    radius_mm: float,
) -> dict[str, float]:
    """Analytic volume of the composed part, as one acceptance bound.

    The wall contributes ``first_leg x width x thickness``. The flange adds
    ``second_leg x width x thickness`` and removes the corner it replaces: the
    measured bend is the quarter annulus between the inside radius and
    ``radius + thickness``. On Creo 12.4.0.0 the two live probes matched this
    bound to 0.002 mm3 (8/12 legs, t=2, width=20, R=0.7366).
    """
    straight = (first_leg_mm + second_leg_mm) * width_mm * thickness_mm
    removed = (1 - math.pi / 4) * ((radius_mm + thickness_mm) ** 2 - radius_mm**2) * width_mm
    return {
        "straight_mm3": straight,
        "bend_removed_mm3": removed,
        "total_mm3": straight - removed,
    }


BASE_FLANGE_OP = "sheetmetal_base_flange"
BASE_FLANGE_LABEL_LIMIT = 22
BASE_FLANGE_SKETCH_SUFFIX = "_sk"
BASE_FLANGE_LEG2_SUFFIX = "_leg2"


def base_flange_names(operation: dict[str, Any]) -> tuple[str, ...]:
    """Every managed feature name the composed base flange creates.

    It creates three: the label is the planar wall, ``<label>_sk`` is that
    wall's driving sketch and ``<label>_leg2`` is the flange. All three are real
    Creo feature names, so all three take part in duplicate, plan-collision and
    tombstone protection.
    """
    if operation.get("op") != BASE_FLANGE_OP:
        return ()
    label = operation.get("label")
    if not isinstance(label, str) or not label:
        return ()
    return (
        label,
        f"{label}{BASE_FLANGE_SKETCH_SUFFIX}",
        f"{label}{BASE_FLANGE_LEG2_SUFFIX}",
    )


def declared_base_flange_names(operations: list[dict[str, Any]]) -> list[str]:
    """Internal names only: the label already arrives from declared_names().

    The plan-level duplicate check gets every operation's label from
    ``native_planar_wall.declared_names``, so only ``<label>_sk`` and
    ``<label>_leg2`` are added here.
    """
    return [name for operation in operations for name in base_flange_names(operation)[1:]]


def base_flange_create_problem(
    model: dict[str, Any] | None,
    aliases: dict[str, Any] | None = None,
    operation: dict[str, Any] | None = None,
) -> str | None:
    """Why the composed base flange cannot start here, or None when it may.

    The composed part is still a *first* wall: the planar wall inside it only
    regenerates in an empty sheetmetal part, so a model that already carries
    geometry is refused before a job exists.
    """
    if model is not None:
        if model.get("model_type") != "sheetmetal":
            return (
                "sheetmetal_base_flange requires an MCP sheetmetal model: the composed "
                "planar wall only regenerates in a sheetmetal part"
            )
        summary = model.get("inspection_summary") or {}
        if summary.get("has_solid"):
            return (
                "sheetmetal_base_flange creates the first wall; this model already has "
                "geometry. Create a new sheetmetal model with the native planar template"
            )
    if operation is not None and aliases is not None:
        taken = [name for name in base_flange_names(operation) if name in aliases]
        if taken:
            return (
                f"sheetmetal_base_flange would create {sorted(taken)}, but that feature name "
                "already exists in this model; managed labels are never overwritten"
            )
    return None


def validate_base_flange_plan(
    model: dict[str, Any] | None,
    operations: list[dict[str, Any]],
    aliases: dict[str, Any] | None = None,
) -> None:
    """Raise ValueError before a job exists when a composed base flange is inadmissible."""
    for operation in operations:
        if operation.get("op") != BASE_FLANGE_OP:
            continue
        problem = base_flange_create_problem(model, aliases, operation)
        if problem:
            raise ValueError(problem)


def y_factor_from_k(k_factor: float) -> float:
    """Convert a K factor to the Creo Y factor (Y = K * pi / 2).

    Creo's attached wall stores a Y factor, while many external plans are
    written with a K factor. K=0.5 becomes Y≈0.7853981634; passing K=0.5
    straight through as a Y factor would silently change the flat length.
    """
    if isinstance(k_factor, bool) or type(k_factor) not in (int, float):
        raise ValueError("K factor must be a finite number")
    if not math.isfinite(k_factor) or not 0 < k_factor <= 1:
        raise ValueError("K factor must be greater than 0 and at most 1")
    return float(k_factor) * math.pi / 2
