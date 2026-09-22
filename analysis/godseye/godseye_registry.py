#!/usr/bin/env python3
# ======================================================================
# MROF GOD'S EYE VIEW — HYPOTHESIS AND LEVEL REGISTRY (data, not logic)
#
# What the study says it tests, written down as data and verified
# against the frozen code it names. tests_godseye.py re-derives every
# threshold below from mrofyt_signals / mrofyt_wave2 / mrofyt_runner on
# random inputs, so this file cannot drift from the code silently.
#
# Nothing here ranks, scores, tunes or interprets. A detector's
# registered direction is quoted from its frozen function; a threshold
# is quoted from the same line the runner evaluates.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
"""Registry entries are plain dicts so the exporter can serialise them
and the frontend can render them without importing research code."""

REGISTRY_VERSION = 'MROF-GODSEYE-REGISTRY-1.0'

# implementation status vocabulary (fixed by the build prompt)
IMPLEMENTED = 'IMPLEMENTED'                  # code exists and is wired
IMPLEMENTED_NOT_WIRED = 'IMPLEMENTED_NOT_WIRED'   # detector exists, an
#                                              input is passed as None
NOT_IMPLEMENTED = 'NOT_IMPLEMENTED'          # registered, no code
CONTROL = 'CONTROL'                          # a comparison arm, not a
#                                              hypothesis

# ---------------------------------------------------------------------
# baselines: the two different "prior history" requirements
# ---------------------------------------------------------------------
BASELINE_Z = dict(
    id='BASELINE_Z',
    text='z-scored inputs use a robust median/MAD baseline per (feature, '
         '5-minute-of-day bucket) over a 20-session window, and return '
         'None until the bucket holds at least 5 PRIOR sessions',
    prior_sessions_min=5, window_sessions=20,
    source='mrofyt_signals.BaselineStore(20).z: len(vals) < 5 -> None')
BASELINE_RESID = dict(
    id='BASELINE_RESID',
    text='the W2-A4f residual model fits per 5-minute bucket on PRIOR '
         'sessions only (20-session window) and speaks once the bucket '
         'holds at least 20 prior observations -- observations, not '
         'sessions',
    prior_obs_min=20, window_sessions=20,
    source='mrofyt_wave2.ResidualModel: MIN_OBS=20, N_SESSIONS=20')

# ---------------------------------------------------------------------
# levels: the 14 active identifiers, verified against
# mrofyt_levels.ACTIVE_LEVEL_IDS by tests_godseye.py
# ---------------------------------------------------------------------
LEVELS = [
    dict(id='YDAY_HIGH', family='YDAY_RANGE',
         definition='high of the preceding completed session',
         available='from the first bar of the session, once a prior '
                   'completed session exists in this pass'),
    dict(id='YDAY_LOW', family='YDAY_RANGE',
         definition='low of the preceding completed session',
         available='as YDAY_HIGH'),
    dict(id='LWEEK_HIGH', family='LWEEK_RANGE',
         definition='high of the preceding ISO week',
         available='once a prior week has been seen in this pass'),
    dict(id='LWEEK_LOW', family='LWEEK_RANGE',
         definition='low of the preceding ISO week',
         available='as LWEEK_HIGH'),
    dict(id='OVERNIGHT_HIGH', family='OVERNIGHT_RANGE',
         definition='high of trades from 18:00 ET until the 09:30 ET '
                    'cash open',
         available='fixed at the first trade at or after 09:30 ET; '
                   'not a level before that'),
    dict(id='OVERNIGHT_LOW', family='OVERNIGHT_RANGE',
         definition='low of the same overnight window',
         available='as OVERNIGHT_HIGH'),
    dict(id='GLOBEX_OPEN', family='OPEN',
         definition='first trade price of the session',
         available='from that trade'),
    dict(id='CASH_OPEN_0930', family='OPEN',
         definition='first trade price at or after 09:30 ET',
         available='from that trade'),
    dict(id='SESSION_VWAP', family='VWAP',
         definition='volume-weighted average price of the session so far',
         available='rolling; updated every completed 1-minute bar'),
    dict(id='VWAP_UPPER', family='VWAP',
         definition='SESSION_VWAP + 2 x its running standard deviation',
         available='rolling with SESSION_VWAP'),
    dict(id='VWAP_LOWER', family='VWAP',
         definition='SESSION_VWAP - 2 x its running standard deviation',
         available='rolling with SESSION_VWAP'),
    dict(id='PP', family='PIVOT',
         definition='(prior high + prior low + prior close) / 3',
         available='as YDAY_HIGH'),
    dict(id='M2', family='PIVOT',
         definition='pivot midpoint (frozen pivot family)',
         available='as YDAY_HIGH'),
    dict(id='M3', family='PIVOT',
         definition='pivot midpoint (frozen pivot family)',
         available='as YDAY_HIGH'),
]

