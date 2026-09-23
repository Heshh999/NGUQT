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


# how each derived (wave-two) family differs from the family it is
# derived from, exactly as mrofyt_wave2 implements it: an input swapped
# (W2-A1, W2-A4r-HC), an input forced None (W2-A4r and everything built
# on it: the response-failure test is progress_ticks <= 1 alone), an
# input required (W2-A4f: evaluated only where the residual model can
# speak), a threshold changed (W2-A4r-z15), a gate added (W2-A4-OPEN)
_SUBSTITUTE = {'W2-A1': {'replenish_z': 'repl10_z'},
               'W2-A4r-HC': {'aggr_z': 'aggr_z_hc'}}
_FORCE_NONE = {'W2-A4r': ('resid_tail_5pct',)}
_REQUIRE = {'W2-A4f': ('resid_tail_5pct',)}
_EXTRA_GATE = {'W2-A4-OPEN': [_c('in_0930_1030', 'is_true')]}


def _rename(cl, subs):
    if cl.get('op') == 'any':
        return _any(*[_rename(c, subs) for c in cl['clauses']])
    return dict(cl, feature=subs.get(cl['feature'], cl['feature']))


def _drop_forced(cl, forced):
    """A clause on a forced-None feature can never hold; inside an
    'any' it is removed, and an 'any' left with one clause is that
    clause (this is what forcing resid None does to A4's fail test)."""
    if cl.get('op') == 'any':
        kept = [_drop_forced(c, forced) for c in cl['clauses']
                if c.get('op') == 'any' or c['feature'] not in forced]
        if len(kept) == 1:
            return kept[0]
        return _any(*kept)
    return cl


def resolve(hid):
    """The gate, conditions and required inputs a family is actually
    judged by, following derived_from. Wave-one entries resolve to
    themselves; wave-two entries resolve to their base with the one
    change the registration made, so the same evaluator explains both."""
    h = by_id(hid)
    if h.get('derived_from'):
        base = resolve(h['derived_from'])
        gate = list(base['gate'])
        conds = [dict(c) for c in base['conditions']]
        req = list(base['required_inputs'])
        forced = set(base['forced_none'])
        chain = base['chain'] + [hid]
    else:
        gate = list(h.get('gate', []))
        conds = list(h.get('conditions', []))
        req = list(h.get('required_inputs') or [
            i['name'] for i in h.get('inputs', [])
            if i.get('role') != 'direction'])
        forced = set()
        chain = [hid]
    subs = _SUBSTITUTE.get(hid, {})
    if subs:
        conds = [_rename(c, subs) for c in conds]
        req = [subs.get(r, r) for r in req]
    forced |= set(_FORCE_NONE.get(hid, ()))
    if forced:
        conds = [_drop_forced(c, forced) for c in conds]
        req = [r for r in req if r not in forced]
    for r in _REQUIRE.get(hid, ()):
        if r not in req:
            req.append(r)
    thr = h.get('threshold_change')
    if thr:
        conds = [dict(c, value=thr['variant'])
                 if c.get('feature') == thr['feature'] and
                 c.get('value') == thr['frozen'] else c for c in conds]
    gate = gate + _EXTRA_GATE.get(hid, [])
    return dict(id=hid, chain=chain, gate=gate, conditions=conds,
                required_inputs=req, forced_none=sorted(forced),
                substitutions=subs,
                direction_sign=h.get('direction_sign'))


def explain(hid, f):
    """{gate: [...], inputs_missing: [...], conditions: [...],
    all_passed: bool} for one recorded feature dict, judged by the
    family's resolved conditions."""
    r = resolve(hid)
    if r['forced_none']:
        f = dict(f, **{k: None for k in r['forced_none']})
    gate = [_clause(c, f) for c in r['gate']]
    missing = [k for k in r['required_inputs'] if f.get(k) is None]
    conds = [_clause(c, f) for c in r['conditions']]
    return dict(gate=gate, inputs_missing=missing, conditions=conds,
                all_passed=(all(g['passed'] for g in gate) and not missing
                            and all(c['passed'] is True for c in conds)))


