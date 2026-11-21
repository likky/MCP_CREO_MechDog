"""BUG-140: modern build caches must not expand legacy line-ending candidates."""

import unittest
from unittest.mock import Mock, patch

import bridge
from creo_mechdog import build_fingerprints as fingerprints
from tests.unit import test_build_fingerprints as fingerprint_tests


class Bug140FingerprintMatchingTests(unittest.TestCase):
    def test_legacy_factory_runs_only_for_a_plausible_legacy_cache(self):
        current = "c" * 64
        legacy = "l" * 64
        factory = Mock(return_value={legacy})
        modern = {
            "algorithm": fingerprints.FINGERPRINT_ALGORITHM,
            "fingerprint": current,
        }
        self.assertEqual(
            fingerprints.match_cached_fingerprint(modern, current, factory),
            (True, current),
        )
        self.assertEqual(
            fingerprints.match_cached_fingerprint(
                {**modern, "fingerprint": "x" * 64}, current, factory
            ),
            (False, None),
        )
        for cache in (None, {}, {"fingerprint": 123}):
            self.assertEqual(
                fingerprints.match_cached_fingerprint(cache, current, factory),
                (False, None),
            )
        factory.assert_not_called()

        self.assertEqual(
            fingerprints.match_cached_fingerprint({"fingerprint": legacy}, current, factory),
            (True, legacy),
        )
        self.assertEqual(
            fingerprints.match_cached_fingerprint({"fingerprint": "z" * 64}, current, factory),
            (False, None),
        )
        self.assertEqual(factory.call_count, 2)

    def test_abnormal_legacy_snapshot_is_conservatively_not_expanded(self):
        snapshot = {f"dependency_{index}.h": b"value\n" for index in range(9)}
        with patch.object(
            fingerprints.itertools,
            "product",
            side_effect=AssertionError("abnormal snapshot reached Cartesian expansion"),
        ):
            self.assertEqual(fingerprints.legacy_digest_candidates(b"p", b"abi", snapshot), set())


class Bug140BridgeCacheTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fingerprint_tests.BuildNativeMigrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        bridge.build_native()

    def test_modern_cache_hit_does_not_call_legacy_generator(self):
        with patch.object(
            bridge,
            "legacy_digest_candidates",
            side_effect=AssertionError("modern cache hit expanded legacy candidates"),
        ) as generator:
            bridge.build_native()
        generator.assert_not_called()
        self.assertEqual(self.fixture.compiles, 1)

    def test_modern_cache_mismatch_does_not_call_legacy_generator(self):
        source = self.fixture.native / "blend_sync.cpp"
        source.write_bytes(source.read_bytes() + b"// changed\n")
        with patch.object(
            bridge,
            "legacy_digest_candidates",
            side_effect=AssertionError("modern cache mismatch expanded legacy candidates"),
        ) as generator:
            bridge.build_native()
        generator.assert_not_called()
        self.assertEqual(self.fixture.compiles, 2)


if __name__ == "__main__":
    unittest.main()
