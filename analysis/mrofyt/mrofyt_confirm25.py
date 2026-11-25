#!/usr/bin/env python3
"""mrofyt_confirm25.py - MROF-YT-W25-CONFIRM-1.0

MROF_YT_WAVE25_CONFIRM_REGISTRATION.md, sections 2a and 2b, turned into
running code: the three rules that passed wave twenty-four's screen, A,
B and E, unchanged, on data they have not seen.

    2a  another market over the same ten years (ES, RTY, YM), with that
        market's contracts, tick and costs; wave twenty-four's bar
    2b  NQ's months after the screen, 2026-07-01 to 2026-11-13, read
        once with --later-months: IN LINE, WEAK, COLLAPSED or TOO FEW

The rules are wave twenty-four's own functions (mrofyt_screen15): this
file only sets the market's costs around them. Sessions from 2026-11-16
are never read. Read-only; no order is placed.

    python3 mrofyt_confirm25.py "<ES minute exports>" --market ES \\
        --out w25_es.json
    python3 mrofyt_confirm25.py "<RTY minute exports>" --market RTY \\
        --out w25_rty.json
    python3 mrofyt_confirm25.py "<every NQ minute export>" --later-months \\
        --out w25_later.json
    options: --stamps-tz UTC|ET (default UTC)  --stamps end|start
             --gaps-ok  (2a only: the feed has no bars for the days named)

A run stops before any rule is computed when the exports have a hole (a
contract not exported), so a half-read never happens by accident.
"""
import collections
import contextlib
import datetime
import json
import math
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_context as CX          # noqa: E402
import mrofyt_screen15 as S          # noqa: E402
import mrofyt_stretchfade as SF      # noqa: E402

W25_VERSION = 'MROF-YT-W25-CONFIRM-1.0'
REGISTRATION = 'MROF_YT_WAVE25_CONFIRM_REGISTRATION.md'
HISTORY_LEDGER = 'MROF_MINUTE_HISTORY_EXPOSURE.json'

RULES = ('A', 'B', 'E')
COMMISSION_RT = 5.0                    # dollars a round trip, all in
MARKETS = collections.OrderedDict((   # tick, dollars a tick
    ('NQ', (0.25, 5.00)), ('ES', (0.25, 12.50)),
    ('RTY', (0.10, 5.00)), ('YM', (1.00, 5.00))))
OTHER_MARKETS = ('ES', 'RTY', 'YM')    # section 2a
REQUIRED = ('ES', 'RTY')               # section 3
LATER_FROM, LATER_TO = '20260701', '20261113'
LATER_REFUSE_FROM = '20261114'         # the gate, for the 2b read only
WINDOW_MIN_N = 30

# operating checks, made before any rule is computed
MIN_SESSIONS = 200                     # usable sessions for 2a
MAX_GAP_DAYS = 5                       # a long weekend is 4 calendar days
LATER_DAYS = 96                        # trading days in 2b's window
LATER_MIN_DAYS = 90
HISTORY_MIN_DAYS = 200                 # trading days before the window


def _date(s):
    return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def market_costs(market):
    """dict(tick, rt, stop) in price units: 5 dollars of commission and
    one tick of spread a round trip, one tick more on a stop."""
    tick, tick_value = MARKETS[market]
    rt_ticks = COMMISSION_RT / tick_value + 1.0
    return dict(tick=tick, rt=round(rt_ticks * tick, 10),
                stop=round((rt_ticks + 1.0) * tick, 10))


@contextlib.contextmanager
def costs(market, times=1.0):
    """Wave twenty-four's rules under `market`'s tick and costs (times
    `times`), then exactly as they were."""
    c = market_costs(market)
    old = S.RT, S.RT_STOP, S.SIDE, S.CO
    S.RT, S.RT_STOP = c['rt'] * times, c['stop'] * times
    S.SIDE = S.RT / 2.0
    S.CO = types.SimpleNamespace(TICK=c['tick'])
    try:
        yield c
    finally:
        S.RT, S.RT_STOP, S.SIDE, S.CO = old


def read(path, market, stamps_tz='UTC', stamps='end', later=False):
    """Wave twenty-two's reader over `market`'s exports, stamps checked.
    later: the 2b read, NQ only: the reader's refusal stands at
    2026-11-14 for this call and is put back whatever happens."""
    if later and market != 'NQ':
        raise CX.ContextDataError('the later months are read on NQ only')
    old = CX.REFUSE_FROM
    if later:
        CX.REFUSE_FROM = LATER_REFUSE_FROM
    try:
        rd = SF.VolReader(market, stamps_tz, stamps, None)
        rd.read_path(path)
        gate = CX.REFUSE_FROM
    finally:
        CX.REFUSE_FROM = old
    if not rd.days:
        raise CX.ContextDataError(CX._nothing_read(
            rd, market, 'before %s' % gate))
    return rd, rd.check_stamps()


