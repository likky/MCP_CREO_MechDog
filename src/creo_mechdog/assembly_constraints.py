"""DEV-089 T5: static assembly mate semantics and their native mapping.

The native executor has six proven constraint types (mate, align, mate_offset,
align_offset, insert, csys). External reports describe relationships instead
("coincident", "concentric", "parallel", "distance"), so this module freezes how
those words translate before a job is dispatched.

Only relationships that map onto an already verified type are admitted:

* ``coincident`` -> ``mate``. PRO_ASM_MATE accepts planar, conical, toroidal and
  cylindrical surfaces (ProAsmcomp.h reference table), so a face pair is legal
  without guessing which kind of face it is.
* ``concentric`` -> ``insert``. PRO_ASM_INSERT is the coaxial constraint and
  accepts cylinder/cone/torus surfaces only; a planar or axis reference is
  refused here instead of failing later inside the kernel.

``parallel`` (PRO_ASM_ORIENT, plane/CSYS) and ``distance`` on axes/points
(PRO_ASM_LINE_DIST / PRO_ASM_PNT_DIST, axis/edge/point) are declared by the
installed SDK but have not been verified on a live assembly in this project.
They stay refused with a named gap; the enum existing is not evidence that the
write path works. Face distance is still expressible with the proven
``mate_offset``/``align_offset`` types.
"""

from __future__ import annotations

from typing import Any

from .geometry_selectors import validate_geometry_selector

SEMANTIC_TYPES = ("coincident", "concentric", "parallel", "distance")

#: Relationship word -> proven native constraint type.
MAPPING = {"coincident": "mate", "concentric": "insert"}

#: Relationship words that stay refused, with the measured gap.
UNVERIFIED = {
    "parallel": (
        "PRO_ASM_ORIENT (parallel) is declared for plane/CSYS references but this project "
        "has not written or solved it on a live assembly; no write-side mapping is opened "
        "yet. Use align/align_offset for same-direction plane pairs"
    ),
    "distance": (
        "distance on axes or points needs PRO_ASM_LINE_DIST/PNT_DIST, which are declared "
        "but not verified on a live assembly here. Face distance is supported today as "
        "mate_offset/align_offset with an explicit offset and sides"
    ),
}

FACE_REFERENCE_KINDS = frozenset(
    {"surface", "plane", "datum_plane", "datum_feature", "geometry_selector"}
)
COAXIAL_REFERENCE_KINDS = frozenset({"surface", "geometry_selector"})


def _selector_reference(reference: dict[str, Any], path: str, kind: str) -> dict[str, Any]:
    """A selector is an anchor, not a face-kind claim: check what it may resolve to.

    ``coincident``/mate needs a real plane, but only the resolved native surface
    can prove that, so the native side re-checks the surface type after
    resolution. ``concentric``/insert needs a cylinder; requiring ``radius_mm``
    here guarantees the selector cannot resolve to a plane in the first place.
    """
    normalized = validate_geometry_selector(reference, path)
    if normalized.get("target") != "surface":
        raise ValueError(
            f"{path}: a {kind} reference needs a surface selector "
            f"({{kind:'geometry_selector',target:'surface',...}}), not "
            f"target={normalized.get('target')!r}"
        )
    if kind == "concentric" and "radius_mm" not in normalized:
        raise ValueError(
            f"{path}: a concentric selector needs radius_mm (and preferably axis) so it can "
            "only resolve to a cylindrical surface; a points-only selector could also hit a "
            "plane and insert cannot use it"
        )
    return normalized


def _reference_kind(reference: Any, path: str) -> str:
    if not isinstance(reference, dict) or not isinstance(reference.get("kind"), str):
        raise ValueError(f"{path}: an assembly reference requires an explicit {{kind:...}}")
    return reference["kind"]


def normalize_constraint_type(constraint: dict[str, Any]) -> dict[str, Any]:
    """Return a copy whose relationship word is a proven native type.

    Base types pass through untouched. Unverified relationships raise with the
    specific missing evidence instead of being mapped to a lookalike.
    """
    kind = constraint.get("type")
    if kind not in SEMANTIC_TYPES:
        return constraint
    if kind in UNVERIFIED:
        raise ValueError(f"Assembly relationship '{kind}' is not supported yet: {UNVERIFIED[kind]}")
    normalized = dict(constraint)
    if kind == "coincident":
        for key in ("assembly_reference", "component_reference"):
            reference = constraint.get(key)
            reference_kind = _reference_kind(reference, f"constraint.{key}")
            if reference_kind not in FACE_REFERENCE_KINDS:
                raise ValueError(
                    f"constraint.{key}: 'coincident' maps to mate and needs a face reference "
                    f"(surface/plane/datum_plane/datum_feature/geometry_selector), not "
                    f"'{reference_kind}'"
                )
            if reference_kind == "geometry_selector":
                normalized[key] = _selector_reference(reference, f"constraint.{key}", kind)
    if kind == "concentric":
        for key in ("assembly_reference", "component_reference"):
            reference = constraint.get(key)
            reference_kind = _reference_kind(reference, f"constraint.{key}")
            if reference_kind not in COAXIAL_REFERENCE_KINDS:
                raise ValueError(
                    f"constraint.{key}: 'concentric' maps to insert and needs a cylindrical "
                    f"{{kind:'surface',id:N}} reference, not '{reference_kind}'; axis/edge "
                    "coaxiality would need the unverified LINE_PARL/LINE_DIST path"
                )
            if reference_kind == "geometry_selector":
                normalized[key] = _selector_reference(reference, f"constraint.{key}", kind)
    normalized["type"] = MAPPING[kind]
    return normalized
