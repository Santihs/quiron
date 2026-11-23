Voice drill: you ask out loud, I answer out loud, you grade. Argument: a topic, `weak` (lowest-confidence concepts from `quiron today`), or empty (cards due or most recent topic).

{% include "_shared/commands/voice-setup.md" %}

One question per turn:
1. Pick one question from the deck ({{ deck_path }}) or write one from {{ topic_notes_path }} for the chosen topic. Show only the question on screen.
2. Ask it: `qv-say{{ ' --es' if voice_lang == 'es' else '' }} "<question>"` (foreground, so recording starts after you finish speaking).
3. Record my answer yourself: `qv-answer{{ ' --es' if voice_lang == 'es' else '' }} --target 60` with Bash (timeout 300000). Never ask me to run it.
4. Grade against the card answer / note: correct (1-5), explains why (1-5), connects to another concept (1-5); add pacing notes only if wpm, pauses or fillers stand out.
5. Speak feedback with `qv-say{{ ' --es' if voice_lang == 'es' else '' }} --bg` (max 3 sentences: what was right, the gap, the better phrasing) as the LAST tool call. On screen: score line + the better phrasing.
6. Record evidence the same way /quiz-me does for this vault (`quiron evidence --add`) when the question maps to a concept.
7. End the turn. `/drill` continues; `/drill again` repeats the question. When I say stop, give a 3-sentence summary and add it to today's daily log.
