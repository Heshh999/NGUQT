# MRV-V1 — MEAN-REVERSION + V-RECOVERY PRE-REGISTRATION

**Committed before any MRV outcome was computed.** Declared family
M = 18 (MR-H1…H8, V-H1…V-H10). **The directive text arrived truncated
after V-H2: V-H3…V-H10 have no received definitions and are marked NOT
SPECIFIED — RECEIVED TRUNCATED.** They are not invented, not replaced;
BH correction still uses the declared M = 18 (untested slots enter as
null placeholders). All tested rules are EXPLORATORY-DERIVED; no true
historical OOS remains. Frozen shelf untouched; no prospective data used.

Canonical reproduction re-verified immediately before this commit
(355,455 / 952 / 133 anchors).

## Data audit deltas (rest as prior audits)

- **VWAP: CAUSALLY DERIVABLE** — session VWAP (18:00 ET roll) from
  completed-bar typical price × volume. Bar-typical-price
  approximation of the tick VWAP, declared as such.
- Session high/low: causally derivable (running extremes since 18:00).
- Footprint-at-price, tick sequencing: NOT AVAILABLE (unchanged).
- 30s: OHLCV only, morning window (unchanged).

## Frozen constants (DEV, set before results; prior freezes reused)

| quantity | value |
|---|---|
| VWAP extension LARGE / EXTREME | ≥ 9.393 / ≥ 14.444 ATR (DEV q75/q90) |
| 30-bar move extension | ≥ 5.357 ATR (DEV q90) |
| volume climax | relVolume ≥ 3.286 (DEV q99) |
| impulse speed FAST / median | ≥ 0.768 / 0.395 ATR-per-bar (DEV q90/q50 among ≥2 ATR moves) |
| aggression / effort-failure | \|delta\| ≥ 511; E2 ≥ 15.9608 (reused) |
| CVD persistence margin | 586 (reused) |
| flush (V-family) | ≥ 1.5 ATR down within ≤5 consecutive bars, max relVol ≥ 2 during flush |
| fast 50% recovery | ≥ 50% of flush within ≤3 completed bars of the flush extreme (slow = 4–10; none = otherwise) |
| primary confirmation (MR family) | completed close above the prior completed bar's high (mirror below low) |
| gates | entry gate / cooldown 30m / costs / partitions / outcomes / ff / matched controls: identical to prior phases |

## Disclosed overlaps with already-run work

MR-H3 re-tests the PRO-OF-H3 REJECTED lead with the specified control
ladder and an added effort-failure arm — a stated replication attempt,
not a new discovery claim. MR-H4's deterioration component was refuted
location-free in V4.2-B (H-NEW5/H-NEW9); here it is re-posed **only**
inside the extension state. MR-H5 extends PRO-OF-H5 with the volume
(not delta) climax definition. MR-H6 is the failed-auction form at the
developing value area (PRO-OF-H6 tested touch-rejection; this tests
excursion-and-re-entry). These overlaps are why the family's honest
prior is low; they are run because the *conditioning states differ*.

## Tested rules (LONG stated; SHORT mirror; entry always on the frozen confirmation close; cooldown 30 m)

- **MR-H1** extension ≥ LARGE below VWAP (EXTREME reported separately) +
  attack bar (delta ≤ −511) with E2 ≥ cut + confirmation. Ablation:
  extension only · +attack · +failure · FULL.
- **MR-H2** ≥30 min into session; excursion below the prior running
  session low; no acceptance (no 3 consecutive closes below within 5
  bars); completed close back above the old extreme → long.
- **MR-H3** sweep of confirmed 3m / 15m / prior-day low (separately) with
  relVol ≥ 2 on the excursion; ladder: sweep only · +volume · +reclaim
  (close back above within 5 bars) · +failed continuation (an E2-failed
  attack while below) · FULL.
- **MR-H4** 30-bar move ≤ −5.357 ATR; last three attack bars show
  result₁ > result₂ > result₃ with effort₃ ≥ 0.9 × effort₁;
  confirmation. Ablation: extension alone · effort-only ladder ·
  result-only ladder · FULL.
- **MR-H5** climax bar relVol ≥ 3.286 with aligned delta (≥ +511 up
  climax / ≤ −511 down); classification in the next 5 bars: REJECTION =
  completed close beyond the climax bar's midpoint against its
  direction → fade entry there; STALL/CONTINUATION measured as states.
  Control: the climax bar itself.
- **MR-H6** profile ready; close below VAL; ≥1 outside bar with relVol
  ≥ 2; no 3 consecutive closes outside within 5 bars; completed close
  back inside → long toward value. Ladder: touch · excursion ·
  re-entry · FULL.
- **MR-H7** impulse ≥ 2 ATR over ≤10 bars; FAST = speed ≥ 0.768.
  Classification in next 5 bars: REJECT = close retracing ≥ 38.2% →
  entry on confirmation close. Compare FAST vs below-median-speed moves
  of equal size.
- **MR-H8** first push: attack bar (delta ≤ −511) making a 30-bar low
  L1; bounce ≥ 0.5 ATR; second push within 30 bars with low ≤ L1 + 0.1
  ATR and extension beyond L1 ≤ 0.25 ATR; arms: weak-effort second push
  (effort₂ ≤ 0.75 × effort₁) · high-effort/low-result (effort₂ ≥ 0.9,
  E2 ≥ cut) · efficient continuation (extends > 0.5 ATR beyond L1 —
  control state); confirmation close → long.
- **V-H1** flush per frozen definition; recovery ≥ 50% of flush within
  ≤3 bars (FAST) vs 4–10 (SLOW) vs none; entry at the completed
  50%-recovery bar (FAST arm = hypothesis).
- **V-H2** FAST V-H1 events where cumulative delta change from flush
  start to the recovery bar remains ≤ −586 (persistent opposing) vs
  recovered-delta control; generic-divergence reference = PRO-OF-H8
  FADE numbers.

Verdict vocabulary, survivor gate, management-only-for-survivors,
tails, long/short, month stability, sign-flip p / day-CI / BH q(18):
identical to prior phases. "None survived" is acceptable.
