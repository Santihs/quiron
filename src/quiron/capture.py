"""Scrape Obsidian callouts from 03-Daily-Logs/ into 00-Meta/inbox.jsonl.

No callout of this kind exists anywhere in the vault today — this is a new
convention, added to the daily-log template rather than requiring a new
tool. Capture asks nothing; classification happens later, in the inbox.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from .vault import Vault

CALLOUT_TYPES = ("duda", "concepto", "aplicado")

# Matches "> [!duda] rest of first line", case-insensitive on the type.
CALLOUT_START_RE = re.compile(
    r"^>\s*\[!(" + "|".join(CALLOUT_TYPES) + r")\]\s*(.*)$",
    re.IGNORECASE,
)
CONTINUATION_RE = re.compile(r"^>\s?(.*)$")


@dataclass(frozen=True)
class Capture:
    kind: str  # duda | concepto | aplicado
    text: str
    source_log: str  # relative path to the daily log
    id: str  # sha1(source_log + text) — stable across re-scans


def _capture_id(source_log: str, text: str) -> str:
    return hashlib.sha1(f"{source_log}\n{text}".encode("utf-8")).hexdigest()[:16]


def extract_captures(body: str, source_log: str) -> list[Capture]:
    lines = body.splitlines()
    out: list[Capture] = []
    seen_ids: set[str] = set()
    collision_counts: dict[str, int] = {}
    i = 0
    while i < len(lines):
        m = CALLOUT_START_RE.match(lines[i])
        if not m:
            i += 1
            continue
        kind = m.group(1).lower()
        parts = [m.group(2).strip()]
        i += 1
        while i < len(lines):
            cont = CONTINUATION_RE.match(lines[i])
            if not cont or CALLOUT_START_RE.match(lines[i]):
                break
            parts.append(cont.group(1).strip())
            i += 1
        text = " ".join(p for p in parts if p).strip()
        if text:
            base_id = _capture_id(source_log, text)
            capture_id = base_id
            if capture_id in seen_ids:
                occurrence = collision_counts.get(base_id, 1)
                while capture_id in seen_ids:
                    capture_id = hashlib.sha1(
                        f"{source_log}\n{kind}\n{occurrence}\n{text}".encode("utf-8")
                    ).hexdigest()[:16]
                    occurrence += 1
                collision_counts[base_id] = occurrence
            seen_ids.add(capture_id)
            out.append(
                Capture(
                    kind=kind,
                    text=text,
                    source_log=source_log,
                    id=capture_id,
                )
            )
    return out


def scan(vault: Vault) -> list[Capture]:
    out: list[Capture] = []
    for p in vault.walk_markdown("03-Daily-Logs"):
        raw = vault.read_text(p)
        out.extend(extract_captures(raw, vault.relative(p)))
    return out


def load_inbox(vault: Vault) -> list[dict]:
    p = vault.path("00-Meta", "inbox.jsonl")
    if not p.exists():
        return []
    lines = vault.read_text(p).splitlines()
    return [json.loads(l) for l in lines if l.strip()]


def write_inbox(vault: Vault, entries: list[dict]) -> None:
    p = vault.path("00-Meta", "inbox.jsonl")
    content = "\n".join(json.dumps(e, ensure_ascii=False) for e in entries)
    if content:
        content += "\n"
    vault.write_text(p, content)


def scan_and_merge(vault: Vault) -> tuple[list[Capture], int]:
    """Scan daily logs, merge new captures into inbox.jsonl by id (idempotent).

    Returns (all_new_captures_found_this_scan, number_actually_added).
    """
    found = scan(vault)
    existing = load_inbox(vault)
    existing_ids = {e["id"] for e in existing}
    added = 0
    for c in found:
        if c.id not in existing_ids:
            existing.append(
                {
                    "id": c.id,
                    "kind": c.kind,
                    "text": c.text,
                    "source_log": c.source_log,
                    "processed": False,
                }
            )
            existing_ids.add(c.id)
            added += 1
    write_inbox(vault, existing)
    return found, added
