# Decisions

## Concepto = heading de 02-Topics (no archivo, no tag)

Los 136 `Ref:` de tarjetas que apuntan a topics apuntan a headings, no a archivos
completos. Un archivo (~12 en karpathy) es demasiado grueso para cobertura útil;
un tag de tarjeta (~40) queda ciego al material que nunca se convirtió en
tarjeta — justo el hueco que `quiron` existe para ver. Heading (~230 en
karpathy real) es la granularidad a la que el vault ya apunta mecánicamente.

## Repo separado (`C:\SANTIAGO\quiron`), no dentro de karpathy-path

`anki-metrics/` y `notifier/` viven dentro de karpathy-path porque son
de un solo vault. `quiron` no lo es — Fase 5 (devtalles) exige que el mismo
código corra contra dos vaults con `--vault` como argumento, sin que uno
importe del repo del otro.

## `ankiconnect.py` y `quizbank.py` no se reescriben

Ya existían, funcionando, en `karpathy-path/anki-metrics/`. `ankiconnect.py`
se copió verbatim a `quiron/src/quiron/ankiconnect.py` (Fase 1 no lo llama
todavía, pero copiarlo con su test evita que Fase 2 arranque con una decisión
pendiente). `anki-metrics/` se queda intacto y funcionando — `/quiz-metrics`
y su CI no se tocan. Retirarlo es decisión de Fase 3, cuando `audit.py` lo
supere.

## El clasificador del inbox es un skill de Claude Code, no una llamada a la API

Python (`capture.py`, `inbox.py`) queda 100% determinístico: escanea, valida,
escribe. La clasificación semántica ("¿de qué concepto es esta duda?") vive en
`/quiron-inbox`, un skill que sigue el patrón ya establecido por
`harvard-review` y `session-close` en este mismo vault. Sin API key nueva, sin
versionado de modelo en el camino crítico de Fase 1 (ese riesgo ya está
documentado en Quiron.md v7 y sigue abierto para cuando el clasificador
importe más).

## `Ref:` se resuelve exacto → prefijo → sin resolver, nunca se fuerza

136 refs de tarjeta a topics: 22 exactos, 101 solo prefijo (el heading real
tiene un paréntesis o sufijo extra), 13 sin match posible. Una tarjeta con
`Ref:` irresoluble no se asigna a ningún concepto — queda reportada por
`quiron doctor` como hallazgo real, no forzada a un match aproximado que
mentiría sobre qué sabe el sistema.

## Rename de heading = concepto huérfano, no rename automático

Renombrar un `## heading` en una nota de tema genera un slug nuevo y dejar
huérfano al viejo (con su evidencia intacta). No se construyó detección de
renames en Fase 1: `doctor` reporta el huérfano, y remapear es editar una
línea de `knowledge.json`. Limitación honesta y visible, preferible a
heurísticas de similitud que fallarían en silencio.

## Diferido — de Quiron.md v7, no de esta fase

Recordado acá para que no se pierda entre fases:

- **Sub-conceptos direccionables.** `Evidence.scope` es texto libre hoy.
  Hacerlo un nodo de primera clase es upgrade real de modelado — después de
  que el loop diario sea hábito, no antes.
- **Currículum desde prerequisites.** Clausura transitiva sobre
  `prerequisites[]`. Necesita dos vaults poblados primero (Fase 5).
- **Conceptos compartidos entre vaults.** Slugs estables permitiendo
  transferir evidencia. Justifica el template de Fase 7 mejor que "para que
  lo instale un tercero".

Las tres son consecuencia de los datos, no features a construir ahora.
