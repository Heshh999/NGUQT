#!/usr/bin/env python3
# ======================================================================
# MLES-V1 CAPTURE INTEGRITY CHECKER  -  OUTCOME-BLIND
# ======================================================================
# Reads only raw capture files and reports schema/coverage/clock/
# sequence/gap/corruption health. It computes NO return, label, signal,
# direction, MFE, MAE or P&L, and it refuses to import anything that
# could. Safe to run during protected partitions (section 11).
#
#   python3 mles_integrity.py <capture_dir> [--session YYYYMMDD]
#
# Exit code 0 = PASS, 1 = WARN, 2 = FAIL.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import csv
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta

SCHEMA = 'MLES-CAPTURE-1.0.0'
STREAMS = ('quotes', 'trades', 'depth', 'quality')
HDR = {
 'quotes': ['schema','runId','session','instrument','contract','stream','seq','tExch','tCb',
            'tRecv','tMono','side','px','sz','bidPx','bidSz','askPx','askSz','flags'],
 'trades': ['schema','runId','session','instrument','contract','stream','seq','tExch','tCb',
            'tRecv','tMono','px','sz','bidPx','bidSz','askPx','askSz','aggrRaw','aggrInf',
            'aggrMethod','aggrConf','flags'],
 'depth':  ['schema','runId','session','instrument','contract','stream','seq','tExch','tCb',
            'tRecv','tMono','bookType','operation','side','level','px','sz','flags'],
 'quality':['schema','runId','session','instrument','tRecv','tMono','kind','detail'],
}
# fields that must never appear in a capture file (outcome leakage guard)
FORBIDDEN = {'pnl','net','mfe','mae','return','label','signal','direction','win','profit'}


def ts(s):
    return datetime.strptime(s[:26] + 'Z', '%Y-%m-%dT%H:%M:%S.%fZ') if s else None


def check_file(path, kind):
    r = dict(path=os.path.basename(path), stream=kind, rows=0, parse_fail=0,
             dup_seq=0, seq_gaps=0, ts_reversal_recv=0, ts_reversal_exch=0,
             crossed=0, first=None, last=None, sha256=None, findings=[])
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for ch in iter(lambda: fh.read(1 << 20), b''):
            h.update(ch)
    r['sha256'] = h.hexdigest()
    with open(path, newline='') as fh:
        rd = csv.reader(fh)
        try:
            hdr = next(rd)
        except StopIteration:
            r['findings'].append('FAIL empty file')
            return r
        if hdr != HDR[kind]:
            r['findings'].append('FAIL header mismatch for %s' % kind)
            return r
        bad = FORBIDDEN & {c.lower() for c in hdr}
        if bad:
            r['findings'].append('FAIL outcome-bearing column present: %s' % sorted(bad))
        i = {c: k for k, c in enumerate(hdr)}
        seen, last_seq, prev_recv, prev_exch = set(), None, None, None
        for row in rd:
            if len(row) != len(hdr):
                r['parse_fail'] += 1
                continue
            r['rows'] += 1
            if row[i['schema']] != SCHEMA:
                r['findings'].append('FAIL schema %r != %s' % (row[i['schema']], SCHEMA))
                return r
            if kind != 'quality':
                s = int(row[i['seq']])
                if s in seen:
                    r['dup_seq'] += 1
                seen.add(s)
                if last_seq is not None and s != last_seq + 1:
                    r['seq_gaps'] += 1
                last_seq = s
                e = ts(row[i['tExch']])
                if prev_exch and e and e < prev_exch:
                    r['ts_reversal_exch'] += 1
                prev_exch = e or prev_exch
                if kind in ('quotes', 'trades'):
                    b, a = row[i['bidPx']], row[i['askPx']]
                    if b and a and float(b) >= float(a):
                        r['crossed'] += 1
            rv = ts(row[i['tRecv']])
            if prev_recv and rv and rv < prev_recv:
                r['ts_reversal_recv'] += 1
            prev_recv = rv or prev_recv
            if r['first'] is None:
                r['first'] = row[i['tRecv']]
            r['last'] = row[i['tRecv']]
    return r


def audit(dirpath, session=None):
    out = dict(dir=dirpath, sessions={}, verdict='PASS', findings=[])
    pat = os.path.join(dirpath, 'MLES_*_%s_*.csv' % (session or '*'))
    files = sorted(glob.glob(pat))
    if not files:
        out['verdict'] = 'FAIL'
        out['findings'].append('FAIL no capture files found in %s' % dirpath)
        return out
    for f in files:
        base = os.path.basename(f)[:-4].split('_')
        if len(base) < 4:
            continue
        inst, sess, kind = base[1], base[2], base[3]
        if kind not in STREAMS:
            continue
        s = out['sessions'].setdefault(sess, {}).setdefault(inst, {})
        s[kind] = check_file(f, kind)

    for sess, insts in out['sessions'].items():
        for inst, streams in insts.items():
            missing = [k for k in STREAMS if k not in streams]
            if missing:
                out['findings'].append('WARN %s/%s missing streams %s' % (sess, inst, missing))
            for kind, r in streams.items():
                for fnd in r['findings']:
                    out['findings'].append('%s/%s/%s %s' % (sess, inst, kind, fnd))
                if r['parse_fail']:
                    rate = r['parse_fail'] / max(1, r['rows'] + r['parse_fail'])
                    lvl = 'FAIL' if rate > 0.001 else 'WARN'
                    out['findings'].append('%s %s/%s/%s parse failures %d (%.4f%%)'
                                           % (lvl, sess, inst, kind, r['parse_fail'], 100 * rate))
                if r['dup_seq']:
                    out['findings'].append('FAIL %s/%s/%s duplicate sequence numbers %d'
                                           % (sess, inst, kind, r['dup_seq']))
                if r['ts_reversal_recv']:
                    out['findings'].append('FAIL %s/%s/%s receive-clock reversals %d'
                                           % (sess, inst, kind, r['ts_reversal_recv']))
                if r['ts_reversal_exch']:
                    out['findings'].append('WARN %s/%s/%s exchange-clock reversals %d '
                                           '(expected on some feeds; must be bounded)'
                                           % (sess, inst, kind, r['ts_reversal_exch']))
                if r['crossed']:
                    out['findings'].append('WARN %s/%s/%s crossed/locked quote rows %d'
                                           % (sess, inst, kind, r['crossed']))
        # cross-instrument coverage for this session
        want = {'NQ', 'ES', 'MNQ'}
        have = set(insts)
        if not want <= have:
            out['findings'].append('WARN %s missing instrument(s) %s'
                                   % (sess, sorted(want - have)))
    if any(f.startswith('FAIL') for f in out['findings']):
        out['verdict'] = 'FAIL'
    elif any(f.startswith('WARN') for f in out['findings']):
        out['verdict'] = 'WARN'
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sess = None
    if '--session' in sys.argv:
        sess = sys.argv[sys.argv.index('--session') + 1]
    res = audit(sys.argv[1], sess)
    print(json.dumps(res, indent=1, default=str))
    print('\nVERDICT: %s   (%d findings)' % (res['verdict'], len(res['findings'])))
    sys.exit({'PASS': 0, 'WARN': 1, 'FAIL': 2}[res['verdict']])
