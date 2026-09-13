"""quiron doctor — diagnostics. Findings, not failures: always exits 0.

Re-runs the seed resolution pass read-only (no writes) to surface what's
wrong: unresolvable Ref: lines, orphaned concepts, doubts nobody linked.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .cardmap import duplicate_card_paths
from .errors import QuironError
from .schema import Knowledge
from .seed import SeedReport, seed
from .vault import Vault


@dataclass
class DoctorReport:
    dangling_refs: list[dict] = field(default_factory=list)
    orphaned_concepts: list[str] = field(default_factory=list)
    unlinked_doubts: list[str] = field(default_factory=list)
    headings_skipped: list[str] = field(default_factory=list)
    concept_count: int = 0
    card_resolved_count: int = 0
    missing_card_refs: list[str] = field(default_factory=list)
    missing_evidence_refs: list[str] = field(default_factory=list)
    missing_resolution_refs: list[str] = field(default_factory=list)
    unknown_prerequisites: list[str] = field(default_factory=list)
    duplicate_card_paths: dict[str, list[str]] = field(default_factory=dict)
    ambiguous_refs: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def run(
    vault: Vault, existing: Knowledge | None = None, deck: str = "karpathy"
) -> DoctorReport:
    source = existing.model_copy(deep=True) if existing is not None else None
    result, seed_report = seed(vault, existing=existing, deck=deck)
    source = source or result
    known_slugs = {c.slug for c in result.concepts}

    def missing(path: str, *, always: bool = False) -> bool:
        if not always and "/" not in path.replace("\\", "/"):
            return False
        try:
            vault.resolve_relative(path, must_exist=True, expected="file")
        except (OSError, QuironError):
            return True
        return False

    missing_cards = sorted(
        cr.path
        for concept in source.concepts
        for cr in concept.card_refs
        if missing(cr.path, always=True)
    )
    missing_evidence = sorted(
        evidence.ref
        for concept in result.concepts
        for evidence in concept.evidence
        if missing(evidence.ref)
    )
    missing_resolutions = sorted(
        doubt.resolution_ref
        for concept in result.concepts
        for doubt in concept.doubts
        if doubt.resolution_ref and missing(doubt.resolution_ref, always=True)
    )
    unknown_prerequisites = sorted(
        f"{concept.slug}:{prerequisite}"
        for concept in result.concepts
        for prerequisite in concept.prerequisites
        if prerequisite not in known_slugs
    )
    return DoctorReport(
        dangling_refs=[
            {"card": path, "ref": ref} for path, ref in seed_report.cards_unresolved
        ],
        orphaned_concepts=list(seed_report.concepts_orphaned),
        unlinked_doubts=list(seed_report.doubts_unlinked),
        headings_skipped=list(seed_report.headings_skipped),
        concept_count=len(result.concepts),
        card_resolved_count=seed_report.cards_resolved,
        missing_card_refs=missing_cards,
        missing_evidence_refs=missing_evidence,
        missing_resolution_refs=missing_resolutions,
        unknown_prerequisites=unknown_prerequisites,
        duplicate_card_paths=duplicate_card_paths(source),
        ambiguous_refs=[
            {"card": path, "ref": ref, "lines": lines}
            for path, ref, lines in seed_report.cards_ambiguous
        ],
    )
