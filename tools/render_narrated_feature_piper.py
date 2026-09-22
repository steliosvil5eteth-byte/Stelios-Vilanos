#!/usr/bin/env python3
"""Render CURRENT narrated features with the free local Piper Greek voice.

This wrapper reuses the existing deterministic 9:16 visual/subtitle renderer,
but replaces Azure synthesis with local Piper el_GR-rapunzelina-medium. It
implements the current gate: narration must be strictly longer than 80s,
there is no artificial maximum duration, no paid fallback, no background
music, and unintended dead-air gaps of about two seconds or longer fail QA.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import render_narrated_feature_strict as strict

base = strict.base
VOICE = "el_GR-rapunzelina-medium"


def synthesize_piper(text: str, output_path: Path, voice: str = VOICE) -> None:
    if voice != VOICE:
        raise RuntimeError(f"Piper voice must be {VOICE}, got {voice}")
    model = os.environ.get("PIPER_MODEL", "").strip()
    if not model:
        raise RuntimeError("PIPER_MODEL is not set")
    model_path = Path(model)
    if not model_path.exists():
        raise RuntimeError(f"Piper model not found: {model_path}")

    raw = output_path.with_name(output_path.stem + "-piper.wav")
    proc = subprocess.run(
        [
            "piper",
            "--model", str(model_path),
            "--output_file", str(raw),
        ],
        input=text,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Piper synthesis failed: {proc.stderr.strip()}")

    # Keep the base renderer's known-good WAV contract (24 kHz mono PCM).
    base.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
        "-ar", str(base.SR), "-ac", "1", "-c:a", "pcm_s16le", str(output_path),
    ])
    raw.unlink(missing_ok=True)


def patch_qa_metadata(path: Path) -> None:
    """Replace the base renderer's legacy Azure-only label for Piper runs."""
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    reports = data if isinstance(data, list) else [data]
    for report in reports:
        if isinstance(report, dict):
            report.pop("azure_only", None)
            report["speech_engine"] = "piper_local"
            report["local_offline_tts"] = True
            report["paid_fallback_used"] = False
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def output_dir_from_argv() -> Path | None:
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            return Path(sys.argv[idx + 1])
    value = os.environ.get("OUTPUT_DIR", "").strip()
    return Path(value) if value else None


# Patch only the synthesis/policy surface. Natural speed is Piper's default
# length scale (1.0); no speed manipulation is passed to the CLI.
base.synthesize = synthesize_piper
base.DEFAULT_VOICE = VOICE
base.MIN_SECONDS = 80.000001
base.PREFERRED_MIN = 80.000001
base.PREFERRED_MAX = 10**9
base.MAX_SECONDS = 10**9
base.MAX_DEAD_AIR = 1.95
base.MAX_TRAILING = 0.50

if __name__ == "__main__":
    base.main()
    out = output_dir_from_argv()
    if out is not None:
        patch_qa_metadata(out / "qa-summary.json")
        for qa in out.glob("*/qa.json"):
            patch_qa_metadata(qa)
