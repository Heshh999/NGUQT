#!/usr/bin/env python3
"""mrofyt_dealer33.py - MROF-YT-W33-DEALER-1.0

MROF_YT_WAVE33_DEALER_REGISTRATION.md turned into running code: when B
works, with the dealers' side read from price.

    FALL       the five trading days before the session fell (known
               before the open)
    MODE       TREND when the morning's five-minute changes continue
               (their autocorrelation from 09:30 to 12:00 is above 0),
               else FIGHT (known at 12:00)
    BFALL      B on FALL sessions only
    BMODE      B, flat from 12:00 after a FIGHT morning
    written    FALL HELPS, MODE HELPS, MODE PERSISTS
    down

    python3 mrofyt_dealer33.py "<NQ exports>" --market NQ --out w33_nq.json
    python3 mrofyt_dealer33.py "<ES exports>" --market ES --out w33_es.json
    python3 mrofyt_dealer33.py "<RTY exports>" --market RTY --out w33_rty.json
    python3 mrofyt_dealer33.py "<NQ exports>" --later-months
                                         --out w33_later.json
    python3 mrofyt_dealer33.py --decide w33_nq.json w33_es.json w33_rty.json
                                         [w33_later.json]
    options: --stamps-tz UTC|ET  --stamps end|start  --gaps-ok

Each read is made once and recorded before any result is shown. B, its
sizing, its legs, the reader and the costs are waves twenty-four to
thirty-two's own. Read-only; no order is placed.
"""
import collections
import datetime
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_clocks30 as C30        # noqa: E402
import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_improve26 as W26       # noqa: E402
import mrofyt_lateday32 as Y         # noqa: E402
import mrofyt_screen15 as S          # noqa: E402

W33_VERSION = 'MROF-YT-W33-DEALER-1.0'
REGISTRATION = 'MROF_YT_WAVE33_DEALER_REGISTRATION.md'
HISTORY_LEDGER = W25.HISTORY_LEDGER
N = S.N_MIN
MARKETS = ('NQ', 'ES', 'RTY')
JUDGED_ON = ('ES', 'RTY')
FALL_DAYS = 5
STEP = 5                             # minutes in a change
MORNING = (1, 30)                    # k: 09:30-09:35 .. 11:55-12:00
AFTERNOON = (31, 78)                 # k: 12:00-12:05 .. 15:55-16:00
NOON = 150                           # 12:00, minutes after 09:30
LOOKBACK = 30                        # B's own last month, in sessions
SHARPE_GAIN = 1.05
CHANGES = ('BFALL', 'BMODE')
STATEMENTS = ('FALL HELPS', 'MODE HELPS', 'MODE PERSISTS')
CELLS = tuple((f, m) for f in ('FALL', 'NOT FALL')
              for m in ('TREND', 'FIGHT'))


# ---------------------------------------------------------------------
# section 2: the two readings
# ---------------------------------------------------------------------
def falls(chain):
    """{session: the compound daily return of the five trading days
    before it}, None when one of them is missing or there are fewer
    than five."""
    out = {}
    for i, r in enumerate(chain):
        prev = chain[max(0, i - FALL_DAYS):i]
        if len(prev) < FALL_DAYS or any(p['ret'] is None for p in prev):
            out[r['session']] = None
            continue
        g = 1.0
        for p in prev:
            g *= 1.0 + p['ret']
        out[r['session']] = g - 1.0
    return out


def is_fall(x):
    """FALL: below 0; unknown counts as not FALL."""
    return x is not None and x < 0


def ac(d, first, last):
    """sum c(k) c(k+1), k = first .. last - 1, over sum c(k)^2,
    k = first .. last, with c(k) = P(5k) - P(5k - 5). None when nothing
    changed."""
    c = [d.p(STEP * k) - d.p(STEP * k - STEP)
         for k in range(first, last + 1)]
    den = sum(x * x for x in c)
    if not den > 0:
        return None
    return sum(a * b for a, b in zip(c, c[1:])) / den


def mode(d):
    """'TREND' when the morning's AC is above 0, else 'FIGHT'."""
    a = ac(d, *MORNING)
    return 'TREND' if a is not None and a > 0 else 'FIGHT'


