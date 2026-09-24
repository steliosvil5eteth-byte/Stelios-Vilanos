#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_carousel_pack as base

ap=argparse.ArgumentParser()
ap.add_argument('--source-manifest',required=True)
ap.add_argument('--output',required=True)
ns=ap.parse_args()

src=json.loads(Path(ns.source_manifest).read_text(encoding='utf-8'))
ids={'current-20260925-0700-relationship-roles','current-20260925-1500-half-orange-story'}
jobs=[j for j in src.get('jobs',[]) if j.get('id') in ids]
if {j.get('id') for j in jobs} != ids:
    raise SystemExit('required repair jobs missing')

DIRECT={
    'Mother and children at home.jpg':'https://upload.wikimedia.org/wikipedia/commons/4/40/Mother_and_children_at_home.jpg',
    'Elderly Couple Eating.jpg':'https://upload.wikimedia.org/wikipedia/commons/6/6b/Elderly_Couple_Eating.jpg'
}
def source(filename):
    return DIRECT.get(filename,'https://commons.wikimedia.org/wiki/Special:Redirect/file/'+urllib.parse.quote(filename,safe='()_,.-')+'?width=1600')

sources={
'current-20260925-0700-relationship-roles':[
 ('Couple walking hand-in-hand on the beach.jpg','RickObst / Wikimedia Commons','CC BY 4.0'),
 ('Kochendes Paar in einer Küche 2017-01-15.jpg','Werner Heiber / Wikimedia Commons','CC0 1.0'),
 ('Senior couple at home checking finance on credit card from above.jpg','Shixart1985 / Wikimedia Commons','CC BY 2.0'),
 ('Couple walking (16267925833).jpg','bluesbby / Wikimedia Commons','CC BY 2.0'),
 ('Mother and children at home.jpg','Ngostary2k / Wikimedia Commons','CC BY-SA 4.0'),
 ('Doctor and couple talking.jpg','Rhoda Baer / National Cancer Institute','Public Domain'),
 ('Older couple enjoys time together indoors.jpg','Shixart1985 / Wikimedia Commons','CC BY 2.0')
],
'current-20260925-1500-half-orange-story':[
 ('Orange slices.jpg','Donna Alvita / Wikimedia Commons','CC BY-SA 4.0'),
 ('Older couple enjoys coffee together.jpg','Shixart1985 / Wikimedia Commons','CC BY 2.0'),
 ('Morning-breakfast-orange-juice (23699976063).jpg','Pixel.la / Wikimedia Commons','CC0 1.0'),
 ('Elderly Couple Eating.jpg','Bill Branson / Wikimedia Commons','CC0 1.0'),
 ('Old couple walking.jpg','Aneeshnl / Wikimedia Commons','CC BY 4.0')
]
}

used=set()
for job in jobs:
    rows=sources[job['id']]
    if len(rows)!=len(job['slides']):
        raise SystemExit(job['id']+': source/card mismatch')
    for slide,(fn,credit,lic) in zip(job['slides'],rows):
        if fn in used:
            raise SystemExit('duplicate photo across repair jobs: '+fn)
        used.add(fn)
        slide['source_url']=source(fn)
        slide['source_query']=fn
        slide['source_credit']=credit
        slide['license']=lic
        slide['source_filename']=fn

repair={
 'approved':True,
 'paid_generation_allowed':False,
 'strategy_id':'CURRENT_TEN_DAILY_REPAIR',
 'local_date':'2026-09-25',
 'require_photographic_visuals':True,
 'purpose':'Direct visual-QA repair for 07:00 and 15:00 using unique rights-cleared photographic sources. No image reuse across either post.',
 'jobs':jobs
}

outroot=Path(ns.output)
outroot.mkdir(parents=True,exist_ok=True)
manifest=outroot/'current-card-repair-manifest.json'
manifest.write_text(json.dumps(repair,ensure_ascii=False,indent=2),encoding='utf-8')
sys.argv=[sys.argv[0],'--manifest',str(manifest),'--output',ns.output]
base.main()
