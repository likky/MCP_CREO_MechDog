"""DEV-089 T8 / DEV-080 H07: submit a plan from one frozen local JSON file.

``creo_execute_plan`` accepts an operations array inline today. Large external
plans are easier to keep as a file, so this module reads one explicitly named
local file once and hands the parsed array to the normal admission path:

* The file must be an absolute local regular file. UNC/network paths,
  device/verbatim paths and relative paths are refused.
* The file is read exactly once. The bytes that were hashed are the bytes that
  are parsed; a file that changes afterwards is never re-read.
* UTF-8 with an optional BOM, duplicate JSON keys and non-finite numbers
  (``NaN``/``Infinity``) are refused.
* The top level must be the existing operations array. Model id, revision,
  assertions and timeout stay as explicit tool arguments, so a plan file cannot
  smuggle a second request envelope.

The parsed array then goes through exactly the same capability gate, revision
check, busy refusal, transaction and assertions as an inline plan.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MAX_PLAN_FILE_BYTES = 16 * 1024 * 1024


def _reject_constant(token: str) -> Any:
    raise ValueError(f"plan_file contains the non-finite JSON number {token}; use finite values")


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(
                f"plan_file has the duplicate JSON key {key!r}; a repeated key would let one "
                "value silently overwrite the other"
            )
        result[key] = value
    return result


def validate_plan_file_path(path: Any) -> Path:
    """Return the local regular file to read, or raise with the reason."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("plan_file must be a non-empty string path")
    text = path.strip()
    if text.startswith(("\\\\?\\", "\\\\.\\")):
        raise ValueError("plan_file must be a normal local file; device/verbatim paths are refused")
    if text.startswith(("\\\\", "//")):
        raise ValueError("plan_file must be a local absolute path; UNC/network paths are refused")
    candidate = Path(text)
    if not candidate.is_absolute():
        raise ValueError(
            "plan_file must be an absolute local path; a relative path would depend on the "
            "executor's working directory"
        )
    if not candidate.exists():
        raise ValueError(f"plan_file does not exist: {candidate}")
    if not candidate.is_file():
        raise ValueError(f"plan_file must be a regular file, not a directory: {candidate}")
    return candidate


def load_plan_operations(path: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read, hash and parse one plan file; return (operations, identity record)."""
    candidate = validate_plan_file_path(path)
    raw = candidate.read_bytes()
    if len(raw) > MAX_PLAN_FILE_BYTES:
        raise ValueError(f"plan_file is {len(raw)} bytes; the limit is {MAX_PLAN_FILE_BYTES} bytes")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"plan_file must be UTF-8 text: {exc}") from None
    try:
        data = json.loads(
            text, object_pairs_hook=_no_duplicate_keys, parse_constant=_reject_constant
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"plan_file is not valid JSON: {exc}") from None
    if not isinstance(data, list):
        raise ValueError(
            "plan_file must contain the operations array (a JSON list); model/revision/"
            "assertions/timeout stay as explicit tool arguments"
        )
    for index, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"plan_file operations[{index}] must be a JSON object")
    record = {
        "path": str(candidate),
        "resolved_path": str(candidate.resolve()),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    return data, record
