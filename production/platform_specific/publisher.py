"""Schedule exactly one reviewed video and verify its immediate live readback.

No scheduler, credentials discovery, synthesis, retry, or policy activation.
Use one verified durable journal and exclusive lease across every executor.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
import datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Callable
from urllib.parse import urlsplit
import urllib.error
import urllib.request

import pipeline as p

BRAND = 7076410
ZONE = "Europe/Athens"
CREATE_TOOL = "mcp__codex_apps__metricool_createscheduledpost"
READ_TOOL = "mcp__codex_apps__metricool_getscheduledposts"
MAX_MEDIA_BYTES = 150 * 1024 * 1024


def utcnow():
    return dt.datetime.now(p.UTC)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def metricool_url(value):
    if not isinstance(value, str):
        raise p.Blocked("STAGED_METRICOOL_VIDEO_REQUIRED")
    u = urlsplit(value)
    if (u.scheme != "https" or u.hostname != "static.metricool.com" or
            u.username or u.password or u.port not in (None, 443) or
            not u.path.lower().endswith(".mp4") or u.fragment):
        raise p.Blocked("STAGED_METRICOOL_VIDEO_REQUIRED")
    return value


def post_info(job, handoff):
    """Observed Metricool scheduler JSON; never copy unrelated *Data fields."""
    delivery = job.get("delivery", {})
    url = metricool_url(delivery.get("media_url"))
    if delivery.get("media_sha256") != handoff["media_sha256"]:
        raise p.Blocked("STAGED_MEDIA_HASH_BINDING_REQUIRED")
    if type(delivery.get("media_bytes")) is not int or delivery["media_bytes"] <= 0:
        raise p.Blocked("STAGED_MEDIA_BYTE_COUNT_REQUIRED")
    local = p.parse_time(handoff["scheduled_at"]).astimezone(p.ZoneInfo(ZONE))
    platform = handoff["platform"]
    body = {"text": handoff["caption"], "providers": [{"network": platform}],
            "publicationDate": {"dateTime": local.strftime("%Y-%m-%dT%H:%M:%S"), "timezone": ZONE},
            "media": [url], "autoPublish": True, "draft": False}
    if platform == "instagram":
        body["instagramData"] = {"type": "REEL", "autoPublish": True,
                                 "showReelOnFeed": True, "isAiGenerated": True}
    elif platform == "facebook":
        # This observed payload shape is retained for schema inspection only.
        # schedule_once blocks Facebook until a native AI field is verified.
        body["facebookData"] = {"type": "REEL", "title": job["title"]}
    elif platform == "tiktok":
        body["tiktokData"] = {"title": job["title"], "privacyOption": "PUBLIC_TO_EVERYONE",
                              "autoAddMusic": False, "photoCoverIndex": 0, "isAigc": True}
    elif platform == "youtube":
        audience = delivery.get("youtube_made_for_kids")
        if type(audience) is not bool:
            raise p.Blocked("EXPLICIT_YOUTUBE_AUDIENCE_REQUIRED")
        body["youtubeData"] = {"title": job["title"], "type": "short", "privacy": "public",
                               "madeForKids": audience, "isAiGeneratedContent": True}
    else:
        raise p.Blocked("UNSUPPORTED_SINGLE_PLATFORM")
    return body


def query_for_day(day):
    local = dt.datetime.fromisoformat(day).replace(tzinfo=p.ZoneInfo(ZONE))
    end = local + dt.timedelta(days=1) - dt.timedelta(seconds=1)
    return {"brandId": str(BRAND), "fromDate": local.isoformat(), "toDate": end.isoformat(),
            "timezone": ZONE, "extendedRange": False}


def validate_brand_fields(record):
    if not isinstance(record, dict):
        return
    values = [record[key] for key in ("blogId", "brandId", "brand_id") if key in record]
    if isinstance(record.get("brand"), dict) and "id" in record["brand"]:
        values.append(record["brand"]["id"])
    if any(type(value) not in (str, int) or str(value) != str(BRAND) for value in values):
        raise p.Blocked("LIVE_BRAND_MISMATCH")


def incomplete_marker(value):
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.replace("_", "").lower()
            if normalized in ("next", "nextpage", "nextcursor", "hasmore", "truncated") and item:
                return True
            if normalized in ("complete", "paginationexhausted") and item is False:
                return True
            if incomplete_marker(item):
                return True
    elif isinstance(value, list):
        return any(incomplete_marker(item) for item in value)
    return False


def unwrap(response):
    """Recognize actual MCP text/structured envelopes and the API data wrapper."""
    if isinstance(response, dict) and response.get("isError"):
        raise p.Blocked("METRICOOL_TOOL_ERROR")
    if incomplete_marker(response):
        raise p.Blocked("INCOMPLETE_METRICOOL_RESPONSE")
    validate_brand_fields(response)
    if isinstance(response, dict) and "structuredContent" in response:
        response = response["structuredContent"]
    elif isinstance(response, dict) and "content" in response:
        blocks = response["content"]
        if not isinstance(blocks, list) or len(blocks) != 1 or blocks[0].get("type") != "text":
            raise p.Blocked("UNKNOWN_METRICOOL_RESPONSE_ENVELOPE")
        try:
            response = json.loads(blocks[0]["text"])
        except (ValueError, KeyError, TypeError) as exc:
            raise p.Blocked("UNREADABLE_METRICOOL_RESPONSE") from exc
    if isinstance(response, dict):
        validate_brand_fields(response)
        if incomplete_marker(response):
            raise p.Blocked("INCOMPLETE_METRICOOL_RESPONSE")
        if any(response.get(k) for k in ("error", "error_code", "error_message", "isError")):
            raise p.Blocked("METRICOOL_API_ERROR")
        if any(response.get(k) for k in ("next", "nextPage", "nextCursor", "hasMore", "truncated")):
            raise p.Blocked("INCOMPLETE_METRICOOL_RESPONSE")
        if "data" in response:
            return response["data"]
    return response


def rows_from(response):
    rows = unwrap(response)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise p.Blocked("COMPLETE_METRICOOL_ROW_LIST_REQUIRED")
    for row in rows:
        validate_brand_fields(row)
    return rows


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise p.Blocked("HTTP_REDIRECT_REQUIRES_RECONCILIATION")


def remote_digest(url):
    """Read exact already-staged bytes; no upload, normalization or credentials."""
    metricool_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "SteliosExactMediaReview/1.0"})
    h, size = hashlib.sha256(), 0
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
        for chunk in iter(lambda: response.read(1024 * 1024), b""):
            size += len(chunk)
            if size > MAX_MEDIA_BYTES:
                raise p.Blocked("STAGED_MEDIA_TOO_LARGE")
            h.update(chunk)
    return {"sha256": h.hexdigest(), "bytes": size}


class MetricoolConnectorTransport:
    """Bind the exact currently exposed connected-tool names and arguments.

    call_tool must be the host's authenticated callable (tool_name, arguments).
    It must not add retries. It is deliberately not an untrusted command string.
    """
    def __init__(self, call_tool: Callable, media_digest: Callable = remote_digest):
        self.call_tool, self.media_digest = call_tool, media_digest

    def create(self, body):
        return self.call_tool(CREATE_TOOL, {"blogId": str(BRAND),
            "date": body["publicationDate"]["dateTime"], "info": canonical(body)})

    def read(self, query):
        return self.call_tool(READ_TOOL, query)


def verify_media(transport, url, expected):
    actual = transport.media_digest(metricool_url(url))
    if actual != {"sha256": expected["media_sha256"], "bytes": expected["media_bytes"]}:
        raise p.Blocked("EXACT_STAGED_BYTES_MISMATCH")


def validate_binding(history, journal, now):
    lease = history.get("sources", {}).get("production_lease", {})
    binding = lease.get("delivery_executor_binding", {})
    if not (binding.get("private") is True and binding.get("verified_shared_durable_store") is True and
            binding.get("executor_id") == lease.get("owner") and binding.get("reviewer") and
            re.fullmatch(r"[0-9a-f]{64}", str(binding.get("evidence_sha256", ""))) and
            binding.get("journal_path") == str(journal.resolve()) and p.fresh(binding, now, 5)):
        raise p.Blocked("VERIFIED_SHARED_DELIVERY_JOURNAL_BINDING_REQUIRED")


def validate_refresh_evidence(history, started, now):
    if p.parse_time(history.get("checked_at", "")) < started or incomplete_marker(history):
        raise p.Blocked("NEW_COMPLETE_HISTORY_READ_REQUIRED_FOR_THIS_CREATE")
    for name in p.HISTORY_SOURCES:
        source = history.get("sources", {}).get(name, {})
        if not p.fresh(source, now, 5) or p.parse_time(source["checked_at"]) < started:
            raise p.Blocked("NEW_SOURCE_READ_REQUIRED:" + name)
        if name != "production_lease" and source.get("pagination_exhausted") is not True:
            raise p.Blocked("ALL_SOURCE_PAGES_REQUIRED:" + name)
    snapshot = history.get("queue_snapshot", {})
    if not p.fresh(snapshot, now, 5) or p.parse_time(snapshot["checked_at"]) < started:
        raise p.Blocked("NEW_QUEUE_READ_REQUIRED_FOR_THIS_CREATE")


def own_inactive(previous, job):
    requested = (previous.get("story_id") == job.get("story_id") and
                 previous.get("inactive") is True and previous.get("candidate_row_only") is True)
    if not requested:
        return False
    inactive_states = {"DRAFT", "BLOCKED", "INACTIVE", "CANCELLED", "CANCELED", "WITHDRAWN"}
    def explicit_inactive(status):
        return isinstance(status, str) and status.strip().upper() in inactive_states
    providers = previous.get("providers", [])
    if (not explicit_inactive(previous.get("status")) or not isinstance(providers, list) or
            any(not isinstance(provider, dict) or not explicit_inactive(provider.get("status"))
                for provider in providers)):
        raise p.Blocked("INVALID_INACTIVE_HISTORY_EXEMPTION")
    return True


def history_media_duplicate(job, history):
    target = job["final"]["sha256"]
    def contains_hash(value):
        if isinstance(value, dict):
            return any((key in ("sha256", "media_sha256", "final_sha256", "video_sha256") and item == target) or
                       (key in ("media_sha256s", "media_hashes") and isinstance(item, list) and target in item) or
                       contains_hash(item) for key, item in value.items())
        return isinstance(value, list) and any(contains_hash(item) for item in value)
    for previous in history.get("stories", []):
        if not own_inactive(previous, job) and contains_hash(previous):
            raise p.Blocked("DUPLICATE_FINAL_MEDIA_IN_FULL_HISTORY")


@contextmanager
def journal_lock(path):
    if not path.is_absolute() or not path.parent.is_dir() or path.is_symlink():
        raise p.Blocked("ABSOLUTE_EXISTING_DURABLE_JOURNAL_DIRECTORY_REQUIRED")
    lock_path = path.with_name(path.name + ".lock")
    if lock_path.is_symlink():
        raise p.Blocked("JOURNAL_LOCK_SYMLINK_FORBIDDEN")
    with lock_path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise p.Blocked("DELIVERY_EXECUTOR_BUSY_NO_RETRY") from None
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def connection(path):
    db = sqlite3.connect(path, timeout=0)
    db.execute("PRAGMA synchronous=FULL")
    db.execute("PRAGMA journal_mode=DELETE")
    db.execute("CREATE TABLE IF NOT EXISTS attempts (key TEXT PRIMARY KEY, story TEXT UNIQUE NOT NULL, "
               "media TEXT UNIQUE NOT NULL, fingerprint TEXT UNIQUE NOT NULL, script TEXT UNIQUE NOT NULL, "
               "payload TEXT NOT NULL, state TEXT NOT NULL, result TEXT NOT NULL)")
    columns = [row[1] for row in db.execute("PRAGMA table_info(attempts)")]
    if columns != ["key", "story", "media", "fingerprint", "script", "payload", "state", "result"]:
        db.close()
        raise p.Blocked("INCOMPATIBLE_DELIVERY_JOURNAL_REQUIRES_RECONCILIATION")
    db.commit()
    return db


def normalized_script_hash(job):
    return hashlib.sha256(p.normalized(job["script"]).encode()).hexdigest()


def known_attempt(db, handoff, job):
    row = db.execute("SELECT state,result FROM attempts WHERE key=? OR story=? OR media=? OR fingerprint=? OR script=?",
        (handoff["idempotency_key"], handoff["story_id"], handoff["media_sha256"],
         p.normalized(job["fingerprint"]), normalized_script_hash(job))).fetchone()
    if row:
        raise p.Blocked("DELIVERY_ALREADY_ATTEMPTED_NO_RETRY:" + row[0])


def require_journal_reconciled(db, history):
    today_keys = {}
    for key, state, payload in db.execute("SELECT key,state,payload FROM attempts"):
        if state in ("WRITE_STARTED_OUTCOME_UNKNOWN", "UNKNOWN_REQUIRES_RECONCILIATION"):
            raise p.Blocked("UNRESOLVED_PREVIOUS_WRITE_BLOCKS_NEW_CREATE")
        if state not in ("SCHEDULED_PENDING", "PUBLISHED", "FAILED_NO_RETRY"):
            raise p.Blocked("UNKNOWN_JOURNAL_STATE_REQUIRES_RECONCILIATION")
        for name in ("metricool", "notion", "repository"):
            keys = history["sources"][name].get("observed_delivery_keys")
            if not isinstance(keys, list) or key not in keys:
                raise p.Blocked("PREVIOUS_DELIVERY_NOT_RECONCILED:" + name)
        if state in ("SCHEDULED_PENDING", "PUBLISHED"):
            try:
                body = json.loads(payload)
                date = body["publicationDate"]
                local_date = dt.datetime.fromisoformat(date["dateTime"]).date().isoformat()
                provider = body["providers"][0]["network"]
                if date["timezone"] != ZONE or len(body["providers"]) != 1 or provider not in p.PLATFORMS:
                    raise ValueError("Invalid stored target")
            except (KeyError, TypeError, ValueError, IndexError):
                raise p.Blocked("INVALID_JOURNAL_PAYLOAD_REQUIRES_RECONCILIATION") from None
            if local_date == history["queue_snapshot"]["local_date"]:
                today_keys.setdefault(provider, set()).add(key)
    for platform, keys in today_keys.items():
        counts = history["queue_snapshot"].get("platforms", {}).get(platform, {})
        observed = counts.get("observed_delivery_keys")
        values = (counts.get("published"), counts.get("active_pending"))
        if (not isinstance(observed, list) or any(key not in observed for key in keys) or
                any(type(value) is not int or value < 0 for value in values) or sum(values) < len(keys)):
            raise p.Blocked("PREVIOUS_DELIVERY_NOT_INCLUDED_IN_QUEUE_COUNTS:" + platform)


def readback_row(rows, body, returned):
    validate_brand_fields(returned)
    identified = []
    if isinstance(returned, dict) and returned.get("id") is not None:
        identified = [row for row in rows if str(row.get("id")) == str(returned["id"])]
    elif isinstance(returned, dict) and returned.get("uuid"):
        identified = [row for row in rows if row.get("uuid") == returned["uuid"]]
    else:
        identified = [row for row in rows if row.get("media") == body["media"] and
                      row.get("publicationDate") == body["publicationDate"] and row.get("text") == body["text"]]
    if len(identified) != 1:
        raise p.Blocked("UNIQUE_LIVE_READBACK_REQUIRED")
    row = identified[0]
    if (type(row.get("id")) not in (str, int) or not str(row["id"]).strip() or
            row["id"] in (0, "0") or not isinstance(row.get("uuid"), str) or not row["uuid"].strip()):
        raise p.Blocked("LIVE_ID_AND_UUID_REQUIRED")
    if isinstance(returned, dict) and returned.get("uuid") and row["uuid"] != returned["uuid"]:
        raise p.Blocked("LIVE_UUID_MISMATCH")
    for key in ("publicationDate", "text", "autoPublish", "draft"):
        if row.get(key) != body[key] or (key in ("autoPublish", "draft") and type(row.get(key)) is not bool):
            raise p.Blocked("LIVE_FIELD_MISMATCH:" + key)
    if len(row.get("providers", [])) != 1 or row["providers"][0].get("network") != body["providers"][0]["network"]:
        raise p.Blocked("LIVE_PROVIDER_MISMATCH")
    if not isinstance(row.get("media"), list) or len(row["media"]) != 1:
        raise p.Blocked("LIVE_SINGLE_MEDIA_REQUIRED")
    for key, data in body.items():
        if key.endswith("Data"):
            for field, value in data.items():
                observed = row.get(key, {}).get(field)
                # TikTok may omit false photo-only music settings for a video.
                if key == "tiktokData" and field == "autoAddMusic" and observed is None:
                    continue
                if observed != value or (type(value) is bool and type(observed) is not bool):
                    raise p.Blocked("LIVE_PLATFORM_SETTING_MISMATCH:" + key + "." + field)
    provider = row["providers"][0]
    status = provider.get("status")
    if status == "PENDING":
        state = "SCHEDULED_PENDING"
    elif status == "PUBLISHED" and provider.get("id") and provider.get("publicUrl"):
        url = urlsplit(provider["publicUrl"])
        platform = body["providers"][0]["network"]
        domains = {"youtube": ("youtube.com", "youtu.be"), "facebook": ("facebook.com", "fb.watch"),
                   "instagram": ("instagram.com",), "tiktok": ("tiktok.com",)}[platform]
        host = url.hostname or ""
        if (url.scheme != "https" or url.username or url.password or not url.path.strip("/") or
                not any(host == domain or host.endswith("." + domain) for domain in domains)):
            raise p.Blocked("LIVE_PUBLICATION_URL_MISMATCH")
        state = "PUBLISHED"
    elif status in ("ERROR", "FAILED"):
        state = "FAILED_NO_RETRY"
    else:
        raise p.Blocked("UNVERIFIED_PROVIDER_STATUS")
    return row, state


def check_live_capacity(rows, job, history, body):
    count = {"PUBLISHED": 0, "PENDING": 0}
    for row in rows:
        if row.get("media") == body["media"] or row.get("text") == body["text"]:
            raise p.Blocked("DUPLICATE_IN_FRESH_METRICOOL_READ")
        date = row.get("publicationDate", {})
        if date.get("timezone") != ZONE or not str(date.get("dateTime", "")).startswith(job["local_date"] + "T"):
            raise p.Blocked("METRICOOL_READ_RANGE_OR_TIMEZONE_MISMATCH")
        for provider in row.get("providers", []):
            if provider.get("network") != job["platform"]:
                continue
            status = provider.get("status")
            if status == "PUBLISHED":
                count[status] += 1
            elif status == "PENDING" and row.get("draft") is False and row.get("autoPublish") is True:
                count[status] += 1
            elif status not in ("PENDING", "ERROR", "FAILED"):
                raise p.Blocked("UNKNOWN_EXISTING_PROVIDER_STATUS")
    prior = history["queue_snapshot"]["platforms"][job["platform"]]
    # The connector documents pending reads; prior publication analytics remain
    # necessary. Conservatively retain the larger observed count for each state.
    if max(count["PUBLISHED"], prior["published"]) + max(count["PENDING"], prior["active_pending"]) >= 10:
        raise p.Blocked("DAILY_PLATFORM_CAP_REACHED")


def schedule_once(job, base: Path, refresh: Callable, transport, journal: Path, *, execute=False, clock=utcnow):
    """Call refresh() inside the exclusive delivery lock for every attempted create.

    refresh returns authentic current {policy, history}; it must reread all four
    sources and hold the external lease, not relabel cached files as fresh.
    """
    job = copy.deepcopy(job)
    def prepare():
        started = clock()
        inputs = copy.deepcopy(refresh())
        policy, history = inputs["policy"], inputs["history"]
        now = clock()
        validate_refresh_evidence(history, started, now)
        # Validate every requested own-candidate exemption before the existing
        # preflight can skip its identity checks based on an unnormalized status.
        history_media_duplicate(job, history)
        handoff = p.release_preflight(job, base, policy, history, now)
        if job["platform"] == "facebook":
            raise p.Blocked("FACEBOOK_NATIVE_AI_FIELD_NOT_VERIFIED")
        return policy, history, handoff, post_info(job, handoff), started

    if not execute:
        _, _, handoff, body, _ = prepare()
        return {"state": "DRY_RUN_NOT_SENT", "handoff": handoff, "request": body, "provider_writes": 0}
    with journal_lock(journal):
        policy, history, handoff, body, started = prepare()
        validate_binding(history, journal, clock())
        db = connection(journal)
        try:
            known_attempt(db, handoff, job)
            require_journal_reconciled(db, history)
            query = query_for_day(job["local_date"])
            rows = rows_from(transport.read(query))
            check_live_capacity(rows, job, history, body)
            verify_media(transport, body["media"][0], job["delivery"])
            # Revalidate clock, lease, exact local bytes and all gates immediately
            # before the durable claim. A slow media read cannot extend clearance.
            p.release_preflight(job, base, policy, history, clock())
            now = clock()
            validate_refresh_evidence(history, started, now)
            validate_binding(history, journal, now)
            result = {"state": "WRITE_STARTED_OUTCOME_UNKNOWN", "job_id": job["id"],
                      "story_id": job["story_id"], "brand_id": BRAND, "platform": job["platform"],
                      "media_sha256": handoff["media_sha256"], "started_at": clock().isoformat(),
                      "fingerprint": job["fingerprint"], "script_sha256": p.script_hash(job["script"]),
                      "normalized_script_sha256": normalized_script_hash(job), "idempotency_key": handoff["idempotency_key"]}
            db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)", (handoff["idempotency_key"],
                handoff["story_id"], handoff["media_sha256"], p.normalized(job["fingerprint"]),
                normalized_script_hash(job), canonical(body), result["state"], canonical(result)))
            db.commit()  # durable BEFORE the non-idempotent connector request
            returned = None
            try:
                returned = unwrap(transport.create(body))
                if isinstance(returned, list) and len(returned) == 1:
                    returned = returned[0]
            except Exception as exc:
                result["create_error_type"] = type(exc).__name__
                result["create_error_code"] = safe_error_code(exc)
            try:
                # Always read immediately after the write, including timeouts or
                # server errors. Absence never authorizes an automatic retry.
                row, state = readback_row(rows_from(transport.read(query)), body, returned)
                verify_media(transport, row["media"][0], job["delivery"])
                result.update(state=state, metricool_id=row["id"], metricool_uuid=row["uuid"],
                    publication_date=row["publicationDate"], providers=row["providers"], media=row["media"],
                    draft=row["draft"], auto_publish=row["autoPublish"],
                    readback_at=clock().isoformat(), exact_uploaded_bytes_verified=True,
                    published=state == "PUBLISHED", scheduled_pending=state == "SCHEDULED_PENDING")
            except Exception as exc:
                result.update(state="UNKNOWN_REQUIRES_RECONCILIATION", readback_error_type=type(exc).__name__,
                              readback_error_code=safe_error_code(exc), published=False, scheduled_pending=False)
            db.execute("UPDATE attempts SET state=?,result=? WHERE key=?",
                       (result["state"], canonical(result), handoff["idempotency_key"]))
            db.commit()
            return result
        finally:
            db.close()


def safe_error_code(exc):
    # Preserve our fixed operational reason codes, never provider response bodies,
    # headers, exception URLs, credentials, or arbitrary exception messages.
    if isinstance(exc, p.Blocked) and re.fullmatch(r"[A-Z][A-Za-z0-9_.:]+", str(exc)):
        return str(exc)
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTP_" + str(exc.code) + "_NO_RETRY"
    return type(exc).__name__
