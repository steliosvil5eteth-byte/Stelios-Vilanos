#!/usr/bin/env python3
"""Build the bounded archival manifest from verified actual Metricool deliveries."""
from pathlib import Path
import hashlib
import json
import shutil

BASE = Path(__file__).resolve().parent
OUT = BASE / 'persistence' / 'commit_files'
NARRATED = {
    'greece_two_day_trip': 'prespes',
    'strange_real_phenomenon': 'singing_dunes',
    'documented_experiments': 'ikea_effect',
    'international_legend': 'tsukumogami',
}
SERIES = {'relationships', 'survival', 'dog_bartender', 'zodiac',
          'love_soul_relationship', 'myth_or_truth', *NARRATED}
NETWORKS = {'facebook', 'instagram', 'tiktok', 'youtube'}

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(rel, value):
    target = OUT / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def main():
    journal = read(BASE / 'release_journal.json')
    if str(journal['brandId']) != '7076410' or journal['date'] != '2026-10-06':
        raise RuntimeError('Unexpected brand or date')
    grouped = {s: [] for s in SERIES}
    for post in journal['metricool_posts']:
        series = journal['mapping'].get(str(post['id']))
        if series not in SERIES:
            raise RuntimeError('Unmapped or unexpected post: ' + str(post['id']))
        grouped[series].append(post)
    assets, summaries = [], []
    for series, posts in sorted(grouped.items()):
        providers = [x['network'] for post in posts for x in post['providers']]
        if len(providers) != 4 or set(providers) != NETWORKS:
            raise RuntimeError('Incomplete or duplicate provider coverage: ' + series)
        folder = BASE / 'narrated' / NARRATED[series] / 'final' if series in NARRATED else BASE / 'final' / series
        manifest = read(folder / 'manifest.json')
        if manifest.get('publish_ready') is not True:
            raise RuntimeError('Missing final release decision: ' + series)
        job_id = manifest.get('job_id') or manifest.get('id')
        if not job_id or not job_id.startswith('current-ten-20261006-'):
            raise RuntimeError('Unexpected job ID: ' + series)
        for post in posts:
            video_post = series in NARRATED or any(p['network'] == 'youtube' for p in post['providers'])
            if video_post:
                videos = list(folder.glob('current-ten-20261006-*.mp4'))
                if len(videos) != 1 or len(post['media']) != 1:
                    raise RuntimeError('Expected exactly one complete final video')
                file = videos[0]
                qa = read(folder / 'qa.json') if series in NARRATED else manifest['video']
                duration = float(qa.get('duration_seconds') or qa.get('duration'))
                assets.append({'job_id': job_id, 'series': series,
                    'path': f'jobs/{job_id}/final/{file.name}', 'url': post['media'][0],
                    'allowed_sha256': [sha(file)], 'width': 1080, 'height': 1920,
                    'min_duration_seconds': duration - 0.1,
                    'max_duration_seconds': duration + 0.1,
                    'metricool_post_id': post['id']})
            else:
                cards = sorted(folder.glob('card-*.jpg'))
                if len(cards) != len(post['media']):
                    raise RuntimeError('Card count changed: ' + series)
                for file, url in zip(cards, post['media']):
                    known = [file, folder / 'hosted' / file.name]
                    assets.append({'job_id': job_id, 'series': series,
                        'path': f'jobs/{job_id}/final/{file.name}', 'url': url,
                        'allowed_sha256': sorted({sha(p) for p in known if p.exists()}),
                        'width': 1080, 'height': 1080, 'metricool_post_id': post['id']})
        archive_dir = OUT / 'media_jobs' / 'current_ten_20261006_release' / series
        archive_dir.mkdir(parents=True, exist_ok=True)
        for name in ['manifest.json', 'caption.txt', 'final-caption.txt', 'subs.ass', 'qa.json', 'audio-binding.json',
                     'final_visual_qa.json', 'final_audio_qa.json',
                     'final_visual_language_qa.json', 'scene-timing.json', 'render-command.json',
                     'root_release_decision.json', 'fresh_dedupe_at_create.json']:
            file = folder / name
            if file.exists():
                shutil.copy2(file, archive_dir / name)
        if series in NARRATED:
            registry = folder.parent / 'source_registry.json'
            if registry.exists():
                shutil.copy2(registry, archive_dir / 'source_registry.json')
        summaries.append({'series': series, 'job_id': job_id, 'title': manifest['title'],
            'content_key': manifest['content_key'], 'metricool_ids': [p['id'] for p in posts],
            'destinations': [{'network': x['network'], 'status': x['status'],
                'url': x.get('publicUrl'), 'metricool_post_id': p['id'],
                'scheduled_time': p['publicationDate']} for p in posts for x in p['providers']]})
    if len(assets) != 45 or len({a['path'] for a in assets}) != 45 or len({a['url'] for a in assets}) != 45:
        raise RuntimeError('Expected 45 unique final media assets')
    if sum(a['path'].endswith('.mp4') for a in assets) != 10:
        raise RuntimeError('Expected exactly 10 final videos')
    write('media_jobs/current_ten_20261006_final_delivery_assets.json', {
        'brandId': 7076410, 'date': '2026-10-06', 'expected_asset_count': 45,
        'expected_logical_posts': 10, 'expected_provider_destinations': 40,
        'release_journal_path': 'media_jobs/current_ten_20261006_delivery_journal.json',
        'assets': assets})
    write('media_jobs/current_ten_20261006_delivery_journal.json', journal)
    write('media_jobs/current_ten_20261006_release_summary.json', {'brandId': 7076410,
        'date': '2026-10-06', 'logical_posts': summaries,
        'meaning': 'Actual scheduled/published destinations; scheduled is not published.'})
    print(json.dumps({'logical_posts': 10, 'provider_destinations': 40, 'assets': len(assets),
                      'output': str(OUT)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
