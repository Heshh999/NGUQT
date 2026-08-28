# MLES-V1 — REPRODUCTION COMMANDS

Environment: Python 3.11.15, numpy 2.4.6, Mono `mcs`, x86_64 Linux.
Freeze A commit: `c40f39a18a3741836b7849d0e2ab3c758c0e67e5`.

```bash
# 1. repository / protection audit (read-only)
python3 analysis/mles/mles_audit.py

# 2. Mode A test suite (synthetic fixtures only, 37 tests)
python3 analysis/mles/tests_mles.py

# 3. compile-verify the recorder against the NT8 API stub harness
mcs -target:library -out:/tmp/mles_check.dll \
    <scratchpad>/ntstub/NtStubs.cs src/MlesV1CaptureHost.cs

# 4. integrity check a capture folder (after you attach the recorder)
python3 analysis/mles/mles_integrity.py "<path to mles_capture>"
#    exit 0 = PASS, 1 = WARN, 2 = FAIL
```

All four are deterministic and open no protected outcome.
