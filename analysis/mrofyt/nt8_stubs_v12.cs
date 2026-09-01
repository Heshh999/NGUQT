// NT8 API STUBS v12 — SYNTAX-CHECK HARNESS ONLY. Mirrors the REAL NT8
// surface the v1.2 host uses: NinjaTrader.Data.Operation members are
// Add/Update/Remove (NOT Insert), and ConnectionStatusEventArgs carries
// BOTH Status and PriceStatus as NinjaTrader.Cbi.ConnectionStatus.
// This is NOT NinjaTrader and does not replace the user-side F5 compile.
using System;

namespace NinjaTrader.Cbi
{
    public enum ConnectionStatus
    {
        Connected, Connecting, ConnectionLost, Disconnected, Disconnecting
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
    public enum Operation { Add, Update, Remove }

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
        public Operation Operation;
        public int Position;
        public double Price;
        public long Volume;
        public DateTime Time;
    }

    public class ConnectionStatusEventArgs
    {
        public NinjaTrader.Cbi.ConnectionStatus Status;
        public NinjaTrader.Cbi.ConnectionStatus PriceStatus;
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
            NinjaTrader.Data.ConnectionStatusEventArgs e) { }
    }
}

namespace NinjaTrader.NinjaScript.Indicators
{
    public class Indicator : NinjaTrader.NinjaScript.NinjaScriptBase
    {
        public bool IsOverlay;
    }
}
