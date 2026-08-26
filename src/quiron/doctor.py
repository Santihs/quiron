"""quiron doctor — diagnostics. Findings, not failures: always exits 0.

Re-runs the seed resolution pass read-only (no writes) to surface what's
wrong: unresolvable Ref: lines, orphaned concepts, doubts nobody linked.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

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

    def to_dict(self) -> dict:
        return asdict(self)


def run(vault: Vault, existing: Knowledge | None = None, deck: str = "karpathy") -> DoctorReport:
    result, seed_report = seed(vault, existing=existing, deck=deck)
    return DoctorReport(
        dangling_refs=[
            {"card": path, "ref": ref} for path, ref in seed_report.cards_unresolved
        ],
        orphaned_concepts=list(seed_report.concepts_orphaned),
        unlinked_doubts=list(seed_report.doubts_unlinked),
        headings_skipped=list(seed_report.headings_skipped),
        concept_count=len(result.concepts),
        card_resolved_count=seed_report.cards_resolved,
    )
