#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W,H=1080,1920
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
CTA='Αν σας άρεσε, ακολουθήστε για περισσότερα.'

def run(cmd):
    p=subprocess.run(cmd,text=True,capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr[-2000:])
    return p.stdout

def font(sz,b=False): return ImageFont.truetype(BOLD if b else FONT,sz)

def wrap(draw,text,f,maxw):
    out=[]
    for para in text.split('\n'):
        words=para.split(); line=''
        for word in words:
            t=(line+' '+word).strip()
            if draw.textlength(t,font=f)<=maxw: line=t
            else:
                if line: out.append(line)
                line=word
        if line: out.append(line)
    return out

def text_box(draw,text,box,size,bold=False,fill='white',spacing=1.25):
    x0,y0,x1,y1=box
    for s in range(size,25,-2):
        f=font(s,bold); lines=wrap(draw,text,f,x1-x0); lead=int(s*spacing)
        if len(lines)*lead<=y1-y0: break
    y=y0+(y1-y0-len(lines)*lead)//2
    for line in lines:
        tw=draw.textlength(line,font=f)
        draw.text((x0+(x1-x0-tw)/2,y),line,font=f,fill=fill,stroke_width=2,stroke_fill=(0,0,0))
        y+=lead

def brain(draw,cx,cy,scale,glow=(72,185,255)):
    # head silhouette plus a clearly visible illustrated brain/network
    pts=[]
    for i in range(80):
        a=2*math.pi*i/80
        r=1+0.05*math.sin(5*a)
        pts.append((cx+scale*0.72*r*math.cos(a),cy+scale*0.55*r*math.sin(a)))
    draw.polygon(pts,fill=(14,35,70),outline=(115,184,255))
    nodes=[]
    for iy in range(-2,3):
        for ix in range(-3,4):
            x=cx+ix*scale*0.15+(iy%2)*scale*0.06
            y=cy+iy*scale*0.14
            if ((x-cx)/(scale*.62))**2+((y-cy)/(scale*.44))**2<1:
                nodes.append((x,y))
    for i,p in enumerate(nodes):
        for q in nodes[i+1:]:
            d=((p[0]-q[0])**2+(p[1]-q[1])**2)**0.5
            if d<scale*.23: draw.line((*p,*q),fill=(42,110,175),width=max(2,int(scale*.008)))
    for x,y in nodes:
        r=max(4,int(scale*.025)); draw.ellipse((x-r,y-r,x+r,y+r),fill=glow)

def backdrop(card_idx):
    im=Image.new('RGB',(W,H),(6,14,34)); d=ImageDraw.Draw(im)
    # gradient bands
    for y in range(H):
        t=y/(H-1); c=(int(6+14*t),int(14+14*t),int(34+30*t)); d.line((0,y,W,y),fill=c)
    # scene-specific visible illustration
    if card_idx==1:
        brain(d,540,590,650,(84,198,255))
        # scanning frame
        for x in (190,890): d.line((x,290,x,890),fill=(40,100,170),width=3)
        d.line((180,590,900,590),fill=(70,180,220),width=3)
    elif card_idx==2:
        brain(d,310,560,350,(110,215,255)); brain(d,770,560,350,(202,120,255))
        d.arc((260,920,820,1400),200,340,fill=(90,180,255),width=10)
        text_box(d,'?',(420,900,660,1260),190,True,fill=(111,205,255))
    elif card_idx==3:
        # MRI-like illustrated sequence, clearly visual not text-only
        for j in range(3):
            x=105+j*300
            d.rounded_rectangle((x,320,x+270,760),radius=20,fill=(10,28,58),outline=(88,165,240),width=4)
            brain(d,x+135,535,210,(90+40*j,190,255))
        for j in range(6):
            x=130+j*145; d.line((x,850,x+80,1040),fill=(40,130+10*j,190),width=5)
            d.ellipse((x+60,1015,x+100,1055),fill=(80,190,255))
    else:
        brain(d,540,570,720,(120,224,255))
        for k in range(12):
            a=2*math.pi*k/12
            x1=540+400*math.cos(a); y1=570+320*math.sin(a)
            x2=540+490*math.cos(a); y2=570+410*math.sin(a)
            d.line((x1,y1,x2,y2),fill=(110,220,255),width=8)
    return im

def make_card(idx,title,body,out):
    im=backdrop(idx); d=ImageDraw.Draw(im,'RGBA')
    d.rounded_rectangle((60,1050,1020,1770),radius=38,fill=(4,9,24,215),outline=(92,175,255,230),width=4)
    d.rounded_rectangle((55,45,1025,145),radius=30,fill=(0,0,0,170))
    text_box(d,f'ΜΥΘΟΣ Ή ΑΛΗΘΕΙΑ;   {idx}/4',(80,55,1000,135),38,True)
    text_box(d,title,(110,1090,970,1290),56,True,fill=(104,205,255))
    text_box(d,body,(110,1290,970,1645),46,False)
    text_box(d,CTA,(100,1675,980,1760),31,True,fill=(225,235,245))
    im.save(out,'JPEG',quality=94,subsampling=0)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
    raw=Path(a.manifest).read_bytes(); m=json.loads(raw); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    if not m.get('approved') or m.get('paid_generation_allowed') is not False: raise ValueError('approval/no-paid flags required')
    cards=m['cards'];
    if len(cards)!=4 or [c['index'] for c in cards] != [1,2,3,4]: raise ValueError('exactly four ordered cards required')
    jpgs=[]
    for c in cards:
        p=out/f"{m['id']}-card-{c['index']}.jpg"; make_card(c['index'],c['title'],c['body'],p); jpgs.append(p)
        im=Image.open(p); im.verify()
        if p.stat().st_size<100000: raise ValueError('card too small / likely invalid')
    # original deterministic instrumental bed: layered synthesized tones; no external recording/copyright source.
    listfile=out/'frames.txt'
    listfile.write_text(''.join(f"file '{p.resolve()}'\nduration 7\n" for p in jpgs)+f"file '{jpgs[-1].resolve()}'\n",encoding='utf-8')
    mp4=out/f"{m['id']}-youtube.mp4"
    filt="sine=frequency=220:sample_rate=48000:duration=28,volume=0.035[a0];sine=frequency=329.63:sample_rate=48000:duration=28,volume=0.018[a1];sine=frequency=440:sample_rate=48000:duration=28,volume=0.010[a2];[a0][a1][a2]amix=inputs=3:normalize=0,afade=t=in:st=0:d=1.5,afade=t=out:st=26:d=2[a]"
    run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(listfile),'-f','lavfi','-i',filt,'-map','0:v','-map','1:a','-vf','scale=1080:1920,fps=30,format=yuv420p','-t','28','-c:v','libx264','-preset','veryfast','-crf','22','-c:a','aac','-b:a','128k','-movflags','+faststart',str(mp4)])
    qa={'id':m['id'],'cards':4,'order':[1,2,3,4],'jpeg_only':all(p.suffix=='.jpg' for p in jpgs),'visible_illustration':'deterministic brain/neural/MRI-style illustration on every card','cta_exact':CTA,'youtube_music':'original deterministic synthesized instrumental, no external recording','narration':False,'paid_credits_used':0,'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in jpgs+[mp4]]}
    (out/'qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(qa,ensure_ascii=False))
if __name__=='__main__': main()
