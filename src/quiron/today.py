"""quiron today — the single entry point. Prints red/yellow/white lines.

Tier rule (v7): red only means something is WRONG. A concept with no cards,
or an unprocessed inbox, is never red — those are decisions not yet made.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .capture import load_inbox
from .schema import Knowledge

STALE_DAYS = 14
NEGLECTED_DAYS = 30


@dataclass
class Line:
    tier: str  # red | yellow | white
    text: str
    action: str | None = None


def _parse_date(d) -> date:
    if isinstance(d, date):
        return d
    return datetime.strptime(str(d), "%Y-%m-%d").date()


def doubt_age_state(raised_at, today: date | None = None) -> str:
    today = today or date.today()
    age = (today - _parse_date(raised_at)).days
    if age > NEGLECTED_DAYS:
        return "neglected"
    if age >= STALE_DAYS:
        return "stale"
    return "fresh"


def build_report(
    vault,
    knowledge: Knowledge,
    unresolved_refs: list[tuple[str, str]] | None = None,
    today: date | None = None,
) -> list[Line]:
    today = today or date.today()
    lines: list[Line] = []

    unresolved_refs = unresolved_refs or []
    if unresolved_refs:
        lines.append(
            Line(
                tier="red",
                text=f"{len(unresolved_refs)} tarjetas con Ref: irresoluble",
                action="quiron doctor",
            )
        )

    open_doubts = 0
    resolved_doubts = 0
    for c in knowledge.concepts:
        for d in c.doubts:
            if d.status != "open":
                resolved_doubts += 1
                continue
            open_doubts += 1
            state = doubt_age_state(d.raised_at, today)
            age = (today - _parse_date(d.raised_at)).days
            if state == "neglected":
                lines.append(
                    Line(
                        tier="red",
                        text=f'duda abierta {age}d · "{d.question}"',
                    )
                )
            elif state == "stale":
                lines.append(
                    Line(
                        tier="yellow",
                        text=f'duda abierta {age}d · "{d.question}"',
                    )
                )

    inbox = load_inbox(vault)
    unprocessed = [e for e in inbox if not e.get("processed", False)]
    if unprocessed:
        lines.append(
            Line(
                tier="yellow",
                text=f"{len(unprocessed)} capturas sin procesar",
                action="/quiron-inbox",
            )
        )

    undecided = [c for c in knowledge.concepts if c.card_policy == "undecided"]
    if undecided:
        lines.append(
            Line(
                tier="yellow",
                text=f"{len(undecided)} conceptos sin decision de retencion",
                action="quiron cards --decide",
            )
        )

    lines.append(
        Line(tier="white", text=f"{open_doubts} dudas abiertas · {resolved_doubts} resueltas")
    )

    return lines


def render(lines: list[Line]) -> str:
    symbol = {"red": "\U0001f534", "yellow": "\U0001f7e1", "white": "⚪"}
    out = []
    for l in lines:
        row = f"{symbol[l.tier]}  {l.text}"
        if l.action:
            row += f"  -> {l.action}"
        out.append(row)
    return "\n".join(out)
