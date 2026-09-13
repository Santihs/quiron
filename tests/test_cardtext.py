from quiron.cardtext import (
    count_enumeration_items,
    jaccard,
    normalize_tokens,
    split_qa,
    word_count,
)
from quiron.cardtext import parse_qa


def test_split_qa_basic():
    body = "Que es X?\n\n---\n\nEs Y.\n\nRef: `02-Topics/x.md`\n"
    q, a = split_qa(body)
    assert q == "Que es X?"
    assert a.startswith("Es Y.")


def test_split_qa_no_separator_returns_whole_body_as_question():
    q, a = split_qa("solo texto sin separador")
    assert q == "solo texto sin separador"
    assert a == ""


def test_parse_qa_marks_missing_separator_as_malformed():
    parsed = parse_qa("solo texto sin separador")

    assert not parsed.valid
    assert parsed.reason == "missing_separator"


def test_normalize_tokens_strips_accents_and_short_words():
    tokens = normalize_tokens("¿Qué es un vector unitario?")
    assert "vector" in tokens
    assert "unitario" in tokens
    assert "que" not in tokens  # too short after normalize (3 chars)
    assert "un" not in tokens


def test_jaccard_identical_sets():
    a = {"vector", "unitario"}
    assert jaccard(a, a) == 1.0


def test_jaccard_disjoint_sets():
    assert jaccard({"vector"}, {"matriz"}) == 0.0


def test_jaccard_empty_set_is_zero_not_crash():
    assert jaccard(set(), {"vector"}) == 0.0


def test_count_enumeration_items_bullets():
    answer = "Intro\n- uno\n- dos\n- tres\n- cuatro\nfinal"
    assert count_enumeration_items(answer) == 4


def test_count_enumeration_items_numbered():
    answer = "1. uno\n2. dos\n3. tres"
    assert count_enumeration_items(answer) == 3


def test_count_enumeration_items_prose_has_zero():
    answer = "Esto es una respuesta en prosa, sin listas, con comas, como esta."
    assert count_enumeration_items(answer) == 0


def test_word_count():
    assert word_count("uno dos tres") == 3
    assert word_count("") == 0
