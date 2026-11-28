#!/usr/bin/env python3
"""mrofyt_stress35.py - MROF-YT-W35-STRESS-1.0

MROF_YT_WAVE35_STRESS_REGISTRATION.md turned into running code: how
often the account plan would lose the account, from NQ's ten years in
another order. Planning only: it judges nothing.

    the days     wave twenty-six's plan, A and B in MNQ: a session's
                 result in dollars and its lowest value at a minute close
    the sizes    the budgets times 1, 1/2 and 1/4, each without and with
                 the day stop
    a year       252 sessions from blocks of 20 consecutive sessions,
                 5,000 years, random seed 35
    the account  $150,000, lost at $4,500 under its highest end-of-day
                 balance, started again after a loss

    python3 mrofyt_stress35.py "<NQ exports>" --out w35_stress.json
    options: --stamps-tz UTC|ET  --stamps end|start  --gaps-ok

The read is made once and recorded before any result is shown. The
plan, its costs and the account are wave twenty-six's own. Read-only;
no order is placed.
"""
import datetime
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_improve26 as W26       # noqa: E402
import mrofyt_screen15 as S          # noqa: E402

W35_VERSION = 'MROF-YT-W35-STRESS-1.0'
REGISTRATION = 'MROF_YT_WAVE35_STRESS_REGISTRATION.md'
HISTORY_LEDGER = W25.HISTORY_LEDGER
SCALES = (1.0, 0.5, 0.25)
BLOCK, YEAR, RUNS, SEED = 20, 252, 5000, 35
STOPS = ('none', 'day stop')


