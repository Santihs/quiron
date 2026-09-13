"""Heading extraction from 02-Topics notes, and Ref: anchor resolution."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
REF_LINE_RE = re.compile(
    r"^\s*Ref:\s*(?:`([^`\r\n]+)`|([^`\r\n]+))\s*$",
    re.IGNORECASE | re.MULTILINE,
)
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")

EM_DASH = "—"

# Structural headings that are not concepts — normalized (no accents, lowercase).
DENYLIST = {
    "doubts resolved",
    "ver tambien",
    "implementacion",
    "implementacion propia",
    "por que importa para ml/ai",
    "resources",
    "recomendacion de recurso complementario",
    "proximo",
    "pendiente / proxima sesion",
    "core concepts to capture",
    "the key insight",
    "why it matters for ai",
    "visto en",
    "notas",
}


def normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.strip().lower()


def slugify(text: str) -> str:
    n = normalize(text)
    n = re.sub(r"[^a-z0-9]+", "-", n)
    return n.strip("-")


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    line_no: int  # 1-indexed


@dataclass(frozen=True)
class AnchorResolution:
    status: Literal["exact", "prefix", "ambiguous", "unresolved"]
    heading: Heading | None = None
    matches: tuple[Heading, ...] = ()


def extract_headings(body: str) -> list[Heading]:
    """All ## and ### headings in a topic note body, in document order."""
    out: list[Heading] = []
    fence: str | None = None
    for line_no, line in enumerate(body.replace("\r\n", "\n").split("\n"), start=1):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence is not None:
            continue
        m = HEADING_RE.match(line)
        if not m:
            continue
        level = len(m.group(1))
        text = m.group(2)
        out.append(Heading(level=level, text=text, line_no=line_no))
    return out


def is_concept_heading(heading: Heading) -> bool:
    return normalize(heading.text) not in DENYLIST


def concept_headings(body: str) -> list[Heading]:
    return [h for h in extract_headings(body) if is_concept_heading(h)]


def extract_ref(card_body: str) -> str | None:
    """Return the raw backtick-wrapped content of the Ref: line, or None."""
    fence: str | None = None
    for line in card_body.replace("\r\n", "\n").split("\n"):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence is not None:
            continue
        m = REF_LINE_RE.match(line)
        if m:
            return (m.group(1) or m.group(2)).strip()
    return None


def parse_ref(ref_content: str) -> tuple[str, str | None]:
    """Split 'path — anchor — with — dashes' into (path, anchor_or_None).

    The path never contains ' — '; anchors can (e.g. '8.3 — Orthogonality'),
    so we split on ALL occurrences and treat everything after the first part
    as the anchor. If the first part doesn't look like a path (.md/.py), the
    whole content is returned as path with anchor=None — caller decides
    whether that's resolvable.
    """
    sep = f" {EM_DASH} "
    if sep not in ref_content:
        return ref_content.strip(), None
    parts = ref_content.split(sep)
    path = parts[0].strip()
    if not (path.endswith(".md") or path.endswith(".py")):
        return ref_content.strip(), None
    anchor = sep.join(parts[1:]).strip()
    return path, anchor


def resolve_anchor_detailed(anchor: str, headings: list[Heading]) -> AnchorResolution:
    """Resolve exact, unique-prefix, ambiguous, and unresolved anchors."""
    anchor_n = anchor.strip()
    exact = tuple(h for h in headings if h.text.strip() == anchor_n)
    if len(exact) == 1:
        return AnchorResolution(status="exact", heading=exact[0], matches=exact)
    if len(exact) > 1:
        return AnchorResolution(status="ambiguous", matches=exact)

    prefix = tuple(h for h in headings if h.text.strip().startswith(anchor_n))
    if len(prefix) == 1:
        return AnchorResolution(status="prefix", heading=prefix[0], matches=prefix)
    if len(prefix) > 1:
        return AnchorResolution(status="ambiguous", matches=prefix)
    return AnchorResolution(status="unresolved")


def resolve_anchor(anchor: str, headings: list[Heading]) -> Heading | None:
    """Return a uniquely resolved exact or prefix anchor."""
    result = resolve_anchor_detailed(anchor, headings)
    return result.heading
