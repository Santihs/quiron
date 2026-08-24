import json
import urllib.request
from typing import Any

ANKICONNECT_URL = "http://127.0.0.1:8765"


class AnkiConnectError(Exception):
    pass


def invoke(action: str, url: str = ANKICONNECT_URL, timeout: int = 10, **params: Any) -> Any:
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8")
    req = urllib.request.Request(url, data=payload)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read())
    except OSError as e:
        raise AnkiConnectError(
            f"Could not reach AnkiConnect at {url} — is Anki Desktop running? ({e})"
        ) from e
    if body.get("error") is not None:
        raise AnkiConnectError(body["error"])
    return body["result"]


def cards_info_by_note_id(note_ids: list[int], url: str = ANKICONNECT_URL) -> dict[int, dict]:
    """Maps noteId -> raw cardsInfo dict. Assumes 1 card per note (true for
    the 'Yanki - Basic' model used by all cards in this vault)."""
    if not note_ids:
        return {}
    notes = invoke("notesInfo", url=url, notes=note_ids)
    card_ids = [cid for n in notes for cid in n["cards"]]
    if not card_ids:
        return {}
    cards = invoke("cardsInfo", url=url, cards=card_ids)
    return {c["note"]: c for c in cards}
