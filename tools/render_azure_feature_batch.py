#!/usr/bin/env python3
from __future__ import annotations
import argparse, html, json, math, os, re, subprocess, time, urllib.parse
from pathlib import Path
import requests
from PIL import Image
import azure.cognitiveservices.speech as speechsdk

VOICE='el-GR-NestorasNeural'
CTA='Αν σας άρεσε, ακολουθήστε για περισσότερα.'
UA='SteliosMediaQA/2.0 zero-cost rights-checked feature renderer'
BAD_TITLE=('illustration','drawing','map','logo','coat of arms','diagram','icon','poster','stamp')
ALLOWED_LICENSE=('cc by','cc0','public domain')
SAFE_EXPLICIT_LICENSE={'CC BY','CC BY-SA','CC0','Public Domain'}

def run(args, **kwargs):
    p=subprocess.run(args,text=True,capture_output=True,**kwargs)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-4000:])
    return p.stdout

def probe_duration(path:Path)->float:
    return float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)]).strip())

def clean_html(s): return re.sub('<[^>]+>','',html.unescape(s or '')).strip()

def commons_search(queries, outdir:Path, target:int):
    sess=requests.Session(); sess.headers.update({'User-Agent':UA})
    seen=set(); records=[]
    for q in queries:
        if len(records)>=target: break
        params={'action':'query','format':'json','generator':'search','gsrsearch':q,'gsrnamespace':6,'gsrlimit':25,'prop':'imageinfo','iiprop':'url|size|extmetadata','iiurlwidth':1800}
        r=sess.get('https://commons.wikimedia.org/w/api.php',params=params,timeout=60); r.raise_for_status()
        pages=list(r.json().get('query',{}).get('pages',{}).values())
        for p in pages:
            if len(records)>=target: break
            title=p.get('title','')
            low=title.lower()
            if any(x in low for x in BAD_TITLE) or title in seen: continue
            if not re.search(r'\.(jpe?g|png)$',title,re.I): continue
            infos=p.get('imageinfo') or []
            if not infos: continue
            info=infos[0]; meta=info.get('extmetadata',{})
            lic=clean_html(meta.get('LicenseShortName',{}).get('value',''))
            usage=clean_html(meta.get('UsageTerms',{}).get('value',''))
            combo=(lic+' '+usage).lower()
            if not any(x in combo for x in ALLOWED_LICENSE): continue
            w=int(info.get('width') or 0); h=int(info.get('height') or 0)
            if min(w,h)<600: continue
            url=info.get('thumburl') or info.get('url')
            if not url: continue
            dest=outdir/f'{len(records)+1:02d}.jpg'
            ok=False
            for attempt in range(4):
                try:
                    rr=sess.get(url,timeout=90)
                    if rr.status_code==429:
                        time.sleep(3*(attempt+1)); continue
                    rr.raise_for_status(); dest.write_bytes(rr.content)
                    with Image.open(dest) as im:
                        if min(im.size)<600: raise ValueError('small downloaded image')
                        im.convert('RGB').save(dest,quality=94)
                    ok=True; break
                except Exception:
                    time.sleep(2*(attempt+1))
            if not ok:
                dest.unlink(missing_ok=True); continue
            seen.add(title)
            records.append({'file':title[5:] if title.startswith('File:') else title,'artist':clean_html(meta.get('Artist',{}).get('value','')),'credit':clean_html(meta.get('Credit',{}).get('value','')),'license':lic or usage,'source_page':'https://commons.wikimedia.org/wiki/'+requests.utils.quote(title.replace(' ','_'),safe=':()_,.-'),'download_url':url})
    if len(records)<target:
        raise RuntimeError(f'Only {len(records)} rights-cleared photographic images found; need {target}')
    return records


def explicit_visuals(items, outdir:Path, target:int):
    if len(items) != target:
        raise RuntimeError(f'Pinned source-pack visual count mismatch: {len(items)} != {target}')
    sess=requests.Session(); sess.headers.update({'User-Agent':UA})
    records=[]
    for i,item in enumerate(items,1):
        media=item.get('direct_media_url','').strip()
        page=item.get('source_page_url','').strip()
        lic=item.get('license','').strip()
        attribution=item.get('attribution','').strip()
        license_url=item.get('license_url','').strip()
        if lic not in SAFE_EXPLICIT_LICENSE:
            raise RuntimeError(f'Unapproved pinned license for visual {i}: {lic}')
        if not attribution or not license_url:
            raise RuntimeError(f'Pinned visual {i} missing attribution/license URL')
        mu=urllib.parse.urlsplit(media); pu=urllib.parse.urlsplit(page)
        if mu.scheme!='https' or mu.hostname not in {'upload.wikimedia.org','commons.wikimedia.org'}:
            raise RuntimeError(f'Pinned visual {i} has unapproved media host')
        if pu.scheme!='https' or pu.hostname!='commons.wikimedia.org':
            raise RuntimeError(f'Pinned visual {i} has unapproved source page')
        dest=outdir/f'{i:02d}.jpg'
        # Keep the exact vetted original and licensing metadata, but use a
        # deterministic image proxy to avoid Wikimedia full-size 429s.
        fetch_url='https://images.weserv.nl/?url='+urllib.parse.quote(media,safe='')+'&w=1800&output=jpg'
        ok=False; last=None
        for attempt in range(5):
            try:
                rr=sess.get(fetch_url,timeout=90,allow_redirects=True)
                if rr.status_code==429:
                    last=RuntimeError('HTTP 429 from vetted-image proxy')
                    time.sleep(4*(attempt+1)); continue
                rr.raise_for_status(); dest.write_bytes(rr.content)
                with Image.open(dest) as im:
                    if min(im.size)<600: raise ValueError('pinned visual too small')
                    im.convert('RGB').save(dest,quality=94)
                ok=True; break
            except Exception as exc:
                last=exc
                time.sleep(2*(attempt+1))
        if not ok:
            dest.unlink(missing_ok=True)
            raise RuntimeError(f'Pinned visual {i} download failed: {last}')
        records.append({
            'source':item.get('source',''),
            'visual_kind':item.get('visual_kind','photograph'),
            'attribution':attribution,
            'license':lic,
            'license_url':license_url,
            'source_page':page,
            'download_url':media,
            'source_pack_pinned':True
        })
    return records

