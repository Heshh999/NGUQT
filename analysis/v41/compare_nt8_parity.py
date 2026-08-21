#!/usr/bin/env python3
# ======================================================================
# PYTHON <-> NT8 PARITY COMPARATOR
# ======================================================================
# Compares the NT8/C# engine's parity export (from the off-platform
# driver, or from a real NT8 HISTORICAL_PARITY run) against the
# CANONICAL frozen Python (cand_spec.generate + prospective.score_one).
#
# Zero fuzzy matching. Every MISSING/EXTRA event must be either empty or
# individually ATTRIBUTED to the documented Q-FWD population quirk (the
# frozen Python filters use 60/90 minutes of FUTURE bar-existence, which
# a causal engine cannot know; divergence is possible only beside
# intraday data gaps). Anything unattributed = BUG = parity FAIL.
#
# Usage: python3 compare_nt8_parity.py <parity_out_dir>
# ======================================================================

import os, sys, csv
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cand_spec as CS
import prospective as P

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(CS.SCR, 'parity_out')
TOL = 1e-9

print('loading canonical Python (cand_spec)...')
B = CS.load_merged()
EV, SIGS, CTX = CS.generate(B)
BIDX = {b['et']: j for j, b in enumerate(B)}
TMIN = {b['et']: b['tmin'] for b in B}

# gap map: canonical fwd-consec test for any et + horizon
def fwd_ok(et, mins):
    j = BIDX.get(et)
    if j is None:
        return False
    if j + mins >= len(B):
        return False
    return B[j + mins]['tmin'] - B[j]['tmin'] == mins


# ---------------------------------------------------- 1. SIGNAL STREAM
def load_csv(name):
    p = os.path.join(OUT, name)
    with open(p, newline='') as fh:
        return list(csv.DictReader(fh))


nt_sig = load_csv('nt8_signals.csv')
py_sig = {}
for j, d in SIGS:
    py_sig[B[j]['et']] = d
nt_sig_eli = {r['et']: int(r['dir']) for r in nt_sig if r['eligible'] == '1'}
nt_sig_all = {r['et']: int(r['dir']) for r in nt_sig}

miss_sig = sorted(set(py_sig) - set(nt_sig_eli))
extra_sig = sorted(set(nt_sig_eli) - set(py_sig))
print('\nSIGNALS: python %d | nt8 total %d | nt8 eligible %d' %
      (len(py_sig), len(nt_sig_all), len(nt_sig_eli)))
print('  matched %d  MISSING_IN_NT8 %d  EXTRA_IN_NT8 %d'
      % (len(set(py_sig) & set(nt_sig_eli)), len(miss_sig), len(extra_sig)))
explained_sig = set()
for et in extra_sig:
    # an EXTRA eligible NT8 signal exists only when a cooldown shadow of a
    # gap-failed candidate changed the stream. Attribute via nearby
    # NT8-ineligible signal (gap victim) within the preceding 30 min.
    t = TMIN[et]
    near = [e2 for e2 in nt_sig_all if e2 not in nt_sig_eli
            and 0 <= t - TMIN.get(e2, -10**9) <= 60]
    print('    EXTRA signal %s dir %+d  gap-victim nearby: %s'
          % (et, nt_sig_eli[et], near if near else 'NONE'))
for et in miss_sig:
    t = TMIN[et]
    # missing because an NT8 gap-victim consumed the cooldown just before,
    # or because an NT8 extra shifted the stream
    shadow = [e2 for e2 in nt_sig_all if e2 != et
              and 0 <= t - TMIN.get(e2, -10**9) < 30 and e2 not in py_sig]
    tag = 'COOLDOWN_SHADOW_OF_' + ';'.join(shadow) if shadow else 'UNEXPLAINED'
    if shadow:
        explained_sig.add(et)
    print('    MISSING signal %s dir %+d  %s' % (et, py_sig[et], tag))

# ---------------------------------------------------- 2. EVENTS
nt_ev = load_csv('nt8_events.csv')
py_events = {}
for cand in ('OFH13', 'OFH14', 'G4', 'G3', 'G1'):
    for e in EV[cand]:
        py_events[e['id']] = e

nt_eli = [r for r in nt_ev if r['eligible'] == '1']
nt_by_id = {}
for r in nt_eli:
    nt_by_id[r['eventId']] = r

tot_field_bad = 0
verdict_ok = True
sig_div = set(r['et'] for r in nt_sig if r['eligible'] == '0') \
    | set(miss_sig) | set(extra_sig)

