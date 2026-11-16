"""Offline TXT bulb preparation, never a Creo surface or mass-property simulator.

The adapter preserves the recorded curves. It only changes their representation
and orientation to fit the existing single-curve guide contract (FEAT-065/066).
"""

from __future__ import annotations

import bisect
import copy
import hashlib
import math
import re
from pathlib import Path
from typing import Any

NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
ROLE_LABELS = {
    "rear_section": "bulb_rear",
    "middle_section": "bulb_mid",
    "upper": "bulb_upper",
    "side": "bulb_side",
    "lower": "bulb_lower",
}
EXACT_TOLERANCE_MM = 1e-7
# Diagnostic only: the existing surface group contract also uses 0.01 mm.
# This does not set or predict Creo's model accuracy or regeneration tolerance.
NETWORK_TOLERANCE_M = 1e-5


def _numbers(text: str) -> list[float]:
    return [float(value) for value in re.findall(NUMBER, text)]


def _points(text: str) -> list[list[float]]:
    points = [_numbers(group) for group in re.findall(r"\(([^()]+)\)", text)]
    if not points or any(len(point) != 3 for point in points):
        raise ValueError("Expected recorded 3D point coordinates")
    return points


def _recorded_curve(block: str) -> dict[str, Any]:
    controls = next(line for line in block.splitlines() if "控制点依次为" in line)
    if "4阶（3次）非周期样条" not in controls:
        raise ValueError("Expected a recorded non-periodic cubic B-spline")
    values = next(line for line in block.splitlines() if "权重依次为" in line)
    weights, knots = values.split("；节点依次为", 1)
    return {
        "degree": 3,
        "control_points": _points(controls.split("控制点依次为", 1)[1]),
        "knots": _numbers(knots),
        "weights": _numbers(weights.split("权重依次为", 1)[1]),
    }


def _parse_source(text: str, filename: str, sha256: str) -> dict[str, Any]:
    blocks: dict[int, str] = {}
    for index, sketch in ((18, 64), (19, 65), (20, 67), (21, 69), (22, 70), (23, 72)):
        matches = re.findall(
            rf"^A{index:02d}．Sketch{sketch}：[\s\S]*?(?=^A\d+．|\Z)", text, re.MULTILINE
        )
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one A{index:02d}/Sketch{sketch} block")
        blocks[index] = matches[0].strip()
    geometry: dict[str, Any] = {}
    for index, role in ((18, "upper"), (19, "lower")):
        line = next(line for line in blocks[index].splitlines() if "：直线，从" in line)
        geometry[role + "_line_m"] = _points(line)
        geometry[role + "_bend"] = _recorded_curve(blocks[index])
    for index, role in ((20, "side"), (22, "middle_section"), (23, "rear_section")):
        geometry[role] = _recorded_curve(blocks[index])
    auxiliary = next(line for line in blocks[20].splitlines() if "：直线，从" in line)
    geometry["excluded_side_auxiliary_line_m"] = _points(auxiliary)
    point = next(line for line in blocks[21].splitlines() if "独立点 1：" in line)
    geometry["tip_m"] = _points(point)[0]
    excerpt = "\n\n".join(blocks.values()) + "\n"
    return {
        "format": "frigate_bulb_source_v1",
        "source": {
            "filename": filename,
            "sha256": sha256,
            "units": "m",
            "half_side": "positive_y_from_appendix",
            "anchors": [f"A{index:02d}" for index in blocks],
            "excerpt_sha256": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
            "excerpt": excerpt,
        },
        "geometry": geometry,
    }


def extract_source(path: Path) -> dict[str, Any]:
    """Extract only A18--A23; missing or duplicate anchors fail explicitly."""
    raw = path.read_bytes()
    return _parse_source(raw.decode("utf-8-sig"), path.name, hashlib.sha256(raw).hexdigest())


def verify_source_snapshot(source: dict[str, Any]) -> bool:
    """Re-extract the frozen text, rather than compare JSON geometry to itself."""
    try:
        meta = source["source"]
        parsed = _parse_source(meta["excerpt"], meta["filename"], meta["sha256"])
        return parsed == source
    except (KeyError, ValueError, StopIteration, TypeError):
        return False


