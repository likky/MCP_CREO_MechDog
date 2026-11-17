// T1-C loader: load the in-session probe DLL through the documented Toolkit API.
//
// The Auxiliary Applications dialog is the interactive route and needs the
// machine owner to accept the unsigned-DLL warning. The owner approved using the
// programmatic route instead, which is Creo's own developer API: it changes no
// security configuration and only loads the DLL compiled in this test directory.
//
// Nothing here writes geometry; it loads one DLL and reports the return codes.
#define NOMINMAX
#include <windows.h>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <string>
#include <ProToolkit.h>
#include <ProCore.h>
#include <ProToolkitDll.h>
#include "third_party/json.hpp"

using Json = nlohmann::json;

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

int wmain(int argc, wchar_t **argv) {
    if (argc != 2)
        return 2;
    const std::wstring dir = argv[1];
    std::ifstream input(std::filesystem::path(dir) / L"load.json", std::ios::binary);
    Json request;
    try {
        input >> request;
    } catch (...) {
        return 3;
    }
    const std::string app_name = request.value("app_name", std::string("T1CProbeV2"));
    const std::string exec_file = request.value("exec_file", std::string());
    const std::string text_dir = request.value("text_dir", std::string());

    Json result = {{"app_name", app_name}, {"exec_file", exec_file}, {"text_dir", text_dir}};

    ProProcessHandle process = {};
    ProError code = connect_creo(&process, 30);
    result["connect_code"] = (int)code;
    if (code) {
        result["success"] = false;
        result["failure"] = "connect";
        std::ofstream(std::filesystem::path(dir) / L"load_result.json", std::ios::binary)
            << result.dump(2);
        return 1;
    }

    ProName name = L"";
    std::wstring wide_name(app_name.begin(), app_name.end());
    wcsncpy_s(name, wide_name.c_str(), _TRUNCATE);

    if (request.value("unload", false)) {
        ProToolkitDllHandle existing = nullptr;
        ProError get_code = ProToolkitDllHandleGet(name, &existing);
        result["handle_get_code"] = (int)get_code;
        if (!get_code && existing) {
            code = ProToolkitDllUnload(existing);
            result["unload_code"] = (int)code;
            result["success"] = code == PRO_TK_NO_ERROR;
        } else {
            result["success"] = false;
            result["failure"] = "handle_not_found";
        }
        std::ofstream(std::filesystem::path(dir) / L"load_result.json", std::ios::binary)
            << result.dump(2);
        ProEngineerDisconnect(&process, 20);
        return result["success"].get<bool>() ? 0 : 1;
    }

    ProCharPath exec = "";
    strncpy_s(exec, sizeof(exec), exec_file.c_str(), _TRUNCATE);
    ProCharPath text = "";
    strncpy_s(text, sizeof(text), text_dir.c_str(), _TRUNCATE);

    ProToolkitDllHandle handle = nullptr;
    ProError user_error = PRO_TK_NO_ERROR;
    ProPath user_string = L"";
    code = ProToolkitDllLoad(name, exec, text, PRO_B_FALSE, &handle, &user_error, user_string);
    result["load_code"] = (int)code;
    result["user_error_code"] = (int)user_error;
    result["user_string"] = std::filesystem::path(user_string).u8string();
    result["handle_non_null"] = handle != nullptr;
    result["success"] = code == PRO_TK_NO_ERROR;

    std::ofstream(std::filesystem::path(dir) / L"load_result.json", std::ios::binary)
        << result.dump(2);
    ProEngineerDisconnect(&process, 20);
    return result["success"].get<bool>() ? 0 : 1;
}