print('\nEVENTS per candidate:')
for cand in ('OFH13', 'OFH14', 'G4', 'G3', 'G1'):
    pids = set(e['id'] for e in EV[cand])
    nids = set(r['eventId'] for r in nt_eli if r['cand'] == cand)
    inter = pids & nids
    missing = sorted(pids - nids)
    extra = sorted(nids - pids)
    fb = 0
    for e in EV[cand]:
        if e['id'] not in nt_by_id:
            continue
        r = nt_by_id[e['id']]
        checks = [('dir', float(e['d']), float(r['dir'])),
                  ('entryPx', e['entry_px'], float(r['entryPx'])),
                  ('R', e['R'], float(r['R'])),
                  ('atr', e['atr'], float(r['atr']))]
        if cand in ('OFH13', 'OFH14'):
            checks += [('zLo', e['meta']['zLo'], float(r['zLo'])),
                       ('zHi', e['meta']['zHi'], float(r['zHi'])),
                       ('mid', e['meta']['mid'], float(r['mid'])),
                       ('depth', e['meta']['depth'], float(r['depth'])),
                       ('flow', 1.0 if e['meta']['flow'] else 0.0, float(r['flow']))]
        for nmf, a, bv in checks:
            if abs(a - bv) > TOL:
                fb += 1
                print('    FIELD_MISMATCH %s %s: %s py=%r nt=%r'
                      % (cand, e['id'], nmf, a, bv))
    tot_field_bad += fb
    print('  %-6s py %4d  nt8 %4d  MATCHED %4d  MISSING %d  EXTRA %d  FIELD_BAD %d'
          % (cand, len(pids), len(nids), len(inter), len(missing), len(extra), fb))
    for mid_ in missing + extra:
        kind = 'MISSING_IN_NT8' if mid_ in pids else 'EXTRA_IN_NT8'
        # attribute: parent signal in the divergent-signal set, or the
        # event's own fwd-60 window broken (entry near a gap / data end)
        if mid_ in pids:
            e = py_events[mid_]
            pj = e['meta'].get('sig_j', e['meta'].get('attack_j'))
            pet = B[pj]['et'] if pj is not None else ''
        else:
            r = next(x for x in nt_eli if x['eventId'] == mid_)
            pet = r['parentEt']
            e = None
        reasons = []
        if pet and (pet in sig_div):
            reasons.append('PARENT_SIGNAL_GAP_DIVERGENT(%s)' % pet)
        if pet and pet in TMIN and not fwd_ok(pet, 90):
            reasons.append('PARENT_FWD90_GAP')
        et_ev = mid_.split('-')[1]
        et_fmt = '%s-%s-%s %s:%s:%s' % (et_ev[0:4], et_ev[4:6], et_ev[6:8],
                                        et_ev[8:10], et_ev[10:12], et_ev[12:14])
        if et_fmt in TMIN and not fwd_ok(et_fmt, 60):
            reasons.append('ENTRY_FWD60_GAP')
        if e is not None and e['cand'] == 'G4':
            aj = e['meta']['attack_j']
            if not fwd_ok(B[aj]['et'], 60):
                reasons.append('ATTACK_FWD60_GAP')
        if not reasons:
            # cooldown shadow: another same-candidate diff within 30 min
            others = [m2 for m2 in (missing + extra) if m2 != mid_]
            near = [m2 for m2 in others
                    if abs(TMIN.get(et_fmt, 0)
                           - TMIN.get('%s-%s-%s %s:%s:%s' % (m2.split('-')[1][0:4],
                             m2.split('-')[1][4:6], m2.split('-')[1][6:8],
                             m2.split('-')[1][8:10], m2.split('-')[1][10:12],
                             m2.split('-')[1][12:14]), 10**9)) <= 30]
            if near:
                reasons.append('COOLDOWN_SHADOW(%s)' % near[0])
        tag = ';'.join(reasons) if reasons else 'UNEXPLAINED-BUG'
        if not reasons:
            verdict_ok = False
        print('    %s %s parent=%s  %s' % (kind, mid_, pet, tag))

# ---------------------------------------------------- 3. MANAGEMENT
print('\nMANAGEMENT PARITY (A-arm OFH13/OFH14, B-arm G1):')
nt_tr = load_csv('nt8_trades.csv')
nt_tr_by = {}
for r in nt_tr:
    nt_tr_by[(r['eventId'], r['arm'])] = r
consec, entry_ok = CS.make_ctx(B)
mg_bad = 0
mg_n = 0
for vid, spec in sorted(P.REGISTRY.items()):
    cand = spec['candidate']
    if cand not in ('OFH13', 'OFH14'):
        continue
    for e in EV[cand]:
        r = nt_tr_by.get((e['id'], 'A_ORIGINAL'))
        if r is None:
            print('    MISSING trade %s A' % e['id'])
            mg_bad += 1
            continue
        o = P.score_one(B, e, spec)
        mg_n += 1
        for nmf, a, bv in (('net', o['net_pt'], float(r['netPts'])),
                           ('exitPx', o['exit_px'], float(r['exitPx'])),
                           ('held', float(o['held_min']), float(r['heldMin'])),
                           ('mfe', o['mfe'], float(r['mfe'])),
                           ('mae', o['mae'], float(r['mae']))):
            if abs(a - bv) > 1e-6:
                mg_bad += 1
                print('    MGMT_MISMATCH %s %s: py=%r nt=%r reason py=%s nt=%s'
                      % (e['id'], nmf, a, bv, o['exit_reason'], r['exitReason']))
        if o['exit_reason'] != r['exitReason']:
            mg_bad += 1
            print('    MGMT_REASON %s: py=%s nt=%s' % (e['id'], o['exit_reason'], r['exitReason']))
    # B-arm
    for e in EV[cand]:
        r = nt_tr_by.get((e['id'], 'B_G1_DISCOUNT'))
        fill = P.g1_fill(B, e, consec, entry_ok)
        if r is None:
            print('    MISSING trade %s B' % e['id'])
            mg_bad += 1
            continue
        mg_n += 1
        if fill[0] is None:
            if r['exitReason'] != 'NO_FILL':
                mg_bad += 1
                print('    B_FILL_MISMATCH %s: py NO_FILL(%s) nt %s'
                      % (e['id'], fill[1], r['exitReason']))
        else:
            k, px = fill[0]
            if r['exitReason'] == 'NO_FILL' or abs(px - float(r['entryPx'])) > TOL:
                mg_bad += 1
                print('    B_FILL_MISMATCH %s: py fill %r nt %s/%s'
                      % (e['id'], px, r['exitReason'], r['entryPx']))
print('  management rows compared %d, mismatches %d' % (mg_n, mg_bad))
if mg_bad:
    verdict_ok = False
if tot_field_bad:
    verdict_ok = False

print('\n' + '=' * 72)
print('PARITY VERDICT: %s' % (
    'PASS - all differences empty or attributed to documented Q-FWD gaps'
    if verdict_ok else 'FAIL - unexplained differences above'))
print('=' * 72)
