from quiron.audit import lapses_signal, layer1_flags, run
from quiron.schema import CardRef, Concept, Evidence, Knowledge
from quiron.vault import Vault, read_frontmatter


def _write_card(vault, name, question, answer, ref="05-Projects/x.py", note_id=1):
    d = vault.path("04-Quiz-Bank", "karpathy")
    d.mkdir(parents=True, exist_ok=True)
    body = f"---\ntags:\n  - repo-karpathy\nnoteId: {note_id}\n---\n{question}\n\n---\n\n{answer}\n\nRef: `{ref}`\n"
    vault.write_text(d / name, body)


def test_layer1_giveaway_overlap(tmp_path):
    v = Vault(root=tmp_path)
    _write_card(
        v,
        "a.md",
        "Que es un vector unitario?",
        "Un vector unitario es un vector unitario de norma uno.",
    )
    _, body = read_frontmatter(v, tmp_path / "04-Quiz-Bank" / "karpathy" / "a.md")
    flags = layer1_flags({"04-Quiz-Bank/karpathy/a.md": (body, False)})
    assert "giveaway_overlap" in flags["04-Quiz-Bank/karpathy/a.md"]


def test_layer1_enumeration(tmp_path):
    body = "Pregunta\n\n---\n\n- uno\n- dos\n- tres\n- cuatro\n\nRef: `x.md`\n"
    flags = layer1_flags({"c.md": (body, False)})
    assert "enumeration" in flags["c.md"]


def test_layer1_enumeration_exempt_for_self_explain():
    body = "Pregunta\n\n---\n\n- paso uno\n- paso dos\n- paso tres\n- paso cuatro\n\nRef: `x.md`\n"
    flags = layer1_flags({"c.md": (body, True)})
    assert "c.md" not in flags or "enumeration" not in flags.get("c.md", [])


def test_layer1_too_long(tmp_path):
    long_answer = " ".join(["palabra"] * 60)
    body = f"Pregunta\n\n---\n\n{long_answer}\n\nRef: `x.md`\n"
    flags = layer1_flags({"c.md": (body, False)})
    assert "too_long" in flags["c.md"]


def test_layer1_too_long_uses_wider_budget_for_self_explain():
    # 60 words trips the normal MAX_WORDS=50 threshold, but is well under
    # the self-explain budget (120) — a derivation card at this length is
    # not "too long" per harvard-reviewer's own spec.
    answer_60_words = " ".join(["palabra"] * 60)
    body = f"Derivacion\n\n---\n\n{answer_60_words}\n\nRef: `x.md`\n"
    flags = layer1_flags({"c.md": (body, True)})
    assert "too_long" not in flags.get("c.md", [])


def test_layer1_duplicate_questions_flag_each_other():
    body_a = "Que es un vector unitario en algebra lineal?\n\n---\n\nRespuesta corta.\n"
    body_b = "Que es un vector unitario en el algebra lineal?\n\n---\n\nOtra respuesta corta.\n"
    flags = layer1_flags({"a.md": (body_a, False), "b.md": (body_b, False)})
    assert "duplicate" in flags["a.md"]
    assert "duplicate" in flags["b.md"]


def test_layer1_fine_card_has_no_flags():
    body = (
        "Que es X?\n\n---\n\nX es Y, una definicion breve y directa.\n\nRef: `x.md`\n"
    )
    flags = layer1_flags({"fine.md": (body, False)})
    assert "fine.md" not in flags


def test_layer1_malformed_qa_is_not_treated_as_clean():
    flags = layer1_flags({"broken.md": ("Pregunta sin respuesta", False)})

    assert "malformed_qa" in flags["broken.md"]


def test_run_flags_card_without_concept_mapping(tmp_path):
    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    _write_card(v, "unmapped.md", "Pregunta", "Respuesta breve.")

    report = run(v, Knowledge(), notes_info={})

    candidate = next(
        c for c in report.candidates if c.card_path.endswith("unmapped.md")
    )
    assert candidate.concept_slug is None
    assert "unmapped_concept" in candidate.reasons


