// DEV-089 T1: geometric anchor selectors resolved against the current model.
//
// Included by generic.cpp after inspection() and the vector helpers, so this
// translation unit owns the whole matching rule for {kind:'geometry_selector'}.
// The request shape is frozen by creo_mechdog.geometry_selectors; this file is
// the second line of defence and never guesses a candidate.
//
// Coordinates in the inspection record are model length units, so every
// comparison converts model -> millimetres with the executor's own measured
// scale. An unknown scale refuses the selector instead of assuming millimetres
// (BUG-080).

struct GeometrySelectorOutcome {
    bool matched = false;
    int id = -1;
    std::string target;
    J diagnostic = J::object();
    std::string error;
};

static double selector_component_error(const V &actual, const V &expected) {
    return std::max(std::max(fabs(actual[0] - expected[0]), fabs(actual[1] - expected[1])),
                    fabs(actual[2] - expected[2]));
}

static double selector_axis_distance(const V &point, const V &origin, const V &axis) {
    V offset = {point[0] - origin[0], point[1] - origin[1], point[2] - origin[2]};
    double along = dot(offset, axis);
    V perpendicular = {offset[0] - axis[0] * along, offset[1] - axis[1] * along,
                       offset[2] - axis[2] * along};
    return sqrt(dot(perpendicular, perpendicular));
}

static double selector_segment_distance(const V &point, const V &first, const V &second) {
    V direction = {second[0] - first[0], second[1] - first[1], second[2] - first[2]};
    double length_squared = dot(direction, direction);
    if (length_squared < 1e-18)
        return selector_component_error(point, first);
    V offset = {point[0] - first[0], point[1] - first[1], point[2] - first[2]};
    double t = dot(offset, direction) / length_squared;
    t = std::max(0.0, std::min(1.0, t));
    V nearest = {first[0] + direction[0] * t, first[1] + direction[1] * t,
                 first[2] + direction[2] * t};
    return sqrt(dot(V{point[0] - nearest[0], point[1] - nearest[1], point[2] - nearest[2]},
                    V{point[0] - nearest[0], point[1] - nearest[1], point[2] - nearest[2]}));
}

static std::string selector_id_list(const std::vector<int> &ids) {
    std::string text;
    for (int id : ids)
        text += (text.empty() ? "" : ", ") + std::to_string(id);
    return text;
}

static double selector_vector_norm(const V &value) {
    return sqrt(dot(value, value));
}

static V selector_cross(const V &first, const V &second) {
    return {first[1] * second[2] - first[2] * second[1],
            first[2] * second[0] - first[0] * second[2],
            first[0] * second[1] - first[1] * second[0]};
}

static std::string selector_edge_error(const std::string &form, const std::vector<int> &matches,
                                       int candidates, double tolerance) {
    if (matches.empty()) {
        std::string text = "geometry_selector edge " + form + " matched none of the " +
                           std::to_string(candidates) +
                           " eligible model edges (tolerance_mm=" + std::to_string(tolerance) + ")";
        if (form == "point_mm") {
            text += "; a single point only matches a finite straight edge - name a circular edge "
                    "with center_mm+radius_mm instead of its centre point";
        } else if (form == "circular") {
            text += "; re-read creo_inspect_model edges[].arc origin/radius and pass current "
                    "model coordinates";
        } else {
            text += "; re-read creo_inspect_model edges[].start/end and pass current "
                    "coordinates, or use {kind:'edge',id:N}";
        }
        return text;
    }
    return "geometry_selector edge " + form + " matched " + std::to_string(matches.size()) +
           " edges (ids " + selector_id_list(matches) +
           "); use a smaller tolerance_mm or an anchor that belongs to exactly one edge";
}

