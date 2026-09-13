"""Build/refresh knowledge.json from what the vault already contains.

Idempotent: never overwrites what the user generated (evidence, doubts,
card_policy). Only refreshes fields derived from the source material
(title, unit, notes_ref, sources, card_refs paths).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .headings import (
    Heading,
    concept_headings,
    extract_headings,
    extract_ref,
    is_concept_heading,
    parse_ref,
    resolve_anchor,
    resolve_anchor_detailed,
    slugify,
)
from .schema import CardRef, Concept, Doubt, Knowledge, Source
from .vault import Vault, read_frontmatter


@dataclass
class SeedReport:
    concepts_created: int = 0
    concepts_refreshed: int = 0
    concepts_orphaned: list[str] = field(default_factory=list)
    headings_skipped: list[str] = field(default_factory=list)
    cards_unresolved: list[tuple[str, str]] = field(default_factory=list)
    cards_ambiguous: list[tuple[str, str, list[int]]] = field(default_factory=list)
    cards_resolved: int = 0
    doubts_unlinked: list[str] = field(default_factory=list)


def _concept_slug(file_stem: str, heading_text: str) -> str:
    return f"{slugify(file_stem)}--{slugify(heading_text)}"


def _sources_from_frontmatter(fm: dict) -> list[Source]:
    sources: list[Source] = []
    for key in ("source_pdf", "source_pdf_2"):
        val = fm.get(key)
        if val:
            sources.append(Source(kind="book", ref=str(val)))
    return sources


def _unit_from_frontmatter(fm: dict) -> str:
    tags = fm.get("tags") or []
    if tags:
        return str(tags[0])
    return "unknown"


def _as_date(value: object, default: date) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return default


def _index_topic_notes(vault: Vault, report: SeedReport):
    """Returns dict: relative_path -> {fm, headings, stem}."""
    index = {}
    for p in vault.walk_markdown("02-Topics"):
        fm, body = read_frontmatter(vault, p)
        had_frontmatter = fm is not None
        fm = fm or {}
        headings = concept_headings(body)
        if not headings and not had_frontmatter:
            # A topic note with NO frontmatter at all (devtalles' shape) and
            # no surviving concept heading is itself the concept — the
            # granularity that vault's one-concept-per-file notes actually
            # use. Gated on missing frontmatter specifically so this never
            # fires for a karpathy stub note (real frontmatter, `## Core
            # concepts to capture` etc. not yet filled in) — that's an
            # unwritten concept, not a file-level one, and seeding it would
            # be noise, not signal.
            title = next(
                (l[2:].strip() for l in body.splitlines() if l.startswith("# ")),
                p.stem,
            )
            headings = [Heading(level=1, text=title, line_no=1)]
        index[vault.relative(p)] = {
            "fm": fm,
            "headings": headings,
            "stem": p.stem,
        }
        for h in extract_headings(body):
            if not is_concept_heading(h):
                label = f"{vault.relative(p)}#{h.text}"
                if label not in report.headings_skipped:
                    report.headings_skipped.append(label)
    return index


def _index_cards(vault: Vault, deck: str) -> list[tuple[str, str]]:
    """Returns list of (card_relative_path, ref_content) for cards with a Ref: line."""
    out = []
    for p in vault.walk_markdown(f"04-Quiz-Bank/{deck}"):
        _, body = read_frontmatter(vault, p)
        ref = extract_ref(body)
        if ref:
            out.append((vault.relative(p), ref))
    return out


def _index_doubts(vault: Vault) -> list[dict]:
    out = []
    for p in vault.walk_markdown("06-Doubts-Resolved"):
        if p.name == "README.md":
            continue
        fm, body = read_frontmatter(vault, p)
        if fm is None:
            continue
        resolved_at = fm.get("date_resolved") or fm.get("date")
        title_line = next((l for l in body.splitlines() if l.startswith("# ")), "")
        question = title_line[2:].strip() or p.stem
        out.append(
            {
                "path": vault.relative(p),
                "question": question,
                "resolved_at": resolved_at,
                "ref": extract_ref(body),
            }
        )
    return out


def seed(
    vault: Vault, existing: Knowledge | None = None, deck: str = "karpathy"
) -> tuple[Knowledge, SeedReport]:
    report = SeedReport()
    by_slug: dict[str, Concept] = {}
    if existing is not None:
        by_slug = {c.slug: c for c in existing.concepts}

    seen_slugs: set[str] = set()
    topic_index = _index_topic_notes(vault, report)

    for topic_path, info in topic_index.items():
        fm = info["fm"]
        stem = info["stem"]
        unit = _unit_from_frontmatter(fm)
        sources = _sources_from_frontmatter(fm)
        seen_at_file: set[str] = set()
        slug_by_line: dict[int, str] = {}

        for h in info["headings"]:
            base_slug = _concept_slug(stem, h.text)
            slug = base_slug
            n = 2
            while slug in seen_at_file:
                slug = f"{base_slug}-{n}"
                n += 1
            seen_at_file.add(slug)
            seen_slugs.add(slug)
            slug_by_line[h.line_no] = slug

            if slug in by_slug:
                c = by_slug[slug]
                c.title = h.text
                c.unit = unit
                c.notes_ref = topic_path
                c.sources = sources
                report.concepts_refreshed += 1
            else:
                c = Concept(
                    slug=slug,
                    title=h.text,
                    unit=unit,
                    notes_ref=topic_path,
                    sources=sources,
                )
                by_slug[slug] = c
                report.concepts_created += 1
        info["slug_by_line"] = slug_by_line

    for slug in by_slug:
        if slug not in seen_slugs:
            report.concepts_orphaned.append(slug)

    # --- card refs: map each card to a concept via Ref: resolution ---
    existing_card_state: dict[str, dict[str, CardRef]] = {
        c.slug: {cr.path: cr for cr in c.card_refs} for c in by_slug.values()
    }
    new_card_refs: dict[str, list[CardRef]] = {slug: [] for slug in by_slug}
    card_to_resolved_slug: dict[str, str] = {}

    for card_path, ref_content in _index_cards(vault, deck):
        path, anchor = parse_ref(ref_content)
        if not anchor:
            # References 06-Doubts-Resolved or a .py file directly — not a
            # topic-heading concept ref in this pass.
            continue
        info = topic_index.get(path)
        if info is None:
            report.cards_unresolved.append((card_path, ref_content))
            continue
        resolution = resolve_anchor_detailed(anchor, info["headings"])
        if resolution.status == "ambiguous":
            report.cards_ambiguous.append(
                (card_path, ref_content, [h.line_no for h in resolution.matches])
            )
            continue
        resolved = resolution.heading
        if resolved is None:
            report.cards_unresolved.append((card_path, ref_content))
            continue
        target_slug = info["slug_by_line"].get(
            resolved.line_no, _concept_slug(info["stem"], resolved.text)
        )
        if target_slug not in new_card_refs:
            # Duplicate-heading suffix wasn't reproduced (rare) — skip safely.
            report.cards_unresolved.append((card_path, ref_content))
            continue
        prior = existing_card_state.get(target_slug, {}).get(card_path)
        new_card_refs[target_slug].append(
            prior if prior is not None else CardRef(path=card_path)
        )
        card_to_resolved_slug[card_path] = target_slug
        report.cards_resolved += 1

    for slug, refs in new_card_refs.items():
        by_slug[slug].card_refs = refs

    # --- doubts: attach only the ones whose OWN Ref: line resolves to a
    # topic heading (exact/prefix, same as cards). Everything else — most
    # doubts have no Ref: line at all — is reported for manual linking; it
    # never blocks `today`, which only looks at *open* doubts.
    doubts = _index_doubts(vault)
    for d in doubts:
        ref_content = d.get("ref")
        slug = None
        if ref_content:
            path, anchor = parse_ref(ref_content)
            info = topic_index.get(path)
            if info is not None and anchor:
                resolved = resolve_anchor(anchor, info["headings"])
                if resolved is not None:
                    candidate = _concept_slug(info["stem"], resolved.text)
                    if candidate in by_slug:
                        slug = candidate
        if slug is None:
            report.doubts_unlinked.append(d["path"])
            continue
        target = by_slug[slug]
        already = any(dd.resolution_ref == d["path"] for dd in target.doubts)
        if already:
            continue
        target.doubts.append(
            Doubt(
                question=d["question"],
                raised_at=_as_date(d["resolved_at"], date(2026, 1, 1)),
                status="resolved",
                resolved_at=_as_date(d["resolved_at"], date(2026, 1, 1)),
                resolution_ref=d["path"],
            )
        )

    result = Knowledge(concepts=list(by_slug.values()))
    return result, report
