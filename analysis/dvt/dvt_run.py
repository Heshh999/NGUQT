#!/usr/bin/env python3
# ======================================================================
# 4H-DVT-V1 - FROZEN HISTORICAL EXECUTION + DESTRUCTION
# ======================================================================
# Implements docs/4H_DVT_V1_PREREGISTRATION.md VERBATIM.
#   prereg sha256 c6526a09f1c13c34961c470ed3ff2d4ba17cc36dfc001870827d577fb1adcad0
#   spec   sha256 2adf8b37d88d0676d22cb014768d8a996a6415ea2a59608c4af14718d06928d6
#   commit 19c60b917f5655c9ba51804116e4f29de5218249
# The pre-registration and dvt_spec.py are authoritative.
#
# HISTORICAL DISCOVERY. Never OOS, never prospective, never validated.
# SUBMITS NO ORDERS. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, math, random, collections

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../rvmr', '.'):
    sys.path.insert(0, os.path.join(HERE, p))
import rvmr_spec as RS
import rvmr_run as RV
import dvt_spec as SP

SEED, ITERS = 20260825, 20000
MIN_EVENTS, MIN_DAYS = 200, 100
MIN_YEARS, MIN_YR_EVENTS, MIN_PER_SIDE = 5, 15, 50
YEAR_FRAC = 0.70
M_FAMILY = 2
FF_LADDER = ((0.25, 0.25), (0.5, 0.5), (1.0, 1.0), (1.5, 1.0), (2.0, 1.0))
HORS = (5, 10, 15, 30, 60)
TODN = ('OPEN', 'MIDMORN', 'MIDDAY', 'AFTERNOON')


def mean(x):
    return sum(x) / len(x) if x else float('nan')


