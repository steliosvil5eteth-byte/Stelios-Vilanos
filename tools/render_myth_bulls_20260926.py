#!/usr/bin/env python3
from __future__ import annotations
import json, math, os, re, subprocess, time, wave
from pathlib import Path
import requests
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageEnhance, ImageFilter

OUT=Path(os.environ.get("OUTPUT_DIR","/tmp/myth-bulls"))
OUT.mkdir(parents=True,exist_ok=True)
UA="SteliosMythCards/1.0"
QUERIES=[
    "bull cattle portrait photograph",
    "bull running photograph",
    "bull pasture photograph",
    "bull arena photograph"
]
ALLOWED=("cc by","cc0","public domain")

def clean(s):
    return re.sub(r"<[^>]+>","",s or "").strip()

def get_photo(q, idx):
    sess=requests.Session(); sess.headers.update({"User-Agent":UA})
    params={"action":"query","format":"json","generator":"search","gsrsearch":q,"gsrnamespace":6,"gsrlimit":30,
            "prop":"imageinfo","iiprop":"url|size|extmetadata","iiurlwidth":1800}
    data=sess.get("https://commons.wikimedia.org/w/api.php",params=params,timeout=60).json()
    pages=list((data.get("query") or {}).get("pages",{}).values())
    for p in pages:
        title=p.get("title","")
        if not re.search(r"\.(jpe?g|png)$",title,re.I): continue
        if any(w in title.lower() for w in ["drawing","painting","illustration","logo","diagram","statue"]): continue
        infos=p.get("imageinfo") or []
        if not infos: continue
        info=infos[0]; meta=info.get("extmetadata") or {}
        lic=(clean((meta.get("LicenseShortName") or {}).get("value",""))+" "+clean((meta.get("UsageTerms") or {}).get("value",""))).lower()
        if not any(x in lic for x in ALLOWED): continue
        if min(int(info.get("width") or 0),int(info.get("height") or 0))<700: continue
        url=info.get("thumburl") or info.get("url")
        if not url: continue
        dst=OUT/f"src_{idx:02d}.jpg"
        r=sess.get(url,timeout=90); r.raise_for_status(); dst.write_bytes(r.content)
        with Image.open(dst) as im:
            im.convert("RGB").save(dst,quality=95)
        return {
            "file":title,
            "author":clean((meta.get("Artist") or {}).get("value","")),
            "license":clean((meta.get("LicenseShortName") or {}).get("value","")) or clean((meta.get("UsageTerms") or {}).get("value","")),
            "source_page":"https://commons.wikimedia.org/wiki/"+requests.utils.quote(title.replace(" ","_"),safe=":()_,.-")
        }
    raise RuntimeError("No suitable image for "+q)

sources=[get_photo(q,i+1) for i,q in enumerate(QUERIES)]
(OUT/"sources.json").write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding="utf-8")

cards=[
 ("ΜΥΘΟΣ Ή ΑΛΗΘΕΙΑ;","Οι ταύροι θυμώνουν πραγματικά με το κόκκινο;"),
 ("ΤΙ ΒΛΕΠΕΙ Ο ΤΑΥΡΟΣ;","Τα βοοειδή έχουν διαφορετική αντίληψη χρώματος από εμάς και δεν ξεχωρίζουν το κόκκινο όπως ο άνθρωπος."),
 ("ΤΙ ΠΡΟΚΑΛΕΙ ΤΗΝ ΑΝΤΙΔΡΑΣΗ;","Η κίνηση του υφάσματος και η πρόκληση τραβούν την προσοχή πολύ περισσότερο από το ίδιο το χρώμα."),
 ("ΑΠΑΝΤΗΣΗ: ΜΥΘΟΣ","Το κόκκινο δεν είναι αυτό που «εξαγριώνει» τον ταύρο. Η κίνηση είναι το βασικό ερέθισμα.")
]

FONT_B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
fb=ImageFont.truetype(FONT_B,48)
fr=ImageFont.truetype(FONT_R,38)
fn=ImageFont.truetype(FONT_B,30)
fs=ImageFont.truetype(FONT_R,23)

def wrap(draw,text,font,maxw):
    out=[]; cur=""
    for w in text.split():
        cand=(cur+" "+w).strip()
        if draw.textbbox((0,0),cand,font=font)[2] <= maxw:
            cur=cand
        else:
            if cur: out.append(cur)
            cur=w
    if cur: out.append(cur)
    return out

card_files=[]
for i,(title,body) in enumerate(cards,1):
    im=Image.open(OUT/f"src_{i:02d}.jpg").convert("RGB")
    hero=ImageOps.fit(im,(1080,620),Image.Resampling.LANCZOS,centering=(0.5,0.5))
    base=Image.new("RGB",(1080,1080),(11,12,14)); base.paste(hero,(0,0))
    d=ImageDraw.Draw(base)
    d.rectangle((0,585,1080,1080),fill=(11,12,14))
    # red/blue visual swatches for color myth
    d.rectangle((0,585,540,595),fill=(190,35,45))
    d.rectangle((540,585,1080,595),fill=(45,90,180))
    d.rounded_rectangle((900,22,1038,80),radius=20,fill=(0,0,0))
    d.text((925,32),f"{i}/4",font=fn,fill="white")
    y=640
    for line in wrap(d,title,fb,960):
        d.text((56,y),line,font=fb,fill="white"); y+=58
    y+=12
    for line in wrap(d,body,fr,960):
        d.text((56,y),line,font=fr,fill=(238,238,238)); y+=49
    d.text((56,1018),"Ιστορίες που μας αγγίζουν",font=fs,fill=(210,210,210))
    p=OUT/f"card_{i:02d}.jpg"; base.save(p,quality=95,subsampling=0); card_files.append(p)

# YouTube vertical slideshow
frames=[]
for i,p in enumerate(card_files,1):
    sq=Image.open(p).convert("RGB")
    bg=sq.resize((1080,1920)).filter(ImageFilter.GaussianBlur(26))
    bg=ImageEnhance.Brightness(bg).enhance(0.45)
    bg.paste(sq.resize((1080,1080)),(0,420))
    fp=OUT/f"frame_{i:02d}.jpg"; bg.save(fp,quality=92); frames.append(fp)
concat=OUT/"concat.txt"
with concat.open("w") as f:
    for fp in frames:
        f.write("file '"+str(fp).replace("'","'\\''")+"'\n")
        f.write("duration 5.2\n")
    f.write("file '"+str(frames[-1]).replace("'","'\\''")+"'\n")

sr=44100; dur=22.0
samples=[]
for n in range(int(sr*dur)):
    t=n/sr
    val=(0.016*math.sin(2*math.pi*110*t)+0.009*math.sin(2*math.pi*165*t)+0.006*math.sin(2*math.pi*220*t))
    env=min(1,t/1.0,(dur-t)/1.0)
    samples.append(int(max(-1,min(1,val*max(0,env)))*32767))
wav=OUT/"instrumental.wav"
with wave.open(str(wav),"w") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
    import array
    wf.writeframes(array.array("h",samples).tobytes())

video=OUT/"myth_bulls_youtube.mp4"
subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-i",str(wav),"-shortest",
                "-vf","fps=30,format=yuv420p","-c:v","libx264","-crf","20","-preset","medium",
                "-c:a","aac","-b:a","128k","-movflags","+faststart",str(video)],check=True)
(OUT/"qa.json").write_text(json.dumps({"publish_ready":True,"cards":4,"youtube_video":str(video),"sources":sources},ensure_ascii=False,indent=2),encoding="utf-8")
print("READY")
