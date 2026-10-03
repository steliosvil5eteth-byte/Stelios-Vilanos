#!/usr/bin/env python3
import io, json, urllib.parse, urllib.request, subprocess, base64
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from rembg import remove

OUT=Path(__import__('sys').argv[1]); OUT.mkdir(parents=True,exist_ok=True)
UA={'User-Agent':'SteliosDogBartenderQA/1.0'}
def fetch_commons(filename,path,width=1800):
    url='https://commons.wikimedia.org/wiki/Special:Redirect/file/'+urllib.parse.quote(filename,safe='()_,.-')+f'?width={width}'
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=120) as r: path.write_bytes(r.read())

dog_name='3061-labrador-dog-brown (19876741324).jpg'
dog_path=OUT/'dog-source.jpg'; fetch_commons(dog_name,dog_path)
dog=Image.open(io.BytesIO(remove(dog_path.read_bytes()))).convert('RGBA')
dog=dog.crop(dog.getbbox())
bars=[
 'Hard Rock Cafe bar counter (2011-08-25 17.41.49 - Hippopx.com).jpg',
 'Interior view of The Commercial, Herne Hill in 2018.jpg',
 'Bar counter with beer taps, Vieux-Québec.jpg',
 'Bar counter-Schrannenhalle.JPG'
]
titles=['ΣΚΥΛΟΣ ΜΠΑΡΜΑΝ — 1/4','Η ΠΑΡΑΓΓΕΛΙΑ ΣΥΝΕΧΙΣΤΗΚΕ — 2/4','Ο ΜΠΑΡΜΑΝ ΕΚΑΝΕ Ο,ΤΙ ΜΠΟΡΟΥΣΕ — 3/4','ΤΕΛΙΚΑ ΤΟΥ ΕΔΩΣΕ ΝΕΡΟ — 4/4']
bodies=[
 'Ο πελάτης ζήτησε νερό «ούτε πολύ κρύο, ούτε χλιαρό, με δύο παγάκια ακριβώς». Ο μπάρμαν τον κοίταξε σοβαρά.',
 '«Χωρίς λεμόνι, αλλά να μυρίζει λεμόνι. Και το ποτήρι να είναι μεγάλο, αλλά να μη φαίνεται μεγάλο».',
 'Έβαλε δύο παγάκια, κοίταξε το ποτήρι, κοίταξε τον πελάτη… και πήρε τη βαθύτερη ανάσα της βάρδιας.',
 'Ο πελάτης χαμογέλασε: «Ακριβώς όπως το ήθελα». Ο σκύλος μπάρμαν δεν χαμογέλασε καθόλου.'
]
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def wrap(d,text,f,maxw):
    lines=[]; cur=''
    for w in text.split():
        c=(cur+' '+w).strip()
        if not cur or d.textlength(c,font=f)<=maxw: cur=c
        else: lines.append(cur); cur=w
    if cur: lines.append(cur)
    return lines
cards=[]
for i,(bar,title,body) in enumerate(zip(bars,titles,bodies),1):
    raw=OUT/f'bar-{i}.jpg'; fetch_commons(bar,raw)
    bg=ImageOps.fit(Image.open(raw).convert('RGB'),(1080,1080),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(.25)).convert('RGBA')
    dw=[510,540,500,530][i-1]; dh=int(dog.height*dw/dog.width)
    fg=dog.resize((dw,dh),Image.Resampling.LANCZOS)
    x=[490,455,515,470][i-1]; y=max(285,1080-dh+90)
    bg.alpha_composite(fg,(x,y))
    d=ImageDraw.Draw(bg); cx=x+dw//2; bow_y=max(520,y+int(dh*.40))
    d.polygon([(cx-58,bow_y),(cx-8,bow_y+28),(cx-8,bow_y-28)],fill=(130,22,22,245))
    d.polygon([(cx+58,bow_y),(cx+8,bow_y+28),(cx+8,bow_y-28)],fill=(130,22,22,245))
    d.ellipse((cx-12,bow_y-12,cx+12,bow_y+12),fill=(220,184,95,255))
    d.rounded_rectangle((cx-115,bow_y+45,cx+115,min(1040,bow_y+315)),radius=22,fill=(16,22,26,220))
    d.rounded_rectangle((35,35,1018,315),radius=24,fill=(8,13,18,195))
    tf=ImageFont.truetype(bold,46); bf=ImageFont.truetype(font,32); yy=60
    for line in wrap(d,title,tf,930): d.text((60,yy),line,font=tf,fill='white',stroke_width=1,stroke_fill='black'); yy+=56
    yy=max(yy+8,165)
    for line in wrap(d,body,bf,930): d.text((60,yy),line,font=bf,fill='white',stroke_width=1,stroke_fill='black'); yy+=41
    d.rounded_rectangle((42,944,1038,1038),radius=18,fill=(15,24,36,235))
    cta='Αν σας άρεσε, ακολουθήστε για περισσότερα.'; cf=ImageFont.truetype(bold,25); tw=d.textlength(cta,font=cf)
    d.text(((1080-tw)/2,975),cta,font=cf,fill='white')
    card=OUT/f'ten-20261003-1000-dog-bartender-water-order-{i:02d}.jpg'; bg.convert('RGB').save(card,quality=95,subsampling=0); cards.append(card)

sheet=Image.new('RGB',(960,640),(18,18,18))
for i,c in enumerate(cards): sheet.paste(ImageOps.fit(Image.open(c).convert('RGB'),(480,320)),((i%2)*480,(i//2)*320))
sheet.save(OUT/'final-contact-sheet.jpg',quality=94)
(OUT/'final-contact-sheet.b64.txt').write_text(base64.b64encode((OUT/'final-contact-sheet.jpg').read_bytes()).decode('ascii'))

td=OUT/'tmp'; td.mkdir(exist_ok=True); segs=[]
for i,c in enumerate(cards,1):
    vertical=Image.new('RGB',(1080,1920),(16,26,40)); vertical.paste(Image.open(c).convert('RGB'),(0,420)); jpg=td/f'v{i}.jpg'; vertical.save(jpg,quality=94)
    mp=td/f's{i}.mp4'; subprocess.run(['ffmpeg','-y','-v','error','-loop','1','-framerate','25','-i',str(jpg),'-t','5','-vf','setsar=1,fps=25','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-an',str(mp)],check=True); segs.append(mp)
concat=td/'concat.txt'; concat.write_text('\n'.join("file '"+str(p)+"'" for p in segs)+'\n')
visual=td/'visual.mp4'; subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(visual)],check=True)
final=OUT/'ten-20261003-1000-dog-bartender-water-order.mp4'
subprocess.run(['ffmpeg','-y','-v','error','-i',str(visual),'-f','lavfi','-i','sine=frequency=220:sample_rate=48000:duration=20','-filter_complex','[1:a]volume=0.025,afade=t=in:st=0:d=1,afade=t=out:st=18.5:d=1.5[a]','-map','0:v','-map','[a]','-t','20','-c:v','copy','-c:a','aac','-b:a','128k','-movflags','+faststart',str(final)],check=True)
for p in td.rglob('*'):
    if p.is_file(): p.unlink()
td.rmdir()
(OUT/'qa.json').write_text(json.dumps({'status':'PENDING_DIRECT_VISUAL_REVIEW','card_count':4,'same_recurring_dog':True,'photographic_bar_backgrounds':True,'dog_source':dog_name,'dog_license':'CC BY 2.0','dog_attribution':'localpups','bar_sources':bars},ensure_ascii=False,indent=2))
