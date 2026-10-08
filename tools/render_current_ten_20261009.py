#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

import render_azure_feature_batch as azure


ROOT = Path(__file__).resolve().parents[1]
VOICE = "el-GR-NestorasNeural"
CTA = "Αν σας άρεσε, ακολουθήστε για περισσότερα."
GRID = {
    "relationships": (4, 2, 7),
    "survival": (3, 3, 9),
    "dog_bartender": (2, 2, 4),
    "zodiac": (3, 2, 6),
    "love_soul_relationship": (3, 2, 5),
    "myth_or_truth": (2, 2, 4),
    "greece_two_day_trip": (3, 3, 9),
    "strange_real_phenomenon": (3, 3, 9),
    "documented_experiments": (3, 3, 9),
    "international_legend": (3, 3, 9),
}


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-5000:])
    return p.stdout


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def duration(path: Path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]).strip())


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=size)


def crop_grid(path: Path, cols: int, rows: int, count: int) -> list[Image.Image]:
    im = Image.open(path).convert("RGB")
    cw, ch = im.width / cols, im.height / rows
    inset = max(3, int(min(cw, ch) * 0.008))
    out = []
    for i in range(count):
        x, y = i % cols, i // cols
        box = (int(x * cw) + inset, int(y * ch) + inset, int((x + 1) * cw) - inset, int((y + 1) * ch) - inset)
        out.append(ImageOps.fit(im.crop(box), (1080, 1080), method=Image.Resampling.LANCZOS))
    return out


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines = []
    for para in text.splitlines():
        if not para.strip():
            lines.append("")
            continue
        current = ""
        for word in para.split():
            candidate = (current + " " + word).strip()
            if current and draw.textbbox((0, 0), candidate, font=fnt)[2] > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def draw_card(scene: Image.Image, text: str, out: Path) -> None:
    canvas = scene.copy()
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(250, 1080):
        alpha = int(25 + 190 * ((y - 250) / 830) ** 0.8)
        od.line((0, y, 1080, y), fill=(0, 0, 0, min(220, alpha)))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)
    d = ImageDraw.Draw(canvas)
    chosen = None
    for size in range(68, 35, -2):
        fnt = font(size)
        lines = wrap(d, text, fnt, 920)
        heights = [d.textbbox((0, 0), ln or " ", font=fnt)[3] for ln in lines]
        total = sum(heights) + max(0, len(lines) - 1) * 16
        if total <= 650 and len(lines) <= 11:
            chosen = (fnt, lines, heights, total)
            break
    if chosen is None:
        raise RuntimeError("Card text cannot fit safely")
    fnt, lines, heights, total = chosen
    y = 1030 - total
    for ln, h in zip(lines, heights):
        if ln:
            box = d.textbbox((0, 0), ln, font=fnt, stroke_width=2)
            x = (1080 - (box[2] - box[0])) // 2
            d.text((x, y), ln, font=fnt, fill="white", stroke_width=3, stroke_fill=(0, 0, 0, 230))
        y += h + 16
    canvas.convert("RGB").save(out, "JPEG", quality=94, subsampling=0)


def vertical_frame(im: Image.Image) -> Image.Image:
    bg = ImageOps.fit(im, (1080, 1920), method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(36))
    shade = Image.new("RGBA", bg.size, (0, 0, 0, 80))
    bg = Image.alpha_composite(bg.convert("RGBA"), shade).convert("RGB")
    fg = im.resize((1080, 1080), Image.Resampling.LANCZOS)
    bg.paste(fg, (0, 420))
    return bg


def make_tone(path: Path, seconds: float) -> None:
    sr = 48000
    n = int(seconds * sr)
    freqs = (146.83, 220.0, 293.66)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            t = i / sr
            env = min(1.0, t / 2.0, max(0.0, (seconds - t) / 2.0))
            val = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
            sample = int(32767 * 0.055 * env * val)
            frames += sample.to_bytes(2, "little", signed=True)
        w.writeframes(frames)


def slideshow(frames: list[Image.Image], out: Path, temp: Path) -> None:
    frame_dir = temp / (out.stem + "-frames")
    frame_dir.mkdir(parents=True, exist_ok=True)
    for i, im in enumerate(frames, 1):
        vertical_frame(im).save(frame_dir / f"{i:02d}.jpg", "JPEG", quality=92)
    seconds = len(frames) * 4.0
    music = temp / (out.stem + "-instrumental.wav")
    make_tone(music, seconds)
    concat = temp / (out.stem + "-concat.txt")
    rows = []
    for i in range(1, len(frames) + 1):
        rows += [f"file '{frame_dir / f'{i:02d}.jpg'}'", "duration 4.0"]
    rows.append(f"file '{frame_dir / f'{len(frames):02d}.jpg'}'")
    concat.write_text("\n".join(rows) + "\n", encoding="utf-8")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-i", str(music),
         "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", str(out)])


