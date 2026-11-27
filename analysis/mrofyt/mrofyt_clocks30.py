#!/usr/bin/env python3
"""mrofyt_clocks30.py - MROF-YT-W30-CLOCKS-1.0

MROF_YT_WAVE30_CLOCKS_REGISTRATION.md turned into running code: B
several times a day. Three changes to B, each judged against B itself.

    BS  the same rule on two other clocks: B+10 decides at 10:10,
        10:40, ..., 15:40 and B+20 at 10:20, ..., 15:50. A check that B
        does not hang on the minute it looks at
    BF  B's rule every ten minutes, 10:00 to 15:50
    BT  B on its own clock with timed fills: an order is filled five
        minutes later when the last three five-minute changes ran in
        its direction
    and, never judged: what the next five minutes give back after
    three changes one way, and how often each rule trades

    python3 mrofyt_clocks30.py "<NQ exports>" --market NQ --out w30_nq.json
    python3 mrofyt_clocks30.py "<ES exports>" --market ES --out w30_es.json
    python3 mrofyt_clocks30.py "<RTY exports>" --market RTY --out w30_rty.json
    python3 mrofyt_clocks30.py "<every NQ export>" --later-months
        --out w30_later.json
    python3 mrofyt_clocks30.py --decide w30_nq.json w30_es.json
        w30_rty.json [w30_later.json]
    options: --stamps-tz UTC|ET  --stamps end|start  --gaps-ok (markets)

Each read is made once and recorded before any result is shown. B, its
bounds, its volatility and its sizing are wave twenty-four's own; costs
and the reader are wave twenty-five's. Read-only; no order is placed.
"""
import collections
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_improve26 as W26       # noqa: E402
import mrofyt_markets28 as W28       # noqa: E402
import mrofyt_screen15 as S          # noqa: E402

W30_VERSION = 'MROF-YT-W30-CLOCKS-1.0'
REGISTRATION = 'MROF_YT_WAVE30_CLOCKS_REGISTRATION.md'
HISTORY_LEDGER = W25.HISTORY_LEDGER
N = S.N_MIN
MARKETS = ('NQ', 'ES', 'RTY')
JUDGED_ON = ('ES', 'RTY')            # "better than B"

STEP = 5                             # minutes of a change c(m)
CLOCKS = collections.OrderedDict((   # minutes after 09:30
    ('B', tuple(range(30, 361, 30))),            # 10:00 ... 15:30
    ('B+10', tuple(range(40, 371, 30))),         # 10:10 ... 15:40
    ('B+20', tuple(range(50, 381, 30))),         # 10:20 ... 15:50
    ('BF', tuple(range(30, 381, 10)))))          # every ten, to 15:50
SHIFTED = ('B+10', 'B+20')
STREAK, WAIT = 3, 5                  # BT
CHANGES = ('BF', 'BT')
T_BAR = 2.5
NAMES = collections.OrderedDict((
    ('B', 'B unchanged'), ('B+10', 'ten minutes later'),
    ('B+20', 'twenty minutes later'), ('BF', 'every ten minutes'),
    ('BT', 'timed fills')))
BESIDE = collections.OrderedDict((   # reported, never judged
    ('BF15', ('every 15 minutes', tuple(range(30, 376, 15)), 0, WAIT)),
    ('BF5', ('every 5 minutes', tuple(range(30, 386, 5)), 0, WAIT)),
    ('BT2', ('two changes in a row', CLOCKS['B'], 2, WAIT)),
    ('BT4', ('four changes in a row', CLOCKS['B'], 4, WAIT)),
    ('BT10', ('a wait of 10 minutes', CLOCKS['B'], STREAK, 10))))
GIVE_FROM, GIVE_TO = 15, 380         # 09:45 ... 15:50
GIVE_STREAKS = (2, 3, 4)


# ---------------------------------------------------------------------
# section 2: B at any clock, with or without timed fills
# ---------------------------------------------------------------------
def change(d, m):
    """c(m): the five-minute change that ends at minute m."""
    return d.p(m) - d.p(m - STEP)


def ran(d, m, streak):
    """The sign that the last `streak` five-minute changes at m share;
    0 when they do not."""
    g = S.sign(change(d, m))
    if g and all(S.sign(change(d, m - STEP * k)) == g
                 for k in range(1, streak)):
        return g
    return 0


