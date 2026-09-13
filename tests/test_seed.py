from quiron.schema import CardRef, Concept, Evidence, Knowledge
from quiron.seed import seed
from quiron.vault import Vault


def test_seed_creates_concepts_from_headings(vault):
    result, report = seed(vault)
    slugs = {c.slug for c in result.concepts}
    assert "coding-the-matrix-inner-product--8-3-orthogonality" in slugs
    assert "coding-the-matrix-inner-product--12-el-annihilator-6-5" in slugs
    # denylisted headings never become concepts
    assert not any("implementacion-propia" in s for s in slugs)
    assert report.concepts_created == len(result.concepts)


def test_seed_skips_structural_headings_and_reports_them(vault):
    _, report = seed(vault)
    assert any("Implementacion propia" in h for h in report.headings_skipped)
    assert any("Doubts Resolved" in h for h in report.headings_skipped)


def test_seed_resolves_card_by_prefix_match(vault):
    result, report = seed(vault)
    c = next(
        c
        for c in result.concepts
        if c.slug == "coding-the-matrix-inner-product--12-el-annihilator-6-5"
    )
    assert len(c.card_refs) == 1
    assert c.card_refs[0].path == "04-Quiz-Bank/karpathy/annihilator-definicion.md"


def test_seed_resolves_card_by_exact_match(vault):
    result, _ = seed(vault)
    c = next(
        c
        for c in result.concepts
        if c.slug == "coding-the-matrix-inner-product--8-3-orthogonality"
    )
    paths = {cr.path for cr in c.card_refs}
    assert "04-Quiz-Bank/karpathy/orthogonality-exact.md" in paths


def test_seed_reports_unresolvable_card_ref(vault):
    _, report = seed(vault)
    unresolved_paths = {p for p, _ in report.cards_unresolved}
    assert "04-Quiz-Bank/karpathy/unresolvable-ref.md" in unresolved_paths


def test_seed_links_doubt_with_own_ref_line(vault):
    result, report = seed(vault)
    c = next(
        c
        for c in result.concepts
        if c.slug == "coding-the-matrix-inner-product--8-3-orthogonality"
    )
    resolution_refs = {d.resolution_ref for d in c.doubts}
    assert (
        "06-Doubts-Resolved/ortogonalidad-por-que-se-define-asi.md" in resolution_refs
    )


def test_seed_reports_unlinked_doubt(vault):
    _, report = seed(vault)
    # span-de-vectores.md has no Ref: line of its own — only reachable by
    # manual linking, per v7 ("las demas se listan ... para adjuntar a mano").
    assert "06-Doubts-Resolved/span-de-vectores.md" in report.doubts_unlinked


def test_seed_is_idempotent_byte_identical(vault):
    result1, _ = seed(vault)
    result2, _ = seed(vault, existing=result1)
    assert result1.model_dump_json() == result2.model_dump_json()


def test_seed_never_overwrites_evidence_doubts_card_policy(vault):
    result1, _ = seed(vault)
    slug = "coding-the-matrix-inner-product--8-3-orthogonality"
    c = next(c for c in result1.concepts if c.slug == slug)
    c.evidence.append(Evidence(kind="applied", at="2026-08-25", ref="scripts/pca.py"))
    c.card_policy = "needed"
    c.declined_reason = None

    result2, _ = seed(vault, existing=result1)
    c2 = next(c for c in result2.concepts if c.slug == slug)
    assert c2.evidence[0].kind == "applied"
    assert c2.card_policy == "needed"


def test_seed_preserves_card_quality_by_path_on_refresh(vault):
    result1, _ = seed(vault)
    slug = "coding-the-matrix-inner-product--8-3-orthogonality"
    c = next(c for c in result1.concepts if c.slug == slug)
    for cr in c.card_refs:
        if cr.path == "04-Quiz-Bank/karpathy/orthogonality-exact.md":
            cr.quality = "ok"
            cr.reviewed_at = "2026-08-20"

    result2, _ = seed(vault, existing=result1)
    c2 = next(c for c in result2.concepts if c.slug == slug)
    target = next(
        cr
        for cr in c2.card_refs
        if cr.path == "04-Quiz-Bank/karpathy/orthogonality-exact.md"
    )
    assert target.quality == "ok"
    assert str(target.reviewed_at) == "2026-08-20"


