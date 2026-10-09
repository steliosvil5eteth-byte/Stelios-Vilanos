#!/usr/bin/env python3
"""Package only the fully published 2026-10-09 forty-post release.

Read-only inputs; no network, publication, media conversion, or repository writes.
All checks finish before any visible output is created. Captions come exclusively
from each ledger entry's actual ``caption`` value, never from a draft manifest.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import urlsplit, urlunsplit
import zipfile


DATE = "2026-10-09"
BRAND_ID = 7076410
VOICE = "el-GR-NestorasNeural"
PLATFORMS = ("facebook", "instagram", "tiktok", "youtube")
LABELS = {"facebook": "Facebook", "instagram": "Instagram", "tiktok": "TikTok", "youtube": "YouTube"}
DOMAINS = {
    "facebook": ("facebook.com", "fb.watch"),
    "instagram": ("instagram.com",),
    "tiktok": ("tiktok.com",),
    "youtube": ("youtube.com", "youtu.be"),
}
HEARING_NOTE = (
    "Φωνή: Νέστορας (el-GR-NestorasNeural), συνθετική ελληνική αφήγηση. "
    "Δεν πραγματοποιήθηκε άμεση ακρόαση από το σύστημα. Οι υπολογιστικοί "
    "έλεγχοι και η απομαγνητοφώνηση δεν ισοδυναμούν με πραγματική ακρόαση."
)


class ReleaseError(ValueError):
    """A required completion or exact-file condition is not satisfied."""


def digest_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def md_text(value: str) -> str:
    """Keep a title on one Markdown line and prevent title text becoming markup."""
    value = " ".join(value.split())
    return re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", value)


def public_url(value: object, platform: str) -> tuple[str, str]:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ReleaseError(f"{platform}: a nonempty public_url is required")
    if re.search(r"[\s<>]", value):
        raise ReleaseError(f"{platform}: malformed public_url")
    parts = urlsplit(value)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or parts.username or parts.password or parts.port not in (None, 443):
        raise ReleaseError(f"{platform}: public_url must be an HTTPS public platform link")
    if not any(host == domain or host.endswith("." + domain) for domain in DOMAINS[platform]):
        raise ReleaseError(f"{platform}: public_url host does not identify the expected platform")
    if not parts.path.strip("/"):
        raise ReleaseError(f"{platform}: public_url is a platform homepage, not a publication")
    normalized = urlunsplit(("https", host, parts.path.rstrip("/"), parts.query, ""))
    return value, normalized


def title_map(manifest: Path | None) -> dict[str, str]:
    if manifest is None:
        return {}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        raise ReleaseError("Optional manifest must contain a jobs list")
    result = {}
    for job in jobs:
        if not isinstance(job, dict):
            raise ReleaseError("Malformed manifest job")
        job_id = job.get("id", job.get("job_id"))
        title = job.get("title")
        if isinstance(job_id, str) and isinstance(title, str) and title.strip():
            if job_id in result:
                raise ReleaseError(f"Duplicate manifest job: {job_id}")
            result[job_id] = title
    return result


def validate_release(ledger_path: Path, deliverables: Path, manifest: Path | None) -> list[dict]:
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(ledger, dict) or ledger.get("brand_id") != BRAND_ID:
        raise ReleaseError(f"Ledger must belong to brand {BRAND_ID}")
    entries = ledger.get("entries")
    if not isinstance(entries, list) or len(entries) != 40:
        raise ReleaseError("Completion requires exactly 40 ledger entries; a partial release is not packaged")
    if not deliverables.is_dir():
        raise ReleaseError("Deliverables directory does not exist")
    titles = title_map(manifest)
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    seen_filenames: set[str] = set()
    seen_metricool_ids: set[str] = set()
    counts: Counter = Counter()
    result = []
    expected = {f"{DATE}-{platform}-{number:02d}" for platform in PLATFORMS for number in range(1, 11)}

    for entry in entries:
        if not isinstance(entry, dict):
            raise ReleaseError("Every ledger entry must be an object")
        job_id = entry.get("job_id")
        if not isinstance(job_id, str) or job_id not in expected or job_id in seen_ids:
            raise ReleaseError(f"Missing, duplicate, or out-of-scope job_id: {job_id!r}")
        seen_ids.add(job_id)
        platform, number = job_id.rsplit("-", 2)[-2:]
        if entry.get("status") != "PUBLISHED" or entry.get("published") is not True:
            raise ReleaseError(f"{job_id}: publication has not been confirmed PUBLISHED")
        url, normalized_url = public_url(entry.get("public_url"), platform)
        if normalized_url in seen_urls:
            raise ReleaseError(f"{job_id}: duplicate public publication URL")
        seen_urls.add(normalized_url)
        providers = entry.get("providers")
        if providers is not None:
            if not isinstance(providers, list):
                raise ReleaseError(f"{job_id}: providers must be a list")
            matching = [p for p in providers if isinstance(p, dict) and p.get("network") == platform]
            if len(matching) != 1 or matching[0].get("status") != "PUBLISHED":
                raise ReleaseError(f"{job_id}: the expected provider is not uniquely PUBLISHED")
            _, provider_url = public_url(matching[0].get("publicUrl"), platform)
            if provider_url != normalized_url:
                raise ReleaseError(f"{job_id}: entry and provider public URLs disagree")
        metricool_id = entry.get("metricool_id")
        if metricool_id is not None:
            key = str(metricool_id)
            if key in seen_metricool_ids:
                raise ReleaseError(f"{job_id}: duplicate Metricool publication record")
            seen_metricool_ids.add(key)
        caption = entry.get("caption")
        if not isinstance(caption, str) or not caption.strip():
            raise ReleaseError(f"{job_id}: exact published entry.caption is required; draft fallback is forbidden")
        filename = entry.get("filename")
        if (not isinstance(filename, str) or not filename or Path(filename).name != filename
                or "/" in filename or "\\" in filename or any(ord(c) < 32 for c in filename)
                or not filename.lower().endswith(".mp4")):
            raise ReleaseError(f"{job_id}: filename must be a plain MP4 basename")
        if filename in seen_filenames:
            raise ReleaseError(f"{job_id}: duplicate deliverable filename")
        seen_filenames.add(filename)
        expected_sha = entry.get("sha256")
        expected_bytes = entry.get("bytes")
        if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha):
            raise ReleaseError(f"{job_id}: a valid SHA256 is required")
        if type(expected_bytes) is not int or expected_bytes <= 0:
            raise ReleaseError(f"{job_id}: a positive exact byte count is required")
        source = deliverables / filename
        if not source.is_file():
            raise ReleaseError(f"{job_id}: missing deliverable {filename}")
        if source.resolve().parent != deliverables.resolve():
            raise ReleaseError(f"{job_id}: deliverable resolves outside its directory")
        actual_sha, actual_bytes = digest_file(source)
        if (actual_sha, actual_bytes) != (expected_sha.lower(), expected_bytes):
            raise ReleaseError(f"{job_id}: deliverable does not match its exact ledger SHA256 and bytes")
        result.append({"job_id": job_id, "platform": platform, "number": int(number),
                       "title": titles.get(job_id, Path(filename).stem), "url": url,
                       "filename": filename, "source": source, "caption": caption,
                       "sha256": actual_sha, "bytes": actual_bytes})
        counts[platform] += 1
    if seen_ids != expected or counts != Counter({p: 10 for p in PLATFORMS}):
        raise ReleaseError("Exactly ten unique published jobs per platform are required")
    return sorted(result, key=lambda item: (PLATFORMS.index(item["platform"]), item["number"]))


def publication_lines(entries: list[dict]) -> list[str]:
    return [f"{row['number']}. [{md_text(row['title'])}](<{row['url']}>)" for row in entries]


def copy_verified_into_zip(archive: zipfile.ZipFile, row: dict) -> None:
    """Recheck the exact bytes while copying, so a changed input cannot be sealed."""
    h = hashlib.sha256()
    count = 0
    with row["source"].open("rb") as source, archive.open(row["filename"], "w", force_zip64=True) as target:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            target.write(chunk)
            h.update(chunk)
            count += len(chunk)
    if h.hexdigest() != row["sha256"] or count != row["bytes"]:
        raise ReleaseError(f"{row['job_id']}: input changed during packaging; no release was committed")


def package_release(ledger: Path, deliverables: Path, output: Path, manifest: Path | None = None) -> dict:
    rows = validate_release(ledger, deliverables, manifest)
    output = output.resolve()
    if output == deliverables.resolve():
        raise ReleaseError("Output must be separate from deliverables")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ReleaseError("Output directory must be new or empty; existing releases are never overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-building-", dir=output.parent))
    artifacts = []
    try:
        report = [f"# Οι 40 δημοσιεύσεις · {DATE}", "",
                  "Ιστορίες που μας αγγίζουν · 10 δημοσιεύσεις ανά πλατφόρμα.", "", HEARING_NOTE, ""]
        for platform in PLATFORMS:
            group = [row for row in rows if row["platform"] == platform]
            links = publication_lines(group)
            archive_path = stage / f"{platform}_10_publications_{DATE}.zip"
            readme = [f"# {LABELS[platform]} · 10 δημοσιεύσεις · {DATE}", "",
                      "Ιστορίες που μας αγγίζουν", "", HEARING_NOTE, "",
                      "Περιεχόμενα: 10 ακριβή MP4, 10 κείμενα δημοσιεύσεων και αυτός ο κατάλογος.",
                      "Τα κείμενα προέρχονται από τις επιβεβαιωμένες δημοσιεύσεις του ledger. "
                      "Τα MP4 διατηρούνται αυτούσια, χωρίς επανακωδικοποίηση.", "",
                      "## Δημοσιεύσεις", "", *links, ""]
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
                for row in group:
                    copy_verified_into_zip(archive, row)
                    archive.writestr(f"{Path(row['filename']).stem}_caption.txt", row["caption"].encode("utf-8"))
                archive.writestr("README.md", "\n".join(readme).encode("utf-8"))
            # Central-directory count and CRC verification catch packaging damage.
            with zipfile.ZipFile(archive_path) as archive:
                if len(archive.infolist()) != 21 or archive.testzip() is not None:
                    raise ReleaseError(f"{platform}: completed archive integrity check failed")
                if any(info.compress_type != zipfile.ZIP_STORED for info in archive.infolist()):
                    raise ReleaseError(f"{platform}: unexpected compression mode")
            checksum, size = digest_file(archive_path)
            artifacts.append({"filename": archive_path.name, "sha256": checksum, "bytes": size,
                              "platform": platform, "published_count": 10})
            report.extend([f"## {LABELS[platform]}", "", *links, ""])
        report_path = stage / f"40_publications_{DATE}.md"
        report_path.write_text("\n".join(report), encoding="utf-8")
        checksum, size = digest_file(report_path)
        artifacts.append({"filename": report_path.name, "sha256": checksum, "bytes": size})
        if output.exists():
            output.rmdir()  # only the previously validated empty output directory
        os.replace(stage, output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return {"status": "COMPLETE_40_PUBLISHED_RELEASE_PACKAGED", "date": DATE,
            "brand_id": BRAND_ID, "published_count": 40, "counts": {p: 10 for p in PLATFORMS},
            "output": str(output), "voice": VOICE, "actual_audio_listened": False,
            "artifacts": [{**item, "path": str(output / item["filename"])} for item in artifacts]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--deliverables", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, help="Optional canonical jobs manifest; used only for titles")
    args = parser.parse_args()
    try:
        result = package_release(args.ledger, args.deliverables, args.output, args.manifest)
    except (ReleaseError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "BLOCKED_INCOMPLETE_OR_MISMATCHED_RELEASE", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
