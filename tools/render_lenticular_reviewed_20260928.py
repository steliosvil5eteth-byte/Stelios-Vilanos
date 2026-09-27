from pathlib import Path
import json,re,subprocess,textwrap,math

P=Path('ready/lenticular28v2')
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
job=json.loads(P.joinpath('job.json').read_text())
bounds=json.loads(P.joinpath('bounds.json').read_text())
words=[x for x in bounds if any(c.isalpha() for c in x['text'])]
starts=[]
for scene in job['scenes']:
 first=scene['text'].split()[:3]
 matches=[words[i]['offset'] for i in range(len(words)-2) if [words[i+j]['text'] for j in range(3)]==first]
 assert len(matches)==1,(first,matches)
 starts.append(matches[0])
starts[0]=0
length=float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(P/'nestoras.wav')]))
ends=starts[1:]+[length]
titles=['ΦΑΚΟΕΙΔΗ ΝΕΦΗ','ΚΥΜΑΤΑ ΠΑΝΩ ΑΠΟ ΤΑ ΒΟΥΝΑ','Η ΥΓΡΑΣΙΑ ΓΙΝΕΤΑΙ ΟΡΑΤΗ','ΜΙΑ ΑΚΙΝΗΤΗ ΕΙΚΟΝΑ','ΠΑΡΑΤΗΡΗΣΕΙΣ ΣΤΗ ΧΑΒΑΗ','ΤΙ ΣΗΜΑΙΝΟΥΝ ΓΙΑ ΤΗΝ ΠΤΗΣΗ','ΕΝΑ ΑΟΡΑΤΟ ΚΥΜΑ']
scenes=[(a,b,images[x['key']],titles[i],'Ενδεικτική αναπαράσταση AI','Πηγές: National Weather Service • weather.gov') for i,(a,b,x) in enumerate(zip(starts,ends,job['scenes']))]
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
run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(P/'scenes.txt'),'-i',str(P/'nestoras.wav'),'-vf',f'ass={P}/corrected.ass','-map','0:v','-map','1:a','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(P/'lenticular-clouds.mp4')])
print('Rendered scene-matched lenticular video')
