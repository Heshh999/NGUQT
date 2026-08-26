#!/usr/bin/env python3
# ======================================================================
# HIGH-ARRIVAL-UTILITY-V1  (H2) - FROZEN HISTORICAL EXECUTION + DESTRUCTION
# ======================================================================
# AUTHORITATIVE PREREGISTRATION:
#   docs/RVMR_STRUCTURE_TO_PREDICTION_V1_PREREGISTRATION.md
#   sha256 afac484b3d75a7bce9533a0fd8304a66fd653587eea5f20e4dac794a0898dbb8
#   commit cdfcb3148513264ba58a7880ea794c4baa72f1e4
#
# H2 ONLY. H1 (MEMORY-PRED-V1) IS NOT USED AND NOT COMBINED. LEVERAGE-V
# IS NOT RE-TESTED AS A HYPOTHESIS - its structural replication already
# stands. H2 asks whether the FROZEN propensity carries INCREMENTAL
# forecast information about future movement, beyond the current shock.
#
# EPISTEMIC STATUS: 2019-07 .. 2026-08 is EXPOSED for this hypothesis.
# DEVELOPMENT / MECHANISM TESTING ONLY - not OOS, not prospective, not
# proof of edge. Best possible status:
# DEVELOPMENT-SUPPORTED PREDICTIVE CANDIDATE.
#
# SUBMITS NO ORDERS. SIMULATES NO TRADE. NOTHING FROZEN IS MODIFIED.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
#
# ----------------------------------------------------------------------
# PRE-COMPUTATION CHOICES, RECORDED BEFORE ANY RESULT EXISTS
# (the preregistration is silent on each; none is chosen to favour the
#  hypothesis; alternates are reported):
#
# (a) HA10 tail-trim scope. GATE = WITHIN-GROUP trim (P-HIGH and P-LOW
#     each lose their own top 1% / 5% by move30); the POOLED trim is
#     also computed and reported with its composition. Same rationale
#     and precedent as H1's MP10: move30 rises mechanically with the
#     propensity group, so a pooled trim removes mostly P-HIGH events
#     and confounds a tail test with a composition shift.
# (b) Time-of-day bucket for dummies/controls = bucket of mod[i1], the
#     DECISION bar (frozen buckets 2.5 name the buckets, not the bar).
# (c) Prior-60-bar controls: rr60 = mean(h-l over array positions
#     i1-59..i1) / c[i1]; logv60 = log(mean volume over the same 60
#     positions, floored at 1e-9). No contiguity requirement - they are
#     smoothing controls, not outcomes.
# (d) The regression coefficient bootstrap uses numpy multinomial
#     day-weights (statistically identical to whole-day resampling with
#     replacement), generator PCG64 seeded 20260825, disclosed. All
#     scalar bootstraps keep random.Random(20260825) exactly as H1.
# (e) BH at M_binding = 2 is now EXACT: H1's primary p = 0.00005 is on
#     the record, so H2's q needs no bound.
# (f) C sliced by CURRENT RVMR state RB[i1] is reported as a
#     directive-requested diagnostic (non-gated). The frozen instrument
#     for the current-RVMR control is the score covariate inside B1/B2.
# (g) Reproduction tolerances: cutpoints 5e-11 (10-dp published);
#     propensities 5e-5 + boundary-drift allowance reported (4-dp
#     published) - parity is verified with FULL-PRECISION discovery
#     cutpoints (exact reproduction of CONFIRM_FREEZE), while the H2
#     run itself uses the FROZEN 10-dp constants, as preregistered.
# ======================================================================

import os, sys, math, random, collections, hashlib, time
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../rvmr'))
import rvmr_spec as RS
import rvmr_run as RV
import numpy as np

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
PREREG = os.path.join(ROOT, 'docs',
                      'RVMR_STRUCTURE_TO_PREDICTION_V1_PREREGISTRATION.md')
PREREG_SHA = ('afac484b3d75a7bce9533a0fd8304a66fd653587eea5f20e4dac794a'
              '0898dbb8')

SEED = 20260825
B_MAIN, B_DESC, PERM = 20000, 4000, 20000
BP = 1e4
DISC_END = '2023-12-31'
PROSPECTIVE_START = '2026-08-26'
H1_PRIMARY_P = 0.00005          # on the record: MEMORY_PRED_V1_FINDINGS
COST_PTS = 0.87

# ---- FROZEN constants (prereg 2.2 / 2.3 / 2.4 / 2.5) ----
DECS9 = [-0.0011017009, -0.0005520548, -0.0002889478, -0.0001179931,
         +0.0000168159, +0.0001601759, +0.0003325537, +0.0005951824,
         +0.0011091640]
PROP = [0.6402, 0.4257, 0.3228, 0.2608, 0.2374, 0.2469, 0.2741,
        0.3174, 0.3870, 0.5562]
GCUT1, GCUT2 = 0.30, 0.40                      # P-LOW < .30 <= P-MID < .40 <= P-HIGH
BANDS = sorted(abs(x) for x in DECS9)          # nine edges -> ten |shock| bands
GN = ('P-LOW', 'P-MID', 'P-HIGH')
TODN = ('OVERNIGHT', 'RTH_AM', 'RTH_PM')
MIN_TOTAL, MIN_GROUP = 100000, 20000
PASS = {True: 'PASS', False: 'FAIL'}


def mean(x):
    return sum(x) / len(x) if x else float('nan')


