#!/usr/bin/env python3
# MROF-YT-OF-01 deterministic fixtures. Synthetic events verify CODE
# BEHAVIOR only — never market evidence. No outcome data exists.
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mrofyt_levels as L   # noqa: E402
import mrofyt_signals as S  # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-62s %s' % (name, 'PASS' if cond else 'FAIL'))


# ---- pivots ----------------------------------------------------------
pv = L.pivots(110, 90, 105)
t('PP=(H+L+C)/3', abs(pv['PP'] - 101.6666667) < 1e-6)
t('M2=(PP+S1)/2 with S1=2PP-H',
  abs(pv['M2'] - (pv['PP'] + (2 * pv['PP'] - 110)) / 2) < 1e-12)
t('M3=(PP+R1)/2 with R1=2PP-L',
  abs(pv['M3'] - (pv['PP'] + (2 * pv['PP'] - 90)) / 2) < 1e-12)
t('S1/R1 computed but not active entry locations',
  'S1' not in L.ACTIVE_LEVEL_IDS and 'R1' not in L.ACTIVE_LEVEL_IDS)

# ---- opens + overnight ----------------------------------------------
ev = [(0, 100.0), (10, 101.0), (3600, 99.0), (34200, 102.0), (34210, 103.0)]
op = L.session_opens(ev, 0, 34200)
t('Globex open != cash open (not interchangeable)',
  op['GLOBEX_OPEN'] == 100.0 and op['CASH_OPEN_0930'] == 102.0)
on1 = L.overnight_extremes(ev, 0, 34200, now_t=30000)
on2 = L.overnight_extremes(ev, 0, 34200, now_t=34200)
t('overnight extremes NOT available before 09:30', on1['available'] is False)
t('overnight extremes fixed at 09:30 (H=101 L=99)',
  on2['available'] and on2['OVERNIGHT_HIGH'] == 101.0 and
  on2['OVERNIGHT_LOW'] == 99.0)

# ---- session VWAP + frozen band -------------------------------------
vw = L.SessionVwap()
for p, v in ((100, 1), (102, 1)):
    vw.update(p, v)
st = vw.state()
t('VWAP volume-weighted (101)', abs(st['SESSION_VWAP'] - 101) < 1e-12)
t('band = VWAP +/- 2 sigma_w (sigma=1)',
  abs(st['VWAP_UPPER'] - 103) < 1e-9 and abs(st['VWAP_LOWER'] - 99) < 1e-9)

# ---- ADR -------------------------------------------------------------
ad = L.adr_state([10] * 14, run_high=105, run_low=100)
t('ADR lines from running extremes (ADR_HIGH=110 ADR_LOW=95)',
  ad['ADR_HIGH'] == 110 and ad['ADR_LOW'] == 95 and ad['ADR_USED'] == 0.5)
t('ADR status is UNVERIFIED_CONTEXT (barred from entry/promotion)',
  ad['status'] == 'UNVERIFIED_CONTEXT')

# ---- PSY construction + audit ---------------------------------------
week = [(0, 100.0), (3600, 108.0), (7 * 3600, 95.0), (9 * 3600, 120.0)]
ps = L.psy_nq_week(week, 0)
t('PSY from first 8h only (H=108 L=95, not the later 120)',
  ps['available'] and ps['PSY_HIGH'] == 108 and ps['PSY_LOW'] == 95)
t('PSY availability stamped at window end', ps['available_from'] == 8 * 3600)
ps2 = L.psy_nq_week([(0, 100.0), (3600, 108.0)], 0)
t('PSY UNAVAILABLE before the 8h window completes',
  ps2['available'] is False)
t('continuous contract fails the PSY audit',
  L.psy_nq_audit(['MNQ-CONT'], [0]) == 'PSY_NQ_UNVERIFIED')
t('gap in window -> PSY_NQ_INSUFFICIENT_DATA',
  L.psy_nq_audit(['NQ 09-26'], [900]) == 'PSY_NQ_INSUFFICIENT_DATA')
t('clean front-contract window verifies',
  L.psy_nq_audit(['NQ 09-26'], [30, 60]) == 'PSY_NQ_VERIFIED')

# ---- clustering ------------------------------------------------------
lv = dict(SESSION_VWAP=100.0, VWAP_UPPER=100.5, VWAP_LOWER=99.5,
          PP=100.2, M2=100.4, YDAY_HIGH=100.3, ADR_HIGH=100.1,
          PSY_HIGH=100.2, LWEEK_HIGH=150.0)
fc = L.family_counts(lv, 100.0, radius=1.0)
t('VWAP + both bands count as ONE family; PP+M2 as ONE',
  fc['active_family_count'] == 3)          # VWAP, PIVOT, YDAY_RANGE
t('context count adds ADR once', fc['all_context_family_count'] == 4)
t('PSY reported separately, never in base counts',
  fc['psy_experimental_present'] is True)
