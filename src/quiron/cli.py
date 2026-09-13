"""quiron CLI — today / seed / capture-scan / inbox / doctor / cards / evidence / next / sources."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import ankiconnect, audit, coverage, nextup, recall, sources
from .capture import scan_and_merge
from .doctor import run as doctor_run
from .evidence import add_evidence
from .errors import QuironError
from .inbox import Proposal, apply_proposals
from .inputs import (
    EvidenceInput,
    PolicyDecisionInput,
    ProposalInput,
    ReviewProposalInput,
    load_records,
    validate_record,
)
from .migrate import run_migrate
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
    try:
        return Knowledge.model_validate_json(vault.read_text(p))
    except ValueError as exc:
        raise QuironError(
            "INVALID_KNOWLEDGE",
            f"knowledge.json is invalid: {p}",
            exit_code=4,
            details={"path": str(p)},
        ) from exc


def save_knowledge(vault: Vault, knowledge: Knowledge) -> None:
    p = _knowledge_path(vault)
    vault.write_text(p, knowledge.model_dump_json(indent=2) + "\n")


def cmd_seed(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    existing = load_knowledge(vault)
    result, report = seed_run(vault, existing=existing, deck=args.deck)
    save_knowledge(vault, result)

    print(
        f"concepts: {report.concepts_created} created, {report.concepts_refreshed} refreshed"
    )
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
        print(
            f"doubts not mechanically linked (need manual attach): {len(report.doubts_unlinked)}"
        )
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
    inputs = load_records(args.apply, ProposalInput, "inbox proposals")
    proposals = [Proposal(**p.model_dump()) for p in inputs]
    knowledge, report = apply_proposals(vault, knowledge, proposals)
    save_knowledge(vault, knowledge)

    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        return 0
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
        vault_path=vault.root,
        deck=args.deck,
    )
    print(render(lines))
    return 0


def cmd_cards(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    knowledge = load_knowledge(vault) or Knowledge()

    if args.list_gaps:
        gaps = coverage.coverage_gap(knowledge)
        if args.json:
            print(
                json.dumps(
                    [
                        {"slug": c.slug, "title": c.title, "notes_ref": c.notes_ref}
                        for c in gaps
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        print(f"{len(gaps)} needed concepts with no cards")
        for c in gaps:
            print(f"  - {c.slug} ({c.notes_ref})")
        return 0

    if args.decide:
        if args.json:
            raise QuironError(
                "INTERACTIVE_JSON_UNSUPPORTED",
                "--decide is interactive and cannot be combined with --json",
                exit_code=2,
            )
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
        inputs = load_records(
            args.record_review, ReviewProposalInput, "review proposals"
        )
        proposals = [audit.ReviewProposal(**p.model_dump()) for p in inputs]
        review_report = audit.record_review(knowledge, proposals)
        save_knowledge(vault, knowledge)
        if args.json:
            print(json.dumps(asdict(review_report), ensure_ascii=False, indent=2))
            return 0
        print(f"recorded: {len(review_report.recorded)}")
        if review_report.skipped_no_card_ref:
            print(
                f"skipped (no matching card_ref): {len(review_report.skipped_no_card_ref)}"
            )
            for path in review_report.skipped_no_card_ref:
                print(f"  - {path}")
        return 0

    if args.list_undecided:
        pending = coverage.undecided(knowledge)
        if args.json:
            print(
                json.dumps(
                    [
                        {"slug": c.slug, "title": c.title, "notes_ref": c.notes_ref}
                        for c in pending
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"{len(pending)} undecided concepts")
            for c in pending:
                print(f"  - {c.slug} ({c.notes_ref})")
        return 0

    if args.set_policy:
        inputs = load_records(args.set_policy, PolicyDecisionInput, "policy decisions")
        decisions = [coverage.PolicyDecision(**d.model_dump()) for d in inputs]
        policy_report = coverage.set_policy(knowledge, decisions)
        save_knowledge(vault, knowledge)
        if args.json:
            print(json.dumps(asdict(policy_report), ensure_ascii=False, indent=2))
            return 0
        print(f"decided: {len(policy_report.decided)}")
        if policy_report.skipped_unknown_slug:
            print(f"skipped (unknown slug): {len(policy_report.skipped_unknown_slug)}")
            for slug in policy_report.skipped_unknown_slug:
                print(f"  - {slug}")
        return 0

    raise QuironError(
        "NO_ACTION",
        "pass exactly one cards action: --decide, --list-gaps, --list-undecided, "
        "--audit, --record-review, or --set-policy",
        exit_code=2,
    )


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


def cmd_migrate(args: argparse.Namespace) -> int:
    vault_path = Path(args.vault).resolve()
    is_existing = (vault_path / "00-Meta" / "knowledge.json").exists()
    if args.dry_run is None:
        dry_run = (
            is_existing  # existing vault: safe by default; new vault: nothing to lose
        )
    else:
        dry_run = args.dry_run.lower() != "false"

    answers = {
        "subject_expertise": args.subject_expertise,
        "deck_path": args.deck_path,
        "topic_notes_path": args.topic_notes_path,
        "resync_command": args.resync_command,
        "domain_framing": args.domain_framing,
    }
    report = run_migrate(vault_path, answers, dry_run=dry_run, deck=args.deck)

    if dry_run:
        print("dry run — nothing written (pass --dry-run=false to apply)")
        return 0

    if report.seed_report:
        sr = report.seed_report
        print(
            f"concepts: {sr.concepts_created} created, {sr.concepts_refreshed} refreshed"
        )
    if report.doctor_report:
        dr = report.doctor_report
        print(
            f"doctor: {dr.concept_count} concepts, {len(dr.dangling_refs)} dangling refs, "
            f"{len(dr.orphaned_concepts)} orphaned, {len(dr.unlinked_doubts)} unlinked doubts"
        )
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    knowledge = load_knowledge(vault) or Knowledge()
    evidence = validate_record(
        {
            "card_path": args.card,
            "kind": args.kind,
            "ref": args.ref,
            "scope": args.scope,
        },
        EvidenceInput,
        "evidence input",
    )
    result = add_evidence(
        knowledge,
        card_path=evidence.card_path,
        kind=evidence.kind,
        ref=evidence.ref,
        scope=evidence.scope,
    )
    if result.slug is None:
        if args.json:
            print(
                json.dumps(
                    {"status": "skipped", "code": "UNMAPPED_CARD"},
                    ensure_ascii=False,
                )
            )
            return 0
        print("card not mapped to any concept — nothing recorded")
        return 0
    save_knowledge(vault, knowledge)
    if args.json:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "slug": result.slug,
                    "concept_title": result.concept_title,
                    "kind": evidence.kind,
                },
                ensure_ascii=False,
            )
        )
        return 0
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
                    {
                        "slug": c.slug,
                        "title": c.title,
                        "reason": c.reason,
                        "detail": c.detail,
                    }
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
        sp.add_argument(
            "--vault", required=True, help="path to the Obsidian vault root"
        )
        sp.add_argument(
            "--deck",
            default="karpathy",
            help="live quiz-bank deck folder under 04-Quiz-Bank/",
        )
        sp.set_defaults(func=fn)

    sp = sub.add_parser("doctor")
    sp.add_argument("--vault", required=True)
    sp.add_argument(
        "--deck",
        default="karpathy",
        help="live quiz-bank deck folder under 04-Quiz-Bank/",
    )
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("inbox")
    sp.add_argument("--vault", required=True)
    sp.add_argument(
        "--apply", required=True, help="path to a JSON list of classified proposals"
    )
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_inbox)

    sp = sub.add_parser("cards")
    sp.add_argument("--vault", required=True)
    sp.add_argument(
        "--deck",
        default="karpathy",
        help="live quiz-bank deck folder under 04-Quiz-Bank/ (used by --audit)",
    )
    actions = sp.add_mutually_exclusive_group()
    actions.add_argument(
        "--decide", action="store_true", help="interactive retention-decision walker"
    )
    actions.add_argument(
        "--list-gaps", action="store_true", help="list needed-but-empty concepts"
    )
    actions.add_argument(
        "--list-undecided",
        action="store_true",
        help="list concepts with no retention decision yet, non-interactively",
    )
    actions.add_argument(
        "--audit",
        action="store_true",
        help="read-only card-quality report (layers 1+2)",
    )
    actions.add_argument(
        "--record-review",
        metavar="FILE",
        help="apply a JSON list of ReviewProposal after harvard-reviewer ran",
    )
    actions.add_argument(
        "--set-policy",
        metavar="FILE",
        help="apply a JSON list of PolicyDecision — non-interactive counterpart to --decide, for a skill/agent to drive",
    )
    sp.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable JSON instead of a text summary",
    )
    sp.set_defaults(func=cmd_cards)

    sp = sub.add_parser("evidence")
    sp.add_argument("--vault", required=True)
    sp.add_argument(
        "--add",
        action="store_true",
        required=True,
        help="only action today; explicit flag leaves room for --list later",
    )
    sp.add_argument(
        "--card", required=True, help="card path relative to the vault root"
    )
    sp.add_argument(
        "--kind", required=True, choices=["encountered", "explained", "applied"]
    )
    sp.add_argument("--ref", required=True)
    sp.add_argument("--scope")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_evidence)

    sp = sub.add_parser("migrate")
    sp.add_argument(
        "--vault",
        required=True,
        help="path to the Obsidian vault root (created if missing)",
    )
    sp.add_argument(
        "--deck",
        default="karpathy",
        help="live quiz-bank deck folder under 04-Quiz-Bank/",
    )
    sp.add_argument("--subject-expertise", default="", dest="subject_expertise")
    sp.add_argument("--deck-path", default="04-Quiz-Bank/*.md", dest="deck_path")
    sp.add_argument(
        "--topic-notes-path", default="02-Topics/*.md", dest="topic_notes_path"
    )
    sp.add_argument(
        "--resync-command",
        default="not applicable — no live per-card Anki-synced deck for this vault yet",
        dest="resync_command",
    )
    sp.add_argument(
        "--domain-framing",
        default="or a claim that doesn't hold up under scrutiny",
        dest="domain_framing",
    )
    sp.add_argument(
        "--dry-run",
        nargs="?",
        const="true",
        default=None,
        help="report what would change without writing; defaults to on for an "
        "existing vault (has 00-Meta/knowledge.json already) and off for a new "
        "one. Pass --dry-run=false to force apply.",
    )
    sp.set_defaults(func=cmd_migrate)

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
    try:
        return args.func(args)
    except QuironError as exc:
        if getattr(args, "json", False):
            print(
                json.dumps(
                    {"status": "error", **exc.as_dict()},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
