#!/usr/bin/env python3
# MROF-YT-W23-VWAPVALUE-1.0 suite. The overnight value area, the 30-minute
# move, the two VWAP zones, the accepted break, the brackets and the
# verdicts are exercised on hand-built bars and trades with known
# answers; the pipeline end to end on synthetic NinjaTrader-format NQ
# exports across the 2019-06-01 split, with every trade's conditions
# re-derived without the module's helpers. Synthetic data verifies CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import bisect
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

import mrofyt_context as CX          # noqa: E402
import mrofyt_ledgers as LG          # noqa: E402
import mrofyt_minutelevels as ML     # noqa: E402
import mrofyt_stretchfade as SF      # noqa: E402
import mrofyt_vwapvalue as VV        # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w23_')
O = 34200.0                                           # 09:30 ET as a key
E18 = -21600.0                                        # 18:00 ET

# ---------------------------------------------------------------------
# VV1: the overnight value area
# ---------------------------------------------------------------------
on_rows = [(E18, 101.0, 99.0, 100.0), (E18 + 60, 100.5, 100.0, 100.0),
           (-3600.0, 100.0, 100.0, 100.0), (32400.0, 105.75, 104.0, 105.0),
           (O, 120.0, 110.0, 115.0)]
on_vols = [30.0, 0.0, 30.0, 20.0, 999.0]
want_prof = {99: 10.0, 100: 40.0, 101: 10.0, 104: 10.0, 105: 10.0}
va1 = VV.overnight_value(on_rows, on_vols)
late = VV.overnight_value([(E18 + 1860, 101.0, 99.0, 100.0)] + on_rows[2:],
                          [30.0, 30.0, 20.0, 999.0])
early_end = VV.overnight_value(on_rows[:3] + on_rows[4:],
                               [30.0, 0.0, 30.0, 999.0])
t('VV1: the overnight value area is the context study\'s 70 % value area '
  'of the bars before 09:30, each bar\'s volume spread evenly over the '
  '1-point bins from its low to its high (a bar without volume adds '
  'nothing, a cash bar nothing); it needs a bar by 18:30 and one from '
  '09:00',
  va1 == CX.value_area(want_prof) and va1[0] == 100.5 and
  late is None and early_end is None and
  VV.overnight_value([], []) is None)

# ---------------------------------------------------------------------
# VV2: the 30-minute move
# ---------------------------------------------------------------------
rows2 = [(O - 2400, 1, 1, 90.0), (O - 1800, 1, 1, 95.0), (O - 60, 1, 1, 99.0),
         (O, 1, 1, 100.0), (O + 30 * 60, 1, 1, 104.0),
         (O + 60 * 60 + 600, 1, 1, 107.0)]
keys2 = [r[0] for r in rows2]
t('VV2: the trend is the close minus the close of the last bar at or '
  'before 30 minutes earlier; a missing minute takes the bar before it if '
  'that is at most 35 minutes back, otherwise there is none',
  VV.trend_at(keys2, rows2, 3) == 5.0 and
  VV.trend_at(keys2, rows2, 4) == 4.0 and
  VV.trend_at(keys2, rows2, 5) is None and
  VV.trend_at(keys2, rows2, 0) is None)


# ---------------------------------------------------------------------
# VV3: the two VWAP zones
# ---------------------------------------------------------------------
def bars_at(closes, start=O - 1800):
    """One bar a minute from `start`, high = low = close."""
    return [(start + 60.0 * k, c, c, c) for k, c in enumerate(closes)]


A3 = 100.0
# 09:00 at 130 (30 minutes of history), flat to 09:29, then at 09:30 the
# close 120 is 20 (0.20 A) above VWAP 100 and 10 below 30 minutes ago
r3 = bars_at([130.0] * 30 + [120.0, 119.0, 121.0])
s3 = VV.zone_signals(r3, [100.0] * len(r3), A3)
# momentum: 30 minutes at VWAP, then 108 (0.08 A above) 8 up: long; then
# 92 below and down: short; a second long the same session is not taken
r4 = bars_at([100.0] * 30 + [108.0, 109.0, 92.0, 91.0])
s4 = VV.zone_signals(r4, [100.0] * len(r4), A3)
# the same pattern at 09:29 and at 15:30 gives nothing
r5 = bars_at([100.0] * 30 + [108.0], start=O - 1860)
r6 = bars_at([100.0] * 30 + [108.0], start=VV.ZONE_TO - 1800)
# the zone edges count: 13 (0.13 A) with a 13 rise is a long, then 15
# rising further away is neither; 3 (0.03 A) with a 3 rise is a long
edge = VV.zone_signals(bars_at([100.0] * 30 + [113.0, 103.0, 115.0]),
                       [100.0] * 33, A3)
