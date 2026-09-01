# MROF-YT-OF-01 — Transcript-Audited Video-Derived Order-Flow Research Wave

**Revision:** Quant-EV mandate added 2026-08-29; official SMB Capital site refresh, NQ/MNQ transfer hardening, the preregistered level/geometry hierarchy, and the conditional Psychological High/Low NQ/FX module added 2026-08-30; causal one-hour supply/demand-zone context, key-level wall hold-versus-flush decision engine, and the futures-native Nour Trades transcript transfer added 2026-08-31. This revision preserves the transcript audit and all earlier safeguards while making independent mathematical strategy discovery and executable positive expected value the explicit research objective.

## Status and governing hierarchy

This is a continuation directive operating underneath the currently governing frozen MROF/master protocol. It does not replace, weaken, or override any existing partition guard, spent-hypothesis prohibition, protected-parent rule, sample floor, statistical gate, execution rule, freeze commit, frequency mandate, Monte Carlo requirement, or evidence classification.

The video material is hypothesis inspiration, not performance evidence. Do not inspect outcome data until this entire wave, its variation budget, signal definitions, execution rules, and promotion gates have been committed and hashed. Retain every failure and include every tested cell in the cumulative multiple-testing burden.

No backtest result is claimed by this document. The user's NQ/MNQ event data was not supplied during the video review.

The reported predecessor implementation at commit `f99c521` and its original freeze must remain immutable. Because no required outcome stream has yet been attached, implement this revision as a separately hashed pre-outcome successor freeze with new deterministic tests and a new commit. Do not rewrite the predecessor commit, silently change A1-A6, open P&L, or attach the recorder until this successor specification is committed. If any outcome data has already been opened, stop and register these additions as a new hypothesis version with a new validation clock.

This revision was audited against every line of the user-supplied `transcript.txt` (8,390 lines; SHA-256 `679f1f2d681e900c679b22600198900b0658bbeb05857292f50bceefd1a062f2`) and the supplemental `transcript(1).txt` (1,167 lines; 26,738 bytes; SHA-256 `76c05fff4c8fe67318f4179c715142bbafaaa4a8d60f1501b9c67592509937a7`). The supplemental file matches Nour Trades' **The Secrets On How To Read Order Flow + Tape** (`4r_3DNeE8_U`). A transcript is still only a source of candidate mechanisms. Presenter confidence, anecdotes, claimed profits, and attractive examples are not evidence that any rule transfers to NQ/MNQ.

## Primary mission: tape-scalping research

Focus this program on **intraday tape scalps**, not an unrestricted search across every conceivable trading style. The intended strategy class uses raw trades, inside quotes, and depth to time entries and exits around causally known market context. Candles, VWAP, VWAP bands, EMA-200, pivots, and prior-session levels identify location and regime; they do not replace the order-flow mechanism.

- A trade may last only seconds when the expected response fails, approximately 2–30 minutes when control persists, or any duration between those bounds. There is no minimum holding time.
- Every position must be flat no later than 30 minutes after entry and before the governing session close. No overnight, swing, or multi-day position may be promoted by this wave.
- Exit immediately at the first executable quote after the frozen invalidation event. Do not wait for a candle close unless the specific exit rule explicitly requires a completed bar.
- Optimize neither holding time nor exit horizon after seeing P&L. Duration must emerge from the frozen stop, target, early-invalidation, control-loss, and 30-minute maximum rules.
- The engine may independently discover new order-flow anomalies, features, interactions, and state transitions, including mechanisms not mentioned in the videos. Freedom to discover does not permit unlimited outcome-driven searching; autonomous work must use the bounded, separately frozen discovery lane defined below.

## High-level quantitative mandate: discover executable positive EV

Act as a senior quantitative market-microstructure researcher, statistician, and execution scientist. Do not merely translate the six video-inspired families into code. Use mathematical reasoning to propose genuinely new, economically coherent tape-scalping strategies and determine whether any has **positive executable expected value after every cost and realistic execution effect**.

The mission is to find positive EV if the data supports it—not to manufacture a passing strategy. `NO VERIFIED EDGE` is a correct result when uncertainty, costs, instability, or multiplicity consume the apparent edge.

For executed trade `j`, define net payoff in dollars as:

`Y_j = direction_j × ((VWAP_exit_j - VWAP_entry_j) / tick_size) × tick_value × filled_quantity_j - commissions_j - exchange_fees_j - modeled_slippage_j`

Use actual quantity-weighted executable fills for partially filled entries and exits. Missed entries are recorded as missed signals and are not converted into theoretical midpoint fills. Also report `Y_j / initial_risk_j` in R units. The strategy's primary economic quantity is:

`EV_net = E[Y_j | frozen signal and executable fill policy]`

Positive win rate, gross markout, profit factor above one, a high classifier AUC, or a visually persuasive tape sequence is not equivalent to positive EV. A strategy may be called a DEV positive-EV candidate only when its completely out-of-sample, net-of-cost estimate passes the governing uncertainty, frequency, stability, and multiple-testing gates. It remains `DEV_PASSER_AWAITING_UNTOUCHED_VALIDATION` until it survives prospectively collected data.

### Quant research responsibilities

1. **Generate mechanisms, not indicator combinations.** Derive candidate edges from measurable microstructure behavior: price response conditional on signed flow; depletion versus non-trade withdrawal; replenishment and resiliency; state transitions; first-passage behavior; self-excitation and decay; lead/lag; spread closure; and interaction with causally known location. Each candidate must explain why another participant may repeatedly pay the strategy after costs.
2. **State the mathematical prediction first.** Before looking at strategy P&L, specify the conditioning event, forecast variable, forecast horizon, expected sign or nonlinear shape, invalidation event, and why it should persist out of sample.
3. **Separate forecasting from trading.** First test whether the feature forecasts price response, time-to-response, or barrier order. Then convert it into exactly one frozen executable entry/exit policy. A statistically detectable forecast that cannot overcome spread, slippage, latency, partial fills, and fees is not a strategy.
4. **Estimate conditional EV, not just direction.** Model both outcome probability and payoff magnitude, or directly model the full net-payoff distribution. A 55% directional prediction may have negative EV when adverse outcomes are larger or execution is worse.
5. **Use all available mathematical freedom within the frozen budget.** The six video-derived families are research seeds, not a ceiling. Independently investigate new anomalies through the autonomous lane, but never hide a parameter sweep, subgroup search, model tournament, or exit search inside one registered family.
6. **Prefer parsimonious explanations.** A simpler model with stable out-of-sample net EV outranks a more complex model with slightly better in-sample fit. Complexity is permitted only when it adds incremental out-of-sample value after its full selection burden.
7. **Quantify uncertainty honestly.** Millions of depth messages do not equal millions of independent observations. Estimate effective sample size after clustering overlapping signals and serially dependent events by session and episode.

### Permitted mathematical discovery ladder

Use the following order. A later stage opens only when the earlier stage is implemented, retained as a benchmark, and the effective sample size can support the added degrees of freedom.

1. **Event studies and conditional response surfaces:** session-blocked markouts, first-passage probabilities, adverse/favorable excursion, empirical conditional EV, quantile effects, and monotone or U-shaped relationships.
2. **Regularized statistical models:** penalized logistic/linear models, robust regression, and generalized additive models for nonlinear but interpretable flow-response relationships. Fit normalization, transformations, interactions, and calibration only on past training data.
3. **Duration and competing-risk models:** survival/hazard analysis for time to target, stop, control loss, or 30-minute timeout, with right-censoring handled explicitly.
4. **Sequence and regime models:** marked Hawkes/point-process models, state-space models, hidden-state models, and change-point detection when their states have a frozen economic interpretation and can be estimated causally in live operation.
5. **Machine learning:** regularized boosted trees or other bounded nonlinear learners only after simpler baselines and learning curves demonstrate enough independent data. Deep order-book or sequence models require a separately approved wave, substantially more independent data, fixed architecture/training budget, and a complete simpler-model comparison.

Do not run an unrestricted algorithm zoo. Each materially different model class, label, feature family, hyperparameter search space, or subgroup search is a tested comparison and must be registered in the cumulative multiplicity ledger. Unsupervised methods may reveal structure, but selecting a cluster because its later P&L is attractive converts that cluster selection into a supervised hypothesis and charges it accordingly.

### Labels and optimization objective

Use three causally aligned research targets without conflating them:

- **Immediate validity:** signed executable markout and expected-response residual at 2s, 5s, and the completed 10s decision window.
- **Path behavior:** which frozen barrier or control-loss event occurs first and the hazard of each event up to 30 minutes.
- **Strategy outcome:** realized net P&L from the one frozen executable policy, including every fill and cost assumption.

The primary selection objective is uncertainty-adjusted `EV_net`, subject to the hard activity requirement and all risk/stability gates. Win rate, Sharpe, profit factor, drawdown, tail loss, calibration, and turnover are required diagnostics, not substitutes for EV. Do not maximize a weighted score whose weights were chosen after results.

A stop, target, timeout, add, or early-exit rule may be mathematically derived from training-only first-passage or hazard estimates, but each family receives exactly one promotional management specification frozen before its outer test. Alternative barriers and horizons are charged as separate comparisons and cannot be chosen from the outer-test results.

### Nested chronological estimation

For any fitted model, use rolling-origin nested evaluation:

1. The inner training window may fit coefficients, causal transformations, regularization, calibration, and the one predeclared decision threshold.
2. Purge overlapping event episodes and embargo the boundary by at least the strategy's 30-minute maximum horizon. Never let a future session contribute to a past normalization or model fit.
3. Produce outer-fold predictions and executable trades using only information and fitted objects available before each outer fold begins.
4. Concatenate each once-only outer-fold prediction into the DEV out-of-sample ledger. Do not revisit a consumed outer fold to revise the candidate; a revision becomes a new registered version.
5. After a full DEV pass, refit the exact frozen pipeline on all permitted DEV data, hash it, and open genuinely untouched future validation only once.

Use session/episode block bootstraps or the governing dependence-aware method, never an IID trade bootstrap when signals cluster. Preserve chronological order in all folds. Preprocessing, feature selection, imputation, probability calibration, threshold choice, and regime estimation belong inside the training fold.

### Positive-EV promotion gate

Apply the stricter of the governing master-protocol gates and these requirements. Before any strategy is called a DEV passer, require:

- positive net EV on the concatenated once-only outer predictions at realistic baseline costs;
- a multiplicity-adjusted one-sided 95% lower confidence bound for net EV above zero using the frozen session/episode-block procedure;
- positive net EV under the governing adverse latency/slippage/cost stress, without changing the signal or management rules;
- the existing minimum sample size, at least one independent trade per week, preferred 1.5–2+ weekly, median at least one weekly, and at least 60% of eligible weeks active;
- no dependence on one day, one week, one volatility state, one side, one key level, or the top 1% of trades for the sign of the edge;
- incremental net EV over the identical candle/key-level baseline and simpler order-flow ablations; and
- a locked prospective-validation plan with no post-freeze threshold or model edits.

If the governing protocol already specifies a multiple-testing correction, use it. Otherwise preregister a dependence-aware Romano-Wolf step-down familywise correction at `alpha = 0.05` across every promotional family, model, label, management rule, threshold choice, and autonomous wave tested to date. Report unadjusted estimates too, but never promote from them.

Report a shrinkage estimate toward zero and the bootstrap probability that `EV_net > 0` as diagnostics. They do not override the lower-bound gate. If the sample cannot support a defensible interval, classify the result `INSUFFICIENT_DATA`, not positive EV.

### Regime and interaction discipline

