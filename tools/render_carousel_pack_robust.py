#!/usr/bin/env python3
"""Compatibility entry point for exact-source carousel rendering.

The historical title/query image overrides and automatic Commons fallbacks
are retired. Every card must pin its own scene-specific source_url or
source_path. A failed source blocks that job instead of substituting an image.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_carousel_pack as base

if __name__ == '__main__':
    base.main()
