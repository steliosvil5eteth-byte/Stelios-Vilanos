#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageSequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from azure_speech_tts import synthesize

W, H = 1080, 1920
SR = 24000
PAUSE = 0.14
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def run(cmd: list[str | Path]) -> None:
    cmd = [str(x) for x in cmd]
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def ffprobe_duration(path: Path) -> float:
    cp = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return float(cp.stdout.strip())


def trim_wav(src: Path, dst: Path) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            src,
            "-af",
            (
                "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-48dB,"
                "areverse,"
                "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-48dB,"
                "areverse"
            ),
            "-ar",
            str(SR),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            dst,
        ]
    )


def srt_time(t: float) -> str:
    ms = int(round(max(0.0, t) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_caption(text: str, max_words: int = 7, max_chars: int = 42) -> list[str]:
    words = text.split()
    out: list[str] = []
    cur: list[str] = []
    for word in words:
        candidate = " ".join(cur + [word])
        if cur and (len(cur) >= max_words or len(candidate) > max_chars):
            out.append(" ".join(cur))
            cur = [word]
        else:
            cur.append(word)
    if cur:
        out.append(" ".join(cur))
    return out


def wrap_two_lines(text: str) -> str:
    words = text.split()
    if len(text) <= 29 or len(words) <= 3:
        return text
    mid = len(words) // 2
    return " ".join(words[:mid]) + "\n" + " ".join(words[mid:])


def download_assets(manifest: dict, work: Path) -> list[tuple[Path, dict]]:
    asset_dir = work / "assets"
    asset_dir.mkdir(parents=True)
    downloaded: list[tuple[Path, dict]] = []
    for i, asset in enumerate(manifest["assets"], 1):
        parsed = urllib.parse.urlparse(asset["url"])
        suffix = Path(parsed.path).suffix.lower() or ".jpg"
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            suffix = ".jpg"
        path = asset_dir / f"asset-{i:02d}{suffix}"
        req = urllib.request.Request(
            asset["url"], headers={"User-Agent": "SteliosSocialPreview/2.0"}
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            path.write_bytes(response.read())
        if path.stat().st_size < 10_000:
            raise RuntimeError(f"downloaded asset is unexpectedly small: {path.name}")
        downloaded.append((path, asset))
        print(f"asset={path.name} bytes={path.stat().st_size}")
    return downloaded


def build_photo_pool(downloaded: list[tuple[Path, dict]]) -> list[tuple[Image.Image, dict]]:
    frames: list[tuple[Image.Image, dict]] = []
    for path, meta in downloaded:
        image = Image.open(path)
        if getattr(image, "is_animated", False):
            sequence = list(ImageSequence.Iterator(image))
            if not sequence:
                continue
            picks = [0, len(sequence) // 4, len(sequence) // 2, (3 * len(sequence)) // 4, len(sequence) - 1]
            seen: set[int] = set()
            for idx in picks:
                idx = min(max(idx, 0), len(sequence) - 1)
                if idx in seen:
                    continue
                seen.add(idx)
                frames.append((sequence[idx].convert("RGB").copy(), meta))
        else:
            frames.append((image.convert("RGB"), meta))
    if len(frames) < 8:
        raise RuntimeError(f"photo pool too small: {len(frames)}")
    return frames


def synthesize_narration(manifest: dict, work: Path) -> tuple[list[str], list[Path], list[float], Path]:
    segments = [s.strip() for s in manifest["narration_segments"] if s.strip()]
    if len(segments) < 16:
        raise RuntimeError("too few narration segments")

    audio_paths: list[Path] = []
    durations: list[float] = []
    for i, text in enumerate(segments, 1):
        raw = work / f"seg-{i:02d}-raw.wav"
        clean = work / f"seg-{i:02d}.wav"
        synthesize(text, raw, manifest["voice"])
        trim_wav(raw, clean)
        d = ffprobe_duration(clean)
        if d < 0.4:
            raise RuntimeError(f"segment {i} is too short: {d:.3f}s")
        audio_paths.append(clean)
        durations.append(d)

    narration = work / "narration.wav"
    silence_frames = int(round(PAUSE * SR))
    with wave.open(str(narration), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SR)
        for i, audio in enumerate(audio_paths):
            with wave.open(str(audio), "rb") as source:
                out.writeframes(source.readframes(source.getnframes()))
            if i != len(audio_paths) - 1:
                out.writeframes(b"\x00\x00" * silence_frames)

    total = ffprobe_duration(narration)
    if total <= float(manifest["min_duration_seconds"]):
        raise RuntimeError(
            f"duration gate failed: {total:.2f}s <= {manifest['min_duration_seconds']}s"
        )
    print(f"narration_seconds={total:.3f}")
    return segments, audio_paths, durations, narration


def make_subtitles(segments: list[str], durations: list[float], work: Path) -> Path:
    srt = work / "subtitles.srt"
    t = 0.0
    index = 1
    with srt.open("w", encoding="utf-8") as handle:
        for i, (text, segment_duration) in enumerate(zip(segments, durations)):
            chunks = split_caption(text)
            weights = [max(1, len(x.replace(" ", ""))) for x in chunks]
            total_weight = sum(weights)
            consumed = 0
            for chunk, weight in zip(chunks, weights):
                start = t + segment_duration * consumed / total_weight
                consumed += weight
                end = t + segment_duration * consumed / total_weight
                handle.write(
                    f"{index}\n{srt_time(start)} --> {srt_time(end)}\n"
                    f"{wrap_two_lines(chunk)}\n\n"
                )
                index += 1
            t += segment_duration
            if i != len(segments) - 1:
                t += PAUSE
    return srt


def prepare_scenes(
    photo_pool: list[tuple[Image.Image, dict]],
    count: int,
    work: Path,
    credits: list[str],
) -> list[Path]:
    scene_dir = work / "scenes"
    scene_dir.mkdir(parents=True)
    title_font = ImageFont.truetype(BOLD, 32)
    small_font = ImageFont.truetype(FONT, 18)
    credit_font = ImageFont.truetype(FONT, 14)

    scenes: list[Path] = []
    for i in range(count):
        base, _ = photo_pool[(i * 3 + i // 4) % len(photo_pool)]
        source = base.copy()

        bg = ImageOps.fit(
            source,
            (W, H),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        ).filter(ImageFilter.GaussianBlur(20))
        bg = Image.alpha_composite(
            bg.convert("RGBA"), Image.new("RGBA", (W, H), (0, 0, 0, 92))
        )

        foreground = source.copy()
        foreground.thumbnail((1000, 1360), Image.Resampling.LANCZOS)
        card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        x = (W - foreground.width) // 2
        y = 220 + (1360 - foreground.height) // 2

        shadow = Image.new(
            "RGBA", (foreground.width + 28, foreground.height + 28), (0, 0, 0, 0)
        )
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle(
            (4, 4, foreground.width + 24, foreground.height + 24),
            radius=18,
            fill=(0, 0, 0, 120),
        )
        card.alpha_composite(shadow, (x - 14, y - 14))
        card.alpha_composite(foreground.convert("RGBA"), (x, y))

        canvas = Image.alpha_composite(bg, card)
        draw = ImageDraw.Draw(canvas)

        draw.rounded_rectangle((52, 68, 690, 122), radius=17, fill=(0, 0, 0, 150))
        draw.text(
            (75, 78), "ΗΦΑΙΣΤΕΙΑΚΟΙ ΚΕΡΑΥΝΟΙ", font=title_font, fill="white"
        )
        draw.text(
            (58, 1780),
            "Πραγματικό φυσικό φαινόμενο",
            font=small_font,
            fill=(232, 232, 232, 255),
        )

        if i == count - 1:
            draw.rounded_rectangle((38, 1685, 1042, 1760), radius=15, fill=(0, 0, 0, 165))
            draw.text(
                (56, 1697),
                "Εικόνες: USGS Public Domain • Etrhamjr/Hike395 CC BY-SA 4.0",
                font=credit_font,
                fill="white",
            )
            draw.text(
                (56, 1725),
                "R. Hadian/Zanaq CC BY-SA 1.0",
                font=credit_font,
                fill="white",
            )

        path = scene_dir / f"scene-{i:02d}.jpg"
        canvas.convert("RGB").save(path, "JPEG", quality=93, subsampling=0)
        scenes.append(path)

    return scenes


def render_video(
    scenes: list[Path],
    durations: list[float],
    narration: Path,
    srt: Path,
    work: Path,
    final: Path,
) -> None:
    clips: list[Path] = []
    for i, (scene, segment_duration) in enumerate(zip(scenes, durations)):
        clip = work / f"clip-{i:02d}.mp4"
        clip_duration = segment_duration + (PAUSE if i != len(scenes) - 1 else 0.0)
        frame_count = max(1, int(math.ceil(clip_duration * 30)))
        direction = 1 if i % 2 == 0 else -1
        x_expr = f"iw/2-(iw/zoom/2)+{direction}*9*sin(on/45)"
        y_expr = "ih/2-(ih/zoom/2)+7*cos(on/53)"
        vf = (
            "scale=1200:2134,"
            "zoompan="
            "z='min(zoom+0.00020,1.032)':"
            f"x='{x_expr}':y='{y_expr}':"
            f"d={frame_count}:s=1080x1920:fps=30,"
            "format=yuv420p"
        )
        run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-loop",
                "1",
                "-i",
                scene,
                "-vf",
                vf,
                "-t",
                f"{clip_duration:.4f}",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                clip,
            ]
        )
        clips.append(clip)

    concat = work / "clips.txt"
    concat.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8"
    )
    visual = work / "visual.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "22",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            visual,
        ]
    )

    escaped = (
        str(srt).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    )
    style = (
        "FontName=DejaVu Sans,"
        "FontSize=20,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BackColour=&H90000000,"
        "BorderStyle=3,"
        "Outline=1,"
        "Shadow=0,"
        "Alignment=2,"
        "MarginL=92,"
        "MarginR=92,"
        "MarginV=300"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            visual,
            "-i",
            narration,
            "-vf",
            f"subtitles='{escaped}':force_style='{style}'",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-shortest",
            "-movflags",
            "+faststart",
            final,
        ]
    )


