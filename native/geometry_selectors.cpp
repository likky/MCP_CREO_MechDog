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

static GeometrySelectorOutcome match_geometry_edge_selector(const J &selector, const J &state,
                                                            double mm_scale, double tolerance) {
    GeometrySelectorOutcome outcome;
    outcome.target = "edge";
    std::vector<int> matches;
    J matched = J::array();
    J nearest = J::array();
    int straight = 0;
    V expected[2] = {vec(selector.at("endpoints_mm").at(0)),
                     vec(selector.at("endpoints_mm").at(1))};
    for (const auto &edge : state.value("edges", J::array())) {
        if (!edge.contains("start") || !edge.contains("end"))
            continue; // arcs and undimensioned curves are not straight edges
        straight++;
        V first = scale(vec(edge["start"]), mm_scale);
        V second = scale(vec(edge["end"]), mm_scale);
        // Undirected: a straight edge has no meaningful start.
        double forward = std::max(selector_component_error(first, expected[0]),
                                  selector_component_error(second, expected[1]));
        double reverse = std::max(selector_component_error(second, expected[0]),
                                  selector_component_error(first, expected[1]));
        double error = std::min(forward, reverse);
        if (error > tolerance)
            continue;
        if (selector.contains("point_mm")) {
            V point = vec(selector["point_mm"]);
            if (selector_segment_distance(point, first, second) > tolerance)
                continue;
        }
        matches.push_back(edge["id"].get<int>());
        matched.push_back({{"id", edge["id"]}, {"endpoint_error_mm", error}});
    }
    if (matches.size() == 1) {
        outcome.matched = true;
        outcome.id = matches[0];
        outcome.diagnostic = {{"target", "edge"},
                              {"matched_geometry_id", matches[0]},
                              {"candidate_count", straight},
                              {"tolerance_mm", tolerance}};
        return outcome;
    }
    outcome.diagnostic = {{"target", "edge"},
                          {"coordinate_space", "model"},
                          {"tolerance_mm", tolerance},
                          {"candidate_count", straight},
                          {"matched_ids", J(matches)}};
    if (matches.empty()) {
        outcome.error =
            "geometry_selector edge endpoints matched none of the " + std::to_string(straight) +
            " straight model edges (tolerance_mm=" + std::to_string(tolerance) +
            "); re-read creo_inspect_model edges[].start/end and pass current coordinates, or "
            "use {kind:'edge',id:N}";
    } else {
        outcome.error = "geometry_selector edge endpoints matched " +
                        std::to_string(matches.size()) + " edges (ids " +
                        selector_id_list(matches) +
                        "); use a smaller tolerance_mm or endpoints that belong to exactly one "
                        "edge";
    }
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