low = VV.zone_signals(bars_at([100.0] * 30 + [103.0, 102.9]),
                      [100.0] * 32, A3)
t('VV3: RUBBER is a close 0.15 x A or more from VWAP with the last 30 '
  'minutes moving back toward it by 0.08 x A or more, traded toward VWAP; '
  'MOMENTUM a close 0.03 to 0.13 x A away with the 30 minutes moving '
  'further away by 0.03 x A or more, traded with it; the first of each '
  'direction per session, from 09:30 to 15:29 only; nothing without A',
  [(x['i'], x['direction'], x['d'], x['trend']) for x in s3['RUBBER']] ==
  [(30, -1, 20.0, -10.0)] and s3['MOMENTUM'] == [] and
  [(x['i'], x['direction']) for x in s4['MOMENTUM']] == [(30, 1), (32, -1)]
  and s4['RUBBER'] == [] and
  VV.zone_signals(r5, [100.0] * len(r5), A3) == dict(RUBBER=[],
                                                     MOMENTUM=[]) and
  VV.zone_signals(r6, [100.0] * len(r6), A3) == dict(RUBBER=[],
                                                     MOMENTUM=[]) and
  VV.zone_signals(r3, [100.0] * len(r3), None) == dict(RUBBER=[],
                                                       MOMENTUM=[]) and
  [(x['i'], x['d'], x['trend']) for x in edge['MOMENTUM']] ==
  [(30, 13.0, 13.0)] and edge['RUBBER'] == [] and
  [(x['i'], x['d']) for x in low['MOMENTUM']] == [(30, 3.0)])

# ---------------------------------------------------------------------
# VV4: the brackets
# ---------------------------------------------------------------------
L = [(O, 100.0, 100.0, 100.0), (O + 60, 110.0, 95.0, 105.0),
     (O + 120, 126.0, 104.0, 120.0)]
both = [(O, 100.0, 100.0, 100.0), (O + 60, 126.0, 84.0, 100.0)]
short_run = [(O, 100.0, 100.0, 100.0), (O + 60, 101.0, 99.0, 100.0)]
flat = [(O, 100.0, 100.0, 100.0)] + \
    [(O + 60.0 * k, 102.0, 98.0, 101.0 + k / 100.0) for k in range(1, 40)]
oc_rub = VV.outcome(L, 0, 1, 100.0, 25.0, 15.0)
oc_acc = VV.outcome(L, 0, 1, 100.0, 15.0, 25.0)
oc_both = VV.outcome(both, 0, -1, 100.0, 15.0, 25.0)
oc_flat = VV.outcome(flat, 0, 1, 100.0, 25.0, 15.0)
trA = VV.take(L, [dict(i=0, direction=1, close=100.0, level_id='ON_VAH')],
              'S', 'ACCEPT')
trR = VV.take(L, [dict(i=0, direction=-1, close=100.0)], 'S', 'RUBBER')
t('VV4: RUBBER and MOMENTUM trade 25 / 15 and ACCEPT 15 / 25 on the next '
  'bars\' highs and lows (a bar touching both is a stop), at most 30 '
  'minutes (else the close of the last bar starting within them), dropped '
  'when the session ends first; costs as everywhere: +24.50 / -15.75 and '
  '+14.50 / -25.75',
  oc_rub == ('TARGET', 100.0, 120.0) and oc_acc == ('TARGET', 60.0, 120.0)
  and oc_both == ('STOP', -100.0, 60.0) and
  VV.outcome(short_run, 0, 1, 100.0, 25.0, 15.0) is None and
  oc_flat[0] == 'TIMEOUT' and abs(oc_flat[1] - 4 * 1.30) < 1e-9 and
  oc_flat[2] == 1800.0 and
  [(x['outcome'], x['net'], x['level_id'], x['rule']) for x in trA] ==
  [('TARGET', 14.5, 'ON_VAH', 'ACCEPT')] and
  [(x['outcome'], x['net']) for x in trR] == [('STOP', -15.75)] and
  ML.net_points('NQ', 'STOP', -100.0) == -25.75 and
  VV.BRACKET == dict(RUBBER=(25.0, 15.0), MOMENTUM=(25.0, 15.0),
                     ACCEPT=(15.0, 25.0)))

