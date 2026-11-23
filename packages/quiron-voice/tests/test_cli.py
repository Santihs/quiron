from quiron_voice import cli, client


def test_say_sends_cleaned_text(monkeypatch, tmp_path):
    sent: list[tuple[dict, bool]] = []
    monkeypatch.setattr(client, "ensure_server", lambda **_: {})
    monkeypatch.setattr(client, "request", lambda msg, payload=b"", wait=True, port=None: sent.append((msg, wait)) or {"ok": True})
    note = tmp_path / "n.md"
    note.write_text("---\na: 1\n---\n# MSE\n\n**error** medio", encoding="utf-8")

    assert cli.say(["-f", str(note), "--es", "--bg"]) == 0
    msg, wait = sent[-1]
    assert msg["op"] == "say" and msg["lang"] == "es" and wait is False
    assert msg["text"] == "MSE\n\nerror medio"


def test_say_stop_and_empty(monkeypatch):
    sent: list[dict] = []
    monkeypatch.setattr(client, "ensure_server", lambda **_: {})
    monkeypatch.setattr(client, "request", lambda msg, *a, **k: sent.append(msg) or {"ok": True})
    assert cli.say(["--stop"]) == 0 and sent == [{"op": "stop"}]
    assert cli.say(["```x```"]) == 0 and len(sent) == 1


def test_say_reports_server_error(monkeypatch, capsys):
    monkeypatch.setattr(client, "ensure_server", lambda **_: {})
    monkeypatch.setattr(client, "request", lambda *a, **k: {"ok": False, "error": "boom"})
    assert cli.say(["hi"]) == 1
    assert "boom" in capsys.readouterr().err


def test_say_unavailable(monkeypatch, capsys):
    def nope(**_):
        raise client.ServerUnavailable("did not start")

    monkeypatch.setattr(client, "ensure_server", nope)
    assert cli.say(["hi"]) == 1
    assert "did not start" in capsys.readouterr().err


def test_server_status_not_running(monkeypatch, capsys):
    def refused(*a, **k):
        raise ConnectionRefusedError()

    monkeypatch.setattr(client, "request", refused)
    assert cli.server(["status"]) == 1
    assert "not running" in capsys.readouterr().out


def test_main_dispatch(monkeypatch):
    monkeypatch.setattr(cli, "say", lambda rest: 7 if rest == ["x"] else 0)
    assert cli.main(["nope"]) == 2
    assert cli.main(["say", "x"]) == 7
