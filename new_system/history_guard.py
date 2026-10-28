"""Offline read-only history screening. Never writes to Notion or publishes."""
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

FIELDS = {"title": "Title", "opening": "Hook", "plot_key": "Fingerprint"}

def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+", value, re.UNICODE))

def check(items, archive, archive_complete=False, threshold=0.88):
    issues = []
    if not archive_complete:
        issues.append("Archive completeness not independently confirmed")
    if not isinstance(items, list) or not isinstance(archive, list):
        return {"clear": False, "issues": issues + ["Invalid items/archive structure"], "matches": []}
    matches = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(f"Invalid candidate {i}")
            continue
        for field, archive_field in FIELDS.items():
            value = normalize(item.get(field))
            if not value:
                issues.append(f"Candidate {i}: missing {field}")
                continue
            for j, row in enumerate(archive):
                if not isinstance(row, dict):
                    issues.append(f"Invalid archive row {j}")
                    continue
                past = normalize(row.get(archive_field))
                if past and SequenceMatcher(None, value, past).ratio() >= threshold:
                    matches.append({"candidate": i, "archive_row": j, "field": field,
                                    "archive_title": str(row.get("Title", ""))})
    return {"clear": not issues and not matches, "issues": sorted(set(issues)),
            "matches": matches, "archive_rows_checked": len(archive)}

def main():
    if len(sys.argv) != 4:
        print("Usage: history_guard.py manifest.json archive_rows.json completeness.json")
        return 2
    try:
        manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        archive = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        proof = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        result = check(manifest["items"], archive, proof.get("archive_complete") is True)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"clear": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["clear"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