# context and registered-but-unbuilt items; statuses verified in tests
CONTEXT = [
    dict(id='RVMR regime', status='IMPLEMENTED',
         where='analysis/rvmr/rvmr_spec.py via mrofyt_runner',
         note='range/volume regime tag at each window; needs 1,440 prior '
              '1-minute bars, so it reads None on short captures'),
    dict(id='ADR', status='CONTEXT_ONLY',
         where='mrofyt_levels.adr_state',
         note='context family (ADR_HIGH/LOW, ADR_50), never an active '
              'level'),
    dict(id='Running session extreme', status='CONTEXT_ONLY',
         where='mrofyt_levels (RUNNING_SESSION_HIGH/LOW)',
         note='context family, never an active level'),
    dict(id='Psychological levels', status='EXPERIMENTAL',
         where='mrofyt_levels.psy_nq_week / psy_nq_audit',
         note='experimental family (PSY_HIGH/LOW); not in the active set'),
    dict(id='Causal swing highs/lows', status='REGISTERED_NOT_INTEGRATED',
         where='mrofyt_swings_v016.py (frozen, 21/21); registration §4.3',
         note='module exists and is tested; it is NOT a level provider '
              'for the runner and has never run on real tape. The '
              'CAUSAL_SWING comparison is declared not_in_this_version '
              'by mrofyt_wave2'),
    dict(id='1-hour supply/demand zones', status='IN_LINEAGE_NOT_IN_RUNNER',
         where='mrofyt_h1zones.py, used by the v01.x coordinators',
         note='frozen module used by the coordinator lineage (label_event, '
              'family_counts_v011); the outcome-blind runner, pilot and '
              'wave two do not import it, so no zone reaches a window'),
    dict(id='EMA context', status='NOT_IMPLEMENTED',
         where='—',
         note='no EMA feature exists in the runner or the registration'),
    dict(id='Asia conditioning', status='REGISTERED_NOT_IMPLEMENTED',
         where='registration §5 (asia_inside, asia_ranged)',
         note='labels are registered with their definitions; no code '
              'computes them yet (wave-two §11)'),
]

# ---------------------------------------------------------------------
# hypotheses. `conditions` is a list of clauses; a clause is
#   ('feature', op, value)          op in >=, <=, <, !=, is_true
#   ('any', [clause, clause])       at least one sub-clause holds
# `gate` is evaluated first (A3, A6); `inputs` must all be non-None
# (the frozen _ok) except where a clause says 'any'.
# ---------------------------------------------------------------------
def _c(feat, op, val=None):
    return dict(feature=feat, op=op, value=val)


def _any(*clauses):
    return dict(op='any', clauses=list(clauses))


