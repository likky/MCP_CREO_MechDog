// surface_loft_panel.h — BUG-120/D1: the resident panel creation route.
//
// The resident panel route replays recorded Creo UI commands through the resident
// callback instead of building a boundary-blend element tree, so it does not need
// element-tree extraction (the Creo 10 host refuses that readback with -18). The
// route is declared here, next to the tree route it shares an operation with:
// `creo_surface_loft` keeps `op="surface_loft"` and adds
// `creation_route="resident_panel"`, so no extra public tool appears.
//
// D1 delivers the route contract, not the backend. Admission refuses a panel
// request in Python before a job exists, and this stub is the second gate for a
// hand-written plan that skipped that admission: it must never silently fall back
// to the element tree, because the two routes create the feature differently and
// only the panel route is expected to work on the target host.
//
// The build reports its panel state in worker build-info so a client can tell
// "not implemented", "compiled out" and "ready" apart instead of inferring it.
#ifndef MECHDOG_SURFACE_LOFT_PANEL_H
#define MECHDOG_SURFACE_LOFT_PANEL_H

// BUG-120/D3 will replace this with the recorded protocol generation and the
// one-shot command tickets it needs. Until then the state is a constant fact of
// the binary, exactly like the boundary-blend element-id probe next door.
inline const char *mechdog_surface_loft_panel_state() { return "not_implemented"; }

// No panel backend exists yet: refuse the operation with a named error. The
// element-tree path stays reachable only when the request asks for it.
inline void generic_surface_loft_panel(const J &op) {
    (void)op;
    throw std::runtime_error(
        "PANEL_SURFACE_LOFT_UNAVAILABLE: creation_route=resident_panel has no native backend in "
        "this build; no feature was created and the request is not retried on the element tree "
        "route. Use creation_route=element_tree on a host that supports it.");
}

#endif  // MECHDOG_SURFACE_LOFT_PANEL_H
