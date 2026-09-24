#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from azure_speech_tts import synthesize

W, H = 1080, 1920
FPS = 30
VOICE = "el-GR-NestorasNeural"


def run(cmd):
    subprocess.run([str(x) for x in cmd], check=True)


def duration(path: Path) -> float:
    cp = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(cp.stdout.strip())


def srt_time(t: float) -> str:
    ms = int(round(max(0.0, t) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def two_lines(text: str, max_chars: int = 38) -> str:
    words = text.split()
    if len(text) <= max_chars or len(words) <= 4:
        return text
    best = None
    for i in range(1, len(words)):
        a = " ".join(words[:i])
        b = " ".join(words[i:])
        score = max(len(a), len(b)) + abs(len(a) - len(b)) * 0.25
        if best is None or score < best[0]:
            best = (score, a, b)
    return best[1] + "\\n" + best[2]


def caption_chunks(text: str, max_words: int = 8, max_chars: int = 46):
    out, cur = [], []
    for word in text.split():
        cand = " ".join(cur + [word])
        if cur and (len(cur) >= max_words or len(cand) > max_chars):
            out.append(" ".join(cur))
            cur = [word]
        else:
            cur.append(word)
    if cur:
        out.append(" ".join(cur))
    return out


def synth_segment(text: str, outwav: Path) -> None:
    last = None
    for attempt in range(8):
        try:
            synthesize(text, outwav, VOICE)
            return
        except RuntimeError as exc:
            last = exc
            if "HTTP 429" not in str(exc) or attempt == 7:
                raise
            time.sleep(15 * (attempt + 1))
    raise last


def download_commons(filename: str, dest: Path) -> None:
    quoted = urllib.parse.quote(filename.replace(" ", "_"), safe="()'-,._")
    url = f"https://commons.wikimedia.org/wiki/Special:Redirect/file/{quoted}?width=1800"
    req = urllib.request.Request(url, headers={"User-Agent": "SteliosTravelVideo/1.0 (Wikimedia Commons attribution workflow)"})
    with urllib.request.urlopen(req, timeout=120) as response:
        data = response.read()
    if len(data) < 20_000:
        raise RuntimeError(f"Downloaded image is unexpectedly small: {filename}")
    dest.write_bytes(data)
    with Image.open(dest) as im:
        im.verify()


def make_scene(src: Path, dest: Path) -> None:
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        # Full-frame blurred photographic background; sharp original photo centered.
        bg = ImageOps.fit(im, (W, H), method=Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=28))
        bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.12)

        max_w, max_h = 1000, 1500
        scale = min(max_w / im.width, max_h / im.height, 1.0)
        fg = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.Resampling.LANCZOS)
        x = (W - fg.width) // 2
        y = (H - fg.height) // 2
        bg.paste(fg, (x, y))
        bg.save(dest, quality=94, optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    assert manifest["approved"] is True
    assert manifest["publish_to_social"] is True
    assert manifest["voice"] == VOICE
    assert manifest["background_music"] is False
    assert manifest["min_duration_seconds"] >= 80

    segments = [s.strip() for s in manifest["narration_segments"] if s.strip()]
    images = manifest["images"]
    if len(segments) != len(images) or len(segments) < 10:
        raise RuntimeError("Narration/image scene count mismatch or too few scenes")
    if segments[-1] != "Αν σας άρεσε, ακολουθήστε για περισσότερα.":
        raise RuntimeError("Exact CTA is missing")

    root = Path(args.output)
    shutil.rmtree(root, ignore_errors=True)
    work = root / "work"
    result = root / "result"
    work.mkdir(parents=True)
    result.mkdir(parents=True)

    scene_files = []
    for i, img in enumerate(images, 1):
        raw = work / f"source-{i:02d}.jpg"
        scene = work / f"scene-{i:02d}.jpg"
        download_commons(img["filename"], raw)
        make_scene(raw, scene)
        scene_files.append(scene)

    wavs = []
    seg_durations = []
    for i, text in enumerate(segments, 1):
        raw = work / f"audio-{i:02d}-raw.wav"
        trimmed = work / f"audio-{i:02d}.wav"
        synth_segment(text, raw)
        run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", raw,
            "-af", "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-48dB,areverse,silenceremove=start_periods=1:start_duration=0.03:start_threshold=-48dB,areverse",
            "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", trimmed,
        ])
        d = duration(trimmed)
        if d <= 1:
            raise RuntimeError(f"Narration segment {i} too short")
        wavs.append(trimmed)
        seg_durations.append(d)

    total = sum(seg_durations)
    if total <= manifest["min_duration_seconds"]:
        raise RuntimeError(f"Duration gate failed: {total:.2f}s")

    # Exact sentence/segment timing from separately synthesized audio.
    srt = work / "subtitles.srt"
    t = 0.0
    sub_idx = 1
    with srt.open("w", encoding="utf-8") as f:
        for text, d in zip(segments, seg_durations):
            chunks = caption_chunks(text)
            weights = [max(1, len(c.replace(" ", ""))) for c in chunks]
            sw = sum(weights)
            used = 0
            for c, w in zip(chunks, weights):
                st = t + d * used / sw
                used += w
                en = t + d * used / sw
                f.write(f"{sub_idx}\n{srt_time(st)} --> {srt_time(en)}\n{two_lines(c)}\n\n")
                sub_idx += 1
            t += d

    audio_list = work / "audio-list.txt"
    audio_list.write_text("".join(f"file '{p.as_posix()}'\n" for p in wavs), encoding="utf-8")
    narration = work / "narration.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", audio_list, "-c:a", "pcm_s16le", narration])

    clips = []
    for i, (scene, d) in enumerate(zip(scene_files, seg_durations), 1):
        clip = work / f"clip-{i:02d}.mp4"
        frames = max(1, int(math.ceil(d * FPS)))
        direction = 1 if i % 2 else -1
        vf = (
            "scale=1140:2027,"
            "zoompan=z='min(zoom+0.00018,1.028)':"
            f"x='iw/2-(iw/zoom/2)+{direction}*7*sin(on/48)':"
            "y='ih/2-(ih/zoom/2)+6*cos(on/55)':"
            f"d={frames}:s=1080x1920:fps={FPS},format=yuv420p"
        )
        run([
            "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", scene,
            "-vf", vf, "-t", f"{d:.4f}", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", clip,
        ])
        clips.append(clip)

    clip_list = work / "clips.txt"
    clip_list.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8")
    visual = work / "visual.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", clip_list,
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS), visual])

    escaped = str(srt).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    style = (
        "FontName=DejaVu Sans,FontSize=20,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BackColour=&H90000000,BorderStyle=3,"
        "Outline=1,Shadow=0,Alignment=2,MarginL=88,MarginR=88,MarginV=290"
    )
    final = result / "monemvasia-travel-20260924.mp4"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", visual, "-i", narration,
        "-vf", f"subtitles='{escaped}':force_style='{style}'",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "1", "-shortest", "-movflags", "+faststart", final,
    ])

    fd = duration(final)
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(final)], capture_output=True, text=True, check=True).stdout)
    vs = [s for s in probe["streams"] if s.get("codec_type") == "video"]
    au = [s for s in probe["streams"] if s.get("codec_type") == "audio"]
    if len(vs) != 1 or len(au) != 1 or int(vs[0]["width"]) != W or int(vs[0]["height"]) != H or fd <= 80:
        raise RuntimeError("Final QA failed")

    qa = {
        "id": "travel-monemvasia-20260924-1830",
        "publish_to_social": True,
        "voice": VOICE,
        "duration_seconds": round(fd, 3),
        "resolution": "1080x1920",
        "burned_subtitles": True,
        "background_music": False,
        "avatar_presenter": False,
        "audio_streams": 1,
        "photo_count": len(images),
        "all_visuals_real_photos": True,
        "cta_exact": True,
        "min_duration_gate_passed": fd > 80,
    }
    (result / "qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    (result / "script.txt").write_text("\n\n".join(segments), encoding="utf-8")
    shutil.copy2(srt, result / "subtitles.srt")
    (result / "visual-attribution.json").write_text(json.dumps(images, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
