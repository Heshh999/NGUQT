# MROF — ONE CONSOLIDATED CLAUDE BUILD AND RESEARCH PROMPT

Prepared for Justin Gaskins — 2026-09-08.

Send this entire file to Claude in the existing MROF/MLES repository or project. It includes the full three source prompts as appendices, so those prompt files do not need to be sent separately. Existing code, registries, and any market data still need to be available in that project.

BEGIN CURRENT CLAUDE DIRECTIVE

## 1. Mission and scope

Continue my existing MROF project as a rigorous quantitative market-microstructure researcher and research-software engineer. Audit the actual implementation, complete missing authorized engineering, and carry out the registered research only when its data and evidence gates permit it.

Find repeatable NQ/MNQ tape-scalping strategies with positive executable expected value after realistic costs, latency, spread, available liquidity, partial fills, and missed trades. Use mathematical reasoning and independently proposed mechanisms as well as the video-inspired A1–A6 families. Do not promise that any strategy will pass.

My intended trading style:
- Trades can last seconds through 30 minutes, with no minimum holding time.
- Preserve the existing 09:30–11:30 ET entry window unless a later authoritative freeze demonstrably changed it. A6 has its separate 09:30–09:45 ET window.
- Enter before a one-minute candle closes when a fully completed causal event/subminute signal permits it. Never use an unfinished required confirmation as though it were complete.
- Use candles and levels for market context; tape, Time & Sales, BBO, depth, and actual price response determine the registered entry and exit conditions.
- There is NO arbitrary maximum number of trades per day, week, month, or strategy, and NO daily trade quota. Take every independently re-armed valid setup that is executable while flat and passes the governing session, risk, data, geometry, and execution gates. Four or more qualifying sequential setups can produce four or more trades; another day can produce one or zero.
- Preserve one-position gating, duplicate suppression, exact-time conflicts, causal reset/re-arm, and account-risk kill switches. Uncapped trade frequency does not authorize simultaneous positions or repeated trading of the same physical episode.
- Existing weekly activity requirements are research/promotion gates, not maximums or quotas. Do not confuse a millions-of-events dataset with millions of independent opportunities.

This is research and read-only shadow work. Do not place live orders. Do not purchase data, contact providers, or publish results without applicable prior authorization. Do not stop a healthy recorder simply because this prompt arrived.

## 2. Authority, actual state, and continuation

Read this entire current directive and Appendices A–C before editing. The appendices contain precise source formulas and source history; this directive governs their integration and resolves the operational conflicts listed here.

Audit the repository's applicable instructions, current entrypoint, source prompts, successor freezes, hypothesis registry, protected strategies, partitions, recorder, parser, tests, and data manifests. Identify the latest actual authoritative implementation, rather than assuming the latest file name or highest version number is active.

The last package supplied in this conversation described v01.5 and MLES capture v1.1. That is historical context, not a claim that the repository is still at that version. The later swing and exit documents are build directives; their presence does not establish that their code exists.

Produce an inventory with: requirement, source, existing code, integration path, relevant tests, engineering status, data status, research status, and any exact remaining dependency.

Required authority handling:
1. Preserve all frozen predecessor files, hashes, spent hypotheses, and protected-parent behavior. Add a successor only where an actual change is necessary; do not rebuild completed modules merely to create another version.
2. Select the next unused successor identifier from the repository. Do not blindly create v01.6 if that identifier is already used.
3. Archive this consolidated prompt with a SHA-256. Verify the embedded source hashes listed below when extracting the appendices.
4. Do not silently replace the source mathematics with a prose summary. Trace implementation to exact source definitions and units.
5. If inherited sources and code differ, document the exact mismatch. Keep the predecessor reproducible. Resolve the affected repair or new variant explicitly before inspecting its outcomes; do not invent a hidden threshold.
6. If required repository files are missing, complete the useful independent work available and name the exact missing files. The appendices supply prompt text, not missing code or absent data.
7. Continue from saved checkpoints and registry state. Repeatedly receiving this prompt must not reset trial counts, rerun consumed outer folds, or relabel exposed data as untouched.

Explicit integration resolutions:
- Old appendix instructions to freeze before attaching a recorder apply to their historical initial build. Ongoing recording may continue. Freeze any new research specification before opening its relevant outcomes.
- Old statements such as “zero captured sessions,” “historical depth nonexistent anywhere,” or “the recorder has never been attached” are historical reports. Inspect the current authorized data inventory and report what actually exists. Never assert that genuine historical depth cannot exist outside this repository.
- A code build and a synthetic fixture suite are distinct from market research and prospective validation.
- Appendix B's original v01.6 file names and v01.5 parent references are examples tied to its creation date. Resolve the actual current parent without changing the intended swing experiment.
- Appendix B's final unconditional INSUFFICIENT_DATA wording is conditional here: use that classification only when data are insufficient. Sufficient research can pass, fail, or be inconclusive.
- The experiment in Appendix C is additional to the baseline, not permission to turn on every B and E management rule together.
- A1–A6 remain the six baseline entry mechanisms. A wall overlay, level extension, grade, or management arm is not an unregistered seventh entry family.
- Preserve distinct feature units. A raw replenishment ratio and a robust replenishment z-score are not interchangeable. Any overlay that adds a different condition must be identified and tested as such.
- In net P&L, charge each execution cost once. If executable fill prices already include spread and slippage, do not subtract the same price deterioration again under a second label.
- A 30-minute liquidation instruction and a completed liquidation are different in a disconnect or liquidity shortage. Preserve the deadline policy, track any remaining position, and never invent a timely fill.

## 3. Market data and complete processing chain

Primary topology: NQ signal contract → causally synchronized MNQ execution contract. NQ and MNQ have separate order books. NQ depth cannot establish an MNQ fill or an MNQ liquidity target.

Use:
- Time & Sales / tape: individual executed trades, size, timestamps, and supported aggressor classification with uncertainty.
- Level I: genuine best bid/ask prices and quantities.
- Level II: genuine supported MBP-10 updates, both sides, with feed-provided actions and ordering.
- Exact individual contract identity, session calendar, receive/availability clocks, sequence fields, run/segment identity, and data-quality events.

Keep immutable raw events. Reconstruct the book, aggregate causal bars, compute training-only baselines and features, build levels, detect episodes, form signals, resolve conflicts, simulate fills and exits, and write complete research/shadow ledgers.

Do not reduce the raw recording to only candles, screenshots, heatmaps, or periodic feature rows. A heatmap can be an optional debugging view of the recorded data; it is not a required input.

Use the latest verified MLES recorder and adapter. Preserve restart-safe files, global event ordering, atomic finalization, manifests, hashes, row counts, contract/session isolation, and drop/gap/error diagnostics. Examine roll handling from recorder through levels, feature warm-up, signal identity, and fills. Do not carry an old contract's absolute levels or open episode into a new contract by relabeling it.

Record the full available session where practical, including the overnight period and opening minutes, because VWAP, overnight levels, weekly constructions, and prior-session baselines require that history. A recording beginning at 09:30 cannot retroactively supply missing overnight events.

Historical vendor/replay data may support engineering or registered DEV research when genuinely available, authorized, and audited. Do not invent missing depth from OHLCV or infer queue identities from MBP. Keep source/provenance and feed-equivalence checks. Data already used for discovery are not prospective evidence.

The integration must have a runnable path from manifest audit → parsing/global ordering → book reconstruction → features/levels → A1–A6 detection → coordinator → fills/exits → ledger. Distinguish a feature-only fixture from this full path; do not claim full integration unless exercised.

## 4. Resolution and candle behavior

Support the following roles from the raw event stream:

| Role | Resolutions | Purpose |
|---|---|---|
| Raw/event based | Each event, event-count and volume-time windows | Preserve sequence and activity-dependent sampling |
| Microstructure | 1s, 5s, 10s, 30s; specific frozen 2s measurements | Flow acceleration, persistence, withdrawal, absorption, response |
| Setup structure | 1m, 3m, 5m | Rejection, reclaim, acceptance, pullbacks, compression/expansion |
| Broader state | 10m, 15m | Persistence, divergence, auction context |
| Higher context | 1h, 4h, daily | Trend, movement/volatility context, location |

Support does not authorize an unrestricted timeframe combination search. Freeze a small set of roles per mechanism; include every promoted comparison in the testing burden. The same burst seen across several timeframes remains one underlying episode.

Use completed bars for any feature requiring a close. Partial-candle observations may be used only if explicitly specified and logged as partial; never use that candle's eventual high, low, close, or volume early.

Candle behaviors include wick/closing-location rejection, break/retest, false break/reclaim, acceptance, trend pullbacks, range compression/expansion, and the separately defined hourly base/displacement construction. Do not automatically import my old discretionary vector-candle or fair-value-gap strategies into A1–A6. A new candle mechanism needs its own definition and registered test.

## 5. Exact level hierarchy

### Base active entry pool: fourteen levels

