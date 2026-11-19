// Synchronous selection callback. Only the immutable, private request next to
// this per-operation DLL copy can supply the model, command and native curves.
#define NOMINMAX
#include <windows.h>
#include <ProToolkitDll.h>
#include <ProUICmd.h>
#include <ProMdl.h>
#include <ProModelitem.h>
#include <ProSelection.h>
#include <ProArray.h>
#include <fstream>
#include <filesystem>
#include <string>
#include <vector>
#include <chrono>
#include "third_party/json.hpp"
#include "callback_identity.h"
#include "callback_api.h"
// BUG-120/D3: the panel generation. Both headers are SDK-free rules; this file
// supplies the SDK side.
#include "panel_protocol.h"
#include "panel_selection_state.h"
static const MechDogCallbackApi *host = nullptr;
using Json = nlohmann::json;
static std::wstring directory, expected_model;
static std::vector<int> curve_ids;
//: BUG-120/D7: the ProType of each position (PRO_CURVE or PRO_POINT). A
//: convergence end is selected as a point; every other position stays a curve.
static std::vector<int> item_types;
static Json outcome = {{"selected", 0}, {"codes", Json::array()}};
static size_t section_index = 0;
static bool resident = false, active = false;
static std::wstring module_directory, resource_root, current_request;
static std::string resident_command;
static Json resident_identity;
static std::filesystem::path identity_file;
static void persist_identity() {
    std::ofstream file(identity_file, std::ios::binary);
    file << resident_identity.dump(2);
    if (!file)
        throw std::runtime_error("Cannot publish callback identity");
}
static bool safe_token(const std::string &value) {
    if (value.empty() || value.size() > 70)
        return false;
    for (char c : value)
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
              c == '_'))
            return false;
    return true;
}
static void persist() {
    std::ofstream f(directory + L"\\callback_result.json", std::ios::binary);
    f << outcome.dump(2);
}

static std::wstring from_utf8(const std::string &value) {
    int size = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), (int)value.size(),
                                   nullptr, 0);
    if (!size)
        throw std::runtime_error("Invalid callback path");
    std::wstring result(size, L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), (int)value.size(),
                        result.data(), size);
    return result;
}

static std::string to_utf8(const std::wstring &value) {
    int size = WideCharToMultiByte(CP_UTF8, 0, value.data(), (int)value.size(), nullptr, 0, nullptr,
                                   nullptr);
    std::string result(size, '\0');
    if (size)
        WideCharToMultiByte(CP_UTF8, 0, value.data(), (int)value.size(), result.data(), size,
                            nullptr, nullptr);
    return result;
}

// ---------------------------------------------------------------------------
// BUG-120/D3+D4: the resident panel route.
//
// The blend path above selects curve ids and always records OVERRIDE. The panel path
// needs three things that path never had: a one-shot ticket per position (a replayed
// macro must not select a position twice), OVERRIDE for the first position and
// TOGGLE for the rest (the dialog's own semantics), and a Done that is only queued
// once every position was consumed.
//
// The rules live in panel_selection_state.h. This file supplies only what the rules
// cannot know: the resolved curve ids, the SDK results, and the ABI2 table. A queued
// Done is *not* a closed panel; the end sequence is reported by the native observer
// through MechDogPanelEvent, and the wait marker below is derived from this run's
// own state, never from a caller's claim.
static const MechDogCallbackApi2 *host2 = nullptr;
static MechDogCallbackApi panel_host;
static mechdog_panel::PanelSelectionState panel_state;
static bool panel_run = false;
static std::string panel_request_id, panel_job_id, panel_nonce, panel_profile_id, panel_model_id;
static std::string panel_done_macro, panel_done_command;
static Json panel_block = Json::object();
static long long panel_marker_seq = 0;

// Defined below, used by the panel entry point which registers the same command
// action as the blend entry.
static uiCmdAccessState access(uiCmdAccessMode);
static int select_section(uiCmdCmdId, uiCmdValue *, void *);

static void persist_panel() {
    outcome["panel"] = panel_block;
    if (!directory.empty())
        persist();
}

//: ABI2 repeats the ABI1 members first (callback_api.h keeps that order), so the
//: shared calls are copied once into a real ABI1 table instead of aliasing two
//: struct types. The size check is what makes the copy safe.
static bool panel_host_view(const MechDogCallbackApi2 *api) {
    if (!api || api->abi != mechdog_panel::loader_abi || api->size != sizeof(MechDogCallbackApi2))
        return false;
    panel_host = {mechdog_callback::loader_abi,
                  sizeof(MechDogCallbackApi),
                  api->array_size,
                  api->array_alloc,
                  api->arguments_free,
                  api->wstring_set,
                  api->current_model,
                  api->model_name,
                  api->model_item,
                  api->selection_alloc,
                  api->selection_record,
                  api->selection_free,
                  api->command_add};
    return true;
}

//: The wait phase this run is in, derived from the state machine. ``panel_ended`` is
//: deliberately not a trusted phase: a finished or failed run must fall back to the
//: ordinary stall contract instead of holding a phase window open.
static const char *panel_phase() {
    switch (panel_state.stage()) {
    case mechdog_panel::PanelStage::Prepared:
        return "panel_select_wait";
    case mechdog_panel::PanelStage::DoneQueued:
        return "panel_done_wait";
    case mechdog_panel::PanelStage::AfterTerminal:
        return "panel_close_wait";
    default:
        return "panel_ended";
    }
}

