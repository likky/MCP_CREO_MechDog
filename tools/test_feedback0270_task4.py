"""0.27.0 feedback task 4: off-plane revolve axis and two equal-radius edges.

Two live cases, both recording evidence rather than guessing:

``axis_off_plane``
    A sketch on a plane offset 50 mm from XY, revolved about the built-in X
    axis. The axis is parallel to the section plane but does not lie in it, so
    the kernel owns the verdict. The case records whether the failure names the
    plane distance and whether a ``revolve_axis`` block is published at all -
    today the axis block only appears after a successful resolve.

``two_equal_radius_edges``
    A plate with two bosses of the same radius, so four circular edges share one
    radius and only their centres differ. Two rounds select one edge each by
    ``center_mm``; both must succeed on the intended boss, and the receipt is
    checked for any echo of the resolved centre.
"""

import argparse
import asyncio
import hashlib
import json
import math
import platform
import sys
import time
import uuid
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from creo_mechdog.paths import SOURCE_PATHS  # noqa: E402
from tools.sheetmetal_live import LiveRunner, failure_text, require_manual_start, unique_name  # noqa: E402
from tools.test_feedback0270_same_circle import (  # noqa: E402
    arc_point,
    circular_groups,
    revision_of,
    saved_reload,
)

ROOT = SOURCE_PATHS.resource_root
HANG_BUDGET_SECONDS = 240.0
PLATE = {"x": 160.0, "y": 60.0, "z": 10.0}
BOSS_RADIUS = 20.0
BOSS_HEIGHT = 10.0
BOSS_X = 40.0

PLATE_VOLUME = PLATE["x"] * PLATE["y"] * PLATE["z"] + 2.0 * math.pi * BOSS_RADIUS**2 * BOSS_HEIGHT


def rectangle(name, x0, y0, x1, y1):
    return {"type": "rectangle", "name": name, "min": [x0, y0], "max": [x1, y1]}


def circle(name, x, y, radius=BOSS_RADIUS):
    return {"type": "circle", "name": name, "center": [x, y], "radius": radius}


OFF_PLANE_PLAN = [
    {
        "op": "sketch",
        "label": "lifted_profile",
        "plane": "XY",
        "offset": 50.0,
        "entities": [rectangle("lifted", 10.0, -5.0, 20.0, 5.0)],
    },
    {
        "op": "datum_axis",
        "label": "x_axis",
        # X axis = intersection of the XZ (id 4) and XY (id 6) datum planes.
        "references": [{"kind": "plane", "id": 4}, {"kind": "plane", "id": 6}],
    },
    {
        "op": "revolve",
        "label": "lifted_revolve",
        "sketch": "lifted_profile",
        "angle": 360.0,
        "mode": "add",
        "direction": "positive",
        "axis": {"kind": "datum_axis_feature", "label": "x_axis"},
    },
]

TWO_EDGE_BASE_PLAN = [
    {
        "op": "sketch",
        "label": "plate_profile",
        "plane": "XY",
        "entities": [
            rectangle("plate", -PLATE["x"] / 2, -PLATE["y"] / 2, PLATE["x"] / 2, PLATE["y"] / 2)
        ],
    },
    {"op": "extrude", "label": "plate", "sketch": "plate_profile", "depth": PLATE["z"]},
    {
        "op": "sketch",
        "label": "bosses_profile",
        "plane": "XY",
        "offset": PLATE["z"],
        "entities": [
            circle("boss_left", -BOSS_X, 0.0),
            circle("boss_right", BOSS_X, 0.0),
        ],
    },
    {
        "op": "extrude",
        "label": "bosses",
        "sketch": "bosses_profile",
        "depth": BOSS_HEIGHT,
        "mode": "add",
    },
]


def rim_selector(center, point) -> dict:
    """One boss rim: centre + radius + a point on the intended span.

    A boss rim comes back as more than one arc of the same circle, so radius +
    centre alone names several edges and a tighter ``tolerance_mm`` cannot
    separate them (FEAT-068, 0.27.0 feedback).
    """
    return {
        "kind": "geometry_selector",
        "target": "edge",
        "radius_mm": BOSS_RADIUS,
        "center_mm": list(center),
        "tolerance_mm": 0.01,
        "point_mm": list(point),
    }


