"""quiron sources — source yield, a query not a feature (v7 question #5).

GROUP BY sources.ref. Not "Axler is better" — it says this material is
turning into usable knowledge, or you're mostly just consuming it.
Derived at query time, never stored.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schema import Knowledge

DONE = ("explained", "applied")


@dataclass(frozen=True)
class SourceYield:
    ref: str
    concept_count: int
    explained_count: int
    applied_count: int


def yield_by_source(knowledge: Knowledge) -> list[SourceYield]:
    """A concept with two Sources contributes to both rows' concept_count."""
    concepts_count: dict[str, int] = {}
    explained_count: dict[str, int] = {}
    applied_count: dict[str, int] = {}

    for concept in knowledge.concepts:
        understanding = concept.understanding
        for source in concept.sources:
            concepts_count[source.ref] = concepts_count.get(source.ref, 0) + 1
            if understanding in DONE:
                explained_count[source.ref] = explained_count.get(source.ref, 0) + 1
            if understanding == "applied":
                applied_count[source.ref] = applied_count.get(source.ref, 0) + 1

    rows = [
        SourceYield(
            ref=ref,
            concept_count=count,
            explained_count=explained_count.get(ref, 0),
            applied_count=applied_count.get(ref, 0),
        )
        for ref, count in concepts_count.items()
    ]
    rows.sort(key=lambda r: -r.concept_count)
    return rows
