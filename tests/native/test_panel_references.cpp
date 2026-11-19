// BUG-120/D2: the curve-reference rules, proven without Creo or the Toolkit.
//
// panel_references.h holds no Toolkit call, so the local compiler can exercise every
// rejection path here. What this file does not prove is that the Toolkit adapter
// enumerates curves on the target host; that is D6's job and needs a live session.
#include <cmath>
#include <iostream>
#include <string>
#include <vector>

#include "panel_references.h"

namespace ref = mechdog_panel_ref;
using namespace mechdog_panel_ref;

namespace {

int failures = 0;

void expect(bool condition, const std::string &what) {
    if (!condition) {
        std::cerr << "FAIL: " << what << '\n';
        ++failures;
    }
}

void expect_code(const ref::PanelCurveReceipt &receipt, const std::string &code,
                 const std::string &what) {
    if (receipt.code != code || receipt.ok) {
        std::cerr << "FAIL: " << what << " expected " << code << " got " << receipt.code
                  << " (ok=" << receipt.ok << ")\n";
        ++failures;
    }
}

ref::PanelCurveRequest request() {
    ref::PanelCurveRequest want;
    want.label = "panel_a";
    want.owner_name = "SKETCH_A";
    want.feature_id = 412;
    want.curve_id = 9001;
    return want;
}

ref::PanelCurveProbe probe() {
    ref::PanelCurveProbe observed;
    observed.feature_found = true;
    observed.feature_id = 412;
    observed.curves_in_feature = 2;
    observed.curve_found = true;
    observed.curve_id = 9001;
    observed.ent_type = 3;
    observed.type_known = true;
    observed.composite = false;
    observed.openness = ref::PanelCurveOpenness::Open;
    observed.length_mm = 12.5;
    observed.length_known = true;
    return observed;
}

void test_open_curve_is_accepted() {
    const ref::PanelCurveReceipt receipt = ref::validate(request(), probe());
    expect(receipt.ok, "an open, typed, finite curve validates");
    expect(receipt.curve_id == 9001, "the receipt carries the observed curve id");
    expect(receipt.curve_type == 3, "the receipt carries the SDK curve type");
    expect(receipt.length_mm == 12.5, "the receipt carries the measured length");
    expect(receipt.openness_verified, "a validated reference records proven openness");
}

void test_api_failure_is_reported_as_itself() {
    ref::PanelCurveProbe observed = probe();
    observed.api_error = "ProCurveTypeGet";
    expect_code(ref::validate(request(), observed), "PANEL_CURVE_API_ERROR",
                "an API failure is not misread as a missing curve");
}

void test_missing_feature_and_owner() {
    ref::PanelCurveProbe missing = probe();
    missing.feature_found = false;
    expect_code(ref::validate(request(), missing), "PANEL_FEATURE_NOT_FOUND",
                "a stale feature id is refused");

    // T1-C's datum-plane counter-example: feature 40 exists but owns no curve.
    ref::PanelCurveProbe datum = probe();
    datum.feature_id = 40;
    datum.curves_in_feature = 0;
    datum.curve_found = false;
    expect_code(ref::validate(request(), datum), "PANEL_CURVE_NONE_IN_FEATURE",
                "a datum or solid feature is not a curve source");

    // The same curve id under a different owner: the feature holds curves, ours is
    // not among them.
    ref::PanelCurveProbe other_owner = probe();
    other_owner.curve_found = false;
    expect_code(ref::validate(request(), other_owner), "PANEL_CURVE_ID_NOT_IN_FEATURE",
                "a curve id owned by another feature is refused");
}

void test_type_rules() {
    ref::PanelCurveProbe untyped = probe();
    untyped.type_known = false;
    expect_code(ref::validate(request(), untyped), "PANEL_CURVE_TYPE_UNKNOWN",
                "an unknown type cannot rule out a composite curve");

    ref::PanelCurveProbe composite = probe();
    composite.composite = true;
    expect_code(ref::validate(request(), composite), "PANEL_CURVE_COMPOSITE",
                "a composite curve is refused before its length is trusted");
}

void test_openness_rules() {
    ref::PanelCurveProbe closed = probe();
    closed.openness = ref::PanelCurveOpenness::Closed;
    expect_code(ref::validate(request(), closed), "PANEL_CURVE_CLOSED",
                "a closed curve is not a blend section");

    ref::PanelCurveProbe unknown = probe();
    unknown.openness = ref::PanelCurveOpenness::Unknown;
    expect_code(ref::validate(request(), unknown), "PANEL_CURVE_OPENNESS_UNVERIFIED",
                "unknown openness is refused instead of assumed open");
}

void test_length_rules() {
    ref::PanelCurveProbe unmeasured = probe();
    unmeasured.length_known = false;
    expect_code(ref::validate(request(), unmeasured), "PANEL_CURVE_LENGTH_UNKNOWN",
                "an unevaluated length cannot prove the curve is non-degenerate");

    const std::vector<double> degenerate_lengths{0.0, -3.0, std::nan(""), (double)INFINITY};
    for (double length : degenerate_lengths) {
        ref::PanelCurveProbe degenerate = probe();
        degenerate.length_mm = length;
        expect_code(ref::validate(request(), degenerate), "PANEL_CURVE_LENGTH_INVALID",
                    "a zero, negative, NaN or infinite length is refused");
    }
}

void test_section_rules() {
    ref::PanelCurveRequest one = request();
    expect(ref::check_sections({one}) == "PANEL_SECTION_COUNT_OUT_OF_RANGE",
           "one position is below the 2-11 range");

    std::vector<ref::PanelCurveRequest> twelve;
    for (int i = 0; i < 12; ++i) {
        ref::PanelCurveRequest section = request();
        section.label = "panel_" + std::to_string(i);
        twelve.push_back(section);
    }
    expect(ref::check_sections(twelve) == "PANEL_SECTION_COUNT_OUT_OF_RANGE",
           "twelve positions are above the 2-11 range");

    std::vector<ref::PanelCurveRequest> eleven;
    for (int i = 0; i < 11; ++i) {
        ref::PanelCurveRequest section = request();
        section.label = "panel_" + std::to_string(i);
        eleven.push_back(section);
    }
    expect(ref::check_sections(eleven).empty(), "eleven distinct positions are accepted");

    std::vector<ref::PanelCurveRequest> duplicated{request(), request()};
    expect(ref::check_sections(duplicated) == "PANEL_SECTION_LABEL_DUPLICATE",
           "the same label twice is refused");

    std::vector<ref::PanelCurveRequest> blank{request(), request()};
    blank[1].label.clear();
    expect(ref::check_sections(blank) == "PANEL_SECTION_LABEL_EMPTY",
           "an empty label is refused");

    std::vector<ref::PanelCurveRequest> two{request(), request()};
    two[1].label = "panel_b";
    expect(ref::check_sections(two).empty(), "two distinct labels are accepted");
}

void test_model_rebinding() {
    PanelReferenceTable table;
    table.model_name = "panel_part";
    table.model_id = "session-7";
    table.refs.push_back(PanelCurveRef{"panel_a", "SKETCH_A", 412, 9001, 3, 12.5});

    expect(table.bound(), "a table with model identity is bound");
    expect(table.recheck("panel_part", "session-7").ok, "the same model re-checks clean");

    const ref::PanelCurveReceipt switched = table.recheck("other_part", "session-7");
    expect_code(switched, "PANEL_MODEL_CHANGED",
                "a model switch fails instead of reusing the curve ids");

    const ref::PanelCurveReceipt id_changed = table.recheck("panel_part", "session-8");
    expect_code(id_changed, "PANEL_MODEL_CHANGED",
                "a new session identity fails even with the same model name");

    PanelReferenceTable unbound;
    expect_code(unbound.recheck("panel_part", "session-7"), "PANEL_REFERENCE_UNBOUND",
                "an unbound table cannot be re-checked");
}

}  // namespace

int main() {
    test_open_curve_is_accepted();
    test_api_failure_is_reported_as_itself();
    test_missing_feature_and_owner();
    test_type_rules();
    test_openness_rules();
    test_length_rules();
    test_section_rules();
    test_model_rebinding();
    if (failures) {
        std::cerr << failures << " panel reference rule(s) failed\n";
        return 1;
    }
    std::cout << "panel_references: all rules hold; toolkit enumeration is D6\n";
    return 0;
}
