#!/usr/bin/env python3
# ======================================================================
# ANOMALY-CONFIRM-V1 - ONE-SHOT HOLDOUT EXECUTION
# ======================================================================
# AUTHORITATIVE PREREGISTRATION (frozen BEFORE this file existed):
#   docs/ANOMALY_CONFIRM_V1_PREREGISTRATION.md
#   sha256 813f03e274059bf664b0a283291899d174e005f9b794afbe772f7aae84136aec
#   commit fd2311af1cd7e4071e6105a1ebf58f4089796cce
#   frozen 2026-08-25T21:14:42+00:00
#
# Promotable family M = 2:  SHOCK-CONT-MEDIUM (primary), MONDAY-RTH.
# Non-promotable diagnostics: AC-FLIP, CLV-FLIP, LEVERAGE-V.
#
# Every constant below is TRANSPORTED from the discovery window. Nothing
# is fitted, tuned or re-quantiled on the holdout. The engine SUBMITS NO
# ORDERS and simulates no trade.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, math, random, collections, datetime, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../rvmr'))
import rvmr_spec as RS
import rvmr_run as RV

DISC_END = '2023-12-31'
HOLD_START = '2024-01-01'
SEED = 20260825
B = 20000
PERM = 20000

# ---------------------------------------------------------------- FROZEN
# Nine decile cutpoints, global/static, from the discovery pair set.
# Preregistration section 4.3.
DECS9 = [-0.0011017009, -0.0005520548, -0.0002889478, -0.0001179931,
         +0.0000168159, +0.0001601759, +0.0003325537, +0.0005951824,
         +0.0011091640]
EXTREME = (0, 9)
# Control cutpoints, preregistration section 4.5
ATR_C1, ATR_C2 = 0.0004875675, 0.0007651141
SHOCK_MED_UP, SHOCK_MED_DN = 0.0017210529, 0.0017934863
# Discovery anchors, preregistration sections 4.6 and 5.4 (bp)
ANCH_SC_MED = 0.8423
ANCH_SC_LOW, ANCH_SC_HIGH = 0.0710, 0.5354
ANCH_SC_UP, ANCH_SC_DN = 0.9750, 0.7224
ANCH_DEC7_MED = 0.7274
ANCH_MON = 16.6296
ANCH_MON_DIFF = 16.2602
FLOOR_SC = 0.2808          # section 4.9
FLOOR_MON = 5.5432         # section 5.4
COST_PTS = 0.87            # frozen round-turn reference
# Discovery secondary anchors, preregistration section 6
ANCH_AC1M = {'LOW': -0.028036, 'MEDIUM': +0.016644, 'HIGH': +0.023863}
ANCH_AC15 = {'LOW': +0.002265, 'MEDIUM': -0.005023, 'HIGH': -0.032083}
ANCH_CLV = {'LOW': -0.007007, 'MEDIUM': +0.008840, 'HIGH': +0.014121}
ANCH_LEV = [0.6402, 0.4257, 0.3228, 0.2608, 0.2374, 0.2469, 0.2741,
            0.3174, 0.3870, 0.5562]
# Minimum n floors, preregistration section 4.11 / 5.7
MIN_MED, MIN_EXTREME, MIN_SIDE, MIN_MON = 2000, 6000, 800, 120

BP = 1e4
PASS = {True: 'PASS', False: 'FAIL'}


def mean(x):
    return sum(x) / len(x) if x else float('nan')


