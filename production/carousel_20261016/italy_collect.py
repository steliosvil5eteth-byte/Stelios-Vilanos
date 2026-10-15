"""Primary-source and photo collection plus byte-integrity audit. No publication writes."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageDraw
import json,hashlib,re,io,time
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'media/carousel_20261016';OUT=BASE/'italy_sources';OUT.mkdir(parents=True,exist_ok=True)
UA='SteliosCarouselResearch/1.0 (https://github.com/steliosvil5eteth-byte/Stelios-Vilanos; credited reuse)'
def get(u):
 with urlopen(Request(u,headers={'User-Agent':UA}),timeout=60) as r:return r.read()
def clean(s):return re.sub('<[^>]+>','',s or '').strip()
r={'sources':[],'photos':[],'errors':[],'release_approved':False}
for ds in ['nama_10_fte','lfsa_ewhan2','ilc_mded01']:
 for geo in ['EL','IT']:
  u='https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'+ds+'?'+urlencode({'lang':'en','geo':geo,'time':'2024'})
  try:
   b=get(u);d=json.loads(b);p=OUT/f'{ds}_{geo}.json';p.write_bytes(b)
   r['sources'].append({'dataset':ds,'geo':geo,'url':u,'sha256':hashlib.sha256(b).hexdigest(),'path':p.name,'dimensions':d.get('id'),'size':d.get('size')})
  except Exception as e:r['errors'].append({'dataset':ds,'geo':geo,'error':str(e)})
queries=[('cover','Rome Colosseum panorama'),('salary','Milan Porta Nuova skyline'),('hours','Roma Termini platforms train'),('prices','Florence market vegetables'),('housing','Naples apartment balconies'),('education','Bologna university library interior'),('health','Policlinico Gemelli Roma building'),('roads','Italy autostrada aerial'),('digital','computer keyboard desk Unsplash'),('closing','Patras waterfront panorama')]
for group,q in queries:
 u='https://commons.wikimedia.org/w/api.php?'+urlencode({'action':'query','format':'json','generator':'search','gsrsearch':q+' filetype:bitmap','gsrnamespace':6,'gsrlimit':5,'prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':1400})
 try:
  pages=sorted(json.loads(get(u)).get('query',{}).get('pages',{}).values(),key=lambda p:p.get('index',999));n=0
  for p in pages:
   ii=p.get('imageinfo',[{}])[0];m=ii.get('extmetadata',{});lic=clean(m.get('LicenseShortName',{}).get('value',''))
   if not any(k in lic.lower() for k in ['cc by','cc0','public domain']) or any(k in lic.lower() for k in ['nc','nd']):continue
   if min(ii.get('width',0),ii.get('height',0))<600:continue
   u2=ii.get('thumburl') or ii.get('url')
   if not u2:continue
   try:
    im=Image.open(io.BytesIO(get(u2))).convert('RGB');p2=OUT/f'{group}_{n+1}.jpg';im.save(p2,quality=95,subsampling=0)
    r['photos'].append({'group':group,'path':p2.name,'title':p['title'],'file_page':ii.get('descriptionurl'),'image_url':u2,'original_url':ii.get('url'),'artist':clean(m.get('Artist',{}).get('value','')),'license':lic,'license_url':m.get('LicenseUrl',{}).get('value',''),'description':clean(m.get('ImageDescription',{}).get('value','')),'sha256':hashlib.sha256(p2.read_bytes()).hexdigest()});n+=1
    if n>=2:break
   except Exception as e:r['errors'].append({'photo':group,'error':str(e)})
 except Exception as e:r['errors'].append({'group':group,'error':str(e)})
 time.sleep(.3)
(OUT/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
ims=r['photos'];w=400;h=320;cols=4
sheet=Image.new('RGB',(cols*w,max(1,(len(ims)+cols-1)//cols)*h),'white');dr=ImageDraw.Draw(sheet)
for i,p in enumerate(ims):
 im=Image.open(OUT/p['path']);im.thumbnail((w,280));x=i%cols*w;y=i//cols*h;sheet.paste(im,(x+(w-im.width)//2,y));dr.text((x+5,y+284),p['path'],fill='black');dr.text((x+5,y+300),p['license'][:45],fill='black')
sheet.save(OUT/'review.jpg',quality=95)
# These exact media URLs came from immediate live readback of our sixteen scheduled records.
ids={
 'taurus_aquarius':(['12296581125992455870','12374054242275064549','13619472477854821367','12110235757954219057','15499951880582917452','17004619302057124772'],'12149989679487164576'),
 'guitar_home':(['14894950785267884707','2409561157426068078','5196535307002841522','2967922428190700745','11741350717196219961','5072606170336072632'],'10022913318579903114'),
 'gemini_capricorn':(['17311676774383453515','4636223304383814285','7635396052154065211','4530692863652778775','15578234949760145614','15859943517777561407'],'4577625946978975734'),
 'first_day_shoes':(['4328287559290168365','10778698945635705287','11025590385710494335','3142613654896467676','13912953416884481437','3399044591307260976'],'14671794108540810458'),
 'libra_aries':(['14363790853012963176','11817173489837946450','15709743265966348348','5464563981830598491','15726296536331367410','8806893680282750844'],'14892201065456864136'),
 'sisters_photo':(['6715752889946991207','6367682017833920656','10692211211185307691','7696958303222718699','5938394091540728169','17797401575340204316'],'15864044035670965579'),
 'sagittarius_pisces':(['11378200867516965732','2535061980857602868','16750488757871631319','16266763433587733877','16065166746994380144','14382008945278125569'],'2540848535002180099'),
 'bus_waited':(['7280524144894867237','4557163221189824983','7353138752784232344','2337475910885538908','11803607550894475847','8783586085577581399'],'6369354964664372454')}
man=json.loads((BASE/'manifest.json').read_text());audit=BASE/'transport_audit';audit.mkdir(exist_ok=True);jobs=[]
for p in man['posts']:
 photo,vid=ids[p['id']]
 for c,fileid in zip(p['cards'],photo):jobs.append((c['path'],c['sha256'],'https://static.metricool.com/planner/202610/7000636-file-'+fileid+'.jpeg'))
 c=p['youtube_video'];jobs.append((c['path'],c['sha256'],'https://static.metricool.com/planner/202610/7000636-file-'+vid+'.mp4'))
def verify(j):
 path,expected,u=j
 try:
  b=get(u);got=hashlib.sha256(b).hexdigest();same=got==expected
  if not same:
   p=audit/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  return {'path':path,'url':u,'expected_sha256':expected,'actual_sha256':got,'identical':same,'bytes':len(b)}
 except Exception as e:return {'path':path,'url':u,'identical':False,'error':str(e)}
with ThreadPoolExecutor(max_workers=4) as ex:checks=list(ex.map(verify,jobs))
a={'kind':'EXACT_BYTES_TRANSPORT_CHECK','expected_files':56,'identical_files':sum(c['identical'] for c in checks),'all_identical':len(checks)==56 and all(c['identical'] for c in checks),'checks':checks,'scope':'Identity to the manually reviewed final files, not a new visual approval and not proof of publication.'}
(audit/'report.json').write_text(json.dumps(a,ensure_ascii=False,indent=2));print(json.dumps({'photo_candidates':len(ims),'audit_identical':a['identical_files'],'errors':r['errors']},ensure_ascii=False))
