import pytest
from pydantic import ValidationError

from quiron.schema import Concept, Doubt, Evidence


def test_understanding_derived_default_unseen():
    c = Concept(slug="x", title="X", unit="phase-0")
    assert c.understanding == "unseen"


def test_understanding_derived_from_max_evidence():
    c = Concept(
        slug="x",
        title="X",
        unit="phase-0",
        evidence=[
            Evidence(kind="encountered", at="2026-08-20", ref="a.md"),
            Evidence(kind="applied", at="2026-08-25", ref="scripts/pca.py"),
        ],
    )
    assert c.understanding == "applied"


def test_understanding_flips_without_field_write():
    c = Concept(slug="x", title="X", unit="phase-0")
    assert c.understanding == "unseen"
    c.evidence.append(Evidence(kind="applied", at="2026-08-25", ref="scripts/pca.py"))
    assert c.understanding == "applied"


def test_evidence_requires_ref():
    with pytest.raises(ValidationError):
        Evidence(kind="explained", at="2026-08-22")


def test_doubt_open_has_no_resolution_fields_required():
    d = Doubt(question="por que?", raised_at="2026-08-01", status="open")
    assert d.status == "open"
    assert d.resolved_at is None
