#!/usr/bin/env python3
# ======================================================================
# V4.2-B  H-NEW1 .. H-NEW15  - shared episode extractor + studies
# ======================================================================
# Rules exactly as docs/V42B_PREREGISTRATION.md (committed first).
# All FVG-based studies read ONE episode record set, so they cannot
# disagree with each other by construction.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, pickle
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cand_spec as CS
import red_lib as R
import v42_run as V

E2_CUT = 15.9608          # frozen in the RED phase; reused, not refit
EPS = 1e-6
LIFE = 30
COOL = 30


def eff_res(B, k, d, medabs):
    """Opposing-side (against direction d) effort / result / efficiency
    / failure on bar k. All causal, bar k only."""
    b = B[k]
    atr = b['atr']
    ms = medabs[k]
    dl = b.get('delta')
    if not atr or atr <= 0 or not ms or ms <= 0 or dl is None:
        return None
    if d > 0:                       # opposing = selling
        if dl >= 0:
            return None
        effort = -dl / ms
        ticks = b.get('dnTicks')
    else:
        if dl <= 0:
            return None
        effort = dl / ms
        ticks = b.get('upTicks')
    if ticks is None:
        return None
    result = (float(ticks) * 0.25) / atr
    return {'effort': effort, 'result': result,
            'eff': result / max(effort, EPS),
            'fail': effort / max(result, EPS)}


def same_side(B, k, d, medabs):
    """WITH-direction efficiency on bar k (for the flip study)."""
    b = B[k]
    atr = b['atr']
    ms = medabs[k]
    dl = b.get('delta')
    if not atr or atr <= 0 or not ms or ms <= 0 or dl is None:
        return None
    if d > 0:
        if dl <= 0:
            return None
        effort = dl / ms
        ticks = b.get('upTicks')
    else:
        if dl >= 0:
            return None
        effort = -dl / ms
        ticks = b.get('dnTicks')
    if ticks is None:
        return None
    result = (float(ticks) * 0.25) / atr
    return {'effort': effort, 'result': result,
            'eff': result / max(effort, EPS)}


def extract(B, fvgs_at, medabs, life=LIFE):
    """One record per FVG mitigation episode that reaches a trigger."""
    out = []
    for fj in sorted(fvgs_at):
        for f in fvgs_at[fj]:
            d, zLo, zHi, mid = f['d'], f['zLo'], f['zHi'], f['mid']
            span = zHi - zLo
            if span <= 0:
                continue
            expire = B[fj]['tmin'] + life
            touched = False
            ext = None
            attacks = []
            flips = []
            press = 0
            prev = None
            touch_j = None
            touch_ext = None
            broke = False
            for k in range(fj + 1, len(B)):
                if prev is not None and B[k]['tmin'] != prev + 1:
                    break
                prev = B[k]['tmin']
                if B[k]['tmin'] > expire:
                    break
                c = B[k]
                if (d > 0 and c['close'] < zLo) or (d < 0 and c['close'] > zHi):
                    broke = True
                    break
                if not touched:
                    if (d > 0 and c['low'] <= zHi) or (d < 0 and c['high'] >= zLo):
                        touched = True
                        touch_j = k
                        ext = c['low'] if d > 0 else c['high']
                        touch_ext = ext
                    else:
                        continue
                else:
                    e = c['low'] if d > 0 else c['high']
                    if (d > 0 and e < ext) or (d < 0 and e > ext):
                        ext = e
                dl = c.get('delta')
                # attack = opposing aggression at/above Q_BD75
                if dl is not None and abs(dl) >= CS.Q_BD75 and dl * d < 0:
                    er = eff_res(B, k, d, medabs)
                    if er:
                        er['j'] = k
                        attacks.append(er)
                # with-direction aggression (for the flip)
                if dl is not None and abs(dl) >= CS.Q_BD75 and dl * d > 0:
                    ss = same_side(B, k, d, medabs)
                    if ss:
                        ss['j'] = k
                        flips.append(ss)
                # time under pressure: elevated opposing delta while the
                # adverse extreme has not extended > 0.25 ATR past first touch
                if dl is not None and dl * d < 0 and medabs[k] and \
                        abs(dl) >= medabs[k]:
                    adv = (touch_ext - ext) if d > 0 else (ext - touch_ext)
                    if adv <= 0.25 * c['atr']:
                        press += 1
                if (d > 0 and c['close'] > mid) or (d < 0 and c['close'] < mid):
                    if not R.entry_ok(B, k):
                        break
                    depth = ((zHi - ext) / span) if d > 0 else ((ext - zLo) / span)
                    far = zLo if d > 0 else zHi
                    out.append({
                        'j': k, 'd': d, 'tmin': B[k]['tmin'], 'fj': fj,
                        'touch_j': touch_j, 'zLo': zLo, 'zHi': zHi,
                        'atr': c['atr'], 'depth': depth,
                        'attacks': attacks, 'flips': flips, 'press': press,
                        'inv_atr': abs(B[k]['close'] - far) / c['atr'],
                        'imp': sum((B[x].get('delta') or 0.0)
                                   for x in (fj - 2, fj - 1, fj)),
                    })
                    break
    return out


def failed(a):
    return a['fail'] >= E2_CUT


def cool(evs):
    out, last = [], -10 ** 9
    for e in sorted(evs, key=lambda x: x['j']):
        if e['tmin'] - last < COOL:
            continue
        last = e['tmin']
        out.append(e)
    return out


def fa(recs, nmin=1):
    """records with >= nmin FAILED attacks (distinct, separated)."""
    out = []
    for r in recs:
        f = [a for a in r['attacks'] if failed(a)]
        if len(f) < nmin:
            continue
        if nmin >= 2:
            # require separation by at least one non-attack bar
            sep = any(f[i + 1]['j'] - f[i]['j'] >= 2 for i in range(len(f) - 1))
            if not sep:
                continue
        r2 = dict(r)
        r2['fails'] = f
        out.append(r2)
    return out


def speed(r):
    return r['j'] - r['fails'][-1]['j']


def bucket_speed(s):
    return 'FAST' if s <= 2 else ('MEDIUM' if s <= 5 else 'SLOW')


def bucket_depth(x):
    return 'SHALLOW' if x < 1 / 3.0 else ('MIDDLE' if x <= 2 / 3.0 else 'DEEP')


def bucket_inv(x):
    return 'NEAR' if x < 0.5 else ('MID' if x <= 1.5 else 'FAR')


def bucket_press(p):
    return '1' if p <= 1 else ('2-3' if p <= 3 else ('4-5' if p <= 5 else '6+'))


def flip_ratio(r):
    """best with-direction efficiency after the last failed attack, over
    that attack's opposing efficiency."""
    if not r.get('fails'):
        return None
    la = r['fails'][-1]
    post = [x for x in r['flips'] if x['j'] > la['j']]
    if not post:
        return None
    best = max(x['eff'] for x in post)
    return best / max(la['eff'], EPS)
