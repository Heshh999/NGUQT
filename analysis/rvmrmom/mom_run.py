#!/usr/bin/env python3
# ======================================================================
# RVMR-MOMENTUM-V1 - FROZEN HISTORICAL EXECUTION + DESTRUCTION
# H1 (5m momentum) + H2 (30m trend) - EXECUTED ONCE, SCORED SEPARATELY
# ======================================================================
# AUTHORITATIVE PREREGISTRATION:
#   docs/RVMR_MOMENTUM_V1_PREREGISTRATION.md
#   sha256 210306f0ffa8f58fc8f200905677ffa51ae2ab648c15fe62bb29ed9222dbfdfe
#   commit 832faa61546ea5f41925f4a066dc2d5e18fc7c33  (2026-08-26T06:34:34Z)
#
# NO COMBINATION of H1 and H2. Neither result modifies the other's
# eligibility, thresholds, controls or implementation.
#
# EPISTEMIC STATUS: all pre-2026-08-26 data is DEVELOPMENT data. Nothing
# here is OOS, prospective, or a validated edge. MEMORY-PRED-V1 Lane A
# stays frozen; the engine asserts zero rows at/after the boundary.
#
# SUBMITS NO ORDERS. SIMULATES NO TRADE. NOTHING FROZEN IS MODIFIED.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ----------------------------------------------------------------------
# PRE-COMPUTATION CHOICES, RECORDED BEFORE ANY RESULT EXISTS
# (prereg silent; none chosen to favour a hypothesis; all disclosed):
# (a) Rotation permutation implementation: for each cluster day the sums
#     of aligned returns over HIGH and LOW labels at EVERY circular
#     offset are precomputed exactly via FFT cross-correlation (verified
#     at offset 0 against direct sums); each iteration draws one uniform
#     offset in [1, n_day-1] per day. Days with a single eligible event
#     cannot rotate and contribute their observed configuration. Offsets
#     are drawn with numpy PCG64 seeded 20260826 (generator disclosed,
#     per the MT6 precedent); scalar bootstraps use
#     random.Random(20260826) as frozen.
# (b) H1's diagnostic regression mirrors H2's frozen B/A forms with
#     |mom5| in place of |trend30| (prereg 5.3: reported only).
# (c) The 27-cell match (ATR x |mom| x ToD, >=30 both sides, common
#     weight) is REPORTED alongside MO6/MO7/MT5/MT7, not gated.
# (d) Forward-window MFE/MAE use max high / min low over t+1..t+FW
#     relative to c[t] in the momentum direction; favorable-first is NOT
#     computed (would require intrabar sequence).
# (e) Cluster day = day[t+FW] (frozen 2.6); years and months follow it.
# (f) MO5 gate is the point-estimate contrast (frozen 4.6); its CI is
#     reported at 4,000 iterations.
# ======================================================================

import os, sys, math, random, collections, hashlib, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../rvmr'))
import rvmr_spec as RS
import rvmr_run as RV

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
PREREG = os.path.join(ROOT, 'docs', 'RVMR_MOMENTUM_V1_PREREGISTRATION.md')
PREREG_SHA = ('210306f0ffa8f58fc8f200905677ffa51ae2ab648c15fe62bb29ed92'
              '22dbfdfe')
SEED = 20260826
B_MAIN, B_DESC, PERM = 20000, 4000, 20000
BP = 1e4
BOUND = '2026-08-26'
COST_PTS = 0.87
TODN = ('OVERNIGHT', 'RTH_AM', 'RTH_PM')
STN = ('LOW', 'MEDIUM', 'HIGH')
PASS = {True: 'PASS', False: 'FAIL'}
FAM4 = [(0.10050, 'SC'), (0.03570, 'MON'), (0.00005, 'MEMPRED'),
        (0.00005, 'HARU')]          # frozen programme-ledger p-values


def mean(x):
    return float(np.mean(x)) if len(x) else float('nan')


def quantile(sv, q):
    n = len(sv)
    hq = (n - 1) * q
    lo = int(math.floor(hq))
    hi = min(lo + 1, n - 1)
    return sv[lo] + (hq - lo) * (sv[hi] - sv[lo])


def boot_diff(blocks, iters, seed=SEED):
    nb = len(blocks)
    SA = sum(b[0] for b in blocks); NA = sum(b[1] for b in blocks)
    SB = sum(b[2] for b in blocks); NB = sum(b[3] for b in blocks)
    if not NA or not NB or nb < 15:
        return float('nan'), float('nan'), float('nan'), float('nan')
    obs = SA / NA - SB / NB
    rnd = random.Random(seed); rr = rnd.randrange
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
    rnd = random.Random(seed); rr = rnd.randrange
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


def bh2(p1, p2):
    ps = sorted([(p1, 0), (p2, 1)])
    q = [0.0, 0.0]
    q_hi = ps[1][0]
    q[ps[1][1]] = q_hi
    q[ps[0][1]] = min(2.0 * ps[0][0], q_hi)
    return q


