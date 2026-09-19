from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ALLOWED_NETWORKS = {"facebook", "instagram", "tiktok", "youtube"}
ALLOWED_STATUS = {
    "pending",
    "processing",
    "heygen_processing",
    "generating",
    "needs_review",
    "scheduled",
    "scheduled_tiktok_photo_video_cancelled",
    "cancelled_non_dog_video",
    "partially_published",
    "published",
    "failed",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def first_present(job: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = job.get(key)
        if value not in (None, "", []):
            return value
    return None


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

        job_id = str(first_present(job, "id", "job_id") or "").strip()
        if not job_id:
            raise ValueError(f"job #{index} is missing id/job_id")
        if job_id in seen_ids:
            raise ValueError(f"duplicate job id: {job_id}")
        seen_ids.add(job_id)

        status = str(job.get("status", "pending")).strip()
        if status not in ALLOWED_STATUS:
            raise ValueError(f"job {job_id}: invalid status {status}")

        title = str(job.get("title", "")).strip()
        if not title:
            raise ValueError(f"job {job_id}: title is required")

        networks = first_present(job, "networks", "platforms")
        # A terminal cancelled archive entry intentionally has no destinations.
        # Keep the non-empty requirement for every active/pending queue entry.
        terminal_cancelled_archive = (
            path.name == "completed.json"
            and status == "cancelled_non_dog_video"
            and job.get("terminal") is True
            and (job.get("networks") == [] or job.get("platforms") == [])
        )
        if networks is None and terminal_cancelled_archive:
            networks = []
        if not isinstance(networks, list) or (
            not networks and not terminal_cancelled_archive
        ):
            raise ValueError(f"job {job_id}: networks/platforms must be a non-empty list")
        invalid = set(networks) - ALLOWED_NETWORKS
        if invalid:
            raise ValueError(f"job {job_id}: invalid networks/platforms {sorted(invalid)}")

        schedule = str(first_present(job, "scheduled_at", "scheduled_time") or "").strip()
        if not schedule:
            raise ValueError(f"job {job_id}: scheduled_at/scheduled_time is required")

        media = first_present(job, "media", "media_url")
        generator = first_present(job, "generator", "heygen_video_id")
        if not media and not generator:
            raise ValueError(
                f"job {job_id}: provide media/media_url or generator/heygen_video_id"
            )


def main() -> None:
    for path in [Path("queue/pending.json"), Path("queue/completed.json")]:
        validate_queue(path)
        print(f"OK: {path}")


if __name__ == "__main__":
    main()
