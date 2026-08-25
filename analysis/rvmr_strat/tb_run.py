#!/usr/bin/env python3
# ======================================================================
# RVMR-STRAT-V1  TRACK B - RVMR-native strategies, M = 8 (frozen)
# ======================================================================
# Frozen by docs/RVMR_STRAT_PREREGISTRATION.md. Runs on the RVMR-
# certified V3 extract (pure OHLCV constructs; direction always from
# price structure; RVMR alone never triggers). Uniform frozen frame:
# 1.5 ATR stop, no target, 60m time exit, 0.87 cost. No management
# rescue. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, math, random, statistics, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../rvmr', '../v41'):
    sys.path.insert(0, os.path.join(HERE, p))
import rvmr_spec as S
import rvmr_run as RV
import rvmr_prospective as RP

COST = 0.87
SEED = 20260825
COOL = 30


def year_of(day):
    return day[:4]


# ---------------------------------------------------------------- data
RV.STAMP_SHIFT = 0
D = RV.load_bars()
N = len(D['c'])
rng = [D['h'][i] - D['l'][i] for i in range(N)]
rr = S.trailing_ratio(rng)
vr = S.trailing_ratio(D['v'])
bars = list(zip(D['et'], D['o'], D['h'], D['l'], D['c'], D['v']))
atr = S.atr20(bars)
RB = [S.bucket(x) if x is not None else None for x in rr]
VB = [S.bucket(x) if x is not None else None for x in vr]


def eligible(j):
    m = D['mod'][j]
    return (S.RTH_START <= m <= S.RTH_END - 60 and atr[j] and atr[j] > 0
            and RB[j] is not None and VB[j] is not None
            and j + 60 < N and D['em'][j + 60] - D['em'][j] == 60)


def frame(j, d):
    px = D['c'][j]; a = atr[j]
    stop = px - 1.5 * a * d
    risk = 1.5 * a
    mfe = mae = 0.0
    net = None; reason = 'TIME'; t_stop = None
    reach = {}
    ff25 = None
    for k in range(1, 61):
        hi_, lo_ = D['h'][j + k], D['l'][j + k]
        u = (hi_ - px) * d; v = (px - lo_) * d
        if u > mfe: mfe = u
        if v > mae: mae = v
        for rm in (0.5, 1, 2, 3):
            if rm not in reach and mfe >= rm * risk:
                reach[rm] = k
        if ff25 is None:
            hu, hd = mfe >= 0.25 * a, mae >= 0.25 * a
            ff25 = 'AMBIG' if (hu and hd) else ('FAV' if hu else ('ADV' if hd else None))
        if net is None and ((lo_ <= stop) if d > 0 else (hi_ >= stop)):
            net, reason, t_stop = (stop - px) * d - COST, 'STOP', k
    if net is None:
        net = (D['c'][j + 60] - px) * d - COST
    return {'net': net, 'R': net / risk, 'mfe': mfe, 'mae': mae, 'atr': a,
            'reason': reason, 'reach': reach, 't_stop': t_stop,
            'ff25': ff25 or 'NEITHER', 'day': D['day'][j], 'et': D['et'][j],
            'year': D['day'][j][:4], 'd': d}


def cool(evs):
    out, last = [], -10 ** 9
    for e in sorted(evs, key=lambda x: x[0]):
        if D['em'][e[0]] - last < COOL:
            continue
        last = D['em'][e[0]]
        out.append(e)
    return out


def balance(j, n=30):
    if j < n or D['em'][j] - D['em'][j - n + 1] != n - 1:
        return None
    hs = D['h'][j - n + 1:j + 1]; ls = D['l'][j - n + 1:j + 1]
    return max(hs), min(ls)


