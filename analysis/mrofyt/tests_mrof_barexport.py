#!/usr/bin/env python3
# MROF-BAR-EXPORT-1.0 suite: compiles src/MrofBarExport.cs with mcs on
# nt8_stubs_export.cs and RUNS it with mono on a fake feed (which
# contracts it asks for and how, the UTC stamps it writes across both
# clock changes, what it does after an error, a contract NinjaTrader
# does not know, a feed that never answers, a chart that is closed), then
# reads what it wrote with the export check. The stubs are NOT
# NinjaTrader: this proves the script's own logic and nothing about the
# real API. The F5 compile and the first real run are the operator's.
# Needs mcs and mono; without them nothing is tested.
import datetime as _dt
import os
import shutil
import subprocess
import sys
import tempfile
import zoneinfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)

import mrofyt_exportcheck as E       # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


if not (shutil.which('mcs') and shutil.which('mono')):
    print('  mcs and mono are not installed: the export script cannot be '
          'run here. Nothing was tested.')
    print('\n0/0 tests passed')
    sys.exit(0)

WORK = tempfile.mkdtemp(prefix='mrof_barexport_')
SCRIPT = os.path.join(ROOT, 'src', 'MrofBarExport.cs')
STUBS = os.path.join(HERE, 'nt8_stubs_export.cs')
HARNESS = os.path.join(HERE, 'mrof_export_harness.cs')
UTC = _dt.timezone.utc
CHICAGO = zoneinfo.ZoneInfo('America/Chicago')
NEW_YORK = zoneinfo.ZoneInfo('America/New_York')


def build(name, *flags):
    exe = os.path.join(WORK, name + '.exe')
    cp = subprocess.run(['mcs', '-warn:4'] + list(flags) + [
        '-out:' + exe, STUBS, SCRIPT, HARNESS], capture_output=True,
        text=True)
    return exe, cp


# ---------------------------------------------------------------------
# X1: the script compiles on the stubs
# ---------------------------------------------------------------------
EXE, cp2 = build('two')
EXE1, cp1 = build('one', '-define:ONE_ARG_ONLY')
_e5, cp5 = build('five', '-langversion:5')
src = open(SCRIPT, encoding='utf-8').read()
code = '\n'.join(ln for ln in src.splitlines()
                 if not ln.strip().startswith('//'))
t('X1: the script compiles on the stubs with no warning, also as C# 5 and '
  'where GetInstrument has one form; it names no order or account API, '
  'and none of the types whose namespace is not certain',
  cp2.returncode == 0 and cp1.returncode == 0 and cp5.returncode == 0 and
  'warning' not in (cp2.stdout + cp2.stderr + cp5.stdout + cp5.stderr) and
  not any(w in code for w in (
      'EnterLong', 'EnterShort', 'ExitLong', 'ExitShort', 'SubmitOrder',
      'CreateOrder', 'Account', 'AtmStrategy', 'CancelOrder', 'ChangeOrder'))
  and 'SetEnum(req, "MergePolicy", "DoNotMerge")' in code and
  'SetEnum(req, "LookupPolicy", "Provider")' in code and
  'Rollover ' not in code and 'MergePolicy.' not in code and
  'LookupPolicies' not in code and 'ErrorCode' not in code
  and '"Default 24 x 7"' in code and 'MROF-BAR-EXPORT-1.0' in code and
  'THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING' in src and
  'the F5 compile and the first' in src)
if cp2.returncode or cp1.returncode:
    print(cp2.stdout, cp2.stderr, cp1.stdout, cp1.stderr)
    print('\n%d/%d tests passed' % (0, len(OK)))
    sys.exit(1)


# ---------------------------------------------------------------------
# the fake market
# ---------------------------------------------------------------------
def utc(y, m, d, hh, mm):
    return _dt.datetime(y, m, d, hh, mm, tzinfo=UTC)


def bars_from(start, n, base):
    """n one-minute bars ending from `start` (UTC) on."""
    out = []
    for k in range(n):
        p = base + 0.25 * (k % 9)
        out.append((start + _dt.timedelta(minutes=k), p, p + 0.75, p - 0.5,
                    p + 0.1 + 0.2, 3 + k))
    return out


TODAY = _dt.datetime.now(UTC).date()
CUR = (TODAY.replace(day=1) + _dt.timedelta(days=32)).replace(day=1)
FAR = (CUR + _dt.timedelta(days=31 * 8)).replace(day=1)
CUR_NAME = 'ES %02d-%02d' % (CUR.month, CUR.year % 100)
YDAY = TODAY - _dt.timedelta(days=1)

