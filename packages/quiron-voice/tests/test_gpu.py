"""Real-model smoke tests. Skipped by default; run with `pytest -m gpu`.

Needs the `all` extra installed. Latency assertions are benchmarks, not
correctness: they only run with QV_BENCH=1 on an otherwise idle GPU (a game or
live wallpaper at 99% GPU makes them meaningless).
"""

from __future__ import annotations

import os
import time

import numpy as np
import pytest

from quiron_voice.device import probe

pytestmark = pytest.mark.gpu
BENCH = os.environ.get("QV_BENCH") == "1"


@pytest.fixture(scope="module")
def device():
    pytest.importorskip("torch")
    pytest.importorskip("faster_whisper")
    return probe()


@pytest.fixture(scope="module")
def tts(device):
    from quiron_voice.engines import KokoroTTS

    engine = KokoroTTS(device)
    engine.load()
    return engine


@pytest.fixture(scope="module")
def stt(device):
    from quiron_voice.engines import WhisperSTT

    engine = WhisperSTT(device)
    engine.load()
    return engine


def test_device_uses_gpu_when_present(device):
    import torch  # pyright: ignore[reportMissingImports]  (gpu extra)

    if torch.cuda.is_available():
        assert device.torch == "cuda" and device.compute_type == "float16"


@pytest.mark.parametrize("lang,text", [("en", "The mean squared error is thirteen."), ("es", "El error cuadrático medio es trece.")])
def test_tts_synthesizes_speech(tts, lang, text):
    t0 = time.perf_counter()
    waves = list(tts.synth(text, lang, None, 1.0))
    elapsed = time.perf_counter() - t0
    audio = np.concatenate(waves)
    seconds = len(audio) / tts.rate
    assert 1.0 < seconds < 10.0
    assert np.abs(audio).max() > 0.01
    if BENCH and tts.device.torch == "cuda":
        assert elapsed < seconds, f"slower than real time: {elapsed:.2f}s for {seconds:.2f}s audio"


def test_round_trip_tts_to_stt(tts, stt):
    """Speak a sentence, resample 24k -> 16k, transcribe it back."""
    audio = np.concatenate(list(tts.synth("Gradient descent lowers the error.", "en", None, 1.0)))
    idx = np.linspace(0, len(audio) - 1, int(len(audio) * 16_000 / tts.rate))
    audio16 = np.interp(idx, np.arange(len(audio)), audio).astype(np.float32)

    t0 = time.perf_counter()
    text = " ".join(s.text for s in stt.transcribe(audio16, "en")).lower()
    elapsed = time.perf_counter() - t0

    assert "gradient" in text and "error" in text
    if BENCH and stt.device.whisper == "cuda":
        audio_s = len(audio16) / 16_000
        assert elapsed < 0.5 * audio_s, f"warm STT {elapsed:.2f}s for {audio_s:.2f}s audio"
