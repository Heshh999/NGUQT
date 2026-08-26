#!/usr/bin/env python3
# ======================================================================
# OFH13-MEMORY-V1  -  PER-EVENT DIAGNOSTIC LISTING
# ======================================================================
# NON-PROMOTABLE DIAGNOSTIC. Produced ON EXPLICIT USER REQUEST AFTER the
# study was closed as INSUFFICIENT FOR INTERACTION STUDY
# (docs/OFH13_MEMORY_V1_FEASIBILITY.md, commit 234f763).
#
# NO PREREGISTRATION EXISTS FOR THIS JOIN. Nothing printed here may be
# used to promote, adopt, filter, or modify anything. Joining MEMORY
# class to OFH13 outcomes IS the interaction result, so this listing
# CONSUMES the 2025-08..2026-08 OFH13 window for the interaction
# question: no future study may treat this window as unexamined for
# OFH13 x MEMORY-PRED. That cost is recorded in the feasibility doc.
#
# The ALIGNED arm holds 10 events. NOTHING inferential can be read from
# it. No p-value, CI, permutation, or gate is computed here, by design.
#
# Everything is read from frozen sources; nothing frozen is modified.
# OFH13 V1 remains byte-for-byte unchanged. SUBMITS NO ORDERS.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
#
# FROZEN OBJECTS REPRODUCED VERBATIM (not reconstructed):
#   entries/direction  cand_spec.generate()['OFH13']
#   management         prospective.py L47  ATR1.5 stop / no target / 60m
#                      = cand_mgmt.race_time(e, 1.5*atr, 60) - COST 0.87
#   FF / MFE / MAE     cand_audit.path()   (ff quirk at x=2.0 preserved:
#                      the adverse leg is capped at 1.0 ATR there)
#   MEMORY signal      RB[t] + sign(r[t]) at the entry bar close
# ======================================================================

import os
import sys
import math
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))

import rvmr_spec as RS
import rvmr_run as RV
from cand_spec import load_merged, generate, COST, HORIZON

STOP_KIND = 'ATR1.5'
TIME_EXIT = 60

print('=' * 118)
print('OFH13-MEMORY-V1   PER-EVENT DIAGNOSTIC LISTING')
print('  NON-PROMOTABLE. No preregistration exists for this join.')
print('  Study already closed INSUFFICIENT (ALIGNED n=10). No gate is scored here.')
print('  This listing CONSUMES the historical window for the interaction question.')
print('=' * 118)

# ------------------------------------------------------------- sources
B = load_merged()
N = len(B)
EV, SIGS, CTX = generate(B)
ev = EV['OFH13']
w = collections.Counter(e['w'] for e in ev)
assert len(ev) == 133 and (w['UNSEEN'], w['DEV'], w['IR']) == (16, 57, 60)
print('\nfrozen reproduction  OFH13 %d events  UNSEEN %d / DEV %d / IR %d  EXACT'
      % (len(ev), w['UNSEEN'], w['DEV'], w['IR']))

RV.STAMP_SHIFT = 0
D = RV.load_bars()
NR = len(D['c'])
c_, em, et_ = D['c'], D['em'], D['et']
rng = [D['h'][i] - D['l'][i] for i in range(NR)]
RB = [RS.bucket(x) if x is not None else None
      for x in RS.trailing_ratio(rng)]
IDX = {}
for i in range(NR):
    IDX[et_[i]] = i


# ------------------------------------------------- frozen path geometry
def path(j, d, px):
    """cand_audit.path() verbatim."""
    atr = B[j]['atr']
    mfe = mae = 0.0
    tf = ta = 0
    ff = {}
    for x in (0.5, 1.0, 1.5, 2.0):
        ff[x] = 0
    for k in range(1, HORIZON + 1):
        b = B[j + k]
        fav = (b['high'] - px) if d > 0 else (px - b['low'])
        adv = (px - b['low']) if d > 0 else (b['high'] - px)
        if fav > mfe:
            mfe, tf = fav, k
        if adv > mae:
            mae, ta = adv, k
        for x in ff:
            if ff[x]:
                continue
            hf, ha = fav >= x * atr, adv >= 1.0 * atr if x > 1.0 else adv >= x * atr
            ff[x] = 3 if (hf and ha) else (1 if hf else (2 if ha else 0))
    return {'mfe': mfe, 'mae': mae, 'tmfe': tf, 'tmae': ta, 'ff': ff}


def race_time_flag(e, S, M):
    """cand_mgmt.race_time() with an explicit stop-out flag."""
    d, px = e['d'], e['entry_px']
    sp = px - d * S
    for k in range(1, M + 1):
        b = B[e['j'] + k]
        if (d > 0 and b['low'] <= sp) or (d < 0 and b['high'] >= sp):
            return -S, True
    return (B[e['j'] + M]['close'] - px) * d, False