| IDs | Meaning |
|---|---|
| YDAY_HIGH, YDAY_LOW | Previous completed exchange-session extremes |
| LWEEK_HIGH, LWEEK_LOW | Previous completed exchange-week extremes |
| OVERNIGHT_HIGH, OVERNIGHT_LOW | Current overnight extremes fixed at the cash open |
| GLOBEX_OPEN | Official exchange-session opening reference |
| CASH_OPEN_0930 | 09:30 ET cash-session reference |
| SESSION_VWAP | Causal session VWAP using the frozen reset |
| VWAP upper band, VWAP lower band | The frozen session VWAP ± 2 volume-weighted standard deviations |
| PP, M2, M3 | Frozen previous-session pivot family |

Use Appendix A's exact session, pivot, proximity, and family-clustering definitions. S1 and R1 are intermediates for M2/M3, not additional active base locations. Do not silently replace session definitions or back-adjust raw prices.

The common source proximity rule is max(4 ticks, 0.20 × ATR20 of completed 1m bars). Maintain dimensional consistency when ATR is represented in price rather than ticks.

### Context and experimental references

Retain:
- EMA-200 distance, slope, and the existing frozen trend state;
- ADR_HIGH/LOW, ADR_50_HIGH/LOW, and ADR_USED;
- current running session high/low;
- the nearest opposing registered level;
- independent-family overlap;
- causal one-hour supply/demand zones;
- the separate psychological high/low branches;
- the confirmed swing experiment in Appendix B.

ADR cannot affect decisions until its required construction/settings certification passes. H1 zones and psychological levels similarly retain their actual audit/status gates. Do not describe “computed” as “certified” or “predictive.”

Other levels supported by an older master engine, such as opening-range references, a weekly open, or manually supplied levels, retain their recorded context role unless an existing authoritative freeze explicitly grants entry eligibility. Do not append them to the fourteen-level pool implicitly.

A context-only level cannot create a base trade on its own. Count each independent family only once; all VWAP variants count as one family, PP/M2/M3 as one, all overlapping H1 zones as one experimental family, and all qualifying swing timeframes as one swing family.

### H1 zones and confirmed swings are separate constructions

Preserve the original hourly zone formula: one to three compact base bars followed by a completed qualifying displacement beyond the base and the max/min of the five completed hourly bars preceding the base. That prior-five-bar extreme is NOT the confirmed-fractal swing definition. Do not replace it with a fractal and still call the result unchanged.

For the new swing module:
- Use the exact five-bar, two-left/two-right asymmetric tie rule in Appendix B.
- 1m swings remain diagnostic only: no eligibility, grade, stop/target, or geometry influence.
- 5m/15m/1h confirmed swings are experimental locations only in their registered arms.
- The swing becomes known at the second right-hand bar's close. The right-side confirmation is 10 minutes for 5m, 30 minutes for 15m, and two hours for H1 after the center bar closes.
- Freeze a new swing episode's anchor and membership so later swing confirmations or changing ATR cannot fabricate a new physical approach. Preserve the parent-off behavior.
- Swing lifecycle retirement after two own-timeframe closes is separate from the five-second tape acceptance used by applicable entries. Do not wait for two hourly closes to execute a completed A2/A6 signal; do not retire a swing simply because five seconds have passed.
- Retire old-contract swings on roll; do not silently flip broken support to resistance or vice versa.
- Preserve the original parent and compare swings off, swings only, parent plus swings, and overlap as the separately registered arms described in Appendix B. Treat each promotional use as a comparison, not a free filter.

### Psychological ranges and RVMR

Keep Appendix A's PSY-NQ futures adaptation separate from its forex alternative. The NQ/MNQ adaptation uses the first eight tradable hours after the official weekly Globex open and cannot be known earlier. A forex branch has its own instrument/venue, data partition, calibration, costs, and validation; success there does not validate NQ.

RVMR, if actually present and causally usable, can provide movement/volatility context in a registered comparison. Inspect its actual outputs and evidence. Distinguish a current LOW/MEDIUM/HIGH environment label from a genuine future forecast with an explicit horizon. Do not invent forecast accuracy, duration, or timing, or make RVMR a mandatory filter merely because it exists.

## 6. Preserve all six entry families

Implement and trace exact formulas, robust baselines, signed control, and timing from Appendix A and the authoritative predecessor. The following table is an orientation guide; the source formulas control.

| Family | Mechanism | Required confirmation and intended trade |
|---|---|---|
| A1 | Replenishing-wall absorption reversal | Strong aggression fails to progress, liquidity replenishes, repeated approaches occur, then opposing control and retreat permit a reversal |
| A2 | Execution-driven wall depletion continuation | Executions consume the displayed wall, replenishment remains low, clearance/acceptance lasts five seconds, and persistent flow supports continuation |
| A3 | Non-trade withdrawal / liquidity vacuum | Target-side near depth withdraws under the frozen 60%/20% two-second rule, then aggression and price progress confirm the vacuum direction |
| A4 | Expected-response failure reversal | Strong flow produces inadequate/wrong response; the level or pre-sweep price is reclaimed and opposing control confirms the fade |
| A5 | Pullback absorption / trend resumption | A pullback at an eligible level encounters absorption and the previously defined trend-direction control returns |
| A6 | Cash-open continuation | Between 09:30 and 09:45 ET, a qualifying opening reference breaks, holds five seconds, and persistent control confirms continuation |

Long and short are symmetric pooled rules. A6 has the restricted level subset in Appendix A, not automatic access to every experimental reference.

Normalize “large,” “fast,” and “strong” with the strict prior-20-session, matching-time-of-day robust baselines. Never use the current session or future observations to fit these baselines. Missing history and undefined scales are unavailable inputs, not license to invent a favorable default.

The wall engine observes and distinguishes hold, execution-driven flush, withdrawal, failed flush/reclaim, and unresolved states. Observed or armed states do not enter. Confirmation must meet the complete applicable family, and fills happen after confirmation and latency.

Record refilling-liquidity estimates without asserting hidden owner identity, spoofing, manipulation, or a confirmed iceberg from MBP. A level disappearing beyond the visible depth window is not proof of cancellation. Ambiguous accounting must produce an explicit uncertainty/data outcome.

Research precontact/contact hold/flush/unresolved probabilities at the registered horizons only with training-only features. Post-clear information cannot enter a precontact prediction. Probabilities remain shadow diagnostics until the complete forecast and prospective gates pass.

## 7. Execution, risk geometry, and exit experiments

Preserve the parent Wave A structural stop beyond the event extreme plus max(2 ticks, 0.10 × completed-1m ATR20), its 2R target, exact early invalidation, later control-loss exit, session flattening, and 30-minute cap.

Use the existing audited latency model. The source assumptions are 150 ms baseline and 300/500 ms stresses; these are not measurements of my actual connection. Record measured latency where available, distinguish observation delay from routing delay and deliberate confirmation, and prevent double counting.

Available_R = distance from executable entry estimate to the next opposing registered level / distance from entry to the structural stop.
- Below 0.70R: reject under the base geometry rule.
- From 0.70R to below 2R: not A+.
- At least 2R: geometrically eligible for A+, but not sufficient for that grade.
- Missing or contradictory required tape confirmation: no entry regardless of geometry.

Use the original uncertainty and cost-adjusted geometry reporting. Grades must come from training-only calibrated net-EV/downside estimates with enough independent observations and prospective evidence; they are not discretionary points or sizing authority.

### Conditional B management studies

Preserve the four distinct Appendix A comparisons:
- B1: control-decay protection.
- B2: opposing-absorption profit protection.
- B3: a single risk-capped addition to a winner.
- B4: persistent-control runner.

Open their market research only when the inherited parent-passer and management gates permit. A B arm cannot rescue a failed parent. Preserve the exact updated B1 definition; it is not merely the parent's already-mandatory initial ten-second invalidation.

Implement contract quantities honestly. A half or third of a position must be achievable in whole contracts under a preregistered sizing policy. If a position size cannot implement a fraction exactly, label that arm unavailable for that size rather than silently rounding, inventing fractional futures, or increasing risk.

### Three separate E exit arms

Implement Appendix C exactly as a separate exit experiment:
- E0: actual baseline behavior, verified against the parent.
- E1: replace only the fixed profit target with the frozen nearest qualifying opposing MNQ wall target, one MNQ tick before the wall. Retain the protective exits.
- E2: remove the fixed target and add the completed-window opposing-control exit. Retain the protective exits and cap.

E1 uses its two-second persistence, prior-session z-score thresholds, available-depth limit, explicit fallback labels, and target-initialization time. Freeze the selected target; do not chase later walls. It triggers a simulated market exit, not an assumed resting-limit fill.

E2 requires signed opposing control, three-of-four persistence, and adverse price progress in a completed ten-second window. Missing information is not favorable control.

Do not combine B1–B4 with E1/E2 into a new unregistered optimization grid. Map overlapping ideas into the existing spent-hypothesis registry.

For exits, track partial liquidation and every remaining contract. Do not cancel an unfilled exit remainder and mark the position flat. Do not fill twice from consumed displayed liquidity or invent depth beyond the capture.

Run both Appendix C evaluations:
1. Paired entry/fill/quantity/initial-risk comparisons in isolated shadow trades to attribute exit differences.
2. Separate deployable sequential replays preserving flat/re-arm/account constraints, where different exits may admit different later entries.

Do not present the overlapping paired comparison as a deployable portfolio equity curve.

## 8. Independent quantitative research and falsification