def med_of(x):
    s = sorted(x)
    return s[len(s) // 2] if s else float('nan')


def quantile(sv, q):
    n = len(sv)
    h = (n - 1) * q
    lo = int(math.floor(h))
    hi = min(lo + 1, n - 1)
    return sv[lo] + (h - lo) * (sv[hi] - sv[lo])


def dec_of(x, cuts=DECS9):
    for k, cc in enumerate(cuts):
        if x < cc:
            return k
    return 9


def grp_of(dec):
    p = PROP[dec]
    return 0 if p < GCUT1 else (1 if p < GCUT2 else 2)


def band_of(a):
    for k, e in enumerate(BANDS):
        if a < e:
            return k
    return 9


def boot_diff(blocks, iters, seed=SEED):
    """blocks: [(sA,nA,sB,nB)] per day -> A-B mean diff, CI, two-sided p."""
    nb = len(blocks)
    SA = sum(b[0] for b in blocks); NA = sum(b[1] for b in blocks)
    SB = sum(b[2] for b in blocks); NB = sum(b[3] for b in blocks)
    if not NA or not NB or nb < 15:
        return float('nan'), float('nan'), float('nan'), float('nan')
    obs = SA / NA - SB / NB
    rnd = random.Random(seed)
    rr = rnd.randrange
    out = []
    for _ in range(iters):
        sa = sb = 0.0; na = nb2 = 0
        for _ in range(nb):
            b = blocks[rr(nb)]
            sa += b[0]; na += b[1]; sb += b[2]; nb2 += b[3]
        if na and nb2:
            out.append(sa / na - sb / nb2)
    out.sort()
    m = len(out)
    lo, hi = out[int(.025 * m)], out[int(.975 * m)]
    le = sum(1 for x in out if x <= 0)
    ge = sum(1 for x in out if x >= 0)
    p = max(2.0 * min(le, ge) / m, 1.0 / (m + 1.0))
    return obs, lo, hi, p


def boot_mean(blocks, iters, seed=SEED):
    nb = len(blocks)
    S = sum(b[0] for b in blocks); N = sum(b[1] for b in blocks)
    if not N or nb < 15:
        return float('nan'), float('nan'), float('nan')
    obs = S / N
    rnd = random.Random(seed)
    rr = rnd.randrange
    out = []
    for _ in range(iters):
        s = 0.0; n = 0
        for _ in range(nb):
            b = blocks[rr(nb)]
            s += b[0]; n += b[1]
        if n:
            out.append(s / n)
    out.sort()
    m = len(out)
    return obs, out[int(.025 * m)], out[int(.975 * m)]


def atr20_arrays(h, l, c):
    n = len(c)
    out = [None] * n
    tr = collections.deque(); s = 0.0; prev = None
    for i in range(n):
        t = (h[i] - l[i]) if prev is None else max(
            h[i] - l[i], abs(h[i] - prev), abs(l[i] - prev))
        tr.append(t); s += t
        prev = c[i]
        if len(tr) > 20:
            s -= tr.popleft()
        if len(tr) == 20:
            out[i] = s / 20.0
    return out


def build_blocks(day, em, c, lo_day, hi_day):
    """Frozen 15m block construction (scan2_run.py:68-89)."""
    N = len(c)
    rets = []
    for i in range(1, N):
        if em[i] - em[i - 1] != 1 or c[i - 1] <= 0:
            continue
        if not (lo_day <= day[i] <= hi_day):
            continue
        rets.append((i, math.log(c[i] / c[i - 1])))
    runs = collections.defaultdict(list)
    for i, r in rets:
        runs[day[i]].append((i, r))
    r15 = []
    for dd in sorted(runs):
        rs = runs[dd]; k = 0
        while k + 15 <= len(rs):
            bk = rs[k:k + 15]
            if bk[-1][0] - bk[0][0] == 14:
                r15.append((bk[0][0], bk[-1][0], sum(x[1] for x in bk), dd))
                k += 15
            else:
                k += 1
    return r15


def main():
    t0 = time.time()
    print('=' * 78)
    print('HIGH-ARRIVAL-UTILITY-V1  (H2)   FROZEN HISTORICAL EXECUTION')
    print('  prereg sha256 %s' % PREREG_SHA[:40])
    print('  commit cdfcb3148513264ba58a7880ea794c4baa72f1e4')
    print('  DEVELOPMENT / MECHANISM TESTING - NOT OOS, NOT PROSPECTIVE')
    print('  H2 ONLY. H1 NOT USED. NO COMBINATION. NO ORDERS.')
    print('=' * 78)

    # ================================================= PHASE 0
    print('\n' + '=' * 78)
    print('PHASE 0  FREEZE VERIFICATION')
    print('=' * 78)
    got = hashlib.sha256(open(PREREG, 'rb').read()).hexdigest()
    ok1 = (got == PREREG_SHA)
    print('  (1,2) prereg sha256 %s  matches frozen: %s' % (got[:32], ok1))
    ok_rs = (RS.T1 == 1.270 and RS.T2 == 2.335 and RS.W == 1440)
    print('  (3) RVMR spec  T1 %.3f T2 %.3f W %d  -> %s'
          % (RS.T1, RS.T2, RS.W, ok_rs))
    print('  (6) propensity groups  P-LOW < %.2f <= P-MID < %.2f <= P-HIGH'
          % (GCUT1, GCUT2))
    gmap = collections.defaultdict(list)
    for d in range(10):
        gmap[grp_of(d)].append(d)
    print('      derived bin sets  P-LOW %s  P-MID %s  P-HIGH %s'
          % (gmap[0], gmap[1], gmap[2]))
    ok_gp = (gmap[0] == [3, 4, 5, 6] and gmap[1] == [2, 7, 8]
             and gmap[2] == [0, 1, 9])
    print('      matches frozen sets {d3..d6}/{d2,d7,d8}/{d1,d9,d0}: %s'
          % ok_gp)
    print('  (7) outcome  move30 = (max high[i1+1..i1+30] - min low[..])'
          ' / close[i1]')
    print('  (8) B2 = B1 + |shock|^2 + down + down*|shock|;'
          '  A = B2 + propensity')
    print('  (9) controls: ATR terc, |shock| terc, ToD, C_matched 27-cell,'
          ' current-RVMR score in B1/B2')
    print('  (10) calibration: 3 frozen groups + 10 deciles, Brier vs'
          ' constant base rate, |err|<=0.10 per group')
    print('  (11) HA1..HA10 as frozen   (12) prospective start %s'
          % PROSPECTIVE_START)

    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    N = len(D['c'])
    h, l, c, v, em, mod, day, et = (D['h'], D['l'], D['c'], D['v'],
                                    D['em'], D['mod'], D['day'], D['et'])
    rng_bar = [h[i] - l[i] for i in range(N)]
    rr = RS.trailing_ratio(rng_bar)
    RB = [RS.bucket(x) if x is not None else None for x in rr]
    atr = atr20_arrays(h, l, c)
    post = sum(1 for i in range(N) if day[i] >= PROSPECTIVE_START)
    print('\n  bars %d   %s .. %s   rows at/after prospective start: %d'
          % (N, et[0], et[-1], post))
    probe_ok = True
    for p in (1440, 500000, 1200000, 2000000, 2500000):
        if p < N:
            direct = rng_bar[p] / (sum(rng_bar[p - 1440:p]) / 1440.0)
            if abs(direct - rr[p]) > 1e-9:
                probe_ok = False
    print('  RVMR causality probes: %s' % ('EXACT' if probe_ok else 'FAIL'))

    # ---- (4,5) discovery cutpoint + propensity lookup parity
    print('\n  (4) discovery cutpoint parity (tolerance 5e-11):')
    r15d = build_blocks(day, em, c, '0000', DISC_END)
    pairs = []
    for a in range(len(r15d) - 1):
        i0, i1, rv_, dd = r15d[a]
        j0, j1, rf, dd2 = r15d[a + 1]
        if j0 - i1 == 1:
            pairs.append(rv_)
    xs = sorted(pairs)
    exact_cuts = [xs[int(q * len(xs) / 10)] for q in range(1, 10)]
    ok_cut = all(abs(exact_cuts[k] - DECS9[k]) <= 5e-11 for k in range(9))
    print('      %d discovery pairs; max |delta| %.2e  -> %s'
          % (len(pairs), max(abs(exact_cuts[k] - DECS9[k])
                             for k in range(9)), ok_cut))
    print('  (5) discovery propensity parity (verbatim leverage scan,'
          ' FULL-PRECISION cuts; 4-dp published):')
    lvd = collections.defaultdict(list)
    for (i0, i1, rv_, dd) in r15d:
        fut = any(RB[j] == 'HIGH' for j in range(i1 + 1, min(i1 + 31, N)))
        lvd[dec_of(rv_, exact_cuts)].append(1 if fut else 0)
    maxdp = 0.0
    for d in range(10):
        pv = mean(lvd[d])
        maxdp = max(maxdp, abs(pv - PROP[d]))
        print('      d%d  reproduced %.6f   frozen %.4f   delta %+.2e'
              % (d, pv, PROP[d], pv - PROP[d]))
    ok_pp = maxdp <= 5e-5
    print('      max |delta| %.2e  (tolerance 5e-5)  -> %s' % (maxdp, ok_pp))
    if not (ok1 and ok_rs and ok_gp and ok_cut and ok_pp and probe_ok):
        print('\nHIGH-ARRIVAL-UTILITY-V1 FREEZE FAILURE')
        return
    print('  FREEZE VERIFIED.  (%.0f s)' % (time.time() - t0))
    del r15d, pairs, xs, lvd

    # ================================================= EVENTS
    print('\n' + '=' * 78)
    print('EVENT CONSTRUCTION  (full development set; post-start rows'
          ' excluded)')
    print('=' * 78)
    r15 = build_blocks(day, em, c, '0000', '9999')
    print('  15m blocks (frozen construction) %d' % len(r15))
    # prefix sums for rr60 / v60
    pre_r = [0.0] * (N + 1)
    pre_v = [0.0] * (N + 1)
    for i in range(N):
        pre_r[i + 1] = pre_r[i] + rng_bar[i]
        pre_v[i + 1] = pre_v[i] + v[i]
    days_all = sorted(set(day))
    dayid = {d: k for k, d in enumerate(days_all)}

    e_day = array('i'); e_grp = array('b'); e_dec = array('b')
    e_mv = array('d'); e_y = array('b'); e_down = array('b')
    e_abs = array('d'); e_atr = array('d'); e_sc = array('d')
    e_tod = array('b'); e_rr60 = array('d'); e_lv60 = array('d')
    e_cst = array('b'); e_px = array('d')
    skip = collections.Counter()
    stmap = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
    for (i0, i1, rv_, dd) in r15:
        if i1 + 30 >= N:
            skip['end-of-data'] += 1; continue
        if em[i1 + 30] - em[i1] != 30:
            skip['forward window not contiguous'] += 1; continue
        if RB[i1] is None or atr[i1] is None or c[i1] <= 0:
            skip['state/atr unavailable'] += 1; continue
        if day[i1 + 1] >= PROSPECTIVE_START:
            skip['prospective (excluded, preserved)'] += 1; continue
        dec = dec_of(rv_)
        mv = (max(h[i1 + 1:i1 + 31]) - min(l[i1 + 1:i1 + 31])) / c[i1]
        yy = 1 if any(RB[j] == 'HIGH'
                      for j in range(i1 + 1, min(i1 + 31, N))) else 0
        m_ = mod[i1]
        e_day.append(dayid[day[i1 + 1]])
        e_grp.append(grp_of(dec)); e_dec.append(dec)
        e_mv.append(mv * BP); e_y.append(yy)
        e_down.append(1 if rv_ < 0 else 0)
        e_abs.append(abs(rv_) * BP)
        e_atr.append(atr[i1] / c[i1] * BP)
        e_sc.append(rr[i1])
        e_tod.append(0 if (m_ >= 1081 or m_ <= 569)
                     else (1 if m_ <= 750 else 2))
        e_rr60.append((pre_r[i1 + 1] - pre_r[i1 - 59]) / 60.0 / c[i1] * BP)
        mv60 = (pre_v[i1 + 1] - pre_v[i1 - 59]) / 60.0
        e_lv60.append(math.log(max(mv60, 1e-9)))
        e_cst.append(stmap[RB[i1]])
        e_px.append(c[i1])
    NE = len(e_mv)
    for k2, n2 in skip.items():
        print('  skipped - %-36s %7d' % (k2, n2))
    print('  ELIGIBLE EVENTS %d' % NE)
    gcnt = collections.Counter(e_grp)
    for g in range(3):
        print('    %-7s %7d  (%.1f%%)' % (GN[g], gcnt[g],
                                          100.0 * gcnt[g] / NE))
    decc = collections.Counter(e_dec)
    print('  decile occupancy under FROZEN cutpoints: '
          + ' '.join('%d:%d' % (d2, decc[d2]) for d2 in range(10)))

    # ================================================= CAUSAL AUDIT
    print('\n' + '=' * 78)
    print('CAUSAL AUDIT')
    print('=' * 78)
    rows = [
        ('block return rv (bars i0..i1)', 'close of bar i1', 'move30', True),
        ('decile: frozen 10-dp cutpoints (2026-08-25)', 'close of i1',
         'move30', True),
        ('propensity: frozen 10-constant lookup', 'close of i1', 'move30',
         True),
        ('group P-LOW/MID/HIGH (cuts .30/.40, frozen)', 'close of i1',
         'move30', True),
        ('down = (rv < 0)', 'close of i1', 'move30', True),
        ('atrRel = atr20(i1)/c[i1] (bars i1-19..i1)', 'close of i1',
         'move30', True),
        ('RVMR score rr[i1] (bars i1-1440..i1-1)', 'close of i1-1',
         'move30', True),
        ('current state RB[i1]', 'close of i1-1', 'move30', True),
        ('ToD bucket of mod[i1]', 'clock', 'move30', True),
        ('rr60 / logv60 (bars i1-59..i1)', 'close of i1', 'move30', True),
        ('move30 (bars i1+1..i1+30)  OUTCOME', 'close of i1+30', 'itself',
         True),
        ('HIGH-arrival y (states of bars i1+1..i1+30)', 'outcome window',
         'itself', True),
    ]
    allyes = True
    print('  %-46s %-18s %-8s %s' % ('FIELD', 'AVAILABLE', 'OUTCOME',
                                     'CAUSAL'))
    for f, a, o, ok in rows:
        allyes = allyes and ok
        print('  %-46s %-18s %-8s %s' % (f, a, o, 'YES' if ok else 'NO'))
    print('  ALL ROWS YES: %s' % (allyes and probe_ok))

    # ================================================= PRIMARY
    print('\n' + '=' * 78)
    print('PRIMARY   E[move30] by frozen propensity group')
    print('=' * 78)
    px_hl = [e_px[i] for i in range(NE) if e_grp[i] != 1]
    pxm = mean(px_hl)
    del px_hl

    def blocks_for(mask):
        dd2 = {}
        for i in range(NE):
            if not mask(i):
                continue
            e = dd2.get(e_day[i])
            if e is None:
                e = dd2[e_day[i]] = [0.0, 0]
            e[0] += e_mv[i]; e[1] += 1
        return [tuple(x) for x in dd2.values()]

    def blocks_diff_for(maskA, maskB):
        dd2 = {}
        for i in range(NE):
            a = maskA(i); b = maskB(i)
            if not (a or b):
                continue
            e = dd2.get(e_day[i])
            if e is None:
                e = dd2[e_day[i]] = [0.0, 0, 0.0, 0]
            if a:
                e[0] += e_mv[i]; e[1] += 1
            if b:
                e[2] += e_mv[i]; e[3] += 1
        return [tuple(x) for x in dd2.values()]

    gm = {}
    print('  %-7s %8s %11s %11s %24s' % ('group', 'n', 'mean bp',
                                         'median bp', '95% CI (bp)'))
    for g in range(3):
        vals = [e_mv[i] for i in range(NE) if e_grp[i] == g]
        m, lo, hi = boot_mean(blocks_for(lambda i, gg=g: e_grp[i] == gg),
                              B_DESC)
        gm[g] = m
        print('  %-7s %8d %11.3f %11.3f   [%9.3f, %9.3f]'
              % (GN[g], len(vals), m, med_of(vals), lo, hi))
        del vals
    mono = gm[0] < gm[1] < gm[2]
    dblk = blocks_diff_for(lambda i: e_grp[i] == 2, lambda i: e_grp[i] == 0)
    C, Clo, Chi, Cp = boot_diff(dblk, B_MAIN)
    print('\n  monotone P-LOW < P-MID < P-HIGH: %s' % mono)
    print('  C = E[move30|P-HIGH] - E[move30|P-LOW] = %+0.3f bp'
          '   CI [%+0.3f, %+0.3f]   boot p %.5f' % (C, Clo, Chi, Cp))
    print('  as %% of P-LOW mean: %+.1f%%   in NQ points at mean close'
          ' %.0f: %+0.3f pts' % (100 * C / gm[0], pxm, C / BP * pxm))
    print('  (%.0f s)' % (time.time() - t0))

    # ================================================= REGRESSION B1/B2/A
    print('\n' + '=' * 78)
    print('THE DECISIVE TEST  B1 / B2 / A = B2 + propensity  (HA6 binding)')
    print('=' * 78)
    X = np.empty((NE, 12))
    X[:, 0] = 1.0
    X[:, 1] = np.frombuffer(e_abs, dtype=np.float64)
    X[:, 2] = np.frombuffer(e_atr, dtype=np.float64)
    X[:, 3] = np.frombuffer(e_sc, dtype=np.float64)
    tod = np.frombuffer(e_tod, dtype=np.int8)
    X[:, 4] = (tod == 1)
    X[:, 5] = (tod == 2)
    X[:, 6] = np.frombuffer(e_rr60, dtype=np.float64)
    X[:, 7] = np.frombuffer(e_lv60, dtype=np.float64)
    X[:, 8] = X[:, 1] ** 2 / 100.0
    X[:, 9] = np.frombuffer(e_down, dtype=np.int8)
    X[:, 10] = X[:, 9] * X[:, 1]
    X[:, 11] = np.array(PROP)[np.frombuffer(e_dec, dtype=np.int8)]
    Y = np.frombuffer(e_mv, dtype=np.float64).copy()
    dayarr = np.frombuffer(e_day, dtype=np.int32).copy()
    order = np.argsort(dayarr, kind='stable')
    X = X[order]; Y = Y[order]; dayarr = dayarr[order]
    ud, starts = np.unique(dayarr, return_index=True)
    Dn = len(ud)
    XP = X[:, :, None] * X[:, None, :]
    Gd = np.add.reduceat(XP.reshape(NE, 144), starts, axis=0)
    del XP
    Hd = np.add.reduceat(X * Y[:, None], starts, axis=0)
    yyd = np.add.reduceat(Y * Y, starts, axis=0)
    ysd = np.add.reduceat(Y, starts, axis=0)
    nd = np.diff(np.append(starts, NE)).astype(np.float64)
    Gf = Gd.sum(0).reshape(12, 12)
    Hf = Hd.sum(0)
    yy = yyd.sum(); ys = ysd.sum(); nn = nd.sum()
    sst = yy - ys * ys / nn

    def fit(cols):
        Gs = Gf[np.ix_(cols, cols)]
        hs = Hf[list(cols)]
        beta = np.linalg.solve(Gs, hs)
        sse = yy - beta @ hs
        return beta, 1.0 - sse / sst

    cB1 = list(range(8))
    cB2 = list(range(11))
    cA = list(range(12))
    bB1, r2B1 = fit(cB1)
    bB2, r2B2 = fit(cB2)
    bA, r2A = fit(cA)
    dR2 = r2A - r2B2
    print('  R2(B1) %.6f   R2(B2) %.6f   R2(A) %.6f   dR2(A vs B2)'
          ' %+.6f' % (r2B1, r2B2, r2A, dR2))
    print('  full-sample propensity coefficient %+0.4f bp of move30 per'
          ' unit propensity' % bA[11])
    print('  ( = %+0.4f bp per +0.10 propensity; frozen P spread'
          ' P-HIGH-P-LOW mean gap is reported below )' % (bA[11] * 0.10))
    # adjusted gap implied by the model at the group propensity means
    pmeans = [mean([PROP[e_dec[i]] for i in range(NE) if e_grp[i] == g])
              for g in range(3)]
    print('  mean propensity by group  P-LOW %.4f  P-MID %.4f  P-HIGH %.4f'
          % tuple(pmeans))
    print('  model-implied adjusted P-HIGH-P-LOW gap: %+0.3f bp'
          % (bA[11] * (pmeans[2] - pmeans[0])))

    # day-multinomial bootstrap of the propensity coefficient
    rngnp = np.random.default_rng(SEED)
    Gdf = Gd.astype(np.float64)
    Hdf = Hd.astype(np.float64)
    betas = np.empty(B_MAIN)
    CH = 2000
    done = 0
    while done < B_MAIN:
        k2 = min(CH, B_MAIN - done)
        W = rngnp.multinomial(Dn, np.full(Dn, 1.0 / Dn),
                              size=k2).astype(np.float64)
        Gb = (W @ Gdf).reshape(k2, 12, 12)
        Hb = W @ Hdf
        try:
            sol = np.linalg.solve(Gb, Hb[..., None])[..., 0]
        except np.linalg.LinAlgError:
            sol = np.stack([np.linalg.lstsq(Gb[j], Hb[j], rcond=None)[0]
                            for j in range(k2)])
        betas[done:done + k2] = sol[:, 11]
        done += k2
    betas.sort()
    blo = betas[int(.025 * B_MAIN)]; bhi = betas[int(.975 * B_MAIN)]
    le = int((betas <= 0).sum()); ge = int((betas >= 0).sum())
    bpv = max(2.0 * min(le, ge) / B_MAIN, 1.0 / (B_MAIN + 1.0))
    print('  day-clustered bootstrap (20,000 multinomial day-weights,'
          ' PCG64 seed %d):' % SEED)
    print('    coefficient CI [%+0.4f, %+0.4f]   two-sided p %.5f'
          % (blo, bhi, bpv))
    ha6 = (bA[11] > 0) and (blo > 0) and (dR2 > 0)
    print('  HA6: coef>0 %s  CI excl 0 %s  dR2>0 %s  -> %s'
          % (bA[11] > 0, blo > 0, dR2 > 0, PASS[ha6]))
    print('  NOTE: with an intercept, in-sample R2 cannot fall when a'
          ' regressor is added, so dR2>0 is near-tautological; the CI is'
          ' the informative leg.')
    print('  (%.0f s)' % (time.time() - t0))

    # ================================================= CONTROL SLICES
    print('\n' + '=' * 78)
    print('CONTROL SLICES  (C recomputed inside frozen partitions)')
    print('=' * 78)
    aa = sorted(e_atr)
    a1, a2 = quantile(aa, 1 / 3.0), quantile(aa, 2 / 3.0)
    del aa
    bb = sorted(e_abs)
    b1, b2 = quantile(bb, 1 / 3.0), quantile(bb, 2 / 3.0)
    del bb
    print('  atrRel tercile cuts (bp)  %.6f  %.6f' % (a1, a2))
    print('  |shock| tercile cuts (bp) %.6f  %.6f' % (b1, b2))

    def atr_t(i):
        x = e_atr[i]
        return 0 if x < a1 else (1 if x <= a2 else 2)

    def abs_t(i):
        x = e_abs[i]
        return 0 if x < b1 else (1 if x <= b2 else 2)

    print('\n  ATR CONTROL (HA5 leg 1)')
    atr_pos = 0
    for t2 in range(3):
        bl = blocks_diff_for(lambda i, tt=t2: e_grp[i] == 2 and atr_t(i) == tt,
                             lambda i, tt=t2: e_grp[i] == 0 and atr_t(i) == tt)
        dd2, lo2, hi2, _ = boot_diff(bl, B_DESC)
        nH2 = sum(1 for i in range(NE) if e_grp[i] == 2 and atr_t(i) == t2)
        nL2 = sum(1 for i in range(NE) if e_grp[i] == 0 and atr_t(i) == t2)
        if dd2 > 0:
            atr_pos += 1
        print('    ATR terc %d  nPH %6d nPL %6d  C %+0.3f bp'
              '  CI [%+0.3f, %+0.3f]' % (t2, nH2, nL2, dd2, lo2, hi2))
    print('    terciles with C > 0: %d of 3' % atr_pos)

    print('\n  |SHOCK| TERCILE SLICES (the overlap problem, reported)')
    for t2 in range(3):
        nH2 = sum(1 for i in range(NE) if e_grp[i] == 2 and abs_t(i) == t2)
        nL2 = sum(1 for i in range(NE) if e_grp[i] == 0 and abs_t(i) == t2)
        if nH2 < 30 or nL2 < 30:
            print('    |shock| terc %d  nPH %6d nPL %6d  C: DEGENERATE'
                  ' (no overlap - propensity is a function of the shock)'
                  % (t2, nH2, nL2))
            continue
        bl = blocks_diff_for(lambda i, tt=t2: e_grp[i] == 2 and abs_t(i) == tt,
                             lambda i, tt=t2: e_grp[i] == 0 and abs_t(i) == tt)
        dd2, lo2, hi2, _ = boot_diff(bl, B_DESC)
        print('    |shock| terc %d  nPH %6d nPL %6d  C %+0.3f bp'
              '  CI [%+0.3f, %+0.3f]' % (t2, nH2, nL2, dd2, lo2, hi2))

    print('\n  C_matched  27-cell (ATR x |shock| x ToD), common weight,'
          ' cells >=30 both sides (HA5 leg 2)')
    agg = {}
    for i in range(NE):
        g = e_grp[i]
        if g == 1:
            continue
        cid = (atr_t(i), abs_t(i), e_tod[i])
        e = agg.get(cid)
        if e is None:
            e = agg[cid] = [0.0, 0, 0.0, 0]
        if g == 2:
            e[0] += e_mv[i]; e[1] += 1
        else:
            e[2] += e_mv[i]; e[3] += 1
    num = den = 0.0
    used = 0
    for cid, e in agg.items():
        if e[1] >= 30 and e[3] >= 30:
            w = e[1] + e[3]
            num += w * (e[0] / e[1] - e[2] / e[3]); den += w
            used += 1
    cov = den / (gcnt[0] + gcnt[2])
    Cm = num / den if den else float('nan')
    print('    cells used %d of 27   events covered %.1f%% of P-HIGH u'
          ' P-LOW' % (used, 100 * cov))
    print('    C_matched %+0.3f bp   vs C_raw %+0.3f bp   retention %.1f%%'
          % (Cm, C, 100 * Cm / C if C else float('nan')))

    print('\n  TIME-OF-DAY (HA7; bucket of decision bar i1)')
    tod_pos = 0
    for t2, nm in enumerate(TODN):
        bl = blocks_diff_for(lambda i, tt=t2: e_grp[i] == 2 and e_tod[i] == tt,
                             lambda i, tt=t2: e_grp[i] == 0 and e_tod[i] == tt)
        dd2, lo2, hi2, _ = boot_diff(bl, B_DESC)
        if dd2 > 0:
            tod_pos += 1
        nH2 = sum(1 for i in range(NE) if e_grp[i] == 2 and e_tod[i] == t2)
        nL2 = sum(1 for i in range(NE) if e_grp[i] == 0 and e_tod[i] == t2)
        print('    %-10s nPH %6d nPL %6d  C %+0.3f bp  CI [%+0.3f, %+0.3f]'
              % (nm, nH2, nL2, dd2, lo2, hi2))
    print('    buckets with C > 0: %d of 3' % tod_pos)

    print('\n  CURRENT-RVMR STATE SLICES (directive-requested diagnostic,'
          ' NON-GATED;')
    print('  the frozen current-RVMR control is the score covariate'
          ' inside B1/B2)')
    for s2, nm in enumerate(('LOW', 'MEDIUM', 'HIGH')):
        nH2 = sum(1 for i in range(NE) if e_grp[i] == 2 and e_cst[i] == s2)
        nL2 = sum(1 for i in range(NE) if e_grp[i] == 0 and e_cst[i] == s2)
        if nH2 < 30 or nL2 < 30:
            print('    RB[i1]=%-7s nPH %6d nPL %6d  C: insufficient'
                  % (nm, nH2, nL2))
            continue
        bl = blocks_diff_for(lambda i, ss=s2: e_grp[i] == 2 and e_cst[i] == ss,
                             lambda i, ss=s2: e_grp[i] == 0 and e_cst[i] == ss)
        dd2, lo2, hi2, _ = boot_diff(bl, B_DESC)
        print('    RB[i1]=%-7s nPH %6d nPL %6d  C %+0.3f bp'
              '  CI [%+0.3f, %+0.3f]' % (nm, nH2, nL2, dd2, lo2, hi2))
    print('  (%.0f s)' % (time.time() - t0))

    # ================================================= CALIBRATION
    print('\n' + '=' * 78)
    print('CALIBRATION  (frozen 3 groups primary; 10 deciles reported;'
          ' HA8)')
    print('=' * 78)
    ybar = mean([e_y[i] for i in range(NE)])
    brier = mean([(PROP[e_dec[i]] - e_y[i]) ** 2 for i in range(NE)])
    brier0 = ybar * (1 - ybar)
    print('  observed overall HIGH-arrival frequency %.4f' % ybar)
    print('  Brier(frozen propensity) %.6f   Brier(constant base rate)'
          ' %.6f   -> beats base: %s' % (brier, brier0, brier < brier0))
    gerr = []
    for g in range(3):
        idx2 = [i for i in range(NE) if e_grp[i] == g]
        pred = mean([PROP[e_dec[i]] for i in idx2])
        obs2 = mean([e_y[i] for i in idx2])
        gerr.append(abs(obs2 - pred))
        print('  %-7s n %7d  predicted %.4f  observed %.4f  |err| %.4f'
              % (GN[g], len(idx2), pred, obs2, abs(obs2 - pred)))
    print('  reliability by decile (frozen predicted vs observed):')
    for d2 in range(10):
        idx2 = [i for i in range(NE) if e_dec[i] == d2]
        print('    d%d  pred %.4f  obs %.4f  (n %d)'
              % (d2, PROP[d2], mean([e_y[i] for i in idx2]), len(idx2)))
    ha8 = all(x <= 0.10 for x in gerr) and brier <= brier0
    print('  HA8: max group |err| %.4f <= 0.10 %s  AND Brier <= base %s'
          '  -> %s' % (max(gerr), max(gerr) <= 0.10, brier <= brier0,
                       PASS[ha8]))

    # ================================================= ASYMMETRY
    print('\n' + '=' * 78)
    print('DOWNSIDE ASYMMETRY  (secondary, never gated; frozen |shock|'
          ' bands)')
    print('=' * 78)
    bandstat = [[0, 0, 0.0, 0, 0, 0.0] for _ in range(10)]
    # per band: nNeg, yNeg, mvNeg, nPos, yPos, mvPos
    dayasym = {}
    for i in range(NE):
        b3 = band_of(e_abs[i] / BP)
        s3 = bandstat[b3]
        e = dayasym.setdefault(e_day[i], [0.0] * 60)
        off = b3 * 6
        if e_down[i]:
            s3[0] += 1; s3[1] += e_y[i]; s3[2] += e_mv[i]
            e[off] += 1; e[off + 1] += e_y[i]; e[off + 2] += e_mv[i]
        else:
            s3[3] += 1; s3[4] += e_y[i]; s3[5] += e_mv[i]
            e[off + 3] += 1; e[off + 4] += e_y[i]; e[off + 5] += e_mv[i]
    eligb = [b3 for b3 in range(10)
             if bandstat[b3][0] >= 30 and bandstat[b3][3] >= 30]
    print('  %-4s %8s %8s %10s %10s %10s | %10s %10s'
          % ('band', 'nNeg', 'nPos', 'P(H|neg)', 'P(H|pos)', 'dP',
             'mvNeg bp', 'mvPos bp'))
    for b3 in range(10):
        s3 = bandstat[b3]
        if s3[0] < 30 or s3[3] < 30:
            print('  %-4d %8d %8d   (band too thin on one side)'
                  % (b3, s3[0], s3[3]))
            continue
        pn, pp2 = s3[1] / s3[0], s3[4] / s3[3]
        print('  %-4d %8d %8d %10.4f %10.4f %+10.4f | %10.3f %10.3f'
              % (b3, s3[0], s3[3], pn, pp2, pn - pp2,
                 s3[2] / s3[0], s3[5] / s3[3]))

    def asym_stat(dayset):
        acc = [[0.0] * 6 for _ in range(10)]
        for dk in dayset:
            e = dayasym.get(dk)
            if e is None:
                continue
            for b3 in range(10):
                off = b3 * 6
                for j in range(6):
                    acc[b3][j] += e[off + j]
        num2 = den2 = numm = 0.0
        for b3 in eligb:
            s3 = acc[b3]
            if s3[0] and s3[3]:
                w = s3[0] + s3[3]
                num2 += w * (s3[1] / s3[0] - s3[4] / s3[3])
                numm += w * (s3[2] / s3[0] - s3[5] / s3[3])
                den2 += w
        return ((num2 / den2 if den2 else float('nan')),
                (numm / den2 if den2 else float('nan')))

    dl = sorted(dayasym)
    obsA, obsM = asym_stat(dl)
    rnd = random.Random(SEED)
    outA = []
    for _ in range(B_DESC):
        sel = [dl[rnd.randrange(len(dl))] for _ in dl]
        a4, _m4 = asym_stat(sel)
        if a4 == a4:
            outA.append(a4)
    outA.sort()
    print('\n  band-matched P(HIGH|neg) - P(HIGH|pos) = %+0.4f'
          '   CI [%+0.4f, %+0.4f]   (%d iters)'
          % (obsA, outA[int(.025 * len(outA))],
             outA[int(.975 * len(outA))], B_DESC))
    print('  band-matched move30(neg) - move30(pos) = %+0.3f bp' % obsM)
    print('  by year (point estimates):')
    for y in sorted(set(days_all[d4][:4] for d4 in dl)):
        sub = [d4 for d4 in dl if days_all[d4][:4] == y]
        a4, m4 = asym_stat(sub)
        print('    %s  dP %+0.4f   dmove30 %+0.3f bp' % (y, a4, m4))
    print('  (%.0f s)' % (time.time() - t0))

    # ================================================= YEAR / MONTH
    print('\n' + '=' * 78)
    print('YEAR DESTRUCTION  (no year is OOS for H2)')
    print('=' * 78)
    yr_of = [days_all[e_day[i]][:4] for i in range(NE)]
    years = sorted(set(yr_of))
    yr_pos = 0
    print('  %-5s %7s %9s %9s %9s %6s %9s %10s'
          % ('year', 'n', 'P-LOW', 'P-MID', 'P-HIGH', 'mono', 'C bp',
             'beta_prop'))
    for y in years:
        idx2 = [i for i in range(NE) if yr_of[i] == y]
        gv = [mean([e_mv[i] for i in idx2 if e_grp[i] == g])
              for g in range(3)]
        Cy = gv[2] - gv[0]
        if Cy > 0:
            yr_pos += 1
        dmask = np.array([days_all[u][:4] == y for u in ud])
        Gy = Gdf[dmask].sum(0).reshape(12, 12)
        Hy = Hdf[dmask].sum(0)
        try:
            by = np.linalg.solve(Gy, Hy)[11]
        except np.linalg.LinAlgError:
            by = float('nan')
        print('  %-5s %7d %9.3f %9.3f %9.3f %6s %+9.3f %+10.4f'
              % (y, len(idx2), gv[0], gv[1], gv[2],
                 'YES' if gv[0] < gv[1] < gv[2] else 'no', Cy, by))
    print('  years with C > 0: %d of %d' % (yr_pos, len(years)))

    print('\n  MONTH DESTRUCTION')
    mo_of = [days_all[e_day[i]][:7] for i in range(NE)]
    magg = {}
    for i in range(NE):
        g = e_grp[i]
        if g == 1:
            continue
        e = magg.setdefault(mo_of[i], [0.0, 0, 0.0, 0])
        if g == 2:
            e[0] += e_mv[i]; e[1] += 1
        else:
            e[2] += e_mv[i]; e[3] += 1
    mvals = []
    for k3 in sorted(magg):
        e = magg[k3]
        if e[1] and e[3]:
            mvals.append((k3, e[0] / e[1] - e[2] / e[3]))
    mpos = sum(1 for _, x in mvals if x > 0)
    best = max(mvals, key=lambda z: z[1]); worst = min(mvals, key=lambda z: z[1])
    print('    months %d   positive %d   negative %d   median %+0.3f bp'
          % (len(mvals), mpos, len(mvals) - mpos,
             med_of([x for _, x in mvals])))
    print('    best %s %+0.3f bp    worst %s %+0.3f bp'
          % (best[0], best[1], worst[0], worst[1]))

    # ================================================= TAILS
    print('\n' + '=' * 78)
    print('TAIL DESTRUCTION  (gate = WITHIN-GROUP trim; pooled reported'
          ' - header note (a))')
    print('=' * 78)
    Hi = [i for i in range(NE) if e_grp[i] == 2]
    Li = [i for i in range(NE) if e_grp[i] == 0]
    Hs = sorted(Hi, key=lambda i: e_mv[i], reverse=True)
    Ls = sorted(Li, key=lambda i: e_mv[i], reverse=True)
    tail_wg = {}
    for frac in (0.01, 0.05):
        kH = max(1, int(round(frac * len(Hs))))
        kL = max(1, int(round(frac * len(Ls))))
        dd2 = (mean([e_mv[i] for i in Hs[kH:]])
               - mean([e_mv[i] for i in Ls[kL:]]))
        tail_wg[frac] = dd2
        print('  within-group remove top %4.1f%% (PH %5d, PL %5d removed)'
              '  C %+0.3f bp' % (frac * 100, kH, kL, dd2))
    pool = sorted(Hi + Li, key=lambda i: e_mv[i], reverse=True)
    for frac in (0.01, 0.05):
        k3 = max(1, int(round(frac * len(pool))))
        cut = set(pool[:k3])
        remH = sum(1 for i in cut if e_grp[i] == 2)
        hv = [e_mv[i] for i in Hi if i not in cut]
        lv = [e_mv[i] for i in Li if i not in cut]
        print('  pooled       remove top %4.1f%% (%6d removed; %5.1f%% of'
              ' them P-HIGH; %4.1f%% of ALL P-HIGH)  C %+0.3f bp'
              % (frac * 100, k3, 100.0 * remH / k3,
                 100.0 * remH / len(Hi), mean(hv) - mean(lv)))
        del hv, lv, cut
    tail_pass = tail_wg[0.01] > 0 and tail_wg[0.05] > 0
    del Hs, Ls, pool

    # ================================================= PERMUTATION
    print('\n' + '=' * 78)
    print('PERMUTATION NULL  within-day shuffle of propensity-group'
          ' labels (%d iters, seed %d)' % (PERM, SEED))
    print('=' * 78)
    byday = {}
    for i in range(NE):
        e = byday.get(e_day[i])
        if e is None:
            e = byday[e_day[i]] = [[], 0, 0]
        e[0].append(e_mv[i])
        if e_grp[i] == 2:
            e[1] += 1
        elif e_grp[i] == 0:
            e[2] += 1
    plan = []
    for k3, (vals, kh, kl) in byday.items():
        if kh == 0 and kl == 0:
            continue
        plan.append((vals, math.fsum(vals), kh, kh + kl, len(vals)))
    del byday
    NH = len(Hi); NL = len(Li)
    rnd = random.Random(SEED)
    rnd_random = rnd.random
    obs = abs(C)
    cnt = 0
    rep = max(1, PERM // 10)
    for it in range(PERM):
        sh = sl = 0.0
        for vals, tot, kh, take, n3 in plan:
            a4 = 0.0
            for j in range(kh):
                r3 = j + int(rnd_random() * (n3 - j))
                vj = vals[r3]; vals[r3] = vals[j]; vals[j] = vj
                a4 += vj
            b4 = 0.0
            for j in range(kh, take):
                r3 = j + int(rnd_random() * (n3 - j))
                vj = vals[r3]; vals[r3] = vals[j]; vals[j] = vj
                b4 += vj
            sh += a4; sl += b4
        if abs(sh / NH - sl / NL) >= obs:
            cnt += 1
        if (it + 1) % rep == 0:
            print('    ... permutation %6d / %d   exceedances %d  (%.0f s)'
                  % (it + 1, PERM, cnt, time.time() - t0), flush=True)
    perm_p = max((cnt + 1.0) / (PERM + 1.0), 1.0 / (PERM + 1.0))
    print('  observed C %+0.3f bp    permutation p = %.5f' % (C, perm_p))

    # ================================================= MULTIPLICITY
    print('\n' + '=' * 78)
    print('MULTIPLICITY  (BH exact - both primary p-values now exist)')
    print('=' * 78)
    ps = sorted([(H1_PRIMARY_P, 'H1'), (Cp, 'H2')])
    q_at = {}
    prev = 1.0
    for rank in (2, 1):
        pv, nm = ps[rank - 1]
        val = min(pv * 2.0 / rank, prev)
        prev = val
        q_at[nm] = val
    # M_cum = 4 is EXACT too: all four family p-values are on the record
    # (SHOCK-CONT-MEDIUM 0.10050, MONDAY-RTH 0.03570, H1 0.00005, H2 Cp).
    fam4 = sorted([(0.10050, 'SC'), (0.03570, 'MON'),
                   (H1_PRIMARY_P, 'H1'), (Cp, 'H2')])
    q4map = {}
    prev4 = 1.0
    for rank in (4, 3, 2, 1):
        pv, nm = fam4[rank - 1]
        prev4 = min(pv * 4.0 / rank, prev4)
        q4map[nm] = prev4
    print('  H1 primary p %.5f   H2 primary p %.5f' % (H1_PRIMARY_P, Cp))
    print('  BH q (M_binding=2):  H1 %.5f   H2 %.5f' % (q_at['H1'],
                                                        q_at['H2']))
    print('  BH q (M_cum=4, NON-BINDING sensitivity, exact): H2 %.5f'
          % q4map['H2'])

    # ================================================= GATES
    print('\n' + '=' * 78)
    print('HA1 - HA10   HIGH-ARRIVAL-UTILITY-V1 GATES')
    print('=' * 78)
    prec = (NE >= MIN_TOTAL and all(gcnt[g] >= MIN_GROUP for g in range(3)))
    print('  PRECONDITION  total %d>=%d, groups %d/%d/%d >= %d  -> %s'
          % (NE, MIN_TOTAL, gcnt[0], gcnt[1], gcnt[2], MIN_GROUP,
             PASS[prec]))
    g5 = []
    g5.append(('HA1', 'no leakage',
               'frozen lookup; predictors at close of i1; outcome'
               ' i1+1..i1+30; %d post-start rows excluded; audit all YES'
               % skip.get('prospective (excluded, preserved)', 0),
               allyes and probe_ok))
    g5.append(('HA2', 'monotone P-LOW < P-MID < P-HIGH',
               '%.3f < %.3f < %.3f' % (gm[0], gm[1], gm[2]), mono))
    g5.append(('HA3', 'CI on C excludes 0',
               'C %+0.3f, CI [%+0.3f, %+0.3f]' % (C, Clo, Chi),
               Clo > 0 or Chi < 0))
    g5.append(('HA4', 'BH q<=0.05 AND perm p<=0.05',
               'q %.5f, perm p %.5f' % (q_at['H2'], perm_p),
               q_at['H2'] <= 0.05 and perm_p <= 0.05))
    g5.append(('HA5', 'C>0 in >=2/3 ATR tercs AND C_matched >= 0.5 C_raw',
               '%d/3; matched %+0.3f vs raw %+0.3f' % (atr_pos, Cm, C),
               atr_pos >= 2 and Cm >= 0.5 * C))
    g5.append(('HA6', 'B2-incremental propensity (BINDING)',
               'coef %+0.4f, CI [%+0.4f, %+0.4f], dR2 %+0.6f'
               % (bA[11], blo, bhi, dR2), ha6))
    g5.append(('HA7', 'C>0 in >=2/3 ToD buckets', '%d of 3' % tod_pos,
               tod_pos >= 2))
    g5.append(('HA8', 'calibration', 'max group err %.4f, Brier %.6f vs'
               ' base %.6f' % (max(gerr), brier, brier0), ha8))
    g5.append(('HA9', 'C>0 in >=6/8 years', '%d of %d' % (yr_pos,
                                                          len(years)),
               yr_pos >= 6))
    g5.append(('HA10', 'C>0 after within-group 1%/5% trims',
               '%+0.3f / %+0.3f bp' % (tail_wg[0.01], tail_wg[0.05]),
               tail_pass))
    for k3, crit, val, ok in g5:
        print('  %-5s %-48s %-52s %s' % (k3, crit, val, PASS[ok]))
    npass = sum(1 for _, _, _, ok in g5 if ok)
    print('  HA PASSED %d / 10' % npass)

    print('\n' + '=' * 78)
    print('EXECUTION COMPLETE  (elapsed %.0f s)' % (time.time() - t0))
    print('H2 ONLY. H1 NOT USED. NO COMBINATION. NO STRATEGY SIMULATED.')
    print('DEVELOPMENT ONLY - NOT OOS, NOT PROSPECTIVE, NOT CONFIRMED.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
    print('=' * 78)


if __name__ == '__main__':
    main()
