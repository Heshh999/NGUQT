#!/usr/bin/env python3
# MROF-YT-W25C-TRADECOST-1.0 suite. The clock, the quote in force, the
# first trade through a price and the two rules' executions are
# exercised on hand-built objects; the whole measurement end to end on
# recorder-format runs written here with known spreads, sizes and slips
# (thirty sessions across a contract roll and the November clock
# change, sessions that must stay unopened, a missing depth file, a
# damaged run and a run that breaks mid-read). Synthetic data verifies
# CODE BEHAVIOR only, never market evidence. No order, fill or P&L
# exists.
import collections
import datetime as _dt
import io
import json
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mles_v12_adapter as AD        # noqa: E402
import mrofyt_runner as RUN          # noqa: E402
import mrofyt_screen15 as S          # noqa: E402
import mrofyt_tradecost as TC        # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


def near(a, b, tol=1e-9):
    return a is not None and abs(a - b) <= tol


WORK = tempfile.mkdtemp(prefix='mrofyt_w25c_')
N = S.N_MIN
EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)
REG = ' '.join(open(os.path.join(HERE, TC.REGISTRATION),
                    encoding='utf-8').read().split())


def utc(y, mo, d, h=0, mi=0):
    return (_dt.datetime(y, mo, d, h, mi, tzinfo=_dt.timezone.utc)
            - EPOCH).total_seconds()


def t0930(session):
    """09:30 New York on the session date, by the runner's own clock."""
    y, mo, d = int(session[:4]), int(session[4:6]), int(session[6:])
    return utc(y, mo, d) + 34200 - RUN.et_offset(utc(y, mo, d, 16))


# ---------------------------------------------------------------------
# K1: the clock and the bars
# ---------------------------------------------------------------------
acc_s, acc_w = TC.Acc('20260902'), TC.Acc('20261104')
ts, tw = utc(2026, 9, 2, 13, 30), utc(2026, 11, 4, 14, 30)
acc_s.trade(ts + 45, 100.0, 2, None)             # 09:30:45
acc_s.trade(ts + 50, 101.0, 3, None)
acc_s.trade(ts - 55500, 99.0, 1, None)           # 18:05 the evening before
st_s = TC.day_stats(acc_s)
t('K1: 09:30 New York is 13:30 UTC in summer and 14:30 after the November '
  'change, as on the runner\'s clock; a trade falls in its minute, the '
  'evening before included',
  acc_s.midnight + 34200 == ts and acc_w.midnight + 34200 == tw and
  t0930('20260902') == ts and t0930('20261104') == tw and
  RUN.et_parts(ts + 45) == ('20260902', 34245.0) and
  RUN.et_parts(tw + 45) == ('20261104', 34245.0) and
  RUN.session_id(ts - 55500) == '20260902' and
  acc_s.bars == {570: [100.0, 101.0, 100.0, 101.0, 5],
                 -355: [99.0, 99.0, 99.0, 99.0, 1]} and
  st_s['rth_n'] == 1 and st_s['rth_open'] == 100.0 and
  st_s['rth_close'] == 101.0 and st_s['rth_vol'] == 5 and
  st_s['on_high'] == 99.0 and list(st_s['bars'][:4]) ==
  [65100 - 86400, 99.0, 99.0, 99.0] and
  acc_s.lows == [] and acc_s.highs == [])

