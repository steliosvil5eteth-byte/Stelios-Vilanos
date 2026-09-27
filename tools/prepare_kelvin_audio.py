from pathlib import Path
import json,sys
sys.path.insert(0,"tools")
from render_azure_feature_batch import synthesize,subtitles
j=json.loads(Path("media_jobs/kelvin_20260929.json").read_text())
out=Path("audio-review");out.mkdir(exist_ok=True)
wav,bounds,dur=synthesize(j["script"],out,80,180)
subtitles(bounds,dur,out/"subs.srt")
(out/"bounds.json").write_text(json.dumps(bounds,ensure_ascii=False))
(out/"meta.json").write_text(json.dumps({"duration":dur,"voice":j["voice"],"background_music":False}))
from faster_whisper import WhisperModel
model=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=4)
segs,info=model.transcribe(str(wav),language="el",beam_size=5,word_timestamps=True)
(out/"transcript.json").write_text(json.dumps([{"start":s.start,"end":s.end,"text":s.text} for s in segs],ensure_ascii=False,indent=2))