# ---------------------------------------------------------------------
# section 3: two changes to B
# ---------------------------------------------------------------------
def day_bmode(d, sigma, trend):
    """(gross, cost, position changes) in units of the open: B's rule,
    flat from 12:00 when the morning is not TREND. On a TREND morning
    this is wave twenty-four's day_b, step for step."""
    pos, pts, cost, n, last = 0, 0.0, 0.0, 0, None
    for j in tuple(S.B_TIMES) + (N,):
        p = d.p(j)
        if last is not None:
            pts += pos * (p - last)
        if j == N or (not trend and j >= NOON):
            want = 0
        else:
            want = W26.b_want(d, sigma, j)
        if want != pos:
            cost += S.SIDE * abs(want - pos)
            n += 1
            pos = want
        last = p
    return pts / d.o, cost / d.o, n


def rules(days, order, bi, fall):
    """{rule: trades} of B, BFALL and BMODE, each sized as B."""
    b = C30.rule(days, order, bi, S.B_TIMES)
    bmode = []
    for s in order:
        if s not in bi:
            continue
        sigma, vol = bi[s]
        g, c, n = day_bmode(days[s], sigma, mode(days[s]) == 'TREND')
        if n:
            bmode.append(S._trade(s, g, c, changes=n, late=0,
                                  lev=min(S.B_VOL_TARGET / vol,
                                          S.B_MAX_LEV)))
    return collections.OrderedDict((
        ('B', b),
        ('BFALL', [t for t in b if is_fall(fall.get(t['session']))]),
        ('BMODE', bmode)))


# ---------------------------------------------------------------------
# sections 5 and 6: the statements and what is reported beside
# ---------------------------------------------------------------------
def _m(v):
    return round(S.mean(v), 5) if v else None


def compare(yes, no):
    """Two groups: their sizes and means, the difference, its Welch t,
    and whether the first mean is above the second (None without both
    groups)."""
    out = dict(n_yes=len(yes), n_no=len(no), mean_yes=_m(yes),
               mean_no=_m(no), diff=None, t=None, held=None)
    if yes and no:
        my, mn = S.mean(yes), S.mean(no)
        out.update(diff=round(my - mn, 5), held=bool(my > mn))
        if len(yes) >= 2 and len(no) >= 2:
            se = math.sqrt(S.stdev(yes) ** 2 / len(yes) +
                           S.stdev(no) ** 2 / len(no))
            if se > 0:
                out['t'] = round((my - mn) / se, 3)
    return out


def _cell(v):
    return dict(n=len(v), mean=_m(v),
                sd=round(S.stdev(v), 5) if len(v) >= 2 else None)


def last_month(xs, keep):
    """B's x by whether its x summed over its previous 30 sessions is at
    or below 0 (yes) or above it (no)."""
    down, up = [], []
    for i in range(LOOKBACK, len(xs)):
        s, x = xs[i]
        if not keep(s):
            continue
        prev = sum(v for _s, v in xs[i - LOOKBACK:i])
        (down if prev <= 0 else up).append(x)
    return compare(down, up)


