#!/usr/bin/env python3
"""mrofyt_markets28.py - MROF-YT-W28-MARKETS-1.0

MROF_YT_WAVE28_MARKETS_REGISTRATION.md turned into running code: A (the
5-minute opening range breakout) and B (out of the noise area), exactly
as wave twenty-four coded them, on markets that are not stock indices.

    the rules     wave twenty-four's own functions; only the day session
                  (each market's own open and close) and the costs are
                  set around them
    the markets   CL NG (energy), GC SI HG (metals), 6E 6J (currencies),
                  BTC (crypto)
    the gates     before any result: the time stamps, no hole, 1,500
                  eligible sessions, and a round trip of at most 2 % of
                  a normal day's move
    one market    one read, once, on the ledger; a report with one
                  number per session and rule, in units of the
                  session's own risk
    the decision  once, on every market read: a pooled test per rule
                  (weekly t of 2.5 or more, above zero in each half),
                  class tests under Benjamini and Hochberg at 10 %

Sessions from 2026-07-01 are never read. Read-only; no order is placed.

    python mrofyt_markets28.py "<CL minute exports>" --market CL
        --out w28_cl.json            (add --gaps-ok only where the feed
                                      has no bars for the missing days)
    python mrofyt_markets28.py --decide w28_cl.json w28_gc.json ...
        shows what would be decided on; add --final to decide (once),
        and --out w28.json to keep the report
"""
import collections
import contextlib
import datetime
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_context as CX          # noqa: E402
import mrofyt_discover as DI         # noqa: E402
import mrofyt_screen15 as S          # noqa: E402
import mrofyt_stretchfade as SF      # noqa: E402
import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_levels27 as L27        # noqa: E402

W28_VERSION = 'MROF-YT-W28-MARKETS-1.0'
REGISTRATION = 'MROF_YT_WAVE28_MARKETS_REGISTRATION.md'
HISTORY_LEDGER = W25.HISTORY_LEDGER

RULES = ('A', 'B')
COMMISSION_RT = 5.0                    # dollars a round trip
Market = collections.namedtuple('Market',
                                'cls open close tick point spread')
MARKETS = collections.OrderedDict((   # the registration, section 2
    ('CL', Market('energy', (9, 0), (14, 30), 0.01, 1000.0, 1)),
    ('NG', Market('energy', (9, 0), (14, 30), 0.001, 10000.0, 1)),
    ('GC', Market('metals', (8, 20), (13, 30), 0.10, 100.0, 1)),
    ('SI', Market('metals', (8, 25), (13, 25), 0.005, 5000.0, 1)),
    ('HG', Market('metals', (8, 10), (13, 0), 0.0005, 25000.0, 1)),
    ('6E', Market('currencies', (8, 20), (15, 0), 0.00005, 125000.0, 1)),
    ('6J', Market('currencies', (8, 20), (15, 0), 0.0000005, 12500000.0,
                  1)),
    ('BTC', Market('crypto', (9, 30), (16, 0), 5.0, 5.0, 4))))
CLASSES = ('energy', 'metals', 'currencies', 'crypto')

COMPLETE_MISSING = 20                  # minutes of a day session
BREAK_FROM, BREAK_TO = 17 * 60, 18 * 60        # ET minute of day
BREAK_SHARE = 0.001                    # gate 1
MAX_GAP_DAYS = W25.MAX_GAP_DAYS        # gate 2
MIN_SESSIONS = 1500                    # gate 3
COST_SHARE_MAX = 0.02                  # gate 4
TICK_SHARE = 0.01                      # of a file's non-zero changes
TICK_MIN_CHANGES = 200                 # a file with fewer says nothing
POOL_T = 2.5
BH_Q = 0.10
MIN_MARKETS, MIN_CLASSES = 4, 2

_CX_NAMES = ('RTH_OPEN', 'RTH_CLOSE', 'IB_END', 'VWAP_EARLY',
             'RTH_MIN_BARS', 'RTH_FIRST_BY', 'RTH_LAST_FROM')
_S_NAMES = ('OPEN_S', 'CLOSE_S', 'N_MIN', 'B_TIMES', 'RT', 'RT_STOP',
            'SIDE', 'CO')


# ---------------------------------------------------------------------
# registration 1-2: the market's day session and costs around the rules
# ---------------------------------------------------------------------
def _sec(hm):
    return hm[0] * 3600 + hm[1] * 60


def minutes_of(market):
    m = MARKETS[market]
    return (_sec(m.close) - _sec(m.open)) // 60


