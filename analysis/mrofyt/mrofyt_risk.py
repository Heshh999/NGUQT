#!/usr/bin/env python3
"""mrofyt_risk.py - MROF-YT-RISK-1.0

What a run of trades from a scored pattern could feel like: drawdowns,
losing streaks, bad days, and a contract count that keeps a bad case
inside a risk budget. Built from the trades one account could take (one
position at a time, net of costs from mrofyt_costs).

Three scenarios, because the sample's average is the least certain
number in it:

    as sampled     each trade drawn from the sample as it is
    half the edge  every trade's gross result moved down by half the
                   sample's average, costs still charged
    no edge        moved down by all of it: the pattern was luck, and
                   what is left is the costs and the noise

Each simulated session takes its number of trades from a real session
of the sample (quiet sessions included, unless --active-days), and each
trade is drawn individually, so a streak can be longer than any the few
sampled days happened to contain. When the sample has 20 or more
sessions with a trade, whole recorded sessions are also resampled as
they happened ("as recorded"). Contracts are sized on the HALF-EDGE
scenario, never on the sample's own average.

    python3 mrofyt_risk.py w3.json                        # Holm survivor(s)
    python3 mrofyt_risk.py w3.json --pattern L2 --stop 60 --instrument NQ \\
        --days 250 --daily-stop 40 --account 50000 --max-dd-pct 20

A simulation of the sample is only as good as the sample. Built from 15
September sessions it inherits all of their flaws; it is a feel for the
size of the swings, never a forecast. Nothing here is a reason to trade.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import json
import math
import random
import sys

import mrofyt_costs as CO

RISK_VERSION = 'MROF-YT-RISK-1.0'
SEED = 20261026
SIMS = 5000
DAYS = 250
PCTS = (5, 25, 50, 75, 95)
MIN_SESSIONS_RELIABLE = 20
SCENARIOS = (('as sampled', 1.0), ('half the edge', 0.5), ('no edge', 0.0))
SIZING_SCENARIO = 'half the edge'


def trades_by_session(rep, pattern, instrument, stop_key,
                      spread_ticks=CO.SPREAD_TICKS,
                      stop_slip_ticks=CO.STOP_SLIP_TICKS, commission_rt=None):
    """{session: [(gross points, cost points)]} in time order, for the
    trades one account could take."""
    rows = CO.one_at_a_time(CO.scored(rep.get('events', []), pattern,
                                      instrument, stop_key))
    out = {}
    for e, sc in rows:
        c = CO.cost_ticks(instrument, sc['outcome'], spread_ticks,
                          stop_slip_ticks, commission_rt)
        out.setdefault(e['session'], []).append(
            (sc['value_ticks'] / CO.TICKS_PER_POINT, c / CO.TICKS_PER_POINT))
    return out


def scenario_nets(by_session, edge):
    """{session: [net points]} with every gross result moved down by
    (1 - edge) x the sample's average gross; costs unchanged."""
    flat = [g for v in by_session.values() for g, _c in v]
    mean = sum(flat) / len(flat) if flat else 0.0
    shift = (1.0 - edge) * mean
    return {s: [g - shift - c for g, c in v] for s, v in by_session.items()}


def path_stats(days, daily_stop=None):
    """days: [[net points per trade]] in order. Applies the daily stop
    (no further trade once the day is down that much), then measures
    the equity path trade by trade."""
    eq = peak = 0.0
    max_dd = 0.0
    streak = longest = 0
    n = 0
    worst_day = 0.0
    losing_days = stop_days = 0
    for day in days:
        day_pnl = 0.0
        for x in day:
            if daily_stop is not None and day_pnl <= -daily_stop:
                break
            day_pnl += x
            n += 1
            eq += x
            if eq > peak:
                peak = eq
            if peak - eq > max_dd:
                max_dd = peak - eq
            if x < 0:
                streak += 1
                longest = max(longest, streak)
            else:
                streak = 0
        if daily_stop is not None and day_pnl <= -daily_stop:
            stop_days += 1
        if day_pnl < 0:
            losing_days += 1
        worst_day = min(worst_day, day_pnl)
    return dict(total=eq, max_dd=max_dd, longest_losing_streak=longest,
                trades=n, worst_day=worst_day, losing_days=losing_days,
                daily_stop_days=stop_days)