def day(d, sigma, times, streak=0, wait=WAIT):
    """(gross, cost, position changes, fills moved) of B's rule on one
    session at the minutes `times`, in units of the open. With `streak`,
    an order is filled `wait` minutes later when the last `streak`
    five-minute changes ran in its direction. With no streak and B's
    own minutes this is wave twenty-four's day_b, step for step."""
    times = tuple(times)
    if streak and any(b - a <= wait for a, b in zip(times, times[1:])):
        raise ValueError('a fill cannot be moved past the next decision')
    pos, pts, cost, n, late = 0, 0.0, 0.0, 0, 0
    last, held = None, None
    for j in times + (N,):
        if held is not None:             # the moved fill comes first
            at, to = held
            p = d.p(at)
            pts += pos * (p - last)
            pos, last, held = to, p, None
        p = d.p(j)
        if last is not None:
            pts += pos * (p - last)
        want = 0 if j == N else W26.b_want(d, sigma, j)
        if want != pos:
            cost += S.SIDE * abs(want - pos)
            n += 1
            side = 1 if want > pos else -1
            if streak and j != N and j + wait < N and \
                    ran(d, j, streak) == side:
                held = (j + wait, want)
                late += 1
            else:
                pos = want
        last = p
    return pts / d.o, cost / d.o, n, late


def rule(days, order, bi, times, streak=0, wait=WAIT):
    """B's rule at `times`: one result a day, on days with a trade,
    sized as B."""
    trades = []
    for s in order:
        if s not in bi:
            continue
        sigma, vol = bi[s]
        gross, cost, n, late = day(days[s], sigma, times, streak, wait)
        if n:
            trades.append(S._trade(s, gross, cost, changes=n, late=late,
                                   lev=min(S.B_VOL_TARGET / vol,
                                           S.B_MAX_LEV)))
    return trades


def all_rules(days, order, bi):
    """{name: trades} of B, the two other clocks, BF and BT."""
    out = collections.OrderedDict(
        (name, rule(days, order, bi, times))
        for name, times in CLOCKS.items())
    out['BT'] = rule(days, order, bi, CLOCKS['B'], STREAK, WAIT)
    return out


# ---------------------------------------------------------------------
# section 3: reported, never judged
# ---------------------------------------------------------------------
def give_back(days, order, streak):
    """After `streak` five-minute changes one way: the next change taken
    against them, at every five-minute mark from 09:45 (or the first
    mark that has the changes) to 15:50."""
    first = max(GIVE_FROM, STEP * streak)
    marks = events = 0
    pts, bps, per = [], [], []
    for s in order:
        d = days[s]
        tot = 0.0
        for m in range(first, GIVE_TO + 1, STEP):
            marks += 1
            g = ran(d, m, streak)
            if not g:
                continue
            events += 1
            x = -g * change(d, m + STEP)
            pts.append((s, x))
            bps.append((s, 1e4 * x / d.p(m)))
            tot += 1e4 * x / d.p(m)
        per.append((s, tot))
    out = dict(streak=streak, marks=marks, events=events,
               share=round(events / float(marks), 4) if marks else None,
               points=None, bp=None, after_round_trip=None, halves={},
               weekly_t=None)
    if events:
        mp = S.mean([x for _s, x in pts])
        out.update(points=round(mp, 4),
                   bp=round(S.mean([x for _s, x in bps]), 4),
                   after_round_trip=round(mp - S.RT, 4))
        for h in S.HALVES:
            v = [x for s, x in pts if S.half_of(s) == h]
            out['halves'][h] = dict(n=len(v),
                                    points=round(S.mean(v), 4) if v else None)
        st = W28.stats(per)
        out['weekly_t'] = None if st['t'] is None else round(st['t'], 3)
    return out


def session_x(sessions, trades):
    """[(session, net basis points in B's sizing)]: 0 on a session
    without a trade."""
    by = dict(S.nets('B', trades, {}))
    return [(s, by.get(s, 0.0)) for s in sessions]


def paired(x_change, x_b):
    """The change's result minus B's, session by session."""
    b = dict(x_b)
    return [(s, x - b[s]) for s, x in x_change]


def _stats(pairs):
    st = W28.stats(pairs)
    return dict(
        sessions=st['n'], differ=sum(1 for _s, x in pairs if x != 0.0),
        mean=None if st['mean'] is None else round(st['mean'], 5),
        t=None if st['t'] is None else round(st['t'], 3), weeks=st['weeks'],
        halves={h: None if v is None else round(v, 5)
                for h, v in st['halves'].items()})


