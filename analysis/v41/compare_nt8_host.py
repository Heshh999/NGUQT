#!/usr/bin/env python3
# ======================================================================
# PYTHON <-> NT8-PLATFORM PARITY COMPARATOR (host export schema)
# ======================================================================
# compare_nt8_parity.py diffs the OFF-PLATFORM driver export (proves the
# C# LOGIC matches the frozen Python). THIS script diffs the export of a
# REAL NinjaTrader 8 HISTORICAL_PARITY run (proves the PLATFORM FEED —
# NT8's own Volumetric bars — produces the same features the research
# capture did).
#
# Two independent diffs are run:
#   A. NT8 host  vs  canonical frozen Python (cand_spec.generate)
#   B. NT8 host  vs  off-platform driver emitted stream (same engine,
#      capture data) - isolates feed differences from logic differences
#
# The host writes one row per event at EMIT time, so its fwdEligible
# column is always PENDING and parentSignalDivergent always FALSE
# (both resolve 60-90 bars later). Eligibility is therefore recomputed
# here with the engine's own rule: 60 consecutive minutes of bars must
# exist after the entry bar.
#
# Usage: python3 compare_nt8_host.py <nt8_run_dir> [driver_out_dir]
# ======================================================================

import os, sys, csv
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cand_spec as CS
import prospective as P

RUN = sys.argv[1]
DRV = sys.argv[2] if len(sys.argv) > 2 else os.path.join(CS.SCR, 'parity_out')
TOL = 1e-4          # host formats with "0.####" -> max rounding error 5e-5
MTOL = 1e-3         # managed P&L fields, same formatting

print('loading canonical Python (cand_spec)...')
B = CS.load_merged()
EV, SIGS, CTX = CS.generate(B)
BIDX = {b['et']: j for j, b in enumerate(B)}
TMIN = {b['et']: b['tmin'] for b in B}
FIRST_ET, LAST_ET = B[0]['et'], B[-1]['et']
print('canonical capture window %s .. %s (%d bars)' % (FIRST_ET, LAST_ET, len(B)))


def fwd_ok(et, mins):
    j = BIDX.get(et)
    if j is None or j + mins >= len(B):
        return False
    return B[j + mins]['tmin'] - B[j]['tmin'] == mins


def rd(path):
    with open(path, newline='') as fh:
        return list(csv.DictReader(fh))


def f(s):
    return float(s) if s not in ('', None) else float('nan')


host_ev = rd(os.path.join(RUN, 'V41_PARITY_EVENTS_MNQ.csv'))
host_tr = rd(os.path.join(RUN, 'V41_PARITY_TRADES_MNQ.csv'))
print('NT8 host export: %d event rows, %d trade rows' % (len(host_ev), len(host_tr)))

# ------------------------------------------------- window scoping
out_win = [r for r in host_ev if r['timestampET'] > LAST_ET or r['timestampET'] < FIRST_ET]
in_win = [r for r in host_ev if FIRST_ET <= r['timestampET'] <= LAST_ET]
print('  outside capture window (expected extras, NT8 loaded more data): %d' % len(out_win))
for r in out_win:
    print('     %-6s %s %s' % (r['candidateId'], r['timestampET'], r['eventId']))

# Eligibility. Engine >= 1.0.1 writes V41_PARITY_RESOLUTION_*.csv carrying
# the FINALIZED flag; prefer it. Engine 1.0 did not, so fall back to
# recomputing the engine's own rule (60 consecutive minutes after entry)
# on the canonical bars.
res_path = os.path.join(RUN, 'V41_PARITY_RESOLUTION_MNQ.csv')
RES = {}
if os.path.exists(res_path):
    for r in rd(res_path):
        RES[r['eventId']] = r
    print('  resolution file found (%d rows) - using FINALIZED eligibility' % len(RES))
else:
    print('  no resolution file (engine 1.0) - recomputing eligibility from canonical bars')

nt_eli, nt_bar_missing = [], []
for r in in_win:
    et = r['timestampET']
    if et not in BIDX:
        nt_bar_missing.append(r)          # NT8 had a bar the capture lacks
        continue
    rr = RES.get(r['eventId'])
    ok = (rr['fwdEligible'] == 'TRUE') if rr is not None else fwd_ok(et, 60)
    if ok:
        nt_eli.append(r)
