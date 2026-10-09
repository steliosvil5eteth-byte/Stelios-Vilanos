"""Cooperative host-wide limits for recovery render and local ASR processes.

Only processes using this helper are counted. Existing processes are not killed
or reconfigured. Kernel flock releases a slot even if its process terminates.
"""
from __future__ import annotations

from contextlib import contextmanager
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import tempfile
import time

CAPACITY = {"ffmpeg": 3, "asr": 1}
LOCK_ROOT = Path(tempfile.gettempdir()) / f"stelios-social-recovery-resources-{os.getuid()}"


@contextmanager
def resource_slot(resource: str):
    if resource not in CAPACITY:
        raise ValueError(f"Unknown recovery resource: {resource}")
    LOCK_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    started = time.monotonic()
    acquired = None
    while acquired is None:
        for number in range(1, CAPACITY[resource] + 1):
            handle = (LOCK_ROOT / f"{resource}-{number}.lock").open("a+")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
                continue
            acquired = handle
            info = {"resource": resource, "capacity": CAPACITY[resource],
                    "slot": number, "pid": os.getpid(),
                    "wait_seconds": round(time.monotonic() - started, 6),
                    "acquired_at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps(info) + "\n")
            handle.flush()
            break
        if acquired is None:
            time.sleep(0.25)
    try:
        yield info
    finally:
        fcntl.flock(acquired.fileno(), fcntl.LOCK_UN)
        acquired.close()
