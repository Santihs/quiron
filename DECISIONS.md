# Decisions

## Assistant plumbing targets both Claude Code and OpenCode; pedagogy stays vault-owned

`quiron migrate` now scaffolds both `.claude/` and `.opencode/` prompt
plumbing from the same `templates/` source. This is a maintenance feature, not
a second vault model: Quiron still owns shared workflows (`quiron-inbox`,
`quiron-cards-*`, `quiz-review`, `quiz-reviewer`, and the shared `quiz-me`
core), while each vault owns its learning protocol in `CLAUDE.md`.

OpenCode needs an `AGENTS.md` bridge because it does not automatically treat
`CLAUDE.md` as project memory. The bridge is intentionally thin: read and
follow `CLAUDE.md`, translate slash commands to `.opencode/commands/`, and use
`.opencode/skills|agents/` for Quiron workflows. It does not duplicate
karpathy/devtalles pedagogy or prescribe a generic study loop.

The same skip posture from Fase 7 applies to OpenCode. `AGENTS.md`,
`.opencode/commands/quiz-me.md`, `.opencode/agents/quiz-reviewer.md`, and
`.opencode/skills/quiz-review/SKILL.md` are protected after first scaffold
because they can carry real vault-specific card-format knowledge. The remaining
OpenCode Quiron workflow skills are thin wrappers over the same deterministic
CLI doors and should stay synchronized from `templates/`.

## Fase 7: `quiron migrate` wraps `copier` against `templates/`, dry-run by default on existing vaults

Fase 6 left `templates/` as canon but the sync onto each vault was manual
copy-paste (`templates/README.md` said so explicitly, and named this phase
as its automation). `quiron migrate` (`src/quiron/migrate.py`) is that
automation: `copier.run_copy()` against `templates/`, then the existing
`seed.py`/`doctor.py` passes, reused rather than reimplemented — no second
templating engine, no hand-rolled skip-if-exists logic.

**Scope, deliberately narrow.** It scaffolds only the quiron-specific
plumbing: `.claude/skills|agents|commands/` (parametrized), the
capture-callout block in `03-Daily-Logs/_template.md`, and the three
`00-Meta/` seed files. It does not generate vault pedagogy — `CLAUDE.md`
session protocols, `01-Phases/` vs `01-Sections/` structure, git init, Anki
deck/namespace setup all stay hand-authored, same as today, for both
existing vaults and a new one. Templating pedagogy would mean guessing a
one-size-fits-all study loop; karpathy's and devtalles' `CLAUDE.md` files
already diverge on purpose (see the "Fase 5 generalization" entry below).

**`_templates_suffix: ""` is required, and was not obvious.** copier's
default only renders files ending in `.jinja`; every file already in
`templates/` (`_shared/skills/*.md`, `_shared/agents/quiz-reviewer.md`,
`_shared/commands/quiz-me-core.md`, and their tool-specific wrappers) has
`{{ }}` placeholders with no `.jinja` suffix,
Fase 6's naming convention. Without this setting, every placeholder would
copy as literal unrendered text into every vault. Found by running copier
for real against a throwaway sandbox (`quiron/migrate/`, gitignored, never
committed) before writing `migrate.py` — confirmed rather than assumed.

**Canonical shared workflow files are not protected by default.**
`_skip_if_exists` protects `CLAUDE.md`, `AGENTS.md`,
`03-Daily-Logs/_template.md`, the three `00-Meta/` seed files, and the
vault-specific `quiz-me` and `quiz-reviewer` files. Other shared Quiron
workflow files are meant to stay byte-identical to `templates/` modulo
`{{ params }}` — that is the purpose of Fase 6 having a canonical source.
A vault that needs a workflow to genuinely diverge (not just different
parameters) should not put it in the shared template; this is the same
reasoning used for `session-close`/`wrap-up` staying vault-specific (Fase 6
entry below). Because a customization beyond parameters would otherwise be
silently overwritten, `quiron migrate` defaults to a dry-run (Copier's own
create/update/skip plan) whenever the target vault already has a
`00-Meta/knowledge.json`; a brand-new vault has nothing to lose and applies
directly. This follows the `quiron-anki-sync` `yanki sync --dry-run`
precedent.

