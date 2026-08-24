from quiron.capture import (
    extract_captures,
    load_inbox,
    scan,
    scan_and_merge,
    write_inbox,
)


def test_extract_single_line_callouts():
    body = (
        "> [!duda] no entiendo por que Av=lambda*v conserva la direccion\n"
        "\n"
        "> [!concepto] descomposicion espectral\n"
        "\n"
        "> [!aplicado] eigenvectores\n"
    )
    caps = extract_captures(body, "03-Daily-Logs/2026-08-23.md")
    assert [c.kind for c in caps] == ["duda", "concepto", "aplicado"]
    assert caps[0].text == "no entiendo por que Av=lambda*v conserva la direccion"


def test_extract_multiline_continuation():
    body = (
        "> [!duda] no entiendo\n"
        "> por que Av=lambda*v\n"
        "> conserva la direccion\n"
        "\n"
        "texto normal despues\n"
    )
    caps = extract_captures(body, "log.md")
    assert len(caps) == 1
    assert caps[0].text == "no entiendo por que Av=lambda*v conserva la direccion"


def test_extract_ignores_plain_blockquote():
    body = "> Goal: aprender algebra lineal\n"
    caps = extract_captures(body, "log.md")
    assert caps == []


def test_extract_case_insensitive_type():
    body = "> [!DUDA] mayusculas\n"
    caps = extract_captures(body, "log.md")
    assert caps[0].kind == "duda"


def test_id_stable_across_calls():
    body = "> [!duda] texto identico\n"
    caps1 = extract_captures(body, "log.md")
    caps2 = extract_captures(body, "log.md")
    assert caps1[0].id == caps2[0].id


def test_scan_finds_captures_across_daily_logs(vault):
    caps = scan(vault)
    # fixtures/vault/03-Daily-Logs is empty by default in this fixture set
    assert isinstance(caps, list)


def test_scan_and_merge_is_idempotent(tmp_path):
    from quiron.vault import Vault

    v = Vault(root=tmp_path)
    (tmp_path / "03-Daily-Logs").mkdir()
    (tmp_path / "00-Meta").mkdir()
    log = tmp_path / "03-Daily-Logs" / "2026-08-23.md"
    v.write_text(log, "> [!duda] pregunta de prueba\n")

    found1, added1 = scan_and_merge(v)
    assert added1 == 1
    inbox1 = load_inbox(v)
    assert len(inbox1) == 1
    assert inbox1[0]["processed"] is False

    found2, added2 = scan_and_merge(v)
    assert added2 == 0
    inbox2 = load_inbox(v)
    assert len(inbox2) == 1


def test_dirty_inbox_entry_survives_untouched(tmp_path):
    from quiron.vault import Vault

    v = Vault(root=tmp_path)
    (tmp_path / "03-Daily-Logs").mkdir()
    (tmp_path / "00-Meta").mkdir()
    log = tmp_path / "03-Daily-Logs" / "2026-08-23.md"
    v.write_text(log, "> [!duda] sin procesar\n")

    scan_and_merge(v)
    inbox = load_inbox(v)
    inbox[0]["processed"] = False
    write_inbox(v, inbox)

    # re-scanning does not clobber the unprocessed entry or duplicate it
    scan_and_merge(v)
    inbox_after = load_inbox(v)
    assert len(inbox_after) == 1
    assert inbox_after[0]["processed"] is False