static void *panel_bracket_data = nullptr;
static bool panel_bracket_registered = false;
//: Set when Creo reports the Done command's after-execution bracket. The dialog is
//: gone at that point, so a following request may start without a release task.
static bool panel_bracket_closed = false;

//: BUG-120/D6: Creo calls this before (entering=1) and after (entering=0) the Done
//: command runs. The event is written from Creo's own UI thread, which is the only
//: place a panel's completion can be observed: a Toolkit task sent while the dialog
//: owns the session blocks until PRO_TK_COMM_ERROR.
static int panel_exit_bracket(uiCmdCmdId command, uiCmdValue *value, int entering, void **data) {
    (void)command;
    (void)value;
    (void)data;
    try {
        if (panel_run && !directory.empty() && !panel_nonce.empty()) {
            const auto epoch_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                                      std::chrono::system_clock::now().time_since_epoch())
                                      .count();
            Json event = {{"job_id", panel_job_id},         {"nonce", panel_nonce},
                          {"profile_id", panel_profile_id}, {"command", panel_done_command},
                          {"entering", entering},           {"at_epoch_ms", epoch_ms}};
            std::string error;
            if (!mechdog_panel::write_marker_atomic(
                    std::filesystem::path(directory) / L"panel_exit.json", event.dump(), error))
                panel_block["exit_bracket_error"] = error;
            if (!entering) {
                // The same bracket runs around the open command too, so only a close
                // that happened after this run's last selection can end it.
                const long long selected_at = panel_block.value("selected_at_ms", 0LL);
                if (selected_at > 0 && epoch_ms >= selected_at) {
                    panel_bracket_closed = true;
                    panel_block["command_finished"] = true;
                    // The dialog is gone, so the run is finished: release it here, on
                    // Creo's UI thread. The next request's preflight only reads the
                    // live identity, and a stale active request would refuse every
                    // later panel job as busy (`callback_busy`).
                    const mechdog_panel::PanelVerdict released =
                        panel_state.release_observed_close(panel_nonce);
                    if (released.ok) {
                        active = false;
                        panel_run = false;
                        panel_bracket_closed = false;
                    } else {
                        panel_block["release_code"] = released.code;
                    }
                }
                persist_panel();
            }
        }
    } catch (...) {
        // A bracket must never break the command it observes.
    }
    return 1; // Non-zero: the command action still runs.
}

//: Publish the wait marker the Python watchdog reads. Without the full identity the
//: marker is not written at all: a partial marker is ignored by the watcher, and
//: writing one anyway would only look like progress that never happened.
static void write_wait_marker() {
    if (!panel_run || directory.empty() || panel_job_id.empty() || panel_nonce.empty() ||
        panel_profile_id.empty())
        return;
    const auto epoch_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                              std::chrono::system_clock::now().time_since_epoch())
                              .count();
    Json marker = {{"job_id", panel_job_id},         {"nonce", panel_nonce},
                   {"profile_id", panel_profile_id}, {"seq", ++panel_marker_seq},
                   {"phase", panel_phase()},         {"at_epoch_ms", epoch_ms}};
    std::string error;
    const auto target = std::filesystem::path(directory) / L"panel_wait.json";
    if (!mechdog_panel::write_marker_atomic(target, marker.dump(), error))
        panel_block["marker_error"] = error;
}

//: The request file argument shared by every panel entry point: one wstring, inside
//: this resource root's jobs directory, named callback_request.json.
static ProError request_argument(ProArgument *inputs, std::wstring &path) {
    int count = 0;
    ProError code = host->array_size((ProArray)inputs, &count);
    if (code || count != 1 || inputs[0].value.type != PRO_VALUE_TYPE_WSTRING ||
        !inputs[0].value.v.w)
        return PRO_TK_BAD_INPUTS;
    auto file = std::filesystem::weakly_canonical(inputs[0].value.v.w);
    auto jobs = std::filesystem::weakly_canonical(std::filesystem::path(resource_root) / L"jobs");
    auto a = jobs.begin(), b = file.begin();
    for (; a != jobs.end(); ++a, ++b)
        if (b == file.end() || _wcsicmp(a->c_str(), b->c_str()))
            return PRO_TK_BAD_INPUTS;
    if (file.filename() != L"callback_request.json")
        return PRO_TK_BAD_INPUTS;
    path = file.wstring();
    return PRO_TK_NO_ERROR;
}

