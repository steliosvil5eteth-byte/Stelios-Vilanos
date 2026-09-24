#!/usr/bin/env python3
# 2026-09-25 repair pass: robust rights-cleared fallbacks plus verified direct media pins.
from __future__ import annotations
import html, json, re, sys, urllib.parse, urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_carousel_pack as base

UA='SteliosPhotoCarousel/3.1 zero-cost rights-checked fallback'
BAD=('illustration','drawing','map','logo','coat of arms','diagram','icon','poster','stamp','flag','symbol')
ALLOWED=('cc by','cc-by','cc0','public domain','attribution')

def clean(s): return re.sub('<[^>]+>','',html.unescape(s or '')).strip()

def variants(query):
    q=' '.join(query.split())
    words=[w for w in q.split() if w.lower() not in {'photograph','photo','image','picture'}]
    vals=[q,' '.join(words)]
    if len(words)>2: vals.append(' '.join(words[:2]))
    if words: vals.append(words[0])
    aliases={
      'elderly couple portrait photograph':['elderly couple','older couple','senior couple'],
      'home blackout night photograph':['blackout flashlight','power outage flashlight','flashlight dark'],
      'Scorpius constellation photograph':['Scorpius Milky Way','Scorpius stars','Antares Scorpius'],
      'elderly married couple photograph':['elderly couple','older couple','senior couple'],
      'brown long eared bat photograph':['Plecotus auritus','long-eared bat','brown long-eared bat'],
      'refrigerator food home photograph':['food refrigerator','open refrigerator food','fridge food']
    }
    vals.extend(aliases.get(query,[]))
    out=[]
    for v in vals:
        v=v.strip()
        if v and v not in out: out.append(v)
    return out

def robust_commons_fallback(query,dst):
    last=None
    for q in variants(query):
        params={'action':'query','format':'json','generator':'search','gsrsearch':q,'gsrnamespace':'6','gsrlimit':'50','prop':'imageinfo','iiprop':'url|size|extmetadata','iiurlwidth':'1600'}
        url='https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(params)
        req=urllib.request.Request(url,headers={'User-Agent':UA})
        try:
            with urllib.request.urlopen(req,timeout=90) as r:
                payload=json.loads(r.read().decode('utf-8'))
        except Exception as exc:
            last=exc; continue
        pages=list(payload.get('query',{}).get('pages',{}).values())
        for p in pages:
            title=p.get('title',''); low=title.lower()
            if any(x in low for x in BAD) or not re.search(r'\.(jpe?g|png)$',title,re.I): continue
            infos=p.get('imageinfo') or []
            if not infos: continue
            info=infos[0]; meta=info.get('extmetadata',{})
            licname=clean(meta.get('LicenseShortName',{}).get('value',''))
            usage=clean(meta.get('UsageTerms',{}).get('value',''))
            combo=(licname+' '+usage).lower()
            if not any(x in combo for x in ALLOWED): continue
            if min(int(info.get('width') or 0),int(info.get('height') or 0))<600: continue
            imgurl=info.get('thumburl') or info.get('url')
            if not imgurl: continue
            try:
                base.download(imgurl,dst)
                from PIL import Image
                with Image.open(dst) as im:
                    if min(im.size)<600: raise ValueError('fallback image too small')
                return {'source_url':imgurl,'source_credit':clean(meta.get('Artist',{}).get('value','')),'license':licname or usage,'source_title':title,'fallback_query':q}
            except Exception as exc:
                last=exc; dst.unlink(missing_ok=True)
                continue
    raise ValueError(f'no rights-cleared Commons fallback found for query: {query}; last={last}')

base.commons_fallback=robust_commons_fallback
_original_render=base.render_card

def commons_redirect(filename):
    return 'https://commons.wikimedia.org/wiki/Special:Redirect/file/'+urllib.parse.quote(filename,safe='()_,.-')+'?width=1600'

def proxy(url):
    return 'https://images.weserv.nl/?url='+urllib.parse.quote(url,safe='')+'&w=1600&output=jpg'

REL='https://upload.wikimedia.org/wikipedia/commons/9/92/Elderly_couple_%281586495%29.jpg'
ORANGE='https://upload.wikimedia.org/wikipedia/commons/3/39/Elderly_couple_%281527965%29.jpg'
BAT='https://upload.wikimedia.org/wikipedia/commons/a/ac/Bat_in_the_Hand_%28251301881%29.jpg'
FRIDGE='https://upload.wikimedia.org/wikipedia/commons/0/09/Food_into_a_refrigerator_-_20111002.jpg'

PINNED={
  'ΕΣΥ ΤΙ ΠΙΣΤΕΥΕΙΣ; — 7/7': proxy(REL),
  'ΜΙΚΡΑ ΠΟΥ ΒΟΗΘΟΥΝ — 2/9': commons_redirect('USB power bank.jpg'),
  'ΑΥΤΟ ΓΙΝΕΤΑΙ ΣΠΙΤΙ — 5/5': proxy(ORANGE),
  'ΖΥΓΟΣ — 1/6': commons_redirect('Photo of the constellation Libra produced by NOIRLab in collaboration with Eckhard Slawik, a German astrophotographer (libra).jpg'),
  'ΣΚΟΡΠΙΟΣ — 2/6': commons_redirect('Photo of the constellation Scorpius produced by NOIRLab in collaboration with Eckhard Slawik, a German astrophotographer (scorpius).jpg'),
  'ΤΟΞΟΤΗΣ — 3/6': commons_redirect('Photo of the constellation Sagittarius produced by NOIRLab in collaboration with Eckhard Slawik, a German astrophotographer (sagittarius).jpg'),
  'ΑΙΓΟΚΕΡΩΣ — 4/6': commons_redirect('Photo of the constellation Capricornus produced by NOIRLab in collaboration with Eckhard Slawik, a German astrophotographer (capricornus).jpg'),
  'ΥΔΡΟΧΟΟΣ — 5/6': commons_redirect('Photo of the constellation Aquarius produced by NOIRLab in collaboration with Eckhard Slawik, a German astrophotographer (aquarius).jpg'),
  'ΙΧΘΥΕΣ — 6/6': commons_redirect('Photo of the constellation Pisces produced by NOIRLab in collaboration with Eckhard Slawik, a German astrophotographer (pisces).jpg')
}
QUERY_PINNED={
  'elderly couple portrait photograph':proxy(REL),
  'elderly married couple photograph':proxy(ORANGE),
  'brown long eared bat photograph':proxy(BAT),
  'refrigerator food home photograph':proxy(FRIDGE)
}

def pinned_render(slide,index,total,work,require_photo):
    title=slide.get('visible_title') or slide.get('title','')
    query=slide.get('source_query','')
    if title in PINNED or query in QUERY_PINNED:
        slide=dict(slide)
        slide['source_url']=PINNED.get(title,QUERY_PINNED.get(query))
    return _original_render(slide,index,total,work,require_photo)

base.render_card=pinned_render
base.main()
