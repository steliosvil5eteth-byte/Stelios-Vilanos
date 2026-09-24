#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, math, re, shutil, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from azure_speech_tts import synthesize

W, H, FPS = 1080, 1920, 30
VOICE = "el-GR-NestorasNeural"
UA = "SteliosTravelVideo/2.0 (Wikimedia Commons attribution workflow)"


def run(cmd):
    subprocess.run([str(x) for x in cmd], check=True)


def duration(path: Path) -> float:
    cp = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nk=1:nw=1",str(path)], capture_output=True, text=True, check=True)
    return float(cp.stdout.strip())


def srt_time(t: float) -> str:
    ms=int(round(max(0.0,t)*1000)); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def caption_chunks(text,max_words=8,max_chars=46):
    out=[]; cur=[]
    for w in text.split():
        cand=" ".join(cur+[w])
        if cur and (len(cur)>=max_words or len(cand)>max_chars): out.append(" ".join(cur)); cur=[w]
        else: cur.append(w)
    if cur: out.append(" ".join(cur))
    return out


def two_lines(text):
    words=text.split()
    if len(text)<=38 or len(words)<=4: return text
    best=None
    for i in range(1,len(words)):
        a=" ".join(words[:i]); b=" ".join(words[i:]); score=max(len(a),len(b))+0.25*abs(len(a)-len(b))
        if best is None or score<best[0]: best=(score,a,b)
    return best[1]+"\\n"+best[2]


def open_retry(req,attempts=6):
    last=None
    for n in range(attempts):
        try: return urllib.request.urlopen(req,timeout=120)
        except Exception as exc:
            last=exc
            if n==attempts-1: raise
            time.sleep(4*(n+1))
    raise last


def norm_name(s): return s.replace("_"," ").strip().casefold()


def resolve_commons(images):
    titles="|".join("File:"+x["filename"] for x in images)
    params=urllib.parse.urlencode({"action":"query","format":"json","prop":"imageinfo","iiprop":"url","iiurlwidth":"1800","titles":titles})
    req=urllib.request.Request("https://commons.wikimedia.org/w/api.php?"+params,headers={"User-Agent":UA})
    with open_retry(req) as r: payload=json.load(r)
    found={}
    for page in payload.get("query",{}).get("pages",{}).values():
        title=page.get("title","")
        if title.startswith("File:") and "imageinfo" in page:
            info=page["imageinfo"][0]
            found[norm_name(title[5:])] = info.get("thumburl") or info.get("url")
    urls=[]
    for img in images:
        u=found.get(norm_name(img["filename"]))
        if not u: raise RuntimeError(f"Wikimedia image could not be resolved: {img['filename']}")
        urls.append(u)
    return urls


def download(url,dest):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    with open_retry(req) as r: data=r.read()
    if len(data)<20000: raise RuntimeError(f"Image download too small: {url}")
    dest.write_bytes(data)
    with Image.open(dest) as im: im.verify()


