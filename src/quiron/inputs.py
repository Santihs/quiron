"""Validated request models for data supplied by agents and skills."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, Self, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

from .errors import QuironError

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
T = TypeVar("T", bound=BaseModel)


class _AgentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def strip_string_values(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProposalInput(_AgentInput):
    capture_id: NonBlank
    kind: Literal["duda", "concepto", "aplicado"]
    target_slug: NonBlank | None = None
    text: NonBlank
    ref: str = ""
    at: date | None = None
    scope: NonBlank | None = None

    @model_validator(mode="after")
    def validate_kind_fields(self) -> Self:
        if self.kind in ("duda", "aplicado") and self.at is None:
            raise ValueError("at is required for duda and aplicado proposals")
        if self.kind == "aplicado":
            if self.target_slug is None:
                raise ValueError("target_slug is required for aplicado proposals")
            if not self.ref.strip():
                raise ValueError("ref is required for aplicado proposals")
        return self


class PolicyDecisionInput(_AgentInput):
    slug: NonBlank
    card_policy: Literal["needed", "declined"]
    declined_reason: NonBlank | None = None

    @model_validator(mode="after")
    def validate_declined_reason(self) -> Self:
        if self.card_policy == "declined" and self.declined_reason is None:
            raise ValueError("declined_reason is required when card_policy is declined")
        if self.card_policy == "needed" and self.declined_reason is not None:
            raise ValueError("declined_reason is only valid for declined policies")
        return self


class ReviewProposalInput(_AgentInput):
    card_path: NonBlank
    quality: Literal["ok", "flagged", "retired"]
    reviewer_verdict: NonBlank
    lapses_at_review: int | None = Field(default=None, ge=0)
    flagged_reason: NonBlank | None = None

    @model_validator(mode="after")
    def validate_flagged_reason(self) -> Self:
        if self.quality == "flagged" and self.flagged_reason is None:
            raise ValueError("flagged_reason is required when quality is flagged")
        return self


class EvidenceInput(_AgentInput):
    card_path: NonBlank
    kind: Literal["encountered", "explained", "applied"]
    ref: NonBlank
    scope: NonBlank | None = None


def validate_record(value: object, model: type[T], label: str) -> T:
    try:
        return model.model_validate(value)
    except (ValidationError, TypeError) as exc:
        raise QuironError(
            "INVALID_INPUT",
            f"{label} has an invalid shape",
            exit_code=3,
        ) from exc


def load_records(path: str, model: type[T], label: str) -> list[T]:
    """Load and validate a complete JSON array before any state is changed."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QuironError(
            "INVALID_INPUT",
            f"{label} must be a readable JSON array: {path}",
            exit_code=3,
            details={"path": path},
        ) from exc

    if not isinstance(value, list):
        raise QuironError(
            "INVALID_INPUT",
            f"{label} must be a JSON array of objects: {path}",
            exit_code=3,
            details={"path": path},
        )

    return [
        validate_record(item, model, f"{label} record {index}")
        for index, item in enumerate(value)
    ]