# ---------------------------------------------------------------------
# K2: the quote in force, the new lows and highs, the first touch
# ---------------------------------------------------------------------
q = (1000.0, 99.75, 4.0, 100.0, 6.0)
acc = TC.Acc('20260902')
t35 = ts + 300
acc.trade(t35 - 1, 100.0, 1, q)                  # 09:34:59: not yet
acc.trade(t35, 100.0, 1, None)                   # the first: low and high
acc.trade(t35 + 1, 100.0, 1, None)               # equal: neither
acc.trade(t35 + 2, 99.5, 1, None)
acc.trade(t35 + 3, 100.25, 1, None)
acc.trade(t35 + 4, 99.75, 1, None)               # above the low: neither
acc.trade(ts + 23400, 90.0, 1, None)             # 16:00:00: over
acc.lows[1][3] = (0.4, 99.25, 2.0, 99.5, 3.0)    # a quote 0.4 s after
acc.lows[1][2] = (99.5, 9.0, 99.75, 9.0)
acc.highs[1][3] = (3.0, 100.25, 1.0, 100.5, 1.0)  # too late to count
acc.highs[1][2] = (100.0, 7.0, 100.25, 8.0)
t('K2: a quote older than 10 seconds is no quote; from 09:35 to 16:00 '
  'every new low and new high is kept; the first trade at or through a '
  'price takes the quote that follows within a second, else the one in '
  'force',
  TC.quote_at(None, 5.0) is None and
  TC.quote_at(q, 1010.0) == (99.75, 4.0, 100.0, 6.0) and
  TC.quote_at(q, 1010.5) is None and
  [r[1] for r in acc.lows] == [100.0, 99.5] and
  [r[1] for r in acc.highs] == [100.0, 100.25] and len(acc.pending) == 4
  and TC.touch_quote(acc, True, 99.5) ==
  ((99.25, 2.0, 99.5, 3.0), 'next quote') and
  TC.touch_quote(acc, True, 99.75) ==
  ((99.25, 2.0, 99.5, 3.0), 'next quote') and
  TC.touch_quote(acc, False, 100.25) ==
  ((100.0, 7.0, 100.25, 8.0), 'in force') and
  TC.touch_quote(acc, True, 99.25) == (None, None) and
  TC.touch_quote(acc, False, 100.0) == (None, 'in force') and
  TC.spread((99.5, 9.0, 100.25, 9.0)) == 3.0 and
  TC.shown((99.5, 9.0, 100.25, 8.0), 1) == 8.0 and
  TC.shown((99.5, 9.0, 100.25, 8.0), -1) == 9.0)


# ---------------------------------------------------------------------
# K3: the executions are wave twenty-four's own
# ---------------------------------------------------------------------
def mk(session, o, pc, closes, highs=None, lows=None):
    c = list(closes) + [closes[-1]] * (N - len(closes))
    h = list(highs) + c[len(highs):] if highs else list(c)
    lo = list(lows) + c[len(lows):] if lows else list(c)
    return S.Day(session, 'NQ 12-26', o, pc, c, h, lo, [1.0] * N)


def flat(session, o, pc, marks):
    c, last = [], o
    for j in range(1, N + 1):
        last = marks.get(j, last)
        c.append(last)
    return mk(session, o, pc, c)


sig = [0.01] * (N + 1)
d_rev = flat('20210104', 100.0, 99.0, {31: 102.0, 151: 97.0})
d_two = flat('20210104', 100.0, 99.0, {1: 100.5, 31: 102.0, 61: 103.0,
                                      91: 100.8, 151: 97.0, 390: 96.0})
d_none = flat('20210104', 100.0, 99.0, {})
res = {k: (TC.b_changes(d, sig), S.day_b(d, sig))
       for k, d in (('rev', d_rev), ('two', d_two), ('none', d_none))}
d_long = mk('20210104', 100.0, 99.0, [100.5, 101.0, 101.5, 102.0, 102.0],
            lows=[99.0])
d_short = mk('20210104', 100.0, 99.0, [99.5, 99.0, 98.5, 98.0, 98.0],
             highs=[100.5])
t('K3: B\'s position changes are day_b\'s, step for step (a turn from '
  'long to short is two contracts at once); A\'s direction, stop and '
  'target are trade_a\'s',
  res['rev'][0] == [(60, 1), (180, -2), (390, 1)] and
  res['none'][0] == [] and
  all(len(ch) == out[2] and near(
      sum(abs(x) for _j, x in ch) * S.SIDE / 100.0, out[1])
      for ch, out in res.values()) and res['two'][1][2] == 4 and
  TC.a_parts(d_long) == (1, 99.0, 132.0) and
  TC.a_parts(d_short) == (-1, 100.5, 73.0))


