#!/usr/bin/env python3
# MROF-YT-EXPORTCHECK-1.0 suite. What the check says of an export folder
# on its own and against a reference is exercised on synthetic
# NinjaTrader-format files built here: holes, an unfinished export, bad
# files, shifted time stamps, a price offset, a shorter export, and the
# gate behind which nothing is compared. Synthetic data verifies CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import datetime as _dt
import io
import json
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_context as CX          # noqa: E402
import mrofyt_exportcheck as E       # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_exportcheck_')
D = _dt.date
SECRET = 31337.75                    # a price no report may show


def weekdays(a, b):
    d, out = a, []
    while d <= b:
        if d.weekday() < 5:
            out.append(d)
        d += _dt.timedelta(days=1)
    return out


def day_bars(day, base, n=480, first_hour=13):
    """n one-minute bars of one trading day, stamped in UTC at their
    END, from first_hour:01: [(stamp, o, h, l, c, v)]."""
    t0 = _dt.datetime(day.year, day.month, day.day, first_hour, 0)
    out = []
    for k in range(n):
        end = t0 + _dt.timedelta(minutes=k + 1)
        p = base + 0.25 * ((k * 7 + day.toordinal()) % 40)
        out.append((end.strftime('%Y%m%d %H%M%S'), p, p + 0.5, p - 0.25,
                    p + 0.25, 10 + k % 5))
    return out


def contract_bars(days, base):
    out = []
    for d in days:
        out.extend(day_bars(d, base))
    return out


def write(folder, contract, bars, name=None):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name or '%s.Last.txt' % contract)
    with open(path, 'w', encoding='utf-8') as fh:
        for b in bars:
            fh.write('%s;%r;%r;%r;%r;%d\n' % b)
    return path


def summary(folder, root, rows, complete=True, written='20240620 120000',
            version=E.SCRIPT_VERSION, lookup='Provider'):
    with open(os.path.join(folder, 'MROF_EXPORT_%s.txt' % root), 'w') as fh:
        fh.write(version + '\n')
        fh.write('market;%s\nwritten_utc;%s\ntime_zone;Central Standard '
                 'Time\nmerge_policy;DoNotMerge\nlookup_policy;%s\n'
                 'contracts;%d\n' % (root, written, lookup, len(rows)))
        for c, st, n, why in rows:
            fh.write('contract;%s;%s;%d;a;b;%s\n' % (c, st, n, why))
        if complete:
            fh.write('complete\n')


