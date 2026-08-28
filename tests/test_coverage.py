from quiron.coverage import PolicyDecision, coverage_gap, decide, set_policy, undecided
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


def test_set_policy_applies_needed_and_declined_with_reason():
    k = Knowledge(
        concepts=[
            Concept(slug="a", title="A", unit="phase-0"),
            Concept(slug="b", title="B", unit="phase-0"),
        ]
    )
    report = set_policy(
        k,
        [
            PolicyDecision(slug="a", card_policy="needed"),
            PolicyDecision(slug="b", card_policy="declined", declined_reason="ya lo se de memoria"),
        ],
    )
    assert report.decided == ["a", "b"]
    assert report.skipped_unknown_slug == []
    by_slug = {c.slug: c for c in k.concepts}
    assert by_slug["a"].card_policy == "needed"
    assert by_slug["b"].card_policy == "declined"
    assert by_slug["b"].declined_reason == "ya lo se de memoria"


def test_set_policy_unknown_slug_is_skipped_not_raised():
    k = Knowledge(concepts=[Concept(slug="a", title="A", unit="phase-0")])
    report = set_policy(k, [PolicyDecision(slug="ghost", card_policy="needed")])
    assert report.decided == []
    assert report.skipped_unknown_slug == ["ghost"]
    assert k.concepts[0].card_policy == "undecided"


def test_set_policy_leaves_untargeted_concepts_undecided():
    k = Knowledge(
        concepts=[
            Concept(slug="a", title="A", unit="phase-0"),
            Concept(slug="b", title="B", unit="phase-0"),
        ]
    )
    set_policy(k, [PolicyDecision(slug="a", card_policy="needed")])
    by_slug = {c.slug: c for c in k.concepts}
    assert by_slug["a"].card_policy == "needed"
    assert by_slug["b"].card_policy == "undecided"
