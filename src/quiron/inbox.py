"""Apply already-classified inbox proposals into knowledge.json.

Classification itself happens outside this module (the /quiron-inbox skill).
This module only validates and writes — it never calls an LLM. Approving a
proposal marks the source inbox.jsonl entry `processed: true`; leaving one
unprocessed is always safe (see capture.py) and never renders red in `today`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .capture import load_inbox, write_inbox
from .schema import Doubt, Evidence, Knowledge


@dataclass
class Proposal:
    """One classified capture, ready to apply.

    kind="duda"      -> opens a Doubt on target_slug
    kind="concepto"  -> currently just marks the capture processed; concept
                         creation from free text is out of scope for Fase 1
                         (concepts come from 02-Topics headings via seed())
    kind="aplicado"  -> appends an Evidence(kind="applied") to target_slug
    """

    capture_id: str
    kind: str
    target_slug: str | None
    text: str  # duda: the question itself. aplicado: unused.
    ref: str = ""  # aplicado: file the evidence points to. duda: unused.
    at: str = ""
    scope: str | None = None


@dataclass
class ApplyReport:
    applied: list[str] = field(default_factory=list)
    skipped_no_target: list[str] = field(default_factory=list)
    skipped_unknown_concept: list[str] = field(default_factory=list)


def apply_proposals(
    vault, knowledge: Knowledge, proposals: list[Proposal]
) -> tuple[Knowledge, ApplyReport]:
    report = ApplyReport()
    by_slug = {c.slug: c for c in knowledge.concepts}
    inbox = load_inbox(vault)
    inbox_by_id = {e["id"]: e for e in inbox}

    for p in proposals:
        if p.kind == "concepto":
            if p.capture_id in inbox_by_id:
                inbox_by_id[p.capture_id]["processed"] = True
            report.applied.append(p.capture_id)
            continue

        if p.target_slug is None:
            report.skipped_no_target.append(p.capture_id)
            continue
        if p.target_slug not in by_slug:
            report.skipped_unknown_concept.append(p.capture_id)
            continue

        target = by_slug[p.target_slug]
        if p.kind == "duda":
            target.doubts.append(
                Doubt(question=p.text, raised_at=p.at, status="open")
            )
        elif p.kind == "aplicado":
            target.evidence.append(
                Evidence(kind="applied", at=p.at, ref=p.ref, scope=p.scope)
            )
        else:
            report.skipped_no_target.append(p.capture_id)
            continue

        if p.capture_id in inbox_by_id:
            inbox_by_id[p.capture_id]["processed"] = True
        report.applied.append(p.capture_id)

    write_inbox(vault, list(inbox_by_id.values()))
    return knowledge, report
