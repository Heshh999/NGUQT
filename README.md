# NGUQT

## Reproducible Quantitative Research, Market Data, and Execution Platform

NGUQT is an end-to-end Python and C# platform for turning trading ideas into **causal,
falsifiable, testable software experiments** on NQ/MNQ index futures. It covers the full
research lifecycle: auditing and canonicalizing market data, building multi-timeframe
feature and context engines, freezing hypotheses before results are inspected, simulating
them under explicit cost and latency assumptions, validating them out-of-sample, and
recording every outcome — including failures — in a permanent registry. A purpose-built
NinjaTrader 8 recorder captures live Level II market depth, time-and-sales and BBO data.
The platform's defining property is not any single strategy; it is the **discipline that
makes each result trustworthy**, including the many that came back negative.

---

## Important research status

**This repository contains research infrastructure, not a validated or profitable trading
system.** Of 99 registered hypotheses, **67 are recorded as `DEAD_FROZEN`** (tested and
rejected), 13 as descriptive-only, 14 reserved and untouched, 2 as insufficient-data, and
3 as passing historical-exploratory screens only — none is promoted to live trading. The
order-flow research program is currently classified `INSUFFICIENT_DATA`. **No strategy in
this repository is approved for unattended live deployment**, and nothing here should be
read as evidence of profitability.

---

## System scale at a glance

Recalculated from Git-tracked files at the current commit:

