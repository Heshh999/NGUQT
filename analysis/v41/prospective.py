#!/usr/bin/env python3
# ======================================================================
# PROSPECTIVE SCORER - frozen candidates on future order-flow data
# ======================================================================
# HARD RULES enforced by this file:
#  1. Only bars with day > FREEZE_DATA_END are scored prospectively.
#     Everything at or before that date is historical and SPENT.
#  2. Prospective data is NEVER used to fit, tune, select or refit
#     anything. This file has no optimiser and no free parameters.
#  3. Entry rules come from cand_spec.py unchanged. Management comes
#     from the frozen registry below. Both are hash-checked at startup;
#     if a source file changed, the run ABORTS.
#  4. Results are appended to a separate ledger CSV. Historical results
#     are never rewritten.
#
# USAGE
#   put new v4_1_orderflow_MNQ_v41of_YYYY-MM.csv files in the drop dir
#   (default <scratch>/ofprospective) and run:
#       python3 prospective.py
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, glob, hashlib, datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cand_spec as CS
from cand_spec import (load_merged, generate, make_ctx, TICK, COST, HORIZON,
                       LIFE, G1_DEPTH_ATR, DOLLARS_PER_POINT)

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = CS.SCR
DROP = os.path.join(SCR, 'ofprospective')
LEDGER = os.path.join(HERE, '..', 'docs', 'prospective_ledger.csv')

# ---------------------------------------------------------------------
# FROZEN REGISTRY - set 2026-08-21, before any prospective data existed.
# NO RULE CHANGES BASED ON PROSPECTIVE OUTCOMES.
# ---------------------------------------------------------------------
FREEZE_DATE = '2026-08-21'
FREEZE_DATA_END = '2026-08-19'          # last bar of the spent history

REGISTRY = {
    'OFH13_PROSPECTIVE_V1': {
        'candidate': 'OFH13', 'role': 'PRIMARY',
        'stop': 'ATR1.5', 'target': None, 'time_exit_min': 60,
        'rationale': 'all 36 stop x exit x partition cells positive; lowest '
                     'maxDD (333 pt) and highest win rate of its stop family; '
                     'volatility-adaptive so it does not depend on FVG geometry '
                     'being re-identified identically in future data',
    },
    'OFH14_PROSPECTIVE_V1': {
        'candidate': 'OFH14', 'role': 'SECONDARY',
        'stop': 'STRUCT', 'target': None, 'time_exit_min': 60,
        'rationale': 'thesis-aligned stop (FVG far boundary); positive in all '
                     'three partitions at all four exits, but THIN (+1.75 '
                     'pt/trade vs 992 pt maxDD) - expect noise to dominate',
    },
    'G4_PROSPECTIVE_V1': {
        'candidate': 'G4', 'role': 'SECONDARY', 'stop': None, 'target': None,
        'time_exit_min': 60,
        'rationale': 'SIGNAL-ONLY. No management version exists: G4 is negative '
                     'on the UNSEEN partition under every declared stop. Scored '
                     'unstopped for diagnosis only, NOT proposed as tradable',
    },
    'G3_PROSPECTIVE_V1': {
        'candidate': 'G3', 'role': 'SECONDARY', 'stop': None, 'target': None,
        'time_exit_min': 60,
        'rationale': 'SIGNAL-ONLY. No management version exists: G3 is negative '
                     'on the IR partition under every declared stop',
    },
}
# G1 is an EXECUTION OVERLAY, never a standalone prospective candidate.
# It is scored as a matched B-arm on OFH13/G4/OFH14 parents. Historical
# per-parent-event EV was WORSE with the overlay on all three, so the
# A-arm is primary; the B-arm is recorded to test that finding forward.
G1_OVERLAY_ARMS = ('OFH13', 'G4', 'OFH14')
G1_ADOPTED = False

# Pre-declared failure conditions (Step 14). Not auto-enforced; reported.
FAILURE_CONDITIONS = [
    'mean net expectancy persistently negative past the 50-trade checkpoint',
    'median outcome materially negative AND mean carried by <5% of trades',
    'medMFE/medMAE collapsing toward 1.00',
    'favourable-first collapsing toward 50% with negative expectancy',
    'both long and short failing simultaneously',
    'one trade producing >50% of cumulative P&L at the 50-trade checkpoint',
    'stop/target plateau disappearing (management cells flipping negative)',
    'drawdown exceeding the historical maxDD by more than 50%',
]
CHECKPOINTS = (20, 50, 100)


