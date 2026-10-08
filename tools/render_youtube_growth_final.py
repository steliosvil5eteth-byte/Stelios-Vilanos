#!/usr/bin/env python3
"""Assemble new photographic YouTube scenes and existing Nestoras narration.

Artwork is never painted or edited by Python. FFmpeg selects the eight atlas
regions, animates them gently, and burns timed Greek subtitles. All review
images come from the exact final MP4. Technical checks cannot approve release.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import math
import re
import subprocess
import unicodedata
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFont

PROGRAM = "YOUTUBE_GROWTH_TEN_DAILY"
VOICE = "el-GR-NestorasNeural"
CTA = "Αν σας άρεσε, ακολουθήστε για περισσότερα."
WIDTH, HEIGHT, FPS = 1080, 1920, 30
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PENDING = "PENDING_FINAL_VISUAL_AND_AUDIO_REVIEW"


def run(args: list[str], *, capture_bytes: bool = False):
    result = subprocess.run(args, capture_output=True, text=not capture_bytes)
    if result.returncode:
        error = result.stderr.decode(errors="replace") if capture_bytes else result.stderr
        raise RuntimeError(error[-2500:])
    return result.stdout


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_write(path: Path, content: object) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def probe(path: Path) -> dict:
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))


def words(text: str) -> list[str]:
    normalized = "".join(
        c for c in unicodedata.normalize("NFD", text.casefold())
        if not unicodedata.combining(c)
    )
    return re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)


def srt_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, milliseconds = re.split("[,.]", rest)
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000


def read_srt(path: Path, audio_duration: float, script: str) -> list[dict]:
    cues = []
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
    for index, block in enumerate(re.split(r"\n\s*\n", text), 1):
        lines = block.splitlines()
        if len(lines) < 3 or lines[0].strip() != str(index):
            raise RuntimeError("SRT indices or cue structure are incomplete")
        match = re.fullmatch(r"(\d\d:\d\d:\d\d[,.]\d{3}) --> (\d\d:\d\d:\d\d[,.]\d{3})", lines[1].strip())
        if not match:
            raise RuntimeError("Invalid SRT timestamps")
        start, end = map(srt_time, match.groups())
        content = "\n".join(lines[2:]).strip()
        if not content or len(content.splitlines()) > 2:
            raise RuntimeError("Each subtitle must have one or two complete lines")
        if start < 0 or end <= start or end > audio_duration + 0.10:
            raise RuntimeError("Subtitle extends outside narration or has invalid duration")
        if cues and start < cues[-1]["end"] - 0.035:
            raise RuntimeError("Subtitle cues overlap")
        cues.append({"index": index, "start": start, "end": end, "text": content})
    if not cues:
        raise RuntimeError("No synchronized Greek subtitles")
    expected = words(script)
    observed = words(" ".join(cue["text"] for cue in cues))
    if expected != observed:
        raise RuntimeError("Full subtitle words differ from the hash-bound approved narration")
    if cues[-1]["end"] < audio_duration - 0.30:
        raise RuntimeError("The ending of the narration is not subtitled")
    return cues


def scene_timeline(script: str, boundaries: list[dict], duration: float, indices=None) -> tuple[list[dict], float]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", script.strip()) if part.strip()]
    if indices is None:
        if len(paragraphs) < 8:
            raise RuntimeError("Eight scenes require paragraph starts or explicit scene_paragraph_indices")
        indices = list(range(8))
    if (
        not isinstance(indices, list) or len(indices) != 8
        or any(isinstance(x, bool) or not isinstance(x, int) for x in indices)
        or indices[0] != 0 or indices != sorted(set(indices))
        or indices[-1] >= len(paragraphs)
    ):
        raise RuntimeError("scene_paragraph_indices must identify eight increasing existing paragraphs")
    expected, paragraph_starts = [], []
    for paragraph in paragraphs:
        paragraph_starts.append(len(expected))
        expected += words(paragraph)
    observed, offsets = [], []
    for boundary in boundaries:
        for token in words(str(boundary["text"])):
            observed.append(token)
            offsets.append(float(boundary["offset"]))
    mapping = {}
    matched = 0
    for match in difflib.SequenceMatcher(a=expected, b=observed, autojunk=False).get_matching_blocks():
        matched += match.size
        for k in range(match.size):
            mapping[match.a + k] = match.b + k
    coverage = matched / max(1, len(expected))
    if coverage < 0.995:
        raise RuntimeError("Word timings do not cover the approved script accurately enough")
    starts = [0.0]
    for paragraph_index in indices[1:]:
        token_index = paragraph_starts[paragraph_index]
        if token_index not in mapping:
            raise RuntimeError("A requested scene paragraph has no exact timing alignment")
        starts.append(offsets[mapping[token_index]])
    if starts != sorted(starts) or len(set(starts)) != 8:
        raise RuntimeError("Scene word timings are not strictly increasing")
    frame_starts = [round(value * FPS) for value in starts] + [math.ceil(duration * FPS)]
    result = []
    for i in range(8):
        frame_count = frame_starts[i + 1] - frame_starts[i]
        if frame_count < 15:
            raise RuntimeError("A paragraph-aligned scene is shorter than half a second")
        result.append({
            "scene": i + 1, "paragraph_index": indices[i],
            "spoken_paragraph_start_seconds": starts[i],
            "start_frame": frame_starts[i], "frame_count": frame_count,
            "start_seconds": frame_starts[i] / FPS,
            "end_seconds": frame_starts[i + 1] / FPS,
            "alignment_error_seconds": frame_starts[i] / FPS - starts[i],
        })
    return result, coverage


def ass_stamp(seconds: float) -> str:
    count = round(seconds * 100)
    hours, count = divmod(count, 360000)
    minutes, count = divmod(count, 6000)
    whole, centiseconds = divmod(count, 100)
    return f"{hours}:{minutes:02d}:{whole:02d}.{centiseconds:02d}"


def create_ass(cues: list[dict], target: Path) -> int:
    chosen = None
    for size in range(55, 41, -1):
        font = ImageFont.truetype(FONT_PATH, size=size)
        if all(font.getlength(line) <= WIDTH - 2 * 120 - 12 for cue in cues for line in cue["text"].splitlines()):
            chosen = size
            break
    if chosen is None:
        raise RuntimeError("Subtitles cannot fit at a legible minimum 42px font within safe margins")
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "ScaledBorderAndShadow: yes\nWrapStyle: 2\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,DejaVu Sans,{chosen},&H00FFFFFF,&H00FFFFFF,&H88000000,&H88000000,"
        "-1,0,0,0,100,100,0,0,3,5,0,2,120,120,300,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    rows = []
    for cue in cues:
        text = cue["text"]
        if any(char in text for char in ("{", "}", "\\")):
            raise RuntimeError("Subtitle control characters require explicit review")
        text = text.replace("\n", r"\N")
        rows.append(f"Dialogue: 0,{ass_stamp(cue['start'])},{ass_stamp(cue['end'])},Default,,0,0,0,,{text}")
    target.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    return chosen


def subtitle_filter(path: Path) -> str:
    # Use a generated local path only; FFmpeg filter syntax is not shell syntax.
    escaped = str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "'\\''")
    return "ass='" + escaped + "'"


def extract_frame(video: Path, seconds: float, out: Path) -> None:
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{seconds:.6f}", "-i", str(video),
         "-frames:v", "1", "-update", "1", str(out)])


def motion_filter(x: int, y: int, width: int, height: int, count: int, index: int) -> str:
    progress = f"on/{max(1, count - 1)}"
    zoom = f"1.008+0.027*({progress})" if index % 2 == 0 else f"1.035-0.027*({progress})"
    return (
        f"crop={width}:{height}:{x}:{y},"
        "scale=1296:2304:force_original_aspect_ratio=increase,crop=1296:2304,"
        f"zoompan=z='{zoom}':x='(iw-iw/zoom)*(0.5+0.06*sin(PI*({progress})))':"
        f"y='(ih-ih/zoom)*0.5':d={count}:s=1080x1920:fps=30,format=yuv420p,setsar=1"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-json", type=Path, required=True)
    parser.add_argument("--audio-dir", type=Path, required=True)
    parser.add_argument("--atlas", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--panel-inset-px", type=int, default=4)
    args = parser.parse_args()
    story = json.loads(args.story_json.read_text(encoding="utf-8"))
    if story.get("program") != PROGRAM or len(story.get("scene_beats", [])) != 8:
        raise RuntimeError("Expected an independent YouTube story with exactly eight scene beats")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,99}", story.get("id", "")):
        raise RuntimeError("Invalid stable story ID")
    script = story["script"]
    if not script.endswith(CTA):
        raise RuntimeError("Exact closing CTA is missing")
    script_sha = hashlib.sha256(script.encode("utf-8")).hexdigest()
    speech = json.loads((args.audio_dir / "speech-meta.json").read_text(encoding="utf-8"))
    wav, srt = args.audio_dir / "nestoras.wav", args.audio_dir / "subs.srt"
    bounds_path = args.audio_dir / "boundaries.json"
    if (
        speech.get("id") != story["id"] or speech.get("program") != PROGRAM
        or speech.get("voice") != VOICE or speech.get("script_sha256") != script_sha
        or speech.get("audio_sha256") != sha(wav) or speech.get("srt_sha256") != sha(srt)
        or speech.get("file_sha256", {}).get("boundaries.json") != sha(bounds_path)
    ):
        raise RuntimeError("Exact approved script, voice, audio and timings must match their hashes")
    narration_probe = probe(wav)
    duration = float(narration_probe["format"]["duration"])
    if not 80.0 <= duration <= 150.0 or abs(duration - float(speech["duration_seconds"])) > 0.08:
        raise RuntimeError("Narration duration or saved duration differs from policy")
    cues = read_srt(srt, duration, script)
    boundaries = json.loads(bounds_path.read_text(encoding="utf-8"))
    timeline, coverage = scene_timeline(script, boundaries, duration, story.get("scene_paragraph_indices"))
    with Image.open(args.atlas) as atlas:
        atlas_width, atlas_height = atlas.size
    if not 0 <= args.panel_inset_px <= 30:
        raise RuntimeError("Atlas panel inset must be explicit and bounded")
    if atlas_width < 1024 or atlas_height < 896:
        raise RuntimeError("Storyboard atlas resolution is too small for eight scene regions")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work, reviews = output / "render-work", output / "review-frames"
    work.mkdir(exist_ok=True); reviews.mkdir(exist_ok=True)
    final = output / "final.mp4"
    inputs = {
        "story_id": story["id"], "script_sha256": script_sha,
        "atlas_sha256": sha(args.atlas), "source_audio_sha256": sha(wav),
        "srt_sha256": sha(srt), "boundaries_sha256": sha(bounds_path),
    }
    previous = output / "render-inputs.json"
    if final.exists() and previous.exists() and json.loads(previous.read_text()) != inputs:
        raise RuntimeError("Existing final belongs to different inputs; select a new output version directory")
    json_write(previous, inputs)
    ass = work / "greek-subtitles.ass"
    font_size = create_ass(cues, ass)
    clips = []
    crop_regions = []
    for item in timeline:
        index = item["scene"] - 1
        column, row = index % 4, index // 4
        x0, x1 = round(column * atlas_width / 4), round((column + 1) * atlas_width / 4)
        y0, y1 = round(row * atlas_height / 2), round((row + 1) * atlas_height / 2)
        inset = args.panel_inset_px
        x, y, width, height = x0 + inset, y0 + inset, x1 - x0 - 2 * inset, y1 - y0 - 2 * inset
        if min(width, height) < 240:
            raise RuntimeError("A scene region has insufficient source pixels")
        crop_regions.append({"scene": index + 1, "x": x, "y": y, "width": width, "height": height})
        count = item["frame_count"]
        motion = motion_filter(x, y, width, height, count, index)
        clip = work / f"scene-{index + 1:02d}.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(args.atlas),
             "-vf", motion, "-frames:v", str(count), "-an", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(clip)])
        clips.append(clip)
        print(json.dumps({"id": story["id"], "scene_rendered": index + 1}), flush=True)
    concat = work / "clips.txt"
    concat.write_text("".join("file '" + str(path).replace("'", "'\\''") + "'\n" for path in clips), encoding="utf-8")
    visual = work / "visual.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
         "-c", "copy", "-an", "-movflags", "+faststart", str(visual)])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(visual), "-i", str(wav),
         "-map", "0:v:0", "-map", "1:a:0", "-vf", subtitle_filter(ass),
         "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-r", "30", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "1",
         "-map_metadata", "-1", "-t", f"{duration:.6f}", "-shortest", "-movflags", "+faststart", str(final)])
    metadata = probe(final)
    json_write(output / "ffprobe.json", metadata)
    final_duration = float(metadata["format"]["duration"])
    video = [item for item in metadata["streams"] if item.get("codec_type") == "video"]
    audio = [item for item in metadata["streams"] if item.get("codec_type") == "audio"]
    issues = []
    if len(video) != 1 or len(audio) != 1:
        issues.append("Expected exactly one video and one narration audio stream")
    elif (
        video[0].get("codec_name") != "h264" or video[0].get("width") != WIDTH
        or video[0].get("height") != HEIGHT or video[0].get("r_frame_rate") != "30/1"
        or audio[0].get("codec_name") != "aac" or audio[0].get("channels") != 1
    ):
        issues.append("Codec, dimensions, FPS or narration channel policy mismatch")
    if abs(final_duration - duration) > 0.12:
        issues.append("Final video duration differs from complete narration")
    if not 80.0 <= final_duration <= 110.12:
        issues.append("Narration target must be reviewed: expected 80–110 seconds")
    run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"])
    final_audio = output / "final-audio.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(final), "-map", "0:a:0",
         "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(final_audio)])
    with wave.open(str(final_audio), "rb") as file:
        pcm = file.readframes(file.getnframes())
    final_pcm_sha = hashlib.sha256(pcm).hexdigest()
    silence = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(final), "-af", "silencedetect=noise=-45dB:d=0.5", "-f", "null", "-"],
        text=True, capture_output=True, check=True,
    ).stderr
    gaps = [(float(end), float(length)) for end, length in re.findall(r"silence_end: ([0-9.]+) \| silence_duration: ([0-9.]+)", silence)]
    if any(length > 1.2 for _, length in gaps):
        issues.append("Audio contains a silence interval longer than 1.2 seconds")
    trailing = max([length for end, length in gaps if end >= final_duration - 0.15] or [0.0])
    if trailing > 0.5:
        issues.append("Trailing silence is longer than 0.5 seconds")
    burned_counts = []
    for i, cue in enumerate((cues[0], cues[len(cues) // 2], cues[-1]), 1):
        stamp = min(duration - 0.10, (cue["start"] + cue["end"]) / 2)
        clean, burned = work / f"subtitle-clean-{i}.png", work / f"subtitle-burned-{i}.png"
        extract_frame(visual, stamp, clean); extract_frame(final, stamp, burned)
        with Image.open(clean).convert("RGB") as a, Image.open(burned).convert("RGB") as b:
            difference = ImageChops.difference(a.crop((0, 1300, WIDTH, HEIGHT)), b.crop((0, 1300, WIDTH, HEIGHT)))
            burned_counts.append(int(np.sum(np.max(np.array(difference), axis=2) > 65)))
    if min(burned_counts) < 1200:
        issues.append("Visible burned subtitle pixels could not be established at every sampled cue")
    review_frames = []
    for item in timeline:
        start, end = item["start_seconds"], min(duration, item["end_seconds"])
        stamp = (start + end) / 2
        frame = reviews / f"{item['scene']:02d}.png"
        extract_frame(final, stamp, frame)
        review_frames.append({"file": str(frame), "scene": item["scene"], "timestamp_seconds": stamp, "sha256": sha(frame)})
    closing_stamp = min(duration - 0.10, (cues[-1]["start"] + cues[-1]["end"]) / 2)
    closing = reviews / "09.png"
    extract_frame(final, closing_stamp, closing)
    review_frames.append({"file": str(closing), "scene": "ending", "timestamp_seconds": closing_stamp, "sha256": sha(closing)})
    sheet = output / "exact-final-contact-sheet.jpg"
    run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "1", "-start_number", "1",
         "-i", str(reviews / "%02d.png"), "-vf", "scale=270:480,tile=3x3:padding=6:margin=6:color=0x202020",
         "-frames:v", "1", "-q:v", "2", "-update", "1", str(sheet)])
    report = {
        "program": PROGRAM, "id": story["id"], "inputs": inputs,
        "video_sha256": sha(final), "final_audio_wav_sha256": sha(final_audio),
        "final_audio_pcm_s16le_24000_sha256": final_pcm_sha,
        "final_audio_pcm_samples": len(pcm) // 2, "voice": VOICE,
        "source_audio_sha256": sha(wav), "source_audio_duration_seconds": duration,
        "duration_seconds": final_duration, "resolution": [WIDTH, HEIGHT], "fps": FPS,
        "avatar": False, "added_music": False, "narration_only": True,
        "scene_count": 8, "atlas_size": [atlas_width, atlas_height],
        "atlas_aspect_ratio_deviation_from_9_8": atlas_width / atlas_height / (9 / 8) - 1,
        "crop_regions": crop_regions, "scene_timeline": timeline,
        "paragraph_timing_word_coverage": coverage, "subtitle_cues": len(cues),
        "subtitle_full_word_match": True, "subtitle_max_lines": 2,
        "subtitle_font_pixels": font_size, "subtitle_safe_margins_pixels": {"left": 120, "right": 120, "bottom": 300},
        "burned_subtitle_sample_pixel_counts": burned_counts,
        "subtitle_continuity_checked": True, "complete_decode_passed": True,
        "trailing_silence_seconds": trailing, "technical_issues": issues,
        "technical_checks_passed": not issues, "review_frames": review_frames,
        "contact_sheet_sha256": sha(sheet), "release_status": PENDING,
        "final_visual_review": "NOT_PERFORMED", "final_audio_review": "NOT_PERFORMED",
        "publish_ready": False,
    }
    json_write(output / "technical-review.json", report)
    print(json.dumps({"id": story["id"], "video_sha256": report["video_sha256"],
                      "technical_checks_passed": not issues, "technical_issues": issues,
                      "release_status": PENDING, "publish_ready": False}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
