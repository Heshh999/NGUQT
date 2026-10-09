#!/usr/bin/env python3
# MROF-YT-W4-DISCOVER-1.0 suite. The search engine is exercised on a
# planted-effect dataset and on pure noise, and the runner on synthetic
# recorder-format runs (mles_v12_synth). Synthetic events verify CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import hashlib
import io
import json
import math
import os
import random
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY      # noqa: E402
import mrofyt_bigmove as BM      # noqa: E402
import mrofyt_discover as DI     # noqa: E402
import mrofyt_pilot as PI        # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w4_')

# ---------------------------------------------------------------------
# F1-F3: the statistics against references
# ---------------------------------------------------------------------
t('F1: Student t two-sided p and critical values match the tables '
  '(t=2.262 df=9 -> 0.05; t_crit(1)=12.706; large df -> 1.960; t=0 -> 1)',
  abs(DI.t_p_two_sided(2.262157, 9) - 0.05) < 1e-5 and
  abs(DI.t_crit(1) - 12.7062) < 1e-3 and
  abs(DI.t_crit(9) - 2.262157) < 1e-5 and
  abs(DI.t_p_two_sided(1.959964, 10 ** 6) - 0.05) < 1e-4 and
  abs(DI.t_p_two_sided(0.0, 5) - 1.0) < 1e-12)
t('F2: Benjamini-Hochberg q-values on a hand case, monotone, with an '
  'untestable None counted in m',
  DI.bh_q([0.01, 0.04, 0.03, 0.005]) == [0.02, 0.04, 0.04, 0.02] and
  DI.bh_q([0.01, None, 0.04], m=3) == [0.03, None, 0.06])
rows = [('a', 1.0, 0.3, 100.0), ('a', 0.0, 0.3, -40.0),
        ('b', 1.0, 0.3, 100.0), ('c', 0.0, 0.3, -40.0),
        ('c', 1.0, 0.3, 100.0), ('c', 1.0, 0.3, 100.0)]
cs = DI.cluster_stats(rows)
# by hand: lift = (4 - 1.8)/6; d_a = 2-.6... resid_s = d_s - lift*n_s
lift = (4 - 1.8) / 6
d = {'a': (2, 1 - 0.6), 'b': (1, 1 - 0.3), 'c': (3, 2 - 0.9)}
ss = sum((ds - lift * n) ** 2 for n, ds in d.values())
se = math.sqrt(3 / 2.0 * ss / 36)
t('F3: the session-clustered lift, standard error, t (df = sessions - 1) '
  'and expectancy equal a hand computation',
  abs(cs['lift'] - round(lift, 4)) < 1e-9 and cs['sessions'] == 3 and
  abs(cs['se'] - round(se, 5)) < 1e-9 and cs['df'] == 2 and
  abs(cs['t'] - round(lift / se, 3)) < 1e-9 and
  cs['expectancy_ticks'] == round(320.0 / 6, 2) and
  cs['ci95'][0] < cs['lift'] < cs['ci95'][1])

# ---------------------------------------------------------------------
# F4-F5: the grammar and the cooldown
# ---------------------------------------------------------------------
rules = DI.enumerate_rules()
fam = {}
for r in rules:
    fam[r['family']] = fam.get(r['family'], 0) + 1
t('F4: the grammar has exactly 736 rules with unique ids (40 single '
  'signed, 16 single unsigned, 360 signed pairs, 320 unsigned-signed '
  'pairs) and 2 208 tests, the numbers the registration fixed',
  len(rules) == DI.N_RULES == 736 and len({r['id'] for r in rules}) == 736
  and fam == dict(S=40, U=16, SS=360, US=320) and DI.K_TESTS == 2208 and
  len(DI.FEATURES) == 14)


class _DS(object):
    def __init__(self, recs):
        self.recs = recs


recs = [dict(session='s1', t=x) for x in (0, 100, 299, 301, 650)] + \
    [dict(session='s2', t=50)]
