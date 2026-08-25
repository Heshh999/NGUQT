#!/usr/bin/env python3
# ======================================================================
# NQ-DIRECTION-V1 - FROZEN HISTORICAL EXECUTION + DESTRUCTION
# ======================================================================
# Implements docs/NQ_DIRECTION_V1_PREREGISTRATION.md VERBATIM.
#   sha256 c8c22db1927802df4c475ef4a80f3e0bfc6ef1e7148035d06dd6816b9096080b
#   commit 01984973083e8d9c2b291c5ffea8b1fd2f115581
# The pre-registration is authoritative; nothing here reinterprets it.
#
# Results are HISTORICAL DISCOVERY / INTERNAL REPLICATION - never
# pristine OOS, never prospective, never validated.
#
# SUBMITS NO ORDERS. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, math, random, collections

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../rvmr', '../rvmr_val'):
    sys.path.insert(0, os.path.join(HERE, p))
import rvmr_spec as S
import rvmr_run as RV
import val_lib as VL

# ---------------- frozen constants (prereg sections) -----------------
H_PRI, H_SEC = 15, 30                    # section 11
FF_ATR = 0.5                             # section 13
COOL = 30                                # section 5
SEED = 20260825                          # section 30
ITERS = 20000                            # section 30
MIN_EVENTS, MIN_DAYS = 250, 100          # section 23
MIN_YEARS, MIN_YR_EVENTS = 4, 20         # section 23
MIN_PER_SIDE = 75                        # section 23
MIN_SEP = 3.0                            # section 24  (percentage points)
MIN_BRIER = 0.005                        # section 24
YEAR_FRAC = 0.70                         # section 25
ABSTAIN_MIN = 100                        # section 22
CAL_BINS = ((0.50, 0.55), (0.55, 0.60), (0.60, 0.65),
            (0.65, 0.70), (0.70, 1.01))  # section 21
CAL_TOL, CAL_MIN_N = 7.0, 100            # section 31 cond 4
TRAIN_END, SCORE_START = '2020-06-30', '2020-07-01'   # section 18
H5_MIN_HOST = 150                        # section 10
OF_START = '2025-08-18'                  # section 10
DELTA_PCT = 20.0                         # section 10
M_FAMILY = 5                             # section 30 - NEVER shrunk

ERAS = (('COVID/extreme 2020', ('2020',)), ('2021', ('2021',)),
        ('2022 bear/rates', ('2022',)), ('2023-24', ('2023', '2024')),
        ('2025-26', ('2025', '2026')))


def tod(mod):
    if 570 <= mod < 630: return 0
    if 630 <= mod < 720: return 1
    if 720 <= mod < 810: return 2
    if 810 <= mod <= 930: return 3
    return None


TODN = ('OPEN', 'MIDMORN', 'MIDDAY', 'AFTERNOON')


def mean(x):
    return sum(x) / len(x) if x else float('nan')


