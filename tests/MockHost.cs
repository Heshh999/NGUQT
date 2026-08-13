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
            Entries.Add(signalName + " " + qty);
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
