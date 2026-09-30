"""Audit Metricool queue coverage against the sole active content strategy. Read-only."""
import argparse, json
from datetime import date, timedelta
from pathlib import Path

NETWORKS=("facebook","instagram","tiktok","youtube")

def load_strategy(path):
    cfg=json.loads(Path(path).read_text())
    sid=str(cfg.get("strategy_id",""))
    slots=cfg.get("slots") or []
    brand=(cfg.get("active_metricool_brand") or {}).get("id")
    if not sid.startswith("CURRENT_TEN_DAILY"):
        raise SystemExit(f"FAIL_CLOSED: inactive/legacy strategy_id {sid!r}")
    if brand != 7076410:
        raise SystemExit(f"FAIL_CLOSED: wrong active brand {brand!r}")
    if len(slots) != 10:
        raise SystemExit(f"FAIL_CLOSED: CURRENT_TEN requires exactly 10 standing slots, found {len(slots)}")
    pairs=[(str(x["time"]),str(x["category"])) for x in slots]
    if len(set(t for t,_ in pairs)) != 10:
        raise SystemExit("FAIL_CLOSED: duplicate standing slot times in active strategy")
    return sid,pairs

def audit(posts,today,slots,days=3):
    report={"today":today.isoformat(),"timezone":"Europe/Athens","minimum_days":2,
            "target_days":3,"consecutive_complete_days":0,"required_slot_count":10,"days":[]}
    consecutive=True
    for offset in range(1,days+1):
        day=(today+timedelta(days=offset)).isoformat()
        row={"date":day,"complete":True,"slots":[]}
        for slot,category in slots:
            stamp=day+"T"+slot+":00"
            matches=[p for p in posts
                     if p.get("publicationDate",{}).get("dateTime")==stamp
                     and p.get("publicationDate",{}).get("timezone")=="Europe/Athens"
                     and not p.get("draft") and p.get("autoPublish") is True]
            missing=[]; bad=[]
            for network in NETWORKS:
                providers=[q for p in matches for q in p.get("providers",[]) if q.get("network")==network]
                if not providers: missing.append(network)
                if any(q.get("status") not in ("PENDING","SCHEDULED","PUBLISHED") for q in providers):
                    bad.append(network)
            good=not (missing or bad)
            row["complete"] &= good
            row["slots"].append({"time":slot,"category":category,"complete":good,
                                 "post_ids":[p.get("id") for p in matches],
                                 "missing":missing,"unexpected_status":bad})
        if len(row["slots"]) != 10:
            row["complete"]=False
        report["days"].append(row)
        consecutive &= row["complete"]
        if consecutive: report["consecutive_complete_days"]+=1
    report["minimum_met"]=report["consecutive_complete_days"]>=2
    report["target_met"]=report["consecutive_complete_days"]>=3
    report["note"]="Coverage only. Exact-final visual QA, current sub-format rules, deduplication and publish reconciliation remain separate hard gates."
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--queue",required=True)
    p.add_argument("--today",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--strategy",default="config/content_strategy.json")
    a=p.parse_args()
    sid,slots=load_strategy(a.strategy)
    raw=json.loads(Path(a.queue).read_text())
    posts=raw.get("data",[]) if isinstance(raw,dict) else raw
    result=audit(posts,date.fromisoformat(a.today),slots)
    result["strategy_id"]=sid
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({"strategy_id":sid,"minimum_met":result["minimum_met"],
                      "target_met":result["target_met"],
                      "consecutive_complete_days":result["consecutive_complete_days"]}))
