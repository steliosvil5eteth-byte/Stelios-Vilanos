#!/usr/bin/env python3
"""Deterministic, rights-safe local visuals for next-day narrated features.
No external images, no paid APIs. Supports Morning Glory and Bloody Mary.
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


def draw_morning_glory(draw, idx, total, rng):
    mode = idx % 7
    gradient(draw, (55, 118, 170), (236, 181, 106))
    horizon = 1160 + int(40 * math.sin(idx * .4))
    draw.rectangle((0, horizon, BG_W, BG_H), fill=(87, 112, 69))
    # distant Gulf / coastal plain
    draw.rectangle((0, horizon - 100, BG_W, horizon), fill=(58, 128, 151))
    # long roll cloud with changing perspective
    cy = 650 + int(110 * math.sin(idx * .31))
    thickness = 150 + (idx % 4) * 20
    for x in range(-220, BG_W + 250, 90):
        jitter = rng.randint(-35, 35)
        r = thickness // 2 + rng.randint(-15, 25)
        draw.ellipse((x-r, cy-r+jitter, x+r+150, cy+r+jitter), fill=(226, 235, 239))
        draw.ellipse((x-r//2, cy+jitter, x+r+120, cy+r+70+jitter), fill=(173, 196, 205))
    if mode in (1, 5):
        # directional airflow arrows
        for y in (970, 1050, 1130):
            draw.line((150, y, 650, y-25), fill=(245, 247, 235), width=11)
            draw.polygon([(650,y-25),(610,y-58),(618,y+5)], fill=(245,247,235))
        label(draw, "ΑΤΜΟΣΦΑΙΡΙΚΟ ΚΥΜΑ • UNDULAR BORE")
    elif mode == 2:
        # stylized vertical circulation
        for x in (260, 600, 940):
            draw.arc((x-80, 720, x+80, 1080), 80, 280, fill=(245,247,235), width=9)
        label(draw, "ΥΓΡΟΣ ΑΕΡΑΣ ΑΝΕΒΑΙΝΕΙ • ΣΥΜΠΥΚΝΩΣΗ")
    elif mode == 3:
        # satellite-like strip abstraction
        draw.rounded_rectangle((140,300,1060,1180), radius=35, fill=(25,58,78), outline=(230,235,238), width=5)
        draw.line((190,740,1010,610), fill=(238,244,246), width=80)
        draw.line((190,780,1010,650), fill=(171,195,204), width=24)
        label(draw, "GULF OF CARPENTARIA • ΑΥΣΤΡΑΛΙΑ")
    elif mode == 4:
        # pressure/wind observation motif
        draw.rounded_rectangle((790,1250,1080,1540), radius=30, fill=(30,45,55), outline=(230,230,220), width=4)
        f = ImageFont.truetype(BOLD, 34)
        draw.text((835,1325), "ΑΝΕΜΟΣ\nΠΙΕΣΗ", font=f, fill="white", spacing=18)
        label(draw, "ΜΕΤΕΩΡΟΛΟΓΙΚΕΣ ΠΑΡΑΤΗΡΗΣΕΙΣ")
    elif mode == 6:
        label(draw, "ΤΟ ΣΥΝΝΕΦΟ ΕΙΝΑΙ Η ΟΡΑΤΗ ΥΠΟΓΡΑΦΗ ΤΟΥ ΚΥΜΑΤΟΣ")
    else:
        label(draw, "MORNING GLORY • ΠΡΑΓΜΑΤΙΚΟ ΜΕΤΕΩΡΟΛΟΓΙΚΟ ΦΑΙΝΟΜΕΝΟ")


def draw_bloody_mary(draw, idx, total, rng):
    mode = idx % 7
    gradient(draw, (20, 18, 29), (4, 5, 10))
    # dim room and mirror
    draw.rectangle((120, 260, 1080, 1660), fill=(44, 36, 43), outline=(128, 105, 92), width=22)
    draw.rectangle((175, 315, 1025, 1605), fill=(35, 45, 55))
    # reflected face, deliberately ambiguous and stylized
    cx = 600 + int(25 * math.sin(idx*.7)); cy = 840
    draw.ellipse((cx-190,cy-245,cx+190,cy+245), fill=(165,158,156))
    draw.ellipse((cx-105,cy-65,cx-35,cy+5), fill=(35,28,32))
    draw.ellipse((cx+35,cy-65,cx+105,cy+5), fill=(35,28,32))
    draw.arc((cx-85,cy+45,cx+85,cy+165), 15, 165, fill=(65,42,45), width=8)
    # perceptual distortions vary by frame
    if mode in (1,3,5):
        for k in range(6):
            off = 18 + k*13
            draw.arc((cx-190-off,cy-245-off,cx+190+off,cy+245+off), 210, 335,
                     fill=(95+rng.randint(0,30),70,85), width=5)
    if mode == 2:
        # candle / low-light condition
        for x in (280, 920):
            draw.rectangle((x-18,1540,x+18,1770), fill=(232,218,185))
            draw.ellipse((x-42,1480,x+42,1570), fill=(242,164,71))
        label(draw, "ΧΑΜΗΛΟΣ ΦΩΤΙΣΜΟΣ • ΚΟΙΤΑΓΜΑ ΣΤΟΝ ΚΑΘΡΕΦΤΗ")
    elif mode == 3:
        label(draw, "ΠΑΡΑΜΟΡΦΩΣΕΙΣ ΠΡΟΣΩΠΟΥ • ΟΠΤΙΚΗ ΨΕΥΔΑΙΣΘΗΣΗ")
    elif mode == 4:
        # folklore archive motif
        draw.rounded_rectangle((160,1720,1040,1990), radius=28, fill=(214,201,175))
        f = ImageFont.truetype(BOLD, 34)
        draw.text((215,1780), "ΛΑΟΓΡΑΦΙΑ • ΠΟΛΛΕΣ ΠΑΡΑΛΛΑΓΕΣ\nΟΧΙ ΕΠΑΛΗΘΕΥΜΕΝΟ ΥΠΕΡΦΥΣΙΚΟ ΓΕΓΟΝΟΣ", font=f, fill=(39,34,31), spacing=14)
        label(draw, "BLOODY MARY • ΑΓΓΛΟΦΩΝΟΣ ΑΣΤΙΚΟΣ ΘΡΥΛΟΣ")
    elif mode == 6:
        label(draw, "Η ΑΝΤΙΛΗΨΗ ΜΠΟΡΕΙ ΝΑ ΠΑΡΑΜΟΡΦΩΣΕΙ ΕΝΑ ΠΡΟΣΩΠΟ")
    else:
        label(draw, "BLOODY MARY • ΛΑΟΓΡΑΦΙΑ, ΟΧΙ ΑΠΟΔΕΙΞΗ ΦΑΝΤΑΣΜΑΤΟΣ")


def make_scene_factory(fallback):
    def make_scene(path: Path, job: dict, idx: int, total: int):
        theme = job.get("visual_theme", "")
        if theme not in {"morning_glory", "bloody_mary"}:
            return fallback(path, job, idx, total)
        seed = int(hashlib.sha256(f"{job['id']}:{idx}".encode()).hexdigest()[:12], 16)
        rng = random.Random(seed)
        img = Image.new("RGB", (BG_W, BG_H))
        d = ImageDraw.Draw(img)
        if theme == "morning_glory":
            draw_morning_glory(d, idx, total, rng)
        else:
            draw_bloody_mary(d, idx, total, rng)
        marker = job.get("visual_marker", "")
        if marker:
            f = ImageFont.truetype(FONT, 26)
            d.rounded_rectangle((45,BG_H-102,1155,BG_H-38), radius=18, fill=(0,0,0))
            d.text((65,BG_H-87), marker, font=f, fill=(226,230,234))
        img.save(path, "JPEG", quality=92, subsampling=0)
    return make_scene
