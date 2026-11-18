// BUG-120/D3: the panel selection protocol, proven without Creo or the Toolkit.
//
// panel_selection_state.h and panel_protocol.h make no Toolkit call, so every rule
// here is checked with the local compiler: one-shot tickets, OVERRIDE then TOGGLE,
// refused re-entry, Done gating, and the Done/AfterTerminal/OuterDrain order. What
// this does not prove is that a real bracket callback delivers those events in that
// order on Creo 10; that needs the target machine (D6).
#include <iostream>
#include <string>
#include <vector>

#include "panel_selection_state.h"
#include "panel_protocol.h"

namespace panel = mechdog_panel;

namespace {

int failures = 0;

void expect(bool condition, const std::string &what) {
    if (!condition) {
        std::cerr << "FAIL: " << what << '\n';
        ++failures;
    }
}

void expect_code(const panel::PanelVerdict &verdict, const std::string &code,
                 const std::string &what) {
    if (verdict.code != code || verdict.ok) {
        std::cerr << "FAIL: " << what << " expected " << code << " got " << verdict.code
                  << " (ok=" << verdict.ok << ")\n";
        ++failures;
    }
}

const std::vector<int> SLOTS{0, 1, 2};

panel::PanelSelectionState prepared() {
    panel::PanelSelectionState state;
    panel::PanelVerdict verdict =
        state.prepare("req-1", "job-1", "nonce-1", "panel_part", "session-7", SLOTS, true);
    expect(verdict.ok, "a valid Prepare is accepted");
    expect(state.stage() == panel::PanelStage::Prepared, "Prepare enters the prepared stage");
    return state;
}

void test_prepare_rules() {
    panel::PanelSelectionState state;
    expect_code(state.prepare("req-1", "job-1", "nonce-1", "part", "session", {0}, true),
                "PANEL_SLOT_COUNT_OUT_OF_RANGE", "one position is below the 2-8 range");
    expect_code(state.prepare("req-1", "job-1", "nonce-1", "part", "session", {0, 0}, true),
                "PANEL_SLOT_DUPLICATE", "the same position twice is refused");
    expect_code(
        state.prepare("req-1", "job-1", "nonce-1", "part", "session", {0, 1}, false),
        "PANEL_TICKET_REGISTRATION_FAILED",
        "a partially registered dialog is not started");
    expect(state.stage() == panel::PanelStage::Idle,
           "a refused Prepare leaves the state idle instead of half-started");
    expect_code(state.prepare("", "job-1", "nonce-1", "part", "session", {0, 1}, true),
                "PANEL_PREPARE_IDENTITY", "Prepare without a request id is refused");
    expect(state.prepare("req-1", "job-1", "nonce-1", "part", "session", {0, 1}, true).ok,
           "a well formed Prepare is accepted");

    // A second Prepare must not reset a live run, and must not destroy it either.
    expect_code(state.prepare("req-2", "job-1", "nonce-1", "part", "session", {0, 1}, true),
                "PANEL_STATE_NOT_IDLE", "a second Prepare is refused");
    expect(state.stage() == panel::PanelStage::Prepared,
           "the refused second Prepare leaves the live run running");
}

void test_override_then_toggle() {
    panel::PanelSelectionState state = prepared();
    const std::vector<panel::PanelTicket> tickets = state.tickets();
    expect(tickets.size() == 3, "one ticket per position");

    panel::PanelVerdict first = state.record(tickets[0]);
    expect(first.ok && first.action == panel::PanelSelectionAction::Override,
           "the first position replaces the dialog selection");

    expect_code(state.record(tickets[0]), "PANEL_TICKET_CONSUMED",
                "a repeated ticket at the same position is refused, not toggled");

    panel::PanelVerdict second = state.record(tickets[1]);
    expect(second.ok && second.action == panel::PanelSelectionAction::Toggle,
           "later positions toggle into the selection");

    // Positions are consumed in order; skipping ahead is refused.
    panel::PanelSelectionState skipping = prepared();
    const std::vector<panel::PanelTicket> ordered = skipping.tickets();
    skipping.record(ordered[0]);
    expect_code(skipping.record(ordered[2]), "PANEL_SLOT_OUT_OF_ORDER",
                "a position cannot be skipped");
}

void test_ticket_identity() {
    panel::PanelSelectionState state = prepared();
    std::vector<panel::PanelTicket> tickets = state.tickets();

    panel::PanelTicket stale = tickets[1];
    stale.ticket_id = "req-0/nonce-0/1";
    expect_code(state.record(stale), "PANEL_TICKET_STALE", "a stale macro is not replayed");

    panel::PanelTicket foreign = tickets[1];
    foreign.nonce = "nonce-2";
    expect_code(state.record(foreign), "PANEL_TICKET_NONCE", "a wrong nonce is refused");

    panel::PanelTicket other_model = tickets[1];
    other_model.model_id = "session-8";
    expect_code(state.record(other_model), "PANEL_TICKET_MODEL",
                "a ticket from another model is refused");

    panel::PanelTicket other_job = tickets[1];
    other_job.job_id = "job-2";
    expect_code(state.record(other_job), "PANEL_TICKET_JOB", "a ticket from another job is refused");

    panel::PanelTicket unknown_slot = tickets[1];
    unknown_slot.slot = 9;
    expect_code(state.record(unknown_slot), "PANEL_SLOT_UNKNOWN",
                "a position that was never prepared is refused");
}

void test_finalize_gates_done() {
    panel::PanelSelectionState incomplete = prepared();
    expect_code(incomplete.finalize(0), "PANEL_SELECTION_INCOMPLETE",
                "Done cannot be queued for a partial selection");
    expect(incomplete.stage() == panel::PanelStage::Locked,
           "an incomplete selection locks the run instead of retrying");

    panel::PanelSelectionState rejected = prepared();
    for (const panel::PanelTicket &ticket : rejected.tickets())
        rejected.record(ticket);
    expect_code(rejected.finalize(7), "PANEL_DONE_QUEUE_FAILED",
                "a refused Done queue is not a committed result");
    expect(rejected.stage() == panel::PanelStage::Locked,
           "a refused Done queue locks the run");

    panel::PanelSelectionState queued = prepared();
    for (const panel::PanelTicket &ticket : queued.tickets())
        queued.record(ticket);
    expect(queued.finalize(0).ok, "a successful Done queue is accepted");
    expect(queued.stage() == panel::PanelStage::DoneQueued, "finalize records done_queued");
    expect(!queued.closed(), "done_queued is not yet a closed panel");
}

//: A run whose items are all selected and whose Done queue returned 0.
panel::PanelSelectionState done_queued() {
    panel::PanelSelectionState state = prepared();
    for (const panel::PanelTicket &ticket : state.tickets())
        state.record(ticket);
    state.finalize(0);
    return state;
}

void test_end_sequence_order() {
    panel::PanelSelectionState state = done_queued();
    expect(state.observe({"done", 2, "job-1", "nonce-1"}).ok, "Done is accepted after finalize");
    expect(state.observe({"after_terminal", 4, "job-1", "nonce-1"}).ok,
           "AfterTerminal follows Done");
    expect(state.observe({"outer_drain", 5, "job-1", "nonce-1"}).ok,
           "OuterDrain follows AfterTerminal");
    expect(state.closed(), "the full in-order sequence closes the run");
}

void test_each_disorder_locks_the_run() {
    {
        panel::PanelSelectionState state = done_queued();
        expect_code(state.observe({"after_terminal", 1, "job-1", "nonce-1"}),
                    "PANEL_EVENT_OUT_OF_ORDER", "AfterTerminal before Done proves nothing");
        expect(state.stage() == panel::PanelStage::Locked, "the run is left unknown");
    }
    {
        panel::PanelSelectionState state = done_queued();
        state.observe({"done", 2, "job-1", "nonce-1"});
        expect_code(state.observe({"done", 3, "job-1", "nonce-1"}), "PANEL_EVENT_OUT_OF_ORDER",
                    "a second terminal event cannot restart the sequence");
    }
    {
        panel::PanelSelectionState state = done_queued();
        expect_code(state.observe({"outer_drain", 2, "job-1", "nonce-1"}),
                    "PANEL_EVENT_OUT_OF_ORDER",
                    "OuterDrain before AfterTerminal is a reversed order");
    }
    {
        panel::PanelSelectionState state = done_queued();
        state.observe({"done", 5, "job-1", "nonce-1"});
        expect_code(state.observe({"after_terminal", 5, "job-1", "nonce-1"}),
                    "PANEL_EVENT_OUT_OF_ORDER", "an event_seq that does not advance is refused");
    }
    {
        panel::PanelSelectionState state = done_queued();
        state.observe({"done", 5, "job-1", "nonce-1"});
        expect_code(state.observe({"after_terminal", 6, "job-1", "nonce-9"}),
                    "PANEL_EVENT_IDENTITY", "an event with the wrong nonce is refused");
    }
    {
        panel::PanelSelectionState state = done_queued();
        state.observe({"done", 5, "job-1", "nonce-1"});
        expect_code(state.observe({"nonsense", 6, "job-1", "nonce-1"}), "PANEL_EVENT_UNKNOWN",
                    "an unknown kind is refused");
    }
    {
        panel::PanelSelectionState state = done_queued();
        state.observe({"done", 1, "job-1", "nonce-1"});
        state.observe({"after_terminal", 2, "job-1", "nonce-1"});
        state.observe({"outer_drain", 3, "job-1", "nonce-1"});
        expect(state.closed(), "the run closed once");
        expect_code(state.observe({"outer_drain", 4, "job-1", "nonce-1"}),
                    "PANEL_EVENT_OUT_OF_ORDER", "a second OuterDrain cannot re-close a closed run");
    }
}

void test_release_rules() {
    panel::PanelSelectionState open = prepared();
    expect_code(open.release(), "PANEL_STATE_NOT_ENDED",
                "an open panel run cannot be released");

    panel::PanelSelectionState queued = done_queued();
    expect_code(queued.release(), "PANEL_STATE_NOT_ENDED", "a Done-queued run is not ended");
    expect(queued.stage() == panel::PanelStage::DoneQueued,
           "a refused release keeps the recorded stage");

    panel::PanelSelectionState done = prepared();
    for (const panel::PanelTicket &ticket : done.tickets())
        done.record(ticket);
    done.finalize(0);
    done.observe({"done", 1, "job-1", "nonce-1"});
    done.observe({"after_terminal", 2, "job-1", "nonce-1"});
    done.observe({"outer_drain", 3, "job-1", "nonce-1"});
    expect(done.closed(), "the completed run is closed");
    expect(done.release().ok, "a closed run can be released");
    expect(done.stage() == panel::PanelStage::Idle, "release returns to idle");
}

void test_quit_yes_is_a_terminal_event() {
    panel::PanelSelectionState state = prepared();
    for (const panel::PanelTicket &ticket : state.tickets())
        state.record(ticket);
    state.finalize(0);
    expect(state.observe({"quit_yes", 1, "job-1", "nonce-1"}).ok,
           "Quit with yes is a terminal event like Done");
    expect(state.observe({"after_terminal", 2, "job-1", "nonce-1"}).ok,
           "AfterTerminal follows Quit/yes");
    expect(state.observe({"outer_drain", 3, "job-1", "nonce-1"}).ok,
           "OuterDrain follows the Quit/yes chain");
    expect(state.closed(), "a Quit/yes chain also closes the run");
}

void test_contract_states() {
    expect(panel::protocol == 4, "this build speaks protocol 4");
    expect(panel::loader_abi == 2, "this build loads ABI 2 payloads");
    expect(panel::contract_state(4, 2, true) == panel::ContractState::Ready,
           "4/2 with a matching digest is ready");
    expect(panel::contract_state(3, 1, true) == panel::ContractState::ProtocolMismatch,
           "the 0.27.0 blend contract is a protocol mismatch for the panel route");
    expect(panel::contract_state(4, 1, true) == panel::ContractState::AbiMismatch,
           "protocol 4 over ABI 1 is refused, not downgraded");
    expect(panel::contract_state(4, 2, false) == panel::ContractState::DeploymentMismatch,
           "a digest mismatch is a deployment mismatch");
    expect(std::string(panel::contract_state_name(panel::ContractState::Ready)) == "ready",
           "the contract state is reportable by name");
}

void test_markers() {
    static const std::string kinds[] = {"panel_open_wait", "panel_select_wait", "panel_done_wait"};
    panel::PanelMarkerRead marker;
    marker.read = true;
    marker.job_id = "job-1";
    marker.nonce = "nonce-1";
    marker.kind = "panel_select_wait";
    marker.event_seq = 4;
    marker.model_matches = true;
    expect(panel::marker_valid(marker, "job-1", "nonce-1", kinds, 3),
           "a matching marker is progress");

    panel::PanelMarkerRead stale = marker;
    stale.nonce = "nonce-0";
    expect(!panel::marker_valid(stale, "job-1", "nonce-1", kinds, 3),
           "a stale nonce is not progress");

    panel::PanelMarkerRead unknown_kind = marker;
    unknown_kind.kind = "panel_almost";
    expect(!panel::marker_valid(unknown_kind, "job-1", "nonce-1", kinds, 3),
           "an untyped kind is not progress");

    panel::PanelMarkerRead zero_seq = marker;
    zero_seq.event_seq = 0;
    expect(!panel::marker_valid(zero_seq, "job-1", "nonce-1", kinds, 3),
           "a marker without an advancing sequence is not progress");

    panel::PanelMarkerRead half_read = marker;
    half_read.read = false;
    expect(!panel::marker_valid(half_read, "job-1", "nonce-1", kinds, 3),
           "a half-read marker is not progress");
}

}  // namespace

int main() {
    test_prepare_rules();
    test_override_then_toggle();
    test_ticket_identity();
    test_finalize_gates_done();
    test_end_sequence_order();
    test_each_disorder_locks_the_run();
    test_release_rules();
    test_quit_yes_is_a_terminal_event();
    test_contract_states();
    test_markers();
    if (failures) {
        std::cerr << failures << " panel selection rule(s) failed\n";
        return 1;
    }
    std::cout << "panel_selection_state: protocol 4 rules hold; native delivery is D6\n";
    return 0;
}