Do more than implement the six video ideas. Once readiness and wave-order gates permit, complete a separately frozen independent discovery wave with at most four economically coherent mechanism families and exactly one promotional specification per family. Do not invent filler or run unlimited variants.

Investigate causal-time price response conditional on signed flow, flow-response nonlinearities, resiliency, depletion/replenishment, waiting time to a barrier, self-excitation/decay, change points, state transitions, and synchronized NQ/MNQ lead/lag.

Use the prescribed progression: event studies and simple baselines → regularized regression/logistic/GAM → duration/competing-risk models → justified sequence/regime models → bounded machine learning only with sufficient independent data. Deep models require their separate source gates and authorization. Complexity must prove incremental value.

A bounded review of relevant primary microstructure research and official SMB Capital tape/depth/open material can inform the registered mechanism backlog. Record links, dates, accessible evidence, and transfer assumptions. Do not claim to watch inaccessible video footage, infer trading success from presenter claims, or modify a frozen mechanism merely because a new article appears.

Required comparisons include:
- Levels/context without tape confirmation.
- Candle-only versus complete flow setup at matched events.
- Delta-only, OFI-only, depth-only, and full joint signal.
- Trades+BBO versus trades+BBO+MBP-10.
- Matched flow/wall behavior at key levels versus outside eligible level windows.
- Displayed wall size versus execution, replenishment, response, and repeated approaches.
- Initial break versus completed acceptance.
- Base versus registered geometry/context/swing variants.
- Parent exits versus each separately registered B or E alternative.
- Simpler price/time-of-day/volatility baselines versus trained forecasts.
- Cost/latency stress, concentration, and observed-regime robustness.

Outside-level examples are controls in the base wave, not newly authorized trades. An ablation that looks better cannot silently replace a failed primary specification.

## 8A. Immediate limited-data pilot on the recorded days

I have already completed the recorder step and currently have only a few recorded market days. Do not respond by rebuilding the recorder or merely repeating `INSUFFICIENT_DATA`. Ingest and audit every presently supplied completed recording, then run the following **PILOT_DIAGNOSTIC_ONLY** analysis now. This section authorizes limited outcome inspection for engineering and descriptive diagnosis; it does not waive any promotion, sample-size, multiplicity, or prospective-validation gate.

Before reading pilot outcomes, archive/hash this directive and freeze the exact pilot calculations below. Permanently label every day inspected by this pilot `EXPOSED_PILOT_DEV`; these days can remain in later DEV/training where the governing protocol permits, but they can never become untouched prospective validation. Do not adjust A1–A6 thresholds, levels, windows, stops, targets, exits, feature definitions, or baselines after seeing these days. Any later change is a separately registered successor hypothesis and may not be evaluated as untouched on these pilot days.

Run this sequence:

1. **Data audit:** report each session/date, instrument, exact contract, covered clock interval, trade/BBO/depth row counts, first/last timestamps and sequences, NQ–MNQ overlap, observed depth levels on both sides, gaps, duplicates, out-of-order events, crossed/locked books, disconnects, reported drops/write errors, manifest/hash results, and contract-roll boundaries. Distinguish a complete session from a partial day. Do not reject an otherwise useful partial recording silently; mark exactly which studies it cannot support.
2. **Pipeline proof on genuine rows:** run manifest audit → parser/global ordering → NQ and MNQ book reconstruction → causal feature calculations → level calculations → approach/episode identity → A1–A6 detection → coordinator → MNQ simulated fills/exits → complete ledger. Report the earliest and latest real event processed by every stage. A synthetic fixture does not satisfy this step.
3. **Feature-health report:** for each session, show availability, missingness, distribution, and impossible-value checks for aggressor delta/confidence, tape intensity/acceleration, OFI/control, spread, three-level imbalance, replenishment, depletion, non-trade-removal inference, price-response residual, persistence, sweeps/reclaims, wall state, and quote/depth health. Undefined baselines remain unavailable; do not replace them with zero.
4. **Level and approach census:** count approaches to every one of the fourteen active base levels, eligible proximity episodes, wall states, hold/flush/reclaim/unresolved outcomes, geometry rejects, duplicate/overlap suppressions, risk/data suppressions, execution misses, and zero-event levels. Report context flags for EMA-200, ADR, H1 zones, psychological ranges, RVMR, and confirmed swings only when their current implementation and data availability permit them.
5. **A1–A6 threshold funnel:** for each family and direction, report how many physical episodes passed each successive frozen condition, how many completed the entire setup, and the precise first failing condition for all nonqualifiers. Count one physical episode once. Do not loosen a threshold because complete setups are rare or absent.
6. **Exact frozen signals and trades:** for every completed A1–A6 signal, report session/time, family, direction, level IDs, causal signal time, entry-eligible time, first executable MNQ price after the frozen latency, quantity available/filled/missed, structural stop, 2R target, Available_R, entry and exit reasons, holding time, MFE/MAE, costs, slippage assumptions, and net dollars/R. Preserve zero-trade days.
7. **Descriptive response check:** at every eligible independent episode—not only executed winners—report signed executable markouts at 1s, 5s, 10s, 30s, 60s, and 180s after signal availability when observable. Also report whether the mechanism's preregistered expected direction occurred before its invalidation horizon. These are descriptive pilot statistics with session/episode denominators, not inferential proof.
8. **Matched sanity controls where sample permits:** show the same frozen measurements for key-level episodes without full tape confirmation and for comparable recorded non-level flow episodes. With only a few days, label these descriptive controls and do not choose the best-looking subgroup.
9. **Visual replay audit:** produce a compact event-log or chart for at least one genuine qualifying episode per observed A family, plus representative near-misses and data-suppressed episodes. Display the causally available level, Time & Sales, BBO/depth state, signal completion, simulated entry after latency, and exit. Do not cherry-pick only profitable examples. If no family qualifies, show the closest near-miss by a predeclared standardized distance-to-threshold measure and clearly label it `NOT_A_SIGNAL`.
10. **No premature model search:** do not fit the autonomous anomaly models, optimize grades, select subgroups, open Wave B, or declare an E1/E2 exit winner from this pilot unless an inherited gate independently permits that study. You may verify that their code paths and inputs are operational on genuine rows without ranking P&L. Do not use these days to create a new hypothesis from an attractive chart and then report its same-day performance as confirmation.

Return two separate answers:

- **IS THE SYSTEM WORKING?** Answer from data integrity, real-row pipeline completion, causal feature availability, deterministic detection, and realistic simulation. This is an engineering/functionality judgment.
- **DO ANY HYPOTHESES APPEAR PROMISING?** Give only a descriptive pilot table for A1–A6 and explicitly state the number of independent episodes/trades. Use `EARLY_DIRECTIONAL_SUPPORT`, `NO_EARLY_SUPPORT`, `MIXED_PILOT`, or `NOT_OBSERVED` as descriptive labels. These labels are not positive-EV classifications.

The final pilot classification must be:

`PILOT_DIAGNOSTIC_COMPLETE — INSUFFICIENT_DATA_FOR_EV`

when the real-data pipeline completes but the evidence remains too small for EV inference. If the real-data pipeline fails, use `PILOT_BLOCKED` and give the first exact failing artifact/stage and repair required. If no complete A1–A6 signals occur, do not call the strategies failed; report `NOT_OBSERVED_IN_PILOT` and preserve the complete threshold funnel.

## 9. Evidence gates and honest outcomes

Inventory real audited sessions and independent episodes. Do not infer readiness or current recording status from an old freeze. Three or six months is not automatic proof; millions of messages are not independent trades. Preserve applicable source readiness/sample/calendar gates and identify any mismatch with current evidence instead of quietly bypassing them.

Before each authorized outcome study, commit/hash the exact definition, variation budget, features, label, horizon, thresholds, model-fitting procedure, costs, exclusions, and evaluation plan. Separate engineering tests from market-outcome access.

Use nested chronological training/test folds, training-only preprocessing/calibration, purging and embargo, session/episode-aware resampling, and the governing cumulative multiple-testing correction. Retain every failed/inconclusive hypothesis and all previous trials.

Require positive net EV and the prescribed uncertainty lower bound, adverse-cost survival, incremental evidence, activity, sample, stability, and concentration gates before a DEV passer. Use Monte Carlo/other risk studies at the source-authorized stage; generated paths cannot create new independent market evidence.

After selection, freeze the complete strategy and test on subsequently collected untouched data. Previously examined days cannot be retroactively designated prospective. Any material modification creates a new version and future-validation clock.

Report no verified edge when results fail. Do not keep mutating thresholds until something passes. Distinguish a predictive pattern from an executable profitable strategy.

## 10. Implementation, verification, and recorder handoff

Complete the authorized engineering that is actually missing. Provide one documented current research entrypoint and a complete review package, including dependencies and test commands. The active import path must use the authoritative current coordinator, rather than accidentally routing through superseded versions.

Verify:
- predecessor parity for genuine feature-off/parent arms;
- causal feature and bar availability, strict baselines, signed/mirrored rules;
- exact-time callback grouping before fills, deterministic episode IDs, conflicts, suppression, and genuine re-arm;
- no duplicate/reused liquidity, correct contract mapping, quantity handling, partial exits, and unresolved execution;
- calendar, gap, restart, maintenance, and contract-roll behavior;
- swing availability, stable approach identity, retirement, and separation from H1 zone construction;
- E0 parity and the exact E1/E2 selection/confirmation/fallback rules;
- full parser-to-signal-to-exit integration on controlled fixtures;
- absence of live-order submission;
- uncapped sequential valid setups with no arbitrary trade counter.

