#!/usr/bin/env python3
# MLES-V1 Mode A tests (§22 subset applicable before capture exists).
# Synthetic fixtures only. No protected outcome is opened.
import csv
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import mles_integrity as MI  # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-62s %s' % (name, 'PASS' if cond else 'FAIL'))


SRC = open(os.path.join(REPO, 'src', 'MlesV1CaptureHost.cs')).read()
# Strip comments before the order-API scan: the header comment legitimately
# NAMES the APIs the class does not have, and prose must not fail a code test.
CODE = re.sub(r'/\*.*?\*/', '', re.sub(r'//[^\n]*', '', SRC), flags=re.S)

print('recorder structural safety (§8, §22)')
ORDER_API = ['EnterLong', 'EnterShort', 'ExitLong', 'ExitShort', 'SubmitOrderUnmanaged',
             'SetStopLoss', 'SetProfitTarget', 'SetTrailStop', 'CancelOrder',
             'ChangeOrder', 'AtmStrategyCreate', 'Account.', 'CreateOrder']
found = [a for a in ORDER_API if a in CODE]
t('contains no order-entry API call', found == [])
t('is an Indicator, not a Strategy',
  'class MlesV1CaptureHost : Indicator' in SRC and ': Strategy' not in SRC)
t('declares zero-order intent in header', 'CANNOT TRADE' in SRC)

print('schema completeness (§7)')
for f in ('schema', 'runId', 'session', 'instrument', 'contract', 'stream', 'seq',
          'tExch', 'tCb', 'tRecv', 'tMono', 'flags'):
    t('common field %-10s present' % f, '"%s' % f in SRC or ',%s' % f in SRC or f in SRC)
t('both BBO sides on every quote row', 'bidPx,bidSz,askPx,askSz' in SRC)
t('aggressor raw and inferred are separate fields',
  'aggrRaw,aggrInf,aggrMethod,aggrConf' in SRC)
t('raw aggressor left empty (not guessed)', '"", inf, meth, conf' in SRC)
t('book type recorded as MBP, never MBO', '"MBP"' in SRC and 'MBO' not in SRC.split('DEPTH TYPE')[1][:400])

print('capture hygiene (§8)')
t('refuses to capture into analysis/docs/scratchpad',
  '"/analysis"' in SRC and '"/docs"' in SRC and '"/scratchpad"' in SRC)
t('manifest written atomically (temp then move)',
  '.tmp' in SRC and 'File.Move(tmp, final)' in SRC)
t('session id rolls at 18:00 ET, not UTC midnight', 'et.Hour >= 18' in SRC)
t('monotonic clock used for intra-run deltas', 'Stopwatch' in SRC)
t('no credential or account logging', 'Account' not in CODE)

print('integrity checker: synthetic fixtures')
d = tempfile.mkdtemp()


def write(inst, sess, kind, rows):
    p = os.path.join(d, 'MLES_%s_%s_%s.csv' % (inst, sess, kind))
    with open(p, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(MI.HDR[kind])
        w.writerows(rows)
    return p


def qrow(seq, tr, bid=100.0, ask=100.25, te=None):
    return [MI.SCHEMA, 'R1', '20260901', 'NQ', 'NQ 12-26', 'QUOTE', seq,
            te or tr, tr, tr, seq * 1000, 'B', bid, 5, bid, 5, ask, 7, '']


good = [qrow(i, '2026-09-01T13:30:%02d.0000000Z' % i) for i in range(1, 11)]
write('NQ', '20260901', 'quotes', good)
write('NQ', '20260901', 'trades', [])
write('NQ', '20260901', 'depth', [])
write('NQ', '20260901', 'quality', [])
r = MI.audit(d, '20260901')
t('clean fixture parses with 10 rows',
  r['sessions']['20260901']['NQ']['quotes']['rows'] == 10)
t('missing ES/MNQ raises a WARN, not silence',
  any('missing instrument' in f for f in r['findings']))

bad = list(good)
bad.append(qrow(5, '2026-09-01T13:30:05.0000000Z'))      # duplicate seq
write('NQ', '20260902', 'quotes', bad)
for k in ('trades', 'depth', 'quality'):
    write('NQ', '20260902', k, [])
r2 = MI.audit(d, '20260902')
t('duplicate sequence number detected -> FAIL',
  r2['verdict'] == 'FAIL' and any('duplicate sequence' in f for f in r2['findings']))

rev = [qrow(1, '2026-09-01T13:30:05.0000000Z'), qrow(2, '2026-09-01T13:30:01.0000000Z')]
write('NQ', '20260903', 'quotes', rev)
for k in ('trades', 'depth', 'quality'):
    write('NQ', '20260903', k, [])
r3 = MI.audit(d, '20260903')
t('receive-clock reversal detected -> FAIL',
  any('receive-clock reversals' in f for f in r3['findings']))

crossed = [qrow(1, '2026-09-01T13:30:01.0000000Z', bid=101.0, ask=100.0)]
write('NQ', '20260904', 'quotes', crossed)
for k in ('trades', 'depth', 'quality'):
    write('NQ', '20260904', k, [])
r4 = MI.audit(d, '20260904')
t('crossed quote detected', any('crossed/locked' in f for f in r4['findings']))

p = write('NQ', '20260905', 'quotes', good)
open(p, 'a').write('short,row\n')
for k in ('trades', 'depth', 'quality'):
    write('NQ', '20260905', k, [])
r5 = MI.audit(d, '20260905')
t('malformed row counted as parse failure',
  r5['sessions']['20260905']['NQ']['quotes']['parse_fail'] == 1)

print('outcome-blindness (§11, §22)')
IS = open(os.path.join(HERE, 'mles_integrity.py')).read()
t('integrity checker imports no analysis/strategy module',
  not re.search(r'import\s+(numpy|pandas|cand_spec|rvmr_run|mofad_lib)', IS))
t('integrity checker computes no P&L/label term',
  not re.search(r'\b(pnl|mfe|mae|win_rate|expectancy)\s*=', IS))
t('forbidden outcome columns are rejected by the checker',
  'FORBIDDEN' in IS and 'outcome-bearing column present' in IS)
t('no protected partition path referenced',
  'VALIDATION' not in IS and 'LOCKBOX' not in IS)

print('readiness status honesty')
ST = json.load(open(os.path.join(HERE, 'MLES_V1_READINESS_STATUS.json')))
t('engineering capture days = 0 (recorder not yet attached)',
  ST['engineering']['days_captured'] == 0)
t('no readiness gate claimed passed', ST['all_gates_passed'] is False)
t('Mode C recorded as not authorized', ST['mode_c_authorized'] is False)

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
