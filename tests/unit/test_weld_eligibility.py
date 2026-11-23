"""FEAT-039: weld qualification shared by admission and submission.

The fixtures reproduce the shapes from the 0.27.0 feedback: a 1.104e-06 mm arc
seam, an obround (long hole) with one short seam, and a lens built from two
different arcs. Each test records what the admission check says and what the
policy layer can actually deliver, so the remediation text cannot recommend a
path the submission gate then refuses.
"""

import math
import unittest

from creo_mechdog.endpoint_welding import (
    eligibility_summary,
    prepare_operations,
    weld_eligibility,
)
from creo_mechdog.profile_diagnostics import validate_solid_profile

REPORTED_GAP = 1.104e-6
# BUG-159: endpoint_welding treats any gap at or below 1e-6 mm as already
# coincident, so a weld-path fixture must stay above that tolerance and inside
# the 1e-4 mm closure-diagnostic scale.
WELD_GAP = 5e-5


def line(name, start, end):
    return {"type": "line", "name": name, "start": list(start), "end": list(end)}


def arc(name, center, radius, start_angle, end_angle):
    return {
        "type": "arc",
        "name": name,
        "center": list(center),
        "radius": radius,
        "start_angle": start_angle,
        "end_angle": end_angle,
    }


def arc_seam(gap=REPORTED_GAP, radius=200.0):
    """Two arcs on one circle whose closing seam is `gap` mm wide."""
    return [
        arc("a1", (0.0, 0.0), radius, 0.0, 180.0),
        arc("a2", (0.0, 0.0), radius, 180.0, 360.0 - math.degrees(gap / radius)),
    ]


def split_ring(gap=REPORTED_GAP, radius=200.0):
    """Two arcs on one circle that are short at *both* ends, so no exact join."""
    half = math.degrees((gap / 2.0) / radius)
    return [
        arc("a1", (0.0, 0.0), radius, half, 180.0 - half),
        arc("a2", (0.0, 0.0), radius, 180.0 + half, 360.0 - half),
    ]


def obround(gap=REPORTED_GAP):
    """A long hole: two lines and two half arcs, one seam short by `gap`."""
    return [
        line("bottom", (-50.0, -20.0), (50.0, -20.0)),
        arc("right", (50.0, 0.0), 20.0, -90.0, 90.0),
        line("top", (50.0, 20.0), (-50.0 + gap, 20.0)),
        arc("left", (-50.0, 0.0), 20.0, 90.0, 270.0),
    ]


def lens(gap=REPORTED_GAP):
    """Two different arcs meeting at both ends, each end short by about `gap`."""
    radius = math.hypot(100.0, 60.0)
    start_angle = math.degrees(math.atan2(60.0, -100.0))
    end_angle = math.degrees(math.atan2(60.0, 100.0))
    return [
        arc("lower", (0.0, 0.0), 100.0, 180.0, 360.0),
        arc("upper", (0.0, -60.0), radius + gap, start_angle, end_angle),
    ]


def gapped_square(gap=WELD_GAP):
    return [
        line("l1", (0.0, 0.0), (10.0, 0.0)),
        line("l2", (10.0, 0.0), (10.0, 10.0)),
        line("l3", (10.0, 10.0), (0.0, 10.0)),
        line("l4", (0.0, 10.0), (0.0, gap)),
    ]


def two_closed_rings(gap=5e-6):
    """Two closed rings whose corners sit `gap` apart: welding would bridge them."""
    return [
        line("a1", (0.0, 0.0), (10.0, 0.0)),
        line("a2", (10.0, 0.0), (10.0, 10.0)),
        line("a3", (10.0, 10.0), (0.0, 10.0)),
        line("a4", (0.0, 10.0), (0.0, 0.0)),
        line("b1", (10.0 + gap, 0.0), (20.0, 0.0)),
        line("b2", (20.0, 0.0), (20.0, 10.0)),
        line("b3", (20.0, 10.0), (10.0 + gap, 10.0)),
        line("b4", (10.0 + gap, 10.0), (10.0 + gap, 0.0)),
    ]


def sketch(entities, **overrides):
    operation = {"op": "sketch", "label": "s1", "entities": entities}
    operation.update(overrides)
    return operation


