"""Engine interfaces plus the real Kokoro (TTS) and faster-whisper (STT) backends.

The daemon only depends on the `TTS`/`STT` protocols, so tests inject fakes and
the heavy imports (torch, kokoro, ctranslate2) happen only inside `load()`.
"""

from __future__ import annotations

import glob
import os
import sys
import threading
from collections.abc import Iterator
from typing import Protocol

import numpy as np

from .device import Device
from .metrics import Segment

VOICES = {"en": ("a", "af_heart"), "es": ("e", "ef_dora")}


class TTS(Protocol):
    rate: int

    def load(self) -> None: ...
    def synth(self, text: str, lang: str, voice: str | None, speed: float) -> Iterator[np.ndarray]: ...


class STT(Protocol):
    def load(self) -> None: ...
    def transcribe(self, audio: np.ndarray, lang: str) -> list[Segment]: ...


def resolve_voice(lang: str, voice: str | None) -> tuple[str, str]:
    """Map our language code to Kokoro's lang_code and a default voice."""
    if lang not in VOICES:
        raise ValueError(f"unsupported language {lang!r}; expected one of {sorted(VOICES)}")
    code, default = VOICES[lang]
    return code, voice or default


def add_nvidia_dll_dirs() -> None:  # pragma: no cover - Windows + pip CUDA wheels
    """CTranslate2 on Windows can't find pip-installed cuBLAS/cuDNN DLLs by itself."""
    if sys.platform != "win32":
        return
    for base in sys.path:
        for d in glob.glob(os.path.join(base, "nvidia", "*", "bin")):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")


class KokoroTTS:  # pragma: no cover - real model
    rate = 24_000

    def __init__(self, device: Device, repo: str = "hexgrad/Kokoro-82M") -> None:
        self.device, self.repo = device, repo
        self._pipes: dict[str, object] = {}
        self._lock = threading.Lock()

    def load(self) -> None:
        with self._lock:
            if self._pipes:
                return
            import torch  # pyright: ignore[reportMissingImports]  (tts extra)
            from kokoro import KModel, KPipeline  # pyright: ignore[reportMissingImports]

            torch.set_grad_enabled(False)
            model = KModel(repo_id=self.repo).to(self.device.torch).eval()
            for lang, (code, voice) in VOICES.items():
                pipe = KPipeline(lang_code=code, repo_id=self.repo, model=model)
                list(pipe("Hi.", voice=voice))  # warm up kernels + load voice pack
                self._pipes[lang] = pipe

    def synth(self, text: str, lang: str, voice: str | None, speed: float) -> Iterator[np.ndarray]:
        self.load()
        _, voice = resolve_voice(lang, voice)
        pipe = self._pipes[lang]
        for result in pipe(text, voice=voice, speed=speed):  # type: ignore[operator]
            if result.audio is not None:
                yield result.audio.detach().cpu().numpy().astype(np.float32)


class WhisperSTT:  # pragma: no cover - real model
    def __init__(self, device: Device, model: str = "small") -> None:
        self.device, self.model_name = device, model
        self._model = None
        self._lock = threading.Lock()

    def load(self) -> None:
        with self._lock:
            if self._model is not None:
                return
            add_nvidia_dll_dirs()
            from faster_whisper import WhisperModel  # pyright: ignore[reportMissingImports]  (stt extra)

            self._model = WhisperModel(
                self.model_name, device=self.device.whisper, compute_type=self.device.compute_type
            )
            self._model.transcribe(np.zeros(16_000, dtype=np.float32), language="en")  # warm up

    def transcribe(self, audio: np.ndarray, lang: str) -> list[Segment]:
        self.load()
        assert self._model is not None
        segments, _info = self._model.transcribe(
            audio, language=lang, beam_size=1, vad_filter=True, condition_on_previous_text=False
        )
        return [Segment(s.start, s.end, s.text) for s in segments]
