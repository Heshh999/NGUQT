#!/usr/bin/env python3
# MROF-YT-COSTS-1.0 and MROF-YT-RISK-1.0 suite. Hand-built events check
# the arithmetic; the frozen DEV wave-three report checks that the tools
# reproduce the numbers already recorded in MROF_YT_W3_W4_DEV_FREEZE.md.
# No order, fill or P&L exists anywhere.
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_costs as CO        # noqa: E402
import mrofyt_risk as RK         # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


def ev(t0, out, val, secs, ses='20260901', inst='NQ', fam='L2', stop='60'):
    return dict(t=t0, session=ses, instrument=inst, family=fam,
                scores={stop: dict(outcome=out, value_ticks=val,
                                   seconds=secs)})


# ---------------------------------------------------------------------
# C1-C5: the cost arithmetic
# ---------------------------------------------------------------------
c_t = CO.cost_ticks('NQ', 'TARGET', 1.0, 1.0, 5.0)
c_s = CO.cost_ticks('NQ', 'STOP', 1.0, 1.0, 5.0)
c_m = CO.cost_ticks('MNQ', 'TIMEOUT', 1.0, 1.0, 2.0)
t('C1: round-trip cost in ticks: NQ $5 = 1 tick + 1 tick of spread; a '
  'stop adds its slip; MNQ $2 = 4 ticks + spread',
  abs(c_t - 2.0) < 1e-12 and abs(c_s - 3.0) < 1e-12 and
  abs(c_m - 5.0) < 1e-12)

rows = [(e, e['scores']['60']) for e in
        [ev(0, 'TARGET', 100, 300), ev(100, 'STOP', -60, 50),
         ev(400, 'STOP', -60, 20), ev(410, 'TIMEOUT', 12, 1800),
         ev(2300, 'TARGET', 100, 10)]]
taken = CO.one_at_a_time(rows)
t('C2: one position at a time skips an event while the taken one is open '
  '(resolution = t + seconds) and takes the next one after it closes',
  [e['t'] for e, _ in taken] == [0, 400, 2300])

s = CO.summarize(taken, 'NQ', 1.0, 1.0, 5.0)
gross = (100 - 60 + 100) / 3.0
cost = (2.0 + 3.0 + 2.0) / 3.0
t('C3: gross, cost and net per trade in points; the break-even extra '
  'cost equals the net',
  abs(s['gross_points'] - round(gross / 4, 3)) < 1e-9 and
  abs(s['cost_points'] - round(cost / 4, 3)) < 1e-9 and
  abs(s['net_points'] - round((gross - cost) / 4, 3)) < 1e-9 and
  s['break_even_extra_points'] == s['net_points'] and s['targets'] == 2)

sens = CO.sensitivity(taken, 'NQ', 5.0)
mono = all(row['slip_0'] >= row['slip_1'] >= row['slip_2'] >= row['slip_4']
           for row in sens) and all(
    sens[0]['slip_%g' % x] > sens[1]['slip_%g' % x] for x in CO.SENS_SLIP)
t('C4: the sensitivity grid falls with more stop slippage and a wider '
  'spread', mono)

rep = dict(wave3='X', events=[r[0] for r in rows],
           tests=[dict(pattern='L2', stop_ticks=60.0, survives_holm=True),
                  dict(pattern='G1', stop_ticks=40.0, survives_holm=False)])
t('C5: with no --pattern the tool costs exactly the Holm survivors',
  CO.default_targets(rep) == [('L2', '60')])

# ---------------------------------------------------------------------
# R1-R7: the risk arithmetic
# ---------------------------------------------------------------------
ps = RK.path_stats([[5, -2, -2, -2, 10], [-1, -1], [3]])
t('R1: path stats: total, worst drawdown peak to trough across days, '
  'longest losing streak across a day boundary, worst day, losing days',
  ps['total'] == 10 and ps['max_dd'] == 6 and
  ps['longest_losing_streak'] == 3 and ps['worst_day'] == -2 and
  ps['losing_days'] == 1 and ps['trades'] == 8)

