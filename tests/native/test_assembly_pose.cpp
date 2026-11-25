#include "assembly_pose.h"
#include "constraint_placement.h"
#include "third_party/json.hpp"

#include <cassert>
#include <cstdio>
#include <limits>

using J = nlohmann::json;

static void close(double actual, double expected) {
    assert(std::abs(actual - expected) < 1e-12);
}

static void pose(const J &euler, const J &rows, const J &point_expected) {
    const J translation = {7, -8, 9};
    double from_euler[4][4], from_matrix[4][4];
    assembly_rigid_transform(J{{"rotation", euler}, {"translation", translation}}, from_euler);
    assembly_rigid_transform(J{{"rotation_matrix", rows}, {"translation", translation}},
                             from_matrix);
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j) {
            close(from_euler[i][j], from_matrix[i][j]);
            if (i < 3 && j < 3)
                close(from_matrix[i][j], rows[i][j]);
        }
    // Each basis vector maps to the corresponding supplied row, plus offset.
    for (int basis = 0; basis < 3; ++basis)
        for (int j = 0; j < 3; ++j)
            close(from_matrix[basis][j] + from_matrix[3][j],
                  rows[basis][j].get<double>() + translation[j].get<double>());
    const double point[] = {2, 3, 5};
    double mapped[3];
    for (int j = 0; j < 3; ++j) {
        mapped[j] = from_matrix[3][j];
        for (int k = 0; k < 3; ++k)
            mapped[j] += point[k] * from_matrix[k][j];
        close(mapped[j], point_expected[j].get<double>() + translation[j].get<double>());
    }
    // Inverse mapping uses the transpose for orthogonal rotations only.
    for (int j = 0; j < 3; ++j) {
        double inverse = 0;
        for (int k = 0; k < 3; ++k)
            inverse += (mapped[k] - from_matrix[3][k]) * from_matrix[j][k];
        close(inverse, point[j]);
    }
    close(from_matrix[3][3], 1);
}

static void rejected(const J &op) {
    double matrix[4][4];
    for (auto &row : matrix)
        for (auto &number : row)
            number = 123;
    bool refused = false;
    try {
        assembly_rigid_transform(op, matrix);
    } catch (const std::exception &) {
        refused = true;
    }
    assert(refused);
    for (auto &row : matrix)
        for (double number : row)
            assert(number == 123); // checks precede output mutation
}

static void constraint_placement_residuals() {
    using namespace mechdog_constraints;
    const PlacementPlane top{{0, 0, 0}, {0, 0, 1}};
    const PlacementPlane opposing{{0, 0, 0}, {0, 0, -1}};
    assert(plane_residual(top, opposing, true, 0).matches());
    close(plane_residual(top, top, true, 0).angle_deg, 180);
    assert(plane_residual(top, top, false, 0).matches());

    // The initial placement reported in BUG-036 violates a zero-offset align
    // on both the normal and the position, even when the kernel says solved.
    const PlacementPlane right{{0, 0, 0}, {1, 0, 0}};
    const PlacementPlane stale{{-30, 20, 0}, {std::sqrt(3.0) / 2, 0.5, 0}};
    const auto residual = plane_residual(right, stale, false, 0);
    close(residual.distance_mm, -30);
    close(residual.angle_deg, 30);
    assert(!residual.matches());

    const PlacementPlane shifted{{40, -90, -5}, {0, 0, -1}};
    assert(plane_residual(top, shifted, true, -5).matches()); // sliding in the plane is legal
    assert(!plane_residual(top, shifted, true, 5).matches());
    const PlacementPlane red_datum{{0, 0, 0}, {0, 0, -1}, -1};
    const PlacementPlane same_facing{{0, 0, 5}, {0, 0, -1}};
    const PlacementPlane opposite_facing{{0, 0, 5}, {0, 0, 1}};
    assert(plane_residual(red_datum, same_facing, false, 5).matches());
    assert(plane_residual(red_datum, opposite_facing, true, 5).matches());
    const PlacementPlane nearly{{0, 0, 0.0009}, {0, 0, 1}};
    assert(plane_residual(top, nearly, false, 0).matches());
    const PlacementPlane unreadable{{0, 0, std::numeric_limits<double>::quiet_NaN()}, {0, 0, 1}};
    assert(!plane_residual(top, unreadable, false, 0).known());
}