def describe(days, order, bi, fall, b_trades, keep=lambda s: True):
    """The three statements, the four cells, the shares, the years and
    B's last month, over the sessions `keep` admits."""
    sessions = [s for s in order if s in bi]
    xs = C30.session_x(sessions, b_trades)
    modes = {s: mode(days[s]) for s in order}
    use = [(s, x) for s, x in xs if keep(s)]
    table = Y.leg_table(days, order, bi)
    pm = {s: sum(x for j, _p, _a, x in table[s] if j >= NOON)
          for s in sessions}
    aft = [(s, ac(days[s], *AFTERNOON)) for s in order if keep(s)]
    st = collections.OrderedDict((
        ('FALL HELPS', compare(
            [x for s, x in use if is_fall(fall.get(s))],
            [x for s, x in use if not is_fall(fall.get(s))])),
        ('MODE HELPS', compare(
            [pm[s] for s, _x in use if modes[s] == 'TREND'],
            [pm[s] for s, _x in use if modes[s] == 'FIGHT'])),
        ('MODE PERSISTS', compare(
            [a for s, a in aft if a is not None and modes[s] == 'TREND'],
            [a for s, a in aft if a is not None and modes[s] == 'FIGHT']))))
    cells = collections.OrderedDict(
        ('%s / %s' % (f, m), _cell([
            x for s, x in use if modes[s] == m and
            is_fall(fall.get(s)) == (f == 'FALL')])) for f, m in CELLS)
    n = len(use)
    shares = dict(
        sessions=n,
        fall=round(sum(1 for s, _x in use if is_fall(fall.get(s))) / n, 4)
        if n else None,
        fall_unknown=sum(1 for s, _x in use if fall.get(s) is None),
        trend=round(sum(1 for s, _x in use if modes[s] == 'TREND') / n, 4)
        if n else None)
    years = collections.OrderedDict()
    for y in sorted({s[:4] for s, _x in use}):
        u = [(s, x) for s, x in use if s[:4] == y]
        years[y] = dict(
            sessions=len(u),
            fall=round(sum(1 for s, _x in u if is_fall(fall.get(s))) /
                       len(u), 4),
            trend=round(sum(1 for s, _x in u if modes[s] == 'TREND') /
                        len(u), 4),
            b_mean=_m([x for _s, x in u]),
            fall_mean=_m([x for s, x in u if is_fall(fall.get(s))]),
            not_fall_mean=_m([x for s, x in u if not is_fall(fall.get(s))]),
            trend_mean=_m([x for s, x in u if modes[s] == 'TREND']),
            fight_mean=_m([x for s, x in u if modes[s] == 'FIGHT']))
    return dict(sessions=n, b_per_session=_m([x for _s, x in use]),
                statements=st, cells=cells, shares=shares, years=years,
                last_month=last_month(xs, keep))


def judge_all(days, order, chain):
    bi = W26.b_inputs(days, order, chain)
    fall = falls(chain)
    sessions = [s for s in order if s in bi]
    rs = rules(days, order, bi, fall)
    res = describe(days, order, bi, fall, rs['B'])
    judged, pf = collections.OrderedDict(), collections.OrderedDict()
    for name, trades in rs.items():
        judged[name] = C30._judged(name, trades, sessions)
        pf[name] = Y.perf(C30.session_x(sessions, trades))
    res.update(rules=judged, perf=pf)
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
        wave33=W33_VERSION, registration=REGISTRATION, part='market',
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
        fall = falls(chain)
        rs = rules(days, order, bi, fall)
        res = describe(days, order, bi, fall, rs['B'], keep=W25.in_window)
        verdicts = collections.OrderedDict()
        for name, trades in rs.items():
            inw = [t for t in trades if W25.in_window(t['session'])]
            verdicts[name] = W25.window_verdict(
                [x for _s, x in S.nets('B', inw, {})])
    rep = dict(
        wave33=W33_VERSION, registration=REGISTRATION, part='2b',
        market='NQ', stamp_check=chk, window=[W25.LATER_FROM, W25.LATER_TO],
        trading_days=len(inside), first_session=inside[0]['session'],
        last_session=inside[-1]['session'], last_session_read=last_read,
        rules=verdicts, n_trades=sum(v['n'] for v in verdicts.values()),
        collapsed=[r for r, v in verdicts.items()
                   if v['status'] == 'COLLAPSED'])
    rep.update(res)
    return rep


# ---------------------------------------------------------------------
# section 4: the verdict
# ---------------------------------------------------------------------
def gains(rep, name):
    """Whether, on one market, B's Sharpe is above 0, the change's is at
    least 5 % higher and its fall ratio is lower."""
    b, x = rep['perf']['B'], rep['perf'][name]
    return bool(
        b['sharpe'] is not None and b['sharpe'] > 0 and
        x['sharpe'] is not None and
        x['sharpe'] >= SHARPE_GAIN * b['sharpe'] and
        b['fall_ratio'] is not None and x['fall_ratio'] is not None and
        x['fall_ratio'] < b['fall_ratio'])


