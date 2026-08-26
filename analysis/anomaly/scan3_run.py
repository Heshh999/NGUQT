#!/usr/bin/env python3
# ======================================================================
# ANOMALY-SCAN-V1 WAVE 3 - direction/trend machinery, DISCOVERY ONLY
# ======================================================================
# Menu frozen first at commit b054a00c71255a74be908df001ee157fbf8c3b0f
# (protocol sha256 3b8f13a8ad6180e91924a3ee66beef18b1e9ed48146c99a6cba1
# 9709e027fbb8). Discovery <= 2023-12-31. Holdout >= 2024-01-01 is NEVER
# read for any statistic in this file.
#
# EXCLUSION ZONE (binding): the frozen, unexecuted RVMR-MOMENTUM-V1
# objects - sign(5m trailing return) x 5m forward and sign(30m trailing
# return) x 15m forward, pooled or by state, and their declared
# baselines - are NOT computed anywhere here. No statistic conditions on
# a trailing 5m or 30m return sign; no statistic uses the 30m/15m
# pairing. S28's 60m/30m adjacency is declared in the frozen menu.
#
# EXPLORATORY / HYPOTHESIS-GENERATING. SUBMITS NO ORDERS.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, math, random, collections, time

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../rvmr', '../dvt'):
    sys.path.insert(0, os.path.join(HERE, p))
import rvmr_spec as RS
import rvmr_run as RV
import dvt_spec as SP

DISC_END = '2023-12-31'
SEED = 20260826
B_MAIN, B_CELL = 5000, 1000
BP = 1e4
STN = ('LOW', 'MEDIUM', 'HIGH')


def mean(x):
    return sum(x) / len(x) if x else float('nan')


