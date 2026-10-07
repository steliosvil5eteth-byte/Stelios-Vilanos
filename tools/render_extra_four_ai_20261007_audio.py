#!/usr/bin/env python3
"""Generate the four requested extra stories using the established Nestoras path.

This creates audio and timing evidence only. It cannot publish or approve media.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import render_azure_feature_batch as renderer

BATCH = 'extra-four-ai-20261007'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    data=json.loads(a.manifest.read_text(encoding='utf-8'))
    jobs=data.get('jobs',[])
    if data.get('batch_id') != BATCH or len(jobs)!=4:
        raise RuntimeError('The authorized extra batch must contain exactly four stories')
    if renderer.VOICE!='el-GR-NestorasNeural':
        raise RuntimeError('Wrong voice configured')
    slugs=[j['slug'] for j in jobs]
    if len(set(slugs))!=4 or any('/' in s or '..' in s for s in slugs):
        raise RuntimeError('Story directories must be distinct safe slugs')
    summary=[]
    for j in jobs:
        if j['id']!=j['slug']:
            raise RuntimeError('Story ID and directory must agree')
        script=j['script']
        script_sha=hashlib.sha256(script.encode('utf-8')).hexdigest()
        if script_sha!=j['script_sha256'] or len(script.split())<250:
            raise RuntimeError('Incomplete or changed narration')
        if not script.endswith(renderer.CTA) or len(j['scenes'])!=7:
            raise RuntimeError('Missing complete story or closing CTA')
        out=a.output/j['slug'];out.mkdir(parents=True,exist_ok=True)
        (out/'script.txt').write_text(script+'\n',encoding='utf-8')
        (out/'caption.txt').write_text(j['caption']+'\n',encoding='utf-8')
        wav,boundaries,duration=renderer.synthesize(script,out,80.01,180)
        srt=out/'subs.srt';cues=renderer.subtitles(boundaries,duration,srt)
        (out/'boundaries.json').write_text(json.dumps(boundaries,ensure_ascii=False,indent=2),encoding='utf-8')
        meta={'id':j['id'],'slug':j['slug'],'batch_id':BATCH,
              'voice':renderer.VOICE,'provider':'Azure Speech','duration_seconds':duration,
              'script_sha256':script_sha,'audio_sha256':sha(wav),'srt_sha256':sha(srt),
              'word_boundaries':len(boundaries),'subtitle_cues':cues,
              'background_music':False,'avatar':False,'filler_padding':False,
              'technical_audio_passed':True,'publish_ready':False,
              'release_gate':'PENDING_ASR_AND_EXACT_FINAL_MEDIA_REVIEW'}
        (out/'speech-meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        summary.append(meta)
        print(json.dumps({'id':j['id'],'seconds':duration,'subtitle_cues':cues},ensure_ascii=False))
    (a.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