## `quiron-anki-sync` skill: yanki is headless, not Obsidian-only

`Quiron.md`'s risk list claimed "Obsidian is required for sync, not
optional" — yanki assumed to be an Obsidian-only plugin with no scriptable
path. Wrong, discovered while closing the loop on claude-devtalles' 14 new
cards (from `quiron-cards-decide`): `npx yanki sync <dir>` is a headless npm
CLI. Verified live: `--dry-run` first (14 creates, 0 touched/deleted, safe to
inspect before committing), then a real run, matching the vault's *existing*
sync group via `--namespace "Obsidian - Vault ID <id>"` — read that id off
any already-synced note's `YankiNamespace` field in Anki before running, so
the new notes join the same group instead of forking a second one under
yanki's default `"Yanki"` namespace.

The same trip surfaced real drift worth generalizing past: claude-devtalles'
Anki deck had 45 notes against only 17 live `## Q:` blocks in the vault — 30
notes whose source content had since been rewritten into `02-Topics/` prose
and never cleaned up Anki-side (yanki only pushes; it doesn't reconcile
deletions when a file's Q&A block simply disappears from a *different* file
than the one it manages). Diagnosed with a one-off AnkiConnect diff script,
confirmed against the vault by hand, deleted via `deleteNotes` — sensitive
enough to require standing user confirmation each time (Claude Code's own
auto-mode classifier blocks `deleteNotes` outright without it), so this stays
a diff-and-report skill, never an auto-delete one.

`quiron-anki-sync` (new skill, `templates/_shared/skills/quiron-anki-sync.md`,
vault-agnostic): wraps the `--dry-run`-then-real `npx yanki sync` flow for
pushing new/changed cards, and a separate orphan-detection pass (AnkiConnect
`findNotes`+`notesInfo` vs. a scan of the vault's `## Q:`/`Ref:` sources) that
lists candidates and always waits for explicit per-run confirmation before
calling `deleteNotes` — never bundled into the push side, and never run
unattended. `ankiconnect.py` stays read-only for quiron's own Python (no
`addNote`/`deleteNotes` added there) — this skill drives `yanki`/AnkiConnect
directly as a Claude Code capability, not as a quiron CLI subcommand, keeping
the "quiron's Python never writes to Anki" boundary from `Quiron.md` intact
even though the *mechanism* for a human process to do so is now scriptable.

## `cards --set-policy` + `quiron-cards-decide`: give `--decide` an agent-drivable door

`quiron cards --vault <vault> --decide` (Fase 2) is a blocking `input()` loop — the
interaction and the persistence live in the same function
(`coverage.decide`). Every other phase in this project keeps Python
deterministic and puts judgment in a Claude Code skill (`quiron-inbox` is the
model: scan/validate/write in Python, classification in the skill, apply
back through Python). `--decide` was the one place that split never
happened, and it went unnoticed until claude-devtalles seeded 20 concepts,
all `undecided`, with titles alone giving no real basis to decide — the
walker's one-line-per-concept format has no room to show the actual note
content.

Fix follows the exact precedent already in this codebase —
`audit.ReviewProposal`/`record_review` — rather than inventing a new shape:
`coverage.PolicyDecision` (slug, card_policy, optional declined_reason) and
`coverage.set_policy(knowledge, decisions) -> SetPolicyReport` apply a
pre-made batch of decisions non-interactively; unknown slugs land in
`skipped_unknown_slug` instead of raising, same posture as every other batch
apply in this codebase (`inbox.apply_proposals`, `audit.record_review`).
Wired into the CLI as `cards --set-policy FILE`, alongside a small read-only
`cards --list-undecided [--json]` (nothing previously exposed the undecided
list without triggering the interactive walker). `coverage.decide()` and
`cards --decide` are untouched — still the right tool outside Claude Code.

`quiron-cards-decide` (new skill, `templates/_shared/skills/quiron-cards-decide.md`,
vault-agnostic like `quiron-inbox` — no parameters block) is the actual
payoff: it reads each undecided concept's `notes_ref` file so the user
decides from real content, accepts natural-language answers instead of
forced `n`/`d`/`s` keystrokes, and persists through `--set-policy`.

