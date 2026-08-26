# /quiz-me — shared core

This is the part of `/quiz-me` that's already identical across every vault that has one —
extracted here so it stays that way on purpose, not by coincidence. It is a **floor, not a full
command**: each vault's real `.claude/commands/quiz-me.md` includes this core plus its own
extensions (card file format, a live Anki-synced deck with `self-explain`/`quiron evidence`
wiring if that vault has one, topic interleaving, an empty-bank fallback, etc.) — those
extensions are vault-specific by design, not omissions. See `quiron/DECISIONS.md`'s Fase 6
entry for why this template stays partial instead of forcing a full merge.

---

1. For each `Q:`/`A:` pair, parse the trailing
   `<!-- srs: ease=X interval=Y due=YYYY-MM-DD lapses=Z last_seen=W -->`
   comment. No `srs:` line = never seen = `due=today`, top priority.

2. **Generation-first, one question at a time:**
   - Show ONLY the question. No hints, no partial answer.
   - Wait for the user's answer before revealing the stored answer.

3. **Grade strictly** after they answer — correct / partial / incorrect.
   Partial = gets the gist but misses a specific detail or qualifier; don't
   round up to correct. Show the stored answer and a one-sentence explanation
   if they missed something.

4. **Update scheduling** for that question's `srs:` line right after grading
   (SM-2 simplified), write it back into the file immediately:
   - Correct → `interval = round(interval * ease)`, `ease = min(3.0, ease + 0.1)`
   - Partial → `interval = max(1, round(interval * 0.5))`, ease unchanged
   - Incorrect → `interval = 1`, `ease = max(1.3, ease - 0.2)`, `lapses += 1`
   - `due = today + interval days`, `last_seen = today`

5. At the end: give a score, flag topics that need review (based on
   incorrect/partial answers), and show the next 1-2 upcoming `due` dates.
