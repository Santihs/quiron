from datetime import date

from quiron.nextup import candidates, is_blocked
from quiron.schema import CardRef, Concept, Doubt, Evidence, Knowledge

TODAY = date(2026, 8, 25)


def test_blocked_excludes_concept_entirely():
    k = Knowledge(
        concepts=[
            Concept(slug="prereq", title="Prereq", unit="phase-0"),
            Concept(
                slug="advanced",
                title="Advanced",
                unit="phase-0",
                prerequisites=["prereq"],
                doubts=[Doubt(question="q", raised_at=TODAY, status="open")],
            ),
        ]
    )
    result = candidates(k, today=TODAY)
    # "prereq" itself is unseen with no signal of its own, so it legitimately
    # shows up as a no_explained candidate — only "advanced" is excluded.
    assert "advanced" not in [c.slug for c in result]


def test_missing_prerequisite_slug_is_treated_as_satisfied():
    k = Knowledge(
        concepts=[
            Concept(slug="advanced", title="Advanced", unit="phase-0", prerequisites=["ghost"]),
        ]
    )
    by_slug = {c.slug: c for c in k.concepts}
    assert is_blocked(k.concepts[0], by_slug) is False


def test_open_doubt_ranks_above_coverage_gap():
    k = Knowledge(
        concepts=[
            Concept(
                slug="gap",
                title="Gap",
                unit="phase-0",
                card_policy="needed",
                evidence=[Evidence(kind="applied", at=TODAY, ref="x.py")],
            ),
            Concept(
                slug="doubty",
                title="Doubty",
                unit="phase-0",
                doubts=[Doubt(question="q", raised_at=date(2026, 7, 20), status="open")],
                evidence=[Evidence(kind="applied", at=TODAY, ref="x.py")],
            ),
        ]
    )
    result = candidates(k, today=TODAY)
    assert [c.reason for c in result] == ["open_doubt", "coverage_gap"]
    assert result[0].slug == "doubty"
    assert result[0].detail == "36d"


def test_applied_with_open_doubt_still_appears_as_open_doubt():
    k = Knowledge(
        concepts=[
            Concept(
                slug="x",
                title="X",
                unit="phase-0",
                evidence=[Evidence(kind="applied", at=TODAY, ref="x.py")],
                doubts=[Doubt(question="q", raised_at=TODAY, status="open")],
            )
        ]
    )
    result = candidates(k, today=TODAY)
    assert len(result) == 1
    assert result[0].reason == "open_doubt"


def test_unblocked_concept_with_no_evidence_yet():
    k = Knowledge(
        concepts=[
            Concept(slug="prereq", title="Prereq", unit="phase-0", evidence=[Evidence(kind="explained", at=TODAY, ref="x.md")]),
            Concept(slug="next-up", title="Next up", unit="phase-0", prerequisites=["prereq"]),
        ]
    )
    result = candidates(k, today=TODAY)
    next_up = next(c for c in result if c.slug == "next-up")
    assert next_up.reason == "unblocked"


def test_no_explained_catchall():
    k = Knowledge(
        concepts=[
            Concept(slug="x", title="X", unit="phase-0", evidence=[Evidence(kind="encountered", at=TODAY, ref="log.md")]),
        ]
    )
    result = candidates(k, today=TODAY)
    assert [c.reason for c in result] == ["no_explained"]


def test_concept_with_explained_evidence_and_no_signal_drops_off():
    k = Knowledge(
        concepts=[
            Concept(slug="x", title="X", unit="phase-0", evidence=[Evidence(kind="explained", at=TODAY, ref="x.md")]),
        ]
    )
    assert candidates(k, today=TODAY) == []


def test_oldest_open_doubt_ranks_first_among_doubts():
    k = Knowledge(
        concepts=[
            Concept(slug="newer", title="Newer", unit="phase-0", doubts=[Doubt(question="q", raised_at=date(2026, 8, 20), status="open")]),
            Concept(slug="older", title="Older", unit="phase-0", doubts=[Doubt(question="q", raised_at=date(2026, 7, 1), status="open")]),
        ]
    )
    result = candidates(k, today=TODAY)
    assert [c.slug for c in result] == ["older", "newer"]
