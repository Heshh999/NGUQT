#!/usr/bin/env python3
# MROF-YT-W30-CLOCKS-1.0 suite. B at any clock against wave twenty-four's
# own day_b and rule_b, the three changes on a day worked out by hand,
# the timed fill's edges, the fast give-back by hand, the paired and
# pooled statistics, and the reads, the verdicts and the ledger end to
# end on synthetic NinjaTrader-format exports. Synthetic data verifies
# CODE BEHAVIOR only, never market evidence. No order, fill or P&L
# exists.
import datetime as _dt
import io
import json
import math
import os
import random
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_clocks30 as C          # noqa: E402
import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_improve26 as W26       # noqa: E402
import mrofyt_screen15 as S          # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


def near(a, b, tol=1e-9):
    return a is not None and abs(a - b) <= tol


def said_by(fn):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = fn()
    return rc, buf.getvalue()


WORK = tempfile.mkdtemp(prefix='mrofyt_w30_')
N = S.N_MIN
D = _dt.date
REG = ' '.join(open(os.path.join(HERE, C.REGISTRATION),
                    encoding='utf-8').read().split())


def mk(session, o, pc, closes):
    c = list(closes) + [closes[-1]] * (N - len(closes))
    return S.Day(session, 'NQ 12-21', o, pc, c, list(c), list(c), [1.0] * N)


def flat(session, o, pc, marks):
    """A session whose price is `o` until a mark {minute: price} moves
    it; highs and lows are the closes, every minute has volume 1."""
    c, last = [], o
    for j in range(1, N + 1):
        last = marks.get(j, last)
        c.append(last)
    return mk(session, o, pc, c)


EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def to_utc(local_epoch):
    y = _dt.datetime.fromtimestamp(local_epoch, _dt.timezone.utc).year
    for off in (4, 5):
        u_ = local_epoch + off * 3600
        w = CX._dst_window(y)
        if (off == 4) == (w[0] <= u_ < w[1]):
            return u_
    return local_epoch + 5 * 3600


def stamp(d, minute):
    loc = int((_dt.datetime(d.year, d.month, d.day, tzinfo=_dt.timezone.utc)
               - EPOCH).total_seconds()) + minute * 60
    return _dt.datetime.fromtimestamp(to_utc(loc) + 60, _dt.timezone.utc
                                      ).strftime('%Y%m%d %H%M%S')


def snap(x, tick):
    return round(round(x / tick) * tick, 2)


def make_rows(first, last, seed, tick=0.25, px0=10000.0, sd=2.0, drift=0.0,
              share=1.0):
    """[(date, row)]: every weekday from `first` to `last` has bars
    08:30-16:14 ET, a random walk on the tick that opens a little back
    toward px0; on a `share` of the days the price drifts `drift` points
    a minute from 09:35 to 16:00 in the direction of the first five
    minutes; one stray bar on every Saturday and Sunday."""
    rng = random.Random(seed)
    px = pc = px0
    out, d = [], first
    while d <= last:
        if d.weekday() >= 5:
            out.append((d, '%s;%.2f;%.2f;%.2f;%.2f;1' % (
                stamp(d, 11 * 60), px, px, px, px)))
        else:
            px = snap(pc + 0.1 * (px0 - pc) + rng.gauss(0, 10.0 * sd), tick)
            on = rng.random() < share
            side, o930 = 0, px
            for m in range(8 * 60 + 30, 16 * 60 + 15):
                if m == 9 * 60 + 30:
                    o930 = px
                if m == 9 * 60 + 35 and on:
                    side = (px > o930) - (px < o930)
                step = rng.gauss(0, sd)
                if 9 * 60 + 35 <= m < 16 * 60:
                    step += side * drift
                o = px
                px = snap(px + step, tick)
                h, lo = max(o, px) + tick, min(o, px) - tick
                v = 50 if m < 9 * 60 + 30 else (3000 if m == 9 * 60 + 30
                                                else 900)
                out.append((d, '%s;%.2f;%.2f;%.2f;%.2f;%d' % (
                    stamp(d, m), o, h, lo, px, v)))
                if m == 15 * 60 + 59:
                    pc = px
        d += _dt.timedelta(days=1)
    return out


