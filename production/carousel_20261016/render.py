"""Render original carousel candidates. A successful render never grants QA approval."""
from __future__ import annotations
import hashlib, json, math, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / 'production/carousel_20261016/request.json'
OUT = ROOT / 'media/carousel_20261016'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
BG = (247, 243, 235)
INK = (26, 30, 34)
BRAND = 'Ιστορίες που μας αγγίζουν'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int, bold: bool = False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def lines_for(text: str, ft, width: int) -> list[str]:
    result = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split():
            proposed = (line + ' ' + word).strip()
            if ft.getlength(proposed) > width:
                if not line:
                    raise ValueError('A word does not fit: ' + word)
                result.append(line)
                line = word
            else:
                line = proposed
        if line:
            result.append(line)
    return result


def fit_text(text: str, width: int, height: int, maximum: int, minimum: int, bold=False):
    for size in range(maximum, minimum - 1, -1):
        ft = font(size, bold)
        lines = lines_for(text, ft, width)
        step = math.ceil(size * 1.28)
        if len(lines) * step <= height:
            return ft, lines, step
    raise ValueError('Text needs shortening; refusing clipped rendering: ' + text)


def text_block(canvas: Image.Image, text: str, box, maximum: int, minimum: int, bold=False, fill=INK, center=False):
    x, y, w, h = box
    ft, lines, step = fit_text(text, w, h, maximum, minimum, bold)
    d = ImageDraw.Draw(canvas)
    for line in lines:
        xx = x + (w-ft.getlength(line))/2 if center else x
        d.text((xx, y), line, font=ft, fill=fill, stroke_width=0)
        y += step
    return ft.size, len(lines)


def cover_fit(im: Image.Image, size: tuple[int,int], cy: float=.42):
    w,h=size
    scale=max(w/im.width, h/im.height)
    im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
    x=(im.width-w)//2
    y=round((im.height-h)*cy)
    return im.crop((x,y,x+w,y+h))


def card(photo, post, i, cta):
    im=Image.new('RGB',(1080,1080),BG)
    im.paste(cover_fit(photo,(1080,650)),(0,0))
    overlay=Image.new('RGBA',im.size,(0,0,0,0))
    od=ImageDraw.Draw(overlay)
    od.rounded_rectangle((28,24,622,81),radius=14,fill=(10,14,20,215))
    od.text((46,33),BRAND,font=font(29,True),fill=(255,255,255,255))
    od.rounded_rectangle((939,24,1053,81),radius=14,fill=(10,14,20,215))
    od.text((958,33),f'{i+1:02d}/06',font=font(28,True),fill='white')
    im=Image.alpha_composite(im.convert('RGBA'),overlay).convert('RGB')
    d=ImageDraw.Draw(im)
    d.rectangle((0,650,1080,657),fill=(173,130,73))
    text=post['copy'][i]
    if i==5:
        fs,n=text_block(im,text,(48,680,984,206),46,38)
        text_block(im,cta,(48,910,984,103),39,35,True)
    else:
        fs,n=text_block(im,text,(48,680,984,310),52 if i==0 else 48,40,i==0)
    d=ImageDraw.Draw(im)
    d.line((48,1029,1032,1029),fill=(202,194,181),width=2)
    d.text((48,1040),post['disclosure'],font=font(23),fill=(77,76,72))
    return im, {'body_font_px':fs,'body_lines':n,'unclipped':True}


def vertical(im, post):
    v=Image.new('RGB',(1080,1920),(17,22,28))
    text_block(v,post['title'],(62,171,956,210),55,44,True,(249,247,241),True)
    v.paste(im.resize((1020,1020),Image.Resampling.LANCZOS),(30,450))
    text_block(v,'6 κάρτες · Ολόκληρο το περιεχόμενο',(70,1570,940,95),35,29,False,(233,224,209),True)
    text_block(v,BRAND,(70,1685,940,110),40,34,True,(233,224,209),True)
    return v


