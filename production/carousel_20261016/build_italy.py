"""Create Greece-Italy review candidates, never publish or grant QA approval."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from PIL import Image,ImageDraw,ImageFont,ImageOps,ImageFilter
import json,hashlib,subprocess,math,io,re
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'media/carousel_20261016';SRC=BASE/'italy_sources';OUT=BASE/'greece_italy';OUT.mkdir(parents=True,exist_ok=True)
CTA='Αν σας άρεσε, ακολουθήστε για περισσότερα.';BRAND='Ιστορίες που μας αγγίζουν'
F='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';B='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
report=json.loads((SRC/'report.json').read_text());photos={p['path']:p for p in report['photos']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def get(u):
 with urlopen(Request(u,headers={'User-Agent':'SteliosCarouselResearch/1.0 (credited Wikimedia reuse)'}),timeout=50) as r:return r.read()
def clean(t):return re.sub('<[^>]+>','',t or '').strip()
def extra(name,title):
 url='https://commons.wikimedia.org/w/api.php?'+urlencode({'action':'query','format':'json','titles':title,'prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':1600})
 page=next(iter(json.loads(get(url))['query']['pages'].values()));ii=page['imageinfo'][0];m=ii['extmetadata'];lic=clean(m.get('LicenseShortName',{}).get('value',''))
 assert any(k in lic.lower() for k in ['cc by','cc0','public domain']) and not any(k in lic.lower() for k in ['nc','nd']),lic
 im=Image.open(io.BytesIO(get(ii.get('thumburl') or ii['url']))).convert('RGB');p=OUT/name;im.save(p,quality=95,subsampling=0)
 photos[name]={'path':name,'title':page['title'],'file_page':ii['descriptionurl'],'original_url':ii['url'],'artist':clean(m.get('Artist',{}).get('value','')),'license':lic,'license_url':m.get('LicenseUrl',{}).get('value',''),'description':clean(m.get('ImageDescription',{}).get('value','')),'sha256':sha(p)}
extra('housing_final.jpg','File:Aigyptou Square Athens.JPG')
extra('education_final.jpg','File:Bologna, Biblioteca Salaborsa.jpg')
extra('health_final.jpg','File:Amalia Fleming hospital Athens.jpg')
extra('closing_final.jpg','File:Golfo de Patras 01.jpg')
def value(ds,geo,codes):
 d=json.loads((SRC/f'{ds}_{geo}.json').read_text());index=0
 for dim,size in zip(d['id'],d['size']):
  cats=d['dimension'][dim]['category']['index'];key=codes.get(dim,next(iter(cats)));index=index*size+cats[key]
 return d['value'][str(index)]
for geo,expected in [('EL',17954),('IT',33523)]:assert value('nama_10_fte',geo,{'unit':'EUR'})==expected
for geo,expected in [('EL',39.8),('IT',36.1)]:assert value('lfsa_ewhan2',geo,{'nace_r2':'TOTAL','wstatus':'EMP','worktime':'TOTAL','age':'Y20-64','sex':'T'})==expected
for geo,expected in [('EL',35.5),('IT',13.6)]:assert value('ilc_mded01',geo,{'hhcomp':'TOTAL','rskpovth':'TOTAL'})==expected
sources=[
 {'id':'salary','url':'https://ec.europa.eu/eurostat/en/web/products-eurostat-news/w/ddn-20251112-1','dataset':'nama_10_fte','definition':'2024 annual gross average full-time-adjusted salary per employee, EUR. Greece17954,Italy33523. Direct Eurostat API responses retained in italy_sources. Not net monthly pay, median salary or a job offer.'},
 {'id':'hours','url':'https://ec.europa.eu/eurostat/de/web/products-eurostat-news/w/ddn-20250514-1','dataset':'lfsa_ewhan2','definition':'2024 actual weekly working hours in main job, employed persons aged20-64, all NACE activities, both sexes, full-time and part-time together. Greece39.8,Italy36.1. Not contracted full-time hours or commuting time.'},
 {'id':'prices','url':'https://www.nsi.bg/index.php/en/statistical-data/109/360','definition':'2024 household final consumption expenditure price-level index,EU27=100. Greece86.5,Italy97.0. Preliminary Eurostat PPP snapshot17Dec2025 displayed by NSI. Not inflation and not a specific household budget. Not claimed to be the latest2026price levels.'},
 {'id':'housing','url':'https://ec.europa.eu/eurostat/databrowser/view/ilc_mded01/default/table?lang=en','dataset':'ilc_mded01','definition':'2024 share of housing costs in disposable household income; hhcompTOTAL,rskpovthTOTAL,unitPC. Greece35.5%,Italy13.6%. Exact direct-API values. Not average rent, only renters, or percentage of households exceeding40%costs.'},
 {'id':'education','url':'https://www.oecd.org/en/publications/pisa-2022-results-volume-i_53f23881-en/full-report/overview-of-performance-trends_ae540546.html','definition':'OECD PISA2022 mathematics mean score among15-year-old students: Greece430,Italy471, rounded to whole points. Country snapshot tables. Not an overall ranking of schools, education systems or universities.'},
 {'id':'health','url':'https://knowledge4policy.ec.europa.eu/health-promotion-knowledge-gateway/health-inequalities-rates-1_en','definition':'Eurostat2023 life expectancy at birth, both sexes: Greece81.6years,Italy83.8years. The first table column is explicitly2023. Multiple determinants; not a score of hospital quality.'},
 {'id':'roads','url':'https://transport.ec.europa.eu/news-events/news/road-safety-statistics-2024-progress-continues-amid-persistent-challenges-2025-10-17_en','definition':'Final2024 road deaths per million residents: Greece64,Italy51. Denominator is population, not distance driven. Does not rank all infrastructure.'},
 {'id':'digital_greece','url':'https://digital-strategy.ec.europa.eu/en/factpages/greece-2025-digital-decade-country-report','definition':'Special Eurobarometer Digital Decade2025:78%of Greek citizens say digitalisation of public and private services makes life easier. Opinion survey, not an objective service-quality score.'},
 {'id':'digital_italy','url':'https://digital-strategy.ec.europa.eu/en/factpages/italy-2025-digital-decade-country-report','definition':'Same2025Eurobarometer item:73%of Italian citizens. No claim of statistical significance or objective country ranking.'}
]
cards=[
 {'heading':'ΕΛΛΑΔΑ VS ΙΤΑΛΙΑ','body':'Ο μισθός δεν λέει όλη την ιστορία.\n8 δείκτες, χωρίς στερεότυπα.','note':'Δέκα κάρτες με συγκρίσιμα στοιχεία ανά δείκτη και το έτος τους. Δεν είναι ενιαία κατάταξη χωρών.','source':'Στοιχεία 2022–2025 · Πηγές στην περιγραφή'},
 {'heading':'ΜΙΣΘΟΣ · 2024','label':'Μέση ετήσια μικτή αμοιβή','gr':'17.954 €','it':'33.523 €','note':'Προσαρμογή σε πλήρη απασχόληση. Όχι καθαρά χρήματα στην τσέπη ούτε εγγυημένος μισθός.','source':'Eurostat · nama_10_fte'},
 {'heading':'ΩΡΕΣ ΕΡΓΑΣΙΑΣ · 2024','label':'Πραγματικές ώρες ανά εβδομάδα','gr':'39,8 ώρες','it':'36,1 ώρες','note':'Κύρια δουλειά, ηλικίες 20–64, πλήρης ΚΑΙ μερική απασχόληση. Όχι το συμβατικό ωράριο όλων.','source':'Eurostat · lfsa_ewhan2'},
 {'heading':'ΕΠΙΠΕΔΟ ΤΙΜΩΝ · 2024','label':'Κατανάλωση νοικοκυριών · ΕΕ = 100','gr':'86,5','it':'97,0','note':'Προσωρινός δείκτης τιμών, όχι πληθωρισμός. Χαμηλότερες τιμές δεν σημαίνουν από μόνες τους μεγαλύτερη άνεση.','source':'Eurostat / NSI · στοιχεία 17.12.2025'},
 {'heading':'ΣΤΕΓΑΣΗ · 2024','label':'Κόστος στέγασης στο διαθέσιμο εισόδημα','gr':'35,5%','it':'13,6%','note':'Για το σύνολο των νοικοκυριών, όχι μόνο ενοικιαστές. Δεν είναι η μέση τιμή ενοικίου.','source':'Eurostat · ilc_mded01'},
 {'heading':'ΠΑΙΔΕΙΑ · PISA 2022','label':'Μαθηματικά · μέση επίδοση 15χρονων','gr':'430 μονάδες','it':'471 μονάδες','note':'Ένας συγκεκριμένος μαθησιακός δείκτης. Δεν βαθμολογεί ολόκληρη την παιδεία ή τα πανεπιστήμια.','source':'OECD · PISA 2022'},
 {'heading':'ΥΓΕΙΑ · 2023','label':'Προσδόκιμο ζωής στη γέννηση','gr':'81,6 χρόνια','it':'83,8 χρόνια','note':'Και τα δύο φύλα. Επηρεάζεται από πολλούς παράγοντες· δεν είναι βαθμολογία νοσοκομείων.','source':'Eurostat · Ευρωπαϊκή Επιτροπή / K4P'},
 {'heading':'ΟΔΙΚΗ ΑΣΦΑΛΕΙΑ · 2024','label':'Νεκροί σε τροχαία ανά εκατομμύριο κατοίκων','gr':'64','it':'51','note':'Εδώ το μικρότερο είναι καλύτερο. Μετρά κατοίκους, όχι χιλιόμετρα οδήγησης ή το σύνολο των υποδομών.','source':'Ευρωπαϊκή Επιτροπή · CARE 2024'},
 {'heading':'ΨΗΦΙΑΚΕΣ ΥΠΗΡΕΣΙΕΣ · 2025','label':'«Η ψηφιοποίηση κάνει τη ζωή ευκολότερη»','gr':'78%','it':'73%','note':'Γνώμη πολιτών για δημόσιες και ιδιωτικές υπηρεσίες. Όχι αντικειμενικός βαθμός ποιότητας υπηρεσιών.','source':'Ειδικό Ευρωβαρόμετρο · Digital Decade 2025'},
 {'heading':'ΤΙ ΜΕΤΡΑ ΠΕΡΙΣΣΟΤΕΡΟ ΓΙΑ ΣΕΝΑ;','body':'Μισθός, σπίτι, χρόνος, υπηρεσίες — και οι άνθρωποί σου.\nΤι θα έβαζες πρώτο;','note':CTA,'source':'Ορισμοί, πηγές και άδειες στην περιγραφή'}
]
selected=['cover_1.jpg','salary_1.jpg','hours_2.jpg','prices_2.jpg','housing_final.jpg','education_final.jpg','health_final.jpg','roads_2.jpg','digital_1.jpg','closing_final.jpg']
font=lambda size,b=False:ImageFont.truetype(B if b else F,size)
def wrap(t,ft,width):
 out=[]
 for para in t.split('\n'):
  line=''
  for word in para.split():
   proposed=(line+' '+word).strip()
   if ft.getlength(proposed)>width:
    assert line,'Word too wide';out.append(line);line=word
   else:line=proposed
  if line:out.append(line)
 return out
def text(im,t,box,maxsize=42,minsize=30,bold=False):
 x,y,w,h=box
 for size in range(maxsize,minsize-1,-1):
  ft=font(size,bold);lines=wrap(t,ft,w);step=math.ceil(size*1.25)
  if len(lines)*step<=h:break
 else:raise ValueError('Unfittable text: '+t)
 d=ImageDraw.Draw(im)
 for line in lines:d.text((x,y),line,font=ft,fill=(25,32,38));y+=step
 return size
manifest={'id':'greece_italy','title':'Ελλάδα VS Ιταλία: πέρα από τα στερεότυπα','date':'2026-10-16','time':'18:30','timezone':'Europe/Athens','brand_id':7076410,'qa_status':'NEEDS_EXACT_FINAL_REVIEW','fingerprint':'greece_vs_country|italy|salary_hours_prices_housing_education_health_roads_digital','cards':[],'sources':sources,'photographs':[],'real_photographs':True,'is_ai_generated_visuals':False}
allcards=[];frames=[]
for i,(c,name) in enumerate(zip(cards,selected)):
 p=photos[name];manifest['photographs'].append(p);sourcepath=(OUT/name) if (OUT/name).exists() else SRC/name
 photo=Image.open(sourcepath).convert('RGB');im=Image.new('RGB',(1080,1080),(247,243,235));im.paste(ImageOps.fit(photo,(1080,420)).filter(ImageFilter.GaussianBlur(28)),(0,0));ph=ImageOps.contain(photo,(1080,420),Image.Resampling.LANCZOS);im.paste(ph,((1080-ph.width)//2,(420-ph.height)//2))
 d=ImageDraw.Draw(im);d.rounded_rectangle((936,20,1057,77),14,fill=(17,23,29));d.text((950,31),f'{i+1:02d}/10',font=font(27,True),fill='white')
 layout={'heading_font':text(im,c['heading'],(45,443,990,105),45,34,True)}
 if 'gr' in c:
  layout['label_font']=text(im,c['label'],(45,550,990,90),37,31)
  text(im,'Ελλάδα: '+c['gr'],(45,650,990,78),57,45,True);text(im,'Ιταλία: '+c['it'],(45,731,990,78),57,45,True)
  layout['note_font']=text(im,c['note'],(45,826,990,140),34,30)
 else:
  layout['body_font']=text(im,c['body'],(45,571,990,245),47,39,True)
  layout['note_font']=text(im,c['note'],(45,850,990,125),35,30,i==9)
 text(im,c['source'],(45,983,990,40),25,21)
 text(im,'Φωτ.: '+p['artist']+' · '+p['license'],(45,1031,990,39),22,16)
 target=OUT/f'card_{i+1:02d}.jpg';im.save(target,quality=95,subsampling=0);exact=Image.open(target).convert('RGB');allcards.append(exact)
 manifest['cards'].append({'path':str(target.relative_to(BASE)),'sha256':sha(target),'copy':c,'photo':name,'layout':layout,'duration_seconds':16})
 v=Image.new('RGB',(1080,1920),(235,232,224));text(v,'Ελλάδα VS Ιταλία',(70,178,940,145),62,50,True);v.paste(exact.resize((1020,1020),Image.Resampling.LANCZOS),(30,445));text(v,'10 κάρτες · Στοιχεία με πηγές και έτη',(70,1560,940,110),39,34,True);text(v,BRAND,(70,1690,940,90),39,34)
 frame=OUT/f'frame_{i+1:02d}.png';v.save(frame);frames.append(frame)
concat=OUT/'slides.ffconcat';parts=['ffconcat version 1.0']
for frame in frames:parts.extend([f"file '{frame}'",'duration 16'])
parts.append(f"file '{frames[-1]}'");concat.write_text('\n'.join(parts)+'\n');video=OUT/'youtube_vertical.mp4'
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-safe','0','-i',str(concat),'-vf','tpad=stop_mode=clone:stop_duration=2,fps=24','-t','160','-c:v','libx264','-preset','ultrafast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart','-an',str(video)],check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)]));assert abs(float(probe['format']['duration'])-160)<.05 and not any(s['codec_type']=='audio' for s in probe['streams'])
manifest['youtube_video']={'path':str(video.relative_to(BASE)),'sha256':sha(video),'duration_seconds':160,'card_durations':[16]*10,'audio_streams':0,'width':1080,'height':1920,'fps':24}
def contact(ims,path,w,cols):
 h=round(w*ims[0].height/ims[0].width);sheet=Image.new('RGB',(w*cols,h*math.ceil(len(ims)/cols)),'white')
 for i,im in enumerate(ims):sheet.paste(im.resize((w,h),Image.Resampling.LANCZOS),((i%cols)*w,(i//cols)*h))
 sheet.save(path,quality=95)
contact(allcards,OUT/'cards_review.jpg',540,2);decoded=[]
for i in range(10):
 p=OUT/f'encoded_frame_{i+1:02d}.jpg';subprocess.run(['ffmpeg','-loglevel','error','-y','-ss',str(i*16+8),'-i',str(video),'-frames:v','1','-q:v','2',str(p)],check=True);decoded.append(Image.open(p).convert('RGB'))
contact(decoded,OUT/'encoded_video_review.jpg',360,2)
for f in frames:f.unlink()
concat.unlink()
manifest['caption']='Ο μισθός δεν λέει όλη την ιστορία.\n\nΕλλάδα VS Ιταλία: δέκα κάρτες για αποδοχές, εργασία, τιμές, στέγαση, παιδεία, υγεία, οδική ασφάλεια και ψηφιακές υπηρεσίες. Κάθε ζεύγος αφορά τον ίδιο δείκτη και έτος. Τα στοιχεία είναι 2022–2025, όχι ισχυρισμός σημερινών τιμών ή συνολική κατάταξη χωρών.\n\nΠοιος παράγοντας μετρά περισσότερο για εσένα;\n\nΠηγές: Eurostat, OECD, Ευρωπαϊκή Επιτροπή, Ειδικό Ευρωβαρόμετρο. Αναλυτικοί ορισμοί και άδειες πραγματικών φωτογραφιών: https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/main/media/carousel_20261016/greece_italy/SOURCES.md\n\nΟι φωτογραφίες είναι εικονογραφική συνοδεία και δεν αποδεικνύουν τα στατιστικά ή τρέχουσες τιμές καταστημάτων. Δεν είναι εικόνες παραγόμενες με AI.\n\n'+CTA+'\n\n#Ελλάδα #Ιταλία #ΚόστοςΖωής #Καθημερινότητα #ΙστορίεςΠουΜαςΑγγίζουν'
assert len([w for w in manifest['caption'].split() if w.startswith('#')])==5
md=['# Ελλάδα VS Ιταλία — πηγές και άδειες','Για τη δημοσίευση της 16ης Οκτωβρίου 2026. Κάθε ζεύγος χωρών συγκρίνεται με τον ίδιο δείκτη και έτος. Τα διαφορετικά έτη 2022–2025 αναγράφονται καθαρά. Δεν πρόκειται για κατάταξη ευημερίας, για εξατομικευμένη οικονομική συμβουλή ή για ισχυρισμό των πιο πρόσφατων τιμών.','## Πρωτογενή δεδομένα']
for s in sources:md += ['### '+s['id'],s['definition'],s['url']]
md += ['### Αποθηκευμένα πρωτογενή δεδομένα Eurostat']
for s in report['sources']:md += [s['url'],'SHA256: '+s['sha256']]
md += ['## Φωτογραφίες και άδειες','Εικονογραφικές φωτογραφίες πραγματικών τόπων/αντικειμένων από διαφορετικά έτη. Η βιβλιοθήκη συνοδεύει το θέμα της μάθησης, όχι συγκεκριμένη μέτρηση PISA. Ο σιδηροδρομικός υπάλληλος συνοδεύει το θέμα της εργασίας, όχι στοιχεία μετακίνησης. Οι φωτογραφίες νοσοκομείου, αγοράς και κατοικιών δεν αποδεικνύουν την επίδοση ή την τιμή ενός συγκεκριμένου οργανισμού.','Προσαρμογές: αλλαγή μεγέθους, θολωμένα περιθώρια και προσθήκη ελληνικού κειμένου. Δεν υπονοείται υποστήριξη από τους φωτογράφους. Οι κάρτες που βασίζονται σε CC BY-SA διατίθενται με την αντίστοιχη ή συμβατή άδεια· το συνολικό βίντεο CC BY-SA4.0. Το νέο κείμενο/διάταξη των λοιπών καρτών CC BY4.0, διατηρώντας τις αρχικές άδειες των φωτογραφιών.','https://creativecommons.org/licenses/by-sa/4.0/','https://creativecommons.org/licenses/by/4.0/']
for i,p in enumerate(manifest['photographs']):md += [f"### Κάρτα {i+1}: {p['title']}",f"Φωτογράφος: {p['artist']} — {p['license']}",p['file_page'],p.get('license_url',''),p['original_url']]
(OUT/'SOURCES.md').write_text('\n\n'.join(md)+'\n');(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('Ten photographic cards and160s silent video rendered. NEEDS_EXACT_FINAL_REVIEW.')