WAVE_ONE = [
    dict(
        id='A1', wave=1, name='Absorption reversal',
        registered_in='MROF_YT_OF01_WAVE_FREEZE.md (frozen wave one)',
        implemented_in='mrofyt_signals.a1_absorption_reversal',
        implementation=IMPLEMENTED,
        mechanism='aggressive flow INTO a level that does not move price '
                  'while the resting side keeps refilling and the '
                  'opposite side flips; the pressure is absorbed',
        direction_rule='-aggr_dir: away from the absorbed aggression (a '
                  'reversal)',
        direction_sign='-aggr_dir',
        grid='10 s decision windows on approaches, 2.5 s persistence grid',
        window_et=None, level_set='ACTIVE_LEVEL_IDS',
        inputs=[
            dict(name='aggr_z', wired=True, baseline='BASELINE_Z'),
            dict(name='progress_ticks', wired=True),
            dict(name='replenish_z', wired=True, baseline='BASELINE_Z',
                 note='observed only when an execution occurs at the '
                      'level (171 of 44,628 windows in the first pilot); '
                      'None elsewhere by definition, not by immaturity'),
            dict(name='approaches_60s', wired=True),
            dict(name='opp_flip_z', wired=True, baseline='BASELINE_Z'),
            dict(name='retreat_ticks', wired=True),
            dict(name='aggr_dir', wired=True, role='direction')],
        conditions=[_c('aggr_z', '>=', 2.0), _c('progress_ticks', '<=', 1),
                    _c('replenish_z', '>=', 1.5),
                    _c('approaches_60s', '>=', 2),
                    _c('opp_flip_z', '>=', 1.0),
                    _c('retreat_ticks', '>=', 1)],
        baseline='BASELINE_Z'),
    dict(
        id='A2', wave=1, name='Depletion continuation',
        registered_in='MROF_YT_OF01_WAVE_FREEZE.md (frozen wave one)',
        implemented_in='mrofyt_signals.a2_depletion_continuation',
        implementation=IMPLEMENTED,
        mechanism='a qualifying resting wall is executed THROUGH and not '
                  'replenished; the clear holds 5 s and flow persists',
        direction_rule='break_dir: CONTINUATION in the direction that cleared '
                  'the wall (not a fade of the wall)',
        direction_sign='break_dir',
        grid='10 s decision windows on approaches',
        window_et=None, level_set='ACTIVE_LEVEL_IDS',
        inputs=[
            dict(name='wall_z', wired=True, baseline='BASELINE_Z',
                 note='from mrofyt_wall_engine; qualifying wall in ~2.1% '
                      'of windows on this feed'),
            dict(name='exec_vs_displayed', wired=True),
            dict(name='replenish_ratio', wired=True),
            dict(name='cleared_held_5s', wired=True),
            dict(name='persist_agree', wired=True),
            dict(name='post_clear_z', wired=True, baseline='BASELINE_Z'),
            dict(name='break_dir', wired=True, role='direction')],
        conditions=[_c('wall_z', '>=', 2.0),
                    _c('exec_vs_displayed', '>=', 1.5),
                    _c('replenish_ratio', '<', 0.25),
                    _c('cleared_held_5s', 'is_true'),
                    _c('persist_agree', '>=', 3),
                    _c('post_clear_z', '>=', 1.0)],
        baseline='BASELINE_Z'),
    dict(
        id='A3', wave=1, name='Vacuum continuation',
        registered_in='MROF_YT_OF01_WAVE_FREEZE.md (frozen wave one)',
        implemented_in='mrofyt_signals.a3_vacuum_continuation',
        implementation=IMPLEMENTED,
        mechanism='target-side 3-level depth falls >= 60% within 2 s '
                  'without matched executions while the opposite side '
                  'falls <= 20%; flow and price advance into the gap',
        direction_rule='vacuum_dir: CONTINUATION into the vacuum',
        direction_sign='vacuum_dir',
        grid='its own 2 s vacuum grid, not the 10 s window grid',
        window_et=None, level_set='ACTIVE_LEVEL_IDS',
        gate=[_c('actions_distinguishable', 'is_true')],
        inputs=[
            dict(name='tgt_drop_frac', wired=True),
            dict(name='opp_drop_frac', wired=True),
            dict(name='delta_z', wired=True, baseline='BASELINE_Z'),
            dict(name='advance_ticks', wired=True),
            dict(name='vacuum_dir', wired=True, role='direction')],
        conditions=[_c('tgt_drop_frac', '>=', 0.60),
                    _c('opp_drop_frac', '<=', 0.20),
                    _c('delta_z', '>=', 1.0),
                    _c('advance_ticks', '>=', 1)],
        baseline='BASELINE_Z'),
    dict(
        id='A4', wave=1, name='Response-failure reversal',
        registered_in='MROF_YT_OF01_WAVE_FREEZE.md (frozen wave one)',
        implemented_in='mrofyt_signals.a4_response_failure_reversal',
        implementation=IMPLEMENTED_NOT_WIRED,
        mechanism='aggressive push through a level that fails to move '
                  'price (or under-responds versus expectation), then '
                  'price comes back through and the opposite side flips',
        direction_rule='-aggr_dir: away from the failed push (a reversal)',
        direction_sign='-aggr_dir',
        grid='10 s decision windows on approaches',
        window_et=None, level_set='ACTIVE_LEVEL_IDS',
        inputs=[
            dict(name='aggr_z', wired=True, baseline='BASELINE_Z'),
            dict(name='opp_flip_z', wired=True, baseline='BASELINE_Z'),
            dict(name='progress_ticks', wired=True,
                 note='the response-failure test that actually ran'),
            dict(name='resid_tail_5pct', wired=False,
                 note='passed as None in wave one (expected-response '
                      'residual model not in frozen code); wired only in '
                      'W2-A4f'),
            dict(name='returned_through_level', wired=True),
            dict(name='sweep_reclaimed_5s', wired=True),
            dict(name='aggr_dir', wired=True, role='direction')],
        conditions=[_c('aggr_z', '>=', 2.0),
                    _any(_c('resid_tail_5pct', 'is_true'),
                         _c('progress_ticks', '<=', 1)),
                    _any(_c('returned_through_level', 'is_true'),
                         _c('sweep_reclaimed_5s', 'is_true')),
                    _c('opp_flip_z', '>=', 1.0)],
        required_inputs=('aggr_z', 'opp_flip_z'),
        baseline='BASELINE_Z',
        not_wired=['resid_tail_5pct']),
    dict(
        id='A5', wave=1, name='Pullback resumption',
        registered_in='MROF_YT_OF01_WAVE_FREEZE.md (frozen wave one)',
        implemented_in='mrofyt_signals.a5_pullback_resumption',
        implementation=IMPLEMENTED_NOT_WIRED,
        mechanism='counter-trend aggression into a level that does not '
                  'move price and is replenished; the trend side flips '
                  'back',
        direction_rule='trend_dir: RESUMPTION with the higher-timeframe trend '
                  '(the pullback is faded, the trend is followed)',
        direction_sign='trend_dir',
        grid='10 s decision windows on approaches',
        window_et=None, level_set='ACTIVE_LEVEL_IDS',
        inputs=[
            dict(name='trend_dir', wired=False,
                 note='"the already-frozen MROF multi-timeframe state"; no '
                      'such code exists; passed as None'),
            dict(name='adverse_z', wired=False, note='passed as None'),
            dict(name='adverse_progress_ticks', wired=False,
                 note='passed as None'),
            dict(name='replenish_z', wired=True, baseline='BASELINE_Z',
                 note='the one wired input; starved as in A1'),
            dict(name='trend_flip_z', wired=False, note='passed as None')],
        conditions=[_c('trend_dir', '!=', 0), _c('adverse_z', '>=', 2.0),
                    _c('adverse_progress_ticks', '<=', 1),
                    _c('replenish_z', '>=', 1.5),
                    _c('trend_flip_z', '>=', 1.0)],
        baseline='BASELINE_Z',
        not_wired=['trend_dir', 'adverse_z', 'adverse_progress_ticks',
                   'trend_flip_z']),
    dict(
        id='A6', wave=1, name='Open continuation',
        registered_in='MROF_YT_OF01_WAVE_FREEZE.md (frozen wave one)',
        implemented_in='mrofyt_signals.a6_open_continuation',
        implementation=IMPLEMENTED,
        mechanism='inside the first 15 minutes of cash trading, a clean '
                  'cross of an open-type level that holds 5 s with '
                  'control flow and no replenishment on the far side',
        direction_rule='break_dir: CONTINUATION of the break -- NOT A4\'s '
                  'reversal, and NOT the W2-A4-OPEN window',
        direction_sign='break_dir',
        grid='10 s decision windows on approaches',
        window_et=(9.5 * 3600, 9.75 * 3600),          # 09:30:00-09:45:00
        level_set=('OVERNIGHT_HIGH', 'OVERNIGHT_LOW', 'YDAY_HIGH',
                   'YDAY_LOW', 'GLOBEX_OPEN', 'CASH_OPEN_0930'),
        gate=[_c('in_0930_0945', 'is_true')],
        inputs=[
            dict(name='control_z', wired=True, baseline='BASELINE_Z'),
            dict(name='clean_cross', wired=True),
            dict(name='held_5s', wired=True),
            dict(name='persist_agree', wired=True),
            dict(name='opp_replenish_z', wired=True, baseline='BASELINE_Z',
                 note='the same execution-only replenishment laggard as '
                      'A1'),
            dict(name='break_dir', wired=True, role='direction')],
        conditions=[_c('control_z', '>=', 2.0),
                    _c('clean_cross', 'is_true'), _c('held_5s', 'is_true'),
                    _c('persist_agree', '>=', 3),
                    _c('opp_replenish_z', '<', 1.5)],
        baseline='BASELINE_Z'),
]

