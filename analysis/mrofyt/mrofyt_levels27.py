#!/usr/bin/env python3
"""mrofyt_levels27.py - MROF-YT-W27-LEVELS-1.0

MROF_YT_WAVE27_LEVELS_REGISTRATION.md turned into running code: every
key level, every way of trading it, counted.

    levels   yesterday's, the overnight's and last week's high and low,
             yesterday's close, the open, the 15- and 60-minute opening
             ranges, the morning's range, the previous hour's, round
             hundreds, 5- and 15-minute swings, the Asian and European
             ranges
    events   break, rejection, retest, failed breakout; the squeeze
    held     15 to 180 minutes, one trade at a time, both directions
    counted  877 strategies as 181 hypotheses (EPROP is the last)
    stage 1  the discovery weeks: what A and B already earn taken out,
             t of the weekly sums at least 2.5, twelve at most go on
    stage 2  the lockbox weeks, once: Benjamini-Hochberg at 10 %

    python3 mrofyt_levels27.py "<NQ minute exports>" --out w27_discovery.json
    python3 mrofyt_levels27.py "<NQ minute exports>" --lockbox --out w27_lockbox.json
    options: --stamps-tz UTC|ET  --stamps end|start

Stage 1 computes nothing on a lockbox session. The lockbox read is made
once and recorded before any result is shown. Read-only; no order is
placed.
"""
import array
import collections
import datetime
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_discover as DI         # noqa: E402
import mrofyt_improve26 as W26       # noqa: E402
import mrofyt_screen15 as S          # noqa: E402

W27_VERSION = 'MROF-YT-W27-LEVELS-1.0'
REGISTRATION = 'MROF_YT_WAVE27_LEVELS_REGISTRATION.md'
HISTORY_LEDGER = W25.HISTORY_LEDGER
NG = 1320                    # the grid: minutes from 18:00 to 16:00
R0 = 930                     # 09:30 on it
ASIA_END, EUR_END = 480, 840     # 02:00, 08:00
AM_END, PM_END = 120, 360    # entry bars, minutes after 09:30
H_RTH, H_ASIA, H_EUR = (15, 30, 60, 120, 180), (30, 60, 120, 180), \
    (15, 30, 60)
EVENTS = ('BRK', 'REJ', 'RET', 'FBK')
OUTER = ('PDX', 'ONX', 'PWX')          # their REJ and FBK: part 16A's
INNER = ('PDC', 'OPN', 'OR15', 'IB60', 'HRX', 'RND', 'SW5', 'SW15')
HOURS = (30, 90, 150, 210, 270, 330)   # 10:00 ... 15:00
ROUND = 100.0
SWING_K = 3
HISTORY = 14
SQZ_BARS, SQZ_SHARE = 30, 0.5
ON_FIRST, ON_BARS = 60, 600
MIN_TRADES, MIN_POSITIVE, MIN_T, MAX_FORWARD = 150, 0.6, 2.5, 12
BH_Q = 0.10


def families():
    """{family: its holds}: the 90 of the registration, in its order."""
    out = collections.OrderedDict()
    for g in OUTER:
        for e in ('BRK', 'RET'):
            for w in ('AM', 'PM'):
                out['%s.%s.%s' % (g, e, w)] = H_RTH
    for g in INNER:
        for e in EVENTS:
            for w in ('AM', 'PM'):
                out['%s.%s.%s' % (g, e, w)] = H_RTH
    for e in EVENTS:
        out['AMX.%s.PM' % e] = H_RTH
    for w in ('AM', 'PM'):
        out['SQZ.BRK.%s' % w] = H_RTH
    for e in EVENTS:
        out['ASIA.%s.EU' % e] = H_ASIA
    for e in EVENTS:
        out['EUR.%s.PRE' % e] = H_EUR
    return out


FAMILIES = families()
HYPOTHESES = tuple(h for f in FAMILIES for h in (f, f + '~')) + ('EPROP',)
N_STRATEGIES = 2 * sum(len(h) for h in FAMILIES.values()) + 1


# ---------------------------------------------------------------------
# the weeks, and the half that is locked away
# ---------------------------------------------------------------------
def _date(s):
    return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def week_label(d):
    y, w, _ = d.isocalendar()
    return '%04d-W%02d' % (y, w)