def gaps(chain):
    """[(the trading day before, the one after)] wherever two trading
    days in a row are more than MAX_GAP_DAYS calendar days apart: the
    mark of a contract that was not exported."""
    return [(a['session'], b['session']) for a, b in zip(chain, chain[1:])
            if (_date(b['session']) - _date(a['session'])).days
            > MAX_GAP_DAYS]


def _gap_text(g):
    return '; '.join('%s and %s' % tuple(x) for x in g[:5]) + (
        '; and %d more' % (len(g) - 5) if len(g) > 5 else '')


def three(days, order, chain):
    """{rule: (trades, notes)} for A, B and E under the costs in force."""
    return collections.OrderedDict((
        ('A', S.rule_a(days, order)),
        ('B', S.rule_b(days, order, chain)),
        ('E', S.rule_e(chain))))


def judged(days, order, chain):
    """{rule: wave twenty-four's verdict} under the costs in force."""
    sess = S.session_returns(chain)
    out = collections.OrderedDict()
    for rule, (trades, notes) in three(days, order, chain).items():
        res = S.judge(S.nets(rule, trades, sess))
        res.update(rule=rule, name=S.NAMES[rule], notes=notes)
        out[rule] = res
    return out


def run_market(path, market, stamps_tz='UTC', stamps='end', gaps_ok=False):
    """Section 2a on one market."""
    if market not in MARKETS:
        raise CX.ContextDataError('unknown market %r: one of %s'
                                  % (market, ', '.join(MARKETS)))
    rd, chk = read(path, market, stamps_tz, stamps)
    days, order, chain = S.build(rd)
    if len(order) < MIN_SESSIONS:
        raise CX.ContextDataError(
            'only %d usable %s sessions: this needs years of minute bars. '
            'Nothing was computed.' % (len(order), market))
    g = gaps(chain)
    if g and not gaps_ok:
        raise CX.ContextDataError(
            'the %s exports have no cash session between %s: a contract was '
            'not exported. Nothing was computed. Export it and run again; '
            'if the feed has no bars for those days, add --gaps-ok.'
            % (market, _gap_text(g)))
    with costs(market) as c:
        base = judged(days, order, chain)
    with costs(market, 2.0):
        twice = judged(days, order, chain)
    return dict(
        wave25=W25_VERSION, registration=REGISTRATION, part='2a',
        market=market, files=len(rd.files), bad_lines=rd.bad_lines,
        stamp_check=chk, sessions=len(order), first_session=order[0],
        last_session=order[-1], trading_days=len(chain),
        gaps=[list(x) for x in g],
        costs=dict(tick=c['tick'], round_trip=c['rt'], stop=c['stop']),
        rules=base,
        costs_doubled=collections.OrderedDict(
            (r, dict(status=v['status'], strong=v['strong'],
                     H1=v['halves']['H1'].get('net'),
                     H2=v['halves']['H2'].get('net')))
            for r, v in twice.items()),
        n_trades=sum(v['both']['n'] for v in base.values()),
        passed=[r for r, v in base.items() if v['status'] == 'PASS'])


def window_verdict(values):
    """Section 2b's verdict on the net results of one rule: the plain
    standard error, the standard deviation over the root of the count."""
    n = len(values)
    out = dict(n=n)
    if n:
        m = S.mean(values)
        out.update(net=round(m, 3),
                   won=round(sum(1 for x in values if x > 0) / n, 4))
    if n < WINDOW_MIN_N:
        out['status'] = 'TOO FEW'
        return out
    se = S.stdev(values) / math.sqrt(n)
    out['standard_error'] = round(se, 3)
    out['status'] = 'IN LINE' if m > 0 else (
        'WEAK' if m >= -2.0 * se else 'COLLAPSED')
    return out


def in_window(session):
    return LATER_FROM <= session <= LATER_TO