static void configure_panel_request(const Json &request) {
    std::string name = request.at("model_name");
    if (!safe_token(name) || name.size() > 31)
        throw std::runtime_error("PANEL_REQUEST_MODEL");
    const Json &sections = request.at("sections");
    if (!sections.is_array())
        throw std::runtime_error("PANEL_SECTION_COUNT_OUT_OF_RANGE");
    std::vector<int> ids;
    std::vector<int> types;
    std::vector<int> slots;
    for (size_t index = 0; index < sections.size(); ++index) {
        const Json &section = sections.at(index);
        const bool point = section.value("kind", "") == "point";
        const int id =
            point ? section.at("point_id").get<int>() : section.at("curve_id").get<int>();
        if (id < 0)
            throw std::runtime_error(point ? "PANEL_POINT_INVALID" : "PANEL_CURVE_INVALID");
        ids.push_back(id);
        types.push_back(point ? (int)PRO_POINT : (int)PRO_CURVE);
        slots.push_back((int)index);
    }
    // BUG-120/D7: the array carries every position (sections and guides), so its
    // bound is the position limit; sections and guides keep their own 2-8 bounds.
    if (ids.size() < 2 || ids.size() > (size_t)mechdog_panel::position_limit)
        throw std::runtime_error("PANEL_SECTION_COUNT_OUT_OF_RANGE");
    panel_request_id = request.at("request_id").get<std::string>();
    panel_job_id = request.at("job_id").get<std::string>();
    panel_nonce = request.at("nonce").get<std::string>();
    panel_model_id = request.at("model_id").get<std::string>();
    panel_profile_id = request.at("profile_id").get<std::string>();
    // The Done is supplied by the caller: this build has no verified macro text, and
    // inventing a command name would be a guess dressed as SDK knowledge.
    panel_done_macro = request.value("done_macro", "");
    panel_done_command = request.value("done_command", "");
    if (!panel_done_macro.empty() || !panel_done_command.empty()) {
        if (!safe_token(panel_done_command) || panel_done_command.size() > 64)
            throw std::runtime_error("PANEL_DONE_COMMAND_INVALID");
        if (panel_done_macro.size() > 512 || panel_done_macro.find('\n') != std::string::npos ||
            panel_done_macro.rfind("~ ", 0) != 0)
            throw std::runtime_error("PANEL_DONE_MACRO_INVALID");
    }
    expected_model.assign(name.begin(), name.end());
    curve_ids = ids;
    item_types = types;
    section_index = 0;
    // BUG-120/D7: positions before ``second_direction_start`` belong to the first
    // direction, the rest to the second. Absent means one direction, so a
    // first-direction-only request keeps its old ticket actions.
    const int second_direction_start =
        request.value("second_direction_start", static_cast<int>(ids.size()));
    if (second_direction_start < 0 || second_direction_start > static_cast<int>(ids.size()))
        throw std::runtime_error("PANEL_DIRECTION_COUNT");
    std::vector<int> directions(ids.size(), 0);
    for (int index = second_direction_start; index < static_cast<int>(ids.size()); ++index)
        directions[(size_t)index] = 1;
    const auto verdict = panel_state.prepare(panel_request_id, panel_job_id, panel_nonce, name,
                                             panel_model_id, slots, true, directions);
    if (!verdict.ok)
        throw std::runtime_error(verdict.code);
}

//: Queue the restricted Done. ``queue_code`` is the real Toolkit result; the state
//: machine decides whether that counts as committed.
static ProError queue_restricted_done(int &queue_code) {
    queue_code = PRO_TK_GENERAL_ERROR;
    if (!host2)
        return PRO_TK_BAD_CONTEXT;
    if (panel_done_macro.empty() || panel_done_command.empty())
        return PRO_TK_BAD_INPUTS;
    uiCmdCmdId found_id = 0;
    const ProError found = host2->command_id_find(panel_done_command.data(), &found_id);
    panel_block["done_command_found"] = found == PRO_TK_NO_ERROR;
    panel_block["done_command"] = panel_done_command;
    if (found)
        return found;
    std::wstring macro = from_utf8(panel_done_macro);
    queue_code = (int)host2->macro_load(macro.data());
    return queue_code ? (ProError)queue_code : PRO_TK_NO_ERROR;
}

static int select_panel_section() {
    ProSelection selected = nullptr;
    try {
        if (!panel_run || panel_state.stage() != mechdog_panel::PanelStage::Prepared) {
            panel_block["code"] = "PANEL_STATE_NOT_PREPARED";
            persist_panel();
            return 0;
        }
        if (panel_state.exhausted()) {
            // Every position already has its selection. Injecting again would toggle
            // one of them back out.
            panel_block["code"] = "PANEL_SELECTION_EXHAUSTED";
            persist_panel();
            return 0;
        }
        const std::vector<mechdog_panel::PanelTicket> tickets = panel_state.tickets();
        const mechdog_panel::PanelTicket ticket = tickets[(size_t)panel_state.selected()];
        const mechdog_panel::PanelVerdict verdict = panel_state.record(ticket);
        if (!verdict.ok) {
            panel_block["code"] = verdict.code;
            panel_block["stage"] = mechdog_panel::panel_stage_name(panel_state.stage());
            persist_panel();
            return 0;
        }
        const bool override = verdict.action == mechdog_panel::PanelSelectionAction::Override;
        panel_block["action"] = override ? "override" : "toggle";
        panel_block["slot"] = ticket.slot;
        panel_block["direction"] = ticket.direction;

        ProMdl model = nullptr;
        ProMdlName name = L"";
        ProError code = host->current_model(&model);
        if (!code)
            code = host->model_name(model, name);
        if (!code && _wcsicmp(name, expected_model.c_str()))
            code = PRO_TK_BAD_CONTEXT;
        ProModelitem item;
        if (!code)
            code = host->model_item(model, curve_ids[(size_t)ticket.slot],
                                    (ProType)item_types[(size_t)ticket.slot], &item);
        if (!code)
            code = host->selection_alloc(nullptr, &item, &selected);
        if (!code)
            code = host->selection_record(selected,
                                          override ? PRO_SELECT_OVERRIDE : PRO_SELECT_TOGGLE);
        if (selected) {
            host->selection_free(&selected);
            selected = nullptr;
        }
        outcome["codes"].push_back(code);
        outcome["selected"] = panel_state.selected();
        if (code) {
            // The ticket is spent and the dialog now holds an unknown selection:
            // abort the run instead of continuing misaligned.
            panel_state.abandon("PANEL_SELECTION_FAILED");
            panel_block["code"] = "PANEL_SELECTION_FAILED";
            panel_block["sdk_code"] = code;
        }
        if (!code) {
            // BUG-120/D6: the last consumed ticket's own time orders the Done bracket.
            // The worker's poll can notice the selection later than it happened, so its
            // clock cannot be used to tell an open-time bracket from a close-time one.
            panel_block["selected_at_ms"] = std::chrono::duration_cast<std::chrono::milliseconds>(
                                                std::chrono::system_clock::now().time_since_epoch())
                                                .count();
        }
        panel_block["stage"] = mechdog_panel::panel_stage_name(panel_state.stage());
        write_wait_marker();
        persist_panel();
    } catch (...) {
        if (selected)
            host->selection_free(&selected);
        try {
            panel_state.abandon("PANEL_SELECTION_EXCEPTION");
            panel_block["code"] = "PANEL_SELECTION_EXCEPTION";
            panel_block["stage"] = mechdog_panel::panel_stage_name(panel_state.stage());
            persist_panel();
        } catch (...) {
        }
    }
    return 0;
}

