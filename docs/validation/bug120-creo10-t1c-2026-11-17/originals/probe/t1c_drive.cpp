// T1-C driving probe: opens the native Boundary Blend dashboard and lets the
// in-session module do the selections and the completion.
//
// The macro is built here from a fixed template and the requested reference
// count. No macro text is read from input, and the tail is deliberately NOT
// "Done": the completion is queued by the in-session module only after every
// selection succeeded, so a rejected selection can no longer submit a feature.
//
// This program is read-only apart from queueing that macro. It never writes
// geometry itself, never saves and never erases a model.
#define NOMINMAX
#include <windows.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <string>
#include <thread>
#include <vector>
#include <ProToolkit.h>
#include <ProCore.h>
#include <ProMdl.h>
#include <ProModelitem.h>
#include <ProSolid.h>
#include <ProFeature.h>
#include <ProArray.h>
#include <ProFeatType.h>
#include <ProMenu.h>
#include <ProUtil.h>
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

struct FeatureScan {
    int max_id = 0;
    int count = 0;
    std::vector<int> ids;
};

// The process has been dying with 0xC0000409 a fixed five seconds after the
// wait loop ends, before probe_result.json appears. Each stage appends one line
// so the next run says exactly which call never returns.
static void trace(const std::filesystem::path &dir, const char *label) {
    std::ofstream out(dir / L"trace.log", std::ios::app | std::ios::binary);
    out << label << "\n";
    out.flush();
}

static ProError feature_cb(ProFeature *feature, ProError status, ProAppData data) {
    auto *scan = static_cast<FeatureScan *>(data);
    if (status)
        return PRO_TK_NO_ERROR;
    int id = feature->id;
    scan->count++;
    scan->ids.push_back(id);
    scan->max_id = id > scan->max_id ? id : scan->max_id;
    return PRO_TK_NO_ERROR;
}

static Json scan_features(ProSolid solid) {
    FeatureScan scan;
    ProSolidFeatVisit(solid, feature_cb, nullptr, &scan);
    Json ids = Json::array();
    for (int id : scan.ids)
        ids.push_back(id);
    return {{"count", scan.count}, {"max_id", scan.max_id}, {"ids", ids}};
}

static Json describe_feature(ProSolid solid, int feature_id) {
    ProFeature feature;
    if (ProFeatureInit(solid, feature_id, &feature) != PRO_TK_NO_ERROR)
        return nullptr;
    ProFeattype type = 0;
    ProFeatureTypeGet(&feature, &type);
    ProBoolean incomplete = PRO_B_FALSE;
    ProFeatureIsIncomplete(&feature, &incomplete);
    ProFeatStatus status = PRO_FEAT_ACTIVE;
    ProFeatureStatusGet(&feature, &status);
    Json parents = Json::array();
    int *list = nullptr;
    int count = 0;
    if (ProFeatureParentsGet(&feature, &list, &count) == PRO_TK_NO_ERROR && list) {
        for (int i = 0; i < count; i++)
            parents.push_back(list[i]);
        // The SDK allocates this with ProArray; the missing free is what made
        // the post-run scan die with 0xC0000409 instead of returning.
        ProArrayFree((ProArray *)&list);
    }
    return {{"feature_id", feature_id},
            {"type", (int)type},
            {"incomplete", incomplete == PRO_B_TRUE},
            {"status", (int)status},
            {"parent_ids", parents}};
}

