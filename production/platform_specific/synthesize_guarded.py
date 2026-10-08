#!/usr/bin/env python3
"""Optional one-job Azure adapter, held by policy and verified account receipts.

No SDK import or network request happens during import, dry run, failed gates,
or tests. One reserved attempt only: failures retain budget and never auto-retry.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import hmac
import json
import os
import re
import uuid
from pathlib import Path

from pipeline import (Blocked, UTC, VOICE, budget_errors, fresh, history_errors, parse_time,
                      lease_errors, production_errors, read_json, script_hash, sha256, source_errors,
                      story_hash, validate_manifest, write_json)


class BudgetLedger:
    """Persistent local reservations; preserve UNKNOWN attempts conservatively.

    A production executor must use one shared durable ledger/lease, not separate
    private copies on forty workers. Local filesystem locking is process-safe.
    """
    def __init__(self, path: Path):
        self.path = path

    @contextlib.contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(self.path.suffix + ".lock").open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                data = read_json(self.path) if self.path.exists() else {"schema_version": 1, "attempts": []}
                yield data
                write_json(self.path, data)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def reserve(self, job: dict, receipt: dict, now: dt.datetime) -> str:
        with self.locked() as data:
            # Even changing a failed job's script cannot silently create a retry.
            if any(attempt["job_id"] == job["id"] for attempt in data["attempts"]):
                raise Blocked("Job already has a synthesis attempt; reconcile it, never auto-retry")
            reserved = 0
            for attempt in data["attempts"]:
                if attempt["resource_id"] != receipt.get("resource_id") or attempt["period"] != receipt.get("period"):
                    continue
                # Monitoring can lag behind the receipt's wall-clock read time.
                # Only an explicit acknowledgement of this completed attempt,
                # covered by the provider's usage window, avoids double counting.
                accounted = False
                if attempt["status"] == "CONSUMED" and attempt["attempt_id"] in receipt.get("included_attempt_ids", []):
                    try:
                        accounted = (parse_time(attempt["provider_completed_at"]) <= parse_time(receipt["usage_window_end"]) <=
                                     parse_time(receipt["checked_at"]) <= now)
                    except (KeyError, TypeError, ValueError):
                        accounted = False
                if not accounted:
                    reserved += attempt["characters"]
            errors = budget_errors(job, receipt, now, reserved)
            if errors:
                raise Blocked("; ".join(errors))
            identifier = uuid.uuid4().hex
            data["attempts"].append({"attempt_id": identifier, "job_id": job["id"], "story_sha256": story_hash(job),
                                     "script_sha256": script_hash(job["script"]), "resource_id": receipt["resource_id"],
                                     "period": receipt["period"], "characters": job["tts_charge_upper_bound"],
                                     "reserved_at": now.isoformat(), "budget_receipt_checked_at": receipt["checked_at"],
                                     "status": "RESERVED", "voice": VOICE})
            return identifier

    def finish(self, identifier: str, status: str, audio_hash: str | None = None):
        if status not in ("CONSUMED", "UNKNOWN"):
            raise Blocked("Reservation may not be released automatically after an attempted call")
        with self.locked() as data:
            attempt = next(item for item in data["attempts"] if item["attempt_id"] == identifier)
            attempt.update(status=status, updated_at=dt.datetime.now(UTC).isoformat())
            if audio_hash is not None:
                attempt["audio_sha256"] = audio_hash
            if status == "CONSUMED" and "provider_completed_at" not in attempt:
                attempt["provider_completed_at"] = dt.datetime.now(UTC).isoformat()


def validate_credentials(receipt: dict) -> tuple[str, str]:
    """Check private fingerprint/region from the same verified resource read.

    Never return, print or persist the current key or its fingerprint. The input
    receipt is private operational evidence and must never enter a public repo.
    """
    key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
    binding = receipt.get("credential_binding", {})
    expected_endpoint = f"https://{region}.tts.speech.microsoft.com"
    if not (key and re.fullmatch(r"[a-z0-9-]+", region) and binding.get("private") is True and
            binding.get("verified_same_resource") is True and binding.get("resource_id") == receipt.get("resource_id") and
            binding.get("region") == region and binding.get("endpoint") == expected_endpoint and
            hmac.compare_digest(hashlib.sha256(key.encode()).hexdigest(), str(binding.get("key_sha256", "")))):
        raise Blocked("Private Azure credential/resource/region binding is missing or mismatched; no request sent")
    return key, region


def validate_ledger_binding(history: dict, receipt: dict, path: Path, now: dt.datetime) -> Path:
    """Use only the private shared ledger verified for this executor and account.

    A matching path cannot prove that two hosts share the same filesystem. The
    executor must actually use the shared durable store named by this evidence.
    """
    lease = history.get("sources", {}).get("production_lease", {})
    binding = lease.get("executor_binding", {})
    try:
        expected = binding.get("ledger_path")
        resolved = path.expanduser().resolve()
        valid = (isinstance(expected, str) and Path(expected).is_absolute() and
                 Path(expected).resolve() == resolved and binding.get("private") is True and
                 binding.get("verified_shared_durable_store") is True and
                 binding.get("executor_id") == lease.get("owner") and binding.get("executor_id") and
                 binding.get("resource_id") == receipt.get("resource_id") and
                 binding.get("period") == receipt.get("period") and binding.get("reviewer") and
                 re.fullmatch(r"[0-9a-f]{64}", str(binding.get("evidence_sha256", ""))) and
                 fresh(binding, now, 15))
    except (OSError, TypeError, ValueError, RuntimeError):
        valid = False
    if not valid:
        raise Blocked("EXECUTOR_LEDGER_BINDING_REQUIRED_OR_MISMATCHED; no request sent")
    return resolved


def azure_synthesize(script: str, credentials: tuple[str, str]) -> tuple[bytes, list[dict]]:
    # The sole provider adapter. Nothing falls back to another voice/account.
    try:
        import azure.cognitiveservices.speech as speechsdk
        key, region = credentials  # immutable snapshot already bound to receipt
        config = speechsdk.SpeechConfig(subscription=key, region=region)
        config.speech_synthesis_voice_name = VOICE
        config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
        boundaries = []
        engine = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=None)
        engine.synthesis_word_boundary.connect(lambda event: boundaries.append({"text": event.text, "offset": float(event.audio_offset) / 10000000.0}))
        result = engine.speak_text_async(script).get()
        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise Blocked("Azure synthesis did not complete")
        return bytes(result.audio_data), boundaries
    except Exception:
        # SDK exceptions can contain request/account diagnostics. Emit no keys,
        # credential fingerprints or raw provider error payloads.
        raise Blocked("Azure synthesis did not complete; reservation retained; no automatic retry") from None


def make_srt(boundaries: list[dict], duration: float, path: Path) -> None:
    from render_local import formatted_time
    groups, current = [], []
    for index, word in enumerate(boundaries):
        current.append(word)
        text = " ".join(item["text"] for item in current)
        if len(current) >= 6 or len(text) >= 38 or index == len(boundaries) - 1:
            start = float(current[0]["offset"])
            end = float(boundaries[index + 1]["offset"]) if index + 1 < len(boundaries) else duration
            if not 0 <= start < end <= duration + .002:
                raise Blocked("Invalid Azure boundary timing; no resynthesis attempted")
            groups.append((start, min(end, duration), text))
            current = []
    if len(groups) < 10:
        raise Blocked("Insufficient word-boundary evidence")
    path.write_text("\n\n".join(f"{number}\n{formatted_time(start)} --> {formatted_time(end)}\n{text}"
                                for number, (start, end, text) in enumerate(groups, 1)) + "\n", encoding="utf-8")


def synthesize_job(job: dict, policy: dict, history: dict, receipt: dict, ledger_path: Path,
                   output: Path, *, execute: bool = False, provider=None, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(UTC)
    errors = (production_errors(policy, job["platform"], "synthesize") + source_errors(job) +
              history_errors(job, history, now) + lease_errors(job, history, now, "synthesize") + budget_errors(job, receipt, now))
    if not execute:
        errors.append("EXECUTION_NOT_REQUESTED")
    if output.exists() or job.get("audio"):
        errors.append("EXISTING_AUDIO_OR_OUTPUT_MUST_BE_REUSED")
    if errors:
        raise Blocked("; ".join(sorted(set(errors))))
    credentials = validate_credentials(receipt)
    ledger_path = validate_ledger_binding(history, receipt, ledger_path, now)
    if provider is None:
        provider = lambda script: azure_synthesize(script, credentials)
    ledger = BudgetLedger(ledger_path)
    attempt = ledger.reserve(job, receipt, now)
    try:
        output.mkdir(parents=True)
        wav, boundaries = provider(job["script"])
        if not isinstance(wav, bytes) or len(wav) < 1000 or not wav.startswith(b"RIFF"):
            raise Blocked("Provider returned no valid WAV; no retry")
        raw = output / "nestoras.wav"
        raw.write_bytes(wav)
        ledger.finish(attempt, "CONSUMED", sha256(raw))
        # Established convention: remove only useless trailing silence, preserving
        # initial timing and natural speech rate. Never pad/stretch narration.
        from render_local import parse_cues, probe, run
        trimmed = output / "nestoras-tail-trim.wav"
        run(["ffmpeg", "-v", "error", "-i", str(raw), "-af",
             "areverse,silenceremove=start_periods=1:start_duration=0.02:start_threshold=-48dB,areverse",
             "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(trimmed)])
        trimmed.replace(raw)
        duration = float(probe(raw)["format"]["duration"])
        if not 80 <= duration <= 110:
            raise Blocked("Narration outside 80–110 seconds; revise script explicitly, never pad or retry automatically")
        write_json(output / "boundaries.json", boundaries)
        (output / "script.txt").write_text(job["script"], encoding="utf-8")
        srt = output / "subs.srt"
        make_srt(boundaries, duration, srt)
        parse_cues(srt, duration, job["script"])
        result = {"path": str(raw.resolve()), "sha256": sha256(raw), "srt_path": str(srt.resolve()), "srt_sha256": sha256(srt),
                  "script_sha256": script_hash(job["script"]), "voice": VOICE, "background_music": False,
                  "provider": "Azure Speech", "duration_seconds": duration, "attempt_id": attempt,
                  "technical_audio_passed": True, "actual_audio_listened": False, "passed_final_review": False}
        write_json(output / "audio.json", result)
        ledger.finish(attempt, "CONSUMED", result["sha256"])
        return result
    except Exception:
        # Unknown usage is held even when a connection failed before audio arrived.
        # If audio already exists the provider call is known to have completed.
        existing = output / "nestoras.wav"
        ledger.finish(attempt, "CONSUMED" if existing.exists() else "UNKNOWN", sha256(existing) if existing.exists() else None)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("manifest", "policy", "history", "budget", "ledger", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        manifest = read_json(args.manifest)
        errors = validate_manifest(manifest)
        if errors:
            raise Blocked("; ".join(errors))
        job = next(job for job in manifest["jobs"] if job["id"] == args.job_id)
        result = synthesize_job(job, read_json(args.policy), read_json(args.history), read_json(args.budget),
                                args.ledger, args.output.resolve(), execute=args.execute)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (Blocked, ValueError, OSError, KeyError, StopIteration) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "automatic_retry": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
