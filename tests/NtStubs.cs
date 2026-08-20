// Minimal NinjaTrader 8 API stubs - SYNTAX/BINDING CHECK ONLY.
// Not a behavioral model of NT8; it exists so the host file's member usage,
// overloads and enum names can be verified by a compiler instead of by eye.
using System;
using System.Collections.Generic;

namespace NinjaTrader.Cbi
{
    public enum MarketPosition { Flat, Long, Short }
    public enum OrderState { Initialized, Submitted, Accepted, Working, Filled, Cancelled, Rejected, PartFilled }
    public enum OrderAction { Buy, Sell, SellShort, BuyToCover }
    public enum ErrorCode { NoError }
    public class Order { public string Name { get; set; } public OrderState OrderState { get; set; } }
    public class Execution { public Order Order { get; set; } }
    public class Position { public MarketPosition MarketPosition { get; set; } public double AveragePrice { get; set; } public int Quantity { get; set; } }
    public class Account { public string Name { get; set; } public double Get(AccountItem i, Currency c) { return 0; } }
    public enum AccountItem { CashValue, NetLiquidation, BuyingPower }
    public enum Currency { UsDollar }
    public class Instrument { public MasterInstrument MasterInstrument { get; set; } public string FullName { get; set; } }
    public class MasterInstrument { public string Name { get; set; } public double TickSize { get; set; } public double PointValue { get; set; } public double RoundToTickSize(double p) { return p; } }
}

namespace NinjaTrader.Data
{
    public enum MarketDataType { Last, Bid, Ask }
    public enum BarsPeriodType { Tick, Volume, Range, Second, Minute, Day, Week, Month, Year }
    public class Bars
    {
        public int Count { get; set; }
        public NinjaTrader.Cbi.Instrument Instrument { get; set; }
        /// Real NT8 API: timestamp of a bar by absolute index. Used by the data-coverage
        /// report to state the true first/last bar of each series.
        public System.DateTime GetTime(int barIndex) { return System.DateTime.MinValue; }
    }
}

namespace NinjaTrader.Core
{
    public static class Globals { public static string UserDataDir = "."; }
}

namespace NinjaTrader.NinjaScript
{
    public enum State { SetDefaults, Configure, Active, DataLoaded, Historical, Transition, Realtime, Terminated, Finalized }
    // V4.1 sets this to Infinite: the engines index back through their own
    // history and a truncated series would silently shorten it.
    public enum MaximumBarsLookBack { TwoHundredFiftySix, Infinite }
    public enum Calculate { OnBarClose, OnPriceChange, OnEachTick }
    public enum EntryHandling { AllEntries, UniqueEntries }
    public enum StartBehavior { WaitUntilFlat, WaitUntilFlatSynchronizeAccount, ImmediatelySubmit, ImmediatelySubmitSynchronizeAccount, AdoptAccountPosition }
    public enum StopTargetHandling { PerEntryExecution, ByStrategyPosition }
    public enum TimeInForce { Day, Gtc }
    public enum RealtimeErrorHandling { StopCancelClose, IgnoreAllErrors, TakeNoAction }
    public enum ConnectionLossHandling { Recalculate, KeepRunning, StopStrategy }
    public enum OrderFillResolution { Standard, High }

    public class Series<T>
    {
        private T[] a = new T[4096];
        public T this[int i] { get { return a[0]; } set { a[0] = value; } }
        public int Count { get { return 0; } }
    }

    public abstract class NinjaScriptBase
    {
        public State State;
        public string Name { get; set; }
        public string Description { get; set; }
        public Calculate Calculate { get; set; }
        public bool IsOverlay { get; set; }
        public int BarsRequiredToTrade { get; set; }
        public int BarsRequiredToPlot { get; set; }
        public MaximumBarsLookBack MaximumBarsLookBack { get; set; }
        public bool IsInstantiatedOnEachOptimizationIteration { get; set; }
        public NinjaTrader.Cbi.Instrument Instrument { get; set; }
        public Series<double> Open, High, Low, Close, Volume;
        public Series<DateTime> Time;
        public NinjaTrader.Data.Bars[] BarsArray = new NinjaTrader.Data.Bars[16];
        public int[] CurrentBars = new int[16];
        public int CurrentBar;
        public int BarsInProgress;
        public Series<double>[] Opens = new Series<double>[16];
        public Series<double>[] Highs = new Series<double>[16];
        public Series<double>[] Lows = new Series<double>[16];
        public Series<double>[] Closes = new Series<double>[16];
        public Series<double>[] Volumes = new Series<double>[16];
        public Series<DateTime>[] Times = new Series<DateTime>[16];
        public double TickSize { get { return 0.25; } }
        public void Print(object o) { }
        public void AddDataSeries(NinjaTrader.Data.BarsPeriodType t, int p) { }
        public void AddDataSeries(string instrument, NinjaTrader.Data.BarsPeriodType t, int p) { }
        public void AddDataSeries(string instrument, NinjaTrader.Data.BarsPeriodType t, int p, NinjaTrader.Data.MarketDataType m) { }
        protected virtual void OnStateChange() { }
        protected virtual void OnBarUpdate() { }
    }
}