def join_line_bezier(line: list[list[float]], bend: dict[str, Any]) -> dict[str, Any]:
    """Return rear-to-tip cubic B-spline exactly equivalent to the two spans.

    TXT line order is join -> rear, and its Bézier order is tip -> join.
    Degree elevation of a straight line is exact; a triple internal knot
    preserves the recorded junction, including a possible tangent break.
    """
    if (
        bend["degree"] != 3
        or len(bend["control_points"]) != 4
        or bend["knots"] != [0] * 4 + [1] * 4
        or bend["weights"] != [1] * 4
    ):
        raise ValueError("Expected cubic Bezier with unit weights and recorded clamped knots")
    join, rear = line
    if join != bend["control_points"][-1]:
        raise ValueError("Recorded line/Bezier join differs; no automatic repair is allowed")
    if rear == join:
        raise ValueError("Recorded line has zero length at join")
    elevated = [
        [rear[axis] + (join[axis] - rear[axis]) * t / 3 for axis in range(3)] for t in range(4)
    ]
    return {
        "degree": 3,
        "control_points": elevated + list(reversed(copy.deepcopy(bend["control_points"])))[1:],
        "knots": [0] * 4 + [1] * 3 + [2] * 4,
        "weights": [1] * 7,
    }


def evaluate(curve: dict[str, Any], parameter: float) -> list[float]:
    """Homogeneous de Boor evaluation of the recorded curve, in source metres."""
    degree, knots, controls = curve["degree"], curve["knots"], curve["control_points"]
    weights = curve["weights"]
    end = len(controls)
    if not math.isfinite(parameter) or not knots[degree] <= parameter <= knots[end]:
        raise ValueError("Parameter outside the finite B-spline domain")
    span = end - 1 if parameter == knots[end] else bisect.bisect_right(knots, parameter) - 1
    work = [
        [*(value * weights[i] for value in controls[i]), weights[i]]
        for i in range(span - degree, span + 1)
    ]
    for level in range(1, degree + 1):
        for j in range(degree, level - 1, -1):
            i = span - degree + j
            denominator = knots[i + degree + 1 - level] - knots[i]
            alpha = (parameter - knots[i]) / denominator if denominator else 0
            work[j] = [(1 - alpha) * a + alpha * b for a, b in zip(work[j - 1], work[j])]
    return [value / work[degree][-1] for value in work[degree][:-1]]


