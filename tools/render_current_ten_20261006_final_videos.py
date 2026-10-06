#!/usr/bin/env python3
"""Create exact final narrated files from hash-bound audio and reviewed sources."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import subprocess
import unicodedata
import wave
from pathlib import Path
import numpy as np
from scipy.signal import correlate
from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE = Path(__file__).resolve().parent
MANIFEST = BASE / 'commit_files/media_jobs/current_ten_20261006_narrated.json'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
PLANS = {
    'singing-dunes': [(1,''),(2,'Το φαινόμενο λέγεται'),(3,'Το 2006'),(4,'Η έκπληξη ήταν'),(5,'Σε μεταγενέστερη μελέτη'),(6,'Σκέψου την εικόνα')],
    'ikea-effect': [(1,''),(2,'Το 2012'),(3,'Οι συμμετέχοντες'),(4,'Μερικοί δημιουργοί'),(5,'Υπήρχε όμως'),(7,'Μια δεύτερη'),(8,'Αυτά είναι ευρήματα'),(6,'Μας δίνουν, πάντως')],
    'tsukumogami': [(1,''),(2,'Σκέψου μια αποθήκη'),(3,'Οι άνθρωποι τα φρόντιζαν'),(4,'Το Δημοτικό Μουσείο'),(5,'Η όψη τους'),(6,'Μια σημερινή')],
    'prespes': [(2,''),(1,'Την πρώτη μέρα'),(3,'Ανάμεσα στα σημαντικότερα'),(4,'Συνεχίζουμε προς'),(5,'Για επίσκεψη στο εσωτερικό'),(6,'Τη δεύτερη μέρα'),(7,'Από εδώ ξεκινούν'),(8,'Αυτό το διήμερο')],
}

def run(args, binary=False):
    process = subprocess.run(args, capture_output=True, text=not binary)
    if process.returncode:
        stderr = process.stderr.decode(errors='replace') if binary else process.stderr
        raise RuntimeError(stderr[-5000:])
    return process.stdout

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def words(text):
    text = ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if not unicodedata.combining(c))
    return re.findall(r'[^\W_]+', text.replace('ς','σ'), re.UNICODE)

def read_probe(path):
    return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))

def parse_time(text):
    h,m,s = text.replace(',','.').split(':');return 3600*int(h)+60*int(m)+float(s)

def ass_time(seconds):
    cs = round(seconds*100);h,cs=divmod(cs,360000);m,cs=divmod(cs,6000);s,cs=divmod(cs,100)
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'

def make_ass(srt, script, output):
    font = ImageFont.truetype(FONT,54)
    cues=[]
    for block in srt.read_text(encoding='utf-8').strip().split('\n\n'):
        lines=block.splitlines();st,en=map(parse_time,lines[1].split(' --> '));text=' '.join(lines[2:]).strip()
        if not words(text):
            if not cues:raise RuntimeError('Leading punctuation-only subtitle')
            cues[-1]['text']+=text;cues[-1]['lines'][-1]+=text;cues[-1]['end']=en
            if max(font.getlength(line) for line in cues[-1]['lines'])>890:raise RuntimeError('Attached punctuation exceeds subtitle width')
            continue
        token=text.split(); possibilities=[]
        if font.getlength(text)<=890:possibilities.append([text])
        for i in range(1,len(token)):
            split=[' '.join(token[:i]),' '.join(token[i:])]
            if max(font.getlength(x) for x in split)<=890:possibilities.append(split)
        if not possibilities:raise RuntimeError('Subtitle does not fit safe width: '+text)
        lines=min(possibilities,key=lambda z:(len(z),max(font.getlength(t) for t in z)-min(font.getlength(t) for t in z)))
        cues.append({'start':st,'end':en,'text':text,'lines':lines})
    if words(' '.join(c['text'] for c in cues)) != words(script):
        raise RuntimeError('Subtitles do not preserve every approved script word')
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,54,&H00FFFFFF,&H000000FF,&H00101010,&H90000000,-1,0,0,0,100,100,0,0,1,3,1,2,90,100,345,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    rows=[header]
    for c in cues:
        text='\\N'.join(c['lines']).replace('{','').replace('}','')
        rows.append(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Default,,0,0,0,,{text}")
    output.write_text('\n'.join(rows)+'\n',encoding='utf-8')
    return cues

def scene_timing(plan,boundaries,duration,exact_edges=None):
    tokens=[]
    for bound in boundaries:
        tokens.extend((w,float(bound['offset'])) for w in words(bound['text']))
    seq=[x[0] for x in tokens];original=[];last=0
    for number,(source,anchor) in enumerate(plan):
        if not anchor:original.append(0.0);continue
        target=words(anchor)
        matches=[i for i in range(last,len(seq)-len(target)+1) if seq[i:i+len(target)]==target]
        if not matches:raise RuntimeError('No spoken scene anchor: '+anchor)
        last=matches[0];original.append(tokens[last][1])
    starts=original.copy()
    for i in range(1,len(starts)):starts[i]=max(starts[i],starts[i-1]+7.0)
    starts.append(duration)
    for i in range(len(plan)-1,0,-1):starts[i]=min(starts[i],starts[i+1]-7.0)
    if exact_edges is not None:starts=[*exact_edges,duration]
    if any(starts[i+1]-starts[i]<6.99 for i in range(len(plan))):raise RuntimeError('Cannot keep every scene at least seven seconds')
    scenes=[]
    for i,(source,anchor) in enumerate(plan):
        start_frame=round(starts[i]*30);end_frame=round(starts[i+1]*30) if i+1<len(plan) else math.ceil(duration*30)
        scenes.append({'scene':i+1,'source_index':source,'anchor':anchor,'anchor_seconds':original[i],
                       'start':start_frame/30,'end':end_frame/30,'duration':(end_frame-start_frame)/30,
                       'frames':end_frame-start_frame,'anchor_adjustment_seconds':round(starts[i]-original[i],3)})
    return scenes

def compare_audio(wav,video,root):
    with wave.open(str(wav),'rb') as stream:
        if stream.getframerate()!=24000 or stream.getnchannels()!=1 or stream.getsampwidth()!=2:raise RuntimeError('Unexpected reviewed WAV format')
        source=np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2').astype(np.float64)/32768
    decoded=run(['ffmpeg','-v','error','-i',str(video),'-map','0:a:0','-ar','24000','-ac','1','-f','s16le','pipe:1'],binary=True)
    actual=np.frombuffer(decoded,dtype='<i2').astype(np.float64)/32768
    preview=min(len(source),24000*12); c=correlate(actual[:preview],source[:preview],mode='full',method='fft')
    center=preview-1;radius=1200;lag=int(np.argmax(c[center-radius:center+radius+1])-radius)
    x=source[max(0,-lag):];y=actual[max(0,lag):];n=min(len(x),len(y));x=x[:n];y=y[:n]
    gain=float(np.dot(x,y)/max(np.dot(x,x),1e-20));res=y-gain*x
    correlation=float(np.dot(x,y)/max(np.sqrt(np.dot(x,x)*np.dot(y,y)),1e-20))
    snr=float(10*np.log10(max(np.mean((gain*x)**2),1e-20)/max(np.mean(res**2),1e-20)))
    windows=[]
    for i in range(0,n-48000,48000):
        a,b=x[i:i+48000],y[i:i+48000]
        if np.sqrt(np.mean(a*a))>.003:
            windows.append(float(np.dot(a,b)/max(np.sqrt(np.dot(a,a)*np.dot(b,b)),1e-20)))
    clipped=float(np.mean(np.abs(actual)>=32767/32768))
    silence=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(video),'-map','0:a:0','-af','silencedetect=noise=-45dB:d=1.2','-f','null','-'],capture_output=True,text=True)
    gaps=[float(t) for t in re.findall(r'silence_duration: ([0-9.]+)',silence.stderr)]
    report={'source_audio_sha256':digest(wav),'video_sha256':digest(video),'lag_samples':lag,'lag_seconds':lag/24000,
            'correlation':correlation,'minimum_voiced_two_second_correlation':min(windows) if windows else 0,
            'signal_to_error_db':snr,'gain':gain,'decoded_peak':float(np.max(np.abs(actual))),
            'clipped_sample_fraction':clipped,'silences_over_1_2_seconds':gaps,
            'decoded_seconds':len(actual)/24000,'source_seconds':len(source)/24000,
            'direct_listening_claimed':False,'independent_asr_review_required':True}
    report['waveform_binding_passed']=correlation>.97 and (min(windows) if windows else 0)>.90 and snr>20 and abs(lag)<1200 and abs(len(actual)-len(source))/24000<.15
    report['signal_quality_passed']=clipped<0.0001 and not gaps
    (root/'audio-binding.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('slug',choices=PLANS);parser.add_argument('--threads',type=int,default=2);args=parser.parse_args()
    slug=args.slug;root=BASE/slug.replace('-','_');audio=root/('audio_final' if (root/'audio_final').is_dir() else 'audio');outdir=root/'final';outdir.mkdir(parents=True,exist_ok=True)
    job=next(j for j in json.loads(MANIFEST.read_text())['jobs'] if j['id']=='current-ten-20261006-'+slug)
    meta=json.loads((audio/'speech-meta.json').read_text());wav=audio/'nestoras.wav';srt=audio/'subs.srt'
    if digest(wav)!=meta['audio_sha256'] or digest(srt)!=meta['srt_sha256'] or meta['script_sha256']!=job['script_sha256']:raise RuntimeError('Audio/subtitle hash binding failed')
    if meta['voice']!='el-GR-NestorasNeural' or meta['duration_seconds']<80:raise RuntimeError('Voice or duration gate failed')
    boundaries=json.loads((audio/'speech-boundaries.json').read_text())
    registry=json.loads((root/'source_registry.json').read_text())
    if isinstance(registry,dict):registry=registry.get('source_records',registry.get('photos',registry.get('sources',registry.get('records',[]))))
    duration=float(meta['duration_seconds']);edges=[0,7,14.967,23.967,30.967,37.967,45.300,67.933] if slug=='prespes' else None;scenes=scene_timing(PLANS[slug],boundaries,duration,edges)
    captions=make_ass(srt,job['script'],outdir/'subs.ass')
    inputs=[];filters=[];paths=[]
    prespes=json.loads((root/'commons_sources.json').read_text())['photos'] if slug=='prespes' else None
    for i,scene in enumerate(scenes):
        index=scene['source_index'];suffix='.jpg' if slug=='prespes' else '.png';path=root/'sources'/f'{index:02d}{suffix}'
        if not path.is_file():raise RuntimeError('Missing reviewed image: '+str(path))
        record=next((r for r in registry if int(r.get('index',r.get('scene',0)))==index),None)
        if record is None:raise RuntimeError('Missing source review record')
        if record.get('sha256')!=digest(path):raise RuntimeError('Source hash changed')
        source_review=record.get('source_visual_review',record.get('review_status',''))
        directly_reviewed=record.get('directly_viewed') is True and source_review.startswith('APPROVED_AS_REAL_SOURCE')
        if not source_review or (not directly_reviewed and 'PASS' not in source_review.upper()):raise RuntimeError('Source direct visual review is missing')
        inputs+=['-i',str(path)];paths.append(path);scene['source_sha256']=digest(path)
        frame_count=scene['frames']
        if slug=='prespes':
            filters.append(f'[{i}:v]split=2[b{i}][f{i}];[b{i}]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=28[bg{i}];[f{i}]scale=1080:1510:force_original_aspect_ratio=decrease[fg{i}];[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2[p{i}]')
            source=f'[p{i}]'
        else:source=f'[{i}:v]'
        zoom=f"1.0+0.040*on/{max(frame_count-1,1)}"
        chain=f"{source}scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='{zoom}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={frame_count}:s=1080x1920:fps=30,setsar=1,format=yuv420p"
        if prespes:
            p=prespes[index-1];credit=outdir/f'credit-{i+1}.txt';credit.write_text(f"Φωτογραφία: {p['creator']} · {p['license']}",encoding='utf-8')
            chain+=f",drawtext=fontfile='{FONT}':textfile='{credit}':fontsize=25:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=10:x=(w-text_w)/2:y=160"
        chain+=f'[v{i}]';filters.append(chain)
    filters.append(''.join(f'[v{i}]' for i in range(len(scenes)))+f"concat=n={len(scenes)}:v=1:a=0,ass='{outdir/'subs.ass'}'[video]")
    video=outdir/(job['id']+'.mp4')
    command=['ffmpeg','-y','-loglevel','error','-filter_complex_threads','1',*inputs,'-i',str(wav),'-filter_complex',';'.join(filters),'-map','[video]','-map',f'{len(scenes)}:a:0','-t',f'{duration:.6f}','-c:v','libx264','-preset','veryfast','-crf','20','-threads',str(args.threads),'-pix_fmt','yuv420p','-r','30','-c:a','aac','-b:a','128k','-ar','48000','-ac','1','-movflags','+faststart',str(video)]
    (outdir/'render-command.json').write_text(json.dumps(command,ensure_ascii=False,indent=2));(outdir/'scene-timing.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2))
    run(command)
    probe=read_probe(video);video_streams=[s for s in probe['streams'] if s['codec_type']=='video'];audio_streams=[s for s in probe['streams'] if s['codec_type']=='audio']
    if len(video_streams)!=1 or len(audio_streams)!=1:raise RuntimeError('Final must contain exactly one video and one audio stream')
    v=video_streams[0]
    if (v['width'],v['height'],v['codec_name'],v['pix_fmt'])!=(1080,1920,'h264','yuv420p') or float(probe['format']['duration'])<80:raise RuntimeError('Final technical format or duration failed')
    binding=compare_audio(wav,video,outdir)
    if not binding['waveform_binding_passed'] or not binding['signal_quality_passed']:raise RuntimeError('Final decoded audio binding or signal-quality review failed')
    frames=[]
    for i,scene in enumerate(scenes,1):
        t=(scene['start']+scene['end'])/2;file=outdir/f'final-scene-{i:02d}.jpg';run(['ffmpeg','-y','-v','error','-ss',str(t),'-i',str(video),'-frames:v','1','-q:v','2',str(file)]);frames.append(file)
    for label,t in [('opening',2.2),('ending',duration-1.6)]:run(['ffmpeg','-y','-v','error','-ss',str(t),'-i',str(video),'-frames:v','1','-q:v','2',str(outdir/f'final-{label}.jpg')])
    columns=3 if len(frames)==6 else 4;cell_w=480 if columns==3 else 432;cell_h=round(cell_w*1920/1080)
    sheet=Image.new('RGB',(columns*cell_w,2*cell_h),(20,20,20))
    for i,p in enumerate(frames):
        with Image.open(p) as image:sheet.paste(ImageOps.fit(image,(cell_w,cell_h)),((i%columns)*cell_w,(i//columns)*cell_h))
    sheet.save(outdir/'final-contact-sheet.jpg',quality=94)
    caption=job['caption']
    if slug=='prespes':caption=caption.replace('οι άδειες και οι δημιουργοί καταγράφονται στις τελικές πιστώσεις.', 'πιστώσεις και άδειες: https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/main/media_jobs/current_ten_20261006_prespes_credits.md')
    (outdir/'final-caption.txt').write_text(caption+'\n',encoding='utf-8')
    qa={'id':job['id'],'video_sha256':digest(video),'duration_seconds':float(probe['format']['duration']),
        'width':1080,'height':1920,'video_codec':'h264','audio_codec':audio_streams[0]['codec_name'],'voice':meta['voice'],
        'scenes':len(scenes),'distinct_source_hashes':len({s['source_sha256'] for s in scenes}),'minimum_scene_seconds':min(s['duration'] for s in scenes),
        'subtitles_burned_in':True,'subtitle_cues':len(captions),'all_script_words_in_subtitles':True,
        'background_music':False,'avatar':False,'filler_padding':False,'waveform_binding_passed':True,
        'signal_quality_passed':True,'publish_ready':False,'direct_listening_claimed':False,
        'release_gate':'PENDING_EXACT_FINAL_VISUAL_REVIEW_AND_INDEPENDENT_ASR_RECONCILIATION'}
    (outdir/'qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(qa,ensure_ascii=False))

if __name__=='__main__':main()
