// DEV-089 T6b: native direction (linear) pattern.
//
// Tree basis: ProPattern.h "Dir Pattern" (PRO_E_GENPAT_DIR with
// PRO_E_DIR_PAT_DIR1_OPT = PRO_GENPAT_TRANSLATIONAL,
// PRO_E_GENPAT_DIR1 -> PRO_E_DIRECTION_COMPOUND -> PRO_E_DIRECTION_REFERENCE,
// PRO_E_DIR_PAT_DIR1_FLIP, PRO_E_GENPAT_DIR1_INC) and
// PRO_E_GENPAT_DIM_FIRST_DIR_NUM_INST, created with ProPatternCreate exactly
// like the existing axis pattern. The published request is a unit vector in
// model coordinates; Creo still needs a real direction reference, so the vector
// is bound to the first straight edge parallel to it (ascending id), then to the
// first planar face whose normal is parallel. The reference's own direction is
// read back, so `flip` reverses the pattern instead of relying on an assumed
// edge orientation. No reference is invented and no duplicate geometry is
// created: the feature count and member ids come from ProPatternMembersGet.

struct LinearPatternDirection {
    bool found = false;
    ProSelection selection = nullptr;
    V direction = {0, 0, 0};
    std::string source;
    int id = -1;
    int candidate_count = 0;
};

static std::string linear_pattern_leader_kind(ProFeattype t) {
    if (t == PRO_FEAT_CURVE)
        return "sketch_or_curve";
    if (t == PRO_FEAT_DATUM)
        return "datum_plane";
    if (t == PRO_FEAT_DATUM_AXIS)
        return "datum_axis";
    if (t == PRO_FEAT_DATUM_POINT)
        return "datum_point";
    if (t == PRO_FEAT_CSYS)
        return "datum_csys";
    if (t == PRO_FEAT_GROUP_HEAD)
        return "feature_group";
    if (t == PRO_FEAT_PATTERN_HEAD)
        return "pattern_head";
    if (t == PRO_FEAT_PROTRUSION || t == PRO_FEAT_FIRST_FEAT)
        return "protrusion";
    if (t == PRO_FEAT_CUT)
        return "cut";
    if (t == PRO_FEAT_HOLE)
        return "hole";
    if (t == PRO_FEAT_ROUND)
        return "round";
    if (t == PRO_FEAT_CHAMFER)
        return "chamfer";
    if (t == PRO_FEAT_SHELL)
        return "shell";
    if (t == PRO_FEAT_RIB)
        return "rib";
    if (t == PRO_FEAT_DRAFT)
        return "draft";
    if (t == PRO_FEAT_DATUM_SURF)
        return "surface";
    return type_name((int)t);
}

static bool is_non_solid_pattern_leader(ProFeattype t) {
    return t == PRO_FEAT_CURVE || t == PRO_FEAT_DATUM || t == PRO_FEAT_DATUM_AXIS ||
           t == PRO_FEAT_DATUM_POINT || t == PRO_FEAT_CSYS;
}

static bool is_solid_alias_op(const std::string &op_name) {
    return op_name == "extrude" || op_name == "revolve" || op_name == "hole" ||
           op_name == "round" || op_name == "chamfer" || op_name == "shell" || op_name == "sweep" ||
           op_name == "loft" || op_name == "rib" || op_name == "draft" || op_name == "mirror" ||
           op_name == "feature_group" || op_name == "sheetmetal_wall" ||
           op_name == "sheetmetal_planar_wall" || op_name == "sheetmetal_flange";
}

