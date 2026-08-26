#!/usr/bin/env python3
# ======================================================================
# ANOMALY-CONFIRM-V2 - ONE-SHOT HYPOTHESIS-SPECIFIC HISTORICAL CONFIRM
# H1 ORDINAL-V-TURN  +  H2 HALF-SESSION-LOW  (scored separately)
# ======================================================================
# AUTHORITATIVE PREREGISTRATION:
#   docs/ANOMALY_CONFIRM_V2_PREREGISTRATION.md
#   sha256 0d7bae634c58d835bcc09577881564a037e828b1249cec8ffb3c7123ddef8ac8
#   commit e6f3f06ca54dc6e14e46a5fe1910086436a4d851 (2026-08-26T11:10:11Z)
#
# CONFIRMATION WINDOW 2024-01-01 .. 2026-08-17 (hypothesis-specific
# unexamined historical). Discovery <= 2023-12-31 is read ONLY to
# recompute the frozen retention anchors (public data). ZERO rows
# >= 2026-08-26 consumed (asserted). MEMORY-PRED-V1 Lane A untouched.
#
# NO RETUNING. NO NEW CANDIDATES. NO STRATEGY. SUBMITS NO ORDERS.
# NOTHING FROZEN IS MODIFIED.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ----------------------------------------------------------------------
# PRE-COMPUTATION CHOICES (prereg silent on implementation; none favours
# a hypothesis; disclosed):
# (a) H1 cluster/window key = day[t+1] (outcome day), matching the S24
#     source and MEMORY-PRED. (b) H1 rotation permutation preserves the
#     r[t+1] outcome series and rotates the motif-id sequence; per-day
#     Vturn/est sums at every offset are computed by FFT circular
#     cross-correlation (Vturn count is offset-invariant), verified at
#     offset 0 against direct sums. numpy PCG64 seeded 20260826 draws
#     offsets; scalar bootstraps use random.Random(20260826). (c) VT8 /
#     HS8 controls use the corrected common-weight difference-of-means.
#     (d) H2 noon ATR/score read at the last morning bar (the noon
#     snapshot). (e) retention anchors recomputed on discovery in-engine.
# ======================================================================

import os, sys, math, random, collections, hashlib, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../rvmr'))
import rvmr_spec as RS
import rvmr_run as RV

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
PREREG = os.path.join(ROOT, 'docs', 'ANOMALY_CONFIRM_V2_PREREGISTRATION.md')
PREREG_SHA = ('0d7bae634c58d835bcc09577881564a037e828b1249cec8ffb3c7123'
              'ddef8ac8')
SEED = 20260826
B_MAIN, B_DESC, PERM = 20000, 4000, 20000
BP = 1e4
CONF_LO, CONF_HI, BOUND = '2024-01-01', '2026-08-17', '2026-08-26'
DISC_END = '2023-12-31'
COST_PTS = 0.87
STN = ('LOW', 'MEDIUM', 'HIGH')
PASS = {True: 'PASS', False: 'FAIL'}
# frozen programme ledger p-values (never-shrink), M_cum = 8
FAM6 = [(0.10050, 'SC'), (0.03570, 'MON'), (0.00005, 'MEMPRED'),
        (0.00005, 'HARU'), (0.36080, 'MOM-H1'), (0.70020, 'MOM-H2')]
# frozen motif encoding
VUP, EUP, VDN, EDN = '102', '012', '201', '210'


def quantile(sv, q):
    n = len(sv)
    hq = (n - 1) * q
    lo = int(math.floor(hq)); hi = min(lo + 1, n - 1)
    return sv[lo] + (hq - lo) * (sv[hi] - sv[lo])


def boot_diff(blocks, iters=B_MAIN, seed=SEED):
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
    out.sort(); m = len(out)
    le = sum(1 for x in out if x <= 0); ge = sum(1 for x in out if x >= 0)
    return obs, out[int(.025 * m)], out[int(.975 * m)], \
        max(2.0 * min(le, ge) / m, 1.0 / (m + 1.0))


def boot_mean(vals, iters=B_MAIN, seed=SEED):
    """simple bootstrap over a vector (H2: day = observation = cluster)."""
    v = np.asarray(vals, dtype=np.float64)
    n = len(v)
    if n < 15:
        return float('nan'), float('nan'), float('nan'), float('nan')
    obs = float(v.mean())
    rng = np.random.default_rng(seed)
    out = np.empty(iters)
    for i in range(iters):
        out[i] = v[rng.integers(0, n, n)].mean()
    out.sort()
    le = int((out <= 0).sum()); ge = int((out >= 0).sum())
    return obs, out[int(.025 * iters)], out[int(.975 * iters)], \
        max(2.0 * min(le, ge) / iters, 1.0 / (iters + 1.0))


def bh_exact(fam):
    ps = sorted(fam); M = len(ps); out = {}; prev = 1.0
    for rank in range(M, 0, -1):
        pv, nm = ps[rank - 1]
        prev = min(prev, pv * M / rank); out[nm] = prev
    return out


