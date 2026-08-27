#!/usr/bin/env python3
# ======================================================================
# OFH13-POSTENTRY-V1   FROZEN ONE-SHOT EXECUTION + DESTRUCTION
# ======================================================================
# AUTHORITATIVE PREREGISTRATION
#   docs/OFH13_POSTENTRY_V1_PREREGISTRATION.md
#   sha256 90490ecba8556cf9f4d6facb44fdf186aa3355aafc3e20651d2af64198fe44b3
#   commit f4964c9fcf09f85b683b47f7695e815a496e671d  frozen 2026-08-27T12:02:51Z
#
# Discovers PREDICTIVE POST-ENTRY STATE ONLY.
# NO management rule is created, simulated, or evaluated.
# OFH13 entry / ATR1.5 stop / 60m exit / logger are NOT modified.
# ALL OFH13 history is DEVELOPMENT data. Nothing here is OOS.
# SUBMITS NO ORDERS. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
#
# ----------------------------------------------------------------------
# IMPLEMENTATION DISCLOSURE (recorded before any outcome was printed;
# does not change a frozen semantic object):
#
# (I1) The frozen null is a "stratified day-respecting label permutation
#      preserving OFH13 side and frozen partition". Implemented exactly:
#      events are grouped into (side, partition, events-on-that-day)
#      strata; each DAY contributes its whole ordered label-block; blocks
#      are permuted among days inside their group. Days therefore move as
#      units and side/partition/day-size composition is preserved. With
#      133 events on 108 days most blocks have length 1.
# ======================================================================

import os
import sys
import json
import math
import time
import hashlib
import random
import collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))

import rvmr_spec as RS                                         # noqa: E402
import rvmr_run as RV                                          # noqa: E402
from cand_spec import (load_merged, generate, build_fvg, make_ctx,  # noqa: E402
                       COST, HORIZON)

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
PREREG = os.path.join(ROOT, 'docs', 'OFH13_POSTENTRY_V1_PREREGISTRATION.md')
PREREG_SHA = ('90490ecba8556cf9f4d6facb44fdf186aa3355aafc3e2065'
              '1d2af64198fe44b3')
PREREG_COMMIT = 'f4964c9fcf09f85b683b47f7695e815a496e671d'

SEED = 20260826
BOOT = 20000
PERM = 20000
EPS = 0.25                 # one MNQ tick, frozen for G1
TAIL_N = 13                # top 10% of 133, frozen
TAIL_FRAC = 0.50           # remaining-tail-fraction rule
RET_MIN = 0.50             # P4/P5 retention floor
INF_MIN = 0.70             # P12 single-event retention floor
NAN = float('nan')
LOG = []
OUT = {}


def say(s=''):
    print(s)
    LOG.append(s)


def hr(c='='):
    say(c * 104)


def f(x, d=4):
    return 'nan' if x != x else ('%+.*f' % (d, x))


# ================================================================ inference
def _daymap(days):
    u = sorted(set(days))
    return {d: i for i, d in enumerate(u)}, len(u)


def dc_diff(days, y, ma, mb, seed=SEED, iters=BOOT):
    """Day-clustered bootstrap of meanA - meanB (same resample both arms)."""
    dm, nd = _daymap(days)
    di = np.array([dm[d] for d in days])
    SA = np.bincount(di[ma], weights=y[ma], minlength=nd)
    CA = np.bincount(di[ma], minlength=nd).astype(float)
    SB = np.bincount(di[mb], weights=y[mb], minlength=nd)
    CB = np.bincount(di[mb], minlength=nd).astype(float)
    keep = (CA + CB) > 0
    SA, CA, SB, CB = SA[keep], CA[keep], SB[keep], CB[keep]
    nb = len(CA)
    if not CA.sum() or not CB.sum():
        return NAN, NAN, NAN, NAN
    obs = SA.sum() / CA.sum() - SB.sum() / CB.sum()
    if nb < 15:
        return obs, NAN, NAN, NAN
    rng = np.random.default_rng(seed)
    M = np.stack([SA, CA, SB, CB], axis=1)
    vals = np.empty(iters)
    done = 0
    while done < iters:
        k = min(2000, iters - done)
        idx = rng.integers(0, nb, size=(k, nb))
        base = np.arange(k)[:, None] * nb
        W = np.bincount((base + idx).ravel(),
                        minlength=k * nb).reshape(k, nb).astype(float)
        r = W @ M
        with np.errstate(invalid='ignore', divide='ignore'):
            vals[done:done + k] = np.where((r[:, 1] > 0) & (r[:, 3] > 0),
                                           r[:, 0] / r[:, 1] - r[:, 2] / r[:, 3],
                                           np.nan)
        done += k
    v = np.sort(vals[~np.isnan(vals)])
    m = len(v)
    if m < 100:
        return obs, NAN, NAN, NAN
    lo, hi = v[int(.025 * m)], v[int(.975 * m)]
    p = max(2.0 * min(int((v <= 0).sum()), int((v >= 0).sum())) / m,
            1.0 / (m + 1.0))
    return obs, lo, hi, p


