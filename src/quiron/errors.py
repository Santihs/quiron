"""Structured errors shared by the CLI and deterministic workflows."""

from __future__ import annotations


class QuironError(Exception):
    """An expected failure with a stable code for humans and agents."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        exit_code: int = 4,
        details: dict | None = None,
        retryable: bool = False,
    ) -> None:
        self.code = code
        self.message = message
        self.exit_code = exit_code
        self.details = details or {}
        self.retryable = retryable
        super().__init__(message)

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
        }
