from pathlib import Path
import json,re,subprocess,textwrap,math

P=Path('ready/milky')
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def run(args):
 r=subprocess.run(args,capture_output=True,text=True)
 if r.returncode: raise RuntimeError(r.stderr[-4000:])
 return r.stdout
def seconds(s):
 h,m,t=s.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(t)
def stamp(t):
 return f'{int(t)//3600}:{int(t)//60%60:02d}:{t%60:05.2f}'
blocks=[]
for part in P.joinpath('subs.srt').read_text().strip().split('\n\n'):
 lines=part.splitlines();a,b=lines[1].split(' --> ');s=' '.join(lines[2:]);s=re.sub(r'\s+([.,;:!?])',r'\1',s)
 if re.fullmatch(r'[.,;:!?]+',s):
  blocks[-1][2]+=s;blocks[-1][1]=seconds(b);continue
 if s and s[0] in ',.;:':
  blocks[-1][2]+=s[0];s=s[1:].strip()
 blocks.append([seconds(a),seconds(b),s])
ass='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,52,&H00FFFFFF,&H00FFFFFF,&H0010141B,&H0010141B,-1,0,0,0,100,100,0,0,3,3,0,2,80,80,220,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
for a,b,s in blocks:
 s='\\N'.join(textwrap.wrap(s,width=32,break_long_words=False))
 ass+=f'Dialogue: 0,{stamp(a)},{stamp(b)},Default,,0,0,0,,{s}\n'
P.joinpath('corrected.ass').write_text(ass)
P.joinpath('corrected-subtitles.json').write_text(json.dumps(blocks,ensure_ascii=False,indent=2))
images=json.loads(P.joinpath('generated.json').read_text())
credit='S. D. Miller, PNAS (2022) • CC BY 4.0'
scenes=[
 (0,9.875,images['intro'],'Η ΘΑΛΑΣΣΑ ΠΟΥ ΛΑΜΠΕΙ','Milky seas • Γαλακτώδεις θάλασσες','Ενδεικτική αναπαράσταση AI'),
 (9.875,14.825,images['blue'],'ΜΙΑ ΔΙΑΦΟΡΕΤΙΚΗ ΛΑΜΨΗ','Σπινθηρίσματα σε αναταραγμένο νερό','Ενδεικτική αναπαράσταση AI'),
 (14.825,19.725,images['uniform'],'ΣΥΝΕΧΗΣ ΚΑΙ ΟΜΟΙΟΜΟΡΦΗ','Η λάμψη εκτείνεται και σε ήρεμο νερό','Ενδεικτική αναπαράσταση AI'),
 (19.725,29.938,images['log'],'ΣΤΑ ΗΜΕΡΟΛΟΓΙΑ ΝΑΥΤΙΚΩΝ','Περιγραφές φωτεινής θάλασσας εδώ και αιώνες','Ιστορική αναπαράσταση AI'),
 (29.938,46.862,'fig-2-0.jpeg','Η ΜΑΤΙΑ ΤΩΝ ΔΟΡΥΦΟΡΩΝ','VIIRS / DNB • Παράδειγμα καταγραφής του 2019',credit),
 (46.862,60.8,'fig-2-0.jpeg','ΝΟΤΙΑ ΤΗΣ ΙΑΒΑΣ • 2019','Φωτεινή περιοχή πάνω από 100.000 km²',credit),
 (60.8,68.462,'fig-3-0.jpeg','Η ΕΠΙΒΕΒΑΙΩΣΗ ΑΠΟ ΤΟ ΣΚΑΦΟΣ','GoPro / Samsung • Δεξιά: χρωματική προσαρμογή',credit),
 (68.462,83.2,images['lab'],'ΤΟ ΙΧΝΟΣ ΤΩΝ ΒΑΚΤΗΡΙΩΝ','Δειγματοληψία στην Αραβική Θάλασσα • 1985','Ενδεικτική αναπαράσταση εργαστηρίου AI'),
 (83.2,93.65,images['lab'],'ΤΑ ΕΡΩΤΗΜΑΤΑ ΠΑΡΑΜΕΝΟΥΝ','Η δομή και ο μηχανισμός ακόμη ερευνώνται','Ενδεικτική αναπαράσταση εργαστηρίου AI'),
 (93.65,103.76,images['end'],'ΑΠΟ ΤΙΣ ΑΦΗΓΗΣΕΙΣ ΣΤΑ ΔΕΔΟΜΕΝΑ','Δορυφορική ανίχνευση και μαρτυρία πληρώματος','Ενδεικτική αναπαράσταση AI')
]
manifest=[]
for i,(a,b,img,title,label,source) in enumerate(scenes):
 path=Path(img) if img.startswith('/') else P/img
 for key,value in [('title',title),('label',label),('credit',source)]:P.joinpath(f'{i}-{key}.txt').write_text(value)
 out=P/f'scene-{i:02d}.mp4'
 vf=f'scale=1000:1120:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:320+(1120-ih)/2:color=0x10141b,setsar=1'
 for key,y,size,font in [('title',175,43,BOLD),('label',1470,30,FONT),('credit',1520,27,FONT)]:
  vf+=f',drawtext=fontfile={font}:textfile={P}/{i}-{key}.txt:fontcolor=white:fontsize={size}:x=(w-tw)/2:y={y}'
 frames=round(b*25)-round(a*25)
 run(['ffmpeg','-v','error','-y','-loop','1','-framerate','25','-i',str(path),'-vf',vf,'-frames:v',str(frames),'-an','-c:v','libx264','-preset','ultrafast','-crf','22','-pix_fmt','yuv420p',str(out)])
 manifest.append({'start':round(a*25)/25,'end':round(b*25)/25,'image':str(path),'title':title,'source':source})
P.joinpath('scenes.txt').write_text(''.join(f"file 'scene-{i:02d}.mp4'\n" for i in range(len(scenes))))
P.joinpath('scene-map.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(P/'scenes.txt'),'-i',str(P/'nestoras.wav'),'-vf',f'ass={P}/corrected.ass','-map','0:v','-map','1:a','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(P/'milky-seas.mp4')])
print('Rendered scene-matched Milky Seas video')
