// NT8 API STUBS v12 — SYNTAX-CHECK HARNESS ONLY.
//
// CORRECTED against REAL F5 compiler evidence (2026-09-01). The prior
// revision placed BOTH `Operation` and `ConnectionStatusEventArgs` in
// NinjaTrader.Data; a genuine NT8 F5 compile rejected both:
//   CS0103 'Operation' does not exist in the current context
//   CS0246 type or namespace 'ConnectionStatusEventArgs' not found
// while `e.Operation` and `NinjaTrader.Cbi.ConnectionStatus` resolved
// cleanly. Lesson recorded: a stub written to match our own code proves
// NOTHING. These stubs now deliberately place the depth-operation enum
// OUTSIDE every namespace the host imports, so that any future attempt
// to name that type bare fails here too instead of being masked.
//
// VERIFIED by F5: e.Operation is a valid property; ConnectionStatus and
// its Connected member live in NinjaTrader.Cbi; the type is NOT in
// NinjaTrader.Data, NinjaTrader.NinjaScript or the NinjaTrader root.
// INFERRED (not yet F5-confirmed): ConnectionStatusEventArgs is in
// NinjaTrader.Cbi.
// This is NOT NinjaTrader and does not replace the user-side F5 compile.
using System;

namespace NinjaTrader.Cbi
{
    public enum ConnectionStatus
    {
        Connected, Connecting, ConnectionLost, Disconnected, Disconnecting
    }

    // Deliberately NOT in NinjaTrader.Data: the host must never name
    // this type, only call .ToString() on the property.
    public enum Operation { Add, Update, Remove }

    public class ConnectionStatusEventArgs
    {
        public ConnectionStatus Status;
        public ConnectionStatus PriceStatus;
    }
    public class MasterInstrument { public string Name; }
    public class Instrument
    {
        public string FullName;
        public MasterInstrument MasterInstrument;
    }
}

namespace NinjaTrader.Data
{
    public enum MarketDataType { Bid, Ask, Last }

    public class MarketDataEventArgs
    {
        public MarketDataType MarketDataType;
        public double Price;
        public long Volume;
        public DateTime Time;
    }

    public class MarketDepthEventArgs
    {
        public MarketDataType MarketDataType;
        public NinjaTrader.Cbi.Operation Operation;
        public int Position;
        public double Price;
        public long Volume;
        public DateTime Time;
    }
}

namespace NinjaTrader.NinjaScript
{
    public enum State { SetDefaults, Configure, DataLoaded, Realtime, Terminated }
    public enum Calculate { OnEachTick, OnBarClose, OnPriceChange }

    [AttributeUsage(AttributeTargets.Property)]
    public class NinjaScriptPropertyAttribute : Attribute { }

    public class NinjaScriptBase
    {
        public string Name;
        public string Description;
        public Calculate Calculate;
        public State State;
        public NinjaTrader.Cbi.Instrument Instrument;
        protected virtual void OnStateChange() { }
        protected virtual void OnMarketData(
            NinjaTrader.Data.MarketDataEventArgs e) { }
        protected virtual void OnMarketDepth(
            NinjaTrader.Data.MarketDepthEventArgs e) { }
        protected virtual void OnConnectionStatusUpdate(
            NinjaTrader.Cbi.ConnectionStatusEventArgs e) { }
    }
}

namespace NinjaTrader.NinjaScript.Indicators
{
    public class Indicator : NinjaTrader.NinjaScript.NinjaScriptBase
    {
        public bool IsOverlay;
    }
}