def rounds_plan(selectors: dict) -> list:
    return [
        {
            "op": "round",
            "label": "round_left_top",
            "size": 2.0,
            "references": [{"edge": selectors["left"]}],
        },
        {
            "op": "round",
            "label": "round_right_top",
            "size": 2.0,
            "references": [{"edge": selectors["right"]}],
        },
    ]


def axis_block(terminal: dict) -> dict:
    result = terminal.get("result") if isinstance(terminal, dict) else None
    block = result if isinstance(result, dict) else {}
    operations = block.get("operations")
    for entry in operations if isinstance(operations, list) else []:
        if isinstance(entry, dict) and isinstance(entry.get("revolve_axis"), dict):
            return entry["revolve_axis"]
    return {}


def plane_relation_block(terminal: dict) -> dict:
    """The measured axis/sketch-plane relation (DEV-093 T4)."""
    result = terminal.get("result") if isinstance(terminal, dict) else None
    block = result if isinstance(result, dict) else {}
    operations = block.get("operations")
    for entry in operations if isinstance(operations, list) else []:
        if isinstance(entry, dict) and isinstance(entry.get("revolve_axis_plane_relation"), dict):
            return entry["revolve_axis_plane_relation"]
    return {}


def volume_of(snapshot: dict) -> float | None:
    inspection = snapshot.get("inspection") if isinstance(snapshot.get("inspection"), dict) else {}
    value = inspection.get("volume_mm3")
    return value if isinstance(value, (int, float)) else None


def close(value, expected: float, tolerance: float) -> bool:
    return isinstance(value, (int, float)) and abs(float(value) - expected) <= tolerance


