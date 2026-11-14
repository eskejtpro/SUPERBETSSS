import tempfile
import unittest
from pathlib import Path

import app


def sample_match(home_score=4, away_score=1, key="match-1", observed_at=None):
    observed_at = observed_at or app.utc_now()
    return {
        "key": key, "observed_at": observed_at, "home": "Alpha", "away": "Beta",
        "competition": "Test League", "home_score": home_score, "away_score": away_score,
        "half": 2, "clock_label": "08:15", "started_at": observed_at,
        "source_url": "https://example.test/match",
    }


class AdvantageHistoryTests(unittest.TestCase):
    def test_three_goal_lead_is_archived(self):
        with tempfile.TemporaryDirectory() as directory:
            db = app.MatchDatabase(Path(directory) / "history.sqlite3")
            self.assertEqual(db.record_advantage_events([sample_match()], 3), 1)
            rows = db.advantage_history()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["leader_at_trigger"], "Alpha")
            self.assertEqual(rows[0]["max_goal_difference"], 3)
            self.assertEqual(rows[0]["score_at_trigger"], "4:1")

    def test_matches_below_threshold_are_not_archived(self):
        with tempfile.TemporaryDirectory() as directory:
            db = app.MatchDatabase(Path(directory) / "history.sqlite3")
            self.assertEqual(db.record_advantage_events([sample_match(3, 1)], 3), 0)
            self.assertEqual(db.advantage_history(), [])

    def test_archive_keeps_largest_lead_and_updates_latest_score(self):
        with tempfile.TemporaryDirectory() as directory:
            db = app.MatchDatabase(Path(directory) / "history.sqlite3")
            db.record_advantage_events([sample_match(4, 1)], 3)
            db.record_advantage_events([sample_match(6, 1, observed_at=app.utc_now())], 3)
            db.record_advantage_events([sample_match(5, 3, observed_at=app.utc_now())], 3)
            rows = db.advantage_history()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["max_goal_difference"], 5)
            self.assertEqual(rows[0]["score_at_trigger"], "6:1")
            self.assertEqual(rows[0]["latest_score"], "5:3")

    def test_archive_can_be_cleared(self):
        with tempfile.TemporaryDirectory() as directory:
            db = app.MatchDatabase(Path(directory) / "history.sqlite3")
            db.record_advantage_events([sample_match()], 3)
            self.assertEqual(db.clear_advantage_history(), 1)
            self.assertEqual(db.advantage_history(), [])


if __name__ == "__main__":
    unittest.main()
