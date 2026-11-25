// BUG-130 offline official STL export wiring test. Real SDK declarations,
// substituted Toolkit calls. Never connects Creo.
#include "stl_export.h"

#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using stl_surface_detail::SurfaceUv;

static const char *tetrahedron = "solid exported\n"
                                 " facet normal 0 0 1\n"
                                 "  outer loop\n"
                                 "   vertex 0 0 0\n"
                                 "   vertex 1 0 0\n"
                                 "   vertex 0 1 0\n"
                                 "  endloop\n"
                                 " endfacet\n"
                                 " facet normal 0 1 0\n"
                                 "  outer loop\n"
                                 "   vertex 0 0 0\n"
                                 "   vertex 1 0 0\n"
                                 "   vertex 0 0 1\n"
                                 "  endloop\n"
                                 " endfacet\n"
                                 " facet normal 1 0 0\n"
                                 "  outer loop\n"
                                 "   vertex 0 0 0\n"
                                 "   vertex 0 1 0\n"
                                 "   vertex 0 0 1\n"
                                 "  endloop\n"
                                 " endfacet\n"
                                 " facet normal 1 1 1\n"
                                 "  outer loop\n"
                                 "   vertex 1 0 0\n"
                                 "   vertex 0 1 0\n"
                                 "   vertex 0 0 1\n"
                                 "  endloop\n"
                                 " endfacet\n"
                                 "endsolid exported\n";

static int allocations = 0, frees = 0;
static double passed[3] = {-1, -1, -1};
static int passed_flags = -1;
static ProError api_code = PRO_TK_NO_ERROR;
static ProError save_code = PRO_TK_NO_ERROR;
static ProError change_code = PRO_TK_NO_ERROR;
static ProError restore_code = PRO_TK_NO_ERROR;
static bool api_writes_file = true;
static std::string api_text = tetrahedron;
static bool in_staging = false;
static std::wstring current_directory = L"C:\\initial";

// Per-surface stubs: the SDK owns the arrays returned by the Get calls; the
// production code frees them, so the fake arrays are heap allocated too.
static int input_allocs = 0, input_frees = 0, tessellation_frees = 0;
static ProError tessellate_code = PRO_TK_NO_ERROR;
static ProError facets_code = PRO_TK_NO_ERROR;
static int surface_id_value = 42;
static bool body_active = true;
static bool collinear_vertices = false;
static bool invalid_facet_index = false;
static ProSolidBody *fake_bodies = nullptr;
static Pro3dPnt *fake_vertices = nullptr;
static ProTriangle *fake_facets = nullptr;
static ProVector *fake_normals = nullptr;
static ProUvParam *fake_params = nullptr;
static int fake_vertex_count = 3;
static int fake_facet_count = 1;

// Parameter-space refinement fixture: a 5x5 UV grid over a curved surface.
// The vertices sit exactly on that surface, so the UV round-trip self-check
// passes the way it does for a real tessellation.
static bool grid_mesh = false;
static double surface_curvature = 0.0;
static int uv_projection_sets = 0;
static int uv_projection_value = -1;

static double curved_height(double u, double v) {
    return surface_curvature * u * (1.0 - u) * v * (1.0 - v);
}

// Analytic normal of the curved fixture, so the refinement screen sees the
// same turn the surface really has.
static StlPoint curved_normal(double u, double v) {
    const double du = surface_curvature * (1.0 - 2.0 * u) * v * (1.0 - v);
    const double dv = surface_curvature * u * (1.0 - u) * (1.0 - 2.0 * v);
    const double length = std::sqrt(du * du + dv * dv + 1.0);
    return {-du / length, -dv / length, 1.0 / length};
}

static std::string fast_facet(const std::array<double, 3> &normal, const std::array<double, 3> &a,
                              const std::array<double, 3> &b, const std::array<double, 3> &c) {
    // The production writer is exercised through a stream, so the test
    // cannot drift away from the code it checks.
    std::ostringstream stream;
    stl_surface_detail::write_facet(stream, normal, a, b, c);
    return stream.str();
}

static void build_grid(std::vector<StlPoint> &points, std::vector<SurfaceUv> &uvs,
                       std::vector<StlTriangle> &faces) {
    const int n = 5;
    points.clear();
    uvs.clear();
    faces.clear();
    for (int j = 0; j < n; ++j) {
        for (int i = 0; i < n; ++i) {
            const double u = static_cast<double>(i) / 4.0;
            const double v = static_cast<double>(j) / 4.0;
            uvs.push_back({u, v});
            points.push_back({u, v, curved_height(u, v)});
        }
    }
    for (int j = 0; j < n - 1; ++j) {
        for (int i = 0; i < n - 1; ++i) {
            const int a = j * n + i, b = a + 1, c = a + n, d = c + 1;
            faces.push_back({a, b, d});
            faces.push_back({a, d, c});
        }
    }
}

