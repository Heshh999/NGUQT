#!/usr/bin/env python3
# MOFAD-V1: run the frozen similarity screen over EVERY proposal
# (accepted and rejected) and record the decisions. Run at freeze time,
# before any outcome is computed.
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import similarity_screen as SS  # noqa: E402

PROPOSALS = [
    # ---- F03 proposals: honest mechanism classification = spent ----
    dict(hyp_id='P-F03-1 delta-burst continuation', family='F03',
         mechanism_class='OF_CUMDELTA_TREND',
         tokens=['bar_delta', 'trend_slope'], granularity='state',
         distinctness=''),
    dict(hyp_id='P-F03-2 trade-size exhaustion fade', family='F03',
         mechanism_class='OF_EFFORT_RESULT',
         tokens=['volume_per_tick', 'bar_delta', 'effort_vs_result'],
         granularity='event', distinctness=''),
    dict(hyp_id='P-F03-3 delta-climax fade at extremes', family='F03',
         mechanism_class='OF_DIVERGENCE_FADE',
         tokens=['bar_delta', 'price_extreme', 'divergence'],
         granularity='event', distinctness=''),
    dict(hyp_id='P-F03-4 signed-imbalance persistence', family='F03',
         mechanism_class='OF_CUMDELTA_TREND',
         tokens=['cum_delta', 'trend_slope'], granularity='state',
         distinctness=''),
    # ---- F08 shock continuation/decay: effort-result derivative ----
    dict(hyp_id='P-F08-3 impact of large delta shocks (continuation/decay)',
         family='F08', mechanism_class='OF_EFFORT_RESULT',
         tokens=['bar_delta', 'bar_range', 'effort_vs_result'],
         granularity='event', distinctness=''),
    # ---- accepted candidates ----
    dict(hyp_id='C-F08-1 lambda-asymmetry drift T15', family='F08',
         mechanism_class='IMPACT_ASYMMETRY',
         tokens=['rolling_price_impact', 'buy_vs_sell_lambda',
                 'liquidity_asymmetry_state'], granularity='state',
         distinctness='new causal source: side-split rolling price-impact '
                      'estimates as a book-asymmetry state; no spent hypothesis '
                      'estimated impact per unit signed volume or conditioned on '
                      'its asymmetry'),
    dict(hyp_id='C-F08-2 lambda-asymmetry drift T30', family='F08',
         mechanism_class='IMPACT_ASYMMETRY',
         tokens=['rolling_price_impact', 'buy_vs_sell_lambda',
                 'liquidity_asymmetry_state'], granularity='state',
         distinctness='same new state as C-F08-1, second frozen horizon'),
    dict(hyp_id='C-F12-1 overnight-inventory open continuation T30',
         family='F12', mechanism_class='INVENTORY_TRANSITION_FLOW',
         tokens=['overnight_cum_delta', 'session_transition',
                 'inventory_imbalance'], granularity='state',
         distinctness='new causal source: overnight aggregated aggressor flow '
                      'as an inventory proxy at the session transition; every '
                      'spent OF hypothesis was RTH intraday event-triggered and '
                      'the MGSD premarket study was price-only'),
    dict(hyp_id='C-F12-1b overnight-inventory open continuation T60',
         family='F12', mechanism_class='INVENTORY_TRANSITION_FLOW',
         tokens=['overnight_cum_delta', 'session_transition',
                 'inventory_imbalance'], granularity='state',
         distinctness='same new state as C-F12-1, second frozen horizon'),
    dict(hyp_id='C-F12-2 preopen-flow open continuation T30', family='F12',
         mechanism_class='INVENTORY_TRANSITION_FLOW',
         tokens=['preopen_cum_delta', 'session_transition',
                 'inventory_imbalance'], granularity='state',
         distinctness='late-premarket (08:00-09:29) aggressor flow window; '
                      'flow-based, unlike the dead price-only LPCC arm'),
    # ---- infeasible-by-floor proposals, recorded for completeness ----
    dict(hyp_id='P-F12-3 close-hour inventory overnight continuation',
         family='F12', mechanism_class='INVENTORY_TRANSITION_FLOW',
         tokens=['closehour_cum_delta', 'session_transition',
                 'inventory_imbalance'], granularity='state',
         distinctness='same new class; EXCLUDED pre-freeze: 197 eligible days '
                      '< 200 frozen floor (feas_counts.py)'),
    dict(hyp_id='P-F12-4 overnight flow-price divergence', family='F12',
         mechanism_class='INVENTORY_TRANSITION_FLOW',
         tokens=['overnight_cum_delta', 'session_return',
                 'flow_price_divergence'], granularity='state',
         distinctness='same new class; EXCLUDED pre-freeze: 38 eligible days '
                      '< 200 frozen floor; retained as a SUBGROUP DIAGNOSTIC '
                      'of C-F12-1 only'),
]

fp = SS.build_fingerprints()
out = []
for p in PROPOSALS:
    v, why = SS.screen(p, fp)
    feas = 'EXCLUDED_PRE_FREEZE' if p['hyp_id'].startswith('P-F12') else None
    out.append(dict(hyp_id=p['hyp_id'], family=p['family'],
                    mechanism_class=p['mechanism_class'],
                    screen_verdict=v, reasons=why,
                    feasibility_exclusion=feas))
    print('%-58s %s%s' % (p['hyp_id'], v, ' (+floor-excluded)' if feas else ''))

with open(os.path.join(HERE, 'MOFAD_V1_SCREEN_DECISIONS.json'), 'w') as fh:
    json.dump(out, fh, indent=1)
acc = [o for o in out if o['screen_verdict'] == 'ACCEPT'
       and not o['feasibility_exclusion']]
print('\nconfirmatory candidates after screen + feasibility: %d' % len(acc))