Do not claim synthetic fixtures prove full system correctness or market profitability. Report what each meaningful test covers and what remains untested.

Give me a current beginner-readable NinjaTrader recording runbook:
1. Exact authoritative .cs file(s), namespace, dependencies, and import/copy destination.
2. How to compile with F5 and identify the recorder in the platform.
3. How to select the actual current NQ and MNQ contracts and confirm genuine Level II entitlement/data.
4. How to attach/start the recorder and confirm trade, quote, depth, heartbeat, and health counts for both instruments.
5. A five-minute functional capture or playback smoke test, clearly labeled engineering data.
6. How to stop/finalize safely, find files/manifests, verify hashes/audits, and transfer a completed session.
7. What must stay running, which overnight periods matter, how to identify failure, and the audited roll/restart procedure.
8. The exact manifest-first ingestion command, expected success summary, and how to see whether research remains gated.
9. Market Replay backup instructions where supported, clearly separated from the recorder's own raw files and from historical Tick Replay limitations.

Verify current platform-specific instructions against actual source and official documentation. Never tell me to compile test API stubs into NinjaTrader. If the environment has no real NT8/Windows/feed, say that real F5 compilation and the genuine smoke test remain user-side; a stub compile is not a substitute.

Do not wait for more market sessions to write runnable software, documentation, or fixtures. Do not bypass the data gates to fabricate an outcome.

## 11. Final deliverables and checkpoints

Deliver:
- A concise actual-state inventory and missing-item list.
- Only necessary additive source modules and tests, with one coherent entrypoint.
- A successor freeze where a change is needed, this archived prompt, exact hashes, and the full review package.
- A requirement → code → test → evidence traceability table.
- Actual commands/results and clear test scope, not invented counts.
- Recorder deployment and session handoff instructions.
- A persisted continuation checkpoint with completed work, exact blockers, next executable step, and registry status.

Classify separately:
- ENGINEERING: complete / partial / blocked.
- DATA: sufficient / insufficient for each named study.
- MARKET RESEARCH: not run / passed / failed / inconclusive.
- PROSPECTIVE VALIDATION: not started / in progress / passed / failed.
- LIVE EXECUTION: not enabled by this directive.

Finish with a short plain-language explanation of what is implemented, which A/B/E and level arms were actually studied, whether any net edge was demonstrated, and exactly what I should do next.

END CURRENT CLAUDE DIRECTIVE

## Embedded source archive and hashes

The following appendices preserve the full source text used to assemble this handoff. Treat historical operational/status statements according to Section 2 above. Precise experiment definitions remain controlling unless an explicit integration resolution above applies; any remaining substantive ambiguity must be identified before that affected experiment opens outcomes.

Extraction convention: each source body is the text immediately after its BEGIN marker through immediately before its END marker, with no marker lines included. Preserve its final newline and UTF-8 encoding when checking the source hash.

- Appendix A: MROF_YT_OF01_FINAL_SOURCE_PROMPT(3).md — 117065 source bytes; SHA-256 `74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b`.
- Appendix B: MROF_YT_OF01_6_CAUSAL_SWING_SUCCESSOR_PROMPT.md — 19237 source bytes; SHA-256 `93738aadd98beb10939bc0ada9f70d68ca107391bfdce2edda34a457f45901a2`.
- Appendix C: MROF_LIQUIDITY_AND_TAPE_EXIT_CLAUDE_PROMPT.md — 12696 source bytes; SHA-256 `262f7e49ba6b4c18e99ba302574bba94e6d17ff802a8fd7cae22a7951c127c03`.

# Appendix A — Original complete MROF tape-scalping source prompt

<!-- BEGIN MROF_SOURCE_A -->
# MROF-YT-OF-01 — Transcript-Audited Video-Derived Order-Flow Research Wave

**Revision:** Quant-EV mandate added 2026-08-29; official SMB Capital site refresh, NQ/MNQ transfer hardening, the preregistered level/geometry hierarchy, and the conditional Psychological High/Low NQ/FX module added 2026-08-30; causal one-hour supply/demand-zone context, key-level wall hold-versus-flush decision engine, futures-native Nour Trades transcript transfer, uncapped independent-setup policy, and recorder-to-research handoff contract added 2026-08-31. This revision preserves the transcript audit and all earlier safeguards while making independent mathematical strategy discovery and executable positive expected value the explicit research objective.

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
- There is no maximum number of trades per day, week, month, or strategy. Execute every newly completed, independent, otherwise valid setup permitted by the frozen trading window, one-position rule, data-quality gates, execution rules, and governing account-risk kill switches. Four valid sequential setups may produce four trades; another day may correctly produce one or zero. Never force a trade to meet a quota.
- The weekly activity requirement is a minimum research/promotion requirement, not a throttle, target, or maximum. Do not discard later valid setups because an earlier trade occurred, because a daily count was reached, or because the preferred weekly frequency was already satisfied.
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

## Operational data acquisition and recorder-to-research handoff

This prompt does not magically obtain market data. The research engine may use data only after the user has recorded or lawfully supplied the actual files and made them available to the environment running Claude. No local NinjaTrader folder, broker connection, replay database, or credential is visible to Claude merely because this prompt names it.

### Authoritative acquisition route

1. Audit the existing `MROF_V1_Engine.zip` and repository before creating or renaming anything. Extend the existing authoritative recorder rather than building a conflicting recorder. If the referenced package is absent, report the exact missing artifact and stop the deployment-specific work without inventing its interface.
2. The primary live capture must subscribe to genuine CME data through NinjaTrader and record Level I/trades from `OnMarketData()` and every supported Level II price-level change from `OnMarketDepth()` or the already-proven equivalent in the supplied engine. Preserve callback receive order; perform expensive feature calculation outside the capture path so recording cannot block the event stream.
3. Capture mode is read-only. Disable every order-submission path and prove in a deterministic test that starting, reconnecting, stopping, replaying, or encountering an exception cannot submit, change, or cancel an order on any account. Recording data is not permission to paper trade or trade live.
4. Capture NQ and MNQ as separate exact front-month contracts and separate books. If one recorder instance supports only its chart instrument, deploy one verified instance for NQ and one for MNQ. If it claims multi-instrument capture, prove both subscriptions and independent event counters in a deterministic/live smoke test.
5. Never use `NQ`, `MNQ`, or a back-adjusted continuous series without the exact expiry identifier in a raw event record. Around rollover, capture both old and new contracts during a declared overlap, retain them separately, and change the research signal contract only under the frozen roll rule. Never splice depth across contracts.
6. The authoritative capture target is the complete CME session, beginning at the versioned `18:00 ET` session open and continuing through the following `17:00 ET` session close. Log the scheduled daily maintenance closure separately and resume before the next session open. At minimum, keep the recorder active from before the Globex open through `11:35 ET` the next day. A morning-only file is not complete evidence for session VWAP, overnight extremes, prior-session features, or full-session integrity and must be labeled accordingly.
7. Record connection/disconnection/reconnection, subscription start/stop, heartbeat, startup book-building state, sequence gap when supplied, dropped/write-failed event, clock offset, contract roll, and orderly shutdown events. Do not mark a stream research-ready until trades, BBO, and both sides of supported depth are advancing and the initial book has reached the declared level count or an explicit provider limitation is recorded.
8. Write immutable, append-only raw files partitioned by capture date, exact contract, and stream type or the existing recorder's equivalent safe schema. Close each session with a manifest containing schema/spec version, start/end timestamps, event counts by type/side/action, first/last sequence when present, disconnects/gaps, file sizes, and SHA-256 hashes. Research ingestion may read only closed, hashed manifests; it must ignore files still being written.
9. Do not silently upload data, credentials, or account information. The user must explicitly copy or upload the closed raw session folders and manifests into the Claude project/repository, or run Claude Code locally with a configured read-only `data_root`. Record the exact path and hashes in the ingestion ledger. If no files are accessible, return `INSUFFICIENT_DATA`.

### Redundant NinjaTrader Market Replay backup

Require the deployment runbook to offer NinjaTrader's native Market Replay recording as a redundant backup, not a substitute for the loss-audited MROF raw schema:

- In Control Center, use `Tools > Options > Market Data > Enable market recording for playback`.
- Keep NQ and MNQ active and receiving live data. NinjaTrader documents that Level II replay data is recorded only while a Level II, SuperDOM, or FX Pro window is open and receiving depth for that instrument; therefore keep a verified Level II or SuperDOM window open for each contract being backed up.
- Native replay files reside under `Documents\NinjaTrader 8\db\replay`. Preserve them unchanged and back them up after NinjaTrader closes or the session is complete.
- Market Replay preserves synchronized Level I and Level II event sequencing, whereas ordinary historical tick/Tick Replay is not a substitute for historical depth. Run a sample replay parity check against the MROF recorder before relying on it for recovery.

### Mandatory Claude deployment deliverables

Before asking the user to collect the first research session, produce `RECORDER_DEPLOYMENT.md` and `DATA_HANDOFF.md` containing:

