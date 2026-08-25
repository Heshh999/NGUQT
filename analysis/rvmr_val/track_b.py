#!/usr/bin/env python3
# ======================================================================
# RVMR-VALIDATION-V1  TRACK B - RVMR-INCR-V1
#   DOES RVMR KNOW ANYTHING ATR DOES NOT ALREADY KNOW?
# ======================================================================
# Pre-registered at docs/RVMR_VALIDATION_V1_PREREGISTRATION.md
#   sha256 025598ad685e617ca8ea4d2d044be52e38343de22ac2db899a22958ea4b161c3
#
# ONE primary ATR definition, frozen before execution: ATR20.
# ATR STATE = trailing_ratio(ATR20) - the IDENTICAL construction RVMR
# uses - so no RVMR advantage can come from RVMR being relative while
# ATR is absolute. Quintiles, cutpoints from the FIRST FULL YEAR only.
#
# NO ML. NO quadratics, interactions, splines, feature selection or lag
# sweeps - before or after seeing any result.
#
# THIS MODULE SUBMITS NO ORDERS. NO LIVE TRADING IS AUTHORIZED.
# ======================================================================

import os, sys, math, random, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import val_lib as L
import rvmr_spec as S

TOOLS = (('rb', 'rr', 'RANGE-REGIME-V1'), ('vb', 'vr', 'VOLUME-REGIME-V1'))
NQ = 5          # ATR quintiles


