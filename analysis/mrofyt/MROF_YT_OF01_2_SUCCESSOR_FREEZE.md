# MROF-YT-OF-01.2 — SUCCESSOR FREEZE (COORDINATOR + SPEC REPAIRS)

Frozen and committed **before any outcome is computed or computable**.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.

## 1. Lineage and immutability

- Predecessors immutable: v01 (`f99c521`) and v01.1 (`0bf0ec5`). All
  **eight** predecessor file hashes are pinned and re-verified by the
  v01.2 suite on every run (see `tests_mrofyt_v01_2.py`). Nothing in
  A1–A6, the level hierarchy, thresholds, or execution defaults was
  amended.
- Authoritative final source prompt: SHA-256
  `74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b`
  — **user-supplied hash; the file itself was not uploaded**, so it is
  recorded here as the external reference and this freeze implements
  the requirement list the user enumerated from it. The v01.1 archived
  source (`76624b82…`) remains the latest full text in the repo.
- No outcome data has ever been opened (0 captured sessions), so these
  additions are pre-outcome specification work, not a post-outcome
  revision.

## 2. New artifacts and hashes (v01.2)

```
2db5524a1a8e4877931c2ad5b578c384d76808661a9994e2d15b33a11a4a66e8  mrofyt_coordinator.py
ea3770f5e0772d2f46a35f55c3c89d08c5b6ce831bd0c6aaaaa549c45bdb8560  tests_mrofyt_v01_2.py
cb9d3fd0d1329dda1e0f8b39974995b8dfa10254d5170c16e7c1aefb948a5a30  RECORDER_DEPLOYMENT.md
2d7a9400ee0823bedad0183d633900f691dfb8819f4d140b0ac0cbf2ff0652b2  DATA_HANDOFF.md
```

## 3. Uncapped independent-setup coordinator (frozen)

`SetupCoordinator`: immutable `SETUP_EPISODE_ID`; **no daily or weekly
trade-count cap** — while flat, every independent valid setup may
trade; one position at a time; duplicate-callback suppression;
overlapping-level labels of one physical episode merge into that
episode (never a second trade); simultaneous opposite-direction
signals (≤1 ms) stand both setups down; internal active-level
eligibility (no caller assumption); liquidity-aware execution with
partial and missed fills. Frozen re-arm/reset: after flat, the same
setup key re-arms after **60 s** or a trigger displaced **≥ 4 ticks**;
neither constant may be searched. Recorded decision states:
`OVERLAP_SUPPRESSED · SIMULTANEOUS_DIRECTION_CONFLICT ·
RISK_SUPPRESSED · DATA_SUPPRESSED · EXECUTION_MISSED ·
DUPLICATE_CALLBACK · NOT_FLAT_SUPPRESSED · NOT_AT_ACTIVE_LEVEL ·
REARM_PENDING`.

## 4. Specification repairs (all pre-outcome; predecessor untouched)

| # | defect | repair (additive) | test |
|---|---|---|---|
| R1 | baselines usable at ≥5 sessions | `StrictBaseline`: ALL 20 prior completed sessions required | R1 |
| R2 | H1 alignment only via external certify | `find_zone_at_strict`: contract identity + hourly session alignment enforced inside formation | R2, R2b |
| R3 | zones could span a roll | same window check kills any construction crossing a contract change | R3 |
| R4 | single-quote full fills | `fill_with_liquidity`: requested qty vs displayed size, partial fills across quotes, VWAP legs, frozen 5 s marketable window → `EXECUTION_MISSED` | R4, R4b, R4c |
| R5 | post-deadline window logic could fire before the cap | `simulate_capped`: any event at/after entry+30 m exits `TIME_30M` with absolute precedence | R5 |
| R6 | `ADVERSE_LARGE_PRINT_SHARE` was signed [−1,1] | renamed `adverse_large_print_polarity` (value preserved); new bounded [0,1] `adverse_large_print_share_bounded` = adverse large volume / total large volume | R6, R6b |
| R7 | no direct A5 tests | four direct A5 detector tests (fire, no-trend, weak replenish, mirror) | R7–R7d |
| R8 | toggle-off parity untested | passthrough harness: predecessor path vs coordinator-passthrough, **digest-identical** signals/fills/P&L | R8 |
| R9 | wall eligibility/dedup caller-assumed | `IntegratedWallGate`: refusal outside active levels and one-episode dedup INSIDE the engine | R9–R9c |

## 5. Test commands and complete counts

```
cd analysis/mrofyt
python3 tests_mrofyt.py          # v01 predecessor        59/59
python3 tests_mrofyt_v01_1.py    # v01.1 predecessor      56/56
python3 tests_mrofyt_v01_2.py    # v01.2 successor        31/31
cd ../mrof   && python3 tests_mrof.py          # engine   42/42
cd ../mofad  && python3 tests_closure.py       # registry 15/15
```

Coordinator proofs C1–C9 (C2 = four sequential independent setups →
four trades) plus the R1–R9 repair proofs and the 8-hash immutability
check are all inside the 31.

## 6. Deployment / handoff (deliverable 2)

`MROF_V1_Engine.zip` audited before any deployment claim: present,
SHA-256 `f4658e9b…`, 13 files, recorder and integrity checker
byte-identical to the committed repo sources. **Deployment is NOT
complete** — the recorder has never been attached; that step is
user-side only. See `RECORDER_DEPLOYMENT.md` and `DATA_HANDOFF.md`.

## 7. Still blocked (explicit)

1. The authoritative final prompt file (`74ff9a99…`) was not supplied
   — implemented from the user's enumerated requirement list; the hash
   cannot be verified against content we do not hold.
2. Captured event sessions = 0; recorder unattached (user-side).
3. H1-zone certification, PSY-NQ audit, and ADR certification remain
   impossible on historical continuous data (no contract identity; no
   TradingView export) — statuses unchanged: `H1_ZONE_UNVERIFIED_
   CONTEXT`, `PSY_NQ_UNVERIFIED`, `UNVERIFIED_CONTEXT`.
4. Historical depth does not exist anywhere; Tier-2/3 history only
   accumulates forward.
5. All probability models, grades, and zone interactions remain
   shadow-only pending State-C and nested-fold training.

## 8. Classification

**`INSUFFICIENT_DATA`** — unchanged. No outcome opened; A1–A6
thresholds unchanged; nothing here is, or is claimed as, evidence of
positive EV — synthetic unit tests verify code behavior only.
