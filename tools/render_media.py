#!/usr/bin/env python3
"""Deterministic social-media finishing. No AI/TTS/payment or publishing APIs.
Only process explicit approved public jobs. Originals are never overwritten.
"""
from __future__ import annotations
import argparse, base64, datetime, hashlib, io, json, math, re, subprocess, tempfile, time, urllib.error, urllib.parse, urllib.request
from email.utils import parsedate_to_datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance

CTA = 'Αν σας άρεσε, ακολουθήστε για περισσότερα.'
ALLOWED_HOSTS = {'static.metricool.com', 'raw.githubusercontent.com', 'upload.wikimedia.org'}
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
MAX_DOWNLOAD = 150 * 1024 * 1024
MAX_OUTPUT = 64 * 1024 * 1024
USER_AGENT = 'SteliosMediaFinisher/1.3 (media-import bot; +https://github.com/steliosvil5eteth-byte/Stelios-Vilanos)'
WIKIMEDIA_INTERVAL = 30.0
DEFAULT_429_COOLDOWN = 60.0
MAX_RETRY_AFTER = 300.0
DETAIL_MAX_BYTES = 900 * 1024


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


class RateLimitedBatch(RuntimeError):
    """No further source requests are permitted in this batch."""


class DownloadPolicy:
    def __init__(self):
        self.events = []
        self.last_wikimedia_attempt = None
        self.retry_not_before = 0.0
        self.rate_limits = 0
        self.stop_reason = None

    def record(self, decision, **details):
        event = {'at_utc': datetime.datetime.fromtimestamp(time.time(), datetime.timezone.utc).isoformat(),
                 'decision': decision, **details}
        self.events.append(event)
        print(json.dumps({'download_policy': event}, ensure_ascii=False), flush=True)

    def before_request(self, url, attempt, redirect=False):
        host = urllib.parse.urlsplit(url).hostname
        if self.stop_reason:
            self.record('source_request_not_attempted', source_host=host, reason=self.stop_reason)
            raise RateLimitedBatch(self.stop_reason)
        target = self.retry_not_before
        if host == 'upload.wikimedia.org' and self.last_wikimedia_attempt is not None:
            target = max(target, self.last_wikimedia_attempt + WIKIMEDIA_INTERVAL)
        delay = max(0.0, target - time.monotonic())
        if delay:
            self.record('wait_before_source_request', source_host=host, attempt=attempt,
                        wait_seconds=round(delay, 3),
                        not_before_utc=datetime.datetime.fromtimestamp(time.time() + delay, datetime.timezone.utc).isoformat())
            while True:
                remaining = target - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(60.0, remaining))
        if host == 'upload.wikimedia.org':
            self.last_wikimedia_attempt = time.monotonic()
        self.record('source_request_started', source_host=host, attempt=attempt, redirect=redirect)

    def rate_limited(self, error, url, attempt):
        received_monotonic, received_wall = time.monotonic(), time.time()
        raw = str((error.headers or {}).get('Retry-After', '')).strip()
        delay, basis = DEFAULT_429_COOLDOWN, 'default_60_seconds'
        try:
            if re.fullmatch(r'[0-9]+', raw):
                delay, basis = int(raw), 'retry_after_seconds'
            elif raw:
                moment = parsedate_to_datetime(raw)
                if moment.tzinfo is None:
                    raise ValueError('HTTP-date has no timezone')
                delay, basis = max(0.0, moment.timestamp() - received_wall), 'retry_after_http_date'
        except (TypeError, ValueError, OverflowError):
            pass
        error.close()
        self.rate_limits += 1
        self.record('http_429', source_host=urllib.parse.urlsplit(url).hostname, attempt=attempt,
                    batch_429_count=self.rate_limits, retry_after_seconds=delay, retry_after_basis=basis)
        if self.rate_limits >= 2 or attempt >= 2:
            self.stop_reason = 'RATE_LIMIT_BATCH_STOP_SECOND_429'
        elif delay > MAX_RETRY_AFTER:
            self.stop_reason = 'RATE_LIMIT_BATCH_STOP_RETRY_AFTER_OVER_300_SECONDS'
        if self.stop_reason:
            self.record('batch_source_requests_stopped', reason=self.stop_reason)
            raise RateLimitedBatch(self.stop_reason)
        self.retry_not_before = received_monotonic + delay
        self.record('single_retry_scheduled', attempt=attempt + 1, cooldown_seconds=delay)