int main() {
    constraint_placement_residuals();
    const J identity = {{1, 0, 0}, {0, 1, 0}, {0, 0, 1}};
    pose({0, 0, 0}, identity, {2, 3, 5});
    pose({90, 0, 0}, {{1, 0, 0}, {0, 0, 1}, {0, -1, 0}}, {2, -5, 3});
    pose({-90, 0, 0}, {{1, 0, 0}, {0, 0, -1}, {0, 1, 0}}, {2, 5, -3});
    pose({0, 90, 0}, {{0, 0, -1}, {0, 1, 0}, {1, 0, 0}}, {5, 3, -2});
    pose({0, -90, 0}, {{0, 0, 1}, {0, 1, 0}, {-1, 0, 0}}, {-5, 3, 2});
    pose({0, 0, 90}, {{0, 1, 0}, {-1, 0, 0}, {0, 0, 1}}, {-3, 2, 5});
    pose({0, 0, -90}, {{0, -1, 0}, {1, 0, 0}, {0, 0, 1}}, {3, -2, 5});
    pose({90, 0, 90}, {{0, 1, 0}, {0, 0, 1}, {1, 0, 0}}, {5, 2, 3});
    pose({90, 90, 90}, {{0, 0, -1}, {0, 1, 0}, {1, 0, 0}}, {5, 3, -2});
    pose({90, -90, 90}, {{0, 0, 1}, {0, -1, 0}, {1, 0, 0}}, {5, -3, 2});
    const double h = std::sqrt(3.0) / 2;
    pose({30, 90, 60}, {{0, 0, -1}, {-0.5, h, 0}, {h, 0.5, 0}}, {-1.5 + 5 * h, 3 * h + 2.5, -2});

    double matrix[4][4];
    assembly_rigid_transform(J::object(), matrix);
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j)
            close(matrix[i][j], i == j ? 1 : 0);
    J near = identity;
    near[0][0] = 1 + 4e-8;
    assembly_rigid_transform(J{{"rotation_matrix", near}}, matrix);
    assert(matrix[0][0] == near[0][0].get<double>()); // no reorthogonalization
    rejected({{"rotation", {0, 0, 0}}, {"rotation_matrix", identity}});
    for (const J &invalid : J::array({J::array(), J::array({1, 0, 0, 0, 1, 0, 0, 0, 1}),
                                      J::array({{1, 0}, {0, 1}, {0, 0}}),
                                      J::array({{1, 0, 0}, {0, 1, 0}}), J("identity")}))
        rejected({{"rotation_matrix", invalid}});
    for (const J &number : J::array({J(true), J("1"), J(nullptr), J(2), J(-1), J(1 + 1e-6),
                                     J(1e308), J(std::numeric_limits<double>::infinity()),
                                     J(std::numeric_limits<double>::quiet_NaN())})) {
        J invalid = identity;
        invalid[0][0] = number;
        rejected({{"rotation_matrix", invalid}});
    }
    J skew = identity;
    skew[0][1] = 1e-4;
    rejected({{"rotation_matrix", skew}});
    J scaled = identity;
    for (int i = 0; i < 3; ++i)
        scaled[i][i] = 1 + 4e-8; // Gram passes, determinant alone exceeds tolerance
    rejected({{"rotation_matrix", scaled}});
    rejected({{"rotation_matrix", identity}, {"translation", {0, true, 0}}});
    rejected({{"rotation", {0, 0}}});
    rejected({{"rotation", {0, std::numeric_limits<double>::infinity(), 0}}});

    // BUG-045/FEAT-012/BUG-133: the reported I032 pose is above the measured
    // 1e-7 boundary (residual 2.24085e-7), and the exact 30-degree pose is strict.
    const double i032[3][3] = {{0, 0.307383, -0.951586}, {0, 0.951586, 0.307383}, {1, 0, 0}};
    const AssemblyRotationAdmission i032_status = assembly_rotation_admission(i032);
    assert(!i032_status.accepted);
    assert(!i032_status.near_orthonormal);
    close(i032_status.orthogonality_residual, 2.2408500011117383e-7);
    close(i032_status.determinant - 1, 2.2408500011117383e-7);
    const double thirty[3][3] = {
        {0.8660254037844387, 0.5, 0}, {-0.5, 0.8660254037844387, 0}, {0, 0, 1}};
    const AssemblyRotationAdmission thirty_status = assembly_rotation_admission(thirty);
    assert(thirty_status.accepted && !thirty_status.near_orthonormal);
    assert(thirty_status.orthogonality_residual == 0);
    assert(thirty_status.determinant == 1);
    // BUG-133: the synthetic 28-degree pose at seven decimals is inside the
    // measured boundary (max |R*R^T-I| = 4.755232e-8) and is echoed verbatim.
    const J rounded7 = {{0.8829476, 0.4694716, 0}, {-0.4694716, 0.8829476, 0}, {0, 0, 1}};
    assembly_rigid_transform(J{{"rotation_matrix", rounded7}}, matrix);
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 3; ++j)
            assert(matrix[i][j] == rounded7[i][j].get<double>()); // echoed, never repaired
    // The six-decimal form (1.129488e-6) is refused, and the ceiling cannot be
    // raised: 1e-7 is the largest accepted rotation_tolerance.
    const J rounded = {{0.882948, 0.469472, 0}, {-0.469472, 0.882948, 0}, {0, 0, 1}};
    rejected({{"rotation_matrix", rounded}});
    rejected({{"rotation_matrix", rounded}, {"rotation_tolerance", 1e-5}});
    // An effective tolerance below the residual still refuses the matrix.
    rejected({{"rotation_matrix", rounded}, {"rotation_tolerance", 1e-7}});
    // BUG-133: the ceiling keeps an explicit tolerance from admitting a
    // reflection (|det-1| = 2) or a scaled basis through the gate.
    rejected({{"rotation_matrix", rounded}, {"rotation_tolerance", 1e-7 + 1e-12}});
    rejected({{"rotation_matrix", rounded}, {"rotation_tolerance", 1.0}});
    rejected({{"rotation_matrix", {{1, 0, 0}, {0, 1, 0}, {0, 0, -1}}},
              {"rotation_tolerance", 1.0}});
    for (const J &bad : J::array({J(true), J("1e-5"), J(0), J(-1e-5), J(1e308),
                                  J(std::numeric_limits<double>::infinity()),
                                  J(std::numeric_limits<double>::quiet_NaN())}))
        rejected({{"rotation_matrix", rounded}, {"rotation_tolerance", bad}});
    // The ceiling itself is admissible and the near-orthonormal matrix is echoed.
    assembly_rigid_transform(J{{"rotation_matrix", rounded7}, {"rotation_tolerance", 1e-7}},
                             matrix);
    assert(matrix[0][0] == rounded7[0][0].get<double>());

    // FEAT-012/T2: an explicit column-vector input is transposed exactly once.
    // 90 degrees about Z, column reading: p_parent = R * p_local + T.
    const J column = {{0, -1, 0}, {1, 0, 0}, {0, 0, 1}};
    assembly_rigid_transform(
        J{{"rotation_matrix", column}, {"rotation_convention", "column"},
          {"translation", {7, -8, 9}}},
        matrix);
    assert(matrix[0][0] == 0 && matrix[0][1] == 1 && matrix[1][0] == -1);
    const double column_point[] = {2, 3, 5};
    double mapped[3];
    for (int j = 0; j < 3; ++j) {
        mapped[j] = matrix[3][j];
        for (int k = 0; k < 3; ++k)
            mapped[j] += column_point[k] * matrix[k][j];
    }
    close(mapped[0], 4);
    close(mapped[1], -6);
    close(mapped[2], 14);
    // The same array without a convention keeps the published row reading.
    assembly_rigid_transform(J{{"rotation_matrix", column}, {"translation", {7, -8, 9}}},
                             matrix);
    assert(matrix[0][1] == -1 && matrix[1][0] == 1);
    // Convention is refused where it cannot apply or names something else.
    rejected({{"rotation_matrix", column}, {"rotation_convention", "euler"}});
    rejected({{"rotation_matrix", column}, {"rotation_convention", true}});
    rejected({{"rotation", {0, 0, 90}}, {"rotation_convention", "column"}});
    rejected({{"rotation_convention", "column"}});
    // A marginal six-decimal column matrix is measured in its canonical row
    // form; its 1.023309e-6 residual is above the measured boundary, so no
    // permitted tolerance admits it.
    const J marginal_column = {{0.965337, -0.258191, 0.038222},
                               {0.258661, 0.965936, -0.007826},
                               {-0.034899, 0.017442, 0.999239}};
    rejected({{"rotation_matrix", marginal_column}, {"rotation_convention", "column"}});
    rejected({{"rotation_matrix", marginal_column},
              {"rotation_convention", "column"},
              {"rotation_tolerance", 1e-7}});
    std::puts("assembly_pose: 11 Euler/matrix poses, basis/known-point/inverse maps, defaults, "
              "tolerance preservation, I032 refusal/30-degree admission, BUG-133 measured 1e-7 "
              "boundary and invalid-input checks passed; no Toolkit connection");
}