def test_seed_topic_note_without_frontmatter_still_seeds(tmp_path):
    v = Vault(root=tmp_path)
    d = tmp_path / "02-Topics"
    d.mkdir()
    v.write_text(
        d / "Skills.md", "# Skills\n\nReusable behaviors.\n\n## Notas\n\nsome text\n"
    )

    result, _ = seed(v)
    assert [c.slug for c in result.concepts] == ["skills--skills"]
    assert result.concepts[0].title == "Skills"


def test_seed_file_level_concept_when_only_denylisted_headings(tmp_path):
    v = Vault(root=tmp_path)
    d = tmp_path / "02-Topics"
    d.mkdir()
    v.write_text(
        d / "Hooks.md",
        "# Hooks\n\nShell commands run on events.\n\n## Visto en\n\n- a\n\n## Notas\n\nmore\n",
    )

    result, report = seed(v)
    assert len(result.concepts) == 1
    assert result.concepts[0].title == "Hooks"
    assert any("Visto en" in h for h in report.headings_skipped)
    assert any("Notas" in h for h in report.headings_skipped)


def test_seed_file_level_concept_falls_back_to_stem_without_h1(tmp_path):
    v = Vault(root=tmp_path)
    d = tmp_path / "02-Topics"
    d.mkdir()
    v.write_text(d / "Worktrees.md", "## Visto en\n\n- a\n")

    result, _ = seed(v)
    assert result.concepts[0].title == "Worktrees"


def test_seed_normal_heading_note_unaffected_by_fallback(tmp_path):
    v = Vault(root=tmp_path)
    d = tmp_path / "02-Topics"
    d.mkdir()
    v.write_text(
        d / "Multi.md", "# Multi\n\n## Concept A\n\ntext\n\n## Concept B\n\ntext\n"
    )

    result, _ = seed(v)
    assert {c.title for c in result.concepts} == {"Concept A", "Concept B"}


def test_seed_deck_param_reads_different_folder(tmp_path):
    v = Vault(root=tmp_path)
    topics = tmp_path / "02-Topics"
    topics.mkdir()
    v.write_text(topics / "X.md", "# X\n\n## Foo\n\ntext\n")

    devtalles_deck = tmp_path / "04-Quiz-Bank" / "devtalles"
    devtalles_deck.mkdir(parents=True)
    v.write_text(
        devtalles_deck / "a.md",
        "---\ntags:\n  - repo-devtalles\nnoteId: 1\n---\nQ\n\n---\n\nA\n\nRef: `02-Topics/X.md — Foo`\n",
    )

    result_default, _ = seed(v)
    assert result_default.concepts[0].card_refs == []

    result_devtalles, report = seed(v, deck="devtalles")
    assert report.cards_resolved == 1
    assert (
        result_devtalles.concepts[0].card_refs[0].path == "04-Quiz-Bank/devtalles/a.md"
    )


def test_seed_reports_orphaned_concept_not_deleted(vault):
    result1, _ = seed(vault)
    ghost = Concept(slug="ghost--slug", title="Ghost", unit="phase-0")
    result1.concepts.append(ghost)

    result2, report = seed(vault, existing=result1)
    slugs = {c.slug for c in result2.concepts}
    assert "ghost--slug" in slugs
    assert "ghost--slug" in report.concepts_orphaned


def test_seed_reports_ambiguous_duplicate_heading_reference(tmp_path):
    v = Vault(root=tmp_path)
    topics = tmp_path / "02-Topics"
    topics.mkdir()
    v.write_text(topics / "X.md", "# X\n\n## Duplicate\n\n## Duplicate\n")
    deck = tmp_path / "04-Quiz-Bank" / "karpathy"
    deck.mkdir(parents=True)
    v.write_text(
        deck / "x.md",
        "Question\n\n---\n\nAnswer\n\nRef: `02-Topics/X.md — Duplicate`\n",
    )

    result, report = seed(v)

    assert {c.slug for c in result.concepts} == {"x--duplicate", "x--duplicate-2"}
    assert report.cards_resolved == 0
    assert report.cards_ambiguous == [
        ("04-Quiz-Bank/karpathy/x.md", "02-Topics/X.md — Duplicate", [3, 5])
    ]
