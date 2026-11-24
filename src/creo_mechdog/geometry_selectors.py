"""DEV-089 T1: geometric anchor selectors for edges and faces.

A plan normally names a geometry item by the ID read from ``creo_inspect_model``.
Those IDs change whenever the model rebuilds, so a plan that must keep targeting
one physical edge or face can describe it geometrically instead:

    {"kind": "geometry_selector", "target": "edge",
     "endpoints_mm": [[0, 0, 0], [0, 0, 40]], "tolerance_mm": 1e-3}

    {"kind": "geometry_selector", "target": "surface",
     "axis": [0, 0, 1], "radius_mm": 5, "points_mm": [[10, 0, 1]],
     "tolerance_mm": 1e-3}

The frozen batch-1 vocabulary is deliberately narrow:

* ``target`` is ``edge`` or ``surface``.
* An edge selector has three admitted forms (DEV-083/FEAT-068 A0):
  ``endpoints_mm`` (two endpoints, matched in either direction, with an optional
  ``point_mm`` filter), ``point_mm`` alone (one point that must lie on exactly
  one finite straight edge), or ``center_mm`` + ``radius_mm`` (+ optional
  ``axis``) for a circular edge. A single point is never treated as a circle's
  centre and a centre is never treated as a point on the edge.
* A surface selector needs at least one of ``points_mm``, ``center_mm``,
  ``radius_mm`` or ``axis``. ``points_mm`` must lie on the surface, ``axis`` is
  the surface normal (plane) or axis (cylinder) compared sign-insensitively with
  ``axis_tolerance_deg``, and ``radius_mm`` is the cylinder radius.
  ``center_mm`` is compared as the perpendicular distance to the axis line, not
  as an absolute cylinder parameter origin: the SDK origin along an axis is not
  unique, so comparing it would reject copies of the same physical cylinder.
* ``coaxial: "any"`` is an explicit opt-in for a ``concentric``/``insert``
  reference: a full cylinder is often reported as two coaxial half faces, and
  insert only needs their common axis. It requires ``radius_mm`` and ``axis``,
  accepts several matching cylinder pieces, and picks the lowest id
  deterministically. It is refused on round/chamfer/flange anchors and on
  ``mate``/``coincident`` references; the default still requires exactly one
  face.
* A planar surface is compared as the unbounded plane (normal plus distance), not
  the trimmed face boundary, so a point elsewhere on the same plane still
  matches. Separate two coplanar faces with another filter or an explicit id.
* ``tolerance_mm`` is required, positive, finite and at most
  ``MAX_TOLERANCE_MM``. Angular error is kept separate in degrees.
* Coordinate space is metric millimetres. ``coordinate_space="model"`` (the
  default) means the frame of the part that owns the geometry.
  ``coordinate_space="assembly"`` means the root-assembly frame and is admitted
  only on the assembly side of a ``component_constraints`` reference that names
  the placed ``assembly_component``. The executor maps those coordinates into
  that component's own frame with the inverse occurrence placement; the moving
  component has no solved pose yet, so assembly-space selectors on
  ``component_reference`` are refused rather than resolved against a guessed
  position.

Zero or multiple matches are always refused. The native executor enumerates the
current model, reports the candidate count and matched IDs, and never falls back
to "the first candidate". Nothing here decides which candidate is "the" one:
this module only validates the request shape before dispatch.
"""

from __future__ import annotations

import math
import re
from typing import Any

GEOMETRY_SELECTOR_KIND = "geometry_selector"
SELECTOR_TARGETS = ("edge", "surface")
COORDINATE_SPACES = ("model", "assembly")
MAX_TOLERANCE_MM = 1000.0
MAX_AXIS_TOLERANCE_DEG = 90.0
DEFAULT_AXIS_TOLERANCE_DEG = 0.5
MAX_POINTS = 8

_ALLOWED_KEYS = frozenset(
    {
        "kind",
        "target",
        "endpoints_mm",
        "point_mm",
        "points_mm",
        "center_mm",
        "radius_mm",
        "axis",
        "tolerance_mm",
        "axis_tolerance_deg",
        "coordinate_space",
        "coaxial",
        "full_circle",
        "feature",
    }
)

