"""Daemon behaviour with fake engines over a real localhost socket."""

from __future__ import annotations

import threading
import time

import numpy as np
import pytest

from quiron_voice import client, protocol
from quiron_voice.metrics import Segment
from quiron_voice.server import VoiceServer, VoiceService


class FakeTTS:
    rate = 24_000

    def __init__(self, delay: float = 0.0, fail: bool = False):
        self.delay, self.fail, self.loaded = delay, fail, False
        self.calls: list[tuple[str, str]] = []

    def load(self):
        if self.fail:
            raise RuntimeError("no gpu")
        self.loaded = True

    def synth(self, text, lang, voice, speed):
        self.calls.append((text, lang))
        time.sleep(self.delay)
        yield np.full(240, 0.5, dtype=np.float32)


class FakeSTT:
    def load(self):
        pass

    def transcribe(self, audio, lang):
        return [Segment(0.0, len(audio) / 16000, f"{lang}:{len(audio)}")]


class FakeSink:
    def __init__(self, hold: threading.Event | None = None):
        self.played: list[np.ndarray] = []
        self.hold = hold
        self.started = threading.Event()

    def play(self, next_chunk, cancel):
        self.started.set()
        while (w := next_chunk()) is not None:
            self.played.append(w)
            if self.hold:
                while not self.hold.is_set() and not cancel.is_set():
                    time.sleep(0.01)


@pytest.fixture
def running():
    def start(service: VoiceService):
        srv = VoiceServer(service, port=0)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        servers.append(srv)
        return srv.server_address[1]

    servers: list[VoiceServer] = []
    yield start
    for s in servers:
        s.shutdown()
        s.server_close()


def test_say_plays_each_sentence_normalized():
    sink = FakeSink()
    svc = VoiceService(FakeTTS(), FakeSTT(), sink)
    resp = svc.say("Uno. Dos.", "es")
    assert resp == {"ok": True, "spoken": 2, "cancelled": False}
    assert len(sink.played) == 2
    assert np.abs(sink.played[0]).max() == pytest.approx(0.97 * np.tanh(2.5), rel=1e-5)
    assert svc.tts.calls == [("Uno.", "es"), ("Dos.", "es")]


def test_say_empty_text_is_noop():
    assert VoiceService(FakeTTS(), FakeSTT(), FakeSink()).say("   ") == {"ok": True, "spoken": 0}


def test_stop_interrupts_current_and_cancels_queued():
    hold = threading.Event()
    sink = FakeSink(hold)
    svc = VoiceService(FakeTTS(), FakeSTT(), sink)
    results: dict[str, dict] = {}
    t1 = threading.Thread(target=lambda: results.__setitem__("a", svc.say("Uno. Dos. Tres.")))
    t1.start()
    assert sink.started.wait(2)
    t2 = threading.Thread(target=lambda: results.__setitem__("b", svc.say("Queued.")))
    t2.start()
    time.sleep(0.05)
    svc.stop()
    t1.join(2), t2.join(2)
    assert results["a"]["cancelled"] is True
    assert results["b"] == {"ok": True, "spoken": 0, "cancelled": True}
    assert len(sink.played) == 1


def test_synth_error_surfaces():
    class Boom(FakeTTS):
        def synth(self, *a):
            raise RuntimeError("kaboom")
            yield  # pragma: no cover

    svc = VoiceService(Boom(), FakeSTT(), FakeSink())
    with pytest.raises(RuntimeError, match="kaboom"):
        svc.say("Hi.")


def test_warm_reports_partial_failure():
    svc = VoiceService(FakeTTS(fail=True), FakeSTT(), FakeSink(), device="cpu")
    svc.warm()
    h = svc.health()
    assert h["models"]["tts"].startswith("error") and h["models"]["stt"] == "ready"
    assert h["device"] == "cpu"


def test_socket_round_trip(running):
    port = running(VoiceService(FakeTTS(), FakeSTT(), FakeSink(), device="fake"))
    assert client.request({"op": "health"}, port=port)["device"] == "fake"
    assert client.request({"op": "say", "text": "Hola."}, port=port)["spoken"] == 1
    audio = np.zeros(1600, dtype=np.float32).tobytes()
    resp = client.request({"op": "transcribe", "lang": "es", "nbytes": len(audio)}, audio, port=port)
    assert resp["text"] == "es:1600" and resp["segments"][0][2] == "es:1600"


def test_socket_rejects_bad_requests(running):
    port = running(VoiceService(FakeTTS(), FakeSTT(), FakeSink()))
    resp = client.request({"op": "launch-missiles"}, port=port)
    assert resp["ok"] is False and "unknown op" in resp["error"]


def test_fire_and_forget_does_not_break_server(running):
    sink = FakeSink()
    port = running(VoiceService(FakeTTS(delay=0.05), FakeSTT(), sink))
    assert client.request({"op": "say", "text": "Bg."}, wait=False, port=port) is None
    deadline = time.time() + 2
    while not sink.played and time.time() < deadline:
        time.sleep(0.01)
    assert sink.played
    assert client.request({"op": "health"}, port=port)["ok"]


def test_ensure_server_spawns_and_polls(monkeypatch):
    # Bound-but-not-serving accepts connections into the backlog and never replies,
    # exactly like a wedged daemon: health must time out, not hang.
    monkeypatch.setattr(client, "HEALTH_TIMEOUT", 0.2)
    service = VoiceService(FakeTTS(), FakeSTT(), FakeSink(), device="spawned")
    srv = VoiceServer(service, port=0)
    port = srv.server_address[1]
    spawned: list[bool] = []

    def spawn():
        spawned.append(True)
        threading.Thread(target=srv.serve_forever, daemon=True).start()

    # A closed port refuses connections, so ensure_server must give up.
    dead = VoiceServer(service, port=0)
    dead_port = dead.server_address[1]
    dead.server_close()
    with pytest.raises(client.ServerUnavailable):
        client.ensure_server(port=dead_port, spawn=lambda: None, wait_s=0.2, poll_s=0.05)

    h = client.ensure_server(port=port, spawn=spawn, wait_s=2, poll_s=0.05)
    assert h["device"] == "spawned"
    srv.shutdown()
    srv.server_close()


def test_wait_ready(running):
    svc = VoiceService(FakeTTS(), FakeSTT(), FakeSink())
    port = running(svc)
    with pytest.raises(client.ServerUnavailable, match="still cold"):
        client.wait_ready("stt", port=port, wait_s=0, poll_s=0)
    svc.models["stt"] = "error: boom"
    with pytest.raises(client.ServerUnavailable, match="boom"):
        client.wait_ready("stt", port=port)
    svc.models["stt"] = "ready"
    client.wait_ready("stt", port=port)


def test_shutdown_op():
    svc = VoiceService(FakeTTS(), FakeSTT(), FakeSink())
    srv = VoiceServer(svc, port=0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    assert client.request({"op": "shutdown"}, port=srv.server_address[1]) == protocol.ok()
    t.join(2)
    assert not t.is_alive()
    srv.server_close()