def contact_sheet(images: list[Image.Image], out: Path, thumb=(360, 360), cols=3) -> None:
    rows = math.ceil(len(images) / cols)
    sheet = Image.new("RGB", (cols * thumb[0], rows * thumb[1]), "#222222")
    for i, im in enumerate(images):
        sheet.paste(ImageOps.fit(im, thumb, method=Image.Resampling.LANCZOS), ((i % cols) * thumb[0], (i // cols) * thumb[1]))
    sheet.save(out, "JPEG", quality=90)


def narrated_video(post: dict, scenes: list[Image.Image], out: Path, temp: Path, qa_dir: Path) -> dict:
    root = temp / post["series"]
    root.mkdir(parents=True, exist_ok=True)
    wav, bounds, audio_dur = azure.synthesize(post["script"], root, 80.0, None)
    srt = root / "subs.srt"
    cue_count = azure.subtitles(bounds, audio_dur, srt)
    scene_dir = root / "vertical-scenes"
    scene_dir.mkdir(exist_ok=True)
    for i, scene in enumerate(scenes, 1):
        vertical_frame(scene).save(scene_dir / f"{i:02d}.jpg", "JPEG", quality=92)
    per = audio_dur / len(scenes)
    concat = root / "scenes.txt"
    rows = []
    for i in range(1, len(scenes) + 1):
        rows += [f"file '{scene_dir / f'{i:02d}.jpg'}'", f"duration {per:.6f}"]
    rows.append(f"file '{scene_dir / f'{len(scenes):02d}.jpg'}'")
    concat.write_text("\n".join(rows) + "\n", encoding="utf-8")
    visual = root / "visual.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", str(visual)])
    style = "FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H9A000000,BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginL=48,MarginR=48,MarginV=110"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(visual), "-i", str(wav), "-vf", f"subtitles='{srt}':force_style='{style}'",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "1", "-shortest", "-movflags", "+faststart", str(out)])
    vd = duration(out)
    if vd < 80.0:
        raise RuntimeError(f"{post['series']} duration below 80 seconds: {vd}")
    probe = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(out)]))
    video = [s for s in probe["streams"] if s.get("codec_type") == "video"]
    audio = [s for s in probe["streams"] if s.get("codec_type") == "audio"]
    if len(video) != 1 or len(audio) != 1 or video[0].get("width") != 1080 or video[0].get("height") != 1920:
        raise RuntimeError(f"{post['series']} stream QA failed")
    run(["ffmpeg", "-v", "error", "-i", str(out), "-f", "null", "-"])
    preview_frames = []
    for n, stamp in enumerate((5.0, vd / 2, vd - 5.0), 1):
        shot = root / f"preview-{n}.jpg"
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{stamp:.3f}", "-i", str(out), "-frames:v", "1", "-q:v", "2", str(shot)])
        preview_frames.append(Image.open(shot).convert("RGB"))
    contact_sheet(preview_frames, qa_dir / f"{post['series']}-final-preview.jpg", thumb=(270, 480), cols=3)
    return {"series": post["series"], "duration_seconds": round(vd, 3), "voice": VOICE, "subtitle_cues": cue_count,
            "resolution": "1080x1920", "avatar": False, "background_music": False, "decode_passed": True,
            "sha256": sha256(out), "release_status": "PENDING_FINAL_VISUAL_REVIEW"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ns = ap.parse_args()
    data = json.loads(ns.manifest.read_text(encoding="utf-8"))
    if data.get("date") != "2026-10-09" or len(data.get("posts", [])) != 10:
        raise RuntimeError("Expected exactly ten posts for 2026-10-09")
    out = ns.output
    qa_dir = out.parent / "qa"
    temp = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "current-ten-20261009"
    out.mkdir(parents=True, exist_ok=True); qa_dir.mkdir(parents=True, exist_ok=True); temp.mkdir(parents=True, exist_ok=True)
    results = []
    for post in data["posts"]:
        series = post["series"]
        cols, rows, expected = GRID[series]
        source = ROOT / "production_20261009" / "sources" / f"{series}.jpg"
        scenes = crop_grid(source, cols, rows, expected)
        target = out / series
        target.mkdir(exist_ok=True)
        if post["format"] == "carousel":
            if len(post.get("cards", [])) != expected:
                raise RuntimeError(f"{series} card count mismatch")
            cards = []
            for i, (scene, text) in enumerate(zip(scenes, post["cards"]), 1):
                card = target / f"card-{i:02d}.jpg"
                draw_card(scene, text, card)
                cards.append(Image.open(card).convert("RGB"))
            yt = target / "youtube-short.mp4"
            slideshow(cards, yt, temp)
            contact_sheet(cards, qa_dir / f"{series}-final-preview.jpg", cols=3)
            files = sorted(target.glob("*.jpg")) + [yt]
            results.append({"series": series, "format": "carousel", "card_count": len(cards), "youtube_complete": True,
                            "resolution": "1080x1080", "files": [{"path": str(p.relative_to(ROOT)), "sha256": sha256(p), "bytes": p.stat().st_size} for p in files],
                            "release_status": "PENDING_FINAL_VISUAL_REVIEW"})
        else:
            if len(post["script"].split()) < 200 or not post["script"].rstrip().endswith(CTA):
                raise RuntimeError(f"Incomplete narrated script: {series}")
            video = target / "final.mp4"
            results.append(narrated_video(post, scenes, video, temp, qa_dir))
    (qa_dir / "technical-summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    journal = {
        "schema": "CURRENT_TEN_DAILY_DELIVERY_JOURNAL_V1",
        "date": "2026-10-09", "brand_id": 7076410, "timezone": "Europe/Athens",
        "baseline_logical_posts": 10, "destinations": 40,
        "voice": VOICE, "final_review": "PENDING_FINAL_VISUAL_REVIEW", "posts": results
    }
    (out.parent / "delivery_journal.json").write_text(json.dumps(journal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"posts": len(results), "status": "PENDING_FINAL_VISUAL_REVIEW"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
