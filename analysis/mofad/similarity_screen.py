#!/usr/bin/env python3
# ======================================================================
# MOFAD-V1  -  DETERMINISTIC SPENT-HYPOTHESIS SIMILARITY SCREEN
# ======================================================================
# Frozen BEFORE any MOFAD outcome is computed. A proposed hypothesis is
# compared against the spent-fingerprint classes derived from
# MOFAD_V1_SPENT_HYPOTHESIS_REGISTRY.csv. The rules are deterministic;
# there is no tunable score and no appeal after outcomes.
#
# REJECT rules (any one suffices):
#   R1  declared mechanism_class equals ANY spent fingerprint class
#       (DEAD_FROZEN, DESCRIPTIVE_ONLY_SPENT, or PASSED-protected -
#       derivatives of the frozen prospective OFH13/OFH14 are equally
#       prohibited while their prospective arms run).
#   R2  information-set token Jaccard >= 0.80 against a spent class's
#       token set AND the same trigger granularity (event vs state) -
#       i.e. same data driving the same kind of decision.
#   R3  the proposal is a management/filter/execution variant of an
#       existing frozen or dead strategy (trigger_type in
#       {'management','filter','execution'} referencing a spent parent).
#
# ACCEPT requires: a mechanism class NOT in the spent set, whose
# distinctness justification names the new causal information source.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, 'MOFAD_V1_SPENT_HYPOTHESIS_REGISTRY.csv')
FP = os.path.join(HERE, 'MOFAD_V1_SPENT_HYPOTHESIS_FINGERPRINTS.json')

# Frozen token sets describing each spent class's information set and
# trigger granularity. Tokens are the causal inputs, not parameters.
CLASS_DEF = {
    'OF_DIVERGENCE_FADE':        {'tokens': ['bar_delta', 'price_extreme', 'divergence'], 'granularity': 'event'},
    'OF_BREAK_CONFIRMATION':     {'tokens': ['bar_delta', 'price_break', 'confirmation_flag'], 'granularity': 'event'},
    'OF_ABSORPTION_REVERSAL':    {'tokens': ['absorption_flag', 'aggressive_volume', 'price_stall'], 'granularity': 'event'},
    'OF_STACKED_IMBALANCE':      {'tokens': ['imbalance_count', 'stacked_levels', 'bar_delta'], 'granularity': 'event'},
    'OF_CUMDELTA_TREND':         {'tokens': ['cum_delta', 'trend_slope'], 'granularity': 'state'},
    'OF_EFFORT_RESULT':          {'tokens': ['bar_delta', 'bar_range', 'effort_vs_result'], 'granularity': 'event'},
    'OF_VALUE_PROFILE':          {'tokens': ['volume_profile', 'poc_vah_val', 'bar_delta'], 'granularity': 'event'},
    'FVG_FLOW_MITIGATION':       {'tokens': ['fvg_zone', 'bar_delta', 'mitigation_retest'], 'granularity': 'event'},
    'OF_CONTEXT_FILTER':         {'tokens': ['flow_context', 'parent_entries'], 'granularity': 'filter'},
    'POSTENTRY_STATE':           {'tokens': ['open_trade_path', 'checkpoint_state'], 'granularity': 'filter'},
    'EXECUTION_REFINEMENT':      {'tokens': ['subminute_timing', 'parent_entries'], 'granularity': 'execution'},
    'MANAGEMENT_VARIANT':        {'tokens': ['stops_targets_exits', 'parent_entries'], 'granularity': 'management'},
    'CROSS_MARKET_PRICE_LEADLAG_1M': {'tokens': ['es_1m_price', 'nq_1m_price', 'lead_lag'], 'granularity': 'event'},
    'PRICE_CONTINUATION_INTRADAY': {'tokens': ['1m_price', 'impulse', 'continuation_window'], 'granularity': 'event'},
    'PRICE_MEANREV_INTRADAY':    {'tokens': ['1m_price', 'extension', 'reversion_window'], 'granularity': 'event'},
    'SESSION_ANCHOR_DISPLACEMENT': {'tokens': ['1m_price', 'session_anchor', 'displacement_memory'], 'granularity': 'state'},
    'PATTERN_GEOMETRY':          {'tokens': ['1m_price', 'bar_pattern', 'structure_zone'], 'granularity': 'event'},
    'CALENDAR_TOD':              {'tokens': ['clock', 'calendar'], 'granularity': 'state'},
    'PRICE_ONLY_FAMILY_SEARCH':  {'tokens': ['1m_price'], 'granularity': 'search'},
    'PRICE_ONLY_MAP':            {'tokens': ['1m_price'], 'granularity': 'descriptive'},
    'INVENTORY_TRANSITION_FLOW': {'tokens': ['overnight_cum_delta', 'session_transition', 'inventory_imbalance'], 'granularity': 'state'},
    'IMPACT_ASYMMETRY':          {'tokens': ['rolling_price_impact', 'buy_vs_sell_lambda', 'liquidity_asymmetry_state'], 'granularity': 'state'},
    'BIDIRECTIONAL_RANGE_HARVEST_DAILY': {'tokens': ['day_vol_forecast', 'open_anchored_two_sided_bands', 'realized_range_harvest'], 'granularity': 'state'},
    'ORDINAL_PATH_SHAPE':        {'tokens': ['ordinal_motif', 'path_shape', 'last_leg_continuation'], 'granularity': 'event'},
    'VOLUME_CLOCK_STRUCTURE':    {'tokens': ['volume_bars', 'event_time_sampling', 'clock_free_structure'], 'granularity': 'descriptive'},
    'DAY_TYPE_TAXONOMY':         {'tokens': ['daily_range_structure', 'day_classification', 'next_day_response'], 'granularity': 'state'},
    'REALIZED_MOMENT_ASYMMETRY': {'tokens': ['semivariance_composition', 'realized_skew', 'variance_asymmetry_state'], 'granularity': 'state'},
    'DURATION_HAZARD_RENEWAL':   {'tokens': ['event_age_clock', 'extreme_refresh_drought', 'renewal_hazard_state'], 'granularity': 'state'},
}


