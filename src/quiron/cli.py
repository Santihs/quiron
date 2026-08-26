"""quiron CLI — today / seed / capture-scan / inbox / doctor / cards / evidence / next / sources."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ankiconnect, audit, coverage, nextup, recall, sources
from .capture import scan_and_merge
from .doctor import run as doctor_run
from .evidence import add_evidence
from .inbox import Proposal, apply_proposals
from .schema import Knowledge
from .seed import seed as seed_run
from .today import build_report, render
from .vault import Vault


def _knowledge_path(vault: Vault) -> Path:
    return vault.path("00-Meta", "knowledge.json")


def load_knowledge(vault: Vault) -> Knowledge | None:
    p = _knowledge_path(vault)
    if not p.exists():
        return None
    return Knowledge.model_validate_json(vault.read_text(p))


def save_knowledge(vault: Vault, knowledge: Knowledge) -> None:
    p = _knowledge_path(vault)
    vault.write_text(p, knowledge.model_dump_json(indent=2) + "\n")


def cmd_seed(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    existing = load_knowledge(vault)
    result, report = seed_run(vault, existing=existing, deck=args.deck)
    save_knowledge(vault, result)

    print(f"concepts: {report.concepts_created} created, {report.concepts_refreshed} refreshed")
    if report.concepts_orphaned:
        print(f"orphaned (kept, not deleted): {len(report.concepts_orphaned)}")
        for s in report.concepts_orphaned:
            print(f"  - {s}")
    print(f"cards resolved: {report.cards_resolved}")
    if report.cards_unresolved:
        print(f"cards with dangling Ref: {len(report.cards_unresolved)}")
        for path, ref in report.cards_unresolved:
            print(f"  - {path} -> {ref}")
    if report.doubts_unlinked:
        print(f"doubts not mechanically linked (need manual attach): {len(report.doubts_unlinked)}")
        for path in report.doubts_unlinked:
            print(f"  - {path}")
    if report.headings_skipped:
        print(f"structural headings skipped: {len(report.headings_skipped)}")
        for h in report.headings_skipped:
            print(f"  - {h}")
    return 0


def cmd_capture_scan(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    found, added = scan_and_merge(vault)
    print(f"scanned: {len(found)} callouts found, {added} new")
    return 0


def cmd_inbox(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    knowledge = load_knowledge(vault) or Knowledge()
    raw = json.loads(Path(args.apply).read_text(encoding="utf-8"))
    proposals = [Proposal(**p) for p in raw]
    knowledge, report = apply_proposals(vault, knowledge, proposals)
    save_knowledge(vault, knowledge)

    print(f"applied: {len(report.applied)}")
    if report.skipped_no_target:
        print(f"skipped (no target_slug): {len(report.skipped_no_target)}")
    if report.skipped_unknown_concept:
        print(f"skipped (unknown concept): {len(report.skipped_unknown_concept)}")
        for cid in report.skipped_unknown_concept:
            print(f"  - {cid}")
    return 0


def cmd_today(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    knowledge = load_knowledge(vault) or Knowledge()
    doctor = doctor_run(vault, existing=knowledge, deck=args.deck)

    contradictions = []
    note_id_to_slug = recall.collect_note_ids(vault, knowledge)
    if note_id_to_slug:
        try:
            notes_info = ankiconnect.cards_info_by_note_id(list(note_id_to_slug))
        except ankiconnect.AnkiConnectError:
            notes_info = {}
        # cards_info_by_note_id keys by note id already; recall expects the
        # same shape (noteId -> cardsInfo dict).
        contradictions = recall.cross_check(knowledge, note_id_to_slug, notes_info)

    lines = build_report(
        vault,
        knowledge,
        unresolved_refs=[(d["card"], d["ref"]) for d in doctor.dangling_refs],
        contradictions=contradictions,
    )
    print(render(lines))
    return 0


def cmd_cards(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    knowledge = load_knowledge(vault) or Knowledge()

    if args.list_gaps:
        gaps = coverage.coverage_gap(knowledge)
        print(f"{len(gaps)} needed concepts with no cards")
        for c in gaps:
            print(f"  - {c.slug} ({c.notes_ref})")
        return 0

    if args.decide:
        report = coverage.decide(knowledge)
        save_knowledge(vault, knowledge)
        print(f"decided: {report.decided}")
        if report.quit_early:
            print("stopped early — the rest stays undecided, safe to resume later")
        return 0

    if args.audit:
        note_id_to_slug = recall.collect_note_ids(vault, knowledge)
        notes_info = {}
        if note_id_to_slug:
            try:
                notes_info = ankiconnect.cards_info_by_note_id(list(note_id_to_slug))
            except ankiconnect.AnkiConnectError:
                notes_info = {}
        report = audit.run(vault, knowledge, notes_info=notes_info, deck=args.deck)

        result = {
            "checked": report.checked,
            "candidates": [
                {
                    "card_path": c.card_path,
                    "concept_slug": c.concept_slug,
                    "reasons": c.reasons,
                    "lapses": c.lapses,
                }
                for c in report.candidates
            ],
            "informational": [
                {
                    "card_path": i.card_path,
                    "concept_slug": i.concept_slug,
                    "reason": i.reason,
                    "lapses": i.lapses,
                }
                for i in report.informational
            ],
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"checked: {report.checked}")
            print(f"candidates: {len(report.candidates)}")
            for c in report.candidates:
                print(f"  - {c.card_path} [{', '.join(c.reasons)}]")
            print(f"informational: {len(report.informational)}")
            for i in report.informational:
                print(f"  - {i.card_path} ({i.reason}, lapses={i.lapses})")
        return 0

    if args.record_review:
        raw = json.loads(Path(args.record_review).read_text(encoding="utf-8"))
        proposals = [audit.ReviewProposal(**p) for p in raw]
        review_report = audit.record_review(knowledge, proposals)
        save_knowledge(vault, knowledge)
        print(f"recorded: {len(review_report.recorded)}")
        if review_report.skipped_no_card_ref:
            print(f"skipped (no matching card_ref): {len(review_report.skipped_no_card_ref)}")
            for path in review_report.skipped_no_card_ref:
                print(f"  - {path}")
        return 0

    print("nothing to do — pass --decide, --list-gaps, --audit, or --record-review")
    return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    knowledge = load_knowledge(vault)
    report = doctor_run(vault, existing=knowledge, deck=args.deck)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"concepts: {report.concept_count}")
        print(f"cards resolved: {report.card_resolved_count}")
        print(f"dangling refs: {len(report.dangling_refs)}")
        for d in report.dangling_refs:
            print(f"  - {d['card']} -> {d['ref']}")
        print(f"orphaned concepts: {len(report.orphaned_concepts)}")
        for s in report.orphaned_concepts:
            print(f"  - {s}")
        print(f"unlinked doubts: {len(report.unlinked_doubts)}")
        for d in report.unlinked_doubts:
            print(f"  - {d}")
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    knowledge = load_knowledge(vault) or Knowledge()
    result = add_evidence(
        knowledge,
        card_path=args.card,
        kind=args.kind,
        ref=args.ref,
        scope=args.scope,
    )
    if result.slug is None:
        print("card not mapped to any concept — nothing recorded")
        return 0
    save_knowledge(vault, knowledge)
    print(f"{result.slug}: {args.kind} evidence added ({result.concept_title})")
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    knowledge = load_knowledge(vault) or Knowledge()
    result = nextup.candidates(knowledge)

    if args.json:
        print(
            json.dumps(
                [
                    {"slug": c.slug, "title": c.title, "reason": c.reason, "detail": c.detail}
                    for c in result
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    symbol = {
        "open_doubt": "⚠",
        "unblocked": "←",
        "coverage_gap": "✗",
        "no_explained": "•",
    }
    for i, c in enumerate(result, start=1):
        row = f"{i}. {c.title} {symbol[c.reason]} {c.reason}"
        if c.detail:
            row += f" {c.detail}"
        print(row)
    if not result:
        print("no candidates — nothing has an open signal right now")
    return 0


def cmd_sources(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    knowledge = load_knowledge(vault) or Knowledge()
    rows = sources.yield_by_source(knowledge)

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "ref": r.ref,
                        "concept_count": r.concept_count,
                        "explained_count": r.explained_count,
                        "applied_count": r.applied_count,
                    }
                    for r in rows
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    for r in rows:
        print(
            f"{r.ref}  {r.concept_count} conceptos "
            f"· {r.explained_count} explicados "
            f"· {r.applied_count} aplicados"
        )
    if not rows:
        print("no sources recorded yet")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quiron")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("capture-scan")
    sp.add_argument("--vault", required=True, help="path to the Obsidian vault root")
    sp.set_defaults(func=cmd_capture_scan)

    for name, fn in (
        ("today", cmd_today),
        ("seed", cmd_seed),
    ):
        sp = sub.add_parser(name)
        sp.add_argument("--vault", required=True, help="path to the Obsidian vault root")
        sp.add_argument("--deck", default="karpathy", help="live quiz-bank deck folder under 04-Quiz-Bank/")
        sp.set_defaults(func=fn)

    sp = sub.add_parser("doctor")
    sp.add_argument("--vault", required=True)
    sp.add_argument("--deck", default="karpathy", help="live quiz-bank deck folder under 04-Quiz-Bank/")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("inbox")
    sp.add_argument("--vault", required=True)
    sp.add_argument("--apply", required=True, help="path to a JSON list of classified proposals")
    sp.set_defaults(func=cmd_inbox)

    sp = sub.add_parser("cards")
    sp.add_argument("--vault", required=True)
    sp.add_argument("--deck", default="karpathy", help="live quiz-bank deck folder under 04-Quiz-Bank/ (used by --audit)")
    sp.add_argument("--decide", action="store_true", help="interactive retention-decision walker")
    sp.add_argument("--list-gaps", action="store_true", help="list needed-but-empty concepts")
    sp.add_argument("--audit", action="store_true", help="read-only card-quality report (layers 1+2)")
    sp.add_argument("--record-review", metavar="FILE", help="apply a JSON list of ReviewProposal after harvard-reviewer ran")
    sp.add_argument("--json", action="store_true", help="with --audit, print JSON instead of a text summary")
    sp.set_defaults(func=cmd_cards)

    sp = sub.add_parser("evidence")
    sp.add_argument("--vault", required=True)
    sp.add_argument("--add", action="store_true", required=True, help="only action today; explicit flag leaves room for --list later")
    sp.add_argument("--card", required=True, help="card path relative to the vault root")
    sp.add_argument("--kind", required=True, choices=["encountered", "explained", "applied"])
    sp.add_argument("--ref", required=True)
    sp.add_argument("--scope")
    sp.set_defaults(func=cmd_evidence)

    for name, fn in (("next", cmd_next), ("sources", cmd_sources)):
        sp = sub.add_parser(name)
        sp.add_argument("--vault", required=True)
        sp.add_argument("--json", action="store_true")
        sp.set_defaults(func=fn)

    return p


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to cp1252, which can't encode em dashes or
    # the emoji tier markers `today` prints — force UTF-8 regardless of
    # locale, matching every other read/write in this codebase.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