- the exact `.cs` files, namespaces, install/import locations, and F5 compile steps supported by the supplied code;
- the exact NinjaTrader windows, instruments/contracts, recorder instances, strategy/indicator settings, output path, and start/stop sequence;
- a visible health panel or log line with per-instrument trade, bid, ask, depth-bid, depth-ask, gap, drop, and write-error counters;
- a five-minute SIM/live smoke test that proves NQ and MNQ events, ten levels when the provider supplies them, timestamps, daily file closure, manifest generation, and clean restart recovery;
- the daily and weekly copy/upload procedure by which closed session folders become accessible to Claude without exposing broker credentials;
- a parser command that performs schema, hash, chronology, book-reconstruction, contract, session, and gap audits before any feature or P&L calculation; and
- a readiness report that keeps the research status `INSUFFICIENT_DATA` until the required streams and minimum independent sessions exist.

Use the first approximately 20 complete sessions for recorder/integrity validation and descriptive engineering. Do not spend them as an untouched strategy holdout. Continue collection while bounded DEV research accumulates; freeze any passer before opening subsequently recorded sessions for prospective validation.

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
- Permit one position at a time, but impose no daily, weekly, monthly, or lifetime trade-count cap. Long and short rules are exact mirrors and form one pooled, symmetric primary family. Direction-specific results are diagnostics unless separately preregistered and charged to multiplicity.
- Primary endpoint: net expectancy of the executable fixed-rule trade. Secondary, non-promotional diagnostics: signed midquote markouts at 1s, 5s, 10s, 30s, 60s, and 180s.
- Never convert a screen color directly into aggressor side, infer participant identity from a refresh, or label an order as spoofing. Record observable events and classification uncertainty only.

### Uncapped independent-setup execution policy

The engine must take every valid independent setup that becomes executable while flat and while all governing time, data-quality, geometry, execution, and account-risk conditions permit. It must not stop because it already traded once, reached a profitable day, lost earlier, or reached any arbitrary signal count. Zero trades is correct when nothing qualifies; four or more sequential trades is correct when four or more independent setups qualify.

1. Create an immutable `SETUP_EPISODE_ID` from specification version, instrument, exact contract, exchange-session date, family ID, independent level-cluster ID, and causal approach/break episode ID. Preserve every family/level tag associated with the physical episode.
2. Permit at most one executed entry per family per `SETUP_EPISODE_ID`. Multiple ticks, overlapping chart levels, repeated callback notifications, partial signal recomputation, or reconnect replay cannot duplicate a trade.
3. A new trade after exit requires the prior position to be flat, the prior episode to be terminal, and the exact family to re-arm from new later data. Use the already frozen two-tick retreat/new-approach reset for wall/test families. Where a family lacks an explicit reset, require price to exit the common proximity band and later re-enter, with every entry condition reforming from events after that exit. No arbitrary time cooldown is added.
4. A signal generated while another position is open is recorded at its original timestamp as `OVERLAP_SUPPRESSED`; it cannot be entered later at a stale price. This is a concurrency constraint, not a trade-count cap.
5. The earliest causally completed executable signal wins when distinct episodes compete while flat. If signals complete at the exact same timestamp and agree in direction, execute one position under the governing frozen precedence; if no precedence exists, use the lowest immutable registry family ID, while tagging every agreeing signal for attribution. If tied signals oppose, execute neither and record `SIMULTANEOUS_DIRECTION_CONFLICT`.
6. Existing account-level risk limits, emergency kill switches, disconnections, bad data, and unavailable liquidity may suppress a trade. Record the exact reason as `RISK_SUPPRESSED`, `DATA_SUPPRESSED`, or `EXECUTION_MISSED`; never misreport such cases as “no setup.” No trade-count limit may masquerade as a risk control.
7. Report the complete daily distribution of eligible episodes, executable signals, actual trades, independent re-arms, overlap suppressions, conflicts, risk/data suppressions, and trades per day. Preserve days with zero trades. Frequency, EV, and uncertainty use actual independent episodes rather than a one-trade-per-day sample.

Before outcome access, add deterministic tests proving that: (a) zero valid episodes create zero trades; (b) four sequential independent episodes create four trades; (c) repeated callbacks and overlapping levels from one episode create one trade; (d) an exit without the frozen reset cannot re-enter; (e) a later fully re-armed setup can re-enter on the same day; (f) same-direction exact ties create one tagged position; (g) opposite-direction exact ties create no position; (h) open-position signals are timestamped as suppressed and never entered late; and (i) no configurable daily/weekly trade-count cap can affect signals while governing risk kill switches remain functional.

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
- Preserve the existing hard frequency requirement of at least one independent trade per week and preferred 1.5–2+ per week. This is a minimum promotion gate, never a target or cap. Do not lower it for an attractive low-frequency near-miss, force trades to satisfy it, or discard additional valid independent trades after it is met.
- Thirty calendar days of depth data is an engineering/descriptive sample, not sufficient strategy validation. At 1–2 trades per week it may contain only about 4–8 qualifying trades.
- Apply every existing sample, net-EV, risk/reward, stability, multiple-testing, execution, and holdout gate.
- Treat the one-hour-zone module as a frozen context comparison, not a seventh Wave A entry family. Zone-only entries, zone-based stops/targets, and grade changes remain disabled unless a future separately frozen wave validates them.
- Treat the hold-versus-flush layer as a causal state/forecast overlay, not a seventh entry family. Its armed states and model probabilities are shadow-only; only exact A1-A4/A6 rule matches can enter until a separately frozen probability-policy version passes all DEV and untouched prospective gates.
- Apply the high-level quant mandate, nested chronological estimation, and uncertainty-adjusted positive-EV gate in this document. A full-sample backtest or an in-sample fitted model cannot promote.
- Any already-viewed historical period remains DEV/exploratory. Freeze the complete winning strategy before opening untouched future data.
- Run the governing minimum 100,000-path reproducible Monte Carlo only after a full DEV passer. Monte Carlo may stress a passer; it may never rescue a failed family.
- Report `NO VERIFIED EDGE` when warranted. Keep every failed cell, seed, configuration, raw result, and registry row.

## Required close-out report

For each cell, report event count, effective independent event count, eligible episodes, executable signals, trades, trades/week, percentage of active weeks, mean/median/90th-percentile/maximum trades per day, percentage of zero-trade days, same-day independent re-entries, overlap suppressions, simultaneous conflicts, risk/data suppressions, and execution misses; once-only outer-fold net expectancy, multiplicity-adjusted one-sided 95% lower confidence bound, stressed-cost net expectancy, shrinkage EV estimate, bootstrap probability `EV_net > 0`, win rate, average win/loss, profit factor, drawdown, fill rate, missed-signal rate, slippage, latency sensitivity, markouts, year/month/regime stability, ablations, multiplicity-adjusted significance, exact failed gates, and reproducibility hashes. For fitted models also report outer-fold boundaries, training-only transformations, degrees of freedom, regularization/calibration choices, learning-curve behavior, calibration, and simpler-model incrementality. Report median, mean, 10th/90th-percentile, minimum, and maximum holding time; percentages exited within 10s, 2m, 5m, 15m, and 30m; and P&L by frozen exit reason. Also report how many events were excluded for missing sequence/depth data, uncertain aggressor classification, right-censored resiliency, crossed/locked books, contract-roll contamination, or an unexecutable quote.

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
- https://ninjatrader.com/support/helpguides/nt8/onmarketdata.htm
- https://ninjatrader.com/support/helpguides/nt8/onmarketdepth.htm
- https://ninjatrader.com/support/helpguides/nt8/set_up12.htm
- https://ninjatrader.com/support/helpguides/nt8/data_files.htm
- https://ninjatrader.com/support/helpguides/nt8/playback.htm
- https://www.tradingview.com/script/Etj1ixAs-Traders-Reality-Main/
- https://www.tradingview.com/script/ZCqmZOUy-Traders-Reality-Psy-Levels-Daily-Open-GMT-Aware/
- https://www.scribd.com/document/727272438/TradersReality-Indicator-Settings-Guide
- https://arxiv.org/abs/2101.07410
- https://arxiv.org/abs/1011.6402
- https://arxiv.org/abs/1512.03492
- https://arxiv.org/abs/1312.0514
- Supplemental uploaded transcript block: https://www.youtube.com/watch?v=QXNyxgbrYro
- Supplemental uploaded transcript block: **The Secrets of Reading Level 2 (Tape Reading for Beginners)** — no supplied video ID; use the transcript text and hash above, not an inferred URL
<!-- END MROF_SOURCE_A -->

# Appendix B — Confirmed-swing successor specification

<!-- BEGIN MROF_SOURCE_B -->
# MROF-YT-OF-01.6 — CAUSAL MULTI-TIMEFRAME SWING-LEVEL SUCCESSOR

## Directive to Claude

Work inside the existing MROF repository and treat this document as an additive successor specification. Build, test, document, hash, commit, and push **MROF-YT-OF-01.6** without editing, replacing, weakening, or silently reinterpreting any frozen predecessor.

