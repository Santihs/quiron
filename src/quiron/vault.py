"""Vault filesystem access: walking, UTF-8 reads, frontmatter parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

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
        return self.root.joinpath(*parts)

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def write_text(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")

    def walk_markdown(self, subdir: str) -> list[Path]:
        """List *.md files under vault/subdir, sorted, skipping excluded dirs."""
        base = self.path(subdir)
        if not base.exists():
            return []
        out: list[Path] = []
        for p in base.rglob("*.md"):
            if any(part in EXCLUDED_DIR_NAMES for part in p.relative_to(self.root).parts):
                continue
            out.append(p)
        return sorted(out)

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()


def split_frontmatter(raw: str) -> tuple[dict | None, str]:
    """Returns (frontmatter_dict_or_None, body). None means no/invalid frontmatter."""
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
