#!/usr/bin/env python3
# MROF-YT-W22-STRETCHFADE-1.0 suite. The bar VWAP, the split, the trades
# and the two verdicts are exercised on hand-built bars and trades with
# known answers; the reader against part 16A's on synthetic
# NinjaTrader-format NQ exports (one contract, and two with a roll); the
# pipeline end to end on a planted export across the 2019-06-01 split,
# every count re-derived from the plan. Synthetic data verifies CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import array
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
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mrofyt_context as CX          # noqa: E402
import mrofyt_l2context as X         # noqa: E402
import mrofyt_l2targets as W         # noqa: E402
import mrofyt_ledgers as LG          # noqa: E402
import mrofyt_minutelevels as ML     # noqa: E402
import mrofyt_stretchfade as SF      # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w22_')
A = lambda *v: array.array('d', v)                    # noqa: E731

# ---------------------------------------------------------------------
# SF1: the session VWAP on bars
# ---------------------------------------------------------------------
bars1 = A(-300, 101, 99, 100,    0, 104, 100, 103,
          60, 106, 102, 105,     -240, 100, 100, 100)
rows1, vw1 = SF.rows_vwap(bars1, A(10, 20, 0, 30))
rows0, vw0 = SF.rows_vwap(A(0, 5, 3, 4, 60, 6, 4, 5), A(0, 2))
t('SF1: the bars come in time order whatever the file\'s order; the VWAP '
  'at each close is the sum of (high + low + close) / 3 x volume over the '
  'sum of volume from the session\'s first bar; a bar without volume '
  'leaves it; there is none until a bar has traded',
  rows1 == ML._rows(bars1) and
  [r[0] for r in rows1] == [-300.0, -240.0, 0.0, 60.0] and
  vw1[0] == 100.0 and vw1[1] == 100.0 and
  abs(vw1[2] - (100.0 * 10 + 100.0 * 30 + 307.0 / 3 * 20) / 60) < 1e-9 and
  vw1[3] == vw1[2] and vw0 == [None, 5.0])

# ---------------------------------------------------------------------
# SF2: the split is wave twelve's rule, unchanged
# ---------------------------------------------------------------------
t('SF2: STRETCHED is a close at least 0.25 x A from VWAP with the fade '
  'trading back toward it (a short above, a long below): the trades wave '
  'twelve\'s TREND filter removed; a fade away from VWAP, or a closer '
  'one, is REST; without A or a VWAP a signal is in neither',
  SF.STRETCH_K == X.TREND_K == 0.25 and
  (SF.RANGE_SESSIONS, SF.RANGE_MIN_SESSIONS) ==
  (W.RANGE_SESSIONS, W.RANGE_MIN_SESSIONS) == (14, 5) and
  SF.group_of(-1, 125.0, 100.0, 100.0) == 'STRETCHED' and
  SF.group_of(-1, 124.75, 100.0, 100.0) == 'REST' and
  SF.group_of(1, 75.0, 100.0, 100.0) == 'STRETCHED' and
  SF.group_of(1, 130.0, 100.0, 100.0) == 'REST' and
  SF.group_of(-1, 70.0, 100.0, 100.0) == 'REST' and
  SF.group_of(-1, 130.0, None, 100.0) is None and
  SF.group_of(-1, 130.0, 100.0, None) is None and
  all((SF.group_of(d, c, 100.0, 40.0) == 'STRETCHED') ==
      (X.classify(d, c, 100.0, None, 40.0)['TREND'] == 'removed')
      for d in (-1, 1) for c in (85.0, 90.0, 95.0, 100.0, 105.0, 110.0,
                                 115.0)))

