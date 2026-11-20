"""FEAT-023 / BUG-076: bounded component-list pages.

``creo_list_components`` used to return every component record, the alias map
and the deleted identities in one response. A 269-component assembly produced a
multi-megabyte reply that clients truncated, so a caller could not tell a cut
list from a complete one.

The shape rules here mirror ``job_pages``:

* a list that already fits ``RESPONSE_BUDGET`` keeps the historical shape with
  no paging metadata, so small assemblies read exactly as before;
* a larger list pages through the project cursor
  (``model_queries.encode_cursor``/``decode_cursor``) and every page states
  ``total``, ``offset``, ``returned_count`` and ``complete``;
* the cursor is bound to the model id, the model revision, the requested field
  projection and a snapshot hash of the component records, so a revision change
  or a different projection invalidates it explicitly instead of silently
  re-slicing a different list;
* a single record above the entry budget is reported as an oversize marker
  (path plus size) instead of being cut in half.
"""

from __future__ import annotations

from typing import Any

from creo_mechdog.model_queries import (
    RESPONSE_BUDGET,
    decode_cursor,
    encode_cursor,
    fingerprint,
    serialized_size,
)

PAGE_LIMIT_MAX = 200
ENTRY_BUDGET = RESPONSE_BUDGET - 2048
DEFAULT_LIMIT = 50

_RESTART = "Model revision or component query changed; restart the query without cursor"


def available_fields(components: Any) -> list[str]:
    """Every key present on at least one component record, sorted."""
    keys: set[str] = set()
    for record in components if isinstance(components, list) else []:
        if isinstance(record, dict):
            keys.update(record)
    return sorted(keys)


def _normalize_fields(fields: Any, components: Any) -> list[str] | None:
    if fields is None:
        return None
    if not isinstance(fields, (list, tuple)) or not fields:
        raise ValueError(
            "fields must be a non-empty list of component record keys; omit it to return "
            "every field"
        )
    normalized: list[str] = []
    for field in fields:
        if not isinstance(field, str) or not field:
            raise ValueError(f"fields entries must be non-empty strings; got {field!r}")
        if field in normalized:
            raise ValueError(f"fields lists {field!r} twice; ask for each key once")
        normalized.append(field)
    known = available_fields(components)
    unknown = sorted(set(normalized) - set(known))
    if unknown:
        raise ValueError(f"unknown component field(s) {unknown}; available fields are {known}")
    return normalized


def _project(records: list[Any], fields: list[str] | None) -> list[Any]:
    if fields is None:
        return list(records)
    return [
        {key: record[key] for key in fields if key in record}
        if isinstance(record, dict)
        else record
        for record in records
    ]


def _oversize(index: int, encoded: int) -> dict[str, Any]:
    return {
        "index": index,
        "oversize": True,
        "size_hint_bytes": encoded,
        "hint": (
            "this single component record exceeds the page budget; request fewer fields "
            "(for example fields=['identity','labels','name']) or inspect the model directly"
        ),
    }


def component_page(
    model_id: str,
    revision: Any,
    components: Any,
    *,
    aliases: Any = None,
    deleted_identities: Any = None,
    identity_key: Any = None,
    fields: Any = None,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Return the component list, whole when it fits and paged when it does not."""
    if not type(limit) is int or not 1 <= limit <= PAGE_LIMIT_MAX:
        raise ValueError(f"limit must be 1-{PAGE_LIMIT_MAX}")
    records = components if isinstance(components, list) else []
    projection = _normalize_fields(fields, records)
    selected = _project(records, projection)
    whole = {
        "model_id": model_id,
        "revision": revision,
        "components": selected,
        "deleted_identities": deleted_identities if isinstance(deleted_identities, list) else [],
        "identity_key": identity_key,
        "aliases": aliases if isinstance(aliases, dict) else {},
    }
    token = decode_cursor(cursor)
    if projection is None and token is None and serialized_size(whole) <= RESPONSE_BUDGET:
        return whole
    identity = {
        "model_id": model_id,
        "revision": revision,
        "fields": projection,
        "snapshot_hash": fingerprint(selected),
    }
    if token is not None:
        if any(token.get(key) != value for key, value in identity.items()):
            raise ValueError(_RESTART)
    start = token["offset"] if token else 0
    if not type(start) is int or start < 0 or start > len(selected):
        raise ValueError("Invalid query cursor offset")
    response: dict[str, Any] = {
        "model_id": model_id,
        "revision": revision,
        "identity_key": identity_key,
        "fields": projection,
        "components": [],
        "offset": start,
        "returned_count": 0,
        "total": len(selected),
        "complete": False,
        "next_cursor": None,
        "response_budget_bytes": RESPONSE_BUDGET,
    }
    # The alias map and the deleted identities are bounded by the component
    # count, not by the page; they ride on the first page only and are dropped
    # with an explicit marker when they alone would blow the budget.
    if start == 0:
        extras = {
            "aliases": whole["aliases"],
            "deleted_identities": whole["deleted_identities"],
        }
        if serialized_size({**response, **extras}) <= RESPONSE_BUDGET:
            response.update(extras)
        else:
            response["aliases_omitted"] = "first page budget; query a single component instead"
            response["deleted_identities_omitted"] = "first page budget"
    end = start
    while end < len(selected) and end - start < limit:
        encoded = serialized_size(selected[end])
        if encoded > ENTRY_BUDGET:
            response["components"].append(_oversize(end, encoded))
        else:
            response["components"].append(selected[end])
        if serialized_size(response) > RESPONSE_BUDGET:
            response["components"].pop()
            if end == start:
                raise ValueError(
                    "Single component record plus the page metadata exceeds the response "
                    "budget; request fewer fields with the fields argument"
                )
            break
        end += 1
    while True:
        response["complete"] = end == len(selected)
        response["returned_count"] = end - start
        response["next_cursor"] = (
            encode_cursor({**identity, "offset": end}) if end < len(selected) else None
        )
        if serialized_size(response) <= RESPONSE_BUDGET:
            return response
        # The cursor and the counters are part of the page: when they no longer
        # fit beside the last record, that record moves to the next page. The
        # offset always matches the records actually returned, so no record is
        # skipped or repeated.
        if end - start <= 0:
            raise ValueError("Component page metadata exceeds the response budget")
        response["components"].pop()
        end -= 1