static double max_chord_error(const std::vector<StlPoint> &points,
                              const std::vector<SurfaceUv> &uvs,
                              const std::vector<StlTriangle> &faces) {
    double worst = 0.0;
    for (const StlTriangle &face : faces) {
        const SurfaceUv centroid = {(uvs[face[0]][0] + uvs[face[1]][0] + uvs[face[2]][0]) / 3.0,
                                    (uvs[face[0]][1] + uvs[face[1]][1] + uvs[face[2]][1]) / 3.0};
        StlPoint evaluated = {0.0, 0.0, 0.0};
        if (!stl_surface_detail::evaluate_surface_uv(reinterpret_cast<ProSurface>(1), centroid,
                                                     evaluated))
            continue;
        const StlPoint &first = points[face[0]];
        const StlPoint normal =
            stl_surface_detail::safe_normal(first, points[face[1]], points[face[2]]);
        double offset = 0.0;
        for (int axis = 0; axis < 3; ++axis)
            offset += normal[axis] * (evaluated[axis] - first[axis]);
        worst = std::max(worst, std::abs(offset));
    }
    return worst;
}

ProError ProArrayAlloc(int n_objs, int obj_size, int, ProArray *array) {
    ++allocations;
    *array = std::malloc(static_cast<std::size_t>(n_objs) * static_cast<std::size_t>(obj_size));
    (void)obj_size;
    return PRO_TK_NO_ERROR;
}

ProError ProArrayFree(ProArray *array) {
    ++frees;
    std::free(*array);
    *array = nullptr;
    return PRO_TK_NO_ERROR;
}

ProError ProArraySizeGet(ProArray array, int *size) {
    if (array == static_cast<ProArray>(fake_bodies))
        *size = 1;
    else if (array == static_cast<ProArray>(fake_vertices))
        *size = fake_vertex_count;
    else if (array == static_cast<ProArray>(fake_facets))
        *size = fake_facet_count;
    else if (array == static_cast<ProArray>(fake_normals))
        *size = fake_vertex_count;
    else if (array == static_cast<ProArray>(fake_params))
        *size = fake_vertex_count;
    else
        return PRO_TK_BAD_INPUTS;
    return PRO_TK_NO_ERROR;
}

ProError ProSolidBodiesCollect(ProSolid, ProSolidBody **bodies) {
    fake_bodies = static_cast<ProSolidBody *>(std::calloc(1, sizeof(ProSolidBody)));
    if (!fake_bodies)
        return PRO_TK_OUT_OF_MEMORY;
    *bodies = fake_bodies;
    return PRO_TK_NO_ERROR;
}

ProError ProSolidBodyStateGet(ProSolidBody *, ProSolidBodyState *state) {
    *state = body_active ? PRO_BODY_STATE_ACTIVE : PRO_BODY_STATE_NONE;
    return PRO_TK_NO_ERROR;
}

ProError ProSolidBodySurfaceVisit(ProSolidBody *,
                                  ProError (*callback)(ProSurface, ProError, ProAppData),
                                  ProAppData data) {
    return callback(reinterpret_cast<ProSurface>(1), PRO_TK_NO_ERROR, data);
}

ProError ProSurfaceIdGet(ProSurface, int *id) {
    *id = surface_id_value;
    return PRO_TK_NO_ERROR;
}

// Surface areas drive the refinement budget split. The fixture hands out a
// different area per surface so the proportional split can be tested.
static double surface_area_value = 100.0;
ProError ProSurfaceAreaEval(ProSurface, double *area) {
    *area = surface_area_value;
    return PRO_TK_NO_ERROR;
}

ProError ProSurfacetessellationinputAlloc(ProSurfaceTessellationInput *input) {
    ++input_allocs;
    *input = reinterpret_cast<ProSurfaceTessellationInput>(2);
    return PRO_TK_NO_ERROR;
}

ProError ProSurfacetessellationinputFree(ProSurfaceTessellationInput) {
    ++input_frees;
    return PRO_TK_NO_ERROR;
}

ProError ProSurfacetessellationinputChordheightSet(ProSurfaceTessellationInput, double) {
    return PRO_TK_NO_ERROR;
}

ProError ProSurfacetessellationinputAnglecontrolSet(ProSurfaceTessellationInput, double) {
    return PRO_TK_NO_ERROR;
}

ProError ProSurfacetessellationinputStepsizeSet(ProSurfaceTessellationInput, double) {
    return PRO_TK_NO_ERROR;
}

ProError ProSurfaceTessellationGet(ProSurface, ProSurfaceTessellationInput,
                                   ProTessellation *tessellation) {
    *tessellation =
        tessellate_code == PRO_TK_NO_ERROR ? reinterpret_cast<ProTessellation>(3) : nullptr;
    return tessellate_code;
}

ProError ProTessellationFree(ProTessellation) {
    ++tessellation_frees;
    return PRO_TK_NO_ERROR;
}

