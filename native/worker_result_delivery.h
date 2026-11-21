// BUG-142: execution facts must survive an abrupt Toolkit disconnect.
#pragma once
#include "result_delivery.h"

template <typename Disconnect>
static int deliver_worker_result(const std::wstring &job, nlohmann::json report, bool connected,
                                 Disconnect disconnect, DWORD disconnect_budget_ms = 20000) {
    report["native_pid"] = GetCurrentProcessId();
    report["delivery_complete"] = false;
    report["completion_stage"] = "before_disconnect";
    report["disconnect_code"] = nullptr;
    report["disconnect_budget_seconds"] = disconnect_budget_ms / 1000.0;
    // This is a recoverable execution/rollback receipt, not a successful delivery.
    // The shared helper publishes delivery_complete=true only after disconnect returns.
    if (!publish_native_json(job + L"\\native_result.json", report))
        return 32;
    return deliver_native_result(job, report, connected, disconnect, disconnect_budget_ms);
}
