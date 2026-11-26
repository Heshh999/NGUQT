#!/usr/bin/env python3
"""mrofyt_improve26.py - MROF-YT-W26-IMPROVE-1.0

MROF_YT_WAVE26_IMPROVE_REGISTRATION.md turned into running code: three
changes to A, judged against A itself, and A and B in micros on a
$150,000 prop account.

    A1  busy opens only: the first five minutes' volume above its
        mean of the 14 previous sessions
    A2  the stop at 10 % of the mean cash-session range of the 14
        previous trading days
    A3  A closed at a half hour when B's own rule is on the other side
    prop  A and B on one account in MNQ: A about 150 dollars at risk a
        trade, B about 500 dollars for a normal day; failed 4,500
        dollars below its highest end-of-day value; with and without
        a daily stop at -1,000

    python3 mrofyt_improve26.py "<NQ minute exports>" --market NQ --out w26_nq.json
    python3 mrofyt_improve26.py "<ES minute exports>" --market ES --out w26_es.json
    python3 mrofyt_improve26.py "<RTY minute exports>" --market RTY --out w26_rty.json
    python3 mrofyt_improve26.py --decide w26_nq.json w26_es.json w26_rty.json
    python3 mrofyt_improve26.py "<every NQ minute export>" --later-months --out w26_later.json
    options: --stamps-tz UTC|ET  --stamps end|start  --gaps-ok (markets only)

Each read is made once and recorded before any result is shown.
A and B are wave twenty-four's own functions; costs and the reader are
wave twenty-five's. Read-only; no order is placed.
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
import mrofyt_screen15 as S          # noqa: E402
import mrofyt_tradecost as TC        # noqa: E402

W26_VERSION = 'MROF-YT-W26-IMPROVE-1.0'
REGISTRATION = 'MROF_YT_WAVE26_IMPROVE_REGISTRATION.md'
HISTORY_LEDGER = W25.HISTORY_LEDGER
N = S.N_MIN
CHANGES = ('A1', 'A2', 'A3')
NAMES = collections.OrderedDict((
    ('A', 'A unchanged'), ('A1', 'busy opens only'),
    ('A2', 'a stop from the normal day'), ('A3', 'out when B is against it')))
HISTORY = 14
A2_SHARE = 0.10
MARKETS = ('NQ', 'ES', 'RTY')
JUDGED_ON = ('ES', 'RTY')            # "better than A"

# section 3: the prop account, in MNQ
MNQ_PT = 2.0                         # dollars a point
MNQ_RT, MNQ_STOP = 1.00, 1.25        # points a round trip; on a stop
MNQ_SIDE = MNQ_RT / 2.0
MAX_MICROS = 15
A_BUDGET, B_BUDGET = 150.0, 500.0
ACCOUNT, TRAIL = 150000.0, 4500.0
DAY_STOP = 1000.0
STOP_COST_SHARE = 0.10


# ---------------------------------------------------------------------
# section 2: A, and three changes to it
# ---------------------------------------------------------------------
def b_want(d, sigma, j):
    """B's own rule at minute j: 1 long, -1 short, 0 flat."""
    hi, lo = max(d.o, d.pc), min(d.o, d.pc)
    p, vw = d.p(j), d.vwap(j)
    if vw is not None and p > hi * (1 + sigma[j]) and p > vw:
        return 1
    if vw is not None and p < lo * (1 - sigma[j]) and p < vw:
        return -1
    return 0


