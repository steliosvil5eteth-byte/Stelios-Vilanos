"""Draft concept guard: checks 10 distinct content slots, never publishes."""
from daily_planner import build

def validate_concepts(day, concepts):
    plan = build(day)
    errors = []
    if not isinstance(concepts, list) or len(concepts) != 10:
        return {"status": "BLOCKED", "errors": ["Exactly 10 concepts required"]}
    for field in ("title", "opening", "ending", "plot_key"):
        values = [str(x.get(field, "")).strip().casefold() for x in concepts if isinstance(x, dict)]
        if len(values) != 10 or any(not x for x in values) or len(set(values)) != 10:
            errors.append(f"Missing or repeated {field}")
    return {"status": "DRAFT_READY" if not errors else "BLOCKED",
            "errors": errors, "publishing_enabled": False,
            "slots": [x["category"] for x in plan["items"]]}
