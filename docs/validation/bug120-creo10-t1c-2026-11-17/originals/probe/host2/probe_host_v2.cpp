// BUG-120 T1-C temporary in-session probe (v2): failure lock + controlled Done.
//
// Differences from the T1-B probe, and why they matter:
//   * The driving macro no longer ends with "Activate ... Done". In T1-B the Done
//     was pre-queued, so a failed selection could still submit the feature. Here
//     the dashboard is completed only by this module, only after every requested
//     reference was recorded successfully.
//   * No macro text is accepted from any input. The request file carries data
//     only (request id, model, ordered geometry ids); the Done macro is a
//     compile-time constant.
//   * A failed selection locks the run: no further selection, no TOGGLE retry,
//     no Done. Later invocations of the command are no-ops that only record that
//     they were suppressed.
//   * The module writes its own end marker (probe_end_marker.json) so the result
//     does not depend on the driver's own bookkeeping.
//
// ProMacroLoad is safe to call here: the SDK documents that a sequence is placed
// on the stack and executed once control returns to Creo, so queueing Done from
// inside a command callback does not re-enter the macro interpreter.
#define NOMINMAX
#include <windows.h>
#include <ProToolkit.h>
#include <ProUICmd.h>
#include <ProMdl.h>
#include <ProModelitem.h>
#include <ProSelection.h>
#include <ProCurve.h>
#include <ProArray.h>
#include <ProMenu.h>
#include <ProObjects.h>
#include <ProUtil.h>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include "third_party/json.hpp"

using Json = nlohmann::json;

// Fixed completion sequence. Never taken from input.
static const wchar_t *DONE_MACRO = L"~ Activate `main_dlg_cur` `dashInst0.Done`;";
static const char *COMMAND_NAME = "MechDogT1CSelect";

struct Reference {
    std::string owner;
    std::string role;
    int geom_id = -1;
};

static std::filesystem::path g_dir;
static std::string g_request_id;
static std::wstring g_model;
static std::vector<Reference> g_refs;
static size_t g_index = 0;
static bool g_prepared = false;
static bool g_locked = false;
static bool g_committed = false;
static std::string g_lock_reason;
static int g_done_code = -1;

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
    int size = MultiByteToWideChar(CP_UTF8, 0, value.data(), (int)value.size(), nullptr, 0);
    std::wstring result(size, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, value.data(), (int)value.size(), result.data(), size);
    return result;
}

static void append_step(const Json &row) {
    std::ofstream out(g_dir / L"session_v2_steps.jsonl", std::ios::binary | std::ios::app);
    out << row.dump() << "\n";
}

// One authoritative end marker, replaced atomically so a reader never sees a
// half-written file.
static void write_marker() {
    Json marker = {
        {"request_id", g_request_id},
        {"state", g_committed ? "committed" : (g_locked ? "locked" : (g_prepared ? "prepared" : "idle"))},
        {"prepared", g_prepared},
        {"locked", g_locked},
        {"lock_reason", g_lock_reason},
        {"committed", g_committed},
        {"selections_ok", g_index},
        {"selections_total", g_refs.size()},
        {"done_macro", utf8(DONE_MACRO)},
        {"done_macro_code", g_done_code},
        {"tick_ms", (long long)GetTickCount64()},
    };
    std::filesystem::path target = g_dir / L"probe_end_marker.json";
    std::filesystem::path temp = g_dir / L"probe_end_marker.json.tmp";
    {
        std::ofstream out(temp, std::ios::binary | std::ios::trunc);
        out << marker.dump(2);
    }
    std::error_code error;
    std::filesystem::remove(target, error);
    std::filesystem::rename(temp, target, error);
}

static void lock_run(const std::string &reason, const Json &detail) {
    g_locked = true;
    g_lock_reason = reason;
    Json row = {{"phase", "lock"}, {"reason", reason}, {"index", (int)g_index}};
    for (auto it = detail.begin(); it != detail.end(); ++it)
        row[it.key()] = it.value();
    append_step(row);
    write_marker();
}

// Bind the request, the current model and every reference before any selection.
static bool prepare() {
    std::ifstream input(g_dir / L"probe_request_v2.json", std::ios::binary);
    if (!input) {
        lock_run("request_missing", {});
        return false;
    }
    Json request;
    try {
        input >> request;
    } catch (...) {
        lock_run("request_invalid", {});
        return false;
    }
    // A different request id starts a new run: refresh_request_id() already
    // cleared the per-request flags before we got here.
    g_request_id = request.value("request_id", std::string());
    g_model = wide(request.value("model", std::string()));
    g_refs.clear();
    for (const auto &entry : request.at("curves")) {
        Reference reference;
        reference.owner = entry.value("owner", std::string());
        reference.role = entry.value("role", std::string("first_dir"));
        reference.geom_id = entry.value("geom_id", -1);
        g_refs.push_back(reference);
    }

    ProMdl model = nullptr;
    ProError code = ProMdlCurrentGet(&model);
    ProMdlName actual = L"";
    if (!code)
        code = ProMdlMdlnameGet(model, actual);
    if (code || _wcsicmp(actual, g_model.c_str())) {
        lock_run("current_model_mismatch",
                 {{"observed", code ? std::string() : utf8(actual)}, {"expected", utf8(g_model)}});
        return false;
    }
    for (const auto &reference : g_refs) {
        if (_wcsicmp(wide(reference.owner).c_str(), actual)) {
            lock_run("reference_owner_mismatch",
                     {{"geom_id", reference.geom_id}, {"owner", reference.owner}});
            return false;
        }
        ProModelitem item;
        if (ProModelitemInit(model, reference.geom_id, PRO_CURVE, &item) != PRO_TK_NO_ERROR) {
            lock_run("reference_not_a_curve", {{"geom_id", reference.geom_id}});
            return false;
        }
        ProCurve curve;
        if (ProCurveInit((ProSolid)model, reference.geom_id, &curve) != PRO_TK_NO_ERROR) {
            lock_run("reference_curve_init_failed", {{"geom_id", reference.geom_id}});
            return false;
        }
        ProEnttype type = PRO_ENT_LINE;
        if (ProCurveTypeGet(curve, &type) != PRO_TK_NO_ERROR) {
            lock_run("reference_curve_type_failed", {{"geom_id", reference.geom_id}});
            return false;
        }
    }
    g_prepared = true;
    append_step({{"phase", "prepare"},
                 {"request_id", g_request_id},
                 {"model", utf8(g_model)},
                 {"references", (int)g_refs.size()}});
    write_marker();
    return true;
}

