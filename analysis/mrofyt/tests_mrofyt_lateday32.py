#!/usr/bin/env python3
# MROF-YT-W32-LATEDAY-1.0 suite. B's twelve legs worked out by hand and
# against wave twenty-four's own day_b on every session, B from 14:00
# against the late legs, the tables by time of day and by age by hand,
# the Sharpe and the fall against wave thirty-one's, a market's report
# against wave twenty-four's own B, the verdict on fabricated reports,
# and the reads and the ledger end to end on synthetic NinjaTrader-format
# exports. Synthetic data verifies CODE BEHAVIOR only, never market
# evidence. No order, fill or P&L exists.
import collections
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

import mrofyt_clocks30 as C30        # noqa: E402
import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_improve26 as W26       # noqa: E402
import mrofyt_lateday32 as Y         # noqa: E402
import mrofyt_markets28 as W28       # noqa: E402
import mrofyt_screen15 as S          # noqa: E402
import mrofyt_sizing31 as Z31        # noqa: E402

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


WORK = tempfile.mkdtemp(prefix='mrofyt_w32_')
N = S.N_MIN
D = _dt.date
REG = ' '.join(open(os.path.join(HERE, Y.REGISTRATION),
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
# L1: the legs by hand
# ---------------------------------------------------------------------
# B buys at 10:30 (1008) and is flat at 13:00 (1001)
MARKS = {35: 1004.0, 46: 1005.0, 51: 1006.0, 56: 1008.0, 62: 1007.0,
         196: 1005.0, 201: 1003.0, 206: 1001.0, 213: 1001.5}
d1 = flat('20210104', 1000.0, 1000.0, MARKS)
sg = [0.002] * (N + 1)
lg1 = Y.legs(d1, sg)
want1 = {60: (1, 1, -1.0, 0.25), 90: (1, 2, 0.0, 0.0), 120: (1, 3, 0.0, 0.0),
         150: (1, 4, 0.0, 0.0), 180: (1, 5, -6.0, 0.25)}
# a reversal: long at 10:30 (1008), short at 13:00 (995), out at 16:00
REV = {35: 1004.0, 56: 1008.0, 200: 995.0, 250: 990.0}
d2 = flat('20210105', 1000.0, 1000.0, REV)
lg2 = Y.legs(d2, sg)
want2 = {60: (1, 1, 0.0, 0.25), 90: (1, 2, 0.0, 0.0), 120: (1, 3, 0.0, 0.0),
         150: (1, 4, 0.0, 0.0), 180: (1, 5, -13.0, 0.25),
         210: (-1, 1, 0.0, 0.25), 240: (-1, 2, 5.0, 0.0),
         270: (-1, 3, 0.0, 0.0), 300: (-1, 4, 0.0, 0.0),
         330: (-1, 5, 0.0, 0.0), 360: (-1, 6, 0.0, 0.25)}


def as_hand(lg, want):
    return all(
        (p, a) == want.get(j, (0, 0, 0.0, 0.0))[:2] and
        near(g * 1000.0, want.get(j, (0, 0, 0.0, 0.0))[2], 1e-9) and
        near(c * 1000.0, want.get(j, (0, 0, 0.0, 0.0))[3], 1e-9)
        for j, p, a, g, c in lg)


t('L1: B has twelve legs, 10:00 to 15:30; a leg carries the position '
  'times the change over it; an order\'s cost is split, what closes to '
  'the leg that ends, what opens to the leg that starts, the flat at '
  '16:00 to the last leg; the age counts half hours since the position '
  'was set and starts again at a reversal',
  [j for j, _p, _a, _g, _c in lg1] == list(S.B_TIMES) and len(lg1) == 12
  and as_hand(lg1, want1) and as_hand(lg2, want2) and
  Y.clock(30) == '10:00' and Y.clock(270) == '14:00' and
  Y.clock(360) == '15:30' and
  [Y.group_of(j) for j in (30, 240, 270, 360)] ==
  ['EARLY', 'EARLY', 'LATE', 'LATE'] and
  [Y.age_of(n) for n in (1, 2, 3, 4, 5, 9)] ==
  ['1', '2', '3-4', '3-4', '5+', '5+'])

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
sesN = [s for s in oN if s in biN]

# ---------------------------------------------------------------------
# L2: the legs add up to wave twenty-four's B
# ---------------------------------------------------------------------
adds, ages_ok, flat_ok = True, True, True
for s in sesN:
    lg = Y.legs(dN[s], biN[s][0])
    g0, c0, _n0 = S.day_b(dN[s], biN[s][0])
    adds = adds and near(sum(g for _j, _p, _a, g, _c in lg), g0, 1e-12) \
        and near(sum(c for _j, _p, _a, _g, c in lg), c0, 1e-12)
    prev_p, prev_a = 0, 0
    for _j, p, a, g, c in lg:
        if p == 0:
            flat_ok = flat_ok and a == 0 and g == 0.0 and c == 0.0
        else:
            ages_ok = ages_ok and a == (prev_a + 1 if p == prev_p else 1)
        prev_p, prev_a = p, a
tabN = Y.leg_table(dN, oN, biN)
own_b = dict(S.nets('B', S.rule_b(dN, oN, cN)[0], {}))
t('L2: on every session the twelve legs add up to wave twenty-four\'s '
  'day_b, gross and cost; in B\'s sizing they add up to its own result; '
  'a leg without a position carries nothing; the ages run 1, 2, 3 while '
  'the direction stays',
  adds and ages_ok and flat_ok and len(sesN) > 300 and
  list(tabN) == sesN and
  all(near(sum(x for _j, _p, _a, x in tabN[s]), own_b.get(s, 0.0), 1e-9)
      for s in sesN) and
  sum(1 for s in sesN if any(p for _j, p, _a, _x in tabN[s])) > 100)

# ---------------------------------------------------------------------
# L3: BL holds what B holds from 14:00
# ---------------------------------------------------------------------
same_g, same_c, carried = True, True, 0
for s in sesN:
    d, sigma = dN[s], biN[s][0]
    lg = Y.legs(d, sigma)
    late_g = sum(g for j, _p, _a, g, _c in lg if j >= Y.LATE_FROM)
    late_c = sum(c for j, _p, _a, _g, c in lg if j >= Y.LATE_FROM)
    pos = {j: p for j, p, _a, _g, _c in lg}
    carry = pos[270] != 0 and pos[240] == pos[270]
    carried += int(carry)
    g, c, _n, _late = C30.day(d, sigma, Y.BL_TIMES)
    same_g = same_g and near(g, late_g, 1e-12)
    same_c = same_c and near(c, late_c + (S.SIDE / d.o if carry else 0.0),
                             1e-12)
bl2 = C30.day(d2, sg, Y.BL_TIMES)
t('L3: BL decides at 14:00, 14:30, 15:00 and 15:30 only; on every '
  'session its gross is that of B\'s four late legs, and its cost theirs '
  'plus one entry at 14:00 when B was already in; on the reversal day it '
  'is short from 14:00 and pays to get in and out',
  Y.BL_TIMES == (270, 300, 330, 360) and same_g and same_c and
  carried > 30 and near(bl2[0], 0.0, 1e-12) and
  near(bl2[1], 0.5 / 1000.0, 1e-12) and bl2[2] == 2 and
  list(Y.RULES) == ['B', 'BL'] and Y.RULES['B'] == tuple(S.B_TIMES))


# ---------------------------------------------------------------------
# L4: the tables by hand
# ---------------------------------------------------------------------
def rows(spec):
    """Twelve legs from {start: (position, age, x)}."""
    return [(j,) + spec.get(j, (0, 0, 0.0)) for j in S.B_TIMES]


# four Mondays, so a week is a session and the weekly t is the plain one
tab4 = collections.OrderedDict((
    ('20210104', rows({60: (1, 1, 2.0), 90: (1, 2, 1.0), 270: (1, 8, 6.0),
                       300: (1, 9, 3.0)})),
    ('20210111', rows({240: (-1, 1, -2.0), 270: (-1, 2, 4.0)})),
    ('20210118', rows({})),
    ('20210125', rows({330: (1, 1, -1.0), 360: (1, 2, 3.0)}))))
s4 = Y.summarize(tab4)
late4 = [('20210104', 9.0), ('20210111', 4.0), ('20210118', 0.0),
         ('20210125', 2.0)]
diff4 = [('20210104', 9.0 - 1.5), ('20210111', 4.0 + 1.0),
         ('20210118', 0.0), ('20210125', 2.0)]
neg = Y.summarize(collections.OrderedDict((
    ('20210104', rows({60: (1, 1, -5.0), 270: (1, 8, 1.0)})),
    ('20210105', rows({})))))
light = Y.summarize(collections.OrderedDict((
    ('20210104', rows({60: (1, 1, 5.0), 270: (1, 8, 5.0)})),
    ('20210105', rows({})))))
t('L4: by hand on four sessions: a leg\'s mean a session, its share of '
  'B\'s whole result, the sessions in a position and its weekly t (6, 4, '
  '0, 0 gives 1.667); EARLY and LATE; the ages; LATE less half of EARLY; '
  'LATE-HEAVY holds above one half, not at one half, and not when B has '
  'no profit',
  s4['sessions'] == 4 and near(s4['total'], 16.0) and
  near(s4['per_session'], 4.0) and
  s4['legs']['14:00'] == dict(held=2, mean=2.5, share=0.625, t=1.667)
  and s4['legs']['10:00']['held'] == 0 and
  s4['legs']['10:00']['t'] is None and
  s4['legs']['10:00']['mean'] == 0.0 and
  s4['groups']['EARLY']['mean'] == 0.25 and
  s4['groups']['EARLY']['share'] == 0.0625 and
  s4['groups']['EARLY']['held'] == 2 and
  s4['groups']['EARLY']['legs_held'] == 3 and
  s4['groups']['LATE']['mean'] == 3.75 and
  s4['groups']['LATE']['share'] == 0.9375 and
  s4['groups']['LATE']['held'] == 3 and
  s4['groups']['LATE']['legs_held'] == 5 and
  near(s4['groups']['LATE']['per_leg'], 3.0) and
  s4['ages']['1']['legs_held'] == 3 and
  near(s4['ages']['1']['per_leg'], round(-1.0 / 3.0, 5)) and
  s4['ages']['2']['legs_held'] == 3 and
  near(s4['ages']['2']['per_leg'], round(8.0 / 3.0, 5)) and
  s4['ages']['3-4']['legs_held'] == 0 and
  s4['ages']['3-4']['per_leg'] is None and
  s4['ages']['5+']['legs_held'] == 2 and s4['ages']['5+']['share'] == 0.5625
  and near(sum(v['share'] for v in s4['ages'].values()), 1.0) and
  near(sum(v['share'] for v in s4['legs'].values()), 1.0) and
  s4['late_less_half_early']['mean'] == round(
      sum(x for _s, x in diff4) / 4.0, 5) and
  s4['late_less_half_early']['t'] == round(W28.stats(diff4)['t'], 3) and
  s4['groups']['LATE']['t'] == round(W28.stats(late4)['t'], 3) and
  s4['late_heavy'] is True and
  neg['late_heavy'] is False and neg['legs']['14:00']['share'] is None and
  light['late_heavy'] is False and
  light['groups']['LATE']['share'] == 0.5 and
  Y.summarize(collections.OrderedDict())['late_heavy'] is None)

# ---------------------------------------------------------------------
# L5: the Sharpe and the fall
# ---------------------------------------------------------------------
rng = random.Random(5)
same_perf = True
for _k in range(40):
    pr = [('2021%02d%02d' % (1 + i // 28, 1 + i % 28), rng.gauss(0.3, 2.0))
          for i in range(rng.randint(2, 200))]
    a, b = Y.perf(pr), Z31.perf(pr)
    same_perf = same_perf and all(a[k] == b[k] for k in a)
p5 = Y.perf([('20201201', 2.0), ('20201202', -1.0), ('20210104', 3.0),
             ('20210105', -2.0), ('20210106', 4.0)])
t('L5: the Sharpe and the fall ratio are wave thirty-one\'s on every '
  'series tried; by hand a mean of 1.2, a largest fall of 2 and a ratio '
  'of 1.6667; nothing without two sessions or a mean above 0',
  same_perf and p5['mean'] == 1.2 and p5['fall'] == 2.0 and
  p5['fall_ratio'] == round(2.0 / 1.2, 4) and
  p5['sharpe'] == round(1.2 / S.stdev([2.0, -1.0, 3.0, -2.0, 4.0]), 6) and
  Y.perf([('20210104', 1.0)])['sharpe'] is None and
  Y.perf([('20210104', -1.0), ('20210105', -2.0)])['fall_ratio'] is None)

# ---------------------------------------------------------------------
# L6: one market's report
# ---------------------------------------------------------------------
with W25.costs('NQ'):
    res6 = Y.judge_all(dN, oN, cN)
    own_trades = S.rule_b(dN, oN, cN)[0]
    bl_trades = C30.rule(dN, oN, biN, Y.BL_TIMES)
bU = [(s, own_b.get(s, 0.0)) for s in sesN]
t('L6: in a market\'s report B is wave twenty-four\'s own B, by its bar '
  'and by its Sharpe; the legs add up to it; BL is judged by the same '
  'bar on its own days; every setting is put back',
  res6['perf']['B'] == Y.perf(bU) and
  res6['rules']['B']['status'] == S.judge(
      S.nets('B', own_trades, {}))['status'] and
  res6['rules']['B']['both']['n'] == len(own_trades) and
  near(res6['per_session'], round(sum(x for _s, x in bU) / len(bU), 5),
       1e-9) and res6['sessions'] == len(sesN) and
  res6['perf']['BL'] == Y.perf(C30.session_x(sesN, bl_trades)) and
  res6['rules']['BL']['both']['n'] == len(bl_trades) and
  0 < len(bl_trades) <= len(own_trades) and
  list(res6['legs']) == [Y.clock(j) for j in S.B_TIMES] and
  list(res6['groups']) == ['EARLY', 'LATE'] and
  list(res6['ages']) == ['1', '2', '3-4', '5+'] and
  res6['groups']['EARLY']['legs_held'] + res6['groups']['LATE']['legs_held']
  == sum(v['legs_held'] for v in res6['ages'].values()) and
  (S.RT, S.RT_STOP, S.SIDE) == (0.5, 0.75, 0.25) and
  CX.REFUSE_FROM == '20260701')


# ---------------------------------------------------------------------
# L7: the verdict
# ---------------------------------------------------------------------
def rep7(market, bl='PASS', b=(0.10, 10.0), x=(0.12, 8.0), late=1.0,
         heavy=True, version=None):
    return dict(
        wave32=version or Y.W32_VERSION, part='market', market=market,
        late_heavy=heavy, groups=dict(LATE=dict(mean=late)),
        rules=dict(B=dict(status='PASS'), BL=dict(status=bl)),
        perf=dict(B=dict(sharpe=b[0], fall_ratio=b[1]),
                  BL=dict(sharpe=x[0], fall_ratio=x[1])))


def three7(**es):
    return [rep7('NQ', late=3.0), rep7('ES', **es), rep7('RTY', late=2.0)]


later_ok = dict(wave32=Y.W32_VERSION, part='2b', market='NQ', collapsed=[],
                late_heavy=False)
later_bad = dict(later_ok, collapsed=['BL'], late_heavy=True)
v1 = Y.decide(three7())
v2 = Y.decide(three7() + [later_ok])
v3 = Y.decide(three7() + [later_bad])
v4 = Y.decide(three7(x=(0.104, 8.0)))
v5 = Y.decide(three7(x=(0.12, 10.0)))
v6 = Y.decide(three7(b=(0.0, None), x=(0.12, 8.0)))
v7 = Y.decide([rep7('NQ', bl='FAIL', late=3.0), rep7('ES'), rep7('RTY')])
v8 = Y.decide(three7(late=3.5, heavy=False))
v9 = Y.decide(three7(b=(0.10, None), x=(0.12, None)))
t('L7: BL is better than B when it passes the bar on NQ, ES and RTY and '
  'on each of ES and RTY its Sharpe is 5 % higher and its fall ratio '
  'lower; collapsed in the later months it is not; the later months are '
  'asked for until given; the two statements are told market by market; '
  'a missing, doubled or foreign report stops',
  v1['bl']['status'] == 'BETTER THAN B' and not v1['later_read'] and
  any('still to be read' in n for n in v1['notes']) and
  any('only if B itself passes' in n for n in v1['notes']) and
  v2['bl']['status'] == 'BETTER THAN B' and v2['later_read'] and
  v2['later_late_heavy'] is False and
  not any('still to be read' in n for n in v2['notes']) and
  v3['bl']['status'] == 'NOT BETTER (collapsed in the later months)' and
  v3['later_late_heavy'] is True and
  v4['bl']['status'] == 'NOT BETTER' and
  v4['bl']['gains'] == dict(ES=False, RTY=True) and
  v5['bl']['status'] == 'NOT BETTER' and
  v6['bl']['status'] == 'NOT BETTER' and
  v7['bl']['status'] == 'NOT BETTER' and
  v7['bl']['passes'] == dict(NQ=False, ES=True, RTY=True) and
  v9['bl']['status'] == 'NOT BETTER' and
  v1['nq_more'] and v1['late_heavy_everywhere'] and
  not v8['nq_more'] and not v8['late_heavy_everywhere'] and
  v8['late_heavy'] == dict(NQ=True, ES=False, RTY=True) and
  'are needed' in stopped(lambda: Y.decide([rep7('ES'), rep7('RTY')])) and
  'are needed' in stopped(lambda: Y.decide(three7() + [rep7('ES')])) and
  'are needed' in stopped(lambda: Y.decide(
      three7() + [later_ok, later_ok])) and
  'not one of' in stopped(lambda: Y.decide(
      [rep7('NQ', version='x'), rep7('ES'), rep7('RTY')])) and
  'BL, B from 14:00: BETTER THAN B' in Y.text(v1) and
  'RTY HELD; on all three: yes' in Y.text(v1) and
  'ES NOT HELD, RTY HELD; on all three: no' in Y.text(v8) and
  'NQ-MORE (the late legs earn more on NQ): HELD' in Y.text(v1) and
  'NQ, the later months: HELD' in Y.text(v3))

# ---------------------------------------------------------------------
# L8: the reads and the ledger
# ---------------------------------------------------------------------
led = os.path.join(WORK, 'ledger.json')
outs = {m: os.path.join(WORK, 'w32_%s.json' % m) for m in Y.MARKETS}
rcN, saidN = said_by(lambda: Y.main([FN, '--market', 'NQ', '--out',
                                     outs['NQ']], ledger=led))
rcE, saidE = said_by(lambda: Y.main([FE, '--market', 'ES', '--out',
                                     outs['ES']], ledger=led))
rcR, saidR = said_by(lambda: Y.main([FR, '--market', 'RTY', '--out',
                                     outs['RTY']], ledger=led))
rcE2, saidE2 = said_by(lambda: Y.main([FE, '--market', 'ES'], ledger=led))
R2 = make_rows(D(2025, 6, 2), D(2026, 11, 20), 5, drift=0.6, share=0.5)
FL = write(os.path.join(WORK, 'later'), 'NQ 12-26.Last.txt', R2)
outL = os.path.join(WORK, 'w32_later.json')
rcL, saidL = said_by(lambda: Y.main([FL, '--later-months', '--out', outL],
                                    ledger=led))
rcL2, saidL2 = said_by(lambda: Y.main([FL, '--later-months'], ledger=led))
files = [outs[m] for m in Y.MARKETS]
rcD, saidD = said_by(lambda: Y.main(['--decide'] + files))
rcD2, saidD2 = said_by(lambda: Y.main(['--decide'] + files + [outL]))
rcD3, saidD3 = said_by(lambda: Y.main(['--decide', outs['ES']]))
rcM, saidM = said_by(lambda: Y.main([FN, '--market', 'YM'], ledger=led))
rcB, saidB = said_by(lambda: Y.main([FN, '--market', 'NQ',
                                     '--later-months'], ledger=led))
rcW, saidW = said_by(lambda: Y.main(
    [FN, '--market', 'NQ', '--out', os.path.join(WORK, 'no', 'x.json')],
    ledger=os.path.join(WORK, 'ledger3.json')))
short = write(os.path.join(WORK, 'short'), 'NQ 12-26.Last.txt',
              make_rows(D(2026, 5, 4), D(2026, 11, 20), 3))
rcS, saidS = said_by(lambda: Y.main(
    [short, '--later-months'], ledger=os.path.join(WORK, 'ledger4.json')))
reps8 = {m: json.load(open(outs[m])) for m in Y.MARKETS}
repL = json.load(open(outL))
ledr = json.load(open(led))['reads']
t('L8: NQ, ES and RTY and the later months are each read once and '
  'recorded before anything is shown; the report from the command is the '
  'pieces\' own; the later months end on 2026-11-13 and hold only the '
  'window\'s sessions; the verdict needs all three markets and takes the '
  'later months when given; what cannot run stops with nothing recorded',
  rcN == rcE == rcR == rcL == 0 and rcE2 == 2 and 'REFUSED' in saidE2 and
  rcL2 == 2 and 'REFUSED' in saidL2 and
  reps8['NQ']['legs'] == json.loads(json.dumps(res6['legs'])) and
  reps8['NQ']['perf'] == json.loads(json.dumps(res6['perf'])) and
  reps8['RTY']['costs'] == dict(tick=0.1, round_trip=0.2, stop=0.3) and
  'LATE-HEAVY (the late legs earn more than half):' in saidN and
  'B from 14:00 (BL) against B:' in saidN and
  'read recorded (1 read(s)' in saidN and
  repL['last_session'] == '20261113' and repL['part'] == '2b' and
  repL['window'] == ['20260701', '20261113'] and
  repL['sessions'] == repL['trading_days'] >= 90 and
  list(repL['rules']) == ['B', 'BL'] and
  all(v['status'] in ('IN LINE', 'WEAK', 'COLLAPSED', 'TOO FEW')
      for v in repL['rules'].values()) and
  'NQ, the later months' in saidL and
  rcD == 0 and 'BL, B from 14:00:' in saidD and rcD2 == 0 and
  'NQ, the later months:' in saidD2 and
  'NQ, the later months:' not in saidD and
  rcD3 == 2 and 'are needed' in saidD3 and rcM == 2 and rcB == 2 and
  'give either' in saidB and rcW == 2 and 'cannot be written' in saidW
  and not os.path.exists(os.path.join(WORK, 'ledger3.json')) and
  rcS == 2 and 'do not hold every NQ contract' in saidS and
  not os.path.exists(os.path.join(WORK, 'ledger4.json')) and
  [(r['version'], r['part'], r['market']) for r in ledr] ==
  [(Y.W32_VERSION, 'market', m) for m in Y.MARKETS] +
  [(Y.W32_VERSION, '2b', 'NQ')] and
  CX.REFUSE_FROM == '20260701' and
  (S.RT, S.RT_STOP, S.SIDE) == (0.5, 0.75, 0.25))

# ---------------------------------------------------------------------
# L9: what is printed
# ---------------------------------------------------------------------
t('L9: everything printed is plain ASCII and says what it is: reported '
  'tables, not P&L, no order placed',
  all(max(s.encode('utf-8')) < 128 for s in (saidN, saidL, saidD2)) and
  all('No order was placed.' in s for s in (saidN, saidL, saidD2)) and
  'by the age of the position' in saidN and
  'age    sessions  legs held   mean bp   bp a leg   share' in saidN and
  saidN.count('\n  1') >= 4)

# ---------------------------------------------------------------------
# L10: the registration's rules are the code's
# ---------------------------------------------------------------------
t('L10: the legs, the late group, the half, BL\'s four times, the 5 % and '
  'the markets judged are the frozen registration\'s',
  (Y.LATE_FROM, Y.HEAVY, Y.SHARPE_GAIN) == (270, 0.5, 1.05) and
  Y.JUDGED_ON == ('ES', 'RTY') and Y.MARKETS == ('NQ', 'ES', 'RTY') and
  Y.AGES == ('1', '2', '3-4', '5+') and
  all(x in REG for x in (
      'FROZEN on 2026-11-27',
      'twelve legs, 10:00\u201310:30 to 15:30\u201316:00',
      '**EARLY** = the eight legs from 10:00 to 14:00',
      '**LATE** = the four legs from 14:00 to 16:00',
      'the leg that starts at the order has age 1',
      'Reported by age 1, 2, 3\u20134, and 5 or more',
      'the LATE legs earn **more than half** of it',
      'larger on NQ than on ES and than on RTY',
      'decisions only at **14:00, 14:30, 15:00 and 15:30**',
      "BL's Sharpe is **at least 5 % higher** than B's, and BL's fall "
      "ratio is lower than B's",
      'BL passes wave twenty-four\'s bar on each of NQ, ES and RTY',
      'but only if B itself passes wave twenty-five',
      'Sessions from 2026-11-16 are never read')))

shutil.rmtree(WORK, ignore_errors=True)
print('\n%d/%d tests passed' % (sum(1 for _n, ok in OK if ok), len(OK)))
sys.exit(0 if all(ok for _n, ok in OK) else 1)
