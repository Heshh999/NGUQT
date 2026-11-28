#!/usr/bin/env python3
# MROF-YT-W35-STRESS-1.0 suite. The sizes against wave twenty-six's own,
# the plan and the account in the history's order against wave
# twenty-six's account, the account by hand, a year from blocks, the
# resampling on sequences whose answer is known, and the read and the
# ledger end to end on synthetic NinjaTrader-format exports. Synthetic
# data verifies CODE BEHAVIOR only, never market evidence. No order,
# fill or P&L exists.
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

import mrofyt_context as CX          # noqa: E402
import mrofyt_improve26 as W26       # noqa: E402
import mrofyt_screen15 as S          # noqa: E402
import mrofyt_stress35 as K          # noqa: E402

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


WORK = tempfile.mkdtemp(prefix='mrofyt_w35_')
D = _dt.date
REG = ' '.join(open(os.path.join(HERE, K.REGISTRATION),
                    encoding='utf-8').read().split())
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
# K1: the sizes
# ---------------------------------------------------------------------
rng = random.Random(1)
risks = [rng.uniform(1.0, 200.0) for _k in range(300)]
vols = [(rng.uniform(0.004, 0.03), rng.uniform(5000.0, 25000.0))
        for _k in range(300)]
t('K1: at size 1 the micros are wave twenty-six\'s own; at a half and a '
  'quarter the budget is that much smaller; never under one micro, never '
  'over fifteen',
  all(K.a_micros(r, 1.0) == W26.a_micros(r) for r in risks) and
  all(K.b_micros(s, o, 1.0) == W26.b_micros(s, o) for s, o in vols) and
  K.a_micros(10.0, 1.0) == 7 and K.a_micros(10.0, 0.5) == 3 and
  K.a_micros(10.0, 0.25) == 1 and K.a_micros(500.0, 0.25) == 1 and
  K.a_micros(0.5, 1.0) == 15 and
  K.b_micros(0.01, 10000.0, 1.0) == 3 and
  K.b_micros(0.01, 10000.0, 0.5) == 1 and
  K.b_micros(0.01, 10000.0, 0.25) == 1 and
  K.b_micros(0.001, 5000.0, 1.0) == 15 and
  K.SCALES == (1.0, 0.5, 0.25))

# ---------------------------------------------------------------------
# the synthetic exports
# ---------------------------------------------------------------------
R1 = make_rows(D(2020, 3, 2), D(2021, 10, 22), 11, drift=0.6, share=0.5)
FN = write(os.path.join(WORK, 'nq'), 'NQ 12-21.Last.txt', R1)
rdN, _chk = S.read(FN)
dN, oN, cN = S.build(rdN)
own_plan = W26.prop_days(dN, oN, cN)

# ---------------------------------------------------------------------
# K2: the plan and the account in the history's own order
# ---------------------------------------------------------------------
pl1 = K.plan(dN, oN, cN, 1.0)
pl4 = K.plan(dN, oN, cN, 0.25)
acc_off = W26.account(dN, own_plan)
acc_on = W26.account(dN, own_plan, W26.DAY_STOP)
seq_off = K.paths(dN, pl1)
seq_on = K.paths(dN, pl1, W26.DAY_STOP)
r_off, r_on = K.run(seq_off), K.run(seq_on)
h_off = K.history(seq_off)
t('K2: at size 1 the plan is wave twenty-six\'s prop_days, and the '
  'account over the history in its own order is wave twenty-six\'s '
  'account: its result, the accounts lost and the largest fall, without '
  'and with the day stop; at a quarter no session has more micros',
  pl1 == own_plan and len(seq_off) == len(oN) > 300 and
  near(r_off[0], acc_off['result'], 0.006) and
  r_off[1] == acc_off['fails'] and
  near(r_off[2], acc_off['largest_fall'], 0.006) and
  near(r_on[0], acc_on['result'], 0.006) and r_on[1] == acc_on['fails']
  and near(r_on[2], acc_on['largest_fall'], 0.006) and
  h_off['sessions'] == len(oN) and h_off['lost'] == acc_off['fails'] and
  near(h_off['result_a_year'], acc_off['result'] * 252.0 / len(oN), 0.006)
  and all((a4 is None) == (a1 is None) and
          (a4 is None or a4['micros'] <= a1['micros']) and
          (b4 is None) == (b1 is None) and
          (b4 is None or (b4[0] == b1[0] and b4[1] <= b1[1]))
          for (_s, a1, b1), (_s4, a4, b4) in zip(pl1, pl4)) and
  any(a4 and a4['micros'] < a1['micros']
      for (_s, a1, _b1), (_s4, a4, _b4) in zip(pl1, pl4)) and
  sum(1 for r, lo in seq_off if r == 0.0 and lo == 0.0) ==
  sum(1 for _s, a, b in pl1 if not (a or b)))