def write(folder, name, rows):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), 'w') as fh:
        fh.write('\n'.join(r for _d, r in rows) + '\n')
    return folder


# ---------------------------------------------------------------------
# the synthetic exports
# ---------------------------------------------------------------------
R1 = make_rows(D(2020, 3, 2), D(2021, 10, 22), 11, drift=0.6, share=0.5)
FN = write(os.path.join(WORK, 'nq'), 'NQ 12-21.Last.txt', R1)
FE = write(os.path.join(WORK, 'es'), 'ES 12-21.Last.txt', R1)
R5 = make_rows(D(2020, 3, 2), D(2021, 10, 22), 7, tick=0.1, px0=2000.0,
               sd=0.4, drift=0.12, share=0.5)
FR = write(os.path.join(WORK, 'rty'), 'RTY 12-21.Last.txt', R5)
rdN, _chk = S.read(FN)
dN, oN, cN = S.build(rdN)
biN = W26.b_inputs(dN, oN, cN)

# ---------------------------------------------------------------------
# C1: on its own clock, with no timed fill, this is wave twenty-four's B
# ---------------------------------------------------------------------
KEYS = ('session', 'gross', 'cost', 'changes', 'lev')


def same(a, b):
    return [tuple(x[k] for k in KEYS) for x in a] == \
        [tuple(x[k] for k in KEYS) for x in b]


mine_nq, own_nq = C.rule(dN, oN, biN, C.CLOCKS['B']), S.rule_b(dN, oN, cN)[0]
with W25.costs('RTY'):
    mine_r = C.rule(dN, oN, biN, C.CLOCKS['B'])
    own_r = S.rule_b(dN, oN, cN)[0]
days_same = all(C.day(dN[s], biN[s][0], S.B_TIMES)[:3] ==
                S.day_b(dN[s], biN[s][0]) for s in oN if s in biN)
t('C1: on B\'s own minutes and with no timed fill, day() is wave '
  'twenty-four\'s day_b to the last digit on every session, and rule() is '
  'its rule_b trade for trade, under NQ\'s costs and under another '
  'market\'s; nothing is moved',
  len(own_nq) >= 150 and same(mine_nq, own_nq) and same(mine_r, own_r) and
  days_same and C.CLOCKS['B'] == S.B_TIMES and
  all(x['late'] == 0 for x in mine_nq) and
  any(x['changes'] > 2 for x in mine_nq))

# ---------------------------------------------------------------------
# C2: one day by hand: B, the two other clocks, the fast clock and the
# timed fills
# ---------------------------------------------------------------------
# minute:  1-34  35-45  46-50  51-55  56-61  62-195  196-200  201-205
# price:   1000  1004   1005   1006   1008   1007    1005     1003
# then 206-212: 1001, from 213: 1001.5. Bounds 1002 and 998.
MARKS = {35: 1004.0, 46: 1005.0, 51: 1006.0, 56: 1008.0, 62: 1007.0,
         196: 1005.0, 201: 1003.0, 206: 1001.0, 213: 1001.5}
d2 = flat('20210104', 1000.0, 1000.0, MARKS)
sg2 = [0.002] * (N + 1)
vw200 = (34 * 1000 + 11 * 1004 + 5 * 1005 + 5 * 1006 + 6 * 1008 +
         134 * 1007 + 5 * 1005) / 200.0
got2 = {k: C.day(d2, sg2, v) for k, v in C.CLOCKS.items()}
bt2 = C.day(d2, sg2, C.CLOCKS['B'], 3, 5)


def pts(x):
    return (x / 1000.0, 2 * 0.25 / 1000.0)


