#!/usr/bin/env python3
# MROF-YT-W28-MARKETS-1.0 suite. The market table against the
# registration, the day session and costs set around wave twenty-four's
# rules and put back, the per-session numbers, the tick seen in the
# files, the four data gates, the once-only reads and decision, and the
# pooled and class verdicts are exercised on hand-built days, fabricated
# series and synthetic NinjaTrader-format exports with planted effects.
# Synthetic data verifies CODE BEHAVIOR only, never market evidence. No
# order, fill or P&L exists.
import array
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
import types
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_context as CX          # noqa: E402
import mrofyt_discover as DI         # noqa: E402
import mrofyt_markets28 as M         # noqa: E402
import mrofyt_screen15 as S          # noqa: E402
import mrofyt_levels27 as L27        # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


def near(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


WORK = tempfile.mkdtemp(prefix='mrofyt_w28_')
D = _dt.date
REG = ' '.join(open(os.path.join(HERE, M.REGISTRATION),
                    encoding='utf-8').read().split())
HOME_LEDGER = os.path.join(HERE, M.HISTORY_LEDGER)
home_before = open(HOME_LEDGER, 'rb').read() \
    if os.path.exists(HOME_LEDGER) else None
MIN_SESSIONS = M.MIN_SESSIONS


def said_by(fn):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = fn()
    return rc, buf.getvalue()


def state():
    return tuple(getattr(CX, k) for k in M._CX_NAMES) + \
        tuple(getattr(S, k) for k in M._S_NAMES)


# ---------------------------------------------------------------------
# M1: the table is the registration's
# ---------------------------------------------------------------------
def fmt(x):
    s = ('%.7f' % x).rstrip('0').rstrip('.')
    return s


def row(mk):
    m = M.MARKETS[mk]
    c = M.market_costs(mk)
    tick = '%.2f' % m.tick if m.tick >= 0.1 else fmt(m.tick)
    money = '%.2f' if mk == 'BTC' else None
    return '| %s | %s | %02d:%02d–%02d:%02d | %d | %s | %s | %s | %s | %s |' % (
        mk, m.cls, m.open[0], m.open[1], m.close[0], m.close[1],
        M.minutes_of(mk), tick, '{:,}'.format(int(m.point)),
        '1 tick' if m.spread == 1 else '%d ticks' % m.spread,
        money % c['rt'] if money else fmt(c['rt']),
        money % c['stop'] if money else fmt(c['stop']))


t('M1: every market\'s class, day session, minutes, tick, dollars a '
  'point, spread and costs are the rows of the registration; the gates '
  'and the bars of the verdicts are its numbers',
  all(row(mk) in REG for mk in M.MARKETS) and
  list(M.MARKETS) == ['CL', 'NG', 'GC', 'SI', 'HG', '6E', '6J', 'BTC'] and
  M.CLASSES == ('energy', 'metals', 'currencies', 'crypto') and
  {m.cls for m in M.MARKETS.values()} == set(M.CLASSES) and
  M.RULES == ('A', 'B') and M.COMMISSION_RT == 5.0 and
  (M.BREAK_FROM, M.BREAK_TO, M.BREAK_SHARE) == (1020, 1080, 0.001) and
  M.MAX_GAP_DAYS == 5 and M.MIN_SESSIONS == 1500 and
  M.COST_SHARE_MAX == 0.02 and M.TICK_SHARE == 0.01 and
  M.COMPLETE_MISSING == 20 and M.POOL_T == 2.5 and M.BH_Q == 0.10 and
  (M.MIN_MARKETS, M.MIN_CLASSES) == (4, 2) and
  all(x in REG for x in (
      'FROZEN on 2026-11-26', '`trade_a`, `rule_a`, `day_b`, `rule_b`, '
      '`nets`, `judge`', 'at most 20 of its minutes without a bar',
      'every 30 minutes, from 30 minutes after the open to the last such '
      'time that is at least 30 minutes before the close',
      '5 dollars of commission and one spread; a stop one spread more',
      'at least 1 in 100 of the non-zero changes',
      'Fewer than 1 in 1,000 of the market\'s bars may start in that hour',
      'more than 5 calendar days apart', '1,500 eligible sessions or more',
      'is at most **0.02**', '**t of 2.5 or more**',
      'Benjamini and Hochberg at 10 %',
      'at least four markets from at least two classes',
      'A market that was read cannot be left out of it',
      'sessions from 2026-07-01 are never read by this wave',
      'Explicitly NOT registered', 'Expected beforehand')))

# ---------------------------------------------------------------------
# M2: the day session and the costs, set and put back
# ---------------------------------------------------------------------
own = state()
inside = {}
for mk in M.MARKETS:
    with M.setup(mk) as c:
        inside[mk] = (state(), c)
back = state()
try:
    with M.setup('HG', tick=0.001, times=2.0) as c_hg:
        hg2 = state()
        raise RuntimeError('a failure inside')
except RuntimeError:
    pass
back2 = state()
gc, btc = inside['GC'][0], inside['BTC'][0]
t('M2: inside, the reader\'s and the rules\' session is the market\'s '
  '(open, close, the hour marks, the bars a complete session needs, B\'s '
  'times) and the costs its own; bitcoin\'s session is NQ\'s; all is put '
  'back, after a failure too',
  gc[:7] == (30000, 48600, 33600, 31800, 290, 30060, 48300) and
  gc[7:11] == (30000, 48600, 310, tuple(range(30, 271, 30))) and
  near(gc[11], 0.15) and near(gc[12], 0.25) and near(gc[13], 0.075) and
  gc[14].TICK == 0.1 and
  btc[:11] == own[:11] and near(btc[11], 21.0) and near(btc[12], 41.0) and
  btc[14].TICK == 5.0 and
  inside['6E'][0][10] == tuple(range(30, 361, 30)) and
  inside['6E'][0][9] == 400 and inside['CL'][0][10][-1] == 300 and
  inside['HG'][0][10][-1] == 240 and inside['SI'][0][10][-1] == 270 and
  own[7:11] == (34200, 57600, 390, tuple(range(30, 361, 30))) and
  near(own[11], 0.5) and back == own and back2 == own and
  back2[14] is own[14] and
  near(hg2[11], 2 * (0.0002 + 0.001)) and near(hg2[12], 2 * (0.0002 +
                                                             0.002)) and
  hg2[14].TICK == 0.001 and c_hg == dict(tick=0.001, rt=0.0012,
                                         stop=0.0022))


# ---------------------------------------------------------------------
# M3: wave twenty-four's rules on another day session
# ---------------------------------------------------------------------
def mk_day(n, session, o, pc, closes, highs=None, lows=None):
    c = list(closes) + [closes[-1]] * (n - len(closes))
    h = list(highs) + c[len(highs):] if highs else list(c)
    lo = list(lows) + c[len(lows):] if lows else list(c)
    return S.Day(session, 'GC 12-21', o, pc, c, h, lo, [1.0] * n)


with M.setup('GC'):
    n_gc = S.N_MIN
    # up 2.0 in five minutes on a low of 1999: risk 3.0; held to the close
    held = mk_day(n_gc, '20210104', 2000.0, 2000.0,
                  [2000.5, 2001.0, 2001.5, 2002.0, 2002.0] + [2010.0],
                  lows=[1999.0, 2000.5, 2001.0, 2001.5, 2001.8])
    ta_held = S.trade_a(held)
    # the same, stopped in the eighth minute
    stopped = mk_day(n_gc, '20210105', 2000.0, 2000.0,
                     [2000.5, 2001.0, 2001.5, 2002.0, 2002.0, 2002.0,
                      2002.0, 1998.0],
                     lows=[1999.0, 2000.5, 2001.0, 2001.5, 2001.8, 2001.9,
                           2001.9, 1998.0])
    ta_stop = S.trade_a(stopped)
    # a first candle under one tick is no trade
    ta_small = S.trade_a(mk_day(n_gc, '20210106', 2000.0, 2000.0,
                                [2000.0] * 4 + [2000.05],
                                lows=[2000.0] * 5))
    # B: above the noise area from the first half hour, flat at the close
    bday = mk_day(n_gc, '20210104', 2000.0, 2000.0, [2000.0] * 29 + [2020.0])
    b_res = S.day_b(bday, [0.001] * (n_gc + 1))
    # B: out at 270 minutes, the last of its times, back in never
    bout = mk_day(n_gc, '20210104', 2000.0, 2000.0,
                  [2000.0] * 29 + [2020.0] * 240 + [2000.0])
    b_out = S.day_b(bout, [0.001] * (n_gc + 1))
    r_held, r_stop = M.risk_share(held), M.risk_share(stopped)
with M.setup('BTC'):
    ta_btc = S.trade_a(mk_day(390, '20210104', 50000.0, 50000.0,
                              [50010.0] * 5 + [50400.0],
                              lows=[49990.0] * 5))
t('M3: on gold\'s 310 minutes A holds to the session\'s close or is '
  'stopped at gold\'s costs, a risk under gold\'s tick is no trade, B '
  'trades at its times to 270 minutes and is flat at the close; the risk '
  'is the one trade_a used; on bitcoin a target pays bitcoin\'s round trip',
  n_gc == 310 and ta_held['how'] == 'CLOSE' and
  near(ta_held['gross'], 8.0 / 2002.0) and
  near(ta_held['cost'], 0.15 / 2002.0) and near(r_held, 3.0 / 2002.0) and
  near(ta_held['lev'], min(0.01 / r_held, 4.0)) and
  ta_stop['how'] == 'STOP' and near(-ta_stop['gross'], r_stop) and
  near(ta_stop['cost'], 0.25 / 2002.0) and ta_small is None and
  b_res[2] == 2 and near(b_res[0], 0.0) and
  near(b_res[1], 2 * 0.075 / 2000.0) and
  b_out[2] == 2 and near(b_out[0], -20.0 / 2000.0) and
  ta_btc['how'] == 'TARGET' and near(ta_btc['cost'], 21.0 / 50010.0) and
  near(ta_btc['gross'], 10 * 20.0 / 50010.0))

# ---------------------------------------------------------------------
# M4: one number per session; the statistic
# ---------------------------------------------------------------------
with M.setup('GC'):
    days4 = {'20210104': held, '20210105': stopped,
             '20210106': mk_day(n_gc, '20210106', 2000.0, 2000.0,
                                [2000.0] * 6)}
    order4 = sorted(days4)
    tr4 = S.rule_a(days4, order4)[0]
sa = M.series_a(days4, order4, tr4)
order_b = ['202101%02d' % k for k in range(4, 24)]
vol_b = {s: 0.01 for s in order_b}
vol_b['20210120'] = None
sb = M.series_b(order_b, vol_b, [
    dict(session='20210119', gross=0.004, cost=0.001),
    dict(session='20210121', gross=-0.002, cost=0.0005),
    dict(session='20210105', gross=9.9, cost=0.0)])
pairs = [('20201228', 1.0), ('20201229', 2.0), ('20201230', -1.0),
         ('20210104', 3.0), ('20210105', 1.0), ('20210111', 2.0),
         ('20210112', 0.0), ('20210119', 4.0)]
st4 = M.stats(pairs)
weekly = [2.0, 4.0, 2.0, 4.0]          # 2020-W53, 2021-W01, W02, W03
t4 = S.mean(weekly) / (S.stdev(weekly) / 2.0)
t('M4: A in multiples of its risk and B over s, 0 where there is no '
  'trade, B only where it has its 14 sessions and its s; the statistic '
  'sums by ISO week; the halves split at 2021',
  [s for s, _x in sa] == order4 and
  near(sa[0][1], (8.0 - 0.15) / 3.0) and
  near(sa[1][1], (-3.0 - 0.25) / 3.0) and sa[2][1] == 0.0 and
  [s for s, _x in sb] == [s for s in order_b[14:] if s != '20210120'] and
  near(dict(sb)['20210119'], 0.3) and near(dict(sb)['20210121'], -0.25)
  and dict(sb)['20210118'] == 0.0 and
  st4['n'] == 8 and near(st4['mean'], 1.5) and st4['weeks'] == 4 and
  near(st4['t'], t4) and
  near(st4['p'], DI.t_p_two_sided(t4, 3) / 2.0) and
  near(st4['halves']['H1'], 2.0 / 3.0) and
  near(st4['halves']['H2'], 2.0) and st4['positive_halves'] and
  M.week_of('20201231') == '2020-W53' and
  not M.stats([('20210104', 1.0), ('20210105', 2.0)])['positive_halves']
  and M.stats([])['t'] is None and
  M.pool([[('a', 1.0), ('b', 3.0)], [('b', 5.0), ('c', -2.0)],
          [('b', 1.0)]]) == [('a', 1.0), ('b', 3.0), ('c', -2.0)])

# ---------------------------------------------------------------------
# M5: the tick the prices are seen to move in
# ---------------------------------------------------------------------
Ctr = collections.Counter
few = Ctr({0.1: 150})
usual = Ctr({0.1: 300, 0.2: 200, 0.3: 100})
coarse = Ctr({0.1: 5, 0.2: 400, 0.4: 200})          # 0.1 is under 1 in 100


def fake_rd(by_contract):
    """A reader holding sessions whose closes step as given."""
    days = {}
    for c, closes_by_session in by_contract.items():
        for k, closes in enumerate(closes_by_session):
            bars = array.array('d')
            for j, x in enumerate(closes):
                bars.extend((float(j), x, x, x))
            days[(c, '202101%02d' % (k + 4))] = dict(bars=bars)
    return types.SimpleNamespace(days=days)


fine = [100.0 + 0.1 * (0, 1, 3, 2)[j % 4] for j in range(400)]
wide = [100.0 + 0.2 * (0, 1, 3, 2)[j % 4] for j in range(400)]
seen5, per5 = M.observed_tick(fake_rd({'GC 02-21': [fine, fine],
                                       'GC 04-21': [wide],
                                       'GC 06-21': [fine[:50]]}))
seen5b, _p = M.observed_tick(fake_rd({'GC 06-21': [fine[:50]]}))
t('M5: a file\'s tick is the smallest step that makes up 1 in 100 of its '
  'non-zero changes, none with too few changes; the market\'s is the '
  'largest over its files; steps are not taken across sessions',
  M.file_tick(few) is None and near(M.file_tick(usual), 0.1) and
  near(M.file_tick(coarse), 0.2) and M.file_tick(Ctr()) is None and
  near(seen5, 0.2) and near(per5['GC 02-21'], 0.1) and
  near(per5['GC 04-21'], 0.2) and per5['GC 06-21'] is None and
  seen5b is None and
  M.market_costs('GC', 0.2) == dict(tick=0.2, rt=0.25, stop=0.45) and
  M.market_costs('BTC', 10.0) == dict(tick=10.0, rt=41.0, stop=81.0))

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


def stamp(d, minute, shift=0):
    """The UTC end-of-bar stamp of the bar that starts `minute` minutes
    after midnight ET of d (negative: the evening before)."""
    loc = int((_dt.datetime(d.year, d.month, d.day, tzinfo=_dt.timezone.utc)
               - EPOCH).total_seconds()) + minute * 60
    return _dt.datetime.fromtimestamp(
        to_utc(loc) + 60 + shift * 60, _dt.timezone.utc).strftime(
            '%Y%m%d %H%M%S')


def weekdays(a, b):
    d, out = a, []
    while d <= b:
        if d.weekday() < 5:
            out.append(d)
        d += _dt.timedelta(days=1)
    return out


def make(folder, mk, days_, seed, px0, sd, drift=0.0, share=1.0, tick=None,
         contract=None, shift=0, skip=(), vol=900):
    """One contract file of market mk: on every day of days_, bars from
    90 minutes before the open to 20 after the close, and six in the
    evening before (20:00 ET, the same session). A random walk on the
    tick that opens a little back toward px0; on `share` of the days it
    drifts `drift` a minute, from the sixth minute to the close, the way
    the first five went. Returns {date: (O, close)}."""
    m = M.MARKETS[mk]
    tick = tick or m.tick
    o_min = m.open[0] * 60 + m.open[1]
    c_min = m.close[0] * 60 + m.close[1]
    rng = random.Random(seed)
    px = pc = px0
    marks = {}
    os.makedirs(folder, exist_ok=True)
    name = '%s.Last.txt' % (contract or '%s 12-21' % mk)

    def snap(x):
        return round(round(x / tick) * tick, 9)
    with open(os.path.join(folder, name), 'a') as fh:
        for d in days_:
            if d in skip:
                continue
            px = snap(pc + 0.1 * (px0 - pc) + rng.gauss(0, 6.0 * sd))
            for k in range(6):
                fh.write('%s;%r;%r;%r;%r;5\n' % (
                    stamp(d, -4 * 60 + k, shift), px, px, px, px))
            on = rng.random() < share
            side, o_px = 0, px
            for mm in range(o_min - 90, c_min + 20):
                if mm == o_min:
                    o_px = px
                if mm == o_min + 5 and on:
                    side = (px > o_px) - (px < o_px)
                step = rng.gauss(0, sd)
                if o_min + 5 <= mm < c_min:
                    step += side * drift
                o = px
                px = snap(px + step)
                h, lo = snap(max(o, px) + tick), snap(min(o, px) - tick)
                v = 40 if mm < o_min else (3 * vol if mm == o_min else vol)
                fh.write('%s;%r;%r;%r;%r;%d\n' % (stamp(d, mm, shift), o, h,
                                                  lo, px, v))
                if mm == c_min - 1:
                    pc = px
            marks[d] = (o_px, pc)
    return marks


SPAN = weekdays(D(2020, 9, 1), D(2021, 4, 30))          # both halves
M.MIN_SESSIONS = 40

# ---------------------------------------------------------------------
# M6: one market from its exports
# ---------------------------------------------------------------------
f_gc = os.path.join(WORK, 'GC')
marks_gc = make(f_gc, 'GC', SPAN, 11, 1900.0, 0.6, drift=0.05, share=0.8)
rep_gc = M.run_market(f_gc, 'GC')
with M.setup('GC') as c_gc:
    rd6 = M.read(f_gc, 'GC')
    days6, order6, chain6 = S.build(rd6)
    ta6 = S.rule_a(days6, order6)[0]
    tb6 = S.rule_b(days6, order6, chain6)[0]
vol6 = L27.daily_vol(chain6)
d6 = days6[order6[20]]
date6 = D(int(d6.session[:4]), int(d6.session[4:6]), int(d6.session[6:8]))
ra, rb = rep_gc['rules']['A'], rep_gc['rules']['B']
sa6, sb6 = rep_gc['series']['A'], rep_gc['series']['B']
by_a = {x['session']: x for x in ta6}
k6 = [s for s, _x in sa6].index(ta6[7]['session'])
t('M6a: gold is read on its own day session: 310 bars from 08:20, O the '
  'last price before it, the previous close gold\'s 13:30, the evening '
  'bars in the same session; every weekday is a trading day',
  rep_gc['market'] == 'GC' and rep_gc['cls'] == 'metals' and
  rep_gc['day_session'] == '08:20-13:30 ET' and rep_gc['minutes'] == 310
  and rep_gc['trading_days'] == len(SPAN) and
  rep_gc['sessions'] == len(order6) == len(SPAN) - 14 and
  len(d6.c) == 310 and near(d6.o, marks_gc[date6][0]) and
  near(d6.c[-1], marks_gc[date6][1]) and
  near(d6.pc, marks_gc[SPAN[SPAN.index(date6) - 1]][1]) and
  rep_gc['gaps'] == [] and rep_gc['break_share'] == 0.0 and
  rep_gc['left_out'] is None and rep_gc['files'] == 1 and
  rep_gc['refused_from_gate'] == 0)
t('M6b: the report holds wave twenty-four\'s own trades under gold\'s '
  'costs: one number per session for A and for B from its 15th session, '
  'the statistic, the halves and the bar; the planted drift shows',
  ra['trades'] == len(ta6) and rb['trades'] == len(tb6) and
  ra['n'] == len(order6) == len(sa6) and
  rb['n'] == len(order6) - S.B_HISTORY == len(sb6) and
  [s for s, _x in sa6] == order6 and
  near(sa6[k6][1], (ta6[7]['gross'] - ta6[7]['cost']) /
       M.risk_share(days6[ta6[7]['session']]), 1e-5) and
  all(near(x, (dict((y['session'], y) for y in tb6)[s]['gross'] -
               dict((y['session'], y) for y in tb6)[s]['cost']) / vol6[s],
           1e-5) for s, x in sb6[:40]
      if s in {y['session'] for y in tb6}) and
  near(ra['mean'], S.mean([x for _s, x in M.series_a(days6, order6, ta6)]))
  and ra['t'] > 3.0 and rb['t'] > 3.0 and ra['positive_halves'] and
  rb['positive_halves'] and ra['bar']['status'] == 'PASS' and
  rb['bar']['status'] == 'PASS' and
  rep_gc['tick'] == dict(registered=0.1, observed=0.1, used=0.1,
                         files_larger=[]) and
  rep_gc['costs'] == dict(round_trip=0.15, stop=0.25) and
  0.0 < rep_gc['cost_share'] < 0.02 and
  rep_gc['n_trades'] == len(ta6) + len(tb6) and
  'GC (metals)' in M.text(rep_gc) and 'never judged' in M.text(rep_gc))

# the same bars under NQ's name: wave twenty-four's untouched path
f_btc = os.path.join(WORK, 'BTC')
make(f_btc, 'BTC', SPAN, 21, 40000.0, 12.0, drift=1.0, share=0.8,
     tick=0.25)
f_nq = os.path.join(WORK, 'NQ')
os.makedirs(f_nq)
shutil.copy(os.path.join(f_btc, 'BTC 12-21.Last.txt'),
            os.path.join(f_nq, 'NQ 12-21.Last.txt'))
rd_nq, _chk = S.read(f_nq)
days_nq, order_nq, chain_nq = S.build(rd_nq)
a_nq = S.rule_a(days_nq, order_nq)[0]
b_nq = S.rule_b(days_nq, order_nq, chain_nq)[0]
with M.setup('BTC', tick=0.25):
    rd_b = M.read(f_btc, 'BTC')
    days_b, order_b6, chain_b = S.build(rd_b)
    a_b = S.rule_a(days_b, order_b6)[0]
    b_b = S.rule_b(days_b, order_b6, chain_b)[0]
t('M6c: on the stock session the set-up path gives wave twenty-four\'s '
  'own sessions and trades (the same exits, results and sizes; only the '
  'cost is the market\'s)',
  order_b6 == order_nq and len(a_b) == len(a_nq) > 100 and
  len(b_b) == len(b_nq) > 50 and
  all(x['session'] == y['session'] and x['how'] == y['how'] and
      near(x['gross'], y['gross']) and near(x['lev'], y['lev'])
      for x, y in zip(a_b, a_nq)) and
  all(x['session'] == y['session'] and x['changes'] == y['changes'] and
      near(x['gross'], y['gross']) and near(x['lev'], y['lev']) and
      near(x['cost'] / y['cost'], 2.0 / 0.5)
      for x, y in zip(b_b, b_nq)))


# ---------------------------------------------------------------------
# M7: the gates
# ---------------------------------------------------------------------
def stopped_with(fn):
    try:
        fn()
    except CX.ContextDataError as exc:
        return str(exc)
    return None


f_shift = os.path.join(WORK, 'CLshift')
make(f_shift, 'CL', SPAN[:60], 31, 60.0, 0.03, shift=180)
e_stamp = stopped_with(lambda: M.run_market(f_shift, 'CL'))
f_hole = os.path.join(WORK, 'CLhole')
make(f_hole, 'CL', SPAN, 32, 60.0, 0.03, drift=0.002,
     skip=set(weekdays(D(2020, 11, 9), D(2020, 11, 17))))
e_hole = stopped_with(lambda: M.run_market(f_hole, 'CL'))
rep_hole = M.run_market(f_hole, 'CL', gaps_ok=True)
M.MIN_SESSIONS = MIN_SESSIONS
e_few = stopped_with(lambda: M.run_market(f_gc, 'GC'))
M.MIN_SESSIONS = 40
f_6j = os.path.join(WORK, '6J')
make(f_6j, '6J', SPAN, 33, 0.0067, 0.0000008)
rep_6j = M.run_market(f_6j, '6J')
f_wide = os.path.join(WORK, 'SI')
make(f_wide, 'SI', SPAN, 34, 25.0, 0.02, drift=0.002, tick=0.01)
rep_wide = M.run_market(f_wide, 'SI')
e_unknown = stopped_with(lambda: M.run_market(f_gc, 'NQ'))
e_none = stopped_with(lambda: M.run_market(f_gc, 'CL'))
t('M7a: bars in the daily break, a hole of trading days and too few '
  'sessions stop the read with nothing computed; a hole can be read '
  'with --gaps-ok; another market\'s folder and a market outside the '
  'wave stop too',
  e_stamp is not None and 'between 17:00 and 18:00 ET' in e_stamp and
  e_hole is not None and '20201106 and 20201118' in e_hole and
  '--gaps-ok' in e_hole and rep_hole['gaps'] == [['20201106', '20201118']]
  and rep_hole['left_out'] is None and
  e_few is not None and 'only %d eligible GC sessions; 1500 are needed' % (
      len(order6)) in e_few and
  e_unknown is not None and 'unknown market' in e_unknown and
  e_none is not None and 'CL' in e_none)
t('M7b: a market whose round trip is more than 2 % of a normal day\'s '
  'move is LEFT OUT with no rule run; a tick seen larger than the '
  'registered one raises the costs',
  rep_6j['left_out'] is not None and 'the cost gate' in rep_6j['left_out']
  and rep_6j['cost_share'] > 0.02 and rep_6j['rules'] == {} and
  rep_6j['series'] == {} and rep_6j['n_trades'] == 0 and
  'LEFT OUT' in M.text(rep_6j) and 'No rule was run' in M.text(rep_6j) and
  rep_wide['tick'] == dict(registered=0.005, observed=0.01, used=0.01,
                           files_larger=['SI 12-21']) and
  rep_wide['costs'] == dict(round_trip=0.011, stop=0.021) and
  rep_wide['left_out'] is None)

# ---------------------------------------------------------------------
# M8: the gate of the minute reader stands
# ---------------------------------------------------------------------
f_late = os.path.join(WORK, 'NG')
late_span = weekdays(D(2026, 3, 2), D(2026, 8, 14))
make(f_late, 'NG', late_span, 41, 3.0, 0.004, drift=0.0004)
rep_late = M.run_market(f_late, 'NG')
t('M8: sessions from 2026-07-01 are refused: the report ends before '
  'them and holds no number of them',
  rep_late['last_session'] == '20260630' and
  rep_late['refused_from_gate'] == len(
      [d for d in late_span if d >= D(2026, 7, 1)]) and
  max(s for s, _x in rep_late['series']['A']) == '20260630' and
  max(s for s, _x in rep_late['series']['B']) == '20260630' and
  CX.REFUSE_FROM == '20260701')

# ---------------------------------------------------------------------
# M9: the decision, on fabricated series
# ---------------------------------------------------------------------
ALL_DAYS = [d.strftime('%Y%m%d') for d in weekdays(D(2019, 1, 2),
                                                   D(2022, 12, 30))]


def fab(mk, mean_a, mean_b, seed, h1_only=False, left_out=None):
    rng = random.Random(seed)

    def ser(mean):
        out = []
        for s in ALL_DAYS:
            mu = mean if not (h1_only and s >= '20210101') else -mean
            out.append([s, round(mu + rng.gauss(0, 1.0), 6)])
        return out
    rep = dict(wave28=M.W28_VERSION, part='market', market=mk,
               cls=M.MARKETS[mk].cls, left_out=left_out, series={})
    if not left_out:
        rep['series'] = dict(A=ser(mean_a), B=ser(mean_b))
    return rep


# B strong everywhere, A nothing
strong = [fab('CL', 0.0, 0.25, 1), fab('NG', 0.0, 0.25, 2),
          fab('GC', 0.0, 0.25, 3), fab('SI', 0.0, 0.25, 4),
          fab('6E', 0.0, 0.25, 5), fab('6J', 0.0, 0.0, 6,
                                       left_out='the cost gate: x')]
dec = M.decide(strong)
# B strong in metals only, and in energy in the first half only
narrow = [fab('CL', 0.0, 0.5, 11, h1_only=True),
          fab('NG', 0.0, 0.5, 12, h1_only=True),
          fab('GC', 0.0, 0.45, 13), fab('SI', 0.0, 0.45, 14),
          fab('HG', 0.0, 0.45, 15), fab('6E', 0.0, -0.3, 16),
          fab('BTC', 0.0, -0.3, 17)]
dec_n = M.decide(narrow)
tests_n = {(c['rule'], c['cls']): c for c in dec_n['class_tests']}
pool_b = M.pool([[tuple(x) for x in r['series']['B']] for r in strong[:5]])
k9 = 123
few_reps = M.decide(strong[:3])
one_class = M.decide([fab('GC', 0, 0, 1), fab('SI', 0, 0, 2),
                      fab('HG', 0, 0, 3), fab('CL', 0, 0, 4,
                                              left_out='the cost gate: x')])
e_twice = stopped_with(lambda: M.decide(strong[:2] + strong[:1]))
e_foreign = stopped_with(lambda: M.decide([dict(wave28='OTHER',
                                                part='market')]))
qs_n = DI.bh_q([c['p'] for c in dec_n['class_tests']])
t('M9a: a rule whose pooled series has t of 2.5 and is above zero in '
  'both halves HOLDS, and goes on in every class above zero in both '
  'halves; the other rule goes nowhere; a market left out is named and '
  'not pooled',
  dec['decided'] and dec['markets'] == ['CL', 'NG', 'GC', 'SI', '6E'] and
  list(dec['left_out']) == ['6J'] and
  dec['classes'] == ['energy', 'metals', 'currencies'] and
  dec['holds'] == dict(A=False, B=True) and
  dec['pooled']['B']['t'] > 2.5 and dec['pooled']['B']['positive_halves']
  and abs(dec['pooled']['A']['t']) < 2.5 and
  dec['goes_on']['B'] == ['energy', 'metals', 'currencies'] and
  dec['goes_on_markets']['B'] == ['CL', 'NG', 'GC', 'SI', '6E'] and
  dec['goes_on']['A'] == [] and dec['goes_on_markets']['A'] == [] and
  len(dec['class_tests']) == 6 and
  near(pool_b[k9][1], S.mean([r['series']['B'][k9][1]
                              for r in strong[:5]])) and
  near(dec['pooled']['B']['mean'], S.mean([x for _s, x in pool_b])) and
  'HOLDS outside stock indices' in M.text(dec) and
  'B goes on to the shadow step on: CL, NG, GC, SI, 6E' in M.text(dec) and
  'A goes on to the shadow step on: nothing' in M.text(dec) and
  'left out: 6J' in M.text(dec))
t('M9b: where the pooled test fails, only a class kept by Benjamini and '
  'Hochberg and above zero in both halves goes on; a class strong in one '
  'half only does not; the q-values are Benjamini and Hochberg\'s',
  dec_n['decided'] and dec_n['holds'] == dict(A=False, B=False) and
  dec_n['goes_on']['B'] == ['metals'] and
  dec_n['goes_on_markets']['B'] == ['GC', 'SI', 'HG'] and
  dec_n['goes_on']['A'] == [] and len(dec_n['class_tests']) == 8 and
  tests_n[('B', 'metals')]['passes'] and
  tests_n[('B', 'metals')]['q'] <= 0.10 and
  not tests_n[('B', 'energy')]['positive_halves'] and
  not tests_n[('B', 'energy')]['passes'] and
  not tests_n[('B', 'currencies')]['kept'] and
  not tests_n[('B', 'crypto')]['kept'] and
  all((c['q'] is None and q is None) or near(c['q'], q)
      for c, q in zip(dec_n['class_tests'], qs_n)) and
  all(c['kept'] == (c['q'] <= 0.10) for c in dec_n['class_tests']) and
  tests_n[('B', 'metals')]['markets'] == ['GC', 'SI', 'HG'] and
  'does not hold' in M.text(dec_n) and 'PASSES' in M.text(dec_n))
t('M9c: fewer than four markets or one class is no decision; two '
  'reports of one market and a report of something else stop',
  not few_reps['decided'] and '3 markets from 2 classes' in few_reps['why']
  and not one_class['decided'] and
  '3 markets from 1 classes' in one_class['why'] and
  one_class['goes_on'] == {} and 'no decision' in M.text(one_class) and
  e_twice is not None and 'two reports of CL' in e_twice and
  e_foreign is not None and 'not a market report' in e_foreign)

# ---------------------------------------------------------------------
# M10: the command: one read a market, one decision, both on the ledger
# ---------------------------------------------------------------------
led = os.path.join(WORK, 'ledger.json')
with open(led, 'w') as fh:
    json.dump(dict(reads=[dict(version='SOMETHING-EARLIER', part='market',
                               market='GC')]), fh)
f_cl = os.path.join(WORK, 'CL')
make(f_cl, 'CL', SPAN, 51, 60.0, 0.03, drift=0.002, share=0.8)
f_hg = os.path.join(WORK, 'HG')
make(f_hg, 'HG', SPAN, 52, 4.0, 0.002, drift=0.0001, share=0.8)
outs = {mk: os.path.join(WORK, 'w28_%s.json' % mk.lower())
        for mk in ('GC', 'CL', 'HG', '6J', 'NG')}
rc_noout, said_noout = said_by(lambda: M.main([f_gc, '--market', 'GC'],
                                              ledger=led))
rc_bad, said_bad = said_by(lambda: M.main(
    [f_gc, '--market', 'GC', '--out', os.path.join(WORK, 'no', 'x.json')],
    ledger=led))
rc_mkt, said_mkt = said_by(lambda: M.main([f_gc, '--market', 'ES', '--out',
                                           outs['GC']], ledger=led))
rc_stop, said_stop = said_by(lambda: M.main(
    [f_hole, '--market', 'CL', '--out', outs['CL']], ledger=led))
nothing_yet = (len(json.load(open(led))['reads']) == 1 and
               not os.path.exists(outs['CL']))
rc_gc, said_gc = said_by(lambda: M.main([f_gc, '--market', 'gc', '--out',
                                         outs['GC']], ledger=led))
rc_again, said_again = said_by(lambda: M.main(
    [f_gc, '--market', 'GC', '--out', outs['GC']], ledger=led))
rc_cl, _s = said_by(lambda: M.main([f_cl, '--market', 'CL', '--out',
                                    outs['CL']], ledger=led))
rc_6j, said_6j = said_by(lambda: M.main([f_6j, '--market', '6J', '--out',
                                         outs['6J']], ledger=led))
doc10 = json.load(open(led))
mine10 = [r for r in doc10['reads'] if r['version'] == M.W28_VERSION]
t('M10a: a market is read once and the read is on the ledger before a '
  'result is shown; the report file is needed; a stop reads nothing and '
  'records nothing; a market left out is recorded as read',
  rc_noout == 2 and 'give --out' in said_noout and
  rc_bad == 2 and 'cannot be written' in said_bad and
  rc_mkt == 2 and '--market is one of CL' in said_mkt and
  rc_stop == 2 and 'STOPPED' in said_stop and nothing_yet and
  rc_gc == 0 and 'read recorded' in said_gc and
  json.load(open(outs['GC']))['rules']['A']['trades'] ==
  rep_gc['rules']['A']['trades'] and
  rc_again == 2 and 'REFUSED' in said_again and 'read GC' in said_again and
  rc_cl == 0 and rc_6j == 0 and 'LEFT OUT' in said_6j and
  [(r['part'], r['market'], r['left_out']) for r in mine10] == [
      ('market', 'GC', False), ('market', 'CL', False),
      ('market', '6J', True)] and
  doc10['reads'][0]['version'] == 'SOMETHING-EARLIER' and
  mine10[0]['first'] == rep_gc['first_session'] and
  mine10[0]['n'] == rep_gc['n_trades'] and M.read_made(led, 'GC') and
  not M.read_made(led, 'HG') and not M.decision_made(led))

dec_out = os.path.join(WORK, 'w28.json')
rc_dry, said_dry = said_by(lambda: M.main(
    ['--decide', outs['GC'], outs['CL'], outs['6J']], ledger=led))
rc_miss, said_miss = said_by(lambda: M.main(
    ['--decide', outs['GC'], outs['CL'], '--final'], ledger=led))
foreign = os.path.join(WORK, 'w28_btc.json')
with open(foreign, 'w') as fh:
    json.dump(fab('BTC', 0.0, 0.3, 9), fh)
rc_for, said_for = said_by(lambda: M.main(
    ['--decide', outs['GC'], outs['CL'], outs['6J'], foreign, '--final'],
    ledger=led))
rc_three, said_three = said_by(lambda: M.main(
    ['--decide', outs['GC'], outs['CL'], outs['6J'], '--final'],
    ledger=led))
still_open = not M.decision_made(led)
rc_hg, _s = said_by(lambda: M.main([f_hg, '--market', 'HG', '--out',
                                    outs['HG']], ledger=led))
rc_ng, _s = said_by(lambda: M.main([f_late, '--market', 'NG', '--out',
                                    outs['NG']], ledger=led))
five = [outs[mk] for mk in ('GC', 'CL', 'HG', '6J', 'NG')]
rc_dec, said_dec = said_by(lambda: M.main(
    ['--decide'] + five + ['--final', '--out', dec_out], ledger=led))
rc_dec2, said_dec2 = said_by(lambda: M.main(
    ['--decide'] + five + ['--final'], ledger=led))
rc_after, said_after = said_by(lambda: M.main(
    [f_wide, '--market', 'SI', '--out', os.path.join(WORK, 'si.json')],
    ledger=led))
rc_garbage, said_garbage = said_by(lambda: M.main(
    ['--decide', os.path.join(WORK, 'nothing.json')],
    ledger=os.path.join(WORK, 'other_ledger.json')))
doc10b = json.load(open(led))
dec10 = json.load(open(dec_out))
t('M10b: the decision says first what it would be made on and computes '
  'nothing; it needs every market the wave has read and takes no report '
  'the ledger does not know; with --final it is made once and recorded, '
  'and no market is read after it',
  rc_dry == 0 and 'would be made on: 6J, CL, GC' in said_dry and
  'Nothing was computed' in said_dry and 'Add --final' in said_dry and
  'left out for good: NG, SI, HG, 6E, BTC' in said_dry and
  rc_miss == 2 and '6J was read by this wave' in said_miss and
  rc_for == 2 and 'no read of BTC' in said_for and
  rc_three == 2 and 'no decision' in said_three and
  'Nothing was recorded' in said_three and still_open and
  rc_hg == 0 and rc_ng == 0 and
  rc_dec == 0 and 'THE DECISION' in said_dec and
  'decision recorded' in said_dec and
  dec10['markets'] == ['GC', 'CL', 'HG', 'NG'] and
  list(dec10['left_out']) == ['6J'] and dec10['decided'] and
  dec10['classes'] == ['energy', 'metals'] and
  doc10b['reads'][-1]['part'] == 'decide' and
  doc10b['reads'][-1]['markets'] == ['6J', 'CL', 'GC', 'HG', 'NG'] and
  rc_dec2 == 2 and 'has been made' in said_dec2 and
  rc_after == 2 and 'no market is read after it' in said_after and
  not os.path.exists(os.path.join(WORK, 'si.json')) and
  rc_garbage == 2 and 'cannot read the reports' in said_garbage)

home_after = open(HOME_LEDGER, 'rb').read() \
    if os.path.exists(HOME_LEDGER) else None
rc_usage, said_usage = said_by(lambda: M.main([]))
t('M10c: nothing here touched the real ledger; the rules are as wave '
  'twenty-four left them',
  home_after == home_before and state() == own and rc_usage == 2 and
  'mrofyt_markets28.py' in said_usage and
  CX.REFUSE_FROM == '20260701' and S.N_MIN == 390 and
  near(S.RT, 0.5) and near(S.RT_STOP, 0.75))

M.MIN_SESSIONS = MIN_SESSIONS
shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