def decide(reps):
    """The verdicts on BFALL and BMODE and the three statements, from
    the three market reports and, when it is given, the later months."""
    for r in reps:
        if r.get('wave33') != W33_VERSION:
            raise CX.ContextDataError('a report is not one of %s. Nothing '
                                      'was decided.' % W33_VERSION)
    by = {r['market']: r for r in reps if r.get('part') == 'market'}
    later = [r for r in reps if r.get('part') == '2b']
    missing = [m for m in MARKETS if m not in by]
    if missing or len(by) + len(later) != len(reps) or len(later) > 1:
        raise CX.ContextDataError(
            'the reports of %s are needed, each once (and at most one of the '
            'later months). Nothing was decided.' % ', '.join(
                missing or MARKETS))
    sts = collections.OrderedDict()
    for k in STATEMENTS:
        held = collections.OrderedDict(
            (m, by[m]['statements'][k]['held']) for m in MARKETS)
        sts[k] = dict(held=held, both=all(held[m] is True
                                          for m in JUDGED_ON),
                      later=later[0]['statements'][k]['held']
                      if later else None)
    verdicts = collections.OrderedDict()
    for name in CHANGES:
        passes = collections.OrderedDict(
            (m, by[m]['rules'][name]['status'] == 'PASS') for m in MARKETS)
        gain = collections.OrderedDict((m, gains(by[m], name))
                                       for m in JUDGED_ON)
        better = all(passes.values()) and all(gain.values())
        status = 'BETTER THAN B' if better else 'NOT BETTER'
        if better and later and name in later[0]['collapsed']:
            status = 'NOT BETTER (collapsed in the later months)'
        verdicts[name] = dict(
            passes=passes, gains=gain, status=status,
            sharpe={m: dict(B=by[m]['perf']['B']['sharpe'],
                            X=by[m]['perf'][name]['sharpe'])
                    for m in MARKETS},
            fall_ratio={m: dict(B=by[m]['perf']['B']['fall_ratio'],
                                X=by[m]['perf'][name]['fall_ratio'])
                        for m in MARKETS})
    notes = []
    good = [n for n, v in verdicts.items() if v['status'] == 'BETTER THAN B']
    if good and not later:
        notes.append('The later months are still to be read: a change does '
                     'not go on if it is COLLAPSED there.')
    if good:
        notes.append("A better change takes B's place only if B itself "
                     'passes wave twenty-five.')
    if len(good) == 2:
        notes.append('Both are better: each goes on alone; together is a '
                     'later file.')
    return dict(wave33=W33_VERSION, part='decide', statements=sts,
                changes=verdicts, later_read=bool(later), notes=notes)


# ---------------------------------------------------------------------
# text, ledger, command
# ---------------------------------------------------------------------
def _f(x, fmt='%+.3f'):
    return 'n/a' if x is None else fmt % x


def _pct(x):
    return 'n/a' if x is None else '%.0f%%' % (100.0 * x)


def _held(x):
    return 'n/a' if x is None else 'HELD' if x else 'NOT HELD'


WHAT = {'FALL HELPS': ('B after a fall', 'B otherwise', 'bp'),
        'MODE HELPS': ("B's afternoon, TREND", 'FIGHT', 'bp'),
        'MODE PERSISTS': ("afternoon's AC, TREND", 'FIGHT', 'AC')}


def _desc_text(rep):
    sh = rep['shares']
    L = ['  B: %s bp a session over %d sessions; FALL on %s of them '
         '(%d unknown), TREND on %s' % (
             _f(rep['b_per_session']), rep['sessions'], _pct(sh['fall']),
             sh['fall_unknown'], _pct(sh['trend'])), '']
    for k, v in rep['statements'].items():
        a, b, u = WHAT[k]
        L.append('  %-13s %s' % (k + ':', _held(v['held'])))
        L.append('    %s %s %s (%d), %s %s (%d); difference %s, '
                 'Welch t %s' % (a, _f(v['mean_yes'], '%+.4f'), u,
                                 v['n_yes'], b, _f(v['mean_no'], '%+.4f'),
                                 v['n_no'], _f(v['diff'], '%+.4f'),
                                 _f(v['t'], '%+.2f')))
    L += ['', '  B in the four cells (bp a session):',
          '  cell                  sessions    mean bp      sd']
    for k, v in rep['cells'].items():
        L.append('  %-20s  %8d  %9s  %8s' % (
            k, v['n'], _f(v['mean']), _f(v['sd'], '%.3f')))
    lm = rep['last_month']
    L += ['', "  B's own last 30 sessions: summed at or below 0 -> %s bp "
          '(%d); above 0 -> %s bp (%d); Welch t %s' % (
              _f(lm['mean_yes']), lm['n_yes'], _f(lm['mean_no']),
              lm['n_no'], _f(lm['t'], '%+.2f')), '',
          '  year  sessions  FALL  TREND   B bp   FALL bp  other bp  '
          'TREND bp  FIGHT bp']
    for y, v in rep['years'].items():
        L.append('  %s  %8d  %4s  %5s  %6s  %7s  %8s  %8s  %8s' % (
            y, v['sessions'], _pct(v['fall']), _pct(v['trend']),
            _f(v['b_mean'], '%+.2f'), _f(v['fall_mean'], '%+.2f'),
            _f(v['not_fall_mean'], '%+.2f'), _f(v['trend_mean'], '%+.2f'),
            _f(v['fight_mean'], '%+.2f')))
    return L


