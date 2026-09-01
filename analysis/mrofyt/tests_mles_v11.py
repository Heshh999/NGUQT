#!/usr/bin/env python3
# MLES-CAPTURE-1.1 + adapter + audit suite, including the LITERAL
# recorder-format end-to-end path:
#   recorder CSV -> manifest audit -> parser -> event ordering ->
#   MBP-10 reconstruction -> feature engine
# Synthetic events verify CODE BEHAVIOR only, never market evidence.
import datetime as _dt
import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)

import mles_v11_adapter as AD      # noqa: E402
import mles_v11_audit as AU        # noqa: E402
import mrofyt_signals as SIG       # noqa: E402
sys.path.insert(0, os.path.join(ROOT, 'analysis', 'mrof'))
import mrof_engine as ME           # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-66s %s' % (name, 'PASS' if cond else 'FAIL'))


# =====================================================================
# LITERAL recorder-format fixture: byte-for-byte what the C# emits
# =====================================================================
COMMON = ','.join(AD.HEADER_COMMON)
HEAD = {
    'quotes': COMMON + ',side,px,sz,bidPx,bidSz,askPx,askSz,flags',
    'trades': COMMON + ',px,sz,bidPx,bidSz,askPx,askSz,aggrRaw,'
                       'aggrInf,aggrMethod,aggrConf,flags',
    'depth': COMMON + ',bookType,action,side,level,px,sz,flags',
    'quality': COMMON + ',kind,detail',
}


def iso(base, micro_off, seven='0'):
    """.NET 'yyyy-MM-ddTHH:mm:ss.fffffffZ' — SEVEN fractional digits."""
    d = base + _dt.timedelta(microseconds=micro_off)
    return d.strftime('%Y-%m-%dT%H:%M:%S.') + \
        '%06d%s' % (d.microsecond, seven) + 'Z'


