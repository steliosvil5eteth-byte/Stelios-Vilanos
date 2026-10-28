#!/usr/bin/env python3
"""New Social Control Center v1: local, read-only, zero external calls.

Usage: python3 new_system/control_center.py [path/to/manifest.json]
No GitHub Actions, network requests, publishing, or paid APIs.
"""
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CATEGORIES = {
    "emotional_story": 5,
    "greek_fictional_myth": 1,
    "zodiac": 1,
    "general_comparison": 1,
    "greece_two_years": 1,
    "name_day_greetings": 1,
}
REQUIRED = {"id", "category", "title", "opening", "ending", "plot_key", "source_status", "qa_status"}
FACTUAL = {"general_comparison", "greece_two_years", "name_day_greetings"}
BASE = Path(__file__).resolve().parent


def audit(manifest):
    errors, warnings = [], []
    if not isinstance(manifest, dict):
        return {"ready": False, "errors": ["Manifest must be an object"], "warnings": []}
    items = manifest.get("items", [])
    if not isinstance(items, list):
        return {"ready": False, "errors": ["items must be a list"], "warnings": []}
    if manifest.get("brand_id") != 7076410:
        errors.append("Wrong or missing brand_id (expected 7076410)")
    if manifest.get("timezone") != "Europe/Athens":
        errors.append("Timezone must be Europe/Athens")
    counts = Counter()
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"Item {i + 1} is not an object")
            continue
        missing = REQUIRED - set(item)
        if missing:
            errors.append(f"Item {i + 1} missing: {', '.join(sorted(missing))}")
        category = item.get("category")
        counts[category] += 1
        if category not in CATEGORIES:
            errors.append(f"Item {i + 1}: unknown category")
        if item.get("qa_status") != "approved":
            errors.append(f"Item {i + 1}: QA not approved")
        if category in FACTUAL and item.get("source_status") != "verified":
            errors.append(f"Item {i + 1}: factual sources not verified")
        if category == "greek_fictional_myth" and item.get("fiction_disclosure") is not True:
            errors.append(f"Item {i + 1}: missing fiction disclosure")
        if item.get("cost_eur", 0) != 0:
            errors.append(f"Item {i + 1}: nonzero or unknown cost")
        if item.get("published") is True:
            warnings.append(f"Item {i + 1}: already marked published; never republish automatically")
    for cat, expected in CATEGORIES.items():
        if counts[cat] != expected:
            errors.append(f"{cat}: expected {expected}, found {counts[cat]}")
    if len(items) != 10:
        errors.append(f"Expected 10 distinct videos, found {len(items)}")
    for field in ("id", "title", "opening", "ending", "plot_key"):
        values = [str(x.get(field, "")).strip().casefold() for x in items if isinstance(x, dict)]
        nonempty = [x for x in values if x]
        if len(nonempty) != len(set(nonempty)):
            errors.append(f"Repeated {field} detected")
    if not manifest.get("history_checked", False):
        errors.append("Historical deduplication not verified")
    if not manifest.get("calendar_verified", False):
        errors.append("Greek name-day calendar not verified")
    if not manifest.get("manual_review_confirmed", False):
        errors.append("Manual final review missing")
    return {
        "ready": not errors,
        "status": "REVIEW_READY" if not errors else "BLOCKED",
        "errors": errors,
        "warnings": warnings,
        "counts": dict(counts),
        "publishing_enabled": False,
        "external_calls": 0,
    }


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "sample_manifest.json"
    if not path.is_file():
        print(json.dumps({"ready": False, "errors": [f"Missing manifest: {path}"]}, ensure_ascii=False))
        return 2
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"ready": False, "errors": [str(exc)]}, ensure_ascii=False))
        return 2
    result = audit(manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
