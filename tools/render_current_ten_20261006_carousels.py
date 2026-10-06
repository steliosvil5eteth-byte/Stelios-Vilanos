#!/usr/bin/env python3
"""Typeset complete reviewed Greek copy over explicit newly generated photographs.

This renderer never grants publication approval. Exact final visual/audio review
and a fresh three-source duplicate check remain mandatory after it runs.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re, subprocess, tempfile, unicodedata, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
WORK=ROOT.parent
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
CTA='Αν σας άρεσε, ακολουθήστε για περισσότερα.'
LABELS={'relationships':'ΣΧΕΣΕΙΣ','survival':'ΚΑΝΟΝΕΣ ΕΠΙΒΙΩΣΗΣ','dog_bartender':'ΣΚΥΛΟΣ ΜΠΑΡΜΑΝ','zodiac':'ΖΩΔΙΑ • ΕΣΕΙΣ ΟΙ ΔΥΟ','love_soul_relationship':'ΙΣΤΟΡΙΕΣ ΨΥΧΗΣ','myth_or_truth':'ΜΥΘΟΣ Ή ΑΛΗΘΕΙΑ;'}
COUNTS={'relationships':7,'survival':9,'dog_bartender':4,'zodiac':6,'love_soul_relationship':5,'myth_or_truth':4}
GLYPHS={'Κριός':'♈','Ταύρος':'♉','Δίδυμοι':'♊','Καρκίνος':'♋','Λέων':'♌','Παρθένος':'♍','Ζυγός':'♎','Σκορπιός':'♏','Τοξότης':'♐','Αιγόκερως':'♑','Υδροχόος':'♒','Ιχθύες':'♓'}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def caps(s): return ''.join(c for c in unicodedata.normalize('NFD',s.upper()) if not unicodedata.combining(c))
def font(size,bold=False): return ImageFont.truetype(BOLD if bold else FONT,size)
def run(args):
    p=subprocess.run(args,text=True,capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr[-4000:])
    return p.stdout
def wrap(draw,text,f,width):
    result=[]
    for para in text.split('\n'):
        line=''
        for word in para.split():
            if draw.textlength(word,font=f)>width: raise ValueError('Word cannot fit')
            test=(line+' '+word).strip()
            if line and draw.textlength(test,font=f)>width: result.append(line);line=word
            else: line=test
        if line:result.append(line)
    return result
def put_text(im,text,box,start=44,minsize=36,bold=False,color='#F9F7F0'):
    d=ImageDraw.Draw(im);x,y,x1,y1=box
    for size in range(start,minsize-1,-1):
        f=font(size,bold);lines=wrap(d,text,f,x1-x);lead=int(size*1.28)
        if len(lines)*lead<=y1-y:break
    else:raise ValueError(f'Text does not fit at {minsize}px: {text}')
    for line in lines:
        d.text((x,y),line,font=f,fill=color,stroke_width=0);y+=lead
    return {'size':size,'lines':lines,'bottom':y,'text':text}

def packs():
    fiction=json.loads((WORK/'fiction_production_proposals.json').read_text())['posts']
    fact=json.loads((WORK/'research_fresh_content_proposed.json').read_text())['items']
    out=[]
    for p in fiction+fact:
        s=p['series']
        if s not in COUNTS:continue
        q=dict(p);q['series']=s;q['card_count']=COUNTS[s]
        q['cards']=[dict(c) if isinstance(c,dict) else {'number':i+1,'of':COUNTS[s],'text':c} for i,c in enumerate(p['cards'])]
        if len(q['cards'])!=COUNTS[s]:raise ValueError('Card count mismatch')
        if s in ['survival','myth_or_truth']:
            q['caption']=q['caption'].replace('\nΑν σας άρεσε,','\nΕικόνες αναπαράστασης δημιουργημένες με ΤΝ.\nΑν σας άρεσε,')
        q['job_id']='current-ten-20261006-'+s.replace('_','-')
        out.append(q)
    return out

def source_for(series,n):
    folder=ROOT/'sources'/series
    candidates=[folder/f'{n:02d}{ext}' for ext in ('.png','.jpg','.jpeg')]
    p=next((p for p in candidates if p.exists()),None)
    if not p: raise FileNotFoundError(f'Missing explicit source {series}/{n:02d}')
    return p

def card(p,c,source,out):
    with Image.open(source) as raw:
        if min(raw.size)<600:raise ValueError('Source too small')
        if raw.width!=raw.height:raise ValueError('Explicit square source required; no blind crop')
        im=raw.convert('RGB').resize((1080,1080),Image.Resampling.LANCZOS)
    # Preserve the selected photograph; only add the requested text layout.
    overlay=Image.new('RGBA',im.size,(0,0,0,0));a=np.zeros((1080,1080,4),dtype=np.uint8)
    a[:,:,:3]=[8,14,20]
    for y in range(1080):
        if y<175:alpha=int(max(0,170*(1-y/175)))
        elif y<570:alpha=0
        elif y<685:alpha=int(235*(y-570)/115)
        else:alpha=242
        a[y,:,3]=alpha
    im=Image.alpha_composite(im.convert('RGBA'),Image.fromarray(a,'RGBA')).convert('RGB')
    d=ImageDraw.Draw(im);d.text((48,30),LABELS[p['series']],font=font(25,True),fill='#F2D18A')
    num=f"{c['number']}/{p['card_count']}";w=d.textlength(num,font=font(27,True))
    d.text((1032-w,28),num,font=font(27,True),fill='#FFFFFF')
    if p['series']=='zodiac':
        pair=p['pairs'][c['number']-1]
        for x,sign in zip([48,552],pair):
            d.rounded_rectangle((x,583,x+480,662),radius=16,fill='#13212B',outline='#BB9855',width=2)
            d.text((x+14,589),GLYPHS[sign],font=font(50,True),fill='#F2D18A')
            d.text((x+88,608),caps(sign),font=font(27,True),fill='#FFFFFF')
    body=c['text'].replace(CTA,'').strip()
    if p['series']=='myth_or_truth' and c['number']==1:body=body.replace('ΜΥΘΟΣ Ή ΑΛΗΘΕΙΑ;\n','')
    final=c['number']==p['card_count'];bott=965 if final else 1000
    typography=put_text(im,body,(52,668,1028,bott),start=46 if c['number']==1 else 43,minsize=36,bold=c['number']==1)
    if final:
        d=ImageDraw.Draw(im);d.line((52,985,1028,985),fill='#A9894D',width=2)
        cta=put_text(im,CTA,(52,1000,1030,1051),start=33,minsize=30,bold=True,color='#F2D18A')
    else:
        kind='ΨΥΧΑΓΩΓΙΑ • ΤΝ' if p['series']=='zodiac' else ('ΜΥΘΟΠΛΑΣΙΑ • ΤΝ' if p['series'] in ['relationships','love_soul_relationship','dog_bartender'] else 'ΕΙΚΟΝΑ ΑΝΑΠΑΡΑΣΤΑΣΗΣ • ΤΝ')
        d.text((52,1037),kind,font=font(16),fill='#AAB6BE')
    im.save(out,'JPEG',quality=94,subsampling=0,optimize=True)
    return {'path':str(out),'source_path':str(source),'source_sha256':sha(source),'sha256':sha(out),'dimensions':[1080,1080],'format':'JPEG','full_text':c['text'],'typography':typography}

def original_music(path,duration):
    sr=48000; samples=int(sr*duration);mix=np.zeros(samples,dtype=np.float64)
    chords=[(57,60,64),(53,57,60),(48,52,55),(55,59,62)]
    step=.75;pattern=(0,1,2,1,0,2,1,2)
    for k,start in enumerate(np.arange(0,duration,step)):
        note=chords[(k//8)%len(chords)][pattern[k%8]]
        hz=440*2**((note-69)/12);length=min(int(sr*2.8),samples-int(sr*start))
        t=np.arange(length)/sr;env=(1-np.exp(-t*32))*np.exp(-t*2.5)
        tone=(np.sin(2*np.pi*hz*t)+.26*np.sin(2*np.pi*2*hz*t)+.08*np.sin(2*np.pi*3*hz*t))*env*.06
        i=int(start*sr);mix[i:i+length]+=tone
    edge=min(int(sr*1.6),samples//2);mix[:edge]*=np.linspace(0,1,edge);mix[-edge:]*=np.linspace(1,0,edge)
    stereo=np.stack([mix,mix*.96],axis=1);pcm=(np.clip(stereo,-.5,.5)*32767).astype('<i2')
    with wave.open(str(path),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm.tobytes())

def video(p,cards,folder):
    # Reading time follows the complete Greek copy, bounded by a ten-second card.
    secs=[max(7.,min(10.,len(re.findall(r'\S+',c['text']))/2.4+1.3)) for c in p['cards']]
    with tempfile.TemporaryDirectory() as temp:
        td=Path(temp);segments=[]
        for i,(src,dur) in enumerate(zip(cards,secs),1):
            with Image.open(src) as square:
                vert=Image.new('RGB',(1080,1920),'#0A121B');vert.paste(square,(0,420))
                dr=ImageDraw.Draw(vert);dr.text((70,225),'Ιστορίες που μας αγγίζουν',font=font(38,True),fill='#EED2A1')
                vp=td/f'{i:02d}.jpg';vert.save(vp,quality=94)
            seg=td/f'{i:02d}.mp4'
            run(['ffmpeg','-y','-v','error','-loop','1','-framerate','25','-i',str(vp),'-t',str(dur),'-vf','setsar=1,fps=25','-c:v','libx264','-threads','2','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-an',str(seg)])
            segments.append(seg)
        listing=td/'concat.txt';listing.write_text('\n'.join("file '"+str(x)+"'" for x in segments)+'\n')
        silent=td/'silent.mp4';run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(silent)])
        meta=json.loads(run(['ffprobe','-v','error','-show_format','-of','json',str(silent)]));dur=float(meta['format']['duration'])
        music=td/'music.wav';original_music(music,dur)
        out=folder/(p['job_id']+'.mp4')
        run(['ffmpeg','-y','-v','error','-i',str(silent),'-i',str(music),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',str(out)])
    meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(out)]))
    if len([x for x in meta['streams'] if x['codec_type']=='audio'])!=1:raise ValueError('Exactly one audio stream required')
    return {'path':str(out),'sha256':sha(out),'duration':float(meta['format']['duration']),'seconds_per_card':secs,'width':1080,'height':1920,'audio':'One original instrumental composition synthesized locally; no voice','complete_card_count':len(cards),'ffprobe':meta}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--series',action='append');ns=ap.parse_args()
    for p in packs():
        if ns.series and p['series'] not in ns.series:continue
        source=[source_for(p['series'],i+1) for i in range(len(p['cards']))]
        if len(set(map(sha,source)))!=len(source):raise ValueError('Duplicate source bytes')
        folder=ROOT/'final'/p['series'];folder.mkdir(parents=True,exist_ok=True)
        rec=[]
        for c,s in zip(p['cards'],source):rec.append(card(p,c,s,folder/f"card-{c['number']:02d}.jpg"))
        v=video(p,[Path(x['path']) for x in rec],folder)
        manifest={'brandId':7076410,'date':'2026-10-06','series':p['series'],'job_id':p['job_id'],'title':p['title'],'content_key':p.get('content_key'),
                  'caption':p['caption'],'cards':rec,'video':v,'source_references':p.get('sources',[]),'release_status':'PENDING_DIRECT_VISUAL_AUDIO_REVIEW','publish_ready':False}
        (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        (folder/'caption.txt').write_text(p['caption']+'\n')
        print(json.dumps({'series':p['series'],'cards':len(rec),'duration':v['duration'],'manifest':str(folder/'manifest.json'),'review':'PENDING'},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