Volatility, time of day, trend, level type, touch count, spread state, and NQ/MNQ lead-lag may condition an edge only when specified before the promotional outer test. Prefer pooled hierarchical or shrinkage interactions over slicing the sample into many small cells. A subgroup may not be rescued from a failed pooled strategy after its result is seen; it becomes a new hypothesis and new validation clock.

Regime models must be causal and deployable. Report state occupancy, transition stability, trades per state, and whether the strategy remains net positive after reasonable state-classification error. A retrospective label such as “trend day” that requires the day's closing information is forbidden at entry time.

## Evidence and attachment audit

The user supplied 11 links representing 10 unique video IDs; `q5DRctM5C-Q` appeared twice. The attachment contains 10 transcript blocks, but it is not a one-for-one match to those 10 linked IDs:

- Eight blocks directly match linked titles: `S2T-cRUnugI`, `q5DRctM5C-Q`, `S1pROkW3XgE`, `YEL79Kpufxo`, `TaY1wePhJ5Q`, `tPgcj4ez3eM`, `5gO9nVJL5IQ`, and `RKV1rncXSkg`.
- The attachment does not contain the identifiable transcript for `Lo7wDgcMLQI` or the Peloton/`PTON` transcript for `1aAY4DlLsdE`.
- It contains two supplemental, unrequested blocks: **Catch EASY Trades by Avoiding this Tape Reading Mistake (with examples)** (searchable as YouTube ID `QXNyxgbrYro`) and **The Secrets of Reading Level 2 (Tape Reading for Beginners)** (no supplied video ID).
- `1aAY4DlLsdE` remains covered by the complete first-party SMB transcript page already reviewed. `Lo7wDgcMLQI` remains description/checklist-level evidence only. Do not represent either as present in the uploaded file.

| Linked video | Evidence now used | Transcript-grounded extraction permitted |
| --- | --- | --- |
| `S2T-cRUnugI` | Complete uploaded transcript, including 31:29 | A displayed/refilling seller is a warning, not an entry; repeated failure to produce the expected move, persistent print speed, and follow-through create the trigger; reduce risk when speed fails |
| `Lo7wDgcMLQI` | First-party description/checklist only; absent from attachment | Pre-filter for an in-play regime and chart location, then inspect Time & Sales speed/size and book state; do not claim its exact spoken thresholds |
| `q5DRctM5C-Q` | Complete uploaded transcript plus first-party article | Spread/depth and liquidity risk, aggressive prints, seller depletion, immediate post-entry confirmation, dip confirmation, and urgent exits when expected response disappears |
| `S1pROkW3XgE` | Complete uploaded transcript | Four exact mistakes: analyzing noise away from key moments; ignoring chart/market/liquidity context; hesitating after a causal trigger; and treating a large print/sweep as meaningful without its subsequent price response |
| `YEL79Kpufxo` | Complete uploaded transcript | Wait at a key level for seller/buyer control to change; refreshing absorption versus true lift; enter before or through the level only with confirmation and sustained control |
| `TaY1wePhJ5Q` | Complete uploaded transcript | Add only to a winning thesis on low-volume pauses/pullbacks or renewed control; do not chase; one-sided tape can justify holding more, but risk remains capped |
| `tPgcj4ez3eM` | Complete uploaded transcript | Cash-open hold/rebid, print acceleration into a break, post-break hold, spread-closing side, repeated-test fatigue, and opening-specific normalization |
| `5gO9nVJL5IQ` | Complete uploaded transcript | Failure to move promptly after a breakout, heavy opposing selling, partial risk reduction, re-entry permission, and a final failed attempt as an exit trigger |
| `1aAY4DlLsdE` | Complete first-party SMB transcript page; absent from attachment | Lack of buying near resistance, cover near known support, no-new-low/control-flip exit, and timeframe-specific management |
| `RKV1rncXSkg` | Complete uploaded transcript, including 1:35 | Visible, refreshing, and hidden liquidity; trade aggressiveness; combined book/prints analysis; and restricting tape reading to in-play moments |

The two supplemental blocks may corroborate or sharpen an already registered mechanism, but they do not create two extra hypothesis families. For any narration not actually available, do not claim the hypothesis reproduces the presenter's rule.

## Supplemental Nour Trades transcript — accepted and rejected transfer

