"""Speaking-quality report from transcript segments. Pure."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

FILLERS: dict[str, tuple[str, ...]] = {
    "en": ("um", "uh", "like", "you know", "basically", "actually", "kind of"),
    "es": ("eh", "este", "o sea", "bueno", "pues", "digamos", "tipo"),
}


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Report:
    seconds: float
    words: int
    wpm: int
    pauses: list[tuple[float, float]] = field(default_factory=list)  # (at, length)
    fillers: dict[str, int] = field(default_factory=dict)
    target: int | None = None

    def render(self) -> str:
        head = f"time: {self.seconds:.0f}s"
        if self.target:
            head += f" / target {self.target}s"
        lines = [head, f"words: {self.words}  wpm: {self.wpm}"]
        if self.pauses:
            lines.append("pauses: " + ", ".join(f"{at:.0f}s ({n:.1f}s)" for at, n in self.pauses))
        if self.fillers:
            lines.append("fillers: " + ", ".join(f"{k} x{v}" for k, v in sorted(self.fillers.items())))
        return "\n".join(lines)


def count_fillers(text: str, lang: str) -> dict[str, int]:
    low = text.lower()
    out: dict[str, int] = {}
    for f in FILLERS.get(lang, FILLERS["en"]):
        n = len(re.findall(rf"(?<!\w){re.escape(f)}(?!\w)", low))
        if n:
            out[f] = n
    return out


def build(
    segments: list[Segment],
    seconds: float,
    lang: str,
    target: int | None = None,
    min_pause: float = 1.5,
) -> Report:
    text = " ".join(s.text.strip() for s in segments)
    words = len(text.split())
    wpm = round(words * 60 / seconds) if seconds > 0 else 0
    pauses = [
        (prev.end, nxt.start - prev.end)
        for prev, nxt in zip(segments, segments[1:])
        if nxt.start - prev.end >= min_pause
    ]
    return Report(seconds, words, wpm, pauses, count_fillers(text, lang), target)