def run_later(path, stamps_tz='UTC', stamps='end'):
    """Section 2b: NQ, sessions 2026-07-01 to 2026-11-13."""
    rd, chk = read(path, 'NQ', stamps_tz, stamps, later=True)
    last_read = max(s for (_c, s) in rd.days)
    if last_read >= LATER_REFUSE_FROM:           # the gate did not hold
        raise CX.ContextDataError('a session from 2026-11-14 on was read '
                                  '(%s). Nothing was computed.' % last_read)
    days, order, chain = S.build(rd)
    before = sum(1 for r in chain if r['session'] < LATER_FROM)
    inside = [r for r in chain if in_window(r['session'])]
    if before < HISTORY_MIN_DAYS:
        raise CX.ContextDataError(
            'only %d trading days before 2026-07-01: the rules need their '
            'histories. Give the folder with EVERY NQ contract, not only '
            'the new files. Nothing was computed.' % before)
    if len(inside) < LATER_MIN_DAYS:
        raise CX.ContextDataError(
            'these exports hold only %d of the %d trading days from '
            '2026-07-01 to 2026-11-13: NQ 09-26 and NQ 12-26 are both '
            'needed, the second exported to 2026-11-13 or later. Nothing '
            'was computed, and the read was not used up.'
            % (len(inside), LATER_DAYS))
    g = gaps(chain)
    if g:
        raise CX.ContextDataError(
            'the NQ exports have no cash session between %s: a contract '
            'was not exported. Nothing was computed, and the read was not '
            'used up.' % _gap_text(g))
    rets = [r['ret'] for r in inside if r['ret'] is not None]
    bench = dict.fromkeys(S.HALVES, S.mean(rets))
    win = [s for s in order if in_window(s)]
    rules = collections.OrderedDict()
    with costs('NQ'):
        for rule, (trades, notes) in three(days, order, chain).items():
            res = window_verdict([x for _s, x in S.nets(
                rule, [t for t in trades if in_window(t['session'])],
                bench)])
            res.update(rule=rule, name=S.NAMES[rule], notes=notes)
            rules[rule] = res
    return dict(
        wave25=W25_VERSION, registration=REGISTRATION, part='2b',
        market='NQ', files=len(rd.files), bad_lines=rd.bad_lines,
        stamp_check=chk, window=[LATER_FROM, LATER_TO],
        trading_days=len(inside), sessions=len(win),
        first_session=inside[0]['session'],
        last_session=inside[-1]['session'], last_session_read=last_read,
        history_days=before,
        refused_from_20261114=len(rd.refused_sessions),
        mean_session_bp=round(1e4 * bench['H2'], 3), rules=rules,
        n_trades=sum(v['n'] for v in rules.values()),
        collapsed=[r for r, v in rules.items()
                   if v['status'] == 'COLLAPSED'])


UNIT = dict(A='bp of capital, the source\'s sizing',
            B='bp of capital, the source\'s sizing',
            E='bp over being long anyway')