def a_core(d, stop=None, sigma=None):
    """A on one session; `stop` replaces the first candle's end (A2);
    with `sigma`, A is closed at B's times when B is on the other side
    (A3). With neither it is wave twenty-four's trade_a."""
    entry = d.p(5)
    sg = S.sign(entry - d.o)
    if not sg:
        return None
    if stop is None:
        stop = min(d.l[:5]) if sg > 0 else max(d.h[:5])
    risk = abs(entry - stop)
    if risk < S.CO.TICK:
        return None
    target = entry + sg * S.A_TARGET_R * risk
    ex, how, xj = d.p(N), 'CLOSE', N
    for j in range(5, N):
        if sigma is not None and j in S.B_TIMES and \
                b_want(d, sigma, j) == -sg:
            ex, how, xj = d.p(j), 'B', j
            break
        if (d.l[j] <= stop) if sg > 0 else (d.h[j] >= stop):
            ex, how, xj = stop, 'STOP', j + 1
            break
        if (d.h[j] >= target) if sg > 0 else (d.l[j] <= target):
            ex, how, xj = target, 'TARGET', j + 1
            break
    cost = (S.RT_STOP if how == 'STOP' else S.RT) / entry
    return S._trade(d.session, sg * (ex - entry) / entry, cost, how=how,
                    lev=min(S.A_RISK / (risk / entry), S.A_MAX_LEV),
                    sg=sg, entry=entry, exit_px=ex, exit_j=xj, risk=risk)


def rule_a(days, order):
    return [t for t in (a_core(days[s]) for s in order) if t]


def rule_a1(days, order):
    out, v5s = [], []
    for s in order:
        d = days[s]
        v5 = sum(d.v[:5])
        if len(v5s) >= HISTORY and v5 > S.mean(v5s[-HISTORY:]):
            t = a_core(d)
            if t:
                out.append(t)
        v5s.append(v5)
    return out


def normal_range(chain):
    """{session: the mean cash high minus low of the 14 trading days
    before it}."""
    out, rng = {}, []
    for r in chain:
        if len(rng) >= HISTORY:
            out[r['session']] = S.mean(rng[-HISTORY:])
        if r['high'] is not None and r['low'] is not None:
            rng.append(r['high'] - r['low'])
    return out


def rule_a2(days, order, chain):
    dr, out = normal_range(chain), []
    for s in order:
        if s not in dr:
            continue
        d = days[s]
        sg = S.sign(d.p(5) - d.o)
        if not sg:
            continue
        t = a_core(d, stop=d.p(5) - sg * A2_SHARE * dr[s])
        if t:
            out.append(t)
    return out


def b_inputs(days, order, chain):
    """{session: (sigma, s)}: B's bounds and 14-day volatility, exactly
    as wave twenty-four's rule_b computes them."""
    rets, vol = [], {}
    for r in chain:
        if len(rets) >= S.B_HISTORY:
            vol[r['session']] = S.stdev(rets[-S.B_HISTORY:])
        if r['ret'] is not None:
            rets.append(r['ret'])
    moves, out = [], {}
    for s in order:
        d = days[s]
        mv = [abs(d.p(j) / d.o - 1.0) for j in range(N + 1)]
        if len(moves) >= S.B_HISTORY and vol.get(s):
            out[s] = ([S.mean([m[j] for m in moves[-S.B_HISTORY:]])
                       for j in range(N + 1)], vol[s])
        moves.append(mv)
    return out


def rule_a3(days, order, chain):
    bi = b_inputs(days, order, chain)
    out = []
    for s in order:
        t = a_core(days[s], sigma=bi[s][0] if s in bi else None)
        if t:
            out.append(t)
    return out


def four(days, order, chain):
    return collections.OrderedDict((
        ('A', rule_a(days, order)), ('A1', rule_a1(days, order)),
        ('A2', rule_a2(days, order, chain)),
        ('A3', rule_a3(days, order, chain))))


def judge_four(days, order, chain):
    sess = S.session_returns(chain)
    out = collections.OrderedDict()
    for rule, trades in four(days, order, chain).items():
        pairs = S.nets('A', trades, sess)
        res = S.judge(pairs)
        res.update(rule=rule, name=NAMES[rule],
                   per_session=round(sum(x for _s, x in pairs) / len(order),
                                     4),
                   exits=dict(collections.Counter(t['how'] for t in trades)))
        out[rule] = res
    return out


