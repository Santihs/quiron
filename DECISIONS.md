# Decisions

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
