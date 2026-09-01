# DATA_HANDOFF.md — capture → research handoff contract (v01.2)

Defines exactly what moves from the user's recording machine to the
research side, and what happens to it. Raw files are immutable; every
derived artifact carries its parents' hashes.

## 1. What the user sends after recording

Per session and instrument (NQ, MNQ, optionally ES):

| file | size class | needed |
|---|---|---|
| `MLES_<inst>_<session>_manifest.json` | tiny | **always — send first** |
| `..._quality.csv` | small | always |
| `..._trades.csv` | large | on request / batched |
| `..._quotes.csv` | large | on request / batched |
| `..._depth.csv` | largest | on request / batched |

Manifests alone let the research side verify row counts, SHA-256s,
coverage windows, and quality counters without moving bulk data. Never
edit, re-save, re-encode, or "clean" any CSV — the SHA-256 in the
manifest must match the file exactly as the recorder wrote it.

## 2. Intake pipeline (research side, deterministic)

1. `mles_integrity.py <folder>` — outcome-blind session score
   (coverage, gaps, reversals, crossed/locked incidence).
2. `mrof_engine.parse_stream` per file — schema check, contract-mix
   refusal, duplicate/gap census; raw rows never modified.
3. Readiness ledger update: sessions accumulate toward the frozen
   floors (20 → pipeline verification; 60 → descriptive audit; the
   MLES State-C floors for outcome research).
4. Only after a committed State-C readiness freeze does ANY outcome
   flow run — the engines physically lack outcome code until then
   (`research_unlocked()` hard lock).

## 3. Partitioning at handoff

Capture data is future data. It is assigned at intake to
engineering/verification versus protected evaluation strictly by the
governing partition rules; no session may be inspected for P&L during
engineering. Blinding follows `analysis/mles/MLES_V1_PARTITION_AND_
BLINDING.md`.

## 4. Chain of custody

Every handoff batch is logged: session IDs, manifest hashes, file
hashes verified on receipt, integrity verdicts, and storage location.
A hash mismatch quarantines the file (`DATA_SUPPRESSED` at the
coordinator level); it is never repaired in place.
