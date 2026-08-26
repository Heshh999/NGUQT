#!/usr/bin/env python3
# ======================================================================
# MEMORY-MATH-IFVG-V1  -  SHARED MACHINERY
# ======================================================================
# AUTHORITATIVE PREREGISTRATION
#   docs/MEMORY_MATH_IFVG_V1_PREREGISTRATION.md
#   sha256 313127d24a8178b7064e9d90af38d7ecaac18d9110f8ba46f0b7827fbc2dac9b
#   commit 7a9136feb54f201295d83e37e0b0c929310de827
#
# This module holds ONLY frozen machinery: the canonical grid, the frozen
# feature formulas, and the frozen inference primitives. It computes no
# outcome and makes no decision.
#
# SUBMITS NO ORDERS. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os
import sys
import math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
import rvmr_spec as RS                                        # noqa: E402
import rvmr_run as RV                                         # noqa: E402

SEED = 20260826
B_BOOT = 20000
PERM = 20000
COST = 0.87
BP = 1e4
ANCHOR = 0.30013          # unconditional MEMORY-PRED Delta, bp
MATERIAL_BP = 0.60        # MA3 floor = 2 x anchor
ANCHOR_PP = 3.2469        # unconditional continuation edge, pp
MATERIAL_PP = 6.4938      # MA3 transport for rate-valued primaries
FIREWALL = '2026-08-26'   # no row at/after this ET date may be consumed
TODN = ('OVN', 'AM', 'PM')
STN = ('LOW', 'MEDIUM', 'HIGH')
NAN = float('nan')