t('C2a: B buys at 10:30 (1008) and sells at 13:00 (1001); ten minutes '
  'later the same rule buys at 10:10 (1004) and sells at 13:10 (1001.5); '
  'twenty minutes later it buys at 10:20 (1005) and is out at 12:50, '
  'when price (1005) is under VWAP (1005.55); every ten minutes it buys '
  'at 10:10 and is out at 12:50',
  near(d2.vwap(200), vw200) and near(vw200, 1005.55) and
  near(d2.vwap(40), 1000.6) and
  all(near(a, b, 1e-12) for a, b in zip(got2['B'][:2], pts(-7.0))) and
  got2['B'][2:] == (2, 0) and
  all(near(a, b, 1e-12) for a, b in zip(got2['B+10'][:2], pts(-2.5))) and
  all(near(a, b, 1e-12) for a, b in zip(got2['B+20'][:2], pts(0.0))) and
  all(near(a, b, 1e-12) for a, b in zip(got2['BF'][:2], pts(1.0))) and
  got2['BF'][2:] == (2, 0) and got2['B+20'][2] == 2 and
  C.CLOCKS['B+10'][0] == 40 and C.CLOCKS['B+10'][-1] == 370 and
  C.CLOCKS['B+20'][0] == 50 and C.CLOCKS['B+20'][-1] == 380 and
  C.CLOCKS['BF'] == tuple(range(30, 381, 10)) and
  [len(v) for v in C.CLOCKS.values()] == [12, 12, 12, 36])
t('C2b: with timed fills B\'s decisions are the same, but the buy at '
  '10:30 comes after three changes up (+1, +1, +2) and is filled at 10:35 '
  '(1007), and the sell at 13:00 after three changes down (-2, -2, -2) '
  'and is filled at 13:05 (1001.5): 5.5 points lost instead of 7, the '
  'same two orders, the same cost',
  [C.change(d2, m) for m in (50, 55, 60)] == [1.0, 1.0, 2.0] and
  [C.change(d2, m) for m in (200, 205, 210)] == [-2.0, -2.0, -2.0] and
  C.ran(d2, 60, 3) == 1 and C.ran(d2, 210, 3) == -1 and
  all(near(a, b, 1e-12) for a, b in zip(bt2[:2], pts(-5.5))) and
  bt2[2:] == (2, 2) and bt2[1] == got2['B'][1])

# ---------------------------------------------------------------------
# C3: the timed fill's edges
# ---------------------------------------------------------------------
# a buy after two changes up and one flat; a buy at 10:30 at 1010, above
# the bound and above VWAP (1005.25), after three changes down from 1020
flat_then_up = flat('20210105', 1000.0, 1000.0,
                    {46: 1004.0, 51: 1004.0, 56: 1006.0, 66: 1009.0})
down_then_buy = flat('20210106', 1000.0, 1000.0,
                     {40: 1020.0, 46: 1016.0, 51: 1013.0, 56: 1010.0})
e_flat = C.day(flat_then_up, sg2, C.CLOCKS['B'], 3, 5)
e_down = C.day(down_then_buy, sg2, C.CLOCKS['B'], 3, 5)
# the last decision of the day and the flat at the close
late_buy = flat('20210107', 1000.0, 1000.0,
                {346: 1003.0, 351: 1004.0, 356: 1005.0, 365: 1006.0,
                 376: 1007.0, 381: 1008.0, 386: 1009.0})
e_late = C.day(late_buy, sg2, C.CLOCKS['B'], 3, 5)
e_late10 = C.day(late_buy, sg2, C.CLOCKS['B'], 3, 10)
try:
    C.day(d2, sg2, C.CLOCKS['BF'], 3, 10)
    too_fast = False
except ValueError:
    too_fast = True
t('C3: a change of zero breaks the run and a run against the order does '
  'not move it; the order at 15:30 is moved to 15:35 like any other, the '
  'flat at 16:00 never, though three changes ran with it; a clock too '
  'fast for the wait is refused; ran() is 0 without a run',
  C.ran(flat_then_up, 60, 3) == 0 and C.ran(flat_then_up, 60, 1) == 1 and
  e_flat[3] == 0 and near(e_flat[0], (1009.0 - 1006.0) / 1000.0, 1e-12) and
  C.ran(down_then_buy, 60, 3) == -1 and e_down[3] == 0 and
  near(down_then_buy.vwap(60), 1005.25) and
  near(e_down[0], 0.0, 1e-12) and e_down[2] == 2 and
  C.ran(late_buy, 360, 3) == 1 and e_late[3] == 1 and
  near(e_late[0], (1009.0 - 1006.0) / 1000.0, 1e-12) and
  C.ran(late_buy, 390, 3) == 1 and e_late[2] == 2 and
  e_late10[3] == 1 and
  near(e_late10[0], (1009.0 - 1006.0) / 1000.0, 1e-12) and too_fast and
  C.ran(d2, 30, 3) == 0)