ev = DI.dedup_ticks(_DS(recs), [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1),
                                (1, -1), (5, 1)])
t('F5: the 300 s cooldown is anchored on the first tick of an event, per '
  'session and direction: ticks at 0,100,299,301,650 give events at 0, '
  '301, 650; another direction or session is its own event',
  [(recs[k]['session'], recs[k]['t'], dd) for k, dd in ev] ==
  [('s1', 0, 1), ('s1', 100, -1), ('s1', 301, 1), ('s1', 650, 1),
   ('s2', 50, 1)])


# ---------------------------------------------------------------------
# F6: a planted effect is found, and pure noise yields no CANDIDATE
# ---------------------------------------------------------------------
def make(planted, seed=11, n_ses=12, per=600):
    rng = random.Random(seed)
    recs, outs = [], []
    for si in range(n_ses):
        ses = '202609%02d' % (si + 1)
        for k in range(per):
            r = dict(instrument='NQ', session=ses,
                     t=1e9 + si * 1e6 + k * 400.0, hour=10)
            for f in DI.FEATURES:
                r[f] = rng.gauss(0, 1)
            r['spread'] = 1.0                      # degenerate, as on NQ
            r['D60'] = rng.choice([-1.0, 1.0])
            recs.append(r)
    cut = sorted(x['z_d60'] for x in recs)[int(0.9 * (len(recs) - 1))]
    for r in recs:
        hot = planted and r['z_d60'] >= cut
        o = {}
        for dd in (1, -1):
            p = 0.75 if (hot and dd == 1) else (0.05 if hot else 0.25)
            o[dd] = [(('TARGET', 100.0) if rng.random() < p else
                      ('STOP', -s)) for s in DI.STOPS]
        outs.append(o)
    return DI.Dataset(recs, outs)


rby = {r['id']: r for r in rules}
dsP = make(True)
testsP, cutsP, evP = DI.search(dsP)
candP = [x for x in testsP if x['status'] == 'CANDIDATE']
nomP = DI.nominate(dsP, testsP, evP, rby)
t('F6: a long-only edge planted on z_d60\'s top decile is found: the '
  'exact rule is nominated first as a CANDIDATE, and nearly every '
  'CANDIDATE names that tail (the false share stays within the 10% FDR)',
  nomP and nomP[0]['rule'] == 'S:z_d60.top.d:with:z_d60' and
  nomP[0]['status'] == 'CANDIDATE' and nomP[0]['lift'] > 0.3 and
  len(testsP) == 2208 and
  sum(1 for x in candP if 'z_d60.top' not in x['rule']) <=
  0.10 * len(candP))
dsN = make(False)
testsN, _cN, evN = DI.search(dsN)
nomN = DI.nominate(dsN, testsN, evN, rby)
t('F6b: on pure noise no rule is a CANDIDATE; whatever is nominated is '
  'a LEAD with q above the bar, never presented as a finding',
  not any(x['status'] == 'CANDIDATE' for x in testsN) and
  all(x['status'] is None and x['q'] > DI.FDR_Q for x in nomN))
t('F6c: the degenerate spread tails (a constant one-tick spread) are '
  'untestable and still counted in m: every run has 2 208 tests',
  all(not x['testable'] for x in testsP if 'spread.' in x['rule']) and
  len(testsN) == 2208)

# ---------------------------------------------------------------------
# F7: the overlap rule keeps nominees distinct
# ---------------------------------------------------------------------
recs7 = [dict(session='s', t=x) for x in (0, 1000, 100, 5000)]
ds7 = _DS(recs7)
t('F7: overlap is the share of a rule\'s events with an event of another '
  'within 300 s on the same session; no two planted-run nominees '
  'overlap by half or more',
  DI._overlap(ds7, [(0, 1), (1, 1)], [(2, 1)]) == 0.5 and
  DI._overlap(ds7, [(0, 1), (1, 1)], [(3, 1)]) == 0.0 and
  all(DI._overlap(dsP, evP[a['rule']], evP[b['rule']]) < DI.OVERLAP_MAX
      for i, a in enumerate(nomP) for b in nomP[:i]))

