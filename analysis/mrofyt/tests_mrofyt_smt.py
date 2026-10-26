#!/usr/bin/env python3
# MROF-YT-W6B-SMT-1.0 suite. The ES-confirmation study is exercised on
# hand-built minute bars, on planted-effect event lists and on synthetic
# NinjaTrader-format NQ and ES exports across the 2019-06-01 split.
# Synthetic data verifies CODE BEHAVIOR only, never market evidence. No
# order, fill or P&L exists anywhere.
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

import mrofyt_context as CX      # noqa: E402
import mrofyt_smt as SM          # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_smt_')
EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def day(rows, hy, ly, atr):
    b = array.array('d')
    for r in rows:
        b.extend(r)
    return dict(bars=b, high_y=hy, low_y=ly, atr=atr)


M = lambda hh, mm: hh * 3600 + mm * 60        # noqa: E731

# ---------------------------------------------------------------------
# M1-M2: events and ES confirmation
# ---------------------------------------------------------------------
fail = day([(M(9, 30), 99, 98, 98.5), (M(9, 31), 100.5, 99, 100.3),
            (M(9, 32), 100.4, 99.5, 99.8), (M(9, 33), 99.9, 99, 99.5)],
           100, 90, 10)
es_yes = day([(M(9, 30), 49, 48, 48.5), (M(9, 31), 50.2, 49, 50)], 50, 40, 5)
es_late = day([(M(9, 30), 49, 48, 48.5), (M(9, 40), 50.2, 49, 50)], 50, 40, 5)
e1 = SM.find_events(fail, es_yes)
e2 = SM.find_events(fail, es_late)
held_rows = [(M(9, 30), 99, 98, 98.5)] + \
    [(M(9, 31 + k), 101, 100.1, 100.5) for k in range(15)]
e3 = SM.find_events(day(held_rows, 100, 90, 10), es_yes)
flat = [(M(9, 30), 99, 98, 98.5)] + \
    [(M(9, 31 + k), 100.6, 99.9, 100.0) for k in range(20)]
late = [(M(15, 0), 101, 99, 99)]
t('M1: a wick through yesterday\'s high closed back inside within 15 bars '
  'is FAILED (fade, at that close); 15 closes beyond is HELD (follow, at '
  'the 15th); closes ON the level are neither; a break from 15:00 does '
  'not count; no ES day, no event',
  len(e1) == 1 and e1[0]['kind'] == 'FAILED' and e1[0]['direction'] == -1
  and e1[0]['entry'] == 99.8 and e1[0]['bar'] == 2 and
  len(e3) == 1 and e3[0]['kind'] == 'HELD' and e3[0]['direction'] == 1 and
  e3[0]['bar'] == 15 and
  SM.find_events(day(flat, 100, 90, 10), es_yes) == [] and
  SM.find_events(day(late, 100, 90, 10), es_yes) == [] and
  SM.find_events(fail, None) == [])
t('M2: ES confirms only if it broke ITS yesterday high by 0.02 of ITS ATR '
  'at a bar no later than the NQ event bar',
  e1[0]['es_confirmed'] is True and e2[0]['es_confirmed'] is False)

# ---------------------------------------------------------------------
# M3: the outcome
# ---------------------------------------------------------------------
rows = [(M(10, 0), 100, 100, 100), (M(10, 1), 103, 99, 101),
        (M(10, 2), 107, 100, 106)]
o1 = SM.outcome(rows, 0, 1, 100.0, 10.0)        # stop 4 (floor), tgt 6.4
o2 = SM.outcome([(0, 0, 0, 0), (1, 107, 95, 100)], 0, 1, 100.0, 10.0)
o3 = SM.outcome([(0, 0, 0, 0), (1, 101, 99, 101), (2, 102, 100, 102)], 0,
                -1, 100.0, 10.0)
o4 = SM.outcome(rows, 0, 1, 100.0, 1000.0)      # stop 50, no touch
t('M3: stop = max(0.05 ATR, 4 points), target 1.6 stops: a target first '
  'is +1.6 R; a bar touching both is a stop; untouched, the last close in '
  'R; net = gross - 0.75 points / stop',
  o1 == ('TARGET', 1.6, 1.6 - 0.75 / 4) and
  o2 == ('STOP', -1.0, -1.0 - 0.75 / 4) and
  o3 == ('CLOSE', -0.5, -0.5 - 0.75 / 4) and
  abs(o4[1] - 6.0 / 50) < 1e-12)

# ---------------------------------------------------------------------
# M4-M5: statistics
# ---------------------------------------------------------------------
dd = SM.diff_stats([('m1', 1.0), ('m1', 3.0), ('m2', 2.0)],
                   [('m1', 0.0), ('m2', 1.0)])
