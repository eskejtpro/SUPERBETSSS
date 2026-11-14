import unittest
from datetime import datetime, timedelta, timezone

import app


class MatchExpiryTests(unittest.TestCase):
    def test_match_is_expired_after_estimated_remaining_time(self):
        now = datetime.now(timezone.utc)
        match = {
            "remaining_seconds": 60,
            "observed_at": (now - timedelta(seconds=61)).isoformat(),
        }
        self.assertTrue(app.match_is_expired(match, now))

    def test_match_is_kept_before_estimated_end(self):
        now = datetime.now(timezone.utc)
        match = {
            "remaining_seconds": 60,
            "observed_at": (now - timedelta(seconds=59)).isoformat(),
        }
        self.assertFalse(app.match_is_expired(match, now))

    def test_zero_remaining_is_removed_immediately(self):
        self.assertTrue(app.match_is_expired({"remaining_seconds": 0}))

    def test_unknown_match_duration_is_not_guessed(self):
        self.assertFalse(app.match_is_expired({"remaining_seconds": None}))


if __name__ == "__main__":
    unittest.main()