# ---------------------------------------------------------------------
# K3: the account by hand
# ---------------------------------------------------------------------
t('K3: by hand: the account is lost when the balance plus the session\'s '
  'lowest value is at or below its highest end-of-day balance less '
  '4,500, exactly at the line too; it starts again after a loss; the '
  'largest fall runs from the highest sum to the lowest value',
  K.run([(1000.0, -500.0), (-2000.0, -3000.0), (-1000.0, -4000.0),
         (500.0, -100.0)]) == (-1500.0, 1, 6000.0) and
  K.run([(0.0, -4500.0)]) == (0.0, 1, 4500.0) and
  K.run([(0.0, -4499.99)])[1] == 0 and
  K.run([(-2000.0, -2000.0), (-2000.0, -2000.0), (-400.0, -500.0)])[1]
  == 1 and
  K.run([(-2000.0, -2000.0), (-2000.0, -2000.0), (-400.0, -499.0)])[1]
  == 0 and
  K.run([(3000.0, 0.0), (-4500.0, -4500.0), (-4000.0, -4400.0)])[1] == 1
  and K.run([]) == (0.0, 0, 0.0) and
  (W26.ACCOUNT, W26.TRAIL, W26.DAY_STOP) == (150000.0, 4500.0, 1000.0))

# ---------------------------------------------------------------------
# K4: a year from blocks
# ---------------------------------------------------------------------
idx = list(range(1000))
y1 = K.a_year(idx, random.Random(35))
y2 = K.a_year(idx, random.Random(35))
y3 = K.a_year(idx, random.Random(36))
blocks = [y1[k:k + 20] for k in range(0, 252, 20)]
wrap = K.a_year(list(range(25)), random.Random(2))
t('K4: a year is 252 sessions in blocks of 20 consecutive ones, the '
  'last block cut short; a block that reaches the end goes on from the '
  'start; the same seed gives the same year; the 5 %, the median and the '
  '95 % are read off the sorted years',
  len(y1) == 252 and y1 == y2 and y1 != y3 and len(blocks) == 13 and
  len(blocks[-1]) == 12 and
  all((b - a) % 1000 == 1 for blk in blocks for a, b in zip(blk, blk[1:]))
  and len({blk[0] for blk in blocks}) > 8 and
  all((b - a) % 25 == 1 for k in range(0, 252, 20)
      for a, b in zip(wrap[k:k + 20], wrap[k + 1:k + 20])) and
  any(b < a for a, b in zip(wrap, wrap[1:])) and
  K.below(list(range(1, 101)), 0.05) == 6 and
  K.below(list(range(100, 0, -1)), 0.5) == 51 and
  K.below(list(range(1, 101)), 0.95) == 96 and
  K.below([7.0], 0.95) == 7.0 and
  (K.BLOCK, K.YEAR, K.RUNS, K.SEED) == (20, 252, 5000, 35))

# ---------------------------------------------------------------------
# K5: the resampling where the answer is known
# ---------------------------------------------------------------------
up = K.stress([(10.0, 0.0)] * 300, runs=50)
dn = K.stress([(-100.0, -100.0)] * 300, runs=50)
mixed = [(50.0, -20.0)] * 280 + [(-5000.0, -5000.0)] * 20
mx = K.stress(mixed, runs=400)
mx2 = K.stress(mixed, runs=400)
t('K5: days that all win lose no account and end the year 2,520 up; '
  'days that all lose 100 lose the account every 45 sessions, five times '
  'a year; with one bad stretch in the history some years lose the '
  'account and some do not; the same seed gives the same numbers',
  up['lost_any'] == 0.0 and up['lost_a_year'] == 0.0 and
  up['result_median'] == 2520.0 and up['result_p5'] == 2520.0 and
  up['fall_median'] == 0.0 and up['years'] == 50 and
  dn['lost_any'] == 1.0 and dn['lost_a_year'] == 5.0 and
  dn['result_median'] == -25200.0 and dn['fall_median'] == 25200.0 and
  0.2 < mx['lost_any'] < 0.9 and mx == mx2 and
  mx['result_p5'] < mx['result_median'] <= mx['result_p95'] and
  mx['result_p95'] == 252 * 50.0 and
  mx['fall_p95'] >= mx['fall_median'])

