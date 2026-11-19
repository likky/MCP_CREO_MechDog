// panel_run.h — BUG-120/D3: the resident panel route's execution sequence.
//
// The tree route builds a boundary-blend element tree and reads it back; the Creo 10
// kernel refuses that readback (-18). The panel route replays a recorded UI command
// sequence instead, and the resident callback consumes one ticket per position while
// it runs. This file is the worker half of that: resolve the references, hand the
// payload a protocol-4 request, drive the recorded macro, queue the restricted Done,
// and refuse to claim anything the end sequence has not confirmed.
//
// Two inputs are deliberately *not* invented here:
//   - the dialog macro comes from the certified UI profile (``open_macro``); without
//     it the route refuses and the run stays selectable;
//   - the Done macro and command name come from the same profile. The payload
//     verifies the command with ProCmdCmdIdFind before loading it.
//
// A queued Done is not a closed panel. Until the native exit observation lands in the
// job result, the receipt projection keeps success=false and
// panel_execution_unconfirmed=true; that is D5's rule, not a limitation of this file.
#ifndef MECHDOG_PANEL_RUN_H
#define MECHDOG_PANEL_RUN_H

#include <ProUICmd.h>

#include <thread>

#include "panel_protocol.h"

inline std::string panel_required_string(const J &panel, const char *key) {
    if (!panel.contains(key) || !panel[key].is_string())
        throw std::runtime_error(std::string("PANEL_ADMISSION_INCOMPLETE: panel.") + key +
                                 " is missing; the request did not go through panel admission");
    const std::string value = panel[key].get<std::string>();
    if (value.empty())
        throw std::runtime_error(std::string("PANEL_ADMISSION_INCOMPLETE: panel.") + key +
                                 " is empty; the request did not go through panel admission");
    return value;
}

