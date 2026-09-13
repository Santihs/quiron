from datetime import date
from unittest.mock import patch

import pytest

from quiron.doctor import run
from quiron.schema import CardRef, Concept, Doubt, Evidence, Knowledge
from quiron.vault import Vault


@pytest.fixture(autouse=True)
def mock_anki_status():
    with patch(
        "quiron.doctor.ankiconnect.status", return_value={"state": "unavailable"}
    ):
        yield


def test_doctor_lists_dangling_ref(vault):
    report = run(vault)
    dangling_cards = {d["card"] for d in report.dangling_refs}
    assert "04-Quiz-Bank/karpathy/unresolvable-ref.md" in dangling_cards


def test_doctor_lists_unlinked_doubt(vault):
    report = run(vault)
    assert "06-Doubts-Resolved/span-de-vectores.md" in report.unlinked_doubts


def test_doctor_reports_headings_skipped(vault):
    report = run(vault)
    assert any("Implementacion propia" in h for h in report.headings_skipped)


def test_doctor_to_dict_is_json_serializable(vault):
    import json

    report = run(vault)
    json.dumps(report.to_dict())


def test_doctor_concept_count_positive(vault):
    report = run(vault)
    assert report.concept_count > 0


def test_doctor_reports_missing_refs_and_unknown_prerequisites(tmp_path):
    vault = Vault(root=tmp_path)
    knowledge = Knowledge(
        concepts=[
            Concept(
                slug="x",
                title="X",
                unit="phase-0",
                prerequisites=["missing"],
                card_refs=[CardRef(path="04-Quiz-Bank/karpathy/missing.md")],
                evidence=[
                    Evidence(
                        kind="applied",
                        at=date(2026, 9, 12),
                        ref="05-Projects/missing.py",
                    )
                ],
                doubts=[
                    Doubt(
                        question="q",
                        raised_at=date(2026, 9, 1),
                        status="resolved",
                        resolved_at=date(2026, 9, 12),
                        resolution_ref="06-Doubts-Resolved/missing.md",
                    )
                ],
            )
        ]
    )

    report = run(vault, existing=knowledge)

    assert report.missing_card_refs == ["04-Quiz-Bank/karpathy/missing.md"]
    assert report.missing_evidence_refs == ["05-Projects/missing.py"]
    assert report.missing_resolution_refs == ["06-Doubts-Resolved/missing.md"]
    assert report.unknown_prerequisites == ["x:missing"]


def test_doctor_reports_anki_status(tmp_path):
    vault = Vault(root=tmp_path)

    with patch("quiron.doctor.ankiconnect.status", return_value={"state": "connected"}):
        report = run(vault)

    assert report.anki_status == {"state": "connected"}
