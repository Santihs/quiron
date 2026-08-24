"""Question/answer splitting and text normalization for a card body.

The card's Ref: line has already been extracted separately by
headings.extract_ref — this module only deals with the front/back text
itself, reused by every layer-1 audit check.
"""

from __future__ import annotations

import re

from .headings import normalize

QA_SEPARATOR_RE = re.compile(r"\n---\n")

MIN_TOKEN_LEN = 4  # a cheap stopword proxy: drop short/common words


def split_qa(body: str) -> tuple[str, str]:
    """Splits on the single '\\n---\\n' separator the validator enforces
    (validate-quiz-bank-lib.mjs). Body may still contain a trailing Ref:
    line — callers that care should strip it via headings.extract_ref first,
    but a leftover Ref: line only affects normalize_tokens, not correctness
    here, since it's the same handful of stopword-length words either way."""
    parts = QA_SEPARATOR_RE.split(body.strip(), maxsplit=1)
    if len(parts) != 2:
        return body.strip(), ""
    return parts[0].strip(), parts[1].strip()


def normalize_tokens(text: str) -> set[str]:
    """Lowercase, accent-stripped (via headings.normalize), word tokens,
    dropping anything under MIN_TOKEN_LEN chars."""
    n = normalize(text)
    tokens = re.split(r"[^a-z0-9]+", n)
    return {t for t in tokens if len(t) >= MIN_TOKEN_LEN}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def count_enumeration_items(answer: str) -> int:
    """Counts bullet/numbered-list lines in the answer. A card whose answer
    is a flat paragraph returns 0 regardless of comma count — commas alone
    are too noisy a signal for Spanish prose."""
    lines = answer.splitlines()
    count = 0
    for line in lines:
        stripped = line.strip()
        if re.match(r"^[-*]\s+\S", stripped) or re.match(r"^\d+[.)]\s+\S", stripped):
            count += 1
    return count


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))
