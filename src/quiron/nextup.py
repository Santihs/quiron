"""quiron next — candidates, not a schedule (v7 question #4).

A candidate is a concept with an open signal: an open doubt, a coverage
gap, a prerequisite just satisfied, or no `explained` evidence yet. One
hard filter — blocked, meaning a prerequisite hasn't reached explained.
The rest rank by urgency; this produces a short list, it does not decide,
and it says nothing about when to review.

Module named nextup, not next, to avoid shadowing the builtin — the CLI
subcommand itself is still `quiron next`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .coverage import coverage_gap
from .schema import Concept, Knowledge

DONE = ("explained", "applied")


def is_blocked(concept: Concept, by_slug: dict[str, Concept]) -> bool:
    """Block until every prerequisite exists and reaches explained evidence."""
    for slug in concept.prerequisites:
        prereq = by_slug.get(slug)
        if prereq is None or prereq.understanding not in DONE:
            return True
    return False


@dataclass(frozen=True)
class Candidate:
    slug: str
    title: str
    reason: str  # open_doubt | unblocked | coverage_gap | no_explained
    detail: str = ""


def candidates(knowledge: Knowledge, today: date | None = None) -> list[Candidate]:
    today = today or date.today()
    by_slug = {c.slug: c for c in knowledge.concepts}
    gap_slugs = {c.slug for c in coverage_gap(knowledge)}

    open_doubt: list[tuple[int, Candidate]] = []
    unblocked: list[Candidate] = []
    gap: list[Candidate] = []
    no_explained: list[Candidate] = []

    for concept in knowledge.concepts:
        if is_blocked(concept, by_slug):
            continue

        open_doubts = [d for d in concept.doubts if d.status == "open"]
        if open_doubts:
            oldest = min(open_doubts, key=lambda d: d.raised_at)
            age = (today - oldest.raised_at).days
            open_doubt.append(
                (age, Candidate(concept.slug, concept.title, "open_doubt", f"{age}d"))
            )
            continue

        if concept.prerequisites and concept.understanding not in DONE:
            unblocked.append(Candidate(concept.slug, concept.title, "unblocked"))
            continue

        if concept.slug in gap_slugs:
            gap.append(Candidate(concept.slug, concept.title, "coverage_gap"))
            continue

        if concept.understanding not in DONE:
            no_explained.append(Candidate(concept.slug, concept.title, "no_explained"))

    open_doubt.sort(key=lambda pair: -pair[0])
    return [c for _, c in open_doubt] + unblocked + gap + no_explained