ProError ProTessellationVerticesGet(ProTessellation, Pro3dPnt **vertices) {
    std::vector<StlPoint> points;
    std::vector<SurfaceUv> uvs;
    std::vector<StlTriangle> faces;
    if (grid_mesh) {
        build_grid(points, uvs, faces);
        fake_vertex_count = static_cast<int>(points.size());
    }
    fake_vertices = static_cast<Pro3dPnt *>(
        std::malloc(static_cast<std::size_t>(fake_vertex_count) * sizeof(Pro3dPnt)));
    if (!fake_vertices)
        return PRO_TK_OUT_OF_MEMORY;
    if (grid_mesh) {
        for (int index = 0; index < fake_vertex_count; ++index)
            for (int axis = 0; axis < 3; ++axis)
                fake_vertices[index][axis] = points[index][axis];
    } else {
        for (int axis = 0; axis < 3; ++axis) {
            fake_vertices[0][axis] = 0.0;
            fake_vertices[1][axis] = axis == 0 ? 1.0 : 0.0;
            fake_vertices[2][axis] =
                collinear_vertices ? (axis == 0 ? 2.0 : 0.0) : (axis == 1 ? 1.0 : 0.0);
        }
    }
    *vertices = fake_vertices;
    return PRO_TK_NO_ERROR;
}

ProError ProTessellationFacetsGet(ProTessellation, ProTriangle **facets) {
    if (facets_code != PRO_TK_NO_ERROR)
        return facets_code;
    if (grid_mesh) {
        std::vector<StlPoint> points;
        std::vector<SurfaceUv> uvs;
        std::vector<StlTriangle> faces;
        build_grid(points, uvs, faces);
        fake_facet_count = static_cast<int>(faces.size());
        fake_facets = static_cast<ProTriangle *>(
            std::malloc(static_cast<std::size_t>(fake_facet_count) * sizeof(ProTriangle)));
        if (!fake_facets)
            return PRO_TK_OUT_OF_MEMORY;
        for (int index = 0; index < fake_facet_count; ++index)
            for (int corner = 0; corner < 3; ++corner)
                fake_facets[index][corner] = faces[index][corner];
        *facets = fake_facets;
        return PRO_TK_NO_ERROR;
    }
    fake_facets = static_cast<ProTriangle *>(std::malloc(sizeof(ProTriangle)));
    if (!fake_facets)
        return PRO_TK_OUT_OF_MEMORY;
    fake_facets[0][0] = 0;
    fake_facets[0][1] = 1;
    fake_facets[0][2] = invalid_facet_index ? 9 : 2;
    *facets = fake_facets;
    return PRO_TK_NO_ERROR;
}

ProError ProTessellationNormalsGet(ProTessellation, ProVector **normals) {
    fake_normals = static_cast<ProVector *>(
        std::malloc(static_cast<std::size_t>(fake_vertex_count) * sizeof(ProVector)));
    if (!fake_normals)
        return PRO_TK_OUT_OF_MEMORY;
    for (int index = 0; index < fake_vertex_count; ++index) {
        if (grid_mesh) {
            const StlPoint normal = curved_normal(static_cast<double>(index % 5) / 4.0,
                                                  static_cast<double>(index / 5) / 4.0);
            for (int axis = 0; axis < 3; ++axis)
                fake_normals[index][axis] = normal[axis];
            continue;
        }
        fake_normals[index][0] = 0.0;
        fake_normals[index][1] = 0.0;
        fake_normals[index][2] = 1.0;
    }
    *normals = fake_normals;
    return PRO_TK_NO_ERROR;
}

ProError ProTessellationParamsGet(ProTessellation, ProUvParam **params) {
    fake_params = static_cast<ProUvParam *>(
        std::malloc(static_cast<std::size_t>(fake_vertex_count) * sizeof(ProUvParam)));
    if (!fake_params)
        return PRO_TK_OUT_OF_MEMORY;
    if (grid_mesh) {
        std::vector<StlPoint> points;
        std::vector<SurfaceUv> uvs;
        std::vector<StlTriangle> faces;
        build_grid(points, uvs, faces);
        for (int index = 0; index < fake_vertex_count; ++index) {
            fake_params[index][0] = uvs[index][0];
            fake_params[index][1] = uvs[index][1];
        }
    } else {
        fake_params[0][0] = 0.0;
        fake_params[0][1] = 0.0;
        if (fake_vertex_count > 1) {
            fake_params[1][0] = 1.0;
            fake_params[1][1] = 0.0;
        }
        if (fake_vertex_count > 2) {
            fake_params[2][0] = 0.0;
            fake_params[2][1] = 1.0;
        }
    }
    *params = fake_params;
    return PRO_TK_NO_ERROR;
}

ProError ProSurfacetessellationinputUvprojectionSet(ProSurfaceTessellationInput,
                                                    ProSurfaceTessellationProjection projection,
                                                    ProCsysdata *) {
    ++uv_projection_sets;
    uv_projection_value = static_cast<int>(projection);
    return PRO_TK_NO_ERROR;
}

