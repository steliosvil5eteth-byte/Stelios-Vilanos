"""Collect primary-source evidence and Commons photo candidates for human review, not release."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
import json,re,time,hashlib
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'media/carousel_20261016/country_sources'
OUT.mkdir(parents=True,exist_ok=True)
UA='SteliosCarouselResearch/1.0 (https://github.com/steliosvil5eteth-byte/Stelios-Vilanos; research and credited reuse)'
def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':UA}),timeout=40) as r:
        return r.read()
def clean(value):
    return re.sub('<[^>]+>','',value or '').strip()
report={'official_data':[],'photo_candidates':[],'errors':[],'release_approved':False}
# Preserve raw Eurostat responses and their exact source URL and hash.
for geo in ['EL','DE']:
    url='https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_fte?'+urlencode({'lang':'en','geo':geo,'time':'2024'})
    try:
        raw=fetch(url);data=json.loads(raw)
        path=OUT/f'salary_{geo}.json';path.write_bytes(raw)
        report['official_data'].append({'id':'salary_'+geo,'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'data':data})
    except Exception as e:report['errors'].append({'id':'salary_'+geo,'error':str(e)})
queries=[('cover','Athens Acropolis cityscape'),('salary','Frankfurt skyline'),('hours','Berlin Hauptbahnhof interior'),('prices','Athens fruit market'),('housing','Athens apartment buildings'),('education','Berlin university library interior'),('health','Charite hospital building'),('roads','Germany Autobahn aerial'),('digital','laptop computer desk'),('closing','Thessaloniki waterfront promenade')]
for label,query in queries:
    params={'action':'query','format':'json','generator':'search','gsrsearch':query+' filetype:bitmap','gsrnamespace':6,'gsrlimit':4,'prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':1400}
    url='https://commons.wikimedia.org/w/api.php?'+urlencode(params)
    try:
        data=json.loads(fetch(url));pages=sorted(data.get('query',{}).get('pages',{}).values(),key=lambda p:p.get('index',999))
        kept=0
        for page in pages:
            ii=page.get('imageinfo',[{}])[0];em=ii.get('extmetadata',{})
            lic=clean(em.get('LicenseShortName',{}).get('value',''))
            if not any(k in lic.lower() for k in ['cc by','cc0','public domain']):continue
            if any(k in lic.lower() for k in ['nc','nd']):continue
            image_url=ii.get('thumburl') or ii.get('url')
            if not image_url or min(ii.get('width',0),ii.get('height',0))<600:continue
            try:
                raw=fetch(image_url);path=OUT/f'{label}_{kept+1}.jpg'
                import io
                im=Image.open(io.BytesIO(raw)).convert('RGB');im.save(path,quality=95,subsampling=0)
                report['photo_candidates'].append({'group':label,'path':str(path.relative_to(OUT)),'title':page['title'],'file_page':ii.get('descriptionurl'),'image_url':image_url,'original_url':ii.get('url'),'license':lic,'license_url':em.get('LicenseUrl',{}).get('value',''),'artist':clean(em.get('Artist',{}).get('value','')),'description':clean(em.get('ImageDescription',{}).get('value','')),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'width':im.width,'height':im.height})
                kept+=1
                if kept==2:break
            except Exception as e:report['errors'].append({'id':label+' image','error':str(e)})
            time.sleep(.3)
    except Exception as e:report['errors'].append({'id':label,'error':str(e)})
    time.sleep(.5)
(OUT/'source_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
# Only a review contact sheet. Each original file must be checked before final rendering.
items=report['photo_candidates'];w=400;h=330;cols=4
sheet=Image.new('RGB',(cols*w,max(1,(len(items)+cols-1)//cols)*h),'white');draw=ImageDraw.Draw(sheet)
for i,item in enumerate(items):
    im=Image.open(OUT/item['path']);im.thumbnail((w,280))
    x=(i%cols)*w;y=(i//cols)*h
    sheet.paste(im,(x+(w-im.width)//2,y))
    draw.text((x+8,y+284),item['path'],fill='black')
    draw.text((x+8,y+300),item['license'][:45],fill='black')
sheet.save(OUT/'photo_candidates_review.jpg',quality=95)
print(json.dumps({'photos':len(items),'errors':report['errors']},ensure_ascii=False))