DOWNLOAD_POLICY = DownloadPolicy()


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, policy=None, attempt=1):
        super().__init__()
        self.policy = policy if policy is not None else DOWNLOAD_POLICY
        self.attempt = attempt

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            self.policy.before_request(newurl, self.attempt, redirect=True)
        return redirected


def download(url: str, path: Path) -> None:
    check_url(url)
    for attempt in (1, 2):
        DOWNLOAD_POLICY.before_request(url, attempt)
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        try:
            with urllib.request.build_opener(SafeRedirect(DOWNLOAD_POLICY, attempt)).open(req, timeout=90) as r, path.open('wb') as f:
                check_url(r.url)
                total = 0
                for data in iter(lambda: r.read(1024*1024), b''):
                    total += len(data)
                    if total > MAX_DOWNLOAD:
                        raise ValueError('Input exceeds the 150 MiB safety limit')
                    f.write(data)
            if total == 0:
                raise ValueError('Empty media')
            DOWNLOAD_POLICY.record('source_download_completed', source_host=urllib.parse.urlsplit(url).hostname,
                                   attempt=attempt, bytes=total)
            return
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            DOWNLOAD_POLICY.rate_limited(exc, exc.url or url, attempt)


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


def compact_preview(image: Path, destination: Path, *, detail=False):
    im=Image.open(image).convert('RGB')
    im.thumbnail((270,480), Image.Resampling.LANCZOS)
    im=im.quantize(colors=24,method=Image.Quantize.MEDIANCUT)
    im.save(destination,format='PNG',optimize=True)
    encoded=base64.b64encode(destination.read_bytes()).decode('ascii')
    destination.with_suffix('.b64').write_text('\n'.join(encoded[i:i+100] for i in range(0,len(encoded),100)),encoding='ascii')
    if detail:
        with Image.open(image) as source:
            detailed = source.convert('RGB')
        detailed.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        for quality in list(range(88, 0, -4)) + [1]:
            buffer = io.BytesIO()
            detailed.save(buffer, format='JPEG', quality=quality, optimize=True)
            if buffer.tell() <= DETAIL_MAX_BYTES:
                destination.with_name(destination.stem + '-detail.jpg').write_bytes(buffer.getvalue())
                break
        else:
            raise ValueError('Full-color detail preview exceeds 900 KiB at the supported quality range')


