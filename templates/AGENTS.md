# Vault OpenCode Instructions

Use `CLAUDE.md` as the canonical project memory for this vault. Follow its session protocol, learning rules, knowledge-persistence requirements, and vault-specific constraints unless the user explicitly overrides them.

When running in OpenCode, translate Claude Code references by intent:

- Slash commands refer to their `.opencode/commands/` equivalents when present.
- Quiron workflows live in `.opencode/skills/` and mirror the shared `.claude/skills/` workflows.
- The `quiz-reviewer` subagent lives in `.opencode/agents/quiz-reviewer.md`.
- Do not read or edit secrets, credentials, tokens, cache/session files, or private runtime data.

Quiron owns the shared assistant plumbing in `.claude/` and `.opencode/`. The vault owns its pedagogy in `CLAUDE.md`, notes, quiz-bank conventions, and session-close behavior.