# ---------------------------------------------------------------------
# recorder-format runs
# ---------------------------------------------------------------------
def iso(x):
    s = int(x)
    return '%s.%07dZ' % (_dt.datetime.fromtimestamp(
        s, _dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'),
        int(round((x - s) * 1e7)))


def write_run(folder, session, contract, events, run_no=1):
    """events, in time order: ('Q', t, bid, bid size, ask, ask size[,
    flags]), ('T', t, price, size) or ('K', t, kind). One depth row, so
    the run declares its four files as the recorder does."""
    os.makedirs(folder, exist_ok=True)
    cid = 'syn%s' % session
    rid = '%s-R%03d' % (cid, run_no)
    com = 'MLES-CAPTURE-1.2,%s,%s,1,%s,NQ,%s,' % (cid, rid, session,
                                                  contract)
    base = 'MLES12_NQ_%s_%s_%s' % (contract.replace(' ', '_'), session, rid)
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
            row('trades', 'TRADE', e[1], '%.2f,%d,%.2f,1,%.2f,1,,BUY,'
                'QUOTE_TEST_v1,HIGH,' % (e[2], e[3], e[2] - 0.25, e[2]))
        else:
            row('quality', 'QUALITY', e[1], '%s,' % e[2])
    man = dict(schema='MLES-CAPTURE-1.2', captureInstanceId=cid, runId=rid,
               session=session, instrument='NQ', contract=contract,
               firstRecvUtc=iso(t1), recorderBuild='1.2.2')
    for k in AD.STREAMS:
        with open(paths[k], 'w') as fh:
            fh.write('\n'.join(rows[k]) + '\n')
        man[k] = dict(present=True, file=os.path.basename(paths[k]),
                      bytes=os.path.getsize(paths[k]), rows=ss[k])
    with open(os.path.join(folder, base + '_manifest.json'), 'w') as fh:
        json.dump(man, fh)
    return paths


def session_events(session, path, quotes=None, extra=(), first=-60,
                   last=N):
    """One trade a minute at second 30, at path(minutes after 09:30),
    from `first` to `last`; before every whole minute of the cash
    session a quote two seconds earlier, one tick wide at the last
    price with 5 bid and 6 offered, unless `quotes` gives that minute
    another (None: none); a last quote five seconds after `last`."""
    t0 = t0930(session)
    quotes = quotes or {}
    ev = [('K', t0 + 60 * first - 5, 'BOOK_RESYNC_START'),
          ('K', t0 + 60 * first - 4, 'BOOK_READY')]
    for m in range(first, last):
        ev.append(('T', t0 + 60 * m + 30, path(m), 1))
    for j in range(max(first + 1, 0), last + 1):
        qq = quotes.get(j, 'usual')
        if qq is None:
            continue
        if qq == 'usual':
            qq = (path(j - 1), 5, path(j - 1) + 0.25, 6)
        ev.append(('Q', t0 + 60 * j - 2) + tuple(qq))
    ev.append(('Q', t0 + 60 * last + 5, path(last - 1), 1,
               path(last - 1) + 0.25, 1))
    ev += list(extra)
    ev.sort(key=lambda e: e[1])
    return ev


def weekdays(n, start=_dt.date(2026, 9, 1)):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.strftime('%Y%m%d'))
        d += _dt.timedelta(days=1)
    return out


def steps(marks, before):
    """path(m): `before` until the first mark, then the last mark at or
    before m."""
    keys = sorted(marks)

    def path(m):
        px = before
        for k in keys:
            if m >= k:
                px = marks[k]
        return px
    return path


