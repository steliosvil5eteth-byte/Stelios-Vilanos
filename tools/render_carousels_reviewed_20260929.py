from pathlib import Path
from PIL import Image
import json,sys
from render_carousel_pack import slideshow,run,probe
pack=sys.argv[1]
p=Path('ready')/pack;p.mkdir(exist_ok=True)
paths=json.loads(Path(pack+'images.json').read_text())
for i,path in enumerate(paths,1):
    Image.open(path).convert('RGB').resize((1080,1080),Image.Resampling.LANCZOS).save(p/f'card-{i:02d}.jpg',quality=91,subsampling=0)
video={'zodiac29':'zodiac-compliment-b.mp4','love29':'love-blazer.mp4','myth29':'myth-camel.mp4','survival29':'survival-storm.mp4'}[pack]
duration=slideshow(sorted(p.glob('card-*.jpg')),p/video,7)
run(['ffmpeg','-v','error','-i',str(p/video),'-f','null','-'])
run(['ffmpeg','-v','error','-y','-i',str(p/video),'-vf','fps=1/7,scale=360:640,tile=3x3','-frames:v','1',str(p/'final-review.jpg')])
(p/'technical-qa.json').write_text(json.dumps({'duration':duration,'cards':len(paths),'full_decode_passed':True,'probe':probe(p/video)},indent=2))
print(pack,video,duration)
