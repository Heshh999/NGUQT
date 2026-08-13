# MnqTwoStrategies — NinjaTrader 8 (MNQ ONLY)

Two completely independent automated strategies in one NT8 host strategy, implemented from
the master specification **V6** (`two_automated_strategies_for_claude_v6_MNQ_ONLY_FINAL.md`,
supersedes V5). V6 locks U1–U9 — see `docs/CHANGELOG_V6.md` and
`docs/COMPLIANCE_AUDIT_V6.md`:

1. **FAKE_BREAKOUT** — 15m failed-breakout reversal at YDay/LWeek highs/lows, 1m/3m entry
2. **VECTOR_BREAK_RETEST** — 15m vector break of the Daily Open, 1m retest entry

Shared read-only utilities: Traders Reality vector classification, key-level calculations,
the 18-level take-profit engine, MNQ ($2/pt) risk-based sizing, session/time helpers, logging.

## Files

| File | Contents |
|---|---|
| `src/MnqTwoStrategiesShared.cs` | Enums, vector classifier, key-level + 18-level target engine, position sizer, trade log/stats, host interface |
| `src/FakeBreakoutEngine.cs` | Strategy 1 state machine (independent) |
| `src/VectorBreakRetestEngine.cs` | Strategy 2 state machine (independent) |
| `src/MnqTwoStrategies.cs` | NT8 Strategy host: series wiring, MNQ gate, orders, parameters |
| `docs/SPEC_ANALYSIS.md` | Pre-implementation analysis (A–E deliverables, V4-era) |
| `docs/COMPLIANCE_AUDIT_V6.md` | **Current** rule-by-rule V6 audit + remaining issues |
| `docs/CHANGELOG_V6.md` | V6 rule-lock pass (U1–U9): previous vs corrected behavior |
| `docs/COMPLIANCE_AUDIT.md` | Superseded V5 audit (kept for history) |
| `docs/CHANGELOG_V5.md` | V5 correction pass: every file/function changed, previous vs corrected behavior |
| `tests/` | Deterministic engine tests (Mono/.NET, no NinjaTrader needed) — 93 assertions |

## Installation

1. Copy the four `src/*.cs` files into
   `Documents\NinjaTrader 8\bin\Custom\Strategies\`.
2. Open the NinjaScript Editor in NT8 and press **F5** to compile.
3. Apply the strategy **to an MNQ chart** (any chart series period — the strategy adds its
   own 1m/3m/15m series and never uses the chart series for logic). It refuses to trade any
   non-MNQ instrument.
4. Load enough historical data: the 1m series must cover at least the previous full week
   (LWeek levels) — 10+ calendar days of 1m data recommended before the first tradable day.

## Important operational notes

- **Calculate.OnBarClose**: every signal uses completed candles (spec anti-repaint rule).
  Entries are market orders submitted at the signal candle's close; in backtests they fill at
  the next bar's open. Stops are real stop-market orders held at the structure price.
- **No strategy-level session-close flatten (V5 Fix 6)**: 11:30 ET is a new-entry cutoff
  only; positions run under their stop/target/trail/runner rules. The *platform* flatten
  option exists as a parameter but defaults OFF and is not a strategy rule. Note: your
  broker/Trading-Hours settings can still flatten independently of this strategy.
- **Exchange day = 18:00 ET (V5 Fix 4)**: Daily Open / YDay / pivot day boundary follows the
  CME exchange day (TR `getdayOpen` daily-bar boundary for MNQ). Set the day-start parameter
  to 0 to reproduce the TR library's literal "exchange midnight" (forex/crypto) behavior.
  YDay/LWeek high/low and all pivot & M-level formulas are confirmed against the TR **main
  indicator** (`f_security(...,'D'/'W',...,false)` = previous completed daily/weekly values).
- **Psy levels use the FOREX path** (confirmed for MNQ; TR's `overridePsyType` selector).
  Window = Monday 00:00–08:00 GMT = Sunday 20:00 → Monday 04:00 ET, fully inside CME hours
  year-round with no DST dependency. The crypto path (Sunday 22:00 → Monday 06:00 GMT,
  Sydney-DST aware) stays selectable via the psy-type parameter. Confirm against TradingView
  with the level-diagnostic parameter — see caveat 2 in `docs/COMPLIANCE_AUDIT.md`.
- **Timezone**: bar times are converted from your machine's timezone to US-Eastern. If your
  NinjaTrader time zone is already US-Eastern, set *"Bar times already US-Eastern"* = true.
- **Level verification**: set *"Print 18 levels on ET date"* (yyyy-MM-dd) to print all 18
  target levels at 9:30 ET on that date for comparison with the Traders Reality TradingView
  indicator.
- **Tests**: `cd tests && mcs -out:run_tests.exe ../src/MnqTwoStrategiesShared.cs
  ../src/FakeBreakoutEngine.cs ../src/VectorBreakRetestEngine.cs MockHost.cs Tests.cs &&
  mono run_tests.exe` — the engines and the handoff coordinator have no NinjaTrader
  dependency, so the V6 scenario tests run anywhere .NET/Mono runs (93 assertions).
- **Backtest sizing** uses the *Backtest starting balance* parameter (default $5,000),
  optionally compounded with realized PnL. Live sizing uses the account cash value.
- **Risk warning**: the spec mandates 50% / 26% / 10% account risk per trade. Those are the
  defaults because the spec says so — they are extremely aggressive.
- **Strategy handoff (V6 U9)**: FB and VBR never hold positions at the same time. If one is
  open and the other produces a valid entry, the open position is flattened first, the
  account-flat confirmation is awaited, and only then is the replacement order submitted —
  which also avoids NT8 netting the two engines together. Watch the first live handoff to
  confirm `OnPositionUpdate` fires as expected.
- **CSV trade log** is written to `Documents\NinjaTrader 8\MnqTwoStrategies_trades_<ts>.csv`;
  diagnostics stream to the NinjaScript Output window. Per-strategy win/loss, R, MFE/MAE
  summaries print when the strategy stops.
- V6-locked behaviors are the defaults; legacy research flags are labelled
  "LEGACY … keep FALSE/TRUE" in the parameter list. See `docs/COMPLIANCE_AUDIT_V6.md`
  before trusting a backtest.