def text(rep):
    L = []
    if rep['part'] == 'market':
        L += ['%s  %s  (%s .. %s)' % (rep['wave33'], rep['market'],
                                      rep['first_session'],
                                      rep['last_session']),
              "When B works: the dealers' side read from price (bp of "
              "capital, B's sizing).", '']
        L += _desc_text(rep)
        L += ['', 'B after a fall (BFALL) and B on trend mornings (BMODE) '
              'against B:',
              '  rule   bar     days   bp a session   Sharpe     fall ratio']
        for name, v in rep['rules'].items():
            p = rep['perf'][name]
            L.append('  %-5s  %-6s  %5d  %12s  %9s  %10s' % (
                name, v['status'], v['both']['n'], _f(v['per_session']),
                _f(p['sharpe'], '%+.4f'), _f(p['fall_ratio'], '%.1f')))
    elif rep['part'] == '2b':
        L += ['%s  NQ, the later months  %s .. %s  (%d trading days)' % (
            rep['wave33'], rep['window'][0], rep['window'][1],
            rep['trading_days']), '']
        L += _desc_text(rep)
        L.append('')
        for name, v in rep['rules'].items():
            L.append('  %-5s in the window: n %d  net %s  %s' % (
                name, v['n'], _f(v.get('net')), v['status']))
    else:
        for k, v in rep['statements'].items():
            L.append('%s: %s; on both ES and RTY: %s%s' % (
                k, ', '.join('%s %s' % (m, _held(h))
                             for m, h in v['held'].items()),
                'yes' if v['both'] else 'no',
                '' if v['later'] is None else
                '; NQ, the later months: %s' % _held(v['later'])))
        for name, v in rep['changes'].items():
            L.append('%s: %s' % (
                'BFALL, B after a fall' if name == 'BFALL' else
                'BMODE, B on trend mornings', v['status']))
            for m in MARKETS:
                L.append('  %-3s  bar %-4s  Sharpe B %s  %s %s   fall ratio '
                         'B %s  %s %s%s' % (
                             m, 'PASS' if v['passes'][m] else 'FAIL',
                             _f(v['sharpe'][m]['B'], '%+.4f'), name,
                             _f(v['sharpe'][m]['X'], '%+.4f'),
                             _f(v['fall_ratio'][m]['B'], '%.1f'), name,
                             _f(v['fall_ratio'][m]['X'], '%.1f'),
                             '' if m not in v['gains'] else
                             '   gains' if v['gains'][m] else '   no gain'))
        L += ['  ' + n for n in rep['notes']]
    L.append('Minute bars, costs charged; not P&L. No order was placed.')
    return '\n'.join(L)


def read_made(path, part, market):
    return any(r.get('version') == W33_VERSION and r.get('part') == part
               and r.get('market') == market
               for r in W25.ledger_doc(path).get('reads', []))


def record_read(rep, path):
    doc = W25.ledger_doc(path)
    doc.setdefault('reads', []).append(dict(
        version=W33_VERSION, part=rep['part'], market=rep['market'],
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
        print('\nwave-thirty-three report -> %s' % out)
    print('read recorded (%d read(s) in %s)' % (n, HISTORY_LEDGER))
    return 0


if __name__ == '__main__':
    sys.exit(main())
