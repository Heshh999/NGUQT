#!/usr/bin/env python3
# MROF-YT-W24-SCREEN15-1.0 suite. The minute grid, each of the thirteen
# judged rules, the benchmark and the pass bar are exercised on
# hand-built sessions with known answers; the pipeline end to end on a
# synthetic NinjaTrader-format export with stray weekend bars and one
# planted effect. Synthetic data verifies CODE BEHAVIOR only, never
# market evidence. No order, fill or P&L exists.
import array
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

import mrofyt_context as CX          # noqa: E402
import mrofyt_screen15 as S          # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


def near(a, b, tol=1e-9):
    return abs(a - b) <= tol


WORK = tempfile.mkdtemp(prefix='mrofyt_w24_')
N = S.N_MIN


def mk(session, o, pc, closes, highs=None, lows=None, vols=None):
    """A Day from 390 closes (a short list is padded with its last)."""
    c = list(closes) + [closes[-1]] * (N - len(closes))
    h = list(highs) + c[len(highs):] if highs else list(c)
    lo = list(lows) + c[len(lows):] if lows else list(c)
    v = list(vols) + [1.0] * (N - len(vols)) if vols else [1.0] * N
    return S.Day(session, 'NQ 12-21', o, pc, c, h, lo, v)


def flat(session, o, pc, marks):
    """A Day whose price steps to marks[j] at minute j (the price at
    09:30 + j is marks[j]; unlisted minutes keep the last price)."""
    c, last = [], o
    for j in range(1, N + 1):
        last = marks.get(j, last)
        c.append(last)
    return mk(session, o, pc, c)


# ---------------------------------------------------------------------
# S1: the minute grid
# ---------------------------------------------------------------------
bars = array.array('d')
vols = array.array('d')
for key, h, lo, c, v in ((34320, 102.5, 101.0, 102.0, 5),     # 09:32
                         (34140, 100.0, 100.0, 100.0, 7),     # 09:29
                         (34080, 99.0, 99.0, 99.0, 7),        # 09:28
                         (34200, 101.0, 99.5, 100.5, 10),     # 09:30
                         (57600, 150.0, 150.0, 150.0, 9)):    # 16:00, after
    bars.extend((key, h, lo, c))
    vols.append(v)
g = S.grid(bars, vols)
none1 = S.grid(array.array('d', (34200, 101.0, 99.5, 100.5)),
               array.array('d', (10,)))
none2 = S.grid(array.array('d', (30000, 99.0, 99.0, 99.0,       # 08:20
                                 34200, 101.0, 99.5, 100.5)),
               array.array('d', (5, 10)))
d1 = S.Day('20210104', 'NQ 03-21', g[0], 99.0, g[1], g[2], g[3], g[4])
t('S1: the grid is 390 one-minute bars from 09:30 whatever the file\'s '
  'order; the open is the last close in the hour before 09:30; a minute '
  'without a bar carries the last close with no range and no volume; no '
  'open, no session; p(j) and the VWAP follow the bars',
  g[0] == 100.0 and len(g[1]) == 390 and g[1][:3] == [100.5, 100.5, 102.0]
  and g[2][1] == 100.5 and g[3][1] == 100.5 and g[4][1] == 0.0 and
  g[1][389] == 102.0 and g[4][389] == 0.0 and none1 is None and
  none2 is None and d1.p(0) == 100.0 and d1.p(1) == 100.5 and
  d1.p(3) == 102.0 and d1.vwap(0) is None and
  near(d1.vwap(1), (101.0 + 99.5 + 100.5) / 3) and
  near(d1.vwap(2), d1.vwap(1)) and
  near(d1.vwap(3), ((101.0 + 99.5 + 100.5) / 3 * 10 +
                    (102.5 + 101.0 + 102.0) / 3 * 5) / 15))

# ---------------------------------------------------------------------
# S2: A, the opening range breakout
# ---------------------------------------------------------------------
first = [100.5, 101.0, 101.5, 102.0, 102.0]


def a_day(tail_c, tail_h=None, tail_l=None, lows0=99.0):
    c = first + tail_c
    h = list(c)
    lo = [lows0] + c[1:]
    for k, x in (tail_h or {}).items():
        h[k] = x
    for k, x in (tail_l or {}).items():
        lo[k] = x
    return mk('20210104', 100.0, 99.0, c, h, lo)


