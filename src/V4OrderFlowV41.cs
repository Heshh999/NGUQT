// ======================================================================
// V4OrderFlowV41.cs  -  MNQ V4.1
// ======================================================================
// The V4.1 extensions to executed order flow: the imbalance parameter
// FAMILY, absorption raw ingredients, cumulative-delta divergence, and
// the MODE 1 / MODE 2 output split.
//
// THIS FILE SUBMITS NO ORDERS.
//
// Three commitments shape this module.
//
// One: no magical ratio. Imbalance is computed across a small PREDECLARED
// family of ratios and every one is emitted. Picking a single ratio in
// engine code would be choosing an answer before the question was asked.
//
// Two: absorption is never a visual label. It is built from raw
// ingredients - aggressive executed volume, price progress in ticks, and
// location at a known extreme - and every ingredient is emitted alongside
// the candidate flag so the research layer can rebuild or reject the
// definition without rerunning the capture.
//
// Three: this whole layer exists only where the Volumetric series exists,
// which is a far shorter history than structure. Every row is stamped
// STRUCTURE_ORDERFLOW so a ten-month result can never be mistaken for a
// seven-year one. V4 already measured what order flow contributes at
// structure breaks - nothing, max |t| 0.91 across four tests - so the
// prior going in should be low, and this module is built to measure that
// honestly rather than to rescue it.
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    /// The declared imbalance family. Three ratios, all reported.
    public static class V4ImbalanceFamily
    {
        public static readonly double[] Ratios = new double[] { 2.0, 3.0, 4.0 };
        public const double MinVolume = 10.0;
        /// Consecutive imbalanced levels that count as "stacked".
        public const int StackedMin = 3;
    }

    /// Everything V4.1 computes from one footprint bar beyond what
    /// V4OrderFlowEngine already produces.
    public class V4OrderFlowFeatures
    {
        // ---- bar-level ------------------------------------------------
        public double TotalVolume, BidVolume, AskVolume, BarDelta, DeltaPct;
        public double CumDelta, CumDeltaChange, CumDeltaSlope;
        public double MinDelta, MaxDelta;
        public double RelVolume, RelDelta;

        // ---- imbalance family -----------------------------------------
        public readonly int[] BuyImbalanceCount = new int[V4ImbalanceFamily.Ratios.Length];
        public readonly int[] SellImbalanceCount = new int[V4ImbalanceFamily.Ratios.Length];
        public readonly int[] StackedBuyLevels = new int[V4ImbalanceFamily.Ratios.Length];
        public readonly int[] StackedSellLevels = new int[V4ImbalanceFamily.Ratios.Length];
        public double MaxBuyImbalanceRatio, MaxSellImbalanceRatio;
        public bool BuyImbalanceNearHigh, SellImbalanceNearLow;

        // ---- absorption raw ingredients --------------------------------
        public double AggressiveBuyVolume, AggressiveSellVolume;
        public int PriceProgressUpTicks, PriceProgressDownTicks;
        public double VolumePerUpTick, VolumePerDownTick;
        public int RepeatedTradeAtExtreme;
        public bool AbsorptionBuyCandidate, AbsorptionSellCandidate;
        public double AbsorptionStrengthRaw;

        // ---- divergence -------------------------------------------------
        public bool PriceNewHigh, PriceNewLow;
        public bool CumDeltaNewHigh, CumDeltaNewLow;
        public bool BullishDeltaDivergenceCandidate, BearishDeltaDivergenceCandidate;
        public bool DeltaConfirmsBreak, DeltaFailsBreak;

        // ---- POC --------------------------------------------------------
        public double PocPrice = double.NaN, PocVolume;
        public double CloseMinusPocPts = double.NaN;

        /// Compute everything from one bar's per-price cells.
        ///
        /// aggressiveBuy is volume traded at the offer, aggressiveSell at
        /// the bid. Progress is measured in ticks so volume-per-tick is a
        /// meaningful "how much did it cost to move one tick" number - that
        /// ratio is the whole basis of the absorption candidate, and it is
        /// emitted raw so the threshold can be changed without recapturing.
        public void Compute(V4FootprintBar b, double tickSize,
                            double prevClose, double relVolume,
                            double absorptionVolPerTickMult,
                            bool atKnownExtreme)
        {
            TotalVolume = b.Volume;
            AskVolume = b.AskTotal;
            BidVolume = b.BidTotal;
            BarDelta = AskVolume - BidVolume;
            DeltaPct = V4Num.Pct(BarDelta, TotalVolume);
            RelVolume = relVolume;

            AggressiveBuyVolume = AskVolume;
            AggressiveSellVolume = BidVolume;

            double range = b.High - b.Low;
            int rangeTicks = (V4Num.Ok(range) && tickSize > 0) ? (int)Math.Round(range / tickSize) : 0;

            double up = b.Close - prevClose;
            PriceProgressUpTicks = (V4Num.Ok(up) && up > 0 && tickSize > 0) ? (int)Math.Round(up / tickSize) : 0;
            PriceProgressDownTicks = (V4Num.Ok(up) && up < 0 && tickSize > 0) ? (int)Math.Round(-up / tickSize) : 0;

            VolumePerUpTick = PriceProgressUpTicks > 0
                ? AggressiveBuyVolume / PriceProgressUpTicks
                : (AggressiveBuyVolume > 0 ? AggressiveBuyVolume : double.NaN);
            VolumePerDownTick = PriceProgressDownTicks > 0
                ? AggressiveSellVolume / PriceProgressDownTicks
                : (AggressiveSellVolume > 0 ? AggressiveSellVolume : double.NaN);

            ComputeImbalances(b, tickSize);
            ComputePoc(b);

            // Absorption: heavy aggression, little progress, at a known
            // extreme. All three, or it is not a candidate.
            double meanVolPerTick = rangeTicks > 0 ? TotalVolume / rangeTicks : double.NaN;
            if (V4Num.Ok(meanVolPerTick) && meanVolPerTick > 0)
            {
                bool heavyBuy = AggressiveBuyVolume > AggressiveSellVolume;
                bool noUp = PriceProgressUpTicks <= 0;
                bool noDown = PriceProgressDownTicks <= 0;

                AbsorptionBuyCandidate = heavyBuy && noUp && atKnownExtreme
                    && V4Num.Ok(VolumePerUpTick)
                    && VolumePerUpTick >= absorptionVolPerTickMult * meanVolPerTick;

                AbsorptionSellCandidate = !heavyBuy && noDown && atKnownExtreme
                    && V4Num.Ok(VolumePerDownTick)
                    && VolumePerDownTick >= absorptionVolPerTickMult * meanVolPerTick;

                double dom = Math.Max(AggressiveBuyVolume, AggressiveSellVolume);
                AbsorptionStrengthRaw = V4Num.SafeDiv(dom, meanVolPerTick, 1e-9);
            }
            else AbsorptionStrengthRaw = double.NaN;

            RepeatedTradeAtExtreme = CountAtExtreme(b, tickSize);
        }

        private void ComputeImbalances(V4FootprintBar b, double tickSize)
        {
            if (b.Levels == null || b.Levels.Count == 0) return;
            List<V4FootprintLevel> lv = b.Levels;

            for (int ri = 0; ri < V4ImbalanceFamily.Ratios.Length; ri++)
            {
                double ratio = V4ImbalanceFamily.Ratios[ri];
                int runBuy = 0, runSell = 0, bestBuy = 0, bestSell = 0;

                for (int i = 0; i < lv.Count; i++)
                {
                    double a = lv[i].AskVolume, bd = lv[i].BidVolume;
                    if (a + bd < V4ImbalanceFamily.MinVolume) { runBuy = runSell = 0; continue; }

                    bool buyImb = bd > 0 && a >= ratio * bd;
                    bool sellImb = a > 0 && bd >= ratio * a;

                    if (buyImb) { BuyImbalanceCount[ri]++; runBuy++; if (runBuy > bestBuy) bestBuy = runBuy; }
                    else runBuy = 0;
                    if (sellImb) { SellImbalanceCount[ri]++; runSell++; if (runSell > bestSell) bestSell = runSell; }
                    else runSell = 0;

                    if (ri == 0)
                    {
                        double br = bd > 0 ? a / bd : double.NaN;
                        double sr = a > 0 ? bd / a : double.NaN;
                        if (V4Num.Ok(br) && br > MaxBuyImbalanceRatio) MaxBuyImbalanceRatio = br;
                        if (V4Num.Ok(sr) && sr > MaxSellImbalanceRatio) MaxSellImbalanceRatio = sr;
                    }
                }
                StackedBuyLevels[ri] = bestBuy >= V4ImbalanceFamily.StackedMin ? bestBuy : 0;
                StackedSellLevels[ri] = bestSell >= V4ImbalanceFamily.StackedMin ? bestSell : 0;
            }

            // where in the bar did the imbalance sit?
            double band = 2 * tickSize;
            for (int i = 0; i < lv.Count; i++)
            {
                double a = lv[i].AskVolume, bd = lv[i].BidVolume;
                if (a + bd < V4ImbalanceFamily.MinVolume) continue;
                if (bd > 0 && a >= 3.0 * bd && lv[i].Price >= b.High - band) BuyImbalanceNearHigh = true;
                if (a > 0 && bd >= 3.0 * a && lv[i].Price <= b.Low + band) SellImbalanceNearLow = true;
            }
        }

        private void ComputePoc(V4FootprintBar b)
        {
            if (b.Levels == null || b.Levels.Count == 0) return;
            double best = -1;
            for (int i = 0; i < b.Levels.Count; i++)
            {
                double v = b.Levels[i].AskVolume + b.Levels[i].BidVolume;
                if (v > best) { best = v; PocPrice = b.Levels[i].Price; PocVolume = v; }
            }
            if (V4Num.Ok(PocPrice)) CloseMinusPocPts = b.Close - PocPrice;
        }

        /// How many price levels traded within two ticks of the bar's own
        /// extreme. High counts with no progress is the raw shape of
        /// absorption, without asserting that is what it means.
        private static int CountAtExtreme(V4FootprintBar b, double tickSize)
        {
            if (b.Levels == null) return 0;
            double band = 2 * tickSize;
            int n = 0;
            for (int i = 0; i < b.Levels.Count; i++)
            {
                double p = b.Levels[i].Price;
                if (p >= b.High - band || p <= b.Low + band) n++;
            }
            return n;
        }

        // ---- CSV --------------------------------------------------------

        public void Write(V4Row r)
        {
            r.F("ofTotalVolume", TotalVolume)
             .F("ofBidVolume", BidVolume)
             .F("ofAskVolume", AskVolume)
             .F("ofBarDelta", BarDelta)
             .F("ofDeltaPct", DeltaPct)
             .F("ofCumDelta", CumDelta)
             .F("ofCumDeltaChange", CumDeltaChange)
             .F("ofCumDeltaSlope", CumDeltaSlope)
             .F("ofMinDelta", MinDelta)
             .F("ofMaxDelta", MaxDelta)
             .F("ofRelVolume", RelVolume);

            for (int i = 0; i < V4ImbalanceFamily.Ratios.Length; i++)
            {
                string t = V4ImbalanceFamily.Ratios[i].ToString("0.#", CultureInfo.InvariantCulture) + "x";
                r.F("buyImbalanceCount_" + t, BuyImbalanceCount[i])
                 .F("sellImbalanceCount_" + t, SellImbalanceCount[i])
                 .F("stackedBuyLevels_" + t, StackedBuyLevels[i])
                 .F("stackedSellLevels_" + t, StackedSellLevels[i]);
            }
            r.F("maxBuyImbalanceRatio", MaxBuyImbalanceRatio)
             .F("maxSellImbalanceRatio", MaxSellImbalanceRatio)
             .F("buyImbalanceNearHigh", BuyImbalanceNearHigh)
             .F("sellImbalanceNearLow", SellImbalanceNearLow);

            r.F("aggressiveBuyVolume", AggressiveBuyVolume)
             .F("aggressiveSellVolume", AggressiveSellVolume)
             .F("priceProgressUpTicks", PriceProgressUpTicks)
             .F("priceProgressDownTicks", PriceProgressDownTicks)
             .F("volumePerUpTick", VolumePerUpTick)
             .F("volumePerDownTick", VolumePerDownTick)
             .F("repeatedTradeAtExtreme", RepeatedTradeAtExtreme)
             .F("absorptionBuyCandidate", AbsorptionBuyCandidate)
             .F("absorptionSellCandidate", AbsorptionSellCandidate)
             .F("absorptionStrengthRaw", AbsorptionStrengthRaw);

            r.F("priceNewHigh", PriceNewHigh).F("priceNewLow", PriceNewLow)
             .F("cumDeltaNewHigh", CumDeltaNewHigh).F("cumDeltaNewLow", CumDeltaNewLow)
             .F("bullishDeltaDivergenceCandidate", BullishDeltaDivergenceCandidate)
             .F("bearishDeltaDivergenceCandidate", BearishDeltaDivergenceCandidate)
             .F("deltaConfirmsBreak", DeltaConfirmsBreak)
             .F("deltaFailsBreak", DeltaFailsBreak);

            r.F("pocPrice", PocPrice).F("pocVolume", PocVolume)
             .F("closeMinusPocPts", CloseMinusPocPts);
        }
    }

    /// Rolling divergence tracker. Divergence is judged from a trailing
    /// window only - a definition needing future confirmation would not be
    /// a feature at all.
    public class V4DivergenceTracker
    {
        public int Lookback = 20;
        private readonly V4Roll price;
        private readonly V4Roll cumDelta;

        public V4DivergenceTracker(int lookback)
        {
            Lookback = lookback;
            price = new V4Roll(lookback);
            cumDelta = new V4Roll(lookback);
        }

        public void Update(V4OrderFlowFeatures f, double high, double low, double cumDeltaNow)
        {
            double priorHigh = price.Count > 0 ? price.Max() : double.NaN;
            double priorLow = price.Count > 0 ? price.Min() : double.NaN;
            double cdHigh = cumDelta.Count > 0 ? cumDelta.Max() : double.NaN;
            double cdLow = cumDelta.Count > 0 ? cumDelta.Min() : double.NaN;

            f.PriceNewHigh = V4Num.Ok(priorHigh) && high > priorHigh;
            f.PriceNewLow = V4Num.Ok(priorLow) && low < priorLow;
            f.CumDeltaNewHigh = V4Num.Ok(cdHigh) && cumDeltaNow > cdHigh;
            f.CumDeltaNewLow = V4Num.Ok(cdLow) && cumDeltaNow < cdLow;

            // price makes a new extreme, cumulative delta does not follow
            f.BearishDeltaDivergenceCandidate = f.PriceNewHigh && !f.CumDeltaNewHigh;
            f.BullishDeltaDivergenceCandidate = f.PriceNewLow && !f.CumDeltaNewLow;

            f.DeltaConfirmsBreak = (f.PriceNewHigh && f.CumDeltaNewHigh)
                                || (f.PriceNewLow && f.CumDeltaNewLow);
            f.DeltaFailsBreak = f.BearishDeltaDivergenceCandidate
                             || f.BullishDeltaDivergenceCandidate;

            price.Add(high); price.Add(low);
            cumDelta.Add(cumDeltaNow);
        }
    }
}