The complete 21:08 transcript for [The Secrets On How To Read Order Flow + Tape](https://www.youtube.com/watch?v=4r_3DNeE8_U) was supplied after the original audit. It is a stock/options lesson using platform-specific share displays, ECNs, and examples such as TSLA, AAPL, AMD, and NVDA. Import only mechanisms that can be expressed from genuine CME NQ/MNQ events; do not copy the presenter's stock thresholds or treat claimed trading success as evidence.

### Valuable concepts accepted into MROF

1. **Context comes before tape.** The transcript begins with higher-timeframe trends, psychological/key levels, and one-hour-or-higher supply/demand zones, then works down toward execution. This corroborates the existing active-level hierarchy and causal one-hour-zone context. It does not authorize tape signals away from those locations or create another zone definition.
2. **Trade side means aggressor location, not buyer-versus-seller existence.** Prints at the ask indicate buyer aggression and prints at the bid indicate seller aggression. Preserve the existing quote-test/aggressor classification and uncertainty rules; never translate screen color directly into side.
3. **Size must be relative to the instrument and time of day.** The useful claim is not “200 shares is large,” but that unusual aggressive executions and displayed depth may matter relative to a causal local baseline. Continue using prior-session time-of-day median/MAD standardization for NQ/MNQ.
4. **A wall must be watched dynamically.** The transcript's “chipping” idea says remaining displayed liquidity, cumulative executed quantity, replenishment, and repeated approaches matter more than the wall's first snapshot. Add causal clearance-rate, remaining-burden, and repeated-approach measurements below.
5. **Clearing a wall is different from sustaining a breakout.** A move may consume the tested wall but lack sufficient same-direction aggression and liquidity support afterward, producing a wick/reclaim. Measure a separate post-clear flow-reserve/acceptance state instead of treating the first trade through as success.
6. **Which quote side chases or concedes may reveal control.** Generalize “bid chasing ask” into a futures-native, event-sequenced BBO migration score that works symmetrically for upward and downward moves and respects NQ's frequent one-tick spread.
7. **Adverse large-print divergence can matter during management.** Repeated unusually large opposing aggressive prints while price is still drifting favorably may precede control decay. Measure this as participant-neutral evidence and compare it with the existing B1/B2 controls; it cannot force a discretionary scale-out.
8. **Tape quality changes by time of day.** The presenter's preference to stop near 11:00–11:30 ET corroborates the already frozen morning window. Do not select a new cutoff from results; report liquidity, event intensity, spread, and feature calibration by the frozen time buckets.

### Claims deliberately not transferred

- Do not use fixed `200`, `500`, or other stock-share filters; learn no threshold from the video's examples.
- Do not multiply CME depth by `100`; that was a stock-platform display convention, not an NQ/MNQ feed rule.
- Do not infer that repeated `90`, `87`, `200`, or other equal-size prints are the same buyer or seller. At most label a participant-neutral `EQUAL_SIZE_PRINT_CLUSTER` diagnostic when raw, unaggregated trade messages support it.
- Do not import ECN/exchange-routing behavior, option implied-volatility claims, stock scanners, or stock-specific candle-volume assumptions into CME futures.
- Do not claim total candle volume is the amount available to consume a wall. Total volume contains both sides and may include activity away from the tested price; use executed-at-level quantity, replenishment, withdrawals, and signed event flow.
- Do not let a displayed wall define a chart level after the fact. It can corroborate a temporary concentration of observable liquidity at an independently preregistered level, but it does not prove that the level is structurally valid or that the wall will remain.
- Do not choose the first, second, or third approach retrospectively. Attempt number and cumulative wall state must be recorded causally; the exact frozen A1-A6 triggers remain controlling.

## Official SMB Capital site refresh — 2026-08-30

The official SMB Training website, its Reading the Tape category/tag archives, and site-indexed material were re-audited for newer discussions of tape reading, Level II/market depth, opening-drive execution, NQ, and MNQ. The accessible official material did **not** surface a newer NQ- or MNQ-specific Level II strategy, a futures-DOM formula, or validated numerical thresholds that can be imported into this wave. The official Reading the Tape category currently surfaces futures-tagged posts through May 2018, while the separate tape tag surfaces recap material through June 2020. Recent 2026 SMB watchlist material mentions equity opening-print, opening-drive, range-break, VWAP, and reactive-scalp ideas, but it does not provide an event-level depth rule or evidence for NQ/MNQ. Record this as `NO_NEW_NQ_MNQ_SMB_RULE_FOUND`, not as missing permission to invent one.

Several official SMB articles not previously formalized in this file add useful **research constraints**, not extra strategy families:

1. **Match tape horizon to trade horizon.** Short-horizon strength or weakness can justify timing, risk reduction, or a scalp, but must not silently overwrite the longer-horizon context supporting a multi-minute trade. Measure both horizons and predeclare how conflict is handled.
2. **Require fast confirmation near the open.** SMB's opening material repeatedly treats a lack of prompt movement through the planned level as deteriorating evidence. The existing 10-second expected-response and early-invalidation rules operationalize this; do not add an outcome-selected grace period.
3. **Exit an opening drive when tape momentum slows.** This is already represented by the frozen persistence/decay measurements and B1 control-decay comparison. It does not authorize discretionary exits or additional decay thresholds.
4. **Use tape to time a contextual setup.** Official SMB material combines tape with levels, technical context, and—when trading stocks—fresh news. For NQ/MNQ, do not copy stock-specific catalyst, float, ECN, or held-bid rules. Any macro-release, overnight-gap, cash-open, volatility, or RVMR condition must be causally defined and preregistered as context.
5. **Automation can reduce reaction delay but cannot create edge.** SMB explicitly notes that computers are faster at pure scalping. Treat this as an execution-design reason to automate a frozen setup, not evidence that the setup has positive EV.

Do not count this source refresh as another hypothesis wave. It corroborates the existing context-first, expected-response, fast-invalidation, and control-decay design. Any genuinely new SMB content found after the audit date must enter a future versioned source memo, be translated into observable futures variables, receive its own variation budget, and be frozen before its outcomes are inspected.

## Transcript-grounded design principles

These are constraints on hypothesis construction, not trading signals by themselves:

1. **Context first.** Do not continuously mine the tape. Activate measurement only at a preregistered key level or event. Middle-of-range order flow is a no-trade control state.
2. **Expected response before observed response.** Every cell must state what price should do after the observed aggression, wall depletion, sweep, or hold. The anomaly is the realized response relative to that frozen expectation.
3. **Intent is not commitment.** Displayed depth can be added or removed. Executed trades, replenishment after execution, and subsequent price movement carry more weight than a standalone wall.
4. **A warning is not a trigger.** A large bidder/seller, a sweep, or a failed first attempt only arms a setup. Entry requires the separately frozen control flip, reclaim, level clear, or continuation event.
5. **Persistence matters.** A burst of print speed that immediately dies is different from speed that persists or accelerates. Measure the sequence; do not describe it by feel.
6. **Repeated tests can weaken a level.** Track touch count, time at level, repulsion after each touch, executed volume, and replenishment. Never assume that more tests make support/resistance stronger.
7. **Management is conditional and rule-based.** Immediate nonconfirmation can cut risk; opposing absorption can protect profit; low-volume pauses can permit one risk-capped add; persistent control can justify a predefined runner. None may be chosen retrospectively trade by trade.
8. **Subjective labels must be normalized.** Terms such as “big,” “fast,” “heavy,” “clean,” and tape scores from −10 to +10 must become causal, instrument- and time-of-day-normalized measurements.

## Critical NQ/MNQ transfer rules

Most examples use individual equities, including lower-float names. Do not copy absolute share sizes, stock spreads, halt behavior, multi-ECN routing, catalyst scores, or stock-specific price offsets into NQ/MNQ.

For CME futures:

- NQ and MNQ reference the same Nasdaq-100 index and share a 0.25-index-point minimum tick, but they are different futures contracts: NQ has a `$20 × index` multiplier and MNQ a `$2 × index` multiplier. Similar price direction does not make their tape, depth, queue, liquidity, fills, or dollar risk interchangeable.
- Normalize size, speed, depth, cancellations, and execution costs separately for each instrument's own time-of-day and volatility distributions. Never apply an NQ size threshold to MNQ or vice versa.
- Treat displayed depth as intent and executed trades as commitment. A large displayed wall alone is not directional evidence.
- Do not label activity as spoofing or manipulation. Measure additions, removals, executions, replenishment, and subsequent price response without inferring intent.
- NQ and MNQ are separate books. Never substitute NQ book states for missing MNQ events or simulate MNQ queue/fills from NQ depth.
- Freeze exactly one primary deployment topology before promotional testing: NQ signal/NQ execution, MNQ signal/MNQ execution, or causally synchronized NQ signal/MNQ execution. If multiple topologies are compared, each is a separate promotional comparison in the multiplicity ledger; do not select the best one after seeing P&L.
- NQ may lead an MNQ execution only when both streams are synchronized causally, the lead/lag relationship is estimated inside training folds, and the MNQ fill model uses genuine later MNQ quotes/depth. Report clock error, signal-to-order delay, missed fills, divergence episodes, and incremental EV versus MNQ-only signals.
- ECN/market-center logic from equities does not transfer directly to the centralized CME Globex book.
- True queue position and order-level iceberg claims require MBO/order identifiers. Event-by-event MBP can support price-level replenishment estimates but not exact order attribution.
- If trade aggressor side is not supplied, associate trades with the contemporaneous BBO using a frozen method and report classification uncertainty. Never trust screen colors as data.

## Preregistered NQ/MNQ level hierarchy and setup geometry

For this wave, use the following exact hierarchy. These locations are candidate context, not evidence of an edge. Their formulas and roles are frozen before order-flow outcomes are opened; no level may be promoted, removed, re-anchored, or given a special threshold because its later P&L looks attractive.

### Active entry-location pool

An A1–A6 or autonomous order-flow signal may become entry-eligible only at one or more of these active locations:

- `YDAY_HIGH` and `YDAY_LOW`;
- `LWEEK_HIGH` and `LWEEK_LOW`;
- `OVERNIGHT_HIGH` and `OVERNIGHT_LOW`;
- `GLOBEX_OPEN`;
- `CASH_OPEN_0930`;
- `SESSION_VWAP`;
- the one already-frozen session-VWAP upper-band formula and lower-band formula;
- `PP`, `M2`, and `M3`.

`PSY_HIGH` and `PSY_LOW` are intentionally handled by the separately controlled module below. They must be tested rather than discarded, but they do not silently join this pooled base-location result because their published forex/crypto weekly-session construction does not map exactly onto CME equity-index futures.

Use one versioned CME exchange calendar, one timezone/DST implementation, and one certified session template for all calculations. Define yesterday and last week from the immediately preceding completed exchange session/week. Define the overnight extremes from the current Globex session open through `09:29:59.999 ET`; at 09:30 they are fixed for this research window. `GLOBEX_OPEN` is the first valid event at the official CME trading-session start; `CASH_OPEN_0930` is the first valid event at or after `09:30:00 ET`. These two opens are not interchangeable. Reset `SESSION_VWAP` at the governing session boundary and never switch between RTH- and ETH-anchored variants after outcomes are seen.

Calculate the pivot family from the preceding completed session:

`PP = (YDAY_HIGH + YDAY_LOW + YDAY_CLOSE) / 3`

`S1 = 2 * PP - YDAY_HIGH`

`R1 = 2 * PP - YDAY_LOW`

`M2 = (PP + S1) / 2`

`M3 = (PP + R1) / 2`

`S1` and `R1` are intermediate calculations only in this wave; they are not active entry locations. PP/M2/M3 enter the preregistered pool because they are a pre-outcome user hypothesis, not because this document claims they outperform R1/S1. Pool the active locations for the primary result and report level-ID results as multiplicity-controlled diagnostics. A profitable-looking level ID cannot rescue a failed pooled family.

The existing A5 EMA-200 trend state remains context under its already-frozen definition. It is not a new Traders Reality level family or a standalone entry trigger here. Any other level from the governing MROF protocol remains context/target information unless a future, separately registered wave makes it active before examining outcomes.

### Context-only state

Calculate and retain the following causal variables, but do not let any of them create an entry by itself:

- `ADR_HIGH`, `ADR_LOW`, `ADR_50_HIGH`, and `ADR_50_LOW`;
- distance already traveled relative to ADR;
- `RUNNING_SESSION_HIGH_t` and `RUNNING_SESSION_LOW_t`, using information available only through time `t`;
- causally confirmed one-hour supply and demand zones under the separately controlled module below;
- the nearest opposing registered level in the proposed trade direction; and
- the number and identities of independent level families clustered near the entry.

Freeze the classical Traders Reality-style ADR variant for this wave. Let `ADR14` be the arithmetic mean of `high - low` over the previous 14 completed exchange sessions, excluding the current session. At time `t`:

`ADR_HIGH_t = RUNNING_SESSION_LOW_t + ADR14`

`ADR_LOW_t = RUNNING_SESSION_HIGH_t - ADR14`

`ADR_50_HIGH_t = RUNNING_SESSION_LOW_t + 0.5 * ADR14`

`ADR_50_LOW_t = RUNNING_SESSION_HIGH_t - 0.5 * ADR14`

`ADR_USED_t = (RUNNING_SESSION_HIGH_t - RUNNING_SESSION_LOW_t) / ADR14`

Do not compare this with the indicator's optional daily-open-anchored ADR inside the same wave. First certify the implementation against the exact saved TradingView indicator settings at no fewer than 100 randomly selected causal timestamps. If it cannot be matched because source settings or session definitions are unavailable, mark the ADR features `UNVERIFIED_CONTEXT` and prevent them from affecting entry, grading, or promotion.

ADR is movement-budget and extension context for RVMR and setup grading. It is not a reversal prediction: reaching ADR does not imply price must turn, and low `ADR_USED_t` does not imply movement must occur.

### Independent level-family clustering

Use the common event eligibility radius as the cluster radius. Count each of the following families at most once, regardless of how many lines from that family overlap:

1. `YDAY_RANGE` — yesterday high/low;
2. `LWEEK_RANGE` — last-week high/low;
3. `OVERNIGHT_RANGE` — overnight high/low;
4. `OPEN` — Globex open and 09:30 cash open;
5. `VWAP` — session VWAP and both frozen VWAP bands collectively;
6. `PIVOT` — PP, M2, and M3 collectively;
7. `ADR` — ADR and 50%-ADR lines collectively; and
8. `RUNNING_SESSION_EXTREME` — current causal session high/low collectively; and
9. `PSYCHOLOGICAL_RANGE` — branch-specific PSY high/low collectively, experimental and unavailable unless its implementation audit passes; and
10. `H1_SUPPLY_DEMAND` — every overlapping causal one-hour supply/demand zone collectively, experimental and unavailable unless its implementation audit passes.

Report `active_family_count` using families 1–6, `all_context_family_count` using families 1–8, `psy_experimental_present`, and `h1_zone_experimental_present` separately. Do not add families 9–10 to either base count unless a future version promotes them after their branches pass. A VWAP, a VWAP band, and a nearly identical alternate VWAP calculation can never count as three confirmations. Nor may PP/M2/M3 count as three independent pivot families, PSY high/low can contribute at most one experimental family, and multiple overlapping one-hour zones can contribute at most one experimental family. A context-only family may strengthen or weaken a calibrated grade only after the frozen interaction validates; it may not make an otherwise ineligible tape event tradable.

### Target-space and A+/A-/B+ grading

At the executable signal time, freeze the structural stop from the applicable Wave A or autonomous-family rule. Exclude levels inside the entry cluster, then find the nearest causally known registered level ahead of the proposed trade. Freeze any dynamic context level at its value at signal time. Define:

`Available_R = distance(entry_price, next_opposing_level) / distance(entry_price, structural_stop)`

Also report a cost-adjusted version using the executable entry estimate, modeled exit cost at the opposing level, commissions, and slippage, but do not replace the transparent ratio above. If no opposing registered level exists before the primary `2R` target, record `Available_R >= 2.0`; never invent empty target space beyond the session or price data.

Apply these preregistered role constraints:

- `Available_R < 0.70`: label `REJECT_GEOMETRY` and do not enter. If this reduces a family below the governing activity floor, that family fails; do not lower the threshold afterward.
- `0.70 <= Available_R < 2.00`: the setup cannot be called A+. It may become A- or B+ only through the training-only, causally calibrated net-EV grading procedure below.
- `Available_R >= 2.00`: the setup is geometrically eligible for A+, but geometry alone is never sufficient.
- If the exact family-specific tape confirmation is absent, weak, internally contradictory, or invalidated, record `NO_TRADE` regardless of available space or level clustering.
- Independent clustering may upgrade a setup by at most one grade only if that frozen interaction adds multiplicity-adjusted, once-only outer-fold net EV. Until then, clustering is diagnostic and cannot change execution.

Derive A+, A-, and B+ from a training-only calibrated prediction of executable `EV_net` and downside risk—not from a discretionary point system or retrospective P&L bins. Freeze the model, grade boundaries, minimum effective sample per grade, and tie handling inside each training fold before scoring its outer fold. Require monotone realized outer-fold EV from B+ to A- to A+, positive stressed net EV for every grade permitted to trade, and sufficient independent events. Otherwise output `UNRATED` or merge grades according to the preregistered sparse-sample rule. Grades remain shadow diagnostics and may not control live size until they pass prospective validation independently; no grade label can override the parent strategy's positive-EV gate.

## Conditional Traders Reality Psychological High/Low module

Do not exclude Psychological High/Low merely because the published indicator describes it for forex and crypto. Implement and test it through the two isolated branches below. The word “psychological” is the source label, not proof of participant psychology, support, resistance, reversal, or positive EV.

### Published reference construction

The published Traders Reality description defines the weekly Psychological High and Low from the first Asian/Sydney-session range beginning during the weekend transition. Its documented implementation uses two completed four-hour bars—an eight-hour window—with Sydney-open/DST handling. Reconstruct the reference variables as:

`TR_PSY_HIGH_w = max(H4_high_1, H4_high_2)`

`TR_PSY_LOW_w = min(H4_low_1, H4_low_2)`

where the two H4 bars are the first two completed bars after the exact frozen weekly Sydney-session anchor. For the forex-reference mode, freeze the indicator's `Forex` setting, its GMT offset, the Sydney DST calendar, broker week/session definition, and bar-stamp convention before reading outcomes. The lines become available only after the second H4 bar closes and remain fixed for the rest of that week. Never make them available earlier in a backtest.

### Branch PSY-NQ-01 — futures-native NQ/MNQ adaptation

Because NQ/MNQ do not trade through the published Saturday-night spot-FX window, define one explicit futures adaptation instead of pretending it is the exact forex line:

`NQ_PSY_HIGH_w = max(high during first 8 tradable hours after official Sunday CME Globex weekly open)`

`NQ_PSY_LOW_w = min(low during first 8 tradable hours after official Sunday CME Globex weekly open)`

Build both values from raw, unadjusted front-contract NQ and MNQ data under the versioned CME calendar. Handle holidays, maintenance gaps, DST, and contract rolls explicitly. The line is unavailable until the complete eight-hour window has elapsed. Do not backfill a missing window, borrow the other contract's price, use a continuous back-adjusted level, or substitute the week's eventual high/low.

Before outcome testing, require deterministic timestamp/session tests, event-to-H4 aggregation checks, exact contract identity, no material gaps in the construction window, and confirmation that the level was fully known before any eligible NY-session signal. If those checks fail, classify the branch `PSY_NQ_UNVERIFIED` or `PSY_NQ_INSUFFICIENT_DATA`; do not approximate it.

When verified, test `NQ_PSY_HIGH` and `NQ_PSY_LOW` as one new `PSYCHOLOGICAL_RANGE` location family. Apply the unchanged A1–A6 order-flow definitions, common proximity rule, execution model, geometry gate, and costs. Each applicable mechanism-by-location cell is registered and charged to multiplicity. First report a pooled PSY-family result; individual high/low, long/short, or weekday results are diagnostics and cannot rescue failure. The base active-location pool remains unchanged, and PSY may join it only in a later version after incremental once-only outer-fold net EV and untouched prospective validation.

Poor NQ/MNQ P&L is a valid tested failure, not a technical “issue” that permits erasing the result or quietly switching markets. A forex branch may still be researched, but it starts a separate registry entry, evidence partition, multiplicity charge, and validation clock.

### Branch PSY-FX-01 — isolated forex option

If the published construction cannot be represented reliably on NQ/MNQ—or if the user separately wants to test its native market—build an isolated forex mode. Freeze exactly one of these routes before inspecting returns:

1. **Preferred for tape/order-flow research: CME EUR/USD futures.** Use `6E` for the primary signal book and `M6E` only as a separately frozen execution topology when genuine M6E quotes/depth are available. This preserves a centralized, sequenced book suitable for trades, BBO, MBP/MBO, OFI, replenishment, and executable fills. Because CME FX futures also have a Sunday open, label its first-eight-tradable-hours range `CME_FX_PSY_ADAPTED`, not the exact weekend spot-FX construction.
2. **Closest to the published forex reference: spot `EURUSD`.** Use one named broker/venue and its exact timestamp/session convention. The published Sydney-anchored `TR_PSY_HIGH/LOW` can be studied as price context. Spot FX has no consolidated global tape or Level II book; broker/ECN depth and aggressor classifications are venue-specific. Unless a complete, licensed venue event stream is supplied and audited, restrict this route to price/level event studies and label it `FX_PRICE_CONTEXT_ONLY`, never full-market order flow.

Do not combine spot EURUSD, 6E, M6E, NQ, or MNQ observations into one sample. Do not calculate a level from one market and claim execution evidence from another without a separately frozen cross-market lead/lag hypothesis and synchronized feeds. Use each instrument's own tick/pip value, session calendar, volatility normalization, fees, spread, depth, latency, and fill model. NQ/MNQ thresholds do not transfer numerically to FX.

For either FX route, repeat the full causal event study, nested chronological evaluation, cost stress, multiplicity control, activity gate, and future-validation process. A positive FX result is an FX strategy; it does not validate Psychological High/Low or order flow on NQ/MNQ.

### Psychological-level routing and clustering

- Always attempt the deterministic PSY-NQ-01 construction audit when the required NQ/MNQ Sunday-session data exists.
- Open PSY-FX-01 only as a separately frozen market study, never as an outcome-selected replacement for a losing NQ/MNQ test.
- Count `PSY_HIGH` and `PSY_LOW` collectively as one `PSYCHOLOGICAL_RANGE` family. They can never contribute two confluence votes.
- Until the relevant branch passes its implementation audit, its PSY levels cannot affect eligibility, target space, RVMR, grading, or clustering.
- After implementation audit but before statistical validation, record PSY proximity and reactions as experimental diagnostics. They may activate only the explicitly registered PSY branch, not the base MROF strategies.
- If neither branch has enough independent weeks or usable market data, return `INSUFFICIENT_DATA`; do not manufacture weekly levels.

## Causal one-hour supply/demand-zone context module

Add this module because a higher-timeframe price area may contain useful location, obstacle, and regime information for a short-horizon tape setup. Do not assume the discretionary labels “supply” and “demand” identify institutional orders or positive EV. The module must convert them into reproducible intervals known only after objective confirmation.

This is an additive pre-outcome revision. If an earlier engine/freeze commit already exists, preserve it permanently and create a new versioned successor such as `MROF-YT-OF-01.1`; never amend, delete, or disguise the predecessor. Hash this module, its tests, and the resulting full specification before attaching the recorder or inspecting market outcomes. Prior deterministic test counts do not cover this new module. If any outcomes were already opened, register this as a new hypothesis wave and do not reuse that exposed period as untouched validation.

### Hourly-bar construction and data gate

- Build completed 60-minute bars from raw, unadjusted contract events under the versioned CME session calendar, aligned from the official `18:00 ET` Globex session start in consecutive one-hour intervals while the market is open. Handle DST, holidays, maintenance breaks, and partial sessions explicitly.
- A forming hourly bar is never available. Store open/close timestamps and the last raw event included in every bar; prove that no event with a later timestamp entered it.
- Under the frozen NQ-signal/MNQ-execution topology, construct zones from the genuine NQ signal contract and use genuine later MNQ quotes/depth for fills under the governing synchronized mapping. Under an MNQ-only topology, construct them from MNQ. Never substitute one book or contract for missing data from the other.
- Require exact individual contract identity and unadjusted prices. At a contract roll, close all predecessor-contract zones as `ROLLED_OFF`; do not carry an absolute zone through a roll or derive it from a back-adjusted continuous series.
- Existing hourly OHLCV may support this module only when its contract, session, timestamp, aggregation, and price basis are certified. Otherwise label the entire module `H1_ZONE_UNVERIFIED_CONTEXT` and prevent it from affecting entries, target space, grades, stops, or promotion.

For completed hourly bar `h`, define:

`TR_h = max(H_h - L_h, abs(H_h - C_(h-1)), abs(L_h - C_(h-1)))`

`body_fraction_h = abs(C_h - O_h) / (H_h - L_h + epsilon)`

Standardize `TR_h` causally against the previous 20 completed sessions for the same one-hour session slot using the existing median/MAD method. Denote the result `TR_z_h`. Do not use current-session or future bars in that baseline.

### One frozen base-and-displacement definition

Do not compare multiple visual definitions. Use exactly this deterministic construction for the primary context test:

1. A **compact base bar** has `TR_z <= 0.0` and `body_fraction <= 0.60`.
2. Immediately before a prospective displacement bar, walk backward through consecutive compact bars. Require at least one and use the most recent maximum of three. If more than three qualify, retain the most recent three and record the longer-run count as a diagnostic; do not select a different subset from outcomes.
3. Let `BASE_HIGH`, `BASE_LOW`, and the base-body extrema come only from those frozen base bars. Let `PRIOR_SWING_HIGH` and `PRIOR_SWING_LOW` be the maximum high and minimum low of the five completed hourly bars immediately preceding the base.
4. A **demand-forming displacement** is the immediately following completed hourly bar with `TR_z >= 2.0`, `body_fraction >= 0.60`, `C > O`, and a close at least one instrument tick above both `BASE_HIGH` and `PRIOR_SWING_HIGH`.
5. A **supply-forming displacement** is the exact mirror: `TR_z >= 2.0`, `body_fraction >= 0.60`, `C < O`, and a close at least one tick below both `BASE_LOW` and `PRIOR_SWING_LOW`.
6. If neither complete condition holds, create no zone. Do not rescue a near miss with discretionary chart interpretation, volume, later price response, or an alternative swing length.

The zone becomes causally available only at the displacement bar's close:

- Demand zone interval: `DEMAND_DISTAL = min(base lows)` through `DEMAND_PROXIMAL = max(max(open, close) for each base bar)`.
- Supply zone interval: `SUPPLY_PROXIMAL = min(min(open, close) for each base bar)` through `SUPPLY_DISTAL = max(base highs)`.

Require positive width and valid price ordering. Store a deterministic zone ID containing instrument, contract, base timestamps, direction, boundaries, displacement timestamp, and specification version.

### Zone lifecycle, freshness, and overlap

- `FRESH`: no later trade event has entered the closed interval after the zone became available.
- `TOUCHED`: price enters the interval after availability. Increment independent touch count only after price first leaves and travels at least `max(zone_width, 4 ticks)` away before re-entry; ordinary tick-by-tick chattering is one touch.
- For every touch, record time to touch, maximum penetration as a fraction of zone width, dwell time, executed volume, tape/control state, maximum 10s/60s/180s rejection, and whether price accepts through the interval.
- `INVALIDATED`: a completed causal one-hour bar closes at least one tick beyond the distal boundary—below demand or above supply. Record intrabar distal breaches separately but do not use a future hourly close early.
- `ROLLED_OFF`: the signal contract changes. Do not automatically convert a broken supply zone into demand or vice versa; a role-reversal zone is a separate future hypothesis.
- Do not impose an outcome-selected maximum age. Retain formation age in hours/sessions and track the nearest fresh and nearest active zone of each direction. Age and touch count are diagnostics until separately validated.
- Preserve every overlapping zone ID, but treat the full collection as one `H1_SUPPLY_DEMAND` family for confluence. Multiple nested or overlapping hourly zones never create multiple confirmation votes.

### Role in MROF tape scalping

In this revision, an hourly zone is **context, not an independent entry trigger**. The original active-location pool and A1–A6 tape requirements remain controlling. A tape event occurring only at an hourly zone and away from every active base location remains `NO_TAPE_SIGNAL` for the primary wave.

For every otherwise eligible tape event, causally label exactly one of the following. Evaluate `H1_ZONE_CONFLICT` first whenever both directions overlap; otherwise assign the applicable aligned, opposing, or no-zone state:

- `ALIGNED_H1_ZONE`: long at/within the common eligibility radius of active demand, or short at/near active supply;
- `OPPOSING_H1_ZONE`: long at/near active supply, or short at/near active demand;
- `H1_ZONE_CONFLICT`: active supply and demand intervals both overlap the event radius; or
- `NO_H1_ZONE`.

Store zone direction, distance to proximal/distal boundaries, width in ticks and hourly ATR units, age, freshness, touch count, penetration history, formation `TR_z`, displacement-body fraction, swing-break distance, and every overlapping base level family. “Fresh,” “strong,” “institutional,” and “high quality” cannot be hand labels.

Calculate a diagnostic `Available_R_H1` using the first proximal boundary of the nearest active opposing hourly zone in the proposed trade direction. Freeze the zone values at signal time. The existing base `Available_R` and `0.70R` execution gate remain primary. Test a separately registered `H1_GEOMETRY_ABLATION` that uses the nearer of the base opposing level and opposing hourly zone; it cannot change execution or rescue the parent unless it adds multiplicity-adjusted, once-only outer-fold net EV and later passes prospective validation.

Likewise, hourly-zone alignment cannot upgrade A+/A-/B+, alter size, widen or tighten the structural stop, or create a target until the exact training-only interaction validates. The original structural stop remains controlling; a zone's distal edge may be reported as a diagnostic stop candidate only. Any future zone-only entry, distal-edge stop, role reversal, refined zone boundary, alternative base length, or alternate displacement threshold is a new frozen family with a new multiplicity charge.

### Required one-hour-zone tests and falsification

Extend the deterministic suite before data attachment. At minimum prove:

1. incomplete hourly bars never form a base, displacement, zone, touch, or invalidation;
2. all median/MAD inputs precede the candidate bar and use the matching session slot;
3. demand and supply constructions are exact mirrors;
4. the five-bar structural break excludes the base and displacement bars;
5. zone boundaries match the frozen body/wick formulas;
6. availability begins only at the displacement close;
7. repeated tick entries without the required retreat remain one touch;
8. completed-bar invalidation has no intrabar lookahead;
9. overlapping zones retain their IDs but contribute one family vote;
10. contract rolls retire zones and continuous-price adjustments cannot leak into them;
11. `Available_R_H1` uses only zones known at the signal timestamp; and
12. disabling the module reproduces the predecessor engine's signals and fills bit-for-bit.

The promotional context comparison is the unchanged parent signal versus that same signal with the one frozen hourly-zone interaction. Also compare the zone definition against a simpler causal five-bar hourly swing-high/low context so a generic recent extreme does not receive credit as a special supply/demand effect. Match non-zone controls by time of day, volatility, trend, distance to the original active level, and touch count. Report `NO_INCREMENTAL_H1_ZONE_EDGE` when the context adds no stable net EV.

## Required raw data

Use synchronized, loss-audited raw events with exchange timestamp when available, local receive timestamp, sequence/order information when available, exact contract identifier, unadjusted price, trade price/quantity, contemporaneous BBO, and ten levels of depth. Preserve the raw event stream and derive 1s, 5s, 10s, 30s, 1m, 3m, 5m, 10m, 15m, 1h, 4h, and daily states causally.

If the feed lacks event actions or reliable sequencing, mark cancellation, replenishment, resiliency, and queue-dependent cells `INSUFFICIENT_DATA`. Do not synthesize those fields from candles or interpolate missing depth.

## Causal feature dictionary

For trade event `i`, let `s_i = +1` for buyer-aggressed and `-1` for seller-aggressed, `q_i` be quantity, `m_t` the midquote, and `tick` the NQ tick size. For a backward-looking window `w`:

1. **Aggressor delta**

   `D_w = sum(s_i * q_i)` and `d_w = D_w / (sum(q_i) + epsilon)`.

2. **Tape intensity and acceleration**

   `lambda_w = trade_count_w / w`, `Q_w = traded_quantity_w / w`, and acceleration is the log ratio of the current 2s or 10s intensity to its immediately preceding equal-length window.

3. **Price response**

   `r_w = (m_t - m_(t-w)) / tick`.

4. **Flow-response efficiency / absorption**

   `eta_w = sign(D_w) * r_w / (abs(D_w) + epsilon)`. Strong signed flow with small or adverse signed price response is absorption/nonresponse.

5. **Expected-response residual**

   Fit only on prior data a frozen, simple robust model for 10s signed price response using signed flow, intensity, three-level book imbalance, realized volatility, distance to level, and minute-of-day. The anomaly is the out-of-sample residual. Do not use a high-capacity model in this first wave.

6. **K-level book imbalance**

   `BI_k = (sum_bid_depth_1_to_k - sum_ask_depth_1_to_k) / (sum_bid_depth_1_to_k + sum_ask_depth_1_to_k + epsilon)`, with `k = 3` frozen for the primary test. Levels 1 and 10 are diagnostics only.

7. **OFI**

   Compute event-level order-flow imbalance using the frozen BBO/MBP definition already governing MROF. Do not switch OFI formulas after results are seen.

8. **Replenishment ratio**

   At a tested price level, `RR = depth_added_after_execution / (executed_quantity_at_level + epsilon)` during the 10s observation window.

9. **Depletion ratio**

   `DR = executed_quantity_at_level / (initial_displayed_depth + added_depth + epsilon)`, paired with whether the level actually clears and remains cleared.

10. **Non-trade withdrawal / liquidity vacuum**

    Measure depth removed without matched executions, separately for bid and ask, over 2s and 10s. Do not call this cancellation if the feed cannot identify event actions.

11. **Book resiliency**

    Measure time until 50% of depleted three-level depth is restored. Right-censor episodes that do not recover inside 30s.

12. **Control score**

    Use an equal-weight, frozen composite of robustly standardized aggressor delta, OFI, three-level book imbalance, and signed price response. Do not fit weights to P&L in this wave.

13. **Flow persistence and decay**

    For four consecutive non-overlapping 2.5s subwindows inside the 10s decision window, record signed aggressor quantity, trade count, and OFI. Define persistence as the fraction sharing the event direction and decay as the final-to-first absolute intensity ratio. The primary persistence condition is at least three of four subwindows in the same direction; do not search alternative run lengths.

14. **Sweep-response and reclaim**

    A sweep is a same-direction sequence that consumes at least three consecutive price levels inside one second. Record levels consumed, quantity, maximum immediate price progress, five-second follow-through, and whether price reclaims the pre-sweep inside five seconds. A sweep alone is never a signal; its response is the feature.

15. **Level-test sequence**

    For approaches separated by at least a two-tick retreat, record touch count within 120s, dwell time within two ticks, executed quantity, added and removed depth, maximum repulsion during the next 10s, and the change in repulsion from the previous touch. This makes “it tested again and should have moved” measurable.

16. **Spread-response dominance**

    When the inside spread widens above its causal 95th percentile, measure whether bids move up or offers move down to close it, time to closure, and the signed midquote change. This is opening-regime and execution context; it is not a standalone entry family.

17. **Pause/pullback quality**

    After a directional move, measure retracement in ticks, adverse aggressive quantity, total quantity and event count relative to the immediately preceding impulse, duration, and whether same-direction control reappears before the structural level fails. “Low-volume pause” means total quantity no greater than 50% of the preceding equal-duration impulse and no adverse-flow `z >= 1.0`; no alternative cutoffs may be searched in this wave.

18. **Multi-horizon tape alignment**

    Compute the same signed-flow, OFI, control, and price-response components over the frozen 10s entry horizon and trailing 60s and 180s context horizons. Label alignment, short-horizon opposition, and full reversal without fitting horizon weights to P&L. For A1–A6 this is a diagnostic and management input only where an existing frozen rule uses it; it may not become a post-result entry filter. A separately tested interaction requires a future preregistered family.

19. **Cash-open shock and normalization**

    Treat 09:30:00 ET as the U.S. equity cash-open shock, not the start of the CME futures session. Record the 09:29:30–09:29:59 pre-open book/flow state and, in fixed non-overlapping 10s windows after 09:30:00, the jump in event intensity, aggressor delta, spread, three-level retained depth, replenishment, signed price response, and time for spread/depth/intensity to return inside the prior-session matching-bucket interquartile range. These measurements are A6 diagnostics unless a later family preregisters an exact use; do not choose the most profitable post-open window retrospectively.

20. **Level identity and independent clustering**

    At every candidate event, store all active and context level IDs, signed distance in ticks, normalized distance in ATR units, family ID, nearest-level identity, `active_family_count`, and `all_context_family_count`. Use the frozen family map above, count each family once, and preserve the complete set rather than relabeling the event with whichever line later has the best outcome.

21. **ADR movement-budget state**

    Store `ADR14`, all four causal ADR lines, `ADR_USED_t`, signed distance to each line, and whether price is inside or beyond each 50%/100% boundary. ADR variables are context for RVMR, extension, and grade calibration only; do not infer direction or time-to-move from ADR alone.

22. **Target-space geometry**

    Store executable entry, structural stop, stop distance, next-opposing-level ID/family, opposing-level distance, transparent `Available_R`, cost-adjusted available R, and the exact reason for `REJECT_GEOMETRY`. Recompute none of these from future extrema or post-entry line movement.

23. **Psychological weekly range**

    Store branch ID, market/instrument, source versus adapted construction, weekly anchor timestamp, DST state, both component H4 bars or eight-hour event range, completion timestamp, `PSY_HIGH`, `PSY_LOW`, signed distance to each, touch/rejection/acceptance state, data-quality status, and whether the level was legally available at signal time. Keep PSY features null before completion and when the branch audit fails.

24. **Causal one-hour supply/demand-zone state**

    Store the complete formation equation inputs and lifecycle required by the hourly-zone module: certified hourly-bar timestamps, causal `TR_z`, body fractions, base run and boundaries, prior five-bar swing, displacement and break magnitude, zone ID/direction/bounds/width, availability time, freshness, independent touches, penetration, dwell, age, invalidation or roll-off reason, signed distance, overlap IDs, event-context label, `h1_zone_experimental_present`, and diagnostic `Available_R_H1`. Keep every field null when the construction or contract data fails certification.

25. **Key-level wall episode and hold/flush state**

    At each eligible active-level approach, store the key-level ID, approach direction, blocking side, wall price, wall-size `z`, initial and maximum displayed quantity, executed quantity, added quantity, non-trade removed quantity, remaining quantity, reconciliation error, wall lifetime, refill count, `RR`, `DR`, flow persistence, price progress, state-transition timestamps, forecast snapshot time, `P_FLUSH`, `P_HOLD_OR_RECLAIM`, `P_UNRESOLVED`, data-quality label, and exact state reason. MBP observations must use `REFILLING_LIQUIDITY_ESTIMATE`; reserve order-level language for fields genuinely supported by MBO and never infer participant identity.

26. **Wall-clearance dynamics and repeated-approach memory**

    For causal windows `w in {2s, 10s}`, calculate execution-only clearance velocity `V_exec_w = (executed_at_wall_w - added_at_wall_w) / w` and total disappearance velocity `V_all_w = (executed_at_wall_w + nontrade_removed_at_wall_w - added_at_wall_w) / w`. Keep them separate. When `V_exec_w > 0`, calculate diagnostic `T_clear_exec_w = remaining_display / V_exec_w`; otherwise right-censor it as non-clearing rather than emitting infinity or a favorable value. Define `WALL_BURDEN_10 = remaining_display / (expected_break_direction_aggressive_quantity_10s + epsilon)`, where the expectation is fit only from prior matching time-of-day training data. Across independently separated approaches to the same frozen wall price within 120s, store cumulative executed, added, non-trade removed, remaining/recovered display, maximum retreat, and attempt number. Never interpret this aggregate memory as proof of one continuing participant.

27. **Post-clear flow reserve and acceptance**

    After a wall first clears, store a completed five-second, break-direction-signed composite of aggressor delta, OFI, quote migration, opposing three-level replenishment, retained depth, and executable price acceptance beyond the level. Freeze equal component weights before outcomes; do not fit them to P&L. Store `POST_CLEAR_RESERVE_5`, time spent beyond the level, maximum favorable/adverse excursion, whether the original wall rebuilt, and the nearest next blocking depth. These are unavailable until the five-second window completes and can never leak into a precontact, contact, or first-cross forecast.

28. **Futures-native quote migration / chase score**

    Classify event-sequenced BBO transitions rather than relying on a visual impression. A buyer-led upward step requires buyer-aggressed execution at the old ask, an ask lift, and a higher bid re-established before the offer returns to the old ask; a seller-led downward step is the exact mirror. Separately count unforced ask concessions toward the bid and bid concessions toward the ask. Over 2s and 10s, compute a signed normalized `QUOTE_MIGRATION_SCORE` from buyer-led upward versus seller-led downward steps, concession direction, and censored/unmatched sequences. Handle one-tick spreads explicitly and require exact long/short symmetry. This extends spread-response dominance beyond only unusually widened spreads; it is not a standalone entry family.

29. **Large-print polarity divergence and equal-size clustering**

    Define a large NQ/MNQ trade only by causal robust trade-size `z >= 2.0` in the prior-session matching time bucket. For a live position direction `p in {-1,+1}`, calculate `ADVERSE_LARGE_PRINT_SHARE_w = -p * sum(s_i*q_i*I[z(q_i)>=2]) / (sum(q_i*I[z(q_i)>=2]) + epsilon)` and record its count, maximum size `z`, interarrival times, and persistence across the existing four subwindows. Also store participant-neutral equal-size recurrence, side consistency, and interarrival clustering when raw trade messages support them. Never call equal-size prints one buyer, one seller, an institution, or an iceberg; aggregation and multiple participants can generate the same pattern. These measurements are diagnostics for B1/B2 and the autonomous lane until a separately frozen comparison proves incremental value.

All standardization must be causal. Except where the hourly-zone module explicitly requires its same one-hour session slot, use a robust median/MAD baseline from the previous 20 completed sessions within the same five-minute time-of-day bucket. Do not include the current or future session in any baseline.

## Key-level wall hold-versus-flush decision engine

Implement an explicit causal decision layer that asks one narrow question when price approaches a preregistered active key level:

> Is observable liquidity and tape behavior presently more consistent with the level holding/rejecting, flushing through, failing a flush and reclaiming, or remaining unresolved?

This is a probabilistic classification and confirmation engine, not a promise that price will hold or break. A displayed wall alone is never confirmation. It may be executed, replenished, canceled, moved, partially hidden, or irrelevant. The layer must combine Time & Sales, BBO, Level II changes, and realized price response. It must emit `UNCERTAIN_NO_TRADE` rather than invent certainty when sequencing, event actions, or reconciliation are inadequate.

### Wall selection and event accounting

- Run the engine only inside the common active-level proximity window. A visually large order in the middle of the range remains context only and cannot create a signal.
- Use `b = +1` for an upward approach through a resistance/sell wall and `b = -1` for a downward approach through a support/buy wall. Sign all flow, OFI, depth change, and price response into this proposed break direction so long/short logic remains exactly symmetric.
- On first entry into the proximity window, define `wall_price` as the largest causally standardized displayed quantity on the blocking side within two ticks of the key level, requiring robust time-of-day `z >= 2.0`; ties go to the price nearest the key level. Freeze that price for the episode. Do not chase a later wall to whichever price explains the outcome best.
- One approach episode begins at first proximity entry and receives at most one precontact snapshot and one first-contact snapshot. Re-arm only after the existing two-tick retreat requirement creates a new independent approach. Preserve overlapping level IDs without duplicating one physical episode into several trades.
- Reconcile every supported wall update as:

  `initial_display + added - executed - nontrade_removed = remaining_display + reconciliation_error`

  Use exchange sequence and action fields when available. Freeze a data-quality tolerance before ingestion testing. If the tolerance fails, events are missing, or execution cannot be distinguished from removal, classify the episode `UNCERTAIN_NO_TRADE`; do not force it into depletion or withdrawal.
- With MBP, call repeated display after executions a `REFILLING_LIQUIDITY_ESTIMATE`, not a confirmed iceberg, hidden buyer, hidden seller, or single participant. MBO/order IDs may support order-level mechanics when genuinely present, but neither MBP nor MBO proves owner identity, intent, or spoofing.

### Causal state machine

The state at timestamp `t` may use only events available by the latency-adjusted local receive time at `t`:

1. `NO_QUALIFYING_WALL`: no blocking-side wall meets `z >= 2.0`. This does not block A4, which can detect expected-response failure without a wall.
2. `WALL_OBSERVED`: a qualifying buy or sell wall exists, but executions and price response have not established hold or flush behavior. This state cannot enter a trade.
3. `HOLD_ARMED`: aggressive flow toward the wall has `z >= 2.0`, ten-second progress in the break direction is no greater than one tick, and same-level `RR >= 1.5`. The wall is absorbing/refilling in observable aggregate terms, but this state still cannot enter.
4. `HOLD_CONFIRMED`: `HOLD_ARMED` is followed by opposing OFI/control `z >= 1.0` and at least a one-tick retreat from the wall. This is the A1 confirmation map; execute only when every other frozen A1 and common rule is also satisfied.
5. `FLUSH_ARMED_EXECUTION`: executed quantity reaches at least `1.5 × initial_display`, `RR < 0.25`, the wall is being depleted, and at least three of four persistence subwindows agree with the break direction, but the required post-clear hold has not completed. This state is an alert, not a new entry rule.
6. `FLUSH_ARMED_WITHDRAWAL`: target-side three-level depth falls at least 60% inside two seconds without matched executions while opposite-side depth falls no more than 20%, but post-level acceptance is not yet confirmed. This maps to the observable precursor in A3 and must remain unavailable when removal cannot be classified.
7. `FLUSH_CONFIRMED`: price has crossed the key level by at least one tick, the tested wall has cleared and stayed cleared for five seconds, at least three of four persistence subwindows agree with the break direction, same-direction OFI/control is `z >= 1.0`, and no opposing replenishment reaches `z >= 1.5`. This is a post-break confirmation map for A2/A6, not permission to fill retrospectively at the break price.
8. `FAILED_FLUSH_RECLAIM`: price crosses or a three-level sweep occurs, then price reclaims the key level or pre-sweep price within five seconds while opposing OFI/control reaches `z >= 1.0`. This is the A4 confirmation map when all other A4 conditions hold.
9. `UNCERTAIN_NO_TRADE`: inputs are incomplete, accounting does not reconcile, withdrawal versus execution is indeterminate, or hold and flush evidence conflicts without reaching a frozen confirmation state.

An armed state may appear before a move, but it is not proof and cannot submit an order on its own. A confirmed state necessarily occurs after its required evidence and therefore must use the first executable quote after confirmation plus the frozen latency. Never backdate an entry to the wall touch, level cross, sweep, or first print.

The transcript-derived `V_exec`, `T_clear_exec`, `WALL_BURDEN`, attempt memory, `QUOTE_MIGRATION_SCORE`, and post-clear reserve are mandatory diagnostics for every applicable episode. They do not add an unstated A2 threshold, permit an anticipatory fill, or authorize choosing the attempt number after results. Any use as a fitted decision variable occurs only inside the registered probability model or a later separately frozen strategy version.

### Before-the-move probability forecasts

For every independent approach, log strictly causal probability snapshots at (a) first entry into the proximity band while price remains at least one tick from the level and (b) first contact with the wall/key level. The first-contact snapshot is the primary research forecast; the precontact snapshot is a separately reported diagnostic and cannot rescue a failed primary model.

At horizons `h in {5s, 10s, 30s}`, estimate:

- `P_FLUSH_h`: probability that a qualifying cross-and-five-second-hold completes by `h`;
- `P_HOLD_OR_RECLAIM_h`: probability that a one-tick rejection or reclaim with opposing control occurs before a qualifying flush by `h`; and
- `P_UNRESOLVED_h = 1 - P_FLUSH_h - P_HOLD_OR_RECLAIM_h`.

Start with session-blocked empirical rates and a parsimonious training-only multinomial/logistic or generalized additive baseline using wall size, executed-versus-removed quantity, `RR`, `DR`, causal `V_exec`, right-censored `T_clear_exec`, `WALL_BURDEN`, quote migration, tape intensity, aggressor delta, OFI, three-level imbalance, spread, approach velocity, touch count, distance to level, time of day, volatility/RVMR state when causally available, and level-family context. Post-clear reserve is forbidden from precontact/contact models because it does not yet exist. Open a competing-risk survival model for time to flush versus hold/reclaim only after the effective sample supports it and the simpler model remains the benchmark. Any threshold, interaction, horizon use, calibration method, or model class is selected inside the nested chronological training process and charged to multiplicity.

Evaluate probabilistic forecasts with once-only outer-fold Brier score, log loss, reliability curves, calibration error, class frequency, and decision-curve/net-EV analysis. AUC or accuracy alone cannot promote. Until the probability model adds stable, multiplicity-adjusted out-of-sample executable EV and then survives untouched prospective testing, expose its probabilities in research/shadow output only; the exact A1-A6 rules remain the sole entry authority.

The live/shadow record for each level must display at minimum:

`LEVEL_ID | WALL_SIDE | WALL_Z | EXECUTED | ADDED | NONTRADE_REMOVED | REMAINING | V_EXEC | T_CLEAR_EXEC | WALL_BURDEN | ATTEMPT | QUOTE_MIGRATION | POST_CLEAR_RESERVE | P_FLUSH_5/10/30 | P_HOLD_5/10/30 | STATE | DATA_QUALITY | REASON`

Do not use these outputs to upgrade an A+, A-, or B+ grade until a separately frozen grade-interaction test proves incremental outer-fold net EV and later passes prospective validation.

### Integration and deterministic tests

This decision layer unifies the observable evidence already used by A1-A4 and A6; it is not a seventh Wave A family. `HOLD_CONFIRMED` may authorize only the matching frozen A1 conditions, `FLUSH_ARMED_WITHDRAWAL` may authorize only the existing A3 timing, `FLUSH_CONFIRMED` may authorize only the matching A2/A6 conditions at the first later executable quote, and `FAILED_FLUSH_RECLAIM` may authorize only matching A4. Preserve every original rule where this descriptive mapping is narrower or later.

Before attaching outcome data, add deterministic tests proving:

1. upward-resistance and downward-support episodes are exact signed mirrors;
2. a large displayed wall with no qualifying executions cannot become absorption or `HOLD_CONFIRMED`;
3. executed depletion and non-trade removal route to different states;
4. wall accounting reconciles additions, executions, removals, and remaining display event by event;
5. missing actions, sequence gaps, or excess reconciliation error force `UNCERTAIN_NO_TRADE`;
6. MBP never emits a participant identity, confirmed iceberg, hidden buyer/seller, or spoof label;
7. `WALL_OBSERVED`, `HOLD_ARMED`, and both `FLUSH_ARMED` states cannot submit orders;
8. `FLUSH_CONFIRMED` cannot occur until the causal five-second post-clear requirement completes;
9. a cross/sweep followed by the frozen five-second reclaim routes to `FAILED_FLUSH_RECLAIM`, not continuation;
10. precontact and contact forecasts contain no feature timestamp later than their snapshot receive time;
11. each independent approach generates at most the frozen snapshots and cannot be duplicated by overlapping level labels;
12. probability transformations, calibration, and thresholds fit only on prior training folds and all three probabilities sum to one within tolerance;
13. walls outside an eligible active-level window cannot produce a primary-wave entry; and
14. disabling this layer reproduces the predecessor engine's signals, timestamps, fills, and P&L bit-for-bit;
15. execution chipping and non-trade removal remain separate across repeated approaches and cancellations never count as executions;
16. `T_clear_exec` is right-censored whenever net execution clearance is nonpositive and cannot produce a divide-by-zero promotion;
17. post-clear reserve and any event after a forecast snapshot are absent from that snapshot's feature vector;
18. synthetic buyer-led upward and seller-led downward quote migrations produce exact mirrored scores, including one-tick-spread cases;
19. equal-size print clusters never emit participant, institution, hidden-order, or spoof labels; and
20. stock-platform share multipliers, fixed share filters, ECN fields, and option variables cannot enter an NQ/MNQ feature pipeline.

## Common event and execution rules

- Respect the existing frozen MROF trading window. If none exists, use 09:30:00–11:30:00 ET.
- Candidate events must occur at or within `max(4 ticks, 0.20 × ATR(20) on completed 1m bars)` of a causally available key level.
- Use the exact active entry-location pool and level-family map in the preregistered hierarchy above. Pool it rather than selecting whichever level later performs best. Other governing levels, EMA-200, ADR, running session extrema, experimental PSY levels, and causal one-hour zones remain context or target information unless an existing frozen family or separately registered module explicitly assigns them a narrower role.
- Treat all periods outside an eligible level/event window as the explicit `NO_TAPE_SIGNAL` control state. Do not search the full session for visually interesting book sequences.
- Before results are viewed, every family must state its expected immediate price response, maximum time allowed for that response, and exact observation that invalidates it.
- If several key levels overlap, apply the frozen level-precedence rule already in MROF. If none exists, label the event with every overlapping level, use distance to the nearest level for eligibility, and do not select a level label after seeing P&L.
- Use raw events for detection and a completed 10s decision window unless a hypothesis explicitly uses a 2s withdrawal trigger.
- Enter at the first executable NQ/MNQ quote after the existing frozen latency. If no latency is frozen, use 150 ms base latency and report 300 ms and 500 ms as non-rescuing stress tests.
- No same-event or same-window fills. Respect queue, available quantity, partial fills, commissions, exchange fees, spread, and slippage.
- Primary Wave A protective stop: beyond the event-window extreme plus `max(2 ticks, 0.10 × ATR(20) on completed 1m bars)`. Primary target: `2R`.
- Calculate target-space geometry before entry and reject `Available_R < 0.70` exactly as specified above. Do not move the opposing level, structural stop, or grade boundary after the trade begins.
- Mandatory early-invalidation exit: at the first executable quote after the first completed 10s post-entry window when favorable excursion is less than one tick and fewer than three of four persistence subwindows agree with the trade direction. A family with an explicitly preregistered 2s invalidation exits on that 2s rule rather than waiting for 10s.
- Mandatory later control-loss exit: after initial confirmation, exit at the first executable quote following any completed 10s window in which opposing control reaches `z >= 1.0` and price crosses the entry price against the position. Otherwise exit at the stop, `2R`, or the 30-minute hard cap—whichever occurs first. Do not tune any horizon after viewing outcomes.
- Permit one position at a time. Long and short rules are exact mirrors and form one pooled, symmetric primary family. Direction-specific results are diagnostics unless separately preregistered and charged to multiplicity.
- Primary endpoint: net expectancy of the executable fixed-rule trade. Secondary, non-promotional diagnostics: signed midquote markouts at 1s, 5s, 10s, 30s, 60s, and 180s.
- Never convert a screen color directly into aggressor side, infer participant identity from a refresh, or label an order as spoofing. Record observable events and classification uncertainty only.

## Wave A — six frozen entry families

### A1. Replenishing-wall absorption reversal

At a predeclared resistance/support level, require:

- aggressive flow toward the level with causal robust `z >= 2.0`;
- price progress in that direction no greater than one tick during 10s;
- same-level replenishment `z >= 1.5`;
- at least two separate approaches to the level within 60s; and
- trigger from an opposing OFI/control-score flip with a one-tick retreat from the level.

Trade away from the absorbing side. This is the measurable version of a hidden/refilling seller or buyer—not a claim about participant identity.

### A2. Displayed-wall depletion continuation

At a predeclared level, require:

- displayed depth at the tested level with causal robust `z >= 2.0` before contact;
- executed quantity at the level at least 1.5 times the initially displayed quantity;
- replenishment ratio below 0.25;
- the level clears and stays cleared for five seconds; and
- at least three of four flow-persistence subwindows agree with the break direction;
- same-direction OFI/control score `z >= 1.0` after clearing.

Trade through the depleted level. A wall that disappears without execution belongs to A3, not A2.

### A3. Non-trade withdrawal and liquidity-vacuum continuation

Require target-side depth within the nearest three levels to fall by at least 60% inside two seconds without matched executions, while opposite-side three-level depth falls by no more than 20%, followed by same-direction aggressor delta `z >= 1.0` and a one-tick price advance. Trade in the direction of the vacuum.

This family is unavailable unless the feed can distinguish or defensibly infer non-trade removals.

### A4. Ten-second expected-response failure reversal

At a predeclared level or attempted breakout:

- same-direction aggressor delta or tape intensity has causal robust `z >= 2.0`;
- the 10s expected-response residual is in the adverse 5% tail or realized progress is no more than one tick;
- price returns through the tested level, or a three-level sweep reclaims its pre-sweep price inside five seconds; and
- opposing OFI/control score reaches `z >= 1.0`.

Fade the failed move. This family does not require a displayed wall or measured replenishment and is therefore distinct from A1.

### A5. Pullback absorption and trend resumption

Define trend context causally using the already-frozen MROF multi-timeframe state; do not search alternative trend filters. During a pullback into one of the active entry locations in the preregistered hierarchy, require adverse aggressor delta `z >= 2.0`, adverse price progress no greater than one tick during 10s, same-side replenishment `z >= 1.5`, and a subsequent trend-direction OFI/control flip `z >= 1.0`. Trade with the prior trend. EMA-200 may describe trend alignment or conflict, but an EMA touch alone does not make the event eligible in this wave.

### A6. Cash-open control continuation

Restrict to 09:30:00–09:45:00 ET and treat it as a separate liquidity regime, not the CME session open. At `OVERNIGHT_HIGH`, `OVERNIGHT_LOW`, `YDAY_HIGH`, `YDAY_LOW`, `GLOBEX_OPEN`, or `CASH_OPEN_0930`, require a 10s control score `z >= 2.0`, a clean level cross, a five-second hold beyond the level, at least three of four flow-persistence subwindows in the break direction, and no opposing replenishment `z >= 1.5`. Record spread-response dominance as a diagnostic fixed before outcome inspection. Trade continuation.

All open-period feature baselines must use only prior sessions' matching minute-of-day buckets. Apply the most conservative frozen latency/slippage stress because 09:30 execution is unusually adverse. The general 10-second early-invalidation rule applies with no opening-drive exception; tape that slows or fails to produce the expected executable price response is an exit, not a reason to widen the stop. Report multi-horizon tape conflict and cash-open shock/normalization as diagnostics, but do not let them create hidden A6 variants.

## Wave B — conditional management families

Do not run Wave B unless at least one Wave A entry family passes every governing DEV gate. Freeze the selected parent and all Wave B rules in a new commit before inspecting management outcomes. Wave B never rescues a failed Wave A family.

### B1. Control-decay profit protection

After the trade has achieved at least one tick of favorable excursion, compare the frozen parent with an otherwise identical version that exits when two consecutive 10s windows each have fewer than two of four persistence subwindows in the trade direction and current tape intensity is below 50% of the entry-window intensity. This detects a move that has stopped working before opposing control fully appears. No threshold or horizon variants.

### B2. Opposing-absorption profit protection

At the next predeclared key level after entry, exit exactly one-third if opposing aggressive flow has `z >= 2.0`, same-direction price progress is no greater than one tick over 10s, and the control score flips. Exit the remainder only if a second attempt within 60s again fails to progress and price then crosses below the first failure window's low for a long or above its high for a short; otherwise manage it with the unchanged Wave A stop/2R/time rules. Compare against the frozen parent; do not choose exits trade by trade.

### B3. Risk-capped add to winner

Add exactly 0.5 of the original quantity only after the parent reaches `+0.5R`, the original thesis remains valid, and either (a) a pause meets the frozen low-volume definition and same-direction control returns with `z >= 2.0`, or (b) a fresh same-direction A2-style depletion occurs. The add executes only on renewed control, never during the pullback and never merely because price is profitable. Recalculate the stop so aggregate worst-case loss, including realized and unrealized P&L and costs, never exceeds the parent's original `1R`. No second add.

### B4. Persistent-control runner

Compare the frozen parent with a version that realizes 50% at `2R` and holds the remainder only while the same-direction control score remains nonnegative. Exit the runner at the first executable quote after either (a) a completed 1m bar closes through a causal 9 EMA against the position, (b) opposing control reaches `z >= 1.0`, or (c) 30 minutes elapse from entry. The original structural stop remains active. The EMA length, partial size, and time cap are fixed and may not be optimized.

## Separately frozen autonomous anomaly-discovery lane

Claude is required—not merely permitted—to act as the mathematician in the research program and search for defensible tape-scalping mechanisms beyond A1–A6 once the data-readiness gates are met. Search for new causal-time patterns in event sequences, flow/price nonlinearity, replenishment and resiliency, duration/hazard, self-excitation, change points, entropy, lead/lag, multi-scale state transitions, and interactions with the frozen key-level context. Do not limit discovery to concepts named by the presenters. “Causal” here means available without lookahead at the decision time; do not claim an economic causal effect from observational backtest data alone.

After the video-derived wave is closed, complete one bounded autonomous quant wave before declaring the discovery cycle finished. The wave may contain fewer than four families when fewer than four economically coherent mechanisms exist. Do not invent filler. If data readiness is insufficient, write and freeze the candidate mathematics and return `INSUFFICIENT_DATA` without opening outcomes.

This freedom operates only through separately frozen research waves:

1. Close and register the current wave before opening another. Never modify a failed family after its outcome is known.
2. Each autonomous wave may contain at most four genuinely distinct mechanism families and exactly one promotional specification per family. Freeze the feature formula, causal inputs, context, direction handling, threshold source, entry, stop, target, early exits, 30-minute cap, costs, latency, and exclusions before inspecting its P&L.
3. Thresholds must come from causal distributional rules or mechanism logic, not from a profitable parameter sweep. Neighboring values are robustness diagnostics and cannot promote a failure.
4. Unsupervised exploration may examine feature distributions and event frequency on DEV data, but it may not use the protected holdout or repeatedly query P&L to choose clusters, embeddings, or anomaly scores.
5. Every new mechanism must materially use trades, quotes, or depth and must demonstrate incrementality over an identical candle/key-level baseline. A candle-only discovery belongs outside this tape-scalping program.
6. Retain all autonomous failures and add all families, waves, and promotional comparisons to the cumulative multiple-testing burden. A new wave is not a reset of prior testing.
7. The engine may conclude that no additional defensible family can be frozen. Do not invent weak variants merely to use the budget.
8. Before outcome access, create a quant memo for each family containing: mechanism and likely counterparty behavior; exact equations; causally available inputs; expected-response curve; forecast horizon; one promotional entry/management policy; anticipated failure regimes; effective-sample estimate; model degrees of freedom; and falsification tests. Hash this memo with the strategy specification.
9. Use the nested chronological procedure and positive-EV promotion gate above. A novel anomaly is not promoted merely because it is statistically unusual; it must generate incremental executable net EV.

## Required controls and ablations

For every Wave A family and every autonomous promotional family, evaluate these frozen comparisons where the required data applies, and charge all promotional comparisons to the cumulative testing burden:

1. Key-level/context event without order-flow confirmation.
2. Candle-only 1m/3m confirmation at the identical event times.
3. Aggressor-delta-only.
4. OFI-only.
5. Depth-only.
6. Full joint signal.
7. Time-of-day, volatility, level-distance, and trend-matched non-events.
8. Within-session block permutation preserving event clustering.
9. Signal-delay stresses of 300 ms and 500 ms.
10. Best-day removal, top-1% trade removal, month/year/regime stability, and neighboring-threshold checks that cannot promote a failure.
11. Identical order-flow shapes sampled outside eligible key-level windows, labeled `NO_TAPE_SIGNAL`, to test the claim that location supplies incrementality.
12. For sweep-based cells, sweep magnitude alone versus sweep plus frozen five-second response/reclaim.
13. For displayed-depth cells, displayed size alone versus executed-and-replenished size, without permitting the weaker ablation to become a replacement strategy.
14. The full frozen signal with the `Available_R >= 0.70` entry gate versus the identical signal without the geometry gate. The ungated version is an ablation only and cannot rescue a gated failure.
15. The frozen grade calibration with independent-family clustering versus the same calibration with clustering removed. Run this only when the preregistered effective-sample floor is met; otherwise report `INSUFFICIENT_DATA_FOR_CLUSTER_INTERACTION`.
16. Pooled active-level results versus level-family diagnostics. Correct the family/level diagnostics for multiplicity and never promote the best-looking individual level after the pooled family fails.
17. For PSY-NQ-01, the identical order-flow mechanism at the futures-adapted PSY family versus time-of-day, volatility, trend, and touch-count-matched events at the base active levels and at non-level locations. Preserve the PSY family's pooled result as primary.
18. For PSY-FX-01, reference PSY proximity versus matched non-PSY weeks/events within the same frozen instrument and venue only. Never use spot-FX price-only results as an ablation for a CME depth strategy.
19. The unchanged parent signal across `ALIGNED_H1_ZONE`, `OPPOSING_H1_ZONE`, `H1_ZONE_CONFLICT`, and `NO_H1_ZONE`, with the context interaction frozen inside training and each promotional use charged to multiplicity. Descriptive subgroup results cannot rescue the pooled parent.
20. Base `Available_R` versus the separately registered `H1_GEOMETRY_ABLATION` using the nearer opposing obstacle. The zone-aware version cannot replace or modify the parent from outer-fold results.
21. The frozen base-and-displacement hourly-zone definition versus a simple causal five-completed-bar hourly swing-high/low context at identical parent-signal times. Require incremental net EV beyond this simpler recent-extreme baseline before attributing value to supply/demand zones.
22. Qualifying wall episodes at active key levels versus time-of-day, volatility, spread, approach-velocity, touch-count, and wall-size-matched wall episodes outside active-level windows. This tests whether the chart location contributes beyond a visually large book order.
23. For hold/flush probability forecasts, compare an unconditional training-only level/time-of-day base rate, a simple price-momentum-plus-distance-and-spread baseline, and the full tape/BBO/depth model. Require better once-only outer-fold calibration and decision/net-EV value; AUC alone is insufficient.
24. At identical eligible episode timestamps, compare trades-plus-BBO (`L1`) against trades-plus-BBO-plus-MBP-10 (`L1+L2`). Level II must add stable out-of-sample forecast or executable value after latency and costs before receiving credit for the strategy.
25. At identical wall approaches, compare initial displayed wall size alone against causal remaining burden, execution-only clearance rate/time, replenishment, and repeated-approach memory. This tests the transcript's “chipping” claim without selecting the most profitable attempt number.
26. Compare first trade-through/clear alone against the frozen five-second acceptance and `POST_CLEAR_RESERVE_5` state. Any fill for the confirmed version occurs only after its five-second window and latency; it cannot receive the earlier break price.
27. Compare the existing full joint signal with and without `QUOTE_MIGRATION_SCORE` inside the same nested chronological folds. Require incremental calibration and net EV after its comparison burden before describing quote chasing as useful on NQ/MNQ.
28. If Wave B legally opens, report the frozen B1/B2 parents with adverse-large-print polarity as a non-promotional diagnostic and one separately registered management comparison only if frozen before the management outcomes. Do not choose print-size cutoffs, scale-out fractions, or exit timing from P&L.

Do not select the best ablation as a new strategy after seeing results. The full joint signal is primary; ablations establish incrementality.

## Promotion and validation

- The video-derived reference wave is exactly six Wave A entry families; transcript-derived refinements and ablations do not authorize hidden variants. Wave B contains exactly four conditional management comparisons and opens only for a full Wave A DEV passer under a new freeze. New ideas are permitted only through the separately frozen autonomous lane, with no more than four promotional families per wave.
- Preserve the existing hard frequency requirement of at least one trade per week and preferred 1.5–2+ per week. Do not lower it for an attractive low-frequency near-miss.
- Thirty calendar days of depth data is an engineering/descriptive sample, not sufficient strategy validation. At 1–2 trades per week it may contain only about 4–8 qualifying trades.
- Apply every existing sample, net-EV, risk/reward, stability, multiple-testing, execution, and holdout gate.
- Treat the one-hour-zone module as a frozen context comparison, not a seventh Wave A entry family. Zone-only entries, zone-based stops/targets, and grade changes remain disabled unless a future separately frozen wave validates them.
- Treat the hold-versus-flush layer as a causal state/forecast overlay, not a seventh entry family. Its armed states and model probabilities are shadow-only; only exact A1-A4/A6 rule matches can enter until a separately frozen probability-policy version passes all DEV and untouched prospective gates.
- Apply the high-level quant mandate, nested chronological estimation, and uncertainty-adjusted positive-EV gate in this document. A full-sample backtest or an in-sample fitted model cannot promote.
- Any already-viewed historical period remains DEV/exploratory. Freeze the complete winning strategy before opening untouched future data.
- Run the governing minimum 100,000-path reproducible Monte Carlo only after a full DEV passer. Monte Carlo may stress a passer; it may never rescue a failed family.
- Report `NO VERIFIED EDGE` when warranted. Keep every failed cell, seed, configuration, raw result, and registry row.

## Required close-out report

For each cell, report event count, effective independent event count, trades, trades/week, percentage of active weeks, once-only outer-fold net expectancy, multiplicity-adjusted one-sided 95% lower confidence bound, stressed-cost net expectancy, shrinkage EV estimate, bootstrap probability `EV_net > 0`, win rate, average win/loss, profit factor, drawdown, fill rate, missed-signal rate, slippage, latency sensitivity, markouts, year/month/regime stability, ablations, multiplicity-adjusted significance, exact failed gates, and reproducibility hashes. For fitted models also report outer-fold boundaries, training-only transformations, degrees of freedom, regularization/calibration choices, learning-curve behavior, calibration, and simpler-model incrementality. Report median, mean, 10th/90th-percentile, minimum, and maximum holding time; percentages exited within 10s, 2m, 5m, 15m, and 30m; and P&L by frozen exit reason. Also report how many events were excluded for missing sequence/depth data, uncertain aggressor classification, right-censored resiliency, crossed/locked books, contract-roll contamination, or an unexecutable quote.

For the level/geometry layer, additionally report every active and context level ID present at entry, distance to each, nearest opposing level, `active_family_count`, `all_context_family_count`, `psy_experimental_present`, `h1_zone_experimental_present`, `ADR_USED_t`, transparent and cost-adjusted `Available_R`, geometry rejects, grade assigned using past information, grade changes attributable to clustering, trades and net EV by level family and grade, grade monotonicity, effective samples, and prospective status. For each PSY branch also report construction parity/audit results, available weeks, missing or partial weekly windows, source/adaptation label, time the weekly range became causal, touches, reactions, trades, net EV, incremental EV, and branch status. For the hourly-zone module, report bar/data certification, zones formed by side, widths, formation strength, causal availability, fresh/touched/invalidated/rolled-off counts, age, independent touch count, penetration, reactions, overlap, context labels, base versus zone-aware `Available_R`, the simple-swing ablation, incremental net EV, exact failed gates, and status. Distinguish descriptive level diagnostics from promotional tests. Never omit rejected signals from the audit trail.

For the hold-versus-flush layer, additionally report episodes by buy/sell wall and level family; state counts and complete transition matrix; wall-size distributions; wall lifetime; initial, added, executed, non-trade-removed, and remaining quantities; reconciliation failures; `RR`, `DR`, execution-only and total disappearance velocity; right-censored clearance time; `WALL_BURDEN_10`; attempt number and cumulative executed/added/removed quantities across repeated approaches; quote-migration components; equal-size-cluster diagnostics; adverse-large-print share; post-clear reserve, acceptance, rebuilt-wall frequency, and next blocking depth; persistence, spread, and response residuals; time from proximity/contact to armed and confirmed states; post-state markouts; realized flush, hold/reclaim, and unresolved rates at 5s/10s/30s; false continuation and false rejection rates under the frozen labels; precontact and contact Brier score, log loss, calibration error, reliability bins, and decision/net-EV curves; L1 versus L1+L2 incrementality; events excluded or routed to `UNCERTAIN_NO_TRADE`; and executable EV by confirmed state. Report probabilities as forecasts and states as timestamped confirmations—never describe either as knowing the future.

End with one of three classifications only:

1. `INSUFFICIENT_DATA`
2. `TESTED_AND_FAILED`
3. `DEV_PASSER_AWAITING_UNTOUCHED_VALIDATION`

Never label a video-inspired idea validated merely because its discretionary example looked convincing.

## Source index

- https://www.youtube.com/watch?v=4r_3DNeE8_U
- https://www.youtube.com/watch?v=S2T-cRUnugI&t=1889s
- https://www.youtube.com/watch?v=Lo7wDgcMLQI
- https://www.youtube.com/watch?v=q5DRctM5C-Q
- https://www.warriortrading.com/what-is-tape-reading-in-trading/
- https://www.youtube.com/watch?v=S1pROkW3XgE
- https://www.youtube.com/watch?v=YEL79Kpufxo
- https://www.youtube.com/watch?v=TaY1wePhJ5Q
- https://www.youtube.com/watch?v=tPgcj4ez3eM
- https://www.youtube.com/watch?v=5gO9nVJL5IQ
- https://www.smbtraining.com/blog/how-to-use-tape-reading-to-help-you-keep-your-trading-profits
- https://www.youtube.com/watch?v=1aAY4DlLsdE
- https://www.smbtraining.com/blog/how-to-use-tape-reading-to-determine-one-of-the-most-profitable-exits
- https://www.youtube.com/watch?v=RKV1rncXSkg&t=95s
- https://www.smbtraining.com/blog/how-to-think-about-reading-the-tape
- https://www.smbtraining.com/blog/stock-trading
- https://www.smbtraining.com/blog/category/reading_the_tape
- https://www.smbtraining.com/blog/tag/reading-the-tape
- https://www.smbtraining.com/blog/reading-the-tape-in-multiple-time-frames
- https://www.smbtraining.com/blog/technicals-trump-the-tape-in-financials
- https://www.smbtraining.com/blog/each-of-these-trades-is-different
- https://www.smbtraining.com/blog/what-is-price-action-confirmation
- https://www.smbtraining.com/blog/traders-ask-how-do-i-read-the-order-flow-in-an-etf
- https://www.smbtraining.com/blog/the-weekly-trade-plan-top-stock-ideas-execution-strategy-week-of-june-15-2026
- https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.html
- https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.html
- https://www.tradingview.com/script/Etj1ixAs-Traders-Reality-Main/
- https://www.tradingview.com/script/ZCqmZOUy-Traders-Reality-Psy-Levels-Daily-Open-GMT-Aware/
- https://www.scribd.com/document/727272438/TradersReality-Indicator-Settings-Guide
- https://arxiv.org/abs/2101.07410
- https://arxiv.org/abs/1011.6402
- https://arxiv.org/abs/1512.03492
- https://arxiv.org/abs/1312.0514
- Supplemental uploaded transcript block: https://www.youtube.com/watch?v=QXNyxgbrYro
- Supplemental uploaded transcript block: **The Secrets of Reading Level 2 (Tape Reading for Beginners)** — no supplied video ID; use the transcript text and hash above, not an inferred URL