def text(rep):
    L = []
    if rep['part'] == '2a':
        c = rep['costs']
        L += ['%s  2a  %s  %d sessions (%s .. %s)' % (
            rep['wave25'], rep['market'], rep['sessions'],
            rep['first_session'], rep['last_session']),
            'The three rules of wave twenty-four, unchanged. Costs: %.2f a '
            'round trip, %.2f on a stop (tick %.2f).' % (
                c['round_trip'], c['stop'], c['tick']),
            'The bar: in each half 30+ trades, a profit after costs, and '
            'still one without its best month.']
        if rep['gaps']:
            L.append('NO CASH SESSION between %s (run with --gaps-ok).'
                     % _gap_text(rep['gaps']))
        L.append('')
        for rule, v in rep['rules'].items():
            L.append('%-2s %s   [%s]' % (rule, v['name'], UNIT[rule]))
            for h in S.HALVES:
                r = v['halves'][h]
                if r['n']:
                    L.append('    %s  n %5d  won %2.0f%%  net %+8.2f  '
                             'without %s %+8.2f  %s' % (
                                 h, r['n'], 100 * r['won'], r['net'],
                                 r['best_month'],
                                 r['net_without_best'] or 0.0,
                                 'ok' if r['ok'] else 'no'))
                else:
                    L.append('    %s  n     0' % h)
            ci = v['both'].get('ci95')
            L.append('    both n %5d  95%% range %s' % (
                v['both']['n'],
                '%+.2f .. %+.2f' % tuple(ci) if ci else '-'))
            d = rep['costs_doubled'][rule]
            L.append('    %s%s      beside, costs doubled: %s (H1 %s, H2 %s)'
                     % (v['status'], ' (strong)' if v['strong'] else '',
                        d['status'],
                        '%+.2f' % d['H1'] if d['H1'] is not None else '-',
                        '%+.2f' % d['H2'] if d['H2'] is not None else '-'))
            if v['notes']:
                L.append('    notes: %s' % json.dumps(v['notes'],
                                                      sort_keys=True))
            L.append('')
        L.append('PASSED ON %s: %s' % (rep['market'],
                                       ', '.join(rep['passed']) or 'none'))
    else:
        L += ['*** LATER MONTHS: NQ sessions 2026-07-01 to 2026-11-13, '
              'once. ***', '',
              '%s  2b  NQ  %d trading days (%s .. %s), %d usable' % (
                  rep['wave25'], rep['trading_days'], rep['first_session'],
                  rep['last_session'], rep['sessions']),
              'Sessions from 2026-11-14 on were refused unread (%d in these '
              'files); the last one read is %s.' % (
                  rep['refused_from_20261114'], rep['last_session_read']),
              'About 96 sessions cannot prove a rule of this size; only '
              'COLLAPSED counts against one.', '']
        for rule, v in rep['rules'].items():
            L.append('%-2s %s   [%s]' % (rule, v['name'], UNIT[rule]))
            if v['n']:
                L.append('    n %4d  won %2.0f%%  net %+8.2f%s' % (
                    v['n'], 100 * v['won'], v['net'],
                    '  (standard error %.2f)' % v['standard_error']
                    if 'standard_error' in v else ''))
            else:
                L.append('    n    0')
            L.append('    %s' % v['status'])
            if v['notes']:
                L.append('    notes: %s' % json.dumps(v['notes'],
                                                      sort_keys=True))
            L.append('')
        L.append('COLLAPSED: %s' % (', '.join(rep['collapsed']) or 'none'))
    L.append('Minute bars, costs charged; not P&L. No order was placed.')
    return '\n'.join(L)


# ---------------------------------------------------------------------
# the ledger: which read was made, and 2b's only once
# ---------------------------------------------------------------------
def ledger_doc(path):
    """The ledger as it stands ({} when there is none yet)."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        doc = None
    if not isinstance(doc, dict):
        raise CX.ContextDataError(
            'the ledger %s cannot be read: restore it before any read is '
            'made. Nothing was computed.' % os.path.basename(path))
    return doc


def later_read_made(path):
    return any(r.get('version') == W25_VERSION and r.get('part') == '2b'
               for r in ledger_doc(path).get('reads', []))


def record_read(rep, path):
    """Append this read to the ledger; the number of reads it holds."""
    doc = ledger_doc(path)
    doc.setdefault('reads', []).append(dict(
        version=W25_VERSION, part=rep['part'], market=rep['market'],
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


def can_write(path):
    """Whether a file can be written there: asked before a read."""
    was = os.path.exists(path)
    try:
        with open(path, 'a'):
            pass
    except OSError:
        return False
    if not was:
        os.remove(path)
    return True


def main(argv=None, ledger=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('--'):
        print(__doc__)
        return 2

    def arg(k):
        i = argv.index(k) + 1 if k in argv else len(argv)
        return argv[i] if i < len(argv) else None
    stz = (arg('--stamps-tz') or 'UTC').upper()
    stp = (arg('--stamps') or 'end').lower()
    later, market = '--later-months' in argv, (arg('--market') or '').upper()
    ledger = ledger or os.path.join(HERE, HISTORY_LEDGER)
    if later == bool(market):
        print('STOPPED: give either --market ES|RTY|YM (section 2a) or '
              '--later-months (section 2b, NQ).')
        return 2
    if market and market not in OTHER_MARKETS:
        print('STOPPED: --market is one of %s.' % ', '.join(OTHER_MARKETS))
        return 2
    out = arg('--out')
    if out and not can_write(out):
        print('STOPPED: %s cannot be written (does the folder exist?). '
              'Nothing was read.' % out)
        return 2
    try:
        if later and later_read_made(ledger):
            print('REFUSED: the later months have been read (%s). The read '
                  'is made once.' % HISTORY_LEDGER)
            return 2
        rep = run_later(argv[0], stz, stp) if later else run_market(
            argv[0], market, stz, stp, '--gaps-ok' in argv)
        n = record_read(rep, ledger)       # on record before it is shown
    except CX.ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
    print(text(rep))
    if out:
        print('\nwave-twenty-five report -> %s' % out)
    print('read recorded (%d read(s) in %s)' % (n, HISTORY_LEDGER))
    return 0


if __name__ == '__main__':
    sys.exit(main())
