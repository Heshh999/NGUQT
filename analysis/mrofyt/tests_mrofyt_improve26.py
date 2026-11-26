#!/usr/bin/env python3
# MROF-YT-W26-IMPROVE-1.0 suite. A against wave twenty-four's own
# trade_a, the three changes, B's inputs against rule_b, the prop sizing,
# the day's path with and without the daily stop, the account with its
# failures, and the reads, the verdict and the ledger end to end on
# synthetic NinjaTrader-format exports. Synthetic data verifies CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import datetime as _dt
import io
import json
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
import mrofyt_improve26 as I         # noqa: E402
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


WORK = tempfile.mkdtemp(prefix='mrofyt_w26_')
N = S.N_MIN
D = _dt.date
REG = ' '.join(open(os.path.join(HERE, I.REGISTRATION),
                    encoding='utf-8').read().split())


def mk(session, o, pc, closes, highs=None, lows=None, vols=None):
    c = list(closes) + [closes[-1]] * (N - len(closes))
    h = list(highs) + c[len(highs):] if highs else list(c)
    lo = list(lows) + c[len(lows):] if lows else list(c)
    v = list(vols) + [1.0] * (N - len(vols)) if vols else [1.0] * N
    return S.Day(session, 'NQ 12-21', o, pc, c, h, lo, v)


