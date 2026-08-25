#!/usr/bin/env python3
# ======================================================================
# RVMR-VALIDATION-V1 - shared library
# ======================================================================
# Frozen by docs/RVMR_VALIDATION_V1_PREREGISTRATION.md
#   sha256 025598ad685e617ca8ea4d2d044be52e38343de22ac2db899a22958ea4b161c3
#   commit 531759c4101a36c2622b445ebde0eb50d0d015aa
#
# OFFLINE COMPANION STUDY. Imports the frozen RVMR spec and uses it
# UNCHANGED. Nothing frozen is modified anywhere in this package.
#
# THIS MODULE SUBMITS NO ORDERS.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, glob, math, random, statistics, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../rvmr', '../xmarket'):
    sys.path.insert(0, os.path.join(HERE, p))
import rvmr_spec as S            # FROZEN - read only
import rvmr_run as RV            # FROZEN - read only

ES_DIR = '/home/user/NGUQT/scratchpad/es_bar1m'
HOR = S.HOR
SEED = S.SEED
EPOCH = datetime.datetime(2019, 1, 1)


def med(x):
    return statistics.median(x) if x else float('nan')


def mean(x):
    return sum(x) / len(x) if x else float('nan')


# ==================================================== ES loader
def load_es(es_dir=ES_DIR):
    """ES 1m bars -> the SAME columnar layout rvmr_run.load_bars produces,
    so the frozen feature/universe code runs on ES without modification.

    Only genuine 1m rows are read (the capture schema is 1m-only, but the
    filter is kept so the loader is safe against the LTF schema too).
    Nothing is interpolated or forward-filled; a missing minute simply
    breaks contiguity and voids the affected windows."""
    rows = []
    for f in sorted(glob.glob(os.path.join(es_dir, '*.csv'))):
        with open(f, newline='') as fh:
            rd = csv.reader(fh)
            h = next(rd)
            ix = {c.strip().lower(): i for i, c in enumerate(h)}
            ti = ix.get('timestampet')
            tf = ix.get('timeframe')
            need = [ix.get(k) for k in ('open', 'high', 'low', 'close', 'volume')]
            if ti is None or any(v is None for v in need):
                continue
            for r in rd:
                if len(r) != len(h):
                    continue
                if tf is not None and r[tf] != '1m':
                    continue
                try:
                    rows.append((r[ti], float(r[need[0]]), float(r[need[1]]),
                                 float(r[need[2]]), float(r[need[3]]),
                                 float(r[need[4]] or 0)))
                except (ValueError, IndexError):
                    continue
    rows.sort(key=lambda r: r[0])
    # first-wins dedupe on identical stamps (there are none, but the
    # guard is kept so a future re-capture cannot silently double a day)
    out = {'et': [], 'day': [], 'mod': [], 'em': [], 'o': [], 'h': [],
           'l': [], 'c': [], 'v': []}
    seen = set()
    for et, o, hh, l, c, v in rows:
        if et in seen:
            continue
        seen.add(et)
        t = datetime.datetime.strptime(et, '%Y-%m-%d %H:%M:%S')
        out['et'].append(et)
        out['day'].append(et[:10])
        out['mod'].append(t.hour * 60 + t.minute)
        out['em'].append(int((t - EPOCH).total_seconds() // 60))
        out['o'].append(o); out['h'].append(hh); out['l'].append(l)
        out['c'].append(c); out['v'].append(v)
    return out


def load_nq():
    RV.STAMP_SHIFT = 0
    return RV.load_bars()


# ============================================ frozen feature builder
def features(D, want_excursion=True):
    """The FROZEN rvmr_run.features construction, transcribed so it can
    also carry the extra causal fields Track B needs. The score, bucket,
    universe gate, horizons and targets are byte-for-byte the frozen
    definitions - only additional CAUSAL columns are appended, and they
    never alter the gate."""
    n = len(D['c'])
    rng = [D['h'][i] - D['l'][i] for i in range(n)]
    rr = S.trailing_ratio(rng)
    vr = S.trailing_ratio(D['v'])
    bars = list(zip(D['et'], D['o'], D['h'], D['l'], D['c'], D['v']))
    atr = S.atr20(bars)
    # ---- FROZEN ATR CONTROL: trailing_ratio applied to ATR20, the very
    # ---- same construction RVMR uses; current bar excluded from the
    # ---- normaliser. Pre-registered before any result existed.
    atr_ratio = S.trailing_ratio([a if a is not None else 0.0 for a in atr])

    U = {'i': [], 'day': [], 'year': [], 'mod': [], 'rr': [], 'vr': [],
         'rb': [], 'vb': [], 'atr': [], 'atrr': []}
    for h in HOR:
        U['abs%d' % h] = []
    if want_excursion:
        U['mfe60'] = []; U['mae60'] = []
    for j in range(n - 60):
        m = D['mod'][j]
        if not (S.RTH_START <= m <= S.RTH_END and (S.RTH_END - m) >= 60):
            continue
        if atr[j] is None or atr[j] <= 0:
            continue
        if rr[j] is None or vr[j] is None:
            continue
        if D['em'][j + 60] - D['em'][j] != 60:
            continue
        px = D['c'][j]
        mfe = mae = 0.0
        for k in range(1, 61):
            u = D['h'][j + k] - px
            d_ = px - D['l'][j + k]
            if u > mfe:
                mfe = u
            if d_ > mae:
                mae = d_
            if k in (5, 10, 15, 30, 60):
                U['abs%d' % k].append(abs(D['c'][j + k] - px))
        U['i'].append(j)
        U['day'].append(D['day'][j])
        U['year'].append(D['day'][j][:4])
        U['mod'].append(D['mod'][j])
        U['rr'].append(rr[j]); U['vr'].append(vr[j])
        U['rb'].append(S.bucket(rr[j])); U['vb'].append(S.bucket(vr[j]))
        U['atr'].append(atr[j])
        U['atrr'].append(atr_ratio[j])
        if want_excursion:
            U['mfe60'].append(mfe); U['mae60'].append(mae)
    return U


# ==================================================== statistics
def spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return float('nan')
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else float('nan')


def day_spearman(days, xs, ys):
    """Per-day median score vs per-day median target, Spearman across
    days - the frozen dependence-aware primary."""
    bx = collections.defaultdict(list); by = collections.defaultdict(list)
    for d, x, y in zip(days, xs, ys):
        bx[d].append(x); by[d].append(y)
    ds = sorted(bx)
    return ds, [med(bx[d]) for d in ds], [med(by[d]) for d in ds]


def day_perm_p(dx, dy, iters=20000, seed=SEED):
    """Permutation p by shuffling WHOLE DAYS (frozen form)."""
    obs = abs(spearman(dx, dy))
    rnd = random.Random(seed)
    y = list(dy)
    cnt = 0
    for _ in range(iters):
        rnd.shuffle(y)
        if abs(spearman(dx, y)) >= obs:
            cnt += 1
    return (cnt + 1.0) / (iters + 1.0)


def day_boot_ci(pairs, iters=20000, seed=SEED):
    """Day-clustered bootstrap CI of a mean. pairs: [(day, value)]."""
    if not pairs:
        return (float('nan'), float('nan'))
    by = collections.defaultdict(list)
    for d, v in pairs:
        by[d].append(v)
    ds = sorted(by)
    rnd = random.Random(seed)
    ms = []
    for _ in range(iters):
        tot = cnt = 0.0
        for _ in ds:
            vs = by[ds[rnd.randrange(len(ds))]]
            tot += sum(vs); cnt += len(vs)
        if cnt:
            ms.append(tot / cnt)
    ms.sort()
    return ms[int(.025 * len(ms))], ms[int(.975 * len(ms))]


def day_boot_delta(pa, pb, iters=20000, seed=SEED):
    """Day-clustered bootstrap of mean(A) - mean(B) with two-sided p.
    Days are resampled ONCE and applied to both arms, preserving the
    within-day dependence structure in the difference."""
    ba = collections.defaultdict(list); bb = collections.defaultdict(list)
    for d, v in pa:
        ba[d].append(v)
    for d, v in pb:
        bb[d].append(v)
    ds = sorted(set(ba) | set(bb))
    if len(ds) < 10:
        return float('nan'), (float('nan'), float('nan')), float('nan')
    rnd = random.Random(seed)
    out = []
    for _ in range(iters):
        ta = ca = tb = cb = 0.0
        for _ in ds:
            d = ds[rnd.randrange(len(ds))]
            if d in ba:
                ta += sum(ba[d]); ca += len(ba[d])
            if d in bb:
                tb += sum(bb[d]); cb += len(bb[d])
        if ca and cb:
            out.append(ta / ca - tb / cb)
    if not out:
        return float('nan'), (float('nan'), float('nan')), float('nan')
    out.sort()
    obs = mean([v for _, v in pa]) - mean([v for _, v in pb])
    neg = sum(1 for x in out if x <= 0) / float(len(out))
    p = min(1.0, 2 * min(neg, 1 - neg) + 1.0 / (iters + 1))
    return obs, (out[int(.025 * len(out))], out[int(.975 * len(out))]), p


def bh_adjust(ps):
    ok = [p if p == p else 1.0 for p in ps]
    idx = sorted(range(len(ok)), key=lambda i: ok[i])
    m = len(ok); q = [None] * m; prev = 1.0
    for rank_, i in enumerate(reversed(idx), 1):
        v = min(prev, ok[i] * m / (m - rank_ + 1))
        q[i] = v; prev = v
    return q


def holm_adjust(ps):
    ok = [p if p == p else 1.0 for p in ps]
    idx = sorted(range(len(ok)), key=lambda i: ok[i])
    m = len(ok); out = [None] * m; prev = 0.0
    for rank_, i in enumerate(idx):
        v = max(prev, min(1.0, ok[i] * (m - rank_)))
        out[i] = v; prev = v
    return out


def quintile_cuts(vals):
    """Cutpoints at 20/40/60/80 percent."""
    s = sorted(vals)
    return [s[int(q * len(s))] for q in (0.2, 0.4, 0.6, 0.8)]


def qbucket(v, cuts):
    if v is None:
        return None
    for k, c in enumerate(cuts):
        if v < c:
            return k
    return len(cuts)


TOD = (('OPEN 0930-1030', 570, 630), ('MIDMORN 1030-1200', 630, 720),
       ('MIDDAY 1200-1330', 720, 810), ('AFTERNOON 1330-1500', 810, 900))


def tod_bucket(m):
    for k, (lab, a, b) in enumerate(TOD):
        if a <= m < b:
            return k
    return None


def monotone_table(U, bkey, mask=None, quiet=False, label=''):
    """FROZEN LOW/MED/HIGH median table across all five horizons."""
    idx = collections.defaultdict(list)
    rng_ = range(len(U['rr'])) if mask is None else mask
    for i in rng_:
        b = U[bkey][i]
        if b:
            idx[b].append(i)
    res = {}
    if not quiet:
        print('  %-7s %8s | %s' % ('bucket', 'n',
                                   '  '.join('%6dm' % h for h in HOR)))
    for b in ('LOW', 'MEDIUM', 'HIGH'):
        ii = idx[b]
        if not ii:
            continue
        meds = [med([U['abs%d' % h][i] for i in ii]) for h in HOR]
        res[b] = {'n': len(ii), 'med': dict(zip(HOR, meds)),
                  'mean30': mean([U['abs30'][i] for i in ii]), 'ii': ii}
        if not quiet:
            print('  %-7s %8d | %s' % (b, len(ii),
                  '  '.join('%7.2f' % v for v in meds)))
    mono = {}
    if all(k in res for k in ('LOW', 'MEDIUM', 'HIGH')):
        for h in HOR:
            mono[h] = (res['LOW']['med'][h] < res['MEDIUM']['med'][h]
                       < res['HIGH']['med'][h])
        if not quiet:
            print('  monotone LOW<MED<HIGH: %d of %d horizons  %s'
                  % (sum(mono.values()), len(mono),
                     ' '.join('%dm:%s' % (h, 'Y' if mono[h] else 'n')
                              for h in HOR)))
    return res, mono