class AdmissionVersusSubmissionTests(unittest.TestCase):
    def test_the_reported_arc_seam_is_admitted_only_as_a_residual(self):
        with self.assertRaises(ValueError) as caught:
            validate_solid_profile(arc_seam(), "coordinates", "extrude")
        self.assertIn("near_tolerance", str(caught.exception))

    def test_the_reported_arc_seam_is_pairable_because_the_arcs_share_a_chain(self):
        eligibility = weld_eligibility(arc_seam(), max_move_mm=1e-6)
        # The two arcs meet exactly at 180 degrees, so they are one chain and
        # the 1.104e-06 mm seam is a pair the policy layer can name. Whether the
        # kernel welds it is still the kernel's answer.
        self.assertEqual(eligibility["candidate_pairs"], 1)
        self.assertEqual(eligibility["verdict"], "weldable")
        self.assertEqual(eligibility["accepted_pairs"], 1)
        self.assertEqual(eligibility["blocking_pairs"], 0)
        self.assertAlmostEqual(eligibility["max_required_move_mm"], REPORTED_GAP / 2.0, places=12)

    def test_a_ring_that_is_short_at_both_ends_is_unresolved_not_refused(self):
        eligibility = weld_eligibility(split_ring(), max_move_mm=1e-6)
        # No exact join means two open chains; welding them would produce one
        # contour, which the 1e-9 mm union cannot prove and the kernel owns.
        self.assertEqual(eligibility["candidate_pairs"], 2)
        self.assertEqual(eligibility["verdict"], "unresolved")
        self.assertEqual(eligibility["blocking_pairs"], 0)
        self.assertEqual(eligibility["unresolved_pairs"], 2)
        self.assertIn("open chains", eligibility_summary(eligibility))

    def test_the_obround_seam_is_paired_rather_than_reported_as_closed(self):
        eligibility = weld_eligibility(obround(), max_move_mm=1e-6)
        self.assertEqual(eligibility["verdict"], "weldable")
        # BUG-159: the trig round-off join between the bottom line and the left
        # arc (7e-15 mm) is below the 1e-6 mm coincidence tolerance and is no
        # longer a candidate; only the reported seam needs welding.
        self.assertEqual(eligibility["accepted_pairs"], 1)
        self.assertAlmostEqual(eligibility["max_required_move_mm"], REPORTED_GAP / 2.0, places=12)

    def test_a_lens_of_two_different_arcs_is_blocked_by_arc_geometry(self):
        eligibility = weld_eligibility(lens(), max_move_mm=1e-6)
        self.assertEqual(eligibility["verdict"], "blocked")
        self.assertEqual(eligibility["blocking_pairs"], 2)
        for pair in eligibility["blocking"]:
            self.assertEqual(pair["reason"], "arc_inconsistent")
        summary = eligibility_summary(eligibility)
        self.assertIn("cannot fix this profile", summary)
        self.assertIn("arc_inconsistent", summary)

    def test_welding_two_closed_rings_is_blocked_by_topology(self):
        eligibility = weld_eligibility(two_closed_rings(), max_move_mm=1e-6)
        self.assertEqual(eligibility["verdict"], "blocked")
        # Both touching corners are two-endpoint clusters, so 2 x 2 pairs are
        # refused; none of them may bridge the two closed rings.
        self.assertEqual(eligibility["blocking_pairs"], 8)
        self.assertEqual(
            {pair["reason"] for pair in eligibility["blocking"]},
            {"would_merge_closed_contours"},
        )

    def test_a_bound_below_the_required_move_blocks_the_weld(self):
        eligibility = weld_eligibility(gapped_square(), max_move_mm=WELD_GAP / 100.0)
        self.assertEqual(eligibility["verdict"], "blocked")
        self.assertEqual(eligibility["blocking"][0]["reason"], "max_move_exceeded")

    def test_an_admitted_weldable_seam_reports_its_largest_move(self):
        eligibility = weld_eligibility(gapped_square(), max_move_mm=WELD_GAP)
        self.assertEqual(eligibility["verdict"], "weldable")
        self.assertEqual(eligibility["accepted_pairs"], 1)
        self.assertAlmostEqual(eligibility["max_required_move_mm"], WELD_GAP / 2.0, places=15)
        self.assertIn("weldable", eligibility_summary(eligibility))

    def test_a_profile_without_any_candidate_join_is_not_dressed_up_as_weldable(self):
        eligibility = weld_eligibility(
            [
                line("l1", (0.0, 0.0), (10.0, 0.0)),
                line("l2", (10.0, 0.0), (10.0, 10.0)),
            ]
        )
        self.assertEqual(eligibility["verdict"], "not_needed")
        self.assertIn("structurally open", eligibility_summary(eligibility))

    def test_residual_arc_joints_below_one_micrometre_are_coincident(self):
        # BUG-159 / 0.35.5 §十三: 3.464e-08 and 4.727e-08 mm residuals must not
        # be classified as arc_inconsistent. Lens shifts the upper arc's radius
        # by the gap, the same defect class as the reported 40-arc profile.
        eligibility = weld_eligibility(lens(gap=4e-8), max_move_mm=1e-6)
        self.assertEqual(eligibility["candidate_pairs"], 0)
        self.assertEqual(eligibility["verdict"], "not_needed")
        self.assertNotIn("arc_inconsistent", eligibility_summary(eligibility))

    def test_a_visible_arc_mismatch_above_the_coincidence_tolerance_is_refused(self):
        eligibility = weld_eligibility(lens(gap=5e-5), max_move_mm=1e-6)
        self.assertEqual(eligibility["verdict"], "blocked")
        self.assertEqual({pair["reason"] for pair in eligibility["blocking"]}, {"arc_inconsistent"})

    def test_a_one_millimetre_gap_is_not_a_closed_contour(self):
        # A 1e-3 mm seam is beyond every published tolerance, so the profile is
        # still refused as open instead of being reported as closed.
        with self.assertRaises(ValueError) as caught:
            validate_solid_profile(lens(gap=1e-3), "autodim", "extrude")
        message = str(caught.exception)
        self.assertIn("no_closed_contour", message)
        self.assertIn("[open]", message)


