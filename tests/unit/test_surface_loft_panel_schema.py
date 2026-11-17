"""BUG-120/D1: ``creation_route`` is additive, and the panel route is its own subset.

Every request written before this field existed must serialize exactly as before, so
the omitted route never adds a key. The panel route accepts 2-8 MCP-owned sketch
labels only: a bare id, a curve/edge/point reference, guides, boundary conditions and
templates stay on the element tree, and the refusal happens while validating the plan
(before a job exists), not after a UI run.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from creo_mechdog.schema import validate_operations


def loft(**extra):
    return {
        "op": "surface_loft",
        "label": "loft_surface",
        "sections": ["loft_a", "loft_b"],
        **extra,
    }


def panel(**extra):
    return loft(creation_route="resident_panel", **extra)


class OmittedRouteIsUnchanged(unittest.TestCase):
    def test_omitted_route_serializes_no_field(self):
        dumped = validate_operations([loft()])[0]
        self.assertNotIn("creation_route", dumped)
        self.assertEqual(sorted(dumped), ["guides", "interpolation", "label", "op", "sections"])

    def test_element_tree_route_keeps_32_sections(self):
        sections = [f"sec_{index:02d}" for index in range(32)]
        dumped = validate_operations(
            [loft(sections=sections, interpolation="smooth", creation_route="element_tree")]
        )[0]
        self.assertEqual(dumped["creation_route"], "element_tree")
        self.assertEqual(len(dumped["sections"]), 32)

    def test_an_unknown_route_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations([loft(creation_route="resident_panel_v2")])
        self.assertIn("creation_route", str(caught.exception))


class PanelRouteAcceptsTheCurveSubset(unittest.TestCase):
    def test_two_and_eight_labels_pass_and_keep_the_route(self):
        for count, interpolation in ((2, "straight"), (3, "smooth"), (8, "smooth")):
            with self.subTest(count=count):
                sections = [f"panel_sec_{index}" for index in range(count)]
                dumped = validate_operations(
                    [panel(sections=sections, interpolation=interpolation)]
                )[0]
                self.assertEqual(dumped["creation_route"], "resident_panel")
                self.assertEqual(dumped["sections"], sections)

    def test_one_section_is_refused_by_the_shared_minimum(self):
        with self.assertRaises(ValueError):
            validate_operations([panel(sections=["only_one"])])

    def test_nine_sections_are_refused_with_the_route_limit(self):
        sections = [f"panel_sec_{index}" for index in range(9)]
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=sections, interpolation="smooth")])
        self.assertIn("2-8 sections", str(caught.exception))
        self.assertIn("element_tree", str(caught.exception))

    def test_repeated_labels_are_still_refused(self):
        with self.assertRaises(ValueError):
            validate_operations([panel(sections=["same_sketch", "same_sketch"])])

    def test_three_sections_still_require_smooth(self):
        sections = ["panel_a", "panel_b", "panel_c"]
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=sections)])
        self.assertIn("smooth", str(caught.exception))


class PanelRouteRefusesTheTreeOnlyForms(unittest.TestCase):
    def test_reference_objects_are_refused(self):
        forms = [
            {"kind": "edge", "id": 7},
            {"kind": "curve", "id": 9},
            {"kind": "point", "id": 11},
            {"kind": "datum_point_feature", "label": "tip_point"},
        ]
        for form in forms:
            with self.subTest(form=form):
                with self.assertRaises(ValueError) as caught:
                    validate_operations([panel(sections=["panel_a", form])])
                self.assertIn("MCP-owned sketch label", str(caught.exception))

    def test_a_bare_feature_id_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=["panel_a", 41])])
        self.assertIn("bare feature id", str(caught.exception))
        self.assertIn("element_tree", str(caught.exception))

    def test_guides_are_refused(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(guides=["guide_a", "guide_b"])])
        self.assertIn("does not accept guides", str(caught.exception))

    def test_boundary_conditions_are_refused(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations(
                [panel(boundary_conditions=[{"boundary": "first_section", "condition": "free"}])]
            )
        self.assertIn("does not accept boundary_conditions", str(caught.exception))

    def test_a_template_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory) / "loft.xml"
            tree.write_text("<root/>", encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                validate_operations([panel(template={"file": str(tree)})])
            self.assertIn("does not accept template", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
