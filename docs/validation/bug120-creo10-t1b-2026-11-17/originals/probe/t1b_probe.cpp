// BUG-120 T1-B minimal probe: drive the native Boundary Blend dashboard by
// geometry id instead of screen picking.
//
// This is a temporary research probe, not a product feature. It is an
// asynchronous Toolkit program: it connects to the already running Creo session
// over the existing single channel, resolves every curve reference from the
// current test model, records selections with ProSelectExternalselectionRecord
// and then completes the dashboard with a loaded macro.
//
// Selection semantics come from the installed SDK header (ProSelection.h):
//   PRO_SELECT_OVERRIDE - unmodified selection
//   PRO_SELECT_TOGGLE   - CTRL modified selection
// so the first reference of a collector uses OVERRIDE and every later reference
// of the same collector uses TOGGLE. The loop is data driven: it never branches
// on 2, 3 or 5 sections.
#define NOMINMAX
#include <windows.h>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <ProToolkit.h>
#include <ProCore.h>
#include <ProMdl.h>
#include <ProModelitem.h>
#include <ProSolid.h>
#include <ProFeature.h>
#include <ProFeatType.h>
#include <ProSelection.h>
#include <ProSelbuffer.h>
#include <ProCurve.h>
#include <ProGeomitem.h>
#include <ProArray.h>
#include <ProMenu.h>
#include <ProUtil.h>
#include <ProView.h>
#include <ProWindows.h>
#include "third_party/json.hpp"

using Json = nlohmann::json;

static std::ofstream g_steps;
static std::wstring g_job_dir;
static std::string g_request_id;

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

static std::wstring wide(const std::string &value) {
    if (value.empty())
        return std::wstring();
    int size = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), (int)value.size(),
                                   nullptr, 0);
    if (!size)
        throw std::runtime_error("invalid utf8");
    std::wstring result(size, L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), (int)value.size(),
                        result.data(), size);
    return result;
}

// Every observation is appended immediately so a later crash cannot hide the
// step that failed.
static void step(const char *phase, const Json &fields) {
    Json entry = fields;
    entry["request_id"] = g_request_id;
    entry["phase"] = phase;
    entry["tick_ms"] = (long long)GetTickCount64();
    g_steps << entry.dump() << "\n";
    g_steps.flush();
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
            ProEngineerDisconnect(process, timeout_seconds < 15 ? timeout_seconds : 15);
            return error ? error : PRO_TK_E_NOT_FOUND;
        }
    }
    return error;
}

struct FeatureRow {
    int id = 0;
    int type = 0;
    std::wstring subtype;
    std::wstring name;
    int status = 0;
    ProBoolean incomplete = PRO_B_FALSE;
    int sections = -1;
};

// Parent feature ids are independent evidence about which sketches the feature
// actually consumed; they are recorded next to the geometry, never instead.
static Json feature_parents(ProSolid solid, int feature_id) {
    ProFeature feature;
    if (ProFeatureInit(solid, feature_id, &feature) != PRO_TK_NO_ERROR)
        return nullptr;
    int *parents = nullptr;
    int count = 0;
    ProError code = ProFeatureParentsGet(&feature, &parents, &count);
    Json list = Json::array();
    if (!code && parents)
        for (int i = 0; i < count; i++)
            list.push_back(parents[i]);
    if (parents)
        ProArrayFree((ProArray *)&parents);
    return {{"parents", list}, {"error", (int)code}};
}

static std::wstring newest_model_file(const std::wstring &directory, const std::wstring &name) {
    WIN32_FIND_DATAW entry;
    std::wstring pattern = directory + L"\\" + name + L".prt.*";
    HANDLE find = FindFirstFileW(pattern.c_str(), &entry);
    if (find == INVALID_HANDLE_VALUE)
        return std::wstring();
    int newest = -1;
    std::wstring result;
    do {
        std::wstring file = entry.cFileName;
        size_t dot = file.rfind(L'.');
        if (dot == std::wstring::npos)
            continue;
        long version = wcstol(file.c_str() + dot + 1, nullptr, 10);
        if (version > newest) {
            newest = (int)version;
            result = directory + L"\\" + file;
        }
    } while (FindNextFileW(find, &entry));
    FindClose(find);
    return result;
}