def market_costs(market, tick=None):
    """dict(tick, rt, stop) in the market's price: 5 dollars and one
    spread a round trip, one spread more on a stop."""
    m = MARKETS[market]
    tick = m.tick if tick is None else tick
    com = COMMISSION_RT / m.point
    return dict(tick=tick, rt=round(com + m.spread * tick, 12),
                stop=round(com + 2 * m.spread * tick, 12))


@contextlib.contextmanager
def setup(market, tick=None, times=1.0):
    """Wave twenty-four's reader and rules under `market`'s day session,
    tick and costs (times `times`), then exactly as they were."""
    m = MARKETS[market]
    o, c = _sec(m.open), _sec(m.close)
    n = (c - o) // 60
    cst = market_costs(market, tick)
    old_cx = [getattr(CX, k) for k in _CX_NAMES]
    old_s = [getattr(S, k) for k in _S_NAMES]
    CX.RTH_OPEN, CX.RTH_CLOSE = o, c
    CX.IB_END, CX.VWAP_EARLY = o + 3600, o + 1800
    CX.RTH_MIN_BARS = n - COMPLETE_MISSING
    CX.RTH_FIRST_BY, CX.RTH_LAST_FROM = o + 60, c - 300
    S.OPEN_S, S.CLOSE_S, S.N_MIN = o, c, n
    S.B_TIMES = tuple(range(30, n - 29, 30))
    S.RT, S.RT_STOP = cst['rt'] * times, cst['stop'] * times
    S.SIDE = S.RT / 2.0
    S.CO = types.SimpleNamespace(TICK=cst['tick'])
    try:
        yield cst
    finally:
        for k, v in zip(_CX_NAMES, old_cx):
            setattr(CX, k, v)
        for k, v in zip(_S_NAMES, old_s):
            setattr(S, k, v)


# ---------------------------------------------------------------------
# registration 2-3: reading, the tick, the gates
# ---------------------------------------------------------------------
def read(path, market):
    """Wave twenty-two's reader over `market`'s exports. Called inside
    setup(): a day session is the market's."""
    rd = SF.VolReader(market, 'UTC', 'end', None)
    rd.read_path(path)
    if not rd.days:
        raise CX.ContextDataError(CX._nothing_read(
            rd, market, 'before %s' % CX.REFUSE_FROM))
    return rd


def break_share(rd):
    """The share of the bars that start in the daily break."""
    total = sum(rd.minute_n.values())
    inside = sum(n for m, n in rd.minute_n.items()
                 if BREAK_FROM <= m < BREAK_TO)
    return inside / float(total) if total else 0.0


def file_tick(steps):
    """The smallest step that makes up TICK_SHARE of a file's non-zero
    changes of the close (steps: Counter), or None with too few."""
    n = sum(steps.values())
    if n < TICK_MIN_CHANGES:
        return None
    for step in sorted(steps):
        if steps[step] >= TICK_SHARE * n:
            return step
    return None


def observed_tick(rd):
    """(the largest file_tick over the contract files, {contract: its
    own}); None where no file says anything."""
    steps = collections.defaultdict(collections.Counter)
    for (c, _s), st in rd.days.items():
        bars = st['bars']
        last = None
        cnt = steps[c]
        for k in range(3, len(bars), 4):
            x = bars[k]
            if last is not None and x != last:
                cnt[round(abs(x - last), 10)] += 1
            last = x
    per = {c: file_tick(cnt) for c, cnt in steps.items()}
    seen = [v for v in per.values() if v]
    return (max(seen) if seen else None), per


