// Only the registered loader links Toolkit. Payloads call this explicit host API,
// so no unregistered Toolkit DLL runtime or private initialization is involved.
//
// Two ABI generations live here at once:
//
// - ``MechDogCallbackApi`` (ABI 1) is the 0.27.0 boundary-blend table. It stays
//   byte-identical so an already registered ABI1 payload keeps working.
// - ``MechDogCallbackApi2`` (ABI 2, BUG-120/D3) repeats the ABI1 members in the
//   same order and appends what the resident-panel route needs: loading a UI macro
//   (the route replays commands instead of building an element tree), locating the
//   native boundary-blend command, bracketing it so its open/Done/Quit sequence is
//   observable, and the curve queries D2 needs to resolve a real reference.
//
// Append-only: a field is never reordered or removed. A payload that was built
// against the shorter table reads fewer entries and must not be handed the longer
// one by accident, which is why the loader checks the declared ABI first.
#pragma once
#include <ProToolkitDll.h>
#include <ProUICmd.h>
#include <ProMdl.h>
#include <ProModelitem.h>
#include <ProSelection.h>
#include <ProArray.h>
#include <ProMenu.h>
#include <ProFeature.h>
#include <ProCurve.h>

struct MechDogCallbackApi {
    int abi;
    size_t size;
    decltype(&ProArraySizeGet) array_size;
    decltype(&ProArrayAlloc) array_alloc;
    decltype(&ProArgumentProarrayFree) arguments_free;
    decltype(&ProValuedataWstringSet) wstring_set;
    decltype(&ProMdlCurrentGet) current_model;
    decltype(&ProMdlMdlnameGet) model_name;
    decltype(&ProModelitemInit) model_item;
    decltype(&ProSelectionAlloc) selection_alloc;
    decltype(&ProSelectExternalselectionRecord) selection_record;
    decltype(&ProSelectionFree) selection_free;
    decltype(&ProCmdActionAdd) command_add;
};

struct MechDogCallbackApi2 {
    int abi;
    size_t size;
    // ABI1 prefix: same order, same meaning.
    decltype(&ProArraySizeGet) array_size;
    decltype(&ProArrayAlloc) array_alloc;
    decltype(&ProArgumentProarrayFree) arguments_free;
    decltype(&ProValuedataWstringSet) wstring_set;
    decltype(&ProMdlCurrentGet) current_model;
    decltype(&ProMdlMdlnameGet) model_name;
    decltype(&ProModelitemInit) model_item;
    decltype(&ProSelectionAlloc) selection_alloc;
    decltype(&ProSelectExternalselectionRecord) selection_record;
    decltype(&ProSelectionFree) selection_free;
    decltype(&ProCmdActionAdd) command_add;
    // ABI2 additions.
    decltype(&ProMacroLoad) macro_load;
    decltype(&ProCmdCmdIdFind) command_id_find;
    decltype(&ProCmdBracketFuncAdd) bracket_func_add;
    decltype(&ProFeatureGeomitemVisit) feature_geomitem_visit;
    decltype(&ProCurveInit) curve_init;
    decltype(&ProCurveTypeGet) curve_type_get;
    decltype(&ProCurveLengthEval) curve_length_eval;
};