def silent_video(image: Path, out: Path, seconds: float=18):
    if not 5 <= seconds <= 120:
        raise ValueError('Silent post duration must be 5-120 seconds')
    run(['ffmpeg','-y','-v','error','-loop','1','-framerate','25','-i',str(image),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t',str(seconds),'-vf','scale=1080:1080,pad=1080:1920:0:420:color=0x101A28,setsar=1','-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-movflags','+faststart','-shortest',str(out)])


def music_video(image: Path, out: Path, seconds: float=35):
    if not 5 <= seconds <= 120:
        raise ValueError('Music post duration must be 5-120 seconds')
    fade_out=max(0.0, seconds-1.5)
    filters=('[1:a]volume=0.032[a1];[2:a]volume=0.024[a2];[3:a]volume=0.020[a3];'
        '[a1][a2][a3]amix=inputs=3:duration=longest:normalize=0,highpass=f=90,lowpass=f=1800,'
        'afade=t=in:st=0:d=1.5,'+f'afade=t=out:st={fade_out}:d=1.5,'+'aformat=sample_rates=48000:channel_layouts=stereo[a]')
    run(['ffmpeg','-y','-v','error','-loop','1','-framerate','25','-i',str(image),
        '-f','lavfi','-i',f'sine=frequency=220:sample_rate=48000:duration={seconds}',
        '-f','lavfi','-i',f'sine=frequency=277.18:sample_rate=48000:duration={seconds}',
        '-f','lavfi','-i',f'sine=frequency=329.63:sample_rate=48000:duration={seconds}',
        '-t',str(seconds),'-vf','scale=1080:1080,pad=1080:1920:0:420:color=0x101A28,setsar=1',
        '-filter_complex',filters,'-map','0:v','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','128k','-movflags','+faststart',str(out)])
    meta=probe(out)
    if not any(s['codec_type']=='audio' for s in meta['streams']): raise ValueError('Music output has no audio stream')
    duration=float(meta['format']['duration'])
    if abs(duration-seconds)>.4: raise ValueError(f'Music output duration mismatch {seconds}->{duration}')
    run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'])
    return duration


def _crop_variant(source: Image.Image, idx: int) -> Image.Image:
    centers=[(0.50,0.46),(0.42,0.56),(0.62,0.48),(0.50,0.62)]
    zooms=[1.00,1.16,1.23,1.34]
    w,h=source.size; side=int(min(w,h)/zooms[idx]); cx=int(w*centers[idx][0]); cy=int(h*centers[idx][1])
    left=max(0,min(w-side,cx-side//2)); top=max(0,min(h-side,cy-side//2))
    crop=source.crop((left,top,left+side,top+side)).resize((1080,1080),Image.Resampling.LANCZOS)
    if idx == 2: crop=ImageOps.mirror(crop)
    if idx == 3: crop=ImageEnhance.Contrast(crop).enhance(1.06)
    return crop


def photo_dialogue_card(source: Image.Image, card: dict, idx: int) -> Image.Image:
    im=_crop_variant(source,idx).convert('RGBA'); shade=Image.new('RGBA',im.size,(0,0,0,0)); sd=ImageDraw.Draw(shade)
    sd.rectangle((0,0,1080,150),fill=(8,12,18,170)); sd.rectangle((0,540,1080,1080),fill=(5,8,12,205))
    im=Image.alpha_composite(im,shade).convert('RGB'); d=ImageDraw.Draw(im); d.rectangle((54,40,1026,44),fill='#D8BA78')
    text_block(im,'ΣΚΥΛΟΣ ΜΠΑΡΜΑΝ • Ο ΠΑΡΑΞΕΝΟΣ ΠΕΛΑΤΗΣ',(60,62,1020,132),38,bold=True,center=True,min_size=29)
    text_block(im,'ΠΕΛΑΤΗΣ: '+card['customer'],(64,585,1016,760),46,bold=True,min_size=32)
    text_block(im,'ΜΠΑΡΜΑΝ: '+card['dog'],(64,778,1016,945),43,min_size=30)
    if idx < 3: text_block(im,card.get('tail','→ Και μετά το έκανε ακόμα πιο παράλογο…'),(64,960,1016,1038),27,bold=True,center=True,min_size=22)
    else: text_block(im,CTA,(64,958,1016,1044),26,bold=True,center=True,min_size=21)
    return im


def carousel_music_video(images: list[Path], out: Path, seconds_per_card: float=6.0) -> float:
    if len(images) < 2 or not 3 <= seconds_per_card <= 15: raise ValueError('Carousel video requires 2+ images and 3-15 seconds per card')
    total=len(images)*seconds_per_card; concat=out.with_suffix('.concat.txt'); lines=[]
    for p in images: lines += [f"file '{p.as_posix()}'", f'duration {seconds_per_card}']
    lines += [f"file '{images[-1].as_posix()}'"]; concat.write_text('\n'.join(lines),encoding='utf-8'); fade_out=max(0.0,total-1.5)
    filters=('[1:a]volume=0.030[a1];[2:a]volume=0.022[a2];[3:a]volume=0.018[a3];'
        '[a1][a2][a3]amix=inputs=3:duration=longest:normalize=0,highpass=f=90,lowpass=f=1800,'
        'afade=t=in:st=0:d=1.2,'+f'afade=t=out:st={fade_out}:d=1.5,'+'aformat=sample_rates=48000:channel_layouts=stereo[a]')
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(concat),
        '-f','lavfi','-i',f'sine=frequency=220:sample_rate=48000:duration={total}',
        '-f','lavfi','-i',f'sine=frequency=277.18:sample_rate=48000:duration={total}',
        '-f','lavfi','-i',f'sine=frequency=329.63:sample_rate=48000:duration={total}',
        '-t',str(total),'-vf','fps=25,scale=1080:1080,pad=1080:1920:0:420:color=0x101A28,setsar=1',
        '-filter_complex',filters,'-map','0:v','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','128k','-movflags','+faststart',str(out)])
    concat.unlink(missing_ok=True); meta=probe(out); duration=float(meta['format']['duration'])
    if not any(s['codec_type']=='audio' for s in meta['streams']): raise ValueError('Carousel video has no audio stream')
    if abs(duration-total)>.6: raise ValueError(f'Carousel duration mismatch {total}->{duration}')
    run(['ffmpeg','-v','error','-i',str(out),'-f','null','-']); return duration


def photo_dialogue_carousel(job: dict, work: Path, outdir: Path) -> dict:
    cards=job.get('cards',[])
    if len(cards) != 4: raise ValueError('Dog Bartender carousel must contain exactly four cards')
    src=work/'source.img'; download(job['source_url'],src); source=Image.open(src).convert('RGB'); outputs=[]
    for idx,card in enumerate(cards):
        im=photo_dialogue_card(source,card,idx); p=outdir/f"{job['id']}-{idx+1:02d}.jpg"; im.save(p,quality=95,subsampling=0,optimize=True)
        if im.size != (1080,1080): raise ValueError('Dog card dimensions are not exactly 1080x1080')
        compact_preview(p,outdir/f"{job['id']}-{idx+1:02d}-qa.png"); outputs.append(p)
    video=outdir/f"{job['id']}.mp4"; duration=carousel_music_video(outputs,video,float(job.get('seconds_per_card',6)))
    return {'card_count':4,'card_dimensions':[1080,1080],'jpeg_cards':True,'narration':False,'card_audio':'silent',
        'youtube_music_embedded':True,'music_source':'original_local_synth_no_external_license','final_duration':duration,
        'source_license':job.get('source_license'),'source_author':job.get('source_author'),'same_source_identity':True,
        'visual_variation':'four deterministic photographic crops; one mirrored; varied zoom/emphasis'}


def finish_video(job,work,outdir):
    src=work/'source.mp4';download(job['source_url'],src); meta=probe(src); v=next(s for s in meta['streams'] if s['codec_type']=='video'); length=float(meta['format']['duration'])
    if not 10 <= length <= 240: raise ValueError(f'Unexpected original duration {length}; no cropped/two-second source accepted')
    w,h=int(v['width']),int(v['height'])
    if abs(w/h-9/16)>.03 or w%2 or h%2: raise ValueError('Original must be an even-sized vertical 9:16 video')
    scale=min(1,1080/w,1920/h);w=int(w*scale)//2*2;h=int(h*scale)//2*2; card=work/'cta.png';end_card((w,h)).save(card)
    if not any(s['codec_type']=='audio' for s in meta['streams']): raise ValueError('Expected narrated original with an audio stream')
    out=outdir/(job['id']+'.mp4'); filters=f'[0:v]scale={w}:{h},setsar=1,fps=25,format=yuv420p,setpts=PTS-STARTPTS[v0];[0:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a0];[1:v]setsar=1,fps=25,format=yuv420p,trim=duration=4,setpts=PTS-STARTPTS[v1];[2:a]atrim=duration=4,asetpts=PTS-STARTPTS[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]'
    run(['ffmpeg','-y','-v','error','-i',str(src),'-loop','1','-framerate','25','-i',str(card),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-filter_complex',filters,'-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','22','-threads','2','-c:a','aac','-b:a','128k','-movflags','+faststart',str(out)])
    final=probe(out);dl=float(final['format']['duration'])
    if abs(dl-(length+4))>.3: raise ValueError(f'Duration mismatch {length}->{dl}')
    run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'])
    for label,sec in [('opening',1),('middle',length/2),('ending',dl-2)]:
        preview=outdir/(job['id']+'-'+label+'.jpg'); run(['ffmpeg','-y','-v','error','-ss',str(sec),'-i',str(out),'-frames:v','1','-vf','scale=360:-2',str(preview)]); compact_preview(preview, outdir/(job['id']+'-'+label+'-qa.png'))
    return {'original_duration':length,'final_duration':dl,'width':w,'height':h,'original_narration_preserved':True,'new_spoken_cta':False,'written_cta_appended':True,'decode_passed':True,'subtitle_review':'original_pixels_preserved; human_visual_review_required'}


def main():
    global DOWNLOAD_POLICY
    DOWNLOAD_POLICY = DownloadPolicy()
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--output',required=True);ns=ap.parse_args(); raw=Path(ns.manifest).read_bytes();batch=json.loads(raw)
    if batch.get('approved') is not True or batch.get('paid_generation_allowed') is not False: raise ValueError('Explicit approval and no-paid-generation flags are required')
    jobs=batch['jobs'];ids=[x['id'] for x in jobs]
    if len(jobs)>60 or len(ids)!=len(set(ids)) or any(not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,80}',s) for s in ids): raise ValueError('Invalid, duplicate or too many jobs')
    key=hashlib.sha256(raw).hexdigest()[:16];output=Path(ns.output)/key;output.mkdir(parents=True,exist_ok=True); report={'batch_sha256':hashlib.sha256(raw).hexdigest(),'batch_id':key,'paid_ai_credits_used':0,'jobs':[]}; (output/'source_manifest.json').write_bytes(raw)
    for job in jobs:
        record={'id':job['id'],'mode':job['mode'],'status':'failed','source_url':job.get('source_url'),'attribution':job.get('attribution'),'title':job.get('title'),'text':job.get('text')}
        event_start = len(DOWNLOAD_POLICY.events)
        try:
            with tempfile.TemporaryDirectory() as td:
                work=Path(td)
                if job['mode']=='video_cta': record.update(finish_video(job,work,output))
                elif job['mode'] in ('simple_post','image_cta'):
                    im=simple_image(job) if job['mode']=='simple_post' else image_cta(job,work); jpg=output/(job['id']+'.jpg');im.save(jpg,quality=94,subsampling=0); compact_preview(jpg,output/(job['id']+'-qa.png'))
                    if job.get('music_copy',False):
                        vid=output/(job['id']+'.mp4');record['final_duration']=music_video(jpg,vid,float(job.get('seconds',35))); record.update({'music_embedded':True,'music_source':'original_local_synth_no_external_license'})
                    elif job.get('youtube_copy',False):
                        vid=output/(job['id']+'.mp4');silent_video(jpg,vid,float(job.get('seconds',18))); record['final_duration']=float(probe(vid)['format']['duration'])
                    record.update({'written_cta':True,'narration':False,'image_size':[1080,1080]})
                elif job['mode']=='image_music_video':
                    src=work/'source.img';download(job['source_url'],src); im=Image.open(src).convert('RGB'); source_jpg=work/'source.jpg';im.save(source_jpg,quality=96,subsampling=0); compact_preview(source_jpg,output/(job['id']+'-qa.png')); vid=output/(job['id']+'.mp4'); record['final_duration']=music_video(source_jpg,vid,float(job.get('seconds',35))); record.update({'music_embedded':True,'music_source':'original_local_synth_no_external_license','narration':False,'source_visual_preserved':True})
                elif job['mode']=='image_jpeg_copy':
                    source=work/'source.img';download(job['source_url'],source); im=Image.open(source).convert('RGB'); jpg=output/(job['id']+'.jpg');im.save(jpg,quality=96,subsampling=0); compact_preview(jpg,output/(job['id']+'-qa.png'),detail=job.get('detail_preview') is True); record.update({'source_visual_preserved':True,'narration':False,'image_size':[im.width,im.height]})
                elif job['mode']=='photo_dialogue_carousel': record.update(photo_dialogue_carousel(job,work,output))
                elif job['mode']=='preview':
                    source=work/'source.img';download(job['source_url'],source)
                    expected = job.get('expected_source_sha256')
                    if expected is not None:
                        actual = digest(source)
                        if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected) or actual != expected:
                            raise ValueError('Preview source SHA256 does not match the expected exact bytes')
                        record['verified_source_sha256'] = actual
                    compact_preview(source,output/(job['id']+'.png'),detail=job.get('detail_preview') is True)
                else: raise ValueError('Unknown job mode')
            record['status']='rendered'; record['files']=[{'name':p.name,'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(output.glob(job['id']+'*')) if p.suffix != '.b64' and not p.name.endswith('.concat.txt')]
            if any(f['bytes']>MAX_OUTPUT for f in record['files']): raise ValueError('Output exceeds the 64 MiB repository safety limit')
        except Exception as exc:
            record['status']='failed';record['error']=str(exc)[:1800]
            if isinstance(exc, RateLimitedBatch):
                record['source_request_policy'] = DOWNLOAD_POLICY.stop_reason
            for p in output.glob(job['id']+'*'):p.unlink()
        record['download_events'] = DOWNLOAD_POLICY.events[event_start:]
        report['jobs'].append(record); print(json.dumps({'id':record['id'],'status':record['status'],'error':record.get('error')},ensure_ascii=False),flush=True)
    report['download_policy'] = {'wikimedia_minimum_interval_seconds': WIKIMEDIA_INTERVAL,
        'default_429_cooldown_seconds': DEFAULT_429_COOLDOWN, 'maximum_retry_after_seconds': MAX_RETRY_AFTER,
        'maximum_retries': 1, 'batch_429_count': DOWNLOAD_POLICY.rate_limits,
        'source_requests_stopped': DOWNLOAD_POLICY.stop_reason is not None,
        'stop_reason': DOWNLOAD_POLICY.stop_reason, 'events': DOWNLOAD_POLICY.events}
    (output/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); (output/'summary.json').write_text(json.dumps({'batch_id':key,'paid_ai_credits_used':0,'jobs':[{k:r.get(k) for k in ['id','status','card_count','final_duration','music_embedded','youtube_music_embedded','error']} for r in report['jobs']]},ensure_ascii=False,indent=2),encoding='utf-8'); print('REPORT_PATH='+str(output/'manifest.json'))

if __name__=='__main__': main()
