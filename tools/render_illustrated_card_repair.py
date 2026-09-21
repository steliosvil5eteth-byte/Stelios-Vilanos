#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, random, subprocess, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
CTA = 'Αν σας άρεσε, ακολουθήστε για περισσότερα.'
ZODIAC_SIGNS = ['ΚΡΙΟΣ','ΤΑΥΡΟΣ','ΔΙΔΥΜΟΙ','ΚΑΡΚΙΝΟΣ','ΛΕΩΝ','ΠΑΡΘΕΝΟΣ']


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if p.returncode:
        raise RuntimeError(p.stderr[-3000:])
    return p.stdout


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def wrap(draw, text, fnt, maxw):
    lines=[]
    for para in text.split('\n'):
        cur=''
        for word in para.split():
            cand=(cur+' '+word).strip()
            if draw.textlength(cand,font=fnt) <= maxw:
                cur=cand
            else:
                if cur: lines.append(cur)
                cur=word
        if cur: lines.append(cur)
    return lines


def text_box(im, text, box, size, *, bold=False, center=False, min_size=24, fill=(255,255,255,255)):
    d=ImageDraw.Draw(im)
    x0,y0,x1,y1=box
    chosen=None
    for s in range(size,min_size-1,-1):
        f=font(s,bold)
        lines=wrap(d,text,f,x1-x0)
        lead=int(s*1.34)
        if len(lines)*lead <= y1-y0:
            chosen=(f,lines,lead); break
    if not chosen: raise ValueError('text does not fit')
    f,lines,lead=chosen
    y=y0 + ((y1-y0-len(lines)*lead)//2 if center else 0)
    for line in lines:
        tw=d.textlength(line,font=f)
        x=x0+(x1-x0-tw)/2 if center else x0
        d.text((x,y),line,font=f,fill=fill,stroke_width=1,stroke_fill=(0,0,0,170))
        y+=lead


def gradient(seed, top, bottom):
    im=Image.new('RGB',(W,H))
    px=im.load()
    for y in range(H):
        t=y/(H-1)
        r=int(top[0]*(1-t)+bottom[0]*t); g=int(top[1]*(1-t)+bottom[1]*t); b=int(top[2]*(1-t)+bottom[2]*t)
        for x in range(W): px[x,y]=(r,g,b)
    return im.convert('RGBA')


def zodiac_bg(idx):
    palettes=[((13,17,45),(72,30,78)),((18,34,45),(37,78,67)),((18,24,57),(54,67,110)),((12,34,57),(39,73,101)),((45,20,33),(104,57,31)),((18,35,38),(62,80,68))]
    im=gradient(idx,*palettes[idx%len(palettes)])
    d=ImageDraw.Draw(im,'RGBA'); rnd=random.Random(2200+idx)
    # Illustrated night sky: stars, constellation, orbit rings, moon glow.
    for _ in range(95):
        x=rnd.randint(25,W-25); y=rnd.randint(20,850); r=rnd.choice([1,1,2,2,3])
        a=rnd.randint(110,235); d.ellipse((x-r,y-r,x+r,y+r),fill=(255,245,205,a))
    cx,cy=840,215
    for rad,a in [(115,18),(88,25),(60,40)]: d.ellipse((cx-rad,cy-rad,cx+rad,cy+rad),fill=(255,225,170,a))
    d.ellipse((790,165,890,265),fill=(247,227,185,210))
    # Constellation unique per card.
    pts=[]
    for k in range(7): pts.append((150+k*105+rnd.randint(-35,35),180+rnd.randint(0,300)))
    for a,b in zip(pts,pts[1:]): d.line((a[0],a[1],b[0],b[1]),fill=(224,205,150,150),width=3)
    for x,y in pts:
        d.ellipse((x-7,y-7,x+7,y+7),fill=(255,244,188,240)); d.ellipse((x-18,y-18,x+18,y+18),outline=(255,230,170,45),width=2)
    # Orbital rings + sign medallion illustration.
    d.ellipse((110,590,970,1120),outline=(210,185,128,65),width=3)
    d.ellipse((175,650,905,1060),outline=(210,185,128,40),width=2)
    d.ellipse((390,660,690,960),fill=(8,12,28,115),outline=(224,194,124,180),width=5)
    symbol=['♈','♉','♊','♋','♌','♍'][idx]
    try: sf=font(180,False); d.text((540,810),symbol,font=sf,anchor='mm',fill=(247,221,160,230),stroke_width=2,stroke_fill=(60,35,20,180))
    except Exception: pass
    return im


def emotional_bg(idx):
    palettes=[((29,25,31),(105,68,54)),((18,28,41),(31,52,70)),((34,28,35),(82,54,64)),((17,31,38),(63,70,63)),((30,35,48),(118,87,54))]
    im=gradient(700+idx,*palettes[idx])
    d=ImageDraw.Draw(im,'RGBA')
    # Distinct, visible illustrated scene per story card.
    if idx==0:
        # wooden table, warm lamp, key
        d.rectangle((0,760,W,H),fill=(79,47,35,255)); d.line((0,910,W,850),fill=(130,83,55,120),width=6)
        d.ellipse((105,230,445,570),fill=(255,205,120,32)); d.rectangle((210,480,250,780),fill=(38,26,25,230)); d.polygon([(135,470),(325,470),(270,340),(190,340)],fill=(225,172,102,190))
        d.ellipse((635,895,735,995),outline=(230,190,110,255),width=18); d.line((720,945,895,1085),fill=(230,190,110,255),width=20); d.rectangle((865,1048,910,1082),fill=(230,190,110,255)); d.rectangle((825,1014,860,1055),fill=(230,190,110,255))
    elif idx==1:
        # rainy window, distant silhouette
        d.rectangle((120,145,960,1015),fill=(20,35,52,190),outline=(170,190,205,150),width=9)
        for x in [400,680]: d.line((x,145,x,1015),fill=(165,188,207,120),width=6)
        for y in [430,720]: d.line((120,y,960,y),fill=(165,188,207,100),width=5)
        rnd=random.Random(710)
        for _ in range(70):
            x=rnd.randint(140,940); y=rnd.randint(170,995); d.line((x,y,x-10,y+35),fill=(185,215,235,rnd.randint(50,140)),width=3)
        d.ellipse((470,735,610,875),fill=(8,12,18,220)); d.rectangle((455,850,625,1150),fill=(8,12,18,220))
    elif idx==2:
        # quiet doorway / conversation ending
        d.rectangle((165,160,915,1180),fill=(35,27,31,170),outline=(205,164,132,165),width=10)
        d.rectangle((520,190,885,1150),fill=(14,17,22,230)); d.polygon([(520,190),(735,250),(735,1080),(520,1150)],fill=(84,63,58,220))
        d.ellipse((270,615,395,740),fill=(14,14,20,235)); d.polygon([(255,725),(410,725),(450,1110),(215,1110)],fill=(14,14,20,235))
        d.ellipse((640,610,755,725),fill=(25,21,24,220)); d.polygon([(620,710),(770,710),(815,1110),(590,1110)],fill=(25,21,24,220))
    elif idx==3:
        # open door and person leaving toward light
        d.rectangle((160,150,920,1190),fill=(39,47,48,195),outline=(196,170,125,150),width=9)
        d.polygon([(520,190),(900,280),(900,1110),(520,1170)],fill=(116,103,73,190)); d.polygon([(560,240),(860,320),(860,1060),(560,1120)],fill=(226,196,129,120))
        d.ellipse((680,650,785,755),fill=(17,20,22,235)); d.polygon([(660,740),(800,740),(840,1130),(625,1130)],fill=(17,20,22,235))
        d.line((690,1080,560,1260),fill=(17,20,22,180),width=24); d.line((770,1080,890,1260),fill=(17,20,22,180),width=24)
    else:
        # sunrise road / healing
        d.ellipse((365,170,715,520),fill=(255,202,112,165)); d.rectangle((0,630,W,H),fill=(38,55,51,180))
        d.polygon([(430,H),(650,H),(590,610),(505,610)],fill=(54,50,48,235))
        for y in range(650,H,90):
            wid=int((y-610)*0.16+20); d.rectangle((540-wid//2,y,540+wid//2,y+24),fill=(230,214,170,120))
        d.polygon([(0,660),(300,460),(470,660)],fill=(24,43,44,220)); d.polygon([(650,660),(880,430),(1080,660)],fill=(24,43,44,220))
    return im


def compose(bg, title, text, footer=None, idx=0, total=1):
    im=bg.copy(); d=ImageDraw.Draw(im,'RGBA')
    # top title panel
    d.rounded_rectangle((55,55,1025,245),radius=30,fill=(5,8,18,190),outline=(235,204,145,100),width=3)
    text_box(im,title,(85,82,995,225),54,bold=True,center=True,min_size=36)
    # main text panel placed low enough to leave illustrated background visible
    d.rounded_rectangle((70,885,1010,1235),radius=28,fill=(4,7,15,205),outline=(255,255,255,45),width=2)
    text_box(im,text,(105,915,975,1135),44,bold=False,center=True,min_size=28)
    if footer:
        text_box(im,footer,(105,1135,975,1188),22,center=True,min_size=18,fill=(220,220,220,255))
    d.rounded_rectangle((65,1248,1015,1330),radius=20,fill=(10,14,24,235))
    text_box(im,CTA,(85,1255,995,1320),28,bold=True,center=True,min_size=22)
    return im.convert('RGB')


def make_music(path, seconds, seed=1):
    sr=44100; total=int(seconds*sr)
    chords=[(220.00,277.18,329.63),(196.00,246.94,293.66),(174.61,220.00,261.63),(196.00,246.94,329.63)]
    with wave.open(str(path),'w') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        frames=bytearray()
        for n in range(total):
            t=n/sr; ci=int(t/4)%len(chords); local=t%4
            env=min(1,local/0.4,(4-local)/0.4) if 0.4<local<3.6 else max(0.05,min(1,local/0.4,(4-local)/0.4))
            val=sum(math.sin(2*math.pi*f*t) for f in chords[ci])/3
            val += 0.24*math.sin(2*math.pi*(chords[ci][0]/2)*t)
            samp=int(max(-1,min(1,val*0.105*env))*32767)
            frames += int(samp).to_bytes(2,'little',signed=True)*2
        wf.writeframes(frames)


def slideshow(images, out, seconds_per, music):
    td=out.parent
    lst=td/(out.stem+'-concat.txt')
    lines=[]
    for p in images:
        lines += [f"file '{p.resolve()}'", f'duration {seconds_per}']
    lines.append(f"file '{images[-1].resolve()}'")
    lst.write_text('\n'.join(lines),encoding='utf-8')
    duration=len(images)*seconds_per
    make_music(music,duration)
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(lst),'-i',str(music),'-t',str(duration),'-vf','scale=1080:1350,pad=1080:1920:0:285:color=0x0A0E18,fps=25,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','21','-c:a','aac','-b:a','128k','-movflags','+faststart',str(out)])
    run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'])


def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--output',required=True); ns=ap.parse_args()
    batch=json.loads(Path(ns.manifest).read_text(encoding='utf-8'))
    if batch.get('approved') is not True or batch.get('paid_generation_allowed') is not False or batch.get('local_date')!='2026-09-22':
        raise ValueError('repair manifest safety gate failed')
    out=Path(ns.output)/'repair-20260922'; out.mkdir(parents=True,exist_ok=True)
    report={'local_date':'2026-09-22','paid_ai_credits_used':0,'jobs':[]}
    for job in batch['jobs']:
        if job['expected_cards'] not in (5,6) or len(job['slides'])!=job['expected_cards']: raise ValueError('card count mismatch')
        imgs=[]
        for i,sl in enumerate(job['slides']):
            bg=zodiac_bg(i) if 'zodiac' in job['id'] else emotional_bg(i)
            im=compose(bg,sl['title'],sl['text'],sl.get('footer'),i,len(job['slides']))
            p=out/f"{job['id']}-{i+1:02d}.jpg"; im.save(p,'JPEG',quality=94,subsampling=0,optimize=True)
            # Technical verification: file nonzero, JPEG, exact dimensions.
            if p.stat().st_size < 20000: raise ValueError(f'implausibly small card {p.name}')
            with Image.open(p) as chk:
                if chk.format!='JPEG' or chk.size!=(W,H): raise ValueError(f'bad card {p.name}')
            imgs.append(p)
        vid=out/f"{job['id']}-slideshow.mp4"; music=out/f"{job['id']}-original-music.wav"
        slideshow(imgs,vid,float(job.get('seconds_per_slide',6)),music)
        report['jobs'].append({'id':job['id'],'status':'rendered','cards':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in imgs],'slideshow':{'name':vid.name,'bytes':vid.stat().st_size,'sha256':sha(vid)},'music_source':'original deterministic synthesis; no catalog/licensed third-party audio','visual_background':'illustrated scene, not text-only','cta_exact':CTA})
        music.unlink(missing_ok=True); (out/(vid.stem+'-concat.txt')).unlink(missing_ok=True)
    (out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__': main()