def make_scene(src,dst):
    with Image.open(src) as im:
        im=ImageOps.exif_transpose(im).convert("RGB")
        bg=ImageOps.fit(im,(W,H),method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(28))
        bg=Image.blend(bg,Image.new("RGB",(W,H),(0,0,0)),0.12)
        scale=min(1000/im.width,1500/im.height,1.0)
        fg=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.LANCZOS)
        bg.paste(fg,((W-fg.width)//2,(H-fg.height)//2)); bg.save(dst,quality=94,optimize=True)


def synth(text,out):
    last=None
    for attempt in range(8):
        try: synthesize(text,out,VOICE); return
        except RuntimeError as exc:
            last=exc
            if "HTTP 429" not in str(exc) or attempt==7: raise
            time.sleep(15*(attempt+1))
    raise last


def safe_slug(s):
    return re.sub(r"[^a-z0-9-]+","-",s.lower()).strip("-") or "travel"


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--manifest",required=True); ap.add_argument("--output",required=True); a=ap.parse_args()
    m=json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    assert m["approved"] is True and m["publish_to_social"] is True
    assert m["voice"]==VOICE and m["background_music"] is False and m["min_duration_seconds"]>=80
    seg=[x.strip() for x in m["narration_segments"] if x.strip()]; imgs=m["images"]
    if len(seg)!=len(imgs) or len(seg)<10: raise RuntimeError("scene count mismatch")
    if seg[-1] != "Αν σας άρεσε, ακολουθήστε για περισσότερα.": raise RuntimeError("exact CTA missing")
    for img in imgs:
        if not img.get("filename") or not img.get("author") or not img.get("license") or not img.get("source_url") or not img.get("scene"):
            raise RuntimeError("incomplete image attribution")
        if "commons.wikimedia.org/wiki/File:" not in img["source_url"]:
            raise RuntimeError("only verified Wikimedia Commons file pages are allowed")

    root=Path(a.output); shutil.rmtree(root,ignore_errors=True); work=root/"work"; result=root/"result"; work.mkdir(parents=True); result.mkdir(parents=True)
    urls=resolve_commons(imgs)
    scenes=[]
    for i,(img,u) in enumerate(zip(imgs,urls),1):
        raw=work/f"source-{i:02d}.jpg"; scene=work/f"scene-{i:02d}.jpg"
        download(u,raw); make_scene(raw,scene); scenes.append(scene); time.sleep(0.8)

    wavs=[]; ds=[]
    for i,text in enumerate(seg,1):
        raw=work/f"a-{i:02d}-raw.wav"; wav=work/f"a-{i:02d}.wav"; synth(text,raw)
        run(["ffmpeg","-y","-loglevel","error","-i",raw,"-af","silenceremove=start_periods=1:start_duration=0.03:start_threshold=-48dB,areverse,silenceremove=start_periods=1:start_duration=0.03:start_threshold=-48dB,areverse","-ar","24000","-ac","1","-c:a","pcm_s16le",wav])
        d=duration(wav)
        if d<=1: raise RuntimeError(f"audio segment {i} too short")
        wavs.append(wav); ds.append(d)
    total=sum(ds)
    if total<=m["min_duration_seconds"]: raise RuntimeError(f"duration gate failed: {total:.2f}s")

    srt=work/"subtitles.srt"; t=0.0; idx=1
    with srt.open("w",encoding="utf-8") as f:
        for text,d in zip(seg,ds):
            chunks=caption_chunks(text); weights=[max(1,len(c.replace(" ",""))) for c in chunks]; sw=sum(weights); used=0
            for c,w in zip(chunks,weights):
                st=t+d*used/sw; used+=w; en=t+d*used/sw
                f.write(f"{idx}\n{srt_time(st)} --> {srt_time(en)}\n{two_lines(c)}\n\n"); idx+=1
            t+=d

    al=work/"audio-list.txt"; al.write_text("".join(f"file '{p.as_posix()}'\n" for p in wavs),encoding="utf-8"); narration=work/"narration.wav"
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",al,"-c:a","pcm_s16le",narration])

    clips=[]
    for i,(scene,d) in enumerate(zip(scenes,ds),1):
        clip=work/f"clip-{i:02d}.mp4"; frames=max(1,int(math.ceil(d*FPS))); direction=1 if i%2 else -1
        vf=("scale=1140:2027,"+"zoompan=z='min(zoom+0.00018,1.028)':"+f"x='iw/2-(iw/zoom/2)+{direction}*7*sin(on/48)':"+"y='ih/2-(ih/zoom/2)+6*cos(on/55)':"+f"d={frames}:s=1080x1920:fps={FPS},format=yuv420p")
        run(["ffmpeg","-y","-loglevel","error","-loop","1","-i",scene,"-vf",vf,"-t",f"{d:.4f}","-an","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p",clip]); clips.append(clip)
    cl=work/"clips.txt"; cl.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips),encoding="utf-8"); visual=work/"visual.mp4"
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",cl,"-an","-c:v","libx264","-preset","veryfast","-crf","21","-pix_fmt","yuv420p","-r",str(FPS),visual])

    escaped=str(srt).replace("\\","\\\\").replace(":","\\:").replace("'","\\'")
    style="FontName=DejaVu Sans,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H90000000,BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginL=88,MarginR=88,MarginV=290"
    final=result/(safe_slug(m["id"])+".mp4")
    run(["ffmpeg","-y","-loglevel","error","-i",visual,"-i",narration,"-vf",f"subtitles='{escaped}':force_style='{style}'","-c:v","libx264","-preset","medium","-crf","21","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-ar","48000","-ac","1","-shortest","-movflags","+faststart",final])
    fd=duration(final); probe=json.loads(subprocess.run(["ffprobe","-v","error","-show_streams","-of","json",str(final)],capture_output=True,text=True,check=True).stdout); vs=[s for s in probe["streams"] if s.get("codec_type")=="video"]; au=[s for s in probe["streams"] if s.get("codec_type")=="audio"]
    if len(vs)!=1 or len(au)!=1 or int(vs[0]["width"])!=W or int(vs[0]["height"])!=H or fd<=80: raise RuntimeError("final QA failed")
    qa={"id":m["id"],"destination":m["destination"],"publish_to_social":True,"voice":VOICE,"duration_seconds":round(fd,3),"resolution":"1080x1920","burned_subtitles":True,"background_music":False,"avatar_presenter":False,"audio_streams":1,"photo_count":len(imgs),"all_visuals_real_photos":True,"cta_exact":True,"min_duration_gate_passed":fd>80,"final_filename":final.name}
    (result/"qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding="utf-8")
    (result/"script.txt").write_text("\n\n".join(seg),encoding="utf-8")
    shutil.copy2(srt,result/"subtitles.srt")
    (result/"visual-attribution.json").write_text(json.dumps(imgs,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(qa,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