CAP = os.path.join(WORK, 'capture')
DAYS = weekdays(28)                  # 2026-09-01 .. 2026-10-08
A1, A2, A3, A4, A5 = DAYS[14:19]
B1, B2 = '20261104', '20261105'      # after the clock change
up5 = {0: 20001.0, 1: 20002.0, 2: 20003.0, 3: 20004.0, 4: 20005.0}
plan = {}
for k, s in enumerate(DAYS):         # flat days: neither rule trades
    plan[s] = dict(path=steps({}, 20000.0 + 10.0 * (k % 3)))
# A1: long, out at the close; two ticks wide at 09:35, one at 16:00
plan[A1] = dict(path=steps({**up5, 5: 20006.0, 389: 20010.0}, 20000.0),
                quotes={5: (20004.75, 3, 20005.25, 7),
                        390: (20009.75, 9, 20010.0, 4)})
# A2: short, stopped at 19999; the ask a second later is 20000: 4 ticks
t2 = t0930(A2) + 60 * 20
plan[A2] = dict(path=steps({0: 19999.0, 1: 19998.0, 2: 19997.0, 3: 19996.0,
                            4: 19995.0, 5: 19996.0}, 20000.0),
                quotes={5: (19994.75, 8, 19995.0, 5)},
                extra=[('T', t2 + 40, 19999.5, 1),
                       ('Q', t2 + 40.4, 19999.75, 6, 20000.0, 2)])
# A3: long, target 20017; no quote within a second after: the one before
t3 = t0930(A3) + 60 * 50
plan[A3] = dict(path=steps({0: 20000.5, 1: 20001.0, 2: 20001.5, 3: 20002.0,
                            5: 20003.0}, 20000.0),
                extra=[('Q', t3 + 38, 20016.75, 10, 20017.25, 12),
                       ('T', t3 + 40, 20017.25, 1),
                       ('Q', t3 + 43, 20003.0, 1, 20003.25, 1)])
# A4: long, stopped at 20001 with the bid still there: no slip
t4 = t0930(A4) + 60 * 30
plan[A4] = dict(path=steps({**up5, 5: 20004.0}, 20000.0),
                extra=[('Q', t4 + 38, 20001.0, 4, 20001.25, 4),
                       ('T', t4 + 40, 20000.75, 1),
                       ('Q', t4 + 45, 20004.0, 1, 20004.25, 1)])
# A5: as A1, but the last quote before 09:35 is 20 seconds old
plan[A5] = dict(path=steps({**up5, 5: 20006.0, 389: 20010.0}, 20000.0),
                quotes={5: None},
                extra=[('Q', t0930(A5) + 280, 20004.0, 5, 20004.25, 6)])
# B1: out of the noise area by 10:00, long to the close
plan[B1] = dict(path=steps({20: 20100.0}, 20000.0),
                quotes={30: (20099.75, 2, 20100.5, 11),
                        390: (20099.75, 4, 20100.0, 9)})
# B2: long at 10:00, short from 13:00, flat at the close
plan[B2] = dict(path=steps({20: 20200.0, 185: 19900.0}, 20100.0),
                quotes={210: (19899.5, 7, 19900.0, 3)})
kept = {}
for k, s in enumerate(DAYS + [B1, B2]):
    kept[s] = write_run(
        CAP, s, 'NQ SEP26' if k < 5 else 'NQ DEC26',
        session_events(s, plan[s]['path'], plan[s].get('quotes'),
                       plan[s].get('extra', ())))
os.remove(kept[A1]['depth'])         # the depth file is never opened
# sessions that must stay unopened: before the first, after the last,
# and inside the dates but not marked in the ledger
for s in ('20260831', '20261112', '20261116'):
    write_run(CAP, s, 'NQ DEC26', session_events(s, steps({}, 20000.0)))
# a damaged run: its quote file is shorter than its manifest declares
bad = write_run(CAP, '20261110', 'NQ DEC26',
                session_events('20261110', steps({}, 20000.0)))
with open(bad['quotes'], 'r+') as fh:
    fh.truncate(os.path.getsize(bad['quotes']) - 40)
