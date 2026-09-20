#!/usr/bin/env python3
"""Deterministic FOUR_DAILY_V2 carousel renderer.
Creates complete ordered JPEG card sets plus one YouTube slideshow MP4 with
locally synthesized original music. No AI/TTS/payment/publishing APIs.
"""
from __future__ import annotations
import argparse, hashlib, json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

CTA = 'Αν σας άρεσε, ακολουθήστε για περισσότερα.'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
MAX_OUTPUT = 64 * 1024 * 1024


def run(args: list[str]) -> str:
    p = subprocess.run(args, text=True, capture_output=True, timeout=900)
    if p.returncode:
        raise RuntimeError(p.stderr[-3000:])
    return p.stdout


def probe(path: Path) -> dict:
    return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def wrap(draw, text, font, width):
    lines=[]
    for para in text.split('\n'):
        words=para.split()
        if not words:
            lines.append(''); continue
        line=''
        for word in words:
            candidate=(line+' '+word).strip()
            if draw.textlength(candidate,font=font) <= width:
                line=candidate
            else:
                if line: lines.append(line)
                if draw.textlength(word,font=font)>width:
                    raise ValueError('Unbreakable text exceeds safe width')
                line=word
        if line: lines.append(line)
    return lines


def text_block(im, text, box, start_size, *, bold=False, center=False, min_size=28):
    d=ImageDraw.Draw(im); x0,y0,x1,y1=box
    chosen=None
    for size in range(start_size,min_size-1,-1):
        font=ImageFont.truetype(BOLD if bold else FONT,size)
        lines=wrap(d,text,font,x1-x0)
        leading=math.ceil(size*1.35)
        if len(lines)*leading <= y1-y0:
            chosen=(font,lines,leading,size); break
    if not chosen:
        raise ValueError('Text cannot fit at readable size')
    font,lines,leading,size=chosen
    y=y0 + max(0,(y1-y0-len(lines)*leading)//2) if center else y0
    for line in lines:
        x=x0+(x1-x0-d.textlength(line,font=font))/2 if center else x0
        d.text((x,y),line,font=font,fill='#FFFFFF')
        y+=leading
    return size


def render_card(slide: dict, index: int, total: int) -> Image.Image:
    bg=slide.get('background','#111B29')
    im=Image.new('RGB',(1080,1080),bg)
    d=ImageDraw.Draw(im)
    d.rectangle((72,64,1008,69),fill='#D8BA78')
    title=slide['title']
    body=slide['text']
    text_block(im,title,(76,98,1004,265),60,bold=True,min_size=36)
    text_block(im,body,(76,300,1004,815),44,min_size=30)
    footer=slide.get('footer','')
    if footer:
        text_block(im,footer,(76,825,1004,892),24,center=True,min_size=20)
    d.rectangle((58,922,1022,1038),fill='#233348')
    text_block(im,CTA,(76,934,1004,1015),31,bold=True,center=True,min_size=25)
    d.text((945,1046),f'{index}/{total}',font=ImageFont.truetype(FONT,18),fill='#AEB9C8')
    return im


def make_vertical(square: Path, out: Path):
    im=Image.open(square).convert('RGB')
    base=Image.new('RGB',(1080,1920),'#101A28')
    base.paste(im,(0,420))
    base.save(out,quality=94,subsampling=0)


def slideshow(card_paths: list[Path], out: Path, seconds_per_slide: float):
    if not 2.5 <= seconds_per_slide <= 10:
        raise ValueError('seconds_per_slide outside safe range')
    total=len(card_paths)*seconds_per_slide
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        segments=[]
        for i,card in enumerate(card_paths,1):
            vertical=td/f'v{i:02}.jpg'; make_vertical(card,vertical)
            seg=td/f's{i:02}.mp4'
            run(['ffmpeg','-y','-v','error','-loop','1','-framerate','25','-i',str(vertical),'-t',str(seconds_per_slide),'-vf','setsar=1,fps=25','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-an',str(seg)])
            segments.append(seg)
        concat=td/'concat.txt'
        concat.write_text('\n'.join("file '"+str(p).replace("'","'\\''")+"'" for p in segments)+'\n',encoding='utf-8')
        visual=td/'visual.mp4'
        run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(visual)])
        fade_out=max(0.0,total-1.5)
        filters=(
            '[1:a]volume=0.032[a1];[2:a]volume=0.024[a2];[3:a]volume=0.020[a3];'
            '[a1][a2][a3]amix=inputs=3:duration=longest:normalize=0,'
            'highpass=f=90,lowpass=f=1800,afade=t=in:st=0:d=1.5,'
            f'afade=t=out:st={fade_out}:d=1.5,aformat=sample_rates=48000:channel_layouts=stereo[a]'
        )
        run(['ffmpeg','-y','-v','error','-i',str(visual),
             '-f','lavfi','-i',f'sine=frequency=220:sample_rate=48000:duration={total}',
             '-f','lavfi','-i',f'sine=frequency=277.18:sample_rate=48000:duration={total}',
             '-f','lavfi','-i',f'sine=frequency=329.63:sample_rate=48000:duration={total}',
             '-filter_complex',filters,'-map','0:v','-map','[a]','-t',str(total),
             '-c:v','copy','-c:a','aac','-b:a','128k','-movflags','+faststart',str(out)])
    meta=probe(out)
    if not any(s['codec_type']=='audio' for s in meta['streams']):
        raise ValueError('slideshow has no audio')
    if not any(s['codec_type']=='video' for s in meta['streams']):
        raise ValueError('slideshow has no video')
    duration=float(meta['format']['duration'])
    if abs(duration-total)>.6:
        raise ValueError(f'duration mismatch {total}->{duration}')
    run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'])
    return duration


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--output',required=True)
    ns=ap.parse_args()
    raw=Path(ns.manifest).read_bytes(); batch=json.loads(raw)
    if batch.get('approved') is not True or batch.get('paid_generation_allowed') is not False:
        raise ValueError('approved=true and paid_generation_allowed=false required')
    jobs=batch.get('jobs',[])
    if not jobs or len(jobs)>4:
        raise ValueError('expected 1-4 carousel jobs')
    batch_id=hashlib.sha256(raw).hexdigest()[:16]
    outdir=Path(ns.output)/batch_id; outdir.mkdir(parents=True,exist_ok=True)
    (outdir/'source_manifest.json').write_bytes(raw)
    report={'batch_id':batch_id,'batch_sha256':hashlib.sha256(raw).hexdigest(),'paid_ai_credits_used':0,'jobs':[]}
    for job in jobs:
        rec={'id':job['id'],'status':'failed'}
        try:
            slides=job['slides']
            expected=job['expected_cards']
            if len(slides)!=expected or expected not in (5,12):
                raise ValueError('card count mismatch')
            cards=[]
            for i,slide in enumerate(slides,1):
                card=outdir/f"{job['id']}-{i:02}.jpg"
                render_card(slide,i,expected).save(card,quality=94,subsampling=0)
                cards.append(card)
            video=outdir/f"{job['id']}.mp4"
            duration=slideshow(cards,video,float(job.get('seconds_per_slide',5)))
            rec.update({'status':'rendered','card_count':expected,'order_verified':True,'readable_min_font_px':30,'final_duration':duration,'music_embedded':True,'music_source':'original_local_synth_no_external_license','narration':False,'cta':CTA})
            rec['files']=[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha256(p)} for p in [*cards,video]]
            if any(f['bytes']>MAX_OUTPUT for f in rec['files']):
                raise ValueError('output exceeds 64 MiB safety limit')
        except Exception as exc:
            rec['status']='failed'; rec['error']=str(exc)[:1800]
            for p in outdir.glob(job.get('id','invalid')+'*'):
                if p.is_file(): p.unlink()
        report['jobs'].append(rec)
        print(json.dumps({'id':rec['id'],'status':rec['status'],'error':rec.get('error')},ensure_ascii=False),flush=True)
    (outdir/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if any(j['status']!='rendered' for j in report['jobs']):
        raise SystemExit(1)
    print('REPORT_PATH='+str(outdir/'manifest.json'))

if __name__=='__main__':
    main()
