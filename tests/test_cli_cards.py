import json
from unittest.mock import patch

from quiron.cli import load_knowledge, main, save_knowledge
from quiron.history import load_history
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
    save_knowledge(
        v, Knowledge(concepts=[Concept(slug="a", title="A", unit="phase-0")])
    )

    inputs = iter(["n"])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))

    rc = main(["cards", "--vault", str(tmp_path), "--decide"])
    assert rc == 0

    k = load_knowledge(v)
    assert k is not None
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


def test_today_scans_new_daily_log_callouts(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()
    (tmp_path / "03-Daily-Logs").mkdir()
    v = Vault(root=tmp_path)
    v.write_text(
        tmp_path / "03-Daily-Logs" / "2026-09-12.md",
        "> [!duda] por que funciona esto?\n",
    )
    save_knowledge(v, Knowledge())

    with patch("quiron.doctor.ankiconnect.status", return_value={"state": "connected"}):
        assert main(["today", "--vault", str(tmp_path)]) == 0

    assert "1 capturas sin procesar" in capsys.readouterr().out
    from quiron.capture import load_inbox

    inbox = load_inbox(v)
    assert len(inbox) == 1
    assert inbox[0]["text"] == "por que funciona esto?"


def test_today_includes_card_audit_candidates(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()
    card_dir = tmp_path / "04-Quiz-Bank" / "karpathy"
    card_dir.mkdir(parents=True)
    v = Vault(root=tmp_path)
    v.write_text(
        card_dir / "too-long.md",
        "Pregunta\n\n---\n\n" + " ".join(["palabra"] * 60) + "\n",
    )

    with patch("quiron.doctor.ankiconnect.status", return_value={"state": "connected"}):
        assert main(["today", "--vault", str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert "too-long.md · too_long, unmapped_concept" in out
    assert "/quiron-cards-audit" in out


def test_audit_via_cli_json(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()
    (tmp_path / "04-Quiz-Bank" / "karpathy").mkdir(parents=True)
    v = Vault(root=tmp_path)
    long_answer = " ".join(["palabra"] * 60)
    v.write_text(
        tmp_path / "04-Quiz-Bank" / "karpathy" / "x.md",
        f"---\ntags:\n  - repo-karpathy\nnoteId: 111\n---\nPregunta\n\n---\n\n{long_answer}\n\nRef: `05-Projects/x.py`\n",
    )
    save_knowledge(v, Knowledge())

    from quiron import ankiconnect

    with patch(
        "quiron.ankiconnect.invoke",
        side_effect=ankiconnect.AnkiConnectError("no Anki"),
    ):
        rc = main(["cards", "--vault", str(tmp_path), "--audit", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["checked"] == 1
    assert any("too_long" in c["reasons"] for c in data["candidates"])


def test_record_review_via_cli_persists(tmp_path):
    (tmp_path / "00-Meta").mkdir()
    v = Vault(root=tmp_path)
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
    proposals_path = tmp_path / "proposals.json"
    proposals_path.write_text(
        json.dumps(
            [
                {
                    "card_path": "04-Quiz-Bank/karpathy/x.md",
                    "quality": "ok",
                    "reviewer_verdict": "fine",
                    "lapses_at_review": 7,
                }
            ]
        ),
        encoding="utf-8",
    )

    rc = main(
        ["cards", "--vault", str(tmp_path), "--record-review", str(proposals_path)]
    )
    assert rc == 0

    k = load_knowledge(v)
    assert k is not None
    cr = k.concepts[0].card_refs[0]
    assert cr.quality == "ok"
    assert cr.reviewer_verdict == "fine"
    assert cr.lapses_at_review == 7
    assert cr.reviewed_at is not None


def test_list_undecided_json(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()
    v = Vault(root=tmp_path)
    save_knowledge(
        v,
        Knowledge(
            concepts=[
                Concept(
                    slug="a", title="A", unit="phase-0", notes_ref="02-Topics/a.md"
                ),
                Concept(slug="b", title="B", unit="phase-0", card_policy="needed"),
            ]
        ),
    )
    rc = main(["cards", "--vault", str(tmp_path), "--list-undecided", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data == [{"slug": "a", "title": "A", "notes_ref": "02-Topics/a.md"}]


def test_set_policy_via_cli_persists(tmp_path):
    (tmp_path / "00-Meta").mkdir()
    v = Vault(root=tmp_path)
    save_knowledge(
        v,
        Knowledge(
            concepts=[
                Concept(slug="a", title="A", unit="phase-0"),
                Concept(slug="b", title="B", unit="phase-0"),
            ]
        ),
    )
    proposals_path = tmp_path / "policy.json"
    proposals_path.write_text(
        json.dumps(
            [
                {"slug": "a", "card_policy": "needed"},
                {
                    "slug": "b",
                    "card_policy": "declined",
                    "declined_reason": "no aplica",
                },
                {"slug": "ghost", "card_policy": "needed"},
            ]
        ),
        encoding="utf-8",
    )

    rc = main(["cards", "--vault", str(tmp_path), "--set-policy", str(proposals_path)])
    assert rc == 0

    k = load_knowledge(v)
    assert k is not None
    by_slug = {c.slug: c for c in k.concepts}
    assert by_slug["a"].card_policy == "needed"
    assert by_slug["b"].card_policy == "declined"
    assert by_slug["b"].declined_reason == "no aplica"


def test_set_policy_retry_writes_one_history_event(tmp_path):
    (tmp_path / "00-Meta").mkdir()
    v = Vault(root=tmp_path)
    save_knowledge(
        v, Knowledge(concepts=[Concept(slug="a", title="A", unit="phase-0")])
    )
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps([{"slug": "a", "card_policy": "needed"}]), encoding="utf-8"
    )
    argv = [
        "cards",
        "--vault",
        str(tmp_path),
        "--set-policy",
        str(policy_path),
        "--operation-id",
        "op-1",
    ]

    assert main(argv) == 0
    assert main(argv) == 0

    assert [event["type"] for event in load_history(v)] == ["policy_decided"]