FFC = {0: 'neither', 1: 'FAV', 2: 'ADV', 3: 'same-bar'}

# ------------------------------------------------------------- classify
rows = []
for e in sorted(ev, key=lambda x: x['et']):
    d = e['d']
    t = IDX.get(e['et'])
    if t is None or t == 0:
        st, lastdir, cls = 'n/a', 'n/a', 'NEUTRAL-unavail'
    elif em[t] - em[t - 1] != 1 or c_[t - 1] <= 0 or c_[t] <= 0:
        st, lastdir, cls = 'n/a', 'n/a', 'NEUTRAL-unavail'
    elif RB[t] is None:
        st, lastdir, cls = 'n/a', 'n/a', 'NEUTRAL-unavail'
    else:
        st = RB[t]
        rt = math.log(c_[t] / c_[t - 1])
        if rt == 0.0:
            lastdir, cls = 'FLAT', 'NEUTRAL-zero'
        else:
            lastdir = 'UP' if rt > 0 else 'DN'
            if st == 'MEDIUM':
                cls = 'NEUTRAL-medium'
            else:
                pred = (1 if rt > 0 else -1) if st == 'HIGH' \
                    else (-1 if rt > 0 else 1)
                cls = 'ALIGNED' if pred == d else 'OPPOSED'
    S = 1.5 * e['atr']
    pnl, stopped = race_time_flag(e, S, TIME_EXIT)
    net = pnl - COST
    p = path(e['j'], d, e['entry_px'])
    rows.append({'et': e['et'], 'w': e['w'], 'side': 'LONG' if d > 0 else 'SHORT',
                 'cls': cls, 'st': st, 'last': lastdir, 'ff05': p['ff'][0.5],
                 'ff1': p['ff'][1.0], 'mfe': p['mfe'], 'mae': p['mae'],
                 'net': net, 'stopped': stopped, 'atr': e['atr'], 'S': S})

# ------------------------------------------------------------- listing
print('\n' + '=' * 118)
print('PER-EVENT LISTING  (frozen management: ATR1.5 stop, no target, 60m exit, '
      'cost %.2f pt)' % COST)
print('  FF columns: FAV = favorable threshold reached first, ADV = adverse first,')
print('              same-bar = both on one bar, neither = neither within 60m')
print('=' * 118)
print('  %-19s %-6s %-5s %-15s %-6s %-4s %-8s %-8s %7s %7s %9s %s'
      % ('entry (ET close)', 'part', 'side', 'MEMORY class', 'RVMR', 'last',
         'FF@0.5A', 'FF@1.0A', 'MFE', 'MAE', 'netPts', 'W/L'))
for r in rows:
    print('  %-19s %-6s %-5s %-15s %-6s %-4s %-8s %-8s %7.2f %7.2f %+9.2f %s%s'
          % (r['et'], r['w'], r['side'], r['cls'], r['st'], r['last'],
             FFC[r['ff05']], FFC[r['ff1']], r['mfe'], r['mae'], r['net'],
             'WIN ' if r['net'] > 0 else 'LOSS',
             ' (stopped)' if r['stopped'] else ''))

# ------------------------------------------------------ class summaries
ORDER = ('ALIGNED', 'OPPOSED', 'NEUTRAL-medium', 'NEUTRAL-unavail')


def ffpct(rs, key):
    f = sum(1 for r in rs if r[key] == 1)
    a = sum(1 for r in rs if r[key] == 2)
    return 100.0 * f / (f + a) if f + a else float('nan')


