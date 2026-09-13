import pytest
from unittest.mock import patch

from quiron.migrate import run_migrate

ANSWERS = {
    "subject_expertise": "test subject",
    "deck_path": "04-Quiz-Bank/*.md",
    "topic_notes_path": "02-Topics/*.md",
    "resync_command": "not applicable",
    "domain_framing": "or a claim that doesn't hold up",
}


@pytest.fixture(autouse=True)
def mock_anki_status():
    with patch(
        "quiron.doctor.ankiconnect.status", return_value={"state": "unavailable"}
    ):
        yield


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

    quiz_me = (vault_path / ".claude" / "commands" / "quiz-me.md").read_text(
        encoding="utf-8"
    )
    assert "<!-- quiron:shared-quiz-me-evidence:start -->" in quiz_me
    assert "quiron evidence --add" in quiz_me

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

    assert not vault_path.exists()
    assert not (vault_path / "00-Meta" / "knowledge.json").exists()
    assert report.seed_report is None
    assert report.doctor_report is None
    assert any(line.startswith("create ") for line in report.copier_output)


def test_run_migrate_validates_existing_knowledge_before_copy(tmp_path, monkeypatch):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    (vault_path / "README.md").write_text("existing", encoding="utf-8")
    (vault_path / "00-Meta").mkdir()
    (vault_path / "00-Meta" / "knowledge.json").write_text("not json", encoding="utf-8")

    def fail_copy(**kwargs):
        raise AssertionError("copier should not run")

    monkeypatch.setattr("quiron.migrate.copier.run_copy", fail_copy)

    from quiron.errors import QuironError

    with pytest.raises(QuironError, match="knowledge.json is invalid"):
        run_migrate(vault_path, ANSWERS, dry_run=False)


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


def test_run_migrate_updates_shared_quiz_me_block_only(tmp_path):
    vault_path = tmp_path / "vault"
    for tool in (".claude", ".opencode"):
        command = vault_path / tool / "commands" / "quiz-me.md"
        command.parent.mkdir(parents=True)
        command.write_text(
            f"# /quiz-me\n\n{tool} custom quiz extension\n", encoding="utf-8"
        )

    with patch("quiron.doctor.ankiconnect.status", return_value={"state": "connected"}):
        run_migrate(vault_path, ANSWERS)

    start = "<!-- quiron:shared-quiz-me-evidence:start -->"
    end = "<!-- quiron:shared-quiz-me-evidence:end -->"
    for tool in (".claude", ".opencode"):
        content = (vault_path / tool / "commands" / "quiz-me.md").read_text(
            encoding="utf-8"
        )
        assert f"{tool} custom quiz extension" in content
        assert content.count(start) == 1
        assert content.count(end) == 1
        assert "quiron evidence --add" in content

    with patch("quiron.doctor.ankiconnect.status", return_value={"state": "connected"}):
        run_migrate(vault_path, ANSWERS)

    for tool in (".claude", ".opencode"):
        content = (vault_path / tool / "commands" / "quiz-me.md").read_text(
            encoding="utf-8"
        )
        assert content.count(start) == 1
        assert content.count(end) == 1


def test_run_migrate_dry_run_reports_quiz_me_sync_without_writing(tmp_path):
    vault_path = tmp_path / "vault"
    command = vault_path / ".claude" / "commands" / "quiz-me.md"
    command.parent.mkdir(parents=True)
    original = "# /quiz-me\n\ncustom extension\n"
    command.write_text(original, encoding="utf-8")

    report = run_migrate(vault_path, ANSWERS, dry_run=True)

    assert "update .claude/commands/quiz-me.md" in report.copier_output
    assert command.read_text(encoding="utf-8") == original


def test_run_migrate_dry_run_skips_identical_shared_workflows(tmp_path):
    vault_path = tmp_path / "vault"
    run_migrate(vault_path, ANSWERS, templates_only=True)

    report = run_migrate(vault_path, ANSWERS, dry_run=True, templates_only=True)

    assert "skip .claude/skills/quiron-inbox/SKILL.md" in report.copier_output
    assert "skip .opencode/skills/quiron-init/SKILL.md" in report.copier_output

    inbox_skill = vault_path / ".claude" / "skills" / "quiron-inbox" / "SKILL.md"
    inbox_skill.write_text("custom workflow", encoding="utf-8")

    report = run_migrate(vault_path, ANSWERS, dry_run=True, templates_only=True)

    assert "update .claude/skills/quiron-inbox/SKILL.md" in report.copier_output


def test_run_migrate_templates_only_preserves_knowledge(tmp_path):
    vault_path = tmp_path / "vault"
    knowledge_path = vault_path / "00-Meta" / "knowledge.json"
    knowledge_path.parent.mkdir(parents=True)
    original = (
        '{"schema_version":2,"concepts":[{"slug":"x","title":"X",'
        '"unit":"u","card_refs":[{"path":"04-Quiz-Bank/legacy.md"}]}]}\n'
    )
    knowledge_path.write_text(original, encoding="utf-8")

    report = run_migrate(vault_path, ANSWERS, templates_only=True)

    assert report.seed_report is None
    assert report.doctor_report is None
    assert knowledge_path.read_text(encoding="utf-8") == original
    quiz_me = (vault_path / ".claude" / "commands" / "quiz-me.md").read_text(
        encoding="utf-8"
    )
    assert "quiron evidence --add" in quiz_me
