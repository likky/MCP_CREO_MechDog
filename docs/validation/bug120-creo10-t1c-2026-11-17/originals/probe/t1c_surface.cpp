// T1-C surface probe: read-only sampling of a quilt's surfaces.
//
// Two questions this answers, without touching the dashboard:
//   1. What the inspection "bbox_mm" field really is. native/quilt_query.h takes
//      the union of ProSurfaceDataGet(...)->p_surface_data->xyz_min/xyz_max, and
//      the SDK header calls those values approximate extents. This probe prints
//      that union per surface next to a UV sample grid of the same surfaces.
//   2. Whether a boundary-blend surface actually passes through a raised middle
//      section: the grid reports the nearest sample to a target point.
//
// Sampling is sampling. It cannot prove exact extremes; the trimmed boundary is
// measured separately from the quilt's open edges. Nothing here writes geometry.
#define NOMINMAX
#include <windows.h>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <ProToolkit.h>
#include <ProCore.h>
#include <ProMdl.h>
#include <ProModelitem.h>
#include <ProSolid.h>
#include <ProQuilt.h>
#include <ProSurface.h>
#include <ProSurfacedata.h>
#include <ProGeomitem.h>
#include <ProArray.h>
#include <ProWindows.h>
#include "third_party/json.hpp"

using Json = nlohmann::json;

static std::string utf8(const std::wstring &value) {
    if (value.empty())
        return std::string();
    int size = WideCharToMultiByte(CP_UTF8, 0, value.data(), (int)value.size(), nullptr, 0, nullptr,
                                   nullptr);
    std::string result(size, '\0');
    WideCharToMultiByte(CP_UTF8, 0, value.data(), (int)value.size(), result.data(), size, nullptr,
                        nullptr);
    return result;
}

static ProError connect_creo(ProProcessHandle *process, unsigned int timeout_seconds) {
    char empty[] = "";
    char *selected = nullptr;
    size_t length = 0;
    _dupenv_s(&selected, &length, "MECHDOG_CREO_SESSION_ID");
    std::string expected = selected ? selected : "";
    free(selected);
    ProBoolean random = PRO_B_FALSE;
    ProError error = ProEngineerConnect(expected.empty() ? empty : expected.data(), empty, empty,
                                        empty, PRO_B_FALSE, timeout_seconds, &random, process);
    if (!error && !expected.empty()) {
        ProConnectionId actual;
        error = ProEngineerConnectIdGet(actual);
        if (error || expected != actual) {
            ProEngineerDisconnect(process, 15);
            return error ? error : PRO_TK_E_NOT_FOUND;
        }
    }
    return error;
}

struct Accumulator {
    int grid = 21;
    bool has_target = false;
    double target[3] = {0, 0, 0};
    Json surfaces = Json::array();
    // union of ProSurfaceDataGet extents
    double data_min[3] = {1e30, 1e30, 1e30};
    double data_max[3] = {-1e30, -1e30, -1e30};
    // union of UV samples
    double s_min[3] = {1e30, 1e30, 1e30};
    double s_max[3] = {-1e30, -1e30, -1e30};
    long long samples = 0;
    long long failures = 0;
    double best_distance = 1e30;
    double best_point[3] = {0, 0, 0};
    // Explicit parameter probes. The blend's parameter direction across the
    // sections is the only geometric record of the order the collector held
    // them in, so the caller asks for named (u,v) points instead of relying on
    // a parent list (which is id-sorted, not ordered).
    std::vector<std::pair<double, double>> probes;
    Json probe_rows = Json::array();
};