def _judged(name, trades, sessions):
    pairs = S.nets('B', trades, {})
    res = S.judge(pairs)
    n = len(trades)
    res.update(
        rule=name,
        per_session=round(sum(x for _s, x in pairs) / len(sessions), 4)
        if sessions else None,
        changes_a_day=round(sum(t['changes'] for t in trades) / float(n), 3)
        if n else None,
        cost_a_day_bp=round(S.mean([1e4 * t['cost'] * t['lev']
                                    for t in trades]), 4) if n else None,
        moved=sum(t['late'] for t in trades))
    return res


def judge_all(days, order, chain):
    """One market's rules, the paired differences and what is reported
    beside them."""
    bi = W26.b_inputs(days, order, chain)
    sessions = [s for s in order if s in bi]
    tr = all_rules(days, order, bi)
    rules = collections.OrderedDict()
    for name, trades in tr.items():
        rules[name] = _judged(name, trades, sessions)
        rules[name]['name'] = NAMES[name]
    xs = {name: session_x(sessions, trades) for name, trades in tr.items()}
    pair = collections.OrderedDict()
    for name in CHANGES:
        d = paired(xs[name], xs['B'])
        pair[name] = dict(_stats(d), series={s: round(x, 6)
                                             for s, x in d if x != 0.0})
    beside = collections.OrderedDict()
    for key, (label, times, streak, wait) in BESIDE.items():
        trades = rule(days, order, bi, times, streak, wait)
        j = _judged(key, trades, sessions)
        d = _stats(paired(session_x(sessions, trades), xs['B']))
        beside[key] = dict(
            name=label, status=j['status'], n=j['both']['n'],
            per_session=j['per_session'], changes_a_day=j['changes_a_day'],
            cost_a_day_bp=j['cost_a_day_bp'], moved=j['moved'],
            against_b=dict(mean=d['mean'], t=d['t']))
    three = [(s, (a + b + c) / 3.0) for (s, a), (_s, b), (_t, c) in zip(
        xs['B'], xs['B+10'], xs['B+20'])]
    tog = dict(sessions=len(sessions))
    if len(sessions) > 1:
        tog.update(
            mean=round(S.mean([x for _s, x in three]), 4),
            sd=round(S.stdev([x for _s, x in three]), 4),
            b_mean=round(S.mean([x for _s, x in xs['B']]), 4),
            b_sd=round(S.stdev([x for _s, x in xs['B']]), 4),
            days_with_a_trade=sum(1 for _s, x in three if x != 0.0))
    return dict(
        rules=rules, paired=pair, beside=beside, three_clocks=tog,
        eligible=sessions,
        give_back=collections.OrderedDict(
            (str(k), give_back(days, order, k)) for k in GIVE_STREAKS))


# ---------------------------------------------------------------------
# the reads
# ---------------------------------------------------------------------
def run_market(path, market, stamps_tz='UTC', stamps='end', gaps_ok=False):
    if market not in MARKETS:
        raise CX.ContextDataError('--market is one of %s'
                                  % ', '.join(MARKETS))
    rd, chk = W25.read(path, market, stamps_tz, stamps)
    days, order, chain = S.build(rd)
    if len(order) < W25.MIN_SESSIONS:
        raise CX.ContextDataError(
            'only %d usable %s sessions: this needs years of minute bars. '
            'Nothing was computed.' % (len(order), market))
    g = W25.gaps(chain)
    if g and not gaps_ok:
        raise CX.ContextDataError(
            'the %s exports have no cash session between %s: a contract was '
            'not exported. Nothing was computed. Export it and run again; '
            'if the feed has no bars for those days, add --gaps-ok.'
            % (market, W25._gap_text(g)))
    with W25.costs(market) as c:
        res = judge_all(days, order, chain)
    rep = dict(
        wave30=W30_VERSION, registration=REGISTRATION, part='market',
        market=market, files=len(rd.files), stamp_check=chk,
        sessions=len(order), first_session=order[0],
        last_session=order[-1], gaps=[list(x) for x in g],
        costs=dict(tick=c['tick'], round_trip=c['rt'], stop=c['stop']))
    rep.update(res)
    rep['n_trades'] = sum(v['both']['n'] for v in rep['rules'].values())
    return rep


