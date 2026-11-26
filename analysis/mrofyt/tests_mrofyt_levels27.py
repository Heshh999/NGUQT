#!/usr/bin/env python3
# MROF-YT-W27-LEVELS-1.0 suite. The registry against the registration,
# the week split, the grid against wave twenty-four's sessions, every
# level and event on hand-built bars, the trades, the squeeze, the
# overnight ranges, EPROP, the statistics and the two stages on built
# data; then causality (no signal changes when the bars after it do)
# and the whole pipeline on a synthetic NinjaTrader-format export with a
# planted effect, the lockbox read once. Synthetic data verifies CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import array
import collections
import datetime as _dt
import hashlib
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

import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_discover as DI         # noqa: E402
import mrofyt_improve26 as W26       # noqa: E402
import mrofyt_levels27 as V          # noqa: E402
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


WORK = tempfile.mkdtemp(prefix='mrofyt_w27_')
D = _dt.date
NG, R0 = V.NG, V.R0
REG = ' '.join(open(os.path.join(HERE, V.REGISTRATION),
                    encoding='utf-8').read().split())


def flat_full(base=100.0, sig=0.01):
    f = V.Full()
    f.C, f.H, f.L = (array.array('d', [base] * NG) for _ in range(3))
    f.V = array.array('d', [1.0] * NG)
    f.session, f.contract, f.week, f.lock = '20210104', 'NQ 03-21', \
        '2021-W01', False
    f.first, f.on_ok, f.sig = 0, True, sig
    f.pdh = f.pdl = f.pdc = f.pwh = f.pwl = None
    return f


def bar(f, i, c, h=None, lo=None):
    prev = f.C[i - 1]
    f.C[i] = c
    f.H[i] = max(prev, c) if h is None else h
    f.L[i] = min(prev, c) if lo is None else lo
    for k in range(i + 1, NG):          # later minutes carry it
        f.C[k] = f.H[k] = f.L[k] = c


def lv(group, price, arm):
    return [group, price, arm, 0, 0]


# ---------------------------------------------------------------------
# L1: the registry is the registration's
# ---------------------------------------------------------------------
fams = V.FAMILIES
t('L1: 90 families, 438 strategies and their mirrors, EPROP: 877 '
  'strategies in 181 hypotheses, as the registration counts them; the '
  'rules already judged on these bars are not among them',
  len(fams) == 90 and sum(len(h) for h in fams.values()) == 438 and
  V.N_STRATEGIES == 877 and len(V.HYPOTHESES) == 181 and
  len(set(V.HYPOTHESES)) == 181 and V.HYPOTHESES[-1] == 'EPROP' and
  sum(1 for f in fams if f.split('.')[0] in V.OUTER) == 12 and
  sum(1 for f in fams if f.split('.')[0] in V.INNER) == 64 and
  not any(f.split('.')[0] in V.OUTER and f.split('.')[1] in ('REJ', 'FBK')
          for f in fams) and
  'AMX.BRK.AM' not in fams and 'AMX.BRK.PM' in fams and
  not any('VW' in f for f in fams) and
  fams['PDX.BRK.AM'] == (15, 30, 60, 120, 180) and
  fams['ASIA.REJ.EU'] == (30, 60, 120, 180) and
  fams['EUR.FBK.PRE'] == (15, 30, 60) and
  (V.MIN_TRADES, V.MIN_POSITIVE, V.MIN_T, V.MAX_FORWARD, V.BH_Q) ==
  (150, 0.6, 2.5, 12, 0.10) and
  all(x in REG for x in (
      'FROZEN on 2026-11-26',
      '90 families; 438 strategies and their 438 mirrors; 180 hypotheses',
      'In all: 877 strategies, 181 hypotheses',
      '| PDX, ONX, PWX | BRK, RET | AM, PM | 12 |',
      '| PDC, OPN, OR15, IB60, HRX, RND, SW5, SW15 | BRK, REJ, RET, FBK | '
      'AM, PM | 64 |', '| AMX | BRK, REJ, RET, FBK | PM | 4 |',
      'H = 15, 30, 60, 120, 180 (ASIA: 30, 60, 120, 180; EUR: 15, 30, 60)',
      'average 150 trades or more', 'at least 60 % of its strategies',
      't ≥ 2.5', 'At most the twelve', 'Benjamini–Hochberg at 10 %',
      'no variant of it is tried on these bars')))

