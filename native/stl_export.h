// BUG-130: official file-based STL export through the Toolkit slice API.
//
// The old worker path walked ProSurfaceTessellationData's nested pointers and
// hit an access violation when the SDK returned a non-zero facet count with a
// null facet array. This path asks Creo itself to write the ASCII STL, then
// validates and publishes the file. It never reads the tessellation arrays.
#pragma once

#include "stl_file_check.h"
#include "stl_mesh_check.h"

#include <ProSolidBody.h>
#include <ProSurface.h>
#include <ProUtil.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <functional>
#include <queue>
#include <sstream>
#include <string>
#include <system_error>
#include <unordered_map>
#include <utility>
#include <vector>

enum class StlExportMethod {
    official_file,
    per_surface
};

struct StlExportOptions {
    double chord_height_mm = 0.05;
    double angle_control = 0.1;
    // BUG-130: per-surface export is the default because the official
    // file exporter did not finish within the job budget on the 14m models.
    // The official path stays available for explicit diagnostics.
    StlExportMethod method = StlExportMethod::per_surface;
    bool stitch_seams = true;
    // BUG-130: the SDK stops refining a surface near 204k facets, so the
    // requested chord height is not reached on very large faces. Surfaces at
    // or above refine_min_facets are split in parameter space and re-sampled
    // until the measured chord height meets the requested value (bounded by
    // the facet caps below, which are reported, never silently applied).
    bool refine_capped_surfaces = true;
    std::uint64_t refine_min_facets = 2000;
    std::uint64_t refine_max_output_facets = 1500000;
    std::uint64_t refine_max_new_vertices = 250000;
    int refine_max_rounds = 6;

    void (*progress)(const char *) = nullptr;

    void stage(const char *name) const {
        if (progress)
            progress(name);
    }
};

struct StlExportReport {
    std::string method = "ProIntfSliceFileWithOptionsMdlnameExport";
    double requested_chord_height_mm = 0.0;
    double requested_angle_control = 0.0;
    double length_scale_to_mm = 0.0;
    double passed_chord_height_native = 0.0;
    double passed_angle_control = 0.0;
    double passed_step_size_native = 0.0;
    int config_flags = PRO_FACET_STEP_SIZE_OFF;
    ProError parameter_alloc_code = PRO_TK_NO_ERROR;
    ProError api_code = PRO_TK_NO_ERROR;
    ProError parameter_free_code = PRO_TK_NO_ERROR;
    ProError directory_save_code = PRO_TK_NO_ERROR;
    ProError directory_change_code = PRO_TK_NO_ERROR;
    ProError directory_restore_code = PRO_TK_NO_ERROR;
    bool staging_file_written = false;
    bool published = false;
    bool success = false;
    std::string error;
    std::string file_error;
    StlFileStats file;
};

namespace stl_export_detail {

inline bool to_pro_path(const std::filesystem::path &value, ProPath output) {
    const std::wstring text = value.wstring();
    if (text.empty() || text.size() >= PRO_PATH_SIZE)
        return false;
    wcscpy_s(output, PRO_PATH_SIZE, text.c_str());
    return true;
}

inline bool to_mdl_file_name(const std::wstring &value, ProMdlFileName output) {
    if (value.empty() || value.size() >= PRO_FILE_MDLNAME_SIZE)
        return false;
    wcscpy_s(output, PRO_FILE_MDLNAME_SIZE, value.c_str());
    return true;
}

struct DirectoryRestore {
    ProPath previous{};
    ProError code = PRO_TK_NO_ERROR;
    bool active = true;

    explicit DirectoryRestore(const ProPath value) {
        wcscpy_s(previous, PRO_PATH_SIZE, value);
    }
    ProError restore() {
        if (!active)
            return code;
        code = ProDirectoryChange(previous);
        active = false;
        return code;
    }
    ~DirectoryRestore() {
        restore();
    }
};

inline std::string publish(const std::filesystem::path &staging_file,
                           const std::filesystem::path &destination) {
    std::error_code exists_error;
    const bool exists = std::filesystem::exists(destination, exists_error);
    if (exists_error)
        return "cannot inspect the STL destination: " + exists_error.message();
    if (exists)
        return "the STL destination already exists: " + destination.string();
    std::error_code rename_error;
    std::filesystem::rename(staging_file, destination, rename_error);
    if (rename_error)
        return "cannot publish the STL file: " + rename_error.message();
    return {};
}

} // namespace stl_export_detail

// Exports one part to ASCII STL under a short staged name, validates the
// produced file and atomically publishes it to ``destination``. The model is
// only read; nothing is saved and the revision is not advanced. Any SDK, IO or
// validation failure leaves ``success`` false and never publishes a file.
inline StlExportReport write_stl_file(ProMdl model, const std::filesystem::path &destination,
                                      const std::filesystem::path &staging_directory,
                                      const std::wstring &staging_name,
                                      const StlExportOptions &options, double length_scale_to_mm,
                                      const StlOutputLimits &limits = {}) {
    using namespace stl_export_detail;
    StlExportReport report;
    report.requested_chord_height_mm = options.chord_height_mm;
    report.requested_angle_control = options.angle_control;
    report.length_scale_to_mm = length_scale_to_mm;
    if (!std::isfinite(length_scale_to_mm) || length_scale_to_mm <= 0.0) {
        report.error = "the model length unit scale is unknown; refusing to guess STL quality";
        return report;
    }
    if (!std::isfinite(options.chord_height_mm) || options.chord_height_mm <= 0.0) {
        report.error = "chord_height_mm must be a finite positive number";
        return report;
    }
    if (!std::isfinite(options.angle_control) || options.angle_control < 0.0 ||
        options.angle_control > 1.0) {
        report.error = "angle_control must be finite and within 0.0..1.0";
        return report;
    }
    report.passed_chord_height_native = options.chord_height_mm / length_scale_to_mm;
    report.passed_angle_control = options.angle_control;
    report.passed_step_size_native = 0.0;

    std::error_code directory_error;
    std::filesystem::create_directories(staging_directory, directory_error);
    if (directory_error) {
        report.error = "cannot create the STL staging directory: " + directory_error.message();
        return report;
    }
    const std::filesystem::path staging_file = staging_directory / staging_name;

    ProPath previous{}, target{};
    if (!to_pro_path(staging_directory, target)) {
        report.error = "the STL staging directory exceeds PRO_PATH_SIZE";
        return report;
    }
    report.directory_save_code = ProDirectoryCurrentGet(previous);
    if (report.directory_save_code != PRO_TK_NO_ERROR) {
        report.error = "cannot read the current Creo directory";
        return report;
    }
    DirectoryRestore restore{previous};
    report.directory_change_code = ProDirectoryChange(target);
    if (report.directory_change_code != PRO_TK_NO_ERROR) {
        report.error = "cannot enter the STL staging directory";
        report.directory_restore_code = restore.restore();
        return report;
    }

    ProArray parameters = nullptr;
    report.parameter_alloc_code = ProArrayAlloc(3, sizeof(double), 1, &parameters);
    if (report.parameter_alloc_code != PRO_TK_NO_ERROR || !parameters) {
        report.error = "cannot allocate the STL quality parameter array";
        report.directory_restore_code = restore.restore();
        return report;
    }
    double *values = static_cast<double *>(parameters);
    values[0] = report.passed_chord_height_native;
    values[1] = report.passed_angle_control;
    values[2] = report.passed_step_size_native;

    ProMdlFileName name{};
    if (!to_mdl_file_name(staging_name, name)) {
        report.error = "the staged STL file name exceeds PRO_FILE_MDLNAME_SIZE";
        report.parameter_free_code = ProArrayFree(&parameters);
        report.directory_restore_code = restore.restore();
        return report;
    }
    options.stage("stl_toolkit_export");
    report.api_code = ProIntfSliceFileWithOptionsMdlnameExport(
        model, name, PRO_SLA_ASCII_FILE, values, PRO_FACET_STEP_SIZE_OFF, nullptr, nullptr);
    report.parameter_free_code = ProArrayFree(&parameters);
    report.directory_restore_code = restore.restore();
    report.staging_file_written = std::filesystem::is_regular_file(staging_file);
    if (report.directory_restore_code != PRO_TK_NO_ERROR) {
        report.error = "cannot restore the Creo working directory";
        return report;
    }
    if (report.api_code != PRO_TK_NO_ERROR) {
        report.error = "ProIntfSliceFileWithOptionsMdlnameExport returned code " +
                       std::to_string(static_cast<int>(report.api_code));
        return report;
    }
    if (!report.staging_file_written) {
        report.error = "the export API reported success but wrote no staging file";
        return report;
    }
    options.stage("stl_validate_mesh");
    try {
        report.file = validate_ascii_stl(staging_file, limits);
    } catch (const StlFileError &error) {
        report.file_error = error.what();
        return report;
    }
    std::error_code output_error;
    std::filesystem::create_directories(destination.parent_path(), output_error);
    if (output_error) {
        report.error = "cannot create the STL output directory: " + output_error.message();
        return report;
    }
    options.stage("stl_publish_verified_mesh");
    const std::string publish_error = publish(staging_file, destination);
    if (!publish_error.empty()) {
        report.error = publish_error;
        return report;
    }
    report.published = true;
    report.success = true;
    return report;
}