LED = os.path.join(WORK, 'exposed.json')
with open(LED, 'w') as fh:
    json.dump(dict(exposed_days=[
        dict(session=s, label='EXPOSED_PILOT_DEV')
        for s in DAYS + [B1, B2, '20260831', '20261110', '20261116']] + [
        dict(session='20261112', label='SOMETHING_ELSE')]), fh)

# ---------------------------------------------------------------------
# K4: section 2c end to end, A
# ---------------------------------------------------------------------
seen = []
rep = TC.run(CAP, LED, seen.append)
ra = {r['session']: r for r in rep['a_trades']}
a = rep['A']
t('K4: each A trade is measured where it really trades: the spread and '
  'the contracts on the side taken at 09:35, at the close, or at the '
  'first trade through the target or the stop, whose slip is the stop '
  'against the price a market order meets; the round trip is 0.25 of '
  'commission, half of each spread and the slip',
  sorted(ra) == [A1, A2, A3, A4, A5] and
  (ra[A1]['direction'], ra[A1]['how'], ra[A1]['entry_spread'],
   ra[A1]['entry_shown'], ra[A1]['exit_spread'], ra[A1]['exit_shown'],
   ra[A1]['exit_quote']) == (1, 'CLOSE', 2.0, 7.0, 1.0, 9.0, 'at 16:00')
  and near(ra[A1]['measured'], 0.625) and ra[A1]['assumed'] == 0.5 and
  'stop_slip' not in ra[A1] and
  (ra[A2]['direction'], ra[A2]['how'], ra[A2]['entry_spread'],
   ra[A2]['entry_shown'], ra[A2]['exit_spread'], ra[A2]['exit_shown'],
   ra[A2]['exit_quote'], ra[A2]['stop_slip']) ==
  (-1, 'STOP', 1.0, 8.0, 1.0, 2.0, 'next quote', 4.0) and
  near(ra[A2]['measured'], 1.5) and ra[A2]['assumed'] == 0.75 and
  (ra[A3]['direction'], ra[A3]['how'], ra[A3]['entry_spread'],
   ra[A3]['entry_shown'], ra[A3]['exit_spread'], ra[A3]['exit_shown'],
   ra[A3]['exit_quote']) == (1, 'TARGET', 1.0, 6.0, 2.0, 10.0, 'in force')
  and near(ra[A3]['measured'], 0.625) and
  (ra[A4]['how'], ra[A4]['exit_spread'], ra[A4]['exit_shown'],
   ra[A4]['exit_quote'], ra[A4]['stop_slip']) ==
  ('STOP', 1.0, 4.0, 'in force', 0.0) and
  near(ra[A4]['measured'], 0.5) and
  ra[A5]['how'] == 'CLOSE' and 'entry_spread' not in ra[A5] and
  'measured' not in ra[A5] and ra[A5]['exit_spread'] == 1.0 and
  a['trades'] == 5 and a['measured'] == 4 and
  a['exits'] == dict(CLOSE=2, STOP=2, TARGET=1) and
  a['entry_spread_ticks'] == dict(n=4, mean=1.25, median=1.0, p90=2.0,
                                  max=2.0) and
  a['exit_spread_ticks'] == dict(n=5, mean=1.2, median=1.0, p90=2.0,
                                 max=2.0) and
  a['stop_slip_ticks'] == dict(n=2, mean=2.0, median=2.0, p90=4.0,
                               max=4.0) and
  a['shown_contracts'] == dict(n=9, median=6.0, p10=2.0, min=2.0) and
  a['round_trip'] == dict(n=4, assumed=0.625, measured=0.8125, times=1.3)
  and a['on_a_stop'] == dict(n=2, assumed=0.75, measured=1.0, times=1.333)
  and a['otherwise'] == dict(n=2, assumed=0.5, measured=0.625, times=1.25)
  and a['status'] == 'WITHIN')

# ---------------------------------------------------------------------
# K5: section 2c end to end, B
# ---------------------------------------------------------------------
rb = collections.defaultdict(list)
for r in rep['b_changes']:
    rb[r['session']].append((r['minute'], r['contracts'], r.get('spread'),
                             r.get('shown')))
