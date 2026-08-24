"""The 'understand vs recall' contradiction (v7 question #2).

You can hold factor:2300 in Anki (perfect recall) and sit at
understanding:encountered (never explained it). Anki alone can't see this —
it has no concept of "explained". The knowledge model alone can't either —
it has no idea you're acing the card. Only the cross-check can.

Deliberately conservative: this is NOT the lapses/card-quality signal
(that's Fase 3's audit.py, layer 2). This only asks "are you coasting on
Anki recall without ever having explained or applied the thing" — informational,
always yellow, never a verdict on the card itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schema import Concept, Knowledge
from .vault import Vault, read_note_id

FACTOR_THRESHOLD = 2500
INTERVAL_THRESHOLD = 21  # days


@dataclass(frozen=True)
class Contradiction:
    concept: Concept
    note_id: int
    factor: int
    interval: int


def collect_note_ids(vault: Vault, knowledge: Knowledge) -> dict[int, str]:
    """Maps noteId -> owning concept slug, for every card_ref in the model."""
    out: dict[int, str] = {}
    for c in knowledge.concepts:
        for cr in c.card_refs:
            note_id = read_note_id(vault, cr.path)
            if note_id is not None:
                out[note_id] = c.slug
    return out


def cross_check(knowledge: Knowledge, note_id_to_slug: dict[int, str], notes_info: dict[int, dict]) -> list[Contradiction]:
    """notes_info: noteId -> AnkiConnect cardsInfo dict, as returned by
    ankiconnect.cards_info_by_note_id. Empty/missing dict means Anki was
    unreachable — callers should pass {} rather than raise, and this
    function then simply finds nothing (never crashes on Anki being closed).
    """
    by_slug = {c.slug: c for c in knowledge.concepts}
    out: list[Contradiction] = []

    for note_id, card in notes_info.items():
        slug = note_id_to_slug.get(note_id)
        if slug is None:
            continue
        concept = by_slug.get(slug)
        if concept is None:
            continue
        if concept.understanding != "encountered":
            continue

        factor = card.get("factor")
        interval = card.get("interval")
        if factor is None or interval is None:
            continue
        if factor >= FACTOR_THRESHOLD and interval >= INTERVAL_THRESHOLD:
            out.append(
                Contradiction(concept=concept, note_id=note_id, factor=factor, interval=interval)
            )

    return out
