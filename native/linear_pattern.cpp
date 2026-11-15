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
    log("LINEAR_PATTERN head=%d leader=%d count=%d member_count=%d spacing=%.6f source=%s "
        "reference_id=%d flip=%d\n",
        head.id, leader.id, count, member_count, spacing, bound.source.c_str(), bound.id,
        (int)flip);
    remember(op, head,
             {{"leader_id", leader.id},
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