static ProError collect_feature(ProFeature *feature, ProError status, ProAppData data) {
    if (status)
        return status;
    auto *rows = static_cast<std::vector<FeatureRow> *>(data);
    FeatureRow row;
    row.id = feature->id;
    ProFeattype type;
    if (ProFeatureTypeGet(feature, &type) == PRO_TK_NO_ERROR)
        row.type = (int)type;
    ProLine subtype = L"";
    if (ProFeatureSubtypeGet(feature, subtype) == PRO_TK_NO_ERROR)
        row.subtype = subtype;
    ProName name = L"";
    if (ProModelitemNameGet(feature, name) == PRO_TK_NO_ERROR)
        row.name = name;
    ProFeatStatus feature_status;
    if (ProFeatureStatusGet(feature, &feature_status) == PRO_TK_NO_ERROR)
        row.status = (int)feature_status;
    ProFeatureIsIncomplete(feature, &row.incomplete);
    int sections = 0;
    if (ProFeatureNumSectionsGet(feature, &sections) == PRO_TK_NO_ERROR)
        row.sections = sections;
    rows->push_back(row);
    return PRO_TK_NO_ERROR;
}

static Json feature_snapshot(ProSolid solid, ProError &code) {
    std::vector<FeatureRow> rows;
    code = ProSolidFeatVisit(solid, collect_feature, nullptr, &rows);
    Json list = Json::array();
    for (const auto &row : rows)
        list.push_back({{"feature_id", row.id},
                        {"type", row.type},
                        {"subtype", utf8(row.subtype)},
                        {"name", utf8(row.name)},
                        {"status", row.status},
                        {"incomplete", row.incomplete != PRO_B_FALSE},
                        {"sections", row.sections}});
    return list;
}

static ProSolid g_solid = nullptr;

// Describe a curve exactly as the model stores it. Coordinates are recorded so a
// caller can prove which curve a geometry id names instead of assuming order.
static void describe_curve(ProSolid solid, int geom_id, Json &row) {
    ProCurve curve;
    ProError code = ProCurveInit(solid, geom_id, &curve);
    row["curve_init_error"] = (int)code;
    if (code)
        return;
    ProEnttype kind;
    code = ProCurveTypeGet(curve, &kind);
    row["curve_type"] = (int)kind;
    row["curve_type_error"] = (int)code;
    double length = 0;
    code = ProCurveLengthEval(curve, &length);
    row["curve_length_mm"] = length;
    row["curve_length_error"] = (int)code;
    ProGeomitemdata *data = nullptr;
    code = ProCurveDataGet(curve, &data);
    row["curve_data_error"] = (int)code;
    if (!code && data && data->data.p_curve_data) {
        int data_type = data->data.p_curve_data->line.type;
        row["curve_data_type"] = data_type;
        if (data_type == PRO_ENT_LINE) {
            row["end1"] = {data->data.p_curve_data->line.end1[0],
                           data->data.p_curve_data->line.end1[1],
                           data->data.p_curve_data->line.end1[2]};
            row["end2"] = {data->data.p_curve_data->line.end2[0],
                           data->data.p_curve_data->line.end2[1],
                           data->data.p_curve_data->line.end2[2]};
        }
        ProGeomitemdataFree(&data);
    }
}

static ProError collect_curve_item(ProGeomitem *item, ProError status, ProAppData data) {
    if (!status) {
        Json *list = static_cast<Json *>(data);
        Json row = {{"geom_id", item->id}, {"type", (int)item->type}};
        if (g_solid)
            describe_curve(g_solid, item->id, row);
        list->push_back(row);
    }
    return PRO_TK_NO_ERROR;
}

static ProError collect_curve_feature(ProFeature *feature, ProError status, ProAppData data) {
    if (status)
        return status;
    Json *list = static_cast<Json *>(data);
    Json items = Json::array();
    ProError code = ProFeatureGeomitemVisit(feature, PRO_CURVE, collect_curve_item, nullptr, &items);
    if (!items.empty()) {
        ProLine subtype = L"";
        ProFeatureSubtypeGet(feature, subtype);
        list->push_back({{"feature_id", feature->id}, {"subtype", utf8(subtype)},
                         {"curves", items}, {"visit_error", (int)code}});
    }
    return PRO_TK_NO_ERROR;
}

