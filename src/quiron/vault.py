"""Vault filesystem access: walking, UTF-8 reads, frontmatter parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .errors import QuironError

EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".obsidian",
}

FRONTMATTER_RE = re.compile(r"^---\n([\s\S]*?)\n---\n([\s\S]*)$")


@dataclass(frozen=True)
class Vault:
    root: Path

    def path(self, *parts: str) -> Path:
        return self.resolve_relative(Path(*parts))

    def resolve_relative(
        self,
        relative: str | Path,
        *,
        must_exist: bool = False,
        expected: str | None = None,
    ) -> Path:
        """Resolve a vault-relative path without allowing filesystem escape."""
        raw = str(relative)
        normalized = raw.replace("\\", "/")
        candidate_input = Path(normalized)
        if (
            candidate_input.is_absolute()
            or candidate_input.drive
            or re.match(r"^[A-Za-z]:/", normalized)
        ):
            raise QuironError(
                "UNSAFE_PATH", f"unsafe vault path: {relative}", exit_code=4
            )

        root = self.root.resolve()
        candidate = (root / candidate_input).resolve()
        if candidate != root and root not in candidate.parents:
            raise QuironError(
                "UNSAFE_PATH", f"unsafe vault path: {relative}", exit_code=4
            )
        if must_exist and not candidate.exists():
            raise QuironError(
                "MISSING_PATH", f"vault path does not exist: {relative}", exit_code=4
            )
        if candidate.exists() and expected == "file" and not candidate.is_file():
            raise QuironError(
                "INVALID_PATH", f"vault path is not a file: {relative}", exit_code=4
            )
        if candidate.exists() and expected == "directory" and not candidate.is_dir():
            raise QuironError(
                "INVALID_PATH",
                f"vault path is not a directory: {relative}",
                exit_code=4,
            )
        return candidate

    def _contained(self, path: Path) -> Path:
        candidate = path.resolve()
        root = self.root.resolve()
        if candidate != root and root not in candidate.parents:
            raise QuironError("UNSAFE_PATH", f"unsafe vault path: {path}", exit_code=4)
        return candidate

    def read_text(self, path: Path) -> str:
        return self._contained(path).read_text(encoding="utf-8")

    def write_text(self, path: Path, content: str) -> None:
        from .store import atomic_write_text

        atomic_write_text(self._contained(path), content)

    def walk_markdown(self, subdir: str) -> list[Path]:
        """List *.md files under vault/subdir, sorted, skipping excluded dirs."""
        base = self.path(subdir)
        if not base.exists():
            return []
        out: list[Path] = []
        for p in base.rglob("*.md"):
            if any(
                part in EXCLUDED_DIR_NAMES for part in p.relative_to(self.root).parts
            ):
                continue
            out.append(p)
        return sorted(out)

    def relative(self, path: Path) -> str:
        return self._contained(path).relative_to(self.root.resolve()).as_posix()


def split_frontmatter(raw: str) -> tuple[dict | None, str]:
    """Returns (frontmatter_dict_or_None, body). None means no/invalid frontmatter."""
    raw = raw.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return None, raw
    fm_text, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return None, raw
    if not isinstance(fm, dict):
        return None, raw
    return fm, body


def read_frontmatter(vault: Vault, path: Path) -> tuple[dict | None, str]:
    raw = vault.read_text(path)
    return split_frontmatter(raw)


def read_note_id(vault: Vault, card_path: str) -> int | None:
    """Reads the `noteId` frontmatter field of a card given its vault-relative
    path (e.g. "04-Quiz-Bank/karpathy/x.md"). Shared by recall.py and
    audit.py — both need to go from a CardRef.path to the Anki note id."""
    try:
        fm, _ = read_frontmatter(vault, vault.path(*card_path.split("/")))
    except (OSError, QuironError):
        return None
    if fm is None:
        return None
    note_id = fm.get("noteId")
    try:
        return int(note_id) if note_id is not None else None
    except (TypeError, ValueError):
        return None