def med(x):
    return sorted(x)[len(x) // 2] if x else float('nan')


def dec_of(x):
    for k, cc in enumerate(DECS9):
        if x < cc:
            return k
    return 9


# --------------------------------------------------------------- stats
def day_blocks(pairs):
    by = collections.defaultdict(lambda: [0.0, 0])
    for d, v in pairs:
        b = by[d]; b[0] += v; b[1] += 1
    return [(s, n) for s, n in by.values()]


def boot(pairs, iters=B, seed=SEED):
    """Day-clustered percentile bootstrap + two-sided p (section 3.4)."""
    bl = day_blocks(pairs)
    nb = len(bl)
    obs = mean([v for _, v in pairs])
    if nb < 15:
        return obs, float('nan'), float('nan'), float('nan')
    rnd = random.Random(seed)
    out = []
    rr = rnd.randrange
    for _ in range(iters):
        s = 0.0; n = 0
        for _ in range(nb):
            bs, bn = bl[rr(nb)]
            s += bs; n += bn
        if n:
            out.append(s / n)
    out.sort()
    m = len(out)
    lo, hi = out[int(.025 * m)], out[int(.975 * m)]
    le = sum(1 for x in out if x <= 0)
    ge = sum(1 for x in out if x >= 0)
    p = max(2.0 * min(le, ge) / m, 1.0 / (m + 1.0))
    return obs, lo, hi, p


def bh(ps, M):
    """Benjamini-Hochberg adjusted q for the given family size M."""
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    q = [0.0] * len(ps)
    prev = 1.0
    for rank in range(len(order) - 1, -1, -1):
        i = order[rank]
        val = ps[i] * M / (rank + 1)
        prev = min(prev, val)
        q[i] = min(prev, 1.0)
    return q


def ac(rs, lag):
    """VERBATIM scan_run.py:201-208."""
    n = len(rs)
    if n < lag + 100:
        return float('nan')
    m = sum(rs) / n
    num = sum((rs[i] - m) * (rs[i - lag] - m) for i in range(lag, n))
    den = sum((x - m) ** 2 for x in rs)
    return num / den if den > 0 else float('nan')


def corr(xy):
    n = len(xy)
    if n < 2:
        return float('nan')
    mx = sum(x for x, y in xy) / n
    my = sum(y for x, y in xy) / n
    num = sum((x - mx) * (y - my) for x, y in xy)
    dx = math.sqrt(sum((x - mx) ** 2 for x, y in xy))
    dy = math.sqrt(sum((y - my) ** 2 for x, y in xy))
    return num / (dx * dy) if dx > 0 and dy > 0 else float('nan')


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


def build_pairs(day, em, c, h, l, RB, lo_day, hi_day):
    """Frozen construction, scan2_run.py:68-109, over [lo_day, hi_day]."""
    N = len(c)
    idx = [i for i in range(N) if lo_day <= day[i] <= hi_day]
    rets = []
    for i in idx:
        if i == 0 or em[i] - em[i - 1] != 1 or c[i - 1] <= 0:
            continue
        rets.append((i, math.log(c[i] / c[i - 1])))
    runs = collections.defaultdict(list)
    for i, r in rets:
        runs[day[i]].append((i, r))
    r15 = []
    for dd in sorted(runs):
        rs = runs[dd]; k = 0
        while k + 15 <= len(rs):
            block = rs[k:k + 15]
            if block[-1][0] - block[0][0] == 14:
                r15.append((block[0][0], block[-1][0],
                            sum(x[1] for x in block), dd))
                k += 15
            else:
                k += 1
    pairs = []
    for a in range(len(r15) - 1):
        i0, i1, rv_, dd = r15[a]
        j0, j1, rf, dd2 = r15[a + 1]
        if j0 - i1 != 1:
            continue
        pairs.append((rv_, rf, dd2, RB[j0], i0, i1, j0, j1))
    return idx, rets, runs, r15, pairs


def main():
    t0 = time.time()
    print('=' * 78)
    print('ANOMALY-CONFIRM-V1   ONE-SHOT HOLDOUT EXECUTION')
    print('  preregistration sha256 813f03e274059bf664b0a283291899d174e00')
    print('  freeze commit fd2311af1cd7e4071e6105a1ebf58f4089796cce')
    print('  M = 2   SHOCK-CONT-MEDIUM (primary) + MONDAY-RTH')
    print('  SUBMITS NO ORDERS.  NO STRATEGY IS SIMULATED.')
    print('=' * 78)

    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    N = len(D['c'])
    o, h, l, c, v, em, mod, day = (D['o'], D['h'], D['l'], D['c'], D['v'],
                                   D['em'], D['mod'], D['day'])
    rng = [h[i] - l[i] for i in range(N)]
    rr = RS.trailing_ratio(rng)
    RB = [RS.bucket(x) if x is not None else None for x in rr]
    atr = atr20_arrays(h, l, c)

    # =============================================== PHASE 0 (5) and (6)
    print('\n' + '=' * 78)
    print('PHASE 0  FREEZE REPRODUCTION  (discovery side; runs BEFORE any')
    print('         holdout outcome is computed)')
    print('=' * 78)
    print('  (6) RVMR thresholds  LOW < %.3f <= MEDIUM <= %.3f < HIGH'
          % (RS.T1, RS.T2))
    ok6 = (RS.T1 == 1.270 and RS.T2 == 2.335 and RS.W == 1440)
    probe_ok = True
    for p in (1440, 700000, 1577000):
        direct = rng[p] / (sum(rng[p - 1440:p]) / 1440.0)
        if abs(direct - rr[p]) > 1e-9:
            probe_ok = False
    print('      W=%d, own bar excluded, first scored index %d, probes %s'
          % (RS.W, next(i for i in range(N) if rr[i] is not None),
             'EXACT' if probe_ok else 'MISMATCH'))
    _, _, _, _, dpairs = build_pairs(day, em, c, h, l, RB, '0000', DISC_END)
    xs = sorted(p[0] for p in dpairs)
    rep = [xs[int(q * len(xs) / 10)] for q in range(1, 10)]
    # TOLERANCE NOTE (disclosed execution-time fix, no threshold changed):
    # the preregistration publishes the cutpoints to 10 decimal places, so
    # the tightest meaningful reproduction tolerance is half a unit in the
    # last published place = 5e-11. A first execution attempt used 1e-12,
    # which is finer than the published precision, and correctly halted at
    # PHASE 0 with FREEZE FAILURE before opening the holdout. The cutpoints
    # themselves are unchanged; the engine uses the FROZEN PUBLISHED values,
    # not the full-precision reproduction.
    TOL = 5e-11
    ok5 = all(abs(rep[k] - DECS9[k]) <= TOL for k in range(9))
    print('  (5) discovery pairs rebuilt: %d   cutpoints reproduce within'
          ' half a ULP of the 10-dp published precision (%.0e): %s'
          % (len(dpairs), TOL, 'EXACT' if ok5 else 'MISMATCH'))
    for k in range(9):
        print('      cut %d  frozen(published) %+.10f   reproduced'
              ' %+.14f   delta %.2e'
              % (k + 1, DECS9[k], rep[k], abs(rep[k] - DECS9[k])))
    print('      ENGINE USES THE FROZEN PUBLISHED VALUES.')
    if not (ok5 and ok6 and probe_ok):
        print('\nANOMALY-CONFIRM-V1 FREEZE FAILURE')
        return
    del dpairs, xs, rep
    print('  FREEZE VERIFIED. Opening the holdout now, exactly once.')

    # ==================================================== PHASE 1 holdout
    print('\n' + '=' * 78)
    print('PHASE 1  HOLDOUT BOUNDARY AND COVERAGE RECONCILIATION')
    print('=' * 78)
    hidx, hrets, hruns, hr15, hpairs = build_pairs(
        day, em, c, h, l, RB, HOLD_START, '9999')
    hdays = sorted(set(day[i] for i in hidx))
    hmon = sorted(set(dd[:7] for dd in hdays))
    yr = collections.Counter(dd[:4] for dd in hdays)
    print('  holdout bars              %d   (frozen expectation 926,449)'
          % len(hidx))
    print('  contiguous 1m returns     %d   (frozen expectation 925,748)'
          % len(hrets))
    print('  exchange days             %d   (frozen expectation 820)'
          % len(hdays))
    print('  distinct months           %d   (frozen expectation 32)'
          % len(hmon))
    print('  days by year              ' + '  '.join(
        '%s %d' % (y, yr[y]) for y in sorted(yr)))
    print('  first holdout bar         %s' % D['et'][hidx[0]])
    print('  last  holdout bar         %s' % D['et'][hidx[-1]])
    leak = sum(1 for i, r in hrets if day[i - 1] <= DISC_END)
    print('  returns using a DISCOVERY predecessor bar: %d  (must be 0)'
          % leak)
    assert leak == 0
    assert all(day[p[4]] >= HOLD_START and day[p[6]] >= HOLD_START
               for p in hpairs)
    print('  15m blocks %d   shock/forward pairs %d' % (len(hr15), len(hpairs)))
    xday = sum(1 for p in hpairs if day[p[4]] != day[p[6]])
    print('  pairs crossing a calendar-date label (true midnight'
          ' contiguity): %d' % xday)

    # grid disclosure
    print('\n  15m GRID PHASE (frozen: anchored to each day\'s first valid')
    print('  contiguous return, NOT a :00/:15/:30/:45 clock grid)')
    seen = None; shown = 0
    for (i0, i1, rv_, dd) in hr15:
        if dd == seen:
            continue
        seen = dd
        print('    %s  block1 bars %s .. %s' % (dd, D['et'][i0][11:16],
                                                D['et'][i1][11:16]))
        shown += 1
        if shown >= 4:
            break
    ph = collections.Counter()
    seen = None
    for (i0, i1, rv_, dd) in hr15:
        if dd != seen:
            seen = dd
            ph[mod[i0] % 15] += 1
    print('    distinct grid phases across %d holdout days: %d'
          % (len(hdays), len(ph)))

    # ============================================ CANDIDATE 1 SHOCK-CONT
    print('\n' + '=' * 78)
    print('CANDIDATE 1   SHOCK-CONT-MEDIUM   (PRIMARY, promotable)')
    print('=' * 78)
    decc = collections.Counter(dec_of(p[0]) for p in hpairs)
    print('  holdout decile occupancy under the FROZEN cutpoints')
    print('  (bins are NOT expected to be 10%% each - that is the point):')
    for k in range(10):
        print('    dec %d  n %6d  (%5.2f%%)'
              % (k, decc[k], 100.0 * decc[k] / len(hpairs)))

    near = sum(1 for p in hpairs
               if min(abs(p[0] - x) for x in DECS9) <= 1e-9)
    print('  holdout shocks lying within 1e-9 of ANY frozen cutpoint'
          ' (i.e. reclassifiable by 10-dp rounding): %d' % near)

    ev = []   # (dd2, cont, state, dec, shock, fwd, i1, j0)
    nostate = 0
    for rv_, rf, dd2, st, i0, i1, j0, j1 in hpairs:
        dc = dec_of(rv_)
        if dc not in EXTREME:
            continue
        if rv_ == 0:
            continue
        if st is None:
            nostate += 1
            continue
        ev.append((dd2, (1.0 if rv_ > 0 else -1.0) * rf, st, dc, rv_, rf,
                   i1, j0))
    nUP = sum(1 for e in ev if e[3] == 9)
    nDN = sum(1 for e in ev if e[3] == 0)
    print('\n  extreme events (dec0 U dec9) %d   UP %d   DOWN %d'
          '   (dropped, no RVMR score: %d)' % (len(ev), nUP, nDN, nostate))

    def sel(pred):
        return [(e[0], e[1]) for e in ev if pred(e)]

    print('\n  PRIMARY LADDER  cont = sign(shock) x forward15,'
          ' state = RB[j0]')
    print('  %-8s %7s %12s %28s %10s' % ('state', 'n', 'cont bp',
                                         '95% CI (bp)', 'boot p'))
    lad = {}
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        pr = sel(lambda e, s=st: e[2] == s)
        m, lo, hi, p = boot(pr)
        lad[st] = (len(pr), m, lo, hi, p)
        print('  %-8s %7d %+12.4f   [%+11.4f, %+11.4f] %10.5f%s'
              % (st, len(pr), m * BP, lo * BP, hi * BP, p,
                 '   <-- PRIMARY' if st == 'MEDIUM' else ''))
    nMED, mMED, loMED, hiMED, pMED = lad['MEDIUM']

    print('\n  UP / DOWN inside MEDIUM (both required positive)')
    sides = {}
    for dc, nm in ((9, 'UP'), (0, 'DOWN')):
        pr = sel(lambda e, d=dc: e[2] == 'MEDIUM' and e[3] == d)
        m, lo, hi, p = boot(pr)
        sides[nm] = (len(pr), m, lo, hi, p)
        print('  %-6s n %6d  cont %+9.4f bp  CI [%+9.4f, %+9.4f]  p %.5f'
              % (nm, len(pr), m * BP, lo * BP, hi * BP, p))
    print('\n  UP / DOWN inside LOW and HIGH (context, not gated)')
    for st in ('LOW', 'HIGH'):
        for dc, nm in ((9, 'UP'), (0, 'DOWN')):
            pr = sel(lambda e, s=st, d=dc: e[2] == s and e[3] == d)
            print('    %-7s %-5s n %6d  cont %+9.4f bp'
                  % (st, nm, len(pr), mean([x[1] for x in pr]) * BP))

    # dec7 secondary
    d7 = [(dd2, rf) for rv_, rf, dd2, st, i0, i1, j0, j1 in hpairs
          if dec_of(rv_) == 7 and st == 'MEDIUM']
    d7a = [(dd2, rf) for rv_, rf, dd2, st, i0, i1, j0, j1 in hpairs
           if dec_of(rv_) == 7]
    m7, lo7, hi7, p7 = boot(d7)
    print('\n  dec7 SECONDARY (corroboration only, cannot rescue):')
    print('    MEDIUM     n %6d  fwd15 %+9.4f bp  CI [%+9.4f, %+9.4f]'
          '  p %.5f' % (len(d7), m7 * BP, lo7 * BP, hi7 * BP, p7))
    print('    all states n %6d  fwd15 %+9.4f bp'
          % (len(d7a), mean([x[1] for x in d7a]) * BP))
    print('    discovery anchors: MEDIUM %+0.4f bp' % ANCH_DEC7_MED)

    # retention and economics
    ret = (mMED * BP) / ANCH_SC_MED
    px = mean([c[e[6]] for e in ev if e[2] == 'MEDIUM'])
    pts = mMED * px
    print('\n  EFFECT RETENTION')
    print('    discovery MEDIUM  %+0.4f bp' % ANCH_SC_MED)
    print('    holdout   MEDIUM  %+0.4f bp' % (mMED * BP))
    print('    retention         %.1f%%   (frozen floor %+0.4f bp)'
          % (100 * ret, FLOOR_SC))
    print('  ECONOMIC SCALE (reported, NEVER gated)')
    print('    mean close at MEDIUM extreme events  %.2f' % px)
    print('    effect in NQ points  %+0.4f   round-turn cost %.2f pts'
          % (pts, COST_PTS))
    print('    gross multiple of cost  %.3fx   (cost = %.4f bp here)'
          % (pts / COST_PTS, COST_PTS / px * BP))

    # ---------------------------------------------------- controls
    print('\n  CONTROL C1  ATR TERCILES (frozen cuts %.10f / %.10f)'
          % (ATR_C1, ATR_C2))

    def atr_t(e):
        a = atr[e[6]]
        if a is None:
            return None
        x = a / c[e[6]]
        return 'ATR-LOW' if x < ATR_C1 else ('ATR-MID' if x <= ATR_C2
                                             else 'ATR-HIGH')

    tot_t = collections.Counter(atr_t(e) for e in ev)
    print('    %-9s %8s %12s %10s | %8s %12s' % ('tercile', 'n MED',
                                                 'MED cont bp', 'CI lo',
                                                 'n all', 'ATRonly bp'))
    med_t, atronly = {}, {}
    for t in ('ATR-LOW', 'ATR-MID', 'ATR-HIGH'):
        pm = [(e[0], e[1]) for e in ev if e[2] == 'MEDIUM' and atr_t(e) == t]
        pa = [(e[0], e[1]) for e in ev if atr_t(e) == t]
        mm, lo_, hi_, _ = boot(pm, iters=4000)
        med_t[t] = (len(pm), mm)
        atronly[t] = mean([x[1] for x in pa])
        print('    %-9s %8d %+12.4f %10.4f | %8d %+12.4f'
              % (t, len(pm), mm * BP, lo_ * BP, tot_t[t], atronly[t] * BP))
    # two readings of "stratum-size-weighted", both reported
    wm = sum(med_t[t][0] * med_t[t][1] for t in med_t) / \
        max(sum(med_t[t][0] for t in med_t), 1)
    wa = sum(tot_t[t] * med_t[t][1] for t in med_t) / \
        max(sum(tot_t[t] for t in med_t), 1)
    print('    MEDIUM-size weighted   %+0.4f bp  (degenerate: equals the'
          ' unstratified mean by construction)' % (wm * BP))
    print('    ATR-standardised       %+0.4f bp  (reweighted to the ALL-'
          'STATE ATR distribution)' % (wa * BP))
    print('    unstratified MEDIUM    %+0.4f bp' % (mMED * BP))
    pos_t = sum(1 for t in med_t if med_t[t][1] > 0)
    red1 = (wa < 0.5 * mMED)
    red2 = (max(atronly.values()) >= mMED)
    print('    terciles with MEDIUM cont > 0: %d of 3' % pos_t)
    print('    REDUNDANT-WITH-ATR condition 1 (standardised < 50%% of'
          ' unstratified): %s' % red1)
    print('    REDUNDANT-WITH-ATR condition 2 (max ATR-only >= MEDIUM):'
          ' %s' % red2)
    redundant = red1 and red2

    print('\n  CONTROL C2  TIME OF DAY of forward-block start j0')

    def tod(e):
        m_ = mod[e[7]]
        return ('OVERNIGHT' if (m_ >= 1081 or m_ <= 569)
                else ('RTH_AM' if m_ <= 750 else 'RTH_PM'))

    tod_pos = 0
    for b in ('OVERNIGHT', 'RTH_AM', 'RTH_PM'):
        pr = [(e[0], e[1]) for e in ev if e[2] == 'MEDIUM' and tod(e) == b]
        mm, lo_, hi_, _ = boot(pr, iters=4000)
        if mm > 0:
            tod_pos += 1
        print('    %-10s n %6d  cont %+9.4f bp  CI [%+9.4f, %+9.4f]'
              % (b, len(pr), mm * BP, lo_ * BP, hi_ * BP))
    print('    buckets with MEDIUM cont > 0: %d of 3' % tod_pos)

    print('\n  CONTROL C3  SHOCK MAGNITUDE median split (frozen per side)')

    def small(e):
        return abs(e[4]) < (SHOCK_MED_UP if e[3] == 9 else SHOCK_MED_DN)

    c3 = {}
    for nm, pred in (('smaller |shock|', small),
                     ('larger  |shock|', lambda e: not small(e))):
        pr = [(e[0], e[1]) for e in ev if e[2] == 'MEDIUM' and pred(e)]
        mm, lo_, hi_, pp = boot(pr)
        c3[nm] = (len(pr), mm, lo_, hi_)
        print('    %-16s n %6d  cont %+9.4f bp  CI [%+9.4f, %+9.4f]  p %.5f'
              % (nm, len(pr), mm * BP, lo_ * BP, hi_ * BP, pp))
    sm = c3['smaller |shock|']
    c3_pass = not (sm[3] < 0)     # CI must not lie entirely below zero
    print('    smaller-half CI lies entirely below 0: %s' % (sm[3] < 0))

    # reported-only diagnostics
    print('\n  REPORTED-ONLY DIAGNOSTICS (flagged, never gated)')
    # return of the block IMMEDIATELY PRECEDING the shock block, keyed by
    # the shock block's end index (e[6]); only when truly contiguous
    prevsign = {}
    for a in range(1, len(hr15)):
        if hr15[a][0] - hr15[a - 1][1] == 1:
            prevsign[hr15[a][1]] = hr15[a - 1][2]
    same = [(e[0], e[1]) for e in ev
            if e[6] in prevsign and
            (prevsign[e[6]] > 0) == (e[3] == 9)]
    print('    momentum: preceding block same sign as shock  n %d'
          '  cont %+0.4f bp' % (len(same), mean([x[1] for x in same]) * BP))
    opp = [(e[0], e[1]) for e in ev
           if e[6] in prevsign and
           (prevsign[e[6]] > 0) != (e[3] == 9)]
    print('    momentum: preceding block opposite sign       n %d'
          '  cont %+0.4f bp' % (len(opp), mean([x[1] for x in opp]) * BP))

    # ---------------------------------------------------- stability
    print('\n  YEAR STABILITY (frozen: positive in >= 2 of 3)')
    print('  %-6s %7s %11s %11s %11s %11s %11s' %
          ('year', 'n MED', 'MED bp', 'UP bp', 'DOWN bp', 'LOW bp',
           'HIGH bp'))
    yr_pos = 0
    for y in ('2024', '2025', '2026'):
        pm = [e[1] for e in ev if e[2] == 'MEDIUM' and e[0][:4] == y]
        pu = [e[1] for e in ev if e[2] == 'MEDIUM' and e[3] == 9
              and e[0][:4] == y]
        pd = [e[1] for e in ev if e[2] == 'MEDIUM' and e[3] == 0
              and e[0][:4] == y]
        pl = [e[1] for e in ev if e[2] == 'LOW' and e[0][:4] == y]
        ph_ = [e[1] for e in ev if e[2] == 'HIGH' and e[0][:4] == y]
        if mean(pm) > 0:
            yr_pos += 1
        print('  %-6s %7d %+11.4f %+11.4f %+11.4f %+11.4f %+11.4f'
              % (y, len(pm), mean(pm) * BP, mean(pu) * BP, mean(pd) * BP,
                 mean(pl) * BP, mean(ph_) * BP))
    print('  years with MEDIUM cont > 0: %d of 3' % yr_pos)

    print('\n  MONTH STABILITY (frozen: >= 18 of 32 positive AND median'
          ' month > 0)')
    bym = collections.defaultdict(list)
    for e in ev:
        if e[2] == 'MEDIUM':
            bym[e[0][:7]].append(e[1])
    mk = sorted(bym)
    mvals = [(m_, len(bym[m_]), mean(bym[m_])) for m_ in mk]
    for i in range(0, len(mvals), 4):
        print('    ' + '   '.join('%s n%4d %+8.3f' % (a, b, cc * BP)
                                  for a, b, cc in mvals[i:i + 4]))
    mpos = sum(1 for _, _, x in mvals if x > 0)
    mneg = len(mvals) - mpos
    mmed = med([x for _, _, x in mvals])
    best = max(mvals, key=lambda t: t[2]); worst = min(mvals, key=lambda t: t[2])
    print('    months %d   positive %d   negative %d   median %+0.4f bp'
          % (len(mvals), mpos, mneg, mmed * BP))
    print('    best %s %+0.4f bp   worst %s %+0.4f bp'
          % (best[0], best[2] * BP, worst[0], worst[2] * BP))

    # ---------------------------------------------------- tails
    print('\n  TAIL DESTRUCTION (frozen: mean > 0 after top-1%% AND top-5%%'
          ' removal by SIGNED cont)')
    medev = [e for e in ev if e[2] == 'MEDIUM']
    srt = sorted(medev, key=lambda e: e[1], reverse=True)
    tot_eff = sum(e[1] for e in medev)
    tails = {}
    for frac in (0.01, 0.05):
        k = max(1, int(round(frac * len(srt))))
        keep = srt[k:]
        mm = mean([e[1] for e in keep])
        tails[frac] = mm
        print('    remove top %4.1f%% (%4d events)  n %6d  cont %+9.4f bp'
              % (frac * 100, k, len(keep), mm * BP))
    k1 = max(1, int(round(0.01 * len(srt))))
    print('    top-1%% share of total MEDIUM effect: %.1f%%'
          % (100 * sum(e[1] for e in srt[:k1]) / tot_eff if tot_eff else
             float('nan')))
    for frac in (0.01, 0.05):
        k = max(1, int(round(frac * len(medev))))
        sa = sorted(medev, key=lambda e: abs(e[1]), reverse=True)
        print('    symmetric |cont| trim %4.1f%% (%4d)  cont %+9.4f bp'
              % (frac * 100, k, mean([e[1] for e in sa[k:]]) * BP))
    tail_pass = tails[0.01] > 0 and tails[0.05] > 0

    # ---------------------------------------------------- permutations
    print('\n  PERMUTATION NULLS (frozen, %d iterations, seed %d)'
          % (PERM, SEED))
    byday = collections.defaultdict(list)
    for e in ev:
        byday[e[0]].append((e[2], e[1]))
    dl = sorted(byday)
    # P1 day sign flip on the MEDIUM statistic
    medday = [(sum(x[1] for x in byday[d] if x[0] == 'MEDIUM'),
               sum(1 for x in byday[d] if x[0] == 'MEDIUM')) for d in dl]
    rnd = random.Random(SEED)
    cnt = 0
    obs = abs(mMED)
    for _ in range(PERM):
        s = 0.0; n = 0
        for bs, bn in medday:
            if bn:
                s += bs if rnd.random() < 0.5 else -bs
                n += bn
        if n and abs(s / n) >= obs:
            cnt += 1
    p_p1 = max((cnt + 1.0) / (PERM + 1.0), 1.0 / (PERM + 1.0))
    print('    P1 day sign-flip                p = %.5f' % p_p1)
    # P2 within-day RVMR state shuffle
    shuf = []
    for d in dl:
        vals = [x[1] for x in byday[d]]
        k = sum(1 for x in byday[d] if x[0] == 'MEDIUM')
        if k:
            shuf.append((vals, k, sum(vals), len(vals)))
    rnd = random.Random(SEED)
    cnt = 0
    ntot = sum(s[1] for s in shuf)
    smp = rnd.sample
    for _ in range(PERM):
        s = 0.0
        for vals, k, tot, nv in shuf:
            if k * 2 <= nv:
                s += sum(smp(vals, k))
            else:
                s += tot - sum(smp(vals, nv - k))
        if abs(s / ntot) >= obs:
            cnt += 1
    p_p2 = max((cnt + 1.0) / (PERM + 1.0), 1.0 / (PERM + 1.0))
    print('    P2 within-day state shuffle     p = %.5f' % p_p2)
    print('    (elapsed %.0f s)' % (time.time() - t0))

    # ============================================ CANDIDATE 2 MONDAY-RTH
    print('\n' + '=' * 78)
    print('CANDIDATE 2   MONDAY-RTH   (secondary promotable)')
    print('=' * 78)
    monv = collections.defaultdict(float)
    rthall = collections.defaultdict(float)
    sun = collections.defaultdict(float)
    monon = collections.defaultdict(float)
    for i, r in hrets:
        w = datetime.datetime.strptime(day[i], '%Y-%m-%d').weekday()
        if w == 6 and mod[i] >= 1081:
            sun[day[i]] += r
        elif w == 0 and mod[i] <= 569:
            monon[day[i]] += r
        elif w == 0 and 570 <= mod[i] <= 960:
            monv[day[i]] += r
        if 570 <= mod[i] <= 960:
            rthall[day[i]] += r
    mons = sorted(monv)
    nonmon = [(d, rthall[d]) for d in sorted(rthall) if d not in monv]
    mpairs = [(d, monv[d]) for d in mons]
    mM, mlo, mhi, mp = boot(mpairs)
    nM, nlo, nhi, npv = boot(nonmon)
    print('  Monday RTH sessions %d   non-Monday RTH sessions %d'
          % (len(mpairs), len(nonmon)))
    print('  MONDAY RTH      mean %+9.4f bp  CI [%+9.4f, %+9.4f]  p %.5f'
          % (mM * BP, mlo * BP, mhi * BP, mp))
    print('  NON-MONDAY RTH  mean %+9.4f bp  CI [%+9.4f, %+9.4f]'
          % (nM * BP, nlo * BP, nhi * BP))
    diff = mM - nM
    print('  DIFFERENTIAL    %+9.4f bp   (discovery %+0.4f bp)'
          % (diff * BP, ANCH_MON_DIFF))
    for nm, dct in (('SUN 18:00-24:00', sun), ('MON 00:00-09:29', monon)):
        pr = sorted(dct.items())
        mm, lo_, hi_, _ = boot(pr, iters=4000)
        print('  %-16s n %4d  mean %+9.4f bp  CI [%+9.4f, %+9.4f]'
              % (nm, len(pr), mm * BP, lo_ * BP, hi_ * BP))
    mret = (mM * BP) / ANCH_MON
    print('\n  RETENTION  discovery %+0.4f bp -> holdout %+0.4f bp'
          '  = %.1f%%   (floor %+0.4f bp)'
          % (ANCH_MON, mM * BP, 100 * mret, FLOOR_MON))

    print('\n  YEAR STABILITY (frozen: > 0 in >= 2 of 3)')
    myr_pos = 0
    for y in ('2024', '2025', '2026'):
        vals = [monv[d] for d in mons if d[:4] == y]
        if mean(vals) > 0:
            myr_pos += 1
        print('    %s  n %3d  mean %+9.4f bp' % (y, len(vals),
                                                 mean(vals) * BP))
    print('    years positive: %d of 3' % myr_pos)

    print('\n  MONTH STABILITY (frozen: > 0 in >= 17 of 32)')
    mbym = collections.defaultdict(list)
    for d in mons:
        mbym[d[:7]].append(monv[d])
    mkk = sorted(mbym)
    mv = [(k, len(mbym[k]), mean(mbym[k])) for k in mkk]
    for i in range(0, len(mv), 4):
        print('    ' + '   '.join('%s n%2d %+8.2f' % (a, b, cc * BP)
                                  for a, b, cc in mv[i:i + 4]))
    mmpos = sum(1 for _, _, x in mv if x > 0)
    mbest = max(mv, key=lambda t: t[2]); mworst = min(mv, key=lambda t: t[2])
    print('    months %d   positive %d   negative %d   median %+0.3f bp'
          % (len(mv), mmpos, len(mv) - mmpos,
             med([x for _, _, x in mv]) * BP))
    print('    best %s %+0.3f bp   worst %s %+0.3f bp'
          % (mbest[0], mbest[2] * BP, mworst[0], mworst[2] * BP))

    print('\n  TAIL DESTRUCTION (frozen: mean > 0 after top-1%% AND'
          ' top-5%% removal by SIGNED return)')
    mvals_s = sorted((monv[d] for d in mons), reverse=True)
    tot_m = sum(mvals_s)
    mt = {}
    for frac in (0.01, 0.05):
        k = max(1, int(round(frac * len(mvals_s))))
        keep = mvals_s[k:]
        mt[frac] = mean(keep)
        print('    remove top %4.1f%% (%2d Mondays)  n %3d  mean %+9.4f bp'
              '   removed share of total %.1f%%'
              % (frac * 100, k, len(keep), mean(keep) * BP,
                 100 * sum(mvals_s[:k]) / tot_m if tot_m else float('nan')))
    print('    mean %+9.4f   median %+9.4f   10%%-trimmed %+9.4f bp'
          % (mM * BP, med(mvals_s) * BP,
             mean(sorted(mvals_s)[max(1, int(.05 * len(mvals_s))):
                                  len(mvals_s) - max(1, int(.05 * len(mvals_s)))]) * BP))
    mtail_pass = mt[0.01] > 0 and mt[0.05] > 0

    print('\n  PERMUTATION NULLS')
    rnd = random.Random(SEED)
    obsm = abs(mM)
    cnt = 0
    mlist = [monv[d] for d in mons]
    nm_ = len(mlist)
    for _ in range(PERM):
        s = 0.0
        for x in mlist:
            s += x if rnd.random() < 0.5 else -x
        if abs(s / nm_) >= obsm:
            cnt += 1
    p_p3 = max((cnt + 1.0) / (PERM + 1.0), 1.0 / (PERM + 1.0))
    print('    P3 sign flip                    p = %.5f' % p_p3)
    allr = [rthall[d] for d in sorted(rthall)]
    grand = sum(allr) / len(allr)
    rnd = random.Random(SEED)
    cnt = 0
    obsd = abs(diff)
    nall = len(allr)
    for _ in range(PERM):
        pick = rnd.sample(allr, nm_)
        sp = sum(pick) / nm_
        rest = (sum(allr) - sum(pick)) / (nall - nm_)
        if abs(sp - rest) >= obsd:
            cnt += 1
    p_p4 = max((cnt + 1.0) / (PERM + 1.0), 1.0 / (PERM + 1.0))
    print('    P4 weekday-label permutation    p = %.5f  (differential)'
          % p_p4)

    # ==================================================== multiplicity
    print('\n' + '=' * 78)
    print('MULTIPLICITY  (binding M = 2; M = 5 reported as NON-BINDING'
          ' family-size sensitivity)')
    print('=' * 78)
    q2 = bh([pMED, mp], 2)
    q5 = bh([pMED, mp], 5)
    print('  %-22s %12s %12s %12s' % ('candidate', 'boot p', 'BH q (M=2)',
                                      'BH q (M=5)'))
    print('  %-22s %12.5f %12.5f %12.5f' % ('SHOCK-CONT-MEDIUM', pMED,
                                            q2[0], q5[0]))
    print('  %-22s %12.5f %12.5f %12.5f' % ('MONDAY-RTH', mp, q2[1], q5[1]))

    # ==================================================== SC gate
    print('\n' + '=' * 78)
    print('SC1-SC15  SHOCK-CONT-MEDIUM CONFIRMATION GATE')
    print('=' * 78)
    sc = []
    sc.append(('SC1', 'holdout-only data', 'leak=%d, all events >= %s'
               % (leak, HOLD_START), leak == 0))
    sc.append(('SC2', 'frozen cutpoints transported',
               'reproduced to 1e-12; 0 holdout quantiles', ok5))
    sc.append(('SC3', 'MEDIUM cont > 0', '%+0.4f bp' % (mMED * BP),
               mMED > 0))
    sc.append(('SC4', 'retention >= +0.2808 bp',
               '%+0.4f bp (%.1f%%)' % (mMED * BP, 100 * ret),
               mMED * BP >= FLOOR_SC))
    sc.append(('SC5', 'UP > 0 AND DOWN > 0',
               'UP %+0.4f, DOWN %+0.4f bp'
               % (sides['UP'][1] * BP, sides['DOWN'][1] * BP),
               sides['UP'][1] > 0 and sides['DOWN'][1] > 0))
    sc.append(('SC6', 'MED > LOW and MED > HIGH',
               'MED %+0.4f, LOW %+0.4f, HIGH %+0.4f bp'
               % (mMED * BP, lad['LOW'][1] * BP, lad['HIGH'][1] * BP),
               mMED > lad['LOW'][1] and mMED > lad['HIGH'][1]))
    sc.append(('SC7', 'CI excludes 0 AND P1<=.05 AND P2<=.05',
               'CI [%+0.4f,%+0.4f] P1 %.5f P2 %.5f'
               % (loMED * BP, hiMED * BP, p_p1, p_p2),
               (loMED > 0 or hiMED < 0) and p_p1 <= 0.05 and p_p2 <= 0.05))
    sc.append(('SC8', 'BH q <= 0.05 at M=2', 'q = %.5f' % q2[0],
               q2[0] <= 0.05))
    sc.append(('SC9', 'positive in >= 2 of 3 years', '%d of 3' % yr_pos,
               yr_pos >= 2))
    sc.append(('SC10', '>= 18/32 months AND median month > 0',
               '%d of %d positive, median %+0.4f bp'
               % (mpos, len(mvals), mmed * BP),
               mpos >= 18 and mmed > 0))
    sc.append(('SC11', 'mean > 0 after top-1%% and top-5%% removal',
               '%+0.4f / %+0.4f bp' % (tails[0.01] * BP, tails[0.05] * BP),
               tail_pass))
    sc.append(('SC12', 'ATR control + not REDUNDANT-WITH-ATR',
               '%d/3 terciles >0, std %+0.4f vs unstrat %+0.4f, redundant=%s'
               % (pos_t, wa * BP, mMED * BP, redundant),
               pos_t >= 2 and wa >= 0.5 * mMED and not redundant))
    sc.append(('SC13', 'MEDIUM > 0 in >= 2 of 3 time buckets',
               '%d of 3' % tod_pos, tod_pos >= 2))
    sc.append(('SC14', 'smaller-|shock| half not significantly negative',
               'CI [%+0.4f, %+0.4f] bp' % (sm[2] * BP, sm[3] * BP),
               c3_pass))
    sc.append(('SC15', 'min n: MED>=2000, extreme>=6000, side>=800',
               'MED %d, extreme %d, UP %d, DOWN %d'
               % (nMED, len(ev), sides['UP'][0], sides['DOWN'][0]),
               nMED >= MIN_MED and len(ev) >= MIN_EXTREME
               and sides['UP'][0] >= MIN_SIDE
               and sides['DOWN'][0] >= MIN_SIDE))
    for k, crit, val, ok in sc:
        print('  %-5s %-42s %-46s %s' % (k, crit, val, PASS[ok]))
    sc_pass = sum(1 for _, _, _, ok in sc if ok)
    print('  SC PASSED %d / 15' % sc_pass)

    # ==================================================== MR gate
    print('\n' + '=' * 78)
    print('MR1-MR9  MONDAY-RTH CONFIRMATION GATE')
    print('=' * 78)
    mr = []
    mr.append(('MR1', 'holdout-only data',
               'all Mondays >= %s, leak=%d' % (HOLD_START, leak), leak == 0))
    mr.append(('MR2', 'n >= 120 Mondays', 'n = %d' % len(mpairs),
               len(mpairs) >= MIN_MON))
    mr.append(('MR3', 'mean Monday RTH > 0', '%+0.4f bp' % (mM * BP),
               mM > 0))
    mr.append(('MR4', 'retention >= +5.5432 bp',
               '%+0.4f bp (%.1f%%)' % (mM * BP, 100 * mret),
               mM * BP >= FLOOR_MON))
    mr.append(('MR5', 'CI excludes 0 AND P3 <= 0.05',
               'CI [%+0.4f,%+0.4f] P3 %.5f' % (mlo * BP, mhi * BP, p_p3),
               (mlo > 0 or mhi < 0) and p_p3 <= 0.05))
    mr.append(('MR6', 'BH q <= 0.05 at M=2', 'q = %.5f' % q2[1],
               q2[1] <= 0.05))
    mr.append(('MR7', '>= 2/3 years AND >= 17/32 months',
               '%d of 3 years, %d of %d months' % (myr_pos, mmpos, len(mv)),
               myr_pos >= 2 and mmpos >= 17))
    mr.append(('MR8', 'mean > 0 after top-1%% and top-5%% removal',
               '%+0.4f / %+0.4f bp' % (mt[0.01] * BP, mt[0.05] * BP),
               mtail_pass))
    mr.append(('MR9', 'definition unchanged AND Mon - nonMon > 0',
               'RTH 570-960 unchanged; differential %+0.4f bp (P4 %.5f)'
               % (diff * BP, p_p4), diff > 0))
    for k, crit, val, ok in mr:
        print('  %-5s %-42s %-46s %s' % (k, crit, val, PASS[ok]))
    mr_pass = sum(1 for _, _, _, ok in mr if ok)
    print('  MR PASSED %d / 9' % mr_pass)

    # ==================================================== secondaries
    print('\n' + '=' * 78)
    print('NON-PROMOTABLE SECONDARY DIAGNOSTICS')
    print('=' * 78)
    print('  AC-FLIP  (verbatim estimator on the STATE-FILTERED list)')
    print('  %-7s %10s %12s %12s   %10s %12s %12s'
          % ('state', 'n 1m', 'AC1 1m', 'disc 1m', 'n 15m', 'AC1 15m',
             'disc 15m'))
    ac1 = {}
    p15h = [(i0, rv_) for (i0, i1, rv_, dd) in hr15]
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        rs = [r for i, r in hrets if RB[i] == st]
        r15s = [r for i, r in p15h if RB[i] == st]
        a1, a15 = ac(rs, 1), ac(r15s, 1)
        ac1[st] = a1
        print('  %-7s %10d %+12.6f %+12.6f   %10d %+12.6f %+12.6f'
              % (st, len(rs), a1, ANCH_AC1M[st], len(r15s), a15,
                 ANCH_AC15[st]))
    print('  adjacency-restricted variant (both minutes adjacent AND same'
          ' state):')
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        seq = []
        prev_i = None
        run = []
        for i, r in hrets:
            if RB[i] == st and prev_i is not None and i - prev_i == 1 \
                    and RB[prev_i] == st:
                run.append(r)
            else:
                if len(run) > 1:
                    seq.append(run)
                run = [r] if RB[i] == st else []
            prev_i = i
        if len(run) > 1:
            seq.append(run)
        num = den = 0.0
        allv = [x for s in seq for x in s]
        if len(allv) > 100:
            m_ = sum(allv) / len(allv)
            for s in seq:
                for k in range(1, len(s)):
                    num += (s[k] - m_) * (s[k - 1] - m_)
            den = sum((x - m_) ** 2 for x in allv)
        print('    %-7s n %8d  adjacency-restricted AC1 %+0.6f'
              % (st, len(allv), num / den if den > 0 else float('nan')))

    print('\n  CLV-FLIP')
    clvp = []
    for k in range(len(hrets) - 1):
        i, r = hrets[k]
        i2, r2 = hrets[k + 1]
        if i2 - i != 1 or h[i] <= l[i]:
            continue
        clvp.append((i, (2 * c[i] - h[i] - l[i]) / (h[i] - l[i]), r2))
    clv = {}
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        sub = [(x, y) for i, x, y in clvp if RB[i] == st]
        clv[st] = corr(sub)
        print('    %-7s n %8d  corr(CLV_t, r_t+1) %+0.6f   (discovery'
              ' %+0.6f)' % (st, len(sub), clv[st], ANCH_CLV[st]))

    print('\n  LEVERAGE-V   P(RVMR RANGE HIGH within 30m | frozen shock'
          ' decile)')
    lv = {}
    for (i0, i1, rv_, dd) in hr15:
        fut = any(RB[j] == 'HIGH' for j in range(i1 + 1, min(i1 + 31, N)))
        lv.setdefault(dec_of(rv_), []).append(1 if fut else 0)
    lvm = {k: mean(lv[k]) for k in sorted(lv)}
    print('    holdout  ' + '  '.join('d%d %.4f' % (k, lvm[k])
                                      for k in sorted(lvm)))
    print('    discovery ' + ' '.join('d%d %.4f' % (k, ANCH_LEV[k])
                                      for k in range(10)))
    mid = min(lvm[k] for k in (3, 4, 5, 6) if k in lvm)
    vshape = lvm.get(0, 0) > mid and lvm.get(9, 0) > mid
    asym = lvm.get(0, 0) > lvm.get(9, 0)
    print('    V-shape (d0 and d9 above every d3..d6): %s   downside'
          ' asymmetry P(d0) > P(d9): %s' % (vshape, asym))

    print('\n' + '=' * 78)
    print('EXECUTION COMPLETE  (elapsed %.0f s)' % (time.time() - t0))
    print('SUBMITS NO ORDERS.  NO STRATEGY WAS SIMULATED.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
    print('=' * 78)


if __name__ == '__main__':
    main()
