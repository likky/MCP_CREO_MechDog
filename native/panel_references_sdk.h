// panel_references_sdk.h — BUG-120/D2: the Toolkit half of panel_references.h.
//
// generic.cpp is the only compile unit that sees the Toolkit headers (worker.cpp
// includes it), so the adapter lives in a header included there instead of a new
// .cpp. It fills PanelCurveProbe with facts it reads and nothing else:
//
//   ProFeatureInit            — does this model still hold that feature id?
//   ProFeatureGeomitemVisit   — how many PRO_CURVE items does it own, and is our id
//                               one of them (the same visit blend_create.cpp uses)?
//   ProCurveInit              — the curve handle for that id
//   ProCurveTypeGet           — ProEnttype; PRO_ENT_CMP_CRV marks a composite curve
//   ProCurveLengthEval        — the length; the SDK documents it as unavailable for
//                               composite curves, which the composite check rules out
//                               first
//
// Openness is *passed in*, never assumed here. This build has no verified way to
// read whether a standalone curve is closed, and guessing "open" from a successful
// length evaluation is the assumption BUG-120 exists to avoid. A caller that has
// real proof supplies it; until then the probe says Unknown and the rules refuse
// the reference with PANEL_CURVE_OPENNESS_UNVERIFIED.
//
// Nothing here is verified on a running Creo in this change: the adapter compiles
// against the installed SDK and its reference rules are proven offline, which is a
// different claim from "the enumeration works on the target host" (D6).
#ifndef MECHDOG_PANEL_REFERENCES_SDK_H
#define MECHDOG_PANEL_REFERENCES_SDK_H

#include "panel_references.h"

namespace mechdog_panel_ref {

//: Visit context for ProFeatureGeomitemVisit. Counts every PRO_CURVE item and
//: records whether the wanted id is among them, which distinguishes "this feature
//: owns no curve at all" from "the id belongs to another owner".
struct PanelCurveVisit {
    int count = 0;
    int wanted = 0;
    bool found = false;
};

inline ProError panel_curve_visit(ProGeomitem *item, ProError status, ProAppData data) {
    if (status == PRO_TK_NO_ERROR && item && data) {
        PanelCurveVisit *visit = static_cast<PanelCurveVisit *>(data);
        ++visit->count;
        if (item->id == visit->wanted)
            visit->found = true;
    }
    return PRO_TK_NO_ERROR;
}

//: Read one curve under one feature. ``openness`` is the caller's proof, not ours.
inline PanelCurveProbe panel_probe_curve(ProSolid model, const PanelCurveRequest &want,
                                         PanelCurveOpenness openness) {
    PanelCurveProbe probe;
    probe.feature_id = want.feature_id;
    probe.curve_id = want.curve_id;
    probe.openness = openness;

    ProFeature feature;
    if (ProFeatureInit(model, want.feature_id, &feature) != PRO_TK_NO_ERROR) {
        probe.api_error = "ProFeatureInit:" + std::to_string((int)PRO_TK_E_NOT_FOUND);
        return probe;
    }
    probe.feature_found = true;

    PanelCurveVisit visit;
    visit.wanted = want.curve_id;
    ProError visited =
        ProFeatureGeomitemVisit(&feature, PRO_CURVE, panel_curve_visit, nullptr, &visit);
    if (visited != PRO_TK_NO_ERROR) {
        probe.api_error = "ProFeatureGeomitemVisit:" + std::to_string((int)visited);
        return probe;
    }
    probe.curves_in_feature = visit.count;
    probe.curve_found = visit.found;
    if (!visit.found)
        return probe;

    ProCurve curve;
    if (ProCurveInit(model, want.curve_id, &curve) != PRO_TK_NO_ERROR) {
        probe.api_error = "ProCurveInit:" + std::to_string((int)PRO_TK_E_NOT_FOUND);
        return probe;
    }
    ProEnttype curve_type = PRO_ENT_NONE;
    if (ProCurveTypeGet(curve, &curve_type) != PRO_TK_NO_ERROR) {
        probe.api_error = "ProCurveTypeGet";
        return probe;
    }
    probe.type_known = true;
    probe.ent_type = (int)curve_type;
    probe.composite = curve_type == PRO_ENT_CMP_CRV;

    double length = 0.0;
    if (ProCurveLengthEval(curve, &length) == PRO_TK_NO_ERROR) {
        probe.length_known = true;
        probe.length_mm = length;
    }
    return probe;
}

//: Resolve every requested section against the live model. The table is only bound
//: when every reference validated with the openness proof the caller supplied, so a
//: partially resolved plan can never reach a selection loop.
struct PanelResolution {
    PanelReferenceTable table;
    std::vector<PanelCurveReceipt> receipts;
    bool ok = false;
    std::string code;
};

inline PanelResolution resolve_panel_sections(ProSolid model, const std::string &model_name,
                                              const std::string &model_id,
                                              const std::vector<PanelCurveRequest> &sections,
                                              PanelCurveOpenness openness) {
    PanelResolution resolution;
    const std::string section_code = check_sections(sections);
    if (!section_code.empty()) {
        resolution.code = section_code;
        return resolution;
    }
    resolution.table.model_name = model_name;
    resolution.table.model_id = model_id;
    for (const PanelCurveRequest &want : sections) {
        const PanelCurveProbe probe = panel_probe_curve(model, want, openness);
        const PanelCurveReceipt receipt = validate(want, probe);
        resolution.receipts.push_back(receipt);
        if (!receipt.ok) {
            if (resolution.code.empty())
                resolution.code = receipt.code;
            continue;
        }
        PanelCurveRef ref;
        ref.label = want.label;
        ref.owner_name = want.owner_name;
        ref.feature_id = want.feature_id;
        ref.curve_id = probe.curve_id;
        ref.curve_type = probe.ent_type;
        ref.length_mm = probe.length_mm;
        resolution.table.refs.push_back(ref);
    }
    // All or nothing: a plan with one unproven section must not select the rest.
    resolution.ok = resolution.code.empty() && resolution.table.refs.size() == sections.size();
    if (!resolution.ok && resolution.code.empty())
        resolution.code = "PANEL_REFERENCE_INCOMPLETE";
    if (!resolution.ok)
        resolution.table.refs.clear();
    return resolution;
}

}  // namespace mechdog_panel_ref

#endif  // MECHDOG_PANEL_REFERENCES_SDK_H
