"""BUG-181: exact 2D curve intersection splitting and clamped B-spline subdivision.

When a coordinate-defined sketch contains interior intersections (for example,
B-splines crossing lines or other B-splines to carve multiple sub-regions, as
in Arm7-S7), an endpoint-only graph only sees the outer boundary. This module
finds pairwise intersections and T-junctions in sketch-local millimetres,
splits lines, arcs and clamped B-splines (via exact Boehm knot insertion) at
interior intersection parameters, and leaves unsplit entities untouched.
"""

from __future__ import annotations

import copy
import math
import re
from typing import Any

#: Minimum parametric distance from 0 or 1 to count as an interior split.
PARAM_EDGE_EPS = 1e-5
#: Distance threshold (mm) for accepting a refined curve-curve intersection or T-junction.
INTERSECT_TOL_MM = 1e-4
#: Minimum distance (mm) for a split sub-entity to be kept (filters degenerate slivers).
MIN_SUBENTITY_LEN_MM = 1e-5


def clamped_uniform_knots(count: int, degree: int) -> list[float]:
    """Return a standard clamped uniform knot vector on [0.0, 1.0]."""
    interior = count - degree - 1
    knots = [0.0] * (degree + 1)
    if interior > 0:
        step = 1.0 / (interior + 1)
        for idx in range(1, interior + 1):
            knots.append(idx * step)
    knots.extend([1.0] * (degree + 1))
    return knots


def _find_knot_span(n_ctrl: int, degree: int, u: float, knots: list[float]) -> int:
    """Return knot span index k such that knots[k] <= u < knots[k + 1]."""
    if u >= knots[n_ctrl]:
        return n_ctrl - 1
    if u <= knots[degree]:
        return degree
    low = degree
    high = n_ctrl
    mid = (low + high) // 2
    while u < knots[mid] or u >= knots[mid + 1]:
        if u < knots[mid]:
            high = mid
        else:
            low = mid
        mid = (low + high) // 2
    return mid


def eval_bspline(
    control_points: list[list[float]],
    degree: int,
    knots: list[float],
    u: float,
    weights: list[float] | None = None,
) -> tuple[float, float]:
    """Evaluate a clamped (optionally rational) 2D B-spline at parameter u."""
    n_ctrl = len(control_points)
    u_min = knots[degree]
    u_max = knots[n_ctrl]
    u = max(u_min, min(u_max, u))
    span = _find_knot_span(n_ctrl, degree, u, knots)
    if weights is not None:
        d = [
            [
                control_points[span - degree + j][0] * weights[span - degree + j],
                control_points[span - degree + j][1] * weights[span - degree + j],
                weights[span - degree + j],
            ]
            for j in range(degree + 1)
        ]
        for r in range(1, degree + 1):
            for j in range(degree, r - 1, -1):
                left = knots[span - degree + j]
                right = knots[span + 1 + j - r]
                denom = right - left
                alpha = 0.0 if denom == 0.0 else (u - left) / denom
                d[j] = [(1.0 - alpha) * d[j - 1][c] + alpha * d[j][c] for c in range(3)]
        w = d[degree][2]
        if abs(w) < 1e-15:
            return (d[degree][0], d[degree][1])
        return (d[degree][0] / w, d[degree][1] / w)

    d2 = [
        [control_points[span - degree + j][0], control_points[span - degree + j][1]]
        for j in range(degree + 1)
    ]
    for r in range(1, degree + 1):
        for j in range(degree, r - 1, -1):
            left = knots[span - degree + j]
            right = knots[span + 1 + j - r]
            denom = right - left
            alpha = 0.0 if denom == 0.0 else (u - left) / denom
            d2[j] = [
                (1.0 - alpha) * d2[j - 1][0] + alpha * d2[j][0],
                (1.0 - alpha) * d2[j - 1][1] + alpha * d2[j][1],
            ]
    return (d2[degree][0], d2[degree][1])


def _insert_knot_once(
    homog_pts: list[list[float]],
    degree: int,
    knots: list[float],
    u: float,
) -> tuple[list[list[float]], list[float]]:
    """Boehm's single knot insertion in homogeneous coordinates [wx, wy, w]."""
    n_ctrl = len(homog_pts)
    k = _find_knot_span(n_ctrl, degree, u, knots)
    new_knots = knots[: k + 1] + [u] + knots[k + 1 :]
    new_pts: list[list[float]] = []
    for i in range(n_ctrl + 1):
        if i <= k - degree:
            new_pts.append(list(homog_pts[i]))
        elif i >= k + 1:
            new_pts.append(list(homog_pts[i - 1]))
        else:
            denom = knots[i + degree] - knots[i]
            alpha = 0.0 if denom == 0.0 else (u - knots[i]) / denom
            prev_p = homog_pts[i - 1]
            curr_p = homog_pts[i]
            new_pts.append(
                [(1.0 - alpha) * prev_p[c] + alpha * curr_p[c] for c in range(len(curr_p))]
            )
    return new_pts, new_knots


