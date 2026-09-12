import json
import shlex

import pytest

from quiron.cli import main
from quiron.schema import Concept, Knowledge
from quiron.today import build_report
from quiron.vault import Vault


def test_cards_rejects_conflicting_actions(tmp_path):
    (tmp_path / "00-Meta").mkdir()

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "cards",
                "--vault",
                str(tmp_path),
                "--list-gaps",
                "--audit",
            ]
        )

    assert exc_info.value.code == 2


def test_cards_list_gaps_has_machine_readable_output(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()
    vault = Vault(root=tmp_path)
    from quiron.cli import save_knowledge

    save_knowledge(
        vault,
        Knowledge(
            concepts=[
                Concept(
                    slug="x",
                    title="X",
                    unit="phase-0",
                    notes_ref="02-Topics/x.md",
                    card_policy="needed",
                )
            ]
        ),
    )

    assert main(["cards", "--vault", str(tmp_path), "--list-gaps", "--json"]) == 0

    assert json.loads(capsys.readouterr().out) == [
        {"slug": "x", "title": "X", "notes_ref": "02-Topics/x.md"}
    ]


def test_cards_without_action_returns_structured_json_error(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()

    rc = main(["cards", "--vault", str(tmp_path), "--json"])

    assert rc == 2
    error = json.loads(capsys.readouterr().out)
    assert error["status"] == "error"
    assert error["code"] == "NO_ACTION"


def test_cards_decide_json_is_rejected_before_prompting(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()

    rc = main(["cards", "--vault", str(tmp_path), "--decide", "--json"])

    assert rc == 2
    error = json.loads(capsys.readouterr().out)
    assert error["code"] == "INTERACTIVE_JSON_UNSUPPORTED"


def test_cards_rejects_malformed_agent_input_as_json_error(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()
    input_path = tmp_path / "policy.json"
    input_path.write_text("{not json", encoding="utf-8")

    rc = main(
        [
            "cards",
            "--vault",
            str(tmp_path),
            "--set-policy",
            str(input_path),
            "--json",
        ]
    )

    assert rc == 3
    error = json.loads(capsys.readouterr().out)
    assert error["code"] == "INVALID_INPUT"
    assert not (tmp_path / "00-Meta" / "knowledge.json").exists()


def test_today_actions_include_runtime_vault_and_deck(tmp_path):
    (tmp_path / "00-Meta").mkdir()
    vault = Vault(root=tmp_path)
    knowledge = Knowledge(
        concepts=[
            Concept(slug="x", title="X", unit="phase-0", card_policy="needed"),
            Concept(slug="y", title="Y", unit="phase-0"),
        ]
    )

    vault_path = tmp_path / "vault with spaces"
    lines = build_report(vault, knowledge, vault_path=vault_path, deck="deck name")
    actions = {line.action for line in lines if line.action}

    quoted_vault = shlex.quote(str(vault_path))
    quoted_deck = shlex.quote("deck name")
    assert (
        f"quiron cards --vault {quoted_vault} --deck {quoted_deck} --list-gaps"
        in actions
    )
    assert (
        f"quiron cards --vault {quoted_vault} --deck {quoted_deck} --decide" in actions
    )