WAVE_TWO = [
    dict(
        id='W2-A1', wave=2, name='A1 with replenishment on every grid tick',
        registered_in='MROF_YT_WAVE2_REGISTRATION.md §1.1',
        implemented_in='mrofyt_wave2.w2_a1',
        implementation=IMPLEMENTED,
        mechanism='A1 unchanged, with replenish_z replaced by repl10_z: '
                  'adds at the top-3 levels of the approached side over '
                  '10 s divided by executions there (+1), observed on '
                  'every grid tick and baselined like delta10',
        direction_rule='-aggr_dir (as A1)', direction_sign='-aggr_dir',
        grid='10 s decision windows (the same windows as wave one)',
        window_et=None, level_set='ACTIVE_LEVEL_IDS',
        inputs=[dict(name='repl10_z', wired=True, baseline='BASELINE_Z',
                     note='replaces replenish_z')],
        derived_from='A1', baseline='BASELINE_Z'),
    dict(
        id='W2-A4r', wave=2, name='A4 as it ran',
        registered_in='MROF_YT_WAVE2_REGISTRATION.md §1',
        implemented_in='mrofyt_wave2.w2_a4r',
        implementation=IMPLEMENTED,
        mechanism='A4 with resid_tail_5pct forced None: the response '
                  'failure is progress_ticks <= 1 alone. This is the '
                  'version that produced every wave-one A4 event',
        direction_rule='-aggr_dir (as A4)', direction_sign='-aggr_dir',
        grid='10 s decision windows', window_et=None,
        level_set='ACTIVE_LEVEL_IDS', derived_from='A4',
        baseline='BASELINE_Z'),
    dict(
        id='W2-A4f', wave=2, name='A4 as written (residual wired)',
        registered_in='MROF_YT_WAVE2_REGISTRATION.md §1',
        implemented_in='mrofyt_wave2.w2_a4f / ResidualModel',
        implementation=IMPLEMENTED,
        mechanism='A4 with the expected-response residual wired in its '
                  'first-wave minimal form; evaluated ONLY on windows '
                  'where the model can speak',
        direction_rule='-aggr_dir (as A4)', direction_sign='-aggr_dir',
        grid='10 s decision windows', window_et=None,
        level_set='ACTIVE_LEVEL_IDS', derived_from='A4',
        inputs=[dict(name='resid_tail_5pct', wired=True,
                     baseline='BASELINE_RESID')],
        baseline='BASELINE_RESID'),
    dict(
        id='W2-A4-OPEN', wave=2, name='A4r where the mechanism is forced',
        registered_in='MROF_YT_WAVE2_REGISTRATION.md §2',
        implemented_in='mrofyt_wave2.w2_a4_open',
        implementation=IMPLEMENTED,
        mechanism='W2-A4r restricted to the first hour of cash trading at '
                  'the cash open and overnight extremes -- a REVERSAL '
                  'family; distinct from A6 (a continuation, 09:30-09:45, '
                  'six open-type levels)',
        direction_rule='-aggr_dir (as A4)', direction_sign='-aggr_dir',
        grid='10 s decision windows',
        window_et=(9.5 * 3600, 10.5 * 3600),          # 09:30:00-10:30:00
        level_set=('CASH_OPEN_0930', 'OVERNIGHT_HIGH', 'OVERNIGHT_LOW'),
        derived_from='W2-A4r', baseline='BASELINE_Z'),
    dict(
        id='W2-A4r-z15', wave=2, name='A4r at aggr_z >= 1.5',
        registered_in='MROF_YT_WAVE2_REGISTRATION.md §3',
        implemented_in='mrofyt_wave2.w2_a4r_z15',
        implementation=IMPLEMENTED,
        mechanism='W2-A4r with the aggression threshold at 1.5 instead of '
                  '2.0; reported beside W2-A4r, never in place of it',
        direction_rule='-aggr_dir (as A4)', direction_sign='-aggr_dir',
        grid='10 s decision windows', window_et=None,
        level_set='ACTIVE_LEVEL_IDS', derived_from='W2-A4r',
        threshold_change=dict(feature='aggr_z', frozen=2.0, variant=1.5),
        baseline='BASELINE_Z'),
    dict(
        id='W2-A4r-HC', wave=2, name='A4r on high-confidence aggressor',
        registered_in='MROF_YT_WAVE2_REGISTRATION.md §6',
        implemented_in='mrofyt_wave2.w2_a4r_hc',
        implementation=IMPLEMENTED,
        mechanism='W2-A4r with aggr_z computed from trades whose inferred '
                  'aggressor side is HIGH confidence only (own baseline '
                  'delta10_hc); measures what the inference costs',
        direction_rule='-aggr_dir (as A4)', direction_sign='-aggr_dir',
        grid='10 s decision windows', window_et=None,
        level_set='ACTIVE_LEVEL_IDS', derived_from='W2-A4r',
        inputs=[dict(name='aggr_z_hc', wired=True, baseline='BASELINE_Z')],
        baseline='BASELINE_Z'),
    dict(
        id='ARM-B1', wave=2, name='Candle-only rejection wick',
        registered_in='MROF_YT_WAVE2_REGISTRATION.md §4.1',
        implemented_in='mrofyt_wave2.arm_b1',
        implementation=CONTROL,
        mechanism='on the 1-minute bar containing the approach: wick '
                  'beyond the level >= 50% of the bar range AND close '
                  'back on the approach side. No flow input',
        direction_rule='-ad: away from the wick', direction_sign='-ad',
        grid='the approach\'s 1-minute bar; decision instant is the first '
             'print after that minute ends',
        window_et=None, level_set='ACTIVE_LEVEL_IDS',
        inputs=[dict(name='bar (o,h,l,c)', wired=True)]),
    dict(
        id='ARM-B2', wave=2, name='Candle-only engulfing reclaim',
        registered_in='MROF_YT_WAVE2_REGISTRATION.md §4.1',
        implemented_in='mrofyt_wave2.arm_b2',
        implementation=CONTROL,
        mechanism='bar closes THROUGH the level and the NEXT 1-minute bar '
                  'closes back on the original side',
        direction_rule='-ad: back toward the original side',
        direction_sign='-ad',
        grid='two 1-minute bars; decision instant after the second',
        window_et=None, level_set='ACTIVE_LEVEL_IDS',
        inputs=[dict(name='bar1, bar2 (o,h,l,c)', wired=True)]),
    dict(
        id='ARM-C', wave=2, name='Placebo levels',
        registered_in='MROF_YT_WAVE2_REGISTRATION.md §4.2',
        implemented_in='mrofyt_wave2.Wave2Runner(mode="placebo")',
        implementation=CONTROL,
        mechanism='the whole pipeline re-run with every real level shifted '
                  '+/- U(6, 20) proximity radii, seeded per (session, '
                  'level_id), kept >= 3 radii from every real level. Not '
                  'a hypothesis: the control every family is compared to',
        direction_rule='n/a (each family keeps its own direction)',
        direction_sign=None, grid='as each family', window_et=None,
        level_set='placebo of ACTIVE_LEVEL_IDS'),
]

