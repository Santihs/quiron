"""The voice daemon: keeps TTS + STT warm and serves requests on localhost TCP.

One process, two warm models: model load (seconds) is paid once per session,
not per `say`/`answer` call. Synthesis runs in a producer thread so the next
sentence is generated while the current one plays.
"""

from __future__ import annotations

import logging
import queue
import socketserver
import sys
import threading
from collections.abc import Callable
from typing import Any, Protocol, cast

import numpy as np

from . import __version__, paths, protocol
from .audio import loudness
from .engines import STT, TTS
from .text import chunks

log = logging.getLogger("quiron_voice.server")


class Sink(Protocol):
    def play(self, next_chunk: Callable[[], np.ndarray | None], cancel: threading.Event) -> None: ...


_END = object()


class VoiceService:
    """Request handling, independent of sockets (unit-testable)."""

    def __init__(self, tts: TTS, stt: STT, sink: Sink, device: str = "unknown") -> None:
        self.tts, self.stt, self.sink, self.device = tts, stt, sink, device
        self._speak_lock = threading.Lock()
        self._cancel = threading.Event()
        self._stop_gen = 0
        self._state_lock = threading.Lock()
        self.models: dict[str, str] = {"tts": "cold", "stt": "cold"}

    # -- lifecycle -------------------------------------------------------
    def warm(self) -> None:
        for name, engine in (("tts", self.tts), ("stt", self.stt)):
            self.models[name] = "loading"
            try:
                engine.load()
                self.models[name] = "ready"
            except Exception as e:  # keep serving the other engine
                log.exception("%s failed to load", name)
                self.models[name] = f"error: {e}"

    # -- ops -------------------------------------------------------------
    def health(self) -> dict[str, Any]:
        return protocol.ok(version=__version__, device=self.device, models=dict(self.models))

    def stop(self) -> dict[str, Any]:
        with self._state_lock:
            self._stop_gen += 1
            self._cancel.set()
        return protocol.ok()

    def say(self, text: str, lang: str = "en", voice: str | None = None, speed: float = 1.0) -> dict[str, Any]:
        pieces = chunks(text)
        if not pieces:
            return protocol.ok(spoken=0)
        with self._state_lock:
            gen = self._stop_gen
        with self._speak_lock:
            with self._state_lock:
                if gen != self._stop_gen:  # a stop arrived while we were queued
                    return protocol.ok(spoken=0, cancelled=True)
                cancel = self._cancel = threading.Event()
            q: queue.Queue[object] = queue.Queue(maxsize=8)

            def put(item: object) -> bool:
                while not cancel.is_set():
                    try:
                        q.put(item, timeout=0.1)
                        return True
                    except queue.Full:
                        continue
                return False

            def produce() -> None:
                try:
                    for piece in pieces:
                        for wave in self.tts.synth(piece, lang, voice, speed):
                            if not put(loudness(wave)):
                                return
                except Exception as e:
                    put(e)
                finally:
                    put(_END)

            threading.Thread(target=produce, name="tts-producer", daemon=True).start()

            def next_chunk() -> np.ndarray | None:
                while not cancel.is_set():
                    try:
                        item = q.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if item is _END:
                        return None
                    if isinstance(item, Exception):
                        raise item
                    return item  # type: ignore[return-value]
                return None

            self.sink.play(next_chunk, cancel)
            cancelled = cancel.is_set()
            cancel.set()  # release the producer if it is still running
            return protocol.ok(spoken=len(pieces), cancelled=cancelled)

    def transcribe(self, audio: np.ndarray, lang: str = "en") -> dict[str, Any]:
        segs = self.stt.transcribe(audio, lang)
        return protocol.ok(
            text=" ".join(s.text.strip() for s in segs).strip(),
            segments=[[s.start, s.end, s.text] for s in segs],
        )

    def handle(self, msg: dict[str, Any], payload: bytes = b"") -> dict[str, Any]:
        op = msg["op"]
        if op == "health":
            return self.health()
        if op == "stop":
            return self.stop()
        if op == "say":
            return self.say(msg["text"], msg.get("lang", "en"), msg.get("voice"), float(msg.get("speed", 1.0)))
        if op == "transcribe":
            return self.transcribe(np.frombuffer(payload, dtype=np.float32), msg.get("lang", "en"))
        raise protocol.ProtocolError(f"unhandled op {op!r}")


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        srv = cast("VoiceServer", self.server)
        try:
            msg = protocol.validate_request(protocol.decode(protocol.read_line(self.rfile)))
            if msg["op"] == "shutdown":
                self._reply(protocol.ok())
                threading.Thread(target=srv.shutdown, daemon=True).start()
                return
            payload = protocol.read_exact(self.rfile, msg["nbytes"]) if msg["op"] == "transcribe" else b""
            self._reply(srv.service.handle(msg, payload))
        except protocol.ProtocolError as e:
            self._reply(protocol.err(str(e)))
        except Exception as e:
            log.exception("request failed")
            self._reply(protocol.err(f"{type(e).__name__}: {e}"))

    def _reply(self, msg: dict[str, Any]) -> None:
        try:
            self.wfile.write(protocol.encode(msg))
        except OSError:
            pass  # client used --bg and hung up; nothing to report


class VoiceServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    # On Windows SO_REUSEADDR lets a second process bind the same port; never want that.
    allow_reuse_address = sys.platform != "win32"

    def __init__(self, service: VoiceService, host: str = paths.HOST, port: int | None = None) -> None:
        self.service = service
        super().__init__((host, paths.port() if port is None else port), _Handler)


def build_default(force_device: str | None = None, whisper_model: str = "small") -> VoiceService:  # pragma: no cover
    from .audio import Player
    from .device import probe
    from .engines import KokoroTTS, WhisperSTT

    dev = probe(force_device)
    return VoiceService(KokoroTTS(dev), WhisperSTT(dev, whisper_model), Player(), dev.describe())


def main(force_device: str | None = None, whisper_model: str = "small") -> None:  # pragma: no cover
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(paths.log_file(), encoding="utf-8"), logging.StreamHandler()],
    )
    service = build_default(force_device, whisper_model)
    with VoiceServer(service) as srv:
        log.info("listening on %s:%s device=%s", *srv.server_address, service.device)
        threading.Thread(target=service.warm, name="warmup", daemon=True).start()
        srv.serve_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
