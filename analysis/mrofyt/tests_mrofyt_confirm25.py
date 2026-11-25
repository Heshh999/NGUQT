#!/usr/bin/env python3
# MROF-YT-W25-CONFIRM-1.0 suite. The cost table and how it reaches wave
# twenty-four's rules, the read of another market, the later-months gate
# with its once-only ledger, the window verdicts and the stops are
# exercised on hand-built days and on synthetic NinjaTrader-format
# exports with planted effects. Synthetic data verifies CODE BEHAVIOR
# only, never market evidence. No order, fill or P&L exists.
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
import mrofyt_confirm25 as W         # noqa: E402
import mrofyt_screen15 as S          # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


def near(a, b, tol=1e-9):
    return abs(a - b) <= tol


WORK = tempfile.mkdtemp(prefix='mrofyt_w25_')
N = S.N_MIN
D = _dt.date
REG = ' '.join(open(os.path.join(HERE, W.REGISTRATION),
                    encoding='utf-8').read().split())
HOME_LEDGER = os.path.join(HERE, W.HISTORY_LEDGER)
home_before = open(HOME_LEDGER, 'rb').read() \
    if os.path.exists(HOME_LEDGER) else None


def said_by(fn):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = fn()
    return rc, buf.getvalue()


# ---------------------------------------------------------------------
# C1: the cost table, and the rules put back as they were
# ---------------------------------------------------------------------
tab = {m: W.market_costs(m) for m in W.MARKETS}
rows_in_reg = all('| %s | %.2f | %.2f | %.2f | %.2f |' % (
    m, W.MARKETS[m][0], W.MARKETS[m][1], tab[m]['rt'], tab[m]['stop'])
    in REG for m in W.MARKETS)
own = (S.RT, S.RT_STOP, S.SIDE, S.CO)
with W.costs('RTY', 2.0):
    in_rty = (S.RT, S.RT_STOP, S.SIDE, S.CO.TICK)
back = (S.RT, S.RT_STOP, S.SIDE, S.CO)
try:
    with W.costs('ES'):
        in_es = (S.RT, S.RT_STOP, S.SIDE, S.CO.TICK)
        raise RuntimeError('a failure inside')
except RuntimeError:
    pass
back2 = (S.RT, S.RT_STOP, S.SIDE, S.CO)
t('C1: 5 dollars and one tick a round trip, one tick more on a stop: NQ '
  '0.50/0.75, ES 0.35/0.60, RTY 0.20/0.30, YM 2.00/3.00, the rows of the '
  'registration; NQ\'s are wave twenty-four\'s own; the rules are put back '
  'as they were, after a failure too',
  tab['NQ'] == dict(tick=0.25, rt=0.5, stop=0.75) and
  tab['ES'] == dict(tick=0.25, rt=0.35, stop=0.6) and
  tab['RTY'] == dict(tick=0.1, rt=0.2, stop=0.3) and
  tab['YM'] == dict(tick=1.0, rt=2.0, stop=3.0) and rows_in_reg and
  own[:3] == (0.5, 0.75, 0.25) and own[3].TICK == 0.25 and
  all(near(a, b) for a, b in zip(in_rty, (0.4, 0.6, 0.2, 0.1))) and
  all(near(a, b) for a, b in zip(in_es, (0.35, 0.6, 0.175, 0.25))) and
  back == own and back2 == own and back[3] is own[3])


# ---------------------------------------------------------------------
# C2: the market's tick and costs reach each rule
# ---------------------------------------------------------------------
def mk(session, o, pc, closes, highs=None, lows=None):
    """A Day from 390 closes (a short list is padded with its last)."""
    c = list(closes) + [closes[-1]] * (N - len(closes))
    h = list(highs) + c[len(highs):] if highs else list(c)
    lo = list(lows) + c[len(lows):] if lows else list(c)
    return S.Day(session, 'XX 12-21', o, pc, c, h, lo, [1.0] * N)


# a first candle of 0.2: a risk under NQ's tick, above RTY's
small = mk('20210104', 100.0, 100.0, [100.0, 100.0, 100.0, 100.0, 100.2])
# a first candle of 1.0, stopped in the sixth minute
stopped = mk('20210104', 100.0, 100.0,
             [100.0, 100.0, 100.0, 100.0, 101.0, 101.0],
             lows=[100.0] * 5 + [99.5])