class Fixture:
    def __init__(self, directory, instrument='NQ', contract='NQ 12-26',
                 session='20260901', run_id='20260901120000000-ABC123'):
        self.dir = directory
        self.inst, self.contract = instrument, contract
        self.session, self.run = session, run_id
        self.ev = 0
        self.seq = dict(QUOTE=0, TRADE=0, DEPTH=0, QUALITY=0)
        self.rows = dict(quotes=[], trades=[], depth=[], quality=[])
        self.counts = dict(depthBid=0, depthAsk=0, depthAdd=0,
                           depthUpdate=0, depthRemove=0)
        self.base = _dt.datetime(2026, 9, 1, 13, 30, 0)
        self.first_ev = None

    def _head(self, stream, exch=True, seg=1):
        self.ev += 1
        self.seq[stream] += 1
        if self.first_ev is None:
            self.first_ev = self.ev
        return ','.join([
            AD.SCHEMA, self.run, str(seg), self.session, self.inst,
            self.contract, stream, str(self.ev), str(self.seq[stream]),
            iso(self.base, self.ev * 1000),
            iso(self.base, self.ev * 1000 - 200) if exch else '',
            str(self.ev * 10000)])

    def quote(self, side, px, sz, bid, bsz, ask, asz):
        self.rows['quotes'].append(
            self._head('QUOTE') + ',%s,%s,%s,%s,%s,%s,%s,' %
            (side, px, sz, bid, bsz, ask, asz))

    def trade(self, px, sz, bid, bsz, ask, asz, inf, conf):
        self.rows['trades'].append(
            self._head('TRADE') + ',%s,%s,%s,%s,%s,%s,,%s,QUOTE_TEST_v1,%s,'
            % (px, sz, bid, bsz, ask, asz, inf, conf))

    def depth(self, action, side, level, px, sz):
        self.counts['depthBid' if side == 'BID' else 'depthAsk'] += 1
        self.counts['depth' + action.capitalize()] += 1
        self.rows['depth'].append(
            self._head('DEPTH') + ',MBP,%s,%s,%d,%s,%s,' %
            (action, side, level, px, sz))

    def quality(self, kind, detail):
        self.rows['quality'].append(
            self._head('QUALITY', exch=False) + ',%s,%s' % (kind, detail))

    def build(self):
        """A minimal but complete session: both depth sides, all three
        actions, quotes, trades, session start/end."""
        self.quality('SESSION_START', 'runId=' + self.run)
        self.depth('ADD', 'BID', 0, '15000.00', '12')
        self.depth('ADD', 'ASK', 0, '15000.25', '9')
        self.depth('ADD', 'BID', 1, '14999.75', '20')
        self.depth('ADD', 'ASK', 1, '15000.50', '15')
        self.quote('BID', '15000.00', '12', '15000.00', '12',
                   '15000.25', '9')
        self.quote('ASK', '15000.25', '9', '15000.00', '12',
                   '15000.25', '9')
        self.trade('15000.25', '4', '15000.00', '12', '15000.25', '9',
                   'BUY', 'HIGH')
        self.depth('UPDATE', 'ASK', 0, '15000.25', '5')
        self.trade('15000.25', '5', '15000.00', '12', '15000.25', '5',
                   'BUY', 'HIGH')
        self.depth('REMOVE', 'ASK', 0, '15000.25', '0')
        self.depth('UPDATE', 'BID', 0, '15000.00', '18')
        self.trade('15000.00', '3', '15000.00', '18', '15000.50', '15',
                   'SELL', 'HIGH')
        self.depth('REMOVE', 'BID', 1, '14999.75', '0')
        self.quality('SESSION_END', 'runId=' + self.run)
        return self

    def write(self, mutate=None):
        files = {}
        for kind in ('quotes', 'trades', 'depth', 'quality'):
            name = 'MLES11_%s_%s_%s_%s_%s.csv' % (
                self.inst, self.contract.replace(' ', '_'), self.session,
                self.run, kind)
            path = os.path.join(self.dir, name)
            body = HEAD[kind] + '\n' + \
                ''.join(r + '\n' for r in self.rows[kind])
            if mutate:
                body = mutate(kind, body)
            with open(path, 'w') as fh:
                fh.write(body)
            files[kind] = (name, path, len(self.rows[kind]))
        man = dict(schema=AD.SCHEMA, runId=self.run,
                   connectionSegments=1, session=self.session,
                   instrument=self.inst, contract=self.contract,
                   bookType='MBP',
                   aggressorSource='ABSENT-feed; inferred QUOTE_TEST_v1',
                   firstRecvUtc=iso(self.base, 1000),
                   lastRecvUtc=iso(self.base, self.ev * 1000),
                   lastExchUtc=iso(self.base, self.ev * 1000 - 200),
                   firstEventSeq=self.first_ev, lastEventSeq=self.ev,
                   firstQuoteSeq=1, lastQuoteSeq=self.seq['QUOTE'],
                   firstTradeSeq=1, lastTradeSeq=self.seq['TRADE'],
                   firstDepthSeq=1, lastDepthSeq=self.seq['DEPTH'],
                   firstQualitySeq=1, lastQualitySeq=self.seq['QUALITY'],
                   gaps=0, duplicates=0, reversals=0, queueOverflows=0,
                   droppedRows=0, writeErrors=0, reconnects=0, crossed=0,
                   bookResets=0, **self.counts)
        for kind, (name, path, rows) in files.items():
            man[kind] = dict(present=True, file=name,
                             bytes=os.path.getsize(path), rows=rows,
                             sha256=AU.sha256(path))
        mpath = os.path.join(self.dir, 'MLES11_%s_%s_%s_%s_manifest.json'
                             % (self.inst,
                                self.contract.replace(' ', '_'),
                                self.session, self.run))
        with open(mpath, 'w') as fh:
            json.dump(man, fh, indent=1)
        return mpath


TMP = tempfile.mkdtemp(prefix='mles11_',
                       dir=os.environ.get('TMPDIR', '/tmp'))


def fresh(sub, **kw):
    d = os.path.join(TMP, sub)
    os.makedirs(d, exist_ok=True)
    return Fixture(d, **kw).build()


# =====================================================================
# D. adapter
# =====================================================================
ts = AD.parse_iso('2026-09-01T13:30:00.1234567Z')
t('D1: 7-fraction-digit .NET ISO-8601 parses WITHOUT float()',
  ts == _dt.datetime(2026, 9, 1, 13, 30, 0, 123456,
                     tzinfo=_dt.timezone.utc))
