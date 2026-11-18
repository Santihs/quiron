"""Pick the fastest available compute device. `choose` is pure; `probe` touches hardware."""

from __future__ import annotations

from dataclasses import dataclass

DEVICES = ("cuda", "mps", "cpu")


@dataclass(frozen=True)
class Device:
    torch: str  # Kokoro: "cuda" | "mps" | "cpu"
    whisper: str  # CTranslate2 has no mps backend: "cuda" | "cpu"
    compute_type: str  # "float16" on GPU, "int8" on CPU

    def describe(self) -> str:
        return f"tts={self.torch} stt={self.whisper}/{self.compute_type}"


def choose(cuda: bool, mps: bool, force: str | None = None) -> Device:
    """Prefer cuda, then mps, then cpu. `force` overrides what the probe found."""
    if force:
        force = force.lower()
        if force not in DEVICES:
            raise ValueError(f"unknown device {force!r}; expected one of {DEVICES}")
        cuda, mps = force == "cuda", force == "mps"
    if cuda:
        return Device("cuda", "cuda", "float16")
    if mps:
        return Device("mps", "cpu", "int8")
    return Device("cpu", "cpu", "int8")


def probe(force: str | None = None) -> Device:  # pragma: no cover - hardware
    cuda = mps = False
    try:
        import torch  # pyright: ignore[reportMissingImports]  (optional extra)

        cuda = torch.cuda.is_available()
        mps = torch.backends.mps.is_available()
    except ImportError:
        try:
            import ctranslate2  # pyright: ignore[reportMissingImports]

            cuda = ctranslate2.get_cuda_device_count() > 0
        except ImportError:
            pass
    return choose(cuda, mps, force)
