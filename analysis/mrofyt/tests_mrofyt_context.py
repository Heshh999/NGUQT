#!/usr/bin/env python3
# MROF-YT-CTX-1.0 suite. The context layer is exercised on synthetic
# NinjaTrader-format minute exports (two contracts across a roll, UTC
# end-of-bar stamps), on hand-built days and on planted-effect records.
# Synthetic data verifies CODE BEHAVIOR only, never market evidence.
# No order, fill or P&L exists anywhere.
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

import mrofyt_context as CX      # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_ctx_')
EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def utc(y, mo, d, h, mi):
    return int((_dt.datetime(y, mo, d, h, mi, tzinfo=_dt.timezone.utc) -
                EPOCH).total_seconds())


# ---------------------------------------------------------------------
# X1-X4: time, stamps, file names, value area
# ---------------------------------------------------------------------
t('X1: US Eastern offsets under both DST regimes: 2006 starts on the '
  'first Sunday of April and ends on the last of October; 2007 on the '
  'second Sunday of March and the first of November',
  CX.et_offset(utc(2006, 3, 12, 12, 0), 2006) == -5 * 3600 and
  CX.et_offset(utc(2006, 4, 2, 6, 59), 2006) == -5 * 3600 and
  CX.et_offset(utc(2006, 4, 2, 7, 0), 2006) == -4 * 3600 and
  CX.et_offset(utc(2006, 10, 29, 5, 59), 2006) == -4 * 3600 and
  CX.et_offset(utc(2006, 10, 29, 6, 0), 2006) == -5 * 3600 and
  CX.et_offset(utc(2007, 3, 11, 7, 0), 2007) == -4 * 3600 and
  CX.et_offset(utc(2026, 11, 1, 6, 0), 2026) == -5 * 3600)
t('X2: an exported bar stamped 14:31 UTC (end) in January is the 09:30 '
  'ET bar of that session; 23:01 UTC is 18:00 ET and belongs to the NEXT '
  'session; a start-stamped or Eastern-stamped file maps the same bar',
  CX.bar_session('20260105', '143100') == ('20260105', 34200) and
  CX.bar_session('20260105', '230100') == ('20260106', 64800) and
  CX.bar_session('20260105', '143000', stamps='start') ==
  ('20260105', 34200) and
  CX.bar_session('20260105', '093100', stamps_tz='ET') ==
  ('20260105', 34200) and
  CX.bar_session('20260706', '133100') == ('20260706', 34200))
t('X3: contract from the export\'s file name; another root is not read; '
  'a file of the root without a month is a continuous series',
  CX.contract_of('NQ 12-26.Last.txt', 'NQ') == 'NQ 12-26' and
  CX.contract_of('MNQ 12-26.Last.txt', 'NQ') is None and
  CX.contract_of('ES 12-26.Last.txt', 'NQ') is None and
  CX.contract_of('NQ ##-##.Last.txt', 'NQ') == 'NQ CONT')
prof = {100: 10.0, 101: 50.0, 102: 30.0, 103: 5.0, 99: 20.0, 98: 1.0}
t('X4: value area: the fullest bin, grown toward the fuller neighbour to '
  '70 % (POC 101.5, VAH 103, VAL 100)',
  CX.value_area(prof) == (101.5, 103.0, 100.0))

# a hand-built day: IB, VWAP, overnight, shock, outcome bars
a = CX.DayAgg()
a.add(18 * 3600 + 60, 100, 101, 99, 100, 10)            # evening
a.add(8 * 3600 + 1800, 100, 104, 98, 103, 50)           # 08:30 shock
a.add(9 * 3600 + 1740, 103, 103, 102, 102.5, 5)         # 09:29
for k in range(60):                                     # 09:30-10:29
    a.add(9 * 3600 + 1800 + 60 * k, 110, 112, 109, 111, 100)
for k in range(330):                                    # 10:30-15:59
    a.add(10 * 3600 + 1800 + 60 * k, 111, 115, 110, 114, 10)
