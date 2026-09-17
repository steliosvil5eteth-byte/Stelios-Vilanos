from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ALLOWED_NETWORKS = {"facebook", "instagram", "tiktok", "youtube"}
ALLOWED_STATUS = {"pending", "processing", "scheduled", "published", "failed"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_queue(path: Path) -> None:
    data = load_json(path)
    if data.get("version") != 1:
        raise ValueError("queue version must be 1")
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("jobs must be a list")

    seen_ids: set[str] = set()
    for index, job in enumerate(jobs, start=1):
        if not isinstance(job, dict):
            raise ValueError(f"job #{index} must be an object")
        job_id = str(job.get("id", "")).strip()
        if not job_id:
            raise ValueError(f"job #{index} is missing id")
        if job_id in seen_ids:
            raise ValueError(f"duplicate job id: {job_id}")
        seen_ids.add(job_id)

        status = job.get("status", "pending")
        if status not in ALLOWED_STATUS:
            raise ValueError(f"job {job_id}: invalid status {status}")

        title = str(job.get("title", "")).strip()
        if not title:
            raise ValueError(f"job {job_id}: title is required")

        networks = job.get("networks")
        if not isinstance(networks, list) or not networks:
            raise ValueError(f"job {job_id}: networks must be a non-empty list")
        invalid = set(networks) - ALLOWED_NETWORKS
        if invalid:
            raise ValueError(f"job {job_id}: invalid networks {sorted(invalid)}")

        schedule = str(job.get("scheduled_at", "")).strip()
        if not schedule:
            raise ValueError(f"job {job_id}: scheduled_at is required")

        media = job.get("media")
        generator = job.get("generator")
        if not media and not generator:
            raise ValueError(f"job {job_id}: provide either media or generator")


def main() -> None:
    for path in [Path("queue/pending.json"), Path("queue/completed.json")]:
        validate_queue(path)
        print(f"OK: {path}")


if __name__ == "__main__":
    main()
