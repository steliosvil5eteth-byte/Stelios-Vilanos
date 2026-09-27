"""Check a live Metricool snapshot for complete future days. Read-only."""
import argparse, json
from datetime import date, timedelta
from pathlib import Path

SLOTS = {"09:00":"survival", "11:00":"zodiac", "15:00":"love_soul_relationship",
         "17:00":"strange_real_phenomenon", "20:00":"myth_or_truth"}
NETWORKS = ("facebook", "instagram", "tiktok", "youtube")

def audit(posts, today, days=3):
    report = {"today":today.isoformat(), "timezone":"Europe/Athens", "minimum_days":2,
              "target_days":3, "consecutive_complete_days":0, "days":[]}
    consecutive = True
    for offset in range(1, days+1):
        day = (today+timedelta(days=offset)).isoformat()
        row = {"date":day, "complete":True, "slots":[]}
        for slot, category in SLOTS.items():
            stamp = day+"T"+slot+":00"
            matches = [p for p in posts if p.get("publicationDate",{}).get("dateTime")==stamp
                       and p.get("publicationDate",{}).get("timezone")=="Europe/Athens"
                       and not p.get("draft") and p.get("autoPublish") is True]
            missing, duplicates, bad = [], [], []
            for network in NETWORKS:
                providers = [(p, q) for p in matches for q in p.get("providers",[])
                             if q.get("network")==network]
                if not providers: missing.append(network)
                if len(providers)>1: duplicates.append(network)
                if any(q.get("status") not in ("PENDING","SCHEDULED") for _,q in providers):
                    bad.append(network)
            good = not (missing or duplicates or bad)
            row["complete"] &= good
            row["slots"].append({"time":slot,"category":category,"complete":good,
                                 "post_ids":[p["id"] for p in matches],"missing":missing,
                                 "duplicate_networks":duplicates,"unexpected_status":bad})
        report["days"].append(row)
        consecutive &= row["complete"]
        if consecutive: report["consecutive_complete_days"] += 1
    report["minimum_met"] = report["consecutive_complete_days"]>=2
    report["target_met"] = report["consecutive_complete_days"]>=3
    report["note"] = "Scheduled coverage only. Final media QA and published reconciliation remain separate gates."
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--queue",required=True)
    p.add_argument("--today",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    raw=json.loads(Path(a.queue).read_text())
    posts=raw.get("data",[]) if isinstance(raw,dict) else raw
    result=audit(posts,date.fromisoformat(a.today))
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({"minimum_met":result["minimum_met"],"target_met":result["target_met"],
                      "consecutive_complete_days":result["consecutive_complete_days"]}))
