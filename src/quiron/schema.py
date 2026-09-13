from pydantic import BaseModel
from typing import Literal, Optional
from datetime import date

LADDER = ["unseen", "encountered", "explained", "applied"]


class Source(BaseModel):
    kind: Literal["book", "course", "paper", "video"]
    ref: str  # "Axler 5.A" / "devtalles leccion 47"


class Evidence(BaseModel):
    kind: Literal["encountered", "explained", "applied"]
    at: date
    ref: str  # obligatorio POR CONSTRUCCION — no Optional
    scope: Optional[str] = None  # "solo la interpretacion geometrica"
    capture_id: Optional[str] = None
    operation_id: Optional[str] = None


class Doubt(BaseModel):
    question: str
    raised_at: date
    status: Literal["open", "resolved"]
    resolved_at: Optional[date] = None
    resolution_ref: Optional[str] = None  # -> 06-Doubts-Resolved/xxx.md
    resolved_by: Optional[str] = None  # "segunda fuente" / "peer" / "solo"
    capture_id: Optional[str] = None
    operation_id: Optional[str] = None


class CardRef(BaseModel):
    path: str  # 04-Quiz-Bank/<deck>/xxx.md
    quality: Literal["unreviewed", "ok", "flagged", "retired"] = "unreviewed"
    flagged_reason: Optional[str] = None
    reviewed_at: Optional[date] = None
    reviewer_verdict: Optional[str] = None  # "split into 2" / "fine"
    lapses_at_review: Optional[int] = None  # cierra el loop de auditoria del reviewer


class Concept(BaseModel):
    slug: str
    title: str
    unit: str
    sources: list[Source] = []
    prerequisites: list[str] = []  # slugs de otros conceptos
    evidence: list[Evidence] = []
    doubts: list[Doubt] = []
    card_refs: list[CardRef] = []
    notes_ref: Optional[str] = None  # -> 02-Topics/xxx.md

    # ¿esto merece memorizarse? — decision explicita, no ausencia
    card_policy: Literal["undecided", "needed", "declined"] = "undecided"
    declined_reason: Optional[str] = None

    @property
    def understanding(self) -> str:
        """Derivado, nunca guardado."""
        return max((e.kind for e in self.evidence), key=LADDER.index, default="unseen")


class Knowledge(BaseModel):
    """Root document persisted at 00-Meta/knowledge.json."""

    schema_version: int = 1
    concepts: list[Concept] = []
