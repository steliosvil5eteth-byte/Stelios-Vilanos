#!/usr/bin/env python3
"""Prepare only the explicitly approved 20 September legend's visual inputs.
No HeyGen, TTS, payment or social-publishing requests are made here.
"""
import hashlib, json, os, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps

OUT=Path(os.environ['OUTPUT_DIR'])/'legend-20260920-flying-dutchman'
OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
CTA='Αν σας άρεσε, ακολουθήστε για περισσότερα.'
ARTS=[
 ('dix','The Flying Dutchman by Charles Temple Dix.jpg','Charles Temple Dix','δεκαετία 1860'),
 ('ryder','Albert Pinkham Ryder - Flying Dutchman - Smithsonian.jpg','Albert Pinkham Ryder','έως το 1887'),
 ('strindberg','August Strindberg - Storm in the Skerries. "The Flying Dutchman" - Google Art Project.jpg','August Strindberg','1892'),
 ('gehrts','Gehrts - Flying Dutchman - 1887.jpg','Johann Gehrts','1887'),
 ('cruikshank','Edward Fitzball - The Flying Dutchman.jpg','Isaac Robert Cruikshank','έως το 1829'),
 ('kingsley','The Flying Dutchman LACMA 47.31.63.jpg','Elbridge Kingsley / LACMA','1887'),
 ('cawse','The Phantom Ship - 1847 frontispiece.jpeg','John Cawse','έκδοση 1847')
]
SPEECH=[
 'Ο θρύλος λέει πως, αν αυτό το πλοίο σε πλησιάσει, δεν πρέπει να δεχτείς τα γράμματά του.',
 'Είναι ο Ιπτάμενος Ολλανδός. Το καράβι που δεν βρίσκει ποτέ λιμάνι.',
 'Και η κατάρα του ξεκίνησε από έναν όρκο.',
 'Σε μια εκδοχή του θρύλου, ένας καπετάνιος προσπαθεί να περάσει το Ακρωτήριο της Καλής Ελπίδας μέσα σε φοβερή καταιγίδα.',
 'Ο άνεμος τον σπρώχνει πίσω. Εκείνος, όμως, αρνείται να υποχωρήσει.',
 'Ορκίζεται ότι θα περάσει, ακόμη κι αν ταξιδεύει για πάντα.',
 'Και τότε, λέει η ιστορία, ο όρκος γίνεται καταδίκη.',
 'Το πλοίο συνεχίζει να πλέει. Μόνο που κανείς δεν επιστρέφει σπίτι.',
 'Οι ναυτικοί το περιγράφουν με παράξενη λάμψη. Με πανιά φουσκωμένα, ακόμη κι όταν η θάλασσα είναι ακίνητη.',
 'Το πιο ανατριχιαστικό, όμως, δεν είναι το πλοίο.',
 'Είναι το πλήρωμά του, που ζητά από περαστικούς να μεταφέρουν γράμματα στη στεριά.',
 'Γράμματα για τους ανθρώπους που άφησαν πίσω. Μηνύματα από ένα ταξίδι που δεν τελειώνει.',
 'Κι όποιος τα δεχτεί, λένε, φέρνει την κακοτυχία κοντά του.',
 'Αυτά ανήκουν στη ναυτική παράδοση, όχι σε αποδεδειγμένο υπερφυσικό γεγονός. Αλλά ο φόβος πίσω από τον θρύλο είναι βαθιά ανθρώπινος:',
 'να περάσει όλη σου η ζωή ταξιδεύοντας, χωρίς να φτάσεις ποτέ εκεί όπου σε περιμένουν.'
]
LABELS=['ΜΗ ΔΕΧΤΕΙΣ ΤΑ ΓΡΑΜΜΑΤΑ','ΤΟ ΠΛΟΙΟ ΧΩΡΙΣ ΛΙΜΑΝΙ','Ο ΟΡΚΟΣ','ΣΤΟ ΑΚΡΩΤΗΡΙΟ','Η ΑΡΝΗΣΗ','ΓΙΑ ΠΑΝΤΑ','Η ΚΑΤΑΔΙΚΗ','ΧΩΡΙΣ ΕΠΙΣΤΡΟΦΗ','ΠΑΝΙΑ ΧΩΡΙΣ ΑΝΕΜΟ','ΤΟ ΠΙΟ ΑΝΑΤΡΙΧΙΑΣΤΙΚΟ','ΤΑ ΓΡΑΜΜΑΤΑ','ΟΙ ΑΝΘΡΩΠΟΙ ΠΙΣΩ','Η ΠΡΟΕΙΔΟΠΟΙΗΣΗ','ΘΡΥΛΟΣ, ΟΧΙ ΑΠΟΔΕΙΞΗ','ΝΑ ΜΗ ΦΤΑΣΕΙΣ ΠΟΤΕ']
SEQUENCE=['dix','ryder','cruikshank','strindberg','dix','cruikshank','gehrts','cawse','ryder','kingsley','gehrts','cawse','kingsley','strindberg','dix']