| Dimension | Measured |
|---|---|
| Tracked files | **827** |
| Python / C# / Markdown files | 222 / 49 / 190 |
| Python / C# lines | 69,450 / 27,917 (**97,367** combined) |
| Analysis module directories | **39** |
| Dedicated test files | **34** (26 Python suites, 8 C# suites) |
| Findings reports | **52** |
| Protocol, preregistration and freeze documents | **53** |
| Data and provenance audits | 17 |
| Registered hypotheses / distinct mechanism classes | **99 / 30** |
| Canonical 1-minute records | **2,503,622** |
| Exchange trading days covered | **2,218** (2019-07-04 → 2026-08-17 ET) |

The canonical dataset's complete audit is documented in
[`analysis/mgsd/MGSD_V1_DATA_AUDIT.md`](analysis/mgsd/MGSD_V1_DATA_AUDIT.md). Related
ES/NQ and IFVG reports —
[`docs/ES_NQ_DATA_V1_AUDIT.md`](docs/ES_NQ_DATA_V1_AUDIT.md) and
[`docs/MEMORY_MATH_IFVG_V1_FINDINGS.md`](docs/MEMORY_MATH_IFVG_V1_FINDINGS.md) —
independently cross-check portions of the same canonical source.

The MGSD audit specifically records **0 duplicates, 0 OHLC violations and 0 non-positive
prices**, alongside 6,059 zero-volume bars retained and flagged rather than silently
dropped, and 1,241,630 missing minutes attributed to weekends, holidays, maintenance and
halts.

---

## Architecture

```mermaid
flowchart TD
    A["Historical MNQ OHLCV data"] --> B["Data audit and canonicalization"]
    H["Live NQ/MNQ Level II data"] --> I["Event capture and book reconstruction"]
    B --> C["Feature and context engines"]
    I --> C
    C --> D["Frozen hypotheses and test harnesses"]
    D --> E["Cost-aware simulation"]
    E --> F["Out-of-sample and robustness validation"]
    F --> K{"Promotion gates passed?"}
    K -->|"No"| G["Findings and rejection registry"]
    K -->|"Yes"| J["Prospective NinjaTrader integration"]
    J --> G
    I --> M["God's Eye View: read-only monitoring dashboard"]
```

### Level II order-flow pipeline and the God's Eye View

The live order-flow program runs as a separate, outcome-blind pipeline. Every arrow into
the dashboard is a read; nothing in it can write to the capture, change a frozen
hypothesis, or place an order.

```mermaid
flowchart TB
    subgraph REC["Recorder laptop - Windows, NinjaTrader 8"]
        R["MlesV12CaptureHost 1.2.2<br/>NQ + MNQ depth, trades, quotes, quality"]
    end
    R -->|"per-run CSVs + hashed manifest"| CF[("Capture folder<br/>external drive")]
    CF --> AU["Auditor<br/>mles_v12_audit"]
    CF --> RC["Recovery tool<br/>mrofyt_recover"]
    RC -->|"reconstructed manifests;<br/>originals never modified"| CF
    CF --> RN["Outcome-blind runner<br/>mrofyt_runner"]
    RN --> PI["Pilot diagnostic<br/>mrofyt_pilot"]
    RN --> W2["Wave-two families<br/>mrofyt_wave2"]
    PI -->|"labels every inspected day"| LG[("Exposure ledger<br/>EXPOSED_PILOT_DEV")]
    AU --> RP[("Reports<br/>audit, recovery, ledger,<br/>pilot, wave two, windows")]
    RC --> RP
    RN --> RP
    PI --> RP
    W2 --> RP
    LOCK["Outcome lock<br/>STATE-C file absent"] -.->|"outcomes stay locked"| RN
    subgraph GE["God's Eye View - read-only, 127.0.0.1"]
        EX["Exporter<br/>bounded reads + blind policy"] --> SN[("Snapshot JSON")]
        SN --> SV["Local server"]
        SV --> UI["Browser: recording health, hypothesis readiness,<br/>mechanism theatre, provenance, exposed-data replay"]
    end
    CF -.->|"manifests, file tails,<br/>Windows liveness check"| EX
    RP -.-> EX
    LG -.-> EX
```

**How the God's Eye View is built** ([`analysis/godseye/`](analysis/godseye/GODS_EYE_README.md)):

- **Exporter** (`godseye_export.py`, a separate process every 5 minutes at below-normal
  priority): reads manifests, the last 64 KB of open streams, one `stat()` per file and
  the report files; asks Windows directly whether NinjaTrader still holds a run; writes
  only into its own output folder, never inside the capture folder. A file the drive
  refuses to read is remembered and not re-read.
- **Blind policy** (`godseye_policy.py`): every session is `EXPOSED`, `BLIND` (the
  hold-out from 2026-09-21), `PROTECTED_UNLISTED` or `UNKNOWN`, and it fails closed.
  Event-level fields are stripped from every non-exposed section, and the finished
  snapshot is scanned before it is written; a hit refuses the write.
- **Server** (`godseye_server.py`, stdlib HTTP on 127.0.0.1): serves the snapshot,
  refuses replay or evidence requests for any session the ledger does not label exposed
  (HTTP 403), and re-reads the ledger when it changes.
- **Page** (vanilla JavaScript, no framework): five views. One of them is a mechanism
  theatre, where each frozen hypothesis has a scripted demonstration and a
  counter-example; the tests run each script through the frozen detector code itself.
- **Verified by** `tests_godseye.py` (46 checks): no writes to the capture folder, no
  event-level key outside the exposed section, 403 for blind and unlisted sessions, no
  order API in any dashboard file, demos consistent with the frozen detectors.

---

## What the platform does

**Data auditing and canonicalization.** Raw vendor exports are never trusted. Loaders
verify timestamp monotonicity, duplicate keys, OHLC consistency, session boundaries,
contract-roll windows and volume sanity before any feature is computed; conflicting
duplicates fail closed rather than merging silently.

**Feature and context engines.** Causal multi-timeframe aggregation, key-level hierarchies,
pivots, VWAP state, supply/demand zone context, volatility and volume regime
classification, and order-flow features including order-flow imbalance, book imbalance,
replenishment and depletion ratios, sweep detection and flow persistence.

**Frozen hypotheses.** Under the current governed research workflow, promotional
specifications — features, thresholds, entries, exits, costs, exclusions — are frozen
before outcomes are inspected. Thresholds must come from distributional rules or mechanism
logic; exploratory parameter scans cannot qualify a strategy on their own.

**Cost-aware simulation.** Fills are modeled against the first executable book snapshot
after a modeled latency, with partial fills, cancellation of the remainder, spread,
commissions and slippage. Latency is stress-tested, not assumed.

**Validation.** Day-block bootstrap and permutation testing (44 and 35 modules
respectively), negative controls, confidence intervals, out-of-sample and holdout
partitions, and multiple-comparison corrections across 12 modules.

**Registries.** A cumulative spent-hypothesis registry with mechanism fingerprinting and a
similarity screen blocking re-tests of a dead idea under a new name.

**Live capture.** A NinjaTrader 8 recorder writes Level II depth, time-and-sales and BBO
into hashed, per-run manifested files. It implements session and contract rotation,
disconnect/reconnect handling and restart-safe auditing. Build 1.2.2 records on the
operator's NinjaTrader; its disconnect repair has been exercised on real data (the
auditor reports 32 feed disconnects across 14 repaired-build runs with zero spurious
`BOOK_READY`, against 2 and 14 on the two earlier builds).

