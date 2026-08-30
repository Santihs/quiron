---
name: quiron-cards-audit
description: Run quiron's card-quality audit (layers 1 and 2 — static checks plus the Anki lapses cross-signal), dispatch quiz-reviewer only on the cards it flags, apply the fixes, and persist the reviewer's verdicts back into knowledge.json. Trigger on "/quiron-cards-audit", "audit the cards", "audita las tarjetas", "check card quality", or when quiron today reports suspect cards.
---

# quiron-cards-audit

`quiron cards --audit` is deterministic and read-only: it never edits a card
and never writes to `knowledge.json`. It only decides *which* cards deserve
a `quiz-reviewer` pass and *why* — the actual judgment still comes from
that agent, unchanged. This skill is the workflow around that split. See
`C:\SANTIAGO\quiron\DECISIONS.md` if you want the reasoning.

## Step 1 — Run the audit

```
uv run --directory C:\SANTIAGO\quiron quiron cards --vault <this vault> --audit --json
```

If `candidates` is empty, say so and stop — do not invent work. Note
`informational` separately: those are cards you're probably failing because
you don't know the material yet, not because the card is bad. They never go
to the reviewer.

## Step 2 — Dispatch, apply, re-sync (via quiz-review)

Follow `quiz-review`'s Steps 2-4 exactly, using the `card_path` list from
`candidates` as the target files instead of asking the user which files to
review:

1. Dispatch `quiz-reviewer` (Agent tool, `subagent_type: quiz-reviewer`) on those exact paths, foreground.
2. Apply every recommended fix with Edit/Write.
3. Run this vault's re-sync command (see `quiz-review`'s parameters) if any card file changed.

## Step 3 — Record the verdicts

For each card the reviewer looked at, build one `ReviewProposal`:

```json
{
  "card_path": "04-Quiz-Bank/karpathy/x.md",
  "quality": "ok",
  "reviewer_verdict": "fine",
  "lapses_at_review": 7,
  "flagged_reason": null
}
```

- `quality` — `"ok"` if the reviewer said fine, `"flagged"` if it
  recommended a fix that couldn't be fully resolved this pass, `"retired"`
  if the card was deleted or merged into another.
- `reviewer_verdict` — the reviewer's own words (e.g. `"split into 2"`,
  `"fine"`, `"revised wording"`).
- `lapses_at_review` — copy this straight from the `--audit` output's
  `lapses` field for that card. Do not re-fetch Anki. The whole point of
  this field is a snapshot of the card's failure count right before the
  fix, so a later `--audit` can tell whether the verdict actually worked.

Write the full list to a temp JSON file, then:

```
uv run --directory C:\SANTIAGO\quiron quiron cards --vault <this vault> --record-review <file>
```

A `card_path` that doesn't match any `CardRef` is reported as skipped, not
silently dropped — check the output for that before reporting done.

## Step 4 — Report

Summarize what was flagged, what changed, and what got recorded — same
terse-but-complete convention as `quiz-review`.
