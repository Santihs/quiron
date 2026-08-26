from datetime import date

from quiron.schema import Concept, Evidence, Knowledge, Source
from quiron.sources import yield_by_source

TODAY = date(2026, 8, 25)


def test_concept_with_two_sources_counts_toward_both():
    k = Knowledge(
        concepts=[
            Concept(
                slug="x",
                title="X",
                unit="phase-0",
                sources=[Source(kind="book", ref="Axler cap.5"), Source(kind="course", ref="devtalles secc.4")],
            )
        ]
    )
    rows = {r.ref: r for r in yield_by_source(k)}
    assert rows["Axler cap.5"].concept_count == 1
    assert rows["devtalles secc.4"].concept_count == 1


def test_explained_and_applied_counts_derive_from_understanding():
    k = Knowledge(
        concepts=[
            Concept(
                slug="a",
                title="A",
                unit="phase-0",
                sources=[Source(kind="book", ref="Axler cap.5")],
                evidence=[Evidence(kind="applied", at=TODAY, ref="x.py")],
            ),
            Concept(
                slug="b",
                title="B",
                unit="phase-0",
                sources=[Source(kind="book", ref="Axler cap.5")],
                evidence=[Evidence(kind="explained", at=TODAY, ref="x.md")],
            ),
            Concept(
                slug="c",
                title="C",
                unit="phase-0",
                sources=[Source(kind="book", ref="Axler cap.5")],
                evidence=[Evidence(kind="encountered", at=TODAY, ref="log.md")],
            ),
        ]
    )
    rows = yield_by_source(k)
    assert len(rows) == 1
    row = rows[0]
    assert row.concept_count == 3
    assert row.explained_count == 2  # a (applied) + b (explained)
    assert row.applied_count == 1  # a only


def test_sorted_by_concept_count_descending():
    k = Knowledge(
        concepts=[
            Concept(slug="a", title="A", unit="phase-0", sources=[Source(kind="book", ref="small")]),
            Concept(slug="b", title="B", unit="phase-0", sources=[Source(kind="book", ref="big")]),
            Concept(slug="c", title="C", unit="phase-0", sources=[Source(kind="book", ref="big")]),
        ]
    )
    rows = yield_by_source(k)
    assert [r.ref for r in rows] == ["big", "small"]


def test_no_sources_produces_empty_list():
    k = Knowledge(concepts=[Concept(slug="a", title="A", unit="phase-0")])
    assert yield_by_source(k) == []
