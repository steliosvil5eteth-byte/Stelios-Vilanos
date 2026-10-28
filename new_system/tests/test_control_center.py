"""Offline tests: python3 -m unittest discover -s new_system/tests -v"""
import copy
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from control_center import audit

CATS = (["emotional_story"] * 5 + ["greek_fictional_myth", "zodiac",
        "general_comparison", "greece_two_years", "name_day_greetings"])

def valid_manifest():
    items = []
    for i, category in enumerate(CATS):
        item = dict(id=f"unique-{i}", category=category, title=f"Title {i}",
                    opening=f"Opening {i}", ending=f"Ending {i}",
                    plot_key=f"plot-{i}", source_status="verified",
                    qa_status="approved", cost_eur=0, published=False)
        if category == "greek_fictional_myth":
            item["fiction_disclosure"] = True
        items.append(item)
    return dict(brand_id=7076410, timezone="Europe/Athens", items=items,
                history_checked=True, calendar_verified=True,
                manual_review_confirmed=True)

class ControlCenterTests(unittest.TestCase):
    def test_empty_fails_closed(self):
        self.assertFalse(audit(dict(brand_id=7076410, timezone="Europe/Athens", items=[]))["ready"])

    def test_valid_fixture_is_review_ready_not_published(self):
        result = audit(valid_manifest())
        self.assertTrue(result["ready"], result["errors"])
        self.assertFalse(result["publishing_enabled"])

    def test_duplicate_plot_blocks(self):
        m = valid_manifest()
        m["items"][1]["plot_key"] = m["items"][0]["plot_key"]
        self.assertIn("Repeated plot_key detected", audit(m)["errors"])

    def test_wrong_category_count_blocks(self):
        m = valid_manifest()
        m["items"][0]["category"] = "zodiac"
        self.assertFalse(audit(m)["ready"])

    def test_unverified_factual_sources_block(self):
        m = valid_manifest()
        m["items"][-1]["source_status"] = "unknown"
        self.assertFalse(audit(m)["ready"])

    def test_missing_fiction_disclosure_blocks(self):
        m = valid_manifest()
        m["items"][5].pop("fiction_disclosure")
        self.assertFalse(audit(m)["ready"])

    def test_paid_item_blocks(self):
        m = valid_manifest()
        m["items"][0]["cost_eur"] = 1
        self.assertFalse(audit(m)["ready"])

    def test_missing_qa_blocks(self):
        m = valid_manifest()
        m["items"][0]["qa_status"] = "draft"
        self.assertFalse(audit(m)["ready"])

    def test_no_history_check_blocks(self):
        m = valid_manifest()
        m["history_checked"] = False
        self.assertFalse(audit(m)["ready"])

    def test_no_calendar_check_blocks(self):
        m = valid_manifest()
        m["calendar_verified"] = False
        self.assertFalse(audit(m)["ready"])

    def test_no_manual_review_blocks(self):
        m = valid_manifest()
        m["manual_review_confirmed"] = False
        self.assertFalse(audit(m)["ready"])

    def test_wrong_brand_blocks(self):
        m = valid_manifest()
        m["brand_id"] = 7000636
        self.assertFalse(audit(m)["ready"])

if __name__ == "__main__":
    unittest.main()
