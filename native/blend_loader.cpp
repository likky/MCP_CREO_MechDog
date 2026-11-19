// The operator registers this immutable loader once per loader/SDK generation.
// Only explicit GUI startup reads deployment.json and loads the selected payload.
#define NOMINMAX
#include <windows.h>
#include <ProToolkitDll.h>
#include <ProArray.h>
#include <filesystem>
#include <fstream>
#include "third_party/json.hpp"
#include "callback_identity.h"
#include "callback_api.h"
#include "panel_protocol.h"

static HMODULE payload = nullptr;
static bool initialized = false;
static bool attempted = false;
using Initialize = int (*)(int, char **, char *, char *, wchar_t *, const wchar_t *,
                           const wchar_t *, const MechDogCallbackApi *);
//: BUG-120/D3: an ABI2 payload takes the longer table. The two signatures are kept
//: apart so a payload can never be handed a table it was not built for.
using Initialize2 = int (*)(int, char **, char *, char *, wchar_t *, const wchar_t *,
                            const wchar_t *, const MechDogCallbackApi2 *);
static const MechDogCallbackApi host_api = {
    mechdog_callback::loader_abi,
    sizeof(MechDogCallbackApi),
    &ProArraySizeGet,
    &ProArrayAlloc,
    &ProArgumentProarrayFree,
    &ProValuedataWstringSet,
    &ProMdlCurrentGet,
    &ProMdlMdlnameGet,
    &ProModelitemInit,
    &ProSelectionAlloc,
    &ProSelectExternalselectionRecord,
    &ProSelectionFree,
    &ProCmdActionAdd,
};
//: The ABI2 table. The ABI1 prefix keeps its exact order; the additions are the
//: calls the panel route and D2 reference resolution actually make.
static const MechDogCallbackApi2 host_api2 = {
    mechdog_panel::loader_abi,
    sizeof(MechDogCallbackApi2),
    &ProArraySizeGet,
    &ProArrayAlloc,
    &ProArgumentProarrayFree,
    &ProValuedataWstringSet,
    &ProMdlCurrentGet,
    &ProMdlMdlnameGet,
    &ProModelitemInit,
    &ProSelectionAlloc,
    &ProSelectExternalselectionRecord,
    &ProSelectionFree,
    &ProCmdActionAdd,
    &ProMacroLoad,
    &ProCmdCmdIdFind,
    &ProCmdBracketFuncAdd,
    &ProFeatureGeomitemVisit,
    &ProCurveInit,
    &ProCurveTypeGet,
    &ProCurveLengthEval,
};
using Terminate = void (*)();
static Terminate terminate_payload = nullptr;
static ProTkdllFunction prepare_payload = nullptr, release_payload = nullptr,
                        identity_payload = nullptr;

extern "C" PRO_TK_DLL_EXPORT ProError MechDogBlendPrepare(ProArgument *in, ProArgument **out) {
    return initialized ? prepare_payload(in, out) : PRO_TK_BAD_CONTEXT;
}
extern "C" PRO_TK_DLL_EXPORT ProError MechDogBlendRelease(ProArgument *in, ProArgument **out) {
    return initialized ? release_payload(in, out) : PRO_TK_BAD_CONTEXT;
}
extern "C" PRO_TK_DLL_EXPORT ProError MechDogBlendIdentity(ProArgument *in, ProArgument **out) {
    return initialized ? identity_payload(in, out) : PRO_TK_BAD_CONTEXT;
}

//: BUG-120/D3: the panel generation's entry points, forwarded the same way. A worker
//: reaches the payload through the loader (ProToolkitTaskExecute names the loader's
//: exports), so the panel route needs its own forwarding exports; without them a
//: panel deployment would load and then have nothing callable.
static ProTkdllFunction panel_prepare_payload = nullptr, panel_finalize_payload = nullptr,
                        panel_event_payload = nullptr, panel_state_payload = nullptr,
                        panel_release_payload = nullptr;

extern "C" PRO_TK_DLL_EXPORT ProError MechDogPanelPrepare(ProArgument *in, ProArgument **out) {
    return initialized && panel_prepare_payload ? panel_prepare_payload(in, out)
                                                : PRO_TK_BAD_CONTEXT;
}
extern "C" PRO_TK_DLL_EXPORT ProError MechDogPanelFinalize(ProArgument *in, ProArgument **out) {
    return initialized && panel_finalize_payload ? panel_finalize_payload(in, out)
                                                 : PRO_TK_BAD_CONTEXT;
}
extern "C" PRO_TK_DLL_EXPORT ProError MechDogPanelEvent(ProArgument *in, ProArgument **out) {
    return initialized && panel_event_payload ? panel_event_payload(in, out) : PRO_TK_BAD_CONTEXT;
}
extern "C" PRO_TK_DLL_EXPORT ProError MechDogPanelState(ProArgument *in, ProArgument **out) {
    return initialized && panel_state_payload ? panel_state_payload(in, out) : PRO_TK_BAD_CONTEXT;
}
extern "C" PRO_TK_DLL_EXPORT ProError MechDogPanelRelease(ProArgument *in, ProArgument **out) {
    return initialized && panel_release_payload ? panel_release_payload(in, out)
                                                : PRO_TK_BAD_CONTEXT;
}