b = rep['B']
t('K5: each position change of B is measured at its half hour, a turn '
  'from long to short as two contracts; the round trip is 0.25 of '
  'commission and the average spread a contract; the days after the '
  'clock change are read at their own hour',
  dict(rb) == {B1: [(30, 1, 3.0, 11.0), (390, -1, 1.0, 4.0)],
               B2: [(30, 1, 1.0, 6.0), (210, -2, 2.0, 7.0),
                    (390, 1, 1.0, 6.0)]} and
  b['days'] == 2 and b['changes'] == 5 and b['contracts'] == 6 and
  b['measured_contracts'] == 6 and
  b['spread_ticks'] == dict(n=5, mean=1.6, median=1.0, p90=3.0, max=3.0)
  and b['shown_contracts'] == dict(n=5, median=6.0, p10=4.0, min=4.0) and
  b['round_trip'] == dict(n=6, assumed=0.5, measured=0.6667, times=1.333)
  and b['status'] == 'WITHIN')

# ---------------------------------------------------------------------
# K6: what is read and what is not
# ---------------------------------------------------------------------
t('K6: only sessions from 2026-09-01 to 2026-11-13 that the ledger marks '
  'EXPOSED_PILOT_DEV are opened; the depth file is not needed; a run '
  'whose file is shorter than declared is skipped and named; the day '
  'after the contract roll is no usable session',
  rep['refused_unread'] == ['20260831', '20261112', '20261116'] and
  rep['sessions_read'] == 30 and rep['first_session'] == DAYS[0] and
  rep['last_session'] == B2 and rep['runs'] == 31 and
  len(rep['runs_skipped']) == 1 and
  rep['runs_skipped'][0]['session'] == '20261110' and
  'truncated' in rep['runs_skipped'][0] and
  rep['trading_days'] == 30 and rep['usable_sessions'] == 16 and
  len(seen) == 31 and sum('SKIPPED' in x for x in seen) == 1 and
  not any(s in x for x in seen
          for s in ('20260831', '20261112', '20261116')) and
  any(x.startswith('%s NQ 09-26 ' % DAYS[0]) for x in seen) and
  any(x.startswith('%s NQ 12-26 ' % DAYS[5]) for x in seen) and
  rep['assumed'] == dict(round_trip=0.5, stop=0.75, commission=0.25))

# ---------------------------------------------------------------------
# K7: a run that breaks mid-read leaves nothing behind
# ---------------------------------------------------------------------
CAP2 = os.path.join(WORK, 'capture2')
flat_path = steps({0: 20001.0, 5: 20002.0, 200: 20050.0}, 20000.0)
write_run(CAP2, '20260902', 'NQ DEC26',
          session_events('20260902', flat_path, last=150), run_no=1)
p2 = write_run(CAP2, '20260902', 'NQ DEC26',
               session_events('20260902', flat_path, first=151), run_no=2)
txt = open(p2['trades']).read()
assert txt.count('20050.00,1,') > 100
head, tail = txt.rsplit('20050.00,1,', 1)
with open(p2['trades'], 'w') as fh:              # the same size, one
    fh.write(head + 'XXXXX.XX,1,' + tail)        # price unreadable
r7 = TC.CostRunner(CAP2, lambda s: True)
led7 = r7.run()
r7.finish()
acc7 = r7.done[('NQ 12-26', '20260902')]
r7b = TC.CostRunner(os.path.join(WORK, 'capture2b'), lambda s: True)
write_run(r7b.dir, '20260902', 'NQ DEC26',
          session_events('20260902', flat_path, last=150), run_no=1)
