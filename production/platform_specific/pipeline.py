#!/usr/bin/env python3
"""No-network production planner for sixty distinct single-platform videos.

This module does not synthesize, publish, change remote policy or manufacture
reviews. It validates evidence and prepares local rendering / release handoffs.
"""
from __future__ import annotations

import argparse
import collections
import copy
import datetime as dt
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

PROGRAM = "PLATFORM_SPECIFIC_FIFTEEN_DAILY"
LEGACY_PROGRAM = "PLATFORM_SPECIFIC_TEN_DAILY"
SCHEMA_VERSION = 2
DAILY_PER_PLATFORM = 15
VOICE = "el-GR-NestorasNeural"
CTA = "Αν σας άρεσε, ακολουθήστε για περισσότερα."
PLATFORMS = ("facebook", "instagram", "tiktok", "youtube")
LEGACY_SLOTS = ("07:00", "09:00", "10:00", "11:00", "13:00", "15:00", "17:00", "18:30", "20:00", "22:00")
ADDITIONAL_SLOTS = ("08:00", "12:00", "14:00", "16:00", "21:00")
SLOTS = tuple(sorted(LEGACY_SLOTS + ADDITIONAL_SLOTS))
DAILY_TOTAL = DAILY_PER_PLATFORM * len(PLATFORMS)
UTC = dt.timezone.utc
HISTORY_SOURCES = ("metricool", "notion", "repository", "production_lease")


class Blocked(ValueError):
    pass


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def script_hash(text: str) -> str:
    # Bind synthesis and review to the exact submitted UTF-8 script, not title.
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def story_hash(job: dict) -> str:
    body = {key: job.get(key) for key in ("story_id", "fingerprint", "title", "script", "caption", "sources", "kind")}
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def parse_time(value: str) -> dt.datetime:
    if not isinstance(value, str) or not value:
        raise Blocked("Evidence timestamp is missing")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise Blocked("Evidence timestamps must include a timezone")
    return parsed.astimezone(UTC)


def fresh(record: dict, now: dt.datetime, maximum_age_minutes: int) -> bool:
    try:
        observed = parse_time(record["checked_at"])
        expires = parse_time(record["expires_at"])
        return observed <= now < expires and now - observed <= dt.timedelta(minutes=maximum_age_minutes)
    except (KeyError, TypeError, ValueError):
        return False


def contains_error(value: object) -> bool:
    """An outer success label must never hide an API error inside a receipt."""
    if isinstance(value, dict):
        return any((key in ("error", "error_code", "error_message", "isError") and bool(item)) or
                   (key == "status" and item in ("ERROR", "FAILED", "INCOMPLETE", "RATE_LIMITED")) or
                   contains_error(item) for key, item in value.items())
    if isinstance(value, list):
        return any(contains_error(item) for item in value)
    return False


def asset_path(base: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or "://" in value:
        raise Blocked("A local asset path is required; fetching URLs is a separate authorized step")
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def verify_asset(base: Path, record: dict, path_key: str = "path", hash_key: str = "sha256") -> Path:
    try:
        path = asset_path(base, record[path_key])
        expected = record[hash_key]
    except (KeyError, TypeError) as exc:
        raise Blocked("Missing exact asset path/hash") from exc
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected)) or not path.is_file() or sha256(path) != expected:
        raise Blocked(f"Missing or changed exact asset: {path.name}")
    return path


def scaffold(day: str) -> dict:
    dt.date.fromisoformat(day)
    return {
        "schema_version": SCHEMA_VERSION, "program": PROGRAM, "brand_id": 7076410,
        "local_date": day, "timezone": "Europe/Athens", "counts_as_scheduled_queue": False,
        "jobs": [{"id": f"{day}-{platform}-{(LEGACY_SLOTS + ADDITIONAL_SLOTS).index(slot) + 1:02d}", "platform": platform,
                  "local_date": day, "slot_local": slot, "story_id": None,
                  "title": None, "fingerprint": None, "script": None, "caption": None,
                  "sources": [], "kind": None, "voice": VOICE,
                  "background_music": False, "avatar": False, "stage": "EMPTY_SLOT"}
                 for platform in PLATFORMS for slot in SLOTS]}


