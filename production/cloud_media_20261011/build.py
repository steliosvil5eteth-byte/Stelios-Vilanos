#!/usr/bin/env python3
import json, os, re, subprocess, time, hashlib
from pathlib import Path
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"production/cloud_media_20261011/manifest.json"
OUT=ROOT/"generated/2026-10-11"
SLIDES=OUT/"slides"
CONTACTS=OUT/"contacts"
for d in (OUT,SLIDES,CONTACTS): d.mkdir(parents=True,exist_ok=True)

cfg=json.loads(MANIFEST.read_text(encoding="utf-8"))
UA="SteliosSocialMediaQA/1.0 (GitHub Actions; educational social production)"
session=requests.Session(); session.headers.update({"User-Agent":UA})
used_pages=set()
source_log=[]
allowed_tokens=("public domain","cc0","cc by","cc-by","cc by-sa","cc-by-sa")

font_candidates=[
 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
font_path=next((p for p in font_candidates if Path(p).exists()),None)
if not font_path: raise RuntimeError("DejaVu font missing")
title_font=ImageFont.truetype(font_path,54)
body_font=ImageFont.truetype(font_path,61)
small_font=ImageFont.truetype(font_path,33)

def clean_html(s):
    return re.sub("<[^>]+>","",s or "").replace("&amp;","&").strip()

def commons_candidates(query, limit=30):
    api="https://commons.wikimedia.org/w/api.php"
    params={
      "action":"query","format":"json","generator":"search",
      "gsrsearch":f'{query} filetype:bitmap',"gsrnamespace":6,"gsrlimit":limit,
      "prop":"imageinfo","iiprop":"url|mime|size|extmetadata","iiurlwidth":1600
    }
    r=session.get(api,params=params,timeout=40); r.raise_for_status()
    pages=(r.json().get("query") or {}).get("pages") or {}
    out=[]
    for pid,p in pages.items():
        ii=(p.get("imageinfo") or [{}])[0]
        mime=(ii.get("mime") or "").lower()
        if mime not in ("image/jpeg","image/png","image/webp"): continue
        if int(ii.get("width") or 0)<700 or int(ii.get("height") or 0)<500: continue
        em=ii.get("extmetadata") or {}
        lic=clean_html((em.get("LicenseShortName") or {}).get("value"))
        usage=clean_html((em.get("UsageTerms") or {}).get("value"))
        lic_l=(lic+" "+usage).lower()
        if not any(t in lic_l for t in allowed_tokens): continue
        out.append({
          "pageid":str(pid),"title":p.get("title",""),"url":ii.get("thumburl") or ii.get("url"),
          "width":ii.get("width"),"height":ii.get("height"),
          "license":lic or usage,
          "artist":clean_html((em.get("Artist") or {}).get("value")),
          "credit":clean_html((em.get("Credit") or {}).get("value")),
          "description":clean_html((em.get("ImageDescription") or {}).get("value"))
        })
    return out

def choose_image(query):
    variants=[query+" photograph", query, query.replace("old ","")+" photograph", " ".join(query.split()[:2])+" photograph"]
    last=[]
    for q in variants:
        try:
            cand=commons_candidates(q)
            last=cand
            for c in cand:
                if c["pageid"] not in used_pages and c.get("url"):
                    used_pages.add(c["pageid"]); return c
        except Exception as e:
            print("search error",q,e,flush=True)
        time.sleep(.8)
    for c in last:
        if c.get("url"): return c
    raise RuntimeError(f"No freely licensed image found for {query}")

def download_img(meta):
    url=meta["url"].split("?")[0]
    last=None
    for attempt in range(6):
        try:
            r=session.get(url,timeout=60)
            if r.status_code==429:
                time.sleep(3*(attempt+1)); last=RuntimeError("429"); continue
            r.raise_for_status()
            return Image.open(BytesIO(r.content)).convert("RGB")
        except Exception as e:
            last=e
            time.sleep(2*(attempt+1))
    raise last

def cover(im,size=(1080,1920)):
    tw,th=size; w,h=im.size
    scale=max(tw/w,th/h); nw,nh=int(w*scale),int(h*scale)
    im=im.resize((nw,nh),Image.LANCZOS)
    l=(nw-tw)//2; t=(nh-th)//2
    return im.crop((l,t,l+tw,t+th))

def wrap(draw,text,font,maxw):
    words=text.split(); lines=[]; cur=""
    for w in words:
        test=(cur+" "+w).strip()
        box=draw.textbbox((0,0),test,font=font,stroke_width=0)
        if box[2]-box[0] <= maxw: cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

def render_slide(story,idx,photo,meta):
    im=cover(photo)
    # Maintain photographic detail, add subtle dark overlay for readability.
    im=ImageEnhance.Contrast(im).enhance(1.05)
    overlay=Image.new("RGBA",im.size,(0,0,0,0))
    od=ImageDraw.Draw(overlay)
    od.rectangle((0,0,1080,1920),fill=(0,0,0,72))
    od.rounded_rectangle((55,110,1025,1810),radius=34,fill=(0,0,0,92))
    im=Image.alpha_composite(im.convert("RGBA"),overlay).convert("RGB")
    d=ImageDraw.Draw(im)
    header=f'{story["id"]} · {story["title"]}'
    y=205
    for line in wrap(d,header,title_font,875):
        d.text((95,y),line,font=title_font,fill="white",stroke_width=3,stroke_fill="black"); y+=68
    y=max(650,y+100)
    for line in wrap(d,story["cards"][idx-1],body_font,860):
        d.text((105,y),line,font=body_font,fill="white",stroke_width=4,stroke_fill="black"); y+=82
    d.text((95,1730),f"{idx}/5",font=small_font,fill="white",stroke_width=2,stroke_fill="black")
    if idx==5:
        cy=1560
        for line in wrap(d,cfg["cta"],small_font,860):
            d.text((105,cy),line,font=small_font,fill="white",stroke_width=2,stroke_fill="black"); cy+=48
    out=SLIDES/f'story_{story["id"]}_{idx:02d}.jpg'
    im.save(out,quality=91,optimize=True)
    return out

def make_video(story,slide_paths):
    concat=OUT/f'concat_{story["id"]}.txt'
    with concat.open("w",encoding="utf-8") as f:
        for p in slide_paths:
            f.write(f"file '{p.resolve()}'\nduration 3\n")
        f.write(f"file '{slide_paths[-1].resolve()}'\n")
    out=OUT/f'story_{story["id"]}.mp4'
    subprocess.run([
      "ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",str(concat),
      "-vf","fps=30,format=yuv420p","-c:v","libx264","-preset","medium","-crf","22",
      "-movflags","+faststart","-an",str(out)
    ],check=True)
    return out

def contact_sheet(story,slide_paths):
    thumbs=[]
    for p in slide_paths:
        im=Image.open(p).convert("RGB"); im.thumbnail((216,384),Image.LANCZOS)
        canvas=Image.new("RGB",(216,384),"black")
        canvas.paste(im,((216-im.width)//2,(384-im.height)//2)); thumbs.append(canvas)
    sheet=Image.new("RGB",(1080,384),"black")
    for i,im in enumerate(thumbs): sheet.paste(im,(i*216,0))
    p=CONTACTS/f'story_{story["id"]}.jpg'; sheet.save(p,quality=86,optimize=True); return p

results=[]
for story in cfg["stories"]:
    print("STORY",story["id"],story["title"],flush=True)
    slide_paths=[]; sources=[]
    for idx,q in enumerate(story["queries"],1):
        meta=choose_image(q)
        photo=download_img(meta)
        p=render_slide(story,idx,photo,meta)
        slide_paths.append(p)
        sources.append({"slide":idx,"query":q,**meta})
        time.sleep(1.1)
    video=make_video(story,slide_paths)
    contact=contact_sheet(story,slide_paths)
    sha=hashlib.sha256(video.read_bytes()).hexdigest()
    results.append({
      "id":story["id"],"title":story["title"],"video":str(video.relative_to(ROOT)),
      "contact":str(contact.relative_to(ROOT)),"sha256":sha,"bytes":video.stat().st_size,
      "sources":sources,"technical_qa":"PASS","visual_qa":"PENDING_MANUAL_REVIEW"
    })
    source_log.extend([{"story":story["id"],**s} for s in sources])

(OUT/"delivery_manifest.json").write_text(json.dumps({
 "date":cfg["date"],"brand_id":cfg["brand_id"],"timezone":cfg["timezone"],
 "stories":results,"status":"PENDING_MANUAL_VISUAL_REVIEW"
},ensure_ascii=False,indent=2),encoding="utf-8")
(OUT/"sources.json").write_text(json.dumps(source_log,ensure_ascii=False,indent=2),encoding="utf-8")

# Overview: 15 contact rows, scaled down to 1350x3240 for inspection.
rows=[]
for story in cfg["stories"]:
    im=Image.open(CONTACTS/f'story_{story["id"]}.jpg').convert("RGB").resize((675,240),Image.LANCZOS)
    label=Image.new("RGB",(675,240),"black")
    d=ImageDraw.Draw(label); d.text((16,16),f'{story["id"]} {story["title"]}',font=ImageFont.truetype(font_path,30),fill="white")
    row=Image.new("RGB",(1350,240),"black"); row.paste(label,(0,0)); row.paste(im,(675,0)); rows.append(row)
overview=Image.new("RGB",(1350,240*len(rows)),"black")
for i,r in enumerate(rows): overview.paste(r,(0,240*i))
overview.save(OUT/"qa_overview.jpg",quality=82,optimize=True)
print("DONE",len(results),flush=True)
