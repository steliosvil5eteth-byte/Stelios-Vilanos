#!/usr/bin/env python3
"""One explicit ordinary Edge narration request; no account, paid API or retry.

This creates review material only. It never approves media or publishes a post.
The isolated caller must hold a fresh shared production lease and clear history.
"""
from __future__ import annotations
import argparse
import asyncio
import datetime as dt
from email.utils import parsedate_to_datetime
import hashlib
import html
from http import HTTPStatus
import json
import ssl
import subprocess
import urllib.request
from pathlib import Path

VOICE = "el-GR-NestorasNeural"

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def safe_error_metadata(exc):
    """Keep useful refusal diagnostics without URLs, request headers or tokens.

    In particular, str(aiohttp.ClientResponseError) includes its request URL.
    Never serialize the exception, request_info, history, or all headers.
    """
    result = {"error_type": type(exc).__name__}
    status = getattr(exc, "status", None)
    if isinstance(status, int) and not isinstance(status, bool) and 100 <= status <= 599:
        result["http_status"] = status
        try:
            result["http_status_message"] = HTTPStatus(status).phrase
        except ValueError:
            result["http_status_message"] = "Unregistered HTTP status"
        result["access_denied"] = status in (401, 403)
        result["rate_limited"] = status == 429
    headers = getattr(exc, "headers", None)
    retry_after = headers.get("Retry-After") if hasattr(headers, "get") else None
    if isinstance(retry_after, str):
        value = retry_after.strip()
        if value.isascii() and value.isdigit() and len(value) <= 12:
            result["retry_after_seconds"] = int(value)
        elif len(value) <= 80:
            try:
                result["retry_after_utc"] = parsedate_to_datetime(value).astimezone(dt.timezone.utc).isoformat()
            except (ValueError, TypeError, OverflowError):
                result["retry_after_present_unparsed"] = True
    # Only fixed, credential-free protocol phrases may be retained verbatim.
    message = getattr(exc, "message", None)
    safe_messages = {
        "Invalid response status", "Invalid upgrade header",
        "Invalid connection header", "Invalid challenge response",
        "Server disconnected", "Connection timeout", "Timeout on reading data from socket",
    }
    if isinstance(message, str) and message:
        result["protocol_message"] = message if message in safe_messages else "Unrecognized message omitted to avoid credentials"
    return result

async def synthesize(job, output):
    import edge_tts
    from edge_tts import communicate
    # Retain certificate and hostname verification while also loading the
    # executor's already-trusted system CA bundle.
    communicate._SSL_CTX.load_default_certs(ssl.Purpose.SERVER_AUTH)
    if communicate._SSL_CTX.verify_mode != ssl.CERT_REQUIRED or not communicate._SSL_CTX.check_hostname:
        raise RuntimeError("TLS verification must remain enabled")
    attempt_path = output / "speech_attempt.json"
    if attempt_path.exists():
        raise RuntimeError("Existing attempt: reconcile its state; no automatic retry")
    script = job["script"]
    if job["voice"] != VOICE or not script.rstrip().endswith("Αν σας άρεσε, ακολουθήστε για περισσότερα."):
        raise RuntimeError("Exact voice or full CTA mismatch")
    attempt = {
        "job_id": job["id"], "story_id": job["story_id"],
        "voice": VOICE, "transport": "microsoft_edge_online_service",
        "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "script_sha256_exact_bytes": hashlib.sha256(script.encode()).hexdigest(),
        "characters": len(script), "paid_account_credentials_used": False,
        "paid_credit_budget": 0, "automatic_retry": False,
        "status": "REQUEST_STARTED", "actual_audio_listened": False,
        "PASSED_FINAL_REVIEW": False, "publishing_permitted": False,
    }
    write(attempt_path, attempt)
    output.joinpath("script.txt").write_text(script + "\n", encoding="utf-8")
    boundaries = []
    audio_path = output / "narration.mp3"
    client = edge_tts.Communicate(script, voice=VOICE, rate="+0%", boundary="WordBoundary", connect_timeout=15, receive_timeout=45)
    try:
        with audio_path.open("xb") as file:
            async for chunk in client.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    boundaries.append({"text": html.unescape(chunk["text"]), "start": chunk["offset"] / 10000000, "end": (chunk["offset"] + chunk["duration"]) / 10000000})
        if audio_path.stat().st_size < 1024 or len(boundaries) < 20:
            raise RuntimeError("Incomplete audio or boundary response")
        write(output / "word_boundaries.json", boundaries)
        # Word events can cover the entire script even when a service response
        # silently omits encoded audio. Inspect a complete PCM decode before
        # reporting a usable narration; neither a header nor event count proves
        # that the actual sound data reaches the final word.
        pcm = subprocess.run([
            "ffmpeg", "-v", "error", "-i", str(audio_path),
            "-ac", "1", "-ar", "24000", "-f", "s16le", "-",
        ], capture_output=True, check=True).stdout
        decoded_seconds = len(pcm) / 48000
        last_word_end = max(float(event["end"]) for event in boundaries)
        attempt.update(audio_bytes=audio_path.stat().st_size, audio_sha256=hashlib.sha256(audio_path.read_bytes()).hexdigest(), word_boundaries=len(boundaries), decoded_audio_seconds=decoded_seconds, last_word_end_seconds=last_word_end, complete_word_span_fits_audio=decoded_seconds + 0.05 >= last_word_end)
        if decoded_seconds + 0.05 < last_word_end:
            raise RuntimeError("Actual decoded audio ends before returned final word boundary")
        attempt.update(status="NARRATION_RENDERED_NEEDS_REVIEW")
    except Exception as exc:
        # Do not echo service URLs, client headers or credentials in errors.
        diagnostic = safe_error_metadata(exc)
        attempt.update(status="FAILED_NO_AUTOMATIC_RETRY", audio_bytes=audio_path.stat().st_size if audio_path.exists() else 0, **diagnostic)
        write(attempt_path, attempt)
        print(json.dumps({"status": attempt["status"], "audio_bytes": attempt["audio_bytes"], **diagnostic}))
        raise SystemExit(2) from None
    attempt["completed_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    write(attempt_path, attempt)
    print(json.dumps(attempt, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public-manifest-url")
    args = parser.parse_args()
    job = next(j for j in json.loads(args.manifest.read_text())["jobs"] if j["id"] == args.job_id)
    if args.public_manifest_url:
        # This verification is deliberately before transmission. Only text
        # already returned by an anonymous public HTTPS GET may be submitted.
        # No account cookie, access token or Authorization header is supplied.
        req = urllib.request.Request(args.public_manifest_url, headers={"User-Agent": "public-source-verification/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError("Public source verification failed")
            public_manifest = json.load(response)
        public_job = next(j for j in public_manifest["jobs"] if j["id"] == args.job_id)
        if public_job["script"] != job["script"]:
            raise RuntimeError("Private or modified source text may not be transmitted")
        job = public_job
    args.output.mkdir(parents=True, exist_ok=True)
    asyncio.run(synthesize(job, args.output))

if __name__ == "__main__":
    main()
