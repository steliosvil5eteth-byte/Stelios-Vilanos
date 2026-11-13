import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from video_finisher import validate


class FailClosedTests(unittest.TestCase):
    def test_reject_unknown_fps(self):
        with self.assertRaisesRegex(ValueError, "30 FPS"):
            validate({"schema_version": 1, "fps": 25}, Path("."))

    def test_reject_missing_manifest_schema(self):
        with self.assertRaisesRegex(ValueError, "schema_version"):
            validate({"fps": 30}, Path("."))

    def test_reject_missing_narration(self):
        with self.assertRaises(ValueError):
            validate({"schema_version": 1, "fps": 30, "narration_file":"does-not-exist.mp3", "scenes":[]}, Path("."))


if __name__ == "__main__":
    unittest.main()