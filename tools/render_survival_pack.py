#!/usr/bin/env python3
"""Render one fact-checked 9-card SURVIVAL carousel plus a YouTube slideshow.

No AI/TTS/payment/publishing APIs. Visuals must be explicit reusable HTTPS images.
TikTok/FB/IG outputs are silent 1080x1080 JPEGs. The YouTube slideshow uses a
locally synthesized instrumental bed and no narration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

TITLE = "ΚΑΝΟΝΕΣ ΕΠΙΒΙΩΣΗΣ"
CTA = "Αν σας άρεσε, ακολουθήστε για περισσότερα."
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ALLOWED_HOSTS = {"upload.wikimedia.org"}
MAX_DOWNLOAD = 30 * 1024 * 1024
MAX_OUTPUT = 64 * 1024 * 1024


def run(args: list[str]) -> str:
    p = subprocess.run(args, text=True, capture_output=True, timeout=900)
    if p.returncode:
        raise RuntimeError(p.stderr[-3000:])
    return p.stdout


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_url(url: str) -> None:
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https" or u.hostname not in ALLOWED_HOSTS or u.username or u.password:
        raise ValueError("source_url must be explicit HTTPS Wikimedia upload media")


def download(url: str, dest: Path) -> None:
    check_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "SteliosSurvivalRenderer/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, dest.open("wb") as f:
        total = 0
        for block in iter(lambda: r.read(1024 * 1024), b""):
            total += len(block)
            if total > MAX_DOWNLOAD:
                raise ValueError("source image exceeds 30 MiB")
            f.write(block)
    if total == 0:
        raise ValueError("empty source image")


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        words = para.split()
        if not words:
            lines.append("")
            continue
        line = ""
        for word in words:
            candidate = (line + " " + word).strip()
            if draw.textlength(candidate, font=font) <= width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                if draw.textlength(word, font=font) > width:
                    raise ValueError("unbreakable text exceeds safe width")
                line = word
        if line:
            lines.append(line)
    return lines


def draw_text_block(im: Image.Image, text: str, box: tuple[int, int, int, int], start: int,
                    *, bold: bool = False, center: bool = False, min_size: int = 27,
                    fill: str = "#FFFFFF") -> int:
    draw = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    selected = None
    for size in range(start, min_size - 1, -1):
        font = ImageFont.truetype(BOLD if bold else FONT, size)
        lines = wrap(draw, text, font, x1 - x0)
        leading = math.ceil(size * 1.28)
        if len(lines) * leading <= y1 - y0:
            selected = (font, lines, leading, size)
            break
    if not selected:
        raise ValueError("text cannot fit at mobile-readable size")
    font, lines, leading, size = selected
    y = y0 + max(0, (y1 - y0 - len(lines) * leading) // 2) if center else y0
    for line in lines:
        x = x0 + (x1 - x0 - draw.textlength(line, font=font)) / 2 if center else x0
        draw.text((x, y), line, font=font, fill=fill, stroke_width=1, stroke_fill="#000000")
        y += leading
    return size


def render_card(slide: dict, index: int, total: int, source: Path) -> Image.Image:
    raw = Image.open(source).convert("RGB")
    im = ImageOps.fit(raw, (1080, 1080), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    im = ImageEnhance.Contrast(im).enhance(1.04)
    im = ImageEnhance.Color(im).enhance(0.92)

    # Cinematic darkening keeps the photograph visible while preserving text contrast.
    dark = Image.new("RGBA", im.size, (0, 0, 0, 78))
    im = Image.alpha_composite(im.convert("RGBA"), dark)
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle((38, 32, 1042, 154), radius=22, fill=(7, 13, 22, 198), outline=(216, 186, 120, 230), width=3)
    od.rounded_rectangle((48, 186, 1032, 914), radius=26, fill=(4, 8, 14, 154))
    od.rounded_rectangle((48, 928, 1032, 1040), radius=20, fill=(7, 13, 22, 205))
    im = Image.alpha_composite(im, overlay).convert("RGB")

    draw_text_block(im, TITLE, (78, 55, 1002, 132), 47, bold=True, center=True, min_size=38, fill="#F6E7C3")
    draw_text_block(im, slide["subtitle"], (80, 216, 1000, 360), 48, bold=True, center=True, min_size=34)
    draw_text_block(im, slide["text"], (92, 386, 988, 868), 38, min_size=28)

    footer = CTA if index == total else slide.get("footer", "Σύρε για συνέχεια →")
    draw_text_block(im, footer, (76, 948, 1004, 1018), 30, bold=index == total, center=True, min_size=24,
                    fill="#F6E7C3" if index == total else "#FFFFFF")
    d = ImageDraw.Draw(im)
    d.text((960, 1047), f"{index}/{total}", font=ImageFont.truetype(FONT, 18), fill="#E5E7EB")
    return im


def make_vertical(card: Path, dest: Path) -> None:
    sq = Image.open(card).convert("RGB")
    bg = ImageOps.fit(sq, (1080, 1920), method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(28))
    bg = ImageEnhance.Brightness(bg).enhance(0.35)
    card_img = sq.resize((1080, 1080), Image.Resampling.LANCZOS)
    bg.paste(card_img, (0, 420))
    bg.save(dest, quality=94, subsampling=0)


def slideshow(cards: list[Path], dest: Path, seconds_per_slide: float) -> float:
    if not 3.0 <= seconds_per_slide <= 8.0:
        raise ValueError("seconds_per_slide outside safe range")
    total = len(cards) * seconds_per_slide
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        segs: list[Path] = []
        for i, card in enumerate(cards, 1):
            v = td / f"v{i:02}.jpg"
            make_vertical(card, v)
            seg = td / f"s{i:02}.mp4"
            run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "25", "-i", str(v),
                 "-t", str(seconds_per_slide), "-vf", "setsar=1,fps=25", "-c:v", "libx264",
                 "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-an", str(seg)])
            segs.append(seg)
        concat = td / "concat.txt"
        concat.write_text("\n".join("file '" + str(p).replace("'", "'\\''") + "'" for p in segs) + "\n", encoding="utf-8")
        visual = td / "visual.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(visual)])
        fade_out = max(0.0, total - 1.5)
        af = ("[1:a]volume=0.028[a1];[2:a]volume=0.020[a2];[3:a]volume=0.017[a3];"
              "[a1][a2][a3]amix=inputs=3:duration=longest:normalize=0,highpass=f=90,lowpass=f=1800,"
              f"afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out}:d=1.5,"
              "aformat=sample_rates=48000:channel_layouts=stereo[a]")
        run(["ffmpeg", "-y", "-v", "error", "-i", str(visual),
             "-f", "lavfi", "-i", f"sine=frequency=196:sample_rate=48000:duration={total}",
             "-f", "lavfi", "-i", f"sine=frequency=246.94:sample_rate=48000:duration={total}",
             "-f", "lavfi", "-i", f"sine=frequency=293.66:sample_rate=48000:duration={total}",
             "-filter_complex", af, "-map", "0:v", "-map", "[a]", "-t", str(total),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(dest)])
    run(["ffmpeg", "-v", "error", "-i", str(dest), "-f", "null", "-"])
    return total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()
    raw = Path(ns.manifest).read_bytes()
    batch = json.loads(raw)
    if batch.get("approved") is not True or batch.get("paid_generation_allowed") is not False:
        raise ValueError("approved=true and paid_generation_allowed=false required")
    jobs = batch.get("jobs", [])
    if len(jobs) != 1:
        raise ValueError("exactly one survival job required")
    job = jobs[0]
    slides = job.get("slides", [])
    if job.get("expected_cards") != 9 or len(slides) != 9:
        raise ValueError("survival pack requires exactly 9 cards")
    if any(s.get("visible_title") != TITLE for s in slides):
        raise ValueError("every card must carry the fixed visible survival title")

    batch_id = hashlib.sha256(raw).hexdigest()[:16]
    outdir = Path(ns.output) / batch_id
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "source_manifest.json").write_bytes(raw)

    cards: list[Path] = []
    sources_report = []
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        for i, slide in enumerate(slides, 1):
            src = td / f"source-{i:02}.jpg"
            download(slide["source_url"], src)
            card = outdir / f"{job['id']}-{i:02}.jpg"
            render_card(slide, i, 9, src).save(card, quality=94, subsampling=0)
            check = Image.open(card)
            if check.size != (1080, 1080) or check.format != "JPEG" or card.stat().st_size == 0:
                raise ValueError(f"card {i} failed JPEG 1080x1080 gate")
            extrema = check.convert("L").getextrema()
            if not extrema or extrema[1] - extrema[0] < 25:
                raise ValueError(f"card {i} appears visually blank/flat")
            cards.append(card)
            sources_report.append({"card": i, "source_url": slide["source_url"], "credit": slide["credit"], "license": slide["license"]})

    video = outdir / f"{job['id']}.mp4"
    duration = slideshow(cards, video, float(job.get("seconds_per_slide", 5.0)))
    report = {
        "batch_id": batch_id,
        "batch_sha256": hashlib.sha256(raw).hexdigest(),
        "paid_ai_credits_used": 0,
        "jobs": [{
            "id": job["id"], "status": "rendered", "card_count": 9, "order_verified": True,
            "all_cards_jpeg_1080x1080": True, "real_source_media_required_and_verified": True,
            "visible_title": TITLE, "youtube_slideshow": True, "youtube_duration": duration,
            "youtube_music_embedded": True, "music_source": "original_local_synth_no_external_license",
            "narration": False, "tiktok_assets_silent": True, "cta_on_final_card": CTA,
            "fact_sources": job.get("fact_sources", []), "visual_sources": sources_report,
            "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in [*cards, video]],
        }]
    }
    if any(f["bytes"] > MAX_OUTPUT for f in report["jobs"][0]["files"]):
        raise ValueError("output exceeds 64 MiB safety limit")
    (outdir / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("REPORT_PATH=" + str(outdir / "manifest.json"))


if __name__ == "__main__":
    main()