def _normalize_knots(knots: list[float]) -> list[float]:
    u0, u1 = knots[0], knots[-1]
    span = u1 - u0
    if span <= 0.0:
        return [0.0 for _ in knots]
    return [(k - u0) / span for k in knots]


def split_bspline_at(
    control_points: list[list[float]],
    degree: int,
    knots: list[float],
    u_split: float,
    weights: list[float] | None = None,
) -> tuple[
    tuple[list[list[float]], list[float], list[float] | None],
    tuple[list[list[float]], list[float], list[float] | None],
]:
    """Split a clamped B-spline at interior knot value u_split via Boehm insertion."""
    if weights is not None:
        homog = [[pt[0] * w, pt[1] * w, w] for pt, w in zip(control_points, weights)]
    else:
        homog = [[pt[0], pt[1], 1.0] for pt in control_points]

    cur_pts = homog
    cur_knots = list(knots)
    mult = sum(1 for k in cur_knots if abs(k - u_split) <= 1e-12)
    insertions = max(0, degree - mult)
    for _ in range(insertions):
        cur_pts, cur_knots = _insert_knot_once(cur_pts, degree, cur_knots, u_split)

    # Locate the last index where cur_knots[idx] == u_split (within tol).
    split_indices = [idx for idx, k in enumerate(cur_knots) if abs(k - u_split) <= 1e-12]
    first_idx = split_indices[0]
    last_idx = split_indices[-1]

    # Left piece uses control points 0 .. first_idx - 1 (wait: for multiplicity p,
    # the split point is control point at index last_idx - degree).
    split_ctrl_idx = last_idx - degree
    left_homog = cur_pts[: split_ctrl_idx + 1]
    right_homog = cur_pts[split_ctrl_idx:]

    left_knots = cur_knots[:first_idx] + [u_split] * (degree + 1)
    right_knots = [u_split] * (degree + 1) + cur_knots[last_idx + 1 :]

    def unpack(hpts: list[list[float]]):
        if weights is not None:
            pts = [[p[0] / p[2], p[1] / p[2]] for p in hpts]
            ws = [p[2] for p in hpts]
            return pts, ws
        return [[p[0], p[1]] for p in hpts], None

    l_pts, l_w = unpack(left_homog)
    r_pts, r_w = unpack(right_homog)
    return (l_pts, _normalize_knots(left_knots), l_w), (
        r_pts,
        _normalize_knots(right_knots),
        r_w,
    )


def _arc_angles(entity: dict[str, Any]) -> tuple[float, float]:
    """Return (start_deg, signed_sweep_deg) for an arc entity."""
    start = float(entity["start_angle"])
    end = float(entity["end_angle"])
    direction = entity.get("dir", "ccw")
    if direction == "cw":
        sweep = (end - start) % 360.0
        if sweep == 0.0:
            sweep = 360.0
        sweep = sweep - 360.0
    else:
        sweep = (end - start) % 360.0
        if sweep == 0.0:
            sweep = 360.0
    return start, sweep


def _eval_entity(entity: dict[str, Any], t: float) -> tuple[float, float]:
    """Evaluate a supported open entity at normalized parameter t in [0, 1]."""
    kind = entity.get("type")
    t = max(0.0, min(1.0, t))
    if kind in ("line", "centerline"):
        a, b = entity["start"], entity["end"]
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
    if kind == "arc":
        cx, cy = entity["center"]
        r = float(entity["radius"])
        start, sweep = _arc_angles(entity)
        ang = math.radians(start + t * sweep)
        return (cx + r * math.cos(ang), cy + r * math.sin(ang))
    if kind == "b_spline":
        ctrl = entity["control_points"]
        degree = int(entity.get("degree", min(3, len(ctrl) - 1)))
        knots = entity.get("knots") or clamped_uniform_knots(len(ctrl), degree)
        weights = entity.get("weights")
        u0, u1 = knots[degree], knots[len(ctrl)]
        return eval_bspline(ctrl, degree, knots, u0 + t * (u1 - u0), weights)
    raise ValueError(f"Unsupported entity type for evaluation: {kind!r}")


