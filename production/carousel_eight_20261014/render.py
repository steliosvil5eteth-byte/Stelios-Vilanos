#!/usr/bin/env python3
"""Generate *draft* six-frame 1:1 cards and slow square slideshows. Never publish."""
import io, json, hashlib, subprocess, pathlib, textwrap, sys
from PIL import Image, ImageOps, ImageDraw, ImageFont
import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
REQUEST = ROOT / "production/carousel_eight_20261014/request.json"
OUT = ROOT / "media/carousel_eight_20261014"
OUT.mkdir(parents=True, exist_ok=True)
CONFIG = json.loads(REQUEST.read_text(encoding="utf-8"))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 StoryboardProduction/1.0"

def fetch_image(url):
    if not url.startswith("https://videocdn.pollo.ai/web-cdn/pollo/production/"):
        raise ValueError("Unauthorized media source URL")
    r = S.get(url, timeout=40)
    r.raise_for_status()
    if len(r.content) > 25000000:
        raise ValueError("Media source exceeds 25MB")
    im = Image.open(io.BytesIO(r.content))
    im.load()
    if im.width < 900 or im.height < 600:
        raise ValueError(f"Image source too small: {im.size}")
    return im.convert("RGB")

def wrap_words(text, font, maxwidth):
    words=text.split()
    probe=ImageDraw.Draw(Image.new("RGB",(10,10)))
    lines=[];cur=""
    for word in words:
        trial=(cur+" "+word).strip()
        if probe.textbbox((0,0),trial,font=font)[2] <= maxwidth:
            cur=trial
        else:
            if cur:lines.append(cur)
            cur=word
    if cur:lines.append(cur)
    return lines

def render_card(photo, text, label, n):
    photo=ImageOps.fit(photo,(1080,1080),method=Image.Resampling.LANCZOS)
    art=photo.convert("RGBA")
    shade=Image.new("RGBA",(1080,1080),(0,0,0,0))
    sp=ImageDraw.Draw(shade)
    for y in range(1080):
        a=int(18+205*max(0,min(1,(y-410)/570))**0.66)
        sp.line((0,y,1079,y),fill=(2,7,16,a),width=1)
    art=Image.alpha_composite(art,shade)
    dr=ImageDraw.Draw(art)
    dr.rounded_rectangle((48,47,1032,135),radius=25,fill=(6,15,29,172))
    sm=ImageFont.truetype(FONT_REG,30)
    dr.text((76,72),label.upper(),font=sm,fill="white")
    dr.text((939,72),f"{n}/6",font=sm,fill="#F7DEAA")
    is_last=n==6
    lead=text
    if is_last:
        lead=text.replace("Ακολουθήστε με για περισσότερα.","").strip()
    allowed_h=315 if not is_last else 215
    start=680 if not is_last else 715
    lines=[];font=None
    for size in range(66,35,-2):
        candidate=ImageFont.truetype(FONT,size)
        ll=wrap_words(lead,candidate,928)
        lh=int(size*1.23)
        if len(ll)*lh<=allowed_h and len(ll)<=6:
            font=candidate;lines=ll;break
    if font is None:
        raise ValueError("Text cannot fit reliably")
    lh=int(font.size*1.23)
    top=start+max(0,(allowed_h-len(lines)*lh)//2)
    for i,line in enumerate(lines):
        dr.text((76,top+i*lh),line,font=font,fill=(255,255,255,255),stroke_width=2,stroke_fill=(8,13,21,175))
    if is_last:
        dr.line((76,942,1003,942),width=2,fill="#F5D79C")
        cfont=ImageFont.truetype(FONT,44)
        cta="Ακολουθήστε με για περισσότερα."
        if dr.textbbox((0,0),cta,font=cfont)[2] > 928:
            raise ValueError("CTA line too long")
        dr.text((76,961),cta,font=cfont,fill="#FFDE97")
    return art.convert("RGB")

def split_sheet(sheet):
    w,h=sheet.size
    cw,ch=w/3,h/2
    if abs(cw-ch)/min(cw,ch)>0.18:
        raise ValueError(f"Contact sheet not 3x2 square cells: {sheet.size}")
    tiles=[]
    for n in range(6):
        col=n%3;row=n//3
        x0=round(col*cw+14);x1=round((col+1)*cw-14)
        y0=round(row*ch+14);y1=round((row+1)*ch-14)
        tiles.append(sheet.crop((x0,y0,x1,y1)))
    return tiles

def render_video(paths, destination):
    playlist=destination.parent/"slides.ffconcat"
    chunks=["ffconcat version 1.0"]
    for p in paths:
        chunks.append("file '"+str(p.resolve()).replace("'","'\\''")+"'")
        chunks.append("duration 11")
    chunks.append("file '"+str(paths[-1].resolve())+"'")
    playlist.write_text("\n".join(chunks)+"\n",encoding="utf-8")
    subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-safe","0","-f","concat","-i",str(playlist),"-vf","fps=2,scale=1080:1080:flags=lanczos,format=yuv420p","-t","66","-an","-c:v","libx264","-preset","fast","-crf","30","-pix_fmt","yuv420p","-movflags","+faststart",str(destination)],check=True,timeout=240)
    return destination

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

summary={"date":CONFIG["date"],"format":"square 1080x1080","review_status":"NEEDS_EXACT_VISUAL_AND_VIDEO_REVIEW","posts":[],"blockers":[]}
all_posts=[{"id":"leo_scorpio","title":"Λέων με ωροσκόπο Σκορπιό","previously_approved":True}]+CONFIG["posts"]
for post in all_posts:
    slug=post["id"]
    target=OUT/slug
    target.mkdir(parents=True,exist_ok=True)
    try:
        cards=[]
        if slug=="leo_scorpio":
            for i,u in enumerate(CONFIG["already_reviewed_leo"]["cards"],1):
                photo=fetch_image(u)
                p=target/f"card_{i:02d}.jpg"
                photo=ImageOps.fit(photo,(1080,1080),Image.Resampling.LANCZOS)
                photo.save(p,quality=93,optimize=True)
                cards.append(p)
        else:
            photos=split_sheet(fetch_image(CONFIG["sources"][slug]))
            for i,(photo,copy) in enumerate(zip(photos,post["copy"]),1):
                art=render_card(photo,copy,post["title"],i)
                p=target/f"card_{i:02d}.jpg"
                art.save(p,quality=93,optimize=True)
                cards.append(p)
        if len(cards)!=6:
            raise ValueError("Wrong card count")
        video=render_video(cards,target/"slideshow.mp4")
        contacts=Image.new("RGB",(1200,800),"#171b25")
        for i,p in enumerate(cards):
            contacts.paste(Image.open(p).resize((392,392)),((i%3)*400+4,(i//3)*400+4))
        contacts.save(target/"qa_contact.jpg",quality=90)
        summary["posts"].append({"slug":slug,"title":post["title"],"review_status":"NEEDS_EXACT_VISUAL_AND_VIDEO_REVIEW","cards":[{"path":str(p.relative_to(ROOT)),"sha256":digest(p)} for p in cards],"video":{"path":str(video.relative_to(ROOT)),"sha256":digest(video)},"caption":post.get("caption","")})
        print("RENDERED",slug,flush=True)
    except Exception as exc:
        summary["blockers"].append({"slug":slug,"error":type(exc).__name__+":"+str(exc)[:180]})
        print("BLOCKED",slug,str(exc)[:180],flush=True)
(OUT/"manifest.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print("SUMMARY",len(summary["posts"]),"created,",len(summary["blockers"]),"blocked",flush=True)
if len(summary["posts"])<1:sys.exit(1)