# ---------------------------------------------------------------- session structures
def session_maps():
    """Per RTH day: overnight H/L (18:00->09:29), prior-day RTH H/L,
    prior-week RTH H/L, OR15, prior RTH close, RTH vwap prefix."""
    on = collections.defaultdict(lambda: [-1e18, 1e18])
    rthhl = collections.defaultdict(lambda: [-1e18, 1e18])
    rclose = {}
    days = sorted(set(D['day']))
    nxt = {}
    rdays = sorted(set(D['day'][i] for i in range(N)
                       if S.RTH_START <= D['mod'][i] <= S.RTH_END))
    for i, d in enumerate(rdays[:-1]):
        nxt[d] = rdays[i + 1]
    for i in range(N):
        m = D['mod'][i]; d = D['day'][i]
        if m >= 1080:
            t = nxt.get(d)
            if t:
                on[t][0] = max(on[t][0], D['h'][i])
                on[t][1] = min(on[t][1], D['l'][i])
        elif m <= 569:
            on[d][0] = max(on[d][0], D['h'][i])
            on[d][1] = min(on[d][1], D['l'][i])
        if S.RTH_START <= m <= S.RTH_END:
            rthhl[d][0] = max(rthhl[d][0], D['h'][i])
            rthhl[d][1] = min(rthhl[d][1], D['l'][i])
            rclose[d] = D['c'][i]
    prevday = {rdays[i + 1]: rdays[i] for i in range(len(rdays) - 1)}
    prevweek = {}
    for d in rdays:
        wk = datetime.datetime.strptime(d, '%Y-%m-%d').isocalendar()[:2]
        prevweek.setdefault(wk, []).append(d)
    wkeys = sorted(prevweek)
    pw_hl = {}
    for i, wk in enumerate(wkeys):
        if i == 0:
            continue
        pd = prevweek[wkeys[i - 1]]
        hh = max(rthhl[x][0] for x in pd); ll = min(rthhl[x][1] for x in pd)
        for d in prevweek[wk]:
            pw_hl[d] = (hh, ll)
    return on, rthhl, rclose, prevday, pw_hl


ON, RTHHL, RCLOSE, PREVD, PWHL = session_maps()
# per-day RTH bar indices + vwap prefix
DAYIDX = collections.defaultdict(list)
for i in range(N):
    if S.RTH_START <= D['mod'][i] <= S.RTH_END:
        DAYIDX[D['day'][i]].append(i)
VWAP = {}
for d, idx in DAYIDX.items():
    pv = vv = 0.0
    for i in idx:
        tp = (D['h'][i] + D['l'][i] + D['c'][i]) / 3.0
        pv += tp * D['v'][i]; vv += D['v'][i]
        VWAP[i] = pv / vv if vv > 0 else None


# ---------------------------------------------------------------- detectors
def accept_events():
    """Frozen: balance breakout close, then 2nd consecutive close beyond
    -> event at the 2nd close. Returns [(j, d)]."""
    ev = []
    j = 0
    for j in range(31, N - 61):
        if not eligible(j):
            continue
        bal = balance(j - 2)          # balance BEFORE the breakout bar
        if bal is None:
            continue
        hi_, lo_ = bal
        c1, c2 = D['c'][j - 1], D['c'][j]
        if D['em'][j] - D['em'][j - 1] != 1:
            continue
        if c1 > hi_ and c2 > hi_ and D['c'][j - 2] <= hi_:
            ev.append((j, 1))
        elif c1 < lo_ and c2 < lo_ and D['c'][j - 2] >= lo_:
            ev.append((j, -1))
    return cool(ev)


def pullback_events():
    """B2: expansion leg + first 1/3 pullback + re-expansion close."""
    ev = []
    for j in range(41, N - 61):
        if not eligible(j):
            continue
        d = 0
        move = D['c'][j] - D['c'][j - 10]
        if abs(move) < 1.5 * atr[j]:
            continue
        d = 1 if move > 0 else -1
        bal = balance(j - 10)
        if bal is None:
            continue
        edge = bal[0] if d > 0 else bal[1]
        beyond = (D['c'][j] > edge and D['c'][j - 1] > edge) if d > 0 else \
                 (D['c'][j] < edge and D['c'][j - 1] < edge)
        if not beyond:
            continue
        O = D['c'][j - 10]
        X = max(D['h'][j - 10:j + 1]) if d > 0 else min(D['l'][j - 10:j + 1])
        leg = abs(X - O)
        pb = None
        for k in range(j + 1, min(j + 31, N - 61)):
            if D['em'][k] - D['em'][j] != k - j:
                break
            ret = (X - D['c'][k]) * d
            if (D['c'][k] - O) * d < 0:
                break
            if ret >= leg / 3.0:
                pb = k
                break
        if pb is None:
            continue
        pe = D['h'][pb] if d > 0 else D['l'][pb]
        for m2 in range(pb + 1, min(pb + 16, N - 61)):
            if D['em'][m2] - D['em'][pb] != m2 - pb:
                break
            if (D['c'][m2] > pe) if d > 0 else (D['c'][m2] < pe):
                if eligible(m2):
                    ev.append((m2, d))
                break
    return cool(ev)