# ---------------------------------------------------------------------
# L2: the weeks and the lockbox
# ---------------------------------------------------------------------
labels = sorted({V.week_label(D(2016, 1, 4) + _dt.timedelta(days=7 * k))
                 for k in range(546)})
lock_share = sum(1 for x in labels if V.is_lockbox(x)) / float(len(labels))
t('L2: a week is its ISO label; it is lockbox when the first eight hex '
  'digits of its SHA-256 are odd: about half of them, and always the '
  'same ones',
  V.week_label(D(2021, 1, 4)) == '2021-W01' and
  V.week_label(D(2021, 1, 3)) == '2020-W53' and
  V.week_label(D(2026, 6, 11)) == '2026-W24' and
  all(V.is_lockbox(x) == (int(hashlib.sha256(x.encode()).hexdigest()[:8],
                              16) % 2 == 1) for x in labels) and
  0.44 < lock_share < 0.56 and len(labels) >= 540)

# ---------------------------------------------------------------------
# L3: the level machine
# ---------------------------------------------------------------------
f = flat_full()
bar(f, 12, 101.25, h=101.5)              # first test from below: closes up
bar(f, 15, 101.1, lo=100.9)              # back to it, closes above: retest
bar(f, 16, 100.0)                        # through it again: finished
m1 = V.machine(f, [lv('X', 101.0, 10)], 10, 40)
f = flat_full()
bar(f, 12, 100.5, h=101.0)               # touches, closes back: rejection
bar(f, 14, 102.0)                        # a later break: finished
m2 = V.machine(f, [lv('X', 101.0, 10)], 10, 40)
f = flat_full(102.0)
bar(f, 12, 100.5)                        # from above, closes below: break
bar(f, 13, 100.75)                       # not back at it
bar(f, 14, 101.5)                        # back, closes through: failed
m3 = V.machine(f, [lv('X', 101.0, 10)], 10, 40)
f = flat_full()
bar(f, 8, 101.5)                         # before it may be tested
bar(f, 9, 100.0)
bar(f, 11, 101.0)                        # closes exactly on it: rejection
m4 = V.machine(f, [lv('X', 101.0, 10)], 10, 40)
f = flat_full(101.0)                     # the price before is the level
bar(f, 12, 103.0)
bar(f, 13, 100.5, lo=100.5)              # now a test from above
m5 = V.machine(f, [lv('X', 101.0, 10)], 10, 40)
f = flat_full(102.0)
bar(f, 12, 101.5, lo=101.0)              # holds from above: long
m6 = V.machine(f, [lv('X', 101.0, 10)], 10, 40)
t('L3: the first test of a level is a break when the bar closes beyond '
  'it and a rejection when it does not; after a break the first return '
  'is a retest or a failed breakout; then the level is finished; nothing '
  'before its first bar, nothing when the price before is on it',
  m1 == [(12, 'X', 'BRK', 1), (15, 'X', 'RET', 1)] and
  m2 == [(12, 'X', 'REJ', -1)] and
  m3 == [(12, 'X', 'BRK', -1), (14, 'X', 'FBK', 1)] and
  m4 == [(11, 'X', 'REJ', -1)] and
  m5 == [(13, 'X', 'BRK', -1)] and m6 == [(12, 'X', 'REJ', 1)])

# ---------------------------------------------------------------------
# L4: the levels of a session
# ---------------------------------------------------------------------
f = flat_full(1000.0)
f.pdh, f.pdl, f.pdc, f.pwh, f.pwl = 1040.0, 960.0, 1010.0, 1100.0, 900.0
bar(f, 100, 1030.0)                      # overnight high
bar(f, 200, 985.0)                       # overnight low
bar(f, 880, 1001.0, h=1021.0)            # 08:40: in the 09:00 hour? no
bar(f, 905, 1002.0, h=1022.0)            # 09:05: the 09:00-10:00 hour
bar(f, R0 + 3, 1005.0, h=1008.0)         # 09:33
bar(f, R0 + 20, 1003.0, lo=996.0)        # 09:50
bar(f, R0 + 100, 1004.0, h=1012.0)       # 11:10
bar(f, R0 + 200, 1004.0, lo=990.0)       # 12:50
got = collections.defaultdict(list)
for g, price, arm, _s, _d in V.rth_levels(f):
    got[g].append((arm - R0, price))