ta = S.trade_a(a_day([103.0] * 10, tail_h={8: 132.0}))
tb = S.trade_a(a_day([103.0] * 10, tail_h={8: 140.0}, tail_l={8: 98.0}))
tc = S.trade_a(a_day([103.0] * 10 + [104.0]))
td = S.trade_a(mk('20210104', 100.0, 99.0, [100.5, 101.0, 100.5, 100.2,
                                             100.0]))
te = S.trade_a(mk('20210104', 100.0, 99.0, [99.5, 99.0, 98.5, 98.0, 98.0,
                                             97.0, 97.0],
                  highs=[100.5, 99.0, 98.5, 98.0, 98.0, 97.0, 101.0]))
tf = S.trade_a(mk('20210104', 100.0, 99.0, [100.5, 101.0, 101.5, 102.0,
                                             102.0],
                  lows=[101.75, 101.75, 101.75, 101.75, 101.75]))
tg = S.trade_a(mk('20210104', 100.0, 99.0, [101.0, 101.0, 101.0, 101.0,
                                             101.0]))
t('S2: A trades the first candle\'s direction from 09:35, stop at its '
  'other end, target at 10 R, a bar touching both a stop, otherwise out at '
  'the close; no trade on a flat candle or a zero risk; sized 1 % of risk '
  'with a 4x cap; a stop costs 0.75 and the rest 0.50',
  ta['how'] == 'TARGET' and near(ta['gross'], 30.0 / 102.0) and
  near(ta['cost'], 0.5 / 102.0) and near(ta['lev'], 0.01 / (3.0 / 102.0))
  and tb['how'] == 'STOP' and near(tb['gross'], -3.0 / 102.0) and
  near(tb['cost'], 0.75 / 102.0) and
  tc['how'] == 'CLOSE' and near(tc['gross'], 2.0 / 102.0) and
  td is None and
  te['how'] == 'STOP' and near(te['gross'], -2.5 / 98.0) and
  near(tf['lev'], 4.0) and tg is None)

# ---------------------------------------------------------------------
# S3: B, out of the noise area
# ---------------------------------------------------------------------
sig = [0.01] * (N + 1)
db = flat('20210104', 100.0, 99.0, {1: 100.5, 31: 102.0, 61: 103.0,
                                    91: 100.8, 151: 97.0, 390: 96.0})
gb = S.day_b(db, sig)
# above the upper bound but under a heavy early VWAP: flat
dv = mk('20210104', 100.0, 99.0, [110.0] * 29 + [101.5],
        vols=[1000.0] * 29 + [1.0])
gv = S.day_b(dv, sig)
# a close above the open lifts the upper bound: 102 is inside it
dg = flat('20210104', 100.0, 103.0, {1: 102.0})
gg = S.day_b(dg, sig)
t('S3: B is long above the upper bound and VWAP, short below the lower '
  'bound and VWAP, flat otherwise, decided on the half hours and flat at '
  'the close; the bounds start from the higher and the lower of the open '
  'and yesterday\'s close; 0.25 a side',
  near(gb[0], (-1.2 + 1.0) / 100.0) and near(gb[1], 4 * 0.25 / 100.0) and
  gb[2] == 4 and gv[2] == 0 and gv[0] == 0.0 and gg[2] == 0)

# ---------------------------------------------------------------------
# S4: C, O4, Q4 and the big nights
# ---------------------------------------------------------------------
days = {}
order = []
base = _dt.date(2021, 1, 4)
ds = []
dd = base
while len(ds) < 24:
    if dd.weekday() < 5:
        ds.append(dd.strftime('%Y%m%d'))
    dd += _dt.timedelta(days=1)
for i, s in enumerate(ds[:20]):                 # twenty nights of 1 %
    days[s] = flat(s, 101.0, 100.0, {})
days[ds[20]] = flat(ds[20], 102.5, 100.0, {15: 101.5, 60: 100.5,
                                           360: 99.0, 390: 98.0})
