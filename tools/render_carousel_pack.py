#!/usr/bin/env python3
"""Deterministic carousel renderer.
Creates complete ordered 1080x1080 JPEG card sets from explicit reusable photos
plus one vertical YouTube slideshow with locally synthesized original music.
No AI/TTS/payment/publishing APIs.
"""
from __future__ import annotations
import argparse, hashlib, html, json, math, re, subprocess, tempfile, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance

CTA='Αν σας άρεσε, ακολουθήστε για περισσότερα.'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
MAX_OUTPUT=64*1024*1024
MAX_DOWNLOAD=25*1024*1024
ALLOWED_HOSTS={'images.weserv.nl','noirlab.edu','storage.noirlab.edu','upload.wikimedia.org','commons.wikimedia.org'}
_CACHE={}
_BAD=('illustration','drawing','map','logo','coat of arms','diagram','icon','poster','stamp')
_ALLOWED_LICENSE=('cc by','cc0','public domain')

def run(args):
    p=subprocess.run(args,text=True,capture_output=True,timeout=900)
    if p.returncode: raise RuntimeError(p.stderr[-3000:])
    return p.stdout

def probe(path): return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def check_url(url):
    u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or u.hostname not in ALLOWED_HOSTS or u.username or u.password:
        raise ValueError('source_url must be approved HTTPS reusable media host')

def download(url,dst):
    check_url(url)
    if url in _CACHE:
        dst.write_bytes(_CACHE[url]); return
    req=urllib.request.Request(url,headers={'User-Agent':'SteliosPhotoCarousel/2.0','Accept':'image/*,*/*;q=0.5'})
    with urllib.request.urlopen(req,timeout=120) as r:
        data=r.read(MAX_DOWNLOAD+1)
    if not data or len(data)>MAX_DOWNLOAD: raise ValueError('invalid source image size')
    _CACHE[url]=data; dst.write_bytes(data)

def _clean(s): return re.sub('<[^>]+>','',html.unescape(s or '')).strip()

def commons_fallback(query,dst):
    params={'action':'query','format':'json','generator':'search','gsrsearch':query,'gsrnamespace':'6','gsrlimit':'20','prop':'imageinfo','iiprop':'url|size|extmetadata','iiurlwidth':'1600'}
    url='https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={'User-Agent':'SteliosPhotoCarousel/2.0'})
    with urllib.request.urlopen(req,timeout=90) as r:
        payload=json.loads(r.read().decode('utf-8'))
    pages=list(payload.get('query',{}).get('pages',{}).values())
    for p in pages:
        title=p.get('title',''); low=title.lower()
        if any(x in low for x in _BAD) or not re.search(r'\.(jpe?g|png)$',title,re.I): continue
        infos=p.get('imageinfo') or []
        if not infos: continue
        info=infos[0]; meta=info.get('extmetadata',{})
        lic=(_clean(meta.get('LicenseShortName',{}).get('value',''))+' '+_clean(meta.get('UsageTerms',{}).get('value',''))).lower()
        if not any(x in lic for x in _ALLOWED_LICENSE): continue
        if min(int(info.get('width') or 0),int(info.get('height') or 0))<600: continue
        imgurl=info.get('thumburl') or info.get('url')
        if not imgurl: continue
        try:
            download(imgurl,dst)
            with Image.open(dst) as im:
                if min(im.size)<600: raise ValueError('fallback image too small')
            return {'source_url':imgurl,'source_credit':_clean(meta.get('Artist',{}).get('value','')),'license':_clean(meta.get('LicenseShortName',{}).get('value','')) or _clean(meta.get('UsageTerms',{}).get('value','')),'source_title':title}
        except Exception:
            dst.unlink(missing_ok=True)
    raise ValueError(f'no rights-cleared Commons fallback found for query: {query}')

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