// Deviation sampling stubs: projecting the sample returns the same point, so
// the measured distance is exactly zero and the wiring is what gets tested.
static double sampled_point[3] = {0.0, 0.0, 0.0};
static int deviation_evals = 0;

ProError ProSurfaceParamEval(ProSolid, ProSurface, ProVector point, ProUvParam uv) {
    for (int axis = 0; axis < 3; ++axis)
        sampled_point[axis] = point[axis];
    uv[0] = 0.0;
    uv[1] = 0.0;
    return PRO_TK_NO_ERROR;
}

ProError ProSurfaceXyzdataEval(ProSurface, ProUvParam uv, ProVector xyz, ProVector[2], ProVector[3],
                               ProVector normal) {
    ++deviation_evals;
    if (surface_curvature > 0.0) {
        xyz[0] = uv[0];
        xyz[1] = uv[1];
        xyz[2] = curved_height(uv[0], uv[1]);
        const StlPoint surface_normal = curved_normal(uv[0], uv[1]);
        for (int axis = 0; axis < 3; ++axis)
            normal[axis] = surface_normal[axis];
    } else {
        for (int axis = 0; axis < 3; ++axis)
            xyz[axis] = sampled_point[axis];
        for (int axis = 0; axis < 3; ++axis)
            normal[axis] = 0.0;
    }
    return PRO_TK_NO_ERROR;
}

ProError ProDirectoryCurrentGet(ProPath path) {
    wcscpy_s(path, PRO_PATH_SIZE, current_directory.c_str());
    return save_code;
}

ProError ProDirectoryChange(ProPath path) {
    if (in_staging) {
        in_staging = false;
        current_directory = path;
        return restore_code;
    }
    const ProError code = change_code;
    if (code == PRO_TK_NO_ERROR) {
        current_directory = path;
        in_staging = true;
    }
    return code;
}

ProError ProIntfSliceFileWithOptionsMdlnameExport(ProMdl, ProMdlFileName name,
                                                  ProImportExportFile file_type, double *parameters,
                                                  int config_flags, ProMatrix, ProAsmcomppath *) {
    for (int index = 0; index < 3; ++index)
        passed[index] = parameters[index];
    passed_flags = config_flags;
    assert(file_type == PRO_SLA_ASCII_FILE);
    if (api_code == PRO_TK_NO_ERROR && api_writes_file) {
        std::ofstream out(fs::path(current_directory) / name, std::ios::binary);
        out << api_text;
    }
    return api_code;
}

static void reset() {
    allocations = frees = 0;
    passed[0] = passed[1] = passed[2] = -1;
    passed_flags = -1;
    api_code = save_code = change_code = restore_code = PRO_TK_NO_ERROR;
    api_writes_file = true;
    api_text = tetrahedron;
    current_directory = L"C:\\initial";
    in_staging = false;
    input_allocs = input_frees = tessellation_frees = 0;
    tessellate_code = facets_code = PRO_TK_NO_ERROR;
    surface_id_value = 42;
    body_active = true;
    collinear_vertices = false;
    invalid_facet_index = false;
    fake_bodies = nullptr;
    fake_vertices = nullptr;
    fake_facets = nullptr;
    fake_normals = nullptr;
    deviation_evals = 0;
    fake_params = nullptr;
    fake_vertex_count = 3;
    fake_facet_count = 1;
    grid_mesh = false;
    surface_curvature = 0.0;
    uv_projection_sets = 0;
    uv_projection_value = -1;
    surface_area_value = 100.0;
}