def reclaim_events():
    """B3: sweep of {ON H/L, PDH/PDL, PWH/PWL, OR15 H/L} then close back
    through within 5 bars. One frozen rule, all level classes."""
    ev = []
    for day, idx in DAYIDX.items():
        if len(idx) < 90:
            continue
        levels = []
        o = ON.get(day)
        if o and o[0] > -1e17:
            levels += [(o[0], -1), (o[1], 1)]
        pd = PREVD.get(day)
        if pd and RTHHL[pd][0] > -1e17:
            levels += [(RTHHL[pd][0], -1), (RTHHL[pd][1], 1)]
        pw = PWHL.get(day)
        if pw:
            levels += [(pw[0], -1), (pw[1], 1)]
        if len(idx) > 15:
            or15 = idx[:15]
            levels += [(max(D['h'][i] for i in or15), -1),
                       (min(D['l'][i] for i in or15), 1)]
            start = idx[15]
        else:
            continue
        used = set()
        for n_, j in enumerate(idx):
            if j < start:
                continue
            for li, (px, d) in enumerate(levels):
                if li in used:
                    continue
                swept = (D['l'][j] < px) if d > 0 else (D['h'][j] > px)
                if not swept:
                    continue
                used.add(li)
                for k in range(j + 1, min(j + 6, N - 61)):
                    if D['em'][k] - D['em'][j] != k - j:
                        break
                    back = (D['c'][k] > px) if d > 0 else (D['c'][k] < px)
                    if back:
                        if eligible(k):
                            ev.append((k, d))
                        break
    return cool(ev)


def meanrev_events():
    ev = []
    for day, idx in DAYIDX.items():
        for j in idx:
            if not eligible(j) or j not in VWAP or VWAP[j] is None:
                continue
            ext = D['c'][j] - VWAP[j]
            if abs(ext) >= 1.5 * atr[j]:
                ev.append((j, -1 if ext > 0 else 1))
    return cool(ev)


def transition_events(kind):
    """B5 LOW->HIGH etc: consecutive RTH states, then a balance breakout
    close within 5 bars; direction = breakout side. kind in
    ('LH','MH','HH') on the RANGE tool."""
    want_prev = {'LH': 'LOW', 'MH': 'MEDIUM', 'HH': 'HIGH'}[kind]
    ev = []
    for day, idx in DAYIDX.items():
        for n_, j in enumerate(idx):
            if n_ == 0 or not eligible(j):
                continue
            pj = idx[n_ - 1]
            if D['em'][j] - D['em'][pj] != 1:
                continue
            if RB[j] != 'HIGH' or RB[pj] != want_prev:
                continue
            bal = balance(j)
            if bal is None:
                continue
            hi_, lo_ = bal
            for k in range(j, min(j + 6, N - 61)):
                if D['em'][k] - D['em'][j] != k - j:
                    break
                if D['c'][k] > hi_:
                    if eligible(k):
                        ev.append((k, 1))
                    break
                if D['c'][k] < lo_:
                    if eligible(k):
                        ev.append((k, -1))
                    break
    return cool(ev)


