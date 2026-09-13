"""Apply already-classified inbox proposals into knowledge.json.

Classification itself happens outside this module (the /quiron-inbox skill).
This module only validates and writes — it never calls an LLM. Approving a
proposal marks the source inbox.jsonl entry `processed: true`; leaving one
unprocessed is always safe (see capture.py) and never renders red in `today`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .capture import load_inbox, write_inbox
from .history import append_events, make_event
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
    target_slug: str | None = None
    text: str = ""  # duda: the question itself. aplicado: unused.
    ref: str = ""  # aplicado: file the evidence points to. duda: unused.
    at: date | str | None = None
    scope: str | None = None


@dataclass
class ApplyReport:
    applied: list[str] = field(default_factory=list)
    skipped_no_target: list[str] = field(default_factory=list)
    skipped_unknown_concept: list[str] = field(default_factory=list)
    skipped_unknown_capture: list[str] = field(default_factory=list)
    skipped_mismatched_capture: list[str] = field(default_factory=list)
    skipped_already_processed: list[str] = field(default_factory=list)


def _as_date(value: date | str | None) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    raise ValueError("proposal date is required")


def apply_proposals(
    vault,
    knowledge: Knowledge,
    proposals: list[Proposal],
    operation_id: str | None = None,
) -> tuple[Knowledge, ApplyReport]:
    report = ApplyReport()
    by_slug = {c.slug: c for c in knowledge.concepts}
    inbox = load_inbox(vault)
    inbox_by_id = {e["id"]: e for e in inbox}
    events: list[dict] = []
    changed_inbox = False
    seen_proposals: set[str] = set()

    for p in proposals:
        capture = inbox_by_id.get(p.capture_id)
        if capture is None:
            report.skipped_unknown_capture.append(p.capture_id)
            continue
        if p.capture_id in seen_proposals or capture.get("processed", False):
            report.skipped_already_processed.append(p.capture_id)
            continue
        seen_proposals.add(p.capture_id)
        if (
            capture.get("kind") != p.kind
            or capture.get("text", "").strip() != p.text.strip()
        ):
            report.skipped_mismatched_capture.append(p.capture_id)
            continue

        event_operation_id = operation_id or f"capture:{p.capture_id}"
        if p.kind == "concepto":
            capture["processed"] = True
            changed_inbox = True
            report.applied.append(p.capture_id)
            events.append(
                make_event(
                    "capture_processed",
                    event_operation_id,
                    p.capture_id,
                    kind=p.kind,
                )
            )
            continue

        if p.target_slug is None:
            report.skipped_no_target.append(p.capture_id)
            continue
        if p.target_slug not in by_slug:
            report.skipped_unknown_concept.append(p.capture_id)
            continue

        target = by_slug[p.target_slug]
        if p.kind == "duda":
            if any(d.capture_id == p.capture_id for d in target.doubts):
                report.skipped_already_processed.append(p.capture_id)
                continue
            target.doubts.append(
                Doubt(
                    question=p.text,
                    raised_at=_as_date(p.at),
                    status="open",
                    capture_id=p.capture_id,
                    operation_id=event_operation_id,
                )
            )
            events.append(
                make_event(
                    "doubt_opened",
                    event_operation_id,
                    p.capture_id,
                    slug=p.target_slug,
                    question=p.text,
                )
            )
        elif p.kind == "aplicado":
            if any(e.capture_id == p.capture_id for e in target.evidence):
                report.skipped_already_processed.append(p.capture_id)
                continue
            target.evidence.append(
                Evidence(
                    kind="applied",
                    at=_as_date(p.at),
                    ref=p.ref,
                    scope=p.scope,
                    capture_id=p.capture_id,
                    operation_id=event_operation_id,
                )
            )
            events.append(
                make_event(
                    "evidence_added",
                    event_operation_id,
                    p.capture_id,
                    slug=p.target_slug,
                    kind="applied",
                    ref=p.ref,
                )
            )
        else:
            report.skipped_no_target.append(p.capture_id)
            continue

        capture["processed"] = True
        changed_inbox = True
        report.applied.append(p.capture_id)

    if changed_inbox:
        write_inbox(vault, list(inbox_by_id.values()))
    append_events(vault, events)
    return knowledge, report
