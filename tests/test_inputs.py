from datetime import date

import pytest
from pydantic import ValidationError

from quiron.inputs import (
    EvidenceInput,
    PolicyDecisionInput,
    ProposalInput,
    ReviewProposalInput,
)


def test_proposal_input_parses_dates_and_strips_strings():
    proposal = ProposalInput(
        capture_id=" capture-1 ",
        kind=" aplicado ",
        target_slug=" concept ",
        text=" ejercicio ",
        ref=" scripts/example.py ",
        at="2026-09-12",
    )

    assert proposal.capture_id == "capture-1"
    assert proposal.kind == "aplicado"
    assert proposal.target_slug == "concept"
    assert proposal.at == date(2026, 9, 12)


@pytest.mark.parametrize(
    "payload",
    [
        {"capture_id": "x", "kind": "duda", "text": "q"},
        {
            "capture_id": "x",
            "kind": "aplicado",
            "target_slug": "concept",
            "text": "run",
            "at": "2026-09-12",
        },
        {
            "capture_id": "x",
            "kind": "aplicado",
            "target_slug": "concept",
            "text": "run",
            "ref": "x.py",
            "at": "2026-09-12",
            "unexpected": True,
        },
    ],
)
def test_proposal_input_rejects_invalid_or_incomplete_payloads(payload):
    with pytest.raises(ValidationError):
        ProposalInput.model_validate(payload)


def test_policy_decision_requires_reason_only_for_declined():
    assert PolicyDecisionInput(slug="x", card_policy="needed").declined_reason is None

    with pytest.raises(ValidationError):
        PolicyDecisionInput(slug="x", card_policy="declined")


def test_review_proposal_rejects_negative_lapses_and_requires_flag_reason():
    with pytest.raises(ValidationError):
        ReviewProposalInput(
            card_path="04-Quiz-Bank/karpathy/x.md",
            quality="ok",
            reviewer_verdict="fine",
            lapses_at_review=-1,
        )

    with pytest.raises(ValidationError):
        ReviewProposalInput(
            card_path="04-Quiz-Bank/karpathy/x.md",
            quality="flagged",
            reviewer_verdict="needs work",
        )


def test_evidence_input_rejects_blank_refs():
    with pytest.raises(ValidationError):
        EvidenceInput(
            card_path="04-Quiz-Bank/karpathy/x.md",
            kind="explained",
            ref="   ",
        )