def operation_entries(terminal: dict) -> list:
    result = terminal.get("result") if isinstance(terminal, dict) else None
    entries = (result or {}).get("operations") if isinstance(result, dict) else None
    return (
        [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
    )


async def run_off_plane(runner: LiveRunner) -> dict:
    name = unique_name("t4_off_plane")
    created = await runner.submit(
        "axis_off_plane:create",
        "creo_execute_plan",
        {"model_name": name, "model_type": "part", "operations": OFF_PLANE_PLAN},
    )
    terminal = await runner.wait_job(created["job_id"], budget=HANG_BUDGET_SECONDS)
    snapshot = await runner.snapshot(created["model_id"])
    block = axis_block(terminal)
    message = failure_text(terminal) if terminal.get("status") != "succeeded" else None
    entry = {
        "case": "axis_off_plane",
        "model_name": name,
        "model_id": created["model_id"],
        "job_id": created["job_id"],
        "job_status": terminal.get("status"),
        "volume_mm3": volume_of(snapshot),
        "revolve_axis": block or None,
        "failure": message,
        "section_plane_offset_mm": 50.0,
        "axis_plane_distance_mm": 50.0,
        "axis_lies_in_section_plane": False,
    }
    text = json.dumps(message, ensure_ascii=False).lower() if message else ""
    relation = plane_relation_block(terminal)
    entry["plane_relation"] = relation or None
    entry["failure_names_plane_distance"] = any(
        word in text for word in ("distance", "offset", "plane", "50")
    )
    entry["axis_block_published"] = bool(block)
    entry["plane_relation_published"] = bool(relation)
    # The contract asks for either a named axis/plane relationship or an
    # explanation of the axis the kernel used. A bare kernel refusal meets
    # neither, so the gap is recorded instead of being read as a pass.
    entry["diagnosis_gap"] = (
        terminal.get("status") != "succeeded"
        and not entry["failure_names_plane_distance"]
        and not block
        and not relation
    )
    entry["contract_met"] = not entry["diagnosis_gap"]
    problems = []
    # DEV-093 T4: the relation must be measured, not restated from the request.
    if not relation:
        problems.append("the operation record carries no revolve_axis_plane_relation")
    else:
        if relation.get("available") is not True:
            problems.append(f"plane relation unavailable: {relation.get('reason')!r}")
        if not close(relation.get("origin_distance_mm"), 50.0, 1e-6):
            problems.append(
                f"origin_distance_mm={relation.get('origin_distance_mm')!r}; the X axis is 50 mm "
                "from the z=50 sketch plane"
            )
        if relation.get("axis_lies_in_plane") is not False:
            problems.append(
                f"axis_lies_in_plane={relation.get('axis_lies_in_plane')!r}; a 50 mm offset is "
                "not in the plane"
            )
    if message and "from the plane" not in json.dumps(message, ensure_ascii=False):
        problems.append("the refusal does not repeat the measured plane distance")
    entry["problems"] = problems
    if terminal.get("status") == "succeeded":
        entry["problems"].append(
            "the kernel accepted a revolve about an axis 50 mm outside the section plane; "
            "the request was expected to be refused or to need an explicit diagnosis"
        )
    if terminal.get("status") != "succeeded" and not message:
        entry["problems"].append("failed without any message")
    entry["passed"] = not entry["problems"]
    return runner.case(entry)


MICRO_OFFSET_MM = 0.00039

MICRO_OFFSET_PLAN = [
    {
        "op": "datum_plane",
        "label": "z_micro",
        "reference": {"kind": "datum_plane", "axis": "z", "offset": 0},
        "offset": MICRO_OFFSET_MM,
    },
    {
        "op": "datum_axis",
        "label": "micro_axis",
        # z=0.00039 crossing x=0: a Y-direction line 0.00039 mm above the XY plane.
        # A plane *feature* label resolves as datum_feature; kind datum_plane
        # references resolve by id/axis/normal and ignore a label.
        "references": [
            {"kind": "datum_feature", "label": "z_micro"},
            {"kind": "datum_plane", "axis": "x", "offset": 0},
        ],
    },
    {
        "op": "sketch",
        "label": "micro_profile",
        "plane": "XY",
        "entities": [rectangle("wall", 20.0, 5.0, 30.0, 10.0)],
    },
    {
        "op": "revolve",
        "label": "micro_solid",
        "sketch": "micro_profile",
        "angle": 360.0,
        "mode": "add",
        "direction": "positive",
        "axis": {"kind": "datum_axis_feature", "label": "micro_axis"},
    },
]

TILTED_AXIS_PLAN = [
    # The tilt plane is built from three datum points instead of a datum_plane
    # angle: the angle mode is refused/failed on this build, and through_points
    # reaches the same geometry without depending on it.
    {
        "op": "datum_points",
        "label": "tilt_p1",
        "points": [{"name": "p1", "position": [0.0, 0.0, 0.0]}],
    },
    {
        "op": "datum_points",
        "label": "tilt_p2",
        "points": [{"name": "p2", "position": [10.0, 0.0, 0.0]}],
    },
    {
        "op": "datum_points",
        "label": "tilt_p3",
        "points": [{"name": "p3", "position": [0.0, 4.0, 6.928203230275509]}],
    },
    {
        "op": "datum_plane",
        "label": "tilt_plane",
        "reference": {"kind": "through_points", "points": ["tilt_p1", "tilt_p2", "tilt_p3"]},
    },
    {
        "op": "datum_axis",
        "label": "tilt_axis",
        # The tilt plane crosses x=0 in a line that is out of the XY plane.
        "references": [
            {"kind": "datum_feature", "label": "tilt_plane"},
            {"kind": "datum_plane", "axis": "x", "offset": 0},
        ],
    },
    {
        "op": "sketch",
        "label": "tilt_profile",
        "plane": "XY",
        "entities": [rectangle("wall", 5.0, 20.0, 10.0, 30.0)],
    },
    {
        "op": "revolve",
        "label": "tilt_solid",
        "sketch": "tilt_profile",
        "angle": 360.0,
        "mode": "add",
        "direction": "positive",
        "axis": {"kind": "datum_axis_feature", "label": "tilt_axis"},
    },
]


def relation_problems(relation: dict, expectations: dict) -> list:
    """Recompute the relation from the reported vectors, then check it.

    The reported distance and angles must follow from the reported axis and
    plane vectors, so a stub or a request echo cannot pass. A non-coplanar axis
    is not an error by itself, so the kernel's own accept/refuse is recorded and
    never asserted here.
    """
    if not relation:
        return ["the operation record carries no revolve_axis_plane_relation"]
    if relation.get("available") is not True:
        return [f"plane relation unavailable: {relation.get('reason')!r}"]
    axis_origin = relation.get("axis_origin_mm")
    axis_direction = relation.get("axis_direction")
    plane_origin = relation.get("plane_origin_mm")
    plane_normal = relation.get("plane_normal")
    if not all(
        isinstance(value, list) and len(value) == 3
        for value in (
            axis_origin,
            axis_direction,
            plane_origin,
            plane_normal,
        )
    ):
        return ["the relation does not report three-component vectors"]
    offset = [a - b for a, b in zip(axis_origin, plane_origin)]
    distance = abs(sum(component * normal for component, normal in zip(offset, plane_normal)))
    along_normal = abs(
        sum(direction * normal for direction, normal in zip(axis_direction, plane_normal))
    )
    angle = math.degrees(math.asin(min(1.0, along_normal)))
    problems = []
    if not close(relation.get("origin_distance_mm"), distance, 1e-9):
        problems.append(
            f"origin_distance_mm={relation.get('origin_distance_mm')!r} does not follow from the "
            f"reported vectors ({distance!r})"
        )
    if not close(relation.get("direction_angle_to_plane_deg"), angle, 1e-9):
        problems.append(
            f"direction_angle_to_plane_deg={relation.get('direction_angle_to_plane_deg')!r} does "
            f"not follow from the reported vectors ({angle!r})"
        )
    thresholds = relation.get("thresholds") if isinstance(relation.get("thresholds"), dict) else {}
    in_plane = distance <= float(thresholds.get("distance_mm", 1e-6)) and angle <= float(
        thresholds.get("angle_deg", 1e-3)
    )
    if relation.get("axis_lies_in_plane") is not in_plane:
        problems.append(
            f"axis_lies_in_plane={relation.get('axis_lies_in_plane')!r} contradicts "
            f"distance={distance!r} mm, angle={angle!r} deg and the published thresholds"
        )
    expected_distance = expectations.get("distance_mm")
    if expected_distance is not None and not close(
        relation.get("origin_distance_mm"),
        expected_distance,
        expectations.get("distance_tolerance_mm", 1e-9),
    ):
        problems.append(
            f"origin_distance_mm={relation.get('origin_distance_mm')!r}; expected "
            f"{expected_distance!r} mm"
        )
    expected_angle = expectations.get("angle_deg")
    if expected_angle is not None and not close(
        relation.get("direction_angle_to_plane_deg"),
        expected_angle,
        expectations.get("angle_tolerance_deg", 1e-9),
    ):
        problems.append(
            f"direction_angle_to_plane_deg={relation.get('direction_angle_to_plane_deg')!r}; "
            f"expected {expected_angle!r} deg"
        )
    angle_range = expectations.get("angle_range")
    if angle_range and not angle_range[0] <= angle <= angle_range[1]:
        problems.append(f"the axis is {angle!r} deg out of the plane; expected {angle_range}")
    return problems


async def run_axis_relation(runner: LiveRunner, case: str, plan: list, expectations: dict) -> dict:
    name = unique_name(f"t4_{case}")
    created = await runner.submit(
        f"{case}:create",
        "creo_execute_plan",
        {"model_name": name, "model_type": "part", "operations": plan},
    )
    terminal = await runner.wait_job(created["job_id"], budget=HANG_BUDGET_SECONDS)
    snapshot = await runner.snapshot(created["model_id"])
    relation = plane_relation_block(terminal)
    entry = {
        "case": case,
        "model_name": name,
        "model_id": created["model_id"],
        "job_id": created["job_id"],
        "job_status": terminal.get("status"),
        "volume_mm3": volume_of(snapshot),
        "plane_relation": relation or None,
        "expectations": expectations,
        "failure": None if terminal.get("status") == "succeeded" else failure_text(terminal),
    }
    problems = relation_problems(relation, expectations)
    if terminal.get("status") != "succeeded" and not entry["failure"]:
        problems.append("failed without any message")
    entry["problems"] = problems
    entry["passed"] = not problems
    return runner.case(entry)


async def run_two_edges(runner: LiveRunner) -> dict:
    """Two R20 bosses: each round must land on its own boss.

    Phase 1 builds the plate and both bosses and reads the measured circles;
    phase 2 rounds one rim per boss. The selector carries a ``point_mm`` taken
    from the measured arc because a boss rim is reported as several arcs of the
    same circle - centre + radius alone can never be unique.
    """
    name = unique_name("t4_two_edges")
    created = await runner.submit(
        "two_equal_radius_edges:create",
        "creo_execute_plan",
        {"model_name": name, "model_type": "part", "operations": TWO_EDGE_BASE_PLAN},
    )
    base = await runner.wait_job(created["job_id"], budget=HANG_BUDGET_SECONDS)
    snapshot = await runner.snapshot(created["model_id"])
    groups = circular_groups(runner.inspection(snapshot).get("edges"))
    top_z = PLATE["z"] + BOSS_HEIGHT
    top_rims = [
        group
        for group in groups
        if abs(group["radius"] - BOSS_RADIUS) <= 0.001 and abs(group["center"][2] - top_z) <= 0.001
    ]
    left = next((group for group in top_rims if group["center"][0] < 0), None)
    right = next((group for group in top_rims if group["center"][0] > 0), None)
    entry = {
        "case": "two_equal_radius_edges",
        "model_name": name,
        "model_id": created["model_id"],
        "base_job_id": created["job_id"],
        "base_status": base.get("status"),
        "volume_mm3": volume_of(snapshot),
        "base_volume_mm3": PLATE_VOLUME,
        "top_rims": [
            {
                "center_mm": group["center"],
                "radius_mm": group["radius"],
                "edge_ids": [edge["id"] for edge in group["edges"]],
            }
            for group in top_rims
        ],
        "left_rim": None if left is None else [edge["id"] for edge in left["edges"]],
        "right_rim": None if right is None else [edge["id"] for edge in right["edges"]],
        "round_entries": [],
        "failure": None,
    }
    problems = []
    if base.get("status") != "succeeded":
        problems.append(f"the base plate with two bosses did not build: {base.get('status')!r}")
    if left is None or right is None:
        problems.append(
            "the inspection did not report one R20 top rim per boss, so the two equal-radius "
            "circles cannot be told apart by centre"
        )
    if problems:
        entry["problems"] = problems
        entry["passed"] = False
        return runner.case(entry)

    revision = revision_of(base, snapshot)
    if not isinstance(revision, int):
        entry["problems"] = ["no revision was reported, so the edit cannot quote expected_revision"]
        entry["passed"] = False
        return runner.case(entry)

    selectors = {
        "left": rim_selector(left["center"], arc_point(left["edges"][0]["arc"])),
        "right": rim_selector(right["center"], arc_point(right["edges"][0]["arc"])),
    }
    entry["selectors"] = selectors
    entry["expected_revision_sent"] = revision
    response = await runner.submit(
        "two_equal_radius_edges:rounds",
        "creo_execute_plan",
        {
            "model_id": created["model_id"],
            "expected_revision": revision,
            "operations": rounds_plan(selectors),
        },
    )
    terminal = await runner.wait_job(response["job_id"], budget=HANG_BUDGET_SECONDS)
    after = await runner.snapshot(created["model_id"])
    entry.update(
        {
            "round_job_id": response["job_id"],
            "round_job_status": terminal.get("status"),
            "saved_reload": saved_reload(terminal),
            "volume_after_mm3": volume_of(after),
            "round_entries": [
                {key: item.get(key) for key in ("label", "execution_status", "effect_status")}
                for item in operation_entries(terminal)
            ],
            "failure": None if terminal.get("status") == "succeeded" else failure_text(terminal),
        }
    )
    if terminal.get("status") != "succeeded":
        problems.append(
            f"the two point-anchored rounds did not succeed: {terminal.get('status')!r}"
        )
    elif entry["saved_reload"] is not True:
        problems.append("the rounds succeeded without saved_file_reloaded_and_verified")
    if entry["volume_after_mm3"] is None or entry["volume_mm3"] is None:
        problems.append("volume not measurable")
    elif not entry["volume_after_mm3"] < entry["volume_mm3"]:
        # A convex round removes material on both bosses.
        problems.append(
            f"volume {entry['volume_after_mm3']!r} did not drop below the unrounded "
            f"{entry['volume_mm3']!r}"
        )
    entry["problems"] = problems
    entry["passed"] = not problems
    return runner.case(entry)


async def main_live(output: Path, run_id: str) -> int:
    require_manual_start(ROOT / "config.json")
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT)
    async with Client(params, read_timeout_seconds=240) as client:
        runner = LiveRunner(
            client,
            output,
            "DEV-093 / 0.27.0 feedback task 4",
            "off-plane revolve axis and two equal-radius circular edges",
            run_id,
        )
        try:
            await runner.start()
            runner.report["hang_budget_seconds"] = HANG_BUDGET_SECONDS
            await run_off_plane(runner)
            await run_two_edges(runner)
            await run_axis_relation(
                runner,
                "axis_micro_offset",
                MICRO_OFFSET_PLAN,
                {
                    "distance_mm": MICRO_OFFSET_MM,
                    "distance_tolerance_mm": 1e-6,
                    "angle_deg": 0.0,
                    "angle_tolerance_deg": 1e-6,
                },
            )
            await run_axis_relation(
                runner,
                "axis_tilted",
                TILTED_AXIS_PLAN,
                {"distance_mm": 0.0, "distance_tolerance_mm": 1e-6, "angle_range": [1.0, 89.0]},
            )
        except BaseException as error:
            runner.report["stopped"] = f"{type(error).__name__}: {error}"
            runner.finish()
            raise
    summary = runner.finish()
    print(json.dumps(summary, ensure_ascii=False))
    rows = [
        {key: case.get(key) for key in ("case", "job_status", "volume_mm3", "problems", "passed")}
        for case in runner.report["cases"]
    ]
    print(json.dumps({"passed": runner.report["passed"], "cases": rows}, ensure_ascii=False))
    return 0 if runner.report["passed"] else 1


