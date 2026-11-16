"""FEAT-069 G1: region signatures in the sketch's YZ plane.

The TXT names a cut region by the endpoint pairs of every boundary segment, not
by an index:

    [B-REGION] region=0 signature_yz_mm=(-4.988707,-11.335864|-1.173416,-14.314501;...)

``region_index_hint`` is traceability only. This module parses that signature,
maps a region's local sketch coordinates through its frame (``origin + u*xdir +
v*ydir``) and refuses to return more than one match. It is a contract only: no
extrude op accepts it until a native region/contour selection path is proven.
"""

from __future__ import annotations

import math
from typing import Any, Iterable

DEFAULT_TOLERANCE_MM = 0.001
MAX_TOLERANCE_MM = 10.0

Point = tuple[float, float]
Segment = tuple[Point, Point]

DESCRIPTION = (
    "A region signature is 'signature_yz_mm=(y,z|y,z;y,z|y,z;...)' with every boundary "
    "segment's two endpoints in the sketch's global YZ coordinates. Endpoint order and "
    "segment order are irrelevant; duplicates and non-finite values are refused. "
    "region_index_hint is never used for selection."
)


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or type(value) not in (int, float):
        raise ValueError(f"{path} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{path} must be finite")
    return number


def _point(value: Any, path: str) -> Point:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{path} must be [y, z] in mm")
    return (_number(value[0], f"{path}[0]"), _number(value[1], f"{path}[1]"))


def _segment(value: Any, path: str) -> Segment:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{path} must name exactly two endpoints")
    first = _point(value[0], f"{path}[0]")
    second = _point(value[1], f"{path}[1]")
    if first == second:
        raise ValueError(f"{path} must name two distinct endpoints")
    return _ordered(first, second)


def _ordered(first: Point, second: Point) -> Segment:
    """Endpoint order carries no meaning, so freeze one representation."""
    return (first, second) if first <= second else (second, first)


def parse_region_signature(text: str) -> frozenset[Segment]:
    """Parse ``(y,z|y,z;...)`` into an unordered, endpoint-order-free set."""
    if not isinstance(text, str):
        raise ValueError("region signature must be a string")
    value = text.strip()
    if value.startswith("signature_yz_mm="):
        value = value[len("signature_yz_mm=") :].strip()
    if not value.startswith("(") or not value.endswith(")"):
        raise ValueError(
            "region signature must be wrapped in parentheses: "
            "(y,z|y,z;y,z|y,z;...); a region index hint is not a signature"
        )
    body = value[1:-1].strip()
    if not body:
        raise ValueError("region signature names no segments")
    segments: set[Segment] = set()
    for index, chunk in enumerate(body.split(";")):
        endpoints = chunk.split("|")
        if len(endpoints) != 2:
            raise ValueError(
                f"region signature segment {index} must be 'y,z|y,z', got {chunk.strip()!r}"
            )
        points = []
        for endpoint_index, endpoint in enumerate(endpoints):
            coordinates = endpoint.split(",")
            if len(coordinates) != 2:
                raise ValueError(
                    f"region signature segment {index} endpoint {endpoint_index} must be "
                    f"'y,z', got {endpoint.strip()!r}"
                )
            try:
                points.append((float(coordinates[0]), float(coordinates[1])))
            except ValueError as error:
                raise ValueError(
                    f"region signature segment {index} has a non-numeric coordinate: "
                    f"{endpoint.strip()!r}"
                ) from error
        segment = _segment(points, f"region signature segment {index}")
        if segment in segments:
            raise ValueError(
                f"region signature repeats segment {segment}; a duplicated boundary would "
                "make membership ambiguous"
            )
        segments.add(segment)
    return frozenset(segments)


def validate_yz_sketch_frame(frame: dict[str, Any], path: str = "frame") -> None:
    """Require the DTM-right frame that makes local ``(u,v)`` map to ``(1.5,v,-u)``.

    The global point is ``origin + u*xdir + v*ydir`` (TXT rule). For the Arm7
    bottom sketch that means x is fixed at 1.5 and y=v, z=-u. If any of that
    fails, the signature and the sketch are not in the same plane and no
    comparison is meaningful.
    """
    if not isinstance(frame, dict):
        raise ValueError(f"{path} must be an object with origin/xdir/ydir")
    origin = _point3(frame.get("origin"), f"{path}.origin")
    xdir = _point3(frame.get("xdir"), f"{path}.xdir")
    ydir = _point3(frame.get("ydir"), f"{path}.ydir")
    for name, vector in (("xdir", xdir), ("ydir", ydir)):
        length = math.sqrt(sum(component * component for component in vector))
        if abs(length - 1.0) > 1e-6:
            raise ValueError(f"{path}.{name} must be a unit vector, got length {length!r}")
    if abs(origin[0] - 1.5) > 1e-6:
        raise ValueError(
            f"{path}.origin.x must be 1.5 for the TXT's (1.5,v,-u) mapping, got {origin[0]!r}; "
            "the signature is not on the same DTM-right plane"
        )
    if abs(xdir[0]) > 1e-6 or abs(ydir[0]) > 1e-6:
        raise ValueError(
            f"{path}: both xdir and ydir must lie in the YZ plane (x component 0); got "
            f"xdir={xdir!r}, ydir={ydir!r}"
        )
    if abs(dot(xdir, ydir)) > 1e-6:
        raise ValueError(f"{path}.xdir and ydir must be orthogonal, dot={dot(xdir, ydir)!r}")
    if abs(xdir[1]) > 1e-6 or abs(ydir[2]) > 1e-6:
        raise ValueError(
            f"{path}: the TXT frame maps local u to global -Z and v to global +Y; got "
            f"xdir={xdir!r}, ydir={ydir!r}"
        )
    if xdir[2] >= 0 or ydir[1] <= 0:
        raise ValueError(
            f"{path}: expected xdir≈(0,0,-1) and ydir≈(0,1,0), got {xdir!r} and {ydir!r}"
        )


