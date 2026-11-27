#!/usr/bin/env python3
"""mrofyt_lateday32.py - MROF-YT-W32-LATEDAY-1.0

MROF_YT_WAVE32_LATEDAY_REGISTRATION.md turned into running code: when
in the day B earns, and for how long.

    the legs   B's result on each of its twelve half hours, 10:00-10:30
               to 15:30-16:00, by time of day and by the age of the
               position (reported)
    written    LATE-HEAVY: the four legs from 14:00 earn more than half
    down       of B's result;  NQ-MORE: they earn more on NQ than on ES
               and on RTY
    BL         B's rule from 14:00 only, judged against B by its Sharpe
               and its fall ratio on ES and RTY

    python3 mrofyt_lateday32.py "<NQ exports>" --market NQ --out w32_nq.json
    python3 mrofyt_lateday32.py "<ES exports>" --market ES --out w32_es.json
    python3 mrofyt_lateday32.py "<RTY exports>" --market RTY --out w32_rty.json
    python3 mrofyt_lateday32.py "<NQ exports>" --later-months
                                         --out w32_later.json
    python3 mrofyt_lateday32.py --decide w32_nq.json w32_es.json w32_rty.json
                                         [w32_later.json]
    options: --stamps-tz UTC|ET  --stamps end|start  --gaps-ok

Each read is made once and recorded before any result is shown. B, its
sizing, the reader and the costs are waves twenty-four to twenty-six's
own. Read-only; no order is placed.
"""
import collections
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_clocks30 as C30        # noqa: E402
import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_improve26 as W26       # noqa: E402
import mrofyt_markets28 as W28       # noqa: E402
import mrofyt_screen15 as S          # noqa: E402

W32_VERSION = 'MROF-YT-W32-LATEDAY-1.0'
REGISTRATION = 'MROF_YT_WAVE32_LATEDAY_REGISTRATION.md'
HISTORY_LEDGER = W25.HISTORY_LEDGER
N = S.N_MIN
MARKETS = ('NQ', 'ES', 'RTY')
JUDGED_ON = ('ES', 'RTY')
LATE_FROM = 270                      # 14:00, minutes after 09:30
BL_TIMES = tuple(j for j in S.B_TIMES if j >= LATE_FROM)   # 14:00..15:30
GROUPS = ('EARLY', 'LATE')
AGES = ('1', '2', '3-4', '5+')
HEAVY = 0.5                          # LATE-HEAVY: more than half
SHARPE_GAIN = 1.05
RULES = collections.OrderedDict((('B', tuple(S.B_TIMES)),
                                 ('BL', BL_TIMES)))


