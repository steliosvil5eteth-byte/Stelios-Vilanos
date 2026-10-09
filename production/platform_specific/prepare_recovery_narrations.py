#!/usr/bin/env python3
"""Prepare the explicitly requested existing public scripts; never publish.

Each request independently verifies anonymous access to the pinned public
manifest before any text transmission. Two ordinary concurrent requests,
no account key, no paid endpoint, no retry, and no hearing attestations.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse, datetime, hashlib, json, os, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_REF = '26f9eac6dd0bc7a807ef0667697e2b5ce5fc01a4'
PUBLIC_URL = 'https://raw.githubusercontent.com/steliosvil5eteth-byte/Stelios-Vilanos/' + PUBLIC_REF + '/production_20261009_platform_specific/manifest.json'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dependencies', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    manifest = ROOT / 'production_20261009_platform_specific/manifest.json'
    jobs = json.loads(manifest.read_text())['jobs']
    held = {'2026-10-09-instagram-01', '2026-10-09-tiktok-02'}
    jobs = [j for j in jobs if j['id'] not in held]
    base = ROOT / 'production_20261009_platform_specific/recovery'
    summary = base / 'batch_narration_summary.json'
    if summary.exists():
        raise SystemExit('Batch already recorded; inspect existing results, never blindly retry')
    if not args.execute:
        print(json.dumps({'jobs': len(jobs), 'held': sorted(held), 'public_ref': PUBLIC_REF, 'network_requests': 0}))
        return
    def process(job):
        output = base / (job['id'].replace('2026-10-09-', '') + '-public-narration')
        if (output / 'speech_attempt.json').exists():
            return {'id': job['id'], 'status': 'EXISTING_ATTEMPT_NOT_RETRIED'}
        env = os.environ.copy()
        env['PYTHONPATH'] = str(args.dependencies)
        cmd = [sys.executable, str(ROOT / 'production/platform_specific/recovery_speech.py'), '--manifest', str(manifest), '--job-id', job['id'], '--output', str(output), '--public-manifest-url', PUBLIC_URL]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
        record = {'id': job['id'], 'exit_code': result.returncode, 'output_directory': str(output), 'script_sha256': hashlib.sha256(job['script'].encode()).hexdigest(), 'actual_audio_listened': False}
        if (output / 'speech_attempt.json').exists():
            state = json.loads((output / 'speech_attempt.json').read_text())
            record.update({k: state.get(k) for k in ['status', 'audio_bytes', 'audio_sha256', 'word_boundaries']})
        else:
            record['status'] = 'FAILED_BEFORE_SYNTHESIS'
            record['diagnostic'] = result.stderr[-1000:]
        print(json.dumps(record, ensure_ascii=False), flush=True)
        return record
    results = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(process, job) for job in jobs]
        for future in as_completed(futures):
            results.append(future.result())
            summary.write_text(json.dumps({'updated_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'public_ref': PUBLIC_REF, 'expected': len(jobs), 'completed': len(results), 'records': results, 'paid_credit_budget': 0, 'actual_audio_listened': False, 'publishable': False}, ensure_ascii=False, indent=2) + '\n')

if __name__ == '__main__':
    main()
