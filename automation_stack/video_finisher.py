#!/usr/bin/env python3
"""Fail-closed still-image + narration MP4 renderer. No API calls or publishing.

Scenes require explicit seconds aligned to narration (not equal-timing guesses).
The renderer supplies technical evidence ONLY; visual/audio final review must be separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(argv: list[str], timeout: int = 1200) -> str:
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(argv[:4])}: {p.stderr[-1800:]}")
    return p.stdout


def probe(p: Path, count_frames: bool = False) -> dict:
    cmd = ["ffprobe", "-v", "error"]
    if count_frames:
        cmd.append("-count_frames")
    cmd += ["-show_streams", "-show_format", "-of", "json", str(p)]
    return json.loads(run(cmd))


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rate(s: str) -> float:
    a, b = s.split("/") if "/" in s else (s, "1")
    return float(a) / float(b)


def src_path(root: Path, value: str) -> Path:
    # Reject URLs, traversal and symlinks leaving the authorized media directory.
    if not isinstance(value, str) or "://" in value or not value:
        raise ValueError("Media references must be local paths")
    p = (root / value).resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file():
        raise ValueError("Media path missing or outside input directory")
    return p


def validate(manifest: dict, source_dir: Path) -> tuple[Path, list[dict], int, float]:
    if manifest.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    if manifest.get("fps") != 30:
        raise ValueError("Narrated MP4s MUST be rendered at exactly 30 FPS")
    size = int(manifest.get("size", 768))
    if size < 512 or size > 1920 or size % 2:
        raise ValueError("size must be even and 512-1920")
    audio = src_path(source_dir, manifest["narration_file"])
    streams = probe(audio)["streams"]
    as_ = [x for x in streams if x.get("codec_type") == "audio"]
    if len(as_) != 1:
        raise ValueError("Narration must contain exactly one audio stream")
    duration = float(as_[0].get("duration") or probe(audio)["format"].get("duration") or 0)
    if not math.isfinite(duration) or duration < 0.2:
        raise ValueError("Narration duration invalid")
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes or len(scenes) > 100:
        raise ValueError("scenes must contain 1-100 entries")
    prev = 0.0
    unique_images = set()
    mapped = []
    for i, s in enumerate(scenes):
        a, b = float(s["start_s"]), float(s["end_s"])
        if not math.isfinite(a) or not math.isfinite(b) or abs(prev - a) > 0.015 or b - a < 0.1:
            raise ValueError(f"Scene {i+1}: non-contiguous, invalid or too short timing")
        p = src_path(source_dir, s["image_file"])
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise ValueError("Only photographic still-image files are supported")
        if sha256(p) in unique_images:
            raise ValueError(f"Scene {i+1}: repeated image bytes forbidden")
        unique_images.add(sha256(p))
        # ffprobe provides exact dimensions without decoding into another image format
        imagestream = next((x for x in probe(p)["streams"] if x.get("codec_type") == "video"), None)
        if not imagestream or int(imagestream.get("width", 0)) != int(imagestream.get("height", -1)):
            raise ValueError(f"Scene {i+1}: image must already be square to avoid crop/letterbox")
        mapped.append({"path": p, "start": a, "end": b})
        prev = b
    if abs(prev - duration) > 0.11:
        raise ValueError(f"Scenes end at {prev:.3f}s; narration ends at {duration:.3f}s. Explicitly synchronize them first")
    return audio, mapped, size, duration


def finish(manifest_file: Path, input_dir: Path, output: Path, report_file: Path) -> dict:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg and ffprobe are required")
    manifest = json.loads(manifest_file.read_text("utf-8"))
    audio, scenes, size, audio_duration = validate(manifest, input_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or report_file.exists():
        raise FileExistsError("Refusing to overwrite an existing video or QA evidence")
    with tempfile.TemporaryDirectory(prefix="cfr30_") as d:
        temp = Path(d)
        list_file = temp / "segments.txt"
        lines = []
        total_frames = round(audio_duration * 30)
        frame_cursor = 0
        for i, s in enumerate(scenes):
            next_cursor = total_frames if i == len(scenes) - 1 else round(s["end"] * 30)
            frames = next_cursor - frame_cursor
            if frames < 3:
                raise ValueError(f"Scene {i+1} has fewer than 3 frames")
            segment = temp / f"scene_{i:03d}.mp4"
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "30",
                "-i", str(s["path"]), "-vf", f"scale={size}:{size}:flags=lanczos,setsar=1,format=yuv420p",
                "-frames:v", str(frames), "-r", "30", "-fps_mode", "cfr", "-an", "-c:v", "libx264",
                "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(segment)
            ])
            lines.append(f"file '{segment.as_posix()}'")
            frame_cursor = next_cursor
        list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        encoded = temp / "joined.mp4"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(encoded)])
        temp_output = temp / "final.mp4"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(encoded), "-i", str(audio),
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
             "-af", "aresample=async=1:first_pts=0", "-movflags", "+faststart", str(temp_output)])
        info = probe(temp_output, count_frames=True)
        video = next(x for x in info["streams"] if x.get("codec_type") == "video")
        sound = next(x for x in info["streams"] if x.get("codec_type") == "audio")
        actual_duration = float(info["format"]["duration"])
        if video["codec_name"] != "h264" or sound["codec_name"] != "aac":
            raise ValueError("Wrong output codec")
        if abs(rate(video["avg_frame_rate"]) - 30) > 1e-6 or abs(rate(video["r_frame_rate"]) - 30) > 1e-6:
            raise ValueError("Final output is not exactly CFR 30")
        if int(video.get("nb_read_frames", 0)) != total_frames:
            raise ValueError(f"Final video frame count is not aligned to narration duration: expected {total_frames}, found {video.get('nb_read_frames')}, video_duration={video.get('duration')} audio_duration={audio_duration} final_duration={actual_duration}")
        if int(video["width"]) != size or int(video["height"]) != size:
            raise ValueError("Incorrect final image dimensions")
        if abs(actual_duration - audio_duration) > 0.12:
            raise ValueError("Video and narration duration mismatch")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-xerror", "-i", str(temp_output), "-f", "null", "-"])
        shutil.copy2(temp_output, output)
    report = {
        "schema_version": 1, "media_sha256": sha256(output), "filename": output.name,
        "scene_count": len(scenes), "audio_sha256": sha256(audio), "narration_seconds": audio_duration,
        "output_seconds": actual_duration, "fps": 30, "fps_mode": "CFR", "video_frames": total_frames,
        "width": size, "height": size, "video_codec": "h264", "audio_codec": "aac",
        "technical_decode": "PASSED", "visual_review": "NOT_PERFORMED", "actual_audio_listening": "NOT_PERFORMED",
        "scene_to_voice_sync_review": "NOT_PERFORMED", "final_review": "BLOCKED",
        "scheduling_authorized": False,
        "note": "Technical rendering does not certify visual/audio story accuracy or authorize publication."
    }
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description="Render precise-timing square narration MP4 at 30 CFR; no publishing")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    x = p.parse_args()
    print(json.dumps(finish(x.manifest, x.input_dir, x.output, x.report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()