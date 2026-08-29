---
name: quiron-anki-sync
description: Push new/changed quiz-bank cards to Anki via the headless `yanki` CLI, and find (never auto-delete) Anki notes orphaned by content that moved or was rewritten in the vault. Trigger on "/quiron-anki-sync", "sincroniza con anki", "sube las cards a anki", "hay cards huérfanas en anki", or after `quiron-cards-decide`/`quiron seed` leaves new card files unsynced.
---

# quiron-anki-sync

`yanki` is a headless npm CLI (`npx yanki sync <dir>`), not an
Obsidian-only plugin — no need to open Obsidian to run it. AnkiConnect
(`http://127.0.0.1:8765`, Anki Desktop must be running) is used directly for
everything read-only or destructive that `yanki` itself doesn't cover.
Read `C:\SANTIAGO\quiron\DECISIONS.md` for why this exists and its
boundaries — quiron's own Python stays read-only against Anki; this skill,
not `quiron`, is what's allowed to write/delete.

This skill has two independent halves. Run whichever the trigger calls for
— they don't need to run together.

## Half A — Push new/changed cards

1. Find the vault's existing sync-group namespace: pick any already-synced
   card (one with a `noteId:` in its frontmatter, or any note in the target
   Anki deck) and read its `YankiNamespace` field via AnkiConnect
   (`notesInfo`). It looks like `Yanki Obsidian - Vault ID <hex>` — the value
   to pass to `--namespace` is everything after the leading `"Yanki "`
   (i.e. `Obsidian - Vault ID <hex>`). If the deck has zero notes yet, ask
   the user — don't guess a namespace, and don't fall back to yanki's
   default `"Yanki"` silently, since that forks a second sync group.

2. Scope the sync directory as narrowly as the situation allows — the
   specific subfolder with new/edited cards (e.g.
   `04-Quiz-Bank/<deck>/`), not the whole vault, unless the whole vault's
   quiz bank genuinely needs re-syncing. yanki deletes Anki notes whose
   local file disappeared from *the directory it's pointed at* — scoping
   tightly limits the blast radius of a mistake.

3. Dry run first, always:
   ```
   cd <vault root>
   npx --yes yanki sync "<dir>" --namespace "<namespace from step 1>" --dry-run --verbose
   ```
   Read the plan. Confirm it's only `Created`/`Updated` for the files you
   expect — no unexpected `Deleted` entries. If anything looks wrong, stop
   and ask rather than proceeding.

4. Run for real (same command minus `--dry-run`). yanki writes `noteId:`
   back into each synced file's frontmatter itself — don't hand-edit it.

5. Report: notes created/updated, and the deck's new total count.

## Half B — Find orphaned Anki notes (report only, never auto-delete)

Anki notes don't disappear on their own when a vault's `## Q:` block or
one-file-per-card source is rewritten elsewhere — yanki only pushes, it
doesn't reconcile a deletion that happens outside the directory it's
watching. This drifts silently over time.

1. Pull every note in the deck via AnkiConnect (`findNotes` query
   `deck:<name>`, then `notesInfo`), strip the Yanki-generated HTML comment
   and tags from the `Front` field.

2. Pull every current source: `## Q:` blocks from the vault's multi-card
   quiz files, and `Ref:`-line questions from one-file-per-card files. Strip
   markdown punctuation (backticks, `*`, `_`) from both sides before
   comparing — literal substring matching on raw markdown produces false
   orphans (a card whose vault question has `` `Shift+Tab` `` won't
   substring-match Anki's plain-text `Shift+Tab`).

3. Anything in Anki with no normalized match in current vault sources is an
   orphan candidate. Present the full list grouped by topic, with *why*
   each one has no source anymore (rewritten into prose elsewhere, file
   deleted, wording changed enough to fork) — not just note IDs.

4. Never call `deleteNotes` without the user explicitly confirming the
   specific batch in this conversation, even if they asked for cleanup in
   general terms — Claude Code's own auto-mode classifier already blocks
   `deleteNotes` without an explicit approval, so plan for that prompt
   rather than working around it.

5. After deleting, report the before/after note count for the deck.
