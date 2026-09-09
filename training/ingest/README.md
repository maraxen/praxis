# `ingest` — Coxswain corpus-ingestion pipeline

Increment 1's package for building and gating the training-recipe corpus
against the canonical PLR tool tables. See
`.praxia/docs/specs/260827_coxswain-corpus-ingestion-increment-1.md` for the
full spec; this file documents the operational surface only.

## Invocation form

**`python -m ingest.<module> <flags>`** — a module under `ingest`, never a
subcommand of a dispatcher. `python -m ingest <subcommand>` is **not** a
supported form; `python -m ingest` itself prints a signpost and exits 0 (it
dispatches nothing — see `__main__.py`).

Every command below is shorthand for
`uv run --package training python -m ingest.<module> <flags>`.

## The five module commands

| module | one-line description |
|---|---|
| `licenses` | License scanning and the D1 descend-rule verification for Increment 2+ eligibility |
| `recipes` | Recipe extraction from `recipes.yml` and API-token classification (two merge-proposal emitters) |
| `eval_split` | Eval split commitment (`eval_split.json`) and leak/lineage-contract verification (gate G5) |
| `audit` | Drift audit of recipe API tokens against the canonical tables, and gate G2 (adjudication completeness) |
| `gap` | Coverage-gap report against the verb x ambiguity matrix, and gate G1 |

Run any module with `--help` for its full flag list.

## Gate order

1. `licenses --check-descend` — **D1**: STOP/PROCEED/INCONCLUSIVE on licensing tier coverage. Kills Increments 2–4 on STOP.
2. `audit --gate` — **G2**: every blocking finding is adjudicated and digest-current.
3. `gap --gate` — **G1**: coverage-gap thresholds (T2/T3) against the committed corpus.

(`eval_split --check-leak <sidecar>` is gate **G5**, run independently — it has
no clone dependency and no STOP/PROCEED framing of its own; it is a leak
detector, not a descend gate.)

## Exit codes

The vocabulary is closed: **eight decision codes (0–7)**, plus **one
non-decision code (64)** for a malformed command line. 64 is listed under its
own heading below so it cannot be mistaken for a ninth decision.

### 0 — OK / PROCEED

The measurement was taken and the gate (or command) passed.

### 1 — Measurement error

The implementation or an input disagrees with a pinned expectation (a parse
failure, a missing committed data file, a T1 invariant violation, a present
clone at the wrong SHA, a write to a protected root).

### 2 — Unadjudicated blocking finding

`audit --gate` (G2) only: at least one blocking finding has no adjudication,
an incomplete one, or a stale `adjudicated_digest`.

### 3 — STOP, licensing

`licenses --check-descend` (D1) only: the tier-1+-effective source count is
below threshold and cannot be rescued by unresolved clones. Kills Increments
2–4.

### 4 — STOP, coverage

`gap --gate` (G1) only: the T2/T3 coverage thresholds fail (and are not
`t2_normalization_sensitive`, which would instead be CONTESTED — see 7).

### 5 — INCONCLUSIVE

The measurement could not be taken (§7.5) — almost always because the
cookbook clone (or, for `licenses`, a registry clone) is absent. **5 is never
a descend signal and never a pass.** See the clone-absent table below for the
per-command breakdown.

### 6 — Eval leak or lineage-contract violation

`eval_split --check-leak` (G5) only: `check_corpus_for_leak` found at least
one violation (cookbook-sourced row with no `recipe_path`, a `split=train` row
on a held-out path, or an undeclared `lineage` key).

### 7 — CONTESTED

`gap --gate` (G1) only: T2's collapsed and strict readings disagree on
pass/fail. Neither PROCEED nor STOP — the disagreement itself is reported.

---

### 64 — Usage error (`EX_USAGE`) — **not a decision**

A malformed command line: no flag from the module's required
mutually-exclusive group, a typo, an unrecognized argument, or a missing
`--out` on one of the six emitter flags. This is deliberately **outside**
the 0–7 decision range (`sysexits.h`'s `EX_USAGE`) so a CI wrapper keyed on
the 0–7 vocabulary can never mistake a malformed command line for a real
gate verdict — in particular, never for exit 2 (`argparse`'s own default,
which this package overrides for exactly this reason; see `cli.py`).

## Clone-absent behaviour (§7.5)

Every command's behaviour when the cookbook clone (or, for the two
`licenses` rows marked *(registry)*, any of the registry's 21 clones) is
absent. `--out <dir>` is required by the parser (not the handler) for the
six emitter flags below, so a missing `--out` always returns 64 regardless
of clone state — that ordering is structural (`cli.run` parses args before
calling the handler), not a per-command choice.

| command | clones present | clone absent |
|---|---|---|
| `licenses --report --out <dir>` | 0 | **0** — an absent clone is a `NOT_CLONED` verdict, which is *data* |
| `licenses --check-descend` *(registry)* | 0 or 3 | **5** |
| `licenses --verify-clones` *(registry)* | 0 | **5** if every failure is an absent clone; **1** if any present clone is at the wrong SHA; `--require-all` forces 1 |
| `recipes --emit-histogram --out <dir>` | 0 | **5** |
| `recipes --emit-receiver-alias-keys --out <dir>` | 0, or 1 if no committed `data/receiver_aliases.json` | **5** (clone check runs first) |
| `audit --report --out <dir>` | 0 | **5** |
| `audit --gate` | 0, 2, or 1 if `data/blocking_census.json` is absent/invalid | **5** (clone check runs first, before the census load) |
| `audit --emit-census --out <dir>` | 0 | **5** |
| `audit --emit-fingerprint --out <dir>` | 0 | **0** — reads only the canonical tables + committed artifacts, never the cookbook |
| `gap --gate` | 0, 4, 7, or 1 | **5** — T3 reads `recipes.yml` |
| `eval_split --check-leak <sidecar>` | 0 | **0, unaffected** — reads only the committed sidecar + `eval_split.json`, never `recipes.yml` |
| `eval_split --emit --out <dir>` | 0 | **5** |
| `eval_split --emit-lineage-contract --out <dir>` | 0 | **0** — reads only the committed sidecar |
| the six emitter commands with `--out` omitted (`recipes --emit-histogram`, `recipes --emit-receiver-alias-keys`, `audit --emit-census`, `audit --emit-fingerprint`, `eval_split --emit`, `eval_split --emit-lineage-contract`) | **64** | **64** — identical in both columns; `--out` is enforced in `parse_args`, which runs before any clone check |
| `pytest -k ingest` | all pass | all pass — clone-dependent tests `skip` with a reason naming the missing path; everything else runs |

## Package layout

```
training/ingest/
    __init__.py
    versions.py     pinned version strings + thresholds
    io.py           write_artifact — the ONLY writer; enforces PROTECTED_ROOTS
    sources.py      the 21-row source registry (sources.json)
    licenses.py      license verification + D1 descend rule
    recipes.py       recipes.yml reader + API tokenizer
    eval_split.py    eval split commitment + leak detection (G5)
    audit.py         drift audit + G2
    gap.py           coverage-gap report + G1
    cli.py          shared exit codes, exception roots, IngestArgumentParser, run()
    __main__.py     signpost only — never dispatches
    data/           committed gate inputs (hand-authored + computed)
    out/            committed gate outputs (license/audit/gap reports)
```

No module under `training/ingest/` uses `subprocess`, `os.system`, `eval`,
`exec`, `importlib`, `runpy`, or a bare `assert` statement (§7.3) — every
invariant raises a typed exception from the hierarchy rooted in `cli.py`.