def contract() -> dict:
    return {
        "axis_off_plane": {
            "fixture": "rectangle on XY offset 50 mm, revolved about the built-in X axis at z=0",
            "axis_plane_distance_mm": 50.0,
            "expectation": (
                "either the kernel refuses and the failure names the axis/plane relationship, "
                "or a revolve_axis block explains what the kernel used; a bare failure with no "
                "diagnosis is the gap this case records"
            ),
        },
        "two_equal_radius_edges": {
            "fixture": "plate plus two R20 bosses; each top rim shares R20 with the other boss",
            "expectation": (
                "centre + radius + a point taken from the measured arc must resolve each boss; "
                "centre + radius alone cannot be unique because a rim is several arcs of one "
                "circle (FEAT-068)"
            ),
        },
        "axis_micro_offset": {
            "fixture": f"datum plane z={MICRO_OFFSET_MM} mm, axis at its crossing with x=0",
            "expectation": (
                "the relation reports the 0.00039 mm offset from the measured axis/plane vectors "
                "and axis_lies_in_plane=false; the kernel's own accept or refuse is recorded, not "
                "asserted, because a non-coplanar axis is not an error by itself"
            ),
        },
        "axis_tilted": {
            "fixture": "datum plane through three datum points, axis at its crossing with x=0",
            "expectation": (
                "the reported distance and angle follow from the reported vectors and the axis "
                "is measured as out of the plane; the angle value is recorded, not pinned to the "
                "nominal tilt, because the crossing line's inclination is not the plane's tilt"
            ),
        },
    }


