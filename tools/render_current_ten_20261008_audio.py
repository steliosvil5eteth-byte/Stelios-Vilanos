#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import render_azure_feature_batch as renderer


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    if data.get("date") != "2026-10-08" or len(data.get("jobs", [])) != 4:
        raise RuntimeError("Expected exactly four 2026-10-08 narrated jobs")
    if renderer.VOICE != "el-GR-NestorasNeural":
        raise RuntimeError("Required Nestoras voice is not configured")
    args.output.mkdir(parents=True, exist_ok=True)
    summary = []
    for job in data["jobs"]:
        if len(job["script"].split()) < 200 or not job["script"].rstrip().endswith(renderer.CTA):
            raise RuntimeError(f"Incomplete narration script: {job['series']}")
        out = args.output / job["series"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "script.txt").write_text(job["script"] + "\n", encoding="utf-8")
        (out / "caption.txt").write_text(job["caption"] + "\n", encoding="utf-8")
        wav, boundaries, duration = renderer.synthesize(job["script"], out, 80.0, None)
        srt = out / "subs.srt"
        cue_count = renderer.subtitles(boundaries, duration, srt)
        (out / "boundaries.json").write_text(json.dumps(boundaries, ensure_ascii=False, indent=2), encoding="utf-8")
        meta = {
            "series": job["series"],
            "voice": renderer.VOICE,
            "provider": "Azure Speech",
            "duration_seconds": duration,
            "minimum_duration_seconds": 80.0,
            "word_boundaries": len(boundaries),
            "subtitle_cues": cue_count,
            "background_music": False,
            "avatar": False,
            "audio_sha256": digest(wav),
            "srt_sha256": digest(srt),
            "technical_audio_passed": True,
        }
        (out / "audio-qa.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        summary.append(meta)
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
