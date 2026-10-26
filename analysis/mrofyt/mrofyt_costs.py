#!/usr/bin/env python3
"""mrofyt_costs.py - MROF-YT-COSTS-1.0

What a mid-to-mid path result keeps after trading costs. Every number
the waves report is mid-to-mid: entry and exit at the mid, no
commission. This tool charges each scored event a round-trip cost and
reports what is left, for every event and for the events a single
account could actually take (one position at a time).

    commission   dollars per round trip (commission + exchange + NFA +
                 clearing, all in) / dollars per tick
    entry        half the spread: a market order pays from the mid to
                 the far side of the book
    exit         half the spread: every exit is charged as a market
                 order sent when the mid condition is met. A resting
                 limit at the target would save it, and might not fill;
                 charging it is the conservative side
    stop slip    extra ticks on STOP exits only: stops fill late in the
                 fast markets that trigger them

The defaults are typical retail figures, not this operator's. Replace
them with the round trip on your own statement (--commission-nq,
--commission-mnq). A sensitivity table shows how the result moves with
the spread and the stop slippage, because those are the two numbers a
tape cannot tell you in advance.

    python3 mrofyt_costs.py w3.json                    # Holm survivors
    python3 mrofyt_costs.py w3.json --pattern L2 --stop 60 --out c.json

Costs are accounting, not a rule: nothing here changes a threshold, a
stop, a target or an exit of any wave. A pattern is judged on what its
registration says; this tool says what would have been kept.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import collections
import gzip
import json
import sys

COSTS_VERSION = 'MROF-YT-COSTS-1.0'
TICK = 0.25
TICKS_PER_POINT = 4.0
POINT_VALUE = dict(NQ=20.0, MNQ=2.0)          # dollars per point
COMMISSION_RT = dict(NQ=5.00, MNQ=2.00)       # dollars, all in, typical
SPREAD_TICKS = 1.0                            # NQ in cash hours, usually
STOP_SLIP_TICKS = 1.0
SENS_SPREAD = (1.0, 2.0)
SENS_SLIP = (0.0, 1.0, 2.0, 4.0)
RESOLVED = ('TARGET', 'STOP', 'TIMEOUT')


def tick_value(instrument):
    return POINT_VALUE[instrument] / TICKS_PER_POINT


def cost_ticks(instrument, outcome, spread_ticks=SPREAD_TICKS,
               stop_slip_ticks=STOP_SLIP_TICKS, commission_rt=None):
    """Round-trip cost of one trade, in ticks of that instrument."""
    com = COMMISSION_RT[instrument] if commission_rt is None \
        else commission_rt
    c = com / tick_value(instrument) + spread_ticks   # half in, half out
    if outcome == 'STOP':
        c += stop_slip_ticks
    return c


def load_report(path):
    opener = gzip.open if path.endswith('.gz') else open
    with opener(path, 'rt') as fh:
        return json.load(fh)


def scored(events, pattern, instrument, stop_key):
    """Events of one pattern and instrument that resolved at this stop,
    in time order: [(event, score)]."""
    out = []
    for e in events:
        if e.get('family') != pattern or e.get('instrument') != instrument:
            continue
        sc = (e.get('scores') or {}).get(stop_key)
        if not sc or sc.get('outcome') not in RESOLVED:
            continue
        out.append((e, sc))
    out.sort(key=lambda x: x[0]['t'])
    return out


def one_at_a_time(rows):
    """The events one account could take: an event is skipped while the
    previously taken one is still open (until its resolution)."""
    taken, busy = [], None
    for e, sc in rows:
        if busy is not None and e['t'] < busy:
            continue
        taken.append((e, sc))
        busy = e['t'] + float(sc.get('seconds') or 0.0)
    return taken


def summarize(rows, instrument, spread_ticks=SPREAD_TICKS,
              stop_slip_ticks=STOP_SLIP_TICKS, commission_rt=None):
    n = len(rows)
    if not n:
        return dict(n=0)
    gross = [sc['value_ticks'] for _e, sc in rows]
    cost = [cost_ticks(instrument, sc['outcome'], spread_ticks,
                       stop_slip_ticks, commission_rt) for _e, sc in rows]
    net = [g - c for g, c in zip(gross, cost)]
    by = collections.defaultdict(lambda: [0, 0.0])
    for (e, _sc), x in zip(rows, net):
        b = by[e['session']]
        b[0] += 1
        b[1] += x
    wins = sum(1 for _e, sc in rows if sc['outcome'] == 'TARGET')
    tv = tick_value(instrument)
    mg, mc, mn = sum(gross) / n, sum(cost) / n, sum(net) / n
    return dict(
        n=n, sessions=len(by), targets=wins, hit=round(wins / n, 4),
        gross_points=round(mg / TICKS_PER_POINT, 3),
        cost_points=round(mc / TICKS_PER_POINT, 3),
        net_points=round(mn / TICKS_PER_POINT, 3),
        net_total_points=round(sum(net) / TICKS_PER_POINT, 2),
        net_dollars_per_contract=round(mn * tv, 2),
        # the extra cost per trade, on top of the one charged, that would
        # bring the average to zero
        break_even_extra_points=round(mn / TICKS_PER_POINT, 3),
        sessions_net_positive=sum(1 for b in by.values() if b[1] > 0),
        by_session={s: dict(n=b[0], net_points=round(b[1] / TICKS_PER_POINT,
                                                     2))
                    for s, b in sorted(by.items())})


def sensitivity(rows, instrument, commission_rt=None):
    """Net points per trade over the spread x stop-slippage grid."""
    grid = []
    for sp in SENS_SPREAD:
        row = dict(spread_ticks=sp)
        for sl in SENS_SLIP:
            s = summarize(rows, instrument, sp, sl, commission_rt)
            row['slip_%g' % sl] = s.get('net_points')
        grid.append(row)
    return grid


def default_targets(rep):
    """(pattern, stop) pairs that survived the wave's own luck check."""
    out = []
    for t in rep.get('tests', []):
        if t.get('survives_holm'):
            out.append((t['pattern'], '%g' % t['stop_ticks']))
    return out