# ====================================================================== data
def load_all():
    """Canonical grid + every frozen feature. Nothing outcome-dependent."""
    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    et = D['et']
    day = D['day']
    n_raw = len(et)

    # ---- prospective firewall, applied BEFORE any feature is built ----
    excl = [i for i in range(n_raw) if day[i] >= FIREWALL]
    fw = {'n': len(excl),
          'first': et[excl[0]] if excl else None,
          'last': et[excl[-1]] if excl else None}
    if excl:
        keep = n_raw - len(excl)
        for k in D:
            D[k] = D[k][:keep] if excl[0] == keep else \
                [D[k][i] for i in range(n_raw) if day[i] < FIREWALL]
        et, day = D['et'], D['day']

    N = len(D['c'])
    c = np.asarray(D['c'], dtype=np.float64)
    h = np.asarray(D['h'], dtype=np.float64)
    lo = np.asarray(D['l'], dtype=np.float64)
    em = np.asarray(D['em'], dtype=np.int64)
    mod = np.asarray(D['mod'], dtype=np.int32)

    # ---- contiguity runs (frozen em clock; gaps skipped, never bridged)
    step1 = np.zeros(N, dtype=bool)
    step1[1:] = (em[1:] - em[:-1]) == 1
    bwd = np.zeros(N, dtype=np.int32)
    for i in range(1, N):
        bwd[i] = bwd[i - 1] + 1 if step1[i] else 0
    fwd = np.zeros(N, dtype=np.int32)
    for i in range(N - 2, -1, -1):
        fwd[i] = fwd[i + 1] + 1 if step1[i + 1] else 0

    # ---- returns (frozen convention) ----
    r = np.full(N, NAN)
    ok = (bwd >= 1) & (c > 0)
    ok[1:] &= c[:-1] > 0
    idx = np.nonzero(ok)[0]
    idx = idx[idx >= 1]
    r[idx] = np.log(c[idx] / c[idx - 1])

    # ---- frozen RVMR (called through the frozen implementation) ----
    rng_l = (h - lo).tolist()
    rr_l = RS.trailing_ratio(rng_l)
    rr = np.array([x if x is not None else NAN for x in rr_l],
                  dtype=np.float64)
    rb = np.full(N, -1, dtype=np.int8)          # 0 LOW 1 MEDIUM 2 HIGH
    good = ~np.isnan(rr)
    rb[good & (rr < RS.T1)] = 0
    rb[good & (rr >= RS.T1) & (rr <= RS.T2)] = 1
    rb[good & (rr > RS.T2)] = 2

    # ---- frozen atr20 ----
    atr = _atr20(h, lo, c)

    # ---- day ids / years / ToD ----
    days_all = sorted(set(day))
    dmap = {d: k for k, d in enumerate(days_all)}
    dayid = np.array([dmap[d] for d in day], dtype=np.int32)
    year = np.array([int(d[:4]) for d in day], dtype=np.int16)
    tod = np.where((mod >= 1081) | (mod <= 569), 0,
                   np.where(mod <= 750, 1, 2)).astype(np.int8)

    # ---- A1 state age (consecutive bars in the same defined state) ----
    age = np.zeros(N, dtype=np.int16)
    prev = -1
    a = 0
    for i in range(N):
        s = rb[i]
        if s < 0:
            a = 0
        elif i > 0 and step1[i] and s == prev and a > 0:
            a = min(a + 1, 240)
        else:
            a = 1
        age[i] = a
        prev = s

    # ---- A4 run length of nonzero return sign ----
    sgn = np.zeros(N, dtype=np.int8)
    nz = ~np.isnan(r) & (r != 0.0)
    sgn[nz & (r > 0)] = 1
    sgn[nz & (r < 0)] = -1
    runlen = np.zeros(N, dtype=np.int16)
    rl = 0
    for i in range(N):
        if sgn[i] == 0 or not step1[i]:
            rl = 1 if sgn[i] != 0 else 0
        elif sgn[i] == sgn[i - 1] and rl > 0:
            rl = min(rl + 1, 240)
        else:
            rl = 1 if sgn[i] != 0 else 0
        runlen[i] = rl

    # ---- A3 score velocity  rr[t]-rr[t-5] ----
    vel = np.full(N, NAN)
    m5 = (bwd >= 5)
    ii = np.nonzero(m5)[0]
    ii = ii[ii >= 5]
    vel[ii] = rr[ii] - rr[ii - 5]

    # ---- A5 path efficiency over 10 bars ----
    absd = np.zeros(N)
    absd[1:] = np.abs(c[1:] - c[:-1])
    cs = np.concatenate([[0.0], np.cumsum(absd)])
    eff = np.full(N, NAN)
    jj = np.nonzero(bwd >= 10)[0]
    jj = jj[jj >= 10]
    denom = cs[jj + 1] - cs[jj - 9]
    num = np.abs(c[jj] - c[jj - 10])
    okd = denom > 0
    eff[jj[okd]] = num[okd] / denom[okd]

    # ---- A6 flip count over r[t-7..t] (8 returns, all nonzero) ----
    flips = np.full(N, -1, dtype=np.int8)
    kk = np.nonzero(bwd >= 8)[0]
    kk = kk[kk >= 8]
    if kk.size:
        win = np.stack([sgn[kk - q] for q in range(7, -1, -1)], axis=1)
        allnz = (win != 0).all(axis=1)
        ch = (win[:, 1:] != win[:, :-1]).sum(axis=1).astype(np.int8)
        flips[kk[allnz]] = ch[allnz]

    # ---- A7 volatility trajectory atr[t]/atr[t-15] ----
    va = np.full(N, NAN)
    pp = np.nonzero(bwd >= 15)[0]
    pp = pp[pp >= 15]
    d0 = atr[pp - 15]
    okv = (~np.isnan(atr[pp])) & (~np.isnan(d0)) & (d0 > 0)
    va[pp[okv]] = atr[pp[okv]] / d0[okv]

    return {'N': N, 'et': et, 'day': day, 'c': c, 'h': h, 'l': lo,
            'em': em, 'mod': mod, 'r': r, 'rr': rr, 'rb': rb, 'atr': atr,
            'dayid': dayid, 'nd': len(days_all), 'year': year, 'tod': tod,
            'bwd': bwd, 'fwd': fwd, 'step1': step1, 'age': age,
            'sgn': sgn, 'runlen': runlen, 'vel': vel, 'eff': eff,
            'flips': flips, 'va': va, 'firewall': fw,
            'days_all': days_all, 'n_raw': n_raw}


