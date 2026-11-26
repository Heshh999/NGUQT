#!/usr/bin/env python3
# MROF-YT-W29-SPEED-1.0 suite. The panel's rows from hand-built tape
# (every number worked out by hand), the two passive orders, the reader
# against the adapter, the runner's rules for which sessions may be
# read, the panel file, the 48 inputs, the walked-forward forecast, the
# three ways to trade, the verdict, the freeze and the one-time
# confirmation are exercised on hand-built rows, on panels built here
# with and without a planted effect, and on recorder-format runs.
# Synthetic data verifies CODE BEHAVIOR only, never market evidence. No
# order, fill or P&L exists.
import array
import collections
import csv
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

import mles_v12_adapter as AD        # noqa: E402
import mrofyt_runner as RUN          # noqa: E402
import mrofyt_speed29 as W           # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


def near(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def about(a, b):
    """Equal as far as a clock in seconds since 1970 can tell."""
    return abs(a - b) <= 1e-5


WORK = tempfile.mkdtemp(prefix='mrofyt_w29_')
REG = ' '.join(open(os.path.join(HERE, W.REGISTRATION),
                    encoding='utf-8').read().split())
EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def said_by(fn):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = fn()
    return rc, buf.getvalue()


def stopped_with(fn, kinds=(W.SpeedDataError, RUN.NoCaptureData)):
    try:
        fn()
    except kinds as exc:
        return str(exc)
    return None


# ---------------------------------------------------------------------
# S1: the clock and the grid
# ---------------------------------------------------------------------
def utc(y, mo, d, h=0, mi=0, s=0):
    return (_dt.datetime(y, mo, d, h, mi, s, tzinfo=_dt.timezone.utc)
            - EPOCH).total_seconds()


t('S1: a row every 5 seconds from 08:00:00 to 16:15:00 New York, in '
  'summer and in winter time; the constants are the registration\'s',
  W.panel_start('20260901') == utc(2026, 9, 1, 12) and
  W.panel_start('20261105') == utc(2026, 11, 5, 13) and
  W.ROWS == 5941 and W.STEP == 5 and
  W.row_time('20260901', 1140) == utc(2026, 9, 1, 13, 35) and
  W.sod_of_row(0) == 8 * 3600 and W.sod_of_row(W.ROWS - 1) == 16 * 3600 + 900
  and W.row_of_sod(9 * 3600 + 35 * 60) == 1140 and
  RUN.session_id(W.panel_start('20261105')) == '20261105' and
  (W.FIRST_SESSION, W.LAST_SESSION, W.FRESH_FROM) ==
  ('20260901', '20261113', '20261116') and
  (W.COMMISSION, W.COMMISSION_MICRO, W.DELAY, W.DELAY_STRESS) ==
  (0.25, 0.75, 0.5, 1.0) and W.MAX_QUOTE_AGE == 10.0 and
  (W.JOIN_LIFE, W.JOIN_GRACE) == (10.0, 0.5) and W.TICK == 0.25 and
  W.INSTRUMENTS == ('NQ', 'MNQ') and
  all(x in REG for x in (
      'FROZEN on 2026-11-26', 'one row every **5 seconds** from 08:00:00 '
      'to 16:15:00 New York time', 'A quote is in force for at most 10 '
      'seconds', 'Commission **0.25 points** a round trip (NQ)',
      'also reported at **0.75** (MNQ)', '**t + 0.5 s**', '**t + 1.0 s**',
      'It is cancelled after 10 seconds; a fill up to 0.5 s after that '
      'still counts', 'The depth files are not opened',
      '2026-09-01 to 2026-11-13', 'from 2026-11-16 on')))

# ---------------------------------------------------------------------
# S2: one row, every number by hand
# ---------------------------------------------------------------------
SES = '20260901'
T0 = W.panel_start(SES)
G = 720                                  # the row of 09:00:00
T = T0 + W.STEP * G
bk = W.Book(SES, True)
bk.quote(T - 8.0, 100.00, 5, 100.25, 7)
bk.quote(T - 3.0, 100.00, 9, 100.25, 7)          # the bid grows by 4
bk.trade(T - 2.5, 100.25, 3, 1)
bk.quote(T - 0.4, 100.25, 2, 100.50, 4)          # both sides step up
bk.trade(T - 0.2, 100.25, 1, -1)
bk.quote(T + 0.3, 100.25, 2, 100.50, 1)          # the offer thins by 3
bk.trade(T + 1.2, 100.50, 1, 1)
bk.trade(T + 2.0, 100.50, 1, 1)                  # the offer's queue is done
bk.trade(T + 3.0, 100.00, 2, -1)                 # through the bid
bk.quote(T + 3.1, 99.75, 3, 100.25, 2)           # and the quote says so
bk.quote(T + 12.0, 99.75, 3, 100.25, 2)
c = bk.col
qi_want = 2.0 * (5 - 7) / 12.0 + 2.6 * (9 - 7) / 16.0 + 0.4 * (2 - 4) / 6.0
t('S2a: the row at 09:00:00: the quote in force, the imbalance of the '
  'best quotes, who hit, volume and price times size, the last second '
  'alone, the queue and spread integrals and the squared second moves',
  c['v'][G] == 1.0 and (c['bid'][G], c['bs'][G], c['ask'][G], c['az'][G])
  == (100.25, 2.0, 100.50, 4.0) and c['ofi'][G] == 13.0 and
  (c['buy'][G], c['sell'][G], c['vol'][G], c['nb'][G], c['ns'][G]) ==
  (3.0, 1.0, 4.0, 1.0, 1.0) and near(c['pv'][G], 401.0) and
  c['ofi1'][G] == 9.0 and c['tfi1'][G] == -1.0 and
  about(c['qi'][G], qi_want) and about(c['qt'][G], 5.0) and
  about(c['spr'][G], 5.0) and about(c['s1'][G], 5.0) and c['s2'][G] == 0.0
  and near(c['sq'][G], 0.0625) and c['sqn'][G] == 5.0 and
  c['gap'][G] == 0.0)
t('S2b: half a second and a second later, the two join orders (the '
  'offer filled when its queue has traded, the bid when a trade prints '
  'through it and the quote confirms), and the deep window',
  (c['b05'][G], c['a05'][G], c['b10'][G], c['a10'][G]) ==
  (100.25, 100.50, 100.25, 100.50) and
  c['fs'][G] == 1500.0 and c['fb'][G] == 2600.0 and
  (c['lo'][G], c['hi'][G], c['lob'][G], c['hia'][G]) ==
  (100.00, 100.50, 99.75, 100.50) and
  c['ofi'][G + 1] == 3.0 - 4.0 and
  (c['buy'][G + 1], c['sell'][G + 1], c['nb'][G + 1], c['ns'][G + 1]) ==
  (2.0, 2.0, 2.0, 1.0) and c['bid'][G + 1] == 99.75 and
  c['fb'][G - 1] == -1.0 and c['fb'][G + 1] == -1.0 and
  # the offer joined 4.5 s before the row was lifted through as well
  c['fs'][G - 1] == 5700.0)

# ---------------------------------------------------------------------
# S3: quotes that go stale, interruptions, and what does not fill
# ---------------------------------------------------------------------
bk = W.Book(SES, True)
bk.quote(T - 1.0, 100.00, 5, 100.50, 5)          # two ticks wide
bk.quote(T + 0.2, 100.00, 5, 100.50, 5)
#   nothing for 14 seconds: the quote of T + 0.2 runs out at T + 10.2
bk.quote(T + 21.0, 100.00, 4, 100.25, 4)
bk.trade(T + 26.0, 100.00, 3, -1)                # 3 of the 4 ahead
bk.trade(T + 27.0, 100.00, 1, 1)                 # a buyer's print: not counted
bk.trade(T + 28.0, 99.75, 1, -1)                 # through, never confirmed
bk.brk(T + 41.0)                                 # the feed drops
bk.quote(T + 52.0, 100.00, 4, 100.25, 4)
bk.trade(T + 56.0, 99.50, 5, -1)                 # through ...
bk.brk(T + 57.0)                                 # ... but the feed drops
bk.finish()
c = bk.col
t('S3a: a quote is in force 10 seconds and no longer; a row without one '
  'is not usable and its seconds are not counted; a two-tick spread is '
  'counted as two',
  c['v'][G] == 1.0 and c['v'][G + 1] == 1.0 and c['v'][G + 2] == 1.0 and
  c['v'][G + 3] == 0.0 and c['v'][G + 4] == 0.0 and c['v'][G + 5] == 1.0
  and about(c['qt'][G + 1], 5.0) and about(c['qt'][G + 2], 5.0) and
  about(c['qt'][G + 3], 0.2) and c['qt'][G + 4] == 0.0 and
  about(c['qt'][G + 5], 4.0) and about(c['s2'][G + 1], 5.0) and
  c['s1'][G + 1] == 0.0 and about(c['spr'][G + 1], 10.0) and
  about(c['s1'][G + 5], 4.0) and c['b05'][G + 2] == 0.0 and
  c['b05'][G + 1] == 100.0 and c['b05'][G + 3] == 0.0 and
  c['fb'][G + 3] == -1.0 and c['sqn'][G + 3] == 0.0 and
  c['sqn'][G + 2] == 5.0)
t('S3b: a join order is not filled by less than its queue plus one, by '
  'the other side\'s prints, or by a print through it that no quote '
  'confirms; an interruption marks its row, empties the book and '
  'spoils the deep window',
  c['fb'][G + 5] == -1.0 and c['fs'][G + 5] == -1.0 and
  c['lo'][G + 5] == 99.75 and c['lob'][G + 5] == 100.00 and
  c['gap'][G + 8] == 0.0 and c['gap'][G + 9] == 1.0 and
  c['v'][G + 9] == 0.0 and c['v'][G + 10] == 0.0 and
  c['v'][G + 11] == 1.0 and c['gap'][G + 12] == 1.0 and
  c['lo'][G + 11] == 0.0 and c['lob'][G + 11] == 0.0 and
  c['fb'][G + 11] == -1.0 and c['v'][G + 12] == 0.0 and
  c['gap'][G + 4] == 0.0 and c['gap'][G + 5] == 0.0)

# the micro contract keeps no execution columns
mb = W.Book(SES, False)
mb.quote(T - 3.0, 100.00, 9, 100.25, 7)
mb.trade(T - 2.5, 100.25, 3, 1)
mb.quote(T - 0.4, 100.25, 2, 100.50, 4)
mb.finish()
t('S3c: the micro contract\'s rows hold the quote and the flows, and no '
  'execution columns; the volume counted is the panel\'s hours\'',
  sorted(mb.col) == sorted(W.COLS_MICRO) and mb.col['ofi'][G] == 9.0 and
  mb.col['buy'][G] == 3.0 and mb.col['v'][G] == 1.0 and
  mb.col['bid'][G] == 100.25 and mb.volume == 3.0 and bk.volume == 10.0
  and sorted(bk.col) == sorted(W.COLS))


# ---------------------------------------------------------------------
# recorder-format runs
# ---------------------------------------------------------------------
def iso(x):
    s = int(math.floor(x + 1e-9))
    return '%s.%07dZ' % (_dt.datetime.fromtimestamp(
        s, _dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'),
        int(round((x - s) * 1e7)))


def write_run(folder, inst, session, contract, events, run_no=1,
              depth=True):
    """events, in time order: ('Q', t, bid, bid size, ask, ask size[,
    flags]), ('T', t, price, size, side) with side BUY, SELL or '', or
    ('K', t, kind). One depth row, so the run declares its four files as
    the recorder does."""
    os.makedirs(folder, exist_ok=True)
    cid = 'syn%s%s' % (inst, session)
    rid = '%s-R%03d' % (cid, run_no)
    com = 'MLES-CAPTURE-1.2,%s,%s,1,%s,%s,%s,' % (cid, rid, session, inst,
                                                  contract)
    base = 'MLES12_%s_%s_%s_%s' % (inst, contract.replace(' ', '_'),
                                   session, rid)
    paths = {k: os.path.join(folder, base + '_%s.csv' % k)
             for k in AD.STREAMS}
    rows = {k: [','.join(AD.HEADERS[k])] for k in AD.STREAMS}
    seq, ss, t1 = [0], collections.Counter(), events[0][1]

    def row(k, stream, x, rest):
        seq[0] += 1
        ss[k] += 1
        rows[k].append(com + '%s,%d,%d,%s,%s,%d,%s' % (
            stream, seq[0], ss[k], iso(x), iso(x - 0.25),
            int((x - t1) * 1e7), rest))
    row('depth', 'DEPTH', t1, 'MBP,ADD,BID,0,100.00,5,')
    for e in events:
        if e[0] == 'Q':
            row('quotes', 'QUOTE', e[1], 'BID,%.2f,%d,%.2f,%d,%.2f,%d,%s' % (
                e[2], e[3], e[2], e[3], e[4], e[5],
                e[6] if len(e) > 6 else ''))
        elif e[0] == 'T':
            row('trades', 'TRADE', e[1], '%.2f,%d,%.2f,1,%.2f,1,,%s,'
                'QUOTE_TEST_v1,HIGH,' % (e[2], e[3], e[2] - 0.25, e[2],
                                         e[4]))
        else:
            row('quality', 'QUALITY', e[1], '%s,' % e[2])
    man = dict(schema='MLES-CAPTURE-1.2', captureInstanceId=cid, runId=rid,
               session=session, instrument=inst, contract=contract,
               firstRecvUtc=iso(t1), lastRecvUtc=iso(events[-1][1]),
               recorderBuild='1.2.2')
    for k in AD.STREAMS:
        with open(paths[k], 'w') as fh:
            fh.write('\n'.join(rows[k]) + '\n')
        man[k] = dict(present=True, file=os.path.basename(paths[k]),
                      bytes=os.path.getsize(paths[k]), rows=ss[k])
    if not depth:
        os.remove(paths['depth'])
        man['depth'] = dict(present=False)
    with open(os.path.join(folder, base + '_manifest.json'), 'w') as fh:
        json.dump(man, fh)
    return paths


def tape(session, seed, px0=20000.0, every=2.0, first=7 * 3600 + 3000,
         last=16 * 3600 + 1200, drift=None):
    """A session's tape: a quote every `every` seconds and a trade a
    second after each, a random walk on the tick; New York seconds of
    day from `first` to `last`. drift(sod, state) may push the walk."""
    rng = random.Random(seed)
    mid0 = W.panel_start(session) - W.PANEL_FROM
    ev, px = [('K', mid0 + first - 2, 'BOOK_RESYNC_START'),
              ('K', mid0 + first - 1, 'BOOK_READY')], px0
    s = float(first)
    while s < last:
        px += 0.25 * rng.choice((-2, -1, -1, 0, 0, 1, 1, 2))
        if drift is not None:
            px += drift(s, rng)
        px = round(px * 4) / 4.0
        bs, az = rng.randint(1, 9), rng.randint(1, 9)
        ev.append(('Q', mid0 + s, px, bs, px + 0.25, az))
        side = rng.choice(('BUY', 'SELL', 'BUY', 'SELL', ''))
        ev.append(('T', mid0 + s + 1.0, px + (0.25 if side == 'BUY' else
                                              0.0), rng.randint(1, 4),
                   side))
        s += every
    return ev


# ---------------------------------------------------------------------
# S4: the reader is the adapter's, inside the panel's hours
# ---------------------------------------------------------------------
f4 = os.path.join(WORK, 'cap4')
ev4 = tape(SES, 4, every=30.0)
p4 = write_run(f4, 'NQ', SES, 'NQ 12-26', ev4)
full = [e for e in AD.merge_run(p4, True) if e['stream'] != 'DEPTH']
lo4, hi4 = T0 + 3600.0, T0 + 7200.0
got = list(W.window_events(p4, lo4, hi4))
want = [e for e in full if _dt.datetime.fromtimestamp(
    int(lo4), _dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S') <=
    iso(e['t_recv'])[:19] <= _dt.datetime.fromtimestamp(
        int(hi4 + 1), _dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')]
bad_cols = dict(p4)
bad_cols['trades'] = os.path.join(f4, 'bad_trades.csv')
lines = open(p4['trades']).read().split('\n')
lines[5] = lines[5] + ',extra'
open(bad_cols['trades'], 'w').write('\n'.join(lines))
bad_num = dict(p4)
bad_num['quotes'] = os.path.join(f4, 'bad_quotes.csv')
lines = open(p4['quotes']).read().split('\n')
k_in = [i for i, ln in enumerate(lines)
        if ln and iso(lo4 + 600.0)[:16] in ln][0]
lines[k_in] = lines[k_in].replace(',BID,', ',BID,x', 1)
open(bad_num['quotes'], 'w').write('\n'.join(lines))
late = dict(p4)
late['quotes'] = os.path.join(f4, 'late_quotes.csv')
lines = open(p4['quotes']).read().split('\n')
lines[-2] = lines[-2].replace(',BID,', ',BID,x', 1)   # after the hours
open(late['quotes'], 'w').write('\n'.join(lines))
empty = dict(p4)
empty['quotes'] = os.path.join(f4, 'empty.csv')
open(empty['quotes'], 'w').close()
offs = dict(p4)                          # stamps with an offset, not a Z
for kind in ('quotes', 'trades'):
    offs[kind] = os.path.join(f4, 'offs_%s.csv' % kind)
    rows4 = list(csv.reader(open(p4[kind], newline='')))
    at4 = rows4[0].index('tRecvUtc')
    for r in rows4[1:]:
        hh = int(r[at4][11:13]) + 2      # the same moment, two hours east
        r[at4] = '%s%02d%s+02:00' % (r[at4][:11], hh, r[at4][13:-1])
    with open(offs[kind], 'w', newline='') as fh:
        csv.writer(fh).writerows(rows4)
got_offs = list(W.window_events(offs, lo4, hi4))
t('S4: inside the hours asked for, the rows are the adapter\'s own, in '
  'its order; a row of the wrong width or with a number that is not one '
  'raises the runner\'s CorruptStream; rows after the hours are not '
  'read; a stamp in another shape is taken by its value, not its text',
  got == want and len(got) > 200 and got[0]['t_recv'] >= lo4 and
  got[-1]['t_recv'] <= hi4 + 2 and
  {e['stream'] for e in got} == {'QUOTE', 'TRADE'} and
  stopped_with(lambda: list(W.window_events(bad_cols, lo4, hi4)),
               (RUN.CorruptStream,)) is not None and
  'expected 24 columns, got 25' in stopped_with(
      lambda: list(W.window_events(bad_cols, lo4, hi4)),
      (RUN.CorruptStream,)) and
  stopped_with(lambda: list(W.window_events(bad_num, lo4, hi4)),
               (RUN.CorruptStream,)) is not None and
  len(list(W.window_events(late, lo4, hi4))) == len(got) and
  [e['event_seq'] for e in got_offs] == [e['event_seq'] for e in got] and
  all(abs(a['t_recv'] - b['t_recv']) < 1e-5
      for a, b in zip(got_offs, got)) and
  'is empty' in stopped_with(
      lambda: list(W.window_events(empty, lo4, hi4)),
      (RUN.CorruptStream,)))



# ---------------------------------------------------------------------
# S5: which sessions are read, and how a session becomes a panel
# ---------------------------------------------------------------------
def ledger_file(name, sessions):
    path = os.path.join(WORK, name)
    with open(path, 'w') as fh:
        json.dump(dict(label='EXPOSED_PILOT_DEV', exposed_days=[
            dict(session=x, label='EXPOSED_PILOT_DEV') for x in sessions]),
            fh)
    return path


cap5 = os.path.join(WORK, 'cap5')
led5 = ledger_file('led5.json', ['20260831', '20260901', '20260902'])
ev_a = tape('20260901', 51, every=20.0)
write_run(cap5, 'NQ', '20260901', 'NQ 12-26', ev_a)
write_run(cap5, 'NQ', '20260901', 'NQ 03-27',                  # the back month
          tape('20260901', 52, every=600.0, px0=20200.0), run_no=2)
write_run(cap5, 'MNQ', '20260901', 'MNQ 12-26',
          tape('20260901', 53, every=20.0))
# 2026-09-02: two runs with a break between them, and one that ended
# before the panel's hours; its depth file is declared and absent
ev_b1 = tape('20260902', 54, every=20.0, last=11 * 3600)
ev_b2 = tape('20260902', 55, every=20.0, first=11 * 3600 + 1800)
write_run(cap5, 'NQ', '20260902', 'NQ 12-26',
          tape('20260902', 56, every=300.0, first=1 * 3600, last=3 * 3600),
          run_no=1)
p_b1 = write_run(cap5, 'NQ', '20260902', 'NQ 12-26', ev_b1, run_no=2)
os.remove(p_b1['depth'])
write_run(cap5, 'NQ', '20260902', 'NQ 12-26', ev_b2, run_no=3)
# its micro contract has a row that cannot be decoded: the run is set aside
p_m = write_run(cap5, 'MNQ', '20260902', 'MNQ 12-26',
                tape('20260902', 57, every=20.0))
lines = open(p_m['quotes']).read().split('\n')
mid_line = len(lines) // 2
lines[mid_line] = lines[mid_line].replace(',BID,', ',BID,x', 1)
open(p_m['quotes'], 'w').write('\n'.join(lines))
man_m = [f for f in os.listdir(cap5) if f.startswith('MLES12_MNQ_MNQ_12-26'
                                                     '_20260902')
         and f.endswith('manifest.json')][0]
mm = json.load(open(os.path.join(cap5, man_m)))
mm['quotes']['bytes'] = os.path.getsize(p_m['quotes'])
json.dump(mm, open(os.path.join(cap5, man_m), 'w'))
# sessions that may not be read
for ses, seed in (('20260831', 58), ('20260903', 59), ('20261116', 60),
                  ('20261117', 61)):
    write_run(cap5, 'NQ', ses, 'NQ 12-26', tape(ses, seed, every=60.0))
said5 = []
pan5 = W.read_capture(cap5, led5, said5.append)
direct = W.Book('20260901', True)
direct.broken = True
t_to5 = W.row_time('20260901', W.ROWS - 1) + W.TAIL_S
for e in ev_a:                   # the rows the reader takes, and no more
    if not (int(direct.t0 - W.STEP - W.WARMUP_S) <= int(e[1]) <=
            int(t_to5 + 1.0)):
        continue
    if e[0] == 'Q':
        direct.quote(e[1], e[2], e[3], e[4], e[5])
    elif e[0] == 'T':
        direct.trade(e[1], e[2], e[3], {'BUY': 1, 'SELL': -1, '': 0}[e[4]])
direct.finish()                  # the tape went on: no interruption
s1, s2 = pan5['sessions']['20260901'], pan5['sessions']['20260902']
g11 = W.row_of_sod(11 * 3600)
t('S5a: only the exposed sessions of 2026-09-01 to 2026-11-13 are opened; '
  'the others are listed; the panel from the files is the one the same '
  'tape gives directly; the front contract is the one with the volume',
  list(pan5['sessions']) == ['20260901', '20260902'] and
  pan5['refused_unread'] == ['20260831', '20260903', '20261116',
                             '20261117'] and
  not pan5['fresh'] and pan5['kind'] == W.PANEL_KIND and
  s1['nq'] == 'NQ 12-26' and s1['mnq'] == 'MNQ 12-26' and
  all(list(s1['cols'][c]) == list(direct.col[c]) for c in W.COLS) and
  sum(s1['cols']['v']) > 1000 and sorted(s1['mcols']) ==
  sorted(W.COLS_MICRO) and sum(s1['mcols']['vol']) > 0 and
  not any('20260903' in x or '20261116' in x or '20260831' in x
          for x in said5) and
  'recordings of 2 sessions to read' in said5[0] and
  any(x.startswith('20260901 NQ 12-26 ') and ' rows in ' in x
      for x in said5) and
  pan5['latency_ms']['NQ']['p50'] in (249, 250))
t('S5b: a break between two runs leaves rows without a quote and a mark; '
  'a run that ended before the hours is not opened; a declared depth '
  'file that is absent stops nothing; a run with a row that cannot be '
  'decoded is set aside whole, and the session goes on without it',
  s2['cols']['v'][g11 - 6] == 1.0 and s2['cols']['v'][g11 - 2] == 0.0 and
  s2['cols']['v'][g11 + 4] == 0.0 and
  s2['cols']['v'][g11 + 360 + 6] == 1.0 and
  s2['cols']['gap'][g11 - 3] == 1.0 and
  s2['cols']['gap'][g11 + 361] == 1.0 and
  sum(s2['cols']['gap'][g11 - 60:g11 + 420]) == 2.0 and
  s2['cols']['lo'][W.ROWS - 1] > 0 and
  pan5['runs_outside_hours'] == 1 and s2['mnq'] is None and
  s2['mcols'] is None and len(pan5['runs_skipped']) == 1 and
  'corrupt' in pan5['runs_skipped'][0] and
  pan5['runs_skipped'][0]['instrument'] == 'MNQ' and
  any('SKIPPED' in x for x in said5))
fresh5 = W.read_capture(cap5, led5, fresh=True)
e_none = stopped_with(lambda: W.read_capture(
    cap5, ledger_file('led5b.json', ['20270104'])))
e_noled = stopped_with(lambda: W.read_capture(
    cap5, os.path.join(WORK, 'no_ledger.json')))
t('S5c: the confirmation read opens only sessions from 2026-11-16 that '
  'the ledger does not hold; a folder with nothing that may be read, and '
  'a missing ledger, stop',
  fresh5['fresh'] and list(fresh5['sessions']) == ['20261116', '20261117']
  and fresh5['refused_unread'] == ['20260831', '20260901', '20260902',
                                   '20260903'] and
  e_none is not None and 'none of them from 2026-09-01' in e_none and
  e_noled is not None and 'names no EXPOSED_PILOT_DEV session' in e_noled)

# ---------------------------------------------------------------------
# S6: the panel as a file
# ---------------------------------------------------------------------
pf = os.path.join(WORK, 'panel.csv.gz')
W.write_panel(pan5, pf)
back = W.read_panel(pf)
b1, b2 = back['sessions']['20260901'], back['sessions']['20260902']


def same_cols(x, y, names):
    for c in names:
        tol = 1e-3 if c in ('qi', 'spr', 'qt', 's1', 's2') else 0.0
        for u, v_ in zip(x[c], y[c]):
            if abs(u - v_) > tol * max(1.0, abs(v_)):
                return False
    return True


import gzip                                              # noqa: E402
with open(os.path.join(WORK, 'junk.csv.gz'), 'wb') as fh:
    fh.write(b'not a panel')
other = os.path.join(WORK, 'other.csv.gz')
with gzip.open(other, 'wt') as fh:
    fh.write('# ' + json.dumps(dict(kind=W.PANEL_KIND, version='OTHER'))
             + '\n')
pf2 = os.path.join(WORK, 'panel2.csv.gz')
W.write_panel(back, pf2)
t('S6: the panel is written whole and read back the same (prices, '
  'counts and squared moves exactly, the integrals to the millisecond), '
  'and the file read back and written again is the same file; what is '
  'not a panel of this version stops',
  gzip.open(pf2, 'rb').read() == gzip.open(pf, 'rb').read() and
  list(back['sessions']) == ['20260901', '20260902'] and
  same_cols(b1['cols'], s1['cols'], W.COLS) and
  same_cols(b1['mcols'], s1['mcols'], W.COLS_MICRO) and
  same_cols(b2['cols'], s2['cols'], W.COLS) and b2['mcols'] is None and
  (b1['nq'], b1['mnq'], b2['mnq']) == ('NQ 12-26', 'MNQ 12-26', None) and
  back['refused_unread'] == pan5['refused_unread'] and
  back['runs_outside_hours'] == 1 and back['fresh'] is False and
  list(b1['cols']['bid']) == list(s1['cols']['bid']) and
  list(b1['cols']['fb']) == list(s1['cols']['fb']) and
  not os.path.exists(pf + '.tmp') and
  'not a panel this version can read' in stopped_with(
      lambda: W.read_panel(os.path.join(WORK, 'junk.csv.gz'))) and
  'not a panel of' in stopped_with(lambda: W.read_panel(other)) and
  stopped_with(lambda: W.read_panel(os.path.join(WORK, 'none.gz')))
  is not None)



# ---------------------------------------------------------------------
# panels built here
# ---------------------------------------------------------------------
def blank_cols():
    c = {k: array.array('d', [0.0]) * W.ROWS for k in W.COLS}
    c['fb'] = array.array('d', [-1.0]) * W.ROWS
    c['fs'] = array.array('d', [-1.0]) * W.ROWS
    return c


def flat_session(shift_at=None):
    """A session every figure of which can be worked out by hand: the
    mid steps half a point up and down, row after row; `shift_at` lifts
    every row from there by two points."""
    c = blank_cols()
    m = {k: array.array('d', [0.0]) * W.ROWS for k in W.COLS_MICRO}
    for g in range(W.ROWS):
        bid = 20000.0 + 0.5 * (g % 2) + (
            2.0 if shift_at is not None and g >= shift_at else 0.0)
        c['v'][g] = 1.0
        c['bid'][g], c['ask'][g], c['bs'][g], c['az'][g] = bid, bid + 0.25, \
            6.0, 2.0
        for k in ('b05', 'b10'):
            c[k][g] = bid
        for k in ('a05', 'a10'):
            c[k][g] = bid + 0.25
        c['buy'][g], c['sell'][g], c['vol'][g] = 6.0, 2.0, 8.0
        c['nb'][g], c['ns'][g], c['ofi'][g] = 3.0, 1.0, 4.0
        c['ofi1'][g], c['tfi1'][g] = 1.0, 2.0
        c['qi'][g], c['qt'][g], c['spr'][g], c['s1'][g] = 2.5, 5.0, 5.0, 5.0
        c['sq'][g], c['sqn'][g], c['pv'][g] = 0.25, 5.0, 8.0 * 20000.375
        m['v'][g] = 1.0
        m['bid'][g], m['ask'][g] = bid + 0.25, bid + 0.5
        m['bs'][g], m['az'][g] = 3.0, 1.0
        m['buy'][g], m['sell'][g], m['vol'][g] = 9.0, 3.0, 12.0
        m['nb'][g], m['ns'][g], m['qt'][g] = 9.0, 3.0, 5.0
    return dict(nq='NQ 12-26', mnq='MNQ 12-26', cols=c, mcols=m)


def walk_session(seed, effect=0.0, vol=1.5, spike=0.0, micro=True):
    """A random walk on the tick. `effect`: the next 5 seconds move by
    that many points for a full imbalance of the hitting (a planted
    forecast). `spike`: on 1 row in 100 the tape prints that far beyond
    the path and comes straight back (a planted deep fill). A join order
    is filled when the next step goes against it."""
    rng = random.Random(seed)
    n = W.ROWS
    c = blank_cols()
    m = {k: array.array('d', [0.0]) * n for k in W.COLS_MICRO} if micro \
        else None
    px, imbs, imb = [20000.0] * (n + 1), [], 0.0
    for g in range(n):
        imb = 0.7 * imb + rng.gauss(0, 0.5)
        x = max(-1.0, min(1.0, imb))
        imbs.append(x)
        px[g + 1] = round((px[g] + rng.gauss(0, vol) + effect * x) * 4) / 4.0
    for g in range(n):
        bid, x, nxt = px[g], imbs[g], px[g + 1]
        tot = 20 + rng.randint(0, 20)
        buy = round(tot * (0.5 + 0.4 * x))
        c['v'][g] = 1.0
        c['bid'][g], c['ask'][g] = bid, bid + 0.25
        c['bs'][g], c['az'][g] = rng.randint(1, 9), rng.randint(1, 9)
        c['b05'][g] = c['b10'][g] = bid
        c['a05'][g] = c['a10'][g] = bid + 0.25
        c['buy'][g], c['sell'][g], c['vol'][g] = buy, tot - buy, tot
        c['nb'][g], c['ns'][g] = round(buy / 2.0), round((tot - buy) / 2.0)
        c['ofi'][g] = (2 * buy - tot) + rng.randint(-3, 3)
        c['ofi1'][g], c['tfi1'][g] = rng.randint(-3, 3), rng.randint(-3, 3)
        c['qi'][g] = 5.0 * (c['bs'][g] - c['az'][g]) / (c['bs'][g] +
                                                        c['az'][g])
        c['qt'][g] = c['spr'][g] = c['s1'][g] = 5.0
        d = px[g] - px[g - 1] if g else 0.0
        c['sq'][g], c['sqn'][g] = d * d, 5.0
        c['pv'][g] = tot * (bid + 0.125)
        lo, hi = min(bid, nxt), max(bid, nxt) + 0.25
        if spike and rng.random() < 0.01:
            if rng.random() < 0.5:
                lo -= spike
            else:
                hi += spike
        c['lo'][g] = c['lob'][g] = lo
        c['hi'][g] = c['hia'][g] = hi
        if nxt < bid:
            c['fb'][g] = 2000.0
        elif nxt > bid:
            c['fs'][g] = 2000.0
        if m is not None:
            m['v'][g] = 1.0
            m['bid'][g], m['ask'][g] = bid, bid + 0.25
            m['bs'][g], m['az'][g] = rng.randint(1, 30), rng.randint(1, 30)
            mb = max(0, min(3 * tot, round(3 * tot * (
                0.5 + 0.2 * x + rng.gauss(0, 0.1)))))
            m['buy'][g], m['sell'][g], m['vol'][g] = mb, 3 * tot - mb, \
                3 * tot
            m['nb'][g], m['ns'][g], m['qt'][g] = mb, 3 * tot - mb, 5.0
    return dict(nq='NQ 12-26', mnq='MNQ 12-26' if micro else None, cols=c,
                mcols=m)


def panel_of(n, seed, fresh=False, **kw):
    d = _dt.date(2026, 11, 16) if fresh else _dt.date(2026, 9, 1)
    ses, k = collections.OrderedDict(), 0
    while len(ses) < n:
        if d.weekday() < 5:
            ses[d.strftime('%Y%m%d')] = walk_session(seed * 1000 + k, **kw)
            k += 1
        d += _dt.timedelta(days=1)
    return dict(kind=W.PANEL_KIND, version=W.W29_VERSION, fresh=fresh,
                sessions=ses, refused_unread=[], runs=n,
                runs_outside_hours=0, runs_skipped=[],
                latency_ms={'NQ': dict(p50=250, p95=300, n=1000)})


# ---------------------------------------------------------------------
# A1: the 48 inputs and what is forecast, by hand; nothing from later
# ---------------------------------------------------------------------
SHIFT = 1300
fs_ = W.derive('20260901', flat_session(SHIFT))
i0 = fs_.pos[1200]                       # 09:40:00, an even row
f0 = {name: fs_.x[k][i0] for k, name in enumerate(W.FEATURES)}
sg = math.sqrt(0.05)
want0 = dict(
    r5=-0.5 / (sg * math.sqrt(5)), r30=0.0, r120=0.0, r600=0.0, r1800=0.0,
    o1=1.0 / (4 * math.sqrt(0.2)), o5=1.0, o30=24 / (4 * math.sqrt(6)),
    o120=96 / (4 * math.sqrt(24)), o600=5.0,
    t1=2.0 / (4 * math.sqrt(0.2)), t5=0.5, t30=0.5, t120=0.5, t600=0.5,
    c30=0.5, c120=0.5, c600=0.5, z120=0.0, q0=0.5, q5=0.5, q30=0.5,
    s0=1.0, srel=0.0, a30=0.0, v30=0.0, pday=-0.5,
    dvwap=-0.25 / (sg * math.sqrt(1800)), d600=-0.25 / (sg * math.sqrt(600)),
    mt5=0.5, mt30=0.5, mt120=0.5, mt600=0.5, mc120=0.5, mq0=0.5, x30=0.0,
    x120=0.0, x600=0.0, ma120=math.log(0.15), basis=1.0, u1=1.0, u2=0.0,
    r120u1=0.0, r120u2=0.0, t120u1=0.5, t120u2=0.0, r600v30=0.0,
    o30a30=0.0)
i_late = fs_.pos[W.row_of_sod(15 * 3600 + 600)]          # 15:10:00
y_at = {h: fs_.y[h][fs_.pos[SHIFT - 2]] for h in W.HORIZONS}
t('A1a: on a session worked out by hand, each of the 48 inputs at 09:40, '
  'sigma, the spread, and what followed at each horizon across a 2-point '
  'lift; the rows used are 09:35 to 15:55, and the outcome is unknown '
  'where h runs past 15:55',
  sorted(want0) == sorted(W.FEATURES) and
  all(near(f0[k], want0[k], 1e-9) for k in W.FEATURES) and
  near(fs_.sigma[i0], sg) and near(fs_.spread[i0], 0.25) and
  near(fs_.mid_at[i0], 20000.125) and fs_.n == 4561 and
  fs_.rows[0] == 1140 and fs_.rows[-1] == W.row_of_sod(15 * 3600 + 3300)
  and fs_.x[W.FEATURES.index('u2')][i_late] == 1.0 and
  fs_.x[W.FEATURES.index('u1')][i_late] == 0.0 and
  near(fs_.x[W.FEATURES.index('t120u2')][i_late], 0.5) and
  all(near(y_at[h], 2.0 / (sg * math.sqrt(h))) for h in W.HORIZONS) and
  all(near(fs_.move[h][fs_.pos[SHIFT - 2]], 2.0) for h in W.HORIZONS) and
  fs_.y[10][fs_.pos[SHIFT - 4]] == 0.0 and
  near(fs_.y[60][fs_.pos[SHIFT - 12]], 2.0 / (sg * math.sqrt(60))) and
  fs_.y[60][fs_.pos[SHIFT - 14]] == 0.0 and
  fs_.y[600][fs_.pos[W.row_of_sod(15 * 3600 + 2700)]] is not None and
  fs_.y[600][fs_.pos[W.row_of_sod(15 * 3600 + 2705)]] is None and
  fs_.y[10][-3] is not None and fs_.y[10][-2] is None)

base = walk_session(77)
before = W.derive('20260901', base)
CUT = 3000
later = walk_session(78)
mixed = dict(nq=base['nq'], mnq=base['mnq'],
             cols={k: array.array('d', list(base['cols'][k][:CUT + 1]) +
                                  list(later['cols'][k][CUT + 1:]))
                   for k in W.COLS},
             mcols={k: array.array('d', list(base['mcols'][k][:CUT + 1]) +
                                   list(later['mcols'][k][CUT + 1:]))
                    for k in W.COLS_MICRO})
after = W.derive('20260901', mixed)
upto = before.pos[CUT]
broken = walk_session(79)
broken['cols']['gap'][2000] = 1.0
for g in range(2500, 2510):
    broken['cols']['v'][g] = 0.0
bs_ = W.derive('20260901', broken)
thin = walk_session(80)
for g in range(1140, 1140 + 1700):
    thin['cols']['v'][g] = 0.0
t('A1b: nothing after a row changes that row\'s inputs, and nothing after '
  't + h changes what followed; an interruption costs the 600 seconds '
  'after it; a row without a quote is not used, and ends the outcome of '
  'the rows that look to it; a session with too few usable rows is not '
  'used',
  before.rows[:upto + 1] == after.rows[:upto + 1] and
  all(list(before.x[k][:upto + 1]) == list(after.x[k][:upto + 1])
      for k in range(W.K)) and
  before.sigma[:upto + 1] == after.sigma[:upto + 1] and
  all(before.y[h][:upto + 1 - h // 5] == after.y[h][:upto + 1 - h // 5]
      for h in W.HORIZONS) and
  before.y[60][upto - 6:upto + 1] != after.y[60][upto - 6:upto + 1] and
  list(before.x[0][upto + 1:upto + 50]) != list(after.x[0][upto + 1:upto + 50])
  and bs_.pos[1999] >= 0 and bs_.pos[2000] == -1 and bs_.pos[2119] == -1
  and bs_.pos[2120] >= 0 and bs_.pos[2505] == -1 and
  bs_.y[60][bs_.pos[2495]] is None and bs_.y[60][bs_.pos[2485]] is not None
  and bs_.y[60][bs_.pos[1995]] is None and
  bs_.y[60][bs_.pos[1985]] is not None and
  W.derive('20260901', thin) is None and before.n == 4561)

# ---------------------------------------------------------------------
# A2: the forecast's arithmetic, against the rows themselves
# ---------------------------------------------------------------------
ss = [W.derive('2026090%d' % (k + 1), walk_session(90 + k, effect=0.3))
      for k in range(4)]
H2 = 60
g2 = W.session_sums(ss[0])[H2]
known = [i for i in range(ss[0].n) if ss[0].y[H2][i] is not None]
rows2 = [[ss[0].x[k][i] for k in range(W.K)] for i in known]
y2 = [ss[0].y[H2][i] for i in known]
a_, b_ = W.FEATURES.index('t30'), W.FEATURES.index('o120')
model = W.fit(g2, 0.1)
pred2 = W.predict(model, ss[0])
res = [y - pred2[i] for i, y in zip(known, y2)]
n2 = float(len(known))
mean_a = sum(r[a_] for r in rows2) / n2
sd_a = math.sqrt(sum((r[a_] - mean_a) ** 2 for r in rows2) / n2)
# the ridge's own condition: the standardised input's covariance with
# what is left over equals the penalty times its standardised weight
lhs = sum((r[a_] - mean_a) / sd_a * e for r, e in zip(rows2, res)) / n2
all_sums = [W.session_sums(x) for x in ss]
cum = W._running(all_sums)
W_INNER, W.INNER = W.INNER, 1
lam3 = W.choose(cum[H2][2], W._plus(cum[H2][3], cum[H2][2], -1.0))
errs = {lam: W.sse(W.fit(cum[H2][2], lam), all_sums[2][H2])
        for lam in W.PENALTIES}
m3 = W.forecast_model(cum[H2], 3)
garbled = list(all_sums)
garbled[3] = W.session_sums(ss[0])           # the session itself, replaced
m3b = W.forecast_model(W._running(garbled)[H2], 3)
W.INNER = W_INNER
i7 = 1234
t('A2: the sums are the rows\' own; the fitted forecast meets the ridge\'s '
  'own condition and leaves no average error; its squared error from the '
  'sums is the rows\'; the penalty chosen is the one that forecasts the '
  'last sessions best; a session\'s forecast does not depend on that '
  'session',
  g2['n'] == n2 and near(g2['sy'], sum(y2), 1e-9) and
  near(g2['sx'][a_], sum(r[a_] for r in rows2), 1e-9) and
  near(g2['sxx'][a_][b_], sum(r[a_] * r[b_] for r in rows2), 1e-9) and
  near(g2['sxx'][b_][a_], g2['sxx'][a_][b_]) and
  near(g2['sxy'][b_], sum(r[b_] * y for r, y in zip(rows2, y2)), 1e-9) and
  near(g2['syy'], sum(y * y for y in y2), 1e-9) and
  abs(sum(res)) < 1e-6 * n2 and
  near(lhs, 0.1 * model['w'][a_] * sd_a, 1e-6) and
  near(W.sse(model, g2), sum(e * e for e in res), 1e-7) and
  near(pred2[i7], model['c'] + sum(model['w'][k] * ss[0].x[k][i7]
                                   for k in range(W.K)), 1e-12) and
  lam3 == min(errs, key=lambda k: (errs[k], -k)) and m3['lam'] == lam3 and
  m3['w'] == W.fit(cum[H2][3], lam3)['w'] and m3['w'] == m3b['w'] and
  m3['n'] == cum[H2][3]['n'] and
  model['w'][W.FEATURES.index('u2')] != 0.0 and
  W.solve([[2.0, 1.0], [1.0, 3.0]], [3.0, 5.0]) == [0.8, 1.4] and
  stopped_with(lambda: W.solve([[1.0, 1.0], [1.0, 1.0]], [1.0, 2.0]))
  is not None)


# ---------------------------------------------------------------------
# A3-A5: the three ways to trade, trade by trade
# ---------------------------------------------------------------------
def fake(rows, sigma=1.0, spread=0.25, mid=100.125):
    s = W.Session()
    s.name, s.c, s.rows = '20260901', blank_cols(), list(rows)
    s.n = len(rows)
    s.sigma = [sigma] * s.n
    s.spread = [spread] * s.n
    s.mid_at = [mid] * s.n
    return s


LATE = W.row_of_sod(15 * 3600 + 54 * 60 + 30)            # 15:54:30
s3 = fake([2000, 2005, 2012, 2030, 2040, 2050, 2062, 2063, LATE])
c3 = s3.c
p3 = [0.1, -0.2, -0.2, 0.05, 0.3, 0.3, -0.3, -0.3, 1.0]
c3['a05'][2000], c3['a10'][2000] = 100.25, 100.50
c3['b05'][2012], c3['b10'][2012] = 101.00, 100.75
c3['a05'][2024] = 100.00                 # its stress quote is missing
c3['a05'][2050] = 60.00                  # held to 2062, where no bid is
c3['b05'][2063], c3['b10'][2063] = 50.00, 49.75
c3['a05'][2075], c3['a10'][2075] = 49.00, 49.25
c3['a05'][LATE] = 10.0
tr3, void3 = W.run_take(s3, p3, 60)
t('A3: T takes when the forecast is larger than the spread plus the '
  'commission, at the quote half a second on, holds h and closes by '
  'taking; one position at a time; nothing after 15:55 less h; a missing '
  'quote at entry is no trade, at the close a trade left open',
  tr3 == [('20260901', 2000, 1, 0.5, 0.0),
          ('20260901', 2012, -1, 0.75, None),
          ('20260901', 2063, -1, 0.75, 0.25)] and void3 == 1)

s4 = fake([2000, 2013, 2014, 2015, 2031])
c4 = s4.c
p4_ = [0.1, -0.1, -0.1, -0.1, 0.1]
c4['b05'][2000], c4['fb'][2000] = 100.00, 3000.0
c4['b05'][2013], c4['b10'][2013] = 100.75, 100.50
c4['a05'][2013] = 101.00                 # joined, never filled
c4['a05'][2014], c4['fs'][2014] = 101.00, 100.0
c4['a05'][2015], c4['fs'][2015] = 101.25, 10400.0
c4['a05'][2030], c4['a10'][2030] = 100.25, 100.50
c4['b05'][2031], c4['fb'][2031] = 99.00, 10600.0     # filled too late
tr4, void4, placed4, filled4 = W.run_join(s4, p4_, 60)
t('A4: M joins when the forecast is larger than half the spread plus the '
  'commission; an order not filled within 10.5 seconds is no trade, and '
  'the next waits 10 seconds; a filled one is held h from its fill and '
  'closed by taking',
  tr4 == [('20260901', 2000, 1, 0.5, 0.25),
          ('20260901', 2015, -1, 0.75, 0.5)] and
  (void4, placed4, filled4) == (0, 4, 2))

s5 = fake([2000, 2001, 2002, 2003, 2013, 2014, 2016], sigma=0.5)
c5 = s5.c
for g in s5.rows:
    c5['b05'][g], c5['a05'][g] = 100.00, 100.25
c5['lo'][2000] = c5['lob'][2000] = 97.50             # through 97.75
c5['b05'][2013], c5['b10'][2013] = 99.00, 98.50
c5['hi'][2001], c5['hia'][2001] = 103.00, 102.50     # no quote through
c5['hi'][2002], c5['hia'][2002] = 103.00, 102.75
c5['a05'][2015], c5['a10'][2015] = 103.50, 103.75
c5['lo'][2003] = c5['lob'][2003] = 90.00             # the buy side is busy
c5['lo'][2013] = c5['lob'][2013] = 97.75             # at the price only
c5['b05'][2014] = 97.50                              # no longer away
c5['lo'][2014] = c5['lob'][2014] = 97.00
c5['lo'][2016] = c5['lob'][2016] = 97.50             # filled; no bid at 2029
tr5, void5 = W.run_deep(s5, 2, 60)
t('A5: D rests k sigma root 5 from the mid, at least a point, rounded '
  'away; it is filled only by a trade through its price that the quote '
  'confirms, and not when the market is already there; one position a '
  'side; held h from the end of its 5 seconds',
  W.deep_price(100.125, 0.5, 2, 1) == 97.75 and
  W.deep_price(100.125, 0.5, 2, -1) == 102.50 and
  W.deep_price(100.125, 0.1, 2, 1) == 99.00 and
  W.deep_price(100.125, 0.1, 2, -1) == 101.25 and
  W.deep_price(100.0, 0.5, 4, 1) == 95.50 and
  tr5 == [('20260901', 2000, 1, 1.0, 0.5),
          ('20260901', 2002, -1, -1.25, -1.5)] and void5 == 1)

# ---------------------------------------------------------------------
# A6: the statistics and the bar
# ---------------------------------------------------------------------
tr6 = [('a', 1, 1, 1.0, 0.5), ('a', 2, 1, 2.0, None), ('b', 3, -1, -1.0, -1.5),
       ('d', 4, 1, 4.0, 3.0)]
st6 = W.summarize(tr6, ['a', 'b', 'c', 'd'], void=2)
t6 = 1.5 / (math.sqrt(17.0 / 3.0) / 2.0)
good = dict(trades=200, session_mean=0.1, t=3.0, first_half=1.0,
            second_half=0.5, net_stress=0.01)
pooled6 = W.pooled([(1.0, 4.0, 9.0), None, (-2.0, 1.0, 1.0),
                    (3.0, 4.0, 4.0)])
t('A6: a way\'s trades, net, net as MNQ, the session sums\' t, the halves '
  'and the stress; a way qualifies only at 60 seconds, 200 trades, t of '
  '3.0, both halves above zero and the stress above zero; the pooled '
  'correlation and its t',
  st6['trades'] == 4 and st6['void'] == 2 and st6['sessions'] == 4 and
  st6['per_session'] == 1.0 and st6['net'] == 1.5 and
  st6['net_micro'] == 1.0 and st6['won'] == 0.75 and
  st6['session_mean'] == 1.5 and near(st6['t'], round(t6, 3)) and
  st6['first_half'] == 2.0 and st6['second_half'] == 4.0 and
  near(st6['net_stress'], round(2.0 / 3.0, 4)) and
  W.qualifies(good, 60) and not W.qualifies(good, 30) and
  not W.qualifies(dict(good, trades=199), 60) and
  not W.qualifies(dict(good, t=2.99), 60) and
  not W.qualifies(dict(good, t=None), 60) and
  not W.qualifies(dict(good, second_half=0.0), 60) and
  not W.qualifies(dict(good, first_half=-1.0), 60) and
  not W.qualifies(dict(good, net_stress=0.0), 60) and
  not W.qualifies(dict(good, net_stress=None), 60) and
  not W.qualifies(dict(good, session_mean=-0.1), 60) and
  W.qualifies(dict(good, trades=100, t=2.0, second_half=-9.0), 60, 2.0,
              100, halves=False) and
  W.summarize([], ['a', 'b'])['net'] is None and
  W.summarize([], ['a', 'b'])['t'] is None and
  W.session_t([1.0, 1.0, 1.0]) is None and W.session_t([1.0, 2.0]) is None
  and near(pooled6[0], round(2.0 / math.sqrt(9.0 * 14.0), 5)) and
  near(pooled6[1], round((2.0 / 3.0) / (math.sqrt(19.0 / 3.0) /
                                        math.sqrt(3.0)), 3)) and
  pooled6[2] == 3 and W.pooled([(1.0, 1.0, 1.0)])[0] is None)



# ---------------------------------------------------------------------
# A7: the whole study on panels with and without something in them
# ---------------------------------------------------------------------
REGISTERED = (W.TRAIN_MIN, W.INNER, W.CONFIRM_SESSIONS)
W.TRAIN_MIN, W.INNER = 8, 3              # small panels, for the suite
said7 = []
rep_e = W.analyze(panel_of(13, 1, effect=1.2), said7.append)
rep_n = W.analyze(panel_of(13, 2))
rep_s = W.analyze(panel_of(13, 3, spike=12.0, micro=False))
qe = {(q['style'], q['key']) for q in rep_e['qualified']}
ways_e = {w['style']: w for w in (rep_e['frozen'] or {}).get('ways', [])}
m60 = rep_e['map']['60']
txt_e, txt_n = W.text(rep_e), W.text(rep_n)
deep_ok = [k for k, st in rep_s['deep'].items() if st['qualifies']]
t('A7a: with a forecast planted in the tape, the forecast finds it on '
  'sessions it was not fitted on, T qualifies at a minute or more and is '
  'frozen with its fitted forecast, and nothing shorter than a minute '
  'can qualify however good',
  {('T', '60'), ('T', '120')} <= qe and
  all(int(k) >= 60 for _s, k in qe) and
  ways_e['T']['key'] == max(
      (k for s_, k in qe if s_ == 'T'),
      key=lambda k: rep_e['take'][k]['t']) and
  len(rep_e['frozen']['ways']) == 1 and
  not rep_e['take']['10']['qualifies'] and
  not rep_e['take']['30']['qualifies'] and
  rep_e['take']['10']['t'] > 3.0 and rep_e['take']['60']['t'] >= 3.0 and
  rep_e['take']['60']['trades'] >= 200 and
  m60['forecast'][0] > 0.05 and m60['forecast'][1] > 3.0 and
  m60['top_move'] > m60['cost'] and m60['move'] > 2.0 and
  m60['cost'] == 0.5 and
  rep_e['forecast_sessions'] == rep_e['sessions_used'][8:] and
  len(rep_e['sessions_used']) == 13 and 'T' in ways_e and
  ways_e['T']['model']['inputs'] == list(W.FEATURES) and
  len(ways_e['T']['model']['w']) == W.K and
  W.seal(rep_e['frozen'])['seal'] == rep_e['frozen']['seal'] and
  rep_e['frozen']['sessions'] == 13 and
  not any(st['qualifies'] for st in rep_e['join'].values()) and
  'QUALIFIES and is frozen: T %s' % ways_e['T']['key'] in txt_e and
  'QUALIFIES (not frozen: another of its kind has the higher t): T'
  in txt_e and
  'a pass here is not evidence' in txt_e and
  any('the forecast at 600 seconds' in x for x in said7))
t('A7b: with nothing in the tape nothing qualifies and nothing is frozen; '
  'with prints planted far beyond the path, D qualifies and T and M do '
  'not; a session without the micro contract is used all the same',
  rep_n['qualified'] == [] and rep_n['frozen'] is None and
  not any(st['qualifies'] for tab in ('take', 'join', 'deep')
          for st in rep_n[tab].values()) and
  'Nothing qualifies' in txt_n and 'THE MAP' in txt_n and
  'A JOIN ORDER WITH NO FORECAST' in txt_n and
  rep_n['join_alone']['share'] > 0.3 and
  rep_n['join_alone']['after']['60'][0] < 0 and
  rep_n['spread']['one_tick'] == 1.0 and rep_n['micro_sessions'] == 13 and
  len(deep_ok) >= 1 and all(int(k.split('/')[1]) >= 60 for k in deep_ok)
  and sorted(q['key'] for q in rep_s['qualified']) == sorted(deep_ok)
  and {q['style'] for q in rep_s['qualified']} == {'D'} and
  len(rep_s['frozen']['ways']) == 1 and
  rep_s['frozen']['ways'][0]['key'] == max(
      deep_ok, key=lambda k: rep_s['deep'][k]['t']) and
  rep_s['frozen']['ways'][0]['style'] == 'D' and
  rep_s['frozen']['ways'][0]['k'] in W.DEEP_K and
  'model' not in rep_s['frozen']['ways'][0] and
  rep_s['micro_sessions'] == 0 and
  stopped_with(lambda: W.analyze(panel_of(8, 4))) is not None and
  'only 8 used sessions' in stopped_with(lambda: W.analyze(panel_of(8, 4))))

# ---------------------------------------------------------------------
# A8: the confirmation
# ---------------------------------------------------------------------
W.CONFIRM_SESSIONS = 6
fresh_e = panel_of(7, 5, fresh=True, effect=1.2)
fresh_n = panel_of(7, 6, fresh=True)
con_e = W.confirm(fresh_e, rep_e['frozen'])
con_n = W.confirm(fresh_n, rep_e['frozen'])
con_d = W.confirm(panel_of(7, 7, fresh=True, spike=12.0), rep_s['frozen'])
tampered = json.loads(json.dumps(rep_e['frozen']))
tampered['ways'][0]['h'] = 300
other_inputs = json.loads(json.dumps(rep_e['frozen']))
other_inputs['ways'][0]['model']['inputs'][0] = 'something'
other_inputs = W.seal(other_inputs)
W.CONFIRM_SESSIONS = 20
e_few8 = stopped_with(lambda: W.confirm(fresh_e, rep_e['frozen']))
W.CONFIRM_SESSIONS = 6
t('A8: the frozen ways alone are run on the fresh sessions, with nothing '
  'fitted: what is still there is CONFIRMED (100 trades, t of 2.0, above '
  'zero at the stress), what is not is dropped; too few sessions, a file '
  'changed after it was frozen, the exposed sessions, and a fresh panel '
  'given to the study all stop',
  con_e['part'] == 'confirm' and
  con_e['confirmed'] == ['T ' + ways_e['T']['key']] and
  con_e['ways'][0]['confirmed'] and con_e['ways'][0]['trades'] >= 100 and
  con_e['ways'][0]['t'] >= 2.0 and con_e['seal'] == rep_e['frozen']['seal']
  and con_n['confirmed'] == [] and not con_n['ways'][0]['confirmed'] and
  [w['style'] for w in con_d['ways']] == ['D'] and
  con_d['confirmed'] == ['D ' + rep_s['frozen']['ways'][0]['key']] and
  'THE CONFIRMATION' in W.text(con_e) and
  'CONFIRMED: T ' + ways_e['T']['key'] in W.text(con_e) and
  'CONFIRMED: nothing' in W.text(con_n) and
  e_few8 is not None and 'only 7 used sessions from 2026-11-16' in e_few8
  and 'changed after it was frozen' in stopped_with(
      lambda: W.confirm(fresh_e, tampered)) and
  'other inputs' in stopped_with(
      lambda: W.confirm(fresh_e, other_inputs)) and
  'from 2026-11-16 only' in stopped_with(
      lambda: W.confirm(panel_of(7, 8), rep_e['frozen'])) and
  'holds the confirmation sessions' in stopped_with(
      lambda: W.analyze(fresh_e)) and
  stopped_with(lambda: W.confirm(fresh_e, dict(wave29='x'))) is not None)

# ---------------------------------------------------------------------
# A9: the command, from recorder-format runs to the report
# ---------------------------------------------------------------------
cap9 = os.path.join(WORK, 'cap9')
dev9 = ['202609%02d' % d for d in (1, 2, 3, 4, 8, 9, 10, 11, 14)]
fresh9 = ['20261116', '20261117', '20261118']
for k, ses in enumerate(dev9 + fresh9):
    write_run(cap9, 'NQ', ses, 'NQ 12-26', tape(ses, 900 + k, every=8.0))
    if k < 2 or ses in fresh9[:1]:
        write_run(cap9, 'MNQ', ses, 'MNQ 12-26',
                  tape(ses, 950 + k, every=8.0))
write_run(cap9, 'NQ', '20260915', 'NQ 12-26',            # not in the ledger
          tape('20260915', 990, every=120.0))
led9 = ledger_file('led9.json', dev9)
reads9 = os.path.join(WORK, 'reads9.json')
home_reads = os.path.join(HERE, W.READS_LEDGER)
home_before = open(home_reads, 'rb').read() \
    if os.path.exists(home_reads) else None
out9 = os.path.join(WORK, 'w29.json')
rc9, said9 = said_by(lambda: W.main([cap9, '--out', out9], ledger=led9,
                                    reads=reads9))
rep9 = json.load(open(out9))
panel9 = os.path.join(WORK, 'w29_panel.csv.gz')
out9b = os.path.join(WORK, 'again.json')
rc9b, said9b = said_by(lambda: W.main(['--from-panel', panel9, '--out',
                                       out9b], reads=reads9))
rep9b = json.load(open(out9b))
doc9 = json.load(open(reads9))
mem9 = W.read_capture(cap9, led9)['sessions']
file9 = W.read_panel(panel9)['sessions']
t('A9a: one command reads the exposed sessions, saves the panel, makes '
  'the report and records it; sessions the ledger does not hold are '
  'listed and never opened; from the saved panel the report is the same '
  'to the last digit; the file holds the squared moves exactly',
  rc9 == 0 and os.path.exists(panel9) and list(file9) == dev9 and
  all(list(file9[x]['cols'][c]) == list(mem9[x]['cols'][c])
      for x in dev9 for c in ('sq', 'sqn', 'pv', 'vol', 'bid', 'fb', 'lo'))
  and sum(1 for x in file9[dev9[0]]['cols']['sq'] if x > 0) > 1000 and
  rep9['sessions_used'] == dev9 and rep9['part'] == 'dev' and
  rep9['refused_unread'] == ['20260915'] + fresh9 and
  rep9['micro_sessions'] == 2 and rep9['forecast_sessions'] == dev9[8:]
  and set(rep9['map']) == {'10', '30', '60', '120', '300', '600'} and
  len(rep9['inputs']) == 48 and len(rep9['deep']) == 12 and
  rep9['latency_ms']['NQ']['p50'] in (249, 250) and
  rep9['qualified'] == [] and rep9['frozen'] is None and
  not os.path.exists(os.path.join(WORK, 'w29_frozen.json')) and
  'THE TAPE' in said9 and 'THE MAP' in said9 and 'THE VERDICT' in said9
  and 'never opened: 4 other session(s)' in said9 and
  'recorded (1 entries' in said9 and rc9b == 0 and rep9b == rep9 and
  said9b.replace(out9b, out9).replace('(2 entries', '(1 entries') == said9
  and [(r['part'], r['from_panel'], r['seal'], r['frozen'])
       for r in doc9['reads']] ==
  [('dev', False, None, []), ('dev', True, None, [])] and
  doc9['reads'][0]['sessions'] == 9 and
  not os.path.exists(os.path.join(WORK, 'again_panel.csv.gz')))

few9 = os.path.join(WORK, 'few.json')
rc_few, said_few = said_by(lambda: W.main(
    [cap9, '--out', few9], ledger=ledger_file('led9c.json', dev9[:3]),
    reads=reads9))
usage9 = [said_by(lambda a=a: W.main(a, ledger=led9, reads=reads9))
          for a in ([cap9],                                  # no --out
                    ['--from-panel', panel9, cap9, '--out', out9b],
                    [cap9, cap9, '--out', out9b],            # two folders
                    [cap9, '--out', out9b, '--faster'],      # not an option
                    [cap9, '--out'],                         # no value
                    [cap9, '--out', '--confirm'],
                    [cap9, '--out', out9b, '--out', out9b],
                    ['--out', out9b],                        # nothing to read
                    [])]
rc_w, said_w = said_by(lambda: W.main(
    [cap9, '--out', os.path.join(WORK, 'no', 'x.json')], ledger=led9,
    reads=reads9))
rc_nd, said_nd = said_by(lambda: W.main(
    [os.path.join(WORK, 'nothing_here'), '--out', few9], ledger=led9,
    reads=reads9))
rc_np, said_np = said_by(lambda: W.main(
    ['--from-panel', os.path.join(WORK, 'junk.csv.gz'), '--out', few9],
    reads=reads9))
t('A9b: the panel is saved before anything is computed from it, so a '
  'stop in the study does not cost the read; a command line that is not '
  'one of the four, a report that cannot be written, a folder that is '
  'not there or a file that is not a panel: nothing is read or recorded',
  rc_few == 2 and 'only 3 used sessions' in said_few and
  os.path.exists(os.path.join(WORK, 'few_panel.csv.gz')) and
  not os.path.exists(few9) and
  list(W.read_panel(os.path.join(WORK, 'few_panel.csv.gz'))['sessions'])
  == dev9[:3] and
  all(rc == 2 and 'mrofyt_speed29.py "<capture>" --out w29.json' in said
      and 'THE MAP' not in said for rc, said in usage9) and
  rc_w == 2 and 'cannot be written' in said_w and
  rc_nd == 2 and 'STOPPED' in said_nd and
  rc_np == 2 and 'not a panel this version can read' in said_np and
  len(json.load(open(reads9))['reads']) == 2)


def confirm9(*a):
    return said_by(lambda: W.main(list(a), ledger=led9, reads=reads9))


fz9 = os.path.join(WORK, 'w29_frozen.json')
frozen9 = W.seal(dict(wave29=W.W29_VERSION, frozen_on=dev9[-1], sessions=9,
                      ways=[dict(style='D', key='2/60', t=3.5, k=2, h=60)]))
json.dump(frozen9, open(fz9, 'w'))
other9 = os.path.join(WORK, 'other_frozen.json')         # whole, not ours
json.dump(W.seal(dict(frozen9, ways=[dict(style='D', key='3/60', t=3.5,
                                          k=3, h=60)])), open(other9, 'w'))
bad9 = os.path.join(WORK, 'bad_frozen.json')             # changed by hand
json.dump(dict(frozen9, sessions=10), open(bad9, 'w'))
out9c = os.path.join(WORK, 'confirm.json')
cpanel9 = os.path.join(WORK, 'confirm_panel.csv.gz')
W.CONFIRM_SESSIONS = 3
rc_s0, said_s0 = confirm9(cap9, '--confirm', fz9, '--out', out9c)
rc_s2, said_s2 = said_by(lambda: W.main(
    [cap9, '--confirm', fz9, '--out', out9c], ledger=led9,
    reads=os.path.join(WORK, 'reads_none.json')))
# the study, as the command records it when it freezes this way
W.record(dict(part='dev', sessions=9, from_panel=True,
              qualified=['D 2/60'], frozen=['D 2/60'],
              seal=frozen9['seal']), reads9)
rc_s1, said_s1 = confirm9(cap9, '--confirm', other9, '--out', out9c)
rc_c1, said_c1 = confirm9(cap9, '--confirm', bad9, '--out', out9c)
rc_c2, said_c2 = confirm9(cap9, '--confirm',
                          os.path.join(WORK, 'none.json'), '--out', out9c)
W.CONFIRM_SESSIONS = 20
rc_c0, said_c0 = confirm9(cap9, '--confirm', fz9, '--out', out9c)
rc_a0, said_a0 = confirm9('--from-panel', panel9, '--confirm', fz9,
                          '--out', out9c)
open_still = not W.confirm_made(reads9) and not os.path.exists(out9c) \
    and not os.path.exists(cpanel9)
W.CONFIRM_SESSIONS = 3
rc_c3, said_c3 = confirm9(cap9, '--confirm', fz9, '--out', out9c)
con9 = json.load(open(out9c))
rc_c4, said_c4 = confirm9(cap9, '--confirm', fz9, '--out', out9c)
rc_c5, said_c5 = said_by(lambda: W.main(
    ['--from-panel', cpanel9, '--out', out9b], reads=reads9))
out9d = os.path.join(WORK, 'confirm_again.json')
rc_a1, said_a1 = confirm9('--from-panel', cpanel9, '--confirm', fz9,
                          '--out', out9d)
rc_a2, said_a2 = confirm9('--from-panel', cpanel9, '--confirm', other9,
                          '--out', out9d)
rc_a3, said_a3 = confirm9('--from-panel', panel9, '--confirm', fz9,
                          '--out', out9d)
doc9c = json.load(open(reads9))
home_after = open(home_reads, 'rb').read() \
    if os.path.exists(home_reads) else None
t('A9c: the confirmation takes only the frozen file the study on record '
  'wrote, reads only the sessions from 2026-11-16, saves their panel, '
  'runs the frozen ways and is recorded before it is shown; it is made '
  'once; with too few sessions, another or a changed frozen file, or no '
  'study on record, it stops with nothing read or recorded',
  rc_s0 == 2 and 'the study on record froze nothing' in said_s0 and
  rc_s2 == 2 and 'holds no study' in said_s2 and
  not os.path.exists(os.path.join(WORK, 'reads_none.json')) and
  rc_s1 == 2 and 'the study on record froze another' in said_s1 and
  rc_c1 == 2 and 'changed after it was frozen' in said_c1 and
  rc_c2 == 2 and 'cannot be read' in said_c2 and
  rc_c0 == 2 and 'only 3 used sessions from 2026-11-16' in said_c0 and
  rc_a0 == 2 and 'has not been made' in said_a0 and open_still and
  rc_c3 == 0 and 'THE CONFIRMATION' in said_c3 and
  'recorded (4 entries' in said_c3 and os.path.exists(cpanel9) and
  con9['part'] == 'confirm' and con9['sessions_used'] == fresh9 and
  con9['refused_unread'] == dev9 + ['20260915'] and
  con9['micro_sessions'] == 1 and
  con9['ways'][0]['key'] == '2/60' and con9['seal'] == frozen9['seal'] and
  list(W.read_panel(cpanel9)['sessions']) == fresh9 and
  W.read_panel(cpanel9)['fresh'] is True and
  doc9c['reads'][3]['part'] == 'confirm' and
  doc9c['reads'][3]['sessions'] == fresh9 and
  doc9c['reads'][3]['seal'] == frozen9['seal'] and
  doc9c['reads'][3]['confirmed'] == [] and
  rc_c4 == 2 and 'REFUSED' in said_c4 and 'made once' in said_c4 and
  rc_c5 == 2 and 'holds the confirmation sessions' in said_c5)
t('A9d: once made, the confirmation\'s report can be made again from its '
  'own saved panel with the same frozen file, and is the same; not with '
  'another frozen file, and not from another panel; the real ledger is '
  'untouched',
  rc_a1 == 0 and json.load(open(out9d)) == con9 and
  said_a1.replace(out9d, out9c).replace('(5 entries', '(4 entries')
  == said_c3 and
  rc_a2 == 2 and 'another frozen file' in said_a2 and
  rc_a3 == 2 and 'from 2026-11-16 only' in said_a3 and
  [r['part'] for r in doc9c['reads']] ==
  ['dev', 'dev', 'dev', 'confirm', 'confirm-again'] and
  home_after == home_before)

W.TRAIN_MIN, W.INNER, W.CONFIRM_SESSIONS = REGISTERED

# ---------------------------------------------------------------------
# A10: the numbers are the registration's
# ---------------------------------------------------------------------
t('A10: the inputs, horizons, penalties, the walk forward, the three '
  'ways, the bar and the confirmation are the registration\'s',
  W.K == 48 == len(set(W.FEATURES)) and W.HORIZONS == (10, 30, 60, 120,
                                                       300, 600) and
  W.PENALTIES == (0.01, 0.1, 1.0) and REGISTERED == (20, 5, 20) and
  W.SIGMA_S == 600 and W.USABLE_MIN == 3000 and W.CLIP == 5.0 and
  (W.ENTRY_FROM, W.ENTRY_TO) == (9 * 3600 + 2100, 15 * 3600 + 3300) and
  W.DEEP_K == (2, 3, 4) and W.DEEP_H == (30, 60, 120, 300) and
  W.DEEP_MIN == 1.0 and W.QUALIFY_H == 60 and W.QUALIFY_TRADES == 200 and
  W.QUALIFY_T == 3.0 and W.CONFIRM_TRADES == 100 and W.CONFIRM_T == 2.0
  and sum(1 for h in W.HORIZONS if h >= W.QUALIFY_H) * 2 +
  len(W.DEEP_K) * sum(1 for h in W.DEEP_H if h >= W.QUALIFY_H) == 17 and
  all(x in REG for x in (
      '**10, 30, 60, 120, 300 and 600 seconds**', '(48 inputs, all known '
      'at t)', 'from the 21st used session on', 'The penalty is one of '
      '0.01, 0.1 and 1', 'all but the last five of the earlier sessions',
      'Rows from 09:35:00 to 15:55:00 less h',
      'larger than the spread at t plus the commission',
      'larger than half the spread plus the commission',
      'the next may be placed 10 seconds after it', 'k = **2, 3, 4**',
      'h = **30, 60, 120, 300** seconds', 'never nearer than 1 point',
      'h is **60 seconds or more**', '**200 trades or more**',
      '**t of 3.0 or more**', 'still above 0 with the 1.0 s delay',
      'Seventeen ways can qualify', 'at least 20 used sessions',
      'it makes 100 trades or more', 't of 2.0 or more',
      'at least 3,000 of its rows from 09:35 to 15:55 are usable',
      'over the 600 seconds to t', 'held between \u22125 and +5',
      'Explicitly NOT registered', 'Expected beforehand')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
