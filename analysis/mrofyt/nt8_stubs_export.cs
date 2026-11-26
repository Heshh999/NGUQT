// NT8 API STUBS for MrofBarExport.cs - SYNTAX AND LOGIC HARNESS ONLY.
//
// This is NOT NinjaTrader. It was written from NinjaTrader's public help
// pages (BarsRequest, RolloverCollection, GetInstrument, the
// application time zone), not from a compile against the platform, so
// it proves nothing about the real API: a stub written to match our own
// code never does (see nt8_stubs_v12.cs). What it does prove is the
// script's own logic - which contracts it asks for, how it turns bar
// times into UTC, what it writes, how it goes on after an error or a
// feed that never answers. The real F5 compile and the first real run
// are the operator's.
//
// Built with -define:ONE_ARG_ONLY, Instrument has no (name, create)
// form, as the help page documents it. NO_MERGE_POLICY and
// NO_LOOKUP_POLICY hide those two members of BarsRequest. MergePolicy
// is a property and LookupPolicy a field here, because the script must
// cope with either.
using System;
using System.Collections.Generic;
using System.Threading;

namespace NinjaTrader.Core
{
    public class GeneralOptions
    {
        public TimeZoneInfo TimeZoneInfo;
    }

    public static class Globals
    {
        public static GeneralOptions GeneralOptions = new GeneralOptions();
    }
}

namespace NinjaTrader.Cbi
{
    public enum ErrorCode { NoError, Panic, UnableToLoadData }

    public enum MergePolicy
    {
        DoNotMerge, MergeBackAdjusted, MergeNonBackAdjusted,
        UseGlobalSettings
    }

    public class Rollover
    {
        public DateTime ContractMonth;
        public DateTime Date;
        public double Offset;
    }

    public class RolloverCollection :
        System.Collections.ObjectModel.Collection<Rollover> { }

    public class MasterInstrument
    {
        public string Name;
        public RolloverCollection RolloverCollection =
            new RolloverCollection();
    }

    public class Instrument
    {
        public string FullName;
        public MasterInstrument MasterInstrument;

        // the harness's database: contracts that exist, and the
        // markets a contract can be created in
        public static readonly Dictionary<string, Instrument> Known =
            new Dictionary<string, Instrument>();
        public static readonly Dictionary<string, MasterInstrument> Masters =
            new Dictionary<string, MasterInstrument>();
        public static int Created;

        public static Instrument GetInstrument(string instrumentName)
        {
            Instrument ins;
            return Known.TryGetValue(instrumentName, out ins) ? ins : null;
        }

#if !ONE_ARG_ONLY
        public static Instrument GetInstrument(string instrumentName,
                                               bool create)
        {
            Instrument ins = GetInstrument(instrumentName);
            if (ins != null || !create) return ins;
            string[] parts = instrumentName.Split(' ');
            MasterInstrument m;
            if (parts.Length != 2 || !Masters.TryGetValue(parts[0], out m))
                return null;
            ins = new Instrument { FullName = instrumentName,
                                   MasterInstrument = m };
            Known[instrumentName] = ins;
            Created++;
            return ins;
        }
#endif
    }
}

namespace NinjaTrader.Data
{
    public enum BarsPeriodType { Tick, Minute, Day }

    public class BarsPeriod
    {
        public BarsPeriodType BarsPeriodType;
        public int Value;
    }

    public class TradingHours
    {
        public string Name;

        public static TradingHours Get(string name)
        {
            return new TradingHours { Name = name };
        }
    }

    public enum LookupPolicies { Provider, Repository }

    public class Bars
    {
        public readonly List<DateTime> T = new List<DateTime>();
        public readonly List<double[]> Ohlc = new List<double[]>();
        public readonly List<long> V = new List<long>();

        public int Count { get { return T.Count; } }
        public DateTime GetTime(int index) { return T[index]; }
        public double GetOpen(int index) { return Ohlc[index][0]; }
        public double GetHigh(int index) { return Ohlc[index][1]; }
        public double GetLow(int index) { return Ohlc[index][2]; }
        public double GetClose(int index) { return Ohlc[index][3]; }
        public long GetVolume(int index) { return V[index]; }
    }

    // One fake bar of the harness's feed, in the application's time.
    public class FeedBar
    {
        public DateTime Time;
        public double[] Ohlc;
        public long Volume;
    }

    public class BarsRequest : IDisposable
    {
        // the harness's feed
        public static readonly Dictionary<string, List<FeedBar>> Feed =
            new Dictionary<string, List<FeedBar>>();
        public static readonly Dictionary<string, string> Behavior =
            new Dictionary<string, string>();     // error|silent|async|late
        public static readonly List<string> Log = new List<string>();
        public static int Disposed;

        private readonly NinjaTrader.Cbi.Instrument instrument;
        private readonly DateTime from, to;