t('M4: the month-clustered difference of means equals the hand '
  'computation (diff 1.5, SE 0.5, t 3.0 on 1 df)',
  dd['diff'] == 1.5 and dd['se'] == 0.5 and dd['t'] == 3.0)


def make(planted, seed, n_months=160):
    rg = random.Random(seed)
    ev = []
    for m in range(n_months):
        mo = '%04d%02d' % (2006 + m // 12, m % 12 + 1)
        for k in range(rg.randint(3, 8)):
            kind = rg.choice(['FAILED', 'HELD'])
            conf = rg.random() < 0.5
            r = rg.gauss(-0.05, 1.0)
            if planted and kind == 'FAILED' and not conf:
                r += 0.35
            ev.append(dict(month=mo, kind=kind, es_confirmed=conf, r_net=r))
    return ev


tp = {x['test']: x for x in SM.tests(make(True, 3))}
false = 0
for seed in range(40, 60):
    false += any(x['status'] == 'PROMISING' for x in SM.tests(make(False,
                                                                   seed)))
t('M5: a planted edge in fading ES-unconfirmed failures is found by S1 '
  'and S3, and not by S2/S4; on noise a false PROMISING turns up in at '
  'most 3 of 20 datasets (observed %d)' % false,
  tp['S1']['status'] == 'PROMISING' and tp['S3']['status'] == 'PROMISING'
  and tp['S2']['status'] != 'PROMISING' and false <= 3)


# ---------------------------------------------------------------------
# M6: end to end on synthetic exports across the split
# ---------------------------------------------------------------------
def to_utc(local_epoch):
    y = _dt.datetime.fromtimestamp(local_epoch, _dt.timezone.utc).year
    for off in (4, 5):
        u = local_epoch + off * 3600
        w = CX._dst_window(y)
        if (off == 4) == (w[0] <= u < w[1]):
            return u
    return local_epoch + 5 * 3600


def write_root(folder, root, days, base, scale, seed):
    rng = random.Random(seed)
    px = base
    rows = []
    for d in days:
        b0 = int((_dt.datetime(d.year, d.month, d.day,
                               tzinfo=_dt.timezone.utc) - EPOCH)
                 .total_seconds())
        mins = [(-6 * 60 + m) for m in range(0, 15 * 60 + 30, 5)]
        mins += list(range(9 * 60 + 30, 16 * 60))
        for m in mins:
            px += rng.gauss(0, 1.2) * scale
            o = round(px * 4) / 4
            h = o + 0.25 * rng.randint(0, 6)
            lo = o - 0.25 * rng.randint(0, 6)
            c = round(rng.uniform(lo, h) * 4) / 4
            v = 100 if m < 9 * 60 + 30 else (3000 if m == 9 * 60 + 30
                                             else 900)
            u = to_utc(b0 + m * 60) + 60
            rows.append('%s;%.2f;%.2f;%.2f;%.2f;%d' % (
                _dt.datetime.fromtimestamp(u, _dt.timezone.utc).strftime(
                    '%Y%m%d %H%M%S'), o, h, lo, c, v))
    with open(os.path.join(folder, '%s 09-19.Last.txt' % root), 'w') as fh:
        fh.write('\n'.join(rows) + '\n')


days = []
d = _dt.date(2019, 1, 2)
while len(days) < 150:
    if d.weekday() < 5:
        days.append(d)
    d += _dt.timedelta(days=1)
F = os.path.join(WORK, 'exports')
os.makedirs(F)
write_root(F, 'NQ', days, 7000.0, 1.0, 1)
write_root(F, 'ES', days, 2600.0, 0.35, 2)
buf = io.StringIO()
with redirect_stdout(buf):
    repD, evD = SM.run(F)
    repV, evV = SM.run(F, unblind=True)
val = [x.strftime('%Y%m%d') for x in days
       if x.strftime('%Y%m%d') < CX.VALIDATION_BEFORE]
_reg = open(os.path.join(HERE, 'MROF_YT_WAVE6_LEVELBREAK_REGISTRATION.md')
            ).read()
t('M6: DEV reads only sessions from 2019-06-01 (the earlier ones dropped '
  'unread, both roots), --unblind only those before; both find break '
  'events, score the four tests and render; the registration states the '
  'tests, the ES rule, the split and the costs',
  repD['first_session'] >= CX.VALIDATION_BEFORE and
  repD['sessions_skipped_unread'] == dict(NQ=len(val), ES=len(val)) and
  repV['last_session'] < CX.VALIDATION_BEFORE and
  repD['events'] > 0 and repV['events'] > 0 and
  [x['test'] for x in repD['tests']] == ['S1', 'S2', 'S3', 'S4'] and
  'S4' in SM.text(repV) and json.dumps(repV, default=str) and
  all(e['session'] < CX.VALIDATION_BEFORE for e in evV) and
  'SMT' in _reg and '2019-06-01' in _reg and '0.75' in _reg and
  'S3' in _reg)

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
