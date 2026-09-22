#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, os, shutil, subprocess, sys, time, wave
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps
sys.path.insert(0, str(Path(__file__).resolve().parent))
from azure_speech_tts import synthesize

W,H=1080,1920
SR=24000
FONT_SIZE=20
MARGIN_V=300

SCENE_ROOT="jobs/945c6068d41ab53d/work-current-20260924-1700-volcanic-lightning"

def run(cmd):
    subprocess.run([str(x) for x in cmd], check=True)

def duration(path:Path)->float:
    cp=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nk=1:nw=1",str(path)],capture_output=True,text=True,check=True)
    return float(cp.stdout.strip())

def srt_time(t:float)->str:
    ms=int(round(max(0,t)*1000))
    h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def split_caption(text,max_words=7,max_chars=40):
    words=text.split(); out=[]; cur=[]
    for w in words:
        cand=" ".join(cur+[w])
        if cur and (len(cur)>=max_words or len(cand)>max_chars):
            out.append(" ".join(cur)); cur=[w]
        else: cur.append(w)
    if cur: out.append(" ".join(cur))
    return out

def two_lines(chunk):
    words=chunk.split()
    if len(chunk)<=30 or len(words)<=3: return chunk
    mid=len(words)//2
    return " ".join(words[:mid])+"\\n"+" ".join(words[mid:])

def azure_one_shot(text, outwav):
    last=None
    for attempt in range(8):
        try:
            synthesize(text,outwav,"el-GR-NestorasNeural")
            return
        except RuntimeError as e:
            last=e
            if "HTTP 429" not in str(e) or attempt==7:
                raise
            wait=15*(attempt+1)
            print(f"Azure 429; retrying in {wait}s", flush=True)
            time.sleep(wait)
    raise last

def copy_scenes(work:Path,count:int):
    out=[]
    for i in range(1,count+1):
        src=f"{SCENE_ROOT}/scene-{i:02d}.jpg"
        dst=work/f"scene-{i:02d}.jpg"
        cp=subprocess.run(["git","show",f"origin/media-output:{src}"],capture_output=True,check=True)
        dst.write_bytes(cp.stdout)
        out.append(dst)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()

    manifest=json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    assert manifest["approved"] is True
    assert manifest["preview_only"] is True
    assert manifest["publish_to_social"] is False
    assert manifest["voice"]=="el-GR-NestorasNeural"

    segments=[x.strip() for x in manifest["narration_segments"] if x.strip()]
    if len(segments)<10: raise RuntimeError("too few segments")

    root=Path(a.output); shutil.rmtree(root,ignore_errors=True); root.mkdir(parents=True)
    work=root/"work"; work.mkdir()
    preview=root/"preview"; preview.mkdir()

    scenes=copy_scenes(work,len(segments))

    text="\n".join(segments)
    raw=work/"nestoras-raw.wav"
    azure_one_shot(text,raw)
    narration=work/"nestoras.wav"
    run(["ffmpeg","-y","-loglevel","error","-i",raw,"-af",
         "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-48dB,areverse,silenceremove=start_periods=1:start_duration=0.03:start_threshold=-48dB,areverse",
         "-ar",str(SR),"-ac","1","-c:a","pcm_s16le",narration])
    total=duration(narration)
    if total<=80: raise RuntimeError(f"duration gate failed {total:.2f}")

    # approximate segment timing by weighted visible characters; no silent padding.
    weights=[max(1,len(s.replace(" ",""))) for s in segments]
    sw=sum(weights)
    seg_d=[total*w/sw for w in weights]

    srt=work/"subtitles.srt"
    t=0.0; idx=1
    with srt.open("w",encoding="utf-8") as f:
        for text,d in zip(segments,seg_d):
            chunks=split_caption(text)
            cw=[max(1,len(c.replace(" ",""))) for c in chunks]; csum=sum(cw); used=0
            for c,w in zip(chunks,cw):
                st=t+d*used/csum; used+=w; en=t+d*used/csum
                f.write(f"{idx}\n{srt_time(st)} --> {srt_time(en)}\n{two_lines(c)}\n\n")
                idx+=1
            t+=d

    clips=[]
    for i,(scene,d) in enumerate(zip(scenes,seg_d),1):
        clip=work/f"clip-{i:02d}.mp4"
        frames=max(1,int(math.ceil(d*30)))
        direction=1 if i%2 else -1
        vf=("scale=1200:2134,"
            "zoompan=z='min(zoom+0.00022,1.035)':"
            f"x='iw/2-(iw/zoom/2)+{direction}*9*sin(on/45)':"
            "y='ih/2-(ih/zoom/2)+7*cos(on/53)':"
            f"d={frames}:s=1080x1920:fps=30,format=yuv420p")
        run(["ffmpeg","-y","-loglevel","error","-loop","1","-i",scene,"-vf",vf,
             "-t",f"{d:.4f}","-an","-c:v","libx264","-preset","veryfast","-crf","23",
             "-pix_fmt","yuv420p",clip])
        clips.append(clip)

    concat=work/"clips.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips),encoding="utf-8")
    visual=work/"visual.mp4"
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",concat,
         "-an","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p","-r","30",visual])

    escaped=str(srt).replace("\\","\\\\").replace(":","\\:").replace("'","\\'")
    style=("FontName=DejaVu Sans,FontSize=20,PrimaryColour=&H00FFFFFF,"
           "OutlineColour=&H00000000,BackColour=&H90000000,BorderStyle=3,"
           "Outline=1,Shadow=0,Alignment=2,MarginL=92,MarginR=92,MarginV=300")
    final=preview/"volcanic-lightning-nestoras-final-preview.mp4"
    run(["ffmpeg","-y","-loglevel","error","-i",visual,"-i",narration,
         "-vf",f"subtitles='{escaped}':force_style='{style}'",
         "-c:v","libx264","-preset","medium","-crf","21","-pix_fmt","yuv420p",
         "-c:a","aac","-b:a","128k","-ar","48000","-ac","1","-shortest","-movflags","+faststart",final])

    fd=duration(final)
    probe=json.loads(subprocess.run(["ffprobe","-v","error","-show_streams","-of","json",str(final)],capture_output=True,text=True,check=True).stdout)
    vs=[s for s in probe["streams"] if s.get("codec_type")=="video"]
    au=[s for s in probe["streams"] if s.get("codec_type")=="audio"]
    if len(vs)!=1 or len(au)!=1 or int(vs[0]["width"])!=W or int(vs[0]["height"])!=H or fd<=80:
        raise RuntimeError("QA failed")
    qa={
        "id":"volcanic-lightning-nestoras-final-preview",
        "preview_only":True,
        "publish_to_social":False,
        "voice":"el-GR-NestorasNeural",
        "duration_seconds":round(fd,3),
        "resolution":"1080x1920",
        "burned_subtitles":True,
        "subtitle_font_size":20,
        "subtitle_margin_vertical":300,
        "subtitle_max_lines":2,
        "photo_or_scene_count":len(scenes),
        "background_music":False,
        "avatar_presenter":False,
        "audio_streams":1
    }
    (preview/"qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.copy2(srt,preview/"subtitles.srt")
    (preview/"script.txt").write_text("\n".join(segments),encoding="utf-8")
    print(json.dumps(qa,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
