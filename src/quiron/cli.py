"""quiron CLI — today / seed / capture-scan / inbox / doctor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .capture import scan_and_merge
from .doctor import run as doctor_run
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
    result, report = seed_run(vault, existing=existing)
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
    doctor = doctor_run(vault, existing=knowledge)
    lines = build_report(vault, knowledge, unresolved_refs=[
        (d["card"], d["ref"]) for d in doctor.dangling_refs
    ])
    print(render(lines))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    vault = Vault(root=Path(args.vault).resolve())
    knowledge = load_knowledge(vault)
    report = doctor_run(vault, existing=knowledge)
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quiron")
    sub = p.add_subparsers(dest="command", required=True)

    for name, fn in (
        ("today", cmd_today),
        ("seed", cmd_seed),
        ("capture-scan", cmd_capture_scan),
    ):
        sp = sub.add_parser(name)
        sp.add_argument("--vault", required=True, help="path to the Obsidian vault root")
        sp.set_defaults(func=fn)

    sp = sub.add_parser("doctor")
    sp.add_argument("--vault", required=True)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("inbox")
    sp.add_argument("--vault", required=True)
    sp.add_argument("--apply", required=True, help="path to a JSON list of classified proposals")
    sp.set_defaults(func=cmd_inbox)

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