def lines(draw,text,font,maxw):
 result=[]
 for para in text.split('\n'):
  line=''
  for word in para.split():
   n=(line+' '+word).strip()
   if draw.textlength(n,font=font)>maxw:
    if not line: raise ValueError('Word will not fit')
    result.append(line);line=word
   else:line=n
  result.append(line)
 return result

def write(im,text,box,size=44,bold=False,color='#ffffff',center=False):
 d=ImageDraw.Draw(im);x,y,w,h=box
 for fs in range(size,23,-1):
  f=ImageFont.truetype(BOLD if bold else FONT,fs);ls=lines(d,text,f,w);lh=int(fs*1.35)
  if len(ls)*lh<=h:break
 else:raise ValueError('Unfittable text')
 for line in ls:
  xx=x+(w-d.textlength(line,font=f))/2 if center else x
  d.text((xx,y),line,font=f,fill=color);y+=lh

class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  u=urllib.parse.urlsplit(newurl)
  if u.scheme!='https' or u.hostname!='upload.wikimedia.org':raise ValueError('Unexpected download host')
  return super().redirect_request(req,fp,code,msg,headers,newurl)

metadata=[];images={}
for key,name,artist,date in ARTS:
 normalized=name.replace(' ','_');md=hashlib.md5(normalized.encode()).hexdigest()
 url='https://upload.wikimedia.org/wikipedia/commons/'+md[0]+'/'+md[:2]+'/'+urllib.parse.quote(normalized,safe='')
 req=urllib.request.Request(url,headers={'User-Agent':'SteliosPublicDomainMedia/1.0 (approved educational legend illustration)'})
 with urllib.request.build_opener(SafeRedirect()).open(req,timeout=90) as r:
  data=r.read(22*1024*1024)
  if len(data)>20*1024*1024:raise ValueError('Oversize source')
  if not r.headers.get('Content-Type','').startswith('image/'):raise ValueError('Non-image source')
 original=OUT/(key+'-original'+Path(normalized).suffix);original.write_bytes(data)
 im=Image.open(original);im.load();images[key]=ImageOps.exif_transpose(im).convert('RGB')
 metadata.append({'id':key,'artist':artist,'artwork_date':date,'license':'Public Domain','license_url':'https://creativecommons.org/publicdomain/mark/1.0/','source_page':'https://commons.wikimedia.org/wiki/File:'+urllib.parse.quote(normalized,safe=''),'direct_url':url,'original_sha256':hashlib.sha256(data).hexdigest(),'width':im.width,'height':im.height,'use':'Historical illustration, not a photograph of an actual ghost ship'})
 print(json.dumps({'downloaded':key,'bytes':len(data)},ensure_ascii=False),flush=True)

