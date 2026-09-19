#!/usr/bin/env python3
"""Deterministic social-media finishing. No AI/TTS/payment or publishing APIs.
Only process explicit, approved public media jobs. Originals are never overwritten.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re, subprocess, tempfile, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

CTA = 'Αν σας άρεσε, ακολουθήστε για περισσότερα.'
ALLOWED_HOSTS = {'static.metricool.com', 'raw.githubusercontent.com', 'upload.wikimedia.org'}
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
MAX_DOWNLOAD = 150 * 1024 * 1024


def run(args: list[str]) -> str:
    p = subprocess.run(args, text=True, capture_output=True, timeout=600)
    if p.returncode:
        raise RuntimeError(p.stderr[-2000:])
    return p.stdout


def probe(p: Path) -> dict:
    return json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(p)]))


def digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def check_url(url: str) -> None:
    u = urllib.parse.urlsplit(url)
    if u.scheme != 'https' or u.hostname not in ALLOWED_HOSTS or u.username or u.password or u.port not in (None, 443):
        raise ValueError('Source must be an explicit HTTPS media URL on the allowed hosts')


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url: str, path: Path) -> None:
    check_url(url)
    req = urllib.request.Request(url, headers={'User-Agent': 'SteliosMediaFinisher/1.0'})
    with urllib.request.build_opener(SafeRedirect()).open(req, timeout=90) as r, path.open('wb') as f:
        check_url(r.url)
        total = 0
        for data in iter(lambda: r.read(1024*1024), b''):
            total += len(data)
            if total > MAX_DOWNLOAD:
                raise ValueError('Input exceeds the 150 MB safety limit')
            f.write(data)
    if total == 0:
        raise ValueError('Empty media')


def wrapped(draw, text, font, max_width):
    result=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split():
            candidate=(line+' '+word).strip()
            if draw.textlength(candidate, font=font) <= max_width:
                line=candidate
            else:
                if line: result.append(line)
                if draw.textlength(word, font=font)>max_width:
                    raise ValueError('Unbreakable text exceeds image width')
                line=word
        result.append(line)
    return result


def text_block(image, text, box, font_size, *, bold=False, fill='#FFFFFF', center=False, min_size=20):
    d=ImageDraw.Draw(image); x0,y0,x1,y1=box
    for size in range(max(font_size,min_size),min_size-1,-1):
        font=ImageFont.truetype(BOLD if bold else FONT,size)
        lines=wrapped(d,text,font,x1-x0)
        leading=math.ceil(size*1.4)
        if len(lines)*leading <= y1-y0:
            break
    else:
        raise ValueError('Text cannot fit without becoming unreadable')
    y=y0 + max(0, (y1-y0-len(lines)*leading)//2) if center else y0
    for line in lines:
        x=x0+(x1-x0-d.textlength(line,font=font))/2 if center else x0
        d.text((x,y),line,font=font,fill=fill,stroke_width=0)
        y+=leading
    return size


def end_card(size):
    w,h=size; im=Image.new('RGB',size,'#101A28');d=ImageDraw.Draw(im)
    d.rectangle((int(w*.12),int(h*.35),int(w*.88),int(h*.353)),fill='#D8BA78')
    text_block(im, CTA, (int(w*.10),int(h*.40),int(w*.90),int(h*.65)),int(w*.070),bold=True,center=True,min_size=int(w*.042))
    text_block(im,'ΣΤΕΛΙΟΣ • ΙΣΤΟΡΙΕΣ',(int(w*.1),int(h*.69),int(w*.9),int(h*.74)),int(w*.025),center=True,min_size=14)
    return im


def simple_image(job):
    im=Image.new('RGB',(1080,1080),job.get('background','#111B29'));d=ImageDraw.Draw(im)
    d.rectangle((76,64,1004,68),fill='#D8BA78')
    text_block(im,job['title'],(76,94,1004,264),64,bold=True,min_size=38)
    text_block(im,job['text'],(76,286,1004,830),44,min_size=30)
    if job.get('footer'):
        text_block(im,job['footer'],(76,836,1004,894),23,min_size=19)
    d.rectangle((60,923,1020,1036),fill='#233348')
    text_block(im,CTA,(80,938,1000,1024),32,bold=True,center=True,min_size=26)
    return im


def image_cta(job, work):
    src=work/'source.img';download(job['source_url'],src)
    im=Image.open(src).convert('RGB')
    base=Image.new('RGB',(1080,1080),'#101A28')
    fitted=ImageOps.contain(im,(1080,934),Image.Resampling.LANCZOS)
    base.paste(fitted,((1080-fitted.width)//2,(934-fitted.height)//2))
    text_block(base,CTA,(56,950,1024,1055),34,bold=True,center=True,min_size=28)
    return base


def silent_video(image: Path, out: Path, seconds: float=18):
    run(['ffmpeg','-y','-v','error','-loop','1','-framerate','25','-i',str(image),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t',str(seconds),'-vf','scale=1080:1080,pad=1080:1920:0:420:color=0x101A28,setsar=1','-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-movflags','+faststart','-shortest',str(out)])


def finish_video(job,work,outdir):
    src=work/'source.mp4';download(job['source_url'],src)
    meta=probe(src); v=next(s for s in meta['streams'] if s['codec_type']=='video')
    length=float(meta['format']['duration'])
    if not 10 <= length <= 240:
        raise ValueError(f'Unexpected original duration {length}; no cropped/two-second source accepted')
    w,h=int(v['width']),int(v['height'])
    if abs(w/h-9/16)>.03 or w%2 or h%2:
        raise ValueError('Original must be an even-sized vertical 9:16 video')
    scale=min(1,1080/w,1920/h);w=int(w*scale)//2*2;h=int(h*scale)//2*2
    card=work/'cta.png';end_card((w,h)).save(card)
    has_audio=any(s['codec_type']=='audio' for s in meta['streams'])
    if not has_audio:
        raise ValueError('Expected narrated original with an audio stream')
    out=outdir/(job['id']+'.mp4')
    filters=f'[0:v]scale={w}:{h},setsar=1,fps=25,format=yuv420p,setpts=PTS-STARTPTS[v0];[0:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a0];[1:v]setsar=1,fps=25,format=yuv420p,trim=duration=4,setpts=PTS-STARTPTS[v1];[2:a]atrim=duration=4,asetpts=PTS-STARTPTS[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]'
    run(['ffmpeg','-y','-v','error','-i',str(src),'-loop','1','-framerate','25','-i',str(card),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-filter_complex',filters,'-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','22','-threads','2','-c:a','aac','-b:a','128k','-movflags','+faststart',str(out)])
    final=probe(out);dl=float(final['format']['duration'])
    if abs(dl-(length+4))>.3:
        raise ValueError(f'Duration mismatch {length}->{dl}')
    run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'])
    for label,sec in [('opening',1),('middle',length/2),('ending',dl-2)]:
        run(['ffmpeg','-y','-v','error','-ss',str(sec),'-i',str(out),'-frames:v','1','-vf','scale=360:-2',str(outdir/(job['id']+'-'+label+'.jpg'))])
    return {'original_duration':length,'final_duration':dl,'width':w,'height':h,'original_narration_preserved':True,'new_spoken_cta':False,'written_cta_appended':True,'decode_passed':True,'subtitle_review':'original_pixels_preserved; human_visual_review_required'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--output',required=True);ns=ap.parse_args()
    manifest_path=Path(ns.manifest); raw=manifest_path.read_bytes();batch=json.loads(raw)
    if batch.get('approved') is not True or batch.get('paid_generation_allowed') is not False:
        raise ValueError('Explicit approval and no-paid-generation flags are required')
    jobs=batch['jobs'];ids=[x['id'] for x in jobs]
    if len(jobs)>60 or len(ids)!=len(set(ids)) or any(not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,80}',s) for s in ids):
        raise ValueError('Invalid, duplicate or too many jobs')
    key=hashlib.sha256(raw).hexdigest()[:16];output=Path(ns.output)/key;output.mkdir(parents=True,exist_ok=True)
    report={'batch_sha256':hashlib.sha256(raw).hexdigest(),'batch_id':key,'paid_ai_credits_used':0,'jobs':[]}
    for job in jobs:
        record={'id':job['id'],'mode':job['mode'],'status':'failed'}
        try:
            with tempfile.TemporaryDirectory() as td:
                work=Path(td)
                if job['mode']=='video_cta':
                    record.update(finish_video(job,work,output))
                elif job['mode'] in ('simple_post','image_cta'):
                    im=simple_image(job) if job['mode']=='simple_post' else image_cta(job,work)
                    jpg=output/(job['id']+'.jpg');im.save(jpg,quality=94,subsampling=0)
                    if job.get('youtube_copy',False):
                        vid=output/(job['id']+'.mp4');silent_video(jpg,vid,float(job.get('seconds',18)))
                        record['final_duration']=float(probe(vid)['format']['duration'])
                    record.update({'written_cta':True,'narration':False,'image_size':[1080,1080]})
                else:
                    raise ValueError('Unknown job mode')
            record['status']='rendered'
            record['files']=[{'name':p.name,'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(output.glob(job['id']+'.*'))]
            if any(f['bytes']>25*1024*1024 for f in record['files']):
                raise ValueError('Output exceeds 25 MB limit')
        except Exception as exc:
            record['status']='failed';record['error']=str(exc)[:1800]
            for p in output.glob(job['id']+'*'):p.unlink()
        report['jobs'].append(record)
        print(json.dumps({'id':record['id'],'status':record['status'],'error':record.get('error')},ensure_ascii=False),flush=True)
    (output/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('REPORT_PATH='+str(output/'manifest.json'))

if __name__=='__main__': main()
