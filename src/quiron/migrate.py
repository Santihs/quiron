"""Scaffold quiron's plumbing into a vault via copier, then seed + doctor it.

Wraps `copier.run_copy()` against `templates/` rather than reimplementing
skip-if-exists/Jinja substitution — see DECISIONS.md for why. Does not
touch vault pedagogy (CLAUDE.md content, AGENTS.md hand overrides,
01-*/ structure) — only the quiron-specific Claude Code/OpenCode
skill/agent/command files and the 00-Meta/ seed files.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

import copier

from .doctor import DoctorReport
from .doctor import run as doctor_run
from .errors import QuironError
from .schema import Knowledge, load_knowledge_json
from .seed import SeedReport
from .seed import seed as seed_run
from .store import vault_lock
from .vault import Vault

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
QUIZ_ME_PATHS = (
    ".claude/commands/quiz-me.md",
    ".opencode/commands/quiz-me.md",
)
QUIZ_ME_EVIDENCE_PATH = TEMPLATES_DIR / "_shared" / "commands" / "quiz-me-evidence.md"
QUIZ_ME_EVIDENCE_START = "<!-- quiron:shared-quiz-me-evidence:start -->"
QUIZ_ME_EVIDENCE_END = "<!-- quiron:shared-quiz-me-evidence:end -->"


@dataclass
class MigrateReport:
    copier_output: list[str] = field(default_factory=list)
    seed_report: SeedReport | None = None
    doctor_report: DoctorReport | None = None


def run_migrate(
    vault_path: Path,
    answers: dict,
    dry_run: bool = False,
    deck: str = "karpathy",
    templates_only: bool = False,
) -> MigrateReport:
    """Run copier against `vault_path`, then seed + doctor the result.

    `dry_run=True` reports what copier would create/update/skip without
    writing anything — the default posture for a vault that already has a
    `00-Meta/knowledge.json` (something to lose); a brand-new vault has
    nothing to lose and can apply directly.
    """
    if dry_run:
        return _run_migrate(
            vault_path,
            answers,
            dry_run=True,
            deck=deck,
            templates_only=templates_only,
        )
    with vault_lock(Vault(root=vault_path)):
        return _run_migrate(
            vault_path,
            answers,
            dry_run=False,
            deck=deck,
            templates_only=templates_only,
        )


def _run_migrate(
    vault_path: Path,
    answers: dict,
    dry_run: bool,
    deck: str,
    templates_only: bool = False,
) -> MigrateReport:
    report = MigrateReport()
    knowledge_path = vault_path / "00-Meta" / "knowledge.json"
    if knowledge_path.exists():
        try:
            load_knowledge_json(knowledge_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise QuironError(
                "INVALID_KNOWLEDGE",
                f"knowledge.json is invalid: {knowledge_path}",
                exit_code=4,
                details={"path": str(knowledge_path)},
            ) from exc

    report.copier_output = _planned_output(vault_path)
    copier.run_copy(
        src_path=str(TEMPLATES_DIR),
        dst_path=str(vault_path),
        data=answers,
        defaults=True,
        unsafe=True,
        vcs_ref="HEAD",
        overwrite=True,
        pretend=dry_run,
    )
    if dry_run:
        return report

    _sync_quiz_me_evidence(vault_path)
    if templates_only:
        return report

    vault = Vault(root=vault_path)
    existing = None
    knowledge_path = vault.path("00-Meta", "knowledge.json")
    if knowledge_path.exists():
        existing = load_knowledge_json(vault.read_text(knowledge_path))
    result, seed_report = seed_run(vault, existing=existing, deck=deck)
    vault.write_text(knowledge_path, result.model_dump_json(indent=2) + "\n")
    report.seed_report = seed_report
    report.doctor_report = doctor_run(vault, existing=result, deck=deck)
    return report


def _quiz_me_evidence_block() -> str:
    return QUIZ_ME_EVIDENCE_PATH.read_text(encoding="utf-8").strip()


def _replace_quiz_me_evidence(text: str, block: str) -> str:
    start = text.find(QUIZ_ME_EVIDENCE_START)
    if start < 0:
        if "quiron evidence --add" in text:
            return text
        return text.rstrip() + "\n\n" + block + "\n"

    end = text.find(QUIZ_ME_EVIDENCE_END, start)
    if end < 0:
        return text.rstrip() + "\n\n" + block + "\n"
    end += len(QUIZ_ME_EVIDENCE_END)
    return text[:start] + block + text[end:]


def _sync_quiz_me_evidence(vault_path: Path) -> None:
    vault = Vault(root=vault_path)
    block = _quiz_me_evidence_block()
    for relative in QUIZ_ME_PATHS:
        path = vault.path(*relative.split("/"))
        if not path.exists():
            continue
        original = vault.read_text(path)
        updated = _replace_quiz_me_evidence(original, block)
        if updated != original:
            vault.write_text(path, updated)


def _quiz_me_needs_sync(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if "quiron evidence --add" in text and QUIZ_ME_EVIDENCE_START not in text:
        return False
    return _replace_quiz_me_evidence(text, _quiz_me_evidence_block()) != text


def _planned_output(vault_path: Path) -> list[str]:
    """Return a stable create/update/skip preview without touching the vault."""
    skip_patterns = [
        "CLAUDE.md",
        "AGENTS.md",
        "03-Daily-Logs/_template.md",
        "00-Meta/knowledge.json",
        "00-Meta/inbox.jsonl",
        "00-Meta/history.jsonl",
        ".claude/commands/quiz-me.md",
        ".opencode/commands/quiz-me.md",
        ".claude/agents/quiz-reviewer.md",
        ".claude/skills/quiz-review/SKILL.md",
        ".opencode/agents/quiz-reviewer.md",
        ".opencode/skills/quiz-review/SKILL.md",
    ]
    output: list[str] = []
    for source in sorted(TEMPLATES_DIR.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(TEMPLATES_DIR).as_posix()
        if relative in {"copier.yml", "README.md"} or relative.startswith("_shared/"):
            continue
        destination = vault_path / relative
        if relative in QUIZ_ME_PATHS and destination.exists():
            action = "update" if _quiz_me_needs_sync(destination) else "skip"
        elif any(fnmatch.fnmatch(relative, pattern) for pattern in skip_patterns):
            action = "skip" if destination.exists() else "create"
        elif destination.exists():
            action = "update"
        else:
            action = "create"
        output.append(f"{action} {relative}")
    return output