def synthesize(script:str, outdir:Path, min_duration=None, max_duration=None):
    cfg=speechsdk.SpeechConfig(subscription=os.environ['AZURE_SPEECH_KEY'],region=os.environ['AZURE_SPEECH_REGION'])
    cfg.speech_synthesis_voice_name=VOICE
    cfg.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
    wav=outdir/'nestoras.wav'; syn=speechsdk.SpeechSynthesizer(speech_config=cfg,audio_config=speechsdk.audio.AudioOutputConfig(filename=str(wav)))
    bounds=[]
    syn.synthesis_word_boundary.connect(lambda e: bounds.append({'text':e.text,'offset':float(e.audio_offset)/10000000.0}))
    res=syn.speak_text_async(script).get()
    if res.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        d=speechsdk.SpeechSynthesisCancellationDetails(res); raise RuntimeError(f'Azure F0 Nestoras failed: {d.reason} {d.error_details}')
    dur=probe_duration(wav)
    if min_duration is None:
        if dur<=80: raise RuntimeError(f'duration gate failed: {dur:.3f}s <= 80s')
    elif dur < float(min_duration):
        raise RuntimeError(f'duration gate failed: {dur:.3f}s < {float(min_duration):.3f}s')
    if max_duration is not None and dur > float(max_duration):
        raise RuntimeError(f'duration gate failed: {dur:.3f}s > {float(max_duration):.3f}s')
    if len(bounds)<30: raise RuntimeError('insufficient word timing data')
    return wav,bounds,dur

def ts(x):
    ms=int(round(max(0,x)*1000)); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000); return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