// BUG-169: measure how many PRO_SURFACE geomitems a pattern leader owns so a
// sketch/datum or zero-geometry feature cannot silently pattern with dV=0.
// For a local feature group, sum owned surfaces across its member features.
static int count_leader_surfaces(ProFeature &leader, bool group, ProError &query_code) {
    if (!group) {
        J surface_ids = J::array();
        query_code =
            ProFeatureGeomitemVisit(&leader, PRO_SURFACE, collect_geom_ids, nullptr, &surface_ids);
        if (query_code == PRO_TK_NO_ERROR)
            return (int)surface_ids.size();
        if (query_code == PRO_TK_E_NOT_FOUND)
            return 0;
        return -1;
    }
    ProGroup grp = {};
    query_code = ProFeatureGroupGet(&leader, &grp);
    if (query_code != PRO_TK_NO_ERROR)
        return -1;
    ProFeature *members = nullptr;
    query_code = ProGroupFeaturesCollect(&grp, &members);
    if (query_code != PRO_TK_NO_ERROR || !members) {
        if (members)
            ProArrayFree((ProArray *)&members);
        return query_code == PRO_TK_E_NOT_FOUND ? 0 : -1;
    }
    int member_count = 0;
    ProError size_code = ProArraySizeGet((ProArray)members, &member_count);
    if (size_code != PRO_TK_NO_ERROR) {
        ProArrayFree((ProArray *)&members);
        query_code = size_code;
        return -1;
    }
    int total_surfaces = 0;
    bool saw_error = false;
    ProError first_error = PRO_TK_NO_ERROR;
    for (int i = 0; i < member_count; i++) {
        J ids = J::array();
        ProError code =
            ProFeatureGeomitemVisit(&members[i], PRO_SURFACE, collect_geom_ids, nullptr, &ids);
        if (code == PRO_TK_NO_ERROR) {
            total_surfaces += (int)ids.size();
        } else if (code != PRO_TK_E_NOT_FOUND && !saw_error) {
            saw_error = true;
            first_error = code;
        }
    }
    ProArrayFree((ProArray *)&members);
    if (saw_error && total_surfaces == 0) {
        query_code = first_error;
        return -1;
    }
    query_code = PRO_TK_NO_ERROR;
    return total_surfaces;
}

static bool parallel_to(const V &candidate, const V &requested) {
    // A direction reference must point along the requested vector, not merely
    // near it: a 0.5 deg skew would move every instance. 1e-9 cosine rejects
    // any real skew while tolerating normalized double noise.
    return fabs(dot(candidate, requested)) >= 1.0 - 1e-9;
}

static LinearPatternDirection bind_linear_pattern_direction(const V &requested) {
    LinearPatternDirection result;
    J state = inspection();
    std::vector<std::pair<int, V>> edges;
    for (const auto &edge : state.value("edges", J::array())) {
        if (!edge.contains("start") || !edge.contains("end"))
            continue; // arcs and other curves have no direction vector
        V a = vec(edge["start"]), b = vec(edge["end"]);
        V delta = {b[0] - a[0], b[1] - a[1], b[2] - a[2]};
        double length = sqrt(dot(delta, delta));
        if (!std::isfinite(length) || length <= 0)
            continue;
        result.candidate_count++;
        V direction = {delta[0] / length, delta[1] / length, delta[2] / length};
        if (!parallel_to(direction, requested))
            continue;
        edges.push_back({edge["id"].get<int>(), direction});
    }
    std::sort(
        edges.begin(), edges.end(),
        [](const std::pair<int, V> &a, const std::pair<int, V> &b) { return a.first < b.first; });
    if (!edges.empty()) {
        result.found = true;
        result.source = "straight_edge";
        result.id = edges[0].first;
        result.direction = edges[0].second;
        result.selection = selection(result.id, PRO_EDGE);
        return result;
    }
    std::vector<std::pair<int, V>> faces;
    for (const auto &surface : state.value("surfaces", J::array())) {
        if (surface.value("type", -1) != PRO_SRF_PLANE || !surface.contains("normal"))
            continue;
        result.candidate_count++;
        V normal = normalized(vec(surface["normal"]));
        if (!parallel_to(normal, requested))
            continue;
        faces.push_back({surface["id"].get<int>(), normal});
    }
    std::sort(
        faces.begin(), faces.end(),
        [](const std::pair<int, V> &a, const std::pair<int, V> &b) { return a.first < b.first; });
    if (!faces.empty()) {
        result.found = true;
        result.source = "planar_face";
        result.id = faces[0].first;
        result.direction = faces[0].second;
        result.selection = selection(result.id, PRO_SURFACE);
        return result;
    }
    return result;
}

