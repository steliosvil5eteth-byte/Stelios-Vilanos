#!/usr/bin/env python3
"""One explicit ordinary Edge narration request; no account, paid API or retry.

This creates review material only. It never approves media or publishes a post.
The isolated caller must hold a fresh shared production lease and clear history.
"""
from __future__ import annotations
import argparse
import asyncio
import datetime as dt
import hashlib
import html
import json
import ssl
import urllib.request
from pathlib import Path

VOICE = "el-GR-NestorasNeural"

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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
        attempt.update(status="NARRATION_RENDERED_NEEDS_REVIEW", audio_bytes=audio_path.stat().st_size, audio_sha256=hashlib.sha256(audio_path.read_bytes()).hexdigest(), word_boundaries=len(boundaries))
    except Exception as exc:
        # Do not echo service URLs, client headers or credentials in errors.
        attempt.update(status="FAILED_NO_AUTOMATIC_RETRY", error_type=type(exc).__name__, audio_bytes=audio_path.stat().st_size if audio_path.exists() else 0)
        write(attempt_path, attempt)
        print(json.dumps({"status": attempt["status"], "error_type": attempt["error_type"], "audio_bytes": attempt["audio_bytes"]}))
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