days[ds[21]] = flat(ds[21], 100.5, 100.0, {15: 99.0, 60: 98.0})   # small
days[ds[22]] = flat(ds[22], 97.0, 100.0, {15: 97.5, 60: 99.0, 390: 99.5})
order = sorted(days)
big = S.big_nights(days, order)
o4, _ = S.rule_o4(days, order)
q4, _ = S.rule_q4(days, order)
cc, _ = S.rule_c(days, order)
c20 = [x for x in cc if x['session'] == ds[20]][0]
t('S4: a big night is at least the mean of the 20 before it; O4 follows '
  'the first 15 minutes to 10:30 and says whether that is with the night; '
  'Q4 trades against the night to the close; C follows the day from 15:30',
  sorted(big) == [ds[20], ds[22]] and len(o4) == 2 and
  o4[0]['part'] == 'against' and
  near(o4[0]['gross'], -(100.5 / 101.5 - 1.0)) and
  near(o4[0]['cost'], 0.5 / 101.5) and
  o4[1]['part'] == 'against' and near(o4[1]['gross'], 99.0 / 97.5 - 1.0)
  and len(q4) == 2 and near(q4[0]['gross'], -(98.0 / 102.5 - 1.0)) and
  near(q4[0]['to_1030'], -(100.5 / 102.5 - 1.0)) and
  near(q4[1]['gross'], 99.5 / 97.0 - 1.0) and
  near(c20['gross'], -(98.0 / 99.0 - 1.0)) and
  near(c20['cost'], 0.5 / 99.0) and len(cc) == 23)

# ---------------------------------------------------------------------
# S5: D, the VWAP trend
# ---------------------------------------------------------------------
dday = mk('20210104', 100.0, 99.0, [101.0, 102.0, 100.0])
gd = S.day_d(dday)
t('S5: D is long above VWAP and short below from 09:31, unchanged when '
  'equal, flat at the close; each contract bought or sold costs 0.25',
  near(gd[0], -2.0 / 100.0) and near(gd[1], (0.25 + 0.5 + 0.25) / 100.0)
  and gd[2] == 3)


# ---------------------------------------------------------------------
# S6: the daily chain rules E, Q3, Q5
# ---------------------------------------------------------------------
def chain_of(rows):
    out, prev = [], None
    for s, close, high, low, ret in rows:
        out.append(dict(session=s, contract='NQ 12-21', close=close,
                        high=high, low=low, ret=ret, prev=prev))
        prev = s
    return out


ce = chain_of([
    ('20210104', 100.5, 110.0, 100.0, None),      # IBS 0.05: buy
    ('20210105', 105.0, 110.0, 100.0, 0.01),      # 0.5: hold
    ('20210106', 109.5, 110.0, 100.0, 0.02),      # 0.95: sell
    ('20210107', 100.2, 110.0, 100.0, 0.00),      # 0.02: buy
    ('20210108', 105.0, 110.0, 100.0, None),      # no return
    ('20210111', 109.9, 110.0, 100.0, 0.01),      # 0.99: sell -> dropped
    ('20210112', 100.1, 110.0, 100.0, 0.00),      # buy, never sold
    ('20210113', 105.0, 105.0, 105.0, 0.00)])     # no range: skipped
te_, ne = S.rule_e(ce)


def month_days(y, m):
    d, out = _dt.date(y, m, 1), []
    while d.month == m:
        if d.weekday() < 5:
            out.append(d.strftime('%Y%m%d'))
        d += _dt.timedelta(days=1)
    return out


rows = []
for (y, m) in ((2021, 1), (2021, 2), (2021, 3)):
    for s in month_days(y, m):
        rows.append((s, 100.0, 101.0, 99.0, 0.001))
cq = chain_of(rows)
cq[0]['ret'] = None
jan, feb, mar = month_days(2021, 1), month_days(2021, 2), month_days(2021, 3)
idx = {r['session']: i for i, r in enumerate(cq)}
for s in feb[:-4]:
    cq[idx[s]]['ret'] = 0.002                     # February so far: up
for s in feb[-3:]:
    cq[idx[s]]['ret'] = -0.004                    # its last three days
q3, n3 = S.rule_q3(cq)
q5, n5 = S.rule_q5(cq)
mtd = 1.002 ** len(feb[:-4]) * 1.001 - 1.0        # to the 4th-to-last
t('S6: E buys a close in the bottom tenth of the day\'s range and sells '
  'one in the top tenth, held over the days between; Q3 holds from the '
  'second-to-last day of a month to the third of the next; Q5 trades '
  'against the month so far over its last three days; a hold across a day '
  'without a return is dropped and counted',
  len(te_) == 1 and te_[0]['session'] == '20210104' and
  near(te_[0]['gross'], 1.01 * 1.02 - 1.0) and te_[0]['units'] == 2 and
  near(te_[0]['cost'], 0.5 / 100.5) and ne['dropped_no_return'] == 1 and
  ne['open_at_the_end'] == 1 and
  [x['session'] for x in q3] == [jan[-2], feb[-2]] and
  q3[0]['units'] == 4 and
  near(q3[0]['gross'], 1.001 * 1.002 ** 3 - 1.0) and
  near(q3[1]['gross'], 0.996 * 1.001 ** 3 - 1.0) and
  [x['session'] for x in q5] == [feb[-4]] and mtd > 0 and
  near(q5[0]['gross'], -(0.996 ** 3 - 1.0)) and
  n3['dropped_no_return'] == 0 and n5['dropped_no_return'] == 0)

