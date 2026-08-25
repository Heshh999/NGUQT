#!/usr/bin/env python3
# ======================================================================
# ANOMALY-CONFIRM-V1 - DISCOVERY-SIDE FREEZE CONSTANTS
# ======================================================================
# This program computes the constants that must TRANSPORT UNCHANGED into
# the 2024-2026 holdout confirmation: decile cutpoints, control
# cutpoints, and the discovery-window effect anchors against which
# retention thresholds are written.
#
# IT READS THE DISCOVERY WINDOW ONLY (day <= 2023-12-31) FOR EVERY
# OUTCOME. A hard assertion enforces this. No candidate outcome for
# 2024+ is computed anywhere in this file.
#
# Definitions are lifted verbatim from the frozen discovery sources:
#   analysis/anomaly/scan_run.py    (Wave 1)
#   analysis/anomaly/scan2_run.py   (Wave 2)
#   analysis/rvmr/rvmr_spec.py      (frozen RVMR-V1)
# SUBMITS NO ORDERS. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, math, random, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../rvmr'))
import rvmr_spec as RS
import rvmr_run as RV

DISC_END = '2023-12-31'
HOLD_START = '2024-01-01'
SEED = 20260825
B_MAIN = 20000


def mean(x):
    return sum(x) / len(x) if x else float('nan')