//: Prepare a panel run. ABI1 deployments cannot reach this: the panel generation is
//: the ABI2 payload, and a protocol-4 request on the blend table is refused instead
//: of being reinterpreted as curve ids.
extern "C" PRO_TK_DLL_EXPORT ProError MechDogPanelPrepare(ProArgument *inputs,
                                                          ProArgument **outputs) {
    if (outputs)
        *outputs = nullptr;
    // BUG-120/D6: Creo reported the previous Done command's after-execution bracket,
    // so that dialog is gone. The next request may start without a release task
    // (a task would block if anything were still open).
    if (active && panel_bracket_closed) {
        const auto released = panel_state.release_observed_close(panel_nonce);
        if (released.ok) {
            active = false;
            panel_run = false;
            panel_bracket_closed = false;
            panel_block = Json::object();
        }
    }
    if (!resident || active || !inputs || !host2)
        return PRO_TK_BAD_CONTEXT;
    try {
        std::wstring path;
        ProError code = request_argument(inputs, path);
        if (code)
            return code;
        std::ifstream input(path, std::ios::binary);
        Json request;
        input >> request;
        if (request.value("protocol", 0) != mechdog_panel::protocol ||
            request.value("contract", "") != mechdog_panel::contract)
            return PRO_TK_BAD_INPUTS;
        configure_panel_request(request);
        ProMdl model = nullptr;
        ProMdlName name = L"";
        code = host->current_model(&model);
        if (!code)
            code = host->model_name(model, name);
        if (code || _wcsicmp(name, expected_model.c_str()))
            return code ? code : PRO_TK_BAD_CONTEXT;
        directory = std::filesystem::path(path).parent_path().wstring();
        current_request = path;
        panel_run = true;
        panel_bracket_closed = false;
        // BUG-120/D6: register the exit bracket on the Done command now, before the
        // dialog opens. After that point no Toolkit task can be sent, so this is the
        // only chance to ask Creo to report the command's completion.
        if (!panel_done_command.empty() && host2->command_id_find && host2->bracket_func_add) {
            std::string done_name = panel_done_command;
            uiCmdCmdId done_id = 0;
            if (host2->command_id_find(&done_name[0], &done_id) == PRO_TK_NO_ERROR && done_id) {
                const ProError added = host2->bracket_func_add(
                    done_id, panel_exit_bracket, const_cast<char *>("MechDogPanelExitBracket"),
                    &panel_bracket_data);
                panel_bracket_registered = added == PRO_TK_NO_ERROR;
                panel_block["exit_bracket_code"] = (int)added;
            }
        }
        outcome = {{"protocol", mechdog_panel::protocol},
                   {"contract", mechdog_panel::contract},
                   {"creation_route", "resident_panel"},
                   {"selected", 0},
                   {"codes", Json::array()},
                   {"command", resident_command},
                   {"prepared", true}};
        panel_block = {{"stage", mechdog_panel::panel_stage_name(panel_state.stage())},
                       {"slots", (int)panel_state.tickets().size()}};
        write_wait_marker();
        persist_panel();
        active = true;
        return PRO_TK_NO_ERROR;
    } catch (const std::exception &exc) {
        panel_block["code"] = exc.what();
        try {
            persist_panel();
        } catch (...) {
        }
        return PRO_TK_BAD_INPUTS;
    } catch (...) {
        return PRO_TK_BAD_INPUTS;
    }
}