# ---------------------------------------------------------------------
# F8: the frozen rule reproduces the search exactly
# ---------------------------------------------------------------------
cuts_by = {'NQ': cutsP}
fr = DI.frozen_rule(rby[nomP[0]['rule']], nomP[0], cuts_by)
j = list(DI.STOPS).index(fr['stop_ticks'])
st8 = DI.rule_stats(dsP, DI.apply_frozen(dsP, fr, 'NQ'), j)
fr2 = json.loads(json.dumps(fr))                 # as committed, via JSON
st8b = DI.rule_stats(dsP, DI.apply_frozen(dsP, fr2, 'NQ'), j)
t('F8: a nominated rule written out with numeric cut-points (and read '
  'back through JSON) reproduces the search\'s events and statistics '
  'exactly when applied to the same data',
  all(st8[k] == nomP[0][k] == st8b[k]
      for k in ('n', 'sessions', 'hit', 'baseline', 'lift', 't', 'p')) and
  fr['parts'][0]['cut']['NQ'] == cutsP['z_d60']['decile'][1] and
  fr['stop_ticks'] == nomP[0]['stop_ticks'])

# ---------------------------------------------------------------------
# F9-F12: the runner end to end on synthetic tape
# ---------------------------------------------------------------------
d9 = os.path.join(WORK, 'e2e')
path9 = lambda i: 15000.0 + 30.0 * math.sin(2 * math.pi * (i * 0.05) / 900.0)  # noqa: E731
SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260905',
            '20260908', '20260921')
for i, ses in enumerate(SESSIONS):
    SY.synth_run(d9, n_depth=40000, dt_step=0.05, price_path=path9,
                 trade_every=10, quote_every=5, cid='w4c%d' % i,
                 session=ses, seed=i)
buf = io.StringIO()
with redirect_stdout(buf):
    rc = DI.main([d9, '--unblind', '--out', os.path.join(WORK, 'x.json')])
t('F9: --unblind without --evaluate is refused before anything is read '
  '(the search reads DEV only, always)',
  rc == 2 and 'REFUSED' in buf.getvalue() and
  not os.path.exists(os.path.join(WORK, 'x.json')))
rep, w3, nom, r9 = DI.run_search(d9)
w3b, _rb = BM.run_bigmove(d9)
t('F10: one read gives wave four AND wave three: the wave-three report '
  'from the search\'s read equals a separate wave-three run (patterns, '
  'tests, baseline cells), and the validation session is refused',
  json.dumps(w3['patterns'], sort_keys=True, default=str) ==
  json.dumps(w3b['patterns'], sort_keys=True, default=str) and
  json.dumps(w3['tests'], sort_keys=True, default=str) ==
  json.dumps(w3b['tests'], sort_keys=True, default=str) and
  w3['baseline_cells'] == w3b['baseline_cells'] and
  rep['sessions_refused'] == ['20260921'] and
  rep['sessions_inspected'] == list(SESSIONS[:-1]) and
  not any(g['session'] > DI.DEV_END for g in r9.grid))
g9 = [g for g in r9.grid if g.get('resp60') is not None]
t('F10b: every grid record carries the fourteen features (None where '
  'history is short), the spread reads a real one-tick quote, and the '
  'report states 736 rules and 2 208 tests',
  all(f in g for g in r9.grid for f in DI.FEATURES) and g9 and
  {g['spread'] for g in r9.grid if g['spread'] is not None} == {1.0} and
  rep['n_rules'] == 736 and rep['k_tests'] == 2208 and
  len(rep['tests']) == 2208 and 'anatomy' in rep and
  json.dumps(rep, default=str))

