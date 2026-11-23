// Recovery phase deadline. It only terminates this worker, never Creo.
#pragma once
#include "result_delivery.h"
#include <stdexcept>

class RecoveryDeadline {
    HANDLE done = nullptr;
    std::thread watchdog;

  public:
    explicit RecoveryDeadline(const std::wstring &job, DWORD budget_ms = 90000) {
        done = CreateEventW(nullptr, TRUE, FALSE, nullptr);
        if (!done)
            throw std::runtime_error("Cannot create recovery budget event");
        try {
            HANDLE event = done;
            watchdog = std::thread([=]() {
                if (WaitForSingleObject(event, budget_ms) == WAIT_TIMEOUT) {
                    publish_native_json(job + L"\\native_checkpoint.json",
                                        {{"success", false},
                                         {"delivery_complete", false},
                                         {"completion_stage", "recovery_phase_timeout"},
                                         {"phase_budget_seconds", budget_ms / 1000.0}});
                    // BUG-171: leave a minimal readable result so the caller can
                    // name the timeout and its budget instead of a bare
                    // "outcome unconfirmed". delivery_complete stays false, so
                    // the unknown_outcome protection is unchanged.
                    publish_native_json(
                        job + L"\\native_result.json",
                        {{"success", false},
                         {"delivery_complete", false},
                         {"completion_stage", "recovery_phase_timeout"},
                         {"failure_phase", "native_worker_started"},
                         {"phase_budget_seconds", budget_ms / 1000.0},
                         {"toolkit_code", -1},
                         {"message", "Recovery native phase exceeded its budget of " +
                                         std::to_string(budget_ms / 1000) +
                                         " s; the worker was stopped. Retry restore_baseline "
                                         "with verify_mode='identity' or a larger budget_seconds, "
                                         "or release the reservation with "
                                         "abandon_unknown_recovery"}});
                    ExitProcess(31);
                }
            });
        } catch (...) {
            CloseHandle(done);
            throw;
        }
    }
    RecoveryDeadline(const RecoveryDeadline &) = delete;
    RecoveryDeadline &operator=(const RecoveryDeadline &) = delete;
    void complete() {
        if (done) {
            SetEvent(done);
            watchdog.join();
            CloseHandle(done);
            done = nullptr;
        }
    }
    ~RecoveryDeadline() {
        complete();
    }
};