def migrate_ten_manifest(manifest: dict) -> dict:
    """Copy an explicit legacy layout; preserve dates, IDs, content and evidence.

    Only twenty empty editorial slots are added. This creates no live clearance,
    queue records or release approval and never moves a story to another date.
    """
    if manifest.get("program") != LEGACY_PROGRAM or manifest.get("schema_version") != 1:
        raise Blocked("EXPLICIT_LEGACY_TEN_MANIFEST_REQUIRED")
    jobs = manifest.get("jobs", [])
    if (not isinstance(jobs, list) or len(jobs) != 40 or any(not isinstance(job, dict) for job in jobs) or
            any(sorted(job.get("slot_local", "") for job in jobs if job.get("platform") == platform) != sorted(LEGACY_SLOTS)
                for platform in PLATFORMS)):
        raise Blocked("EXACT_LEGACY_TEN_SLOT_LAYOUT_REQUIRED")
    result = copy.deepcopy(manifest)
    additions = [job for job in scaffold(manifest["local_date"])["jobs"] if job["slot_local"] in ADDITIONAL_SLOTS]
    result.update(program=PROGRAM, schema_version=SCHEMA_VERSION, counts_as_scheduled_queue=False,
                  migration={"source_program": LEGACY_PROGRAM, "source_schema_version": 1,
                             "preserved_jobs": 40, "added_empty_slots": 20,
                             "creates_release_clearance": False})
    result["jobs"].extend(additions)
    result["jobs"].sort(key=lambda job: (PLATFORMS.index(job["platform"]), job["slot_local"]))
    errors = validate_manifest(result)
    if errors:
        raise Blocked("; ".join(errors))
    return result


def import_catalog(manifest: dict, catalog: list[dict]) -> dict:
    """Assign actual source packs only; duplicates stay errors, not new variants."""
    seen = {job.get("story_id") for job in manifest["jobs"] if job.get("story_id")}
    for source in catalog:
        platform = source.get("platform")
        if platform not in PLATFORMS:
            raise Blocked("Every source pack needs exactly one explicit platform")
        story_id = source.get("story_id") or source.get("id")
        if not story_id or story_id in seen:
            raise Blocked("Missing or repeated source story ID")
        dates = {source[key] for key in ("local_date", "date", "proposed_date") if source.get(key)}
        if len(dates) > 1:
            raise Blocked("Conflicting dates on source pack")
        if (next(iter(dates)) if dates else manifest["local_date"]) != manifest["local_date"]:
            continue
        slot = next((job for job in manifest["jobs"] if job["platform"] == platform and not job.get("story_id")), None)
        if slot is None:
            raise Blocked(f"No empty {platform} slot remains; {DAILY_PER_PLATFORM} is the daily maximum")
        for key in ("title", "fingerprint", "script", "caption", "sources", "kind", "hook", "scene_beats"):
            if key in source:
                slot[key] = source[key]
        slot["story_id"] = story_id
        if source.get("scene_plan") and not slot.get("scene_beats"):
            slot["scene_beats"] = source["scene_plan"]
        slot["stage"] = "SOURCE_PACK_IMPORTED_NOT_REVIEWED"
        slot["source_pack_id"] = source.get("id", story_id)
        seen.add(story_id)
    return manifest