# ---------------------------------------------------------------------
# VV5: the accepted break
# ---------------------------------------------------------------------
VA5 = (100.5, 105.0, 99.0)                            # POC, VAH, VAL
r5a = [(O - 120, 106.0, 100.0, 103.0),       # before 09:30: no level yet
       (O - 60, 106.0, 103.0, 106.0),        # through VAH before 09:30
       (O, 104.0, 102.0, 103.0),             # 09:30: below VAH
       (O + 60, 105.5, 103.0, 106.0),        # 2 ticks through, closes out
       (O + 120, 106.0, 103.5, 104.0),       # back inside: the signal
       (O + 180, 104.0, 98.5, 99.5),         # 2 ticks under VAL, closes
       (O + 240, 100.0, 99.0, 99.75)]        # back above in the same bar
sg5 = VV.accept_signals(r5a, VA5)
fade5 = ML.first_per_level(ML.signals(
    r5a, lambda i: dict(zip(VV.ON_IDS, VA5)) if r5a[i][0] >= O else {}))
t('VV5: ACCEPT takes part 16A\'s failed breaks of the overnight POC, VAH '
  'and VAL from 09:30 only, the first at each level, turned WITH the '
  'break: up through VAH and back inside is a long, down through VAL and '
  'back is a short; without a value area there is none',
  [(x['i'], x['level_id'], x['direction'], x['faded']) for x in sg5] ==
  [(4, 'ON_VAH', 1, -1), (5, 'ON_VAL', -1, 1)] and
  [(x['i'], x['level_id']) for x in fade5] ==
  [(x['i'], x['level_id']) for x in sg5] and
  all(x['direction'] == -f['direction'] for x, f in zip(sg5, fade5)) and
  VV.accept_signals(r5a, None) == [])


# ---------------------------------------------------------------------
# VV6: the verdicts
# ---------------------------------------------------------------------
def months(values, per=10):
    return [dict(month='2020%02d' % (i + 1), net=v)
            for i, v in enumerate(values) for _k in range(per)]


good = VV.verdicts(dict(RUBBER=months([17.0, 15.0] * 6),
                        MOMENTUM=months([-4.0, -3.0] * 6),
                        ACCEPT=months([17.0, 15.0] * 6)[:90]))
edge6 = VV.verdicts(dict(RUBBER=months([17.3, -2.7] * 6),
                         MOMENTUM=months([16.3, -1.7] * 6),
                         ACCEPT=months([60.0, -60.0] * 6)))
t('VV6: each rule passes with 100+ trades, the month-clustered 95 % range '
  'above 0 and a profit without the best month; a rule that loses stays '
  'NOT PROVEN even when its loss is significant; under 100 it is not '
  'judged but still counts in Holm over the three; a pass Holm does not '
  'reject is NOT PROVEN',
  [x['test'] for x in good] == list(VV.RULES) and
  [x['status'] for x in good] == ['PASS', 'NOT PROVEN',
                                  'NOT ENOUGH TRADES'] and
  [x['holm_rejected'] for x in good] == [True, True, False] and
  good[1]['reasons'] == ['loses after costs'] and
  good[2]['reasons'] == ['90 of the 100 needed'] and
  0.0167 < edge6[0]['p'] < 0.05 and edge6[0]['ci95'][0] > 0 and
  edge6[0]['status'] == 'NOT PROVEN' and
  edge6[0]['reasons'][-1] ==
  'could be luck after allowing for three rules (Holm)' and
  VV.MIN_TRADES == 100)

