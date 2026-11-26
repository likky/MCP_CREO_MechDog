"""FEAT-078 Creo 10 solid bounding boxes with independent geometry oracles."""

from __future__ import annotations

import argparse
import json
import math
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bridge  # noqa: E402
from creo_mechdog import generic_bridge as general  # noqa: E402
from tools.test_feedback0358_pattern_scope import git_commit_and_dirty, sha256_file, wait_job  # noqa: E402

RADIUS = 41.0
TOLERANCE_MM = 0.005


def sketch(label: str, plane: str, *entities: dict) -> dict:
    return {
        "op": "sketch",
        "label": label,
        "plane": plane,
        "dimensioning": "coordinates",
        "entities": [dict(entity, name=f"e{i}") for i, entity in enumerate(entities)],
    }


def rectangle(x0: float, y0: float, x1: float, y1: float) -> dict:
    return {"type": "rectangle", "min": [x0, y0], "max": [x1, y1]}


def extrude(label: str, section: str, **options: object) -> dict:
    return {"op": "extrude", "label": label, "sketch": section, **options}


def run(output: Path, *, baseline: bool) -> None:
    session = bridge.session_status(connect_timeout_seconds=15)
    assert session["connected"], session
    report = {
        "baseline": baseline,
        "session": session,
        "source": git_commit_and_dirty(),
        "worker_sha256": sha256_file(ROOT / "build/creo_worker.exe"),
        "worker_source_digest": (ROOT / "build/source.sha256").read_text().strip(),
        "tolerance_mm": TOLERANCE_MM,
        "jobs": {},
    }
    suffix = uuid.uuid4().hex[:8]

    def job(key, operations, expected, prior=None, *, model_type="part", readonly=False):
        arguments = {"model_name": f"b078_{key}_{suffix}", "model_type": model_type}
        if prior is not None:
            arguments = {"model_id": prior["model_id"], "readonly": readonly}
            if not readonly:
                arguments["expected_revision"] = prior["revision"]
        created = general.submit(operations, **arguments)
        job_id = created["job_id"]
        result = wait_job(job_id)
        native = json.loads((ROOT / "jobs" / job_id / "native_result.json").read_text("utf-8"))
        inspection = native.get("inspection") or {}
        compact = general.inspect_model(created["model_id"], detail="compact")
        box = inspection.get("bounding_box_mm")
        errors = (
            None
            if box is None or expected is None
            else {
                key: [a - b for a, b in zip(box[key], values, strict=True)]
                for key, values in zip(("min", "max"), expected, strict=True)
            }
        )
        record = {
            "job_id": job_id,
            "model_id": created["model_id"],
            "status": result["status"],
            "message": result["message"],
            "revision": compact["revision"],
            "input": operations,
            "expected_mm": expected,
            "error_mm": errors,
            "box": box,
            "volume_mm3": inspection.get("volume_mm3"),
            "bodies": inspection.get("bodies"),
            "components": inspection.get("components"),
            "source": inspection.get("bounding_box_source"),
            "status_detail": inspection.get("bounding_box_status"),
            "inspection_source": native.get("inspection_source"),
            "saved_reloaded": native.get("saved_file_reloaded_and_verified"),
        }
        report["jobs"][key] = record
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(key, job_id, result["status"], box, errors, result["message"], flush=True)
        assert result["status"] == "succeeded", record
        if not readonly:
            assert record["saved_reloaded"] is True, record
        if not baseline:
            assert compact["inspection"].get("bounding_box_mm") == box, record
            assert compact["inspection"].get("bounding_box_source") == record["source"], record
            assert compact["inspection"].get("bounding_box_status") == record["status_detail"], (
                record
            )
            assert record["source"] == "solid_face_tessellation", record
            if expected is None:
                assert box is None, record
                assert record["status_detail"]["state"] == "no_solid", record
            else:
                assert record["status_detail"]["state"] == "measured", record
                assert errors and all(
                    abs(e) <= TOLERANCE_MM for row in errors.values() for e in row
                ), record
                assert all(
                    abs(s - (hi - lo)) < 1e-9
                    for s, hi, lo in zip(box["size"], box["max"], box["min"], strict=True)
                ), record
        return record

    disk = job(
        "disk",
        [
            sketch("disc_sk", "XY", {"type": "circle", "center": [0, 0], "radius": RADIUS}),
            extrude("disc", "disc_sk", depth=5),
        ],
        ([-41, -41, 0], [41, 41, 5]),
    )
    tooth = job(
        "tooth",
        [
            sketch("tooth_sk", "XY", rectangle(-1, 39, 1, 41.25)),
            extrude(
                "tooth_cut", "tooth_sk", mode="cut", direction="symmetric", depth_type="through_all"
            ),
        ],
        ([-41, -41, 0], [41, math.sqrt(RADIUS**2 - 1), 5]),
        disk,
    )
    assert tooth["volume_mm3"] < disk["volume_mm3"]

    plate = job(
        "plate",
        [
            sketch("plate_sk", "XY", rectangle(-50, -40, 50, 40)),
            extrude("plate", "plate_sk", depth=5),
        ],
        ([-50, -40, 0], [50, 40, 5]),
    )
    slot = job(
        "slot",
        [
            sketch("slot_sk", "XZ", rectangle(8, -0.5, 15, 5.5)),
            extrude(
                "slot_cut", "slot_sk", mode="cut", direction="symmetric", depth_type="through_all"
            ),
        ],
        ([-50, -40, 0], [50, 40, 5]),
        plate,
    )
    assert math.isclose(slot["volume_mm3"], (100 - 7) * 80 * 5, abs_tol=1e-6)

    center, inner, outer = 15.0, 72.367, 75.370
    a, b = center - outer, center - inner
    c, d = 1.4, 2.88
    profile = {
        "type": "polyline",
        "closed": True,
        "points": [
            [a + c, -6],
            [b - c, -6],
            [b, -6 + d],
            [b, 6 - d],
            [b - c, 6],
            [a + c, 6],
            [a, 6 - d],
            [a, -6 + d],
        ],
    }
    half_angle = math.radians(33.5)
    sweep_end = outer * math.sin(half_angle)
    shell_bounds = ([a, -6, -sweep_end], [center - inner * math.cos(half_angle), 6, sweep_end])
    shell = job(
        "shell",
        [
            sketch(
                "shell_sk",
                "XY",
                profile,
                {"type": "centerline", "start": [center, -10], "end": [center, 10]},
            ),
            {
                "op": "revolve",
                "label": "shell",
                "sketch": "shell_sk",
                "angle": 67,
                "direction": "symmetric",
            },
        ],
        shell_bounds,
    )
    assert shell["volume_mm3"] > 0

    # A large detached quilt must remain absent, even in the rotated assembly.
    quilt_ops = [
        sketch("outlying_sk", "XY", rectangle(120, 110, 140, 160)),
        extrude("outlying_quilt", "outlying_sk", depth=25, mode="surface"),
    ]
    job("quilt_only", quilt_ops, None)
    # An uncut disk has closed-form support under an oblique rotation.
    cylinder = job("cylinder", disk["input"] + quilt_ops, ([-41, -41, 0], [41, 41, 5]))
    sx, cx = 0.5, math.sqrt(3) / 2
    sz, cz = math.sin(math.radians(37)), math.cos(math.radians(37))
    rotation = [[cz, sz, 0], [-cx * sz, cx * cz, sx], [sx * sz, -sx * cz, cx]]
    translation = [12, 25, -3]
    support = [RADIUS * math.hypot(rotation[0][i], rotation[1][i]) for i in range(3)]
    axial = [5 * value for value in rotation[2]]
    assembly_bounds = (
        [translation[i] - support[i] + min(0, axial[i]) for i in range(3)],
        [translation[i] + support[i] + max(0, axial[i]) for i in range(3)],
    )
    assembly = job(
        "assembly",
        [
            {
                "op": "assemble_component",
                "label": "tilted_disc",
                "source_model_id": cylinder["model_id"],
                "placement": "fixed",
                "rotation_matrix": rotation,
                "translation": translation,
            }
        ],
        assembly_bounds,
        model_type="assembly",
    )
    lo, hi = assembly_bounds
    nested_bounds = (
        [min(-161, -hi[1]), min(-41, lo[0]), min(0, lo[2] + 8)],
        [max(-79, -lo[1]), max(41, hi[0]), max(5, hi[2] + 8)],
    )
    nested = job(
        "nested",
        [
            {
                "op": "assemble_component",
                "label": "sub",
                "source_model_id": assembly["model_id"],
                "rotation": [0, 0, 90],
                "translation": [0, 0, 8],
            },
            {
                "op": "assemble_component",
                "label": "second",
                "source_model_id": cylinder["model_id"],
                "translation": [-120, 0, 0],
            },
        ],
        nested_bounds,
        model_type="assembly",
    )
    for key, original, bounds in (
        ("tooth", tooth, tooth["expected_mm"]),
        ("slot", slot, slot["expected_mm"]),
        ("shell", shell, shell_bounds),
        ("assembly", assembly, assembly_bounds),
        ("nested", nested, nested_bounds),
    ):
        saved = job(key + "_reload", [{"op": "save"}], bounds, original)
        refreshed = job(key + "_refresh", [], bounds, saved, readonly=True)
        assert saved["box"] == refreshed["box"], key


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "build/feat078_solid_bbox.json")
    args = parser.parse_args()
    run(args.output, baseline=args.baseline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