def validate_manifest(manifest: dict) -> list[str]:
    errors = []
    if manifest.get("program") == LEGACY_PROGRAM:
        errors.append("LEGACY_TEN_MANIFEST_REQUIRES_EXPLICIT_MIGRATION")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("Current manifest schema version is required")
    if manifest.get("program") != PROGRAM or manifest.get("brand_id") != 7076410 or manifest.get("timezone") != "Europe/Athens":
        errors.append("Canonical program, brand and Athens timezone are required")
    try:
        dt.date.fromisoformat(manifest["local_date"])
    except (KeyError, TypeError, ValueError):
        errors.append("Invalid local_date")
    jobs = manifest.get("jobs", [])
    if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
        return errors + ["jobs must be a list of job objects"]
    if any(not isinstance(job.get("platform"), str) for job in jobs):
        return errors + ["Each job must have one platform string, never a list"]
    counts = collections.Counter(job.get("platform") for job in jobs)
    if len(jobs) != DAILY_TOTAL or counts != collections.Counter({platform: DAILY_PER_PLATFORM for platform in PLATFORMS}):
        errors.append(f"Exactly {DAILY_TOTAL} job slots, {DAILY_PER_PLATFORM} per platform, are required")
    seen = {key: {} for key in ("id", "story_id", "fingerprint", "title", "script", "audio_sha256", "final_sha256")}
    times = set()
    for job in jobs:
        jid = job.get("id", "MISSING_ID")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", str(jid)) or jid == "MISSING_ID":
            errors.append("Job IDs must be nonempty safe filename identifiers")
        if job.get("local_date") != manifest.get("local_date"):
            errors.append(f"{jid}: date differs from manifest")
        slot = job.get("slot_local", "")
        if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", slot):
            errors.append(f"{jid}: invalid local slot")
        pair = (job.get("platform"), slot)
        if pair in times:
            errors.append(f"{jid}: repeated platform/time slot")
        times.add(pair)
        if "providers" in job or "platforms" in job:
            errors.append(f"{jid}: broadcast routing fields are forbidden")
        if job.get("voice") != VOICE or job.get("background_music") is not False or job.get("avatar") is not False:
            errors.append(f"{jid}: exact Nestoras, no music and no avatar are mandatory")
        for key in seen:
            value = job.get("audio", {}).get("sha256") if key == "audio_sha256" else job.get("final", {}).get("sha256") if key == "final_sha256" else job.get(key)
            if value:
                identity = normalized(str(value))
                if identity in seen[key]:
                    errors.append(f"{jid}: duplicate {key} with {seen[key][identity]}")
                seen[key][identity] = jid
        script = job.get("script")
        if script and (not script.rstrip().endswith(CTA) or len(script) > 10000):
            errors.append(f"{jid}: full required CTA or safe text length missing")
    return errors


def source_errors(job: dict) -> list[str]:
    missing = [key for key in ("story_id", "title", "fingerprint", "script", "caption", "kind") if not job.get(key)]
    if missing:
        return ["SOURCE_PACK_MISSING:" + ",".join(missing)]
    result = []
    if job["kind"] not in ("fiction", "folklore", "documented", "science", "travel", "entertainment"):
        result.append("STORY_KIND_INVALID")
    if job["kind"] not in ("fiction", "entertainment") and not job.get("sources"):
        result.append("FACTUAL_SOURCES_MISSING")
    if not job["script"].rstrip().endswith(CTA):
        result.append("COMPLETE_SPOKEN_CTA_MISSING")
    if not job["caption"].rstrip() or len(re.findall(r"(?<!\w)#[\wΆ-ώ]+", job["caption"])) > 5:
        result.append("CAPTION_INVALID")
    review = job.get("source_review", {})
    if not (review.get("passed") is True and review.get("story_sha256") == story_hash(job) and review.get("reviewer")):
        result.append("SOURCE_REVIEW_REQUIRED")
    return result


def history_errors(job: dict, evidence: dict, now: dt.datetime) -> list[str]:
    if not fresh(evidence, now, 30) or evidence.get("complete") is not True or contains_error(evidence):
        return ["FRESH_HISTORY_REQUIRED"]
    sources = evidence.get("sources", {})
    if any(sources.get(name, {}).get("status") != "READ_SUCCEEDED" or
           sources.get(name, {}).get("complete") is not True for name in HISTORY_SOURCES):
        return ["ALL_FOUR_HISTORY_SOURCES_REQUIRED"]
    if not isinstance(evidence.get("stories"), list) or not evidence["stories"]:
        return ["EMPTY_HISTORY_IS_NOT_CLEARANCE"]
    if any(not isinstance(sources[name].get("rows_seen"), int) or sources[name]["rows_seen"] <= 0
           for name in ("metricool", "notion", "repository")):
        return ["HISTORY_READ_COUNTS_REQUIRED"]
    lease = sources.get("production_lease", {})
    if lease.get("conflicting_active_lease") is not False:
        return ["EXCLUSIVE_LEASE_REQUIRED"]
    result = []
    for previous in evidence.get("stories", []):
        # The candidate's own inactive row can only be exempted explicitly by
        # the reviewer; published or active records never receive an exemption.
        own_inactive = (previous.get("story_id") == job.get("story_id") and
                        previous.get("inactive") is True and
                        previous.get("candidate_row_only") is True and
                        previous.get("status") not in ("PUBLISHED", "SCHEDULED", "PENDING"))
        if own_inactive:
            continue
        checks = (("story_id", job.get("story_id")), ("fingerprint", job.get("fingerprint")),
                  ("script_sha256", script_hash(job.get("script") or "")))
        if any(value and normalized(str(previous.get(key, ""))) == normalized(str(value)) for key, value in checks):
            result.append("DUPLICATE_IN_LIVE_HISTORY")
            break
    semantic = evidence.get("semantic_reviews", {}).get(job.get("id"), {})
    if not (semantic.get("clear") is True and semantic.get("story_sha256") == story_hash(job) and semantic.get("reviewer")):
        result.append("SEMANTIC_DUPLICATE_REVIEW_REQUIRED")
    try:
        if not parse_time(evidence["checked_at"]) <= parse_time(semantic["checked_at"]) <= now:
            result.append("SEMANTIC_REVIEW_NOT_CURRENT")
    except (KeyError, TypeError, ValueError):
        result.append("SEMANTIC_REVIEW_NOT_CURRENT")
    return result


