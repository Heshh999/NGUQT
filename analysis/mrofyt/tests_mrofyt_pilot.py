#!/usr/bin/env python3
# MROF-YT-PILOT-1.0 suite. The pilot diagnostic is exercised on
# synthetic recorder-format runs (mles_v12_synth) plus hand-built
# fixtures. Synthetic events verify CODE BEHAVIOR only, never market
# evidence. P1 and P2 pin the two defects that the first genuine
# recordings exposed. No outcome, R or P&L exists anywhere.
import json
import math
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY      # noqa: E402
import mrofyt_pilot as PI        # noqa: E402
import mrofyt_runner as RN       # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_pilot_')
path = lambda i: 15000.0 + 3.0 * math.sin(2 * math.pi * (i * 0.0005) / 20.0)  # noqa: E731

# ---------------------------------------------------------------------
# P1: a manifest whose bulk CSVs have not arrived is SKIPPED WHOLE and
# recorded — never crashed on, and never half-ingested. The documented
# handoff sends manifests first, so this is an ordinary state.
# ---------------------------------------------------------------------
d1 = os.path.join(WORK, 'partial')
SY.synth_run(d1, n_depth=120000, price_path=path, trade_every=10,
             quote_every=5, cid='full', session='20260901')
mp2 = SY.synth_run(d1, n_depth=20000, price_path=path, trade_every=10,
                   quote_every=5, cid='gone', session='20260901',
                   t0=None, run_no=2)
man2 = json.load(open(mp2))
removed = []
for k in ('quotes', 'trades'):
    f = os.path.join(d1, man2[k]['file'])
    os.remove(f)
    removed.append(man2[k]['file'])
led1 = RN.Runner(d1, ('NQ',)).run()
sk = led1.get('skipped_runs', [])
t('P1: a manifest with absent bulk CSVs is skipped whole (never crashes, '
  'never partially ingested) and the missing files are named',
  len(sk) == 1 and sorted(sk[0]['missing']) == sorted(removed) and
  led1['totals']['events'] > 0 and
  sum(1 for r in led1['runs'] if r.get('skipped')) == 1)

t('P1b: the skipped run contributes no events and the summary reports '
  'ingested and skipped counts separately',
  'skipped-missing-files 1' in RN.summary(led1))

# ---------------------------------------------------------------------
# P2: markouts. The horizon almost never lands exactly on a tick, so the
# coverage test is "the run reaches the horizon", not "a tick exists at
# the horizon"; and a markout never spans two runs, because concurrent
# duplicate recorder instances overlap in time and a cross-run markout
# would read a recording gap as a price move.
# ---------------------------------------------------------------------
r2 = PI.PilotRunner.__new__(PI.PilotRunner)
r2.series = {}
import array as _a  # noqa: E402
ts, ps = _a.array('d'), _a.array('d')
for i in range(100):
    ts.append(1000.0 + i * 0.37)          # no tick lands on a whole second
    ps.append(15000.0 + i * 0.25)
r2.series[('NQ', 'RUN_A')] = (ts, ps)
ts2, ps2 = _a.array('d'), _a.array('d')
for i in range(50):
    ts2.append(9000.0 + i * 0.37)         # a much later, separate run
    ps2.append(16000.0 + i * 0.25)
r2.series[('NQ', 'RUN_B')] = (ts2, ps2)

m1 = r2.markout('NQ', 'RUN_A', 1000.0, 1.0)
m_far = r2.markout('NQ', 'RUN_A', 1000.0, 180.0)
m_other = r2.markout('NQ', 'RUN_A', 9000.0, 1.0)
t('P2: a markout resolves when the run reaches the horizon even though '
  'no tick lands on it (last mid at or before, never interpolated)',
  m1 is not None and abs(m1 - 2.0) < 1e-9)
t('P2b: a horizon beyond the end of the run returns None instead of '
  'silently using the last available price',
  m_far is None)
