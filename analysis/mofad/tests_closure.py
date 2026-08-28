#!/usr/bin/env python3
# MOFAD-V1 closure-stage tests: registry integrity + similarity screen.
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import similarity_screen as SS  # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-58s %s' % (name, 'PASS' if cond else 'FAIL'))


rows = SS.load_registry()
VALID = {'DEAD_FROZEN', 'INSUFFICIENT_DATA', 'DESCRIPTIVE_ONLY_SPENT',
         'PASSED_HISTORICAL_EXPLORATORY', 'RESERVED_UNTOUCHED'}

print('registry integrity')
t('every row has a valid disposition',
  all(r['disposition'] in VALID for r in rows))
t('every non-reserved row has a known fingerprint class',
  all(r['fingerprint_class'] in SS.CLASS_DEF
      for r in rows if r['fingerprint_class'] not in ('', '-')))
t('unique hypothesis ids', len({r['hyp_id'] for r in rows}) == len(rows))
t('ODMC registered DEAD_FROZEN',
  any(r['hyp_id'] == 'ODMC' and r['disposition'] == 'DEAD_FROZEN' for r in rows))
t('PASSED rows are exactly OFH13/OFH14/NVQ-STREAK3DN',
  sorted(r['hyp_id'] for r in rows
         if r['disposition'] == 'PASSED_HISTORICAL_EXPLORATORY')
  == ['NVQ-STREAK3DN', 'OFH13', 'OFH14'])

print('fingerprints deterministic')
fp = SS.build_fingerprints()
fp_disk = json.load(open(os.path.join(HERE, 'MOFAD_V1_SPENT_HYPOTHESIS_FINGERPRINTS.json')))
t('regenerated fingerprints byte-identical to committed file',
  json.dumps(fp, sort_keys=True) == json.dumps(fp_disk, sort_keys=True))
t('FVG_FLOW_MITIGATION is protected', fp['FVG_FLOW_MITIGATION']['protected'])

print('similarity screen enforcement')
# derivative rescues that MUST be rejected
rej = [
    dict(hyp_id='cumdelta-again', mechanism_class='OF_CUMDELTA_TREND',
         tokens=['cum_delta', 'trend_slope'], granularity='state', distinctness='x'),
    dict(hyp_id='ofh13-clone', mechanism_class='FVG_FLOW_MITIGATION',
         tokens=['fvg_zone', 'bar_delta', 'mitigation_retest'], granularity='event',
         distinctness='x'),
    dict(hyp_id='renamed-effort', mechanism_class='NEW_NAME_SAME_THING',
         tokens=['bar_delta', 'bar_range', 'effort_vs_result'], granularity='event',
         distinctness='x'),
    dict(hyp_id='mgmt-variant', mechanism_class='NEW_EXIT_RULE',
         tokens=['stops_targets_exits', 'parent_entries'], granularity='management',
         distinctness='x'),
    dict(hyp_id='no-justification', mechanism_class='SOMETHING_NEW',
         tokens=['overnight_flow'], granularity='state', distinctness=''),
]
for p in rej:
    v, _ = SS.screen(p, fp)
    t('rejects %s' % p['hyp_id'], v == 'REJECT')
# the MOFAD-V1 classes are spent now too - their rescue must be blocked
for cls, toks in (('INVENTORY_TRANSITION_FLOW',
                   ['overnight_cum_delta', 'session_transition',
                    'inventory_imbalance']),
                  ('IMPACT_ASYMMETRY',
                   ['rolling_price_impact', 'buy_vs_sell_lambda',
                    'liquidity_asymmetry_state'])):
    v, _ = SS.screen(dict(hyp_id='rescue-' + cls, mechanism_class=cls,
                          tokens=toks, granularity='state', distinctness='x'), fp)
    t('rejects rescue of spent MOFAD class %s' % cls, v == 'REJECT')
# a genuinely new mechanism class MUST be accepted
acc = dict(hyp_id='queue-depletion-msg', mechanism_class='QUEUE_DEPLETION_MSG',
           tokens=['depth_updates', 'queue_depletion', 'cancel_rate'],
           granularity='event',
           distinctness='new causal source: message-level depth updates from the '
                        'MOFAD capture program; no spent hypothesis observed the book')
v, why = SS.screen(acc, fp)
t('accepts a genuinely new mechanism class', v == 'ACCEPT')

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
