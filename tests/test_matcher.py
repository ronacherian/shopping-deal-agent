"""Unit tests for DealMatcher specification extraction and criteria verification."""
import unittest
from src.models import RawListing
from src.matcher import DealMatcher

class TestDealMatcher(unittest.TestCase):
    def setUp(self):
        self.matcher = DealMatcher()

    def test_valid_m3_pro_match(self):
        listing = RawListing(
            id="test_1",
            source="TestStore",
            title="Apple MacBook Pro 14-inch M3 Pro 24GB Unified Memory 1TB SSD Space Black",
            price=1849.00,
            url="https://example.com/item1"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertTrue(is_match)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.ram_gb, 24)
        self.assertEqual(parsed.storage_gb, 1000)
        self.assertIn("M3 Pro", parsed.chip)
        self.assertEqual(parsed.screen_size, '14"')

    def test_valid_m4_match(self):
        listing = RawListing(
            id="test_m4",
            source="TestStore",
            title="Apple MacBook Pro 14-inch M4 Pro 24GB RAM 1TB SSD Space Black",
            price=1899.00,
            url="https://example.com/item_m4"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertTrue(is_match)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.ram_gb, 24)
        self.assertEqual(parsed.storage_gb, 1000)
        self.assertIn("M4 Pro", parsed.chip)

    def test_valid_m3_max_36gb_match(self):
        listing = RawListing(
            id="test_m3_max",
            source="TestStore",
            title="Apple 14\" MacBook Pro M3 Max 36GB 1TB SSD Liquid Retina XDR",
            price=1950.00,
            url="https://example.com/item_max"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertTrue(is_match)
        self.assertEqual(parsed.ram_gb, 36)
        self.assertEqual(parsed.storage_gb, 1000)

    def test_valid_m3_pro_48gb_2tb_match(self):
        listing = RawListing(
            id="test_48gb_2tb",
            source="TestStore",
            title="MacBook Pro 16-inch M3 Pro 48GB RAM 2TB SSD Silver",
            price=1980.00,
            url="https://example.com/item_2tb"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertTrue(is_match)
        self.assertEqual(parsed.ram_gb, 48)
        self.assertEqual(parsed.storage_gb, 2000)
        self.assertEqual(parsed.screen_size, '16"')

    def test_reject_low_ram(self):
        listing = RawListing(
            id="test_low_ram",
            source="TestStore",
            title="Apple MacBook Pro 14 M3 16GB Unified Memory 1TB SSD Space Gray",
            price=1599.00,
            url="https://example.com/low_ram"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertFalse(is_match)
        self.assertIsNone(parsed)

    def test_reject_low_ram_18gb(self):
        listing = RawListing(
            id="test_18gb",
            source="TestStore",
            title="Apple MacBook Pro 14 M3 Pro 18GB Memory 1TB SSD",
            price=1699.00,
            url="https://example.com/18gb"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertFalse(is_match)

    def test_reject_low_storage_512gb(self):
        listing = RawListing(
            id="test_512gb",
            source="TestStore",
            title="Apple MacBook Pro 14 M3 Pro 36GB Memory 512GB SSD",
            price=1799.00,
            url="https://example.com/512gb"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertFalse(is_match)

    def test_reject_old_m2_generation(self):
        listing = RawListing(
            id="test_m2",
            source="TestStore",
            title="Apple MacBook Pro 14 M2 Pro 32GB RAM 1TB SSD Space Gray",
            price=1499.00,
            url="https://example.com/m2"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertFalse(is_match)

    def test_reject_old_m1_generation(self):
        listing = RawListing(
            id="test_m1",
            source="TestStore",
            title="Apple MacBook Pro 16 M1 Max 32GB RAM 1TB SSD",
            price=1399.00,
            url="https://example.com/m1"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertFalse(is_match)

    def test_reject_price_exceeds_ceiling(self):
        listing = RawListing(
            id="test_expensive",
            source="TestStore",
            title="Apple MacBook Pro 16 M3 Max 36GB 1TB SSD Space Black",
            price=2499.00,
            url="https://example.com/expensive"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertFalse(is_match)

    def test_reject_suspiciously_cheap_or_accessories(self):
        listing = RawListing(
            id="test_case",
            source="TestStore",
            title="Hard Shell Case for Apple MacBook Pro 14 inch M3 Pro Max",
            price=24.99,
            url="https://example.com/case"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertFalse(is_match)

    def test_reject_macbook_air(self):
        listing = RawListing(
            id="test_air",
            source="TestStore",
            title="Apple MacBook Air 15 M3 24GB Unified Memory 1TB SSD",
            price=1699.00,
            url="https://example.com/air"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertFalse(is_match)

    def test_reject_broken_or_parts_only(self):
        listing = RawListing(
            id="test_broken",
            source="TestStore",
            title="Apple MacBook Pro 14 M3 Pro 36GB 1TB SSD - FOR PARTS ONLY BROKEN SCREEN",
            price=799.00,
            url="https://example.com/broken"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertFalse(is_match)

    def test_screen_size_detection_16_inch(self):
        listing = RawListing(
            id="test_16inch",
            source="TestStore",
            title="Apple MacBook Pro 16-inch M3 Pro 36GB 1TB SSD",
            price=1949.00,
            url="https://example.com/16inch"
        )
        is_match, parsed = self.matcher.fast_filter(listing)
        self.assertTrue(is_match)
        self.assertEqual(parsed.screen_size, '16"')

if __name__ == "__main__":
    unittest.main()