f2 = flat_full(1000.0)
f2.on_ok = False
t('L4: each group\'s levels and the first bar that may test them: '
  'yesterday, the overnight (only with overnight bars), last week, the '
  'open from 10:00, the ranges once complete, each clock hour\'s, the '
  'round hundreds',
  sorted(got['PDX']) == [(0, 960.0), (0, 1040.0)] and
  sorted(got['ONX']) == [(0, 985.0), (0, 1030.0)] and
  sorted(got['PWX']) == [(0, 900.0), (0, 1100.0)] and
  got['PDC'] == [(0, 1010.0)] and got['OPN'] == [(30, 1002.0)] and
  sorted(got['OR15']) == [(15, 1002.0), (15, 1008.0)] and
  sorted(got['IB60']) == [(60, 996.0), (60, 1008.0)] and
  sorted(got['AMX']) == [(150, 996.0), (150, 1012.0)] and
  sorted(got['HRX'])[:2] == [(30, 996.0), (30, 1022.0)] and
  got['HRX'].count((90, 1003.0)) == 2 and
  (150, 1012.0) in got['HRX'] and (150, 1003.0) in got['HRX'] and
  (210, 990.0) in got['HRX'] and (210, 1004.0) in got['HRX'] and
  len(got['HRX']) == 12 and
  sorted(got['RND']) == [(0, 900.0), (0, 1000.0), (0, 1100.0)] and
  'ONX' not in {x[0] for x in V.rth_levels(f2)})

# ---------------------------------------------------------------------
# L5: swings
# ---------------------------------------------------------------------
f = flat_full(100.0)
for b, hi in ((4, 105.0), (5, 101.0), (9, 104.0), (10, 104.0)):
    f.H[R0 + 5 * b + 2] = hi             # one high inside 5-minute bar b
f.L[R0 + 5 * 7 + 1] = 95.0               # a low in bar 7
sw = V.swings(f.H, f.L, 5)
f15 = flat_full(100.0)
f15.H[R0 + 15 * 4 + 7] = 108.0
sw15 = V.swings(f15.H, f15.L, 15)
t('L5: a swing high is a bar\'s high above the three before it and not '
  'below the three after; it may be tested from the bar after those '
  'three; equal highs keep the first',
  (40, 105.0) in sw and (55, 95.0) in sw and (65, 104.0) in sw and
  not any(p == 101.0 for _a, p in sw) and
  sum(1 for _a, p in sw if p == 104.0) == 1 and
  sw15 == [(120, 108.0)])

# ---------------------------------------------------------------------
# L6: the trades of a session
# ---------------------------------------------------------------------
f = flat_full(1000.0, sig=0.01)
for i in range(R0 + 10, NG):
    f.C[i] = 1000.0 + (i - R0 - 10) * 0.5      # +0.5 a minute from 09:40
sig6 = [(R0 + 10, 'OR15', 'BRK', 1), (R0 + 14, 'OR15', 'BRK', 1),
        (R0 + 30, 'OR15', 'BRK', -1), (R0 + 119, 'SW5', 'REJ', 1),
        (R0 + 120, 'SW5', 'REJ', 1), (R0 + 355, 'RND', 'BRK', 1),
        (R0 + 50, 'PDX', 'REJ', 1), (500, 'ASIA', 'RET', -1),
        (900, 'EUR', 'FBK', 1)]
r6 = V.day_results(f, sig6, 0.5)


def gross(i, h, d=1):
    t0 = i + 1
    t1 = min(t0 + h, NG)
    return d * (f.C[t1 - 1] - f.C[t0 - 1]) / f.C[t0 - 1] / 0.01


t('L6: a trade is entered at the close of the event\'s bar and left H '
  'minutes on, at 16:00 at the latest; a strategy holds one at a time; '
  'results are in R with the cost a trade; events fall in AM or PM by '
  'their bar; a family not registered takes none',
  sorted(r6) == ['ASIA.RET.EU', 'EUR.FBK.PRE', 'OR15.BRK.AM',
                 'RND.BRK.PM', 'SW5.REJ.AM', 'SW5.REJ.PM'] and
  [x[2] for x in r6['OR15.BRK.AM']] == [2, 1, 1, 1, 1] and
  near(gross(R0 + 10, 15), 0.75) and
  near(r6['OR15.BRK.AM'][0][0], 0.75 - 7.5 / 1010.0 / 0.01) and
  near(r6['OR15.BRK.AM'][0][1], 0.05 + 0.5 / 1010.0 / 0.01) and
  near(r6['OR15.BRK.AM'][1][0], 1.5) and
  near(r6['OR15.BRK.AM'][4][0], 9.0) and
  near(r6['OR15.BRK.AM'][4][1], 0.05) and
  near(r6['RND.BRK.PM'][4][0], (f.C[NG - 1] - f.C[R0 + 355]) /
       f.C[R0 + 355] / 0.01) and
  near(r6['RND.BRK.PM'][0][0], gross(R0 + 355, 15)) and
  [x[2] for x in r6['SW5.REJ.AM']] == [1] * 5 and
  [x[2] for x in r6['SW5.REJ.PM']] == [1] * 5 and
  [x[2] for x in r6['ASIA.RET.EU']] == [1] * 4 and
  near(r6['ASIA.RET.EU'][0][0], 0.0) and len(r6['EUR.FBK.PRE']) == 3 and
  V.family_of(R0 + 119, 'HRX', 'BRK') == 'HRX.BRK.AM' and
  V.family_of(R0 + 120, 'HRX', 'BRK') == 'HRX.BRK.PM')