def production_errors(policy: dict, platform: str, action: str) -> list[str]:
    enabled = policy.get("production", {})
    errors = []
    if policy.get("program_label") != PROGRAM or policy.get("enabled") is not True:
        errors.append("CANONICAL_PROGRAM_DISABLED")
    targets = policy.get("targets", {})
    expected = {"per_platform_daily_video_target": DAILY_PER_PLATFORM, "daily_distinct_stories": DAILY_TOTAL,
                "daily_distinct_videos": DAILY_TOTAL, "daily_provider_destinations": DAILY_TOTAL}
    if (any(type(targets.get(key)) is not int or targets[key] != value for key, value in expected.items()) or
            any(policy.get("platforms", {}).get(name, {}).get("daily_video_target") != DAILY_PER_PLATFORM for name in PLATFORMS) or
            policy.get("scheduling", {}).get("proposed_local_slots") != list(SLOTS)):
        errors.append("CANONICAL_CADENCE_TARGETS_MISMATCH")
    if enabled.get("enabled") is not True or policy.get("platforms", {}).get(platform, {}).get("enabled") is not True:
        errors.append("PLATFORM_PRODUCTION_DISABLED")
    key = {"synthesize": "new_media_enabled", "render": "new_media_enabled", "release": "publication_enabled"}[action]
    if enabled.get(key) is not True:
        errors.append(f"{action.upper()}_DISABLED")
    return errors


def lease_errors(job: dict, history: dict, now: dt.datetime, action: str) -> list[str]:
    lease = history.get("sources", {}).get("production_lease", {})
    try:
        valid = (lease.get("owned_active_lease") is True and lease.get("owner") and
                 lease.get("brand_id") == 7076410 and lease.get("local_date") == job["local_date"] and
                 action in lease.get("authorized_actions", []) and
                 now < parse_time(lease["lease_expires_at"]))
    except (KeyError, ValueError, TypeError):
        valid = False
    return [] if valid else ["OWNED_ACTIVE_LEASE_FOR_ACTION_REQUIRED"]


def budget_errors(job: dict, evidence: dict, now: dt.datetime, reserved_characters: int = 0) -> list[str]:
    """Validate a reviewed live-account receipt; this is not an Azure query.

    Never infer F0 from environment names or derive free allowance from a public
    tariff. A real account receipt must supply provider-observed remaining units.
    """
    if not fresh(evidence, now, 15) or evidence.get("complete") is not True or contains_error(evidence):
        return ["FRESH_ACCOUNT_BUDGET_REQUIRED"]
    resource = evidence.get("resource_id", "")
    if not isinstance(resource, str) or not re.fullmatch(r"/subscriptions/[^/]+/resourceGroups/[^/]+/providers/Microsoft\.CognitiveServices/accounts/[^/]+", resource):
        return ["VERIFIED_AZURE_RESOURCE_REQUIRED"]
    errors = []
    if not (evidence.get("actual_sku") == "F0" and evidence.get("zero_cost_verified") is True and
            evidence.get("usage_complete_for_period") is True and evidence.get("reviewer") and
            evidence.get("source") == "azure_management_live_read" and evidence.get("evidence_sha256")):
        errors.append("ACTUAL_FREE_CAPACITY_UNVERIFIED")
    binding = evidence.get("credential_binding", {})
    if not (binding.get("private") is True and binding.get("verified_same_resource") is True and
            binding.get("resource_id") == resource and binding.get("region") and
            re.fullmatch(r"[0-9a-f]{64}", str(binding.get("key_sha256", "")))):
        errors.append("PRIVATE_RESOURCE_CREDENTIAL_BINDING_REQUIRED")
    if evidence.get("period") != now.strftime("%Y-%m") or evidence.get("voice") != VOICE:
        errors.append("BUDGET_PERIOD_OR_VOICE_MISMATCH")
    remaining = evidence.get("remaining_tts_characters")
    if not isinstance(remaining, int) or isinstance(remaining, bool) or remaining < 0:
        errors.append("REMAINING_TTS_ALLOWANCE_UNKNOWN")
    # Account receipt must state a conservative charge bound from its billing
    # meter. Raw text length alone does not cover provider SSML charging rules.
    charge = job.get("tts_charge_upper_bound")
    if not isinstance(charge, int) or isinstance(charge, bool) or charge < len(job.get("script") or ""):
        errors.append("VERIFIED_TTS_CHARGE_BOUND_REQUIRED")
    elif isinstance(remaining, int) and remaining - reserved_characters < charge:
        errors.append("INSUFFICIENT_FREE_TTS_CAPACITY")
    return errors