t('D1b: fractional digits are truncated, never rounded',
  AD.parse_iso('2026-09-01T00:00:00.9999999Z').microsecond == 999999)
t('D1c: offset timestamps and empty values handled',
  AD.parse_iso('2026-09-01T09:30:00.000000+05:30').utcoffset() ==
  _dt.timedelta(hours=5, minutes=30) and AD.parse_iso('') is None)
src = open(os.path.join(HERE, 'mles_v11_adapter.py')).read()
ts_fn = src.split('def parse_iso')[1].split('\ndef ')[0]
t('D1d: parse_iso contains no float() call', 'float(' not in ts_fn)

t('D2: side/action enums normalize (Insert->ADD, Bid->BID)',
  AD._action('Insert') == 'ADD' and AD._action('update') == 'UPDATE' and
  AD._action('Delete') == 'REMOVE' and AD._side('Bid') == 'BID' and
  AD._side('a') == 'ASK')
for bad, fn in (('SWEEP', AD._action), ('MIDDLE', AD._side)):
    try:
        fn(bad)
        got = False
    except AD.UnknownEnumError:
        got = True
    t('D3: unknown enum %r REJECTED (never silently ignored)' % bad, got)

fx = fresh('good')
mpath = fx.write()
q = AD.parse_file(os.path.join(fx.dir, os.path.basename(
    json.load(open(mpath))['quotes']['file'])), 'quotes')
t('D4: canonical quote carries identity + both clocks',
  q[0]['run_id'] == fx.run and q[0]['contract'] == 'NQ 12-26' and
  q[0]['seg_id'] == 1 and q[0]['side'] == 'BID' and
  q[0]['t_recv'].tzinfo is not None and q[0]['t_exch'] is not None)

# =====================================================================
# E. audit — happy path then adversarial
# =====================================================================
res = AU.audit_run(mpath)
t('E1: clean run passes the manifest-authoritative audit',
  res['ok'] and res['failures'] == [])
t('E1b: audit reports both depth sides and all three actions',
  res['info']['depth_sides'] == ['ASK', 'BID'] and
  res['info']['depth_actions'] == ['ADD', 'REMOVE', 'UPDATE'])


def codes(r):
    return {c for c, _ in r['failures']}


d = os.path.join(TMP, 'corrupt')
os.makedirs(d, exist_ok=True)
fx2 = Fixture(d, run_id='RUN-CORRUPT').build()
m2 = fx2.write()
man = json.load(open(m2))
qf = os.path.join(d, man['quotes']['file'])
with open(qf, 'a') as fh:
    fh.write(HEAD['quotes'].split(',')[0] + '\n')   # tamper
t('E2 adversarial: corrupted file -> HASH_MISMATCH',
  'HASH_MISMATCH' in codes(AU.audit_run(m2)))

d = os.path.join(TMP, 'seqreset')
os.makedirs(d, exist_ok=True)
fx3 = Fixture(d, run_id='RUN-SEQRESET').build()


def reset_seq(kind, body):
    if kind != 'depth':
        return body
    lines = body.split('\n')
    out = [lines[0]]
    for i, ln in enumerate(lines[1:]):
        if not ln:
            out.append(ln)
            continue
        c = ln.split(',')
        if i >= 3:
            c[7] = '1'                    # eventSeq reset to 1
        out.append(','.join(c))
    return '\n'.join(out)


m3 = fx3.write(mutate=reset_seq)
t('E3 adversarial: sequence reset -> SEQUENCE_REVERSAL',
  'SEQUENCE_REVERSAL' in codes(AU.audit_run(m3)))

d = os.path.join(TMP, 'mixedcontract')
os.makedirs(d, exist_ok=True)
fx4 = Fixture(d, run_id='RUN-MIXC').build()


def mix_contract(kind, body):
    if kind != 'trades':
        return body
    lines = body.split('\n')
    for i in range(2, min(4, len(lines))):
        if lines[i]:
            c = lines[i].split(',')
            c[5] = 'NQ 03-27'             # a different contract
            lines[i] = ','.join(c)
    return '\n'.join(lines)