def _atr20(h, lo, c):
    n = len(c)
    tr = np.empty(n)
    tr[0] = h[0] - lo[0]
    tr[1:] = np.maximum.reduce([h[1:] - lo[1:], np.abs(h[1:] - c[:-1]),
                                np.abs(lo[1:] - c[:-1])])
    out = np.full(n, NAN)
    cs = np.concatenate([[0.0], np.cumsum(tr)])
    out[19:] = (cs[20:] - cs[:-20]) / 20.0
    return out


# ================================================================ inference
def _mult_apply(nb, iters, seed, mats):
    """Day-cluster bootstrap: resample nb whole days with replacement and
    return the resampled column sums of every supplied per-day vector.
    All vectors share the SAME resample, which is what makes a paired
    difference of means valid."""
    rng = np.random.default_rng(seed)
    M = np.stack(mats, axis=1)                       # (nb, ncols)
    outs = np.empty((iters, M.shape[1]))
    done = 0
    base = None
    while done < iters:
        k = min(1000, iters - done)
        idx = rng.integers(0, nb, size=(k, nb))
        if base is None or len(base) != k:
            base = np.arange(k)[:, None] * nb
        W = np.bincount((base + idx).ravel(),
                        minlength=k * nb).reshape(k, nb).astype(np.float64)
        outs[done:done + k] = W @ M
        done += k
    return [outs[:, a] for a in range(M.shape[1])]


def dc_diff_cw(dayid, y, ma, mb, cells, nd, minc,
               iters=B_BOOT, seed=SEED):
    """Day-clustered bootstrap of the COMMON-WEIGHT standardised
    difference of means. The cell set and the cell weights are frozen
    from the observed sample; only the day resample varies."""
    use, wts, mats = [], [], []
    for cv in np.unique(cells):
        if cv < 0:
            continue
        sa = ma & (cells == cv)
        sb = mb & (cells == cv)
        na, nb2 = int(sa.sum()), int(sb.sum())
        if na < minc or nb2 < minc:
            continue
        use.append(cv)
        wts.append(float(na + nb2))
        mats += [np.bincount(dayid[sa], weights=y[sa], minlength=nd),
                 np.bincount(dayid[sa], minlength=nd).astype(np.float64),
                 np.bincount(dayid[sb], weights=y[sb], minlength=nd),
                 np.bincount(dayid[sb], minlength=nd).astype(np.float64)]
    if not use:
        return NAN, NAN, NAN, NAN, 0, 0
    keep = np.zeros(nd, dtype=bool)
    for a in range(1, len(mats), 4):
        keep |= mats[a] > 0
    for a in range(3, len(mats), 4):
        keep |= mats[a] > 0
    mats = [m[keep] for m in mats]
    nb = int(keep.sum())
    W = np.asarray(wts)
    obs = float(sum(W[i] * (mats[4 * i].sum() / mats[4 * i + 1].sum()
                            - mats[4 * i + 2].sum() / mats[4 * i + 3].sum())
                    for i in range(len(use))) / W.sum())
    if nb < 15:
        return obs, NAN, NAN, NAN, len(use), nb
    res = _mult_apply(nb, iters, seed, mats)
    num = np.zeros(iters)
    okall = np.ones(iters, dtype=bool)
    for i in range(len(use)):
        sa, ca, sb, cb = res[4 * i:4 * i + 4]
        okall &= (ca > 0) & (cb > 0)
        with np.errstate(invalid='ignore', divide='ignore'):
            num += W[i] * np.where((ca > 0) & (cb > 0),
                                   sa / ca - sb / cb, 0.0)
    v = np.where(okall, num / W.sum(), np.nan)
    lo, hi, p = _ci_p(v)
    return obs, lo, hi, p, len(use), nb


