"""Read-only queue coverage for an explicitly selected social program."""
import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path

COMMON_PROVIDERS = {"facebook", "instagram", "tiktok"}
READY_STATUSES = {"PENDING", "SCHEDULED", "PUBLISHED"}


def load_strategy(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    sid = str(cfg.get("strategy_id", ""))
    program = str(cfg.get("program_label", ""))
    if sid.startswith("CURRENT_TEN_DAILY") and program == "CURRENT_TEN_DAILY":
        required_providers = COMMON_PROVIDERS
    elif sid.startswith("YOUTUBE_GROWTH_TEN_DAILY") and program == "YOUTUBE_GROWTH_TEN_DAILY":
        required_providers = {"youtube"}
    else:
        raise SystemExit(f"FAIL_CLOSED: inactive/unknown strategy {sid!r}")
    if cfg.get("enabled", cfg.get("active_schedule", False)) is not True:
        raise SystemExit(f"FAIL_CLOSED: strategy {program} is disabled")
    if (cfg.get("active_metricool_brand") or {}).get("id") != 7076410:
        raise SystemExit("FAIL_CLOSED: wrong active brand")
    if cfg.get("timezone") != "Europe/Athens":
        raise SystemExit("FAIL_CLOSED: wrong program timezone")
    providers = cfg.get("providers")
    if not isinstance(providers, list) or len(providers) != len(set(providers)):
        raise SystemExit("FAIL_CLOSED: explicit unique providers are required")
    if set(providers) != required_providers:
        raise SystemExit(f"FAIL_CLOSED: wrong providers for {program}")
    slots = cfg.get("slots") or []
    if len(slots) != 10:
        raise SystemExit("FAIL_CLOSED: exactly ten normal-day slots are required")
    times = [str(x.get("time", "")) for x in slots]
    if len(set(times)) != 10 or any(
        not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", stamp) for stamp in times
    ):
        raise SystemExit("FAIL_CLOSED: invalid or duplicate slot times")
    categories = [str(x.get("category", "")) for x in slots]
    if any(not x for x in categories) or len(set(categories)) != 10:
        raise SystemExit("FAIL_CLOSED: exactly ten distinct slot/category identifiers are required")
    destinations = len(slots) * len(providers)
    if cfg.get("daily_target_logical_posts") != 10 or cfg.get("destination_target_per_day") != destinations:
        raise SystemExit("FAIL_CLOSED: strategy targets disagree with slots/providers")
    if cfg.get("require_format_profile_selection_before_enable"):
        if cfg.get("active_format_profile") not in (cfg.get("format_profiles") or {}):
            raise SystemExit("FAIL_CLOSED: select the YouTube format profile before activation")
    return {
        "strategy_id": sid,
        "program_label": program,
        "providers": tuple(providers),
        "slots": slots,
        "physical": len(slots),
        "destinations": destinations,
        "require_attribution": cfg.get("require_explicit_program_attribution", False),
        "transition": cfg.get("transition") or {},
    }


def _provider_rows(post):
    return [p for p in post.get("providers", []) if isinstance(p, dict)]


def _program_tag(post):
    routing = post.get("routing_context") or {}
    tag = post.get("program_label") or routing.get("program_label")
    if tag:
        return str(tag)
    # Planner labels may carry attribution; reconciled snapshots may instead use
    # routing_context after matching the delivery ledger by id, uuid and media.
    for label in post.get("labels") or []:
        name = label if isinstance(label, str) else label.get("name", "") if isinstance(label, dict) else ""
        if name in {"CURRENT_TEN_DAILY", "YOUTUBE_GROWTH_TEN_DAILY"}:
            return name
    return None


def _on_day(post, day):
    stamp = post.get("publicationDate") or {}
    return stamp.get("timezone") == "Europe/Athens" and str(stamp.get("dateTime", "")).startswith(day + "T")


def _transition_budget(posts, today, strategy):
    transition = strategy["transition"]
    if strategy["providers"] != ("youtube",) or transition.get("date") != today.isoformat():
        return None
    published = set()
    pending = set()
    for index, post in enumerate(posts):
        if not _on_day(post, today.isoformat()):
            continue
        for provider in _provider_rows(post):
            if provider.get("network") != "youtube":
                continue
            identity = str(post.get("id") or post.get("uuid") or f"snapshot-row-{index}")
            if provider.get("status") == "PUBLISHED":
                published.add(identity)
            elif provider.get("status") in {"PENDING", "SCHEDULED"} and not post.get("draft") and post.get("autoPublish") is True:
                pending.add(identity)
    baseline = int(transition.get("already_published_youtube_videos", 0))
    limit = int(transition.get("daily_total_limit", 10))
    published_count = max(baseline, len(published))
    occupied = published_count + len(pending - published)
    return {
        "date": today.isoformat(),
        "daily_total_limit": limit,
        "previously_confirmed_published": baseline,
        "published_in_snapshot": len(published),
        "active_pending_in_snapshot": len(pending - published),
        "remaining_capacity_in_snapshot": max(0, limit - occupied),
        "within_daily_limit": occupied <= limit,
        "note": "Counts cover the supplied snapshot. Refresh complete live history before every create; this report is not publication authorization.",
    }


def audit(posts, today, strategy, days=3):
    networks = strategy["providers"]
    slots = strategy["slots"]
    report = {
        "today": today.isoformat(),
        "timezone": "Europe/Athens",
        "strategy_id": strategy["strategy_id"],
        "program_label": strategy["program_label"],
        "providers": list(networks),
        "minimum_days": 2,
        "target_days": 3,
        "consecutive_complete_days": 0,
        "required_standing_series": len(slots),
        "required_logical_posts": strategy["physical"],
        "required_destinations": strategy["destinations"],
        "days": [],
    }
    consecutive = True
    for offset in range(1, days + 1):
        day = (today + timedelta(days=offset)).isoformat()
        row = {"date": day, "complete": True, "standing_series": [], "destination_count": 0}
        for spec in slots:
            stamp = day + "T" + str(spec["time"]) + ":00"
            candidates = [
                post for post in posts
                if (post.get("publicationDate") or {}).get("dateTime") == stamp
                and (post.get("publicationDate") or {}).get("timezone") == "Europe/Athens"
                and not post.get("draft") and post.get("autoPublish") is True
                and any(p.get("network") in networks for p in _provider_rows(post))
            ]
            matches = []
            attribution_failures = []
            forbidden_providers = []
            wrong_brand = []
            for post in candidates:
                identity = post.get("id") or post.get("uuid")
                tag = _program_tag(post)
                if (tag and tag != strategy["program_label"]) or (strategy["require_attribution"] and not tag):
                    attribution_failures.append(identity)
                    continue
                present_brand = post.get("brand_id", post.get("brandId", post.get("blogId")))
                if present_brand is not None and str(present_brand) != "7076410":
                    wrong_brand.append(identity)
                    continue
                other = sorted({p.get("network") for p in _provider_rows(post) if p.get("network") not in networks})
                if other:
                    forbidden_providers.append({"post_id": identity, "providers": other})
                matches.append(post)
            missing = []
            excess = []
            bad = []
            network_counts = {}
            for network in networks:
                providers = [p for post in matches for p in _provider_rows(post) if p.get("network") == network]
                network_counts[network] = len(providers)
                row["destination_count"] += len(providers)
                if not providers:
                    missing.append({"network": network, "expected": 1, "found": 0})
                if len(providers) > 1:
                    excess.append({"network": network, "expected": 1, "found": len(providers)})
                if any(p.get("status") not in READY_STATUSES for p in providers):
                    bad.append(network)
            good = not (missing or excess or bad or attribution_failures or forbidden_providers or wrong_brand)
            row["complete"] = row["complete"] and good
            row["standing_series"].append({
                "time": spec["time"],
                "category": spec["category"],
                "expected_logical_posts": 1,
                "complete": good,
                "post_ids": [p.get("id") for p in matches],
                "network_counts": network_counts,
                "missing": missing,
                "excess": excess,
                "unexpected_status": bad,
                "unattributed_or_wrong_program_records": attribution_failures,
                "forbidden_providers_in_record": forbidden_providers,
                "wrong_brand_records": wrong_brand,
            })
        if row["destination_count"] != strategy["destinations"]:
            row["complete"] = False
        report["days"].append(row)
        consecutive = consecutive and row["complete"]
        if consecutive:
            report["consecutive_complete_days"] += 1
    report["transition_budget"] = _transition_budget(posts, today, strategy)
    cap_passed = report["transition_budget"] is None or report["transition_budget"]["within_daily_limit"]
    report["minimum_met"] = report["consecutive_complete_days"] >= 2 and cap_passed
    report["target_met"] = report["consecutive_complete_days"] >= 3 and cap_passed
    report["note"] = (
        "Program/provider queue coverage only. Exact-final visual/audio QA, media-hash binding, "
        "cross-program story deduplication and complete live reconciliation remain separate hard gates. "
        "PENDING is not Published. Independent YouTube attribution must come from observed planner "
        "labels or an id/uuid/media-matched delivery ledger; absence blocks coverage."
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--today", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--strategy", default="config/content_strategy.json")
    args = parser.parse_args()
    strategy = load_strategy(args.strategy)
    raw = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    posts = raw.get("data", []) if isinstance(raw, dict) else raw
    result = audit(posts, date.fromisoformat(args.today), strategy)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        key: result[key] for key in (
            "strategy_id", "providers", "minimum_met", "target_met",
            "consecutive_complete_days", "required_logical_posts", "required_destinations"
        )
    }))
