"""Card quality, layers 1 and 2 (v7's Card quality section).

Layer 1 is static and deterministic — no LLM, no Anki. Layer 2 is the Anki
lapses cross-signal: only meaningful once we know whether the concept was
ever explained/applied, which is exactly what schema.Concept.understanding
already derives. Layer 3 (harvard-reviewer) is NOT this module — audit.py
only decides *which* cards deserve that dispatch and *why*; it never edits
a card and never writes to knowledge.json. That happens later, in
`quiron cards --record-review`, after a human/skill has actually reviewed
the candidates this module flagged.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from datetime import date

from . import cardtext
from .cardmap import card_to_concept
from .headings import REF_LINE_RE, extract_ref
from .schema import Concept, Knowledge
from .seed import seed
from .vault import Vault, read_frontmatter, read_note_id

OVERLAP_THRESHOLD = 0.5
MIN_INFO_ITEMS = 4
MAX_WORDS = 50
# self-explain:true cards are, by harvard-reviewer's own spec, "one
# tightly-coupled derivation where the steps only make sense together" —
# exempt from the enumeration check and held to a longer length budget,
# not the ~15-20s-aloud heuristic meant for simple recall cards.
MAX_WORDS_SELF_EXPLAIN = 120
DUPLICATE_RATIO = 0.85
LAPSES_THRESHOLD = 4


@dataclass(frozen=True)
class Candidate:
    card_path: str
    concept_slug: str | None
    reasons: list[str]
    lapses: int | None = None


@dataclass(frozen=True)
class Informational:
    card_path: str
    concept_slug: str
    reason: str
    lapses: int


@dataclass
class AuditReport:
    candidates: list[Candidate] = field(default_factory=list)
    informational: list[Informational] = field(default_factory=list)
    checked: int = 0


def _strip_ref_line(answer: str) -> str:
    return REF_LINE_RE.sub("", answer).strip()


def _load_cards(vault: Vault, deck: str) -> dict[str, tuple[str, bool]]:
    """card_path -> (body post-frontmatter, self_explain flag), for every
    card in 04-Quiz-Bank/<deck>."""
    out: dict[str, tuple[str, bool]] = {}
    for p in vault.walk_markdown(f"04-Quiz-Bank/{deck}"):
        fm, body = read_frontmatter(vault, p)
        self_explain = bool(fm.get("self-explain")) if fm else False
        out[vault.relative(p)] = (body, self_explain)
    return out


def layer1_flags(cards: dict[str, tuple[str, bool]]) -> dict[str, list[str]]:
    """cards: card_path -> (body, self_explain). Returns card_path -> list of
    layer-1 reason strings. A card with no flags is simply absent from the
    result."""
    flags: dict[str, list[str]] = {}
    normalized_questions: dict[str, set[str]] = {}

    for path, (body, self_explain) in cards.items():
        parsed = cardtext.parse_qa(body)
        question = parsed.question
        answer = _strip_ref_line(parsed.answer)
        reasons: list[str] = []
        if not parsed.valid:
            flags[path] = ["malformed_qa"]
            normalized_questions[path] = cardtext.normalize_tokens(question)
            continue

        q_tokens = cardtext.normalize_tokens(question)
        a_tokens = cardtext.normalize_tokens(answer)
        if cardtext.jaccard(q_tokens, a_tokens) >= OVERLAP_THRESHOLD:
            reasons.append("giveaway_overlap")

        # a self-explain derivation's numbered steps are expected and
        # exempt — that IS the "one tightly-coupled derivation" the
        # reviewer's own spec calls right-sized.
        if (
            not self_explain
            and cardtext.count_enumeration_items(answer) >= MIN_INFO_ITEMS
        ):
            reasons.append("enumeration")

        max_words = MAX_WORDS_SELF_EXPLAIN if self_explain else MAX_WORDS
        if cardtext.word_count(answer) > max_words:
            reasons.append("too_long")

        if reasons:
            flags[path] = reasons
        normalized_questions[path] = q_tokens

    # fuzzy duplicates: all pairs, 148^2 is trivial at this scale
    paths = list(normalized_questions.keys())
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            tokens_i = normalized_questions[paths[i]]
            tokens_j = normalized_questions[paths[j]]
            if not tokens_i or not tokens_j:
                continue
            ratio = difflib.SequenceMatcher(
                None, sorted(tokens_i), sorted(tokens_j)
            ).ratio()
            if ratio >= DUPLICATE_RATIO:
                flags.setdefault(paths[i], []).append("duplicate")
                flags.setdefault(paths[j], []).append("duplicate")

    return flags


def lapses_signal(concept: Concept, lapses: int) -> str | None:
    if lapses < LAPSES_THRESHOLD:
        return None
    if concept.understanding in ("explained", "applied"):
        return "suspect_card"
    return "probably_dont_know_it"


def run(
    vault: Vault,
    knowledge: Knowledge,
    notes_info: dict[int, dict] | None = None,
    deck: str = "karpathy",
) -> AuditReport:
    """notes_info: noteId -> AnkiConnect cardsInfo dict, or None/{} if Anki
    is unreachable — layer 2 is then simply skipped, layer 1 still runs.
    """
    cards = _load_cards(vault, deck)
    card_to_slug = card_to_concept(knowledge)
    by_slug = {c.slug: c for c in knowledge.concepts}

    flags = layer1_flags(cards)
    for path in cards:
        if path not in card_to_slug:
            flags.setdefault(path, []).append("unmapped_concept")

    # dangling Ref: — reuse seed's own resolution, no new logic
    _, seed_report = seed(vault, existing=knowledge, deck=deck)
    dangling_paths = {path for path, _ in seed_report.cards_unresolved}
    for path in dangling_paths:
        flags.setdefault(path, []).append("dangling_ref")

    report = AuditReport(checked=len(cards))
    notes_info = notes_info or {}

    lapses_by_path: dict[str, int] = {}
    if notes_info:
        for path in cards:
            note_id = read_note_id(vault, path)
            if note_id is None:
                continue
            card_info = notes_info.get(note_id)
            if card_info is None:
                continue
            lapses = card_info.get("lapses")
            if lapses is None:
                continue
            lapses_by_path[path] = lapses

            slug = card_to_slug.get(path)
            concept = by_slug.get(slug) if slug else None
            if concept is None:
                continue
            signal = lapses_signal(concept, lapses)
            if signal == "suspect_card":
                flags.setdefault(path, []).append("suspect_card")
            elif signal == "probably_dont_know_it":
                report.informational.append(
                    Informational(
                        card_path=path, concept_slug=slug, reason=signal, lapses=lapses
                    )
                )

    for path, reasons in flags.items():
        report.candidates.append(
            Candidate(
                card_path=path,
                concept_slug=card_to_slug.get(path),
                reasons=reasons,
                lapses=lapses_by_path.get(path),
            )
        )

    return report


@dataclass(frozen=True)
class ReviewProposal:
    """One card's outcome after harvard-reviewer looked at it. quality/
    reviewer_verdict come from the reviewer's judgment (via the
    quiron-cards-audit skill); lapses_at_review is the value --audit already
    captured for this card in the same run — never re-fetched, so it's a
    true snapshot of "state right before the fix", not "state whenever
    --record-review happens to run"."""

    card_path: str
    quality: str  # "ok" | "flagged" | "retired"
    reviewer_verdict: str
    lapses_at_review: int | None = None
    flagged_reason: str | None = None


@dataclass
class RecordReviewReport:
    recorded: list[str] = field(default_factory=list)
    skipped_no_card_ref: list[str] = field(default_factory=list)


def record_review(
    knowledge: Knowledge, proposals: list[ReviewProposal]
) -> RecordReviewReport:
    report = RecordReviewReport()
    today = date.today()

    card_refs_by_path = {}
    for c in knowledge.concepts:
        for cr in c.card_refs:
            card_refs_by_path[cr.path] = cr

    for p in proposals:
        cr = card_refs_by_path.get(p.card_path)
        if cr is None:
            report.skipped_no_card_ref.append(p.card_path)
            continue
        cr.quality = p.quality
        cr.reviewed_at = today
        cr.reviewer_verdict = p.reviewer_verdict
        cr.lapses_at_review = p.lapses_at_review
        cr.flagged_reason = p.flagged_reason
        report.recorded.append(p.card_path)

    return report
