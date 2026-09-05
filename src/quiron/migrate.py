"""Scaffold quiron's plumbing into a vault via copier, then seed + doctor it.

Wraps `copier.run_copy()` against `templates/` rather than reimplementing
skip-if-exists/Jinja substitution — see DECISIONS.md for why. Does not
touch vault pedagogy (CLAUDE.md content, AGENTS.md hand overrides,
01-*/ structure) — only the quiron-specific Claude Code/OpenCode
skill/agent/command files and the 00-Meta/ seed files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import copier

from .doctor import DoctorReport
from .doctor import run as doctor_run
from .schema import Knowledge
from .seed import SeedReport
from .seed import seed as seed_run
from .vault import Vault

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


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
) -> MigrateReport:
    """Run copier against `vault_path`, then seed + doctor the result.

    `dry_run=True` reports what copier would create/update/skip without
    writing anything — the default posture for a vault that already has a
    `00-Meta/knowledge.json` (something to lose); a brand-new vault has
    nothing to lose and can apply directly.
    """
    vault_path.mkdir(parents=True, exist_ok=True)
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
    report = MigrateReport()
    if dry_run:
        return report

    vault = Vault(root=vault_path)
    existing = None
    knowledge_path = vault.path("00-Meta", "knowledge.json")
    if knowledge_path.exists():
        existing = Knowledge.model_validate_json(vault.read_text(knowledge_path))
    result, seed_report = seed_run(vault, existing=existing, deck=deck)
    vault.write_text(knowledge_path, result.model_dump_json(indent=2) + "\n")
    report.seed_report = seed_report
    report.doctor_report = doctor_run(vault, existing=result, deck=deck)
    return report