This successor adds causally confirmed swing highs and swing lows to the key-level research program. It does **not** claim they possess positive expected value. Their incremental value must be measured against the existing active-level pool using genuine future NQ/MNQ trade, BBO, and MBP-10 data after readiness gates permit outcome research.

This remains a research and shadow-execution system. It does not authorize live orders.

## 1. Governing lineage and immutable inputs

Before making changes, locate and verify the complete repository lineage, including the following authoritative artifacts when present:

- `MROF_YT_OF01_FINAL_SOURCE_PROMPT.md` — expected SHA-256:
  `74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b`
- `MROF_YT_OF01_5_SUCCESSOR_FREEZE.md` — supplied-package SHA-256:
  `b753a09cc077267a935df37f9b531f2179d920b8f76dc6ee5788628c264f7194`
- `mrofyt_engine_v015.py` — expected SHA-256:
  `e3da36cd63a18a22935124e852ce8f8b785e96df136d98944f7e88654b1c6847`

If repository filenames differ only because uploaded copies contain suffixes, resolve the canonical committed files and record their actual hashes. Stop on a substantive hash mismatch. Do not overwrite a mismatch or invent an explanation.

The following remain unchanged:

- entry families A1–A6;
- all frozen order-flow thresholds;
- wall hold/flush/reclaim state definitions;
- signal grouping, physical-approach identity, reset, re-arm, conflict, suppression, fill, latency, and ledger rules;
- the 30-minute maximum holding time and permission to exit earlier;
- NQ-signal/MNQ-execution topology;
- no daily or weekly trade cap: every independently re-armed valid setup may trade while flat;
- all data-integrity, readiness, multiple-testing, cost, slippage, and future-validation requirements.

Do not open market outcome, trade-result, or P&L data while implementing this successor. The swing rules must be frozen first.

## 2. Research question

Answer one primary question:

> When NQ/MNQ approaches a causally confirmed 5-minute, 15-minute, or one-hour swing high or swing low, does tape and market depth distinguish hold, rejection, failed break/reclaim, and accepted flush behavior with positive executable incremental EV beyond the existing MROF key-level engine?

Swing levels are hypotheses about **where** order flow may matter. They are never proof of direction by themselves. Entries still require a complete frozen A1–A6 or separately registered autonomous order-flow mechanism.

## 3. Frozen swing construction

### 3.1 Bar construction and availability

Reconstruct completed 1-minute bars causally from the audited event stream and aggregate them into exchange-calendar-aligned 5-minute, 15-minute, and 60-minute bars.

- Use exact underlying contract identifiers and raw, unadjusted prices.
- Use the versioned CME session calendar and timezone/DST implementation already governing MROF.
- Never aggregate across a contract roll, maintenance break, data gap, mixed run, or failed manifest.
- A bar is usable only after its scheduled closing timestamp and only when its source interval passes completeness checks.
- An incomplete or uncertain bar cannot form or confirm a swing. Route dependent signals to `DATA_SUPPRESSED`.
- Never use a partially formed current bar to create, move, or confirm a swing.

### 3.2 Five-bar confirmed-fractal rule

For each timeframe `TF` in `{1m, 5m, 15m, 60m}`, use five consecutive completed bars indexed `j-2, j-1, j, j+1, j+2`.

A confirmed swing high at center bar `j` exists only when:

```text
H[j] >= H[j-1]
H[j] >= H[j-2]
H[j] >  H[j+1]
H[j] >  H[j+2]
```

A confirmed swing low is the exact mirror:

```text
L[j] <= L[j-1]
L[j] <= L[j-2]
L[j] <  L[j+1]
L[j] <  L[j+2]
```

This asymmetric tie rule assigns an equal-price plateau to its last occurrence before price departs. It prevents duplicate swing IDs while retaining repeated equal-tick highs or lows. Do not substitute a different tie rule after examining results.

The swing's price comes from center bar `j`, but its **causal availability time** is the close of `j+2`. No signal, feature, grade, stop, target, or chart-location label before that timestamp may use the swing.

Store at minimum:

- `swing_id`;
- instrument and exact contract;
- session identity;
- timeframe;
- side (`SWING_HIGH` or `SWING_LOW`);
- center-bar timestamp and price;
- confirmation/availability timestamp;
- all five source-bar timestamps and OHLCV values;
- age in elapsed time, own-timeframe completed bars, and completed sessions;
- touch count and independent-approach IDs;
- current lifecycle state and state-transition timestamps;
- distance in ticks and contemporaneous completed-1m ATR units;
- overlap level IDs and independent level families.

### 3.3 Roles by timeframe

Freeze the following roles before outcomes are inspected:

| Timeframe | Frozen role |
|---|---|
| `1m` | Diagnostic/context only. It cannot create entry eligibility, change setup grade, move a stop/target, or rescue a failed strategy in v01.6. |
| `5m` | Active experimental swing entry location and target-space input after causal confirmation. |
| `15m` | Active experimental structural swing entry location and target-space input after causal confirmation. |
| `60m` | Higher-timeframe context and active experimental entry location when price enters the unchanged MROF proximity window. |

Do not introduce 3-minute, 10-minute, 30-minute, four-hour, or daily swing variants in this wave. They require a later hypothesis registration. This restriction bounds multiplicity; it does not assert those timeframes are useless.

### 3.4 Level identifiers and family voting

Create deterministic level IDs such as:

```text
SWING_5M_HIGH|contract|center_t|price_tick
SWING_5M_LOW|contract|center_t|price_tick
SWING_15M_HIGH|contract|center_t|price_tick
SWING_15M_LOW|contract|center_t|price_tick
SWING_60M_HIGH|contract|center_t|price_tick
SWING_60M_LOW|contract|center_t|price_tick
```

All active swing IDs map to exactly one independent clustering family:

```text
CAUSAL_SWING
```

A coincident 5m, 15m, and 60m swing therefore contributes one family vote, not three. Preserve each timeframe-specific level ID for diagnostics. Existing VWAP, open, prior-range, pivot, zone, psychological, ADR, and session-extreme families remain distinct under their frozen definitions.

Merge same-side swing prices into one physical swing cluster when their prices lie within the existing MROF proximity radius:

```text
max(4 instrument ticks, 0.20 * ATR(20) from completed 1m bars)
```

The cluster anchor is the earliest causally available member's price; ties use timeframe order `60m`, `15m`, `5m`, followed by lexical `swing_id`. Do not move the anchor to a later price that better explains the outcome. Add later-confirmed members to the cluster's diagnostic membership without resetting its physical approach or making it a new independent confirmation vote.

Opposite-side swings within the same proximity cluster must retain their side labels. They do not cancel silently. Any simultaneously completed opposing trade directions continue through the inherited conflict adjudication and must produce zero fill when the frozen conflict rule applies.

## 4. Frozen lifecycle

Each confirmed swing follows this causal state machine:

1. `CONFIRMED_UNTOUCHED`: available after `j+2`; no post-availability touch.
2. `ACTIVE_TESTED`: price has entered the unchanged proximity band on an independent physical approach.
3. `BROKEN_PENDING_ACCEPTANCE`: price traded at least one tick beyond the swing in the break direction, but acceptance is not yet complete.
4. `RECLAIMED_BEFORE_ACCEPTANCE`: price returned through the swing before two consecutive completed bars of the swing's own timeframe closed beyond it. This state may condition A4 only when every inherited A4 order-flow requirement is also satisfied.
5. `ACCEPTED_BROKEN`: two consecutive completed bars of the swing's own timeframe closed at least one tick beyond it in the break direction.
6. `ROLLED_OFF`: the exact contract changed or source-data certification failed.

For a swing high, “beyond” means above. For a swing low, it means below.

`ACCEPTED_BROKEN` retires the level from new entry eligibility in this wave. Do not automatically reverse its polarity into support/resistance; a polarity-flip strategy would be a separate hypothesis. Keep the retired level in the ledger for audit and target-path reconstruction.

Do not impose an optimized age cutoff. Retain a confirmed swing until accepted broken, rolled off, or invalidated by data quality. Eligibility is naturally bounded by the unchanged proximity window. Report age and freshness so later preregistered waves can test decay without choosing a favorable cutoff here.

An independent retest must use the inherited physical-approach and re-arm machinery. A label change, newly overlapping level, repeated callback, or passage of time alone cannot manufacture another setup episode.

## 5. Integration with the existing key-level engine

Add `SWING_5M_*`, `SWING_15M_*`, and `SWING_60M_*` to an **experimental active-location branch**. Do not silently rewrite the predecessor's primary active pool.

The engine must support deterministic toggles:

```text
SWINGS_OFF_PARENT
SWINGS_ONLY
PARENT_PLUS_SWINGS
PARENT_AND_SWING_OVERLAP
```

- `SWINGS_OFF_PARENT` must be bit-for-bit identical to the v01.5 executable path for the same non-outcome fixture.
- `SWINGS_ONLY` requires an eligible active swing and does not receive credit from another key-level family.
- `PARENT_PLUS_SWINGS` admits either the unchanged parent pool or an active swing.
- `PARENT_AND_SWING_OVERLAP` is a separately reported confluence branch requiring at least one unchanged parent family and `CAUSAL_SWING` in the same frozen proximity cluster.

No branch may choose a favorable label after the trade. Log the complete set of available level IDs and families at first proximity, signal completion, entry-release, fill, early exit, and terminal exit.