static GeometrySelectorOutcome match_geometry_edge_selector(const J &selector, const J &state,
                                                            double mm_scale, double tolerance) {
    GeometrySelectorOutcome outcome;
    outcome.target = "edge";
    const bool circular = selector.contains("center_mm") || selector.contains("radius_mm");
    std::string form = circular                            ? "circular"
                       : selector.contains("endpoints_mm") ? "endpoints"
                                                           : "point_mm";
    std::vector<int> matches;
    J matched = J::array();
    int candidates = 0;
    if (circular) {
        V center = vec(selector["center_mm"]);
        const double radius = selector["radius_mm"].get<double>();
        const bool filter_axis = selector.contains("axis");
        const double axis_tolerance = selector.value("axis_tolerance_deg", 0.5);
        const double cosine_limit = std::cos(axis_tolerance * 3.14159265358979323846 / 180.0);
        const V requested = filter_axis ? normalized(vec(selector["axis"])) : V{0, 0, 0};
        for (const auto &edge : state.value("edges", J::array())) {
            if (!edge.contains("arc"))
                continue; // only measured circular edges are eligible
            candidates++;
            const J &arc = edge["arc"];
            V arc_center = scale(vec(arc["origin"]), mm_scale);
            const double arc_radius = arc["radius"].get<double>() * mm_scale;
            if (fabs(arc_radius - radius) > tolerance)
                continue;
            if (selector_component_error(arc_center, center) > tolerance)
                continue;
            if (filter_axis) {
                V arc_axis = selector_cross(vec(arc["v1"]), vec(arc["v2"]));
                const double axis_length = selector_vector_norm(arc_axis);
                if (axis_length <= 1e-9)
                    continue; // no measured plane normal, so no axis filter can pass
                arc_axis = scale(arc_axis, 1.0 / axis_length);
                if (fabs(dot(arc_axis, requested)) < cosine_limit)
                    continue;
            }
            if (selector.contains("point_mm")) {
                // FEAT-068 A0: a full rim is often split into two arcs with the
                // same centre and radius. The point selects the piece whose
                // measured angular span contains it; it must lie on the circle.
                V arc_v1 = normalized(vec(arc["v1"]));
                V arc_v2 = normalized(vec(arc["v2"]));
                V normal = selector_cross(arc_v1, arc_v2);
                const double normal_length = selector_vector_norm(normal);
                if (normal_length <= 1e-9)
                    continue;
                normal = scale(normal, 1.0 / normal_length);
                V point = vec(selector["point_mm"]);
                V radial = {point[0] - arc_center[0], point[1] - arc_center[1],
                            point[2] - arc_center[2]};
                if (fabs(dot(radial, normal)) > tolerance)
                    continue;
                if (fabs(selector_vector_norm(radial) - radius) > tolerance)
                    continue;
                const double two_pi = 2.0 * 3.14159265358979323846;
                const double start_angle = arc["start_angle"].get<double>();
                const double raw_span = arc["end_angle"].get<double>() - start_angle;
                if (raw_span < two_pi - 1e-6) {
                    double span = raw_span;
                    if (span < 0)
                        span += two_pi;
                    double offset =
                        std::atan2(dot(radial, arc_v2), dot(radial, arc_v1)) - start_angle;
                    offset = std::fmod(offset, two_pi);
                    if (offset < 0)
                        offset += two_pi;
                    const double angular_tolerance = tolerance / std::max(radius, 1e-9) + 1e-6;
                    if (offset > span + angular_tolerance)
                        continue;
                }
            }
            matches.push_back(edge["id"].get<int>());
            matched.push_back({{"id", edge["id"]},
                               {"radius_mm", arc_radius},
                               {"center_error_mm", selector_component_error(arc_center, center)}});
        }
    } else {
        V expected[2] = {vec(selector.contains("endpoints_mm") ? selector.at("endpoints_mm").at(0)
                                                               : selector.at("point_mm")),
                         V{0, 0, 0}};
        if (selector.contains("endpoints_mm"))
            expected[1] = vec(selector.at("endpoints_mm").at(1));
        for (const auto &edge : state.value("edges", J::array())) {
            if (!edge.contains("start") || !edge.contains("end"))
                continue; // arcs and undimensioned curves are not straight edges
            candidates++;
            V first = scale(vec(edge["start"]), mm_scale);
            V second = scale(vec(edge["end"]), mm_scale);
            double error = 0;
            if (selector.contains("endpoints_mm")) {
                // Undirected: a straight edge has no meaningful start.
                double forward = std::max(selector_component_error(first, expected[0]),
                                          selector_component_error(second, expected[1]));
                double reverse = std::max(selector_component_error(second, expected[0]),
                                          selector_component_error(first, expected[1]));
                error = std::min(forward, reverse);
                if (error > tolerance)
                    continue;
                if (selector.contains("point_mm")) {
                    V point = vec(selector["point_mm"]);
                    if (selector_segment_distance(point, first, second) > tolerance)
                        continue;
                }
            } else {
                // FEAT-068 A0: one point on one finite straight edge. The
                // distance is measured to the segment, never to its infinite
                // line, so a point beyond an endpoint cannot match.
                error = selector_segment_distance(expected[0], first, second);
                if (error > tolerance)
                    continue;
            }
            matches.push_back(edge["id"].get<int>());
            matched.push_back({{"id", edge["id"]}, {"anchor_error_mm", error}});
        }
    }
    if (matches.size() == 1) {
        outcome.matched = true;
        outcome.id = matches[0];
        outcome.diagnostic = {{"target", "edge"},
                              {"form", form},
                              {"matched_geometry_id", matches[0]},
                              {"candidate_count", candidates},
                              {"tolerance_mm", tolerance}};
        return outcome;
    }
    outcome.diagnostic = {{"target", "edge"},
                          {"form", form},
                          {"coordinate_space", "model"},
                          {"tolerance_mm", tolerance},
                          {"candidate_count", candidates},
                          {"matched_ids", J(matches)}};
    outcome.error = selector_edge_error(form, matches, candidates, tolerance);
    return outcome;
}

