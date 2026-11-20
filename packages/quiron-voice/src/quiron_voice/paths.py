"""Per-user locations and network config, portable via platformdirs."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_cache_dir, user_log_dir

APP = "quiron-voice"
HOST = "127.0.0.1"  # loopback only: the daemon is never reachable from the network
DEFAULT_PORT = 47811


def port() -> int:
    return int(os.environ.get("QUIRON_VOICE_PORT", DEFAULT_PORT))


def cache_dir() -> Path:
    p = Path(os.environ.get("QUIRON_VOICE_CACHE") or user_cache_dir(APP, appauthor=False))
    p.mkdir(parents=True, exist_ok=True)
    return p


def log_file() -> Path:
    p = Path(os.environ.get("QUIRON_VOICE_CACHE") or user_log_dir(APP, appauthor=False))
    p.mkdir(parents=True, exist_ok=True)
    return p / "server.log"


def last_transcript() -> Path:
    return cache_dir() / "last.txt"