struct StlPerSurfaceReport {
    std::string method = "ProSurfaceTessellationGet";
    double requested_chord_height_mm = 0.0;
    double requested_angle_control = 0.0;
    double length_scale_to_mm = 0.0;
    double passed_chord_height_native = 0.0;
    double passed_angle_control = 0.0;
    std::uint64_t surface_count = 0;
    std::uint64_t facet_count = 0;
    std::uint64_t zero_area_facets = 0;
    std::uint64_t normal_surfaces = 0;
    std::uint64_t normal_flipped_facets = 0;
    std::uint64_t stitched_triangles = 0;
    std::uint64_t inverted_stitch_facets = 0;
    std::uint64_t winding_flipped_facets = 0;
    std::uint64_t winding_conflicts = 0;
    double signed_volume_mm3 = 0.0;
    bool global_flipped = false;
    // Optional sampled distance from triangle interiors to the native surface
    // they were tessellated from (diagnostic, see MECHDOG_STL_DEVIATION).
    bool deviation_requested = false;
    std::uint64_t deviation_samples = 0;
    std::uint64_t deviation_failed = 0;
    double deviation_max_mm = 0.0;
    double deviation_mean_mm = 0.0;
    double deviation_p99_mm = 0.0;
    std::uint64_t deviation_vertex_samples = 0;
    double deviation_vertex_max_mm = 0.0;
    int deviation_worst_surface_id = -1;
    std::array<double, 3> deviation_worst_point = {0.0, 0.0, 0.0};
    // Parameter-space refinement of surfaces that the SDK tessellated coarser
    // than the requested chord height.
    bool refine_enabled = false;
    double refine_target_native = 0.0;
    std::uint64_t refined_surfaces = 0;
    std::uint64_t refine_input_facets = 0;
    std::uint64_t refine_output_facets = 0;
    std::uint64_t refine_created_vertices = 0;
    std::uint64_t refine_pinned_triangles = 0;
    std::uint64_t refine_rejected_edges = 0;
    std::uint64_t refine_skipped_uv = 0;
    std::uint64_t refine_skipped_uv_query = 0;
    std::uint64_t refine_skipped_uv_mismatch = 0;
    std::uint64_t refine_skipped_normals = 0;
    double refine_uv_max_mismatch = 0.0;
    double refine_max_estimated_sag = 0.0;
    std::uint64_t refine_limited_surfaces = 0;
    std::uint64_t refine_zero_area_facets = 0;
    int refine_max_level = 0;
    // Per-surface facet counts make a per-surface tessellation ceiling visible.
    std::vector<std::pair<int, std::uint64_t>> surface_facets;
    int failed_surface_id = -1;
    int failed_facet_index = -1;
    std::string failed_indices;
    std::string failed_stage;
    ProError failed_code = PRO_TK_NO_ERROR;
    bool staging_file_written = false;
    bool published = false;
    bool success = false;
    std::string error;
    std::string file_error;
    StlFileStats file;
};

namespace stl_surface_detail {

struct SurfaceInputGuard {
    ProSurfaceTessellationInput input = nullptr;
    ~SurfaceInputGuard() {
        if (input)
            ProSurfacetessellationinputFree(input);
    }
};

struct TessellationGuard {
    ProTessellation tessellation = nullptr;
    ~TessellationGuard() {
        if (tessellation)
            ProTessellationFree(tessellation);
    }
};

struct ProArrayGuard {
    ProArray array = nullptr;
    explicit ProArrayGuard(ProArray value) : array(value) {
    }
    ~ProArrayGuard() {
        if (array)
            ProArrayFree(&array);
    }
};

struct WeldKey {
    std::int64_t x = 0, y = 0, z = 0;
    bool operator==(const WeldKey &other) const {
        return x == other.x && y == other.y && z == other.z;
    }
};

struct WeldKeyHash {
    std::size_t operator()(const WeldKey &key) const {
        std::size_t value = static_cast<std::size_t>(key.x) * 73856093u;
        value ^= static_cast<std::size_t>(key.y) * 19349663u;
        value ^= static_cast<std::size_t>(key.z) * 83492791u;
        return value;
    }
};

struct BoundaryEdge {
    int count = 0;
    int first = 0;
    int second = 0;
    std::array<double, 3> normal = {0.0, 0.0, 0.0};
};

struct DeviationSample {
    ProSurface surface = nullptr;
    int surface_id = -1;
    std::array<double, 3> point = {0.0, 0.0, 0.0};
    // Tessellation vertices lie on the native surface by construction, so their
    // measured distance is a self-check of the projection API.
    bool vertex = false;
};

struct Context {
    std::ofstream *out = nullptr;
    double chord_height_native = 0.0;
    double angle_control = 0.1;
    StlMeshBudget budget;
    std::uint64_t surface_count = 0;
    std::uint64_t normal_surfaces = 0;
    std::uint64_t normal_flipped_facets = 0;
    std::uint64_t stitched_triangles = 0;
    std::uint64_t inverted_stitch_facets = 0;
    double signed_volume = 0.0;
    double weld_tolerance = 0.001;
    bool deviation_enabled = false;
    std::uint64_t deviation_seen = 0;
    // Projecting a sample point onto a trimmed B-spline surface is expensive
    // (tens of milliseconds), so only a small, deterministic subset of facets
    // is sampled: one facet per 500, four points each.
    std::uint64_t deviation_stride = 500;
    std::size_t deviation_limit = 8000;
    std::vector<DeviationSample> deviation_samples;
    std::vector<std::pair<int, std::uint64_t>> surface_facets;
    bool refine_enabled = false;
    double refine_target = 0.0;
    std::uint64_t refine_min_facets = 0;
    std::uint64_t refine_max_output_facets = 0;
    std::uint64_t refine_vertex_budget = 0;
    int refine_surface_total = 0;
    int refine_surfaces_seen = 0;
    int refine_max_rounds = 6;
    std::uint64_t refined_surfaces = 0;
    std::uint64_t refine_input_facets = 0;
    std::uint64_t refine_output_facets = 0;
    std::uint64_t refine_created_vertices = 0;
    std::uint64_t refine_pinned_triangles = 0;
    std::uint64_t refine_rejected_edges = 0;
    std::uint64_t refine_skipped_uv = 0;
    std::uint64_t refine_skipped_uv_query = 0;
    std::uint64_t refine_skipped_uv_mismatch = 0;
    std::uint64_t refine_skipped_normals = 0;
    double refine_uv_max_mismatch = 0.0;
    double refine_max_estimated_sag = 0.0;
    std::uint64_t refine_limited_surfaces = 0;
    int refine_max_level = 0;
    std::uint64_t refine_zero_area_facets = 0;
    std::unordered_map<WeldKey, int, WeldKeyHash> weld;
    std::vector<std::array<double, 3>> welded_points;
    std::vector<std::array<double, 3>> stitch_centers;
    std::unordered_map<std::uint64_t, BoundaryEdge> edges;
    int failed_surface_id = -1;
    int failed_facet_index = -1;
    std::string failed_indices;
    std::string failed_stage;
    ProError failed_code = PRO_TK_NO_ERROR;
    std::string error;
};

inline int weld_vertex(Context &context, const std::array<double, 3> &point) {
    const std::int64_t scale = static_cast<std::int64_t>(1.0 / context.weld_tolerance);
    const WeldKey key{static_cast<std::int64_t>(std::llround(point[0] * scale)),
                      static_cast<std::int64_t>(std::llround(point[1] * scale)),
                      static_cast<std::int64_t>(std::llround(point[2] * scale))};
    const auto found = context.weld.find(key);
    if (found != context.weld.end())
        return found->second;
    // Check the neighbouring cells so a coordinate on a cell boundary does not
    // create a duplicate vertex within the tolerance.
    for (int dx = -1; dx <= 1; ++dx) {
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dz = -1; dz <= 1; ++dz) {
                if (!dx && !dy && !dz)
                    continue;
                const auto neighbour =
                    context.weld.find(WeldKey{key.x + dx, key.y + dy, key.z + dz});
                if (neighbour == context.weld.end())
                    continue;
                const auto &other = context.welded_points[neighbour->second];
                if (std::abs(other[0] - point[0]) <= context.weld_tolerance &&
                    std::abs(other[1] - point[1]) <= context.weld_tolerance &&
                    std::abs(other[2] - point[2]) <= context.weld_tolerance)
                    return neighbour->second;
            }
        }
    }
    const int id = static_cast<int>(context.welded_points.size());
    context.welded_points.push_back(point);
    context.weld.emplace(key, id);
    return id;
}

inline bool weld_collision(const Context &context, const std::array<double, 3> &point) {
    for (const auto &other : context.welded_points) {
        if (std::abs(other[0] - point[0]) <= context.weld_tolerance &&
            std::abs(other[1] - point[1]) <= context.weld_tolerance &&
            std::abs(other[2] - point[2]) <= context.weld_tolerance)
            return true;
    }
    for (const auto &other : context.stitch_centers) {
        if (std::abs(other[0] - point[0]) <= context.weld_tolerance &&
            std::abs(other[1] - point[1]) <= context.weld_tolerance &&
            std::abs(other[2] - point[2]) <= context.weld_tolerance)
            return true;
    }
    return false;
}