def exhaustion_events():
    """B6: >=3 HIGH in last 10 states, now LOW; price re-enters the
    balance within 5 bars after being outside; fade toward balance mid."""
    ev = []
    for day, idx in DAYIDX.items():
        for n_, j in enumerate(idx):
            if n_ < 10 or not eligible(j):
                continue
            last10 = [RB[idx[n_ - k]] for k in range(1, 11)]
            if RB[j] != 'LOW' or sum(1 for x in last10 if x == 'HIGH') < 3:
                continue
            bal = balance(j)
            if bal is None:
                continue
            hi_, lo_ = bal
            was_out = D['c'][j] > hi_ or D['c'][j] < lo_
            if not was_out:
                continue
            d = -1 if D['c'][j] > hi_ else 1
            for k in range(j + 1, min(j + 6, N - 61)):
                if D['em'][k] - D['em'][j] != k - j:
                    break
                if lo_ <= D['c'][k] <= hi_:
                    if eligible(k):
                        ev.append((k, d))
                    break
    return cool(ev)


def open_drive_events():
    """B7 frozen from MAG: drive >= 1 ATR by 09:44, held beyond ON
    extreme, no origin reclaim, continuation on new extreme."""
    ev = []
    for day, idx in DAYIDX.items():
        if len(idx) < 90:
            continue
        j0 = idx[0]
        if not atr[j0]:
            continue
        opening = idx[:15]
        if len(opening) < 15:
            continue
        endj = opening[-1]
        drive = (D['c'][endj] - D['o'][j0]) / atr[j0]
        if abs(drive) < 1.0:
            continue
        d = 1 if drive > 0 else -1
        o = ON.get(day)
        if not o or o[0] < -1e17:
            continue
        lvl = o[0] if d > 0 else o[1]
        held = (D['c'][endj] > lvl) if d > 0 else (D['c'][endj] < lvl)
        if not held:
            continue
        ext = max(D['h'][i] for i in opening) if d > 0 else \
            min(D['l'][i] for i in opening)
        origin = D['o'][j0]
        for j in idx[15:45]:
            if (D['c'][j] < origin) if d > 0 else (D['c'][j] > origin):
                break
            made = (D['c'][j] > ext) if d > 0 else (D['c'][j] < ext)
            if made:
                if eligible(j):
                    ev.append((j, d, endj))
                break
    return ev


def gap_events():
    """B8: |open - prior RTH close| >= 0.5 ATR; decision at 09:44 close:
    accepted -> continuation; rejected -> fade."""
    acc, rej = [], []
    for day, idx in DAYIDX.items():
        pd = PREVD.get(day)
        if not pd or pd not in RCLOSE or len(idx) < 90:
            continue
        j0 = idx[0]
        if not atr[j0]:
            continue
        gap = D['o'][j0] - RCLOSE[pd]
        if abs(gap) < 0.5 * atr[j0]:
            continue
        d = 1 if gap > 0 else -1
        if len(idx) < 15:
            continue
        j = idx[14]
        if not eligible(j):
            continue
        still = (D['c'][j] > RCLOSE[pd]) if d > 0 else (D['c'][j] < RCLOSE[pd])
        (acc if still else rej).append((j, d if still else -d))
    return acc, rej


# ---------------------------------------------------------------- stats
def signflip_p(rows, iters=20000, seed=SEED):
    if not rows:
        return float('nan')
    rnd = random.Random(seed)
    byday = collections.defaultdict(list)
    for r in rows:
        byday[r['day']].append(r['net'])
    days = sorted(byday)
    sums = {d: sum(byday[d]) for d in days}
    n = sum(len(byday[d]) for d in days)
    obs = abs(sum(sums.values()) / n)
    cnt = 0
    for _ in range(iters):
        t = sum(sums[d] if rnd.random() < 0.5 else -sums[d] for d in days)
        if abs(t / n) >= obs:
            cnt += 1
    return (cnt + 1.0) / (iters + 1.0)


def day_ci(rows, iters=10000, seed=SEED):
    if not rows:
        return (float('nan'),) * 2
    rnd = random.Random(seed)
    byday = collections.defaultdict(list)
    for r in rows:
        byday[r['day']].append(r['net'])
    days = sorted(byday)
    ms = []
    for _ in range(iters):
        vals = []
        for _ in days:
            vals.extend(byday[days[rnd.randrange(len(days))]])
        ms.append(sum(vals) / len(vals))
    ms.sort()
    return ms[int(.025 * len(ms))], ms[int(.975 * len(ms))]


