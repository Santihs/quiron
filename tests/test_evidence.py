from datetime import date

from quiron.evidence import add_evidence
from quiron.schema import CardRef, Concept, Knowledge


def _knowledge_with_card():
    return Knowledge(
        concepts=[
            Concept(
                slug="eigenvectores",
                title="Eigenvectores",
                unit="phase-0",
                card_refs=[CardRef(path="04-Quiz-Bank/karpathy/eig.md")],
            )
        ]
    )


def test_add_evidence_appends_to_mapped_concept():
    k = _knowledge_with_card()
    result = add_evidence(
        k,
        card_path="04-Quiz-Bank/karpathy/eig.md",
        kind="explained",
        ref="05-Explanations/eig.md",
        scope="interpretacion geometrica",
        today=date(2026, 8, 25),
    )
    assert result.slug == "eigenvectores"
    assert result.concept_title == "Eigenvectores"

    concept = k.concepts[0]
    assert len(concept.evidence) == 1
    ev = concept.evidence[0]
    assert ev.kind == "explained"
    assert ev.ref == "05-Explanations/eig.md"
    assert ev.scope == "interpretacion geometrica"
    assert ev.at == date(2026, 8, 25)


def test_add_evidence_defaults_at_to_today():
    k = _knowledge_with_card()
    add_evidence(
        k, card_path="04-Quiz-Bank/karpathy/eig.md", kind="explained", ref="x.md"
    )
    assert k.concepts[0].evidence[0].at == date.today()


def test_add_evidence_unmapped_card_leaves_knowledge_untouched():
    k = _knowledge_with_card()
    before = k.model_dump()
    result = add_evidence(
        k, card_path="04-Quiz-Bank/karpathy/nope.md", kind="explained", ref="x.md"
    )
    assert result.slug is None
    assert result.concept_title is None
    assert k.model_dump() == before


def test_add_evidence_operation_is_idempotent():
    k = _knowledge_with_card()

    first = add_evidence(
        k,
        card_path="04-Quiz-Bank/karpathy/eig.md",
        kind="explained",
        ref="x.md",
        operation_id="op-1",
    )
    second = add_evidence(
        k,
        card_path="04-Quiz-Bank/karpathy/eig.md",
        kind="explained",
        ref="x.md",
        operation_id="op-1",
    )

    assert first.changed
    assert not second.changed
    assert len(k.concepts[0].evidence) == 1
