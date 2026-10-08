#!/usr/bin/env python3
"""Create isolated YouTube narration through the established Azure F0 path.

This tool never schedules, publishes, purchases, upgrades, approves final media,
or substitutes voices. Azure's Speech SDK does not expose the account's billing
SKU: the established resource must remain F0. No paid fallback is implemented.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import date, time
from pathlib import Path

PROGRAM = "YOUTUBE_GROWTH_TEN_DAILY"
VOICE = "el-GR-NestorasNeural"
CTA = "Αν σας άρεσε, ακολουθήστε για περισσότερα."
MIN_SECONDS = 80.0
TARGET_MAX_SECONDS = 110.0
HARD_MAX_SECONDS = 150.0
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9_-]{2,99}\Z")
AUDIO_FILES = ("nestoras.wav", "boundaries.json", "subs.srt", "script.txt")


class PolicyError(RuntimeError):
    pass


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def write_json(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def normalized_script(script: str) -> str:
    return " ".join(unicodedata.normalize("NFC", script).casefold().split())


def validate_manifest(data: dict, selected_ids: list[str]) -> list[dict]:
    required = {
        "program": PROGRAM, "brand_id": 7076410, "timezone": "Europe/Athens",
        "voice": VOICE, "azure_tier_required": "F0",
        "paid_generation_allowed": False,
    }
    for key, expected in required.items():
        if data.get(key) != expected or (
            expected is False and data.get(key) is not False
        ):
            raise PolicyError(f"Manifest policy mismatch: {key}")
    if not isinstance(data.get("batch_id"), str) or not SAFE_ID.fullmatch(data["batch_id"]):
        raise PolicyError("batch_id must be a stable safe identifier")
    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= 25:
        raise PolicyError("Expected 1 to 25 explicit new YouTube jobs")
    limits = data.get("daily_new_video_limits")
    if not isinstance(limits, dict):
        raise PolicyError("Explicit daily_new_video_limits are required")
    counts: Counter[str] = Counter()
    identifiers, story_hashes, slots = set(), set(), set()
    for job in jobs:
        if not isinstance(job, dict):
            raise PolicyError("Every job must be an object")
        job_id = job.get("id")
        if not isinstance(job_id, str) or not SAFE_ID.fullmatch(job_id):
            raise PolicyError("Each job requires a safe stable id")
        if job_id in identifiers:
            raise PolicyError(f"Duplicate job id: {job_id}")
        identifiers.add(job_id)
        day, slot = job.get("local_date"), job.get("slot")
        try:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError()
            parsed_time = time.fromisoformat(slot)
            if parsed_time.tzinfo or parsed_time.strftime("%H:%M") != slot:
                raise ValueError()
        except (TypeError, ValueError):
            raise PolicyError(f"Invalid Europe/Athens date or slot for {job_id}") from None
        if (day, slot) in slots:
            raise PolicyError(f"Duplicate YouTube date/slot: {day} {slot}")
        slots.add((day, slot))
        counts[day] += 1
        script = job.get("script")
        if (
            not isinstance(script, str)
            or script != script.strip()
            or not script.endswith(CTA)
            or script.count(CTA) != 1
            or len(script) > 10000
        ):
            raise PolicyError(f"Missing complete script, exact CTA, or safe length: {job_id}")
        if digest_bytes(script.encode("utf-8")) != job.get("script_sha256"):
            raise PolicyError(f"Script hash mismatch: {job_id}")
        normalized_hash = digest_bytes(normalized_script(script).encode("utf-8"))
        if normalized_hash in story_hashes:
            raise PolicyError(f"Repeated narration inside batch: {job_id}")
        story_hashes.add(normalized_hash)
        if job.get("voice", VOICE) != VOICE:
            raise PolicyError(f"Voice substitution forbidden: {job_id}")
        if job.get("background_music", False) is not False:
            raise PolicyError(f"Added music forbidden: {job_id}")
        if job.get("avatar", False) is not False:
            raise PolicyError(f"Avatar forbidden: {job_id}")
        if job.get("providers", ["youtube"]) != ["youtube"]:
            raise PolicyError(f"This isolated batch supports only YouTube: {job_id}")
    for day, count in counts.items():
        limit = limits.get(day)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 10:
            raise PolicyError(f"Missing valid remaining new-video limit for {day}")
        if count > limit:
            raise PolicyError(f"New-video count exceeds declared remaining limit for {day}")
    if len(selected_ids) != len(set(selected_ids)):
        raise PolicyError("Repeated selected job id")
    if not set(selected_ids) <= identifiers:
        raise PolicyError("Selected job ids are absent from the validated manifest")
    return [job for job in jobs if not selected_ids or job["id"] in selected_ids]


def execution_blockers(batch: dict, jobs: list[dict]) -> list[str]:
    """Keep read-only validation separate from permission to invoke the provider."""
    blockers = []
    if batch.get("automatic_execution_authorized") is not True:
        blockers.append("EXPLICIT_EXECUTION_AUTHORIZATION_REQUIRED")
    for scope, item in [("batch", batch), *[(job["id"], job) for job in jobs]]:
        for field in ("production_status", "release_status"):
            status = item.get(field)
            if isinstance(status, str) and "BLOCKED" in status.upper():
                blockers.append(f"{scope}.{field}")
    return blockers


def verified_cached_audio(root: Path, job: dict, batch_id: str) -> dict | None:
    if not root.exists() or not any(root.iterdir()):
        return None
    meta_path = root / "speech-meta.json"
    if not meta_path.is_file():
        raise PolicyError("BLOCKED_PARTIAL_OUTPUT: existing audio needs explicit reconciliation")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta["id"] != job["id"] or meta["batch_id"] != batch_id
            or meta["program"] != PROGRAM or meta["voice"] != VOICE
            or meta["script_sha256"] != job["script_sha256"]
            or meta.get("azure_tier_required") != "F0"
        ):
            raise ValueError()
        if not MIN_SECONDS <= float(meta["duration_seconds"]) <= HARD_MAX_SECONDS:
            raise ValueError()
        for filename in AUDIO_FILES:
            if digest(root / filename) != meta["file_sha256"][filename]:
                raise ValueError()
        if (root / "script.txt").read_text(encoding="utf-8") != job["script"] + "\n":
            raise ValueError()
    except (KeyError, ValueError, TypeError, OSError):
        raise PolicyError("BLOCKED_CACHE_MISMATCH: do not synthesize over existing output") from None
    return meta


def safe_failure_category(exc: Exception) -> str:
    # Inspect error text only for classification. Never echo SDK details,
    # environment variables, endpoints, credentials, or complete exception text.
    message = str(exc).lower()
    if any(x in message for x in ("429", "quota", "too many", "throttl")):
        return "AZURE_QUOTA_OR_RATE_LIMIT"
    if any(x in message for x in ("401", "403", "auth", "subscription", "forbidden")):
        return "AZURE_AUTH_OR_RESOURCE_POLICY"
    if "duration gate" in message:
        return "NARRATION_DURATION_OUT_OF_BOUNDS"
    if isinstance(exc, PolicyError):
        return "LOCAL_POLICY_OR_EXISTING_OUTPUT_CONFLICT"
    return "AUDIO_GENERATION_OR_DEPENDENCY_ERROR"


def create_audio(renderer, root: Path, job: dict, batch: dict) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    (root / "script.txt").write_text(job["script"] + "\n", encoding="utf-8")
    if "caption" in job:
        (root / "caption.txt").write_text(str(job["caption"]) + "\n", encoding="utf-8")
    wav, boundaries, seconds = renderer.synthesize(
        job["script"], root, MIN_SECONDS, HARD_MAX_SECONDS
    )
    if wav.resolve() != (root / "nestoras.wav").resolve():
        raise PolicyError("Unexpected narration output path")
    if not MIN_SECONDS <= seconds <= HARD_MAX_SECONDS:
        raise PolicyError("Narration duration is outside hard bounds")
    if len(boundaries) < 30:
        raise PolicyError("Insufficient true word-boundary timing evidence")
    offsets = [float(item["offset"]) for item in boundaries]
    if offsets != sorted(offsets) or min(offsets) < 0 or max(offsets) > seconds + 0.25:
        raise PolicyError("Invalid or unordered speech word timings")
    srt = root / "subs.srt"
    cues = renderer.subtitles(boundaries, seconds, srt)
    if cues < 1 or not srt.is_file() or not srt.stat().st_size:
        raise PolicyError("No complete synchronized subtitle artifact")
    write_json(root / "boundaries.json", boundaries)
    target_met = MIN_SECONDS <= seconds <= TARGET_MAX_SECONDS
    meta = {
        "id": job["id"], "program": PROGRAM, "batch_id": batch["batch_id"],
        "brand_id": 7076410, "local_date": job["local_date"], "slot": job["slot"],
        "voice": VOICE, "provider": "azure_speech_f0", "azure_tier_required": "F0",
        "resource_sku_verified_by_this_script": False,
        "duration_seconds": seconds, "duration_target_seconds": [MIN_SECONDS, TARGET_MAX_SECONDS],
        "hard_max_duration_seconds": HARD_MAX_SECONDS, "duration_target_met": target_met,
        "script_sha256": job["script_sha256"],
        "audio_sha256": digest(wav), "srt_sha256": digest(srt),
        "file_sha256": {filename: digest(root / filename) for filename in AUDIO_FILES},
        "word_boundaries": len(boundaries), "subtitle_cues": cues,
        "background_music": False, "avatar": False, "filler_padding": False,
        "paid_fallback_used": False, "automatic_retry_performed": False,
        "technical_audio_passed": target_met, "publish_ready": False,
        "release_gate": (
            "PENDING_ASR_AND_EXACT_FINAL_MEDIA_REVIEW"
            if target_met else "BLOCKED_DURATION_TARGET_REVIEW"
        ),
    }
    write_json(root / "speech-meta.json", meta)
    return meta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--job-id", action="append", default=[])
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        raw = args.manifest.read_bytes()
        batch = json.loads(raw)
        jobs = validate_manifest(batch, args.job_id)
        blockers = execution_blockers(batch, jobs)
        if args.validate_only:
            print(json.dumps({
                "manifest_valid": True, "program": PROGRAM,
                "batch_id": batch["batch_id"], "selected_jobs": len(jobs),
                "manifest_sha256": digest_bytes(raw), "tts_calls": 0,
                "execution_authorized": not blockers, "execution_blockers": blockers,
            }))
            return 0
        if blockers:
            print(json.dumps({
                "failure_category": "EXECUTION_NOT_AUTHORIZED",
                "execution_authorized": False, "execution_blockers": blockers,
                "tts_calls": 0, "tts_execution_complete": False,
                "publish_ready": False, "automatic_retry_performed": False,
            }), file=sys.stderr)
            return 1
        if args.output is None:
            raise PolicyError("--output is required for synthesis")
        renderer = importlib.import_module("render_azure_feature_batch")
        if renderer.VOICE != VOICE or renderer.CTA != CTA:
            raise PolicyError("Established renderer voice or CTA policy differs")
        args.output.mkdir(parents=True, exist_ok=True)
        results = []
        state = {
            "program": PROGRAM, "batch_id": batch["batch_id"],
            "manifest_sha256": digest_bytes(raw), "selected_job_ids": [job["id"] for job in jobs],
            "publish_ready": False, "final_review": "NOT_PERFORMED",
            "tts_execution_complete": False, "jobs": results,
        }
        write_json(args.output / "batch-summary.json", state)
        for job in jobs:
            try:
                root = args.output / job["id"]
                meta = verified_cached_audio(root, job, batch["batch_id"])
                reused = meta is not None
                if meta is None:
                    meta = create_audio(renderer, root, job, batch)
                result = {
                    key: meta[key] for key in (
                        "id", "duration_seconds", "audio_sha256",
                        "subtitle_cues", "duration_target_met", "release_gate",
                    )
                }
                result["reused_hash_verified_audio"] = reused
                results.append(result)
                write_json(args.output / "batch-summary.json", state)
                print(json.dumps(result, ensure_ascii=False), flush=True)
            except Exception as exc:
                state["stopped_job_id"] = job["id"]
                state["failure_category"] = safe_failure_category(exc)
                state["remaining_unattempted_ids"] = [
                    entry["id"] for entry in jobs[jobs.index(job) + 1:]
                ]
                state["automatic_retry_performed"] = False
                write_json(args.output / "batch-summary.json", state)
                print(json.dumps({
                    "stopped_job_id": job["id"], "failure_category": state["failure_category"],
                    "automatic_retry_performed": False, "publish_ready": False,
                }), file=sys.stderr, flush=True)
                return 1
        state["tts_execution_complete"] = True
        state["all_duration_targets_met"] = all(item["duration_target_met"] for item in results)
        write_json(args.output / "batch-summary.json", state)
        return 0 if state["all_duration_targets_met"] else 2
    except Exception as exc:
        print(json.dumps({
            "failure_category": safe_failure_category(exc),
            "tts_execution_complete": False, "publish_ready": False,
            "automatic_retry_performed": False,
        }), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