inline std::uint64_t edge_key(int first, int second) {
    const std::uint64_t low = static_cast<std::uint64_t>(std::min(first, second));
    const std::uint64_t high = static_cast<std::uint64_t>(std::max(first, second));
    return (low << 32) | high;
}

inline bool write_facet(std::ofstream &out, const std::array<double, 3> &normal,
                        const std::array<double, 3> &a, const std::array<double, 3> &b,
                        const std::array<double, 3> &c) {
    out << "facet normal " << normal[0] << ' ' << normal[1] << ' ' << normal[2]
        << "\n outer loop\n";
    for (const std::array<double, 3> *point : {&a, &b, &c})
        out << "  vertex " << (*point)[0] << ' ' << (*point)[1] << ' ' << (*point)[2] << '\n';
    out << " endloop\nendfacet\n";
    return static_cast<bool>(out);
}

inline ProError fail(Context &context, int surface_id, const char *stage,
                     const std::string &message, ProError code) {
    context.failed_surface_id = surface_id;
    context.failed_stage = stage;
    context.failed_code = code;
    context.error = std::string(stage) + ": " + message;
    return code != PRO_TK_NO_ERROR ? code : PRO_TK_GENERAL_ERROR;
}

inline std::array<double, 3> safe_normal(const StlPoint &a, const StlPoint &b, const StlPoint &c) {
    const double u[3] = {b[0] - a[0], b[1] - a[1], b[2] - a[2]};
    const double v[3] = {c[0] - a[0], c[1] - a[1], c[2] - a[2]};
    const std::array<double, 3> cross = {u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
                                         u[0] * v[1] - u[1] * v[0]};
    const double length =
        std::sqrt(cross[0] * cross[0] + cross[1] * cross[1] + cross[2] * cross[2]);
    if (!std::isfinite(length) || length <= 0.0)
        return {0.0, 0.0, 0.0};
    return {cross[0] / length, cross[1] / length, cross[2] / length};
}

// --- Parameter-space refinement of a capped surface tessellation -------------
//
// ProSurfaceTessellationGet stops refining very large surfaces around 204k
// facets, so the requested chord height is not reached there. The tessellation
// carries the surface UV of every vertex (PRO_SRFTESS_NO_PROJECTION), which
// lets this path split triangles in parameter space and evaluate the exact
// surface point of each new vertex. Only interior edges are split: the trim
// boundary keeps the SDK vertices, so neighbouring surfaces still meet as
// before and the existing weld/stitch pass is unchanged.

struct RefineStats {
    std::uint64_t input_facets = 0;
    std::uint64_t output_facets = 0;
    std::uint64_t created_vertices = 0;
    std::uint64_t pinned_triangles = 0;
    std::uint64_t rejected_edges = 0;
    std::uint64_t zero_area_facets = 0;
    double max_estimated_sag = 0.0;
    int levels = 0;
    bool limited = false;
};

using SurfaceUv = std::array<double, 2>;

// Diagnostic hooks: the worker installs a log sink only when MECHDOG_STL_TRACE
// is set, so the offline tests stay silent and the live run can time each phase.
inline void (*trace_hook)(const char *) = nullptr;
inline std::uint64_t evaluation_count = 0;

inline void trace(const std::string &text) {
    if (trace_hook)
        trace_hook(text.c_str());
}

inline long long elapsed_ms(std::chrono::steady_clock::time_point start) {
    return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() -
                                                                 start)
        .count();
}

inline bool evaluate_surface_uv(ProSurface surface, const SurfaceUv &uv, StlPoint &xyz,
                                StlPoint *normal_out = nullptr) {
    ++evaluation_count;
    ProUvParam parameter = {uv[0], uv[1]};
    ProVector point = {0.0, 0.0, 0.0};
    ProVector deriv1[2] = {};
    ProVector deriv2[3] = {};
    ProVector normal = {0.0, 0.0, 0.0};
    if (ProSurfaceXyzdataEval(surface, parameter, point, deriv1, deriv2, normal) != PRO_TK_NO_ERROR)
        return false;
    for (int axis = 0; axis < 3; ++axis) {
        if (!std::isfinite(point[axis]))
            return false;
        xyz[axis] = point[axis];
        if (normal_out)
            (*normal_out)[axis] = std::isfinite(normal[axis]) ? normal[axis] : 0.0;
    }
    return true;
}

// Angle between two vertex normals, in radians; zero when either is missing.
inline double normal_angle(const StlPoint &a, const StlPoint &b) {
    const double length_a = std::sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]);
    const double length_b = std::sqrt(b[0] * b[0] + b[1] * b[1] + b[2] * b[2]);
    if (!(length_a > 0.0) || !(length_b > 0.0))
        return 0.0;
    double cosine = (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (length_a * length_b);
    cosine = std::max(-1.0, std::min(1.0, cosine));
    return std::acos(cosine);
}

inline double point_distance(const StlPoint &a, const StlPoint &b) {
    const double dx = a[0] - b[0], dy = a[1] - b[1], dz = a[2] - b[2];
    return std::sqrt(dx * dx + dy * dy + dz * dz);
}

inline double triangle_area(const StlPoint &a, const StlPoint &b, const StlPoint &c) {
    const double u[3] = {b[0] - a[0], b[1] - a[1], b[2] - a[2]};
    const double v[3] = {c[0] - a[0], c[1] - a[1], c[2] - a[2]};
    const double cross[3] = {u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
                             u[0] * v[1] - u[1] * v[0]};
    return 0.5 * std::sqrt(cross[0] * cross[0] + cross[1] * cross[1] + cross[2] * cross[2]);
}

// The tessellation error of a triangle is bounded by how far the surface
// bulges out of that triangle's plane.
inline double plane_distance(const StlPoint &point, const StlPoint &a, const StlPoint &b,
                             const StlPoint &c) {
    const double u[3] = {b[0] - a[0], b[1] - a[1], b[2] - a[2]};
    const double v[3] = {c[0] - a[0], c[1] - a[1], c[2] - a[2]};
    const double normal[3] = {u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
                              u[0] * v[1] - u[1] * v[0]};
    const double length =
        std::sqrt(normal[0] * normal[0] + normal[1] * normal[1] + normal[2] * normal[2]);
    if (!(length > 0.0))
        return 0.0;
    const double offset = (point[0] - a[0]) * normal[0] + (point[1] - a[1]) * normal[1] +
                          (point[2] - a[2]) * normal[2];
    return std::abs(offset) / length;
}

inline bool surface_uv_roundtrip_ok(ProSurface surface, const std::vector<StlPoint> &points,
                                    const std::vector<SurfaceUv> &uvs, double tolerance,
                                    double &worst) {
    worst = 0.0;
    if (points.size() != uvs.size() || points.empty())
        return false;
    const std::size_t step = std::max<std::size_t>(1, points.size() / 32);
    int checked = 0, failed = 0;
    for (std::size_t index = 0; index < points.size() && checked < 32; index += step) {
        StlPoint evaluated = {0.0, 0.0, 0.0};
        ++checked;
        if (!evaluate_surface_uv(surface, uvs[index], evaluated)) {
            ++failed;
            continue;
        }
        const double distance = point_distance(evaluated, points[index]);
        worst = std::max(worst, distance);
        if (distance > tolerance)
            ++failed;
    }
    // A parameterisation that does not round-trip would put refined vertices
    // somewhere else on the surface, so it is rejected instead of guessed.
    return checked > 0 && failed * 10 <= checked;
}

