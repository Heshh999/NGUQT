#!/usr/bin/env python3
"""mrofyt_screen15.py - MROF-YT-W24-SCREEN15-1.0

MROF_YT_WAVE24_SCREEN15_REGISTRATION.md turned into running code: fifteen
ideas screened on ten years of NQ one-minute bars.

    the fifteen  O1-O5 our own, A-E public trading ideas, Q1-Q5 from
                 quantitative research (the registration, section 3)
    judged       thirteen of them: a profit after costs in each half
                 (to 2020-12-31, from 2021-01-01), also without the
                 month of the largest total, 30 trades or days at least
                 in each; long-only rules on what they add to being long
    not judged   O2 is a benchmark for step 3; O3 needs the order flow

A SCREEN on bars already read, not a test: a pass earns a look at the
recorded order flow and proves nothing. Read-only; no order is placed.

    python3 mrofyt_screen15.py "<NQ minute exports>" --out w24.json
    options: --stamps-tz UTC|ET (default UTC)  --stamps end|start
"""
import collections
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_context as CX          # noqa: E402
import mrofyt_costs as CO            # noqa: E402
import mrofyt_minutelevels as ML     # noqa: E402
import mrofyt_stretchfade as SF      # noqa: E402

W24_VERSION = 'MROF-YT-W24-SCREEN15-1.0'
REGISTRATION = 'MROF_YT_WAVE24_SCREEN15_REGISTRATION.md'

HALF_SPLIT = '20210101'
HALVES = ('H1', 'H2')
OPEN_S, CLOSE_S = int(CX.RTH_OPEN), int(CX.RTH_CLOSE)
N_MIN = (CLOSE_S - OPEN_S) // 60                       # 390
RT = CO.cost_ticks('NQ', 'TARGET') / CO.TICKS_PER_POINT        # 0.50
RT_STOP = CO.cost_ticks('NQ', 'STOP') / CO.TICKS_PER_POINT     # 0.75
SIDE = RT / 2.0                                        # one contract, one way
MIN_N = 30
CASH_DAY_BARS = 100                # a cash session, half days included
LONG_ONLY = ('O1', 'E', 'Q3')
JUDGED = ('O1', 'O4', 'O5', 'A', 'B', 'C', 'D', 'E',
          'Q1', 'Q2', 'Q3', 'Q4', 'Q5')
NAMES = collections.OrderedDict((
    ('O1', 'after selling into the close, the night rebounds'),
    ('O2', 'how far the next half hour moves (benchmark)'),
    ('O3', 'sweeps carry information (not screened)'),
    ('O4', 'the first 15 minutes decide a big overnight move'),
    ('O5', 'breakouts in busy hours, fades in quiet hours'),
    ('A', 'the 5-minute opening range breakout'),
    ('B', 'out of the noise area'),
    ('C', 'the last half hour follows the day'),
    ('D', 'the VWAP trend'),
    ('E', 'buy weakness at the close'),
    ('Q1', 'the same half hour as on earlier days'),
    ('Q2', 'a liquidity shock gives part of it back'),
    ('Q3', 'the turn of the month'),
    ('Q4', 'the day takes back the night'),
    ('Q5', 'month-end rebalancing')))


def half_of(session):
    return 'H1' if session < HALF_SPLIT else 'H2'


def sign(x):
    return (x > 0) - (x < 0)


def mean(v):
    return sum(v) / len(v)


def stdev(v):
    m = mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


# ---------------------------------------------------------------------
# registration 1: the minute grid of one session, and the daily chain
# ---------------------------------------------------------------------
class Day(object):
    """One eligible session on its front contract. c, h, l, v: 390
    one-minute bars from 09:30; vw: the VWAP after each of them (None
    until volume has traded). p(j) = the price j minutes after 09:30:
    the open for j = 0, else the close of bar j - 1."""
    __slots__ = ('session', 'contract', 'o', 'pc', 'c', 'h', 'l', 'v', 'vw')

    def __init__(self, session, contract, o, pc, c, h, lo, v):
        self.session, self.contract, self.o, self.pc = session, contract, \
            o, pc
        self.c, self.h, self.l, self.v = c, h, lo, v
        num = den = 0.0
        self.vw = []
        for k in range(len(c)):
            if v[k] > 0:
                num += (h[k] + lo[k] + c[k]) / 3.0 * v[k]
                den += v[k]
            self.vw.append(num / den if den > 0 else None)

    def p(self, j):
        return self.o if j == 0 else self.c[j - 1]

    def vwap(self, j):
        return self.vw[j - 1] if j >= 1 else None