inline void generic_surface_loft_panel(const J &op) {
    if (!op.contains("panel") || !op["panel"].is_object())
        throw std::runtime_error(
            "PANEL_ADMISSION_INCOMPLETE: creation_route=resident_panel requires the panel block "
            "that admission adds (job, request, nonce, profile and model identity); nothing was "
            "created and the request is not retried on the element tree route.");
    const J &panel = op["panel"];
    const std::string job_id = panel_required_string(panel, "job_id");
    const std::string request_id = panel_required_string(panel, "request_id");
    const std::string nonce = panel_required_string(panel, "nonce");
    const std::string profile_id = panel_required_string(panel, "profile_id");
    // The name is optional: when the request names a model, the live model must match
    // it; when it does not, the live model is the one this run selects in.
    const std::string wanted_model = panel.value("model_name", "");
    const std::string open_macro = panel.value("open_macro", "");
    // BUG-120/D7: an optional recorded collector switch (the second direction). A
    // profile that does not freeze it keeps the first-direction sequence unchanged;
    // when it is present the macro is one more step of the same dialog, never a
    // second dialog and never a guessed control name.
    const std::string second_direction_macro = panel.value("second_direction_macro", "");
    const std::string done_macro = panel.value("done_macro", "");
    const std::string done_command = panel.value("done_command", "");
    if (open_macro.empty())
        throw std::runtime_error(
            "PANEL_OPEN_MACRO_MISSING: creation_route=resident_panel needs the recorded dialog "
            "sequence of a certified UI profile (open_macro). This build records no macro of its "
            "own, because a guessed command sequence is exactly what the panel route must not do. "
            "No feature was created and the request was not retried on the element tree route.");

    if (!second_direction_macro.empty()) {
        // The optional slot is replayed as whole UI steps, so a line the macro
        // engine cannot read is refused here, before the dialog exists, instead of
        // being submitted as a step that silently does nothing.
        bool malformed =
            second_direction_macro.size() > 4096 ||
            second_direction_macro.find(mechdog_panel::select_placeholder) != std::string::npos;
        for (size_t start = 0; !malformed && start <= second_direction_macro.size();) {
            const size_t end = second_direction_macro.find('\n', start);
            const std::string line = second_direction_macro.substr(
                start, end == std::string::npos ? std::string::npos : end - start);
            malformed = line.rfind("~ ", 0) != 0;
            if (end == std::string::npos)
                break;
            start = end + 1;
        }
        if (malformed)
            throw std::runtime_error(
                "PANEL_SECOND_DIRECTION_MACRO_INVALID: panel.second_direction_macro must be "
                "whole '~ ' macro lines under 4096 bytes and must not name the resident selection "
                "command; the dialog was not opened and no position was selected.");
    }

    // D2: resolve every position against the live model before anything is selected.
    // A section names its sketch by label (public clients may pass the plain string)
    // or by {label, open_confirmed}; the sketch feature id is resolved here through
    // the same alias table the element-tree route uses, because this backend would
    // otherwise hand feature id 0 to ProFeatureInit and refuse a valid request.
    std::vector<mechdog_panel_ref::PanelCurveRequest> wants;
    J intent_labels = J::array();
    auto read_position = [&](const J &entry, const char *role, size_t index) {
        mechdog_panel_ref::PanelCurveRequest want;
        bool open_confirmed = false;
        if (entry.is_string()) {
            want.label = entry.get<std::string>();
        } else if (entry.is_object()) {
            const std::string kind = entry.value("kind", "");
            if (kind == "datum_point_feature") {
                // BUG-120/D7: a convergence end is an MCP-owned datum point. It is
                // resolved by label like a sketch, but it has no openness or length
                // to certify, so the curve-only proof below does not apply.
                want.point = true;
                want.label = entry.value("label", "");
            } else if (kind == "point") {
                throw std::runtime_error(
                    std::string("PANEL_SECTION_FORM_INVALID: resident_panel ") + role + " " +
                    std::to_string(index) +
                    " uses {kind:'point',id:N}; the panel route resolves a point by its "
                    "MCP-owned label, so pass {kind:'datum_point_feature',label:'...'}");
            } else {
                want.label = entry.value("label", "");
                want.owner_name = entry.value("owner", "");
                want.feature_id = entry.value("feature_id", 0);
                want.curve_id = entry.value("curve_id", 0);
                open_confirmed = entry.value("open_confirmed", false);
            }
        } else {
            throw std::runtime_error(
                std::string("PANEL_SECTION_FORM_INVALID: resident_panel ") + role + " " +
                std::to_string(index) +
                " is a sketch label or {label, open_confirmed}; nothing was selected and the "
                "dialog was not opened");
        }
        if (want.label.empty())
            throw std::runtime_error(
                std::string("PANEL_SECTION_FORM_INVALID: resident_panel ") + role + " " +
                std::to_string(index) +
                " carries no label; nothing was selected and the dialog was not opened");
        if (!want.point && !open_confirmed)
            // The caller certifies that a position is an open curve. Without that
            // fact D2 refuses instead of assuming "probably open". A point has no
            // openness to certify, so only curve positions take this proof.
            throw std::runtime_error(
                std::string("PANEL_CURVE_OPENNESS_UNVERIFIED: ") + role + " " + want.label +
                " does not declare open_confirmed=true; this build cannot read a standalone "
                "curve's openness, so it refuses the position instead of assuming it");
        if (want.feature_id == 0)
            want.feature_id = feature_id(want.label);
        intent_labels.push_back(want.label);
        wants.push_back(want);
    };
    for (size_t index = 0; index < op.at("sections").size(); ++index)
        read_position(op.at("sections").at(index), "section", index);
    const size_t section_count = wants.size();
    if (section_count < 2 || section_count > 8)
        throw std::runtime_error(
            "PANEL_SECTION_COUNT_OUT_OF_RANGE: the panel route selects 2 to 8 first-direction "
            "sections");
    size_t point_count = 0;
    for (size_t index = 0; index < section_count; ++index) {
        if (!wants[index].point)
            continue;
        ++point_count;
        if (index != 0 && index + 1 != section_count)
            throw std::runtime_error(
                "PANEL_POINT_POSITION: resident_panel section " + std::to_string(index) +
                " is a point; a convergence end is only the first or last section. Move it to "
                "sections[0] or the last section; nothing was selected and the dialog was not "
                "opened");
    }
    if (point_count > 1)
        throw std::runtime_error(
            "PANEL_POINT_COUNT: resident_panel accepts one convergence point per run; this "
            "request has " +
            std::to_string(point_count) +
            ". Keep one point at one end; nothing was selected and the dialog was not opened");
    // BUG-120/D7: guides are the second direction. They are resolved with the same
    // openness rule as a section and appended after it, so the selection order is
    // the dialog order: every first-direction position, then the collector switch,
    // then every guide.
    size_t guide_count = 0;
    if (op.contains("guides") && !op["guides"].is_null()) {
        if (!op["guides"].is_array())
            throw std::runtime_error(
                "PANEL_SECTION_FORM_INVALID: resident_panel guides must be an array of sketch "
                "labels or {label, open_confirmed}; nothing was selected and the dialog was not "
                "opened");
        for (size_t index = 0; index < op["guides"].size(); ++index) {
            read_position(op["guides"].at(index), "guide", index);
            if (wants.back().point)
                throw std::runtime_error(
                    "PANEL_POINT_NOT_A_GUIDE: resident_panel guide " + std::to_string(index) +
                    " is a point; a guide is a curve crossing every section and cannot be a "
                    "convergence end. Nothing was selected and the dialog was not opened");
        }
        guide_count = wants.size() - section_count;
        // An explicit empty array means "no second direction": the shared schema
        // always serializes guides, so requiring 2 here would refuse every
        // first-direction-only request (including a point convergence).
        if (guide_count == 1 || guide_count > 8)
            throw std::runtime_error(
                "PANEL_SECTION_COUNT_OUT_OF_RANGE: the panel route selects 2 to 8 second-direction "
                "guides; omit the array or pass 2 to 8");
    }
    if (wants.size() > (size_t)mechdog_panel::position_limit)
        throw std::runtime_error(
            "PANEL_SECTION_COUNT_OUT_OF_RANGE: the panel route selects 2 to " +
            std::to_string(mechdog_panel::position_limit) +
            " positions per run (sections and guides together); this request has " +
            std::to_string(wants.size()));
    if (guide_count > 0 && second_direction_macro.empty())
        // A guide cannot be picked until the second-direction collector is active. The
        // profile is the only source of that recorded switch, so a request with guides
        // against a first-direction-only profile is refused before the dialog opens.
        throw std::runtime_error(
            "PANEL_COMMAND_MISSING: the request selects " + std::to_string(guide_count) +
            " second-direction guides but the profile freezes no second_direction_macro; the "
            "dialog was not opened and no position was selected.");

    ProMdl model = nullptr;
    CK(ProMdlCurrentGet(&model));
    ProMdlName live_name;
    CK(ProMdlMdlnameGet(model, live_name));
    const std::string model_name_utf8 = utf8(live_name);
    if (!wanted_model.empty() && model_name_utf8 != wanted_model)
        throw std::runtime_error("PANEL_MODEL_CHANGED: the request names model " + wanted_model +
                                 " but the session holds " + model_name_utf8 +
                                 "; no selection was attempted and the ids were not reused");
    int model_id = 0;
    CK(ProMdlIdGet(model, &model_id));
    const mechdog_panel_ref::PanelResolution resolution = mechdog_panel_ref::resolve_panel_sections(
        (ProSolid)model, model_name_utf8, std::to_string(model_id), wants,
        mechdog_panel_ref::PanelCurveOpenness::Open);
    if (!resolution.ok) {
        std::string detail;
        for (const auto &receipt : resolution.receipts)
            if (!receipt.ok) {
                detail = receipt.message;
                break;
            }
        throw std::runtime_error(resolution.code + ": " + detail);
    }

    wchar_t executable[MAX_PATH];
    GetModuleFileNameW(nullptr, executable, MAX_PATH);
    const auto build = std::filesystem::path(executable).parent_path();
    std::string resident_command;
    ProToolkitDllHandle module = resident_blend_callback(build, resident_command);
    if (!module)
        require_blend_callback_setup(build);
    // The panel generation is a different deployment of the same payload: protocol 4
    // over loader ABI 2. A blend-generation deployment cannot serve this route.
    J setup;
    try {
        std::ifstream setup_file(build / L"blend_callback_setup.json");
        setup_file >> setup;
    } catch (...) {
        throw std::runtime_error(
            "PANEL_DEPLOYMENT_REQUIRED: the callback setup metadata cannot be read; prepare a "
            "panel deployment instead of a blend one");
    }
    if (setup.value("protocol", 0) != mechdog_panel::protocol ||
        setup.value("loader_abi", 0) != mechdog_panel::loader_abi)
        throw std::runtime_error(
            "PANEL_DEPLOYMENT_REQUIRED: the registered callback declares protocol " +
            std::to_string(setup.value("protocol", 0)) + " / loader ABI " +
            std::to_string(setup.value("loader_abi", 0)) +
            "; the panel route needs protocol 4 over ABI 2. Prepare that deployment and restart "
            "Creo before retrying; no feature was created.");

    // Pre-flight: every frozen command is checked before the dialog opens. Discovering
    // a missing Done after the panel is on screen would leave a run nobody can close,
    // so this refusal happens before Prepare and before any macro is loaded.
    const std::string select_template = panel.value("select_command", "");
    if (done_command.empty() || done_macro.empty() || select_template.empty())
        throw std::runtime_error(
            "PANEL_COMMAND_MISSING: the profile must freeze done_command (verified with "
            "ProCmdCmdIdFind), done_macro (the restricted Done) and select_command; the request "
            "carries " +
            std::to_string(!done_command.empty()) + "/" + std::to_string(!done_macro.empty()) +
            "/" + std::to_string(!select_template.empty()) +
            " of them. The dialog was not opened and no position was selected.");
    if (select_template.find(mechdog_panel::select_placeholder) == std::string::npos)
        throw std::runtime_error(
            std::string("PANEL_COMMAND_MISSING: select_command must contain ") +
            mechdog_panel::select_placeholder +
            "; a step that cannot name the resident command would degrade back into waiting for a "
            "human screen pick. The dialog was not opened.");
    if (select_template.find("~ Command `") == std::string::npos)
        // A bare placeholder substitutes to a bare command name, which the macro
        // engine ignores: three Creo 10 attempts consumed zero positions that way.
        throw std::runtime_error(
            "PANEL_COMMAND_MISSING: select_command must be the whole macro line "
            "~ Command `%MECHDOG_COMMAND%`;, not the bare placeholder; a command name without the "
            "~ Command wrapper is not a macro step. The dialog was not opened.");
    {
        // T1-B proved that a resident action registered with ProCmdActionAdd is
        // invocable by a macro "~ Command" line, but only if the action exists under
        // exactly that name. Resolve it before the dialog opens so a bad name is a
        // refusal, not a silent macro line with zero selections.
        std::string select_name = resident_command;
        uiCmdCmdId select_id = 0;
        const ProError found = ProCmdCmdIdFind(&select_name[0], &select_id);
        if (found != PRO_TK_NO_ERROR || select_id == 0)
            throw std::runtime_error(
                "PANEL_COMMAND_MISSING: ProCmdCmdIdFind cannot resolve the resident selection "
                "command '" +
                resident_command + "' (code " + std::to_string((int)found) +
                "); the payload registered no action this session can invoke, so every selection "
                "step would be a no-op. The dialog was not opened.");
    }
    {
        // ProCmdCmdIdFind takes a mutable char*, so it is handed a copy rather than
        // casting away constness on the profile text.
        std::string done_name = done_command;
        uiCmdCmdId done_id = 0;
        const ProError found = ProCmdCmdIdFind(&done_name[0], &done_id);
        if (found != PRO_TK_NO_ERROR || done_id == 0)
            throw std::runtime_error(
                "PANEL_COMMAND_MISSING: ProCmdCmdIdFind cannot resolve done_command '" +
                done_command + "' (code " + std::to_string((int)found) +
                "); the profile names a command this session does not know. The dialog was not "
                "opened.");
    }

    activate_blend_context();
    CK(ProSelbufferClear());
    const std::string token = "MechDogPanel_" + std::to_string(GetCurrentProcessId()) + "_" +
                              std::to_string(GetTickCount64());
    std::filesystem::path callback_dir = std::filesystem::path(generic_job) / token;
    std::filesystem::create_directory(callback_dir);
    J sections = J::array();
    for (size_t index = 0; index < resolution.table.refs.size(); ++index) {
        const auto &ref = resolution.table.refs[index];
        J entry{{"label", ref.label}, {"feature_id", ref.feature_id}};
        if (ref.point) {
            entry["kind"] = "point";
            entry["point_id"] = ref.point_id;
        } else {
            entry["curve_id"] = ref.curve_id;
        }
        sections.push_back(entry);
    }
    {
        // The optional collector switch travels with the run as evidence: the payload
        // does not need it to select, but callback_result.json then names the exact
        // sequence this dialog was driven with. It is omitted when the profile has no
        // such slot, so the first-direction request stays byte-identical.
        J request_doc{{"protocol", mechdog_panel::protocol},
                      {"contract", mechdog_panel::contract},
                      {"request_id", request_id},
                      {"job_id", job_id},
                      {"nonce", nonce},
                      {"profile_id", profile_id},
                      {"model_name", model_name_utf8},
                      {"model_id", std::to_string(model_id)},
                      {"command", resident_command},
                      {"sections", sections},
                      {"done_macro", done_macro},
                      {"done_command", done_command}};
        if (!second_direction_macro.empty())
            request_doc["second_direction_macro"] = second_direction_macro;
        if (guide_count > 0)
            // The payload groups the one-shot tickets by direction, so the first
            // guide replaces the empty second collector instead of toggling into it.
            request_doc["second_direction_start"] = static_cast<int>(section_count);
        std::ofstream request(callback_dir / L"callback_request.json", std::ios::binary);
        request << request_doc.dump(2);
    }
    log("PANEL_CALLBACK_MODE=resident_panel\n");
    // BUG-120/T1-B (Creo 10, 2026-11-17): the whole dialog sequence must be ONE
    // macro - open, one resident command per position, Done. Any further Toolkit
    // task sent after the panel opens blocks until the session reports
    // PRO_TK_COMM_ERROR (-11), and the macro itself runs asynchronously, so the
    // result is read from the payload's callback_result.json, never from a task.
    auto read_panel_state = [&]() -> J {
        J outcome = J::object();
        try {
            std::ifstream result_file(callback_dir / L"callback_result.json");
            result_file >> outcome;
        } catch (...) {
            outcome = J::object();
        }
        return outcome;
    };
    auto panel_selected = [&](const J &outcome) {
        int selected = outcome.value("selected", 0);
        if (outcome.contains("panel") && outcome["panel"].is_object())
            selected = outcome["panel"].value("selected", selected);
        return selected;
    };
    // This build observes the exit through Creo's own bracket callback on the Done
    // command (registered by the payload before the dialog opened). The event file is
    // written on the UI thread, so it survives exactly where a Toolkit task would
    // block. The event is ordered against the payload's own last-selection time, not
    // the worker's poll clock: polling can notice a selection later than it happened.
    auto read_bracket_exit = [&]() -> J {
        J event = J::object();
        try {
            // The payload persists callback_result.json and panel_exit.json in the
            // per-run callback directory, not in the job root.
            std::ifstream file(callback_dir / L"panel_exit.json");
            file >> event;
        } catch (...) {
            event = J::object();
        }
        return event;
    };
    auto read_panel_exit = [&]() -> J {
        const J outcome = read_panel_state();
        const J state =
            outcome.contains("panel") && outcome["panel"].is_object() ? outcome["panel"] : J();
        const J bracket = read_bracket_exit();
        const long long selected_at = state.is_object() ? state.value("selected_at_ms", 0LL) : 0LL;
        const bool finished = bracket.is_object() && bracket.value("entering", 1) == 0 &&
                              bracket.value("nonce", "") == nonce && selected_at > 0 &&
                              bracket.value("at_epoch_ms", 0LL) >= selected_at;
        if (finished)
            return J{
                {"method", "command_bracket"},
                {"supported", true},
                {"closed", true},
                {"reason",
                 "Creo reported the Done command's after-execution bracket for this run, so the "
                 "dialog's command returned after every position was consumed"},
                {"evidence", {{"bracket", bracket}, {"panel", state}}}};
        J observation = {
            {"method", "callback_result"},
            {"supported", false},
            {"closed", J()},
            {"reason",
             "no after-execution bracket for this run's Done command has been observed yet; the "
             "panel exit stays unobservable in this process state"},
            {"evidence", {{"bracket", bracket}, {"panel", state}}}};
        if (state.is_object() && state.value("closed", false)) {
            observation["supported"] = true;
            observation["closed"] = true;
            observation["reason"] =
                "the payload recorded a complete Done->AfterTerminal->OuterDrain sequence";
        }
        return observation;
    };
    auto stage_panel = [&](int selected) {
        stage_operation_result({{"op", "surface_loft"},
                                {"creation_route", "resident_panel"},
                                {"panel",
                                 {{"profile_id", profile_id},
                                  {"selected", selected},
                                  {"slots", static_cast<int>(sections.size())}}},
                                {"selection_intent", {{"labels", intent_labels}}},
                                {"exit_observation", read_panel_exit()}});
    };
    resident_blend_task(module, "MechDogPanelPrepare",
                        (callback_dir / L"callback_request.json").wstring());
    // The recorded sequence opens the dialog. The recording's screen-pick pauses are
    // replaced by one invocation of the resident command per position, and the
    // restricted Done is appended to the same macro: T1-B proved this order on
    // Creo 10, and a separate Finalize call would block behind the open dialog.
    std::string select_text = select_template;
    select_text.replace(select_text.find(mechdog_panel::select_placeholder),
                        std::strlen(mechdog_panel::select_placeholder), resident_command);
    std::string sequence = open_macro;
    // BUG-120/D7: the recorded second-direction collector switch sits between the two
    // direction phases, because the dialog's active collector decides where the next
    // selection lands. Without guides the macro is absent and the sequence is
    // byte-identical to the certified first-direction profile. It is never sent as a
    // separate task: anything queued after the dialog opens blocks behind it (T1-B,
    // Creo 10).
    for (size_t index = 0; index < section_count; ++index)
        sequence += "\n" + select_text;
    if (guide_count > 0)
        sequence += "\n" + second_direction_macro;
    for (size_t index = section_count; index < sections.size(); ++index)
        sequence += "\n" + select_text;
    sequence += "\n" + done_macro;
    {
        // The exact text is evidence: a macro line that silently does nothing is
        // otherwise indistinguishable from a dialog that never opened.
        std::string shown;
        for (char c : sequence)
            shown += c == '\n' ? " | " : std::string(1, c);
        log("PANEL_MACRO=%s\n", shown.c_str());
    }
    CK(trace_blend_call("panel_macro_submit", [&] { return ProMacroLoad(wide(sequence).data()); }));
    // Bounded wait for the payload to record one ticket per position. Only the file
    // is polled: a Toolkit task here is exactly what blocked the 2026-11-18 run.
    int selected = panel_selected(read_panel_state());
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(60);
    while (selected < static_cast<int>(sections.size()) &&
           std::chrono::steady_clock::now() < deadline) {
        std::this_thread::sleep_for(std::chrono::milliseconds(250));
        selected = panel_selected(read_panel_state());
    }
    // The Done command's after-execution bracket is written when its dialog finally
    // closes, which can be a few hundred milliseconds after the last ticket. Wait for
    // that event with a bounded file poll; no Toolkit task is sent.
    if (selected >= static_cast<int>(sections.size())) {
        const auto exit_deadline = std::chrono::steady_clock::now() + std::chrono::seconds(30);
        while (std::chrono::steady_clock::now() < exit_deadline) {
            const J state = read_panel_state();
            const long long selected_at =
                state.is_object() ? state.value("selected_at_ms", 0LL) : 0LL;
            const J event = read_bracket_exit();
            if (event.is_object() && event.value("entering", 1) == 0 &&
                event.value("nonce", "") == nonce && selected_at > 0 &&
                event.value("at_epoch_ms", 0LL) >= selected_at)
                break;
            std::this_thread::sleep_for(std::chrono::milliseconds(200));
        }
    }
    stage_panel(selected);
    if (selected != static_cast<int>(sections.size()))
        throw std::runtime_error(
            "PANEL_SELECTION_INCOMPLETE: the callback consumed " + std::to_string(selected) +
            " of " + std::to_string(sections.size()) +
            " positions; inspect callback_result.json and the native log. The dialog may still be "
            "open, so the run is reported as unconfirmed instead of successful, and no further "
            "Toolkit task is sent because that would block behind the dialog.");
    log("PANEL_ROUTE=resident_panel selected=%zu\n", sections.size());
}

#endif // MECHDOG_PANEL_RUN_H