def queue_capacity_errors(job: dict, history: dict, now: dt.datetime) -> list[str]:
    snapshot = history.get("queue_snapshot", {})
    if (not fresh(snapshot, now, 5) or snapshot.get("status") != "READ_SUCCEEDED" or
            snapshot.get("complete") is not True or contains_error(snapshot)):
        return ["FRESH_COMPLETE_QUEUE_SNAPSHOT_REQUIRED"]
    if (snapshot.get("brand_id") != 7076410 or snapshot.get("timezone") != "Europe/Athens" or
            snapshot.get("local_date") != job["local_date"]):
        return ["QUEUE_BRAND_DATE_TIMEZONE_MISMATCH"]
    counts = snapshot.get("platforms", {}).get(job["platform"], {})
    published, pending = counts.get("published"), counts.get("active_pending")
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in (published, pending)):
        return ["EXPLICIT_PLATFORM_QUEUE_COUNTS_REQUIRED"]
    if published + pending >= DAILY_PER_PLATFORM:
        return ["DAILY_PLATFORM_CAP_REACHED"]
    return []


def audio_errors(job: dict, base: Path) -> list[str]:
    audio = job.get("audio", {})
    if not audio:
        return ["NESTORAS_AUDIO_MISSING"]
    try:
        verify_asset(base, audio)
        verify_asset(base, audio, "srt_path", "srt_sha256")
    except Blocked as exc:
        return [str(exc)]
    if audio.get("voice") != VOICE or audio.get("script_sha256") != script_hash(job.get("script") or ""):
        return ["AUDIO_VOICE_OR_SCRIPT_BINDING_MISMATCH"]
    if audio.get("background_music") is not False:
        return ["NO_MUSIC_PROVENANCE_REQUIRED"]
    return []


def scene_errors(job: dict, base: Path) -> list[str]:
    scenes = job.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 4:
        return ["REVIEWED_DISTINCT_SCENES_MISSING"]
    seen, errors = set(), []
    for number, scene in enumerate(scenes, 1):
        try:
            verify_asset(base, scene)
        except Blocked as exc:
            errors.append(f"SCENE_{number}:{exc}")
            continue
        if scene["sha256"] in seen:
            errors.append("REPEATED_SCENE_FORBIDDEN")
        seen.add(scene["sha256"])
        if not (scene.get("rights_verified") is True and scene.get("relevant_to_story") is True and
                scene.get("photographic") is True and scene.get("contains_child_face") is False and
                scene.get("contains_avatar") is False and scene.get("reviewer") and
                scene.get("story_sha256") == story_hash(job)):
            errors.append(f"SCENE_{number}:RIGHTS_CONTENT_REVIEW_REQUIRED")
    return errors


