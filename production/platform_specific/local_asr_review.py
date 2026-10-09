import os
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

import argparse
import difflib
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import time
import unicodedata
import numpy as np
from faster_whisper import WhisperModel

p = argparse.ArgumentParser()
p.add_argument('--audio', required=True)
p.add_argument('--script', required=True)
p.add_argument('--model-dir', required=True)
p.add_argument('--out-dir', required=True)
a = p.parse_args()
out = Path(a.out_dir)
out.mkdir(parents=True, exist_ok=True)
started = time.time()
audio_path = Path(a.audio)
ref_path = Path(a.script)
model = WhisperModel(a.model_dir, device='cpu', compute_type='int8', cpu_threads=4, num_workers=1, local_files_only=True)
decoded = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(audio_path), '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', 'pipe:1'], capture_output=True, check=True)
waveform = np.frombuffer(decoded.stdout, dtype=np.float32)
segments, info = model.transcribe(waveform, language='el', task='transcribe', beam_size=5, best_of=5, temperature=0.0, vad_filter=False, word_timestamps=True, condition_on_previous_text=True, initial_prompt=None)
items = []
for seg in segments:
    item = seg._asdict()
    item['words'] = [w._asdict() for w in (seg.words or [])]
    items.append(item)
    print(f'{seg.start:.2f}-{seg.end:.2f}: {seg.text}', flush=True)
transcript = ''.join(s['text'] for s in items).strip()
(out / 'transcript.txt').write_text(transcript + '\n', encoding='utf-8')

def tokens(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s.casefold()) if not unicodedata.combining(c)).replace('ς', 'σ')
    return re.findall(r'\w+', s)

ref = tokens(ref_path.read_text(encoding='utf-8'))
hyp = tokens(transcript)
alignment = []
for tag, i, j, k, l in difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False).get_opcodes():
    if tag != 'equal':
        alignment.append({'type': tag, 'reference_start': i, 'reference': ref[i:j], 'asr_start': k, 'asr': hyp[k:l]})
previous = list(range(len(hyp) + 1))
for i, word in enumerate(ref, 1):
    current = [i]
    for j, heard in enumerate(hyp, 1):
        current.append(min(current[-1] + 1, previous[j] + 1, previous[j-1] + (word != heard)))
    previous = current
errors = previous[-1]
result = {
    'method': 'Fully local independent ASR. No transcript prompt supplied. No audio sent to any remote service. Not direct human/audio perception and not automatic final approval.',
    'audio_path': str(audio_path),
    'audio_sha256': hashlib.sha256(audio_path.read_bytes()).hexdigest(),
    'script_path': str(ref_path),
    'script_sha256': hashlib.sha256(ref_path.read_bytes()).hexdigest(),
    'model_repo': 'Systran/faster-whisper-small',
    'model_revision': '536b0662742c02347bc0e980a01041f333bce120',
    'faster_whisper_version': importlib.metadata.version('faster-whisper'),
    'ctranslate2_version': importlib.metadata.version('ctranslate2'),
    'language': info.language,
    'duration_seconds': info.duration,
    'decoder': 'FFmpeg full exact-file audio decode, mono 16000 Hz float32; no source trimming',
    'elapsed_seconds': time.time() - started,
    'normalization': 'casefold, remove combining accents, normalize final sigma, word tokens',
    'reference_words': len(ref),
    'asr_words': len(hyp),
    'normalized_word_edit_distance': errors,
    'normalized_word_error_rate': errors / len(ref) if ref else None,
    'discrepancies_requiring_review': alignment,
    'segments': items,
}
(out / 'asr_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: result[k] for k in ['duration_seconds','elapsed_seconds','reference_words','asr_words','normalized_word_edit_distance','normalized_word_error_rate','discrepancies_requiring_review']}, ensure_ascii=False), flush=True)
