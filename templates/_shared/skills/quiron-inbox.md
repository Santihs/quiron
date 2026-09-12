Quiron's Python side is deterministic on purpose: it scrapes callouts, it
validates, it writes. Classifying a raw capture against the concept model -
"which concept is this duda about?", "what source does this concepto belong
to?" - needs judgment, so it lives here instead of in a hand-rolled prompt or
an API call. Read `C:\SANTIAGO\quiron\DECISIONS.md` if you want the reasoning
behind that split.

## Step 1 - Load The Unprocessed Captures

Run `uv run --directory C:\SANTIAGO\quiron quiron capture-scan --vault <this vault>`
first, so anything written since the last run is in the inbox. Then read
`00-Meta/inbox.jsonl` and keep only entries where `"processed": false`.

If there are none, say so and stop. Do not invent work.

## Step 2 - Load The Concept Model

Read `00-Meta/knowledge.json`. You need the `slug`, `title`, and `sources` of
every concept to propose a target.

## Step 3 - Propose A Classification Per Capture

For each unprocessed entry:

- `duda`: propose the `target_slug` of the concept it is most likely about, matching the capture text against concept titles and, if the source log's `topics_touched` frontmatter helps, that too. If nothing matches confidently, propose `target_slug: null`.
- `concepto`: these do not create new concepts in Fase 1. Concepts come from `02-Topics/` headings via `quiron seed`. Note which existing concept, if any, the capture seems to relate to.
- `aplicado`: propose the `target_slug` plus a `ref` (a real path: the script, note, or exercise file the capture mentions) and a `scope` if the text implies a partial application.

Present the full batch to the user as a numbered list with your proposed
classification already filled in. Default is accept; ask which ones need
editing or should be skipped.

## Step 4 - Apply

For each capture the user approved, write one proposal object and hand the
batch to:

```bash
uv run --directory C:\SANTIAGO\quiron quiron inbox --vault <this vault> --apply <proposals.json>
```

Each proposal needs: `capture_id`, `kind`, `target_slug` (or `null`), `text`
(the doubt's question, for `duda`), `ref` and `at` (today's date, for
`aplicado`), and optional `scope`.

Skipped or edited-to-skip captures stay `processed: false`. That is correct,
not a failure. The inbox can stay dirty forever; never force it to zero.

## Step 5 - Report

Tell the user what got applied and what is still unprocessed, if anything.
