#!/usr/bin/env python3
"""mrofyt_sizing31.py - MROF-YT-W31-SIZING-1.0

MROF_YT_WAVE31_SIZING_REGISTRATION.md turned into running code: how far
the market will move, used only for size. A position of A or B decided
in a HIGH state is taken at half size, under each of two measures:

    RVMR  the frozen range regime of analysis/rvmr/rvmr_spec.py
          (imported, not copied): the bar's range over the mean of the
          1,440 bars before it; HIGH above 2.335
    ATR   the mean true range of the 20 bars to the decision against
          its mean at the same minute on the 14 previous sessions;
          HIGH at 1.5 times or more

Compared on the same sessions with the unchanged rules: the Sharpe of
a session's result and its largest fall. Judged on ES and RTY.

    python3 mrofyt_sizing31.py "<NQ exports>" --market NQ --out w31_nq.json
    python3 mrofyt_sizing31.py "<ES exports>" --market ES --out w31_es.json
    python3 mrofyt_sizing31.py "<RTY exports>" --market RTY --out w31_rty.json
    python3 mrofyt_sizing31.py --decide w31_nq.json w31_es.json w31_rty.json
    options: --stamps-tz UTC|ET  --stamps end|start  --gaps-ok

Each read is made once and recorded before any result is shown. A, B,
their sizing, the reader and the costs are waves twenty-four to
twenty-six's own. Read-only; no order is placed.
"""
import bisect
import collections
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RVMR_DIR = os.path.join(HERE, '..', 'rvmr')
sys.path.insert(1, RVMR_DIR)

import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_improve26 as W26       # noqa: E402
import mrofyt_screen15 as S          # noqa: E402
import rvmr_spec as RV               # noqa: E402

W31_VERSION = 'MROF-YT-W31-SIZING-1.0'
REGISTRATION = 'MROF_YT_WAVE31_SIZING_REGISTRATION.md'
HISTORY_LEDGER = W25.HISTORY_LEDGER
RVMR_SPEC = os.path.join(RVMR_DIR, 'rvmr_spec.py')
RVMR_SHA16 = 'e348f035a9209540'      # the frozen file, docs/RVMR_V1_SPEC.md
N = S.N_MIN
MARKETS = ('NQ', 'ES', 'RTY')
JUDGED_ON = ('ES', 'RTY')
RULES = ('UNCHANGED', 'ATR', 'RVMR')
MEASURES = ('ATR', 'RVMR')
STRATEGIES = ('A', 'B')
A_MINUTE = 5                         # 09:35
HALF = 0.5
ATR_HIGH = 1.5
USUAL_N = 14
SHARPE_GAIN = 1.05
DECISIONS = (A_MINUTE,) + tuple(S.B_TIMES)


def rvmr_unchanged():
    """Stop unless analysis/rvmr/rvmr_spec.py is the frozen file."""
    try:
        with open(RVMR_SPEC, 'rb') as fh:
            got = hashlib.sha256(fh.read()).hexdigest()
    except OSError as exc:
        raise CX.ContextDataError('the frozen RVMR file cannot be read '
                                  '(%s). Nothing was read.' % exc)
    if not got.startswith(RVMR_SHA16):
        raise CX.ContextDataError(
            'analysis/rvmr/rvmr_spec.py is not the frozen RVMR file (sha256 '
            '%s..., frozen %s...). A changed tool is a new tool. Nothing was '
            'read.' % (got[:16], RVMR_SHA16))
    return got


