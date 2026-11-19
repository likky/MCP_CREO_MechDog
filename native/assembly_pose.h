#pragma once

#include <cmath>
#include <cstdio>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>

// Shared by the production assembly entries and the offline harness. Row-vector
// local-to-parent mapping; translation is the last row. Never repair input poses.
// BUG-045/FEAT-012: receipts publish this exact name beside the transform they
// read back from the kernel; it is the same mapping the input schema states.
inline const char *assembly_rotation_convention() {
    return "row_vectors_local_to_parent";
}

// BUG-045/FEAT-012: the published admission tolerance. Python mirrors this in
// ``creo_mechdog/rotation_admission.py``; both layers use the same numbers.
inline constexpr double assembly_admission_tolerance() {
    return 1e-6;
}

// Classification only: at or below this residual the matrix is "strict". It is
// not an admission limit and not a known Creo threshold.
inline constexpr double assembly_near_orthonormal_tolerance() {
    return 1e-9;
}

// BUG-133: the ceiling for an explicit rotation_tolerance. Beyond it the number
// no longer describes rounding and would admit a reflection (|det-1| = 2) or a
// scaled basis through the gate. Python mirrors this in rotation_admission.py.
inline constexpr double assembly_max_admission_tolerance() {
    return 1e-3;
}

inline std::string assembly_number_text(double value) {
    char buffer[32] = {};
    std::snprintf(buffer, sizeof buffer, "%.9g", value);
    return buffer;
}

inline std::string assembly_tolerance_text(double tolerance) {
    if (tolerance == assembly_admission_tolerance())
        return "1e-6";
    char buffer[32] = {};
    std::snprintf(buffer, sizeof buffer, "%g", tolerance);
    return buffer;
}

// BUG-133: the effective tolerance comes from the operation itself. Absent or
// null keeps the published default; a boolean, string, non-finite, non-positive
// or above-ceiling value is refused here so the native entry cannot accept what
// the Python entry refused (or the reverse).
template <typename Json> inline double assembly_tolerance_from_json(const Json &value) {
    if (value.is_null())
        return assembly_admission_tolerance();
    if (!value.is_number() || value.is_boolean())
        throw std::runtime_error("rotation_tolerance must be a positive finite number");
    const double tolerance = value.template get<double>();
    if (!std::isfinite(tolerance) || tolerance <= 0)
        throw std::runtime_error("rotation_tolerance must be a positive finite number");
    if (tolerance > assembly_max_admission_tolerance())
        throw std::runtime_error(
            "rotation_tolerance must be at most " +
            assembly_tolerance_text(assembly_max_admission_tolerance()) +
            "; a larger value stops describing a rounded matrix and would admit a reflection "
            "or a scaled basis");
    return tolerance;
}

// FEAT-012/T2: the caller's own matrix convention. Absent or null keeps the
// published row-vector reading; "column" is transposed exactly once, here, and
// is the only place the request array is converted.
template <typename Json> inline std::string assembly_input_convention(const Json &op) {
    if (!op.contains("rotation_convention") || op.at("rotation_convention").is_null())
        return "row";
    if (!op.at("rotation_convention").is_string())
        throw std::runtime_error("rotation_convention must be row or column");
    const std::string convention = op.at("rotation_convention").get<std::string>();
    if (convention != "row" && convention != "column")
        throw std::runtime_error("rotation_convention must be row or column");
    return convention;
}

template <typename Json> inline double assembly_effective_tolerance(const Json &op) {
    return assembly_tolerance_from_json(
        op.contains("rotation_tolerance") ? op.at("rotation_tolerance") : Json(nullptr));
}

struct AssemblyRotationAdmission {
    double orthogonality_residual = 0;
    double determinant = 1;
    bool accepted = true;
    bool near_orthonormal = false;
};

// Never repairs the input. A rejected matrix keeps its numbers so the caller
// can see the residual and the determinant instead of only the tolerance.
// BUG-133: the caller supplies the effective tolerance it already validated;
// the default stays the published 1e-6 for every existing call site.
template <typename Matrix>
inline AssemblyRotationAdmission assembly_rotation_admission(
    const Matrix &rotation, double tolerance = assembly_admission_tolerance()) {
    AssemblyRotationAdmission status;
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 3; ++j) {
            double dot = 0;
            for (int k = 0; k < 3; ++k)
                dot += rotation[i][k] * rotation[j][k];
            const double target = (i == j ? 1.0 : 0.0);
            if (!std::isfinite(dot)) {
                status.accepted = false;
                status.orthogonality_residual = std::numeric_limits<double>::infinity();
                return status;
            }
            const double error = std::abs(dot - target);
            if (error > status.orthogonality_residual)
                status.orthogonality_residual = error;
        }
    const auto &a = rotation[0], &b = rotation[1], &c = rotation[2];
    status.determinant = a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) +
                         a[2] * (b[0] * c[1] - b[1] * c[0]);
    status.accepted = std::isfinite(status.determinant) &&
                      status.orthogonality_residual <= tolerance &&
                      std::abs(status.determinant - 1.0) <= tolerance;
    status.near_orthonormal =
        status.accepted && status.orthogonality_residual > assembly_near_orthonormal_tolerance();
    return status;
}

