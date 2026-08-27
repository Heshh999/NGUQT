#!/usr/bin/env python3
# ======================================================================
# OFH13-POSTENTRY-V1  -  CHECKPOINT ELIGIBILITY, COUNTS ONLY
# ======================================================================
# The preregistration directive requires: "Report eligibility counts
# BEFORE outcomes." This script prints COUNTS AND NOTHING ELSE.
#
# NO P&L. NO MFE. NO MAE. NO WIN RATE. NO FEATURE VALUE. NO OUTCOME.
# NO FEATURE-OUTCOME RELATIONSHIP OF ANY KIND.
#
# Sample floors were fixed in the preregistration text BEFORE this
# script was run; they are not adjusted to whatever it prints.
#
# Eligibility is a CAUSAL SURVIVOR population: "given the trade is still
# open at T under the UNCHANGED frozen management, what can be known at
# T?" The frozen stop / exit are NOT altered to increase eligibility.
#
# Frozen OFH13 management (prospective.py L47): ATR1.5 stop, no target,
# 60m time exit. Open at +T  <=>  the stop was not touched in bars
# entry+1 .. entry+T.
#
# NOTHING FROZEN IS MODIFIED. SUBMITS NO ORDERS.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))

import rvmr_run as RV                                          # noqa: E402
from cand_spec import load_merged, generate, build_fvg, make_ctx  # noqa: E402

print('=' * 78)
print('OFH13-POSTENTRY-V1   CHECKPOINT ELIGIBILITY  (COUNTS ONLY)')
print('  no P&L, no MFE, no MAE, no win rate, no feature, no outcome')
print('=' * 78)

B = load_merged()
N = len(B)
consec, _ = make_ctx(B)
EV, SIGS, CTX = generate(B)
ev = EV['OFH13']
w = collections.Counter(e['w'] for e in ev)
print('\nfrozen reproduction  OFH13 %d events  UNSEEN %d / DEV %d / IR %d'
      % (len(ev), w['UNSEEN'], w['DEV'], w['IR']))
assert len(ev) == 133 and (w['UNSEEN'], w['DEV'], w['IR']) == (16, 57, 60)
print('  merged OF bars %d   %s .. %s' % (N, B[0]['et'], B[-1]['et']))

FVG_AT = build_fvg(B, consec)


def open_at(e, T):
    """Still open under the UNCHANGED frozen ATR1.5 stop at +T minutes."""
    d, px, j = e['d'], e['entry_px'], e['j']
    sp = px - d * 1.5 * e['atr']
    for k in range(1, T + 1):
        b = B[j + k]
        if (d > 0 and b['low'] <= sp) or (d < 0 and b['high'] >= sp):
            return False
    return True


# ---- RVMR grid coverage (F4 availability) --------------------------
RV.STAMP_SHIFT = 0
D = RV.load_bars()
GRID = set(D['et'])
print('  rvmr 1m grid %d bars  %s .. %s'
      % (len(D['c']), D['et'][0], D['et'][-1]))

rows = []
for e in sorted(ev, key=lambda x: x['et']):
    fv = None
    for f in FVG_AT.get(e['meta'].get('fvg_j', -1), ()):
        if f['d'] == e['d']:
            fv = f
            break
    rows.append({'et': e['et'], 'day': e['day'], 'w': e['w'],
                 'side': 'LONG' if e['d'] > 0 else 'SHORT',
                 't5': open_at(e, 5), 't15': open_at(e, 15),
                 'zone': fv is not None,
                 'rvmr': e['et'] in GRID,
                 'fwd60': (e['j'] + 60) < N})


def block(sel, label):
    n = len(sel)
    days = len(set(r['day'] for r in sel))
    lo = sum(1 for r in sel if r['side'] == 'LONG')
    sh = n - lo
    pw = collections.Counter(r['w'] for r in sel)
    print('  %-16s n %4d   days %4d   LONG %3d  SHORT %3d   '
          'UNSEEN %2d / DEV %2d / IR %2d'
          % (label, n, days, lo, sh, pw['UNSEEN'], pw['DEV'], pw['IR']))
    return n, days


print('\n' + '=' * 78)
print('CHECKPOINT ELIGIBILITY (frozen management unchanged)')
print('=' * 78)
block(rows, 'ALL PARENTS')
t5 = [r for r in rows if r['t5']]
t15 = [r for r in rows if r['t15']]
block(t5, 'T5-ELIGIBLE')
block(t15, 'T15-ELIGIBLE')
print('  %-16s n %4d' % ('stopped by +5m', len(rows) - len(t5)))
print('  %-16s n %4d' % ('stopped by +15m', len(rows) - len(t15)))

print('\nFEATURE-INPUT AVAILABILITY (counts only)')
print('  frozen FVG zone (zLo/zHi) recoverable   %3d of %d'
      % (sum(1 for r in rows if r['zone']), len(rows)))
print('  entry stamp present on the rvmr 1m grid %3d of %d   (F4 only)'
      % (sum(1 for r in rows if r['rvmr']), len(rows)))
print('  60 forward bars present                 %3d of %d'
      % (sum(1 for r in rows if r['fwd60']), len(rows)))
print('  T5-eligible AND on rvmr grid            %3d'
      % sum(1 for r in t5 if r['rvmr']))
print('  T15-eligible AND on rvmr grid           %3d'
      % sum(1 for r in t15 if r['rvmr']))

print('\nBROAD FROZEN ToD BUCKETS (OFH13 is RTH-only, >=30m after open,'
      ' >=90m to close)')
for lab, lo_, hi_ in (('RTH_AM 570-750', 570, 750), ('RTH_PM 751-960', 751, 960)):
    for nm, sel in (('T5 ', t5), ('T15', t15)):
        c = sum(1 for r in sel
                if lo_ <= int(r['et'][11:13]) * 60 + int(r['et'][14:16]) <= hi_)
        print('  %-16s %s  n %3d' % (lab, nm, c))

print('\nCOUNTS-ONLY ELIGIBILITY COMPLETE. No outcome was computed.')