static GeometrySelectorOutcome match_geometry_surface_selector(const J &selector, const J &state,
                                                               double mm_scale, double tolerance) {
    GeometrySelectorOutcome outcome;
    outcome.target = "surface";
    const double axis_tolerance = selector.value("axis_tolerance_deg", 0.5);
    const double cosine_limit = std::cos(axis_tolerance * 3.14159265358979323846 / 180.0);
    std::vector<int> matches;
    int eligible = 0;
    for (const auto &surface : state.value("surfaces", J::array())) {
        int type = surface.value("type", -1);
        const bool plane = type == PRO_SRF_PLANE;
        const bool cylinder = type == PRO_SRF_CYL;
        if (!plane && !cylinder)
            continue;
        eligible++;
        V axis = {0, 0, 0};
        bool has_axis = false;
        if (plane && surface.contains("normal")) {
            axis = normalized(vec(surface["normal"]));
            has_axis = true;
        }
        if (cylinder && surface.contains("axis")) {
            axis = normalized(vec(surface["axis"]));
            has_axis = true;
        }
        // Normal/axis direction is compared sign-insensitively: the same planar
        // face reports opposite normals depending on which body is queried.
        if (selector.contains("axis")) {
            if (!has_axis)
                continue;
            V requested = normalized(vec(selector["axis"]));
            if (fabs(dot(axis, requested)) < cosine_limit)
                continue;
        }
        if (selector.contains("radius_mm")) {
            if (!cylinder || !surface.contains("radius"))
                continue;
            if (fabs(surface["radius"].get<double>() * mm_scale -
                     selector["radius_mm"].get<double>()) > tolerance)
                continue;
        }
        V origin =
            surface.contains("origin") ? scale(vec(surface["origin"]), mm_scale) : V{0, 0, 0};
        if (selector.contains("center_mm")) {
            // The cylinder's parameter origin is not unique along its axis, so
            // only the perpendicular distance to the axis line is meaningful.
            if (!cylinder || !has_axis)
                continue;
            if (selector_axis_distance(vec(selector["center_mm"]), origin, axis) > tolerance)
                continue;
        }
        if (selector.contains("points_mm")) {
            bool all_on_surface = true;
            for (const auto &item : selector["points_mm"]) {
                V point = vec(item);
                double offset = 0;
                if (plane) {
                    offset = fabs(dot(
                        V{point[0] - origin[0], point[1] - origin[1], point[2] - origin[2]}, axis));
                } else if (has_axis && surface.contains("radius")) {
                    offset = fabs(selector_axis_distance(point, origin, axis) -
                                  surface["radius"].get<double>() * mm_scale);
                } else {
                    all_on_surface = false;
                    break;
                }
                if (offset > tolerance) {
                    all_on_surface = false;
                    break;
                }
                // A coaxial cylinder is often reported as several pieces (and a
                // large plane can also be split); the infinite-surface offset is
                // identical for all of them. Require the point to be inside the
                // reported piece's own bounding box so one anchor names one piece.
                if (surface.contains("bbox") && surface["bbox"].is_array() &&
                    surface["bbox"].size() == 2) {
                    V low = scale(vec(surface["bbox"][0]), mm_scale);
                    V high = scale(vec(surface["bbox"][1]), mm_scale);
                    for (int axis = 0; axis < 3; axis++)
                        if (point[axis] < low[axis] - tolerance ||
                            point[axis] > high[axis] + tolerance) {
                            all_on_surface = false;
                            break;
                        }
                }
                if (!all_on_surface)
                    break;
            }
            if (!all_on_surface)
                continue;
        }
        matches.push_back(surface["id"].get<int>());
    }
    if (matches.size() == 1) {
        outcome.matched = true;
        outcome.id = matches[0];
        outcome.diagnostic = {{"target", "surface"},
                              {"matched_geometry_id", matches[0]},
                              {"candidate_count", eligible},
                              {"tolerance_mm", tolerance}};
        return outcome;
    }
    outcome.diagnostic = {{"target", "surface"},
                          {"coordinate_space", "model"},
                          {"tolerance_mm", tolerance},
                          {"candidate_count", eligible},
                          {"matched_ids", J(matches)}};
    if (matches.empty()) {
        outcome.error =
            "geometry_selector surface filters matched none of the " + std::to_string(eligible) +
            " planar/cylindrical model faces (tolerance_mm=" + std::to_string(tolerance) +
            ", axis_tolerance_deg=" + std::to_string(axis_tolerance) +
            "); re-read creo_inspect_model surfaces[] and pass current normal/origin/radius, or "
            "use {kind:'surface',id:N}";
    } else {
        outcome.error = "geometry_selector surface filters matched " +
                        std::to_string(matches.size()) + " faces (ids " +
                        selector_id_list(matches) +
                        "); add points_mm/radius_mm/start-or-endpoints that belong to exactly "
                        "one face, or use an explicit id";
    }
    return outcome;
}

