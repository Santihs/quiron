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
