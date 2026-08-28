# MLES-V1 — PARTITION GOVERNANCE AND OUTCOME BLINDING

## 1. Existing boundaries take precedence
DEV ≤ 2026-08-17 · buffer 2026-08-18→31 · VALIDATION 2026-09-01→2027-02-28 ·
OOS 2027-03-01→2027-08-31 · FINAL LOCKBOX 2027-09-01+.

MLES-V1 does **not** move, reinterpret, or relabel any of these. In
particular it may not treat a VALIDATION/OOS/LOCKBOX date as its own DEV
while that would reveal outcomes protected for another programme
(OFH13/OFH14 and MEMORY-PRED prospective arms are live on exactly those
dates).

## 2. What may run during a protected period
- **Raw message capture: yes, continuously.** Recording bytes is not
  reading outcomes.
- **Integrity/health monitoring: yes** — counts, clocks, hashes only.
- **Anything outcome-bearing: no.** No returns, labels, signal
  performance, directional accuracy, MFE/MAE, or P&L from sealed dates.

The separation is structural: `mles_integrity.py` cannot compute an
outcome (it imports no analysis module and rejects outcome-bearing
columns), and the recorder writes no derived value at all.

## 3. Blinding for the eventual Freeze B
When readiness is reached, Freeze B must be written **without viewing
any outcome label**. Feature debugging uses synthetic fixtures, replay
invariants, or masked/randomised labels — never real protected returns.
Outcome-bearing derived files, once they exist, live in a separate
directory from raw capture, with parent hashes, and are not read by any
Mode B tool.

## 4. Once opened, never independent again
If a date is legitimately opened for one programme, it may later serve
as exploratory data but **never again as independent confirmation**.
This is why MLES capture during VALIDATION is safe (bytes only) while
MLES *analysis* of those dates is not authorized here.

## 5. Automated scoring of protected parents
Permitted only if results remain sealed and inaccessible until the
predeclared opening date. No such scoring is configured by this run.

---
Freeze A commit: `c40f39a18a3741836b7849d0e2ab3c758c0e67e5`
