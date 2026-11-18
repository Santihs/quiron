import io

import numpy as np
import pytest

from quiron_voice import protocol
from quiron_voice.audio import SilenceDetector, beep, loudness, rms, trim_trailing_silence
from quiron_voice.device import choose
from quiron_voice.engines import resolve_voice
from quiron_voice.metrics import Segment, build, count_fillers


# --- device -------------------------------------------------------------------
@pytest.mark.parametrize(
    "cuda,mps,force,expected",
    [
        (True, False, None, ("cuda", "cuda", "float16")),
        (True, True, None, ("cuda", "cuda", "float16")),
        (False, True, None, ("mps", "cpu", "int8")),
        (False, False, None, ("cpu", "cpu", "int8")),
        (True, False, "cpu", ("cpu", "cpu", "int8")),
        (False, False, "CUDA", ("cuda", "cuda", "float16")),
    ],
)
def test_device_choice(cuda, mps, force, expected):
    d = choose(cuda, mps, force)
    assert (d.torch, d.whisper, d.compute_type) == expected


def test_device_rejects_unknown():
    with pytest.raises(ValueError):
        choose(True, False, "tpu")


# --- protocol -----------------------------------------------------------------
def test_protocol_round_trip_unicode():
    msg = {"op": "say", "text": "¿qué tal? ŷ"}
    assert protocol.decode(protocol.encode(msg)) == msg


@pytest.mark.parametrize("line", [b"", b"not json\n", b"[1,2]\n", b"\xff\n"])
def test_protocol_decode_errors(line):
    with pytest.raises(protocol.ProtocolError):
        protocol.decode(line)


@pytest.mark.parametrize(
    "msg",
    [
        {"op": "nope"},
        {"op": "say"},
        {"op": "transcribe"},
        {"op": "transcribe", "nbytes": -4},
        {"op": "transcribe", "nbytes": 3},
        {"op": "transcribe", "nbytes": True},
        {"op": "transcribe", "nbytes": protocol.MAX_AUDIO + 4},
    ],
)
def test_protocol_invalid_requests(msg):
    with pytest.raises(protocol.ProtocolError):
        protocol.validate_request(msg)


def test_protocol_read_exact_and_truncation():
    assert protocol.read_exact(io.BytesIO(b"abcdef"), 4) == b"abcd"
    with pytest.raises(protocol.ProtocolError):
        protocol.read_exact(io.BytesIO(b"ab"), 4)


def test_protocol_line_limit():
    with pytest.raises(protocol.ProtocolError):
        protocol.read_line(io.BytesIO(b"x" * (protocol.MAX_LINE + 10)))


# --- audio DSP ------------------------------------------------------------------
def test_loudness_bounds_and_silence():
    w = loudness(np.array([0.0, 0.01, -0.02], dtype=np.float32))
    assert np.abs(w).max() <= 0.97 + 1e-6 and np.abs(w).max() > 0.9
    assert not loudness(np.zeros(10)).any()
    assert loudness(np.zeros(0)).size == 0


def test_beep_shape():
    b = beep(seconds=0.1, rate=1000)
    assert b.shape == (100,) and b.dtype == np.float32 and abs(b[0]) < 1e-3


def _tone(sec, amp=0.1, rate=16000):
    return (amp * np.sin(np.linspace(0, 2 * np.pi * 200 * sec, int(rate * sec)))).astype(np.float32)


def _quiet(sec, rate=16000):
    return np.zeros(int(rate * sec), dtype=np.float32)


def _feed(det, pieces, step=0.5):
    for i, p in enumerate(pieces):
        if det.feed(p):
            return i
    return None


def test_silence_detector_stops_after_speech_then_quiet():
    det = SilenceDetector(silence_s=1.0)
    pieces = [_tone(0.5)] * 2 + [_quiet(0.5)] * 4
    assert _feed(det, pieces) == 3  # 2 speech chunks + 1.0 s quiet
    assert det.heard_speech and det.quiet == pytest.approx(1.0)


def test_silence_detector_waits_for_speech_then_gives_up():
    det = SilenceDetector(silence_s=1.0, lead_s=2.0)
    assert _feed(det, [_quiet(0.5)] * 10) == 3  # 2.0 s of nobody talking


def test_silence_detector_short_pause_does_not_stop():
    det = SilenceDetector(silence_s=1.0)
    pieces = [_tone(0.5), _quiet(0.5), _tone(0.5), _quiet(0.5), _tone(0.5)]
    assert _feed(det, pieces) is None


def test_silence_detector_max():
    det = SilenceDetector(max_s=1.0)
    assert _feed(det, [_tone(0.5)] * 5) == 1


def test_trim_and_rms():
    a = np.ones(16000 * 3, dtype=np.float32)
    assert len(trim_trailing_silence(a, quiet_s=2.0)) == 16000 * 3 - int(1.7 * 16000)
    assert len(trim_trailing_silence(a, quiet_s=0.1)) == len(a)
    assert rms(np.zeros(0)) == 0.0


# --- engines / metrics ------------------------------------------------------------
def test_resolve_voice():
    assert resolve_voice("es", None) == ("e", "ef_dora")
    assert resolve_voice("en", "am_adam") == ("a", "am_adam")
    with pytest.raises(ValueError):
        resolve_voice("fr", None)


def test_fillers_word_boundaries():
    assert count_fillers("Este, o sea, este testeo", "es") == {"este": 2, "o sea": 1}
    assert count_fillers("I like umbrellas, um", "en") == {"like": 1, "um": 1}


def test_metrics_report():
    segs = [Segment(0, 2, "one two three"), Segment(4.0, 5, "four"), Segment(5.2, 6, "five um")]
    r = build(segs, seconds=30, lang="en", target=60)
    assert r.words == 6 and r.wpm == 12
    assert r.pauses == [(2, 2.0)]
    assert r.fillers == {"um": 1}
    out = r.render()
    assert "target 60s" in out and "wpm: 12" in out and "um x1" in out


def test_metrics_zero_seconds():
    assert build([], 0, "en").wpm == 0