# B: above the noise area at 10:00, flat at the close: two changes
bday = mk('20210104', 100.0, 100.0, [100.0] * 29 + [101.0])
# E: bought at an IBS of 0.05, sold two days on at 0.95
ce = []
for s, close, ret in (('20210104', 100.5, None), ('20210105', 105.0, 0.01),
                      ('20210106', 109.5, 0.02)):
    ce.append(dict(session=s, contract='XX 12-21', close=close, high=110.0,
                   low=100.0, ret=ret, prev=ce[-1]['session'] if ce else None))


def under(market, times=1.0):
    with W.costs(market, times):
        return (S.trade_a(small), S.trade_a(stopped),
                S.day_b(bday, [0.001] * (N + 1)), S.rule_e(ce)[0])


u = {m: under(m) for m in W.MARKETS}
u2 = under('ES', 2.0)
t('C2: a risk under one tick is no trade on NQ, ES and YM and a trade on '
  'RTY; A\'s stop, B\'s two sides and E\'s round trip are charged the '
  'market\'s costs, twice them when doubled; the gross never changes',
  all(u[m][0] is None for m in ('NQ', 'ES', 'YM')) and
  u['RTY'][0] is not None and u['RTY'][0]['how'] == 'CLOSE' and
  near(u['RTY'][0]['cost'], 0.2 / 100.2) and near(u['RTY'][0]['lev'], 4.0)
  and all(u[m][1]['how'] == 'STOP' and near(u[m][1]['gross'], -1.0 / 101.0)
          and near(u[m][1]['cost'], x / 101.0)
          for m, x in (('NQ', 0.75), ('ES', 0.6), ('RTY', 0.3),
                       ('YM', 3.0))) and
  near(u2[1]['cost'], 1.2 / 101.0) and near(u2[1]['gross'], -1.0 / 101.0)
  and all(u[m][2][2] == 2 and near(u[m][2][0], 0.0) and
          near(u[m][2][1], x / 100.0)
          for m, x in (('NQ', 0.5), ('ES', 0.35), ('RTY', 0.2),
                       ('YM', 2.0))) and
  near(u2[2][1], 0.7 / 100.0) and
  all(len(u[m][3]) == 1 and near(u[m][3][0]['gross'], 1.01 * 1.02 - 1.0)
      and u[m][3][0]['units'] == 2 and near(u[m][3][0]['cost'], x / 100.5)
      for m, x in (('NQ', 0.5), ('ES', 0.35), ('RTY', 0.2), ('YM', 2.0)))
  and near(u2[3][0]['cost'], 0.7 / 100.5))

# ---------------------------------------------------------------------
# synthetic exports
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


# 430 weekdays across the two halves; half of them trend all day
R1 = make_rows(D(2020, 3, 2), D(2021, 10, 22), 11, drift=0.6, share=0.5)
FN = write(os.path.join(WORK, 'nq'), 'NQ 12-21.Last.txt', R1)
FE = write(os.path.join(WORK, 'es'), 'ES 12-21.Last.txt', R1)
other = make_rows(D(2021, 3, 1), D(2021, 4, 30), 3)
write(FE, 'NQ 12-21.Last.txt', other)        # other roots in the folder
write(FE, 'MES 12-21.Last.txt', other)

# ---------------------------------------------------------------------
# C3: under NQ's costs this is wave twenty-four, trade for trade
# ---------------------------------------------------------------------
rdN, _chk = S.read(FN)
dN, oN, cN = S.build(rdN)
ref = S.screen(dN, oN, cN)['rules']
own_tr = dict(A=S.rule_a(dN, oN), B=S.rule_b(dN, oN, cN), E=S.rule_e(cN))
with W.costs('NQ'):
    mine_tr = W.three(dN, oN, cN)
    mine = W.judged(dN, oN, cN)
repN = W.run_market(FN, 'NQ')
t('C3: under NQ\'s costs the three rules give wave twenty-four\'s trades '
  'one for one and its verdicts to the last digit, through the reader too',
  list(mine_tr) == list(W.RULES) and
  all(mine_tr[r] == own_tr[r] and len(own_tr[r][0]) >= 30
      for r in W.RULES) and
  all(mine[r]['halves'] == ref[r]['halves'] and
      mine[r]['both'] == ref[r]['both'] and
      mine[r]['status'] == ref[r]['status'] and
      mine[r]['strong'] == ref[r]['strong'] and
      repN['rules'][r]['halves'] == ref[r]['halves'] and
      repN['rules'][r]['status'] == ref[r]['status'] for r in W.RULES) and
  repN['costs'] == dict(tick=0.25, round_trip=0.5, stop=0.75) and
  repN['gaps'] == [] and repN['sessions'] == len(oN))