r7b.run()
r7b.finish()
acc7b = r7b.done[('NQ 12-26', '20260902')]
t('K7: a second run with an unreadable row is skipped whole and named, '
  'and the session holds exactly what the first run gave it: no bar, '
  'quote or new high of the broken run stays',
  len(led7['skipped_runs']) == 1 and
  'corrupt' in led7['skipped_runs'][0] and
  [x.get('skipped') for x in led7['runs']] == [None, 'CORRUPT_STREAM'] and
  acc7.bars == acc7b.bars and max(acc7.bars) == 570 + 149 and
  acc7.snap == acc7b.snap and acc7.next_j == acc7b.next_j == 151 and
  acc7.lows == acc7b.lows and acc7.highs == acc7b.highs and
  acc7.hi == 20002.0 and len(acc7.snap) == 151)

# ---------------------------------------------------------------------
# K8: the bar
# ---------------------------------------------------------------------
sa = TC.summary_a([
    dict(how='STOP', assumed=0.75, measured=1.75, entry_spread=1.0,
         exit_spread=1.0, entry_shown=3.0, exit_shown=4.0, stop_slip=5.0),
    dict(how='CLOSE', assumed=0.5, measured=0.76, entry_spread=1.0,
         exit_spread=1.0, entry_shown=3.0, exit_shown=4.0)])
sb = TC.summary_b([dict(contracts=1, spread=3.0, shown=2.0),
                   dict(contracts=-2, spread=3.0, shown=2.0),
                   dict(contracts=1)], 1)
t('K8: at most twice the assumed cost is WITHIN, exactly twice included, '
  'anything above is OVER, nothing measured is NOT MEASURED; A is judged '
  'on the average of its trades, B on the average contract',
  TC.verdict(1.0, 0.5) == 'WITHIN' and TC.verdict(1.001, 0.5) == 'OVER' and
  TC.verdict(0.3, 0.5) == 'WITHIN' and
  TC.verdict(None, None) == 'NOT MEASURED' and
  sa['round_trip'] == dict(n=2, assumed=0.625, measured=1.255,
                           times=2.008) and sa['status'] == 'OVER' and
  sb['contracts'] == 4 and sb['measured_contracts'] == 3 and
  sb['round_trip'] == dict(n=3, assumed=0.5, measured=1.0, times=2.0) and
  sb['status'] == 'WITHIN' and
  TC.summary_a([])['status'] == 'NOT MEASURED' and
  TC.summary_b([], 0)['status'] == 'NOT MEASURED' and
  TC.COMMISSION_PTS == 0.25 and TC.BAR == 2.0 and TC.TICK == 0.25)


# ---------------------------------------------------------------------
# K9: the command, and the frozen registration
# ---------------------------------------------------------------------
def said_by(fn):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = fn()
    return rc, buf.getvalue()


out9 = os.path.join(WORK, 'w25c.json')
led_none = os.path.join(WORK, 'exposed_none.json')
with open(led_none, 'w') as fh:
    json.dump(dict(exposed_days=[]), fh)
led_far = os.path.join(WORK, 'exposed_far.json')
with open(led_far, 'w') as fh:
    json.dump(dict(exposed_days=[dict(session='20261116',
                                      label='EXPOSED_PILOT_DEV')]), fh)
rc0, said0 = said_by(lambda: TC.main([]))
rc_ok, said_ok = said_by(lambda: TC.main([CAP, '--out', out9, '--quiet'],
                                         ledger=LED))
rc_none, said_none = said_by(lambda: TC.main([CAP, '--quiet'],
                                             ledger=led_none))
rc_far, said_far = said_by(lambda: TC.main([CAP, '--quiet'],
                                           ledger=led_far))
rc_dir, said_dir = said_by(lambda: TC.main(
    [os.path.join(WORK, 'no_such_folder'), '--quiet'], ledger=LED))
