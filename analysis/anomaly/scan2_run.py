#!/usr/bin/env python3
# ======================================================================
# ANOMALY-SCAN-V1 WAVE 2 - discovery window only (<= 2023-12-31)
# ======================================================================
# Wave-2 menu frozen first at commit c4c4d8202 (protocol sha256
# edd1f1baae50619a689da15b2ffedfb9c5865e698304c45588b4dbb2ab19255f).
# Holdout >= 2024-01-01 is NEVER read for any statistic here.
# EXPLORATORY / HYPOTHESIS-GENERATING. SUBMITS NO ORDERS.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, math, random, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../rvmr'))
import rvmr_spec as RS
import rvmr_run as RV

DISC_END = '2023-12-31'
SEED = 20260825


def mean(x):
    return sum(x) / len(x) if x else float('nan')


def med(x):
    return sorted(x)[len(x) // 2] if x else float('nan')


def day_boot(pairs, iters=2000, seed=SEED):
    by = collections.defaultdict(list)
    for d, v in pairs:
        by[d].append(v)
    ds = sorted(by)
    if len(ds) < 15:
        return mean([v for _, v in pairs]), (float('nan'), float('nan'))
    rnd = random.Random(seed)
    out = []
    for _ in range(iters):
        s = n = 0.0
        for _ in ds:
            k = ds[rnd.randrange(len(ds))]
            s += sum(by[k]); n += len(by[k])
        if n:
            out.append(s / n)
    out.sort()
    return mean([v for _, v in pairs]), (out[int(.025 * len(out))],
                                         out[int(.975 * len(out))])


def main():
    print('=' * 78)
    print('ANOMALY-SCAN-V1  WAVE 2   DISCOVERY <= %s ONLY' % DISC_END)
    print('  menu frozen at commit c4c4d8202 before computation')
    print('  EXPLORATORY. SUBMITS NO ORDERS.')
    print('=' * 78)
    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    N = len(D['c'])
    o, h, l, c, v, em, mod, day = (D['o'], D['h'], D['l'], D['c'], D['v'],
                                   D['em'], D['mod'], D['day'])
    idx = [i for i in range(N) if day[i] <= DISC_END]
    rr = RS.trailing_ratio([h[i] - l[i] for i in range(N)])
    RB = [RS.bucket(x) if x is not None else None for x in rr]
    print('discovery bars %d' % len(idx))

    rets = []
    for i in idx:
        if i == 0 or em[i] - em[i - 1] != 1 or c[i - 1] <= 0:
            continue
        rets.append((i, math.log(c[i] / c[i - 1])))

    # 15m non-overlapping grid blocks (18:00-anchored)
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

    # ================================================= S9 shock response
    print('\n' + '=' * 78)
    print('S9  SHOCK-RESPONSE: forward 15m return by decile of prior 15m return')
    print('=' * 78)
    pairs9 = []
    for a in range(len(r15) - 1):
        i0, i1, rv_, dd = r15[a]
        j0, j1, rf, dd2 = r15[a + 1]
        if j0 - i1 != 1:
            continue
        pairs9.append((rv_, rf, dd2, RB[j0]))
    xs = sorted(p[0] for p in pairs9)
    decs9 = [xs[int(q * len(xs) / 10)] for q in range(1, 10)]

    def dec_of(x, _d=decs9):
        for k, cc in enumerate(_d):
            if x < cc:
                return k
        return 9

    print('  %-5s %10s %12s %26s %7s' % ('dec', 'prior bp', 'fwd15 bp',
                                          'day-clustered 95% CI', 'n'))
    for dc in range(10):
        sub = [(dd, rf) for rv_, rf, dd, st in pairs9 if dec_of(rv_) == dc]
        pri = mean([rv_ for rv_, rf, dd, st in pairs9 if dec_of(rv_) == dc])
        m, (lo, hi) = day_boot(sub, iters=1500)
        sig = (hi < 0 or lo > 0) and lo == lo
        print('  %-5d %+10.2f %+12.3f   [%+9.3f, %+9.3f] %7d%s'
              % (dc, pri * 1e4, m * 1e4, lo * 1e4, hi * 1e4, len(sub),
                 '  <-- CI excludes 0' if sig else ''))
    print('\n  extreme deciles by RVMR state (fwd15 bp):')
    for dc in (0, 9):
        for st in ('LOW', 'MEDIUM', 'HIGH'):
            sub = [(dd, rf) for rv_, rf, dd, s2 in pairs9
                   if dec_of(rv_) == dc and s2 == st]
            if len(sub) < 200:
                continue
            m, (lo, hi) = day_boot(sub, iters=1000)
            sig = (hi < 0 or lo > 0) and lo == lo
            print('    dec %d  %-7s fwd15 %+9.3f bp  CI [%+8.3f, %+8.3f]  n %6d%s'
                  % (dc, st, m * 1e4, lo * 1e4, hi * 1e4, len(sub),
                     '  <-- CI excludes 0' if sig else ''))

    # ================================================= S10 impact asymmetry
    print('\n' + '=' * 78)
    print('S10  ASYMMETRIC PRICE IMPACT  |r|/volume, up-bars vs down-bars')
    print('=' * 78)
    lamu, lamd = [], []
    for i, r in rets:
        if v[i] <= 0 or r == 0:
            continue
        lam = abs(r) / v[i] * 1e9
        (lamu if r > 0 else lamd).append((day[i], lam))
    mu, (lu, hu2) = day_boot(lamu, iters=1500)
    md_, (ld, hd) = day_boot(lamd, iters=1500)
    print('  lambda UP   %8.3f  CI [%8.3f, %8.3f]  n %d' % (mu, lu, hu2, len(lamu)))
    print('  lambda DOWN %8.3f  CI [%8.3f, %8.3f]  n %d' % (md_, ld, hd, len(lamd)))
    print('  DOWN/UP ratio %.4f' % (md_ / mu))
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        u2 = [x for (i, r), x in zip(rets, [None] * 0)]  # placeholder no-op
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        uu = [abs(r) / v[i] * 1e9 for i, r in rets
              if v[i] > 0 and r > 0 and RB[i] == st]
        dd2 = [abs(r) / v[i] * 1e9 for i, r in rets
               if v[i] > 0 and r < 0 and RB[i] == st]
        if uu and dd2:
            print('  %-7s DOWN/UP %.4f   (nU %d nD %d)'
                  % (st, mean(dd2) / mean(uu), len(uu), len(dd2)))

    # ================================================= S11 range geometry
    print('\n' + '=' * 78)
    print('S11  PARKINSON/CC VARIANCE RATIO + CLOSE-LOCATION VALUE')
    print('=' * 78)
    pk = []
    for dd in sorted(runs):
        rs = runs[dd]
        sp = scc = 0.0
        n2 = 0
        for i, r in rs:
            if h[i] > l[i] > 0:
                sp += math.log(h[i] / l[i]) ** 2
                scc += r * r
                n2 += 1
        if n2 > 300 and scc > 0:
            pk.append((dd, (sp / (4 * math.log(2))) / scc))
    m, (lo, hi) = day_boot(pk, iters=1500)
    print('  Parkinson/CC per day: mean %.4f  CI [%.4f, %.4f]  (GBM = 1.0)'
          % (m, lo, hi))
    # CLV -> next-bar return
    clvp = []
    for k in range(len(rets) - 1):
        i, r = rets[k]
        i2, r2 = rets[k + 1]
        if i2 - i != 1 or h[i] <= l[i]:
            continue
        clv = (2 * c[i] - h[i] - l[i]) / (h[i] - l[i])
        clvp.append((i, clv, r2))
    def corr(xy):
        n2 = len(xy)
        mx = sum(x for x, y in xy) / n2
        my = sum(y for x, y in xy) / n2
        num = sum((x - mx) * (y - my) for x, y in xy)
        dx = math.sqrt(sum((x - mx) ** 2 for x, y in xy))
        dy = math.sqrt(sum((y - my) ** 2 for x, y in xy))
        return num / (dx * dy) if dx > 0 and dy > 0 else float('nan')
    print('  corr(CLV_t, r_{t+1}) pooled %+.4f   (n %d, naive se %.4f)'
          % (corr([(x, y) for _, x, y in clvp]), len(clvp),
             1 / math.sqrt(len(clvp))))
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        sub = [(x, y) for i, x, y in clvp if RB[i] == st]
        if len(sub) > 5000:
            print('  %-7s corr(CLV, r+1) %+.4f  (n %d)' % (st, corr(sub), len(sub)))

    # ================================================= S12 gap response
    print('\n' + '=' * 78)
    print('S12  OPEN-GAP RESPONSE CURVE (deciles; strategies before, curve new)')
    print('=' * 78)
    # prior 16:00 close and 09:30 open + RTH O->C per day
    prev_close = {}
    rth_oc = {}
    open930 = {}
    lastc = None
    lastd = None
    for i in idx:
        if mod[i] == 960:
            prev_close[day[i]] = c[i]
        if mod[i] == 570:
            open930[day[i]] = o[i]
        if 570 <= mod[i] <= 960:
            if day[i] not in rth_oc:
                rth_oc[day[i]] = [o[i], c[i]]
            else:
                rth_oc[day[i]][1] = c[i]
    ds = sorted(open930)
    gaps = []
    for k in range(1, len(ds)):
        dd = ds[k]; pd = ds[k - 1]
        if pd in prev_close and dd in rth_oc:
            g = math.log(open930[dd] / prev_close[pd])
            ocr = math.log(rth_oc[dd][1] / rth_oc[dd][0])
            gaps.append((g, ocr, dd))
    xs = sorted(g for g, _, _ in gaps)
    decs12 = [xs[int(q * len(xs) / 10)] for q in range(1, 10)]
    print('  %-5s %10s %12s %26s %5s' % ('dec', 'gap bp', 'RTH O->C bp',
                                          'day-clustered 95% CI', 'n'))
    for dc in range(10):
        sub = [(dd, ocr) for g, ocr, dd in gaps if dec_of2(g, decs12) == dc]
        pri = mean([g for g, ocr, dd in gaps if dec_of2(g, decs12) == dc])
        m, (lo, hi) = day_boot(sub, iters=1500)
        sig = (hi < 0 or lo > 0) and lo == lo
        print('  %-5d %+10.1f %+12.2f   [%+9.2f, %+9.2f] %5d%s'
              % (dc, pri * 1e4, m * 1e4, lo * 1e4, hi * 1e4, len(sub),
                 '  <-- CI excludes 0' if sig else ''))

    # ================================================= S13 |r| long memory
    print('\n' + '=' * 78)
    print('S13  LONG MEMORY OF |r| - ACF decay and memory length vs RVMR 1440')
    print('=' * 78)
    absr = [abs(r) for _, r in rets]
    n2 = len(absr)
    m2 = sum(absr) / n2
    var2 = sum((x - m2) ** 2 for x in absr)
    lags = (1, 5, 10, 30, 60, 120, 240, 480, 960, 1440)
    acs = {}
    for lg in lags:
        num = sum((absr[i] - m2) * (absr[i - lg] - m2) for i in range(lg, n2, 3))
        den = var2 * (((n2 - lg) // 3) / n2 * 3) / 3
        # subsampled estimator; renormalize by matching subsample variance
        sub = [(absr[i] - m2) ** 2 for i in range(lg, n2, 3)]
        acs[lg] = (num / len(sub)) / (sum(sub) / len(sub))
    for lg in lags:
        print('  lag %5d   ACF|r| %+.4f' % (lg, acs[lg]))
    pts = [(math.log(lg), math.log(acs[lg])) for lg in lags if acs[lg] > 0]
    if len(pts) >= 4:
        mx = mean([x for x, y in pts]); my = mean([y for x, y in pts])
        b = (sum((x - mx) * (y - my) for x, y in pts)
             / sum((x - mx) ** 2 for x, y in pts))
        print('  log-log decay slope %.3f  (power-law long memory; -0.2..-0.4'
              ' typical of equity vol)' % b)
    below = [lg for lg in lags if acs[lg] < 0.05]
    print('  first frozen lag with ACF < 0.05: %s   (RVMR window = 1440)'
          % (below[0] if below else '>1440'))

    # ================================================= S14 vol seasonality
    print('\n' + '=' * 78)
    print('S14  MINUTE-OF-DAY |r| SEASONALITY - deviations > 30% from local')
    print('=' * 78)
    bymin = collections.defaultdict(list)
    for i, r in rets:
        bymin[mod[i]].append(abs(r))
    mins = sorted(bymin)
    curve = {m3: mean(bymin[m3]) for m3 in mins}
    flags = []
    for m3 in mins:
        loc = [curve[x] for x in range(m3 - 10, m3 + 11)
               if x in curve and x != m3]
        if len(loc) < 12:
            continue
        base = med(loc)
        if base > 0 and abs(curve[m3] / base - 1) > 0.30:
            flags.append((m3, curve[m3] / base))
    for m3, ratio in sorted(flags, key=lambda x: -abs(x[1] - 1))[:15]:
        print('  %02d:%02d ET  |r| = %.2fx local median' % (m3 // 60, m3 % 60, ratio))

    # ================================================= S19 state process
    print('\n' + '=' * 78)
    print('S19  RVMR STATE PROCESS - transitions, dwell, leverage asymmetry')
    print('=' * 78)
    seq = [(i, RB[i]) for i in idx if RB[i] is not None]
    trans = collections.Counter()
    dwell = collections.defaultdict(list)
    cur, start = None, None
    prev_i = None
    for i, st in seq:
        if prev_i is not None and i - prev_i == 1:
            trans[(pst, st)] += 1
            if st != cur:
                dwell[cur].append(i - start)
                cur, start = st, i
        else:
            cur, start = st, i
        pst = st
        prev_i = i
    for a in ('LOW', 'MEDIUM', 'HIGH'):
        tot = sum(trans[(a, b)] for b in ('LOW', 'MEDIUM', 'HIGH'))
        row = '  '.join('%s %.4f' % (b, trans[(a, b)] / tot)
                        for b in ('LOW', 'MEDIUM', 'HIGH'))
        print('  from %-7s  %s   (n %d)' % (a, row, tot))
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        dw = dwell[st]
        if dw:
            print('  dwell %-7s median %5.0f min   p90 %5.0f   n %d'
                  % (st, med(dw), sorted(dw)[int(.9 * len(dw))], len(dw)))
    # leverage: P(reach HIGH within 30m) by signed prior 15m return decile
    print('\n  leverage asymmetry: P(HIGH within 30m | prior 15m return decile):')
    rbmap = {}
    for a in range(len(r15)):
        i0, i1, rv_, dd = r15[a]
        fut = any(RB[j] == 'HIGH' for j in range(i1 + 1, min(i1 + 31, N)))
        rbmap.setdefault(dec_of(rv_), []).append(1 if fut else 0)
    for dc in range(10):
        if dc in rbmap:
            print('    dec %d  P %.4f  (n %d)' % (dc, mean(rbmap[dc]),
                                                  len(rbmap[dc])))

    # ================================================= S22 periodogram + Monday
    print('\n' + '=' * 78)
    print('S22  DAY-CYCLE PERIODOGRAM of mean signed return by minute-of-day')
    print('=' * 78)
    mm = {m3: mean([r for r in [x for x in []]]) for m3 in []}
    sigm = collections.defaultdict(list)
    for i, r in rets:
        sigm[mod[i]].append(r)
    vec = [(m3, mean(sigm[m3])) for m3 in sorted(sigm) if len(sigm[m3]) > 200]
    M3 = len(vec)
    amps = []
    for k in range(1, 49):
        re = sum(y * math.cos(2 * math.pi * k * j / M3)
                 for j, (_, y) in enumerate(vec))
        im = sum(y * math.sin(2 * math.pi * k * j / M3)
                 for j, (_, y) in enumerate(vec))
        amps.append((math.hypot(re, im) / M3, k))
    amps.sort(reverse=True)
    for a2, k in amps[:5]:
        print('  harmonic k=%2d  period %6.1f min  amplitude %.4f bp'
              % (k, M3 / k, a2 * 1e4))
    print('\n  MONDAY DECOMPOSITION (accrual per Monday, day-clustered):')
    import datetime as dt
    segs = {'SUN 18:00-24:00': [], 'MON 00:00-09:29': [], 'MON RTH': []}
    for i, r in rets:
        w = dt.datetime.strptime(day[i], '%Y-%m-%d').weekday()
        if w == 6 and mod[i] >= 1081:
            segs['SUN 18:00-24:00'].append((day[i], r))
        elif w == 0 and mod[i] <= 569:
            segs['MON 00:00-09:29'].append((day[i], r))
        elif w == 0 and 570 <= mod[i] <= 960:
            segs['MON RTH'].append((day[i], r))
    for nm2 in ('SUN 18:00-24:00', 'MON 00:00-09:29', 'MON RTH'):
        by = collections.defaultdict(float)
        for dd, r in segs[nm2]:
            by[dd] += r
        pairs = list(by.items())
        m, (lo, hi) = day_boot(pairs, iters=2000)
        sig = (hi < 0 or lo > 0) and lo == lo
        print('    %-16s mean %+7.2f bp/session  CI [%+7.2f, %+7.2f]  n %d%s'
              % (nm2, m * 1e4, lo * 1e4, hi * 1e4, len(pairs),
                 '  <-- CI excludes 0' if sig else ''))

    print('\n' + '=' * 78)
    print('WAVE 2 COMPLETE - DISCOVERY ONLY. HOLDOUT UNTOUCHED.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
    print('=' * 78)


def dec_of2(x, decs):
    for k, cc in enumerate(decs):
        if x < cc:
            return k
    return 9


if __name__ == '__main__':
    main()