## Fase 6: `quiron/templates/` as canon, reviewer parametrized, quiz-me partially templated

Full inventory of both vaults' `.claude/{agents,skills,commands}/` before deciding what's
shareable (per an explicit ask to "review what is useful too," not just template everything):

- **`quiron-inbox`** was already byte-identical between vaults (confirmed by diff) — already
  de facto shared, just with no common source. Moved into `quiron/templates/_shared/`
  unchanged; both vault copies still diff clean against it.
- **`harvard-reviewer`/`harvard-review`** generalized cleanly: of 37 lines, exactly four were
  karpathy-specific (the ML/AI framing, the hardcoded deck path, one domain-flavored phrase),
  everything else — the accuracy pass, minimum-information sizing, self-explain handling, the
  typed verdict, the report format — was already generic. Renamed `quiz-reviewer`/`quiz-review`,
  the four spots became a `## Parameters for this vault` block with `{{ mustache }}`
  placeholders in the canonical template (`quiron/templates/_shared/agents/quiz-reviewer.md`,
  `quiron/templates/_shared/skills/quiz-review.md`) — deliberately copier/Jinja-compatible syntax
  so Fase 7 can consume these files directly. karpathy-path's filled-in copy diffs clean
  against the template outside the parameters block.
- **devtalles' `quiz-reviewer.md` diverges beyond the parameters block**, and that divergence is
  real, not an error: this vault's cards have no `Ref:` line and no `self-explain` convention
  (confirmed in Fase 5's exploration), so the template's format-checking paragraph — written
  for karpathy's `Ref:`-per-card, `self-explain`-flagged format — would send the reviewer
  hunting for something that doesn't exist. Its copy instead says to cross-check against the
  relevant topic/section note by topic match, and drops the `self-explain` sizing exception.
  This is the same category of finding as Fase 5's card-model gap: the *shape* of the review
  (accuracy pass, sizing pass, typed verdict) generalizes; a couple of format-dependent
  sentences inside it don't, yet, and forcing false uniformity there would be worse than naming
  the real difference.
- **`quiron-cards-audit`** moved into `templates/_shared/` as a canonical, parameter-free copy
  (its `harvard-reviewer`/`harvard-review` references became `quiz-reviewer`/`quiz-review`).
  Still only lives in karpathy-path — not copied to devtalles, same root cause as Fase 5 (cards
  there aren't individually addressable, so the audit round trip has nothing to dispatch on).
- **`/quiz-me`** got a *partial* template (`quiron/templates/_shared/commands/quiz-me-core.md`):
  the parts already byte-identical in both vaults today — the generation-first flow and strict
  grading rubric. The old shared copy also carried scheduler comments and SM-2 arithmetic, but
  that text is now removed from the canonical core because Anki owns scheduling. Both vaults'
  real `quiz-me.md` files got a one-line marker comment pointing at this template for that
  section; nothing else about either file changed — this template is a floor, not a merge. The
  parts that differ
  (card file format, karpathy's live-deck + `self-explain` + `quiron evidence` branch,
  topic-interleaving selection, devtalles' empty-bank draft-from-notes fallback and
  save-new-question step) stay as genuine per-vault extensions.
- **`session-close`/`wrap-up` and `note-collect`/`cc-note-verify` were explicitly NOT
  templated** this phase. Both pairs look like duplicates but diverged for real reasons:
  `session-close` (karpathy) has WAIT gates, streak/hour tracking, and an unconditional push
  after confirmation; `wrap-up` (devtalles) is simpler, has no WAIT gate, and pushes only on
  full-section completion — reconciling these is a content decision about how much rigor
  devtalles' session-closing should have, not a mechanical extraction. `note-collect` does web
  research + generates LaTeX/HTML visuals (linear algebra needs this, devtalles doesn't);
  `cc-note-verify` does two-source fact-checking (subagent + direct `WebFetch` against official
  docs) because this course's own narration has been wrong before (a real, documented incident,
  commit `6f32cdb`) — a failure mode karpathy's material doesn't have. Forcing these into one
  template would either strip devtalles' extra rigor or bolt visual-generation onto a vault that
  doesn't need it. Left alone on purpose; revisit only if a real duplicated-effort pain shows up,
  not preemptively.
- **`quiron/templates/`** is now the canonical source for shared vault-side prompt assets, the
  same role `src/quiron/` plays for the Python. Sync is manual this phase (edit the template,
  copy into each vault, fill in that vault's parameters) — Fase 7's copier is expected to
  automate exactly this, which is why the placeholder syntax was chosen to match it now.

## Fase 5 generalization: frontmatter optional, file-level concept fallback, cards stay karpathy-only

Pointing quiron at a second real vault (`claude-devtalles`) surfaced three
concrete mismatches with what Fase 1-4 assumed, none of which needed a
schema change:

- **No topic-note frontmatter.** All 11 `02-Topics/*.md` files in
  claude-devtalles start directly with `# Title`, no YAML block. `seed.py`
  used to skip any topic note with `fm is None` — meaning it silently
  produced zero concepts there, not noisy ones. Fixed by treating a missing
  frontmatter block as `{}` rather than skipping the file; `unit` already
  fell back to `"unknown"` when tags are absent, so nothing else changed.

- **Concept granularity is the file, not a heading inside it.** Karpathy's
  topic notes hold several `##` concept headings each; devtalles' hold one
  concept per file (the H1 *is* the concept), using `##` only for
  organization ("Visto en", "Notas" — added to `headings.DENYLIST`). `seed()`
  now falls back to a single file-level concept (titled from the `# H1`
  line, or the file stem if there isn't one) whenever a topic note has zero
  surviving concept headings after the denylist. This never triggers for
  karpathy, whose notes always have real concept headings.

- **The live Anki deck doesn't generalize, on purpose, this phase.**
  Confirmed via AnkiConnect: a real `devtalles` deck exists (45 notes,
  yanki-synced) but sourced from multi-`## Q:`/`**A:**`-pair files
  (`04-Quiz-Bank/*.md`), not karpathy's one-file-per-card format — no
  `noteId` stored anywhere in the vault, no current `Ref:` line in source.
  Making cards addressable there means rethinking what `CardRef.path`
  identifies (a file today; would need to become a file+block reference),
  which is a real schema question, not a one-file fix. Deliberately out of
  scope: `04-Quiz-Bank/karpathy` became a `deck` parameter (default
  `"karpathy"`, threaded through `seed`/`doctor`/`audit`/the CLI) so the
  name itself isn't hardcoded, but devtalles simply has no matching deck
  folder to point it at yet — `--audit`/`--cards`/recall report empty there,
  honestly, rather than crash or fake a result.

## `quiron next`'s `coverage_gap` detail is empty, not a lesson count (Fase 4)

`Quiron.md`'s worked example for `quiron next` shows `sección 4 / MCP ✗ 28
lecciones sin tocar` — a per-lesson progress count. The schema has no field
for that (`Source` is just `kind` + `ref`, no lesson-level tracking), so
fabricating it would mean inventing data the system never collected.
`coverage_gap` candidates carry an empty `detail` instead — same posture as
Fase 2's `coverage_gap` tier-color divergence: the worked example is
illustrative, not a literal spec, and a real field beats a plausible-looking
number with no source.

## `self-explain: true` cards get a wider length budget and skip the enumeration check (Fase 3)

First run of `audit.py`'s `too_long` check (`MAX_WORDS=50`) against the real
deck flagged 18 cards; 13 of those were `self-explain: true` derivation
cards. `harvard-reviewer`'s own spec explicitly treats those differently:
"one tightly-coupled derivation where the steps only make sense together"
is right-sized, and the ~15-20s-aloud heuristic is stated for simple recall
cards, not dense derivations. `layer1_flags` now reads the `self-explain`
frontmatter flag and applies `MAX_WORDS_SELF_EXPLAIN=120` instead of `50`,
and skips the `enumeration` check entirely for those cards (numbered
derivation steps are the point, not a minimum-information violation). Real
candidate count on the karpathy deck dropped from 38 to 26 after the fix —
14 of those are the pre-existing dangling `Ref:` findings from Fase 1, so
the actual new layer-1/2 signal is closer to a dozen cards, not a quarter
of the deck.

## `coverage_gap` is yellow, always — never red (Fase 2)

`Quiron.md` v7 contradicts itself: the build order says "coverage reports
only needed-and-empty as red", but `today`'s tier table ("a concept with no
cards is never red") and the worked example (section 4 "MCP" renders 🟡) say
otherwise. The hard rule wins, not the build-order line — it's the one
repeated and explicitly justified (alarm fatigue). A `needed` concept with
no cards yet is a decision of yours not executed, not a system error. Red
stays reserved for: dangling `Ref:`, a `neglected` doubt (>30d), and — from
Fase 3 — suspect cards.

## AnkiConnect connects in Fase 2 only for "understand vs recall"

Of v7's 5 questions, #2 (high `factor` in Anki but
`understanding: encountered`) is the only one that needs Anki connected and
isn't explicitly assigned to another phase (`next`/`sources` are Fase 4 by
v7's own text; the lapses signal is Fase 3 by v7's own text). `recall.py`
implements it with a conservative threshold (`factor>=2500,
interval>=21`) and degrades to "no line at all" if Anki is closed —
`quiron today` never fails because of it.

## Concept = 02-Topics heading (not file, not tag)

The 136 card `Ref:` lines that point at topics point at headings, not whole
files. A file (~12 in karpathy) is too coarse for useful coverage; a card
tag (~40) stays blind to material that never became a card — exactly the
gap `quiron` exists to see. Heading (~230 in the real karpathy vault) is the
granularity the vault already points at mechanically.

## Separate repo (`C:\SANTIAGO\quiron`), not inside karpathy-path

`anki-metrics/` and `notifier/` live inside karpathy-path because they
belong to one vault. `quiron` doesn't — Fase 5 (devtalles) requires the same
code to run against two vaults via `--vault`, without one importing from the
other's repo.

## `ankiconnect.py` and `quizbank.py` are not rewritten

They already existed, working, in `karpathy-path/anki-metrics/`.
`ankiconnect.py` was copied verbatim to `quiron/src/quiron/ankiconnect.py`
(Fase 1 doesn't call it yet, but copying it with its test avoided Fase 2
starting with an open decision). `anki-metrics/` stays intact and working —
`/quiz-metrics` and its CI are untouched. Retiring it is a Fase 3 decision,
once `audit.py` supersedes it.

## The inbox classifier is a Claude Code skill, not an API call

Python (`capture.py`, `inbox.py`) stays fully deterministic: it scans,
validates, writes. Semantic classification ("which concept is this doubt
about?") lives in `/quiron-inbox`, a skill following the pattern already
established by `harvard-review` and `session-close` in this same vault. No
new API key, no model-versioning risk on Fase 1's critical path (that risk
is already documented in `Quiron.md` v7 and stays open for when the
classifier matters more).

## `Ref:` resolves exact → prefix → unresolved, never forced

136 card refs into topics: 22 exact, 101 prefix-only (the real heading has
an extra parenthetical or suffix), 13 with no possible match. A card with an
unresolvable `Ref:` is never assigned to any concept — it's reported by
`quiron doctor` as a real finding, not forced into an approximate match that
would lie about what the system knows.

## Heading rename = orphaned concept, not automatic rename

Renaming a `## heading` in a topic note generates a new slug and orphans the
old one (with its evidence intact). No rename detection was built in
Fase 1: `doctor` reports the orphan, and remapping is editing one line of
`knowledge.json`. An honest, visible limitation — preferable to a
similarity heuristic that would fail silently.

## Deferred — from Quiron.md v7, not from this phase

Recorded here so they aren't lost between phases:

- **Addressable sub-concepts.** `Evidence.scope` is free text today. Making
  it a first-class node is a real modeling upgrade — after the daily loop is
  a habit, not before.
- **Curriculum from prerequisites.** Transitive closure over
  `prerequisites[]`. Needs two populated vaults first (Fase 5).
- **Concepts shared across vaults.** Stable slugs letting evidence transfer.
  Justifies the Fase 7 template far better than "so a third party can
  install it."

All three are a consequence of the data, not features to build now.