rep9 = json.load(open(out9))
t('K9: the command prints the measurement and writes the report; it '
  'stops on a missing folder, on a ledger that names no session and on '
  'a folder with no session it may read; the constants are the frozen '
  'registration\'s',
  rc0 == 2 and 'mrofyt_tradecost.py' in said0 and
  rc_ok == 0 and rep9['A'] == json.loads(json.dumps(rep['A'])) and
  rep9['B'] == json.loads(json.dumps(rep['B'])) and
  'A  the 5-minute opening range breakout: 5 trades, 4 measured (2 stops, '
  '1 targets, 2 at the close)' in said_ok and
  'round trip         assumed 0.62 points, measured 0.81 points: 1.30 '
  'times  (n 4)' in said_ok and
  'B  out of the noise area: 2 days, 5 position changes, 6 of 6 contracts '
  'measured' in said_ok and said_ok.count('    WITHIN') == 2 and
  'Sessions listed and never opened: 3. Runs skipped as damaged: 1.'
  in said_ok and 'section-2c report ->' in said_ok and
  rc_none == 2 and 'names no EXPOSED_PILOT_DEV session' in said_none and
  rc_far == 2 and 'none of them from 2026-09-01 to 2026-11-13' in said_far
  and rc_dir == 2 and said_dir.startswith('STOPPED: ') and
  (TC.FIRST_SESSION, TC.LAST_SESSION) == ('20260901', '20261113') and
  all(x in REG for x in (
      'the 55 recorded sessions (2026-09-01 to 2026-11-13)',
      'every A and B trade those sessions give, by the rules of §1 on '
      'one-minute bars of the recorded trades',
      'the spread at that second',
      'the contracts shown at the best price on the side taken',
      'the stop price against the best price on the far side at the first '
      'trade at or through the stop',
      '5 dollars of commission + half the spread at entry + half the '
      'spread at exit + the slip on a stop',
      'is **at most twice** the assumed one (0.50 points; 0.75 on a stop)')))

# ---------------------------------------------------------------------
# K10: the read is saved before anything is computed from it
# ---------------------------------------------------------------------
raw9 = TC.raw_path(out9)
out10 = os.path.join(WORK, 'again.json')
rc_again, said_again = said_by(lambda: TC.main(
    ['--from-raw', raw9, '--out', out10]))
no_dir = os.path.join(WORK, 'no_such_folder', 'w25c.json')
rc_out, said_out = said_by(lambda: TC.main([CAP, '--out', no_dir, '--quiet'],
                                           ledger=LED))
rc_notraw, said_notraw = said_by(lambda: TC.main(['--from-raw', out9]))
rc_gone, said_gone = said_by(lambda: TC.main(
    ['--from-raw', os.path.join(WORK, 'nothing.json')]))
a_list = os.path.join(WORK, 'list.json')
with open(a_list, 'w') as fh:
    json.dump([1, 2, 3], fh)
rc_list, said_list = said_by(lambda: TC.main(['--from-raw', a_list]))
raw_doc = json.load(open(raw9))
t('K10: with --out the read is written to its own file before the '
  'measurement, and --from-raw gives the same report from that file '
  'without the recordings; a report that cannot be written stops the run '
  'before the read; another file is not taken for a saved read',
  raw9.endswith('w25c_raw.json') and os.path.exists(raw9) and
  raw_doc['wave25c'] == TC.W25C_VERSION and
  len(raw_doc['sessions']) == 30 and
  raw_doc['refused_unread'] == ['20260831', '20261112', '20261116'] and
  not any(x['session'] > '20261113' for x in raw_doc['sessions']) and
  'the read itself  -> %s' % raw9 in said_ok and
  rc_again == 0 and json.load(open(out10)) == rep9 and
  'the read itself' not in said_again and
  not os.path.exists(TC.raw_path(out10)) and
  TC.measure(raw_doc) == TC.measure(json.loads(json.dumps(raw_doc))) and
  json.loads(json.dumps(TC.measure(raw_doc))) == rep9 and
  rc_out == 2 and 'cannot be written' in said_out and
  'Nothing was read' in said_out and
  not os.path.exists(os.path.dirname(no_dir)) and
  rc_notraw == 2 and 'is not a read saved by' in said_notraw and
  rc_list == 2 and 'is not a read saved by' in said_list and
  rc_gone == 2 and 'STOPPED: cannot read' in said_gone)

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
