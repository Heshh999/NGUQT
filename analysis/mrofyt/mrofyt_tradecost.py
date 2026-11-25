#!/usr/bin/env python3
"""mrofyt_tradecost.py - MROF-YT-W25C-TRADECOST-1.0

MROF_YT_WAVE25_CONFIRM_REGISTRATION.md, section 2c, turned into running
code: what a trade of A or B really costs, measured on the recorded NQ
sessions.

    bars      one-minute bars of the recorded trades
    trades    every A and B trade wave twenty-four's rules give on them
    measured  at each entry and exit the spread in ticks and the
              contracts shown at the best price on the side taken; for
              A's stops the slip from the stop price
    the bar   the measured average round trip (5 dollars of commission,
              half the spread in, half the spread out, the slip on a
              stop) at most twice the assumed one (0.50 points; 0.75 on
              a stop)

Only the quote, trade and quality files of NQ are read; the depth files
are not opened. Only sessions from 2026-09-01 to 2026-11-13 that the
exposure ledger marks EXPOSED_PILOT_DEV are read; any other session is
listed and never opened. It records nothing in any ledger and places no
order.

    python3 mrofyt_tradecost.py "<capture>" --out w25c.json
    python3 mrofyt_tradecost.py --from-raw w25c_raw.json --out w25c.json

The read takes hours. With --out it is saved (w25c_raw.json) before
anything is computed from it, and --from-raw makes the report again from
that file without reading the recordings.
"""
import collections
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_pilot as PI            # noqa: E402
import mrofyt_runner as RUN          # noqa: E402
import mrofyt_screen15 as S          # noqa: E402
import mrofyt_stretchfade as SF      # noqa: E402

W25C_VERSION = 'MROF-YT-W25C-TRADECOST-1.0'
REGISTRATION = W25.REGISTRATION
INSTRUMENT = 'NQ'
FIRST_SESSION, LAST_SESSION = '20260901', W25.LATER_TO
EXPOSURE_LEDGER = 'MROF_EXPOSED_PILOT_DEV_DAYS.json'
TICK, _TICK_VALUE = W25.MARKETS[INSTRUMENT]
COMMISSION_PTS = W25.COMMISSION_RT / (_TICK_VALUE / TICK)      # 0.25
BAR = 2.0                    # at most twice the assumed cost
MAX_QUOTE_AGE = 10.0         # seconds: an older quote is no quote
NEXT_QUOTE_S = 1.0           # the quote after a trade, if it comes so soon
A_FROM_S = S.OPEN_S + 300    # 09:35: A is in the market from here
RAW_KIND = 'section 2c, the read'


