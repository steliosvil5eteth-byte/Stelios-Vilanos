#!/usr/bin/env python3
"""Remux verified existing scenes with a visual CTA hold; preserve old exports."""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path

import batch_recovery_render as r


def remux(inventory: Path, narration: Path, previous: Path, output: Path, threads: int = 3) -> dict:
    args = argparse.Namespace(inventory=inventory.resolve(), audio=(narration / "derived/narration.wav").resolve(),
                              srt=(narration / "derived/narration.srt").resolve(), script=(narration / "script.txt").resolve(),
                              output=output.resolve(), voice=r.VOICE, title=None, threads=threads, execute=False)
    report = r.build(args)
    old = json.loads((previous / "render_report.json").read_text())
    for key in ("narration_text_sha256", "input_srt_sha256", "source_inventory_sha256"):
        if old[key] != report[key]:
            raise r.RenderBlocked(f"Existing export belongs to a different input: {key}")
    if old["audio"]["sha256"] != report["audio"]["sha256"]:
        raise r.RenderBlocked("Original narration bytes changed")
    checks = []
    for scene in report["scenes"]:
        segment = previous / "segments" / f"{scene['scene']:02d}.mp4"
        streams = r.probe(segment)["streams"]
        video = [s for s in streams if s["codec_type"] == "video"]
        if (len(video) != 1 or int(video[0].get("nb_frames", 0)) != scene["frames"]
                or (video[0].get("width"), video[0].get("height")) != (r.WIDTH, r.HEIGHT)):
            raise r.RenderBlocked(f"Source segment {scene['scene']} is incomplete")
        checks.append({"scene": scene["scene"], "expected_frames": scene["frames"],
                       "actual_frames": int(video[0]["nb_frames"]), "sha256": r.digest(segment),
                       "reused_from": str(segment.resolve()), "format_probe_passed": True})
    output = output.resolve()
    if output.exists():
        raise r.RenderBlocked("Preserve existing output; use a fresh revision directory")
    output.mkdir(parents=True)
    shutil.copytree(previous / "segments", output / "segments")
    shutil.copytree(previous / "scene_frames", output / "scene_frames")
    shutil.copyfile(previous / "segments.ffconcat", output / "segments.ffconcat")
    inv = json.loads(inventory.read_text())
    duration = report["audio"]["duration_seconds"]
    r.write_ass(output / "final.ass", inv["title"], report["subtitle_cues"], duration, inv["disclosure"])
    final = output / "final.mp4"
    r.run(["ffmpeg", "-v", "error", "-f", "concat", "-safe", "1", "-i", "segments.ffconcat",
           "-i", str(args.audio), "-map", "0:v:0", "-map", "1:a:0", "-vf", "ass=final.ass",
           "-t", f"{duration:.6f}", "-c:v", "libx264", "-preset", "fast", "-crf", "19",
           "-threads", str(threads), "-pix_fmt", "yuv420p", "-r", str(r.FPS), "-c:a", "aac",
           "-b:a", "160k", "-ar", "48000", "-ac", "1", "-movflags", "+faststart", str(final)],
          cwd=output, log_path=output / "execution_logs/final.json")
    info = r.probe(final)
    video = [s for s in info["streams"] if s["codec_type"] == "video"]
    audio = [s for s in info["streams"] if s["codec_type"] == "audio"]
    if (len(video) != 1 or len(audio) != 1
            or (video[0]["width"], video[0]["height"]) != (r.WIDTH, r.HEIGHT)
            or any(abs(float(s.get("duration", 0)) - duration) > .1 for s in [info["format"], video[0], audio[0]])):
        raise r.RenderBlocked("Final stream structure or duration is incomplete")
    r.run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"],
          log_path=output / "execution_logs/final-decode.json")
    report["review_frames"] = r.create_review_frames(final, report["subtitle_cues"], report["scenes"], output)
    report["review_contact_sheets"] = r.create_review_sheets(report["review_frames"], output)
    report["layouts"] = old["layouts"]
    report["segment_checks"] = checks
    report["status"] = "NEEDS_FINAL_REVIEW"
    report["remux_revision_of"] = str(previous.resolve())
    report["remux_scope"] = "Visual final-caption hold only; exact narration audio and actual source SRT retained"
    report["final"] = {"path": str(final), "sha256": r.digest(final), "bytes": final.stat().st_size,
                       "duration_seconds": float(info["format"]["duration"]),
                       "video_duration_seconds": float(video[0]["duration"]),
                       "audio_duration_seconds": float(audio[0]["duration"]),
                       "width": r.WIDTH, "height": r.HEIGHT, "video_codec": video[0]["codec_name"],
                       "audio_codec": audio[0]["codec_name"], "audio_streams": 1, "technical_decode_passed": True}
    for name in ("caption.txt", "source_attributions.md"):
        shutil.copyfile(inventory.parent / name, output / name)
    (output / "render_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("inventory", "narration", "previous", "output"):
        p.add_argument("--" + arg, type=Path, required=True)
    p.add_argument("--threads", type=int, default=3)
    a = p.parse_args()
    try:
        result = remux(a.inventory, a.narration, a.previous, a.output, a.threads)
    except (r.RenderBlocked, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "publishable": False}, ensure_ascii=False))
        raise SystemExit(2)
    print(json.dumps(result["final"], ensure_ascii=False))
