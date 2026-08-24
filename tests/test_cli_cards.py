from unittest.mock import patch

from quiron.cli import load_knowledge, main, save_knowledge
from quiron.schema import CardRef, Concept, Knowledge
from quiron.vault import Vault


def test_list_gaps(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()
    v = Vault(root=tmp_path)
    save_knowledge(
        v,
        Knowledge(
            concepts=[
                Concept(slug="a--b", title="B", unit="phase-0", card_policy="needed"),
                Concept(slug="c--d", title="D", unit="phase-0", card_policy="declined"),
            ]
        ),
    )
    rc = main(["cards", "--vault", str(tmp_path), "--list-gaps"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "a--b" in out
    assert "c--d" not in out


def test_decide_via_cli_persists(tmp_path, monkeypatch):
    (tmp_path / "00-Meta").mkdir()
    v = Vault(root=tmp_path)
    save_knowledge(v, Knowledge(concepts=[Concept(slug="a", title="A", unit="phase-0")]))

    inputs = iter(["n"])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))

    rc = main(["cards", "--vault", str(tmp_path), "--decide"])
    assert rc == 0

    k = load_knowledge(v)
    assert k.concepts[0].card_policy == "needed"


def test_today_survives_ankiconnect_unreachable(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()
    (tmp_path / "04-Quiz-Bank" / "karpathy").mkdir(parents=True)
    v = Vault(root=tmp_path)
    v.write_text(
        tmp_path / "04-Quiz-Bank" / "karpathy" / "x.md",
        "---\ntags:\n  - repo-karpathy\nnoteId: 111\n---\nQ\n\n---\n\nA\n",
    )
    save_knowledge(
        v,
        Knowledge(
            concepts=[
                Concept(
                    slug="x",
                    title="X",
                    unit="phase-0",
                    card_refs=[CardRef(path="04-Quiz-Bank/karpathy/x.md")],
                )
            ]
        ),
    )

    from quiron import ankiconnect

    with patch(
        "quiron.ankiconnect.invoke",
        side_effect=ankiconnect.AnkiConnectError("no Anki"),
    ):
        rc = main(["today", "--vault", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "factor" not in out
