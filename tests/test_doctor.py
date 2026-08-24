from quiron.doctor import run


def test_doctor_lists_dangling_ref(vault):
    report = run(vault)
    dangling_cards = {d["card"] for d in report.dangling_refs}
    assert "04-Quiz-Bank/karpathy/unresolvable-ref.md" in dangling_cards


def test_doctor_lists_unlinked_doubt(vault):
    report = run(vault)
    assert "06-Doubts-Resolved/span-de-vectores.md" in report.unlinked_doubts


def test_doctor_reports_headings_skipped(vault):
    report = run(vault)
    assert any("Implementacion propia" in h for h in report.headings_skipped)


def test_doctor_to_dict_is_json_serializable(vault):
    import json

    report = run(vault)
    json.dumps(report.to_dict())


def test_doctor_concept_count_positive(vault):
    report = run(vault)
    assert report.concept_count > 0
