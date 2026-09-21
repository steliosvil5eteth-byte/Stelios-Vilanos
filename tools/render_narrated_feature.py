#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from azure_speech_tts import synthesize, DEFAULT_VOICE

W, H = 1080, 1920
BG_W, BG_H = 1200, 2134
SR = 24000
PAUSE_SECONDS = 0.20
MIN_SECONDS = 90.0
PREFERRED_MIN = 95.0
PREFERRED_MAX = 115.0
MAX_SECONDS = 120.0
MAX_DEAD_AIR = 1.20
MAX_TRAILING = 0.50

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]
BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]

def pick_font(candidates: list[str]) -> str:
    for p in candidates:
        if Path(p).exists():
            return p
    raise RuntimeError("No Greek-capable font found")

FONT = pick_font(FONT_CANDIDATES)
BOLD = pick_font(BOLD_CANDIDATES)

def run(cmd: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=True, text=True, capture_output=capture)

def ffprobe_duration(path: Path) -> float:
    cp = run([
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",str(path)
    ], capture=True)
    return float(cp.stdout.strip())

def ffprobe_streams(path: Path) -> dict[str, Any]:
    cp = run([
        "ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)
    ], capture=True)
    return json.loads(cp.stdout)

def trim_wav(src: Path, dst: Path) -> None:
    run([
        "ffmpeg","-y","-loglevel","error","-i",str(src),
        "-af",
        "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-48dB:"
        "stop_periods=1:stop_duration=0.03:stop_threshold=-48dB",
        "-ar",str(SR),"-ac","1","-c:a","pcm_s16le",str(dst)
    ])