def atr20_arrays(h, l, c):
    n = len(c); out = np.full(n, np.nan)
    tr = collections.deque(); s = 0.0; prev = None
    for i in range(n):
        t = (h[i] - l[i]) if prev is None else max(
            h[i] - l[i], abs(h[i] - prev), abs(l[i] - prev))
        tr.append(t); s += t; prev = c[i]
        if len(tr) > 20:
            s -= tr.popleft()
        if len(tr) == 20:
            out[i] = s / 20.0
    return out


def std_delta(cell_ids, is_hi, is_lo, val):
    """common-weight difference-of-means over cells >=30 both sides."""
    agg = {}
    for cid, ih, il, v in zip(cell_ids, is_hi, is_lo, val):
        if not (ih or il):
            continue
        e = agg.get(cid)
        if e is None:
            e = agg[cid] = [0.0, 0, 0.0, 0]
        if ih:
            e[0] += v; e[1] += 1
        else:
            e[2] += v; e[3] += 1
    num = den = 0.0; used = 0
    for e in agg.values():
        if e[1] >= 30 and e[3] >= 30:
            w = e[1] + e[3]
            num += w * (e[0] / e[1] - e[2] / e[3]); den += w; used += 1
    return (num / den if den else float('nan')), used


def motif_of(x0, x1, x2):
    order = sorted(range(3), key=lambda j: (x0, x1, x2)[j])
    return '%d%d%d' % (order[0], order[1], order[2])


