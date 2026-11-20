"""FEAT-023 / BUG-076: component lists page without losing identity."""

import asyncio
import unittest

import server
from creo_mechdog.component_pages import component_page
from creo_mechdog.model_queries import RESPONSE_BUDGET, serialized_size

SOURCE = "0123456789abcdef0123456789abcdef"


def component(feature_id, source_revision=2, **overrides):
    record = {
        "name": f"c_{SOURCE[:8]}_{feature_id}",
        "feature_id": feature_id,
        "identity": {"model_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "feature_id": feature_id},
        "labels": [f"part_{feature_id}"],
        "label": f"part_{feature_id}",
        "label_state": "single",
        "source_model_id": SOURCE,
        "source_revision": source_revision,
        "bindings": [
            {
                "label": f"part_{feature_id}",
                "source_model_id": SOURCE,
                "source_revision": source_revision,
            }
        ],
        "transform": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, feature_id * 10.0, 0.0, 0.0],
        "placement_status": "assembled",
    }
    record.update(overrides)
    return record


def page(components, **kwargs):
    kwargs.setdefault("identity_key", {"model_id": "a" * 32, "key": "model_identity+feature_id"})
    return component_page("a" * 32, kwargs.pop("revision", 3), components, **kwargs)


def many(count=269):
    """A fixture large enough that the whole list cannot fit the budget."""
    return [component(index) for index in range(1, count + 1)]


def walk(components, **kwargs):
    """Follow every page and return (pages, collected feature ids)."""
    pages, seen, cursor = [], [], None
    while True:
        current = page(components, cursor=cursor, **kwargs)
        pages.append(current)
        for record in current["components"]:
            if isinstance(record, dict) and "identity" in record:
                seen.append(record["identity"]["feature_id"])
        cursor = current.get("next_cursor")
        if cursor is None:
            break
        if len(pages) > 100:
            raise AssertionError("paging did not terminate")
    return pages, seen


class SmallListTests(unittest.TestCase):
    def test_a_list_that_fits_keeps_the_historical_shape(self):
        records = [component(1), component(2)]
        result = page(records, aliases={"part_1": {"op": "assemble_component", "feature_id": 1}})
        self.assertEqual(
            set(result),
            {"model_id", "revision", "components", "deleted_identities", "identity_key", "aliases"},
        )
        self.assertEqual(len(result["components"]), 2)
        self.assertEqual(result["aliases"]["part_1"]["feature_id"], 1)

    def test_empty_list_is_still_an_empty_list_not_a_page(self):
        result = page([])
        self.assertEqual(result["components"], [])
        self.assertNotIn("next_cursor", result)


class PagedListTests(unittest.TestCase):
    def test_269_components_page_without_duplicates_or_gaps(self):
        records = many()
        pages, seen = walk(records, limit=50)
        self.assertGreater(len(pages), 1)
        self.assertEqual(len(seen), 269)
        self.assertEqual(len(set(seen)), 269)
        self.assertEqual(seen, list(range(1, 270)))
        self.assertTrue(pages[-1]["complete"])
        self.assertIsNone(pages[-1]["next_cursor"])
        for index, current in enumerate(pages):
            self.assertEqual(current["total"], 269)
            self.assertFalse(current["complete"] and index != len(pages) - 1)
            self.assertLessEqual(serialized_size(current), RESPONSE_BUDGET)
            self.assertEqual(current["returned_count"], len(current["components"]))

    def test_two_instances_of_one_source_model_keep_distinct_occurrences(self):
        records = many()
        pages, seen = walk(records, limit=50)
        returned = [
            record
            for current in pages
            for record in current["components"]
            if isinstance(record, dict) and "identity" in record
        ]
        identities = [record["identity"] for record in returned]
        self.assertEqual([item["feature_id"] for item in identities], list(range(1, 270)))
        # Every occurrence points at the same source model but keeps its own
        # component identity; a page never merges two instances into one.
        self.assertEqual({record["source_model_id"] for record in returned}, {SOURCE})
        self.assertEqual(len({item["feature_id"] for item in identities}), 269)
        self.assertEqual(seen, list(range(1, 270)))

    def test_aliases_and_deleted_identities_ride_the_first_page_only(self):
        pages, _ = walk(
            many(),
            limit=10,
            aliases={"part_1": {"op": "assemble_component", "feature_id": 1}},
            deleted_identities=[{"identity": {"model_id": "a" * 32, "feature_id": 999}}],
        )
        self.assertGreater(len(pages), 1)
        self.assertIn("aliases", pages[0])
        self.assertIn("deleted_identities", pages[0])
        self.assertNotIn("aliases", pages[1])
        self.assertNotIn("deleted_identities", pages[1])

    def test_revision_change_invalidates_the_cursor(self):
        records = many()
        first = page(records, limit=10)
        with self.assertRaises(ValueError) as caught:
            page(records, limit=10, cursor=first["next_cursor"], revision=4)
        self.assertIn("restart the query", str(caught.exception))

    def test_a_different_field_projection_invalidates_the_cursor(self):
        records = many()
        first = page(records, limit=10, fields=["identity"])
        with self.assertRaises(ValueError) as caught:
            page(records, limit=10, fields=["identity", "name"], cursor=first["next_cursor"])
        self.assertIn("restart the query", str(caught.exception))

    def test_changed_records_at_the_same_revision_also_invalidate_the_cursor(self):
        records = many()
        first = page(records, limit=10)
        records[0]["transform"][0] = 2.0
        with self.assertRaises(ValueError) as caught:
            page(records, limit=10, cursor=first["next_cursor"])
        self.assertIn("restart the query", str(caught.exception))

    def test_an_oversized_record_becomes_a_marker_not_a_truncation(self):
        records = [component(1), component(2, payload="x" * 40000), component(3)]
        pages, _ = walk(records, limit=10)
        flat = [record for current in pages for record in current["components"]]
        self.assertEqual(len(flat), 3)
        marker = flat[1]
        self.assertTrue(marker["oversize"])
        self.assertEqual(marker["index"], 1)
        self.assertGreater(marker["size_hint_bytes"], 30000)
        self.assertNotIn("payload", marker)


class FieldsTests(unittest.TestCase):
    def test_projection_returns_only_the_requested_keys(self):
        records = [component(index) for index in range(1, 40)]
        result = page(records, limit=5, fields=["identity", "label"])
        self.assertEqual(set(result["components"][0]), {"identity", "label"})
        self.assertEqual(result["fields"], ["identity", "label"])
        self.assertEqual(result["total"], 39)

    def test_unknown_field_lists_the_available_ones(self):
        with self.assertRaises(ValueError) as caught:
            page([component(1)], fields=["transform_matrix"])
        message = str(caught.exception)
        self.assertIn("unknown component field", message)
        self.assertIn("identity", message)

    def test_field_list_shape_is_refused(self):
        for fields in ([], "identity", ["identity", "identity"], [1]):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                page([component(1)], fields=fields)

    def test_limit_bounds_are_refused(self):
        for limit in (0, 201, True, "5", 2.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                page([component(1)], limit=limit)


class ServerSchemaTests(unittest.TestCase):
    def test_the_public_tool_exposes_fields_limit_and_cursor(self):
        tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
        properties = tools["creo_list_components"].input_schema["properties"]
        self.assertIn("fields", properties)
        self.assertIn("cursor", properties)
        self.assertEqual(properties["limit"]["default"], 50)
        self.assertEqual(properties["limit"]["maximum"], 200)


if __name__ == "__main__":
    unittest.main()