// DEV-089 T1 assembly occurrences: a selector written in root-assembly
// coordinates is mapped into the component's own model frame with the inverse of
// the occurrence placement. ProMatrix rows are the local axes expressed in the
// parent frame and row 3 is the origin, so:
//   p_local = (p_assembly - origin) . row[axis]     for each axis row
// A direction only rotates. Nothing here assumes an identity placement.
static J occurrence_point_to_model(const J &item, const ProMatrix &position) {
    const double offset[3] = {item.at(0).get<double>() - position[3][0],
                              item.at(1).get<double>() - position[3][1],
                              item.at(2).get<double>() - position[3][2]};
    J result = J::array();
    for (int row = 0; row < 3; row++)
        result.push_back(offset[0] * position[row][0] + offset[1] * position[row][1] +
                         offset[2] * position[row][2]);
    return result;
}

static J occurrence_vector_to_model(const J &item, const ProMatrix &position) {
    const double vector[3] = {item.at(0).get<double>(), item.at(1).get<double>(),
                              item.at(2).get<double>()};
    double local[3] = {0, 0, 0};
    for (int row = 0; row < 3; row++)
        local[row] = vector[0] * position[row][0] + vector[1] * position[row][1] +
                     vector[2] * position[row][2];
    const double length =
        std::sqrt(local[0] * local[0] + local[1] * local[1] + local[2] * local[2]);
    if (length <= 1e-12)
        throw std::runtime_error(
            "geometry_selector axis became degenerate while mapping assembly coordinates into "
            "the component frame; check the occurrence placement");
    J result = J::array();
    for (double value : local)
        result.push_back(value / length);
    return result;
}

static J selector_to_component_model(const J &selector, const ProMatrix &position) {
    J mapped = selector;
    for (const char *key : {"endpoints_mm", "points_mm"}) {
        if (!selector.contains(key))
            continue;
        J points = J::array();
        for (const auto &item : selector[key])
            points.push_back(occurrence_point_to_model(item, position));
        mapped[key] = points;
    }
    for (const char *key : {"point_mm", "center_mm"})
        if (selector.contains(key))
            mapped[key] = occurrence_point_to_model(selector[key], position);
    if (selector.contains("axis"))
        mapped["axis"] = occurrence_vector_to_model(selector["axis"], position);
    mapped["coordinate_space"] = "model";
    return mapped;
}

static GeometrySelectorOutcome match_geometry_selector(const J &selector, const J &state,
                                                       double mm_scale) {
    const std::string target = selector.at("target").get<std::string>();
    const double tolerance = selector.at("tolerance_mm").get<double>();
    if (target == "edge")
        return match_geometry_edge_selector(selector, state, mm_scale, tolerance);
    if (target == "surface")
        return match_geometry_surface_selector(selector, state, mm_scale, tolerance);
    GeometrySelectorOutcome outcome;
    outcome.error = "geometry_selector target must be 'edge' or 'surface', not '" + target + "'";
    return outcome;
}
