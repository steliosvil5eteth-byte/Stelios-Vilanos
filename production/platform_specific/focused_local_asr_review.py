#!/usr/bin/env python3
"""Transcribe explicit windows from the exact local final audio without a prompt."""
import os
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from faster_whisper import WhisperModel
from recovery_resource_limits import resource_slot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--window', action='append', required=True, help='Exact start:end seconds; repeat for independent windows')
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    windows = [tuple(float(v) for v in text.split(':')) for text in args.window]
    if any(len(w) != 2 or not 0 <= w[0] < w[1] for w in windows):
        raise ValueError('Each explicit window must satisfy 0 <= start < end')
    if args.out_dir.exists():
        raise ValueError('Preserve earlier evidence; use a fresh output directory')
    started = time.monotonic()
    with resource_slot('asr') as asr_slot:
        with resource_slot('ffmpeg') as decode_slot:
            decoded = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(args.audio), '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', 'pipe:1'], stdin=subprocess.DEVNULL, capture_output=True, check=True)
        samples = np.frombuffer(decoded.stdout, np.float32)
        duration = len(samples) / 16000
        if any(end > duration for start, end in windows):
            raise ValueError('Window extends beyond the actually decoded audio')
        model = WhisperModel(str(args.model_dir), device='cpu', compute_type='int8', cpu_threads=4, num_workers=1, local_files_only=True)
        results = []
        for start, end in windows:
            segments, info = model.transcribe(samples[int(start*16000):int(end*16000)], language='el', beam_size=5, best_of=5, temperature=0.0, vad_filter=False, condition_on_previous_text=False, initial_prompt=None, word_timestamps=True)
            items = []
            for segment in segments:
                item = segment._asdict()
                item['start'] += start
                item['end'] += start
                item['words'] = [{**word._asdict(), 'start': word.start+start, 'end': word.end+start} for word in (segment.words or [])]
                items.append(item)
            result = {'requested_start_seconds': start, 'requested_end_seconds': end, 'transcript': ''.join(item['text'] for item in items).strip(), 'segments': items}
            results.append(result)
            print(json.dumps({k: result[k] for k in ['requested_start_seconds','requested_end_seconds','transcript']}, ensure_ascii=False), flush=True)
        record = {'method': 'Fully offline independent ASR of explicit windows from the exact supplied final file. No transcript prompt, no previous-text conditioning, no remote audio transfer. This is not actual hearing or final approval.', 'actual_audio_listened': False, 'audio_path': str(args.audio.resolve()), 'audio_sha256': hashlib.sha256(args.audio.read_bytes()).hexdigest(), 'full_decoded_duration_seconds': duration, 'model_repo': 'Systran/faster-whisper-small', 'model_revision': '536b0662742c02347bc0e980a01041f333bce120', 'language': 'el', 'initial_prompt': None, 'condition_on_previous_text': False, 'vad_filter': False, 'resource_slot': asr_slot, 'decoder_resource_slot': decode_slot, 'elapsed_seconds': time.monotonic()-started, 'windows': results}
        args.out_dir.mkdir(parents=True)
        (args.out_dir / 'focused_asr_result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')

if __name__ == '__main__':
    main()
