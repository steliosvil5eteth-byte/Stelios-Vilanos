"""Audit Metricool queue coverage against the sole active CURRENT_TEN_DAILY strategy. Read-only."""
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
        raise SystemExit(f"FAIL_CLOSED: CURRENT_TEN requires exactly 10 standing series, found {len(slots)}")
    if len({str(x["time"]) for x in slots}) != 10:
        raise SystemExit("FAIL_CLOSED: duplicate standing slot times in active strategy")
    physical=sum(int(x.get("member_posts",1)) for x in slots)
    destinations=physical*len(NETWORKS)
    if physical != 15 or destinations != 60:
        raise SystemExit(f"FAIL_CLOSED: expected 15 physical member posts / 60 destinations, got {physical}/{destinations}")
    return sid,slots,physical,destinations

def _provider_rows(matches, network):
    return [(p,q) for p in matches for q in p.get("providers",[]) if q.get("network")==network]

def audit(posts,today,slots,physical,destinations,days=3):
    report={"today":today.isoformat(),"timezone":"Europe/Athens","minimum_days":2,
            "target_days":3,"consecutive_complete_days":0,
            "required_standing_series":10,
            "required_physical_member_posts":physical,
            "required_destinations":destinations,
            "days":[]}
    consecutive=True
    for offset in range(1,days+1):
        day=(today+timedelta(days=offset)).isoformat()
        row={"date":day,"complete":True,"standing_series":[],"destination_count":0}
        for spec in slots:
            slot=str(spec["time"]); category=str(spec["category"])
            expected=int(spec.get("member_posts",1))
            stamp=day+"T"+slot+":00"
            matches=[p for p in posts
                     if p.get("publicationDate",{}).get("dateTime")==stamp
                     and p.get("publicationDate",{}).get("timezone")=="Europe/Athens"
                     and not p.get("draft") and p.get("autoPublish") is True]
            network_counts={}
            missing=[]; excess=[]; bad=[]
            for network in NETWORKS:
                providers=_provider_rows(matches,network)
                network_counts[network]=len(providers)
                row["destination_count"] += len(providers)
                if len(providers) < expected:
                    missing.append({"network":network,"expected":expected,"found":len(providers)})
                if len(providers) > expected:
                    excess.append({"network":network,"expected":expected,"found":len(providers)})
                if any(q.get("status") not in ("PENDING","SCHEDULED","PUBLISHED") for _,q in providers):
                    bad.append(network)
            # For zodiac bundle, six separate member posts are mandatory.
            # Distinct post records may be split social-vs-YouTube, so provider count per network
            # is the reliable queue-level check; exact pair coverage remains a final-media QA gate.
            good=not (missing or excess or bad)
            row["complete"] &= good
            row["standing_series"].append({
                "time":slot,"category":category,
                "expected_member_posts":expected,
                "complete":good,
                "post_ids":[p.get("id") for p in matches],
                "network_counts":network_counts,
                "missing":missing,"excess":excess,"unexpected_status":bad
            })
        if len(row["standing_series"]) != 10 or row["destination_count"] != destinations:
            row["complete"]=False
        report["days"].append(row)
        consecutive &= row["complete"]
        if consecutive: report["consecutive_complete_days"]+=1
    report["minimum_met"]=report["consecutive_complete_days"]>=2
    report["target_met"]=report["consecutive_complete_days"]>=3
    report["note"]="Queue coverage only. Zodiac requires six member posts (24 destinations) inside the single 11:00 standing series. Exact pair coverage, final visual QA, dedupe and provider/public reconciliation remain separate hard gates."
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--queue",required=True)
    p.add_argument("--today",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--strategy",default="config/content_strategy.json")
    a=p.parse_args()
    sid,slots,physical,destinations=load_strategy(a.strategy)
    raw=json.loads(Path(a.queue).read_text())
    posts=raw.get("data",[]) if isinstance(raw,dict) else raw
    result=audit(posts,date.fromisoformat(a.today),slots,physical,destinations)
    result["strategy_id"]=sid
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({"strategy_id":sid,"minimum_met":result["minimum_met"],
                      "target_met":result["target_met"],
                      "consecutive_complete_days":result["consecutive_complete_days"],
                      "required_physical_member_posts":physical,
                      "required_destinations":destinations}))
