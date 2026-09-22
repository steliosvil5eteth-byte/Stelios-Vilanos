#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, random, subprocess, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W,H=1080,1920
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
CTA='Αν σας άρεσε, ακολουθήστε για περισσότερα.'

def run(cmd):
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
    if p.returncode: raise RuntimeError(p.stderr[-2500:])
    return p.stdout

def font(n,b=False): return ImageFont.truetype(BOLD if b else FONT,n)

def gradient(top,bottom):
    im=Image.new('RGB',(W,H)); px=im.load()
    for y in range(H):
        t=y/(H-1); c=tuple(int(top[i]*(1-t)+bottom[i]*t) for i in range(3))
        for x in range(W): px[x,y]=c
    return im.convert('RGBA')

def wrap(draw,text,f,maxw):
    lines=[]
    for para in text.split('\n'):
        cur=''
        for word in para.split():
            cand=(cur+' '+word).strip()
            if draw.textlength(cand,font=f)<=maxw: cur=cand
            else:
                if cur: lines.append(cur)
                cur=word
        if cur: lines.append(cur)
    return lines

def textbox(im,text,box,size,bold=True,center=False,min_size=24,fill=(255,255,255,255)):
    d=ImageDraw.Draw(im,'RGBA'); x0,y0,x1,y1=box
    for s in range(size,min_size-1,-2):
        f=font(s,bold); lines=wrap(d,text,f,x1-x0); lead=int(s*1.28)
        if len(lines)*lead<=y1-y0: break
    else: raise ValueError('text does not fit')
    y=y0
    for line in lines:
        tw=d.textlength(line,font=f); x=x0+(x1-x0-tw)/2 if center else x0
        d.text((x,y),line,font=f,fill=fill,stroke_width=1,stroke_fill=(0,0,0,190)); y+=lead

def story_bg(idx):
    pals=[((70,35,64),(18,28,50)),((35,47,65),(15,27,44)),((58,34,52),(22,25,40)),((43,38,70),(18,29,55)),((93,51,57),(25,38,55))]
    im=gradient(*pals[idx]); d=ImageDraw.Draw(im,'RGBA')
    if idx==0:
        d.rectangle((0,0,W,770),fill=(22,31,53,100)); d.rounded_rectangle((370,145,710,660),45,fill=(8,12,22,255),outline=(220,230,255,235),width=8)
        d.rounded_rectangle((415,270,665,450),28,fill=(85,135,205,245)); d.text((455,315),'ΠΡΟΧΕΙΡΟ',font=font(38,True),fill='white')
        d.ellipse((115,300,275,460),fill=(13,15,24,245)); d.rounded_rectangle((90,445,305,810),28,fill=(13,15,24,245))
    elif idx==1:
        d.rectangle((120,120,960,790),fill=(18,33,50,185),outline=(180,200,220,160),width=8)
        for x in (400,680): d.line((x,120,x,790),fill=(180,200,220,100),width=5)
        rnd=random.Random(23)
        for _ in range(70):
            x=rnd.randint(140,940); y=rnd.randint(145,770); d.line((x,y,x-12,y+38),fill=(190,215,235,105),width=3)
        d.ellipse((470,520,610,660),fill=(8,12,18,235)); d.rounded_rectangle((445,645,635,915),30,fill=(8,12,18,235))
    elif idx==2:
        d.rounded_rectangle((365,130,715,680),45,fill=(7,11,20,255),outline=(225,235,255,220),width=8)
        d.rounded_rectangle((410,260,670,440),28,fill=(79,130,205,245)); d.text((450,310),'ΑΠΟΣΤΑΛΗΚΕ',font=font(35,True),fill='white')
        d.ellipse((125,420,270,565),fill=(15,15,24,245)); d.rounded_rectangle((105,550,290,850),30,fill=(15,15,24,245)); d.ellipse((810,420,955,565),fill=(15,15,24,245)); d.rounded_rectangle((790,550,975,850),30,fill=(15,15,24,245))
    elif idx==3:
        d.ellipse((135,235,285,385),fill=(13,13,24,255)); d.rounded_rectangle((115,370,305,710),30,fill=(13,13,24,255)); d.ellipse((795,235,945,385),fill=(16,16,27,255)); d.rounded_rectangle((775,370,965,710),30,fill=(16,16,27,255))
        d.rounded_rectangle((395,140,685,590),42,fill=(8,10,18,255),outline=(220,230,255,255),width=8); d.rounded_rectangle((430,240,650,430),25,fill=(86,134,205,255)); d.text((468,310),'ΜΗΝΥΜΑ',font=font(31,True),fill='white')
    else:
        for x in (170,370,710,910): d.ellipse((x,80,x+38,118),fill=(255,220,130,220)); d.line((x+19,0,x+19,80),fill=(160,140,110,255),width=4)
        d.ellipse((250,430,830,680),fill=(92,54,38,255))
        for cx in (395,650):
            d.rectangle((cx-45,450,cx+45,520),fill=(235,230,215,255)); d.ellipse((cx-45,438,cx+45,475),fill=(80,50,30,255)); d.arc((cx+25,465,cx+85,525),0,300,fill=(235,230,215,255),width=12)
        d.ellipse((120,260,250,390),fill=(18,18,25,255)); d.rounded_rectangle((100,370,275,700),30,fill=(18,18,25,255)); d.ellipse((830,260,960,390),fill=(18,18,25,255)); d.rounded_rectangle((805,370,980,700),30,fill=(18,18,25,255))
    return im

def cloud(d,cx,cy,scale=1.0):
    for ox,oy,r in [(-120,20,130),(-30,-20,160),(80,15,135),(0,45,180)]:
        d.ellipse((cx+(ox-r)*scale,cy+(oy-r)*scale,cx+(ox+r)*scale,cy+(oy+r)*scale),fill=(61,72,102,255))