# ---------------------------------------------------------------------
# C4: the fast give-back, by hand
# ---------------------------------------------------------------------
g4 = flat('20210108', 1000.0, 1000.0,
          {5: 1001.0, 10: 1002.0, 15: 1003.0, 20: 1001.0, 205: 999.0,
           210: 998.0, 215: 997.0, 220: 996.0})
days4 = {'20210108': g4}
gb3 = C.give_back(days4, ['20210108'], 3)
gb2 = C.give_back(days4, ['20210108'], 2)
gb4 = C.give_back(days4, ['20210108'], 4)
t('C4: after three changes up to 09:45 the next gives back 2 points; '
  'after three down to 13:05 the next goes on 1 more (-1), and after the '
  'three to 13:10 nothing: three events in 74 marks, a third of a point '
  'on average, less the round trip; two in a row has four events, four '
  'in a row one, from its first mark at 09:50',
  gb3['marks'] == 74 and gb3['events'] == 3 and
  near(gb3['points'], round(1.0 / 3.0, 4)) and
  near(gb3['bp'], round(1e4 * (2 / 1003.0 - 1 / 997.0) / 3.0, 4)) and
  near(gb3['after_round_trip'], round(1.0 / 3.0 - 0.5, 4)) and
  gb3['share'] == round(3 / 74.0, 4) and
  gb3['halves']['H2']['n'] == 3 and gb3['halves']['H1']['n'] == 0 and
  gb2['events'] == 4 and near(gb2['points'], 0.0) and gb2['marks'] == 74
  and gb4['events'] == 1 and gb4['marks'] == 73 and
  near(gb4['points'], 0.0) and
  C.give_back(days4, [], 3)['events'] == 0 and
  (C.GIVE_FROM, C.GIVE_TO, C.GIVE_STREAKS) == (15, 380, (2, 3, 4)))

# ---------------------------------------------------------------------
# C5: a session's result, the paired difference, the pooled statistic
# ---------------------------------------------------------------------
tr5 = [S._trade('20210104', 0.0010, 0.0002, lev=2.0, changes=2, late=0),
       S._trade('20210111', -0.0004, 0.0001, lev=4.0, changes=2, late=1)]
x5 = C.session_x(['20210104', '20210105', '20210111'], tr5)
p5 = C.paired([('20210104', 3.0), ('20210105', -1.0), ('20210111', 0.5)],
              [('20210104', 1.0), ('20210105', -1.0), ('20210111', 2.0)])
MON = ['20210104', '20210111', '20210118', '20210125']


def fake(market, status=None, d=None, eligible=None, later=None):
    """A market report as decide() reads it."""
    status = status or {}
    r = dict(wave30=C.W30_VERSION, part='market', market=market,
             eligible=list(eligible or MON), rules={}, paired={})
    for name in C.NAMES:
        r['rules'][name] = dict(status=status.get(name, 'PASS'))
    for name in C.CHANGES:
        ser = (d or {}).get(name, {})
        vals = [ser.get(s, 0.0) for s in r['eligible']]
        r['paired'][name] = dict(mean=sum(vals) / len(vals), series=ser)
    return r


es5 = fake('ES', d=dict(BT=dict(zip(MON, (2.0, 4.0, 2.0, 4.0)))))
rty5 = fake('RTY', eligible=MON[:3],
            d=dict(BT={MON[0]: 4.0, MON[1]: 2.0}))
pool5 = C.pooled([es5, rty5], 'BT')
sd5 = math.sqrt(((0.25) ** 2 * 2 + 1.75 ** 2 + 1.25 ** 2) / 3.0)
t('C5: a session\'s result is its net basis points in B\'s sizing, 0 '
  'without a trade; the paired difference is the change minus B, session '
  'by session; over two markets a session counts the average of the '
  'markets that have it, and t is of the weekly sums',
  x5[1] == ('20210105', 0.0) and near(x5[0][1], 1e4 * 0.0008 * 2.0) and
  near(x5[2][1], 1e4 * -0.0005 * 4.0) and
  p5 == [('20210104', 2.0), ('20210105', 0.0), ('20210111', -1.5)] and
  pool5 == [(MON[0], 3.0), (MON[1], 3.0), (MON[2], 1.0), (MON[3], 4.0)] and
  near(C.W28.stats(pool5)['t'], 2.75 / (sd5 / 2.0)) and
  near(C.W28.stats(pool5)['mean'], 2.75) and
  C._stats(p5)['differ'] == 2 and C._stats(p5)['sessions'] == 3)