DESCRIPTION = (
    "A geometric anchor selector is {kind:'geometry_selector',target:'edge'|'surface',"
    "tolerance_mm:>0,...}. Edges take endpoints_mm (two endpoints, either direction) with an "
    "optional point_mm filter, point_mm alone for one finite straight or circular arc edge "
    "(resolving a shared seam endpoint between two arcs of the same circle to the smallest id), "
    "or center_mm+radius_mm (+axis, +point_mm on the arc span, or full_circle:true to pick one "
    "deterministic arc of a split full circle for round/chamfer propagation) for a circular edge; "
    "surfaces take points_mm on the "
    "surface and/or center_mm/radius_mm/axis with axis_tolerance_deg for the direction. "
    "It must match exactly one current model item (or one split circle when full_circle:true or "
    "point_mm hits the seam between complementary arcs of one circle); zero or multiple matches "
    "are refused. "
    "coordinate_space is 'model' (default) or 'assembly'; an assembly-space selector is only "
    "valid on the assembly side of a component constraint that names the placed "
    "assembly_component and is mapped into that component's frame by the executor. "
    "A surface selector may set coaxial:'any' only on an insert/concentric reference; it requires "
    "radius_mm+axis and accepts several coaxial cylinder pieces instead of exactly one face."
)


def is_geometry_selector(value: Any) -> bool:
    return isinstance(value, dict) and value.get("kind") == GEOMETRY_SELECTOR_KIND


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or type(value) not in (int, float):
        raise ValueError(f"{path} must be a finite number, not a boolean or string")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{path} must be finite")
    return number


