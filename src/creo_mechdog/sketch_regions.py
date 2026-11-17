"""P1/FEAT-069: turn one signed region of an existing sketch into a derived sketch.

The TXT names a cut region by the endpoint pairs of every boundary segment. A
multi-loop sketch cannot be cut one region at a time by the current extrude
path, which consumes the whole sketch. This module resolves the signature to
exactly one closed loop of the source sketch's own entities and copies those
entities, unchanged, into a derived sketch that the extrude then references.

Nothing here re-draws or approximates geometry: the derived sketch carries the
same plane, the same entities and the same coordinates as the source. A sketch
that still needs dimensions, constraints or a weld plan to resolve is refused,
because dropping those would silently change what the copy means.
"""

from __future__ import annotations

import copy
import hashlib
import math
import re
from typing import Any

from creo_mechdog.region_selection import (
    DEFAULT_TOLERANCE_MM,
    MAX_TOLERANCE_MM,
    parse_region_signature,
    segments_match,
)

#: Endpoint clustering for loop building, in sketch-local millimetres. The TXT
#: values are printed at six decimals, so this only absorbs representation noise;
#: it never moves or rewrites an entity.
ENDPOINT_EPS_MM = 1e-6
#: Bounds that keep a pathological sketch from turning admission into a hang.
MAX_CYCLE_EDGES = 64
MAX_CYCLES = 5000
#: Total DFS pops across every start edge. Admission must stay bounded even for
#: a dense sketch whose cycles are far fewer than its walks.
MAX_WALK_STEPS = 200000
#: Keys copied from the source sketch so the derived sketch keeps its native
#: solve/closure behaviour. Dimensions, constraints and weld_pairs are handled
#: separately (and refused, see ``derive_sketch``).
COPY_KEYS = (
    "offset",
    "endpoint_policy",
    "snap_endpoints",
    "max_endpoint_move_mm",
    "closure_tolerance_mm",
    "geometry_tolerance_mm",
    "dimensioning",
)

NAME_KEYS = {"line", "centerline", "arc", "polyline", "spline", "b_spline"}


