// BUG-142 controlled helper test. No Creo/Toolkit calls and no real model success.
#define NOMINMAX
#include "worker_result_delivery.h"
#include <filesystem>

int wmain(int argc, wchar_t **argv) {
    if (argc != 3)
        return 2;
    const std::wstring job = argv[2];
    std::ifstream mode_file(job + L"\\scenario.txt");
    std::string mode;
    mode_file >> mode;
    const bool success = mode == "success" || mode == "invalid_utf8_complete";
    nlohmann::json report = {{"success", success},
                             {"toolkit_code", success ? 0 : -4},
                             {"message", success ? "fixture success" : "fixture operation failed"},
                             {"fixture_only", true}};
    if (mode == "invalid_utf8" || mode == "invalid_utf8_complete" ||
        mode == "strict_dump_crash") {
        // A Toolkit-shaped string that is not valid UTF-8. nlohmann's default
        // handler throws on it; the replacement handler publishes it.
        report["message"] = std::string("toolkit text with invalid \x92 byte");
    }
    if (mode == "strict_dump_crash") {
        // BUG-142 pre-fix reproduction: the old publication path called
        // dump(2) with the strict handler, and the uncaught type_error ends in
        // abort(), observed as 0xC0000409 with no result file.
        std::ofstream output(job + L"\\strict_result.json", std::ios::binary);
        output << report.dump(2);
        output.close();
        return 0;
    }
    if (!success) {
        report["rollback_succeeded"] = true;
        report["rollback_code"] = 0;
        report["rollback_witness"] = {{"checkpoint", "saved"}, {"verified", true}};
    }

    auto disconnect = [&]() {
        const std::wstring result_file = job + L"\\native_result.json";
        const std::wstring checkpoint_file = job + L"\\native_checkpoint.json";
        nlohmann::json observed = {
            {"native_result_exists", std::filesystem::exists(result_file)},
            {"native_checkpoint_exists", std::filesystem::exists(checkpoint_file)}};
        if (observed["native_result_exists"].get<bool>()) {
            std::ifstream input(result_file);
            nlohmann::json persisted;
            input >> persisted;
            observed["delivery_complete"] = persisted.value("delivery_complete", true);
            observed["completion_stage"] = persisted.value("completion_stage", "");
            observed["rollback_succeeded"] = persisted.value("rollback_succeeded", false);
        }
        if (!publish_native_json(job + L"\\disconnect_observed.json", observed))
            ExitProcess(91);
        if (mode == "crash" || mode == "legacy_crash")
            ExitProcess(0xC0000409u);
        if (mode == "hang")
            Sleep(60000);
        return 0;
    };
    if (mode == "legacy_crash")
        return deliver_native_result(job, report, true, disconnect, 200);
    return deliver_worker_result(job, report, true, disconnect, 200);
}
