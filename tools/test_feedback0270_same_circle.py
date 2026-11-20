"""0.27.0 feedback / FEAT-068: one rim reported as several arcs of the same circle.

A 360 degree revolve of a wall profile produces circular rims that Creo may
report as more than one arc. Because every arc of one rim shares the centre and
the radius, a ``geometry_selector`` edge filter on radius + centre matches all of
them, and a tighter ``tolerance_mm`` can never separate them.

The live run records three things the customer needs to be able to do:

``unselected``
    Submit a round on that circle with radius + centre only. The job must fail
    and the refusal must name the split rim, list the ids, and point at
    ``point_mm`` / ``{kind:'edge',id:N}`` instead of a smaller tolerance.

``point_anchor``
    The same circle with a ``point_mm`` on one arc span. This must resolve to
    exactly one arc and round it.

``edge_id``
    The same circle addressed by one arc id. This must also round it.

Only measured geometry decides the case: the split rim is discovered from the
saved inspection, never assumed from the plan. If the revolved rim comes back as
a single arc, the run records ``split_rim_found=false`` and the three cases stay
``not_verified`` - a fixture that cannot reproduce the input proves nothing about
the refusal text.
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

ROOT = SOURCE_PATHS.resource_root
HANG_BUDGET_SECONDS = 300.0
WALL = {"x0": 20.0, "x1": 30.0, "y0": 5.0, "y1": 10.0}
OUTER_RADIUS = WALL["y1"]
INNER_RADIUS = WALL["y0"]
TUBE_VOLUME_MM3 = math.pi * (OUTER_RADIUS**2 - INNER_RADIUS**2) * (WALL["x1"] - WALL["x0"])
ROUND_SIZE = 2.0
TOLERANCE_MM = 0.01
GROUP_EPSILON_MM = 0.001


def base_plan() -> list:
    return [
        {
            "op": "sketch",
            "label": "wall_profile",
            "plane": "XY",
            "entities": [
                {
                    "type": "rectangle",
                    "name": "wall",
                    "min": [WALL["x0"], WALL["y0"]],
                    "max": [WALL["x1"], WALL["y1"]],
                }
            ],
        },
        {
            "op": "datum_axis",
            "label": "x_axis",
            # X axis = intersection of the XZ (id 4) and XY (id 6) datum planes.
            "references": [{"kind": "plane", "id": 4}, {"kind": "plane", "id": 6}],
        },
        {
            "op": "revolve",
            "label": "tube",
            "sketch": "wall_profile",
            "angle": 360.0,
            "mode": "add",
            "direction": "positive",
            "axis": {"kind": "datum_axis_feature", "label": "x_axis"},
        },
    ]


CYLINDER = {"x0": 0.0, "x1": 10.0, "radius": OUTER_RADIUS}
CYLINDER_VOLUME_MM3 = math.pi * CYLINDER["radius"] ** 2 * (CYLINDER["x1"] - CYLINDER["x0"])
WIDE_TOLERANCE_MM = 20.0


def cylinder_plan() -> list:
    """A solid cylinder: two rims of the same radius at different centres.

    Both rims have radius 10 and are 10 mm apart, so a wide ``tolerance_mm``
    matches arcs of two different circles while a tight one matches only the
    arcs of a single circle. That contrast is what tells the same-circle refusal
    from the generic one.
    """
    return [
        {
            "op": "sketch",
            "label": "solid_profile",
            "plane": "XY",
            "entities": [
                {
                    "type": "rectangle",
                    "name": "solid",
                    "min": [CYLINDER["x0"], 0.0],
                    "max": [CYLINDER["x1"], CYLINDER["radius"]],
                }
            ],
        },
        {
            "op": "datum_axis",
            "label": "x_axis",
            "references": [{"kind": "plane", "id": 4}, {"kind": "plane", "id": 6}],
        },
        {
            "op": "revolve",
            "label": "cylinder",
            "sketch": "solid_profile",
            "angle": 360.0,
            "mode": "add",
            "direction": "positive",
            "axis": {"kind": "datum_axis_feature", "label": "x_axis"},
        },
    ]


def round_plan(selector: dict) -> list:
    return [
        {
            "op": "round",
            "label": "round_rim",
            "size": ROUND_SIZE,
            "references": [{"edge": selector}],
        }
    ]


def circular_selector(center, point=None) -> dict:
    selector = {
        "kind": "geometry_selector",
        "target": "edge",
        "radius_mm": OUTER_RADIUS,
        "center_mm": list(center),
        "tolerance_mm": TOLERANCE_MM,
    }
    if point is not None:
        selector["point_mm"] = list(point)
    return selector


def unit(vector: list) -> list:
    length = math.sqrt(sum(component * component for component in vector))
    if length <= 1e-12:
        return [0.0, 0.0, 0.0]
    return [component / length for component in vector]


def arc_point(arc: dict, fraction: float = 0.5) -> list:
    """A point on the measured arc, using the arc frame the selector reads."""
    origin = arc["origin"]
    radius = arc["radius"]
    v1 = unit(arc["v1"])
    v2 = unit(arc["v2"])
    start = arc["start_angle"]
    span = arc["end_angle"] - start
    if span < 0.0:
        span += 2.0 * math.pi
    angle = start + span * fraction
    return [
        origin[index] + radius * (math.cos(angle) * v1[index] + math.sin(angle) * v2[index])
        for index in range(3)
    ]


def circular_groups(edges: list) -> list:
    """Group measured circular edges by the circle they actually lie on."""
    groups = []
    for edge in edges if isinstance(edges, list) else []:
        arc = edge.get("arc") if isinstance(edge, dict) else None
        if not isinstance(arc, dict):
            continue
        origin = [float(value) for value in arc["origin"]]
        radius = float(arc["radius"])
        for group in groups:
            if (
                abs(group["radius"] - radius) <= GROUP_EPSILON_MM
                and max(abs(a - b) for a, b in zip(group["center"], origin)) <= GROUP_EPSILON_MM
            ):
                group["edges"].append({"id": edge.get("id"), "arc": arc})
                break
        else:
            groups.append(
                {
                    "center": origin,
                    "radius": radius,
                    "edges": [{"id": edge.get("id"), "arc": arc}],
                }
            )
    return groups


def pick_split_group(groups: list) -> dict | None:
    """The outer rim, when Creo reported it as several arcs."""
    candidates = [
        group
        for group in groups
        if len(group["edges"]) > 1 and abs(group["radius"] - OUTER_RADIUS) <= GROUP_EPSILON_MM
    ]
    if not candidates:
        return None
    return max(
        candidates, key=lambda group: max(edge["arc"]["origin"][0] for edge in group["edges"])
    )


def message_text(terminal: dict) -> str:
    evidence = failure_text(terminal)
    parts = [str(evidence.get("message") or "")]
    for operation in evidence.get("operations") or []:
        for key in ("error", "message"):
            value = operation.get(key) if isinstance(operation, dict) else None
            if value:
                parts.append(str(value))
    parts.append(str(evidence.get("native_log_tail") or ""))
    return "\n".join(part for part in parts if part)


def saved_reload(terminal: dict) -> bool | None:
    result = terminal.get("result") if isinstance(terminal.get("result"), dict) else {}
    value = result.get("saved_file_reloaded_and_verified")
    return value if isinstance(value, bool) else None


def revision_of(terminal: dict, snapshot: dict) -> int | None:
    """The revision a follow-up submission must quote.

    An existing model is only editable with ``expected_revision``; a missing
    value therefore stops the run instead of quietly weakening the guard.
    """
    inspection = snapshot.get("inspection") if isinstance(snapshot.get("inspection"), dict) else {}
    for value in (
        terminal.get("revision"),
        snapshot.get("revision"),
        inspection.get("revision"),
    ):
        if isinstance(value, int):
            return value
    return None


async def create_base(runner: LiveRunner, key: str, plan: list | None = None) -> dict:
    name = unique_name("sc_rim")
    created = await runner.submit(
        f"{key}:base",
        "creo_execute_plan",
        {"model_name": name, "model_type": "part", "operations": plan or base_plan()},
    )
    terminal = await runner.wait_job(created["job_id"], budget=HANG_BUDGET_SECONDS)
    snapshot = await runner.snapshot(created["model_id"])
    inspection = runner.inspection(snapshot)
    groups = circular_groups(inspection.get("edges"))
    revision = revision_of(terminal, snapshot)
    if not isinstance(revision, int):
        raise RuntimeError(
            f"no revision for model {created['model_id']}; an existing model must be edited "
            "with expected_revision, so this run refuses to submit the round cases"
        )
    return {
        "model_name": name,
        "model_id": created["model_id"],
        "base_job_id": created["job_id"],
        "base_status": terminal.get("status"),
        "base_message": terminal.get("message"),
        "base_saved_reload": saved_reload(terminal),
        "revision": revision,
        "volume_mm3": runner.volume(snapshot),
        "groups": groups,
        "split_group": pick_split_group(groups),
    }


async def round_on(runner: LiveRunner, key: str, base: dict, selector: dict) -> dict:
    expected_revision = base["revision"]
    response = await runner.submit(
        f"{key}:round",
        "creo_execute_plan",
        {
            "model_id": base["model_id"],
            "expected_revision": expected_revision,
            "operations": round_plan(selector),
        },
    )
    terminal = await runner.wait_job(response["job_id"], budget=HANG_BUDGET_SECONDS)
    snapshot = await runner.snapshot(base["model_id"])
    revision = revision_of(terminal, snapshot)
    if isinstance(revision, int):
        # A failed job rolls back to the saved checkpoint; keep the next
        # submission aligned with whatever the terminal record reports.
        base["revision"] = revision
    return {
        "job_id": response["job_id"],
        "job_status": terminal.get("status"),
        "expected_revision_sent": expected_revision,
        "message": message_text(terminal),
        "saved_reload": saved_reload(terminal),
        "revision": revision,
        "volume_mm3": runner.volume(snapshot),
    }


def base_evidence(base: dict) -> dict:
    group = base.get("split_group") or {}
    return {
        "model_name": base["model_name"],
        "model_id": base["model_id"],
        "base_job_id": base["base_job_id"],
        "base_status": base["base_status"],
        "base_message": base["base_message"],
        "base_saved_reload": base["base_saved_reload"],
        "base_revision": base.get("revision"),
        "base_volume_mm3": base["volume_mm3"],
        "expected_tube_volume_mm3": TUBE_VOLUME_MM3,
        "circular_groups": [
            {
                "center_mm": group_record["center"],
                "radius_mm": group_record["radius"],
                "edge_ids": [edge["id"] for edge in group_record["edges"]],
            }
            for group_record in base["groups"]
        ],
        "split_rim_center_mm": group.get("center"),
        "split_rim_radius_mm": group.get("radius"),
        "split_rim_edge_ids": [edge["id"] for edge in group.get("edges", [])],
    }


async def run_unselected(runner: LiveRunner, base: dict) -> dict:
    group = base["split_group"]
    outcome = await round_on(runner, "unselected", base, circular_selector(group["center"]))
    entry = {
        "case": "unselected",
        **base_evidence(base),
        "selector": circular_selector(group["center"]),
        **outcome,
    }
    text = entry["message"]
    problems = []
    if entry["job_status"] != "failed":
        problems.append(
            f"the radius+centre selector returned {entry['job_status']!r}; the split rim was "
            "expected to be refused as ambiguous"
        )
    if "arcs of one circle" not in text:
        problems.append("the refusal does not name the split rim")
    if "point_mm" not in text:
        problems.append("the refusal does not offer point_mm")
    if "{kind:'edge',id:N}" not in text:
        problems.append("the refusal does not offer a per-arc id")
    if "use a smaller tolerance_mm or an anchor" in text:
        problems.append("the refusal still recommends a smaller tolerance as the remedy")
    for edge_id in [edge["id"] for edge in group["edges"]]:
        if str(edge_id) not in text:
            problems.append(f"arc id {edge_id} is not listed in the refusal")
    if entry["saved_reload"] is True:
        problems.append("a failed selection reported a saved reload")
    entry["problems"] = problems
    entry["passed"] = not problems
    return runner.case(entry)


async def run_point_anchor(runner: LiveRunner, base: dict) -> dict:
    group = base["split_group"]
    arc = group["edges"][0]["arc"]
    point = arc_point(arc)
    selector = circular_selector(group["center"], point)
    outcome = await round_on(runner, "point_anchor", base, selector)
    entry = {"case": "point_anchor", **base_evidence(base), "selector": selector, **outcome}
    problems = []
    if entry["job_status"] != "succeeded":
        problems.append(f"point_mm did not resolve the split rim: {entry['job_status']!r}")
    elif entry["saved_reload"] is not True:
        problems.append("the round succeeded without saved_file_reloaded_and_verified")
    if entry["volume_mm3"] is None:
        problems.append("volume not measurable after the round")
    elif entry["volume_mm3"] >= base["volume_mm3"]:
        problems.append(
            f"volume {entry['volume_mm3']!r} did not drop below the unrounded "
            f"{base['volume_mm3']!r}"
        )
    entry["problems"] = problems
    entry["passed"] = not problems
    return runner.case(entry)


async def run_edge_id(runner: LiveRunner, base: dict) -> dict:
    group = base["split_group"]
    edge_id = group["edges"][-1]["id"]
    selector = {"kind": "edge", "id": edge_id}
    outcome = await round_on(runner, "edge_id", base, selector)
    entry = {
        "case": "edge_id",
        **base_evidence(base),
        "selector": selector,
        **outcome,
        "selected_edge_id": edge_id,
    }
    problems = []
    if entry["job_status"] != "succeeded":
        problems.append(f"the per-arc id {edge_id} did not round: {entry['job_status']!r}")
    elif entry["saved_reload"] is not True:
        problems.append("the round succeeded without saved_file_reloaded_and_verified")
    if entry["volume_mm3"] is None:
        problems.append("volume not measurable after the round")
    elif entry["volume_mm3"] >= base["volume_mm3"]:
        problems.append(
            f"volume {entry['volume_mm3']!r} did not drop below the unrounded "
            f"{base['volume_mm3']!r}"
        )
    entry["problems"] = problems
    entry["passed"] = not problems
    return runner.case(entry)


async def run_tolerance_contrast(runner: LiveRunner, base: dict) -> list:
    """Same radius, two centres: a wide tolerance must not be blamed on the rim.

    The cylinder rims sit at x=0 and x=10 with radius 10. A tolerance that
    reaches both circles matches arcs of two different circles, where shrinking
    the tolerance is still the right advice; narrowing it leaves the arcs of one
    circle, which must switch to the same-circle refusal.
    """
    rims = sorted(
        (
            group
            for group in base["groups"]
            if abs(group["radius"] - OUTER_RADIUS) <= GROUP_EPSILON_MM
        ),
        key=lambda group: group["center"][0],
    )
    if len(rims) < 2:
        return [
            not_verified(
                runner,
                "wide_tolerance",
                base,
                "the cylinder did not report two same-radius rims at different centres",
            )
        ]

    near_rim = rims[0]
    wide = {**circular_selector(near_rim["center"]), "tolerance_mm": WIDE_TOLERANCE_MM}
    wide_outcome = await round_on(runner, "wide_tolerance", base, wide)
    wide_entry = {
        "case": "wide_tolerance",
        **base_evidence(base),
        "selector": wide,
        "same_radius_rims": len(rims),
        "rim_centres_mm": [group["center"] for group in rims],
        **wide_outcome,
    }
    text = wide_entry["message"]
    problems = []
    if wide_entry["job_status"] != "failed":
        problems.append(
            f"the wide-tolerance selector returned {wide_entry['job_status']!r}; arcs of two "
            "different circles were expected to be refused as ambiguous"
        )
    if "arcs of one circle" in text:
        problems.append("two distinct circles were reported as arcs of one circle")
    if "use a smaller tolerance_mm" not in text:
        problems.append("the wide-tolerance refusal dropped the smaller-tolerance advice")
    if wide_entry["volume_mm3"] != base["volume_mm3"]:
        problems.append("the refused selection changed the model volume")
    wide_entry["problems"] = problems
    wide_entry["passed"] = not problems
    runner.case(wide_entry)

    narrow = circular_selector(near_rim["center"])
    narrow_outcome = await round_on(runner, "narrow_tolerance", base, narrow)
    narrow_entry = {
        "case": "narrow_tolerance",
        **base_evidence(base),
        "selector": narrow,
        **narrow_outcome,
    }
    narrow_text = narrow_entry["message"]
    narrow_problems = []
    if narrow_entry["job_status"] != "failed":
        narrow_problems.append(
            f"the tightened selector returned {narrow_entry['job_status']!r}; the remaining "
            "arcs of one circle were expected to be refused"
        )
    if "arcs of one circle" not in narrow_text:
        narrow_problems.append("tightening the tolerance did not switch to the same-circle refusal")
    if narrow_entry["volume_mm3"] != base["volume_mm3"]:
        narrow_problems.append("the refused selection changed the model volume")
    narrow_entry["problems"] = narrow_problems
    narrow_entry["passed"] = not narrow_problems
    runner.case(narrow_entry)
    return [wide_entry, narrow_entry]


def not_verified(runner: LiveRunner, case: str, base: dict, reason: str) -> dict:
    entry = {"case": case, **base_evidence(base), "problems": [reason], "passed": False}
    entry["verified"] = False
    return runner.case(entry)


async def main_live(output: Path, run_id: str) -> int:
    require_manual_start(ROOT / "config.json")
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT)
    async with Client(params, read_timeout_seconds=300) as client:
        runner = LiveRunner(
            client,
            output,
            "FEAT-068 / 0.27.0 feedback same-circle rim",
            "one rim reported as several arcs: refusal text and the two working remedies",
            run_id,
        )
        try:
            await runner.start()
            runner.report["hang_budget_seconds"] = HANG_BUDGET_SECONDS

            first = await create_base(runner, "first")
            base_problems = []
            if first["base_status"] != "succeeded":
                base_problems.append(f"the base tube did not build: {first['base_status']!r}")
            if first["base_saved_reload"] is not True:
                base_problems.append("the base tube was not saved and reloaded")
            volume = first["volume_mm3"]
            if volume is None:
                base_problems.append("the base tube volume is not measurable")
            elif abs(volume - TUBE_VOLUME_MM3) > TUBE_VOLUME_MM3 * 0.01:
                base_problems.append(
                    f"base volume {volume!r} does not match the analytic tube {TUBE_VOLUME_MM3!r}"
                )
            runner.case(
                {
                    "case": "base_split_rim",
                    **base_evidence(first),
                    "split_rim_found": first["split_group"] is not None,
                    "problems": base_problems,
                    "passed": not base_problems,
                    "verified": first["split_group"] is not None,
                }
            )
            if first["split_group"] is None:
                reason = (
                    "the revolved rim came back as a single arc, so the split-rim refusal "
                    "cannot be exercised with this fixture"
                )
                for case in ("unselected", "point_anchor", "edge_id"):
                    not_verified(runner, case, first, reason)
            else:
                await run_unselected(runner, first)
                await run_point_anchor(runner, first)
                second = await create_base(runner, "second")
                if second["split_group"] is None:
                    not_verified(
                        runner,
                        "edge_id",
                        second,
                        "the second base model did not report a split rim",
                    )
                else:
                    await run_edge_id(runner, second)

            third = await create_base(runner, "third", plan=cylinder_plan())
            cylinder_problems = []
            if third["base_status"] != "succeeded":
                cylinder_problems.append(f"the cylinder did not build: {third['base_status']!r}")
            cylinder_volume = third["volume_mm3"]
            if cylinder_volume is None:
                cylinder_problems.append("the cylinder volume is not measurable")
            elif abs(cylinder_volume - CYLINDER_VOLUME_MM3) > CYLINDER_VOLUME_MM3 * 0.01:
                cylinder_problems.append(
                    f"cylinder volume {cylinder_volume!r} does not match the analytic "
                    f"{CYLINDER_VOLUME_MM3!r}"
                )
            runner.case(
                {
                    "case": "base_cylinder",
                    **base_evidence(third),
                    "problems": cylinder_problems,
                    "passed": not cylinder_problems,
                }
            )
            if cylinder_problems:
                for case in ("wide_tolerance", "narrow_tolerance"):
                    not_verified(
                        runner,
                        case,
                        third,
                        "the cylinder base model is unusable, so the tolerance contrast "
                        "was not exercised",
                    )
            else:
                await run_tolerance_contrast(runner, third)
        except BaseException as error:
            runner.report["stopped"] = f"{type(error).__name__}: {error}"
            runner.finish()
            raise
    summary = runner.finish()
    print(json.dumps(summary, ensure_ascii=False))
    rows = [
        {
            key: case.get(key)
            for key in ("case", "job_status", "volume_mm3", "verified", "problems", "passed")
        }
        for case in runner.report["cases"]
    ]
    print(json.dumps({"passed": runner.report["passed"], "cases": rows}, ensure_ascii=False))
    return 0 if runner.report["passed"] else 1


def contract() -> dict:
    return {
        "fixture": {
            "plan": "rectangle x 20..30, y 5..10 on XY, revolved 360 deg about the X axis",
            "expected_volume_mm3": TUBE_VOLUME_MM3,
            "outer_rim_radius_mm": OUTER_RADIUS,
            "assumption": (
                "whether Creo reports the revolved rim as several arcs is read from the "
                "inspection, never assumed"
            ),
        },
        "unselected": {
            "expectation": (
                "failed; message names 'arcs of one circle', lists every arc id, offers point_mm "
                "and {kind:'edge',id:N}, and does not recommend a smaller tolerance_mm"
            )
        },
        "point_anchor": {
            "expectation": "succeeded on exactly one arc, volume drops, saved reload verified"
        },
        "edge_id": {"expectation": "succeeded by arc id, volume drops, saved reload verified"},
        "wide_tolerance": {
            "fixture": "solid cylinder x 0..10, r=10; rims at x=0 and x=10 share radius 10",
            "expectation": (
                "with tolerance 20 the selection reaches arcs of two different circles; the "
                "refusal must keep the smaller-tolerance advice and must not claim one circle"
            ),
        },
        "narrow_tolerance": {
            "expectation": (
                "with tolerance 0.01 only the x=0 rim matches; the refusal must switch to the "
                "same-circle wording and offer point_mm / per-arc id"
            )
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
    output = args.output or ROOT / "build" / "feedback0270_same_circle" / run_id / "report.json"
    if output.exists():
        raise SystemExit(f"refusing to overwrite {output}")
    if args.live:
        if not args.confirm_session_usable:
            print("live runs require --confirm-session-usable", file=sys.stderr)
            return 2
        return asyncio.run(main_live(output, run_id))
    report = {
        "task": "FEAT-068 / 0.27.0 feedback same-circle rim",
        "mode": "offline",
        "native_acceptance": "not_run",
        "contract": contract(),
        "plans": {
            "tube_base": base_plan(),
            "cylinder_base": cylinder_plan(),
            "round": round_plan(circular_selector([30.0, 0.0, 0.0])),
        },
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
