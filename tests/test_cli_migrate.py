from quiron.cli import main


def test_migrate_new_vault_applies_directly(tmp_path, capsys):
    vault_path = tmp_path / "vault"
    rc = main(
        ["migrate", "--vault", str(vault_path), "--subject-expertise", "interview prep"]
    )
    assert rc == 0

    out = capsys.readouterr().out
    assert "dry run" not in out
    assert (vault_path / "00-Meta" / "knowledge.json").exists()
    assert (vault_path / ".claude" / "skills" / "quiron-inbox" / "SKILL.md").exists()
    assert (vault_path / "AGENTS.md").exists()
    assert (vault_path / ".opencode" / "skills" / "quiron-inbox" / "SKILL.md").exists()
    assert (vault_path / ".opencode" / "skills" / "quiron-init" / "SKILL.md").exists()
    opencode_init = (
        vault_path / ".opencode" / "skills" / "quiron-init" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "{% include" not in opencode_init
    assert "AGENTS.md" in opencode_init


def test_migrate_existing_vault_defaults_to_dry_run(tmp_path, capsys):
    vault_path = tmp_path / "vault"
    main(["migrate", "--vault", str(vault_path), "--subject-expertise", "v1"])
    capsys.readouterr()

    (vault_path / "CLAUDE.md").write_text("MY PEDAGOGY", encoding="utf-8")
    (vault_path / "AGENTS.md").write_text("MY OPENCODE BRIDGE", encoding="utf-8")

    rc = main(["migrate", "--vault", str(vault_path), "--subject-expertise", "v2"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "dry run" in out
    assert (vault_path / "CLAUDE.md").read_text(encoding="utf-8") == "MY PEDAGOGY"
    assert (vault_path / "AGENTS.md").read_text(
        encoding="utf-8"
    ) == "MY OPENCODE BRIDGE"

    rc = main(
        [
            "migrate",
            "--vault",
            str(vault_path),
            "--subject-expertise",
            "v2",
            "--dry-run=false",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "dry run" not in out
    assert (vault_path / "CLAUDE.md").read_text(encoding="utf-8") == "MY PEDAGOGY"
    assert (vault_path / "AGENTS.md").read_text(
        encoding="utf-8"
    ) == "MY OPENCODE BRIDGE"
    # quiz-reviewer.md is also _skip_if_exists (it can carry vault-specific
    # card-format knowledge beyond these params, e.g. devtalles' lack of a
    # Ref: line convention) -- so it keeps its original "v1" value.
    reviewer = (vault_path / ".claude" / "agents" / "quiz-reviewer.md").read_text(
        encoding="utf-8"
    )
    assert "v1" in reviewer
    assert "v2" not in reviewer
    opencode_reviewer = (
        vault_path / ".opencode" / "agents" / "quiz-reviewer.md"
    ).read_text(encoding="utf-8")
    assert "v1" in opencode_reviewer
    assert "v2" not in opencode_reviewer
