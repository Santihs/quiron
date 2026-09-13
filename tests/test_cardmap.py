from quiron.cardmap import card_to_concept, duplicate_card_paths
from quiron.schema import CardRef, Concept, Knowledge


def test_card_to_concept_maps_every_card_ref():
    k = Knowledge(
        concepts=[
            Concept(
                slug="a",
                title="A",
                unit="phase-0",
                card_refs=[
                    CardRef(path="04-Quiz-Bank/karpathy/a1.md"),
                    CardRef(path="04-Quiz-Bank/karpathy/a2.md"),
                ],
            ),
            Concept(
                slug="b",
                title="B",
                unit="phase-0",
                card_refs=[CardRef(path="04-Quiz-Bank/karpathy/b1.md")],
            ),
        ]
    )
    mapping = card_to_concept(k)
    assert mapping == {
        "04-Quiz-Bank/karpathy/a1.md": "a",
        "04-Quiz-Bank/karpathy/a2.md": "a",
        "04-Quiz-Bank/karpathy/b1.md": "b",
    }


def test_card_to_concept_empty_knowledge():
    assert card_to_concept(Knowledge()) == {}


def test_duplicate_card_paths_are_reported_and_first_owner_is_stable():
    path = "04-Quiz-Bank/karpathy/shared.md"
    k = Knowledge(
        concepts=[
            Concept(
                slug="a", title="A", unit="phase-0", card_refs=[CardRef(path=path)]
            ),
            Concept(
                slug="b", title="B", unit="phase-0", card_refs=[CardRef(path=path)]
            ),
        ]
    )

    assert card_to_concept(k)[path] == "a"
    assert duplicate_card_paths(k) == {path: ["a", "b"]}
