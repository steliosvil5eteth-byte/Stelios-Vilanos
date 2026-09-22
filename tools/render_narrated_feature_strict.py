#!/usr/bin/env python3
"""Strict wrapper for narrated features.

Keeps the renderer's hard QA gates while trimming only leading/trailing Azure
silence. It deliberately preserves natural internal pauses and has no paid
fallback path. Current deterministic visual themes are rights-safe local art.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_narrated_feature as base
import render_current_visuals as current_visuals
import render_next_visuals as next_visuals


def trim_edges_only(src: Path, dst: Path) -> None:
    filt = (
        "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-48dB,"
        "areverse,"
        "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-48dB,"
        "areverse"
    )
    base.run([
        "ffmpeg","-y","-loglevel","error","-i",str(src),
        "-af",filt,
        "-ar",str(base.SR),"-ac","1","-c:a","pcm_s16le",str(dst)
    ])


base.trim_wav = trim_edges_only
base.make_scene = next_visuals.make_scene_factory(current_visuals.make_scene_factory(base.make_scene))

if __name__ == "__main__":
    base.main()