def file_hash(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        h.update(fh.read())
    return h.hexdigest()[:16]


FROZEN_SOURCES = ['cand_spec.py', 'ofh6_spec.py', 'ofht_spec.py', 'ofht_cache.py']


def hashes():
    return {f: file_hash(os.path.join(HERE, f)) for f in FROZEN_SOURCES}


# Recorded at freeze time by --freeze; verified on every scoring run.
HASH_FILE = os.path.join(HERE, 'FROZEN_HASHES.txt')


def stop_dist(B, e, kind):
    if kind is None:
        return None
    if kind == 'STRUCT':
        return e['R']
    if kind == 'TRIG':
        b = B[e['j']]
        ref = b['low'] if e['d'] > 0 else b['high']
        return (e['entry_px'] - (ref - TICK)) if e['d'] > 0 else ((ref + TICK) - e['entry_px'])
    if kind == 'ATR1.0':
        return 1.0 * e['atr']
    if kind == 'ATR1.5':
        return 1.5 * e['atr']
    raise ValueError(kind)


def score_one(B, e, spec, entry_px=None, entry_j=None):
    """Apply frozen management. Returns a full record."""
    j = e['j'] if entry_j is None else entry_j
    px = e['entry_px'] if entry_px is None else entry_px
    d, atr = e['d'], e['atr']
    S = stop_dist(B, e, spec['stop'])
    T = spec['target']
    M = spec['time_exit_min']
    mfe = mae = 0.0
    ffs = {0.5: 0, 1.0: 0, 2.0: 0}
    exit_reason, exit_px, held = 'TIME', None, M
    tp = px + d * T * S if (T and S) else None
    sp = px - d * S if S else None
    for k in range(1, M + 1):
        if j + k >= len(B):
            break
        c = B[j + k]
        fav = (c['high'] - px) if d > 0 else (px - c['low'])
        adv = (px - c['low']) if d > 0 else (c['high'] - px)
        mfe = max(mfe, fav)
        mae = max(mae, adv)
        if S:
            for x in ffs:
                if ffs[x]:
                    continue
                hf, ha = fav >= x * S, adv >= 1.0 * S
                ffs[x] = 3 if (hf and ha) else (1 if hf else (2 if ha else 0))
        hs = sp is not None and ((c['low'] <= sp) if d > 0 else (c['high'] >= sp))
        ht = tp is not None and ((c['high'] >= tp) if d > 0 else (c['low'] <= tp))
        if hs and ht:
            exit_reason, exit_px, held = 'AMBIGUOUS_STOP', sp, k
            break
        if hs:
            exit_reason, exit_px, held = 'STOP', sp, k
            break
        if ht:
            exit_reason, exit_px, held = 'TARGET', tp, k
            break
    if exit_px is None:
        exit_px = B[min(j + M, len(B) - 1)]['close']
    net = (exit_px - px) * d - COST
    return {'entry_px': px, 'exit_px': exit_px, 'exit_reason': exit_reason,
            'held_min': held, 'net_pt': net, 'net_usd': net * DOLLARS_PER_POINT,
            'R': (net / S) if S else None, 'stop_pt': S, 'mfe': mfe, 'mae': mae,
            'ratio': (mfe / mae) if mae else None,
            'ff05': ffs[0.5], 'ff1': ffs[1.0], 'ff2': ffs[2.0]}


def g1_fill(B, e, consec, entry_ok):
    d, atr = e['d'], e['atr']
    lim = B[e['j']]['close'] - d * G1_DEPTH_ATR * atr
    for k in range(e['j'] + 1, min(e['j'] + LIFE + 1, len(B))):
        if not consec(k, e['j']) or not entry_ok(k):
            return None, 'WINDOW_END'
        c = B[k]
        if (d > 0 and c['low'] <= lim) or (d < 0 and c['high'] >= lim):
            return (k, lim), None
    return None, 'NO_FILL_IN_30MIN'


FIELDS = ['candidate_id', 'version', 'lineage', 'arm', 'event_id', 'et', 'day',
          'month', 'iso_week', 'direction', 'entry_px', 'stop_kind', 'stop_pt',
          'target', 'time_exit_min', 'exit_px', 'exit_reason', 'held_min',
          'net_pt', 'net_usd', 'R', 'mfe', 'mae', 'ratio', 'ff05', 'ff1', 'ff2',
          'fill_assumption', 'no_fill_reason']


def main():
    if '--freeze' in sys.argv:
        with open(HASH_FILE, 'w') as fh:
            fh.write('# frozen %s\n' % FREEZE_DATE)
            for k, v in sorted(hashes().items()):
                fh.write('%s  %s\n' % (v, k))
        print('frozen hashes written to %s' % HASH_FILE)
        for k, v in sorted(hashes().items()):
            print('  %s  %s' % (v, k))
        return
    if os.path.exists(HASH_FILE):
        want = {}
        for line in open(HASH_FILE):
            if line.startswith('#') or not line.strip():
                continue
            h, n = line.split()
            want[n] = h
        cur = hashes()
        bad = [n for n in want if cur.get(n) != want[n]]
        if bad:
            print('ABORT - frozen source changed since freeze: %s' % bad)
            print('  A changed rule is a NEW VERSION and cannot inherit evidence.')
            return
        print('hash check: PASS (%d frozen sources unchanged)' % len(want))
    else:
        print('WARNING: no FROZEN_HASHES.txt - run with --freeze first')

    extra = [DROP] if os.path.isdir(DROP) and glob.glob(os.path.join(DROP, '*.csv')) else []
    if not extra:
        print('\nNo prospective data in %s' % DROP)
        print('Nothing to score. Registry is frozen and ready:')
        for vid, s in sorted(REGISTRY.items()):
            print('  %-24s %-6s %-8s stop=%-7s target=%-4s exit=%dm'
                  % (vid, s['candidate'], s['role'], str(s['stop']), str(s['target']),
                     s['time_exit_min']))
        print('  G1 overlay: adopted=%s, scored as B-arm on %s'
              % (G1_ADOPTED, ', '.join(G1_OVERLAY_ARMS)))
        return

    B = load_merged(extra_dirs=extra)
    consec, entry_ok = make_ctx(B)
    EV, SIGS, CTX = generate(B)
    rows = []
    for vid, spec in sorted(REGISTRY.items()):
        cand = spec['candidate']
        for e in EV[cand]:
            if e['day'] <= FREEZE_DATA_END:
                continue                      # historical - not prospective
            y, mo, dy = int(e['day'][:4]), int(e['day'][5:7]), int(e['day'][8:10])
            iso = datetime.date(y, mo, dy).isocalendar()
            base = {'candidate_id': cand, 'version': vid, 'lineage': cand,
                    'event_id': e['id'], 'et': e['et'], 'day': e['day'],
                    'month': e['day'][:7], 'iso_week': '%d-W%02d' % (iso[0], iso[1]),
                    'direction': e['d'], 'stop_kind': str(spec['stop']),
                    'target': str(spec['target']),
                    'time_exit_min': spec['time_exit_min']}
            r = score_one(B, e, spec)
            rec = dict(base)
            rec.update(r)
            rec['arm'] = 'A_ORIGINAL'
            rec['fill_assumption'] = 'MARKET_AT_CLOSE'
            rec['no_fill_reason'] = ''
            rows.append(rec)
            if cand in G1_OVERLAY_ARMS:
                fill, why = g1_fill(B, e, consec, entry_ok)
                rec2 = dict(base)
                rec2['arm'] = 'B_G1_DISCOUNT'
                rec2['fill_assumption'] = 'LIMIT_TOUCH_0.5ATR'
                if fill is None:
                    rec2.update({'entry_px': '', 'exit_px': '', 'exit_reason': 'NO_FILL',
                                 'held_min': '', 'net_pt': 0.0, 'net_usd': 0.0, 'R': '',
                                 'stop_pt': '', 'mfe': '', 'mae': '', 'ratio': '',
                                 'ff05': '', 'ff1': '', 'ff2': '',
                                 'no_fill_reason': why})
                else:
                    k, px = fill
                    rec2.update(score_one(B, e, spec, entry_px=px, entry_j=k))
                    rec2['no_fill_reason'] = ''
                rows.append(rec2)
    if not rows:
        print('\nProspective data present but no events after %s yet.' % FREEZE_DATA_END)
        return
    newfile = not os.path.exists(LEDGER)
    with open(LEDGER, 'a', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction='ignore')
        if newfile:
            w.writeheader()
        for r in rows:
            w.writerow(r)
    print('\nwrote %d prospective records to %s' % (len(rows), LEDGER))
    report(rows)


def report(rows):
    print('\n' + '=' * 100)
    print('PROSPECTIVE CHECKPOINT REPORT (A-arm; B-arm shown for G1 A/B only)')
    print('=' * 100)
    for vid in sorted(REGISTRY):
        a = [r for r in rows if r['version'] == vid and r['arm'] == 'A_ORIGINAL']
        if not a:
            continue
        a.sort(key=lambda r: r['et'])
        print('\n  %s   n=%d' % (vid, len(a)))
        for cp in CHECKPOINTS:
            if len(a) < cp:
                continue
            sub = a[:cp]
            nets = [r['net_pt'] for r in sub]
            mu = sum(nets) / len(nets)
            s = sorted(nets)
            wins = sum(1 for x in nets if x > 0)
            top = sorted(nets, reverse=True)[0]
            print('    @%3d trades: mean %+7.2f  median %+7.2f  win%% %4.1f  '
                  'top trade %+7.1f (%4.1f%% of total)'
                  % (cp, mu, s[len(s) // 2], 100.0 * wins / len(sub), top,
                     100.0 * top / sum(nets) if sum(nets) else float('nan')))
        b = [r for r in rows if r['version'] == vid and r['arm'] == 'B_G1_DISCOUNT']
        if b:
            filled = [r for r in b if r['exit_reason'] != 'NO_FILL']
            print('    G1 B-arm: fill %d/%d  per-parent-event EV  A %+0.2f  B %+0.2f'
                  % (len(filled), len(b),
                     sum(r['net_pt'] for r in a) / len(a),
                     sum(r['net_pt'] for r in b) / len(b)))
    print('\n  Pre-declared failure conditions under watch:')
    for f in FAILURE_CONDITIONS:
        print('    - %s' % f)


if __name__ == '__main__':
    main()