### 5.1 Available-R geometry

Include active confirmed swings in the already-frozen target-space calculation without altering its thresholds:

```text
Available_R = distance to next opposing eligible structural level
              / distance to frozen structural stop
```

The nearest opposing swing can reduce available target space. A same-direction supporting swing can be recorded as location context but cannot expand available space by ignoring a closer opposing non-swing level.

Preserve the existing rejection below `0.70R` and A+-eligibility requirement of at least `2.0R`. Do not assume a swing improves grade. Grade changes must be calculated causally and remain shadow-only until validated.

## 6. Order-flow questions at swings

At every eligible independent swing approach, apply the unchanged A1–A6 and wall-state mathematics. Explicitly classify and report:

- displayed wall holds with executed-volume replenishment;
- wall depletion with execution-confirmed clearance;
- non-trade withdrawal and liquidity-vacuum behavior;
- aggressive flow that fails to move price;
- multi-level sweeps and five-second reclaims;
- accepted flush through the swing;
- pullback absorption with the prevailing causal trend;
- post-contact OFI, delta, tape intensity, acceleration, spread response, resiliency, and price-response residuals;
- early invalidation when expected tape/price response fails.

MBP-10 cannot identify a named “hidden buyer,” “hidden seller,” iceberg owner, spoofer, or institution. Use participant-neutral evidence labels such as repeated executed absorption, replenishment, non-trade removal, and adverse-flow price nonresponse. Never infer identity or intent from displayed size.

The order-flow engine may enter before a 1-minute candle closes only when the swing was already causally confirmed and every applicable sub-minute signal rule is complete. An unconfirmed developing swing cannot justify a sub-minute entry.

## 7. Preregistered comparisons and hypothesis budget

### 7.1 Primary promotional comparison

Use one pooled primary comparison:

```text
PARENT_PLUS_SWINGS versus SWINGS_OFF_PARENT
```

Require stable, cost-adjusted incremental EV rather than merely more trades. The addition fails if it raises gross opportunity count but worsens executable expectancy, drawdown, tail risk, calibration, or prospective stability.

### 7.2 Required secondary comparisons

Report, with multiplicity control:

1. `SWINGS_ONLY` versus time-of-day, volatility, spread, trend, approach-velocity, and touch-count-matched non-swing locations.
2. `PARENT_AND_SWING_OVERLAP` versus matched parent-only approaches.
3. 5m versus 15m versus 60m swing IDs as diagnostics; none may rescue a failed pooled result.
4. Swing highs versus swing lows as diagnostics.
5. Confirmed-untouched versus previously tested swings.
6. Wall episodes at swings versus wall-size-matched episodes outside all active key-level windows.
7. Hold/reclaim, failed-flush/reclaim, and accepted-flush outcomes at 5s, 10s, 30s, 2m, 5m, 15m, and the inherited 30-minute cap.
8. Existing one-hour supply/demand zones versus simple 60m swings at identical parent-signal times, preserving the predecessor's required zone ablation.
9. L1-only versus L1+L2 at swing approaches.

Apply the inherited family-wise multiple-testing procedure across all new swing branches, timeframes, sides, lifecycle states, order-flow interactions, and management comparisons. Failed and inconclusive tests permanently consume their hypothesis fingerprints.

Do not optimize pivot width, left/right bar count, tie treatment, timeframe list, acceptance count, proximity radius, lifecycle, or age after outcomes are opened. Any future alternative becomes a separately numbered wave with a fresh validation clock.

## 8. Readiness and evidence standards

Implementation may occur now. Promotional outcome research may not begin until the governing MROF readiness gates are satisfied with genuine audited data.

At minimum:

- genuine NQ and MNQ trades, BBO, and both-sided MBP-10 events;
- passing manifests, hashes, global sequencing, enum, contract, session, depth-side/action, gap, duplicate, restart, and roll audits;
- causally reconstructable complete bars for each tested timeframe;
- strict prior-session baselines wherever required;
- realistic commissions, spread, slippage, latency, partial fills, misses, and data gaps;
- no use of synthetic tests as evidence of positive EV;
- chronological walk-forward evaluation with purging/embargo as applicable;
- untouched future validation after a strategy is frozen;
- all inherited frequency, regime-stability, bootstrap/permutation, multiple-testing, drawdown, concentration, delayed-entry, and cost-stress gates.

If captured sessions remain zero or readiness is otherwise insufficient, return exactly:

```text
INSUFFICIENT_DATA
```

Build the machinery and tests, but do not fabricate a research result.

## 9. Required implementation artifacts

Create additive artifacts using repository conventions, including at minimum:

- `mrofyt_swings_v016.py` — bar aggregation, confirmed swings, clusters, lifecycle, and feature records;
- `mrofyt_engine_v016.py` — sole v01.6 executable research entrypoint, inheriting v01.5 behavior and adding the frozen swing toggles;
- `tests_mrofyt_v01_6.py` — deterministic and adversarial tests;
- `MROF_YT_OF01_6_SUCCESSOR_FREEZE.md` — complete equations, roles, lifecycle, toggles, hashes, traceability, commands, counts, blocked items, and classification;
- an updated review-package manifest and ZIP containing the entire required lineage and v01.6 additions.

Do not modify predecessor files. Pin and reverify their hashes from the v01.6 suite. The v01.6 engine must not route through superseded coordinators. Reuse the authoritative v01.5 coordinator behavior rather than copying an older version.

## 10. Mandatory deterministic and adversarial tests

At minimum, prove all of the following:

1. A center high/low cannot become available until the second right-hand bar closes.
2. Reversing callback arrival order cannot alter a swing ID, cluster ID, approach ID, or adjudication.
3. The asymmetric equal-price plateau rule creates one deterministic swing rather than duplicates.
4. Partial, gapped, maintenance-window, holiday-misaligned, mixed-session, mixed-run, or mixed-contract bars cannot form a swing.
5. 1m-to-5m/15m/60m aggregation is exchange-calendar aligned and never crosses a contract roll.
6. `1m` swings remain diagnostic and cannot create entry eligibility or affect grade/geometry.
7. Confirmed 5m/15m/60m swings can create experimental eligibility only after availability.
8. Coincident swing timeframes produce one `CAUSAL_SWING` family vote while retaining all level IDs.
9. A later-confirmed overlapping swing cannot reset a physical approach already in progress.
10. Two own-timeframe closes beyond a level create `ACCEPTED_BROKEN`; a reclaim before the second close creates `RECLAIMED_BEFORE_ACCEPTANCE`.
11. An accepted-broken swing cannot silently flip polarity or generate a new trade.
12. Contract roll retires prior-contract active swings.
13. Duplicate callbacks and stale signals cannot generate duplicate episodes.
14. Opposing exact-time signals still conflict before any fill and create zero filled quantity.
15. Every suppression, miss, conflict, trade, lifecycle transition, and terminal outcome receives a complete ledger record.
16. Four sequential, independently re-armed valid setups can still produce four trades; no daily trade counter exists.
17. `SWINGS_OFF_PARENT` is bit-for-bit identical to v01.5 on the same deterministic fixture.
18. No production or research source submits, modifies, or cancels a live order.
19. The full inherited suite plus the v01.6 suite passes.

Synthetic tests prove implementation behavior only. State that explicitly.

## 11. Required final response

Return:

1. The new successor-freeze filename and SHA-256.
2. Every created or modified additive filename and SHA-256.
3. Confirmation that no predecessor was edited, with reverified hashes.
4. Exact commands and unabridged test counts.
5. A requirement-to-code-to-test traceability table.
6. Confirmation that `SWINGS_OFF_PARENT` is bit-for-bit identical to v01.5.
7. The number of genuine captured sessions and the resulting readiness classification.
8. Every blocked user-side step, especially NT8 F5 compilation or Market Replay/live smoke testing that this environment could not genuinely perform.
9. A plain-language description of what swing levels can and cannot do.

Do not describe successful synthetic tests as validation, profitability, prediction accuracy, or positive EV. Until audited sessions exist and the complete research and future-validation gates pass, the only honest classification remains `INSUFFICIENT_DATA`.
<!-- END MROF_SOURCE_B -->

# Appendix C — Liquidity-target and flow-controlled exit experiment

<!-- BEGIN MROF_SOURCE_C -->
# MROF — Liquidity-target and tape-controlled exit research

## Task and scope

In the existing MROF repository, implement an additive, preregistered exit experiment. Determine whether liquidity-targeted or flow-controlled exits improve the existing tape-scalping strategies after execution costs. Build engineering fixtures now; run market-outcome research only when the inherited readiness gates and conditional management gates permit it.

This is a research/shadow implementation, not authorization to place live orders. Do not promise positive EV. Do not alter the recorder merely to support this experiment unless an actual schema deficiency is identified and documented separately.

Audit the latest authoritative executable engine, source prompt, freezes, hypothesis registry, and management comparisons first. Select the next unused successor identifier; do not assume v01.6 was implemented merely because a swing prompt exists. Pin actual predecessor hashes, preserve frozen files, and document all additions. Reuse existing authoritative features and execution machinery after checking that their behavior is fit for this experiment.

