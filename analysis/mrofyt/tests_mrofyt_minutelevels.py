#!/usr/bin/env python3
# MROF-YT-W16A-MINUTELEVELS-1.0 suite. The minute-bar signal, the trade
# and the month-clustered verdict are exercised on hand-built bars with
# known answers; the history pipeline on synthetic NinjaTrader-format NQ
# exports across the 2019-06-01 split; the recordings pipeline on
# synthetic recorder-format runs (mles_v12_synth) with wave six's
# suite-only plumbing L2 detector, restored afterwards. Synthetic data
# verifies CODE BEHAVIOR only, never market evidence. No order, fill or
# P&L exists.
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
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY          # noqa: E402
import mrofyt_bigmove as BM          # noqa: E402
import mrofyt_closereclaim as C      # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_l2firstsignal as FS    # noqa: E402
import mrofyt_ledgers as LG          # noqa: E402
import mrofyt_minutelevels as ML     # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w16a_')
LV = {'YDAY_HIGH': 100.0}
at = lambda i: LV                                    # noqa: E731

# ---------------------------------------------------------------------
# ML1: the signal
# ---------------------------------------------------------------------
wick = [(0, 99.5, 99.0, 99.25), (60, 100.5, 99.5, 99.5)]
late = [(0, 99.5, 99.0, 99.25), (60, 100.75, 99.5, 100.5),
        (120, 101.0, 100.25, 100.5), (180, 100.5, 99.5, 99.5)]
held = [(0, 99.5, 99.0, 99.25)] + \
    [(60 * k, 101.0, 100.25, 100.5) for k in range(1, 6)] + \
    [(360, 100.75, 99.5, 100.5)]            # down poke from above, back up
poke1 = [(0, 99.5, 99.0, 99.25), (60, 100.25, 99.5, 99.5)]
s_w, s_l, s_h, s_p = (ML.signals(b, at) for b in (wick, late, held, poke1))
two = ML.signals(wick + [(120, 99.5, 99.0, 99.25), (180, 100.5, 99.5, 99.5)],
                 lambda i: dict(YDAY_HIGH=100.0, LWEEK_HIGH=99.0
                                if i >= 2 else None))
t('ML1: a bar 2 ticks through and a close back within 5 bars is a signal '
  'at that close, fading the break (the break bar itself counts); 5 '
  'closes through is held and flips the side, so a later poke back is a '
  'signal the other way; a 1-tick poke is nothing; only the first per '
  'level is kept',
  [(x['i'], x['direction']) for x in s_w] == [(1, -1)] and
  [(x['i'], x['direction']) for x in s_l] == [(3, -1)] and
  [(x['i'], x['direction']) for x in s_h] == [(6, 1)] and s_p == [] and
  [(x['i'], x['level_id']) for x in two] == [(1, 'YDAY_HIGH'),
                                            (3, 'YDAY_HIGH')] and
  [(x['i'], x['level_id']) for x in ML.first_per_level(two)] ==
  [(1, 'YDAY_HIGH')])

# ---------------------------------------------------------------------
# ML2: the trade on minute bars
# ---------------------------------------------------------------------
B0 = [(0, 100.5, 99.5, 100.0)]
tgt = ML.outcome_bars(B0 + [(60, 101.0, 74.75, 80.0)], 0, -1, 100.0)
both = ML.outcome_bars(B0 + [(60, 115.0, 75.0, 90.0)], 0, -1, 100.0)
tmo = ML.outcome_bars(B0 + [(60 * k, 99.0, 97.0, 98.0) for k in range(1, 40)],
                      0, -1, 100.0)
short = ML.outcome_bars(B0 + [(60 * k, 99.0, 97.0, 98.0)
                              for k in range(1, 11)], 0, -1, 100.0)
t('ML2: first touch of 25 / 15 on the next bars (a bar touching both is a '
  'stop), else the close of the last bar starting within 30 minutes; a '
  'session that ends first drops the trade',
  tgt == ('TARGET', 100.0, 60.0) and both == ('STOP', -60.0, 60.0) and
  tmo == ('TIMEOUT', 8.0, 1800.0) and short is None)

# ---------------------------------------------------------------------
# ML3: the month-clustered verdict
# ---------------------------------------------------------------------
months = ['2018%02d' % m for m in range(1, 13)] + \
    ['2017%02d' % m for m in range(1, 13)]
good = [(m, x) for i, m in enumerate(months)
        for x in ((24.5, 24.5, -15.75) if i % 3 else (24.5, -15.75, -15.75))]
