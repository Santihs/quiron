"""Talk to the daemon; start it on demand."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any

from . import paths, protocol


class ServerUnavailable(RuntimeError):
    pass


HEALTH_TIMEOUT = 3.0  # a healthy daemon answers health instantly; longer means wedged


def connect(port: int | None = None, timeout: float = 2.0, read_timeout: float | None = None) -> socket.socket:
    s = socket.create_connection((paths.HOST, paths.port() if port is None else port), timeout=timeout)
    s.settimeout(read_timeout)
    return s


def request(
    msg: dict[str, Any],
    payload: bytes = b"",
    wait: bool = True,
    port: int | None = None,
    read_timeout: float | None = None,
) -> dict[str, Any] | None:
    """Send one request. With wait=False, return right after sending (fire and forget).

    `read_timeout=None` waits indefinitely (say/transcribe can take long); health
    checks pass HEALTH_TIMEOUT so a wedged daemon raises instead of hanging.
    """
    with connect(port, read_timeout=read_timeout) as s:
        s.sendall(protocol.encode(msg) + payload)
        if not wait:
            return None
        with s.makefile("rb") as f:
            return protocol.decode(protocol.read_line(f))


def spawn_server(extra_args: list[str] | None = None) -> subprocess.Popen[bytes]:  # pragma: no cover
    """Start the daemon detached, with no console window on Windows."""
    cmd = [sys.executable, "-m", "quiron_voice.cli", "server", "run", *(extra_args or [])]
    log = open(paths.log_file(), "ab")
    kwargs: dict[str, Any] = {"stdout": log, "stderr": log, "stdin": subprocess.DEVNULL}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def ensure_server(
    port: int | None = None,
    spawn: Callable[[], object] = spawn_server,
    wait_s: float = 180.0,
    poll_s: float = 0.25,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Return the daemon's health, starting it if nothing answers.

    First start can be slow (model download), hence the generous wait.
    """
    try:
        return request({"op": "health"}, port=port, read_timeout=HEALTH_TIMEOUT) or {}
    except OSError:
        pass
    spawn()
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        sleep(poll_s)
        try:
            return request({"op": "health"}, port=port, read_timeout=HEALTH_TIMEOUT) or {}
        except OSError:
            continue
    raise ServerUnavailable(f"voice server did not start; see {paths.log_file()}")


def wait_ready(
    engine: str,
    port: int | None = None,
    wait_s: float = 600.0,
    poll_s: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Block until `engine` ("tts"/"stt") reports ready; raise if it failed to load."""
    deadline = time.monotonic() + wait_s
    while True:
        h = request({"op": "health"}, port=port, read_timeout=HEALTH_TIMEOUT) or {}
        state = h.get("models", {}).get(engine, "cold")
        if state == "ready":
            return
        if state.startswith("error"):
            raise ServerUnavailable(f"{engine} {state}")
        if time.monotonic() >= deadline:
            raise ServerUnavailable(f"{engine} still {state} after {wait_s:.0f}s")
        sleep(poll_s)