# ---------------------------------------------------------------------
# MECHANISM THEATRE: one scripted, synthetic scenario per hypothesis.
#
# These are ILLUSTRATIONS of what each frozen rule is looking for, not
# data: the values were chosen so that the final beat satisfies every
# resolved condition, and tests_godseye.py::G11 proves that by running
# the frozen detector itself on them. Each demo also carries one
# counter-example that changes ONE thing and does not fire, so the
# rule's edge is visible. `inputs` accumulate beat by beat; `px` is the
# price in ticks relative to the level; `bid`/`ask` are displayed sizes
# resting at the level; `prints` are executions in that beat.
# ---------------------------------------------------------------------
def _beat(caption, px, bid, ask, prints=(), inputs=()):
    return dict(caption=caption, px=px, bid=bid, ask=ask,
                prints=[list(p) for p in prints],
                inputs=[list(i) for i in inputs])


_A4_BEATS = [
    _beat('approach from below: price climbs into the level; sellers rest '
          'on the offer there', -2, 9, 30, [['BUY', 4]]),
    _beat('an aggressive push: buyers hit the level hard (aggr_z 2.3), '
          'price pokes one tick through (progress 1) and no further -- '
          'the push under-responds', 1, 7, 26,
          [['BUY', 14], ['BUY', 11], ['BUY', 9]],
          [['aggr_z', 2.3], ['progress_ticks', 1], ['aggr_dir', 1]]),
    _beat('price comes back through the level (returned_through_level)',
          -1, 12, 34, [['SELL', 8], ['SELL', 6]],
          [['returned_through_level', True], ['sweep_reclaimed_5s', False]]),
    _beat('the opposite side flips: sellers turn aggressive '
          '(opp_flip_z 1.2)', -2, 15, 38, [['SELL', 12], ['SELL', 9]],
          [['opp_flip_z', 1.2]]),
    _beat('decision: aggression, failed response, return, flip -- fire '
          'SHORT (-aggr_dir), away from the failed push', -3, 17, 40,
          [['SELL', 5]]),
]