Keep A1–A6 entries, entry eligibility, initial protective stops, position sizing, session windows, and the 30-minute maximum unchanged. Preserve every independent valid setup without an arbitrary daily/weekly trade-count cap, subject to existing position, risk, data, and re-arm rules. Exit rules may change how long a position occupies the account; measure that effect explicitly.

## 1. Exactly three exit arms

E0 — Parent: reproduce the actual frozen baseline exits, including its fixed profit target, early invalidation, stop, session flattening, and timeout. Verify what the executable code actually does; do not assume all proposed management comparisons are already active.

E1 — Liquidity hybrid: preserve the parent's protective stop, early invalidation, session flattening, and timeout. Replace only its fixed profit target with the nearest qualifying opposing displayed-liquidity target defined below. This arm takes profit before the selected wall; it does not also introduce a runner or discretion to hold through that wall.

E2 — Flow-controlled: preserve the same protective stop, early invalidation, session flattening, and timeout. Remove the fixed profit target and add the confirmed opposing-control exit below. This arm may continue through a consumed wall while the frozen exit conditions remain false. Absence of an exit condition does not mean certainty that control persists.

No new scaling-in, partial-profit, breakeven, trailing-stop, or runner variants in this wave. Existing risk-reducing actions common to the baseline remain common. Map overlap with earlier management hypotheses into the spent registry; relabeling a previous test does not create a new independent hypothesis.

## 2. Signal and execution books

Maintain exact contract identities and separate NQ signal observations from MNQ execution observations. Use NQ for inherited flow/control features, and MNQ for E1's executable liquidity target and all fill simulation. Never transfer an NQ wall price into an MNQ order without an explicitly registered mapping experiment; no such mapping experiment is authorized here.

Use only audited event data available to the strategy at the decision time. Record event and receive clocks, source ordering, availability timestamps, quote age, feed health, and aggressor-classification uncertainty. A price level that was last changed some time ago is not necessarily stale: distinguish an unchanged valid level from an unhealthy or disconnected book.

Reuse documented freshness/health gates. If a required gate is absent, specify one engineering policy with rationale and fixtures before inspecting outcomes; list it as a new assumption, not an inherited rule. Never silently weaken a gate to produce more trades.

## 3. Frozen E1 wall-selection rule

The following are initial research choices, not established optimal settings. Do not tune them after seeing results.

At the parent's target-initialization time, using the latest valid MNQ book available then, consider ask levels for a long and bid levels for a short. A candidate must:

- lie strictly in the profitable direction from the actual entry fill;
- lie within the currently supported, visible depth;
- have current displayed size at robust time-of-day z-score >= 2.0, calculated using the existing strict prior-20-session median/MAD baseline on that instrument, side, and depth rank;
- have remained continuously visible at the same price for the preceding two seconds with z-score >= 1.5 throughout the supported observations;
- have a valid baseline and complete observable history for that persistence interval.

If compatible rank/side baselines do not exist, implement them from prior sessions only, freezing slot definitions before research. Missing baselines or zero MAD make the candidate unavailable; do not add an outcome-tuned epsilon.

Choose the nearest qualifying price. Set the profit-taking trigger one MNQ tick before that wall: wall minus one tick for a long; wall plus one tick for a short. Require that trigger to remain beyond entry in the profitable direction. Freeze the price, side, size, z-score, observation window, and selection timestamp.

If no wall qualifies, use the parent's fixed target for the whole trade and label NO_QUALIFYING_LIQUIDITY_TARGET. If only incomplete data prevents selection, label TARGET_DATA_UNAVAILABLE and follow inherited data-health rules. Neither fallback may be reported as a successful liquidity-target trade.

The selected trigger does not move after entry. Track subsequent wall changes diagnostically, but do not chase a new wall, extend the target after removal, or retroactively select a better wall. This tests one clean hybrid hypothesis. Dynamic retargeting requires a later wave.

Trigger profit-taking when the executable MNQ bid reaches or exceeds the trigger for a long, or the executable ask reaches or falls below it for a short. Submit a simulated market exit through the latency/fill engine. This is not a resting limit order and does not assume a fill at the wall or trigger price.

## 4. Frozen E2 opposing-control exit

Use the inherited 10-second window and its four persistence subwindows. At a completed window, require all of:

- the existing signed control score favors the direction opposite the position at magnitude z >= 1.0;
- at least three of four subwindows favor that opposing direction;
- NQ price progress across the completed window is adverse to the position by at least one NQ tick, using the parent's frozen price-response convention.

If true, issue a simulated market exit on MNQ after the decision becomes available. Inherited early-invalidation exits may fire sooner. Define exact score polarity and cite the authoritative implementation. Do not substitute unsigned intensity for signed control.

Confirm all timing against observed data: a completed 10-second condition cannot be used to exit at its beginning. Wall disappearance by itself does not trigger continuation or exit. Missing features are unknown, not zero or favorable control.

## 5. Book accounting and protective execution

Track executions, displayed additions, net size changes, removal, and loss of visibility separately. MBP changes do not always uniquely identify cancellations or hidden replenishment. Record ambiguous attribution as unknown. A level moving outside the visible ten-level window is not evidence of cancellation or complete consumption.

In replay, fills must use later, valid MNQ bid/ask/depth after the applicable latency; include spread, commissions, slippage, available quantity, and partial fills. Never fill against an already consumed snapshot twice. Do not invent liquidity beyond the captured book.

An unfilled exit remainder remains an open position. Preserve stop protection and track subsequent liquidation attempts under a frozen policy; do not cancel the remainder and pretend the trade is flat. Gaps or insufficient visible depth must produce unresolved/stressed execution outcomes rather than optimistic P&L. Report these cases in the denominator.

At a common decision timestamp, protective exits take precedence over profit-taking; record all reasons. Preserve event ordering and the inherited hard timeout. Distinguish a liquidation instruction issued by the deadline from the actual fill, which may be later. Never manufacture a deadline fill during a disconnect.

## 6. Fair comparison and bounded research

Use two explicitly different evaluations:

1. Paired exit attribution: replay each frozen parent entry with identical entry fill, quantity, initial stop, and initial risk in three isolated shadow trades. This isolates exits. Hypothetical trades may overlap; this is not a deployable portfolio equity curve, and cross-arm liquidity consumption is not added together.
2. Deployable sequential replay: run each complete arm independently under identical account limits, one-position gating and genuine re-arm rules. Faster/slower exits can admit/suppress different subsequent entries. Report that difference rather than claiming entries remain identical here.

Pre-register E1 minus E0 and E2 minus E0 as the two primary exit comparisons and correct them jointly under the governing research protocol. Treat E1 versus E2 and wall/side/time-of-day subdivisions as secondary diagnostics, with applicable multiplicity control. Preserve all previous trials and failed fingerprints. Do not silently replace an inherited statistical method with another.

Report net expectancy per trade and per day, paired net-P&L differences, drawdown, tail loss, holding duration, maximum adverse/favorable excursion, favorable excursion given back before exit, realized reward/risk, costs, partial/unresolved fills, target fallback rate, and entry opportunity changes. Resample by session or longer blocks where needed to preserve dependence; millions of callbacks are not millions of independent samples.

Do not require every metric to improve. Promotion requires the governing positive-net-EV and incremental-evidence gates plus acceptable preregistered risk limits. Choose one primary economic metric and its inferential method before opening outcomes, document it, and do not switch metrics to rescue a loser.

Maintain chronological development/validation separation, overlapping-label purging where appropriate, cost/latency stresses and concentration checks. Freeze the selected complete strategy before prospective confirmation. Three or six months is not an automatic pass: report readiness from data quality, independent opportunities, uncertainty and observed conditions. If existing calendar gates differ, disclose them; do not bypass the source protocol.

## 7. Required proof and delivery

Add meaningful tests for:

- E0 parity with the authoritative parent, including fills and ledger;
- future-data perturbations leaving earlier targets/decisions unchanged;
- two-second persistence, missing/zero-MAD baselines and absent walls;
- mirrored long/short targets and selection from MNQ rather than NQ;
- wall removal or depth-window exit not moving the frozen trigger;
- E2 signed score, completed windows, three-of-four persistence and adverse-price confirmation;
- healthy unchanged levels versus an unhealthy feed;
- exit latency, partial fills, remaining position protection and unresolved gaps;
- stop/target/time precedence and no impossible deadline fills;
- identical paired entries versus independently gated sequential replays;
- repeated valid setups remaining uncapped and all exclusions being logged;
- no live order submission and unchanged predecessor hashes.

Deliver additive modules, tests, a successor freeze with actual SHA-256 hashes, a runnable research command, a complete review package, and concise requirement-to-code-to-test traceability. Report actual test output and distinguish synthetic correctness from market evidence. Do not claim commits, pushes, NT8 compilation, smoke tests, or positive EV unless actually performed and supported.

Classify separately: implementation complete/blocked; data sufficient/insufficient; market research not run/passed/failed/inconclusive; prospective validation not started/in progress/passed/failed. INSUFFICIENT_DATA is appropriate when data readiness fails, not a permanent label after sufficient research returns no edge.

Finish by stating which exits are implemented, which studies actually ran, whether either alternative improved the parent, and what remains unverified. A valid result is that the original exit works better or that no verified edge exists.
<!-- END MROF_SOURCE_C -->