// A view change has to be provable, so it is done with the SDK view-matrix
// setter and read back, never with a macro that may silently do nothing. The
// target matrix is the canonical 3/4 view rotated about the model Z axis, which
// keeps every row unit length and orthogonal as the setter requires.
static void build_view(double degrees, ProMatrix out) {
    const double a0 = 0.7071067811865476, a1 = -0.4082482904638631, a2 = 0.5773502691896258;
    const double b0 = 0.7071067811865476, b1 = 0.4082482904638631, b2 = -0.5773502691896258;
    const double c0 = 0.0, c1 = 0.8164965809277260, c2 = 0.5773502691896258;
    const double radians = degrees * 3.14159265358979323846 / 180.0;
    const double c = cos(radians), s = sin(radians);
    out[0][0] = a0 * c - a1 * s;
    out[0][1] = a0 * s + a1 * c;
    out[0][2] = a2;
    out[0][3] = 0;
    out[1][0] = b0 * c - b1 * s;
    out[1][1] = b0 * s + b1 * c;
    out[1][2] = b2;
    out[1][3] = 0;
    out[2][0] = c0 * c - c1 * s;
    out[2][1] = c0 * s + c1 * c;
    out[2][2] = c2;
    out[2][3] = 0;
    out[3][0] = 0;
    out[3][1] = 0;
    out[3][2] = 0;
    out[3][3] = 1;
}

static Json matrix_rows(const ProMatrix value) {
    Json rows = Json::array();
    for (int row = 0; row < 3; row++)
        rows.push_back({value[row][0], value[row][1], value[row][2]});
    return rows;
}

// Creo applies its own shift and scale, so only the rotation is compared.
static bool view_rotation_changed(const ProMatrix before, const ProMatrix after) {
    for (int row = 0; row < 3; row++)
        for (int column = 0; column < 3; column++)
            if (fabs(before[row][column] - after[row][column]) > 1e-6)
                return true;
    return false;
}

static Json macro_load(const std::wstring &macro, const char *phase) {    if (macro.empty())
        return Json{{"skipped", true}};
    std::wstring buffer = macro;
    ProError code = ProMacroLoad(buffer.data());
    step(phase, {{"api", "ProMacroLoad"}, {"macro", utf8(macro)}, {"error", (int)code}});
    return Json{{"macro", utf8(macro)}, {"error", (int)code}};
}

