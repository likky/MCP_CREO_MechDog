"""FEAT-069 G1: region signature parsing and unique YZ matching."""

import unittest

from creo_mechdog.region_selection import (
    match_region,
    parse_region_signature,
    region_yz_segments,
    sketch_point_to_yz,
    validate_yz_sketch_frame,
)

FRAME = {
    "origin": [1.5, 0, 0],
    "xdir": [0, 0, -1],
    "ydir": [0, 1, 0],
}

# Verbatim Arm7-S7 [B-REGION] lines from the archived 0.25.0 feedback.
REGION_0 = (
    "(-4.988707,-11.335864|-1.173416,-14.314501;"
    "-4.988707,-11.335864|3.653839,-14.413131;"
    "-1.173416,-14.314501|3.665824,-14.400255;"
    "3.653839,-14.413131|3.665824,-14.400255)"
)
REGION_1 = (
    "(8.520784,-45.311209|13.237871,-43.399633;"
    "8.520784,-45.311209|14.17272,-30.529286;"
    "13.237871,-43.399633|16.37991,-35.975847;"
    "14.17272,-30.529286|16.37991,-35.975847)"
)
REGION_2 = (
    "(3.653839,-14.413131|3.665824,-14.400255;"
    "3.653839,-14.413131|8.911922,-27.388205;"
    "3.665824,-14.400255|8.520784,-45.311209;"
    "4.765011,-36.043298|5.348889,-35.806684;"
    "4.765011,-36.043298|8.520784,-45.311209;"
    "5.348889,-35.806684|8.911922,-27.388205)"
)

REGIONS = [
    {"name": "0", "signature_yz_mm": REGION_0},
    {"name": "1", "signature_yz_mm": REGION_1},
    {"name": "2", "signature_yz_mm": REGION_2},
]


class RegionSignatureTests(unittest.TestCase):
    def test_real_region_lines_parse(self):
        self.assertEqual(len(parse_region_signature(REGION_0)), 4)
        self.assertEqual(len(parse_region_signature(REGION_1)), 4)
        self.assertEqual(len(parse_region_signature(REGION_2)), 6)

    def test_frame_maps_the_txt_point(self):
        # [B-GEO] i=0 arc x1=11.335863926 y1=-4.988706789 -> global (y,z)
        self.assertEqual(
            sketch_point_to_yz(FRAME, [11.335863926, -4.988706789]),
            (-4.988706789, -11.335863926),
        )

    def test_frame_must_match_the_txt_orientation(self):
        for frame in (
            {**FRAME, "origin": [0, 0, 0]},
            {**FRAME, "xdir": [0, 0, 1]},
            {**FRAME, "ydir": [1, 0, 0]},
            {**FRAME, "xdir": [0, 0, -2]},
        ):
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                validate_yz_sketch_frame(frame)

    def test_each_real_region_matches_exactly_one_candidate(self):
        for expected, signature in (("0", REGION_0), ("1", REGION_1), ("2", REGION_2)):
            with self.subTest(region=expected):
                matched = match_region(signature, REGIONS, tolerance=1e-6)
                self.assertEqual(matched["region"], expected)
                self.assertEqual(matched["segments"], len(parse_region_signature(signature)))

    def test_endpoint_and_segment_order_do_not_matter(self):
        reordered = (
            "(3.665824,-14.400255|3.653839,-14.413131;"
            "-1.173416,-14.314501|-4.988707,-11.335864;"
            "3.665824,-14.400255|-1.173416,-14.314501;"
            "3.653839,-14.413131|-4.988707,-11.335864)"
        )
        self.assertEqual(match_region(reordered, REGIONS, tolerance=1e-6)["region"], "0")

    def test_local_segments_map_through_the_frame(self):
        # A 20 x 10 local rectangle becomes y in [0,10], z in [-20,0].
        region = {
            "name": "bottom",
            "frame": FRAME,
            "segments": [
                [[0, 0], [20, 0]],
                [[20, 0], [20, 10]],
                [[20, 10], [0, 10]],
                [[0, 10], [0, 0]],
            ],
        }
        signature = "(0,0|0,-20;0,-20|10,-20;10,-20|10,0;10,0|0,0)"
        self.assertEqual(match_region(signature, [region], tolerance=1e-6)["region"], "bottom")
        self.assertEqual(len(region_yz_segments(region)), 4)

    def test_duplicate_segments_are_refused(self):
        with self.assertRaises(ValueError):
            parse_region_signature("(0,0|0,1;0,1|0,0)")

    def test_malformed_signatures_are_refused(self):
        for bad in (
            "0,0|0,1",
            "(0,0|0,1;)",
            "(0,0|0,1;1,1)",
            "(0,0|0,1,2)",
            "(0,0|0,nan)",
            "(0,0|0,1;0,0|0,1;)",
            "(0,0|0,0)",
            "",
        ):
            with self.subTest(signature=bad), self.assertRaises(ValueError):
                parse_region_signature(bad)

    def test_zero_and_multiple_matches_are_refused(self):
        missing = "(100,100|100,101;101,101|100,101)"
        with self.assertRaisesRegex(ValueError, "matched none"):
            match_region(missing, REGIONS)
        duplicated = [REGIONS[0], {**REGIONS[0], "name": "copy"}]
        with self.assertRaisesRegex(ValueError, "more than one"):
            match_region(REGION_0, duplicated)

    def test_region_index_hint_is_not_used(self):
        # The TXT hint is 4,2,5 while the names are 0,1,2; matching must follow
        # geometry, not the hint or the order in the list.
        hinted = [{**region, "region_index_hint": 4} for region in reversed(REGIONS)]
        self.assertEqual(match_region(REGION_2, hinted, tolerance=1e-6)["region"], "2")

    def test_tolerance_bounds_the_comparison(self):
        nudged = REGION_0.replace("-4.988707", "-4.9887075")
        self.assertEqual(match_region(nudged, REGIONS, tolerance=1e-6)["region"], "0")
        with self.assertRaisesRegex(ValueError, "matched none"):
            match_region(nudged, REGIONS, tolerance=1e-9)
        for bad in (0, -1, 11):
            with self.subTest(tolerance=bad), self.assertRaises(ValueError):
                match_region(REGION_0, REGIONS, tolerance=bad)


if __name__ == "__main__":
    unittest.main()