def _ci_p(vals):
    v = np.sort(vals[~np.isnan(vals)])
    m = len(v)
    if m < 100:
        return NAN, NAN, NAN
    lo = v[int(0.025 * m)]
    hi = v[int(0.975 * m)]
    le = int(np.sum(v <= 0))
    ge = int(np.sum(v >= 0))
    p = max(2.0 * min(le, ge) / m, 1.0 / (m + 1.0))
    return lo, hi, p


def dc_mean(dayid, y, nd, iters=B_BOOT, seed=SEED):
    """Day-clustered bootstrap of a mean. Returns obs, lo, hi, p, ndays."""
    S = np.bincount(dayid, weights=y, minlength=nd)
    C = np.bincount(dayid, minlength=nd).astype(np.float64)
    k = C > 0
    S, C = S[k], C[k]
    nb = len(C)
    obs = S.sum() / C.sum() if C.sum() else NAN
    if nb < 15:
        return obs, NAN, NAN, NAN, nb
    bs, bc = _mult_apply(nb, iters, seed, [S, C])
    with np.errstate(invalid='ignore', divide='ignore'):
        v = np.where(bc > 0, bs / bc, np.nan)
    lo, hi, p = _ci_p(v - obs + obs)
    return obs, lo, hi, p, nb


def dc_diff(dayid, y, ma, mb, nd, iters=B_BOOT, seed=SEED):
    """Day-clustered bootstrap of meanA - meanB. Same resample for both."""
    SA = np.bincount(dayid[ma], weights=y[ma], minlength=nd)
    CA = np.bincount(dayid[ma], minlength=nd).astype(np.float64)
    SB = np.bincount(dayid[mb], weights=y[mb], minlength=nd)
    CB = np.bincount(dayid[mb], minlength=nd).astype(np.float64)
    k = (CA + CB) > 0
    SA, CA, SB, CB = SA[k], CA[k], SB[k], CB[k]
    nb = len(CA)
    obs = (SA.sum() / CA.sum() - SB.sum() / CB.sum()) \
        if CA.sum() and CB.sum() else NAN
    if nb < 15:
        return obs, NAN, NAN, NAN, nb
    bsa, bca, bsb, bcb = _mult_apply(nb, iters, seed, [SA, CA, SB, CB])
    with np.errstate(invalid='ignore', divide='ignore'):
        v = np.where((bca > 0) & (bcb > 0), bsa / bca - bsb / bcb, np.nan)
    lo, hi, p = _ci_p(v)
    return obs, lo, hi, p, nb


def day_slices(dayid_ev):
    """Contiguous per-day slices of an event array already in time order."""
    assert np.all(np.diff(dayid_ev) >= 0), 'events not day-ordered'
    u, st, ct = np.unique(dayid_ev, return_index=True, return_counts=True)
    return st.astype(np.int64), ct.astype(np.int64)


def _rot_corr(st, ct, y, g):
    """corr[s+k] = sum_j y[j] * g[(j-k) mod n], per day, all offsets."""
    out = np.empty(len(y))
    for s, n in zip(st, ct):
        yd = y[s:s + n]
        gd = g[s:s + n]
        if n == 1:
            out[s] = yd[0] * gd[0]
            continue
        out[s:s + n] = np.fft.irfft(
            np.conj(np.fft.rfft(gd, n)) * np.fft.rfft(yd, n), n)
    return out


