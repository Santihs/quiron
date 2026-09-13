from datetime import date

from quiron.audit import AuditReport, Candidate
from quiron.capture import write_inbox
from quiron.schema import Concept, Doubt, Knowledge
from quiron.today import build_report, doubt_age_state, render


def test_doubt_age_states():
    today = date(2026, 8, 23)
    assert doubt_age_state("2026-08-20", today) == "fresh"  # 3d
    assert doubt_age_state("2026-08-05", today) == "stale"  # 18d
    assert doubt_age_state("2026-07-01", today) == "neglected"  # 53d


def test_no_cards_is_never_red(tmp_path):
    from quiron.vault import Vault

    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    k = Knowledge(concepts=[Concept(slug="x", title="X", unit="phase-0")])
    lines = build_report(v, k)
    assert all(l.tier != "red" for l in lines)


def test_unprocessed_inbox_is_yellow_never_red(tmp_path):
    from quiron.vault import Vault

    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    write_inbox(
        v,
        [
            {
                "id": "a",
                "kind": "duda",
                "text": "x",
                "source_log": "l.md",
                "processed": False,
            }
        ],
    )
    k = Knowledge()
    lines = build_report(v, k)
    inbox_lines = [l for l in lines if "capturas sin procesar" in l.text]
    assert len(inbox_lines) == 1
    assert inbox_lines[0].tier == "yellow"


def test_neglected_doubt_is_red(tmp_path):
    from quiron.vault import Vault

    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    k = Knowledge(
        concepts=[
            Concept(
                slug="x",
                title="X",
                unit="phase-0",
                doubts=[
                    Doubt(
                        question="por que?", raised_at=date(2026, 7, 1), status="open"
                    )
                ],
            )
        ]
    )
    lines = build_report(v, k, today=date(2026, 8, 23))
    red = [l for l in lines if l.tier == "red" and "duda" in l.text]
    assert len(red) == 1


def test_stale_doubt_is_yellow(tmp_path):
    from quiron.vault import Vault

    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    k = Knowledge(
        concepts=[
            Concept(
                slug="x",
                title="X",
                unit="phase-0",
                doubts=[
                    Doubt(
                        question="por que?", raised_at=date(2026, 8, 5), status="open"
                    )
                ],
            )
        ]
    )
    lines = build_report(v, k, today=date(2026, 8, 23))
    yellow = [l for l in lines if l.tier == "yellow" and "duda" in l.text]
    red = [l for l in lines if l.tier == "red" and "duda" in l.text]
    assert len(yellow) == 1
    assert len(red) == 0


def test_dangling_refs_render_red(tmp_path):
    from quiron.vault import Vault

    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    k = Knowledge()
    lines = build_report(v, k, unresolved_refs=[("a.md", "ref")])
    assert lines[0].tier == "red"
    assert "1 tarjetas" in lines[0].text


def test_audit_candidate_renders_red_with_reviewer_action(tmp_path):
    from quiron.vault import Vault

    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    report = AuditReport(
        candidates=[
            Candidate(
                card_path="04-Quiz-Bank/karpathy/x.md",
                concept_slug="x",
                reasons=["suspect_card"],
                lapses=7,
            )
        ]
    )

    lines = build_report(v, Knowledge(), audit_report=report)

    audit_lines = [l for l in lines if "suspect_card" in l.text]
    assert len(audit_lines) == 1
    assert audit_lines[0].tier == "red"
    assert audit_lines[0].action == "/quiron-cards-audit"


def test_render_includes_symbol_and_action():
    from quiron.today import Line

    out = render(
        [Line(tier="yellow", text="4 capturas sin procesar", action="/quiron-inbox")]
    )
    assert "4 capturas sin procesar" in out
    assert "/quiron-inbox" in out