NOT_IN_THIS_VERSION = [
    dict(id='CAUSAL_SWING comparison',
         registered_in='MROF_YT_WAVE2_REGISTRATION.md §4.3',
         implementation=NOT_IMPLEMENTED,
         note='needs mrofyt_swings_v016 as a level provider and the frozen '
              'approach loop to accept ids outside ACTIVE_LEVEL_IDS; '
              'declared not_in_this_version by mrofyt_wave2'),
    dict(id='Asia labels (asia_inside, asia_ranged)',
         registered_in='MROF_YT_WAVE2_REGISTRATION.md §5',
         implementation=NOT_IMPLEMENTED,
         note='registered as stratification labels; not computed'),
]

HYPOTHESES = WAVE_ONE + WAVE_TWO


def by_id(hid):
    for h in HYPOTHESES:
        if h['id'] == hid:
            return h
    raise KeyError(hid)


# ---------------------------------------------------------------------
# condition evaluation for display: which clauses passed on a recorded
# feature vector. Pure bookkeeping; the verdict itself always comes
# from the frozen function (tests pin that the two agree).
# ---------------------------------------------------------------------
def _clause(cl, f):
    if cl.get('op') == 'any':
        subs = [_clause(c, f) for c in cl['clauses']]
        return dict(op='any', clauses=subs,
                    passed=any(s['passed'] is True for s in subs))
    v = f.get(cl['feature'])
    op, val = cl['op'], cl.get('value')
    if v is None:
        passed = None
    elif op == 'is_true':
        passed = v is True
    elif op == '>=':
        passed = v >= val
    elif op == '<=':
        passed = v <= val
    elif op == '<':
        passed = v < val
    elif op == '!=':
        passed = v != val
    else:
        raise ValueError(op)
    return dict(feature=cl['feature'], op=op, value=val, observed=v,
                passed=passed)


