import tempfile
import unittest
from pathlib import Path

import app


LIVE = {
    "home": "Player A",
    "away": "Player B",
    "half": 1,
    "clock": 240,
    "clockLabel": "4:00",
    "homeScore": 2,
    "awayScore": 0,
    "status": "aktywny",
    "formatMinutes": 20,
    "url": "https://superbet.pl/zaklady-bukmacherskie/e-pilka-nozna/live/enhancement-test",
}


class LiveEnhancementTests(unittest.TestCase):
    def test_extra_time_and_first_half_break_are_included(self):
        remaining = app.remaining_seconds({
            "format_minutes": 20,
            "half": 1,
            "clock_seconds": 240,
            "added_time_seconds": 30,
            "break_seconds": 60,
        })
        self.assertEqual(remaining, 17 * 60 + 30)

    def test_normalized_match_has_start_and_estimated_end(self):
        match = app.normalize_match(
            {**LIVE, "addedTimeSeconds": 30, "breakSeconds": 45},
            app.utc_now(),
        )
        self.assertEqual(match["added_time_seconds"], 30)
        self.assertEqual(match["break_seconds"], 45)
        self.assertIsNotNone(match["started_at"])
        self.assertIsNotNone(match["estimated_end_at"])
        self.assertEqual(match["remaining_seconds"], 16 * 60 + 30 + 45)

    def test_new_highlight_and_notification_settings_are_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = app.SettingsStore(Path(directory) / "settings.json")
            saved = store.update({
                "potential_enabled": False,
                "potential_goal_difference": 3,
                "potential_color": "#123abc",
                "notify_enabled": False,
                "notify_cooldown_seconds": 300,
            })
            self.assertFalse(saved["potential_enabled"])
            self.assertEqual(saved["potential_goal_difference"], 3)
            self.assertEqual(saved["potential_color"], "#123abc")
            self.assertFalse(saved["notify_enabled"])
            self.assertEqual(saved["notify_cooldown_seconds"], 300)

    def test_invalid_color_and_out_of_range_settings_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = app.SettingsStore(Path(directory) / "settings.json")
            saved = store.update({
                "potential_color": "red",
                "potential_remaining_seconds": 99999,
                "notify_cooldown_seconds": -1,
            })
            self.assertEqual(saved["potential_color"], "#f59e0b")
            self.assertEqual(saved["potential_remaining_seconds"], 300)
            self.assertEqual(saved["notify_cooldown_seconds"], 120)


if __name__ == "__main__":
    unittest.main()
