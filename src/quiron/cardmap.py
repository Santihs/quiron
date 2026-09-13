"""Shared card_path -> concept_slug lookup.

Extracted because three callers need the exact same walk over
knowledge.concepts -> card_refs: audit.py's candidate/informational
resolution, recall.py's note-id collection, and evidence.py's
card-to-concept resolution for --add. Same precedent as vault.read_note_id
in Fase 3 — a second private copy is tolerated, a third is not.
"""

from __future__ import annotations

from .schema import Knowledge


def card_to_concept(knowledge: Knowledge) -> dict[str, str]:
    """card_path -> owning concept slug, for every card_ref in the model."""
    out: dict[str, str] = {}
    for c in knowledge.concepts:
        for cr in c.card_refs:
            out.setdefault(cr.path, c.slug)
    return out


def duplicate_card_paths(knowledge: Knowledge) -> dict[str, list[str]]:
    """Return card paths assigned to more than one concept, deterministically."""
    owners: dict[str, list[str]] = {}
    for concept in knowledge.concepts:
        for card in concept.card_refs:
            owners.setdefault(card.path, []).append(concept.slug)
    return {path: slugs for path, slugs in owners.items() if len(slugs) > 1}
