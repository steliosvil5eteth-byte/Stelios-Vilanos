#!/usr/bin/env python3
"""Render one reviewed local scene sequence and an existing Nestoras WAV.

No network, speech SDK, ASR or publication imports. Review sheets are evidence
for a reviewer, never proof that anyone watched or listened to the video.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from pipeline import (Blocked, CTA, UTC, VOICE, asset_path, read_json, render_preflight,
                      sha256, story_hash, validate_manifest, write_json)

FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
FPS, WIDTH, HEIGHT = 30, 1080, 1920


def run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise Blocked(f"Local media command failed ({Path(args[0]).name}): {result.stderr[-1500:]}")
    return result.stdout


def probe(path: Path) -> dict:
    return json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]))


def check_silence(path: Path, duration: float) -> dict:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                             "silencedetect=noise=-45dB:d=0.5", "-f", "null", "-"], text=True, capture_output=True)
    if result.returncode:
        raise Blocked("Local silence inspection failed")
    gaps = [(float(end), float(length)) for end, length in re.findall(r"silence_end: ([0-9.]+) \| silence_duration: ([0-9.]+)", result.stderr)]
    trailing = max([length for end, length in gaps if end >= duration - .12] or [0.0])
    if any(length > 2.0 for _, length in gaps) or trailing > .5:
        raise Blocked("Narration has excessive dead air or trailing silence; no automatic padding/edit")
    return {"longest_detected_silence_seconds": max([length for _, length in gaps] or [0.0]), "trailing_silence_seconds": trailing}


def stamp(value: str) -> float:
    h, m, s = value.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def formatted_time(seconds: float, ass: bool = False) -> str:
    unit = 100 if ass else 1000
    total = round(seconds * unit)
    h, total = divmod(total, 3600 * unit)
    m, total = divmod(total, 60 * unit)
    s, fraction = divmod(total, unit)
    return f"{h}:{m:02}:{s:02}.{fraction:02}" if ass else f"{h:02}:{m:02}:{s:02},{fraction:03}"


def lexical(text: str) -> list[str]:
    # Punctuation emitted as separate Azure boundaries is not a dropped word.
    return re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE)


def parse_cues(path: Path, duration: float, script: str) -> list[dict]:
    cues = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip()):
        lines = block.splitlines()
        if len(lines) < 3 or "-->" not in lines[1]:
            raise Blocked("Malformed source SRT")
        start, end = [stamp(part.strip()) for part in lines[1].split("-->")]
        text = " ".join(" ".join(lines[2:]).split())
        if not text or not 0 <= start < end <= duration + 0.002 or (cues and start < cues[-1]["end"] - 0.002):
            raise Blocked("Subtitle timing is invalid or overlaps")
        cues.append({"start": start, "end": min(end, duration), "text": text})
    if not cues or lexical(" ".join(cue["text"] for cue in cues)) != lexical(script):
        raise Blocked("Subtitle word sequence does not match the exact narration script")
    if lexical(" ".join(cue["text"] for cue in cues))[-len(lexical(CTA)):] != lexical(CTA):
        raise Blocked("Complete final CTA missing from subtitles")
    # Combine only a trailing group exactly equal to the full required CTA.
    # No narration timing is changed, and earlier CTA-like text is untouched.
    for count in range(1, min(4, len(cues)) + 1):
        if lexical(" ".join(cue["text"] for cue in cues[-count:])) == lexical(CTA):
            if duration - cues[-count]["start"] < 1.5:
                raise Blocked("Complete CTA has insufficient final display time")
            cues = cues[:-count] + [{"start": cues[-count]["start"], "end": duration, "text": CTA}]
            break
    return cues


def wrap(text: str, font: ImageFont.FreeTypeFont, width: int = 816) -> list[str]:
    if font.getlength(text) <= width:
        return [text]
    words, candidates = text.split(), []
    for index in range(1, len(words)):
        pair = [" ".join(words[:index]), " ".join(words[index:])]
        lengths = [font.getlength(line) for line in pair]
        if max(lengths) <= width:
            candidates.append((abs(lengths[0] - lengths[1]), pair))
    if not candidates:
        raise Blocked("Subtitle cannot fit in two measured 52px lines; split using actual word boundaries")
    return min(candidates, key=lambda item: item[0])[1]


def escape_ass(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def overlays(job: dict, cues: list[dict], duration: float, output: Path) -> None:
    font = ImageFont.truetype(str(FONT), 52)
    title_font = ImageFont.truetype(str(FONT), 38)
    title = job.get("on_screen_title") or job["title"]
    title_lines = wrap(title, title_font, 830)
    ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,DejaVu Sans,52,&H00FFFFFF,&H00FFFFFF,&H00100C09,&H80000000,-1,0,0,0,100,100,0,0,1,2.2,0.3,5,80,160,0,1
Style: Title,DejaVu Sans,38,&H00FFFFFF,&H00FFFFFF,&H00100C09,&H80000000,-1,0,0,0,100,100,0,0,1,2,0.3,5,80,160,0,1
Style: Disclosure,DejaVu Sans,25,&H00FFFFFF,&H00FFFFFF,&H00100C09,&H80000000,0,0,0,0,100,100,0,0,1,1.5,0,7,0,0,0,1
Style: Panel,DejaVu Sans,20,&H00171410,&H00171410,&H00171410,&H00171410,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def event(layer: int, start: float, end: float, style: str, text: str) -> str:
        return f"Dialogue: {layer},{formatted_time(start, True)},{formatted_time(end, True)},{style},,0,0,0,,{text}\n"
    ass += event(0, 0, duration, "Panel", r"{\an7\pos(50,1444)\p1\1a&H28&}m 0 0 l 900 0 l 900 192 l 0 192{\p0}")
    ass += event(1, 0, duration, "Title", r"{\an5\pos(500,235)\q2}" + r"\N".join(escape_ass(line) for line in title_lines))
    disclosure = job.get("visual_disclosure", "Ενδεικτική αναπαράσταση με AI")
    if ImageFont.truetype(str(FONT), 25).getlength(disclosure) > 850:
        raise Blocked("Visual disclosure overflows safe width")
    ass += event(1, 0, duration, "Disclosure", r"{\an7\pos(65,1396)}" + escape_ass(disclosure))
    rows = []
    for number, cue in enumerate(cues, 1):
        cue["number"], cue["lines"] = number, wrap(cue["text"], font)
        cue["widths_px"] = [round(font.getlength(line), 3) for line in cue["lines"]]
        rows.append(f"{number}\n{formatted_time(cue['start'])} --> {formatted_time(cue['end'])}\n" + "\n".join(cue["lines"]))
        ass += event(2, cue["start"], cue["end"], "Sub", r"{\an5\pos(500,1535)\q2}" + r"\N".join(escape_ass(line) for line in cue["lines"]))
    (output / "final.srt").write_text("\n\n".join(rows) + "\n", encoding="utf-8")
    (output / "final.ass").write_text(ass, encoding="utf-8")
    write_json(output / "subtitle_layout.json", {"font": str(FONT), "font_sha256": sha256(FONT), "font_size": 52,
                                                 "max_width": 816, "max_lines": 2, "cues": cues,
                                                 "subtitle_text_verified": True, "actual_audio_listened": False})


def timeline(job: dict, base: Path, duration: float) -> list[dict]:
    result, expected_start = [], 0.0
    for scene in job["scenes"]:
        start, end = float(scene["start"]), float(scene["end"])
        if abs(start - expected_start) > 0.002 or not start < end <= duration + 0.002:
            raise Blocked("Scene timeline must cover narration once, without gaps or padding")
        image = asset_path(base, scene["path"])
        with Image.open(image) as bitmap:
            if bitmap.width >= bitmap.height:
                raise Blocked("Each scene must be a single portrait photograph")
            bitmap.verify()
        x, y = float(scene.get("crop_x", .5)), float(scene.get("crop_y", .5))
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise Blocked("Scene crop focus must be in [0,1]")
        # Static reviewed crops are the safe default; no repeated scene loops.
        result.append({**scene, "path": str(image), "crop_x": x, "crop_y": y, "start": start, "end": end})
        expected_start = end
    if abs(expected_start - duration) > 0.002:
        raise Blocked("Final scene must end with the complete narration")
    return result


def contact(entries: list[dict], destination: Path) -> None:
    width, height, gap, header = 270, 480, 10, 30
    canvas = Image.new("RGB", (3 * width + 4 * gap, math.ceil(len(entries) / 3) * (height + header + gap) + gap), "#161b22")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(FONT), 14)
    for index, entry in enumerate(entries):
        x, y = gap + index % 3 * (width + gap), gap + index // 3 * (height + header + gap)
        draw.text((x, y + 4), entry["label"], font=font, fill="white")
        with Image.open(entry["path"]) as frame:
            canvas.paste(ImageOps.contain(frame.convert("RGB"), (width, height)), (x, y + header))
    canvas.save(destination, quality=93)


def review_frames(final: Path, cues: list[dict], scenes: list[dict], output: Path) -> dict:
    directory = output / "review_frames"
    directory.mkdir()
    requests = [{"kind": "cue", "number": cue["number"], "time": (cue["start"] + cue["end"]) / 2} for cue in cues]
    requests += [{"kind": "scene", "number": i + 1, "time": (scene["start"] + scene["end"]) / 2} for i, scene in enumerate(scenes)]
    requests.append({"kind": "opening", "number": 1, "time": .5})
    numbers = sorted(set(round(item["time"] * FPS) for item in requests))
    select = "+".join(f"eq(n,{number})" for number in numbers)
    run(["ffmpeg", "-v", "error", "-i", str(final), "-vf", f"select='{select}'", "-fps_mode", "vfr", "-q:v", "2", str(directory / "frame-%03d.jpg")])
    lookup = {number: directory / f"frame-{i + 1:03d}.jpg" for i, number in enumerate(numbers)}
    for request in requests:
        path = lookup[round(request["time"] * FPS)]
        if not path.is_file():
            raise Blocked("An exact-file review frame is missing")
        request.update(path=str(path), sha256=sha256(path), label=f"{request['kind']} {request['number']} | {request['time']:.3f}s")
    sheets = []
    for kind in ("cue", "scene", "opening"):
        selected = [item for item in requests if item["kind"] == kind]
        for index in range(0, len(selected), 9):
            target = directory / f"{kind}-contact-{index // 9 + 1:02d}.jpg"
            contact(selected[index:index + 9], target)
            sheets.append({"path": str(target), "sha256": sha256(target)})
    result = {"media_sha256": sha256(final), "frames": requests, "contact_sheets": sheets,
              "actual_audio_listened": False, "visual_review_passed": False, "passed_final_review": False}
    write_json(output / "review_index.json", result)
    return result


def render(job: dict, base: Path, output: Path, policy: dict, history: dict, threads: int = 2) -> dict:
    """Public API enforces the same guard as the CLI before any rendering."""
    render_preflight(job, base, policy, history, dt.datetime.now(UTC))
    if output.exists():
        raise Blocked("Output directory already exists; do not overwrite reviewed media")
    audio = asset_path(base, job["audio"]["path"])
    source = probe(audio)
    duration = float(source["format"]["duration"])
    streams = source.get("streams", [])
    if not 80 <= duration <= 110 or len(streams) != 1 or streams[0].get("codec_type") != "audio" or streams[0].get("channels") != 1:
        raise Blocked("Source must be one mono 80–110-second narration; padding is forbidden")
    silence = check_silence(audio, duration)
    cues = parse_cues(asset_path(base, job["audio"]["srt_path"]), duration, job["script"])
    scenes = timeline(job, base, duration)
    output.mkdir(parents=True)
    overlays(job, cues, duration, output)
    segments = output / "segments"
    segments.mkdir()
    cuts = [round(scene["start"] * FPS) for scene in scenes] + [math.ceil(duration * FPS)]
    for number, scene in enumerate(scenes):
        frames = cuts[number + 1] - cuts[number]
        if frames < 1:
            raise Blocked("Scene is shorter than one output frame")
        filter_ = (f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
                   f"crop=1080:1920:(iw-1080)*{scene['crop_x']}:(ih-1920)*{scene['crop_y']},setsar=1,format=yuv420p")
        target = segments / f"scene-{number + 1:02d}.mp4"
        run(["ffmpeg", "-v", "error", "-loop", "1", "-framerate", "30", "-i", scene["path"], "-vf", filter_,
             "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-threads", str(threads), str(target)])
    # Only generated safe basenames appear in ffconcat/filter syntax.
    (output / "segments.ffconcat").write_text("ffconcat version 1.0\n" + "".join(f"file 'segments/scene-{i + 1:02d}.mp4'\n" for i in range(len(scenes))))
    final = output / "final.mp4"
    run(["ffmpeg", "-v", "error", "-f", "concat", "-safe", "1", "-i", "segments.ffconcat", "-i", str(audio),
         "-map", "0:v:0", "-map", "1:a:0", "-vf", "ass=final.ass,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-r", "30", "-threads", str(threads), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "1",
         "-t", f"{duration:.6f}", "-shortest", "-movflags", "+faststart", "final.mp4"], cwd=output)
    meta = probe(final)
    video = [stream for stream in meta["streams"] if stream["codec_type"] == "video"]
    sound = [stream for stream in meta["streams"] if stream["codec_type"] == "audio"]
    if not (len(video) == len(sound) == 1 and video[0]["width"] == WIDTH and video[0]["height"] == HEIGHT and
            video[0]["codec_name"] == "h264" and video[0]["pix_fmt"] == "yuv420p" and video[0]["r_frame_rate"] == "30/1" and
            sound[0]["codec_name"] == "aac" and sound[0]["sample_rate"] == "48000" and sound[0]["channels"] == 1 and
            abs(float(meta["format"]["duration"]) - duration) <= 1 / FPS):
        raise Blocked("Exact final technical format or duration failed")
    run(["ffmpeg", "-v", "error", "-xerror", "-i", str(final), "-f", "null", "-"])
    review_frames(final, cues, scenes, output)
    now = dt.datetime.now(UTC).isoformat()
    report = {"job_id": job["id"], "story_sha256": story_hash(job), "platform": job["platform"],
              "media_sha256": sha256(final), "created_at": now, "technical_passed": True,
              "full_decode_passed": True, "subtitle_text_verified": True, "duration_seconds": float(meta["format"]["duration"]),
              "width": WIDTH, "height": HEIGHT, "fps": FPS, "video_codec": "h264", "pixel_format": "yuv420p",
              "audio_codec": "aac", "audio_rate": 48000, "audio_channels": 1, "voice": VOICE,
              "background_music": False, "avatar": False, "source_audio_sha256": sha256(audio),
              "audio_stretched": False, "audio_padded": False, "scenes": scenes, "subtitle_cues": len(cues),
              "new_synthesis_calls": 0, "new_asr_calls": 0, "actual_audio_listened": False, "passed_final_review": False}
    report["silence_check"] = silence
    write_json(output / "technical_review.json", report)
    review = {key: report[key] for key in ("job_id", "story_sha256", "platform", "media_sha256")}
    review.update(reviewer=None, reviewed_at=None, actual_audio_listened=False, complete_audio_review_passed=False,
                  nestoras_voice_confirmed=False, visual_review_passed=False, all_scenes_reviewed=False,
                  all_subtitle_cues_reviewed=False, pronunciation_passed=False, subtitle_sync_passed=False,
                  opening_reviewed=False, complete_cta_reviewed=False, passed_final_review=False)
    write_json(output / "final_review.PENDING.json", review)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("manifest", "policy", "history", "output"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    try:
        manifest = read_json(args.manifest)
        errors = validate_manifest(manifest)
        if errors:
            raise Blocked("; ".join(errors))
        job = next(job for job in manifest["jobs"] if job["id"] == args.job_id)
        report = render(job, args.manifest.parent, args.output.resolve(), read_json(args.policy), read_json(args.history), args.threads)
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (Blocked, ValueError, OSError, StopIteration, KeyError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "new_provider_calls": 0}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