namespace NinjaTrader.NinjaScript.Indicators
{
    public class EMA : NinjaScriptBase { public double this[int i] { get { return 0; } } }
    public class Indicator : NinjaScriptBase { }
}

namespace NinjaTrader.NinjaScript.Strategies
{
    using NinjaTrader.Cbi;
    public class TradeCollectionStub { public int Count { get { return 0; } } }
    public class TradesPerfStub { public TradeCollectionStub TradesPerformance = new TradeCollectionStub(); public TradeCollectionStub Count = new TradeCollectionStub(); }
    public class SystemPerformanceStub { public AllTradesStub AllTrades = new AllTradesStub(); }
    public class AllTradesStub { public int Count { get { return 0; } } public TradesPerformanceStub TradesPerformance = new TradesPerformanceStub(); }
    public class TradesPerformanceStub { public CurrencyStub Currency = new CurrencyStub(); public double NetProfit { get { return 0; } } }
    public class CurrencyStub { public double CumProfit { get { return 0; } } }
    public abstract class Strategy : NinjaScriptBase
    {
        public EntryHandling EntryHandling { get; set; }
        public int EntriesPerDirection { get; set; }
        public bool IsExitOnSessionCloseStrategy { get; set; }
        public int ExitOnSessionCloseSeconds { get; set; }
        public StartBehavior StartBehavior { get; set; }
        public StopTargetHandling StopTargetHandling { get; set; }
        public TimeInForce TimeInForce { get; set; }
        public RealtimeErrorHandling RealtimeErrorHandling { get; set; }
        public ConnectionLossHandling ConnectionLossHandling { get; set; }
        public OrderFillResolution OrderFillResolution { get; set; }
        public bool TraceOrders { get; set; }
        public int DefaultQuantity { get; set; }
        public Account Account { get; set; }
        public Position Position { get; set; }
        public SystemPerformanceStub SystemPerformance = new SystemPerformanceStub();

        public Indicators.EMA EMA(NinjaTrader.Data.Bars b, int p) { return new Indicators.EMA(); }
        public Indicators.EMA EMA(int p) { return new Indicators.EMA(); }

        public Order EnterLong(int bip, int qty, string sig) { return null; }
        public Order EnterShort(int bip, int qty, string sig) { return null; }
        public Order ExitLong(int bip, int qty, string sig, string from) { return null; }
        public Order ExitShort(int bip, int qty, string sig, string from) { return null; }
        public Order ExitLongStopMarket(int bip, bool liveUntilCancelled, int qty, double stop, string sig, string from) { return null; }
        public Order ExitShortStopMarket(int bip, bool liveUntilCancelled, int qty, double stop, string sig, string from) { return null; }

        protected virtual void OnExecutionUpdate(Execution e, string id, double price, int qty, MarketPosition mp, string oid, DateTime t) { }
        protected virtual void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled, double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error, string comment) { }
        protected virtual void OnPositionUpdate(Position p, double ap, int q, MarketPosition mp) { }
    }
}

namespace System.ComponentModel.DataAnnotations
{
    [AttributeUsage(AttributeTargets.All, AllowMultiple = true)]
    public class DisplayAttribute : Attribute
    {
        public string Name { get; set; }
        public string GroupName { get; set; }
        public string Description { get; set; }
        public int Order { get; set; }
    }
    [AttributeUsage(AttributeTargets.All, AllowMultiple = true)]
    public class RangeAttribute : Attribute
    {
        public RangeAttribute(double min, double max) { }
        public RangeAttribute(int min, int max) { }
        public RangeAttribute(Type t, string min, string max) { }
    }
}

namespace NinjaTrader.NinjaScript
{
    [AttributeUsage(AttributeTargets.All, AllowMultiple = true)]
    public class NinjaScriptPropertyAttribute : Attribute { }
}