t('P2c: a markout never crosses a run boundary, so an adjacent run '
  'cannot supply the forward price',
  m_other is None)

# ---------------------------------------------------------------------
# P3: the funnel decomposition matches the frozen detectors exactly —
# any window the funnel marks PASSED_ALL_STAGES must fire, and any
# window it disqualifies must not.
# ---------------------------------------------------------------------
pass_f = dict(aggr_z=2.5, aggr_dir=1, progress_ticks=0, replenish_z=2.0,
              approaches_60s=3, opp_flip_z=1.5, retreat_ticks=2)
fail_f = dict(pass_f, aggr_z=1.0)
none_f = dict(pass_f, replenish_z=None)


def stage_of(fam, f):
    for name, pred in PI.FUNNELS[fam]:
        try:
            ok = pred(f)
        except (TypeError, KeyError):
            ok = False
        if not ok:
            return name
    return 'PASSED_ALL_STAGES'


t('P3: a window the A1 funnel passes fires A1, one it stops at a '
  'threshold does not, and a missing input stops it at inputs_available',
  stage_of('A1', pass_f) == 'PASSED_ALL_STAGES' and
  PI.SIG.DETECTORS['A1'](pass_f) != 0 and
  stage_of('A1', fail_f) == 'aggr_z>=2.0' and
  PI.SIG.DETECTORS['A1'](fail_f) == 0 and
  stage_of('A1', none_f) == 'inputs_available' and
  PI.SIG.DETECTORS['A1'](none_f) == 0)

t('P3b: every family in FUNNELS is a frozen detector and A5 stops at '
  'inputs_available because trend_dir is NOT WIRED',
  set(PI.FUNNELS) <= set(PI.SIG.DETECTORS) and
  stage_of('A5', dict(trend_dir=None, adverse_z=3.0,
                      adverse_progress_ticks=0, replenish_z=2.0,
                      trend_flip_z=2.0)) == 'inputs_available')

# ---------------------------------------------------------------------
# P4: end-to-end pilot on synthetic data — the report is produced, the
# two answers are separate, and step 10 records that no model was
# searched.
# ---------------------------------------------------------------------
rep, r4 = PI.run_pilot(d1)
v = rep['verdicts']
t('P4: the pilot returns TWO separate answers and does not let either '
  'imply the other',
  set(v) == {'answer_1_is_the_system_working',
             'answer_2_do_any_hypotheses_appear_promising',
             'separation_note'} and
  v['answer_1_is_the_system_working']['verdict'] == 'YES' and
  v['answer_2_do_any_hypotheses_appear_promising']['verdict'] ==
  'NOT_OBSERVED')

t('P4b: with zero frozen signals the signal markouts stay EMPTY and the '
  'window block is explicitly labelled non-directional',
  rep['step7_descriptive_markouts']['signal_population'] ==
  'NO_FROZEN_SIGNALS' and
  all(d['n'] == 0 for d in rep['step7_descriptive_markouts']
      ['signal_markouts_signed_ticks'].values()) and
  'not directional evidence' in
  rep['step7_descriptive_markouts']['window_reference_caveat'])

t('P4c: matched controls are NOT_APPLICABLE rather than invented when '
  'there is no signal population to match',
  rep['step8_matched_controls']['status'] == 'NOT_APPLICABLE')

t('P4d: step 10 records that no model, threshold or feature was '
  'searched on these days',
  rep['step10_model_search']['performed'] is False)

t('P4e: the pilot report contains no fill, stop, target, R or P&L key',
  not re.search(r'"(R|pnl|fill|target|stop)[a-z_]*":',
                json.dumps(rep, default=str)))

