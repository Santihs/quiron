from quiron.headings import (
    concept_headings,
    extract_headings,
    extract_ref,
    is_concept_heading,
    parse_ref,
    resolve_anchor,
    slugify,
)
from quiron.vault import read_frontmatter


def _body(vault, *parts):
    p = vault.path(*parts)
    _, body = read_frontmatter(vault, p)
    return body


def test_extract_headings_levels_and_order(vault):
    body = _body(vault, "02-Topics", "Coding-the-Matrix-Inner-Product.md")
    headings = extract_headings(body)
    texts = [h.text for h in headings]
    assert "8.1 — El fire engine problem" in texts
    assert "8.3 — Orthogonality" in texts
    assert "8.3.2 — Descomposicion paralela + ortogonal" in texts
    # order preserved
    assert texts.index("8.1 — El fire engine problem") < texts.index(
        "8.3 — Orthogonality"
    )


def test_extract_headings_ignores_fenced_code():
    body = "## Real\n\n```markdown\n## Not a concept\n```\n\n### Also real\n"

    assert [h.text for h in extract_headings(body)] == ["Real", "Also real"]


def test_duplicate_heading_both_present(vault):
    body = _body(vault, "02-Topics", "Coding-the-Matrix-Inner-Product.md")
    headings = extract_headings(body)
    dupes = [h for h in headings if h.text == "Implementacion propia"]
    assert len(dupes) == 2
    assert dupes[0].line_no < dupes[1].line_no


def test_denylist_filters_structural_headings(vault):
    body = _body(vault, "02-Topics", "Coding-the-Matrix-Inner-Product.md")
    concepts = concept_headings(body)
    texts = {h.text for h in concepts}
    assert "Implementacion propia" not in texts
    assert "Por que importa para ML/AI" not in texts
    assert "Doubts Resolved" not in texts
    assert "Ver tambien" not in texts
    assert "8.3 — Orthogonality" in texts


def test_second_h1_mid_file_does_not_break_h2_extraction(vault):
    body = _body(vault, "02-Topics", "Probability-Fundamentals.md")
    headings = extract_headings(body)
    texts = {h.text for h in headings}
    assert "Sum Rule, Product Rule y Bayes' Theorem" in texts
    assert "Parte 2, seccion 5" in texts


def test_parse_ref_with_anchor_containing_em_dash():
    path, anchor = parse_ref("02-Topics/X.md — 8.3 — Orthogonality")
    assert path == "02-Topics/X.md"
    assert anchor == "8.3 — Orthogonality"


def test_parse_ref_no_anchor():
    path, anchor = parse_ref("06-Doubts-Resolved/span-de-vectores.md")
    assert path == "06-Doubts-Resolved/span-de-vectores.md"
    assert anchor is None


def test_parse_ref_py_target_no_anchor():
    path, anchor = parse_ref("05-Projects/coding-the-matrix/src/x.py")
    assert path.endswith("x.py")
    assert anchor is None


def test_resolve_anchor_exact_match():
    from quiron.headings import Heading

    headings = [Heading(level=2, text="8.3 — Orthogonality", line_no=10)]
    h = resolve_anchor("8.3 — Orthogonality", headings)
    assert h is not None and h.line_no == 10


def test_resolve_anchor_prefix_match():
    from quiron.headings import Heading

    headings = [Heading(level=2, text="12. El Annihilator (6.5)", line_no=20)]
    h = resolve_anchor("12. El Annihilator", headings)
    assert h is not None and h.line_no == 20


def test_resolve_anchor_unresolved():
    from quiron.headings import Heading

    headings = [Heading(level=2, text="8.3 — Orthogonality", line_no=10)]
    h = resolve_anchor("Parte 1, seccion 1", headings)
    assert h is None


def test_resolve_anchor_detailed_reports_ambiguous_prefix():
    from quiron.headings import Heading, resolve_anchor_detailed

    result = resolve_anchor_detailed(
        "8.3",
        [
            Heading(level=2, text="8.3 — Orthogonality", line_no=10),
            Heading(level=2, text="8.3 — Applications", line_no=20),
        ],
    )

    assert result.status == "ambiguous"
    assert len(result.matches) == 2
    assert resolve_anchor("8.3", result.matches) is None


def test_extract_ref_from_card(vault):
    _, body = read_frontmatter(
        vault, vault.path("04-Quiz-Bank", "karpathy", "annihilator-definicion.md")
    )
    ref = extract_ref(body)
    assert ref == "02-Topics/Coding-the-Matrix-Inner-Product.md — 12. El Annihilator"


def test_end_to_end_101_style_prefix_resolution(vault):
    """The 101/136-case pattern: ref anchor is a prefix of the real heading."""
    topic_body = _body(vault, "02-Topics", "Coding-the-Matrix-Inner-Product.md")
    headings = concept_headings(topic_body)

    card_body = _body(vault, "04-Quiz-Bank", "karpathy", "annihilator-definicion.md")
    ref = extract_ref(card_body)
    assert ref is not None
    path, anchor = parse_ref(ref)
    assert path == "02-Topics/Coding-the-Matrix-Inner-Product.md"
    assert anchor is not None
    resolved = resolve_anchor(anchor, headings)
    assert resolved is not None
    assert resolved.text == "12. El Annihilator (6.5)"


def test_end_to_end_exact_resolution(vault):
    topic_body = _body(vault, "02-Topics", "Coding-the-Matrix-Inner-Product.md")
    headings = concept_headings(topic_body)

    card_body = _body(vault, "04-Quiz-Bank", "karpathy", "orthogonality-exact.md")
    ref = extract_ref(card_body)
    assert ref is not None
    path, anchor = parse_ref(ref)
    assert anchor is not None
    resolved = resolve_anchor(anchor, headings)
    assert resolved is not None
    assert resolved.text == "8.3 — Orthogonality"


def test_end_to_end_unresolvable(vault):
    topic_body = _body(vault, "02-Topics", "Probability-Fundamentals.md")
    headings = concept_headings(topic_body)

    card_body = _body(vault, "04-Quiz-Bank", "karpathy", "unresolvable-ref.md")
    ref = extract_ref(card_body)
    assert ref is not None
    path, anchor = parse_ref(ref)
    resolved = resolve_anchor(anchor, headings) if anchor else None
    assert resolved is None


def test_slugify():
    assert slugify("8.3 — Orthogonality") == "8-3-orthogonality"
    assert slugify("12. El Annihilator (6.5)") == "12-el-annihilator-6-5"