# ---------------------------------------------------------------------
# SF3: one session by hand
# ---------------------------------------------------------------------
O = 34200.0                                           # 09:30 ET
day3 = dict(
    bars=A(-3600, 100.25, 99.75, 100.0,      # the evening: VWAP 100
           O, 105.0, 100.0, 105.0,           # up through last week's low 104
           O + 60, 109.75, 105.0, 109.5,     # under yesterday's high 110
           O + 120, 110.5, 109.0, 109.25,    # 2 ticks through, closed back
           O + 180, 109.25, 106.0, 107.0,
           O + 240, 107.0, 105.5, 106.0,     # 104 held from above
           O + 300, 106.0, 103.5, 104.5,     # 2 ticks under 104, closed back
           O + 360, 104.5, 88.0, 89.0,       # the long is stopped (89.5)
           O + 420, 89.0, 84.0, 85.0),       # the short reaches 84.25
    vols=A(1000, 10, 10, 10, 10, 10, 10, 10, 10),
    yday=(110.0, 50.0), lweek=(200.0, 104.0), a=32.0)
rows3, sig3 = SF.session_signals(day3)
vw3 = SF.rows_vwap(day3['bars'], day3['vols'])[1]
tr3 = dict((g, SF.take(rows3, [x for x in sig3 if x['group'] == g], 'S'))
           for g in SF.GROUPS)
ev3 = SF.take(rows3, sig3, 'S')
_r, sig3n = SF.session_signals(dict(day3, a=None))
t('SF3: one session by hand: a failed break of yesterday\'s high far above '
  'VWAP is a STRETCHED short; a failed break down through last week\'s '
  'low, above VWAP, is a REST long (it trades away from VWAP); each group '
  'trades one position at a time on its own (25 / 15 / 30 min on the next '
  'bars, costs charged); unsplit, the long falls inside the short\'s '
  'trade; without A the signals are in neither group',
  [(x['i'], x['level_id'], x['direction'], x['close'], x['group'],
    x['first']) for x in sig3] ==
  [(3, 'YDAY_HIGH', -1, 109.25, 'STRETCHED', True),
   (6, 'LWEEK_LOW', 1, 104.5, 'REST', True)] and
  abs(sig3[0]['dist'] - (109.25 - vw3[3])) < 1e-12 and
  sig3[0]['dist'] >= 0.25 * 32.0 and 0 < sig3[1]['dist'] < 0.25 * 32.0 and
  [(x['outcome'], x['net'], x['key'], x['group'], x['month'], x['year'])
   for x in tr3['STRETCHED']] ==
  [('TARGET', 24.5, O + 180, 'STRETCHED', 'S', 'S')] and
  [(x['outcome'], x['net'], x['key'], x['direction'])
   for x in tr3['REST']] == [('STOP', -15.75, O + 360, 1)] and
  [(x['level_id'], x['outcome']) for x in ev3] == [('YDAY_HIGH', 'TARGET')]
  and [x['group'] for x in sig3n] == [None, None])


# ---------------------------------------------------------------------
# SF4: the reader is part 16A's, with the volume and the scale
# ---------------------------------------------------------------------
EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)
MINS = list(range(-6 * 60, 9 * 60 + 30, 5)) + \
    list(range(9 * 60 + 30, 16 * 60 + 15)) + \
    list(range(16 * 60 + 15, 17 * 60, 5))


def to_utc(local_epoch):
    y = _dt.datetime.fromtimestamp(local_epoch, _dt.timezone.utc).year
    for off in (4, 5):
        u = local_epoch + off * 3600
        w = CX._dst_window(y)
        if (off == 4) == (w[0] <= u < w[1]):
            return u
    return local_epoch + 5 * 3600


def stamp(d, m):
    base = int((_dt.datetime(d.year, d.month, d.day,
                             tzinfo=_dt.timezone.utc) - EPOCH)
               .total_seconds())
    u = to_utc(base + m * 60) + 60                    # UTC, END of the bar
    return _dt.datetime.fromtimestamp(u, _dt.timezone.utc).strftime(
        '%Y%m%d %H%M%S')


def sessions_from(start, n):
    d, out = start, []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += _dt.timedelta(days=1)
    return out


