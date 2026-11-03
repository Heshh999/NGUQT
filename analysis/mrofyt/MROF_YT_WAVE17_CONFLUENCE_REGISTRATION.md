# MROF_YT_WAVE17_CONFLUENCE_REGISTRATION.md — confluence grades across every level group, and whether to size into them

**Status: FROZEN on 2026-11-03, before any validation session (on or
after 2026-09-21) or replay holdout session was read by any tool, and
before confluence was computed on any recorded session.**

The operator asked whether a level that many traders see from different
angles makes a better trade than a level only one kind of trader
watches: yesterday's high near a round 100, the initial balance high on
top of an overnight high. More stop and breakout orders should sit there,
so a failed break should snap back harder. If it does, the operator wants
to size into those setups: an **A+** setup bigger than an **A**, an **A**
bigger than a plain one.

Nothing here comes from results: no tool has computed confluence on any
session.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. The levels and their families

Every level the registered waves build, on the runner they share, each in
one **family**:

| family | levels | from |
| --- | --- | --- |
| YDAY | yesterday's high, low | wave eleven's grid copy |
| OVERNIGHT | the overnight high, low | wave eleven's grid copy |
| LWEEK | last week's high, low | wave eleven's grid copy |
| CASH_OPEN | the 09:30 open | wave eleven's grid copy |
| GLOBEX_OPEN | the Globex open | wave eleven's grid copy |
| VWAP | session VWAP, upper and lower band | wave eleven's grid copy |
| PIVOT | PP, R1, S1, M2, M3 | wave eleven's grid copy |
| SWING_1H, SWING_4H | confirmed 1-hour and 4-hour swings | wave eleven §A |
| VALUE | yesterday's cash-session POC, VAH, VAL | wave thirteen §1, for the whole session |
| IB | the initial balance high, low | wave fifteen §1 |
| ROUND | every 100 points | wave fifteen §1 |
| EQUAL | equal highs and lows | wave fifteen §1.2 |

Each level is known when its own wave says it is known, and not before.

## 2. The signal

Wave eleven's WICK entry, the 10-second L2 analogue, unchanged, at every
level of every family:

- **Break:** a 10 s grid close a tick or more beyond the level, the last
  close not at it having been on the other side.
- **Entry:** the first 10 s tick within 300 s where the mid is back a
  tick through, with aggression against the break (`z_delta_s >= 1.0`).
  The trade fades the break.

Only **the first signal at each level per session** is taken. Signals of
one instrument in the same direction whose times fall within **60 s** of
the first of them are one event (several levels in one zone fire
together), traded once, at the first signal.

## 3. The grade

At the event's first signal, count the **distinct families** with a level
known at that moment within **8 ticks (2.00 points)** of any level that
fired in the event, those levels' own families included:

| families in the zone | grade |
| --- | --- |
| 3 or more | **A+** |
| 2 | **A** |
| 1 | **B** (no confluence) |

## 4. The trades

- **FIXED:** target 100 ticks (25 points), stop 60 ticks (15 points),
  1 800 s.
- **WIDE:** target 160 ticks (40 points), same stop and limit.
- Both are scored on every event, mid-to-mid (wave six's `path_exit`). A
  trade either version leaves unresolved is dropped.
- **Costs:** `mrofyt_costs`' round trip.
- **One position at a time** per instrument, in time order, over all
  grades, with the FIXED trade's length.

## 5. The tests (NQ; Holm over four at 0.05)

| test | question | rule |
| --- | --- | --- |
| **C1** | Does confluence pay? | FIXED net a trade of A+ and A together minus B: session-clustered difference (wave six B's influence-function estimator) above 0 with its 95 % interval above 0; each side 30 or more trades |
| **C2** | Is A+ better than A? | the same, A+ minus A |
| **C3** | Do confluence trades go further? | among A+ and A, WIDE minus FIXED net, paired per trade, session-clustered, above 0 with its 95 % interval above 0; 30 or more |
| **C4** | Do confluence trades make money? | A+ and A, FIXED: wave fourteen's verdict (mean net above 0 with its 95 % interval above 0, and still above 0 with the best session removed); 30 or more |

A test needing more trades than it has is **NOT ENOUGH TRADES**. A test
whose rule holds and that survives Holm is **PASS**; anything else with
enough trades is **NOT PROVEN**, with the reason. MNQ is reported beside
and never tested.

## 6. The sizing ladder (described, not tested)

**1 contract for B, 2 for A, 3 for A+**, against 1 contract for every
event, both one position at a time on FIXED. Reported: total net points
(points × contracts), points per contract, and the deepest drawdown of
each.

Sizing changes how much is risked, not whether an edge exists. **The
ladder may be adopted only if C1 passes** (and its A+ step only if C2
also passes) on held-out sessions, and then only in a later registration
judged on sessions read by nothing before it.

## 7. Fewer than 30 trades: results withheld

On a held-out read, a test without the trades it needs shows its counts
only; its means, intervals and the sizing figures are withheld from
screen and file (wave fourteen §5). The verdict comes at the first read
that holds them. No threshold is lowered.

## 8. Where it is judged

- **DEV** (sessions `<= 20260918`): describes only.
- **Validation** (`--unblind`, every session `>= 20260921`): a
  **secondary** test beside wave fourteen; part of the one-read
  checkpoint from V41 on.
- **Replay holdout** (`--holdout`): judged by the same rule, separately.

## Explicitly NOT registered

- other zone widths, other grade cut-offs, weights for some families over
  others
- counting levels of one family twice
- the L2 detector, the EARLY or CLOSE entries as the signal
- other targets, stops or hold limits; trailing or partial exits
- any other sizing ladder; sizing by volatility or account
- combining with wave twelve's filters or any other wave
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-03

`mrofyt_confluence.py`, `tests_mrofyt_confluence.py`. Written against
this file before any held-out session was read by it; verified on
hand-built levels, grids and trades and on synthetic recorder-format
runs, never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `all_levels`, `family_of` | VALUE levels last the whole session they belong to |
| §2 | `signals` (wave eleven's `run_episodes`, WICK, on the fixed levels and every listed level), `first_per_level`, `events` | none |
| §3 | `grade` | the zone is read from the grid record at the first signal |
| §4 | `score` | none |
| §5 | `tests` | none |
| §6 | `ladder` | the drawdown is the deepest fall from a running peak of cumulative net points |
| §7–§8 | `run`, `text`, the ledgers | none |