def block(rs):
    if not rs:
        return None
    n = len(rs)
    nets = [r['net'] for r in rs]
    win = [x for x in nets if x > 0]
    los = [x for x in nets if x <= 0]
    sn = sorted(nets)
    pos = sum(win)
    neg = -sum(los)
    return {'n': n, 'wr': 100.0 * len(win) / n, 'ev': sum(nets) / n,
            'med': sn[n // 2], 'tot': sum(nets),
            'pf': pos / neg if neg else float('inf'),
            'aw': sum(win) / len(win) if win else float('nan'),
            'al': sum(los) / len(los) if los else float('nan'),
            'mfe': sum(r['mfe'] for r in rs) / n,
            'mae': sum(r['mae'] for r in rs) / n,
            'ff05': ffpct(rs, 'ff05'), 'ff1': ffpct(rs, 'ff1'),
            'stop': 100.0 * sum(1 for r in rs if r['stopped']) / n,
            'days': len(set(r['et'][:10] for r in rs))}


print('\n' + '=' * 118)
print('CLASS SUMMARY  (DESCRIPTIVE ONLY - no inference, no gate, no promotion)')
print('=' * 118)
print('  %-16s %4s %5s %8s %8s %9s %6s %8s %8s %7s %7s %7s %7s %5s'
      % ('class', 'n', 'days', 'winRate', 'EV/trade', 'totalPnL', 'PF',
         'avgWin', 'avgLoss', 'medTr', 'FF0.5A', 'FF1.0A', 'avgMAE', 'stop%'))
ALLR = block(rows)
for k in ORDER + ('__ALL__',):
    rs = rows if k == '__ALL__' else [r for r in rows if r['cls'] == k]
    b = block(rs)
    if not b:
        continue
    print('  %-16s %4d %5d %7.1f%% %+8.2f %+9.1f %6.2f %+8.2f %+8.2f %+7.2f '
          '%7.1f %7.1f %7.2f %4.0f%%'
          % ('OFH13 (all)' if k == '__ALL__' else k, b['n'], b['days'], b['wr'],
             b['ev'], b['tot'], b['pf'], b['aw'], b['al'], b['med'],
             b['ff05'], b['ff1'], b['mae'], b['stop']))

print('\n  BINDING RULE - EXPECTANCY PER ORIGINAL PARENT (denominator 133)')
for k in ORDER:
    rs = [r for r in rows if r['cls'] == k]
    if rs:
        print('    %-16s retained %3d  totalPnL %+9.1f  per ORIGINAL parent %+7.2f pt'
              % (k, len(rs), sum(r['net'] for r in rs),
                 sum(r['net'] for r in rs) / 133.0))
print('    %-16s retained %3d  totalPnL %+9.1f  per ORIGINAL parent %+7.2f pt'
      % ('OFH13 (all)', 133, ALLR['tot'], ALLR['tot'] / 133.0))

print('\n  TAIL / MAJOR-WINNER RETENTION')
srt = sorted(rows, key=lambda r: -r['net'])
for lab, k in (('top 1', 1), ('top 5', 5), ('top 10', 10),
               ('top 5%% (n=%d)' % max(1, 133 // 20), max(1, 133 // 20)),
               ('top 10%% (n=%d)' % max(1, 133 // 10), max(1, 133 // 10))):
    top = srt[:k]
    cc = collections.Counter(r['cls'] for r in top)
    print('    %-16s P&L %+9.1f   ALIGNED %d  OPPOSED %d  NEUTRAL-med %d  '
          'NEUTRAL-unavail %d'
          % (lab, sum(r['net'] for r in top), cc['ALIGNED'], cc['OPPOSED'],
             cc['NEUTRAL-medium'], cc['NEUTRAL-unavail']))
tw = sum(r['net'] for r in rows if r['net'] > 0)
for k in ORDER:
    rs = [r for r in rows if r['cls'] == k and r['net'] > 0]
    print('    winner P&L in %-16s %+9.1f  = %5.1f%% of all winner P&L'
          % (k, sum(r['net'] for r in rs),
             100.0 * sum(r['net'] for r in rs) / tw if tw else float('nan')))

print('\n  LONG / SHORT SPLIT')
print('  %-16s %-6s %4s %8s %9s %9s %7s'
      % ('class', 'side', 'n', 'winRate', 'EV/trade', 'totalPnL', 'FF1.0A'))
for k in ORDER:
    for sd in ('LONG', 'SHORT'):
        rs = [r for r in rows if r['cls'] == k and r['side'] == sd]
        b = block(rs)
        if not b:
            continue
        print('  %-16s %-6s %4d %7.1f%% %+9.2f %+9.1f %7.1f'
              % (k, sd, b['n'], b['wr'], b['ev'], b['tot'], b['ff1']))

print('\n  PARTITION SPLIT (frozen OFH13 partitions; NONE is OOS for this join)')
print('  %-16s %-7s %4s %8s %9s %9s'
      % ('class', 'part', 'n', 'winRate', 'EV/trade', 'totalPnL'))
for k in ('ALIGNED', 'OPPOSED'):
    for pw in ('UNSEEN', 'DEV', 'IR'):
        rs = [r for r in rows if r['cls'] == k and r['w'] == pw]
        b = block(rs)
        if not b:
            continue
        print('  %-16s %-7s %4d %7.1f%% %+9.2f %+9.1f'
              % (k, pw, b['n'], b['wr'], b['ev'], b['tot']))

print('\n' + '=' * 118)
print('LISTING COMPLETE. DESCRIPTIVE ONLY.')
print('  ALIGNED n=10 cannot support inference. No verdict is issued and none may')
print('  be inferred. OFH13_PROSPECTIVE_V1 is unchanged and remains the only')
print('  frozen OFH13 object. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
print('=' * 118)
