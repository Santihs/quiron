# quiron/templates/

Canonical source for vault-side prompt assets (agents, skills, commands) that more than one
vault uses — the same role `src/quiron/` plays for the Python side. Before this existed, shared
assets got hand-copied between vaults with no common source (`quiron-inbox/SKILL.md` first, in
Fase 5); this directory is where you edit first, going forward.

Shared workflow bodies live under `_shared/`. Tool-specific files under `.claude/` and
`.opencode/` should stay thin: keep only discovery/frontmatter differences there, then include
the shared body with Jinja. `copier.yml` excludes `_shared/` from vault output, so generated
vault files contain the fully rendered workflow but not the source-only partials.

## How sync works (Fase 7): `quiron migrate`

`quiron migrate --vault <path> --subject-expertise "..." --deck-path "..." ...` (see
`src/quiron/migrate.py`, `.claude/skills/quiron-init/SKILL.md`, and
`.opencode/skills/quiron-init/SKILL.md`) wraps `copier` against this directory. It fills in
`{{ params }}`, skips files a vault has hand-authored (`_skip_if_exists` in `copier.yml`:
`CLAUDE.md`, `AGENTS.md`, `03-Daily-Logs/_template.md`, the three `00-Meta/` seed files, and the
vault-owned quiz/reviewer files that carry card-format knowledge), and defaults to a dry-run
whenever the target vault already has a `00-Meta/knowledge.json` — pass `--dry-run=false` to
apply. Shared plumbing under `.claude/` and `.opencode/` is maintained here; a skill that needs
to genuinely diverge (not just different params) doesn't belong here at all — see
`DECISIONS.md`'s Fase 6 entry on `session-close`/`wrap-up`.

Before Fase 7, this was manual copy-paste per vault — no longer needed, `quiron migrate` is the
only way to sync a change here into a vault now.

## What's NOT here, on purpose

Not every vault asset with a same-named counterpart belongs here. `session-close`/`wrap-up` and
`note-collect`/`cc-note-verify` look like duplicates but have genuinely diverged in scope and
rigor for reasons specific to each vault — see `quiron/DECISIONS.md`'s Fase 6 entry before
"fixing" that by unifying them.