static void sample_surface(ProSurface surface, const ProSurfacedata &sd, Accumulator &acc) {
    if (sd.uv_max[0] <= sd.uv_min[0] || sd.uv_max[1] <= sd.uv_min[1])
        return;
    for (int i = 0; i <= acc.grid; i++) {
        for (int j = 0; j <= acc.grid; j++) {
            ProUvParam uv = {
                sd.uv_min[0] + (sd.uv_max[0] - sd.uv_min[0]) * i / acc.grid,
                sd.uv_min[1] + (sd.uv_max[1] - sd.uv_min[1]) * j / acc.grid,
            };
            ProVector xyz = {0, 0, 0};
            ProVector d1[2] = {{0, 0, 0}, {0, 0, 0}};
            ProVector d2[3] = {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}};
            ProVector normal = {0, 0, 0};
            if (ProSurfaceXyzdataEval(surface, uv, xyz, d1, d2, normal) != PRO_TK_NO_ERROR) {
                acc.failures++;
                continue;
            }
            acc.samples++;
            for (int k = 0; k < 3; k++) {
                acc.s_min[k] = std::min(acc.s_min[k], xyz[k]);
                acc.s_max[k] = std::max(acc.s_max[k], xyz[k]);
            }
            if (acc.has_target) {
                double dx = xyz[0] - acc.target[0];
                double dy = xyz[1] - acc.target[1];
                double dz = xyz[2] - acc.target[2];
                double distance = std::sqrt(dx * dx + dy * dy + dz * dz);
                if (distance < acc.best_distance) {
                    acc.best_distance = distance;
                    acc.best_point[0] = xyz[0];
                    acc.best_point[1] = xyz[1];
                    acc.best_point[2] = xyz[2];
                }
            }
        }
    }
}

static void probe_uvs(ProSurface surface, const ProSurfacedata &sd, Accumulator &acc, int surface_id) {
    for (const auto &probe : acc.probes) {
        ProUvParam uv = {
            sd.uv_min[0] + (sd.uv_max[0] - sd.uv_min[0]) * probe.first,
            sd.uv_min[1] + (sd.uv_max[1] - sd.uv_min[1]) * probe.second,
        };
        ProVector xyz = {0, 0, 0};
        ProVector d1[2] = {{0, 0, 0}, {0, 0, 0}};
        ProVector d2[3] = {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}};
        ProVector normal = {0, 0, 0};
        Json row = {{"u", probe.first}, {"v", probe.second}, {"surface_id", surface_id}};
        if (ProSurfaceXyzdataEval(surface, uv, xyz, d1, d2, normal) == PRO_TK_NO_ERROR) {
            row["xyz"] = {xyz[0], xyz[1], xyz[2]};
        } else {
            row["xyz"] = nullptr;
            row["error"] = "ProSurfaceXyzdataEval failed";
        }
        acc.probe_rows.push_back(row);
    }
}

static ProError surface_cb(ProSurface surface, ProError status, ProAppData data) {
    auto *acc = static_cast<Accumulator *>(data);
    if (status)
        return PRO_TK_NO_ERROR;
    int surface_id = 0;
    ProSurfaceIdGet(surface, &surface_id);
    ProSrftype surface_type = PRO_SRF_PLANE;
    ProSurfaceTypeGet(surface, &surface_type);
    ProGeomitemdata *geom = nullptr;
    int data_code = (int)ProSurfaceDataGet(surface, &geom);
    Json row = {{"surface_id", surface_id},
                {"surface_type", (int)surface_type},
                {"data_code", data_code}};
    if (!data_code && geom && geom->data.p_surface_data) {
        const ProSurfacedata *sd = geom->data.p_surface_data;
        row["uv_min"] = {sd->uv_min[0], sd->uv_min[1]};
        row["uv_max"] = {sd->uv_max[0], sd->uv_max[1]};
        row["data_xyz_min"] = {sd->xyz_min[0], sd->xyz_min[1], sd->xyz_min[2]};
        row["data_xyz_max"] = {sd->xyz_max[0], sd->xyz_max[1], sd->xyz_max[2]};
        for (int i = 0; i < 3; i++) {
            acc->data_min[i] = std::min(acc->data_min[i], sd->xyz_min[i]);
            acc->data_max[i] = std::max(acc->data_max[i], sd->xyz_max[i]);
        }
        sample_surface(surface, *sd, *acc);
        probe_uvs(surface, *sd, *acc, surface_id);
    }
    acc->surfaces.push_back(row);
    if (geom)
        ProGeomitemdataFree(&geom);
    return PRO_TK_NO_ERROR;
}