def _point(value: Any, path: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{path} must be [x, y, z]")
    return [_number(item, f"{path}[{index}]") for index, item in enumerate(value)]


def _points(value: Any, path: str, minimum: int, maximum: int) -> list[list[float]]:
    if not isinstance(value, (list, tuple)) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{path} must contain {minimum}..{maximum} [x, y, z] points")
    return [_point(item, f"{path}[{index}]") for index, item in enumerate(value)]


def _unit_vector(value: Any, path: str) -> list[float]:
    vector = _point(value, path)
    length = math.sqrt(sum(component * component for component in vector))
    if abs(length - 1.0) > 1e-6:
        raise ValueError(
            f"{path} must be a unit vector (length 1 within 1e-6); got length {length!r}"
        )
    return vector


def validate_geometry_selector(value: Any, path: str = "selector") -> dict[str, Any]:
    """Validate one geometric selector and return a normalized copy.

    Unknown keys are refused rather than ignored, so a misspelled filter can
    never widen the match silently.
    """
    if not isinstance(value, dict):
        raise ValueError(f"{path}: " + DESCRIPTION)
    if value.get("kind") != GEOMETRY_SELECTOR_KIND:
        raise ValueError(f"{path}: " + DESCRIPTION)
    unknown = sorted(set(value) - _ALLOWED_KEYS)
    if unknown:
        raise ValueError(f"{path}: unknown geometry_selector field(s) {unknown}; " + DESCRIPTION)
    target = value.get("target")
    if target not in SELECTOR_TARGETS:
        raise ValueError(f"{path}.target must be 'edge' or 'surface'; " + DESCRIPTION)
    if "coaxial" in value and target != "surface":
        raise ValueError(
            f"{path}.coaxial is only valid on a surface selector: it relaxes a coaxial "
            "cylinder choice, not an edge choice"
        )
    if "full_circle" in value and target != "edge":
        raise ValueError(
            f"{path}.full_circle is only valid on a circular edge selector (center_mm+radius_mm)"
        )

    if "tolerance_mm" not in value:
        raise ValueError(
            f"{path}.tolerance_mm is required: every geometric selector records its own "
            "length tolerance in millimetres; " + DESCRIPTION
        )
    tolerance = _number(value["tolerance_mm"], f"{path}.tolerance_mm")
    if tolerance <= 0 or tolerance > MAX_TOLERANCE_MM:
        raise ValueError(
            f"{path}.tolerance_mm must be greater than 0 and at most {MAX_TOLERANCE_MM} mm"
        )

    coordinate_space = value.get("coordinate_space", "model")
    if coordinate_space not in COORDINATE_SPACES:
        raise ValueError(
            f"{path}.coordinate_space must be 'model' or 'assembly'; got {coordinate_space!r}"
        )

    axis_tolerance = value.get("axis_tolerance_deg", DEFAULT_AXIS_TOLERANCE_DEG)
    axis_tolerance = _number(axis_tolerance, f"{path}.axis_tolerance_deg")
    if not 0 < axis_tolerance <= MAX_AXIS_TOLERANCE_DEG:
        raise ValueError(
            f"{path}.axis_tolerance_deg must be greater than 0 and at most "
            f"{MAX_AXIS_TOLERANCE_DEG} degrees"
        )

    normalized: dict[str, Any] = {
        "kind": GEOMETRY_SELECTOR_KIND,
        "target": target,
        "coordinate_space": coordinate_space,
        "tolerance_mm": tolerance,
        "axis_tolerance_deg": axis_tolerance,
    }
    if "feature" in value:
        feature = value["feature"]
        if (
            target not in ("surface", "edge")
            or coordinate_space != "model"
            or not isinstance(feature, str)
            or re.fullmatch(r"[a-z][a-z0-9_]{0,27}", feature) is None
        ):
            raise ValueError(
                f"{path}.feature must be a feature label on a model-space edge or surface selector"
            )
        normalized["feature"] = feature

    if target == "edge":
        if "points_mm" in value:
            raise ValueError(
                f"{path}.points_mm is a surface filter; an edge selector uses endpoints_mm, "
                "point_mm, or center_mm/radius_mm for a circular edge"
            )
        circular_fields = ("center_mm", "radius_mm")
        if any(field in value for field in circular_fields):
            if "endpoints_mm" in value:
                raise ValueError(
                    f"{path}: a circular edge selector (center_mm/radius_mm) cannot also carry "
                    "endpoints_mm; choose one form"
                )
            if "center_mm" not in value or "radius_mm" not in value:
                raise ValueError(
                    f"{path}: a circular edge selector needs both center_mm and radius_mm; a "
                    "single one would match every circle or every edge through a point"
                )
            center = _point(value["center_mm"], f"{path}.center_mm")
            radius = _number(value["radius_mm"], f"{path}.radius_mm")
            if radius <= 0 or radius > MAX_TOLERANCE_MM:
                raise ValueError(
                    f"{path}.radius_mm must be greater than 0 and at most {MAX_TOLERANCE_MM} mm"
                )
            normalized["center_mm"] = center
            normalized["radius_mm"] = radius
            if "axis" in value:
                normalized["axis"] = _unit_vector(value["axis"], f"{path}.axis")
            # A point on the circle narrows a split rim to the piece whose arc
            # actually spans that angle; a centre point is never inferred.
            if "point_mm" in value:
                normalized["point_mm"] = _point(value["point_mm"], f"{path}.point_mm")
            if "full_circle" in value:
                if type(value["full_circle"]) is not bool:
                    raise ValueError(f"{path}.full_circle must be a boolean (true or false)")
                normalized["full_circle"] = value["full_circle"]
            return normalized
        if "full_circle" in value:
            raise ValueError(
                f"{path}.full_circle only accompanies a circular edge selector with "
                "center_mm and radius_mm"
            )
        if "axis" in value:
            raise ValueError(
                f"{path}.axis only accompanies a circular edge selector with center_mm/radius_mm"
            )
        if "endpoints_mm" in value:
            endpoints = _points(value["endpoints_mm"], f"{path}.endpoints_mm", 2, 2)
            if endpoints[0] == endpoints[1]:
                raise ValueError(f"{path}.endpoints_mm must name two distinct points")
            normalized["endpoints_mm"] = endpoints
            if "point_mm" in value:
                normalized["point_mm"] = _point(value["point_mm"], f"{path}.point_mm")
            return normalized
        if "point_mm" not in value:
            raise ValueError(
                f"{path}: an edge selector needs endpoints_mm (two finite endpoints), point_mm "
                "(one point on the edge), or center_mm/radius_mm for a circular edge"
            )
        normalized["point_mm"] = _point(value["point_mm"], f"{path}.point_mm")
        return normalized

    if "endpoints_mm" in value or "point_mm" in value:
        raise ValueError(
            f"{path}.endpoints_mm/point_mm belong to an edge selector; a surface selector "
            "uses points_mm, center_mm, radius_mm and axis"
        )
    if not any(field in value for field in ("points_mm", "center_mm", "radius_mm", "axis")):
        raise ValueError(
            f"{path}: a surface selector needs at least one of points_mm, center_mm, "
            "radius_mm or axis; a target and tolerance alone would match any face"
        )
    if "points_mm" in value:
        points = _points(value["points_mm"], f"{path}.points_mm", 1, MAX_POINTS)
        normalized["points_mm"] = points
    if "axis" in value:
        normalized["axis"] = _unit_vector(value["axis"], f"{path}.axis")
    if "center_mm" in value:
        if "axis" not in normalized:
            raise ValueError(
                f"{path}.center_mm is measured as the perpendicular distance to the axis "
                "line; it requires axis"
            )
        normalized["center_mm"] = _point(value["center_mm"], f"{path}.center_mm")
    if "radius_mm" in value:
        if "axis" not in normalized:
            raise ValueError(f"{path}.radius_mm identifies a cylinder and requires axis")
        radius = _number(value["radius_mm"], f"{path}.radius_mm")
        if radius <= 0 or radius > MAX_TOLERANCE_MM:
            raise ValueError(
                f"{path}.radius_mm must be greater than 0 and at most {MAX_TOLERANCE_MM} mm"
            )
        normalized["radius_mm"] = radius
    if "coaxial" in value:
        if value["coaxial"] != "any":
            raise ValueError(
                f"{path}.coaxial must be 'any' (the only admitted relaxation); got "
                f"{value['coaxial']!r}"
            )
        if "radius_mm" not in normalized or "axis" not in normalized:
            raise ValueError(
                f"{path}.coaxial='any' requires radius_mm and axis: only coaxial cylinder "
                "pieces are interchangeable for insert/concentric"
            )
        normalized["coaxial"] = "any"
    return normalized


def _reject_coaxial_anchor(selector: Any, where: str) -> None:
    """coaxial='any' is an assembly-constraint relaxation, never a feature anchor."""
    if isinstance(selector, dict) and selector.get("coaxial") is not None:
        raise ValueError(
            f"{where}: coaxial is only valid on a component_constraints insert/concentric "
            "reference; round/chamfer/flange anchors must name one face"
        )


def validate_reference_list(references: list[dict[str, Any]], path: str) -> None:
    """Validate the shape of a round/chamfer reference list before dispatch.

    A reference is a wrapper, never a bare selector: the native executor reads
    ``refs.at("edge")`` or ``refs["surfaces"][0..1]``, so a top-level selector, a
    mixed wrapper or a two-face set of the wrong length used to pass admission
    and then fail (or silently drop entries) inside the feature tree. Only the
    structure is checked here; the selector filters are validated as before.
    """
    for index, reference in enumerate(references):
        where = f"{path}[{index}]"
        if not isinstance(reference, dict):
            continue
        if is_geometry_selector(reference):
            raise ValueError(
                f"{where} is a bare geometry selector; a {_op_of(path)} reference is a wrapper: "
                'use {"edge": <edge selector>} for one edge, or '
                '{"surfaces": [<surface selector>, <surface selector>]} for a two-face set. '
                "The wrapper is what tells the executor which element to fill."
            )
        has_edge, has_surfaces = "edge" in reference, "surfaces" in reference
        if has_edge and has_surfaces:
            raise ValueError(
                f"{where} carries both 'edge' and 'surfaces'; one reference names either one "
                'edge ({"edge": <edge selector>}) or exactly two faces '
                '({"surfaces": [<first>, <second>]}), never both'
            )
        if not has_edge and not has_surfaces:
            raise ValueError(
                f"{where} names no reference: expected "
                '{"edge": <edge selector>} or {"surfaces": [<first>, <second>]}; '
                f"got the keys {sorted(reference)}"
            )
        if has_surfaces:
            _validate_surface_set(reference["surfaces"], f"{where}.surfaces")
            continue
        _validate_edge_reference(reference["edge"], f"{where}.edge")


def _op_of(path: str) -> str:
    return path.split(".", 1)[0] or "feature"


def _validate_edge_reference(edge: Any, where: str) -> None:
    if is_geometry_selector(edge):
        _reject_coaxial_anchor(edge, where)
        normalized = validate_geometry_selector(edge, where)
        if normalized["target"] != "edge":
            raise ValueError(
                f"{where}.target is {normalized['target']!r}; the 'edge' slot of a round/chamfer "
                "reference accepts an edge selector only (use the 'surfaces' slot for faces)"
            )
        return
    if edge is None or (isinstance(edge, dict) and not edge):
        raise ValueError(
            f"{where} is empty; name the edge either with an edge selector "
            "({kind:'geometry_selector',target:'edge',...}) or with an explicit edge reference"
        )


def _validate_surface_set(surfaces: Any, where: str) -> None:
    if not isinstance(surfaces, (list, tuple)):
        raise ValueError(
            f"{where} must be a list of exactly two faces; a round/chamfer set takes "
            "PRO_E_RNDCH_REFERENCE_SURFACE1 and SURFACE2, so one or three entries are refused"
        )
    if len(surfaces) != 2:
        raise ValueError(
            f"{where} must contain exactly 2 faces (got {len(surfaces)}); the two-face set is "
            "the only surface form the executor can fill, and extra entries would be dropped"
        )
    for slot, surface in enumerate(surfaces):
        if not is_geometry_selector(surface):
            continue
        _reject_coaxial_anchor(surface, f"{where}[{slot}]")
        normalized = validate_geometry_selector(surface, f"{where}[{slot}]")
        if normalized["target"] != "surface":
            raise ValueError(
                f"{where}[{slot}].target is {normalized['target']!r}; the 'surfaces' slot accepts "
                "surface selectors only (use the 'edge' slot for an edge)"
            )
