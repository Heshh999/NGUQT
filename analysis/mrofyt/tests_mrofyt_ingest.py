#!/usr/bin/env python3
# MROF-YT-INGEST-1.0 suite: the ingest front door -- CSV parsing,
# timestamp decoding, enum gates and eventSeq merging -- exercised
# directly on hand-built recorder-format fixtures. Every fixture here
# is synthetic and verifies CODE BEHAVIOR only, never market evidence.
# No outcome, R or P&L exists anywhere.
#
# Why a separate suite: tests_mles_v12.py owns the audit's merge and
# pairing checks, but it shells out to mcs/mono at import time to build
# the C# recorder harness, so on a machine without the Mono toolchain
# it aborts before a single Python check runs. The pure functions below
# need no toolchain, so the parsing and merging paths every ingest pass
# depends on stay covered wherever Python runs.
import csv
import datetime as _dt
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v11_adapter as AD11   # noqa: E402
import mles_v12_adapter as AD     # noqa: E402
import mles_v12_audit as AU       # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


def raises(exc, fn, *a, **kw):
    """True when fn raises exc. A test that asserts a gate must prove
    the gate fired, never merely that nothing came back."""
    try:
        fn(*a, **kw)
    except exc:
        return True
    except Exception:
        return False
    return False


def _msg(path, kind):
    """The text of the error a file raises -- an operator reading the
    skip report has only this string to find the bad file by."""
    try:
        AD.parse_file(path, kind)
    except Exception as exc:
        return str(exc)
    return ''


WORK = tempfile.mkdtemp(prefix='mrofyt_ingest_', dir='/tmp')
EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)

# A row of each kind, as the recorder writes it: values keyed by the
# canonical header so a fixture can override one field by name.
BASE = dict(schema=AD.SCHEMA, captureInstanceId='ci-1', runId='r-1',
            segId='0', session='20260901', instrument='NQ',
            contract='NQ 12-26', stream='', eventSeq='1', streamSeq='1',
            tRecvUtc='2026-09-01T13:30:00.1234567Z',
            tExchUtc='2026-09-01T13:30:00.1200000Z', tMono='1000',
            flags='')
EXTRA = {
    'quotes': dict(side='BID', px='15000.25', sz='4', bidPx='15000.25',
                   bidSz='4', askPx='15000.50', askSz='7', flags=''),
    'trades': dict(px='15000.50', sz='2', bidPx='15000.25', bidSz='4',
                   askPx='15000.50', askSz='7', aggrRaw='Buy',
                   aggrInf='BUY', aggrMethod='TICK', aggrConf='HIGH',
                   flags=''),
    'depth':  dict(bookType='MBP', action='ADD', side='BID', level='0',
                   px='15000.25', sz='4', flags=''),
    'quality': dict(kind='HEARTBEAT', detail='ok', flags=''),
}


def row(file_kind, **over):
    """One recorder row of `file_kind` as a list in canonical header
    order. Named `file_kind` because 'kind' is itself a quality column,
    which an override has to be free to set."""
    d = dict(BASE)
    d.update(EXTRA[file_kind])
    d['stream'] = AD.STREAM_OF_FILE[file_kind]
    d.update(over)
    return [d[c] for c in AD.HEADERS[file_kind]]


_seq_n = [0]


