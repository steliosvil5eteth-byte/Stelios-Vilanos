from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_plan(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_plan(plan: dict[str, Any]) -> None:
    required = ["mode", "timezone", "platforms", "posts"]
    missing = [key for key in required if key not in plan]
    if missing:
        raise ValueError(f"Missing required keys: {', '.join(missing)}")

    if plan["mode"] not in {"dry-run", "live"}:
        raise ValueError("mode must be 'dry-run' or 'live'")

    if not isinstance(plan["platforms"], list) or not plan["platforms"]:
        raise ValueError("platforms must be a non-empty list")

    if not isinstance(plan["posts"], list):
        raise ValueError("posts must be a list")

    for index, post in enumerate(plan["posts"], start=1):
        for key in ["title", "caption", "media_path", "scheduled_at"]:
            if not post.get(key):
                raise ValueError(f"Post #{index} is missing '{key}'")


def run_dry_run(plan: dict[str, Any]) -> None:
    print("SOCIAL MEDIA AUTOMATION — DRY RUN")
    print(f"Timezone: {plan['timezone']}")
    print(f"Platforms: {', '.join(plan['platforms'])}")
    print(f"Posts: {len(plan['posts'])}\n")

    for i, post in enumerate(plan["posts"], start=1):
        hashtags = " ".join(f"#{tag.lstrip('#')}" for tag in post.get("hashtags", []))
        print(f"[{i}] {post['title']}")
        print(f"Schedule: {post['scheduled_at']}")
        print(f"Media: {post['media_path']}")
        print(f"Caption: {post['caption']}")
        print(f"Hashtags: {hashtags}")
        print("Action: SKIPPED (dry-run)\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Social media automation pipeline")
    parser.add_argument(
        "--plan",
        default="config/content_plan.example.json",
        help="Path to a content-plan JSON file",
    )
    args = parser.parse_args()

    plan_path = Path(args.plan)
    plan = load_plan(plan_path)
    validate_plan(plan)

    # Safety lock: live publishing is intentionally not implemented yet.
    if plan["mode"] == "live":
        raise RuntimeError(
            "Live publishing is locked until provider credentials and explicit adapters are configured."
        )

    run_dry_run(plan)


if __name__ == "__main__":
    main()