int wmain(int argc, wchar_t **argv) {
    if (argc != 2)
        return 2;
    const std::wstring dir = argv[1];
    std::ifstream input(std::filesystem::path(dir) / L"probe.json", std::ios::binary);
    Json request;
    try {
        input >> request;
    } catch (...) {
        return 3;
    }
    const std::string request_id = request.value("request_id", std::string("unnamed"));
    const std::string model_expected = request.value("model", std::string());
    const int quilt_id = request.value("quilt_id", -1);

    Json result = {{"request_id", request_id},
                   {"probe", "t1c-surface"},
                   {"model", model_expected},
                   {"quilt_id", quilt_id},
                   {"sampling_note", "UV grid samples; not exact extremes"}};

    ProProcessHandle process = {};
    ProError code = connect_creo(&process, 30);
    result["connect_code"] = (int)code;
    if (code) {
        result["success"] = false;
        result["failure"] = "connect";
        std::ofstream(std::filesystem::path(dir) / L"probe_result.json", std::ios::binary)
            << result.dump(2);
        return 1;
    }

    ProMdl current = nullptr;
    code = ProMdlCurrentGet(&current);
    ProMdlName name = {};
    if (!code && current)
        code = ProMdlMdlnameGet(current, name);
    result["current_model"] = code ? std::string() : utf8(name);
    result["model_matches"] = !code && model_expected == utf8(name);

    if (!code && current && quilt_id > 0) {
        ProQuilt quilt = nullptr;
        ProError init = ProQuiltInit((ProSolid)current, quilt_id, &quilt);
        result["quilt_init_code"] = (int)init;
        if (!init) {
            Accumulator acc;
            acc.grid = request.value("grid", 21);
            Json target = request.value("target_point", Json::array());
            if (target.is_array() && target.size() == 3) {
                acc.has_target = true;
                for (int i = 0; i < 3; i++)
                    acc.target[i] = target[i].get<double>();
            }
            Json probes = request.value("uv_probes", Json::array());
            if (probes.is_array()) {
                for (const auto &item : probes) {
                    if (item.is_array() && item.size() == 2)
                        acc.probes.emplace_back(item[0].get<double>(), item[1].get<double>());
                }
            }
            ProError visit = ProQuiltSurfaceVisit(quilt, surface_cb, nullptr, &acc);
            result["surface_visit_code"] = (int)visit;
            result["surface_count"] = acc.surfaces.size();
            result["surfaces"] = acc.surfaces;
            result["uv_probe_note"] =
                "u,v are normalised within each surface's own uv range; the section "
                "direction is whichever parameter varies between the section planes";
            result["uv_probes"] = acc.probe_rows;
            result["data_range_union"] = {
                {"min", {acc.data_min[0], acc.data_min[1], acc.data_min[2]}},
                {"max", {acc.data_max[0], acc.data_max[1], acc.data_max[2]}},
                {"source", "ProSurfaceDataGet xyz_min/xyz_max (SDK: approximate extents)"}};
            result["samples"] = {
                {"count", acc.samples},
                {"failures", acc.failures},
                {"min", {acc.s_min[0], acc.s_min[1], acc.s_min[2]}},
                {"max", {acc.s_max[0], acc.s_max[1], acc.s_max[2]}}};
            if (acc.has_target) {
                result["target"] = {
                    {"point", {acc.target[0], acc.target[1], acc.target[2]}},
                    {"nearest_sample", {acc.best_point[0], acc.best_point[1], acc.best_point[2]}},
                    {"nearest_distance_mm", acc.best_distance}};
            }
        }
    }

    result["success"] = true;
    std::ofstream(std::filesystem::path(dir) / L"probe_result.json", std::ios::binary)
        << result.dump(2);
    ProEngineerDisconnect(&process, 20);
    return 0;
}