//: Queue the restricted Done and let the state machine decide whether it committed.
extern "C" PRO_TK_DLL_EXPORT ProError MechDogPanelFinalize(ProArgument *inputs,
                                                           ProArgument **outputs) {
    if (outputs)
        *outputs = nullptr;
    if (!resident || !panel_run || !inputs)
        return PRO_TK_BAD_CONTEXT;
    try {
        std::wstring path;
        ProError code = request_argument(inputs, path);
        if (code)
            return code;
        if (panel_done_macro.empty() || panel_done_command.empty()) {
            // Nothing was attempted, so the run stays selectable: D6 supplies the
            // verified macro after checking it in the target session.
            panel_block["code"] = "PANEL_DONE_MACRO_MISSING";
            persist_panel();
            return PRO_TK_BAD_INPUTS;
        }
        int queue_code = PRO_TK_GENERAL_ERROR;
        const ProError queued = queue_restricted_done(queue_code);
        const mechdog_panel::PanelVerdict verdict = panel_state.finalize((int)queue_code);
        panel_block["done_queued"] = verdict.ok;
        panel_block["queue_code"] = (int)queue_code;
        if (!verdict.ok)
            panel_block["code"] = verdict.code;
        panel_block["stage"] = mechdog_panel::panel_stage_name(panel_state.stage());
        write_wait_marker();
        persist_panel();
        if (verdict.ok)
            return PRO_TK_NO_ERROR;
        return queued ? queued : PRO_TK_BAD_INPUTS;
    } catch (...) {
        return PRO_TK_GENERAL_ERROR;
    }
}

//: Record one native end-of-run event. The caller names the event; the state machine
//: decides whether that order is admissible, and the marker phase is derived here,
//: not taken from the claim.
extern "C" PRO_TK_DLL_EXPORT ProError MechDogPanelEvent(ProArgument *inputs,
                                                        ProArgument **outputs) {
    if (outputs)
        *outputs = nullptr;
    if (!resident || !panel_run || !inputs)
        return PRO_TK_BAD_CONTEXT;
    try {
        int count = 0;
        ProError code = host->array_size((ProArray)inputs, &count);
        if (code || count != 1 || inputs[0].value.type != PRO_VALUE_TYPE_WSTRING ||
            !inputs[0].value.v.w)
            return PRO_TK_BAD_INPUTS;
        Json event;
        {
            std::string text = to_utf8(inputs[0].value.v.w);
            event = Json::parse(text, nullptr, false);
            if (event.is_discarded() || !event.is_object())
                return PRO_TK_BAD_INPUTS;
        }
        mechdog_panel::PanelEvent record;
        record.kind = event.at("kind").get<std::string>();
        record.event_seq = event.at("event_seq").get<int>();
        record.job_id = event.value("job_id", panel_job_id);
        record.nonce = event.value("nonce", panel_nonce);
        const mechdog_panel::PanelVerdict verdict = panel_state.observe(record);
        panel_block["event"] = record.kind;
        panel_block["event_seq"] = record.event_seq;
        panel_block["stage"] = mechdog_panel::panel_stage_name(panel_state.stage());
        panel_block["closed"] = panel_state.closed();
        if (!verdict.ok)
            panel_block["code"] = verdict.code;
        write_wait_marker();
        persist_panel();
        return verdict.ok ? PRO_TK_NO_ERROR : PRO_TK_BAD_CONTEXT;
    } catch (...) {
        return PRO_TK_GENERAL_ERROR;
    }
}

//: The run's own state, for the worker and the target-machine checks. Returns a
//: JSON wstring; no Toolkit state is invented here.
extern "C" PRO_TK_DLL_EXPORT ProError MechDogPanelState(ProArgument *inputs,
                                                        ProArgument **outputs) {
    if (!outputs)
        return PRO_TK_BAD_INPUTS;
    *outputs = nullptr;
    if (!resident || !host)
        return PRO_TK_BAD_CONTEXT;
    try {
        std::wstring path;
        ProError code = request_argument(inputs, path);
        if (code)
            return code;
        Json state = {{"stage", mechdog_panel::panel_stage_name(panel_state.stage())},
                      {"selected", panel_state.selected()},
                      {"slots", (int)panel_state.tickets().size()},
                      {"closed", panel_state.closed()},
                      {"exhausted", panel_state.exhausted()},
                      {"failure_code", panel_state.failure_code()},
                      {"last_event_seq", panel_state.last_event_seq()}};
        code = host->array_alloc(1, sizeof(ProArgument), 1, (ProArray *)outputs);
        if (code)
            return code;
        (*outputs)[0] = {};
        wcscpy_s((*outputs)[0].label, L"panel");
        (*outputs)[0].value.type = PRO_VALUE_TYPE_WSTRING;
        auto value = from_utf8(state.dump());
        code = host->wstring_set(&(*outputs)[0].value, value.data());
        if (code)
            host->arguments_free(outputs);
        return code;
    } catch (...) {
        if (*outputs)
            host->arguments_free(outputs);
        return PRO_TK_GENERAL_ERROR;
    }
}

