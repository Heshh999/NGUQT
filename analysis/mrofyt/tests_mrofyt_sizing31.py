#!/usr/bin/env python3
# MROF-YT-W31-SIZING-1.0 suite. The frozen RVMR file checked and used
# unchanged, the bar each decision reads, RVMR's and ATR's states worked
# out by hand, B with its positions scaled against wave twenty-four's own
# day_b, A halved, the Sharpe and the fall by hand, a market's report
# against wave twenty-four's own A and B, the verdict on fabricated
# reports, and the reads and the ledger end to end on synthetic
# NinjaTrader-format exports. Synthetic data verifies CODE BEHAVIOR
# only, never market evidence. No order, fill or P&L exists.
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

import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_improve26 as W26       # noqa: E402
import mrofyt_screen15 as S          # noqa: E402
import mrofyt_sizing31 as Z          # noqa: E402

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


def stopped(fn):
    try:
        fn()
    except CX.ContextDataError as exc:
        return str(exc)
    return None


WORK = tempfile.mkdtemp(prefix='mrofyt_w31_')
N = S.N_MIN
D = _dt.date
REG = ' '.join(open(os.path.join(HERE, Z.REGISTRATION),
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
# Z1: the frozen RVMR file
# ---------------------------------------------------------------------
sha = Z.rvmr_unchanged()
frozen_src = open(Z.RVMR_SPEC, 'rb').read()
keep = Z.RVMR_SHA16
Z.RVMR_SHA16 = '0000000000000000'
e_hash = stopped(Z.rvmr_unchanged)
e_read = stopped(lambda: Z.run_market(os.path.join(WORK, 'nowhere'), 'NQ'))
Z.RVMR_SHA16 = keep
t('Z1: the RVMR used is the frozen file, imported and not copied; with '
  'any other file the tool stops before it reads a bar',
  sha.startswith('e348f035a9209540') and Z.RVMR_SHA16 == sha[:16] and
  Z.RV.T2 == 2.335 and Z.RV.W == 1440 and
  Z.RV.trailing_ratio.__module__ == 'rvmr_spec' and
  e_hash is not None and 'not the frozen RVMR file' in e_hash and
  e_read is not None and 'not the frozen RVMR file' in e_read)


# ---------------------------------------------------------------------
# Z2: the series and the bar each decision reads
# ---------------------------------------------------------------------
class FakeReader(object):
    def __init__(self, days):
        self.days = days


def session_bars(keys, ranges, close=100.0):
    b = array.array('d')
    for k, r in zip(keys, ranges):
        b.extend((k, close + r / 2.0, close - r / 2.0, close))
    return dict(bars=b)


O = S.OPEN_S
k1 = [-6 * 3600, -6 * 3600 + 60, O - 60, O, O + 60, O + 120, O + 240]
fr = FakeReader({('NQ 12-21', '20210104'): session_bars(
    list(reversed(k1)), [1, 2, 3, 4, 5, 6, 7]),
    ('NQ 03-22', '20210105'): session_bars([-6 * 3600, O], [8, 9]),
    ('NQ 12-21', '20210105'): session_bars([O], [99])})
ch2 = [dict(session='20210104', contract='NQ 12-21'),
       dict(session='20210105', contract='NQ 03-22')]
rows2, where2 = Z.series(fr, ch2)
t('Z2: the front contract\'s bars of each trading day in time order, the '
  'night first; a decision reads the last bar that ended at or before it '
  '(a missing minute reads the bar before); a session without the bars '
  'reads nothing',
  [r[0] for r in rows2] == sorted(k1) + [-6 * 3600, O] and
  [round(r[1] - r[2], 9) for r in rows2] == [7, 6, 5, 4, 3, 2, 1, 8, 9]
  and where2['20210105'][:2] == (7, 9) and
  Z.decision_row(where2, '20210104', 1) == 3 and
  Z.decision_row(where2, '20210104', 2) == 4 and
  Z.decision_row(where2, '20210104', 4) == 5 and
  Z.decision_row(where2, '20210104', 5) == 6 and
  Z.decision_row(where2, '20210104', 0) == 2 and
  Z.decision_row(where2, '20210106', 5) is None and
  Z.decision_row({'x': (0, 0, [])}, 'x', 5) is None)

# ---------------------------------------------------------------------
# Z3: RVMR's and ATR's states by hand
# ---------------------------------------------------------------------
# 16 sessions, a bar every minute 08:00-15:59 (480 bars), close 100, a
# range of 1 everywhere except: on session 15 the 20 bars to 09:35 have
# a range of 2 and the bar ending at 09:35 a range of 3; on session 16
# the 20 bars to 09:35 have 1.4.
ses3 = ['202102%02d' % d for d in range(1, 17)]
keys3 = list(range(8 * 3600, 16 * 3600, 60))
day3 = {}
for n, s in enumerate(ses3, 1):
    rg = [1.0] * len(keys3)
    for i, k in enumerate(keys3):
        if O + 4 * 60 - 19 * 60 <= k <= O + 4 * 60:
            if n == 15:
                rg[i] = 3.0 if k == O + 4 * 60 else 2.0
            elif n == 16:
                rg[i] = 1.4
    day3[('NQ 03-21', s)] = session_bars(keys3, rg)
ch3 = [dict(session=s, contract='NQ 03-21') for s in ses3]
st3 = Z.states(FakeReader(day3), ch3, ses3)
a15, a16, a14 = st3[ses3[14]][5], st3[ses3[15]][5], st3[ses3[13]][5]
want15 = (19 * 2.0 + 3.0) / 20.0
# the 1,440 bars before each 09:35 bar: 94 of its own session (19 of
# them at 09:15-09:33), the rest from the sessions before
score15 = 3.0 / ((1421 * 1.0 + 19 * 2.0) / 1440.0)
score16 = 1.4 / ((866 + 460 + 75 + 19 * 2.0 + 3.0 + 19 * 1.4) / 1440.0)
t('Z3: at 09:35 RVMR\'s score is the bar\'s range over the mean of the '
  '1,440 bars before it, HIGH above 2.335; ATR is the 20-bar true range '
  'against its mean at that minute on the 14 sessions before, HIGH at '
  '1.5 times; without 14 sessions or 1,440 bars there is no state',
  st3[ses3[0]][5]['score'] is None and st3[ses3[0]][5]['rvmr'] is None and
  a14['usual'] is None and a14['ratio'] is None and
  near(a15['atr'], want15) and near(a15['usual'], 1.0) and
  near(a15['ratio'], want15) and Z.high('ATR', a15) and
  near(a15['score'], score15) and a15['rvmr'] == 'HIGH' and
  Z.high('RVMR', a15) and near(a16['score'], score16) and
  near(a16['usual'], (13 * 1.0 + want15) / 14.0) and
  near(a16['ratio'], 1.4 / ((13 * 1.0 + want15) / 14.0)) and
  not Z.high('ATR', a16) and a16['rvmr'] == 'MEDIUM' and
  not Z.high('RVMR', a16) and
  Z.factor('UNCHANGED', a15) == 1.0 and Z.factor('ATR', a15) == 0.5 and
  Z.factor('RVMR', a16) == 1.0 and set(st3[ses3[3]]) == set(Z.DECISIONS))

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
# Z4: B with its positions scaled
# ---------------------------------------------------------------------
same_b = all(Z.day_b_scaled(dN[s], biN[s][0], lambda j: 1.0) ==
             S.day_b(dN[s], biN[s][0]) for s in oN if s in biN)
half_b = all(
    near(Z.day_b_scaled(dN[s], biN[s][0], lambda j: 0.5)[0],
         0.5 * S.day_b(dN[s], biN[s][0])[0], 1e-15) and
    near(Z.day_b_scaled(dN[s], biN[s][0], lambda j: 0.5)[1],
         0.5 * S.day_b(dN[s], biN[s][0])[1], 1e-15)
    for s in oN if s in biN)
# by hand: B buys at 10:30 (1008), sells to flat at 13:00 (1001)
MARKS = {35: 1004.0, 46: 1005.0, 51: 1006.0, 56: 1008.0, 62: 1007.0,
         196: 1005.0, 201: 1003.0, 206: 1001.0, 213: 1001.5}
d4 = flat('20210104', 1000.0, 1000.0, MARKS)
sg4 = [0.002] * (N + 1)
h4 = Z.day_b_scaled(d4, sg4, lambda j: 0.5 if j == 60 else 1.0)
# a reversal: long at full size, then short at half size
REV = {35: 1004.0, 56: 1008.0, 200: 995.0, 250: 990.0}
d5 = flat('20210105', 1000.0, 1000.0, REV)
r5 = Z.day_b_scaled(d5, sg4, lambda j: 0.5 if j == 210 else 1.0)
r5_full = S.day_b(d5, sg4)
t('Z4: with every factor 1 B is wave twenty-four\'s day_b on every '
  'session; at half size everything halves; by hand, a half-size long '
  'from 1008 to 1001 loses 3.5 points and pays 0.25; a full long turned '
  'into a half short pays for 1.5 contracts at the turn',
  same_b and half_b and len([s for s in oN if s in biN]) > 300 and
  near(h4[0], -3.5 / 1000.0, 1e-12) and near(h4[1], 0.25 / 1000.0, 1e-12)
  and h4[2] == 2 and r5_full[2] == 3 and
  near(r5[1], (0.25 * 1.0 + 0.25 * 1.5 + 0.25 * 0.5) / 1000.0, 1e-12) and
  near(r5[0], ((995.0 - 1008.0) * 1.0 + (995.0 - 990.0) * 0.5) / 1000.0,
       1e-12))

# ---------------------------------------------------------------------
# Z5: A halved
# ---------------------------------------------------------------------
stN = Z.states(rdN, cN, oN)
aU = Z.a_series(dN, oN, stN, 'UNCHANGED')
own_a = dict(S.nets('A', S.rule_a(dN, oN)[0], {}))
fake_st = {s: {j: dict(score=3.0 if k % 3 == 0 else 1.0,
                       rvmr='HIGH' if k % 3 == 0 else 'LOW',
                       atr=1.0, usual=1.0, ratio=1.6 if k % 4 == 0 else None)
               for j in Z.DECISIONS} for k, s in enumerate(oN)}
aR = dict(Z.a_series(dN, oN, fake_st, 'RVMR'))
aA = dict(Z.a_series(dN, oN, fake_st, 'ATR'))
t('Z5: A unchanged is wave twenty-four\'s own A, trade for trade, and 0 '
  'without a trade; under a measure a trade decided in a HIGH state is '
  'halved and no other; no state is full size',
  len(aU) == len(oN) and all(near(x, own_a.get(s, 0.0), 1e-9)
                              for s, x in aU) and
  all(near(aR[s], own_a.get(s, 0.0) * (0.5 if k % 3 == 0 else 1.0), 1e-9)
      for k, s in enumerate(oN)) and
  all(near(aA[s], own_a.get(s, 0.0) * (0.5 if k % 4 == 0 else 1.0), 1e-9)
      for k, s in enumerate(oN)) and
  sum(1 for s in oN if own_a.get(s)) > 300)

# ---------------------------------------------------------------------
# Z6: the numbers by hand
# ---------------------------------------------------------------------
pairs6 = [('20201201', 2.0), ('20201202', -1.0), ('20210104', 3.0),
          ('20210105', -2.0), ('20210106', 4.0)]
p6 = Z.perf(pairs6)
sd6 = math.sqrt(26.8 / 4.0)
sd_h2 = S.stdev([3.0, -2.0, 4.0])
t('Z6: the Sharpe is the mean over the standard deviation; the fall is '
  'the largest drop of the running sum (2 here) and its ratio the fall '
  'over the mean; each half has its own Sharpe; nothing without two '
  'sessions or a mean above 0',
  near(p6['mean'], 1.2) and near(p6['sd'], round(sd6, 5)) and
  near(p6['sharpe'], round(1.2 / sd6, 6)) and p6['fall'] == 2.0 and
  near(p6['fall_ratio'], round(2.0 / 1.2, 4)) and
  near(p6['halves']['H1'], round(0.5 / S.stdev([2.0, -1.0]), 6)) and
  near(p6['halves']['H2'], round((5.0 / 3.0) / sd_h2, 6)) and
  Z.perf([('20210104', 1.0)])['sharpe'] is None and
  Z.perf([('20210104', -1.0), ('20210105', -2.0)])['fall_ratio'] is None)

# ---------------------------------------------------------------------
# Z7: one market's report
# ---------------------------------------------------------------------
with W25.costs('NQ'):
    res7 = Z.judge_all(dN, oN, cN, rdN)
own_b = dict(S.nets('B', S.rule_b(dN, oN, cN)[0], {}))
bU = [(s, own_b.get(s, 0.0)) for s in oN if s in biN]
t('Z7: in a market\'s report the unchanged rules are wave twenty-four\'s '
  'own A and B; each rule is reported under each measure, with A and B '
  'together and how often each measure is HIGH; every setting is put '
  'back',
  res7['rules']['A']['UNCHANGED'] == Z.perf(aU) and
  res7['rules']['B']['UNCHANGED'] == Z.perf(bU) and
  list(res7['rules']) == ['A', 'B'] and
  all(list(v) == list(Z.RULES) for v in res7['rules'].values()) and
  list(res7['together']) == list(Z.RULES) and
  set(res7['high_share']) == {'ATR', 'RVMR'} and
  res7['high_share']['RVMR']['a_decisions'] == sum(
      1 for s in oN if own_a.get(s) is not None and s in own_a) and
  res7['high_share']['RVMR']['b_decisions'] > 200 and
  (S.RT, S.RT_STOP, S.SIDE) == (0.5, 0.75, 0.25) and
  CX.REFUSE_FROM == '20260701')


# ---------------------------------------------------------------------
# Z8: the verdict
# ---------------------------------------------------------------------
def rep8(market, a=None, b=None, version=None):
    """A market report as decide() reads it. a, b: {rule: (sharpe,
    fall ratio)}."""
    base = dict(UNCHANGED=(0.10, 10.0), ATR=(0.10, 10.0),
                RVMR=(0.10, 10.0))
    rules = {}
    for strat, given in (('A', a), ('B', b)):
        v = dict(base, **(given or {}))
        rules[strat] = {r: dict(sharpe=v[r][0], fall_ratio=v[r][1])
                        for r in Z.RULES}
    return dict(wave31=version or Z.W31_VERSION, part='market',
                market=market, rules=rules)


win_rv = dict(RVMR=(0.12, 8.0), ATR=(0.11, 9.0))
d1 = Z.decide([rep8('NQ'), rep8('ES', b=win_rv), rep8('RTY', b=win_rv)])
atr_rty = dict(RVMR=(0.12, 8.0), ATR=(0.13, 7.0))
d2 = Z.decide([rep8('ES', b=dict(RVMR=(0.12, 8.0), ATR=(0.11, 9.0))),
               rep8('RTY', b=atr_rty)])
d3 = Z.decide([rep8('ES', a=dict(ATR=(0.104, 8.0))),
               rep8('RTY', a=dict(ATR=(0.12, 8.0)))])
d4 = Z.decide([rep8('ES', a=dict(ATR=(0.12, 10.0))),
               rep8('RTY', a=dict(ATR=(0.12, 8.0)))])
d5 = Z.decide([rep8('ES', b=win_rv), rep8('RTY', b=win_rv)],
              passed=dict(A=True, B=False))
d6 = Z.decide([rep8('ES', b=dict(RVMR=(0.12, 8.0), ATR=(0.13, 10.0))),
               rep8('RTY', b=dict(RVMR=(0.12, 8.0), ATR=(0.13, 10.0)))])
t('Z8: a measure goes on when its Sharpe is 5 % higher and its fall '
  'ratio lower on both ES and RTY, RVMR only when it is at least as good '
  'as ATR on both (else ATR if it passes, else neither); a rule that '
  'failed wave twenty-five gets nothing; a missing, doubled or foreign '
  'report stops',
  d1['rules']['B']['goes_on'] == 'RVMR' and d1['rules']['A']['goes_on']
  is None and d1['rules']['B']['better'] == dict(ATR=True, RVMR=True) and
  'goes on only if B passes' in d1['rules']['B']['note'] and
  d2['rules']['B']['goes_on'] == 'ATR' and
  not d2['rules']['B']['rvmr_beats_atr'] and
  d3['rules']['A']['goes_on'] is None and
  not d3['rules']['A']['better']['ATR'] and
  d4['rules']['A']['goes_on'] is None and
  d5['rules']['B']['goes_on'] is None and
  'did not pass wave twenty-five' in d5['rules']['B']['note'] and
  d6['rules']['B']['goes_on'] is None and
  d6['rules']['B']['better']['RVMR'] and
  'are needed' in stopped(lambda: Z.decide([rep8('ES')])) and
  'two reports' in stopped(lambda: Z.decide([rep8('ES'), rep8('ES'),
                                             rep8('RTY')])) and
  'not a market report' in stopped(lambda: Z.decide(
      [rep8('ES', version='x'), rep8('RTY')])) and
  'GOES ON: RVMR' in Z.text(d1))

# ---------------------------------------------------------------------
# Z9: the reads and the ledger
# ---------------------------------------------------------------------
led = os.path.join(WORK, 'ledger.json')
outs = {m: os.path.join(WORK, 'w31_%s.json' % m) for m in Z.MARKETS}
rcN, saidN = said_by(lambda: Z.main([FN, '--market', 'NQ', '--out',
                                     outs['NQ']], ledger=led))
rcE, saidE = said_by(lambda: Z.main([FE, '--market', 'ES', '--out',
                                     outs['ES']], ledger=led))
rcR, saidR = said_by(lambda: Z.main([FR, '--market', 'RTY', '--out',
                                     outs['RTY']], ledger=led))
rcE2, saidE2 = said_by(lambda: Z.main([FE, '--market', 'ES'], ledger=led))
rcD, saidD = said_by(lambda: Z.main(['--decide'] + [outs[m] for m in
                                                    Z.MARKETS]))
rcD2, saidD2 = said_by(lambda: Z.main(['--decide', outs['ES']]))
Z.RVMR_SHA16 = '0000000000000000'
led2 = os.path.join(WORK, 'ledger2.json')
rcH, saidH = said_by(lambda: Z.main([FN, '--market', 'NQ'], ledger=led2))
Z.RVMR_SHA16 = keep
rcM, saidM = said_by(lambda: Z.main([FN, '--market', 'YM'], ledger=led))
rcW, saidW = said_by(lambda: Z.main(
    [FN, '--market', 'NQ', '--out', os.path.join(WORK, 'no', 'x.json')],
    ledger=os.path.join(WORK, 'ledger3.json')))
reps9 = {m: json.load(open(outs[m])) for m in Z.MARKETS}
ledr = json.load(open(led))['reads']
t('Z9: NQ, ES and RTY are each read once and recorded before anything is '
  'shown; the report from the command is the pieces\' own; the verdict '
  'needs ES and RTY; a changed RVMR file, an unknown market or a report '
  'that cannot be written stops with nothing recorded; the frozen RVMR '
  'file is untouched',
  rcN == rcE == rcR == 0 and rcE2 == 2 and 'REFUSED' in saidE2 and
  reps9['NQ']['rules'] == json.loads(json.dumps(res7['rules'])) and
  reps9['RTY']['costs'] == dict(tick=0.1, round_trip=0.2, stop=0.3) and
  'How often a decision is HIGH' in saidN and
  'read recorded (1 read(s)' in saidN and
  rcD == 0 and 'GOES ON:' in saidD and rcD2 == 2 and
  'are needed' in saidD2 and rcH == 2 and 'not the frozen RVMR' in saidH
  and not os.path.exists(led2) and rcM == 2 and rcW == 2 and
  'cannot be written' in saidW and
  not os.path.exists(os.path.join(WORK, 'ledger3.json')) and
  [(r['version'], r['market']) for r in ledr] ==
  [(Z.W31_VERSION, m) for m in Z.MARKETS] and
  open(Z.RVMR_SPEC, 'rb').read() == frozen_src)

# ---------------------------------------------------------------------
# Z10: the registration's rules are the code's
# ---------------------------------------------------------------------
t('Z10: the measures, the thresholds, the half, the 14 sessions, the 5 % '
  'and the markets judged are the frozen registration\'s',
  (Z.HALF, Z.ATR_HIGH, Z.USUAL_N, Z.SHARPE_GAIN, Z.A_MINUTE) ==
  (0.5, 1.5, 14, 1.05, 5) and Z.JUDGED_ON == ('ES', 'RTY') and
  Z.DECISIONS == (5,) + tuple(range(30, 361, 30)) and
  all(x in REG for x in (
      'FROZEN on 2026-11-27', 'sha256 beginning `e348f035a9209540`',
      '**HIGH** when the score is above 2.335',
      'the mean true range of the 20 bars ending at the decision bar',
      'on the 14 previous eligible sessions', 'at least **1.5 times**',
      'is taken at **half size**', 'at least 5 % higher',
      'its fall ratio is lower than UNCHANGED\'s',
      'the simpler tool wins a tie or a loss',
      '**only if that rule itself passes wave twenty-five**',
      'NQ\'s ten years are reported, never judged',
      'Explicitly NOT registered', 'Expected beforehand')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
