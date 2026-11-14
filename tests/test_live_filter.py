import tempfile
import unittest
from pathlib import Path
import app


LIVE = {
    "home": "Player A", "away": "Player B", "half": 1, "clock": 125,
    "clockLabel": "2'", "homeScore": 1, "awayScore": 0, "status": "aktywny",
    "url": "https://superbet.pl/zaklady-bukmacherskie/e-pilka-nozna/live/test",
}


class LiveOnlyTests(unittest.TestCase):
    def test_live_match_is_normalized(self):
        match = app.normalize_match(LIVE, app.utc_now())
        self.assertTrue(match["is_live"])
        self.assertEqual(match["half"], 1)

    def test_pre_match_without_half_is_rejected(self):
        with self.assertRaises(ValueError):
            app.normalize_match({**LIVE, "half": None, "clock": None}, app.utc_now())

    def test_match_without_clock_is_rejected(self):
        with self.assertRaises(ValueError):
            app.normalize_match({**LIVE, "clock": None}, app.utc_now())

    def test_only_live_matches_enter_current_state(self):
        with tempfile.TemporaryDirectory() as directory:
            database = app.MatchDatabase(Path(directory) / "test.sqlite3")
            state = app.LiveState(database)
            accepted = state.ingest([LIVE, {**LIVE, "half": None, "clock": None}])
            self.assertEqual(accepted, 1)
            payload = state.live_payload()
            self.assertEqual(payload["count"], 1)
            self.assertTrue(payload["matches"][0]["is_live"])


if __name__ == "__main__":
    unittest.main()
