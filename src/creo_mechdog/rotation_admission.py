"""BUG-045/FEAT-012/BUG-133: one admissions rule for caller-supplied rotation matrices.

Row-vector local-to-parent poses are accepted only when the 3x3 block is
orthonormal and has determinant +1 within the **published** ``1e-7`` tolerance.
The numbers are computed here (and mirrored by ``native/assembly_pose.h``) so a
rejection can quote the caller's own matrix, its orthogonality residual and its
determinant instead of only naming a tolerance.

The 2026-11-21 live perturbation sweep on Creo 10.0.0.0 / release 42 pinned the
kernel boundary: residuals 4.5e-10, 7.7e-9 and 4.76e-8 placed; 2.24e-7, 4.89e-7
and 1.13e-6 were rejected by both ``ProAsmcompAssemble`` and
``ProAsmcompPositionSet`` with code -2. ``1e-7`` therefore sits between the
largest accepted and the smallest rejected matrix. Passing a larger explicit
``rotation_tolerance`` used to admit poses the kernel cannot place; it is now
refused so the failure happens before a job exists.

``NEAR_ORTHONORMAL_TOLERANCE`` only classifies an accepted matrix as ``strict``
or ``near_orthonormal``. A near-orthonormal pose is sent verbatim — never
repaired, Gram-Schmidt'd or transposed — and its class is echoed in the failure
context so a kernel placement rejection stays actionable.
"""

from __future__ import annotations

import math
from typing import Any

#: The published admission tolerance, set by the measured kernel boundary. Both
#: layers use this exact value.
ADMISSION_TOLERANCE = 1e-7

#: BUG-133: ceiling for a caller-supplied ``rotation_tolerance``. It equals the
#: published default because the kernel rejected every tested residual above it;
#: a larger value would admit a pose Creo cannot place. ``native/assembly_pose.h``
#: mirrors this as ``assembly_max_admission_tolerance``.
MAX_ADMISSION_TOLERANCE = 1e-7

#: Classification only: at or below this residual the matrix is ``strict``.
NEAR_ORTHONORMAL_TOLERANCE = 1e-9

PRECISION_CLASSES = ("strict", "near_orthonormal", "invalid")

PRECISION_ADVICE = (
    "The pose passed admission within {tolerance} but is not strictly orthonormal "
    "(max |R*R^T-I| = {residual:.3g}). It was sent verbatim, not repaired. Creo 10 "
    "rejected every measured residual above 1e-7, so this pose is at the edge of "
    "what the kernel places; if it fails, rebuild the matrix from exact orthonormal "
    "values (for example rotation angles in degrees)."
)


def tolerance_text(tolerance: float) -> str:
    """Format a tolerance the way both layers quote it."""
    return "1e-7" if tolerance == ADMISSION_TOLERANCE else f"{tolerance:g}"


def validate_tolerance(tolerance: float | None) -> float:
    """Return the effective admission tolerance, refusing anything out of contract."""
    if tolerance is None:
        return ADMISSION_TOLERANCE
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        raise ValueError("rotation_tolerance must be a positive finite number")
    value = float(tolerance)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("rotation_tolerance must be a positive finite number")
    if value > MAX_ADMISSION_TOLERANCE:
        raise ValueError(
            f"rotation_tolerance must be at most "
            f"{tolerance_text(MAX_ADMISSION_TOLERANCE)}; Creo 10 rejected every measured "
            "residual above this bound (code -2 at ProAsmcompAssemble and "
            "ProAsmcompPositionSet), so a larger value would admit a pose the kernel cannot place"
        )
    return value


def orthogonality_residual(rotation: list[list[float]]) -> float:
    residual = 0.0
    try:
        for left in range(3):
            for right in range(3):
                dot = sum(rotation[left][k] * rotation[right][k] for k in range(3))
                residual = max(residual, abs(float(dot) - (1.0 if left == right else 0.0)))
    except (OverflowError, TypeError, ValueError):
        return math.inf
    return residual


def determinant(rotation: list[list[float]]) -> float:
    try:
        a, b, c = rotation
        return (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        )
    except (OverflowError, TypeError, ValueError):
        return math.nan


def admission_status(
    rotation: list[list[float]], tolerance: float = ADMISSION_TOLERANCE
) -> dict[str, Any]:
    """Return the admission numbers and the caller-facing classification."""
    residual = orthogonality_residual(rotation)
    try:
        det = float(determinant(rotation))
    except (OverflowError, TypeError, ValueError):
        det = math.nan
    accepted = (
        math.isfinite(residual)
        and math.isfinite(det)
        and residual <= tolerance
        and abs(det - 1.0) <= tolerance
    )
    if not accepted:
        precision = "invalid"
    elif residual <= NEAR_ORTHONORMAL_TOLERANCE:
        precision = "strict"
    else:
        precision = "near_orthonormal"
    return {
        "accepted": accepted,
        "orthogonality_residual": residual,
        "determinant": det,
        "determinant_error": abs(det - 1.0) if math.isfinite(det) else None,
        "tolerance": tolerance,
        "precision": precision,
        "advice": PRECISION_ADVICE.format(tolerance=tolerance_text(tolerance), residual=residual)
        if precision == "near_orthonormal"
        else None,
    }