m4 = fx4.write(mutate=mix_contract)
t('E4 adversarial: two contracts inside one file -> MIXED_CONTRACT',
  'MIXED_CONTRACT' in codes(AU.audit_run(m4)))

d = os.path.join(TMP, 'mixedrun')
os.makedirs(d, exist_ok=True)
fx5 = Fixture(d, run_id='RUN-MIXR').build()


def mix_run(kind, body):
    if kind != 'quotes':
        return body
    lines = body.split('\n')
    if len(lines) > 2 and lines[2]:
        c = lines[2].split(',')
        c[1] = 'OTHER-RUN'
        lines[2] = ','.join(c)
    return '\n'.join(lines)


m5 = fx5.write(mutate=mix_run)
t('E5 adversarial: appended foreign run -> MIXED_RUN',
  'MIXED_RUN' in codes(AU.audit_run(m5)))

d = os.path.join(TMP, 'nodepthask')
os.makedirs(d, exist_ok=True)
fx6 = Fixture(d, run_id='RUN-NOASK')
fx6.quality('SESSION_START', 'x')
fx6.depth('ADD', 'BID', 0, '15000.00', '12')
fx6.depth('UPDATE', 'BID', 0, '15000.00', '15')
fx6.depth('REMOVE', 'BID', 0, '15000.00', '0')
fx6.quote('BID', '15000.00', '12', '15000.00', '12', '15000.25', '9')
fx6.trade('15000.25', '2', '15000.00', '12', '15000.25', '9',
          'BUY', 'HIGH')
m6 = fx6.write()
t('E6 adversarial: depth missing the ASK side -> MISSING_DEPTH_SIDE',
  'MISSING_DEPTH_SIDE' in codes(AU.audit_run(m6)))

d = os.path.join(TMP, 'badhead')
os.makedirs(d, exist_ok=True)
fx7 = Fixture(d, run_id='RUN-BADHEAD').build()
m7 = fx7.write(mutate=lambda k, b: ('bogus,header\n' +
                                    '\n'.join(b.split('\n')[1:]))
               if k == 'quality' else b)
t('E7 adversarial: malformed header -> MALFORMED_HEADER',
  'MALFORMED_HEADER' in codes(AU.audit_run(m7)))

d = os.path.join(TMP, 'rowcount')
os.makedirs(d, exist_ok=True)
fx8 = Fixture(d, run_id='RUN-ROWS').build()
m8 = fx8.write()
man8 = json.load(open(m8))
man8['trades']['rows'] += 5
json.dump(man8, open(m8, 'w'), indent=1)
t('E8 adversarial: row-count disagreement -> ROW_COUNT_MISMATCH',
  'ROW_COUNT_MISMATCH' in codes(AU.audit_run(m8)))

d = os.path.join(TMP, 'counters')
os.makedirs(d, exist_ok=True)
fx9 = Fixture(d, run_id='RUN-COUNTERS').build()
m9 = fx9.write()
man9 = json.load(open(m9))
man9['droppedRows'] = 3
json.dump(man9, open(m9, 'w'), indent=1)
t('E9: recorder-reported dropped rows FAIL the audit',
  'RECORDER_REPORTED_DROPPEDROWS' in codes(AU.audit_run(m9)))

d = os.path.join(TMP, 'unknownenum')
os.makedirs(d, exist_ok=True)
fx10 = Fixture(d, run_id='RUN-ENUM').build()
m10 = fx10.write(mutate=lambda k, b: b.replace(',MBP,ADD,BID,',
                                               ',MBP,SWEEP,BID,')
                 if k == 'depth' else b)
t('E10 adversarial: unknown depth action -> UNKNOWN_ENUM failure',
  'UNKNOWN_ENUM' in codes(AU.audit_run(m10)))

# ---- capture-level: NQ+MNQ required, ES optional, collisions --------
cap = os.path.join(TMP, 'capture')
os.makedirs(cap, exist_ok=True)
Fixture(cap, instrument='NQ', contract='NQ 12-26',
        run_id='RUN-NQ-1').build().write()
r_nqonly = AU.audit_capture(cap)
t('E11: capture with only NQ -> MISSING_REQUIRED_INSTRUMENT (MNQ)',
  ('MISSING_REQUIRED_INSTRUMENT', 'MNQ') in r_nqonly['failures'])
