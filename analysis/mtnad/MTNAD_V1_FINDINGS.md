# MTNAD-V1 — DURATION / HAZARD / RENEWAL — FINDINGS

Protocol frozen at `7deabd8` before any outcome; engine + 22/22 unit
tests committed before the run. One-shot run, no reruns, no
corrections. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## Verdict

**0 / 8 confirmatory cells pass the full frozen gate battery.**

`NO VERIFIED NEW HIGH-OPPORTUNITY-FREQUENCY EDGE FOUND UNDER THE
FROZEN SEARCH AND AVAILABLE GENUINE DATA.`

Monte Carlo was not run (protocol: MC only for full passers; MC can
never rescue a failure). All results are
`EXPLORATORY DEV EVIDENCE — NOT INDEPENDENT CONFIRMATION`.

Scope: 16,254 intraday evaluations per scale over ~1,800 days; 1,812
daily evaluations; ~8,000 executed simulated trades; the intraday
cells ran at 3.3–3.6 trades/week with ≥91% of weeks active — the
frequency band the mandate demanded was genuinely tested.

## Intraday cells (S1 session / S2 rolling-4h / S1V volume-clock): dead

| cell | n | stressed | perm p | verdict |
|---|---|---|---|---|
| C1 S1 fresh-high LONG | 1248 | −0.933 | 0.378 | dead |
| C2 S1 fresh-low SHORT | 1175 | −1.575 | 0.560 | dead |
| C3 S2 fresh-high LONG | 1251 | −0.768 | 0.320 | dead |
| C4 S2 fresh-low SHORT | 1171 | −0.121 | 0.260 | dead |
| C5 S1V fresh-high LONG | 1219 | −1.199 | 0.467 | dead |
| C6 S1V fresh-low SHORT | 1165 | −0.955 | 0.415 | dead |

Every intraday cell is negative after stressed costs (BH q ≈ 0.55
across the board); three are negative even at base costs, and the
gross means (+0.11 to +1.18 on the positive side) sit below one
spread. Neighbors, delays and alternate exits are consistently
negative. The volume clock adds nothing over the wall clock.
**Refresh-age asymmetry carries no monetizable intraday information at
the 60m horizon** — the renewal clocks are new mathematics but not new
alpha.

## Daily cells: one loud near-miss, correctly refused

**C8** (short when the 20-day low is fresh / high stale): dead
(−0.34 stressed, p 0.48). Down-fresh states do not continue down —
consistent with every prior failure to short this instrument.

**C7 — LONG day when the 20-day high is fresh and the 20-day low is
stale (ARd ≥ causal q80)** is the strongest single cell any discovery
wave has produced since OFH13:

- n=390 days, stressed **+15.72 pt/trade** (≈ $31 MNQ), PF 1.37,
  win 53.3%, CI [+2.67, +28.65], perm p 0.0066
- survives best-day removal (+14.57), top-1% removal (+12.80),
  entry delayed to open+30m (+14.30), both frozen neighbors
  (q75 +13.19, q85 +12.10)
- **incrementality passed**: positive in BOTH 20-day-return-sign
  strata (+15.78 when trailing momentum is up, +10.55 when it is
  down) — the age signal is not just displacement momentum relabeled.

**Exact binding failures (three, frozen before outcomes):**

1. `q<=0.05` — BH q = **0.0528** across the 8-cell family.
2. `years_pos>=6` — **5/7**: 2020 −8.65 and 2024 −10.87 are negative;
   and 2026 (+80.83) supplies 46% of all profit (domination 0.46,
   inside the 0.50 gate but only just).
3. `weeks_ge1>=60%` — only **41.5%** of complete weeks contain a
   trade (mean 1.11/wk but median 0): it fails the primary
   high-opportunity-frequency mandate it was tested under.

The adversarial reading: C7 is a daily trend-state harvest that pays
in trending years (2022/2023/2026) and bleeds in chop (2020/2024);
2026's outsized contribution is exactly the regime-concentration
pattern the year and BH gates exist to catch. The protocol states
"failure kills the family as frozen — no rescue, no inversion, no
re-thresholding." **C7 is registered DEAD_FROZEN**, and is reported
here as the *closest nonqualifying candidate* with its exact binding
failures, per the directive. No prospective freeze is created: unlike
STREAK3DN (which failed only the n floor), C7 failed substantive
statistical and robustness gates.

What genuine future evidence could responsibly revisit this
mechanism: only a new, separately frozen programme on data not yet
exposed (VALIDATION opens 2026-09-01 for the three already-frozen
candidates; nothing here earns a seat in it).

## Ledger and reproduction

- Full raw statistics: `MTNAD_V1_RAW.json`; console: `MTNAD_RUN_OUTPUT.txt`.
- Registry: `MTNAD-DHR-INTRADAY` (C1–C6) and `MTNAD-DHR-DAILY`
  (C7–C8) → DEAD_FROZEN, new class `DURATION_HAZARD_RENEWAL` added to
  CLASS_DEF; fingerprints regenerated; closure tests re-run.
- Reproduce: `python3 analysis/mtnad/mtnad_run.py` (~128 s); seeds
  20260920/21/22 frozen in protocol.