def _median(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def cost_share(days, order, vol, rt):
    """Gate 4's number: the median over the eligible sessions that have
    s of (round trip / O) / s; None without one."""
    v = [(rt / days[s].o) / vol[s] for s in order if vol.get(s)]
    return _median(v) if v else None


# ---------------------------------------------------------------------
# registration 4: one number per session, in units of its own risk
# ---------------------------------------------------------------------
def risk_share(d):
    """A's risk over its entry on one session: the first lines of
    wave twenty-four's trade_a."""
    entry = d.p(5)
    sg = S.sign(entry - d.o)
    stop = min(d.l[:5]) if sg > 0 else max(d.h[:5])
    return abs(entry - stop) / entry


def series_a(days, order, trades):
    """[(session, net in multiples of the trade's risk)], every
    eligible session; 0 without a trade."""
    by = {t['session']: t for t in trades}
    out = []
    for s in order:
        t = by.get(s)
        out.append((s, 0.0 if t is None else
                    (t['gross'] - t['cost']) / risk_share(days[s])))
    return out


def series_b(order, vol, trades):
    """[(session, net / s)], every session where B has its 14 sessions
    and its s; 0 without a trade."""
    by = {t['session']: t for t in trades}
    out = []
    for s in order[S.B_HISTORY:]:
        if not vol.get(s):
            continue
        t = by.get(s)
        out.append((s, 0.0 if t is None else
                    (t['gross'] - t['cost']) / vol[s]))
    return out


def week_of(session):
    return L27.week_label(W25._date(session))


def stats(pairs):
    """pairs: [(session, x)]. dict(n, mean, t, p one-sided, weeks,
    halves={H1, H2: mean or None}, positive_halves)."""
    out = dict(n=len(pairs), mean=None, t=None, p=None, weeks=0,
               halves=dict.fromkeys(S.HALVES), positive_halves=False)
    if not pairs:
        return out
    pairs = sorted(pairs)
    vals = [x for _s, x in pairs]
    wt = L27.weekly_t(vals, [week_of(s) for s, _x in pairs])
    out.update(mean=S.mean(vals), t=wt['t'], p=wt['p'], weeks=wt['weeks'])
    for h in S.HALVES:
        v = [x for s, x in pairs if S.half_of(s) == h]
        out['halves'][h] = S.mean(v) if v else None
    out['positive_halves'] = all(
        out['halves'][h] is not None and out['halves'][h] > 0
        for h in S.HALVES)
    return out


def _bar(rule, trades):
    """Wave twenty-four's bar in the source's sizing (beside)."""
    j = S.judge(S.nets(rule, trades, {}))
    return dict(status=j['status'], strong=j['strong'], n=j['both']['n'],
                H1=j['halves']['H1'].get('net'),
                H2=j['halves']['H2'].get('net'))


# ---------------------------------------------------------------------
# one market
# ---------------------------------------------------------------------
def run_market(path, market, gaps_ok=False):
    if market not in MARKETS:
        raise CX.ContextDataError('unknown market %r: one of %s'
                                  % (market, ', '.join(MARKETS)))
    m = MARKETS[market]
    with setup(market):
        rd = read(path, market)
        days, order, chain = S.build(rd)
    share = break_share(rd)
    if share >= BREAK_SHARE:
        raise CX.ContextDataError(
            '%.2f %% of the %s bars start between 17:00 and 18:00 ET, when '
            'the market is closed: the time stamps are not UTC bar ends. '
            'Nothing was computed.' % (100 * share, market))
    g = W25.gaps(chain)
    if g and not gaps_ok:
        raise CX.ContextDataError(
            'the %s exports have no day session between %s: a contract was '
            'not exported. Nothing was computed. Export it and run again; '
            'if the feed has no bars for those days, add --gaps-ok.'
            % (market, W25._gap_text(g)))
    if len(order) < MIN_SESSIONS:
        raise CX.ContextDataError(
            'only %d eligible %s sessions; %d are needed. Nothing was '
            'computed.' % (len(order), market, MIN_SESSIONS))
    seen, per_file = observed_tick(rd)
    tick = max(m.tick, seen or 0.0)
    vol = L27.daily_vol(chain)
    cst = market_costs(market, tick)
    cs = cost_share(days, order, vol, cst['rt'])
    rep = dict(
        wave28=W28_VERSION, registration=REGISTRATION, part='market',
        market=market, cls=m.cls,
        day_session='%02d:%02d-%02d:%02d ET' % (m.open + m.close),
        minutes=minutes_of(market), files=len(rd.files),
        bad_lines=rd.bad_lines, sessions=len(order), first_session=order[0],
        last_session=order[-1], trading_days=len(chain),
        gaps=[list(x) for x in g], break_share=round(share, 6),
        refused_from_gate=len(rd.refused_sessions),
        tick=dict(registered=m.tick, observed=seen, used=tick,
                  files_larger=sorted(c for c, v in per_file.items()
                                      if v and v > m.tick * (1 + 1e-9))),
        costs=dict(round_trip=cst['rt'], stop=cst['stop']),
        cost_share=None if cs is None else round(cs, 6),
        left_out=None, rules={}, series={}, n_trades=0)
    if cs is None or cs > COST_SHARE_MAX:
        rep['left_out'] = 'the cost gate: a round trip is %s of a normal ' \
            'day\'s move, above %.0f %%' % (
                'unknown' if cs is None else '%.2f %%' % (100 * cs),
                100 * COST_SHARE_MAX)
        return rep
    with setup(market, tick):
        ta = S.rule_a(days, order)[0]
        tb = S.rule_b(days, order, chain)[0]
        bars = dict(A=_bar('A', ta), B=_bar('B', tb))
    with setup(market, tick, 2.0):
        twice = dict(A=_bar('A', S.rule_a(days, order)[0]),
                     B=_bar('B', S.rule_b(days, order, chain)[0]))
    ser = dict(A=series_a(days, order, ta), B=series_b(order, vol, tb))
    for rule, trades in (('A', ta), ('B', tb)):
        st = stats(ser[rule])
        st.update(trades=len(trades), bar=bars[rule],
                  bar_costs_doubled=twice[rule]['status'])
        rep['rules'][rule] = st
        rep['series'][rule] = [[s, round(x, 6)] for s, x in ser[rule]]
    rep['n_trades'] = len(ta) + len(tb)
    return rep


# ---------------------------------------------------------------------
# registration 5: the decision
# ---------------------------------------------------------------------
def pool(series):
    """series: [[(session, x)]] of several markets -> [(session, the
    plain average over the markets that have the session)]."""
    by = collections.defaultdict(list)
    for ser in series:
        for s, x in ser:
            by[s].append(x)
    return [(s, S.mean(v)) for s, v in sorted(by.items())]


def decide(reps):
    """reps: this wave's market reports. -> the decision."""
    seen = set()
    for r in reps:
        if r.get('wave28') != W28_VERSION or r.get('part') != 'market':
            raise CX.ContextDataError(
                'a report is not a market report of %s' % W28_VERSION)
        if r['market'] in seen:
            raise CX.ContextDataError('two reports of %s' % r['market'])
        seen.add(r['market'])
    judged = [r for r in reps if not r.get('left_out')]
    out = dict(
        wave28=W28_VERSION, registration=REGISTRATION, part='decide',
        markets=[r['market'] for r in judged],
        left_out={r['market']: r['left_out'] for r in reps
                  if r.get('left_out')},
        classes=[c for c in CLASSES if any(r['cls'] == c for r in judged)],
        decided=False, why=None, pooled={}, class_tests=[], holds={},
        goes_on={}, goes_on_markets={})
    if len(judged) < MIN_MARKETS or len(out['classes']) < MIN_CLASSES:
        out['why'] = 'no decision: %d markets from %d classes; %d from %d ' \
            'are needed' % (len(judged), len(out['classes']), MIN_MARKETS,
                            MIN_CLASSES)
        return out
    out['decided'] = True
    tests = []
    for rule in RULES:
        st = stats(pool([[tuple(x) for x in r['series'][rule]]
                         for r in judged]))
        st['holds'] = bool(st['t'] is not None and st['t'] >= POOL_T and
                           st['positive_halves'])
        out['pooled'][rule] = st
        out['holds'][rule] = st['holds']
        for cls in out['classes']:
            cs = stats(pool([[tuple(x) for x in r['series'][rule]]
                             for r in judged if r['cls'] == cls]))
            cs.update(rule=rule, cls=cls, markets=[
                r['market'] for r in judged if r['cls'] == cls])
            tests.append(cs)
    qs = DI.bh_q([c['p'] for c in tests])
    for c, q in zip(tests, qs):
        c['q'] = q
        c['kept'] = bool(q is not None and q <= BH_Q)
        c['passes'] = bool(c['kept'] and c['positive_halves'])
    out['class_tests'] = tests
    for rule in RULES:
        mine = [c for c in tests if c['rule'] == rule]
        on = [c['cls'] for c in mine
              if (c['positive_halves'] if out['holds'][rule]
                  else c['passes'])]
        out['goes_on'][rule] = on
        out['goes_on_markets'][rule] = [r['market'] for r in judged
                                        if r['cls'] in on]
    return out


# ---------------------------------------------------------------------
# text, ledger, command
# ---------------------------------------------------------------------
def _h(x, fmt='%+.2f'):
    """A mean in hundredths of the session's risk."""
    return '  n/a' if x is None else fmt % (100.0 * x)


def _t(x):
    return ' n/a' if x is None else '%+.2f' % x


def text(rep):
    if rep.get('part') == 'decide':
        return text_decide(rep)
    L = ['%s   %s (%s)   day session %s, %d minutes' % (
        rep['wave28'], rep['market'], rep['cls'], rep['day_session'],
        rep['minutes']),
        'files %d   eligible sessions %d (%s to %s)   trading days %d' % (
            rep['files'], rep['sessions'], rep['first_session'],
            rep['last_session'], rep['trading_days']),
        'gates: bars in the daily break %.3f %%;  holes %s;  a round trip '
        'is %s of a normal day\'s move' % (
            100 * rep['break_share'],
            'none' if not rep['gaps'] else '%d (read with --gaps-ok)'
            % len(rep['gaps']),
            'n/a' if rep['cost_share'] is None
            else '%.2f %%' % (100 * rep['cost_share'])),
        'tick %g (registered %g, seen %s)   round trip %g, on a stop %g' % (
            rep['tick']['used'], rep['tick']['registered'],
            'n/a' if rep['tick']['observed'] is None
            else '%g' % rep['tick']['observed'],
            rep['costs']['round_trip'], rep['costs']['stop'])]
    if rep['left_out']:
        L += ['', 'LEFT OUT: %s. No rule was run.' % rep['left_out']]
        return '\n'.join(L)
    L += ['', 'One market alone is reported, never judged. Means are in '
          'hundredths of the session\'s own risk.',
          '  rule  sessions  trades     mean     t     first half  second '
          'half   wave 24\'s bar (costs doubled)']
    for rule in RULES:
        r = rep['rules'][rule]
        L.append('  %-4s  %8d  %6d  %s  %s      %s       %s   %s%s (%s)' % (
            rule, r['n'], r['trades'], _h(r['mean'], '%+7.2f'), _t(r['t']),
            _h(r['halves']['H1'], '%+6.2f'), _h(r['halves']['H2'], '%+6.2f'),
            r['bar']['status'], ' strong' if r['bar']['strong'] else '',
            r['bar_costs_doubled']))
    L.append('Minute bars, costs charged; not P&L. No order was placed.')
    return '\n'.join(L)


def text_decide(rep):
    L = ['%s   THE DECISION' % rep['wave28'],
         'markets: %s' % (', '.join(rep['markets']) or 'none')]
    for mk, why in sorted(rep['left_out'].items()):
        L.append('left out: %s (%s)' % (mk, why))
    if not rep['decided']:
        L.append(rep['why'])
        return '\n'.join(L)
    L += ['', 'THE POOLED TEST (t of %.1f or more, above zero in each half)'
          % POOL_T,
          '  rule   days    mean      t   first half  second half']
    for rule in RULES:
        p = rep['pooled'][rule]
        L.append('  %-4s  %5d  %s  %s      %s       %s    %s' % (
            rule, p['n'], _h(p['mean'], '%+6.2f'), _t(p['t']),
            _h(p['halves']['H1'], '%+6.2f'), _h(p['halves']['H2'], '%+6.2f'),
            'HOLDS outside stock indices' if p['holds']
            else 'does not hold'))
    L += ['', 'THE CLASS TESTS (Benjamini-Hochberg at %.0f %% over %d tests)'
          % (100 * BH_Q, len(rep['class_tests'])),
          '  rule  class        markets        mean      t      q   '
          'halves']
    for c in rep['class_tests']:
        L.append('  %-4s  %-11s  %-12s  %s  %s  %s   %s   %s' % (
            c['rule'], c['cls'], ' '.join(c['markets']),
            _h(c['mean'], '%+6.2f'), _t(c['t']),
            ' n/a' if c['q'] is None else '%.3f' % c['q'],
            'both up' if c['positive_halves'] else 'not both',
            'PASSES' if c['passes'] else '-'))
    L.append('')
    for rule in RULES:
        on = rep['goes_on_markets'][rule]
        L.append('%s goes on to the shadow step on: %s' % (
            rule, ', '.join(on) if on else 'nothing'))
    L.append('Means are in hundredths of a session\'s own risk. Minute '
             'bars, costs charged; not P&L. No order was placed.')
    return '\n'.join(L)


def reads(path):
    """This wave's entries on the ledger."""
    return [r for r in W25.ledger_doc(path).get('reads', [])
            if r.get('version') == W28_VERSION]


def read_made(path, market):
    return any(r.get('part') == 'market' and r.get('market') == market
               for r in reads(path))


def decision_made(path):
    return any(r.get('part') == 'decide' for r in reads(path))


def record(entry, path):
    doc = W25.ledger_doc(path)
    entry = dict(entry, version=W28_VERSION,
                 at=datetime.datetime.now(datetime.timezone.utc).strftime(
                     '%Y-%m-%dT%H:%M:%SZ'))
    doc.setdefault('reads', []).append(entry)
    try:
        with open(path, 'w') as fh:
            json.dump(doc, fh, indent=1)
    except OSError as exc:
        raise CX.ContextDataError(
            'the ledger %s cannot be written (%s): no result is shown '
            'before the read is on record.' % (os.path.basename(path), exc))
    return len(doc['reads'])


def _main_decide(argv, ledger, out):
    final = '--final' in argv
    files = [a for a in argv[argv.index('--decide') + 1:]
             if not a.startswith('--') and a != out]
    reps = []
    try:
        for f in files:
            with open(f) as fh:
                reps.append(json.load(fh))
        have = {r['market'] for r in reps}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('STOPPED: cannot read the reports (%s). Nothing was decided.'
              % exc)
        return 2
    on_ledger = sorted({r['market'] for r in reads(ledger)
                        if r.get('part') == 'market'})
    missing = [mk for mk in on_ledger if mk not in have]
    never = [mk for mk in MARKETS if mk not in on_ledger and mk not in have]
    if decision_made(ledger):
        print('REFUSED: this wave\'s decision has been made (%s). It is '
              'made once.' % HISTORY_LEDGER)
        return 2
    if missing:
        print('STOPPED: %s was read by this wave and its report is not '
              'given. A market that was read cannot be left out. Nothing '
              'was decided.' % ', '.join(missing))
        return 2
    unread = sorted(h for h in have if h not in on_ledger)
    if unread:
        print('STOPPED: the ledger has no read of %s: its report is not '
              'this wave\'s. Nothing was decided.' % ', '.join(unread))
        return 2
    if not final:
        print('The decision would be made on: %s.' % (
            ', '.join(sorted(have)) or 'nothing'))
        if never:
            print('Not read, and so left out for good: %s.'
                  % ', '.join(never))
        print('It is made ONCE. Nothing was computed. Add --final to make '
              'it.')
        return 0
    rep = decide(reps)
    if not rep['decided']:
        print('STOPPED: %s. Nothing was recorded.' % rep['why'])
        return 2
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
    try:
        n = record(dict(part='decide', markets=sorted(have)), ledger)
    except CX.ContextDataError:
        if out and os.path.exists(out):
            os.remove(out)
        raise
    print(text(rep))
    if out:
        print('\nwave-twenty-eight decision -> %s' % out)
    print('decision recorded (%d entries in %s)' % (n, HISTORY_LEDGER))
    return 0


def main(argv=None, ledger=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    ledger = ledger or os.path.join(HERE, HISTORY_LEDGER)

    def arg(k):
        i = argv.index(k) + 1 if k in argv else len(argv)
        return argv[i] if i < len(argv) else None
    out = arg('--out')
    try:
        if out and not W25.can_write(out):
            print('STOPPED: %s cannot be written (does the folder exist?). '
                  'Nothing was read.' % out)
            return 2
        if '--decide' in argv:
            return _main_decide(argv, ledger, out)
        if argv[0].startswith('--'):
            print(__doc__)
            return 2
        market = (arg('--market') or '').upper()
        if market not in MARKETS:
            print('STOPPED: --market is one of %s.' % ', '.join(MARKETS))
            return 2
        if not out:
            print('STOPPED: give --out <file>: the report holds the '
                  'numbers the decision is made on. Nothing was read.')
            return 2
        if decision_made(ledger):
            print('REFUSED: this wave\'s decision has been made (%s); no '
                  'market is read after it.' % HISTORY_LEDGER)
            return 2
        if read_made(ledger, market):
            print('REFUSED: this wave has read %s (%s). Each market is read '
                  'once.' % (market, HISTORY_LEDGER))
            return 2
        rep = run_market(argv[0], market, '--gaps-ok' in argv)
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
        try:
            n = record(dict(part='market', market=market,
                            first=rep['first_session'],
                            last=rep['last_session'], n=rep['n_trades'],
                            left_out=bool(rep['left_out'])), ledger)
        except CX.ContextDataError:
            os.remove(out)
            raise
    except CX.ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    print(text(rep))
    print('\nwave-twenty-eight report -> %s' % out)
    print('read recorded (%d entries in %s)' % (n, HISTORY_LEDGER))
    return 0


if __name__ == '__main__':
    sys.exit(main())
