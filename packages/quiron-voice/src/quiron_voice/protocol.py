"""JSON-lines protocol between client and daemon over localhost TCP.

Request : one JSON object + "\\n". For `transcribe`, `nbytes` raw float32 PCM
          bytes (mono, 16 kHz) follow the line.
Response: one JSON object + "\\n": {"ok": true, ...} or {"ok": false, "error": ...}.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

OPS = frozenset({"say", "stop", "transcribe", "health", "shutdown"})
MAX_LINE = 1 << 20  # 1 MiB of JSON is plenty for any spoken text
MAX_AUDIO = 16_000 * 4 * 60 * 10  # 10 min of float32 mono at 16 kHz


class ProtocolError(ValueError):
    pass


class Reader(Protocol):
    """Anything with file-like binary reads (socket makefile, BytesIO, rfile)."""

    def read(self, size: int = ..., /) -> bytes: ...
    def readline(self, size: int = ..., /) -> bytes: ...


def encode(msg: dict[str, Any]) -> bytes:
    return (json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8")


def read_line(f: Reader) -> bytes:
    line = f.readline(MAX_LINE + 1)
    if len(line) > MAX_LINE:
        raise ProtocolError("line too long")
    return line


def decode(line: bytes) -> dict[str, Any]:
    if not line:
        raise ProtocolError("connection closed")
    try:
        msg = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ProtocolError(f"bad json: {e}") from e
    if not isinstance(msg, dict):
        raise ProtocolError("message must be a JSON object")
    return msg


def validate_request(msg: dict[str, Any]) -> dict[str, Any]:
    op = msg.get("op")
    if op not in OPS:
        raise ProtocolError(f"unknown op {op!r}")
    if op == "say" and not isinstance(msg.get("text"), str):
        raise ProtocolError("say needs a text string")
    if op == "transcribe":
        n = msg.get("nbytes")
        if not isinstance(n, int) or isinstance(n, bool) or n < 0 or n > MAX_AUDIO or n % 4:
            raise ProtocolError("transcribe needs nbytes: a non-negative multiple of 4 within limits")
    return msg


def read_exact(f: Reader, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        part = f.read(n - len(buf))
        if not part:
            raise ProtocolError("connection closed mid-payload")
        buf += part
    return bytes(buf)


def ok(**fields: Any) -> dict[str, Any]:
    return {"ok": True, **fields}


def err(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message}
