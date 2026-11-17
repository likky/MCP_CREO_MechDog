// BUG-120 T1-B temporary in-session probe.
//
// The asynchronous Toolkit program proved that a dashboard cannot be driven
// step by step from outside: once the Boundary Blend dashboard is open the
// session stops completing further asynchronous UI calls. The selection must
// therefore happen inside the session, while the collector is active, which is
// what this temporary registered Toolkit application does.
//
// It registers one command. A single macro opens the native Boundary Blend
// dashboard, invokes the command once per requested reference and then clicks
// Done. Each invocation resolves the reference from the live model by geometry
// id, records it with ProSelectExternalselectionRecord and appends one line to
// session_steps.jsonl.
//
// Selection semantics from the installed SDK header (ProSelection.h):
//   PRO_SELECT_OVERRIDE - unmodified selection
//   PRO_SELECT_TOGGLE   - CTRL modified selection
// First reference of a collector uses OVERRIDE, every later reference of the
// same collector uses TOGGLE. The loop never branches on 2, 3 or 5 sections.
#define NOMINMAX
#include <windows.h>
#include <ProToolkit.h>
#include <ProUICmd.h>
#include <ProMdl.h>
#include <ProModelitem.h>
#include <ProSelection.h>
#include <ProCurve.h>
#include <ProArray.h>
#include <ProObjects.h>
#include <ProUtil.h>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include "third_party/json.hpp"

using Json = nlohmann::json;

static std::filesystem::path g_dir;
static std::string g_command = "MechDogT1BSelect";
static Json g_request;
static std::string g_request_id;
static std::wstring g_model;
static size_t g_index = 0;
static bool g_ready = false, g_blocked = false, g_resolved = false;

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
        return std::wstring();
    std::wstring result(size, L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), (int)value.size(),
                        result.data(), size);
    return result;
}

static void append(const std::filesystem::path &file, const Json &entry) {
    try {
        std::ofstream out(file, std::ios::binary | std::ios::app);
        out << entry.dump() << "\n";
        out.flush();
    } catch (...) {
    }
}

static void step(const Json &entry) {
    Json row = entry;
    row["source"] = "session_command";
    row["request_id"] = g_request_id;
    row["tick_ms"] = (long long)GetTickCount64();
    append(g_dir / L"session_steps.jsonl", row);
}

static void write_state() {
    try {
        Json state = {{"request_id", g_request_id},
                      {"command", g_command},
                      {"resolved", g_resolved},
                      {"blocked", g_blocked},
                      {"selected", (int)g_index},
                      {"expected", g_request.contains("curves") ? (int)g_request["curves"].size()
                                                                : 0},
                      {"model", utf8(g_model)}};
        std::ofstream out(g_dir / L"probe_state.json", std::ios::binary);
        out << state.dump(2);
    } catch (...) {
    }
}

// Resolve every reference once, before the first selection, so a wrong id,
// wrong owner or wrong curve is recorded as a refusal instead of a silent pick.
static void resolve_all(ProMdl model) {
    g_resolved = true;
    Json references = Json::array();
    size_t position = 0;
    for (const auto &entry : g_request.at("curves")) {
        Json row = {{"index", (int)position},
                    {"role", entry.value("role", std::string("first_dir"))},
                    {"owner", entry.value("owner", std::string())},
                    {"geom_id", entry.value("geom_id", -1)},
                    {"feature_id", entry.value("feature_id", -1)}};
        std::wstring owner = wide(entry.value("owner", std::string()));
        if (_wcsicmp(owner.c_str(), g_model.c_str())) {
            row["error"] = "owner_mismatch";
            g_blocked = true;
        } else {
            int geom_id = entry.value("geom_id", -1);
            ProModelitem item;
            ProError code = ProModelitemInit(model, geom_id, PRO_CURVE, &item);
            row["modelitem_error"] = (int)code;
            if (!code) {
                ProCurve curve;
                code = ProCurveInit((ProSolid)model, geom_id, &curve);
                row["curve_init_error"] = (int)code;
            }
            if (!code) {
                ProCurve curve;
                ProCurveInit((ProSolid)model, geom_id, &curve);
                ProEnttype kind;
                code = ProCurveTypeGet(curve, &kind);
                row["curve_type"] = (int)kind;
                if (!code && kind != PRO_ENT_LINE && kind != PRO_ENT_SPLINE &&
                    kind != PRO_ENT_ARC)
                    code = PRO_TK_BAD_INPUTS;
                row["curve_type_error"] = (int)code;
            }
            if (!code) {
                ProCurve curve;
                ProCurveInit((ProSolid)model, geom_id, &curve);
                double length = 0;
                code = ProCurveLengthEval(curve, &length);
                row["curve_length_mm"] = length;
                row["curve_length_error"] = (int)code;
            }
            if (!code) {
                ProCurve curve;
                ProCurveInit((ProSolid)model, geom_id, &curve);
                ProGeomitemdata *data = nullptr;
                code = ProCurveDataGet(curve, &data);
                row["curve_data_error"] = (int)code;
                if (!code && data && data->data.p_curve_data &&
                    data->data.p_curve_data->line.type == PRO_ENT_LINE) {
                    row["end1"] = {data->data.p_curve_data->line.end1[0],
                                   data->data.p_curve_data->line.end1[1],
                                   data->data.p_curve_data->line.end1[2]};
                    row["end2"] = {data->data.p_curve_data->line.end2[0],
                                   data->data.p_curve_data->line.end2[1],
                                   data->data.p_curve_data->line.end2[2]};
                }
                if (data)
                    ProGeomitemdataFree(&data);
            }
            if (code) {
                row["error"] = "reference_unresolved";
                g_blocked = true;
            } else {
                row["resolved"] = true;
            }
        }
        references.push_back(row);
        position++;
    }
    step({{"phase", "resolve_all"}, {"references", references}, {"blocked", g_blocked}});
    write_state();
}