# ---------------------------------------------------------------------
# VV7: end to end on synthetic exports, every trade re-derived
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
    u = to_utc(base + m * 60) + 60
    return _dt.datetime.fromtimestamp(u, _dt.timezone.utc).strftime(
        '%Y%m%d %H%M%S')


def sessions_from(start, n):
    d, out = start, []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += _dt.timedelta(days=1)
    return out


def write_random(folder, days, name, seed):
    os.makedirs(folder, exist_ok=True)
    rng = random.Random(seed)
    px, rows = 8000.0, []
    for d in days:
        for m in MINS:
            px += rng.gauss(0, 3.0)
            o = round(px * 4) / 4
            h = o + 0.25 * rng.randint(0, 12)
            lo = o - 0.25 * rng.randint(0, 12)
            c = round(rng.uniform(lo, h) * 4) / 4
            v = rng.randint(50, 150) if m < 570 else \
                (3000 if m == 570 else rng.randint(600, 1200))
            rows.append('%s;%.2f;%.2f;%.2f;%.2f;%d' % (stamp(d, m), o, h, lo,
                                                       c, v))
    with open(os.path.join(folder, name), 'w') as fh:
        fh.write('\n'.join(rows) + '\n')


DAYS = sessions_from(_dt.date(2019, 1, 7), 160)       # spans 2019-06-01
F7 = os.path.join(WORK, 'hist')
write_random(F7, DAYS, 'NQ 06-19.Last.txt', 11)
repN = VV.run(F7)
repN2 = VV.run(F7)
repO = VV.run(F7, unblind=True)
daysN = SF.history_sessions(F7, CX.is_dev)[0]
trN, cntN = VV.history_trades(daysN)


def my_vwap(rows, vols):
    out, num, den = [], 0.0, 0.0
    for (_k, h, lo, c), v in zip(rows, vols):
        if v > 0:
            num, den = num + (h + lo + c) / 3.0 * v, den + v
        out.append(num / den if den else None)
    return out


def my_trend(rows, i):
    best = None
    for j in range(i, -1, -1):
        if rows[j][0] <= rows[i][0] - 1800.0:
            best = j
            break
    if best is None or rows[best][0] < rows[i][0] - 2100.0:
        return None
    return rows[i][3] - rows[best][3]


def my_value(rows, vols):
    prof = collections.defaultdict(float)
    on = [(r, v) for r, v in zip(rows, vols) if r[0] < O]
    for (_k, h, lo, _c), v in on:
        if v > 0:
            n = int(math.floor(h)) - int(math.floor(lo)) + 1
            for b in range(int(math.floor(lo)), int(math.floor(h)) + 1):
                prof[b] += v / n
    return CX.value_area(dict(prof))


bad = []
for rule in VV.RULES:
    by_ses = collections.defaultdict(list)
    for x in trN[rule]:
        by_ses[x['session']].append(x)
    for s, xs in by_ses.items():
        day = daysN[s]
        pairs = sorted(zip([day['bars'][4 * k] for k in
                            range(len(day['vols']))],
                           range(len(day['vols']))))
        rows = [tuple(day['bars'][4 * k:4 * k + 4]) for _key, k in pairs]
        vols = [day['vols'][k] for _key, k in pairs]
        vw, a = my_vwap(rows, vols), day['a']
        keys = [r[0] for r in rows]
        last_exit = None
        for x in sorted(xs, key=lambda x: x['key']):
            i = keys.index(x['key'] - 60.0)
            c, d, tr = rows[i][3], rows[i][3] - vw[i], my_trend(rows, i)
            if rule == 'RUBBER':
                ok = (O <= rows[i][0] < VV.ZONE_TO and abs(d) >= 0.15 * a
                      - 1e-9 and x['direction'] == (-1 if d > 0 else 1) and
                      x['direction'] * tr >= 0.08 * a - 1e-9)
            elif rule == 'MOMENTUM':
                ok = (O <= rows[i][0] < VV.ZONE_TO and 0.03 * a - 1e-9 <=
                      abs(d) <= 0.13 * a + 1e-9 and
                      x['direction'] == (1 if d > 0 else -1) and
                      x['direction'] * tr >= 0.03 * a - 1e-9)
            else:
                va = my_value(rows, vols)
                lv = dict(zip(VV.ON_IDS, va))[x['level_id']]
                f = [sg for sg in ML.signals(
                    rows, lambda j: {x['level_id']: lv}
                    if O <= rows[j][0] < VV.ACCEPT_TO else {})][:1]
                ok = (len(f) == 1 and f[0]['i'] == i and
                      x['direction'] == -f[0]['direction'])
            if last_exit is not None and x['key'] < last_exit:
                ok = False
            last_exit = x['key']
            if not ok:
                bad.append((rule, s, x['key']))
    firsts = collections.Counter((x['session'], x['direction'])
                                 for x in trN[rule]) if rule != 'ACCEPT' \
        else collections.Counter((x['session'], x['level_id'])
                                 for x in trN[rule])
    if firsts and max(firsts.values()) > 1:
        bad.append((rule, 'more than one first'))
