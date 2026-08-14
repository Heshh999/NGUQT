# tests/NtStubs.cs

Minimal stand-ins for the NinjaTrader 8 API surface that `src/MnqTwoStrategies.cs`
touches. **This is a syntax and binding check only** — it is not a behavioral model
of NinjaTrader, and a clean compile here is NOT evidence that the strategy behaves
correctly at runtime.

Its single purpose is to let a compiler verify member names, overload shapes and
enum spellings in the NT8 host file, instead of discovering them via F5 in
NinjaTrader. It already caught one real regression (a field initializer referencing
another instance field after the series indices stopped being `const`).

Run it from the repo root:

```
mcs -target:library -out:/tmp/host.dll \
  tests/NtStubs.cs \
  src/MnqTwoStrategiesShared.cs \
  src/FakeBreakoutEngine.cs \
  src/VectorBreakRetestEngine.cs \
  src/MnqTwoStrategies.cs
```

The deterministic behavior suite is separate and does not use these stubs:

```
mcs -out:/tmp/run_tests.exe \
  src/MnqTwoStrategiesShared.cs \
  src/FakeBreakoutEngine.cs \
  src/VectorBreakRetestEngine.cs \
  tests/MockHost.cs tests/Tests.cs && mono /tmp/run_tests.exe
```