fa = a.finalize()
t('X5: a day\'s statistics: IB high/low/volume and the 10:30 price from '
  'bars before 10:30 only, VWAP at 10:00 and 10:30, the overnight range '
  'from 18:00 to 09:29, the 08:30 shock range, complete cash session',
  fa['complete'] and fa['ib_high'] == 112 and fa['ib_low'] == 109 and
  fa['ib_vol'] == 6000 and fa['p1030'] == 111 and
  abs(fa['vwap_1030'] - (112 + 109 + 111) / 3.0) < 1e-9 and
  abs(fa['vwap_1000'] - fa['vwap_1030']) < 1e-9 and fa['on_high'] == 104 and
  fa['on_low'] == 98 and fa['p0929'] == 102.5 and fa['s830'] == 6 and
  fa['rth_close'] == 114 and len(fa['post']) == 660)
t('X5b: first touch after 10:30 of +/- 0.5 ATR: a bar spanning both is '
  'BOTH, never guessed',
  CX.first_touch(fa['post'], 111, 3.0) == 'UP' and
  CX.first_touch([110.0, 100.0], 105, 2.0) == 'BOTH' and
  CX.first_touch([105.5, 104.5], 105, 2.0) == 'NONE')


# ---------------------------------------------------------------------
# synthetic NinjaTrader exports
# ---------------------------------------------------------------------
def _dst(y):
    return CX._dst_window(y)


def to_utc(local_epoch):
    """ET wall clock (as if UTC) -> true UTC epoch."""
    y = _dt.datetime.fromtimestamp(local_epoch, _dt.timezone.utc).year
    for off in (4, 5):
        u = local_epoch + off * 3600
        w = _dst(y)
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


