"""BUG-157 live acceptance: an assembly killed mid-job is recoverable.

The fixture saves a two-part assembly, then submits one long plan made of
assemble_component operations. Once the job is running, ``creo_cancel_job``
kills the runner after its worker started, which is the recorded
``unknown_outcome`` state that used to leave an assembly with no action at all.

The run then asserts, from the MCP responses only:

* the cancelled job ends ``unknown_outcome`` and keeps the model reservation;
* ``creo_reconcile_model`` inspect offers ``restore_baseline`` (no "assembly
  reconciliation is not supported" verdict) and publishes the widened recovery
  phase budget;
* apply restore_baseline succeeds with ``verification="identity"``,
  ``full_inspection_verified=false`` and ``saved_file_reloaded_and_verified``;
* the model returns to ready at the baseline revision, the saved file bytes are
  unchanged, and the assembly is usable again.

Nothing is retried or resubmitted; a refusal is recorded and stops the run.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import sys
import time
import uuid
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from creo_mechdog.paths import SOURCE_PATHS  # noqa: E402
from tools.sheetmetal_live import LiveRunner, require_manual_start  # noqa: E402

ROOT = SOURCE_PATHS.resource_root
PART_VOLUME_MM3 = 10.0 * 10.0 * 5.0
LONG_JOB_OPERATIONS = 60
VOLUME_TOLERANCE = 0.02


def part_plan() -> list:
    return [
        {
            "op": "sketch",
            "label": "profile",
            "plane": "XY",
            "entities": [
                {"type": "rectangle", "name": "body", "min": [0.0, 0.0], "max": [10.0, 10.0]}
            ],
        },
        {"op": "extrude", "label": "solid", "sketch": "profile", "depth": 5.0},
    ]


def long_plan(source_model_id: str) -> list:
    return [
        {
            "op": "assemble_component",
            "label": f"c{index:02d}",
            "source_model_id": source_model_id,
            "translation": [float(index) * 20.0, 0.0, 0.0],
        }
        for index in range(LONG_JOB_OPERATIONS)
    ]


def file_sha256(path: str | None) -> str | None:
    if not path:
        return None
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


async def job(runner: LiveRunner, key: str, tool: str, arguments: dict) -> tuple[dict, dict]:
    receipt = await runner.submit(key, tool, arguments)
    terminal = await runner.wait_job(receipt["job_id"], budget=600.0)
    return receipt, terminal


async def wait_status(
    runner: LiveRunner, job_id: str, statuses: tuple[str, ...], budget: float
) -> dict:
    """Poll a job up to one of the given statuses; keep the last view as evidence."""
    deadline = time.monotonic() + budget
    view: dict = {}
    while time.monotonic() < deadline:
        view = await runner.call("creo_get_job", {"job_id": job_id})
        if view.get("status") in statuses:
            return view
        await asyncio.sleep(1.0)
    return view


async def main_live(output: Path, run_id: str) -> int:
    require_manual_start(ROOT / "config.json")
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT)
    async with Client(params, read_timeout_seconds=300) as client:
        runner = LiveRunner(
            client,
            output,
            "BUG-157 assembly unknown_outcome recovery",
            "kill a running assembly job, then restore its verified baseline by identity",
            run_id,
        )
        try:
            await runner.start()
            runner.report["environment_detail"] = await runner.call("creo_check_environment", {})

            _, part = await job(runner, "part", "creo_execute_plan", {"operations": part_plan()})
            _, assembly_new = await job(runner, "assembly_new", "creo_new_assembly", {})
            assembly_id = assembly_new["model_id"]
            _, assembled = await job(
                runner,
                "assemble",
                "creo_assemble_component",
                {
                    "model_id": assembly_id,
                    "expected_revision": assembly_new["revision"],
                    "label": "p1",
                    "source_model_id": part["model_id"],
                },
            )
            if assembled.get("status") != "succeeded":
                runner.report["stopped"] = "the baseline assembly did not build"
                runner.finish()
                print(json.dumps({"report": str(output), "passed": False}, ensure_ascii=False))
                return 1

            baseline = await runner.call("creo_inspect_model", {"model_id": assembly_id})
            baseline_revision = baseline.get("revision")
            baseline_sha = file_sha256(baseline.get("part_file"))
            runner.case(
                {
                    "case": "baseline",
                    "model_id": assembly_id,
                    "revision": baseline_revision,
                    "part_file": baseline.get("part_file"),
                    "part_sha256_registry": baseline.get("part_sha256"),
                    "part_sha256_disk": baseline_sha,
                    "volume_mm3": (baseline.get("inspection") or {}).get("volume_mm3"),
                    "passed": baseline_sha is not None
                    and isinstance(baseline.get("revision"), int),
                }
            )

            # One long job, then kill it after the worker started.
            receipt = await runner.submit(
                "long_job",
                "creo_execute_plan",
                {
                    "model_id": assembly_id,
                    "operations": long_plan(part["model_id"]),
                    "expected_revision": baseline_revision,
                },
            )
            job_id = receipt["job_id"]
            running = None
            deadline = time.monotonic() + 180.0
            while time.monotonic() < deadline:
                view = await runner.call("creo_get_job", {"job_id": job_id})
                if view.get("status") not in ("queued", "running"):
                    running = view
                    break
                if view.get("worker_started") is True:
                    running = view
                    break
                await asyncio.sleep(0.5)
            cancel = None
            if running is not None and running.get("status") in ("queued", "running"):
                cancel = await runner.call("creo_cancel_job", {"job_id": job_id})
                cancelled = await wait_status(
                    runner,
                    job_id,
                    ("unknown_outcome", "failed", "succeeded", "cancelled", "aborted"),
                    budget=180.0,
                )
            else:
                cancelled = running or {}
            runner.case(
                {
                    "case": "cancel_window",
                    "job_id": job_id,
                    "running_view": running,
                    "cancel": cancel,
                    "terminal_status": cancelled.get("status"),
                    "passed": cancelled.get("status") == "unknown_outcome",
                }
            )
            if cancelled.get("status") != "unknown_outcome":
                runner.report["stopped"] = (
                    "the long job finished before cancellation; unknown_outcome was not constructed"
                )
                runner.finish()
                print(json.dumps({"report": str(output), "passed": False}, ensure_ascii=False))
                return 1

            uncertain = await runner.call("creo_inspect_model", {"model_id": assembly_id})
            inspect = await runner.call("creo_reconcile_model", {"model_id": assembly_id})
            restore = (inspect.get("actions") or {}).get("restore_baseline") or {}
            problems = []
            if uncertain.get("status") != "unknown_outcome":
                problems.append(f"model status after cancel: {uncertain.get('status')!r}")
            if not restore.get("available"):
                problems.append(f"restore_baseline unavailable: {restore.get('reason')!r}")
            if "not supported" in str(restore.get("reason") or "").lower():
                problems.append(
                    "restore_baseline still reports assembly reconciliation unsupported"
                )
            budgets = inspect.get("budgets") or {}
            phase = budgets.get("native_phase_seconds")
            if not isinstance(phase, int) or phase < 30:
                problems.append(f"inspect native_phase_seconds={phase!r}")
            if budgets.get("outer_seconds") != max(115, (phase or 0) + 30):
                problems.append(f"inspect outer_seconds={budgets.get('outer_seconds')!r}")
            runner.case(
                {
                    "case": "reconcile_inspect",
                    "model_status": uncertain.get("status"),
                    "pending_job": inspect.get("pending_job"),
                    "restore_baseline": restore,
                    "budgets": budgets,
                    "problems": problems,
                    "passed": not problems,
                }
            )
            if problems:
                runner.report["stopped"] = "reconcile inspect did not offer restore_baseline"
                runner.finish()
                print(json.dumps({"report": str(output), "passed": False}, ensure_ascii=False))
                return 1

            applied = await runner.call(
                "creo_reconcile_model",
                {
                    "model_id": assembly_id,
                    "mode": "apply",
                    "action": "restore_baseline",
                    "expected_revision": inspect.get("revision"),
                    "expected_pending_job_id": inspect.get("pending_job"),
                    "evidence_token": inspect.get("evidence_token"),
                    "idempotency_key": f"bug157-{uuid.uuid4().hex[:12]}",
                },
            )
            recovery_job = applied.get("job_id")
            recovered = await runner.wait_job(recovery_job, budget=600.0)
            result = recovered.get("result") or {}
            recovery_problems = []
            if recovered.get("status") != "succeeded":
                recovery_problems.append(f"recovery job {recovered.get('status')!r}")
            if result.get("verification") != "identity":
                recovery_problems.append(f"verification={result.get('verification')!r}")
            if result.get("full_inspection_verified") is not False:
                recovery_problems.append(
                    f"full_inspection_verified={result.get('full_inspection_verified')!r}"
                )
            if result.get("saved_file_reloaded_and_verified") is not True:
                recovery_problems.append("recovery did not save/reload")
            volume = result.get("volume_mm3")
            if (
                not isinstance(volume, (int, float))
                or abs(volume - PART_VOLUME_MM3) > PART_VOLUME_MM3 * VOLUME_TOLERANCE
            ):
                recovery_problems.append(f"recovery volume_mm3={volume!r}")
            runner.case(
                {
                    "case": "restore_baseline",
                    "job_id": recovery_job,
                    "job_status": recovered.get("status"),
                    "verification": result.get("verification"),
                    "feature_count": result.get("feature_count"),
                    "volume_mm3": volume,
                    "full_inspection_verified": result.get("full_inspection_verified"),
                    "saved_reload": result.get("saved_file_reloaded_and_verified"),
                    "message": recovered.get("message"),
                    "problems": recovery_problems,
                    "passed": not recovery_problems,
                }
            )

            after = await runner.call("creo_inspect_model", {"model_id": assembly_id})
            components = await runner.call("creo_list_components", {"model_id": assembly_id})
            after_sha = file_sha256(after.get("part_file"))
            disk_problems = []
            if after.get("status") != "ready":
                disk_problems.append(f"model status {after.get('status')!r}")
            if after.get("pending_job") is not None:
                disk_problems.append(f"pending_job {after.get('pending_job')!r}")
            if after.get("revision") != baseline_revision:
                disk_problems.append(
                    f"revision {after.get('revision')!r} != baseline {baseline_revision!r}"
                )
            if after_sha != baseline_sha:
                disk_problems.append("saved assembly bytes changed")
            if len(components.get("components") or []) != 1:
                disk_problems.append(
                    f"components after recovery: {len(components.get('components') or [])}"
                )
            runner.case(
                {
                    "case": "after_recovery",
                    "status": after.get("status"),
                    "revision": after.get("revision"),
                    "pending_job": after.get("pending_job"),
                    "part_file": after.get("part_file"),
                    "part_sha256_disk": after_sha,
                    "component_count": len(components.get("components") or []),
                    "problems": disk_problems,
                    "passed": not disk_problems,
                }
            )
        except BaseException as error:
            runner.report["stopped"] = f"{type(error).__name__}: {error}"
            runner.finish()
            raise
    summary = runner.finish()
    print(json.dumps(summary, ensure_ascii=False))
    rows = [
        {key: case.get(key) for key in ("case", "job_status", "problems", "passed")}
        for case in runner.report["cases"]
    ]
    print(json.dumps({"passed": runner.report["passed"], "cases": rows}, ensure_ascii=False))
    return 0 if runner.report["passed"] else 1


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
    output = args.output or ROOT / "build" / "feedback0355_recovery" / run_id / "report.json"
    if output.exists():
        raise SystemExit(f"refusing to overwrite {output}")
    if args.live:
        if not args.confirm_session_usable:
            print("live runs require --confirm-session-usable", file=sys.stderr)
            return 2
        return asyncio.run(main_live(output, run_id))
    report = {
        "task": "BUG-157 assembly unknown_outcome recovery",
        "mode": "offline",
        "native_acceptance": "not_run",
        "fixture": {
            "part": part_plan(),
            "long_job_operations": LONG_JOB_OPERATIONS,
            "expected_part_volume_mm3": PART_VOLUME_MM3,
        },
        "provenance": provenance(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(output), "mode": "offline"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