def wav_frames(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != SR:
            raise RuntimeError(f"Unexpected WAV format for {path}")
        n = wf.getnframes()
        return wf.readframes(n), n

def sec_to_srt(t: float) -> str:
    if t < 0:
        t = 0
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def wrap_caption(text: str, width: int = 34) -> str:
    words = text.split()
    lines, cur = [], ""
    for word in words:
        candidate = (cur + " " + word).strip()
        if len(candidate) <= width:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    if len(lines) > 3:
        lines = [text]
    return "\n".join(lines)

def gradient(draw: ImageDraw.ImageDraw, top: tuple[int,int,int], bottom: tuple[int,int,int]) -> None:
    for y in range(BG_H):
        t = y / max(1, BG_H - 1)
        c = tuple(int(top[i]*(1-t) + bottom[i]*t) for i in range(3))
        draw.line((0,y,BG_W,y), fill=c)

def draw_brine_scene(draw: ImageDraw.ImageDraw, idx: int, total: int, rng: random.Random) -> None:
    gradient(draw, (6, 30, 55), (1, 9, 24))
    edge = 250 + int(35*math.sin(idx*0.7))
    draw.rectangle((0,0,BG_W,edge), fill=(183,225,241))
    for x in range(-50, BG_W+100, 95):
        y = edge + rng.randint(-30,30)
        draw.polygon([(x,0),(x+80,0),(x+55,y),(x+12,y+35)], fill=(207,238,248))
    grow = 0.22 + 0.72*((idx+1)/total)
    tip = int(edge + (BG_H-edge-260)*grow)
    cx = BG_W//2 + int(80*math.sin(idx*0.45))
    widths = [65,52,44,36,26]
    ys = [edge, int(edge+(tip-edge)*.25), int(edge+(tip-edge)*.5), int(edge+(tip-edge)*.75), tip]
    pts_l = [(cx-widths[i], ys[i]) for i in range(5)]
    pts_r = [(cx+widths[i], ys[i]) for i in reversed(range(5))]
    draw.polygon(pts_l+pts_r, fill=(198,239,250), outline=(235,252,255))
    draw.line((cx, edge+8, cx, max(edge+10,tip-12)), fill=(38,108,152), width=18)
    for j in range(8):
        px = cx + rng.randint(-75,75)
        py = tip + 25 + j*36
        r = 7 + rng.randint(0,8)
        draw.ellipse((px-r,py-r,px+r,py+r), fill=(61,123,157))
    bed = BG_H-245
    draw.rectangle((0,bed,BG_W,BG_H), fill=(23,38,45))
    for j in range(13):
        x = rng.randint(20,BG_W-20)
        y = rng.randint(bed+15,BG_H-20)
        r = rng.randint(8,25)
        draw.ellipse((x-r,y-r,x+r,y+r), fill=(64,77,73))
    f = ImageFont.truetype(BOLD, 34)
    label = "ΠΑΓΟΣ ΘΑΛΑΣΣΑΣ" if idx % 3 == 0 else "ΨΥΧΡΗ ΑΛΜΗ"
    draw.rounded_rectangle((60,85,470,145), radius=20, fill=(0,0,0))
    draw.text((82,95), label, font=f, fill="white")

def draw_llorona_scene(draw: ImageDraw.ImageDraw, idx: int, total: int, rng: random.Random) -> None:
    gradient(draw, (18, 26, 58), (3, 8, 20))
    horizon = 820 + int(40*math.sin(idx*.45))
    mx = 900 - int(160*(idx/total))
    my = 290 + int(25*math.sin(idx*.3))
    draw.ellipse((mx-95,my-95,mx+95,my+95), fill=(232,232,208))
    draw.polygon([(0,horizon),(190,590),(360,horizon),(535,650),(725,horizon),(910,610),(BG_W,horizon),(BG_W,1100),(0,1100)], fill=(15,28,40))
    draw.polygon([(0,horizon),(BG_W,horizon),(BG_W,BG_H),(0,BG_H)], fill=(8,34,56))
    for j in range(12):
        y = horizon+80+j*75
        offset = int(75*math.sin(idx*.4+j))
        draw.line((80+offset,y,BG_W-80+offset//2,y), fill=(47,80,101), width=4)
    for j in range(5):
        y = 700+j*170+rng.randint(-30,30)
        draw.rounded_rectangle((rng.randint(-100,100),y,BG_W-rng.randint(-100,100),y+30), radius=15, fill=(82,95,111))
    for x in list(range(35,260,34))+list(range(940,1180,34)):
        h = rng.randint(170,350)
        draw.line((x,BG_H-100,x+rng.randint(-35,35),BG_H-100-h), fill=(56,69,57), width=10)
    sx = 520 + int(70*math.sin(idx*.33))
    sy = 1080 + int(30*math.sin(idx*.5))
    draw.ellipse((sx-35,sy-155,sx+35,sy-85), fill=(210,215,220))
    draw.polygon([(sx,sy-85),(sx-115,sy+220),(sx+115,sy+220)], fill=(200,205,213))
    veil = [(sx-20,sy-120),(sx-105,sy+40),(sx-145,sy+235),(sx+145,sy+235),(sx+90,sy+30)]
    draw.line(veil, fill=(225,228,231), width=10)
    f = ImageFont.truetype(BOLD, 32)
    draw.rounded_rectangle((60,85,545,145), radius=20, fill=(0,0,0))
    draw.text((82,95), "ΛΑΪΚΗ ΠΑΡΑΔΟΣΗ — ΜΕΞΙΚΟ", font=f, fill="white")

def make_scene(path: Path, job: dict[str, Any], idx: int, total: int) -> None:
    seed = int(hashlib.sha256(f"{job['id']}:{idx}".encode()).hexdigest()[:12],16)
    rng = random.Random(seed)
    img = Image.new("RGB",(BG_W,BG_H))
    d = ImageDraw.Draw(img)
    visual = job.get("visual_theme","brinicle")
    if visual == "brinicle":
        draw_brine_scene(d, idx, total, rng)
    elif visual == "la_llorona":
        draw_llorona_scene(d, idx, total, rng)
    else:
        gradient(d,(22,32,55),(5,10,20))
    f = ImageFont.truetype(FONT, 28)
    marker = job.get("visual_marker","")
    if marker:
        d.text((62,BG_H-75), marker, font=f, fill=(220,225,230))
    img.save(path, "JPEG", quality=91, subsampling=0)

def render_visual_clip(img: Path, out: Path, duration: float, idx: int) -> None:
    z_expr = "min(zoom+0.00055,1.075)"
    if idx % 2 == 0:
        x_expr = "iw/2-(iw/zoom/2)+18*sin(on/35)"
    else:
        x_expr = "iw/2-(iw/zoom/2)-18*sin(on/35)"
    y_expr = "ih/2-(ih/zoom/2)+12*cos(on/41)"
    frames = max(1, int(math.ceil(duration*30)))
    vf = (
        f"scale={BG_W}:{BG_H},"
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={frames}:s={W}x{H}:fps=30,format=yuv420p"
    )
    run([
        "ffmpeg","-y","-loglevel","error","-loop","1","-i",str(img),
        "-vf",vf,"-t",f"{duration:.4f}",
        "-an","-c:v","libx264","-preset","veryfast","-crf","25",
        "-pix_fmt","yuv420p",str(out)
    ])

def silence_metrics(audio: Path) -> tuple[float,float]:
    cp = subprocess.run([
        "ffmpeg","-hide_banner","-nostats","-i",str(audio),
        "-af","silencedetect=noise=-45dB:d=0.05","-f","null","-"
    ], text=True, capture_output=True)
    starts=[]
    ends=[]
    maxdur=0.0
    for line in cp.stderr.splitlines():
        if "silence_start:" in line:
            try: starts.append(float(line.split("silence_start:")[1].strip().split()[0]))
            except Exception: pass
        if "silence_end:" in line:
            try: ends.append(float(line.split("silence_end:")[1].strip().split()[0]))
            except Exception: pass
        if "silence_duration:" in line:
            try:
                dur=float(line.split("silence_duration:")[1].strip().split()[0])
                maxdur=max(maxdur,dur)
            except Exception: pass
    dur=ffprobe_duration(audio)
    trailing=0.0
    if starts and (not ends or starts[-1] > ends[-1]):
        trailing=max(0.0,dur-starts[-1])
    return maxdur,trailing

def render_job(job: dict[str, Any], root: Path) -> dict[str, Any]:
    if job.get("voice") != DEFAULT_VOICE:
        raise RuntimeError(f"{job['id']}: voice must be {DEFAULT_VOICE}")
    segments = [s.strip() for s in job.get("segments",[]) if s.strip()]
    if len(segments) < 16:
        raise RuntimeError(f"{job['id']}: too few substantive narration segments")
    work = root / ("work-" + job["id"])
    outdir = root / job["id"]
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(outdir, ignore_errors=True)
    work.mkdir(parents=True)
    outdir.mkdir(parents=True)

    audio_frames=[]
    segment_durations=[]
    for i, text in enumerate(segments,1):
        raw=work/f"seg-{i:02d}-raw.wav"
        clean=work/f"seg-{i:02d}.wav"
        synthesize(text, raw, DEFAULT_VOICE)
        trim_wav(raw, clean)
        data, frames=wav_frames(clean)
        dur=frames/SR
        if dur <= 0.25:
            raise RuntimeError(f"{job['id']} segment {i} has invalid short audio")
        audio_frames.append(data)
        segment_durations.append(dur)

    narration=work/"narration.wav"
    silence_frames=int(round(PAUSE_SECONDS*SR))
    silence=b"\x00\x00"*silence_frames
    with wave.open(str(narration),"wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        for i,data in enumerate(audio_frames):
            wf.writeframes(data)
            if i != len(audio_frames)-1:
                wf.writeframes(silence)

    total_audio=ffprobe_duration(narration)
    if not (MIN_SECONDS <= total_audio <= MAX_SECONDS):
        raise RuntimeError(
            f"{job['id']}: duration gate failed: {total_audio:.2f}s "
            f"(required {MIN_SECONDS:.0f}-{MAX_SECONDS:.0f}s)"
        )

    srt=work/"subtitles.srt"
    t=0.0
    with srt.open("w",encoding="utf-8") as f:
        for i,(text,dur) in enumerate(zip(segments,segment_durations),1):
            start=t
            end=t+dur
            f.write(f"{i}\n{sec_to_srt(start)} --> {sec_to_srt(end)}\n{wrap_caption(text)}\n\n")
            t=end
            if i != len(segments):
                t += PAUSE_SECONDS

    clips=[]
    for i,dur in enumerate(segment_durations,1):
        scene=work/f"scene-{i:02d}.jpg"
        clip=work/f"clip-{i:02d}.mp4"
        make_scene(scene,job,i-1,len(segments))
        clip_dur=dur + (PAUSE_SECONDS if i != len(segments) else 0.0)
        render_visual_clip(scene,clip,clip_dur,i)
        clips.append(clip)

    concat=work/"clips.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips),encoding="utf-8")
    visual=work/"visual.mp4"
    run([
        "ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",str(concat),
        "-an","-c:v","libx264","-preset","veryfast","-crf","24",
        "-pix_fmt","yuv420p","-r","30",str(visual)
    ])

    final=outdir/f"{job['id']}.mp4"
    escaped_srt=str(srt).replace("\\","\\\\").replace(":","\\:").replace("'","\\'")
    style=(
        "FontName=DejaVu Sans,FontSize=28,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BackColour=&H78000000,"
        "BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=170"
    )
    run([
        "ffmpeg","-y","-loglevel","error","-i",str(visual),"-i",str(narration),
        "-vf",f"subtitles='{escaped_srt}':force_style='{style}'",
        "-c:v","libx264","-preset","medium","-crf","22","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","128k","-ar","48000","-ac","1",
        "-shortest","-movflags","+faststart",str(final)
    ])

    meta=ffprobe_streams(final)
    streams=meta.get("streams",[])
    v=[s for s in streams if s.get("codec_type")=="video"]
    a=[s for s in streams if s.get("codec_type")=="audio"]
    if len(v)!=1 or len(a)!=1:
        raise RuntimeError(f"{job['id']}: expected exactly one video and one audio stream")
    if int(v[0].get("width",0))!=W or int(v[0].get("height",0))!=H:
        raise RuntimeError(f"{job['id']}: output is not 1080x1920")
    if a[0].get("codec_name")!="aac":
        raise RuntimeError(f"{job['id']}: audio is not AAC")
    duration=ffprobe_duration(final)
    if not (MIN_SECONDS <= duration <= MAX_SECONDS):
        raise RuntimeError(f"{job['id']}: final duration {duration:.2f}s outside gate")
    maxsil,trailing=silence_metrics(final)
    if maxsil > MAX_DEAD_AIR + 0.03:
        raise RuntimeError(f"{job['id']}: dead-air gate failed: {maxsil:.3f}s")
    if trailing > MAX_TRAILING + 0.03:
        raise RuntimeError(f"{job['id']}: trailing-silence gate failed: {trailing:.3f}s")

    report={
        "id":job["id"],
        "voice":DEFAULT_VOICE,
        "azure_only":True,
        "paid_fallback_used":False,
        "duration_seconds":round(duration,3),
        "preferred_duration_met":PREFERRED_MIN <= duration <= PREFERRED_MAX,
        "max_detected_silence_seconds":round(maxsil,3),
        "trailing_silence_seconds":round(trailing,3),
        "resolution":f"{W}x{H}",
        "audio_streams":1,
        "background_music":False,
        "burned_subtitles":True,
        "avatar_presenter":False,
        "segments":len(segments),
        "source_note":job.get("source_note",""),
    }
    (outdir/"qa.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (outdir/"script.txt").write_text("\n".join(segments),encoding="utf-8")
    shutil.copy2(srt,outdir/"subtitles.srt")
    print(json.dumps(report,ensure_ascii=False))
    return report

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if not manifest.get("approved"):
        raise RuntimeError("Manifest is not approved")
    if manifest.get("paid_generation_allowed") is not False:
        raise RuntimeError("paid_generation_allowed must be false")
    jobs=manifest.get("jobs",[])
    if not jobs:
        raise RuntimeError("No jobs")
    root=Path(args.output)
    root.mkdir(parents=True,exist_ok=True)
    reports=[render_job(job,root) for job in jobs]
    (root/"qa-summary.json").write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__":
    main()
