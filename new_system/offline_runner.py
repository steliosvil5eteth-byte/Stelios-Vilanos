"""Read-only daily execution report. Never connects to providers or publishes."""
import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from daily_planner import build
from control_center import audit

def report(day):
    plan = build(day)
    inspection = audit(plan)
    return {
        "date": day,
        "mode": "OFFLINE_READ_ONLY",
        "state": "BLOCKED",
        "publishing_enabled": False,
        "external_writes": 0,
        "slot_count": len(plan["items"]),
        "pending_slots": [x["id"] for x in plan["items"]],
        "validation_errors": inspection["errors"],
        "next_step": "Complete canonical first story; verify 16 individual scene assets and natural narration.",
        "note": "This audit is NOT an automatic content generation or publishing worker."
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=date.today().isoformat())
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    data = report(args.date)
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)
if __name__ == "__main__":
    main()