def explain(hid, f):
    """{gate: [...], inputs_missing: [...], conditions: [...],
    all_passed: bool} for one recorded feature dict."""
    h = by_id(hid)
    gate = [_clause(c, f) for c in h.get('gate', [])]
    req = h.get('required_inputs') or tuple(
        i['name'] for i in h.get('inputs', []) if i.get('role') != 'direction')
    missing = [k for k in req if f.get(k) is None]
    conds = [_clause(c, f) for c in h.get('conditions', [])]
    return dict(gate=gate, inputs_missing=missing, conditions=conds,
                all_passed=(all(g['passed'] for g in gate) and not missing
                            and all(c['passed'] is True for c in conds)))


DISCREPANCIES = [
    dict(item='A2 direction',
         earlier='"a large resting order gets hit and holds -> fade it"',
         verified='a2_depletion_continuation returns break_dir: a wall '
                  'that is executed THROUGH and not replenished, the clear '
                  'holding 5 s -> CONTINUATION in the break direction'),
    dict(item='A5 direction',
         earlier='"a level touch against the higher-timeframe trend -> '
                 'fade it"',
         verified='a5_pullback_resumption returns trend_dir: counter-trend '
                  'aggression that is absorbed and replenished -> RESUME '
                  'with the trend. Four of five inputs are passed as None'),
    dict(item='A6 versus W2-A4-OPEN',
         earlier='"A6: A4\'s setup, but only in the first hour"',
         verified='a6_open_continuation is a CONTINUATION (break_dir) '
                  'gated to 09:30:00-09:45:00 ET on six open-type levels '
                  '(OVERNIGHT_HIGH/LOW, YDAY_HIGH/LOW, GLOBEX_OPEN, '
                  'CASH_OPEN_0930). W2-A4-OPEN is a REVERSAL (W2-A4r) '
                  'gated to 09:30-10:30 ET on CASH_OPEN_0930 and the '
                  'overnight extremes. Different mechanism, window and '
                  'levels. The registration "folded A6 into W2-A4-OPEN" '
                  'as a budget decision, not an equivalence'),
    dict(item='prior history: 5 versus 20',
         earlier='various',
         verified='z-scores need >= 5 PRIOR SESSIONS in the 5-minute '
                  'bucket (20-session window); the W2-A4f residual model '
                  'needs >= 20 prior OBSERVATIONS in the bucket '
                  '(20-session window). Neither needs 20 sessions'),
    dict(item='A5 inputs that exist',
         earlier='"4 of 5 inputs hardcoded None"',
         verified='confirmed: trend_dir, adverse_z, adverse_progress_ticks '
                  'and trend_flip_z are None in mrofyt_runner; replenish_z '
                  'is wired (and execution-starved as in A1)'),
    dict(item='swing levels and Asia labels',
         earlier='"registered, not built"',
         verified='confirmed: mrofyt_swings_v016 exists as a frozen module '
                  'but is not a level provider for the runner and has '
                  'never run on real tape; Asia labels have no code'),
    dict(item='exposed sessions',
         earlier='"Sept 1-18 fully readable"',
         verified='the exposure ledger in the repository lists 20260901-'
                  '20260905 only; sessions are exposed by the pilot run '
                  'that inspects them, and the ledger that records it '
                  'lives beside the pilot that was run. A session not in '
                  'the ledger is protected here, whatever its date'),
    dict(item='the fourteen level identifiers',
         earlier='as listed in the build prompt',
         verified='identical to mrofyt_levels.ACTIVE_LEVEL_IDS'),
]