def grid(bars, vols):
    """(open, close[390], high[390], low[390], volume[390]) from a
    session's bars (key, high, low, close, in file order) and volumes.
    The open is the close of the last bar in the hour before 09:30; a
    minute without a bar carries the last close with no range and no
    volume. None when there is no open."""
    slot = {}
    o_key, o = None, None
    for k in range(len(vols)):
        key, h, lo, c = bars[4 * k:4 * k + 4]
        if OPEN_S <= key < CLOSE_S:
            slot[int((key - OPEN_S) // 60)] = (c, h, lo, vols[k])
        elif OPEN_S - 3600 <= key < OPEN_S and (o_key is None or
                                                key > o_key):
            o_key, o = key, c
    if o is None:
        return None
    cs, hs, ls, vs = [], [], [], []
    last = o
    for m in range(N_MIN):
        b = slot.get(m)
        if b is None:
            cs.append(last), hs.append(last), ls.append(last), vs.append(0.0)
        else:
            cs.append(b[0]), hs.append(b[1]), ls.append(b[2]), vs.append(b[3])
            last = b[0]
    return o, cs, hs, ls, vs


def _weekday(session):
    return ML._date(session).weekday() < 5


def build(rd):
    """(days, order, chain) from wave twenty-two's reader.
    chain: the trading days (a weekday with a cash session of 100 bars
    or more, so a half day counts and a stray weekend bar does not) in
    time order, each dict(session, contract, close, high, low, ret,
    prev), ret being the cash close over the previous trading day's cash
    close on the same contract (None when no contract holds both).
    days: {session: Day} for the eligible sessions: the context study's
    front contract with a complete cash session and 14 earlier sessions,
    yesterday (the previous TRADING DAY) complete on the same contract,
    and an open. order: those sessions in time order."""
    by_ses = collections.defaultdict(dict)
    for (c, s), st in rd.days.items():
        by_ses[s][c] = st
    recs = CX.build_days(rd.days)
    front_of = {r['session']: r['contract'] for r in recs}
    has_history = {r['session'] for r in recs if r['eligible']}
    trading = [s for s in sorted(by_ses) if _weekday(s) and any(
        st['rth_n'] >= CASH_DAY_BARS for st in by_ses[s].values())]

    def front(s):
        if s in front_of:
            return front_of[s]
        cand = {c: st for c, st in by_ses[s].items()
                if st['rth_n'] >= CASH_DAY_BARS}
        return max(cand, key=lambda c: (cand[c]['rth_vol'], c))

    chain, prev = [], None
    for s in trading:
        f = front(s)
        st = by_ses[s][f]
        ret = None
        if prev is not None:
            for c in (f, chain[-1]['contract']):
                a, b = by_ses[prev].get(c), by_ses[s].get(c)
                if a and b and a['rth_close'] and b['rth_close'] and \
                        a['rth_n'] >= CASH_DAY_BARS and \
                        b['rth_n'] >= CASH_DAY_BARS:
                    ret = b['rth_close'] / a['rth_close'] - 1.0
                    break
        chain.append(dict(session=s, contract=f, close=st['rth_close'],
                          high=st['rth_high'], low=st['rth_low'], ret=ret,
                          prev=prev))
        prev = s
    days = {}
    for r in chain:
        s, p = r['session'], r['prev']
        if s not in has_history or p is None:
            continue
        c = front_of[s]
        st, pst = by_ses[s][c], by_ses[p].get(c)
        if pst is None or not pst['complete']:
            continue
        g = grid(st['bars'], st['vols'])
        if g is None:
            continue
        days[s] = Day(s, c, g[0], pst['rth_close'], g[1], g[2], g[3], g[4])
    return days, sorted(days), chain


def _trade(session, gross, cost, **kw):
    t = dict(session=session, gross=gross, cost=cost)
    t.update(kw)
    return t


# ---------------------------------------------------------------------
# registration 3: our own
# ---------------------------------------------------------------------
O1_HISTORY, O1_RANK = 100, 20


def rule_o1(days, order, chain):
    """After selling into the close, the night rebounds. Long-only."""
    nxt = {r['prev']: r['session'] for r in chain if r['prev']}
    xs, trades, skipped = [], [], 0
    for s in order:
        d = days[s]
        x = math.log(d.p(N_MIN) / d.p(N_MIN - 30))
        if len(xs) >= O1_HISTORY:
            thr = sorted(xs[-O1_HISTORY:])[O1_RANK - 1]
            if x <= thr:
                n = nxt.get(s)
                if n in days:
                    trades.append(_trade(s, days[n].o / days[n].pc - 1.0,
                                         RT / d.p(N_MIN), units=1))
                else:
                    skipped += 1
        xs.append(x)
    return trades, dict(skipped_next_not_eligible=skipped)


def night_returns(days, order):
    """{half: the mean night} over every eligible session: O1's bench."""
    v = collections.defaultdict(list)
    for s in order:
        v[half_of(s)].append(days[s].o / days[s].pc - 1.0)
    return {h: mean(x) for h, x in v.items()}


def session_returns(chain):
    """{half: the mean trading-day return}: the bench of E and Q3."""
    v = collections.defaultdict(list)
    for r in chain:
        if r['ret'] is not None:
            v[half_of(r['session'])].append(r['ret'])
    return {h: mean(x) for h, x in v.items()}


O2_HISTORY = 14


def bench_o2(days, order):
    """{half: dict(n, r2_f1, r2_f2)}: the share of the variance of the
    next half hour's log range explained by the time of day (F1) and by
    F1 plus today's previous surprise (F2)."""
    hist = [[] for _ in range(13)]
    rows = collections.defaultdict(list)
    for s in order:
        d = days[s]
        ys, f1s = [], []
        for k in range(13):
            a, b = 30 * k, 30 * k + 30
            rng = max(d.h[a:b]) - min(d.l[a:b])
            y = math.log(rng / d.p(a)) if rng > 0 else None
            f1 = mean(hist[k][-O2_HISTORY:]) if len(hist[k]) >= O2_HISTORY \
                else None
            ys.append(y), f1s.append(f1)
            if y is not None and f1 is not None:
                f2 = f1
                if k and ys[k - 1] is not None and f1s[k - 1] is not None:
                    f2 = f1 + ys[k - 1] - f1s[k - 1]
                rows[half_of(s)].append((y, f1, f2))
        for k in range(13):
            if ys[k] is not None:
                hist[k].append(ys[k])
    out = {}
    for h, v in rows.items():
        my = mean([r[0] for r in v])
        sst = sum((r[0] - my) ** 2 for r in v)
        out[h] = dict(n=len(v),
                      r2_f1=round(1 - sum((r[0] - r[1]) ** 2 for r in v)
                                  / sst, 4),
                      r2_f2=round(1 - sum((r[0] - r[2]) ** 2 for r in v)
                                  / sst, 4))
    return out


BIG_HISTORY = 20


def big_nights(days, order):
    """{session: g} for the sessions whose overnight move |g| is at
    least the mean |g| of the 20 previous eligible sessions."""
    gs, out = [], {}
    for s in order:
        g = math.log(days[s].o / days[s].pc)
        if len(gs) >= BIG_HISTORY and abs(g) >= mean(gs[-BIG_HISTORY:]):
            out[s] = g
        gs.append(abs(g))
    return out


def rule_o4(days, order):
    """The first 15 minutes decide a big overnight move."""
    trades = []
    for s, g in sorted(big_nights(days, order).items()):
        d = days[s]
        sg = sign(d.p(15) - d.o)
        if sg:
            trades.append(_trade(s, sg * (d.p(60) / d.p(15) - 1.0),
                                 RT / d.p(15),
                                 part='with' if sg == sign(g) else 'against'))
    return trades, {}


O5_BUSY, O5_QUIET = (30, 60, 330, 360), (150, 180, 210, 240)
O5_HISTORY, O5_K = 14, 1.5


def rule_o5(days, order):
    """Breakouts in busy hours, fades in quiet hours."""
    hist = collections.defaultdict(list)
    trades = []
    for s in order:
        d = days[s]
        for j in sorted(O5_BUSY + O5_QUIET):
            r = math.log(d.p(j) / d.p(j - 30))
            h = hist[j]
            if len(h) >= O5_HISTORY and r and \
                    abs(r) >= O5_K * mean(h[-O5_HISTORY:]):
                busy = j in O5_BUSY
                sg = sign(r) if busy else -sign(r)
                trades.append(_trade(s, sg * (d.p(j + 30) / d.p(j) - 1.0),
                                     RT / d.p(j),
                                     part='busy' if busy else 'quiet'))
            h.append(abs(r))
    return trades, {}


# ---------------------------------------------------------------------
# registration 3: public trading ideas
# ---------------------------------------------------------------------
A_TARGET_R, A_RISK, A_MAX_LEV = 10.0, 0.01, 4.0


def trade_a(d):
    """The 5-minute opening range breakout on one session, or None."""
    entry = d.p(5)
    sg = sign(entry - d.o)
    if not sg:
        return None
    stop = min(d.l[:5]) if sg > 0 else max(d.h[:5])
    risk = abs(entry - stop)
    if risk < CO.TICK:
        return None
    target = entry + sg * A_TARGET_R * risk
    ex, how = d.p(N_MIN), 'CLOSE'
    for j in range(5, N_MIN):
        if (d.l[j] <= stop) if sg > 0 else (d.h[j] >= stop):
            ex, how = stop, 'STOP'
            break
        if (d.h[j] >= target) if sg > 0 else (d.l[j] <= target):
            ex, how = target, 'TARGET'
            break
    cost = (RT_STOP if how == 'STOP' else RT) / entry
    return _trade(d.session, sg * (ex - entry) / entry, cost, how=how,
                  lev=min(A_RISK / (risk / entry), A_MAX_LEV))


def rule_a(days, order):
    trades = [t for t in (trade_a(days[s]) for s in order) if t]
    return trades, {}


B_HISTORY, B_TIMES = 14, tuple(range(30, 361, 30))
B_VOL_TARGET, B_MAX_LEV = 0.02, 4.0


def day_b(d, sigma):
    """(gross, cost, number of position changes) of the noise-area rule
    on one session, in units of the open; sigma[j] for j = 0..390."""
    hi, lo = max(d.o, d.pc), min(d.o, d.pc)
    pos, pts, cost, n = 0, 0.0, 0.0, 0
    last = None
    for j in B_TIMES + (N_MIN,):
        p = d.p(j)
        if last is not None:
            pts += pos * (p - last)
        if j == N_MIN:
            want = 0
        else:
            vw = d.vwap(j)
            ub, lb = hi * (1 + sigma[j]), lo * (1 - sigma[j])
            want = 0
            if vw is not None and p > ub and p > vw:
                want = 1
            elif vw is not None and p < lb and p < vw:
                want = -1
        if want != pos:
            cost += SIDE * abs(want - pos)
            n += 1
            pos = want
        last = p
    return pts / d.o, cost / d.o, n


def rule_b(days, order, chain):
    """Out of the noise area; one result a day, on days with a trade."""
    rets, vol = [], {}
    for r in chain:                       # s: the 14 daily returns before
        if len(rets) >= B_HISTORY:
            vol[r['session']] = stdev(rets[-B_HISTORY:])
        if r['ret'] is not None:
            rets.append(r['ret'])
    moves, trades = [], []
    for s in order:
        d = days[s]
        mv = [abs(d.p(j) / d.o - 1.0) for j in range(N_MIN + 1)]
        if len(moves) >= B_HISTORY and vol.get(s):
            sigma = [mean([m[j] for m in moves[-B_HISTORY:]])
                     for j in range(N_MIN + 1)]
            gross, cost, n = day_b(d, sigma)
            if n:
                trades.append(_trade(s, gross, cost, changes=n, lev=min(
                    B_VOL_TARGET / vol[s], B_MAX_LEV)))
        moves.append(mv)
    return trades, {}


def rule_c(days, order):
    """The last half hour follows the day."""
    trades = []
    for s in order:
        d = days[s]
        sg = sign(d.p(N_MIN - 30) - d.pc)
        if sg:
            trades.append(_trade(
                s, sg * (d.p(N_MIN) / d.p(N_MIN - 30) - 1.0),
                RT / d.p(N_MIN - 30)))
    return trades, {}


def day_d(d):
    """(gross, cost, number of position changes) of the VWAP trend on
    one session, in units of the open."""
    pos, pts, cost, n = 0, 0.0, 0.0, 0
    for j in range(1, N_MIN):
        p, vw = d.p(j), d.vwap(j)
        want = pos
        if vw is not None:
            want = 1 if p > vw else (-1 if p < vw else pos)
        if want != pos:
            cost += SIDE * abs(want - pos)
            n += 1
            pos = want
        pts += pos * (d.p(j + 1) - p)
    if pos:
        cost += SIDE * abs(pos)
        n += 1
    return pts / d.o, cost / d.o, n


def rule_d(days, order):
    trades = []
    for s in order:
        gross, cost, n = day_d(days[s])
        if n:
            trades.append(_trade(s, gross, cost, changes=n))
    return trades, {}


def _hold(chain, i, k):
    """The return of holding from the close of chain[i] to the close of
    chain[k], or None when a day in between has no return."""
    acc = 1.0
    for r in chain[i + 1:k + 1]:
        if r['ret'] is None:
            return None
        acc *= 1.0 + r['ret']
    return acc - 1.0


E_BUY, E_SELL = 0.1, 0.9


def rule_e(chain):
    """Buy weakness at the close (IBS). Long-only."""
    trades, dropped, entry = [], 0, None
    for i, r in enumerate(chain):
        if r['high'] is None or r['high'] <= r['low']:
            continue
        ibs = (r['close'] - r['low']) / (r['high'] - r['low'])
        if entry is None:
            if ibs < E_BUY:
                entry = i
        elif ibs > E_SELL:
            g = _hold(chain, entry, i)
            if g is None:
                dropped += 1
            else:
                trades.append(_trade(chain[entry]['session'], g,
                                     RT / chain[entry]['close'],
                                     units=i - entry))
            entry = None
    return trades, dict(dropped_no_return=dropped,
                        open_at_the_end=int(entry is not None))


# ---------------------------------------------------------------------
# registration 3: from quantitative research
# ---------------------------------------------------------------------
Q1_HISTORY, Q1_T = 20, 1.0


def rule_q1(days, order):
    """The same half hour as on earlier days."""
    hist = [[] for _ in range(13)]
    trades = []
    for s in order:
        d = days[s]
        for k in range(13):
            a, b = 30 * k, 30 * k + 30
            h = hist[k]
            if len(h) >= Q1_HISTORY:
                v = h[-Q1_HISTORY:]
                m, sd = mean(v), stdev(v)
                if sd > 0 and abs(m / (sd / math.sqrt(Q1_HISTORY))) >= Q1_T:
                    trades.append(_trade(
                        s, sign(m) * (d.p(b) / d.p(a) - 1.0), RT / d.p(a),
                        slot=k))
            h.append(math.log(d.p(b) / d.p(a)))
    return trades, {}


Q2_TIMES = tuple(range(15, 346, 15))
Q2_HISTORY, Q2_MOVE, Q2_VOLUME = 14, 3.0, 1.5


def rule_q2(days, order):
    """A liquidity shock gives part of it back."""
    hr, hv = collections.defaultdict(list), collections.defaultdict(list)
    trades = []
    for s in order:
        d = days[s]
        free = 0
        for j in Q2_TIMES:
            r = math.log(d.p(j) / d.p(j - 15))
            vol = sum(d.v[j - 15:j])
            if len(hr[j]) >= Q2_HISTORY:
                m = mean(hr[j][-Q2_HISTORY:])
                vb = mean(hv[j][-Q2_HISTORY:])
                if j >= free and r and m > 0 and vb > 0 and \
                        abs(r) >= Q2_MOVE * m and vol / vb >= Q2_VOLUME:
                    trades.append(_trade(
                        s, -sign(r) * (d.p(j + 30) / d.p(j) - 1.0),
                        RT / d.p(j), at=j))
                    free = j + 30
            hr[j].append(abs(r))
            hv[j].append(vol)
    return trades, {}


def _months(chain):
    """[(yyyymm, [index in chain])] in time order."""
    out = collections.OrderedDict()
    for i, r in enumerate(chain):
        out.setdefault(r['session'][:6], []).append(i)
    return list(out.items())


def rule_q3(chain):
    """The turn of the month. Long-only."""
    ms = _months(chain)
    trades, dropped = [], 0
    for (_m, idx), (_m2, nxt) in zip(ms, ms[1:]):
        if len(idx) < 2 or len(nxt) < 3:
            continue
        i, k = idx[-2], nxt[2]
        g = _hold(chain, i, k)
        if g is None:
            dropped += 1
            continue
        trades.append(_trade(chain[i]['session'], g, RT / chain[i]['close'],
                             units=k - i))
    return trades, dict(dropped_no_return=dropped)


def rule_q4(days, order):
    """The day takes back the night."""
    trades = []
    for s, g in sorted(big_nights(days, order).items()):
        d = days[s]
        sg = -sign(g)
        if sg:
            trades.append(_trade(s, sg * (d.p(N_MIN) / d.o - 1.0), RT / d.o,
                                 to_1030=sg * (d.p(60) / d.o - 1.0)))
    return trades, {}


def rule_q5(chain):
    """Month-end rebalancing: against the month so far, over the last
    three trading days."""
    ms = _months(chain)
    trades, dropped = [], 0
    for n in range(1, len(ms) - 1):       # a month before and one after
        idx = ms[n][1]
        if len(idx) < 5:
            continue
        e = idx[-4]
        mtd = _hold(chain, ms[n - 1][1][-1], e)
        g = _hold(chain, e, idx[-1])
        if mtd is None or g is None:
            dropped += 1
            continue
        if mtd:
            trades.append(_trade(chain[e]['session'], -sign(mtd) * g,
                                 RT / chain[e]['close']))
    return trades, dict(dropped_no_return=dropped)


# ---------------------------------------------------------------------
# registration 2: the pass bar
# ---------------------------------------------------------------------
def nets(rule, trades, bench):
    """[(session, net basis points)]: gross minus cost, in the source's
    sizing for A and B, minus the half's average holding for the
    long-only rules."""
    out = []
    for t in trades:
        x = t['gross'] - t['cost']
        if rule in ('A', 'B'):
            x *= t['lev']
        if rule in LONG_ONLY:
            x -= bench[half_of(t['session'])] * t['units']
        out.append((t['session'], 1e4 * x))
    return out


def judge(pairs):
    """pairs: [(session, net)]. The screen's verdict."""
    out = dict(halves={})
    ok = True
    for h in HALVES:
        v = [(s[:6], x) for s, x in pairs if half_of(s) == h]
        r = dict(n=len(v))
        if v:
            by = collections.defaultdict(float)
            for m, x in v:
                by[m] += x
            best = max(by, key=lambda m: (by[m], m))
            rest = [x for m, x in v if m != best]
            r.update(net=round(mean([x for _m, x in v]), 3),
                     won=round(sum(1 for _m, x in v if x > 0) / len(v), 4),
                     best_month=best,
                     net_without_best=round(mean(rest), 3) if rest else None)
        r['ok'] = bool(r['n'] >= MIN_N and r['net'] > 0 and
                       r['net_without_best'] is not None and
                       r['net_without_best'] > 0)
        ok = ok and r['ok']
        out['halves'][h] = r
    mv = ML.month_verdict([(s[:6], x) for s, x in pairs], MIN_N) \
        if pairs else dict(n=0)
    out['both'] = dict(n=mv.get('n', 0), net=mv.get('net_points'),
                       ci95=mv.get('ci95'), t=mv.get('t'), p=mv.get('p'))
    ci = mv.get('ci95')
    out['status'] = 'PASS' if ok else 'FAIL'
    out['strong'] = bool(ok and ci and ci[0] > 0)
    return out


def _beside(rule, trades):
    """The registration's "beside" lines: plain means, never judged."""
    out = {}
    if rule in ('A', 'B'):
        out['unsized'] = judge([(t['session'], 1e4 * (t['gross'] - t['cost']))
                                for t in trades])
    for key in ('part',):
        parts = sorted({t[key] for t in trades if key in t})
        for p in parts:
            v = [1e4 * (t['gross'] - t['cost']) for t in trades
                 if t.get(key) == p]
            out[p] = dict(n=len(v), net=round(mean(v), 3))
    if rule == 'Q4':
        v = [1e4 * (t['to_1030'] - t['cost']) for t in trades]
        out['out_at_1030'] = dict(n=len(v), net=round(mean(v), 3)) if v \
            else dict(n=0)
    if rule in LONG_ONLY:
        v = [1e4 * (t['gross'] - t['cost']) for t in trades]
        out['before_the_bench'] = dict(n=len(v), net=round(mean(v), 3)) \
            if v else dict(n=0)
    gross = [1e4 * t['gross'] for t in trades]
    out['before_costs'] = round(mean(gross), 3) if gross else None
    return out


def screen(days, order, chain):
    night, sess = night_returns(days, order), session_returns(chain)
    runs = collections.OrderedDict((
        ('O1', lambda: rule_o1(days, order, chain)),
        ('O4', lambda: rule_o4(days, order)),
        ('O5', lambda: rule_o5(days, order)),
        ('A', lambda: rule_a(days, order)),
        ('B', lambda: rule_b(days, order, chain)),
        ('C', lambda: rule_c(days, order)),
        ('D', lambda: rule_d(days, order)),
        ('E', lambda: rule_e(chain)),
        ('Q1', lambda: rule_q1(days, order)),
        ('Q2', lambda: rule_q2(days, order)),
        ('Q3', lambda: rule_q3(chain)),
        ('Q4', lambda: rule_q4(days, order)),
        ('Q5', lambda: rule_q5(chain))))
    rules = collections.OrderedDict()
    for rule, fn in runs.items():
        trades, notes = fn()
        bench = night if rule == 'O1' else sess
        res = judge(nets(rule, trades, bench))
        res.update(rule=rule, name=NAMES[rule], notes=notes,
                   beside=_beside(rule, trades),
                   unit='bp of capital, the source\'s sizing'
                   if rule in ('A', 'B') else (
                       'bp over being long anyway' if rule in LONG_ONLY
                       else 'bp of the entry price'))
        rules[rule] = res
    return dict(rules=rules, benchmark_o2=bench_o2(days, order),
                bench=dict(mean_night_bp={h: round(1e4 * x, 3)
                                          for h, x in night.items()},
                           mean_session_bp={h: round(1e4 * x, 3)
                                            for h, x in sess.items()}))


def read(path, stamps_tz='UTC', stamps='end'):
    """Wave twenty-two's reader over the exports, the stamps checked."""
    rd = SF.VolReader('NQ', stamps_tz, stamps, None)
    rd.read_path(path)
    if not rd.days:
        raise CX.ContextDataError(CX._nothing_read(
            rd, 'NQ', 'before 2026-07-01'))
    return rd, rd.check_stamps()


def run(path, stamps_tz='UTC', stamps='end'):
    rd, chk = read(path, stamps_tz, stamps)
    days, order, chain = build(rd)
    if len(order) < 200:
        raise CX.ContextDataError(
            'only %d usable sessions: the screen needs years of minute '
            'bars. Nothing was computed.' % len(order))
    rep = dict(wave24=W24_VERSION, registration=REGISTRATION,
               files=len(rd.files), stamp_check=chk,
               sessions=len(order), first_session=order[0],
               last_session=order[-1], trading_days=len(chain),
               half_split=HALF_SPLIT, min_n=MIN_N,
               costs=dict(round_trip=RT, stop=RT_STOP, side=SIDE))
    rep.update(screen(days, order, chain))
    rep['passed'] = [r for r, v in rep['rules'].items()
                     if v['status'] == 'PASS']
    return rep


def text(rep):
    L = ['%s  fifteen ideas on %d sessions (%s .. %s)' % (
        rep['wave24'], rep['sessions'], rep['first_session'],
        rep['last_session']),
        'A SCREEN on bars already read, not a test. Halves: to 2020-12-31 '
        '(H1), from 2021-01-01 (H2).',
        'The bar: in each half 30+ trades, a profit after costs, and still '
        'one without its best month.', '']
    for rule, v in rep['rules'].items():
        L.append('%-3s %s   [%s]' % (rule, v['name'], v['unit']))
        for h in HALVES:
            r = v['halves'][h]
            if r['n']:
                L.append('    %s  n %5d  won %2.0f%%  net %+8.2f  without '
                         '%s %+8.2f  %s' % (
                             h, r['n'], 100 * r['won'], r['net'],
                             r['best_month'], r['net_without_best'] or 0.0,
                             'ok' if r['ok'] else 'no'))
            else:
                L.append('    %s  n     0' % h)
        b = v['both']
        ci = b.get('ci95')
        L.append('    both n %5d  net %s  95%% range %s' % (
            b['n'], '%+.2f' % b['net'] if b.get('net') is not None else '-',
            '%+.2f .. %+.2f' % tuple(ci) if ci else '-'))
        L.append('    %s%s' % (v['status'],
                               ' (strong)' if v['strong'] else ''))
        bs = v['beside']
        extra = ['before costs %+.2f' % bs['before_costs']
                 if bs.get('before_costs') is not None else '']
        for k, x in bs.items():
            if k in ('before_costs',):
                continue
            if k == 'unsized':
                extra.append('unsized: H1 %s, H2 %s' % tuple(
                    '%+.2f' % x['halves'][h]['net']
                    if x['halves'][h]['n'] else '-' for h in HALVES))
            elif x.get('n'):
                extra.append('%s: n %d, net %+.2f' % (k, x['n'], x['net']))
        L.append('    beside: ' + '; '.join(e for e in extra if e))
        if v['notes']:
            L.append('    notes: %s' % json.dumps(v['notes'], sort_keys=True))
        L.append('')
    L.append('O2  benchmark: share of the variance of the next half hour\'s '
             'range explained')
    for h in HALVES:
        b = rep['benchmark_o2'].get(h)
        if b:
            L.append('    %s  n %d  time of day alone %.1f%%  with today\'s '
                     'last surprise %.1f%%' % (h, b['n'], 100 * b['r2_f1'],
                                                100 * b['r2_f2']))
    L.append('O3  not screened: it needs the order flow.')
    L.append('')
    L.append('PASSED THE SCREEN: %s' % (', '.join(rep['passed']) or 'none'))
    L.append('Minute bars, costs charged; not P&L. No order was placed.')
    return '\n'.join(L)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('--'):
        print(__doc__)
        return 2

    def arg(k):
        return argv[argv.index(k) + 1] if k in argv else None
    try:
        rep = run(argv[0], (arg('--stamps-tz') or 'UTC').upper(),
                  (arg('--stamps') or 'end').lower())
    except CX.ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    print(text(rep))
    out = arg('--out')
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
        print('\nwave-twenty-four report -> %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
