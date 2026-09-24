#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_azure_feature_batch as base

ap=argparse.ArgumentParser()
ap.add_argument('--source-manifest',required=True)
ap.add_argument('--output',required=True)
ns=ap.parse_args()

src=json.loads(Path(ns.source_manifest).read_text(encoding='utf-8'))
ids={'phenom-moonbow-20260925','legend-selkie-20260925'}
jobs=[j for j in src.get('jobs',[]) if j.get('id') in ids]
if {j.get('id') for j in jobs} != ids:
    raise SystemExit('required current repair jobs missing')

for j in jobs:
    j['approved']=True
    j['publish_to_social']=False
    j['reset_hold']=False
    j['scenes']=int(j['photo_target'])
    j['max_duration_seconds']=None

selkie=next(j for j in jobs if j['id']=='legend-selkie-20260925')
selkie['visuals'][0]={
    'source':'Grey Seal — Seoirse29 (2024)',
    'direct_media_url':'https://commons.wikimedia.org/wiki/Special:Redirect/file/Grey_Seal.jpg',
    'source_page_url':'https://commons.wikimedia.org/wiki/File:Grey_Seal.jpg',
    'attribution':'Seoirse29, “Grey Seal”, CC BY-SA 4.0, via Wikimedia Commons; indicate crops/changes.',
    'license':'CC BY-SA',
    'license_url':'https://creativecommons.org/licenses/by-sa/4.0/',
    'visual_kind':'photograph'
}

for j in jobs:
    visuals=j.get('visuals') or []
    if len(visuals)!=int(j['photo_target']):
        raise SystemExit(f"{j['id']}: visual count mismatch")
    if any(v.get('visual_kind')!='photograph' for v in visuals):
        raise SystemExit(f"{j['id']}: non-photographic visual forbidden")
    pages=[v.get('source_page_url') for v in visuals]
    if len(set(pages))!=len(pages):
        raise SystemExit(f"{j['id']}: duplicate source visual forbidden")

repair={
    'approved':True,
    'paid_generation_allowed':False,
    'local_date':'2026-09-25',
    'require_unique_visual_per_scene':True,
    'jobs':jobs
}
outroot=Path(ns.output)
outroot.mkdir(parents=True,exist_ok=True)
manifest=outroot/'current-repair-manifest.json'
manifest.write_text(json.dumps(repair,ensure_ascii=False,indent=2),encoding='utf-8')

_original=base.make_video
def unique_make_video(job,photos,wav,srt,dur,out):
    files=sorted(photos.glob('*.jpg'))
    scenes=int(job.get('scenes',len(files)))
    if scenes!=len(files):
        raise RuntimeError(f"{job['id']}: exactly one unique visual per scene required ({scenes} scenes, {len(files)} photos)")
    return _original(job,photos,wav,srt,dur,out)

base.make_video=unique_make_video
sys.argv=[sys.argv[0],'--manifest',str(manifest),'--output',ns.output]
base.main()
