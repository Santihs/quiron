import json

from quiron.capture import write_inbox
from quiron.cli import load_knowledge, main, save_knowledge
from quiron.schema import Concept, Knowledge
from quiron.vault import Vault


def _setup(tmp_path):
    (tmp_path / "00-Meta").mkdir()
    v = Vault(root=tmp_path)
    k = Knowledge(concepts=[Concept(slug="x--y", title="Y", unit="phase-0")])
    save_knowledge(v, k)
    write_inbox(
        v,
        [
            {
                "id": "abc123",
                "kind": "duda",
                "text": "por que Av=lambda*v conserva la direccion",
                "source_log": "03-Daily-Logs/2026-08-23.md",
                "processed": False,
            }
        ],
    )
    return v


def test_inbox_apply_opens_doubt_and_marks_processed(tmp_path):
    v = _setup(tmp_path)
    proposals_path = tmp_path / "proposals.json"
    proposals_path.write_text(
        json.dumps(
            [
                {
                    "capture_id": "abc123",
                    "kind": "duda",
                    "target_slug": "x--y",
                    "text": "por que Av=lambda*v conserva la direccion",
                    "at": "2026-08-23",
                }
            ]
        ),
        encoding="utf-8",
    )

    rc = main(["inbox", "--vault", str(tmp_path), "--apply", str(proposals_path)])
    assert rc == 0

    k = load_knowledge(v)
    assert k is not None
    c = next(c for c in k.concepts if c.slug == "x--y")
    assert len(c.doubts) == 1
    assert c.doubts[0].status == "open"

    from quiron.capture import load_inbox

    inbox = load_inbox(v)
    assert inbox[0]["processed"] is True


def test_inbox_apply_skip_leaves_unprocessed(tmp_path):
    v = _setup(tmp_path)
    proposals_path = tmp_path / "proposals.json"
    proposals_path.write_text(json.dumps([]), encoding="utf-8")

    main(["inbox", "--vault", str(tmp_path), "--apply", str(proposals_path)])

    from quiron.capture import load_inbox

    inbox = load_inbox(v)
    assert inbox[0]["processed"] is False


def test_inbox_rejects_invalid_batch_without_writing(tmp_path, capsys):
    v = _setup(tmp_path)
    knowledge = load_knowledge(v)
    assert knowledge is not None
    before_knowledge = knowledge.model_dump()
    before_inbox = v.read_text(v.path("00-Meta", "inbox.jsonl"))
    proposals_path = tmp_path / "proposals.json"
    proposals_path.write_text(
        json.dumps(
            [
                {
                    "capture_id": "abc123",
                    "kind": "duda",
                    "target_slug": "x--y",
                    "text": "q",
                    "at": "2026-08-23",
                },
                {
                    "capture_id": "bad",
                    "kind": "unknown",
                    "target_slug": "x--y",
                    "text": "q",
                    "at": "2026-08-23",
                },
            ]
        ),
        encoding="utf-8",
    )

    rc = main(
        ["inbox", "--vault", str(tmp_path), "--apply", str(proposals_path), "--json"]
    )

    assert rc == 3
    assert json.loads(capsys.readouterr().out)["code"] == "INVALID_INPUT"
    knowledge = load_knowledge(v)
    assert knowledge is not None
    assert knowledge.model_dump() == before_knowledge
    assert v.read_text(v.path("00-Meta", "inbox.jsonl")) == before_inbox


def test_inbox_json_reports_apply_result(tmp_path, capsys):
    v = _setup(tmp_path)
    proposals_path = tmp_path / "proposals.json"
    proposals_path.write_text(
        json.dumps(
            [
                {
                    "capture_id": "abc123",
                    "kind": "duda",
                    "target_slug": "x--y",
                    "text": "por que Av=lambda*v conserva la direccion",
                    "at": "2026-08-23",
                }
            ]
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "inbox",
                "--vault",
                str(tmp_path),
                "--apply",
                str(proposals_path),
                "--json",
            ]
        )
        == 0
    )

    assert json.loads(capsys.readouterr().out)["applied"] == ["abc123"]


def test_inbox_reapplying_capture_is_idempotent(tmp_path):
    v = _setup(tmp_path)
    proposal = tmp_path / "proposals.json"
    proposal.write_text(
        json.dumps(
            [
                {
                    "capture_id": "abc123",
                    "kind": "duda",
                    "target_slug": "x--y",
                    "text": "por que Av=lambda*v conserva la direccion",
                    "at": "2026-08-23",
                }
            ]
        ),
        encoding="utf-8",
    )

    assert main(["inbox", "--vault", str(tmp_path), "--apply", str(proposal)]) == 0
    assert main(["inbox", "--vault", str(tmp_path), "--apply", str(proposal)]) == 0

    k = load_knowledge(v)
    assert k is not None
    assert len(k.concepts[0].doubts) == 1


def test_inbox_rejects_proposal_that_does_not_match_capture(tmp_path):
    v = _setup(tmp_path)
    proposal = tmp_path / "proposals.json"
    proposal.write_text(
        json.dumps(
            [
                {
                    "capture_id": "abc123",
                    "kind": "duda",
                    "target_slug": "x--y",
                    "text": "different text",
                    "at": "2026-08-23",
                }
            ]
        ),
        encoding="utf-8",
    )

    assert main(["inbox", "--vault", str(tmp_path), "--apply", str(proposal)]) == 0

    k = load_knowledge(v)
    assert k is not None
    assert k.concepts[0].doubts == []