def write_random(folder, days, name, seed, vscale=1, px=8000.0):
    """A random walk: {session: (full high, full low)} and {session:
    volumes in file order} as written."""
    os.makedirs(folder, exist_ok=True)
    rng = random.Random(seed)
    rows, full, vols = [], {}, {}
    for d in days:
        ses = d.strftime('%Y%m%d')
        hi = lo_ = None
        vs = []
        for m in MINS:
            px += rng.gauss(0, 1.5)
            o = round(px * 4) / 4
            h = o + 0.25 * rng.randint(0, 8)
            lo = o - 0.25 * rng.randint(0, 8)
            c = round(rng.uniform(lo, h) * 4) / 4
            hi = h if hi is None else max(hi, h)
            lo_ = lo if lo_ is None else min(lo_, lo)
            v = vscale * (rng.randint(50, 150) if m < 570 else
                          (3000 if m == 570 else rng.randint(600, 1200)))
            vs.append(float(v))
            rows.append('%s;%.2f;%.2f;%.2f;%.2f;%d' % (stamp(d, m), o, h, lo,
                                                       c, v))
        full[ses], vols[ses] = (hi, lo_), vs
    with open(os.path.join(folder, name), 'w') as fh:
        fh.write('\n'.join(rows) + '\n')
    return full, vols


def same_days(mine, theirs):
    return sorted(mine) == sorted(theirs) and all(
        mine[s]['contract'] == theirs[s]['contract'] and
        mine[s]['bars'] == theirs[s]['bars'] and
        mine[s]['yday'] == theirs[s]['yday'] and
        mine[s]['lweek'] == theirs[s]['lweek'] for s in theirs)


def plain(tr):
    return [(x['session'], x['key'], x['level_id'], x['direction'],
             x['outcome'], x['net']) for x in tr]


DAYS = sessions_from(_dt.date(2019, 3, 18), 110)      # spans 2019-06-01
F1 = os.path.join(WORK, 'one')
FULL, VOLS = write_random(F1, DAYS, 'NQ 06-19.Last.txt', 3)
dev, rd1, chk1 = SF.history_sessions(F1, CX.is_dev)
val, _rv, _cv = SF.history_sessions(F1, CX.is_validation)
dev16, _r16, chk16 = ML.history_sessions(F1, CX.is_dev)
val16 = ML.history_sessions(F1, CX.is_validation)[0]
kept = sorted(s for s in FULL if CX.is_dev(s))
s4 = sorted(dev)[5]
j4 = kept.index(s4)
F2 = os.path.join(WORK, 'two')                       # the roll in July
write_random(F2, DAYS[:90], 'NQ 06-19.Last.txt', 5)
write_random(F2, DAYS[80:], 'NQ 09-19.Last.txt', 6, vscale=2, px=8050.0)
roll, _rr, _cr = SF.history_sessions(F2, CX.is_dev)
roll16 = ML.history_sessions(F2, CX.is_dev)[0]
tr4, cnt4 = SF.history_trades(dev)
n_by_group = {g: 0 for g in SF.GROUPS + (None,)}
for s in dev:
    for x in SF.session_signals(dev[s])[1]:
        n_by_group[x['group']] += 1
t('SF4: the reader gives part 16A\'s sessions, front contract, bars and '
  'levels exactly, on one contract and across a roll, with each bar\'s '
  'volume beside it; A is the mean full range of the 14 sessions before; '
  'unsplit, the trades are part 16A\'s "every" trade for trade; every '
  'signal is in exactly one group or in neither; the two eras never mix',
  chk1 == chk16 and chk1['open_minute'] == '09:30' and dev and val and
  same_days(dev, dev16) and same_days(val, val16) and
  same_days(roll, roll16) and len({d['contract'] for d in
                                   roll.values()}) == 2 and
  min(dev) >= '20190601' and max(val) < '20190601' and
  all(list(dev[s]['vols']) == VOLS[s] for s in dev) and
  all(len(d['vols']) * 4 == len(d['bars']) for d in roll.values()) and
  j4 >= 14 and abs(dev[s4]['a'] - sum(FULL[p][0] - FULL[p][1]
                                      for p in kept[j4 - 14:j4]) / 14.0)
  < 1e-9 and
  plain(tr4['EVERY']) == plain(ML.history_trades(dev16)['every']) and
  tr4['EVERY'] and tr4['STRETCHED'] and tr4['REST'] and
  cnt4['signals'] == sum(n_by_group.values()) and
  cnt4['unsplit'] == n_by_group[None] == 0 and
  all(x['group'] == g for g in SF.GROUPS for x in tr4[g]) and
  all(abs(x['dist']) >= 0.25 * dev[x['session']]['a'] - 1e-9 and
      x['direction'] * x['dist'] < 0 for x in tr4['STRETCHED']) and
  len(tr4['FIRST_STRETCHED']) <= len(tr4['STRETCHED']) and
  len(tr4['FIRST_REST']) <= len(tr4['REST']))


