import builtins
import sys
import types

from quiron import cli


def test_voice_commands_delegate(monkeypatch):
    calls: list[list[str]] = []
    fake = types.ModuleType("quiron_voice.cli")
    fake.main = lambda argv: calls.append(argv) or 0  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "quiron_voice.cli", fake)

    assert cli.main(["say", "--es", "hola"]) == 0
    assert cli.main(["voice-server", "status"]) == 0
    assert calls == [["say", "--es", "hola"], ["server", "status"]]


def test_voice_missing_package_explains_install(monkeypatch, capsys):
    real_import = builtins.__import__

    def no_voice(name, *args, **kwargs):
        if name.startswith("quiron_voice"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "quiron_voice.cli", raising=False)
    monkeypatch.setattr(builtins, "__import__", no_voice)
    assert cli.main(["answer"]) == 2
    assert "uv tool install" in capsys.readouterr().err
