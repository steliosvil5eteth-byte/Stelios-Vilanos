#!/usr/bin/env python3
"""Finish one approved narrator-only legend. No generation or publishing calls.
Downloads the returned source and SRT, burns readable captions, validates full
length and exports real frame samples. Original narration is preserved.
"""
from __future__ import annotations
import hashlib,json,os,re,shutil,subprocess,urllib.parse,urllib.request,unicodedata
from pathlib import Path

ROOT=Path(os.environ['OUTPUT_DIR'])/'legend-20260920-flying-dutchman-final'
ROOT.mkdir(parents=True,exist_ok=True)
JOB=json.loads(Path('media_jobs/legend-20260920-final.json').read_text())
if JOB.get('approved') is not True or JOB.get('paid_generation_allowed') is not False:
    raise ValueError('This technical finishing job requires approved/no-generation flags')
if JOB.get('key')!='2026-09-20:legend:flying-dutchman':
    raise ValueError('Unexpected publishing identity')
HOSTS={'files2.heygen.ai','files.heygen.ai','resource2.heygen.ai','static.heygen.ai'}

def check(url):
    p=urllib.parse.urlsplit(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):
        raise ValueError('Unexpected media URL')
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        check(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def download(url,dest,limit):
    check(url)
    req=urllib.request.Request(url,headers={'User-Agent':'SteliosLegendTechnicalQA/1.0'})
    with urllib.request.build_opener(Redirect()).open(req,timeout=120) as r,dest.open('wb') as f:
        check(r.url);total=0
        for b in iter(lambda:r.read(1024*1024),b''):
            total+=len(b)
            if total>limit:raise ValueError('Media exceeds declared safety limit')
            f.write(b)
    if not total:raise ValueError('Empty input')

def run(args):
    result=subprocess.run(args,capture_output=True,text=True,timeout=600)
    if result.returncode:raise RuntimeError(result.stderr[-3000:])
    return result.stdout,result.stderr

def probe(path):
    return json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)])[0])

def normalized(text):
    return ' '.join(re.sub(r'[^\w\s]',' ',unicodedata.normalize('NFC',text).lower()).split())

def stamp(value):
    h,m,s=value.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)

source=ROOT/'source.mp4';srt=ROOT/'subtitles.srt'
download(JOB['source_video_url'],source,150*1024*1024)
download(JOB['subtitle_url'],srt,1024*1024)
meta=probe(source);length=float(meta['format']['duration'])
expected=float(JOB['expected_duration'])
if not 45<=length<=210 or abs(length-expected)>.5:
    raise ValueError('Unexpected full video duration; cropped two-second inputs rejected')
video=next(x for x in meta['streams'] if x['codec_type']=='video')
if abs(video['width']/video['height']-9/16)>.02 or video['width']<720:
    raise ValueError('Unexpected canvas')
if not any(x['codec_type']=='audio' for x in meta['streams']):
    raise ValueError('Narration audio is missing')
text=srt.read_text(encoding='utf-8-sig')
blocks=re.split(r'\n\s*\n',text.strip());caption_text=[];last_end=0;count=0
for block in blocks:
    lines=block.strip().splitlines()
    match=next((i for i,x in enumerate(lines) if '-->' in x),None)
    if match is None:continue
    times=lines[match].split('-->')
    start=stamp(times[0].strip());end=stamp(times[1].strip().split()[0])
    if start<0 or end<=start or end>length+.5:
        raise ValueError('Invalid subtitle timestamps')
    last_end=max(last_end,end);caption_text.extend(lines[match+1:]);count+=1
plain=re.sub(r'<[^>]+>','', ' '.join(caption_text))
expected_words=normalized(' '.join(JOB['scripts'])).split();actual_words=normalized(plain).split()
from difflib import SequenceMatcher
coverage=SequenceMatcher(None,expected_words,actual_words,autojunk=False).ratio()
if coverage<.88 or count<15 or last_end<length-12:
    raise ValueError('Missing or materially mismatched full narration subtitles')
cta='Αν σας άρεσε, ακολουθήστε για περισσότερα.'
if normalized(cta) not in normalized(plain):raise ValueError('Spoken CTA absent from subtitles')
final=ROOT/'flying-dutchman-20260920.mp4'
# Use the original, uncaptioned full render, not the provider captioned copy.
# Caption baseline is above the art attribution footer, leaving Greek text legible.
style='FontName=DejaVu Sans,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,Outline=1.5,Shadow=0.5,Alignment=2,MarginL=25,MarginR=25,MarginV=58'
filter_value="subtitles='"+str(srt).replace("'", "\\'")+"':original_size=1080x1920:force_style='"+style+"'"
run(['ffmpeg','-y','-v','error','-i',str(source),'-vf',filter_value,'-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(final)])
fin=probe(final);final_length=float(fin['format']['duration'])
if abs(final_length-length)>.12:raise ValueError('Finishing changed full duration')
run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'])
_,levels=run(['ffmpeg','-hide_banner','-i',str(final),'-af','volumedetect','-vn','-sn','-dn','-f','null','-'])
if final.stat().st_size>64*1024*1024:raise ValueError('Final video exceeds publication storage limit')
previews=ROOT/'qa';previews.mkdir()
seconds=sorted(set([1,4]+[round(length*f,2) for f in [.10,.18,.26,.34,.42,.50,.58,.66,.74,.82,.90]]+[max(1,length-10),max(1,length-5),length-1]))
for i,sec in enumerate(seconds,1):
    run(['ffmpeg','-y','-v','error','-ss',str(sec),'-i',str(final),'-frames:v','1','-vf','scale=540:-2',str(previews/f'frame-{i:02d}.jpg')])
report={'key':JOB['key'],'heygen_video_id':JOB['heygen_video_id'],'source_duration':length,'final_duration':final_length,'width':video['width'],'height':video['height'],'caption_count':count,'caption_script_similarity':coverage,'last_caption_end':last_end,'audio_preserved_stream_copy':True,'audio_levels':levels[-1500:],'burned_in_captions':True,'spoken_cta_in_transcript':True,'full_decode_passed':True,'visual_review_required':True,'paid_generation_calls':0,'publishing_calls':0,'final_file':final.name,'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'bytes':final.stat().st_size,'preview_seconds':seconds}
(ROOT/'qa-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
# Keep the original as a review artifact; publication branch receives only final/SRT/report/previews.
print(json.dumps(report,ensure_ascii=False,indent=2))