print('  in-window rows %d -> eligible %d, on-bars-the-capture-lacks %d'
      % (len(in_win), len(nt_eli), len(nt_bar_missing)))
for r in nt_bar_missing:
    print('     NT8_ONLY_BAR %-6s %s' % (r['candidateId'], r['timestampET']))

nt_by_id = dict((r['eventId'], r) for r in nt_eli)

# ------------------------------------------------- A. vs canonical Python
print('\n' + '=' * 74)
print('DIFF A - NT8 PLATFORM RUN vs CANONICAL FROZEN PYTHON')
print('=' * 74)
verdict_ok = True
tot_field_bad = 0
sig_et = set(B[j]['et'] for j, d in SIGS)

for cand in ('OFH13', 'OFH14', 'G4', 'G3', 'G1'):
    pids = set(e['id'] for e in EV[cand])
    nids = set(r['eventId'] for r in nt_eli if r['candidateId'] == cand)
    missing, extra = sorted(pids - nids), sorted(nids - pids)
    fb = 0
    for e in EV[cand]:
        r = nt_by_id.get(e['id'])
        if r is None:
            continue
        checks = [('dir', float(e['d']), f(r['direction'])),
                  ('entryPx', e['entry_px'], f(r['entryPrice'])),
                  ('atr', e['atr'], f(r['atr']))]
        if cand in ('OFH13', 'OFH14'):
            checks += [('fvgHigh', e['meta']['zHi'], f(r['fvgHigh'])),
                       ('fvgLow', e['meta']['zLo'], f(r['fvgLow'])),
                       ('fvgMid', e['meta']['mid'], f(r['fvgMid'])),
                       ('depth', e['meta']['depth'], f(r['depth'])),
                       ('flow', 1.0 if e['meta']['flow'] else 0.0,
                        1.0 if r['flow'] == 'TRUE' else 0.0)]
        for nm, a, b in checks:
            if abs(a - b) > TOL:
                fb += 1
                print('    FIELD_MISMATCH %s %s %s: py=%r nt=%r' % (cand, e['id'], nm, a, b))
    tot_field_bad += fb
    print('  %-6s py %4d  nt8 %4d  MATCHED %4d  MISSING %d  EXTRA %d  FIELD_BAD %d'
          % (cand, len(pids), len(nids), len(pids & nids), len(missing), len(extra), fb))
    for mid_ in missing + extra:
        kind = 'MISSING_IN_NT8' if mid_ in pids else 'EXTRA_IN_NT8'
        raw = mid_.split('-')[1]
        et = '%s-%s-%s %s:%s:%s' % (raw[0:4], raw[4:6], raw[6:8], raw[8:10], raw[10:12], raw[12:14])
        if mid_ in pids:
            e = CS_ev = next(x for x in EV[cand] if x['id'] == mid_)
            pj = e['meta'].get('sig_j', e['meta'].get('attack_j'))
            pet = B[pj]['et'] if pj is not None else ''
        else:
            pet = nt_by_id[mid_]['parentEt']
        reasons = []
        if pet and pet in TMIN and not fwd_ok(pet, 90):
            reasons.append('PARENT_FWD90_GAP')
        if pet and pet not in TMIN:
            reasons.append('PARENT_BAR_NOT_IN_CAPTURE')
        if et in TMIN and not fwd_ok(et, 60):
            reasons.append('ENTRY_FWD60_GAP')
        if et not in TMIN:
            reasons.append('ENTRY_BAR_NOT_IN_CAPTURE')
        tag = ';'.join(reasons) if reasons else 'UNEXPLAINED-BUG'
        if not reasons:
            verdict_ok = False
        print('    %s %s parent=%s  %s' % (kind, mid_, pet, tag))

