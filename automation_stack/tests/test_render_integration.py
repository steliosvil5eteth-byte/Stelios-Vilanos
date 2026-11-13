"""Smoke render with synthetic fixtures. No publishing/network/secrets."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from video_finisher import finish, probe


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg missing')
class RenderSmokeTest(unittest.TestCase):
    def test_real_video_thirty_cfr_and_review_blocked(self):
        with tempfile.TemporaryDirectory(prefix='n8n_smoke_') as d:
            root=Path(d)
            for index, color in enumerate(['red', 'blue'],1):
                subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i',f'color=c={color}:s=512x512:d=1','-frames:v','1',str(root/f'scene{index}.jpg')],check=True)
            subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i','sine=frequency=425:duration=2.0',str(root/'voice.wav')],check=True)
            src=probe(root/'voice.wav')
            duration=float(src['format']['duration'])
            manifest={'schema_version':1,'fps':30,'size':512,'narration_file':'voice.wav','scenes':[{'image_file':'scene1.jpg','start_s':0,'end_s':1},{'image_file':'scene2.jpg','start_s':1,'end_s':duration}]}
            (root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            report=finish(root/'manifest.json',root,root/'result.mp4',root/'qa.json')
            self.assertEqual(report['fps'],30)
            self.assertEqual(report['technical_decode'],'PASSED')
            self.assertEqual(report['final_review'],'BLOCKED')
            self.assertFalse(report['scheduling_authorized'])
            self.assertEqual(report['video_frames'],round(duration*30))


if __name__=='__main__': unittest.main()