def test_lapses_signal_suspect_when_understood():
    c = Concept(
        slug="x",
        title="X",
        unit="phase-0",
        evidence=[Evidence(kind="applied", at="2026-08-01", ref="scripts/x.py")],
    )
    assert lapses_signal(c, 7) == "suspect_card"


def test_lapses_signal_probably_dont_know_when_only_encountered():
    c = Concept(
        slug="x",
        title="X",
        unit="phase-0",
        evidence=[Evidence(kind="encountered", at="2026-08-01", ref="log.md")],
    )
    assert lapses_signal(c, 7) == "probably_dont_know_it"


def test_lapses_signal_none_below_threshold():
    c = Concept(slug="x", title="X", unit="phase-0")
    assert lapses_signal(c, 2) is None


def test_run_layer1_only_when_anki_unreachable(tmp_path):
    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    _write_card(v, "a.md", "Pregunta larga", " ".join(["palabra"] * 60))
    k = Knowledge()
    report = run(v, k, notes_info={})
    assert report.checked == 1
    assert any(c.card_path.endswith("a.md") for c in report.candidates)
    assert report.informational == []


def test_run_suspect_card_becomes_candidate_not_informational(tmp_path):
    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    _write_card(v, "a.md", "Pregunta ok", "Respuesta ok y breve.", note_id=555)
    k = Knowledge(
        concepts=[
            Concept(
                slug="x",
                title="X",
                unit="phase-0",
                evidence=[Evidence(kind="applied", at="2026-08-01", ref="s.py")],
                card_refs=[CardRef(path="04-Quiz-Bank/karpathy/a.md")],
            )
        ]
    )
    notes_info = {555: {"lapses": 7}}
    report = run(v, k, notes_info=notes_info)
    candidate_paths = {c.card_path for c in report.candidates}
    assert "04-Quiz-Bank/karpathy/a.md" in candidate_paths
    matched = next(
        c for c in report.candidates if c.card_path == "04-Quiz-Bank/karpathy/a.md"
    )
    assert "suspect_card" in matched.reasons
    assert matched.lapses == 7
    assert report.informational == []


def test_run_deck_param_reads_different_folder(tmp_path):
    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    long_answer = " ".join(["palabra"] * 60)
    _write_card(v, "a.md", "Pregunta larga", long_answer, ref="05-Projects/x.py")
    d = tmp_path / "04-Quiz-Bank" / "devtalles"
    d.mkdir(parents=True)
    body = f"---\ntags:\n  - repo-devtalles\nnoteId: 1\n---\n{'Pregunta larga'}\n\n---\n\n{long_answer}\n\nRef: `05-Projects/x.py`\n"
    v.write_text(d / "b.md", body)

    k = Knowledge()
    report_karpathy = run(v, k, notes_info={})
    assert report_karpathy.checked == 1

    report_devtalles = run(v, k, notes_info={}, deck="devtalles")
    assert report_devtalles.checked == 1
    assert any(
        c.card_path.endswith("devtalles/b.md") for c in report_devtalles.candidates
    )


def test_run_probably_dont_know_is_informational_not_candidate(tmp_path):
    v = Vault(root=tmp_path)
    (tmp_path / "00-Meta").mkdir()
    _write_card(v, "a.md", "Pregunta ok", "Respuesta ok y breve.", note_id=555)
    k = Knowledge(
        concepts=[
            Concept(
                slug="x",
                title="X",
                unit="phase-0",
                evidence=[Evidence(kind="encountered", at="2026-08-01", ref="log.md")],
                card_refs=[CardRef(path="04-Quiz-Bank/karpathy/a.md")],
            )
        ]
    )
    notes_info = {555: {"lapses": 7}}
    report = run(v, k, notes_info=notes_info)
    candidate_paths = {c.card_path for c in report.candidates}
    assert "04-Quiz-Bank/karpathy/a.md" not in candidate_paths
    assert len(report.informational) == 1
    assert report.informational[0].reason == "probably_dont_know_it"