FEED = {
    # both sides of the March 2016 and November 2016 clock changes
    'ES 03-16': bars_from(utc(2015, 12, 14, 14, 31), 30, 2012.25) +
    bars_from(utc(2016, 3, 11, 23, 30), 60, 2015.0) +
    bars_from(utc(2016, 3, 13, 22, 1), 45, 2016.5),
    'ES 06-16': bars_from(utc(2016, 3, 10, 14, 31), 30, 2002.0) +
    bars_from(utc(2016, 3, 14, 13, 31), 30, 2004.0) +
    bars_from(utc(2016, 6, 10, 20, 30), 40, 2090.25),
    'ES 09-16': bars_from(utc(2016, 9, 1, 14, 0), 10, 2170.0),
    'ES 12-16': bars_from(utc(2016, 11, 4, 19, 30), 30, 2085.0) +
    bars_from(utc(2016, 11, 6, 23, 1), 30, 2095.0) +
    bars_from(utc(2016, 11, 7, 14, 31), 30, 2125.0),
    'ES 03-17': bars_from(utc(2017, 1, 5, 15, 0), 10, 2260.0),
    CUR_NAME: bars_from(_dt.datetime(YDAY.year, YDAY.month, YDAY.day, 10, 0,
                                     tzinfo=UTC), 20, 6800.0),
}
MONTHS = ['2015-12', '2016-03', '2016-06', '2016-09', '2016-12', '2017-03',
          '2017-06', CUR.strftime('%Y-%m'), FAR.strftime('%Y-%m')]
ASKED = ['ES 03-16', 'ES 06-16', 'ES 09-16', 'ES 12-16', 'ES 03-17',
         'ES 06-17', CUR_NAME]


def feed_file(name, bars, zone, future=False):
    path = os.path.join(WORK, 'feed_%s_%s.txt' % (
        name.replace(' ', '_'), zone.key.replace('/', '_')))
    with open(path, 'w') as fh:
        for b in bars:
            fh.write('%s;%r;%r;%r;%r;%d\n' % ((b[0].astimezone(
                zone).strftime('%Y-%m-%d %H:%M:%S'),) + b[1:]))
        if future:
            fh.write('FUTURE;1.0;2.0;0.5;1.5;9\n')
    return path


def scenario(name, exe, zone=CHICAGO, tz='UTC', zone_line=True,
             known=('ES 03-16',), behavior=(), extra=(), feed=None,
             months=None, root='ES'):
    lines = ['root;%s' % root, 'fromyear;2016', 'answer;1', 'wait;60']
    if zone_line:
        lines.append('zone;%s' % zone.key)
    lines += ['month;%s' % m for m in (MONTHS if months is None else months)]
    lines += ['known;%s' % k for k in known]
    for c, bars in (FEED if feed is None else feed).items():
        lines.append('bars;%s;%s' % (c, feed_file(c, bars, zone,
                                                  future=c == CUR_NAME)))
    lines += ['behavior;%s;%s' % b for b in behavior]
    lines += list(extra)
    path = os.path.join(WORK, name + '.txt')
    with open(path, 'w') as fh:
        fh.write('\n'.join(lines) + '\n')
    out = os.path.join(WORK, name)
    env = dict(os.environ, TZ=tz)
    run = subprocess.run(['mono', exe, path, out], capture_output=True,
                         text=True, timeout=180, env=env)
    req, printed, done = [], [], {}
    for ln in run.stdout.splitlines():
        if ln.startswith('HARNESS request '):
            req.append(dict(p.split('=', 1) for p in ln.split()[2:]))
        elif ln.startswith('HARNESS print '):
            printed.append(ln[len('HARNESS print '):])
        elif ln.startswith('HARNESS done '):
            done = dict(p.split('=', 1) for p in ln.split()[2:])
    return dict(rc=run.returncode, req=req, printed=printed, done=done,
                out=os.path.join(out, root), err=run.stderr,
                text='\n'.join(printed))


def read(path):
    with open(path) as fh:
        return [ln.rstrip('\n') for ln in fh]


def expected(bars):
    return [(b[0].strftime('%Y%m%d %H%M%S'),) + b[1:] for b in bars]


def parsed(path):
    out = []
    for ln in read(path):
        p = ln.split(';')
        out.append((p[0], float(p[1]), float(p[2]), float(p[3]), float(p[4]),
                    int(p[5])))
    return out