# ---------------------------------------------------------------------
# section 3: A and B on a prop account
# ---------------------------------------------------------------------
def a_micros(risk):
    return max(1, min(MAX_MICROS, int(A_BUDGET // (risk * MNQ_PT))))


def b_micros(s, o):
    return max(1, min(MAX_MICROS, int(B_BUDGET / (s * o * MNQ_PT) + 0.5)))


def day_path(d, a=None, b=None, day_stop=None):
    """(the day's result in dollars, its lowest value at a minute close)
    of A (a trade of a_core, with 'micros') and B ((changes, micros))
    on one session, in MNQ with its costs; with day_stop, everything is
    closed at the first minute close at or below -day_stop."""
    cash, pos, a_open, low = 0.0, 0, False, 0.0
    ch, qb = b if b else ([], 0)
    k = 0
    for j in range(N + 1):
        p = d.p(j)
        if a and j == 5:
            cash -= a['micros'] * MNQ_PT * MNQ_SIDE
            a_open = True
        if a_open and j == a['exit_j']:
            cash += a['micros'] * MNQ_PT * (
                a['sg'] * (a['exit_px'] - a['entry']) -
                (MNQ_STOP - MNQ_SIDE if a['how'] == 'STOP' else MNQ_SIDE))
            a_open = False
        while k < len(ch) and ch[k][0] == j:
            delta = ch[k][1]
            cash -= delta * qb * MNQ_PT * p + abs(delta) * qb * MNQ_PT * \
                MNQ_SIDE
            pos += delta
            k += 1
        mark = cash + pos * qb * MNQ_PT * p + (
            a['micros'] * MNQ_PT * a['sg'] * (p - a['entry'])
            if a_open else 0.0)
        if day_stop is not None and mark <= -day_stop:
            if a_open:
                cash += a['micros'] * MNQ_PT * (
                    a['sg'] * (p - a['entry']) - MNQ_SIDE)
            if pos:
                cash += pos * qb * MNQ_PT * p - abs(pos) * qb * MNQ_PT * \
                    MNQ_SIDE
            low = min(low, mark, cash)
            return cash, low, j
        low = min(low, mark)
    return cash, low, None


def prop_days(days, order, chain):
    """[(session, a trade or None, (changes, micros) or None)]."""
    bi = b_inputs(days, order, chain)
    out = []
    for s in order:
        d = days[s]
        a = a_core(d)
        if a:
            a = dict(a, micros=a_micros(a['risk']))
        b = None
        if s in bi:
            ch = TC.b_changes(d, bi[s][0])
            if ch:
                b = (ch, b_micros(bi[s][1], d.o))
        out.append((s, a, b))
    return out


def account(days, plan, day_stop=None):
    """The prop account over the sessions of `plan`."""
    bal = peak = ACCOUNT
    fails, by = [], collections.OrderedDict()
    cum = top = fall = 0.0
    stops = 0
    parts = dict(A=0.0, B=0.0)
    for s, a, b in plan:
        if not (a or b):
            continue
        d = days[s]
        res, low, stop_j = day_path(d, a, b, day_stop)
        if stop_j is not None:
            stops += 1
        for key, x in (('A', a), ('B', b)):
            if x:
                parts[key] += day_path(d, x if key == 'A' else None,
                                       x if key == 'B' else None)[0]
        y = by.setdefault(s[:4], dict(result=0.0, fails=0, days=0))
        y['result'] += res
        y['days'] += 1
        fall = max(fall, top - (cum + low))
        cum += res
        top = max(top, cum)
        if bal + low <= peak - TRAIL:
            fails.append(s)
            y['fails'] += 1
            bal = peak = ACCOUNT
            continue
        bal += res
        peak = max(peak, bal)
    for y in by.values():
        y['result'] = round(y['result'], 2)
    return dict(result=round(cum, 2), fails=len(fails), failed_on=fails,
                largest_fall=round(fall, 2), day_stops=stops,
                a_alone=round(parts['A'], 2), b_alone=round(parts['B'], 2),
                by_year=by)


def prop(days, order, chain):
    plan = prop_days(days, order, chain)
    off, on = account(days, plan), account(days, plan, DAY_STOP)
    keep = (on['fails'] < off['fails'] or
            on['largest_fall'] < off['largest_fall']) and \
        off['result'] - on['result'] <= STOP_COST_SHARE * abs(off['result'])
    kept = on if keep else off
    return dict(
        budgets=dict(A=A_BUDGET, B=B_BUDGET), trail=TRAIL,
        day_stop=DAY_STOP, without_day_stop=off, with_day_stop=on,
        keep_day_stop=keep, fails_kept=kept['fails'],
        halve_budgets=kept['fails'] > 1,
        for_step3=dict(A=A_BUDGET / (2 if kept['fails'] > 1 else 1),
                       B=B_BUDGET / (2 if kept['fails'] > 1 else 1),
                       day_stop=DAY_STOP if keep else None),
        micros=dict(
            A=dict(collections.Counter(a['micros'] for _s, a, _b in plan
                                       if a)),
            B=dict(collections.Counter(b[1] for _s, _a, b in plan if b))))


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
        rules = judge_four(days, order, chain)
    rep = dict(
        wave26=W26_VERSION, registration=REGISTRATION, part='market',
        market=market, files=len(rd.files), stamp_check=chk,
        sessions=len(order), first_session=order[0],
        last_session=order[-1], gaps=[list(x) for x in g],
        costs=dict(tick=c['tick'], round_trip=c['rt'], stop=c['stop']),
        rules=rules, n_trades=sum(v['both']['n'] for v in rules.values()))
    if market == 'NQ':
        rep['prop'] = prop(days, order, chain)
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
        tr = four(days, order, chain)
        for rule in CHANGES:
            inw = [t for t in tr[rule] if W25.in_window(t['session'])]
            res = W25.window_verdict([x for _s, x in S.nets('A', inw, {})])
            res.update(rule=rule, name=NAMES[rule])
            rules[rule] = res
    return dict(
        wave26=W26_VERSION, registration=REGISTRATION, part='2b',
        market='NQ', stamp_check=chk, window=[W25.LATER_FROM, W25.LATER_TO],
        trading_days=len(inside), first_session=inside[0]['session'],
        last_session=inside[-1]['session'], last_session_read=last_read,
        rules=rules, n_trades=sum(v['n'] for v in rules.values()),
        collapsed=[r for r, v in rules.items()
                   if v['status'] == 'COLLAPSED'])


def decide(reps):
    """The verdict on each change from the three market reports."""
    by = {r['market']: r for r in reps}
    missing = [m for m in MARKETS if m not in by]
    if missing:
        raise CX.ContextDataError('the reports of %s are needed. Nothing '
                                  'was decided.' % ', '.join(missing))
    out = collections.OrderedDict()
    for rule in CHANGES:
        passes = {m: by[m]['rules'][rule]['status'] == 'PASS'
                  for m in MARKETS}
        better = {m: by[m]['rules'][rule]['per_session'] >
                  by[m]['rules']['A']['per_session'] for m in JUDGED_ON}
        status = 'DROPPED' if not all(passes.values()) else (
            'BETTER THAN A' if all(better.values()) else 'ALTERNATIVE')
        out[rule] = dict(passes=passes, better=better, status=status,
                         per_session_es_rty=round(sum(
                             by[m]['rules'][rule]['per_session']
                             for m in JUDGED_ON), 4))
    best = [r for r in CHANGES if out[r]['status'] == 'BETTER THAN A']
    best.sort(key=lambda r: -out[r]['per_session_es_rty'])
    a_ok = all(by[m]['rules']['A']['status'] == 'PASS' for m in MARKETS)
    return dict(changes=out, goes_on=best[0] if best else None,
                a_passes_everywhere=a_ok,
                note=None if a_ok else 'A itself did not pass on every '
                'market: no change can go on until it passes wave '
                'twenty-five.')


# ---------------------------------------------------------------------
# text, ledger, command
# ---------------------------------------------------------------------
def _usd(x):
    return '%s$%s' % ('-' if x < 0 else '+', format(abs(int(round(x))), ','))


def text(rep):
    L = []
    if rep['part'] == 'market':
        L += ['%s  %s  %d sessions (%s .. %s)' % (
            rep['wave26'], rep['market'], rep['sessions'],
            rep['first_session'], rep['last_session']),
            'A and three changes to it, by wave twenty-four\'s bar (bp of '
            'capital, the source\'s sizing).', '']
        for rule, v in rep['rules'].items():
            L.append('%-2s %s' % (rule, v['name']))
            for h in S.HALVES:
                r = v['halves'][h]
                L.append('    %s  n %5d  won %2.0f%%  net %+8.2f  without '
                         'best month %+8.2f  %s' % (
                             h, r['n'], 100 * r.get('won', 0),
                             r.get('net') or 0.0,
                             r.get('net_without_best') or 0.0,
                             'ok' if r['ok'] else 'no') if r['n'] else
                         '    %s  n     0' % h)
            L.append('    %s%s   a session on average %+.3f   exits %s' % (
                v['status'], ' (strong)' if v['strong'] else '',
                v['per_session'], json.dumps(v['exits'], sort_keys=True)))
            L.append('')
        if 'prop' in rep:
            p = rep['prop']
            L.append('The $150,000 prop account, A and B in MNQ (A ~$150 at '
                     'risk, B ~$500 a normal day):')
            for key, title in (('without_day_stop', 'without the daily '
                                'stop'), ('with_day_stop', 'with the daily '
                                          'stop at -$1,000')):
                x = p[key]
                L.append('  %s: result %s (A %s, B %s), failures %d, '
                         'largest fall %s, daily stops %d' % (
                             title, _usd(x['result']), _usd(x['a_alone']),
                             _usd(x['b_alone']), x['fails'],
                             _usd(-x['largest_fall']), x['day_stops']))
                L.append('    ' + '  '.join(
                    '%s %s%s' % (y, _usd(v['result']),
                                 ' (%d failed)' % v['fails']
                                 if v['fails'] else '')
                    for y, v in x['by_year'].items()))
            L.append('  daily stop kept: %s; budgets halved for step 3: %s'
                     % ('yes' if p['keep_day_stop'] else 'no',
                        'yes' if p['halve_budgets'] else 'no'))
            L.append('')
    elif rep['part'] == '2b':
        L += ['*** LATER MONTHS: NQ 2026-07-01 to 2026-11-13, once (A1, A2, '
              'A3). ***', '']
        for rule, v in rep['rules'].items():
            L.append('%-2s %s: n %d%s  %s' % (
                rule, v['name'], v['n'],
                '  net %+.2f' % v['net'] if v['n'] else '', v['status']))
        L.append('COLLAPSED: %s' % (', '.join(rep['collapsed']) or 'none'))
    else:
        for rule, v in rep['changes'].items():
            L.append('%-2s %s: passes %s; better than A on %s -> %s' % (
                rule, NAMES[rule],
                ', '.join(m for m, ok in v['passes'].items() if ok) or
                'none',
                ', '.join(m for m, ok in v['better'].items() if ok) or
                'neither', v['status']))
        L.append('GOES ON: %s' % (rep['goes_on'] or 'none'))
        if rep['note']:
            L.append(rep['note'])
    L.append('Minute bars, costs charged; not P&L. No order was placed.')
    return '\n'.join(L)


def read_made(path, part, market):
    return any(r.get('version') == W26_VERSION and r.get('part') == part
               and r.get('market') == market
               for r in W25.ledger_doc(path).get('reads', []))


def record_read(rep, path):
    doc = W25.ledger_doc(path)
    doc.setdefault('reads', []).append(dict(
        version=W26_VERSION, part=rep['part'], market=rep['market'],
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
            rep = dict(decide(reps), part='decide')
        except (OSError, ValueError, KeyError) as exc:
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
        print('\nwave-twenty-six report -> %s' % out)
    print('read recorded (%d read(s) in %s)' % (n, HISTORY_LEDGER))
    return 0


if __name__ == '__main__':
    sys.exit(main())
