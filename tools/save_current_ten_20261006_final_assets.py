#!/usr/bin/env python3
"""Validate exactly 45 reviewed Metricool media files, then save bounded Git blobs.

No publishing, rendering, synthesis, branch checkout, force update, or blind retry.
Validation downloads run without GitHub credentials. Persistence consumes their
hash-bound proof and updates media-output once through GitHub's Git Data API.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import math
import os
import re
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

REPOSITORY = 'steliosvil5eteth-byte/Stelios-Vilanos'
BRANCH = 'media-output'
DATE = '2026-10-06'
BRAND = '7076410'
MANIFEST_PATH = 'media_jobs/current_ten_20261006_final_delivery_assets.json'
JOURNAL_PATH = 'media_jobs/current_ten_20261006_delivery_journal.json'
REPORT_PATH = 'reports/current-ten-20261006-final-delivery-assets.json'
SERIES = {'relationships', 'survival', 'dog_bartender', 'zodiac',
          'love_soul_relationship', 'myth_or_truth', 'greece_two_day_trip',
          'strange_real_phenomenon', 'documented_experiments', 'international_legend'}
NARRATED = {'greece_two_day_trip', 'strange_real_phenomenon',
            'documented_experiments', 'international_legend'}
NETWORKS = {'facebook', 'instagram', 'tiktok', 'youtube'}
DELIVERY_STATUSES = {'PENDING', 'PUBLISHED', 'PUBLISHING', 'SCHEDULED', 'AWAITING_CONFIRMATION'}
FILE_LIMIT = 30 * 1024 * 1024
TOTAL_LIMIT = 200 * 1024 * 1024
SHA256 = re.compile(r'[0-9a-f]{64}\Z')
GIT_SHA = re.compile(r'[0-9a-f]{40}\Z')
JOB = re.compile(r'current-ten-20261006-[a-z0-9]+(?:-[a-z0-9]+)*\Z')
FILENAME = re.compile(r'[a-z0-9][a-z0-9._-]*\.(?:jpg|mp4)\Z')


def fail(message):
    raise RuntimeError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def now():
    return datetime.now(timezone.utc).isoformat()


def metricool_url(url):
    if not isinstance(url, str) or any(ord(c) < 32 for c in url):
        fail('Malformed media URL')
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'static.metricool.com'
            or parsed.port not in (None, 443) or parsed.username or parsed.password
            or parsed.fragment or not parsed.path.startswith('/')):
        fail('Media URL or redirect leaves the approved static.metricool.com origin')
    return url


class MetricoolRedirects(urllib.request.HTTPRedirectHandler):
    max_redirections = 3
    max_repeats = 1

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        metricool_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fail('Unexpected redirect from canonical GitHub API; credentials were not forwarded')


def validate_contract(manifest_path):
    manifest_path = Path(manifest_path)
    manifest = read_json(manifest_path)
    if (str(manifest.get('brandId')) != BRAND or manifest.get('date') != DATE
            or manifest.get('expected_asset_count') != 45
            or manifest.get('expected_logical_posts') != 10
            or manifest.get('expected_provider_destinations') != 40
            or manifest.get('release_journal_path') != JOURNAL_PATH):
        fail('Manifest is outside the approved 6 October / 45 asset / 10 post scope')
    # Resolve this fixed repository-relative path, never a caller-controlled file.
    repo_root = manifest_path.resolve().parent.parent
    if manifest_path.resolve() != repo_root / MANIFEST_PATH:
        fail('Unexpected manifest location')
    journal_path = repo_root / JOURNAL_PATH
    journal = read_json(journal_path)
    if str(journal.get('brandId')) != BRAND or journal.get('date') != DATE:
        fail('Delivery journal belongs to another brand or date')
    posts = journal.get('metricool_posts', [])
    mapping = journal.get('mapping', {})
    if not isinstance(posts, list) or not isinstance(mapping, dict):
        fail('Malformed delivery journal')
    by_post, coverage = {}, defaultdict(list)
    for post in posts:
        post_id = str(post.get('id', ''))
        series = mapping.get(post_id)
        if not post_id.isdecimal() or post_id in by_post or series not in SERIES:
            fail('Duplicate, unmapped, or unexpected delivery journal post')
        if post.get('draft') is True:
            fail('Draft post is not a confirmed delivery')
        providers = post.get('providers', [])
        if not providers or not isinstance(providers, list):
            fail('Post lacks actual provider destinations')
        for provider in providers:
            network = provider.get('network')
            if network not in NETWORKS or provider.get('status') not in DELIVERY_STATUSES:
                fail('Unexpected network or failed/unknown delivery status')
            coverage[series].append(network)
        by_post[post_id] = post
    if set(coverage) != SERIES or any(len(v) != 4 or set(v) != NETWORKS for v in coverage.values()):
        fail('Journal must contain exactly four unique destinations for each of ten series')
    assets = manifest.get('assets')
    if not isinstance(assets, list) or len(assets) != 45:
        fail('Expected exactly 45 assets')
    paths, urls, jobs, media_by_post = set(), set(), {}, defaultdict(list)
    kinds, series_kinds = Counter(), defaultdict(Counter)
    for asset in assets:
        job, series, path = asset.get('job_id'), asset.get('series'), asset.get('path')
        if not isinstance(job, str) or not JOB.fullmatch(job) or series not in SERIES:
            fail('Unexpected job ID or series')
        parts = PurePosixPath(path).parts if isinstance(path, str) else ()
        if (len(parts) != 4 or parts[:3] != ('jobs', job, 'final')
                or not FILENAME.fullmatch(parts[-1]) or '..' in parts[-1]
                or str(PurePosixPath(path)) != path):
            fail('Asset path is outside its bounded final job directory')
        suffix = Path(path).suffix
        if suffix == '.jpg' and not re.fullmatch(r'card-[0-9]{2}\.jpg', parts[-1]):
            fail('JPEG asset must use a numbered final card path')
        url = metricool_url(asset.get('url'))
        if path in paths or url in urls:
            fail('Duplicate asset path or URL')
        paths.add(path); urls.add(url)
        allowed = asset.get('allowed_sha256')
        if (not isinstance(allowed, list) or not 1 <= len(allowed) <= 4
                or any(not isinstance(h, str) or not SHA256.fullmatch(h) for h in allowed)
                or len(set(allowed)) != len(allowed)):
            fail('Every asset requires explicit unique reviewed SHA256 values')
        width, height = asset.get('width'), asset.get('height')
        if width != 1080 or height not in (1080, 1920):
            fail('Unexpected reviewed media dimensions')
        if suffix == '.mp4':
            low, high = asset.get('min_duration_seconds'), asset.get('max_duration_seconds')
            if (not isinstance(low, (int, float)) or not isinstance(high, (int, float))
                    or isinstance(low, bool) or isinstance(high, bool)
                    or not math.isfinite(low) or not math.isfinite(high)
                    or not 0 < low <= high <= 300 or high - low > .201 or height != 1920):
                fail('Video requires a narrow finite reviewed duration and 1080x1920 dimensions')
            if series in NARRATED and high < 80:
                fail('Narrated delivery cannot be shorter than eighty seconds')
        elif series in NARRATED:
            fail('Narrated series has no final carousel images in this delivery')
        if job in jobs and jobs[job] != series:
            fail('One job cannot span multiple series')
        jobs[job] = series
        kinds[suffix] += 1; series_kinds[series][suffix] += 1
        post_id = str(asset.get('metricool_post_id', ''))
        post = by_post.get(post_id)
        if not post or mapping[post_id] != series or url not in post.get('media', []):
            fail('Asset lacks the exact confirmed Metricool post/media association')
        media_by_post[post_id].append(url)
    if (kinds != {'.jpg': 35, '.mp4': 10} or len(jobs) != 10 or set(jobs.values()) != SERIES
            or any(series_kinds[s]['.mp4'] != 1 for s in SERIES)
            or sum(series_kinds[s]['.jpg'] > 0 for s in SERIES) != 6):
        fail('Expected 35 JPEGs and one MP4 per each of ten distinct logical posts')
    for post_id, post in by_post.items():
        if Counter(media_by_post[post_id]) != Counter(post.get('media', [])):
            fail('Manifest must include each delivery journal media URL exactly once')
    return manifest, journal, sha256(manifest_path.read_bytes()), sha256(journal_path.read_bytes())


def probe(path, asset):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                             '-of', 'json', str(path)], capture_output=True, text=True, timeout=30)
    if result.returncode:
        fail('Downloaded media could not be decoded by ffprobe: ' + asset['path'])
    metadata = json.loads(result.stdout)
    streams = metadata.get('streams', [])
    video = [s for s in streams if s.get('codec_type') == 'video']
    audio = [s for s in streams if s.get('codec_type') == 'audio']
    if len(video) != 1 or (video[0].get('width'), video[0].get('height')) != (asset['width'], asset['height']):
        fail('Media stream count or reviewed dimensions changed: ' + asset['path'])
    summary = {'width': video[0]['width'], 'height': video[0]['height'],
               'video_codec': video[0]['codec_name'], 'audio_stream_count': len(audio)}
    if asset['path'].endswith('.jpg'):
        if video[0]['codec_name'] != 'mjpeg' or audio or len(streams) != 1:
            fail('Expected an actual single JPEG image')
    else:
        if (video[0]['codec_name'] != 'h264' or len(audio) != 1
                or audio[0].get('codec_name') != 'aac' or len(streams) != 2):
            fail('Expected exactly one H264 video stream and one AAC audio stream')
        duration = float(metadata['format']['duration'])
        if (not math.isfinite(duration) or not asset['min_duration_seconds'] <= duration <= asset['max_duration_seconds']
                or (asset['series'] in NARRATED and duration < 80)):
            fail('Actual video duration differs from reviewed media')
        summary.update(duration_seconds=duration, audio_codec=audio[0]['codec_name'])
    return summary


class DownloadBudget:
    def __init__(self):
        self.lock = threading.Lock()
        self.used = 0

    def add(self, amount):
        with self.lock:
            if self.used + amount >= TOTAL_LIMIT:
                fail('The complete batch must remain below 200 MiB')
            self.used += amount


def download_one(index, asset, work, budget):
    destination = work / 'files' / (f'{index:02d}' + Path(asset['path']).suffix)
    opener = urllib.request.build_opener(MetricoolRedirects())
    request = urllib.request.Request(asset['url'], headers={'User-Agent': 'Stelios-reviewed-media-archive'})
    digest, count = hashlib.sha256(), 0
    try:
        with opener.open(request, timeout=60) as response, destination.open('wb') as file:
            metricool_url(response.geturl())
            declared = response.headers.get('Content-Length')
            if declared and int(declared) >= FILE_LIMIT:
                fail('Media response exceeds the 30 MiB per-file bound')
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if count >= FILE_LIMIT:
                    fail('Media exceeds the 30 MiB per-file bound')
                budget.add(len(chunk)); digest.update(chunk); file.write(chunk)
            final_url = response.geturl()
    except urllib.error.HTTPError as error:
        fail(f'Media asset {index} returned HTTP {error.code}; no blind retry')
    if count == 0 or digest.hexdigest() not in asset['allowed_sha256']:
        fail('Actual downloaded bytes do not match any reviewed hash: ' + asset['path'])
    media = probe(destination, asset)
    data = destination.read_bytes()
    return {'index': index, 'job_id': asset['job_id'], 'series': asset['series'],
            'path': asset['path'], 'url': asset['url'], 'resolved_url': final_url,
            'metricool_post_id': asset['metricool_post_id'], 'local_file': str(destination.resolve()),
            'sha256': digest.hexdigest(), 'bytes': count, 'git_blob_sha1': git_blob_sha(data),
            'media': media, 'reviewed_hash_match': True}


def validate(manifest_path, work):
    manifest, journal, manifest_hash, journal_hash = validate_contract(manifest_path)
    (work / 'files').mkdir(parents=True, exist_ok=True)
    budget = DownloadBudget()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(download_one, i, a, work, budget) for i, a in enumerate(manifest['assets'], 1)]
        records = [future.result() for future in futures]
    report = {'status': 'ALL_45_ACTUAL_MEDIA_BYTES_MATCH_REVIEWED_HASHES', 'validated_at_utc': now(),
              'brandId': 7076410, 'date': DATE, 'asset_count': len(records), 'logical_posts': 10,
              'provider_destinations': 40, 'manifest_sha256': manifest_hash, 'journal_sha256': journal_hash,
              'total_bytes': sum(r['bytes'] for r in records), 'assets': records,
              'publication_status_note': 'This archives existing Metricool delivery records. Pending, scheduled, publishing, or awaiting-confirmation destinations are not claimed as already published.',
              'publish_action_performed': False, 'publish_ready_inferred': False}
    write_json(work / 'validated_assets.json', report)
    print(json.dumps({'validation': report['status'], 'assets': 45, 'total_bytes': report['total_bytes']}))


def api(method, endpoint, payload=None):
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    request = urllib.request.Request('https://api.github.com/repos/' + REPOSITORY + '/' + endpoint,
        data=body, method=method, headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
        'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json', 'User-Agent': 'Stelios-bounded-final-media-archive'})
    try:
        with urllib.request.build_opener(NoRedirects()).open(request, timeout=90) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        fail(f'GitHub {method} {endpoint} returned HTTP {error.code}; no blind retry')


def checked_git_sha(value):
    if not isinstance(value, str) or not GIT_SHA.fullmatch(value):
        fail('Unexpected Git object identifier')
    return value


def tree_entry(root_sha, path, cache):
    current = checked_git_sha(root_sha)
    parts = PurePosixPath(path).parts
    for i, part in enumerate(parts):
        if current not in cache:
            data = api('GET', 'git/trees/' + current)
            if data.get('truncated'):
                fail('Single-level Git tree readback was truncated')
            cache[current] = data['tree']
        entry = next((x for x in cache[current] if x['path'] == part), None)
        if entry is None:
            return None
        if i == len(parts) - 1:
            return entry
        if entry.get('type') != 'tree':
            fail('Existing media path traverses a non-directory Git object')
        current = checked_git_sha(entry['sha'])
    fail('Empty tree path')


def persist(manifest_path, work):
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY or not os.environ.get('GITHUB_TOKEN'):
        fail('Persistence requires this repository and its scoped Actions token')
    manifest, journal, manifest_hash, journal_hash = validate_contract(manifest_path)
    report = read_json(work / 'validated_assets.json')
    records = report.get('assets', [])
    if (report.get('manifest_sha256') != manifest_hash or report.get('journal_sha256') != journal_hash
            or report.get('asset_count') != 45 or len(records) != 45):
        fail('Validation proof is stale or belongs to different inputs')
    files = {}
    for i, (asset, record) in enumerate(zip(manifest['assets'], records), 1):
        expected = (work / 'files' / (f'{i:02d}' + Path(asset['path']).suffix)).resolve()
        if record.get('path') != asset['path'] or record.get('local_file') != str(expected):
            fail('Validation proof changed media association')
        data = expected.read_bytes()
        actual_hash = sha256(data)
        if (not 0 < len(data) < FILE_LIMIT or actual_hash not in asset['allowed_sha256']
                or actual_hash != record.get('sha256') or len(data) != record.get('bytes')
                or git_blob_sha(data) != record.get('git_blob_sha1')):
            fail('Validated media changed before persistence')
        files[asset['path']] = (expected, record)
    if sum(r['bytes'] for _, r in files.values()) >= TOTAL_LIMIT:
        fail('Persistence batch exceeds the total byte bound')
    base = checked_git_sha(api('GET', 'git/ref/heads/' + BRANCH)['object']['sha'])
    base_tree = checked_git_sha(api('GET', 'git/commits/' + base)['tree']['sha'])
    cache = {}
    existing = {path: tree_entry(base_tree, path, cache) for path in files}
    complete = all(e and e.get('type') == 'blob' and e.get('mode') == '100644' and e.get('sha') == files[p][1]['git_blob_sha1']
                   and e.get('size') == files[p][1]['bytes'] for p, e in existing.items())
    outcome = {'status': 'VALIDATED_READY_TO_PERSIST', 'base_commit': base, 'validated_assets': 45,
               'manifest_sha256': manifest_hash, 'journal_sha256': journal_hash,
               'branch': BRANCH, 'publish_action_performed': False}
    write_json(work / 'persistence-result.json', outcome)
    entries = []
    for path, (file, record) in files.items():
        expected_sha = record['git_blob_sha1']
        old = existing[path]
        if not old or old.get('sha') != expected_sha or old.get('type') != 'blob':
            data = file.read_bytes()
            blob = api('POST', 'git/blobs', {'content': base64.b64encode(data).decode('ascii'), 'encoding': 'base64'})
            if checked_git_sha(blob.get('sha')) != expected_sha:
                fail('GitHub blob hash differs from exact submitted media bytes')
        entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': expected_sha})
    if complete:
        commit_sha, tree_sha = base, base_tree
        outcome['status'] = 'ALREADY_PERSISTED_IDENTICAL_MEDIA'
    else:
        # The permanent evidence file binds SHA256 to the Git content-addressed blobs.
        saved_report = {k: v for k, v in report.items() if k != 'assets'}
        saved_report.update(base_commit=base, assets=[{k: v for k, v in r.items() if k != 'local_file'} for r in records])
        proof_data = (json.dumps(saved_report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        proof_blob = api('POST', 'git/blobs', {'content': base64.b64encode(proof_data).decode('ascii'), 'encoding': 'base64'})
        if checked_git_sha(proof_blob.get('sha')) != git_blob_sha(proof_data):
            fail('Permanent proof blob hash differs from submitted bytes')
        entries.append({'path': REPORT_PATH, 'mode': '100644', 'type': 'blob', 'sha': proof_blob['sha']})
        tree_sha = checked_git_sha(api('POST', 'git/trees', {'base_tree': base_tree, 'tree': entries})['sha'])
        commit_sha = checked_git_sha(api('POST', 'git/commits', {
            'message': 'Archive 45 reviewed final media files for 6 October confirmed deliveries',
            'tree': tree_sha, 'parents': [base]})['sha'])
        outcome.update(status='COMMIT_CREATED_REF_NOT_YET_UPDATED', media_output_commit=commit_sha)
        write_json(work / 'persistence-result.json', outcome)
        if api('GET', 'git/ref/heads/' + BRANCH)['object']['sha'] != base:
            fail('media-output advanced before nonforce update; reconcile rather than overwrite or retry')
        api('PATCH', 'git/refs/heads/' + BRANCH, {'sha': commit_sha, 'force': False})
        outcome['status'] = 'REF_UPDATED_READBACK_PENDING'
        write_json(work / 'persistence-result.json', outcome)
    actual = checked_git_sha(api('GET', 'git/ref/heads/' + BRANCH)['object']['sha'])
    if actual != commit_sha:
        fail('media-output head changed during live readback; preserve evidence and reconcile')
    live_tree = checked_git_sha(api('GET', 'git/commits/' + actual)['tree']['sha'])
    if live_tree != tree_sha:
        fail('Live commit tree differs from intended tree')
    live_cache, verified = {}, []
    for path, (_, record) in files.items():
        entry = tree_entry(live_tree, path, live_cache)
        if (not entry or entry.get('type') != 'blob' or entry.get('mode') != '100644'
                or entry.get('sha') != record['git_blob_sha1'] or entry.get('size') != record['bytes']):
            fail('Final path/blob/byte-count readback mismatch: ' + path)
        verified.append({'path': path, 'sha256': record['sha256'], 'bytes': record['bytes'],
                         'git_blob_sha1': entry['sha'], 'tree_readback_verified': True})
    if api('GET', 'git/ref/heads/' + BRANCH)['object']['sha'] != actual:
        fail('Branch changed during final path verification; reconcile before reporting success')
    outcome.update(status='ALL_45_MEDIA_PERSISTED_AND_LIVE_READBACK_VERIFIED',
        media_output_commit=actual, tree_sha=live_tree, completed_at_utc=now(),
        asset_count=45, jpeg_count=35, mp4_count=10, total_bytes=sum(r['bytes'] for r in records),
        already_present=complete, assets=verified,
        verification_note='Each SHA256 was measured from actual reviewed CDN bytes. Git blob SHA1 was derived from those exact bytes, checked against API creation, and all final tree blob IDs and sizes were read back at the verified live commit.')
    write_json(work / 'persistence-result.json', outcome)
    print(json.dumps({k: v for k, v in outcome.items() if k != 'assets'}))
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_path:
        with open(summary_path, 'a', encoding='utf-8') as summary:
            summary.write(f'## Final media archive verified\n\n45 files: 35 JPEG + 10 MP4; 10 logical posts; 40 existing Metricool destination records. Only records explicitly marked PUBLISHED are published.\n\nCommit: `{actual}` on `media-output`.\n\nAll reviewed SHA256 values, Git blob IDs, and byte counts verified. No publication action was performed by this workflow.\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['validate', 'persist'], required=True)
    parser.add_argument('--manifest', type=Path, default=Path(MANIFEST_PATH))
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    try:
        (validate if args.mode == 'validate' else persist)(args.manifest, args.work)
    except Exception as error:
        # Keep a concise bounded failure record; never log credentials or HTTP bodies.
        write_json(args.work / ('failure-' + args.mode + '.json'), {
            'status': 'FAILED_REQUIRES_RECONCILIATION', 'mode': args.mode,
            'time_utc': now(), 'error_type': type(error).__name__, 'message': str(error)[:1200],
            'automatic_retry_performed': False, 'publish_action_performed': False})
        raise


if __name__ == '__main__':
    main()
