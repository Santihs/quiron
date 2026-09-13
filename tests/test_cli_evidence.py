from quiron.cli import load_knowledge, main, save_knowledge
from quiron.history import load_history
from quiron.schema import CardRef, Concept, Knowledge
from quiron.vault import Vault


def test_evidence_add_via_cli_persists(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()
    v = Vault(root=tmp_path)
    save_knowledge(
        v,
        Knowledge(
            concepts=[
                Concept(
                    slug="eigenvectores",
                    title="Eigenvectores",
                    unit="phase-0",
                    card_refs=[CardRef(path="04-Quiz-Bank/karpathy/eig.md")],
                )
            ]
        ),
    )

    rc = main(
        [
            "evidence",
            "--vault",
            str(tmp_path),
            "--add",
            "--card",
            "04-Quiz-Bank/karpathy/eig.md",
            "--kind",
            "explained",
            "--ref",
            "05-Explanations/eig.md",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "eigenvectores" in out

    k = load_knowledge(v)
    assert k is not None
    ev = k.concepts[0].evidence[0]
    assert ev.kind == "explained"
    assert ev.ref == "05-Explanations/eig.md"


def test_evidence_add_unmapped_card_does_not_write(tmp_path, capsys):
    (tmp_path / "00-Meta").mkdir()
    v = Vault(root=tmp_path)
    save_knowledge(
        v, Knowledge(concepts=[Concept(slug="x", title="X", unit="phase-0")])
    )

    rc = main(
        [
            "evidence",
            "--vault",
            str(tmp_path),
            "--add",
            "--card",
            "04-Quiz-Bank/karpathy/nope.md",
            "--kind",
            "explained",
            "--ref",
            "x.md",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "not mapped" in out

    k = load_knowledge(v)
    assert k is not None
    assert k.concepts[0].evidence == []


def test_evidence_operation_is_idempotent_and_recorded_once(tmp_path):
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
    argv = [
        "evidence",
        "--vault",
        str(tmp_path),
        "--add",
        "--card",
        "04-Quiz-Bank/karpathy/x.md",
        "--kind",
        "explained",
        "--ref",
        "x.md",
        "--operation-id",
        "op-1",
    ]

    assert main(argv) == 0
    assert main(argv) == 0

    k = load_knowledge(v)
    assert k is not None
    assert len(k.concepts[0].evidence) == 1
    assert len(load_history(v)) == 1