# ---------------------------------------------------------------------
# S7: O1, the night after selling into the close
# ---------------------------------------------------------------------
dates, dd = [], _dt.date(2020, 6, 1)
while len(dates) < 104:
    if dd.weekday() < 5:
        dates.append(dd.strftime('%Y%m%d'))
    dd += _dt.timedelta(days=1)
d7 = {}
for i, s in enumerate(dates[:100]):
    x = (i - 50) * 1e-4
    d7[s] = flat(s, 100.0, 100.0, {360: 100.0, 390: 100.0 * math.exp(x)})
thr = (19 - 50) * 1e-4                            # the 20th smallest
d7[dates[100]] = flat(dates[100], 100.0, 100.0,
                      {360: 100.0, 390: 100.0 * math.exp(thr)})
d7[dates[101]] = flat(dates[101], 100.6, 100.0,
                      {360: 100.0, 390: 100.0 * math.exp(-0.02)})
d7[dates[103]] = flat(dates[103], 101.0, 100.0, {})
c7 = chain_of([(s, 100.0, 101.0, 99.0, 0.0) for s in dates])
o7 = sorted(d7)                                   # dates[102] not eligible
t1, n1 = S.rule_o1(d7, o7, c7)
net1 = S.nets('O1', t1, dict(H1=0.001, H2=0.0))
t('S7: O1 buys the close when the last half hour is at or below the 20th '
  'smallest of the 100 before it and holds to the next open; a next '
  'session that is not eligible is skipped and counted; a long-only rule '
  'is judged over the half\'s average holding',
  len(t1) == 1 and t1[0]['session'] == dates[100] and
  near(t1[0]['gross'], 100.6 / 100.0 - 1.0) and
  near(t1[0]['cost'], 0.5 / (100.0 * math.exp(thr))) and
  n1['skipped_next_not_eligible'] == 1 and
  near(net1[0][1], 1e4 * (t1[0]['gross'] - t1[0]['cost'] - 0.001), 1e-6))