# ---------------------------------------------------------------------
# L7: the squeeze
# ---------------------------------------------------------------------
f = flat_full(100.0)
f.H[R0 + 20], f.L[R0 + 25] = 102.0, 98.0
f.C[R0 + 40] = f.H[R0 + 40] = 102.25
f.C[R0 + 42] = f.H[R0 + 42] = 102.5
f.C[R0 + 45] = f.L[R0 + 45] = 97.5
hist = [[10.0] * (V.PM_END - V.SQZ_BARS) for _ in range(14)]
q7 = V.sqz_signals(f, V.widths(f), hist)
fw = flat_full(100.0)
fw.H[R0 + 35] = 106.0
fw.C[R0 + 40] = fw.H[R0 + 40] = 107.0
wd7 = V.widths(f)
t('L7: the squeeze is a close out of the last 30 bars\' range while '
  'that range is under half its median at that minute over the 14 '
  'sessions before; once a side a session',
  wd7[10] == (102.0, 98.0) and wd7[0] == (102.0, 98.0) and
  len(wd7) == 330 and
  q7 == [(R0 + 40, 'SQZ', 'BRK', 1), (R0 + 45, 'SQZ', 'BRK', -1)] and
  V.sqz_signals(fw, V.widths(fw), hist) == [])

# ---------------------------------------------------------------------
# L8: the overnight ranges
# ---------------------------------------------------------------------
f = flat_full(100.0)
f.H[100], f.L[200] = 101.0, 99.0
bar(f, 500, 101.2, h=101.5)
bar(f, 850, 99.5)
bar(f, 860, 100.5)
t('L8: the Asian range (18:00-02:00) is tested from 02:00 to 08:00 and '
  'the European range (02:00-08:00) from 08:00 to 09:30, by the same '
  'machine',
  V.on_signals(f) == [(500, 'ASIA', 'BRK', 1), (850, 'EUR', 'BRK', -1),
                      (860, 'EUR', 'FBK', 1)] and
  V.family_of(500, 'ASIA', 'BRK') == 'ASIA.BRK.EU' and
  V.family_of(850, 'EUR', 'BRK') == 'EUR.BRK.PRE')

# ---------------------------------------------------------------------
# L9: EPROP
# ---------------------------------------------------------------------
ch9 = [dict(session=x, close=c, high=h, low=lo) for x, c, h, lo in (
    ('20210104', 100.5, 110.0, 100.0),       # IBS 0.05: bought
    ('20210105', 105.0, 110.0, 100.0),
    ('20210106', 109.5, 110.0, 100.0),       # 0.95: sold
    ('20210107', 100.2, 110.0, 100.0),       # bought
    ('20210108', 105.0, 105.0, 105.0),       # no range: still long
    ('20210111', 109.9, 110.0, 100.0),       # sold
    ('20210112', 105.0, 110.0, 100.0))]
d9 = dict(sessions=['a', 'b', 'c'], weeks=['w1', 'w1', 'w2'],
          A=[0.0] * 3, B=[0.0] * 3, fam={},
          eprop=[(True, 0.01, 0.0001, 0.01, True),
                 (False, 0.02, 0.0001, 0.01, True),
                 (True, -0.005, 0.0001, 0.02, True)])
b9 = V.eprop_bench(d9)
x9, m9, n9 = V.series(d9, 'EPROP', b9)
t('L9: EPROP is long every session from the day after E buys to the day '
  'E sells, a day without a range included; its result is the session\'s '
  'return less the cost and less the mean session, in R',
  V.eprop_sessions(ch9) == {'20210105', '20210106', '20210108',
                            '20210111'} and
  near(b9, 0.025 / 3) and n9 == 2 and
  near(x9[0], (0.01 - 0.0001 - b9) / 0.01) and x9[1] == 0.0 and
  near(x9[2], (-0.005 - 0.0001 - b9) / 0.02) and near(m9[0], S.mean(x9)))

