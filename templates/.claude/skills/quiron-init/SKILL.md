---
name: quiron-init
description: Scaffold or re-sync quiron's plumbing into this vault via `quiron migrate` — the skill/agent/command files, the capture-callout daily-log block, and the 00-Meta/ seed files. Trigger on "/quiron-init", "arranca quiron en este vault", "instala quiron acá", "sincronizá quiron con la última versión", or when setting up a brand-new study vault from scratch.
---

# quiron-init

`quiron migrate` (`src/quiron/migrate.py`) wraps `copier` against
`C:\SANTIAGO\quiron\templates\` — it does NOT invent vault pedagogy
(`CLAUDE.md` session protocols, `01-Phases/` vs `01-Sections/` structure,
git init, Anki deck/namespace setup). Those stay yours to write. What it
does scaffold: the shared `.claude/skills|agents|commands/` files
(parametrized), the capture-callout block in `03-Daily-Logs/_template.md`,
and the three `00-Meta/` seed files (`knowledge.json`, `inbox.jsonl`,
`history.jsonl`). This skill is the judgment layer over that command — same
split as `quiron-cards-decide` over `cards --set-policy`.

## Step 1 — Confirm the vault path and gather the parameters

Confirm `--vault` with the user (absolute path). Then work out the 5
answers `quiron migrate` needs — this is the actual judgment call, not the
templating:

- `--subject-expertise`: 1-2 sentences on the domain and the expected
  reviewer expertise (feeds `quiz-reviewer.md`'s accuracy checks). Turn
  whatever the user said in conversation ("interview prep", "the DevTalles
  Claude Code course") into this framing yourself — don't just ask them to
  write it verbatim.
- `--deck-path`: glob for the live quiz-bank deck, e.g. `04-Quiz-Bank/*.md`.
  Default is fine for a brand-new vault with no per-topic subfolder yet.
- `--topic-notes-path`: glob for topic notes, e.g. `02-Topics/*.md`.
- `--resync-command`: leave the default ("not applicable...") unless this
  vault already has a live Anki-synced deck and a known sync command.
- `--domain-framing`: a short clause `quiz-reviewer.md` inserts when
  checking topic notes (e.g. "or a math derivation skipping a step" for a
  math vault, "or a claim that would fall apart under interviewer
  follow-up" for interview prep).

## Step 2 — Dry-run first if the vault already has quiron installed

Check whether `<vault>/00-Meta/knowledge.json` already exists — if so, this
is a re-sync, not a fresh install, and `quiron migrate` defaults to dry-run
automatically in that case anyway. Run it without `--dry-run=false` first
regardless of what you expect, read the plan (`create`/`update`/`skip` per
file), and confirm nothing unexpected would be overwritten before applying.
A hand-customized skill/agent/command file beyond its `{{ params }}` WILL
be overwritten on apply — `_skip_if_exists` only protects `CLAUDE.md`,
`03-Daily-Logs/_template.md`, and the three `00-Meta/` seed files. Flag
this to the user if the dry-run plan shows an `update` on a file they might
have hand-edited.

```
uv run --directory C:\SANTIAGO\quiron quiron migrate --vault <vault> ^
  --subject-expertise "<...>" --deck-path "<...>" --topic-notes-path "<...>" ^
  --resync-command "<...>" --domain-framing "<...>"
```

## Step 3 — Apply

Once the plan looks right, re-run with `--dry-run=false`.

## Step 4 — Report

Summarize: files created/updated, the seed report (concepts found from any
pre-existing `02-Topics/`/`04-Quiz-Bank/` content), and the doctor report
(dangling refs, orphaned concepts, unlinked doubts — same output as running
`quiron doctor` directly). For a brand-new vault these will all be zero,
which is expected, not a failure. Remind the user that `CLAUDE.md`
pedagogy, `01-*/` structure, git init, and Anki setup are still manual next
steps this command doesn't touch.