def _pct(vals, p):
    v = sorted(vals)
    if not v:
        return None
    k = (len(v) - 1) * p / 100.0
    lo = int(math.floor(k))
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def simulate(sessions, nets, days=DAYS, sims=SIMS, seed=SEED,
             daily_stop=None, mode='trades'):
    """mode 'trades': a session's trade COUNT is drawn from a real
    session, each trade individually from the pooled trades. mode
    'days': whole recorded sessions, as they happened."""
    rng = random.Random(seed)
    per_day = [nets.get(s, []) for s in sessions]
    pool = [x for v in per_day for x in v]
    if not per_day or not pool:
        return None
    counts = [len(v) for v in per_day]
    res = []
    for _ in range(sims):
        stretch = []
        for _d in range(days):
            if mode == 'days':
                stretch.append(per_day[rng.randrange(len(per_day))])
            else:
                k = counts[rng.randrange(len(counts))]
                stretch.append([pool[rng.randrange(len(pool))]
                                for _k in range(k)])
        res.append(path_stats(stretch, daily_stop))
    out = {}
    for key in ('total', 'max_dd', 'longest_losing_streak', 'trades',
                'worst_day', 'losing_days', 'daily_stop_days'):
        out[key] = {('p%d' % p): round(_pct([r[key] for r in res], p), 2)
                    for p in PCTS}
    out['share_of_stretches_losing'] = round(
        sum(1 for r in res if r['total'] < 0) / float(sims), 4)
    return out


def expected_longest_streak(n_trades, p_loss):
    """The textbook approximation log(n * p_win) / log(1 / p_loss)."""
    if not n_trades or n_trades <= 0 or not 0.0 < p_loss < 1.0:
        return None
    return math.log(n_trades * (1.0 - p_loss)) / math.log(1.0 / p_loss)


def contracts_for(account, max_dd_pct, dd_points, instrument):
    if not account or not dd_points or dd_points <= 0:
        return None
    return int(math.floor(account * max_dd_pct / 100.0 /
                          (dd_points * CO.POINT_VALUE[instrument])))


def risk_report(rep, pattern, stop_key, instrument, days=DAYS, sims=SIMS,
                seed=SEED, daily_stop=None, active_days=False, account=None,
                max_dd_pct=20.0, spread_ticks=CO.SPREAD_TICKS,
                stop_slip_ticks=CO.STOP_SLIP_TICKS, commission_rt=None):
    by = trades_by_session(rep, pattern, instrument, stop_key, spread_ticks,
                           stop_slip_ticks, commission_rt)
    flat = [g - c for v in by.values() for g, c in v]
    sessions = sorted(by) if active_days else \
        sorted(set(rep.get('sessions_inspected') or []) | set(by))
    out = dict(risk=RISK_VERSION, source=rep.get('wave3'),
               source_unblind=rep.get('unblind'), pattern=pattern,
               stop_ticks=float(stop_key), instrument=instrument,
               sessions_resampled=sessions, active_days_only=active_days,
               days_per_stretch=days, sims=sims, seed=seed,
               daily_stop_points=daily_stop,
               costs=dict(spread_ticks=spread_ticks,
                          stop_slip_ticks=stop_slip_ticks,
                          commission_round_trip_dollars=(
                              CO.COMMISSION_RT[instrument]
                              if commission_rt is None else commission_rt)),
               sample=dict(trades=len(flat), sessions_with_trades=len(by),
                           net_points_per_trade=(round(sum(flat) / len(flat),
                                                       3) if flat else None),
                           losing_share=(round(sum(1 for x in flat if x < 0) /
                                               float(len(flat)), 4)
                                         if flat else None)))
    if not flat:
        out['note'] = 'no resolved trades for this pattern and stop'
        return out
    if len(by) < MIN_SESSIONS_RELIABLE:
        out['warning'] = (
            'only %d session(s) had a trade. Every number below leans on '
            'them; the "as sampled" row is the most fragile, and sizing '
            'uses the half-edge row for that reason' % len(by))
    scen = []
    for label, edge in SCENARIOS:
        nets = scenario_nets(by, edge)
        sim = simulate(sessions, nets, days, sims, seed, daily_stop, 'trades')
        allv = [x for v in nets.values() for x in v]
        scen.append(dict(scenario=label, edge=edge, mode='trades',
                         net_points_per_trade=round(sum(allv) / len(allv), 3),
                         simulated=sim))
    if len(by) >= MIN_SESSIONS_RELIABLE:
        sim = simulate(sessions, scenario_nets(by, 1.0), days, sims, seed,
                       daily_stop, 'days')
        scen.append(dict(scenario='as recorded (whole sessions)', edge=1.0,
                         mode='days',
                         net_points_per_trade=out['sample'][
                             'net_points_per_trade'], simulated=sim))
    out['scenarios'] = scen
    base = scen[0]['simulated']
    out['textbook_longest_losing_streak'] = round(
        expected_longest_streak(base['trades']['p50'],
                                out['sample']['losing_share']) or 0, 1)
    pv = CO.POINT_VALUE[instrument]
    for s in scen:
        m = s['simulated']
        s['per_contract_dollars'] = dict(
            max_dd_p50=round(m['max_dd']['p50'] * pv, 0),
            max_dd_p95=round(m['max_dd']['p95'] * pv, 0),
            worst_day_p5=round(m['worst_day']['p5'] * pv, 0))
    if account:
        sz = [s for s in scen if s['scenario'] == SIZING_SCENARIO][0]
        # a scenario that loses money on average sizes to nothing: a
        # drawdown budget is no reason to hold a losing bet
        n_c = 0 if sz['net_points_per_trade'] <= 0 else contracts_for(
            account, max_dd_pct, sz['simulated']['max_dd']['p95'],
            instrument)
        out['sizing'] = dict(
            account=account, max_dd_pct=max_dd_pct, scenario=SIZING_SCENARIO,
            contracts=n_c,
            rule='largest whole number of contracts whose 95th-percentile '
                 'drawdown in the half-edge scenario stays within '
                 'max_dd_pct of the account; none when that scenario loses '
                 'money on average')
    return out


