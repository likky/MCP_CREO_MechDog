"""BUG-120/D5: the receipt a resident-panel loft has to earn.

A panel run is not a tree run with a different menu. It replays UI commands, so the
things that make its result trustworthy are different:

- which UI profile ran it and whether that profile was certified or only a
  development candidate;
- what the callback asked the dialog to select, and what the dialog actually
  recorded;
- whether the panel exit was observed at all — a worker that returned while a dialog
  was still waiting has not told us what happened;
- whether the feature and quilt in the model are the ones this run created, not a
  quilt that already existed;
- whether the geometry check was performed on this product, and whether the bbox is
  the approximate ``ProSurfaceDataGet`` range rather than a measured boundary.

This module projects the native record into that receipt and refuses to promote an
unproven run to ``success``. It never invents a missing native value: an absent exit
observation stays unknown, an absent geometry check stays unknown, and an
unconfirmed panel exit forces ``success=false`` with
``panel_execution_unconfirmed=true`` exactly like the tree path does.
"""

from __future__ import annotations

from typing import Any

CONTRACT = "panel-receipt-v1"

#: Native report fields of an exit observation. A record that cannot supply these
#: is treated as "not supported", never as "closed".
EXIT_FIELDS = ("method", "supported", "closed", "reason", "evidence")

#: Failure codes this projection may add. They are stable so a client can branch.
PROBLEM_CODES = (
    "panel_exit_unconfirmed",
    "panel_selection_intent_mismatch",
    "panel_reference_missing",
    "panel_quilt_not_new",
    "panel_face_group_invalid",
    "panel_area_not_positive",
    "panel_feature_not_associated",
    "panel_kernel_completion_claimed",
)


def _panel_records(result: dict[str, Any], route: str | None) -> list[dict[str, Any]]:
    records = result.get("operations")
    if not isinstance(records, list):
        return []
    selected = [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("op") == "surface_loft"
        and (record.get("creation_route") == "resident_panel" or route == "resident_panel")
    ]
    return selected


def _exit_observation(record: dict[str, Any]) -> dict[str, Any]:
    """The native exit report, or an explicit "not supported/unknown" record."""
    report = record.get("exit_observation")
    if not isinstance(report, dict):
        return {
            "supported": False,
            "closed": None,
            "method": None,
            "reason": "the native panel backend reported no exit observation",
            "evidence": None,
        }
    normalized = {field: report.get(field) for field in EXIT_FIELDS}
    if normalized.get("supported") is not True:
        # An unsupported observer cannot have seen a close, whatever the record says.
        normalized["closed"] = None
        if not normalized.get("reason"):
            normalized["reason"] = "the native panel backend reported exit support=false"
    return normalized


def _geometry_check(record: dict[str, Any], prior_inspection: object) -> dict[str, Any]:
    check = record.get("geometry_check")
    verification = check if isinstance(check, dict) else {}
    bbox = verification.get("bbox")
    bbox_view = None
    if isinstance(bbox, dict):
        # ProSurfaceDataGet returns an approximate range. Keeping the flag on the
        # receipt is what stops a later reader from treating it as a measured bound.
        bbox_view = {
            "xyz_min": bbox.get("xyz_min"),
            "xyz_max": bbox.get("xyz_max"),
            "source": bbox.get("source"),
            "approximate": bbox.get("source") != "measured",
        }
    quilt_id = record.get("quilt_id")
    prior_quilts: set[object] = set()
    if isinstance(prior_inspection, dict):
        for key in ("quilts", "surfaces"):
            values = prior_inspection.get(key)
            if isinstance(values, list):
                prior_quilts.update(
                    value.get("id") if isinstance(value, dict) else value for value in values
                )
    return {
        "verified": verification.get("verified") is True,
        "quilt_id": quilt_id,
        "quilt_is_new": None
        if not prior_quilts or quilt_id is None
        else quilt_id not in prior_quilts,
        "face_groups": verification.get("face_groups"),
        "area_mm2": verification.get("area_mm2"),
        "bbox": bbox_view,
        "samples": verification.get("samples"),
        "method": verification.get("method"),
    }


def _selection(record: dict[str, Any], inputs: list[dict[str, Any]] | None, position: int) -> tuple:
    intent = record.get("selection_intent")
    recorded = record.get("selection_record")
    source = inputs[position] if isinstance(inputs, list) and position < len(inputs) else None
    labels = None
    if isinstance(source, dict):
        sections = source.get("sections")
        if isinstance(sections, list):
            labels = [str(label) for label in sections]
    problems = []
    if isinstance(recorded, dict):
        selected = recorded.get("labels")
        if labels and isinstance(selected, list) and [str(v) for v in selected] != labels:
            problems.append(
                {
                    "code": "panel_selection_intent_mismatch",
                    "message": (
                        f"the dialog recorded {selected!r} but the request asked for {labels!r}; "
                        "the created surface is not the requested one"
                    ),
                }
            )
        references = recorded.get("references")
        if isinstance(references, list) and any(
            isinstance(ref, dict) and ref.get("missing") is True for ref in references
        ):
            problems.append(
                {
                    "code": "panel_reference_missing",
                    "message": (
                        "a curve reference was resolved from the label but was not found in the "
                        "created product"
                    ),
                }
            )
    return intent, recorded, problems


