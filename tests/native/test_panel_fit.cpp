// BUG-120 task 2: compile and run the curve-fit diagnostics without Creo.
//
// native/panel_fit.h calls no Pro* function: the caller supplies the point
// evaluator. This test uses analytic curves, so the sampling and refinement
// rules are proven before the Toolkit adapter (panel_run.h) uses them on a real
// model. A pass here says nothing about a live Creo session.
#include "panel_fit.h"

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

namespace {

int failures = 0;

void check(bool condition, const std::string &what) {
    if (!condition) {
        std::printf("FAIL %s\n", what.c_str());
        ++failures;
    }
}

using Point = std::array<double, 3>;

//: Analytic evaluators below: t in [0,1] maps to a straight segment.
struct Segment {
    Point start;
    Point end;
};

bool evaluate_segment(const mechdog_panel_fit::FitCurve &curve, double t, Point &point) {
    const auto &segments = *static_cast<const std::vector<Segment> *>(curve.user_data);
    if (segments.empty())
        return false;
    const Segment &segment = segments.front();
    for (int axis = 0; axis < 3; ++axis)
        point[axis] = segment.start[axis] + (segment.end[axis] - segment.start[axis]) * t;
    return true;
}

mechdog_panel_fit::FitCurve curve(const char *role, const char *label,
                                  const std::vector<Segment> *segments) {
    mechdog_panel_fit::FitCurve value;
    value.role = role;
    value.label = label;
    value.feature_id = 40;
    value.curve_id = 45;
    value.user_data = segments;
    return value;
}

void crossing_lines_are_measured() {
    const std::vector<Segment> section{{{-10.0, 0.0, 0.0}, {10.0, 0.0, 0.0}}};
    const std::vector<Segment> guide{{{0.0, -10.0, 0.0}, {0.0, 10.0, 0.0}}};
    const std::vector<mechdog_panel_fit::FitCurve> sections{
        curve("section", "sec_a", &section)};
    const std::vector<mechdog_panel_fit::FitCurve> guides{curve("guide", "guide_a", &guide)};
    const auto report = mechdog_panel_fit::analyse(
        sections, guides, evaluate_segment, 0.5, std::vector<int>{0}, std::vector<int>{0});
    check(report.pairs.size() == 1, "one pair is reported");
    const auto &pair = report.pairs.front();
    check(pair.measured, "the crossing pair was measured");
    check(pair.state == "crossing", "a crossing inside the tolerance is named crossing");
    check(pair.min_distance <= 0.5, "the measured distance is inside the tolerance");
    check(std::fabs(pair.section_t - 0.5) < 1e-3, "the section parameter is near the midpoint");
    check(std::fabs(pair.guide_t - 0.5) < 1e-3, "the guide parameter is near the midpoint");
    check(pair.endpoints_measured, "exact endpoints were evaluated");
}

void separated_lines_stay_unverified() {
    const std::vector<Segment> section{{{-10.0, 0.0, 0.0}, {10.0, 0.0, 0.0}}};
    const std::vector<Segment> guide{{{0.0, 2.0, 0.0}, {0.0, 12.0, 0.0}}};
    const std::vector<mechdog_panel_fit::FitCurve> sections{
        curve("section", "sec_a", &section)};
    const std::vector<mechdog_panel_fit::FitCurve> guides{curve("guide", "guide_a", &guide)};
    const auto report = mechdog_panel_fit::analyse(
        sections, guides, evaluate_segment, 0.5, std::vector<int>{0}, std::vector<int>{0});
    const auto &pair = report.pairs.front();
    check(pair.measured, "a separated pair is still measured");
    check(pair.state == "no_sample_intersection",
          "a sampled minimum farther than tolerance is not called 'no crossing'");
    check(pair.min_distance > 0.5, "the measured gap is reported");
    check(std::fabs(pair.min_distance - 2.0) < 1e-4, "the gap is the true 2 mm offset");
}

void a_small_endpoint_gap_is_still_a_crossing() {
    const std::vector<Segment> section{{{0.0, 0.0, 0.0}, {10.0, 0.0, 0.0}}};
    const std::vector<Segment> guide{{{0.2, 0.0, 0.0}, {0.2, 10.0, 0.0}}};
    const std::vector<mechdog_panel_fit::FitCurve> sections{
        curve("section", "sec_a", &section)};
    const std::vector<mechdog_panel_fit::FitCurve> guides{curve("guide", "guide_a", &guide)};
    const auto report = mechdog_panel_fit::analyse(
        sections, guides, evaluate_segment, 0.5, std::vector<int>{0}, std::vector<int>{0});
    const auto &pair = report.pairs.front();
    check(pair.state == "crossing", "a 0.2 mm gap is inside the stated tolerance");
    check(pair.endpoint_min_distance <= 0.5, "the exact endpoint gap is reported separately");
}

void a_failed_evaluation_is_unverified_without_a_zero() {
    const std::vector<Segment> section{{{-10.0, 0.0, 0.0}, {10.0, 0.0, 0.0}}};
    const std::vector<Segment> guide{};
    const std::vector<mechdog_panel_fit::FitCurve> sections{
        curve("section", "sec_a", &section)};
    const std::vector<mechdog_panel_fit::FitCurve> guides{curve("guide", "guide_a", &guide)};
    const auto report = mechdog_panel_fit::analyse(
        sections, guides, evaluate_segment, 0.5, std::vector<int>{0}, std::vector<int>{0});
    const auto &pair = report.pairs.front();
    check(!pair.measured, "an unevaluable guide is not measured");
    check(pair.state == "unverified", "the pair stays unverified");
    check(!(pair.min_distance == pair.min_distance), "no zero distance is written for a failure");
    check(report.unverified_pairs == 1, "the summary counts the unverified pair");
}

void crossing_order_is_read_from_the_guide_parameter() {
    const std::vector<Segment> sec_a{{{-10.0, 0.0, 0.0}, {10.0, 0.0, 0.0}}};
    const std::vector<Segment> sec_b{{{-10.0, 5.0, 0.0}, {10.0, 5.0, 0.0}}};
    const std::vector<Segment> guide{{{0.0, -10.0, 0.0}, {0.0, 10.0, 0.0}}};
    const std::vector<mechdog_panel_fit::FitCurve> sections{
        curve("section", "sec_a", &sec_a), curve("section", "sec_b", &sec_b)};
    const std::vector<mechdog_panel_fit::FitCurve> guides{curve("guide", "guide_a", &guide)};
    const auto report = mechdog_panel_fit::analyse(
        sections, guides, evaluate_segment, 0.5, std::vector<int>{0, 0}, std::vector<int>{0});
    check(report.orders.size() == 1, "one guide order is reported");
    const auto &order = report.orders.front();
    check(order.available, "both sections crossed the guide");
    check(order.consistent, "the crossing parameter advances monotonically");
    check(order.direction == "forward", "the direction is forward");
}

} // namespace

int main() {
    crossing_lines_are_measured();
    separated_lines_stay_unverified();
    a_small_endpoint_gap_is_still_a_crossing();
    a_failed_evaluation_is_unverified_without_a_zero();
    crossing_order_is_read_from_the_guide_parameter();
    if (failures == 0) {
        std::printf("panel_fit: all rules hold\n");
        return 0;
    }
    std::printf("panel_fit: %d failure(s)\n", failures);
    return 1;
}