def rank(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    for pos, i in enumerate(order):
        r[i] = pos
    return r


def ols(y, X, names):
    """Plain OLS by normal equations. No regularization, no selection."""
    k = len(X)
    n = len(y)
    A = [[sum(X[a][i] * X[b][i] for i in range(n)) for b in range(k)]
         for a in range(k)]
    bvec = [sum(X[a][i] * y[i] for i in range(n)) for a in range(k)]
    # gaussian elimination
    M = [row[:] + [bvec[r]] for r, row in enumerate(A)]
    for c in range(k):
        piv = max(range(c, k), key=lambda r: abs(M[r][c]))
        M[c], M[piv] = M[piv], M[c]
        if abs(M[c][c]) < 1e-12:
            return None
        for r in range(k):
            if r == c:
                continue
            f = M[r][c] / M[c][c]
            for cc in range(c, k + 1):
                M[r][cc] -= f * M[c][cc]
    return {names[i]: M[i][k] / M[i][i] for i in range(k)}


def day_boot_ols(days, y, X, names, iters=2000, seed=L.SEED):
    """Day-clustered block bootstrap of every coefficient."""
    byday = collections.defaultdict(list)
    for i, d in enumerate(days):
        byday[d].append(i)
    ds = sorted(byday)
    rnd = random.Random(seed)
    acc = collections.defaultdict(list)
    for _ in range(iters):
        idx = []
        for _ in ds:
            idx.extend(byday[ds[rnd.randrange(len(ds))]])
        yy = [y[i] for i in idx]
        XX = [[x[i] for i in idx] for x in X]
        b = ols(yy, XX, names)
        if b:
            for k2, v in b.items():
                acc[k2].append(v)
    out = {}
    for k2, v in acc.items():
        v.sort()
        out[k2] = (v[int(.025 * len(v))], v[int(.975 * len(v))])
    return out


def run():
    print('=' * 78)
    print('RVMR-VALIDATION-V1   TRACK B - RVMR-INCR-V1')
    print('  DOES RVMR ADD INFORMATION BEYOND ATR AND TIME OF DAY?')
    print('  PRIMARY ATR  = ATR20 (SMA of true range, 20 bars ending at j)')
    print('  ATR STATE    = trailing_ratio(ATR20), W=%d, current bar' % S.W)
    print('                 excluded from the normaliser - the IDENTICAL')
    print('                 construction RVMR itself uses')
    print('  STRATA       = quintiles, cutpoints from the FIRST FULL YEAR')
    print('  NO ATR-period sweep. NO ML. NO interactions or splines.')
    print('  HISTORICAL RESEARCH - never relabelled prospective.')
    print('=' * 78)

    D = L.load_nq()
    print('NQ bars %d   %s .. %s' % (len(D['c']), D['et'][0], D['et'][-1]))
    U = L.features(D)
    nU = len(U['rr'])
    print('eligible universe %d bars, %d days\n' % (nU, len(set(U['day']))))

    # ---- causal ATR quintiles from the FIRST FULL YEAR only
    y0 = min(U['year'])
    cal = [U['atrr'][i] for i in range(nU)
           if U['year'][i] == y0 and U['atrr'][i] is not None]
    if len(cal) < 5000:
        y0b = sorted(set(U['year']))[1]
        cal = [U['atrr'][i] for i in range(nU)
               if U['year'][i] in (y0, y0b) and U['atrr'][i] is not None]
        print('  first year thin; calibration window %s..%s' % (y0, y0b))
    cuts = L.quintile_cuts(cal)
    print('ATR-ratio quintile cutpoints (from %s, n=%d, applied unchanged):'
          % (y0, len(cal)))
    print('  %s\n' % '  '.join('%.4f' % c for c in cuts))
    aq = [L.qbucket(U['atrr'][i], cuts) for i in range(nU)]
    tq = [L.tod_bucket(U['mod'][i]) for i in range(nU)]

    # ------------------------------------------------- unconditional
    print('=' * 78)
    print('REFERENCE - UNCONDITIONAL HIGH-LOW (the number to beat)')
    print('=' * 78)
    uncond = {}
    for bkey, skey, nm in TOOLS:
        hi = [(U['day'][i], U['abs30'][i]) for i in range(nU) if U[bkey][i] == 'HIGH']
        lo = [(U['day'][i], U['abs30'][i]) for i in range(nU)
              if U[bkey][i] in ('LOW', 'MEDIUM')]
        d, ci, p = L.day_boot_delta(hi, lo, iters=5000)
        uncond[nm] = d
        print('  %-18s HIGH n %6d vs LOW+MED n %6d   delta %+0.3f'
              '  CI [%+0.3f,%+0.3f]' % (nm, len(hi), len(lo), d, ci[0], ci[1]))
    print()

    # ------------------------------------------------- B1 surface
    print('=' * 78)
    print('B1 - ATR QUINTILE x RVMR STATE SURFACE (median |ret|@30m)')
    print('=' * 78)
    B1 = {}
    for bkey, skey, nm in TOOLS:
        print(nm)
        print('  %-10s %s' % ('ATR q', '   '.join(
            '%14s' % b for b in ('LOW', 'MEDIUM', 'HIGH'))) + '    monotone')
        okq = 0; tested = 0
        for q in range(NQ):
            cells = []
            for b in ('LOW', 'MEDIUM', 'HIGH'):
                ii = [i for i in range(nU) if aq[i] == q and U[bkey][i] == b]
                cells.append((len(ii), L.med([U['abs30'][i] for i in ii]) if ii else None))
            if any(c[1] is None or c[0] < 100 for c in cells):
                print('  q%-9d %s   under-populated'
                      % (q, '   '.join('%6d %7s' % (c[0], '-') for c in cells)))
                continue
            tested += 1
            mono = cells[0][1] < cells[1][1] < cells[2][1]
            if mono:
                okq += 1
            print('  q%-9d %s   %s'
                  % (q, '   '.join('%6d %7.2f' % (c[0], c[1]) for c in cells),
                     'Y' if mono else 'n'))
        B1[nm] = (okq, tested)
        print('  monotone in %d of %d populated ATR quintiles\n' % (okq, tested))

    # ------------------------------------------------- B2 ATR x ToD
    print('=' * 78)
    print('B2 - ATR QUINTILE x TIME-OF-DAY x RVMR  (median |ret|@30m)')
    print('  similar ATR + similar time of day + different RVMR')
    print('=' * 78)
    for bkey, skey, nm in TOOLS:
        print(nm)
        ok = tot = 0
        for q in range(NQ):
            row = []
            for t in range(len(L.TOD)):
                cells = []
                for b in ('LOW', 'MEDIUM', 'HIGH'):
                    ii = [i for i in range(nU) if aq[i] == q and tq[i] == t
                          and U[bkey][i] == b]
                    cells.append((len(ii), L.med([U['abs30'][i] for i in ii])
                                  if ii else None))
                if any(c[1] is None or c[0] < 50 for c in cells):
                    row.append(' -- ')
                    continue
                tot += 1
                mono = cells[0][1] < cells[1][1] < cells[2][1]
                if mono:
                    ok += 1
                row.append(' Y  ' if mono else ' n  ')
            print('  q%d  %s' % (q, ''.join(row)))
        print('  ToD columns: %s' % ' / '.join(t[0].split()[0] for t in L.TOD))
        print('  monotone in %d of %d populated (ATR x ToD) cells\n' % (ok, tot))

    # ------------------------------------------------- B4 matched
    print('=' * 78)
    print('B4 - MATCHED INCREMENTAL TEST')
    print('  cells = (ATR quintile x ToD bucket x year), dropped SYMMETRICALLY')
    print('=' * 78)
    B4 = {}
    for bkey, skey, nm in TOOLS:
        ctrl = collections.defaultdict(list)
        for i in range(nU):
            if U[bkey][i] in ('LOW', 'MEDIUM'):
                ctrl[(aq[i], tq[i], U['year'][i])].append(U['abs30'][i])
        pa, pb = [], []
        for i in range(nU):
            if U[bkey][i] != 'HIGH':
                continue
            k = (aq[i], tq[i], U['year'][i])
            if k not in ctrl or len(ctrl[k]) < 20:
                continue
            pa.append((U['day'][i], U['abs30'][i]))
            pb.append((U['day'][i], sum(ctrl[k]) / len(ctrl[k])))
        if len(pa) < 100:
            print('  %-18s INSUFFICIENT MATCHED DATA' % nm)
            B4[nm] = None
            continue
        d, ci, p = L.day_boot_delta(pa, pb, iters=20000)
        ret = 100.0 * d / uncond[nm] if uncond[nm] else float('nan')
        print('  %-18s matched n %6d   HIGH-control %+0.4f'
              % (nm, len(pa), d))
        print('      day-clustered 95%% CI [%+0.4f, %+0.4f]   p %.4f' % (ci[0], ci[1], p))
        print('      unconditional delta %+0.4f  ->  RETENTION %.1f%%\n'
              % (uncond[nm], ret))
        B4[nm] = {'d': d, 'ci': ci, 'p': p, 'ret': ret, 'n': len(pa)}

    # ------------------------------------------------- B3 model
    print('=' * 78)
    print('B3 - CONTINUOUS MODEL (frozen form, no mining)')
    print('=' * 78)
    ry = rank(U['abs30'])
    ra = rank(U['atrr'])
    rr_ = rank(U['rr'])
    rv = rank(U['vr'])
    n = float(nU)
    def z(v):
        m = sum(v) / n
        sd = math.sqrt(sum((x - m) ** 2 for x in v) / n)
        return [(x - m) / sd for x in v]
    zy, za, zr, zv = z(ry), z(ra), z(rr_), z(rv)
    Xc = [[1.0] * nU, za, zr, zv]
    names = ['const', 'ATR', 'RANGE', 'VOLUME']
    for t in range(len(L.TOD) - 1):
        Xc.append([1.0 if tq[i] == t else 0.0 for i in range(nU)])
        names.append('ToD%d' % t)
    b = ols(zy, Xc, names)
    print('  PRIMARY - standardized rank OLS, ToD fixed effects')
    print('  rank(|ret|@30) ~ ATR + RANGE + VOLUME + ToD')
    print('  bootstrapping day-clustered CIs (2,000 day resamples) ...')
    ci = day_boot_ols(U['day'], zy, Xc, names, iters=2000)
    for k in ('ATR', 'RANGE', 'VOLUME'):
        lo, hi = ci.get(k, (float('nan'), float('nan')))
        sig = 'CI excludes 0' if (lo > 0 or hi < 0) else 'CI INCLUDES 0'
        print('    beta_%-7s %+0.4f   day-clustered 95%% CI [%+0.4f, %+0.4f]   %s'
              % (k, b[k], lo, hi, sig))
    # single-tool models, to see each one's standalone incremental beta
    print('\n  RANGE after ATR only:')
    b2 = ols(zy, [[1.0] * nU, za, zr], ['const', 'ATR', 'RANGE'])
    print('    beta_ATR %+0.4f   beta_RANGE %+0.4f' % (b2['ATR'], b2['RANGE']))
    print('  VOLUME after ATR only:')
    b3 = ols(zy, [[1.0] * nU, za, zv], ['const', 'ATR', 'VOLUME'])
    print('    beta_ATR %+0.4f   beta_VOLUME %+0.4f' % (b3['ATR'], b3['VOLUME']))
    print('  ATR alone:')
    b4 = ols(zy, [[1.0] * nU, za], ['const', 'ATR'])
    print('    beta_ATR %+0.4f' % b4['ATR'])
    print('  RANGE alone / VOLUME alone:')
    print('    beta_RANGE %+0.4f   beta_VOLUME %+0.4f'
          % (ols(zy, [[1.0] * nU, zr], ['const', 'RANGE'])['RANGE'],
             ols(zy, [[1.0] * nU, zv], ['const', 'VOLUME'])['VOLUME']))
    print('\n  SECONDARY - raw units')
    rawX = [[1.0] * nU, U['atrr'], U['rr'], U['vr']]
    rb_ = ols(U['abs30'], rawX, ['const', 'ATR', 'RANGE', 'VOLUME'])
    print('    beta_ATR %+0.4f  beta_RANGE %+0.4f  beta_VOLUME %+0.4f  (pts)'
          % (rb_['ATR'], rb_['RANGE'], rb_['VOLUME']))
    print()

    # ------------------------------------------------- year stability
    print('=' * 78)
    print('YEAR STABILITY OF THE INCREMENTAL EFFECT')
    print('  consistent sign matters more than per-year significance')
    print('=' * 78)
    for bkey, skey, nm in TOOLS:
        print(nm)
        pos = tot = 0
        for y in sorted(set(U['year'])):
            ctrl = collections.defaultdict(list)
            for i in range(nU):
                if U['year'][i] == y and U[bkey][i] in ('LOW', 'MEDIUM'):
                    ctrl[(aq[i], tq[i])].append(U['abs30'][i])
            hs, cs = [], []
            for i in range(nU):
                if U['year'][i] != y or U[bkey][i] != 'HIGH':
                    continue
                k = (aq[i], tq[i])
                if k not in ctrl or len(ctrl[k]) < 20:
                    continue
                hs.append(U['abs30'][i]); cs.append(sum(ctrl[k]) / len(ctrl[k]))
            if len(hs) < 100:
                print('    %s  n %5d  thin' % (y, len(hs)))
                continue
            tot += 1
            d = L.mean(hs) - L.mean(cs)
            if d > 0:
                pos += 1
            print('    %s  matched n %6d   HIGH-control %+0.4f   %s'
                  % (y, len(hs), d, 'POS' if d > 0 else 'NEG'))
        print('    -> %d of %d years positive\n' % (pos, tot))

    # ------------------------------------------------- tails
    print('=' * 78)
    print('TAIL DESTRUCTION (robustness only)')
    print('=' * 78)
    order = sorted(range(nU), key=lambda i: U['abs30'][i])
    for cut, lab in ((0.99, 'drop top 1%'), (0.95, 'drop top 5%')):
        keep = set(order[:int(cut * nU)])
        for bkey, skey, nm in TOOLS:
            ctrl = collections.defaultdict(list)
            for i in keep:
                if U[bkey][i] in ('LOW', 'MEDIUM'):
                    ctrl[(aq[i], tq[i], U['year'][i])].append(U['abs30'][i])
            hs, cs = [], []
            for i in keep:
                if U[bkey][i] != 'HIGH':
                    continue
                k = (aq[i], tq[i], U['year'][i])
                if k not in ctrl or len(ctrl[k]) < 20:
                    continue
                hs.append(U['abs30'][i]); cs.append(sum(ctrl[k]) / len(ctrl[k]))
            if hs:
                print('  %-12s %-18s matched n %6d  HIGH-control %+0.4f'
                      % (lab, nm, len(hs), L.mean(hs) - L.mean(cs)))
    print()

    # ------------------------------------------------- slow vs local
    print('=' * 78)
    print('SLOW REGIME vs LOCAL STATE (certified TEST 15 lag methodology)')
    print('=' * 78)
    bydm = {}
    for i in range(nU):
        bydm[(U['day'][i], U['mod'][i], 'r')] = U['rb'][i]
        bydm[(U['day'][i], U['mod'][i], 'v')] = U['vb'][i]
    dl = sorted(set(U['day'])); dp = {d: k for k, d in enumerate(dl)}
    for bkey, skey, nm in TOOLS:
        tag = 'r' if bkey == 'rb' else 'v'
        ctrl = collections.defaultdict(list)
        for i in range(nU):
            if U[bkey][i] in ('LOW', 'MEDIUM'):
                ctrl[(aq[i], tq[i], U['year'][i])].append(U['abs30'][i])
        hs, cs = [], []
        for i in range(nU):
            k = dp[U['day'][i]]
            if k < 3:
                continue
            lb = bydm.get((dl[k - 3], U['mod'][i], tag))
            if lb != 'HIGH':
                continue
            key = (aq[i], tq[i], U['year'][i])
            if key not in ctrl or len(ctrl[key]) < 20:
                continue
            hs.append(U['abs30'][i]); cs.append(sum(ctrl[key]) / len(ctrl[key]))
        lagd = (L.mean(hs) - L.mean(cs)) if hs else float('nan')
        live = B4[nm]['d'] if B4.get(nm) else float('nan')
        print('  %-18s live label %+0.4f   3-day-lagged label %+0.4f'
              '   slow share %.0f%%'
              % (nm, live, lagd,
                 100.0 * lagd / live if live and live == live else float('nan')))
    print('  (a large lagged effect = multi-day volatility clustering;')
    print('   a small one = the information is LOCAL to the current state)')
    print()

    # ------------------------------------------------- verdict
    print('=' * 78)
    print('TRACK B - DECLARED VERDICT RULES')
    print('=' * 78)
    verdicts = {}
    for bkey, skey, nm in TOOLS:
        r = B4.get(nm)
        if r is None:
            verdicts[nm] = 'INSUFFICIENT DATA'
            continue
        okq, tq_ = B1[nm]
        excl = r['ci'][0] > 0 or r['ci'][1] < 0
        ret = r['ret']
        print('\n  %s' % nm)
        print('    matched delta            %+0.4f' % r['d'])
        print('    CI excludes 0            %s' % ('YES' if excl else 'NO'))
        print('    retention                %.1f%%' % ret)
        print('    monotone ATR quintiles   %d of %d' % (okq, tq_))
        if r['d'] <= 0 or ret < 5:
            v = 'FULLY REDUNDANT WITH ATR/TIME OF DAY'
        elif not excl or ret < 20:
            v = 'MOSTLY REDUNDANT WITH ATR'
        elif ret < 50:
            v = 'MODEST INCREMENTAL VALUE BEYOND ATR'
        else:
            v = 'STRONG INCREMENTAL VALUE BEYOND ATR'
        verdicts[nm] = v
        print('    ---> %s' % v)
    print('\n' + '=' * 78)
    print('TRACK B VERDICTS')
    for k, v in verdicts.items():
        print('  %-20s %s' % (k, v))
    print('=' * 78)
    print('HISTORICAL RESEARCH ONLY. NOTHING FROZEN WAS MODIFIED.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')


if __name__ == '__main__':
    run()