# ---------------------------------------------------------------------
# SF5: the two verdicts and Holm
# ---------------------------------------------------------------------
def months(values, per=10, start=0):
    """per trades in each month, every trade of month i at values[i]."""
    return [dict(month='2020%02d' % (start + i + 1), net=v)
            for i, v in enumerate(values) for _k in range(per)]


good = SF.verdicts(dict(STRETCHED=months([17.0, 15.0] * 6),
                        REST=months([-4.0, -3.0] * 6)))
few = SF.verdicts(dict(STRETCHED=months([17.0, 15.0] * 6)[:99],
                       REST=months([-4.0, -3.0] * 6)))
flat = SF.verdicts(dict(STRETCHED=months([-4.0, -3.0] * 6),
                        REST=months([17.0, 15.0] * 6)))
# ST1 alone would pass (p about 0.034), ST2 is noise: Holm over the two
edge = SF.verdicts(dict(STRETCHED=months([17.3, -2.7] * 6),
                        REST=months([60.0, -60.0] * 6)))
t('SF5: ST1 passes with 100+ trades, the month-clustered 95 % range above '
  '0 and a profit without the best month; ST2 passes when STRETCHED minus '
  'REST is above 0 with its range above 0 and 100+ trades on each side; '
  'under 100 neither is judged; a pass that Holm over the two does not '
  'reject is NOT PROVEN',
  [x['test'] for x in good] == ['ST1', 'ST2'] and
  [x['status'] for x in good] == ['PASS', 'PASS'] and
  [x['holm_rejected'] for x in good] == [True, True] and
  good[0]['n'] == 120 and good[0]['net_points'] == 16.0 and
  good[1]['n'] == 120 and good[1]['n_rest'] == 120 and
  good[1]['diff'] == 19.5 and good[1]['ci95'][0] > 0 and
  [x['status'] for x in few] == ['NOT ENOUGH TRADES'] * 2 and
  few[0]['reasons'] == ['99 of the 100 needed'] and
  few[1]['reasons'] == ['99 and 120 of the 100 needed on each side'] and
  [x['holm_rejected'] for x in few] == [False, False] and
  [x['status'] for x in flat] == ['NOT PROVEN', 'NOT PROVEN'] and
  flat[0]['reasons'] == ['loses after costs'] and
  flat[1]['reasons'] == ['the stretched trades do no better than the rest']
  and 0.025 < edge[0]['p'] < 0.05 and edge[0]['ci95'][0] > 0 and
  edge[0]['without_best']['net_points'] > 0 and
  edge[0]['status'] == 'NOT PROVEN' and
  edge[0]['reasons'] == ['could be luck after allowing for two tests '
                         '(Holm)'] and
  edge[1]['status'] == 'NOT PROVEN' and
  edge[1]['reasons'] == ['could be luck: the 95 % range reaches zero'] and
  [x['holm_rejected'] for x in edge] == [False, False] and
  SF.MIN_TRADES == 100)