def run_later(path, stamps_tz='UTC', stamps='end'):
    rd, chk = W25.read(path, 'NQ', stamps_tz, stamps, later=True)
    last_read = max(s for (_c, s) in rd.days)
    if last_read >= W25.LATER_REFUSE_FROM:
        raise CX.ContextDataError('a session from 2026-11-14 on was read '
                                  '(%s). Nothing was computed.' % last_read)
    days, order, chain = S.build(rd)
    before = sum(1 for r in chain if r['session'] < W25.LATER_FROM)
    inside = [r for r in chain if W25.in_window(r['session'])]
    if before < W25.HISTORY_MIN_DAYS or len(inside) < W25.LATER_MIN_DAYS \
            or W25.gaps(chain):
        raise CX.ContextDataError(
            'these exports do not hold every NQ contract to 2026-11-13 '
            '(%d trading days before 2026-07-01, %d of the %d in the window, '
            'holes: %s). Nothing was computed, and the read was not used '
            'up.' % (before, len(inside), W25.LATER_DAYS,
                     W25._gap_text(W25.gaps(chain)) or 'none'))
    rules = collections.OrderedDict()
    with W25.costs('NQ'):
        bi = W26.b_inputs(days, order, chain)
        tr = all_rules(days, order, bi)
        for name in SHIFTED + CHANGES:
            inw = [t for t in tr[name] if W25.in_window(t['session'])]
            res = W25.window_verdict([x for _s, x in S.nets('B', inw, {})])
            res.update(rule=name, name=NAMES[name])
            rules[name] = res
    return dict(
        wave30=W30_VERSION, registration=REGISTRATION, part='2b',
        market='NQ', stamp_check=chk, window=[W25.LATER_FROM, W25.LATER_TO],
        trading_days=len(inside), first_session=inside[0]['session'],
        last_session=inside[-1]['session'], last_session_read=last_read,
        rules=rules, n_trades=sum(v['n'] for v in rules.values()),
        collapsed=[r for r, v in rules.items()
                   if v['status'] == 'COLLAPSED'])


def pooled(reps, name):
    """The paired difference over ES and RTY together: a session's D is
    the average of the markets that have the session."""
    by = collections.defaultdict(list)
    for r in reps:
        ser = r['paired'][name]['series']
        for s in r['eligible']:
            by[s].append(ser.get(s, 0.0))
    return [(s, S.mean(v)) for s, v in sorted(by.items())]


def decide(reps):
    """The verdicts from the three market reports and, when it is
    given, the later months."""
    for r in reps:
        if r.get('wave30') != W30_VERSION:
            raise CX.ContextDataError('a report is not one of %s. Nothing '
                                      'was decided.' % W30_VERSION)
    by = {r['market']: r for r in reps if r.get('part') == 'market'}
    later = [r for r in reps if r.get('part') == '2b']
    missing = [m for m in MARKETS if m not in by]
    if missing or len(by) + len(later) != len(reps) or len(later) > 1:
        raise CX.ContextDataError(
            'the reports of %s are needed, each once (and at most one of the '
            'later months). Nothing was decided.' % ', '.join(
                missing or MARKETS))
    ok = {m: {n: by[m]['rules'][n]['status'] == 'PASS'
              for n in by[m]['rules']} for m in MARKETS}
    both = {m: all(ok[m][n] for n in SHIFTED) for m in MARKETS}
    if both['NQ'] and all(both[m] for m in JUDGED_ON if ok[m]['B']):
        clock = 'ROBUST'
    elif not any(ok['NQ'][n] for n in SHIFTED):
        clock = 'FRAGILE'
    else:
        clock = 'MIXED'
    collapsed = later[0]['collapsed'] if later else []
    changes = collections.OrderedDict()
    for name in CHANGES:
        passes = {m: ok[m][name] for m in MARKETS}
        means = {m: by[m]['paired'][name]['mean'] for m in JUDGED_ON}
        st = W28.stats(pooled([by[m] for m in JUDGED_ON], name))
        better = all(passes.values()) and \
            all(means[m] is not None and means[m] > 0 for m in JUDGED_ON) \
            and st['mean'] is not None and st['mean'] > 0 and \
            st['t'] is not None and st['t'] >= T_BAR
        status = 'BETTER THAN B' if better else 'NOT BETTER'
        if better and name in collapsed:
            status = 'NOT BETTER (collapsed in the later months)'
        changes[name] = dict(
            passes=passes, mean_d=means,
            pooled=dict(mean=None if st['mean'] is None
                        else round(st['mean'], 5),
                        t=None if st['t'] is None else round(st['t'], 3),
                        weeks=st['weeks']),
            status=status)
    b_ok = all(ok[m]['B'] for m in MARKETS)
    notes = []
    if not b_ok:
        notes.append('B itself did not pass on every market here: no change '
                     'can go on until B passes wave twenty-five.')
    if not later:
        notes.append('The later months are still to be read: a change that '
                     'is COLLAPSED there does not go on.')
    return dict(
        wave30=W30_VERSION, part='decide', clock=clock,
        clocks={m: {n: ok[m][n] for n in ('B',) + SHIFTED}
                for m in MARKETS},
        changes=changes,
        goes_on=[n for n in CHANGES
                 if changes[n]['status'] == 'BETTER THAN B'],
        b_passes_everywhere=b_ok, later_read=bool(later), notes=notes)


