// T1-C feature lister: read-only inventory of the current model's features.
//
// Replaces the drive probe's post-run scan, which fails inside this environment
// once a freshly committed boundary blend is present (the process dies with
// 0xC0000409 before writing its result). This program opens no dashboard, sends
// no macro and writes no geometry: it only visits features and reports ids,
// types, incomplete flags, statuses and parent ids.
#define NOMINMAX
#include <windows.h>
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
#include <ProFeature.h>
#include <ProArray.h>
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

struct Collector {
    Json features = Json::array();
};

static ProError feature_cb(ProFeature *feature, ProError status, ProAppData data) {
    auto *collector = static_cast<Collector *>(data);
    if (status || !feature)
        return PRO_TK_NO_ERROR;
    Json row = {{"feature_id", feature->id}};

    ProFeattype type = 0;
    if (ProFeatureTypeGet(feature, &type) == PRO_TK_NO_ERROR)
        row["type"] = (int)type;

    ProBoolean incomplete = PRO_B_FALSE;
    if (ProFeatureIsIncomplete(feature, &incomplete) == PRO_TK_NO_ERROR)
        row["incomplete"] = (incomplete == PRO_B_TRUE);

    ProFeatStatus feat_status = PRO_FEAT_ACTIVE;
    if (ProFeatureStatusGet(feature, &feat_status) == PRO_TK_NO_ERROR)
        row["status"] = (int)feat_status;

    int *parents = nullptr;
    int parent_count = 0;
    if (ProFeatureParentsGet(feature, &parents, &parent_count) == PRO_TK_NO_ERROR && parents) {
        Json list = Json::array();
        for (int i = 0; i < parent_count; i++)
            list.push_back(parents[i]);
        row["parent_ids"] = list;
        // ProFeatureParentsGet allocates with ProArray; leaving it allocated
        // corrupts the heap of a long-running async program.
        ProArrayFree((ProArray *)&parents);
    }
    collector->features.push_back(row);
    return PRO_TK_NO_ERROR;
}

int wmain(int argc, wchar_t **argv) {
    if (argc != 2)
        return 2;
    const std::wstring dir = argv[1];
    const std::filesystem::path base(dir);

    std::ifstream input(base / L"probe.json", std::ios::binary);
    Json request;
    try {
        input >> request;
    } catch (...) {
        return 3;
    }
    const std::string request_id = request.value("request_id", std::string("unnamed"));
    const std::string model_expected = request.value("model", std::string());

    Json result = {{"request_id", request_id}, {"probe", "t1c-features"}};

    ProProcessHandle process = {};
    ProError code = connect_creo(&process, 30);
    result["connect_code"] = (int)code;
    if (code) {
        result["success"] = false;
        result["failure"] = "connect";
        std::ofstream(base / L"probe_result.json", std::ios::binary) << result.dump(2);
        return 1;
    }

    ProMdl current = nullptr;
    code = ProMdlCurrentGet(&current);
    ProMdlName name = {};
    if (!code && current)
        code = ProMdlMdlnameGet(current, name);
    result["current_model"] = code ? std::string() : utf8(name);
    if (code || !current || model_expected != utf8(name)) {
        result["success"] = false;
        result["failure"] = "model_mismatch";
        std::ofstream(base / L"probe_result.json", std::ios::binary) << result.dump(2);
        ProEngineerDisconnect(&process, 10);
        return 4;
    }

    Collector collector;
    ProSolidFeatVisit((ProSolid)current, feature_cb, nullptr, &collector);
    result["features"] = collector.features;
    result["count"] = (int)collector.features.size();
    int max_id = 0;
    for (const auto &row : collector.features) {
        const int id = row.value("feature_id", 0);
        max_id = id > max_id ? id : max_id;
    }
    result["max_id"] = max_id;
    result["success"] = true;

    std::ofstream(base / L"probe_result.json", std::ios::binary) << result.dump(2);
    ProEngineerDisconnect(&process, 20);
    return 0;
}