# ---------------------------------------------------------------------
# SF6: end to end on a planted export
# ---------------------------------------------------------------------
def planted_day(kind):
    """{minute: (open, high, low, close, volume)} of one session.
    Overnight flat at 15000 (range 14999-15001). 09:31 pokes 2 ticks over
    the overnight high and closes back at 15000, next to VWAP: a REST
    short, stopped by the rally to 15049. 'A': the rally touches 15050.
    'W' / 'L' (the day after an A day): 10:01 pokes 2 ticks over
    yesterday's high 15050 and closes back at 15049, far above VWAP: a
    STRETCHED short that reaches its target ('W') or is stopped ('L')."""
    out = {}
    for m in MINS:
        if m < 570:
            out[m] = (15000.0, 15001.0, 14999.0, 15000.0, 100)
        else:
            out[m] = (15000.0, 15000.25, 14999.75, 15000.0,
                      900 if m < 975 else 100)
    out[570] = (15000.0, 15000.75, 14999.25, 15000.0, 3000)
    out[571] = (15000.0, 15001.5, 14999.5, 15000.0, 900)
    prev = 15000.0
    for m in range(572, 601):                          # the rally
        c = 15000.0 + round(4 * 49.0 * (m - 571) / 29.0) / 4.0
        out[m] = (prev, c, prev, c, 900)
        prev = c
    top = 15050.0 if kind == 'A' else 15050.5
    out[601] = (prev, top, 15048.75, 15049.0, 900)
    prev, m = 15049.0, 602
    if kind == 'L':
        for c in (15054.0, 15059.0, 15065.0):          # through 15064
            out[m] = (prev, c, prev, c, 900)
            prev, m = c, m + 1
        for _k in range(8):                            # held above
            out[m] = (prev, max(prev, 15060.0), 15060.0, 15060.0, 900)
            prev, m = 15060.0, m + 1
    while prev > 15000.0:                              # back to 15000
        c = max(15000.0, prev - (5.0 if kind != 'L' else 10.0))
        out[m] = (prev, prev, c, c, 900)
        prev, m = c, m + 1
    return out


def write_planted(folder, days, name):
    """Days alternate A, then W or L (every fifth of those an L). Returns
    {session: kind}."""
    os.makedirs(folder, exist_ok=True)
    rows, kinds, b = [], {}, 0
    for k, d in enumerate(days):
        if k % 2 == 0:
            kind = 'A'
        else:
            kind = 'L' if b % 5 == 4 else 'W'
            b += 1
        kinds[d.strftime('%Y%m%d')] = kind
        day = planted_day(kind)
        for m in MINS:
            o, h, lo, c, v = day[m]
            rows.append('%s;%.2f;%.2f;%.2f;%.2f;%d' % (stamp(d, m), o, h, lo,
                                                       c, v))
    with open(os.path.join(folder, name), 'w') as fh:
        fh.write('\n'.join(rows) + '\n')
    return kinds


PD = sessions_from(_dt.date(2018, 11, 5), 400)
F3 = os.path.join(WORK, 'planted')
KINDS = write_planted(F3, PD, 'NQ 12-19.Last.txt')
repN = SF.run(F3)
repO = SF.run(F3, unblind=True)


def plan(era_ok):
    """(W days, L days, all days) among the era's sessions after its
    first 14, which have no 14 sessions of history."""
    ses = sorted(s for s in KINDS if era_ok(s))[14:]
    return (sum(1 for s in ses if KINDS[s] == 'W'),
            sum(1 for s in ses if KINDS[s] == 'L'), len(ses))


