#!/usr/bin/env python3
"""Independent Greek ASR evidence. This tool never approves publication."""
from __future__ import annotations
import argparse
import difflib
import hashlib
import json
import os
import re
import threading
import unicodedata
from pathlib import Path
import azure.cognitiveservices.speech as speechsdk


def tokens(text):
    clean = ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if not unicodedata.combining(c))
    return re.findall(r'[^\W_]+', clean.replace('ς', 'σ'), re.UNICODE)


def recognize(wav: Path, duration: float):
    config = speechsdk.SpeechConfig(subscription=os.environ['AZURE_SPEECH_KEY'], region=os.environ['AZURE_SPEECH_REGION'])
    config.speech_recognition_language = 'el-GR'
    config.output_format = speechsdk.OutputFormat.Detailed
    config.request_word_level_timestamps()
    recognizer = speechsdk.SpeechRecognizer(speech_config=config, audio_config=speechsdk.audio.AudioConfig(filename=str(wav)))
    segments, errors, no_matches = [], [], []
    stopped = threading.Event()

    def recognized(event):
        if event.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            segments.append({'text': event.result.text, 'offset_ticks': event.result.offset,
                             'duration_ticks': event.result.duration, 'detailed': json.loads(event.result.json)})
        elif event.result.reason == speechsdk.ResultReason.NoMatch:
            no_matches.append({'offset_ticks': event.result.offset, 'duration_ticks': event.result.duration})

    def canceled(event):
        details = event.result.cancellation_details
        if details.reason == speechsdk.CancellationReason.Error:
            errors.append({'reason': str(details.reason), 'code': str(details.error_code), 'details': details.error_details})
        stopped.set()

    recognizer.recognized.connect(recognized)
    recognizer.canceled.connect(canceled)
    recognizer.session_stopped.connect(lambda event: stopped.set())
    recognizer.start_continuous_recognition_async().get()
    completed = stopped.wait(timeout=duration * 2 + 90)
    recognizer.stop_continuous_recognition_async().get()
    if not completed:
        errors.append({'reason': 'Recognition timeout'})
    segments.sort(key=lambda s: s['offset_ticks'])
    return segments, errors, no_matches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    if len(manifest['jobs']) != 4:
        raise RuntimeError('This review batch requires exactly four narrated jobs')
    reports = []
    errors_found = False
    for job in manifest['jobs']:
        root = args.source / job['id']
        wav = root / 'nestoras.wav'
        meta = json.loads((root / 'speech-meta.json').read_text(encoding='utf-8'))
        digest = hashlib.sha256(wav.read_bytes()).hexdigest()
        if digest != meta['audio_sha256'] or meta['script_sha256'] != job['script_sha256']:
            raise RuntimeError('Saved narration is not bound to the approved script and audio hash')
        segments, errors, no_matches = recognize(wav, float(meta['duration_seconds']))
        transcript = ' '.join(s['text'] for s in segments)
        expected, actual = tokens(job['script']), tokens(transcript)
        differences = []
        for kind, i1, i2, j1, j2 in difflib.SequenceMatcher(a=expected, b=actual, autojunk=False).get_opcodes():
            if kind != 'equal':
                differences.append({'kind': kind, 'expected_word_range': [i1, i2], 'recognized_word_range': [j1, j2],
                                    'expected': ' '.join(expected[i1:i2]), 'recognized': ' '.join(actual[j1:j2])})
        report = {
            'id': job['id'], 'provider': 'Azure Speech independent speech recognition', 'language': 'el-GR',
            'recognizer_received_script_hints': False, 'audio_sha256': digest, 'script_sha256': job['script_sha256'],
            'audio_duration_seconds': meta['duration_seconds'], 'recognized_text': transcript,
            'expected_word_count': len(expected), 'recognized_word_count': len(actual),
            'normalized_exact_match': expected == actual, 'differences': differences,
            'segments': segments, 'errors': errors, 'no_match_regions': no_matches,
            'asr_completed': bool(segments) and not errors, 'direct_listening_claimed': False,
            'publish_ready': False, 'release_gate': 'PENDING_REVIEW_OF_ASR_DIFFERENCES_AND_EXACT_FINAL_MEDIA',
        }
        out = args.output / job['id']; out.mkdir(parents=True, exist_ok=True)
        (out / 'speech-recognition.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        (out / 'recognized-text.txt').write_text(transcript + '\n', encoding='utf-8')
        reports.append({k: report[k] for k in ['id', 'audio_sha256', 'asr_completed', 'normalized_exact_match', 'differences', 'errors', 'publish_ready']})
        errors_found |= not report['asr_completed']
        print(json.dumps(reports[-1], ensure_ascii=False))
    (args.output / 'asr-batch-summary.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
    if errors_found:
        raise SystemExit('One or more recognitions did not complete; all review remains pending')


if __name__ == '__main__':
    main()