def text_block(im,text,box,start_size,*,bold=False,center=False,min_size=27,fill='#FFFFFF'):
    d=ImageDraw.Draw(im); x0,y0,x1,y1=box; chosen=None
    for size in range(start_size,min_size-1,-1):
        font=ImageFont.truetype(BOLD if bold else FONT,size); lines=wrap(d,text,font,x1-x0); leading=math.ceil(size*1.30)
        if len(lines)*leading<=y1-y0: chosen=(font,lines,leading,size); break
    if not chosen: raise ValueError('text cannot fit at readable size')
    font,lines,leading,size=chosen; y=y0+max(0,(y1-y0-len(lines)*leading)//2) if center else y0
    for line in lines:
        x=x0+(x1-x0-d.textlength(line,font=font))/2 if center else x0
        d.text((x,y),line,font=font,fill=fill,stroke_width=1,stroke_fill='#000000'); y+=leading
    return size

def render_card(slide,index,total,work,require_photo):
    if require_photo and not slide.get('source_url') and not slide.get('source_query'): raise ValueError('photographic source_url or source_query required')
    if slide.get('source_url') or slide.get('source_query'):
        src=work/f'src-{index:02}.img'; used=None
        if slide.get('source_url'):
            try:
                download(slide['source_url'],src); used={'source_url':slide['source_url'],'source_credit':slide.get('source_credit',''),'license':slide.get('license','')}
            except Exception:
                if not slide.get('source_query'): raise
        if used is None:
            used=commons_fallback(slide['source_query'],src)
        slide['_resolved_source']=used
        photo=Image.open(src).convert('RGB')
        im=ImageOps.fit(photo,(1080,1080),method=Image.Resampling.LANCZOS,centering=(0.5,0.5))
        im=ImageEnhance.Contrast(im).enhance(0.92)
        overlay=Image.new('RGBA',(1080,1080),(0,0,0,0)); od=ImageDraw.Draw(overlay)
        od.rectangle((0,0,1080,1080),fill=(0,0,0,65))
        od.rounded_rectangle((48,55,1032,905),radius=30,fill=(0,0,0,120))
        im=Image.alpha_composite(im.convert('RGBA'),overlay).convert('RGB')
    else:
        im=Image.new('RGB',(1080,1080),slide.get('background','#111B29'))
    d=ImageDraw.Draw(im)
    d.rectangle((72,64,1008,70),fill='#D8BA78')
    title=slide.get('visible_title') or slide['title']; subtitle=slide.get('subtitle','')
    if subtitle:
        text_block(im,title,(76,90,1004,185),52,bold=True,center=True,min_size=34)
        text_block(im,subtitle,(76,190,1004,285),39,bold=True,center=True,min_size=27)
        body_box=(76,315,1004,815)
    else:
        text_block(im,title,(76,98,1004,265),56,bold=True,min_size=34)
        body_box=(76,300,1004,815)
    text_block(im,slide['text'],body_box,42,min_size=28)
    footer=slide.get('footer','')
    if footer: text_block(im,footer,(76,825,1004,885),21,center=True,min_size=18)
    d.rounded_rectangle((58,920,1022,1038),radius=18,fill=(15,24,36))
    text_block(im,CTA,(76,934,1004,1015),30,bold=True,center=True,min_size=24)
    d.text((945,1046),f'{index}/{total}',font=ImageFont.truetype(FONT,18),fill='#D5DCE6')
    return im

def make_vertical(square,out):
    im=Image.open(square).convert('RGB'); base=Image.new('RGB',(1080,1920),'#101A28'); base.paste(im,(0,420)); base.save(out,quality=94,subsampling=0)

def slideshow(card_paths,out,seconds_per_slide):
    if not 2.5<=seconds_per_slide<=10: raise ValueError('seconds_per_slide outside safe range')
    total=len(card_paths)*seconds_per_slide
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); segs=[]
        for i,card in enumerate(card_paths,1):
            vertical=td/f'v{i:02}.jpg'; make_vertical(card,vertical); seg=td/f's{i:02}.mp4'
            run(['ffmpeg','-y','-v','error','-loop','1','-framerate','25','-i',str(vertical),'-t',str(seconds_per_slide),'-vf','setsar=1,fps=25','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-an',str(seg)]); segs.append(seg)
        concat=td/'concat.txt'; concat.write_text('\n'.join("file '"+str(p).replace("'","'\\''")+"'" for p in segs)+'\n',encoding='utf-8')
        visual=td/'visual.mp4'; run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(visual)])
        fade=max(0,total-1.5)
        filters='[1:a]volume=0.032[a1];[2:a]volume=0.024[a2];[3:a]volume=0.020[a3];[a1][a2][a3]amix=inputs=3:duration=longest:normalize=0,highpass=f=90,lowpass=f=1800,afade=t=in:st=0:d=1.5,afade=t=out:st='+str(fade)+':d=1.5,aformat=sample_rates=48000:channel_layouts=stereo[a]'
        run(['ffmpeg','-y','-v','error','-i',str(visual),'-f','lavfi','-i',f'sine=frequency=220:sample_rate=48000:duration={total}','-f','lavfi','-i',f'sine=frequency=277.18:sample_rate=48000:duration={total}','-f','lavfi','-i',f'sine=frequency=329.63:sample_rate=48000:duration={total}','-filter_complex',filters,'-map','0:v','-map','[a]','-t',str(total),'-c:v','copy','-c:a','aac','-b:a','128k','-movflags','+faststart',str(out)])
    meta=probe(out)
    if not any(s['codec_type']=='audio' for s in meta['streams']) or not any(s['codec_type']=='video' for s in meta['streams']): raise ValueError('slideshow stream missing')
    duration=float(meta['format']['duration'])
    if abs(duration-total)>.6: raise ValueError('duration mismatch')
    return duration

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--output',required=True); ns=ap.parse_args()
    raw=Path(ns.manifest).read_bytes(); batch=json.loads(raw)
    if batch.get('approved') is not True or batch.get('paid_generation_allowed') is not False: raise ValueError('approved=true and paid_generation_allowed=false required')
    jobs=batch.get('jobs',[])
    if batch.get('require_photographic_visuals') is not True:
        raise ValueError('require_photographic_visuals=true required; plain/text-only carousel cards are forbidden')
    require_photo=True
    if not jobs or len(jobs)>8: raise ValueError('expected 1-8 carousel jobs')
    batch_id=hashlib.sha256(raw).hexdigest()[:16]; outdir=Path(ns.output)/batch_id; outdir.mkdir(parents=True,exist_ok=True); (outdir/'source_manifest.json').write_bytes(raw)
    report={'batch_id':batch_id,'batch_sha256':hashlib.sha256(raw).hexdigest(),'paid_ai_credits_used':0,'photographic_visuals_required':require_photo,'jobs':[]}
    for job in jobs:
        rec={'id':job['id'],'status':'failed'}
        try:
            slides=job['slides']; expected=job['expected_cards']
            if len(slides)!=expected or expected not in (4,5,6,7,9,12): raise ValueError('card count mismatch')
            with tempfile.TemporaryDirectory() as td:
                work=Path(td); cards=[]
                for i,slide in enumerate(slides,1):
                    card=outdir/f"{job['id']}-{i:02}.jpg"; render_card(slide,i,expected,work,require_photo).save(card,quality=94,subsampling=0); cards.append(card)
                video=outdir/f"{job['id']}.mp4"; duration=slideshow(cards,video,float(job.get('seconds_per_slide',5)))
            rec.update({'status':'rendered','card_count':expected,'order_verified':True,'image_size':[1080,1080],'photographic_backgrounds':require_photo,'readable_min_font_px':28,'final_duration':duration,'music_embedded':True,'music_source':'original_local_synth_no_external_license','narration':False,'cta':CTA,'resolved_sources':[s.get('_resolved_source') for s in slides]})
            rec['files']=[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha256(p)} for p in [*cards,video]]
            if any(f['bytes']>MAX_OUTPUT for f in rec['files']): raise ValueError('output exceeds 64 MiB')
        except Exception as exc:
            rec['status']='failed'; rec['error']=str(exc)[:1800]
            for p in outdir.glob(job.get('id','invalid')+'*'):
                if p.is_file(): p.unlink()
        report['jobs'].append(rec); print(json.dumps({'id':rec['id'],'status':rec['status'],'error':rec.get('error')},ensure_ascii=False),flush=True)
    (outdir/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if any(j['status']!='rendered' for j in report['jobs']): raise SystemExit(1)
    print('REPORT_PATH='+str(outdir/'manifest.json'))
if __name__=='__main__': main()