//: Release the run after it ended. A run that is still open, or one that failed,
//: refuses: releasing it here would forget a panel that may be open.
extern "C" PRO_TK_DLL_EXPORT ProError MechDogPanelRelease(ProArgument *inputs,
                                                          ProArgument **outputs) {
    if (outputs)
        *outputs = nullptr;
    if (!resident || !panel_run || !inputs)
        return PRO_TK_BAD_CONTEXT;
    try {
        std::wstring path;
        ProError code = request_argument(inputs, path);
        if (code)
            return code;
        if (path != current_request)
            return PRO_TK_BAD_INPUTS;
        const mechdog_panel::PanelVerdict verdict = panel_state.release();
        panel_block["released"] = verdict.ok;
        panel_block["stage"] = mechdog_panel::panel_stage_name(panel_state.stage());
        if (!verdict.ok)
            panel_block["code"] = verdict.code;
        persist_panel();
        if (!verdict.ok)
            return PRO_TK_BAD_CONTEXT;
        outcome["released"] = true;
        persist_panel();
        active = false;
        panel_run = false;
        curve_ids.clear();
        item_types.clear();
        return PRO_TK_NO_ERROR;
    } catch (...) {
        return PRO_TK_BAD_INPUTS;
    }
}

//: The ABI2 entry point. Separate from MechDogBlendInitialize on purpose: an ABI1
//: deployment keeps using the blend entry with the blend rules, and a panel
//: deployment cannot reach the blend one by mistake.
extern "C" __declspec(dllexport) int MechDogPanelInitialize(int, char **, char *, char *,
                                                            wchar_t errmsg[80],
                                                            const wchar_t *application_id,
                                                            const wchar_t *loader_file,
                                                            const MechDogCallbackApi2 *api) {
    try {
        if (!panel_host_view(api))
            return PRO_TK_BAD_INPUTS;
        host2 = api;
        host = &panel_host;
        wchar_t filename[MAX_PATH];
        HMODULE module = nullptr;
        if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                (LPCWSTR)&MechDogPanelInitialize, &module) ||
            !GetModuleFileNameW(module, filename, MAX_PATH))
            return PRO_TK_GENERAL_ERROR;
        directory = filename;
        directory = directory.substr(0, directory.find_last_of(L"\\"));
        module_directory = directory;
        resident = true;
        std::ifstream input(directory + L"\\callback_bootstrap.json");
        Json request;
        input >> request;
        std::string command = request.at("command");
        if (!safe_token(command))
            return PRO_TK_BAD_INPUTS;
        auto actual_root =
            std::filesystem::path(filename).parent_path().parent_path().parent_path().parent_path();
        if (request.value("protocol", 0) != mechdog_panel::protocol ||
            request.value("contract", "") != mechdog_panel::contract ||
            _wcsicmp(actual_root.c_str(), from_utf8(request.at("resource_root")).c_str()) ||
            request.value("dll_sha256", "") != mechdog_callback::sha256(filename) ||
            !application_id || !*application_id || !loader_file || !*loader_file)
            return PRO_TK_BAD_INPUTS;
        resource_root = from_utf8(request.at("resource_root"));
        resident_command = command;
        outcome["protocol"] = mechdog_panel::protocol;
        outcome["contract"] = mechdog_panel::contract;
        outcome["terminated"] = false;
        outcome["command"] = command;
        outcome["resource_root"] = request.at("resource_root");
        outcome["module_file"] = std::filesystem::path(filename).u8string();
        outcome["dll_sha256"] = request.at("dll_sha256");
        outcome["loader_file"] = std::filesystem::path(loader_file).u8string();
        outcome["loader_sha256"] = mechdog_callback::sha256(loader_file);
        outcome["loader_abi"] = mechdog_panel::loader_abi;
        outcome["process_id"] = GetCurrentProcessId();
        identity_file = std::filesystem::path(loader_file).parent_path() / L"callback_result.json";
        persist();
        ProError identified =
            application_id && *application_id ? PRO_TK_NO_ERROR : PRO_TK_BAD_INPUTS;
        outcome["application_id_code"] = identified;
        if (!identified)
            outcome["application_id"] = to_utf8(std::wstring(application_id));
        persist();
        if (identified)
            return identified;
        uiCmdCmdId action;
        ProError code = host->command_add(command.data(), select_section, uiProeAsynch, access,
                                          PRO_B_FALSE, PRO_B_FALSE, &action);
        outcome["initialize_code"] = code;
        persist();
        resident_identity = outcome;
        persist_identity();
        return code;
    } catch (...) {
        wcscpy_s(errmsg, 80, L"Invalid MechDog panel callback request");
        return PRO_TK_BAD_INPUTS;
    }
}

// Required by the Toolkit DLL link support, but payloads are never registered directly.
extern "C" __declspec(dllexport) int user_initialize(int, char **, char *, char *,
                                                     wchar_t errmsg[80]) {
    wcscpy_s(errmsg, 80, L"Register the MechDog loader protk.dat, not the callback payload");
    return PRO_TK_BAD_CONTEXT;
}

static void configure_request(const Json &request) {
    std::string name = request.at("model_name");
    if (!safe_token(name) || name.size() > 31)
        throw std::runtime_error("Invalid callback model");
    auto ids = request.at("curve_ids").get<std::vector<int>>();
    if (ids.size() < 2 || ids.size() > 20)
        throw std::runtime_error("Invalid callback section count");
    for (int id : ids)
        if (id < 0)
            throw std::runtime_error("Invalid callback curve");
    expected_model.assign(name.begin(), name.end());
    curve_ids = std::move(ids);
    section_index = 0;
}

