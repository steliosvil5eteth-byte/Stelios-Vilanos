#!/usr/bin/env python3
"""Deterministic local visuals for 2026-09-24 current narrated features.
No external images, no paid APIs. Supports volcanic lightning and Baba Yaga.
"""
from __future__ import annotations

import hashlib
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BG_W, BG_H = 1200, 2134
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def gradient(draw, top, bottom):
    for y in range(BG_H):
        t = y / max(1, BG_H - 1)
        c = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        draw.line((0, y, BG_W, y), fill=c)


def label(draw, text, y=84):
    f = ImageFont.truetype(BOLD, 30)
    box = draw.textbbox((0, 0), text, font=f)
    w = min(BG_W - 120, box[2] - box[0] + 48)
    draw.rounded_rectangle((60, y, 60 + w, y + 62), radius=18, fill=(0, 0, 0))
    draw.text((82, y + 11), text, font=f, fill="white")


def lightning(draw, pts, width=11):
    draw.line(pts, fill=(255, 245, 184), width=width, joint="curve")
    draw.line(pts, fill=(255, 255, 245), width=max(3, width // 3), joint="curve")


def draw_volcanic_lightning(draw, idx, total, rng):
    gradient(draw, (31, 39, 56), (7, 8, 13))
    horizon = 1450
    # volcanic cone
    draw.polygon([(60, horizon), (455, 920), (610, 820), (760, 940), (1140, horizon)], fill=(38, 31, 30))
    draw.polygon([(390, 1000), (610, 820), (820, 1040), (675, 990), (590, 950)], fill=(59, 43, 37))
    # ash plume, different composition each segment
    cx = 610 + int(50 * math.sin(idx * .45))
    for k in range(20):
        y = 870 - k * 39 + rng.randint(-22, 22)
        spread = 90 + k * 15
        x = cx + rng.randint(-spread, spread)
        rx = rng.randint(85, 180)
        ry = rng.randint(55, 115)
        shade = rng.randint(78, 130)
        draw.ellipse((x-rx, y-ry, x+rx, y+ry), fill=(shade, shade, shade+5))
    mode = idx % 6
    if mode in (0, 2, 4):
        for off in (-260, 40, 280):
            x0 = cx + off + rng.randint(-60, 60)
            pts = [(x0, 330), (x0-45, 485), (x0+20, 570), (x0-70, 720), (x0-20, 875)]
            lightning(draw, pts, 10)
    if mode == 1:
        # particle collision motif
        for _ in range(55):
            x = rng.randint(220, 980); y = rng.randint(420, 1050); r = rng.randint(3, 9)
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(210, 206, 194))
        label(draw, "ΣΥΓΚΡΟΥΣΕΙΣ ΣΤΑΧΤΗΣ • ΔΙΑΧΩΡΙΣΜΟΣ ΦΟΡΤΙΟΥ")
    elif mode == 3:
        # icy upper plume motif
        for _ in range(35):
            x = rng.randint(180, 1020); y = rng.randint(240, 650); r = rng.randint(4, 10)
            draw.polygon([(x, y-r), (x+r, y), (x, y+r), (x-r, y)], fill=(200, 228, 240))
        label(draw, "ΠΑΓΟΣ + ΥΔΡΑΤΜΟΙ • ΗΛΕΚΤΡΙΣΜΟΣ ΨΗΛΑ ΣΤΟ ΝΕΦΟΣ")
    elif mode == 5:
        # expanding ring motif inspired by measured lightning locations, not a literal photo
        for r in (180, 300, 430):
            draw.ellipse((cx-r, 480-r//3, cx+r, 480+r//3), outline=(232, 223, 162), width=8)
        label(draw, "HUNGA 2022 • ΔΑΚΤΥΛΙΟΙ ΚΕΡΑΥΝΩΝ ΣΤΟ ΝΕΦΟΣ")
    else:
        label(draw, "ΗΦΑΙΣΤΕΙΑΚΟΙ ΚΕΡΑΥΝΟΙ • ΠΡΑΓΜΑΤΙΚΟ ΦΑΙΝΟΜΕΝΟ")
    # lava glow at vent for cinematic depth
    draw.ellipse((545, 805, 675, 890), fill=(179, 72, 35))


def draw_baba_yaga(draw, idx, total, rng):
    gradient(draw, (23, 31, 48), (5, 8, 13))
    # moon
    mx = 925 - int(60 * math.sin(idx * .27)); my = 300
    draw.ellipse((mx-120, my-120, mx+120, my+120), fill=(218, 214, 178))
    # layered forest
    for layer, base_y, col in ((0, 1550, (27, 42, 37)), (1, 1710, (17, 31, 28))):
        step = 105 if layer == 0 else 85
        for x in range(-40, BG_W+60, step):
            h = rng.randint(360, 650)
            draw.rectangle((x+35, base_y-h//3, x+48, BG_H), fill=col)
            draw.polygon([(x, base_y), (x+42, base_y-h), (x+85, base_y)], fill=col)
    # hut with chicken legs
    hut_x = 300 + int(45 * math.sin(idx * .4)); hut_y = 1080
    draw.polygon([(hut_x, hut_y), (hut_x+250, hut_y-175), (hut_x+500, hut_y), (hut_x+470, hut_y+300), (hut_x+30, hut_y+300)], fill=(92, 63, 43))
    draw.polygon([(hut_x-30, hut_y+20), (hut_x+250, hut_y-230), (hut_x+530, hut_y+20)], fill=(54, 40, 34))
    draw.rectangle((hut_x+180, hut_y+100, hut_x+310, hut_y+300), fill=(43, 28, 24))
    draw.rectangle((hut_x+70, hut_y+80, hut_x+145, hut_y+155), fill=(203, 158, 77))
    # articulated bird-like legs
    for lx in (hut_x+150, hut_x+360):
        draw.line((lx, hut_y+300, lx-35, hut_y+520), fill=(156, 125, 82), width=26)
        draw.line((lx-35, hut_y+520, lx-120, hut_y+580), fill=(156, 125, 82), width=18)
        draw.line((lx-35, hut_y+520, lx+45, hut_y+590), fill=(156, 125, 82), width=18)
        draw.line((lx-35, hut_y+520, lx-5, hut_y+610), fill=(156, 125, 82), width=16)
    mode = idx % 6
    if mode in (1, 4):
        # mortar-riding silhouette
        bx = 820; by = 980 + rng.randint(-40, 40)
        draw.ellipse((bx-70, by-220, bx+70, by-80), fill=(15, 14, 16))
        draw.polygon([(bx-75, by-90), (bx-125, by+125), (bx+125, by+125), (bx+75, by-90)], fill=(22, 19, 20))
        draw.arc((bx-155, by+20, bx+155, by+220), 0, 180, fill=(116, 91, 63), width=24)
        draw.line((bx+90, by-40, bx+280, by-310), fill=(113, 87, 57), width=18)
        label(draw, "ΜΠΑΜΠΑ ΓΙΑΓΚΑ • ΣΛΑΒΙΚΗ ΛΑΪΚΗ ΠΑΡΑΔΟΣΗ")
    elif mode == 2:
        label(draw, "ΤΟ ΣΠΙΤΙ ΜΕ ΤΑ ΠΟΔΙΑ ΚΟΤΑΣ • ΜΟΤΙΒΟ ΤΩΝ ΠΑΡΑΜΥΘΙΩΝ")
    elif mode == 3:
        # crossroads / choice motif
        draw.line((120, 1900, 600, 1450), fill=(128, 105, 78), width=70)
        draw.line((1080, 1900, 600, 1450), fill=(128, 105, 78), width=70)
        label(draw, "ΑΠΕΙΛΗ Ή ΒΟΗΘΕΙΑ; • Ο ΡΟΛΟΣ ΑΛΛΑΖΕΙ ΑΝΑ ΙΣΤΟΡΙΑ")
    elif mode == 5:
        label(draw, "ΛΑΟΓΡΑΦΙΑ • ΟΧΙ ΑΠΟΔΕΙΞΗ ΥΠΕΡΦΥΣΙΚΟΥ")
    else:
        label(draw, "ΜΠΑΜΠΑ ΓΙΑΓΚΑ • Η ΚΑΛΥΒΑ ΣΤΟ ΔΑΣΟΣ")


def make_scene_factory(fallback):
    def make_scene(path: Path, job: dict, idx: int, total: int):
        theme = job.get("visual_theme", "")
        if theme not in {"volcanic_lightning", "baba_yaga"}:
            return fallback(path, job, idx, total)
        seed = int(hashlib.sha256(f"{job['id']}:{idx}".encode()).hexdigest()[:12], 16)
        rng = random.Random(seed)
        img = Image.new("RGB", (BG_W, BG_H))
        d = ImageDraw.Draw(img)
        if theme == "volcanic_lightning":
            draw_volcanic_lightning(d, idx, total, rng)
        else:
            draw_baba_yaga(d, idx, total, rng)
        marker = job.get("visual_marker", "")
        if marker:
            f = ImageFont.truetype(FONT, 25)
            d.rounded_rectangle((45, BG_H-102, 1155, BG_H-38), radius=18, fill=(0,0,0))
            d.text((65, BG_H-87), marker, font=f, fill=(226,230,234))
        img.save(path, "JPEG", quality=92, subsampling=0)
    return make_scene