def contact(images, path: Path, columns: int, width: int=540):
    rows=math.ceil(len(images)/columns)
    ratio=images[0].height/images[0].width
    height=round(width*ratio)
    sheet=Image.new('RGB',(columns*width,rows*height),(255,255,255))
    for i,im in enumerate(images):
        sheet.paste(im.resize((width,height),Image.Resampling.LANCZOS),((i%columns)*width,(i//columns)*height))
    sheet.save(path,quality=95)


def main():
    req=json.loads(REQUEST.read_text())
    assert req['brand_id']==7076410
    OUT.mkdir(parents=True,exist_ok=True)
    source_dir=OUT/'source';source_dir.mkdir(exist_ok=True)
    sheets={};source_hashes={}
    for name,url in req['sources'].items():
        if not url.startswith('https://videocdn.pollo.ai/'):
            raise ValueError('Unexpected source host')
        target=source_dir/(name+'.png')
        request=urllib.request.Request(url,headers={'User-Agent':'CarouselCandidateRenderer/1.0'})
        with urllib.request.urlopen(request,timeout=60) as r:
            target.write_bytes(r.read())
        im=Image.open(target).convert('RGB')
        if im.width<3000 or abs(im.width/im.height-1.5)>.04:
            raise ValueError(f'Unexpected sheet dimensions: {im.size}')
        sheets[name]=im
        source_hashes[name]={'url':url,'sha256':sha(target),'width':im.width,'height':im.height}
        contact([im],source_dir/(name+'_preview.jpg'),1,1800)
    manifest={'date':req['date'],'brand_id':7076410,'qa_status':'NEEDS_EXACT_FINAL_REVIEW','request_sha256':sha(REQUEST),'sources':source_hashes,'posts':[]}
    for post in req['posts']:
        assert len(post['copy'])==6
        assert req['cta'] in post['caption']
        assert len([w for w in post['caption'].split() if w.startswith('#')])<=5
        folder=OUT/post['id'];folder.mkdir(exist_ok=True)
        sheet=sheets[post['source']]
        cards=[];frames=[];card_rows=[];durations=[]
        for i in range(6):
            x0=round(i*sheet.width/6)+3;x1=round((i+1)*sheet.width/6)-3
            y0=round(post['row']*sheet.height/4)+3;y1=round((post['row']+1)*sheet.height/4)-3
            photo=sheet.crop((x0,y0,x1,y1))
            out,layout=card(photo,post,i,req['cta'])
            path=folder/f'card_{i+1:02d}.jpg';out.save(path,quality=95,subsampling=0)
            # Use the encoded JPEG bytes, not the in-memory draft, in the final video.
            exact=Image.open(path).convert('RGB');cards.append(exact.copy())
            v=vertical(exact,post);frame=folder/f'frame_{i+1:02d}.png';v.save(frame);frames.append(frame)
            words=len(post['copy'][i].split())+(len(req['cta'].split()) if i==5 else 0)
            duration=max(12,math.ceil(words/2.4+2));durations.append(duration)
            card_rows.append({'path':str(path.relative_to(OUT)),'sha256':sha(path),'source_crop':[x0,y0,x1,y1], 'duration_seconds':duration,**layout})
        contact(cards,folder/'cards_review.jpg',3,540)
        parts=['ffconcat version 1.0']
        for path,dur in zip(frames,durations):
            parts.extend([f"file '{path.as_posix()}'",f'duration {dur}'])
        parts.append(f"file '{frames[-1].as_posix()}'")
        concat=folder/'video.ffconcat';concat.write_text('\n'.join(parts)+'\n')
        video=folder/'youtube_vertical.mp4';total=sum(durations)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-safe','0','-i',str(concat),'-t',str(total),'-r','24','-c:v','libx264','-preset','ultrafast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart','-an',str(video)],check=True)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]))
        streams=probe['streams'];vs=[s for s in streams if s['codec_type']=='video'];aus=[s for s in streams if s['codec_type']=='audio']
        assert len(vs)==1 and not aus and vs[0]['width']==1080 and vs[0]['height']==1920
        assert abs(float(probe['format']['duration'])-total)<.1
        decoded=[];t=0
        for i,dur in enumerate(durations):
            output=folder/f'encoded_frame_{i+1:02d}.jpg'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(t+dur/2),'-i',str(video),'-frames:v','1','-q:v','2',str(output)],check=True)
            decoded.append(Image.open(output).convert('RGB'));t+=dur
        contact(decoded,folder/'encoded_video_review.jpg',3,360)
        for f in frames:f.unlink()
        concat.unlink()
        manifest['posts'].append({'id':post['id'],'title':post['title'],'time':post['time'],'fingerprint':post['fingerprint'],'qa_status':'NEEDS_EXACT_FINAL_REVIEW','cards':card_rows,'youtube_video':{'path':str(video.relative_to(OUT)),'sha256':sha(video),'width':1080,'height':1920,'duration_seconds':total,'card_durations':durations,'fps':24,'audio_streams':0},'caption':post['caption']})
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'rendered_candidates':len(manifest['posts']),'qa_status':manifest['qa_status']},ensure_ascii=False))

if __name__=='__main__':
    main()