// A resident callback is loaded by the operator before modeling, so PROMPT
// policy never blocks an asynchronous modeling worker on DLL authorization.
extern "C" PRO_TK_DLL_EXPORT ProError MechDogBlendPrepare(ProArgument *inputs,
                                                          ProArgument **outputs) {
    if (outputs)
        *outputs = nullptr;
    if (!resident || active || !inputs)
        return PRO_TK_BAD_CONTEXT;
    try {
        int count = 0;
        ProError code = host->array_size((ProArray)inputs, &count);
        if (code || count != 1 || inputs[0].value.type != PRO_VALUE_TYPE_WSTRING ||
            !inputs[0].value.v.w)
            return PRO_TK_BAD_INPUTS;
        auto file = std::filesystem::weakly_canonical(inputs[0].value.v.w);
        auto jobs =
            std::filesystem::weakly_canonical(std::filesystem::path(resource_root) / L"jobs");
        auto a = jobs.begin(), b = file.begin();
        for (; a != jobs.end(); ++a, ++b)
            if (b == file.end() || _wcsicmp(a->c_str(), b->c_str()))
                return PRO_TK_BAD_INPUTS;
        if (file.filename() != L"callback_request.json")
            return PRO_TK_BAD_INPUTS;
        std::ifstream input(file, std::ios::binary);
        Json request;
        input >> request;
        if (request.value("protocol", 0) == mechdog_panel::protocol)
            // A panel request needs the ABI2 table. Refusing here keeps a protocol-4
            // request from being parsed as curve ids by the blend rules.
            return PRO_TK_BAD_CONTEXT;
        if (request.value("protocol", 0) != mechdog_callback::protocol)
            return PRO_TK_BAD_INPUTS;
        configure_request(request);
        ProMdl model = nullptr;
        ProMdlName name = L"";
        code = host->current_model(&model);
        if (!code)
            code = host->model_name(model, name);
        if (code || _wcsicmp(name, expected_model.c_str()))
            return code ? code : PRO_TK_BAD_CONTEXT;
        directory = file.parent_path().wstring();
        current_request = file.wstring();
        outcome = {{"protocol", mechdog_callback::protocol},
                   {"selected", 0},
                   {"codes", Json::array()},
                   {"command", resident_command},
                   {"prepared", true}};
        persist();
        active = true;
        return PRO_TK_NO_ERROR;
    } catch (...) {
        return PRO_TK_BAD_INPUTS;
    }
}