def bolt(x,y,s=1.0): return [(x,y),(x+70*s,y+120*s),(x+25*s,y+120*s),(x+95*s,y+245*s),(x-20*s,y+145*s),(x+25*s,y+145*s)]

def myth_bg(idx):
    im=gradient((20,42,72),(12,16,32)); d=ImageDraw.Draw(im,'RGBA'); cloud(d,540,300,1.5)
    if idx==0:
        d.polygon(bolt(470,300,1.5),fill=(255,229,105,255)); d.rectangle((470,620,610,900),fill=(25,28,35,255)); d.polygon([(540,500),(465,620),(615,620)],fill=(25,28,35,255))
    elif idx==1:
        d.polygon(bolt(690,330,1.2),fill=(255,229,105,255)); d.ellipse((120,430,250,560),fill=(15,18,26,255)); d.rounded_rectangle((100,550,275,920),30,fill=(15,18,26,255)); d.line((240,640,470,520),fill=(15,18,26,255),width=38)
    elif idx==2:
        for off in (-130,30,170): d.polygon(bolt(480+off,290,.75),fill=(255,229,105,230))
        d.rectangle((485,640,595,900),fill=(24,27,36,255)); d.polygon([(540,510),(470,640),(610,640)],fill=(24,27,36,255)); d.ellipse((470,880,610,1020),outline=(255,100,60,255),width=14)
    else:
        for x in (330,500,670): d.polygon(bolt(x,300,.8),fill=(255,229,105,220))
        d.rectangle((480,650,600,920),fill=(20,23,30,255)); d.polygon([(540,520),(460,650),(620,650)],fill=(20,23,30,255)); d.rounded_rectangle((255,955,825,1095),30,fill=(130,35,35,230)); d.text((390,985),'ΜΥΘΟΣ',font=font(72,True),fill='white')
    for x,w,h in [(0,150,280),(170,110,210),(300,130,250),(750,160,230),(920,160,300)]: d.rectangle((x,900-h,x+w,900),fill=(8,10,18,255))
    return im

def compose(bg,label,title,text,final=False):
    im=bg.copy(); d=ImageDraw.Draw(im,'RGBA')
    d.rounded_rectangle((45,35,1035,115),20,fill=(6,10,22,210)); d.text((75,55),label,font=font(28,True),fill='white')
    d.rounded_rectangle((55,1080,1025,1710),35,fill=(5,10,24,215)); d.text((85,1135),title,font=font(48,True),fill=(255,247,225,255)); textbox(im,text,(85,1245,995,1605),52,True,True,32)
    if final:
        d.rounded_rectangle((55,1740,1025,1880),24,fill=(20,30,55,235)); textbox(im,CTA,(90,1770,990,1860),32,True,True,24)
    d.text((800,1885),'@steliosvilanos',font=font(18),fill=(235,235,235,255)); return im.convert('RGB')

def make_music(path,seconds):
    sr=44100; total=int(seconds*sr); chords=[(220.0,277.18,329.63),(196.0,246.94,293.66),(174.61,220.0,261.63),(196.0,246.94,329.63)]
    with wave.open(str(path),'w') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr); buf=bytearray()
        for n in range(total):
            t=n/sr; c=chords[int(t/4)%4]; v=sum(math.sin(2*math.pi*f*t) for f in c)/3 + .2*math.sin(2*math.pi*(c[0]/2)*t); s=int(max(-1,min(1,v*.09))*32767); buf += s.to_bytes(2,'little',signed=True)*2
        wf.writeframes(buf)

def slideshow(cards,out,seconds_per):
    lst=out.with_suffix('.txt'); lines=[]
    for p in cards: lines += [f"file '{p.resolve()}'",f'duration {seconds_per}']
    lines.append(f"file '{cards[-1].resolve()}'"); lst.write_text('\n'.join(lines),encoding='utf-8'); dur=len(cards)*seconds_per; wav=out.with_suffix('.wav'); make_music(wav,dur)
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(lst),'-i',str(wav),'-t',str(dur),'-vf','fps=25,scale=1080:1920,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','24','-c:a','aac','-b:a','96k','-movflags','+faststart',str(out)])
    run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--output',required=True); ns=ap.parse_args(); data=json.loads(Path(ns.manifest).read_text())
    if data.get('approved') is not True or data.get('paid_generation_allowed') is not False or data.get('local_date')!='2026-09-23': raise ValueError('safety gate')
    out=Path(ns.output)/'fix-20260923-card-visuals'; out.mkdir(parents=True,exist_ok=True); report={'local_date':'2026-09-23','paid_ai_credits_used':0,'jobs':[]}
    for job in data['jobs']:
        cards=[]
        for i,sl in enumerate(job['slides']):
            bg=story_bg(i) if job['kind']=='story' else myth_bg(i); im=compose(bg,sl['label'],sl['title'],sl['text'],i==len(job['slides'])-1); p=out/f"{job['id']}-{i+1:02d}.jpg"; im.save(p,'JPEG',quality=90,optimize=True,subsampling=1)
            with Image.open(p) as chk:
                if chk.size!=(W,H) or chk.format!='JPEG': raise ValueError('bad image')
            if p.stat().st_size<30000: raise ValueError('implausibly small card')
            cards.append(p)
        vid=out/f"{job['id']}-youtube.mp4"; slideshow(cards,vid,float(job['seconds_per_card']))
        report['jobs'].append({'id':job['id'],'kind':job['kind'],'status':'rendered','cards':[p.name for p in cards],'youtube':vid.name})
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__': main()