def is_lockbox(label):
    return int(hashlib.sha256(label.encode('ascii')).hexdigest()[:8],
               16) % 2 == 1


# ---------------------------------------------------------------------
# the grid of one session
# ---------------------------------------------------------------------
class Full(object):
    """One usable session on the grid from 18:00 to 16:00: C, H, L, V of
    each minute (a minute without a bar carries the last close). P(t),
    the last close before grid minute t, is C[t - 1]."""
    __slots__ = ('session', 'contract', 'C', 'H', 'L', 'V', 'first',
                 'on_ok', 'sig', 'week', 'lock', 'pdh', 'pdl', 'pdc',
                 'pwh', 'pwl')


def grid_of(st):
    """(C, H, L, V, the first minute with a bar, bars before 09:30) from
    the reader's bars of one contract and session; None without a bar."""
    bars, vols = st['bars'], st['vols']
    slot = {}
    for k in range(len(vols)):
        i = int((bars[4 * k] + 21600) // 60)
        if 0 <= i < NG:
            slot[i] = (bars[4 * k + 3], bars[4 * k + 1], bars[4 * k + 2],
                       vols[k])
    if not slot:
        return None
    first = min(slot)
    last = slot[first][0]
    C, H, L, V = (array.array('d', bytes(8 * NG)) for _ in range(4))
    for i in range(NG):
        b = slot.get(i)
        if b is None:
            C[i] = H[i] = L[i] = last
        else:
            C[i], H[i], L[i], V[i] = b
            last = b[0]
    return C, H, L, V, first, sum(1 for i in slot if i < R0)


def daily_vol(chain):
    """{session: the standard deviation of the 14 daily returns before
    it}: B's own s."""
    rets, vol = [], {}
    for r in chain:
        if len(rets) >= S.B_HISTORY:
            vol[r['session']] = S.stdev(rets[-S.B_HISTORY:])
        if r['ret'] is not None:
            rets.append(r['ret'])
    return vol


def week_ranges(rd):
    """{contract: {week: [high, low]}} over whole weekday sessions."""
    out = collections.defaultdict(dict)
    for (c, s), st in rd.days.items():
        d = _date(s)
        if d.weekday() >= 5 or st.get('full_high') is None:
            continue
        hl = out[c].setdefault(week_label(d), [st['full_high'],
                                               st['full_low']])
        hl[0], hl[1] = max(hl[0], st['full_high']), min(hl[1],
                                                        st['full_low'])
    return out


def sessions(rd, days, order, chain):
    """The usable sessions, one Full at a time, in order."""
    vol, weeks = daily_vol(chain), week_ranges(rd)
    prev_of = {r['session']: r['prev'] for r in chain}
    for s in order:
        if not vol.get(s):
            continue
        d = days[s]
        g = grid_of(rd.days[(d.contract, s)])
        if g is None:
            continue
        f = Full()
        f.session, f.contract, f.sig = s, d.contract, vol[s]
        f.C, f.H, f.L, f.V, f.first, n_on = g
        f.on_ok = f.first < ON_FIRST and n_on >= ON_BARS
        day = _date(s)
        f.week = week_label(day)
        f.lock = is_lockbox(f.week)
        pst = rd.days[(d.contract, prev_of[s])]
        f.pdh, f.pdl, f.pdc = pst['rth_high'], pst['rth_low'], d.pc
        hl = weeks[d.contract].get(week_label(
            day - datetime.timedelta(days=7)))
        f.pwh, f.pwl = hl if hl else (None, None)
        yield f


# ---------------------------------------------------------------------
# levels and events
# ---------------------------------------------------------------------
def swings(H, L, w, k=SWING_K):
    """[(the first bar that may test it, minutes after 09:30, price)] of
    the swing highs and lows of w-minute bars from 09:30."""
    nb = (NG - R0) // w
    hs = [max(H[R0 + b * w:R0 + (b + 1) * w]) for b in range(nb)]
    ls = [min(L[R0 + b * w:R0 + (b + 1) * w]) for b in range(nb)]
    out = []
    for b in range(k, nb - k):
        arm = (b + k + 1) * w
        if hs[b] > max(hs[b - k:b]) and hs[b] >= max(hs[b + 1:b + k + 1]):
            out.append((arm, hs[b]))
        if ls[b] < min(ls[b - k:b]) and ls[b] <= min(ls[b + 1:b + k + 1]):
            out.append((arm, ls[b]))
    return out


def rth_levels(f):
    """[[group, price, first bar on the grid, state, break direction]]
    of the cash session, by first bar."""
    H, L = f.H, f.L
    lv = []

    def add(group, price, arm):
        if price is not None:
            lv.append([group, price, R0 + arm, 0, 0])
    add('PDX', f.pdh, 0)
    add('PDX', f.pdl, 0)
    if f.on_ok:
        add('ONX', max(H[:R0]), 0)
        add('ONX', min(L[:R0]), 0)
    add('PWX', f.pwh, 0)
    add('PWX', f.pwl, 0)
    add('PDC', f.pdc, 0)
    add('OPN', f.C[R0 - 1], 30)
    for group, n in (('OR15', 15), ('IB60', 60), ('AMX', 150)):
        add(group, max(H[R0:R0 + n]), n)
        add(group, min(L[R0:R0 + n]), n)
    for t in HOURS:
        add('HRX', max(H[R0 + t - 60:R0 + t]), t)
        add('HRX', min(L[R0 + t - 60:R0 + t]), t)
    lo, hi = min(L[R0:R0 + PM_END]), max(H[R0:R0 + PM_END])
    for k in range(int(math.floor(lo / ROUND)), int(math.ceil(hi / ROUND))
                   + 1):
        add('RND', ROUND * k, 0)
    for group, w in (('SW5', 5), ('SW15', 15)):
        for arm, price in swings(H, L, w):
            add(group, price, arm)
    lv.sort(key=lambda x: x[2])
    return lv


def machine(f, levels, i_from, i_to):
    """[(bar, group, event, own direction)]: each level's first test
    (BRK when the bar closes beyond it, REJ when not) and, after a
    break, its first return (RET when it closes on the break's side,
    FBK when not), over the bars i_from .. i_to - 1."""
    C, H, L = f.C, f.H, f.L
    out, active, pi = [], [], 0
    for i in range(i_from, i_to):
        while pi < len(levels) and levels[pi][2] <= i:
            active.append(levels[pi])
            pi += 1
        prev, hi, lo, cl = C[i - 1], H[i], L[i], C[i]
        done = False
        for lv in active:
            x = lv[1]
            if lv[3] == 0:
                if prev < x:
                    if hi >= x:
                        if cl > x:
                            out.append((i, lv[0], 'BRK', 1))
                            lv[3], lv[4] = 1, 1
                        else:
                            out.append((i, lv[0], 'REJ', -1))
                            lv[3], done = 2, True
                elif prev > x and lo <= x:
                    if cl < x:
                        out.append((i, lv[0], 'BRK', -1))
                        lv[3], lv[4] = 1, -1
                    else:
                        out.append((i, lv[0], 'REJ', 1))
                        lv[3], done = 2, True
            elif lv[4] > 0:
                if lo <= x:
                    out.append((i, lv[0], 'RET', 1) if cl > x else
                               (i, lv[0], 'FBK', -1))
                    lv[3], done = 2, True
            elif hi >= x:
                out.append((i, lv[0], 'RET', -1) if cl < x else
                           (i, lv[0], 'FBK', 1))
                lv[3], done = 2, True
        if done:
            active = [lv for lv in active if lv[3] != 2]
    return out


def rth_signals(f):
    return machine(f, rth_levels(f), R0, R0 + PM_END)


def on_signals(f):
    """The Asian range tested 02:00-08:00, the European 08:00-09:30."""
    out = []
    for group, a, b, end in (('ASIA', 0, ASIA_END, EUR_END),
                             ('EUR', ASIA_END, EUR_END, R0)):
        out += machine(f, [[group, max(f.H[a:b]), b, 0, 0],
                           [group, min(f.L[a:b]), b, 0, 0]], b, end)
    return out


def widths(f):
    """[(highest high, lowest low) of the 30 bars before bar j] for j =
    30 .. 359 minutes after 09:30."""
    H, L = f.H, f.L
    return [(max(H[R0 + j - SQZ_BARS:R0 + j]),
             min(L[R0 + j - SQZ_BARS:R0 + j]))
            for j in range(SQZ_BARS, PM_END)]


def sqz_signals(f, wd, hist):
    """A close out of the last 30 bars' range while that range is under
    half its median at that minute over the 14 sessions in `hist`."""
    out, up, dn = [], False, False
    mid = len(hist) // 2
    for n, (hi, lo) in enumerate(wd):
        v = sorted(h[n] for h in hist)
        if hi - lo >= SQZ_SHARE * 0.5 * (v[mid - 1] + v[mid]):
            continue
        i = R0 + SQZ_BARS + n
        cl = f.C[i]
        if cl > hi and not up:
            out.append((i, 'SQZ', 'BRK', 1))
            up = True
        elif cl < lo and not dn:
            out.append((i, 'SQZ', 'BRK', -1))
            dn = True
    return out


def family_of(i, group, event):
    if group == 'ASIA':
        return 'ASIA.%s.EU' % event
    if group == 'EUR':
        return 'EUR.%s.PRE' % event
    return '%s.%s.%s' % (group, event, 'AM' if i - R0 < AM_END else 'PM')


def day_results(f, sigs, cost):
    """{family: [(gross, cost, trades) for each hold]} of one session,
    in R; a strategy holds one trade at a time."""
    by = collections.OrderedDict()
    for i, group, event, d in sigs:
        fid = family_of(i, group, event)
        if fid in FAMILIES:
            by.setdefault(fid, []).append((i, d))
    C, s, out = f.C, f.sig, {}
    for fid, ev in by.items():
        res = []
        for h in FAMILIES[fid]:
            g = c = 0.0
            n = busy = 0
            for i, d in ev:
                t0 = i + 1
                if t0 < busy:
                    continue
                t1 = min(t0 + h, NG)
                if t1 <= t0:
                    continue
                p0 = C[t0 - 1]
                g += d * (C[t1 - 1] - p0) / p0 / s
                c += cost / p0 / s
                n += 1
                busy = t1
            res.append((g, c, n))
        out[fid] = res
    return out


def eprop_sessions(chain):
    """The sessions EPROP is long: from the day after E's buy to the day
    of its sell."""
    held, long_ = set(), False
    for r in chain:
        if long_:
            held.add(r['session'])
        if r['high'] is None or r['high'] <= r['low']:
            continue
        ibs = (r['close'] - r['low']) / (r['high'] - r['low'])
        if not long_ and ibs < S.E_BUY:
            long_ = True
        elif long_ and ibs > S.E_SELL:
            long_ = False
    return held


# ---------------------------------------------------------------------
# one set's daily results
# ---------------------------------------------------------------------
def compute(rd, days, order, chain, cost, lockbox=False, only=None):
    """The daily results of every family (of `only`) on the usable
    sessions of the discovery weeks, or of the lockbox weeks; nothing of
    the other set is computed, its bars serve as history alone."""
    bi = W26.b_inputs(days, order, chain)
    held = eprop_sessions(chain)
    out = dict(sessions=[], weeks=[], A=[], B=[], fam={}, eprop=[],
               other=0)
    fam, hist = out['fam'], collections.deque(maxlen=HISTORY)
    for f in sessions(rd, days, order, chain):
        wd = widths(f)
        if f.lock != lockbox:
            out['other'] += 1
            hist.append([hi - lo for hi, lo in wd])
            continue
        k = len(out['sessions'])
        out['sessions'].append(f.session)
        out['weeks'].append(f.week)
        d = days[f.session]
        t = S.trade_a(d)
        out['A'].append((t['gross'] - t['cost']) / f.sig if t else 0.0)
        b = 0.0
        if f.session in bi:
            g, c, n = S.day_b(d, bi[f.session][0])
            if n:
                b = (g - c) / f.sig
        out['B'].append(b)
        p0 = f.C[f.first]
        out['eprop'].append(
            (f.session in held and f.first < ON_FIRST,
             f.C[NG - 1] / p0 - 1.0, cost / p0, f.sig,
             f.first < ON_FIRST))
        sigs = rth_signals(f)
        if len(hist) == HISTORY:
            sigs += sqz_signals(f, wd, hist)
        if f.on_ok:
            sigs += on_signals(f)
        for fid, res in day_results(f, sigs, cost).items():
            if only is not None and fid not in only:
                continue
            fam.setdefault(fid, {})[k] = res
        hist.append([hi - lo for hi, lo in wd])
    return out


def series(data, hid, bench=None):
    """(the hypothesis's daily results, each strategy's mean daily
    result, mean trades a strategy) over the set's sessions."""
    n = len(data['sessions'])
    if hid == 'EPROP':
        x = [(r - c - bench) / s if held else 0.0
             for held, r, c, s, _ok in data['eprop']]
        m = S.mean(x) if n else 0.0
        return x, [m], sum(1 for e in data['eprop'] if e[0])
    fid, sign = (hid[:-1], -1.0) if hid.endswith('~') else (hid, 1.0)
    holds = len(FAMILIES[fid])
    per = [[0.0] * n for _ in range(holds)]
    trades = [0] * holds
    for k, res in data['fam'].get(fid, {}).items():
        for v, (g, c, m) in enumerate(res):
            per[v][k] = sign * g - c
            trades[v] += m
    x = [sum(per[v][k] for v in range(holds)) / holds for k in range(n)]
    return x, [S.mean(p) if n else 0.0 for p in per], \
        sum(trades) / float(holds)


def eprop_bench(data):
    v = [e[1] for e in data['eprop'] if e[4]]
    return S.mean(v) if v else 0.0


# ---------------------------------------------------------------------
# the statistics
# ---------------------------------------------------------------------
def slopes(x, a, b):
    """The slopes of x on a and on b, fitted together with a constant."""
    n = len(x)
    if n < 3:
        return 0.0, 0.0
    mx, ma, mb = S.mean(x), S.mean(a), S.mean(b)
    saa = sum((u - ma) ** 2 for u in a)
    sbb = sum((u - mb) ** 2 for u in b)
    sab = sum((u - ma) * (v - mb) for u, v in zip(a, b))
    sax = sum((u - ma) * (v - mx) for u, v in zip(a, x))
    sbx = sum((u - mb) * (v - mx) for u, v in zip(b, x))
    det = saa * sbb - sab * sab
    if det <= 1e-12 * saa * sbb or det <= 0.0:
        return (sax / saa if saa > 0 else 0.0), 0.0
    return (sax * sbb - sbx * sab) / det, (sbx * saa - sax * sab) / det


def weekly_t(vals, weeks):
    """dict(t, p one-sided, weeks) of the weekly sums of vals."""
    sums = collections.OrderedDict()
    for v, w in zip(vals, weeks):
        sums[w] = sums.get(w, 0.0) + v
    x = list(sums.values())
    n = len(x)
    if n < 3:
        return dict(t=None, p=None, weeks=n)
    sd = S.stdev(x)
    if sd <= 0.0:
        return dict(t=None, p=None, weeks=n)
    t = S.mean(x) / (sd / math.sqrt(n))
    p2 = DI.t_p_two_sided(t, n - 1)
    return dict(t=t, p=p2 / 2.0 if t > 0 else 1.0 - p2 / 2.0, weeks=n)


def _corr(x, y):
    mx, my = S.mean(x), S.mean(y)
    sxx = sum((u - mx) ** 2 for u in x)
    syy = sum((u - my) ** 2 for u in y)
    if sxx <= 0 or syy <= 0:
        return 0.0
    return sum((u - mx) * (v - my) for u, v in zip(x, y)) / math.sqrt(
        sxx * syy)


def assess(data, hid, bench, betas=None):
    """One hypothesis on one set: raw, the share of its strategies above
    0, the slopes on A and B (given, or fitted here), alpha and its t."""
    x, means, trades = series(data, hid, bench)
    A, B = data['A'], data['B']
    ba, bb = betas if betas is not None else slopes(x, A, B)
    alpha = [u - ba * a - bb * b for u, a, b in zip(x, A, B)]
    wt = weekly_t(alpha, data['weeks'])
    return dict(
        id=hid, trades=round(trades, 1), raw=S.mean(x) if x else 0.0,
        positive=sum(1 for m in means if m > 0) / float(len(means)),
        beta_a=ba, beta_b=bb, corr_a=round(_corr(x, A), 3),
        corr_b=round(_corr(x, B), 3),
        alpha=S.mean(alpha) if alpha else 0.0, t=wt['t'], p=wt['p'],
        weeks=wt['weeks'])


def stage1(data):
    bench = eprop_bench(data)
    rows = [assess(data, h, bench) for h in HYPOTHESES]
    for r in rows:
        r['eligible'] = bool(
            r['trades'] >= MIN_TRADES and r['raw'] > 0 and
            r['positive'] >= MIN_POSITIVE and r['t'] is not None and
            r['t'] >= MIN_T)
    fwd = sorted((r for r in rows if r['eligible']),
                 key=lambda r: (-r['t'], r['id']))[:MAX_FORWARD]
    ids = [r['id'] for r in fwd]
    for r in rows:
        r['forwarded'] = r['id'] in ids
    return rows, ids, bench


def stage2(data, forwarded, bench):
    """forwarded: [stage 1's row of each hypothesis that went on]."""
    rows = [assess(data, r['id'], bench, (r['beta_a'], r['beta_b']))
            for r in forwarded]
    qs = DI.bh_q([r['p'] for r in rows])
    for r, q in zip(rows, qs):
        r['q'] = q
        r['status'] = 'CONFIRMED' if (q is not None and q <= BH_Q and
                                      r['raw'] > 0) else 'NOT CONFIRMED'
    return rows


# ---------------------------------------------------------------------
# the reads
# ---------------------------------------------------------------------
def run(path, lockbox=False, stamps_tz='UTC', stamps='end', market='NQ'):
    rd, chk = W25.read(path, market, stamps_tz, stamps)
    days, order, chain = S.build(rd)
    if len(order) < W25.MIN_SESSIONS:
        raise CX.ContextDataError(
            'only %d usable %s sessions: this needs years of minute bars. '
            'Nothing was computed.' % (len(order), market))
    g = W25.gaps(chain)
    if g:
        raise CX.ContextDataError(
            'the %s exports have no cash session between %s: a contract was '
            'not exported. Nothing was computed.' % (market,
                                                     W25._gap_text(g)))
    with W25.costs(market) as c:
        disc = compute(rd, days, order, chain, c['rt'])
        rows, ids, bench = stage1(disc)
        rep = dict(
            wave27=W27_VERSION, registration=REGISTRATION,
            part='lockbox' if lockbox else 'discovery', market=market,
            stamp_check=chk, cost=c['rt'], strategies=N_STRATEGIES,
            hypotheses=len(HYPOTHESES),
            discovery=dict(sessions=len(disc['sessions']),
                           weeks=len(set(disc['weeks'])),
                           first=disc['sessions'][0],
                           last=disc['sessions'][-1]),
            lockbox_sessions=disc['other'], eprop_bench=bench,
            rows=sorted(rows, key=lambda r: (r['t'] is None,
                                             -(r['t'] or 0.0), r['id'])),
            forwarded=ids, first_session=order[0], last_session=order[-1],
            n_trades=int(sum(r['trades'] for r in rows)))
        if lockbox:
            by = {r['id']: r for r in rows}
            fams = {h.rstrip('~') for h in ids}
            lock = compute(rd, days, order, chain, c['rt'], True, fams)
            res = stage2(lock, [by[h] for h in ids], bench)
            rep['lockbox'] = dict(
                sessions=len(lock['sessions']),
                weeks=len(set(lock['weeks'])), rows=res,
                confirmed=[r['id'] for r in res
                           if r['status'] == 'CONFIRMED'])
    return rep


NAMES = dict(
    PDX='yesterday\'s high/low', ONX='overnight high/low',
    PWX='last week\'s high/low', PDC='yesterday\'s close', OPN='the open',
    OR15='15-min opening range', IB60='first-hour range',
    AMX='morning range', HRX='previous hour\'s high/low',
    RND='round hundreds', SW5='5-min swings', SW15='15-min swings',
    SQZ='squeeze', ASIA='Asian range', EUR='European range',
    BRK='break', REJ='rejection', RET='retest', FBK='failed breakout')


def name_of(hid):
    if hid == 'EPROP':
        return 'E for a prop account'
    g, e, w = hid.rstrip('~').split('.')
    return '%s, %s, %s%s' % (NAMES[g], NAMES[e], w,
                             ' (reversed)' if hid.endswith('~') else '')


def _row(r):
    return '  %-16s %-46s %7.0f %+7.2f %4.0f%% %+5.2f %+5.2f %+7.2f %s' % (
        r['id'], name_of(r['id'])[:46], r['trades'], 100 * r['raw'],
        100 * r['positive'], r['corr_a'], r['corr_b'], 100 * r['alpha'],
        '%+5.2f' % r['t'] if r['t'] is not None else '    -')


def text(rep, top=30):
    d = rep['discovery']
    L = ['%s  %s  %d strategies in %d hypotheses' % (
        rep['wave27'], rep['market'], rep['strategies'],
        rep['hypotheses']),
        'Stage 1, discovery weeks: %d sessions in %d weeks (%s .. %s); %d '
        'lockbox sessions not computed.' % (
            d['sessions'], d['weeks'], d['first'], d['last'],
            rep['lockbox_sessions']),
        'raw and alpha: hundredths of a normal day\'s move, a day; alpha '
        'has A and B taken out.', '',
        '  %-16s %-46s %7s %7s %5s %5s %5s %7s %5s' % (
            'hypothesis', '', 'trades', 'raw', 'pos', 'cA', 'cB', 'alpha',
            't')]
    L += [_row(r) for r in rep['rows'][:top]]
    L += ['', 'With t at least %.1f: %d. Forwarded (at most %d): %s' % (
        MIN_T, sum(1 for r in rep['rows']
                   if r['t'] is not None and r['t'] >= MIN_T),
        MAX_FORWARD, ', '.join(rep['forwarded']) or 'none')]
    if 'lockbox' in rep:
        k = rep['lockbox']
        L += ['', '*** LOCKBOX: %d sessions in %d weeks, read once. ***' % (
            k['sessions'], k['weeks'])]
        for r in k['rows']:
            L.append('  %-16s %-46s raw %+6.2f  alpha %+6.2f  t %s  p %s  '
                     'q %s  %s' % (
                         r['id'], name_of(r['id'])[:46], 100 * r['raw'],
                         100 * r['alpha'],
                         '%+.2f' % r['t'] if r['t'] is not None else '-',
                         '%.4f' % r['p'] if r['p'] is not None else '-',
                         '%.3f' % r['q'] if r['q'] is not None else '-',
                         r['status']))
        L.append('CONFIRMED: %s' % (', '.join(k['confirmed']) or 'none'))
    L.append('Minute bars, costs charged; not P&L. No order was placed.')
    return '\n'.join(L)


def read_made(path, part, market):
    return any(r.get('version') == W27_VERSION and r.get('part') == part
               and r.get('market') == market
               for r in W25.ledger_doc(path).get('reads', []))


def record_read(rep, path):
    doc = W25.ledger_doc(path)
    doc.setdefault('reads', []).append(dict(
        version=W27_VERSION, part=rep['part'], market=rep['market'],
        first=rep['first_session'], last=rep['last_session'],
        n=rep['n_trades'],
        at=datetime.datetime.now(datetime.timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%SZ')))
    try:
        with open(path, 'w') as fh:
            json.dump(doc, fh, indent=1)
    except OSError as exc:
        raise CX.ContextDataError(
            'the ledger %s cannot be written (%s): no result is shown '
            'before the read is on record.' % (os.path.basename(path), exc))
    return len(doc['reads'])


def main(argv=None, ledger=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('--'):
        print(__doc__)
        return 2

    def arg(k):
        i = argv.index(k) + 1 if k in argv else len(argv)
        return argv[i] if i < len(argv) else None
    stz = (arg('--stamps-tz') or 'UTC').upper()
    stp = (arg('--stamps') or 'end').lower()
    lockbox = '--lockbox' in argv
    ledger = ledger or os.path.join(HERE, HISTORY_LEDGER)
    out = arg('--out')
    if out and not W25.can_write(out):
        print('STOPPED: %s cannot be written (does the folder exist?). '
              'Nothing was read.' % out)
        return 2
    try:
        if lockbox and read_made(ledger, 'lockbox', 'NQ'):
            print('REFUSED: the lockbox weeks have been read (%s). The read '
                  'is made once.' % HISTORY_LEDGER)
            return 2
        rep = run(argv[0], lockbox, stz, stp)
        n = record_read(rep, ledger)
    except CX.ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
    print(text(rep))
    if out:
        print('\nwave-twenty-seven report -> %s' % out)
    print('read recorded (%d read(s) in %s)' % (n, HISTORY_LEDGER))
    return 0


if __name__ == '__main__':
    sys.exit(main())