int wmain(int argc, wchar_t **argv) {
    if (argc != 2)
        return 2;
    const std::wstring dir = argv[1];
    const std::filesystem::path base(dir);
    std::ifstream input(std::filesystem::path(dir) / L"probe.json", std::ios::binary);
    Json request;
    try {
        input >> request;
    } catch (...) {
        return 3;
    }
    const std::string request_id = request.value("request_id", std::string("unnamed"));
    trace(base, "start");
    const std::string model_expected = request.value("model", std::string());
    const int curves = (int)request.at("curves").size();
    const int wait_seconds = request.value("wait_seconds", 45);

    Json result = {{"request_id", request_id},
                   {"probe", "t1c-drive"},
                   {"model", model_expected},
                   {"requested_references", curves}};

    std::filesystem::path marker = std::filesystem::path(dir).parent_path().parent_path() /
                                   L"probe" / L"host2" / L"probe_end_marker.json";
    if (request.contains("marker_path"))
        marker = std::filesystem::path(request.at("marker_path").get<std::string>());
    std::error_code ignored;
    std::filesystem::remove(marker, ignored);
    result["marker_path"] = marker.u8string();

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
    trace(base, "connected");
    ProMdlName name = {};
    if (!code && current)
        code = ProMdlMdlnameGet(current, name);
    result["current_model"] = code ? std::string() : utf8(name);
    if (code || model_expected != utf8(name)) {
        result["success"] = false;
        result["failure"] = "model_mismatch";
        std::ofstream(std::filesystem::path(dir) / L"probe_result.json", std::ios::binary)
            << result.dump(2);
        ProEngineerDisconnect(&process, 10);
        return 4;
    }

    const Json before = scan_features((ProSolid)current);
    result["features_before"] = before;
    trace(base, "scanned_before");

    // Fixed template: open the dashboard, then one command invocation per
    // reference. No Done here - the module owns the completion. The optional
    // "quit" tail replays the cancel sequence recorded in Creo's own trail
    // (Enter + Activate on dashInst0.Quit), never a guessed control name.
    const std::string select_command = request.value("select_command", std::string("MechDogT1CSelect"));
    const std::string tail = request.value("tail", std::string("none"));
    std::wstring macro = L"~ Command `ProCmdFtBndBlend`;";
    for (int i = 0; i < curves; i++)
        macro += L" ~ Command `" + std::wstring(select_command.begin(), select_command.end()) + L"`;";
    if (tail == "quit" || tail == "quit_yes") {
        macro += L" ~ Enter `main_dlg_cur` `dashInst0.Quit`;"
                 L" ~ Activate `main_dlg_cur` `dashInst0.Quit`;";
    }
    if (tail == "quit_yes") {
        // The confirmation step is in Creo's own trail (trail.txt.1, right after
        // the two Quit lines): "! Message Dialog: Warning / 确实要取消吗?" then
        // "~ Activate `UI Message Dialog` `yes`". So the whole cancel really is
        // macroable; there is no need to click it by hand.
        macro += L" ~ Activate `UI Message Dialog` `yes`;";
    }
    result["tail"] = tail;
    result["select_command"] = select_command;
    result["macro"] = utf8(macro);
    result["macro_api_code"] = (int)ProMacroLoad(macro.data());
    trace(base, "macro_queued");

    Json marker_value;
    bool seen = false;
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(wait_seconds);
    while (std::chrono::steady_clock::now() < deadline) {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        std::ifstream in(marker, std::ios::binary);
        if (!in)
            continue;
        try {
            in >> marker_value;
            seen = true;
            if (marker_value.value("committed", false) || marker_value.value("locked", false))
                break;
        } catch (...) {
        }
    }
    result["end_marker"] = marker_value;
    result["end_marker_seen"] = seen;
    trace(base, "loop_done");

    // While the dashboard is still open the UI thread cannot service another
    // Toolkit call from this asynchronous program, so the post-run scan is only
    // safe when the run committed (or when nothing was opened at all).
    //
    // Even after a commit this scan is not reliable here: twice it died with
    // 0xC0000409 about five seconds after the wait ended, while the standalone
    // lister (t1c_features.exe) reads the same model in under five seconds.
    // Callers therefore pass post_scan=false and take the inventory separately.
    // A marker that is absent or only partly written must not be read as an
    // object: nlohmann throws on type mismatch and an uncaught throw aborts the
    // process (0xC0000409), which is exactly what happened before this guard.
    const bool marker_is_object = marker_value.is_object();
    const bool locked_with_panel = marker_is_object && marker_value.value("locked", false);
    trace(base, "read_locked");
    const bool cancel_pending = tail == "quit" || tail == "quit_yes";
    const bool post_scan = request.value("post_scan", true);
    trace(base, "read_flags");
    if (locked_with_panel || cancel_pending || !post_scan) {
        result["features_after"] = nullptr;
        result["features_created"] = Json::array();
        trace(base, "cleared_scan_fields");
        result["scan_skipped"] = cancel_pending
                                     ? "dashboard interaction pending"
                                     : (locked_with_panel ? "run locked, dashboard left open"
                                                          : "post_scan disabled; use t1c_features.exe");
        result["success"] = true;
        trace(base, "result_ready");
        std::ofstream(std::filesystem::path(dir) / L"probe_result.json", std::ios::binary)
            << result.dump(2);
        trace(base, "written");
        ProEngineerDisconnect(&process, 20);
        trace(base, "disconnected");
        return 0;
    }

    const Json after = scan_features((ProSolid)current);
    result["features_after"] = after;
    Json created = Json::array();
    std::vector<int> before_ids = before.at("ids").get<std::vector<int>>();
    for (int id : after.at("ids").get<std::vector<int>>()) {
        if (std::find(before_ids.begin(), before_ids.end(), id) == before_ids.end())
            created.push_back(describe_feature((ProSolid)current, id));
    }
    result["features_created"] = created;
    result["success"] = true;
    std::ofstream(std::filesystem::path(dir) / L"probe_result.json", std::ios::binary)
        << result.dump(2);
    ProEngineerDisconnect(&process, 20);
    return 0;
}