static uiCmdAccessState access(uiCmdAccessMode) { return ACCESS_AVAILABLE; }

// A new request id in the bound request file starts a fresh run. Without this a
// second case in the same Creo session would stay suppressed by the first one.
static void refresh_request_id() {
    std::ifstream input(g_dir / L"probe_request_v2.json", std::ios::binary);
    if (!input)
        return;
    Json request;
    try {
        input >> request;
    } catch (...) {
        return;
    }
    const std::string id = request.value("request_id", std::string());
    if (id.empty() || id == g_request_id)
        return;
    g_request_id = id;
    g_index = 0;
    g_prepared = false;
    g_locked = false;
    g_committed = false;
    g_lock_reason.clear();
    g_done_code = -1;
    g_refs.clear();
}

static int select_next(uiCmdCmdId, uiCmdValue *, void *) {
    refresh_request_id();
    // A locked or committed run never touches the collector again.
    if (g_locked || g_committed) {
        append_step({{"phase", "suppressed"},
                     {"request_id", g_request_id},
                     {"locked", g_locked},
                     {"committed", g_committed},
                     {"index", (int)g_index}});
        return 0;
    }
    if (!g_prepared && !prepare()) {
        append_step({{"phase", "suppressed"}, {"request_id", g_request_id}, {"why", "prepare_failed"}});
        return 0;
    }
    if (g_index >= g_refs.size()) {
        append_step({{"phase", "suppressed"}, {"request_id", g_request_id}, {"why", "index_out_of_range"}});
        return 0;
    }

    ProMdl model = nullptr;
    ProError code = ProMdlCurrentGet(&model);
    if (code) {
        lock_run("current_model_lost", {{"error", (int)code}});
        return 0;
    }
    const Reference &reference = g_refs[g_index];
    ProModelitem item;
    code = ProModelitemInit(model, reference.geom_id, PRO_CURVE, &item);
    ProSelection selection = nullptr;
    if (!code)
        code = ProSelectionAlloc(nullptr, &item, &selection);
    const bool first = g_index == 0;
    const ProSelectRecordAction action = first ? PRO_SELECT_OVERRIDE : PRO_SELECT_TOGGLE;
    if (!code)
        code = ProSelectExternalselectionRecord(selection, action);
    if (selection)
        ProSelectionFree(&selection);

    append_step({{"phase", "select"},
                 {"request_id", g_request_id},
                 {"index", (int)g_index},
                 {"role", reference.role},
                 {"owner", reference.owner},
                 {"geom_id", reference.geom_id},
                 {"api", "ProSelectExternalselectionRecord"},
                 {"selection_action", first ? "PRO_SELECT_OVERRIDE" : "PRO_SELECT_TOGGLE"},
                 {"error", (int)code}});

    if (code) {
        // No advance, no retry, no Done. The dashboard is left open on purpose.
        lock_run("selection_rejected",
                 {{"geom_id", reference.geom_id}, {"error", (int)code}, {"action", first ? "OVERRIDE" : "TOGGLE"}});
        return 0;
    }

    g_index++;
    write_marker();
    if (g_index == g_refs.size()) {
        // Every requested position was accepted: only now queue the completion.
        g_committed = true;
        write_marker();
        g_done_code = (int)ProMacroLoad(const_cast<wchar_t *>(DONE_MACRO));
        append_step({{"phase", "commit"},
                     {"request_id", g_request_id},
                     {"selections", (int)g_index},
                     {"done_macro_code", g_done_code}});
        write_marker();
    }
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
        Json identity = {{"command", COMMAND_NAME},
                         {"module_file", std::filesystem::path(filename).u8string()},
                         {"process_id", GetCurrentProcessId()},
                         {"initialized_tick_ms", (long long)GetTickCount64()},
                         {"terminated", false},
                         {"done_macro", utf8(DONE_MACRO)},
                         {"accepts_macro_text_from_input", false}};
        std::ofstream(g_dir / L"probe_identity_v2.json", std::ios::binary) << identity.dump(2);
        uiCmdCmdId id;
        ProError code = ProCmdActionAdd(const_cast<char *>(COMMAND_NAME), select_next,
                                        uiProeAsynch, access, PRO_B_FALSE, PRO_B_FALSE, &id);
        if (code) {
            wcscpy_s(errmsg, 80, L"Cannot register the T1-C probe command");
            return code;
        }
        return PRO_TK_NO_ERROR;
    } catch (...) {
        wcscpy_s(errmsg, 80, L"Invalid T1-C probe configuration");
        return PRO_TK_BAD_INPUTS;
    }
}

extern "C" __declspec(dllexport) void user_terminate() {
    try {
        Json identity;
        std::ifstream in(g_dir / L"probe_identity_v2.json", std::ios::binary);
        if (in)
            in >> identity;
        identity["terminated"] = true;
        std::ofstream(g_dir / L"probe_identity_v2.json", std::ios::binary) << identity.dump(2);
    } catch (...) {
    }
}