int main() {
    const fs::path root = fs::temp_directory_path() / "mechdog_stl_export_test";
    std::error_code ignored;
    fs::remove_all(root, ignored);
    fs::create_directories(root / "staging");
    fs::create_directories(root / "output");
    const fs::path destination = root / "output" / "part.stl";
    const fs::path staging = root / "staging";

    reset();
    StlExportReport report =
        write_stl_file(nullptr, destination, staging, L"stl_0.stl", StlExportOptions{}, 1.0);
    assert(report.success && report.published);
    assert(report.file.facet_count == 4 && report.file.bytes > 0);
    assert(allocations == 1 && frees == 1);
    assert(passed[0] == 0.05 && passed[1] == 0.1 && passed[2] == 0.0);
    assert(passed_flags == PRO_FACET_STEP_SIZE_OFF);
    assert(report.directory_restore_code == PRO_TK_NO_ERROR);
    assert(current_directory == L"C:\\initial");
    assert(!fs::exists(staging / "stl_0.stl"));
    assert(fs::is_regular_file(destination));

    // The ASCII writer keeps the coordinates within its 15-digit precision.
    {
        const std::vector<std::array<double, 3>> values = {
            {0.0, 0.0, 1.0},
            {1.0, -2.0, 3.5},
            {-0.000123456789012, 1.0e-7, 12345.6789},
            {78095.063, -1817.98, -6600.001},
            {1.0 / 3.0, 2.0 / 3.0, 1e-300},
            {0.1, 0.2, 0.3},
            {-1.0e-9, 1.0e9, 6.02214076e23},
            {0.0, -0.0, 123456789.123456},
        };
        // Four coordinate triples per facet: the normal and the corners.
        for (std::size_t index = 0; index + 4 <= values.size(); index += 4) {
            const std::array<double, 3> normal = values[index];
            const std::array<double, 3> a = values[index + 1];
            const std::array<double, 3> b = values[index + 2];
            const std::array<double, 3> c = values[index + 3];
            const std::string fast = fast_facet(normal, a, b, c);
            std::istringstream input(fast);
            std::string keyword;
            input >> keyword;
            assert(keyword == "facet");
            const auto check_coordinates = [&input, &keyword](const char *label,
                                                              const StlPoint &expected) {
                input >> keyword;
                assert(keyword == label);
                for (double component : expected) {
                    double measured = 0.0;
                    assert(input >> measured);
                    assert(std::abs(measured - component) <= 5.0e-15 * std::abs(component));
                }
            };
            check_coordinates("normal", normal);
            input >> keyword;
            assert(keyword == "outer");
            input >> keyword;
            assert(keyword == "loop");
            check_coordinates("vertex", a);
            check_coordinates("vertex", b);
            check_coordinates("vertex", c);
            input >> keyword;
            assert(keyword == "endloop");
            input >> keyword;
            assert(keyword == "endfacet");
        }
    }

    // The requested millimeter chord height is converted into the model's
    // native unit; it is never passed as bare millimeters.
    reset();
    fs::remove(destination);
    report = write_stl_file(nullptr, destination, staging, L"stl_0.stl", StlExportOptions{}, 25.4);
    assert(report.success);
    assert(passed[0] == 0.05 / 25.4);

    // Unknown units must not be guessed.
    reset();
    fs::remove(destination);
    report = write_stl_file(nullptr, destination, staging, L"stl_0.stl", StlExportOptions{}, 0.0);
    assert(!report.success && report.error.find("length unit") != std::string::npos);
    assert(allocations == 0 && !fs::exists(destination));

    StlExportOptions bad_angle;
    bad_angle.angle_control = 1.5;
    report = write_stl_file(nullptr, destination, staging, L"stl_0.stl", bad_angle, 1.0);
    assert(!report.success && allocations == 0);

    StlExportOptions bad_chord;
    bad_chord.chord_height_mm = 0.0;
    report = write_stl_file(nullptr, destination, staging, L"stl_0.stl", bad_chord, 1.0);
    assert(!report.success && allocations == 0);

    // SDK failure: the parameter array is still freed, the directory is
    // restored and nothing is published.
    reset();
    api_code = PRO_TK_GENERAL_ERROR;
    report = write_stl_file(nullptr, destination, staging, L"stl_0.stl", StlExportOptions{}, 1.0);
    assert(!report.success && report.api_code == PRO_TK_GENERAL_ERROR);
    assert(allocations == 1 && frees == 1);
    assert(report.directory_restore_code == PRO_TK_NO_ERROR);
    assert(!fs::exists(destination));

    // API success without a file is still a failure.
    reset();
    api_writes_file = false;
    report = write_stl_file(nullptr, destination, staging, L"stl_0.stl", StlExportOptions{}, 1.0);
    assert(!report.success && !report.staging_file_written);
    assert(allocations == 1 && frees == 1 && !fs::exists(destination));

    // An empty or invalid staging file fails validation and is not published.
    reset();
    api_text.clear();
    report = write_stl_file(nullptr, destination, staging, L"stl_0.stl", StlExportOptions{}, 1.0);
    assert(!report.success && !report.file_error.empty());
    assert(fs::is_regular_file(staging / "stl_0.stl"));

    // Existing destinations are never overwritten.
    reset();
    std::ofstream(destination) << "user file";
    report = write_stl_file(nullptr, destination, staging, L"stl_0.stl", StlExportOptions{}, 1.0);
    assert(!report.success && report.error.find("already exists") != std::string::npos);
    assert(fs::file_size(destination) == 9);
    fs::remove(destination);

    // Directory failures are reported without allocating or exporting.
    reset();
    change_code = PRO_TK_BAD_INPUTS;
    report = write_stl_file(nullptr, destination, staging, L"stl_0.stl", StlExportOptions{}, 1.0);
    assert(!report.success && report.directory_change_code == PRO_TK_BAD_INPUTS);
    assert(allocations == 0 && !fs::exists(destination));

    reset();
    save_code = PRO_TK_BAD_INPUTS;
    report = write_stl_file(nullptr, destination, staging, L"stl_0.stl", StlExportOptions{}, 1.0);
    assert(!report.success && report.directory_save_code == PRO_TK_BAD_INPUTS && allocations == 0);

    // A restore failure is recorded and blocks publication.
    reset();
    change_code = PRO_TK_NO_ERROR;
    restore_code = PRO_TK_BAD_INPUTS;
    report = write_stl_file(nullptr, destination, staging, L"stl_0.stl", StlExportOptions{}, 1.0);
    assert(!report.success && report.directory_restore_code == PRO_TK_BAD_INPUTS);
    assert(!fs::exists(destination));

    // Per-surface path: one active body, one surface, one borrowed triangle.
    reset();
    StlExportOptions per_surface;
    per_surface.method = StlExportMethod::per_surface;
    per_surface.stitch_seams = false;
    StlPerSurfaceReport surface_report =
        write_stl_per_surface(nullptr, destination, staging, L"ps_0.stl", per_surface, 1.0);
    assert(surface_report.success && surface_report.published);
    assert(surface_report.surface_count == 1 && surface_report.facet_count == 1);
    assert(surface_report.file.facet_count == 1 && surface_report.file.bytes > 0);
    assert(surface_report.zero_area_facets == 0);
    assert(surface_report.surface_facets.size() == 1);
    assert(surface_report.surface_facets[0].first == 42);
    assert(surface_report.surface_facets[0].second == 1);
    assert(input_allocs == 1 && input_frees == 1 && tessellation_frees == 1);
    assert(frees == 4); // bodies + vertices + facets + normals; no UV array below the gate
    assert(uv_projection_sets == 1 && uv_projection_value == PRO_SRFTESS_NO_PROJECTION);
    assert(surface_report.refine_enabled && surface_report.refined_surfaces == 0);
    assert(fs::is_regular_file(destination));

    // Zero-area facets are counted explicitly and do not fail the surface.
    reset();
    fs::remove(destination);
    collinear_vertices = true;
    surface_report =
        write_stl_per_surface(nullptr, destination, staging, L"ps_0.stl", per_surface, 1.0);
    assert(surface_report.success && surface_report.zero_area_facets == 1);

    // Bad indices reject the whole export before any coordinate is written.
    reset();
    fs::remove(destination);
    invalid_facet_index = true;
    surface_report =
        write_stl_per_surface(nullptr, destination, staging, L"ps_0.stl", per_surface, 1.0);
    assert(!surface_report.success);
    assert(surface_report.failed_surface_id == 42 && surface_report.failed_facet_index == 0);
    assert(surface_report.failed_indices == "0,1,9");
    assert(surface_report.failed_stage == "mesh_check");
    assert(input_frees == 1 && tessellation_frees == 1 && frees == 4);
    assert(!fs::exists(destination));

    // Incomplete tessellation is a hard failure, not a partial mesh.
    reset();
    tessellate_code = PRO_TK_INCOMPLETE_TESS;
    surface_report =
        write_stl_per_surface(nullptr, destination, staging, L"ps_0.stl", per_surface, 1.0);
    assert(!surface_report.success && surface_report.failed_stage == "tessellate");
    assert(input_frees == 1 && tessellation_frees == 0 && frees == 1);
    assert(!fs::exists(destination));

    // A facets query failure still frees the input, vertices and tessellation.
    reset();
    facets_code = PRO_TK_GENERAL_ERROR;
    surface_report =
        write_stl_per_surface(nullptr, destination, staging, L"ps_0.stl", per_surface, 1.0);
    assert(!surface_report.success && surface_report.failed_stage == "facets_get");
    assert(input_frees == 1 && tessellation_frees == 1 && frees == 3);
    assert(!fs::exists(destination));

    // No active bodies is not a successful empty STL.
    reset();
    body_active = false;
    surface_report =
        write_stl_per_surface(nullptr, destination, staging, L"ps_0.stl", per_surface, 1.0);
    assert(!surface_report.success &&
           surface_report.error.find("no active solid") != std::string::npos);
    assert(frees == 1 && !fs::exists(destination));

    // The explicit facet budget rejects the surface without publishing.
    reset();
    StlOutputLimits no_facets;
    no_facets.max_facets = 0;
    surface_report = write_stl_per_surface(nullptr, destination, staging, L"ps_0.stl", per_surface,
                                           1.0, no_facets);
    assert(!surface_report.success && surface_report.failed_stage == "mesh_check");
    assert(surface_report.error.find("budget") != std::string::npos);
    assert(!fs::exists(destination));

    // Optional deviation sampling projects triangle-interior samples back to
    // the native surface and reports the measured distance.
    reset();
    fs::remove(destination);
    _putenv_s("MECHDOG_STL_DEVIATION", "1");
    surface_report =
        write_stl_per_surface(nullptr, destination, staging, L"ps_0.stl", per_surface, 1.0);
    _putenv_s("MECHDOG_STL_DEVIATION", "");
    assert(surface_report.success && surface_report.deviation_requested);
    assert(surface_report.deviation_samples == 4 && surface_report.deviation_failed == 0);
    assert(surface_report.deviation_max_mm == 0.0 && surface_report.deviation_mean_mm == 0.0);
    assert(surface_report.deviation_vertex_samples == 1);
    assert(surface_report.deviation_vertex_max_mm == 0.0);
    assert(deviation_evals == 5);

    // Parameter-space refinement (unit): the coarse 5x5 grid over a curved
    // surface is split until its measured chord error meets the target.
    reset();
    surface_curvature = 10.0;
    {
        std::vector<StlPoint> points;
        std::vector<SurfaceUv> uvs;
        std::vector<StlTriangle> faces;
        build_grid(points, uvs, faces);
        std::vector<StlPoint> vertex_normals;
        for (const SurfaceUv &uv : uvs)
            vertex_normals.push_back(curved_normal(uv[0], uv[1]));
        const double before = max_chord_error(points, uvs, faces);
        stl_surface_detail::RefineStats stats;
        std::uint64_t budget = 200000;
        stl_surface_detail::refine_surface_mesh(reinterpret_cast<ProSurface>(1), points,
                                                vertex_normals, uvs, faces, 0.005, 200000, budget,
                                                6, stats);
        const double after = max_chord_error(points, uvs, faces);
        assert(before > 0.05 && after <= before * 0.5);
        assert(after <= 0.005 + 1.0e-12);
        assert(stats.input_facets == 32 && faces.size() == stats.output_facets);
        assert(stats.levels >= 1 && !stats.limited && stats.rejected_edges == 0);
        assert(stats.pinned_triangles == 0 && stats.created_vertices > 0);

        // A single triangle has no interior edge; splitting it would open the
        // trim boundary, so it is reported as pinned instead of refined.
        std::vector<SurfaceUv> open_uvs = {{0.25, 0.25}, {0.5, 0.25}, {0.25, 0.5}};
        std::vector<StlPoint> open_points;
        std::vector<StlPoint> open_normals;
        for (const SurfaceUv &uv : open_uvs) {
            open_points.push_back({uv[0], uv[1], curved_height(uv[0], uv[1])});
            open_normals.push_back(curved_normal(uv[0], uv[1]));
        }
        std::vector<StlTriangle> open_faces = {{0, 1, 2}};
        std::uint64_t open_budget = 1000;
        stl_surface_detail::RefineStats pinned;
        stl_surface_detail::refine_surface_mesh(reinterpret_cast<ProSurface>(1), open_points,
                                                open_normals, open_uvs, open_faces, 0.005, 1000,
                                                open_budget, 6, pinned);
        assert(open_faces.size() == 1 && pinned.pinned_triangles >= 1);
    }

    // Refinement respects its output cap and reports the truncation.
    reset();
    surface_curvature = 10.0;
    {
        std::vector<StlPoint> points;
        std::vector<SurfaceUv> uvs;
        std::vector<StlTriangle> faces;
        build_grid(points, uvs, faces);
        std::vector<StlPoint> vertex_normals;
        for (const SurfaceUv &uv : uvs)
            vertex_normals.push_back(curved_normal(uv[0], uv[1]));
        stl_surface_detail::RefineStats stats;
        std::uint64_t budget = 1000;
        stl_surface_detail::refine_surface_mesh(reinterpret_cast<ProSurface>(1), points,
                                                vertex_normals, uvs, faces, 0.005, 33, budget, 6,
                                                stats);
        assert(stats.limited && stats.levels == 0 && faces.size() == 32);
    }

    // The refinement budget follows the surface area, not the surface count.
    // A model with one large face and several small ones used to give every
    // face the same share, which cut the large face off before it reached
    // the target chord height.
    {
        using stl_surface_detail::allocate_refine_budget;
        using stl_surface_detail::claim_refine_budget;
        using stl_surface_detail::RefineSurfaceShare;
        std::vector<RefineSurfaceShare> shares(3);
        shares[0].surface_id = 119;
        shares[0].area = 900.0;
        shares[1].surface_id = 131;
        shares[1].area = 99.0;
        shares[2].surface_id = 166;
        shares[2].area = 1.0;
        allocate_refine_budget(shares, 250000);
        // The weights are the fractions of the model area.
        assert(shares[0].weight > 0.89 && shares[0].weight < 0.91);
        assert(shares[1].weight > 0.09 && shares[1].weight < 0.10);
        assert(shares[2].weight > 0.0009 && shares[2].weight < 0.0011);
        // The allowance follows the weight, so the large face may draw most
        // of the pool and the small face only a little.
        assert(shares[0].allowance == 225000);
        assert(shares[2].allowance == 250);
        // A surface draws at most its own allowance from the shared pool.
        // The first slice is limited, so the surface keeps the rest for the
        // rounds in which it still has triangles above the target.
        std::uint64_t pool = 250000;
        const std::uint64_t large = claim_refine_budget(shares[0], pool, 50000);
        assert(large == 50000);
        // The surface may draw more later, up to its own allowance.
        const std::uint64_t more = claim_refine_budget(shares[0], pool, 0);
        assert(more == 175000);
        // Drawing again does not hand out the same allowance twice.
        const std::uint64_t again = claim_refine_budget(shares[0], pool, 0);
        assert(again == 0);
        // A small surface may not draw more than its own share.
        const std::uint64_t small = claim_refine_budget(shares[2], pool, 0);
        assert(small == 250);
        // The pool keeps what the surfaces did not draw.
        assert(pool > 20000);

        // A surface whose area cannot be measured still gets a share, so one
        // unreadable surface does not block the export.
        std::vector<RefineSurfaceShare> mixed(2);
        mixed[0].surface_id = 1;
        mixed[0].area = 100.0;
        mixed[1].surface_id = 2;
        mixed[1].area = 0.0;
        allocate_refine_budget(mixed, 250000);
        assert(mixed[0].weight > 0.49 && mixed[0].weight < 0.51);
        assert(mixed[1].weight > 0.49 && mixed[1].weight < 0.51);
        assert(mixed[0].allowance == 125000);

        // When no area can be measured at all, every surface gets an equal
        // share.
        std::vector<RefineSurfaceShare> blind(3);
        for (std::size_t index = 0; index < blind.size(); ++index)
            blind[index].surface_id = static_cast<int>(index);
        allocate_refine_budget(blind, 250000);
        for (const RefineSurfaceShare &share : blind) {
            assert(share.weight > 0.32 && share.weight < 0.34);
            assert(share.allowance == 83333);
        }
    }

    // Both triangles keep the shared diagonal when its evaluated midpoint
    // lands beside an existing vertex. With the same input and no guard the
    // diagonal splits on both sides.
    {
        surface_curvature = 10.0;
        const std::vector<StlPoint> corners = {{0.0, 0.0, 0.0},
                                               {1.0, 0.0, 0.0},
                                               {1.0, 1.0, 0.0},
                                               {0.0, 1.0, 0.0},
                                               {0.503, 0.5, curved_height(0.5, 0.5)}};
        const std::vector<StlTriangle> original = {{0, 1, 2}, {0, 2, 3}};
        for (double spacing : {0.0, 0.008}) {
            std::vector<StlPoint> points = corners;
            std::vector<SurfaceUv> uvs = {{0, 0}, {1, 0}, {1, 1}, {0, 1}, {0.5, 0.5}};
            std::vector<StlPoint> normals(points.size(), {0.0, 0.0, 1.0});
            normals[0] = {1.0, 0.0, 0.0};
            std::vector<StlTriangle> faces = original;
            stl_surface_detail::RefineStats stats;
            std::uint64_t budget = 10;
            stl_surface_detail::refine_surface_mesh(reinterpret_cast<ProSurface>(1), points,
                                                    normals, uvs, faces, 0.01, 100, budget, 1,
                                                    stats, nullptr, 0, nullptr, 0.0, spacing);
            if (spacing == 0.0) {
                assert(stats.created_vertices == 1 && faces.size() == 4);
                assert(stats.remaining_candidates == 2);
                assert(stats.stop == stl_surface_detail::RefineStats::Stop::rounds);
            } else {
                assert(stats.rejected_edges == 1 && stats.created_vertices == 0);
                assert(faces == original && points == corners);
                assert(stats.remaining_candidates == 2);
                assert(stats.stop == stl_surface_detail::RefineStats::Stop::blocked);
            }
        }
    }

    // The export path refines a coarse surface it would otherwise write as is.
    reset();
    grid_mesh = true;
    surface_curvature = 10.0;
    {
        StlExportOptions refine_options;
        refine_options.method = StlExportMethod::per_surface;
        refine_options.stitch_seams = false;
        refine_options.refine_min_facets = 1;
        StlExportOptions fine_target = refine_options;
        fine_target.chord_height_mm = 0.005;
        fs::remove(destination);
        surface_report =
            write_stl_per_surface(nullptr, destination, staging, L"rf_0.stl", fine_target, 1.0);
        assert(surface_report.success);
        assert(surface_report.refine_enabled && surface_report.refined_surfaces == 1);
        assert(surface_report.refine_skipped_uv == 0);
        assert(surface_report.refine_skipped_uv_query == 0);
        assert(surface_report.refine_skipped_uv_mismatch == 0);
        assert(surface_report.refine_input_facets == 32);
        assert(surface_report.refine_output_facets > 32);
        assert(surface_report.refine_max_level >= 1);
        assert(surface_report.facet_count == surface_report.refine_output_facets);
        assert(surface_report.file.facet_count == surface_report.refine_output_facets);
        assert(surface_report.surface_facets.size() == 1);
        assert(surface_report.surface_facets[0].second == surface_report.refine_output_facets);
        assert(surface_report.refine_zero_area_facets == 0);
        assert(frees == 5);
    }

    fs::remove_all(root, ignored);
    std::puts("STL_EXPORT_OK cases=27; substituted SDK calls; no Toolkit connection");
    return 0;
}