extern "C" PRO_TK_DLL_EXPORT ProError MechDogBlendRelease(ProArgument *inputs,
                                                          ProArgument **outputs) {
    if (outputs)
        *outputs = nullptr;
    if (!resident || !active || !inputs)
        return PRO_TK_BAD_CONTEXT;
    try {
        int count = 0;
        ProError code = host->array_size((ProArray)inputs, &count);
        if (code || count != 1 || inputs[0].value.type != PRO_VALUE_TYPE_WSTRING ||
            !inputs[0].value.v.w ||
            std::filesystem::weakly_canonical(inputs[0].value.v.w).wstring() != current_request)
            return PRO_TK_BAD_INPUTS;
        outcome["released"] = true;
        persist();
        active = false;
        curve_ids.clear();
        return PRO_TK_NO_ERROR;
    } catch (...) {
        return PRO_TK_BAD_INPUTS;
    }
}
static uiCmdAccessState access(uiCmdAccessMode) {
    return ACCESS_AVAILABLE;
}
static int select_section(uiCmdCmdId, uiCmdValue *, void *) {
    if (!resident || !active || resident_identity.value("terminated", true))
        return 0;
    if (panel_run)
        return select_panel_section();
    ProSelection selected = nullptr;
    try {
        ProMdl model = nullptr;
        ProMdlName name = L"";
        ProError code = host->current_model(&model);
        if (!code)
            code = host->model_name(model, name);
        if (!code && (_wcsicmp(name, expected_model.c_str()) || section_index >= curve_ids.size()))
            code = PRO_TK_BAD_CONTEXT;
        ProModelitem item;
        if (!code)
            code = host->model_item(model, curve_ids[section_index], PRO_CURVE, &item);
        if (!code)
            code = host->selection_alloc(nullptr, &item, &selected);
        if (!code)
            code = host->selection_record(selected, PRO_SELECT_OVERRIDE);
        if (selected) {
            host->selection_free(&selected);
            selected = nullptr;
        }
        outcome["codes"].push_back(code);
        if (!code)
            section_index++;
        outcome["selected"] = section_index;
        persist();
    } catch (...) {
        if (selected)
            host->selection_free(&selected);
        try {
            outcome["exception"] = true;
            persist();
        } catch (...) {
        }
    }
    return 0;
}
extern "C" __declspec(dllexport) int MechDogBlendInitialize(int, char **, char *, char *,
                                                            wchar_t errmsg[80],
                                                            const wchar_t *application_id,
                                                            const wchar_t *loader_file,
                                                            const MechDogCallbackApi *api) {
    try {
        if (!api || api->abi != mechdog_callback::loader_abi ||
            api->size != sizeof(MechDogCallbackApi))
            return PRO_TK_BAD_INPUTS;
        host = api;
        wchar_t filename[MAX_PATH];
        HMODULE module = nullptr;
        if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                (LPCWSTR)&MechDogBlendInitialize, &module) ||
            !GetModuleFileNameW(module, filename, MAX_PATH))
            return PRO_TK_GENERAL_ERROR;
        directory = filename;
        directory = directory.substr(0, directory.find_last_of(L"\\"));
        module_directory = directory;
        resident = true;
        std::ifstream input(directory + L"\\callback_bootstrap.json");
        Json request;
        input >> request;
        std::string command = request.at("command");
        if (!safe_token(command))
            return PRO_TK_BAD_INPUTS;
        if (resident) {
            auto actual_root = std::filesystem::path(filename)
                                   .parent_path()
                                   .parent_path()
                                   .parent_path()
                                   .parent_path();
            if (request.value("protocol", 0) != mechdog_callback::protocol ||
                request.value("contract", "") != mechdog_callback::contract ||
                _wcsicmp(actual_root.c_str(), from_utf8(request.at("resource_root")).c_str()) ||
                request.value("dll_sha256", "") != mechdog_callback::sha256(filename) ||
                !application_id || !*application_id || !loader_file || !*loader_file)
                return PRO_TK_BAD_INPUTS;
            resource_root = from_utf8(request.at("resource_root"));
            resident_command = command;
            outcome["protocol"] = mechdog_callback::protocol;
            outcome["terminated"] = false;
            outcome["command"] = command;
            outcome["contract"] = mechdog_callback::contract;
            outcome["resource_root"] = request.at("resource_root");
            outcome["module_file"] = std::filesystem::path(filename).u8string();
            outcome["dll_sha256"] = request.at("dll_sha256");
            outcome["loader_file"] = std::filesystem::path(loader_file).u8string();
            outcome["loader_sha256"] = mechdog_callback::sha256(loader_file);
            outcome["loader_abi"] = mechdog_callback::loader_abi;
            outcome["process_id"] = GetCurrentProcessId();
            identity_file =
                std::filesystem::path(loader_file).parent_path() / L"callback_result.json";
        } else {
            configure_request(request);
        }
        // Persist Creo's real identifier before exposing the command. A later worker
        // can locate this module after a loader prompt outlives the original process.
        outcome["initialize_stage"] = "before_application_id";
        outcome["initialize_tick_ms"] = GetTickCount64();
        persist();
        // The registered loader supplies its identifier. The payload itself is
        // never independently registered as a Toolkit application.
        ProError identified =
            application_id && *application_id ? PRO_TK_NO_ERROR : PRO_TK_BAD_INPUTS;
        outcome["application_id_code"] = identified;
        outcome["initialize_stage"] = "after_application_id";
        if (!identified) {
            std::wstring id = application_id;
            outcome["application_id"] = to_utf8(id);
        }
        persist();
        if (identified)
            return identified;
        outcome["initialize_stage"] = "before_command_register";
        persist();
        uiCmdCmdId action;
        ProError code = host->command_add(command.data(), select_section, uiProeAsynch, access,
                                          PRO_B_FALSE, PRO_B_FALSE, &action);
        outcome["initialize_code"] = code;
        outcome["initialize_stage"] = "after_command_register";
        persist();
        if (resident) {
            resident_identity = outcome;
            persist_identity();
        }
        return code;
    } catch (...) {
        wcscpy_s(errmsg, 80, L"Invalid MechDog Blend callback request");
        return PRO_TK_BAD_INPUTS;
    }
}
extern "C" __declspec(dllexport) void user_terminate() {
    try {
        outcome["terminated"] = true;
        persist();
        if (resident) {
            resident_identity["terminated"] = true;
            persist_identity();
        }
    } catch (...) {
    }
}

// A live response, not an initialization file, proves that this exact module is
// running in the selected Creo session. It does not reset an active request.
extern "C" PRO_TK_DLL_EXPORT ProError MechDogBlendIdentity(ProArgument *inputs,
                                                           ProArgument **outputs) {
    if (!outputs)
        return PRO_TK_BAD_INPUTS;
    *outputs = nullptr;
    try {
        if (!resident || !host || resident_identity.value("initialize_code", -1) != 0 ||
            resident_identity.value("terminated", false))
            return PRO_TK_BAD_CONTEXT;
        int count = 0;
        ProError array_code =
            inputs ? host->array_size((ProArray)inputs, &count) : PRO_TK_BAD_INPUTS;
        if (array_code)
            return array_code;
        if (count != 1 || inputs[0].value.type != PRO_VALUE_TYPE_WSTRING || !inputs[0].value.v.w)
            return PRO_TK_BAD_INPUTS;
        std::wstring nonce = inputs[0].value.v.w;
        if (nonce.size() != 32 ||
            nonce.find_first_not_of(L"0123456789abcdef") != std::wstring::npos)
            return PRO_TK_BAD_INPUTS;
        Json identity = resident_identity;
        identity.erase("application_id");
        identity["nonce"] = to_utf8(nonce);
        identity["active_request"] = active;
        ProError code = host->array_alloc(1, sizeof(ProArgument), 1, (ProArray *)outputs);
        if (code)
            return code;
        (*outputs)[0] = {};
        wcscpy_s((*outputs)[0].label, L"identity");
        (*outputs)[0].value.type = PRO_VALUE_TYPE_WSTRING;
        auto value = from_utf8(identity.dump());
        code = host->wstring_set(&(*outputs)[0].value, value.data());
        if (code)
            host->arguments_free(outputs);
        return code;
    } catch (...) {
        if (*outputs)
            host->arguments_free(outputs);
        return PRO_TK_GENERAL_ERROR;
    }
}