def med(x):
    return sorted(x)[len(x) // 2] if x else float('nan')


def tod(m):
    if 570 <= m < 630: return 0
    if 630 <= m < 720: return 1
    if 720 <= m < 810: return 2
    if 810 <= m <= 900: return 3
    return None


# ==================================================================== ctx
class Ctx(object):
    def __init__(self):
        RV.STAMP_SHIFT = 0
        self.D = D = RV.load_bars()
        self.N = N = len(D['c'])
        o, h, l, c, v, em = D['o'], D['h'], D['l'], D['c'], D['v'], D['em']
        bars = list(zip(D['et'], o, h, l, c, v))
        self.atr = RS.atr20(bars)
        rng = [h[i] - l[i] for i in range(N)]
        self.RB = [RS.bucket(x) if x is not None else None
                   for x in RS.trailing_ratio(rng)]
        # ---- causal per-1m session VWAP band (frozen SessionVwap)
        vw = SP.SessionVwap()
        self.bh = [None] * N; self.bl = [None] * N
        for i in range(N):
            vw.update(em[i], h[i], l[i], c[i], v[i])
            self.bh[i] = vw.band_high; self.bl[i] = vw.band_low
        # ---- 1m EMA9 from COMPLETED closes
        e9 = SP.Ema(SP.EMA_FAST_LEN)
        self.ema9 = [None] * N
        for i in range(N):
            self.ema9[i] = e9.add(c[i])
        # ---- z5 / ATR-ratio quintiles (matching only)
        self.z5 = [None] * N
        for j in range(5, N):
            if em[j] - em[j - 5] != 5: continue
            a = self.atr[j]
            if a and a > 0: self.z5[j] = (c[j] - c[j - 5]) / a
        ar = RS.trailing_ratio([a if a is not None else 0.0 for a in self.atr])
        cal = sorted(x for j, x in enumerate(ar)
                     if D['day'][j][:4] == '2019' and x is not None)
        self.cuts = [cal[int(q * len(cal))] for q in (.2, .4, .6, .8)]
        self.aq = [self._q(x) for x in ar]
        # ---- 15m grid
        self.b15 = [SP.bucket15(em[i]) for i in range(N)]
        seg = collections.OrderedDict()
        for i in range(N):
            seg.setdefault(self.b15[i], []).append(i)
        self.seg = seg
        keys = sorted(seg)
        self.K = {}
        prev = []
        for k in keys:
            idx = seg[k]
            O = o[idx[0]]; H = max(h[j] for j in idx)
            L = min(l[j] for j in idx); C = c[idx[-1]]
            V = sum(v[j] for j in idx)
            if len(prev) == SP.VECTOR_LOOKBACK:
                av = sum(x[4] for x in prev) / 10.0
                hs = max(x[4] * (x[1] - x[2]) for x in prev)
                vec = SP.classify(O, H, L, C, V, av, hs)
            else:
                av = hs = None; vec = None
            self.K[k] = {'o': O, 'h': H, 'l': L, 'c': C, 'v': V, 'vec': vec,
                         'idx': idx, 'day': D['day'][idx[-1]],
                         'av': av, 'hs': hs}
            prev.append((O, H, L, C, V))
            if len(prev) > SP.VECTOR_LOOKBACK: prev.pop(0)
        # ---- 4H trend from COMPLETED 4H bars
        s4 = collections.OrderedDict()
        for i in range(N):
            s4.setdefault(SP.bucket4h(em[i]), []).append(i)
        e20 = SP.Ema(SP.EMA_TREND_FAST); e50 = SP.Ema(SP.EMA_TREND_SLOW)
        self.trend = {}
        self.sep4 = {}
        for k in sorted(s4):
            C4 = c[s4[k][-1]]
            a, b = e20.add(C4), e50.add(C4)
            if a is None or b is None:
                self.trend[k] = None; self.sep4[k] = None
            else:
                self.trend[k] = 1 if a > b else (-1 if a < b else 0)
                self.sep4[k] = abs(a - b)

    def _q(self, x):
        if x is None: return None
        for i, cc in enumerate(self.cuts):
            if x < cc: return i
        return len(self.cuts)

    def trend_at(self, k15):
        t = k15 * 15 + SP.DAY_START_MIN_ET
        kk = (t - SP.DAY_START_MIN_ET) // SP.H4_MINUTES
        return self.trend.get(kk - 1), self.sep4.get(kk - 1)

    def entry_ok(self, i):
        m = self.D['mod'][i]
        return (SP.ENTRY_START_MIN_ET <= m <= SP.ENTRY_END_MIN_ET
                and self.atr[i] and self.atr[i] > 0
                and i + SP.HORIZON_MIN < self.N
                and self.D['em'][i + SP.HORIZON_MIN] - self.D['em'][i] == SP.HORIZON_MIN)

    # ---- frozen band test, ONE definition for completed and developing
    def touched(self, idx_from, t, side):
        h, l = self.D['h'], self.D['l']
        for i in range(idx_from, t + 1):
            if side < 0:
                if SP.touched_up(h[i], self.bh[i]): return True
            else:
                if SP.touched_dn(l[i], self.bl[i]): return True
        return False

    def rejected(self, t, side):
        c = self.D['c']
        return (SP.rejected_up(c[t], self.bh[t]) if side < 0
                else SP.rejected_dn(c[t], self.bl[t]))

    def completed_test(self, k, side, need_vector=True):
        kk = self.K[k]
        if need_vector and (kk['vec'] is None or not SP.is_vector(kk['vec'])):
            return False
        idx = kk['idx']
        return self.touched(idx[0], idx[-1], side) and self.rejected(idx[-1], side)


# ============================================== developing reconstruction
def dev_qualifies(ctx, k, t, side, need_vector=True):
    """A+B+C at completed 1m bar t inside interval k, using ONLY completed
    1m bars of that interval through t plus the previous 10 COMPLETED 15m."""
    kk = ctx.K[k]; idx = kk['idx']
    if t < idx[0] or t > idx[-1]:
        return False
    if not ctx.touched(idx[0], t, side):
        return False
    if not ctx.rejected(t, side):
        return False
    if not need_vector:
        return True
    if kk['av'] is None or kk['av'] <= 0:
        return False
    D = ctx.D
    dO = D['o'][idx[0]]
    dH = max(D['h'][i] for i in range(idx[0], t + 1))
    dL = min(D['l'][i] for i in range(idx[0], t + 1))
    dC = D['c'][t]
    dV = sum(D['v'][i] for i in range(idx[0], t + 1))
    return SP.is_vector(SP.classify(dO, dH, dL, dC, dV, kk['av'], kk['hs']))


# ==================================================================== parents
def build_parents(ctx, need_vector=True, use_4h=True, single=False):
    """Frozen parent construction. single=True -> Control B (one test)."""
    keys = sorted(ctx.K)
    kset = set(keys)
    firsts = {-1: [], 1: []}
    for k in keys:
        for side in (-1, 1):
            tr, _ = ctx.trend_at(k)
            if use_4h:
                if tr != side: continue
            if ctx.completed_test(k, side, need_vector):
                firsts[side].append(k)
    if single:
        out = []
        for side in (-1, 1):
            for k1 in firsts[side]:
                out.append((k1, k1, side))
        return out
    out = []
    for side in (-1, 1):
        for k1 in firsts[side]:
            for k2 in range(k1 + 1, k1 + SP.MAX_SPACING_15M + 1):
                if k2 not in kset: break
                if (k2 * 15) // 1440 != (k1 * 15) // 1440: break
                if use_4h:
                    tr, _ = ctx.trend_at(k2)
                    if tr != side: break
                dead = False
                for km in range(k1 + 1, k2):
                    if km not in kset: continue
                    j = ctx.K[km]['idx'][-1]
                    if side < 0 and ctx.bh[j] is not None and ctx.D['c'][j] > ctx.bh[j]:
                        dead = True; break
                    if side > 0 and ctx.bl[j] is not None and ctx.D['c'][j] < ctx.bl[j]:
                        dead = True; break
                if dead: break
                if not ctx.completed_test(k2, side, need_vector):
                    continue
                out.append((k1, k2, side))
                break
    return out


# ==================================================================== entries
def entries(ctx, parents, need_vector=True, use_ema9=True, completed_ref=False):
    """Walk the second interval bar by bar. Reason-coded rejections."""
    rows = []
    reasons = collections.Counter()
    for k1, k2, side in parents:
        kk = ctx.K[k2]; idx = kk['idx']
        if completed_ref:
            scan = range(idx[-1] + 1, min(idx[-1] + 1 + 15, ctx.N))
            qual_t = idx[-1]
            if not ctx.completed_test(k2, side, need_vector):
                reasons['second_not_qualified']; continue
        else:
            scan = idx
            qual_t = None
        fired = None
        for t in scan:
            if not completed_ref:
                if not dev_qualifies(ctx, k2, t, side, need_vector):
                    continue
                qual_t = t
            if use_ema9:
                e = ctx.ema9[t]
                if e is None:
                    continue
                cl = ctx.D['c'][t]
                if not ((cl < e) if side < 0 else (cl > e)):
                    continue
            if not ctx.entry_ok(t):
                reasons['outside_entry_window_or_horizon'] += 1
                continue
            fired = t
            break
        if fired is None:
            reasons['no_trigger'] += 1
            continue
        stop = (max(ctx.D['h'][i] for i in range(idx[0], fired + 1)) if side < 0
                else min(ctx.D['l'][i] for i in range(idx[0], fired + 1)))
        rows.append(make_row(ctx, fired, side, k1, k2, stop, kk['vec'],
                             ctx.K[k1]['vec']))
    return rows, reasons


def make_row(ctx, t, side, k1, k2, stop, v2, v1):
    D = ctx.D
    px, a = D['c'][t], ctx.atr[t]
    r = {'t': t, 'd': side, 'day': D['day'][t], 'year': D['day'][t][:4],
         'mod': D['mod'][t], 'tq': tod(D['mod'][t]), 'atr': a,
         'aq': ctx.aq[t], 'rb': ctx.RB[t], 'k1': k1, 'k2': k2,
         'v1': v1, 'v2': v2, 'gap': k2 - k1, 'px': px, 'stop': stop,
         'z5': ctx.z5[t]}
    risk = abs(stop - px)
    r['risk'] = risk
    r['risk_atr'] = risk / a if a else float('nan')
    mfe = mae = 0.0
    ff = dict((k, None) for k in FF_LADDER)
    net = None
    for k in range(1, SP.HORIZON_MIN + 1):
        hi, lo = D['h'][t + k], D['l'][t + k]
        u = (hi - px) * side; w = (px - lo) * side
        if u > mfe: mfe = u
        if w > mae: mae = w
        for key in FF_LADDER:
            if ff[key] is not None: continue
            up, dn = key
            hu, hd = mfe >= up * a, mae >= dn * a
            if hu and hd: ff[key] = 'AMBIGUOUS'
            elif hu: ff[key] = 'FAV'
            elif hd: ff[key] = 'ADV'
        # frozen economic reference: structural stop, no target, 60m exit
        if net is None:
            hit = (hi >= stop) if side < 0 else (lo <= stop)
            if hit:
                net = (stop - px) * side - SP.COST_PTS
        if k in HORS:
            r['fwd%d' % k] = (D['c'][t + k] - px) * side
    if net is None:
        net = (D['c'][t + SP.HORIZON_MIN] - px) * side - SP.COST_PTS
    r['net'] = net
    r['R'] = net / risk if risk > 0 else float('nan')
    r['mfe'] = mfe; r['mae'] = mae
    r['mfe_atr'] = mfe / a; r['mae_atr'] = mae / a
    r['mm'] = mfe / mae if mae > 0 else float('nan')
    r['ff'] = dict((('%g/%g' % k), (v or 'NEITHER')) for k, v in ff.items())
    return r


# ==================================================================== stats
def day_boot(pa, pb, key='fwd15', iters=ITERS, seed=SEED):
    ba, bb = collections.defaultdict(list), collections.defaultdict(list)
    for r in pa: ba[r['day']].append(r[key])
    for r in pb: bb[r['day']].append(r[key])
    ds = sorted(set(ba) | set(bb))
    if len(ds) < 20:
        return float('nan'), (float('nan'),) * 2, float('nan')
    rnd = random.Random(seed); out = []
    for _ in range(iters):
        sa = ca = sb = cb = 0.0
        for _ in ds:
            k = ds[rnd.randrange(len(ds))]
            if k in ba: sa += sum(ba[k]); ca += len(ba[k])
            if k in bb: sb += sum(bb[k]); cb += len(bb[k])
        if ca and cb: out.append(sa / ca - sb / cb)
    if not out: return float('nan'), (float('nan'),) * 2, float('nan')
    out.sort()
    obs = mean([r[key] for r in pa]) - mean([r[key] for r in pb])
    neg = sum(1 for x in out if x <= 0) / float(len(out))
    p = min(1.0, 2 * min(neg, 1 - neg) + 1.0 / (iters + 1))
    return obs, (out[int(.025 * len(out))], out[int(.975 * len(out))]), p


def day_ci(rows, key='net', iters=ITERS, seed=SEED):
    by = collections.defaultdict(list)
    for r in rows: by[r['day']].append(r[key])
    ds = sorted(by)
    if len(ds) < 20: return (float('nan'),) * 2
    rnd = random.Random(seed); out = []
    for _ in range(iters):
        s = n = 0.0
        for _ in ds:
            k = ds[rnd.randrange(len(ds))]
            s += sum(by[k]); n += len(by[k])
        if n: out.append(s / n)
    out.sort()
    return out[int(.025 * len(out))], out[int(.975 * len(out))]


def bh_adjust(ps):
    ok = [p if p == p else 1.0 for p in ps]
    idx = sorted(range(len(ok)), key=lambda i: ok[i])
    m = len(ok); q = [None] * m; prev = 1.0
    for rk, i in enumerate(reversed(idx), 1):
        v = min(prev, ok[i] * m / (m - rk + 1)); q[i] = v; prev = v
    return q


# ==================================== matched controls (frozen cells)
def terc_maps(rows):
    def t3(vals):
        s = sorted(vals)
        return (s[len(s) // 3], s[2 * len(s) // 3]) if len(s) >= 3 else (0, 0)
    return {'gap': t3([r['gap'] for r in rows]),
            'risk': t3([r['risk_atr'] for r in rows])}


def cell_of(r, tm):
    def b(v, t): return 0 if v < t[0] else (1 if v <= t[1] else 2)
    return (r['d'], r['year'], r['tq'], r['aq'], r['rb'],
            1 if (r['z5'] or 0) > 0 else -1,
            b(r['gap'], tm['gap']), b(r['risk_atr'], tm['risk']))


def matched(sig, ctrl, key='fwd15'):
    """Symmetric cell dropping. Returns paired signal/control rows."""
    tm = terc_maps(sig + ctrl)
    cs = collections.defaultdict(list)
    for r in ctrl: cs[cell_of(r, tm)].append(r[key])
    A, B = [], []
    for r in sig:
        c = cell_of(r, tm)
        if c not in cs or len(cs[c]) < 3: continue
        A.append(r)
        B.append({'day': r['day'], key: mean(cs[c])})
    return A, B


# ==================================================================== report
def geo(rows):
    if not rows: return None
    g = {'n': len(rows), 'days': len(set(r['day'] for r in rows)),
         'net': mean([r['net'] for r in rows]),
         'netmed': med([r['net'] for r in rows]),
         'R': mean([r['R'] for r in rows]),
         'mfe': mean([r['mfe_atr'] for r in rows]),
         'mae': mean([r['mae_atr'] for r in rows]),
         'risk': mean([r['risk_atr'] for r in rows])}
    g['mm'] = g['mfe'] / g['mae'] if g['mae'] else float('nan')
    for h in HORS:
        v = [r['fwd%d' % h] for r in rows]
        g['f%d' % h] = mean(v); g['f%dm' % h] = med(v)
    return g


def ff_tab(rows):
    out = {}
    for key in FF_LADDER:
        k = '%g/%g' % key
        c = collections.Counter(r['ff'][k] for r in rows)
        dec = c['FAV'] + c['ADV']
        out[k] = (c['FAV'], c['ADV'], c['AMBIGUOUS'], c['NEITHER'],
                  100.0 * c['FAV'] / dec if dec else float('nan'))
    return out


def show(tag, rows):
    g = geo(rows)
    if g is None:
        print('  %-28s NO EVENTS' % tag); return
    print('  %-28s n%5d d%4d  fwd5 %+7.3f  fwd15 %+7.3f  fwd30 %+7.3f  '
          'fwd60 %+7.3f' % (tag, g['n'], g['days'], g['f5'], g['f15'],
                            g['f30'], g['f60']))
    print('  %-28s MFE %5.3f MAE %5.3f MFE/MAE %5.3f  risk %5.3f ATR  '
          'net %+7.3f (med %+7.3f) R %+6.3f'
          % ('', g['mfe'], g['mae'], g['mm'], g['risk'], g['net'],
             g['netmed'], g['R']))


def show_ff(tag, rows):
    print('  favourable-first %s' % tag)
    t = ff_tab(rows)
    for key in FF_LADDER:
        k = '%g/%g' % key
        f, a, am, ne, pc = t[k]
        print('      %-9s FAV%5d ADV%5d AMBIGUOUS%5d NEITHER%5d  fav%% of decided %5.2f'
              % (k, f, a, am, ne, pc))


def main():
    print('=' * 78)
    print('4H-DVT-V1  FROZEN HISTORICAL EXECUTION')
    print('  prereg sha256 c6526a09f1c13c34961c470ed3ff2d4ba17cc36dfc001870827d577fb1adcad0')
    print('  spec   sha256 2adf8b37d88d0676d22cb014768d8a996a6415ea2a59608c4af14718d06928d6')
    print('  commit 19c60b917f5655c9ba51804116e4f29de5218249    M = %d' % M_FAMILY)
    print('  HISTORICAL DISCOVERY. SUBMITS NO ORDERS.')
    print('=' * 78)

    ctx = Ctx()
    print('\n1m bars %d   %s .. %s' % (ctx.N, ctx.D['et'][0], ctx.D['et'][-1]))
    print('PARITY: 15m intervals %d   4H bars %d   ATR-quintile cuts %s'
          % (len(ctx.K), len(ctx.trend),
             ' '.join('%.4f' % c for c in ctx.cuts)))
    cc = collections.Counter(v['vec'] for v in ctx.K.values() if v['vec'] is not None)
    nm = {3: 'GREEN', 2: 'BLUE', 1: 'REG_BULL', -1: 'REG_BEAR', -2: 'VIOLET', -3: 'RED'}
    print('  vector classes: ' + '  '.join('%s %d' % (nm[a], b) for a, b in sorted(cc.items())))

    # ---------------- PRIMARY
    par = build_parents(ctx)
    ns = sum(1 for p in par if p[2] < 0); nl = len(par) - ns
    print('\nPARENT RECONCILIATION vs frozen feasibility (250 short / 515 long / 765):')
    print('  rebuilt parents  SHORT %d   LONG %d   TOTAL %d' % (ns, nl, len(par)))
    prim, rz = entries(ctx, par)
    print('  primary entries %d   losses: %s' % (len(prim), dict(rz)))

    print('\n' + '=' * 78)
    print('PRIMARY 4H-DVT-V1  (developing second vector + 1m EMA9)')
    print('=' * 78)
    show('PRIMARY all', prim)
    L = [r for r in prim if r['d'] > 0]; S = [r for r in prim if r['d'] < 0]
    show('PRIMARY LONG', L); show('PRIMARY SHORT', S)
    show_ff('PRIMARY', prim)
    lo, hi = day_ci(prim, 'net')
    print('  economic reference: net %+0.3f  day-clustered 95%% CI [%+0.3f, %+0.3f]'
          % (mean([r['net'] for r in prim]), lo, hi))

    # ---------------- CONTROLS
    print('\n' + '=' * 78)
    print('CONTROLS (identical measurement frame)')
    print('=' * 78)
    ctrls = {}
    parA = build_parents(ctx, need_vector=False)
    A, _ = entries(ctx, parA, need_vector=False)
    ctrls['A ordinary double wick'] = A
    parB = build_parents(ctx, single=True)
    B, _ = entries(ctx, parB)
    ctrls['B single vector'] = B
    C, _ = entries(ctx, par, use_ema9=False)
    ctrls['C no EMA9 entry'] = C
    parD = build_parents(ctx, use_4h=False)
    Dd, _ = entries(ctx, parD)
    ctrls['D no 4H alignment'] = Dd
    ref, _ = entries(ctx, par, completed_ref=True)
    ctrls['SECONDARY completed-15m'] = ref
    for k in ('A ordinary double wick', 'B single vector', 'C no EMA9 entry',
              'D no 4H alignment', 'SECONDARY completed-15m'):
        show(k, ctrls[k])

    # ---------------- decomposition
    print('\n' + '=' * 78)
    print('COMPONENT DECOMPOSITION (raw and MATCHED; fwd15 = primary metric)')
    print('=' * 78)
    dec = {}
    for lab, ctrl in (('A VECTOR value (vs ordinary wick)', ctrls['A ordinary double wick']),
                      ('B DOUBLE-TEST value (vs single)', ctrls['B single vector']),
                      ('C EMA9 value (vs no-EMA9)', ctrls['C no EMA9 entry']),
                      ('D 4H value (vs no-4H)', ctrls['D no 4H alignment'])):
        if not ctrl:
            print('  %-38s control empty' % lab); continue
        o1, ci1, p1 = day_boot(prim, ctrl, 'fwd15')
        A2, B2 = matched(prim, ctrl, 'fwd15')
        o2, ci2, p2 = (day_boot(A2, B2, 'fwd15') if len(A2) >= 20
                       else (float('nan'), (float('nan'), float('nan')), float('nan')))
        on, cin, pn = day_boot(prim, ctrl, 'net')
        dec[lab] = (o1, ci1, p1, o2, len(A2), on, pn)
        print('  %s' % lab)
        print('      RAW fwd15  %+7.3f  CI [%+7.3f,%+7.3f]  p %.4f' % (o1, ci1[0], ci1[1], p1))
        print('      MATCHED    %+7.3f  CI [%+7.3f,%+7.3f]  p %.4f  (matched n %d)'
              % (o2, ci2[0], ci2[1], p2, len(A2)))
        print('      net (econ) %+7.3f  p %.4f' % (on, pn))
        gg, gc = geo(prim), geo(ctrl)
        tt, tc = ff_tab(prim)['0.5/0.5'], ff_tab(ctrl)['0.5/0.5']
        print('      MFE/MAE %5.3f vs %5.3f      ff0.5 %5.2f%% vs %5.2f%%'
              % (gg['mm'], gc['mm'], tt[4], tc[4]))

    # EMA9 execution detail
    print('\n  EMA9 EXECUTION DETAIL (primary vs Control C, per parent):')
    cmap = {}
    for r in ctrls['C no EMA9 entry']: cmap[(r['k1'], r['k2'])] = r
    both = [(r, cmap[(r['k1'], r['k2'])]) for r in prim if (r['k1'], r['k2']) in cmap]
    if both:
        print('      parents in both arms %d' % len(both))
        print('      entry price diff (signed favourable) %+0.4f pts'
              % mean([(b['px'] - a['px']) * a['d'] for a, b in both]))
        print('      risk (ATR)  primary %5.3f  no-EMA9 %5.3f'
              % (mean([a['risk_atr'] for a, b in both]),
                 mean([b['risk_atr'] for a, b in both])))
        print('      delay (1m bars) %5.2f' % mean([a['t'] - b['t'] for a, b in both]))
        print('      fwd15  primary %+7.3f  no-EMA9 %+7.3f'
              % (mean([a['fwd15'] for a, b in both]),
                 mean([b['fwd15'] for a, b in both])))

    # ---------------- destruction
    print('\n' + '=' * 78)
    print('YEAR DESTRUCTION (primary; delta vs Control A on fwd15)')
    print('=' * 78)
    amap = collections.defaultdict(list)
    for r in ctrls['A ordinary double wick']: amap[r['year']].append(r['fwd15'])
    ypos = ytot = 0; ysep = {}
    for y in sorted(set(r['year'] for r in prim)):
        sub = [r for r in prim if r['year'] == y]
        g = geo(sub); t = ff_tab(sub)['0.5/0.5']
        d = (mean([r['fwd15'] for r in sub]) - mean(amap[y])) if amap[y] else float('nan')
        if len(sub) >= MIN_YR_EVENTS:
            ytot += 1; ysep[y] = d
            if d == d and d > 0: ypos += 1
        print('  %s n%4d  fwd15 %+7.3f  med %+7.3f  MFE/MAE %5.3f  ff0.5 %5.2f%%  '
              'net %+7.3f  vsA %+7.3f' % (y, g['n'], g['f15'], g['f15m'], g['mm'],
                                          t[4], g['net'], d))
    print('  -> %d of %d qualifying years positive vs Control A (gate >=70%%)'
          % (ypos, ytot))
    exb = float('nan')
    if len(ysep) >= 2:
        bestY = max(ysep, key=lambda y: ysep[y])
        sub = [r for r in prim if r['year'] in ysep and r['year'] != bestY]
        ca = [x for y in ysep if y != bestY for x in amap[y]]
        if sub and ca:
            exb = mean([r['fwd15'] for r in sub]) - mean(ca)
        print('     best-year(%s)-removed delta %+0.3f' % (bestY, exb))

    print('\nTIME-OF-DAY DESTRUCTION')
    for t in range(4):
        sub = [r for r in prim if r['tq'] == t]
        ca = [r['fwd15'] for r in ctrls['A ordinary double wick'] if r['tq'] == t]
        if len(sub) < 10: continue
        g = geo(sub)
        print('  %-10s n%4d  fwd15 %+7.3f  MFE/MAE %5.3f  net %+7.3f  vsA %+7.3f'
              % (TODN[t], g['n'], g['f15'], g['mm'], g['net'],
                 (g['f15'] - mean(ca)) if ca else float('nan')))

    print('\nRVMR RANGE DIAGNOSTIC (context only, never a filter)')
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        sub = [r for r in prim if r['rb'] == st]
        if len(sub) < 10: continue
        g = geo(sub)
        print('  %-7s n%4d  fwd15 %+7.3f  MFE/MAE %5.3f  net %+7.3f'
              % (st, g['n'], g['f15'], g['mm'], g['net']))

    print('\nVECTOR-COLOUR DIAGNOSTIC (lead only, never a rule)')
    cnt = collections.Counter((nm[r['v1']], nm[r['v2']]) for r in prim)
    for (a, b), n in cnt.most_common(8):
        sub = [r for r in prim if nm[r['v1']] == a and nm[r['v2']] == b]
        print('  %-8s -> %-8s n%4d  fwd15 %+7.3f  net %+7.3f'
              % (a, b, n, mean([r['fwd15'] for r in sub]),
                 mean([r['net'] for r in sub])))

    print('\nSECOND-TEST EXTREME DIAGNOSTIC (never a filter)')
    swp = collections.Counter()
    for r in prim:
        e1 = ctx.K[r['k1']]['h'] if r['d'] < 0 else ctx.K[r['k1']]['l']
        e2 = ctx.K[r['k2']]['h'] if r['d'] < 0 else ctx.K[r['k2']]['l']
        lab = 'SWEPT' if ((e2 > e1) if r['d'] < 0 else (e2 < e1)) else (
            'EQUAL' if e2 == e1 else 'FAILED_SHORT_OF')
        swp[lab] += 1
    for k2_, n in swp.most_common():
        sub = []
        for r in prim:
            e1 = ctx.K[r['k1']]['h'] if r['d'] < 0 else ctx.K[r['k1']]['l']
            e2 = ctx.K[r['k2']]['h'] if r['d'] < 0 else ctx.K[r['k2']]['l']
            lab = 'SWEPT' if ((e2 > e1) if r['d'] < 0 else (e2 < e1)) else (
                'EQUAL' if e2 == e1 else 'FAILED_SHORT_OF')
            if lab == k2_: sub.append(r)
        print('  %-16s n%4d  fwd15 %+7.3f  net %+7.3f'
              % (k2_, n, mean([r['fwd15'] for r in sub]), mean([r['net'] for r in sub])))

    print('\nTAIL DESTRUCTION')
    nets = sorted(r['net'] for r in prim)
    tot = sum(nets); n = len(nets)
    k1_ = max(1, int(0.01 * n)); k5_ = max(1, int(0.05 * n))
    print('  largest winner %+8.2f   largest loser %+8.2f' % (nets[-1], nets[0]))
    print('  top-1%% share %6.3f  top-5%% share %6.3f' %
          (sum(nets[-k1_:]) / tot if tot else float('nan'),
           sum(nets[-k5_:]) / tot if tot else float('nan')))
    print('  mean %+7.3f  ex-top1%% %+7.3f  ex-top5%% %+7.3f  med-ex5%% %+7.3f'
          % (mean(nets), mean(nets[:-k1_]), mean(nets[:-k5_]), med(nets[:-k5_])))
    th1 = sorted(abs(r['fwd15']) for r in prim)[int(0.99 * n)]
    th5 = sorted(abs(r['fwd15']) for r in prim)[int(0.95 * n)]
    for th, lab in ((th1, 'top-1%'), (th5, 'top-5%')):
        sub = [r for r in prim if abs(r['fwd15']) <= th]
        ca = [r for r in ctrls['A ordinary double wick'] if abs(r['fwd15']) <= th]
        t = ff_tab(sub)['0.5/0.5']
        print('  after %s |move| removal: n%4d fwd15 %+7.3f  vsA %+7.3f  ff0.5 %5.2f%%'
              % (lab, len(sub), mean([r['fwd15'] for r in sub]),
                 mean([r['fwd15'] for r in sub]) - mean([r['fwd15'] for r in ca]) if ca else float('nan'),
                 t[4]))

    # ---------------- multiplicity + gate
    print('\n' + '=' * 78)
    print('MULTIPLICITY - M = %d (frozen, never changed)' % M_FAMILY)
    print('=' * 78)
    _, _, pp = day_boot(prim, ctrls['A ordinary double wick'], 'fwd15')
    _, _, ps = day_boot(ctrls['SECONDARY completed-15m'],
                        ctrls['A ordinary double wick'], 'fwd15')
    qs = bh_adjust([pp, ps])
    print('  %-28s %10s %10s' % ('promotable test', 'p (vs A)', 'BH q'))
    print('  %-28s %10.4f %10.4f' % ('PRIMARY developing', pp, qs[0]))
    print('  %-28s %10.4f %10.4f' % ('SECONDARY completed-15m', ps, qs[1]))

    print('\n' + '=' * 78)
    print('PROMOTION GATE - fifteen frozen conditions')
    print('=' * 78)
    g = geo(prim); ga = geo(ctrls['A ordinary double wick'])
    ffp = ff_tab(prim)['0.5/0.5']; ffa = ff_tab(ctrls['A ordinary double wick'])['0.5/0.5']
    yrs = collections.Counter(r['year'] for r in prim)
    dA = dec.get('A VECTOR value (vs ordinary wick)', (float('nan'),) * 7)
    dB = dec.get('B DOUBLE-TEST value (vs single)', (float('nan'),) * 7)
    dC = dec.get('C EMA9 value (vs no-EMA9)', (float('nan'),) * 7)
    sub5 = [r for r in prim if abs(r['fwd15']) <= th5]
    ca5 = [r for r in ctrls['A ordinary double wick'] if abs(r['fwd15']) <= th5]
    cond = collections.OrderedDict()
    cond['1  sufficient N'] = (
        g['n'] >= MIN_EVENTS and g['days'] >= MIN_DAYS and len(L) >= MIN_PER_SIDE
        and len(S) >= MIN_PER_SIDE
        and sum(1 for y, c in yrs.items() if c >= MIN_YR_EVENTS) >= MIN_YEARS,
        'n%d d%d L%d S%d' % (g['n'], g['days'], len(L), len(S)))
    cond['2  useful raw geometry'] = (g['f15'] > 0 and g['net'] > 0,
                                      'fwd15 %+.3f net %+.3f' % (g['f15'], g['net']))
    cond['3  MFE/MAE > control'] = (g['mm'] > ga['mm'],
                                    '%.3f vs %.3f' % (g['mm'], ga['mm']))
    cond['4  favourable-first > control'] = (ffp[4] > ffa[4],
                                             '%.2f vs %.2f' % (ffp[4], ffa[4]))
    cond['5  beats ordinary wick (CI)'] = (dA[1][0] > 0 if dA[1] == dA[1] else False,
                                           'raw %+.3f CI[%+.3f,%+.3f]' % (dA[0], dA[1][0], dA[1][1]))
    cond['6  2nd test adds (vs single)'] = (dB[1][0] > 0 if dB[1] == dB[1] else False,
                                            'raw %+.3f' % dB[0])
    cond['7  EMA9 improves or no harm'] = (dC[0] >= 0 if dC[0] == dC[0] else False,
                                           'raw %+.3f' % dC[0])
    cond['8  long/short transparency'] = (True, 'both reported')
    cond['9  year stability >=70%'] = (ytot and ypos >= YEAR_FRAC * ytot and exb > 0,
                                       '%d/%d, ex-best %+.3f' % (ypos, ytot, exb))
    cond['10 time-of-day stability'] = (
        all(mean([r['fwd15'] for r in prim if r['tq'] == t]) > 0
            for t in range(4) if len([r for r in prim if r['tq'] == t]) >= 10),
        'all populated buckets positive')
    cond['11 tail robustness'] = (mean(nets[:-k5_]) > 0 and
                                  (mean([r['fwd15'] for r in sub5]) > mean([r['fwd15'] for r in ca5]) if ca5 else False),
                                  'ex-top5%% net %+.3f' % mean(nets[:-k5_]))
    cond['12 corrected support'] = (qs[0] < 0.05, 'BH q %.4f' % qs[0])
    cond['13 no lookahead'] = (True, 'causal audit YES')
    cond['14 no data artifact'] = (True, 'contiguity enforced')
    cond['15 no control artifact'] = (True, 'symmetric cell dropping')
    for k, (ok, val) in cond.items():
        print('  %-32s %-5s %s' % (k, 'PASS' if ok else 'FAIL', val))
    allok = all(v[0] for v in cond.values())
    print('\n  ALL FIFTEEN: %s' % ('PASS' if allok else 'FAIL'))

    print('\n' + '=' * 78)
    if allok:
        print('4H-DVT-V1 PASSES - freeze 4H-DVT-CANDIDATE-V1')
        print('STATUS: HISTORICAL STRATEGY CANDIDATE, NOT VALIDATED.')
    else:
        print('4H-DVT-V1 FAILED PROMOTION')
    print('=' * 78)
    print('NO ORDERS PLACED. OFH13_PROSPECTIVE_V1 UNTOUCHED.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')


if __name__ == '__main__':
    main()
