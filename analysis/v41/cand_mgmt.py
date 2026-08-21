#!/usr/bin/env python3
# ======================================================================
# MANAGEMENT SUPPLEMENT - two gaps the main audit left
#   (a) G3's payoff map was built on its TIGHTEST stop (TRIG, 89.9% hit,
#       up to 44% intrabar ambiguity). That is an unfair primary. G3's
#       FROZEN R is 1.0 x ATR (discrepancy D6), so ATR1.0 is its correct
#       structural stop. Remapped here.
#   (b) No candidate showed a fixed-R plateau, so the relevant remaining
#       question is STOP + TIME EXIT with NO TARGET - risk control on a
#       drift edge rather than geometry capture.
# Declared stop family only: STRUCT / TRIG / ATR1.0 / ATR1.5. No search.
# ======================================================================

import os, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cand_spec import (load_merged, generate, make_ctx, window_of, TICK, COST,
                       HORIZON, CANDIDATES, DOLLARS_PER_POINT)

B = load_merged()
N = len(B)
consec, entry_ok = make_ctx(B)
EV, SIGS, CTX = generate(B)
WINS = ('UNSEEN', 'DEV', 'IR')
TARGETS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0]
EXITS = [20, 30, 45, 60]


def med(v):
    s = sorted(v)
    return s[len(s) // 2] if s else float('nan')


def stop_dist(e, kind):
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
    return None


def race_target(e, S, T):
    d, px = e['d'], e['entry_px']
    sp, tp = px - d * S, px + d * T
    for k in range(1, HORIZON + 1):
        c = B[e['j'] + k]
        hs = (c['low'] <= sp) if d > 0 else (c['high'] >= sp)
        ht = (c['high'] >= tp) if d > 0 else (c['low'] <= tp)
        if hs and ht:
            return -1.0, True
        if hs:
            return -1.0, False
        if ht:
            return T / S, False
    return ((B[e['j'] + HORIZON]['close'] - px) * d) / S, False


def race_time(e, S, M):
    """Stop, no target, exit at M minutes. Returns points."""
    d, px = e['d'], e['entry_px']
    sp = px - d * S
    for k in range(1, M + 1):
        c = B[e['j'] + k]
        if (d > 0 and c['low'] <= sp) or (d < 0 and c['high'] >= sp):
            return -S
    return (B[e['j'] + M]['close'] - px) * d


print('=' * 112)
print('(a) G3 REMAPPED ON ITS CORRECT STRUCTURAL STOP (ATR1.0 == frozen R, see D6)')
print('=' * 112)
print('  %-6s %-24s %-24s %-24s' % ('tgt', 'UNSEEN', 'DEV', 'IR'))
for T in TARGETS:
    row = '  %-6.2f' % T
    for w in WINS:
        evs = [e for e in EV['G3'] if e['w'] == w]
        rs = []
        amb = 0
        for e in evs:
            S = stop_dist(e, 'ATR1.0')
            r, a = race_target(e, S, T * S)
            rs.append(r - COST / S)
            amb += 1 if a else 0
        wn = sum(1 for x in rs if x > 0)
        row += ' %+7.3f %5.1f%% %5.1f%%   ' % (sum(rs) / len(rs), 100.0 * wn / len(rs),
                                               100.0 * amb / len(rs))
    print(row)

print('\n' + '=' * 112)
print('(b) STOP + TIME EXIT, NO TARGET - net pt/trade after %.2f cost' % COST)
print('=' * 112)
for c in CANDIDATES:
    print('\n  ---- %s ----' % c)
    print('   %-8s %-6s %s' % ('stop', 'win', ''.join('%10s' % ('%dm' % m) for m in EXITS)))
    for kind in ('STRUCT', 'ATR1.0', 'ATR1.5'):
        if c == 'G3' and kind == 'STRUCT':
            continue                       # identical to ATR1.0 for G3
        for w in WINS:
            evs = [e for e in EV[c] if e['w'] == w]
            if not evs:
                continue
            row = '   %-8s %-6s' % (kind, w)
            for M in EXITS:
                vals = []
                for e in evs:
                    S = stop_dist(e, kind)
                    if not S or S <= 0:
                        continue
                    vals.append(race_time(e, S, M) - COST)
                row += '%+10.2f' % (sum(vals) / len(vals))
            print(row)
        # full-history line with risk stats
        vals = []
        maxdd = 0.0
        cum = peak = 0.0
        for e in sorted(EV[c], key=lambda x: x['et']):
            S = stop_dist(e, kind)
            if not S or S <= 0:
                continue
            v = race_time(e, S, 60) - COST
            vals.append(v)
            cum += v
            peak = max(peak, cum)
            maxdd = min(maxdd, cum - peak)
        wn = sum(1 for x in vals if x > 0)
        pos = sum(x for x in vals if x > 0)
        neg = -sum(x for x in vals if x < 0)
        print('   %-8s %-6s ALL n=%d  60m mean %+0.2f  med %+0.2f  win%% %.1f  PF %.2f  '
              'maxDD %.0f pt ($%.0f)'
              % (kind, 'FULL', len(vals), sum(vals) / len(vals), med(vals),
                 100.0 * wn / len(vals), pos / neg if neg else float('inf'),
                 -maxdd, -maxdd * DOLLARS_PER_POINT))
