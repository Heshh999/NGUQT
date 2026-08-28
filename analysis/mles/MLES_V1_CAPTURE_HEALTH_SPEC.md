# MLES-V1 — CAPTURE HEALTH SPEC (outcome-blind by construction)

Health monitoring must be able to run **during protected partitions**.
It therefore reports only counts, times, hashes and structural facts.

## Permitted health outputs
- Row counts per stream, per instrument, per session.
- First/last receive timestamp; wall-clock coverage vs expected session.
- Heartbeat continuity; gap count and longest gap.
- Disconnect/reconnect count and durations.
- Sequence continuity: duplicates, gaps.
- Timestamp reversals (receive clock and exchange clock, separately).
- Crossed/locked quote counts.
- Book-reset counts.
- Parse-failure count and rate.
- SHA-256 per file; manifest verification.
- Per-instrument presence (NQ / ES / MNQ) for each session.

## Explicitly prohibited in any health output
Returns, price change, direction, accuracy, trade labels, signals, MFE,
MAE, P&L, equity curves, win rates, or any chart of price against an
outcome. `mles_integrity.py` enforces this two ways: it refuses files
whose header contains an outcome-bearing column name, and it imports no
analysis module (tested).

## Thresholds (frozen with Freeze A)
| Check | PASS | WARN | FAIL |
|---|---|---|---|
| parse success | ≥ 99.9% | ≥ 99.0% | < 99.0% |
| duplicate sequence | 0 | — | ≥ 1 |
| receive-clock reversal | 0 | — | ≥ 1 |
| exchange-clock reversal | 0 | bounded and logged | unexplained |
| session coverage | ≥ 95% | ≥ 90% | < 90% |
| instruments present | NQ+ES+MNQ | 2 of 3 | ≤ 1 |
| manifest verifies | yes | — | no |

A FAIL blocks those days from research use. Days may also be excluded
if the schema or recorder changes materially (§9).
