Voice chat. I talk, you answer.

{% include "_shared/commands/voice-setup.md" %}

1. Record me right away: run `qv-answer{{ ' --es' if voice_lang == 'es' else '' }} --no-beep --silence 3` with Bash (timeout 300000). Say nothing before recording.
2. Treat the TRANSCRIPT as my message. Whisper can mishear domain terms; resolve them from this vault's notes ({{ topic_notes_path }}) before asking me.
3. Do what I asked, exactly as for a typed message (answer, explain, edit notes, run code).
4. Reply out loud with `qv-say{{ ' --es' if voice_lang == 'es' else '' }} --bg "..."` as the LAST tool call: it returns at once and keeps speaking while my screen shows your text. Spoken reply: plain sentences, math said in words, no code or paths. On screen: file paths, code, tables, at most 3 keywords.
5. End the turn. I run `/talk` again to say the next thing; `qv-say --stop` silences you.
