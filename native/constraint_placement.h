#pragma once

#include <array>
#include <cmath>

namespace mechdog_constraints {

constexpr double plane_distance_tolerance_mm = 0.001;
constexpr double plane_angle_tolerance_deg = 0.01;

struct PlacementPlane {
    std::array<double, 3> origin;
    std::array<double, 3> normal;
    double offset_axis_sign = 1.0;
};

struct PlaneResidual {
    double distance_mm;
    double angle_deg;

    bool known() const {
        return std::isfinite(distance_mm) && std::isfinite(angle_deg);
    }
    bool matches() const {
        return known() && std::abs(distance_mm) <= plane_distance_tolerance_mm &&
               angle_deg <= plane_angle_tolerance_deg;
    }
};

// The caller supplies unit normals in the owning assembly's physical frame.
// A mate faces the other plane. Align points in the same direction.
inline PlaneResidual plane_residual(const PlacementPlane &assembly, const PlacementPlane &component,
                                    bool mate, double expected_gap_mm) {
    double gap = 0;
    double cosine = 0;
    const auto &a = assembly.normal;
    const auto &b = component.normal;
    for (int i = 0; i < 3; ++i) {
        gap += (component.origin[i] - assembly.origin[i]) * a[i];
        cosine += a[i] * b[i];
    }
    const double sine =
        std::hypot(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]);
    return {gap * assembly.offset_axis_sign - expected_gap_mm,
            std::atan2(sine, mate ? -cosine : cosine) * 180.0 / std::acos(-1.0)};
}

} // namespace mechdog_constraints
