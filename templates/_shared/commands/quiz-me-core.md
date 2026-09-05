This is the part of `/quiz-me` already identical across every vault that has
one. It is a floor, not a full command: each vault's real command may include
this core plus its own extensions such as card file format, live Anki deck,
`self-explain`/Quiron evidence wiring, topic interleaving, empty-bank fallback,
or save-new-question steps. Those extensions are vault-specific by design.

---

1. For each `Q:`/`A:` pair, parse the trailing `<!-- srs: ease=X interval=Y due=YYYY-MM-DD lapses=Z last_seen=W -->` comment. No `srs:` line means never seen and due today.
2. Generation-first, one question at a time: show only the question, with no hints or partial answer. Wait for the user's answer before revealing the stored answer.
3. Grade strictly after they answer: correct, partial, or incorrect. Partial means they get the gist but miss a specific detail or qualifier. Show the stored answer and a one-sentence explanation if they missed something.
4. Update scheduling for that question's `srs:` line right after grading, write it back into the file immediately: correct means `interval = round(interval * ease)`, `ease = min(3.0, ease + 0.1)`; partial means `interval = max(1, round(interval * 0.5))`, ease unchanged; incorrect means `interval = 1`, `ease = max(1.3, ease - 0.2)`, `lapses += 1`; then set `due = today + interval days`, `last_seen = today`.
5. At the end: give a score, flag topics that need review based on incorrect/partial answers, and show the next one or two upcoming `due` dates.
