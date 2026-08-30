---
name: quiron-cards-decide
description: Walk concepts with no retention decision yet (card_policy=undecided) conversationally, showing real note content instead of just a title, and record needed/declined decisions. Trigger on "/quiron-cards-decide", "decidí las cards", "revisemos qué necesita tarjeta", or when quiron today/next reports several undecided concepts.
---

# quiron-cards-decide

`quiron cards --decide` (the CLI's own interactive walker) works, but it's a
blocking `input()` loop with no context beyond a title — only useful from a
real terminal. This skill is the same decision, made with judgment instead
of a bare keystroke: it shows you the actual note content per concept, lets
you answer in natural language (one at a time or in bulk), then persists via
`quiron cards --set-policy`, the non-interactive counterpart built for
exactly this. Read `C:\SANTIAGO\quiron\DECISIONS.md` for why both paths
exist side by side.

## Step 1 — List what's undecided

Run:
```
uv run --directory C:\SANTIAGO\quiron quiron cards --vault <this vault> --list-undecided --json
```
If empty, say so and stop — nothing to decide.

## Step 2 — Show real content, not just titles

For each undecided concept, read its `notes_ref` file (the whole note if
short, the relevant section if long) so the user is deciding from the actual
material, not a bare title. Group concepts from the same note together when
presenting — easier to decide in one pass than context-switching per line.

Present each with a brief summary of what the concept actually covers, and
ask: needed (you want a quiz card for this), declined (you don't, and why),
or skip (decide later — leaving it undecided is fine). Let the user answer
in whatever form is natural — "los primeros 3 sí, el resto no" is a valid
answer, don't force one-line-per-concept replies.

## Step 3 — Apply

Build one `PolicyDecision` object per concept the user actually decided
(skipped ones are simply omitted — they stay `undecided`, that's correct,
not an error):
```json
{"slug": "...", "card_policy": "needed"}
{"slug": "...", "card_policy": "declined", "declined_reason": "..."}
```
Write the batch to a temp JSON file and run:
```
uv run --directory C:\SANTIAGO\quiron quiron cards --vault <this vault> --set-policy <file>
```

## Step 4 — Report

Tell the user how many were decided, list any `skipped (unknown slug)` the
command reports (shouldn't happen unless knowledge.json changed mid-session),
and say how many concepts are still undecided. No need to reach zero — same
posture as the inbox: it's fine to leave the rest for next time.