# ---------------------------------------------------------------------
# K6: every size
# ---------------------------------------------------------------------
rows6 = K.all_sizes(dN, oN, cN, runs=60)
t('K6: six lines: the budgets times 1, 1/2 and 1/4, each without and '
  'with the day stop, which shrinks with them; the first line\'s history '
  'is wave twenty-six\'s account; a smaller size never has a larger '
  'fall in the history',
  [(r['size'], r['day_stop']) for r in rows6] ==
  [(1.0, None), (1.0, 1000.0), (0.5, None), (0.5, 500.0), (0.25, None),
   (0.25, 250.0)] and
  rows6[0]['budgets'] == dict(A=150.0, B=500.0) and
  rows6[4]['budgets'] == dict(A=37.5, B=125.0) and
  rows6[0]['history'] == h_off and
  rows6[1]['history']['lost'] == acc_on['fails'] and
  rows6[4]['history']['largest_fall'] <=
  rows6[0]['history']['largest_fall'] and
  all(r['years'] == 60 and 0.0 <= r['lost_any'] <= 1.0 and
      r['result_p5'] <= r['result_median'] <= r['result_p95']
      for r in rows6))

# ---------------------------------------------------------------------
# K7: the read and the ledger
# ---------------------------------------------------------------------
led = os.path.join(WORK, 'ledger.json')
outp = os.path.join(WORK, 'w35.json')
rc1, said1 = said_by(lambda: K.main([FN, '--out', outp], ledger=led,
                                    runs=60))
rc2, said2 = said_by(lambda: K.main([FN], ledger=led, runs=60))
rcW, saidW = said_by(lambda: K.main(
    [FN, '--out', os.path.join(WORK, 'no', 'x.json')],
    ledger=os.path.join(WORK, 'ledger3.json'), runs=60))
short = write(os.path.join(WORK, 'short'), 'NQ 12-21.Last.txt',
              make_rows(D(2021, 6, 1), D(2021, 10, 22), 3))
rcS, saidS = said_by(lambda: K.main(
    [short], ledger=os.path.join(WORK, 'ledger4.json'), runs=60))
rc0, said0 = said_by(lambda: K.main([]))
rep7 = json.load(open(outp))
ledr = json.load(open(led))['reads']
t('K7: NQ is read once and recorded before anything is shown; the '
  'report from the command is the pieces\' own; what cannot run stops '
  'with nothing recorded',
  rc1 == 0 and rc2 == 2 and 'REFUSED' in said2 and
  rep7['sizes'] == json.loads(json.dumps(rows6)) and
  rep7['resampling'] == dict(block=20, year=252, years=60, seed=35) and
  rep7['account'] == dict(start=150000.0, trail=4500.0) and
  rep7['sessions'] == len(oN) and
  'read recorded (1 read(s)' in said1 and
  rcW == 2 and 'cannot be written' in saidW and
  not os.path.exists(os.path.join(WORK, 'ledger3.json')) and
  rcS == 2 and 'this needs years of minute bars' in saidS and
  not os.path.exists(os.path.join(WORK, 'ledger4.json')) and rc0 == 2 and
  [(r['version'], r['part'], r['market'], r['n']) for r in ledr] ==
  [(K.W35_VERSION, 'stress', 'NQ', len(oN))] and
  CX.REFUSE_FROM == '20260701' and
  (S.RT, S.RT_STOP, S.SIDE) == (0.5, 0.75, 0.25))

# ---------------------------------------------------------------------
# K8: what is printed, and the registration's rules are the code's
# ---------------------------------------------------------------------
t('K8: everything printed is plain ASCII and says it is planning only, '
  'not a forecast, not P&L, and that no order was placed; the blocks, '
  'the year, the 5,000 years, the seed and the sizes are the frozen '
  'registration\'s',
  max(said1.encode('utf-8')) < 128 and
  'Planning only: nothing is judged.' in said1 and
  'Not a forecast' in said1 and 'No order was placed.' in said1 and
  said1.count('\n  1.00 ') == 2 and said1.count('\n  0.25 ') == 2 and
  all(x in REG for x in (
      'FROZEN on 2026-11-28',
      '**This file judges nothing.**',
      'times **1**, times **1/2** and times **1/4**',
      '$1,000 times the same factor',
      'at or below the highest end-of-day balance so far less $4,500',
      'A **year** is 252 sessions put together from **blocks of 20 '
      'consecutive sessions**',
      '**5,000 years**, from the fixed random seed 35',
      'a block that reaches the last session goes on from the first',
      'Sessions from 2026-07-01 are never read')))

shutil.rmtree(WORK, ignore_errors=True)
print('\n%d/%d tests passed' % (sum(1 for _n, ok in OK if ok), len(OK)))
sys.exit(0 if all(ok for _n, ok in OK) else 1)
