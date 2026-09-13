from datetime import date
from typing import Annotated, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

LADDER = ["unseen", "encountered", "explained", "applied"]
CURRENT_SCHEMA_VERSION = 2
NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _PersistedModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, str_strip_whitespace=True
    )

    @field_validator("*", mode="before")
    @classmethod
    def strip_string_values(cls, value):
        return value.strip() if isinstance(value, str) else value


class Source(_PersistedModel):
    kind: Literal["book", "course", "paper", "video"]
    ref: NonBlank  # "Axler 5.A" / "devtalles leccion 47"


class Evidence(_PersistedModel):
    kind: Literal["encountered", "explained", "applied"]
    at: date
    ref: NonBlank  # obligatorio POR CONSTRUCCION — no Optional
    scope: NonBlank | None = None  # "solo la interpretacion geometrica"
    capture_id: NonBlank | None = None
    operation_id: NonBlank | None = None


class Doubt(_PersistedModel):
    question: NonBlank
    raised_at: date
    status: Literal["open", "resolved"]
    resolved_at: Optional[date] = None
    resolution_ref: NonBlank | None = None  # -> 06-Doubts-Resolved/xxx.md
    resolved_by: NonBlank | None = None  # "segunda fuente" / "peer" / "solo"
    capture_id: NonBlank | None = None
    operation_id: NonBlank | None = None

    @model_validator(mode="after")
    def validate_resolution_state(self):
        resolution_fields = (self.resolved_at, self.resolution_ref, self.resolved_by)
        if self.status == "open" and any(
            value is not None for value in resolution_fields
        ):
            raise ValueError("open doubts cannot contain resolution fields")
        if self.status == "resolved" and self.resolved_at is None:
            raise ValueError("resolved doubts require resolved_at")
        return self


class CardRef(_PersistedModel):
    path: NonBlank  # 04-Quiz-Bank/<deck>/xxx.md
    quality: Literal["unreviewed", "ok", "flagged", "retired"] = "unreviewed"
    flagged_reason: NonBlank | None = None
    reviewed_at: Optional[date] = None
    reviewer_verdict: NonBlank | None = None  # "split into 2" / "fine"
    lapses_at_review: Optional[int] = Field(
        default=None, ge=0
    )  # cierra el loop de auditoria del reviewer


class Concept(_PersistedModel):
    slug: NonBlank
    title: NonBlank
    unit: NonBlank
    sources: list[Source] = Field(default_factory=list)
    prerequisites: list[NonBlank] = []  # slugs de otros conceptos
    evidence: list[Evidence] = Field(default_factory=list)
    doubts: list[Doubt] = Field(default_factory=list)
    card_refs: list[CardRef] = Field(default_factory=list)
    notes_ref: NonBlank | None = None  # -> 02-Topics/xxx.md

    # ¿esto merece memorizarse? — decision explicita, no ausencia
    card_policy: Literal["undecided", "needed", "declined"] = "undecided"
    declined_reason: NonBlank | None = None

    @property
    def understanding(self) -> str:
        """Derivado, nunca guardado."""
        return max((e.kind for e in self.evidence), key=LADDER.index, default="unseen")


class Knowledge(_PersistedModel):
    """Root document persisted at 00-Meta/knowledge.json."""

    schema_version: int = CURRENT_SCHEMA_VERSION
    concepts: list[Concept] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value not in (1, CURRENT_SCHEMA_VERSION):
            raise ValueError(f"unsupported schema version: {value}")
        return value


def load_knowledge_json(raw: str) -> Knowledge:
    """Load persisted knowledge and explicitly upgrade the legacy v1 shape."""
    knowledge = Knowledge.model_validate_json(raw)
    if knowledge.schema_version == 1:
        knowledge.schema_version = CURRENT_SCHEMA_VERSION
    return knowledge
