// ============================================================================
// MockHost.cs — deterministic test host for the two strategy engines.
// Implements IMnqHost with fixed session times (9:30-11:30 ET), $10,000
// balance, MNQ tick size 0.25, and records every order/diagnostic so tests
// can assert on engine behavior without NinjaTrader.
// ============================================================================

using System;
using System.Collections.Generic;
using NinjaTrader.NinjaScript.Strategies.MnqTwo;

namespace MnqTwoTests
{
    public class MockHost : IMnqHost
    {
        public KeyLevelEngine LevelsEngine = new KeyLevelEngine();
        public List<string> Diags = new List<string>();
        public List<string> Entries = new List<string>();   // "SIGNAL qty"
        public List<string> Exits = new List<string>();
        public List<string> Stops = new List<string>();
        public List<TradeRecord> Trades = new List<TradeRecord>();
        public double Balance = 10000;
        public bool AllowOpen = true;

        // ---- V6 U9 handoff wiring (uses the SAME shared coordinator as the NT host) ----
        public FakeBreakoutEngine Fb;
        public VectorBreakRetestEngine Vbr;
        public HandoffCoordinator Handoff;
        /// Ordered record of every execution-affecting action, so tests can assert
        /// that a replacement entry is never submitted before the flatten fill.
        public List<string> Sequence = new List<string>();

        public void WireHandoff()
        {
            Handoff = new HandoffCoordinator(
                delegate(StrategyId id)
                {
                    return id == StrategyId.FAKE_BREAKOUT
                        ? (Fb != null && Fb.HasOpenOrPendingPosition)
                        : (Vbr != null && Vbr.HasOpenOrPendingPosition);
                },
                delegate(StrategyId id)
                {
                    if (id == StrategyId.FAKE_BREAKOUT) { if (Fb != null) Fb.FlattenForHandoff(); }
                    else { if (Vbr != null) Vbr.FlattenForHandoff(); }
                },
                delegate(StrategyId id, TradeDirection dir, int qty, string signal)
                {
                    Entries.Add(signal + " " + qty);
                    Sequence.Add("ENTRY " + signal + " x" + qty);
                },
                delegate(StrategyId id, string msg) { Diag(id, msg); });
        }

        /// Simulate the broker confirming the account is flat after a flatten fill.
        public void ConfirmFlat()
        {
            Sequence.Add("FLAT_CONFIRMED");
            if (Handoff != null) Handoff.NotifyFlat();
        }

        public KeyLevelEngine Levels { get { return LevelsEngine; } }
        public double AccountBalance { get { return Balance; } }
        public double TickSize { get { return 0.25; } }
        public bool InstrumentOk { get { return true; } }

        public bool IsEntryTimeAllowed(DateTime et)
        {
            double m = et.TimeOfDay.TotalMinutes;
            return m >= 570 && m <= 690;
        }
        public bool IsAtOrAfterSessionStart(DateTime et) { return et.TimeOfDay.TotalMinutes >= 570; }
        public bool IsAfterEntryCutoff(DateTime et) { return et.TimeOfDay.TotalMinutes > 690; }
        public bool CanOpenPosition(StrategyId id) { return AllowOpen; }
        public bool TpLevelEnabled(TpLevelId id) { return true; }

        public int EnterPosition(StrategyId id, TradeDirection dir, int qty, string signalName)
        {
            if (Handoff != null)
            {
                Handoff.RequestEntry(id, dir, qty, signalName); // V6 U9 sequencing
                return qty;
            }
            Entries.Add(signalName + " " + qty);
            Sequence.Add("ENTRY " + signalName + " x" + qty);
            return qty;
        }
        public void SubmitOrUpdateStop(StrategyId id, TradeDirection dir, int qty, double stopPrice,
            string stopName, string fromEntrySignal)
        {
            Stops.Add(stopName + " " + qty + " @ " + stopPrice.ToString("0.00"));
        }
        public void ExitMarket(StrategyId id, TradeDirection dir, int qty, string exitName, string fromEntrySignal)
        {
            Exits.Add(exitName + " " + qty);
            Sequence.Add("EXIT " + exitName + " x" + qty);
        }
        public void Diag(StrategyId id, string msg) { Diags.Add("[" + id + "] " + msg); }
        public void LogTrade(TradeRecord rec) { Trades.Add(rec); }
        public double RoundToTick(double price) { return Math.Round(price / 0.25) * 0.25; }

        public bool AnyDiagContains(string s)
        {
            foreach (string d in Diags) if (d.Contains(s)) return true;
            return false;
        }
        public int CountDiagContains(string s)
        {
            int n = 0;
            foreach (string d in Diags) if (d.Contains(s)) n++;
            return n;
        }
    }
}
