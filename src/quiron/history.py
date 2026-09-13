"""Append-only operation history for user-visible knowledge changes."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .errors import QuironError
from .store import vault_lock
from .vault import Vault

HISTORY_PATH = ("00-Meta", "history.jsonl")
HISTORY_VERSION = 1


def operation_id(namespace: str, payload: Any) -> str:
    """Return a stable key for a retryable operation when none was supplied."""
    encoded = json.dumps(
        {"namespace": namespace, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:24]


def make_event(event_type: str, operation_id: str, subject: str, **data: Any) -> dict:
    identity = json.dumps(
        {
            "version": HISTORY_VERSION,
            "type": event_type,
            "operation_id": operation_id,
            "subject": subject,
            "data": data,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    event_id = hashlib.sha256(identity).hexdigest()[:24]
    return {
        "version": HISTORY_VERSION,
        "event_id": event_id,
        "operation_id": operation_id,
        "type": event_type,
        "subject": subject,
        "at": datetime.now(timezone.utc).isoformat(),
        **data,
    }


def load_history(vault: Vault) -> list[dict]:
    path = vault.path(*HISTORY_PATH)
    if not path.exists():
        return []

    events: list[dict] = []
    for line_number, line in enumerate(vault.read_text(path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise QuironError(
                "INVALID_HISTORY",
                f"history.jsonl contains invalid JSON at line {line_number}",
                exit_code=4,
                details={"path": str(path), "line": line_number},
            ) from exc
        if not isinstance(event, dict) or not event.get("event_id"):
            raise QuironError(
                "INVALID_HISTORY",
                f"history.jsonl contains an invalid event at line {line_number}",
                exit_code=4,
                details={"path": str(path), "line": line_number},
            )
        events.append(event)
    return events


def append_events(vault: Vault, events: list[dict]) -> int:
    """Append unseen events and return the number written."""
    with vault_lock(vault):
        return _append_events(vault, events)


def _append_events(vault: Vault, events: list[dict]) -> int:
    if not events:
        return 0
    existing = load_history(vault)
    existing_ids = {event["event_id"] for event in existing}
    new_events: list[dict] = []
    for event in events:
        if event["event_id"] in existing_ids:
            continue
        existing_ids.add(event["event_id"])
        new_events.append(event)
    if not new_events:
        return 0

    path = vault.path(*HISTORY_PATH)
    content = "\n".join(
        json.dumps(event, ensure_ascii=False, sort_keys=True) for event in new_events
    )
    if path.exists() and path.stat().st_size:
        content = "\n" + content
    vault.write_text(path, content + "\n")
    return len(new_events)