class SubmissionGateTests(unittest.TestCase):
    def test_weld_policy_refuses_a_pair_the_policy_layer_cannot_weld(self):
        with self.assertRaises(ValueError) as caught:
            prepare_operations([sketch(lens(), endpoint_policy="weld", max_endpoint_move_mm=1e-6)])
        message = str(caught.exception)
        self.assertIn("endpoint policy weld", message)
        self.assertIn("arc_inconsistent", message)
        self.assertIn("cannot fix this profile", message)

    def test_weld_policy_still_accepts_a_weldable_seam_and_publishes_eligibility(self):
        operation = sketch(gapped_square(), endpoint_policy="weld", max_endpoint_move_mm=WELD_GAP)
        prepared = prepare_operations([operation])
        self.assertEqual(len(prepared[0]["weld_pairs"]), 1)
        self.assertEqual(prepared[0]["endpoint_weld_eligibility"]["verdict"], "weldable")

    def test_weld_policy_reports_an_unresolved_seam_without_refusing_the_plan(self):
        operation = sketch(split_ring(), endpoint_policy="weld", max_endpoint_move_mm=REPORTED_GAP)
        prepared = prepare_operations([operation])
        eligibility = prepared[0]["endpoint_weld_eligibility"]
        # The 2026-11-02 measurement showed the kernel welding a 8.215e-07 mm
        # gap, so an unproved chain merge is reported, never refused here.
        self.assertEqual(eligibility["verdict"], "unresolved")
        self.assertEqual(prepared[0]["weld_pairs"], [])

    def test_snap_endpoints_refuses_instead_of_silently_not_moving_two_arcs(self):
        with self.assertRaises(ValueError) as caught:
            prepare_operations([sketch(arc_seam(), snap_endpoints=True, max_endpoint_move_mm=1e-6)])
        message = str(caught.exception)
        self.assertIn("snap_endpoints asked the policy layer", message)
        self.assertIn("arc_pair_not_snappable", message)

    def test_snap_endpoints_still_rewrites_a_weldable_line_seam(self):
        operation = sketch(gapped_square(), snap_endpoints=True, max_endpoint_move_mm=WELD_GAP)
        prepared = prepare_operations([operation])
        self.assertEqual(prepared[0]["entities"][3]["end"], [0.0, WELD_GAP / 2.0])
        self.assertEqual(prepared[0]["snap_endpoint_receipt"]["applied"], True)
        self.assertEqual(prepared[0]["endpoint_weld_eligibility"]["verdict"], "weldable")

    def test_report_policy_never_raises_and_never_moves_geometry(self):
        entities = lens()
        prepared = prepare_operations([sketch(entities, endpoint_policy="report")])
        self.assertEqual(prepared[0]["entities"], lens())
        self.assertNotIn("weld_pairs", prepared[0])


class RemediationTextTests(unittest.TestCase):
    def test_rejection_keeps_the_documented_terms(self):
        with self.assertRaises(ValueError) as caught:
            validate_solid_profile(gapped_square(), "coordinates", "extrude")
        message = str(caught.exception)
        for term in ("closure_tolerance_mm", "polyline", "snap_endpoints", "submission"):
            self.assertIn(term, message)

    def test_rejection_states_what_welding_can_and_cannot_do(self):
        with self.assertRaises(ValueError) as caught:
            validate_solid_profile(lens(), "coordinates", "extrude")
        message = str(caught.exception)
        self.assertIn("For this profile:", message)
        self.assertIn("cannot fix this profile", message)
        self.assertIn("arc_inconsistent", message)

    def test_rejection_names_the_unresolved_seam_instead_of_promising_a_weld(self):
        with self.assertRaises(ValueError) as caught:
            validate_solid_profile(split_ring(), "coordinates", "extrude")
        message = str(caught.exception)
        self.assertIn("For this profile:", message)
        self.assertIn("open chains", message)
        self.assertIn("endpoint_policy='weld'", message)

    def test_rejection_confirms_a_weldable_seam_instead_of_hedging(self):
        with self.assertRaises(ValueError) as caught:
            validate_solid_profile(arc_seam(), "coordinates", "extrude")
        message = str(caught.exception)
        self.assertIn("For this profile:", message)
        self.assertIn("All 1 near join(s) are weldable", message)
        self.assertIn("largest move 5.520e-07 mm", message)

    def test_an_admitted_profile_raises_nothing(self):
        # A seam inside the residual band (1e-7 mm at the default scale) is
        # admitted, so no remediation text is produced at all.
        report = validate_solid_profile(gapped_square(5e-8), "coordinates", "extrude")
        self.assertEqual(report["analysis"], "complete")


if __name__ == "__main__":
    unittest.main()