def probe_media(path: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise Blocked("Exact final file is not a readable media container")
    return json.loads(result.stdout)


def final_errors(job: dict, base: Path, now: dt.datetime | None = None) -> list[str]:
    now = now or dt.datetime.now(UTC)
    final = job.get("final", {})
    try:
        media = verify_asset(base, final)
        technical_path = verify_asset(base, final, "technical_path", "technical_sha256")
        review_path = verify_asset(base, final, "review_path", "review_sha256")
        technical, review = read_json(technical_path), read_json(review_path)
    except (Blocked, OSError, ValueError) as exc:
        return ["EXACT_FINAL_EVIDENCE_REQUIRED:" + str(exc)]
    digest = sha256(media)
    expected_binding = {"media_sha256": digest, "story_sha256": story_hash(job), "platform": job["platform"], "job_id": job["id"]}
    if any(record.get(key) != value for record in (technical, review) for key, value in expected_binding.items()):
        return ["FINAL_EVIDENCE_BINDING_MISMATCH"]
    required_technical = ("full_decode_passed", "subtitle_text_verified", "technical_passed")
    required_review = ("actual_audio_listened", "complete_audio_review_passed", "nestoras_voice_confirmed", "visual_review_passed",
                       "all_scenes_reviewed", "all_subtitle_cues_reviewed", "pronunciation_passed",
                       "subtitle_sync_passed", "opening_reviewed", "complete_cta_reviewed", "passed_final_review")
    if any(technical.get(key) is not True for key in required_technical):
        return ["TECHNICAL_REVIEW_REQUIRED"]
    technical_format = {"width": 1080, "height": 1920, "fps": 30, "video_codec": "h264", "pixel_format": "yuv420p",
                        "audio_codec": "aac", "audio_rate": 48000, "audio_channels": 1, "voice": VOICE,
                        "background_music": False, "avatar": False, "audio_stretched": False, "audio_padded": False}
    duration = technical.get("duration_seconds")
    if (any(technical.get(key) != value for key, value in technical_format.items()) or
            not isinstance(duration, (int, float)) or not 80 <= duration <= 110):
        return ["FINAL_TECHNICAL_FORMAT_MISMATCH"]
    try:
        actual = probe_media(media)
        videos = [stream for stream in actual["streams"] if stream["codec_type"] == "video"]
        sounds = [stream for stream in actual["streams"] if stream["codec_type"] == "audio"]
        actual_duration = float(actual["format"]["duration"])
        if not (len(videos) == len(sounds) == 1 and videos[0]["width"] == 1080 and videos[0]["height"] == 1920 and
                videos[0]["codec_name"] == "h264" and videos[0]["pix_fmt"] == "yuv420p" and videos[0]["r_frame_rate"] == "30/1" and
                sounds[0]["codec_name"] == "aac" and sounds[0]["sample_rate"] == "48000" and sounds[0]["channels"] == 1 and
                80 <= actual_duration <= 110 and abs(actual_duration - duration) <= .034):
            return ["EXACT_FINAL_PROBE_MISMATCH"]
    except (Blocked, OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        return ["EXACT_FINAL_PROBE_FAILED"]
    if any(review.get(key) is not True for key in required_review) or not review.get("reviewer"):
        return ["ACTUAL_EXACT_FINAL_AUDIO_AND_VISUAL_REVIEW_REQUIRED"]
    try:
        created_at, reviewed_at = parse_time(technical["created_at"]), parse_time(review["reviewed_at"])
        if created_at > now or reviewed_at > now:
            return ["FINAL_EVIDENCE_TIMESTAMP_IN_FUTURE"]
        if reviewed_at < created_at:
            return ["FINAL_REVIEW_PREDATES_RENDER"]
    except (KeyError, TypeError, ValueError):
        return ["FINAL_REVIEW_TIMESTAMP_REQUIRED"]
    return []


def inspect_job(job: dict, base: Path, policy: dict, history: dict, budget: dict,
                now: dt.datetime, reserved: int = 0) -> dict:
    source = source_errors(job)
    result = {"job_id": job["id"], "story_id": job.get("story_id"), "platform": job["platform"],
              "title": job.get("title"), "state": "EMPTY_SLOT", "blockers": [],
              "counts_as_ready_media": False, "counts_as_scheduled_queue": False,
              "new_provider_calls": 0}
    if not job.get("script"):
        result["blockers"] = source
        return result
    result["state"] = "SOURCE_PACK_READY_REVIEW_PENDING"
    history_issues = history_errors(job, history, now)
    audio = audio_errors(job, base)
    scenes = scene_errors(job, base)
    result["blockers"] = source + history_issues
    result["next_action"] = "synthesize_existing_script" if audio else "prepare_scenes" if scenes else "render_local"
    if audio:
        result["blockers"] += (audio + production_errors(policy, job["platform"], "synthesize") +
                               lease_errors(job, history, now, "synthesize") + budget_errors(job, budget, now, reserved))
    elif scenes:
        result["state"] = "AUDIO_READY_SCENES_PENDING"
        result["blockers"] += scenes
    elif not job.get("final"):
        result["state"] = "LOCAL_RENDER_INPUTS_PRESENT"
        result["blockers"] += production_errors(policy, job["platform"], "render") + lease_errors(job, history, now, "render")
    else:
        result["state"] = "MEDIA_READY_REVIEW_PENDING"
        finals = final_errors(job, base, now)
        result["blockers"] += finals
        if not finals and not source and not history_issues:
            result["state"] = "PASSED_FINAL_REVIEW"
            result["counts_as_ready_media"] = True
            result["next_action"] = "release_preflight"
    result["blockers"] = sorted(set(result["blockers"]))
    return result


def plan(manifest: dict, base: Path, policy: dict, history: dict, budget: dict, now: dt.datetime) -> dict:
    validation = validate_manifest(manifest)
    jobs, reserved = [], 0
    for job in ([] if validation else manifest.get("jobs", [])):
        record = inspect_job(job, base, policy, history, budget, now, reserved)
        jobs.append(record)
        # Reserve cumulatively even when a later preflight must still block.
        # This prevents a dry run from promising the same allowance sixty times.
        if job.get("script") and not job.get("audio") and not budget_errors(job, budget, now, reserved):
            reserved += job["tts_charge_upper_bound"]
    return {"program": PROGRAM, "local_date": manifest.get("local_date"), "generated_at": now.isoformat(),
            "mode": "NO_NETWORK_DRY_RUN", "manifest_errors": validation,
            "new_synthesis_calls": 0, "new_publication_calls": 0,
            "real_scheduled_queue_count": 0, "scheduled_status_not_inferred_from_manifest": True,
            "daily_complete": False, "reserved_tts_characters_in_plan_only": reserved,
            "per_platform": {p: {"slots": sum(j["platform"] == p for j in jobs),
                                  "source_packs": sum(j["platform"] == p and j["state"] != "EMPTY_SLOT" for j in jobs),
                                  "exact_final_ready": sum(j["platform"] == p and j["counts_as_ready_media"] for j in jobs)} for p in PLATFORMS},
            "jobs": jobs}


def render_preflight(job: dict, base: Path, policy: dict, history: dict, now: dt.datetime) -> None:
    errors = (production_errors(policy, job["platform"], "render") + source_errors(job) +
              history_errors(job, history, now) + lease_errors(job, history, now, "render") +
              audio_errors(job, base) + scene_errors(job, base))
    if errors:
        raise Blocked("; ".join(sorted(set(errors))))


def release_preflight(job: dict, base: Path, policy: dict, history: dict, now: dt.datetime) -> dict:
    errors = (production_errors(policy, job["platform"], "release") + source_errors(job) +
              history_errors(job, history, now) + lease_errors(job, history, now, "release") +
              final_errors(job, base, now) + queue_capacity_errors(job, history, now))
    if policy.get("production", {}).get("scheduling_enabled") is not True:
        errors.append("SCHEDULING_DISABLED")
    # Connected networks are inventory, never permission to publish. Require
    # the canonical schedule and explicit target allowlist on every release,
    # even when an operator has enabled the other production flags.
    if policy.get("active_schedule") is not True or policy.get("scheduling", {}).get("enabled") is not True:
        errors.append("ACTIVE_SCHEDULE_DISABLED")
    allowed = policy.get("routing", {}).get("active_publish_providers")
    if (not isinstance(allowed, list) or
            any(not isinstance(provider, str) or provider not in PLATFORMS for provider in allowed) or
            len(allowed) != len(set(allowed))):
        errors.append("PUBLISH_PROVIDER_ALLOWLIST_INVALID")
    elif job["platform"] not in allowed:
        errors.append("PLATFORM_NOT_IN_PUBLISH_ALLOWLIST")
    disclosure = job.get("native_ai_disclosure", {})
    if disclosure.get("platform") != job["platform"] or disclosure.get("verified") is not True or not disclosure.get("evidence"):
        errors.append("SUPPORTED_NATIVE_AI_DISCLOSURE_REQUIRED")
    scheduled = dt.datetime.fromisoformat(f"{job['local_date']}T{job['slot_local']}:00").replace(tzinfo=ZoneInfo("Europe/Athens"))
    if scheduled <= now:
        errors.append("FUTURE_TIME_REQUIRED_NO_BACKDATING")
    if errors:
        raise Blocked("; ".join(sorted(set(errors))))
    identity = f"{PROGRAM}|{job['local_date']}|{job['story_id']}|{job['platform']}|{job['final']['sha256']}"
    return {"job_id": job["id"], "story_id": job["story_id"], "platform": job["platform"],
            "brand_id": 7076410, "program": PROGRAM, "scheduled_at": scheduled.isoformat(),
            "media_path": str(verify_asset(base, job["final"])), "media_sha256": job["final"]["sha256"],
            "caption": job["caption"], "native_ai_disclosure": disclosure,
            "idempotency_key": hashlib.sha256(identity.encode()).hexdigest(), "history_expires_at": history["expires_at"],
            "status": "RELEASE_HANDOFF_ONLY_NOT_SCHEDULED", "requires_live_write_readback": True,
            "refresh_all_history_after_this_write": True, "native_write_transport_verified_here": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("scaffold")
    create.add_argument("--date", required=True)
    create.add_argument("--output", type=Path, required=True)
    ingest = sub.add_parser("import-catalog")
    ingest.add_argument("--manifest", type=Path, required=True)
    ingest.add_argument("--catalog", type=Path, required=True)
    ingest.add_argument("--output", type=Path, required=True)
    migrate = sub.add_parser("migrate-ten-manifest")
    migrate.add_argument("--manifest", type=Path, required=True)
    migrate.add_argument("--output", type=Path, required=True)
    dry = sub.add_parser("plan")
    dry.add_argument("--manifest", type=Path, required=True)
    dry.add_argument("--policy", type=Path, required=True)
    dry.add_argument("--history", type=Path)
    dry.add_argument("--budget", type=Path)
    dry.add_argument("--output", type=Path, required=True)
    release = sub.add_parser("export-release")
    for key in ("manifest", "policy", "history", "output"):
        release.add_argument("--" + key, type=Path, required=True)
    release.add_argument("--job-id", required=True)
    args = parser.parse_args()
    try:
        if args.command == "scaffold":
            write_json(args.output, scaffold(args.date))
        elif args.command == "migrate-ten-manifest":
            if (args.output.resolve() == args.manifest.resolve() or args.output.exists() or
                    args.output.parent.resolve() != args.manifest.parent.resolve()):
                raise Blocked("MIGRATION_REQUIRES_NEW_SIBLING_FILE_PRESERVING_ASSET_BASE")
            write_json(args.output, migrate_ten_manifest(read_json(args.manifest)))
        elif args.command == "import-catalog":
            source = read_json(args.catalog)
            entries = source if isinstance(source, list) else source.get("jobs", source.get("stories"))
            if not isinstance(entries, list):
                raise Blocked("Catalog must be a list or contain jobs/stories")
            result = import_catalog(read_json(args.manifest), entries)
            errors = validate_manifest(result)
            if errors:
                raise Blocked("; ".join(errors))
            write_json(args.output, result)
        elif args.command == "export-release":
            manifest = read_json(args.manifest)
            errors = validate_manifest(manifest)
            if errors:
                raise Blocked("; ".join(errors))
            job = next((job for job in manifest["jobs"] if job["id"] == args.job_id), None)
            if job is None:
                raise Blocked("Unknown job ID")
            result = release_preflight(job, args.manifest.parent, read_json(args.policy), read_json(args.history), dt.datetime.now(UTC))
            write_json(args.output, result)
        else:
            result = plan(read_json(args.manifest), args.manifest.parent, read_json(args.policy),
                          read_json(args.history) if args.history else {}, read_json(args.budget) if args.budget else {},
                          dt.datetime.now(UTC))
            write_json(args.output, result)
            print(json.dumps({key: value for key, value in result.items() if key != "jobs"}, ensure_ascii=False))
            return 2 if result["manifest_errors"] else 0
    except (Blocked, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "new_provider_calls": 0}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