def bh_exact(fam):
    """fam: list of (p, name). Returns {name: q}."""
    ps = sorted(fam)
    M = len(ps)
    out = {}
    prev = 1.0
    for rank in range(M, 0, -1):
        pv, nm = ps[rank - 1]
        prev = min(prev, pv * M / rank)
        out[nm] = prev
    return out


def atr20_arrays(h, l, c):
    n = len(c)
    out = np.full(n, np.nan)
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


def main():
    t0 = time.time()
    print('=' * 78)
    print('RVMR-MOMENTUM-V1   FROZEN HISTORICAL EXECUTION  (H1 + H2,'
          ' scored separately)')
    print('  prereg sha256 %s' % PREREG_SHA[:40])
    print('  commit 832faa61546ea5f41925f4a066dc2d5e18fc7c33')
    print('  DEVELOPMENT ONLY - NOT OOS, NOT PROSPECTIVE. NO COMBINATION.')
    print('  SUBMITS NO ORDERS.')
    print('=' * 78)

    # ---------------------------------------------------------- PHASE 0
    print('\n' + '=' * 78)
    print('PHASE 0  FREEZE VERIFICATION')
    print('=' * 78)
    got = hashlib.sha256(open(PREREG, 'rb').read()).hexdigest()
    ok1 = (got == PREREG_SHA)
    print('  (1,2) prereg sha256 %s...  matches frozen: %s' % (got[:32], ok1))
    ok3 = (RS.T1 == 1.270 and RS.T2 == 2.335 and RS.W == 1440)
    print('  (3) RVMR spec T1 %.3f T2 %.3f W %d -> %s'
          % (RS.T1, RS.T2, RS.W, ok3))
    print('  (4-7) mom5 = c[t]/c[t-5]-1 (em==5); fut5 = c[t+5]/c[t]-1;')
    print('        trend30 = c[t]/c[t-30]-1 (em==30); fut15 = c[t+15]/c[t]-1')
    print('  (8) state RB[t], available at close of t-1; atr20(t) required')
    print('  (9-10) common-weight standardisation on |mom|/ATR terciles,'
          ' >=0.50 retention')
    print('  (11) H2 baseline B = 1+|tr|+|tr|^2+up+up*|tr|+atrRel+ToD;'
          ' A = B + MED + HIGH; gate on HIGH coef')
    print('  (12) ToD of mod[t]: OVERNIGHT >=1081|<=569, AM 570-750,'
          ' PM 751-960')
    print('  (13) tails: within-state top-1%/5% by |aligned| (pooled'
          ' reported)')
    print('  (14) boot 20,000 seed %d; within-day circular rotation'
          ' permutation 20,000' % SEED)
    print('  (15-16) MO1..MO10 / MT1..MT10 as frozen')

    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    N = len(D['c'])
    et = D['et']
    ok17 = et[-1] < BOUND + ' 00:00:00'
    post = sum(1 for dd in D['day'] if dd >= BOUND)
    print('  (17) prospective boundary: max timestamp %s < %s 00:00 -> %s'
          '   rows at/after boundary: %d' % (et[-1], BOUND, ok17, post))
    if not (ok1 and ok3 and ok17 and post == 0):
        print('\nRVMR-MOMENTUM-V1 FREEZE FAILURE')
        return
    print('  FREEZE VERIFIED.')

    h = np.array(D['h']); l = np.array(D['l']); c = np.array(D['c'])
    em = np.array(D['em'], dtype=np.int64)
    mod = np.array(D['mod'], dtype=np.int32)
    day = D['day']
    rr_ = RS.trailing_ratio([D['h'][i] - D['l'][i] for i in range(N)])
    sc_arr = np.array([x if x is not None else np.nan for x in rr_])
    smap = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
    st_arr = np.array([smap.get(RS.bucket(x) if x is not None else None, -1)
                       for x in rr_], dtype=np.int8)
    atr = atr20_arrays(D['h'], D['l'], D['c'])
    days_all = sorted(set(day))
    dayid = {d: k for k, d in enumerate(days_all)}
    dayidx = np.array([dayid[d] for d in day], dtype=np.int32)
    badc = np.cumsum(np.concatenate([[0], (c <= 0).astype(np.int64)]))
    print('  bars %d   %s .. %s   exchange days %d   (%.0f s)'
          % (N, et[0], et[-1], len(days_all), time.time() - t0))

    # ---------------------------------------------------------- CAUSAL
    print('\n' + '=' * 78)
    print('CAUSAL AUDIT (shared)')
    print('=' * 78)
    rows = [
        ('mom / trend (closes t-LB..t)', 'close of t', 'fut', 'YES'),
        ('sign(mom)', 'close of t', 'fut', 'YES'),
        ('RB[t] (bars t-1440..t-1)', 'close of t-1', 'fut', 'YES'),
        ('score rr[t]', 'close of t-1', 'fut', 'YES'),
        ('atr20(t) (bars t-19..t)', 'close of t', 'fut', 'YES'),
        ('|mom| / |trend|', 'close of t', 'fut', 'YES'),
        ('ToD bucket of mod[t]', 'clock', 'fut', 'YES'),
        ('fut (closes t..t+FW) OUTCOME', 'close of t+FW', 'itself', 'YES'),
        ('MFE/MAE (bars t+1..t+FW) OUTCOME', 'close of t+FW', 'itself',
         'YES'),
    ]
    for f, a, o, y in rows:
        print('  %-36s %-14s %-8s %s' % (f, a, o, y))
    print('  ALL ROWS YES')

    # ================================================================
    def build(LB, FW):
        ok = np.zeros(N, dtype=bool)
        ok[LB:N - FW] = True
        idx = np.arange(LB, N - FW)
        ok[idx] &= (em[idx] - em[idx - LB] == LB)
        ok[idx] &= (em[idx + FW] - em[idx] == FW)
        idx = np.nonzero(ok)[0]
        # all closes in t-LB..t+FW positive
        idx = idx[(badc[idx + FW + 1] - badc[idx - LB]) == 0]
        m = c[idx] / c[idx - LB] - 1.0
        keep = m != 0.0
        idx = idx[keep]; m = m[keep]
        keep = (st_arr[idx] >= 0) & ~np.isnan(atr[idx])
        idx = idx[keep]; m = m[keep]
        f = c[idx + FW] / c[idx] - 1.0
        up = (m > 0)
        al = np.where(up, f, -f) * BP
        # forward MFE/MAE via sliding windows
        swh = np.lib.stride_tricks.sliding_window_view(h, FW)
        swl = np.lib.stride_tricks.sliding_window_view(l, FW)
        fmax = swh[idx + 1].max(axis=1)
        fmin = swl[idx + 1].min(axis=1)
        mfe = np.where(up, (fmax - c[idx]), (c[idx] - fmin)) / c[idx] * BP
        mae = np.where(up, (c[idx] - fmin), (fmax - c[idx])) / c[idx] * BP
        m2 = mod[idx]
        tod = np.where((m2 >= 1081) | (m2 <= 569), 0,
                       np.where(m2 <= 750, 1, 2)).astype(np.int8)
        ev = {
            'idx': idx, 'st': st_arr[idx].astype(np.int8),
            'al': al, 'fut': f * BP, 'am': np.abs(m) * BP,
            'up': up.astype(np.int8),
            'atr': atr[idx] / c[idx] * BP, 'tod': tod,
            'sc': sc_arr[idx], 'px': c[idx], 'mfe': mfe, 'mae': mae,
            'cd': dayidx[idx + FW],
        }
        return ev

    # ================================================================
    def blocks_from(cd, val, maskA, maskB, Dn):
        sA = np.bincount(cd[maskA], weights=val[maskA], minlength=Dn)
        nA = np.bincount(cd[maskA], minlength=Dn)
        sB = np.bincount(cd[maskB], weights=val[maskB], minlength=Dn)
        nB = np.bincount(cd[maskB], minlength=Dn)
        use = (nA + nB) > 0
        return list(zip(sA[use], nA[use], sB[use], nB[use]))

    def blocks_mean(cd, val, mask, Dn):
        s = np.bincount(cd[mask], weights=val[mask], minlength=Dn)
        n = np.bincount(cd[mask], minlength=Dn)
        use = n > 0
        return list(zip(s[use], n[use]))

    Dn = len(days_all)

    def analyze(tag, ev, LB, FW, floors, binding_reg):
        res = {}
        cd = ev['cd']; st = ev['st']; al = ev['al']; am = ev['am']
        up = ev['up']; atrb = ev['atr']; tod = ev['tod']; sc = ev['sc']
        NE = len(al)
        print('\n' + '=' * 78)
        print('%s   EVENTS AND PRIMARY' % tag)
        print('=' * 78)
        cnt = collections.Counter(st.tolist())
        nL, nM, nH = cnt[0], cnt[1], cnt[2]
        print('  eligible events %d   LOW %d  MEDIUM %d  HIGH %d'
              % (NE, nL, nM, nH))
        prec = (nL >= floors[0] and nM >= floors[1] and nH >= floors[2])
        print('  minimum-n precondition (%d/%d/%d): %s'
              % (floors[0], floors[1], floors[2], PASS[prec]))
        res['prec'] = prec

        isH = st == 2; isL = st == 0; isM = st == 1
        stat = {}
        for k, nm in enumerate(STN):
            msk = st == k
            vals = al[msk]
            mn, lo, hi = boot_mean(blocks_mean(cd, al, msk, Dn), B_DESC)
            nz = vals[ev['fut'][msk] != 0.0]
            pc = float((nz > 0).mean()) if len(nz) else float('nan')
            stat[nm] = (int(msk.sum()), mn, float(np.median(vals)), lo, hi,
                        pc)
            print('  %-7s n %8d  aligned %+9.4f bp  med %+8.4f'
                  '  CI [%+8.4f, %+8.4f]  P(cont) %.4f  P(rev) %.4f'
                  % (nm, msk.sum(), mn, np.median(vals), lo, hi, pc, 1 - pc))
        dblk = blocks_from(cd, al, isH, isL, Dn)
        d_, dlo, dhi, dp = boot_diff(dblk, B_MAIN)
        res['delta'], res['dlo'], res['dhi'], res['p'] = d_, dlo, dhi, dp
        print('\n  DELTA = HIGH - LOW = %+0.4f bp   CI [%+0.4f, %+0.4f]'
              '   boot p %.5f' % (d_, dlo, dhi, dp))
        # continuation-probability contrast
        fz = ev['fut'] != 0.0
        ind = (al > 0).astype(np.float64)
        pb = blocks_from(cd, ind, isH & fz, isL & fz, Dn)
        pd_, plo, phi, _pp = boot_diff(pb, B_DESC)
        res['dprob'] = pd_
        print('  P(cont|HIGH) - P(cont|LOW) = %+0.4f = %+0.2f pp'
              '   CI [%+0.2f, %+0.2f] pp' % (pd_, 100 * pd_, 100 * plo,
                                             100 * phi))
        pxm = float(ev['px'][isH | isL].mean())
        res['high_pts'] = stat['HIGH'][1] / BP * pxm
        print('  economics: mean close %0.0f;  DELTA %+0.4f NQ pts;'
              ' HIGH-arm aligned %+0.4f bp = %+0.4f pts vs cost %.2f'
              ' (x%.3f)'
              % (pxm, d_ / BP * pxm, stat['HIGH'][1],
                 res['high_pts'], COST_PTS,
                 abs(res['high_pts']) / COST_PTS))
        print('  MFE/MAE by state (bp, direction-relative):')
        for k, nm in enumerate(STN):
            msk = st == k
            print('    %-7s MFE %8.3f   MAE %8.3f'
                  % (nm, ev['mfe'][msk].mean(), ev['mae'][msk].mean()))

        # ---------------- long / short
        print('\n  LONG/SHORT  (HIGH-LOW contrast within each side)')
        side_d = {}
        for sval, nm in ((1, 'mom>0'), (0, 'mom<0')):
            msk_side = up == sval
            for k, snm in enumerate(STN):
                mm = al[msk_side & (st == k)]
                nzz = mm[ev['fut'][msk_side & (st == k)] != 0.0]
                print('    %-6s %-7s n %8d  aligned %+9.4f bp  P(cont) %.4f'
                      % (nm, snm, len(mm), mm.mean() if len(mm) else
                         float('nan'),
                         (nzz > 0).mean() if len(nzz) else float('nan')))
            bl = blocks_from(cd, al, msk_side & isH, msk_side & isL, Dn)
            dd2, lo2, hi2, _ = boot_diff(bl, B_DESC)
            side_d[nm] = dd2
            print('    %-6s DELTA %+0.4f bp  CI [%+0.4f, %+0.4f]'
                  % (nm, dd2, lo2, hi2))
        res['side_d'] = side_d
        res['asym'] = min(side_d.values()) <= 0

        # ---------------- magnitude robustness
        ams = np.sort(am)
        p50, p80 = quantile(ams, 0.50), quantile(ams, 0.80)
        print('\n  MAGNITUDE ROBUSTNESS (frozen ALL/TOP50/TOP20;'
              ' cuts %.4f / %.4f bp)' % (p50, p80))
        for nm2, thr in (('ALL', None), ('TOP50', p50), ('TOP20', p80)):
            mk = np.ones(NE, dtype=bool) if thr is None else (am >= thr)
            bl = blocks_from(cd, al, mk & isH, mk & isL, Dn)
            dd2, lo2, hi2, _ = boot_diff(bl, B_DESC)
            print('    %-6s nH %8d nL %9d  DELTA %+0.4f bp'
                  '  CI [%+0.4f, %+0.4f]'
                  % (nm2, (mk & isH).sum(), (mk & isL).sum(), dd2, lo2, hi2))

        # ---------------- standardisations
        aa = np.sort(atrb)
        a1, a2 = quantile(aa, 1 / 3.0), quantile(aa, 2 / 3.0)
        b1, b2 = quantile(ams, 1 / 3.0), quantile(ams, 2 / 3.0)
        at = np.digitize(atrb, [a1, a2])
        bt = np.digitize(am, [b1, b2])

        def std_delta(cellids):
            agg = {}
            for cid, s2, v in zip(cellids, st, al):
                if s2 == 1:
                    continue
                e = agg.get(cid)
                if e is None:
                    e = agg[cid] = [0.0, 0, 0.0, 0]
                if s2 == 2:
                    e[0] += v; e[1] += 1
                else:
                    e[2] += v; e[3] += 1
            num = den = 0.0; used = 0
            for e in agg.values():
                if e[1] >= 30 and e[3] >= 30:
                    w = e[1] + e[3]
                    num += w * (e[0] / e[1] - e[2] / e[3]); den += w
                    used += 1
            return (num / den if den else float('nan')), used

        dm_mag, u1 = std_delta(bt)
        dm_atr, u2 = std_delta(at)
        dm_full, u3 = std_delta(at.astype(np.int64) * 100
                                + bt.astype(np.int64) * 10 + tod)
        print('\n  MAGNITUDE CONTROL  |x|-tercile standardised DELTA'
              ' %+0.4f bp  retention %.1f%%  (cells %d)'
              % (dm_mag, 100 * dm_mag / d_ if d_ else float('nan'), u1))
        print('  ATR CONTROL        per-tercile:')
        for t3 in range(3):
            mk = at == t3
            bl = blocks_from(cd, al, mk & isH, mk & isL, Dn)
            dd2, lo2, hi2, _ = boot_diff(bl, 2000)
            print('    ATR terc %d  nH %8d nL %9d  DELTA %+0.4f bp'
                  '  CI [%+0.4f, %+0.4f]'
                  % (t3, (mk & isH).sum(), (mk & isL).sum(), dd2, lo2, hi2))
        print('  ATR-standardised DELTA %+0.4f bp  retention %.1f%%'
              '  (cells %d)' % (dm_atr, 100 * dm_atr / d_ if d_ else
                                float('nan'), u2))
        print('  27-cell match (reported): %+0.4f bp  retention %.1f%%'
              '  (cells %d)' % (dm_full, 100 * dm_full / d_ if d_ else
                                float('nan'), u3))
        res['dm_mag'], res['dm_atr'] = dm_mag, dm_atr

        # ---------------- ToD
        print('\n  TIME-OF-DAY')
        tod_pos = 0
        for t3, nm2 in enumerate(TODN):
            mk = tod == t3
            bl = blocks_from(cd, al, mk & isH, mk & isL, Dn)
            dd2, lo2, hi2, _ = boot_diff(bl, 2000)
            if dd2 > 0:
                tod_pos += 1
            print('    %-10s nH %8d nL %9d  DELTA %+0.4f bp'
                  '  CI [%+0.4f, %+0.4f]'
                  % (nm2, (mk & isH).sum(), (mk & isL).sum(), dd2, lo2,
                     hi2))
        print('    buckets with DELTA > 0: %d of 3' % tod_pos)
        res['tod_pos'] = tod_pos

        # ---------------- baselines
        print('\n  DIRECTIONAL BASELINES')
        fz2 = ev['fut'] != 0.0
        print('    A unconditional: P(fut>0) %.4f   mean fut %+0.4f bp'
              % ((ev['fut'][fz2] > 0).mean(), ev['fut'].mean()))
        pm, plo2, phi2 = boot_mean(blocks_mean(cd, al,
                                               np.ones(NE, bool), Dn),
                                   B_DESC)
        res['pooled'] = (pm, plo2, phi2)
        print('    B momentum-only pooled aligned %+0.4f bp'
              '  CI [%+0.4f, %+0.4f]' % (pm, plo2, phi2))
        print('    C RVMR-only (mean SIGNED fut by state, no momentum'
              ' conditioning):')
        for k, nm2 in enumerate(STN):
            print('      %-7s %+0.4f bp' % (nm2, ev['fut'][st == k].mean()))
        print('    D matched baselines: see standardisations above')

        # ---------------- regression (binding for H2, diagnostic for H1)
        X = np.empty((NE, 10))
        X[:, 0] = 1.0
        X[:, 1] = am
        X[:, 2] = am ** 2 / 100.0
        X[:, 3] = up
        X[:, 4] = up * am
        X[:, 5] = atrb
        X[:, 6] = tod == 1
        X[:, 7] = tod == 2
        X[:, 8] = isM
        X[:, 9] = isH
        Y = al.copy()
        order = np.argsort(cd, kind='stable')
        Xs = X[order]; Ys = Y[order]; cds = cd[order]
        ud, starts = np.unique(cds, return_index=True)
        # memory-safe per-day sufficient statistics: 100 bincounts of
        # column products instead of a (NE,10,10) outer-product array
        DA = len(days_all)
        Gfull = np.empty((DA, 100))
        for i2 in range(10):
            for j2 in range(10):
                Gfull[:, i2 * 10 + j2] = np.bincount(
                    cds, weights=Xs[:, i2] * Xs[:, j2], minlength=DA)
        Hfull = np.empty((DA, 10))
        for i2 in range(10):
            Hfull[:, i2] = np.bincount(cds, weights=Xs[:, i2] * Ys,
                                       minlength=DA)
        Gd = Gfull[ud]
        Hd = Hfull[ud]
        del Gfull, Hfull
        Gf = Gd.sum(0).reshape(10, 10)
        Hf = Hd.sum(0)
        yy = float(Ys @ Ys); ysum = float(Ys.sum())
        sst = yy - ysum * ysum / NE

        def fit(cols):
            Gs = Gf[np.ix_(cols, cols)]
            beta = np.linalg.solve(Gs, Hf[list(cols)])
            sse = yy - beta @ Hf[list(cols)]
            return beta, 1.0 - sse / sst

        bB, r2B = fit(list(range(8)))
        bA, r2A = fit(list(range(10)))
        rngnp = np.random.default_rng(SEED)
        betas = np.empty(B_MAIN)
        done = 0
        Dr = len(ud)
        while done < B_MAIN:
            k2 = min(2000, B_MAIN - done)
            W = rngnp.multinomial(Dr, np.full(Dr, 1.0 / Dr),
                                  size=k2).astype(np.float64)
            Gb = (W @ Gd).reshape(k2, 10, 10)
            Hb = W @ Hd
            sol = np.linalg.solve(Gb, Hb[..., None])[..., 0]
            betas[done:done + k2] = sol[:, 9]
            done += k2
        betas.sort()
        blo, bhi = betas[int(.025 * B_MAIN)], betas[int(.975 * B_MAIN)]
        le = int((betas <= 0).sum()); ge = int((betas >= 0).sum())
        bpv = max(2.0 * min(le, ge) / B_MAIN, 1.0 / (B_MAIN + 1.0))
        lab = 'BINDING (MT6)' if binding_reg else 'DIAGNOSTIC (reported)'
        print('\n  NONLINEAR BASELINE REGRESSION  [%s]' % lab)
        print('    R2(B) %.6f  R2(A=B+MED+HIGH) %.6f  dR2 %+.6f'
              % (r2B, r2A, r2A - r2B))
        print('    HIGH coefficient %+0.4f bp   day-clustered CI'
              ' [%+0.4f, %+0.4f]   p %.5f'
              % (bA[9], blo, bhi, bpv))
        print('    MEDIUM coefficient %+0.4f bp' % bA[8])
        res['reg_hi'], res['reg_lo'], res['reg_hiCI'] = bA[9], blo, bhi
        res['reg_ok'] = (bA[9] > 0) and (blo > 0)

        # ---------------- score diagnostic
        scs = np.sort(sc)
        qs = [quantile(scs, x) for x in (0.2, 0.4, 0.6, 0.8)]
        qt = np.digitize(sc, qs)
        print('\n  SCORE QUINTILE DIAGNOSTIC (frozen; thresholds'
              ' untouched): aligned bp by rr[t] quintile')
        print('    ' + '  '.join('Q%d %+0.4f' % (q + 1, al[qt == q].mean())
                                 for q in range(5)))

        # ---------------- years
        print('\n  YEAR DESTRUCTION (cluster-day year; none is OOS)')
        yr_of = np.array([days_all[k][:4] for k in cd])
        years = sorted(set(yr_of.tolist()))
        print('  %-5s %9s %9s %9s %9s %9s %9s %9s'
              % ('year', 'n', 'LOW bp', 'HIGH bp', 'DELTA', 'dP pp',
                 'D(up)', 'D(dn)'))
        yr_pos = 0
        yreg = {}
        for y in years:
            mk = yr_of == y
            lw = al[mk & isL]; hg = al[mk & isH]
            dd2 = hg.mean() - lw.mean()
            if dd2 > 0:
                yr_pos += 1
            nzH = al[mk & isH & fz2]; nzL = al[mk & isL & fz2]
            dpp = ((nzH > 0).mean() - (nzL > 0).mean()) * 100
            du = (al[mk & isH & (up == 1)].mean()
                  - al[mk & isL & (up == 1)].mean())
            dn2 = (al[mk & isH & (up == 0)].mean()
                   - al[mk & isL & (up == 0)].mean())
            dmask = np.array([days_all[u][:4] == y for u in ud])
            try:
                yreg[y] = np.linalg.solve(
                    Gd[dmask].sum(0).reshape(10, 10),
                    Hd[dmask].sum(0))[9]
            except np.linalg.LinAlgError:
                yreg[y] = float('nan')
            print('  %-5s %9d %+9.4f %+9.4f %+9.4f %+9.3f %+9.4f %+9.4f'
                  '   reg_HIGH %+8.4f'
                  % (y, mk.sum(), lw.mean(), hg.mean(), dd2, dpp, du, dn2,
                     yreg[y]))
        print('  years with DELTA > 0: %d of %d' % (yr_pos, len(years)))
        res['yr_pos'] = yr_pos

        # ---------------- months
        mo_of = np.array([days_all[k][:7] for k in cd])
        movals = []
        for mo in sorted(set(mo_of.tolist())):
            mk = mo_of == mo
            if (mk & isH).sum() and (mk & isL).sum():
                movals.append((mo, al[mk & isH].mean()
                               - al[mk & isL].mean()))
        mpos = sum(1 for _, x in movals if x > 0)
        best = max(movals, key=lambda z: z[1])
        worst = min(movals, key=lambda z: z[1])
        print('\n  MONTHS  %d total  %d positive  %d negative'
              '  median %+0.4f bp' % (len(movals), mpos,
                                      len(movals) - mpos,
                                      float(np.median([x for _, x in
                                                       movals]))))
        print('    best %s %+0.4f   worst %s %+0.4f'
              % (best[0], best[1], worst[0], worst[1]))

        # ---------------- tails
        print('\n  TAIL DESTRUCTION (gate = within-state; pooled reported)')
        tails = {}
        Hv = np.sort(np.abs(al[isH]))[::-1]
        Lv = np.sort(np.abs(al[isL]))[::-1]
        for frac in (0.01, 0.05):
            thH = Hv[max(1, int(round(frac * len(Hv)))) - 1]
            thL = Lv[max(1, int(round(frac * len(Lv)))) - 1]
            mH = al[isH][np.abs(al[isH]) < thH]
            mL = al[isL][np.abs(al[isL]) < thL]
            tails[frac] = mH.mean() - mL.mean()
            print('    within-state trim %4.1f%%  DELTA %+0.4f bp'
                  % (frac * 100, tails[frac]))
        both = np.abs(al[isH | isL])
        for frac in (0.01, 0.05):
            th = np.sort(both)[::-1][max(1, int(round(frac * len(both))))
                                     - 1]
            keepH = al[isH][np.abs(al[isH]) < th]
            keepL = al[isL][np.abs(al[isL]) < th]
            remH = (np.abs(al[isH]) >= th).sum()
            remT = (both >= th).sum()
            print('    pooled       trim %4.1f%%  DELTA %+0.4f bp'
                  '  (%.0f%% of removed are HIGH)'
                  % (frac * 100, keepH.mean() - keepL.mean(),
                     100.0 * remH / remT))
        res['tails'] = tails

        # ---------------- rotation permutation
        print('\n  PERMUTATION - within-day circular rotation of the'
              ' state-label sequence')
        baseH = baseL = 0.0
        segs = []
        lab_all = st[order]
        for a in range(len(ud)):
            s0 = starts[a]
            s1 = starts[a + 1] if a + 1 < len(ud) else NE
            vals = Ys[s0:s1]
            lab = lab_all[s0:s1]
            n3 = s1 - s0
            hiI = (lab == 2).astype(np.float64)
            loI = (lab == 0).astype(np.float64)
            if hiI.sum() == 0 and loI.sum() == 0:
                continue
            if n3 == 1:
                baseH += float(vals[lab == 2].sum())
                baseL += float(vals[lab == 0].sum())
                continue
            FV = np.fft.rfft(vals)
            SH = np.fft.irfft(FV * np.conj(np.fft.rfft(hiI)), n3)
            SL = np.fft.irfft(FV * np.conj(np.fft.rfft(loI)), n3)
            err = abs(SH[0] - vals[lab == 2].sum()) + \
                abs(SL[0] - vals[lab == 0].sum())
            assert err < 1e-4, 'FFT parity failure'
            segs.append((SH, SL, n3))
        segs = [s for s in segs if s is not None]
        NH = int(isH.sum()); NL = int(isL.sum())
        obs = abs(res['delta'])
        flatH = np.concatenate([s[0] for s in segs])
        flatL = np.concatenate([s[1] for s in segs])
        lens = np.array([s[2] for s in segs])
        bases = np.concatenate([[0], np.cumsum(lens)])[:-1]
        rngp = np.random.default_rng(SEED)
        cntx = 0
        done = 0
        while done < PERM:
            k2 = min(2000, PERM - done)
            offs = 1 + (rngp.random((k2, len(segs)))
                        * (lens - 1)).astype(np.int64)
            gi = bases[None, :] + offs
            dH = (flatH[gi].sum(axis=1) + baseH) / NH
            dL = (flatL[gi].sum(axis=1) + baseL) / NL
            cntx += int((np.abs(dH - dL) >= obs).sum())
            done += k2
        perm_p = max((cntx + 1.0) / (PERM + 1.0), 1.0 / (PERM + 1.0))
        print('    rotatable days %d   observed |DELTA| %.4f bp'
              '   permutation p = %.5f' % (len(segs), obs, perm_p))
        res['perm_p'] = perm_p
        print('  (%s done at %.0f s)' % (tag, time.time() - t0))
        return res

    # ================================================================
    H1 = analyze('H1  SHORT-HORIZON MOMENTUM (mom5 -> fut5)',
                 build(5, 5), 5, 5, (500000, 80000, 25000), False)
    H2 = analyze('H2  BROADER TREND STATE (trend30 -> fut15)',
                 build(30, 15), 30, 15, (400000, 60000, 20000), True)

    # ================================================================
    print('\n' + '=' * 78)
    print('JOINT MULTIPLICITY')
    print('=' * 78)
    q2 = bh2(H1['p'], H2['p'])
    print('  raw p:  H1 %.5f   H2 %.5f' % (H1['p'], H2['p']))
    print('  BH q (M_binding=2):  H1 %.5f   H2 %.5f' % (q2[0], q2[1]))
    fam6 = FAM4 + [(H1['p'], 'MOM-H1'), (H2['p'], 'MOM-H2')]
    q6 = bh_exact(fam6)
    print('  BH q (M_cum=6, NON-BINDING, exact):  H1 %.5f   H2 %.5f'
          % (q6['MOM-H1'], q6['MOM-H2']))

    # ================================================================
    def gates(tag, R, q, names, binding_reg):
        print('\n' + '=' * 78)
        print('%s GATES' % tag)
        print('=' * 78)
        g = []
        g.append((names + '1', 'causal integrity',
                  'em conditions enforced in construction; audit YES;'
                  ' 0 post-boundary rows', True))
        g.append((names + '2', 'DELTA > 0', '%+0.4f bp' % R['delta'],
                  R['delta'] > 0))
        g.append((names + '3', 'CI excludes 0',
                  '[%+0.4f, %+0.4f]' % (R['dlo'], R['dhi']),
                  R['dlo'] > 0 or R['dhi'] < 0))
        g.append((names + '4', 'BH q<=0.05 AND rotation perm p<=0.05',
                  'q %.5f, perm %.5f' % (q, R['perm_p']),
                  q <= 0.05 and R['perm_p'] <= 0.05))
        if binding_reg:
            g.append(('MT5', '|trend| std DELTA>0 AND >=0.5 raw',
                      'std %+0.4f vs raw %+0.4f' % (R['dm_mag'],
                                                    R['delta']),
                      R['dm_mag'] > 0 and R['dm_mag'] >= 0.5 * R['delta']))
            g.append(('MT6', 'HIGH coef in nonlinear baseline (BINDING)',
                      'coef %+0.4f CI [%+0.4f, %+0.4f]'
                      % (R['reg_hi'], R['reg_lo'], R['reg_hiCI']),
                      R['reg_ok']))
        else:
            g.append(('MO5', 'P(cont|HIGH) - P(cont|LOW) > 0',
                      '%+0.4f pp' % (100 * R['dprob']), R['dprob'] > 0))
            g.append(('MO6', '|mom| std DELTA>0 AND >=0.5 raw',
                      'std %+0.4f vs raw %+0.4f' % (R['dm_mag'],
                                                    R['delta']),
                      R['dm_mag'] > 0 and R['dm_mag'] >= 0.5 * R['delta']))
        g.append((names + '7', 'ATR std DELTA>0 AND >=0.5 raw',
                  'std %+0.4f vs raw %+0.4f' % (R['dm_atr'], R['delta']),
                  R['dm_atr'] > 0 and R['dm_atr'] >= 0.5 * R['delta']))
        g.append((names + '8', 'DELTA>0 in >=2/3 ToD buckets',
                  '%d of 3' % R['tod_pos'], R['tod_pos'] >= 2))
        g.append((names + '9', 'DELTA>0 in >=6/8 years',
                  '%d of 8' % R['yr_pos'], R['yr_pos'] >= 6))
        g.append((names + '10', 'DELTA>0 after 1%/5% within-state trims',
                  '%+0.4f / %+0.4f bp' % (R['tails'][0.01],
                                          R['tails'][0.05]),
                  R['tails'][0.01] > 0 and R['tails'][0.05] > 0))
        for k3, crit, val, ok in g:
            print('  %-5s %-44s %-42s %s' % (k3, crit, val, PASS[ok]))
        npass = sum(1 for _, _, _, ok in g if ok)
        print('  PASSED %d / 10' % npass)
        return g, npass

    g1, n1 = gates('H1  MO1-MO10', H1, q2[0], 'MO', False)
    g2, n2 = gates('H2  MT1-MT10', H2, q2[1], 'MT', True)

    # ================================================================
    def verdict(tag, R, g, npass, kind):
        gd = {row[0]: row[3] for row in g}
        core = (gd[kind + '2'] and gd[kind + '3'] and gd[kind + '4'])
        # VERDICT FIX (disclosed): the frozen REDUNDANT class requires the
        # pooled aligned return to be POSITIVE with CI excluding 0
        # (prereg 8: "the pooled aligned return (baseline 2) is positive
        # with day-clustered CI excluding 0"). The first implementation
        # wrongly accepted a significantly NEGATIVE pooled return. No
        # threshold or statistic changed; only this comparison.
        pooled_real = R['pooled'][1] > 0
        if kind == 'MO':
            red_fail = (not gd['MO6']) or (not gd['MO7'])
            surv = 'RVMR-CONDITIONED MOMENTUM SURVIVES'
            red = 'MOMENTUM REAL - RVMR REDUNDANT'
        else:
            red_fail = (not gd['MT5']) or (not gd['MT6']) or \
                (not gd['MT7'])
            surv = 'RVMR-CONDITIONED TREND SURVIVES'
            red = 'TREND REAL - RVMR REDUNDANT'
        if not R['prec']:
            v = 'INSUFFICIENT DATA'
        elif npass == 10:
            v = surv if R['high_pts'] > COST_PTS else surv + ' BUT SUB-COST'
        elif pooled_real and red_fail:
            v = red
        elif core and ((not gd[kind + '8']) or (not gd[kind + '9'])):
            v = 'UNSTABLE'
        else:
            fails = [row[0] for row in g if not row[3]]
            v = 'FAILED  (failing gates: %s)' % ', '.join(fails)
        if R['asym'] and npass == 10:
            v += '   [ASYMMETRIC]'
        print('\n  %s VERDICT: %s' % (tag, v))
        return v

    print('\n' + '=' * 78)
    print('VERDICTS (mechanical, frozen precedence)')
    print('=' * 78)
    v1 = verdict('H1', H1, g1, n1, 'MO')
    v2 = verdict('H2', H2, g2, n2, 'MT')

    print('\n' + '=' * 78)
    print('EXECUTION COMPLETE  (%.0f s)' % (time.time() - t0))
    print('H1 AND H2 SCORED SEPARATELY. NO COMBINATION. NO STRATEGY.')
    print('DEVELOPMENT ONLY. THIS PROJECT DOES NOT AUTHORIZE LIVE'
          ' TRADING.')
    print('=' * 78)


if __name__ == '__main__':
    main()