def rot_perm(st, ct, y, glist, combine, obs, iters=PERM, seed=SEED):
    """Within-day circular rotation null (frozen). glist: label vectors
    rotated jointly; combine(sums)->statistic. Returns p and a degeneracy
    fraction (share of events on days too short to rotate)."""
    corrs = [_rot_corr(st, ct, y, g) for g in glist]
    nd = len(st)
    rng = np.random.default_rng(seed)
    hits = 0
    done = 0
    tot = 0
    while done < iters:
        k = min(1000, iters - done)
        off = rng.integers(0, np.maximum(ct, 1)[None, :], size=(k, nd))
        idx = st[None, :] + off
        sums = [cc[idx].sum(axis=1) for cc in corrs]
        stat = combine(sums)
        hits += int(np.sum(np.abs(stat) >= abs(obs) - 1e-15))
        tot += k
        done += k
    p = max(hits / tot, 1.0 / (tot + 1.0))
    degen = float(np.sum(ct[ct < 3])) / float(np.sum(ct))
    return p, degen


def bh(pvals):
    """Benjamini-Hochberg q-values over the frozen family."""
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    o = np.argsort(p)
    q = np.empty(m)
    prev = 1.0
    for rank in range(m - 1, -1, -1):
        i = o[rank]
        val = min(prev, m * p[i] / (rank + 1))
        q[i] = val
        prev = val
    return q


# ============================================================== diagnostics
def common_weight(y, ma, mb, cells, minc):
    """Corrected common-weight difference-of-means standardisation."""
    num = den = 0.0
    used = 0
    for cv in np.unique(cells):
        if cv < 0:
            continue
        sa = ma & (cells == cv)
        sb = mb & (cells == cv)
        na, nb2 = int(sa.sum()), int(sb.sum())
        if na < minc or nb2 < minc:
            continue
        d = y[sa].mean() - y[sb].mean()
        w = na + nb2
        num += w * d
        den += w
        used += 1
    return (num / den if den else NAN), used


def split_sign(y, ma, mb, key, ref):
    """Sign agreement of a contrast across the levels of `key`."""
    out = {}
    agree = 0
    for kv in sorted(set(key.tolist())):
        sa = ma & (key == kv)
        sb = mb & (key == kv)
        if sa.sum() == 0 or sb.sum() == 0:
            out[kv] = (int(sa.sum()), int(sb.sum()), NAN)
            continue
        d = y[sa].mean() - y[sb].mean()
        out[kv] = (int(sa.sum()), int(sb.sum()), d)
        if (d > 0) == (ref > 0) and d == d:
            agree += 1
    return out, agree


def split_sign_mean(y, m, key, ref):
    out = {}
    agree = 0
    for kv in sorted(set(key.tolist())):
        s = m & (key == kv)
        if s.sum() == 0:
            out[kv] = (0, NAN)
            continue
        v = y[s].mean()
        out[kv] = (int(s.sum()), v)
        if (v > 0) == (ref > 0):
            agree += 1
    return out, agree


def trim_diff(y, ma, mb, frac):
    """Within-condition trim of the largest |y| in each arm."""
    def keep(m):
        v = np.abs(y[m])
        if v.size == 0:
            return m.copy()
        cut = np.quantile(v, 1.0 - frac)
        k = m.copy()
        k[np.nonzero(m)[0][v > cut]] = False
        return k
    ka, kb = keep(ma), keep(mb)
    if ka.sum() == 0 or kb.sum() == 0:
        return NAN
    return y[ka].mean() - y[kb].mean()


def trim_mean(y, m, frac):
    v = np.abs(y[m])
    if v.size == 0:
        return NAN
    cut = np.quantile(v, 1.0 - frac)
    k = m.copy()
    k[np.nonzero(m)[0][v > cut]] = False
    return y[k].mean() if k.sum() else NAN


def terciles(v):
    g = v[~np.isnan(v)]
    return np.quantile(g, 1.0 / 3.0), np.quantile(g, 2.0 / 3.0)


def tercode(v, cuts):
    out = np.full(len(v), -1, dtype=np.int8)
    g = ~np.isnan(v)
    out[g & (v <= cuts[0])] = 0
    out[g & (v > cuts[0]) & (v <= cuts[1])] = 1
    out[g & (v > cuts[1])] = 2
    return out
