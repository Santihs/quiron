# `quiron` — a knowledge model for learning vaults

> **Consumption ≠ Learning.**
> The system does not measure how much material you finished. It models what part of that material turned into knowledge you can use.

> **Document status:** v7 design and historical roadmap. Written 2026-08-23.
> v6 was the pivot (stop competing with Anki's scheduler; model concepts instead). v7 is the correction that makes v6 survivable: v6 had a good **data model** and no **interaction model** — it described a system that starts after the knowledge already exists, with four commands and no reason to open any of them. v7 adds capture, a single entry point, and turns `understanding` from a stored claim into a derived reading of recorded evidence.
>
> **Repository status:** package `0.1.0`, persisted model schema `v2` (with an explicit v1 upgrade path), and implementation through Fase 7 plus the hardening pass. The phase descriptions and examples below preserve the original design intent; behavior that is not live is listed under **Pending gaps**.

---

## Current implementation status

The current repository exposes these command surfaces:

- `capture-scan` discovers callouts and merges them into `00-Meta/inbox.jsonl`.
- `inbox --apply FILE` applies already-classified proposals; classification stays in the `/quiron-inbox` skill.
- `today` scans new callouts, renders vault findings, runs the card audit, and performs an optional Anki recall contradiction check.
- `cards --list-gaps`, `cards --decide`, `cards --list-undecided`, `cards --audit`, `cards --record-review`, and `cards --set-policy FILE` cover card-policy and card-quality workflows.
- `evidence --add` records evidence explicitly, while `next` and `sources` query the persisted model.
- `doctor` reports seed-resolution findings, and `migrate` scaffolds the shared Claude Code/OpenCode plumbing.

Migrated vault-specific `/quiz-me` commands now receive a managed handoff for `explained` evidence. Automatic conversion of `aplicado` captures into `applied` evidence remains a pending gap, not a current guarantee.

## What quiron is

**Anki models a card:** when should you see this again so you don't forget it.
**Quiron models a concept:** what did you actually do with it, what's unresolved, what's missing, what depends on what.

Anki has no idea a concept called "eigenvectores" exists — it has six loose cards. It doesn't know you've had an open question about determinants for 31 days, that this concept gates three others, or that you can recite the definition and have never once explained it.

Quiron holds the *material*, the *notes*, the *cards*, and the *open questions* as one connected model. Anki keeps scheduling. Untouched.

### The loop

```
        ESTUDIAR
           │
           ▼
       CAPTURAR            callouts en el daily log — no hay comando
           │
           ▼
       PROCESAR            inbox propone, vos aprobás en lote
           │
           ▼
    quiron today           diagnostica: rojo / amarillo / blanco
           │
           ▼
        DECIDIR            qué entender · qué resolver · qué retener
           │
      ┌────┴────┐
      ▼         ▼
 explicar/    Anki  ──────►  FSRS, reviews diarias
  aplicar       │
      │         │
      └────┬────┘
           ▼
       EVIDENCIA  ─────────► vuelve al modelo
```

Four jobs, not five: **capturar → diagnosticar → decidir → retener.** *Organizar* is not a job — the user should never feel they are doing it. Quiron organizes as a consequence of studying.

---

## The line that is never crossed

Not a promise — a structural rule:

> **If Anki is authoritative for a piece of data, that data is never stored in the model.**

No `interval`, `ease`, `factor`, `due`, `reps`, `lapses` — ever persisted. Read from AnkiConnect at query time and discarded. If it's in the Pydantic model, Anki doesn't know or care about it. If Anki owns it, it isn't in the model.

Makes "we don't replace FSRS" verifiable by inspection rather than by intention.

---

## Capture — the part that decides whether the system survives

v6 began after the knowledge already existed. It never said how it gets there. That is the difference between a tool you use and a tool you designed.

**The cheapest capture is the one that uses the app already open.** You are in Obsidian, mid-lesson. If capturing means leaving for a terminal, you don't capture.

So: **there is no `quiron capture` command.** You write callouts the way you'd write any note. They render natively in Obsidian. Quiron discovers them.

```markdown
> [!duda] no entiendo por qué Av=λv conserva la dirección

> [!concepto] descomposición espectral — conecta con eigenvectores

> [!aplicado] eigenvectores — implementé PCA a mano en scripts/pca.py
```

Three callout types, scraped from `03-Daily-Logs/`. `duda` opens a `Doubt`. `concepto` proposes a `Concept` or attaches to one. `aplicado` is the intended source of `applied` evidence, but the current workflow still requires a classified proposal and the inbox apply step.

### Capture and processing are different cognitive modes

Capture asks **nothing**. Not which concept, not which source, not what type. `capture-scan` appends callouts to `00-Meta/inbox.jsonl` unclassified. Asking a question at capture time is exactly what breaks a study session. `today` now runs that scan automatically before rendering, while `capture-scan` remains available as an explicit operation.

Processing happens when you choose `/quiron-inbox`:

```
[1/4] duda · "por qué Av=λv conserva la dirección"
      → concepto: eigenvectores            (existe, 6 tarjetas)
      → fuente:   Axler 5.A                (del daily log 2026-08-23)
      [enter] aceptar · [e] editar · [s] saltear
```

The classifier proposes **everything filled in**; you approve in bulk. Default is accept.
After approval, the skill applies the proposal file with:

```
$ quiron inbox --vault <vault> --apply <proposals.json>
```

**And the inbox is allowed to stay dirty forever.** An unprocessed capture is still searchable text in your daily log — exactly where you wrote it, losing nothing. An inbox that demands zero is an inbox that generates guilt, and then you stop opening it. Never counted as red in `today`.

> Design note: capture friction and processing friction are the same budget. v6 had no capture; the naive fix moves all the friction to processing and nets zero. Bulk-approve with defaults plus a dirty-tolerant inbox is what actually spends less.

---

## The knowledge model

`src/quiron/schema.py` — one Pydantic model, single source of truth. Lives in a **new** file, `00-Meta/knowledge.json`. It does not modify `progress.json`, so nothing existing breaks (notably `notifier/remind.py`, which reads `progress["meta"]` with silent `.get()` fallbacks and would fail invisibly on a schema change).

```python
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import date

LADDER = ["unseen", "encountered", "explained", "applied"]

class Source(BaseModel):
    kind: Literal["book", "course", "paper", "video"]
    ref: str                        # "Axler 5.A" / "devtalles lección 47"

class Evidence(BaseModel):
    kind: Literal["encountered", "explained", "applied"]
    at: date
    ref: str                        # obligatorio POR CONSTRUCCIÓN
    scope: Optional[str] = None     # "solo la interpretación geométrica"

class Doubt(BaseModel):
    question: str
    raised_at: date
    status: Literal["open", "resolved"]
    resolved_at: Optional[date] = None
    resolution_ref: Optional[str] = None    # → 06-Doubts-Resolved/xxx.md
    resolved_by: Optional[str] = None       # "segunda fuente" / "peer" / "solo"

class CardRef(BaseModel):
    path: str                               # 04-Quiz-Bank/<deck>/xxx.md
    quality: Literal["unreviewed", "ok", "flagged", "retired"] = "unreviewed"
    flagged_reason: Optional[str] = None
    reviewed_at: Optional[date] = None
    reviewer_verdict: Optional[str] = None  # "split into 2" / "fine"
    lapses_at_review: Optional[int] = None  # cierra el loop — ver Card quality

class Concept(BaseModel):
    slug: str
    title: str
    unit: str
    sources: list[Source] = []
    prerequisites: list[str] = []           # slugs de otros conceptos
    evidence: list[Evidence] = []
    doubts: list[Doubt] = []
    card_refs: list[CardRef] = []
    notes_ref: Optional[str] = None         # → 02-Topics/xxx.md

    # ¿esto merece memorizarse? — decisión explícita, no ausencia
    card_policy: Literal["undecided", "needed", "declined"] = "undecided"
    declined_reason: Optional[str] = None   # "es referencia, se busca no se memoriza"

    @property
    def understanding(self) -> str:
        """Derivado, nunca guardado."""
        return max((e.kind for e in self.evidence),
                   key=LADDER.index, default="unseen")

class Knowledge(BaseModel):
    schema_version: int = 1
    concepts: list[Concept] = []
```

### Why `understanding` is derived and not a field

v6 stored `understanding: "explained"` and forced an `explanation_ref` alongside it. That was better than nothing, and still wrong: a **stored claim about your own knowledge** is the hand-typed `confidence: 3` problem wearing a validator.

v7 stores **events, and derives the interpretation.**

```
2026-08-20  encountered  ref: 03-Daily-Logs/2026-08-20.md
2026-08-22  explained    ref: 05-Explanations/eigenvectores.md   scope: "geométrica"
2026-08-25  applied      ref: scripts/pca.py
                                                    → understanding = applied
```

Four problems close at once:

- **Rigidity** — `scope` records partial understanding: *the geometric reading, not the algebraic one.* The concept stops being one giant boolean.
- **Non-linearity** — real learning isn't a monotone climb. You can apply a pattern by copying it before you can explain it. Evidence accumulates in any order; the ladder is read off it, not marched up.
- **The validator disappears** — you cannot have evidence without a `ref`. Structural, not a rule someone enforces.
- **History for free** — the list *is* the trajectory. `history.jsonl` no longer needs to track this transition at all.

And the framing becomes honest on its own: **`evidence` is what you did, not what you know.** `understanding` is a reading of it — and a reading you can change later without migrating a single record.

| level | meaning | who can tell |
|---|---|---|
| `unseen` | in the material, untouched | quiron |
| `encountered` | read it / watched it | quiron |
| `explained` | explained it in your own words, unaided | quiron (the self-explain gate) |
| `applied` | used it to solve something real | quiron |
| *recalling a card* | — | **Anki, and only Anki** |

You can hold `factor: 2300` in Anki (perfect recall) and sit at `encountered` with two open doubts. That contradiction is real information, and today it is lost entirely because the two halves live in systems that never speak.

### `applied` needs a mechanism or it stays empty forever

Look at where each rung comes from: `encountered` ← callouts and daily logs. `explained` ← the shared `/quiz-me` handoff, which this design redefines: it **produces** evidence (makes you explain, saves the explanation, writes the ref) rather than competing with Anki at presenting cards. `quiron migrate` inserts or refreshes that handoff while preserving each vault's quiz extension.

`applied` had **no producer** in v6. And it is both the top of the ladder and the input to the most interesting query in the system (source yield, below). If it depends on remembering to hand-edit JSON, it is empty forever and the best metric never has data.

Hence the `> [!aplicado]` callout — same scraper, nothing new invented. `doctor` now checks that cited evidence and resolution files exist; converting the callout into `applied` evidence is still pending.

### `card_policy` — absence is a decision, not an error

v6 computed `coverage_gap = encountered AND card_refs == []`. That flags every concept you consciously decided not to memorize. By month two the report has 60 false positives and you stop reading it.

**Alarm fatigue kills the tool long before any technical problem does.**

`card_policy` splits coverage in three: real gaps (`needed`, 0 cards) / undecided / deliberately declined. Only the first is allowed to be loud.

---

## `quiron today` — the only command you need to remember

`cards --list-gaps`, `cards --audit`, `next`, and `sources` are capabilities. They don't create a habit. One entry point does — and every line it prints ends in the command that acts on it, so nothing else has to be memorized.

```
$ quiron today --vault <vault>

🔴  eigenvectores · fallás la tarjeta #4 (7 lapses) y el concepto está aplicado
        → la tarjeta es sospechosa, no vos
🔴  Ref: colgante · 02-Topics/Matrices.md#Traza (la sección no existe)
🔴  duda abierta 31d · "por qué det(A-λI)=0 implica no invertible"

🟡  4 capturas sin procesar                       → /quiron-inbox
🟡  <n> conceptos "needed" sin tarjetas           → quiron cards --vault <vault> --list-gaps
🟡  3 conceptos sin decisión de retención         → quiron cards --vault <vault> --decide

⚪  23 reviews pendientes en Anki
⚪  descomposición-espectral ← recién desbloqueado
```

### The rule that keeps the tiers meaningful

Tiers are worthless the moment everything is red. So the rule is hard:

| tier | admits |
|---|---|
| 🔴 | something is **wrong**: a contradiction, a dangling `Ref:`, a suspect card, a *neglected* doubt (>30d) |
| 🟡 | something **waits on a decision from you** — including a *stale* doubt (14–30d) |
| ⚪ | information |

**A concept with no cards is never red.** It's a decision you haven't made. Neither is an unprocessed inbox.

Doubt age is three states, not a boolean — a single `stale_doubt` flag would put a two-week-old question and a two-month-old one in the same bucket, and the older one is the only one that means something went wrong:

```
0–14 días   fresh       nada
14–30 días  stale       🟡
30+ días    neglected   🔴
```

`cards --list-gaps`, `cards --audit`, `next`, and `sources` are the current CLI surfaces. There is no top-level `coverage` or `status` command; coverage and audit are options of `cards`.

---

## The questions it answers

Each is a query over the model; none touches scheduling.

**1. Coverage — is there anything to review at all?**
```
✗ eigenvectores — `card_policy: needed`, 0 tarjetas
```
The concept needs retention but has no card, so there is nothing for Anki to schedule. FSRS will never warn you: **you cannot forget a card that doesn't exist.** The current coverage command reports this concept-level gap; it does not infer lesson counts.

**2. Understanding vs recall — the contradiction**
```
⚠ eigenvectores — factor 2300 en Anki, understanding: encountered
   (recitás la definición; nunca la explicaste)
```

**3. Doubts — what stayed unresolved**
```
⚠ "por qué det(A-λI)=0 implica no invertible" — abierta hace 31 días
```
`06-Doubts-Resolved/` already exists in karpathy-path. The tracking is already part of the real workflow; today it's loose files nothing cross-references.

**4. What's next — candidates, not a schedule**
```
$ quiron next --vault <vault>
1. eigenvectores            ⚠ duda abierta 31d
2. descomposicion-espectral ← recién desbloqueado
3. <concepto>               ✗ coverage gap
```
A **candidate** is a concept with an open signal on it: a doubt still open, a coverage gap (`card_policy: needed`, no cards), a prerequisite just satisfied, or no `explained` evidence yet. One hard filter only — `blocked`, meaning a prerequisite hasn't reached `explained`. The rest rank by urgency. It produces a short list; it does not decide, and it says nothing about when to review.

**`applied` does not mean finished, and does not remove a concept from the list.** Having used something once is not having mastered it — you can apply SQL joins in one query and still hold two open doubts and want the harder cases. Evidence of use is evidence of use, nothing more.

The reason nothing tracks "done" is that nothing needs to. A concept with no open doubt, no coverage gap, and no unblocked successor simply has no signal, so it doesn't rank — it drops off because there is nothing to do with it, not because a field says so. Open a doubt about it in six months and it comes back on its own. A `state: active/dormant/archived` field would be the hand-typed `confidence: 3` returning under a third name.

**5. Source yield — a query, not a feature**
```
$ quiron sources --vault <vault>

Axler cap.5        12 conceptos ·  9 explicados ·  4 aplicados
devtalles secc.4   <n> conceptos ·  3 explicados ·  0 aplicados
```
Not "Axler is better." It says: *this material is turning into usable knowledge for me; this one I am mostly consuming.* You spend money and months on courses and books, and nothing today tells you which ones paid off — Anki doesn't know where a card came from, and your vault doesn't know what happened afterward.

**This is a `GROUP BY sources.ref`, not a phase.** It exists the day there is evidence. Nothing to build and nothing to defer — but the fields must be collected from Fase 1, or the data is simply lost. Deferring the *report* is fine; deferring the *field* is not.

Derived at query time, never stored:
```
coverage_gap → card_policy == "needed" AND card_refs == []
blocked      → algún prerequisito no llegó a "explained"
doubt_age    → fresh (<14d) / stale (14–30d) / neglected (>30d)
candidate    → not blocked AND (duda abierta OR coverage_gap
                                OR recién desbloqueado OR sin "explained")
understanding→ max(evidence.kind)   # lectura derivada, no veredicto
recall       → de AnkiConnect, en vivo, descartado después
```

---

## Card quality — three layers, and one signal that needs both systems

`karpathy-path/.claude/agents/harvard-reviewer.md` already exists and is good: read-only, dual expertise (subject matter + learning science), verifies every claim against the `Ref:`'d source note, applies the minimum-information principle, returns paste-ready fixes with a typed verdict per card. **It is not rewritten.** It is fed and remembered.

**Layer 1 — static, deterministic, no LLM.** Answer-in-question token overlap; enumerations (an answer listing ≥4 independently-forgettable items violates minimum information); length as a proxy for the reviewer's own ~15–20s read-aloud heuristic; fuzzy duplicates across the deck; dangling `Ref:` paths; cards mapped to no concept. Canonical reference: [Wozniak's 20 rules](https://super-memory.com/articles/20rules.htm).

**Layer 2 — the Anki cross-signal. The one that justifies having both systems.**

A card with many lapses is ambiguous: do you not know it, or is the card bad? Anki alone cannot disambiguate. The knowledge model can:

```
muchos lapses  +  evidencia de "explained"/"applied"  →  ⚠ la TARJETA es sospechosa
muchos lapses  +  solo "encountered"                  →  probablemente no lo sabés
```

If you demonstrated understanding — and a file in the repo proves it — but you systematically fail that specific card, the problem is the card. Impossible with Anki alone; impossible with the model alone.

**Layer 3 — `harvard-reviewer`, on the ~6 cards that gave signal, not on 148.** Its own skill file names the cost: *"reviewing 100+ unrelated cards in one pass dilutes the report and burns context."* Layers 1–2 are the fix.

```
$ quiron cards --vault <vault> --audit

⚠ 3 sospechosas (las fallás, el concepto tiene evidencia de aplicado)
   · eigenvectores.md#4 — 7 lapses, aplicado 2026-09-17 (scripts/pca.py)
⚠ 5 violan información mínima (enumeran ≥4 ítems)
✗ 2 duplicadas
✗ 1 Ref: colgante → 02-Topics/Matrices.md#Traza (la sección no existe)
→ despachar reviewer sobre estas 11
```

### What the reviewer is missing today, and what fixes it

| gap | fix |
|---|---|
| ciego a Anki — revisa texto, no ve 7 lapses | layer 2 se lo pasa en el prompt de dispatch |
| **sin memoria** — las revisiones son efímeras; re-revisás para siempre o nunca | `CardRef.quality` / `reviewed_at` persisten el veredicto |
| selección de target manual ("los archivos que acabás de escribir") | `--audit` responde *cuáles* y *por qué* |
| todo es juicio de LLM, incluso lo que resuelve un script de 10 líneas | layers 1–2 pre-filtran |
| hardcodeado a karpathy (deck, español, persona ML/AI) | subject + deck pasan a ser parámetros |
| **nadie valida al reviewer** | `lapses_at_review` — abajo |

`lapses_at_review` closes the last one: the reviewer says "split this" at 7 lapses; three weeks later the split cards sit at 1 → **the verdict worked.** Still at 7 → card size was never the problem. The reviewer becomes auditable instead of authoritative.

---

## What quiron explicitly does not do

| does | does not |
|---|---|
| ¿este concepto tiene tarjetas, y las necesita? | ¿están bien *programadas*? → **Anki** |
| ¿qué dudas hay abiertas, hace cuánto? | cuándo repasar → **Anki/FSRS** |
| ¿lo explicaste, o solo lo recordás? | si tu explicación es *correcta* → el reviewer |
| ¿qué está bloqueado por un prerequisito? | si el material fuente es bueno |
| ¿qué parte del material sigue sin tocar? | hacerte sentar a estudiar |
| ¿las tarjetas están bien formadas? | sync markdown → Anki → **yanki** |

Also out: habit tracking (`life-os`, different genre), `due.py` (Anki already shows what's due), and any write-back of grades through AnkiConnect (answering via AnkiConnect while also reviewing on AnkiDroid risks an AnkiWeb sync conflict — Anki's sync isn't a merge, one side's review log is discarded).

**Deferred deliberately, recorded in `DECISIONS.md` so they aren't silently lost:**

- **Addressable sub-concepts / scopes.** `Evidence.scope` is free text today. Making scopes first-class (so "geométrica" is a queryable sub-node) is a real modeling upgrade — after the daily loop is a habit, not before.
- **Curriculum from prerequisites.** Transitive closure over `prerequisites[]` gives the minimum ordered path to a goal: *"quiero entender attention → te faltan 7 conceptos, en este orden, 3 ya explicados."* Needs two populated vaults first.
- **Shared concepts across vaults.** Stable slugs let evidence transfer — you don't re-learn what you already applied, and a new vault starts partly populated. This justifies the Fase 7 template far better than "so someone else can install it."

These three are consequences of the data, not features to build now. Collect the fields; build later or never.

---

## Structure

```
quiron/
├── src/quiron/
│   ├── schema.py          # el modelo — single source of truth
│   ├── ankiconnect.py     # cliente read-only; split transitorio/permanente
│   ├── capture.py         # scrape de callouts → inbox.jsonl
│   ├── cardmap.py         # card path → concept resolution
│   ├── cardtext.py        # card parsing and static text checks
│   ├── inbox.py           # clasificar + aprobar en lote
│   ├── coverage.py        # material ↔ tarjetas
│   ├── audit.py           # calidad de tarjetas, layers 1 + 2
│   ├── today.py           # el punto de entrada; reglas de tier
│   ├── nextup.py          # candidate concepts; CLI: quiron next
│   ├── sources.py         # source-yield query
│   ├── recall.py          # optional Anki recall cross-check
│   ├── evidence.py        # explicit evidence writes
│   ├── migrate.py         # copier-based vault scaffolding
│   ├── doctor.py          # seed-resolution findings; --json
│   ├── headings.py        # topic-heading extraction
│   ├── seed.py            # concept model seeding
│   └── vault.py           # vault filesystem access
├── tests/
└── DECISIONS.md           # incl. por qué se cortó el routing loop, y los 3 diferidos

<vault>/00-Meta/
├── progress.json          # SIN TOCAR — units, sesión, datos del notifier
├── knowledge.json         # NUEVO — el modelo. Puramente aditivo.
├── inbox.jsonl            # NUEVO — capturas sin clasificar
└── history.jsonl          # NUEVO — transiciones append-only
```

`knowledge.json` being a **new file** is the point: Fase 1 touches nothing that exists. Its root document includes `schema_version` (currently `2`), and the loader explicitly upgrades legacy v1 documents.

`history.jsonl` records what `evidence[]` does not — doubts opened/resolved, cards flagged/fixed, and `card_policy` decisions — one line each, appended, never rewritten. Supported mutating CLI paths now append retry-safe events.

---

## AnkiConnect client — one correctness note

AnkiConnect **always returns HTTP 200** and puts failures in the body:
```json
{"result": null, "error": "collection is not available"}
{"result": null, "error": "deck was not found: karpathy"}
```
The client retries transient connection failures once while Anki is still starting, raises on the second failure, and does not retry permanent Anki body errors.

General rule for reading user data: no `.get(key, default)` swallowing a missing field — direct indexing, or an explicit assert with a message. Both vaults have already produced one silent-failure bug each (`notifier/remind.py`'s fallbacks; a skill referencing a deleted `viz_html.py`).

Cards come back from AnkiConnect as **rendered HTML**, even `fields.Front`. Resolve back to source markdown in `04-Quiz-Bank/<deck>/` via `noteId` rather than parsing HTML.

---

## Historical build order (v7)

Reordered in v7: **capture first.** Coverage is the more impressive demo, but capture is what decides whether there is a system in three weeks. This section preserves the original phase plan; the repository status and the explicit pending gaps above and below are authoritative for what is live today.

**Fase 1 — capture + today, on karpathy, today.**
`schema.py` + `capture.py` + `inbox.py` + a minimal `today.py`. Add the three callout types to the daily-log template, scrape existing `03-Daily-Logs/`, seed `knowledge.json` from what's already there (`02-Topics/` → concepts, `04-Quiz-Bank/karpathy/` → card_refs, `06-Doubts-Resolved/` → resolved doubts). `sources[]` is populated from day one even though nothing reads it yet — that's the source-yield field, and it cannot be backfilled. Nothing existing is modified.

**Fase 2 — coverage + the retention decision.**
`coverage.py`, `ankiconnect.py`. `quiron cards --vault <vault> --decide` walks undecided concepts so `card_policy` starts meaning something. Coverage reports only `needed`-and-empty; the current tier rule renders that gap yellow, never red.

**Fase 3 — card audit + reviewer fed and remembered.**
`audit.py` (layers 1+2), persist `quality` / `reviewed_at` / `reviewer_verdict` / `lapses_at_review`. `harvard-reviewer` unchanged in its logic; the dispatch now names *which* cards and *why*.

**Fase 4 — evidence at full depth.**
The evidence API, `quiron next`, and `quiron sources` are live. Migrated `/quiz-me` commands now include the shared `explained` evidence handoff; end-to-end processing of `> [!aplicado]` into `applied` evidence remains pending.

**Fase 5 — second vault: devtalles.** The real generalization test, already sitting there: 187 lessons, 45 cards, an ordered `sections[]` array with no `meta` block — structurally incompatible with karpathy on purpose. If the model survives devtalles unchanged, it generalizes; if not, the fix costs one file, not a rebuild. (Replaces the earlier plan's speculative "3rd vault" — a vault the same author builds to a schema they just designed is confirmation, not validation.)

**Fase 6 — parametrize the reviewer.** `harvard-reviewer` → `quiz-reviewer`, subject expertise and deck path as inputs. The review *structure* (accuracy against `Ref:`, minimum information, typed verdict) is identical for linear algebra and a Claude Code course; only persona and paths differ.

**Fase 7 — template, only if 1–6 hold.** copier, `copier.yml`, `_skip_if_exists`, `quiron migrate`. Deferred deliberately: generalizing before it works on two real vaults is what earlier versions did wrong. If two vaults work and nobody else ever uses it, the template was overhead — a fine thing to discover cheaply rather than build into.

**Vault-side housekeeping, still pending:** archive legacy `srs:` files, remove the legacy scheduler line from the vault-owned `CLAUDE.md`, update vault-specific `quiz-me.md` files that still mention "FSRS-lite" or SM-2 arithmetic, fix `note-collect/SKILL.md` Step 4's reference to the nonexistent `viz_html.py`, and enable FSRS in Anki where it is still off. These are outside this repository's runtime and canonical shared core.

---

## Pending gaps

These items are intentionally documented as pending. The current update aligns
the documentation with the implementation; it does not implement these
features:

- An `> [!aplicado]` capture is not converted to `applied` evidence without a classified proposal and the inbox apply step.
- `Evidence.ref` is required and non-empty at model construction time, and `doctor` reports missing referenced files; semantic validation of evidence content remains outside the deterministic core.
- Test fixtures still contain legacy frontmatter such as `confidence`; it is not a field in the persisted `Knowledge` model.

The deferred modeling decisions in `DECISIONS.md` — addressable scopes,
curriculum traversal, and shared concepts across vaults — remain deferred as
well.

---

## Honest risks

- **The processing bottleneck is real, not solved by assertion.** Bulk-approve and a dirty-tolerant inbox are the design answer; whether they suffice is an empirical question Fase 1 answers within two weeks. If `quiron inbox` becomes a chore, the capture premise fails, and the honest response is to cut processing entirely and let callouts stay raw text.
- **Three external dependencies on the critical path** — Anki desktop, the AnkiConnect addon (community-maintained, historically breaks on Anki updates), the yanki plugin. `doctor.py` and `today` now report Anki availability and degrade the layer-2 cross-signal when Anki is closed. Capture, coverage, doubts and source yield still work without Anki.
- ~~Obsidian is required for sync, not optional.~~ **Corrected 2026-08-29**: `yanki` is a headless npm CLI (`npx yanki sync <dir>`), not an Obsidian-only plugin — verified live against claude-devtalles (`--dry-run` then real sync, 14 notes created, matched the existing vault's namespace via `--namespace "Obsidian - Vault ID <id>"` read off an already-synced note's `YankiNamespace` field first). `.obsidian/**` still isn't templated and the vault-ID namespace still can't be fabricated for a vault that's never been opened in Obsidian at least once — but once it exists, every subsequent sync is scriptable. See `quiron-anki-sync` skill.
- **Prompt behavior is prompt + model; only the prompt is versioned.** When the model changes, the same `quiz-me.md` may grade harder or softer and nothing detects it. Record the model version alongside any fixture result so drift has a baseline to contradict. Now applies to the inbox classifier too.
- **Evidence is enforceable; its quality is not.** A non-empty, existing ref is intended to prove where evidence came from, not that the explanation is correct. That's the reviewer's job, and the reviewer is itself a model. Layered defenses, not a proof.
- **Narrow moat as a public product.** Card generation with LLMs is commoditized; sync is solved by yanki; agent-operates-a-vault has an 11k★ incumbent (`claude-obsidian`). The unclaimed piece is exactly this knowledge/quality layer — and every prior AI+Anki+Obsidian project found is abandoned (2023, 2024, Apr 2025); the survivors are pure plumbing. As personal infrastructure this is a sound bet; as a public product, thin.
- **Anki MCP servers evaluated and rejected** (2026-08-23): none official (`ankimcp`'s MCP-registry listing is self-publication, not endorsement), the only live one is 11 months old with 227/230 commits from one person, and **none exposes per-card stats** — only deck-level aggregates, which is precisely what layer 2 needs. For cron/CI strictly worse than a direct POST to `127.0.0.1:8765`. Optional complement later; never a dependency.

---

## Verification status

The following checks describe behavior that is currently implemented:

- A `Concept` derives `understanding` from its evidence; adding an `applied` entry changes the derived value without writing an `understanding` field.
- `Evidence` requires a `ref` field at model construction time.
- `quiron cards --vault <vault> --list-gaps` reports only `needed` concepts with no cards, and the command does not write `progress.json`.
- A concept with `card_policy: "declined"` and zero cards is absent from the coverage gap list.
- `quiron next --vault <vault>` keeps a concept with an open doubt in its candidate list even when it has `applied` evidence.
- Doubt age is rendered as fresh, stale, or neglected using the 14-day and 30-day thresholds.
- `quiron cards --vault <vault> --audit` combines static card checks with the optional Anki lapse signal.
- A dangling `Ref:` is reported by `doctor.py` as a seed-resolution finding.
- `today` automatically scans callouts, runs the card audit, and reports degraded Anki connectivity without failing the command.
- `doctor.py` reports missing card/evidence/resolution references, unknown prerequisites, duplicate card paths, and Anki connectivity.
- AnkiConnect retries transient transport failures once and does not retry permanent body errors.
- Supported mutating CLI operations append idempotent transition events to `history.jsonl`.
- `quiron sources --vault <vault>` derives its table from persisted source and evidence fields.
- Nothing in `knowledge.json` duplicates Anki scheduling fields. `lapses_at_review` is a reviewer-audit snapshot, not a scheduling input.

The following are pending acceptance checks rather than current guarantees:

- Automatic applied-callout writes for `applied` evidence.
- A complete under-a-minute inbox workflow with default acceptance across vaults.

**Current next action:** use the remaining pending-gaps list as the backlog for the
next implementation task.
