#!/usr/bin/env python3
import html
import os
import sys
import urllib.request
from pathlib import Path

region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
if not region or not key:
    raise SystemExit("Missing Azure Speech secrets")

text_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
text = text_path.read_text(encoding="utf-8").strip()
if not text:
    raise SystemExit("Empty demo text")

ssml = f"""<speak version="1.0" xml:lang="el-GR">
<voice name="el-GR-NestorasNeural"><prosody rate="0%" pitch="0%">{html.escape(text)}</prosody></voice>
</speak>""".encode("utf-8")

url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
req = urllib.request.Request(
    url,
    data=ssml,
    method="POST",
    headers={
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
        "User-Agent": "SteliosNestorasDemo/1.0",
    },
)
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        audio = resp.read()
except Exception as exc:
    raise SystemExit(f"Azure Speech request failed: {exc.__class__.__name__}") from exc

if len(audio) < 1000 or not audio.startswith(b"RIFF"):
    raise SystemExit("Azure Speech returned an invalid audio payload")

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_bytes(audio)
print("Azure Nestoras synthesis succeeded")