# ---------------------------------------------------------------------
# S8: O5, Q1, Q2
# ---------------------------------------------------------------------
d8, o8 = {}, dates[:16]
for s in o8[:14]:                                 # 0.1 % each half hour
    d8[s] = flat(s, 100.0, 100.0, dict(
        (j, 100.0 * 1.001 ** (j // 30)) for j in range(30, 391, 30)))
p10 = 100.0 * 1.002
p12 = p10 * 1.002
d8[o8[14]] = flat(o8[14], 100.0, 100.0, {
    30: p10, 60: p10 * 1.01, 150: p10 * 1.01, 180: p12 * 1.01,
    210: p12 * 1.01 * 0.99})
o5, _ = S.rule_o5(d8, o8[:15])
d9 = {}
for i, s in enumerate(dates[:21]):
    up = 1.001 + (1e-6 if i % 2 else 0.0)
    alt = 1.001 if i % 2 else 1 / 1.001
    d9[s] = flat(s, 100.0, 100.0, {30: 100.0 * up, 150: 100.0 * up,
                                   180: 100.0 * up * alt})
q1, _ = S.rule_q1(d9, dates[:21])
d10 = {}
for s in dates[:14]:
    marks, p = {}, 100.0
    for j in range(15, 391, 15):
        p *= 1.0005
        marks[j] = p
    d10[s] = mk(s, 100.0, 100.0, flat(s, 100.0, 100.0, marks).c,
                vols=[100.0 / 15] * N)
mk15 = {15: 100.0, 30: 99.8, 45: 99.6, 60: 99.4, 75: 99.2, 90: 99.3,
        105: 99.3, 120: 99.1}        # 10:30 on: ordinary volume
shock = flat(dates[14], 100.0, 100.0, mk15).c
v10 = [100.0 / 15] * N
for j in range(15, 75):                           # heavy to 10:30
    v10[j] = 200.0 / 15
d10[dates[14]] = mk(dates[14], 100.0, 100.0, shock, vols=v10)
q2, _ = S.rule_q2(d10, dates[:15])
t('S8: O5 follows a move of 1.5x the usual on a busy half hour and fades '
  'it on a quiet one; Q1 trades a half hour whose last 20 days lean one '
  'way; Q2 fades a move of 3x the usual on 1.5x the volume, one trade at a '
  'time, and needs the volume',
  [x['part'] for x in o5] == ['busy', 'busy', 'quiet', 'quiet'] and
  near(o5[0]['gross'], 0.01) and near(o5[1]['gross'], 0.0) and
  near(o5[2]['gross'], 0.01) and near(o5[3]['gross'], 0.0) and
  [x['slot'] for x in q1] == [0] and q1[0]['session'] == dates[20] and
  [x['at'] for x in q2] == [30, 60] and
  near(q2[0]['gross'], 99.4 / 99.8 - 1.0) and
  near(q2[1]['gross'], 99.3 / 99.4 - 1.0))

# ---------------------------------------------------------------------
# S9: the pass bar
# ---------------------------------------------------------------------
def pairs(h1, h2):
    return [('2020%02d%02d' % (1 + k % 12, 1 + k % 28), x)
            for k, x in enumerate(h1)] + \
           [('2021%02d%02d' % (1 + k % 12, 1 + k % 28), x)
            for k, x in enumerate(h2)]


rng = random.Random(3)
good = [1.0 + rng.gauss(0, 0.5) for _ in range(60)]
j_ok = S.judge(pairs(good, good))
j_few = S.judge(pairs(good[:29], good))
one = [-0.1] * 55 + [0.0] * 5
one_month = [x + (30.0 if k % 12 == 0 else 0.0) for k, x in enumerate(one)]
j_one = S.judge(pairs(one_month, good))
j_neg = S.judge(pairs(good, [-x for x in good]))
t('S9: the screen passes a rule only with a profit in each half, still '
  'one without its best month, on 30 trades or more in each; a pass whose '
  '95 % range is above zero is strong',
  j_ok['status'] == 'PASS' and j_ok['strong'] and
  j_few['status'] == 'FAIL' and not j_few['halves']['H1']['ok'] and
  j_one['halves']['H1']['net'] > 0 and
  j_one['halves']['H1']['net_without_best'] < 0 and
  j_one['status'] == 'FAIL' and j_neg['status'] == 'FAIL' and
  not j_neg['strong'] and S.judge([])['status'] == 'FAIL')

# ---------------------------------------------------------------------
# S10: the benchmark O2
# ---------------------------------------------------------------------
d11 = {}
for i, s in enumerate(dates[:60]):
    c, h, lo = [], [], []
    mult = 2.0 if i % 2 else 1.0                  # every other day doubles
    for k in range(13):
        r = (k + 1) * mult
        c += [100.0] * 30
        h += [100.0 + r] + [100.0] * 29
        lo += [100.0] * 30
    d11[s] = mk(s, 100.0, 100.0, c, h, lo)
b2 = S.bench_o2(d11, dates[:60])
d12 = {s: mk(s, 100.0, 100.0, d11[dates[0]].c, d11[dates[0]].h,
             d11[dates[0]].l) for s in dates[:40]}
b3 = S.bench_o2(d12, dates[:40])
t('S10: the benchmark explains the next half hour\'s range by the time of '
  'day, and better with today\'s previous surprise when surprises last',
  b3['H1']['r2_f1'] == 1.0 and b3['H1']['r2_f2'] == 1.0 and
  b2['H1']['r2_f2'] > b2['H1']['r2_f1'] and b2['H1']['r2_f2'] > 0.9)

# ---------------------------------------------------------------------
# S11: end to end on a synthetic export
# ---------------------------------------------------------------------
EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def to_utc(local_epoch):
    y = _dt.datetime.fromtimestamp(local_epoch, _dt.timezone.utc).year
    for off in (4, 5):
        u = local_epoch + off * 3600
        w = CX._dst_window(y)
        if (off == 4) == (w[0] <= u < w[1]):
            return u
    return local_epoch + 5 * 3600


def stamp(d, minute):
    loc = int((_dt.datetime(d.year, d.month, d.day, tzinfo=_dt.timezone.utc)
               - EPOCH).total_seconds()) + minute * 60
    return _dt.datetime.fromtimestamp(to_utc(loc) + 60, _dt.timezone.utc
                                      ).strftime('%Y%m%d %H%M%S')


def write_export(folder, n_days=430, seed=11, plant=0.5):
    """One contract, weekdays from 2020-03-02: bars 08:30-16:14 ET, a
    random walk; in the last half hour the price drifts `plant` points a
    minute in the direction of the day so far (C's effect); a stray bar
    on every Sunday and Saturday."""
    os.makedirs(folder, exist_ok=True)
    rng = random.Random(seed)
    px, pc = 10000.0, 10000.0
    rows, d, n = [], _dt.date(2020, 3, 2), 0
    while n < n_days:
        if d.weekday() >= 5:
            rows.append('%s;%.2f;%.2f;%.2f;%.2f;1' % (
                stamp(d, 11 * 60), px, px, px, px))
        else:
            n += 1
            px = pc + rng.gauss(0, 20.0)
            side = 0
            for m in range(8 * 60 + 30, 16 * 60 + 15):
                if m == 15 * 60 + 30:
                    side = (px > pc) - (px < pc)
                step = rng.gauss(0, 2.0)
                if 15 * 60 + 30 <= m < 16 * 60:
                    step += side * plant
                o = px
                px = round((px + step) * 4) / 4
                h, lo = max(o, px) + 0.25, min(o, px) - 0.25
                v = 50 if m < 9 * 60 + 30 else (3000 if m == 9 * 60 + 30
                                                else 900)
                rows.append('%s;%.2f;%.2f;%.2f;%.2f;%d' % (
                    stamp(d, m), o, h, lo, px, v))
                if m == 15 * 60 + 59:
                    pc = px
        d += _dt.timedelta(days=1)
    with open(os.path.join(folder, 'NQ 12-21.Last.txt'), 'w') as fh:
        fh.write('\n'.join(rows) + '\n')


F = os.path.join(WORK, 'export')
write_export(F)
rep = S.run(F)
rd, _chk = S.read(F)
dz, oz, cz = S.build(rd)
mon_all = sum(1 for r in cz if _dt.date(int(r['session'][:4]),
                                        int(r['session'][4:6]),
                                        int(r['session'][6:])).weekday() == 0)
mon_kept = sum(1 for s in oz if _dt.date(int(s[:4]), int(s[4:6]),
                                         int(s[6:])).weekday() == 0)
txt = S.text(rep)
out11 = os.path.join(WORK, 'w24.json')
buf = io.StringIO()
with redirect_stdout(buf):
    rc0 = S.main([])
    rc_none = S.main([os.path.join(WORK, 'no_such_folder')])
    rc_ok = S.main([F, '--out', out11])
said = buf.getvalue()
_reg = open(os.path.join(HERE, S.REGISTRATION), encoding='utf-8').read()
t('S11: end to end on a synthetic export with a stray bar every weekend: '
  'Mondays are kept, the planted last-half-hour effect passes strongly, '
  'the VWAP trend on a random walk fails on its costs, thirteen rules are '
  'judged and O2 reported; the command writes the report and stops on a '
  'missing folder; the registration states the bar and the fifteen',
  rep['rules']['C']['status'] == 'PASS' and rep['rules']['C']['strong']
  and rep['rules']['D']['status'] == 'FAIL' and
  rep['rules']['D']['halves']['H1']['net'] < 0 and
  list(rep['rules']) == list(S.JUDGED) and
  set(rep['benchmark_o2']) == {'H1', 'H2'} and
  len(cz) == 430 and mon_all == 86 and mon_kept >= mon_all - 4 and
  rep['sessions'] == len(oz) and len(oz) >= 400 and
  all(S.NAMES[r] in txt for r in S.NAMES if r not in ('O2', 'O3')) and
  'PASSED THE SCREEN' in txt and json.dumps(rep, default=str) and
  rc0 == 2 and rc_none == 2 and rc_ok == 0 and
  'STOPPED: cannot read' in said and
  'wave-twenty-four report ->' in said and
  json.load(open(out11))['passed'] == rep['passed'] and
  all(x in _reg for x in (
      'FROZEN on 2026-11-24', 'This is a screen, not a test',
      '**O1 ', '**O2 ', '**O3 ', '**O4 ', '**O5 ', '**A ', '**B ', '**C ',
      '**D ', '**E ', '**Q1 ', '**Q2 ', '**Q3 ', '**Q4 ', '**Q5 ',
      'at least 30 trades', 'Long-only rules (O1, E, Q3)',
      'Already seen on these bars', 'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
