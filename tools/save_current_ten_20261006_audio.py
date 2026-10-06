#!/usr/bin/env python3
"""Persist only this batch through Git Data API, with a nonforce ref update."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

REPOSITORY = 'steliosvil5eteth-byte/Stelios-Vilanos'
JOB_IDS = ['current-ten-20261006-prespes', 'current-ten-20261006-singing-dunes',
           'current-ten-20261006-ikea-effect', 'current-ten-20261006-tsukumogami']

def api(method, endpoint, payload=None):
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    request = urllib.request.Request('https://api.github.com/repos/' + REPOSITORY + '/' + endpoint,
        data=body, method=method, headers={
            'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
            'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json', 'User-Agent': 'Stelios-owned-narration-repair'})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'GitHub {method} {endpoint} returned HTTP {error.code}; no blind retry') from None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--asr', type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise RuntimeError('Unexpected repository for this production batch')
    files = {}
    for job_id in JOB_IDS:
        folder = args.audio / job_id
        meta = json.loads((folder / 'speech-meta.json').read_text(encoding='utf-8'))
        wav = folder / 'nestoras.wav'
        if meta['id'] != job_id or meta.get('publish_ready') is not False:
            raise RuntimeError('Wrong job or premature release claim')
        if hashlib.sha256(wav.read_bytes()).hexdigest() != meta['audio_sha256']:
            raise RuntimeError('Audio changed before persistence')
        for file in sorted(folder.iterdir()):
            if file.is_file(): files['jobs/' + job_id + '/' + file.name] = file
        review = args.asr / job_id
        if review.exists():
            for file in sorted(review.iterdir()):
                if file.is_file(): files['jobs/' + job_id + '/' + file.name] = file
    for folder, filename, target in [
        (args.audio, 'audio-batch-summary.json', 'reports/current-ten-20261006-narrated-audio.json'),
        (args.asr, 'asr-batch-summary.json', 'reports/current-ten-20261006-narrated-asr.json'),
    ]:
        file = folder / filename
        if file.is_file(): files[target] = file
    if not files: raise RuntimeError('No completed audio files to persist')
    base = api('GET', 'git/ref/heads/media-output')['object']['sha']
    base_tree = api('GET', 'git/commits/' + base)['tree']['sha']
    entries = []
    for path, file in files.items():
        data = file.read_bytes()
        if len(data) > 25 * 1024 * 1024: raise RuntimeError('Unexpected oversized audio output')
        blob = api('POST', 'git/blobs', {'content': base64.b64encode(data).decode('ascii'), 'encoding': 'base64'})
        entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
    tree = api('POST', 'git/trees', {'base_tree': base_tree, 'tree': entries})
    commit = api('POST', 'git/commits', {
        'message': 'Save 6 October Nestoras audio and independent recognition evidence; release pending',
        'tree': tree['sha'], 'parents': [base],
    })
    api('PATCH', 'git/refs/heads/media-output', {'sha': commit['sha'], 'force': False})
    actual = api('GET', 'git/ref/heads/media-output')['object']['sha']
    if actual != commit['sha']: raise RuntimeError('media-output head changed during readback; reconcile before publishing')
    print(json.dumps({'media_output_commit': actual, 'files_saved': len(entries), 'publish_ready': False}))

if __name__ == '__main__': main()
