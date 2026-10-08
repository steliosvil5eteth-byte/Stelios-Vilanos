#!/usr/bin/env python3
"""Independent Greek recognition of 1–25 explicitly hash-bound media files.

Uses the existing Azure F0 recognition helper, never TTS. Final-video evidence
must match both the exact MP4 hash and the final video's decoded PCM hash.
Recognition differences always require review; this tool cannot approve media.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

PROGRAM = "YOUTUBE_GROWTH_TEN_DAILY"
VOICE = "el-GR-NestorasNeural"
CTA = "Αν σας άρεσε, ακολουθήστε για περισσότερα."
SHA = re.compile(r"[a-f0-9]{64}\Z")
SAFE_ID = re.compile(r"[a-z0-9][a-z0-9_-]{2,99}\Z")


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: list[str]) -> str:
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError("Media probing or PCM extraction failed")
    return result.stdout


def validate(data: dict, selected_ids: list[str]) -> list[dict]:
    for key, value in {
        "program": PROGRAM, "brand_id": 7076410, "voice": VOICE,
        "azure_tier_required": "F0", "paid_generation_allowed": False,
    }.items():
        if data.get(key) != value or (value is False and data.get(key) is not False):
            raise ValueError(f"ASR policy mismatch: {key}")
    if not isinstance(data.get("batch_id"), str) or not SAFE_ID.fullmatch(data["batch_id"]):
        raise ValueError("Stable batch ID required")
    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= 25:
        raise ValueError("ASR requires 1–25 explicit jobs")
    ids = []
    for job in jobs:
        job_id = job.get("id")
        if not isinstance(job_id, str) or not SAFE_ID.fullmatch(job_id) or job_id in ids:
            raise ValueError("Invalid or duplicate stable ID")
        ids.append(job_id)
        script = job.get("script", "")
        if not script.endswith(CTA) or hashlib.sha256(script.encode()).hexdigest() != job.get("script_sha256"):
            raise ValueError("ASR comparison script must be complete and hash-bound")
        media = job.get("review_media", {})
        if media.get("kind") not in {"final_mp4", "source_wav"}:
            raise ValueError("review_media.kind must explicitly identify final_mp4 or source_wav")
        relative = media.get("path")
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError("Media path must remain within the downloaded artifact")
        expected_suffix = ".mp4" if media["kind"] == "final_mp4" else ".wav"
        if Path(relative).suffix.lower() != expected_suffix:
            raise ValueError("Media extension disagrees with explicit review stage")
        if not SHA.fullmatch(str(media.get("sha256", ""))):
            raise ValueError("Exact media SHA-256 is required")
        if media["kind"] == "final_mp4" and not SHA.fullmatch(str(media.get("audio_pcm_sha256", ""))):
            raise ValueError("Final MP4 review requires the renderer's exact decoded PCM hash")
    if len(selected_ids) != len(set(selected_ids)) or not set(selected_ids) <= set(ids):
        raise ValueError("Selected job IDs are repeated or not present in the request")
    return [job for job in jobs if not selected_ids or job["id"] in selected_ids]


def verified_media(job: dict, source: Path) -> Path:
    root = source.resolve(strict=True)
    media = (root / job["review_media"]["path"]).resolve(strict=True)
    if not media.is_relative_to(root) or not media.is_file():
        raise ValueError("Media resolved outside the supplied artifact")
    if file_sha(media) != job["review_media"]["sha256"]:
        raise ValueError("Exact media hash mismatch")
    return media


def classify(exc: Exception) -> str:
    text = str(exc).lower()
    if any(part in text for part in ("429", "quota", "too many", "throttl")):
        return "AZURE_ASR_QUOTA_OR_RATE_LIMIT"
    if any(part in text for part in ("401", "403", "auth", "subscription", "forbidden")):
        return "AZURE_ASR_AUTH_OR_RESOURCE_POLICY"
    if isinstance(exc, (ValueError, FileNotFoundError)):
        return "MEDIA_OR_REQUEST_RECONCILIATION_REQUIRED"
    return "ASR_OR_MEDIA_PROCESSING_ERROR"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--job-id", action="append", default=[])
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        request_bytes = args.manifest.read_bytes()
        request = json.loads(request_bytes)
        jobs = validate(request, args.job_id)
        media_files = {job["id"]: verified_media(job, args.source) for job in jobs} if args.source else {}
        if args.validate_only:
            print(json.dumps({"request_valid": True, "jobs": len(jobs),
                              "media_hashes_verified": bool(media_files), "asr_calls": 0}))
            return 0
        if args.source is None or args.output is None:
            raise ValueError("--source and --output are required for independent recognition")
        reviewer = importlib.import_module("qa_current_ten_20261006_asr")
        args.output.mkdir(parents=True, exist_ok=True)
        results = []
        summary = {
            "program": PROGRAM, "batch_id": request["batch_id"],
            "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
            "selected_job_ids": [job["id"] for job in jobs], "jobs": results,
            "recognizer_received_script_hints": False, "tts_calls": 0,
            "publish_ready": False, "final_review": "NOT_PERFORMED",
            "asr_execution_complete": False,
        }
        write_json(args.output / "asr-batch-summary.json", summary)
        for job in jobs:
            try:
                output = args.output / job["id"]
                report_path = output / "speech-recognition.json"
                if report_path.exists():
                    previous = json.loads(report_path.read_text(encoding="utf-8"))
                    if (
                        previous.get("input_media_sha256") == job["review_media"]["sha256"]
                        and previous.get("script_sha256") == job["script_sha256"]
                        and previous.get("program") == PROGRAM
                        and previous.get("review_media_kind") == job["review_media"]["kind"]
                        and (
                            job["review_media"]["kind"] != "final_mp4"
                            or previous.get("recognized_audio_pcm_sha256") == job["review_media"]["audio_pcm_sha256"]
                        )
                        and previous.get("asr_completed") is True
                    ):
                        result = {key: previous[key] for key in ("id", "asr_completed", "normalized_exact_match", "review_media_kind", "input_media_sha256")}
                        result["reused_existing_recognition"] = True
                        results.append(result)
                        write_json(args.output / "asr-batch-summary.json", summary)
                        continue
                    raise ValueError("Existing ASR report conflicts; reconcile before another request")
                if output.exists() and any(output.iterdir()):
                    raise ValueError("Partial ASR output exists; do not recognize it again blindly")
                output.mkdir(parents=True, exist_ok=True)
                media = media_files[job["id"]]
                wav = output / "exact-reviewed-audio.wav"
                run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(media), "-map", "0:a:0",
                     "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
                with wave.open(str(wav), "rb") as file:
                    if file.getnchannels() != 1 or file.getsampwidth() != 2 or file.getframerate() != 24000:
                        raise ValueError("ASR input PCM format differs from final renderer evidence")
                    pcm = file.readframes(file.getnframes())
                    duration = file.getnframes() / file.getframerate()
                pcm_sha = hashlib.sha256(pcm).hexdigest()
                expected_pcm = job["review_media"].get("audio_pcm_sha256")
                if expected_pcm is not None and pcm_sha != expected_pcm:
                    raise ValueError("Exact final decoded audio hash mismatch; ASR must not start")
                if not 80.0 <= duration <= 150.25:
                    raise ValueError("Reviewed narration duration is outside hard bounds")
                segments, errors, no_matches = reviewer.recognize(wav, duration)
                safe_errors = [{key: value for key, value in error.items() if key in {"reason", "code"}} for error in errors]
                transcript = " ".join(segment["text"] for segment in segments)
                expected, observed = reviewer.tokens(job["script"]), reviewer.tokens(transcript)
                differences = []
                for kind, i1, i2, j1, j2 in difflib.SequenceMatcher(a=expected, b=observed, autojunk=False).get_opcodes():
                    if kind != "equal":
                        differences.append({
                            "kind": kind, "expected_word_range": [i1, i2],
                            "recognized_word_range": [j1, j2],
                            "expected": " ".join(expected[i1:i2]), "recognized": " ".join(observed[j1:j2]),
                        })
                completed = bool(segments) and not errors
                report = {
                    "id": job["id"], "program": PROGRAM, "batch_id": request["batch_id"],
                    "provider": "Azure Speech F0 independent speech recognition", "language": "el-GR",
                    "azure_tier_required": "F0", "resource_sku_verified_by_this_script": False,
                    "review_media_kind": job["review_media"]["kind"],
                    "input_media_sha256": job["review_media"]["sha256"],
                    "script_sha256": job["script_sha256"], "recognized_audio_pcm_sha256": pcm_sha,
                    "recognized_audio_wav_sha256": file_sha(wav), "audio_duration_seconds": duration,
                    "final_video_audio_hash_match": job["review_media"]["kind"] == "final_mp4" and pcm_sha == expected_pcm,
                    "recognizer_received_script_hints": False, "recognized_text": transcript,
                    "expected_word_count": len(expected), "recognized_word_count": len(observed),
                    "normalized_exact_match": expected == observed,
                    "differences": differences, "segments": segments, "errors": safe_errors,
                    "no_match_regions": no_matches, "asr_completed": completed,
                    "direct_listening_claimed": False, "voice_identity_independently_verified": False,
                    "tts_calls": 0, "paid_fallback_used": False, "automatic_retry_performed": False,
                    "publish_ready": False,
                    "release_status": "PENDING_FINAL_VISUAL_AND_AUDIO_REVIEW",
                }
                write_json(report_path, report)
                (output / "recognized-text.txt").write_text(transcript + "\n", encoding="utf-8")
                result = {key: report[key] for key in ("id", "asr_completed", "normalized_exact_match", "review_media_kind", "input_media_sha256")}
                result["reused_existing_recognition"] = False
                results.append(result)
                write_json(args.output / "asr-batch-summary.json", summary)
                print(json.dumps(result, ensure_ascii=False), flush=True)
                if errors:
                    summary["stopped_job_id"] = job["id"]
                    summary["failure_category"] = "AZURE_ASR_CANCELED_OR_INCOMPLETE"
                    summary["remaining_unattempted_ids"] = [entry["id"] for entry in jobs[jobs.index(job) + 1:]]
                    write_json(args.output / "asr-batch-summary.json", summary)
                    return 1
            except Exception as exc:
                summary["stopped_job_id"] = job["id"]
                summary["failure_category"] = classify(exc)
                summary["remaining_unattempted_ids"] = [entry["id"] for entry in jobs[jobs.index(job) + 1:]]
                write_json(args.output / "asr-batch-summary.json", summary)
                print(json.dumps({"stopped_job_id": job["id"], "failure_category": summary["failure_category"],
                                  "automatic_retry_performed": False, "publish_ready": False}), file=sys.stderr)
                return 1
        summary["asr_execution_complete"] = True
        summary["all_transcripts_match"] = all(result["normalized_exact_match"] for result in results)
        write_json(args.output / "asr-batch-summary.json", summary)
        return 0 if summary["all_transcripts_match"] else 2
    except Exception as exc:
        print(json.dumps({"failure_category": classify(exc), "asr_execution_complete": False,
                          "publish_ready": False, "automatic_retry_performed": False}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
