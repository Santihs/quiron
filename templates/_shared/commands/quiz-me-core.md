This is the part of `/quiz-me` already identical across every vault that has
one. It is a floor, not a full command: each vault's real command may include
this core plus its own extensions such as card file format, live Anki deck,
`self-explain`/Quiron evidence wiring, topic interleaving, empty-bank fallback,
or save-new-question steps. Those extensions are vault-specific by design.

---

1. Treat Anki as the sole owner of scheduling. Do not parse, calculate, or write scheduler fields such as `ease`, `interval`, `due`, `lapses`, or `last_seen` in card files. A missing scheduling record is not a quiron due signal.
2. Generation-first, one question at a time: show only the question, with no hints or partial answer. Wait for the user's answer before revealing the stored answer.
3. Grade strictly after they answer: correct, partial, or incorrect. Partial means they get the gist but miss a specific detail or qualifier. Show the stored answer and a one-sentence explanation if they missed something.
4. If a vault-specific extension records Quiron evidence, append a dated record with a real `ref`. Evidence recording is separate from scheduling and must not write back to Anki-owned fields.
5. At the end: give a score, flag topics that need review based on incorrect/partial answers, and direct the user to Anki for its own due-card schedule.