wN, lN, dN = plan(CX.is_dev)
wO, lO, dO = plan(CX.is_validation)
st1, st2 = repN['tests']
bN = repN['beside']
led = os.path.join(WORK, 'hist_ledger.json')
LG.record_history_read(repO, led, SF.W22_VERSION)
L = json.load(open(led))
txtN, txtO = SF.text(repN), SF.text(repO)
t('SF6: end to end on a planted export: every session after the first 14 '
  'gives one REST short at the overnight high, stopped; every second one '
  'a STRETCHED short at yesterday\'s high, a winner four times in five; '
  'the counts, win rate and net are those of the plan and no other signal '
  'appears; ST1 and ST2 pass on the newer years; the older years are read '
  'only with --unblind, hold too few trades to judge, and are recorded '
  'with their range; both reports render',
  wN + lN >= 100 and st1['n'] == wN + lN == repN['n_trades'] and
  st1['won'] == round(wN / float(wN + lN), 4) and
  st1['net_points'] == round((24.5 * wN - 15.75 * lN) / (wN + lN), 3) and
  st1['status'] == 'PASS' and st1['holm_rejected'] and
  st2['n_rest'] == dN and st2['mean_b'] == -15.75 and
  st2['status'] == 'PASS' and st2['diff'] == round(
      (24.5 * wN - 15.75 * lN) / (wN + lN) + 15.75, 4) and
  repN['signals'] == dN + wN + lN and repN['unsplit'] == 0 and
  bN['rest'] == dict(n=dN, won=0.0, net_points=-15.75,
                     total_points=round(-15.75 * dN, 2)) and
  bN['every']['n'] == dN + wN + lN and
  bN['first']['stretched']['n'] == wN + lN and
  bN['first']['rest']['n'] == dN and
  bN['by_direction']['long'] == dict(n=0) and
  bN['by_direction']['short']['n'] == wN + lN and
  bN['by_level']['YDAY_HIGH']['n'] == wN + lN and
  all(bN['by_level'][k] == dict(n=0) for k in ML.LEVEL_IDS
      if k != 'YDAY_HIGH') and
  sum(v['stretched']['n'] for v in bN['by_year'].values()) == wN + lN and
  sum(v['rest']['n'] for v in bN['by_year'].values()) == dN and
  repN['first_session'] >= '20190601' and repN['era'] == 'newer' and
  repN['stamp_check']['open_minute'] == '09:30' and
  repN['files'][0]['contract'] == 'NQ 12-19' and
  0 < wO + lO < 100 and repO['tests'][0]['n'] == wO + lO and
  [x['status'] for x in repO['tests']] == ['NOT ENOUGH TRADES'] * 2 and
  repO['last_session'] < '20190601' and repO['era'] == 'older' and
  repO['beside']['rest']['n'] == dO and
  L['reads'][0]['version'] == SF.W22_VERSION and
  L['reads'][0]['last'] == repO['last_session'] and
  L['reads'][0]['n'] == wO + lO and
  'VERDICT: PASS' in txtN and 'NEWER YEARS' in txtN and
  'run the same command with --unblind' in txtN and
  'OLDER YEARS' in txtO and 'VERDICT: NOT ENOUGH TRADES' in txtO and
  json.dumps(repN, default=str) and json.dumps(repO, default=str))

# ---------------------------------------------------------------------
# SF7: the command, the stops and the registration
# ---------------------------------------------------------------------
out7 = os.path.join(WORK, 'w22.json')
buf = io.StringIO()
with redirect_stdout(buf):
    rc0 = SF.main([])
    rc_flag = SF.main(['--unblind'])
    rc_none = SF.main([os.path.join(WORK, 'no_such_folder')])
    rc_tz = SF.main([F3, '--stamps-tz', 'ET'])
    rc_ok = SF.main([F3, '--out', out7])
said = buf.getvalue()
_reg = open(os.path.join(HERE, SF.REGISTRATION), encoding='utf-8').read()
t('SF7: the command prints the report and writes it; no folder, a missing '
  'folder or time stamps in the wrong zone stop before anything is '
  'computed; the registration states the signal, the stretch, the two '
  'tests, the two eras, what was seen beforehand and what is not '
  'registered',
  rc0 == 2 and rc_flag == 2 and rc_none == 2 and rc_tz == 2 and
  rc_ok == 0 and 'STOPPED: cannot read' in said and
  'not 09:30' in said and 'Nothing was computed' in said and
  json.load(open(out7))['tests'][0]['status'] == 'PASS' and
  'wave-twenty-two report ->' in said and
  not os.path.exists(os.path.join(WORK, SF.HISTORY_LEDGER)) and
  all(x in _reg for x in (
      'FROZEN on 2026-11-17', '**Every signal**',
      '`(high + low + close) / 3 × volume`', '**5 at least**',
      '`|c − VWAP| >= 0.25 × A`', 'back\n  toward VWAP',
      '| **ST1** |', '| **ST2** |', '**Holm over the two**',
      'at least 100 trades', '| **NEWER** |', '| **OLDER** |',
      '**CONFIRMED:** ST1 passes in both eras', '**ONE ERA ONLY:**',
      '104 trades, 46.2 % won, +2.83', 'low prior',
      'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