def clock(j):
    """'10:00' for minute 30 after 09:30."""
    m = 9 * 60 + 30 + j
    return '%02d:%02d' % (m // 60, m % 60)


def group_of(start):
    return 'LATE' if start >= LATE_FROM else 'EARLY'


def age_of(n):
    return '1' if n == 1 else '2' if n == 2 else '3-4' if n <= 4 else '5+'


# ---------------------------------------------------------------------
# section 2: the legs of B
# ---------------------------------------------------------------------
def legs(d, sigma):
    """B's twelve legs on one session: [(start, position, age, gross,
    cost)] in units of the open. An order's cost is split: what closes
    the old position goes to the leg that ends at the order, what opens
    the new one to the leg that starts at it. The legs add up to wave
    twenty-four's day_b."""
    out, pos, age = [], 0, 0
    times = tuple(S.B_TIMES)
    for k, j in enumerate(times):
        want = W26.b_want(d, sigma, j)
        opened = 0.0
        if want != pos:
            if out:
                out[-1][4] += S.SIDE * abs(pos)
            opened = S.SIDE * abs(want)
            pos, age = want, 0
        if pos:
            age += 1
        end = times[k + 1] if k + 1 < len(times) else N
        out.append([j, pos, age if pos else 0,
                    pos * (d.p(end) - d.p(j)), opened])
    out[-1][4] += S.SIDE * abs(pos)              # flat at 16:00
    return [(j, p, a, g / d.o, c / d.o) for j, p, a, g, c in out]


def leg_table(days, order, bi):
    """{session: [(start, position, age, x)]}: x = the leg's net basis
    points of capital in B's sizing."""
    out = collections.OrderedDict()
    for s in order:
        if s not in bi:
            continue
        sigma, vol = bi[s]
        lev = min(S.B_VOL_TARGET / vol, S.B_MAX_LEV)
        out[s] = [(j, p, a, 1e4 * lev * (g - c))
                  for j, p, a, g, c in legs(days[s], sigma)]
    return out


def _row(pairs, held, total, legs_held=None):
    st = W28.stats(pairs)
    part = sum(x for _s, x in pairs)
    row = dict(held=held,
               mean=None if st['mean'] is None else round(st['mean'], 5),
               share=round(part / total, 4) if total > 0 else None,
               t=None if st['t'] is None else round(st['t'], 3))
    if legs_held is not None:
        row.update(legs_held=legs_held,
                   per_leg=round(part / legs_held, 5) if legs_held else None)
    return row


def summarize(table):
    """The legs by time of day, by group and by age; LATE less half of
    EARLY; LATE-HEAVY."""
    sessions = list(table)
    total = sum(x for rows in table.values() for _j, _p, _a, x in rows)
    by_leg = collections.OrderedDict()
    for k, j in enumerate(S.B_TIMES):
        by_leg[clock(j)] = _row(
            [(s, table[s][k][3]) for s in sessions],
            sum(1 for s in sessions if table[s][k][1]), total)
    groups, gx = collections.OrderedDict(), {}
    for g in GROUPS:
        gx[g] = [(s, sum(x for j, _p, _a, x in table[s] if group_of(j) == g))
                 for s in sessions]
        groups[g] = _row(
            gx[g], sum(1 for s in sessions if any(
                p for j, p, _a, _x in table[s] if group_of(j) == g)),
            total, sum(1 for s in sessions for j, p, _a, _x in table[s]
                       if p and group_of(j) == g))
    ages = collections.OrderedDict()
    for a in AGES:
        ages[a] = _row(
            [(s, sum(x for _j, p, n, x in table[s]
                     if p and age_of(n) == a)) for s in sessions],
            sum(1 for s in sessions if any(
                p and age_of(n) == a for _j, p, n, _x in table[s])),
            total, sum(1 for s in sessions for _j, p, n, _x in table[s]
                       if p and age_of(n) == a))
    early = dict(gx['EARLY'])
    st = W28.stats([(s, x - early[s] / 2.0) for s, x in gx['LATE']])
    late = sum(x for _s, x in gx['LATE'])
    return dict(
        sessions=len(sessions), total=round(total, 4),
        per_session=round(total / len(sessions), 5) if sessions else None,
        legs=by_leg, groups=groups, ages=ages,
        late_less_half_early=dict(
            mean=None if st['mean'] is None else round(st['mean'], 5),
            t=None if st['t'] is None else round(st['t'], 3)),
        late_heavy=bool(total > 0 and late > HEAVY * total)
        if sessions else None)


# ---------------------------------------------------------------------
# sections 4 and 5: BL, the Sharpe and the fall
# ---------------------------------------------------------------------
def perf(pairs):
    """dict(sessions, mean, sd, sharpe, fall, fall_ratio): wave
    thirty-one's numbers."""
    v = [x for _s, x in pairs]
    out = dict(sessions=len(v), mean=None, sd=None, sharpe=None, fall=None,
               fall_ratio=None)
    if len(v) < 2:
        return out
    m, sd = S.mean(v), S.stdev(v)
    cum = top = fall = 0.0
    for x in v:
        cum += x
        top = max(top, cum)
        fall = max(fall, top - cum)
    out.update(mean=round(m, 5), sd=round(sd, 5),
               sharpe=round(m / sd, 6) if sd > 0 else None,
               fall=round(fall, 4),
               fall_ratio=round(fall / m, 4) if m > 0 else None)
    return out


def both_rules(days, order, bi):
    """{rule: trades} of B and of BL, by wave thirty's rule()."""
    return collections.OrderedDict(
        (name, C30.rule(days, order, bi, times))
        for name, times in RULES.items())


def judge_all(days, order, chain):
    bi = W26.b_inputs(days, order, chain)
    sessions = [s for s in order if s in bi]
    res = summarize(leg_table(days, order, bi))
    rules, pf = collections.OrderedDict(), collections.OrderedDict()
    for name, trades in both_rules(days, order, bi).items():
        rules[name] = C30._judged(name, trades, sessions)
        pf[name] = perf(C30.session_x(sessions, trades))
    res.update(rules=rules, perf=pf)
    return res


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
        wave32=W32_VERSION, registration=REGISTRATION, part='market',
        market=market, files=len(rd.files), stamp_check=chk,
        first_session=order[0], last_session=order[-1],
        gaps=[list(x) for x in g],
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
    with W25.costs('NQ'):
        bi = W26.b_inputs(days, order, chain)
        table = collections.OrderedDict(
            (s, rows) for s, rows in leg_table(days, order, bi).items()
            if W25.in_window(s))
        res = summarize(table)
        verdicts = collections.OrderedDict()
        for name, trades in both_rules(days, order, bi).items():
            inw = [t for t in trades if W25.in_window(t['session'])]
            verdicts[name] = W25.window_verdict(
                [x for _s, x in S.nets('B', inw, {})])
    rep = dict(
        wave32=W32_VERSION, registration=REGISTRATION, part='2b',
        market='NQ', stamp_check=chk, window=[W25.LATER_FROM, W25.LATER_TO],
        trading_days=len(inside), first_session=inside[0]['session'],
        last_session=inside[-1]['session'], last_session_read=last_read,
        rules=verdicts, n_trades=sum(v['n'] for v in verdicts.values()),
        collapsed=[r for r, v in verdicts.items()
                   if v['status'] == 'COLLAPSED'])
    rep.update(res)
    return rep


# ---------------------------------------------------------------------
# section 5: the verdict
# ---------------------------------------------------------------------
def gains(rep):
    """Whether, on one market, B's Sharpe is above 0, BL's is at least
    5 % higher and BL's fall ratio is lower."""
    b, x = rep['perf']['B'], rep['perf']['BL']
    return bool(
        b['sharpe'] is not None and b['sharpe'] > 0 and
        x['sharpe'] is not None and
        x['sharpe'] >= SHARPE_GAIN * b['sharpe'] and
        b['fall_ratio'] is not None and x['fall_ratio'] is not None and
        x['fall_ratio'] < b['fall_ratio'])


def decide(reps):
    """The two statements and BL's verdict from the three market
    reports and, when it is given, the later months."""
    for r in reps:
        if r.get('wave32') != W32_VERSION:
            raise CX.ContextDataError('a report is not one of %s. Nothing '
                                      'was decided.' % W32_VERSION)
    by = {r['market']: r for r in reps if r.get('part') == 'market'}
    later = [r for r in reps if r.get('part') == '2b']
    missing = [m for m in MARKETS if m not in by]
    if missing or len(by) + len(later) != len(reps) or len(later) > 1:
        raise CX.ContextDataError(
            'the reports of %s are needed, each once (and at most one of the '
            'later months). Nothing was decided.' % ', '.join(
                missing or MARKETS))
    heavy = collections.OrderedDict((m, by[m]['late_heavy'])
                                    for m in MARKETS)
    late = collections.OrderedDict(
        (m, by[m]['groups']['LATE']['mean']) for m in MARKETS)
    nq_more = all(late[m] is not None for m in MARKETS) and all(
        late['NQ'] > late[m] for m in JUDGED_ON)
    passes = collections.OrderedDict(
        (m, by[m]['rules']['BL']['status'] == 'PASS') for m in MARKETS)
    gain = collections.OrderedDict((m, gains(by[m])) for m in JUDGED_ON)
    better = all(passes.values()) and all(gain.values())
    collapsed = bool(later) and 'BL' in later[0]['collapsed']
    status = 'BETTER THAN B' if better else 'NOT BETTER'
    if better and collapsed:
        status = 'NOT BETTER (collapsed in the later months)'
    notes = []
    if better and not later:
        notes.append('The later months are still to be read: BL does not go '
                     'on if it is COLLAPSED there.')
    if status == 'BETTER THAN B':
        notes.append("BL takes B's place only if B itself passes wave "
                     'twenty-five.')
    return dict(
        wave32=W32_VERSION, part='decide',
        late_heavy=heavy, late_heavy_everywhere=all(
            bool(v) for v in heavy.values()),
        late_mean=late, nq_more=bool(nq_more),
        later_late_heavy=later[0]['late_heavy'] if later else None,
        bl=dict(passes=passes, gains=gain, status=status,
                sharpe={m: dict(B=by[m]['perf']['B']['sharpe'],
                                BL=by[m]['perf']['BL']['sharpe'])
                        for m in MARKETS},
                fall_ratio={m: dict(B=by[m]['perf']['B']['fall_ratio'],
                                    BL=by[m]['perf']['BL']['fall_ratio'])
                            for m in MARKETS}),
        later_read=bool(later), notes=notes)


# ---------------------------------------------------------------------
# text, ledger, command
# ---------------------------------------------------------------------
def _f(x, fmt='%+.3f'):
    return 'n/a' if x is None else fmt % x


def _pct(x):
    return 'n/a' if x is None else '%.0f%%' % (100.0 * x)


def _legs_text(rep):
    L = ['  B\'s whole result: %s bp a session over %d sessions' % (
        _f(rep['per_session']), rep['sessions']), '',
        '  leg from   in a position   mean bp   share   weekly t']
    for name, v in rep['legs'].items():
        L.append('  %-9s  %13d  %8s  %6s  %9s' % (
            name, v['held'], _f(v['mean']), _pct(v['share']),
            _f(v['t'], '%+.2f')))
    L.append('')
    for g, v in rep['groups'].items():
        L.append('  %-5s (%s)  mean %s bp  share %s  t %s  legs held %d' % (
            g, '10:00-14:00' if g == 'EARLY' else '14:00-16:00',
            _f(v['mean']), _pct(v['share']), _f(v['t'], '%+.2f'),
            v['legs_held']))
    d = rep['late_less_half_early']
    L += ['  LATE less half of EARLY: %s bp a session, weekly t %s' % (
        _f(d['mean']), _f(d['t'], '%+.2f')),
        '  LATE-HEAVY (the late legs earn more than half): %s' % (
            'n/a' if rep['late_heavy'] is None else
            'HELD' if rep['late_heavy'] else 'NOT HELD'), '',
        '  by the age of the position (half hours since it was set):',
        '  age    sessions  legs held   mean bp   bp a leg   share   '
        'weekly t']
    for a, v in rep['ages'].items():
        L.append('  %-5s  %8d  %9d  %8s  %9s  %6s  %9s' % (
            a, v['held'], v['legs_held'], _f(v['mean']), _f(v['per_leg']),
            _pct(v['share']), _f(v['t'], '%+.2f')))
    return L


def text(rep):
    L = []
    if rep['part'] == 'market':
        L += ['%s  %s  (%s .. %s)' % (rep['wave32'], rep['market'],
                                      rep['first_session'],
                                      rep['last_session']),
              'When in the day B earns (bp of capital, B\'s sizing; '
              'reported).', '']
        L += _legs_text(rep)
        L += ['', 'B from 14:00 (BL) against B:',
              '  rule  bar     days   bp a session   Sharpe     fall ratio']
        for name, v in rep['rules'].items():
            p = rep['perf'][name]
            L.append('  %-4s  %-6s  %5d  %12s  %9s  %10s' % (
                name, v['status'], v['both']['n'], _f(v['per_session']),
                _f(p['sharpe'], '%+.4f'), _f(p['fall_ratio'], '%.1f')))
    elif rep['part'] == '2b':
        L += ['%s  NQ, the later months  %s .. %s  (%d trading days)' % (
            rep['wave32'], rep['window'][0], rep['window'][1],
            rep['trading_days']), '']
        L += _legs_text(rep)
        L.append('')
        for name, v in rep['rules'].items():
            L.append('  %-2s in the window: n %d  net %s  %s' % (
                name, v['n'], _f(v.get('net')), v['status']))
    else:
        L.append('LATE-HEAVY: ' + ', '.join(
            '%s %s' % (m, 'n/a' if v is None else 'HELD' if v else 'NOT HELD')
            for m, v in rep['late_heavy'].items()) + '; on all three: %s'
            % ('yes' if rep['late_heavy_everywhere'] else 'no'))
        if rep['later_late_heavy'] is not None:
            L.append('  NQ, the later months: %s' % (
                'HELD' if rep['later_late_heavy'] else 'NOT HELD'))
        L.append('NQ-MORE (the late legs earn more on NQ): %s   (%s)' % (
            'HELD' if rep['nq_more'] else 'NOT HELD', ', '.join(
                '%s %s' % (m, _f(v)) for m, v in rep['late_mean'].items())))
        b = rep['bl']
        L.append('BL, B from 14:00: %s' % b['status'])
        for m in MARKETS:
            L.append('  %-3s  bar %-4s  Sharpe B %s  BL %s   fall ratio B %s'
                     '  BL %s%s' % (
                         m, 'PASS' if b['passes'][m] else 'FAIL',
                         _f(b['sharpe'][m]['B'], '%+.4f'),
                         _f(b['sharpe'][m]['BL'], '%+.4f'),
                         _f(b['fall_ratio'][m]['B'], '%.1f'),
                         _f(b['fall_ratio'][m]['BL'], '%.1f'),
                         '' if m not in b['gains'] else
                         '   gains' if b['gains'][m] else '   no gain'))
        L += ['  ' + n for n in rep['notes']]
    L.append('Minute bars, costs charged; not P&L. No order was placed.')
    return '\n'.join(L)


def read_made(path, part, market):
    return any(r.get('version') == W32_VERSION and r.get('part') == part
               and r.get('market') == market
               for r in W25.ledger_doc(path).get('reads', []))


def record_read(rep, path):
    doc = W25.ledger_doc(path)
    doc.setdefault('reads', []).append(dict(
        version=W32_VERSION, part=rep['part'], market=rep['market'],
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
        print('\nwave-thirty-two report -> %s' % out)
    print('read recorded (%d read(s) in %s)' % (n, HISTORY_LEDGER))
    return 0


if __name__ == '__main__':
    sys.exit(main())