**Audit and recovery.** The streaming auditor verifies every manifest's hashes, row
counts, sequence continuity and NQ/MNQ pairing, and tells a run still being recorded apart
from an orphan by asking Windows directly. The recovery tool rebuilds manifests for runs
killed before finalizing (power loss, a dropped drive). It never modifies an original
file, refuses any run the recorder still holds, and refuses a repair that would leave the
recording drive under 40 GB free. A file the drive cannot read is set aside rather than
stopping the pass. A real pass reports each run as it goes, oldest session first. If a
write fails, it asks the drive and the folder separately and says which one stopped
answering, takes back that run's unfinished copies, and stops. A manifest left by an
interrupted pass is checked against its files before it is trusted.

**Outcome-blind ingest.** The ingest runner computes the frozen features and detector
firings without computing any outcome. The outcome stage is locked behind an
authorization file that does not exist. A run with any decode failure or read error is
skipped whole and wound back, so a skipped run leaves no counts behind. A capture that
cannot be read stops the pass with no ledger, rather than reporting a quiet market.

**Monitoring — the God's Eye View.** A local, read-only research dashboard covering
recording health, hypothesis readiness, data provenance and exposed-data replay, with the
validation blind enforced in its backend (see the architecture above).

---

## Research and engineering standards

- **Negative results are kept.** Without the 67 dead hypotheses the multiplicity burden
  cannot be honestly accounted for.
- **Causality enforcement.** Features must be computable at decision time; snapshot
  helpers raise on lookahead rather than warning.
- **Fail closed.** Ambiguous data quarantines a batch instead of being repaired in place.
- **Blinding in code.** Days inspected by the pilot are permanently labelled
  `EXPOSED_PILOT_DEV`; the validation hold-out is withheld by the tools and the dashboard's
  backend, not by convention.
- **Explicit epistemic status.** Documents state what was verified, what was inferred, and
  what was not run.
- **Corrections of record.** A disproven claim is amended into its freeze document rather
  than quietly edited.

---

## Representative evidence — Start Here

| Read this | Why it matters |
|---|---|
| [`analysis/mofad/MOFAD_V1_SPENT_HYPOTHESIS_REGISTRY.csv`](analysis/mofad/MOFAD_V1_SPENT_HYPOTHESIS_REGISTRY.csv) | 99 hypotheses, dispositions, binding failure reasons |
| [`analysis/mgsd/MGSD_V1_DATA_AUDIT.md`](analysis/mgsd/MGSD_V1_DATA_AUDIT.md) | Dataset audit that disproved a claim in its own task statement |
| [`docs/ES_NQ_DATA_V1_AUDIT.md`](docs/ES_NQ_DATA_V1_AUDIT.md) | A `NOT READY` verdict blocking a program on insufficient coverage |
| [`analysis/rvmr/RVMR_5Y_OUTPUT.txt`](analysis/rvmr/RVMR_5Y_OUTPUT.txt) | 11-test, 5-year regime battery, year-by-year monotonicity |
| [`analysis/mrofyt/MLES_CAPTURE_V12_FREEZE.md`](analysis/mrofyt/MLES_CAPTURE_V12_FREEZE.md) | Recorder freeze including a failed compile and its correction |
| [`analysis/rnvp/RNVP_V1_FINDINGS.md`](analysis/rnvp/RNVP_V1_FINDINGS.md) | A rejection: positive point estimates that failed significance |
| [`analysis/mofad/MOFAD_V1_PROTOCOL_FREEZE.md`](analysis/mofad/MOFAD_V1_PROTOCOL_FREEZE.md) | Full preregistration structure |
| [`analysis/mrofyt/OPERATING_RUNBOOK.md`](analysis/mrofyt/OPERATING_RUNBOOK.md) | Operational capture procedure |
| [`analysis/godseye/GODS_EYE_README.md`](analysis/godseye/GODS_EYE_README.md) | The read-only dashboard: permission model, blind enforcement, verification |
| [`analysis/mrofyt/REVIEW_PACKAGE_MANIFEST_v01_6_7.md`](analysis/mrofyt/REVIEW_PACKAGE_MANIFEST_v01_6_7.md) | Hash-pinned review package and every amendment, including defects found on real data |
| [`analysis/mrofyt/RUNNER_GUIDE.md`](analysis/mrofyt/RUNNER_GUIDE.md) | Running the outcome-blind ingest runner, and what each skip means |
| [`docs/COMPLIANCE_AUDIT_V6.md`](docs/COMPLIANCE_AUDIT_V6.md) | Rule-by-rule audit listing open issues |