def med(x):
    s = sorted(x)
    return s[len(s) // 2] if s else float('nan')


def day_boot_mean(pairs, iters=B_CELL, seed=SEED):
    by = collections.defaultdict(lambda: [0.0, 0])
    for d, v in pairs:
        e = by[d]; e[0] += v; e[1] += 1
    bl = [tuple(x) for x in by.values()]
    nb = len(bl)
    if nb < 15:
        return mean([v for _, v in pairs]), float('nan'), float('nan')
    obs = sum(b[0] for b in bl) / sum(b[1] for b in bl)
    rnd = random.Random(seed); rr = rnd.randrange
    out = []
    for _ in range(iters):
        s = 0.0; n = 0
        for _ in range(nb):
            b = bl[rr(nb)]
            s += b[0]; n += b[1]
        if n:
            out.append(s / n)
    out.sort()
    m = len(out)
    return obs, out[int(.025 * m)], out[int(.975 * m)]


def day_boot_diff(blocks, iters=B_MAIN, seed=SEED):
    """blocks: {day: [sA,nA,sB,nB]} -> A-B ratio-of-sums diff, CI, p."""
    bl = [tuple(x) for x in blocks.values()]
    nb = len(bl)
    NA = sum(b[1] for b in bl); NB = sum(b[3] for b in bl)
    if not NA or not NB or nb < 15:
        return float('nan'), float('nan'), float('nan'), float('nan')
    obs = sum(b[0] for b in bl) / NA - sum(b[2] for b in bl) / NB
    rnd = random.Random(seed); rr = rnd.randrange
    out = []
    for _ in range(iters):
        sa = sb = 0.0; na = nb2 = 0
        for _ in range(nb):
            b = bl[rr(nb)]
            sa += b[0]; na += b[1]; sb += b[2]; nb2 += b[3]
        if na and nb2:
            out.append(sa / na - sb / nb2)
    out.sort()
    m = len(out)
    lo, hi = out[int(.025 * m)], out[int(.975 * m)]
    le = sum(1 for x in out if x <= 0)
    ge = sum(1 for x in out if x >= 0)
    pv = max(2.0 * min(le, ge) / m, 1.0 / (m + 1.0))
    return obs, lo, hi, pv


def main():
    t0 = time.time()
    print('=' * 78)
    print('ANOMALY-SCAN-V1  WAVE 3   DISCOVERY <= %s ONLY' % DISC_END)
    print('  menu frozen at commit b054a00c before computation, seed %d'
          % SEED)
    print('  EXCLUSION ZONE ACTIVE: frozen RVMR-MOMENTUM-V1 objects not'
          ' computed')
    print('  EXPLORATORY. SUBMITS NO ORDERS.')
    print('=' * 78)
    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    N = len(D['c'])
    o, h, l, c, v, em, mod, day = (D['o'], D['h'], D['l'], D['c'], D['v'],
                                   D['em'], D['mod'], D['day'])
    rr_ = RS.trailing_ratio([h[i] - l[i] for i in range(N)])
    RB = [RS.bucket(x) if x is not None else None for x in rr_]
    LAST = max(i for i in range(N) if day[i] <= DISC_END)
    print('discovery bars %d of %d   last discovery index %d (%s)'
          % (sum(1 for i in range(N) if day[i] <= DISC_END), N, LAST,
             day[LAST]))

    # per-bar 1m return (contiguous only), sign
    rarr = [None] * N
    for i in range(1, N):
        if em[i] - em[i - 1] == 1 and c[i - 1] > 0 and c[i] > 0:
            rarr[i] = math.log(c[i] / c[i - 1])

    def fwd(t, K):
        """log forward return over t+1..t+K, contiguous, inside discovery."""
        if t + K > LAST or em[t + K] - em[t] != K:
            return None
        return math.log(c[t + K] / c[t])

    # ================================================== S23 RUN HAZARD
    print('\n' + '=' * 78)
    print('S23  DIRECTIONAL RUN HAZARD  h(k) = P(run continues | length k)')
    print('     flat hazard = martingale; zero return or gap terminates')
    print('=' * 78)
    KMAX = 9
    opp = [[0] * (KMAX + 1) for _ in range(4)]     # 0..2 states, 3 pooled
    cont = [[0] * (KMAX + 1) for _ in range(4)]
    hz_days = {}                                    # day -> [c3,o3,c1,o1]
    smap = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
    st_hz = {nm: {} for nm in STN}
    cur_s, cur_k = 0, 0
    for i in range(1, LAST + 1):
        if day[i] > DISC_END:
            continue
        ri = rarr[i]
        if ri is None or ri == 0.0:
            cur_k = 0
            continue
        sgn = 1 if ri > 0 else -1
        cur_k = cur_k + 1 if sgn == cur_s else 1
        cur_s = sgn
        rn = rarr[i + 1] if i + 1 <= LAST else None
        if rn is None or rn == 0.0 or day[i + 1] > DISC_END:
            continue
        k = min(cur_k, KMAX)
        good = 1 if ((rn > 0) == (sgn > 0)) else 0
        opp[3][k] += 1; cont[3][k] += good
        sb = RB[i]
        if sb is not None:
            si = smap[sb]
            opp[si][k] += 1; cont[si][k] += good
        e = hz_days.setdefault(day[i], [0, 0, 0, 0])
        if cur_k >= 3:
            e[0] += good; e[1] += 1
        elif cur_k == 1:
            e[2] += good; e[3] += 1
        if sb is not None:
            e2 = st_hz[sb].setdefault(day[i], [0, 0, 0, 0])
            if cur_k >= 3:
                e2[0] += good; e2[1] += 1
            elif cur_k == 1:
                e2[2] += good; e2[3] += 1
    print('  %-4s' % 'k' + ''.join('%10s' % nm for nm in
                                   ('pooled', 'LOW', 'MEDIUM', 'HIGH')))
    for k in range(1, KMAX + 1):
        lab = '%d' % k if k < KMAX else '%d+' % KMAX
        row = ''
        for gi in (3, 0, 1, 2):
            row += ('%10.4f' % (cont[gi][k] / opp[gi][k])
                    if opp[gi][k] >= 200 else '%10s' % '-')
        print('  %-4s%s   (n pooled %d)' % (lab, row, opp[3][k]))
    dd, lo, hi, pv = day_boot_diff(hz_days)
    print('\n  HEADLINE h(3+) - h(1) pooled  %+0.4f   CI [%+0.4f, %+0.4f]'
          '   p %.5f' % (dd, lo, hi, pv))
    for nm in STN:
        dd2, lo2, hi2, _ = day_boot_diff(st_hz[nm], iters=2000)
        print('    %-7s h(3+) - h(1)  %+0.4f   CI [%+0.4f, %+0.4f]'
              % (nm, dd2, lo2, hi2))

    # 15m block runs
    rets = [(i, rarr[i]) for i in range(1, LAST + 1)
            if rarr[i] is not None and day[i] <= DISC_END]
    runs = collections.defaultdict(list)
    for i, r in rets:
        runs[day[i]].append((i, r))
    r15 = []
    for dd_ in sorted(runs):
        rs = runs[dd_]; k = 0
        while k + 15 <= len(rs):
            bk = rs[k:k + 15]
            if bk[-1][0] - bk[0][0] == 14:
                r15.append((bk[0][0], bk[-1][0], sum(x[1] for x in bk)))
                k += 15
            else:
                k += 1
    bopp = [[0] * 5 for _ in range(4)]
    bcont = [[0] * 5 for _ in range(4)]
    cur_s, cur_k = 0, 0
    for a in range(len(r15) - 1):
        i0, i1, rv = r15[a]
        j0, j1, rf = r15[a + 1]
        if j0 - i1 != 1 or rv == 0.0:
            cur_k = 0
            continue
        sgn = 1 if rv > 0 else -1
        cur_k = cur_k + 1 if sgn == cur_s else 1
        cur_s = sgn
        if rf == 0.0:
            continue
        k = min(cur_k, 4)
        good = 1 if ((rf > 0) == (sgn > 0)) else 0
        bcont[3][k] += 1 if good else 0; bopp[3][k] += 1
        sb = RB[i0]
        if sb is not None:
            bcont[smap[sb]][k] += good; bopp[smap[sb]][k] += 1
    print('\n  15m BLOCK RUNS  (k, pooled hazard, n):')
    for k in range(1, 5):
        lab = '%d' % k if k < 4 else '4+'
        print('    k=%-3s pooled %.4f (n %d)   LOW %.4f  MED %.4f  HIGH %s'
              % (lab, bcont[3][k] / bopp[3][k] if bopp[3][k] else float('nan'),
                 bopp[3][k],
                 bcont[0][k] / bopp[0][k] if bopp[0][k] > 100 else float('nan'),
                 bcont[1][k] / bopp[1][k] if bopp[1][k] > 100 else float('nan'),
                 '%.4f' % (bcont[2][k] / bopp[2][k]) if bopp[2][k] > 100
                 else '-'))
    print('  (%.0f s)' % (time.time() - t0))

    # ================================================== S24 ORDINAL MOTIFS
    print('\n' + '=' * 78)
    print('S24  ORDINAL 3-MOTIFS of closes (Bandt-Pompe; ties skipped)')
    print('=' * 78)
    PATS = ('012', '021', '102', '120', '201', '210')
    mot_n = collections.Counter()
    mot_up = collections.Counter()
    mot_nz = collections.Counter()
    mot_sum = collections.defaultdict(float)
    mot_state = collections.defaultdict(float)
    mot_state_n = collections.Counter()
    ad_days = {}
    for t in range(2, LAST):
        if day[t + 1] > DISC_END or em[t] - em[t - 2] != 2 \
                or em[t + 1] - em[t] != 1:
            continue
        x0, x1, x2 = c[t - 2], c[t - 1], c[t]
        if x0 == x1 or x1 == x2 or x0 == x2:
            continue
        order = sorted(range(3), key=lambda j: (x0, x1, x2)[j])
        pat = ''.join(str(j) for j in order)
        rn = rarr[t + 1]
        if rn is None:
            continue
        mot_n[pat] += 1
        mot_sum[pat] += rn
        if rn != 0.0:
            mot_nz[pat] += 1
            if rn > 0:
                mot_up[pat] += 1
        sb = RB[t]
        if sb is not None:
            mot_state[(pat, sb)] += rn
            mot_state_n[(pat, sb)] += 1
        if pat in ('012', '210'):
            e = ad_days.setdefault(day[t + 1], [0.0, 0, 0.0, 0])
            if pat == '012':
                e[0] += rn; e[1] += 1
            else:
                e[2] += rn; e[3] += 1
    tot = sum(mot_n.values())
    print('  pattern encoding: indices of sorted closes; 012 = ascending'
          ' (x0<x1<x2), 210 = descending')
    print('  %-5s %9s %8s %10s %12s' % ('pat', 'n', 'freq', 'P(up)',
                                        'E[r+1] bp'))
    for pat in PATS:
        print('  %-5s %9d %8.4f %10.4f %+12.4f'
              % (pat, mot_n[pat], mot_n[pat] / tot,
                 mot_up[pat] / mot_nz[pat] if mot_nz[pat] else float('nan'),
                 mot_sum[pat] / mot_n[pat] * BP if mot_n[pat] else 0))
    dd, lo, hi, pv = day_boot_diff(ad_days)
    print('\n  HEADLINE E[r|ascending 012] - E[r|descending 210]'
          '  %+0.4f bp   CI [%+0.4f, %+0.4f]   p %.5f'
          % (dd * BP, lo * BP, hi * BP, pv))
    print('\n  motif mean E[r+1] bp by state:')
    print('  %-5s %10s %10s %10s' % ('pat', 'LOW', 'MEDIUM', 'HIGH'))
    for pat in PATS:
        row = ''
        for nm in STN:
            n2 = mot_state_n[(pat, nm)]
            row += ('%+10.4f' % (mot_state[(pat, nm)] / n2 * BP)
                    if n2 > 5000 else '%10s' % '-')
        print('  %-5s %s' % (pat, row))
    print('  disclosure: the last-leg sign marginal duplicates the exposed'
          ' lag-1 result.')
    print('  the incremental content is CROSS-motif structure at a FIXED'
          ' last leg:')
    print('    last leg UP   = x2 > x1 = motifs {012, 102, 120}')
    print('    last leg DOWN = x2 < x1 = motifs {021, 201, 210}')
    print('  (%.0f s)' % (time.time() - t0))

    # ================================================== S25 RANGE POSITION
    print('\n' + '=' * 78)
    print('S25  RANGE-POSITION RESPONSE  PosR (60m Donchian) -> fwd 30m')
    print('=' * 78)
    dq_hi = collections.deque()
    dq_lo = collections.deque()
    seg = 0
    cells25 = collections.defaultdict(list)
    cells25s = collections.defaultdict(list)
    for i in range(1, LAST + 1):
        if em[i] - em[i - 1] != 1:
            dq_hi.clear(); dq_lo.clear(); seg = i
        while dq_hi and h[dq_hi[-1]] <= h[i]:
            dq_hi.pop()
        dq_hi.append(i)
        while dq_lo and l[dq_lo[-1]] >= l[i]:
            dq_lo.pop()
        dq_lo.append(i)
        while dq_hi[0] < i - 59:
            dq_hi.popleft()
        while dq_lo[0] < i - 59:
            dq_lo.popleft()
        if i - seg < 59 or day[i] > DISC_END:
            continue
        hh, ll = h[dq_hi[0]], l[dq_lo[0]]
        if hh <= ll:
            continue
        pos = (c[i] - ll) / (hh - ll)
        f = fwd(i, 30)
        if f is None:
            continue
        dc = min(int(pos * 10), 9)
        cells25[dc].append((day[i + 30], f))
        sb = RB[i]
        if sb is not None and dc in (0, 9):
            cells25s[(dc, sb)].append((day[i + 30], f))
    print('  %-6s %9s %12s %26s' % ('decile', 'n', 'fwd30 bp',
                                    'day-clustered 95% CI'))
    for dc in range(10):
        sub = cells25[dc]
        m, lo, hi = day_boot_mean(sub, iters=B_CELL)
        sig = (lo > 0 or hi < 0) and lo == lo
        print('  %-6d %9d %+12.4f   [%+9.4f, %+9.4f]%s'
              % (dc, len(sub), m * BP, lo * BP, hi * BP,
                 '  <-- CI excludes 0' if sig else ''))
    print('  extreme deciles by state (fwd30 bp):')
    for dc in (0, 9):
        for nm in STN:
            sub = cells25s.get((dc, nm), [])
            if len(sub) < 300:
                continue
            m, lo, hi = day_boot_mean(sub, iters=B_CELL)
            print('    dec %d %-7s n %7d  %+9.4f  [%+9.4f, %+9.4f]'
                  % (dc, nm, len(sub), m * BP, lo * BP, hi * BP))
    print('  (%.0f s)' % (time.time() - t0))

    # ================================================== S26 EXTREME AGING
    print('\n' + '=' * 78)
    print('S26  EXTREME AGING  a = ageOfHigh - ageOfLow (240m, ties->recent)')
    print('     a < 0: high is FRESHER (recent strength)')
    print('=' * 78)
    dq_hi.clear(); dq_lo.clear(); seg = 0
    BINS = ((-239, -180), (-179, -90), (-89, -30), (-29, -1), (0, 0),
            (1, 29), (30, 89), (90, 179), (180, 239))
    cells26 = collections.defaultdict(list)
    ag_days = {}
    ag_days_st = {nm: {} for nm in STN}
    for i in range(1, LAST + 1):
        if em[i] - em[i - 1] != 1:
            dq_hi.clear(); dq_lo.clear(); seg = i
        while dq_hi and h[dq_hi[-1]] <= h[i]:
            dq_hi.pop()
        dq_hi.append(i)
        while dq_lo and l[dq_lo[-1]] >= l[i]:
            dq_lo.pop()
        dq_lo.append(i)
        while dq_hi[0] < i - 239:
            dq_hi.popleft()
        while dq_lo[0] < i - 239:
            dq_lo.popleft()
        if i - seg < 239 or day[i] > DISC_END:
            continue
        a = (i - dq_hi[0]) - (i - dq_lo[0])
        f = fwd(i, 30)
        if f is None:
            continue
        for bi, (a0, a1) in enumerate(BINS):
            if a0 <= a <= a1:
                cells26[bi].append((day[i + 30], f))
                break
        if a <= -30 or a >= 30:
            e = ag_days.setdefault(day[i + 30], [0.0, 0, 0.0, 0])
            if a <= -30:
                e[0] += f; e[1] += 1
            else:
                e[2] += f; e[3] += 1
            sb = RB[i]
            if sb is not None:
                e2 = ag_days_st[sb].setdefault(day[i + 30], [0.0, 0, 0.0, 0])
                if a <= -30:
                    e2[0] += f; e2[1] += 1
                else:
                    e2[2] += f; e2[3] += 1
    print('  %-14s %9s %12s' % ('a bin', 'n', 'fwd30 bp'))
    for bi, (a0, a1) in enumerate(BINS):
        sub = cells26.get(bi, [])
        print('  [%4d,%4d]   %9d %+12.4f'
              % (a0, a1, len(sub), mean([x[1] for x in sub]) * BP
                 if sub else float('nan')))
    dd, lo, hi, pv = day_boot_diff(ag_days)
    print('\n  HEADLINE fresh-high (a<=-30) - fresh-low (a>=+30)'
          '  %+0.4f bp   CI [%+0.4f, %+0.4f]   p %.5f'
          % (dd * BP, lo * BP, hi * BP, pv))
    for nm in STN:
        dd2, lo2, hi2, _ = day_boot_diff(ag_days_st[nm], iters=2000)
        print('    %-7s %+0.4f bp   CI [%+0.4f, %+0.4f]'
              % (nm, dd2 * BP, lo2 * BP, hi2 * BP))
    print('  (%.0f s)' % (time.time() - t0))

    # ================================================== S27 VWAP OCCUPANCY
    print('\n' + '=' * 78)
    print('S27  VWAP-SIDE OCCUPANCY (60m) -> fwd 60m  (OU-informed horizon)')
    print('=' * 78)
    vw = SP.SessionVwap()
    ind = [None] * N
    for i in range(N):
        vw.update(em[i], h[i], l[i], c[i], v[i])
        if vw.vwap is not None:
            ind[i] = 1 if c[i] > vw.vwap else 0
    P1 = [0] * (N + 1); PN = [0] * (N + 1)
    for i in range(N):
        P1[i + 1] = P1[i] + (ind[i] or 0)
        PN[i + 1] = PN[i] + (1 if ind[i] is None else 0)
    cells27 = collections.defaultdict(list)
    oc_days = {}
    oc_days_st = {nm: {} for nm in STN}
    for i in range(60, LAST + 1):
        if day[i] > DISC_END or em[i] - em[i - 59] != 59:
            continue
        if PN[i + 1] - PN[i - 59] != 0:
            continue
        occ = (P1[i + 1] - P1[i - 59]) / 60.0
        f = fwd(i, 60)
        if f is None:
            continue
        if occ == 0.0:
            b = 'occ=0'
        elif occ == 1.0:
            b = 'occ=1'
        else:
            b = '(%0.1f,%0.1f]' % (math.floor(occ * 10) / 10,
                                   math.floor(occ * 10) / 10 + 0.1)
        cells27[b].append((day[i + 60], f))
        if occ in (0.0, 1.0):
            e = oc_days.setdefault(day[i + 60], [0.0, 0, 0.0, 0])
            if occ == 1.0:
                e[0] += f; e[1] += 1
            else:
                e[2] += f; e[3] += 1
            sb = RB[i]
            if sb is not None:
                e2 = oc_days_st[sb].setdefault(day[i + 60],
                                               [0.0, 0, 0.0, 0])
                if occ == 1.0:
                    e2[0] += f; e2[1] += 1
                else:
                    e2[2] += f; e2[3] += 1
    order27 = ['occ=0'] + ['(%0.1f,%0.1f]' % (k / 10, k / 10 + 0.1)
                           for k in range(10)] + ['occ=1']
    print('  %-12s %9s %12s' % ('bin', 'n', 'fwd60 bp'))
    for b in order27:
        sub = cells27.get(b, [])
        if not sub:
            continue
        print('  %-12s %9d %+12.4f'
              % (b, len(sub), mean([x[1] for x in sub]) * BP))
    dd, lo, hi, pv = day_boot_diff(oc_days)
    print('\n  HEADLINE E[fwd60 | occ=1] - E[fwd60 | occ=0]'
          '  %+0.4f bp   CI [%+0.4f, %+0.4f]   p %.5f'
          % (dd * BP, lo * BP, hi * BP, pv))
    for nm in STN:
        dd2, lo2, hi2, _ = day_boot_diff(oc_days_st[nm], iters=2000)
        print('    %-7s %+0.4f bp   CI [%+0.4f, %+0.4f]'
              % (nm, dd2 * BP, lo2 * BP, hi2 * BP))
    print('  (%.0f s)' % (time.time() - t0))

    # ================================================== S28 OBV DIVERGENCE
    print('\n' + '=' * 78)
    print('S28  OBV-PRICE DIVERGENCE (60m trail -> 30m fwd; declared')
    print('     timeframe-neighbour of frozen momentum objects)')
    print('=' * 78)
    SV = [0.0] * (N + 1)
    for i in range(N):
        ri = rarr[i]
        SV[i + 1] = SV[i] + ((v[i] if ri > 0 else (-v[i] if ri < 0 else 0.0))
                             if ri is not None else 0.0)
    cells28 = collections.defaultdict(list)
    dv_days = {}
    dv_days_st = {nm: {} for nm in STN}
    for i in range(60, LAST + 1):
        if day[i] > DISC_END or em[i] - em[i - 60] != 60:
            continue
        dP = c[i] - c[i - 60]
        if dP == 0:
            continue
        dV = SV[i + 1] - SV[i - 59]
        f = fwd(i, 30)
        if f is None:
            continue
        al = f if dP > 0 else -f
        conf = (dV > 0) == (dP > 0)
        cells28[('up' if dP > 0 else 'dn', 'confirm' if conf else
                 'diverge')].append((day[i + 30], al))
        e = dv_days.setdefault(day[i + 30], [0.0, 0, 0.0, 0])
        if conf:
            e[0] += al; e[1] += 1
        else:
            e[2] += al; e[3] += 1
        sb = RB[i]
        if sb is not None:
            e2 = dv_days_st[sb].setdefault(day[i + 30], [0.0, 0, 0.0, 0])
            if conf:
                e2[0] += al; e2[1] += 1
            else:
                e2[2] += al; e2[3] += 1
    print('  %-4s %-9s %9s %14s' % ('dP', 'volume', 'n', 'aligned30 bp'))
    for key in (('up', 'confirm'), ('up', 'diverge'), ('dn', 'confirm'),
                ('dn', 'diverge')):
        sub = cells28.get(key, [])
        print('  %-4s %-9s %9d %+14.4f'
              % (key[0], key[1], len(sub),
                 mean([x[1] for x in sub]) * BP if sub else float('nan')))
    dd, lo, hi, pv = day_boot_diff(dv_days)
    print('\n  HEADLINE confirm - diverge (pooled, aligned30)'
          '  %+0.4f bp   CI [%+0.4f, %+0.4f]   p %.5f'
          % (dd * BP, lo * BP, hi * BP, pv))
    for nm in STN:
        dd2, lo2, hi2, _ = day_boot_diff(dv_days_st[nm], iters=2000)
        print('    %-7s %+0.4f bp   CI [%+0.4f, %+0.4f]'
              % (nm, dd2 * BP, lo2 * BP, hi2 * BP))
    print('  (%.0f s)' % (time.time() - t0))

    # ================================================== S29 DAILY TSMOM
    print('\n' + '=' * 78)
    print('S29  DAILY TIME-SERIES MOMENTUM  lags {1, 5, 20} (complete set)')
    print('=' * 78)
    dayret = collections.defaultdict(float)
    day_sc = collections.defaultdict(list)
    for i in range(1, LAST + 1):
        if day[i] > DISC_END or rarr[i] is None:
            continue
        dayret[day[i]] += rarr[i]
        if rr_[i] is not None:
            day_sc[day[i]].append(rr_[i])
    ds = sorted(dayret)
    dmed = {d: med(day_sc[d]) for d in ds if day_sc[d]}
    svals = sorted(dmed.values())
    t1_, t2_ = svals[len(svals) // 3], svals[2 * len(svals) // 3]
    for L in (1, 5, 20):
        al = []
        for k in range(L, len(ds) - 1):
            pred = sum(dayret[ds[j]] for j in range(k - L + 1, k + 1))
            if pred == 0:
                continue
            nxt = dayret[ds[k + 1]]
            al.append((ds[k], (1 if pred > 0 else -1) * nxt))
        rnd = random.Random(SEED)
        vals = [x[1] for x in al]
        nb = len(vals)
        out = []
        for _ in range(2000):
            s = 0.0
            for _ in range(nb):
                s += vals[rnd.randrange(nb)]
            out.append(s / nb)
        out.sort()
        pm = mean([1 if x > 0 else 0 for x in vals if x != 0])
        print('  L=%-3d n %4d  aligned %+8.2f bp/day  CI [%+8.2f, %+8.2f]'
              '  P(match) %.4f'
              % (L, nb, mean(vals) * BP, out[int(.025 * len(out))] * BP,
                 out[int(.975 * len(out))] * BP, pm))
        for nm, sel in (('LOW terc', lambda d: dmed.get(d, 9) < t1_),
                        ('MID terc', lambda d: t1_ <= dmed.get(d, 9) <= t2_),
                        ('HIGH terc', lambda d: dmed.get(d, -9) > t2_)):
            sub = [x[1] for x in al if sel(x[0])]
            if len(sub) > 50:
                print('      day-score %-9s n %4d  aligned %+8.2f bp'
                      % (nm, len(sub), mean(sub) * BP))
    print('  (%.0f s)' % (time.time() - t0))

    # ================================================== S30 HALF-SESSION
    print('\n' + '=' * 78)
    print('S30  HALF-SESSION PERSISTENCE  sign(09:31-12:00) x (12:01-16:00)')
    print('=' * 78)
    am = collections.defaultdict(float); am_n = collections.Counter()
    pm_ = collections.defaultdict(float); pm_n = collections.Counter()
    noonRB = {}
    for i in range(1, LAST + 1):
        if day[i] > DISC_END or rarr[i] is None:
            continue
        m_ = mod[i]
        if 571 <= m_ <= 720:
            am[day[i]] += rarr[i]; am_n[day[i]] += 1
            noonRB[day[i]] = RB[i]
        elif 721 <= m_ <= 960:
            pm_[day[i]] += rarr[i]; pm_n[day[i]] += 1
    al = []
    for d in sorted(am):
        if am_n[d] >= 120 and pm_n[d] >= 180 and am[d] != 0:
            al.append((d, (1 if am[d] > 0 else -1) * pm_[d],
                       noonRB.get(d), dmed.get(d)))
    vals = [x[1] for x in al]
    rnd = random.Random(SEED)
    out = []
    for _ in range(2000):
        s = 0.0
        for _ in range(len(vals)):
            s += vals[rnd.randrange(len(vals))]
        out.append(s / len(vals))
    out.sort()
    pmch = mean([1 if x > 0 else 0 for x in vals if x != 0])
    print('  n days %d   aligned PM %+8.2f bp   CI [%+8.2f, %+8.2f]'
          '   P(match) %.4f'
          % (len(vals), mean(vals) * BP, out[int(.025 * len(out))] * BP,
             out[int(.975 * len(out))] * BP, pmch))
    for nm in STN:
        sub = [x[1] for x in al if x[2] == nm]
        if len(sub) > 50:
            print('    noon RB=%-7s n %4d  aligned %+8.2f bp  P(match) %.4f'
                  % (nm, len(sub), mean(sub) * BP,
                     mean([1 if x > 0 else 0 for x in sub if x != 0])))
    for nm, sel in (('LOW terc', lambda s: s is not None and s < t1_),
                    ('MID terc', lambda s: s is not None and t1_ <= s <= t2_),
                    ('HIGH terc', lambda s: s is not None and s > t2_)):
        sub = [x[1] for x in al if sel(x[3])]
        if len(sub) > 50:
            print('    day-score %-9s n %4d  aligned %+8.2f bp'
                  % (nm, len(sub), mean(sub) * BP))

    print('\n' + '=' * 78)
    print('WAVE 3 COMPLETE - DISCOVERY ONLY. HOLDOUT UNTOUCHED BY THIS'
          ' SCAN.')
    print('EXCLUSION ZONE RESPECTED: no frozen RVMR-MOMENTUM-V1 object'
          ' computed.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.  (%.0f s)'
          % (time.time() - t0))
    print('=' * 78)


if __name__ == '__main__':
    main()