DEMOS = [
    dict(id='A1', title='Absorption reversal', level='YDAY_HIGH', ad=1,
         setting='price rises into yesterday\'s high from below; sellers '
                 'rest at the level',
         beats=[
             _beat('a second approach inside 60 s (approaches_60s 2): price '
                   'climbs back to the level', -2, 8, 40, [['BUY', 5]],
                   [['approaches_60s', 2]]),
             _beat('aggressive buying hits the offer (aggr_z 2.6) but price '
                   'does not advance (progress 0 ticks)', 0, 6, 32,
                   [['BUY', 12], ['BUY', 9], ['BUY', 14]],
                   [['aggr_z', 2.6], ['progress_ticks', 0], ['aggr_dir', 1]]),
             _beat('the offer refills faster than it is eaten '
                   '(replenish_z 2.1): the buying is being absorbed', 0, 6, 44,
                   [['BUY', 7]], [['replenish_z', 2.1]]),
             _beat('the other side flips: sellers turn aggressive '
                   '(opp_flip_z 1.4) and price retreats a tick '
                   '(retreat_ticks 1)', -1, 10, 46, [['SELL', 11], ['SELL', 8]],
                   [['opp_flip_z', 1.4], ['retreat_ticks', 1]]),
             _beat('decision: every condition held -- fire SHORT (-aggr_dir), '
                   'away from the absorbed buyers', -2, 12, 48, [['SELL', 6]]),
         ],
         counter=dict(caption='same tape, but the offer is NOT refilled '
                              '(replenish_z 0.3): nothing absorbed the '
                              'buying, so A1 stays silent -- a wall being '
                              'eaten through is A2\'s territory, not A1\'s',
                      inputs=[['replenish_z', 0.3]])),
    dict(id='A2', title='Depletion continuation', level='YDAY_HIGH', ad=1,
         setting='a qualifying wall (wall_z 2.4) rests on the offer at '
                 'yesterday\'s high; price approaches from below',
         beats=[
             _beat('the wall is visible: displayed size on the offer is 2.4 '
                   'baseline deviations above normal', -2, 8, 120, [],
                   [['wall_z', 2.4]]),
             _beat('it is executed THROUGH: 1.8x its displayed size trades '
                   'into it (exec_vs_displayed 1.8)', 0, 8, 40,
                   [['BUY', 60], ['BUY', 70], ['BUY', 85]],
                   [['exec_vs_displayed', 1.8]]),
             _beat('and it is not refilled (replenish_ratio 0.1): the level '
                   'clears', 1, 10, 12, [['BUY', 20]],
                   [['replenish_ratio', 0.1]]),
             _beat('the clear holds 5 s (cleared_held_5s) and flow keeps '
                   'agreeing, tick after tick (persist_agree 4)', 2, 14, 10,
                   [['BUY', 9], ['BUY', 11], ['BUY', 8], ['BUY', 10]],
                   [['cleared_held_5s', True], ['persist_agree', 4],
                    ['break_dir', 1]]),
             _beat('flow after the clear is still elevated (post_clear_z '
                   '1.3) -- fire LONG (break_dir): continuation THROUGH the '
                   'wall, not a fade of it', 3, 16, 9, [['BUY', 13]],
                   [['post_clear_z', 1.3]]),
         ],
         counter=dict(caption='the wall is hit just as hard, but it refills '
                              '(replenish_ratio 0.6): not a depletion -- '
                              'that tape is closer to A1',
                      inputs=[['replenish_ratio', 0.6]])),
    dict(id='A3', title='Vacuum continuation', level='SESSION_VWAP', ad=1,
         setting='the book above price thins out without being traded '
                 'through; this family runs on its own 2 s grid and needs a '
                 'feed on which ADD/REMOVE/UPDATE are distinguishable',
         beats=[
             _beat('the feed distinguishes depth actions '
                   '(actions_distinguishable): pulls can be told from '
                   'executions', -1, 20, 60, [],
                   [['actions_distinguishable', True]]),
             _beat('the target side (the offer) drops 70% within 2 s with no '
                   'matching executions (tgt_drop_frac 0.70): the liquidity '
                   'was pulled, not eaten', -1, 20, 18, [],
                   [['tgt_drop_frac', 0.70]]),
             _beat('the opposite side barely moves (opp_drop_frac 0.10): '
                   'this is not a book reset', -1, 18, 16, [],
                   [['opp_drop_frac', 0.10]]),
             _beat('flow leans into the gap (delta_z 1.4) and price advances '
                   'two ticks (advance_ticks 2)', 1, 18, 14,
                   [['BUY', 9], ['BUY', 12]],
                   [['delta_z', 1.4], ['advance_ticks', 2], ['vacuum_dir', 1]]),
             _beat('decision: fire LONG (vacuum_dir): continuation INTO the '
                   'vacuum', 2, 18, 12, [['BUY', 7]]),
         ],
         counter=dict(caption='both sides drop together (opp_drop_frac '
                              '0.50): that is a book reset or a blackout, '
                              'not a vacuum -- no fire',
                      inputs=[['opp_drop_frac', 0.50]])),
    dict(id='A4', title='Response-failure reversal', level='YDAY_HIGH', ad=1,
         setting='price pushes through yesterday\'s high from below and '
                 'the push does not get paid',
         beats=_A4_BEATS,
         counter=dict(caption='the push under-responds and sellers flip, '
                              'but price never comes back through the level '
                              '(no return, no reclaim): no reversal to '
                              'trade -- no fire',
                      inputs=[['returned_through_level', False],
                              ['sweep_reclaimed_5s', False]])),
    dict(id='A5', title='Pullback resumption', level='SESSION_VWAP', ad=-1,
         setting='an up-trend (trend_dir +1) pulls back DOWN into VWAP from '
                 'above. NOTE: four of these five inputs are passed as '
                 'None by the runner today, so this is what the rule '
                 'WOULD look for, not something the pilot can see',
         beats=[
             _beat('the higher-timeframe trend is up (trend_dir +1); price '
                   'pulls back into VWAP from above', 1, 40, 12,
                   [['SELL', 5]], [['trend_dir', 1]]),
             _beat('counter-trend selling hits the bid at the level '
                   '(adverse_z 2.2) and price does not give way '
                   '(adverse_progress_ticks 0)', 0, 34, 10,
                   [['SELL', 13], ['SELL', 10], ['SELL', 12]],
                   [['adverse_z', 2.2], ['adverse_progress_ticks', 0]]),
             _beat('the bid refills (replenish_z 1.9): the pullback is being '
                   'absorbed', 0, 46, 10, [['SELL', 6]],
                   [['replenish_z', 1.9]]),
             _beat('the trend side flips back to aggression '
                   '(trend_flip_z 1.3)', 1, 48, 8, [['BUY', 11], ['BUY', 9]],
                   [['trend_flip_z', 1.3]]),
             _beat('decision: fire LONG (trend_dir): RESUMPTION with the '
                   'trend -- the pullback is faded, the trend followed',
                   2, 50, 7, [['BUY', 8]]),
         ],
         counter=dict(caption='the pullback is absorbed but the trend side '
                              'never flips back (trend_flip_z 0.2): no '
                              'resumption yet -- no fire',
                      inputs=[['trend_flip_z', 0.2]])),
    dict(id='A6', title='Open continuation', level='OVERNIGHT_LOW', ad=-1,
         setting='09:31 ET: price breaks the overnight low from above '
                 '(ad -1) inside the first 15 minutes of cash trading',
         beats=[
             _beat('the gate: 09:30:00-09:45:00 ET and an open-type level '
                   '(in_0930_0945)', 1, 30, 14, [['SELL', 6]],
                   [['in_0930_0945', True]]),
             _beat('a clean cross: price goes through the level without '
                   'trading back across it (clean_cross)', -1, 12, 16,
                   [['SELL', 14], ['SELL', 11]],
                   [['clean_cross', True], ['break_dir', -1]]),
             _beat('control flow is strong (control_z 2.5) and the break '
                   'holds 5 s (held_5s)', -2, 10, 18,
                   [['SELL', 12], ['SELL', 9], ['SELL', 10]],
                   [['control_z', 2.5], ['held_5s', True]]),
             _beat('flow keeps agreeing tick after tick (persist_agree 3) '
                   'and the far side does NOT refill (opp_replenish_z 0.4)',
                   -3, 9, 20, [['SELL', 8], ['SELL', 7], ['SELL', 9]],
                   [['persist_agree', 3], ['opp_replenish_z', 0.4]]),
             _beat('decision: fire SHORT (break_dir): CONTINUATION of the '
                   'break -- not A4\'s reversal', -4, 8, 22, [['SELL', 6]]),
         ],
         counter=dict(caption='same break, but the far side refills '
                              '(opp_replenish_z 2.0): the break is being '
                              'absorbed -- no continuation, no fire',
                      inputs=[['opp_replenish_z', 2.0]])),
    dict(id='W2-A1', title='A1 with replenishment on every grid tick',
         level='YDAY_HIGH', ad=1,
         setting='the same tape as A1; the one change is HOW '
                 'replenishment is measured: adds at the top-3 levels over '
                 '10 s divided by executions there, observed on EVERY grid '
                 'tick (repl10_z) instead of only when an execution '
                 'happens at the level',
         beats=[
             _beat('second approach inside 60 s', -2, 8, 40, [['BUY', 5]],
                   [['approaches_60s', 2]]),
             _beat('aggressive buying (aggr_z 2.6), no progress', 0, 6, 32,
                   [['BUY', 12], ['BUY', 9], ['BUY', 14]],
                   [['aggr_z', 2.6], ['progress_ticks', 0], ['aggr_dir', 1]]),
             _beat('adds at the top three offer levels outrun executions '
                   'over the 10 s window (repl10_z 2.0) -- measurable on '
                   'this tick even though nothing traded AT the level',
                   0, 6, 44, [], [['repl10_z', 2.0]]),
             _beat('sellers flip (opp_flip_z 1.4), price retreats a tick',
                   -1, 10, 46, [['SELL', 11], ['SELL', 8]],
                   [['opp_flip_z', 1.4], ['retreat_ticks', 1]]),
             _beat('decision: fire SHORT (-aggr_dir), as A1', -2, 12, 48,
                   [['SELL', 6]]),
         ],
         counter=dict(caption='adds do not outrun executions '
                              '(repl10_z 0.2): no absorption -- no fire',
                      inputs=[['repl10_z', 0.2]])),
    dict(id='W2-A4r', title='A4 as it ran', level='YDAY_HIGH', ad=1,
         setting='A4 with resid_tail_5pct forced None: the response-failure '
                 'test is progress_ticks <= 1 alone. This is the version '
                 'that produced every wave-one A4 event',
         beats=_A4_BEATS,
         counter=dict(caption='sellers never flip (opp_flip_z 0.3): the '
                              'failed push is not answered -- no fire',
                      inputs=[['opp_flip_z', 0.3]])),
    dict(id='W2-A4f', title='A4 as written (residual wired)',
         level='YDAY_HIGH', ad=1,
         setting='the push DOES move price three ticks -- but the '
                 'expected-response model says that is in the bottom 5% '
                 'of what such aggression normally buys (resid_tail_5pct). '
                 'Only the residual can call this a failure; progress '
                 'alone would not',
         beats=[
             _beat('approach from below', -2, 9, 30, [['BUY', 4]]),
             _beat('a hard push (aggr_z 2.8) moves price three ticks '
                   '(progress 3) -- on its face, a response', 3, 7, 22,
                   [['BUY', 16], ['BUY', 13], ['BUY', 12]],
                   [['aggr_z', 2.8], ['progress_ticks', 3], ['aggr_dir', 1]]),
             _beat('the residual model, fitted on >= 20 prior observations '
                   'in this 5-minute bucket, expected far more: the response '
                   'is in the bottom 5% tail (resid_tail_5pct True)', 3, 7, 24,
                   [], [['resid_tail_5pct', True]]),
             _beat('price comes back through (returned_through_level) and '
                   'sellers flip (opp_flip_z 1.3)', -1, 13, 36,
                   [['SELL', 12], ['SELL', 10], ['SELL', 9]],
                   [['returned_through_level', True],
                    ['sweep_reclaimed_5s', False], ['opp_flip_z', 1.3]]),
             _beat('decision: fire SHORT (-aggr_dir), and this event is '
                   'resid-only: A4r would NOT have fired here', -2, 15, 40,
                   [['SELL', 6]]),
         ],
         counter=dict(caption='the model says the three-tick response was '
                              'normal (resid_tail_5pct False): with progress '
                              '3 there is no failure -- no fire',
                      inputs=[['resid_tail_5pct', False]])),
    dict(id='W2-A4-OPEN', title='A4r where the mechanism is forced',
         level='CASH_OPEN_0930', ad=1,
         setting='09:52 ET, at the cash open price: the first hour, where '
                 'a failed push is most likely to be a genuine failure. A '
                 'REVERSAL family -- the opposite of A6',
         beats=[_beat('the gate: 09:30-10:30 ET on CASH_OPEN_0930 or an '
                      'overnight extreme (in_0930_1030)', -2, 9, 30,
                      [['BUY', 4]], [['in_0930_1030', True]])] + _A4_BEATS[1:],
         counter=dict(caption='the identical tape at 10:45 ET '
                              '(in_0930_1030 False): outside the window '
                              'the mechanism is not forced -- W2-A4r may '
                              'fire, W2-A4-OPEN does not',
                      inputs=[['in_0930_1030', False]])),
    dict(id='W2-A4r-z15', title='A4r at aggr_z >= 1.5', level='YDAY_HIGH',
         ad=1,
         setting='the same failed push with milder aggression (aggr_z 1.7): '
                 'below the frozen 2.0, above the variant\'s 1.5. Reported '
                 'BESIDE W2-A4r, never in place of it',
         beats=[
             _beat('approach from below', -2, 9, 30, [['BUY', 4]]),
             _beat('a moderate push (aggr_z 1.7) pokes one tick through and '
                   'stalls (progress 1)', 1, 7, 26, [['BUY', 9], ['BUY', 8]],
                   [['aggr_z', 1.7], ['progress_ticks', 1], ['aggr_dir', 1]]),
             _beat('price comes back through', -1, 12, 34,
                   [['SELL', 8], ['SELL', 6]],
                   [['returned_through_level', True],
                    ['sweep_reclaimed_5s', False]]),
             _beat('sellers flip (opp_flip_z 1.2)', -2, 15, 38,
                   [['SELL', 12], ['SELL', 9]], [['opp_flip_z', 1.2]]),
             _beat('decision: the z15 variant fires SHORT; W2-A4r itself '
                   'would not (1.7 < 2.0)', -3, 17, 40, [['SELL', 5]]),
         ],
         counter=dict(caption='aggression at 1.2: below even the variant\'s '
                              'threshold -- no fire',
                      inputs=[['aggr_z', 1.2]])),
    dict(id='W2-A4r-HC', title='A4r on high-confidence aggressor',
         level='YDAY_HIGH', ad=1,
         setting='aggr_z is recomputed from prints whose inferred aggressor '
                 'side is HIGH confidence only (aggr_z_hc). Here the '
                 'all-prints z is 1.4 -- much of it low-confidence -- while '
                 'the high-confidence prints alone read 2.2',
         beats=[
             _beat('approach from below', -2, 9, 30, [['BUY', 4]]),
             _beat('a push whose HIGH-confidence prints are decisive '
                   '(aggr_z_hc 2.2; all-prints aggr_z only 1.4); one tick '
                   'through, stall', 1, 7, 26, [['BUY', 14], ['BUY', 10]],
                   [['aggr_z_hc', 2.2], ['aggr_z', 1.4], ['progress_ticks', 1],
                    ['aggr_dir', 1]]),
             _beat('price comes back through', -1, 12, 34,
                   [['SELL', 8], ['SELL', 6]],
                   [['returned_through_level', True],
                    ['sweep_reclaimed_5s', False]]),
             _beat('sellers flip (opp_flip_z 1.2)', -2, 15, 38,
                   [['SELL', 12], ['SELL', 9]], [['opp_flip_z', 1.2]]),
             _beat('decision: fire SHORT on the high-confidence measure; '
                   'this arm measures what the aggressor inference costs',
                   -3, 17, 40, [['SELL', 5]]),
         ],
         counter=dict(caption='the high-confidence prints alone are not '
                              'decisive (aggr_z_hc 1.1): no fire, whatever '
                              'the all-prints z says',
                      inputs=[['aggr_z_hc', 1.1]])),
    dict(id='ARM-B1', title='Candle-only rejection wick', level='YDAY_HIGH',
         ad=1, kind='candles',
         setting='no flow input at all: the 1-minute bar containing the '
                 'approach. The control every flow family must beat',
         bars=[[0, 14998.0, 15004.0, 14997.5, 14998.5, 100]],
         level_px=15000.0,
         beats=[
             _beat('the bar containing the approach opens below the level '
                   'and pokes above it', 0, 0, 0),
             _beat('the wick beyond the level is 4.0 of a 6.5 range (62%, '
                   '>= 50%)', 0, 0, 0),
             _beat('and the bar closes back below the level (14998.5 < '
                   '15000): fire SHORT (-ad), away from the wick, at the '
                   'first print after the minute ends', 0, 0, 0),
         ],
         counter=dict(caption='the same wick, but the bar closes ABOVE the '
                              'level (15001): not a rejection -- no fire',
                      bars=[[0, 14998.0, 15004.0, 14997.5, 15001.0, 100]])),
    dict(id='ARM-B2', title='Candle-only engulfing reclaim', level='YDAY_HIGH',
         ad=1, kind='candles',
         setting='two 1-minute bars: the first closes THROUGH the level, '
                 'the next closes back on the original side',
         bars=[[0, 14998.5, 15002.0, 14998.0, 15001.5, 100],
               [60, 15001.5, 15002.0, 14997.0, 14998.0, 120]],
         level_px=15000.0,
         beats=[
             _beat('bar 1 closes through the level (15001.5 > 15000)', 0, 0, 0),
             _beat('bar 2 opens there and trades back down', 0, 0, 0),
             _beat('bar 2 closes back on the original side (14998 < 15000): '
                   'fire SHORT (-ad) at the second bar\'s close', 0, 0, 0),
         ],
         counter=dict(caption='bar 2 closes at 15000.5: still through -- '
                              'no reclaim, no fire',
                      bars=[[0, 14998.5, 15002.0, 14998.0, 15001.5, 100],
                            [60, 15001.5, 15002.0, 14997.0, 15000.5, 120]])),
    dict(id='ARM-C', title='Placebo levels', level='placebo(YDAY_HIGH)', ad=1,
         setting='the W2-A4r tape replayed at a level that is NOT a level: '
                 'yesterday\'s high shifted by 6-20 proximity radii, seeded '
                 'per session and level, kept >= 3 radii from every real '
                 'level. If the families fire as often here, the level is '
                 'not doing the work',
         beats=_A4_BEATS,
         counter=dict(caption='(the control has no counter-example: it is '
                              'compared to, not judged)', inputs=[])),
]


def demo_inputs(demo, counter=False):
    """The accumulated input dict at the final beat (with the
    counter-example's overrides applied when asked)."""
    f = {}
    for b in demo['beats']:
        for k, v in b['inputs']:
            f[k] = v
    if counter:
        for k, v in demo['counter'].get('inputs', []):
            f[k] = v
    return f


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