oneb = [(months[0], 24.5)] * 60 + [(m, x) for m in months[1:]
                                   for x in (24.5, -15.75, -15.75)]
v_good, v_one = ML.month_verdict(good, 50), ML.month_verdict(oneb, 50)
v_few = ML.month_verdict(good[:40], 50)
v_lose = ML.month_verdict([(m, -1.0) for m in months] * 3, 50)
t('ML3: PASS needs enough trades, the month-clustered 95 % range above 0 '
  'and a profit without the best month; one big month, a loss or too few '
  'trades say so',
  v_good['status'] == 'PASS' and v_good['clusters'] == 24 and
  v_one['status'] == 'NOT PROVEN' and v_one['net_points'] > 0 and
  any('one month' in r for r in v_one['reasons']) and
  v_few['status'] == 'NOT ENOUGH TRADES' and
  v_lose['reasons'] == ['loses after costs'])

# ---------------------------------------------------------------------
# ML4: history end to end on synthetic exports
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


def write_exports(folder, days, seed=3):
    """One contract, every session 18:00 (previous day) to 17:00 ET:
    overnight and 16:15-17:00 every 5 minutes, 09:30-16:15 every minute.
    Returns {session: (full high, full low)} as written."""
    os.makedirs(folder, exist_ok=True)
    rng = random.Random(seed)
    px, rows, full = 8000.0, [], {}
    for d in days:
        ses = d.strftime('%Y%m%d')
        base = int((_dt.datetime(d.year, d.month, d.day,
                                 tzinfo=_dt.timezone.utc) - EPOCH)
                   .total_seconds())
        mins = list(range(-6 * 60, 9 * 60 + 30, 5)) + \
            list(range(9 * 60 + 30, 16 * 60 + 15)) + \
            list(range(16 * 60 + 15, 17 * 60, 5))
        hi = lo_ = None
        for m in mins:
            px += rng.gauss(0, 1.5)
            o = round(px * 4) / 4
            h = o + 0.25 * rng.randint(0, 8)
            lo = o - 0.25 * rng.randint(0, 8)
            c = round(rng.uniform(lo, h) * 4) / 4
            hi = h if hi is None else max(hi, h)
            lo_ = lo if lo_ is None else min(lo_, lo)
            v = 100 if m < 9 * 60 + 30 else (3000 if m == 9 * 60 + 30
                                             else 900)
            u = to_utc(base + m * 60) + 60
            stamp = _dt.datetime.fromtimestamp(u, _dt.timezone.utc).strftime(
                '%Y%m%d %H%M%S')
            rows.append('%s;%.2f;%.2f;%.2f;%.2f;%d' % (stamp, o, h, lo, c, v))
        full[ses] = (hi, lo_)
    with open(os.path.join(folder, 'NQ 06-19.Last.txt'), 'w') as fh:
        fh.write('\n'.join(rows) + '\n')
    return full


def sessions_from(start, n):
    d, out = start, []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += _dt.timedelta(days=1)
    return out


DAYS = sessions_from(_dt.date(2019, 3, 18), 110)     # spans 2019-06-01
F1 = os.path.join(WORK, 'hist')
FULL = write_exports(F1, DAYS)
dev, _rd, chk = ML.history_sessions(F1, CX.is_dev)
val, _rv, _ck = ML.history_sessions(F1, CX.is_validation)
s1 = sorted(dev)[3]
prev = max(s for s in FULL if s < s1)
wk = (ML._date(s1) - _dt.timedelta(days=7)).isocalendar()[:2]
lw = [FULL[s] for s in FULL if ML._date(s).isocalendar()[:2] == wk]
rows1 = ML._rows(dev[s1]['bars'])
base1, full1 = ML.session_levels(rows1, dev[s1])
on = [(h, lo) for k, h, lo, _c in rows1 if k < CX.RTH_OPEN]
t('ML4: the history reader keeps every bar of the session in time order; '
  'yesterday is the previous session\'s full high and low, last week the '
  'ISO week before, the overnight 18:00-09:29 and only from 09:30; DEV and '
  'validation years never mix',
  chk['open_minute'] == '09:30' and dev and val and
  min(dev) >= '20190601' and max(val) < '20190601' and
  dev[s1]['yday'] == FULL[prev] and
  dev[s1]['lweek'] == (max(x[0] for x in lw), min(x[1] for x in lw)) and
  rows1 == sorted(rows1) and rows1[0][0] < 0 and
  full1['OVERNIGHT_HIGH'] == max(h for h, _l in on) and
  'OVERNIGHT_HIGH' not in base1)

