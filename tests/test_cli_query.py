import json
from datetime import date

from quiron.cli import main, save_knowledge
from quiron.schema import Concept, Doubt, Evidence, Knowledge, Source
from quiron.vault import Vault


def test_next_via_cli_json(tmp_path, capsys):
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
                    doubts=[
                        Doubt(question="q", raised_at=date(2026, 7, 1), status="open")
                    ],
                )
            ]
        ),
    )
    rc = main(["next", "--vault", str(tmp_path), "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["slug"] == "x"
    assert data[0]["reason"] == "open_doubt"


def test_next_via_cli_text_empty(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()
    v = Vault(root=tmp_path)
    save_knowledge(v, Knowledge())
    rc = main(["next", "--vault", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "no candidates" in out


def test_sources_via_cli_json(tmp_path, capsys):
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
                    sources=[Source(kind="book", ref="Axler cap.5")],
                    evidence=[
                        Evidence(kind="applied", at=date(2026, 8, 1), ref="x.py")
                    ],
                )
            ]
        ),
    )
    rc = main(["sources", "--vault", str(tmp_path), "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["ref"] == "Axler cap.5"
    assert data[0]["concept_count"] == 1
    assert data[0]["applied_count"] == 1


def test_sources_via_cli_text_empty(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()
    v = Vault(root=tmp_path)
    save_knowledge(v, Knowledge())
    rc = main(["sources", "--vault", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "no sources recorded yet" in out
