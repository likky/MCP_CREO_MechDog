"""BUG-191 live regression using temporary Creo parts and a native relation.

The relation reduces an existing block when the next extrude introduces its
depth dimension. The same plan without the relation produces ordinary growth.
Run with --baseline against an unguarded worker to reproduce the unsafe save.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bridge  # noqa: E402
import generic_bridge as general  # noqa: E402
from tools.test_feedback0358_pattern_scope import (  # noqa: E402
    git_commit_and_dirty,
    sha256_file,
    wait_job,
)


def sketch(label: str, x: int, size: int) -> dict:
    return {
        "op": "sketch",
        "label": label,
        "plane": "XY",
        "dimensioning": "coordinates",
        "entities": [
            {"type": "rectangle", "name": "outline", "min": [x, 0], "max": [x + size, size]}
        ],
    }


def extrusion(label: str, depth: int, *, new_body: bool = False) -> dict:
    return {
        "op": "extrude",
        "label": label,
        "sketch": label + "_sk",
        "depth": depth,
        "new_body": new_body,
    }


def depth_dimension(job: dict, label: str, depth: float) -> dict:
    native = job["native"]
    feature_id = native["aliases"][label]["feature_id"]
    feature = next(f for f in native["inspection"]["features"] if f["id"] == feature_id)
    matching = [d for d in feature["dimensions"] if math.isclose(d["value"], depth)]
    assert len(matching) == 1, (label, depth, matching)
    return matching[0]


def set_marker_depth(job: dict) -> dict:
    marker = depth_dimension(job, "mark", 3)
    return {"op": "set_dimensions", "values": [{"id": marker["id"], "value": 4}]}


def volume(job: dict) -> float:
    return job["native"]["inspection"]["volume_mm3"]


def run(output: Path, *, baseline: bool) -> None:
    suffix = uuid.uuid4().hex[:8]
    session = bridge.session_status(connect_timeout_seconds=15)
    assert session["connected"], session
    report = {
        "baseline": baseline,
        "source": git_commit_and_dirty(),
        "worker_sha256": sha256_file(ROOT / "build/creo_worker.exe"),
        "worker_source_digest": (ROOT / "build/source.sha256").read_text().strip(),
        "session": session,
        "jobs": {},
    }

    def job(
        key: str,
        ops: list[dict],
        previous: dict | None = None,
        *,
        readonly: bool = False,
        expected_status: str = "succeeded",
    ) -> dict:
        if previous is None:
            accepted = general.submit(ops, model_name=f"b191_{key}_{suffix}")
        else:
            accepted = general.submit(
                ops,
                model_id=previous["model_id"],
                expected_revision=None if readonly else previous["revision"],
                readonly=readonly,
            )
        job_id = accepted["job_id"]
        terminal = wait_job(job_id)
        model = general.model_info(accepted["model_id"])
        native = json.loads((ROOT / "jobs" / job_id / "native_result.json").read_text("utf-8"))
        compact = bridge.get_job(job_id, detail="compact")
        full = bridge.get_job(job_id, detail="full", section="operations_result")
        row = {
            "job_id": job_id,
            "model_id": accepted["model_id"],
            "status": terminal["status"],
            "message": terminal["message"],
            "revision": model["revision"],
            "operations": ops,
            "part_file": model.get("part_file"),
            "native": native,
            "compact_operations": compact.get("result", {}).get("operations"),
            "full_operations": full["data"]["operations_result"],
        }
        report["jobs"][key] = row
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(
            key,
            job_id,
            row["status"],
            (native.get("inspection") or {}).get("volume_mm3"),
            row["message"],
            flush=True,
        )
        assert row["status"] == expected_status, row["message"]
        if expected_status == "succeeded" and not readonly:
            assert native["saved_file_reloaded_and_verified"] is True
        return row

    def with_relation(model: dict, shrink_to: float, trigger_symbol: str) -> dict:
        base_symbol = depth_dimension(model, "base", 20)["symbol"]
        relation = {
            "op": "set_relations",
            "lines": [
                f'IF EXISTS("{trigger_symbol}")',
                f"{base_symbol} = {shrink_to}",
                "ELSE",
                f"{base_symbol} = 20",
                "ENDIF",
            ],
        }
        # The public relation schema only accepts arithmetic assignments. Let
        # Creo author the conditional fixture through the native setter. Every
        # measured and rejected operation uses standard admission.
        with patch.object(general, "validate_operations", return_value=[relation]):
            return job("relation" if shrink_to == 2 else "balanced_relation", [relation], model)

    model_ops = [
        sketch("base_sk", 0, 10),
        extrusion("base", 20),
        sketch("mark_sk", 22, 1),
        extrusion("mark", 3, new_body=True),
        sketch("small_sk", 32, 1),
    ]
    add = extrusion("small", 2, new_body=True)
    control = job("control", model_ops)
    control_edit = job("control_edit", [set_marker_depth(control), add], control)
    assert math.isclose(volume(control_edit), 2006.0)
    trigger_symbol = depth_dimension(control_edit, "small", 2)["symbol"]

    base = job("base", model_ops)
    saved = with_relation(base, 2, trigger_symbol)
    assert math.isclose(volume(saved), 2003.0)
    checkpoint = Path(saved["part_file"])
    digest = sha256_file(checkpoint)
    report["checkpoint_sha256"] = digest
    event = job(
        "event",
        [set_marker_depth(base), add],
        saved,
        expected_status="succeeded" if baseline else "failed",
    )
    if baseline:
        assert math.isclose(volume(event), 206.0)
        assert event["revision"] == saved["revision"] + 1
        return

    assert event["native"]["rollback_succeeded"] is True
    assert event["native"]["inspection_source"] == "rollback_verified"
    assert event["revision"] == saved["revision"]
    assert Path(event["part_file"]) == checkpoint
    assert digest and sha256_file(checkpoint) == digest
    assert [
        (op["execution_status"], op["effect_status"]) for op in event["native"]["operations"]
    ] == [("succeeded", "rolled_back"), ("failed", "rolled_back")]
    for operations in (event["full_operations"], event["compact_operations"]):
        failed = operations[1]
        assert failed["add_volume_check"]["reason"] == "add_reduced_volume"
        assert math.isclose(failed["volume_before_mm3"], 2004.0)
        assert math.isclose(failed["volume_after_mm3"], 206.0)
        assert math.isclose(failed["material_delta_mm3"], -1798.0)

    live = job("refresh", [], event, readonly=True)
    assert live["revision"] == saved["revision"]
    assert math.isclose(volume(live), volume(saved))
    for key in ("bodies", "features", "surfaces"):
        assert live["native"]["inspection"][key] == saved["native"]["inspection"][key], key
    depth_dimension(live, "base", 20)
    depth_dimension(live, "mark", 3)

    balanced = with_relation(live, 19.98, trigger_symbol)
    zero_delta = job("zero_delta", [add], balanced)
    assert math.isclose(volume(zero_delta), 2003.0)
    record = zero_delta["native"]["operations"][0]
    assert record["add_volume_check"]["status"] == "passed"
    assert abs(record["material_delta_mm3"]) <= record["add_volume_check"]["tolerance_mm3"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "build/bug191_add_volume_guard.json")
    args = parser.parse_args()
    run(args.output, baseline=args.baseline)
    print(args.output, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