---

## Repository structure

```
analysis/   39 research modules — features, protocols, findings, registries, tests
  mrofyt/   Level II order flow: capture audit, recovery, outcome-blind runner, pilot, wave two
  godseye/  God's Eye View: read-only research dashboard (stdlib Python + vanilla JavaScript)
docs/       101 protocol, preregistration, findings, audit and runbook documents
src/        34 C# files — NT8 strategies, research hosts, capture recorders
tests/      C# deterministic suites, NT8 API stubs, parity drivers
```

---

## Technology and engineering capabilities

**Python 3:** NumPy- and Pandas-based quantitative research modules, alongside
standard-library streaming pipelines for memory-bounded ingestion, auditing, hashing and
statistical validation. The Level II audit and ingestion path uses heap-merged streaming
and bounded-memory processing for multi-gigabyte event files.

**C# / .NET (NinjaTrader 8):** strategy and indicator hosts, a permanent-worker capture
architecture with atomic sequence assignment under a single lock, atomic file finalization
with per-run hashed manifests, and Mono-compatible engine cores testable without
NinjaTrader.

**Engineering practices:** deterministic tests over synthetic fixtures, adversarial tests
that falsify manifests to prove auditors catch tampering, lifecycle harnesses exercising
real concurrency and rotation, hash-pinned lineage across freezes, and import-graph proofs
that one wired entrypoint is the only executable path.

---

## Running selected tests

Dependencies vary by module: many research modules require NumPy (MGSD among them) and
some require Pandas, while the Level II capture, audit and ingestion path runs on the
standard library alone.

```bash
cd analysis/mrofyt && python3 tests_mrofyt.py          # 59 assertions
cd analysis/mrof   && python3 tests_mrof.py            # 42 assertions
cd analysis/mofad  && python3 tests_closure.py         # registry closure
cd analysis/mgsd   && python3 tests_mgsd.py            # 19 assertions (requires NumPy and the dataset)
```

The Level II order-flow package and the dashboard run on the standard library alone,
from a fresh clone:

```bash
cd analysis/mrofyt  && for f in tests_*.py; do python3 "$f" | tail -1; done   # 15 suites, 584 checks
cd analysis/godseye && python3 tests_godseye.py                               # 46 checks
```

At the current commit those 630 checks all pass, both from the repository and from inside
the unzipped review package
([`REVIEW_PACKAGE_MANIFEST_v01_6_7.md`](analysis/mrofyt/REVIEW_PACKAGE_MANIFEST_v01_6_7.md)
pins every file by SHA-256). Four historical suites (MGSD, MOFAD, MTF, VTBS) need the
canonical 1-minute dataset, which is never committed, so they stop at their first
real-data check in a fresh clone. Every other Python suite runs, and all pass except one
known, deliberate check in `tests_nmae_precondition.py` (18/19). That check compares an
immutable 78-row historical ontology snapshot with the current 99-row registry; it
correctly reports the difference and exits nonzero. The last full run with the dataset
present reported 549 passing checks plus that same mismatch.

C# engine suites run under Mono or .NET, no NinjaTrader required:

```bash
cd tests && mcs -out:run_tests.exe \
  ../src/MnqTwoStrategiesShared.cs ../src/FakeBreakoutEngine.cs \
  ../src/VectorBreakRetestEngine.cs MockHost.cs Tests.cs && mono run_tests.exe
```

A separate syntax and binding check against NT8 API stubs is documented in
[`tests/README_NTSTUBS.md`](tests/README_NTSTUBS.md); a clean compile there verifies member
names and overload shapes only, and is **not** evidence of runtime correctness.