def annotate(
    result: dict[str, Any],
    *,
    admission: object = None,
    inputs: list[dict[str, Any]] | None = None,
    prior_inspection: object = None,
    route: str | None = None,
) -> dict[str, Any]:
    """Attach the panel receipt and refuse to call an unproven run successful."""
    records = _panel_records(result, route)
    if not records:
        return result
    record = records[0]
    position = result.get("operations", []).index(record)
    intent, recorded, problems = _selection(record, inputs, position)
    exit_report = _exit_observation(record)
    geometry = _geometry_check(record, prior_inspection)

    if exit_report.get("closed") is not True:
        problems.append(
            {
                "code": "panel_exit_unconfirmed",
                "message": (
                    "the resident panel exit was not observed ("
                    f"{exit_report.get('reason') or 'no evidence'}); the job's final effect is "
                    "unknown and no rollback is claimed"
                ),
            }
        )
    if geometry["quilt_is_new"] is False:
        problems.append(
            {
                "code": "panel_quilt_not_new",
                "message": (
                    f"quilt {geometry['quilt_id']!r} already existed before this job, so it is not "
                    "the product of this run"
                ),
            }
        )
    groups = geometry.get("face_groups")
    if isinstance(groups, list) and len(groups) != 1:
        problems.append(
            {
                "code": "panel_face_group_invalid",
                "message": (
                    f"the created surface has {len(groups)} face groups; a single open quilt is "
                    "expected"
                ),
            }
        )
    area = geometry.get("area_mm2")
    if isinstance(area, (int, float)) and not isinstance(area, bool) and area <= 0:
        problems.append(
            {
                "code": "panel_area_not_positive",
                "message": f"the reported surface area is {area} mm²; a zero or negative area is "
                "not a created surface",
            }
        )
    quilt_id = geometry.get("quilt_id")
    feature_id = record.get("feature_id")
    association = record.get("feature_quilt")
    if association is not None and quilt_id is not None and association != quilt_id:
        problems.append(
            {
                "code": "panel_feature_not_associated",
                "message": (
                    f"feature {feature_id!r} is associated with {association!r}, not with the "
                    f"created quilt {quilt_id!r}"
                ),
            }
        )
    completion = record.get("kernel_completion")
    if isinstance(completion, dict) and completion.get("state") == "supported":
        # The tree route's completion proof does not exist for a panel run.
        record["kernel_completion"] = {
            **completion,
            "state": "not_applicable",
            "reason": "a resident panel run has no element-tree extract to prove",
        }
        problems.append(
            {
                "code": "panel_kernel_completion_claimed",
                "message": (
                    "the panel result claimed the element-tree kernel completion state; it was "
                    "downgraded to not_applicable"
                ),
            }
        )

    profile = None
    if isinstance(admission, dict):
        profile = {
            "profile_id": admission.get("profile_id"),
            "mode": admission.get("mode"),
            "release_numeric": admission.get("release_numeric"),
            "host_release_numeric": admission.get("host_release_numeric"),
            "unverified_bindings": admission.get("unverified_bindings"),
        }
    receipt = {
        "contract": CONTRACT,
        "creation_route": "resident_panel",
        "profile": profile,
        "selection_intent": intent,
        "selection_record": recorded,
        "exit_observation": exit_report,
        "feature_id": record.get("feature_id"),
        "quilt_id": record.get("quilt_id"),
        "geometry_check": geometry,
        "saved_file_reloaded_and_verified": result.get("saved_file_reloaded_and_verified") is True,
        "problems": problems,
    }
    result["creation_route"] = "resident_panel"
    result["panel_receipt"] = receipt
    if problems:
        codes = {problem["code"] for problem in problems}
        if "panel_exit_unconfirmed" in codes:
            result["panel_execution_unconfirmed"] = True
            result["success"] = False
            result["rollback_succeeded"] = False
        result["success"] = False
        result["message"] = "; ".join(
            [str(result.get("message") or "")]
            + [f"{problem['code']}: {problem['message']}" for problem in problems]
        ).strip("; ")
        receipt["status"] = "failed"
    else:
        receipt["status"] = "succeeded" if result.get("success") else "unknown"
    return result
