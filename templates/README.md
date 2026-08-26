# quiron/templates/

Canonical source for vault-side prompt assets (agents, skills, commands) that more than one
vault uses — the same role `src/quiron/` plays for the Python side. Before this existed, shared
assets got hand-copied between vaults with no common source (`quiron-inbox/SKILL.md` first, in
Fase 5); this directory is where you edit first, going forward.

## How sync works today (Fase 6): manual

There is no templating engine yet. To apply a change:

1. Edit the file here.
2. Copy it into each vault that uses it (`<vault>/.claude/agents/...`, `<vault>/.claude/skills/...`).
3. For files with a `## Parameters for this vault` block (currently `agents/quiz-reviewer.md`
   and `skills/quiz-review/SKILL.md`), fill in that vault's `{{ mustache }}` placeholders —
   everything else in the file should stay byte-identical to the template.

Files with no parameters block (`skills/quiron-inbox/SKILL.md`) are copied verbatim, no edits.

## What Fase 7 automates

Fase 7 ("template, only if 1-6 hold") introduces `copier` + `copier.yml` + `quiron migrate`.
The `{{ }}` placeholder syntax used here is deliberately copier/Jinja-compatible so those files
can be consumed directly by that tooling without a rewrite — this phase proves the parameter
shape works by hand first.

## What's NOT here, on purpose

Not every vault asset with a same-named counterpart belongs here. `session-close`/`wrap-up` and
`note-collect`/`cc-note-verify` look like duplicates but have genuinely diverged in scope and
rigor for reasons specific to each vault — see `quiron/DECISIONS.md`'s Fase 6 entry before
"fixing" that by unifying them.