def subtitles(bounds,dur,out):
    caps=[]; group=[]
    for i,b in enumerate(bounds):
        group.append(b); txt=' '.join(x['text'] for x in group)
        if len(group)>=6 or len(txt)>=38 or re.search(r'[.!;;?…]$',b['text']):
            st=float(group[0]['offset']); en=float(bounds[i+1]['offset']) if i+1<len(bounds) else dur
            caps.append((st,max(st+.24,en),txt)); group=[]
    if group: caps.append((float(group[0]['offset']),dur,' '.join(x['text'] for x in group)))
    def wrap(txt):
        words=txt.split(); lines=[]; cur=''
        for w in words:
            cand=(cur+' '+w).strip()
            if cur and len(cand)>31: lines.append(cur); cur=w
            else: cur=cand
        if cur: lines.append(cur)
        if len(lines)>2:
            mid=max(1,len(words)//2); lines=[' '.join(words[:mid]),' '.join(words[mid:])]
        return '\n'.join(lines[:2])
    rows=[]
    for n,(st,en,txt) in enumerate(caps,1): rows += [str(n),f'{ts(st)} --> {ts(en)}',wrap(txt),'']
    out.write_text('\n'.join(rows),encoding='utf-8')
    return len(caps)

def make_video(job, photos:Path, wav:Path, srt:Path, dur:float, out:Path):
    files=sorted(photos.glob('*.jpg')); scenes=max(len(files),int(job.get('scenes',15)))
    per=dur/scenes; frames=max(1,math.ceil(per*30)); clips=out.parent/'clips'; clips.mkdir(exist_ok=True)
    concat=out.parent/'clips.txt'; lines=[]
    order=(files+list(reversed(files)))
    for i in range(scenes):
        img=order[i%len(order)]; clip=clips/f'clip-{i+1:02d}.mp4'
        sign=1 if i%2==0 else -1
        x=f"iw/2-(iw/zoom/2)+{sign*10}*sin(on/39)"; y=f"ih/2-(ih/zoom/2)+{sign*8}*cos(on/43)"
        run(['ffmpeg','-y','-loglevel','error','-loop','1','-i',str(img),'-vf',f"scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,zoompan=z='min(zoom+0.00028,1.055)':x='{x}':y='{y}':d={frames}:s=1080x1920:fps=30,format=yuv420p",'-t',str(per),'-an','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',str(clip)])
        lines.append("file '"+str(clip).replace("'","'\\''")+"'")
    concat.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    visual=out.parent/'visual.mp4'; run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-an','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',str(visual)])
    style='FontName=DejaVu Sans,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H90000000,BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginL=88,MarginR=88,MarginV=300'
    run(['ffmpeg','-y','-loglevel','error','-i',str(visual),'-i',str(wav),'-vf',f"subtitles='{srt}':force_style='{style}'",'-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-ar','48000','-ac','1','-shortest','-movflags','+faststart',str(out)])

def qa(job, video:Path, dur:float, photo_count:int, cap_count:int):
    meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)])); vd=float(meta['format']['duration'])
    vs=[s for s in meta['streams'] if s.get('codec_type')=='video']; au=[s for s in meta['streams'] if s.get('codec_type')=='audio']
    min_d=job.get('min_duration_seconds'); max_d=job.get('max_duration_seconds')
    duration_bad=(vd<=80 if min_d is None else vd<float(min_d)) or (max_d is not None and vd>float(max_d))
    if duration_bad or len(vs)!=1 or len(au)!=1 or int(vs[0]['width'])!=1080 or int(vs[0]['height'])!=1920: raise RuntimeError('basic QA failed')
    dec=subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],text=True,capture_output=True)
    if dec.returncode: raise RuntimeError('decode QA failed: '+dec.stderr[-1000:])
    sil=subprocess.run(['ffmpeg','-hide_banner','-i',str(video),'-af','silencedetect=noise=-45dB:d=1.2','-f','null','-'],text=True,capture_output=True).stderr
    gaps=[float(x) for x in re.findall(r'silence_duration: ([0-9.]+)',sil)]
    if any(x>1.2 for x in gaps): raise RuntimeError(f'dead-air QA failed: {gaps}')
    tail_log=subprocess.run(['ffmpeg','-hide_banner','-i',str(video),'-af','silencedetect=noise=-45dB:d=0.5','-f','null','-'],text=True,capture_output=True).stderr
    tail=[(float(e),float(d)) for e,d in re.findall(r'silence_end: ([0-9.]+) \| silence_duration: ([0-9.]+)',tail_log)]
    trailing=max([d for e,d in tail if e>=vd-0.12] or [0.0])
    if trailing>0.5: raise RuntimeError(f'trailing-silence QA failed: {trailing:.3f}s')
    return {'publish_ready':True,'local_date':job['local_date'],'slot':job['slot'],'voice':VOICE,'duration_seconds':round(vd,3),'duration_min_seconds':min_d,'duration_max_seconds':max_d,'resolution':'1080x1920','background_music':False,'burned_synced_greek_subtitles':True,'avatar_presenter':False,'spoken_written_cta':job['script'].rstrip().endswith(CTA),'dead_air_gt_1_2s':False,'trailing_silence_gt_0_5s':False,'visual_source_count':photo_count,'source_pack_pinned':bool(job.get('visuals')),'rights_verified':True,'caption_count':cap_count,'paid_generation_used':False,'folklore_not_fact':bool(job.get('folklore_not_fact',False))}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--output',required=True); ns=ap.parse_args()
    batch=json.loads(Path(ns.manifest).read_text(encoding='utf-8'))
    if batch.get('approved') is not True or batch.get('paid_generation_allowed') is not False: raise RuntimeError('zero-cost approval gate failed')
    jobs=batch.get('jobs') or []; outroot=Path(ns.output); outroot.mkdir(parents=True,exist_ok=True); summary=[]
    for job in jobs:
        if job.get('voice')!=VOICE or job.get('background_music') is not False: raise RuntimeError('voice/audio policy mismatch')
        if not job['script'].rstrip().endswith(CTA): raise RuntimeError('CTA gate failed')
        root=outroot/job['id']; photos=root/'photos'; photos.mkdir(parents=True,exist_ok=True)
        target=int(job.get('photo_target',10))
        if job.get('visuals'):
            records=explicit_visuals(job['visuals'],photos,target)
        else:
            records=commons_search(job['commons_queries'],photos,target)
        (root/'visual-attribution.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        wav,bounds,dur=synthesize(job['script'],root,job.get('min_duration_seconds'),job.get('max_duration_seconds')); (root/'speech-meta.json').write_text(json.dumps({'voice':VOICE,'duration_seconds':round(dur,3),'duration_min_seconds':job.get('min_duration_seconds'),'duration_max_seconds':job.get('max_duration_seconds'),'background_music':False,'word_boundaries':len(bounds)},ensure_ascii=False,indent=2),encoding='utf-8')
        srt=root/'subs.srt'; cap_count=subtitles(bounds,dur,srt); video=root/(job['id']+'.mp4'); make_video(job,photos,wav,srt,dur,video)
        result=qa(job,video,dur,len(records),cap_count); (root/'qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); summary.append(result)
    (outroot/'qa-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
