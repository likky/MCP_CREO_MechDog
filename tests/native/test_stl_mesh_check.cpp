// BUG-130 offline per-surface mesh validation. No Toolkit, no Creo connection.
#include "stl_mesh_check.h"

#include <cassert>
#include <cstdio>

static StlPoint vertices[] = {{0, 0, 0}, {1, 0, 0}, {0, 1, 0}, {0, 0, 1}};
static StlTriangle facets[] = {{0, 1, 2}, {0, 1, 3}};

static void accept(const StlPoint *v, int vc, const StlTriangle *f, int fc) {
    StlMeshBudget budget;
    const StlMeshCheck check = validate_mesh_view(v, vc, f, fc, 17, budget);
    assert(check.valid && check.reason.empty() && check.surface_id == 17);
}

static void reject(const StlPoint *v, int vc, const StlTriangle *f, int fc, const char *reason) {
    StlMeshBudget budget;
    const StlMeshCheck check = validate_mesh_view(v, vc, f, fc, 23, budget);
    assert(!check.valid && check.surface_id == 23);
    assert(check.reason.find(reason) != std::string::npos);
    assert(budget.accumulated_facets == 0);
}

int main() {
    accept(vertices, 4, facets, 2);

    // A collinear triangle is explicitly counted, not silently dropped.
    StlPoint line[] = {{0, 0, 0}, {1, 0, 0}, {2, 0, 0}};
    StlTriangle flat[] = {{0, 1, 2}};
    StlMeshBudget budget;
    StlMeshCheck check = validate_mesh_view(line, 3, flat, 1, 5, budget);
    assert(check.valid && budget.zero_area_facets == 1);

    reject(vertices, -1, facets, 2, "negative");
    reject(vertices, 4, facets, -1, "negative");
    reject(nullptr, 4, facets, 2, "null array");
    reject(vertices, 4, nullptr, 2, "null array");

    StlTriangle negative[] = {{0, 1, -1}};
    reject(vertices, 4, negative, 1, "out of range");
    StlTriangle high[] = {{0, 1, 4}};
    reject(vertices, 4, high, 1, "out of range");

    StlTriangle duplicate[] = {{0, 0, 2}};
    reject(vertices, 4, duplicate, 1, "repeats");

    StlPoint nan_vertices[] = {{0, 0, 0}, {1, 0, 0}, {0, 1, 0}};
    nan_vertices[1][2] = std::numeric_limits<double>::quiet_NaN();
    StlTriangle unit[] = {{0, 1, 2}};
    reject(nan_vertices, 3, unit, 1, "non-finite vertex");

    StlPoint inf_vertices[] = {{0, 0, 0}, {1, 0, 0}, {0, 1, 0}};
    inf_vertices[2][0] = std::numeric_limits<double>::infinity();
    reject(inf_vertices, 3, unit, 1, "non-finite vertex");

    StlPoint huge[] = {{0, 0, 0}, {1e308, 1e308, 0}, {1e308, 0, 1e308}};
    reject(huge, 3, unit, 1, "non-finite facet area");

    StlMeshBudget small;
    small.max_facets = 1;
    check = validate_mesh_view(vertices, 4, facets, 2, 9, small);
    assert(!check.valid && small.accumulated_facets == 0);

    StlMeshBudget accumulated;
    accumulated.max_facets = 3;
    assert(validate_mesh_view(vertices, 4, facets, 2, 9, accumulated).valid);
    assert(accumulated.accumulated_facets == 2);
    assert(!validate_mesh_view(vertices, 4, facets, 2, 10, accumulated).valid);
    assert(accumulated.accumulated_facets == 2);

    // Failure details retain the offending facet and indices.
    StlTriangle bad[] = {{0, 1, 9}};
    const StlMeshCheck detail = validate_mesh_view(vertices, 4, bad, 1, 31, accumulated);
    assert(!detail.valid && detail.facet_index == 0 && detail.indices[2] == 9);

    std::puts("STL_MESH_CHECK_OK cases=12; borrowed arrays; no Toolkit connection");
    return 0;
}