def bh_adjust(ps):
    idx = sorted(range(len(ps)), key=lambda i: ps[i])
    m = len(ps); q = [None] * m; prev = 1.0
    for rank, i in enumerate(reversed(idx), 1):
        v = min(prev, ps[i] * m / (m - rank + 1))
        q[i] = v; prev = v
    return q


def describe(name, rows, quiet=False):
    if not rows:
        print('  %-34s NO EVENTS' % name)
        return None
    nets = [r['net'] for r in rows]
    w = [x for x in nets if x > 0]; l = [x for x in nets if x <= 0]
    mfe = statistics.median([r['mfe'] / r['atr'] for r in rows])
    mae = statistics.median([r['mae'] / r['atr'] for r in rows])
    ff = [r for r in rows if r['ff25'] in ('FAV', 'ADV')]
    lo, hi = day_ci(rows)
    p = signflip_p(rows)
    s = sorted(nets, reverse=True)
    n5 = max(1, int(.05 * len(s)))
    res = {'n': len(rows), 'ev': sum(nets) / len(nets),
           'pf': (sum(w) / abs(sum(l))) if l and sum(l) else float('inf'),
           'wr': 100.0 * len(w) / len(nets), 'med': statistics.median(nets),
           'mfe': mfe, 'mae': mae, 'ratio': mfe / mae if mae else float('nan'),
           'ff': 100.0 * sum(1 for r in ff if r['ff25'] == 'FAV') / len(ff) if ff else float('nan'),
           'stop': 100.0 * sum(1 for r in rows if r['reason'] == 'STOP') / len(rows),
           'p': p, 'ci': (lo, hi),
           'ex5': sum(s[n5:]) / (len(s) - n5),
           'p2r': 100.0 * sum(1 for r in rows if 2 in r['reach']
                              and (r['t_stop'] is None or r['reach'][2] <= r['t_stop']))
                  / len(rows),
           'rows': rows}
    if not quiet:
        yr = collections.defaultdict(list)
        for r in rows:
            yr[r['year']].append(r['net'])
        print('  %-34s n %5d  EV %+7.2f  WR %4.1f%%  PF %5.2f  med %+7.2f  '
              'M/M %4.2f  ff %4.1f%%  P2R %4.1f%%  CI[%+.2f,%+.2f]  p %.4f'
              % (name, res['n'], res['ev'], res['wr'], res['pf'], res['med'],
                 res['ratio'], res['ff'], res['p2r'], lo, hi, p))
        print('      exTop5%% %+6.2f | years: ' % res['ex5'] + '  '.join(
            '%s %+0.1f' % (y, sum(v) / len(v)) for y, v in sorted(yr.items())))
    return res


def by_state(evs, tool='R'):
    """Split (j,d) events by frozen state at decision bar."""
    out = collections.defaultdict(list)
    SB = RB if tool == 'R' else VB
    for e in evs:
        j, d = e[0], e[1]
        st = SB[j]
        if st:
            out[st].append(frame(j, d))
    return out


