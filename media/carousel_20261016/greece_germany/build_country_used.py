"""Build a ten-card country comparison. Never publish or auto-approve the output."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from PIL import Image,ImageDraw,ImageFont,ImageOps,ImageFilter
import json,hashlib,subprocess,math,io,re
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'media/carousel_20261016';SRC=BASE/'country_sources';OUT=BASE/'greece_germany';OUT.mkdir(parents=True,exist_ok=True)
CTA='Αν σας άρεσε, ακολουθήστε για περισσότερα.'
BRAND='Ιστορίες που μας αγγίζουν'
F='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';B='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
report=json.loads((SRC/'source_report.json').read_text())
def get(url):
 with urlopen(Request(url,headers={'User-Agent':'SteliosCarouselResearch/1.0 (credited Wikimedia reuse)'}),timeout=50) as r:return r.read()
# A specifically sourced work-desk photograph, rather than an irrelevant balloon at a station.
u='https://commons.wikimedia.org/w/api.php?'+urlencode({'action':'query','format':'json','titles':'File:Working at office (Unsplash).jpg','prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':1400})
p=next(iter(json.loads(get(u))['query']['pages'].values()));ii=p['imageinfo'][0];em=ii['extmetadata']
clean=lambda s:re.sub('<[^>]+>','',s or '').strip()
lic=clean(em.get('LicenseShortName',{}).get('value',''))
assert lic in ['CC0','Public domain'] or lic.startswith('CC BY'), lic
im=Image.open(io.BytesIO(get(ii.get('thumburl') or ii['url']))).convert('RGB');im.save(SRC/'work_office.jpg',quality=95,subsampling=0)
report['photo_candidates'].append({'path':'work_office.jpg','title':p['title'],'file_page':ii['descriptionurl'],'original_url':ii['url'],'license':lic,'license_url':em.get('LicenseUrl',{}).get('value',''),'artist':clean(em.get('Artist',{}).get('value','')),'description':clean(em.get('ImageDescription',{}).get('value',''))})
# Both raw salary responses were fetched directly from Eurostat and inspected.
for geo,val in [('EL',17954),('DE',53791)]:
 d=json.loads((SRC/f'salary_{geo}.json').read_text());assert d['dimension']['unit']['category']['index']['EUR']==0 and d['value']['0']==val
selected=['cover_1.jpg','salary_1.jpg','work_office.jpg','prices_1.jpg','housing_2.jpg','digital_1.jpg','health_2.jpg','roads_1.jpg','digital_2.jpg','closing_1.jpg']
sources=[
 {'id':'salary','url':'https://ec.europa.eu/eurostat/en/web/products-eurostat-news/w/ddn-20251112-1','dataset':'nama_10_fte','definition':'2024 annual gross average full-time-adjusted salary per employee, EUR. Greece 17954; Germany 53791. Direct Eurostat API values saved as salary_EL.json and salary_DE.json; not net wages or a job offer.'},
 {'id':'hours','url':'https://ec.europa.eu/eurostat/de/web/products-eurostat-news/w/ddn-20250514-1','definition':'2024 actual weekly hours in main job, employed persons aged 20-64, full-time and part-time together. Greece39.8/Germany33.9; not contractual full-time hours or commuting.'},
 {'id':'prices','url':'https://www.nsi.bg/index.php/en/statistical-data/109/360','definition':'2024 household final consumption expenditure price-level index, EU27=100. Greece86.5/Germany108.8. Preliminary values from Eurostat PPP snapshot17Dec2025. Not inflation or an individual cost-of-living budget.'},
 {'id':'housing','url':'https://ec.europa.eu/eurostat/fr/web/interactive-publications/housing-2025','definition':'2024 housing costs as share of disposable household income. Rounded values Greece36%,Germany25%; not the percentage of households exceeding a40%cost threshold.'},
 {'id':'education','url':'https://www.destatis.de/DE/Themen/Laender-Regionen/Internationales/Thema/bevoelkerung-arbeit-soziales/bildung/PISA2022.html','definition':'OECD PISA2022 mathematics mean score of15-year-olds: Greece430,Germany475 rounded. Not a comprehensive ranking of education or universities.'},
 {'id':'health','url':'https://knowledge-for-policy.ec.europa.eu/node/73222_el','definition':'Eurostat2023 life expectancy at birth, both sexes: Greece81.6,Germany81.2years. Multiple determinants; not a ranking of hospital quality.'},
 {'id':'roads','url':'https://transport.ec.europa.eu/news-events/news/road-safety-statistics-2024-progress-continues-amid-persistent-challenges-2025-10-17_en','definition':'2024 road fatalities per million residents: Greece64,Germany33. Population denominator, not distance driven or total infrastructure quality.'},
 {'id':'digital_greece','url':'https://digital-strategy.ec.europa.eu/en/factpages/greece-2025-digital-decade-country-report','definition':'SpecialEurobarometer2025:78%ofGreek citizens consider digitisation of public and private services makes life easier. Opinion survey, not objective service-quality score.'},
 {'id':'digital_germany','url':'https://digital-strategy.ec.europa.eu/en/factpages/germany-2025-digital-decade-country-report','definition':'Same2025Eurobarometer item:74%ofGerman citizens. Do not interpret the4point difference as statistical significance or an objective country ranking.'}
]
cards=[
 {'heading':'ΕΛΛΑΔΑ VS ΓΕΡΜΑΝΙΑ','body':'Ο μεγαλύτερος μισθός λέει όλη την ιστορία;\nΔέκα κάρτες, οκτώ όψεις της καθημερινότητας — πέρα από τα στερεότυπα.','note':'Συγκρίσιμα στοιχεία ανά δείκτη, με το έτος τους. Δεν είναι ενιαία κατάταξη χωρών.','source':'Στοιχεία 2023–2025 · Πηγές στην περιγραφή'},
 {'heading':'ΜΙΣΘΟΣ · 2024','label':'Μέση ετήσια μικτή αμοιβή','gr':'17.954 €','de':'53.791 €','note':'Προσαρμογή σε πλήρη απασχόληση. Όχι καθαρά χρήματα στην τσέπη ούτε εγγυημένος μισθός.','source':'Eurostat · nama_10_fte'},
 {'heading':'ΩΡΕΣ ΕΡΓΑΣΙΑΣ · 2024','label':'Πραγματικές ώρες ανά εβδομάδα','gr':'39,8 ώρες','de':'33,9 ώρες','note':'Κύρια δουλειά, ηλικίες 20–64, πλήρης ΚΑΙ μερική απασχόληση. Όχι το συμβατικό ωράριο όλων.','source':'Eurostat · lfsa_ewhan2'},
 {'heading':'ΕΠΙΠΕΔΟ ΤΙΜΩΝ · 2024','label':'Κατανάλωση νοικοκυριών · ΕΕ = 100','gr':'86,5','de':'108,8','note':'Προσωρινός δείκτης τιμών, όχι πληθωρισμός. Οι χαμηλότερες τιμές δεν αρκούν χωρίς σύγκριση εισοδήματος.','source':'Eurostat / NSI · ενημέρωση 17.12.2025'},
 {'heading':'ΣΤΕΓΑΣΗ · 2024','label':'Κόστος στέγασης στο διαθέσιμο εισόδημα','gr':'36%','de':'25%','note':'Μέσο μερίδιο εισοδήματος των νοικοκυριών, με στρογγυλοποίηση. Δεν είναι η μέση τιμή ενοικίου.','source':'Eurostat · Housing in Europe 2025'},
 {'heading':'ΠΑΙΔΕΙΑ · PISA 2022','label':'Μαθηματικά · μέση επίδοση 15χρονων','gr':'430 μονάδες','de':'475 μονάδες','note':'Ένας συγκεκριμένος μαθησιακός δείκτης. Δεν βαθμολογεί ολόκληρη την παιδεία ή τα πανεπιστήμια.','source':'OECD PISA 2022 · πίνακας Destatis'},
 {'heading':'ΥΓΕΙΑ · 2023','label':'Προσδόκιμο ζωής στη γέννηση','gr':'81,6 χρόνια','de':'81,2 χρόνια','note':'Και τα δύο φύλα. Επηρεάζεται από πολλούς παράγοντες· δεν είναι βαθμολογία νοσοκομείων.','source':'Eurostat · Ευρωπαϊκή Επιτροπή / K4P'},
 {'heading':'ΟΔΙΚΗ ΑΣΦΑΛΕΙΑ · 2024','label':'Νεκροί σε τροχαία ανά εκατομμύριο κατοίκων','gr':'64','de':'33','note':'Εδώ το μικρότερο είναι καλύτερο. Ο δείκτης αφορά κατοίκους, όχι χιλιόμετρα οδήγησης ή όλες τις υποδομές.','source':'Ευρωπαϊκή Επιτροπή · CARE 2024'},
 {'heading':'ΨΗΦΙΑΚΗ ΚΑΘΗΜΕΡΙΝΟΤΗΤΑ · 2025','label':'«Η ψηφιοποίηση κάνει τη ζωή ευκολότερη»','gr':'78%','de':'74%','note':'Γνώμη πολιτών για δημόσιες και ιδιωτικές υπηρεσίες. Όχι αντικειμενικός βαθμός ποιότητας των υπηρεσιών.','source':'Ειδικό Ευρωβαρόμετρο · Digital Decade 2025'},
 {'heading':'ΔΕΝ ΥΠΑΡΧΕΙ ΜΟΝΟ ΕΝΑΣ ΑΡΙΘΜΟΣ','body':'Μισθός, στέγαση, χρόνος, υπηρεσίες — και οι άνθρωποί σου.\nΠοιο από αυτά θα βάραινε περισσότερο στη δική σου επιλογή;','note':CTA,'source':'Πηγές, ορισμοί και άδειες φωτογραφιών στην περιγραφή'}
]
font=lambda s,b=False:ImageFont.truetype(B if b else F,s)
def wrap(text,ft,width):
 out=[]
 for para in text.split('\n'):
  line=''
  for w in para.split():
   new=(line+' '+w).strip()
   if ft.getlength(new)>width:out.append(line);line=w
   else:line=new
  if line:out.append(line)
 return out
def text(im,t,box,maxsize=42,minsize=30,bold=False):
 x,y,w,h=box
 for sz in range(maxsize,minsize-1,-1):
  ft=font(sz,bold);ls=wrap(t,ft,w);step=math.ceil(sz*1.25)
  if len(ls)*step<=h:break
 else:raise ValueError('Text does not fit: '+t)
 d=ImageDraw.Draw(im)
 for line in ls:d.text((x,y),line,font=ft,fill=(25,32,38));y+=step
 return sz
manifest={'id':'greece_germany','title':'Ελλάδα VS Γερμανία: πέρα από τον μισθό','date':'2026-10-16','time':'18:30','brand_id':7076410,'qa_status':'NEEDS_EXACT_FINAL_REVIEW','cards':[],'sources':sources,'photographs':[]}

cards[0]['body']='Ο μεγαλύτερος μισθός λέει όλη την ιστορία;\nΔέκα κάρτες για τη ζωή στις δύο χώρες.'
cards[0]['source']='Στοιχεία 2023–2025 · Πηγές στην περιγραφή'
cards[3].update(heading='ΕΠΙΠΕΔΟ ΤΙΜΩΝ · 2025',gr='87,4',de='108,3',source='Eurostat / Statistics Norway · προσωρινά 2025')
sources[2]={'id':'prices','url':'https://www.ssb.no/en/priser-og-prisindekser/konsumpriser/statistikk/sammenlikning-av-prisniva-i-europa','definition':'2025 preliminary household final consumption price-level indices, EU27=100: Greece87.4/Germany108.3. Statistics Norway, source Eurostat, updated19June2026. Not inflation or purchasing power.'}
cards[5].update(heading='ΠΑΙΔΕΙΑ · PISA 2025',label='15χρονοι με βασικό επίπεδο στα μαθηματικά',gr='50%',de='66%',note='Επίπεδο 2 και πάνω. Ένας μαθησιακός δείκτης, όχι συνολική βαθμολογία της παιδείας.',source='OECD · PISA 2025 · σημειώματα χωρών')
sources[4]={'id':'education','url':'https://www.oecd.org/en/publications/pisa-2025-results-volume-i-country-notes_2d4ff9ea-en/greece_dd7e428b-en.html','germany_url':'https://www.oecd.org/de/publications/pisa-2025-ergebnisse-band-i_eade94cd-de/deutschland_8a1ce578-de.html','definition':'PISA2025, share of15-year-old students reaching at least Level2 in mathematics: Greece50%,Germany66%. Both current OECD country notes verified15Oct2026. Not a comprehensive education ranking.'}
cards[6].update(gr='81,8 χρόνια',de='81,1 χρόνια',source='OECD · Health at a Glance 2025 · στοιχεία 2023')
sources[5]={'id':'health','url':'https://www.oecd.org/en/publications/health-at-a-glance-2025_8f9e3f98-en/full-report/indicator-overview-country-dashboards-and-major-trends_368ac397.html','definition':'2023 life expectancy at birth, both sexes, OECD Health at a Glance2025 dashboard: Greece81.8,Germany81.1years. Not hospital-quality ranking.'}
cards[9]['body']='Μισθός, σπίτι, χρόνος, υπηρεσίες.\nΤι μετρά περισσότερο στη δική σου ζωή;'
manifest['date']='2026-10-15'
manifest['time']=None
manifest['reservation_token']='cf0080df-7787-48b4-bf2a-f41d0f7263b0'
manifest['publication_requested_before']='2026-10-16T00:00:00+03:00'

allcards=[];frames=[]
for i,(c,f) in enumerate(zip(cards,selected)):
 p=next(p for p in report['photo_candidates'] if p['path']==f);manifest['photographs'].append(p)
 photo=Image.open(SRC/f).convert('RGB');im=Image.new('RGB',(1080,1080),(247,243,235))
 bg=ImageOps.fit(photo,(1080,420)).filter(ImageFilter.GaussianBlur(26));im.paste(bg,(0,0))
 ph=ImageOps.contain(photo,(1080,420));im.paste(ph,((1080-ph.width)//2,(420-ph.height)//2))
 d=ImageDraw.Draw(im);d.rounded_rectangle((936,20,1057,77),14,fill=(17,23,29));d.text((950,31),f'{i+1:02d}/10',font=font(27,True),fill='white')
 text(im,c['heading'],(45,447,990,100),45,33,True)
 if 'gr' in c:
  text(im,c['label'],(45,554,990,87),36,31)
  text(im,'Ελλάδα: '+c['gr'],(45,648,990,80),57,45,True)
  text(im,'Γερμανία: '+c['de'],(45,730,990,80),57,45,True)
  text(im,c['note'],(45,827,990,139),34,29)
 else:
  text(im,c['body'],(45,565,990,250),46,36,True)
  text(im,c['note'],(45,846,990,130),36,30,i==9)
 text(im,c['source'],(45,983,990,42),25,21)
 artist=p['artist'].replace(' (www.c-w-design.de)','').replace(' (Tupungato) Photo portfolio','').replace(' fredmarriage','')
 text(im,'Φωτ.: '+artist+' · '+p['license']+' · Προσαρμογή: '+BRAND,(45,1031,990,38),21,15)
 path=OUT/f'card_{i+1:02d}.jpg';im.save(path,quality=95,subsampling=0)
 exact=Image.open(path).convert('RGB');allcards.append(exact)
 manifest['cards'].append({'path':str(path.relative_to(BASE)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'copy':c,'photograph':f})
 v=Image.new('RGB',(1080,1920),(235,232,224));text(v,'Ελλάδα VS Γερμανία',(70,178,940,145),59,48,True);v.paste(exact.resize((1020,1020),Image.Resampling.LANCZOS),(30,445))
 text(v,'10 κάρτες · Στοιχεία με πηγές και έτη',(70,1560,940,110),39,34,True);text(v,BRAND,(70,1690,940,90),39,34)
 fp=OUT/f'frame_{i+1:02d}.png';v.save(fp);frames.append(fp)
concat=OUT/'slides.ffconcat';parts=['ffconcat version 1.0']
for f in frames:parts.extend([f"file '{f}'",'duration 16'])
parts.append(f"file '{frames[-1]}'");concat.write_text('\n'.join(parts)+'\n')
v=OUT/'youtube_vertical.mp4'
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-safe','0','-i',str(concat),'-vf','tpad=stop_mode=clone:stop_duration=2,fps=24','-t','160','-c:v','libx264','-preset','ultrafast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart','-an',str(v)],check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(v)]));assert abs(float(probe['format']['duration'])-160)<.05 and not any(s['codec_type']=='audio' for s in probe['streams'])
manifest['youtube_video']={'path':str(v.relative_to(BASE)),'sha256':hashlib.sha256(v.read_bytes()).hexdigest(),'duration_seconds':160,'card_durations':[16]*10,'audio_streams':0,'width':1080,'height':1920}
def contact(ims,out,width,cols):
 h=round(width*ims[0].height/ims[0].width);sheet=Image.new('RGB',(width*cols,h*math.ceil(len(ims)/cols)),'white')
 for i,im in enumerate(ims):sheet.paste(im.resize((width,h)),((i%cols)*width,(i//cols)*h))
 sheet.save(out,quality=95)
contact(allcards,OUT/'cards_review.jpg',540,2)
dec=[]
for i in range(10):
 p=OUT/f'encoded_frame_{i+1:02d}.jpg';subprocess.run(['ffmpeg','-loglevel','error','-y','-ss',str(i*16+8),'-i',str(v),'-frames:v','1','-q:v','2',str(p)],check=True);dec.append(Image.open(p).convert('RGB'))
contact(dec,OUT/'encoded_video_review.jpg',360,2)
for f in frames:f.unlink()
concat.unlink()
manifest['caption']='Ο μεγαλύτερος μισθός λέει όλη την ιστορία;\n\nΕλλάδα VS Γερμανία: ένα καρουζέλ δέκα καρτών για αποδοχές, εργασία, τιμές, στέγαση, παιδεία, υγεία, οδική ασφάλεια και ψηφιακή καθημερινότητα. Κάθε δείκτης έχει το δικό του έτος (2023–2025) και τον ορισμό του. Δεν είναι συνολική κατάταξη χωρών ή προσωπική οικονομική συμβουλή.\n\nΠοιος παράγοντας μετρά περισσότερο για εσένα;\n\nΠηγές: Eurostat, OECD/Destatis, Ευρωπαϊκή Επιτροπή, Ευρωβαρόμετρο. Αναλυτικοί ορισμοί, πρωτογενείς σύνδεσμοι και άδειες πραγματικών φωτογραφιών: https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/main/media/carousel_20261016/greece_germany/SOURCES.md\n\nΟι φωτογραφίες είναι εικονογραφική συνοδεία, όχι απόδειξη των στατιστικών ή τρέχουσες τιμές καταστημάτων. Δεν είναι εικόνες παραγόμενες με AI.\n\n'+CTA+'\n\n#Ελλάδα #Γερμανία #ΚόστοςΖωής #Καθημερινότητα #ΙστορίεςΠουΜαςΑγγίζουν'
md=['# Ελλάδα VS Γερμανία — πηγές, ορισμοί και φωτογραφίες','Εκδοτική σύγκριση για15/10/2026. Κάθε ζεύγος χωρών αφορά τον ίδιο δείκτη και έτος. Δεν είναι ενιαίος βαθμός ευημερίας.','## Πρωτογενή δεδομένα']
for s in sources:md+=['### '+s['id'],s['definition'],s['url'],s.get('germany_url','')]
md+=['## Φωτογραφίες και άδειες','Οι φωτογραφίες είναι εικονογραφικές και ενδέχεται να έχουν παλαιότερη ημερομηνία. Τα βιβλία/γραφεία συμβολίζουν μάθηση/εργασία και δεν παρουσιάζονται ως φωτογραφίες συγκεκριμένου ελληνικού ή γερμανικού εκπαιδευτικού ιδρύματος. Δεν υπονοείται υποστήριξη από φωτογράφους.','Προσαρμογές: αλλαγή μεγέθους, θολωμένο περιθώριο, προσθήκη ελληνικού κειμένου και διάταξης. Κάθε προσαρμοσμένη κάρτα διατίθεται με την ίδια άδεια CC BY-SA όπου αυτή απαιτείται· οι υπόλοιπες με CC BY4.0 για το νέο κείμενο/διάταξη, διατηρώντας τα δικαιώματα του αρχικού φωτογράφου. Το συνολικό βίντεο, που συνδυάζει τις κάρτες, διατίθεται με CC BY-SA4.0. Οι πρωτότυπες CC0φωτογραφίες παραμένουν CC0.','Άδειες: https://creativecommons.org/licenses/by-sa/4.0/ · https://creativecommons.org/licenses/by/4.0/']
for i,p in enumerate(manifest['photographs']):md += [f"### Κάρτα {i+1}: {p['title']}",f"Φωτογράφος: {p['artist']} — {p['license']}",p['file_page'],p.get('license_url',''),p['original_url']]
(OUT/'SOURCES.md').write_text('\n\n'.join(md)+'\n');(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('Created10cards and160-second video; exact final review REQUIRED')