def add_months(d, k):
    m = d.year * 12 + d.month - 1 + k
    return _dt.date(m // 12, m % 12 + 1, 1)


# ---------------------------------------------------------------------
# X2: the whole run - what it asks for, writes and says
# ---------------------------------------------------------------------
main = scenario('main', EXE, behavior=(('ES 09-16', 'error'),
                                       ('ES 12-16', 'async'),
                                       ('ES 03-17', 'silent')))
names = [r['name'].replace('_', ' ') for r in main['req']]
t('X2a: it asks once for each contract from the first year on, not for '
  'one far ahead, in order, each on its own, at the provider, in '
  'one-minute bars on the 24-hour template',
  main['rc'] == 0 and main['done'].get('ok') == '1' and
  main['done'].get('defaults') == '1' and names == ASKED and
  all(r['merge'] == 'DoNotMerge' and r['lookup'] == 'Provider' and
      r['hours'] == 'Default_24_x_7' and r['period'] == 'Minute/1'
      for r in main['req']))

windows_ok = True
for r in main['req']:
    mm, yy = r['name'].split('_')[1].split('-')
    cm = _dt.date(2000 + int(yy), int(mm), 1)
    lo = add_months(cm, -7).strftime('%Y%m%d')
    hi = add_months(cm, 1)
    his = {min(hi, TODAY + _dt.timedelta(days=k)).strftime('%Y%m%d')
           for k in (0, 1, 2)}
    windows_ok = windows_ok and r['from'] == lo and r['to'] in his
t('X2b: each request runs from seven months before the contract month '
  'to a month after it, and never past tomorrow',
  windows_ok and main['req'][0]['from'] == '20150801' and
  main['req'][0]['to'] == '20160401')

files = sorted(os.listdir(main['out']))
wrote = {c: parsed(os.path.join(main['out'], c + '.Last.txt'))
         for c in ('ES 03-16', 'ES 06-16', 'ES 12-16', CUR_NAME)}
t('X2c: one file per contract with bars, named as a manual export; the '
  'stamps are UTC at the bar\'s end on both sides of both clock changes; '
  'prices and volumes come back exactly; a bar still forming is left out',
  files == sorted([c + '.Last.txt' for c in wrote] + ['MROF_EXPORT_ES.txt'])
  and all(wrote[c] == expected(FEED[c]) for c in wrote) and
  wrote['ES 03-16'][30][0] == '20160311 233000' and
  wrote['ES 03-16'][90][0] == '20160313 220100' and
  wrote['ES 12-16'][0][0] == '20161104 193000' and
  wrote['ES 12-16'][60][0] == '20161107 143100' and
  read(os.path.join(main['out'], 'ES 03-16.Last.txt'))[0] ==
  '20151214 143100;2012.25;2013;2011.75;2012.55;3' and
  len(wrote[CUR_NAME]) == 20)

summ = read(os.path.join(main['out'], 'MROF_EXPORT_ES.txt'))
rows = [ln.split(';') for ln in summ if ln.startswith('contract;')]
total = sum(len(v) for v in wrote.values())
t('X2d: the summary names every contract with what happened to it, and '
  'ends with "complete"; the run goes on after an error, a contract '
  'without bars and a feed that never answers',
  summ[0] == 'MROF-BAR-EXPORT-1.0' and summ[1] == 'market;ES' and
  summ[2].startswith('written_utc;%d' % TODAY.year) and
  summ[3] == 'time_zone;America/Chicago' and
  summ[4] == 'merge_policy;DoNotMerge' and
  summ[5] == 'lookup_policy;Provider' and summ[6] == 'contracts;7' and
  summ[7] == 'with_bars;4' and summ[8] == 'bars;%d' % total and
  summ[-1] == 'complete' and
  [(r[1], r[2], int(r[3])) for r in rows] == [
      ('ES 03-16', 'OK', 135), ('ES 06-16', 'OK', 100),
      ('ES 09-16', 'ERROR', 0), ('ES 12-16', 'OK', 90),
      ('ES 03-17', 'NO ANSWER', 0), ('ES 06-17', 'NO BARS', 0),
      (CUR_NAME, 'OK', 20)] and
  rows[0][4:6] == ['20151214 143100', '20160313 224500'] and
  'UnableToLoadData the harness refuses this contract' in rows[2][6] and
  'no answer in 1 seconds' in rows[4][6])

t('X2e: what it prints: the folder, each contract as it is done, and '
  'COMPLETE with the counts; old contracts were created on the fly and '
  'every answered request was disposed of',
  'MROF EXPORT ES  -  no orders  -  MROF-BAR-EXPORT-1.0' in main['text'] and
  'contracts  7  (ES 03-16 to %s)' % CUR_NAME in main['text'] and
  'MROF export  ES 06-16  OK  bars 100' in main['text'] and
  '[7/7]' in main['text'] and 'MROF EXPORT COMPLETE  ES' in main['text'] and
  'contracts with bars  4 of 7' in main['text'] and
  'without bars         1' in main['text'] and
  'ERROR / NO ANSWER    2' in main['text'] and
  'NOT FOUND' not in main['text'] and
  main['text'].count('MROF EXPORT COMPLETE') == 1 and
  main['done']['created'] == '6' and main['done']['disposed'] == '6')

# ---------------------------------------------------------------------
# X3: the export check reads what the script wrote
# ---------------------------------------------------------------------
ref = os.path.join(WORK, 'reference')
os.makedirs(ref)
for c in ('ES 03-16', 'ES 06-16', 'ES 12-16'):
    with open(os.path.join(ref, c + '.Last.txt'), 'w') as fh:
        for b in expected(FEED[c]):
            fh.write('%s;%r;%r;%r;%r;%d\n' % b)
rep = E.run(main['out'], 'ES', ref)
s3 = rep['export']['script_summary']
t('X3: the export check finds the script\'s files the SAME as files '
  'written straight from the feed, and reads its summary: the error, the '
  'feed that never answered and the contract without bars between two',
  rep['reference']['verdict'] == 'SAME' and
  rep['reference']['compared'] == 3 and
  [r['same'] for r in rep['reference']['rows']] == [135, 100, 90] and
  s3['complete'] and s3['version'] == 'MROF-BAR-EXPORT-1.0' and
  s3['time_zone'] == 'America/Chicago' and
  s3['statuses'] == {'OK': 4, 'ERROR': 1, 'NO ANSWER': 1, 'NO BARS': 1} and
  any('ES 09-16: ERROR' in w for w in rep['export']['why']) and
  any('ES 03-17: NO ANSWER' in w for w in rep['export']['why']) and
  any('ES 06-17: NO BARS' in w for w in rep['export']['why']))

# ---------------------------------------------------------------------
# X4: the time zone is NinjaTrader's, not the computer's
# ---------------------------------------------------------------------
tokyo = scenario('tokyo', EXE, tz='Asia/Tokyo',
                 behavior=(('ES 09-16', 'error'), ('ES 03-17', 'error')))
local = scenario('local', EXE, zone=NEW_YORK, tz='America/New_York',
                 zone_line=False,
                 behavior=(('ES 09-16', 'error'), ('ES 03-17', 'error')))
t('X4: on a computer in another time zone the same UTC stamps are '
  'written; where NinjaTrader gives no zone, the computer\'s is used',
  tokyo['rc'] == 0 and local['rc'] == 0 and
  all(parsed(os.path.join(tokyo['out'], c + '.Last.txt')) ==
      expected(FEED[c]) for c in ('ES 03-16', 'ES 06-16', 'ES 12-16')) and
  all(parsed(os.path.join(local['out'], c + '.Last.txt')) ==
      expected(FEED[c]) for c in ('ES 03-16', 'ES 06-16', 'ES 12-16')) and
  read(os.path.join(tokyo['out'], 'MROF_EXPORT_ES.txt'))[3] ==
  'time_zone;America/Chicago' and
  'MROF EXPORT COMPLETE' in tokyo['text'] and
  'MROF EXPORT COMPLETE' in local['text'])

# ---------------------------------------------------------------------
# X5: a NinjaTrader that cannot create a contract
# ---------------------------------------------------------------------
one = scenario('one', EXE1, known=('ES 03-16', 'ES 12-16'))
rows1 = [ln.split(';') for ln in read(os.path.join(
    one['out'], 'MROF_EXPORT_ES.txt')) if ln.startswith('contract;')]
t('X5: where a contract cannot be found or created it is NOT FOUND, the '
  'others are written and the run completes',
  one['rc'] == 0 and [r['name'] for r in one['req']] == ['ES_03-16',
                                                         'ES_12-16'] and
  [(r[1], r[2]) for r in rows1] == [
      ('ES 03-16', 'OK'), ('ES 06-16', 'NOT FOUND'),
      ('ES 09-16', 'NOT FOUND'), ('ES 12-16', 'OK'),
      ('ES 03-17', 'NOT FOUND'), ('ES 06-17', 'NOT FOUND'),
      (CUR_NAME, 'NOT FOUND')] and
  'NOT FOUND            5' in one['text'] and
  'MROF EXPORT COMPLETE' in one['text'] and one['done']['created'] == '0'
  and sorted(os.listdir(one['out'])) == [
      'ES 03-16.Last.txt', 'ES 12-16.Last.txt', 'MROF_EXPORT_ES.txt'])

# ---------------------------------------------------------------------
# X6: the chart is closed while it runs
# ---------------------------------------------------------------------
os.makedirs(os.path.join(WORK, 'closed', 'ES'))
stale = os.path.join(WORK, 'closed', 'ES', 'MROF_EXPORT_ES.txt')
with open(stale, 'w') as fh:
    fh.write('MROF-BAR-EXPORT-1.0\ncomplete\n')
closed = scenario('closed', EXE, behavior=(('ES 06-16', 'late'),),
                  extra=('terminate_after_ms;500',))
t('X6: closed in mid-run it asks for nothing more, writes nothing of '
  'the late answer and leaves no summary, so the folder shows an export '
  'that did not finish (an older summary is removed at the start)',
  closed['rc'] == 0 and len(closed['req']) == 2 and
  sorted(os.listdir(closed['out'])) == ['ES 03-16.Last.txt'] and
  'MROF EXPORT COMPLETE' not in closed['text'] and
  'ES 06-16  STOPPED' in closed['text'] and not os.path.exists(stale))

# ---------------------------------------------------------------------
# X7: nothing to export
# ---------------------------------------------------------------------
none = scenario('none', EXE, root='NONE')
empty = scenario('empty', EXE, months=['2014-03', '2015-12'], feed={})
again = scenario('again', EXE, feed={'ES 03-16': FEED['ES 03-16']},
                 months=['2016-03'])
t('X7: a chart without an instrument and a market without contract '
  'months write nothing and say so; a second start on the same chart '
  'asks for nothing twice',
  none['rc'] == 0 and none['req'] == [] and
  'the chart has no instrument. Nothing is written.' in none['text'] and
  not os.path.isdir(none['out']) and
  empty['rc'] == 0 and empty['req'] == [] and
  'ES has no contract months from 2016 on' in empty['text'] and
  os.listdir(empty['out']) == [] and
  again['rc'] == 0 and len(again['req']) == 1 and
  again['text'].count('MROF EXPORT COMPLETE') == 1)

# ---------------------------------------------------------------------
# X8: a NinjaTrader without one of the two request policies
# ---------------------------------------------------------------------
EXE_NM, cp_nm = build('nomerge', '-define:NO_MERGE_POLICY')
EXE_NL, cp_nl = build('nolookup', '-define:NO_LOOKUP_POLICY')
nm = scenario('nomerge', EXE_NM)
nl = scenario('nolookup', EXE_NL, behavior=(('ES 09-16', 'error'),
                                            ('ES 03-17', 'error')))
summ_nm = read(os.path.join(nm['out'], 'MROF_EXPORT_ES.txt'))
summ_nl = read(os.path.join(nl['out'], 'MROF_EXPORT_ES.txt'))
t('X8: where a contract cannot be asked for on its own, nothing is asked '
  'for or written and every contract is an ERROR that says why; where '
  'the feed cannot be named, the bars are written and the summary and '
  'the Output window say so',
  cp_nm.returncode == 0 and cp_nl.returncode == 0 and nm['rc'] == 0 and
  nm['req'] == [] and os.listdir(nm['out']) == ['MROF_EXPORT_ES.txt'] and
  summ_nm[4] == 'merge_policy;NOT SET' and summ_nm[7] == 'with_bars;0' and
  sum(1 for ln in summ_nm if ';ERROR;0;;;this NinjaTrader gives no way to '
      'ask for a contract on its own (MergePolicy)' in ln) == 7 and
  summ_nm[-1] == 'complete' and 'ERROR / NO ANSWER    7' in nm['text'] and
  nl['rc'] == 0 and summ_nl[4] == 'merge_policy;DoNotMerge' and
  summ_nl[5] == 'lookup_policy;NOT SET' and summ_nl[7] == 'with_bars;4' and
  'gave no way to ask the data feed (LookupPolicy)' in nl['text'] and
  'LookupPolicy' not in main['text'] and
  parsed(os.path.join(nl['out'], 'ES 06-16.Last.txt')) ==
  expected(FEED['ES 06-16']))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