// Splitting is adaptive red-green refinement: a triangle over the target chord
// height splits every interior edge it has, and neighbours follow so no
// T-junction is left behind. Both adjacent triangles split a shared edge into
// the same two halves, keeping the surface mesh conforming.
inline void refine_surface_mesh(ProSurface surface, std::vector<StlPoint> &points,
                                std::vector<StlPoint> &vertex_normals, std::vector<SurfaceUv> &uvs,
                                std::vector<StlTriangle> &faces, double target,
                                std::uint64_t max_output_facets, std::uint64_t &vertex_budget,
                                int max_rounds, RefineStats &stats) {
    stats.input_facets = static_cast<std::uint64_t>(faces.size());
    for (int round = 0; round < max_rounds; ++round) {
        const auto round_start = std::chrono::steady_clock::now();
        if (vertex_budget == 0) {
            stats.limited = true;
            break;
        }
        std::unordered_map<std::uint64_t, int> uses;
        uses.reserve(faces.size() * 3);
        for (const StlTriangle &face : faces)
            for (int pair = 0; pair < 3; ++pair)
                ++uses[edge_key(face[pair], face[(pair + 1) % 3])];
        // The chord error is estimated from how far the vertex normals turn
        // across a triangle (sag ~ L * turn / 8). This needs no surface
        // evaluation at all: a Creo surface point costs about 0.3 ms here,
        // which rules out scanning 200k triangles per round.
        std::vector<std::pair<double, int>> order;
        order.reserve(faces.size());
        for (std::size_t index = 0; index < faces.size(); ++index) {
            const StlTriangle &face = faces[index];
            const double longest = std::max({point_distance(points[face[0]], points[face[1]]),
                                             point_distance(points[face[1]], points[face[2]]),
                                             point_distance(points[face[2]], points[face[0]])});
            const double turn =
                std::max({normal_angle(vertex_normals[face[0]], vertex_normals[face[1]]),
                          normal_angle(vertex_normals[face[1]], vertex_normals[face[2]]),
                          normal_angle(vertex_normals[face[2]], vertex_normals[face[0]])});
            // Estimated chord error: sag ~ L * turn / 8 for a triangle whose
            // vertex normals turn by `turn` across it.
            const double sag = 0.125 * longest * turn;
            if (!(sag > target))
                continue;
            stats.max_estimated_sag = std::max(stats.max_estimated_sag, sag);
            order.push_back({sag, static_cast<int>(index)});
        }
        if (order.empty())
            break;
        std::sort(order.begin(), order.end(),
                  [](const std::pair<double, int> &left, const std::pair<double, int> &right) {
                      return left.first > right.first;
                  });
        std::unordered_map<std::uint64_t, int> splits;
        std::uint64_t planned = 0;
        for (const auto &candidate : order) {
            const StlTriangle &face = faces[static_cast<std::size_t>(candidate.second)];
            bool interior = false;
            std::uint64_t needed = 0;
            for (int pair = 0; pair < 3; ++pair) {
                const std::uint64_t key = edge_key(face[pair], face[(pair + 1) % 3]);
                if (uses[key] != 2)
                    continue;
                interior = true;
                if (splits.find(key) == splits.end())
                    ++needed;
            }
            if (!interior) {
                // Nothing can be split without opening the trim boundary.
                ++stats.pinned_triangles;
                continue;
            }
            if (needed > vertex_budget - planned) {
                stats.limited = true;
                break;
            }
            for (int pair = 0; pair < 3; ++pair) {
                const std::uint64_t key = edge_key(face[pair], face[(pair + 1) % 3]);
                if (uses[key] == 2)
                    splits.emplace(key, -1);
            }
            planned += needed;
        }
        if (splits.empty())
            break;
        for (auto &entry : splits) {
            const int first = static_cast<int>(entry.first >> 32);
            const int second = static_cast<int>(entry.first & 0xffffffffu);
            const SurfaceUv midpoint = {(uvs[first][0] + uvs[second][0]) / 2.0,
                                        (uvs[first][1] + uvs[second][1]) / 2.0};
            const double length = point_distance(points[first], points[second]);
            StlPoint evaluated = {0.0, 0.0, 0.0};
            StlPoint evaluated_normal = {0.0, 0.0, 0.0};
            if (!evaluate_surface_uv(surface, midpoint, evaluated, &evaluated_normal) ||
                point_distance(evaluated, points[first]) > length * 0.75 + target ||
                point_distance(evaluated, points[second]) > length * 0.75 + target) {
                ++stats.rejected_edges;
                continue;
            }
            entry.second = static_cast<int>(points.size());
            points.push_back(evaluated);
            vertex_normals.push_back(evaluated_normal);
            uvs.push_back(midpoint);
            if (vertex_budget > 0)
                --vertex_budget;
            ++stats.created_vertices;
        }
        std::vector<StlTriangle> next;
        next.reserve(faces.size() + splits.size());
        std::uint64_t round_zero_area = 0;
        const auto split_of = [&splits](int first, int second) {
            const auto found = splits.find(edge_key(first, second));
            return found == splits.end() ? -1 : found->second;
        };
        for (const StlTriangle &face : faces) {
            const int first = face[0];
            const int second = face[1];
            const int third = face[2];
            const int m0 = split_of(first, second);
            const int m1 = split_of(second, third);
            const int m2 = split_of(third, first);
            const int count = (m0 >= 0 ? 1 : 0) + (m1 >= 0 ? 1 : 0) + (m2 >= 0 ? 1 : 0);
            const auto emit = [&points, &next, &round_zero_area](int a, int b, int c) {
                if (triangle_area(points[a], points[b], points[c]) <= 0.0)
                    ++round_zero_area;
                next.push_back({a, b, c});
            };
            if (count == 3) {
                emit(first, m0, m2);
                emit(m0, second, m1);
                emit(m2, m1, third);
                emit(m0, m1, m2);
            } else if (count == 2 && m0 >= 0 && m1 >= 0) {
                emit(first, m0, m1);
                emit(m0, second, m1);
                emit(first, m1, third);
            } else if (count == 2 && m1 >= 0 && m2 >= 0) {
                emit(first, second, m1);
                emit(first, m1, m2);
                emit(m2, m1, third);
            } else if (count == 2 && m0 >= 0 && m2 >= 0) {
                emit(first, m0, m2);
                emit(m0, second, m2);
                emit(second, third, m2);
            } else if (count == 1 && m0 >= 0) {
                emit(first, m0, third);
                emit(m0, second, third);
            } else if (count == 1 && m1 >= 0) {
                emit(first, second, m1);
                emit(first, m1, third);
            } else if (count == 1 && m2 >= 0) {
                emit(first, second, m2);
                emit(second, third, m2);
            } else {
                emit(first, second, third);
            }
        }
        trace("refine_round=" + std::to_string(round + 1) + " facets=" +
              std::to_string(faces.size()) + " candidates=" + std::to_string(order.size()) +
              " splits=" + std::to_string(splits.size()) + " next=" + std::to_string(next.size()) +
              " created=" + std::to_string(stats.created_vertices) + " evals=" +
              std::to_string(evaluation_count) + " ms=" + std::to_string(elapsed_ms(round_start)));
        if (next.size() <= faces.size())
            break;
        if (next.size() > max_output_facets) {
            stats.limited = true;
            break;
        }
        faces.swap(next);
        stats.zero_area_facets += round_zero_area;
        ++stats.levels;
    }
    stats.output_facets = static_cast<std::uint64_t>(faces.size());
}

inline ProError count_surface_callback(ProSurface, ProError status, ProAppData data) {
    if (status == PRO_TK_NO_ERROR && data)
        ++*static_cast<int *>(data);
    return PRO_TK_NO_ERROR;
}

