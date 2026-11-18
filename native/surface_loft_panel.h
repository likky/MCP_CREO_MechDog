// surface_loft_panel.h — BUG-120/D1/D3: the resident panel creation route.
//
// The resident panel route replays a recorded Creo UI command sequence through the
// resident callback instead of building a boundary-blend element tree, so it does not
// need element-tree extraction (the Creo 10 host refuses that readback with -18). The
// route keeps `op="surface_loft"` and adds `creation_route="resident_panel"`, so no
// extra public tool appears.
//
// D1 delivered the route contract; D3 delivers the backend (panel_run.h). The backend
// still refuses to invent two things: the recorded dialog macro and the restricted
// Done both come from a certified UI profile. Without a certified profile the request
// is refused with a named code and the run stays selectable — it never falls back to
// the element tree, because the two routes create the feature differently.
//
// The build reports its panel state in worker build-info so a client can tell
// "not implemented", "compiled out" and "ready" apart instead of inferring it.
#ifndef MECHDOG_SURFACE_LOFT_PANEL_H
#define MECHDOG_SURFACE_LOFT_PANEL_H

// The backend is compiled into this binary (panel_run.h, included after the helpers
// it uses). "ready" means the route executes here; it does not mean the recorded
// profile or the target host has been verified.
inline const char *mechdog_surface_loft_panel_state() { return "ready"; }

// Defined by panel_run.h, which is included later in the same translation unit
// because it uses the resident-callback helpers.
void generic_surface_loft_panel(const J &op);

#endif  // MECHDOG_SURFACE_LOFT_PANEL_H
