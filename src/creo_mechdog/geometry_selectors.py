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
    }
)

DESCRIPTION = (
    "A geometric anchor selector is {kind:'geometry_selector',target:'edge'|'surface',"
    "tolerance_mm:>0,...}. Edges take endpoints_mm (two endpoints, either direction) with an "
    "optional point_mm filter, point_mm alone for one finite straight edge, or "
    "center_mm+radius_mm (+axis, +point_mm on the arc span) for a circular edge; surfaces take "
    "points_mm on the "
    "surface and/or center_mm/radius_mm/axis with axis_tolerance_deg for the direction. "
    "It must match exactly one current model item; zero or multiple matches are refused. "
    "coordinate_space is 'model' (default) or 'assembly'; an assembly-space selector is only "
    "valid on the assembly side of a component constraint that names the placed "
    "assembly_component and is mapped into that component's frame by the executor."
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
            return normalized
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
    return normalized


def validate_reference_list(references: list[dict[str, Any]], path: str) -> None:
    """Validate the geometry selectors inside a reference list before dispatch.

    Round/chamfer references are ``{"edge": selector}`` or
    ``{"surfaces": [selector, selector]}`` wrappers, so the selector is not
    always the top-level dictionary.
    """
    for index, reference in enumerate(references):
        where = f"{path}[{index}]"
        if not isinstance(reference, dict):
            continue
        if is_geometry_selector(reference):
            validate_geometry_selector(reference, where)
            continue
        edge = reference.get("edge")
        if is_geometry_selector(edge):
            validate_geometry_selector(edge, f"{where}.edge")
        surfaces = reference.get("surfaces")
        if isinstance(surfaces, list):
            for slot, surface in enumerate(surfaces):
                if is_geometry_selector(surface):
                    validate_geometry_selector(surface, f"{where}.surfaces[{slot}]")