def write(kind, rows, name=None, header=None, raw_tail=None):
    """Write a recorder CSV and return its path. `header` replaces the
    canonical header; `raw_tail` is appended verbatim (blank lines and
    other things csv.writer will not emit)."""
    _seq_n[0] += 1
    p = os.path.join(WORK, name or ('%s_%d.csv' % (kind, _seq_n[0])))
    with open(p, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(AD.HEADERS[kind] if header is None else header)
        for r in rows:
            w.writerow(r)
        if raw_tail is not None:
            fh.write(raw_tail)
    return p


# =====================================================================
# A. tRecvUtc/tExchUtc decoding. iso_to_epoch is a fixed-format fast
# path in front of the ISO parser; every event in every stream goes
# through it, so a silent divergence between the two would shift the
# whole ingest rather than fail it.
# =====================================================================
def _iso_epoch(s):
    d = AD.parse_iso(s)
    return None if d is None else (d - EPOCH).total_seconds()


FAST = ['2026-09-01T13:30:00Z', '2026-09-01T13:30:00.1234567Z',
        '2026-09-01T00:00:00.0000000Z', '2026-12-31T23:59:59.9999999Z',
        '2026-03-08T07:00:00.5Z', '1970-01-01T00:00:00Z']
t('A1: on the recorder fixed format the fast path returns exactly what '
  'the ISO parser returns, to the microsecond',
  all(AD.iso_to_epoch(s) == _iso_epoch(s) for s in FAST) and
  AD.iso_to_epoch('1970-01-01T00:00:00Z') == 0.0)

t('A2: a blank timestamp decodes to None, not to the epoch -- a missing '
  'tExchUtc must stay missing rather than become 1970',
  AD.iso_to_epoch('') is None and AD.iso_to_epoch(None) is None and
  AD._to_epoch(None) is None)

# Shapes the recorder does not emit, which a hand-edited or foreign
# file can still contain. Each must fall back, and the fallback must
# agree with the ISO parser rather than guess.
OFF = ['2026-09-01T13:30:00+00:00', '2026-09-01T13:30:00',
       '2026-09-01T13:30:00.abcZ', '2026-09-01T13:30:00.123456789Z',
       '2026-09-01 13:30:00Z', '2026-09-01T13:30Z', 'not a time',
       '2026-09-01T13:30:00.Z', '2026-09-01T13:30:00XZ',
       '2026-09-01T13:30:00.123456Z ']


def _outcome(fn, s):
    """(value) or the exception type, so two decoders can be compared
    on the inputs that are supposed to fail as well as those that are
    supposed to parse."""
    try:
        return ('ok', fn(s))
    except Exception as exc:
        return ('raised', type(exc).__name__)


t('A3: shapes off the fast path defer to the ISO parser completely -- '
  'same value where it parses, same error where it refuses',
  all(_outcome(AD.iso_to_epoch, s) == _outcome(_iso_epoch, s)
      for s in OFF + FAST) and
  _outcome(AD.iso_to_epoch, 'not a time')[0] == 'raised')

t('A4: an impossible date raises from both paths alike, so a corrupt '
  'day can never decode to a plausible epoch',
  raises(ValueError, AD.iso_to_epoch, '2026-13-01T13:30:00Z') and
  raises(ValueError, AD.parse_iso, '2026-13-01T13:30:00Z') and
  raises(ValueError, AD.iso_to_epoch, '2026-09-01T2x:30:00Z'))

# The 100 ns recorder tick is truncated to the microsecond, never
# rounded: a rounded .9999999 would carry into the next second and
# reorder two events that arrived in the order the file records.
_t0 = AD.iso_to_epoch('2026-09-01T13:30:00Z')
t('A5: the sub-second fraction is TRUNCATED to microseconds, never '
  'rounded up, at both ends of a second',
  AD.parse_iso('2026-09-01T13:30:00.1234567Z').microsecond == 123456 and
  AD.parse_iso('2026-09-01T13:30:00.9999999Z').microsecond == 999999 and
  abs((AD.iso_to_epoch('2026-09-01T13:30:00.9999999Z') - _t0)
      - 0.999999) < 1e-6 and
  AD.iso_to_epoch('2026-09-01T13:30:00.9999999Z') <
  AD.iso_to_epoch('2026-09-01T13:30:01Z'))

t('A6: a shorter-than-7-digit fraction is scaled by position, not by '
  'digit count (.5 is half a second, not 5 microseconds)',
  AD.iso_to_epoch('2026-09-01T13:30:00.5Z') -
  AD.iso_to_epoch('2026-09-01T13:30:00Z') == 0.5 and
  AD.iso_to_epoch('2026-09-01T13:30:00.25Z') -
  AD.iso_to_epoch('2026-09-01T13:30:00Z') == 0.25)

# The day component is memoised in a module-level cache. A cache that
# leaked across days would move a whole session by a whole day.
_probe = ['2026-09-01T00:00:00Z', '2026-09-02T00:00:00Z',
          '2026-09-01T00:00:00Z', '2025-12-31T23:59:59Z']
_first = [AD.iso_to_epoch(s) for s in _probe]
_again = [AD.iso_to_epoch(s) for s in reversed(_probe)][::-1]
t('A7: the memoised day base is per-day -- decoding several days in any '
  'order gives each day its own answer, matching the ISO parser',
  _first == _again == [_iso_epoch(s) for s in _probe] and
  _first[1] - _first[0] == 86400.0)


# =====================================================================
# B. Header and row shape. iter_file is the only door into the ingest,
# and the runner's CORRUPT_STREAM net depends on it raising a typed
# error rather than yielding a short row with fields shifted by one.
# =====================================================================
p_ok = write('quotes', [row('quotes', eventSeq='1'),
                        row('quotes', eventSeq='2')], name='b_ok.csv')
t('B1: a canonical file parses, one dict per row, fields decoded',
  [e['event_seq'] for e in AD.parse_file(p_ok, 'quotes', lite=True)] ==
  [1, 2] and
  AD.parse_file(p_ok, 'quotes', lite=True)[0]['bid_px'] == 15000.25)

p_hdr = write('quotes', [row('quotes')], name='b_hdr.csv',
              header=['schema'] + AD.HEADERS['quotes'][2:])
t('B2: a header missing a column is MalformedHeaderError, raised before '
  'any row is yielded -- never a silently shifted file',
  raises(AD.MalformedHeaderError, AD.parse_file, p_hdr, 'quotes') and
  raises(AD.MalformedHeaderError,
         lambda: next(AD.iter_file(p_hdr, 'quotes'))))

p_ord = write('quotes', [row('quotes')], name='b_ord.csv',
              header=[AD.HEADERS['quotes'][1], AD.HEADERS['quotes'][0]]
              + AD.HEADERS['quotes'][2:])
t('B3: a header with the right columns in the wrong ORDER is rejected, '
  'because column order is what maps a value to its field',
  raises(AD.MalformedHeaderError, AD.parse_file, p_ord, 'quotes'))

p_empty = os.path.join(WORK, 'b_empty.csv')
open(p_empty, 'w').close()
t('B4: a zero-byte file is MalformedHeaderError, not an empty run -- a '
  'file that never got written must not read as a stream with no events',
  raises(AD.MalformedHeaderError, AD.parse_file, p_empty, 'quotes'))

p_short = write('quotes', [row('quotes')[:-1]], name='b_short.csv')
p_long = write('quotes', [row('quotes') + ['extra']], name='b_long.csv')
t('B5: a short row and a long row are both rejected, and the error names '
  'the file with the expected and actual column counts',
  raises(AD.MalformedHeaderError, AD.parse_file, p_short, 'quotes') and
  raises(AD.MalformedHeaderError, AD.parse_file, p_long, 'quotes') and
  'b_short.csv' in _msg(p_short, 'quotes') and
  'expected %d columns, got %d' % (len(AD.HEADERS['quotes']),
                                   len(AD.HEADERS['quotes']) - 1)
  in _msg(p_short, 'quotes'))

p_blank = write('quotes', [row('quotes')], name='b_blank.csv',
                raw_tail='\n\n')
t('B6: blank lines are skipped, not errors -- the recorder leaves a '
  'trailing newline and that is not corruption',
  len(AD.parse_file(p_blank, 'quotes', lite=True)) == 1)

# Streaming, not buffering: the runner catches the typed error from
# INSIDE its merge loop, so the good rows before the bad one must
# already have been yielded when it fires.
p_mid = write('quotes', [row('quotes', eventSeq='1'),
                         row('quotes', eventSeq='2'),
                         row('quotes', eventSeq='3')[:-2],
                         row('quotes', eventSeq='4')], name='b_mid.csv')
_got, _err = [], None
try:
    for _e in AD.iter_file(p_mid, 'quotes', lite=True):
        _got.append(_e['event_seq'])
except AD.MalformedHeaderError as _exc:
    _err = _exc
t('B7: a bad row mid-file raises from inside the iteration after the '
  'good rows before it were yielded -- iter_file streams, never buffers',
  _got == [1, 2] and _err is not None)


# =====================================================================
# C. Schema and enum gates. Every one of these is a refusal: an
# unrecognised value must stop the run, because the alternative is a
# feature computed from a field the ingest guessed at.
# =====================================================================
p_sch = write('quotes', [row('quotes', schema='MLES-CAPTURE-1.1')],
              name='c_schema.csv')
t('C1: a row carrying a foreign schema is UnknownEnumError -- a 1.1 file '
  'under a 1.2 name is refused, never read with 1.2 column meanings',
  raises(AD.UnknownEnumError, AD.parse_file, p_sch, 'quotes'))

p_str = write('quotes', [row('quotes', stream='TRADE')], name='c_str.csv')
t('C2: a row whose stream disagrees with the file it sits in is refused, '
  'so trade rows can never be merged in as quotes',
  raises(AD.UnknownEnumError, AD.parse_file, p_str, 'quotes') and
  AD.parse_file(write('quotes', [row('quotes', stream='quote')],
                      name='c_str_ok.csv'), 'quotes',
                lite=True)[0]['stream'] == 'QUOTE')

t('C3: aggrInf and aggrConf accept only the documented values (blank '
  'included, which is the recorder saying it could not infer)',
  all(AD.parse_file(write('trades', [row('trades', aggrInf=v)],
                          name='c_inf_%s.csv' % (v or 'blank')),
                    'trades', lite=True)[0]['aggr_inf'] == v
      for v in AD11._AGGR_INF) and
  raises(AD.UnknownEnumError, AD.parse_file,
         write('trades', [row('trades', aggrInf='MAYBE')],
               name='c_inf_bad.csv'), 'trades') and
  raises(AD.UnknownEnumError, AD.parse_file,
         write('trades', [row('trades', aggrConf='MEDIUM')],
               name='c_conf_bad.csv'), 'trades'))

t('C4: bookType accepts MBP and MBO in any case and refuses anything '
  'else -- the book depth model is not guessed',
  all(AD.parse_file(write('depth', [row('depth', bookType=v)],
                          name='c_bt_%s.csv' % v), 'depth',
                    lite=True)[0]['book_type'] == v.upper()
      for v in ('MBP', 'MBO', 'mbp')) and
  raises(AD.UnknownEnumError, AD.parse_file,
         write('depth', [row('depth', bookType='L2')],
               name='c_bt_bad.csv'), 'depth'))

t('C5: every documented quality kind is accepted and an undocumented '
  'one is refused -- the lifecycle vocabulary is closed',
  all(AD.parse_file(write('quality', [row('quality', kind=k)],
                          name='c_q_%s.csv' % k), 'quality',
                    lite=True)[0]['kind'] == k
      for k in AD.QUALITY_KINDS) and
  raises(AD.UnknownEnumError, AD.parse_file,
         write('quality', [row('quality', kind='BOOK_NEARLY_READY')],
               name='c_q_bad.csv'), 'quality'))

t('C6: side and depth action aliases normalise to one spelling, so a '
  'recorder build that writes B/INSERT is not a second vocabulary',
  AD.parse_file(write('quotes', [row('quotes', side='b')],
                      name='c_side.csv'), 'quotes',
                lite=True)[0]['side'] == 'BID' and
  AD.parse_file(write('depth', [row('depth', action='Insert', side='A')],
                      name='c_act.csv'), 'depth',
                lite=True)[0]['action'] == 'ADD' and
  raises(AD.UnknownEnumError, AD.parse_file,
         write('quotes', [row('quotes', side='MID')],
               name='c_side_bad.csv'), 'quotes'))

t('C7: a blank eventSeq is refused rather than defaulted to 0 -- the '
  'merge orders on this field and a silent 0 would reorder the run',
  raises(AD.UnknownEnumError, AD.parse_file,
         write('quotes', [row('quotes', eventSeq='')],
               name='c_seq.csv'), 'quotes') and
  raises(AD.UnknownEnumError, AD.parse_file,
         write('quotes', [row('quotes', streamSeq='  ')],
               name='c_sseq.csv'), 'quotes'))

t('C8: a blank numeric field stays None instead of collapsing to 0.0 -- '
  'an absent ask size is not a zero-size ask',
  AD.parse_file(write('quotes', [row('quotes', askSz='', px='')],
                      name='c_num.csv'), 'quotes',
                lite=True)[0]['ask_sz'] is None)

# lite=True is what the runner uses on multi-gigabyte files; lite=False
# is what the small-fixture callers use. They must describe the same
# instant, or a lite ingest and a non-lite audit would disagree.
_lt = AD.parse_file(p_ok, 'quotes', lite=True)[0]
_full = AD.parse_file(p_ok, 'quotes', lite=False)[0]
t('C9: lite and non-lite decode the same row to the same instant, one '
  'as epoch seconds and one as an aware datetime',
  isinstance(_full['t_recv'], _dt.datetime) and
  _full['t_recv'].tzinfo is not None and
  isinstance(_lt['t_recv'], float) and
  abs((_full['t_recv'] - EPOCH).total_seconds() - _lt['t_recv']) < 1e-6 and
  {k: v for k, v in _lt.items() if k not in ('t_recv', 't_exch')} ==
  {k: v for k, v in _full.items() if k not in ('t_recv', 't_exch')})


# =====================================================================
# D. The run merge. The four recorder files are separate streams of one
# run, and every downstream feature assumes it sees them in the order
# the exchange produced them. That order is eventSeq, and this merge is
# the only thing that restores it.
# =====================================================================
def run_dir(name, seqs, base=None):
    """A run folder: {kind: [eventSeq, ...]} written to one file each,
    plus the manifest that declares them. Returns (dir, manifest)."""
    d = os.path.join(WORK, name)
    os.makedirs(d, exist_ok=True)
    man = dict(schema=AD.SCHEMA, instrument='NQ', session='20260901',
               runId='r-1')
    for kind, ss in seqs.items():
        fn = '%s.csv' % kind
        with open(os.path.join(d, fn), 'w', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(AD.HEADERS[kind])
            for i, s in enumerate(ss):
                w.writerow(row(kind, eventSeq=str(s), streamSeq=str(i + 1)))
        man[kind] = dict(present=True, file=fn,
                         bytes=os.path.getsize(os.path.join(d, fn)))
    return d, man


d1, man1 = run_dir('d_merge', dict(quotes=[1, 5, 9], trades=[2, 6],
                                   depth=[3, 4, 7], quality=[8, 10]))
_ev = list(AD.merge_run(AD.run_paths(man1, d1), lite=True))
t('D1: the four files interleave into one strictly ascending eventSeq '
  'order, and every event still names the stream it came from',
  [e['event_seq'] for e in _ev] == list(range(1, 11)) and
  [e['stream'] for e in _ev[:4]] == ['QUOTE', 'TRADE', 'DEPTH', 'DEPTH'] and
  set(e['stream'] for e in _ev) == set(AD.STREAM_OF_FILE.values()))

t('D2: run_paths resolves only the streams the manifest declares '
  'present, against the manifest directory, and skips the rest',
  set(AD.run_paths(man1, d1)) == set(AD.STREAMS) and
  all(os.path.dirname(p) == d1 for p in AD.run_paths(man1, d1).values()) and
  set(AD.run_paths(dict(man1, trades=dict(present=False, file='t.csv'),
                        depth=None, quality=dict(present=True)), d1)) ==
  {'quotes'})

t('D3: a run whose manifest declares fewer streams merges the ones it '
  'has, in the same global order, without inventing the absent ones',
  [e['event_seq'] for e in
   AD.merge_run(AD.run_paths(man1, d1), lite=True,
                kinds=('quotes', 'depth'))] == [1, 3, 4, 5, 7, 9])

# The runner catches MalformedHeaderError/UnknownEnumError from inside
# its merge loop and reports the run skipped. That net only works if
# the merge is lazy: a corrupt row late in one file must surface while
# the loop is running, not at merge_run() call time.
d2 = os.path.join(WORK, 'd_corrupt')
os.makedirs(d2, exist_ok=True)
with open(os.path.join(d2, 'quotes.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(AD.HEADERS['quotes'])
    w.writerow(row('quotes', eventSeq='1'))
    w.writerow(row('quotes', eventSeq='3', side='SIDEWAYS'))
with open(os.path.join(d2, 'trades.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(AD.HEADERS['trades'])
    w.writerow(row('trades', eventSeq='2'))
_paths2 = {'quotes': os.path.join(d2, 'quotes.csv'),
           'trades': os.path.join(d2, 'trades.csv')}
_it = AD.merge_run(_paths2, lite=True)
_seen, _raised = [], None
try:
    for _e in _it:
        _seen.append(_e['event_seq'])
except (AD.MalformedHeaderError, AD.UnknownEnumError) as _exc:
    _raised = type(_exc).__name__
t('D4: merge_run is lazy -- constructing it validates no header and '
  'reads no row, so every parse error surfaces inside the runner loop',
  AD.merge_run({'quotes': write('quotes', [row('quotes')],
                                name='d_lazy.csv',
                                header=['bogus'])}, lite=True)
  is not None and
  raises(AD.MalformedHeaderError,
         lambda: next(iter(AD.merge_run(
             {'quotes': os.path.join(WORK, 'd_lazy.csv')}, lite=True)))))

t('D5: a corrupt row raises the typed error from inside the iteration, '
  'which is what the runner catches to skip the run whole',
  _raised == 'UnknownEnumError' and _seen == [1])

# heapq.merge keeps one row of look-ahead per stream, so the error can
# fire up to one event per stream BEFORE the corrupt row's own place in
# the global order -- above, seq 2 never arrives even though it sits in
# a clean file ahead of the bad row. Harmless by construction: the
# runner discards everything the run fed in and reports it skipped, so
# there is no half-ingested prefix for the early stop to truncate.
t('D5a: whatever the look-ahead swallows, the corrupt row itself is '
  'never yielded and what was yielded is a prefix of the clean order',
  3 not in _seen and _seen == [1, 2][:len(_seen)] and
  len(_seen) >= 3 - len(_paths2))

# Memory: the depth file of one genuine session is 25M rows, so the
# merge must hold one row per stream and nothing more.
import tracemalloc                                           # noqa: E402
d3, man3 = run_dir('d_mem', dict(quotes=list(range(1, 60000, 3)),
                                 trades=list(range(2, 60000, 3)),
                                 depth=list(range(3, 60001, 3))))
_p3 = AD.run_paths(man3, d3)
tracemalloc.start()
_n = 0
_last = 0
for _e in AD.merge_run(_p3, lite=True):
    _n += 1
    _last = _e['event_seq']
_peak = tracemalloc.get_traced_memory()[1]
tracemalloc.stop()
t('D6: merging ~60k rows across three streams holds O(streams) memory, '
  'not the file -- the peak stays under a megabyte',
  _n == 60000 and _last == 60000 and _peak < 1024 * 1024)

t('D7: the merge is deterministic -- the same run merged twice yields '
  'the same sequence, so two passes can never disagree',
  [(e['stream'], e['event_seq'])
   for e in AD.merge_run(AD.run_paths(man1, d1), lite=True)] ==
  [(e['stream'], e['event_seq'])
   for e in AD.merge_run(AD.run_paths(man1, d1), lite=True)])

t('D8: merge_streams orders two already-sorted streams on eventSeq '
  'alone, whatever order the iterators are handed to it in',
  [e['event_seq'] for e in AD.merge_streams(
      [iter([dict(event_seq=1), dict(event_seq=4)]),
       iter([dict(event_seq=2), dict(event_seq=3)])])] == [1, 2, 3, 4] and
  [e['event_seq'] for e in AD.merge_streams(
      [iter([dict(event_seq=2), dict(event_seq=3)]),
       iter([dict(event_seq=1), dict(event_seq=4)])])] == [1, 2, 3, 4])


# =====================================================================
# E. The auditor's coverage merge and NQ/MNQ pairing. These are pure
# functions, and they decide whether a session's two instruments are
# judged to have been recorded side by side at all. tests_mles_v12.py
# owns them today, but it builds the C# recorder harness with mcs at
# import time, so on a machine without Mono none of it runs. The checks
# below need no toolchain.
# =====================================================================
def T(h, m=0, s=0, day=1):
    return _dt.datetime(2026, 9, day, h, m, s, tzinfo=_dt.timezone.utc)


def info(inst, first, last, session='20260901', **kw):
    d = dict(instrument=inst, session=session,
             first_recv=first, last_recv=last)
    d.update(kw)
    return d


t('E1: coverage() merges overlapping runs into one interval, keeps '
  'disjoint runs apart, and returns them in time order',
  AU.coverage([info('NQ', T(9), T(11)), info('NQ', T(10), T(12))]) ==
  [(T(9), T(12))] and
  AU.coverage([info('NQ', T(13), T(14)), info('NQ', T(9), T(10))]) ==
  [(T(9), T(10)), (T(13), T(14))] and
  AU.coverage([]) == [])

t('E2: a run wholly inside another does not shorten the coverage -- a '
  'restart nested in a longer run must not shrink the session',
  AU.coverage([info('NQ', T(9), T(16)), info('NQ', T(10), T(11))]) ==
  [(T(9), T(16))])

t('E3: runs that merely touch end to end become one interval, so an '
  'ordinary mid-session restart does not read as two sessions',
  AU.coverage([info('NQ', T(9), T(12)), info('NQ', T(12), T(15))]) ==
  [(T(9), T(15))])

t('E4: a run with no recorded first/last is skipped rather than merged '
  'as a zero-length interval or crashed on',
  AU.coverage([info('NQ', T(9), T(10)), info('NQ', None, None),
               dict(instrument='NQ')]) == [(T(9), T(10))])

t('E5: identical coverage overlaps fully, disjoint coverage not at all, '
  'and coverage that only touches at an endpoint counts as no overlap',
  AU.overlap_frac([(T(9), T(12))], [(T(9), T(12))])[1] == 1.0 and
  AU.overlap_frac([(T(9), T(10))], [(T(11), T(12))]) == (0.0, 0.0) and
  AU.overlap_frac([(T(9), T(10))], [(T(10), T(12))])[0] == 0.0)

t('E6: the overlap is divided by the SMALLER coverage, so a short run '
  'entirely inside a long one is fully paired, not one third paired',
  AU.overlap_frac([(T(9), T(18))], [(T(10), T(13))]) ==
  (3 * 3600.0, 1.0) and
  AU.overlap_frac([(T(10), T(13))], [(T(9), T(18))])[1] == 1.0)

t('E7: overlap against empty coverage is zero and does not divide by '
  'zero -- an instrument with no usable run reports 0, never a crash',
  AU.overlap_frac([], [(T(9), T(12))]) == (0.0, 0.0) and
  AU.overlap_frac([], []) == (0.0, 0.0))

t('E8: overlap sums across several disjoint intervals on each side, so '
  'two restarts on one side still count toward the pairing',
  AU.overlap_frac([(T(9), T(10)), (T(11), T(12))],
                  [(T(9), T(12))]) == (2 * 3600.0, 1.0))

# ---- instance seq contiguity ----------------------------------------


def seq(first, last, count, holes=()):
    return dict(seq_first=first, seq_last=last, seq_count=count,
                seq_holes=list(holes))


t('E9: one run covering 1..N is contiguous, and a run that does not '
  'start at 1 is not -- the instance must account for every seq',
  AU.instance_seq_contiguous([seq(1, 100, 100)])[0] and
  not AU.instance_seq_contiguous([seq(2, 100, 99)])[0] and
  AU.instance_seq_contiguous([])[0] and
  AU.instance_seq_contiguous([seq(0, 0, 0)])[0])

t('E10: a gap between two runs of the same instance is caught, and the '
  'reason names the count against the span',
  not AU.instance_seq_contiguous([seq(1, 10, 10), seq(21, 30, 10)])[0] and
  'count' in AU.instance_seq_contiguous([seq(1, 10, 10),
                                         seq(21, 30, 10)])[1] and
  AU.instance_seq_contiguous([seq(1, 10, 10), seq(11, 20, 10)])[0])

t('E11: a hole inside one run is fine when exactly one other run of the '
  'instance carries it -- that is what rotation interleaving looks like',
  AU.instance_seq_contiguous([seq(1, 11, 10, holes=[6]),
                              seq(6, 6, 1)])[0])

t('E12: a seq claimed by two runs at once is refused -- the rows of a '
  'duplicated rotation boundary would otherwise be ingested twice',
  not AU.instance_seq_contiguous([seq(1, 10, 10), seq(6, 6, 1)])[0] and
  'count 11' in AU.instance_seq_contiguous([seq(1, 10, 10),
                                            seq(6, 6, 1)])[1])

_hole = [seq(1, 10, 9, holes=[3]), seq(6, 6, 1)]
t('E13: a hole no other run of the instance fills is refused, and the '
  'reason names the seq that nothing accounts for',
  not AU.instance_seq_contiguous(_hole)[0] and
  'seq 3 present in 0 runs' == AU.instance_seq_contiguous(_hole)[1])

# ---- NQ/MNQ session pairing -----------------------------------------


def audited(inst, first, last, session='20260901'):
    return dict(info=info(inst, first, last, session=session))


_f, _o = AU.pair_sessions([audited('NQ', T(9), T(16)),
                           audited('MNQ', T(9), T(16))])
t('E14: a session whose NQ and MNQ cover the same hours pairs cleanly, '
  'and the overlap it reports is complete',
  _f == [] and _o['20260901']['overlap_frac'] == 1.0 and
  _o['20260901']['nq_runs'] == 1 and
  _o['20260901']['overlap_seconds'] == 7 * 3600.0)

_f2, _o2 = AU.pair_sessions([audited('NQ', T(9), T(16))])
t('E14b: a session recorded on one instrument only fails as a session '
  'mismatch and reports no overlap at all',
  [c for c, _ in _f2] == ['NQ_MNQ_SESSION_MISMATCH'] and _o2 == {})

# NQ 09:00-16:00 against MNQ 14:00-20:00: two shared hours out of the
# six-hour MNQ side, a third of the smaller coverage.
_f3, _o3 = AU.pair_sessions([audited('NQ', T(9), T(16)),
                             audited('MNQ', T(14), T(20))])
t('E15: coverage that overlaps for less than the required fraction '
  'fails, and the failure carries the fraction it measured',
  [c for c, _ in _f3] == ['NQ_MNQ_INSUFFICIENT_OVERLAP'] and
  abs(_o3['20260901']['overlap_frac'] - 1.0 / 3) < 1e-12 and
  'frac=0.333' in _f3[0][1])

t('E15a: a short run sitting wholly inside the other side is fully '
  'paired, not penalised for the hours it was not recording',
  AU.pair_sessions([audited('NQ', T(9), T(16)),
                    audited('MNQ', T(15), T(16))])[0] == [])

_f4, _o4 = AU.pair_sessions([audited('NQ', T(9), T(12)),
                             audited('NQ', T(12), T(16)),
                             audited('MNQ', T(9), T(16))])
t('E16: the pairing uses the UNION of a side\'s runs, so an ordinary '
  'mid-session restart does not read as half a session of overlap',
  _f4 == [] and _o4['20260901']['overlap_frac'] == 1.0 and
  _o4['20260901']['nq_runs'] == 2)

_f5, _o5 = AU.pair_sessions([audited('NQ', T(9), T(16)),
                             audited('MNQ', T(9), T(16)),
                             audited('ES', T(9), T(10))])
t('E17: an optional instrument is ignored by the pairing rather than '
  'demanded of every session',
  _f5 == [] and AU.OPTIONAL_INSTRUMENTS == ('ES',) and
  set(_o5) == {'20260901'})

_f6, _o6 = AU.pair_sessions([audited('NQ', None, None),
                             audited('MNQ', T(9), T(16))])
t('E18: a side with no usable window is PAIR_WINDOW_UNKNOWN, which is '
  'not the same finding as too little overlap',
  [c for c, _ in _f6] == ['PAIR_WINDOW_UNKNOWN'] and _o6 == {})

_f7, _o7 = AU.pair_sessions([audited('NQ', T(9), T(16), '20260901'),
                             audited('MNQ', T(9), T(16), '20260901'),
                             audited('NQ', T(9), T(16), '20260902')])
t('E19: sessions are paired one at a time -- a good session is not '
  'excused by a bad one beside it, nor punished for it',
  [c for c, _ in _f7] == ['NQ_MNQ_SESSION_MISMATCH'] and
  '20260902' in _f7[0][1] and _o7['20260901']['overlap_frac'] == 1.0)

_thr = [audited('NQ', T(9), T(16)), audited('MNQ', T(14), T(20))]
t('E20: the overlap threshold is a parameter and the default is the one '
  'the auditor documents, so a caller can demand more without a fork',
  AU.MIN_OVERLAP_FRAC == 0.5 and
  [c for c, _ in AU.pair_sessions(_thr, min_overlap=0.5)[0]] ==
  ['NQ_MNQ_INSUFFICIENT_OVERLAP'] and
  AU.pair_sessions(_thr, min_overlap=0.3)[0] == [])


# =====================================================================
# F. Discovery, the step before any parsing. A capture folder is
# whatever the handoff dropped in it: half-copied manifests, manifests
# from another instrument, manifests from another schema. Discovery
# decides which of them the ingest will even look at.
# =====================================================================
import json                                                  # noqa: E402
import mrofyt_runner as RN                                   # noqa: E402

DISC = os.path.join(WORK, 'discover')
os.makedirs(DISC, exist_ok=True)


def manifest(name, **over):
    man = dict(schema=AD.SCHEMA, instrument='NQ', session='20260901',
               runId=name, firstRecvUtc='2026-09-01T13:30:00.0000000Z')
    man.update(over)
    p = os.path.join(DISC, name)
    with open(p, 'w') as fh:
        json.dump(man, fh)
    return p


_m_a = manifest('NQ_20260901_manifest.json')
_m_b = manifest('NQ_20260901_manifest_collision_2.json',
                runId='r-b', firstRecvUtc='2026-09-01T15:00:00.0000000Z')
_m_c = manifest('MNQ_20260901_manifest.json', instrument='MNQ',
                runId='r-c')
open(os.path.join(DISC, 'NQ_20260901_manifest.json.tmp'), 'w').write('{}')
open(os.path.join(DISC, 'notes.json'), 'w').write('{}')

t('F1: discovery finds primary and collision manifests together and in '
  'a stable order, and ignores json that is not a manifest',
  AU.discover_manifests(DISC) == sorted([_m_a, _m_b, _m_c]) and
  not any(p.endswith('notes.json') for p in AU.discover_manifests(DISC)))

t('F2: a half-written manifest still carrying its .tmp suffix is not '
  'discovered, so an in-flight copy is never ingested',
  not any(p.endswith('.tmp') for p in AU.discover_manifests(DISC)))

# A manifest truncated mid-copy is unreadable JSON. It must cost the
# folder that one run, not the whole pass.
open(os.path.join(DISC, 'NQ_20260901_manifest_bad.json'),
     'w').write('{"schema": "MLES-CAPT')
_plan = RN.Runner(DISC, ('NQ', 'MNQ')).plan()
t('F3: a manifest that is not valid JSON is skipped and the manifests '
  'beside it are still planned -- one bad file is not a dead folder',
  sorted((i, s) for i, s, _ in _plan) ==
  [('MNQ', '20260901'), ('NQ', '20260901')] and
  sum(len(r) for _, _, r in _plan) == 3)

manifest('NQ_20260901_manifest_old.json', schema='MLES-CAPTURE-1.1',
         runId='r-old')
manifest('ES_20260901_manifest.json', instrument='ES', runId='r-es')
_plan2 = RN.Runner(DISC, ('NQ', 'MNQ')).plan()
t('F4: a manifest from another schema or another instrument is left out '
  'of the plan rather than read with this schema\'s meanings',
  sum(len(r) for _, _, r in _plan2) == 3 and
  all(m.get('schema') == AD.SCHEMA and m.get('instrument') in ('NQ', 'MNQ')
      for _, _, runs in _plan2 for _, m in runs))

_nq = [runs for i, s, runs in _plan2 if i == 'NQ'][0]
t('F5: the runs of one session are planned in firstRecvUtc order, so a '
  'restart is replayed after the run it restarted, never before',
  [m['runId'] for _, m in _nq] == ['NQ_20260901_manifest.json', 'r-b'])

manifest('NQ_20260901_manifest_norecv.json', runId='r-norecv',
         firstRecvUtc=None)
_nq2 = [runs for i, s, runs in RN.Runner(DISC, ('NQ',)).plan()
        if i == 'NQ'][0]
t('F6: a manifest with no firstRecvUtc is still planned, sorted ahead '
  'of the timed runs instead of crashing the sort',
  [m['runId'] for _, m in _nq2][0] == 'r-norecv' and len(_nq2) == 3)

_plan3 = RN.Runner(DISC, ('NQ',), max_sessions=1).plan()
t('F7: planning is per (instrument, session) and ordered by session, so '
  'a session cap takes whole sessions in time order',
  [(i, s) for i, s, _ in _plan3] == [('NQ', '20260901')])


# =====================================================================
# G. The auditor end to end, on synthetic captures. audit_run streams
# the eventSeq-merged union of a run's four files and checks it against
# the manifest that declares it; audit_capture then judges the folder.
# Both are pure Python, so the whole path can be exercised here without
# the Mono toolchain that tests_mles_v12.py needs for its C# harness.
# Synthetic rows verify CODE BEHAVIOR only, never market evidence.
# =====================================================================
import math                                                  # noqa: E402
import mles_v12_synth as SY                                  # noqa: E402

PRICE = (lambda i: 15000.0                                   # noqa: E731
         + 3.0 * math.sin(2 * math.pi * (i * 0.0005) / 20.0))
_cap_n = [0]


def capture(n_depth=4000):
    """A clean two-instrument capture folder. Returns (dir, nq, mnq)."""
    _cap_n[0] += 1
    d = os.path.join(WORK, 'cap%d' % _cap_n[0])
    kw = dict(n_depth=n_depth, price_path=PRICE, trade_every=10,
              quote_every=5, session='20260901')
    nq = SY.synth_run(d, instrument='NQ', cid='c1', **kw)
    mnq = SY.synth_run(d, instrument='MNQ', cid='c2', **kw)
    return d, nq, mnq


def codes(result):
    return [c for c, _ in result['failures']]


_d, _nq, _mnq = capture()
_run = AU.audit_run(_nq)
_man = json.load(open(_nq))
t('G1: a clean run audits with no findings, and the run info it reports '
  'agrees with the manifest that declared the run',
  _run['ok'] and _run['failures'] == [] and
  _run['info']['run_id'] == _man['runId'] and
  _run['info']['instrument'] == 'NQ' and
  _run['info']['seq_first'] == 1 and
  _run['info']['seq_count'] == _run['info']['seq_last'] and
  _run['info']['seq_holes'] == [] and
  _run['info']['first_recv'] <= _run['info']['last_recv'])

_capr = AU.audit_capture(_d)
t('G2: a clean NQ/MNQ capture folder audits clean end to end and the '
  'pairing it reports covers both sides completely',
  _capr['ok'] and _capr['failures'] == [] and
  _capr['info']['manifests'] == 2 and
  _capr['info']['overlaps']['20260901']['overlap_frac'] == 1.0)

_d3, _nq3, _ = capture()
_m3 = json.load(open(_nq3))
with open(os.path.join(_d3, _m3['depth']['file']), 'r+') as _fh:
    _fh.truncate(_m3['depth']['bytes'] - 500)
t('G3: a bulk CSV shorter than its manifest declares is caught on size '
  'AND on hash, so a half-copied file cannot audit clean',
  {'BYTE_SIZE_MISMATCH', 'HASH_MISMATCH'} <= set(codes(AU.audit_run(_nq3))))

_d4, _nq4, _ = capture()
_m4 = json.load(open(_nq4))
os.remove(os.path.join(_d4, _m4['trades']['file']))
t('G4: a declared stream whose file is absent is MISSING_FILE, reported '
  'rather than crashed on -- manifests arrive before their CSVs',
  codes(AU.audit_run(_nq4)) == ['MISSING_FILE'] and
  'RUN_AUDIT_FAILED' in codes(AU.audit_capture(_d4)))

# A row corrupted without changing the byte count slips past the size
# and hash pre-flight only if the enum gate lets it: this substitution
# is the same length as the value it replaces.
_d5, _nq5, _ = capture()
_m5 = json.load(open(_nq5))
_qf = os.path.join(_d5, _m5['quotes']['file'])
_lines = open(_qf).read().splitlines(True)
_lines[3] = _lines[3].replace(',BID,', ',BAD,', 1)
open(_qf, 'w').writelines(_lines)
_r5 = AU.audit_run(_nq5)
t('G5: an unknown enum in a row that kept the file\'s byte count is '
  'reported as UNKNOWN_ENUM, not raised out of the audit',
  'UNKNOWN_ENUM' in codes(_r5) and not _r5['ok'] and
  'BYTE_SIZE_MISMATCH' not in codes(_r5))

_d6, _, _ = capture()
open(os.path.join(_d6, 'stray.csv'), 'w').write('x\n')
open(os.path.join(_d6, 'MLES12_NQ_x_20260901_c1-R002_depth.csv.partial'),
     'w').write('x\n')
t('G6: a CSV no manifest references and an unfinalized .partial are '
  'both reported, so a folder cannot hide rows from the audit',
  {'ORPHAN_FINALIZED_CSV', 'ORPHAN_PARTIAL'} <= set(codes(
      AU.audit_capture(_d6))))

_d7, _nq7, _ = capture()
_txt = AU.summary(AU.audit_capture(_d7))
_txt_bad = AU.summary(AU.audit_capture(_d4))
t('G7: the summary states the verdict and one line per run, and names '
  'every failure when there is one',
  'ok=True' in _txt and 'manifests=2' in _txt and
  _txt.count('20260901') >= 2 and 'pair 20260901' in _txt and
  'ok=False' in _txt_bad and 'MISSING_FILE' in _txt_bad)

t('G8: a folder holding only one of the two required instruments is '
  'reported missing that instrument as well as unpaired',
  {'MISSING_REQUIRED_INSTRUMENT', 'NQ_MNQ_SESSION_MISMATCH'} <= set(
      codes(AU.audit_capture(os.path.dirname(
          SY.synth_run(os.path.join(WORK, 'solo'), n_depth=2000,
                       price_path=PRICE, trade_every=10, quote_every=5,
                       cid='c9', session='20260901'))))))
shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
