#!/usr/bin/env python3
"""Local, explicit fiction-card layout adjustments; never edits shared renderer."""
import importlib.util
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('root_renderer',ROOT/'render_final_carousels.py')
r=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

def redraw(p,c,source,out,*,clay=False):
    with Image.open(source) as raw:
        im=raw.convert('RGB').resize((1080,1080),Image.Resampling.LANCZOS)
    start,end=(700,760) if clay else (570,685)
    a=np.zeros((1080,1080,4),dtype=np.uint8)
    a[:,:,:3]=[8,14,20]
    for y in range(1080):
        if y<175: alpha=int(max(0,170*(1-y/175)))
        elif y<start: alpha=0
        elif y<end: alpha=int(235*(y-start)/(end-start))
        else: alpha=242
        a[y,:,3]=alpha
    im=Image.alpha_composite(im.convert('RGBA'),Image.fromarray(a,'RGBA')).convert('RGB')
    d=ImageDraw.Draw(im)
    d.text((48,30),r.LABELS[p['series']],font=r.font(25,True),fill='#F2D18A')
    num=f"{c['number']}/{p['card_count']}"
    d.text((1032-d.textlength(num,font=r.font(27,True)),28),num,font=r.font(27,True),fill='#FFFFFF')
    final=c['number']==p['card_count']
    typography=r.put_text(im,c['text'].replace(r.CTA,'').strip(),
                          (52,760 if clay else 668,1028,965 if final else 1000),
                          start=38 if clay else 43,minsize=36)
    cta_typography=None
    if final:
        d.line((52,985,1028,985),fill='#A9894D',width=2)
        cta_typography=r.put_text(im,r.CTA,(52,1000,1030,1051),start=36,minsize=36,bold=True,color='#F2D18A')
    else:
        d.text((52,1037),'ΜΥΘΟΠΛΑΣΙΑ • ΤΝ',font=r.font(16),fill='#AAB6BE')
    im.save(out,'JPEG',quality=94,subsampling=0,optimize=True)
    rec={'path':str(out),'source_path':str(source),'source_sha256':r.sha(source),'sha256':r.sha(out),
         'dimensions':[1080,1080],'format':'JPEG','full_text':c['text'],'typography':typography,
         'layout_adjustment':{'scope':'this card only','photo_crop':False,'overlay_fade':[start,end],
                              'reason':'Show collapsed clay bowl without covering it with copy' if clay else 'CTA at minimum 36 px'}}
    if cta_typography:rec['cta_typography']=cta_typography
    return rec

def main():
    for p in r.packs():
        s=p['series']
        if s not in ('relationships','love_soul_relationship'):continue
        folder=ROOT/'final'/s
        m=json.loads((folder/'manifest.json').read_text())
        targets=[len(p['cards'])]
        if s=='love_soul_relationship':targets.insert(0,3)
        for n in targets:
            m['cards'][n-1]=redraw(p,p['cards'][n-1],r.source_for(s,n),folder/f'card-{n:02d}.jpg',clay=(s=='love_soul_relationship' and n==3))
        m['video']=r.video(p,[Path(c['path']) for c in m['cards']],folder)
        m['layout_adjustments']='Card-specific local adjustments in final/fiction_layout_adjustments.py; shared renderer unchanged; original music unchanged.'
        (folder/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'series':s,'changed_cards':targets,'video_sha256':m['video']['sha256']}),flush=True)

if __name__=='__main__':main()
