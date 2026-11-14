import tempfile
import unittest
from pathlib import Path
import app


class HighlightSettingsTests(unittest.TestCase):
    def test_defaults_enable_three_goal_and_90_second_highlight(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = app.SettingsStore(Path(directory) / "settings.json").get()
        self.assertTrue(settings["highlight_enabled"])
        self.assertEqual(settings["highlight_goal_difference"], 3)
        self.assertEqual(settings["highlight_remaining_seconds"], 90)

    def test_user_can_customize_thresholds(self):
        with tempfile.TemporaryDirectory() as directory:
            store = app.SettingsStore(Path(directory) / "settings.json")
            saved = store.update({"highlight_enabled": True, "highlight_goal_difference": 4, "highlight_remaining_seconds": 60})
            self.assertEqual(saved["highlight_goal_difference"], 4)
            self.assertEqual(saved["highlight_remaining_seconds"], 60)

    def test_invalid_thresholds_are_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = app.SettingsStore(Path(directory) / "settings.json")
            saved = store.update({"highlight_goal_difference": 0, "highlight_remaining_seconds": 9999})
            self.assertEqual(saved["highlight_goal_difference"], 3)
            self.assertEqual(saved["highlight_remaining_seconds"], 90)


if __name__ == "__main__":
    unittest.main()