# ---------------------------------------------------------------------
# P5: coverage arithmetic. Concurrent duplicate recorder instances of
# the same feed collapse into one window: they are copies, not
# independent observations, and counting them twice would overstate the
# evidence base.
# ---------------------------------------------------------------------
ver = [dict(instrument='NQ', first='2026-09-01T14:00:00Z',
            last='2026-09-01T14:01:00Z'),
       dict(instrument='NQ', first='2026-09-01T14:00:00Z',
            last='2026-09-01T14:01:00Z'),      # duplicate instance
       dict(instrument='NQ', first='2026-09-01T14:05:00Z',
            last='2026-09-01T14:06:00Z'),
       dict(instrument='MNQ', first='2026-09-01T14:00:30Z',
            last='2026-09-01T14:02:00Z')]
cov = PI.coverage_windows(ver)
t('P5: duplicate concurrent instances collapse into one coverage window '
  '(120 s from three NQ runs, not 180 s)',
  cov['NQ']['seconds'] == 120.0 and len(cov['NQ']['windows']) == 2 and
  cov['NQ']['runs'] == 3)
t('P5b: NQ/MNQ simultaneous coverage is the intersection, not the sum',
  cov['NQ_MNQ_simultaneous_seconds'] == 30.0)

# ---------------------------------------------------------------------
# P6: exposure labelling is permanent and append-only.
# ---------------------------------------------------------------------
led_path = os.path.join(WORK, 'exposed.json')
PI.write_exposure_ledger(dict(sessions_inspected=['20260901'],
                              sessions_with_verified_bulk_csv=['20260901']),
                         led_path)
PI.write_exposure_ledger(dict(sessions_inspected=['20260902'],
                              sessions_with_verified_bulk_csv=[]),
                         led_path)
ex = json.load(open(led_path))
days = {d['session'] for d in ex['exposed_days']}
t('P6: the exposure ledger is append-only, so a day once labelled '
  'EXPOSED_PILOT_DEV can never be unlabelled by a later run',
  days == {'20260901', '20260902'} and
  all(d['label'] == 'EXPOSED_PILOT_DEV' for d in ex['exposed_days']) and
  'never become untouched prospective validation' in ex['rule'])

# ---------------------------------------------------------------------
# P7: the pilot classifies BLOCKED, with the exact failing artifact, when
# a stage genuinely cannot run.
# ---------------------------------------------------------------------
d7 = os.path.join(WORK, 'manifests_only')
mp = SY.synth_run(d7, n_depth=5000, price_path=path, cid='m1',
                  session='20260901')
man = json.load(open(mp))
for k in ('quotes', 'trades', 'depth', 'quality'):
    os.remove(os.path.join(d7, man[k]['file']))
rep7, _ = PI.run_pilot(d7)
cl = rep7['classification']
t('P7: manifests with no bulk CSV at all classify PILOT_BLOCKED and name '
  'the exact blocking stage and artifact',
  cl['status'] == 'PILOT_BLOCKED' and
  any(b['stage'] == 'step2_pipeline_proof' for b in cl['blocking']))

t('P7b: a pilot that completed every stage the data can support is '
  'PILOT_DIAGNOSTIC_COMPLETE - INSUFFICIENT_DATA_FOR_EV, which still '
  'asserts nothing about EV',
  rep['classification']['status'].startswith(
      'PILOT_DIAGNOSTIC_COMPLETE') and
  'INSUFFICIENT_DATA_FOR_EV' in rep['classification']['status'])

# ---------------------------------------------------------------------
# P8: the pilot never unlocks outcomes.
# ---------------------------------------------------------------------
try:
    RN.compute_outcomes()
    locked = False
except RuntimeError as e:
    locked = 'STATE-C LOCKED' in str(e)
src = open(os.path.join(HERE, 'mrofyt_pilot.py')).read()
t('P8: the pilot module calls no fill/stop/target/simulate/P&L function '
  'and compute_outcomes still raises STATE-C LOCKED',
  locked and not re.search(r'\b(entry_fill|structural_stop|simulate|'
                           r'y_dollars|compute_outcomes)\s*\(', src))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