# ---------------------------------------------------------------------
# L10: the statistics
# ---------------------------------------------------------------------
rng = random.Random(4)
a10 = [rng.gauss(0, 1) for _ in range(60)]
b10 = [rng.gauss(0, 1) + 0.3 * u for u in a10]
x10 = [1.0 + 2.0 * u - 3.0 * v for u, v in zip(a10, b10)]
sl = V.slopes(x10, a10, b10)
sl_flat = V.slopes([3.0 * u for u in a10], a10, [0.5] * 60)
wt = V.weekly_t([1, 2, 3, -1, 4, 0], ['a', 'a', 'b', 'b', 'c', 'c'])
wn = V.weekly_t([-1, -2, -3, 1, -4, 0], ['a', 'a', 'b', 'b', 'c', 'c'])
p2 = DI.t_p_two_sided(3.0 * math.sqrt(3.0), 2)
t('L10: the slopes on A and B are the least-squares ones; t is the mean '
  'of the weekly sums over its standard error, p one-sided from '
  'Student\'s t; under three weeks there is none',
  near(sl[0], 2.0, 1e-9) and near(sl[1], -3.0, 1e-9) and
  near(sl_flat[0], 3.0, 1e-9) and sl_flat[1] == 0.0 and
  near(wt['t'], 3.0 * math.sqrt(3.0)) and wt['weeks'] == 3 and
  near(wt['p'], p2 / 2.0) and near(wn['t'], -3.0 * math.sqrt(3.0)) and
  near(wn['p'], 1.0 - p2 / 2.0) and
  V.weekly_t([1, 2], ['a', 'b'])['t'] is None and
  V.weekly_t([1, 1, 1], ['a', 'b', 'c'])['t'] is None)