# ---------------------------------------------------------------------
# section 3: the two measures at each decision minute
# ---------------------------------------------------------------------
def series(rd, chain):
    """(rows, where): rows = [(key, high, low, close)] of each trading
    day's front contract in time order, overnight included; where =
    {session: (first row, end, [keys])}."""
    rows, where = [], {}
    for r in chain:
        st = rd.days.get((r['contract'], r['session']))
        if st is None:
            continue
        b = st['bars']
        idx = sorted(range(len(b) // 4), key=lambda k: b[4 * k])
        start = len(rows)
        rows.extend((b[4 * k], b[4 * k + 1], b[4 * k + 2], b[4 * k + 3])
                    for k in idx)
        where[r['session']] = (start, len(rows),
                               [b[4 * k] for k in idx])
    return rows, where


def decision_row(where, session, j):
    """The row of the last completed bar ending at or before minute j
    after 09:30 (a bar is keyed by its start), or None."""
    w = where.get(session)
    if w is None:
        return None
    start, _end, keys = w
    k = bisect.bisect_left(keys, S.OPEN_S + j * 60)
    return start + k - 1 if k > 0 else None


def states(rd, chain, order):
    """{session: {minute: dict(rvmr, score, atr, usual, ratio)}} at every
    decision minute of every eligible session."""
    rows, where = series(rd, chain)
    score = RV.trailing_ratio([h - lo for _k, h, lo, _c in rows])
    atr = RV.atr20([(None, None, h, lo, c, None) for _k, h, lo, c in rows])
    hist = {j: [] for j in DECISIONS}
    out = {}
    for s in order:
        out[s] = {}
        for j in DECISIONS:
            i = decision_row(where, s, j)
            sc = score[i] if i is not None else None
            a = atr[i] if i is not None else None
            prev = hist[j][-USUAL_N:]
            usual = sum(prev) / len(prev) if len(prev) == USUAL_N else None
            out[s][j] = dict(
                score=sc, rvmr=RV.bucket(sc), atr=a, usual=usual,
                ratio=(a / usual) if a is not None and usual else None)
            if a is not None:
                hist[j].append(a)
    return out


def high(rule, st):
    if rule == 'RVMR':
        return st['rvmr'] == 'HIGH'
    if rule == 'ATR':
        return st['ratio'] is not None and st['ratio'] >= ATR_HIGH
    return False


def factor(rule, st):
    return HALF if high(rule, st) else 1.0


# ---------------------------------------------------------------------
# section 4: A and B with the size of each decision scaled
# ---------------------------------------------------------------------
def day_b_scaled(d, sigma, fac):
    """(gross, cost, changes) of B on one session in units of the open,
    with the position taken at each change multiplied by fac(j). With
    fac = 1 everywhere this is wave twenty-four's day_b step for step."""
    pos, want_was, pts, cost, n = 0.0, 0, 0.0, 0.0, 0
    last = None
    for j in S.B_TIMES + (N,):
        p = d.p(j)
        if last is not None:
            pts += pos * (p - last)
        want = 0 if j == N else W26.b_want(d, sigma, j)
        if want != want_was:
            new = want * fac(j) if want else 0.0
            cost += S.SIDE * abs(new - pos)
            n += 1
            pos, want_was = new, want
        last = p
    return pts / d.o, cost / d.o, n


def a_series(days, order, st, rule):
    """[(session, x)]: A's net basis points in its source's sizing, the
    trade halved when decided in a HIGH state; 0 without a trade."""
    out = []
    for s in order:
        t = W26.a_core(days[s])
        x = 0.0
        if t:
            x = 1e4 * t['lev'] * (t['gross'] - t['cost']) * \
                factor(rule, st[s][A_MINUTE])
        out.append((s, x))
    return out


def b_series(days, order, bi, st, rule):
    """[(session, x)] of B on the sessions with its bounds and its
    volatility, each position halved when decided in a HIGH state."""
    out = []
    for s in order:
        if s not in bi:
            continue
        sigma, vol = bi[s]
        g, c, n = day_b_scaled(days[s], sigma,
                               lambda j, s=s: factor(rule, st[s][j]))
        x = 1e4 * min(S.B_VOL_TARGET / vol, S.B_MAX_LEV) * (g - c) if n \
            else 0.0
        out.append((s, x))
    return out


# ---------------------------------------------------------------------
# section 5: the numbers
# ---------------------------------------------------------------------
def perf(pairs):
    """dict(sessions, mean, sd, sharpe, fall, fall_ratio, halves)."""
    v = [x for _s, x in pairs]
    out = dict(sessions=len(v), mean=None, sd=None, sharpe=None, fall=None,
               fall_ratio=None, halves={})
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
    for h in S.HALVES:
        hv = [x for s, x in pairs if S.half_of(s) == h]
        hs = S.stdev(hv) if len(hv) > 1 else 0.0
        out['halves'][h] = round(S.mean(hv) / hs, 6) if hs > 0 else None
    return out


def judge_all(days, order, chain, rd):
    bi = W26.b_inputs(days, order, chain)
    st = states(rd, chain, order)
    res = collections.OrderedDict()
    for strat in STRATEGIES:
        res[strat] = collections.OrderedDict()
        for rule in RULES:
            ser = a_series(days, order, st, rule) if strat == 'A' else \
                b_series(days, order, bi, st, rule)
            res[strat][rule] = perf(ser)
    together = collections.OrderedDict()
    for rule in RULES:
        a = dict(a_series(days, order, st, rule))
        together[rule] = perf([(s, a[s] + x) for s, x in
                               b_series(days, order, bi, st, rule)])
    # beside: how often each measure is HIGH, and A before halving
    share = {}
    a_trades = [(s, W26.a_core(days[s])) for s in order]
    a_trades = [(s, t) for s, t in a_trades if t]
    b_dec = []
    for s in order:
        if s in bi:
            for j, _delta in W26.TC.b_changes(days[s], bi[s][0]):
                if j != N:
                    b_dec.append(st[s][j])
    for m in MEASURES:
        on = [1e4 * t['lev'] * (t['gross'] - t['cost']) for s, t in a_trades
              if high(m, st[s][A_MINUTE])]
        off = [1e4 * t['lev'] * (t['gross'] - t['cost'])
               for s, t in a_trades if not high(m, st[s][A_MINUTE])]
        share[m] = dict(
            a_decisions=len(a_trades),
            a_high=round(len(on) / float(len(a_trades)), 4)
            if a_trades else None,
            b_decisions=len(b_dec),
            b_high=round(sum(1 for x in b_dec if high(m, x)) /
                         float(len(b_dec)), 4) if b_dec else None,
            a_mean_high=round(S.mean(on), 4) if on else None,
            a_mean_other=round(S.mean(off), 4) if off else None)
    unavailable = sum(1 for s in order if st[s][A_MINUTE]['score'] is None)
    return dict(rules=res, together=together, high_share=share,
                rvmr_unavailable_at_a=unavailable)


# ---------------------------------------------------------------------
# the reads and the verdict
# ---------------------------------------------------------------------
def run_market(path, market, stamps_tz='UTC', stamps='end', gaps_ok=False):
    if market not in MARKETS:
        raise CX.ContextDataError('--market is one of %s'
                                  % ', '.join(MARKETS))
    rvmr_unchanged()
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
        res = judge_all(days, order, chain, rd)
    rep = dict(
        wave31=W31_VERSION, registration=REGISTRATION, part='market',
        market=market, files=len(rd.files), stamp_check=chk,
        sessions=len(order), first_session=order[0],
        last_session=order[-1], gaps=[list(x) for x in g],
        costs=dict(tick=c['tick'], round_trip=c['rt'], stop=c['stop']),
        n_trades=res['rules']['A']['UNCHANGED']['sessions'])
    rep.update(res)
    return rep


def better(by, strat, m):
    """Whether measure m is BETTER than UNCHANGED for strat on each of
    ES and RTY."""
    for mk in JUDGED_ON:
        r = by[mk]['rules'][strat]
        u, x = r['UNCHANGED'], r[m]
        if u['sharpe'] is None or x['sharpe'] is None or u['sharpe'] <= 0:
            return False
        if x['sharpe'] < SHARPE_GAIN * u['sharpe']:
            return False
        if u['fall_ratio'] is None or x['fall_ratio'] is None or \
                x['fall_ratio'] >= u['fall_ratio']:
            return False
    return True


def decide(reps, passed=None):
    """The verdict per rule. passed: {'A': bool, 'B': bool}, whether the
    rule passed wave twenty-five (None: not yet known)."""
    for r in reps:
        if r.get('wave31') != W31_VERSION or r.get('part') != 'market':
            raise CX.ContextDataError('a report is not a market report of '
                                      '%s. Nothing was decided.'
                                      % W31_VERSION)
    by = {}
    for r in reps:
        if r['market'] in by:
            raise CX.ContextDataError('two reports of %s. Nothing was '
                                      'decided.' % r['market'])
        by[r['market']] = r
    missing = [m for m in JUDGED_ON if m not in by]
    if missing:
        raise CX.ContextDataError('the reports of %s are needed. Nothing '
                                  'was decided.' % ', '.join(missing))
    out = collections.OrderedDict()
    for strat in STRATEGIES:
        ok = {m: better(by, strat, m) for m in MEASURES}
        rv_beats = all(
            (by[mk]['rules'][strat]['RVMR']['sharpe'] or 0.0) >=
            (by[mk]['rules'][strat]['ATR']['sharpe'] or 0.0)
            for mk in JUDGED_ON)
        goes = 'RVMR' if ok['RVMR'] and rv_beats else (
            'ATR' if ok['ATR'] else None)
        note = None
        if goes and passed is not None and not passed.get(strat):
            note = ('%s did not pass wave twenty-five: nothing goes on for '
                    'it.' % strat)
            goes = None
        elif goes and passed is None:
            note = ('goes on only if %s passes wave twenty-five'
                    % strat)
        out[strat] = dict(better=ok, rvmr_beats_atr=rv_beats, goes_on=goes,
                          note=note)
    return dict(wave31=W31_VERSION, part='decide', rules=out,
                markets=sorted(by))


# ---------------------------------------------------------------------
# text, ledger, command
# ---------------------------------------------------------------------
def _f(x, fmt='%+.4f'):
    return 'n/a' if x is None else fmt % x


def text(rep):
    L = []
    if rep['part'] == 'market':
        L += ['%s  %s  %d sessions (%s .. %s)' % (
            rep['wave31'], rep['market'], rep['sessions'],
            rep['first_session'], rep['last_session']),
            'A and B, each position halved when decided in a HIGH state '
            '(bp of capital, the source\'s sizing).', '',
            '        rule        sessions   mean      Sharpe    fall '
            'ratio   H1 Sharpe  H2 Sharpe']
        for strat in STRATEGIES + ('A+B',):
            tab = rep['rules'][strat] if strat != 'A+B' else rep['together']
            for rule, v in tab.items():
                L.append('  %-4s  %-10s  %6d  %8s  %9s  %10s  %9s  %9s' % (
                    strat, rule, v['sessions'], _f(v['mean'], '%+.3f'),
                    _f(v['sharpe']), _f(v['fall_ratio'], '%.1f'),
                    _f(v['halves'].get('H1')), _f(v['halves'].get('H2'))))
            L.append('')
        L.append('How often a decision is HIGH (reported):')
        for m, v in rep['high_share'].items():
            L.append('  %-4s  A: %s of %d (A\'s mean %s when HIGH, %s '
                     'otherwise, bp)   B: %s of %d changes' % (
                         m, _f(v['a_high'], '%.2f'), v['a_decisions'],
                         _f(v['a_mean_high'], '%+.2f'),
                         _f(v['a_mean_other'], '%+.2f'),
                         _f(v['b_high'], '%.2f'), v['b_decisions']))
        L.append('  RVMR unavailable at 09:35 (warming up): %d sessions'
                 % rep['rvmr_unavailable_at_a'])
    else:
        for strat, v in rep['rules'].items():
            L.append('%s: ATR %s, RVMR %s; RVMR at least ATR on both: %s -> '
                     'GOES ON: %s%s' % (
                         strat, 'BETTER' if v['better']['ATR'] else 'not',
                         'BETTER' if v['better']['RVMR'] else 'not',
                         'yes' if v['rvmr_beats_atr'] else 'no',
                         v['goes_on'] or 'neither',
                         ' (%s)' % v['note'] if v['note'] else ''))
    L.append('Minute bars, costs charged; not P&L. No order was placed.')
    return '\n'.join(L)


def read_made(path, market):
    return any(r.get('version') == W31_VERSION and r.get('part') == 'market'
               and r.get('market') == market
               for r in W25.ledger_doc(path).get('reads', []))


def record_read(rep, path):
    doc = W25.ledger_doc(path)
    doc.setdefault('reads', []).append(dict(
        version=W31_VERSION, part='market', market=rep['market'],
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
    market = (arg('--market') or '').upper()
    if market not in MARKETS:
        print('STOPPED: --market is one of %s.' % ', '.join(MARKETS))
        return 2
    stz = (arg('--stamps-tz') or 'UTC').upper()
    stp = (arg('--stamps') or 'end').lower()
    ledger = ledger or os.path.join(HERE, HISTORY_LEDGER)
    out = arg('--out')
    if out and not W25.can_write(out):
        print('STOPPED: %s cannot be written (does the folder exist?). '
              'Nothing was read.' % out)
        return 2
    try:
        if read_made(ledger, market):
            print('REFUSED: this wave has read %s (%s). Each read is made '
                  'once.' % (market, HISTORY_LEDGER))
            return 2
        rep = run_market(argv[0], market, stz, stp, '--gaps-ok' in argv)
        n = record_read(rep, ledger)
    except CX.ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
    print(text(rep))
    if out:
        print('\nwave-thirty-one report -> %s' % out)
    print('read recorded (%d read(s) in %s)' % (n, HISTORY_LEDGER))
    return 0


if __name__ == '__main__':
    sys.exit(main())