inline ProError surface_callback(ProSurface surface, ProError status, ProAppData data) {
    Context &context = *static_cast<Context *>(data);
    const auto phase_start = std::chrono::steady_clock::now();
    if (status != PRO_TK_NO_ERROR)
        return fail(context, -1, "surface_status", "surface visit reported an error", status);
    int surface_id = -1;
    ProError code = ProSurfaceIdGet(surface, &surface_id);
    if (code != PRO_TK_NO_ERROR)
        return fail(context, -1, "surface_id", "cannot read the surface id", code);
    ProSurfaceTessellationInput input = nullptr;
    code = ProSurfacetessellationinputAlloc(&input);
    if (code != PRO_TK_NO_ERROR || !input)
        return fail(context, surface_id, "input_alloc", "cannot allocate tessellation input", code);
    SurfaceInputGuard input_guard{input};
    code = ProSurfacetessellationinputChordheightSet(input, context.chord_height_native);
    if (code != PRO_TK_NO_ERROR)
        return fail(context, surface_id, "chord_height", "cannot set the chord height", code);
    code = ProSurfacetessellationinputAnglecontrolSet(input, context.angle_control);
    if (code != PRO_TK_NO_ERROR)
        return fail(context, surface_id, "angle_control", "cannot set the angle control", code);
    code = ProSurfacetessellationinputStepsizeSet(input, 0.0);
    if (code != PRO_TK_NO_ERROR)
        return fail(context, surface_id, "step_size", "cannot disable the step size", code);
    // Refinement needs the surface UV of every tessellation vertex. The
    // no-projection mode returns the unmodified surface parameters, which
    // ProSurfaceXyzdataEval accepts.
    if (context.refine_enabled) {
        code =
            ProSurfacetessellationinputUvprojectionSet(input, PRO_SRFTESS_NO_PROJECTION, nullptr);
        if (code != PRO_TK_NO_ERROR)
            return fail(context, surface_id, "uv_projection",
                        "cannot request the surface UV parameters", code);
    }
    ProTessellation tessellation = nullptr;
    code = ProSurfaceTessellationGet(surface, input, &tessellation);
    if (code == PRO_TK_INCOMPLETE_TESS)
        return fail(context, surface_id, "tessellate",
                    "Creo reported an incomplete surface tessellation", code);
    if (code != PRO_TK_NO_ERROR || !tessellation)
        return fail(context, surface_id, "tessellate", "surface tessellation failed", code);
    TessellationGuard tessellation_guard{tessellation};
    trace("tess surface=" + std::to_string(surface_id) +
          " ms=" + std::to_string(elapsed_ms(phase_start)));

    Pro3dPnt *vertices = nullptr;
    code = ProTessellationVerticesGet(tessellation, &vertices);
    if (code != PRO_TK_NO_ERROR)
        return fail(context, surface_id, "vertices_get", "cannot read tessellation vertices", code);
    ProArrayGuard vertices_guard{(ProArray)vertices};
    int vertex_count = 0;
    code = ProArraySizeGet((ProArray)vertices, &vertex_count);
    if (code != PRO_TK_NO_ERROR)
        return fail(context, surface_id, "vertices_size", "cannot size tessellation vertices",
                    code);
    if (vertex_count <= 0)
        return PRO_TK_NO_ERROR;

    ProVector *normals = nullptr;
    code = ProTessellationNormalsGet(tessellation, &normals);
    ProArrayGuard normals_guard{(ProArray)normals};
    bool surface_normals = false;
    if (code == PRO_TK_NO_ERROR && normals) {
        int normal_count = 0;
        surface_normals = ProArraySizeGet((ProArray)normals, &normal_count) == PRO_TK_NO_ERROR &&
                          normal_count == vertex_count;
    }
    if (surface_normals)
        ++context.normal_surfaces;

    ProTriangle *facets = nullptr;
    code = ProTessellationFacetsGet(tessellation, &facets);
    if (code != PRO_TK_NO_ERROR)
        return fail(context, surface_id, "facets_get", "cannot read tessellation facets", code);
    ProArrayGuard facets_guard{(ProArray)facets};
    int facet_count = 0;
    code = ProArraySizeGet((ProArray)facets, &facet_count);
    if (code != PRO_TK_NO_ERROR)
        return fail(context, surface_id, "facets_size", "cannot size tessellation facets", code);
    trace("mesh surface=" + std::to_string(surface_id) +
          " vertices=" + std::to_string(vertex_count) + " facets=" + std::to_string(facet_count) +
          " ms=" + std::to_string(elapsed_ms(phase_start)));

    // Pro3dPnt and ProTriangle are exactly three doubles/ints; the std::array
    // view is borrowed and never mutated or freed through this pointer.
    const StlMeshCheck check = validate_mesh_view(
        reinterpret_cast<const StlPoint *>(vertices), vertex_count,
        reinterpret_cast<const StlTriangle *>(facets), facet_count, surface_id, context.budget);
    if (!check.valid) {
        context.failed_facet_index = check.facet_index;
        if (!check.indices.empty()) {
            context.failed_indices = std::to_string(check.indices[0]) + "," +
                                     std::to_string(check.indices[1]) + "," +
                                     std::to_string(check.indices[2]);
        }
        return fail(context, surface_id, "mesh_check", check.reason, PRO_TK_GENERAL_ERROR);
    }
    // Work on a copy: the SDK arrays stay borrowed, and the winding decided
    // from the SDK vertex normals is settled before refinement so every split
    // triangle inherits its parent's orientation.
    std::vector<StlPoint> points(reinterpret_cast<const StlPoint *>(vertices),
                                 reinterpret_cast<const StlPoint *>(vertices) + vertex_count);
    std::vector<StlTriangle> faces(reinterpret_cast<const StlTriangle *>(facets),
                                   reinterpret_cast<const StlTriangle *>(facets) + facet_count);
    if (surface_normals) {
        for (StlTriangle &face : faces) {
            const StlPoint &a = points[face[0]];
            const StlPoint &b = points[face[1]];
            const StlPoint &c = points[face[2]];
            const std::array<double, 3> normal = safe_normal(a, b, c);
            const double sum[3] = {normals[face[0]][0] + normals[face[1]][0] + normals[face[2]][0],
                                   normals[face[0]][1] + normals[face[1]][1] + normals[face[2]][1],
                                   normals[face[0]][2] + normals[face[1]][2] + normals[face[2]][2]};
            const double length = std::sqrt(sum[0] * sum[0] + sum[1] * sum[1] + sum[2] * sum[2]);
            if (length > 0.0 &&
                (normal[0] * sum[0] + normal[1] * sum[1] + normal[2] * sum[2]) < 0.0) {
                std::swap(face[1], face[2]);
                ++context.normal_flipped_facets;
            }
        }
    }
    const std::uint64_t input_facets = static_cast<std::uint64_t>(faces.size());
    // Split the remaining vertex budget across the surfaces still to visit, so
    // no single surface can starve the rest of the model.
    const int remaining_surfaces =
        std::max(1, context.refine_surface_total - context.refine_surfaces_seen);
    ++context.refine_surfaces_seen;
    if (context.refine_enabled && input_facets >= context.refine_min_facets) {
        const auto params_start = std::chrono::steady_clock::now();
        ProUvParam *params = nullptr;
        const ProError uv_code = ProTessellationParamsGet(tessellation, &params);
        ProArrayGuard params_guard{(ProArray)params};
        int param_count = 0;
        const bool have_uv = uv_code == PRO_TK_NO_ERROR && params &&
                             ProArraySizeGet((ProArray)params, &param_count) == PRO_TK_NO_ERROR &&
                             param_count == vertex_count;
        trace("params surface=" + std::to_string(surface_id) + " code=" +
              std::to_string(static_cast<int>(uv_code)) + " count=" + std::to_string(param_count) +
              " ms=" + std::to_string(elapsed_ms(params_start)));
        if (!have_uv) {
            ++context.refine_skipped_uv;
            ++context.refine_skipped_uv_query;
        } else if (!surface_normals) {
            // The refinement screen needs the SDK vertex normals.
            ++context.refine_skipped_normals;
        } else {
            std::vector<SurfaceUv> uvs(static_cast<std::size_t>(vertex_count));
            for (int index = 0; index < vertex_count; ++index)
                uvs[index] = {params[index][0], params[index][1]};
            std::vector<StlPoint> vertex_normals(static_cast<std::size_t>(vertex_count));
            for (int index = 0; index < vertex_count; ++index)
                for (int axis = 0; axis < 3; ++axis)
                    vertex_normals[static_cast<std::size_t>(index)][axis] = normals[index][axis];
            double mismatch = 0.0;
            // A UV round-trip error is also the placement error of a refined
            // vertex, so it must stay well below the chord height; a gross
            // parameterisation mistake (seam wrap) is far above it and is
            // rejected instead of refined.
            const double roundtrip_tolerance = std::max(1.0e-3, 0.25 * context.refine_target);
            const bool roundtrip_ok =
                surface_uv_roundtrip_ok(surface, points, uvs, roundtrip_tolerance, mismatch);
            context.refine_uv_max_mismatch = std::max(context.refine_uv_max_mismatch, mismatch);
            if (!roundtrip_ok) {
                ++context.refine_skipped_uv;
                ++context.refine_skipped_uv_mismatch;
            } else {
                const std::uint64_t remaining =
                    context.budget.max_facets > context.budget.accumulated_facets
                        ? context.budget.max_facets - context.budget.accumulated_facets
                        : 0;
                RefineStats refine_stats;
                std::uint64_t surface_budget =
                    context.refine_vertex_budget / static_cast<std::uint64_t>(remaining_surfaces);
                const std::uint64_t surface_budget_start = surface_budget;
                refine_surface_mesh(surface, points, vertex_normals, uvs, faces,
                                    context.refine_target,
                                    std::min(context.refine_max_output_facets, remaining),
                                    surface_budget, context.refine_max_rounds, refine_stats);
                const std::uint64_t spent = surface_budget_start - surface_budget;
                context.refine_vertex_budget -= std::min(context.refine_vertex_budget, spent);
                ++context.refined_surfaces;
                context.refine_input_facets += refine_stats.input_facets;
                context.refine_output_facets += refine_stats.output_facets;
                context.refine_created_vertices += refine_stats.created_vertices;
                context.refine_pinned_triangles += refine_stats.pinned_triangles;
                context.refine_rejected_edges += refine_stats.rejected_edges;
                context.refine_zero_area_facets += refine_stats.zero_area_facets;
                context.refine_max_level = std::max(context.refine_max_level, refine_stats.levels);
                context.refine_max_estimated_sag =
                    std::max(context.refine_max_estimated_sag, refine_stats.max_estimated_sag);
                if (refine_stats.limited)
                    ++context.refine_limited_surfaces;
                if (refine_stats.output_facets > refine_stats.input_facets)
                    context.budget.accumulated_facets +=
                        refine_stats.output_facets - refine_stats.input_facets;
                trace("refine_done surface=" + std::to_string(surface_id) +
                      " levels=" + std::to_string(refine_stats.levels) +
                      " facets=" + std::to_string(refine_stats.output_facets) +
                      " sag=" + std::to_string(refine_stats.max_estimated_sag) +
                      " limited=" + (refine_stats.limited ? "1" : "0") +
                      " ms=" + std::to_string(elapsed_ms(phase_start)));
            }
        }
    }
    // Sample the deviation per surface with a surface-relative stride, so a
    // surface visited late is not starved by the global sample cap.
    context.deviation_seen = 0;
    context.deviation_stride =
        std::max<std::uint64_t>(1, static_cast<std::uint64_t>(faces.size()) / 200);
    for (const StlTriangle &facet : faces) {
        const StlPoint &a = points[facet[0]];
        const StlPoint &b = points[facet[1]];
        const StlPoint &c = points[facet[2]];
        const std::array<double, 3> normal = safe_normal(a, b, c);
        const double cross[3] = {b[1] * c[2] - b[2] * c[1], b[2] * c[0] - b[0] * c[2],
                                 b[0] * c[1] - b[1] * c[0]};
        context.signed_volume += (a[0] * cross[0] + a[1] * cross[1] + a[2] * cross[2]) / 6.0;
        const int ids[3] = {weld_vertex(context, a), weld_vertex(context, b),
                            weld_vertex(context, c)};
        for (int pair = 0; pair < 3; ++pair) {
            const int first = ids[pair];
            const int second = ids[(pair + 1) % 3];
            BoundaryEdge &edge = context.edges[edge_key(first, second)];
            if (edge.count == 0) {
                edge.first = first;
                edge.second = second;
                edge.normal = normal;
            }
            ++edge.count;
        }
        // Diagnostic sampling for the chord-deviation check: triangle centroid
        // and edge midpoints are interior/off-surface points, unlike vertices
        // which lie exactly on the native surface.
        if (context.deviation_enabled) {
            const std::uint64_t seen = context.deviation_seen++;
            if (seen % context.deviation_stride == 0) {
                const std::array<double, 3> centroid = {(a[0] + b[0] + c[0]) / 3.0,
                                                        (a[1] + b[1] + c[1]) / 3.0,
                                                        (a[2] + b[2] + c[2]) / 3.0};
                for (const std::array<double, 3> &point :
                     {centroid,
                      std::array<double, 3>{(a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0,
                                            (a[2] + b[2]) / 2.0},
                      std::array<double, 3>{(b[0] + c[0]) / 2.0, (b[1] + c[1]) / 2.0,
                                            (b[2] + c[2]) / 2.0},
                      std::array<double, 3>{(c[0] + a[0]) / 2.0, (c[1] + a[1]) / 2.0,
                                            (c[2] + a[2]) / 2.0}}) {
                    if (context.deviation_samples.size() >= context.deviation_limit)
                        break;
                    context.deviation_samples.push_back({surface, surface_id, point, false});
                }
                // One vertex per sampled facet, as a projection self-check.
                if (context.deviation_samples.size() < context.deviation_limit)
                    context.deviation_samples.push_back({surface, surface_id, a, true});
            }
        }
        if (!write_facet(*context.out, normal, a, b, c))
            return fail(context, surface_id, "write", "STL write failed", PRO_TK_GENERAL_ERROR);
    }
    context.surface_facets.push_back({surface_id, static_cast<std::uint64_t>(faces.size())});
    trace("write surface=" + std::to_string(surface_id) + " facets=" +
          std::to_string(faces.size()) + " ms=" + std::to_string(elapsed_ms(phase_start)));
    ++context.surface_count;
    return PRO_TK_NO_ERROR;
}

// Closes boundary edges left by independently tessellated surfaces. Each
// boundary component receives a centroid fan whose triangles traverse the
// original boundary edge in the opposite direction, so the edge becomes
// manifold. The filled area is tiny (small end-face holes); the added
// triangles and inverted-normal count are reported, never hidden.
inline ProError stitch_boundaries(Context &context) {
    std::vector<BoundaryEdge> boundary;
    for (const auto &entry : context.edges)
        if (entry.second.count == 1)
            boundary.push_back(entry.second);
    if (boundary.empty())
        return PRO_TK_NO_ERROR;
    std::unordered_map<int, std::vector<std::size_t>> adjacency;
    for (std::size_t index = 0; index < boundary.size(); ++index) {
        adjacency[boundary[index].first].push_back(index);
        adjacency[boundary[index].second].push_back(index);
    }
    std::vector<bool> visited_edge(boundary.size(), false);
    // Decompose the boundary graph into simple cycles. Branched components
    // (T-junctions) are split so each fan has its own centroid; a single
    // component-wide centroid would make some centroid edges non-manifold.
    std::function<bool(int, int, std::vector<int> &, std::vector<std::size_t> &)> find_cycle;
    find_cycle = [&](int start, int current, std::vector<int> &vertices,
                     std::vector<std::size_t> &edges) -> bool {
        for (std::size_t edge_index : adjacency[current]) {
            if (visited_edge[edge_index])
                continue;
            if (!edges.empty() && edge_index == edges.back())
                continue;
            const int other = boundary[edge_index].first == current ? boundary[edge_index].second
                                                                    : boundary[edge_index].first;
            if (other == start && edges.size() >= 2) {
                edges.push_back(edge_index);
                return true;
            }
            if (std::find(vertices.begin(), vertices.end(), other) != vertices.end())
                continue;
            vertices.push_back(other);
            edges.push_back(edge_index);
            if (find_cycle(start, other, vertices, edges))
                return true;
            edges.pop_back();
            vertices.pop_back();
        }
        return false;
    };
    for (std::size_t start_edge = 0; start_edge < boundary.size(); ++start_edge) {
        if (visited_edge[start_edge])
            continue;
        std::vector<int> cycle_vertices{boundary[start_edge].first, boundary[start_edge].second};
        std::vector<std::size_t> cycle_edges{start_edge};
        if (!find_cycle(boundary[start_edge].first, boundary[start_edge].second, cycle_vertices,
                        cycle_edges)) {
            context.error = "stitch: cannot form a boundary cycle";
            return PRO_TK_GENERAL_ERROR;
        }
        for (std::size_t edge_index : cycle_edges)
            visited_edge[edge_index] = true;
        std::array<double, 3> centroid = {0.0, 0.0, 0.0};
        for (int vertex : cycle_vertices)
            for (int axis = 0; axis < 3; ++axis)
                centroid[axis] += context.welded_points[vertex][axis];
        for (int axis = 0; axis < 3; ++axis)
            centroid[axis] /= static_cast<double>(cycle_vertices.size());
        // Keep each fan vertex distinct under the same welding tolerance used
        // by analysis tools; two coincident centroids would create a
        // non-manifold edge after welding.
        for (int attempt = 0; attempt < 16 && weld_collision(context, centroid); ++attempt)
            centroid[0] += context.weld_tolerance * 2.0;
        context.stitch_centers.push_back(centroid);
        for (std::size_t edge_index : cycle_edges) {
            const BoundaryEdge &edge = boundary[edge_index];
            const std::array<double, 3> &first = context.welded_points[edge.first];
            const std::array<double, 3> &second = context.welded_points[edge.second];
            // The owning facet traverses first -> second. A closing facet must
            // traverse the shared edge in the opposite direction, otherwise the
            // two facets have conflicting orientations.
            const std::array<double, 3> normal = safe_normal(second, first, centroid);
            const double alignment = normal[0] * edge.normal[0] + normal[1] * edge.normal[1] +
                                     normal[2] * edge.normal[2];
            if (alignment < 0.0)
                ++context.inverted_stitch_facets;
            if (!write_facet(*context.out, normal, second, first, centroid))
                return fail(context, -1, "stitch", "STL stitch write failed", PRO_TK_GENERAL_ERROR);
            context.signed_volume +=
                (second[0] * (first[1] * centroid[2] - first[2] * centroid[1]) +
                 second[1] * (first[2] * centroid[0] - first[0] * centroid[2]) +
                 second[2] * (first[0] * centroid[1] - first[1] * centroid[0])) /
                6.0;
            ++context.stitched_triangles;
        }
    }
    if (context.budget.accumulated_facets + context.stitched_triangles >
        context.budget.max_facets) {
        context.error = "stitch: facet budget exceeded";
        return PRO_TK_GENERAL_ERROR;
    }
    context.budget.accumulated_facets += context.stitched_triangles;
    return PRO_TK_NO_ERROR;
}

// Makes the winding of a welded closed mesh globally consistent and outward.
// Shared edges carry a direction per adjacent face; a BFS propagates a flip
// flag across the face graph. The rewritten file is then checked for a positive
// signed volume. Conflicts are reported instead of hidden.
inline bool fix_staged_winding(const std::filesystem::path &file, double tolerance,
                               std::string &error, std::uint64_t &flipped_faces,
                               std::uint64_t &conflicts, double &volume, bool &global_flipped) {
    std::ifstream input(file, std::ios::binary);
    if (!input) {
        error = "cannot reopen the staged STL for winding repair";
        return false;
    }
    Context weld;
    weld.weld_tolerance = tolerance;
    std::vector<StlTriangle> faces;
    // Raw corner coordinates are kept so the repair never snaps geometry: the
    // welded ids serve only for adjacency, and writing back snapped points was
    // observed to collapse sliver triangles into zero-area facets.
    std::vector<std::array<std::array<double, 3>, 3>> coordinates;
    std::vector<std::array<double, 3>> normals;
    std::string line;
    while (std::getline(input, line)) {
        if (line.rfind("facet normal", 0) != 0)
            continue;
        std::istringstream header(line);
        std::string keyword;
        std::array<double, 3> normal = {0.0, 0.0, 0.0};
        header >> keyword >> normal[0] >> normal[1] >> normal[2];
        std::array<double, 3> vertices[3];
        int count = 0;
        while (std::getline(input, line)) {
            std::istringstream tokens(line);
            std::string keyword;
            if (!(tokens >> keyword))
                continue;
            // The staged file indents "vertex" lines and "endfacet", so match on
            // the first token instead of the raw prefix.
            if (keyword == "endfacet")
                break;
            if (keyword != "vertex")
                continue;
            if (count >= 3) {
                error = "extra vertex while repairing winding";
                return false;
            }
            if (!(tokens >> vertices[count][0] >> vertices[count][1] >> vertices[count][2])) {
                error = "non-numeric vertex while repairing winding";
                return false;
            }
            ++count;
        }
        if (count != 3) {
            error = "malformed facet while repairing winding";
            return false;
        }
        faces.push_back({weld_vertex(weld, vertices[0]), weld_vertex(weld, vertices[1]),
                         weld_vertex(weld, vertices[2])});
        coordinates.push_back({vertices[0], vertices[1], vertices[2]});
        normals.push_back(normal);
    }
    input.close();
    if (faces.empty()) {
        error = "no facets while repairing winding";
        return false;
    }
    // Edge -> (face, direction). Direction +1 means low index -> high index.
    std::unordered_map<std::uint64_t, std::vector<std::pair<int, int>>> uses;
    for (int face = 0; face < static_cast<int>(faces.size()); ++face) {
        for (int pair = 0; pair < 3; ++pair) {
            const int first = faces[face][pair];
            const int second = faces[face][(pair + 1) % 3];
            uses[edge_key(first, second)].push_back({face, first < second ? 1 : -1});
        }
    }
    std::vector<int> flip(faces.size(), -1);
    conflicts = 0;
    std::queue<int> pending;
    for (int start = 0; start < static_cast<int>(faces.size()); ++start) {
        if (flip[start] != -1)
            continue;
        flip[start] = 0;
        pending.push(start);
        while (!pending.empty()) {
            const int face = pending.front();
            pending.pop();
            for (int pair = 0; pair < 3; ++pair) {
                const int first = faces[face][pair];
                const int second = faces[face][(pair + 1) % 3];
                const auto found = uses.find(edge_key(first, second));
                if (found == uses.end() || found->second.size() != 2)
                    continue;
                const auto &entries = found->second;
                const int other = entries[0].first == face ? entries[1].first : entries[0].first;
                const int direction =
                    entries[0].first == face ? entries[0].second : entries[1].second;
                const int other_direction =
                    entries[0].first == face ? entries[1].second : entries[0].second;
                const int required = flip[face] ^ (direction == other_direction ? 1 : 0);
                if (flip[other] == -1) {
                    flip[other] = required;
                    pending.push(other);
                } else if (flip[other] != required) {
                    ++conflicts;
                }
            }
        }
    }
    flipped_faces = 0;
    volume = 0.0;
    for (std::size_t index = 0; index < faces.size(); ++index) {
        if (flip[index] == 1) {
            std::swap(faces[index][1], faces[index][2]);
            std::swap(coordinates[index][1], coordinates[index][2]);
            for (double &value : normals[index])
                value = -value;
            ++flipped_faces;
        }
        const auto &a = coordinates[index][0];
        const auto &b = coordinates[index][1];
        const auto &c = coordinates[index][2];
        volume += (a[0] * (b[1] * c[2] - b[2] * c[1]) + a[1] * (b[2] * c[0] - b[0] * c[2]) +
                   a[2] * (b[0] * c[1] - b[1] * c[0])) /
                  6.0;
    }
    global_flipped = volume < 0.0;
    if (global_flipped) {
        volume = -volume;
        for (std::size_t index = 0; index < faces.size(); ++index) {
            std::swap(faces[index][1], faces[index][2]);
            std::swap(coordinates[index][1], coordinates[index][2]);
            for (double &value : normals[index])
                value = -value;
        }
        // A global flip reverses the BFS set as well, so report the net change.
        flipped_faces = faces.size() - flipped_faces;
    }
    const std::filesystem::path temporary = file.string() + ".winding";
    std::ofstream output(temporary, std::ios::binary);
    if (!output) {
        error = "cannot open the winding-repaired STL";
        return false;
    }
    output.precision(12);
    output << "solid creo_native\n";
    for (std::size_t index = 0; index < faces.size(); ++index) {
        const auto &a = coordinates[index][0];
        const auto &b = coordinates[index][1];
        const auto &c = coordinates[index][2];
        if (!write_facet(output, normals[index], a, b, c)) {
            error = "writing the winding-repaired STL failed";
            return false;
        }
    }
    output << "endsolid creo_native\n";
    output.flush();
    output.close();
    if (!output) {
        error = "closing the winding-repaired STL failed";
        return false;
    }
    std::error_code rename_error;
    std::filesystem::rename(temporary, file, rename_error);
    if (rename_error) {
        error = "cannot replace the staged STL with the winding-repaired file: " +
                rename_error.message();
        return false;
    }
    return true;
}

// Reverses every facet of a staged ASCII STL (normal and vertex order). Used
// only when the whole mesh's signed volume is negative, i.e. the SDK surface
// orientation yielded inward-facing triangles.
inline bool reverse_staged_stl(const std::filesystem::path &file, std::string &error) {
    std::ifstream input(file, std::ios::binary);
    if (!input) {
        error = "cannot reopen the staged STL for normal reversal";
        return false;
    }
    const std::filesystem::path temporary = file.string() + ".reversed";
    std::ofstream output(temporary, std::ios::binary);
    if (!output) {
        error = "cannot open the reversed STL file";
        return false;
    }
    output.precision(12);
    std::string line;
    std::vector<std::string> block;
    bool in_facet = false;
    while (std::getline(input, line)) {
        if (!in_facet) {
            if (line.rfind("facet normal", 0) == 0) {
                std::istringstream stream(line);
                std::string keyword;
                double x = 0.0, y = 0.0, z = 0.0;
                stream >> keyword >> x >> y >> z;
                output << "facet normal " << -x << ' ' << -y << ' ' << -z << '\n';
                in_facet = true;
            } else {
                output << line << '\n';
            }
            continue;
        }
        block.push_back(line);
        if (line != "endfacet")
            continue;
        std::vector<std::size_t> vertices;
        for (std::size_t index = 0; index < block.size(); ++index)
            if (block[index].rfind("vertex", 0) == 0)
                vertices.push_back(index);
        if (vertices.size() != 3) {
            error = "malformed facet while reversing the STL";
            return false;
        }
        std::swap(block[vertices[1]], block[vertices[2]]);
        for (const std::string &entry : block)
            output << entry << '\n';
        block.clear();
        in_facet = false;
    }
    output.flush();
    output.close();
    input.close();
    if (!output) {
        error = "writing the reversed STL failed";
        return false;
    }
    std::error_code rename_error;
    std::filesystem::rename(temporary, file, rename_error);
    if (rename_error) {
        error = "cannot replace the staged STL with the reversed one: " + rename_error.message();
        return false;
    }
    return true;
}

} // namespace stl_surface_detail

