"""BUG-120/D1: ``creation_route`` is additive, and the panel route is its own subset.

Every request written before this field existed must serialize exactly as before, so
the omitted route never adds a key. The panel route accepts 2-8 MCP-owned sketch
labels: a bare id, a curve/edge reference or a bare point id stays on the element
tree, and the refusal happens while validating the plan (before a job exists), not
after a UI run. BUG-120/D7 adds guides as the same kind of label (2 or more, at most
8 positions together with the sections) and one datum-point label at either end as
the convergence section.
"""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from creo_mechdog.schema import validate_operations


def sec(label):
    """A panel position with the caller's openness proof (BUG-120, 2026-11-19)."""
    return {"label": label, "open_confirmed": True}


def loft(**extra):
    return {
        "op": "surface_loft",
        "label": "loft_surface",
        "sections": ["loft_a", "loft_b"],
        **extra,
    }


def panel(**extra):
    extra.setdefault("sections", [sec("loft_a"), sec("loft_b")])
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
                sections = [sec(f"panel_sec_{index}") for index in range(count)]
                dumped = validate_operations(
                    [panel(sections=sections, interpolation=interpolation)]
                )[0]
                self.assertEqual(dumped["creation_route"], "resident_panel")
                self.assertEqual(dumped["sections"], sections)

    def test_one_section_is_refused_by_the_shared_minimum(self):
        with self.assertRaises(ValueError):
            validate_operations([panel(sections=[sec("only_one")])])

    def test_nine_sections_are_refused_with_the_route_limit(self):
        sections = [sec(f"panel_sec_{index}") for index in range(9)]
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=sections, interpolation="smooth")])
        self.assertIn("2-8 sections", str(caught.exception))
        self.assertIn("element_tree", str(caught.exception))

    def test_repeated_labels_are_still_refused(self):
        with self.assertRaises(ValueError):
            validate_operations([panel(sections=[sec("same_sketch"), sec("same_sketch")])])

    def test_three_sections_still_require_smooth(self):
        sections = [sec("panel_a"), sec("panel_b"), sec("panel_c")]
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=sections)])
        self.assertIn("smooth", str(caught.exception))

    def test_a_bare_label_is_refused_before_a_job_exists(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=["panel_a", "panel_b"])])
        text = str(caught.exception)
        self.assertIn("bare label", text)
        self.assertIn("open_confirmed", text)
        self.assertIn("No job was created", text)
        self.assertIn("element_tree", text)

    def test_a_bare_guide_label_is_refused_before_a_job_exists(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations(
                [panel(sections=[sec("panel_a"), sec("panel_b")], guides=["guide_a", "guide_b"])]
            )
        self.assertIn("guides[0] is the bare label", str(caught.exception))

    def test_the_element_tree_route_still_accepts_bare_labels(self):
        dumped = validate_operations(
            [loft(sections=["loft_a", "loft_b"], creation_route="element_tree")]
        )[0]
        self.assertEqual(dumped["sections"], ["loft_a", "loft_b"])


class PanelRouteRefusesTheTreeOnlyForms(unittest.TestCase):
    def test_reference_objects_are_refused(self):
        forms = [
            {"kind": "edge", "id": 7},
            {"kind": "curve", "id": 9},
        ]
        for form in forms:
            with self.subTest(form=form):
                with self.assertRaises(ValueError) as caught:
                    validate_operations([panel(sections=[sec("panel_a"), form])])
                self.assertIn("MCP-owned sketch label", str(caught.exception))

    def test_a_bare_point_id_is_refused_in_favour_of_its_label(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=[sec("panel_a"), {"kind": "point", "id": 11}])])
        self.assertIn("MCP-owned label", str(caught.exception))
        self.assertIn("datum_point_feature", str(caught.exception))

    def test_a_bare_feature_id_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=[sec("panel_a"), 41])])
        self.assertIn("bare feature id", str(caught.exception))
        self.assertIn("element_tree", str(caught.exception))

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


class PanelRouteAcceptsTheSecondDirection(unittest.TestCase):
    """BUG-120/D7: guides are the second direction, admitted as sketch labels."""

    def test_two_guides_pass_and_keep_their_order(self):
        guides = [sec("guide_a"), sec("guide_b")]
        dumped = validate_operations([panel(sections=[sec("sec_a"), sec("sec_b")], guides=guides)])[
            0
        ]
        self.assertEqual(dumped["guides"], guides)
        self.assertEqual(dumped["sections"], [sec("sec_a"), sec("sec_b")])

    def test_label_objects_with_open_confirmed_pass(self):
        dumped = validate_operations(
            [
                panel(
                    sections=[
                        {"label": "sec_a", "open_confirmed": True},
                        {"label": "sec_b", "open_confirmed": True},
                    ],
                    guides=[
                        {"label": "guide_a", "open_confirmed": True},
                        {"label": "guide_b", "open_confirmed": True},
                    ],
                )
            ]
        )[0]
        self.assertEqual(len(dumped["guides"]), 2)

    def test_one_guide_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(guides=[sec("guide_a")])])
        self.assertIn("2 or more guides", str(caught.exception))

    def test_a_guide_reference_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(guides=[sec("guide_a"), {"kind": "edge", "id": 7}])])
        self.assertIn("MCP-owned sketch label", str(caught.exception))

    def test_a_guide_repeating_a_section_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations(
                [
                    panel(
                        sections=[sec("sec_a"), sec("sec_b")], guides=[sec("sec_a"), sec("guide_b")]
                    )
                ]
            )
        self.assertIn("must be distinct sketches", str(caught.exception))

    def test_sections_and_guides_share_the_eleven_position_budget(self):
        sections = [sec(f"sec_{index}") for index in range(8)]
        guides = [sec(f"guide_{index}") for index in range(4)]
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=sections, guides=guides, interpolation="smooth")])
        self.assertIn("at most 11 positions", str(caught.exception))

    def test_the_seven_curve_point_and_three_guide_case_fits(self):
        sections = [sec(f"sec_{index}") for index in range(7)] + [
            {"kind": "datum_point_feature", "label": "tip"}
        ]
        guides = [sec(f"guide_{index}") for index in range(3)]
        dumped = validate_operations(
            [panel(sections=sections, guides=guides, interpolation="smooth")]
        )[0]
        self.assertEqual(len(dumped["sections"]), 8)
        self.assertEqual(len(dumped["guides"]), 3)


