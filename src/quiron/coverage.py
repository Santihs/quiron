"""Coverage queries and the interactive retention-decision walker.

A concept with no cards is never red (v7's hard tier rule) — this module
only produces yellow-tier data. Deciding needed/declined is a human call;
quiron never infers it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .schema import Concept, Knowledge


def coverage_gap(knowledge: Knowledge) -> list[Concept]:
    """Concepts you decided need cards, but don't have any yet."""
    return [c for c in knowledge.concepts if c.card_policy == "needed" and not c.card_refs]


def undecided(knowledge: Knowledge) -> list[Concept]:
    """Concepts with no retention decision at all."""
    return [c for c in knowledge.concepts if c.card_policy == "undecided"]


@dataclass
class DecideReport:
    decided: int = 0
    quit_early: bool = False
    slugs_decided: list[str] = field(default_factory=list)


def decide(
    knowledge: Knowledge,
    input_fn: Callable[[], str] | None = None,
    print_fn: Callable[[str], None] = print,
) -> DecideReport:
    """Walk undecided concepts one at a time. Never blocks on a full pass —
    quitting mid-walk keeps everything decided so far and leaves the rest
    undecided, same as an unprocessed inbox entry: safe to leave dirty.

    input_fn defaults to None rather than `input` directly so tests that
    monkeypatch builtins.input still take effect — a bound default would
    freeze the reference at import time, before the patch exists.
    """
    if input_fn is None:
        input_fn = input
    report = DecideReport()
    pending = sorted(undecided(knowledge), key=lambda c: c.slug)
    total = len(pending)

    for i, concept in enumerate(pending, start=1):
        print_fn(f"[{i}/{total}] {concept.title} ({concept.notes_ref})")
        print_fn(f"  {len(concept.card_refs)} tarjetas existentes")
        answer = input_fn().strip().lower()

        if answer in ("q", "quit"):
            report.quit_early = True
            break
        if answer in ("n", "needed"):
            concept.card_policy = "needed"
        elif answer in ("d", "declined"):
            concept.card_policy = "declined"
            reason = input_fn().strip()
            concept.declined_reason = reason or None
        else:
            # s / skip / empty / anything else: stays undecided
            continue

        report.decided += 1
        report.slugs_decided.append(concept.slug)

    return report
