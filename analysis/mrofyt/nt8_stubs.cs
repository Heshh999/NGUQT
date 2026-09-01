// NT8 API STUBS — SYNTAX-CHECK HARNESS ONLY.
// This is NOT NinjaTrader and is NOT a substitute for the F5 compile
// inside NinjaTrader 8. It exists so `mcs` can verify that the recorder
// source is syntactically valid and type-consistent against the exact
// API surface it uses.
using System;

namespace NinjaTrader.Data
{
    public enum MarketDataType { Bid, Ask, Last }
    public enum Operation { Insert, Update, Remove }
    public enum ConnectionStatus { Connected, Disconnected }

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
        public ConnectionStatus Status;
    }
}

namespace NinjaTrader.Cbi
{
    public class MasterInstrument { public string Name; }
    public class Instrument
    {
        public string FullName;
        public MasterInstrument MasterInstrument;
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
