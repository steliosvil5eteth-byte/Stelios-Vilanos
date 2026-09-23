#!/usr/bin/env python3
"""Render one fact-checked 9-card SURVIVAL carousel plus a YouTube slideshow.
No AI/TTS/payment/publishing APIs. Visuals must be explicit reusable HTTPS images.
TikTok/FB/IG outputs are silent 1080x1080 JPEGs. The YouTube slideshow uses a
locally synthesized instrumental bed and no narration.
"""
from __future__ import annotations
import argparse, hashlib, json, math, subprocess, tempfile, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
TITLE='ΚΑΝΟΝΕΣ ΕΠΙΒΙΩΣΗΣ'; CTA='Αν σας άρεσε, ακολουθήστε για περισσότερα.'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
ALLOWED_HOSTS={'upload.wikimedia.org','images.weserv.nl'}; MAX_DOWNLOAD=30*1024*1024; MAX_OUTPUT=64*1024*1024

def run(args):
 p=subprocess.run(args,text=True,capture_output=True,timeout=900)
 if p.returncode: raise RuntimeError(p.stderr[-3000:])
 return p.stdout

def sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()
def check_url(url):
 u=urllib.parse.urlsplit(url)
 if u.scheme!='https' or u.hostname not in ALLOWED_HOSTS or u.username or u.password: raise ValueError('source_url must be explicit approved HTTPS reusable media')
def download(url,dest):
 check_url(url); req=urllib.request.Request(url,headers={'User-Agent':'SteliosSurvivalRenderer/1.2','Accept':'image/*,*/*;q=0.5'})
 with urllib.request.urlopen(req,timeout=120) as r:
  data=r.read(MAX_DOWNLOAD+1)
 if not data or len(data)>MAX_DOWNLOAD: raise ValueError('invalid source image size')
 dest.write_bytes(data)
def wrap(draw,text,font,width):
 lines=[]
 for para in text.split('\n'):
  words=para.split()
  if not words: lines.append(''); continue
  line=''
  for word in words:
   cand=(line+' '+word).strip()
   if draw.textlength(cand,font=font)<=width: line=cand
   else:
    if line: lines.append(line)
    if draw.textlength(word,font=font)>width: raise ValueError('unbreakable text exceeds safe width')
    line=word
  if line: lines.append(line)
 return lines