# ---------------------------------------------------------------------
# C6: one market's report against the pieces
# ---------------------------------------------------------------------
with W25.costs('NQ'):
    res6 = C.judge_all(dN, oN, cN)
    ref6 = S.screen(dN, oN, cN)['rules']['B']
ses6 = [s for s in oN if s in biN]
xb6 = C.session_x(ses6, C.rule(dN, oN, biN, C.CLOCKS['B']))
xt6 = C.session_x(ses6, C.rule(dN, oN, biN, C.CLOCKS['B'], 3, 5))
x10 = C.session_x(ses6, C.rule(dN, oN, biN, C.CLOCKS['B+10']))
x20 = C.session_x(ses6, C.rule(dN, oN, biN, C.CLOCKS['B+20']))
d6 = C.paired(xt6, xb6)
three6 = [(a + b + c) / 3.0 for (_s, a), (_t, b), (_u, c) in
          zip(xb6, x10, x20)]
t('C6: in a market\'s report B is wave twenty-four\'s own verdict; BT '
  'makes B\'s orders and pays B\'s costs and only its fills differ; a '
  'faster clock makes more orders; the paired figures, the three clocks '
  'together and the lines beside are the pieces\' own',
  res6['rules']['B']['halves'] == ref6['halves'] and
  res6['rules']['B']['status'] == ref6['status'] and
  list(res6['rules']) == ['B', 'B+10', 'B+20', 'BF', 'BT'] and
  res6['eligible'] == ses6 and len(ses6) > 300 and
  res6['rules']['BT']['changes_a_day'] ==
  res6['rules']['B']['changes_a_day'] and
  res6['rules']['BT']['cost_a_day_bp'] ==
  res6['rules']['B']['cost_a_day_bp'] and
  res6['rules']['BT']['moved'] > 50 and res6['rules']['B']['moved'] == 0
  and res6['rules']['BF']['changes_a_day'] >
  res6['rules']['B']['changes_a_day'] and
  near(res6['rules']['B']['per_session'],
       round(sum(x for _s, x in xb6) / len(ses6), 4)) and
  res6['paired']['BT']['mean'] == round(S.mean([x for _s, x in d6]), 5)
  and res6['paired']['BT']['differ'] == len(res6['paired']['BT']['series'])
  and res6['paired']['BT']['differ'] == sum(1 for _s, x in d6 if x) and
  near(res6['three_clocks']['mean'], round(S.mean(three6), 4)) and
  near(res6['three_clocks']['sd'], round(S.stdev(three6), 4)) and
  res6['three_clocks']['sd'] <= res6['three_clocks']['b_sd'] and
  list(res6['beside']) == ['BF15', 'BF5', 'BT2', 'BT4', 'BT10'] and
  res6['beside']['BF5']['changes_a_day'] >
  res6['rules']['BF']['changes_a_day'] and
  res6['beside']['BT2']['moved'] > res6['rules']['BT']['moved'] >
  res6['beside']['BT4']['moved'] and
  list(res6['give_back']) == ['2', '3', '4'] and
  res6['give_back']['3']['events'] > 1000)

