`quiron cards --decide` works, but it is a blocking `input()` loop with no
context beyond a title. This skill is the same decision made with judgment: it
shows the actual note content per concept, lets the user answer naturally, and
persists through `quiron cards --set-policy`, the non-interactive counterpart
built for this. Read `C:\SANTIAGO\quiron\DECISIONS.md` for why both paths
exist side by side.

## Step 1 - List What Is Undecided

Run:

```bash
uv run --directory C:\SANTIAGO\quiron quiron cards --vault <this vault> --list-undecided --json
```

If empty, say so and stop. There is nothing to decide.

## Step 2 - Show Real Content, Not Just Titles

For each undecided concept, read its `notes_ref` file (the whole note if
short, the relevant section if long) so the user is deciding from the actual
material. Group concepts from the same note together when presenting.

Present each with a brief summary and ask: `needed` (the user wants a quiz
card for this), `declined` (they do not, and why), or skip (decide later).
Let the user answer in whatever form is natural.

## Step 3 - Apply

Build one `PolicyDecision` object per concept the user actually decided:

```json
{"slug": "...", "card_policy": "needed"}
{"slug": "...", "card_policy": "declined", "declined_reason": "..."}
```

Skipped concepts are omitted and stay `undecided`. Write the batch to a temp
JSON file and run:

```bash
uv run --directory C:\SANTIAGO\quiron quiron cards --vault <this vault> --set-policy <file>
```

## Step 4 - Report

Tell the user how many concepts were decided, list any skipped unknown slugs,
and say how many concepts are still undecided.