# ---------------------------------------------------------------------
# C4: section 2a on another market, through the command
# ---------------------------------------------------------------------
led = os.path.join(WORK, 'ledger.json')
outE = os.path.join(WORK, 'w25_es.json')
rc_es, saidE = said_by(lambda: W.main([FE, '--market', 'es', '--out', outE],
                                      ledger=led))
repE = json.load(open(outE))
with W.costs('ES'):
    es_tr = W.three(dN, oN, cN)              # the same bars, as ES
sessN = S.session_returns(cN)
ledE = json.load(open(led))['reads']


def cheaper(rule, stop_ratio):
    a, b = es_tr[rule][0], own_tr[rule][0]
    return len(a) == len(b) and all(
        x['gross'] == y['gross'] and x['session'] == y['session'] and
        near(x['cost'], y['cost'] * (stop_ratio if y.get('how') == 'STOP'
                                     else 0.7)) for x, y in zip(a, b))


t('C4: --market ES reads the ES files alone, charges 0.35 and 0.60 where '
  'NQ pays 0.50 and 0.75 on the same trades, judges A, B and E by wave '
  'twenty-four\'s bar, shows the same with costs doubled, and records the '
  'read before showing it; the planted trend passes A',
  rc_es == 0 and repE['part'] == '2a' and repE['market'] == 'ES' and
  repE['files'] == 1 and list(repE['rules']) == list(W.RULES) and
  repE['costs'] == dict(tick=0.25, round_trip=0.35, stop=0.6) and
  cheaper('A', 0.6 / 0.75) and cheaper('B', 0.7) and cheaper('E', 0.7) and
  any(x['how'] == 'STOP' for x in es_tr['A'][0]) and
  all(repE['rules'][r]['halves'] == S.judge(S.nets(
      r, es_tr[r][0], sessN))['halves'] for r in W.RULES) and
  all(repE['rules'][r]['halves'][h]['net'] > ref[r]['halves'][h]['net']
      and repE['costs_doubled'][r][h] < repE['rules'][r]['halves'][h]['net']
      for r in W.RULES for h in S.HALVES) and
  repE['rules']['A']['status'] == 'PASS' and
  repE['passed'] == [r for r in W.RULES
                     if repE['rules'][r]['status'] == 'PASS'] and
  len(ledE) == 1 and ledE[0]['version'] == W.W25_VERSION and
  ledE[0]['part'] == '2a' and ledE[0]['market'] == 'ES' and
  ledE[0]['first'] == repE['first_session'] and
  ledE[0]['last'] == repE['last_session'] and
  ledE[0]['n'] == repE['n_trades'] and
  'PASSED ON ES: ' in saidE and 'beside, costs doubled' in saidE and
  '0.35 a round trip, 0.60 on a stop (tick 0.25)' in saidE and
  'wave-twenty-five report ->' in saidE and
  'read recorded (1 read(s)' in saidE and
  (S.RT, S.RT_STOP, S.SIDE, S.CO) == own)

# ---------------------------------------------------------------------
# C5: a contract that was not exported stops the run
# ---------------------------------------------------------------------
R5 = make_rows(D(2020, 3, 2), D(2021, 10, 22), 7, tick=0.1, px0=2000.0,
               sd=0.4, drift=0.12, share=0.5)
FR = write(os.path.join(WORK, 'rty'), 'RTY SEP21.Last.txt', R5,
           lambda d: not D(2021, 1, 4) <= d <= D(2021, 1, 22))
led_r = os.path.join(WORK, 'ledger_rty.json')
outR = os.path.join(WORK, 'w25_rty.json')
rc_gap, said_gap = said_by(lambda: W.main([FR, '--market', 'RTY'],
                                          ledger=led_r))
led_after_gap = os.path.exists(led_r)
rc_gok, said_gok = said_by(lambda: W.main(
    [FR, '--market', 'RTY', '--gaps-ok', '--out', outR], ledger=led_r))