# ------------------------------------------------- management
print('\nMANAGEMENT PARITY (A-arm OFH13/OFH14 managed, B-arm G1 diagnostic):')
tr_by = dict(((r['eventId'], r['arm']), r) for r in host_tr)
consec, entry_ok = CS.make_ctx(B)
mg_n = mg_bad = 0
for vid, spec in sorted(P.REGISTRY.items()):
    cand = spec['candidate']
    if cand not in ('OFH13', 'OFH14'):
        continue
    for e in EV[cand]:
        r = tr_by.get((e['id'], 'A_ORIGINAL'))
        if r is None:
            continue                        # membership already reported above
        o = P.score_one(B, e, spec)
        mg_n += 1
        for nm, a, b in (('net', o['net_pt'], f(r['netPts'])),
                         ('exitPx', o['exit_px'], f(r['exitPrice'])),
                         ('held', float(o['held_min']), f(r['heldMin'])),
                         ('mfe', o['mfe'], f(r['mfe'])),
                         ('mae', o['mae'], f(r['mae']))):
            if abs(a - b) > MTOL:
                mg_bad += 1
                print('    MGMT_MISMATCH %s %s: py=%r nt=%r (reason py=%s nt=%s)'
                      % (e['id'], nm, a, b, o['exit_reason'], r['exitReason']))
        if o['exit_reason'] != r['exitReason']:
            mg_bad += 1
            print('    MGMT_REASON %s: py=%s nt=%s' % (e['id'], o['exit_reason'], r['exitReason']))
    for e in EV[cand]:
        r = tr_by.get((e['id'], 'B_G1_DISCOUNT'))
        if r is None:
            continue
        mg_n += 1
        fill = P.g1_fill(B, e, consec, entry_ok)
        if fill[0] is None:
            if r['exitReason'] != 'NO_FILL':
                mg_bad += 1
                print('    B_FILL_MISMATCH %s: py NO_FILL(%s) nt %s' % (e['id'], fill[1], r['exitReason']))
        else:
            k, px = fill[0]
            if r['exitReason'] == 'NO_FILL' or abs(px - f(r['entryPrice'])) > TOL:
                mg_bad += 1
                print('    B_FILL_MISMATCH %s: py fill %r nt %s/%s'
                      % (e['id'], px, r['exitReason'], r['entryPrice']))
print('  management rows compared %d, mismatches %d' % (mg_n, mg_bad))
if mg_bad or tot_field_bad:
    verdict_ok = False

# ------------------------------------------------- B. vs off-platform driver
print('\n' + '=' * 74)
print('DIFF B - NT8 PLATFORM RUN vs OFF-PLATFORM DRIVER (same engine, capture data)')
print('=' * 74)
try:
    drv = rd(os.path.join(DRV, 'nt8_events.csv'))
except IOError:
    drv = None
if drv is None:
    print('  driver export not found - skipped')
else:
    d_ids = set(r['eventId'] for r in drv)                     # emitted, any eligibility
    h_ids = set(r['eventId'] for r in in_win)
    only_d, only_h = sorted(d_ids - h_ids), sorted(h_ids - d_ids)
    print('  emitted events: driver %d  nt8(in-window) %d  shared %d'
          % (len(d_ids), len(h_ids), len(d_ids & h_ids)))
    print('  driver-only %d   nt8-only %d' % (len(only_d), len(only_h)))
    for i in only_d[:40]:
        print('     DRIVER_ONLY %s' % i)
    for i in only_h[:40]:
        print('     NT8_ONLY    %s' % i)
    d_by = dict((r['eventId'], r) for r in drv)
    feed_bad = 0
    worst = []
    for r in in_win:
        d = d_by.get(r['eventId'])
        if d is None:
            continue
        for nm, a, b in (('entryPx', f(d['entryPx']), f(r['entryPrice'])),
                         ('atr', f(d['atr']), f(r['atr']))):
            if abs(a - b) > TOL:
                feed_bad += 1
                worst.append((abs(a - b), r['eventId'], nm, a, b))
    worst.sort(reverse=True)
    print('  feature mismatches on shared events: %d' % feed_bad)
    for w in worst[:20]:
        print('     FEED_MISMATCH %s %s driver=%r nt8=%r (d=%.6f)' % (w[1], w[2], w[3], w[4], w[0]))

print('\n' + '=' * 74)
print('NT8 PLATFORM PARITY VERDICT: %s' % (
    'PASS - every difference empty or attributed to the documented Q-FWD / window effects'
    if verdict_ok else 'FAIL - unexplained differences above'))
print('=' * 74)