class PanelRouteAcceptsTheConvergencePoint(unittest.TestCase):
    """BUG-120/D7: one end may be an MCP-owned datum point, by label only."""

    def test_a_point_at_the_last_section_passes(self):
        sections = [sec("sec_a"), sec("sec_b"), {"kind": "datum_point_feature", "label": "tip"}]
        dumped = validate_operations([panel(sections=sections, interpolation="smooth")])[0]
        self.assertEqual(dumped["sections"], sections)

    def test_a_point_at_the_first_section_passes(self):
        sections = [{"kind": "datum_point_feature", "label": "tip"}, sec("sec_a"), sec("sec_b")]
        dumped = validate_operations([panel(sections=sections, interpolation="smooth")])[0]
        self.assertEqual(dumped["sections"][0], sections[0])

    def test_a_point_in_the_middle_is_refused(self):
        sections = [sec("sec_a"), {"kind": "datum_point_feature", "label": "tip"}, sec("sec_b")]
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=sections, interpolation="smooth")])
        self.assertIn("first or last section", str(caught.exception))

    def test_two_points_are_refused(self):
        sections = [
            {"kind": "datum_point_feature", "label": "tip_a"},
            sec("sec_a"),
            {"kind": "datum_point_feature", "label": "tip_b"},
        ]
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=sections, interpolation="smooth")])
        self.assertIn("one convergence point", str(caught.exception))

    def test_a_point_needs_a_non_empty_label(self):
        sections = [sec("sec_a"), sec("sec_b"), {"kind": "datum_point_feature", "label": ""}]
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=sections, interpolation="smooth")])
        self.assertIn("point label", str(caught.exception))

    def test_a_point_with_extra_keys_is_refused(self):
        sections = [
            sec("sec_a"),
            sec("sec_b"),
            {"kind": "datum_point_feature", "label": "tip", "id": 11},
        ]
        with self.assertRaises(ValueError) as caught:
            validate_operations([panel(sections=sections, interpolation="smooth")])
        self.assertIn("only kind and label", str(caught.exception))

    def test_a_point_cannot_be_a_guide(self):
        with self.assertRaises(ValueError) as caught:
            validate_operations(
                [
                    panel(
                        sections=[sec("sec_a"), sec("sec_b")],
                        guides=[
                            {"kind": "datum_point_feature", "label": "tip"},
                            sec("guide_b"),
                        ],
                    )
                ]
            )
        self.assertIn("cannot be a convergence point", str(caught.exception))


class BothPublicEntriesShareTheValidation(unittest.TestCase):
    """BUG-120 task 1: the tool and the generic plan entry refuse the same input."""

    def refuse(self, call):
        import server

        with patch.object(server.startup, "require_ready"):
            with self.assertRaises(Exception) as caught:
                asyncio.run(call())
        self.assertIn("bare label", str(caught.exception))
        self.assertIn("open_confirmed", str(caught.exception))

    def test_creo_surface_loft_refuses_a_bare_panel_label(self):
        import server

        self.refuse(
            lambda: server.creo_surface_loft(
                model_id="model",
                expected_revision=1,
                label="loft_surface",
                sections=["panel_a", "panel_b"],
                creation_route="resident_panel",
            )
        )

    def test_creo_execute_plan_refuses_a_bare_panel_label(self):
        import json

        import server

        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory) / "plan.json"
            plan.write_text(json.dumps([panel(sections=["panel_a", "panel_b"])]), encoding="utf-8")
            self.refuse(
                lambda: server.creo_execute_plan(
                    model_id="model", expected_revision=1, plan_file=str(plan)
                )
            )


class ToolWrapperForwardsTheRoute(unittest.TestCase):
    def test_the_tool_only_forwards_an_explicit_route(self):
        import server

        captured = AsyncMock(return_value={"status": "accepted"})
        base = dict(model_id="m", expected_revision=1, label="loft_surface", sections=["a", "b"])
        with patch.object(server, "invoke", captured):
            asyncio.run(server.creo_surface_loft(**base))
            self.assertNotIn("creation_route", captured.call_args.args[1][0])
            asyncio.run(server.creo_surface_loft(**base, creation_route="resident_panel"))
            self.assertEqual(captured.call_args.args[1][0]["creation_route"], "resident_panel")
            asyncio.run(server.creo_surface_loft(**base, creation_route="element_tree"))
            self.assertEqual(captured.call_args.args[1][0]["creation_route"], "element_tree")

    def test_the_tool_schema_publishes_both_routes(self):
        import server

        tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
        schema = tools["creo_surface_loft"].input_schema["properties"]["creation_route"]
        self.assertEqual(sorted(schema["anyOf"][0]["enum"]), ["element_tree", "resident_panel"])


if __name__ == "__main__":
    unittest.main()
