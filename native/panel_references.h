// panel_references.h — BUG-120/D2: what makes a curve reference real.
//
// The resident panel route asks the dialog to select curves that the MCP caller
// named by label. A label is not a curve: the alias table maps it to a feature id
// and a curve id, and those ids are only trustworthy if the model still holds that
// curve under that feature, if it is a single (non-composite) curve, if it is open
// and if it has a finite positive length. Sending the dialog a stale or wrong id is
// exactly the failure T1-C recorded (the macro picked something and the API still
// returned 0), so the reference is resolved and re-checked before any selection.
//
// This header holds only the rules. It includes no Toolkit header and calls no
// Pro* function, which is what lets tests/native/test_panel_references.cpp compile
// it with the local C++ compiler and prove every rejection path without Creo.
// The Toolkit adapter that fills PanelCurveProbe lives in panel_references_sdk.h.
//
// Openness is tri-state on purpose. A curve that is provably closed is refused, and
// a curve whose openness this build cannot prove is refused too: guessing "open"
// from a successful length evaluation is the kind of assumption BUG-120 rules out.
#ifndef MECHDOG_PANEL_REFERENCES_H
#define MECHDOG_PANEL_REFERENCES_H

#include <cmath>
#include <string>
#include <vector>

namespace mechdog_panel_ref {

//: A resolved, re-checked curve reference. ``curve_type`` keeps the SDK's own
//: ProEnttype value so a receipt never re-labels what the SDK reported.
struct PanelCurveRef {
    std::string label;
    std::string owner_name;
    int feature_id = 0;
    int curve_id = 0;
    int curve_type = 0;
    double length_mm = 0.0;
};

//: What the caller asked for: the label it used and the ids the alias table claims.
struct PanelCurveRequest {
    std::string label;
    std::string owner_name;
    int feature_id = 0;
    int curve_id = 0;
};

//: Whether a curve is open. UNKNOWN is not "probably open".
enum class PanelCurveOpenness { Open, Closed, Unknown };

//: What the Toolkit adapter observed. Every field is a fact it read, never a wish.
struct PanelCurveProbe {
    bool feature_found = false;
    int feature_id = 0;
    int curves_in_feature = 0;
    bool curve_found = false;
    int curve_id = 0;
    int ent_type = 0;
    bool type_known = false;
    bool composite = false;
    PanelCurveOpenness openness = PanelCurveOpenness::Unknown;
    double length_mm = 0.0;
    bool length_known = false;
    std::string api_error;
};

//: The verdict for one reference. ``ok`` is the only thing a caller may treat as
//: permission to select; every failure carries one of the codes below.
struct PanelCurveReceipt {
    bool ok = false;
    std::string code;
    std::string message;
    int curve_id = 0;
    int curve_type = 0;
    double length_mm = 0.0;
    bool openness_verified = false;
};

inline PanelCurveReceipt failure(const std::string &code, const std::string &message) {
    PanelCurveReceipt receipt;
    receipt.code = code;
    receipt.message = message;
    return receipt;
}

inline PanelCurveReceipt success(const PanelCurveRef &ref, bool openness_verified) {
    PanelCurveReceipt receipt;
    receipt.ok = true;
    receipt.curve_id = ref.curve_id;
    receipt.curve_type = ref.curve_type;
    receipt.length_mm = ref.length_mm;
    receipt.openness_verified = openness_verified;
    return receipt;
}

//: Reject a resolved reference that is not one open, finite, single curve under the
//: feature the label named. Order matters: an API failure is reported as itself
//: instead of being misread as "the curve is missing".
inline PanelCurveReceipt validate(const PanelCurveRequest &want, const PanelCurveProbe &probe) {
    if (!probe.api_error.empty())
        return failure("PANEL_CURVE_API_ERROR",
                       "a Toolkit query for this reference failed (" + probe.api_error +
                           "); no selection was made");
    if (!probe.feature_found)
        return failure("PANEL_FEATURE_NOT_FOUND",
                       "the label resolved to feature " + std::to_string(want.feature_id) +
                           ", which this model no longer holds");
    if (probe.curves_in_feature == 0)
        // A datum plane or a solid feature carries no curve at all; T1-C's datum id
        // counter-example lands here instead of becoming a bogus selection.
        return failure("PANEL_CURVE_NONE_IN_FEATURE",
                       "feature " + std::to_string(want.feature_id) +
                           " holds no curve, so the label does not name the datum or "
                           "reference geometry it was recorded against");
    if (!probe.curve_found)
        return failure("PANEL_CURVE_ID_NOT_IN_FEATURE",
                       "curve " + std::to_string(want.curve_id) + " is not one of the " +
                           std::to_string(probe.curves_in_feature) + " curves under feature " +
                           std::to_string(want.feature_id) +
                           "; the id belongs to another owner in this model");
    if (!probe.type_known)
        return failure("PANEL_CURVE_TYPE_UNKNOWN",
                       "the SDK did not report a type for curve " +
                           std::to_string(probe.curve_id) +
                           ", so a composite curve cannot be ruled out");
    if (probe.composite)
        return failure("PANEL_CURVE_COMPOSITE",
                       "curve " + std::to_string(probe.curve_id) +
                           " is a composite curve; the dialog takes single curves and its "
                           "length cannot be evaluated");
    if (probe.openness == PanelCurveOpenness::Closed)
        return failure("PANEL_CURVE_CLOSED",
                       "curve " + std::to_string(probe.curve_id) +
                           " is closed; a boundary-blend section must be an open curve");
    if (probe.openness == PanelCurveOpenness::Unknown)
        return failure("PANEL_CURVE_OPENNESS_UNVERIFIED",
                       "this build cannot prove curve " + std::to_string(probe.curve_id) +
                           " is open; the reference is refused instead of assumed open");
    if (!probe.length_known)
        return failure("PANEL_CURVE_LENGTH_UNKNOWN",
                       "the length of curve " + std::to_string(probe.curve_id) +
                           " was not evaluated, so a degenerate curve cannot be ruled out");
    if (!std::isfinite(probe.length_mm) || probe.length_mm <= 0.0)
        return failure("PANEL_CURVE_LENGTH_INVALID",
                       "curve " + std::to_string(probe.curve_id) + " has length " +
                           std::to_string(probe.length_mm) +
                           " mm; a boundary-blend section needs a finite positive length");
    PanelCurveRef ref;
    ref.label = want.label;
    ref.owner_name = want.owner_name;
    ref.feature_id = want.feature_id;
    ref.curve_id = probe.curve_id;
    ref.curve_type = probe.ent_type;
    ref.length_mm = probe.length_mm;
    return success(ref, true);
}

//: Section-count and label rules, checked before anything touches the model.
inline std::string check_sections(const std::vector<PanelCurveRequest> &sections) {
    if (sections.size() < 2 || sections.size() > 8)
        return "PANEL_SECTION_COUNT_OUT_OF_RANGE";
    for (size_t i = 0; i < sections.size(); ++i) {
        if (sections[i].label.empty())
            return "PANEL_SECTION_LABEL_EMPTY";
        for (size_t j = i + 1; j < sections.size(); ++j)
            if (sections[i].label == sections[j].label)
                return "PANEL_SECTION_LABEL_DUPLICATE";
    }
    return "";
}

//: The immutable reference table the callback re-checks before each selection. It
//: carries the model it was built for: a curve id from another model means nothing
//: here, and a model switch must fail instead of selecting a same-numbered curve.
struct PanelReferenceTable {
    std::string model_name;
    std::string model_id;
    std::vector<PanelCurveRef> refs;

    bool bound() const { return !model_name.empty() && !model_id.empty(); }

    PanelCurveReceipt recheck(const std::string &current_model_name,
                              const std::string &current_model_id) const {
        if (!bound())
            return failure("PANEL_REFERENCE_UNBOUND",
                           "the reference table has no model identity; it cannot be re-checked");
        if (current_model_name != model_name || current_model_id != model_id)
            return failure("PANEL_MODEL_CHANGED",
                           "the reference table was built for model " + model_name + " (" +
                               model_id + ") but the session now holds " + current_model_name +
                               " (" + current_model_id +
                               "); the selection was abandoned instead of reusing the ids");
        PanelCurveReceipt receipt;
        receipt.ok = true;
        return receipt;
    }
};

}  // namespace mechdog_panel_ref

#endif  // MECHDOG_PANEL_REFERENCES_H