def flat(session, o, pc, marks, vols=None):
    c, last = [], o
    for j in range(1, N + 1):
        last = marks.get(j, last)
        c.append(last)
    return mk(session, o, pc, c, vols=vols)


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
    minutes (against it when negative); one stray bar on every Saturday
    and Sunday."""
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


def write(folder, name, rows, keep=None):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), 'w') as fh:
        fh.write('\n'.join(r for d, r in rows
                           if keep is None or keep(d)) + '\n')
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

# ---------------------------------------------------------------------
# I1: A is wave twenty-four's trade_a
# ---------------------------------------------------------------------
KEYS = ('session', 'gross', 'cost', 'how', 'lev')


def same(a, b):
    return [tuple(x[k] for k in KEYS) for x in a] == \
        [tuple(x[k] for k in KEYS) for x in b]


mine_nq, own_nq = I.rule_a(dN, oN), S.rule_a(dN, oN)[0]
with W25.costs('RTY'):
    mine_r, own_r = I.rule_a(dN, oN), S.rule_a(dN, oN)[0]
t('I1: without a change, a_core is wave twenty-four\'s trade_a trade for '
  'trade, under NQ\'s costs and under another market\'s tick and costs',
  len(own_nq) >= 300 and same(mine_nq, own_nq) and same(mine_r, own_r) and
  any(x['how'] == 'STOP' for x in own_nq) and
  all(x['exit_j'] == N for x in mine_nq if x['how'] == 'CLOSE'))

# ---------------------------------------------------------------------
# I2: A1, busy opens only
# ---------------------------------------------------------------------
ses = ['202101%02d' % k for k in range(4, 20)]
up = [100.25, 100.5, 100.75, 101.0, 101.25]
lows5 = [99.0, 100.0, 100.25, 100.5, 100.75]
d1 = {}
for k, s in enumerate(ses):
    v5 = 10.0 if k == 14 else 5.0
    d1[s] = mk(s, 100.0, 99.0, up + [101.5], lows=lows5,
               vols=[v5 / 5] * 5)
a1 = I.rule_a1(d1, ses)
t('I2: A1 trades only when the first five minutes\' volume is above its '
  'mean over the 14 sessions before, and not before there are 14',
  [x['session'] for x in a1] == [ses[14]] and
  same(a1, [S.trade_a(d1[ses[14]])]))

# ---------------------------------------------------------------------
# I3: A2, the stop from the normal day
# ---------------------------------------------------------------------
ch3 = []
for k, s in enumerate(ses):
    ch3.append(dict(session=s, contract='NQ 12-21', close=100.0,
                    high=110.0 if k < 15 else 150.0, low=100.0, ret=0.0,
                    prev=ch3[-1]['session'] if ch3 else None))
dr = I.normal_range(ch3)
d3 = {s: mk(s, 100.0, 99.0, up + [101.5, 100.5], lows=lows5 + [101.0, 100.0])
      for s in ses}
a2 = I.rule_a2(d3, ses, ch3)
x2 = [x for x in a2 if x['session'] == ses[14]][0]
x2b = [x for x in a2 if x['session'] == ses[15]][0]
t('I2b/I3: A2\'s risk is 10 % of the mean cash range of the 14 trading '
  'days before (none before 14); its own stop and 10 R target, the '
  'source\'s sizing on that risk',
  sorted(dr) == ses[14:] and near(dr[ses[14]], 10.0) and
  near(dr[ses[15]], 10.0) and
  [x['session'] for x in a2] == ses[14:] and
  x2['how'] == 'STOP' and near(x2['exit_px'], 100.25) and
  near(x2['gross'], -1.0 / 101.25) and near(x2['risk'], 1.0) and
  near(x2['lev'], min(0.01 / (1.0 / 101.25), 4.0)) and
  near(x2['cost'], 0.75 / 101.25) and x2b['how'] == 'STOP')

# ---------------------------------------------------------------------
# I4: A3, out when B is against it
# ---------------------------------------------------------------------
sig = [0.001] * (N + 1)
d4 = flat('20210104', 100.0, 100.0, {1: 100.25, 2: 100.5, 3: 100.75,
                                     4: 101.0, 5: 101.25, 10: 99.5,
                                     40: 99.25})
d4.l[:5] = [99.0] * 5
d4b = flat('20210104', 100.0, 100.0, {1: 100.25, 2: 100.5, 3: 100.75,
                                      4: 101.0, 5: 101.25, 10: 102.0})
d4b.l[:5] = [99.0] * 5
x4, y4 = I.a_core(d4, sigma=sig), I.a_core(d4)
x4b = I.a_core(d4b, sigma=sig)
t('I4: A3 closes a long A at the first of B\'s times when B\'s rule is '
  'short (P below the lower bound and VWAP), at P and a plain round trip; '
  'when B is with A or flat, A3 is A',
  I.b_want(d4, sig, 30) == -1 and x4['how'] == 'B' and x4['exit_j'] == 30
  and near(x4['gross'], (99.5 - 101.25) / 101.25) and
  near(x4['cost'], 0.5 / 101.25) and
  y4['how'] == 'CLOSE' and near(y4['gross'], (99.25 - 101.25) / 101.25) and
  I.b_want(d4b, sig, 30) == 1 and
  same([x4b], [S.trade_a(d4b)]) and same([I.a_core(d4b)], [x4b]))

# ---------------------------------------------------------------------
# I5: B's inputs are rule_b's
# ---------------------------------------------------------------------
bi = I.b_inputs(dN, oN, cN)
own_b = S.rule_b(dN, oN, cN)[0]
mine_b = []
for s in oN:
    if s in bi:
        g, c, n = S.day_b(dN[s], bi[s][0])
        if n:
            mine_b.append((s, g, c, min(0.02 / bi[s][1], 4.0)))
a3n = I.rule_a3(dN, oN, cN)
t('I5: B\'s bounds and volatility rebuilt here give rule_b\'s days, '
  'results and sizing exactly; on the export every A3 trade B did not '
  'close is A\'s own trade',
  len(own_b) >= 100 and mine_b == [(x['session'], x['gross'], x['cost'],
                                    x['lev']) for x in own_b] and
  len(a3n) == len(mine_nq) and
  all(same([x], [y]) for x, y in zip(a3n, mine_nq) if x['how'] != 'B'))

# ---------------------------------------------------------------------
# I6: the prop sizing
# ---------------------------------------------------------------------
t('I6: A: floor(150 / (R x 2)) micros, B: round(500 / (s x O x 2)), each '
  'from 1 to 15; MNQ pays 1.00 a round trip and 1.25 on a stop',
  I.a_micros(10.0) == 7 and I.a_micros(200.0) == 1 and
  I.a_micros(1.0) == 15 and I.a_micros(37.5) == 2 and
  I.b_micros(0.01, 20000.0) == 1 and I.b_micros(0.01, 4500.0) == 6 and
  I.b_micros(0.001, 4500.0) == 15 and I.b_micros(0.05, 26000.0) == 1 and
  (I.MNQ_PT, I.MNQ_RT, I.MNQ_STOP) == (2.0, 1.0, 1.25) and
  (I.A_BUDGET, I.B_BUDGET, I.ACCOUNT, I.TRAIL, I.DAY_STOP) ==
  (150.0, 500.0, 150000.0, 4500.0, 1000.0))

# ---------------------------------------------------------------------
# I7: the day's path
# ---------------------------------------------------------------------
d7 = flat('20210104', 100.0, 100.0, {5: 100.0, 30: 101.0, 100: 102.0,
                                     390: 103.0})
a7 = dict(sg=1, entry=100.0, exit_px=99.0, exit_j=20, how='STOP', micros=2)
b7 = ([(30, 1), (390, -1)], 3)
r_a = I.day_path(d7, a7)
r_b = I.day_path(d7, None, b7)
r_ab = I.day_path(d7, a7, b7)
marks = {}
for j in range(N + 1):
    marks[j] = 1000.0 - 10.0 * max(0, j - 50)
d7s = flat('20210104', 1000.0, 1000.0, marks)
b7s = ([(30, 1), (390, -1)], 5)
r_s = I.day_path(d7s, None, b7s, I.DAY_STOP)
r_n = I.day_path(d7s, None, b7s)
t('I7: a day\'s dollars in MNQ: A\'s stop pays its move and 1.25, B pays '
  '1.00 a round trip a micro; together they add; the daily stop closes '
  'everything at the first minute close at or below -1,000',
  near(r_a[0], 2 * 2 * (-1.0 - 1.25)) and near(r_a[1], -9.0) and
  r_a[2] is None and
  near(r_b[0], 3 * 2 * (2.0 - 1.0)) and near(r_ab[0], r_a[0] + r_b[0]) and
  r_s[2] == 60 and near(r_s[0], 5 * 2 * (-100.0 - 1.0)) and
  near(r_n[0], 5 * 2 * (-3400.0 - 1.0)) and r_n[2] is None)

# ---------------------------------------------------------------------
# I8: the account
# ---------------------------------------------------------------------
days8, plan8 = {}, []
for k, (s, drop) in enumerate((('20210104', 0), ('20210105', 200),
                               ('20210106', 0))):
    m = {30: 1000.0, 200: 1000.0 - drop, 201: 1000.0, 300: 1034.0}
    days8[s] = flat(s, 1000.0, 1000.0, m)
    plan8.append((s, None, ([(30, 1), (390, -1)], 15)))
acc8 = I.account(days8, plan8)
one = 15 * 2 * (34.0 - 1.0)
t('I8: the account fails at a minute close 4,500 below its highest '
  'end-of-day value, and a new one starts the next day; the largest fall '
  'and the results by year count every day',
  acc8['fails'] == 1 and acc8['failed_on'] == ['20210105'] and
  near(acc8['result'], 3 * one) and
  near(acc8['largest_fall'], 15 * 2 * 200 + 15 * 2 * 0.5) and
  acc8['by_year']['2021'] == dict(result=round(3 * one, 2), fails=1,
                                  days=3) and
  near(acc8['b_alone'], 3 * one) and acc8['a_alone'] == 0.0)

# ---------------------------------------------------------------------
# I9: the reads, the verdict and the ledger
# ---------------------------------------------------------------------
led = os.path.join(WORK, 'ledger.json')
outs = {m: os.path.join(WORK, 'w26_%s.json' % m) for m in I.MARKETS}
rcN, saidN = said_by(lambda: I.main([FN, '--market', 'NQ', '--out',
                                     outs['NQ']], ledger=led))
rcE, saidE = said_by(lambda: I.main([FE, '--market', 'ES', '--out',
                                     outs['ES']], ledger=led))
rcR, saidR = said_by(lambda: I.main([FR, '--market', 'RTY', '--out',
                                     outs['RTY']], ledger=led))
rcE2, saidE2 = said_by(lambda: I.main([FE, '--market', 'ES'], ledger=led))
reps = {m: json.load(open(outs[m])) for m in I.MARKETS}
rcD, saidD = said_by(lambda: I.main(['--decide'] + [outs[m] for m in
                                                    I.MARKETS]))
dec = I.decide(list(reps.values()))
rcD2, saidD2 = said_by(lambda: I.main(['--decide', outs['NQ']]))
pr = reps['NQ']['prop']
with W25.costs('NQ'):
    ref = S.screen(dN, oN, cN)['rules']['A']
R2 = make_rows(D(2025, 6, 2), D(2026, 11, 20), 5, drift=0.6, share=0.5)
FL = write(os.path.join(WORK, 'later'), 'NQ 12-26.Last.txt', R2)
rcL, saidL = said_by(lambda: I.main([FL, '--later-months'], ledger=led))
rcL2, saidL2 = said_by(lambda: I.main([FL, '--later-months'], ledger=led))
ledr = json.load(open(led))['reads']
t('I9: NQ, ES and RTY are each read once and recorded; A in the report is '
  'wave twenty-four\'s verdict; NQ carries the prop account with and '
  'without the daily stop and what follows from it; the verdict needs '
  'all three markets; the later months are read once to 2026-11-13',
  rcN == rcE == rcR == 0 and rcE2 == 2 and 'REFUSED' in saidE2 and
  reps['NQ']['rules']['A']['halves'] == json.loads(json.dumps(
      ref['halves'])) and reps['NQ']['rules']['A']['status'] == ref['status']
  and list(reps['ES']['rules']) == ['A', 'A1', 'A2', 'A3'] and
  reps['RTY']['costs'] == dict(tick=0.1, round_trip=0.2, stop=0.3) and
  'prop' not in reps['ES'] and
  set(pr) >= {'without_day_stop', 'with_day_stop', 'keep_day_stop',
              'halve_budgets', 'for_step3'} and
  pr['halve_budgets'] == (pr['fails_kept'] > 1) and
  pr['for_step3']['A'] == (75.0 if pr['halve_budgets'] else 150.0) and
  'The $150,000 prop account' in saidN and
  rcD == 0 and 'GOES ON:' in saidD and set(dec['changes']) ==
  set(I.CHANGES) and
  all(v['status'] in ('DROPPED', 'ALTERNATIVE', 'BETTER THAN A')
      for v in dec['changes'].values()) and
  rcD2 == 2 and 'are needed' in saidD2 and
  rcL == 0 and '*** LATER MONTHS' in saidL and rcL2 == 2 and
  'REFUSED' in saidL2 and [(r['part'], r['market']) for r in ledr] ==
  [('market', 'NQ'), ('market', 'ES'), ('market', 'RTY'), ('2b', 'NQ')] and
  ledr[3]['last'] == '20261113' and CX.REFUSE_FROM == '20260701' and
  (S.RT, S.RT_STOP, S.SIDE) == (0.5, 0.75, 0.25))

# ---------------------------------------------------------------------
# I10: the decision rule, and the frozen registration
# ---------------------------------------------------------------------


def fake(market, a_pass, per):
    r = dict(market=market, rules={})
    for rule in ('A',) + I.CHANGES:
        ok = a_pass if rule == 'A' else per[rule][0]
        r['rules'][rule] = dict(status='PASS' if ok else 'FAIL',
                                per_session=per[rule][1] if rule != 'A'
                                else 1.0)
    return r


per = dict(A1=(True, 2.0), A2=(True, 0.5), A3=(False, 9.0))
dd = I.decide([fake(m, True, per) for m in I.MARKETS])
dd2 = I.decide([fake(m, m != 'RTY', dict(A1=(True, 3.0), A2=(True, 2.0),
                                         A3=(True, 1.5)))
                for m in I.MARKETS])
t('I10: a change passing on all three and better than A on ES and RTY '
  'goes on (the best of them); passing but not better is an alternative; '
  'failing anywhere drops it; nothing goes on while A itself fails; the '
  'registration\'s rules are the code\'s',
  dd['changes']['A1']['status'] == 'BETTER THAN A' and
  dd['changes']['A2']['status'] == 'ALTERNATIVE' and
  dd['changes']['A3']['status'] == 'DROPPED' and dd['goes_on'] == 'A1' and
  dd['a_passes_everywhere'] and dd2['goes_on'] == 'A1' and
  not dd2['a_passes_everywhere'] and dd2['note'] and
  all(x in REG for x in (
      'FROZEN on 2026-11-26', 'mean V5 of the 14 previous eligible sessions',
      'R = 0.10 × D', 'is closed at P(m) and pays the round trip',
      'higher than unchanged A\'s on **both ES and RTY**',
      'micros = floor(150 / (R × 2)), at least 1, at most 15',
      'micros = round(500 / (s × O × 2)), at least 1, at most 15',
      '4,500 dollars below its highest end-of-day value',
      'reaches −1,000 dollars', 'both budgets are halved',
      'costs at most 10 % of the total result',
      'A change can go on only if A itself passes wave twenty-five',
      'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
