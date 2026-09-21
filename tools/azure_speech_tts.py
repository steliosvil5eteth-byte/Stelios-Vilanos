#!/usr/bin/env python3
"""Azure Speech TTS helper for the approved Greek narration path.

Uses repository secrets AZURE_SPEECH_KEY and AZURE_SPEECH_REGION.
Never logs credentials. No paid fallback is implemented.
"""
from __future__ import annotations

import argparse
import html
import os
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_VOICE = "el-GR-NestorasNeural"
MAX_TEXT_CHARS_PER_CALL = 10000


def synthesize(text: str, output: Path, voice: str = DEFAULT_VOICE) -> None:
    region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
    key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    if not region or not key:
        raise RuntimeError("Azure Speech secrets are missing")
    text = text.strip()
    if not text:
        raise ValueError("Narration text is empty")
    if len(text) > MAX_TEXT_CHARS_PER_CALL:
        raise ValueError("Narration text exceeds the safe per-call limit")

    ssml = (
        "<speak version='1.0' xml:lang='el-GR'>"
        f"<voice name='{html.escape(voice, quote=True)}'>"
        f"<prosody rate='0%' pitch='0%'>{html.escape(text)}</prosody>"
        "</voice></speak>"
    ).encode("utf-8")

    req = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml,
        method="POST",
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
            "User-Agent": "SteliosSocialNarration/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            audio = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Azure Speech failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Azure Speech connection failed") from exc

    if len(audio) < 1000 or not audio.startswith(b"RIFF"):
        raise RuntimeError("Azure Speech returned invalid audio")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(audio)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    args = parser.parse_args()
    text = Path(args.text_file).read_text(encoding="utf-8")
    synthesize(text, Path(args.output), args.voice)
    print(f"voice={args.voice}")
    print(f"characters={len(text.strip())}")
    print("paid_fallback_used=false")


if __name__ == "__main__":
    main()
