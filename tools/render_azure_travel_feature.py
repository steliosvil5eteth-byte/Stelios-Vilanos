#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
import render_azure_feature_batch as base


def diverse_commons_search(queries, outdir: Path, target: int):
    outdir.mkdir(parents=True, exist_ok=True)
    records = []
    seen = set()
    for i, q in enumerate(queries, 1):
        if len(records) >= target:
            break
        tmp = outdir.parent / f'_q{i:02d}'
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            recs = base.commons_search([q], tmp, 1)
        except Exception:
            continue
        rec = recs[0]
        key = rec.get('source_page') or rec.get('file')
        if key in seen:
            continue
        src = next(tmp.glob('*.jpg'))
        dst = outdir / f'{len(records)+1:02d}.jpg'
        shutil.copy2(src, dst)
        records.append(rec)
        seen.add(key)
    if len(records) < target:
        raise RuntimeError(f'Only {len(records)} distinct rights-cleared photos found; need {target}')
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--output', required=True)
    ns = ap.parse_args()
    batch = json.loads(Path(ns.manifest).read_text(encoding='utf-8'))
    if batch.get('approved') is not True or batch.get('paid_generation_allowed') is not False:
        raise RuntimeError('zero-cost approval gate failed')
    outroot = Path(ns.output)
    outroot.mkdir(parents=True, exist_ok=True)
    summary = []
    for job in batch.get('jobs') or []:
        if job.get('voice') != base.VOICE or job.get('background_music') is not False:
            raise RuntimeError('voice/audio policy mismatch')
        if not job['script'].rstrip().endswith(base.CTA):
            raise RuntimeError('CTA gate failed')
        root = outroot / job['id']
        photos = root / 'photos'
        photos.mkdir(parents=True, exist_ok=True)
        records = diverse_commons_search(job['commons_queries'], photos, int(job.get('photo_target', 8)))
        (root / 'visual-attribution.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
        wav, bounds, dur = base.synthesize(job['script'], root)
        (root / 'speech-meta.json').write_text(json.dumps({'voice': base.VOICE, 'duration_seconds': round(dur, 3), 'background_music': False, 'word_boundaries': len(bounds)}, ensure_ascii=False, indent=2), encoding='utf-8')
        srt = root / 'subs.srt'
        cap_count = base.subtitles(bounds, dur, srt)
        video = root / (job['id'] + '.mp4')
        base.make_video(job, photos, wav, srt, dur, video)
        result = base.qa(job, video, dur, len(records), cap_count)
        result['diverse_query_sourcing'] = True
        (root / 'qa.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        summary.append(result)
    (outroot / 'qa-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
