`quiron cards --audit` is deterministic and read-only: it never edits a card
and never writes to `knowledge.json`. It only decides which cards deserve a
`quiz-reviewer` pass and why. The actual judgment still comes from that
reviewer. This skill is the workflow around that split. See
`C:\SANTIAGO\quiron\DECISIONS.md` if you want the reasoning.

## Step 1 - Run The Audit

```bash
uv run --directory C:\SANTIAGO\quiron quiron cards --vault <this vault> --audit --json
```

If `candidates` is empty, say so and stop. Note `informational` separately:
those are cards the user may be failing because they do not know the material
yet, not because the card is bad. They do not go to the reviewer.

## Step 2 - Dispatch, Apply, Re-Sync

Follow `quiz-review`'s dispatch/apply/re-sync workflow using the `card_path`
list from `candidates` as the target files instead of asking the user which
files to review:

1. Dispatch `quiz-reviewer` on those exact paths in the foreground.
2. Apply every recommended fix with normal file edits.
3. Run this vault's re-sync command if any card file changed and the vault has one.

## Step 3 - Record The Verdicts

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

- `quality`: `"ok"` if the reviewer said fine, `"flagged"` if it recommended a fix that could not be fully resolved this pass, `"retired"` if the card was deleted or merged into another.
- `reviewer_verdict`: the reviewer's own words, e.g. `"split into 2"`, `"fine"`, or `"revised wording"`.
- `lapses_at_review`: copy this from the `--audit` output's `lapses` field for that card. Do not re-fetch Anki.

Write the full list to a temp JSON file, then run:

```bash
uv run --directory C:\SANTIAGO\quiron quiron cards --vault <this vault> --record-review <file>
```

A `card_path` that does not match any `CardRef` is reported as skipped, not
silently dropped. Check the output before reporting done.

## Step 4 - Report

Summarize what was flagged, what changed, and what got recorded.
