from quiron.coverage import coverage_gap, decide, undecided
from quiron.schema import CardRef, Concept, Knowledge


def test_coverage_gap_needed_and_empty():
    k = Knowledge(
        concepts=[
            Concept(slug="a", title="A", unit="phase-0", card_policy="needed"),
            Concept(
                slug="b",
                title="B",
                unit="phase-0",
                card_policy="needed",
                card_refs=[CardRef(path="x.md")],
            ),
            Concept(slug="c", title="C", unit="phase-0", card_policy="declined"),
            Concept(slug="d", title="D", unit="phase-0", card_policy="undecided"),
        ]
    )
    gaps = coverage_gap(k)
    assert [c.slug for c in gaps] == ["a"]


def test_declined_never_in_gap_or_undecided():
    k = Knowledge(
        concepts=[
            Concept(slug="c", title="C", unit="phase-0", card_policy="declined"),
        ]
    )
    assert coverage_gap(k) == []
    assert undecided(k) == []


def test_undecided_query():
    k = Knowledge(
        concepts=[
            Concept(slug="a", title="A", unit="phase-0"),
            Concept(slug="b", title="B", unit="phase-0", card_policy="needed"),
        ]
    )
    assert [c.slug for c in undecided(k)] == ["a"]


def test_decide_walker_applies_needed_and_declined():
    k = Knowledge(
        concepts=[
            Concept(slug="a-1", title="A", unit="phase-0"),
            Concept(slug="b-2", title="B", unit="phase-0"),
        ]
    )
    inputs = iter(["n", "d", "no lo necesito"])
    report = decide(k, input_fn=lambda: next(inputs), print_fn=lambda *_: None)

    assert report.decided == 2
    assert not report.quit_early
    a = next(c for c in k.concepts if c.slug == "a-1")
    b = next(c for c in k.concepts if c.slug == "b-2")
    assert a.card_policy == "needed"
    assert b.card_policy == "declined"
    assert b.declined_reason == "no lo necesito"


def test_decide_walker_skip_leaves_undecided():
    k = Knowledge(concepts=[Concept(slug="a", title="A", unit="phase-0")])
    inputs = iter(["s"])
    report = decide(k, input_fn=lambda: next(inputs), print_fn=lambda *_: None)
    assert report.decided == 0
    assert k.concepts[0].card_policy == "undecided"


def test_decide_walker_quit_stops_early_and_keeps_prior_decisions():
    k = Knowledge(
        concepts=[
            Concept(slug="a", title="A", unit="phase-0"),
            Concept(slug="b", title="B", unit="phase-0"),
            Concept(slug="c", title="C", unit="phase-0"),
        ]
    )
    inputs = iter(["n", "q"])
    report = decide(k, input_fn=lambda: next(inputs), print_fn=lambda *_: None)

    assert report.decided == 1
    assert report.quit_early
    by_slug = {c.slug: c for c in k.concepts}
    assert by_slug["a"].card_policy == "needed"
    assert by_slug["b"].card_policy == "undecided"
    assert by_slug["c"].card_policy == "undecided"


def test_decide_only_walks_undecided_not_already_decided():
    k = Knowledge(
        concepts=[
            Concept(slug="a", title="A", unit="phase-0", card_policy="needed"),
            Concept(slug="b", title="B", unit="phase-0"),
        ]
    )
    inputs = iter(["d", ""])
    report = decide(k, input_fn=lambda: next(inputs), print_fn=lambda *_: None)
    # only "b" was undecided — walker never touches "a" again
    assert report.decided == 1
    assert k.concepts[0].card_policy == "needed"
    assert k.concepts[1].card_policy == "declined"