class Acc(object):
    """One contract in one session: its one-minute bars, the quote in
    force at each whole minute of the cash session, and every new low
    and new high traded from 09:35 to 16:00 with the quotes around it.
    The first trade at or through a price below the market is a new low,
    so these are all a stop or a target can need."""

    def __init__(self, session):
        day0 = CX._day_epoch(session)
        # 00:00 New York on the session date; the offset of that morning
        self.midnight = day0 - CX.et_offset(day0 + 14 * 3600,
                                            int(session[:4]))
        self.bars = {}               # minute of that day -> [o, h, l, c, v]
        self.snap = {}               # minutes after 09:30 -> quote or None
        self.next_j = 0
        self.lo = self.hi = None
        self.lows, self.highs = [], []   # [t, price, quote, next quote]
        self.pending = []

    def trade(self, t, px, sz, q):
        raw = t - self.midnight
        m = int(raw // 60)
        b = self.bars.get(m)
        if b is None:
            self.bars[m] = [px, px, px, px, sz]
        else:
            if px > b[1]:
                b[1] = px
            if px < b[2]:
                b[2] = px
            b[3] = px
            b[4] += sz
        if A_FROM_S <= raw < S.CLOSE_S:
            if self.lo is None or px < self.lo:
                self.lo = px
                rec = [t, px, quote_at(q, t), None]
                self.lows.append(rec)
                self.pending.append(rec)
            if self.hi is None or px > self.hi:
                self.hi = px
                rec = [t, px, quote_at(q, t), None]
                self.highs.append(rec)
                self.pending.append(rec)


def quote_at(q, t):
    """(bid, bid size, ask, ask size) in force at t; None when there is
    no quote, or the last one is older than MAX_QUOTE_AGE."""
    if q is None or t - q[0] > MAX_QUOTE_AGE:
        return None
    return q[1:]


class CostRunner(RUN.Runner):
    """The runner's discovery, its checks of each run's files and its
    handling of a damaged run, unchanged; the stream itself is read here,
    without the depth file, into one Acc per contract and session."""

    def __init__(self, capture_dir, allowed, progress=None):
        RUN.Runner.__init__(self, capture_dir, instruments=(INSTRUMENT,))
        self.allowed = allowed
        self.progress = progress
        self.done = {}                   # (contract, session) -> Acc
        self.refused = set()
        self.ledger['wave25c'] = dict(version=W25C_VERSION)

    def plan(self):
        keep = []
        for inst, ses, runs in RUN.Runner.plan(self):
            if self.allowed(ses):
                keep.append((inst, ses, runs))
            else:
                self.refused.add(ses)    # listed, never opened
        return keep

    def _flush(self, st):
        for c, acc in getattr(st, 'cost', {}).items():
            self.done[(c, st.cost_session)] = acc

    def finish(self):
        for st in self.states.values():
            self._flush(st)
            st.cost = {}

    def _process_run(self, st, mp, man):
        man = dict(man)
        man.pop('depth', None)           # the depth file is not opened
        if getattr(st, 'cost_session', None) != st.session:
            self._flush(st)
            st.cost_session, st.cost = st.session, {}
        st.cost_contract = CX.contract_of(
            str(man.get('contract') or ''), INSTRUMENT) or \
            '%s CONT' % INSTRUMENT
        RUN.Runner._process_run(self, st, mp, man)
        if self.progress:
            rec = self.ledger['runs'][-1]
            self.progress('%s %s %s: %s' % (
                st.session, st.cost_contract, rec.get('run_id'),
                'SKIPPED (%s)' % rec['skipped'] if rec.get('skipped')
                else '%d rows' % rec.get('events', 0)))

    def _stream_run(self, st, paths):
        acc = st.cost.get(st.cost_contract)
        if acc is None:
            acc = st.cost[st.cost_contract] = Acc(st.session)
        acc.pending = []         # no quote of this run follows those trades
        q = None                 # this run's last good quote
        n = crossed = quotes = 0
        t_j = acc.midnight + S.OPEN_S + 60.0 * acc.next_j
        for e in self._decoded(paths):
            n += 1
            t = e['t_recv']
            if t is None:
                continue
            k = e['stream']
            if k == 'QUALITY':
                if e['kind'] in ('DISCONNECT', 'RECONNECT'):
                    q = None
                continue
            while t >= t_j and acc.next_j <= S.N_MIN:
                acc.snap[acc.next_j] = quote_at(q, t_j)
                acc.next_j += 1
                t_j += 60.0
            if k == 'QUOTE':
                quotes += 1
                b, a = e['bid_px'], e['ask_px']
                if b is None or a is None:
                    continue
                if b >= a:
                    crossed += 1
                    continue
                flags = e['flags']
                if 'DATA_SUPPRESSED' in flags or 'DISCONNECTED' in flags:
                    q = None     # the recorder's own word that it is stale
                    continue
                q = (t, b, e['bid_sz'] or 0.0, a, e['ask_sz'] or 0.0)
                if acc.pending:
                    for rec in acc.pending:
                        rec[3] = (t - rec[0],) + q[1:]
                    acc.pending = []
            elif k == 'TRADE':
                px, sz = e['px'], e['sz']
                if px is None or sz is None:
                    continue
                acc.trade(t, px, sz, q)
        return n, crossed, quotes


# ---------------------------------------------------------------------
# the bars, and wave twenty-four's trades on them
# ---------------------------------------------------------------------
def day_stats(acc):
    """The reader's statistics of one session from its recorded bars."""
    agg = SF.VolDayAgg()
    for m in sorted(acc.bars):
        o, h, lo, c, v = acc.bars[m]
        agg.add((m * 60) % 86400, o, h, lo, c, v)
    return agg.finalize()


def build(done):
    """Wave twenty-four's (days, order, chain) from the recorded bars."""
    return S.build(types.SimpleNamespace(
        days={k: day_stats(a) for k, a in done.items() if a.bars}))


def spread(q):
    return (q[2] - q[0]) / TICK


def shown(q, side):
    """Contracts at the best price a buy (+) or a sell (-) meets."""
    return q[3] if side > 0 else q[1]


def a_parts(d):
    """(direction, stop, target) of A on a session: trade_a's own lines."""
    entry = d.p(5)
    sg = S.sign(entry - d.o)
    stop = min(d.l[:5]) if sg > 0 else max(d.h[:5])
    return sg, stop, entry + sg * S.A_TARGET_R * abs(entry - stop)


def touch_quote(acc, falling, level):
    """(quote, which) at the first trade at or through `level`: the
    first quote after that trade when it comes within NEXT_QUOTE_S (the
    book an order meets there), else the quote in force at the trade."""
    for rec in (acc.lows if falling else acc.highs):
        if (rec[1] <= level) if falling else (rec[1] >= level):
            nxt = rec[3]
            if nxt is not None and nxt[0] <= NEXT_QUOTE_S:
                return nxt[1:], 'next quote'
            return rec[2], 'in force'
    return None, None


def measure_a(days, order, done):
    """One record for each A trade."""
    out = []
    for s in order:
        d = days[s]
        tr = S.trade_a(d)
        if tr is None:
            continue
        acc = done[(d.contract, s)]
        sg, stop, target = a_parts(d)
        entry, how = d.p(5), tr['how']
        exit_px = stop if how == 'STOP' else (
            target if how == 'TARGET' else d.p(S.N_MIN))
        if abs(tr['gross'] - sg * (exit_px - entry) / entry) > 1e-9:
            raise RuntimeError('session %s: the stop and target do not '
                               'reproduce wave twenty-four\'s A' % s)
        rec = dict(session=s, contract=d.contract, direction=sg, how=how,
                   assumed=S.RT_STOP if how == 'STOP' else S.RT)
        q_in = acc.snap.get(5)
        if q_in:
            rec.update(entry_spread=spread(q_in),
                       entry_shown=shown(q_in, sg))
        if how == 'CLOSE':
            q_out, which = acc.snap.get(S.N_MIN), 'at 16:00'
        else:
            q_out, which = touch_quote(acc, (how == 'STOP') == (sg > 0),
                                       exit_px)
        slip = 0.0
        if q_out:
            rec.update(exit_spread=spread(q_out),
                       exit_shown=shown(q_out, -sg), exit_quote=which)
            if how == 'STOP':
                slip = (stop - q_out[0] if sg > 0 else q_out[2] - stop) \
                    / TICK
                rec['stop_slip'] = slip
        if q_in and q_out:
            rec['measured'] = COMMISSION_PTS + TICK * (
                0.5 * rec['entry_spread'] + 0.5 * rec['exit_spread'] + slip)
        out.append(rec)
    return out


def b_changes(d, sigma):
    """[(minutes after 09:30, contracts bought (+) or sold (-))]: the
    position changes of wave twenty-four's day_b, step for step."""
    hi, lo = max(d.o, d.pc), min(d.o, d.pc)
    pos, out = 0, []
    for j in S.B_TIMES + (S.N_MIN,):
        want = 0
        if j != S.N_MIN:
            p, vw = d.p(j), d.vwap(j)
            if vw is not None and p > hi * (1 + sigma[j]) and p > vw:
                want = 1
            elif vw is not None and p < lo * (1 - sigma[j]) and p < vw:
                want = -1
        if want != pos:
            out.append((j, want - pos))
            pos = want
    return out


def measure_b(days, order, chain, done):
    """(one record for each position change of B, the days B traded)."""
    calls, orig = [], S.day_b

    def spy(d, sigma):
        res = orig(d, sigma)
        calls.append((d, sigma, res))
        return res
    S.day_b = spy
    try:
        trades, _notes = S.rule_b(days, order, chain)
    finally:
        S.day_b = orig
    traded = {t['session'] for t in trades}
    out = []
    for d, sigma, (_gross, cost, n) in calls:
        if d.session not in traded:
            continue
        ch = b_changes(d, sigma)
        if len(ch) != n or abs(sum(abs(x) for _j, x in ch) * S.SIDE / d.o
                               - cost) > 1e-12:
            raise RuntimeError('session %s: the position changes do not '
                               'reproduce wave twenty-four\'s B' % d.session)
        acc = done[(d.contract, d.session)]
        for j, delta in ch:
            rec = dict(session=d.session, contract=d.contract, minute=j,
                       contracts=delta)
            q = acc.snap.get(j)
            if q:
                rec.update(spread=spread(q), shown=shown(q, delta))
            out.append(rec)
    return out, len(traded)


# ---------------------------------------------------------------------
# the measured round trip against the assumed one
# ---------------------------------------------------------------------
def _at(v, p):
    return v[min(len(v) - 1, int(p * len(v)))]


def _median(v):
    return (v[(len(v) - 1) // 2] + v[len(v) // 2]) / 2.0


def spread_stats(v):
    v = sorted(v)
    if not v:
        return dict(n=0)
    return dict(n=len(v), mean=round(S.mean(v), 3), median=_median(v),
                p90=_at(v, 0.9), max=v[-1])


def shown_stats(v):
    v = sorted(v)
    if not v:
        return dict(n=0)
    return dict(n=len(v), median=_median(v), p10=_at(v, 0.1), min=v[0])


def verdict(measured, assumed):
    if measured is None:
        return 'NOT MEASURED'
    return 'WITHIN' if measured <= BAR * assumed + 1e-9 else 'OVER'


def _trip(pairs):
    """dict(assumed, measured, times) of [(assumed, measured)] or {}."""
    if not pairs:
        return dict(n=0)
    a, m = S.mean([x for x, _y in pairs]), S.mean([y for _x, y in pairs])
    return dict(n=len(pairs), assumed=round(a, 4), measured=round(m, 4),
                times=round(m / a, 3))


def summary_a(recs):
    full = [(r['assumed'], r['measured']) for r in recs if 'measured' in r]
    out = dict(
        trades=len(recs), measured=len(full),
        exits=dict(collections.Counter(r['how'] for r in recs)),
        entry_spread_ticks=spread_stats(
            [r['entry_spread'] for r in recs if 'entry_spread' in r]),
        exit_spread_ticks=spread_stats(
            [r['exit_spread'] for r in recs if 'exit_spread' in r]),
        shown_contracts=shown_stats(
            [r[k] for r in recs for k in ('entry_shown', 'exit_shown')
             if k in r]),
        stop_slip_ticks=spread_stats(
            [r['stop_slip'] for r in recs if 'stop_slip' in r]),
        round_trip=_trip(full),
        on_a_stop=_trip([(r['assumed'], r['measured']) for r in recs
                         if 'measured' in r and r['how'] == 'STOP']),
        otherwise=_trip([(r['assumed'], r['measured']) for r in recs
                         if 'measured' in r and r['how'] != 'STOP']))
    out['status'] = verdict(out['round_trip'].get('measured'),
                            out['round_trip'].get('assumed'))
    return out


def summary_b(recs, n_days):
    got = [r for r in recs if 'spread' in r]
    w = sum(abs(r['contracts']) for r in got)
    out = dict(
        days=n_days, changes=len(recs),
        contracts=sum(abs(r['contracts']) for r in recs),
        measured_contracts=w,
        spread_ticks=spread_stats([r['spread'] for r in got]),
        shown_contracts=shown_stats([r['shown'] for r in got]),
        round_trip=dict(n=0))
    if w:
        m = COMMISSION_PTS + TICK * sum(
            abs(r['contracts']) * r['spread'] for r in got) / w
        out['round_trip'] = dict(n=w, assumed=round(S.RT, 4),
                                 measured=round(m, 4),
                                 times=round(m / S.RT, 3))
    out['status'] = verdict(out['round_trip'].get('measured'),
                            out['round_trip'].get('assumed'))
    return out


def exposed_sessions(path):
    try:
        with open(path) as fh:
            days = json.load(fh).get('exposed_days', [])
    except (OSError, ValueError):
        return set()
    return {d.get('session') for d in days
            if d.get('label') == PI.EXPOSURE_LABEL}


def read_capture(capture_dir, ledger=None, progress=None):
    """Everything the measurement needs from the recordings, as plain
    lists and numbers: it is saved to a file before anything is computed
    from it, so a read of hours is never made twice."""
    ledger = ledger or os.path.join(HERE, EXPOSURE_LEDGER)
    exposed = exposed_sessions(ledger)
    if not exposed:
        raise RUN.NoCaptureData(
            'the exposure ledger %s names no %s session, so none may be '
            'read. Nothing was read.' % (os.path.basename(ledger),
                                         PI.EXPOSURE_LABEL))
    r = CostRunner(
        capture_dir,
        lambda s: FIRST_SESSION <= s <= LAST_SESSION and s in exposed,
        progress)
    try:
        led = r.run()
    except RUN.NoCaptureData:
        if not r.refused:
            raise
        raise RUN.NoCaptureData(
            'the folder holds %d NQ session(s), none of them from '
            '2026-09-01 to 2026-11-13 and marked %s in the ledger. Nothing '
            'was read.' % (len(r.refused), PI.EXPOSURE_LABEL))
    r.finish()
    return dict(
        wave25c=W25C_VERSION, kind=RAW_KIND,
        refused_unread=sorted(r.refused), runs=len(led['runs']),
        runs_skipped=[dict(x) for x in led['skipped_runs']],
        sessions=[dict(contract=c, session=s, next_j=a.next_j,
                       bars=[[m] + list(a.bars[m]) for m in sorted(a.bars)],
                       snap=[[j, a.snap[j]] for j in sorted(a.snap)],
                       lows=a.lows, highs=a.highs)
                  for (c, s), a in sorted(r.done.items())])


def accs_of(raw):
    """{(contract, session): Acc} back from a saved read."""
    if not isinstance(raw, dict) or raw.get('wave25c') != W25C_VERSION \
            or raw.get('kind') != RAW_KIND:
        raise RUN.NoCaptureData('this is not a read saved by %s. Nothing '
                                'was computed.' % W25C_VERSION)

    def tup(x):
        return tuple(x) if x else None
    done = {}
    for x in raw['sessions']:
        acc = Acc(x['session'])
        acc.next_j = x['next_j']
        acc.bars = {b[0]: list(b[1:]) for b in x['bars']}
        acc.snap = {j: tup(q) for j, q in x['snap']}
        acc.lows = [[r[0], r[1], tup(r[2]), tup(r[3])] for r in x['lows']]
        acc.highs = [[r[0], r[1], tup(r[2]), tup(r[3])] for r in x['highs']]
        done[(x['contract'], x['session'])] = acc
    return done


def measure(raw):
    """The report of section 2c from a read, fresh or saved."""
    done = accs_of(raw)
    days, order, chain = build(done)
    a_recs = measure_a(days, order, done)
    b_recs, b_days = measure_b(days, order, chain, done)
    read = sorted({s for (_c, s) in done})
    return dict(
        wave25c=W25C_VERSION, registration=REGISTRATION, part='2c',
        instrument=INSTRUMENT, sessions_read=len(read),
        first_session=read[0] if read else None,
        last_session=read[-1] if read else None,
        refused_unread=list(raw['refused_unread']), runs=raw['runs'],
        runs_skipped=list(raw['runs_skipped']),
        trading_days=len(chain), usable_sessions=len(order),
        assumed=dict(round_trip=S.RT, stop=S.RT_STOP,
                     commission=COMMISSION_PTS),
        A=summary_a(a_recs), B=summary_b(b_recs, b_days),
        a_trades=a_recs, b_changes=b_recs)


def run(capture_dir, ledger=None, progress=None):
    return measure(read_capture(capture_dir, ledger, progress))


def _sp(st, unit='ticks'):
    if not st.get('n'):
        return 'none measured'
    return 'mean %.2f %s, median %g, nine in ten at most %g, most %g  ' \
        '(n %d)' % (st['mean'], unit, st['median'], st['p90'], st['max'],
                    st['n'])


def _trip_text(tr):
    if not tr.get('n'):
        return 'none measured'
    return 'assumed %.2f points, measured %.2f points: %.2f times  (n %d)' \
        % (tr['assumed'], tr['measured'], tr['times'], tr['n'])


def text(rep):
    a, b = rep['A'], rep['B']
    L = ['%s  2c  NQ  %d sessions read (%s .. %s), %d usable' % (
        rep['wave25c'], rep['sessions_read'], rep['first_session'],
        rep['last_session'], rep['usable_sessions']),
        'What a trade really costs, measured on the recorded quotes. The '
        'bar: the measured',
        'round trip at most twice the assumed one (0.50 points; 0.75 on a '
        'stop).',
        'Sessions listed and never opened: %d. Runs skipped as damaged: %d.'
        % (len(rep['refused_unread']), len(rep['runs_skipped'])), '']
    ex = a['exits']
    L += ['A  %s: %d trades, %d measured (%d stops, %d targets, %d at the '
          'close)' % (S.NAMES['A'], a['trades'], a['measured'],
                      ex.get('STOP', 0), ex.get('TARGET', 0),
                      ex.get('CLOSE', 0)),
          '    spread at entry    %s' % _sp(a['entry_spread_ticks']),
          '    spread at exit     %s' % _sp(a['exit_spread_ticks']),
          '    slip on a stop     %s' % _sp(a['stop_slip_ticks'])]
    sh = a['shown_contracts']
    if sh.get('n'):
        L.append('    contracts shown    median %g, one time in ten %g or '
                 'fewer, least %g' % (sh['median'], sh['p10'], sh['min']))
    L += ['    on a stop          %s' % _trip_text(a['on_a_stop']),
          '    otherwise          %s' % _trip_text(a['otherwise']),
          '    round trip         %s' % _trip_text(a['round_trip']),
          '    %s' % a['status'], '']
    L += ['B  %s: %d days, %d position changes, %d of %d contracts '
          'measured' % (S.NAMES['B'], b['days'], b['changes'],
                        b['measured_contracts'], b['contracts']),
          '    spread at a change %s' % _sp(b['spread_ticks'])]
    sh = b['shown_contracts']
    if sh.get('n'):
        L.append('    contracts shown    median %g, one time in ten %g or '
                 'fewer, least %g' % (sh['median'], sh['p10'], sh['min']))
    L += ['    round trip         %s' % _trip_text(b['round_trip']),
          '    %s' % b['status'], '',
          'Recorded quotes and trades; no order was placed.']
    return '\n'.join(L)


def raw_path(out):
    return os.path.splitext(out)[0] + '_raw.json'


def main(argv=None, ledger=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    def arg(k):
        i = argv.index(k) + 1 if k in argv else len(argv)
        return argv[i] if i < len(argv) else None
    saved, out = arg('--from-raw'), arg('--out')
    if not argv or (argv[0].startswith('--') and not saved):
        print(__doc__)
        return 2
    if out and not (W25.can_write(out) and (
            saved or W25.can_write(raw_path(out)))):
        print('STOPPED: %s cannot be written (does the folder exist?). '
              'Nothing was read.' % out)
        return 2

    def progress(line):
        sys.stderr.write('  %s\n' % line)
        sys.stderr.flush()
    try:
        if saved:
            try:
                with open(saved) as fh:
                    raw = json.load(fh)
            except (OSError, ValueError) as exc:
                print('STOPPED: cannot read %s (%s).' % (saved, exc))
                return 2
        else:
            raw = read_capture(argv[0], ledger,
                               None if '--quiet' in argv else progress)
            if out:                  # on disk before anything is computed
                with open(raw_path(out), 'w') as fh:
                    json.dump(raw, fh, separators=(',', ':'))
        rep = measure(raw)
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
    print(text(rep))
    if out:
        print('\nsection-2c report -> %s' % out)
        if not saved:
            print('the read itself  -> %s  (--from-raw makes the report '
                  'again without reading)' % raw_path(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
