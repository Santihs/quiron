import json
import time
import urllib.error
import urllib.request
from typing import Any

ANKICONNECT_URL = "http://127.0.0.1:8765"


class AnkiConnectError(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        self.retryable = retryable
        super().__init__(message)


def invoke(
    action: str,
    url: str = ANKICONNECT_URL,
    timeout: int = 10,
    retries: int = 1,
    **params: Any,
) -> Any:
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode(
        "utf-8"
    )
    req = urllib.request.Request(url, data=payload)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read())
            if (
                not isinstance(body, dict)
                or "error" not in body
                or "result" not in body
            ):
                raise AnkiConnectError("AnkiConnect returned a malformed response")
            if body["error"] is not None:
                raise AnkiConnectError(str(body["error"]))
            return body["result"]
        except AnkiConnectError:
            raise
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ) as exc:
            transient = _is_transient(exc)
            if transient and attempt < retries:
                time.sleep(0.05)
                continue
            raise AnkiConnectError(
                f"Could not reach AnkiConnect at {url} — is Anki Desktop running? ({exc})",
                retryable=transient,
            ) from exc
        except (TypeError, ValueError) as exc:
            raise AnkiConnectError("AnkiConnect returned malformed JSON") from exc
    raise AssertionError("unreachable")


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code >= 500
    return isinstance(
        exc, (urllib.error.URLError, TimeoutError, ConnectionError, OSError)
    )


def status(url: str = ANKICONNECT_URL, timeout: int = 2) -> dict[str, Any]:
    try:
        invoke("version", url=url, timeout=timeout)
    except AnkiConnectError as exc:
        return {
            "state": "unavailable",
            "message": str(exc),
            "retryable": exc.retryable,
        }
    return {"state": "connected"}


def cards_by_note_id(
    note_ids: list[int], url: str = ANKICONNECT_URL
) -> dict[int, list[dict]]:
    if not note_ids:
        return {}
    notes = invoke("notesInfo", url=url, notes=note_ids)
    if not isinstance(notes, list):
        raise AnkiConnectError("AnkiConnect returned malformed notesInfo data")
    card_ids: list[int] = []
    for note in notes:
        if not isinstance(note, dict) or not isinstance(note.get("cards"), list):
            raise AnkiConnectError("AnkiConnect returned malformed notesInfo data")
        card_ids.extend(note["cards"])
    if not card_ids:
        return {}
    cards = invoke("cardsInfo", url=url, cards=card_ids)
    if not isinstance(cards, list):
        raise AnkiConnectError("AnkiConnect returned malformed cardsInfo data")
    result: dict[int, list[dict]] = {}
    for card in cards:
        if not isinstance(card, dict) or not isinstance(card.get("note"), int):
            raise AnkiConnectError("AnkiConnect returned malformed card data")
        result.setdefault(card["note"], []).append(card)
    return result


def cards_info_by_note_id(
    note_ids: list[int], url: str = ANKICONNECT_URL
) -> dict[int, dict]:
    """Maps noteId -> raw cardsInfo dict. Assumes 1 card per note (true for
    the 'Yanki - Basic' model used by all cards in this vault)."""
    if not note_ids:
        return {}
    all_cards = cards_by_note_id(note_ids, url=url)
    return {note_id: cards[0] for note_id, cards in all_cards.items() if cards}
