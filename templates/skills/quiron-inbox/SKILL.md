---
name: quiron-inbox
description: Classify unprocessed captures in quiron's inbox (00-Meta/inbox.jsonl) — duda/concepto/aplicado callouts written during study — and apply them to knowledge.json. Trigger on "/quiron-inbox", "process the inbox", "procesa el inbox", or when quiron today reports unprocessed captures.
---

# quiron-inbox

quiron's Python side is deterministic on purpose: it scrapes callouts, it
validates, it writes. Classifying a raw capture against the concept model —
"which concept is this duda about?", "what source does this concepto belong
to?" — needs judgment, so it lives here instead of in a hand-rolled prompt or
an API call. Read `C:\SANTIAGO\quiron\DECISIONS.md` if you want the reasoning
behind that split.

## Step 1 — Load the unprocessed captures

Run `uv run --directory C:\SANTIAGO\quiron quiron capture-scan --vault <this vault>`
first, so anything written since the last run is in the inbox. Then read
`00-Meta/inbox.jsonl` and keep only entries where `"processed": false`.

If there are none, say so and stop — do not invent work.

## Step 2 — Load the concept model

Read `00-Meta/knowledge.json`. You need the `slug`, `title`, and `sources` of
every concept to propose a target.

## Step 3 — Propose a classification per capture

For each unprocessed entry:

- **`duda`** → propose the `target_slug` of the concept it's most likely
  about, matching the capture text against concept titles and, if the source
  log's `topics_touched` frontmatter helps, that too. If nothing matches
  confidently, propose `target_slug: null` — don't force a bad match.
- **`concepto`** → these don't create new concepts in Fase 1 (concepts come
  from `02-Topics/` headings via `quiron seed`). Just note which existing
  concept, if any, the capture seems to relate to — informational only.
- **`aplicado`** → propose the `target_slug` plus a `ref` (a real path — the
  script, note, or exercise file the capture mentions) and a `scope` if the
  text implies a partial application.

Present the full batch to the user as a numbered list, one line per capture,
with your proposed classification already filled in — they should be able to
approve most of it by just confirming, not by typing everything out. Default
is accept; ask which ones (if any) need editing or should be skipped.

## Step 4 — Apply

For each capture the user approved (as proposed, or edited), write one
proposal object and hand the batch to
`uv run --directory C:\SANTIAGO\quiron quiron inbox --apply <proposals.json>`
via a temp JSON file, or apply the same effect directly through the
`quiron.inbox.apply_proposals` function if running in a context where that's
simpler. Each proposal needs: `capture_id`, `kind`, `target_slug` (or `null`),
`text` (the doubt's question, for `duda`), `ref` and `at` (today's date, for
`aplicado`), and optional `scope`.

Skipped or edited-to-skip captures stay `processed: false` — that's correct,
not a failure. The inbox is allowed to stay dirty forever; never treat an
unprocessed leftover as something to clean up by force.

## Step 5 — Report

Tell the user what got applied (N doubts opened, N applied-evidence entries
added) and what's still sitting unprocessed, if anything. No need to reach
zero.