def load_registry():
    with open(REG, newline='') as fh:
        return [r for r in csv.DictReader(fh)]


def build_fingerprints():
    rows = load_registry()
    classes = {}
    for r in rows:
        c = r['fingerprint_class']
        if c in ('', '-'):
            continue
        d = classes.setdefault(c, {'members': [], 'dispositions': set()})
        d['members'].append(r['hyp_id'])
        d['dispositions'].add(r['disposition'])
    out = {}
    for c, d in sorted(classes.items()):
        cd = CLASS_DEF[c]
        out[c] = {
            'information_set_tokens': cd['tokens'],
            'trigger_granularity': cd['granularity'],
            'members': sorted(d['members']),
            'dispositions': sorted(d['dispositions']),
            'protected': 'PASSED_HISTORICAL_EXPLORATORY' in d['dispositions'],
        }
    return out


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / max(1, len(a | b))


def screen(proposal, fp=None):
    """proposal: dict with keys hyp_id, mechanism_class, tokens,
    granularity, distinctness. Returns (verdict, reasons)."""
    fp = fp or build_fingerprints()
    reasons = []
    if proposal['mechanism_class'] in fp:
        reasons.append('R1: mechanism_class %r is a spent fingerprint class'
                       % proposal['mechanism_class'])
    for c, d in fp.items():
        j = jaccard(proposal['tokens'], d['information_set_tokens'])
        if j >= 0.80 and proposal['granularity'] == d['trigger_granularity']:
            reasons.append('R2: token Jaccard %.2f vs %s at same granularity'
                           % (j, c))
    if proposal['granularity'] in ('management', 'filter', 'execution'):
        reasons.append('R3: variant of an existing strategy, not a new mechanism')
    if reasons:
        return 'REJECT', reasons
    if not proposal.get('distinctness'):
        return 'REJECT', ['no distinctness justification naming the new causal source']
    return 'ACCEPT', ['new mechanism class %r; %s'
                      % (proposal['mechanism_class'], proposal['distinctness'])]


if __name__ == '__main__':
    fp = build_fingerprints()
    with open(FP, 'w') as fh:
        json.dump(fp, fh, indent=1)
    print('fingerprint classes: %d   registry rows: %d'
          % (len(fp), len(load_registry())))
    for c, d in fp.items():
        print('  %-32s members %2d  protected %s'
              % (c, len(d['members']), d['protected']))