# ---------------------------------------------------------------------
# C6b: every rule against a slow second implementation
# ---------------------------------------------------------------------
def slow_day(d, sigma, times, streak, wait):
    """The same day written another way: first every order (when it is
    decided, when it is filled), then the position minute by minute."""
    hi, lo = max(d.o, d.pc), min(d.o, d.pc)
    orders, pos, moved = [], 0, 0
    for j in times:
        p, vw = d.p(j), d.vwap(j)
        want = 0
        if vw is not None and p > hi * (1 + sigma[j]) and p > vw:
            want = 1
        elif vw is not None and p < lo * (1 - sigma[j]) and p < vw:
            want = -1
        if want == pos:
            continue
        side = 1 if want > pos else -1
        at = j
        if streak and j + wait < N and all(
                (d.p(j - 5 * k) - d.p(j - 5 * k - 5)) * side > 0
                for k in range(streak)):
            at, moved = j + wait, moved + 1
        orders.append((at, pos, want))
        pos = want
    if pos:
        orders.append((N, pos, 0))
    held, gross = 0, 0.0
    for m in range(N):
        for at, _was, new in orders:
            if at == m:
                held = new
        gross += held * (d.p(m + 1) - d.p(m))
    cost = sum(0.25 * abs(new - was) for _at, was, new in orders)
    return gross / d.o, cost / d.o, len(orders), moved


VARIANTS = [(v, 0, 5) for v in C.CLOCKS.values()] + \
    [(C.CLOCKS['B'], 3, 5)] + [v[1:] for v in C.BESIDE.values()]
worst, n_cmp, n_moved = 0.0, 0, 0
for s_ in ses6:
    for times_, streak_, wait_ in VARIANTS:
        a = C.day(dN[s_], biN[s_][0], times_, streak_, wait_)
        b = slow_day(dN[s_], biN[s_][0], times_, streak_, wait_)
        worst = max(worst, abs(a[0] - b[0]), abs(a[1] - b[1]),
                    abs(a[2] - b[2]), abs(a[3] - b[3]))
        n_cmp += 1
        n_moved += a[3]
t('C6b: on every session of the synthetic export, each of the ten rules '
  '(four clocks, the timed fills, and the five reported beside) gives '
  'the result, the cost, the orders and the moved fills of a slow second '
  'implementation that first lists every order and then holds the '
  'position minute by minute',
  n_cmp == 10 * len(ses6) and worst < 1e-12 and n_moved > 500)

# ---------------------------------------------------------------------
# C7: the reads, the verdict and the ledger
# ---------------------------------------------------------------------
led = os.path.join(WORK, 'ledger.json')
outs = {m: os.path.join(WORK, 'w30_%s.json' % m) for m in C.MARKETS}
rcN, saidN = said_by(lambda: C.main([FN, '--market', 'NQ', '--out',
                                     outs['NQ']], ledger=led))
rcE, saidE = said_by(lambda: C.main([FE, '--market', 'ES', '--out',
                                     outs['ES']], ledger=led))
rcR, saidR = said_by(lambda: C.main([FR, '--market', 'RTY', '--out',
                                     outs['RTY']], ledger=led))
rcE2, saidE2 = said_by(lambda: C.main([FE, '--market', 'ES'], ledger=led))
reps = {m: json.load(open(outs[m])) for m in C.MARKETS}
rcD, saidD = said_by(lambda: C.main(['--decide'] + [outs[m] for m in
                                                    C.MARKETS]))
rcD2, saidD2 = said_by(lambda: C.main(['--decide', outs['NQ']]))
R2 = make_rows(D(2025, 6, 2), D(2026, 11, 20), 5, drift=0.6, share=0.5)
FL = write(os.path.join(WORK, 'later'), 'NQ 12-26.Last.txt', R2)
outL = os.path.join(WORK, 'w30_later.json')
rcL, saidL = said_by(lambda: C.main([FL, '--later-months', '--out', outL],
                                    ledger=led))
rcL2, saidL2 = said_by(lambda: C.main([FL, '--later-months'], ledger=led))
rcD3, saidD3 = said_by(lambda: C.main(['--decide'] + [outs[m] for m in
                                                      C.MARKETS] + [outL]))
rcU, saidU = said_by(lambda: C.main([FN, '--market', 'YM'], ledger=led))
rcU2, saidU2 = said_by(lambda: C.main([FN], ledger=led))
rcW, saidW = said_by(lambda: C.main(
    [FN, '--market', 'NQ', '--out', os.path.join(WORK, 'no', 'x.json')],
    ledger=os.path.join(WORK, 'other_ledger.json')))
