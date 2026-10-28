#!/usr/bin/env python3
"""Offline, read-only content readiness audit. Never publishes."""
import json
import sys
from collections import Counter
from pathlib import Path

CATEGORIES = {
    "emotional_story": 5, "greek_fictional_myth": 1, "zodiac": 1,
    "general_comparison": 1, "greece_two_years": 1, "name_day_greetings": 1,
}
REQUIRED = {"id", "category", "title", "opening", "ending", "plot_key",
            "source_status", "qa_status", "cost_eur", "published"}
FACTUAL = {"general_comparison", "greece_two_years", "name_day_greetings"}
BASE = Path(__file__).resolve().parent


def audit(manifest):
    errors, warnings = [], []
    if not isinstance(manifest, dict):
        return {"ready": False, "status": "BLOCKED",
                "errors": ["Manifest must be an object"], "warnings": [],
                "publishing_enabled": False}
    items = manifest.get("items", [])
    if not isinstance(items, list):
        return {"ready": False, "status": "BLOCKED",
                "errors": ["items must be a list"], "warnings": [],
                "publishing_enabled": False}
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
        if type(item.get("cost_eur")) not in (int, float) or item["cost_eur"] != 0:
            errors.append(f"Item {i + 1}: nonzero or unknown cost")
        if item.get("published") is not False:
            errors.append(f"Item {i + 1}: published status must explicitly be false")
    for category, expected in CATEGORIES.items():
        if counts[category] != expected:
            errors.append(f"{category}: expected {expected}, found {counts[category]}")
    if len(items) != 10:
        errors.append(f"Expected 10 distinct videos, found {len(items)}")
    for field in ("id", "title", "opening", "ending", "plot_key"):
        values = [str(item.get(field, "")).strip().casefold()
                  for item in items if isinstance(item, dict)]
        if any(not value for value in values):
            errors.append(f"Empty {field} detected")
        if len(values) != len(set(values)):
            errors.append(f"Repeated {field} detected")
    if manifest.get("history_checked") is not True:
        errors.append("Historical deduplication not verified")
    if manifest.get("calendar_verified") is not True:
        errors.append("Greek name-day calendar not verified")
    if manifest.get("manual_review_confirmed") is not True:
        errors.append("Manual final review missing")
    return {
        "ready": not errors, "status": "REVIEW_READY" if not errors else "BLOCKED",
        "errors": errors, "warnings": warnings, "counts": dict(counts),
        "publishing_enabled": False, "external_calls": 0,
    }


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "sample_manifest.json"
    if not path.is_file():
        print(json.dumps({"ready": False, "errors": [f"Missing manifest: {path}"]},
                         ensure_ascii=False))
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