def _vector3(value: Any, path: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{path} must be [x, y, z]")
    result = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{path}[{index}] must be a finite number")
        number = float(item)
        if not math.isfinite(number):
            raise ValueError(f"{path}[{index}] must be finite")
        result.append(number)
    return (result[0], result[1], result[2])


def _unit(value: Any, path: str) -> tuple[float, float, float]:
    vector = _vector3(value, path)
    length = math.sqrt(sum(item * item for item in vector))
    if abs(length - 1.0) > 1e-6:
        raise ValueError(f"{path} must be a unit vector, got length {length!r}")
    return vector


def validate_frame(frame: Any, path: str = "region.frame") -> tuple[Any, Any, Any]:
    """Require ``origin + u*xdir + v*ydir`` to land in the global YZ plane.

    The signature is a ``(y, z)`` boundary, so a frame whose axes leave the YZ
    plane cannot describe it: a local point would move in x and the projection
    would lose information. No particular origin x is demanded; the caller's
    own frame (for example the TXT DTM-right frame) is used as given.
    """
    if not isinstance(frame, dict):
        raise ValueError(f"{path} must be an object with origin/xdir/ydir")
    origin = _vector3(frame.get("origin"), f"{path}.origin")
    xdir = _unit(frame.get("xdir"), f"{path}.xdir")
    ydir = _unit(frame.get("ydir"), f"{path}.ydir")
    if abs(sum(a * b for a, b in zip(xdir, ydir))) > 1e-6:
        raise ValueError(f"{path}.xdir and ydir must be orthogonal")
    if abs(xdir[0]) > 1e-6 or abs(ydir[0]) > 1e-6:
        raise ValueError(
            f"{path}: xdir and ydir must lie in the YZ plane (x component 0) for a "
            "signature_yz_mm boundary"
        )
    return origin, xdir, ydir


def _named_plane_frame(plane: Any, offset: Any) -> tuple[Any, Any, Any]:
    if plane != "YZ":
        raise ValueError(
            "region requires a YZ sketch frame; pass region.frame explicitly for a "
            f"sketch on plane {plane!r}"
        )
    shift = 0.0 if offset is None else offset
    if isinstance(shift, bool) or not isinstance(shift, (int, float)) or not math.isfinite(shift):
        raise ValueError("sketch offset must be a finite number")
    return (float(shift), 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)


def resolve_frame(selector: dict[str, Any], sketch: dict[str, Any]) -> tuple[Any, Any, Any]:
    """Explicit selector frame wins; otherwise a named YZ sketch supplies one."""
    frame = selector.get("frame")
    if frame is not None:
        return validate_frame(frame)
    return _named_plane_frame(sketch.get("plane", "XY"), sketch.get("offset"))


def _arc_endpoints(entity: dict[str, Any]) -> tuple[list[float], list[float]]:
    radius = float(entity["radius"])
    center = entity["center"]
    start = math.radians(float(entity["start_angle"]))
    end = math.radians(float(entity["end_angle"]))
    return (
        [center[0] + radius * math.cos(start), center[1] + radius * math.sin(start)],
        [center[0] + radius * math.cos(end), center[1] + radius * math.sin(end)],
    )


def entity_endpoints(entity: dict[str, Any]) -> tuple[list[float], list[float]] | None:
    """The entity's two boundary endpoints in sketch-local coordinates.

    Circles, rectangles and ellipses are closed shapes with no boundary
    endpoints, and construction geometry is not part of a profile, so both
    return None. An open polyline/spline uses its first and last point; a
    clamped b_spline interpolates its first and last control point.
    """
    if entity.get("construction"):
        return None
    kind = entity.get("type")
    if kind in ("line", "centerline"):
        return entity["start"], entity["end"]
    if kind == "arc":
        return _arc_endpoints(entity)
    if kind in ("polyline", "spline"):
        if entity.get("closed"):
            return None
        points = entity["points"]
        return points[0], points[-1]
    if kind == "b_spline":
        points = entity["control_points"]
        return points[0], points[-1]
    return None


def _cluster_vertices(points: list[list[float]], eps: float) -> list[int]:
    parent = list(range(len(points)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        left, right = find(first), find(second)
        if left != right:
            parent[right] = left

    for right in range(len(points)):
        for left in range(right):
            if math.dist(points[left], points[right]) <= eps:
                union(left, right)
    return [find(index) for index in range(len(points))]


def _enumerate_cycles(edges: list[tuple[int, int]], limit: int) -> list[frozenset[int]]:
    """Every simple cycle of the entity-endpoint graph, bounded by ``limit``.

    A region boundary in a multi-loop sketch is one cycle; shared edges mean
    vertices can have degree above two, so the walk never reuses an edge and
    accepts only cycles whose smallest edge index starts the walk (one record
    per cycle).
    """
    adjacency: dict[int, list[tuple[int, int]]] = {}
    for index, (start, end) in enumerate(edges):
        adjacency.setdefault(start, []).append((index, end))
        adjacency.setdefault(end, []).append((index, start))
    cycles: set[frozenset[int]] = set()
    steps = 0
    for first, (start, end) in enumerate(edges):
        stack = [(end, frozenset((first,)), 1)]
        while stack:
            steps += 1
            if steps > MAX_WALK_STEPS:
                return list(cycles)
            vertex, used, depth = stack.pop()
            for index, other in adjacency.get(vertex, ()):
                if index in used:
                    continue
                if other == start:
                    cycle = used | {index}
                    if len(cycle) >= 2 and min(cycle) == first:
                        cycles.add(cycle)
                        if len(cycles) >= limit:
                            return list(cycles)
                    continue
                if depth >= MAX_CYCLE_EDGES - 1:
                    continue
                stack.append((other, used | {index}, depth + 1))
    return list(cycles)


def _to_yz(point: list[float], frame: tuple[Any, Any, Any]) -> tuple[float, float]:
    origin, xdir, ydir = frame
    world = [origin[axis] + point[0] * xdir[axis] + point[1] * ydir[axis] for axis in range(3)]
    return (world[1], world[2])


def _segment(first: list[float], second: list[float], frame: tuple[Any, Any, Any]):
    """One boundary segment in global YZ, endpoint order made irrelevant."""
    left, right = _to_yz(first, frame), _to_yz(second, frame)
    return (left, right) if left <= right else (right, left)


def _loop_segments(
    entity: dict[str, Any], frame: tuple[Any, Any, Any]
) -> tuple[tuple[float, float], tuple[float, float]]:
    endpoints = entity_endpoints(entity)
    if endpoints is None:  # pragma: no cover - the loop builder filtered it already
        raise ValueError("entity has no boundary endpoints")
    return _segment(endpoints[0], endpoints[1], frame)


def _usable_sketch(sketch: dict[str, Any], label: str) -> None:
    if sketch.get("op") != "sketch":
        raise ValueError(f"region source {label!r} is not a sketch operation")
    if not isinstance(sketch.get("entities"), list) or not sketch["entities"]:
        raise ValueError(f"region source {label!r} has no entities")
    for key in ("dimensions", "constraints", "weld_pairs"):
        if sketch.get(key):
            raise ValueError(
                f"region source {label!r} carries {key}; a derived sketch cannot keep "
                "them without rewriting their entity references, so expand the region "
                "from a coordinate-defined sketch instead"
            )


def find_region(
    sketch: dict[str, Any],
    signature: str,
    frame: tuple[Any, Any, Any],
    tolerance: float,
) -> tuple[frozenset[int], list[dict[str, Any]]]:
    """Return the one entity cycle whose YZ boundary equals ``signature``."""
    expected = parse_region_signature(signature)
    entities = sketch["entities"]
    points: list[list[float]] = []
    edge_owner: list[int] = []
    raw_edges: list[tuple[int, int]] = []
    for index, entity in enumerate(entities):
        if entity.get("type") not in NAME_KEYS:
            continue
        endpoints = entity_endpoints(entity)
        if endpoints is None:
            continue
        start_id, end_id = len(points), len(points) + 1
        points.extend([list(endpoints[0]), list(endpoints[1])])
        edge_owner.append(index)
        raw_edges.append((start_id, end_id))
    if not raw_edges:
        raise ValueError(
            f"region source {sketch.get('label')!r} has no open boundary entities "
            "(lines, arcs, open splines or b_splines); circles/rectangles/ellipses "
            "cannot be named by a boundary signature"
        )
    clusters = _cluster_vertices(points, ENDPOINT_EPS_MM)
    edges = [(clusters[a], clusters[b]) for a, b in raw_edges]
    cycles = _enumerate_cycles(edges, MAX_CYCLES)
    matches: list[tuple[frozenset[int], list[dict[str, Any]]]] = []
    for cycle in cycles:
        names = [edge_owner[index] for index in sorted(cycle)]
        segments = [_loop_segments(entities[index], frame) for index in names]
        if segments_match(expected, segments, tolerance):
            matches.append((cycle, [entities[index] for index in names]))
    label = sketch.get("label")
    if not matches:
        raise ValueError(
            f"region signature matched none of {len(cycles)} closed loops in sketch "
            f"{label!r}; compare the YZ endpoints with the sketch frame, not "
            "region_index_hint"
        )
    if len(matches) > 1:
        raise ValueError(
            f"region signature matched {len(matches)} closed loops in sketch {label!r}; "
            "a cut needs exactly one selected region"
        )
    return matches[0]


def _derived_label(source_label: str, entities: list[dict[str, Any]], used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9_]", "_", str(source_label).lower()).lstrip("_")[:18] or "sketch"
    names = ",".join(sorted(str(entity.get("name", "")) for entity in entities))
    for length in (8, 10, 12):
        candidate = f"{base}_r{hashlib.sha1(names.encode('utf-8')).hexdigest()[:length]}"
        if candidate not in used:
            return candidate
    raise ValueError(f"could not derive a unique sketch label from {source_label!r}")


def derive_sketch(
    source: dict[str, Any], entities: list[dict[str, Any]], label: str
) -> dict[str, Any]:
    """Copy one loop's entities, unchanged, into a new sketch operation."""
    derived: dict[str, Any] = {
        "op": "sketch",
        "label": label,
        "plane": source.get("plane", "XY"),
        "entities": copy.deepcopy(entities),
    }
    for key in COPY_KEYS:
        if key in source:
            derived[key] = copy.deepcopy(source[key])
    return derived


def _selector(operation: dict[str, Any]) -> dict[str, Any] | None:
    region = operation.get("region")
    return region if isinstance(region, dict) else None


def _tolerance(selector: dict[str, Any]) -> float:
    value = selector.get("tolerance_mm", DEFAULT_TOLERANCE_MM)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("region.tolerance_mm must be a number")
    number = float(value)
    if not math.isfinite(number) or number <= 0 or number > MAX_TOLERANCE_MM:
        raise ValueError(f"region.tolerance_mm must be > 0 and at most {MAX_TOLERANCE_MM} mm")
    return number


def adapt_region_extrudes(
    operations: list[Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Expand every ``extrude.region`` into a derived sketch plus a plain extrude.

    Returns the rewritten operation list and one record per derivation. The
    source sketch is never modified; a region used by several extrudes is
    derived once and shared. Operations without a region pass through unchanged
    (and keep their original Python values when they are already dicts).
    """
    adapted = [
        operation if isinstance(operation, dict) else operation.model_dump(exclude_none=True)
        for operation in operations
    ]
    sketches: dict[str, dict[str, Any]] = {}
    used_labels = {
        operation["label"] for operation in adapted if isinstance(operation.get("label"), str)
    }
    records: list[dict[str, Any]] = []
    cache: dict[tuple[str, frozenset[int]], str] = {}
    result: list[dict[str, Any]] = []
    for operation in adapted:
        if operation.get("op") == "sketch" and isinstance(operation.get("label"), str):
            sketches[operation["label"]] = operation
            result.append(operation)
            continue
        selector = _selector(operation)
        if selector is None:
            result.append(operation)
            continue
        source_label = operation.get("sketch")
        if not isinstance(source_label, str):
            raise ValueError(
                f"extrude {operation.get('label')!r} uses region but does not name its "
                "source sketch by label"
            )
        if operation.get("mode") == "surface":
            raise ValueError(
                f"extrude {operation.get('label')!r} uses region with a surface extrude; "
                "region applies to a solid add/cut extrusion"
            )
        source = sketches.get(source_label)
        if source is None:
            raise ValueError(
                f"extrude {operation.get('label')!r} region source {source_label!r} is not "
                "an earlier sketch operation in this plan"
            )
        _usable_sketch(source, source_label)
        frame = resolve_frame(selector, source)
        tolerance = _tolerance(selector)
        signature = selector.get("signature_yz_mm")
        if not isinstance(signature, str):
            raise ValueError("region.signature_yz_mm must be a string")
        cycle, entities = find_region(source, signature, frame, tolerance)
        key = (source_label, cycle)
        label = cache.get(key)
        if label is None:
            label = _derived_label(source_label, entities, used_labels)
            used_labels.add(label)
            cache[key] = label
            result.append(derive_sketch(source, entities, label))
            records.append(
                {
                    "source_sketch": source_label,
                    "derived_sketch": label,
                    "signature_sha256": hashlib.sha256(signature.encode("utf-8")).hexdigest(),
                    "entity_names": [entity.get("name") for entity in entities],
                    "segment_count": len(entities),
                    "tolerance_mm": tolerance,
                    "note": (
                        "entities are copied unchanged from the source sketch; the region "
                        "was resolved offline from the boundary signature"
                    ),
                }
            )
        rewritten = dict(operation)
        rewritten["sketch"] = label
        rewritten.pop("region", None)
        result.append(rewritten)
    return result, records