# ---------------------------------------------------------------------
# L11: the two stages on built data
# ---------------------------------------------------------------------
def built(n_weeks, spec, seed=1, a_mean=0.05):
    """A set of 5 sessions a week; spec: {family: per-hold lists of the
    daily results its own direction makes (None: no trade that day)}."""
    r = random.Random(seed)
    n = 5 * n_weeks
    data = dict(sessions=['s%04d' % k for k in range(n)],
                weeks=['w%03d' % (k // 5) for k in range(n)],
                A=[a_mean + r.gauss(0, 0.5) for _ in range(n)],
                B=[0.02 + r.gauss(0, 0.5) for _ in range(n)],
                fam={}, eprop=[(False, 0.0, 0.0, 0.01, True)] * n)
    for fid, holds in spec.items():
        for k in range(n):
            if holds[0][k] is None:
                continue
            data['fam'].setdefault(fid, {})[k] = [
                (h[k] + 0.01, 0.01, 1) for h in holds]
    return data


r11 = random.Random(7)
N11 = 200
good = [0.05 + r11.gauss(0, 0.2) for _ in range(N11)]
few = [good[k] if k % 4 == 0 else None for k in range(N11)]
hi_ = [0.30 + r11.gauss(0, 0.2) for _ in range(N11)]
lo_ = [-0.10 + r11.gauss(0, 0.2) for _ in range(N11)]
d11 = built(40, {
    'PDC.BRK.AM': [good] * 5,
    'RND.BRK.AM': [few] * 5,
    'SW5.BRK.AM': [hi_, hi_, lo_, lo_, lo_]})
copy_a = [2.0 * u + r11.gauss(0, 0.01) for u in d11['A']]
for k in range(N11):
    d11['fam'].setdefault('OPN.REJ.PM', {})[k] = [
        (copy_a[k] + 0.01, 0.01, 1)] * 5
rows11, ids11, bench11 = V.stage1(d11)
by11 = {r['id']: r for r in rows11}
many = {}
for n_, g_ in enumerate(V.INNER):
    for e_ in ('BRK', 'REJ'):
        many['%s.%s.AM' % (g_, e_)] = [[0.05 + 0.004 * n_ +
                                        r11.gauss(0, 0.1)
                                        for _ in range(N11)]] * 5
rows_m, ids_m, _b = V.stage1(built(40, many, seed=3))
elig_m = sorted((r for r in rows_m if r['eligible']),
                key=lambda r: (-r['t'], r['id']))
lock11 = built(40, {
    'PDC.BRK.AM': [[0.05 + r11.gauss(0, 0.2) for _ in range(N11)]] * 5,
    'HRX.BRK.AM': [[r11.gauss(0, 0.2) for _ in range(N11)]] * 5,
    'IB60.RET.PM': [[-0.05 + r11.gauss(0, 0.2) for _ in range(N11)]] * 5},
    seed=9)
fwd11 = [dict(by11['PDC.BRK.AM']),
         dict(by11['HRX.BRK.AM'], beta_a=0.0, beta_b=0.0),
         dict(by11['IB60.RET.PM'], beta_a=0.0, beta_b=0.0)]
res11 = V.stage2(lock11, fwd11, bench11)
q11 = DI.bh_q([r['p'] for r in res11])
same_beta = V.assess(lock11, 'PDC.BRK.AM', bench11,
                     (by11['PDC.BRK.AM']['beta_a'],
                      by11['PDC.BRK.AM']['beta_b']))
t('L11: stage 1 forwards a hypothesis with 150 trades a strategy, a raw '
  'mean above 0, 60 % of its strategies above 0 and t at least 2.5, the '
  'twelve highest at most; a copy of A has no alpha; stage 2 uses stage '
  '1\'s slopes and confirms by Benjamini-Hochberg at 10 % with a raw '
  'mean above 0',
  ids11 == ['PDC.BRK.AM'] and by11['PDC.BRK.AM']['eligible'] and
  by11['PDC.BRK.AM']['trades'] == 200 and
  by11['PDC.BRK.AM~']['raw'] < 0 and not by11['PDC.BRK.AM~']['eligible']
  and by11['RND.BRK.AM']['trades'] == 50 and
  by11['RND.BRK.AM']['raw'] > 0 and not by11['RND.BRK.AM']['eligible'] and
  by11['SW5.BRK.AM']['raw'] > 0 and
  near(by11['SW5.BRK.AM']['positive'], 0.4) and
  by11['SW5.BRK.AM']['t'] > 2.5 and not by11['SW5.BRK.AM']['eligible'] and
  by11['OPN.REJ.PM']['raw'] > 0 and
  near(by11['OPN.REJ.PM']['beta_a'], 2.0, 0.01) and
  by11['OPN.REJ.PM']['corr_a'] > 0.99 and
  abs(by11['OPN.REJ.PM']['t']) < 2.5 and
  not by11['OPN.REJ.PM']['eligible'] and
  by11['EPROP']['t'] is None and len(rows11) == 181 and
  len(elig_m) == 16 and len(ids_m) == 12 and
  ids_m == [r['id'] for r in elig_m[:12]] and
  sum(1 for r in rows_m if r['forwarded']) == 12 and
  [r['q'] for r in res11] == q11 and
  [r['status'] for r in res11] == ['CONFIRMED', 'NOT CONFIRMED',
                                   'NOT CONFIRMED'] and
  res11[0]['q'] <= 0.10 and res11[2]['raw'] < 0 and
  res11[0]['beta_a'] == by11['PDC.BRK.AM']['beta_a'] and
  res11[0] == dict(same_beta, q=res11[0]['q'], status='CONFIRMED'))


# ---------------------------------------------------------------------
# a synthetic export: whole sessions from 18:00, with a planted effect
# ---------------------------------------------------------------------
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


def make_rows(first, last, seed, plant=0.5):
    """Every weekday: bars from 18:00 the evening before to 16:14, a
    random walk on the tick (quieter overnight). After the first close
    beyond the 09:30-09:45 range, the price drifts `plant` points a
    minute that way for an hour: a break of the 15-minute opening range
    that continues."""
    rng = random.Random(seed)
    px, out, d = 10000.0, [], first
    while d <= last:
        if d.weekday() < 5:
            eve = d - _dt.timedelta(days=1)
            orh = orl = None
            drift = left = 0
            for day, m in [(eve, x) for x in range(1080, 1440)] + \
                    [(d, x) for x in range(0, 975)]:
                rth = day == d and 570 <= m < 960
                step = rng.gauss(0, 2.0 if rth else 0.7)
                if left > 0:
                    step += drift * plant
                    left -= 1
                o = px
                px = round((px + step) * 4) / 4
                h, lo = max(o, px) + 0.25, min(o, px) - 0.25
                if day == d and 570 <= m < 585:
                    orh = h if orh is None else max(orh, h)
                    orl = lo if orl is None else min(orl, lo)
                elif day == d and 585 <= m < 900 and not drift:
                    if px > orh:
                        drift, left = 1, 60
                    elif px < orl:
                        drift, left = -1, 60
                v = 3000 if (rth and m == 570) else (900 if rth else 20)
                out.append('%s;%.2f;%.2f;%.2f;%.2f;%d' % (
                    stamp(day, m), o, h, lo, px, v))
        d += _dt.timedelta(days=1)
    return out


FN = os.path.join(WORK, 'nq')
os.makedirs(FN)
with open(os.path.join(FN, 'NQ 12-21.Last.txt'), 'w') as fh:
    fh.write('\n'.join(make_rows(D(2020, 3, 2), D(2021, 6, 4), 21)) + '\n')
rdN, _chk = W25.read(FN, 'NQ')
dN, oN, cN = S.build(rdN)
fulls = list(V.sessions(rdN, dN, oN, cN))
byf = {f.session: f for f in fulls}

# ---------------------------------------------------------------------
# L12: the grid is wave twenty-four's session, and more
# ---------------------------------------------------------------------
biN = W26.b_inputs(dN, oN, cN)
ok_grid = len(fulls) >= 280
for k, f in enumerate(fulls):
    d = dN[f.session]
    ok_grid = ok_grid and list(f.C[R0:]) == d.c and list(f.H[R0:]) == d.h \
        and list(f.L[R0:]) == d.l and list(f.V[R0:]) == d.v and \
        f.C[R0 - 1] == d.o and f.pdc == d.pc and f.first == 0 and \
        f.on_ok and f.week == V.week_label(V._date(f.session)) and \
        f.lock == V.is_lockbox(f.week) and \
        (f.session not in biN or f.sig == biN[f.session][1])
    if k and fulls[k - 1].session == [r['prev'] for r in cN
                                      if r['session'] == f.session][0]:
        pf = fulls[k - 1]
        ok_grid = ok_grid and f.pdh == max(pf.H[R0:]) and \
            f.pdl == min(pf.L[R0:])
wk = V.week_ranges(rdN)['NQ 12-21']
f0 = fulls[40]
prev_lab = V.week_label(V._date(f0.session) - _dt.timedelta(days=7))
in_prev = [x for x in fulls if x.week == prev_lab]
t('L12: on an export the grid\'s cash session is wave twenty-four\'s bar '
  'for bar, with its open and yesterday\'s close; yesterday\'s high and '
  'low, last week\'s (whole sessions) and s are the reader\'s own',
  ok_grid and len(in_prev) == 5 and
  f0.pwh == max(max(x.H) for x in in_prev) and
  f0.pwl == min(min(x.L) for x in in_prev) and
  (f0.pwh, f0.pwl) == tuple(wk[prev_lab]) and
  0.4 < sum(1 for x in fulls if x.lock) / float(len(fulls)) < 0.6)

# ---------------------------------------------------------------------
# L13: nothing looks ahead
# ---------------------------------------------------------------------


def cut_copy(f, cut):
    g = V.Full()
    for name in V.Full.__slots__:
        setattr(g, name, getattr(f, name))
    g.C, g.H, g.L = (array.array('d', x) for x in (f.C, f.H, f.L))
    for i in range(cut, NG):
        g.C[i] = g.H[i] = g.L[i] = f.C[cut - 1]
    return g


hist13 = [[hi - lo for hi, lo in V.widths(x)] for x in fulls[20:34]]
causal, seen13 = True, collections.Counter()
for f in fulls[34:94]:
    for cut in (R0 + 90, R0 + 200):
        g = cut_copy(f, cut)
        a = [x for x in V.rth_signals(f) if x[0] < cut]
        causal = causal and a == [x for x in V.rth_signals(g)
                                  if x[0] < cut]
        causal = causal and [x for x in V.sqz_signals(
            f, V.widths(f), hist13) if x[0] < cut] == [
            x for x in V.sqz_signals(g, V.widths(g), hist13) if x[0] < cut]
        if cut == R0 + 200:
            seen13.update((x[1], x[2]) for x in a)
            ra = V.day_results(f, [x for x in a if x[0] + 16 <= cut], 0.5)
            rb = V.day_results(g, [x for x in a if x[0] + 16 <= cut], 0.5)
            causal = causal and all(ra[k][0] == rb[k][0] for k in ra)
    g = cut_copy(f, 700)
    causal = causal and [x for x in V.on_signals(f) if x[0] < 700] == [
        x for x in V.on_signals(g) if x[0] < 700]
groups13 = {g for g, _e in seen13}
t('L13: when every bar after a moment is replaced, no signal before that '
  'moment changes, in the cash session, the squeeze or the overnight '
  'ranges, and no trade that ended before it; every level group and '
  'event occurs on the export',
  causal and groups13 >= {'PDX', 'ONX', 'PWX', 'PDC', 'OPN', 'OR15',
                          'IB60', 'HRX', 'RND', 'SW5', 'SW15'} and
  {e for _g, e in seen13} == set(V.EVENTS))

# ---------------------------------------------------------------------
# L14: the two stages on the export, the lockbox once
# ---------------------------------------------------------------------
led = os.path.join(WORK, 'ledger.json')
out_d, out_l = (os.path.join(WORK, x) for x in ('w27_d.json', 'w27_l.json'))
V.MIN_TRADES = 40                    # the export is 15 months, not 10 years
try:
    rc_d, said_d = said_by(lambda: V.main([FN, '--out', out_d], ledger=led))
    rc_d2, _x = said_by(lambda: V.main([FN], ledger=led))
    rc_l, said_l = said_by(lambda: V.main([FN, '--lockbox', '--out', out_l],
                                          ledger=led))
    rc_l2, said_l2 = said_by(lambda: V.main([FN, '--lockbox'], ledger=led))
    with W25.costs('NQ') as c14:
        disc = V.compute(rdN, dN, oN, cN, c14['rt'])
        lock = V.compute(rdN, dN, oN, cN, c14['rt'], True,
                         {'OR15.BRK.AM'})
finally:
    V.MIN_TRADES = 150
rep_d, rep_l = json.load(open(out_d)), json.load(open(out_l))
rows_d = {r['id']: r for r in rep_d['rows']}
ledr = json.load(open(led))['reads']
x_or, _m, n_or = V.series(disc, 'OR15.BRK.AM')
rc_no, said_no = said_by(lambda: V.main(
    [os.path.join(WORK, 'no_such_folder')], ledger=led))
t('L14: stage 1 computes the discovery weeks alone and forwards the '
  'planted break of the 15-minute range, not its mirror; the lockbox, '
  'read once and recorded, confirms it; a second lockbox read is '
  'refused; stage 1 may be repeated',
  rc_d == 0 and rc_d2 == 0 and rc_l == 0 and rc_l2 == 2 and
  'REFUSED: the lockbox weeks have been read' in said_l2 and
  rep_d['part'] == 'discovery' and 'lockbox' not in rep_d and
  rep_d['strategies'] == 877 and rep_d['hypotheses'] == 181 and
  len(rep_d['rows']) == 181 and
  all(not V.is_lockbox(w) for w in disc['weeks']) and
  all(V.is_lockbox(w) for w in lock['weeks']) and
  len(disc['sessions']) + len(lock['sessions']) == len(fulls) and
  disc['other'] == len(lock['sessions']) and
  rep_d['discovery']['sessions'] == len(disc['sessions']) and
  rep_d['lockbox_sessions'] == len(lock['sessions']) and
  set(lock['fam']) == {'OR15.BRK.AM'} and
  'OR15.BRK.AM' in rep_d['forwarded'] and
  'OR15.BRK.AM~' not in rep_d['forwarded'] and
  rows_d['OR15.BRK.AM']['t'] >= 2.5 and rows_d['OR15.BRK.AM~']['raw'] < 0
  and near(rows_d['OR15.BRK.AM']['raw'], S.mean(x_or)) and
  near(rows_d['OR15.BRK.AM']['trades'], n_or) and
  len(rep_d['forwarded']) <= 12 and
  rep_l['forwarded'] == rep_d['forwarded'] and
  'OR15.BRK.AM' in rep_l['lockbox']['confirmed'] and
  [r['id'] for r in rep_l['lockbox']['rows']] == rep_d['forwarded'] and
  all((r['status'] == 'CONFIRMED') == (r['q'] is not None and
                                       r['q'] <= 0.10 and r['raw'] > 0)
      for r in rep_l['lockbox']['rows']) and
  [(r['part'], r['market']) for r in ledr] == [
      ('discovery', 'NQ'), ('discovery', 'NQ'), ('lockbox', 'NQ')] and
  'Stage 1, discovery weeks' in said_d and '*** LOCKBOX' in said_l and
  'CONFIRMED: ' in said_l and '*** LOCKBOX' not in said_d and
  rc_no == 2 and 'STOPPED: ' in said_no and
  (S.RT, S.RT_STOP, S.SIDE) == (0.5, 0.75, 0.25) and
  CX.REFUSE_FROM == '20260701')

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