def _sample_entity(entity: dict[str, Any]) -> list[tuple[float, float, float]]:
    """Sample an entity into [(t, x, y), ...] polyline points."""
    kind = entity.get("type")
    if kind in ("line", "centerline"):
        steps = 1
    elif kind == "arc":
        steps = 48
    elif kind == "b_spline":
        steps = 64
    else:
        return []
    out: list[tuple[float, float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        x, y = _eval_entity(entity, t)
        out.append((t, x, y))
    return out


def _bbox(
    samples: list[tuple[float, float, float]], pad: float = INTERSECT_TOL_MM
) -> tuple[float, float, float, float]:
    xs = [p[1] for p in samples]
    ys = [p[2] for p in samples]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def _bboxes_overlap(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _seg_seg_intersect(
    p0: tuple[float, float],
    p1: tuple[float, float],
    q0: tuple[float, float],
    q1: tuple[float, float],
) -> tuple[float, float] | None:
    """Return local (alpha, beta) in [0, 1]^2 if segments p0-p1 and q0-q1 intersect."""
    dx1, dy1 = p1[0] - p0[0], p1[1] - p0[1]
    dx2, dy2 = q1[0] - q0[0], q1[1] - q0[1]
    denom = dx1 * dy2 - dy1 * dx2
    if abs(denom) < 1e-14:
        return None
    rx, ry = q0[0] - p0[0], q0[1] - p0[1]
    alpha = (rx * dy2 - ry * dx2) / denom
    beta = (rx * dy1 - ry * dx1) / denom
    if -1e-6 <= alpha <= 1.0 + 1e-6 and -1e-6 <= beta <= 1.0 + 1e-6:
        return (max(0.0, min(1.0, alpha)), max(0.0, min(1.0, beta)))
    return None


def _refine_intersection(
    ent_a: dict[str, Any],
    ent_b: dict[str, Any],
    ta: float,
    tb: float,
    ta_lo: float,
    ta_hi: float,
    tb_lo: float,
    tb_hi: float,
) -> tuple[float, float, float]:
    """Refine (ta, tb) by damped Gauss-Newton + coordinate search; return (ta, tb, dist)."""
    a_cur, b_cur = ta, tb
    h = 1e-6
    for _ in range(16):
        pa = _eval_entity(ent_a, a_cur)
        pb = _eval_entity(ent_b, b_cur)
        rx, ry = pa[0] - pb[0], pa[1] - pb[1]
        dist = math.hypot(rx, ry)
        if dist < 1e-11:
            return (a_cur, b_cur, dist)
        # Finite-difference Jacobian of (pa(ta) - pb(tb))
        da_p = _eval_entity(ent_a, min(1.0, a_cur + h))
        da_m = _eval_entity(ent_a, max(0.0, a_cur - h))
        da_span = min(1.0, a_cur + h) - max(0.0, a_cur - h)
        db_p = _eval_entity(ent_b, min(1.0, b_cur + h))
        db_m = _eval_entity(ent_b, max(0.0, b_cur - h))
        db_span = min(1.0, b_cur + h) - max(0.0, b_cur - h)
        if da_span <= 0 or db_span <= 0:
            break
        j00 = (da_p[0] - da_m[0]) / da_span
        j10 = (da_p[1] - da_m[1]) / da_span
        j01 = -(db_p[0] - db_m[0]) / db_span
        j11 = -(db_p[1] - db_m[1]) / db_span
        det = j00 * j11 - j01 * j10
        if abs(det) < 1e-14:
            break
        step_a = -(j11 * rx - j01 * ry) / det
        step_b = -(-j10 * rx + j00 * ry) / det
        cand_a = max(ta_lo, min(ta_hi, a_cur + step_a))
        cand_b = max(tb_lo, min(tb_hi, b_cur + step_b))
        pa2 = _eval_entity(ent_a, cand_a)
        pb2 = _eval_entity(ent_b, cand_b)
        dist2 = math.hypot(pa2[0] - pb2[0], pa2[1] - pb2[1])
        if dist2 < dist:
            a_cur, b_cur = cand_a, cand_b
        else:
            break
    pa = _eval_entity(ent_a, a_cur)
    pb = _eval_entity(ent_b, b_cur)
    return (a_cur, b_cur, math.hypot(pa[0] - pb[0], pa[1] - pb[1]))


def _closest_param_on_entity(
    entity: dict[str, Any],
    samples: list[tuple[float, float, float]],
    pt: tuple[float, float],
) -> tuple[float, float]:
    """Find (t, dist) minimizing ||entity(t) - pt||."""
    best_idx = 0
    best_d2 = float("inf")
    for idx, (_, x, y) in enumerate(samples):
        d2 = (x - pt[0]) ** 2 + (y - pt[1]) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_idx = idx
    lo = samples[max(0, best_idx - 1)][0]
    hi = samples[min(len(samples) - 1, best_idx + 1)][0]
    # Golden-section search on [lo, hi]
    inv_phi = (math.sqrt(5.0) - 1.0) / 2.0
    for _ in range(36):
        c = hi - inv_phi * (hi - lo)
        d = lo + inv_phi * (hi - lo)
        pc = _eval_entity(entity, c)
        pd = _eval_entity(entity, d)
        dc = (pc[0] - pt[0]) ** 2 + (pc[1] - pt[1]) ** 2
        dd = (pd[0] - pt[0]) ** 2 + (pd[1] - pt[1]) ** 2
        if dc < dd:
            hi = d
        else:
            lo = c
    t_best = 0.5 * (lo + hi)
    p_best = _eval_entity(entity, t_best)
    return (t_best, math.hypot(p_best[0] - pt[0], p_best[1] - pt[1]))


def _sub_name(base: str, idx: int) -> str:
    clean = re.sub(r"[^a-z0-9_]", "_", str(base).lower()).lstrip("_") or "seg"
    if not clean[0].isalpha():
        clean = f"s_{clean}"
    suffix = f"_s{idx}"
    return f"{clean[: 28 - len(suffix)]}{suffix}"


def _split_one_entity(entity: dict[str, Any], raw_params: list[float]) -> list[dict[str, Any]]:
    """Split entity at interior parameters in (0, 1); return [entity] unchanged if none."""
    params = sorted(t for t in raw_params if PARAM_EDGE_EPS < t < 1.0 - PARAM_EDGE_EPS)
    dedup: list[float] = []
    for t in params:
        if not dedup or abs(t - dedup[-1]) > PARAM_EDGE_EPS:
            dedup.append(t)
    if not dedup:
        return [entity]

    kind = entity.get("type")
    base_name = str(entity.get("name", "seg"))
    cuts = [0.0, *dedup, 1.0]

    if kind in ("line", "centerline"):
        out: list[dict[str, Any]] = []
        for idx in range(len(cuts) - 1):
            p0 = list(_eval_entity(entity, cuts[idx]))
            p1 = list(_eval_entity(entity, cuts[idx + 1]))
            if math.dist(p0, p1) < MIN_SUBENTITY_LEN_MM:
                continue
            piece = copy.deepcopy(entity)
            piece["name"] = _sub_name(base_name, idx)
            piece["start"] = p0
            piece["end"] = p1
            out.append(piece)
        return out or [entity]

    if kind == "arc":
        start, sweep = _arc_angles(entity)
        r = float(entity["radius"])
        out = []
        for idx in range(len(cuts) - 1):
            a0 = start + cuts[idx] * sweep
            a1 = start + cuts[idx + 1] * sweep
            if abs(math.radians(a1 - a0)) * r < MIN_SUBENTITY_LEN_MM:
                continue
            piece = copy.deepcopy(entity)
            piece["name"] = _sub_name(base_name, idx)
            piece["start_angle"] = a0
            piece["end_angle"] = a1
            out.append(piece)
        return out or [entity]

    if kind == "b_spline":
        ctrl = copy.deepcopy(entity["control_points"])
        degree = int(entity.get("degree", min(3, len(ctrl) - 1)))
        knots = list(entity.get("knots") or clamped_uniform_knots(len(ctrl), degree))
        weights = list(entity["weights"]) if entity.get("weights") is not None else None
        # Iteratively split the remaining right piece from left to right.
        u_lo_orig = knots[degree]
        u_hi_orig = knots[len(ctrl)]
        u_cuts = [u_lo_orig + t * (u_hi_orig - u_lo_orig) for t in dedup]
        cur_ctrl, cur_knots, cur_weights = ctrl, knots, weights
        cur_u_start, cur_u_end = u_lo_orig, u_hi_orig
        pieces_data: list[tuple[list[list[float]], list[float], list[float] | None]] = []
        for u_target in u_cuts:
            span = cur_u_end - cur_u_start
            if span <= 1e-12:
                continue
            frac = (u_target - cur_u_start) / span
            if not (PARAM_EDGE_EPS < frac < 1.0 - PARAM_EDGE_EPS):
                continue
            k0, k1 = cur_knots[degree], cur_knots[len(cur_ctrl)]
            u_local = k0 + frac * (k1 - k0)
            left_part, right_part = split_bspline_at(
                cur_ctrl, degree, cur_knots, u_local, cur_weights
            )
            pieces_data.append(left_part)
            cur_ctrl, cur_knots, cur_weights = right_part
            cur_u_start = u_target
        pieces_data.append((cur_ctrl, _normalize_knots(cur_knots), cur_weights))

        out = []
        for idx, (p_ctrl, p_knots, p_weights) in enumerate(pieces_data):
            if math.dist(p_ctrl[0], p_ctrl[-1]) < MIN_SUBENTITY_LEN_MM and len(p_ctrl) <= 2:
                continue
            piece = copy.deepcopy(entity)
            piece["name"] = _sub_name(base_name, idx)
            piece["degree"] = degree
            piece["control_points"] = p_ctrl
            piece["knots"] = p_knots
            if p_weights is not None:
                piece["weights"] = p_weights
            out.append(piece)
        return out or [entity]

    return [entity]


def split_intersecting_entities(
    entities: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    """Return ``(working_entities, did_split)`` after splitting at interior intersections.

    When no interior intersections or T-junctions exist, returns ``(entities, False)``
    with every entity preserved unchanged.
    """
    splittable_types = {"line", "centerline", "arc", "b_spline"}
    indexed_samples: list[
        tuple[int, list[tuple[float, float, float]], tuple[float, float, float, float]]
    ] = []
    for idx, ent in enumerate(entities):
        if ent.get("construction"):
            continue
        if ent.get("type") not in splittable_types:
            continue
        samples = _sample_entity(ent)
        if len(samples) >= 2:
            indexed_samples.append((idx, samples, _bbox(samples)))

    if len(indexed_samples) < 2:
        return entities, False

    splits: dict[int, list[float]] = {}
    for pos_a in range(len(indexed_samples)):
        idx_a, samp_a, box_a = indexed_samples[pos_a]
        ent_a = entities[idx_a]
        for pos_b in range(pos_a + 1, len(indexed_samples)):
            idx_b, samp_b, box_b = indexed_samples[pos_b]
            if not _bboxes_overlap(box_a, box_b):
                continue
            ent_b = entities[idx_b]
            # 1) Segment-segment crossings
            for i in range(len(samp_a) - 1):
                ta0, ax0, ay0 = samp_a[i]
                ta1, ax1, ay1 = samp_a[i + 1]
                for j in range(len(samp_b) - 1):
                    tb0, bx0, by0 = samp_b[j]
                    tb1, bx1, by1 = samp_b[j + 1]
                    hit = _seg_seg_intersect((ax0, ay0), (ax1, ay1), (bx0, by0), (bx1, by1))
                    if hit is None:
                        continue
                    ta_init = ta0 + hit[0] * (ta1 - ta0)
                    tb_init = tb0 + hit[1] * (tb1 - tb0)
                    ta_ref, tb_ref, dist = _refine_intersection(
                        ent_a, ent_b, ta_init, tb_init, ta0, ta1, tb0, tb1
                    )
                    if dist <= INTERSECT_TOL_MM:
                        if PARAM_EDGE_EPS < ta_ref < 1.0 - PARAM_EDGE_EPS:
                            splits.setdefault(idx_a, []).append(ta_ref)
                        if PARAM_EDGE_EPS < tb_ref < 1.0 - PARAM_EDGE_EPS:
                            splits.setdefault(idx_b, []).append(tb_ref)
            # 2) T-junctions: endpoints of A on interior of B, and endpoints of B on interior of A
            for end_pt in ((samp_a[0][1], samp_a[0][2]), (samp_a[-1][1], samp_a[-1][2])):
                tb_c, dist = _closest_param_on_entity(ent_b, samp_b, end_pt)
                if dist <= INTERSECT_TOL_MM and PARAM_EDGE_EPS < tb_c < 1.0 - PARAM_EDGE_EPS:
                    splits.setdefault(idx_b, []).append(tb_c)
            for end_pt in ((samp_b[0][1], samp_b[0][2]), (samp_b[-1][1], samp_b[-1][2])):
                ta_c, dist = _closest_param_on_entity(ent_a, samp_a, end_pt)
                if dist <= INTERSECT_TOL_MM and PARAM_EDGE_EPS < ta_c < 1.0 - PARAM_EDGE_EPS:
                    splits.setdefault(idx_a, []).append(ta_c)

    if not splits:
        return entities, False

    result: list[dict[str, Any]] = []
    did_split = False
    for idx, ent in enumerate(entities):
        if idx in splits:
            pieces = _split_one_entity(ent, splits[idx])
            if len(pieces) > 1:
                did_split = True
            result.extend(pieces)
        else:
            result.append(ent)
    return result, did_split