def qa(final: Path, manifest: dict, photo_pool_size: int) -> dict:
    duration = ffprobe_duration(final)
    cp = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(final)],
        check=True,
        text=True,
        capture_output=True,
    )
    streams = json.loads(cp.stdout)["streams"]
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if len(videos) != 1 or len(audios) != 1:
        raise RuntimeError("stream QA failed")
    if int(videos[0]["width"]) != W or int(videos[0]["height"]) != H:
        raise RuntimeError("resolution QA failed")
    if duration <= float(manifest["min_duration_seconds"]):
        raise RuntimeError("duration QA failed")

    return {
        "id": "volcanic-lightning-preview-v2",
        "preview_only": True,
        "publish_to_social": False,
        "voice": manifest["voice"],
        "duration_seconds": round(duration, 3),
        "resolution": f"{W}x{H}",
        "burned_subtitles": True,
        "subtitle_font_size": 20,
        "subtitle_margin_vertical": 300,
        "subtitle_max_lines": 2,
        "photo_based_visuals": True,
        "photo_pool_frames": photo_pool_size,
        "background_music": False,
        "avatar_presenter": False,
        "asset_credits": [x["credit"] for x in manifest["assets"]],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if not manifest.get("approved"):
        raise RuntimeError("manifest is not approved")
    if manifest.get("preview_only") is not True:
        raise RuntimeError("preview_only must be true")
    if manifest.get("publish_to_social") is not False:
        raise RuntimeError("publish_to_social must be false")
    if manifest.get("voice") != "el-GR-NestorasNeural":
        raise RuntimeError("voice must be el-GR-NestorasNeural")

    root = Path(args.output)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    work = root / "work"
    work.mkdir()
    job = root / "preview"
    job.mkdir()

    downloaded = download_assets(manifest, work)
    pool = build_photo_pool(downloaded)
    segments, _, durations, narration = synthesize_narration(manifest, work)
    srt = make_subtitles(segments, durations, work)
    scenes = prepare_scenes(
        pool, len(segments), work, [x["credit"] for x in manifest["assets"]]
    )
    final = job / "volcanic-lightning-preview-v2-nestoras.mp4"
    render_video(scenes, durations, narration, srt, work, final)

    report = qa(final, manifest, len(pool))
    (job / "qa.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (job / "script.txt").write_text("\n".join(segments), encoding="utf-8")
    shutil.copy2(srt, job / "subtitles.srt")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
