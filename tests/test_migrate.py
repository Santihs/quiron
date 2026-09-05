from quiron.migrate import run_migrate

ANSWERS = {
    "subject_expertise": "test subject",
    "deck_path": "04-Quiz-Bank/*.md",
    "topic_notes_path": "02-Topics/*.md",
    "resync_command": "not applicable",
    "domain_framing": "or a claim that doesn't hold up",
}


def test_run_migrate_scaffolds_new_vault(tmp_path):
    vault_path = tmp_path / "vault"
    report = run_migrate(vault_path, ANSWERS)

    assert (vault_path / "00-Meta" / "knowledge.json").exists()
    assert (vault_path / "00-Meta" / "inbox.jsonl").exists()
    assert (vault_path / "00-Meta" / "history.jsonl").exists()
    assert (vault_path / "03-Daily-Logs" / "_template.md").exists()
    assert (vault_path / ".claude" / "skills" / "quiron-inbox" / "SKILL.md").exists()
    assert (vault_path / ".claude" / "skills" / "quiz-review" / "SKILL.md").exists()
    assert (vault_path / ".claude" / "agents" / "quiz-reviewer.md").exists()
    assert (vault_path / ".claude" / "commands" / "quiz-me.md").exists()
    assert (vault_path / "AGENTS.md").exists()
    assert (vault_path / ".opencode" / "skills" / "quiron-inbox" / "SKILL.md").exists()
    assert (vault_path / ".opencode" / "skills" / "quiz-review" / "SKILL.md").exists()
    assert (vault_path / ".opencode" / "agents" / "quiz-reviewer.md").exists()
    assert (vault_path / ".opencode" / "commands" / "quiz-me.md").exists()

    review_skill = (
        vault_path / ".claude" / "skills" / "quiz-review" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert (
        "test subject" not in review_skill
    )  # subject_expertise goes into quiz-reviewer.md, not this file
    assert "04-Quiz-Bank/*.md" in review_skill
    assert "{{" not in review_skill  # every placeholder rendered, none left literal

    reviewer_agent = (vault_path / ".claude" / "agents" / "quiz-reviewer.md").read_text(
        encoding="utf-8"
    )
    assert "test subject" in reviewer_agent
    assert "{{" not in reviewer_agent

    opencode_review_skill = (
        vault_path / ".opencode" / "skills" / "quiz-review" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "04-Quiz-Bank/*.md" in opencode_review_skill
    assert "{{" not in opencode_review_skill

    opencode_reviewer_agent = (
        vault_path / ".opencode" / "agents" / "quiz-reviewer.md"
    ).read_text(encoding="utf-8")
    assert "test subject" in opencode_reviewer_agent
    assert "{{" not in opencode_reviewer_agent

    for rendered_path in (
        vault_path / ".claude" / "skills" / "quiron-inbox" / "SKILL.md",
        vault_path / ".opencode" / "skills" / "quiron-inbox" / "SKILL.md",
        vault_path / ".opencode" / "skills" / "quiron-init" / "SKILL.md",
        vault_path / ".opencode" / "skills" / "quiron-cards-decide" / "SKILL.md",
    ):
        rendered = rendered_path.read_text(encoding="utf-8")
        assert "{% include" not in rendered
        assert "{{" not in rendered
        assert "Use the same workflow as `.claude" not in rendered

    opencode_init = (
        vault_path / ".opencode" / "skills" / "quiron-init" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "AGENTS.md" in opencode_init
    assert "_skip_if_exists" in opencode_init
    assert not (vault_path / "_shared").exists()

    assert report.seed_report is not None
    assert report.doctor_report is not None
    assert report.doctor_report.concept_count == 0


def test_run_migrate_dry_run_writes_nothing(tmp_path):
    vault_path = tmp_path / "vault"
    report = run_migrate(vault_path, ANSWERS, dry_run=True)

    assert not (vault_path / "00-Meta" / "knowledge.json").exists()
    assert report.seed_report is None
    assert report.doctor_report is None


def test_run_migrate_skip_if_exists_protects_hand_authored_files(tmp_path):
    vault_path = tmp_path / "vault"
    run_migrate(vault_path, ANSWERS)

    claude_md = vault_path / "CLAUDE.md"
    claude_md.write_text("MY HAND-WRITTEN PEDAGOGY", encoding="utf-8")
    agents_md = vault_path / "AGENTS.md"
    agents_md.write_text("MY OPENCODE BRIDGE", encoding="utf-8")
    knowledge_path = vault_path / "00-Meta" / "knowledge.json"
    original_knowledge = knowledge_path.read_text(encoding="utf-8")

    run_migrate(vault_path, {**ANSWERS, "subject_expertise": "changed subject"})

    assert claude_md.read_text(encoding="utf-8") == "MY HAND-WRITTEN PEDAGOGY"
    assert agents_md.read_text(encoding="utf-8") == "MY OPENCODE BRIDGE"
    # knowledge.json is _skip_if_exists too -- untouched by copier itself,
    # though run_migrate's own seed pass may rewrite it with the same content.
    assert "concepts" in knowledge_path.read_text(encoding="utf-8")

    reviewer_agent = (vault_path / ".claude" / "agents" / "quiz-reviewer.md").read_text(
        encoding="utf-8"
    )
    assert "test subject" in reviewer_agent  # skip-protected -- NOT re-synced
    assert "changed subject" not in reviewer_agent

    review_skill = (
        vault_path / ".claude" / "skills" / "quiz-review" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert (
        "not applicable" in review_skill
    )  # original resync_command, also skip-protected

    opencode_reviewer = (
        vault_path / ".opencode" / "agents" / "quiz-reviewer.md"
    ).read_text(encoding="utf-8")
    assert "test subject" in opencode_reviewer
    assert "changed subject" not in opencode_reviewer

    opencode_review_skill = (
        vault_path / ".opencode" / "skills" / "quiz-review" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "not applicable" in opencode_review_skill

    assert original_knowledge  # sanity: it existed before the second run too
