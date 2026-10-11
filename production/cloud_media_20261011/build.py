#!/usr/bin/env python3
import json, subprocess, hashlib, time
from pathlib import Path
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT=Path(__file__).resolve().parents[2]
CFG=json.loads((ROOT/"production/cloud_media_20261011/manifest.json").read_text(encoding="utf-8"))
OUT=ROOT/"generated/2026-10-11"
SRC=OUT/"source"
SLIDES=OUT/"slides"
CONTACTS=OUT/"contacts"
for d in (OUT,SRC,SLIDES,CONTACTS): d.mkdir(parents=True,exist_ok=True)

UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36"
session=requests.Session()
session.headers.update({"User-Agent":UA,"Referer":"https://www.pexels.com/"})

font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
title_font=ImageFont.truetype(font_path,48)
body_font=ImageFont.truetype(font_path,57)
small_font=ImageFont.truetype(font_path,31)

def wrap(draw,text,font,maxw):
    words=text.split(); lines=[]; cur=""
    for w in words:
        t=(cur+" "+w).strip()
        if draw.textbbox((0,0),t,font=font)[2] <= maxw:
            cur=t
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

def download_pexels(video_id, out):
    url=f"https://www.pexels.com/download/video/{video_id}/"
    last=None
    for attempt in range(5):
        try:
            with session.get(url,stream=True,timeout=90,allow_redirects=True) as r:
                if r.status_code in (429,403):
                    last=RuntimeError(f"Pexels HTTP {r.status_code}")
                    time.sleep(4*(attempt+1)); continue
                r.raise_for_status()
                ctype=(r.headers.get("content-type") or "").lower()
                if "video" not in ctype and "octet-stream" not in ctype:
                    # Some CDN responses omit a precise video content type. Accept only sizable bodies.
                    pass
                with out.open("wb") as fp:
                    for chunk in r.iter_content(1024*1024):
                        if chunk: fp.write(chunk)
            if out.stat().st_size < 250_000:
                raise RuntimeError(f"Downloaded source too small: {out.stat().st_size}")
            return r.url
        except Exception as e:
            last=e
            if out.exists(): out.unlink()
            time.sleep(3*(attempt+1))
    raise last

def duration(path):
    s=subprocess.check_output([
      "ffprobe","-v","error","-show_entries","format=duration",
      "-of","default=nw=1:nk=1",str(path)
    ],text=True).strip()
    return max(1.0,float(s))

def extract_frame(src,t,out):
    subprocess.run([
      "ffmpeg","-y","-loglevel","error","-ss",f"{t:.3f}","-i",str(src),
      "-frames:v","1","-q:v","2",str(out)
    ],check=True)

def portrait_canvas(photo):
    photo=photo.convert("RGB")
    w,h=photo.size
    # background fill: cover + heavy blur
    scale=max(1080/w,1920/h)
    bg=photo.resize((int(w*scale),int(h*scale)),Image.LANCZOS)
    l=(bg.width-1080)//2; t=(bg.height-1920)//2
    bg=bg.crop((l,t,l+1080,t+1920)).filter(ImageFilter.GaussianBlur(26))
    bg=ImageEnhance.Brightness(bg).enhance(0.55)
    # foreground: contain, preserving visible action
    scale=min(990/w,1720/h)
    fg=photo.resize((max(1,int(w*scale)),max(1,int(h*scale))),Image.LANCZOS)
    x=(1080-fg.width)//2; y=(1920-fg.height)//2
    bg.paste(fg,(x,y))
    return bg

