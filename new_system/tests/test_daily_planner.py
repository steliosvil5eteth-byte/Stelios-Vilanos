"""Regression tests for the isolated ten-slot offline planner."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from daily_planner import build, SLOTS

class DailyPlannerTests(unittest.TestCase):
    def test_ten_slots(self):
        self.assertEqual(len(build("2026-10-29")["items"]), 10)
    def test_all_categories(self):
        from collections import Counter
        actual = Counter(x["category"] for x in build("2026-10-29")["items"])
        self.assertEqual(actual["emotional_story"], 5)
        for cat in ("zodiac", "general_comparison", "greek_fictional_myth", "greece_two_years", "name_day_greetings"):
            self.assertEqual(actual[cat], 1)
    def test_all_blocked_and_zero_cost(self):
        d = build("2026-10-29")
        self.assertFalse(d["publishing_enabled"])
        self.assertFalse(d["history_checked"])
        self.assertTrue(all(x["status"].startswith("BLOCKED") and x["cost_eur"] == 0 for x in d["items"]))
    def test_unique_ids(self):
        ids = [x["id"] for x in build("2026-10-29")["items"]]
        self.assertEqual(len(ids), len(set(ids)))
    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            build("2026-02-30")
if __name__ == "__main__":
    unittest.main()