t('far level excluded from cluster', 'LWEEK_RANGE' not in fc['families'])
t('eligibility radius = max(4 ticks, 0.2*ATR)',
  L.eligibility_radius(2.0) == 1.0 and L.eligibility_radius(0.1) == 1.0)

# ---- geometry --------------------------------------------------------
g = L.available_R(100.0, 99.0, +1, dict(PP=100.5, YDAY_HIGH=102.5), 0.3)
t('Available_R uses nearest opposing level outside cluster (0.5R)',
  abs(g['Available_R'] - 0.5) < 1e-12 and g['role'] == 'REJECT_GEOMETRY')
g2 = L.available_R(100.0, 99.0, +1, dict(YDAY_HIGH=101.2), 0.3)
t('0.70<=AR<2 -> A-/B+ only', g2['role'] == 'A_MINUS_B_PLUS_ONLY')
g3 = L.available_R(100.0, 99.0, +1, dict(YDAY_LOW=95.0), 0.3)
t('no opposing level before 2R -> AR>=2, A+ eligible',
  g3['Available_R'] >= 2.0 and g3['role'] == 'A_PLUS_ELIGIBLE')

# ---- book reconstruction --------------------------------------------
bk = S.KLevelBook()
bk.apply('ADD', 'bid', 0, 100.00, 5)
bk.apply('ADD', 'bid', 1, 99.75, 3)
bk.apply('ADD', 'ask', 0, 100.25, 4)
bk.apply('UPDATE', 'bid', 0, 100.00, 7)
t('MBP add/update maintain levels', bk.depth('bid', 2) == 10)
bk.apply('REMOVE', 'bid', 0, 100.00, 0)
t('MBP remove promotes next level', bk.bid[0][0] == 99.75)
t('BI_k signed correctly', bk.bi(1) == (3 - 4) / (3 + 4))

# ---- baselines: causality -------------------------------------------
bs = S.BaselineStore(n_sessions=20)
for ses in range(6):
    bs.observe('delta', 34500, 10.0 + ses)
    bs.close_session()
z_lo = bs.z('delta', 34500, 12.0)
bs.observe('delta', 34500, 1000.0)          # current session, NOT closed
z_lo2 = bs.z('delta', 34500, 12.0)
t('baseline uses previous sessions only (current excluded)',
  z_lo is not None and z_lo == z_lo2)
t('insufficient history -> z None', bs.z('delta', 60000, 5.0) is None)

# ---- features --------------------------------------------------------
tr = [(0.0, 100.00, 5, 1), (0.5, 100.25, 3, 1), (1.2, 100.25, 2, -1)]
d, nd = S.aggr_delta(tr)
t('aggressor delta signed sum (+6)', d == 6 and abs(nd - 0.6) < 1e-12)
t('flow efficiency sign(D)*r/|D|',
  abs(S.flow_efficiency(6, 3.0) - 0.5) < 1e-6)
t('replenishment ratio', abs(S.replenishment_ratio(10, 40) - 0.25) < 1e-9)
t('depletion ratio', abs(S.depletion_ratio(30, 15, 5) - 1.5) < 1e-9)
t('non-trade withdrawal subtracts matched executions',
  S.nontrade_withdrawal(100, 30) == 70)
t('vacuum condition 60/20', S.vacuum_event(0.65, 0.10) and
  not S.vacuum_event(0.65, 0.30) and not S.vacuum_event(0.50, 0.10))
r = S.resiliency(0.0, 40.0)
t('resiliency right-censored at 30s', r['censored'] and r['time_s'] == 30)
t('control score equal-weight; None disqualifies',
  S.control_score(2, 2, 1, 1) == 1.5 and
  S.control_score(2, None, 1, 1) is None)
ag, dec = S.persistence([(0.2, 0, 5, 1), (2.6, 0, 4, 1), (5.1, 0, 3, 1),
                         (7.6, 0, 2, -1)], 0.0, +1)
t('persistence 3-of-4 with decay ratio', ag == 3 and abs(dec - 0.4) < 1e-9)
sw = S.sweep([(0.0, 100.00, 2, 1), (0.3, 100.25, 2, 1), (0.6, 100.50, 2, 1)])
t('sweep = 3 consecutive levels inside 1s', sw and sw['levels'] == 3)
t('sweep reclaim within 5s',
  S.sweep_reclaimed(sw, [(3.0, 99.90)]) is True and
  S.sweep_reclaimed(sw, [(9.0, 99.90)]) is False)
t('no sweep across direction change',
  S.sweep([(0.0, 100.00, 2, 1), (0.3, 100.25, 2, -1),
           (0.6, 100.50, 2, 1)]) is None)
t('pause quality: <=50% volume and no adverse z>=1',
  S.pause_quality(100, 40, 0.5) and not S.pause_quality(100, 60, 0.5)
  and not S.pause_quality(100, 40, 1.2))

