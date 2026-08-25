#!/usr/bin/env python3
# ======================================================================
# ANOMALY-SCAN-V1 - structural anomaly scan, DISCOVERY WINDOW ONLY
# ======================================================================
# Protocol frozen first: docs/ANOMALY_SCAN_V1_PROTOCOL.md
#   sha256 179af253437dae3cf53ac6fb0f4ca86ae3f156c2e7da7daf85d3e7072347ea67
#   commit 9f71b24b0fc9018fc8132b34684c105c6764ca45
# Discovery <= 2023-12-31. Holdout >= 2024-01-01 is NEVER read for any
# statistic in this file. EXPLORATORY / HYPOTHESIS-GENERATING only.
# SUBMITS NO ORDERS. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, math, random, collections

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../rvmr', '../dvt'):
    sys.path.insert(0, os.path.join(HERE, p))
import rvmr_spec as RS
import rvmr_run as RV
import dvt_spec as SP

DISC_END = '2023-12-31'
SEED, ITERS = 20260825, 5000
QLIST = (2, 5, 10, 15, 30, 60, 120)


def mean(x):
    return sum(x) / len(x) if x else float('nan')


def med(x):
    return sorted(x)[len(x) // 2] if x else float('nan')


def day_boot_mean(pairs, iters=ITERS, seed=SEED):
    """pairs: [(day, value)] -> mean, day-clustered 95% CI."""
    by = collections.defaultdict(list)
    for d, v in pairs:
        by[d].append(v)
    ds = sorted(by)
    if len(ds) < 20:
        return float('nan'), (float('nan'), float('nan'))
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
    print('ANOMALY-SCAN-V1   DISCOVERY WINDOW <= %s ONLY' % DISC_END)
    print('  protocol sha256 179af253437dae3cf53ac6fb0f4ca86ae3f156c2e7da7')
    print('  EXPLORATORY / HYPOTHESIS-GENERATING. SUBMITS NO ORDERS.')
    print('=' * 78)
    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    N = len(D['c'])
    # ---------------- restrict to discovery
    idx = [i for i in range(N) if D['day'][i] <= DISC_END]
    print('discovery bars %d of %d   %s .. %s'
          % (len(idx), N, D['et'][idx[0]], D['et'][idx[-1]]))
    assert D['day'][idx[-1]] <= DISC_END
    c, h, l, v, em, mod, day = (D['c'], D['h'], D['l'], D['v'], D['em'],
                                D['mod'], D['day'])
    # frozen RVMR range state (score + bucket), computed on full series
    # causally but only READ inside discovery
    rr = RS.trailing_ratio([h[i] - l[i] for i in range(N)])
    RB = [RS.bucket(x) if x is not None else None for x in rr]

    # log returns on contiguous minutes, discovery only
    rets = []          # (i, r, day, state, mod)
    for i in idx:
        if i == 0 or em[i] - em[i - 1] != 1 or day[i] > DISC_END:
            continue
        if c[i - 1] <= 0:
            continue
        r = math.log(c[i] / c[i - 1])
        rets.append((i, r))
    print('contiguous 1m log returns: %d' % len(rets))

    # ================================================= S1 variance ratios
    print('\n' + '=' * 78)
    print('S1  VARIANCE RATIOS  VR(q) = Var(r_q) / (q Var(r_1))   (non-overlap)')
    print('    VR < 1 = mean reversion at that scale; VR > 1 = momentum')
    print('=' * 78)
    # per-day sufficient stats
    dstat = collections.defaultdict(lambda: {'n': 0, 's': 0.0, 'ss': 0.0})
    qstat = {q: collections.defaultdict(lambda: {'n': 0, 's': 0.0, 'ss': 0.0})
             for q in QLIST}
    # build per-day contiguous runs
    runs = collections.defaultdict(list)
    for i, r in rets:
        dd = day[i]
        dstat[dd]['n'] += 1; dstat[dd]['s'] += r; dstat[dd]['ss'] += r * r
        runs[dd].append((i, r))
    for dd, rs in runs.items():
        for q in QLIST:
            k = 0
            while k + q <= len(rs):
                block = rs[k:k + q]
                if block[-1][0] - block[0][0] == q - 1:
                    rq = sum(x[1] for x in block)
                    st = qstat[q][dd]
                    st['n'] += 1; st['s'] += rq; st['ss'] += rq * rq
                    k += q
                else:
                    k += 1
    days_all = sorted(dstat)

    def vr_from(dsel):
        n1 = sum(dstat[d]['n'] for d in dsel)
        s1 = sum(dstat[d]['s'] for d in dsel)
        ss1 = sum(dstat[d]['ss'] for d in dsel)
        v1 = ss1 / n1 - (s1 / n1) ** 2
        out = {}
        for q in QLIST:
            nq = sum(qstat[q][d]['n'] for d in dsel if d in qstat[q])
            if nq < 100:
                out[q] = float('nan'); continue
            sq = sum(qstat[q][d]['s'] for d in dsel if d in qstat[q])
            ssq = sum(qstat[q][d]['ss'] for d in dsel if d in qstat[q])
            vq = ssq / nq - (sq / nq) ** 2
            out[q] = vq / (q * v1) if v1 > 0 else float('nan')
        return out

    obs = vr_from(days_all)
    rnd = random.Random(SEED)
    boots = {q: [] for q in QLIST}
    for _ in range(ITERS):
        sel = [days_all[rnd.randrange(len(days_all))] for _ in days_all]
        vb = vr_from(sel)
        for q in QLIST:
            if vb[q] == vb[q]:
                boots[q].append(vb[q])
    print('  %-6s %8s   %s' % ('q', 'VR(q)', 'day-clustered 95% CI'))
    for q in QLIST:
        b = sorted(boots[q])
        lo, hi = b[int(.025 * len(b))], b[int(.975 * len(b))]
        star = ' <-- RW REJECTED' if (hi < 1.0 or lo > 1.0) else ''
        print('  %-6d %8.4f   [%7.4f, %7.4f]%s' % (q, obs[q], lo, hi, star))

    # VR(15) by RVMR state (state at block start)
    print('\n  VR(15) by RVMR RANGE state of the block-start bar:')
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        sub_d = collections.defaultdict(lambda: {'n': 0, 's': 0.0, 'ss': 0.0})
        sub_q = collections.defaultdict(lambda: {'n': 0, 's': 0.0, 'ss': 0.0})
        for dd, rs in runs.items():
            k = 0
            while k + 15 <= len(rs):
                block = rs[k:k + 15]
                if block[-1][0] - block[0][0] == 14 and RB[block[0][0]] == st:
                    rq = sum(x[1] for x in block)
                    sub_q[dd]['n'] += 1; sub_q[dd]['s'] += rq
                    sub_q[dd]['ss'] += rq * rq
                    for x in block:
                        sub_d[dd]['n'] += 1; sub_d[dd]['s'] += x[1]
                        sub_d[dd]['ss'] += x[1] * x[1]
                    k += 15
                else:
                    k += 1
        dsel = sorted(sub_d)
        n1 = sum(sub_d[d]['n'] for d in dsel)
        if n1 < 1000:
            print('    %-7s insufficient' % st); continue
        s1 = sum(sub_d[d]['s'] for d in dsel); ss1 = sum(sub_d[d]['ss'] for d in dsel)
        v1 = ss1 / n1 - (s1 / n1) ** 2
        nq = sum(sub_q[d]['n'] for d in dsel)
        sq = sum(sub_q[d]['s'] for d in dsel); ssq = sum(sub_q[d]['ss'] for d in dsel)
        vq = ssq / nq - (sq / nq) ** 2
        vr = vq / (15 * v1)
        # bootstrap
        bb = []
        rnd2 = random.Random(SEED)
        for _ in range(2000):
            sel = [dsel[rnd2.randrange(len(dsel))] for _ in dsel]
            n1b = sum(sub_d[d]['n'] for d in sel)
            s1b = sum(sub_d[d]['s'] for d in sel); ss1b = sum(sub_d[d]['ss'] for d in sel)
            nqb = sum(sub_q[d]['n'] for d in sel)
            if not n1b or not nqb: continue
            sqb = sum(sub_q[d]['s'] for d in sel); ssqb = sum(sub_q[d]['ss'] for d in sel)
            v1b = ss1b / n1b - (s1b / n1b) ** 2
            vqb = ssqb / nqb - (sqb / nqb) ** 2
            if v1b > 0: bb.append(vqb / (15 * v1b))
        bb.sort()
        print('    %-7s VR(15) %7.4f  CI [%7.4f, %7.4f]   (n blocks %d)'
              % (st, vr, bb[int(.025 * len(bb))], bb[int(.975 * len(bb))], nq))

    # ================================================= S2 autocorrelation
    print('\n' + '=' * 78)
    print('S2  SERIAL CORRELATION of 1m returns (pooled and by RVMR state)')
    print('=' * 78)

    def ac(rs, lag):
        n = len(rs)
        if n < lag + 100:
            return float('nan')
        m = sum(rs) / n
        num = sum((rs[i] - m) * (rs[i - lag] - m) for i in range(lag, n))
        den = sum((x - m) ** 2 for x in rs)
        return num / den if den > 0 else float('nan')

    pooled = [r for _, r in rets]
    print('  pooled 1m  ' + '  '.join('AC%d %+.4f' % (k, ac(pooled, k))
                                      for k in (1, 2, 3, 5, 10)))
    se = 1.0 / math.sqrt(len(pooled))
    print('  naive iid s.e. %.5f (day clustering widens this; treat AC as'
          ' effect size)' % se)
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        rs = [r for i, r in rets if RB[i] == st]
        print('  %-7s 1m  n %8d  ' % (st, len(rs)) +
              '  '.join('AC%d %+.4f' % (k, ac(rs, k)) for k in (1, 2, 3)))
    # 15m non-overlapping returns
    r15 = []
    for dd, rs in runs.items():
        k = 0
        while k + 15 <= len(rs):
            block = rs[k:k + 15]
            if block[-1][0] - block[0][0] == 14:
                r15.append((block[0][0], sum(x[1] for x in block)))
                k += 15
            else:
                k += 1
    p15 = [r for _, r in r15]
    print('  pooled 15m n %6d  ' % len(p15) +
          '  '.join('AC%d %+.4f' % (k, ac(p15, k)) for k in (1, 2, 3, 4)))
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        rs = [r for i, r in r15 if RB[i] == st]
        print('  %-7s 15m n %6d  ' % (st, len(rs)) +
              '  '.join('AC%d %+.4f' % (k, ac(rs, k)) for k in (1, 2)))

    # ================================================= S3 clock drift
    print('\n' + '=' * 78)
    print('S3  CLOCK DRIFT - mean 1m log return by hour-of-day (bp = 1e-4)')
    print('=' * 78)
    byhr = collections.defaultdict(list)
    for i, r in rets:
        byhr[mod[i] // 60].append((day[i], r))
    print('  %-4s %10s %26s %8s' % ('hr', 'mean bp', 'day-clustered 95% CI',
                                    'n'))
    strong = []
    for hr in sorted(byhr):
        m, (lo, hi) = day_boot_mean(byhr[hr], iters=2000)
        sig = (hi < 0 or lo > 0)
        if sig:
            strong.append((hr, m))
        print('  %-4d %+10.4f   [%+9.4f, %+9.4f]  %8d%s'
              % (hr, m * 1e4, lo * 1e4, hi * 1e4, len(byhr[hr]),
                 '   <-- CI excludes 0' if sig else ''))
    # overnight vs RTH accrual by year
    print('\n  OVERNIGHT (18:00-09:29) vs RTH (09:30-16:00) accrual per year'
          ' (sum of 1m log returns, in %):')
    ovn = collections.defaultdict(float)
    rth = collections.defaultdict(float)
    for i, r in rets:
        y = day[i][:4]
        m_ = mod[i]
        if m_ >= 1081 or m_ <= 569:
            ovn[y] += r
        elif 570 <= m_ <= 960:
            rth[y] += r
    for y in sorted(set(list(ovn) + list(rth))):
        print('    %s  OVERNIGHT %+8.2f%%   RTH %+8.2f%%'
              % (y, 100 * ovn[y], 100 * rth[y]))
    print('    TOTAL OVERNIGHT %+8.2f%%   TOTAL RTH %+8.2f%%'
          % (100 * sum(ovn.values()), 100 * sum(rth.values())))

    # ================================================= S4 minute-of-half-hour
    print('\n' + '=' * 78)
    print('S4  MINUTE-OF-HALF-HOUR signed drift (RTH only, bp)')
    print('=' * 78)
    bymo = collections.defaultdict(list)
    for i, r in rets:
        if 570 <= mod[i] <= 960:
            bymo[mod[i] % 30].append((day[i], r))
    for off in sorted(bymo):
        m, (lo, hi) = day_boot_mean(bymo[off], iters=1000)
        sig = (hi < 0 or lo > 0)
        if sig or off in (0, 1, 29):
            print('  offset %2d  mean %+8.4f bp  CI [%+8.4f, %+8.4f]  n %7d%s'
                  % (off, m * 1e4, lo * 1e4, hi * 1e4, len(bymo[off]),
                     '  <-- CI excludes 0' if sig else ''))

    # ================================================= S5 calendar
    print('\n' + '=' * 78)
    print('S5  CALENDAR - exchange-day return by day-of-week / turn-of-month')
    print('=' * 78)
    dayret = collections.defaultdict(float)
    for i, r in rets:
        dayret[day[i]] += r
    import datetime as dt
    dows = collections.defaultdict(list)
    ds = sorted(dayret)
    for k2, dd in enumerate(ds):
        w = dt.datetime.strptime(dd, '%Y-%m-%d').weekday()
        dows[w].append((dd, dayret[dd]))
    for w, nm in enumerate(('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')):
        if w not in dows:
            continue
        m, (lo, hi) = day_boot_mean(dows[w], iters=2000)
        print('  %-4s n %4d  mean %+7.2f bp  CI [%+7.2f, %+7.2f]%s'
              % (nm, len(dows[w]), m * 1e4, lo * 1e4, hi * 1e4,
                 '  <-- CI excludes 0' if (hi < 0 or lo > 0) else ''))
    # turn of month: last 2 + first 3 trading days
    months = collections.defaultdict(list)
    for dd in ds:
        months[dd[:7]].append(dd)
    tom = set()
    mk = sorted(months)
    for j, mm in enumerate(mk):
        tom.update(months[mm][-2:])
        tom.update(months[mm][:3])
    a = [(dd, dayret[dd]) for dd in ds if dd in tom]
    b = [(dd, dayret[dd]) for dd in ds if dd not in tom]
    ma, (la, ha) = day_boot_mean(a, iters=2000)
    mb, (lb, hb) = day_boot_mean(b, iters=2000)
    print('  TURN-OF-MONTH n %4d  mean %+7.2f bp CI [%+7.2f,%+7.2f]'
          % (len(a), ma * 1e4, la * 1e4, ha * 1e4))
    print('  OTHER DAYS    n %4d  mean %+7.2f bp CI [%+7.2f,%+7.2f]'
          % (len(b), mb * 1e4, lb * 1e4, hb * 1e4))

    # ================================================= S6 OU half-life
    print('\n' + '=' * 78)
    print('S6  OU HALF-LIFE of (close - session VWAP), RTH sessions')
    print('=' * 78)
    vw = SP.SessionVwap()
    dev = [None] * N
    for i in range(N):
        vw.update(em[i], h[i], l[i], c[i], v[i])
        vv = vw.vwap
        if vv is not None:
            dev[i] = c[i] - vv
    hls = []
    day_rr = collections.defaultdict(list)
    for i in idx:
        if rr[i] is not None:
            day_rr[day[i]].append(rr[i])
    sess = collections.defaultdict(list)
    for i in idx:
        if 570 <= mod[i] <= 960 and dev[i] is not None:
            sess[day[i]].append((i, dev[i]))
    for dd, xs in sess.items():
        if len(xs) < 200:
            continue
        num = den = 0.0
        for k2 in range(1, len(xs)):
            if xs[k2][0] - xs[k2 - 1][0] != 1:
                continue
            num += xs[k2][1] * xs[k2 - 1][1]
            den += xs[k2 - 1][1] ** 2
        if den <= 0:
            continue
        phi = num / den
        if 0 < phi < 1:
            hl = -math.log(2) / math.log(phi)
            hls.append((dd, hl, med(day_rr.get(dd, [1.0]))))
    hlv = [x[1] for x in hls]
    print('  sessions %d   half-life median %.1f min   p25 %.1f   p75 %.1f'
          % (len(hls), med(hlv), sorted(hlv)[len(hlv) // 4],
             sorted(hlv)[3 * len(hlv) // 4]))
    hs = sorted(hls, key=lambda x: x[2])
    t1, t2 = hs[len(hs) // 3][2], hs[2 * len(hs) // 3][2]
    for nm2, sel in (('day rr-score LOW terc', [x for x in hls if x[2] < t1]),
                     ('day rr-score MID terc', [x for x in hls if t1 <= x[2] <= t2]),
                     ('day rr-score HIGH terc', [x for x in hls if x[2] > t2])):
        print('    %-24s n %4d  median HL %6.1f min'
              % (nm2, len(sel), med([x[1] for x in sel])))

    # ================================================= S7 sign entropy
    print('\n' + '=' * 78)
    print('S7  SIGN-SEQUENCE 5-BIT BLOCK ENTROPY (max 5.0000 bits)')
    print('=' * 78)

    def entropy5(sgns):
        cnt = collections.Counter()
        for k2 in range(0, len(sgns) - 4, 5):
            cnt[tuple(sgns[k2:k2 + 5])] += 1
        tot = sum(cnt.values())
        if tot < 200:
            return float('nan'), tot
        e = -sum((n2 / tot) * math.log(n2 / tot, 2) for n2 in cnt.values())
        return e, tot

    allsg = [1 if r > 0 else 0 for _, r in rets if r != 0]
    e, tot = entropy5(allsg)
    print('  pooled     entropy %.4f bits  (deficit %.4f)  blocks %d'
          % (e, 5.0 - e, tot))
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        sg = [1 if r > 0 else 0 for i, r in rets if r != 0 and RB[i] == st]
        e, tot = entropy5(sg)
        print('  %-9s  entropy %.4f bits  (deficit %.4f)  blocks %d'
              % (st, e, 5.0 - e, tot))
    for nm2, a2, b2 in (('OPEN', 570, 630), ('MIDDAY', 720, 810),
                        ('OVERNIGHT', 1081, 1440)):
        sg = [1 if r > 0 else 0 for i, r in rets
              if r != 0 and a2 <= mod[i] < b2]
        e, tot = entropy5(sg)
        print('  %-9s  entropy %.4f bits  (deficit %.4f)  blocks %d'
              % (nm2, e, 5.0 - e, tot))

    # ================================================= S8 Hill tail
    print('\n' + '=' * 78)
    print('S8  HILL TAIL INDEX of |15m| moves (top 5%%; higher = thinner tail)')
    print('=' * 78)

    def hill(vals):
        x = sorted(abs(a2) for a2 in vals if a2 != 0)
        k2 = max(50, int(0.05 * len(x)))
        top = x[-k2:]
        xm = top[0]
        s = sum(math.log(t / xm) for t in top[1:])
        return (k2 - 1) / s if s > 0 else float('nan'), k2

    a0, k0 = hill(p15)
    print('  pooled   alpha %.3f  (k %d)' % (a0, k0))
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        rs = [r for i, r in r15 if RB[i] == st]
        if len(rs) < 2000:
            print('  %-8s insufficient' % st); continue
        a2, k2 = hill(rs)
        print('  %-8s alpha %.3f  (k %d, n %d)' % (st, a2, k2, len(rs)))

    print('\n' + '=' * 78)
    print('SCAN COMPLETE - DISCOVERY WINDOW ONLY. EVERYTHING EXPLORATORY.')
    print('HOLDOUT (>= 2024-01-01) UNTOUCHED BY THIS SCAN.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
    print('=' * 78)


if __name__ == '__main__':
    main()