repH = ML.run_history(F1)
repV = ML.run_history(F1, unblind=True)
led = os.path.join(WORK, 'hist_ledger.json')
LG.record_history_read(repV, led, ML.W16A_VERSION)
L = json.load(open(led))
t('ML5: end to end: DEV years describe, the validation years are read only '
  'with --unblind and recorded once with their range; trades come one at '
  'a time, first per level per session; the report renders',
  repH['n_trades'] > 0 and 'DEV years: describes' in repH['test']['status']
  and repH['first_session'] >= '20190601' and
  repV['last_session'] < '20190601' and
  'DEV' not in repV['test']['status'] and
  repV['test']['status'] == 'NOT ENOUGH TRADES' and
  L['reads'][0]['version'] == ML.W16A_VERSION and
  L['reads'][0]['last'] == repV['last_session'] and
  sum(v['n'] for v in repH['by_year'].values()) == repH['n_trades'] and
  repH['every']['n'] >= repH['n_trades'] and
  'VERDICT' in ML.text_history(repH) and json.dumps(repH, default=str))

# ---------------------------------------------------------------------
# ML6-ML7: recordings end to end (plumbing L2)
# ---------------------------------------------------------------------
mb = ML.minute_bars(array.array('d', [60.0, 70.0, 130.0, 250.0]),
                    array.array('d', [100.0, 101.0, 99.0, 102.0]))
_FROZEN_L2 = BM.l2_sweep_reclaim


def _l2_plumbing(fr):
    if fr.get('level_id') not in BM.RANGE_LEVELS:
        return 0
    ad = fr.get('ad')
    if not ad or not fr.get('returned_through_level'):
        return 0
    return -ad


def _path(amp):
    return lambda i: 15000.0 + amp * math.sin(2 * math.pi * (i * 0.05) /
                                              900.0)


SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260905',
            '20260908', '20260909', '20260921')
D5 = os.path.join(WORK, 'e2e')
for i, s in enumerate(SESSIONS):
    SY.synth_run(D5, n_depth=60000, dt_step=0.05, price_path=_path(30 + 3 * i),
                 trade_every=10, quote_every=5, cid='w16a%d' % i, session=s,
                 seed=i)
BM.l2_sweep_reclaim = _l2_plumbing
try:
    repR, rR = ML.run_recordings(D5)
    trR = ML.recording_trades(rR)
    repU, _rU = ML.run_recordings(D5, unblind=True)
    rC = C.CloseRunner(D5)
    rC.run()
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
keys = [(x[0]['session'], x[0]['level_id']) for x in trR]
nq = repR['results']['NQ']
t('ML6: minute bars of the mid carry the mid in force (a quiet minute is '
  'flat); on recordings the rule takes the first signal per level per '
  'session at the minute\'s end, beside wave fourteen\'s L2 first signals; '
  'the runner is wave ten\'s (same fires and grid); the report renders',
  mb == [(1, 101.0, 100.0, 101.0), (2, 101.0, 99.0, 99.0),
         (3, 99.0, 99.0, 99.0), (4, 102.0, 99.0, 102.0)] and
  trR and len(keys) == len(set(keys)) and
  all(x[0]['t'] % 60 == 0 and x[0]['level_id'] in BM.RANGE_LEVELS
      for x in trR) and
  nq['without_flow']['n'] > 0 and nq['with_flow']['n'] > 0 and
  'DEV, seen before the registration' in nq['status'] and
  repR['sessions_refused'] == ['20260921'] and
  rR.w3_fires == rC.w3_fires and rR.grid == rC.grid and
  rR.ledger['wave16a']['version'] == ML.W16A_VERSION and
  'ORDER FLOW ADDS?' in ML.text_recordings(repR))

blob = json.dumps(repU['results'], default=str)
buf = io.StringIO()
with redirect_stdout(buf):
    rc_uh = ML.main([D5, '--unblind', '--holdout'])
    rc_h = ML.main(['--history', os.path.join(WORK, 'nothing_here')])
reg = open(os.path.join(HERE, ML.REGISTRATION)).read()
t('ML7: a held-out read under 30 trades on either side withholds every '
  'result; --unblind with --holdout is refused; a missing export folder '
  'stops the history mode; the registration fixes part 16A',
  repU['withheld'] and 'net_points' not in blob and '"diff"' not in blob and
  'results withheld' in ML.text_recordings(repU) and rc_uh == 2 and
  rc_h == 2 and 'STOPPED' in buf.getvalue() and
  all(w in reg for w in ('Part 16A', '2 ticks or more through',
                         'closes back', 'month-clustered',
                         'minus this rule (without)', 'at least 100 trades',
                         'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