ledr = json.load(open(led))['reads']
repL = json.load(open(outL))
t('C7: NQ, ES and RTY are each read once and recorded before anything is '
  'shown; the report\'s B is the same as from the pieces; the verdict '
  'needs all three markets and takes the later months when given; the '
  'later months are read once, to 2026-11-13; every setting is put back',
  rcN == rcE == rcR == 0 and rcE2 == 2 and 'REFUSED' in saidE2 and
  reps['NQ']['rules'] == json.loads(json.dumps(res6['rules'])) and
  reps['NQ']['paired'] == json.loads(json.dumps(res6['paired'])) and
  reps['RTY']['costs'] == dict(tick=0.1, round_trip=0.2, stop=0.3) and
  reps['RTY']['rules']['B']['status'] in ('PASS', 'FAIL') and
  'The fast give-back' in saidN and 'Against B, session by session'
  in saidN and 'read recorded (1 read(s)' in saidN and
  rcD == 0 and 'THE CLOCK (BS):' in saidD and 'GOES ON:' in saidD and
  'The later months are still to be read' in saidD and
  rcD2 == 2 and 'are needed' in saidD2 and
  rcL == 0 and '*** LATER MONTHS' in saidL and rcL2 == 2 and
  'REFUSED' in saidL2 and list(repL['rules']) ==
  ['B+10', 'B+20', 'BF', 'BT'] and repL['last_session'] == '20261113' and
  all(v['status'] in ('IN LINE', 'WEAK', 'COLLAPSED', 'TOO FEW')
      for v in repL['rules'].values()) and
  rcD3 == 0 and 'still to be read' not in saidD3 and
  rcU == 2 and '--market is one of' in saidU and rcU2 == 2 and
  rcW == 2 and 'cannot be written' in saidW and
  not os.path.exists(os.path.join(WORK, 'other_ledger.json')) and
  [(r['version'], r['part'], r['market']) for r in ledr] ==
  [(C.W30_VERSION, 'market', 'NQ'), (C.W30_VERSION, 'market', 'ES'),
   (C.W30_VERSION, 'market', 'RTY'), (C.W30_VERSION, '2b', 'NQ')] and
  CX.REFUSE_FROM == '20260701' and
  (S.RT, S.RT_STOP, S.SIDE) == (0.5, 0.75, 0.25) and
  S.B_TIMES == tuple(range(30, 361, 30)))

# ---------------------------------------------------------------------
# C8: the verdicts
# ---------------------------------------------------------------------
GOOD = dict(BT=dict(zip(MON, (2.0, 4.0, 2.0, 4.0))),
            BF=dict(zip(MON, (3.0, -3.0, 1.0, 4.0))))


def three(nq=None, es=None, rty=None, d_es=GOOD, d_rty=GOOD):
    return [fake('NQ', nq), fake('ES', es, d_es), fake('RTY', rty, d_rty)]


dec = C.decide(three())
bad_rty = dict(GOOD, BT=dict(zip(MON, (1.0, -3.0, 1.0, 0.5))))
dec_sign = C.decide(three(d_rty=bad_rty))
dec_bar = C.decide(three(es=dict(BT='FAIL')))
later_ok = dict(wave30=C.W30_VERSION, part='2b', market='NQ', collapsed=[])
later_bad = dict(later_ok, collapsed=['BT'])
dec_l = C.decide(three() + [later_ok])
dec_c = C.decide(three() + [later_bad])
dec_fr = C.decide(three(nq={'B+10': 'FAIL', 'B+20': 'FAIL'}))
dec_mx = C.decide(three(nq={'B+10': 'FAIL'}))
dec_mx2 = C.decide(three(rty={'B+20': 'FAIL'}))
dec_rb = C.decide(three(rty={'B': 'FAIL', 'B+20': 'FAIL'}))


def stops(reps_):
    try:
        C.decide(reps_)
    except CX.ContextDataError as exc:
        return str(exc)
    return None


