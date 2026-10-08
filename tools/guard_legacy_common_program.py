#!/usr/bin/env python3
"""Local policy interlock for archived CURRENT_TEN_DAILY media entrypoints.

This only checks whether the legacy program is retired/disabled. Passing this
check would not prove Azure F0, available quota, zero cost, deduplication, final
QA or publication authorization. It never imports a provider SDK or calls one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

POLICY_PATH = Path("config/platform_growth_strategy.json")
NEW_PROGRAM = "PLATFORM_SPECIFIC_TEN_DAILY"


def block_reason(policy: object) -> str | None:
    if not isinstance(policy, dict):
        return "BLOCKED: platform growth policy must be a JSON object"
    # The new program supersedes common production independently of activation.
    # In particular, setting enabled=true for forty unique videos must NEVER
    # re-enable ten shared stories or their historical YouTube adaptations.
    if policy.get("program_label") == NEW_PROGRAM:
        return "SUPERSEDED: CURRENT_TEN_DAILY cannot execute under PLATFORM_SPECIFIC_TEN_DAILY"
    legacy = policy.get("legacy_common_program")
    if not isinstance(legacy, dict):
        return "BLOCKED: legacy common program authorization is missing"
    if legacy.get("enabled") is not True or legacy.get("status") != "ACTIVE":
        return "SUPERSEDED: legacy common production is disabled or retired"
    production = policy.get("production")
    if policy.get("enabled") is not True or not isinstance(production, dict) or production.get("enabled") is not True:
        return "BLOCKED: global media production is disabled"
    if policy.get("program_label") != "CURRENT_TEN_DAILY":
        return "BLOCKED: policy does not explicitly authorize the legacy common program"
    return None


def require_legacy_common_program(repo_root: Path) -> None:
    """Fail before dependency imports, output creation, rendering or provider use."""
    try:
        policy = json.loads((repo_root / POLICY_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit("BLOCKED: readable valid platform growth policy is required; no media work started") from exc
    reason = block_reason(policy)
    if reason:
        raise SystemExit(reason + "; no media work started")


def main() -> int:
    require_legacy_common_program(Path(__file__).resolve().parents[1])
    print("Legacy program retirement check passed; provider/cost/QA authorization is NOT established")
    return 0


if __name__ == "__main__":
    sys.exit(main())
