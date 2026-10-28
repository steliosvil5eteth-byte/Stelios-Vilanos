import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from history_guard import check

class HistoryGuardTests(unittest.TestCase):
    def test_exact_title_duplicate(self):
        result = check([{"title":"Η συνταγή του πατέρα","opening":"Άνοιγμα","plot_key":"new"}], [{"Title":"Η συνταγή του πατέρα","Hook":"Άλλο","Fingerprint":"old"}], True)
        self.assertFalse(result["clear"])
        self.assertEqual(result["matches"][0]["field"], "title")

    def test_accents_and_punctuation(self):
        self.assertFalse(check([{"title":"Η Συνταγή, του Πατέρα!","opening":"α","plot_key":"β"}], [{"Title":"η συνταγη του πατερα"}], True)["clear"])

    def test_incomplete_archive_blocks(self):
        self.assertFalse(check([{"title":"a","opening":"b","plot_key":"c"}], [], False)["clear"])

    def test_complete_nonmatching_archive(self):
        self.assertTrue(check([{"title":"unrelated story alpha","opening":"different intro","plot_key":"unique plot"}], [{"Title":"completely other words","Hook":"another hook","Fingerprint":"another plot"}], True)["clear"])

    def test_missing_candidate_fields_blocks(self):
        self.assertFalse(check([{"title":"a"}], [], True)["clear"])

    def test_invalid_archive_blocks(self):
        self.assertFalse(check([{"title":"a","opening":"b","plot_key":"c"}], {}, True)["clear"])
