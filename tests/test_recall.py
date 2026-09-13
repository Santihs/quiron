from datetime import date

from quiron.recall import collect_note_ids, cross_check
from quiron.schema import CardRef, Concept, Evidence, Knowledge
from quiron.vault import Vault


def _vault_with_card(tmp_path, note_id: int) -> Vault:
    v = Vault(root=tmp_path)
    d = tmp_path / "04-Quiz-Bank" / "karpathy"
    d.mkdir(parents=True)
    v.write_text(
        d / "x.md",
        f"---\ntags:\n  - repo-karpathy\nnoteId: {note_id}\n---\nQ\n\n---\n\nA\n",
    )
    return v


def test_collect_note_ids_maps_note_to_slug(tmp_path):
    v = _vault_with_card(tmp_path, 12345)
    k = Knowledge(
        concepts=[
            Concept(
                slug="x",
                title="X",
                unit="phase-0",
                card_refs=[CardRef(path="04-Quiz-Bank/karpathy/x.md")],
            )
        ]
    )
    mapping = collect_note_ids(v, k)
    assert mapping == {12345: "x"}


def test_cross_check_flags_encountered_with_strong_recall():
    k = Knowledge(
        concepts=[
            Concept(
                slug="x",
                title="X",
                unit="phase-0",
                evidence=[
                    Evidence(kind="encountered", at=date(2026, 8, 1), ref="log.md")
                ],
            )
        ]
    )
    note_id_to_slug = {111: "x"}
    notes_info = {111: {"factor": 2600, "interval": 30}}
    result = cross_check(k, note_id_to_slug, notes_info)
    assert len(result) == 1
    assert result[0].concept.slug == "x"
    assert result[0].factor == 2600


def test_cross_check_ignores_applied_concept():
    k = Knowledge(
        concepts=[
            Concept(
                slug="x",
                title="X",
                unit="phase-0",
                evidence=[
                    Evidence(kind="applied", at=date(2026, 8, 1), ref="scripts/x.py")
                ],
            )
        ]
    )
    result = cross_check(k, {111: "x"}, {111: {"factor": 2600, "interval": 30}})
    assert result == []


def test_cross_check_ignores_below_threshold():
    k = Knowledge(
        concepts=[
            Concept(
                slug="x",
                title="X",
                unit="phase-0",
                evidence=[
                    Evidence(kind="encountered", at=date(2026, 8, 1), ref="log.md")
                ],
            )
        ]
    )
    result = cross_check(k, {111: "x"}, {111: {"factor": 2000, "interval": 5}})
    assert result == []


def test_cross_check_empty_notes_info_never_crashes():
    k = Knowledge(concepts=[Concept(slug="x", title="X", unit="phase-0")])
    result = cross_check(k, {111: "x"}, {})
    assert result == []


def test_cross_check_handles_multiple_cards_for_one_note():
    k = Knowledge(
        concepts=[
            Concept(
                slug="x",
                title="X",
                unit="phase-0",
                evidence=[
                    Evidence(kind="encountered", at=date(2026, 8, 1), ref="log.md")
                ],
            )
        ]
    )

    result = cross_check(
        k,
        {111: "x"},
        {111: [{"factor": 1000, "interval": 4}, {"factor": 2600, "interval": 30}]},
    )

    assert len(result) == 1
    assert result[0].factor == 2600
