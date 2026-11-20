// panel_fit.h — BUG-120 task 2: section/guide fit diagnostics for the panel route.
//
// The recorded boundary-blend dialog accepts a first direction and an optional
// second direction. Whether every guide really crosses every section is the
// kernel's decision, but a caller should learn what the model actually holds
// before a dialog opens instead of reading a regeneration failure afterwards.
//
// This header is pure C++: every curve point comes from an evaluator the caller
// supplies, so the sampling/refinement rules can be proven offline. panel_run.h
// plugs ProCurveXyzdataEval in. Nothing here guesses a curve's shape from its
// control points and nothing converts units: values stay in native units and the
// caller applies its measured scale.
//
// A pair is reported as:
//   * "crossing"              — a sampled local minimum is within tolerance;
//   * "no_sample_intersection"— the sampled minimum is farther than tolerance,
//                              which is NOT the claim "the curves do not cross";
//   * "unverified"            — a point evaluation failed or a curve was not
//                              sampled, with the raw code that stopped it.
// A zero distance is never written for a failed measurement.
#ifndef MECHDOG_PANEL_FIT_H
#define MECHDOG_PANEL_FIT_H

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <string>
#include <vector>

namespace mechdog_panel_fit {

//: BUG-120 task 2: a diagnostic tolerance, not a rule the kernel must satisfy. A
//: pair whose measured minimum is inside it is reported as a crossing; anything
//: farther is "no sample intersection" and stays unverified. The value is reported
//: with the result so a reader never mistakes it for a Creo regeneration threshold.
constexpr double DEFAULT_TOLERANCE_MM = 0.5;

//: Coarse grids seed the local search; the alternating refinement below makes the
//: final distance accurate instead of sample-spacing accurate.
constexpr int COARSE_SECTION_SAMPLES = 96;
constexpr int COARSE_GUIDE_SAMPLES = 192;
constexpr int REFINE_CANDIDATES = 3;
constexpr int REFINE_ITERATIONS = 20;
constexpr int REFINE_ALTERNATIONS = 2;

struct FitCurve {
    std::string role; // "section" or "guide"
    std::string label;
    int feature_id = 0;
    int curve_id = 0;
    //: Opaque handle for the caller's evaluator (the Toolkit adapter stores the
    //: curve id in a map instead; the standalone test stores analytic segments).
    const void *user_data = nullptr;
};

struct FitPoint {
    double t = 0.0;
    std::array<double, 3> p{0.0, 0.0, 0.0};
};

struct FitPair {
    std::size_t section_index = 0;
    std::size_t guide_index = 0;
    bool measured = false;
    double min_distance = std::numeric_limits<double>::quiet_NaN();
    double section_t = 0.0;
    double guide_t = 0.0;
    std::array<double, 3> section_point{0.0, 0.0, 0.0};
    std::array<double, 3> guide_point{0.0, 0.0, 0.0};
    //: Exact endpoint comparison (ProCurveXyzdataEval at 0.0/1.0), kept apart
    //: from the sampled interior minimum.
    bool endpoints_measured = false;
    double endpoint_min_distance = std::numeric_limits<double>::quiet_NaN();
    std::string endpoint_case;
    std::array<double, 3> endpoint_section{0.0, 0.0, 0.0};
    std::array<double, 3> endpoint_guide{0.0, 0.0, 0.0};
    std::string state = "unverified";
    std::string reason = "not sampled";
    int raw_code = 0;
};

struct FitOrder {
    std::size_t guide_index = 0;
    bool available = false;
    bool consistent = false;
    std::string direction = "unknown";
    std::vector<double> guide_parameters;
    std::vector<bool> crossing;
    std::string reason;
};

struct FitReport {
    std::vector<FitPair> pairs;
    std::vector<FitOrder> orders;
    std::size_t measured_pairs = 0;
    std::size_t crossing_pairs = 0;
    std::size_t unverified_pairs = 0;
    //: This version reports only. The route refuses on its own hard rules
    //: (missing feature, composite/closed curve, zero length) before this runs.
    bool blocking = false;
};

inline double distance3(const std::array<double, 3> &a, const std::array<double, 3> &b) {
    const double dx = a[0] - b[0];
    const double dy = a[1] - b[1];
    const double dz = a[2] - b[2];
    return std::sqrt(dx * dx + dy * dy + dz * dz);
}

//: Closest point on segment [a,b] to p; ``t`` is the segment parameter in [0,1].
inline double point_segment_distance(const std::array<double, 3> &p, const std::array<double, 3> &a,
                                     const std::array<double, 3> &b, double &t) {
    const std::array<double, 3> ab{b[0] - a[0], b[1] - a[1], b[2] - a[2]};
    const std::array<double, 3> ap{p[0] - a[0], p[1] - a[1], p[2] - a[2]};
    const double length2 = ab[0] * ab[0] + ab[1] * ab[1] + ab[2] * ab[2];
    if (!(length2 > 0.0)) {
        t = 0.0;
        return std::sqrt(ap[0] * ap[0] + ap[1] * ap[1] + ap[2] * ap[2]);
    }
    double ratio = (ap[0] * ab[0] + ap[1] * ab[1] + ap[2] * ab[2]) / length2;
    ratio = std::max(0.0, std::min(1.0, ratio));
    t = ratio;
    const std::array<double, 3> q{a[0] + ab[0] * ratio, a[1] + ab[1] * ratio, a[2] + ab[2] * ratio};
    return distance3(p, q);
}

//: Golden-section minimum of a unimodal bracket. The bracket is local, so the
//: caller keeps it narrow around the coarse candidate.
template <typename Fn>
inline double golden_minimize(Fn &&fn, double low, double high, int iterations,
                              double &best_value) {
    constexpr double INV_PHI = 0.6180339887498949;
    double a = low, b = high;
    double c = b - (b - a) * INV_PHI;
    double d = a + (b - a) * INV_PHI;
    double fc = fn(c), fd = fn(d);
    for (int step = 0; step < iterations; ++step) {
        if (fc < fd) {
            b = d;
            d = c;
            fd = fc;
            c = b - (b - a) * INV_PHI;
            fc = fn(c);
        } else {
            a = c;
            c = d;
            fc = fd;
            d = a + (b - a) * INV_PHI;
            fd = fn(d);
        }
    }
    if (fc < fd) {
        best_value = fc;
        return c;
    }
    best_value = fd;
    return d;
}

inline std::string endpoint_case_name(int section_end, int guide_end) {
    return std::string(section_end ? "section_end" : "section_start") + "-" +
           (guide_end ? "guide_end" : "guide_start");
}

//: Analyse one section against one guide. ``eval`` returns false when the SDK
//: cannot evaluate that parameter; the pair then stays unverified with the raw
//: code the caller stored for that curve.
template <typename Eval>
FitPair analyse_pair(const FitCurve &section, const FitCurve &guide, std::size_t section_index,
                     std::size_t guide_index, Eval &&eval, double tolerance, int section_code,
                     int guide_code) {
    FitPair pair;
    pair.section_index = section_index;
    pair.guide_index = guide_index;
    pair.raw_code = section_code ? section_code : guide_code;

    // Exact endpoint comparison first: it is a real ProCurveXyzdataEval result,
    // not a sample, and a coincident end does not imply an interior crossing.
    std::array<double, 3> section_ends[2];
    std::array<double, 3> guide_ends[2];
    const bool section_ends_ok =
        eval(section, 0.0, section_ends[0]) && eval(section, 1.0, section_ends[1]);
    const bool guide_ends_ok = eval(guide, 0.0, guide_ends[0]) && eval(guide, 1.0, guide_ends[1]);
    if (section_ends_ok && guide_ends_ok) {
        pair.endpoints_measured = true;
        pair.endpoint_min_distance = std::numeric_limits<double>::infinity();
        for (int s_end = 0; s_end < 2; ++s_end) {
            for (int g_end = 0; g_end < 2; ++g_end) {
                const double distance = distance3(section_ends[s_end], guide_ends[g_end]);
                if (distance < pair.endpoint_min_distance) {
                    pair.endpoint_min_distance = distance;
                    pair.endpoint_case = endpoint_case_name(s_end, g_end);
                    pair.endpoint_section = section_ends[s_end];
                    pair.endpoint_guide = guide_ends[g_end];
                }
            }
        }
    }

    // Coarse grid: section points against guide polyline segments.
    std::vector<FitPoint> guide_points;
    guide_points.reserve(COARSE_GUIDE_SAMPLES);
    for (int step = 0; step < COARSE_GUIDE_SAMPLES; ++step) {
        const double t = static_cast<double>(step) / (COARSE_GUIDE_SAMPLES - 1);
        FitPoint point{t, {0.0, 0.0, 0.0}};
        if (!eval(guide, t, point.p)) {
            pair.reason = "guide point evaluation failed";
            return pair;
        }
        guide_points.push_back(point);
    }
    struct Candidate {
        double distance;
        double section_t;
        double guide_t;
        std::array<double, 3> section_point;
        std::array<double, 3> guide_point;
    };
    std::vector<Candidate> candidates;
    for (int step = 0; step < COARSE_SECTION_SAMPLES; ++step) {
        const double t = static_cast<double>(step) / (COARSE_SECTION_SAMPLES - 1);
        std::array<double, 3> point{0.0, 0.0, 0.0};
        if (!eval(section, t, point)) {
            pair.reason = "section point evaluation failed";
            return pair;
        }
        for (std::size_t segment = 0; segment + 1 < guide_points.size(); ++segment) {
            double ratio = 0.0;
            const double distance = point_segment_distance(point, guide_points[segment].p,
                                                           guide_points[segment + 1].p, ratio);
            Candidate candidate{distance,
                                t,
                                guide_points[segment].t +
                                    ratio * (guide_points[segment + 1].t - guide_points[segment].t),
                                point,
                                {0.0, 0.0, 0.0}};
            for (int axis = 0; axis < 3; ++axis)
                candidate.guide_point[axis] =
                    guide_points[segment].p[axis] +
                    (guide_points[segment + 1].p[axis] - guide_points[segment].p[axis]) * ratio;
            candidates.push_back(candidate);
        }
    }
    if (candidates.empty())
        return pair;
    std::partial_sort(
        candidates.begin(),
        candidates.begin() + std::min<std::size_t>(REFINE_CANDIDATES, candidates.size()),
        candidates.end(),
        [](const Candidate &a, const Candidate &b) { return a.distance < b.distance; });
    const std::size_t refinable = std::min<std::size_t>(REFINE_CANDIDATES, candidates.size());

    double section_step = 1.0 / (COARSE_SECTION_SAMPLES - 1);
    double guide_step = 1.0 / (COARSE_GUIDE_SAMPLES - 1);
    for (std::size_t index = 0; index < refinable; ++index) {
        Candidate best = candidates[index];
        for (int round = 0; round < REFINE_ALTERNATIONS; ++round) {
            double value = 0.0;
            const double low_s = std::max(0.0, best.section_t - section_step);
            const double high_s = std::min(1.0, best.section_t + section_step);
            const double t_s = golden_minimize(
                [&](double t) {
                    std::array<double, 3> point{0.0, 0.0, 0.0};
                    if (!eval(section, t, point))
                        return std::numeric_limits<double>::infinity();
                    return distance3(point, best.guide_point);
                },
                low_s, high_s, REFINE_ITERATIONS, value);
            if (std::isfinite(value)) {
                std::array<double, 3> point{0.0, 0.0, 0.0};
                eval(section, t_s, point);
                best.section_t = t_s;
                best.section_point = point;
                best.distance = value;
            }
            const double low_g = std::max(0.0, best.guide_t - 2.0 * guide_step);
            const double high_g = std::min(1.0, best.guide_t + 2.0 * guide_step);
            const double t_g = golden_minimize(
                [&](double t) {
                    std::array<double, 3> point{0.0, 0.0, 0.0};
                    if (!eval(guide, t, point))
                        return std::numeric_limits<double>::infinity();
                    return distance3(point, best.section_point);
                },
                low_g, high_g, REFINE_ITERATIONS, value);
            if (std::isfinite(value)) {
                std::array<double, 3> point{0.0, 0.0, 0.0};
                eval(guide, t_g, point);
                best.guide_t = t_g;
                best.guide_point = point;
                best.distance = value;
            }
        }
        if (!pair.measured || best.distance < pair.min_distance) {
            pair.measured = true;
            pair.min_distance = best.distance;
            pair.section_t = best.section_t;
            pair.guide_t = best.guide_t;
            pair.section_point = best.section_point;
            pair.guide_point = best.guide_point;
        }
    }
    if (!pair.measured) {
        pair.reason = "local search produced no evaluable candidate";
        return pair;
    }
    if (pair.min_distance <= tolerance) {
        pair.state = "crossing";
        pair.reason.clear();
    } else {
        pair.state = "no_sample_intersection";
        pair.reason =
            "the sampled local minimum is farther than the stated tolerance; this is not the "
            "claim that the curves never cross";
    }
    return pair;
}

inline FitOrder analyse_order(const std::vector<FitPair> &pairs, std::size_t guide_index,
                              std::size_t section_count) {
    FitOrder order;
    order.guide_index = guide_index;
    order.guide_parameters.assign(section_count, 0.0);
    order.crossing.assign(section_count, false);
    for (const FitPair &pair : pairs) {
        if (pair.guide_index != guide_index || pair.section_index >= section_count)
            continue;
        order.guide_parameters[pair.section_index] = pair.guide_t;
        order.crossing[pair.section_index] = pair.state == "crossing";
    }
    for (std::size_t index = 0; index < section_count; ++index) {
        if (!order.crossing[index]) {
            order.available = false;
            order.reason = "not every section has a measured crossing for this guide";
            return order;
        }
    }
    order.available = true;
    bool increasing = true, decreasing = true;
    for (std::size_t index = 1; index < section_count; ++index) {
        if (!(order.guide_parameters[index] > order.guide_parameters[index - 1] + 1e-9))
            increasing = false;
        if (!(order.guide_parameters[index] < order.guide_parameters[index - 1] - 1e-9))
            decreasing = false;
    }
    order.consistent = increasing || decreasing;
    order.direction = increasing ? "forward" : decreasing ? "reverse" : "mixed";
    if (!order.consistent)
        order.reason = "the crossing parameter is not monotone along the guide";
    return order;
}

template <typename Eval>
FitReport analyse(const std::vector<FitCurve> &sections, const std::vector<FitCurve> &guides,
                  Eval &&eval, double tolerance, const std::vector<int> &section_codes,
                  const std::vector<int> &guide_codes) {
    FitReport report;
    for (std::size_t guide_index = 0; guide_index < guides.size(); ++guide_index) {
        for (std::size_t section_index = 0; section_index < sections.size(); ++section_index) {
            const int section_code =
                section_index < section_codes.size() ? section_codes[section_index] : 0;
            const int guide_code = guide_index < guide_codes.size() ? guide_codes[guide_index] : 0;
            FitPair pair = analyse_pair(sections[section_index], guides[guide_index], section_index,
                                        guide_index, eval, tolerance, section_code, guide_code);
            if (pair.state == "unverified")
                ++report.unverified_pairs;
            else {
                ++report.measured_pairs;
                if (pair.state == "crossing")
                    ++report.crossing_pairs;
            }
            report.pairs.push_back(pair);
        }
    }
    for (std::size_t guide_index = 0; guide_index < guides.size(); ++guide_index)
        report.orders.push_back(analyse_order(report.pairs, guide_index, sections.size()));
    return report;
}

} // namespace mechdog_panel_fit

#endif // MECHDOG_PANEL_FIT_H
