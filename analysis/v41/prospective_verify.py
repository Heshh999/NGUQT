#!/usr/bin/env python3
# ======================================================================
# PROSPECTIVE LOGGING VERIFIER - NT8 forward files vs frozen canon
# ======================================================================
# Operational verifier for the PROSPECTIVE_LOG phase. It NEVER writes the
# ledger and NEVER modifies frozen sources - it only checks. Roles:
#
#   NT8 host           records forward events causally (V41_PROSPECTIVE_*)
#   prospective.py     (frozen, untouched) scores the raw capture and owns
#                      docs/prospective_ledger.csv
#   THIS FILE          verifies the NT8 files are clean, and - when the
#                      matching raw capture CSV is available - cross-checks
#                      the NT8 rows against the canonical frozen pipeline
#                      (cand_spec.generate + prospective.score_one) exactly
#                      as every parity gate before it did.
#
# Usage:
#   python3 prospective_verify.py <V41_prospective_dir> [capture_drop_dir]
#
# Checks (any FAIL -> overall FAIL):
#   1. frozen source hashes unchanged (same check prospective.py runs)
#   2. every row is after the frozen cutoff (day > FREEZE_DATA_END)
#   3. no duplicate eventIds / (eventId, arm) pairs
#   4. stamped engine hashes match FROZEN_HASHES.txt
#   5. one engine version per file set; schema complete
#   6. resolution: one finalized row per event, no PENDING left behind
#   7. barSource provenance present (REALTIME vs HISTORICAL_LOAD reported)
#   8. [with capture] NT8 events == canonical events, nets == score_one
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, glob
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cand_spec as CS
import prospective as P

FAILS = []


def chk(name, cond, detail=''):
    print('  %-64s %s%s' % (name, 'PASS' if cond else 'FAIL',
                            ('  ' + detail if detail and not cond else '')))
    if not cond:
        FAILS.append(name)


def rd(path):
    with open(path, newline='') as fh:
        return list(csv.DictReader(fh))


