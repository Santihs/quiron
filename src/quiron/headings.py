"""Heading extraction from 02-Topics notes, and Ref: anchor resolution."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$", re.MULTILINE)
REF_LINE_RE = re.compile(r"^Ref:\s*`(.+)`\s*$", re.MULTILINE)

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


def extract_headings(body: str) -> list[Heading]:
    """All ## and ### headings in a topic note body, in document order."""
    out: list[Heading] = []
    for m in HEADING_RE.finditer(body):
        level = len(m.group(1))
        text = m.group(2)
        line_no = body.count("\n", 0, m.start()) + 1
        out.append(Heading(level=level, text=text, line_no=line_no))
    return out


def is_concept_heading(heading: Heading) -> bool:
    return normalize(heading.text) not in DENYLIST


def concept_headings(body: str) -> list[Heading]:
    return [h for h in extract_headings(body) if is_concept_heading(h)]


def extract_ref(card_body: str) -> str | None:
    """Return the raw backtick-wrapped content of the Ref: line, or None."""
    m = REF_LINE_RE.search(card_body)
    if not m:
        return None
    return m.group(1)


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


def resolve_anchor(anchor: str, headings: list[Heading]) -> Heading | None:
    """exact match -> prefix match -> None (unresolved)."""
    anchor_n = anchor.strip()
    for h in headings:
        if h.text.strip() == anchor_n:
            return h
    for h in headings:
        if h.text.strip().startswith(anchor_n):
            return h
    return None
