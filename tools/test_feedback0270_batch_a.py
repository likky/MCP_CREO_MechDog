"""0.27.0 feedback batch A, task 2: live arc-preservation fixtures.

Four sketch tiers whose volume is derived from the request geometry only, so a
lost arc, a swapped sweep or a coordinate rewrite shows up as a volume or a
create failure rather than as a plausible-looking solid:

* two semicircles forming one circle,
* four quarter arcs forming the same circle,
* eight 45-degree arcs forming the same circle,
* concentric semicircles with two chords (half annulus).

Every case is created, checked against ``require_solid``/``volume_mm3``,
inspected, saved and reloaded. ``--live --confirm-session-usable`` is required;
without it the script prints the contract and writes an offline report.
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
HANG_BUDGET_SECONDS = 240.0
OUTER_RADIUS = 20.0
INNER_RADIUS = 10.0
DEPTH = 5.0
CIRCLE_VOLUME = math.pi * OUTER_RADIUS**2 * DEPTH
HALF_ANNULUS_VOLUME = 0.5 * math.pi * (OUTER_RADIUS**2 - INNER_RADIUS**2) * DEPTH


def arc(name, start_angle, end_angle, radius=OUTER_RADIUS, direction=1):
    entity = {
        "type": "arc",
        "name": name,
        "center": [0.0, 0.0],
        "radius": radius,
        "start_angle": start_angle,
        "end_angle": end_angle,
    }
    if direction != 1:
        entity["dir"] = direction
    return entity


def chord(name, start, end):
    return {"type": "line", "name": name, "start": list(start), "end": list(end)}


def sketch(name, entities):
    return {"op": "sketch", "label": name, "plane": "XY", "entities": entities}


def extrude(name, sketch_label, depth=DEPTH):
    return {"op": "extrude", "label": name, "sketch": sketch_label, "depth": depth}


FIXTURES = {
    "arcs_two_semicircles": {
        "operations": [
            sketch(
                "two_semicircles",
                [arc("upper", 0.0, 180.0), arc("lower", 180.0, 360.0)],
            ),
            extrude("two_semicircles_extrude", "two_semicircles"),
        ],
        "volume_mm3": CIRCLE_VOLUME,
        "arc_count": 2,
    },
    "arcs_four_quarters": {
        "operations": [
            sketch(
                "four_quarters",
                [
                    arc("q1", 0.0, 90.0),
                    arc("q2", 90.0, 180.0),
                    arc("q3", 180.0, 270.0),
                    arc("q4", 270.0, 360.0),
                ],
            ),
            extrude("four_quarters_extrude", "four_quarters"),
        ],
        "volume_mm3": CIRCLE_VOLUME,
        "arc_count": 4,
    },
    "arcs_eight": {
        "operations": [
            sketch(
                "eight_arcs",
                [arc(f"e{index}", index * 45.0, (index + 1) * 45.0) for index in range(8)],
            ),
            extrude("eight_arcs_extrude", "eight_arcs"),
        ],
        "volume_mm3": CIRCLE_VOLUME,
        "arc_count": 8,
    },
    "arcs_concentric_with_chords": {
        "operations": [
            sketch(
                "half_annulus",
                [
                    arc("outer", 0.0, 180.0, OUTER_RADIUS),
                    chord("left_chord", (-OUTER_RADIUS, 0.0), (-INNER_RADIUS, 0.0)),
                    # The inner boundary runs from 180 deg back to 0 deg through
                    # the upper half (clockwise), so it subtracts the inner half
                    # disc instead of adding the lower one.
                    arc("inner", 180.0, 0.0, INNER_RADIUS, direction=-1),
                    chord("right_chord", (INNER_RADIUS, 0.0), (OUTER_RADIUS, 0.0)),
                ],
            ),
            extrude("half_annulus_extrude", "half_annulus"),
        ],
        "volume_mm3": HALF_ANNULUS_VOLUME,
        "arc_count": 2,
    },
}


def volume_of(snapshot: dict) -> float | None:
    inspection = snapshot.get("inspection") if isinstance(snapshot.get("inspection"), dict) else {}
    value = inspection.get("volume_mm3")
    return value if isinstance(value, (int, float)) else None


def reload_flag(terminal: dict) -> object:
    result = terminal.get("result") if isinstance(terminal, dict) else None
    block = result if isinstance(result, dict) else {}
    return block.get("saved_file_reloaded_and_verified")


def near(left: float | None, right: float | None, tolerance: float) -> bool:
    return left is not None and right is not None and abs(float(left) - float(right)) <= tolerance


async def run_case(runner: LiveRunner, case: str) -> dict:
    fixture = FIXTURES[case]
    name = unique_name(f"t2_{case}")
    created = await runner.submit(
        f"{case}:create",
        "creo_execute_plan",
        {
            "model_name": name,
            "model_type": "part",
            "operations": fixture["operations"],
            "assertions": {"volume_mm3": fixture["volume_mm3"], "require_solid": True},
        },
    )
    terminal = await runner.wait_job(created["job_id"], budget=HANG_BUDGET_SECONDS)
    snapshot = await runner.snapshot(created["model_id"])
    entry = {
        "case": case,
        "model_name": name,
        "model_id": created["model_id"],
        "job_id": created["job_id"],
        "job_status": terminal.get("status"),
        "expected_volume_mm3": fixture["volume_mm3"],
        "volume_mm3": volume_of(snapshot),
        "revision": snapshot.get("revision"),
        "arc_count": fixture["arc_count"],
    }
    problems = []
    if terminal.get("status") != "succeeded":
        entry["failure"] = failure_text(terminal)
        entry["problems"] = problems + [f"job {terminal.get('status')}"]
        entry["passed"] = False
        return runner.case(entry)
    if not near(entry["volume_mm3"], fixture["volume_mm3"], 1.0):
        problems.append(
            f"volume={entry['volume_mm3']!r} expected {fixture['volume_mm3']!r} "
            "(a lost or rewritten arc changes the section area)"
        )
    saved = await runner.submit(
        f"{case}:save",
        "creo_save_model",
        {"model_id": created["model_id"], "expected_revision": entry["revision"]},
    )
    save_terminal = await runner.wait_job(saved["job_id"], budget=HANG_BUDGET_SECONDS)
    post = await runner.snapshot(created["model_id"])
    entry["save_reload"] = {
        "job_id": save_terminal.get("job_id"),
        "status": save_terminal.get("status"),
        "saved_file_reloaded_and_verified": reload_flag(save_terminal),
        "post_reload_revision": post.get("revision"),
        "post_reload_volume_mm3": volume_of(post),
    }
    if save_terminal.get("status") != "succeeded":
        problems.append(f"save job {save_terminal.get('status')}")
    if reload_flag(save_terminal) is not True:
        problems.append("saved_file_reloaded_and_verified is not true")
    if not near(entry["save_reload"]["post_reload_volume_mm3"], fixture["volume_mm3"], 1.0):
        problems.append(f"post-reload volume {entry['save_reload']['post_reload_volume_mm3']!r}")
    entry["problems"] = problems
    entry["passed"] = not problems
    return runner.case(entry)


async def live(output: Path, run_id: str) -> int:
    require_manual_start(ROOT / "config.json")
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT)
    async with Client(params, read_timeout_seconds=240) as client:
        runner = LiveRunner(
            client,
            output,
            "DEV-093 / 0.27.0 feedback task 2",
            "arc preservation: two, four and eight arcs on one circle, plus a chorded half annulus",
            run_id,
        )
        try:
            await runner.start()
            runner.report["hang_budget_seconds"] = HANG_BUDGET_SECONDS
            for case in FIXTURES:
                await run_case(runner, case)
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
        "oracles_mm3": {"circle": CIRCLE_VOLUME, "half_annulus": HALF_ANNULUS_VOLUME},
        "rule": (
            "the volume comes from the requested section only; an arc that is dropped, "
            "swept the wrong way or rewritten to its chord changes the area, so a passing "
            "volume plus a verified save/reload is the acceptance signal"
        ),
        "arc_tiers": {
            "two_semicircles": "one circle from two 180 degree arcs",
            "four_quarters": "one circle from four 90 degree arcs",
            "eight": "one circle from eight 45 degree arcs",
            "concentric_with_chords": "half annulus: two concentric arcs plus two chords",
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
    output = args.output or ROOT / "build" / "feedback0270_batch_a" / run_id / "report.json"
    if output.exists():
        raise SystemExit(f"refusing to overwrite {output}")
    if args.live:
        if not args.confirm_session_usable:
            print("live runs require --confirm-session-usable", file=sys.stderr)
            return 2
        return asyncio.run(live(output, run_id))
    report = {
        "task": "DEV-093 / 0.27.0 feedback task 2",
        "mode": "offline",
        "native_acceptance": "not_run",
        "contract": contract(),
        "fixtures": FIXTURES,
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
