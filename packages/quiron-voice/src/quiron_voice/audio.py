"""Audio I/O. DSP helpers are pure numpy; device access goes through sounddevice.

sounddevice wraps PortAudio, so the same code drives WASAPI (Windows),
PulseAudio/PipeWire/ALSA (Debian) and CoreAudio (macOS).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

TTS_RATE = 24_000  # Kokoro output
STT_RATE = 16_000  # Whisper input


def loudness(wave: np.ndarray, drive: float = 2.5, ceiling: float = 0.97) -> np.ndarray:
    """Peak-normalize then soft-clip with tanh: louder speech, no hard clipping."""
    w = np.asarray(wave, dtype=np.float32)
    if w.size == 0:
        return w
    peak = float(np.abs(w).max())
    if peak < 1e-9:
        return np.zeros_like(w)
    return (np.tanh(drive * w / peak) * ceiling).astype(np.float32)


def beep(freq: float = 880.0, seconds: float = 0.12, rate: int = TTS_RATE, volume: float = 0.4) -> np.ndarray:
    t = np.arange(int(rate * seconds), dtype=np.float32) / rate
    fade = np.minimum(1.0, np.minimum(t, t[::-1]) / 0.01).astype(np.float32)
    return (np.sin(2 * np.pi * freq * t) * fade * volume).astype(np.float32)


def rms(chunk: np.ndarray) -> float:
    c = np.asarray(chunk, dtype=np.float32)
    return float(np.sqrt(np.mean(c * c))) if c.size else 0.0


@dataclass
class SilenceDetector:
    """Decide when a spoken answer is over.

    Recording stops once speech has been heard and `silence_s` of quiet follows,
    or when `max_s` is reached. Quiet before any speech never stops it, except
    `lead_s` of total silence (nobody answered).
    """

    rate: int = STT_RATE
    silence_s: float = 3.0
    max_s: float = 240.0
    lead_s: float = 15.0
    threshold: float = 0.012

    def __post_init__(self) -> None:
        self.elapsed = 0.0
        self.quiet = 0.0
        self.heard_speech = False

    def feed(self, chunk: np.ndarray) -> bool:
        """Consume one chunk; return True when recording should stop."""
        dt = len(chunk) / self.rate
        self.elapsed += dt
        if rms(chunk) >= self.threshold:
            self.heard_speech = True
            self.quiet = 0.0
        else:
            self.quiet += dt
        if self.elapsed >= self.max_s:
            return True
        if self.heard_speech:
            return self.quiet >= self.silence_s
        return self.elapsed >= self.lead_s


def trim_trailing_silence(audio: np.ndarray, quiet_s: float, rate: int = STT_RATE, keep_s: float = 0.3) -> np.ndarray:
    cut = int(max(0.0, quiet_s - keep_s) * rate)
    return audio[: len(audio) - cut] if 0 < cut < len(audio) else audio


class Player:  # pragma: no cover - needs an audio device
    """Streams float32 mono chunks to the default output, interruptible."""

    def __init__(self, rate: int = TTS_RATE) -> None:
        import sounddevice as sd

        self._sd = sd
        self.rate = rate

    def play(self, next_chunk: Callable[[], np.ndarray | None], cancel: threading.Event) -> None:
        """Pull chunks until None (end) or `cancel` is set."""
        with self._sd.OutputStream(samplerate=self.rate, channels=1, dtype="float32") as out:
            while not cancel.is_set():
                w = next_chunk()
                if w is None:
                    break
                step = self.rate // 10  # 100 ms writes keep `stop` responsive
                for i in range(0, len(w), step):
                    if cancel.is_set():
                        out.abort()
                        return
                    out.write(w[i : i + step].reshape(-1, 1))

    def play_once(self, wave: np.ndarray) -> None:
        self._sd.play(wave, self.rate, blocking=True)


def record(
    detector: SilenceDetector,
    on_start: Callable[[], None] | None = None,
    chunk_s: float = 0.25,
) -> tuple[np.ndarray, float]:  # pragma: no cover - needs a microphone
    """Record mono float32 at detector.rate until the detector says stop.

    Returns (audio with trailing silence trimmed, wall seconds spoken).
    """
    import sounddevice as sd

    frames: list[np.ndarray] = []
    blocksize = int(detector.rate * chunk_s)
    started = time.perf_counter()
    with sd.InputStream(samplerate=detector.rate, channels=1, dtype="float32", blocksize=blocksize) as stream:
        if on_start:
            on_start()
        while True:
            data, _overflow = stream.read(blocksize)
            mono = data[:, 0].copy()
            frames.append(mono)
            if detector.feed(mono):
                break
    audio = np.concatenate(frames) if frames else np.zeros(0, dtype=np.float32)
    audio = trim_trailing_silence(audio, detector.quiet, detector.rate)
    spoken = max(0.0, time.perf_counter() - started - detector.quiet)
    return audio, spoken
