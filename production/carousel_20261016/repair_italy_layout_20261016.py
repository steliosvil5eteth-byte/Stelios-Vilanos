from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json, math, shutil, subprocess

SRC = Path('/tmp/greece-italy-drfWEA/files')
OUT = Path('/tmp/greece-italy-drfWEA/repaired')
OUT.mkdir(parents=True, exist_ok=True)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
INK = (25, 32, 38)
PAPER = (247, 243, 235)

def ft(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)

def wrap(text, font, width):
    lines = []
    for para in text.split('\n'):
        line = ''
        for word in para.split():
            trial = (line + ' ' + word).strip()
            if font.getlength(trial) > width and line:
                lines.append(line)
                line = word
            else:
                line = trial
        if line:
            lines.append(line)
    return lines

def draw_fit(draw, text, xy, width, max_size, min_size, max_lines, bold=False, spacing=1.18):
    x, y = xy
    for size in range(max_size, min_size - 1, -1):
        font = ft(size, bold)
        lines = wrap(text, font, width)
        if len(lines) <= max_lines:
            break
    else:
        raise RuntimeError(f'Cannot fit: {text}')
    step = math.ceil(size * spacing)
    for line in lines:
        draw.text((x, y), line, font=font, fill=INK)
        y += step
    return size, y

manifest = json.loads((SRC / 'manifest.json').read_text())
photo_by_path = {p['path']: p for p in manifest['photographs']}
affected = {2, 4, 6, 8}

for i, card in enumerate(manifest['cards'], start=1):
    source = SRC / f'card_{i:02d}.jpg'
    target = OUT / source.name
    if i not in affected:
        shutil.copy2(source, target)
        continue
    image = Image.open(source).convert('RGB')
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 420, 1080, 1080), fill=PAPER)
    copy = card['copy']
    photo = photo_by_path[card['photo']]
    draw_fit(draw, copy['heading'], (45, 445), 990, 45, 36, 2, True)
    draw_fit(draw, copy['label'], (45, 525), 990, 35, 29, 2)
    draw_fit(draw, 'Ελλάδα: ' + copy['gr'], (45, 625), 990, 51, 40, 1, True)
    draw_fit(draw, 'Ιταλία: ' + copy['it'], (45, 705), 990, 51, 40, 1, True)
    draw_fit(draw, copy['note'], (45, 790), 990, 31, 26, 4)
    draw_fit(draw, copy['source'], (45, 950), 990, 23, 19, 2)
    draw_fit(draw, 'Φωτ.: ' + photo['artist'] + ' · ' + photo['license'], (45, 1014), 990, 20, 16, 2)
    image.save(target, quality=95, subsampling=0)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

for i, card in enumerate(manifest['cards'], start=1):
    card['sha256'] = sha(OUT / f'card_{i:02d}.jpg')
    card['path'] = f'greece_italy_repaired/card_{i:02d}.jpg'

frames = []
for i in range(1, 11):
    card = Image.open(OUT / f'card_{i:02d}.jpg').convert('RGB')
    frame = Image.new('RGB', (1080, 1920), (235, 232, 224))
    draw = ImageDraw.Draw(frame)
    draw.text((70, 178), 'Ελλάδα VS Ιταλία', font=ft(62, True), fill=INK)
    frame.paste(card.resize((1020, 1020), Image.Resampling.LANCZOS), (30, 445))
    draw.text((70, 1560), '10 κάρτες · Στοιχεία με πηγές και έτη', font=ft(39, True), fill=INK)
    draw.text((70, 1690), 'Ιστορίες που μας αγγίζουν', font=ft(39), fill=INK)
    path = OUT / f'frame_{i:02d}.png'
    frame.save(path)
    frames.append(path)

concat = OUT / 'slides.ffconcat'
parts = ['ffconcat version 1.0']
for frame in frames:
    parts += [f"file '{frame}'", 'duration 16']
parts.append(f"file '{frames[-1]}'")
concat.write_text('\n'.join(parts) + '\n')
video = OUT / 'youtube_vertical.mp4'
subprocess.run([
    'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-safe', '0', '-i', str(concat),
    '-vf', 'fps=2', '-t', '160', '-c:v', 'libx264', '-threads', '1',
    '-preset', 'ultrafast', '-crf', '21', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', str(video)
], check=True)
probe = json.loads(subprocess.check_output([
    'ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(video)
]))
assert abs(float(probe['format']['duration']) - 160) < 0.05
assert not any(s['codec_type'] == 'audio' for s in probe['streams'])
manifest['qa_status'] = 'NEEDS_NEW_EXACT_FINAL_REVIEW_AFTER_LAYOUT_REPAIR'
manifest['repair'] = {
    'reason': 'Country labels and source/credit lines clipped on cards 02,04,06,08',
    'affected_cards': [2, 4, 6, 8],
    'unchanged_cards': [1, 3, 5, 7, 9, 10]
}
manifest['youtube_video']['path'] = 'greece_italy_repaired/youtube_vertical.mp4'
manifest['youtube_video']['sha256'] = sha(video)
manifest['youtube_video']['fps'] = 2
(OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
shutil.copy2(SRC / 'SOURCES.md', OUT / 'SOURCES.md')
for p in frames:
    p.unlink()
concat.unlink()
print(json.dumps({
    'cards': {f'{i:02d}': sha(OUT / f'card_{i:02d}.jpg') for i in range(1, 11)},
    'video': sha(video), 'duration': float(probe['format']['duration']), 'audio_streams': 0
}, ensure_ascii=False, indent=2))
