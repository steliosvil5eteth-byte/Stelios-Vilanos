#!/usr/bin/env python3
"""Native explanatory diagrams for the already sourced water-density story.

These are explicitly labelled diagrams, never photographs or measured data.
No generative image service or external paid call is used.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json, hashlib

BASE = Path(__file__).resolve().parents[2] / 'production_20261009_platform_specific/recovery/youtube-01/diagrams'
BASE.mkdir(parents=True, exist_ok=True)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
W,H=1280,1280
INK='#102D3C';MUTED='#496A79';BLUE='#1389AE';PALE='#DCEFF5';TEAL='#0D8C85'

def canvas(title, subtitle):
    im=Image.new('RGB',(W,H),'#F6FBFD');d=ImageDraw.Draw(im)
    d.rounded_rectangle((35,35,1245,1245),radius=40,fill='white',outline='#D6E6EB',width=3)
    centered(d,title,110,58,INK,True)
    centered(d,subtitle,195,34,MUTED)
    return im,d

def centered(d,text,y,size=48,fill=INK,bold=False):
    f=ImageFont.truetype(BOLD if bold else FONT,size)
    if d.textlength(text,font=f)>1160: raise ValueError('Diagram text overflow: '+text)
    d.text((W/2,y),text,anchor='mt',font=f,fill=fill)

def save(im,name,description):
    p=BASE/name;im.save(p)
    return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'dimensions_px':[W,H], 'kind':'explanatory_diagram','description':description,'creator':'Ιστορίες που μας αγγίζουν — επεξηγηματική σύνθεση','license':'CC BY-SA 4.0','license_url':'https://creativecommons.org/licenses/by-sa/4.0/','source_page_url':'https://www.usgs.gov/water-science-school/science/water-density','not_a_photograph':True,'not_measured_data':True}

records=[]
im,d=canvas('Τι σημαίνει πυκνότητα;','Σχηματική σύγκριση της ίδιας μάζας — όχι σε κλίμακα')
d.rounded_rectangle((130,405,535,975),radius=22,fill=PALE,outline=BLUE,width=6)
d.rounded_rectangle((665,300,1150,975),radius=22,fill='#E8F6F9',outline=BLUE,width=6)
for x0,y0,dx,dy in [(188,472,94,89),(732,374,113,101)]:
    for row in range(5):
        for col in range(4):
            x=x0+dx*col;y=y0+dy*row;d.ellipse((x-19,y-19,x+19,y+19),fill=TEAL)
f=ImageFont.truetype(BOLD,38)
d.text((333,1032),'Μικρότερος όγκος',anchor='mt',font=f,fill=INK)
d.text((908,1032),'Μεγαλύτερος όγκος',anchor='mt',font=f,fill=INK)
centered(d,'Πυκνότητα = μάζα / όγκος',1140,51,INK,True)
records.append(save(im,'density-volume.png','Ίσος αριθμός συμβολικών μονάδων μάζας σε διαφορετικό σχηματικό όγκο. Οι κουκκίδες δεν είναι διάγραμμα μοριακών δεσμών.'))

im,d=canvas('Μια ιδιαιτερότητα του νερού','Σε συνηθισμένη πίεση — επεξηγηματικό σχήμα')
x=372;top=330;bottom=1000
d.rounded_rectangle((x-48,top-35,x+48,bottom+12),radius=48,fill='#E7EFF4',outline=INK,width=5)
d.ellipse((x-83,bottom-60,x+83,bottom+106),fill=TEAL,outline=INK,width=5)
for value in range(11):
    y=bottom-(bottom-top)*value/10
    d.line((x+70,y,x+110,y),fill=INK,width=4)
    d.text((x+135,y),str(value)+'°C',anchor='lm',font=ImageFont.truetype(FONT,38),fill=INK)
y4=bottom-(bottom-top)*.4
d.rectangle((x-25,y4,x+25,bottom+40),fill=TEAL)
d.ellipse((x-24,y4-22,x+24,y4+22),fill=TEAL)
d.line((620,y4,1050,y4),fill=TEAL,width=7)
d.polygon([(615,y4),(641,y4-17),(641,y4+17)],fill=TEAL)
d.text((865,y4-130),'Περίπου 4°C',anchor='mt',font=ImageFont.truetype(BOLD,54),fill=TEAL)
d.text((865,y4+52),'Μέγιστη',anchor='mt',font=ImageFont.truetype(BOLD,49),fill=INK)
d.text((865,y4+122),'πυκνότητα',anchor='mt',font=ImageFont.truetype(BOLD,49),fill=INK)
centered(d,'Δεν απεικονίζεται πραγματική μέτρηση.',1170,31,MUTED)
records.append(save(im,'water-four-degrees.png','Σχηματικό θερμόμετρο υπογραμμίζει το περίπου4°C μέγιστο πυκνότητας καθαρού νερού σε συνήθεις συνθήκες. Δεν είναι πραγματικό όργανο ή σύνολο μετρήσεων.'))

im,d=canvas('Κάτω από την επιφάνεια','Σχηματική τομή λίμνης — όχι σε κλίμακα')
d.rectangle((100,315,1180,590),fill='#E7F3F9')
d.polygon([(100,580),(230,715),(360,1040),(920,1040),(1050,715),(1180,580),(1180,1100),(100,1100)],fill='#A3ADB0')
d.polygon([(168,585),(295,820),(390,1020),(890,1020),(985,820),(1112,585)],fill='#178EB9')
d.rounded_rectangle((155,548,1125,626),radius=18,fill='#F0FAFF',outline='#81BCCF',width=4)
for x in [220,380,570,730,920,1060]:d.line((x,553,x+27,576,x+8,619),fill='#BCDCE8',width=3)
d.text((640,405),'ΚΡΥΟΣ ΑΕΡΑΣ',anchor='mt',font=ImageFont.truetype(BOLD,48),fill=INK)
d.text((640,563),'ΠΑΓΟΣ',anchor='mt',font=ImageFont.truetype(BOLD,43),fill=INK)
d.text((640,796),'ΥΓΡΟ ΝΕΡΟ',anchor='mt',font=ImageFont.truetype(BOLD,58),fill='white')
centered(d,'Το βάθος και οι συνθήκες έχουν σημασία.',1150,40,INK)
records.append(save(im,'lake-cross-section.png','Γενική τομή που δείχνει ότι μπορεί να παραμένει υγρό νερό κάτω από επιφανειακό πάγο. Δεν παρουσιάζεται ως πραγματική λίμνη ή καθολική κατάσταση όλων των λιμνών.'))
(BASE/'diagram_metadata.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'diagrams':len(records),'paths':[r['path'] for r in records]},ensure_ascii=False))