def cost_report(rep, targets=None, spread_ticks=SPREAD_TICKS,
                stop_slip_ticks=STOP_SLIP_TICKS, commission=None):
    commission = commission or {}
    targets = default_targets(rep) if targets is None else targets
    insts = sorted({e.get('instrument') for e in rep.get('events', [])
                    if e.get('instrument') in POINT_VALUE})
    out = dict(costs=COSTS_VERSION, source=rep.get('wave3') or
               rep.get('wave4'), source_unblind=rep.get('unblind'),
               sessions_inspected=rep.get('sessions_inspected'),
               assumptions=dict(
                   commission_round_trip_dollars={
                       i: commission.get(i, COMMISSION_RT[i]) for i in insts},
                   spread_ticks=spread_ticks,
                   stop_slip_ticks=stop_slip_ticks,
                   exits='every exit charged as a market order at the mid '
                         'condition: half the spread; stops add the slip'),
               results=[])
    for pat, sk in targets:
        for inst in insts:
            rows = scored(rep.get('events', []), pat, inst, sk)
            com = commission.get(inst)
            taken = one_at_a_time(rows)
            out['results'].append(dict(
                pattern=pat, stop_ticks=float(sk), instrument=inst,
                all_events=summarize(rows, inst, spread_ticks,
                                     stop_slip_ticks, com),
                one_at_a_time=summarize(taken, inst, spread_ticks,
                                        stop_slip_ticks, com),
                sensitivity_one_at_a_time=sensitivity(taken, inst, com)))
    return out


def text(out):
    a = out['assumptions']
    lines = ['%s  on %s  unblind=%s' % (out['costs'], out['source'],
                                       out['source_unblind']),
             'costs per round trip: commission %s dollars all in; spread %g '
             'tick(s) (half in, half out); stops slip %g tick(s)'
             % (', '.join('%s %.2f' % kv for kv in
                          sorted(a['commission_round_trip_dollars'].items())),
                a['spread_ticks'], a['stop_slip_ticks']), '']
    if not out['results']:
        lines.append('nothing to cost: no pattern survived its luck check '
                     'in this report (use --pattern)')
    for r in out['results']:
        lines.append('%s stop %g ticks, %s' % (r['pattern'], r['stop_ticks'],
                                               r['instrument']))
        for k, label in (('all_events', 'every event'),
                         ('one_at_a_time', 'one position at a time')):
            s = r[k]
            if not s.get('n'):
                lines.append('  %-24s n=0' % label)
                continue
            lines.append(
                '  %-24s n=%-4d hit=%.3f  gross %+.2f  cost %.2f  net %+.2f '
                'pts/trade  (%+.2f $/contract; %d of %d sessions net '
                'positive)' % (label, s['n'], s['hit'], s['gross_points'],
                               s['cost_points'], s['net_points'],
                               s['net_dollars_per_contract'],
                               s['sessions_net_positive'], s['sessions']))
        lines.append('  net pts/trade, one at a time, by spread (rows) and '
                     'stop slippage (columns, ticks):')
        lines.append('    spread  ' + '  '.join('%6s' % ('slip %g' % x)
                                                for x in SENS_SLIP))
        for row in r['sensitivity_one_at_a_time']:
            lines.append('    %-6g  ' % row['spread_ticks'] + '  '.join(
                '%+6.2f' % row['slip_%g' % x] if row['slip_%g' % x]
                is not None else '%6s' % '-' for x in SENS_SLIP))
        lines.append('')
    lines.append('Mid-to-mid results with costs charged. Not P&L: no queue, '
                 'no partial fills, no latency. No order was placed.')
    return '\n'.join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('--'):
        print(__doc__)
        return 2

    def arg(name, cast=str, default=None):
        if name in argv:
            return cast(argv[argv.index(name) + 1])
        return default
    rep = load_report(argv[0])
    pat = arg('--pattern')
    targets = None
    if pat:
        stops = [arg('--stop')] if arg('--stop') else \
            sorted({'%g' % t['stop_ticks'] for t in rep.get('tests', [])
                    if t.get('pattern') == pat}, key=float)
        targets = [(pat, s) for s in stops]
    commission = {}
    if arg('--commission-nq') is not None:
        commission['NQ'] = arg('--commission-nq', float)
    if arg('--commission-mnq') is not None:
        commission['MNQ'] = arg('--commission-mnq', float)
    out = cost_report(rep, targets,
                      arg('--spread', float, SPREAD_TICKS),
                      arg('--stop-slip', float, STOP_SLIP_TICKS),
                      commission)
    print(text(out))
    dest = arg('--out')
    if dest:
        with open(dest, 'w') as fh:
            json.dump(out, fh, indent=1)
        print('\ncosts report -> %s' % dest)
    return 0


if __name__ == '__main__':
    sys.exit(main())