# ---------------------------------------------------------------- main
if __name__ == '__main__':
    print('TRACK B  universe: %d bars  %s .. %s' % (N, D['et'][0], D['et'][-1]))
    fam = []

    def run_cell(bid, title, all_evs, gate_state, tool='R', flip_gate=None):
        """gate_state: state required for the PRIMARY arm."""
        print('=' * 96)
        print('%s  %s' % (bid, title))
        st = by_state(all_evs, tool)
        allrows = [x for v in st.values() for x in v]
        base = describe('CONTROL: structure alone (all states)', allrows)
        for s2 in ('LOW', 'MEDIUM', 'HIGH'):
            if st.get(s2):
                describe('  state %s' % s2, st[s2])
        prim = st.get(gate_state, [])
        res = describe('PRIMARY: structure + %s %s' % (tool, gate_state), prim)
        if res and base:
            print('      delta vs control %+0.2f   (control EV %+0.2f)'
                  % (res['ev'] - base['ev'], base['ev']))
            fam.append((bid, res['p'], res, base))
        else:
            fam.append((bid, 1.0, res, base))
        print()
        return st

    ae = accept_events()
    run_cell('B1', 'HIGH-RVMR accepted breakout', ae, 'HIGH', 'R')
    st_v = by_state(ae, 'V')
    r_ = describe('  B1 volume arm: + VOLUME HIGH', st_v.get('HIGH', []))

    pe = pullback_events()
    run_cell('B2', 'HIGH-RVMR first pullback continuation', pe, 'HIGH', 'R')

    re_ = reclaim_events()
    run_cell('B3', 'sweep -> reclaim across level classes', re_, 'HIGH', 'R')

    me = meanrev_events()
    run_cell('B4', 'LOW-RVMR mean reversion to VWAP', me, 'LOW', 'R')

    print('=' * 96)
    print('B5  LOW->HIGH expansion transition vs MED->HIGH vs HIGH->HIGH')
    tr = {}
    for kind, lab in (('LH', 'LOW->HIGH'), ('MH', 'MED->HIGH'), ('HH', 'HIGH->HIGH')):
        evs = transition_events(kind)
        rows = [frame(j, d) for j, d in evs]
        tr[kind] = describe('%s + breakout' % lab, rows)
    if tr['LH']:
        fam.append(('B5', tr['LH']['p'], tr['LH'], tr['HH']))
    print()

    print('=' * 96)
    print('B6  HIGH->LOW exhaustion (fade re-entry)')
    ex = exhaustion_events()
    rows6 = [frame(j, d) for j, d in ex]
    r6 = describe('HIGH->LOW + balance re-entry fade', rows6)
    fam.append(('B6', r6['p'] if r6 else 1.0, r6, None))
    print()

    od = open_drive_events()
    print('=' * 96)
    print('B7  opening drive continuation + HIGH RVMR (decision at 09:44)')
    all7 = [frame(j, d) for j, d, ej in od]
    b7 = describe('CONTROL: drive continuation alone', all7)
    hi7 = [frame(j, d) for j, d, ej in od if RB[ej] == 'HIGH']
    r7 = describe('PRIMARY: + RANGE HIGH at 09:44', hi7)
    for s2 in ('LOW', 'MEDIUM'):
        g = [frame(j, d) for j, d, ej in od if RB[ej] == s2]
        if g:
            describe('  state %s' % s2, g)
    fam.append(('B7', r7['p'] if r7 else 1.0, r7, b7))
    print()

    print('=' * 96)
    print('B8  gap acceptance / rejection x RVMR')
    acc, rej = gap_events()
    for lab, evs, gate in (('ACCEPTED gap continuation', acc, 'HIGH'),
                           ('REJECTED gap fade', rej, 'HIGH')):
        st = by_state(evs, 'R')
        allrows = [x for v in st.values() for x in v]
        b = describe('%s: all states' % lab, allrows)
        for s2 in ('LOW', 'MEDIUM', 'HIGH'):
            if st.get(s2):
                describe('  state %s' % s2, st[s2])
    accst = by_state(acc, 'R')
    r8 = describe('PRIMARY: accepted gap + RANGE HIGH', accst.get('HIGH', []))
    b8 = describe('control (all accepted)', [x for v in accst.values() for x in v],
                  quiet=True)
    fam.append(('B8', r8['p'] if r8 else 1.0, r8, b8))
    print()

    print('=' * 96)
    print('TRACK B FAMILY ACCOUNTING  (M = 8, BH; promotion needs the full gate)')
    ps = [p for _, p, _, _ in fam]
    qs = bh_adjust(ps)
    for (bid, p, res, base), q in zip(fam, qs):
        ev = res['ev'] if res else float('nan')
        print('  %-4s EV %+8.2f  n %5s  p %.4f  q %.4f%s'
              % (bid, ev, res['n'] if res else '-', p, q,
                 '' if q > 0.05 else '  <-- passes q only; full gate decides'))
