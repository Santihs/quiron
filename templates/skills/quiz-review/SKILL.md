---
name: quiz-review
description: Dispatch the quiz-reviewer subagent (a subject-matter + learning-science expert) to review freshly-written or existing quiz cards and/or topic notes, then apply its recommended fixes. Use this whenever the user asks to "review the cards", "revisa las preguntas/cards", "revisa mis apuntes/notas", says something like "lanza un profesor/harvard que revise" (legacy phrasing kept intentionally), or right after generating new quiz cards or a topic note when the session calls for a quality pass before committing. Covers BOTH quiz-card accuracy+Anki-sizing review and topic-note rigor review in one workflow — don't hand-roll a review prompt inline, use this skill so the review stays consistent across sessions.
---

# quiz-review

## Parameters for this vault
- **Deck path:** {{ deck_path }}
- **Topic notes path:** {{ topic_notes_path }}
- **Re-sync command:** {{ resync_command }}

One read-only subagent (`quiz-reviewer`, see `.claude/agents/quiz-reviewer.md`) does the actual reviewing — this skill is just the workflow around dispatching it, applying its findings, and cleaning up afterward. Never review inline yourself as the main thread; the whole point is a second, adversarial, expert pass that isn't anchored on the same reasoning that produced the material.

## When to use which mode

- **Cards mode**: user just generated (or wants to check) quiz cards in {{ deck_path }}. Handles accuracy AND Anki modularity/sizing in one dispatch — never split these into two separate agent calls, the reviewer does both passes itself (see its own instructions).
- **Notes mode**: user wants a note in {{ topic_notes_path }} checked for rigor, completeness, or accuracy.
- **Both**: if the session produced a note AND cards derived from it in the same sitting, one dispatch can review both — say so explicitly in the prompt so the agent gives you two clearly separated report sections instead of conflating them.

## Workflow

1. **Identify the target files.** For cards mode, that's the specific `.md` files just written or named by the user (not the whole deck — reviewing 100+ unrelated cards in one pass dilutes the report and burns context for no reason). For notes mode, the specific topic note file(s).

2. **Dispatch the subagent.** Use the Agent tool with `subagent_type: quiz-reviewer`. Give it the exact file paths (absolute), and for cards mode remind it to also read the `Ref:`'d source note(s) so it can cross-check accuracy — it will do this anyway per its instructions, but naming the source note paths up front saves it a search. Run in the foreground (`run_in_background: false`) — you need its report before you can act, this isn't a fire-and-forget task.

3. **Apply the fixes.** The agent never edits files itself — read its report and apply each recommended change with Edit/Write, same as you would from any code review. For card splits: create the new files, trim/delete the old ones per the report, keep tags and `self-explain` flags as the report specifies. Don't silently skip a recommendation — if you disagree with one, say so to the user rather than quietly dropping it.

4. **Re-sync if cards changed.** Any time a card file is added, edited, or removed, run {{ resync_command }} so the live deck matches the vault. Skip this step if only a topic note was reviewed, or if this vault has no re-sync command yet.

5. **Report back to the user.** Summarize what the reviewer flagged and what you changed — don't just say "done", give them the punch list (matches this vault's existing convention of terse-but-complete session summaries).

## Why a subagent instead of reviewing inline

The Claude instance that wrote the cards/note is anchored on its own reasoning — it's much better at catching its own mistakes when a fresh instance, primed specifically as a domain expert with no investment in the original phrasing, looks at the output cold. This is the same reason code review works better as a separate pass than self-review. Don't shortcut this by "reviewing it yourself real quick" — that defeats the purpose.
