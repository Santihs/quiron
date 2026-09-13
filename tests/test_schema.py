from datetime import date

import pytest
from pydantic import ValidationError

from quiron.schema import (
    CardRef,
    Concept,
    Doubt,
    Evidence,
    Knowledge,
    load_knowledge_json,
)


def test_understanding_derived_default_unseen():
    c = Concept(slug="x", title="X", unit="phase-0")
    assert c.understanding == "unseen"


def test_understanding_derived_from_max_evidence():
    c = Concept(
        slug="x",
        title="X",
        unit="phase-0",
        evidence=[
            Evidence(kind="encountered", at=date(2026, 8, 20), ref="a.md"),
            Evidence(kind="applied", at=date(2026, 8, 25), ref="scripts/pca.py"),
        ],
    )
    assert c.understanding == "applied"


def test_understanding_flips_without_field_write():
    c = Concept(slug="x", title="X", unit="phase-0")
    assert c.understanding == "unseen"
    c.evidence.append(
        Evidence(kind="applied", at=date(2026, 8, 25), ref="scripts/pca.py")
    )
    assert c.understanding == "applied"


def test_evidence_requires_ref():
    with pytest.raises(ValidationError):
        Evidence(kind="explained", at=date(2026, 8, 22))  # pyright: ignore[reportCallIssue]


def test_doubt_open_has_no_resolution_fields_required():
    d = Doubt(question="por que?", raised_at=date(2026, 8, 1), status="open")
    assert d.status == "open"
    assert d.resolved_at is None


def test_evidence_ref_must_not_be_blank():
    with pytest.raises(ValidationError):
        Evidence(kind="explained", at=date(2026, 8, 22), ref="   ")


def test_persisted_models_reject_unknown_fields_and_bad_assignments():
    with pytest.raises(ValidationError):
        Concept.model_validate(
            {"slug": "x", "title": "X", "unit": "phase-0", "unexpected": True}
        )

    concept = Concept(slug="x", title="X", unit="phase-0")
    with pytest.raises(ValidationError):
        concept.card_policy = "invalid"  # pyright: ignore[reportAttributeAccessIssue]


def test_cardref_rejects_negative_lapse_snapshot():
    with pytest.raises(ValidationError):
        CardRef(path="x.md", lapses_at_review=-1)


def test_knowledge_rejects_unsupported_schema_version():
    with pytest.raises(ValidationError):
        Knowledge(schema_version=99)


def test_legacy_knowledge_is_explicitly_upgraded():
    knowledge = load_knowledge_json('{"schema_version": 1, "concepts": []}')

    assert knowledge.schema_version == 2