def said(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = E.main(argv)
    return rc, out.getvalue(), err.getvalue()


# the market: three contracts, four days of both at each roll
M = dict()
M['XX 03-24'] = contract_bars(weekdays(D(2023, 12, 11), D(2024, 3, 14)),
                              SECRET)
M['XX 06-24'] = contract_bars(weekdays(D(2024, 3, 11), D(2024, 6, 13)),
                              SECRET + 60)
M['XX 09-24'] = contract_bars(weekdays(D(2024, 6, 10), D(2024, 6, 19)),
                              SECRET + 120)


def folder_of(name, market=None, drop=()):
    f = os.path.join(WORK, name)
    for c, bars in (market or M).items():
        if c not in drop:
            write(f, c, bars)
    return f


# ---------------------------------------------------------------------
# E1: a clean export, on its own
# ---------------------------------------------------------------------
f1 = folder_of('e1')
summary(f1, 'XX', [('XX 03-24', 'OK', len(M['XX 03-24']), ''),
                   ('XX 06-24', 'OK', len(M['XX 06-24']), ''),
                   ('XX 09-24', 'OK', len(M['XX 09-24']), ''),
                   ('XX 12-24', 'NO BARS', 0, ''),
                   ('XX 03-25', 'NOT FOUND', 0, 'x')])
rep1 = E.run(f1, 'XX')
e1 = rep1['export']
days_all = sorted({b[0][:8] for bars in M.values() for b in bars})
t('E1: a clean export is COMPLETE; contracts, bars, trading days and the '
  'days two contracts hold are counted; no price is shown',
  e1['verdict'] == 'COMPLETE' and e1['why'] == [] and
  [r['contract'] for r in e1['contracts']] ==
  ['XX 03-24', 'XX 06-24', 'XX 09-24'] and
  [r['bars'] for r in e1['contracts']] == [len(M[c]) for c in (
      'XX 03-24', 'XX 06-24', 'XX 09-24')] and
  e1['trading_days'] == len(days_all) and e1['first_day'] == '20231211'
  and e1['last_day'] == '20240619' and e1['holes'] == [] and
  e1['days_in_two_contracts'] == 4 + 4 and
  e1['days_before_gate'] == len(days_all) and e1['days_from_gate'] == 0 and
  e1['script_summary']['complete'] and
  e1['script_summary']['statuses'] == {'OK': 3, 'NO BARS': 1,
                                       'NOT FOUND': 1} and
  rep1['reference'] is None and rep1['gate'] == CX.REFUSE_FROM and
  '31337' not in E.text(rep1) and '31337' not in json.dumps(rep1) and
  'THE EXPORT: COMPLETE' in E.text(rep1))

# ---------------------------------------------------------------------
# E2: what makes an export INCOMPLETE
# ---------------------------------------------------------------------
gap = dict(M)
gap['XX 06-24'] = [b for b in M['XX 06-24']
                   if not '20240416' <= b[0][:8] <= '20240424']
f2 = folder_of('e2', gap)
r2 = E.run(f2, 'XX')['export']
f2b = folder_of('e2b')
summary(f2b, 'XX', [('XX 03-24', 'OK', len(M['XX 03-24']), ''),
                    ('XX 06-24', 'ERROR', 0, 'Panic boom'),
                    ('XX 09-24', 'OK', len(M['XX 09-24']) - 1, '')],
        complete=False, version='SOMETHING-ELSE')
r2b = E.run(f2b, 'XX')['export']
f2c = folder_of('e2c', drop=('XX 09-24',))
summary(f2c, 'XX', [('XX 12-23', 'NO BARS', 0, ''),
                    ('XX 03-24', 'OK', len(M['XX 03-24']), ''),
                    ('XX 06-24', 'OK', len(M['XX 06-24']), ''),
                    ('XX 09-24', 'NOT FOUND', 0, ''),
                    ('XX 12-24', 'NO BARS', 0, '')],
        written='20240901 120000')
r2c = E.run(f2c, 'XX')['export']
f2d = folder_of('e2d')
summary(f2d, 'XX', [('XX 03-24', 'OK', len(M['XX 03-24']), ''),
                    ('XX 06-24', 'NO BARS', 0, ''),
                    ('XX 09-24', 'OK', len(M['XX 09-24']), ''),
                    ('XX 12-24', 'NO ANSWER', 0, 'no answer in 300 s')])
r2d = E.run(f2d, 'XX')['export']
f2e = folder_of('e2e')
summary(f2e, 'XX', [(c, 'OK', len(M[c]), '') for c in sorted(M)],
        lookup='NOT SET')
r2e = E.run(f2e, 'XX')['export']
t('E2: a hole of trading days, an unfinished or foreign summary, an '
  'error, a bar count that is not the file\'s, bars that end long before '
  'the export, and a contract without bars between two with bars',
  r2['verdict'] == 'INCOMPLETE' and r2['holes'] == [['20240415',
                                                      '20240425', 10]] and
  any('20240415 and 20240425' in w for w in r2['why']) and
  r2b['verdict'] == 'INCOMPLETE' and
  any('did not finish' in w for w in r2b['why']) and
  any('SOMETHING-ELSE' in w for w in r2b['why']) and
  any('XX 06-24: ERROR (Panic boom)' in w for w in r2b['why']) and
  any('XX 09-24: the script wrote %d bars, the file holds %d' % (
      len(M['XX 09-24']) - 1, len(M['XX 09-24'])) in w
      for w in r2b['why']) and
  r2c['verdict'] == 'INCOMPLETE' and len(r2c['why']) == 1 and
  'the bars end on 20240613' in r2c['why'][0] and
  r2d['verdict'] == 'INCOMPLETE' and
  sorted(w[:19] for w in r2d['why']) == ['XX 06-24: NO BARS', 'XX 12-24: '
                                         'NO ANSWER'[:19]] and
  r2e['verdict'] == 'INCOMPLETE' and len(r2e['why']) == 1 and
  'could not ask the data feed' in r2e['why'][0])

# ---------------------------------------------------------------------
# E3: files that are not clean
# ---------------------------------------------------------------------
f3 = os.path.join(WORK, 'e3')
bad = list(M['XX 09-24'])
bad.insert(5, bad[2])                           # a stamp twice, and back
bad[40] = (bad[40][0][:13] + '30',) + bad[40][1:]      # 30 seconds
p3 = write(f3, 'XX 09-24', bad)
with open(p3, 'a') as fh:
    fh.write('Date;Open;High;Low;Close;Volume\n\n20240620;1;2;3\n')
r3 = E.run(f3, 'XX')['export']
row3 = r3['contracts'][0]
t('E3: lines that are not bars, a stamp written twice, bars out of order '
  'and a stamp off the minute are counted and make it INCOMPLETE',
  r3['verdict'] == 'INCOMPLETE' and row3['bad_lines'] == 2 and
  row3['repeated'] == 1 and row3['unordered'] == 1 and
  row3['off_minute'] == 1 and len(r3['why']) == 4)

# ---------------------------------------------------------------------
# E4: against a reference - the same, more, and less
# ---------------------------------------------------------------------
ref = folder_of('ref')
same = E.run(f1, 'XX', ref)['reference']
more = dict(M)
more['XX 06-24'] = contract_bars(weekdays(D(2024, 3, 4), D(2024, 3, 8)),
                                 SECRET + 60) + M['XX 06-24']
more['XX 12-24'] = contract_bars(weekdays(D(2024, 6, 17), D(2024, 6, 19)),
                                 5.0)
r_more = E.run(folder_of('e4more', more), 'XX', ref)['reference']
less = dict(M)
less['XX 06-24'] = [b for b in M['XX 06-24'] if b[0][:8] >= '20240313']
r_less = E.run(folder_of('e4less', less), 'XX', ref)['reference']
r_miss = E.run(folder_of('e4miss', drop=('XX 03-24',)), 'XX',
               ref)['reference']
row_more = [r for r in r_more['rows'] if r['contract'] == 'XX 06-24'][0]
row_less = [r for r in r_less['rows'] if r['contract'] == 'XX 06-24'][0]
t('E4: the same bars are SAME, also when the export holds more; a '
  'shorter contract or a missing one is SAME WHERE BOTH HAVE BARS',
  same['verdict'] == 'SAME' and same['compared'] == 3 and
  all(r['same'] == len(M[r['contract']]) and r['different'] == 0
      for r in same['rows']) and
  r_more['verdict'] == 'SAME' and row_more['outside_export'] == 5 * 480 and
  row_more['same'] == len(M['XX 06-24']) and
  [r['contract'] for r in r_more['rows']] == ['XX 03-24', 'XX 06-24',
                                              'XX 09-24'] and
  r_less['verdict'] == 'SAME WHERE BOTH HAVE BARS' and
  row_less['outside_reference'] == 2 * 480 and row_less['different'] == 0
  and 'XX 06-24' in r_less['why'][0] and
  r_miss['verdict'] == 'SAME WHERE BOTH HAVE BARS' and
  r_miss['rows'][0] == dict(contract='XX 03-24', missing=True,
                            reference_bars=len(M['XX 03-24'])) and
  'XX 03-24' in r_miss['why'][0])


# ---------------------------------------------------------------------
# E5: differences, and what is behind them
# ---------------------------------------------------------------------
def shifted(bars, minutes):
    out = []
    for b in bars:
        d = _dt.datetime.strptime(b[0], '%Y%m%d %H%M%S') + \
            _dt.timedelta(minutes=minutes)
        out.append((d.strftime('%Y%m%d %H%M%S'),) + b[1:])
    return out


hour = {c: shifted(b, 60) for c, b in M.items()}
r_hour = E.run(folder_of('e5hour', hour), 'XX', ref)['reference']
minute = {c: shifted(b, -1) for c, b in M.items()}
r_min = E.run(folder_of('e5min', minute), 'XX', ref)['reference']
adj = {c: [(b[0], b[1] + 12.5, b[2] + 12.5, b[3] + 12.5, b[4] + 12.5, b[5])
           for b in bars] for c, bars in M.items()}
r_adj = E.run(folder_of('e5adj', adj), 'XX', ref)['reference']
one = dict(M)
one['XX 09-24'] = list(M['XX 09-24'])
k = 777
one['XX 09-24'][k] = one['XX 09-24'][k][:5] + (99999,)
one['XX 09-24'][k + 1] = (one['XX 09-24'][k + 1][0],
                          one['XX 09-24'][k + 1][1] + 0.25) + \
    one['XX 09-24'][k + 1][2:]
del one['XX 09-24'][k + 5]
rep_one = E.run(folder_of('e5one', one), 'XX', ref)
r_one = rep_one['reference']
row_one = [r for r in r_one['rows'] if r['contract'] == 'XX 09-24'][0]
t('E5: stamps an hour or a minute off, one price offset everywhere, and '
  'single bars that differ are DIFFERENT, each with what is behind it',
  r_hour['verdict'] == 'DIFFERENT' and
  r_hour['rows'][0]['shift'] == dict(minutes=-60, share=1.0) and
  '-60 minutes off' in r_hour['why'][0] and
  r_hour['rows'][2]['shift'] is not None and
  r_min['verdict'] == 'DIFFERENT' and
  r_min['rows'][0]['shift'] == dict(minutes=1, share=1.0) and
  r_adj['verdict'] == 'DIFFERENT' and r_adj['rows'][0]['offset'] == 12.5
  and r_adj['rows'][0]['shift'] is None and
  'back-adjusted' in r_adj['why'][0] and
  r_adj['rows'][0]['fields'] == {x: len(M['XX 03-24']) for x in 'ohlc'}
  and r_one['verdict'] == 'DIFFERENT' and row_one['different'] == 2 and
  row_one['only_reference'] == 1 and row_one['only_export'] == 0 and
  row_one['fields'] == {'v': 1, 'o': 1} and
  row_one['examples'] == [
      '%s differs in v' % M['XX 09-24'][k][0],
      '%s differs in o' % M['XX 09-24'][k + 1][0],
      '%s only in the reference' % M['XX 09-24'][k + 5][0]] and
  row_one['shift'] is None and row_one['offset'] is None and
  len(r_one['why']) == 1 and '31337' not in E.text(rep_one) and
  '99999' not in E.text(rep_one))

# ---------------------------------------------------------------------
# E6: nothing from the gate on is compared or shown
# ---------------------------------------------------------------------
late_days = weekdays(D(2026, 6, 22), D(2026, 7, 10))
G = {'XX 09-26': contract_bars(late_days, SECRET)}
G_other = {'XX 09-26': [
    b if b[0][:8] < '20260701' else (b[0], 1.0, 2.0, 0.5, 1.5, 1)
    for b in G['XX 09-26']]}
# 2026-06-30 from 22:01 UTC is the session of 2026-07-01
evening = day_bars(D(2026, 6, 30), SECRET, n=120, first_hour=21)
G['XX 09-26'] = sorted(G['XX 09-26'] + evening)
G_other['XX 09-26'] = sorted(G_other['XX 09-26'] + [
    (b[0], 1.0, 2.0, 0.5, 1.5, 1) if b[0] > '20260630 220000' else b
    for b in evening])
fg, fgo = folder_of('e6', G), folder_of('e6o', G_other)
rep6 = E.run(fg, 'XX', fgo)
before6 = sum(1 for b in G['XX 09-26']
              if CX.bar_session(b[0][:8], b[0][9:])[0] < CX.REFUSE_FROM)
row6 = rep6['reference']['rows'][0]
only_late = {'XX 12-26': contract_bars(weekdays(D(2026, 9, 14),
                                                D(2026, 9, 18)), 7.0)}
rep6b = E.run(folder_of('e6b', only_late), 'XX', folder_of('e6br',
                                                           only_late))
t('E6: bars from the gate on are counted and not compared: files that '
  'differ only there are SAME, and a reference without earlier bars is '
  'NOT COMPARED',
  rep6['reference']['verdict'] == 'SAME' and row6['same'] == before6 and
  before6 == 7 * 480 + 60 and
  rep6['export']['contracts'][0]['bars_from_gate'] ==
  len(G['XX 09-26']) - before6 and
  rep6['export']['days_before_gate'] == 7 and
  rep6['export']['days_from_gate'] == 8 and
  rep6b['reference']['verdict'] == 'NOT COMPARED' and
  rep6b['reference']['rows'] == [] and
  rep6b['export']['days_before_gate'] == 0)

# ---------------------------------------------------------------------
# E7: the command and its stops
# ---------------------------------------------------------------------
out7 = os.path.join(WORK, 'check.json')
rc_ok, said_ok, _e = said([f1, '--market', 'XX', '--reference', ref,
                           '--out', out7])
rc_inferred, said_inf, _e = said([f1])
rc_diff, said_diff, _e = said([os.path.join(WORK, 'e5hour'), '--market',
                               'XX', '--reference', ref])
rc_inc, _s, _e = said([f2, '--market', 'XX'])
two = folder_of('e7two')
write(two, 'XX 03-24', M['XX 09-24'], name='XX MAR24.Last.txt')
rc_two, _s, err_two = said([two, '--market', 'XX'])
mixed = folder_of('e7mixed')
write(mixed, 'YY 03-24', M['XX 09-24'])
rc_mixed, _s, err_mixed = said([mixed])
rc_mixed_named, _s, _e = said([mixed, '--market', 'YY'])
rc_none, _s, err_none = said([f1, '--market', 'ZZ'])
rc_nodir, _s, err_nodir = said([os.path.join(WORK, 'nothing'), '--market',
                                'XX'])
rc_usage, _s, err_usage = said([])
rc_noval, _s, err_noval = said([f1, '--market'])
t('E7: the command: 0 when complete and the same, 3 otherwise, a report '
  'file; it stops on a folder that is not one, no files of the market, '
  'two files of one contract, and two markets without --market',
  rc_ok == 0 and 'AGAINST THE REFERENCE' in said_ok and
  'before 20260701: SAME' in said_ok and
  json.load(open(out7))['reference']['verdict'] == 'SAME' and
  rc_inferred == 0 and 'XX' in said_inf.splitlines()[0] and
  rc_diff == 3 and 'DIFFERENT' in said_diff and rc_inc == 3 and
  rc_two == 1 and 'the same contract (XX 03-24)' in err_two and
  rc_mixed == 1 and 'name the market with --market' in err_mixed and
  rc_mixed_named == 0 and
  rc_none == 1 and 'no ZZ minute exports' in err_none and
  rc_nodir == 1 and 'is not a folder' in err_nodir and
  rc_usage == 2 and 'mrofyt_exportcheck.py' in err_usage and
  rc_noval == 1 and '--market needs a value' in err_noval)

# ---------------------------------------------------------------------
# E8: the sessions are the minute reader's, across both clock changes
# ---------------------------------------------------------------------
clock = []
for day in (D(2024, 3, 8), D(2024, 3, 10), D(2024, 3, 11), D(2024, 11, 1),
            D(2024, 11, 3), D(2024, 11, 4), D(2024, 7, 3)):
    clock.extend(day_bars(day, 100.0, n=1380, first_hour=0))
p8 = write(os.path.join(WORK, 'e8'), 'XX 03-24', clock)
l8 = E.load(p8)
want8 = {}
for b in clock:
    s = CX.bar_session(b[0][:8], b[0][9:])[0]
    want8[s] = want8.get(s, 0) + 1
rd8 = CX.Reader('XX')
rd8.read_file(p8)
t('E8: every bar is put in the minute reader\'s session, across the '
  'March and November clock changes and the 18:00 roll',
  l8['sessions'] == want8 and len(want8) == 10 and
  sum(want8.values()) == len(clock) == len(l8['bars']) and
  sorted(want8) == sorted({s for _c, s in rd8.days}) and
  E._stamp(E._minute('20240308', '235900')) == '20240308 235900' and
  E._stamp(E._minute('20000101', '000000')) == '20000101 000000' and
  E.same_bar((1.0, 2.0), (1.0 + 1e-12, 2.0)) and
  not E.same_bar((1.0, 2.0), (1.0, 2.001)) and
  E.holes(['20240105', '20240108', '20240116']) == [
      ('20240108', '20240116', 8)] and
  E.contract_key('XX 03-24') < E.contract_key('XX 12-24') <
  E.contract_key('XX 03-25'))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
