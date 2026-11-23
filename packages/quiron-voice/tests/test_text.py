import pytest

from quiron_voice.text import chunks, to_speech


def test_strips_frontmatter_code_and_comments():
    md = "---\ntags: [x]\n---\n# Title\n\nHello.\n```py\nprint(1)\n```\n<!-- hidden -->\nBye."
    out = to_speech(md)
    assert "tags" not in out and "print" not in out and "hidden" not in out
    assert "Title" in out and "Hello." in out and "Bye." in out


def test_links_keep_their_label():
    assert to_speech("see [[Linear-Algebra|álgebra]] and [docs](http://x)") == "see álgebra and docs"
    assert to_speech("see [[Probability]]") == "see Probability"
    assert to_speech("img ![[plot.png]] end") == "img end"


def test_callouts_bullets_tables_inline_code():
    md = "> [!concepto] MSE — error\n- one\n1. two\n| a | b |\n|---|---|\nuse `np.cov` now"
    out = to_speech(md)
    assert "[!" not in out and "|" not in out and "`" not in out and "---" not in out
    assert "MSE" in out and "one" in out and "two" in out and "np.cov" in out


def test_paragraph_breaks_survive_and_collapse():
    assert to_speech("a\n\n\n\nb") == "a\n\nb"


def test_chunks_split_on_sentences_and_paragraphs():
    assert chunks("Uno. Dos? Tres!\n\nCuatro") == ["Uno.", "Dos?", "Tres!", "Cuatro"]


def test_chunks_respect_max_chars():
    long = ", ".join(["palabra"] * 80) + "."
    parts = chunks(long, max_chars=60)
    assert all(0 < len(p) <= 60 for p in parts)
    assert " ".join(parts).replace(" ", "") == long.replace(" ", "")


def test_chunks_hard_wrap_without_spaces():
    parts = chunks("x" * 25, max_chars=10)
    assert parts == ["x" * 10, "x" * 10, "x" * 5]


def test_chunks_empty_and_invalid():
    assert chunks("   \n\n ") == []
    with pytest.raises(ValueError):
        chunks("a", max_chars=0)
