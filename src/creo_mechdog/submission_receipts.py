"""FEAT-023: bounded submission receipts for ``creo_execute_plan``.

``submit()`` used to hand the whole job manifest back, including the normalized
operation list it had just frozen. A 200-operation plan therefore echoed itself
into the client response even though ``job.json`` already holds the same array
and ``creo_get_job`` reads it back.

This module only decides what the *submit* call returns. The job record stays
complete: ``response_detail="compact"`` never truncates ``job.json``, never hides
the identity or failure fields, and never drops a file input's path or already
computed digest. It removes one thing - the operations array - and replaces it
with a count and a pointer to the job detail.
"""

from __future__ import annotations

from typing import Any

DETAIL_LEVELS = ("full", "compact")
DEFAULT_DETAIL = "full"

#: Identity, status and operational pointers a compact receipt keeps.
_COMPACT_KEYS = (
    "job_id",
    "kind",
    "model_id",
    "model_name",
    "status",
    "revision",
    "readonly",
    "readonly_source",
    "timeout_seconds",
    "timeout_source",
    # BUG-158: the stall watchdog is separate from the job budget; a compact
    # receipt that drops it cannot answer "will timeout_seconds keep the job
    # alive?". Keep the pair and the files the watchdog reads.
    "stall_watchdog_seconds",
    "stall_watchdog_source",
    "watch_files",
    "job_directory",
    "output_directory",
    "region_adaptation",
    "construction",
    # A failure message is identity-critical and must survive compaction.
    "message",
)

#: Operation fields that point at a file the plan reads, with the digest each
#: schema variant stores next to it. Nothing is hashed here: a value the plan
#: does not already carry is reported as absent, not recomputed.
_FILE_FIELDS = ("file", "file_path")
_DIGEST_FIELDS = ("file_sha256", "profile_sha256", "sha256")

COMPACT_MESSAGE = (
    "Poll creo_get_job with this job_id; the normalized operations stay in the job "
    "record and are not echoed here"
)


def normalize_detail(detail: Any) -> str:
    """Return the effective detail level, refusing anything outside the contract."""
    if detail is None:
        return DEFAULT_DETAIL
    if not isinstance(detail, str) or detail not in DETAIL_LEVELS:
        raise ValueError(
            "response_detail must be 'full' or 'compact'; got "
            f"{detail!r}. 'full' (the default) echoes the normalized operations, "
            "'compact' returns the count and leaves them in the job record"
        )
    return detail


def _file_inputs(operations: Any) -> list[dict[str, Any]]:
    if not isinstance(operations, list):
        return []
    inputs: list[dict[str, Any]] = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            continue
        path_field = next((field for field in _FILE_FIELDS if operation.get(field)), None)
        if path_field is None:
            continue
        digest_field = next(
            (field for field in _DIGEST_FIELDS if isinstance(operation.get(field), str)),
            None,
        )
        entry: dict[str, Any] = {
            "index": index,
            "op": operation.get("op"),
            "label": operation.get("label"),
            "path": operation[path_field],
            "path_field": path_field,
            "sha256": operation[digest_field] if digest_field else None,
            "sha256_field": digest_field,
        }
        inputs.append(entry)
    return inputs


def project_receipt(receipt: dict[str, Any], detail: str = DEFAULT_DETAIL) -> dict[str, Any]:
    """Return the receipt to publish for this detail level.

    ``full`` returns the manifest untouched, so every existing caller keeps its
    current shape. ``compact`` keeps the identity and failure-relevant fields,
    the operation count, the file inputs and the pointer to the job detail.
    """
    level = normalize_detail(detail)
    if not isinstance(receipt, dict) or level == DEFAULT_DETAIL:
        return receipt
    operations = receipt.get("operations")
    compact = {key: receipt[key] for key in _COMPACT_KEYS if key in receipt}
    compact["operation_count"] = len(operations) if isinstance(operations, list) else None
    compact["file_inputs"] = _file_inputs(operations)
    # The job's own message is never replaced: a failure message is the one
    # field a compact reader must not lose. The pointer lives beside it.
    compact["operations_hint"] = COMPACT_MESSAGE
    compact["response_detail"] = "compact"
    compact["full_operations"] = "creo_get_job"
    return compact
