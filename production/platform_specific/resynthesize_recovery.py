#!/usr/bin/env python3
"""Replace only explicitly identified faulty narrations; preserve every prior take.

The public source is independently verified before each ordinary Microsoft Edge
request. No account credentials, paid fallback, automatic retry, publication,
or claim of human/audio-perception review is supported here.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dependencies', type=Path, required=True)
    parser.add_argument('--public-ref', required=True)
    parser.add_argument('--job-ids', nargs='+', required=True)
    parser.add_argument('--output-suffix', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    manifest = root / 'production_20261009_platform_specific/manifest.json'
    jobs = {j['id']: j for j in json.loads(manifest.read_text())['jobs']}
    if any(job_id not in jobs for job_id in args.job_ids):
        raise SystemExit('Unknown job')
    if len(set(args.job_ids)) != len(args.job_ids):
        raise SystemExit('Duplicate job request')
    base = root / 'production_20261009_platform_specific/recovery'
    public_url = 'https://raw.githubusercontent.com/steliosvil5eteth-byte/Stelios-Vilanos/' + args.public_ref + '/production_20261009_platform_specific/manifest.json'
    outputs = {j: base / (j.replace('2026-10-09-', '') + '-' + args.output_suffix) for j in args.job_ids}
    if any((out / 'speech_attempt.json').exists() for out in outputs.values()):
        raise SystemExit('At least one requested output already records an attempt; inspect instead of retrying')
    if not args.execute:
        print(json.dumps({'jobs': args.job_ids, 'public_ref': args.public_ref, 'network_requests': 0}))
        return
    selection_hash = hashlib.sha256('\n'.join(args.job_ids).encode()).hexdigest()[:12]
    summary = base / (args.output_suffix + '-' + selection_hash + '-summary.json')
    def process(job_id):
        env = os.environ.copy()
        env['PYTHONPATH'] = str(args.dependencies)
        result = subprocess.run([sys.executable, str(root / 'production/platform_specific/recovery_speech.py'), '--manifest', str(manifest), '--job-id', job_id, '--output', str(outputs[job_id]), '--public-manifest-url', public_url], env=env, capture_output=True, text=True, timeout=150)
        record = {'id': job_id, 'exit_code': result.returncode, 'output_directory': str(outputs[job_id]), 'actual_audio_listened': False}
        attempt_path = outputs[job_id] / 'speech_attempt.json'
        if attempt_path.exists():
            attempt = json.loads(attempt_path.read_text())
            record.update({k: attempt.get(k) for k in ['status', 'audio_bytes', 'audio_sha256', 'word_boundaries', 'script_sha256_exact_bytes']})
        else:
            record.update(status='FAILED_BEFORE_SYNTHESIS', diagnostic=result.stderr[-800:])
        print(json.dumps(record, ensure_ascii=False), flush=True)
        return record
    records = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(process, job_id) for job_id in args.job_ids]
        for future in as_completed(futures):
            records.append(future.result())
            summary.write_text(json.dumps({'updated_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'public_ref': args.public_ref, 'requested': len(args.job_ids), 'completed': len(records), 'records': records, 'actual_audio_listened': False, 'publishable': False}, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
