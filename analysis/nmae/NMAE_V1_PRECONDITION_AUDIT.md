# NMAE-V1 — MLES-V1 PRECONDITION AUDIT

**Result: PRECONDITION FAILS. NMAE discovery is NOT authorized.**
Only Mode A (read-only precondition, exposure and data-availability
audit) was performed. No outcome, candidate, or discovery result exists
in this program. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## 1. What §1 required, and what was found

| §1 requirement | Found |
|---|---|
| Committed MLES-V1 protocol | **NONE** |
| Complete MLES-V1 hypothesis ledger | **NONE** |
| MLES-V1 final report | **NONE** |
| MLES-V1 frozen-candidate file | **NONE** |
| MLES-V1 cumulative exposure ledger | **NONE** |
| MLES-V1 results commit | **NONE** |
| Protocol commit preceding outcomes | N/A — no protocol, no outcomes |
| Results commit in current ancestry | N/A |

**MLES-V1 does not exist in this repository.** It was never
preregistered, never run, and never committed. A word-boundary search
for `MLES` / `MLES-V1` across all Markdown, CSV, JSON and Python files
returns zero matches, and `git log --all` contains no MLES commit. (A
loose case-insensitive substring search returns five files, but every
hit is the letters "mles" inside words such as *samples*; none is an
MLES artifact. This is recorded so the negative result is reproducible
rather than assumed.)

The MLES conclusion could not be read from committed files because
there are no committed files to read. Per §1 this is the maximal case of
"incomplete", so the branch that applies is *If MLES is incomplete or
still collecting data*.

## 2. Consequences enforced (not bypassed)

- **No NMAE discovery, no protocol freeze, no candidate definition.**
- **MLES reserved mechanisms are NOT classified as dead.** Message-level
  mechanisms (top-of-book imbalance, OFI/queue depletion, absorption
  and replenishment, sweep/vacuum, intensity clustering, spread/depth
  regimes) remain **RESERVED_UNTOUCHED**. They were never given an
  evidential test, so they may not be imported into the spent registry
  and may not be reused as NMAE families.
- **No spent-registry import from MLES occurred**, because there is
  nothing to import.

## 3. Nearest analogue, and why it is not a substitute

MOFAD-V1 (commits `7c8a854` → `938382b`) is the closest program in this
repository: a microstructure/order-flow discovery run. It is **not**
MLES-V1 and is not treated as such. For completeness of the audit
trail:

- MOFAD's data audit found **no quotes, no depth, no tick/message data,
  no fills and no authenticated events anywhere** in the repository.
- MOFAD therefore ran only three bar-aggregate families (F03/F08/F12)
  and classified the seven genuinely message-level families as
  `CAPTURE_ONLY` — i.e. *not tested*, awaiting data capture.
- MOFAD's own verdict was `MOFAD-V1 FOUND NO FULL-GATE MICROSTRUCTURE
  CANDIDATE`, but the message-level mechanisms inside it were never
  evidentially tested.

So even under the most generous reading — treating MOFAD as a proxy for
MLES — the precondition would fail on the second branch instead
(`MLES-V1 DID NOT COMPLETE AN EVIDENTIAL TEST`), because the message
data required for a real test do not exist. Under **either** reading,
NMAE discovery is unauthorized. The returned line follows the literal
finding: MLES-V1 is absent, therefore the precondition is incomplete.

## 4. Repository state at audit time

- Branch `claude/ninjatrader-mnq-automation-rqjzgg`, HEAD
  `9c75fff743294a092b75c9502144edbfe716da8f`.
- Working tree clean at audit start (one file added by this audit).
- **All 15 prior freeze/result commits verified present in ancestry**
  (Wave-4, LPCC, CCHC, ODMC, MGSD, MOFAD, VTBS freeze and results
  commits). No history was rewritten, squashed, reset or deleted.
- Environment: Python 3.11.15, numpy 2.4.6, x86_64 Linux.
- Protected partitions **remain unopened**: buffer 2026-08-18→31,
  VALIDATION 2026-09-01→2027-02-28, OOS 2027-03-01→2027-08-31,
  FINAL LOCKBOX 2027-09-01+.
