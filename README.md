# quiron

Modelo de conocimiento sobre vaults de Obsidian usados con Anki. Anki agenda
tarjetas; quiron modela conceptos, evidencia, dudas y cobertura. Ver
`C:\SANTIAGO\Quiron.md` (plan v7) para el diseño completo, y `DECISIONS.md`
para las decisiones tomadas al implementar Fase 1.

## Uso

```
uv sync
uv run quiron seed --vault ../karpathy-path          # siembra/refresca knowledge.json
uv run quiron capture-scan --vault ../karpathy-path   # callouts nuevos -> inbox.jsonl
uv run quiron today --vault ../karpathy-path          # el unico comando que hace falta recordar
uv run quiron doctor --vault ../karpathy-path --json  # hallazgos: refs colgantes, huerfanos, dudas sueltas
```

`seed` y `capture-scan` son idempotentes — correrlos de nuevo no duplica ni
sobrescribe lo que ya generaste a mano (`evidence`, `doubts`, `card_policy`).

## Estado — Fase 1

Captura por callouts, seeding desde `02-Topics/` + `04-Quiz-Bank/karpathy/` +
`06-Doubts-Resolved/`, y `quiron today`. No usa AnkiConnect todavía (Fase 2).
No modifica `progress.json` en ningún caso.

## Tests

```
uv run pytest
```
