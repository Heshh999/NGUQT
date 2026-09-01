# DATA_HANDOFF_v01_3.md — completed recorder→research handoff contract

Supersedes the v01.2 `DATA_HANDOFF.md` (unchanged, hash-pinned).
Implements the final prompt's handoff requirements verbatim.

## 1. What moves, and how (no credentials, ever)

Nothing is uploaded silently. The user **explicitly copies** closed
session folders — never files still being written — by one of:

1. Uploading the closed raw session folder + manifests into this
   project/repository; or
2. Running Claude Code locally with a read-only **`data_root`**
   pointing at the capture directory (record the exact path).

Send **manifests first** (`MLES_<inst>_<session>_manifest.json`,
tiny): they carry schema version, run id, contract, first/last receive
times, per-stream row counts, quality counters, and **SHA-256** per
file, so integrity is verifiable before bulk transfer. Daily: copy
yesterday's closed folder. Weekly: verify the week's manifests are
all present and hashed. Broker credentials, account data, and
NinjaTrader configuration never leave the machine.

## 2. Parser command (runs BEFORE any feature work)

```
python3 analysis/mles/mles_integrity.py  <session folder>   # outcome-blind session score
python3 - <<'EOF'                                           # schema/hash/chronology/book/contract/session/gap audit
import sys; sys.path.insert(0,'analysis/mrof'); import mrof_engine as E
rows, integ = E.parse_stream('<file>', '<stream>')
print(integ)
EOF
```

`parse_stream` refuses silent contract mixing, counts sequence gaps,
duplicates and timestamp reversals, and never modifies raw rows; book
reconstruction and ten-level verification run from the depth stream
(`mrofyt_signals.KLevelBook`). A manifest-hash mismatch quarantines
the file (`DATA_SUPPRESSED`) — files are never repaired in place.

## 3. Ingestion ledger

Every batch is recorded: session IDs, exact source path or
`data_root`, manifest hashes, receipt-time hash verification, parser
verdicts, storage location. Research ingestion reads only closed,
hashed manifests and ignores in-progress files.

## 4. Session budget and status

The first ~20 complete sessions are recorder/integrity validation and
descriptive engineering — they are **not** an untouched strategy
holdout. Collection continues while bounded DEV research accumulates;
any passer is frozen before subsequently recorded sessions open for
prospective validation. Until the required streams and minimum
independent sessions exist, the standing research status is
**`INSUFFICIENT_DATA`** — and if no files are accessible, that is the
returned classification, not a workaround.
