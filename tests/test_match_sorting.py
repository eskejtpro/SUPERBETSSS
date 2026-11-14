import unittest
import app


class RemainingTimeTests(unittest.TestCase):
    def test_first_half_includes_current_and_second_half(self):
        self.assertEqual(app.remaining_seconds({"format_minutes": 20, "half": 1, "clock_seconds": 240}), 16 * 60)

    def test_second_half_only_counts_remainder_of_second_half(self):
        self.assertEqual(app.remaining_seconds({"format_minutes": 20, "half": 2, "clock_seconds": 240}), 6 * 60)

    def test_missing_format_is_unknown(self):
        self.assertIsNone(app.remaining_seconds({"format_minutes": None, "half": 2, "clock_seconds": 240}))

    def test_clock_beyond_half_duration_is_unknown(self):
        self.assertIsNone(app.remaining_seconds({"format_minutes": 20, "half": 2, "clock_seconds": 700}))

    def test_sort_places_soonest_match_first_and_unknown_last(self):
        matches = [
            {"remaining_seconds": None, "home": "A", "key": "a"},
            {"remaining_seconds": 6 * 60, "home": "B", "key": "b"},
            {"remaining_seconds": 16 * 60, "home": "C", "key": "c"},
        ]
        matches.sort(key=app.LiveState._remaining_sort_key)
        self.assertEqual([item["key"] for item in matches], ["b", "c", "a"])


if __name__ == "__main__":
    unittest.main()