        public BarsPeriod BarsPeriod;
        public TradingHours TradingHours;
#if NO_MERGE_POLICY
        private NinjaTrader.Cbi.MergePolicy MergePolicy =
            NinjaTrader.Cbi.MergePolicy.UseGlobalSettings;
#else
        public NinjaTrader.Cbi.MergePolicy MergePolicy { get; set; }
#endif
#if NO_LOOKUP_POLICY
        private LookupPolicies LookupPolicy = LookupPolicies.Provider;
#else
        public LookupPolicies LookupPolicy = LookupPolicies.Repository;
#endif
        public Bars Bars = new Bars();

        public BarsRequest(NinjaTrader.Cbi.Instrument instrument,
                           int barsBack)
        {
            throw new NotSupportedException("the harness has no barsBack");
        }

        public BarsRequest(NinjaTrader.Cbi.Instrument instrument,
                           DateTime fromLocal, DateTime toLocal)
        {
#if !NO_MERGE_POLICY
            MergePolicy = NinjaTrader.Cbi.MergePolicy.UseGlobalSettings;
#endif
            this.instrument = instrument;
            from = fromLocal.Date;
            to = toLocal.Date.AddDays(1);
        }

        public void Request(
            Action<BarsRequest, NinjaTrader.Cbi.ErrorCode, string> callback)
        {
            string name = instrument.FullName;
            lock (Log)
            {
                Log.Add("request name=" + name.Replace(' ', '_') +
                    " from=" + from.ToString("yyyyMMdd") +
                    " to=" + to.AddDays(-1).ToString("yyyyMMdd") +
                    " merge=" + MergePolicy +
                    " lookup=" + LookupPolicy +
                    " hours=" + (TradingHours == null ? "none"
                        : TradingHours.Name.Replace(' ', '_')) +
                    " period=" + (BarsPeriod == null ? "none"
                        : BarsPeriod.BarsPeriodType + "/" +
                          BarsPeriod.Value));
            }
            string how;
            Behavior.TryGetValue(name, out how);
            if (how == "silent") return;
            if (how == "error")
            {
                callback(this, NinjaTrader.Cbi.ErrorCode.UnableToLoadData,
                         "the harness refuses this contract");
                return;
            }
            // a repository-only lookup finds nothing: the harness's
            // bars are all at the provider
            if (LookupPolicy == LookupPolicies.Provider)
            {
                List<string> take = new List<string>();
                take.Add(name);
                // a merging request also pulls every earlier contract
                if (MergePolicy != NinjaTrader.Cbi.MergePolicy.DoNotMerge)
                    foreach (string other in Feed.Keys)
                        if (other != name) take.Add(other);
                foreach (string key in take)
                {
                    List<FeedBar> all;
                    if (!Feed.TryGetValue(key, out all)) continue;
                    foreach (FeedBar b in all)
                        if (b.Time >= from && b.Time < to)
                        {
                            Bars.T.Add(b.Time);
                            Bars.Ohlc.Add(b.Ohlc);
                            Bars.V.Add(b.Volume);
                        }
                }
            }
            if (how == "async" || how == "late")
            {
                int wait = how == "late" ? 3000 : 50;
                Thread th = new Thread(delegate()
                {
                    Thread.Sleep(wait);
                    callback(this, NinjaTrader.Cbi.ErrorCode.NoError, "");
                });
                th.IsBackground = true;
                th.Start();
                return;
            }
            callback(this, NinjaTrader.Cbi.ErrorCode.NoError, "");
        }

        public void Dispose()
        {
            Interlocked.Increment(ref Disposed);
        }
    }
}

namespace NinjaTrader.NinjaScript
{
    public enum State
    {
        SetDefaults, Configure, Active, DataLoaded, Historical, Transition,
        Realtime, Terminated
    }

    public enum Calculate { OnBarClose, OnEachTick, OnPriceChange }

    [AttributeUsage(AttributeTargets.Property)]
    public class NinjaScriptPropertyAttribute : Attribute { }

    public class NinjaScriptBase
    {
        public static readonly List<string> Printed = new List<string>();

        public string Name { get; set; }
        public string Description { get; set; }
        public Calculate Calculate { get; set; }
        public State State { get; set; }
        public NinjaTrader.Cbi.Instrument Instrument { get; set; }
        // the script names the TYPES BarsPeriod and TradingHours inside
        // a class that also has members of those names, as here
        public NinjaTrader.Data.BarsPeriod BarsPeriod { get; set; }
        public NinjaTrader.Data.TradingHours TradingHours { get; set; }

        protected virtual void OnStateChange() { }
        protected virtual void OnBarUpdate() { }

        protected void Print(object message)
        {
            lock (Printed) Printed.Add(Convert.ToString(message));
        }

        public void SetState(State state)        // the harness's hook
        {
            State = state;
            OnStateChange();
        }
    }
}

namespace NinjaTrader.NinjaScript.Indicators
{
    public class Indicator : NinjaTrader.NinjaScript.NinjaScriptBase
    {
        public bool IsOverlay { get; set; }
    }
}