Fixture(cap, instrument='MNQ', contract='MNQ 12-26',
        run_id='RUN-MNQ-1').build().write()
r_both = AU.audit_capture(cap)
t('E12: NQ + MNQ present -> capture audit passes',
  r_both['ok'] and r_both['instruments'] == ['MNQ', 'NQ'])
Fixture(cap, instrument='ES', contract='ES 12-26',
        run_id='RUN-ES-1').build().write()
t('E13: ES is explicitly OPTIONAL (its presence changes nothing)',
  AU.audit_capture(cap)['ok'])

coll = os.path.join(TMP, 'restart_collision')
os.makedirs(coll, exist_ok=True)
Fixture(coll, instrument='NQ', contract='NQ 12-26',
        run_id='RUN-SAME').build().write()
f_dup = Fixture(coll, instrument='NQ', contract='NQ 12-26',
                run_id='RUN-SAME').build()
f_dup.session = '20260902'
mdup = f_dup.write()
shutil.copy(mdup, mdup + '.dup_manifest.json')
Fixture(coll, instrument='MNQ', contract='MNQ 12-26',
        run_id='RUN-MNQ-2').build().write()
t('E14 adversarial: restart collision (duplicate runId) -> '
  'RESTART_COLLISION',
  'RESTART_COLLISION' in {c for c, _ in AU.audit_capture(coll)['failures']})

roll = os.path.join(TMP, 'roll_collision')
os.makedirs(roll, exist_ok=True)
a = Fixture(roll, instrument='NQ', contract='NQ 12-26',
            run_id='RUN-ROLL').build()
a.write()
b = Fixture(roll, instrument='NQ', contract='NQ 03-27',
            run_id='RUN-ROLL').build()
b.write()
Fixture(roll, instrument='MNQ', contract='MNQ 12-26',
        run_id='RUN-MNQ-3').build().write()
rc = {c for c, _ in AU.audit_capture(roll)['failures']}
t('E15 adversarial: one runId spanning two contracts -> '
  'CONTRACT_ROLL_COLLISION', 'CONTRACT_ROLL_COLLISION' in rc)

# =====================================================================
# LITERAL END-TO-END: CSV -> audit -> parse -> order -> MBP-10 -> feats
# =====================================================================
e2e = AU.audit_run(mpath)
assert e2e['ok'], e2e['failures']
ordered = e2e['events']
t('E2E-1: manifest audit is the entrypoint and it passed', e2e['ok'])
t('E2E-2: global event ordering is strictly monotonic across all '
  'four streams',
  [x['event_seq'] for x in ordered] ==
  sorted(x['event_seq'] for x in ordered) and
  len({x['event_seq'] for x in ordered}) == len(ordered))
book = SIG.KLevelBook(k=10)
for e in ordered:
    if e['stream'] == 'DEPTH':
        book.apply(e['action'], e['side'].lower(), e['level'],
                   e['px'], e['sz'])
t('E2E-3: MBP-10 reconstruction from literal depth rows',
  book.depth('bid', 10) == 18 and book.depth('ask', 10) == 15 and
  abs(book.bi(10) - (18 - 15) / 33.0) < 1e-12)
trades = [(e['t_recv'].timestamp(), e['px'], e['sz'],
           1 if e['aggr_inf'] == 'BUY' else
           -1 if e['aggr_inf'] == 'SELL' else 0)
          for e in ordered if e['stream'] == 'TRADE']
d_, nd = SIG.aggr_delta(trades)
t('E2E-4: feature engine consumes the canonical trades (delta +6 of '
  '12 classified)', d_ == 6 and abs(nd - 0.5) < 1e-12)
qs = [e for e in ordered if e['stream'] == 'QUOTE']
st = ME.quote_state(dict(bidPx=qs[-1]['bid_px'], bidSz=qs[-1]['bid_sz'],
                          askPx=qs[-1]['ask_px'], askSz=qs[-1]['ask_sz']))
t('E2E-5: quote state derives a valid 1-tick spread from literal rows',
  st['state'] == 'VALID' and st['spread_ticks'] == 1)

shutil.rmtree(TMP, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
