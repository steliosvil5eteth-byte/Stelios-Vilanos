"""Read the pinned Notion archive through its unfiltered saved view.

This is raw collection, not publication clearance or an unattended host.  It
does not infer QA, delivery acknowledgments, lease ownership, or source expiry.
The authenticated synchronous call_tool callback remains a host dependency.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import re
from urllib.parse import urlsplit

FETCH_TOOL = "mcp__codex_apps__notion_fetch"
QUERY_TOOL = "mcp__codex_apps__notion_query_data_sources"
DATA_SOURCE = "collection://46cd5cf4-5f7e-46e8-b0ef-274aeadbdb52"
VIEW = "view://9200bc65-1a99-4479-b680-df8aedba0e6b"
UTC = dt.timezone.utc


class ArchiveReadBlocked(RuntimeError):
    """Only fixed operational codes; never attach connector bodies or tokens."""


def utcnow():
    return dt.datetime.now(UTC)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def partial_guard(value):
    for item in (value, value.get("metadata", {})):
        if not isinstance(item, dict):
            raise ArchiveReadBlocked("NOTION_RESPONSE_SHAPE_INVALID")
        if (item.get("truncated", False) is not False or
                type(item.get("unknown_block_count", 0)) is not int or
                item.get("unknown_block_count", 0) != 0 or
                item.get("unknown_block_ids", []) != []):
            raise ArchiveReadBlocked("NOTION_PARTIAL_RESPONSE")


def object_json(text):
    try:
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError()
        canonical(value)  # Reject non-JSON numeric values as well.
        return value
    except (TypeError, ValueError):
        raise ArchiveReadBlocked("NOTION_JSON_OBJECT_REQUIRED") from None


def payload(response):
    """Observed fetch structuredContent and query content[0].text envelopes."""
    if not isinstance(response, dict):
        raise ArchiveReadBlocked("NOTION_RESPONSE_SHAPE_INVALID")
    if response.get("isError", False) is not False:
        raise ArchiveReadBlocked("NOTION_TOOL_ERROR")
    partial_guard(response)
    if "structuredContent" in response:
        value = response["structuredContent"]
    else:
        content = response.get("content")
        if (not isinstance(content, list) or len(content) != 1 or
                not isinstance(content[0], dict) or content[0].get("type") != "text"):
            raise ArchiveReadBlocked("NOTION_RESPONSE_SHAPE_INVALID")
        value = object_json(content[0].get("text"))
    if not isinstance(value, dict):
        raise ArchiveReadBlocked("NOTION_RESPONSE_SHAPE_INVALID")
    partial_guard(value)
    return value


def reference(value):
    if not isinstance(value, str):
        return None
    return value[2:-2] if value.startswith("{{") and value.endswith("}}") else value


def tagged_entity(value, entity, expected):
    text = value.get("text")
    if (value.get("metadata", {}).get("type") != entity.replace("-", "_") or
            reference(value.get("id")) != expected or not isinstance(text, str)):
        raise ArchiveReadBlocked("NOTION_ENTITY_BINDING_MISMATCH")
    tags = re.findall(r"<" + re.escape(entity) + r' url="([^"]+)">', text)
    if len(tags) != 1 or reference(tags[0]) != expected:
        raise ArchiveReadBlocked("NOTION_ENTITY_BINDING_MISMATCH")
    return text


def json_tag(text, tag):
    matches = re.findall(r"<" + tag + r">\s*(.*?)\s*</" + tag + r">", text, re.S)
    if len(matches) != 1:
        raise ArchiveReadBlocked("NOTION_ENTITY_BODY_INVALID")
    return object_json(matches[0])


def schema_from(value):
    text = tagged_entity(value, "data-source", DATA_SOURCE)
    state = json_tag(text, "data-source-state")
    schema = state.get("schema")
    if (reference(state.get("url")) != DATA_SOURCE or not isinstance(schema, dict) or
            not schema or not all(isinstance(k, str) and isinstance(v, dict)
                                  for k, v in schema.items())):
        raise ArchiveReadBlocked("NOTION_SCHEMA_BINDING_INVALID")
    return state


def view_from(value, schema):
    text = tagged_entity(value, "view", VIEW)
    # The observed connector wraps the view URL in enhanced-Markdown braces.
    matches = re.findall(r'<view url="[^"]+">\s*(.*?)\s*</view>', text, re.S)
    if len(matches) != 1:
        raise ArchiveReadBlocked("NOTION_ENTITY_BODY_INVALID")
    settings = object_json(matches[0])
    if reference(settings.get("dataSourceUrl")) != DATA_SOURCE:
        raise ArchiveReadBlocked("NOTION_VIEW_SOURCE_MISMATCH")
    # Unknown settings fail closed; silently accepting a future filter would
    # turn a partial view into an apparent full archive enumeration.
    allowed = {"dataSourceUrl", "displayProperties", "name", "type", "sorts",
               "filter", "advancedFilter"}
    if set(settings) - allowed:
        raise ArchiveReadBlocked("NOTION_UNRECOGNIZED_VIEW_SETTING")
    if any(settings.get(key) not in (None, {}, []) for key in ("filter", "advancedFilter")):
        raise ArchiveReadBlocked("NOTION_UNFILTERED_VIEW_REQUIRED")
    properties = settings.get("displayProperties")
    if (settings.get("type") != "table" or not isinstance(properties, list) or
            not all(isinstance(item, str) for item in properties) or
            len(properties) != len(set(properties)) or not set(schema).issubset(properties)):
        raise ArchiveReadBlocked("NOTION_FULL_SCHEMA_VIEW_REQUIRED")
    return settings


def page_identity(row):
    if not isinstance(row, dict) or not isinstance(row.get("url"), str):
        raise ArchiveReadBlocked("NOTION_ROW_URL_REQUIRED")
    try:
        url = urlsplit(row["url"])
        match = re.search(r"(?:^|/|-)([0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})$", url.path)
        if (url.scheme != "https" or url.hostname not in {"app.notion.com", "notion.so", "www.notion.so"} or
                url.username or url.password or url.port not in (None, 443) or url.fragment or not match):
            raise ValueError()
        return match[1].replace("-", "").lower()
    except ValueError:
        raise ArchiveReadBlocked("NOTION_ROW_URL_INVALID") from None


def collect_archive(call_tool, *, clock=utcnow, page_size=100, max_pages=1000, max_rows=100000):
    """Consume active AND archived pagination; no retries or write callbacks.

    The result is deliberately not a publisher history/source receipt.  A host
    must still coordinate concurrent changes, join external evidence and obtain
    current clearance; pagination is not an atomic snapshot of Notion.
    """
    if (not callable(call_tool) or type(page_size) is not int or not 1 <= page_size <= 100 or
            type(max_pages) is not int or max_pages < 2 or
            type(max_rows) is not int or max_rows < 1):
        raise ArchiveReadBlocked("NOTION_READ_ARGUMENTS_INVALID")
    last_time = None

    def timestamp():
        nonlocal last_time
        value = clock()
        if not isinstance(value, dt.datetime) or value.utcoffset() is None:
            raise ArchiveReadBlocked("NOTION_AWARE_CLOCK_REQUIRED")
        value = value.astimezone(UTC)
        if last_time is not None and value < last_time:
            raise ArchiveReadBlocked("NOTION_CLOCK_MOVED_BACKWARD")
        last_time = value
        return value.isoformat()

    def read(name, arguments):
        if name not in {FETCH_TOOL, QUERY_TOOL}:
            raise ArchiveReadBlocked("NOTION_READ_TOOL_NOT_ALLOWED")
        try:
            response = call_tool(name, arguments)
        except Exception:
            raise ArchiveReadBlocked("NOTION_READ_CALL_FAILED") from None
        timestamp()
        return payload(response)

    started_at = timestamp()
    schema = schema_from(read(FETCH_TOOL, {"id": DATA_SOURCE}))
    view = view_from(read(FETCH_TOOL, {"id": VIEW}), schema["schema"])
    rows, pages, identities = {"active": [], "archived": []}, {"active": 0, "archived": 0}, set()
    for archived, partition in ((False, "active"), (True, "archived")):
        cursor, seen_cursors = None, set()
        while True:
            if sum(pages.values()) >= max_pages:
                raise ArchiveReadBlocked("NOTION_PAGE_LIMIT_REACHED")
            data = {"mode": "view", "view_url": VIEW, "page_size": page_size, "is_archived": archived}
            if cursor is not None:
                data["start_cursor"] = cursor
            page = read(QUERY_TOOL, {"data": data})
            batch, more, following = page.get("results"), page.get("has_more"), page.get("next_cursor")
            if (set(page) - {"results", "has_more", "next_cursor"} or
                    not isinstance(batch, list) or type(more) is not bool):
                raise ArchiveReadBlocked("NOTION_PAGINATION_SHAPE_INVALID")
            if sum(map(len, rows.values())) + len(batch) > max_rows:
                raise ArchiveReadBlocked("NOTION_ROW_LIMIT_REACHED")
            for row in batch:
                identity = page_identity(row)
                if identity in identities:
                    raise ArchiveReadBlocked("NOTION_DUPLICATE_PAGE_ID")
                identities.add(identity)
                rows[partition].append(copy.deepcopy(row))
            pages[partition] += 1
            if not more:
                if following not in (None, ""):
                    raise ArchiveReadBlocked("NOTION_CONTRADICTORY_END_CURSOR")
                break
            if not isinstance(following, str) or not following.strip():
                raise ArchiveReadBlocked("NOTION_NEXT_CURSOR_REQUIRED")
            if following in seen_cursors:
                raise ArchiveReadBlocked("NOTION_CURSOR_LOOP")
            seen_cursors.add(following)
            cursor = following
    final_schema = schema_from(read(FETCH_TOOL, {"id": DATA_SOURCE}))
    final_view = view_from(read(FETCH_TOOL, {"id": VIEW}), final_schema["schema"])
    if canonical(final_schema) != canonical(schema) or canonical(final_view) != canonical(view):
        raise ArchiveReadBlocked("NOTION_SCHEMA_OR_VIEW_CHANGED_DURING_READ")
    checked_at = timestamp()
    return {"artifact_kind": "notion_archive_raw_read_v1", "source": "notion",
            "data_source_url": DATA_SOURCE, "view_url": VIEW,
            "started_at": started_at, "checked_at": checked_at,
            "pagination_exhausted": True, "atomic_snapshot": False, "release_clearance": False,
            "pages_read": pages, "rows_seen": len(identities),
            "schema_sha256": digest(schema), "view_sha256": digest(view), "rows_sha256": digest(rows),
            "active_rows": rows["active"], "archived_rows": rows["archived"]}