# ---------------------------------------------------------------------
# text, ledger, command
# ---------------------------------------------------------------------
def _f(x, fmt='%+.2f'):
    return 'n/a' if x is None else fmt % x


def text(rep):
    L = []
    if rep['part'] == 'market':
        L += ['%s  %s  %d sessions (%s .. %s)' % (
            rep['wave30'], rep['market'], rep['sessions'],
            rep['first_session'], rep['last_session']),
            'B and three changes to it, by wave twenty-four\'s bar (bp of '
            'capital, B\'s sizing).', '']
        for name, v in rep['rules'].items():
            L.append('%-4s %s' % (name, v['name']))
            for h in S.HALVES:
                r = v['halves'][h]
                L.append('    %s  days %5d  won %2.0f%%  net %+8.2f  without '
                         'best month %+8.2f  %s' % (
                             h, r['n'], 100 * r.get('won', 0),
                             r.get('net') or 0.0,
                             r.get('net_without_best') or 0.0,
                             'ok' if r['ok'] else 'no') if r['n'] else
                         '    %s  days     0' % h)
            L.append('    %s%s   a session on average %s   orders a day %s, '
                     'costing %s bp%s' % (
                         v['status'], ' (strong)' if v['strong'] else '',
                         _f(v['per_session'], '%+.3f'),
                         _f(v['changes_a_day'], '%.2f'),
                         _f(v['cost_a_day_bp'], '%.2f'),
                         '   fills moved %d' % v['moved']
                         if v['moved'] else ''))
            L.append('')
        L.append('Against B, session by session (the change minus B, bp):')
        for name, v in rep['paired'].items():
            L.append('  %-4s mean %s   weekly t %s   sessions that differ %d'
                     % (name, _f(v['mean'], '%+.4f'), _f(v['t']),
                        v['differ']))
        tc = rep['three_clocks']
        if 'mean' in tc:
            L += ['', 'The three clocks together (reported): mean %+.3f, '
                  'standard deviation %.2f; B alone: mean %+.3f, standard '
                  'deviation %.2f' % (tc['mean'], tc['sd'], tc['b_mean'],
                                      tc['b_sd'])]
        L += ['', 'Beside (reported, never judged):']
        for key, v in rep['beside'].items():
            L.append('  %-5s %-22s %s  a session %s  orders a day %s  '
                     'against B %s (t %s)' % (
                         key, v['name'], v['status'],
                         _f(v['per_session'], '%+.3f'),
                         _f(v['changes_a_day'], '%.2f'),
                         _f(v['against_b']['mean'], '%+.4f'),
                         _f(v['against_b']['t'])))
        L += ['', 'The fast give-back (reported, never judged): after k '
              'five-minute changes one way, the next one taken against '
              'them:']
        for k, v in rep['give_back'].items():
            L.append('  k = %s: at %s %% of the marks; %s points on average '
                     '(%s bp, weekly t %s); after a round trip of %.2f: %s '
                     'points' % (
                         k, _f(100 * v['share'] if v['share'] is not None
                               else None, '%.1f'), _f(v['points'], '%+.3f'),
                         _f(v['bp'], '%+.3f'), _f(v['weekly_t']),
                         rep['costs']['round_trip'],
                         _f(v['after_round_trip'], '%+.3f')))
    elif rep['part'] == '2b':
        L += ['*** LATER MONTHS: NQ 2026-07-01 to 2026-11-13, once (B+10, '
              'B+20, BF, BT). ***', '']
        for name, v in rep['rules'].items():
            L.append('%-4s %s: days %d%s  %s' % (
                name, v['name'], v['n'],
                '  net %+.2f' % v['net'] if v['n'] else '', v['status']))
        L.append('COLLAPSED: %s' % (', '.join(rep['collapsed']) or 'none'))
    else:
        L.append('THE CLOCK (BS): %s' % rep['clock'])
        for m, v in rep['clocks'].items():
            L.append('  %-3s passes: %s' % (m, ', '.join(
                n for n, ok in v.items() if ok) or 'none'))
        for name, v in rep['changes'].items():
            L.append('%-2s %s: passes the bar on %s; against B on ES %s, on '
                     'RTY %s; together %s with a weekly t of %s -> %s' % (
                         name, NAMES[name],
                         ', '.join(m for m, ok in v['passes'].items() if ok)
                         or 'none', _f(v['mean_d']['ES'], '%+.4f'),
                         _f(v['mean_d']['RTY'], '%+.4f'),
                         _f(v['pooled']['mean'], '%+.4f'),
                         _f(v['pooled']['t']), v['status']))
        L.append('GOES ON: %s' % (', '.join(rep['goes_on']) or 'none'))
        L += rep['notes']
    L.append('Minute bars, costs charged; not P&L. No order was placed.')
    return '\n'.join(L)


