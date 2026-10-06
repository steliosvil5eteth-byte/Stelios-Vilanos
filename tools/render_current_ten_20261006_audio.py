#!/usr/bin/env python3
"""Render reviewed narration only; technical audio checks never release a post."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

import render_azure_feature_batch as renderer


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_subtitles(path: Path) -> int:
    cues = []
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        lines = block.splitlines()
        if len(lines) < 3:
            raise RuntimeError("Malformed subtitle cue")
        text = re.sub(r"\s+([,.;;:!?·…])", r"\1", " ".join(lines[2:]).strip())
        if text and text[0] in ",.;;:!?·…" and cues:
            cues[-1][1] += text[0]
            text = text[1:].lstrip()
        if text:
            cues.append([lines[1], text])
    rows = []
    for number, (timing, text) in enumerate(cues, 1):
        words = text.split()
        wrapped, line = [], ""
        for word in words:
            candidate = (line + " " + word).strip()
            if line and len(candidate) > 31:
                wrapped.append(line)
                line = word
            else:
                line = candidate
        if line:
            wrapped.append(line)
        if len(wrapped) > 2:
            split = min(range(1, len(words)), key=lambda i: max(len(" ".join(words[:i])), len(" ".join(words[i:]))))
            wrapped = [" ".join(words[:split]), " ".join(words[split:])]
        if len(wrapped) > 2 or any(len(line) > 43 for line in wrapped):
            raise RuntimeError("Subtitle is too wide for the portrait safe area")
        if re.search(r"\s+[,.;;:!?·…]", " ".join(wrapped)) or re.match(r"^[,.;;:!?·…]", text):
            raise RuntimeError("Subtitle punctuation normalization failed")
        rows.extend([str(number), timing, *wrapped, ""])
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return len(cues)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    lease = json.loads(Path(manifest["production_lease_path"]).read_text(encoding="utf-8"))
    now = dt.datetime.now(dt.timezone.utc)
    if lease.get("owner") != manifest["production_lease_owner"]:
        raise RuntimeError("This narration batch does not own the production lease")
    expiry = dt.datetime.fromisoformat(lease["expires_at"].replace("Z", "+00:00"))
    if now >= expiry or lease.get("status") != "PRODUCTION_IN_PROGRESS_NOT_QA_APPROVED":
        raise RuntimeError("Production lease is expired or no longer in production")
    if renderer.VOICE != "el-GR-NestorasNeural":
        raise RuntimeError("Required Greek Nestoras voice is unavailable")
    jobs = manifest["jobs"]
    if len(jobs) != 4 or len({job["id"] for job in jobs}) != 4:
        raise RuntimeError("Expected the four distinct approved narrated jobs")
    args.output.mkdir(parents=True, exist_ok=True)
    summary = []
    for job in jobs:
        if job["series"] not in lease.get("categories", []):
            raise RuntimeError("Job category is outside the owned production lease")
        script = job["script"]
        if hashlib.sha256(script.encode("utf-8")).hexdigest() != job["script_sha256"]:
            raise RuntimeError("Narration script hash changed")
        if not script.rstrip().endswith(renderer.CTA):
            raise RuntimeError("Required spoken CTA is missing")
        if len(script.split()) < 200:
            raise RuntimeError("Narration is too short for this approved batch")
        root = args.output / job["id"]
        root.mkdir(parents=True, exist_ok=True)
        (root / "script.txt").write_text(script + "\n", encoding="utf-8")
        (root / "final-caption.txt").write_text(job["caption"] + "\n", encoding="utf-8")
        wav, boundaries, duration = renderer.synthesize(script, root, 80.0, None)
        srt = root / "subs.srt"
        renderer.subtitles(boundaries, duration, srt)
        subtitle_count = normalized_subtitles(srt)
        (root / "speech-boundaries.json").write_text(json.dumps(boundaries, ensure_ascii=False, indent=2), encoding="utf-8")
        metadata = {
            "id": job["id"], "series": job["series"], "title": job["title"],
            "voice": renderer.VOICE, "provider": "Azure Speech", "synthetic_voice": True,
            "duration_seconds": duration, "minimum_duration_seconds": 80.0,
            "natural_rate": True, "padding_added": False, "background_music": False,
            "avatar": False, "word_boundaries": len(boundaries), "subtitle_cues": subtitle_count,
            "script_sha256": job["script_sha256"], "audio_sha256": sha256(wav),
            "srt_sha256": sha256(srt), "technical_audio_passed": True,
            "final_video_exists": False, "subtitles_burned_in": False,
            "publish_ready": False, "direct_review_required": True,
            "release_gate": "PENDING_FINAL_VIDEO_AND_DIRECT_VISUAL_AUDIO_REVIEW",
        }
        (root / "speech-meta.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "release-gate.txt").write_text(metadata["release_gate"] + "\n", encoding="utf-8")
        summary.append(metadata)
        print(json.dumps({"id": job["id"], "duration_seconds": round(duration, 3), "publish_ready": False}))
    (args.output / "audio-batch-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
