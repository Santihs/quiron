"""Fase 4 — the deterministic half of "quiz-me produces explained evidence".

Judgment (did the user actually explain it correctly?) happens in quiz-me.md,
outside this module entirely. This module only resolves which concept a card
belongs to and appends the Evidence record — same split as every prior
phase's skill/Python boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .cardmap import card_to_concept
from .schema import Evidence, Knowledge


@dataclass(frozen=True)
class AddEvidenceResult:
    slug: str | None
    concept_title: str | None


def add_evidence(
    knowledge: Knowledge,
    card_path: str,
    kind: str,
    ref: str,
    scope: str | None = None,
    today: date | None = None,
) -> AddEvidenceResult:
    """Resolves card_path -> concept via card_to_concept, appends
    Evidence(kind, at=today or date.today(), ref, scope) to that concept.

    An unmapped card_path is reported (slug=None) and knowledge is left
    untouched — never raises. A card whose Ref: never resolved to a concept
    is a known Fase-1 possibility, already surfaced by doctor/today; this is
    not the place to fail on it.
    """
    by_path = card_to_concept(knowledge)
    slug = by_path.get(card_path)
    if slug is None:
        return AddEvidenceResult(slug=None, concept_title=None)

    concept = next(c for c in knowledge.concepts if c.slug == slug)
    concept.evidence.append(
        Evidence(kind=kind, at=today or date.today(), ref=ref, scope=scope)
    )
    return AddEvidenceResult(slug=slug, concept_title=concept.title)
