## Parameters For This Vault

- **Deck path:** `{{ deck_path }}`
- **Topic notes path:** `{{ topic_notes_path }}`
- **Re-sync command:** `{{ resync_command }}`

One read-only subagent (`quiz-reviewer`) does the actual reviewing. This skill
is the workflow around dispatching it, applying findings, and cleaning up
afterward. Never review inline as the main thread when the user asked for a
card or note quality pass. The second, adversarial pass is the point.

## When To Use Which Mode

- **Cards mode:** user just generated or wants to check quiz cards in `{{ deck_path }}`. Handles accuracy and Anki modularity/sizing in one dispatch.
- **Notes mode:** user wants a note in `{{ topic_notes_path }}` checked for rigor, completeness, or accuracy.
- **Both:** if the session produced a note and cards derived from it, one dispatch can review both. Say so explicitly in the prompt so the reviewer gives two clearly separated report sections.

## Workflow

1. Identify the target files. For cards mode, use the specific `.md` files just written or named by the user, not the whole deck by default. For notes mode, use the specific topic note file(s).
2. Dispatch `quiz-reviewer` with exact file paths. For cards mode, remind it to read the source note(s) referenced by the cards so it can cross-check accuracy. Run in the foreground; you need its report before acting.
3. Apply the fixes. The reviewer never edits files itself. Apply each recommended change with normal file edits. For card splits: create new files, trim/delete old ones per the report, and preserve tags and `self-explain` flags as specified. Do not silently skip a recommendation; if you disagree, say so to the user.
4. Re-sync if cards changed. Any time a card file is added, edited, or removed, run `{{ resync_command }}` so the live deck matches the vault. Skip if only a topic note changed, or if this vault has no re-sync command yet.
5. Report what the reviewer flagged and what changed.

## Why A Subagent Instead Of Reviewing Inline

The assistant that wrote the cards or notes is anchored on its own reasoning.
A fresh instance, primed specifically as a domain expert with no investment in
the original phrasing, catches mistakes better. Do not shortcut this by
reviewing it yourself quickly.