scenes=[]
for index,(key,script,label) in enumerate(zip(SEQUENCE,SPEECH,LABELS),1):
 source=images[key]
 bg=ImageOps.fit(source,(1080,1920),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(35))
 bg=ImageEnhance.Brightness(bg).enhance(.30)
 panel=ImageOps.contain(source,(1020,1130),Image.Resampling.LANCZOS)
 bg.paste(panel,((1080-panel.width)//2,340+(1130-panel.height)//2))
 overlay=Image.new('RGBA',(1080,1920),(0,0,0,0));d=ImageDraw.Draw(overlay)
 d.rectangle((0,0,1080,310),fill=(8,16,26,215));d.rectangle((0,1510,1080,1920),fill=(8,16,26,225))
 bg=Image.alpha_composite(bg.convert('RGBA'),overlay).convert('RGB')
 write(bg,'Ο ΘΡΥΛΟΣ ΛΕΕΙ…',(70,85,920,75),42,True,'#dfc38a')
 write(bg,label,(70,174,920,135),53,True)
 m=next(x for x in metadata if x['id']==key)
 write(bg,'Ιστορική εικονογράφηση • όχι πραγματική λήψη',(65,1690,950,60),28,False,'#dfc38a')
 write(bg,m['artist']+' • '+m['artwork_date'],(65,1750,950,55),29)
 write(bg,'Public Domain • Wikimedia Commons',(65,1807,950,55),26)
 filename=f'scene-{index:02d}.jpg';bg.save(OUT/filename,quality=93)
 scenes.append({'file':filename,'source_art':key,'script':script,'voice_id':'8bc71625549d425d9a38b4e4a296ba32'})

credit=Image.new('RGB',(1080,1920),'#0c1522')
write(credit,'ΠΗΓΕΣ & ΕΙΚΟΝΕΣ',(75,190,930,130),58,True,'#dfc38a')
write(credit,'Ναυτική παράδοση:\nCape Point — The Cape of Ghosts\nRoyal Museums Greenwich',(75,385,930,280),37)
write(credit,'Ιστορικά έργα δημόσιου τομέα:\nCharles Temple Dix • δεκαετία 1860\nAlbert Pinkham Ryder • έως το 1887\nAugust Strindberg • 1892\nJohann Gehrts • 1887\nI. R. Cruikshank • έως το 1829\nElbridge Kingsley / LACMA • 1887\nJohn Cawse • έκδοση 1847',(75,705,930,625),35)
write(credit,'15 σκηνές από 7 ιστορικά έργα.\nΔεν πρόκειται για φωτογραφίες\nπραγματικού υπερφυσικού συμβάντος.\nΠλήρεις πηγές στην περιγραφή.',(75,1410,930,290),33)
credit.save(OUT/'credits.jpg',quality=93)
closing=Image.new('RGB',(1080,1920),'#0c1522')
write(closing,'Ο ΙΠΤΑΜΕΝΟΣ\nΟΛΛΑΝΔΟΣ',(90,360,900,245),70,True,'#dfc38a',True)
write(closing,CTA,(90,850,900,385),69,True,center=True)
write(closing,'ΝΑΥΤΙΚΟΙ ΘΡΥΛΟΙ • ΣΤΕΛΙΟΣ',(90,1430,900,100),31,center=True)
closing.save(OUT/'closing.jpg',quality=93)
report={'key':'2026-09-20:legend:flying-dutchman','phase':'visual-inputs-ready','not_final_video':True,'scenes':scenes,'credits_file':'credits.jpg','credits_hold_seconds':7,'closing_file':'closing.jpg','closing_script':CTA,'source_art_count':len(metadata),'art':metadata,'research':['https://capepoint.co.za/capepointmoments-the-cape-of-ghosts/','https://www.rmg.co.uk/stories/maritime-history/halloween-on-board-cutty-sark'],'paid_ai_calls':0,'publishing_calls':0}
report['files']=[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.glob('*.jpg')) if '-original' not in p.name]
(OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('PREPARED '+str(len(scenes))+' scene cards; no TTS/video generated',flush=True)
