# MLES-V1 — ANCESTRY AND PROTECTION AUDIT (Mode A)

Machine-readable companion: `MLES_V1_AUDIT.json`.
No protected outcome was opened. No unrelated artifact was modified.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## 1. Repository state

- Branch `claude/ninjatrader-mnq-automation-rqjzgg`, starting HEAD
  `10a0c324` (NMAE-V1 Mode A audit), tree clean at audit start.
- Environment: Python 3.11.15, numpy 2.4.6, Mono `mcs`, x86_64 Linux.
- **Ancestry verified 16/16**: Wave-4 `eac54fe`; LPCC `f08396b`/`be1fff6`;
  CCHC `5133c51`/`963009d`; ODMC `9072bd3`/`9fec078`; MGSD
  `7062e67`/`bb6986b`; MOFAD `7c8a854`/`643343f`/`e628b9d`/`938382b`;
  VTBS `8dfc2de`/`537a662`; NMAE `10a0c32`.
- Nothing reset, rewritten, squashed, deleted or concealed.

## 2. Protected rules — hashes recorded (SHA-256, first 32 hex)

`analysis/v41/cand_spec.py`, `ofh6_spec.py`, `ofht_spec.py`,
`ofht_cache.py`, `prospective.py`, `docs/PROSPECTIVE_REGISTRY.md`,
`src/MnqV41ProspectiveResearchHost.cs`, `src/V41FrozenCandidateEngine.cs`,
`src/MofadV1MicroCaptureHost.cs`, `analysis/mgsd/mgsd_lib.py`,
`analysis/mofad/MOFAD_V1_SPENT_HYPOTHESIS_REGISTRY.csv`,
`analysis/mofad/similarity_screen.py` — **12 of 12 present and hashed**
(values in `MLES_V1_AUDIT.json`). None was modified by MLES-V1.

OFH13/OFH14 parent rules, direction, eligibility and exits are
**immutable** for MLES purposes (§12 M4). The spent registry (78 rows:
59 `DEAD_FROZEN`, 10 `DESCRIPTIVE_ONLY_SPENT`, 2 `INSUFFICIENT_DATA`,
2 `PASSED_HISTORICAL_EXPLORATORY`, 5 `RESERVED_UNTOUCHED`) and its
deterministic screen are carried forward unchanged.

## 3. Partitions — unchanged and unopened

DEV ≤ 2026-08-17 · buffer 2026-08-18→31 · VALIDATION 2026-09-01→2027-02-28 ·
OOS 2027-03-01→2027-08-31 · FINAL LOCKBOX 2027-09-01+. Existing project
boundaries take precedence over MLES-V1 (§11). **No sealed date was
relabelled as MLES DEV.**

## 4. Recorder audit — `MofadV1MicroCaptureHost.cs`

Audited against §6/§7/§8 rather than duplicated. It is sound in
principle (Indicator, no order APIs, append-only, per-stream sequence,
heartbeats, gap/reconnect markers, daily SHA-256 manifest) but **14
schema gaps and 6 operational gaps** block MLES use:

| # | Gap | §ref |
|---|---|---|
| 1 | no schema version on rows | 7 |
| 2 | no capture-run ID | 7 |
| 3 | no session ID (rolls on UTC midnight, not the 18:00 ET session) | 7 |
| 4 | instrument/contract only in a log line, not per row | 7 |
| 5 | no platform callback timestamp | 7 |
| 6 | no monotonic clock (wall-clock adjustments corrupt deltas) | 7 |
| 7 | quote rows carry only the changed side, not full BBO | 7 |
| 8 | no book-reset/recovery indicator | 7 |
| 9 | no per-row connection/quality flags | 7 |
| 10 | no aggressor fields at all — neither raw nor inferred | 7, 3 |
| 11 | `mbo` column hardcoded to `MBP` as an assumption, undocumented | 6 |
| 12 | no session-state/roll flags | 7 |
| 13 | no timestamp-reversal detection | 7 |
| 14 | manifest is a text blob, not machine-readable | 7 |
| 15 | manifest written non-atomically (torn file on crash) | 8 |
| 16 | no guard against capturing into research folders | 8 |
| 17 | no multi-instrument run linkage (NQ/ES/MNQ unrelatable) | 6, 8 |
| 18 | `AutoFlush` per line — high I/O cost at message rates | 8 |
| 19 | no integrity checker existed | 8 |
| 20 | no capture-health status separate from analytics | 8 |

**Resolution:** `src/MlesV1CaptureHost.cs` (schema
`MLES-CAPTURE-1.0.0`) closes all 20. The MOFAD recorder is left
**untouched** as a committed research artifact and is superseded, not
deleted. Compile-verified clean against the NT8 API stub harness.

## 5. Feed capability classification (stated, not assumed)

- Depth: **MBP (market-by-price)** on NinjaTrader retail feeds. The
  recorder writes `bookType=MBP` and never implies order identity.
  **Passive queue fills are `NOT IDENTIFIABLE` from this data.**
- Aggressor: **no exchange-supplied flag.** `aggrRaw` is written empty;
  a versioned `QUOTE_TEST_v1` classification is stored separately in
  `aggrInf`/`aggrMethod`/`aggrConf`. Inference is never presented as
  ground truth.
- Provider sequence IDs: **not supplied by NT8** — the recorder's own
  per-stream arrival sequence is the ordering field, and that limitation
  is recorded rather than papered over.
- Cross-market lead/lag: **`NOT IDENTIFIABLE` until measured.** Clock
  uncertainty between instrument streams must be measured from captured
  data and shown to be under one third of any claimed median lead before
  M2 may be called a lead/lag effect (§9).

## 6. Existing data — nothing synthesized

Message-level capture files present: **quotes 0, trades 0, depth 0.**
The recorder has never been attached in NinjaTrader. **No tick, quote,
depth, trade sequence or fill was reconstructed, interpolated or
synthesized from bars**, and none will be.

---
Freeze A commit: `c40f39a18a3741836b7849d0e2ab3c758c0e67e5`
