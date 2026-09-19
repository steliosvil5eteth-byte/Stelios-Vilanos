#!/usr/bin/env python3
"""Finish one approved full-length legend without generation or publishing APIs."""
from __future__ import annotations
import hashlib,json,os,re,subprocess,urllib.parse,urllib.request,unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from PIL import ImageFont
ROOT=Path(os.environ['OUTPUT_DIR'])/'legend-20260920-flying-dutchman-final'
ROOT.mkdir(parents=True,exist_ok=True)
JOB=json.loads(Path('media_jobs/legend-20260920-final.json').read_text())
if JOB.get('approved') is not True or JOB.get('paid_generation_allowed') is not False or JOB.get('key')!='2026-09-20:legend:flying-dutchman':
    raise ValueError('Only the approved non-generation legend finishing job is accepted')
HOSTS={'files2.heygen.ai','files.heygen.ai','resource2.heygen.ai','static.heygen.ai'}
def check(url):
    p=urllib.parse.urlsplit(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):raise ValueError('Unexpected media URL')
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
            if total>limit:raise ValueError('Oversize media')
            f.write(b)
    if not total:raise ValueError('Empty media')
def run(args):
    r=subprocess.run(args,capture_output=True,text=True,timeout=600)
    if r.returncode:raise RuntimeError(r.stderr[-3000:])
    return r.stdout,r.stderr
def probe(p):return json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)])[0])
def normalized(t):return ' '.join(re.sub(r'[^\w\s]',' ',unicodedata.normalize('NFC',t).lower()).split())
def stamp(t):
    h,m,s=t.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)
def ass_time(t):
    cs=round(t*100);h,cs=divmod(cs,360000);m,cs=divmod(cs,6000);s,cs=divmod(cs,100)
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'
source=ROOT/'source.mp4';srt=ROOT/'subtitles.srt'
download(JOB['source_video_url'],source,150*1024*1024)
download(JOB['subtitle_url'],srt,1024*1024)
meta=probe(source);length=float(meta['format']['duration']);expected=float(JOB['expected_duration'])
if not 45<=length<=210 or abs(length-expected)>.5:raise ValueError('Unexpected full duration; two-second clips rejected')
v=next(x for x in meta['streams'] if x['codec_type']=='video')
if abs(v['width']/v['height']-9/16)>.02 or v['width']<720:raise ValueError('Unexpected canvas')
if not any(x['codec_type']=='audio' for x in meta['streams']):raise ValueError('Missing narration')
text=srt.read_text(encoding='utf-8-sig');entries=[]
for block in re.split(r'\n\s*\n',text.strip()):
    lines=block.strip().splitlines();i=next((n for n,x in enumerate(lines) if '-->' in x),None)
    if i is None:continue
    times=lines[i].split('-->');start=stamp(times[0].strip());end=stamp(times[1].strip().split()[0])
    if start<0 or end<=start or end>length+.5:raise ValueError('Invalid caption timestamps')
    words=re.sub(r'<[^>]+>','', ' '.join(lines[i+1:])).strip()
    entries.append((start,end,words))
plain=' '.join(x[2] for x in entries);coverage=SequenceMatcher(None,normalized(' '.join(JOB['scripts'])).split(),normalized(plain).split(),autojunk=False).ratio()
last_end=max((x[1] for x in entries),default=0)
if coverage<.88 or len(entries)<15 or last_end<length-12:raise ValueError('Incomplete or materially mismatched subtitles')
cta='Αν σας άρεσε, ακολουθήστε για περισσότερα.'
if normalized(cta) not in normalized(plain):raise ValueError('Spoken CTA absent from transcript')
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',52)
def wrapped(t):
    lines=[];line=''
    for word in t.split():
        candidate=(line+' '+word).strip()
        if font.getlength(candidate)>930 and line:lines.append(line);line=word
        else:line=candidate
    if line:lines.append(line)
    return lines
ass=ROOT/'subtitles.ass'
header='[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Default,DejaVu Sans,52,&H00FFFFFF,&H00FFFFFF,&H00101010,&H60000000,-1,0,0,0,100,100,0,0,1,3,1,2,70,70,315,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n'
events=[]
for start,end,t in entries:
    ls=wrapped(t)
    if len(ls)>3:raise ValueError('Subtitle too long for safe display')
    escaped=[x.replace('\\','').replace('{','').replace('}','') for x in ls]
    body='\\N'.join(escaped)
    events.append(f'Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{body}')
ass.write_text(header+'\n'.join(events)+'\n',encoding='utf-8')
final=ROOT/'flying-dutchman-20260920.mp4'
run(['ffmpeg','-y','-v','error','-i',str(source),'-vf','ass='+str(ass),'-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(final)])
fm=probe(final);final_length=float(fm['format']['duration'])
if abs(final_length-length)>.12:raise ValueError('Finishing changed full duration')
run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'])
_,levels=run(['ffmpeg','-hide_banner','-i',str(final),'-af','volumedetect','-vn','-sn','-dn','-f','null','-'])
if final.stat().st_size>64*1024*1024:raise ValueError('Final too large for publication storage')
previews=ROOT/'qa';previews.mkdir()
seconds=sorted(set([1,4]+[round(length*f,2) for f in [.10,.18,.26,.34,.42,.50,.58,.66,.74,.82,.90]]+[max(1,length-10),max(1,length-5),length-1]))
for i,sec in enumerate(seconds,1):
    run(['ffmpeg','-y','-v','error','-ss',str(sec),'-i',str(final),'-frames:v','1','-vf','scale=540:-2',str(previews/f'frame-{i:02d}.jpg')])
run(['ffmpeg','-y','-v','error','-ss','4','-i',str(source),'-frames:v','1','-vf','scale=540:-2',str(previews/'original-at-4s.jpg')])
report={'key':JOB['key'],'heygen_video_id':JOB['heygen_video_id'],'source_duration':length,'final_duration':final_length,'width':v['width'],'height':v['height'],'caption_count':len(entries),'caption_script_similarity':coverage,'last_caption_end':last_end,'audio_preserved_stream_copy':True,'audio_levels':levels[-1500:],'burned_in_captions':True,'spoken_cta_in_transcript':True,'full_decode_passed':True,'visual_review_required':True,'paid_generation_calls':0,'publishing_calls':0,'final_file':final.name,'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'bytes':final.stat().st_size,'preview_seconds':seconds}
(ROOT/'qa-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