t('C8a: a change is better than B only when it passes the bar on all '
  'three markets, its difference is above 0 on ES and on RTY, and the '
  'two together have a weekly t of 2.5 or more; collapsed in the later '
  'months it does not go on; the later months are asked for until given',
  dec['changes']['BT']['status'] == 'BETTER THAN B' and
  near(dec['changes']['BT']['pooled']['t'],
       round(3.0 / (math.sqrt(4.0 / 3.0) / 2.0), 3)) and
  dec['changes']['BF']['status'] == 'NOT BETTER' and
  dec['changes']['BF']['pooled']['t'] < 2.5 and
  dec['changes']['BF']['pooled']['mean'] > 0 and dec['goes_on'] == ['BT']
  and dec_sign['changes']['BT']['status'] == 'NOT BETTER' and
  dec_sign['changes']['BT']['mean_d']['RTY'] < 0 and
  dec_sign['changes']['BT']['pooled']['mean'] > 0 and
  dec_bar['changes']['BT']['status'] == 'NOT BETTER' and
  not dec['later_read'] and any('still to be read' in x
                                for x in dec['notes']) and
  dec_l['later_read'] and dec_l['goes_on'] == ['BT'] and
  dec_l['notes'] == [] and
  dec_c['changes']['BT']['status'].startswith('NOT BETTER (collapsed') and
  dec_c['goes_on'] == [] and C.T_BAR == 2.5)
t('C8b: the clock is ROBUST when both other clocks pass on NQ and on '
  'each of ES and RTY where B itself passes, FRAGILE when neither passes '
  'on NQ, MIXED otherwise; without B passing everywhere nothing goes on '
  'until wave twenty-five; a missing market, two of one or another '
  'wave\'s report stop',
  dec['clock'] == 'ROBUST' and dec['b_passes_everywhere'] and
  dec_fr['clock'] == 'FRAGILE' and dec_mx['clock'] == 'MIXED' and
  dec_mx2['clock'] == 'MIXED' and dec_rb['clock'] == 'ROBUST' and
  not dec_rb['b_passes_everywhere'] and
  any('until B passes wave twenty-five' in x for x in dec_rb['notes']) and
  'are needed' in stops(three()[:2]) and
  stops(three() + [fake('ES')]) is not None and
  stops(three() + [later_ok, later_ok]) is not None and
  'not one of' in stops(three()[:2] + [dict(wave26='x', part='market',
                                            market='RTY')]) and
  'THE CLOCK (BS): ROBUST' in C.text(dec) and
  'GOES ON: BT' in C.text(dec))

# ---------------------------------------------------------------------
# C9: the registration's rules are the code's
# ---------------------------------------------------------------------
t('C9: the clocks, the three changes in a row, the wait, the marks of '
  'the give-back, what is reported beside and the bar are the frozen '
  'registration\'s',
  (C.STREAK, C.WAIT, C.STEP) == (3, 5, 5) and C.SHIFTED == ('B+10', 'B+20')
  and C.CHANGES == ('BF', 'BT') and C.JUDGED_ON == ('ES', 'RTY') and
  C.BESIDE['BF15'][1] == tuple(range(30, 376, 15)) and
  C.BESIDE['BF5'][1] == tuple(range(30, 386, 5)) and
  [v[2:] for v in C.BESIDE.values()] ==
  [(0, 5), (0, 5), (2, 5), (4, 5), (3, 10)] and
  all(x in REG for x in (
      'FROZEN on 2026-11-27',
      '**B+10** decides at 10:10, 10:40, \u2026, 15:40',
      '**B+20** at 10:20, 10:50, \u2026, 15:50',
      'B\'s rule at every ten minutes: 10:00, 10:10, \u2026, 15:50 (36 times)',
      '**When c(m), c(m \u2212 5) and c(m \u2212 10) are all in the order\'s '
      'direction**', 'at P(m + 5); otherwise at P(m).',
      'The flat at 16:00 is never moved',
      'At every five-minute mark m from 09:45 to 15:50',
      'The same for two and for four changes in a row',
      'every 15 minutes; every 5 minutes',
      'two changes in a row; four; a wait of 10 minutes',
      'both pass on NQ, and both pass on each of ES and RTY on which B '
      'itself passes', 'neither passes on NQ',
      'the mean of D is above 0 on ES and above 0 on RTY',
      '**weekly t of 2.5 or more**', 'must not be COLLAPSED',
      '**but only if B itself passes wave twenty-five**',
      'Explicitly NOT registered', 'Expected beforehand')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