template <typename Json> inline void assembly_rigid_transform(const Json &op, double matrix[4][4]) {
    auto vector3 = [](const Json &value) {
        if (!value.is_array() || value.size() != 3)
            throw std::runtime_error("Assembly pose requires a three-element vector");
        for (const auto &number : value)
            if (!number.is_number() || !std::isfinite(number.template get<double>()))
                throw std::runtime_error("Assembly pose requires finite real numbers");
    };
    const Json zero = Json::array({0, 0, 0});
    const auto &translation = op.contains("translation") ? op.at("translation") : zero;
    vector3(translation);
    const bool has_matrix = op.contains("rotation_matrix") && !op.at("rotation_matrix").is_null();
    const bool has_euler = op.contains("rotation") && !op.at("rotation").is_null();
    if (has_matrix && has_euler)
        throw std::runtime_error("rotation and rotation_matrix are mutually exclusive");
    const bool has_tolerance =
        op.contains("rotation_tolerance") && !op.at("rotation_tolerance").is_null();
    const bool has_convention =
        op.contains("rotation_convention") && !op.at("rotation_convention").is_null();
    const double tolerance =
        has_matrix ? assembly_effective_tolerance(op) : assembly_admission_tolerance();
    double rotation[3][3];
    if (has_matrix) {
        const auto &input = op.at("rotation_matrix");
        if (!input.is_array() || input.size() != 3)
            throw std::runtime_error("rotation_matrix must be a nested 3x3 array");
        for (int i = 0; i < 3; ++i) {
            vector3(input[i]);
            for (int j = 0; j < 3; ++j)
                rotation[i][j] = input[i][j].template get<double>();
        }
        // FEAT-012/T2: a column-vector input is transposed exactly once, here,
        // into the canonical row form used by the gate and the written matrix.
        if (assembly_input_convention(op) == "column")
            for (int i = 0; i < 3; ++i)
                for (int j = i + 1; j < 3; ++j)
                    std::swap(rotation[i][j], rotation[j][i]);
        const AssemblyRotationAdmission admission =
            assembly_rotation_admission(rotation, tolerance);
        const std::string within = assembly_tolerance_text(tolerance);
        if (!std::isfinite(admission.orthogonality_residual) ||
            admission.orthogonality_residual > tolerance)
            throw std::runtime_error(
                "rotation_matrix must be orthogonal within " + within +
                " (max |R*R^T-I| = " + assembly_number_text(admission.orthogonality_residual) +
                "); the input is echoed and never repaired, so supply exact orthonormal values, "
                "or pass an explicit rotation_tolerance to admit a documented rounded matrix");
        if (!std::isfinite(admission.determinant) ||
            std::abs(admission.determinant - 1) > tolerance)
            throw std::runtime_error(
                "rotation_matrix determinant must be +1 within " + within +
                " (det = " + assembly_number_text(admission.determinant) +
                "); the input is echoed and never repaired, so supply a right-handed "
                "orthonormal basis");
    } else {
        if (has_tolerance)
            throw std::runtime_error(
                "rotation_tolerance only applies to an explicit rotation_matrix; the Euler "
                "expansion is always admitted at the published 1e-6");
        if (has_convention)
            throw std::runtime_error(
                "rotation_convention only applies to an explicit rotation_matrix; the Euler "
                "expansion is always row-vector");
        const auto &euler = has_euler ? op.at("rotation") : zero;
        vector3(euler);
        const double radians = std::acos(-1.0) / 180;
        const double x = euler[0].template get<double>() * radians,
                     y = euler[1].template get<double>() * radians,
                     z = euler[2].template get<double>() * radians;
        const double cx = std::cos(x), sx = std::sin(x), cy = std::cos(y), sy = std::sin(y),
                     cz = std::cos(z), sz = std::sin(z);
        // Preserve the existing Euler transform exactly (transpose of Rz Ry Rx).
        const double column_rotation[3][3] = {
            {cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx},
            {sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx},
            {-sy, cy * sx, cy * cx}};
        for (int i = 0; i < 3; ++i)
            for (int j = 0; j < 3; ++j)
                rotation[i][j] = column_rotation[j][i];
    }
    // All input checks precede even writing the caller's matrix.
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j)
            matrix[i][j] = 0;
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 3; ++j)
            matrix[i][j] = rotation[i][j];
    for (int j = 0; j < 3; ++j)
        matrix[3][j] = translation[j].template get<double>();
    matrix[3][3] = 1;
}
