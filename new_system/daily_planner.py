"""Deterministic offline draft planner. Never publishes."""
import argparse
import json
from datetime import date
from pathlib import Path

SLOTS = [
    ("09:00", "emotional_story"), ("10:30", "zodiac"),
    ("12:00", "emotional_story"), ("13:30", "general_comparison"),
    ("15:00", "emotional_story"), ("16:30", "greek_fictional_myth"),
    ("18:00", "emotional_story"), ("19:30", "greece_two_years"),
    ("21:00", "emotional_story"), ("22:30", "name_day_greetings"),
]

def build(day):
    date.fromisoformat(day)
    return {
        "date": day, "brand_id": 7076410, "timezone": "Europe/Athens",
        "history_checked": False, "calendar_verified": False,
        "manual_review_confirmed": False, "publishing_enabled": False,
        "items": [
            {"id": f"{day}-{i:02d}", "slot_local": time, "category": category,
             "title": "", "opening": "", "ending": "", "plot_key": "",
             "source_status": "unverified", "qa_status": "draft",
             "cost_eur": 0, "published": False, "status": "BLOCKED_PENDING_CONTENT"}
            for i, (time, category) in enumerate(SLOTS, 1)
        ],
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("date")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build(args.date)
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            parser.error("Output already exists; refusing overwrite")
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")

if __name__ == "__main__":
    main()
