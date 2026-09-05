`quiron migrate` (`src/quiron/migrate.py`) wraps `copier` against
`C:\SANTIAGO\quiron\templates\`. It does not invent vault pedagogy
(`CLAUDE.md` session protocols, `01-Phases/` vs `01-Sections/` structure,
git init, Anki deck/namespace setup). Those stay vault-owned.

What it scaffolds: shared `.claude/` and `.opencode/` skill/agent/command
files, the OpenCode `AGENTS.md` bridge, the capture-callout block in
`03-Daily-Logs/_template.md`, and the three `00-Meta/` seed files
(`knowledge.json`, `inbox.jsonl`, `history.jsonl`). This skill is the
judgment layer over that deterministic command, same split as
`quiron-cards-decide` over `cards --set-policy`.

## Step 1 - Confirm The Vault Path And Gather Parameters

Confirm `--vault` with the user as an absolute path. Then work out the five
answers `quiron migrate` needs. This is the judgment call, not the templating:

- `--subject-expertise`: one or two sentences on the domain and expected reviewer expertise. Turn what the user said in conversation into this framing yourself; do not just ask them to write it verbatim.
- `--deck-path`: glob for the live quiz-bank deck, e.g. `04-Quiz-Bank/*.md`. The default is fine for a brand-new vault with no per-topic subfolder yet.
- `--topic-notes-path`: glob for topic notes, e.g. `02-Topics/*.md`.
- `--resync-command`: leave the default unless this vault already has a live Anki-synced deck and a known sync command.
- `--domain-framing`: a short clause `quiz-reviewer.md` inserts when checking topic notes, e.g. `or a math derivation skipping a step` for a math vault, or `or a claim that would fail in a real project` for a tooling course.

## Step 2 - Dry-Run First For Existing Vaults

Check whether `<vault>/00-Meta/knowledge.json` exists. If so, this is a
re-sync, not a fresh install, and `quiron migrate` defaults to dry-run
automatically. Run it without `--dry-run=false` first regardless, read the
plan (`create`/`update`/`skip` per file), and confirm nothing unexpected would
be overwritten before applying.

These files are protected after first scaffold by `_skip_if_exists`:
`CLAUDE.md`, `AGENTS.md`, `03-Daily-Logs/_template.md`, the three `00-Meta/`
seed files, `.claude/commands/quiz-me.md`, `.opencode/commands/quiz-me.md`,
`.claude/agents/quiz-reviewer.md`, `.opencode/agents/quiz-reviewer.md`,
`.claude/skills/quiz-review/SKILL.md`, and
`.opencode/skills/quiz-review/SKILL.md`.

Other shared Quiron workflow files are allowed to update from the canonical
templates on apply. Flag any dry-run `update` for a file the user may have
hand-edited.

```bash
uv run --directory C:\SANTIAGO\quiron quiron migrate --vault <vault> --subject-expertise "<...>" --deck-path "<...>" --topic-notes-path "<...>" --resync-command "<...>" --domain-framing "<...>"
```

## Step 3 - Apply

Once the plan looks right, re-run with `--dry-run=false`.

## Step 4 - Report

Summarize the files created/updated/skipped, the seed report, and the doctor
report. For a brand-new vault, zero concepts and zero findings are expected.
Remind the user that `CLAUDE.md` pedagogy, `01-*/` structure, git init, and
Anki setup are still manual next steps; `AGENTS.md` is only the OpenCode
bridge to that vault-owned pedagogy.