def main():
    t0 = time.time()
    print('=' * 78)
    print('ANOMALY-CONFIRM-V2   ONE-SHOT HYPOTHESIS-SPECIFIC CONFIRMATION')
    print('  prereg sha256 %s' % PREREG_SHA[:40])
    print('  commit e6f3f06ca54dc6e14e46a5fe1910086436a4d851')
    print('  CONFIRMED (hypothesis-specific historical) is the CEILING'
          ' label')
    print('  SUBMITS NO ORDERS. NO RETUNING. NO STRATEGY.')
    print('=' * 78)

    got = hashlib.sha256(open(PREREG, 'rb').read()).hexdigest()
    ok1 = (got == PREREG_SHA)
    ok3 = (RS.T1 == 1.270 and RS.T2 == 2.335 and RS.W == 1440)
    print('\nPHASE 0  prereg sha256 match %s   RVMR spec %s'
          % (ok1, ok3))
    if not (ok1 and ok3):
        print('ANOMALY-CONFIRM-V2 FREEZE FAILURE'); return

    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    N = len(D['c'])
    h = np.array(D['h']); l = np.array(D['l']); c = np.array(D['c'])
    em = np.array(D['em'], dtype=np.int64)
    mod = np.array(D['mod'], dtype=np.int32)
    day = D['day']
    rr_ = RS.trailing_ratio([D['h'][i] - D['l'][i] for i in range(N)])
    smap = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
    st = np.array([smap.get(RS.bucket(x) if x is not None else None, -1)
                   for x in rr_], dtype=np.int8)
    sc = np.array([x if x is not None else np.nan for x in rr_])
    atr = atr20_arrays(D['h'], D['l'], D['c'])
    post = sum(1 for dd in day if dd >= BOUND)
    print('  bars %d   %s .. %s   rows >= %s (firewall): %d'
          % (N, D['et'][0], D['et'][-1], BOUND, post))
    assert post == 0, 'PROSPECTIVE FIREWALL BREACH'
    # per-bar contiguous 1m log return
    r = np.full(N, np.nan)
    cont = (em[1:] - em[:-1] == 1) & (c[:-1] > 0) & (c[1:] > 0)
    r[1:][cont] = np.log(c[1:][cont] / c[:-1][cont])
    days_all = sorted(set(day))
    dayid = {d: k for k, d in enumerate(days_all)}
    print('  discovery days %d   confirmation days %d   (%.0f s)'
          % (sum(1 for d in days_all if d <= DISC_END),
             sum(1 for d in days_all if CONF_LO <= d <= CONF_HI),
             time.time() - t0))

    # ==================================================================
    # H1  ORDINAL-V-TURN
    # ==================================================================
    def h1_events(lo_day, hi_day):
        rows = []
        for t in range(2, N - 1):
            d1 = day[t + 1]
            if not (lo_day <= d1 <= hi_day):
                continue
            if em[t] - em[t - 2] != 2 or em[t + 1] - em[t] != 1:
                continue
            x0, x1, x2 = c[t - 2], c[t - 1], c[t]
            if x0 == x1 or x1 == x2 or x0 == x2:
                continue
            r1 = r[t + 1]
            if not (r1 == r1):
                continue
            m = motif_of(x0, x1, x2)
            lls = 1.0 if x2 > x1 else -1.0
            rows.append((dayid[d1], m, lls * r1 * BP, abs(x2 - x1) / c[t]
                         * BP, atr[t] / c[t] * BP if atr[t] == atr[t]
                         else np.nan, mod[t], st[t], r1 * BP))
        return rows

    print('\n' + '=' * 78)
    print('H1  ORDINAL-V-TURN')
    print('=' * 78)
    ev = h1_events(CONF_LO, CONF_HI)
    mcnt = collections.Counter(e[1] for e in ev)
    print('  confirmation motif events %d' % len(ev))
    for m in ('012', '021', '102', '120', '201', '210'):
        print('    %s  n %8d' % (m, mcnt[m]))
    # group masks
    cd = np.array([e[0] for e in ev])
    mot = np.array([e[1] for e in ev])
    ta = np.array([e[2] for e in ev])          # turnAligned (bp)
    llmag = np.array([e[3] for e in ev])
    atrb = np.array([e[4] for e in ev])
    todv = np.array([e[5] for e in ev])
    stv = np.array([e[6] for e in ev])
    isV = np.isin(mot, [VUP, VDN])
    isE = np.isin(mot, [EUP, EDN])
    Dn = len(days_all)

    def dblocks(mA, mB):
        d = {}
        for i in np.nonzero(mA | mB)[0]:
            k = cd[i]
            e = d.get(k)
            if e is None:
                e = d[k] = [0.0, 0, 0.0, 0]
            if mA[i]:
                e[0] += ta[i]; e[1] += 1
            if mB[i]:
                e[2] += ta[i]; e[3] += 1
        return list(d.values())

    draw, dlo, dhi, dp = boot_diff(dblocks(isV, isE))
    # discovery anchor
    evd = h1_events('0000', DISC_END)
    tad = np.array([e[2] for e in evd]); motd = np.array([e[1] for e in evd])
    disc_draw = (tad[np.isin(motd, [VUP, VDN])].mean()
                 - tad[np.isin(motd, [EUP, EDN])].mean())
    print('\n  PRIMARY  Delta_turn = E[ta|V-turn] - E[ta|established]')
    print('    holdout  %+0.4f bp   CI [%+0.4f, %+0.4f]   boot p %.5f'
          % (draw, dlo, dhi, dp))
    print('    discovery anchor %+0.4f bp   retention %.1f%%   floor'
          ' (1/3) %+0.4f' % (disc_draw, 100 * draw / disc_draw,
                             disc_draw / 3.0))
    # per-motif means (partially-exposed marginals; reported)
    print('  per-motif mean turnAligned (bp):  '
          + '  '.join('%s %+0.4f' % (m, ta[mot == m].mean())
                      for m in (VUP, EUP, VDN, EDN)))
    vup = ta[mot == VUP].mean() - ta[mot == EUP].mean()
    vdn = ta[mot == VDN].mean() - ta[mot == EDN].mean()
    print('  VT6 V-up vs est-up   %+0.4f bp  (%s)'
          % (vup, PASS[vup > 0]))
    print('  VT7 V-dn vs est-dn   %+0.4f bp  (%s)'
          % (vdn, PASS[vdn > 0]))
    # incremental-vs-lag1 demonstration
    lag1 = ta.mean()   # pooled turnAligned = lag1 direction-normalized
    print('  incremental check: pooled turnAligned (= lag-1 MEMORY-PRED'
          ' marginal) %+0.4f bp;  Delta_turn cancels it by construction'
          % lag1)

    # VT8 final-leg magnitude match
    good = np.isfinite(atrb)
    llq = np.sort(llmag)
    la, lb = quantile(llq, 1/3.), quantile(llq, 2/3.)
    aq = np.sort(atrb[good])
    aa, ab = quantile(aq, 1/3.), quantile(aq, 2/3.)
    ll_t = np.digitize(llmag, [la, lb])
    at_t = np.digitize(atrb, [aa, ab])
    cellid = (ll_t.astype(np.int64) * 100 + at_t.astype(np.int64) * 10
              + todv.astype(np.int64))
    dm, ncell = std_delta(cellid, isV, isE, ta)
    print('\n  VT8 final-leg-magnitude match (|lastleg| x ATR x ToD,'
          ' common weight)')
    print('    matched Delta_turn %+0.4f bp   raw %+0.4f   retention'
          ' %.1f%%   cells %d   -> %s'
          % (dm, draw, 100 * dm / draw if draw else float('nan'), ncell,
             PASS[dm > 0 and dm >= 0.5 * draw]))
    vt8 = dm > 0 and dm >= 0.5 * draw

    # VT-amp RVMR
    print('\n  VT-amp RVMR (secondary, corroborating): Delta_turn by RB[t]')
    amp = {}
    for k, nm in enumerate(STN):
        mk = stv == k
        dd2, lo2, hi2, _ = boot_diff(dblocks(isV & mk, isE & mk), B_DESC)
        amp[nm] = dd2
        print('    %-7s %+0.4f bp  CI [%+0.4f, %+0.4f]' % (nm, dd2, lo2, hi2))
    print('    HIGH > LOW amplification: %s' % (amp['HIGH'] > amp['LOW']))

    # VT9 ATR terciles
    atr_pos = 0
    print('\n  VT9 ATR terciles (Delta_turn):')
    for t3 in range(3):
        mk = at_t == t3
        dd2, lo2, hi2, _ = boot_diff(dblocks(isV & mk, isE & mk), B_DESC)
        if dd2 > 0:
            atr_pos += 1
        print('    ATR%d  %+0.4f bp  CI [%+0.4f, %+0.4f]' % (t3, dd2, lo2, hi2))
    print('    terciles > 0: %d/3' % atr_pos)

    # VT10 ToD
    tod_pos = 0
    print('  VT10 ToD (Delta_turn):')
    for t3, nm in enumerate(('OVN', 'AM', 'PM')):
        tb = np.where((todv >= 1081) | (todv <= 569), 0,
                      np.where(todv <= 750, 1, 2))
        mk = tb == t3
        dd2, lo2, hi2, _ = boot_diff(dblocks(isV & mk, isE & mk), B_DESC)
        if dd2 > 0:
            tod_pos += 1
        print('    %-4s %+0.4f bp  CI [%+0.4f, %+0.4f]' % (nm, dd2, lo2, hi2))
    print('    buckets > 0: %d/3' % tod_pos)

    # VT11 years, VT12 months
    yr_of = np.array([days_all[k][:4] for k in cd])
    print('  VT11 years:')
    yr_pos = 0; years = sorted(set(yr_of.tolist()))
    for y in years:
        mk = yr_of == y
        dv = ta[mk & isV].mean() - ta[mk & isE].mean()
        dmv, _ = std_delta(cellid[mk], isV[mk], isE[mk], ta[mk])
        if dv > 0:
            yr_pos += 1
        print('    %s  n %7d  raw %+0.4f  matched %+0.4f  Vup %+0.4f'
              '  Vdn %+0.4f'
              % (y, mk.sum(), dv, dmv,
                 ta[mk & (mot == VUP)].mean() - ta[mk & (mot == EUP)].mean(),
                 ta[mk & (mot == VDN)].mean() - ta[mk & (mot == EDN)].mean()))
    print('    years > 0: %d/%d' % (yr_pos, len(years)))
    mo_of = np.array([days_all[k][:7] for k in cd])
    mvals = []
    for mo in sorted(set(mo_of.tolist())):
        mk = mo_of == mo
        if (mk & isV).sum() and (mk & isE).sum():
            mvals.append((mo, ta[mk & isV].mean() - ta[mk & isE].mean()))
    mpos = sum(1 for _, x in mvals if x > 0)
    mvv = sorted(x for _, x in mvals)
    print('  VT12 months: %d total  %d positive  median %+0.4f  worst %s'
          '  best %s' % (len(mvals), mpos, mvv[len(mvv) // 2],
                         min(mvals, key=lambda z: z[1]),
                         max(mvals, key=lambda z: z[1])))

    # VT13 tails (within-group)
    vV = np.sort(np.abs(ta[isV]))[::-1]; vE = np.sort(np.abs(ta[isE]))[::-1]
    tails = {}
    for frac in (0.01, 0.05):
        thV = vV[max(1, int(round(frac * len(vV)))) - 1]
        thE = vE[max(1, int(round(frac * len(vE)))) - 1]
        mV = ta[isV][np.abs(ta[isV]) < thV].mean()
        mE = ta[isE][np.abs(ta[isE]) < thE].mean()
        tails[frac] = mV - mE
        print('  VT13 within-group trim %4.1f%%  Delta_turn %+0.4f bp'
              % (frac * 100, tails[frac]))
    vt13 = tails[0.01] > 0 and tails[0.05] > 0

    # rotation permutation (FFT)
    print('  rotation permutation (motif-id sequence; r[t+1] outcome'
          ' preserved):')
    order = np.argsort(cd, kind='stable')
    cds = cd[order]
    r1bp = np.array([e[7] for e in ev])          # r[t+1] in bp (signed)
    sVup = (mot == VUP).astype(np.float64)
    sVdn = (mot == VDN).astype(np.float64)
    sEup = (mot == EUP).astype(np.float64)
    sEdn = (mot == EDN).astype(np.float64)
    ud, starts = np.unique(cds, return_index=True)
    r1o = r1bp[order]
    Vsig = (sVup - sVdn)[order]; Esig = (sEup - sEdn)[order]
    segs = []
    baseV = baseE = 0.0
    NV = int(isV.sum()); NE_ = int(isE.sum())
    for a in range(len(ud)):
        s0 = starts[a]; s1 = starts[a + 1] if a + 1 < len(ud) else len(ev)
        n3 = s1 - s0
        rr1 = r1o[s0:s1]; vs = Vsig[s0:s1]; es = Esig[s0:s1]
        nv = int((np.abs(vs) > 0).sum()); ne = int((np.abs(es) > 0).sum())
        if nv == 0 and ne == 0:
            continue
        if n3 == 1:
            baseV += float((vs * rr1).sum()); baseE += float((es * rr1).sum())
            continue
        FR = np.fft.rfft(rr1)
        SV = np.fft.irfft(FR * np.conj(np.fft.rfft(vs)), n3)
        SE = np.fft.irfft(FR * np.conj(np.fft.rfft(es)), n3)
        assert abs(SV[0] - (vs * rr1).sum()) < 1e-3
        segs.append((SV, SE, n3))
    flatV = np.concatenate([s[0] for s in segs])
    flatE = np.concatenate([s[1] for s in segs])
    lens = np.array([s[2] for s in segs])
    bases = np.concatenate([[0], np.cumsum(lens)])[:-1]
    rng = np.random.default_rng(SEED)
    obs = abs(draw); cnt = 0; done = 0
    while done < PERM:
        k2 = min(2000, PERM - done)
        offs = 1 + (rng.random((k2, len(segs))) * (lens - 1)).astype(np.int64)
        gi = bases[None, :] + offs
        dV = (flatV[gi].sum(axis=1) + baseV) / NV
        dE = (flatE[gi].sum(axis=1) + baseE) / NE_
        cnt += int((np.abs(dV - dE) >= obs).sum()); done += k2
    perm_p = max((cnt + 1.0) / (PERM + 1.0), 1.0 / (PERM + 1.0))
    print('    permutation p = %.5f  (%.0f s)' % (perm_p, time.time() - t0))

    # RUN-AGE diagnostic (non-promotable)
    print('  RUN-AGE-HAZARD diagnostic (non-promotable): h(k) by state')
    hz = {nm: {k: [0, 0] for k in (1, 3, 5, 9)} for nm in ('POOL',) + STN}
    cur_s = cur_k = 0
    for i in range(1, N):
        if not (CONF_LO <= day[i] <= CONF_HI):
            cur_k = 0; continue
        ri = r[i]
        if not (ri == ri) or ri == 0.0:
            cur_k = 0; continue
        sgn = 1 if ri > 0 else -1
        cur_k = cur_k + 1 if sgn == cur_s else 1
        cur_s = sgn
        rn = r[i + 1] if i + 1 < N else np.nan
        if not (rn == rn) or rn == 0.0 or not (CONF_LO <= day[i+1] <= CONF_HI):
            continue
        kk = 1 if cur_k == 1 else (3 if cur_k in (3, 4) else
                                   (5 if cur_k in (5, 6, 7, 8) else
                                    (9 if cur_k >= 9 else None)))
        if kk is None:
            continue
        good = 1 if ((rn > 0) == (sgn > 0)) else 0
        hz['POOL'][kk][0] += good; hz['POOL'][kk][1] += 1
        if st[i] >= 0:
            nm = STN[st[i]]
            hz[nm][kk][0] += good; hz[nm][kk][1] += 1
    for nm in ('POOL',) + STN:
        print('    %-6s ' % nm + '  '.join(
            'h(%d) %.4f' % (k, hz[nm][k][0] / hz[nm][k][1])
            if hz[nm][k][1] > 200 else 'h(%d) -' % k for k in (1, 3, 5, 9)))

    # H1 minimum n + gates
    minn = min(mcnt[m] for m in (VUP, EUP, VDN, EDN))
    prec1 = minn >= 20000
    vt = []
    vt.append(('VT1', 'holdout integrity', 'all in-window; %d rows>=bound'
               % post, post == 0))
    vt.append(('VT2', 'motifs transported', 'tie-skip+em2 verbatim; 6'
               ' classes', True))
    vt.append(('VT3', 'Delta_turn > 0', '%+0.4f bp' % draw, draw > 0))
    vt.append(('VT4', 'CI excludes 0', '[%+0.4f,%+0.4f]' % (dlo, dhi),
               dlo > 0 or dhi < 0))
    q_pending = None  # filled after H2
    vt.append(('VT5', 'BH q<=.05 AND perm p<=.05', 'perm %.5f' % perm_p,
               None))   # BH filled later
    vt.append(('VT6', 'V-up > est-up', '%+0.4f' % vup, vup > 0))
    vt.append(('VT7', 'V-dn > est-dn', '%+0.4f' % vdn, vdn > 0))
    vt.append(('VT8', 'magnitude match >=0.5 raw', 'matched %+0.4f' % dm,
               vt8))
    vt.append(('VT9', '>=2/3 ATR terciles', '%d/3' % atr_pos, atr_pos >= 2))
    vt.append(('VT10', '>=2/3 ToD', '%d/3' % tod_pos, tod_pos >= 2))
    vt.append(('VT11', '>=2/3 years', '%d/%d' % (yr_pos, len(years)),
               yr_pos >= 2))
    vt.append(('VT12', '>=18 months', '%d/%d pos' % (mpos, len(mvals)),
               mpos >= 18))
    vt.append(('VT13', 'tails', '%+0.4f/%+0.4f' % (tails[0.01], tails[0.05]),
               vt13))
    vt.append(('VT14', 'retention >= 1/3 disc',
               '%.1f%%' % (100 * draw / disc_draw), draw >= disc_draw / 3.0))
    H1 = dict(draw=draw, dp=dp, perm=perm_p, vt=vt, dm=dm, vt8=vt8,
              prec=prec1, minn=minn, high_arm=ta[mot == VUP].mean(),
              vup=vup, vdn=vdn, amp=(amp['HIGH'] > amp['LOW']),
              disc=disc_draw)

    # ==================================================================
    # H2  HALF-SESSION-LOW
    # ==================================================================
    print('\n' + '=' * 78)
    print('H2  HALF-SESSION-LOW')
    print('=' * 78)

    def h2_days(lo_day, hi_day):
        am = collections.defaultdict(float); am_n = collections.Counter()
        pm = collections.defaultdict(float); pm_n = collections.Counter()
        noonRB = {}; noonATR = {}; noonSC = {}
        for i in range(1, N):
            d = day[i]
            if not (lo_day <= d <= hi_day) or not (r[i] == r[i]):
                continue
            m_ = mod[i]
            if 571 <= m_ <= 720:
                am[d] += r[i]; am_n[d] += 1; noonRB[d] = st[i]
                noonATR[d] = atr[i] / c[i] if atr[i] == atr[i] else np.nan
                noonSC[d] = sc[i]
            elif 721 <= m_ <= 960:
                pm[d] += r[i]; pm_n[d] += 1
        out = []
        for d in sorted(am):
            if am_n[d] >= 120 and pm_n[d] >= 180 and am[d] != 0:
                sgn = 1.0 if am[d] > 0 else -1.0
                out.append((d, sgn * pm[d] * BP, noonRB.get(d),
                            abs(am[d]) * BP, sgn, noonATR.get(d),
                            noonSC.get(d)))
        return out

    hd = h2_days(CONF_LO, CONF_HI)
    hdd = h2_days('0000', DISC_END)
    print('  confirmation eligible days %d   (discovery %d)'
          % (len(hd), len(hdd)))
    byrb = collections.Counter(x[2] for x in hd)
    print('  by noon RB:  LOW %d  MED %d  HIGH %d  (None %d)'
          % (byrb[0], byrb[1], byrb[2], byrb[-1]))
    aligned = {k: np.array([x[1] for x in hd if x[2] == k]) for k in (0, 1, 2)}
    pooled = np.array([x[1] for x in hd])
    print('  pooled aligned %+0.3f bp (CONTEXT ONLY, non-supporting)'
          % pooled.mean())
    for k, nm in enumerate(STN):
        v = aligned[k]
        if len(v):
            print('    %-7s n %4d  aligned %+8.3f bp  P(match) %.4f'
                  % (nm, len(v), v.mean(), (v > 0).mean()))
    low = aligned[0]
    lowm, llo, lhi, lp = boot_mean(low)
    disc_low = np.array([x[1] for x in hdd if x[2] == 0]).mean()
    print('\n  PRIMARY  E[aligned | noon LOW] = %+0.3f bp   CI [%+0.3f,'
          ' %+0.3f]   p %.5f' % (lowm, llo, lhi, lp))
    print('    discovery LOW %+0.3f bp   retention %.1f%%   floor +2.77'
          % (disc_low, 100 * lowm / disc_low))
    print('    economics: LOW mean %+0.3f bp' % lowm)

    # HS7 symmetry
    lpos = np.array([x[1] for x in hd if x[2] == 0 and x[4] > 0])
    lneg = np.array([x[1] for x in hd if x[2] == 0 and x[4] < 0])
    print('  HS7 direction symmetry: am>0 %+0.3f bp (n %d)   am<0 %+0.3f bp'
          ' (n %d)' % (lpos.mean(), len(lpos), lneg.mean(), len(lneg)))
    hs7 = lpos.mean() > 0 and lneg.mean() > 0

    # HS8 morning magnitude (median split of LOW |am|)
    lam = np.array([x[3] for x in hd if x[2] == 0])
    med_am = np.median(lam)
    lo_small = low[lam < med_am]; lo_big = low[lam >= med_am]
    print('  HS8 morning-magnitude split: small|am| %+0.3f (n %d)  big|am|'
          ' %+0.3f (n %d)' % (lo_small.mean(), len(lo_small), lo_big.mean(),
                              len(lo_big)))
    hs8 = lo_small.mean() > 0 and lo_big.mean() > 0

    # HS9 specificity LOW vs non-LOW
    nonlow = np.array([x[1] for x in hd if x[2] in (1, 2)])
    spec = lowm - nonlow.mean()
    # day-clustered here = day-level; simple two-sample bootstrap diff
    rng = np.random.default_rng(SEED)
    outs = np.empty(B_MAIN)
    for i in range(B_MAIN):
        a = low[rng.integers(0, len(low), len(low))].mean()
        b = nonlow[rng.integers(0, len(nonlow), len(nonlow))].mean()
        outs[i] = a - b
    outs.sort()
    slo, shi = outs[int(.025 * B_MAIN)], outs[int(.975 * B_MAIN)]
    print('  HS9 LOW-specificity: LOW - nonLOW %+0.3f bp  CI [%+0.3f,'
          ' %+0.3f]' % (spec, slo, shi))
    hs9 = spec > 0 and (slo > 0 or shi < 0)

    # HS10 ATR control (median split of LOW noon atrRel)
    latr = np.array([x[5] for x in hd if x[2] == 0])
    fin = np.isfinite(latr)
    med_atr = np.median(latr[fin])
    lo_lv = low[fin][latr[fin] < med_atr]; lo_hv = low[fin][latr[fin] >= med_atr]
    print('  HS10 ATR split: lowvol %+0.3f (n %d)  highvol %+0.3f (n %d)'
          % (lo_lv.mean(), len(lo_lv), lo_hv.mean(), len(lo_hv)))
    hs10 = lo_lv.mean() > 0 and lo_hv.mean() > 0

    # HS11 years, HS12 months
    print('  HS11 years:')
    hy_pos = 0
    lyears = sorted(set(x[0][:4] for x in hd if x[2] == 0))
    for y in lyears:
        vv = np.array([x[1] for x in hd if x[2] == 0 and x[0][:4] == y])
        p = np.array([x[1] for x in hd if x[2] == 0 and x[0][:4] == y
                      and x[4] > 0])
        n = np.array([x[1] for x in hd if x[2] == 0 and x[0][:4] == y
                      and x[4] < 0])
        if vv.mean() > 0:
            hy_pos += 1
        print('    %s  LOW days %3d  aligned %+8.3f bp  am>0 %+7.3f'
              '  am<0 %+7.3f' % (y, len(vv), vv.mean(),
                                 p.mean() if len(p) else float('nan'),
                                 n.mean() if len(n) else float('nan')))
    print('    LOW-years > 0: %d/%d' % (hy_pos, len(lyears)))
    lmonths = {}
    for x in hd:
        if x[2] == 0:
            lmonths.setdefault(x[0][:7], []).append(x[1])
    hm = [(k, float(np.mean(v))) for k, v in sorted(lmonths.items())]
    hmpos = sum(1 for _, x in hm if x > 0)
    print('  HS12 months: %d total  %d positive  median %+0.3f  worst %s'
          '  best %s' % (len(hm), hmpos, np.median([x for _, x in hm]),
                         min(hm, key=lambda z: z[1]),
                         max(hm, key=lambda z: z[1])))

    # HS13 tails
    ls = np.sort(low)[::-1]
    tl = {}
    for frac in (0.01, 0.05):
        k = max(1, int(round(frac * len(ls))))
        tl[frac] = ls[k:].mean()
        print('  HS13 remove top %4.1f%% (%d days)  LOW mean %+0.3f bp'
              % (frac * 100, k, tl[frac]))
    print('    median %+0.3f  10%%-trim %+0.3f  5 largest days %s'
          % (np.median(low),
             np.sort(low)[max(1, int(.05*len(low))):
                          len(low)-max(1, int(.05*len(low)))].mean(),
             ' '.join('%+0.1f' % x for x in ls[:5])))
    hs13 = tl[0.01] > 0 and tl[0.05] > 0

    # permutation: day sign-flip over LOW days
    rng = np.random.default_rng(SEED)
    obs = abs(lowm); cnt = 0
    for _ in range(PERM):
        s = (low * rng.choice([-1.0, 1.0], len(low))).mean()
        if abs(s) >= obs:
            cnt += 1
    hperm = max((cnt + 1.0) / (PERM + 1.0), 1.0 / (PERM + 1.0))
    print('  permutation (day sign-flip) p = %.5f' % hperm)

    prec2 = len(low) >= 120
    hs = []
    hs.append(('HS1', 'exact LOW subgroup def', 'S30 verbatim', True))
    hs.append(('HS2', 'n >= 120 LOW days', '%d' % len(low), prec2))
    hs.append(('HS3', 'LOW aligned > 0', '%+0.3f bp' % lowm, lowm > 0))
    hs.append(('HS4', 'retention >= +2.77 bp', '%+0.3f bp' % lowm,
               lowm >= 2.77))
    hs.append(('HS5', 'CI excludes 0', '[%+0.3f,%+0.3f]' % (llo, lhi),
               llo > 0 or lhi < 0))
    hs.append(('HS6', 'BH q<=.05 AND perm<=.05', 'perm %.5f' % hperm, None))
    hs.append(('HS7', 'both morning signs > 0',
               'am>0 %+0.3f am<0 %+0.3f' % (lpos.mean(), lneg.mean()), hs7))
    hs.append(('HS8', 'morning-magnitude both halves > 0',
               '%+0.3f/%+0.3f' % (lo_small.mean(), lo_big.mean()), hs8))
    hs.append(('HS9', 'LOW-specific vs nonLOW',
               '%+0.3f CI [%+0.3f,%+0.3f]' % (spec, slo, shi), hs9))
    hs.append(('HS10', 'ATR both halves > 0',
               '%+0.3f/%+0.3f' % (lo_lv.mean(), lo_hv.mean()), hs10))
    hs.append(('HS11', '>=2/3 years', '%d/%d' % (hy_pos, len(lyears)),
               hy_pos >= 2))
    hs.append(('HS12', '>=17 months', '%d/%d' % (hmpos, len(hm)),
               hmpos >= 17))
    hs.append(('HS13', 'tails', '%+0.3f/%+0.3f' % (tl[0.01], tl[0.05]),
               hs13))
    hs.append(('HS14', 'no subgroup rescue', 'pooled not used as support',
               True))
    H2 = dict(low=lowm, lp=lp, perm=hperm, hs=hs, prec=prec2, spec=spec,
              hs7=hs7, hs13=hs13, disc=disc_low, nlow=len(low))

    # ==================================================================
    # JOINT MULTIPLICITY  + fill BH gates
    # ==================================================================
    print('\n' + '=' * 78)
    print('JOINT MULTIPLICITY')
    print('=' * 78)
    p1, p2 = H1['dp'], H2['lp']
    ps = sorted([(p1, 'H1'), (p2, 'H2')])
    q = {}
    q[ps[1][1]] = ps[1][0]
    q[ps[0][1]] = min(2.0 * ps[0][0], ps[1][0])
    print('  raw p:  H1 %.5f   H2 %.5f' % (p1, p2))
    print('  BH q (M=2 binding):  H1 %.5f   H2 %.5f' % (q['H1'], q['H2']))
    q8 = bh_exact(FAM6 + [(p1, 'V2-H1'), (p2, 'V2-H2')])
    print('  BH q (M_cum=8 non-binding):  H1 %.5f   H2 %.5f'
          % (q8['V2-H1'], q8['V2-H2']))

    for tab, key, perm in ((vt, 'H1', H1['perm']), (hs, 'H2', H2['perm'])):
        for i, row in enumerate(tab):
            if row[3] is None:
                ok = (q[key] <= 0.05) and (perm <= 0.05)
                tab[i] = (row[0], row[1], 'q %.5f, perm %.5f'
                          % (q[key], perm), ok)

    print('\n' + '=' * 78)
    print('VT1-VT14 GATES')
    print('=' * 78)
    for k, crit, val, ok in vt:
        print('  %-5s %-40s %-38s %s' % (k, crit, val, PASS[ok]))
    n_vt = sum(1 for _, _, _, ok in vt if ok)
    print('  VT PASSED %d / 14' % n_vt)

    print('\n' + '=' * 78)
    print('HS1-HS14 GATES')
    print('=' * 78)
    for k, crit, val, ok in hs:
        print('  %-5s %-40s %-42s %s' % (k, crit, val, PASS[ok]))
    n_hs = sum(1 for _, _, _, ok in hs if ok)
    print('  HS PASSED %d / 14' % n_hs)

    # verdicts
    def h1_verdict():
        gd = {row[0]: row[3] for row in vt}
        if not H1['prec']:
            return 'INSUFFICIENT DATA'
        if n_vt == 14:
            arm = H1['high_arm']
            return ('CONFIRMED (hypothesis-specific historical)'
                    if abs(arm) > COST_PTS else
                    'CONFIRMED (hypothesis-specific historical) BUT'
                    ' SUB-COST')
        core = gd['VT3'] and gd['VT4'] and gd['VT5']
        if core and not gd['VT8']:
            return 'PATH-SHAPE REDUNDANT'
        if core and (not gd['VT11'] or not gd['VT12']):
            return 'UNSTABLE'
        if core:
            return 'PARTIALLY CONFIRMED'
        return 'FAILED  (failing: %s)' % ', '.join(
            row[0] for row in vt if not row[3])

    def h2_verdict():
        gd = {row[0]: row[3] for row in hs}
        if not H2['prec']:
            return 'INSUFFICIENT DATA'
        if n_hs == 14:
            return 'CONFIRMED (hypothesis-specific historical)'
        core = gd['HS3'] and gd['HS5'] and gd['HS6']
        if core and not gd['HS13']:
            return 'TAIL-DEPENDENT'
        if core and not gd['HS7']:
            return 'PARTIALLY CONFIRMED [ASYMMETRIC]'
        if core and (not gd['HS11'] or not gd['HS12']):
            return 'UNSTABLE'
        if core:
            return 'PARTIALLY CONFIRMED'
        return 'FAILED  (failing: %s)' % ', '.join(
            row[0] for row in hs if not row[3])

    print('\n' + '=' * 78)
    print('VERDICTS')
    print('=' * 78)
    print('  H1 ORDINAL-V-TURN:   %s' % h1_verdict())
    print('  H2 HALF-SESSION-LOW: %s' % h2_verdict())
    print('\nEXECUTION COMPLETE  (%.0f s)' % (time.time() - t0))
    print('CONFIRMED ceiling = hypothesis-specific historical. NO'
          ' STRATEGY. NO ORDERS.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
    print('=' * 78)


if __name__ == '__main__':
    main()
