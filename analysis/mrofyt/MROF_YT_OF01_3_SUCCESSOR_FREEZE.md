# MROF-YT-OF-01.3 — SUCCESSOR FREEZE (FINAL-PROMPT-EXACT COORDINATOR)

Frozen and committed **before any outcome is computed or computable**.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.

## 1. Lineage, immutability, and the authoritative prompt

- Predecessors immutable: v01 `f99c521`, v01.1 `0bf0ec5`, v01.2
  `3aa0f61`. **Thirteen** predecessor file hashes are pinned and
  re-verified by the v01.3 suite on every run. A1–A6 thresholds are
  untouched.
- **Authoritative final prompt archived and hash-VERIFIED**:
  `MROF_YT_OF01_FINAL_SOURCE_PROMPT.md`, SHA-256
  `74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b`
  (924 lines) — the reference that v01.2 could only record as a
  user-supplied hash is now held, verified, and governing verbatim.
- The v01.2 coordinator's two invented rules (60 s/4-tick re-arm;
  1 ms simultaneity window) are **superseded, not edited**: the v01.2
  module remains frozen, and `mrofyt_coordinator_v013.py` implements
  the final prompt exactly. The integration path uses v01.3.

## 2. v01.3 artifacts and hashes

```
74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b  MROF_YT_OF01_FINAL_SOURCE_PROMPT.md
c0fd9f04d4c17b78722e74bd48f1dd4f57a521993907818fea0d65e75941d4ef  mrofyt_coordinator_v013.py
788248f531afc7e56ad793fb9a9a8828cdc180d605987c7ca36ab1104a18f971  tests_mrofyt_v01_3.py
c5b0a9023631a5f1cc21fddc868bbbc95d9ec42dd825f08b34639bfa761293f4  RECORDER_DEPLOYMENT_v01_3.md
71bcf2f6b23aae830bbaf9e84dce7161596921342f2788c0eb8b46c613376f8d  DATA_HANDOFF_v01_3.md
```

## 3. Final-prompt requirement traceability

| final-prompt requirement (line) | implementation | test |
|---|---|---|
| deterministic SETUP_EPISODE_ID from spec version, instrument, exact contract, session date, family, cluster, approach; callback-order independent (repair 1) | `_episode_id` + `_cluster_id` (family-canonical, label-free) | R1, R1b |
| no trade cap; weekly floor is a minimum, never a throttle (§23–24, 715) | no cap variable exists in source | (b), (i) |
| wall/test families reset by two-tick retreat/new approach (§621, 719) | `on_price` WALL_TEST_FAMILIES branch | (d), (e) |
| other families reset by proximity-band exit + re-entry (§719) | `on_price` band branch | non-wall reset test |
| entry conditions reform ENTIRELY from later data (§719) | `formed_from_t > reformed_after_t` gate | (e2) |
| **no arbitrary time cooldown** (§719) | no time constant in re-arm path | (d2) |
| earliest signal wins; exact same-timestamp agreeing ties → one position, lowest family ID precedence, all tagged (§721) | `on_signals` group resolution | (f) |
| opposing exact ties → neither executes; no fill/position/TRADE_OPENED (§721) | conflict branch returns before any fill call | (g) |
| no arbitrary 1 ms simultaneity window (repair 3) | groups are exact-timestamp submissions only | repair3 |
| open-position signals recorded at original time, never entered later (§725 h) | NOT_FLAT at t, no queue exists | (h) |
| canonical cluster identity for re-arm bookkeeping; display labels never change the reset key (repair 4) | reset key = (anchor tick, family, direction) | repair4 |
| event-driven liquidity: unchanged repeated quote ≠ new liquidity; only genuine executions/replenishment add (repair 5) | `fill_event_driven` availability ledger | repair5–5c |
| strict 20-session readiness on EVERY baseline incl. H1 slots; calendar/DST/holiday/maintenance/contract validation across the whole swing/base/displacement window (repair 6) | `StrictSlotBaseline`, `SessionCalendar`, `find_zone_at_v013` | repair6–6d |
| wall-episode identity instrument\|contract\|session\|side\|approach; terminal/close/reset; new approach = new episode; opposite sides never merge (repair 7) | `WallEpisodeRegistryV013` | repair7–7d |
| deployment deliverables: exact .cs/namespace/F5, windows/settings/start-stop, health counters, 5-min NQ+MNQ smoke test, ten-level verification, Market Replay backup, manifests, copy/upload, read-only proof, parser command, INSUFFICIENT_DATA readiness (§472–482) | `RECORDER_DEPLOYMENT_v01_3.md`, `DATA_HANDOFF_v01_3.md` (supersede v01.2 docs, which stay hash-pinned) | repair8, 8b |
| required tests (a)–(i) incl. four-sequential-setups anti-cap proof (§725) | full adversarial suite | (a)–(i2) |

## 4. Test commands and complete counts

```
cd analysis/mrofyt
python3 tests_mrofyt.py          →  59/59
python3 tests_mrofyt_v01_1.py    →  56/56
python3 tests_mrofyt_v01_2.py    →  31/31
python3 tests_mrofyt_v01_3.py    →  32/32
cd ../mrof  && python3 tests_mrof.py     →  42/42
cd ../mofad && python3 tests_closure.py  →  15/15
```

## 5. Still blocked (explicit)

1. Captured event sessions = 0; the recorder has never been attached
   (user-side §2–§5 of the runbook).
2. H1-zone certification, PSY-NQ audit, ADR certification: impossible
   on historical continuous data; statuses unchanged.
3. Historical depth does not exist anywhere; Tier-2/3 accumulates
   forward only.
4. Probability models, grades, zone interactions: shadow-only pending
   State-C readiness and nested-fold training.

## 6. Classification

**`INSUFFICIENT_DATA`** — unchanged. Four green suites (178 checks)
prove the machine matches the frozen specification; none of them is,
or is claimed as, evidence of positive EV.
