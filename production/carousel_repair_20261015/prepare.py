#!/usr/bin/env python3
"""Prepare review candidates only. Never schedule or publish content."""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SLUGS = ['cancer_aries','virgo_sagittarius','pisces_capricorn','mother_light','breakup_message','father_actions','bench_flower']
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
CTA = 'Αν σας άρεσε, ακολουθήστε για περισσότερα.'

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare(source: Path, out: Path, make_video: bool) -> None:
    manifest = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    posts = {p['slug']:p for p in manifest['posts']}
    result = {'brand_id':7076410,'qa_status':'NEEDS_EXACT_FINAL_REVIEW','source_manifest_sha256':sha(source/'manifest.json'),'posts':[]}
    for slug in SLUGS:
        post=posts[slug]; target=out/slug; target.mkdir(parents=True,exist_ok=True)
        paths=[]; frames=[]
        for index, card in enumerate(post['cards'],1):
            src=source/slug/Path(card['path']).name
            if sha(src)!=card['sha256']: raise ValueError(f'Source hash mismatch: {src}')
            with Image.open(src) as im:
                if im.size!=(1080,1080): raise ValueError(f'Wrong size: {src}')
                art=im.convert('RGB'); d=ImageDraw.Draw(art)
                label='Εικόνες AI • Ψυχαγωγική αστρολογία' if slug in SLUGS[:3] else 'Εικόνες AI • Μυθοπλασία'
                small=ImageFont.truetype(REG,25)
                width=int(d.textlength(label,font=small))+30
                d.rounded_rectangle((60,149,60+width,194),radius=12,fill=(8,15,24))
                d.text((75,157),label,font=small,fill=(238,240,245))
                if index==6:
                    d.rectangle((0,941,1079,1079),fill=(5,12,22))
                    d.line((76,942,1004,942),fill=(245,215,156),width=2)
                    font=ImageFont.truetype(FONT,39)
                    for line,y in [('Αν σας άρεσε, ακολουθήστε',958),('για περισσότερα.',1007)]:
                        if d.textlength(line,font=font)>928: raise ValueError('CTA overflow')
                        d.text((76,y),line,font=font,fill=(255,222,151))
                p=target/f'card_{index:02d}.jpg';art.save(p,quality=95,optimize=True)
            paths.append(p)
            frame=Image.new('RGB',(1080,1920),(5,12,22))
            frame.paste(Image.open(p),(0,360))
            fd=ImageDraw.Draw(frame)
            fd.text((64,205),'ΙΣΤΟΡΙΕΣ ΠΟΥ ΜΑΣ ΑΓΓΙΖΟΥΝ',font=ImageFont.truetype(FONT,42),fill=(237,237,240))
            fd.text((64,1558),'Εικόνες AI • Χωρίς αφήγηση',font=ImageFont.truetype(REG,31),fill=(197,202,212))
            fp=target/f'video_frame_{index:02d}.png';frame.save(fp);frames.append(fp)
        video=target/'youtube_vertical.mp4'
        if make_video:
            concat=target/'vertical.ffconcat'
            lines=['ffconcat version 1.0']
            for fp in frames: lines += ["file '"+str(fp.resolve())+"'",'duration 11']
            lines += ["file '"+str(frames[-1].resolve())+"'"]
            concat.write_text('\n'.join(lines)+'\n',encoding='utf-8')
            subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-safe','0','-f','concat','-i',str(concat),'-vf','fps=24,format=yuv420p','-t','66','-an','-c:v','libx264','-preset','ultrafast','-crf','23','-threads','2','-movflags','+faststart',str(video)],check=True,timeout=180)
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]))
            streams=probe['streams'];v=streams[0]
            if len(streams)!=1 or v['codec_type']!='video' or (v['width'],v['height'])!=(1080,1920) or abs(float(probe['format']['duration'])-66)>0.1: raise ValueError('Video validation failed')
        contact=Image.new('RGB',(1080,1620))
        for i,p in enumerate(paths): contact.paste(Image.open(p).resize((540,540)),((i%2)*540,(i//2)*540))
        contact.save(target/'final_cards_contact.jpg',quality=95)
        entry={'slug':slug,'title':post['title'],'qa_status':'NEEDS_EXACT_FINAL_REVIEW','cards':[{'path':str(p.relative_to(out)),'sha256':sha(p)} for p in paths]}
        if make_video:entry['youtube_video']={'path':str(video.relative_to(out)),'sha256':sha(video),'duration_seconds':66,'width':1080,'height':1920,'fps':24,'audio_streams':0}
        result['posts'].append(entry)
    out.mkdir(parents=True,exist_ok=True)
    (out/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'candidates':len(result['posts']),'status':result['qa_status'],'output':str(out)}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--video',action='store_true');args=ap.parse_args();prepare(args.source,args.out,args.video)