def provenance() -> dict:
    from version import VERSION

    return {
        "version": VERSION,
        "environment": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "auto_start_creo": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-session-usable", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    run_id = f"{time.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
    output = args.output or ROOT / "build" / "feedback0270_task4" / run_id / "report.json"
    if output.exists():
        raise SystemExit(f"refusing to overwrite {output}")
    if args.live:
        if not args.confirm_session_usable:
            print("live runs require --confirm-session-usable", file=sys.stderr)
            return 2
        return asyncio.run(main_live(output, run_id))
    report = {
        "task": "DEV-093 / 0.27.0 feedback task 4",
        "mode": "offline",
        "native_acceptance": "not_run",
        "contract": contract(),
        "plans": {
            "axis_off_plane": OFF_PLANE_PLAN,
            "axis_micro_offset": MICRO_OFFSET_PLAN,
            "axis_tilted": TILTED_AXIS_PLAN,
            "two_equal_radius_edges_base": TWO_EDGE_BASE_PLAN,
            "two_equal_radius_edges_rounds": rounds_plan(
                {
                    "left": rim_selector([-BOSS_X, 0.0, PLATE["z"] + BOSS_HEIGHT], [0.0, 0.0, 0.0]),
                    "right": rim_selector([BOSS_X, 0.0, PLATE["z"] + BOSS_HEIGHT], [0.0, 0.0, 0.0]),
                }
            ),
        },
        "expected_base_volume_mm3": PLATE_VOLUME,
        "provenance": provenance(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_name("report.sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "contract": report["contract"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
