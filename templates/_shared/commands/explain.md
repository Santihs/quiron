Explain out loud. Argument: a concept, a note path, or empty (= the last thing you explained in this conversation).

{% include "_shared/commands/voice-setup.md" %}

1. Pick the source: the argument's note under {{ topic_notes_path }}, or the latest explanation in this chat.
2. Write a spoken version: at most 6 short sentences, intuition first, then the one formula that matters said in words ("the mean of the squared errors"), then one concrete example with real numbers. No markdown, no symbols that sound wrong when read.
3. Show the spoken text on screen, then speak it with `qv-say{{ ' --es' if voice_lang == 'es' else '' }} --bg "..."` as the LAST tool call.
4. If while writing it you find a gap in the note, add a `> [!duda]` capture there instead of explaining it away.
