"""FEAT-057: normalize the native mass-properties reading.

The native executor measures the geometry and reports which density it used
(``model_material``, ``request`` or ``none``). This module only shapes that
reading for the public receipt and refuses combinations that cannot be true, so
a missing mass is never filled in from an assumed density.

An assembly adds one more failure mode: Creo sums active occurrences, so a
component without a material (or one whose model did not resolve) would weigh
zero without saying so. The native scan reports those occurrences, and this
module keeps ``mass_g`` null whenever the scan cannot vouch for the total.
"""

from __future__ import annotations

from math import isfinite
from typing import Any

DENSITY_SOURCES = ("model_material", "request", "none")

#: Why a reading carries no mass. The native executor names the broken link so
#: the receipt does not repeat "assign a material" when a material already
#: exists but its unit (or density) cannot be used.
MASS_UNAVAILABLE_REASONS = (
    "no_density",
    "unsupported_mass_unit",
    "material_density_unavailable",
    "material_query_failed",
    "volume_unavailable",
    "component_material_missing",
    "component_unavailable",
    "component_scan_incomplete",
    "no_components",
)

#: Native readings from before the assembly path carry no model_type; those can
#: only be parts, so the default keeps old receipts valid.
MODEL_TYPES = ("part", "assembly")


def normalize_mass_properties(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Return the public receipt for one native ``mass_properties`` block."""
    if not isinstance(raw, dict):
        raise ValueError("Mass properties reading is missing")
    if raw.get("mass_value_unit", "g") != "g":
        raise ValueError("mass_value_unit must be g for mass_g")

    volume = _number_or_none(raw.get("volume_mm3"), "volume_mm3")
    surface_area = _number_or_none(raw.get("surface_area_mm2"), "surface_area_mm2")
    if surface_area is not None and surface_area < 0:
        raise ValueError("surface_area_mm2 must not be negative")
    mass = _number_or_none(raw.get("mass_g"), "mass_g")
    density = _number_or_none(raw.get("density_g_cm3"), "density_g_cm3")
    model_type = raw.get("model_type", "part")
    if model_type not in MODEL_TYPES:
        raise ValueError(f"Unknown mass properties model type: {model_type!r}")
    component_scan = _component_scan(raw.get("component_scan"))
    effective_average = raw.get("density_is_effective_average", False)
    if not isinstance(effective_average, bool):
        raise ValueError("density_is_effective_average must be a boolean")
    source = raw.get("density_source")
    if source not in DENSITY_SOURCES:
        raise ValueError(f"Unknown density source: {source!r}")
    mass_source = raw.get("mass_source")
    if mass_source is None:
        mass_source = {
            "request": "computed_from_density",
            "model_material": "native",
            "none": "none",
        }[source]
    expected_mass_source = {
        "request": "computed_from_density",
        "model_material": "native",
        "none": "none",
    }[source]
    if mass_source != expected_mass_source:
        raise ValueError("mass_source disagrees with density_source")
    reason = raw.get("mass_unavailable_reason")
    if reason is not None and reason not in MASS_UNAVAILABLE_REASONS:
        raise ValueError(f"Unknown mass unavailable reason: {reason!r}")
    if source != "none" and reason is not None:
        raise ValueError(
            "A mass reading with a density source cannot carry an unavailable reason "
            f"(density_source={source}, mass_unavailable_reason={reason}, "
            f"mass_g={mass}, volume_mm3={volume}, "
            f"hint_present={raw.get('hint') is not None})"
        )
    if effective_average and (model_type != "assembly" or source != "model_material"):
        raise ValueError(
            "density_is_effective_average only describes an assembly mass taken from "
            f"model materials (model_type={model_type}, density_source={source})"
        )
    if model_type == "assembly" and source == "model_material" and component_scan is None:
        raise ValueError("An assembly mass from model materials needs its component scan")

    if source == "none":
        if mass is not None or density is not None:
            raise ValueError("A reading without a density source cannot carry mass or density")
    else:
        if volume is None or volume <= 0:
            raise ValueError("A mass reading needs a positive volume")
        if mass is None or density is None:
            raise ValueError("A mass reading with a density source must carry mass and density")
        product = volume * density
        if not isfinite(product):
            raise ValueError("volume_mm3 * density_g_cm3 must be finite for mass_g consistency")
        expected = product / 1000.0
        difference = expected - mass
        if not isfinite(difference):
            raise ValueError("mass_g difference from volume_mm3 * density_g_cm3 must be finite")
        if abs(difference) > max(1e-9, abs(expected) * 1e-9):
            raise ValueError(f"Mass {mass} g does not match volume {volume} mm3 at {density} g/cm3")

    hint = raw.get("hint")
    mass_code = raw.get("mass_query_code")
    if reason == "material_query_failed" and type(mass_code) is int and mass_code != 0:
        hint = (
            f"Creo mass query ProSolidMassPropertyWithDensityGet "
            f"(PRO_MP_DENS_DEFAULT) returned {mass_code}. Check the assigned material and its "
            "density in Creo. Supply density_g_cm3 to calculate an explicit what-if mass."
        )
    return {
        "model_type": model_type,
        "volume_mm3": volume,
        "surface_area_mm2": surface_area,
        "mass_g": mass,
        "mass_value_unit": "g",
        "mass_source": mass_source,
        "density_g_cm3": density,
        "density_source": source,
        "density_is_effective_average": effective_average,
        "mass_unavailable_reason": reason,
        "center_of_mass_mm": _triple_or_none(raw.get("center_of_mass_mm")),
        "center_of_volume_mm": _triple_or_none(raw.get("center_of_volume_mm")),
        "material_assigned": bool(raw.get("material_assigned")),
        "mass_unit": raw.get("mass_unit"),
        "native_mass_unit": raw.get("mass_unit"),
        "component_scan": component_scan,
        "hint": hint,
        "query_codes": {
            "volume": raw.get("volume_query_code"),
            "mass": mass_code,
            "units": raw.get("units_query_code"),
        },
    }


def _number_or_none(value: Any, field: str) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return _finite_number(value, field)


def _finite_number(value: int | float, field: str) -> float:
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"{field} cannot be represented as a finite float") from exc
    if not isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _triple_or_none(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        return None
    return [_finite_number(item, f"center_of_mass_mm[{index}]") for index, item in enumerate(value)]


def _component_scan(value: Any) -> dict[str, Any] | None:
    """Validate the per-occurrence assembly evidence before publishing it.

    The scan is the only proof that an assembly total is complete, so a
    malformed block is refused instead of being echoed: a caller must never see
    ``complete`` disagreeing with the lists it summarises.
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("component_scan must be an object")
    occurrences = _count(value.get("occurrences"), "component_scan.occurrences")
    suppressed = _count(value.get("suppressed"), "component_scan.suppressed")
    truncated = value.get("truncated")
    if not isinstance(truncated, bool):
        raise ValueError("component_scan.truncated must be a boolean")
    complete = value.get("complete")
    if not isinstance(complete, bool):
        raise ValueError("component_scan.complete must be a boolean")
    without_material = _occurrence_paths(
        value.get("without_material"), "component_scan.without_material"
    )
    unresolved = _unresolved_items(value.get("unresolved"))
    visit_codes = value.get("visit_codes")
    if not isinstance(visit_codes, list):
        raise ValueError("component_scan.visit_codes must be a list")
    codes = [
        _code(visit_code, f"component_scan.visit_codes[{index}]")
        for index, visit_code in enumerate(visit_codes)
    ]
    expected_complete = not truncated and not without_material and not unresolved and not codes
    if complete != expected_complete:
        raise ValueError("component_scan.complete disagrees with its recorded evidence")
    return {
        "occurrences": occurrences,
        "suppressed": suppressed,
        "without_material": without_material,
        "unresolved": unresolved,
        "truncated": truncated,
        "visit_codes": codes,
        "complete": complete,
    }


def _count(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer")
    return value


def _code(value: Any, field: str) -> int:
    """Toolkit return codes are signed; only their type is checked."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be a Toolkit return code integer")
    return value


def _occurrence_paths(value: Any, field: str) -> list[list[int]]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    paths: list[list[int]] = []
    for index, path in enumerate(value):
        if not isinstance(path, list) or not path:
            raise ValueError(f"{field}[{index}] must be a non-empty occurrence path")
        paths.append([_count(item, f"{field}[{index}]") for item in path])
    return paths


def _unresolved_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("component_scan.unresolved must be a list")
    items: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        field = f"component_scan.unresolved[{index}]"
        if not isinstance(item, dict) or set(item) != {"occurrence_path", "code"}:
            raise ValueError(f"{field} must carry only occurrence_path and code")
        path = _occurrence_paths([item["occurrence_path"]], f"{field}.occurrence_path")[0]
        items.append({"occurrence_path": path, "code": _code(item["code"], f"{field}.code")})
    return items
