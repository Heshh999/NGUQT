# DATA_HANDOFF_V12.md — capture → research handoff (MLES-CAPTURE-1.2)

Supersedes the v01.3 handoff for schema. Raw files are immutable;
nothing is uploaded silently; broker credentials never leave the
machine.

## 1. What moves

Per run: send `..._manifest.json` FIRST (tiny; carries
captureInstanceId, runId, session, exact contract, connection
segments, first/last global and per-stream sequences, SHA-256 + bytes
+ rows per file, depth side/action counts, overflow/drop/write-error
counters and the flush policy). Bulk CSVs follow on request. Never
edit, re-save or "clean" a file — the manifest hash must match the
recorder's bytes exactly. `.csv.partial` files are never sent: a
partial next to no manifest means the run did not close cleanly; send
the `_RECOVERY.json` artifact instead if one exists.

## 2. Intake (manifest-authoritative)

```
python3 analysis/mrofyt/mles_v12_audit.py   # via audit_capture(<dir>)
```

`audit_capture` verifies every hash/byte/row count, identity on every
row, sequence monotonicity, per-run counter resets, segment ranges,
both depth sides and all three actions, declared depth, book-resync
intervals, orphan partials, orphan CSVs, collision manifests,
duplicate run IDs and contract-roll collisions — and pairs NQ with
MNQ by session, failing on session mismatch or <50% window overlap.
A failed audit quarantines the batch (`DATA_SUPPRESSED`); files are
never repaired in place.

## 3. Ledger and budget

Every batch: session IDs, source path, manifest hashes, verification
verdicts, storage location. First ~20 complete sessions = recorder/
integrity validation and engineering only — never a strategy holdout.
Status remains `INSUFFICIENT_DATA — ZERO GENUINE RECORDED SESSIONS`
until the required streams and minimum independent sessions exist.
