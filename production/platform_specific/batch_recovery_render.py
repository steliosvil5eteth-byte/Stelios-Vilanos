#!/usr/bin/env python3
"""Build one local review video from an exact voice track and a source inventory.

No network, TTS, ASR, or publishing calls occur here. Supplied subtitle timings
are preserved. Exports remain NEEDS_FINAL_REVIEW; this renderer cannot attest
that anyone watched or listened to the result. A dry run is the default.
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import hashlib
import html
import json
import math
import re
import subprocess
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from recovery_resource_limits import resource_slot

VOICE = "el-GR-NestorasNeural"
CTA = "Αν σας άρεσε, ακολουθήστε για περισσότερα."
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
WIDTH, HEIGHT, FPS = 1080, 1920, 30
SUB_SIZE, SUB_WIDTH = 64, 850
ALLOWED_PLATFORMS = {"facebook", "instagram", "tiktok", "youtube"}


class RenderBlocked(RuntimeError):
    pass


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def run(args: list[str], cwd: Path | None = None, log_path: Path | None = None) -> str:
    if Path(args[0]).name == "ffmpeg" and "-nostdin" not in args:
        args = [args[0], "-nostdin", *args[1:]]
    slot = None
    if Path(args[0]).name == "ffmpeg":
        with resource_slot("ffmpeg") as slot:
            result = subprocess.run(args, cwd=cwd, stdin=subprocess.DEVNULL, text=True, capture_output=True)
    else:
        result = subprocess.run(args, cwd=cwd, stdin=subprocess.DEVNULL, text=True, capture_output=True)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps({"command": args, "cwd": str(cwd) if cwd else None,
                                       "returncode": result.returncode, "stdout": result.stdout,
                                       "stderr": result.stderr, "resource_slot": slot}, ensure_ascii=False, indent=2) + "\n")
    if result.returncode:
        raise RenderBlocked(f"{Path(args[0]).name} failed: {result.stderr[-2500:]}")
    return result.stdout


def probe(path: Path) -> dict:
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))


def words(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold(), re.UNICODE)


def seconds(value: str) -> float:
    h, m, s = value.replace(",", ".").split(":")
    return 3600 * int(h) + 60 * int(m) + float(s)


def ass_time(value: float) -> str:
    cs = round(value * 100)
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def wrap_two_lines(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    if font.getlength(text) <= width:
        return [text]
    tokens, choices = text.split(), []
    for cut in range(1, len(tokens)):
        pair = [" ".join(tokens[:cut]), " ".join(tokens[cut:])]
        widths = [font.getlength(line) for line in pair]
        if max(widths) <= width:
            choices.append((abs(widths[0] - widths[1]), pair))
    if not choices:
        raise RenderBlocked("Cue exceeds two measured 64px subtitle lines. Regroup actual word-boundary cues; do not invent new timings. " + text)
    return min(choices, key=lambda item: item[0])[1]


def derive_narration(mp3: Path, boundaries_path: Path, script_path: Path, output: Path) -> dict:
    """Decode existing speech and group its actual word timestamps into cues.

    Punctuation comes from the exact source script. Paragraphs cannot straddle a
    subtitle cue; no words or timestamps are guessed, stretched, or synthesized.
    """
    script = script_path.read_text(encoding="utf-8").strip()
    paragraphs = [part.split() for part in re.split(r"\n\s*\n", script) if part.strip()]
    tokens = [token for paragraph in paragraphs for token in paragraph]
    actual_events = json.loads(boundaries_path.read_text(encoding="utf-8"))
    if len(paragraphs) not in (8, 9):
        raise RenderBlocked("The exact script must have eight or nine paragraphs")
    audio_duration = float(probe(mp3)["format"]["duration"])
    for i, boundary in enumerate(actual_events):
        if not 0 <= boundary["start"] < boundary["end"] <= audio_duration + .06:
            raise RenderBlocked(f"Actual speech word {i + 1} has an invalid timestamp")
        if i and boundary["start"] < actual_events[i - 1]["end"] - .003:
            raise RenderBlocked("Actual speech word timestamps overlap")
    # Find the smallest indivisible units whose boundaries are BOTH written
    # token boundaries and actual speech-event boundaries. This permits Ό,τι
    # as two real events, or a single event such as "1921 Ύπατος", without
    # splitting an event or inventing an internal timestamp.
    lexical_script, script_ends = [], {0: 0}
    for index, token in enumerate(tokens, 1):
        parts = words(token)
        if not parts:
            raise RenderBlocked("A script token has no lexical content")
        lexical_script.extend(parts)
        script_ends[len(lexical_script)] = index
    lexical_events, event_ends = [], {0: 0}
    for index, event in enumerate(actual_events, 1):
        parts = words(event["text"])
        if not parts:
            raise RenderBlocked("A word event has no lexical content")
        lexical_events.extend(parts)
        event_ends[len(lexical_events)] = index
    if lexical_script != lexical_events:
        raise RenderBlocked("The full actual speech-event lexical sequence differs from the exact script")
    common_ends = sorted(set(script_ends) & set(event_ends))
    paragraph_ends, lexical_cursor = [], 0
    for paragraph in paragraphs:
        lexical_cursor += sum(len(words(token)) for token in paragraph)
        paragraph_ends.append(lexical_cursor)
    if not set(paragraph_ends).issubset(common_ends):
        raise RenderBlocked("An indivisible actual speech event crosses a narration paragraph boundary")
    boundaries, token_event_alignment = [], []
    timed_paragraphs = [[] for _ in paragraphs]
    paragraph_index, previous_end = 0, 0
    for end in common_ends[1:]:
        token_start, token_end = script_ends[previous_end], script_ends[end]
        event_start, event_end = event_ends[previous_end], event_ends[end]
        text = " ".join(tokens[token_start:token_end])
        boundaries.append({"text": text, "start": actual_events[event_start]["start"],
                           "end": actual_events[event_end - 1]["end"]})
        token_event_alignment.append({"script_token_start_index": token_start,
                                      "script_token_end_index_exclusive": token_end,
                                      "actual_event_start_index": event_start,
                                      "actual_event_end_index_exclusive": event_end})
        timed_paragraphs[paragraph_index].append(text)
        if end == paragraph_ends[paragraph_index]:
            paragraph_index += 1
        previous_end = end
    paragraphs = timed_paragraphs
    font = ImageFont.truetype(str(FONT), SUB_SIZE)
    groups, offset = [], 0
    for paragraph_number, paragraph in enumerate(paragraphs, 1):
        @functools.lru_cache(None)
        def partition(start: int) -> tuple[float, tuple[tuple[int, int], ...]]:
            if start == len(paragraph):
                return 0.0, ()
            options = []
            for end in range(start + 1, min(len(paragraph), start + 7) + 1):
                caption = " ".join(paragraph[start:end])
                try:
                    wrap_two_lines(caption, font, SUB_WIDTH)
                except RenderBlocked:
                    continue
                count = sum(len(unit.split()) for unit in paragraph[start:end])
                if count > 7:
                    continue
                elapsed = boundaries[offset + end - 1]["end"] - boundaries[offset + start]["start"]
                if elapsed > 3.6:
                    continue
                crossing = sum(bool(re.search(r"[.!;·:]$", token)) for token in paragraph[start:end - 1])
                punctuation = bool(re.search(r"[.!;·:,]$", paragraph[end - 1]))
                local_cost = .12 * (count - 5) ** 2 + .2 * (elapsed - 2.1) ** 2
                local_cost += 3 * crossing + (0 if punctuation or end == len(paragraph) else .85)
                local_cost += 4 if count < 3 else 0
                following_cost, following = partition(end)
                options.append((local_cost + following_cost, ((start, end),) + following))
            if not options:
                return float("inf"), ()
            return min(options, key=lambda option: option[0])
        cost, chosen = partition(0)
        if not math.isfinite(cost):
            raise RenderBlocked("Actual speech cannot fit safe short subtitle cues without changing timestamps")
        for start, end in chosen:
            first_alignment = token_event_alignment[offset + start]
            last_alignment = token_event_alignment[offset + end - 1]
            groups.append({"number": len(groups) + 1, "paragraph": paragraph_number,
                           "word_start_index": first_alignment["script_token_start_index"],
                           "word_end_index_exclusive": last_alignment["script_token_end_index_exclusive"],
                           "actual_event_start_index": first_alignment["actual_event_start_index"],
                           "actual_event_end_index_exclusive": last_alignment["actual_event_end_index_exclusive"],
                           "start": boundaries[offset + start]["start"],
                           "end": boundaries[offset + end - 1]["end"],
                           "text": " ".join(paragraph[start:end])})
        offset += len(paragraph)
    def srt_time(value: float) -> str:
        ms = round(value * 1000)
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    wav, srt = output / "narration.wav", output / "narration.srt"
    audit_path = output / "subtitle_derivation.json"
    if any(path.exists() for path in (wav, srt, audit_path)):
        raise RenderBlocked("Derived narration outputs already exist; preserve them")
    output.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-v", "error", "-i", str(mp3), "-map", "0:a:0", "-vn", "-c:a", "pcm_s16le", str(wav)])
    srt.write_text("\n\n".join(f"{g['number']}\n{srt_time(g['start'])} --> {srt_time(g['end'])}\n{g['text']}" for g in groups) + "\n", encoding="utf-8")
    decoded_duration = float(probe(wav)["format"]["duration"])
    read_cues(srt, script, decoded_duration)
    audit = {"source_mp3_sha256": digest(mp3), "actual_word_boundaries_sha256": digest(boundaries_path),
             "script_sha256": digest(script_path), "wav_sha256": digest(wav), "srt_sha256": digest(srt),
             "script_words": len(tokens), "actual_boundary_count": len(actual_events), "subtitle_cues": groups,
             "atomic_speech_units": token_event_alignment,
             "subtitle_word_indices_reference": "Script whitespace tokens; each maps to complete actual events above",
             "word_alignment_exact": True, "paragraph_boundaries_preserved": True,
             "source_duration_seconds": audio_duration, "decoded_duration_seconds": decoded_duration,
             "timing_source": "Actual WordBoundary events from this exact existing narration",
             "srt_rounding_max_seconds": .0005, "audio_synthesized": False,
             "audio_time_stretch_or_padding": False, "actual_audio_listened": False}
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return audit


def read_cues(path: Path, script: str, duration: float) -> list[dict]:
    font = ImageFont.truetype(str(FONT), SUB_SIZE)
    cues, token_cursor = [], 0
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    for block in re.split(r"\n\s*\n", text.strip()):
        rows = block.splitlines()
        timing_index = next((i for i, row in enumerate(rows) if "-->" in row), None)
        if timing_index is None:
            raise RenderBlocked("Malformed SRT cue")
        start_text, end_text = rows[timing_index].split("-->", 1)
        start, end = seconds(start_text.strip()), seconds(end_text.strip().split()[0])
        caption = html.unescape(" ".join(" ".join(rows[timing_index + 1:]).split()))
        if re.search(r"<[^>]+>", caption):
            raise RenderBlocked("Unexpected markup in source captions")
        if not caption or not 0 <= start < end <= duration + .06:
            raise RenderBlocked("SRT timing falls outside actual narration")
        if cues and start < cues[-1]["end"] - .003:
            raise RenderBlocked("SRT cues overlap")
        lines = wrap_two_lines(caption, font, SUB_WIDTH)
        count = len(words(caption))
        cues.append({"number": len(cues) + 1, "start": start, "end": min(end, duration),
                     "text": caption, "lines": lines, "token_start": token_cursor,
                     "token_end": token_cursor + count,
                     "line_widths_px": [round(font.getlength(line), 2) for line in lines]})
        token_cursor += count
    if not cues or words(" ".join(c["text"] for c in cues)) != words(script):
        raise RenderBlocked("Subtitle words do not match the complete exact narration script")
    if words(script)[-len(words(CTA)):] != words(CTA):
        raise RenderBlocked("The exact final CTA is missing from the script")
    return cues


def scene_timeline(script: str, cues: list[dict], duration: float) -> list[dict]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", script.strip()) if part.strip()]
    if len(paragraphs) not in (8, 9):
        raise RenderBlocked("The active source packs contain eight or nine narration paragraphs")
    starts, cursor = [0.0], 0
    for paragraph in paragraphs[:-1]:
        cursor += len(words(paragraph))
        aligned = next(c for c in cues if c["token_start"] <= cursor < c["token_end"])
        starts.append(aligned["start"])
    boundaries = [0] + [round(value * FPS) for value in starts[1:]] + [math.ceil(duration * FPS)]
    if any(b <= a for a, b in zip(boundaries, boundaries[1:])):
        raise RenderBlocked("Scene boundaries are not distinct and ordered")
    return [{"scene": i + 1, "start": boundaries[i] / FPS,
             "end": min(boundaries[i + 1] / FPS, duration),
             "frames": boundaries[i + 1] - boundaries[i],
             "timing_basis": "Actual SRT cue containing first word of narration paragraph",
             "paragraph": paragraphs[i]} for i in range(len(paragraphs))]


def read_sources(path: Path, paragraph_count: int) -> list[dict]:
    inventory = json.loads(path.read_text(encoding="utf-8"))
    sources = sorted(inventory["assets"], key=lambda item: item["scene"])
    if [item["scene"] for item in sources] != list(range(1, paragraph_count + 1)):
        raise RenderBlocked("Every narration paragraph requires one ordered source asset")
    seen_sources = {}
    for source in sources:
        if source.get("paragraph_index", source["scene"]) != source["scene"]:
            raise RenderBlocked("Source paragraph mapping is out of order")
        original_diagram = (source.get("original_user_composition") is True
                            and source.get("kind") == "explanatory_diagram")
        provenance_fields = ["asset_label", "creator", "license"]
        if original_diagram:
            provenance_fields += ["rightsholder", "copyright_statement"]
            scientific_sources = source.get("scientific_source_urls")
            if (not isinstance(scientific_sources, list) or not scientific_sources
                    or any(not isinstance(url, str) or not re.match(r"https?://[^/\s]+", url)
                           for url in scientific_sources)):
                raise RenderBlocked("An original explanatory diagram requires its scientific-source URLs")
        else:
            provenance_fields += ["source_page_url", "license_url"]
        for field in provenance_fields:
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise RenderBlocked(f"Source provenance field {field} is missing")
        source_path = Path(source.get("path", source.get("local_path", ""))).resolve()
        if digest(source_path) != source["sha256"]:
            raise RenderBlocked(f"Source bytes changed: scene {source['scene']}")
        with Image.open(source_path) as bitmap:
            bitmap.verify()
        source["path"] = str(source_path)
        previous = seen_sources.get(source["sha256"])
        if previous is not None:
            reason = source.get("source_reuse_reason", "")
            if not isinstance(reason, str) or not reason.strip():
                raise RenderBlocked("An intentionally repeated source needs source_reuse_reason")
            identity_fields = ("source_page_url", "creator", "license", "license_url",
                               "original_user_composition", "kind", "rightsholder",
                               "copyright_statement", "scientific_source_urls")
            if any(source.get(field) != previous.get(field) for field in identity_fields):
                raise RenderBlocked("Repeated source bytes have inconsistent source identity or attribution")
            source["source_reused_from_scene"] = previous["scene"]
        else:
            seen_sources[source["sha256"]] = source
    return sources


def render_frame(source: dict, output: Path) -> dict:
    with Image.open(source["path"]) as opened:
        photo = ImageOps.exif_transpose(opened).convert("RGB")
    # A quiet same-image background maintains the vertical canvas while the
    # foreground of geographically wide photos remains complete and undistorted.
    background = ImageOps.fit(photo, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(42))
    background = ImageEnhance.Brightness(background).enhance(.46)
    mode = source.get("layout", "contain")
    if mode not in ("contain", "cover"):
        raise RenderBlocked("An asset layout must be contain or cover")
    focus_x, focus_y = source.get("crop_focus", [.5, .5])
    if not 0 <= focus_x <= 1 or not 0 <= focus_y <= 1:
        raise RenderBlocked("Crop focus coordinates must fall between zero and one")
    box = (0, 390, WIDTH, 1390)
    if mode == "contain":
        foreground = ImageOps.contain(photo, (WIDTH, box[3] - box[1]), method=Image.Resampling.LANCZOS)
    else:
        foreground = ImageOps.fit(photo, (WIDTH, box[3] - box[1]), method=Image.Resampling.LANCZOS,
                                  centering=(focus_x, focus_y))
    x = (WIDTH - foreground.width) // 2
    y = box[1] + (box[3] - box[1] - foreground.height) // 2
    background.paste(foreground, (x, y))
    draw = ImageDraw.Draw(background)
    draw.rounded_rectangle((52, 1460, 954, 1695), radius=24, fill=(9, 16, 20))
    label_font = ImageFont.truetype(str(REGULAR), 30)
    label = source.get("context_label", source["asset_label"])
    label_lines = wrap_two_lines(label, label_font, 880)
    for line_number, text in enumerate(label_lines):
        draw.text((504 - label_font.getlength(text) / 2, 299 + line_number * 39), text,
                  font=label_font, fill=(238, 243, 246))
    credit = source.get("creator_display", source["creator"]) + " · " + source["license"].replace("-", " ")
    credit_font = ImageFont.truetype(str(REGULAR), 21)
    if credit_font.getlength(credit) > 880:
        raise RenderBlocked("Source credit needs a reviewed shorter display form")
    draw.text((64, 1418), credit, font=credit_font, fill=(217, 225, 229))
    background.save(output, quality=95, subsampling=0)
    return {"scene": source["scene"], "layout": mode, "source_dimensions": list(photo.size),
            "foreground_rect": [x, y, foreground.width, foreground.height],
            "complete_source_preserved": mode == "contain", "crop_focus": [focus_x, focus_y],
            "frame_sha256": digest(output), "background": "Blurred darker same-source image",
            "visible_credit": credit, "visible_context_label": label,
            "final_visual_review_passed": False}


def escaped(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def write_ass(path: Path, title: str, cues: list[dict], duration: float,
              disclosure: str = "Αρχειακό υλικό · Συνθετική αφήγηση") -> None:
    title_lines = wrap_two_lines(title, ImageFont.truetype(str(FONT), 52), 880)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,DejaVu Sans,64,&H00FFFFFF,&H00FFFFFF,&H00141009,&H00141009,-1,0,0,0,100,100,0,0,1,1.8,0,5,64,156,0,1
Style: Title,DejaVu Sans,52,&H00FFFFFF,&H00FFFFFF,&H00141009,&H00141009,-1,0,0,0,100,100,0,0,1,2,0,5,64,156,0,1
Style: Note,DejaVu Sans,25,&H00DFE6EB,&H00DFE6EB,&H00141009,&H00141009,0,0,0,0,100,100,0,0,1,1,0,5,64,156,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def line(start: float, end: float, style: str, text: str) -> str:
        return f"Dialogue: 1,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{text}\n"
    header += line(0, duration, "Title", r"{\an5\pos(504,208)\q2}" + r"\N".join(escaped(t) for t in title_lines))
    note_font = ImageFont.truetype(str(REGULAR), 25)
    if note_font.getlength(disclosure) > 880:
        raise RenderBlocked("Disclosure exceeds the measured display width")
    header += line(0, duration, "Note", r"{\an5\pos(504,1750)}" + escaped(disclosure))
    for index, cue in enumerate(cues):
        # Retain the final CTA visually through the natural audio tail. This
        # display extension never changes source SRT or actual speech events.
        visible_end = duration if index == len(cues) - 1 else cue["end"]
        header += line(cue["start"], visible_end, "Sub", r"{\an5\pos(503,1575)\q2}" + r"\N".join(escaped(t) for t in cue["lines"]))
    path.write_text(header, encoding="utf-8")


def create_review_frames(final: Path, cues: list[dict], scenes: list[dict], output: Path) -> list[dict]:
    requests = [{"kind": "caption", "number": c["number"], "time": (c["start"] + c["end"]) / 2} for c in cues]
    requests += [{"kind": "scene", "number": s["scene"], "time": (s["start"] + s["end"]) / 2} for s in scenes]
    requests.append({"kind": "ending", "number": 1, "time": max(0, float(probe(final)["format"]["duration"]) - .15)})
    frame_numbers = sorted({round(request["time"] * FPS) for request in requests})
    folder = output / "review_frames"
    folder.mkdir()
    expression = "+".join(f"eq(n,{number})" for number in frame_numbers)
    run(["ffmpeg", "-v", "error", "-i", str(final), "-vf", f"select='{expression}'", "-vsync", "0",
         "-q:v", "2", str(folder / "%04d.jpg")])
    outputs = sorted(folder.glob("*.jpg"))
    if len(outputs) != len(frame_numbers):
        raise RenderBlocked("Final video review-frame extraction was incomplete")
    mapping = {number: str(path) for number, path in zip(frame_numbers, outputs)}
    for request in requests:
        request["frame_path"] = mapping[round(request["time"] * FPS)]
    return requests


def create_review_sheets(requests: list[dict], output: Path) -> list[str]:
    """Collect exact exported-frame regions for inspection, without passing QA."""
    folder = output / "review_sheets"
    folder.mkdir()
    label_font = ImageFont.truetype(str(REGULAR), 22)
    paths = []
    scene_requests = [item for item in requests if item["kind"] == "scene"]
    scene_sheet = Image.new("RGB", (1080, math.ceil(len(scene_requests) / 3) * 677), (235, 240, 243))
    draw = ImageDraw.Draw(scene_sheet)
    for index, request in enumerate(scene_requests):
        x, y = (index % 3) * 360, (index // 3) * 677
        with Image.open(request["frame_path"]) as frame:
            scene_sheet.paste(frame.resize((360, 640), Image.Resampling.LANCZOS), (x, y + 32))
        draw.text((x + 12, y + 3), f"Scene {request['number']} / {request['time']:.2f}s", font=label_font, fill=(0, 0, 0))
    target = folder / "scene-sheet.jpg"
    scene_sheet.save(target, quality=95, subsampling=0)
    paths.append(str(target))
    captions = [item for item in requests if item["kind"] == "caption"]
    for page, start in enumerate(range(0, len(captions), 18), 1):
        sheet = Image.new("RGB", (1800, 9 * 290), (235, 240, 243))
        draw = ImageDraw.Draw(sheet)
        for index, request in enumerate(captions[start:start + 18]):
            x, y = (index % 2) * 900, (index // 2) * 290
            with Image.open(request["frame_path"]) as frame:
                sheet.paste(frame.crop((53, 1460, 953, 1705)), (x, y + 35))
            draw.text((x + 12, y + 5), f"Cue {request['number']:02d} / {request['time']:.3f}s", font=label_font, fill=(0, 0, 0))
        target = folder / f"caption-sheet-{page:02d}.jpg"
        sheet.save(target, quality=95, subsampling=0)
        paths.append(str(target))
    first = captions[0]["frame_path"]
    (output / "thumbnail.jpg").write_bytes(Path(first).read_bytes())
    return paths


def build(args: argparse.Namespace) -> dict:
    if args.voice != VOICE:
        raise RenderBlocked("Only the approved exact Nestoras voice is accepted")
    audio, srt, script_path = args.audio.resolve(), args.srt.resolve(), args.script.resolve()
    script = script_path.read_text(encoding="utf-8").strip()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    for field in ("job_id", "story_id", "title", "platform"):
        if not isinstance(inventory.get(field), str) or not inventory[field].strip():
            raise RenderBlocked(f"Inventory identity field {field} is missing")
    if inventory["platform"] not in ALLOWED_PLATFORMS or inventory.get("brand_id") != 7076410:
        raise RenderBlocked("Inventory falls outside the authorized brand and four platforms")
    # Apply the same overlay limits before any expensive scene rendering.
    # write_ass keeps its own check for callers that only remux existing scenes.
    wrap_two_lines(args.title or inventory["title"], ImageFont.truetype(str(FONT), 52), 880)
    disclosure = inventory.get("disclosure", "Αρχειακό υλικό · Συνθετική αφήγηση")
    if ImageFont.truetype(str(REGULAR), 25).getlength(disclosure) > 880:
        raise RenderBlocked("Disclosure exceeds the measured display width")
    expected_script = inventory.get("script_sha256")
    narration_hash = hashlib.sha256(script.encode("utf-8")).hexdigest()
    if expected_script is not None and expected_script != narration_hash:
        raise RenderBlocked("Inventory script fingerprint differs from supplied exact narration")
    metadata = probe(audio)
    streams = [stream for stream in metadata["streams"] if stream["codec_type"] == "audio"]
    if len(streams) != 1 or streams[0].get("channels") != 1:
        raise RenderBlocked("One mono narration track is required")
    duration = float(metadata["format"]["duration"])
    maximum = 150 if inventory["platform"] == "youtube" else None
    if duration < 80 or (maximum is not None and duration > maximum):
        limit = f"80–{maximum}s" if maximum is not None else "at least 80s"
        raise RenderBlocked(f"Measured narration duration {duration:.3f}s must be {limit}; never pad or resynthesize automatically")
    cues = read_cues(srt, script, duration)
    scenes = scene_timeline(script, cues, duration)
    sources = read_sources(args.inventory.resolve(), len(scenes))
    report = {"schema_version": 1, "job_id": inventory["job_id"], "story_id": inventory["story_id"],
              "platform": inventory["platform"], "brand_id": 7076410,
              "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "status": "DRY_RUN_INPUTS_VALIDATED", "voice_claim_from_input": args.voice,
              "audio": {"path": str(audio), "sha256": digest(audio), "duration_seconds": duration},
              "duration_limits_seconds": {"minimum": 80, "maximum": maximum},
              "script_sha256": digest(script_path), "input_srt_sha256": digest(srt),
              "source_inventory_sha256": digest(args.inventory), "source_assets": sources,
              "unique_source_count": len({source["sha256"] for source in sources}),
              "source_reuse": [{"scene": source["scene"],
                                "reuses_scene": source["source_reused_from_scene"],
                                "sha256": source["sha256"],
                                "reason": source["source_reuse_reason"]}
                               for source in sources if "source_reused_from_scene" in source],
              "narration_text_sha256": narration_hash,
              "scenes": scenes, "subtitle_font_px": SUB_SIZE, "subtitle_max_lines": 2,
              "subtitle_max_width_px": SUB_WIDTH, "subtitle_cues": cues,
              "final_caption_visual_hold": {"cue_number": cues[-1]["number"],
                                            "actual_cue_end_seconds": cues[-1]["end"],
                                            "visible_until_seconds": duration,
                                            "source_srt_and_audio_unchanged": True},
              "actual_audio_listened": False, "exact_final_visual_review": False,
              "passed_final_review": False, "publishable": False, "publishing_actions": 0,
              "paid_services_called": 0, "background_music": False, "avatar": False}
    if not args.execute:
        return report
    output = args.output.resolve()
    if output.exists():
        raise RenderBlocked("Output directory already exists; preserve previous exports and choose a new revision directory")
    output.mkdir(parents=True)
    frames, segments = output / "scene_frames", output / "segments"
    frames.mkdir(); segments.mkdir()
    report["layouts"] = []
    report["segment_checks"] = []
    for source, scene in zip(sources, scenes):
        image_path = frames / f"{source['scene']:02d}.jpg"
        report["layouts"].append(render_frame(source, image_path))
        segment_path = segments / f"{source['scene']:02d}.mp4"
        run(["ffmpeg", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(image_path),
             "-frames:v", str(scene["frames"]), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "19",
             "-pix_fmt", "yuv420p", "-threads", str(args.threads), str(segment_path)],
            log_path=output / "execution_logs" / f"scene-{source['scene']:02d}.json")
        segment_info = probe(segment_path)
        segment_video = [stream for stream in segment_info["streams"] if stream["codec_type"] == "video"]
        if (len(segment_video) != 1
                or (segment_video[0].get("width"), segment_video[0].get("height")) != (WIDTH, HEIGHT)
                or int(segment_video[0].get("nb_frames", 0)) != scene["frames"]):
            raise RenderBlocked(f"Scene {source['scene']} did not produce its complete expected video frames")
        report["segment_checks"].append({"scene": source["scene"], "path": str(segment_path),
                                         "bytes": segment_path.stat().st_size,
                                         "expected_frames": scene["frames"],
                                         "actual_frames": int(segment_video[0]["nb_frames"]),
                                         "format_probe_passed": True})
    (output / "segments.ffconcat").write_text("ffconcat version 1.0\n" + "".join(f"file 'segments/{i:02d}.mp4'\n" for i in range(1, len(scenes) + 1)), encoding="utf-8")
    write_ass(output / "final.ass", args.title or inventory["title"], cues, duration,
              inventory.get("disclosure", "Αρχειακό υλικό · Συνθετική αφήγηση"))
    final = output / "final.mp4"
    run(["ffmpeg", "-v", "error", "-f", "concat", "-safe", "1", "-i", "segments.ffconcat", "-i", str(audio),
         "-map", "0:v:0", "-map", "1:a:0", "-vf", "ass=final.ass", "-t", f"{duration:.6f}",
         "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-threads", str(args.threads),
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "1",
         "-movflags", "+faststart", str(final)], cwd=output,
        log_path=output / "execution_logs" / "final.json")
    final_info = probe(final)
    video = [stream for stream in final_info["streams"] if stream["codec_type"] == "video"]
    audio_streams = [stream for stream in final_info["streams"] if stream["codec_type"] == "audio"]
    if len(video) != 1 or len(audio_streams) != 1 or (video[0]["width"], video[0]["height"]) != (WIDTH, HEIGHT):
        raise RenderBlocked("Final format validation failed")
    if abs(float(final_info["format"]["duration"]) - duration) > .1:
        raise RenderBlocked("Final duration does not preserve complete narration")
    if any(abs(float(stream.get("duration", 0)) - duration) > .1 for stream in [video[0], audio_streams[0]]):
        raise RenderBlocked("An individual final audio or video stream ends before the complete narration")
    run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"],
        log_path=output / "execution_logs" / "final-decode.json")
    report["review_frames"] = create_review_frames(final, cues, scenes, output)
    report["review_contact_sheets"] = create_review_sheets(report["review_frames"], output)
    report["status"] = "NEEDS_FINAL_REVIEW"
    report["final"] = {"path": str(final), "sha256": digest(final), "bytes": final.stat().st_size,
                       "duration_seconds": float(final_info["format"]["duration"]),
                       "width": WIDTH, "height": HEIGHT, "video_codec": video[0]["codec_name"],
                       "audio_codec": audio_streams[0]["codec_name"], "audio_streams": 1,
                       "technical_decode_passed": True}
    report["sidecar_assets"] = []
    for name in ("caption.txt", "source_attributions.md"):
        source = args.inventory.parent / name
        if source.is_file():
            target = output / name
            target.write_bytes(source.read_bytes())
            report["sidecar_assets"].append({"name": name, "path": str(target.resolve()),
                                               "sha256": digest(target), "copied_exactly_from": str(source.resolve())})
    (output / "render_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("audio", "srt", "script", "inventory", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--title")
    parser.add_argument("--voice", default=VOICE)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        report = build(args)
    except (RenderBlocked, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc), "publishable": False}, ensure_ascii=False))
        return 2
    print(json.dumps({key: report.get(key) for key in ("status", "story_id", "audio", "final", "passed_final_review", "publishable")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