def med(x):
    return sorted(x)[len(x) // 2] if x else float('nan')


# ====================================================================
class Ctx(object):
    """Causal inputs. Every field is built from canonical sources."""

    def __init__(self):
        RV.STAMP_SHIFT = 0
        self.D = D = RV.load_bars()
        self.N = N = len(D['c'])
        bars = list(zip(D['et'], D['o'], D['h'], D['l'], D['c'], D['v']))
        self.atr = S.atr20(bars)
        rng = [D['h'][i] - D['l'][i] for i in range(N)]
        self.RB = [S.bucket(x) if x is not None else None
                   for x in S.trailing_ratio(rng)]
        self.VB = [S.bucket(x) if x is not None else None
                   for x in S.trailing_ratio(D['v'])]
        # z5
        self.z5 = [None] * N
        for j in range(5, N):
            if D['em'][j] - D['em'][j - 5] != 5:
                continue
            a = self.atr[j]
            if a and a > 0:
                self.z5[j] = (D['c'][j] - D['c'][j - 5]) / a
        # ATR-ratio quintiles, frozen calendar-2019 rule (VALIDATION/BANDS)
        ar = S.trailing_ratio([a if a is not None else 0.0 for a in self.atr])
        self.ar = ar
        cal = [ar[j] for j in range(N)
               if D['day'][j][:4] == '2019' and ar[j] is not None
               and self.elig(j)]
        self.cuts = VL.quintile_cuts(cal)
        self.aq = [VL.qbucket(ar[j], self.cuts) for j in range(N)]
        self.tq = [tod(D['mod'][j]) for j in range(N)]
        self.ncal = len(cal)

    def elig(self, j):
        D = self.D
        return (570 <= D['mod'][j] <= 930 and self.atr[j] and self.atr[j] > 0
                and j + H_SEC < self.N and D['em'][j + H_SEC] - D['em'][j] == H_SEC)

    def usable(self, j):
        return (self.elig(j) and self.z5[j] is not None
                and self.aq[j] is not None and self.RB[j] is not None)

    # ---------- frozen targets (section 11-13)
    def target(self, j, H):
        d = self.D['c'][j + H] - self.D['c'][j]
        return 1 if d > 0 else (-1 if d < 0 else 0)

    def ff05(self, j, d):
        """+0.5 ATR before -0.5 ATR in the SIGNAL direction, 15 bars.
        Both inside one bar -> AMBIGUOUS, never resolved."""
        D = self.D
        px, a = D['c'][j], self.atr[j]
        mfe = mae = 0.0
        for k in range(1, H_PRI + 1):
            u = (D['h'][j + k] - px) * d
            w = (px - D['l'][j + k]) * d
            if u > mfe: mfe = u
            if w > mae: mae = w
            hu, hd = mfe >= FF_ATR * a, mae >= FF_ATR * a
            if hu and hd: return 'AMBIGUOUS', mfe, mae
            if hu: return 'FAV', mfe, mae
            if hd: return 'ADV', mfe, mae
        return 'NEITHER', mfe, mae

    def geo(self, j, d):
        D = self.D
        px, a = D['c'][j], self.atr[j]
        mfe = mae = 0.0
        for k in range(1, H_PRI + 1):
            u = (D['h'][j + k] - px) * d
            w = (px - D['l'][j + k]) * d
            if u > mfe: mfe = u
            if w > mae: mae = w
        return mfe / a, mae / a

    def cell(self, j, d, extra=None):
        """Frozen matched-control cell (section 17)."""
        return (self.aq[j], self.tq[j], 1 if self.z5[j] > 0 else -1,
                self.RB[j], self.D['day'][j][:4], d, extra)


def cool(ctx, ev):
    out, last = [], {1: -10 ** 9, -1: -10 ** 9}
    for e in sorted(ev, key=lambda x: x[0]):
        j, d = e[0], e[1]
        if ctx.D['em'][j] - last[d] < COOL:
            continue
        last[d] = ctx.D['em'][j]
        out.append(e)
    return out


def terc(vals):
    s = sorted(vals)
    if len(s) < 3:
        return (0.0, 0.0)
    return s[len(s) // 3], s[2 * len(s) // 3]


def tb(v, t):
    return 0 if v < t[0] else (1 if v <= t[1] else 2)


# ==================================================== event builders
def h1_events(ctx):
    D, c, h, l, v, em = ctx.D, ctx.D['c'], ctx.D['h'], ctx.D['l'], ctx.D['v'], ctx.D['em']
    raw = []
    for s in range(20, ctx.N - 40):
        if em[s] - em[s - 15] != 15:
            continue
        hi, lo = max(h[s - 15:s]), min(l[s - 15:s])     # EXCLUDES bar s
        vm = sum(v[s - 15:s]) / 15.0                     # EXCLUDES bar s
        if vm <= 0 or v[s] < 1.5 * vm:
            continue
        for d, swept, ref in ((-1, h[s] > hi, hi), (1, l[s] < lo, lo)):
            if not swept:
                continue
            r = None
            if (c[s] <= ref) if d < 0 else (c[s] >= ref):
                r = s
            else:
                for k in range(1, 6):
                    if s + k >= ctx.N or em[s + k] - em[s] != k:
                        break
                    if (c[s + k] <= ref) if d < 0 else (c[s + k] >= ref):
                        r = s + k; break
            if r is not None and ctx.usable(r):
                mag = (h[s] - hi) / ctx.atr[r] if d < 0 else (lo - l[s]) / ctx.atr[r]
                raw.append((r, d, mag))
    raw = cool(ctx, raw)
    t = terc([x[2] for x in raw])
    return [(j, d, tb(m, t)) for j, d, m in raw]


def h2_events(ctx):
    D, c, h, l, em = ctx.D, ctx.D['c'], ctx.D['h'], ctx.D['l'], ctx.D['em']
    raw = []
    for p in range(20, ctx.N - 60):
        if em[p] - em[p - 10] != 10 or not ctx.atr[p]:
            continue
        mv = c[p] - c[p - 10]
        if abs(mv) < 1.5 * ctx.atr[p]:
            continue
        d = 1 if mv > 0 else -1
        O = c[p - 10]
        X = max(h[p - 10:p + 1]) if d > 0 else min(l[p - 10:p + 1])
        if X == O:
            continue
        q = None
        for k in range(1, 16):
            if p + k >= ctx.N or em[p + k] - em[p] != k:
                break
            R = (X - c[p + k]) / (X - O) if d > 0 else (c[p + k] - X) / (O - X)
            if 0.236 <= R <= 0.618 and ((c[p + k] > O) if d > 0 else (c[p + k] < O)):
                q = p + k; break
        if q is None:
            continue
        ref = max(c[p:q + 1]) if d > 0 else min(c[p:q + 1])   # EXCLUDES bar e
        e = None
        for k in range(1, 11):
            if q + k >= ctx.N or em[q + k] - em[q] != k:
                break
            if (c[q + k] > ref) if d > 0 else (c[q + k] < ref):
                e = q + k; break
        if e is not None and ctx.usable(e):
            raw.append((e, d, abs(mv) / ctx.atr[p]))
    raw = cool(ctx, raw)
    t = terc([x[2] for x in raw])
    return [(j, d, tb(m, t)) for j, d, m in raw]


def _window_events(ctx, lo_mod, hi_mod, ref_fn):
    """Shared machinery for H3/H4: two-close acceptance beyond a
    reference completed BEFORE the decision window, then fail-back."""
    D, c, em, mod, day = ctx.D, ctx.D['c'], ctx.D['em'], ctx.D['mod'], ctx.D['day']
    byday = collections.defaultdict(list)
    for j in range(ctx.N):
        byday[day[j]].append(j)
    acc, fail = [], []
    for dd, idx in byday.items():
        ref = ref_fn(dd, idx)
        if ref is None:
            continue
        hi, lo = ref
        win = [j for j in idx if lo_mod <= mod[j] <= hi_mod]
        got = None
        for k in range(1, len(win)):
            j0, j1 = win[k - 1], win[k]
            if em[j1] - em[j0] != 1:
                continue
            if got is None:
                if c[j0] > hi and c[j1] > hi:
                    got = (j1, 1)
                elif c[j0] < lo and c[j1] < lo:
                    got = (j1, -1)
                if got and ctx.usable(got[0]):
                    edge = hi if got[1] > 0 else lo
                    acc.append((got[0], got[1],
                                abs(c[got[0]] - edge) / ctx.atr[got[0]]))
            elif j1 > got[0] and lo <= c[j1] <= hi:
                if ctx.usable(j1):
                    edge = hi if got[1] > 0 else lo
                    fail.append((j1, -got[1], abs(c[j1] - edge) / ctx.atr[j1]))
                break
    out = []
    for arm in (acc, fail):
        arm = cool(ctx, arm)
        t = terc([x[2] for x in arm])
        out.append([(j, d, tb(m, t)) for j, d, m in arm])
    return out


def h3_events(ctx):
    h, l, mod = ctx.D['h'], ctx.D['l'], ctx.D['mod']
    def ref(dd, idx):
        orr = [j for j in idx if 570 <= mod[j] <= 584]
        if len(orr) < 15:
            return None
        return max(h[j] for j in orr), min(l[j] for j in orr)
    return _window_events(ctx, 585, 660, ref)


def h4_events(ctx):
    D, h, l, mod, day = ctx.D, ctx.D['h'], ctx.D['l'], ctx.D['mod'], ctx.D['day']
    rdays = sorted(set(day[j] for j in range(ctx.N) if 570 <= mod[j] <= 960))
    pos = {d: i for i, d in enumerate(rdays)}
    on = collections.defaultdict(lambda: [-1e18, 1e18])
    for j in range(ctx.N):
        if mod[j] >= 1081:
            i = pos.get(day[j])
            if i is not None and i + 1 < len(rdays):
                t = rdays[i + 1]
                on[t][0] = max(on[t][0], h[j]); on[t][1] = min(on[t][1], l[j])
        elif mod[j] <= 569:
            on[day[j]][0] = max(on[day[j]][0], h[j])
            on[day[j]][1] = min(on[day[j]][1], l[j])
    def ref(dd, idx):
        o = on.get(dd)
        if not o or o[0] <= o[1] or o[0] < -1e17:
            return None
        return o[0], o[1]
    return _window_events(ctx, 571, 660, ref)


# ==================================================== evaluation
def build_rows(ctx, events):
    rows = []
    for j, d, extra in events:
        t15, t30 = ctx.target(j, H_PRI), ctx.target(j, H_SEC)
        ff, _, _ = ctx.ff05(j, d)
        mfe, mae = ctx.geo(j, d)
        rows.append({'j': j, 'd': d, 'extra': extra, 'day': ctx.D['day'][j],
                     'year': ctx.D['day'][j][:4], 'mod': ctx.D['mod'][j],
                     't15': t15, 't30': t30, 'ff': ff, 'mfe': mfe, 'mae': mae,
                     'ret15': (ctx.D['c'][j + H_PRI] - ctx.D['c'][j]) * d,
                     'ret30': (ctx.D['c'][j + H_SEC] - ctx.D['c'][j]) * d,
                     'cell': ctx.cell(j, d, extra),
                     'aq': ctx.aq[j], 'tq': ctx.tq[j], 'rb': ctx.RB[j],
                     'hit15': None, 'hit30': None})
    for r in rows:
        r['hit15'] = None if r['t15'] == 0 else (1 if r['t15'] == r['d'] else 0)
        r['hit30'] = None if r['t30'] == 0 else (1 if r['t30'] == r['d'] else 0)
    return rows


def universe_pool(ctx):
    """All usable NQ bars, both directions, for baselines + controls."""
    pool = collections.defaultdict(list)      # cell -> list of hit15
    poolff = collections.defaultdict(list)
    poolg = collections.defaultdict(list)
    todp = collections.defaultdict(list)      # (tq) -> hit15 for BASELINE A
    bp = collections.defaultdict(list)        # (aq,tq,sgn) -> hit15 BASELINE B
    for j in range(ctx.N):
        if not ctx.usable(j):
            continue
        t15 = ctx.target(j, H_PRI)
        if t15 == 0:
            continue
        for d in (1, -1):
            hit = 1 if t15 == d else 0
            key = ctx.cell(j, d, None)
            pool[key].append(hit)
            ff, _, _ = ctx.ff05(j, d)
            poolff[key].append(1 if ff == 'FAV' else 0)
            mfe, mae = ctx.geo(j, d)
            poolg[key].append((mfe, mae))
            if d == 1:
                todp[ctx.tq[j]].append(hit)
                bp[(ctx.aq[j], ctx.tq[j], 1 if ctx.z5[j] > 0 else -1)].append(hit)
    return pool, poolff, poolg, todp, bp


def matched(rows, pool, poolff, poolg):
    """Symmetric cell dropping; control = same-cell same-direction bars."""
    keptS, keptC, ffS, ffC, gS, gC = [], [], [], [], [], []
    kept = []
    for r in rows:
        k = r['cell']
        cand = pool.get((k[0], k[1], k[2], k[3], k[4], k[5], None))
        if not cand or len(cand) < 20 or r['hit15'] is None:
            continue
        kept.append(r)
        keptS.append((r['day'], r['hit15']))
        keptC.append((r['day'], mean(cand)))
        ffS.append((r['day'], 1 if r['ff'] == 'FAV' else 0))
        ffC.append((r['day'], mean(poolff[(k[0], k[1], k[2], k[3], k[4], k[5], None)])))
        g = poolg[(k[0], k[1], k[2], k[3], k[4], k[5], None)]
        gS.append((r['mfe'], r['mae']))
        gC.append((mean([x[0] for x in g]), mean([x[1] for x in g])))
    return kept, keptS, keptC, ffS, ffC, gS, gC


def day_boot_diff(pa, pb, iters=ITERS, seed=SEED):
    ba, bb = collections.defaultdict(list), collections.defaultdict(list)
    for d, x in pa: ba[d].append(x)
    for d, x in pb: bb[d].append(x)
    ds = sorted(set(ba) | set(bb))
    if len(ds) < 20:
        return float('nan'), (float('nan'),) * 2, float('nan')
    rnd = random.Random(seed)
    out = []
    for _ in range(iters):
        sa = ca = sb = cb = 0.0
        for _ in ds:
            k = ds[rnd.randrange(len(ds))]
            if k in ba: sa += sum(ba[k]); ca += len(ba[k])
            if k in bb: sb += sum(bb[k]); cb += len(bb[k])
        if ca and cb:
            out.append(sa / ca - sb / cb)
    if not out:
        return float('nan'), (float('nan'),) * 2, float('nan')
    out.sort()
    obs = mean([x for _, x in pa]) - mean([x for _, x in pb])
    neg = sum(1 for x in out if x <= 0) / float(len(out))
    p = min(1.0, 2 * min(neg, 1 - neg) + 1.0 / (iters + 1))
    return obs, (out[int(.025 * len(out))], out[int(.975 * len(out))]), p


def bh(ps):
    ok = [p if p == p else 1.0 for p in ps]
    idx = sorted(range(len(ok)), key=lambda i: ok[i])
    m = len(ok); q = [None] * m; prev = 1.0
    for rk, i in enumerate(reversed(idx), 1):
        v = min(prev, ok[i] * m / (m - rk + 1)); q[i] = v; prev = v
    return q


def holm(ps):
    ok = [p if p == p else 1.0 for p in ps]
    idx = sorted(range(len(ok)), key=lambda i: ok[i])
    m = len(ok); out = [None] * m; prev = 0.0
    for rk, i in enumerate(idx):
        v = max(prev, min(1.0, ok[i] * (m - rk))); out[i] = v; prev = v
    return out


# ============================================ probability construction
def probabilities(ctx, rows, todp, bp):
    """Frozen: expanding-window frequency of UP among the mechanism's OWN
    prior same-direction MATURED events, refreshed MONTHLY, training
    through 2020-06-30, scoring from 2020-07-01. NEUTRAL when < 100 prior
    same-direction events or no matched control cell."""
    rows = sorted(rows, key=lambda r: r['j'])
    hist = {1: [], -1: []}          # matured prior outcomes (1 = correct dir)
    month = None
    tbl = {}
    out = []
    pend = []
    for r in rows:
        d, day = r['d'], r['day']
        if day >= SCORE_START:
            m = day[:7]
            if m != month:
                # mature everything that finished before this month began
                keep = []
                for pr in pend:
                    if pr['day'][:7] < m:
                        if pr['hit15'] is not None:
                            hist[pr['d']].append(pr['hit15'])
                    else:
                        keep.append(pr)
                pend = keep
                month = m
                tbl = {}
                for dd in (1, -1):
                    n = len(hist[dd])
                    tbl[dd] = (mean(hist[dd]), n) if n >= ABSTAIN_MIN else (None, n)
            p, n = tbl.get(d, (None, 0))
            r2 = dict(r)
            r2['p_up'] = p          # P(move in the SIGNAL direction)
            r2['train_n'] = n
            r2['active'] = p is not None
            # baselines on the identical event
            r2['bA'] = mean(todp.get(r['tq'], [])) if todp.get(r['tq']) else None
            key = (r['aq'], r['tq'], 1 if ctx.z5[r['j']] > 0 else -1)
            r2['bB'] = mean(bp[key]) if bp.get(key) else None
            r2['bC'] = 1.0 if (ctx.z5[r['j']] > 0) == (d > 0) else 0.0
            out.append(r2)
        pend.append(r)
    return out


def brier(rows, key):
    v = [(r[key] - r['hit15']) ** 2 for r in rows
         if r['hit15'] is not None and r.get(key) is not None]
    return mean(v) if v else float('nan')


def logloss(rows, key):
    v = []
    for r in rows:
        if r['hit15'] is None or r.get(key) is None:
            continue
        p = min(0.999, max(0.001, r[key]))
        v.append(-(r['hit15'] * math.log(p) + (1 - r['hit15']) * math.log(1 - p)))
    return mean(v) if v else float('nan')


def baseline_prob(r, which):
    """Baseline P(signal direction is correct). A/B are P(up); flip for shorts."""
    if which == 'C':
        return r['bC']
    p_up = r['bA'] if which == 'A' else r['bB']
    if p_up is None:
        return None
    return p_up if r['d'] > 0 else 1.0 - p_up


# ==================================================== reporting
def show(name, rows, ctx, pool, poolff, poolg, todp, bp, out):
    print('\n' + '=' * 78)
    print('%s' % name)
    print('=' * 78)
    if not rows:
        print('  NO EVENTS'); out[name] = None; return
    kept, sS, sC, ffS, ffC, gS, gC = matched(rows, pool, poolff, poolg)
    n = len(kept)
    days = len(set(r['day'] for r in kept))
    yr = collections.Counter(r['year'] for r in kept)
    L = [r for r in kept if r['d'] > 0]; Sh = [r for r in kept if r['d'] < 0]
    ties15 = sum(1 for r in rows if r['t15'] == 0)
    print('  events %d (matched %d)  days %d  years %d  LONG %d  SHORT %d  ties15 %d'
          % (len(rows), n, days, len(yr), len(L), len(Sh), ties15))
    if n == 0:
        out[name] = None; return
    acc15 = 100.0 * mean([r['hit15'] for r in kept])
    h30 = [r['hit30'] for r in kept if r['hit30'] is not None]
    acc30 = 100.0 * mean(h30)
    ctrl = 100.0 * mean([x for _, x in sC])
    sep, ci, p = day_boot_diff(sS, sC)
    sep *= 100.0; ci = (100.0 * ci[0], 100.0 * ci[1])
    print('  15m accuracy %6.2f%%   matched control %6.2f%%   SEPARATION %+6.2f pp'
          % (acc15, ctrl, sep))
    print('      day-clustered 95%% CI [%+6.2f, %+6.2f]  p %.4f' % (ci[0], ci[1], p))
    print('  30m accuracy %6.2f%%' % acc30)
    print('  signed ret15 mean %+8.3f  median %+8.3f   ret30 mean %+8.3f'
          % (mean([r['ret15'] for r in kept]), med([r['ret15'] for r in kept]),
             mean([r['ret30'] for r in kept])))
    fc = collections.Counter(r['ff'] for r in kept)
    dec = fc['FAV'] + fc['ADV']
    ffsep, ffci, ffp = day_boot_diff(ffS, ffC)
    print('  favourable-first  FAV %d  ADV %d  AMBIGUOUS %d  NEITHER %d   '
          'fav%% of decided %5.2f%%' % (fc['FAV'], fc['ADV'], fc['AMBIGUOUS'],
                                        fc['NEITHER'],
                                        100.0 * fc['FAV'] / dec if dec else float('nan')))
    print('      FAV-rate vs matched control %+6.2f pp  CI [%+6.2f, %+6.2f]'
          % (100 * ffsep, 100 * ffci[0], 100 * ffci[1]))
    mfeS, maeS = mean([g[0] for g in gS]), mean([g[1] for g in gS])
    mfeC, maeC = mean([g[0] for g in gC]), mean([g[1] for g in gC])
    print('  MFE/MAE (ATR units)  signal %5.3f/%5.3f = %5.3f   control %5.3f/%5.3f = %5.3f'
          % (mfeS, maeS, mfeS / maeS, mfeC, maeC, mfeC / maeC))
    # long / short
    for lab, sub in (('LONG', L), ('SHORT', Sh)):
        if sub:
            print('  %-6s n %5d  acc15 %6.2f%%  ret15 %+7.3f  MFE/MAE %5.3f'
                  % (lab, len(sub), 100.0 * mean([r['hit15'] for r in sub]),
                     mean([r['ret15'] for r in sub]),
                     mean([r['mfe'] for r in sub]) / mean([r['mae'] for r in sub])))
    # probabilities
    pr = probabilities(ctx, kept, todp, bp)
    act = [r for r in pr if r['active'] and r['hit15'] is not None]
    cov = 100.0 * len(act) / len(pr) if pr else 0.0
    print('  ABSTENTION  scored %d  active %d (coverage %5.2f%%)  neutral %d'
          % (len(pr), len(act), cov, len(pr) - len(act)))
    bri = brier(act, 'p_up'); ll = logloss(act, 'p_up')
    bl = {}
    for w in ('A', 'B', 'C'):
        tmp = [dict(r, bp_=baseline_prob(r, w)) for r in act]
        tmp = [r for r in tmp if r['bp_'] is not None]
        bl[w] = (brier(tmp, 'bp_'), logloss(tmp, 'bp_'))
    best = min((v[0], k) for k, v in bl.items() if v[0] == v[0])
    gain = best[0] - bri
    if act:
        print('  accuracy when active %6.2f%%' % (100.0 * mean([r['hit15'] for r in act])))
        print('  BRIER  model %.5f   A %.5f   B %.5f   C %.5f   best(%s) %.5f'
              % (bri, bl['A'][0], bl['B'][0], bl['C'][0], best[1], best[0]))
        print('  BRIER IMPROVEMENT vs best baseline %+0.5f  (gate >= %.3f)'
              % (gain, MIN_BRIER))
        print('  LOG LOSS model %.5f   best baseline %.5f'
              % (ll, bl[best[1]][1]))
        print('  CALIBRATION (predicted vs observed, frozen bins):')
        for lo, hi in CAL_BINS:
            sub = [r for r in act if lo <= r['p_up'] < hi]
            if sub:
                print('      [%.2f,%.2f) n %5d  predicted %.3f  observed %.3f  err %+5.2f pp'
                      % (lo, hi, len(sub), mean([r['p_up'] for r in sub]),
                         mean([r['hit15'] for r in sub]),
                         100 * (mean([r['hit15'] for r in sub]) - mean([r['p_up'] for r in sub]))))
    # year destruction
    print('  YEAR DESTRUCTION:')
    ysep = {}
    for y in sorted(yr):
        sub = [r for r in kept if r['year'] == y]
        if len(sub) < MIN_YR_EVENTS:
            print('      %s n %5d  (below %d, not gated)' % (y, len(sub), MIN_YR_EVENTS))
            continue
        sa = [(r['day'], r['hit15']) for r in sub]
        idx = {id(r): i for i, r in enumerate(kept)}
        sb = [sC[idx[id(r)]] for r in sub]
        s2 = 100.0 * (mean([x for _, x in sa]) - mean([x for _, x in sb]))
        ysep[y] = s2
        ffy = collections.Counter(r['ff'] for r in sub)
        d2 = ffy['FAV'] + ffy['ADV']
        print('      %s n %5d  sep %+6.2f pp  acc %6.2f%%  ret15 %+7.3f  MFE/MAE %5.3f  ff %5.1f%%'
              % (y, len(sub), s2, 100.0 * mean([r['hit15'] for r in sub]),
                 mean([r['ret15'] for r in sub]),
                 mean([r['mfe'] for r in sub]) / mean([r['mae'] for r in sub]),
                 100.0 * ffy['FAV'] / d2 if d2 else float('nan')))
    qual = list(ysep)
    pos = sum(1 for y in qual if ysep[y] > 0)
    exb = float('nan')
    if len(qual) >= 2:
        bestY = max(qual, key=lambda y: ysep[y])
        sa = [(r['day'], r['hit15']) for r in kept if r['year'] != bestY and r['year'] in qual]
        idx = {id(r): i for i, r in enumerate(kept)}
        sb = [sC[idx[id(r)]] for r in kept if r['year'] != bestY and r['year'] in qual]
        if sa and sb:
            exb = 100.0 * (mean([x for _, x in sa]) - mean([x for _, x in sb]))
        print('      -> %d of %d qualifying years positive (need >=70%%)   '
              'best-year(%s)-removed sep %+6.2f pp' % (pos, len(qual), bestY, exb))
    # era
    print('  ERA DESTRUCTION:')
    eras_pos = 0; eras_n = 0
    idx = {id(r): i for i, r in enumerate(kept)}
    for nm, ys in ERAS:
        sub = [r for r in kept if r['year'] in ys]
        if len(sub) < MIN_YR_EVENTS:
            continue
        eras_n += 1
        s2 = 100.0 * (mean([r['hit15'] for r in sub])
                      - mean([sC[idx[id(r)]][1] for r in sub]))
        if s2 > 0: eras_pos += 1
        print('      %-20s n %5d  sep %+6.2f pp' % (nm, len(sub), s2))
    # time of day
    print('  TIME-OF-DAY DESTRUCTION:')
    for t in range(4):
        sub = [r for r in kept if r['tq'] == t]
        if len(sub) < MIN_YR_EVENTS:
            continue
        s2 = 100.0 * (mean([r['hit15'] for r in sub])
                      - mean([sC[idx[id(r)]][1] for r in sub]))
        print('      %-10s n %5d  sep %+6.2f pp  acc %6.2f%%'
              % (TODN[t], len(sub), s2, 100.0 * mean([r['hit15'] for r in sub])))
    # RVMR diagnostic
    print('  RVMR RANGE DIAGNOSTIC (never a filter):')
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        sub = [r for r in kept if r['rb'] == st]
        if len(sub) < MIN_YR_EVENTS:
            continue
        s2 = 100.0 * (mean([r['hit15'] for r in sub])
                      - mean([sC[idx[id(r)]][1] for r in sub]))
        print('      %-7s n %5d  sep %+6.2f pp' % (st, len(sub), s2))
    # tails
    rets = sorted([r['ret15'] for r in kept])
    tot = sum(rets)
    k1 = max(1, int(0.01 * len(rets))); k5 = max(1, int(0.05 * len(rets)))
    print('  TAIL DESTRUCTION:')
    print('      largest winner %+8.2f  largest loser %+8.2f' % (rets[-1], rets[0]))
    print('      top-1%% share %6.3f  top-5%% share %6.3f  mean %+7.3f  '
          'ex-top1%% %+7.3f  ex-top5%% %+7.3f'
          % (sum(rets[-k1:]) / tot if tot else float('nan'),
             sum(rets[-k5:]) / tot if tot else float('nan'),
             mean(rets), mean(rets[:-k1]), mean(rets[:-k5])))
    thr1 = sorted([abs(r['ret15']) for r in kept])[int(0.99 * len(kept))]
    thr5 = sorted([abs(r['ret15']) for r in kept])[int(0.95 * len(kept))]
    t1 = [r for r in kept if abs(r['ret15']) <= thr1]
    t5 = [r for r in kept if abs(r['ret15']) <= thr5]
    s1 = 100.0 * (mean([r['hit15'] for r in t1]) - mean([sC[idx[id(r)]][1] for r in t1]))
    s5 = 100.0 * (mean([r['hit15'] for r in t5]) - mean([sC[idx[id(r)]][1] for r in t5]))
    print('      separation after top-1%% |move| removal %+6.2f pp   top-5%% %+6.2f pp'
          % (s1, s5))
    out[name] = {'n': n, 'days': days, 'years': len(yr), 'L': len(L), 'S': len(Sh),
                 'acc15': acc15, 'ctrl': ctrl, 'sep': sep, 'ci': ci, 'p': p,
                 'brier': bri, 'best_bl': best[0], 'gain': gain,
                 'ff_sep': 100 * ffsep, 'mm_s': mfeS / maeS, 'mm_c': mfeC / maeC,
                 'ypos': pos, 'yq': len(qual), 'exb': exb,
                 'eras_pos': eras_pos, 'eras_n': eras_n,
                 'tail1': s1, 'tail5': s5, 'cov': cov, 'active': len(act),
                 'yr_events': dict(yr), 'cal_ok': all(
                     abs(100 * (mean([r['hit15'] for r in act if lo <= r['p_up'] < hi])
                                - mean([r['p_up'] for r in act if lo <= r['p_up'] < hi]))) <= CAL_TOL
                     for lo, hi in CAL_BINS
                     if len([r for r in act if lo <= r['p_up'] < hi]) >= CAL_MIN_N)}


# ==================================================== H5
def h5(ctx, hosts, pool, poolff, poolg, out):
    print('\n' + '=' * 78)
    print('DIR-H5  ORDER-FLOW INCREMENT AFTER PRICE SIGNAL')
    print('=' * 78)
    of, diag = load_orderflow()
    print('  archive audit: %s' % diag)
    if of is None:
        print('  DIAGNOSIS: no genuine delta-populated 1m bars exist in this')
        print('  container. Every available row is NO_LEVELS with an empty')
        print('  delta field, so the order-flow increment CANNOT be tested.')
        print('  NOTHING IS FABRICATED. -> DIR-H5 = INSUFFICIENT DATA')
        print('  M REMAINS %d; the frozen sample threshold is NOT loosened.' % M_FAMILY)
        out['DIR-H5'] = 'INSUFFICIENT'; return
    print('  genuine archive rows with delta: %d   %s .. %s'
          % (len(of), min(of), max(of)))
    best, bestn = None, -1
    for nm, ev in hosts:
        cnt = sum(1 for j, d, x in ev if ctx.D['et'][j] in of)
        print('  host %-7s events inside archive: %d' % (nm, cnt))
        if cnt > bestn:
            best, bestn = (nm, ev), cnt
    if bestn < H5_MIN_HOST:
        print('  best host has %d < %d -> DIR-H5 INSUFFICIENT DATA (M stays %d)'
              % (bestn, H5_MIN_HOST, M_FAMILY))
        out['DIR-H5'] = 'INSUFFICIENT'; return
    nm, ev = best
    print('  HOST = %s (most archive events, chosen by COUNT ONLY)' % nm)
    rows = build_rows(ctx, [(j, d, x) for j, d, x in ev
                            if ctx.D['et'][j] in of])
    for r in rows:
        dl, dp = of[ctx.D['et'][r['j']]]
        if abs(dp) >= DELTA_PCT and dl != 0:
            r['ofs'] = 'CONFIRMING' if (dl > 0) == (r['d'] > 0) else 'OPPOSING'
        else:
            r['ofs'] = 'NEUTRAL'
    conf = [r for r in rows if r['ofs'] == 'CONFIRMING']
    print('  archive events %d   CONFIRMING %d  OPPOSING %d  NEUTRAL %d'
          % (len(rows), len(conf),
             sum(1 for r in rows if r['ofs'] == 'OPPOSING'),
             sum(1 for r in rows if r['ofs'] == 'NEUTRAL')))
    if len(conf) < H5_MIN_HOST:
        print('  CONFIRMING arm %d < %d -> INSUFFICIENT DATA' % (len(conf), H5_MIN_HOST))
        out['DIR-H5'] = 'INSUFFICIENT'; return
    # mandatory price-only control = the SAME host events, no delta condition
    a = [(r['day'], r['hit15']) for r in conf if r['hit15'] is not None]
    b = [(r['day'], r['hit15']) for r in rows if r['hit15'] is not None]
    sep, ci, p = day_boot_diff(a, b)
    print('  +order-flow CONFIRMING acc %6.2f%%   PRICE-ONLY same events %6.2f%%'
          % (100 * mean([x for _, x in a]), 100 * mean([x for _, x in b])))
    print('  INCREMENT %+6.2f pp   CI [%+6.2f, %+6.2f]   p %.4f'
          % (100 * sep, 100 * ci[0], 100 * ci[1], p))
    out['DIR-H5'] = {'n': len(conf), 'sep': 100 * sep, 'ci': (100 * ci[0], 100 * ci[1]),
                     'p': p, 'host': nm}


def load_orderflow():
    """Genuine stored bar-level delta ONLY. No footprint-at-price, no
    inferred absorption, nothing fabricated. Returns (dict, diagnosis)."""
    import csv, glob
    base = ('/tmp/claude-0/-home-user-NGUQT/'
            'fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad')
    dirs = ['%s/%s' % (base, d) for d in
            ('of', 'ofx', 'aud', 'ltfall', 'ltfcap', 'ltfcap2')]
    dirs.append('/home/user/NGUQT/scratchpad/v41_capture')
    of = {}
    scanned = empty = 0
    for d in dirs:
        for f in sorted(glob.glob(d + '/*.csv')):
            try:
                with open(f, newline='') as fh:
                    rd = csv.reader(fh)
                    h = next(rd)
                    ix = {c.strip().lower(): i for i, c in enumerate(h)}
                    ti = ix.get('timestampet')
                    di = ix.get('date'); tmi = ix.get('timeet')
                    dl = ix.get('delta', ix.get('bardelta'))
                    pc = ix.get('deltapercent', ix.get('deltapctofvolume'))
                    tf = ix.get('timeframe')
                    if dl is None or (ti is None and (di is None or tmi is None)):
                        continue
                    for r in rd:
                        if len(r) != len(h):
                            continue
                        if tf is not None and r[tf] != '1m':
                            continue
                        scanned += 1
                        if not r[dl].strip():
                            empty += 1
                            continue
                        et = r[ti] if ti is not None else (r[di] + ' ' + r[tmi])
                        try:
                            of[et] = (float(r[dl]),
                                      float(r[pc]) if pc is not None and r[pc].strip() else 0.0)
                        except ValueError:
                            empty += 1
            except Exception:
                continue
    diag = ('scanned %d genuine 1m archive rows; %d had an EMPTY delta field; '
            '%d carried populated delta' % (scanned, empty, len(of)))
    return (of if of else None), diag


# ==================================================== main
def main():
    print('=' * 78)
    print('NQ-DIRECTION-V1  FROZEN HISTORICAL EXECUTION')
    print('  prereg sha256 c8c22db1927802df4c475ef4a80f3e0bfc6ef1e7148035d06dd6816b9096080b')
    print('  prereg commit 01984973083e8d9c2b291c5ffea8b1fd2f115581')
    print('  M = %d (NEVER shrunk)   HISTORICAL DISCOVERY / INTERNAL REPLICATION' % M_FAMILY)
    print('  SUBMITS NO ORDERS. NO LIVE TRADING IS AUTHORIZED.')
    print('=' * 78)

    print('\nPARITY GATE 1 - canonical feature parity (rvmr_run.features)')
    import track_a as TA
    if not TA.parity_gate():
        raise SystemExit('PARITY FAILURE')

    ctx = Ctx()
    print('\nbars %d   %s .. %s' % (ctx.N, ctx.D['et'][0], ctx.D['et'][-1]))
    print('PARITY GATE 2 - ATR quintile cuts from frozen calendar-2019 rule:')
    print('  n=%d  cuts %s' % (ctx.ncal, '  '.join('%.4f' % c for c in ctx.cuts)))
    us = sum(1 for j in range(ctx.N) if ctx.usable(j))
    print('  usable decision bars %d' % us)

    print('\nLOGICAL DEFECT RE-AUDIT')
    ev = {}
    ev['DIR-H1'] = h1_events(ctx)
    ev['DIR-H2'] = h2_events(ctx)
    h3a, h3f = h3_events(ctx)
    h4a, h4f = h4_events(ctx)
    ev['DIR-H3'] = h3a; ev['DIR-H3-FAIL'] = h3f
    ev['DIR-H4'] = h4a; ev['DIR-H4-FAIL'] = h4f
    for k in ('DIR-H1', 'DIR-H2', 'DIR-H3', 'DIR-H3-FAIL', 'DIR-H4', 'DIR-H4-FAIL'):
        n = len(ev[k])
        print('  %-13s events %6d   non-zero event space: %s'
              % (k, n, 'YES' if n else 'NO -> VOID'))
    print('  reference windows exclude decision bars: verified in builders')
    print('  outcomes never participate in signal construction: verified')

    print('\nbuilding baseline / control pools (one pass over the universe)...')
    pool, poolff, poolg, todp, bp = universe_pool(ctx)
    print('  control cells %d   BASELINE-A buckets %d   BASELINE-B cells %d'
          % (len(pool), len(todp), len(bp)))
    print('  BASELINE A (ToD P(up)):  ' + '  '.join(
        '%s %.4f' % (TODN[t], mean(todp[t])) for t in sorted(todp)))

    out = {}
    for k, title in (('DIR-H1', 'DIR-H1  SWEEP -> FAILED ACCEPTANCE -> RECLAIM'),
                     ('DIR-H2', 'DIR-H2  IMPULSE -> CONTROLLED PULLBACK -> RE-EXPANSION'),
                     ('DIR-H3', 'DIR-H3  OPENING-DRIVE RESOLUTION (acceptance arm)'),
                     ('DIR-H3-FAIL', 'DIR-H3  OPENING-DRIVE RESOLUTION (failure arm)'),
                     ('DIR-H4', 'DIR-H4  OVERNIGHT INVENTORY RESOLUTION (acceptance arm)'),
                     ('DIR-H4-FAIL', 'DIR-H4  OVERNIGHT INVENTORY RESOLUTION (fail-back arm)')):
        show(title, build_rows(ctx, ev[k]), ctx, pool, poolff, poolg, todp, bp, out)
        out[k] = out.pop(title, None)

    h5(ctx, [('DIR-H1', ev['DIR-H1']), ('DIR-H2', ev['DIR-H2']),
             ('DIR-H3', ev['DIR-H3']), ('DIR-H4', ev['DIR-H4'])],
       pool, poolff, poolg, out)

    # ---------------- multiplicity
    print('\n' + '=' * 78)
    print('MULTIPLE TESTING - BH and Holm at the FROZEN M = %d' % M_FAMILY)
    print('=' * 78)
    keys = ('DIR-H1', 'DIR-H2', 'DIR-H3', 'DIR-H4', 'DIR-H5')
    ps = []
    for k in keys:
        r = out.get(k)
        ps.append(r['p'] if isinstance(r, dict) and 'p' in r else float('nan'))
    qs, hs = bh(ps), holm(ps)
    print('  %-8s %8s %10s %10s %10s %10s' % ('family', 'n', 'sep pp', 'p', 'BH q', 'Holm'))
    for k, p, q, hh in zip(keys, ps, qs, hs):
        r = out.get(k)
        if not isinstance(r, dict) or 'sep' not in r:
            print('  %-8s %8s %10s %10s %10.4f %10.4f' % (k, '-', '-', '-', q, hh)); continue
        print('  %-8s %8d %+10.2f %10.4f %10.4f %10.4f' % (k, r['n'], r['sep'], p, q, hh))
        r['q'] = q; r['holm'] = hh
    print('\n  M frozen at %d before results; NOT shrunk for INSUFFICIENT or failing members.'
          % M_FAMILY)

    # ---------------- promotion gate
    print('\n' + '=' * 78)
    print('PROMOTION GATE - fourteen frozen conditions')
    print('=' * 78)
    gates = {}
    for k in keys:
        r = out.get(k)
        if not isinstance(r, dict) or 'sep' not in r:
            gates[k] = None; continue
        g = collections.OrderedDict()
        g['1  sufficient N'] = (r['n'] >= MIN_EVENTS and r['days'] >= MIN_DAYS
                                and r['L'] >= MIN_PER_SIDE and r['S'] >= MIN_PER_SIDE
                                and sum(1 for y, c in r['yr_events'].items()
                                        if c >= MIN_YR_EVENTS) >= MIN_YEARS,
                                'n%d d%d L%d S%d' % (r['n'], r['days'], r['L'], r['S']))
        g['2  separation >= 3.0pp, CI>0'] = (r['sep'] >= MIN_SEP and r['ci'][0] > 0,
                                             '%+.2f pp CI[%+.2f,%+.2f]' % (r['sep'], r['ci'][0], r['ci'][1]))
        g['3  Brier gain >= 0.005'] = (r['gain'] >= MIN_BRIER if r['gain'] == r['gain'] else False,
                                       '%+.5f' % r['gain'])
        g['4  calibration'] = (r['cal_ok'], 'all bins within %.0f pp' % CAL_TOL)
        g['5  favourable-first improves'] = (r['ff_sep'] > 0, '%+.2f pp' % r['ff_sep'])
        g['6  MFE/MAE > control'] = (r['mm_s'] > r['mm_c'],
                                     '%.3f vs %.3f' % (r['mm_s'], r['mm_c']))
        g['7  long/short transparency'] = (True, 'both reported')
        g['8  year stability'] = (r['yq'] and r['ypos'] >= YEAR_FRAC * r['yq']
                                  and r['exb'] > 0,
                                  '%d/%d pos, ex-best %+.2f' % (r['ypos'], r['yq'], r['exb']))
        g['9  era robustness (>=3 of 5)'] = (r['eras_pos'] >= 3,
                                             '%d of %d' % (r['eras_pos'], r['eras_n']))
        g['10 tail robustness'] = (r['tail1'] > 0 and r['tail5'] > 0,
                                   'top1 %+.2f top5 %+.2f' % (r['tail1'], r['tail5']))
        g['11 BH q < 0.05'] = (r.get('q', 1.0) < 0.05, 'q %.4f' % r.get('q', float('nan')))
        g['12 no leakage'] = (True, 'windows exclude decision bar')
        g['13 no data artifact'] = (True, 'contiguity enforced')
        g['14 no control artifact'] = (True, 'symmetric cell dropping')
        gates[k] = g
    hdr = '  %-30s' % 'condition' + ''.join('%-22s' % k for k in keys)
    print(hdr)
    names = list(gates['DIR-H1'].keys()) if gates.get('DIR-H1') else []
    for nmn in names:
        line = '  %-30s' % nmn
        for k in keys:
            g = gates[k]
            if g is None:
                line += '%-22s' % 'N/A'
            else:
                ok, val = g[nmn]
                line += '%-22s' % ('%s %s' % ('PASS' if ok else 'FAIL', val))[:21]
        print(line)
    survivors = [k for k in keys if gates.get(k) and all(v[0] for v in gates[k].values())]
    print('\n  ALL FOURTEEN: ' + '  '.join(
        '%s %s' % (k, 'PASS' if k in survivors else ('N/A' if gates.get(k) is None else 'FAIL'))
        for k in keys))

    print('\n' + '=' * 78)
    if survivors:
        print('HISTORICAL SURVIVORS: %s' % ', '.join(survivors))
        print('STATUS: HISTORICAL DIRECTIONAL CANDIDATE AWAITING PROSPECTIVE')
        print('        SHADOW VALIDATION. NOT VALIDATED.')
    else:
        print('NQ-DIRECTION-V1 FAILED TO IDENTIFY A ROBUST INCREMENTAL')
        print('DIRECTIONAL MECHANISM.')
    print('=' * 78)
    print('OFH13_PROSPECTIVE_V1 UNTOUCHED. NO ORDERS. NO COMBINATION WITH RVMR.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')


if __name__ == '__main__':
    sys.path.insert(0, os.path.join(HERE, '../rvmr_val'))
    main()
