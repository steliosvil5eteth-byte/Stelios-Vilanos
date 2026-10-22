"""Render 21 Oct carousel candidates from explicitly selected Pexels photos.

A successful render is only a candidate build. It never grants final QA. Zodiac validation requires six two-sign cards covering all 12 signs exactly once.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / "production/carousel_20261022/request.json"
OUT = ROOT / "media/carousel_20261022"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BG = (247, 243, 235)
INK = (26, 30, 34)
BRAND = "Ιστορίες που μας αγγίζουν"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int, bold: bool = False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def wrap(text: str, ft, width: int) -> list[str]:
    rows: list[str] = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = (line + " " + word).strip()
            if ft.getlength(candidate) > width:
                if not line:
                    raise ValueError(f"Word does not fit: {word}")
                rows.append(line)
                line = word
            else:
                line = candidate
        if line:
            rows.append(line)
    return rows


def fit(text: str, width: int, height: int, maximum: int, minimum: int, bold=False):
    for size in range(maximum, minimum - 1, -1):
        ft = font(size, bold)
        rows = wrap(text, ft, width)
        step = math.ceil(size * 1.25)
        if len(rows) * step <= height:
            return ft, rows, step
    raise ValueError("Text needs shortening: " + text)


def text_block(canvas, text, box, maximum, minimum, bold=False, fill=INK, center=False):
    x, y, width, height = box
    ft, rows, step = fit(text, width, height, maximum, minimum, bold)
    draw = ImageDraw.Draw(canvas)
    for row in rows:
        xx = x + (width - ft.getlength(row)) / 2 if center else x
        draw.text((xx, y), row, font=ft, fill=fill)
        y += step
    return ft.size, len(rows)


def download(url: str, target: Path):
    if url.startswith("repo://"):
        source = ROOT / url.removeprefix("repo://")
        shutil.copyfile(source, target)
        im = Image.open(target).convert("RGB")
        if min(im.size) < 650:
            raise ValueError(f"Local source too small: {url} {im.size}")
        return im
    req = urllib.request.Request(url, headers={"User-Agent": "CarouselRenderer/20261022"})
    with urllib.request.urlopen(req, timeout=90) as response:
        ctype = response.headers.get("content-type", "")
        if not ctype.startswith("image/"):
            raise ValueError(f"Not an image: {url} ({ctype})")
        target.write_bytes(response.read())
    im = Image.open(target)
    im.verify()
    im = Image.open(target).convert("RGB")
    if min(im.size) < 900:
        raise ValueError(f"Source too small: {url} {im.size}")
    return im


def make_card(photo: Image.Image, post: dict, index: int, cta: str):
    im = Image.new("RGB", (1080, 1080), BG)
    # Greece/Spain source panels already contain an old top counter. Crop it before adding our own single 01/10 counter.
    if post["series"] == "greece_vs_country":
        trim = max(24, round(photo.height * 0.08))
        photo = photo.crop((0, trim, photo.width, photo.height))
    photo = ImageOps.fit(photo, (1080, 650), method=Image.Resampling.LANCZOS, centering=(0.5, 0.45))
    im.paste(photo, (0, 0))
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle((28, 24, 622, 81), radius=14, fill=(10, 14, 20, 218))
    od.text((46, 33), BRAND, font=font(29, True), fill="white")
    od.rounded_rectangle((939, 24, 1053, 81), radius=14, fill=(10, 14, 20, 218))
    od.text((958, 33), f"{index + 1:02d}/{len(post['copy']):02d}", font=font(28, True), fill="white")
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 650, 1080, 657), fill=(173, 130, 73))
    if index == len(post["copy"]) - 1:
        body_size, body_lines = text_block(im, post["copy"][index], (48, 677, 984, 225), 43, 32)
        cta_size, cta_lines = text_block(im, cta, (48, 910, 984, 90), 36, 32, True)
    else:
        body_size, body_lines = text_block(im, post["copy"][index], (48, 680, 984, 320), 46 if index == 0 else 43, 32, index == 0)
        cta_size, cta_lines = None, 0
    draw = ImageDraw.Draw(im)
    draw.line((48, 1028, 1032, 1028), fill=(202, 194, 181), width=2)
    draw.text((48, 1038), post["disclosure"], font=font(22), fill=(77, 76, 72))
    return im, {
        "body_font_px": body_size,
        "body_lines": body_lines,
        "cta_font_px": cta_size,
        "cta_lines": cta_lines,
        "unclipped": True,
    }


def vertical_frame(card: Image.Image, post: dict):
    frame = Image.new("RGB", (1080, 1920), (17, 22, 28))
    text_block(frame, post["title"], (62, 115, 956, 230), 58, 40, True, (249, 247, 241), True)
    # Paste the entire square card. No crop.
    frame.paste(card, (0, 420))
    text_block(frame, "Ολόκληρη κάρτα · χρόνος ανάγνωσης ≥ 11″", (70, 1580, 940, 90), 33, 27, False, (233, 224, 209), True)
    text_block(frame, BRAND, (70, 1710, 940, 100), 40, 34, True, (233, 224, 209), True)
    return frame


def contact(images: list[Image.Image], path: Path, columns: int, width: int):
    rows = math.ceil(len(images) / columns)
    height = round(width * images[0].height / images[0].width)
    sheet = Image.new("RGB", (columns * width, rows * height), "white")
    for i, image in enumerate(images):
        sheet.paste(image.resize((width, height), Image.Resampling.LANCZOS), ((i % columns) * width, (i // columns) * height))
    sheet.save(path, quality=94)


def main():
    request = json.loads(REQUEST.read_text())
    assert request["brand_id"] == 7076410
    assert request["date"] == "2026-10-22"
    assert len(request["posts"]) == 4
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "date": request["date"],
        "brand_id": request["brand_id"],
        "program": request["program"],
        "qa_status": "NEEDS_EXACT_FINAL_REVIEW",
        "request_sha256": sha(REQUEST),
        "paid_charges_eur": 0,
        "generation_credits_used": 0,
        "posts": [],
    }
    global_sources = ["# Source ledger", "", f"Pexels license: {request['source_license']}", "", "## Official comparison sources", *[f"- {x}" for x in request.get("sources", [])], ""]
    seen_source_hashes = set()
    for post in request["posts"]:
        expected_count = 10 if post["series"] == "greece_vs_country" else 6
        assert len(post["copy"]) == expected_count
        if post["series"] == "zodiac_pairs_all_twelve":
            expected_signs = {"Κριός","Ταύρος","Δίδυμοι","Καρκίνος","Λέων","Παρθένος","Ζυγός","Σκορπιός","Τοξότης","Αιγόκερως","Υδροχόος","Ιχθύες"}
            assert len(post["sign_pairs"]) == 6
            flat = [sign for pair in post["sign_pairs"] for sign in pair]
            assert len(flat) == 12 and set(flat) == expected_signs
        assert len(post["photos"]) == expected_count
        assert request["cta"] in post["caption"]
        assert len([w for w in post["caption"].split() if w.startswith("#")]) <= 5
        folder = OUT / post["id"]
        source_dir = folder / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        cards: list[Image.Image] = []
        frames: list[Path] = []
        durations: list[int] = []
        card_rows = []
        global_sources += [f"## {post['title']}", ""]
        for index, (url, page, alt) in enumerate(post["photos"]):
            print(f"DOWNLOADING {post['id']} {index + 1}/{len(post['photos'])} {url}", flush=True)
            source_path = source_dir / f"source_{index + 1:02d}.jpg"
            photo = download(url, source_path)
            source_hash = sha(source_path)
            if source_hash in seen_source_hashes:
                raise ValueError(f"Duplicate source image hash: {source_hash} in {post['id']}")
            seen_source_hashes.add(source_hash)
            card, layout = make_card(photo, post, index, request["cta"])
            card_path = folder / f"card_{index + 1:02d}.jpg"
            card.save(card_path, quality=95, subsampling=0)
            exact = Image.open(card_path).convert("RGB")
            cards.append(exact.copy())
            frame_path = folder / f"frame_{index + 1:02d}.png"
            vertical_frame(exact, post).save(frame_path)
            frames.append(frame_path)
            words = len(post["copy"][index].split()) + (len(request["cta"].split()) if index == 5 else 0)
            duration = max(12, math.ceil(words / 2.35 + 2))
            durations.append(duration)
            global_sources.append(f"{index + 1}. [{alt}]({page})")
            card_rows.append({
                "path": str(card_path.relative_to(OUT)),
                "sha256": sha(card_path),
                "source_path": str(source_path.relative_to(OUT)),
                "source_sha256": source_hash,
                "source_page": page,
                "source_url": url,
                "source_alt": alt,
                "duration_seconds": duration,
                **layout,
            })
        global_sources.append("")
        contact(cards, folder / "cards_review.jpg", 5 if len(cards) == 10 else 3, 360 if len(cards) == 10 else 540)
        concat = folder / "video.ffconcat"
        parts = ["ffconcat version 1.0"]
        for frame_path, duration in zip(frames, durations):
            parts += [f"file '{frame_path.as_posix()}'", f"duration {duration}"]
        parts.append(f"file '{frames[-1].as_posix()}'")
        concat.write_text("\n".join(parts) + "\n")
        video_path = folder / "youtube_vertical.mp4"
        total = sum(durations)
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-safe", "0", "-i", str(concat),
            "-t", str(total), "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "21",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(video_path)
        ], check=True)
        probe = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video_path)
        ]))
        video_streams = [s for s in probe["streams"] if s["codec_type"] == "video"]
        audio_streams = [s for s in probe["streams"] if s["codec_type"] == "audio"]
        assert len(video_streams) == 1 and not audio_streams
        assert video_streams[0]["width"] == 1080 and video_streams[0]["height"] == 1920
        actual_duration = float(probe["format"]["duration"])
        # Concat demuxer + CFR normalization can round each still boundary.
        # Enforce the editorial requirement (at least 11 seconds per card)
        # and reject a materially extended result; preserve the exact delta
        # in the manifest for final review.
        assert actual_duration >= 11 * len(post["copy"])
        assert actual_duration <= total + 2.0
        decoded: list[Image.Image] = []
        cursor = 0
        for index, duration in enumerate(durations):
            decoded_path = folder / f"encoded_frame_{index + 1:02d}.jpg"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(cursor + duration / 2),
                "-i", str(video_path), "-frames:v", "1", "-q:v", "2", str(decoded_path)
            ], check=True)
            decoded.append(Image.open(decoded_path).convert("RGB"))
            cursor += duration
        contact(decoded, folder / "encoded_video_review.jpg", 3, 360)
        for frame_path in frames:
            frame_path.unlink()
        concat.unlink()
        manifest["posts"].append({
            "id": post["id"], "title": post["title"], "time": post["time"], "series": post["series"],
            "fingerprint": post["fingerprint"], "qa_status": "NEEDS_EXACT_FINAL_REVIEW", "cards": card_rows,
            "youtube_video": {
                "path": str(video_path.relative_to(OUT)), "sha256": sha(video_path), "width": 1080, "height": 1920,
                "duration_seconds": actual_duration, "planned_duration_seconds": total,
                "duration_delta_seconds": actual_duration - total,
                "card_durations": durations, "fps": 24, "audio_streams": 0,
            },
            "caption": post["caption"],
        })
    (OUT / "SOURCES.md").write_text("\n".join(global_sources) + "\n")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"rendered_candidates": len(manifest["posts"]), "qa_status": manifest["qa_status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