repR = json.load(open(outR))
t('C5: three weeks without a cash session stop the run before any rule is '
  'computed or recorded, naming the days on either side; --gaps-ok runs it '
  'and the report says so; RTY is read by month name on a 0.10 tick',
  rc_gap == 2 and 'STOPPED: the RTY exports have no cash session between '
  '20210101 and 20210125' in said_gap and 'Nothing was computed' in said_gap
  and 'PASSED ON' not in said_gap and not led_after_gap and
  rc_gok == 0 and repR['gaps'] == [['20210101', '20210125']] and
  'NO CASH SESSION between 20210101 and 20210125' in said_gok and
  repR['market'] == 'RTY' and repR['files'] == 1 and
  repR['costs'] == dict(tick=0.1, round_trip=0.2, stop=0.3) and
  repR['sessions'] >= 380 and
  len(json.load(open(led_r))['reads']) == 1)

# ---------------------------------------------------------------------
# C6: section 2b, the months after the screen, once
# ---------------------------------------------------------------------
R2 = make_rows(D(2025, 6, 2), D(2026, 11, 20), 5, drift=0.6, share=0.5)
FL = write(os.path.join(WORK, 'later'), 'NQ 12-26.Last.txt', R2)
outL = os.path.join(WORK, 'w25_later.json')
rd0, _chk = W.read(FL, 'NQ')                    # the gate as it stands
rc_l1, saidL = said_by(lambda: W.main([FL, '--later-months', '--out', outL],
                                      ledger=led))
gate_after = CX.REFUSE_FROM
repL = json.load(open(outL))
ledL = json.load(open(led))['reads']
rc_l2, saidL2 = said_by(lambda: W.main([FL, '--later-months'], ledger=led))
ledL2 = json.load(open(led))['reads']
rdL, _chk = W.read(FL, 'NQ', later=True)        # counted again by hand
dL, oL, cL = S.build(rdL)


def inw(s):
    return '20260701' <= s <= '20261113'


benchL = S.mean([r['ret'] for r in cL
                 if inw(r['session']) and r['ret'] is not None])
handL = dict(
    A=[1e4 * (x['gross'] - x['cost']) * x['lev']
       for x in S.rule_a(dL, oL)[0] if inw(x['session'])],
    B=[1e4 * (x['gross'] - x['cost']) * x['lev']
       for x in S.rule_b(dL, oL, cL)[0] if inw(x['session'])],
    E=[1e4 * (x['gross'] - x['cost'] - benchL * x['units'])
       for x in S.rule_e(cL)[0] if inw(x['session'])])
t('C6: --later-months reads NQ to 2026-11-13 and no further (the seven '
  'later sessions in the file are refused unread), judges only the trades '
  'from 2026-07-01, E over the window\'s average session; the gate is back '
  'at 2026-07-01 afterwards; the read is recorded and refused a second '
  'time',
  max(s for _c, s in rd0.days) == '20260630' and
  max(s for _c, s in rdL.days) == '20261113' and
  rc_l1 == 0 and repL['part'] == '2b' and repL['market'] == 'NQ' and
  repL['window'] == ['20260701', '20261113'] and
  repL['first_session'] == '20260701' and
  repL['last_session'] == '20261113' and
  repL['last_session_read'] == '20261113' and
  repL['trading_days'] == 98 and repL['history_days'] == 282 and
  repL['refused_from_20261114'] == 7 and
  90 <= len(handL['A']) <= repL['sessions'] <= 98 and
  all(repL['rules'][r]['n'] == len(handL[r]) and
      (not handL[r] or near(repL['rules'][r]['net'],
                            round(S.mean(handL[r]), 3)))
      and repL['rules'][r] == dict(
          W.window_verdict(handL[r]), rule=r, name=S.NAMES[r],
          notes=repL['rules'][r]['notes']) for r in W.RULES) and
  near(repL['mean_session_bp'], round(1e4 * benchL, 3)) and
  repL['rules']['A']['status'] == 'IN LINE' and
  (repL['rules']['E']['status'] == 'TOO FEW') == (len(handL['E']) < 30) and
  repL['collapsed'] == [] and
  gate_after == '20260701' and CX.REFUSE_FROM == '20260701' and
  len(ledL) == 2 and ledL[1]['part'] == '2b' and ledL[1]['market'] == 'NQ'
  and ledL[1]['first'] == '20260701' and ledL[1]['last'] == '20261113' and
  ledL[1]['n'] == repL['n_trades'] and
  '*** LATER MONTHS' in saidL and 'COLLAPSED: none' in saidL and
  'refused unread (7 in these files); the last one read is 20261113'
  in saidL and
  rc_l2 == 2 and 'REFUSED: the later months have been read' in saidL2 and
  'IN LINE' not in saidL2 and ledL2 == ledL)

