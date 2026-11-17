// BUG-130: borrowed per-surface mesh validation.
//
// The per-surface route receives SDK-owned vertex/facet arrays. This header
// only borrows them: it never allocates, mutates or frees SDK data. It rejects
// invalid counts/indices/non-finite coordinates before any coordinate lookup
// and accounts for zero-area facets explicitly instead of silently skipping
// them.
#pragma once

#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <string>

using StlPoint = std::array<double, 3>;
using StlTriangle = std::array<int, 3>;

struct StlMeshCheck {
    bool valid = false;
    std::string reason;
    int surface_id = -1;
    int facet_index = -1;
    StlTriangle indices = {-1, -1, -1};
    bool zero_area = false;
};

struct StlMeshBudget {
    std::uint64_t max_facets = 2000000;
    std::uint64_t accumulated_facets = 0;
    std::uint64_t zero_area_facets = 0;
};

// Validates one surface's borrowed mesh. `budget` accumulates across surfaces
// and is only written after the whole surface passed; a rejected surface does
// not partially consume the budget.
inline StlMeshCheck validate_mesh_view(const StlPoint *vertices, int vertex_count,
                                       const StlTriangle *facets, int facet_count, int surface_id,
                                       StlMeshBudget &budget) {
    StlMeshCheck result;
    result.surface_id = surface_id;
    if (vertex_count < 0 || facet_count < 0) {
        result.reason = "negative vertex/facet count";
        return result;
    }
    if (vertex_count > 0 && !vertices) {
        result.reason = "non-zero vertex count with a null array";
        return result;
    }
    if (facet_count > 0 && !facets) {
        result.reason = "non-zero facet count with a null array";
        return result;
    }
    const std::uint64_t count = static_cast<std::uint64_t>(facet_count);
    if (count > budget.max_facets || budget.accumulated_facets > budget.max_facets - count) {
        result.reason = "facet budget exceeded";
        return result;
    }
    std::uint64_t zero_area = 0;
    for (int index = 0; index < facet_count; ++index) {
        const StlTriangle &facet = facets[index];
        const bool bad_index = facet[0] < 0 || facet[1] < 0 || facet[2] < 0 ||
                               facet[0] >= vertex_count || facet[1] >= vertex_count ||
                               facet[2] >= vertex_count;
        if (bad_index) {
            result.reason = "facet index out of range";
            result.facet_index = index;
            result.indices = facet;
            return result;
        }
        if (facet[0] == facet[1] || facet[1] == facet[2] || facet[0] == facet[2]) {
            result.reason = "facet repeats a vertex index";
            result.facet_index = index;
            result.indices = facet;
            return result;
        }
        const StlPoint &a = vertices[facet[0]];
        const StlPoint &b = vertices[facet[1]];
        const StlPoint &c = vertices[facet[2]];
        for (int axis = 0; axis < 3; ++axis) {
            if (!std::isfinite(a[axis]) || !std::isfinite(b[axis]) || !std::isfinite(c[axis])) {
                result.reason = "non-finite vertex coordinate";
                result.facet_index = index;
                result.indices = facet;
                return result;
            }
        }
        const double u[3] = {b[0] - a[0], b[1] - a[1], b[2] - a[2]};
        const double v[3] = {c[0] - a[0], c[1] - a[1], c[2] - a[2]};
        const double cross[3] = {u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
                                 u[0] * v[1] - u[1] * v[0]};
        const double area =
            0.5 * std::sqrt(cross[0] * cross[0] + cross[1] * cross[1] + cross[2] * cross[2]);
        if (!std::isfinite(area)) {
            result.reason = "non-finite facet area";
            result.facet_index = index;
            result.indices = facet;
            return result;
        }
        if (area <= 0.0)
            ++zero_area;
    }
    budget.accumulated_facets += count;
    budget.zero_area_facets += zero_area;
    result.indices = {-1, -1, -1};
    result.valid = true;
    return result;
}
