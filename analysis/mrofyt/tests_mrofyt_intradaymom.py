#!/usr/bin/env python3
# MROF-YT-W16C-INTRADAYMOM-1.0 suite. The momentum rule is exercised on
# synthetic NinjaTrader-format NQ exports whose 10:00, 15:30 and 16:00
# prices are set by hand, across the 2019-06-01 split, with a planted
# effect in the judged years only, an early-close day and a day with no
# morning move. Synthetic data verifies CODE BEHAVIOR only, never market
# evidence. No order, fill or P&L exists.
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
import mrofyt_intradaymom as IM      # noqa: E402
import mrofyt_ledgers as LG          # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w16c_')
EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def to_utc(local_epoch):
    y = _dt.datetime.fromtimestamp(local_epoch, _dt.timezone.utc).year
    for off in (4, 5):
        u = local_epoch + off * 3600
        w = CX._dst_window(y)
        if (off == 4) == (w[0] <= u < w[1]):
            return u
    return local_epoch + 5 * 3600


def sessions_from(start, n):
    d, out = start, []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += _dt.timedelta(days=1)
    return out


def write(folder, days, plant_before, early=(), zero=(), seed=5):
    """Each session: flat at yesterday's close until the 09:59 bar closes
    at close + r; flat to the 15:29 bar (+ noise), then the 15:59 bar
    adds e. e = (8 +/- 2) x sign(r) before plant_before, random after.
    Returns {session: (prev close, c0959, c1529, c1559)}."""
    os.makedirs(folder, exist_ok=True)
    rng = random.Random(seed)
    close, rows, truth = 9000.0, [], {}
    for d in days:
        ses = d.strftime('%Y%m%d')
        r = 0.0 if ses in zero else rng.choice([-1, 1]) * \
            round(rng.uniform(5, 20) * 4) / 4
        c0959 = close + r
        c1529 = c0959 + round(rng.uniform(-6, 6) * 4) / 4
        sgn = (r > 0) - (r < 0)
        e = sgn * (8.0 + round(rng.uniform(-2, 2) * 4) / 4) \
            if ses < plant_before else \
            rng.choice([-1, 1]) * round(rng.uniform(0, 8) * 4) / 4
        c1559 = c1529 + e
        truth[ses] = (close, c0959, c1529, c1559)
        base = int((_dt.datetime(d.year, d.month, d.day,
                                 tzinfo=_dt.timezone.utc) - EPOCH)
                   .total_seconds())
        last_rth = 13 * 60 if ses in early else 16 * 60
        mins = list(range(-6 * 60, 9 * 60 + 30, 5)) + \
            list(range(9 * 60 + 30, last_rth))
        for m in mins:
            if m < 9 * 60 + 59:
                c = close
            elif m < 15 * 60 + 29:
                c = c0959
            elif m < 15 * 60 + 59:
                c = c1529
            else:
                c = c1559
            v = 100 if m < 9 * 60 + 30 else (3000 if m == 9 * 60 + 30
                                             else 900)
            u = to_utc(base + m * 60) + 60
            stamp = _dt.datetime.fromtimestamp(u, _dt.timezone.utc).strftime(
                '%Y%m%d %H%M%S')
            rows.append('%s;%.2f;%.2f;%.2f;%.2f;%d' % (
                stamp, c, c + 0.5, c - 0.5, c, v))
        if ses not in early:
            close = c1559
        else:
            close = c0959
    with open(os.path.join(folder, 'NQ 06-19.Last.txt'), 'w') as fh:
        fh.write('\n'.join(rows) + '\n')
    return truth


DAYS = sessions_from(_dt.date(2018, 3, 1), 380)       # ~310 before the split
SES = [d.strftime('%Y%m%d') for d in DAYS]
EARLY = {SES[40], SES[340]}
ZERO = {SES[50], SES[350]}
F1 = os.path.join(WORK, 'mom')
TRUTH = write(F1, DAYS, CX.VALIDATION_BEFORE, EARLY, ZERO)

dev, _rd, chk = IM.momentum_days(F1, CX.is_dev)
val, _rv, _ck = IM.momentum_days(F1, CX.is_validation)
dv = {x['session']: x for x in dev}
s1 = SES[360]
p_close, c0959, c1529, c1559 = TRUTH[s1]
d1 = 1 if c0959 > p_close else -1
t('IM1: the side is the move from yesterday\'s cash close to the 10:00 '
  'price; the trade is 15:30 to 16:00 in that direction, net of 0.50 '
  'points; an early-close day and a day without a morning move have no '
  'trade; DEV and the judged years never mix',
  chk['open_minute'] == '09:30' and s1 in dv and
  dv[s1]['direction'] == d1 and
  dv[s1]['gross'] == round(d1 * (c1559 - c1529), 2) and
  dv[s1]['net'] == round(d1 * (c1559 - c1529) - 0.5, 4) and
  not (EARLY | ZERO) & ({x['session'] for x in dev} |
                        {x['session'] for x in val}) and
  min(dv) >= '20190601' and max(x['session'] for x in val) < '20190601')

repD = IM.run(F1)
repV = IM.run(F1, unblind=True)
led = os.path.join(WORK, 'hist.json')
LG.record_history_read(repV, led, IM.W16C_VERSION)
t('IM2: the planted effect in the judged years PASSES (about +7.50 a day '
  'net); the DEV years, where it is absent, only describe; the read is '
  'recorded with its range; the report renders',
  repV['test']['status'] == 'PASS' and repV['test']['n'] >= IM.MIN_DAYS and
  7.0 < repV['test']['net_points'] < 8.0 and
  repV['sides']['long']['n'] + repV['sides']['short']['n'] ==
  repV['test']['n'] and
  'DEV years: describes' in repD['test']['status'] and
  repD['test']['n'] == len(dev) and
  json.load(open(led))['reads'][0]['version'] == IM.W16C_VERSION and
  'VERDICT: PASS' in IM.text(repV) and json.dumps(repD, default=str))

buf = io.StringIO()
with redirect_stdout(buf):
    rc = IM.main([os.path.join(WORK, 'missing')])
reg = open(os.path.join(HERE, IM.REGISTRATION)).read()
t('IM3: a missing export folder stops the tool; the registration fixes '
  'part 16C with its source and the overlap with the published sample',
  rc == 2 and 'STOPPED' in buf.getvalue() and
  all(w in reg for w in ('Part 16C', 'Gao, Han, Li and Zhou',
                         'close of the 09:59 bar', '15:29 bar',
                         'at least 250 days', 'overlaps the judged')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