// The request for this run is written next to the module before the macro is
// loaded, so the first command invocation picks it up. A new request_id resets
// the index; the same request_id never replays a completed run.
static void load_request() {
    try {
        std::ifstream input(g_dir / L"probe_request.json", std::ios::binary);
        if (!input)
            return;
        Json request;
        input >> request;
        std::string id = request.value("request_id", std::string());
        if (id.empty() || id == g_request_id)
            return;
        g_request = request;
        g_request_id = id;
        g_model = wide(request.value("model", std::string()));
        g_index = 0;
        g_resolved = false;
        g_blocked = false;
        g_ready = true;
        step({{"phase", "load_request"},
              {"model", request.value("model", std::string())},
              {"expected", (int)request.at("curves").size()}});
        write_state();
    } catch (...) {
        g_ready = false;
    }
}

static uiCmdAccessState access(uiCmdAccessMode) {
    return ACCESS_AVAILABLE;
}

static int select_next(uiCmdCmdId, uiCmdValue *, void *) {
    load_request();
    if (!g_ready) {
        step({{"phase", "select"}, {"index", (int)g_index}, {"error", "no_request"}});
        return 0;
    }
    ProMdl model = nullptr;
    ProError code = ProMdlCurrentGet(&model);
    ProMdlName actual = L"";
    if (!code)
        code = ProMdlMdlnameGet(model, actual);
    if (code || _wcsicmp(actual, g_model.c_str())) {
        step({{"phase", "select"},
              {"index", (int)g_index},
              {"error", "current_model_mismatch"},
              {"observed", utf8(actual)},
              {"expected", utf8(g_model)}});
        return 0;
    }
    if (!g_resolved)
        resolve_all(model);
    if (g_blocked) {
        step({{"phase", "select"}, {"index", (int)g_index}, {"error", "request_blocked"}});
        return 0;
    }
    if (g_index >= g_request.at("curves").size()) {
        step({{"phase", "select"}, {"index", (int)g_index}, {"error", "request_exhausted"}});
        return 0;
    }
    const auto &entry = g_request.at("curves")[g_index];
    int geom_id = entry.value("geom_id", -1);
    ProModelitem item;
    code = ProModelitemInit(model, geom_id, PRO_CURVE, &item);
    ProSelection selection = nullptr;
    if (!code)
        code = ProSelectionAlloc(nullptr, &item, &selection);
    bool first = g_index == 0;
    ProSelectRecordAction action = first ? PRO_SELECT_OVERRIDE : PRO_SELECT_TOGGLE;
    if (!code)
        code = ProSelectExternalselectionRecord(selection, action);
    if (selection)
        ProSelectionFree(&selection);
    Json row = {{"phase", "select"},
                {"index", (int)g_index},
                {"role", entry.value("role", std::string("first_dir"))},
                {"owner", entry.value("owner", std::string())},
                {"geom_id", geom_id},
                {"feature_id", entry.value("feature_id", -1)},
                {"api", "ProSelectExternalselectionRecord"},
                {"selection_action", first ? "PRO_SELECT_OVERRIDE" : "PRO_SELECT_TOGGLE"},
                {"error", (int)code}};
    step(row);
    if (!code)
        g_index++;
    write_state();
    return 0;
}

extern "C" __declspec(dllexport) int user_initialize(int, char **, char *, char *,
                                                     wchar_t errmsg[80]) {
    try {
        wchar_t filename[MAX_PATH];
        HMODULE self = nullptr;
        if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                (LPCWSTR)&user_initialize, &self) ||
            !GetModuleFileNameW(self, filename, MAX_PATH))
            return PRO_TK_GENERAL_ERROR;
        g_dir = std::filesystem::path(filename).parent_path();
        std::ifstream config(g_dir / L"probe_config.json", std::ios::binary);
        if (config) {
            Json value;
            config >> value;
            if (value.contains("command"))
                g_command = value.at("command").get<std::string>();
        }
        Json identity = {{"command", g_command},
                         {"module_file", std::filesystem::path(filename).u8string()},
                         {"process_id", GetCurrentProcessId()},
                         {"initialized_tick_ms", (long long)GetTickCount64()},
                         {"terminated", false}};
        std::ofstream(g_dir / L"probe_identity.json", std::ios::binary) << identity.dump(2);
        uiCmdCmdId id;
        ProError code = ProCmdActionAdd(const_cast<char *>(g_command.c_str()), select_next,
                                        uiProeAsynch, access, PRO_B_FALSE, PRO_B_FALSE, &id);
        if (code) {
            wcscpy_s(errmsg, 80, L"Cannot register the T1-B probe command");
            return code;
        }
        return PRO_TK_NO_ERROR;
    } catch (...) {
        wcscpy_s(errmsg, 80, L"Invalid T1-B probe configuration");
        return PRO_TK_BAD_INPUTS;
    }
}

extern "C" __declspec(dllexport) void user_terminate() {
    try {
        Json identity;
        std::ifstream in(g_dir / L"probe_identity.json", std::ios::binary);
        if (in)
            in >> identity;
        identity["terminated"] = true;
        std::ofstream(g_dir / L"probe_identity.json", std::ios::binary) << identity.dump(2);
    } catch (...) {
    }
}