// Per-surface export candidate (BUG-130 Task 4). Only active solid bodies are
// visited; each surface owns its input/tessellation/array handles and releases
// them exactly once. Facets are streamed immediately, so the worker never owns
// a copy of the whole mesh. Nothing is published unless the whole file passes
// validation.
inline StlPerSurfaceReport write_stl_per_surface(ProMdl model,
                                                 const std::filesystem::path &destination,
                                                 const std::filesystem::path &staging_directory,
                                                 const std::wstring &staging_name,
                                                 const StlExportOptions &options,
                                                 double length_scale_to_mm,
                                                 const StlOutputLimits &limits = {}) {
    using namespace stl_export_detail;
    using namespace stl_surface_detail;
    StlPerSurfaceReport report;
    report.requested_chord_height_mm = options.chord_height_mm;
    report.requested_angle_control = options.angle_control;
    report.length_scale_to_mm = length_scale_to_mm;
    if (!std::isfinite(length_scale_to_mm) || length_scale_to_mm <= 0.0) {
        report.error = "the model length unit scale is unknown; refusing to guess STL quality";
        return report;
    }
    if (!std::isfinite(options.chord_height_mm) || options.chord_height_mm <= 0.0) {
        report.error = "chord_height_mm must be a finite positive number";
        return report;
    }
    if (!std::isfinite(options.angle_control) || options.angle_control < 0.0 ||
        options.angle_control > 1.0) {
        report.error = "angle_control must be finite and within 0.0..1.0";
        return report;
    }
    report.passed_chord_height_native = options.chord_height_mm / length_scale_to_mm;
    report.passed_angle_control = options.angle_control;
    std::error_code directory_error;
    std::filesystem::create_directories(staging_directory, directory_error);
    if (directory_error) {
        report.error = "cannot create the STL staging directory: " + directory_error.message();
        return report;
    }
    const std::filesystem::path staging_file = staging_directory / staging_name;
    std::ofstream out(staging_file, std::ios::binary);
    if (!out) {
        report.error = "cannot open the staged STL file";
        return report;
    }
    out.precision(12);
    out << "solid creo_native\n";
    if (!out) {
        report.error = "cannot write the staged STL header";
        return report;
    }
    Context context;
    context.out = &out;
    context.chord_height_native = report.passed_chord_height_native;
    context.angle_control = report.passed_angle_control;
    context.budget.max_facets = limits.max_facets;
    const char *deviation_probe = std::getenv("MECHDOG_STL_DEVIATION");
    context.deviation_enabled = deviation_probe && *deviation_probe == '1';
    report.deviation_requested = context.deviation_enabled;
    // Refinement is on by default: the SDK tessellation is left coarse on the
    // largest faces, so the requested chord height is checked and restored
    // here. MECHDOG_STL_REFINE=0 keeps the unrefined mesh for comparison.
    const char *refine_probe = std::getenv("MECHDOG_STL_REFINE");
    context.refine_enabled =
        options.refine_capped_surfaces && !(refine_probe && *refine_probe == '0');
    context.refine_target = context.chord_height_native;
    context.refine_min_facets = options.refine_min_facets;
    context.refine_max_output_facets = options.refine_max_output_facets;
    context.refine_vertex_budget = options.refine_max_new_vertices;
    context.refine_max_rounds = options.refine_max_rounds;
    report.refine_enabled = context.refine_enabled;
    report.refine_target_native = context.refine_target;

    options.stage("stl_collect_surfaces");
    ProSolidBody *bodies = nullptr;
    ProError code = ProSolidBodiesCollect((ProSolid)model, &bodies);
    if (code != PRO_TK_NO_ERROR || !bodies) {
        report.error = "cannot collect the solid bodies (code " + std::to_string(code) + ")";
        return report;
    }
    ProArrayGuard bodies_guard{(ProArray)bodies};
    int body_count = 0;
    code = ProArraySizeGet((ProArray)bodies, &body_count);
    if (code != PRO_TK_NO_ERROR) {
        report.error = "cannot size the solid body array (code " + std::to_string(code) + ")";
        return report;
    }
    int active_bodies = 0;
    // Count the surfaces first so the refinement vertex budget is shared
    // between them instead of being consumed by the first large surface.
    int surface_total = 0;
    for (int index = 0; index < body_count; ++index) {
        ProSolidBodyState state;
        code = ProSolidBodyStateGet(&bodies[index], &state);
        if (code != PRO_TK_NO_ERROR) {
            report.error = "cannot read a solid body state (code " + std::to_string(code) + ")";
            return report;
        }
        if (state != PRO_BODY_STATE_ACTIVE)
            continue;
        code = ProSolidBodySurfaceVisit(&bodies[index], count_surface_callback, &surface_total);
        if (code != PRO_TK_NO_ERROR) {
            report.error = "cannot count the surfaces (code " + std::to_string(code) + ")";
            return report;
        }
    }
    context.refine_surface_total = surface_total;
    options.stage("stl_tessellate_and_write");
    for (int index = 0; index < body_count; ++index) {
        ProSolidBodyState state;
        code = ProSolidBodyStateGet(&bodies[index], &state);
        if (code != PRO_TK_NO_ERROR) {
            report.error = "cannot read a solid body state (code " + std::to_string(code) + ")";
            return report;
        }
        if (state != PRO_BODY_STATE_ACTIVE)
            continue;
        ++active_bodies;
        code = ProSolidBodySurfaceVisit(&bodies[index], surface_callback, &context);
        if (code != PRO_TK_NO_ERROR || !context.error.empty()) {
            report.error = context.error.empty()
                               ? "surface visit failed (code " + std::to_string(code) + ")"
                               : context.error;
            report.failed_surface_id = context.failed_surface_id;
            report.failed_facet_index = context.failed_facet_index;
            report.failed_indices = context.failed_indices;
            report.failed_stage = context.failed_stage;
            report.failed_code = context.failed_code;
            return report;
        }
    }
    if (active_bodies == 0) {
        report.error = "the model has no active solid bodies";
        return report;
    }
    if (context.deviation_enabled && !context.deviation_samples.empty()) {
        double total = 0.0;
        std::uint64_t counted = 0;
        std::vector<double> distances;
        distances.reserve(context.deviation_samples.size());
        for (const DeviationSample &sample : context.deviation_samples) {
            ProUvParam uv = {0.0, 0.0};
            ProVector point = {sample.point[0], sample.point[1], sample.point[2]};
            ProVector closest = {0.0, 0.0, 0.0};
            ProVector deriv1[2] = {};
            ProVector deriv2[3] = {};
            ProVector normal = {0.0, 0.0, 0.0};
            if (ProSurfaceParamEval((ProSolid)model, sample.surface, point, uv) !=
                    PRO_TK_NO_ERROR ||
                ProSurfaceXyzdataEval(sample.surface, uv, closest, deriv1, deriv2, normal) !=
                    PRO_TK_NO_ERROR) {
                ++report.deviation_failed;
                continue;
            }
            const double dx = sample.point[0] - closest[0];
            const double dy = sample.point[1] - closest[1];
            const double dz = sample.point[2] - closest[2];
            const double distance = std::sqrt(dx * dx + dy * dy + dz * dz) * length_scale_to_mm;
            if (!std::isfinite(distance)) {
                ++report.deviation_failed;
                continue;
            }
            if (distances.empty() || distance > report.deviation_max_mm) {
                report.deviation_max_mm = distance;
                report.deviation_worst_surface_id = sample.surface_id;
                report.deviation_worst_point = sample.point;
            }
            if (sample.vertex) {
                ++report.deviation_vertex_samples;
                report.deviation_vertex_max_mm = std::max(report.deviation_vertex_max_mm, distance);
                continue;
            }
            distances.push_back(distance);
            total += distance;
            ++counted;
        }
        report.deviation_samples = counted;
        report.deviation_mean_mm = counted ? total / static_cast<double>(counted) : 0.0;
        if (!distances.empty()) {
            std::sort(distances.begin(), distances.end());
            const std::size_t index =
                static_cast<std::size_t>(0.99 * static_cast<double>(distances.size() - 1));
            report.deviation_p99_mm = distances[index];
        }
    }
    if (options.stitch_seams) {
        options.stage("stl_stitch_mesh");
        code = stitch_boundaries(context);
        if (code != PRO_TK_NO_ERROR) {
            report.error = context.error;
            report.failed_stage = context.failed_stage;
            report.failed_code = context.failed_code;
            return report;
        }
    }
    out << "endsolid creo_native\n";
    out.flush();
    if (!out) {
        report.error = "STL write/flush failed";
        return report;
    }
    out.close();
    if (!out) {
        report.error = "STL close failed";
        return report;
    }
    report.staging_file_written = std::filesystem::is_regular_file(staging_file);
    report.surface_count = context.surface_count;
    report.facet_count = context.budget.accumulated_facets;
    report.zero_area_facets = context.budget.zero_area_facets;
    report.normal_surfaces = context.normal_surfaces;
    report.normal_flipped_facets = context.normal_flipped_facets;
    report.stitched_triangles = context.stitched_triangles;
    report.inverted_stitch_facets = context.inverted_stitch_facets;
    report.surface_facets = context.surface_facets;
    report.refined_surfaces = context.refined_surfaces;
    report.refine_input_facets = context.refine_input_facets;
    report.refine_output_facets = context.refine_output_facets;
    report.refine_created_vertices = context.refine_created_vertices;
    report.refine_pinned_triangles = context.refine_pinned_triangles;
    report.refine_rejected_edges = context.refine_rejected_edges;
    report.refine_skipped_uv = context.refine_skipped_uv;
    report.refine_skipped_uv_query = context.refine_skipped_uv_query;
    report.refine_skipped_uv_mismatch = context.refine_skipped_uv_mismatch;
    report.refine_skipped_normals = context.refine_skipped_normals;
    report.refine_uv_max_mismatch = context.refine_uv_max_mismatch;
    report.refine_max_estimated_sag = context.refine_max_estimated_sag;
    report.refine_limited_surfaces = context.refine_limited_surfaces;
    report.refine_zero_area_facets = context.refine_zero_area_facets;
    report.refine_max_level = context.refine_max_level;
    std::string winding_error;
    double fixed_volume = 0.0;
    bool global_flipped = false;
    // Adjacency for winding repair must match the coordinates actually written.
    // The 0.001 mm stitching tolerance is used only to find holes; reusing it
    // here merges genuinely distinct vertices (observed at 5e-4 mm apart) and
    // hides winding conflicts that external tools still see.
    constexpr double winding_weld_tolerance = 1.0e-9;
    options.stage("stl_repair_winding");
    if (!fix_staged_winding(staging_file, winding_weld_tolerance, winding_error,
                            report.winding_flipped_facets, report.winding_conflicts, fixed_volume,
                            global_flipped)) {
        report.error = winding_error;
        return report;
    }
    report.signed_volume_mm3 = fixed_volume;
    report.global_flipped = global_flipped;
    options.stage("stl_validate_mesh");
    try {
        report.file = validate_ascii_stl(staging_file, limits);
    } catch (const StlFileError &error) {
        report.file_error = error.what();
        return report;
    }
    std::error_code output_error;
    std::filesystem::create_directories(destination.parent_path(), output_error);
    if (output_error) {
        report.error = "cannot create the STL output directory: " + output_error.message();
        return report;
    }
    options.stage("stl_publish_verified_mesh");
    const std::string publish_error = publish(staging_file, destination);
    if (!publish_error.empty()) {
        report.error = publish_error;
        return report;
    }
    report.published = true;
    report.success = true;
    return report;
}