def _reverse(curve: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(curve)
    total = curve["knots"][0] + curve["knots"][-1]
    result["knots"] = [total - value for value in reversed(curve["knots"])]
    result["control_points"].reverse()
    result["weights"].reverse()
    return result


def _curves(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if source["source"]["units"] != "m":
        raise ValueError("Source must explicitly use metres")
    geometry = source["geometry"]
    curves = {role: copy.deepcopy(geometry[role]) for role in ("rear_section", "middle_section")}
    for role in ("upper", "lower"):
        curves[role] = _reverse(
            join_line_bezier(geometry[role + "_line_m"], geometry[role + "_bend"])
        )
    curves["side"] = _reverse(geometry["side"])
    return curves


def _scale(value: float) -> float:
    if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError("mm_per_m must be a finite positive number")
    return float(value)


def build_plan(source: dict[str, Any], mm_per_m: float = 1000) -> dict[str, Any]:
    """Public execute_plan payload; no service submission and no guessed CAD bbox."""
    factor = _scale(mm_per_m)
    curves = _curves(source)
    operations: list[dict[str, Any]] = []
    for role, label in ROLE_LABELS.items():
        curve = copy.deepcopy(curves[role])
        points = curve.pop("control_points")
        if role.endswith("section"):
            plane, offset, axes = "YZ", points[0][0], (1, 2)
            fixed_axis = 0
        elif role == "side":
            plane, offset, axes = "XY", points[0][2], (0, 1)
            fixed_axis = 2
        else:
            plane, offset, axes = "XZ", points[0][1], (0, 2)
            fixed_axis = 1
        if any(point[fixed_axis] != offset for point in points):
            raise ValueError(f"{role} is not in its recorded coordinate plane")
        operations.append(
            {
                "op": "sketch",
                "label": label,
                "plane": plane,
                "offset": offset * factor,
                "dimensioning": "autodim",
                "entities": [
                    {
                        "type": "b_spline",
                        "name": "curve",
                        **curve,
                        "control_points": [
                            [point[axis] * factor for axis in axes] for point in points
                        ],
                    }
                ],
            }
        )
    operations.extend(
        [
            {
                "op": "datum_points",
                "label": "bulb_tip",
                "points": [
                    {"name": "tip", "position": [v * factor for v in source["geometry"]["tip_m"]]}
                ],
            },
            {
                "op": "surface_loft",
                "label": "bulb_half_surface",
                "sections": [
                    "bulb_rear",
                    "bulb_mid",
                    # The identical three-guide case with the point first
                    # failed regeneration; point last passed in Creo 12.4.
                    {"kind": "datum_point_feature", "label": "bulb_tip"},
                ],
                "guides": ["bulb_upper", "bulb_side", "bulb_lower"],
                "interpolation": "smooth",
            },
        ]
    )
    return {"operations": operations, "assertions": {"require_solid": False}}


def _at_coordinate(curve: dict[str, Any], axis: int, target: float) -> tuple[float, list[float]]:
    """Find the rear/middle crossing on these curves, not their global extrema.

    The lower guide briefly overshoots the tip X. Our requested rear/middle X
    values are below the tip, so that turn cannot introduce a second crossing.
    The tip itself is evaluated by its endpoint, never by this search.
    """
    left, right = curve["knots"][curve["degree"]], curve["knots"][len(curve["control_points"])]
    start, end = evaluate(curve, left)[axis], evaluate(curve, right)[axis]
    if not min(start, end) <= target <= max(start, end):
        raise ValueError("Requested intersection coordinate is outside the recorded curve")
    for _ in range(90):
        middle = (left + right) / 2
        if (evaluate(curve, middle)[axis] < target) == (start < end):
            left = middle
        else:
            right = middle
    parameter = (left + right) / 2
    return parameter, evaluate(curve, parameter)


def _bernstein(points: list[list[float]], t: float) -> list[float]:
    return [
        sum(
            math.comb(3, j) * (1 - t) ** (3 - j) * t**j * point[axis]
            for j, point in enumerate(points)
        )
        for axis in range(3)
    ]


def _bezier_maximum(points: list[list[float]], axis: int) -> tuple[float, float]:
    """Cubic axis maximum from all real derivative roots in [0, 1]."""
    p0, p1, p2, p3 = [point[axis] for point in points]
    a = 3 * (-p0 + 3 * p1 - 3 * p2 + p3)
    b = 2 * (3 * p0 - 6 * p1 + 3 * p2)
    c = -3 * p0 + 3 * p1
    candidates = [0.0, 1.0]
    if abs(a) < 1e-14:
        roots = [-c / b] if abs(b) >= 1e-14 else []
    else:
        discriminant = b * b - 4 * a * c
        roots = (
            [(-b + sign * math.sqrt(discriminant)) / (2 * a) for sign in (-1, 1)]
            if discriminant >= 0
            else []
        )
    candidates.extend(root for root in roots if 0 <= root <= 1)
    return max(((_bernstein(points, t)[axis], t) for t in candidates))


def audit(source: dict[str, Any], plan: dict[str, Any], mm_per_m: float = 1000) -> dict[str, Any]:
    """Check curve equivalence, frame reconstruction and the nine network crossings.

    No surface extrema, area, volume, feature completeness or reload result is
    inferred from these computations. Those remain measurements for Creo.
    """
    from .schema import validate_operations

    factor = _scale(mm_per_m)
    geometry = source["geometry"]
    curves = _curves(source)
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, **detail: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), **detail})

    check("source_reextracted_from_excerpt", verify_source_snapshot(source))
    try:
        validate_operations(copy.deepcopy(plan["operations"]))
        check("public_operations_schema", True)
    except ValueError as error:
        check("public_operations_schema", False, error=str(error))
    join_errors = []
    for role in ("upper", "lower"):
        joined = join_line_bezier(geometry[role + "_line_m"], geometry[role + "_bend"])
        join, rear = geometry[role + "_line_m"]
        for i in range(1001):
            t = i / 1000
            linear = [a * (1 - t) + b * t for a, b in zip(rear, join)]
            cubic = _bernstein(list(reversed(geometry[role + "_bend"]["control_points"])), t)
            join_errors.extend(
                [
                    math.dist(evaluate(joined, t), linear) * factor,
                    math.dist(evaluate(joined, 1 + t), cubic) * factor,
                ]
            )
        for t in (math.nextafter(1, 0), 1, math.nextafter(1, 2)):
            join_errors.append(math.dist(evaluate(joined, t), join) * factor)
    max_join = max(join_errors)
    check("exact_line_bezier_equivalence", max_join <= EXACT_TOLERANCE_MM, max_error_mm=max_join)

    expected = build_plan(source, factor)
    check("public_plan_shape", plan == expected)
    by_label = {op["label"]: op for op in plan["operations"] if op["op"] == "sketch"}
    frame_errors = []
    for role, label in ROLE_LABELS.items():
        sketch = by_label[label]
        entity = sketch["entities"][0]
        check(
            label + "_single_curve", len(sketch["entities"]) == 1 and entity["type"] == "b_spline"
        )
        check(
            label + "_nurbs_metadata",
            all(entity[key] == curves[role][key] for key in ("degree", "knots", "weights")),
        )
        for local, point in zip(entity["control_points"], curves[role]["control_points"]):
            u, v = local
            if sketch["plane"] == "YZ":
                restored = [sketch["offset"], u, v]
            elif sketch["plane"] == "XZ":
                restored = [u, sketch["offset"], v]
            else:
                restored = [u, v, sketch["offset"]]
            frame_errors.append(math.dist(restored, [v * factor for v in point]))
    max_frame = max(frame_errors)
    check(
        "all_control_points_restored_to_global_mm",
        max_frame <= EXACT_TOLERANCE_MM,
        max_error_mm=max_frame,
    )
    point_op = next(op for op in plan["operations"] if op["op"] == "datum_points")
    check(
        "tip_global_mm",
        point_op["points"][0]["position"] == [v * factor for v in geometry["tip_m"]],
    )

    intersections = []
    for section_role in ("rear_section", "middle_section", "tip"):
        for guide_role in ("upper", "side", "lower"):
            guide = curves[guide_role]
            if section_role == "tip":
                target = geometry["tip_m"]
                parameter = guide["knots"][guide["degree"]]
                actual = evaluate(guide, parameter)
            else:
                section = geometry[section_role]
                if guide_role == "side":
                    _, target = _at_coordinate(section, 2, geometry["tip_m"][2])
                else:
                    target = section["control_points"][0 if guide_role == "upper" else -1]
                parameter, actual = _at_coordinate(guide, 0, target[0])
            gap = math.dist(actual, target) * factor
            intersections.append(
                {
                    "section": section_role,
                    "guide": guide_role,
                    "guide_parameter": parameter,
                    "section_point_mm": [v * factor for v in target],
                    "guide_point_mm": [v * factor for v in actual],
                    "gap_mm": gap,
                }
            )
    max_gap = max(item["gap_mm"] for item in intersections)
    network_tolerance = NETWORK_TOLERANCE_M * factor
    check(
        "source_network_intersections", max_gap <= network_tolerance, tolerance_mm=network_tolerance
    )
    rear_mid = evaluate(geometry["rear_section"], 0.5)
    lower_max_x, lower_parameter = _bezier_maximum(geometry["lower_bend"]["control_points"], 0)
    return {
        "mode": "offline",
        "passed": all(item["passed"] for item in checks),
        "creo_tested": False,
        "source_sha256": source["source"]["sha256"],
        "mm_per_m": factor,
        "guide_orientation": "tip_to_rear",
        "half_side": "positive_y",
        "checks": checks,
        "max_join_error_mm": max_join,
        "max_frame_error_mm": max_frame,
        "max_intersection_gap_mm": max_gap,
        "network_tolerance_mm": network_tolerance,
        "intersections": intersections,
        "rear_section_midpoint_mm": [v * factor for v in rear_mid],
        "rear_section_control_point_max_y_mm": max(
            p[1] for p in geometry["rear_section"]["control_points"]
        )
        * factor,
        "lower_guide_max_x_mm": lower_max_x * factor,
        "lower_guide_original_bezier_parameter_at_max_x": lower_parameter,
        "lower_guide_forward_of_tip_mm": (lower_max_x - geometry["tip_m"][0]) * factor,
        "not_verified": [
            "Creo sketch solving, stored control points and single-curve geometry count",
            "C0 internal-knot retention and actual boundary-blend regeneration",
            "surface shape, extrema, area and absence of self-intersection",
            "planar caps, quilt merge, solidify, mirror and solid volume",
            "save/reload, revision, rollback and Creo 9/10 compatibility",
        ],
    }