def read_made(path, part, market):
    return any(r.get('version') == W30_VERSION and r.get('part') == part
               and r.get('market') == market
               for r in W25.ledger_doc(path).get('reads', []))


def record_read(rep, path):
    doc = W25.ledger_doc(path)
    doc.setdefault('reads', []).append(dict(
        version=W30_VERSION, part=rep['part'], market=rep['market'],
        first=rep['first_session'], last=rep['last_session'],
        n=rep['n_trades'],
        at=datetime.datetime.now(datetime.timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%SZ')))
    try:
        with open(path, 'w') as fh:
            json.dump(doc, fh, indent=1)
    except OSError as exc:
        raise CX.ContextDataError(
            'the ledger %s cannot be written (%s): no result is shown '
            'before the read is on record.' % (os.path.basename(path), exc))
    return len(doc['reads'])


def main(argv=None, ledger=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2

    def arg(k):
        i = argv.index(k) + 1 if k in argv else len(argv)
        return argv[i] if i < len(argv) else None
    if '--decide' in argv:
        files = argv[argv.index('--decide') + 1:]
        try:
            reps = []
            for f in files:
                with open(f) as fh:
                    reps.append(json.load(fh))
            rep = decide(reps)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print('STOPPED: cannot read the reports (%s).' % exc)
            return 2
        except CX.ContextDataError as exc:
            print('STOPPED: %s' % exc)
            return 2
        print(text(rep))
        return 0
    if argv[0].startswith('--'):
        print(__doc__)
        return 2
    stz = (arg('--stamps-tz') or 'UTC').upper()
    stp = (arg('--stamps') or 'end').lower()
    later, market = '--later-months' in argv, (arg('--market') or '').upper()
    ledger = ledger or os.path.join(HERE, HISTORY_LEDGER)
    if later == bool(market):
        print('STOPPED: give either --market NQ|ES|RTY or --later-months.')
        return 2
    if market and market not in MARKETS:
        print('STOPPED: --market is one of %s.' % ', '.join(MARKETS))
        return 2
    out = arg('--out')
    if out and not W25.can_write(out):
        print('STOPPED: %s cannot be written (does the folder exist?). '
              'Nothing was read.' % out)
        return 2
    part, mk = ('2b', 'NQ') if later else ('market', market)
    try:
        if read_made(ledger, part, mk):
            print('REFUSED: this wave has read %s (%s). Each read is made '
                  'once.' % ('the later months' if later else mk,
                             HISTORY_LEDGER))
            return 2
        rep = run_later(argv[0], stz, stp) if later else run_market(
            argv[0], market, stz, stp, '--gaps-ok' in argv)
        n = record_read(rep, ledger)
    except CX.ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
    print(text(rep))
    if out:
        print('\nwave-thirty report -> %s' % out)
    print('read recorded (%d read(s) in %s)' % (n, HISTORY_LEDGER))
    return 0


if __name__ == '__main__':
    sys.exit(main())
