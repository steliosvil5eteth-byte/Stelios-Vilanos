#!/usr/bin/env python3
"""Resilient wrapper for render_survival_pack.py.
Caches duplicate source images in-memory and retries transient Wikimedia 429/5xx
responses with bounded backoff. Rendering/QA behavior remains in the base module.
"""
from __future__ import annotations

import time
import urllib.error
import urllib.request

import render_survival_pack as base

_CACHE: dict[str, bytes] = {}


def resilient_download(url: str, dest):
    base.check_url(url)
    if url in _CACHE:
        dest.write_bytes(_CACHE[url])
        return
    last_error = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "SteliosSurvivalRenderer/1.1 (social media preparation; source attribution preserved)",
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read(base.MAX_DOWNLOAD + 1)
            if len(data) == 0:
                raise ValueError("empty source image")
            if len(data) > base.MAX_DOWNLOAD:
                raise ValueError("source image exceeds 30 MiB")
            _CACHE[url] = data
            dest.write_bytes(data)
            return
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504):
                raise
            if attempt == 4:
                break
            time.sleep(8 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 4:
                break
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"source download failed after bounded retries: {last_error}")


base.download = resilient_download

if __name__ == "__main__":
    base.main()