# F11: causality -- the features at a tick do not change when the tape
# AFTER that tick is cut away
d11 = os.path.join(WORK, 'cut')
for i, ses in enumerate(SESSIONS[:-1]):
    SY.synth_run(d11, n_depth=(20000 if ses == '20260908' else 40000),
                 dt_step=0.05, price_path=path9, trade_every=10,
                 quote_every=5, cid='w4c%d' % i, session=ses, seed=i)
r11 = DI.DiscoverRunner(d11)
r11.run()
full = {(g['session'], g['t']): g for g in r9.grid
        if g['session'] == '20260908'}
cut = [g for g in r11.grid if g['session'] == '20260908']
keys = list(DI.FEATURES) + ['D60']
t('F11: causal by construction -- with the last session cut in half, '
  'every feature of every grid tick that still exists is identical to '
  'the full tape\'s (nothing after a tick feeds that tick)',
  cut and len(cut) < len(full) and
  all((g['session'], g['t']) in full and
      all(g.get(k) == full[(g['session'], g['t'])].get(k) for k in keys)
      for g in cut))

# F12: evaluate mode -- DEV reproduction, then the checkpoint read
nomfile = os.path.join(WORK, 'nom.json')
frs = [DI.frozen_rule(rby['U:dist_level.bottom.d:against:D60'],
                      dict(stop_ticks=40.0), rep['cuts'])]
json.dump(dict(nominated=frs), open(nomfile, 'w'))
repE, rE = DI.run_evaluate(d9, frs, unblind=False)
repU, rU = DI.run_evaluate(d9, frs, unblind=True)
led = os.path.join(WORK, 'ledger.json')
json.dump(dict(exposed_days=[dict(session='20260921',
                                  label=PI.BLIND_LABEL)]), open(led, 'w'))
DI.write_exposure_on_unblind(repU, led)
days = {x['session']: x for x in json.load(open(led))['exposed_days']}
t('F12: --evaluate without --unblind reads DEV only and labels its '
  'verdicts a reproduction; with --unblind it evaluates ONLY the '
  'validation session and the ledger marks it exposed by wave four',
  repE['sessions_refused'] == ['20260921'] and
  '20260921' not in repE['sessions_evaluated'] and
  all('reproduction' in x['verdict'] for x in repE['rules']) and
  repU['sessions_evaluated'] == ['20260921'] and
  repU['sessions_refused'] == [] and
  repU['rules'][0]['verdict'] in ('NOT TESTED', 'NO SIGNAL', 'PROMISING')
  and days['20260921']['label'] == PI.EXPOSURE_LABEL and
  days['20260921']['exposed_by'] == DI.W4_VERSION and
  days['20260921'].get('previously_blind') is True)

# ---------------------------------------------------------------------
# F13: nothing frozen changed
# ---------------------------------------------------------------------
_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
_led1 = PI.PilotRunner(d9, max_sessions=6).run()
_reg = open(os.path.join(HERE, 'MROF_YT_WAVE4_DISCOVERY_REGISTRATION.md')
            ).read()
t('F13: the wave-one ledger is byte-identical through the wave-four '
  'runner, the frozen signal module keeps its pinned hash, and the '
  'registration states the grammar, the tests, the cooldown, the '
  'halves, the five-rule cap and the pre-run correction',
  json.dumps({k: _led1.get(k) for k in _CMP}, sort_keys=True) ==
  json.dumps({k: r9.ledger.get(k) for k in _CMP}, sort_keys=True) and
  hashlib.sha256(open(os.path.join(HERE, 'mrofyt_signals.py'),
                      'rb').read()).hexdigest() ==
  '06ce854a40717a2398231eb8c5120d8e709c18fd8f7cb8d1ac2cc4ecc640a8e1' and
  '736' in _reg and '2 208' in _reg and '300 s' in _reg and
  'both' in _reg and 'At most five' in _reg and
  'pre-run correction' in _reg and 'Explicitly NOT registered' in _reg)

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
