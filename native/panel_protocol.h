// panel_protocol.h — BUG-120/D3: the wire contract for the resident panel.
//
// Protocol 3 / ABI 1 is the boundary-blend callback contract shipped in 0.27.0. The
// panel route needs more than that boundary offers: a macro load call (the route
// replays UI commands rather than building an element tree), and the SDK queries
// that make a curve reference and a panel exit observable. Those arrive as protocol
// 4 / ABI 2. The two are never mixed: a payload built for 3/1 cannot speak 4/2, and
// a loader that cannot see both halves reports not_ready instead of guessing.
//
// Everything here is SDK-free on purpose so the rules can be proven by
// tests/native/test_panel_selection_state.cpp with the local compiler.
#ifndef MECHDOG_PANEL_PROTOCOL_H
#define MECHDOG_PANEL_PROTOCOL_H

#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>

namespace mechdog_panel {

//: The panel wire contract. Changing either number is an incompatible change.
constexpr int protocol = 4;
constexpr int loader_abi = 2;
constexpr const char *contract = "resident-panel-selection-v4-ticketed-mm";

//: One entry per selection position the protocol will accept in a single run.
//: Sized by the documented resource boundary, not by the 2-8 section bound: the
//: tickets also cover probes that never become sections.
constexpr int ticket_capacity = 512;

//: Exports an ABI2 payload must provide. The panel generation uses its own prepare /
//: finalize / event / state / release entry points (the blend ones keep the blend
//: rules), plus the identity probe and the Toolkit-required terminate.
constexpr const char *panel_exports[] = {
    "MechDogPanelInitialize",
    "user_terminate",
    "MechDogPanelPrepare",
    "MechDogPanelFinalize",
    "MechDogPanelEvent",
    "MechDogPanelState",
    "MechDogPanelRelease",
    "MechDogBlendIdentity",
};

//: Why a deployment cannot serve the panel route. ``Ready`` is the only value a
//: caller may treat as usable; every other value keeps the route closed.
enum class ContractState {
    Ready,
    ProtocolMismatch,
    AbiMismatch,
    DeploymentMismatch,
};

inline const char *contract_state_name(ContractState state) {
    switch (state) {
    case ContractState::Ready:
        return "ready";
    case ContractState::ProtocolMismatch:
        return "protocol_mismatch";
    case ContractState::AbiMismatch:
        return "abi_mismatch";
    case ContractState::DeploymentMismatch:
        return "deployment_mismatch";
    }
    return "unknown";
}

//: Judge a deployment's declared numbers against this build. A 3/1 payload is a
//: valid *blend* deployment and an invalid *panel* one: that is a mismatch, not a
//: fallback opportunity.
inline ContractState contract_state(int deployment_protocol, int deployment_abi,
                                    bool digest_matches) {
    if (!digest_matches)
        return ContractState::DeploymentMismatch;
    if (deployment_protocol != protocol)
        return ContractState::ProtocolMismatch;
    if (deployment_abi != loader_abi)
        return ContractState::AbiMismatch;
    return ContractState::Ready;
}

//: A marker read from the job directory. Filled by the native reader; the rules
//: below never parse text, so they cannot accept a half-read file.
struct PanelMarkerRead {
    bool read = false;
    bool valid = false;
    std::string reason;
    std::string job_id;
    std::string nonce;
    std::string kind;
    int event_seq = 0;
    bool model_matches = false;
};

//: A marker counts only when it was read, names this job and nonce, carries a
//: positive sequence and names a known event kind. A marker from another job, a
//: stale nonce or a typo in the kind is "no progress", never progress.
inline bool marker_valid(const PanelMarkerRead &marker, const std::string &job_id,
                         const std::string &nonce, const std::string *known_kinds,
                         int known_count) {
    if (!marker.read || job_id.empty() || nonce.empty() || marker.job_id != job_id ||
        marker.nonce != nonce || marker.event_seq <= 0 || !marker.model_matches)
        return false;
    for (int index = 0; index < known_count; ++index)
        if (marker.kind == known_kinds[index])
            return true;
    return false;
}

//: Write a marker atomically: a temporary sibling is flushed and closed, then
//: renamed over the target. A failed rename reports the error; the old file is not
//: deleted first, because losing the previous marker is worse than a stale one.
inline bool write_marker_atomic(const std::filesystem::path &target, const std::string &text,
                                std::string &error) {
    std::error_code code;
    const std::filesystem::path temporary = target.string() + ".tmp";
    {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output) {
            error = "cannot open " + temporary.string();
            return false;
        }
        output.write(text.data(), (std::streamsize)text.size());
        output.flush();
        if (!output) {
            error = "cannot write " + temporary.string();
            return false;
        }
    }
    std::filesystem::rename(temporary, target, code);
    if (code) {
        error = "cannot replace " + target.string() + ": " + code.message();
        return false;
    }
    return true;
}

}  // namespace mechdog_panel

#endif  // MECHDOG_PANEL_PROTOCOL_H