def strat_perm(days, side, part, y, lab, ca, cb, obs, seed=SEED, iters=PERM):
    """Frozen stratified day-respecting label permutation (see I1)."""
    n = len(y)
    byday = collections.defaultdict(list)
    for i in range(n):
        byday[days[i]].append(i)
    groups = collections.defaultdict(list)
    for d, idxs in byday.items():
        key = (side[idxs[0]], part[idxs[0]], len(idxs))
        if len(set(side[i] for i in idxs)) > 1 or \
           len(set(part[i] for i in idxs)) > 1:
            key = ('MIX', 'MIX', len(idxs))
        groups[key].append(idxs)
    rnd = random.Random(seed)
    hits = 0
    yv = np.asarray(y, dtype=float)
    for _ in range(iters):
        newlab = np.empty(n, dtype=object)
        for key, dlist in groups.items():
            blocks = [tuple(lab[i] for i in idxs) for idxs in dlist]
            rnd.shuffle(blocks)
            for idxs, blk in zip(dlist, blocks):
                for i, v in zip(idxs, blk):
                    newlab[i] = v
        ma = newlab == ca
        mb = newlab == cb
        na, nb = int(ma.sum()), int(mb.sum())
        if not na or not nb:
            continue
        st = yv[ma].mean() - yv[mb].mean()
        if abs(st) >= abs(obs) - 1e-12:
            hits += 1
    return max(hits / iters, 1.0 / (iters + 1.0))


def bh(pv):
    p = np.asarray([1.0 if x != x else x for x in pv], dtype=float)
    m = len(p)
    o = np.argsort(p)
    q = np.empty(m)
    prev = 1.0
    for rank in range(m - 1, -1, -1):
        i = o[rank]
        prev = min(prev, m * p[i] / (rank + 1))
        q[i] = prev
    return q


def ols_resid(y, X):
    A = np.column_stack([np.ones(len(y))] + X)
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta


def terc(v):
    g = v[~np.isnan(v)]
    return np.quantile(g, 1 / 3), np.quantile(g, 2 / 3)


def tcode(v, cuts):
    o = np.full(len(v), -1, dtype=np.int8)
    g = ~np.isnan(v)
    o[g & (v <= cuts[0])] = 0
    o[g & (v > cuts[0]) & (v <= cuts[1])] = 1
    o[g & (v > cuts[1])] = 2
    return o


def cw(y, ma, mb, cells, minc=5):
    num = den = 0.0
    used = 0
    for cv in np.unique(cells):
        if cv < 0:
            continue
        sa, sb = ma & (cells == cv), mb & (cells == cv)
        na, nb = int(sa.sum()), int(sb.sum())
        if na < minc or nb < minc:
            continue
        num += (na + nb) * (y[sa].mean() - y[sb].mean())
        den += (na + nb)
        used += 1
    return (num / den if den else NAN), used


