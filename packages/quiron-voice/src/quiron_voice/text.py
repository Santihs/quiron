"""Turn markdown/notes into text a TTS engine can read naturally. Pure functions."""

from __future__ import annotations

import re

_FRONTMATTER = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.S)
_CODE_FENCE = re.compile(r"```.*?```", re.S)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_EMBED = re.compile(r"!\[\[.*?\]\]")
_WIKILINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_MDLINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_TABLE_RULE = re.compile(r"^\s*\|?[-:| ]+\|[-:| ]*$", re.M)
_CALLOUT = re.compile(r"^\s*>\s*\[![^\]]*\][+-]?\s*", re.M)
_BULLET = re.compile(r"^\s*(?:[-+*]|\d+\.)\s+", re.M)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_MARKUP = re.compile(r"[#*_>|~]+")
_SPACES = re.compile(r"[ \t]+")
_SENTENCE_END = re.compile(r"(?<=[.!?:;])\s+|\n{2,}")
_COMMA = re.compile(r"(?<=,)\s+")


def to_speech(markdown: str) -> str:
    """Strip markdown/Obsidian syntax; keep the words a listener needs.

    Paragraph breaks survive as a blank line so `chunks` can split on them.
    """
    t = _FRONTMATTER.sub("", markdown)
    t = _CODE_FENCE.sub(" ", t)
    t = _HTML_COMMENT.sub(" ", t)
    t = _EMBED.sub(" ", t)
    t = _WIKILINK.sub(r"\1", t)
    t = _MDLINK.sub(r"\1", t)
    t = _TABLE_RULE.sub("", t)
    t = _CALLOUT.sub("", t)
    t = _BULLET.sub("", t)
    t = _INLINE_CODE.sub(r"\1", t)
    t = _MARKUP.sub(" ", t)
    out: list[str] = []
    for raw in t.splitlines():
        line = _SPACES.sub(" ", raw).strip()
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()


def _wrap(part: str, max_chars: int) -> list[str]:
    pieces: list[str] = []
    while len(part) > max_chars:
        cut = part.rfind(" ", 0, max_chars)
        cut = cut if cut > 0 else max_chars
        pieces.append(part[:cut].strip())
        part = part[cut:].strip()
    if part:
        pieces.append(part)
    return pieces


def chunks(text: str, max_chars: int = 300) -> list[str]:
    """Split into sentence-sized pieces so the first audio starts fast.

    Sentences longer than `max_chars` split on commas, then hard-wrap on spaces.
    Every returned piece is non-empty and at most `max_chars` long.
    """
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    pieces: list[str] = []
    for sent in _SENTENCE_END.split(text):
        sent = " ".join(sent.split())
        if not sent:
            continue
        if len(sent) <= max_chars:
            pieces.append(sent)
            continue
        buf = ""
        for part in _COMMA.split(sent):
            for sub in _wrap(part, max_chars):
                if buf and len(buf) + 1 + len(sub) > max_chars:
                    pieces.append(buf)
                    buf = sub
                else:
                    buf = f"{buf} {sub}".strip()
        if buf:
            pieces.append(buf)
    return pieces