def main():
    nt_dir = sys.argv[1]
    drop = sys.argv[2] if len(sys.argv) > 2 else None

    print('=' * 74)
    print('PROSPECTIVE LOGGING VERIFIER')
    print('=' * 74)

    # ---- 1. frozen hashes --------------------------------------------
    want = {}
    for line in open(P.HASH_FILE):
        if line.startswith('#') or not line.strip():
            continue
        h, n = line.split()
        want[n] = h
    cur = P.hashes()
    bad = [n for n in want if cur.get(n) != want[n]]
    chk('frozen source hashes unchanged (%d files)' % len(want), not bad, str(bad))

    # ---- load NT8 prospective files ----------------------------------
    ev, tr, rs = [], [], []
    for f in sorted(glob.glob(os.path.join(nt_dir, 'V41_PROSPECTIVE_EVENTS_*.csv'))):
        ev += rd(f)
    for f in sorted(glob.glob(os.path.join(nt_dir, 'V41_PROSPECTIVE_TRADES_*.csv'))):
        tr += rd(f)
    for f in sorted(glob.glob(os.path.join(nt_dir, 'V41_PROSPECTIVE_RESOLUTION_*.csv'))):
        rs += rd(f)
    print('\nNT8 prospective files: %d events, %d trades, %d resolution rows'
          % (len(ev), len(tr), len(rs)))
    if not ev:
        chk('prospective event rows present', False)
        finish()
        return

    # ---- 2. cutoff ----------------------------------------------------
    pre = [r for r in ev + tr + rs if r['timestampET'][:10] <= P.FREEZE_DATA_END]
    chk('all rows after frozen cutoff %s' % P.FREEZE_DATA_END, not pre,
        '%d contaminated rows' % len(pre))

    # ---- 3. duplicates -------------------------------------------------
    ce = Counter(r['eventId'] for r in ev)
    ct = Counter((r['eventId'], r['arm']) for r in tr)
    cr = Counter(r['eventId'] for r in rs)
    chk('no duplicate eventIds in events', max(ce.values()) == 1,
        str([k for k, v in ce.items() if v > 1][:5]))
    chk('no duplicate (eventId,arm) in trades', not ct or max(ct.values()) == 1,
        str([k for k, v in ct.items() if v > 1][:5]))
    chk('no duplicate eventIds in resolution', max(cr.values()) == 1,
        str([k for k, v in cr.items() if v > 1][:5]))

    # ---- 4. stamped hashes / 5. version ------------------------------
    chk('stamped cand_spec hash matches freeze',
        all(r['candSpecHash'] == want.get('cand_spec.py') for r in ev))
    chk('stamped ofh6 hash matches freeze',
        all(r['ofh6Hash'] == want.get('ofh6_spec.py') for r in ev))
    vers = set(r['engineVersion'] for r in ev + tr + rs)
    chk('single engine version across all rows', len(vers) == 1, str(sorted(vers)))
    print('    engine version: %s' % sorted(vers))

    # ---- 6. resolution completeness ----------------------------------
    eids = set(r['eventId'] for r in ev)
    rids = set(r['eventId'] for r in rs)
    chk('every event has a resolution row', eids <= rids,
        str(sorted(eids - rids)[:5]))
    pend = [r for r in rs if r['fwdEligible'] == 'PENDING']
    chk('no PENDING rows left in resolution', not pend,
        '%d pending (strategy stopped too early?)' % len(pend))
    eli = set(r['eventId'] for r in rs if r['fwdEligible'] == 'TRUE')
    inel = [r for r in rs if r['fwdEligible'] == 'FALSE']
    print('    eligibility: %d TRUE, %d FALSE' % (len(eli), len(inel)))
    for r in inel[:10]:
        print('      INELIGIBLE %s %s (Q-FWD window incomplete - gap or early stop)'
              % (r['eventId'], r['timestampET']))

    # ---- 7. provenance -------------------------------------------------
    src = Counter(r.get('barSource', '') for r in ev)
    print('    barSource: %s' % dict(src))
    chk('barSource present on every event row', '' not in src or src[''] == 0)
    hist = [r['eventId'] for r in ev if r.get('barSource') == 'HISTORICAL_LOAD']
    if hist:
        print('    NOTE: %d events were logged from HISTORICAL_LOAD bars (chart'
              ' warm-up of already-elapsed forward days) - they are cutoff-'
              'eligible but were not observed live; kept flagged, disclosed'
              % len(hist))

    # ---- trades belong to eligible OFH13/OFH14/G4 events --------------
    need_a = set(r['eventId'] for r in ev
                 if r['candidateId'] in ('OFH13', 'OFH14') and r['eventId'] in eli)
    have_a = set(r['eventId'] for r in tr if r['arm'] == 'A_ORIGINAL')
    chk('every eligible OFH13/OFH14 event has an A-arm trade', need_a <= have_a,
        str(sorted(need_a - have_a)[:5]))

    # ---- 8. canonical cross-check -------------------------------------
    if drop and glob.glob(os.path.join(drop, '*.csv')):
        print('\ncanonical cross-check (raw capture present in %s):' % drop)
        B = CS.load_merged(extra_dirs=[drop])
        EV, SIGS, CTX = CS.generate(B)
        canon = {}
        for cand in EV:
            for e in EV[cand]:
                if e['day'] > P.FREEZE_DATA_END:
                    canon[e['id']] = e
        nt_eli_ids = set(r['eventId'] for r in ev if r['eventId'] in eli)
        chk('NT8 eligible events == canonical frozen events',
            nt_eli_ids == set(canon),
            'only-NT8 %s only-canon %s' % (sorted(nt_eli_ids - set(canon))[:4],
                                           sorted(set(canon) - nt_eli_ids)[:4]))
        ev_by = dict((r['eventId'], r) for r in ev)
        fb = 0
        for eid, e in sorted(canon.items()):
            r = ev_by.get(eid)
            if r is None:
                continue
            for nm, a, b in (('dir', float(e['d']), float(r['direction'])),
                             ('entryPx', e['entry_px'], float(r['entryPrice'])),
                             ('atr', e['atr'], float(r['atr']))):
                if abs(a - b) > 1e-4:
                    fb += 1
                    print('    FIELD %s %s py=%r nt=%r' % (eid, nm, a, b))
        chk('canonical field check (dir/entryPx/atr)', fb == 0, '%d mismatches' % fb)
        tr_by = dict(((r['eventId'], r['arm']), r) for r in tr)
        mg = bad = 0
        for vid, spec in sorted(P.REGISTRY.items()):
            cand = spec['candidate']
            if cand not in ('OFH13', 'OFH14'):
                continue
            for e in EV[cand]:
                if e['day'] <= P.FREEZE_DATA_END or e['id'] not in nt_eli_ids:
                    continue
                r = tr_by.get((e['id'], 'A_ORIGINAL'))
                if r is None:
                    continue
                o = P.score_one(B, e, spec)
                mg += 1
                for nm, a, b in (('net', o['net_pt'], float(r['netPts'])),
                                 ('exitPx', o['exit_px'], float(r['exitPrice'])),
                                 ('mfe', o['mfe'], float(r['mfe'])),
                                 ('mae', o['mae'], float(r['mae']))):
                    if abs(a - b) > 1e-3:
                        bad += 1
                        print('    MGMT %s %s py=%r nt=%r' % (e['id'], nm, a, b))
        chk('canonical management check (%d A-arm trades)' % mg, bad == 0)
        print('    -> ledger append is done by the FROZEN prospective.py itself:')
        print('       python3 prospective.py     (reads the same drop dir)')
    else:
        print('\nno raw capture drop dir supplied - canonical cross-check skipped')
        print('  (upload the v4_1_orderflow monthly CSV to run it; the frozen')
        print('   prospective.py scores that capture and owns the ledger)')

    finish()


def finish():
    print('\n' + '=' * 74)
    print('PROSPECTIVE LOGGING VERIFIER: %s'
          % ('PASS' if not FAILS else 'FAIL - ' + '; '.join(FAILS)))
    print('=' * 74)


if __name__ == '__main__':
    main()