def _point3(value: Any, path: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{path} must be [x, y, z]")
    return (
        _number(value[0], f"{path}[0]"),
        _number(value[1], f"{path}[1]"),
        _number(value[2], f"{path}[2]"),
    )


def dot(first: Iterable[float], second: Iterable[float]) -> float:
    return sum(a * b for a, b in zip(first, second))


def sketch_point_to_yz(frame: dict[str, Any], point: Any, path: str = "point") -> Point:
    """Map one local ``(u, v)`` sketch point to global ``(y, z)`` mm."""
    validate_yz_sketch_frame(frame)
    local = _point(point, path)
    origin = _point3(frame["origin"], "frame.origin")
    xdir = _point3(frame["xdir"], "frame.xdir")
    ydir = _point3(frame["ydir"], "frame.ydir")
    world = [origin[axis] + local[0] * xdir[axis] + local[1] * ydir[axis] for axis in range(3)]
    return (world[1], world[2])


def region_yz_segments(
    region: dict[str, Any], frame: dict[str, Any] | None = None, path: str = "region"
) -> frozenset[Segment]:
    """The region's boundary as global YZ segments.

    A region either carries a ready ``signature_yz_mm`` or local ``segments`` plus
    the sketch ``frame`` (its own or the caller's).
    """
    if not isinstance(region, dict):
        raise ValueError(f"{path} must be an object")
    signature = region.get("signature_yz_mm")
    if signature is not None:
        return parse_region_signature(signature)
    raw_segments = region.get("segments")
    if not isinstance(raw_segments, (list, tuple)) or not raw_segments:
        raise ValueError(f"{path} needs signature_yz_mm or a non-empty segments list")
    local_frame = region.get("frame", frame)
    if local_frame is None:
        raise ValueError(f"{path} has local segments but no frame")
    validate_yz_sketch_frame(local_frame, f"{path}.frame")
    segments: set[Segment] = set()
    for index, raw in enumerate(raw_segments):
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            raise ValueError(f"{path}.segments[{index}] must name exactly two endpoints")
        first = sketch_point_to_yz(local_frame, raw[0], f"{path}.segments[{index}][0]")
        second = sketch_point_to_yz(local_frame, raw[1], f"{path}.segments[{index}][1]")
        segment = _segment([first, second], f"{path}.segments[{index}]")
        if segment in segments:
            raise ValueError(f"{path}.segments[{index}] repeats another segment")
        segments.add(segment)
    return frozenset(segments)


def segments_match(
    left: Iterable[Segment], right: Iterable[Segment], tolerance: float = DEFAULT_TOLERANCE_MM
) -> bool:
    """Unordered, endpoint-order-free comparison within ``tolerance`` mm."""
    left = list(left)
    right = list(right)
    if len(left) != len(right):
        return False
    remaining = list(right)
    for segment in left:
        for index, candidate in enumerate(remaining):
            if _segments_close(segment, candidate, tolerance):
                remaining.pop(index)
                break
        else:
            return False
    return True


def _segments_close(first: Segment, second: Segment, tolerance: float) -> bool:
    forward = max(
        abs(first[0][0] - second[0][0]),
        abs(first[0][1] - second[0][1]),
        abs(first[1][0] - second[1][0]),
        abs(first[1][1] - second[1][1]),
    )
    reverse = max(
        abs(first[0][0] - second[1][0]),
        abs(first[0][1] - second[1][1]),
        abs(first[1][0] - second[0][0]),
        abs(first[1][1] - second[0][1]),
    )
    return min(forward, reverse) <= tolerance


def match_region(
    signature: str | Iterable[Segment],
    regions: list[dict[str, Any]],
    frame: dict[str, Any] | None = None,
    tolerance: float = DEFAULT_TOLERANCE_MM,
) -> dict[str, Any]:
    """Return the one region whose YZ boundary set equals the signature.

    0 matches and >1 matches both raise: a signature is only useful when it is
    unique. ``region_index_hint`` is ignored, by design.
    """
    tolerance = _number(tolerance, "tolerance")
    if tolerance <= 0 or tolerance > MAX_TOLERANCE_MM:
        raise ValueError(f"tolerance must be > 0 and at most {MAX_TOLERANCE_MM} mm")
    expected = (
        parse_region_signature(signature)
        if isinstance(signature, str)
        else frozenset(_segment(item, "signature segment") for item in signature)
    )
    if not regions:
        raise ValueError("no candidate regions were supplied")
    matches: list[str] = []
    for index, region in enumerate(regions):
        name = region.get("name") if isinstance(region, dict) else None
        name = str(name) if name is not None else f"region[{index}]"
        actual = region_yz_segments(region, frame, name)
        if segments_match(expected, actual, tolerance):
            matches.append(name)
    names = [str(region.get("name", f"region[{index}]")) for index, region in enumerate(regions)]
    if not matches:
        raise ValueError(
            f"region signature matched none of {len(regions)} regions ({names}); compare the "
            "YZ endpoints against the active sketch frame, not region_index_hint"
        )
    if len(matches) > 1:
        raise ValueError(
            f"region signature matched more than one region {matches}; a cut needs exactly one "
            "selected region, so the signature is not unique in this sketch"
        )
    return {"region": matches[0], "segments": len(expected)}