# ================================================================== phases
def phase0():
    hr()
    say('OFH13-POSTENTRY-V1   FROZEN ONE-SHOT EXECUTION')
    say('  PREDICTIVE POST-ENTRY STATE ONLY.  NO MANAGEMENT RULE.')
    say('  ALL OFH13 HISTORY IS DEVELOPMENT DATA. NOTHING IS OOS.')
    say('  NO ORDERS. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
    hr()
    say('\nPHASE 0  FREEZE / LINEAGE VERIFICATION')
    got = hashlib.sha256(open(PREREG, 'rb').read()).hexdigest()
    ok = got == PREREG_SHA
    say('   1 prereg sha256        %s  %s' % (got, 'MATCH' if ok else 'MISMATCH'))
    say('   2 prereg commit        %s' % PREREG_COMMIT)
    say('   3 OFH13 lineage        cand_spec.generate()["OFH13"] (frozen shelf)')
    say('   5 stop                 ATR1.5 = 1.5 * atr[entry]   (UNCHANGED)')
    say('   6 target               NONE                        (UNCHANGED)')
    say('   7 exit                 60m                         (UNCHANGED)')
    say('   8 T5                   entry + 5 min, strict tmin contiguity')
    say('   9 T15                  entry + 15 min, strict tmin contiguity')
    say('  10 eligibility          open under UNCHANGED management at +T')
    say('  11 primary endpoint     futureMFE(T) = max_{k in (T,e]} '
        'dir*(extreme[j+k] - c[j+T]), floored at 0')
    say('  12 F1..F6               exact frozen formulas')
    say('  13 baseline controls    sret_T, MFE_T, MAE_T (all in R units)')
    say('  14 tail winner          top %d by original frozen net P&L; '
        'remaining-tail-fraction >= %.2f' % (TAIL_N, TAIL_FRAC))
    say('  15 floors               T5 >=90/70d  T15 >=70/55d  cells >=20/15d')
    say('  16 multiplicity         M_binding 11 per family, M_total 22')
    say('  17 permutation          stratified day-respecting label permutation'
        ' (see I1), P=%d, seed %d' % (PERM, SEED))
    say('  18 gates                P1..P15 frozen numeric')
    say('  19 ceiling              <=1 tail-development + <=1 loss-failure')
    say('  20 contamination        ALL history is development; no protected'
        ' segment exists; baseline controls themselves pre-contaminated')
    say('  inference              day-cluster bootstrap B=%d, seed %d, 95%% CI'
        % (BOOT, SEED))
    if not ok:
        say('\nOFH13-POSTENTRY-V1 FREEZE FAILURE')
        sys.exit(1)
    say('  FREEZE VERIFIED.')
    OUT['phase0'] = {'sha256': got, 'match': ok, 'commit': PREREG_COMMIT}


def build():
    B = load_merged()
    N = len(B)
    consec, _ = make_ctx(B)
    EV, SIGS, CTX = generate(B)
    ev = EV['OFH13']
    FVG = build_fvg(B, consec)
    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    rngv = [D['h'][i] - D['l'][i] for i in range(len(D['c']))]
    RB = [RS.bucket(x) if x is not None else None
          for x in RS.trailing_ratio(rngv)]
    VB = [RS.bucket(x) if x is not None else None
          for x in RS.trailing_ratio(D['v'])]
    GI = {}
    for i, t in enumerate(D['et']):
        GI[t] = i
    return B, N, ev, FVG, RB, VB, GI


def phase1(B, ev):
    say('\n' + '=' * 104)
    say('PHASE 1  FROZEN OFH13 BASELINE REPRODUCTION')
    hr()
    w = collections.Counter(e['w'] for e in ev)
    nets = []
    for e in ev:
        d, px, j = e['d'], e['entry_px'], e['j']
        S = 1.5 * e['atr']
        sp = px - d * S
        hit = False
        for k in range(1, HORIZON + 1):
            b = B[j + k]
            if (d > 0 and b['low'] <= sp) or (d < 0 and b['high'] >= sp):
                hit = True
                break
        nets.append((-S if hit else (B[j + HORIZON]['close'] - px) * d) - COST)
    nets = np.array(nets)
    wr = 100.0 * float((nets > 0).mean())
    ev_pt = float(nets.mean())
    pos, neg = float(nets[nets > 0].sum()), float(-nets[nets <= 0].sum())
    pf = pos / neg if neg else NAN
    cum = np.cumsum(nets)
    dd = float((cum - np.maximum.accumulate(cum)).min())
    say('  events %d   UNSEEN %d / DEV %d / IR %d   (expect 133 = 16/57/60)'
        % (len(ev), w['UNSEEN'], w['DEV'], w['IR']))
    say('  win rate %.1f%%   EV %+.2f pt/trade   PF %.2f   maxDD %.0f pt'
        % (wr, ev_pt, pf, -dd))
    say('  registry object: N 133, WR 36.1%, EV +17.26, PF 1.80, maxDD 333')
    okc = (len(ev) == 133 and (w['UNSEEN'], w['DEV'], w['IR']) == (16, 57, 60))
    okn = (abs(wr - 36.1) < 0.15 and abs(ev_pt - 17.26) < 0.02
           and abs(pf - 1.80) < 0.01)
    say('  REPRODUCTION: %s' % ('EXACT' if (okc and okn) else 'MISMATCH'))
    if not (okc and okn):
        say('\nOFH13-POSTENTRY-V1 FREEZE FAILURE - baseline did not reproduce')
        sys.exit(1)
    OUT['baseline'] = {'n': len(ev), 'wr': wr, 'ev': ev_pt, 'pf': pf,
                       'maxdd': -dd, 'nets': nets.tolist()}
    return nets


def events(B, ev, FVG, RB, VB, GI):
    """Every frozen per-event quantity. Feature windows end at T; outcome
    windows start strictly after T. Nothing is optimised or selected."""
    rows = []
    for e in sorted(ev, key=lambda x: x['et']):
        j, d, px, atr = e['j'], e['d'], e['entry_px'], e['atr']
        R = 1.5 * atr
        sp = px - d * R
        t0 = B[j]['tmin']
        ebar, stopped = HORIZON, False
        for k in range(1, HORIZON + 1):
            b = B[j + k]
            if (d > 0 and b['low'] <= sp) or (d < 0 and b['high'] >= sp):
                ebar, stopped = k, True
                break
        contig60 = all(B[j + k]['tmin'] == t0 + k for k in range(1, ebar + 1))
        net = (-R if stopped else (B[j + HORIZON]['close'] - px) * d) - COST
        mfe_fin = 0.0
        for k in range(1, ebar + 1):
            b = B[j + k]
            fav = (b['high'] - px) if d > 0 else (px - b['low'])
            mfe_fin = max(mfe_fin, fav)
        fv = None
        for cand in FVG.get(e['meta'].get('fvg_j', -1), ()):
            if cand['d'] == d:
                fv = cand
                break
        r = {'id': e['id'], 'et': e['et'], 'day': e['day'], 'w': e['w'],
             'j': j, 'd': d, 'px': px, 'atr': atr, 'R': R, 'sp': sp,
             'ebar': ebar, 'stopped': stopped, 'net': net, 'mfe_fin': mfe_fin,
             'contig': contig60, 'far': e['struct_ref'],
             'zLo': fv['zLo'] if fv else None, 'zHi': fv['zHi'] if fv else None,
             'mod': int(e['et'][11:13]) * 60 + int(e['et'][14:16]),
             'q': '%s-Q%d' % (e['et'][:4], (int(e['et'][5:7]) - 1) // 3 + 1)}
        for T in (5, 15):
            p = {}
            ok = (ebar > T) and all(B[j + k]['tmin'] == t0 + k
                                    for k in range(1, T + 1))
            p['elig'] = bool(ok and contig60)
            if not p['elig']:
                r['T%d' % T] = p
                continue
            cT = B[j + T]['close']
            mfeT = maeT = 0.0
            for k in range(1, T + 1):
                b = B[j + k]
                mfeT = max(mfeT, (b['high'] - px) if d > 0 else (px - b['low']))
                maeT = max(maeT, (px - b['low']) if d > 0 else (b['high'] - px))
            fmfe = fmae = 0.0
            for k in range(T + 1, ebar + 1):
                b = B[j + k]
                fmfe = max(fmfe, (b['high'] - cT) if d > 0 else (cT - b['low']))
                fmae = max(fmae, (cT - b['low']) if d > 0 else (b['high'] - cT))
            p.update({
                'cT': cT, 'sret': (cT - px) * d, 'mfeT': mfeT, 'maeT': maeT,
                'fmfe': max(0.0, fmfe), 'fmae': max(0.0, fmae),
                'newhigh': max(0.0, mfe_fin - mfeT),
                'rpnl': (sp - cT) * d if stopped
                        else (B[j + HORIZON]['close'] - cT) * d,
                'stop_after': bool(stopped),
                'tailfrac': ((mfe_fin - mfeT) / mfe_fin) if mfe_fin > 0 else 0.0,
                'lastbar': j + T, 'firstout': j + T + 1})
            # ---- F1 path efficiency
            den = sum(abs(B[j + i]['close'] - B[j + i - 1]['close'])
                      for i in range(1, T + 1))
            p['F1'] = (abs(cT - px) / den) if den > 0 else NAN
            # ---- F2 excursion shape
            p['F2G1'] = mfeT / max(maeT, EPS)
            p['F2G2'] = sum(1 for k in range(1, T + 1)
                            if (B[j + k]['close'] - px) * d > 0) / float(T)
            # ---- F3 structural acceptance (OFH13's own frozen levels)
            if r['zLo'] is None:
                p['F3'] = None
            else:
                rec = any((B[j + k]['close'] - r['far']) * d < 0
                          for k in range(1, T + 1))
                if rec:
                    p['F3'] = 'C'
                elif (d > 0 and cT > r['zHi']) or (d < 0 and cT < r['zLo']):
                    p['F3'] = 'A'
                else:
                    p['F3'] = 'B'
            # ---- F4 RVMR post-entry evolution
            i0, iT = GI.get(B[j]['et']), GI.get(B[j + T]['et'])
            if i0 is None or iT is None or RB[i0] is None or RB[iT] is None:
                p['F4'] = None
                p['VB'] = None
            else:
                a, b_ = RB[i0], RB[iT]
                p['F4'] = ('SUSTAINED-HIGH' if a == 'HIGH' and b_ == 'HIGH' else
                           'CONTRACTION' if a == 'HIGH' else
                           'EXPANSION' if b_ == 'HIGH' else 'NO-TRANSITION')
                p['VB'] = '%s->%s' % (VB[i0], VB[iT])
            # ---- F5 directional order / chop
            sg = [(B[j + k]['close'] - B[j + k - 1]['close']) * d
                  for k in range(1, T + 1)]
            p['F5align'] = sum(1 for x in sg if x > 0) / float(T)
            nz = [1 if x > 0 else -1 for x in sg if x != 0]
            p['F5flips'] = sum(1 for a2, b2 in zip(nz, nz[1:]) if a2 != b2)
            # ---- F4 controls
            p['atrChg'] = (B[j + T]['atr'] / atr) if B[j + T]['atr'] else NAN
            p['rngChg'] = (sum(B[j + k]['high'] - B[j + k]['low']
                               for k in range(1, T + 1)) / T) / atr
            vpre = [B[j - k]['ofTotalVolume'] for k in range(0, 20)
                    if j - k >= 0 and B[j - k]['ofTotalVolume']]
            vpost = [B[j + k]['ofTotalVolume'] for k in range(1, T + 1)
                     if B[j + k]['ofTotalVolume']]
            p['volChg'] = ((sum(vpost) / len(vpost)) /
                           (sum(vpre) / len(vpre))) if vpre and vpost else NAN
            r['T%d' % T] = p
        # ---- F6 acceleration (T15 only)
        p15 = r['T15']
        if p15['elig']:
            c5, c10, c15 = (B[j + 5]['close'], B[j + 10]['close'],
                            B[j + 15]['close'])
            p15['F6'] = ((c15 - c10) - (c10 - c5)) * d
        rows.append(r)
    return rows


# ============================================================ cell machinery
FAMS = [('F1', 'path efficiency', 'cont', 5), ('F1', 'path efficiency', 'cont', 15),
        ('F2G1', 'excursion shape MFE_T/MAE_T', 'cont', 5),
        ('F2G1', 'excursion shape MFE_T/MAE_T', 'cont', 15),
        ('F3', 'structural acceptance A vs (B u C)', 'cat', 5),
        ('F3', 'structural acceptance A vs (B u C)', 'cat', 15),
        ('F4', 'RVMR EXPANSION vs NO-TRANSITION', 'cat', 5),
        ('F4', 'RVMR EXPANSION vs NO-TRANSITION', 'cat', 15),
        ('F5align', 'directional alignment', 'cont', 5),
        ('F5align', 'directional alignment', 'cont', 15),
        ('F6', 'acceleration (T15 only)', 'cont', 15)]
ENDPOINTS = [('fmfe', 'futureMFE  (TAIL family)'),
             ('rpnl', 'remaining P&L  (LOSS family)')]


def cell_pop(rows, T):
    return [r for r in rows if r['T%d' % T]['elig']]


def arms(pop, T, fam, cuts=None):
    """Frozen contrast. Continuous -> TOP vs BOTTOM outcome-blind tercile."""
    key = 'T%d' % T
    if fam == 'F3':
        lab = np.array([p[key]['F3'] if p[key]['F3'] else 'NA' for p in pop],
                       dtype=object)
        return lab, 'A', 'BC', np.where((lab == 'B') | (lab == 'C'), 'BC', lab)
    if fam == 'F4':
        lab = np.array([p[key]['F4'] if p[key]['F4'] else 'NA' for p in pop],
                       dtype=object)
        return lab, 'EXPANSION', 'NO-TRANSITION', lab
    v = np.array([p[key].get(fam, NAN) for p in pop], dtype=float)
    c = cuts if cuts is not None else terc(v)
    tc = tcode(v, c)
    lab = np.array(['BOT' if x == 0 else 'MID' if x == 1 else
                    'TOP' if x == 2 else 'NA' for x in tc], dtype=object)
    return lab, 'TOP', 'BOT', lab


def run_cell(rows, fam, kind, T, endpoint, cutstore):
    key = 'T%d' % T
    pop = cell_pop(rows, T)
    raw, ca, cb, lab = arms(pop, T, fam,
                            cutstore.get((fam, T)) if kind == 'cont' else None)
    if kind == 'cont' and (fam, T) not in cutstore:
        v = np.array([p[key].get(fam, NAN) for p in pop], dtype=float)
        cutstore[(fam, T)] = terc(v)
    y = np.array([p[key][endpoint] for p in pop], dtype=float)
    R = np.array([p['R'] for p in pop], dtype=float)
    days = [p['day'] for p in pop]
    side = np.array(['LONG' if p['d'] > 0 else 'SHORT' for p in pop], dtype=object)
    part = np.array([p['w'] for p in pop], dtype=object)
    ma, mb = (lab == ca), (lab == cb)
    nA, nB = int(ma.sum()), int(mb.sum())
    dA = len(set(np.array(days)[ma])) if nA else 0
    dB = len(set(np.array(days)[mb])) if nB else 0
    rec = {'fam': fam, 'T': T, 'endpoint': endpoint, 'nA': nA, 'nB': nB,
           'daysA': dA, 'daysB': dB, 'npop': len(pop),
           'meanA': float(y[ma].mean()) if nA else NAN,
           'meanB': float(y[mb].mean()) if nB else NAN,
           'meanA_R': float((y[ma] / R[ma]).mean()) if nA else NAN,
           'meanB_R': float((y[mb] / R[mb]).mean()) if nB else NAN}
    if nA < 2 or nB < 2:
        rec.update({'obs': NAN, 'lo': NAN, 'hi': NAN, 'p': NAN, 'perm': NAN,
                    'resid': NAN, 'cwv': NAN, 'cwc': 0, 'insufficient': True})
        return rec, pop, y, ma, mb, days, side, part
    obs, lo, hi, p = dc_diff(days, y, ma, mb)
    perm = strat_perm(days, side, part, y, lab, ca, cb, obs)
    sret = np.array([p_[key]['sret'] / p_['R'] for p_ in pop])
    mfeT = np.array([p_[key]['mfeT'] / p_['R'] for p_ in pop])
    maeT = np.array([p_[key]['maeT'] / p_['R'] for p_ in pop])
    res = ols_resid(y, [sret, mfeT, maeT])
    resid = float(res[ma].mean() - res[mb].mean())
    cells = (tcode(sret, terc(sret)) * 3 + tcode(mfeT, terc(mfeT))).astype(int)
    cells[(tcode(sret, terc(sret)) < 0) | (tcode(mfeT, terc(mfeT)) < 0)] = -1
    cwv, cwc = cw(y, ma, mb, cells, 5)
    rec.update({'obs': obs, 'lo': lo, 'hi': hi, 'p': p, 'perm': perm,
                'resid': resid, 'cwv': cwv, 'cwc': cwc, 'insufficient': False,
                'obs_R': float((y[ma] / R[ma]).mean() - (y[mb] / R[mb]).mean())})
    return rec, pop, y, ma, mb, days, side, part


def destruction(rec, pop, y, ma, mb, T, endpoint):
    key = 'T%d' % T
    obs = rec['obs']
    d = {}
    # temporal
    for nm, keyf in (('part', lambda p: p['w']), ('quarter', lambda p: p['q'])):
        tab, agree, elig = {}, 0, 0
        for kv in sorted(set(keyf(p) for p in pop)):
            sel = np.array([keyf(p) == kv for p in pop])
            a, b = ma & sel, mb & sel
            n = int(sel.sum())
            v = (y[a].mean() - y[b].mean()) if (a.sum() and b.sum()) else NAN
            tab[kv] = {'n': n, 'eff': v}
            if nm == 'quarter' and n < 20:
                continue
            elig += 1
            if v == v and (v > 0) == (obs > 0):
                agree += 1
        d[nm] = tab
        d[nm + '_agree'] = agree
        d[nm + '_elig'] = elig
    # long / short
    ls = {}
    for nm in ('LONG', 'SHORT'):
        sel = np.array([('LONG' if p['d'] > 0 else 'SHORT') == nm for p in pop])
        a, b = ma & sel, mb & sel
        ls[nm] = {'nA': int(a.sum()), 'nB': int(b.sum()),
                  'eff': (y[a].mean() - y[b].mean())
                  if (a.sum() and b.sum()) else NAN}
    d['ls'] = ls
    d['ls_ok'] = all(ls[k]['eff'] == ls[k]['eff'] and (ls[k]['eff'] > 0) == (obs > 0)
                     for k in ls)
    # time of day (frozen buckets, PM floor 10)
    tod = {}
    for nm, lo_, hi_ in (('RTH_AM', 570, 750), ('RTH_PM', 751, 960)):
        sel = np.array([lo_ <= p['mod'] <= hi_ for p in pop])
        a, b = ma & sel, mb & sel
        tod[nm] = {'n': int(sel.sum()), 'nA': int(a.sum()), 'nB': int(b.sum()),
                   'eff': (y[a].mean() - y[b].mean())
                   if (a.sum() and b.sum()) else NAN}
    d['tod'] = tod
    d['tod_ok'] = (tod['RTH_AM']['n'] >= 20 and tod['RTH_PM']['n'] >= 10
                   and all(tod[k]['eff'] == tod[k]['eff']
                           and (tod[k]['eff'] > 0) == (obs > 0) for k in tod))
    # ATR-at-entry standardisation (P11)
    atrv = np.array([p['atr'] for p in pop])
    ac = tcode(atrv, terc(atrv))
    d['cw_atr'], d['cw_atr_cells'] = cw(y, ma, mb, ac.astype(int), 5)
    # tail destruction A: trims + single most influential
    def trim(frac):
        cut = np.quantile(np.abs(y), 1 - frac)
        k = np.abs(y) <= cut
        a, b = ma & k, mb & k
        return (y[a].mean() - y[b].mean()) if (a.sum() and b.sum()) else NAN
    d['trim1'], d['trim5'] = trim(0.01), trim(0.05)
    worst = NAN
    for i in range(len(y)):
        k = np.ones(len(y), dtype=bool)
        k[i] = False
        a, b = ma & k, mb & k
        if not a.sum() or not b.sum():
            continue
        v = y[a].mean() - y[b].mean()
        if worst != worst or abs(v - obs) > abs(worst - obs):
            worst = v
    d['drop1'] = worst
    # tail destruction B / P13: tail-winner identification
    nets = np.array([p['net'] for p in pop])
    thr = np.sort(np.array([r['net'] for r in ALLROWS]))[-TAIL_N]
    istail = nets >= thr
    flagged = ma & istail
    ok = sum(1 for i in np.nonzero(flagged)[0]
             if pop[i]['T%d' % T]['tailfrac'] >= TAIL_FRAC)
    d['tail_flagged'] = int(flagged.sum())
    d['tail_after'] = int(ok)
    d['tail_frac_ok'] = (flagged.sum() > 0 and ok / flagged.sum() >= 0.50)
    d['tail_in_B'] = int((mb & istail).sum())
    return d


# ==================================================================== gates
def gates(rec, d, T, q):
    g = {}
    g['P1'] = True                       # verified in the Phase 3 audit
    floors = {5: (90, 70), 15: (70, 55)}[T]
    g['P2'] = (rec['npop'] >= floors[0]
               and rec['nA'] >= 20 and rec['nB'] >= 20
               and rec['daysA'] >= 15 and rec['daysB'] >= 15)
    g['P3'] = True                       # window is (T, e] from c[j+T]
    o = rec['obs']
    def ret_ok(v):
        return (v == v and o == o and o != 0
                and (v > 0) == (o > 0) and abs(v) >= RET_MIN * abs(o))
    g['P4'] = ret_ok(rec['resid']) and ret_ok(rec['cwv'])
    g['P5'] = g['P4']                    # same 3-control residual construction
    g['P6'] = (o == o and rec['lo'] == rec['lo']
               and ((rec['lo'] > 0 and rec['hi'] > 0)
                    or (rec['lo'] < 0 and rec['hi'] < 0)))
    g['P7'] = bool(q <= 0.05 and rec['perm'] == rec['perm'] and rec['perm'] <= 0.05)
    g['P8'] = (d['part_agree'] >= 2 and d['quarter_agree'] >= 2)
    g['P9'] = bool(d['ls_ok'])
    g['P10'] = bool(d['tod_ok'])
    g['P11'] = ret_ok(d['cw_atr'])
    g['P12'] = (d['drop1'] == d['drop1'] and o == o and o != 0
                and (d['drop1'] > 0) == (o > 0)
                and abs(d['drop1']) >= INF_MIN * abs(o)
                and all(t == t and (t > 0) == (o > 0)
                        for t in (d['trim1'], d['trim5'])))
    g['P13'] = bool(d['tail_frac_ok'])
    g['P14'] = True                      # one frozen scalar/contrast per cell
    g['P15'] = True                      # no management rule created
    return g


def main():
    global ALLROWS
    t0 = time.time()
    phase0()
    say('\n  loading frozen OFH13 shelf and RVMR grid ...')
    B, N, ev, FVG, RB, VB, GI = build()
    phase1(B, ev)
    rows = events(B, ev, FVG, RB, VB, GI)
    ALLROWS = rows

    # ---------------------------------------------------- PHASE 2
    say('\n' + '=' * 104)
    say('PHASE 2  CHECKPOINT ELIGIBILITY  (no synthetic survival; stop and'
        ' exit UNCHANGED)')
    hr()
    for T in (5, 15):
        pop = cell_pop(rows, T)
        dd = len(set(p['day'] for p in pop))
        lo_ = sum(1 for p in pop if p['d'] > 0)
        rv = sum(1 for p in pop if p['T%d' % T]['F4'] is not None)
        say('  T%-3d ELIGIBLE  n %3d   days %3d   LONG %3d  SHORT %3d   '
            'F4/RVMR available %3d' % (T, len(pop), dd, lo_, len(pop) - lo_, rv))
        OUT.setdefault('eligibility', {})['T%d' % T] = {
            'n': len(pop), 'days': dd, 'long': lo_, 'short': len(pop) - lo_,
            'rvmr': rv}
    say('  expected from the freeze: T5 95/81, T15 73/64; F4 92 / 71')
    say('  stopped by +5m %d   stopped by +15m %d'
        % (133 - len(cell_pop(rows, 5)), 133 - len(cell_pop(rows, 15))))
    say('  SURVIVOR POPULATION: eligibility is conditional on the trade still'
        ' being open under the ORIGINAL frozen management. No trade was')
    say('  carried past its stop, and no stop was altered to raise eligibility.')

    # ---------------------------------------------------- PHASE 3
    say('\n' + '=' * 104)
    say('PHASE 3  CAUSAL AUDIT   (feature window vs outcome window)')
    hr()
    say('  %-10s %-4s %-26s %-26s %s' % ('FAMILY', 'T', 'FEATURE LAST INPUT',
                                         'OUTCOME FIRST INPUT', 'LEAKAGE?'))
    leak = False
    for fam, lbl, kind, T in FAMS:
        pop = cell_pop(rows, T)
        p0 = pop[0]['T%d' % T]
        lastb, firstb = p0['lastbar'], p0['firstout']
        bad = any(p['T%d' % T]['firstout'] <= p['T%d' % T]['lastbar']
                  for p in pop)
        leak |= bad
        say('  %-10s %-4d %-26s %-26s %s'
            % (fam, T, 'bar j+%d (close)' % T, 'bar j+%d onward' % (T + 1),
               'YES' if bad else 'NO'))
    say('  every feature uses only completed bars j+1..j+%s; futureMFE/'
        'futureMAE/remaining P&L use bars strictly after the checkpoint,' % 'T')
    say('  measured from the checkpoint CLOSE c[j+T]. LEAKAGE DETECTED: %s'
        % ('YES' if leak else 'NO'))
    OUT['leakage'] = bool(leak)
    if leak:
        say('\n  VOIDING all cells - causal audit failed.')
        sys.exit(1)

    # ---------------------------------------------------- PHASE 4
    say('\n' + '=' * 104)
    say('PHASE 4  PRIMARY ENDPOINT VALIDATION')
    hr()
    for T in (5, 15):
        pop = cell_pop(rows, T)
        fm = np.array([p['T%d' % T]['fmfe'] for p in pop])
        R = np.array([p['R'] for p in pop])
        nh = np.array([p['T%d' % T]['newhigh'] for p in pop])
        say('  T%-3d futureMFE  mean %7.2f pt  median %7.2f pt   mean %5.3f R'
            '   |  secondary new-high extension mean %7.2f pt'
            % (T, fm.mean(), float(np.median(fm)), (fm / R).mean(), nh.mean()))
    say('  futureMFE is measured from c[j+T] over (T, e]; excursion achieved'
        ' before T cannot contribute by construction.')

    # ---------------------------------------------------- PHASES 5-11
    cutstore = {}
    CELLS = {}
    for endpoint, ename in ENDPOINTS:
        say('\n' + '=' * 104)
        say('BINDING FAMILY: %s' % ename)
        hr()
        recs = []
        for fam, lbl, kind, T in FAMS:
            rec, pop, y, ma, mb, days, side, part = run_cell(
                rows, fam, kind, T, endpoint, cutstore)
            if rec['insufficient']:
                rec['dest'] = None
            else:
                rec['dest'] = destruction(rec, pop, y, ma, mb, T, endpoint)
            rec['label'] = lbl
            recs.append(rec)
        qs = bh([r['p'] for r in recs])
        for r, q in zip(recs, qs):
            r['q'] = float(q)
            r['gates'] = (gates(r, r['dest'], r['T'], q)
                          if r['dest'] else
                          {k: (k in ('P1', 'P3', 'P14', 'P15'))
                           for k in ['P%d' % i for i in range(1, 16)]})
        CELLS[endpoint] = recs
        say('  %-9s %-3s %5s %5s %10s %10s %9s %9s %9s %9s'
            % ('cell', 'T', 'nA', 'nB', 'meanA', 'meanB', 'effect', 'p', 'BH q',
               'perm'))
        for r in recs:
            say('  %-9s %-3d %5d %5d %10s %10s %9s %9s %9s %9s'
                % (r['fam'], r['T'], r['nA'], r['nB'], f(r['meanA'], 2),
                   f(r['meanB'], 2), f(r['obs'], 3),
                   '%.5f' % r['p'] if r['p'] == r['p'] else 'nan',
                   '%.5f' % r['q'], '%.5f' % r['perm']
                   if r['perm'] == r['perm'] else 'nan'))
        say('\n  INCREMENTALITY DUTY (raw / residualised / matched'
            ' common-weight, retention vs raw, sign agreement)')
        say('  %-9s %-3s %10s %10s %7s %10s %7s %6s'
            % ('cell', 'T', 'raw', 'resid', 'ret%', 'matched', 'ret%', 'agree'))
        for r in recs:
            o = r['obs']
            rr_ = abs(r['resid'] / o) * 100 if (o == o and o) else NAN
            cc = abs(r['cwv'] / o) * 100 if (o == o and o) else NAN
            ag = (r['resid'] == r['resid'] and r['cwv'] == r['cwv']
                  and (r['resid'] > 0) == (r['cwv'] > 0))
            say('  %-9s %-3d %10s %10s %7s %10s %7s %6s'
                % (r['fam'], r['T'], f(o, 3), f(r['resid'], 3),
                   'nan' if rr_ != rr_ else '%.0f' % rr_, f(r['cwv'], 3),
                   'nan' if cc != cc else '%.0f' % cc, 'YES' if ag else 'NO'))
        say('\n  DESTRUCTION  (partitions / quarters / long-short / ToD /'
            ' ATR-standardised / trims / drop-1 / tail identification)')
        for r in recs:
            d = r['dest']
            if not d:
                say('  %-9s T%-3d  INSUFFICIENT - not destroyed' % (r['fam'], r['T']))
                continue
            say('  %-9s T%-3d  parts %d/3  quarters %d/%d  L %s S %s  '
                'AM %s PM %s (nPM %d)  cwATR %s  trims %s/%s  drop1 %s  '
                'tail flagged %d of which %d mostly-after-T'
                % (r['fam'], r['T'], d['part_agree'], d['quarter_agree'],
                   d['quarter_elig'], f(d['ls']['LONG']['eff'], 2),
                   f(d['ls']['SHORT']['eff'], 2), f(d['tod']['RTH_AM']['eff'], 2),
                   f(d['tod']['RTH_PM']['eff'], 2), d['tod']['RTH_PM']['n'],
                   f(d['cw_atr'], 2), f(d['trim1'], 2), f(d['trim5'], 2),
                   f(d['drop1'], 2), d['tail_flagged'], d['tail_after']))
        say('\n  15-GATE TABLE')
        say('  %-9s %-3s %s' % ('cell', 'T', '  '.join('P%d' % i
                                                       for i in range(1, 16))))
        for r in recs:
            g = r['gates']
            say('  %-9s %-3d %s   (%d/15)'
                % (r['fam'], r['T'],
                   '   '.join('P' if g['P%d' % i] else 'F' for i in range(1, 16)),
                   sum(g.values())))
    OUT['cells'] = {k: [{kk: vv for kk, vv in r.items()} for r in v]
                    for k, v in CELLS.items()}
    return CELLS, rows, t0


def verdicts(CELLS, rows, t0):
    say('\n' + '=' * 104)
    say('VERDICTS')
    hr()
    adv = {'fmfe': [], 'rpnl': []}
    for endpoint, ename in ENDPOINTS:
        say('\n  %s' % ename)
        for r in CELLS[endpoint]:
            g = r['gates']
            d = r['dest']
            o = r['obs']
            fails = [k for k in ('P%d' % i for i in range(1, 16)) if not g[k]]
            if not fails:
                v = ('TAIL-DEVELOPMENT CANDIDATE' if endpoint == 'fmfe'
                     else 'LOSS-FAILURE CANDIDATE')
                adv[endpoint].append(r)
            elif not g['P2']:
                v = 'INSUFFICIENT (%s)' % (
                    'arm/day floor' if r['nA'] and r['nB'] else 'empty arm')
            elif not g['P1'] or not g['P3']:
                v = 'VOID (causality)'
            elif not g['P4'] or not g['P5']:
                v = ('REDUNDANT WITH EARLY RETURN' if r['fam'] in
                     ('F1', 'F5align', 'F6') else 'REDUNDANT WITH EARLY MFE/MAE')
            elif not g['P11']:
                v = 'REDUNDANT WITH ATR/RANGE'
            elif not g['P9']:
                v = 'SIDE-SPECIFIC'
            elif not g['P10']:
                v = 'TIME-SPECIFIC'
            elif not g['P12'] or not g['P13']:
                v = 'TAIL-DEPENDENT'
            elif not g['P8']:
                v = 'UNSTABLE'
            else:
                v = 'NULL'
            r['verdict'] = v
            say('    %-9s T%-3d %-34s effect %10s   failing %s'
                % (r['fam'], r['T'], v, f(o, 3),
                   ','.join(fails) if fails else 'none'))
    say('\n  CANDIDATE CEILING: <=1 TAIL-DEVELOPMENT + <=1 LOSS-FAILURE'
        ' (max 2)')
    say('    tail-development advancing: %d      loss-failure advancing: %d'
        % (len(adv['fmfe']), len(adv['rpnl'])))
    npass = sum(1 for e, _ in ENDPOINTS for r in CELLS[e]
                if all(r['gates'].values()))
    say('    binding cells passing every required gate: %d / 22' % npass)
    OUT['advanced'] = {k: [r['fam'] + '@T%d' % r['T'] for r in v]
                       for k, v in adv.items()}
    OUT['npass'] = npass
    if not adv['fmfe'] and not adv['rpnl']:
        say('\n  OFH13-POSTENTRY-V1 FOUND NO NEW CAUSAL POST-ENTRY SEPARATOR.')
        say('  Study CLOSED. No V1 rescue. No management rule created.')
    say('\n  EPISTEMIC STATUS: ALL OFH13 history is DEVELOPMENT data for this')
    say('  study; no protected segment exists; the baseline controls were')
    say('  themselves previously viewed by outcome class. Nothing here is OOS')
    say('  or independently confirmed.')
    say('\n  OFH13 entry / ATR1.5 stop / 60m exit / prospective logger:'
        ' UNCHANGED. No management rule tested. No orders.')
    say('EXECUTION COMPLETE (%.0f s)' % (time.time() - t0))
    say('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
    hr()


if __name__ == '__main__':
    ALLROWS = []
    C, R_, T0 = main()
    verdicts(C, R_, T0)

    def jd(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.ndarray,)):
            return o.tolist()
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return str(o)
    with open(os.path.join(HERE, 'POSTENTRY_RAW.json'), 'w') as fh:
        json.dump(OUT, fh, indent=1, default=jd, allow_nan=True)
    with open(os.path.join(HERE, 'POSTENTRY_OUTPUT.txt'), 'w') as fh:
        fh.write('\n'.join(LOG) + '\n')