led = os.path.join(WORK, 'hist_ledger.json')
LG.record_history_read(dict(repO, n_trades=sum(repO['n_trades'].values())),
                       led, VV.W23_VERSION)
L7 = json.load(open(led))
txtN = VV.text(repN)
t('VV7: end to end: every RUBBER, MOMENTUM and ACCEPT trade re-derived '
  'without the module\'s helpers (its VWAP, its 30-minute move, its '
  'overnight value area and the signal at that level), the first per '
  'direction or level, one at a time; the newer years without a flag, the '
  'older only with --unblind and recorded; a read is repeatable; the '
  'report renders',
  not bad and all(trN[r] for r in VV.RULES) and
  all(repN['n_trades'][r] == len(trN[r]) for r in VV.RULES) and
  all(cntN['signals'][r] >= len(trN[r]) for r in VV.RULES) and
  repN['first_session'] >= '20190601' and repO['last_session'] < '20190601'
  and repO['era'] == 'older' and
  json.dumps(repN, sort_keys=True, default=str) ==
  json.dumps(repN2, sort_keys=True, default=str) and
  sum(v['n'] for v in repN['beside']['ACCEPT']['by_level'].values()) ==
  repN['n_trades']['ACCEPT'] and
  L7['reads'][0]['version'] == VV.W23_VERSION and
  L7['reads'][0]['last'] == repO['last_session'] and
  all(nm in txtN for nm in VV.NAMES.values()) and
  'run the same command with --unblind' in txtN and
  'OLDER YEARS' in VV.text(repO) and json.dumps(repO, default=str))

# ---------------------------------------------------------------------
# VV8: the command, the stops and the registration
# ---------------------------------------------------------------------
out8 = os.path.join(WORK, 'w23.json')
buf = io.StringIO()
with redirect_stdout(buf):
    rc0 = VV.main([])
    rc_flag = VV.main(['--unblind'])
    rc_none = VV.main([os.path.join(WORK, 'no_such_folder')])
    rc_tz = VV.main([F7, '--stamps-tz', 'ET'])
    rc_ok = VV.main([F7, '--out', out8])
said = buf.getvalue()
_reg = open(os.path.join(HERE, VV.REGISTRATION)).read()
t('VV8: the command prints the report and writes it; no folder, a missing '
  'folder or time stamps in the wrong zone stop before anything is '
  'computed; the registration states the three rules, their brackets, '
  'the tests, the eras, what was seen beforehand and what is not '
  'registered',
  rc0 == 2 and rc_flag == 2 and rc_none == 2 and rc_tz == 2 and
  rc_ok == 0 and 'STOPPED: cannot read' in said and 'not 09:30' in said
  and len(json.load(open(out8))['tests']) == 3 and
  'wave-twenty-three report ->' in said and
  not os.path.exists(os.path.join(WORK, VV.HISTORY_LEDGER)) and
  all(x in _reg for x in (
      'FROZEN on 2026-11-17', '| **RUBBER** |', '| **MOMENTUM** |',
      '| **ACCEPT** |', '`|d| >= 0.15 × A`', '`0.03 × A <= |d| <= 0.13 × A`',
      '**with the break**', '| ACCEPT | 15 points | 25 points |',
      '**Holm over the three**', 'at least 100 trades', '| **NEWER** |',
      '| **OLDER** |', '**CONFIRMED:** a rule passes in both eras',
      'long minus short', '26 times in 31',
      'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