def text(out):
    s = out['sample']
    lines = ['%s  %s stop %g ticks on %s  (source %s, unblind=%s)'
             % (out['risk'], out['pattern'], out['stop_ticks'],
                out['instrument'], out['source'], out['source_unblind']),
             'sample: %d trades one at a time on %d sessions, net %s pts per '
             'trade after costs, %s of trades lose' % (
                 s['trades'], s['sessions_with_trades'],
                 s['net_points_per_trade'], s['losing_share'])]
    if 'scenarios' not in out:
        lines.append(out.get('note', ''))
        return '\n'.join(lines)
    if out.get('warning'):
        lines.append('WARNING: ' + out['warning'])
    lines.append('%d sessions per stretch (%s), %d stretches%s' % (
        out['days_per_stretch'],
        'trading days only' if out['active_days_only']
        else 'quiet days included', out['sims'],
        ', daily stop %g pts' % out['daily_stop_points']
        if out['daily_stop_points'] else ''))
    lines.append('')
    lines.append('%-30s %8s %9s %9s %9s %9s %8s %7s' % (
        'scenario', 'pts/trd', 'total p5', 'total p50', 'dd p50', 'dd p95',
        'streak95', 'losing'))
    for sc in out['scenarios']:
        m = sc['simulated']
        lines.append('%-30s %+8.2f %9.0f %9.0f %9.0f %9.0f %8.0f %6.1f%%' % (
            sc['scenario'], sc['net_points_per_trade'], m['total']['p5'],
            m['total']['p50'], m['max_dd']['p50'], m['max_dd']['p95'],
            m['longest_losing_streak']['p95'],
            100 * m['share_of_stretches_losing']))
    lines.append('(points per stretch; dd = worst drawdown; streak95 = the '
                 'longest losing streak in a bad stretch; losing = share of '
                 'stretches that end below zero)')
    lines.append('textbook longest losing streak for this many trades: about '
                 '%s' % out['textbook_longest_losing_streak'])
    lines.append('')
    lines.append('worst drawdown per contract, in dollars (median / bad '
                 'case):')
    for sc in out['scenarios']:
        d = sc['per_contract_dollars']
        lines.append('  %-30s $%s / $%s' % (sc['scenario'], d['max_dd_p50'],
                                             d['max_dd_p95']))
    if out.get('sizing'):
        z = out['sizing']
        if z['contracts'] == 0:
            lines.append('sizing (%s scenario): none. At half the sampled '
                         'edge this loses money after costs, or one '
                         'contract already breaks the %g%% budget'
                         % (z['scenario'], z['max_dd_pct']))
        else:
            lines.append('sizing (%s scenario): %s contract(s) keep the '
                         'bad-case drawdown under %g%% of $%s' % (
                             z['scenario'], z['contracts'], z['max_dd_pct'],
                             z['account']))
    lines.append('')
    lines.append('A resampling of the sample, not a forecast: it cannot '
                 'show a market the sample never saw. No order was placed.')
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
    rep = CO.load_report(argv[0])
    pat = arg('--pattern')
    if pat:
        stop = arg('--stop')
        if stop is None:
            print('--pattern needs --stop (ticks, e.g. 60)')
            return 2
        targets = [(pat, '%g' % float(stop))]
    else:
        targets = CO.default_targets(rep)
        if not targets:
            print('no pattern survived its luck check in this report; name '
                  'one with --pattern and --stop')
            return 2
    insts = [arg('--instrument')] if arg('--instrument') else ['NQ']
    outs = []
    for p, sk in targets:
        for inst in insts:
            com = arg('--commission-%s' % inst.lower(), float)
            out = risk_report(
                rep, p, sk, inst, arg('--days', int, DAYS),
                arg('--sims', int, SIMS), arg('--seed', int, SEED),
                arg('--daily-stop', float), '--active-days' in argv,
                arg('--account', float), arg('--max-dd-pct', float, 20.0),
                arg('--spread', float, CO.SPREAD_TICKS),
                arg('--stop-slip', float, CO.STOP_SLIP_TICKS), com)
            print(text(out))
            print('')
            outs.append(out)
    dest = arg('--out')
    if dest:
        with open(dest, 'w') as fh:
            json.dump(outs, fh, indent=1)
        print('risk report -> %s' % dest)
    return 0


if __name__ == '__main__':
    sys.exit(main())