int wmain(int argc, wchar_t **argv) {
    if (argc != 2)
        return 2;
    g_job_dir = argv[1];
    std::ifstream input(std::filesystem::path(g_job_dir) / L"probe.json", std::ios::binary);
    Json request;
    try {
        input >> request;
    } catch (...) {
        return 3;
    }
    g_request_id = request.value("request_id", std::string("unnamed"));
    std::ofstream steps_file(std::filesystem::path(g_job_dir) / L"probe_steps.jsonl",
                             std::ios::binary);
    g_steps = std::move(steps_file);
    Json result = {{"request_id", g_request_id},
                   {"probe", "t1b-async-id-driven"},
                   {"model", request.value("model", std::string())},
                   {"stage", request.value("stage", std::string("all"))},
                   {"mode", request.value("mode", std::string("collector"))}};

    const std::string stage = result["stage"];
    const std::string mode = result["mode"];
    const std::wstring model_expected = wide(request.value("model", std::string()));

    ProProcessHandle process = {};
    ProError code = connect_creo(&process, 30);
    result["connect_code"] = (int)code;
    step("connect", {{"api", "ProEngineerConnect"}, {"error", (int)code}});
    if (code) {
        result["success"] = false;
        result["failure"] = "connect";
        std::ofstream(std::filesystem::path(g_job_dir) / L"probe_result.json", std::ios::binary)
            << result.dump(2);
        return 20;
    }

    ProMdl model = nullptr;
    code = ProMdlCurrentGet(&model);
    ProMdlName actual = L"";
    if (!code)
        code = ProMdlMdlnameGet(model, actual);
    // A closed window leaves no current model; the close stage still has to find
    // the resident object by name to erase it.
    if (code && stage == "close" && !model_expected.empty()) {
        ProName name;
        wcscpy_s(name, model_expected.c_str());
        ProError init = ProMdlInit(name, PRO_MDL_PART, &model);
        if (!init) {
            code = PRO_TK_NO_ERROR;
            ProMdlMdlnameGet(model, actual);
        }
    }
    result["current_model"] = utf8(actual);
    result["current_model_code"] = (int)code;
    step("model", {{"api", "ProMdlCurrentGet/ProMdlMdlnameGet"},
                   {"error", (int)code},
                   {"observed", utf8(actual)},
                   {"expected", utf8(model_expected)}});

    std::string failure;
    if (code)
        failure = "current_model_unreadable";
    else if (_wcsicmp(actual, model_expected.c_str()))
        failure = "current_model_mismatch";

    // Discovery stage: list the curve geometry of the live model so a caller can
    // re-resolve references for this model instead of reusing another model's id.
    if (failure.empty() && stage == "list") {
        Json curves = Json::array();
        g_solid = (ProSolid)model;
        ProError list_code =
            ProSolidFeatVisit((ProSolid)model, collect_curve_feature, nullptr, &curves);
        result["curve_features"] = curves;
        result["list_code"] = (int)list_code;
        result["success"] = true;
        step("list", {{"api", "ProSolidFeatVisit/ProFeatureGeomitemVisit"},
                      {"error", (int)list_code},
                      {"features", (int)curves.size()}});
        ProEngineerDisconnect(&process, 15);
        std::ofstream(std::filesystem::path(g_job_dir) / L"probe_result.json", std::ios::binary)
            << result.dump(2);
        return 0;
    }

    // Persist the session result into this round's own directory so an
    // independent MCP adoption can verify the saved bytes.
    if (failure.empty() && stage == "save") {
        std::wstring target = wide(request.value("save_dir", std::string()));
        ProPath directory;
        if (target.size() >= PRO_PATH_SIZE)
            failure = "save_dir_too_long";
        else {
            wcscpy_s(directory, PRO_PATH_SIZE, target.c_str());
            ProError save_code = ProMdlnameBackup(model, directory);
            std::wstring saved = newest_model_file(target, actual);
            result["save_code"] = (int)save_code;
            result["saved_file"] = utf8(saved);
            step("save", {{"api", "ProMdlnameBackup"},
                          {"error", (int)save_code},
                          {"directory", utf8(target)},
                          {"file", utf8(saved)}});
            if (save_code)
                failure = "save_failed";
        }
        result["success"] = failure.empty();
        if (!failure.empty())
            result["failure"] = failure;
        ProEngineerDisconnect(&process, 15);
        std::ofstream(std::filesystem::path(g_job_dir) / L"probe_result.json", std::ios::binary)
            << result.dump(2);
        return failure.empty() ? 0 : 21;
    }

    // Drop this round's test model from the session so an independent adoption
    // reads the saved bytes instead of a modified resident copy.
    if (failure.empty() && stage == "close") {
        ProError erase_code = ProMdlErase(model);
        result["erase_code"] = (int)erase_code;
        step("close", {{"api", "ProMdlErase"}, {"error", (int)erase_code}});
        if (erase_code)
            failure = "erase_failed";
        result["success"] = failure.empty();
        if (!failure.empty())
            result["failure"] = failure;
        ProEngineerDisconnect(&process, 15);
        std::ofstream(std::filesystem::path(g_job_dir) / L"probe_result.json", std::ios::binary)
            << result.dump(2);
        return failure.empty() ? 0 : 21;
    }

    // Resolve every reference from the live model. Nothing is cached across
    // models and nothing falls back to a same-numbered object of another owner.
    Json resolved = Json::array();
    std::vector<ProSelection> selections;
    if (failure.empty() && request.contains("curves")) {
        int index = 0;
        for (const auto &entry : request.at("curves")) {
            Json row = {{"index", index},
                        {"owner", entry.value("owner", std::string())},
                        {"geom_id", entry.value("geom_id", -1)},
                        {"feature_id", entry.value("feature_id", -1)},
                        {"role", entry.value("role", std::string("first_dir"))}};
            std::wstring owner = wide(entry.value("owner", std::string()));
            if (_wcsicmp(owner.c_str(), actual)) {
                row["error"] = "owner_mismatch";
                row["resolved"] = false;
                resolved.push_back(row);
                failure = "reference_owner_mismatch";
                step("resolve", row);
                break;
            }
            int geom_id = entry.value("geom_id", -1);
            ProModelitem item;
            code = ProModelitemInit(model, geom_id, PRO_CURVE, &item);
            row["modelitem_error"] = (int)code;
            if (!code)
                describe_curve((ProSolid)model, geom_id, row);
            if (!code) {
                ProMdl owner_model = nullptr;
                code = ProModelitemMdlGet(&item, &owner_model);
                ProMdlName owner_name = L"";
                if (!code && owner_model)
                    code = ProMdlMdlnameGet(owner_model, owner_name);
                row["resolved_owner"] = utf8(owner_name);
                row["owner_error"] = (int)code;
                if (!code && _wcsicmp(owner_name, actual))
                    code = PRO_TK_BAD_CONTEXT;
            }
            if (!code) {
                ProSelection selection = nullptr;
                code = ProSelectionAlloc(nullptr, &item, &selection);
                row["selection_alloc_error"] = (int)code;
                if (!code) {
                    selections.push_back(selection);
                    row["resolved"] = true;
                }
            } else {
                row["resolved"] = false;
            }
            row["error"] = code ? Json((int)code) : Json(nullptr);
            step("resolve", row);
            resolved.push_back(row);
            if (code) {
                failure = "reference_unresolved";
                break;
            }
            index++;
        }
        result["resolved_count"] = (int)selections.size();
    }
    result["references"] = resolved;

    const std::wstring macro_open = wide(request.value("macro_open", std::string()));
    const std::wstring macro_focus = wide(request.value("macro_focus", std::string()));
    const std::wstring macro_before_each = wide(request.value("macro_before_each", std::string()));
    const std::wstring macro_done = wide(request.value("macro_done", std::string()));
    const std::wstring macro_cancel = wide(request.value("macro_cancel", std::string()));

    // A registered in-session probe must prove it is running before any macro is
    // loaded; otherwise the panel would open with no way to fill its collector.
    if (failure.empty() && request.contains("require_identity")) {
        std::filesystem::path identity = wide(request.at("require_identity").get<std::string>());
        bool ok = false;
        try {
            std::ifstream input(identity, std::ios::binary);
            Json value;
            input >> value;
            ok = !value.value("terminated", false) && !value.value("command", "").empty();
            result["session_probe_identity"] = value;
        } catch (...) {
        }
        step("session_identity", {{"file", identity.u8string()}, {"available", ok}});
        if (!ok)
            failure = "session_probe_not_running";
    }

    // Optional view change before the panel opens: the same references must be
    // selected after the graphics window moved, so nothing may depend on where
    // a curve happens to be on screen.
    Json view_record = nullptr;
    if (failure.empty() && request.contains("view_rotate_deg") && stage != "cancel") {
        int window = -1;
        ProError window_code = ProWindowCurrentGet(&window);
        ProMdl window_model = nullptr;
        if (!window_code)
            window_code = ProWindowMdlGet(window, &window_model);
        bool matches = !window_code && window_model == model;
        if (!window_code && !matches) {
            ProMdlName shown = L"", wanted = L"";
            if (!ProMdlMdlnameGet(window_model, shown) && !ProMdlMdlnameGet(model, wanted))
                matches = !_wcsicmp(shown, wanted);
        }
        if (!matches && !ProMdlDisplay(model)) {
            ProMdl displayed = nullptr;
            if (!ProMdlWindowGet(model, &window) && !ProWindowMdlGet(window, &displayed))
                matches = displayed == model;
            window_code = matches ? PRO_TK_NO_ERROR : PRO_TK_GENERAL_ERROR;
        }
        ProMatrix before = {}, after = {};
        ProError before_code = PRO_TK_GENERAL_ERROR, set_code = PRO_TK_GENERAL_ERROR,
                after_code = PRO_TK_GENERAL_ERROR;
        int refit_code = -1, repaint_code = -1;
        const double degrees = request.at("view_rotate_deg").get<double>();
        if (matches) {
            before_code = ProViewMatrixGet(model, nullptr, before);
            ProMatrix target = {};
            build_view(degrees, target);
            set_code = ProViewMatrixSet(model, nullptr, target);
            if (!set_code) {
                refit_code = ProWindowRefit(window);
                ProWindowRefresh(window);
                repaint_code = ProWindowRepaint(window);
                after_code = ProViewMatrixGet(model, nullptr, after);
            }
        }
        const bool changed = !after_code && view_rotation_changed(before, after);
        view_record = {{"window", window},
                       {"window_code", (int)window_code},
                       {"window_matches_model", matches},
                       {"rotate_deg", degrees},
                       {"before_code", (int)before_code},
                       {"set_code", (int)set_code},
                       {"refit_code", refit_code},
                       {"repaint_code", repaint_code},
                       {"after_code", (int)after_code},
                       {"before", matrix_rows(before)},
                       {"after", matrix_rows(after)},
                       {"changed", changed}};
        step("view", view_record);
        if (!matches)
            failure = "view_window_mismatch";
        else if (set_code)
            failure = "view_not_applied";
        else if (!changed)
            failure = "view_unchanged";
    }
    result["view"] = view_record;

    Json panels = Json::array();
    Json selection_log = Json::array();
    Json features_before = Json::array();
    if (failure.empty() && (stage == "all" || stage == "session")) {
        ProError baseline_code = PRO_TK_NO_ERROR;
        features_before = feature_snapshot((ProSolid)model, baseline_code);
        result["features_before_count"] = (int)features_before.size();
        result["features_before_code"] = (int)baseline_code;
    }
    if (failure.empty()) {
        if (stage == "cancel") {
            panels.push_back(macro_load(macro_cancel, "panel_cancel"));
        } else {
            if (mode == "preselect") {
                // Record into the selection buffer first; the panel then consumes
                // the pre-selection. Kept as an explicit alternative mode.
            } else {
                panels.push_back(macro_load(macro_open, "panel_open"));
                if (!macro_focus.empty())
                    panels.push_back(macro_load(macro_focus, "panel_focus"));
            }
            if (stage != "resolve" && stage != "open" && stage != "session") {
                int position = 0;
                for (auto selection : selections) {
                    bool first = position == 0;
                    ProSelectRecordAction action =
                        first ? PRO_SELECT_OVERRIDE : PRO_SELECT_TOGGLE;
                    if (!macro_before_each.empty())
                        macro_load(macro_before_each, "panel_before_each");
                    ProError record_code = ProSelectExternalselectionRecord(selection, action);
                    Json row = {{"role", "first_dir"},
                                {"index", position},
                                {"geom_id", resolved[position]["geom_id"]},
                                {"owner", resolved[position]["owner"]},
                                {"api", "ProSelectExternalselectionRecord"},
                                {"selection_action",
                                 first ? "PRO_SELECT_OVERRIDE" : "PRO_SELECT_TOGGLE"},
                                {"error", (int)record_code}};
                    step("select", row);
                    selection_log.push_back(row);
                    position++;
                }
                result["selection_recorded"] = position;
            }
            if (mode == "preselect" && stage != "resolve") {
                panels.push_back(macro_load(macro_open, "panel_open"));
                if (!macro_focus.empty())
                    panels.push_back(macro_load(macro_focus, "panel_focus"));
            }
            if (stage == "all" || stage == "done")
                panels.push_back(macro_load(macro_done, "panel_done"));
        }
    }
    result["panel"] = panels;
    result["selection"] = selection_log;

    for (auto selection : selections)
        ProSelectionFree(&selection);

    if (failure.empty() && (stage == "all" || stage == "done" || stage == "session")) {
        Sleep(300);
        ProSolidRegenerate((ProSolid)model, PRO_REGEN_NO_FLAGS);
        ProError snapshot_code = PRO_TK_NO_ERROR;
        Json after = feature_snapshot((ProSolid)model, snapshot_code);
        result["features_after"] = after;
        result["features_after_code"] = (int)snapshot_code;
        if (request.contains("features_before")) {
            std::vector<int> known;
            for (const auto &row : request.at("features_before"))
                known.push_back(row.get<int>());
            Json created = Json::array();
            for (const auto &row : after) {
                int id = row["feature_id"].get<int>();
                bool existed = false;
                for (int previous : known)
                    if (previous == id)
                        existed = true;
                if (!existed)
                    created.push_back(row);
            }
            result["features_created"] = created;
        } else if (!features_before.empty()) {
            std::vector<int> known;
            for (const auto &row : features_before)
                known.push_back(row["feature_id"].get<int>());
            Json created = Json::array();
            for (const auto &row : after) {
                int id = row["feature_id"].get<int>();
                bool existed = false;
                for (int previous : known)
                    if (previous == id)
                        existed = true;
                if (!existed) {
                    Json created_row = row;
                    created_row["reference_parents"] = feature_parents((ProSolid)model, id);
                    created.push_back(created_row);
                }
            }
            result["features_created"] = created;
            result["features_before"] = features_before;
        }
    }

    result["success"] = failure.empty();
    if (!failure.empty())
        result["failure"] = failure;
    step("finish", {{"success", failure.empty()}, {"failure", failure}});
    ProEngineerDisconnect(&process, 15);
    std::ofstream(std::filesystem::path(g_job_dir) / L"probe_result.json", std::ios::binary)
        << result.dump(2);
    return failure.empty() ? 0 : 21;
}