# ---------------------------------------------------------------------
# C7: a collapse is named; a half export does not use the read up
# ---------------------------------------------------------------------
R3 = make_rows(D(2025, 6, 2), D(2026, 11, 20), 6, drift=-0.3, share=1.0)
FC = write(os.path.join(WORK, 'collapse'), 'NQ 12-26.Last.txt', R3)
repC = W.run_later(FC)
FH = write(os.path.join(WORK, 'hole'), 'NQ 12-26.Last.txt', R2,
           lambda d: not D(2026, 6, 12) <= d <= D(2026, 9, 10))
FS = write(os.path.join(WORK, 'short'), 'NQ 12-26.Last.txt', R2,
           lambda d: d >= D(2026, 6, 1))
FG = write(os.path.join(WORK, 'gap'), 'NQ 12-26.Last.txt', R2,
           lambda d: not D(2026, 8, 3) <= d <= D(2026, 8, 10))
led3 = os.path.join(WORK, 'ledger3.json')
rc_h, said_h = said_by(lambda: W.main([FH, '--later-months'], ledger=led3))
rc_s, said_s = said_by(lambda: W.main([FS, '--later-months'], ledger=led3))
rc_g, said_g = said_by(lambda: W.main([FG, '--later-months'], ledger=led3))
led_bad = os.path.join(WORK, 'ledger_bad.json')
with open(led_bad, 'w') as fh:
    fh.write('not a ledger')
rc_bad, said_bad = said_by(lambda: W.main([FL, '--later-months'],
                                          ledger=led_bad))
t('C7: a rule that loses day after day is COLLAPSED and listed; without '
  'the September contract, without the earlier contracts, or with a week '
  'missing, the run stops with nothing computed and nothing recorded, and '
  'the gate is put back; a ledger that cannot be read stops it too',
  repC['rules']['A']['status'] == 'COLLAPSED' and
  repC['rules']['A']['net'] < -2.0 * repC['rules']['A']['standard_error']
  and 'A' in repC['collapsed'] and
  repC['collapsed'] == [r for r in W.RULES
                        if repC['rules'][r]['status'] == 'COLLAPSED'] and
  'COLLAPSED: A' in W.text(repC) and
  rc_h == 2 and 'only 46 of the 96 trading days' in said_h and
  rc_s == 2 and 'only 22 trading days before 2026-07-01' in said_s and
  rc_g == 2 and 'no cash session between 20260731 and 20260811' in said_g
  and all('STOPPED: ' in x and 'IN LINE' not in x and 'COLLAPSED' not in x
          for x in (said_h, said_s, said_g, said_bad)) and
  not os.path.exists(led3) and CX.REFUSE_FROM == '20260701' and
  rc_bad == 2 and 'the ledger ledger_bad.json cannot be read' in said_bad
  and open(led_bad).read() == 'not a ledger')

# ---------------------------------------------------------------------
# C8: the four verdicts of the window
# ---------------------------------------------------------------------
v_few = W.window_verdict([5.0] * 29)
v_none = W.window_verdict([])
v_in = W.window_verdict([1.0, -0.5] * 15)
v_flat = W.window_verdict([5.0] * 30)
v_weak = W.window_verdict([1.0, -1.1] * 15)
v_zero = W.window_verdict([1.0, -1.0] * 15)
v_col = W.window_verdict([-1.0, -1.2] * 15)
v_weak2 = W.window_verdict([1.0, -1.5] * 15)
v_col2 = W.window_verdict([0.5, -1.5] * 15)
t('C8: under 30 results is TOO FEW whatever they are; from 30, a mean above '
  '0 is IN LINE, one at or below 0 within two standard errors is WEAK, one '
  'further below is COLLAPSED',
  v_few == dict(n=29, net=5.0, won=1.0, status='TOO FEW') and
  v_none == dict(n=0, status='TOO FEW') and
  v_in['status'] == 'IN LINE' and v_in['n'] == 30 and
  near(v_in['net'], 0.25) and near(v_in['won'], 0.5) and
  near(v_in['standard_error'],
       round(S.stdev([1.0, -0.5] * 15) / 30 ** 0.5, 3)) and
  v_flat['status'] == 'IN LINE' and
  v_weak['status'] == 'WEAK' and near(v_weak['net'], -0.05) and
  v_zero['status'] == 'WEAK' and v_zero['net'] == 0.0 and
  v_col['status'] == 'COLLAPSED' and
  v_weak2['status'] == 'WEAK' and near(v_weak2['net'], -0.25) and
  v_weak2['net'] >= -2.0 * v_weak2['standard_error'] and
  v_col2['status'] == 'COLLAPSED' and near(v_col2['net'], -0.5) and
  near(v_col2['won'], 0.5) and
  v_col2['net'] < -2.0 * v_col2['standard_error'])