def render_slide(story,idx,frame):
    im=portrait_canvas(Image.open(frame))
    overlay=Image.new("RGBA",im.size,(0,0,0,0))
    od=ImageDraw.Draw(overlay)
    od.rectangle((0,0,1080,1920),fill=(0,0,0,40))
    od.rounded_rectangle((58,118,1022,1802),radius=28,fill=(0,0,0,88))
    im=Image.alpha_composite(im.convert("RGBA"),overlay).convert("RGB")
    d=ImageDraw.Draw(im)
    y=205
    header=f'{story["id"]} · {story["title"]}'
    for line in wrap(d,header,title_font,875):
        d.text((95,y),line,font=title_font,fill="white",stroke_width=3,stroke_fill="black")
        y+=62
    y=max(635,y+105)
    for line in wrap(d,story["cards"][idx-1],body_font,855):
        d.text((110,y),line,font=body_font,fill="white",stroke_width=4,stroke_fill="black")
        y+=78
    d.text((95,1718),f"{idx}/5",font=small_font,fill="white",stroke_width=2,stroke_fill="black")
    if idx==5:
        cy=1510
        for line in wrap(d,CFG["cta"],small_font,850):
            d.text((110,cy),line,font=small_font,fill="white",stroke_width=2,stroke_fill="black")
            cy+=44
    out=SLIDES/f'story_{story["id"]}_{idx:02d}.jpg'
    im.save(out,quality=92,optimize=True)
    return out

def make_video(story,slides):
    concat=OUT/f'concat_{story["id"]}.txt'
    with concat.open("w",encoding="utf-8") as fp:
        for p in slides:
            fp.write(f"file '{p.resolve()}'\nduration 3\n")
        fp.write(f"file '{slides[-1].resolve()}'\n")
    out=OUT/f'story_{story["id"]}.mp4'
    subprocess.run([
      "ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",str(concat),
      "-vf","fps=30,format=yuv420p","-c:v","libx264","-preset","medium","-crf","22",
      "-movflags","+faststart","-an",str(out)
    ],check=True)
    return out

def make_contact(story,slides):
    sheet=Image.new("RGB",(1080,384),"black")
    for i,p in enumerate(slides):
        im=Image.open(p).convert("RGB").resize((216,384),Image.LANCZOS)
        sheet.paste(im,(i*216,0))
    out=CONTACTS/f'story_{story["id"]}.jpg'
    sheet.save(out,quality=88,optimize=True)
    return out

results=[]
for story in CFG["stories"]:
    sid=story["id"]; print("STORY",sid,story["title"],flush=True)
    src=SRC/f"{sid}.mp4"
    final_url=download_pexels(story["pexels_video_id"],src)
    dur=duration(src)
    # Five distinct moments, avoiding exact first/last frame.
    times=[dur*x for x in (0.10,0.28,0.46,0.64,0.82)]
    slides=[]
    for idx,t in enumerate(times,1):
        frame=SRC/f"{sid}_{idx:02d}.jpg"
        extract_frame(src,t,frame)
        slides.append(render_slide(story,idx,frame))
    video=make_video(story,slides)
    contact=make_contact(story,slides)
    results.append({
      "id":sid,"title":story["title"],"video":str(video.relative_to(ROOT)),
      "contact":str(contact.relative_to(ROOT)),
      "sha256":hashlib.sha256(video.read_bytes()).hexdigest(),
      "bytes":video.stat().st_size,
      "source_page":story["source_page"],
      "source_license":story["source_license"],
      "source_video_id":story["pexels_video_id"],
      "resolved_download_url":final_url,
      "technical_qa":"PASS",
      "visual_qa":"PENDING_FINAL_REVIEW"
    })

# Build review overview from exact rendered slide files.
rows=[]
label_font=ImageFont.truetype(font_path,28)
for story in CFG["stories"]:
    contact=Image.open(CONTACTS/f'story_{story["id"]}.jpg').convert("RGB").resize((810,288),Image.LANCZOS)
    row=Image.new("RGB",(1350,288),"black")
    d=ImageDraw.Draw(row)
    yy=28
    for line in wrap(d,f'{story["id"]} · {story["title"]}',label_font,480):
        d.text((22,yy),line,font=label_font,fill="white"); yy+=40
    row.paste(contact,(540,0)); rows.append(row)
overview=Image.new("RGB",(1350,288*len(rows)),"black")
for i,row in enumerate(rows): overview.paste(row,(0,288*i))
overview.save(OUT/"qa_overview.jpg",quality=88,optimize=True)

(OUT/"delivery_manifest.json").write_text(json.dumps({
 "date":CFG["date"],"brand_id":CFG["brand_id"],"timezone":CFG["timezone"],
 "status":"PENDING_FINAL_VISUAL_REVIEW","stories":results
},ensure_ascii=False,indent=2),encoding="utf-8")
print("DONE",len(results),flush=True)
