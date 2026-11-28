#!/usr/bin/env python3
# MROF-YT-W33-DEALER-1.0 suite. The fall over five days and the
# morning's autocorrelation worked out by hand, B flat from 12:00 by hand
# and against B's own legs on every session, B after a fall and B on
# trend mornings against wave twenty-four's own B, the statements and
# the cells by hand and against independent sums, the verdict on
# fabricated reports, and the reads and the ledger end to end on
# synthetic NinjaTrader-format exports. Synthetic data verifies CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import collections
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

import mrofyt_clocks30 as C30        # noqa: E402
import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_dealer33 as G          # noqa: E402
import mrofyt_improve26 as W26       # noqa: E402
import mrofyt_lateday32 as Y         # noqa: E402
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


def stopped(fn):
    try:
        fn()
    except CX.ContextDataError as exc:
        return str(exc)
    return None


WORK = tempfile.mkdtemp(prefix='mrofyt_w33_')
N = S.N_MIN
D = _dt.date
REG = ' '.join(open(os.path.join(HERE, G.REGISTRATION),
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
# G1: FALL by hand
# ---------------------------------------------------------------------
RETS = [None, 0.01, -0.02, 0.01, 0.0, 0.005, -0.001, None, 0.002]
CH1 = [dict(session='202101%02d' % (4 + i), ret=r)
       for i, r in enumerate(RETS)]
f1 = G.falls(CH1)
g6 = 1.01 * 0.98 * 1.01 * 1.0 * 1.005 - 1.0
g7 = 0.98 * 1.01 * 1.0 * 1.005 * 0.999 - 1.0
t('G1: FALL is the compound return of the five trading days before the '
  'session, its own day left out; fewer than five or a missing one is '
  'unknown, and unknown is not FALL',
  [f1[r['session']] for r in CH1[:6]] == [None] * 6 and
  near(f1['20210110'], g6, 1e-15) and near(f1['20210111'], g7, 1e-15) and
  f1['20210112'] is None and
  not G.is_fall(f1['20210110']) and G.is_fall(f1['20210111']) and
  not G.is_fall(None) and not G.is_fall(0.0) and G.is_fall(-1e-12) and
  G.FALL_DAYS == 5)

# ---------------------------------------------------------------------
# G2: the morning's AC by hand
# ---------------------------------------------------------------------
steady = flat('20210104', 1000.0, 1000.0,
              {5 * k: 1000.0 + k for k in range(1, 79)})
zigzag = flat('20210104', 1000.0, 1000.0,
              {5 * k: 1000.0 + (k % 2) for k in range(1, 79)})
still = flat('20210104', 1000.0, 1000.0, {})
# a spike inside a five-minute change does not count
SPIKE = {5 * k: 1000.0 + k for k in range(1, 31)}
SPIKE.update({7: 1050.0, 9: 1001.0})
spike = flat('20210104', 1000.0, 1000.0, SPIKE)
HALF = {5 * k: 1000.0 + (k % 2) for k in range(1, 31)}
HALF.update({5 * k: 970.0 + k for k in range(31, 79)})
half = flat('20210104', 1000.0, 1000.0, HALF)
t('G2: AC is the sum of each five-minute change times the next over the '
  'sum of their squares: 29/30 on a steady climb (TREND), -29/30 on a '
  'zigzag (FIGHT), none without a change (FIGHT); only the marks every '
  'five minutes count; the afternoon runs 12:00 to 16:00 on its own',
  near(G.ac(steady, 1, 30), 29.0 / 30.0) and G.mode(steady) == 'TREND' and
  near(G.ac(zigzag, 1, 30), -29.0 / 30.0) and G.mode(zigzag) == 'FIGHT' and
  G.ac(still, 1, 30) is None and G.mode(still) == 'FIGHT' and
  near(G.ac(spike, 1, 30), 29.0 / 30.0) and
  G.mode(half) == 'FIGHT' and near(G.ac(half, 31, 78), 47.0 / 48.0) and
  near(G.ac(steady, 31, 78), 47.0 / 48.0) and
  (G.MORNING, G.AFTERNOON, G.NOON, G.STEP) == ((1, 30), (31, 78), 150, 5)
  and G.STEP * G.AFTERNOON[1] == N)

# ---------------------------------------------------------------------
# G3: BMODE by hand
# ---------------------------------------------------------------------
sg = [0.002] * (N + 1)
M3 = {35: 1004.0, 56: 1008.0, 151: 1012.0}
for k in range(13, 31):
    M3[5 * k] = 1009.0 if k % 2 else 1007.0
d3 = flat('20210105', 1000.0, 1000.0, M3)
b3 = S.day_b(d3, sg)
m3 = G.day_bmode(d3, sg, False)
m3t = G.day_bmode(d3, sg, True)
t('G3: by hand: on a zigzag morning B is long from 10:30 (1008) and holds '
  'to 16:00 (1012); BMODE closes at 12:00 (1007) and pays to get in and '
  'out; on a TREND morning BMODE is B',
  G.mode(d3) == 'FIGHT' and near(b3[0] * 1000.0, 4.0) and
  near(b3[1] * 1000.0, 0.5) and b3[2] == 2 and
  near(m3[0] * 1000.0, -1.0) and near(m3[1] * 1000.0, 0.5) and m3[2] == 2
  and m3t == b3)

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
fN = G.falls(cN)
modN = {s: G.mode(dN[s]) for s in oN}

# ---------------------------------------------------------------------
# G4: BMODE against B's own legs on every session
# ---------------------------------------------------------------------
same_t, same_f, closed = True, True, 0
for s in sesN:
    d, sigma = dN[s], biN[s][0]
    same_t = same_t and G.day_bmode(d, sigma, True) == S.day_b(d, sigma)
    lg = Y.legs(d, sigma)
    pos = {j: p for j, p, _a, _g, _c in lg}
    g0 = sum(g for j, _p, _a, g, _c in lg if j < G.NOON)
    extra = S.SIDE * abs(pos[120]) / d.o if pos[150] == pos[120] else 0.0
    c0 = sum(c for j, _p, _a, _g, c in lg if j < G.NOON) + extra
    gm, cm, _n = G.day_bmode(d, sigma, False)
    same_f = same_f and near(gm, g0, 1e-12) and near(cm, c0, 1e-12)
    closed += int(pos[120] != 0)
t('G4: on every session BMODE on a TREND morning is wave twenty-four\'s '
  'day_b; on a FIGHT morning its gross is that of B\'s legs before 12:00 '
  'and its cost theirs plus the close at 12:00 when B did not trade then',
  same_t and same_f and closed > 30 and len(sesN) > 300 and
  0 < sum(1 for s in sesN if modN[s] == 'TREND') < len(sesN))

# ---------------------------------------------------------------------
# G5: the three rules
# ---------------------------------------------------------------------
with W25.costs('NQ'):
    rs5 = G.rules(dN, oN, biN, fN)
    own = S.rule_b(dN, oN, cN)[0]
key = [(x['session'], x['gross'], x['cost'], x['lev']) for x in own]
fall_ses = [s for s in sesN if G.is_fall(fN.get(s))]
bm = {x['session']: x for x in rs5['BMODE']}
bb = {x['session']: x for x in rs5['B']}
tr_ok = all(
    (bm.get(s) is None) == (bb.get(s) is None) and
    (s not in bm or (bm[s]['gross'], bm[s]['cost'], bm[s]['lev']) ==
     (bb[s]['gross'], bb[s]['cost'], bb[s]['lev']))
    for s in sesN if modN[s] == 'TREND')
fi_ok = all(
    (s in bm) == (G.day_bmode(dN[s], biN[s][0], False)[2] > 0)
    for s in sesN if modN[s] == 'FIGHT')
t('G5: B is wave twenty-four\'s own B; BFALL is B on the FALL sessions '
  'and nothing else; BMODE is B after TREND mornings and B flat from '
  '12:00 after FIGHT mornings, sized as B',
  list(rs5) == ['B', 'BFALL', 'BMODE'] and
  [(x['session'], x['gross'], x['cost'], x['lev']) for x in rs5['B']]
  == key and
  [x['session'] for x in rs5['BFALL']] ==
  [x['session'] for x in rs5['B'] if x['session'] in set(fall_ses)] and
  0 < len(rs5['BFALL']) < len(rs5['B']) and tr_ok and fi_ok and
  all(x['late'] == 0 for x in rs5['BMODE']) and
  0 < len(fall_ses) < len(sesN))

# ---------------------------------------------------------------------
# G6: the comparisons and B's last month by hand
# ---------------------------------------------------------------------
c6 = G.compare([1.0, 2.0, 3.0], [0.0, 0.0, 1.0, -1.0])
se6 = math.sqrt(1.0 / 3.0 + (2.0 / 3.0) / 4.0)
SES = ['2%07d' % i for i in range(1, 70)]
xs1 = list(zip(SES, [-1.0] * 30 + [7.0] + [2.0] * 30 + [4.0]))
lm1 = G.last_month(xs1, lambda s: s in (SES[30], SES[61]))
xs2 = list(zip(SES, [1.0] * 15 + [-1.0] * 15 + [9.0]))
lm2 = G.last_month(xs2, lambda s: True)
t('G6: by hand: the means, the difference and the Welch t (2.828); '
  '"above" is strict; one group missing tells nothing; B\'s last month '
  'counts its previous 30 sessions, and a sum of exactly 0 counts as '
  'at or below 0',
  c6['diff'] == 2.0 and c6['held'] is True and
  near(c6['t'], round(2.0 / se6, 3)) and c6['n_yes'] == 3 and
  c6['n_no'] == 4 and c6['mean_no'] == 0.0 and
  G.compare([1.0], [2.0])['held'] is False and
  G.compare([1.0], [2.0])['t'] is None and
  G.compare([2.0, 2.0], [2.0, 2.0])['held'] is False and
  G.compare([2.0, 2.0], [2.0, 2.0])['t'] is None and
  G.compare([], [1.0])['held'] is None and
  G.compare([], [1.0])['mean_no'] == 1.0 and
  (lm1['n_yes'], lm1['mean_yes'], lm1['n_no'], lm1['mean_no']) ==
  (1, 7.0, 1, 4.0) and lm1['held'] is True and
  (lm2['n_yes'], lm2['mean_yes'], lm2['n_no']) == (1, 9.0, 0) and
  G.LOOKBACK == 30)

# ---------------------------------------------------------------------
# G7: one market's report against independent sums
# ---------------------------------------------------------------------
with W25.costs('NQ'):
    res7 = G.judge_all(dN, oN, cN)
    tab7 = Y.leg_table(dN, oN, biN)
ownx = dict(S.nets('B', own, {}))
xb = [(s, ownx.get(s, 0.0)) for s in sesN]
aft = {s: sum(x for j, _p, _a, x in tab7[s] if j >= 150) for s in sesN}
acs = [(s, G.ac(dN[s], 31, 78)) for s in oN]
st7 = res7['statements']
fh, mh, mp = st7['FALL HELPS'], st7['MODE HELPS'], st7['MODE PERSISTS']
t('G7: in a market\'s report FALL HELPS sets B\'s own x after a fall '
  'against the rest, MODE HELPS B\'s legs from 12:00 after TREND against '
  'FIGHT, MODE PERSISTS the afternoon\'s AC over every session; the cells '
  'and the years add up to the sessions; the three rules are judged by '
  'wave twenty-four\'s bar and wave thirty-two\'s Sharpe',
  res7['sessions'] == len(sesN) and
  fh['n_yes'] == len(fall_ses) and fh['n_yes'] + fh['n_no'] == len(sesN)
  and near(fh['mean_yes'], round(S.mean(
      [x for s, x in xb if s in set(fall_ses)]), 5), 1e-9) and
  near(mh['mean_yes'], round(S.mean(
      [aft[s] for s in sesN if modN[s] == 'TREND']), 5), 1e-9) and
  mh['n_yes'] + mh['n_no'] == len(sesN) and
  mp['n_yes'] + mp['n_no'] == sum(1 for _s, a in acs if a is not None)
  and near(mp['mean_no'], round(S.mean(
      [a for s, a in acs if a is not None and modN[s] == 'FIGHT']), 5),
      1e-9) and
  sum(v['n'] for v in res7['cells'].values()) == len(sesN) and
  list(res7['cells']) == ['FALL / TREND', 'FALL / FIGHT',
                          'NOT FALL / TREND', 'NOT FALL / FIGHT'] and
  sum(v['sessions'] for v in res7['years'].values()) == len(sesN) and
  list(res7['years']) == ['2020', '2021'] and
  res7['last_month']['n_yes'] + res7['last_month']['n_no'] ==
  len(sesN) - 30 and
  res7['perf']['B'] == Y.perf(xb) and
  res7['rules']['B']['status'] == S.judge(
      S.nets('B', own, {}))['status'] and
  res7['perf']['BFALL'] == Y.perf(C30.session_x(sesN, rs5['BFALL'])) and
  res7['rules']['BMODE']['both']['n'] == len(rs5['BMODE']) and
  (S.RT, S.RT_STOP, S.SIDE) == (0.5, 0.75, 0.25) and
  CX.REFUSE_FROM == '20260701')


# ---------------------------------------------------------------------
# G8: the verdict
# ---------------------------------------------------------------------
def rep8(market, bar=('PASS', 'PASS'), b=(0.10, 10.0), fall=(0.12, 8.0),
         mode=(0.12, 8.0), held=(True, True, True), version=None):
    return dict(
        wave33=version or G.W33_VERSION, part='market', market=market,
        statements={k: dict(held=h) for k, h in zip(G.STATEMENTS, held)},
        rules=dict(B=dict(status='PASS'), BFALL=dict(status=bar[0]),
                   BMODE=dict(status=bar[1])),
        perf=dict(B=dict(sharpe=b[0], fall_ratio=b[1]),
                  BFALL=dict(sharpe=fall[0], fall_ratio=fall[1]),
                  BMODE=dict(sharpe=mode[0], fall_ratio=mode[1])))


def three8(**es):
    return [rep8('NQ'), rep8('ES', **es), rep8('RTY')]


later_ok = dict(wave33=G.W33_VERSION, part='2b', market='NQ', collapsed=[],
                statements={k: dict(held=False) for k in G.STATEMENTS})
later_bad = dict(later_ok, collapsed=['BMODE'])
v1 = G.decide(three8())
v2 = G.decide(three8() + [later_bad])
v3 = G.decide(three8(fall=(0.104, 8.0), mode=(0.12, 10.0)))
v4 = G.decide(three8(b=(0.0, None)))
v5 = G.decide([rep8('NQ', bar=('FAIL', 'PASS')), rep8('ES'), rep8('RTY')])
v6 = G.decide(three8(held=(False, None, True)))
v7 = G.decide(three8(fall=(0.11, 8.0), mode=(0.13, 7.0)) + [later_ok])
t('G8: a change is better than B when it passes the bar on NQ, ES and '
  'RTY and on each of ES and RTY its Sharpe is 5 % higher and its fall '
  'ratio lower; collapsed in the later months it is not; the statements '
  'are told market by market and on both ES and RTY; a missing, doubled '
  'or foreign report stops',
  v1['changes']['BFALL']['status'] == 'BETTER THAN B' and
  v1['changes']['BMODE']['status'] == 'BETTER THAN B' and
  any('still to be read' in n for n in v1['notes']) and
  any('each goes on alone' in n for n in v1['notes']) and
  any('only if B itself passes' in n for n in v1['notes']) and
  v2['changes']['BMODE']['status'] ==
  'NOT BETTER (collapsed in the later months)' and
  v2['changes']['BFALL']['status'] == 'BETTER THAN B' and
  v2['statements']['FALL HELPS']['later'] is False and
  v3['changes']['BFALL']['status'] == 'NOT BETTER' and
  v3['changes']['BFALL']['gains'] == dict(ES=False, RTY=True) and
  v3['changes']['BMODE']['status'] == 'NOT BETTER' and
  v3['notes'] == [] and
  v4['changes']['BFALL']['status'] == 'NOT BETTER' and
  v5['changes']['BFALL']['status'] == 'NOT BETTER' and
  v5['changes']['BFALL']['passes'] == dict(NQ=False, ES=True, RTY=True) and
  v5['changes']['BMODE']['status'] == 'BETTER THAN B' and
  v1['statements']['MODE HELPS']['both'] is True and
  v6['statements']['FALL HELPS']['both'] is False and
  v6['statements']['MODE HELPS']['both'] is False and
  v6['statements']['MODE HELPS']['held'] == dict(NQ=True, ES=None,
                                                 RTY=True) and
  v6['statements']['MODE PERSISTS']['both'] is True and
  v7['later_read'] and
  not any('still to be read' in n for n in v7['notes']) and
  'are needed' in stopped(lambda: G.decide([rep8('ES'), rep8('RTY')])) and
  'are needed' in stopped(lambda: G.decide(three8() + [rep8('ES')])) and
  'are needed' in stopped(lambda: G.decide(
      three8() + [later_ok, later_ok])) and
  'not one of' in stopped(lambda: G.decide(
      [rep8('NQ', version='x'), rep8('ES'), rep8('RTY')])) and
  'BFALL, B after a fall: BETTER THAN B' in G.text(v1) and
  'FALL HELPS: NQ HELD, ES NOT HELD, RTY HELD; on both ES and RTY: no'
  in G.text(v6) and
  'MODE HELPS: NQ HELD, ES n/a, RTY HELD' in G.text(v6) and
  'NQ, the later months: NOT HELD' in G.text(v7))

# ---------------------------------------------------------------------
# G9: the reads and the ledger
# ---------------------------------------------------------------------
led = os.path.join(WORK, 'ledger.json')
outs = {m: os.path.join(WORK, 'w33_%s.json' % m) for m in G.MARKETS}
rcN, saidN = said_by(lambda: G.main([FN, '--market', 'NQ', '--out',
                                     outs['NQ']], ledger=led))
rcE, saidE = said_by(lambda: G.main([FE, '--market', 'ES', '--out',
                                     outs['ES']], ledger=led))
rcR, saidR = said_by(lambda: G.main([FR, '--market', 'RTY', '--out',
                                     outs['RTY']], ledger=led))
rcE2, saidE2 = said_by(lambda: G.main([FE, '--market', 'ES'], ledger=led))
R2 = make_rows(D(2025, 6, 2), D(2026, 11, 20), 5, drift=0.6, share=0.5)
FL = write(os.path.join(WORK, 'later'), 'NQ 12-26.Last.txt', R2)
outL = os.path.join(WORK, 'w33_later.json')
rcL, saidL = said_by(lambda: G.main([FL, '--later-months', '--out', outL],
                                    ledger=led))
rcL2, saidL2 = said_by(lambda: G.main([FL, '--later-months'], ledger=led))
files = [outs[m] for m in G.MARKETS]
rcD, saidD = said_by(lambda: G.main(['--decide'] + files))
rcD2, saidD2 = said_by(lambda: G.main(['--decide'] + files + [outL]))
rcD3, saidD3 = said_by(lambda: G.main(['--decide', outs['ES']]))
rcM, saidM = said_by(lambda: G.main([FN, '--market', 'YM'], ledger=led))
rcB, saidB = said_by(lambda: G.main([FN, '--market', 'NQ',
                                     '--later-months'], ledger=led))
rcW, saidW = said_by(lambda: G.main(
    [FN, '--market', 'NQ', '--out', os.path.join(WORK, 'no', 'x.json')],
    ledger=os.path.join(WORK, 'ledger3.json')))
short = write(os.path.join(WORK, 'short'), 'NQ 12-26.Last.txt',
              make_rows(D(2026, 5, 4), D(2026, 11, 20), 3))
rcS, saidS = said_by(lambda: G.main(
    [short, '--later-months'], ledger=os.path.join(WORK, 'ledger4.json')))
reps9 = {m: json.load(open(outs[m])) for m in G.MARKETS}
repL = json.load(open(outL))
ledr = json.load(open(led))['reads']
t('G9: NQ, ES and RTY and the later months are each read once and '
  'recorded before anything is shown; the report from the command is the '
  'pieces\' own; the later months end on 2026-11-13 and hold only the '
  'window\'s sessions; the verdict needs all three markets and takes the '
  'later months when given; what cannot run stops with nothing recorded',
  rcN == rcE == rcR == rcL == 0 and rcE2 == 2 and 'REFUSED' in saidE2 and
  rcL2 == 2 and 'REFUSED' in saidL2 and
  reps9['NQ']['statements'] == json.loads(json.dumps(st7)) and
  reps9['NQ']['perf'] == json.loads(json.dumps(res7['perf'])) and
  reps9['RTY']['costs'] == dict(tick=0.1, round_trip=0.2, stop=0.3) and
  'MODE PERSISTS:' in saidN and 'B in the four cells' in saidN and
  'read recorded (1 read(s)' in saidN and
  repL['last_session'] == '20261113' and repL['part'] == '2b' and
  repL['window'] == ['20260701', '20261113'] and
  repL['sessions'] <= repL['trading_days'] and repL['sessions'] >= 85 and
  list(repL['years']) == ['2026'] and
  list(repL['rules']) == ['B', 'BFALL', 'BMODE'] and
  all(v['status'] in ('IN LINE', 'WEAK', 'COLLAPSED', 'TOO FEW')
      for v in repL['rules'].values()) and
  'NQ, the later months' in saidL and
  rcD == 0 and 'BMODE, B on trend mornings:' in saidD and rcD2 == 0 and
  'NQ, the later months:' in saidD2 and
  'NQ, the later months:' not in saidD and
  rcD3 == 2 and 'are needed' in saidD3 and rcM == 2 and rcB == 2 and
  'give either' in saidB and rcW == 2 and 'cannot be written' in saidW
  and not os.path.exists(os.path.join(WORK, 'ledger3.json')) and
  rcS == 2 and 'do not hold every NQ contract' in saidS and
  not os.path.exists(os.path.join(WORK, 'ledger4.json')) and
  [(r['version'], r['part'], r['market']) for r in ledr] ==
  [(G.W33_VERSION, 'market', m) for m in G.MARKETS] +
  [(G.W33_VERSION, '2b', 'NQ')] and
  CX.REFUSE_FROM == '20260701' and
  (S.RT, S.RT_STOP, S.SIDE) == (0.5, 0.75, 0.25))

# ---------------------------------------------------------------------
# G10: what is printed, and the registration's rules are the code's
# ---------------------------------------------------------------------
t('G10: everything printed is plain ASCII and says it is not P&L and no '
  'order was placed; the five days, the thirty morning changes, 12:00, '
  'the 30 sessions, the 5 % and the markets judged are the frozen '
  'registration\'s',
  all(max(s.encode('utf-8')) < 128 for s in (saidN, saidL, saidD2)) and
  all('No order was placed.' in s for s in (saidN, saidL, saidD2)) and
  G.SHARPE_GAIN == 1.05 and G.JUDGED_ON == ('ES', 'RTY') and
  G.MARKETS == ('NQ', 'ES', 'RTY') and G.CHANGES == ('BFALL', 'BMODE') and
  all(x in REG for x in (
      'FROZEN on 2026-11-28',
      'over the five trading days before the session, less 1, is below 0',
      'When any of the five is missing, FALL is unknown and counts as not '
      'FALL',
      'c(k) = P(5k) \u2212 P(5k \u2212 5) for k = 1 \u2026 30',
      '**TREND** when AC is above 0; otherwise **FIGHT**',
      '16:00 (k = 31 \u2026 78), reported only',
      'B is flat from 12:00 (the order at 12:00 closes any position, '
      "paying B's cost)",
      "the change's Sharpe is **at least 5 % higher** than B's",
      'it passes wave twenty-four\'s bar on each of NQ, ES and RTY',
      "B's x summed over its previous 30 sessions is at or below 0",
      '**only if B itself passes wave twenty-five**',
      'Sessions from 2026-11-16 are never read')))

shutil.rmtree(WORK, ignore_errors=True)
print('\n%d/%d tests passed' % (sum(1 for _n, ok in OK if ok), len(OK)))
sys.exit(0 if all(ok for _n, ok in OK) else 1)
