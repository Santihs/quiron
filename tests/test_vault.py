import pytest

from quiron.errors import QuironError
from quiron.vault import read_note_id
from quiron.vault import split_frontmatter


def test_walk_markdown_finds_topics(vault):
    files = vault.walk_markdown("02-Topics")
    names = {p.name for p in files}
    assert "Coding-the-Matrix-Inner-Product.md" in names
    assert "Probability-Fundamentals.md" in names


def test_walk_markdown_missing_dir_returns_empty(vault):
    assert vault.walk_markdown("99-Does-Not-Exist") == []


def test_frontmatter_inline_tags():
    raw = "---\ntags: [phase-0, math]\nstatus: seed\n---\nbody text\n"
    fm, body = split_frontmatter(raw)
    assert fm is not None
    assert fm["tags"] == ["phase-0", "math"]
    assert body == "body text\n"


def test_frontmatter_block_tags():
    raw = (
        "---\ntags:\n  - repo-karpathy\n  - phase-0\nnoteId: 123\n---\nQ\n\n---\n\nA\n"
    )
    fm, body = split_frontmatter(raw)
    assert fm is not None
    assert fm["tags"] == ["repo-karpathy", "phase-0"]
    assert fm["noteId"] == 123


def test_frontmatter_date_vs_date_resolved_both_readable(vault):
    from quiron.vault import read_frontmatter

    p = vault.path("06-Doubts-Resolved", "span-de-vectores.md")
    fm, _ = read_frontmatter(vault, p)
    assert fm is not None
    assert (
        fm["date_resolved"] == "2026-07-17" or str(fm["date_resolved"]) == "2026-07-17"
    )

    p2 = vault.path("06-Doubts-Resolved", "ortogonalidad-por-que-se-define-asi.md")
    fm2, _ = read_frontmatter(vault, p2)
    assert fm2 is not None
    assert "date" in fm2 and "date_resolved" not in fm2


def test_no_frontmatter_returns_none():
    fm, body = split_frontmatter("# just a heading\nno frontmatter here\n")
    assert fm is None


def test_utf8_em_dash_roundtrip(vault, tmp_path):
    from quiron.vault import Vault

    p = tmp_path / "x.md"
    v = Vault(root=tmp_path)
    v.write_text(p, "Ref: `02-Topics/X.md — 8.3 — Orthogonality`\n")
    assert v.read_text(p) == "Ref: `02-Topics/X.md — 8.3 — Orthogonality`\n"


def test_frontmatter_accepts_bom_and_crlf():
    fm, body = split_frontmatter("\ufeff---\r\ntags: [phase-0]\r\n---\r\nbody\r\n")

    assert fm is not None
    assert fm["tags"] == ["phase-0"]
    assert body == "body\n"


def test_vault_path_rejects_traversal_and_absolute_paths(tmp_path):
    from quiron.vault import Vault

    vault = Vault(root=tmp_path)
    with pytest.raises(QuironError, match="unsafe vault path"):
        vault.path("..", "outside.txt")
    with pytest.raises(QuironError, match="unsafe vault path"):
        vault.path(str(tmp_path / "outside.txt"))


def test_read_note_id_ignores_malformed_frontmatter_value(tmp_path):
    from quiron.vault import Vault

    vault = Vault(root=tmp_path)
    card = tmp_path / "card.md"
    card.write_text("---\nnoteId: not-an-int\n---\nQ\n", encoding="utf-8")

    assert read_note_id(vault, "card.md") is None