# ---------------------------------------------------------------------
# sections 1 and 2: the days at a size
# ---------------------------------------------------------------------
def a_micros(risk, scale):
    return max(1, min(W26.MAX_MICROS, int(
        (W26.A_BUDGET * scale) // (risk * W26.MNQ_PT))))


def b_micros(s, o, scale):
    return max(1, min(W26.MAX_MICROS, int(
        W26.B_BUDGET * scale / (s * o * W26.MNQ_PT) + 0.5)))


def plan(days, order, chain, scale=1.0):
    """[(session, A's trade or None, (B's changes, micros) or None)]:
    wave twenty-six's prop_days with both budgets times `scale`."""
    bi = W26.b_inputs(days, order, chain)
    out = []
    for s in order:
        d = days[s]
        a = W26.a_core(d)
        if a:
            a = dict(a, micros=a_micros(a['risk'], scale))
        b = None
        if s in bi:
            ch = W26.TC.b_changes(d, bi[s][0])
            if ch:
                b = (ch, b_micros(bi[s][1], d.o, scale))
        out.append((s, a, b))
    return out


def paths(days, the_plan, day_stop=None):
    """[(result, lowest value)] in dollars, one a session; 0 and 0 on a
    session without a trade."""
    out = []
    for s, a, b in the_plan:
        if not (a or b):
            out.append((0.0, 0.0))
            continue
        res, low, _j = W26.day_path(days[s], a, b, day_stop)
        out.append((res, low))
    return out


# ---------------------------------------------------------------------
# sections 3 and 4: the account, and a year from blocks
# ---------------------------------------------------------------------
def run(seq):
    """(result, accounts lost, largest fall) of the account over the
    sessions `seq` in their order: wave twenty-six's account."""
    bal = peak = W26.ACCOUNT
    cum = top = fall = 0.0
    lost = 0
    for res, low in seq:
        fall = max(fall, top - (cum + low))
        cum += res
        top = max(top, cum)
        if bal + low <= peak - W26.TRAIL:
            lost += 1
            bal = peak = W26.ACCOUNT
            continue
        bal += res
        peak = max(peak, bal)
    return cum, lost, fall


def a_year(seq, rng):
    """252 sessions from blocks of 20 consecutive ones; a block that
    reaches the last session goes on from the first."""
    n, out = len(seq), []
    while len(out) < YEAR:
        i = rng.randrange(n)
        out.extend(seq[(i + k) % n] for k in range(BLOCK))
    return out[:YEAR]


def below(values, share):
    """The value that `share` of the sorted values stay below."""
    v = sorted(values)
    return v[min(len(v) - 1, int(share * len(v)))]


def stress(seq, runs=RUNS, seed=SEED):
    rng = random.Random(seed)
    res, lost, falls = [], [], []
    for _k in range(runs):
        r, n, f = run(a_year(seq, rng))
        res.append(r)
        lost.append(n)
        falls.append(f)
    return dict(
        years=runs,
        lost_any=round(sum(1 for n in lost if n) / float(runs), 4),
        lost_a_year=round(S.mean(lost), 4),
        result_p5=round(below(res, 0.05), 2),
        result_median=round(below(res, 0.5), 2),
        result_p95=round(below(res, 0.95), 2),
        fall_median=round(below(falls, 0.5), 2),
        fall_p95=round(below(falls, 0.95), 2))


def history(seq):
    """The history in its own order, in the same terms."""
    r, n, f = run(seq)
    return dict(sessions=len(seq), result=round(r, 2), lost=n,
                largest_fall=round(f, 2),
                result_a_year=round(r * YEAR / len(seq), 2)
                if seq else None)


def all_sizes(days, order, chain, runs=RUNS, seed=SEED):
    out = []
    for scale in SCALES:
        pl = plan(days, order, chain, scale)
        for name in STOPS:
            stop = W26.DAY_STOP * scale if name == 'day stop' else None
            seq = paths(days, pl, stop)
            row = dict(size=scale, day_stop=stop,
                       budgets=dict(A=W26.A_BUDGET * scale,
                                    B=W26.B_BUDGET * scale),
                       history=history(seq))
            row.update(stress(seq, runs, seed))
            out.append(row)
    return out


# ---------------------------------------------------------------------
# the read
# ---------------------------------------------------------------------
def run_nq(path, stamps_tz='UTC', stamps='end', gaps_ok=False, runs=RUNS):
    rd, chk = W25.read(path, 'NQ', stamps_tz, stamps)
    days, order, chain = S.build(rd)
    if len(order) < W25.MIN_SESSIONS:
        raise CX.ContextDataError(
            'only %d usable NQ sessions: this needs years of minute bars. '
            'Nothing was computed.' % len(order))
    g = W25.gaps(chain)
    if g and not gaps_ok:
        raise CX.ContextDataError(
            'the NQ exports have no cash session between %s: a contract was '
            'not exported. Nothing was computed. Export it and run again; '
            'if the feed has no bars for those days, add --gaps-ok.'
            % W25._gap_text(g))
    return dict(
        wave35=W35_VERSION, registration=REGISTRATION, part='stress',
        market='NQ', files=len(rd.files), stamp_check=chk,
        sessions=len(order), first_session=order[0],
        last_session=order[-1], gaps=[list(x) for x in g],
        account=dict(start=W26.ACCOUNT, trail=W26.TRAIL),
        resampling=dict(block=BLOCK, year=YEAR, years=runs, seed=SEED),
        sizes=all_sizes(days, order, chain, runs))


# ---------------------------------------------------------------------
# text, ledger, command
# ---------------------------------------------------------------------
def _d(x):
    return 'n/a' if x is None else '{:+,.0f}'.format(x)


def text(rep):
    rs = rep['resampling']
    L = ['%s  NQ  (%s .. %s)  %d sessions' % (
        rep['wave35'], rep['first_session'], rep['last_session'],
        rep['sessions']),
        'The account plan in another order: %d years of %d sessions from '
        'blocks of %d.' % (rs['years'], rs['year'], rs['block']),
        'Planning only: nothing is judged. Dollars, A and B in MNQ.', '',
        '  size  day stop | history: lost  $ a year | years with a loss  '
        'lost a year |  a year: 5%   median      95% | median fall']
    for r in rep['sizes']:
        h = r['history']
        L.append('  %4.2f  %8s | %13d  %8s | %16.0f%%  %11.2f | %10s  %7s  '
                 '%7s | %11s' % (
                     r['size'],
                     'none' if r['day_stop'] is None else
                     '$%.0f' % r['day_stop'], h['lost'],
                     _d(h['result_a_year']), 100.0 * r['lost_any'],
                     r['lost_a_year'], _d(r['result_p5']),
                     _d(r['result_median']), _d(r['result_p95']),
                     _d(-r['fall_median'])))
    L += ['', 'The account: $%.0f, lost at $%.0f under its highest '
          'end-of-day balance.' % (rep['account']['start'],
                                   rep['account']['trail']),
          'Not a forecast: later days are assumed to be like these. If B '
          'stops working, the truth is worse.',
          'Minute bars, costs charged; not P&L. No order was placed.']
    return '\n'.join(L)


def read_made(path):
    return any(r.get('version') == W35_VERSION
               for r in W25.ledger_doc(path).get('reads', []))


def record_read(rep, path):
    doc = W25.ledger_doc(path)
    doc.setdefault('reads', []).append(dict(
        version=W35_VERSION, part=rep['part'], market=rep['market'],
        first=rep['first_session'], last=rep['last_session'],
        n=rep['sessions'],
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


def main(argv=None, ledger=None, runs=RUNS):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('--'):
        print(__doc__)
        return 2

    def arg(k):
        i = argv.index(k) + 1 if k in argv else len(argv)
        return argv[i] if i < len(argv) else None
    stz = (arg('--stamps-tz') or 'UTC').upper()
    stp = (arg('--stamps') or 'end').lower()
    ledger = ledger or os.path.join(HERE, HISTORY_LEDGER)
    out = arg('--out')
    if out and not W25.can_write(out):
        print('STOPPED: %s cannot be written (does the folder exist?). '
              'Nothing was read.' % out)
        return 2
    try:
        if read_made(ledger):
            print('REFUSED: this wave has read NQ (%s). Each read is made '
                  'once.' % HISTORY_LEDGER)
            return 2
        rep = run_nq(argv[0], stz, stp, '--gaps-ok' in argv, runs)
        n = record_read(rep, ledger)
    except CX.ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
    print(text(rep))
    if out:
        print('\nwave-thirty-five report -> %s' % out)
    print('read recorded (%d read(s) in %s)' % (n, HISTORY_LEDGER))
    return 0


if __name__ == '__main__':
    sys.exit(main())