static void generic_linear_pattern(const J &op) {
    ProFeature leader = feature(op["leader"]);
    ProFeattype leader_type;
    CK(ProFeatureTypeGet(&leader, &leader_type));
    const bool group = leader_type == PRO_FEAT_GROUP_HEAD;
    const std::string leader_kind = linear_pattern_leader_kind(leader_type);
    ProError surface_query_code = PRO_TK_NO_ERROR;
    const int leader_surface_count = count_leader_surfaces(leader, group, surface_query_code);
    const J leader_surface_json = leader_surface_count >= 0 ? J(leader_surface_count) : J(nullptr);
    const std::string leader_desc =
        op["leader"].is_string() ? op["leader"].get<std::string>() : op["leader"].dump();
    stage_operation_result({{"op", "linear_pattern"},
                            {"feature", op["label"]},
                            {"leader_id", leader.id},
                            {"leader_kind", leader_kind},
                            {"leader_feature_type", (int)leader_type},
                            {"leader_surface_count", leader_surface_json},
                            {"leader_surface_query_code", (int)surface_query_code},
                            {"group_leader", group}});
    // BUG-169: refuse alias/runtime mismatch and non-solid leaders before
    // ProPatternCreate so a sketch or datum can never silently pattern with dV=0.
    if (op["leader"].is_string()) {
        if (const J *alias = alias_entry(op["leader"].get<std::string>())) {
            const std::string recorded_op = alias->value("op", "");
            if (is_solid_alias_op(recorded_op) && is_non_solid_pattern_leader(leader_type)) {
                throw std::runtime_error("LINEAR_PATTERN_LEADER_ALIAS_MISMATCH: alias '" +
                                         leader_desc + "' is recorded as op='" + recorded_op +
                                         "' (feature_id=" + std::to_string(leader.id) +
                                         ") but Creo reports type=" + leader_kind +
                                         "; inspect the model feature tree before patterning");
            }
        }
    }
    if (is_non_solid_pattern_leader(leader_type)) {
        throw std::runtime_error(
            "LINEAR_PATTERN_NON_SOLID_LEADER: linear_pattern leader must be a solid feature "
            "(extrude/cut/hole/sweep/feature_group), not '" +
            leader_desc + "' (feature_id=" + std::to_string(leader.id) + ", type=" + leader_kind +
            ", surfaces=" +
            (leader_surface_count >= 0 ? std::to_string(leader_surface_count) : "unknown") +
            "); pass the solid feature label instead of its predecessor sketch or datum");
    }
    if (leader_surface_count == 0) {
        throw std::runtime_error(
            "LINEAR_PATTERN_NON_SOLID_LEADER: linear_pattern leader '" + leader_desc +
            "' (feature_id=" + std::to_string(leader.id) + ", type=" + leader_kind +
            ") owns 0 surfaces; pass a solid-producing feature instead of an empty or sketch-only "
            "feature");
    }
    const double spacing = op["spacing"].get<double>();
    const int count = op["count"].get<int>();
    if (!std::isfinite(spacing) || spacing <= 0)
        throw std::runtime_error("linear_pattern spacing must be a positive mm length");
    if (count < 2)
        throw std::runtime_error("linear_pattern count includes the leader and must be at least 2");
    if (!op["direction"].is_array() || op["direction"].size() != 3)
        throw std::runtime_error("linear_pattern direction must be an [x,y,z] unit vector");
    V requested = normalized(vec(op["direction"]));
    const bool flip = op.value("flip", false);
    V effective = {flip ? -requested[0] : requested[0], flip ? -requested[1] : requested[1],
                   flip ? -requested[2] : requested[2]};
    LinearPatternDirection bound = bind_linear_pattern_direction(effective);
    if (!bound.found) {
        J reference = op["direction"];
        throw std::runtime_error(
            "linear_pattern could not bind the requested direction to a model reference: no "
            "straight edge or planar face is parallel to " +
            reference.dump() +
            " (straight-edge candidates=" + std::to_string(bound.candidate_count) +
            "). Creo needs a real direction reference; create a datum axis or an edge along the "
            "pattern direction, or pass a direction that matches existing geometry");
    }
    ProElement root = node(nullptr, PRO_E_PATTERN_ROOT);
    integer(root, PRO_E_GENPAT_TYPE, PRO_GENPAT_DIR_DRIVEN);
    integer(root, PRO_E_GENPAT_REGEN_METHOD, PRO_PAT_GENERAL);
    ProElement settings = node(root, PRO_E_GENPAT_DIR);
    integer(settings, PRO_E_DIR_PAT_DIR1_OPT, PRO_GENPAT_TRANSLATIONAL);
    ProElement direction = node(node(settings, PRO_E_GENPAT_DIR1), PRO_E_DIRECTION_COMPOUND);
    ref(direction, PRO_E_DIRECTION_REFERENCE, bound.selection);
    ProSelectionFree(&bound.selection);
    integer(direction, PRO_E_DIRECTION_FLIP, PRO_DIRECTION_FLIP_ALONG);
    // The reference's own orientation decides the sign: an edge's start->end
    // vector is arbitrary, so the tree flip is set from the measured dot product
    // instead of assuming the reference already points the requested way.
    const bool tree_flip = dot(bound.direction, effective) < 0;
    integer(settings, PRO_E_DIR_PAT_DIR1_FLIP, tree_flip ? 1 : 0);
    real(settings, PRO_E_GENPAT_DIR1_INC, spacing);
    integer(settings, PRO_E_GENPAT_DIM_FIRST_DIR_NUM_INST, count);
    ProPatternClass kind = group ? PRO_GROUP_PATTERN : PRO_FEAT_PATTERN;
    ProError code = ProPatternCreate(&leader, kind, root);
    ProElementFree(&root);
    check(code, "CreateNativeLinearPattern");
    ProPattern pattern;
    ProFeature head;
    CK(ProFeaturePatternGet(&leader, kind, &pattern));
    CK(ProPatternHeaderGet(&pattern, &head));
    ProName name;
    wcscpy_s(name, wide(op["label"]).c_str());
    CK(ProModelitemNameSet(&head, name));
    ProFeature *members = nullptr;
    ProError member_code = ProPatternMembersGet(&pattern, &members);
    int member_count = 0;
    if (!member_code && members) {
        CK(ProArraySizeGet((ProArray)members, &member_count));
        ProArrayFree((ProArray *)&members);
    }
    log("LINEAR_PATTERN head=%d leader=%d leader_kind=%s leader_surfaces=%d count=%d "
        "member_count=%d spacing=%.6f source=%s reference_id=%d flip=%d\n",
        head.id, leader.id, leader_kind.c_str(), leader_surface_count, count, member_count, spacing,
        bound.source.c_str(), bound.id, (int)flip);
    remember(op, head,
             {{"leader_id", leader.id},
              {"leader_kind", leader_kind},
              {"leader_feature_type", (int)leader_type},
              {"leader_surface_count", leader_surface_json},
              {"count", count},
              {"spacing", spacing},
              {"direction", xyz(requested.data())},
              {"flip", flip},
              {"direction_reference", {{"source", bound.source}, {"id", bound.id}}}});
    stage_operation_result(
        {{"op", "linear_pattern"},
         {"feature", op["label"]},
         {"feature_id", head.id},
         {"leader_id", leader.id},
         {"leader_kind", leader_kind},
         {"leader_feature_type", (int)leader_type},
         {"leader_surface_count", leader_surface_json},
         {"leader_surface_query_code", (int)surface_query_code},
         {"count", count},
         {"spacing", spacing},
         {"direction", xyz(requested.data())},
         {"flip", flip},
         {"direction_reference",
          {{"source", bound.source}, {"id", bound.id}, {"direction", xyz(bound.direction.data())}}},
         {"tree_flip", tree_flip},
         {"member_count", member_code ? J(nullptr) : J(member_count)},
         {"member_query_code", (int)member_code},
         {"group_leader", group}});
}