**NinjaTrader installation.** Installation differs by component. For the automated
strategy, copy `src/MnqTwoStrategies.cs`, `src/MnqTwoStrategiesShared.cs`,
`src/FakeBreakoutEngine.cs`, and `src/VectorBreakRetestEngine.cs` into
`Documents\NinjaTrader 8\bin\Custom\Strategies\`. For Level II capture, create a
NinjaScript Indicator or place `src/MlesV12CaptureHost.cs` in
`Documents\NinjaTrader 8\bin\Custom\Indicators\`. Compile with **F5**. The automated
strategy must be applied to an MNQ chart and refuses non-MNQ instruments. Read
[`docs/COMPLIANCE_AUDIT_V6.md`](docs/COMPLIANCE_AUDIT_V6.md) and
[`docs/CHANGELOG_V6.md`](docs/CHANGELOG_V6.md) before interpreting a backtest;
[`analysis/mrofyt/OPERATING_RUNBOOK.md`](analysis/mrofyt/OPERATING_RUNBOOK.md) covers
capture installation and operation.

---

## Current status and limitations

- **No validated edge exists.** The great majority of tested hypotheses were rejected.
- The historical dataset is **OHLCV only** — no historical bid/ask, trade prints or depth.
  Depth data cannot be reconstructed retrospectively; it exists only from the moment
  capture begins.
- Order-flow research is at `INSUFFICIENT_DATA` pending a minimum number of recorded
  sessions; the outcome stage is gated behind an authorization file that does not exist,
  and the ingest runner raises rather than computing outcomes.
- Three candidates are frozen awaiting prospective validation; none is promoted.
- Recorder build 1.2.2 is compiled in NinjaTrader and recording NQ and MNQ; the auditor
  confirms its disconnect repair on real feed disconnects. Mono stub compiles elsewhere in
  the repository prove syntax only.
- The order-flow pilot has inspected five sessions (2026-09-01 to 09-05), each labelled
  `EXPOSED_PILOT_DEV` for good. Sessions from 2026-09-21 onward are a validation hold-out
  that the tools and the dashboard withhold. Two wave-one families are
  `IMPLEMENTED_NOT_WIRED`. A5 has four of its five frozen inputs uncomputed, so it cannot
  fire on real data. A4 runs with one of its two alternative residual inputs uncomputed.
- The capture drive recorded file-system damage in two depth files after a disconnect on
  2026-09-22. The audit and recovery tools set those runs aside rather than reading
  guessed data. The first full repair pass, on 2026-09-26, stopped partway when Windows
  refused to create a file on that drive and the folder stopped listing; recovery 1.5
  reports which part failed and checks the folder takes a new file before it starts.
- A genuine MNQ run recorded a 259 ms median receive-minus-exchange timestamp difference.
  Clock-synchronization confounding remains unresolved, so this is recorded but not
  interpreted as pure feed or network latency — see
  [`analysis/mrofyt/MLES_CAPTURE_V12_FREEZE.md`](analysis/mrofyt/MLES_CAPTURE_V12_FREEZE.md).

---

## My role and use of AI assistance

I defined the research questions, trading constraints, acceptance gates, validation
standards and deployment requirements; directed iterative AI-assisted implementation;
reviewed results; maintained the experiment and exposure registries; and managed the
NinjaTrader data-capture and verification workflow.

AI coding assistants were used extensively for implementation, code review and
documentation throughout.

**To be unambiguous:** NGUQT demonstrates **AI-assisted software engineering**. It does
**not** contain, implement or depend on an LLM, RAG pipeline or agent framework at runtime.
No model is invoked by any code in this repository. Every runtime component is
deterministic Python or C#.

---

## Research and risk disclaimer

This repository is research infrastructure published for engineering and methodological
review. It is **not** investment advice and **not** an offer of any financial product.

The Level II capture components and the God's Eye View are read-only and contain no
order-submission APIs (the dashboard's suite scans every one of its files for one).
Separate NinjaTrader strategy code contains order-entry methods, but it is not presented as
validated or approved for live use.

Futures trading carries substantial risk of loss. Historical or simulated results —
particularly the rejected hypotheses documented here — do not indicate future performance.