def write_exports(folder, days, seed=1, stamps_tz='UTC', stamps='end',
                  roll_at=90, overlap=10, post_shift=None, day_shift=None,
                  extra=None):
    """Contract A on the first roll_at+overlap sessions, B from
    roll_at-overlap on, B priced 20 points above A; A thin after the
    roll, B thin before it. post_shift: {session: points} added to every
    bar after 10:30 (outcome surgery); day_shift: added to every bar of
    the session."""
    os.makedirs(folder, exist_ok=True)
    rng = random.Random(seed)
    files = {'NQ 03-15': [], 'NQ 06-15': []}
    px = 4000.0
    for i, d in enumerate(days):
        ses = d.strftime('%Y%m%d')
        base_local = int((_dt.datetime(d.year, d.month, d.day,
                                       tzinfo=_dt.timezone.utc) -
                          EPOCH).total_seconds())
        mins = [(-6 * 60 + m) for m in range(0, 15 * 60 + 30, 5)]   # ON
        mins += list(range(9 * 60 + 30, 16 * 60 + 15))             # RTH+
        shift = (post_shift or {}).get(ses, 0.0)
        dshift = (day_shift or {}).get(ses, 0.0)
        for m in mins:
            px += rng.gauss(0, 1.5)
            o = round(px * 4) / 4
            h = o + 0.25 * rng.randint(0, 8)
            lo = o - 0.25 * rng.randint(0, 8)
            c = round(rng.uniform(lo, h) * 4) / 4
            if m >= 10 * 60 + 30 and shift:
                o, h, lo, c = o + shift, h + shift, lo + shift, c + shift
            if dshift:
                o, h, lo, c = o + dshift, h + dshift, lo + dshift, c + dshift
            v = 100 if m < 9 * 60 + 30 else (3000 if m == 9 * 60 + 30
                                             else 900)
            if m == 8 * 60 + 30:
                v = 400
            start_local = base_local + m * 60
            u = to_utc(start_local) if stamps_tz == 'UTC' else start_local
            if stamps == 'end':
                u += 60
            stamp = _dt.datetime.fromtimestamp(u, _dt.timezone.utc).strftime(
                '%Y%m%d %H%M%S')
            for name, active, off in (('NQ 03-15', i < roll_at + overlap,
                                       0.0),
                                      ('NQ 06-15', i >= roll_at - overlap,
                                       20.0)):
                if not active:
                    continue
                front = (i < roll_at) == (name == 'NQ 03-15')
                vv = v if front else max(1, v // 10)
                files[name].append('%s;%.2f;%.2f;%.2f;%.2f;%d' % (
                    stamp, o + off, h + off, lo + off, c + off, vv))
    for name, rows in files.items():
        with open(os.path.join(folder, name + '.Last.txt'), 'w') as fh:
            fh.write('\n'.join(rows) + '\n')
    if extra:
        with open(os.path.join(folder, 'NQ 09-26.Last.txt'), 'w') as fh:
            fh.write('\n'.join(extra) + '\n')


DAYS = sessions_from(_dt.date(2018, 12, 3), 260)    # spans 2019-06-01
F1 = os.path.join(WORK, 'base')
write_exports(F1, DAYS)
rd, chk, recs = CX.read_days(F1)
by = {r['session']: r for r in recs}
roll_day = DAYS[90].strftime('%Y%m%d')
after = DAYS[91].strftime('%Y%m%d')
t('X6: the stamp check finds the cash-open volume jump at 09:30 on UTC '
  'end-stamped exports',
  chk['open_minute'] == '09:30' and rd.bad_lines == 0)
rk = CX.Reader('NQ')
for m, (vol, n) in {509: (100.0, 10), 510: (2500.0, 10),      # 08:29 -> 08:30
                    569: (3000.0, 10), 570: (30000.0, 10),    # 09:29 -> 09:30
                    958: (20000.0, 10), 959: (40000.0, 10)}.items():
    rk.minute_vol[m], rk.minute_n[m] = vol, n
t('X6a: the stamp check ignores a thin minute with a sharper jump (08:30 '
  'at 25x but a tenth of the peak) and names 09:30',
  rk.open_minute()[0] == 570)
t('X6b: the front contract is chosen by the PREVIOUS session\'s volume: '
  'still the old one on the first day the new one leads, the new one the '
  'day after',
  by[roll_day]['contract'] == 'NQ 03-15' and
  by[after]['contract'] == 'NQ 06-15' and
  by[DAYS[20].strftime('%Y%m%d')]['contract'] == 'NQ 03-15')
st_after = rd.days[('NQ 06-15', after)]
st_prev = rd.days[('NQ 06-15', roll_day)]
r_after = by[after]
t('X6c: across the roll, yesterday\'s close comes from the SAME contract '
  '(a 20-point basis never shows up as a gap)',
  abs(r_after['features']['gap'] * r_after['atr'] -
      (st_after['rth_open'] - st_prev['rth_close'])) < 1e-6)
el = [r for r in recs if r['eligible']]
t('X6d: eligibility needs 14 earlier sessions for ATR; the regime feature '
  'needs 100 and the 20-session medians 20',
  recs[13]['eligible'] is False and recs[14]['eligible'] is True and
  recs[14]['features']['ib_range_rel'] is None and
  recs[20]['features']['ib_range_rel'] is not None and
  recs[99]['features']['atr_rel'] is None and
  recs[100]['features']['atr_rel'] is not None)

for kind, kw, needle in (('et', dict(stamps_tz='ET'), 'whole hours off'),
                         ('start', dict(stamps='start'), 'START')):
    fx = os.path.join(WORK, 'bad_' + kind)
    write_exports(fx, DAYS[:30], **kw)
    try:
        CX.read_days(fx)
        msg = ''
    except CX.ContextDataError as exc:
        msg = str(exc)
    t('X7%s: exports stamped %s are refused with the reason and the fix, '
      'nothing computed' % ('' if kind == 'et' else 'b',
                            'in Eastern time read as UTC' if kind == 'et'
                            else 'at the bar start read as end'),
      needle in msg and 'Nothing was computed' in msg)
fx = os.path.join(WORK, 'bad_et')
rdx, chkx, recx = CX.read_days(fx, stamps_tz='ET')
t('X7c: ...and read correctly with the flag the message names',
  chkx['open_minute'] == '09:30')


# ---------------------------------------------------------------------
# X8: the search engine on planted effects and noise
# ---------------------------------------------------------------------
def make(planted, seed=4, n=2600):
    rg = random.Random(seed)
    out = []
    d = _dt.date(2006, 1, 2)
    for i in range(n):
        while d.weekday() >= 5:
            d += _dt.timedelta(days=1)
        ses = d.strftime('%Y%m%d')
        f = {k: rg.gauss(0, 1) for k in CX.FEATURES}
        y = rg.gauss(0.02, 0.6)
        if planted and f['gap'] > 1.2816:          # top decile of N(0,1)
            y -= 0.35
        out.append(dict(session=ses, month=ses[:6], year=ses[:4],
                        contract='NQ CONT', eligible=True, features=f, y=y,
                        y_points=y * 50, close_loc=rg.random()))
        d += _dt.timedelta(days=1)
    return out


dsP = make(True)
testsP, cutsP, daysP = CX.search(dsP)
byP = {x['rule']: x for x in testsP}
nomP = CX.nominate(testsP, daysP)
t('X8: a planted rest-of-day edge (fade the top-decile gap) is found as '
  'a CANDIDATE and nominated first; the opposite direction is not',
  byP['S:gap.top.d:short']['status'] == 'CANDIDATE' and
  byP['S:gap.top.d:long']['status'] is None and nomP and
  nomP[0]['rule'] == 'S:gap.top.d:short')
noise_hits = 0
for seed in range(100, 140):
    testsN, _c, _d = CX.search(make(False, seed=seed))
    noise_hits += any(x.get('status') == 'CANDIDATE' for x in testsN)
t('X8b: on pure noise 676 tests are counted and a false CANDIDATE turns '
  'up in at most 10 %% of 40 independent datasets (BH at q = 0.10 '
  'bounds it; observed %d of 40)' % noise_hits,
  len(testsN) == CX.N_RULES and noise_hits <= 4)

# ---------------------------------------------------------------------
# X9-X12: the modes, the split and what is never read
# ---------------------------------------------------------------------
rep1, nom1, recs1 = CX.run_search(F1)
val_ses = [d.strftime('%Y%m%d') for d in DAYS
           if d.strftime('%Y%m%d') < CX.VALIDATION_BEFORE]
F2 = os.path.join(WORK, 'surgery')
write_exports(F2, DAYS, day_shift={x: 300.0 for x in val_ses})
rep2, nom2, _r2 = CX.run_search(F2)
el1 = [r['session'] for r in recs1 if r['eligible']]
t('X9: the search reads DEV only -- every session before 2019-06-01 is '
  'dropped unread and counted, none reaches a record, and moving every '
  'validation bar by 300 points changes nothing in the search report',
  val_ses and rep1['validation_sessions_skipped_unread'] == len(val_ses)
  and min(r['session'] for r in recs1) >= CX.VALIDATION_BEFORE and
  rep1['dev_days'] == len(el1) and
  json.dumps([rep1['tests'], rep1['cuts'], rep1['nominated'],
              rep1['anatomy']], sort_keys=True, default=str) ==
  json.dumps([rep2['tests'], rep2['cuts'], rep2['nominated'],
              rep2['anatomy']], sort_keys=True, default=str))

late = []
for k in range(400):
    u = utc(2026, 7, 6, 13, 31) + 60 * k
    late.append('%s;99999;99999;1;5;1000000' % _dt.datetime.fromtimestamp(
        u, _dt.timezone.utc).strftime('%Y%m%d %H%M%S'))
F3 = os.path.join(WORK, 'late')
write_exports(F3, DAYS, extra=late)
rep3, _n3, _r3 = CX.run_search(F3)
t('X10: sessions from 2026-07-01 are refused before anything is kept '
  '(absurd bars there change nothing) and counted',
  rep3['input']['sessions_refused'] == 1 and
  json.dumps(rep3['tests'], sort_keys=True, default=str) ==
  json.dumps(rep1['tests'], sort_keys=True, default=str))

rules = {r['id']: r for r in CX.enumerate_rules()}
cut1 = CX.quantile_cuts([r for r in recs1 if r['eligible']])
pick = [x for x in rep1['tests'] if x.get('testable') and
        x['rule'].startswith('S:')][0]
fr = CX.frozen_rule(rules[pick['rule']], pick, cut1)
repE = CX.run_evaluate(F1, [fr], unblind=False)
repU = CX.run_evaluate(F1, [fr], unblind=True)
_rv, _cv, recv = CX.read_days(F1, allow=CX.is_validation)
n_val = sum(1 for r in recv if r['eligible'])
led = os.path.join(WORK, 'ctx_ledger.json')
CX.record_validation_read(repU, led)
try:
    CX.run_evaluate(F1, [dict(fr, validation_before=None)], unblind=True)
    bad_ok = False
except CX.ContextDataError:
    bad_ok = True
t('X11: --evaluate on DEV reproduces the search\'s numbers for a frozen '
  'rule and says so; with --unblind it reads ONLY the years before '
  '2019-06-01 (DEV dropped unread), and the read is recorded; a rule '
  'without the registered split is refused',
  repE['rules'][0]['result']['days'] == pick['days'] and
  repE['rules'][0]['result']['lift_atr'] == pick['lift_atr'] and
  'reproduction' in repE['rules'][0]['verdict'] and
  repU['last_day'] < CX.VALIDATION_BEFORE and
  repU['days_evaluated'] == n_val and
  repU['input']['sessions_skipped_unread'] == len(DAYS) - len(val_ses) and
  json.load(open(led))['reads'][0]['days'] == n_val and bad_ok)

d_dev = el1[30]
F4 = os.path.join(WORK, 'causal')
write_exports(F4, DAYS, post_shift={d_dev: 50.0})
_rd4, _c4, recs4 = CX.read_days(F4)
a4 = {r['session']: r for r in recs4}
b1 = {r['session']: r for r in CX.read_days(F1)[2]}
t('X12: causal by construction -- moving a day\'s bars after 10:30 '
  'changes its outcome but none of its 10:30 features',
  a4[d_dev]['features'] == b1[d_dev]['features'] and
  abs(a4[d_dev]['y_points'] - b1[d_dev]['y_points'] - 50.0) < 1e-6)

# ---------------------------------------------------------------------
# X13: the command line
# ---------------------------------------------------------------------
buf = io.StringIO()
with redirect_stdout(buf):
    rc1 = CX.main([F1, '--unblind', '--out', os.path.join(WORK, 'u.json')])
    nomf = os.path.join(WORK, 'nom.json')
    daysf = os.path.join(WORK, 'days.csv')
    rc2 = CX.main([F1, '--out', os.path.join(WORK, 's.json'),
                   '--nominated-out', nomf, '--days-out', daysf])
nomd = json.load(open(nomf))
csv_ses = [line.split(',')[0] for line in open(daysf).read().split('\n')[1:]
           if line]
_reg = open(os.path.join(HERE, 'MROF_YT_CONTEXT_REGISTRATION.md')).read()
t('X13: --unblind without --evaluate is refused; a search writes the '
  'report, the nominated file with the registered split, and DEV-only '
  'features; the registration states the 13 features, 676 rules, the '
  '2019-06-01 split and the July 2026 refusal',
  rc1 == 2 and 'REFUSED' in buf.getvalue() and rc2 == 0 and
  nomd['validation_before'] == CX.VALIDATION_BEFORE and
  min(csv_ses) >= CX.VALIDATION_BEFORE and
  '676' in _reg and '2019-06-01' in _reg and '2026-07-01' in _reg and
  'Explicitly NOT registered' in _reg and
  all(f in _reg for f in CX.FEATURES))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