extern "C" __declspec(dllexport) int user_initialize(int argc, char **argv, char *version,
                                                     char *build, wchar_t errmsg[80]) {
    if (attempted) {
        wcscpy_s(errmsg, 80, L"Restart Creo before starting this loader again");
        return PRO_TK_BAD_CONTEXT;
    }
    attempted = true;
    try {
        wchar_t filename[MAX_PATH];
        HMODULE self = nullptr;
        if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                (LPCWSTR)&user_initialize, &self) ||
            !GetModuleFileNameW(self, filename, MAX_PATH))
            throw std::runtime_error("Cannot identify loader");
        auto directory = std::filesystem::path(filename).parent_path();
        std::ifstream input(directory / L"deployment.json", std::ios::binary);
        nlohmann::json deployment;
        input >> deployment;
        std::string digest = deployment.at("dll_sha256");
        const int declared_abi = deployment.value("loader_abi", 0);
        const int declared_protocol = deployment.value("protocol", mechdog_callback::protocol);
        if (!mechdog_callback::digest_valid(digest))
            throw std::runtime_error("Unsupported loader deployment");
        // BUG-120/D3: two ABI generations, never mixed. ABI1 stays the blend-only
        // table; ABI2 is the panel generation and must also declare protocol 4.
        if (declared_abi != mechdog_callback::loader_abi &&
            declared_abi != mechdog_panel::loader_abi)
            throw std::runtime_error("Unsupported loader deployment");
        const bool panel_generation = declared_abi == mechdog_panel::loader_abi;
        if (panel_generation &&
            mechdog_panel::contract_state(declared_protocol, declared_abi, true) !=
                mechdog_panel::ContractState::Ready)
            // 3/1 and 4/2 are different contracts; a mixed deployment is not
            // downgraded, it is not started.
            throw std::runtime_error("Panel deployment protocol mismatch");
        // Derive the absolute payload path from our own installation. The pointer
        // cannot redirect a registered loader into another installation directory.
        auto module =
            directory.parent_path().parent_path() / L"blend_callback" / digest / L"callback.dll";
        if (mechdog_callback::sha256(module) != digest)
            throw std::runtime_error("Callback payload hash mismatch");
        ProName application_id;
        ProError identified = ProToolkitDllIdGet(nullptr, application_id);
        if (identified)
            return identified;
        payload = LoadLibraryExW(module.c_str(), nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
        if (!payload)
            throw std::runtime_error("Cannot load callback payload");
        auto initialize = (Initialize)GetProcAddress(payload, "MechDogBlendInitialize");
        // The panel generation has its own entry point: an ABI2 payload is never
        // initialized through the blend entry.
        auto initialize2 = (Initialize2)GetProcAddress(payload, "MechDogPanelInitialize");
        terminate_payload = (Terminate)GetProcAddress(payload, "user_terminate");
        prepare_payload = (ProTkdllFunction)GetProcAddress(payload, "MechDogBlendPrepare");
        release_payload = (ProTkdllFunction)GetProcAddress(payload, "MechDogBlendRelease");
        identity_payload = (ProTkdllFunction)GetProcAddress(payload, "MechDogBlendIdentity");
        bool panel_exports_present = true;
        if (panel_generation) {
            for (const char *name : mechdog_panel::panel_exports)
                if (!GetProcAddress(payload, name))
                    panel_exports_present = false;
            panel_prepare_payload =
                (ProTkdllFunction)GetProcAddress(payload, "MechDogPanelPrepare");
            panel_finalize_payload =
                (ProTkdllFunction)GetProcAddress(payload, "MechDogPanelFinalize");
            panel_event_payload = (ProTkdllFunction)GetProcAddress(payload, "MechDogPanelEvent");
            panel_state_payload = (ProTkdllFunction)GetProcAddress(payload, "MechDogPanelState");
            panel_release_payload =
                (ProTkdllFunction)GetProcAddress(payload, "MechDogPanelRelease");
            panel_exports_present = panel_exports_present && panel_prepare_payload &&
                                    panel_finalize_payload && panel_event_payload &&
                                    panel_state_payload && panel_release_payload;
        }
        // Compare before combining: the two signatures are deliberately different
        // types, so they are never put in one conditional expression.
        const bool initialized_export = panel_generation
                                            ? (initialize2 != nullptr && panel_exports_present)
                                            : initialize != nullptr;
        if (!initialized_export || !terminate_payload || !prepare_payload || !release_payload ||
            !identity_payload)
            throw std::runtime_error("Callback loader ABI exports missing");
        int code = PRO_TK_GENERAL_ERROR;
        if (panel_generation)
            code = initialize2(argc, argv, version, build, errmsg, application_id, filename,
                               &host_api2);
        else
            code =
                initialize(argc, argv, version, build, errmsg, application_id, filename, &host_api);
        initialized = code == PRO_TK_NO_ERROR;
        // Never unload partially initialized code: a Toolkit command may already
        // reference it. Preserve it until process exit and report failure.
        return code;
    } catch (...) {
        wcscpy_s(errmsg, 80,
                 L"Callback setup invalid; rebuild and inspect deployment before startup");
        return PRO_TK_BAD_INPUTS;
    }
}

extern "C" __declspec(dllexport) void user_terminate() {
    if (initialized)
        terminate_payload();
    initialized = false;
    // No FreeLibrary: Creo command callbacks can outlive an application stop.
    // The process owns the payload image until a normal Creo restart.
}
