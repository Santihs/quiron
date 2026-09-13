"""Coverage queries and the interactive retention-decision walker.

A concept with no cards is never red (v7's hard tier rule) — this module
only produces yellow-tier data. Deciding needed/declined is a human call;
quiron never infers it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

from .schema import Concept, Knowledge


def coverage_gap(knowledge: Knowledge) -> list[Concept]:
    """Concepts you decided need cards, but don't have any yet."""
    return [
        c for c in knowledge.concepts if c.card_policy == "needed" and not c.card_refs
    ]


def undecided(knowledge: Knowledge) -> list[Concept]:
    """Concepts with no retention decision at all."""
    return [c for c in knowledge.concepts if c.card_policy == "undecided"]


@dataclass(frozen=True)
class PolicyDecision:
    """One concept's retention decision, arrived at conversationally (e.g. by
    the quiron-cards-decide skill) rather than typed into decide()'s input()
    loop. Same role as audit.ReviewProposal: a batch a skill can build once
    it has judgment, handed to a deterministic apply function."""

    slug: str
    card_policy: Literal["needed", "declined"]
    declined_reason: str | None = None


@dataclass
class SetPolicyReport:
    decided: list[str] = field(default_factory=list)
    skipped_unknown_slug: list[str] = field(default_factory=list)


def set_policy(
    knowledge: Knowledge, decisions: list[PolicyDecision]
) -> SetPolicyReport:
    """Non-interactive counterpart to decide() — applies a batch of already-made
    decisions instead of prompting for them. Exists so a Claude Code skill can
    drive this instead of only a human typing into a real terminal (decide()'s
    input() loop can't be scripted from a skill). decide() is untouched; this
    is a second door into the same state, not a replacement."""
    report = SetPolicyReport()
    by_slug = {c.slug: c for c in knowledge.concepts}
    for d in decisions:
        concept = by_slug.get(d.slug)
        if concept is None:
            report.skipped_unknown_slug.append(d.slug)
            continue
        concept.card_policy = d.card_policy
        if d.card_policy == "declined":
            concept.declined_reason = d.declined_reason
        report.decided.append(d.slug)
    return report


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
