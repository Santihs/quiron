from datetime import date

from quiron.recall import Contradiction
from quiron.schema import CardRef, Concept, Evidence, Knowledge
from quiron.today import build_report
from quiron.vault import Vault


def test_gap_is_yellow_never_red(tmp_path):
    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    k = Knowledge(concepts=[Concept(slug="a", title="A", unit="phase-0", card_policy="needed")])
    lines = build_report(v, k)
    gap_lines = [l for l in lines if "needed" in l.text]
    assert len(gap_lines) == 1
    assert gap_lines[0].tier == "yellow"
    assert all(l.tier != "red" for l in lines)


def test_declined_produces_no_line_at_all(tmp_path):
    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    k = Knowledge(
        concepts=[
            Concept(
                slug="a",
                title="A",
                unit="phase-0",
                card_policy="declined",
                declined_reason="es referencia",
            )
        ]
    )
    lines = build_report(v, k)
    assert all("A" not in l.text for l in lines)


def test_undecided_still_yellow_and_separate_from_gap(tmp_path):
    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    k = Knowledge(
        concepts=[
            Concept(slug="a", title="A", unit="phase-0", card_policy="needed"),
            Concept(slug="b", title="B", unit="phase-0"),  # undecided
        ]
    )
    lines = build_report(v, k)
    texts = [l.text for l in lines]
    assert any("needed" in t for t in texts)
    assert any("decision de retencion" in t for t in texts)


def test_contradiction_line_is_yellow(tmp_path):
    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    k = Knowledge()
    c = Concept(
        slug="x",
        title="Eigenvectores",
        unit="phase-0",
        evidence=[Evidence(kind="encountered", at="2026-08-01", ref="log.md")],
    )
    contradiction = Contradiction(concept=c, note_id=1, factor=2600, interval=30)
    lines = build_report(v, k, contradictions=[contradiction])
    matches = [l for l in lines if "Eigenvectores" in l.text]
    assert len(matches) == 1
    assert matches[0].tier == "yellow"
    assert "factor 2600" in matches[0].text


def test_no_contradictions_no_extra_lines(tmp_path):
    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    k = Knowledge()
    lines_without = build_report(v, k)
    lines_with_empty = build_report(v, k, contradictions=[])
    assert len(lines_without) == len(lines_with_empty)