# ---- detectors -------------------------------------------------------
f1 = dict(aggr_z=2.5, progress_ticks=1, replenish_z=1.6, approaches_60s=2,
          opp_flip_z=1.1, retreat_ticks=1, aggr_dir=1)
t('A1 fires against absorbed buyers (short)',
  S.a1_absorption_reversal(f1) == -1)
t('A1 silent when replenishment weak',
  S.a1_absorption_reversal(dict(f1, replenish_z=1.4)) == 0)
f2 = dict(wall_z=2.2, exec_vs_displayed=1.6, replenish_ratio=0.2,
          cleared_held_5s=True, persist_agree=3, post_clear_z=1.2,
          break_dir=1)
t('A2 fires through depleted wall', S.a2_depletion_continuation(f2) == 1)
t('A2 silent when wall vanishes without execution (belongs to A3)',
  S.a2_depletion_continuation(dict(f2, exec_vs_displayed=0.4)) == 0)
t('A3 unavailable when feed cannot distinguish actions',
  S.a3_vacuum_continuation(dict(actions_distinguishable=False)) == 0)
t('A3 fires on distinguishable vacuum',
  S.a3_vacuum_continuation(dict(actions_distinguishable=True,
                                tgt_drop_frac=0.7, opp_drop_frac=0.1,
                                delta_z=1.2, advance_ticks=1,
                                vacuum_dir=-1)) == -1)
f4 = dict(aggr_z=2.1, progress_ticks=1, resid_tail_5pct=False,
          returned_through_level=True, sweep_reclaimed_5s=False,
          opp_flip_z=1.0, aggr_dir=1)
t('A4 fades failed aggression', S.a4_response_failure_reversal(f4) == -1)
f6 = dict(in_0930_0945=True, control_z=2.4, clean_cross=True, held_5s=True,
          persist_agree=3, opp_replenish_z=0.5, break_dir=-1)
t('A6 fires only inside 09:30-09:45',
  S.a6_open_continuation(f6) == -1 and
  S.a6_open_continuation(dict(f6, in_0930_0945=False)) == 0)

# ---- execution -------------------------------------------------------
qs = [(10.05, 100.00, 5, 100.25, 5), (10.20, 100.00, 5, 100.25, 5),
      (10.40, 100.25, 5, 100.50, 5)]
px, ft = S.entry_fill(qs, 10.0, +1)
t('entry at first quote strictly after latency (150ms)',
  ft == 10.20 and px == 100.25)
t('structural stop = extreme + max(2 ticks, 0.1*ATR)',
  S.structural_stop(100.0, +1, 10.0) == 99.0 and
  S.structural_stop(100.0, +1, 1.0) == 99.5)
# stop / target / early-invalidation / 30m cap
qser = [(11 + i, 100.25 + 0.25 * i, 5, 100.50 + 0.25 * i, 5)
        for i in range(10)]
res = S.simulate(qser, 100.50, 10.0, +1, 99.50,
                 check_10s=lambda tw: (2, 4),
                 check_control_loss=lambda tw: (0.0, False))
t('2R target exits at target price', res['exit'] == 'TARGET_2R'
  and res['R'] == 2.0)
res2 = S.simulate([(11, 99.40, 5, 99.65, 5)], 100.50, 10.0, +1, 99.50,
                  check_10s=lambda tw: (2, 4),
                  check_control_loss=lambda tw: (0.0, False))
t('stop exit at worse of stop/quote', res2['exit'] == 'STOP')
res3 = S.simulate([(25.0, 100.50, 5, 100.75, 5)], 100.50, 10.0, +1, 99.50,
                  check_10s=lambda tw: (0, 1),
                  check_control_loss=lambda tw: (0.0, False))
t('10s early-invalidation fires on <1 tick and <3/4 persistence',
  res3['exit'] == 'EARLY_INVALIDATION')
res4 = S.simulate([(21.0, 100.60, 5, 100.85, 5),
                   (10.0 + 1900, 100.60, 5, 100.85, 5)],
                  100.50, 10.0, +1, 99.50,
                  check_10s=lambda tw: (2, 4),
                  check_control_loss=lambda tw: (0.0, False))
t('30-minute hard cap enforced', res4['exit'] == 'TIME_30M')
res5 = S.simulate([(21.0, 100.60, 5, 100.85, 5),
                   (31.0, 100.40, 5, 100.65, 5)],
                  100.50, 10.0, +1, 99.50,
                  check_10s=lambda tw: (2, 4),
                  check_control_loss=lambda tw: (1.5, True))
t('control-loss exit after confirmation', res5['exit'] == 'CONTROL_LOSS')
t('Y_j dollar accounting (MNQ $0.50/tick minus costs)',
  abs(S.y_dollars(+1, 100.00, 100.50, commissions=0.74) -
      (2 * 0.50 - 0.74)) < 1e-9)

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
