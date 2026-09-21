#!/usr/bin/env python3
"""Deterministic, rights-safe visual themes for CURRENT narrated features.
All artwork is generated locally with PIL. No external images, no paid APIs.
The module exposes make_scene_factory(fallback) so unsupported themes keep the
existing renderer behavior.
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


def gradient(draw: ImageDraw.ImageDraw, top, bottom):
    for y in range(BG_H):
        t = y / max(1, BG_H - 1)
        c = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        draw.line((0, y, BG_W, y), fill=c)


def label(draw: ImageDraw.ImageDraw, text: str, *, y: int = 84):
    f = ImageFont.truetype(BOLD, 31)
    box = draw.textbbox((0, 0), text, font=f)
    w = min(BG_W - 120, box[2] - box[0] + 48)
    draw.rounded_rectangle((60, y, 60 + w, y + 62), radius=18, fill=(0, 0, 0))
    draw.text((82, y + 11), text, font=f, fill="white")


def draw_sailing_stones(draw: ImageDraw.ImageDraw, idx: int, total: int, rng: random.Random):
    mode = idx % 6
    gradient(draw, (35, 74, 106), (226, 183, 118))
    # distant mountains
    horizon = 650 + int(25 * math.sin(idx * .7))
    draw.polygon([(0,horizon),(180,470),(340,horizon),(520,500),(690,horizon),(880,455),(1200,horizon),(1200,850),(0,850)], fill=(92,83,80))
    # playa
    draw.polygon([(0,horizon),(1200,horizon),(1200,2134),(0,2134)], fill=(194,171,132))
    for k in range(18):
        y = horizon + 80 + k * 70
        draw.line((0,y,1200,y+rng.randint(-10,10)), fill=(174,150,115), width=2)
    # rare shallow water / ice states
    if mode in (2,3):
        draw.rectangle((0, horizon+80, 1200, 1350), fill=(136,174,185))
        for k in range(9):
            x = rng.randint(-80, 1050); y = rng.randint(horizon+100, 1280)
            w = rng.randint(120,300); h = rng.randint(35,85)
            draw.polygon([(x,y),(x+w,y+rng.randint(-15,15)),(x+w-35,y+h),(x+25,y+h+rng.randint(-12,12))], fill=(198,220,222))
    # principal rock and trail
    rx = 520 + int(150 * math.sin(idx * .55))
    ry = 1450 + int(90 * math.cos(idx * .38))
    trail_len = 430 + (idx * 37) % 260
    draw.line((rx, ry, max(90, rx-trail_len), min(2020, ry+350)), fill=(116,95,73), width=30)
    draw.ellipse((rx-72,ry-48,rx+72,ry+55), fill=(72,67,64), outline=(42,40,39), width=5)
    # secondary tracks for parallel-motion idea
    if mode in (0,4,5):
        for off in (-220, 210):
            sx = min(1120,max(80,rx+off)); sy=ry+rng.randint(-130,130)
            draw.line((sx,sy,max(70,sx-300),min(2070,sy+260)), fill=(128,103,78), width=18)
            draw.ellipse((sx-44,sy-30,sx+44,sy+32), fill=(84,75,67))
    if mode == 1:
        # instrumented research scene
        draw.rounded_rectangle((790,990,1090,1250), radius=25, fill=(45,58,62), outline=(230,230,220), width=4)
        draw.line((940,990,940,825), fill=(235,235,225), width=7)
        draw.ellipse((925,810,955,840), fill=(210,50,40))
        label(draw,"ΠΑΡΑΚΟΛΟΥΘΗΣΗ GPS • ΕΡΕΥΝΑ")
    elif mode == 3:
        label(draw,"ΛΕΠΤΟΣ ΠΑΓΟΣ + ΝΕΡΟ + ΕΛΑΦΡΥΣ ΑΝΕΜΟΣ")
    elif mode == 4:
        # wind arrows
        for y in (1040,1150,1260):
            draw.line((120,y,480,y-30), fill=(235,245,245), width=12)
            draw.polygon([(480,y-30),(435,y-62),(445,y-15)], fill=(235,245,245))
        label(draw,"RACETRACK PLAYA • DEATH VALLEY")
    else:
        label(draw,"ΚΙΝΟΥΜΕΝΕΣ ΠΕΤΡΕΣ • ΠΡΑΓΜΑΤΙΚΟ ΦΑΙΝΟΜΕΝΟ")


def draw_mothman(draw: ImageDraw.ImageDraw, idx: int, total: int, rng: random.Random):
    mode = idx % 6
    gradient(draw, (18, 25, 50), (2, 6, 16))
    # moon/sky
    mx, my = 930, 300
    draw.ellipse((mx-90,my-90,mx+90,my+90), fill=(222,222,195))
    # river
    draw.polygon([(0,1260),(1200,1180),(1200,2134),(0,2134)], fill=(12,34,52))
    for k in range(10):
        y=1370+k*70
        draw.line((80,y,1120,y+rng.randint(-12,12)), fill=(38,65,82), width=4)
    # bridge silhouette / towers, varied by mode
    if mode in (0,2,4,5):
        deck=1120
        draw.rectangle((0,deck,1200,deck+38), fill=(37,41,49))
        for tx in (270,930):
            draw.rectangle((tx-28,690,tx+28,deck), fill=(45,48,55))
        draw.line((270,700,930,700), fill=(68,71,78), width=10)
        for x in range(310,910,90):
            draw.line((270,710,x,deck),(68,71,78),6)
            draw.line((930,710,x,deck),(68,71,78),6)
    # folklore figure, clearly stylized
    cx = 570 + int(90*math.sin(idx*.45)); cy = 880 + int(70*math.cos(idx*.36))
    if mode in (0,1,3,5):
        draw.ellipse((cx-45,cy-150,cx+45,cy-60), fill=(7,9,14))
        draw.ellipse((cx-29,cy-118,cx-9,cy-98), fill=(205,30,30))
        draw.ellipse((cx+9,cy-118,cx+29,cy-98), fill=(205,30,30))
        draw.polygon([(cx,cy-60),(cx-260,cy+260),(cx-70,cy+80),(cx,cy+330),(cx+70,cy+80),(cx+260,cy+260)], fill=(8,10,15))
    if mode == 1:
        # road/headlights eyewitness framing
        draw.polygon([(360,2134),(840,2134),(670,1320),(530,1320)], fill=(38,38,42))
        draw.ellipse((470,1840,540,1890), fill=(244,227,164)); draw.ellipse((660,1840,730,1890), fill=(244,227,164))
        label(draw,"POINT PLEASANT • 1966 • ΜΑΡΤΥΡΙΕΣ")
    elif mode == 2:
        # archival/newspaper-inspired abstract panel, no copied text
        draw.rounded_rectangle((120,350,1080,1040), radius=18, fill=(226,219,194), outline=(85,78,66), width=5)
        f=ImageFont.truetype(BOLD,45)
        draw.text((180,420),"ΑΝΑΦΟΡΕΣ ΓΙΑ\nΜΙΑ ΦΤΕΡΩΤΗ ΜΟΡΦΗ",font=f,fill=(35,32,28),spacing=18)
        for y in range(620,940,65): draw.rectangle((180,y,980,y+13),fill=(105,99,88))
        label(draw,"ΤΟΠΙΚΟΣ ΤΥΠΟΣ • ΛΑΪΚΗ ΙΣΤΟΡΙΑ")
    elif mode == 4:
        label(draw,"SILVER BRIDGE • Η ΚΑΤΑΡΡΕΥΣΗ ΕΧΕΙ ΜΗΧΑΝΙΚΗ ΑΙΤΙΑ")
    else:
        label(draw,"MOTHMAN • ΑΜΕΡΙΚΑΝΙΚΟΣ ΣΥΓΧΡΟΝΟΣ ΘΡΥΛΟΣ")


def make_scene_factory(fallback):
    def make_scene(path: Path, job: dict, idx: int, total: int):
        theme = job.get("visual_theme", "")
        if theme not in {"sailing_stones", "mothman"}:
            return fallback(path, job, idx, total)
        seed = int(hashlib.sha256(f"{job['id']}:{idx}".encode()).hexdigest()[:12], 16)
        rng = random.Random(seed)
        img = Image.new("RGB", (BG_W, BG_H))
        d = ImageDraw.Draw(img)
        if theme == "sailing_stones":
            draw_sailing_stones(d, idx, total, rng)
        else:
            draw_mothman(d, idx, total, rng)
        marker = job.get("visual_marker", "")
        if marker:
            f = ImageFont.truetype(FONT, 27)
            d.rounded_rectangle((45,BG_H-100,1155,BG_H-38), radius=18, fill=(0,0,0))
            d.text((65,BG_H-86), marker, font=f, fill=(226,230,234))
        img.save(path, "JPEG", quality=92, subsampling=0)
    return make_scene