pd = RK.path_stats([[-10, -10, -10, 50], [5]], daily_stop=15)
t('R2: the daily stop ends the day once it is down that much (the third '
  '-10 and the 50 are never taken) and is counted; the next day trades',
  pd['trades'] == 3 and pd['total'] == -15 and pd['daily_stop_days'] == 1)

by = {'a': [(10.0, 1.0), (-5.0, 1.0)], 'b': [(7.0, 1.0)]}
n1 = RK.scenario_nets(by, 1.0)
n0 = RK.scenario_nets(by, 0.0)
mean0 = sum(x for v in n0.values() for x in v) / 3.0
t('R3: scenarios move every gross result down by (1 - edge) x the '
  'average; at no edge the average net is minus the costs',
  n1['a'] == [9.0, -6.0] and abs(mean0 + 1.0) < 1e-12)

sims_a = RK.simulate(['a', 'b', 'q'], n1, days=50, sims=200, seed=7)
sims_b = RK.simulate(['a', 'b', 'q'], n1, days=50, sims=200, seed=7)
t('R4: the simulation is deterministic under its seed', sims_a == sims_b)

flat = {'a': [1.0, 1.0], 'b': [1.0]}
sf = RK.simulate(['a', 'b'], flat, days=20, sims=50, seed=1)
t('R5: a sample of only winners has no drawdown and no losing streak',
  sf['max_dd']['p95'] == 0 and sf['longest_losing_streak']['p95'] == 0)

few = {'a': [1.0, -1.0, 1.0, -1.0]}
st_days = RK.simulate(['a'], few, days=200, sims=200, seed=3, mode='days')
st_trd = RK.simulate(['a'], few, days=200, sims=200, seed=3, mode='trades')
t('R6: drawing trades one by one lets a losing streak run longer than any '
  'recorded session contained (whole-session resampling cannot)',
  st_days['longest_losing_streak']['p95'] == 1 and
  st_trd['longest_losing_streak']['p50'] > 3)

t('R7: sizing: floor(account x budget / (drawdown x $/point)); the '
  'textbook streak for 500 trades at 50 % is about 8',
  RK.contracts_for(50000, 20, 100, 'NQ') == 5 and
  RK.contracts_for(50000, 20, 100, 'MNQ') == 50 and
  abs(RK.expected_longest_streak(500, 0.5) - 7.97) < 0.01)

loser = dict(wave3='X', sessions_inspected=['20260901'],
             events=[ev(i * 4000, 'STOP', -60, 30) for i in range(5)] +
             [ev(30000, 'TARGET', 100, 30)],
             tests=[])
lr = RK.risk_report(loser, 'L2', '60', 'NQ', days=20, sims=50, account=50000)
t('R8: a scenario that loses money sizes to no contracts at all',
  lr['sizing']['contracts'] == 0)

# ---------------------------------------------------------------------
# R9-R10: the frozen DEV report reproduces what the freeze recorded
# ---------------------------------------------------------------------
fz = os.path.join(HERE, 'frozen_dev_20261024', 'w3.json.gz')
w3 = CO.load_report(fz)
cr = CO.cost_report(w3)
nq = [r for r in cr['results'] if r['instrument'] == 'NQ'][0]
t('R9: on the frozen DEV report: L2 at 60 ticks is the only survivor, '
  'every-event gross +5.00 pts on 116, one at a time 57 trades at +6.76 '
  '(MROF_YT_W3_W4_DEV_FREEZE.md section 5)',
  [(r['pattern'], r['stop_ticks']) for r in cr['results']] ==
  [('L2', 60.0), ('L2', 60.0)] and
  nq['all_events']['n'] == 116 and nq['all_events']['gross_points'] == 5.004
  and nq['one_at_a_time']['n'] == 57 and
  nq['one_at_a_time']['gross_points'] == 6.763)

rr = RK.risk_report(w3, 'L2', '60', 'NQ', days=50, sims=100)
t('R10: the risk report on it warns that only 6 sessions had a trade, and '
  'its no-edge scenario loses exactly the costs on average',
  'only 6 session' in rr.get('warning', '') and
  abs(rr['scenarios'][2]['net_points_per_trade'] +
      nq['one_at_a_time']['cost_points']) < 0.002)

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
