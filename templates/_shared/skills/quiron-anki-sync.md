`yanki` is a headless CLI (`npx yanki sync <dir>`), not an Obsidian-only
plugin. AnkiConnect (`http://127.0.0.1:8765`, Anki Desktop must be running) is
used directly for everything read-only or destructive that `yanki` itself does
not cover. Read `C:\SANTIAGO\quiron\DECISIONS.md` for why this exists and its
boundaries: Quiron's own Python stays read-only against Anki; this assistant
workflow is what may write/delete, with explicit user control.

This skill has two independent halves. Run whichever the trigger calls for;
they do not need to run together.

## Half A - Push New Or Changed Cards

1. Find the vault's existing sync-group namespace. Pick any already-synced card (one with a `noteId:` in frontmatter, or any note in the target Anki deck) and read its `YankiNamespace` field via AnkiConnect (`notesInfo`). It looks like `Yanki Obsidian - Vault ID <hex>`; pass everything after the leading `Yanki ` to `--namespace`. If the deck has zero notes yet, ask the user. Do not guess or silently fall back to yanki's default `Yanki` namespace.
2. Scope the sync directory narrowly, usually the specific subfolder with new/edited cards, e.g. `04-Quiz-Bank/<deck>/`. Yanki can delete Anki notes whose local file disappeared from the directory it is pointed at, so limit the blast radius.
3. Dry run first, always:

```bash
npx --yes yanki sync "<dir>" --namespace "<namespace>" --dry-run --verbose
```

Read the plan. Confirm it is only `Created`/`Updated` for expected files and
has no unexpected `Deleted` entries. If anything looks wrong, stop and ask.

4. Run for real with the same command minus `--dry-run`. Yanki writes `noteId:` back into each synced file's frontmatter itself; do not hand-edit it.
5. Report notes created/updated and the deck's new total count.

## Half B - Find Orphaned Anki Notes

Report only unless the user explicitly approves deletion for the specific
batch in this conversation.

1. Pull every note in the deck via AnkiConnect (`findNotes` query `deck:<name>`, then `notesInfo`), strip the Yanki-generated HTML comment and tags from the `Front` field.
2. Pull every current source: `## Q:` blocks from multi-card quiz files, and `Ref:`-line questions from one-file-per-card files. Strip markdown punctuation from both sides before comparing.
3. Anything in Anki with no normalized match in current vault sources is an orphan candidate. Present the full list grouped by topic, with why each has no source anymore.
4. Never call `deleteNotes` without explicit confirmation for this exact candidate batch.
5. After deleting, report the before/after note count for the deck.
