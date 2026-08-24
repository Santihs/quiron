import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from quiron import ankiconnect


def _mock_response(body: dict):
    ctx = MagicMock()
    ctx.__enter__.return_value.read.return_value = json.dumps(body).encode("utf-8")
    return ctx


def test_invoke_sends_correct_payload():
    with patch(
        "urllib.request.urlopen", return_value=_mock_response({"result": 42, "error": None})
    ) as mock_urlopen:
        result = ankiconnect.invoke("findCards", query="deck:karpathy")

    assert result == 42
    sent_req = mock_urlopen.call_args[0][0]
    sent_payload = json.loads(sent_req.data)
    assert sent_payload == {
        "action": "findCards",
        "version": 6,
        "params": {"query": "deck:karpathy"},
    }


def test_invoke_raises_on_anki_error():
    with patch(
        "urllib.request.urlopen",
        return_value=_mock_response({"result": None, "error": "deck not found"}),
    ):
        with pytest.raises(ankiconnect.AnkiConnectError, match="deck not found"):
            ankiconnect.invoke("findCards", query="deck:missing")


def test_invoke_raises_when_anki_not_running():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(ankiconnect.AnkiConnectError, match="is Anki Desktop running"):
            ankiconnect.invoke("findCards")


def test_cards_info_by_note_id_maps_correctly():
    notes_info = [{"noteId": 111, "cards": [1001]}, {"noteId": 222, "cards": [1002]}]
    cards_info = [{"note": 111, "cardId": 1001, "interval": 21}, {"note": 222, "cardId": 1002, "interval": 5}]

    with patch("quiron.ankiconnect.invoke", side_effect=[notes_info, cards_info]) as mock_invoke:
        result = ankiconnect.cards_info_by_note_id([111, 222])

    assert result == {111: cards_info[0], 222: cards_info[1]}
    assert mock_invoke.call_args_list[0].args[0] == "notesInfo"
    assert mock_invoke.call_args_list[1].args[0] == "cardsInfo"


def test_cards_info_by_note_id_empty_list_short_circuits():
    with patch("quiron.ankiconnect.invoke") as mock_invoke:
        result = ankiconnect.cards_info_by_note_id([])

    assert result == {}
    mock_invoke.assert_not_called()