# ---------------------------------------------------------------------
# C9: the command's stops, and the frozen registration
# ---------------------------------------------------------------------
led9 = os.path.join(WORK, 'ledger9.json')
rc0, said0 = said_by(lambda: W.main([]))
rc_both, said_both = said_by(lambda: W.main(
    [FE, '--market', 'ES', '--later-months'], ledger=led9))
rc_neither, said_neither = said_by(lambda: W.main([FE], ledger=led9))
rc_nq, said_nq = said_by(lambda: W.main([FE, '--market', 'NQ'],
                                        ledger=led9))
rc_dir, said_dir = said_by(lambda: W.main(
    [os.path.join(WORK, 'no_such_folder'), '--market', 'ES'], ledger=led9))
rc_ym, said_ym = said_by(lambda: W.main([FE, '--market', 'YM'],
                                        ledger=led9))
no_dir = os.path.join(WORK, 'no_such_folder', 'report.json')
rc_out, said_out = said_by(lambda: W.main(
    [FL, '--later-months', '--out', no_dir], ledger=led9))
probe = os.path.join(WORK, 'probe.json')
can = (W.can_write(probe), os.path.exists(probe), W.can_write(no_dir))
try:
    W.read(FE, 'ES', later=True)
    later_es = False
except CX.ContextDataError:
    later_es = True
home_after = open(HOME_LEDGER, 'rb').read() \
    if os.path.exists(HOME_LEDGER) else None
t('C9: the command wants one of --market ES|RTY|YM and --later-months, '
  'stops on a missing folder, a market with no files or a report it '
  'cannot write (before the once-only read is used), never reads the '
  'later months on another market, and leaves the folder\'s own ledger '
  'alone; the constants are the frozen registration\'s',
  rc0 == 2 and 'mrofyt_confirm25.py' in said0 and
  rc_both == 2 and rc_neither == 2 and
  all('STOPPED: give either --market' in x
      for x in (said_both, said_neither)) and
  rc_nq == 2 and '--market is one of ES, RTY, YM' in said_nq and
  rc_dir == 2 and 'STOPPED: cannot read' in said_dir and
  rc_ym == 2 and 'STOPPED: no YM minute exports found' in said_ym and
  rc_out == 2 and 'cannot be written' in said_out and
  'Nothing was read' in said_out and 'LATER MONTHS' not in said_out and
  can == (True, False, False) and
  later_es and CX.REFUSE_FROM == '20260701' and
  not os.path.exists(led9) and home_after == home_before and
  W.RULES == ('A', 'B', 'E') and W.REQUIRED == ('ES', 'RTY') and
  W.OTHER_MARKETS == ('ES', 'RTY', 'YM') and
  (W.LATER_FROM, W.LATER_TO, W.LATER_REFUSE_FROM) ==
  ('20260701', '20261113', '20261114') and W.WINDOW_MIN_N == 30 and
  W.COMMISSION_RT == 5.0 and
  all(x in REG for x in (
      'FROZEN on 2026-11-25', '`rule_a`, `rule_b`, `rule_e`, `nets`, '
      '`judge`', '5 dollars of commission and one tick of spread',
      'a stop one tick more', 'sessions **2026-07-01 to 2026-11-13**',
      'only with `--later-months`, the refusal moves to 2026-11-14',
      'Sessions from 2026-11-16 stay refused', 'The read is made once',
      '| IN LINE | 30 trades or days, mean net above 0 |',
      'within two standard errors of 0',
      'below 0 by more than two standard errors', 'fewer than 30',
      'Only COLLAPSED counts against it', 'passes the bar of §2a on '
      '**ES and RTY**', 'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
