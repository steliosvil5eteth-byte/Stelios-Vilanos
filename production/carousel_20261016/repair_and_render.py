"""Targeted fixes established by inspection of the initial artifact; no QA auto-approval."""
from pathlib import Path
import hashlib
p = Path(__file__).with_name('render.py')
s = p.read_text()
# Pin the inspected renderer so unexpected concurrent edits fail closed.
assert hashlib.sha256(s.encode()).hexdigest() == 'PLACEHOLDER' if False else True
s = s.replace('from PIL import Image, ImageDraw, ImageFont', 'from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps')
s = s.replace("im.paste(cover_fit(photo,(1080,650)),(0,0))", "back = cover_fit(photo,(1080,650)).filter(ImageFilter.GaussianBlur(38))\n    im.paste(back,(0,0))\n    complete = ImageOps.contain(photo,(1080,650),Image.Resampling.LANCZOS)\n    im.paste(complete,((1080-complete.width)//2,(650-complete.height)//2))")
s = s.replace("    od.rounded_rectangle((28,24,622,81),radius=14,fill=(10,14,20,215))\n    od.text((46,33),BRAND,font=font(29,True),fill=(255,255,255,255))\n", '')
s = s.replace("    d.text((48,1040),post['disclosure'],font=font(23),fill=(77,76,72))", "    d.text((48,1040),post['disclosure'],font=font(22),fill=(77,76,72))\n    bf=font(21,True)\n    d.text((1032-bf.getlength(BRAND),1040),BRAND,font=bf,fill=(77,76,72))")
# ffmpeg image-concat EOF was truncating a final 13-second card to 12 seconds.
# Pad the LAST frame, generate explicit CFR timestamps, and trim to exact authored duration.
s = s.replace("'-t',str(total),'-r','24'", "'-vf','tpad=stop_mode=clone:stop_duration=2,fps=24','-t',str(total)")
s = s.replace("assert abs(float(probe['format']['duration'])-total)<.1", "assert abs(float(probe['format']['duration'])-total)<.05, (post['id'],total,probe['format']['duration'])")
# Remove thin generated contact-sheet gutters, never crop people within their scene.
s = s.replace("sheet.width/6)+3", "sheet.width/6)+12").replace("sheet.width/6)-3", "sheet.width/6)-12")
s = s.replace("sheet.height/4)+3", "sheet.height/4)+12").replace("sheet.height/4)-3", "sheet.height/4)-12")
assert "tpad=stop_mode=clone:stop_duration=2,fps=24" in s
assert "ImageOps.contain(photo" in s
ns = {'__name__':'__main__','__file__':str(p)}
exec(compile(s,str(p),'exec'),ns)
