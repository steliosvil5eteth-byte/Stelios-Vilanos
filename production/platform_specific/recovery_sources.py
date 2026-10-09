#!/usr/bin/env python3
"""Package acquired photographs and an explicit visual-review record.

This helper makes no network, audio, rendering or publication calls. It accepts
only an already reviewed source plan tied to the acquired image byte hashes.
"""
from pathlib import Path
import datetime as dt
import hashlib
import html
import json
import re

from PIL import Image


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(value):
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def build_pack(pack, job, plan, review, intro, hashtags):
    pack = Path(pack)
    if (pack / "inventory.json").exists():
        raise RuntimeError("Preserve existing completed source inventory")
    if len(plan) != len(job["script"].strip().split("\n\n")):
        raise RuntimeError("One source image per unchanged paragraph is required")
    if not review.get("all_actual_images_viewed") or not review.get("review_artifact"):
        raise RuntimeError("An explicit actual-source visual review is required")
    if not Path(review["review_artifact"]).is_file():
        raise RuntimeError("Review artifact is missing")
    script_path = pack / "script.txt"
    if script_path.read_text().strip() != job["script"].strip():
        raise RuntimeError("Source script changed")
    assets = []
    for index, row in enumerate(plan, 1):
        page = row["metadata"]
        info = page["imageinfo"][0]
        meta = info.get("extmetadata", {})
        value = lambda key: clean(meta.get(key, {}).get("value"))
        path = Path(row.get("path") or pack / "assets" / f"{index:02}.jpg")
        image_hash = file_sha(path)
        if review["reviewed_sha256"][index - 1] != image_hash:
            raise RuntimeError("Review does not cover these exact image bytes")
        with Image.open(path) as im:
            dimensions = list(im.size)
            im.verify()
        creator = row.get("creator") or value("Artist")
        license_name = row.get("license") or value("LicenseShortName")
        source_page = info["descriptionurl"]
        license_url = row.get("license_url") or value("LicenseUrl") or source_page
        if not all([creator, license_name, license_url, row["label"], row["context"]]):
            raise RuntimeError("Incomplete source, creator, license or context")
        assets.append({"scene": index, "paragraph_index": index,
                       "path": str(path), "sha256": image_hash,
                       "bytes": path.stat().st_size, "dimensions_px": dimensions,
                       "asset_label": row["label"], "source_page_url": source_page,
                       "media_url": row.get("media_url") or info["thumburl"],
                       "original_media_url": info["url"], "source_title": page["title"],
                       "creator": creator, "creator_display": row.get("creator_display") or creator,
                       "license": license_name, "license_url": license_url,
                       "historical_context": row["context"], "layout": row.get("layout", "contain"),
                       "asset_type": row.get("asset_type", "photograph"),
                       "source_reuse_reason": row.get("source_reuse_reason", ""),
                       "commons_page_id": page["pageid"],
                       "source_visual_review_complete": True,
                       "source_visual_review_method": review["method"]})
    seen = {}
    for asset in assets:
        previous = seen.get(asset["sha256"])
        if previous:
            identity = ("source_page_url", "creator", "license", "license_url")
            if not asset["source_reuse_reason"].strip() or any(asset[k] != previous[k] for k in identity):
                raise RuntimeError("Repeated sources need an explicit reason and consistent source identity")
        else:
            seen[asset["sha256"]] = asset
    photographs_only = all(asset["asset_type"] == "photograph" for asset in assets)
    material_label = "Φωτογραφίες αρχείου" if photographs_only else "Φωτογραφίες και τεκμήρια αρχείου"
    inventory = {"schema_version": 1, "job_id": job["id"], "story_id": job["story_id"],
                 "title": job["title"], "platform": job["platform"], "brand_id": 7076410,
                 "script_path": str(script_path),
                 "script_sha256": hashlib.sha256(job["script"].strip().encode()).hexdigest(),
                 "disclosure": ("Φωτογραφίες αρχείου" if photographs_only else "Αρχειακό υλικό") + " · Συνθετική αφήγηση", "assets": assets,
                 "unique_source_count": len(seen),
                 "sources": job["sources"], "source_visual_review_complete": True,
                 "actual_audio_listened": False, "exact_final_visual_review": False,
                 "passed_final_review": False, "publishable": False}
    credits = "\n".join(f"{a['scene']}. {a['creator']} · {a['license']} · https://commons.wikimedia.org/?curid={a['commons_page_id']}" for a in assets)
    caption = (intro + "\n\n" + material_label + ". Συνθετική αφήγηση Νέστορα. Προσαρμογή μεγέθους, θολό φόντο, μοντάζ και υπότιτλοι. "
               "Σύνθεση οπτικού υλικού: CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/).\n\nΟπτικές πηγές / άδειες:\n" + credits +
               "\n\nΑν σας άρεσε, ακολουθήστε για περισσότερα.\n" + hashtags)
    if job["platform"] == "instagram" and len(caption) > 2200:
        raise RuntimeError(f"Caption exceeds Instagram limit: {len(caption)}")
    attribution = (f"# Οπτικές πηγές — {job['title']}\n\n"
                   "Οι πηγές διατηρούνται ολόκληρες και προσαρμόζονται σε κάδρο 9:16. "
                   "Προστίθενται θολό αντίγραφο στο φόντο, τίτλος, λεζάντες και υπότιτλοι. "
                   "Η αφήγηση είναι συνθετική. Η σύνθεση οπτικού υλικού διατίθεται με CC BY-SA 4.0 "
                   "(https://creativecommons.org/licenses/by-sa/4.0/). Οι πρωτογενείς πηγές διατηρούν τις άδειές τους.\n\n")
    for a in assets:
        attribution += (f"## Σκηνή {a['scene']} — {a['asset_label']}\n\n"
                        f"- Αρχείο: {a['source_title']}\n- Δημιουργός: {a['creator']}\n"
                        f"- Πηγή και τεκμήριο άδειας: {a['source_page_url']}\n"
                        f"- Άδεια: {a['license']} — {a['license_url']}\n"
                        f"- Κατεβασμένο μέσο: {a['media_url']}\n- SHA256: {a['sha256']}\n"
                        f"- Πλαίσιο: {a['historical_context']}\n\n")
    review = {**review, "job_id": job["id"], "reviewed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "actual_audio_listened": False, "exact_final_visual_review": False, "passed_final_review": False}
    for name, value in [("inventory.json", inventory), ("source_review.json", review)]:
        (pack / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    (pack / "caption.txt").write_text(caption + "\n")
    (pack / "source_attributions.md").write_text(attribution)
    return {"job_id": job["id"], "inventory": str(pack / "inventory.json"), "assets": len(assets), "caption_characters": len(caption)}