def draw_text_block(im,text,box,start,*,bold=False,center=False,min_size=27,fill='#FFFFFF'):
 d=ImageDraw.Draw(im); x0,y0,x1,y1=box; selected=None
 for size in range(start,min_size-1,-1):
  font=ImageFont.truetype(BOLD if bold else FONT,size); lines=wrap(d,text,font,x1-x0); leading=math.ceil(size*1.28)
  if len(lines)*leading<=y1-y0: selected=(font,lines,leading,size); break
 if not selected: raise ValueError('text cannot fit at readable size')
 font,lines,leading,size=selected; y=y0+max(0,(y1-y0-len(lines)*leading)//2) if center else y0
 for line in lines:
  x=x0+(x1-x0-d.textlength(line,font=font))/2 if center else x0; d.text((x,y),line,font=font,fill=fill,stroke_width=1,stroke_fill='#000'); y+=leading
 return size
def render_card(slide,index,total,work):
 src=work/f'source-{index:02}.img'; download(slide['source_url'],src); photo=Image.open(src).convert('RGB')
 im=ImageOps.fit(photo,(1080,1080),method=Image.Resampling.LANCZOS,centering=(0.5,0.5)); im=ImageEnhance.Contrast(im).enhance(.95)
 ov=Image.new('RGBA',(1080,1080),(0,0,0,0)); od=ImageDraw.Draw(ov); od.rectangle((0,0,1080,1080),fill=(0,0,0,58)); od.rounded_rectangle((48,45,1032,910),radius=30,fill=(0,0,0,125)); im=Image.alpha_composite(im.convert('RGBA'),ov).convert('RGB')
 d=ImageDraw.Draw(im); d.rectangle((70,58,1010,64),fill='#E2C47E')
 draw_text_block(im,TITLE,(72,82,1008,165),46,bold=True,center=True,min_size=34); draw_text_block(im,slide['subtitle'],(72,174,1008,285),38,bold=True,center=True,min_size=27); draw_text_block(im,slide['text'],(76,310,1004,820),40,min_size=27)
 d.rounded_rectangle((58,922,1022,1038),radius=18,fill=(15,24,36)); draw_text_block(im,CTA,(76,936,1004,1016),29,bold=True,center=True,min_size=23); d.text((945,1047),f'{index}/{total}',font=ImageFont.truetype(FONT,18),fill='#D5DCE6'); return im
def make_vertical(square,out):
 im=Image.open(square).convert('RGB'); base=Image.new('RGB',(1080,1920),'#101A28'); base.paste(im,(0,420)); base.save(out,quality=94,subsampling=0)
def slideshow(cards,out,seconds):
 total=len(cards)*seconds
 with tempfile.TemporaryDirectory() as td:
  td=Path(td); segs=[]
  for i,c in enumerate(cards,1):
   v=td/f'v{i}.jpg'; make_vertical(c,v); s=td/f's{i}.mp4'; run(['ffmpeg','-y','-v','error','-loop','1','-framerate','25','-i',str(v),'-t',str(seconds),'-vf','setsar=1,fps=25','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-an',str(s)]); segs.append(s)
  lst=td/'concat.txt'; lst.write_text('\n'.join("file '"+str(x)+"'" for x in segs)+'\n'); visual=td/'visual.mp4'; run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(visual)])
  fade=max(0,total-1.5); filt='[1:a]volume=0.032[a1];[2:a]volume=0.024[a2];[3:a]volume=0.020[a3];[a1][a2][a3]amix=inputs=3:duration=longest:normalize=0,highpass=f=90,lowpass=f=1800,afade=t=in:st=0:d=1.5,afade=t=out:st='+str(fade)+':d=1.5,aformat=sample_rates=48000:channel_layouts=stereo[a]'
  run(['ffmpeg','-y','-v','error','-i',str(visual),'-f','lavfi','-i',f'sine=frequency=196:sample_rate=48000:duration={total}','-f','lavfi','-i',f'sine=frequency=246.94:sample_rate=48000:duration={total}','-f','lavfi','-i',f'sine=frequency=293.66:sample_rate=48000:duration={total}','-filter_complex',filt,'-map','0:v','-map','[a]','-t',str(total),'-c:v','copy','-c:a','aac','-b:a','128k','-movflags','+faststart',str(out)])
 return total
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--output',required=True); ns=ap.parse_args(); raw=Path(ns.manifest).read_bytes(); batch=json.loads(raw)
 if batch.get('approved') is not True or batch.get('paid_generation_allowed') is not False: raise ValueError('approval/no-paid flags required')
 jobs=batch.get('jobs',[])
 if len(jobs)!=1: raise ValueError('exactly one survival job required')
 job=jobs[0]; slides=job['slides']
 if job.get('expected_cards')!=9 or len(slides)!=9: raise ValueError('survival requires exactly 9 cards')
 if not all(s.get('visible_title')==TITLE and s.get('source_url') for s in slides): raise ValueError('title/source gate failed')
 outdir=Path(ns.output)/hashlib.sha256(raw).hexdigest()[:16]; outdir.mkdir(parents=True,exist_ok=True); (outdir/'source_manifest.json').write_bytes(raw)
 cards=[]
 with tempfile.TemporaryDirectory() as td:
  work=Path(td)
  for i,s in enumerate(slides,1):
   p=outdir/f"{job['id']}-{i:02}.jpg"; render_card(s,i,9,work).save(p,quality=94,subsampling=0); cards.append(p)
 video=outdir/f"{job['id']}.mp4"; duration=slideshow(cards,video,float(job.get('seconds_per_slide',5)))
 report={'batch_id':outdir.name,'paid_ai_credits_used':0,'jobs':[{'id':job['id'],'status':'rendered','card_count':9,'image_size':[1080,1080],'order_verified':True,'photographic_backgrounds':True,'final_duration':duration,'narration':False,'music_source':'original_local_synth_no_external_license','files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha256(p)} for p in [*cards,video]]}]}
 (outdir/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)); print('REPORT_PATH='+str(outdir/'manifest.json'))
if __name__=='__main__': main()
