#!/usr/bin/env python3
"""Assemble verified NASA photographs and exact explanatory lunar diagrams."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import copy, hashlib, json, math
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'production_20261009_platform_specific/recovery/youtube-02'
DIAGRAMS=BASE/'diagrams'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
INK='#142E41'; BLUE='#1475A0'; TEAL='#00877D'; LIGHT='#E9F3F6'
PAGE='https://www.nasa.gov/missions/laser-beams-reflected-between-earth-and-moon-boost-science/'
POLICY='https://www.nasa.gov/nasa-brand-center/images-and-media/'
def text(d,s,x,y,size=44,fill=INK,bold=False,anchor='mt'):
 f=ImageFont.truetype(BOLD if bold else FONT,size)
 if d.textlength(s,font=f)>1160: raise ValueError('Text too wide: '+s)
 d.text((x,y),s,font=f,fill=fill,anchor=anchor)
def canvas(title,subtitle):
 im=Image.new('RGB',(1280,1280),'#F7FBFD');d=ImageDraw.Draw(im)
 d.rounded_rectangle((30,30,1250,1250),radius=36,fill='white',outline='#D8E8EE',width=3)
 text(d,title,640,95,54,bold=True);text(d,subtitle,640,190,31,fill='#58717E')
 return im,d
def arrow(d,a,b,color=BLUE,width=7):
 d.line((*a,*b),fill=color,width=width)
 angle=math.atan2(b[1]-a[1],b[0]-a[0]);size=24
 pts=[b,(b[0]-size*math.cos(angle-.5),b[1]-size*math.sin(angle-.5)),(b[0]-size*math.cos(angle+.5),b[1]-size*math.sin(angle+.5))]
 d.polygon(pts,fill=color)
def save_diagram(im,name,label,description,sources):
 DIAGRAMS.mkdir(parents=True,exist_ok=True);p=DIAGRAMS/name;im.save(p)
 return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'dimensions_px':[1280,1280],'kind':'explanatory_diagram','not_a_photograph':True,'not_measured_data':True,'original_user_composition':True,'creator':'Ιστορίες που μας αγγίζουν','creator_display':'Ιστορίες που μας αγγίζουν','rightsholder':'Ιστορίες που μας αγγίζουν','copyright_statement':'Original explanatory composition made for this requested video. The original contribution is offered under CC BY 4.0.','license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/','source_page_url':sources[0],'scientific_source_urls':sources,'historical_context':description,'asset_label':label,'context_label':label,'layout':'contain','crop_focus':[.5,.5]}
def main():
 job=next(x for x in json.loads((ROOT/'production_20261009_platform_specific/manifest.json').read_text())['jobs'] if x['id']=='2026-10-09-youtube-02')
 sources=[s['url'] for s in job['sources']]
 BASE.mkdir(parents=True,exist_ok=True);(BASE/'script.txt').write_text(job['script']+'\n')
 diagrams=[]
 im,d=canvas('Μετράμε τον χρόνο του φωτός','Επεξηγηματικό σχήμα — αποστάσεις και σώματα όχι σε κλίμακα')
 d.ellipse((130,440,350,660),fill='#247B9C');d.ellipse((920,490,1060,630),fill='#B4BCC2')
 text(d,'Γη',240,700,52,bold=True);text(d,'Σελήνη',990,700,52,bold=True)
 arrow(d,(350,470),(910,470));arrow(d,(915,625),(360,625),TEAL)
 text(d,'Παλμός προς τον ανακλαστήρα',635,340,38)
 text(d,'Επιστροφή προς το όργανο',635,790,38,fill=TEAL)
 text(d,'Απόσταση = ταχύτητα φωτός × χρόνος / 2',640,985,43,bold=True)
 text(d,'Ο χρόνος περιλαμβάνει και τις δύο διαδρομές.',640,1125,34)
 diagrams.append(save_diagram(im,'round-trip.png','Χρόνος μετ’ επιστροφής · επεξηγηματικό σχήμα','Συμβολική αρχή της μέτρησης· όχι πραγματική κλίμακα ή αριθμητικό παράδειγμα μέτρησης.',sources))
 im,d=canvas('Η μέτρηση χρειάζεται διορθώσεις','Επεξηγηματική οργάνωση των παραγόντων — όχι δεδομένα')
 for y,title,detail in [(350,'Ατμόσφαιρα','Το φως διασχίζει δύο φορές τον αέρα.'),(605,'Κίνηση της Γης','Η θέση του σταθμού μεταβάλλεται.'),(860,'Κίνηση της Σελήνης','Ο ανακλαστήρας κινείται στην τροχιά.')]:
  d.rounded_rectangle((125,y,1155,y+175),radius=24,fill=LIGHT,outline='#B7D4DF',width=3)
  text(d,title,640,y+24,46,bold=True);text(d,detail,640,y+104,34)
 text(d,'Πολλές παρατηρήσεις → ακριβέστερο αποτέλεσμα',640,1150,36,fill=TEAL)
 diagrams.append(save_diagram(im,'measurement-corrections.png','Ατμόσφαιρα και κίνηση · επεξηγηματικό σχήμα','Τρεις πραγματικοί παράγοντες της μεθόδου, χωρίς κατασκευασμένες τιμές ή όργανα.',sources))
 im,d=canvas('Μια παλιρροϊκή αλληλεπίδραση','Επεξηγηματικό σχήμα — όχι σε κλίμακα')
 d.ellipse((125,420,425,720),fill='#247B9C');text(d,'Περιστροφή Γης',275,775,39,bold=True)
 d.ellipse((880,485,1030,635),fill='#B4BCC2');text(d,'Σεληνιακή τροχιά',950,775,35,bold=True)
 arrow(d,(460,565),(835,565),TEAL,10);text(d,'Μεταφορά',650,405,40,fill=TEAL);text(d,'στροφορμής',650,465,40,fill=TEAL)
 text(d,'Η Γη περιστρέφεται πολύ σταδιακά πιο αργά.',640,965,38)
 text(d,'Η Σελήνη απομακρύνεται μακροχρόνια.',640,1040,40,bold=True)
 text(d,'Δεν απεικονίζεται στιγμιαία μετακίνηση.',640,1155,33,fill='#58717E')
 diagrams.append(save_diagram(im,'tidal-transfer.png','Παλίρροιες και στροφορμή · επεξηγηματικό σχήμα','Ποιοτική μεταφορά στροφορμής από την περιστροφή της Γης στη σεληνιακή τροχιά· το βέλος δεν είναι φυσική δέσμη.',sources))
 im,d=canvas('Η απόσταση αλλάζει και στην τροχιά','Επεξηγηματικό σχήμα — τα μεγέθη των σωμάτων όχι σε κλίμακα')
 cx,cy,a,e=640,620,380,.055;b=a*math.sqrt(1-e*e);fx=cx-a*e
 d.ellipse((cx-a,cy-b,cx+a,cy+b),outline='#A9BBC5',width=6)
 d.ellipse((fx-52,cy-52,fx+52,cy+52),fill='#247B9C')
 text(d,'Γη',fx,cy+92,43,bold=True)
 for x,label in [(cx-a,'Πιο κοντά'),(cx+a,'Πιο μακριά')]:
  d.ellipse((x-25,cy-25,x+25,cy+25),fill='#B4BCC2',outline='#667684',width=3)
  text(d,label,x,cy-92,35,bold=True)
 arrow(d,(fx-62,cy),(cx-a+36,cy),TEAL,5);arrow(d,(fx+62,cy),(cx+a-36,cy),BLUE,5)
 text(d,'Δύο θέσεις της ίδιας Σελήνης σε άλλες στιγμές.',640,1080,34)
 text(d,'Η διαφορά μέσα στην τροχιά δεν είναι ο ετήσιος ρυθμός.',640,1150,31)
 diagrams.append(save_diagram(im,'orbit-variation.png','Μεταβολή στην τροχιά · επεξηγηματικό σχήμα','Έλλειψη με ενδεικτική εκκεντρότητα0.055 και Γη στη μία εστία· υπερτονισμένα μεγέθη σωμάτων. Δύο θέσεις της ίδιας Σελήνης, όχι δύο φεγγάρια ή μετρημένη τροχιά.',sources))
 receipts={Path(x['path']).name:x for x in json.loads((BASE/'photos/download_receipts.json').read_text())}
 def photo(scene,name,label,context,creator='NASA'):
  p=BASE/'photos'/name;rec=receipts[name]
  return {**rec,'scene':scene,'paragraph_index':scene,'asset_label':label,'context_label':label,'source_title':context,'source_page_url':PAGE,'creator':creator,'creator_display':creator,'license':'NASA media use','license_url':POLICY,'rights_basis':'NASA credited factual imagery used for educational/informational narration under NASA media usage guidelines; no endorsement represented.','historical_context':context,'kind':'photograph','not_a_photograph':False,'layout':'contain','crop_focus':[.5,.5]}
 opening=photo(1,'apollo14-reflector.jpg','Ανακλαστήρας Apollo 14 · Σελήνη, 1971','Πραγματική φωτογραφία του ανακλαστήρα Apollo14 στην επιφάνεια της Σελήνης,5/2/1971.')
 deploy=photo(2,'aldrin-deploying-experiments.jpg','Buzz Aldrin · ανάπτυξη πειραμάτων, 1969','Ο Aldrin μεταφέρει τον ανακλαστήρα Apollo11 και σεισμικό πείραμα στη Σελήνη. Φωτογραφία Neil Armstrong/NASA,1969.','Neil Armstrong / NASA')
 laser=photo(3,'goddard-laser-ranging.jpg','NASA Goddard · μέτρηση προς το σκάφος LRO','Πραγματική φωτογραφία του σταθμού Goddard: οι δέσμες στο συγκεκριμένο στιγμιότυπο στοχεύουν τον σεληνιακό τροχιακό δορυφόροLRO, όχι επιφανειακό ανακλαστήραApollo. Χρησιμοποιείται με σαφή ετικέτα ως πλαίσιο της τεχνικής.')
 close=copy.deepcopy(opening);close.update(scene=6,paragraph_index=6,asset_label='Σημερινός μέσος ρυθμός: περίπου 3,8 cm/έτος',context_label='Apollo 14 · επιστροφή στο σεληνιακό όργανο',layout='cover',crop_focus=[.51,.71],source_reuse_reason='Return to the actual surface reflector after the method explanation, with a closer view; the photograph itself is not a measurement of the annual rate.')
 ending=copy.deepcopy(opening);ending.update(scene=9,paragraph_index=9,asset_label='Το όργανο που συνεχίζει να δίνει απαντήσεις',context_label='Επιστροφή στον ανακλαστήρα Apollo 14',source_reuse_reason='The ending resolves the opening question using the same historic instrument photograph and complete CTA; no padding or second story.')
 def dg(scene,index):
  item=copy.deepcopy(diagrams[index]);item.update(scene=scene,paragraph_index=scene);return item
 assets=[opening,deploy,laser,dg(4,0),dg(5,1),close,dg(7,2),dg(8,3),ending]
 inv={'schema_version':1,'job_id':job['id'],'story_id':job['story_id'],'title':job['title'],'platform':'youtube','brand_id':7076410,'script_path':str(BASE/'script.txt'),'script_sha256':hashlib.sha256(job['script'].encode()).hexdigest(),'assets':assets,'source_research':job['sources'],'source_review':'PHOTOS_VISUALLY_REVIEWED_DIAGRAM_REVIEW_PENDING','source_review_notes':{'photographic_sources':3,'original_precision_diagrams':4,'unique_source_files':7,'intentional_within_story_returns':[6,9],'actual_audio_listened':False,'final_visual_review':False},'caption_path':str(BASE/'caption.txt')}
 (BASE/'inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
 (DIAGRAMS/'diagram_metadata.json').write_text(json.dumps(diagrams,ensure_ascii=False,indent=2)+'\n')
 caption='Πώς μετράμε εκατοστά σε απόσταση εκατοντάδων χιλιάδων χιλιομέτρων; Με ανακλαστήρες, παλμούς λέιζερ και ακριβή χρονισμό.\n\nΠηγές: '+' · '.join(sources)+'\n\nΠραγματικές φωτογραφίες NASA/Neil Armstrong: ανακλαστήραςApollo14 (1971), ανάπτυξη πειραμάτωνApollo11 (1969) και σταθμόςGoddard. Στη φωτογραφία του σταθμού οι δέσμες στοχεύουν το σκάφοςLRO, όπως επισημαίνεται στο βίντεο. Πηγές φωτογραφιών: '+PAGE+' · Όροι χρήσης: '+POLICY+'\n\nΤέσσερα πρωτότυπα επεξηγηματικά σχήματα, όχι φωτογραφίες ή μετρημένα δεδομένα: Ιστορίες που μας αγγίζουν, CC BY4.0 — https://creativecommons.org/licenses/by/4.0/. Εννέα σκηνές από επτά μοναδικά αρχεία· σκόπιμη επιστροφή στον ίδιο ανακλαστήρα. Προστέθηκαν κάθετη σύνθεση, κοντινή θέαση και υπότιτλοι. Συνθετική ελληνική αφήγηση με τη φωνήΝέστορας.\n\nΑν σας άρεσε, ακολουθήστε για περισσότερα.\n\n#Σελήνη #Διάστημα #Φυσική #NASA'
 caption=caption.replace('ανακλαστήραςApollo','ανακλαστήρας Apollo').replace('πειραμάτωνApollo','πειραμάτων Apollo').replace('σταθμόςGoddard','σταθμός Goddard').replace('σκάφοςLRO','σκάφος LRO').replace('BY4.0','BY 4.0').replace('φωνήΝέστορας','φωνή Νέστορας')
 (BASE/'caption.txt').write_text(caption+'\n')
 lines=['# Σεληνιακή απόσταση — πηγές εικόνων και σχημάτων','','Τρία φωτογραφικά τεκμήρια και τέσσερα πρωτότυπα επιστημονικά σχήματα. Εννέα σκηνές, επτά μοναδικά αρχεία.','']
 for x in assets:
  lines += [f"## Σκηνή {x['scene']}: {x['asset_label']}",'',x['historical_context'],'',f"Δημιουργός: {x['creator']}. Άδεια/όροι: {x['license']} — {x['license_url']}",'',f"Πηγή: {x['source_page_url']}",'',f"Αρχείο SHA256: {x['sha256']}",'']
  if x.get('source_reuse_reason'): lines += [x['source_reuse_reason'],'']
 lines+=['## Επιστημονική τεκμηρίωση','']+[s['url'] for s in job['sources']]
 (BASE/'source_attributions.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'inventory':str(BASE/'inventory.json'),'diagrams':[x['path'] for x in diagrams],'caption_characters':len(caption),'actual_audio_listened':False},ensure_ascii=False))
if __name__=='__main__': main()