def med(x):
    return sorted(x)[len(x) // 2] if x else float('nan')


def day_boot(pairs, iters, seed=SEED):
    """Day-clustered percentile bootstrap. pairs: [(dayKey, value)]."""
    by = collections.defaultdict(list)
    for d, v in pairs:
        by[d].append(v)
    ds = sorted(by)
    if len(ds) < 15:
        return mean([v for _, v in pairs]), (float('nan'), float('nan'))
    rnd = random.Random(seed)
    blocks = [(sum(by[d]), len(by[d])) for d in ds]
    nb = len(blocks)
    out = []
    for _ in range(iters):
        s = n = 0.0
        for _ in range(nb):
            bs, bn = blocks[rnd.randrange(nb)]
            s += bs; n += bn
        if n:
            out.append(s / n)
    out.sort()
    return (mean([v for _, v in pairs]),
            (out[int(.025 * len(out))], out[int(.975 * len(out))]))


def ac(rs, lag):
    """VERBATIM from scan_run.py:201-208."""
    n = len(rs)
    if n < lag + 100:
        return float('nan')
    m = sum(rs) / n
    num = sum((rs[i] - m) * (rs[i - lag] - m) for i in range(lag, n))
    den = sum((x - m) ** 2 for x in rs)
    return num / den if den > 0 else float('nan')


def corr(xy):
    n = len(xy)
    mx = sum(x for x, y in xy) / n
    my = sum(y for x, y in xy) / n
    num = sum((x - mx) * (y - my) for x, y in xy)
    dx = math.sqrt(sum((x - mx) ** 2 for x, y in xy))
    dy = math.sqrt(sum((y - my) ** 2 for x, y in xy))
    return num / (dx * dy) if dx > 0 and dy > 0 else float('nan')


def atr20_arrays(h, l, c):
    """SMA(20) of true range - identical to rvmr_spec.atr20 but on
    parallel arrays instead of 2.5M tuples. Equality is asserted below
    against the frozen implementation on a slice."""
    n = len(c)
    out = [None] * n
    tr = collections.deque()
    s = 0.0
    prev = None
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


def main():
    print('=' * 78)
    print('ANOMALY-CONFIRM-V1   DISCOVERY-SIDE FREEZE CONSTANTS')
    print('  discovery window  <= %s   (the ONLY window read here)' % DISC_END)
    print('  holdout           >= %s   NOT READ FOR ANY OUTCOME' % HOLD_START)
    print('  seed %d   bootstrap %d' % (SEED, B_MAIN))
    print('=' * 78)

    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    N = len(D['c'])
    o, h, l, c, v, em, mod, day = (D['o'], D['h'], D['l'], D['c'], D['v'],
                                   D['em'], D['mod'], D['day'])
    idx = [i for i in range(N) if day[i] <= DISC_END]
    print('\ntotal bars %d   discovery bars %d   (holdout bars %d)'
          % (N, len(idx), N - len(idx)))
    print('discovery span %s .. %s' % (D['et'][idx[0]], D['et'][idx[-1]]))
    LAST_DISC = idx[-1]

    # ---------------------------------------------------------------
    # RVMR parity audit (allowed pre-freeze: no outcome)
    # ---------------------------------------------------------------
    print('\n' + '-' * 78)
    print('RVMR PARITY AUDIT')
    print('-' * 78)
    rng = [h[i] - l[i] for i in range(N)]
    rr = RS.trailing_ratio(rng)
    RB = [RS.bucket(x) if x is not None else None for x in rr]
    # independent recomputation of the trailing ratio at 5 probe points
    probes = [1440, 100000, 700000, 1200000, 1577000]
    ok = True
    for p in probes:
        direct = rng[p] / (sum(rng[p - 1440:p]) / 1440.0)
        if abs(direct - rr[p]) > 1e-9:
            ok = False
            print('  MISMATCH at %d: direct %.12f vs spec %.12f'
                  % (p, direct, rr[p]))
    print('  trailing_ratio(W=1440, excludes own bar) parity at 5 probes: %s'
          % ('EXACT' if ok else 'FAILED'))
    print('  first index with a score: %d (expected 1440)'
          % next(i for i in range(N) if rr[i] is not None))
    print('  bucket thresholds  LOW < %.3f <= MEDIUM <= %.3f < HIGH'
          % (RS.T1, RS.T2))
    # atr parity
    atr = atr20_arrays(h, l, c)
    bars_slice = list(zip(D['et'][:5000], o[:5000], h[:5000], l[:5000],
                          c[:5000], v[:5000]))
    ref = RS.atr20(bars_slice)
    bad = sum(1 for i in range(100, 5000)
              if ref[i] is None or abs(ref[i] - atr[i]) > 1e-9)
    print('  atr20 array implementation vs frozen rvmr_spec.atr20 on'
          ' bars 100..4999: %d mismatches' % bad)
    assert bad == 0 and ok

    # ---------------------------------------------------------------
    # returns and 15m blocks - VERBATIM scan2_run.py:68-89
    # ---------------------------------------------------------------
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
        rs = runs[dd]
        k = 0
        while k + 15 <= len(rs):
            block = rs[k:k + 15]
            if block[-1][0] - block[0][0] == 14:
                r15.append((block[0][0], block[-1][0],
                            sum(x[1] for x in block), dd))
                k += 15
            else:
                k += 1
    print('\ncontiguous 1m log returns (discovery) %d' % len(rets))
    print('non-overlapping 15m blocks (discovery)  %d' % len(r15))

    # ---- block-grid diagnostic: what clock does the grid actually sit on?
    print('\n' + '-' * 78)
    print('15m BLOCK GRID ANCHORING (this is a FACT about the frozen code,')
    print('not a choice: blocks are anchored to each calendar day\'s FIRST')
    print('contiguous return, not to a :00/:15/:30/:45 clock grid)')
    print('-' * 78)
    shown = 0
    seen_day = None
    for (i0, i1, rv_, dd) in r15:
        if dd == seen_day:
            continue
        seen_day = dd
        print('  day %s  block1 bars %s .. %s   (return spans close %s -> %s)'
              % (dd, D['et'][i0][11:16], D['et'][i1][11:16],
                 D['et'][i0 - 1][11:16], D['et'][i1][11:16]))
        shown += 1
        if shown >= 4:
            break

    # ---------------------------------------------------------------
    # shock pairs - VERBATIM scan2_run.py:95-109
    # ---------------------------------------------------------------
    pairs9 = []
    for a in range(len(r15) - 1):
        i0, i1, rv_, dd = r15[a]
        j0, j1, rf, dd2 = r15[a + 1]
        if j0 - i1 != 1:
            continue
        pairs9.append((rv_, rf, dd2, RB[j0], i0, i1, j0, j1))
    print('\nshock/forward pairs (discovery) %d' % len(pairs9))
    xdays = sum(1 for p in pairs9 if day[p[4]] != day[p[6]])
    print('  pairs whose shock block and forward block sit on DIFFERENT'
          ' calendar dates: %d' % xdays)
    print('  (minute-adjacency j0-i1==1 is enforced; a true midnight-'
          'contiguous pair therefore crosses the date label)')
    assert all(day[p[6]] <= DISC_END and day[p[4]] <= DISC_END
               for p in pairs9), 'HOLDOUT LEAK'

    xs = sorted(p[0] for p in pairs9)
    decs9 = [xs[int(q * len(xs) / 10)] for q in range(1, 10)]

    def dec_of(x, _d=decs9):
        for k, cc in enumerate(_d):
            if x < cc:
                return k
        return 9

    print('\n' + '=' * 78)
    print('FROZEN DECILE CUTPOINTS  (global, static, in-sample over the')
    print('ENTIRE discovery pair set - not trailing, not annual). These')
    print('nine numbers TRANSPORT UNCHANGED to the holdout.')
    print('=' * 78)
    for q in range(9):
        print('  cut %d (dec%d|dec%d)   %+.10f  log-return   (%+8.3f bp)'
              % (q + 1, q, q + 1, decs9[q], decs9[q] * 1e4))
    cnt = collections.Counter(dec_of(p[0]) for p in pairs9)
    print('  decile counts: ' + ' '.join('%d:%d' % (k, cnt[k])
                                         for k in range(10)))

    # ---------------------------------------------------------------
    # CONTINUATION construction
    # ---------------------------------------------------------------
    # direction-normalised: cont = sign(shock) * forward15
    EXTREME = (0, 9)
    ev = []          # (dd2, cont, state, dec, shock, fwd, i1, j0)
    for rv_, rf, dd2, st, i0, i1, j0, j1 in pairs9:
        dc = dec_of(rv_)
        if dc not in EXTREME:
            continue
        sgn = 1.0 if rv_ > 0 else (-1.0 if rv_ < 0 else 0.0)
        if sgn == 0.0:
            continue
        ev.append((dd2, sgn * rf, st, dc, rv_, rf, i1, j0))
    print('\n' + '=' * 78)
    print('SHOCK-CONT DISCOVERY ANCHORS  (extreme set = dec0 U dec9,')
    print('cont = sign(shock) x forward15, state = RB[j0] = RVMR RANGE')
    print('state of the FIRST BAR OF THE FORWARD BLOCK)')
    print('=' * 78)
    print('  extreme events %d   (dec0 %d, dec9 %d)'
          % (len(ev), sum(1 for e in ev if e[3] == 0),
             sum(1 for e in ev if e[3] == 9)))

    def blk(sel):
        return [(e[0], e[1]) for e in sel]

    print('\n  %-8s %8s %12s %28s' % ('state', 'n', 'cont bp', '95% CI (bp)'))
    anchors = {}
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        sel = [e for e in ev if e[2] == st]
        it = B_MAIN if st == 'MEDIUM' else 4000
        m, (lo, hi) = day_boot(blk(sel), iters=it)
        anchors[st] = m
        print('  %-8s %8d %+12.4f   [%+11.4f, %+11.4f]%s'
              % (st, len(sel), m * 1e4, lo * 1e4, hi * 1e4,
                 '   <-- PRIMARY ANCHOR' if st == 'MEDIUM' else ''))
    seln = [e for e in ev if e[2] is None]
    print('  %-8s %8d  (bars with no RVMR score - excluded)'
          % ('None', len(seln)))

    print('\n  UP / DOWN decomposition inside each state:')
    print('  %-8s %-5s %8s %12s' % ('state', 'side', 'n', 'cont bp'))
    updn = {}
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        for dc, nm in ((9, 'UP'), (0, 'DOWN')):
            sel = [e for e in ev if e[2] == st and e[3] == dc]
            m = mean([e[1] for e in sel])
            updn[(st, nm)] = m
            print('  %-8s %-5s %8d %+12.4f' % (st, nm, len(sel), m * 1e4))
    mu = updn[('MEDIUM', 'UP')]
    mdw = updn[('MEDIUM', 'DOWN')]
    print('\n  MEDIUM UP   %+0.4f bp   MEDIUM DOWN %+0.4f bp   both positive: %s'
          % (mu * 1e4, mdw * 1e4, 'YES' if (mu > 0 and mdw > 0) else 'NO'))

    # dec7 secondary (source nomenclature: dec7 showed continuation)
    d7 = [(dd2, rf) for rv_, rf, dd2, st, i0, i1, j0, j1 in pairs9
          if dec_of(rv_) == 7 and st == 'MEDIUM']
    m7 = mean([x[1] for x in d7])
    d7all = [(dd2, rf) for rv_, rf, dd2, st, i0, i1, j0, j1 in pairs9
             if dec_of(rv_) == 7]
    print('\n  dec7 SECONDARY:  MEDIUM n %d  fwd15 %+0.4f bp   |'
          '  all-states n %d  fwd15 %+0.4f bp'
          % (len(d7), m7 * 1e4, len(d7all), mean([x[1] for x in d7all]) * 1e4))

    # ---------------------------------------------------------------
    # CONTROL CUTPOINTS (discovery-frozen; transport unchanged)
    # ---------------------------------------------------------------
    print('\n' + '=' * 78)
    print('CONTROL CUTPOINTS - frozen on the discovery extreme-event set')
    print('=' * 78)
    # C1 ATR: atrRel = atr20(i1) / close(i1), measured at the last bar of
    # the shock block (known before the forward block starts)
    arel = sorted(atr[e[6]] / c[e[6]] for e in ev if atr[e[6]] is not None)
    a1, a2 = arel[len(arel) // 3], arel[2 * len(arel) // 3]
    print('  C1 ATR  atrRel = atr20(i1)/close(i1)   n scored %d' % len(arel))
    print('     tercile cuts  %.10f   %.10f   (ATR-LOW < c1 <= ATR-MID'
          ' <= c2 < ATR-HIGH)' % (a1, a2))
    # C2 time of day of the forward block start j0
    tod = collections.Counter()
    for e in ev:
        m_ = mod[e[7]]
        b = ('OVERNIGHT' if (m_ >= 1081 or m_ <= 569)
             else ('RTH_AM' if m_ <= 750 else 'RTH_PM'))
        tod[b] += 1
    print('  C2 TIME-OF-DAY of forward-block start j0 (frozen buckets:'
          ' OVERNIGHT mod>=1081 or mod<=569; RTH_AM 570..750;'
          ' RTH_PM 751..960)')
    print('     discovery counts  ' + '  '.join('%s %d' % (k, tod[k])
                                                for k in sorted(tod)))
    # C3 shock magnitude split, frozen per side
    up_abs = sorted(abs(e[4]) for e in ev if e[3] == 9)
    dn_abs = sorted(abs(e[4]) for e in ev if e[3] == 0)
    up_med, dn_med = med(up_abs), med(dn_abs)
    print('  C3 |shock| median split   UP %.10f (%.3f bp)   DOWN %.10f'
          ' (%.3f bp)' % (up_med, up_med * 1e4, dn_med, dn_med * 1e4))

    # ---------------------------------------------------------------
    # MONDAY-RTH anchor - VERBATIM scan2_run.py:357-377
    # ---------------------------------------------------------------
    print('\n' + '=' * 78)
    print('MONDAY-RTH DISCOVERY ANCHOR (verbatim S22 segmentation)')
    print('=' * 78)
    segs = {'SUN 18:00-24:00': [], 'MON 00:00-09:29': [], 'MON RTH': []}
    rth_all = collections.defaultdict(float)
    for i, r in rets:
        w = datetime.datetime.strptime(day[i], '%Y-%m-%d').weekday()
        if w == 6 and mod[i] >= 1081:
            segs['SUN 18:00-24:00'].append((day[i], r))
        elif w == 0 and mod[i] <= 569:
            segs['MON 00:00-09:29'].append((day[i], r))
        elif w == 0 and 570 <= mod[i] <= 960:
            segs['MON RTH'].append((day[i], r))
        if 570 <= mod[i] <= 960:
            rth_all[day[i]] += r
    for nm in ('SUN 18:00-24:00', 'MON 00:00-09:29', 'MON RTH'):
        by = collections.defaultdict(float)
        for dd, r in segs[nm]:
            by[dd] += r
        pr = list(by.items())
        it = B_MAIN if nm == 'MON RTH' else 4000
        m, (lo, hi) = day_boot(pr, iters=it)
        print('  %-16s n %4d   mean %+8.4f bp   CI [%+8.4f, %+8.4f]%s'
              % (nm, len(pr), m * 1e4, lo * 1e4, hi * 1e4,
                 '   <-- PRIMARY ANCHOR' if nm == 'MON RTH' else ''))
    monset = set(dd for dd in rth_all
                 if datetime.datetime.strptime(dd, '%Y-%m-%d').weekday() == 0)
    nonmon = [(dd, rth_all[dd]) for dd in sorted(rth_all) if dd not in monset]
    mm, _ = day_boot([(dd, rth_all[dd]) for dd in sorted(monset)], iters=4000)
    nm_, _ = day_boot(nonmon, iters=4000)
    print('  NON-MONDAY RTH   n %4d   mean %+8.4f bp' % (len(nonmon), nm_ * 1e4))
    print('  DIFFERENTIAL  Monday RTH - non-Monday RTH = %+0.4f bp'
          % ((mm - nm_) * 1e4))
    print('  (the differential is NOT in the frozen S22 source; it is'
          ' declared here as a required SIGN gate, not the primary)')

    # ---------------------------------------------------------------
    # NON-PROMOTABLE SECONDARY ANCHORS
    # ---------------------------------------------------------------
    print('\n' + '=' * 78)
    print('NON-PROMOTABLE SECONDARY DIAGNOSTIC ANCHORS (discovery)')
    print('=' * 78)
    print('  AC-FLIP  (scan_run.py ac(), applied to the STATE-FILTERED list)')
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        rs = [r for i, r in rets if RB[i] == st]
        print('    1m  %-7s n %8d   AC1 %+0.6f' % (st, len(rs), ac(rs, 1)))
    p15 = [(i0, rv_) for (i0, i1, rv_, dd) in r15]
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        rs = [r for i, r in p15 if RB[i] == st]
        print('    15m %-7s n %8d   AC1 %+0.6f' % (st, len(rs), ac(rs, 1)))
    print('  CLV-FLIP  (scan2_run.py:180-202)')
    clvp = []
    for k in range(len(rets) - 1):
        i, r = rets[k]
        i2, r2 = rets[k + 1]
        if i2 - i != 1 or h[i] <= l[i]:
            continue
        clvp.append((i, (2 * c[i] - h[i] - l[i]) / (h[i] - l[i]), r2))
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        sub = [(x, y) for i, x, y in clvp if RB[i] == st]
        print('    %-7s n %8d   corr(CLV_t, r_t+1) %+0.6f'
              % (st, len(sub), corr(sub)))
    print('  LEVERAGE-V  (scan2_run.py:326-334)')
    lv = {}
    for (i0, i1, rv_, dd) in r15:
        fut = any(RB[j] == 'HIGH' for j in range(i1 + 1, min(i1 + 31, N)))
        lv.setdefault(dec_of(rv_), []).append(1 if fut else 0)
    print('    ' + '  '.join('d%d %.4f' % (k, mean(lv[k]))
                             for k in sorted(lv)))
    # lineage note: the frozen leverage statistic scans forward 30 bars
    # from i1 with min(i1+31, N) where N is the FULL series length.
    late = sum(1 for (i0, i1, rv_, dd) in r15
               if i1 + 31 > LAST_DISC + 1)
    print('    LINEAGE NOTE: blocks whose 30-bar forward scan could reach'
          ' past the last discovery bar: %d' % late)

    print('\n' + '=' * 78)
    print('FREEZE CONSTANTS COMPLETE - DISCOVERY WINDOW ONLY.')
    print('NO 2024+ CANDIDATE OUTCOME WAS COMPUTED IN THIS FILE.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
    print('=' * 78)


if __name__ == '__main__':
    main()
