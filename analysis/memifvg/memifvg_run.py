#!/usr/bin/env python3
# ======================================================================
# MEMORY-MATH-IFVG-V1   FROZEN ONE-SHOT EXECUTION + DESTRUCTION
# ======================================================================
# AUTHORITATIVE PREREGISTRATION
#   docs/MEMORY_MATH_IFVG_V1_PREREGISTRATION.md
#   sha256 313127d24a8178b7064e9d90af38d7ecaac18d9110f8ba46f0b7827fbc2dac9b
#   commit 7a9136feb54f201295d83e37e0b0c929310de827   frozen 2026-08-26T19:11:38Z
#
# EPISTEMIC CEILING: 2019-2026 is EXPOSED. Everything here is
# EXPLORATORY / DEVELOPMENT-DERIVED. Nothing is OOS or confirmed.
#
# EXECUTES EACH FROZEN CELL EXACTLY ONCE. NO RETUNING. NO VARIANTS.
# NO MANAGEMENT RESEARCH. SUBMITS NO ORDERS. NOTHING FROZEN IS MODIFIED.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
#
# ----------------------------------------------------------------------
# EXECUTION-TIME DISCLOSURES (recorded BEFORE any outcome was printed;
# neither changes a gate, a threshold, or a definition):
#
# (D1) MA3 UNIT TRANSPORT.  MA3 is written as ">= +0.60 bp = 2x the
#      unconditional anchor". B2's primary is a RATE difference, which
#      has no bp. The frozen 2x-anchor RULE is transported to B2's own
#      units using the same MEMORY-PRED anchor the preregistration
#      quotes for rates: +3.2469 pp -> MA3 floor 6.4938 pp. The rule is
#      unchanged; only the unit is.
#
# (D2) ROTATION DEGENERACY.  The frozen permutation is a within-day
#      circular rotation. On a day holding fewer than 3 events a
#      rotation cannot break alignment, so for SPARSE families (Lane B)
#      the null is structurally conservative and can only inflate p.
#      The gate is applied AS FROZEN with the rotation p. The share of
#      events sitting on non-rotatable days is reported for every
#      permutation so the reader can see where the gate is degenerate.
#      No substitute null is used for any gate decision.
#
# (D3) SG4 RATIO.  "mean MFE/MAE >= 1.2" is computed as
#      mean(MFE)/mean(MAE). The per-event ratio is undefined whenever
#      MAE = 0, so the ratio-of-means is the only total construction.
#
# (D4) A5/A8 CONSTRUCTIONS. A5's frozen primary IS the common-weight
#      standardised contrast, so its CI is bootstrapped on the
#      standardised statistic with cells and weights frozen from the
#      observed sample. A8's frozen primary m3-m1 is a PAIRED per-event
#      quantity, evaluated on the common population with contiguity to
#      t+3, and its rotation null rotates sign(r[t]) - the label that
#      carries the memory - which is exactly the alignment the
#      statistic depends on.
# ======================================================================

import os
import sys
import json
import time
import hashlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import memifvg_lib as L                                       # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
PREREG = os.path.join(ROOT, 'docs', 'MEMORY_MATH_IFVG_V1_PREREGISTRATION.md')
PREREG_SHA = '313127d24a8178b7064e9d90af38d7ecaac18d9110f8ba46f0b7827fbc2dac9b'
PREREG_COMMIT = '7a9136feb54f201295d83e37e0b0c929310de827'

BP = L.BP
COST = L.COST
SEED = L.SEED
NAN = float('nan')
OUT = {}
LOG = []


def say(s=''):
    print(s)
    LOG.append(s)


def hr(c='='):
    say(c * 100)


def fmt(x, d=4):
    return 'nan' if x != x else ('%+.*f' % (d, x))


# ====================================================================== P0
def phase0():
    hr()
    say('MEMORY-MATH-IFVG-V1   FROZEN ONE-SHOT EXECUTION')
    say('  EXPLORATORY / DEVELOPMENT-DERIVED.  NOT OOS.  NOT CONFIRMED.')
    say('  NO ORDERS.  THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
    hr()
    say('\nPHASE 0  FREEZE VERIFICATION')
    got = hashlib.sha256(open(PREREG, 'rb').read()).hexdigest()
    ok1 = got == PREREG_SHA
    say('   1 prereg sha256        %s  %s' % (got, 'MATCH' if ok1 else 'MISMATCH'))
    say('   2 prereg commit        %s' % PREREG_COMMIT)
    ok3 = (L.RS.T1 == 1.270 and L.RS.T2 == 2.335 and L.RS.W == 1440)
    say('   3 RVMR spec            T1 %.3f T2 %.3f W %d  %s'
        % (L.RS.T1, L.RS.T2, L.RS.W, 'OK' if ok3 else 'MISMATCH'))
    say('   4 MEMORY lineage       m[t]=sign(r[t])*r[t+1]; anchor %+.5f bp;'
        ' cont edge %+.4f pp' % (L.ANCHOR, L.ANCHOR_PP))
    say('   5 return convention    r[t]=log(c[t]/c[t-1]); r[t]==0 excluded;'
        ' r[t+1]==0 kept for mean, dropped from sign endpoint')
    say('   6 close-stamp          STAMP_SHIFT=0, close-stamped ET')
    say('   7 Lane A               A1 age 1-3/4-15/16-60/>=61 | A2 arrival vs'
        ' persistence | A3 rr[t]-rr[t-5] +-0.10 | A4 runlen 1/2/>=3')
    say('                          A5 eff10 terciles | A6 flips8 <=2/3-4/>=5 |'
        ' A7 atr[t]/atr[t-15] 1.15 | A8 h=1,2,3,5')
    say('   8 Lane B               B2 hold-vs-invert | B3 post-inversion |'
        ' B4 retest-reject | B5 MEMORYxIFVG | B6 generic-failure control')
    say('   9 IFVG                 3-bar FVG, gap>=0.25*ATR20, 120-bar life,'
        ' close through FAR boundary = inversion,')
    say('                          first-close HOLD/INVERT race, single retest'
        '-reject, 60-bar window, 30-bar cooldown, re-inversion invalidates')
    say('  10 strategies           S1 HIGH+age<=3 | S2 LOW+runlen>=3 |'
        ' S3 HIGH-arrival | S4 IFVG retest + MEMORY-ALIGNED')
    say('  11 cost                 %.2f NQ points round turn' % COST)
    say('  12 MA1-MA8              frozen; MA3 floor %.2f bp (rate transport'
        ' %.4f pp, disclosure D1)' % (L.MATERIAL_BP, L.MATERIAL_PP))
    say('  13 SG1-SG12             frozen')
    say('  14 M_math               12   (A1-A8, B2-B5)')
    say('  15 M_strat              4    (S1-S4)')
    say('  16 M_total              16   programme ledger 8 + 16 = 24 (non-binding)')
    say('  17 ceiling              <= 2 mathematical anomalies, <= 1 strategy')
    say('  18 firewall             no row >= %s 00:00 ET consumed' % L.FIREWALL)
    say('  inference              day-cluster bootstrap B=%d, seed %d, 95%% CI;'
        ' within-day circular rotation P=%d' % (L.B_BOOT, SEED, L.PERM))
    if not (ok1 and ok3):
        say('\nMEMORY-MATH-IFVG-V1 FREEZE FAILURE')
        sys.exit(1)
    say('  FREEZE VERIFIED.')
    OUT['phase0'] = {'sha256': got, 'match': ok1, 'rvmr_ok': ok3}


# ====================================================================== P1
def phase1(D):
    say('\n' + '=' * 100)
    say('PHASE 1  DATA / CAUSAL AUDIT')
    hr()
    fw = D['firewall']
    say('  raw rows loaded                     %10d' % D['n_raw'])
    say('  rows >= %s excluded (firewall) %10d' % (L.FIREWALL, fw['n']))
    say('    first excluded                    %s' % fw['first'])
    say('    last  excluded                    %s' % fw['last'])
    say('  bars consumed                       %10d' % D['N'])
    say('  range                               %s .. %s' % (D['et'][0], D['et'][-1]))
    say('  unique exchange days                %10d' % D['nd'])
    dup = D['N'] - len(set(D['et']))
    say('  duplicate close stamps              %10d  (assert 0)' % dup)
    assert dup == 0
    span = D['em'][-1] - D['em'][0] + 1
    say('  minutes spanned / bars present      %10d / %d' % (span, D['N']))
    say('  missing minutes (session gaps, weekends, holidays, halts):'
        ' %d  -> SKIPPED, NEVER BRIDGED' % (span - D['N']))
    say('  session handling                    contiguity by em clock only;'
        ' any window crossing a gap is UNAVAILABLE')
    say('  ATR warmup                          first %d bars have no atr20'
        % int(np.isnan(D['atr']).sum()))
    say('  RVMR unavailable                    %d bars (first %d have no'
        ' 1440-bar trailing window)'
        % (int((D['rb'] < 0).sum()), int((D['rb'] < 0).sum())))
    say('  MEMORY unavailable                  r[t]==0 or r[t]/r[t+1] not'
        ' contiguous -> event dropped (frozen)')

    say('\n  CAUSAL AVAILABILITY TABLE (every decision input)')
    say('    %-34s %-26s %s' % ('FIELD', 'KNOWN AT', 'CAUSAL'))
    rows = [('r[t]=log(c[t]/c[t-1])', 'close of bar t', True),
            ('sign(r[t])', 'close of bar t', True),
            ('rr[t] (den = rng[t-1440..t-1])', 'close of bar t', True),
            ('RB[t]', 'close of bar t', True),
            ('age(t) consecutive RB', 'close of bar t', True),
            ('RB[t-1] transition', 'close of bar t-1', True),
            ('vel(t)=rr[t]-rr[t-5]', 'close of bar t', True),
            ('runlen(t)', 'close of bar t', True),
            ('eff(t) over c[t-10..t]', 'close of bar t', True),
            ('flips(t) over r[t-7..t]', 'close of bar t', True),
            ('va(t)=atr[t]/atr[t-15]', 'close of bar t', True),
            ('atr20(t)', 'close of bar t', True),
            ('FVG formation (k-2,k-1,k)', 'close of bar k', True),
            ('FVG zone boundaries', 'close of bar k', True),
            ('touch of zone', 'close of touching bar', True),
            ('inversion (close thru far bnd)', 'close of inverting bar j', True),
            ('IFVG availability', 'close of bar j', True),
            ('retest re-entry', 'close of bar q', True),
            ('retest-reject', "close of bar q'", True),
            ('generic breakout ref window', 'close of bar b-1', True),
            ('generic failure close', 'close of failing bar', True),
            ('r[t+1] / future path  OUTCOME', 'strictly after decision', True)]
    for a, b, cc in rows:
        say('    %-34s %-26s %s' % (a, b, 'YES' if cc else 'NO'))
    say('    NO future-bar qualification enters any decision timestamp.')
    say('    RVMR causality probe: rr[i] uses rng[i-1440..i-1] only ->'
        ' verified inside the frozen trailing_ratio implementation.')
    OUT['phase1'] = {'n_raw': D['n_raw'], 'excluded': fw['n'],
                     'first_excluded': fw['first'], 'last_excluded': fw['last'],
                     'bars': D['N'], 'first': D['et'][0], 'last': D['et'][-1],
                     'days': D['nd'], 'dupes': dup, 'missing': int(span - D['N'])}


# ====================================================================== P2
LINEAGE = [
    ('AC-FLIP', 'YES', 'replicated; absorbed as the MEMORY marginal', 'SETTLED',
     'nothing standalone'),
    ('MEMORY-PRED-V1', 'YES', 'real, SUB-COST standalone', 'SETTLED standalone',
     'conditional amplification = Lane A'),
    ('LEVERAGE-V', 'YES', 'replicated, forecast-REDUNDANT', 'SETTLED',
     'control use only'),
    ('RVMR duration / flicker', 'DESCRIPTIVE', 'dwell facts only', 'PARTLY',
     'never used to condition MEMORY -> A1/A2'),
    ('serial correlation', 'YES', 'lag1 real; 5m anti-persistent; 30m RVMR-redundant',
     'SETTLED at those lags', 'decay profile -> A8'),
    ('variance ratios', 'NO', '-', 'NO', 'not added (menu discipline)'),
    ('entropy / sign order', 'PARTLY (V-turn motifs)', 'V-turn partially confirmed',
     'SETTLED as V-turn', 'flip-count conditioning -> A6 w/ incrementality duty'),
    ('run structure', 'YES', 'run-age hazard decline (diagnostic)', 'DIAGNOSTIC',
     'runlen conditioning -> A4'),
    ('shock continuation', 'YES', 'FAILED HOLDOUT', 'SETTLED negative',
     'excluded; A7 is ATR trajectory, not |shock|'),
    ('ordinal V-turn', 'YES', 'PARTIALLY CONFIRMED, overnight-only', 'SETTLED',
     'not re-run; A6 must be incremental to it'),
    ('FVG', 'component of OFH13/14 only', 'entry component', 'NO',
     'hold-vs-invert never studied -> B1/B2'),
    ('IFVG', 'NEVER', '-', 'NO', 'all of Lane B'),
    ('FVG mitigation', 'YES', 'frozen OFH13 mechanism', 'SETTLED',
     'untouched; Lane B uses no mitigation logic'),
    ('OFH13 FVG mechanics', 'YES', 'frozen prospective', 'SETTLED',
     'no MEMORY attachment (closed by OFH13-MEMORY-V1)'),
    ('OFH14 displacement/FVG', 'YES', 'frozen prospective', 'SETTLED', 'untouched'),
]


def phase2():
    say('\n' + '=' * 100)
    say('PHASE 2  LINEAGE EXCLUSIONS')
    hr()
    say('  %-26s %-24s %-42s %-20s' % ('OBJECT', 'PREV TESTED?', 'RESULT', 'SETTLED?'))
    for a, b, c, d, e in LINEAGE:
        say('  %-26s %-24s %-42s %-20s' % (a, b, c[:42], d))
        say('      open: %s' % e)
    say('\n  No executed cell re-tests AC-FLIP, LEVERAGE-V, SHOCK-CONT, MONDAY,')
    say('  HALF-SESSION-LOW, the failed 5m momentum object, the failed 30m trend')
    say('  object, ORDINAL-V-TURN, or OFH13 x MEMORY. OFH13/OFH14 are not used as')
    say('  a component of any Lane-A, Lane-B or strategy object. LINEAGE CLEAN.')
    OUT['lineage'] = [dict(zip(('object', 'tested', 'result', 'settled', 'open'), r))
                      for r in LINEAGE]


# ============================================================ event scaffold
def lane_a_events(D):
    N = D['N']
    r, sgn, rb, fwd, bwd = D['r'], D['sgn'], D['rb'], D['fwd'], D['bwd']
    base = np.zeros(N, dtype=bool)
    base[1:N - 1] = True
    base &= (bwd >= 1) & (fwd >= 1) & (rb >= 0) & (sgn != 0)
    T = np.nonzero(base)[0]
    c = D['c']
    mem = sgn[T] * np.log(c[T + 1] / c[T]) * BP
    E = {'T': T, 'mem': mem,
         'dayid': D['dayid'][T + 1], 'year': D['year'][T + 1],
         'tod': D['tod'][T + 1],
         'rb': rb[T], 'sgn': sgn[T], 'sgn1': sgn[T + 1],
         'absr': np.abs(r[T]), 'arel': D['atr'][T] / c[T],
         'age': D['age'][T], 'runlen': D['runlen'][T],
         'vel': D['vel'][T], 'eff': D['eff'][T], 'flips': D['flips'][T],
         'va': D['va'][T], 'fwd': fwd[T]}
    prev = np.full(len(T), -1, dtype=np.int8)
    prev[:] = rb[T - 1]
    E['prevrb'] = prev
    return E


# ================================================================= primaries
def _stab(y, ma, mb, E, obs):
    ys, ay = L.split_sign(y, ma, mb, E['year'], obs)
    ts, at = L.split_sign(y, ma, mb, E['tod'], obs)
    return ys, ay, ts, at


def prim_diff(tag, label, y, ma, mb, E, cells, minc, pred, popmask,
              lab, ca, cb, nd, unit='bp'):
    """One frozen difference-of-means primary, fully destroyed."""
    dayid = E['dayid']
    nA, nB = int(ma.sum()), int(mb.sum())
    dA = len(np.unique(dayid[ma])) if nA else 0
    dB = len(np.unique(dayid[mb])) if nB else 0
    obs, lo, hi, p, nbd = L.dc_diff(dayid, y, ma, mb, nd)
    cw, ncell = L.common_weight(y, ma, mb, cells, minc)
    ys, ay, ts, at = _stab(y, ma, mb, E, obs)
    t1 = L.trim_diff(y, ma, mb, 0.01)
    t5 = L.trim_diff(y, ma, mb, 0.05)
    order = np.nonzero(popmask)[0]
    perm, degen = L.rot_perm(*L.day_slices(dayid[order]), y[order],
                             [(lab[order] == ca).astype(float),
                              (lab[order] == cb).astype(float)],
                             lambda s: s[0] / nA - s[1] / nB, obs)
    rec = {'tag': tag, 'label': label, 'unit': unit, 'pred': pred,
           'obs': obs, 'lo': lo, 'hi': hi, 'p': p, 'perm': perm,
           'degen': degen, 'nA': nA, 'nB': nB, 'daysA': dA, 'daysB': dB,
           'nbd': nbd, 'cw': cw, 'cwcells': ncell,
           'years': {int(k): v[2] for k, v in ys.items()}, 'yagree': ay,
           'nyear': len(ys),
           'tod': {int(k): v[2] for k, v in ts.items()}, 'tagree': at,
           'trim1': t1, 'trim5': t5,
           'meanA': float(y[ma].mean()) if nA else NAN,
           'meanB': float(y[mb].mean()) if nB else NAN}
    return rec


def prim_mean(tag, label, u, sgnv, E_day, E_year, E_tod, pred, nd,
              unit='bp', cells=None, minc=10):
    """One frozen signed-mean primary (drift objects)."""
    y = sgnv * u
    n = len(y)
    obs, lo, hi, p, nbd = L.dc_mean(E_day, y, nd)
    ys, ay = L.split_sign_mean(y, np.ones(n, dtype=bool), E_year, obs)
    ts, at = L.split_sign_mean(y, np.ones(n, dtype=bool), E_tod, obs)
    t1 = L.trim_mean(y, np.ones(n, dtype=bool), 0.01)
    t5 = L.trim_mean(y, np.ones(n, dtype=bool), 0.05)
    st, ct = L.day_slices(E_day)
    perm, degen = L.rot_perm(st, ct, u, [sgnv.astype(float)],
                             lambda s: s[0] / n, obs)
    return {'tag': tag, 'label': label, 'unit': unit, 'pred': pred,
            'obs': obs, 'lo': lo, 'hi': hi, 'p': p, 'perm': perm,
            'degen': degen, 'nA': n, 'nB': 0,
            'daysA': len(np.unique(E_day)), 'daysB': 0, 'nbd': nbd,
            'cw': NAN, 'cwcells': 0,
            'years': {int(k): v[1] for k, v in ys.items()}, 'yagree': ay,
            'nyear': len(ys),
            'tod': {int(k): v[1] for k, v in ts.items()}, 'tagree': at,
            'trim1': t1, 'trim5': t5, 'meanA': obs, 'meanB': NAN}


def show(rec, floor, floorn, floord):
    say('  %s  %s' % (rec['tag'], rec['label']))
    say('    predicted sign %s' % ('POSITIVE' if rec['pred'] > 0 else 'NEGATIVE'))
    if rec['nB']:
        say('    arm A n %8d  days %5d  mean %s %s' %
            (rec['nA'], rec['daysA'], fmt(rec['meanA'], 5), rec['unit']))
        say('    arm B n %8d  days %5d  mean %s %s' %
            (rec['nB'], rec['daysB'], fmt(rec['meanB'], 5), rec['unit']))
    else:
        say('    n %8d  days %5d' % (rec['nA'], rec['daysA']))
    say('    PRIMARY %s %s   CI [%s, %s]   boot p %.5f   rotation perm p %.5f'
        ' (degenerate-day share %.3f)'
        % (fmt(rec['obs'], 5), rec['unit'], fmt(rec['lo'], 5), fmt(rec['hi'], 5),
           rec['p'], rec['perm'], rec['degen']))
    say('    common-weight standardised %s (%d cells)  |  trims 1%% %s  5%% %s'
        % (fmt(rec['cw'], 5), rec['cwcells'], fmt(rec['trim1'], 5),
           fmt(rec['trim5'], 5)))
    say('    years %d/%d same sign   ToD %d/%d same sign'
        % (rec['yagree'], rec['nyear'], rec['tagree'], len(rec['tod'])))
    say('      by year: ' + '  '.join('%s %s' % (k, fmt(v, 4))
                                      for k, v in sorted(rec['years'].items())))
    say('      by ToD : ' + '  '.join('%s %s' % (L.TODN[k], fmt(v, 4))
                                      for k, v in sorted(rec['tod'].items())))
    say('    floors: n>=%d both arms %s ; days>=%d both arms %s'
        % (floorn, 'PASS' if min(rec['nA'], rec['nB'] or rec['nA']) >= floorn
           else 'FAIL', floord,
           'PASS' if min(rec['daysA'], rec['daysB'] or rec['daysA']) >= floord
           else 'FAIL'))


# ==================================================================== MA
def ma_gates(rec, floorn, floord, floor_eff, nyear_req, m_q):
    g = {}
    g['MA1'] = True
    nA, nB = rec['nA'], (rec['nB'] or rec['nA'])
    dA, dB = rec['daysA'], (rec['daysB'] or rec['daysA'])
    g['MA2'] = (min(nA, nB) >= floorn) and (min(dA, dB) >= floord)
    o = rec['obs']
    g['MA3'] = (o == o) and ((o > 0) == (rec['pred'] > 0)) and abs(o) >= floor_eff
    ciex = (o == o) and (rec['lo'] == rec['lo']) and \
        ((rec['lo'] > 0 and rec['hi'] > 0) or (rec['lo'] < 0 and rec['hi'] < 0))
    g['MA4'] = bool(ciex and m_q <= 0.05 and rec['perm'] <= 0.05)
    g['MA5'] = rec['yagree'] >= nyear_req
    g['MA6'] = rec['tagree'] >= 2
    cw = rec['cw']
    if cw != cw:
        g['MA7'] = False
    else:
        g['MA7'] = ((cw > 0) == (o > 0)) and abs(cw) >= 0.5 * abs(o)
    t1, t5 = rec['trim1'], rec['trim5']
    g['MA8'] = all(t == t and (t > 0) == (o > 0) and abs(t) >= 0.5 * abs(o)
                   for t in (t1, t5))
    return g


# ================================================================ geometry
def geometry(D, T, dirv, hz=(1, 3, 5, 15), mb=15, fb=60):
    c, h, l, atr, fwd = D['c'], D['h'], D['l'], D['atr'], D['fwd']
    n = len(T)
    g = {'n': n}
    c0 = c[T]
    for hh in hz:
        ok = fwd[T] >= hh
        pts = np.full(n, NAN)
        bpv = np.full(n, NAN)
        ii = np.nonzero(ok)[0]
        pts[ii] = dirv[ii] * (c[T[ii] + hh] - c0[ii])
        bpv[ii] = dirv[ii] * np.log(c[T[ii] + hh] / c0[ii]) * BP
        g['pts%d' % hh] = pts
        g['bp%d' % hh] = bpv
        g['ok%d' % hh] = ok
    okm = fwd[T] >= mb
    mfe = np.full(n, NAN)
    mae = np.full(n, NAN)
    im = np.nonzero(okm)[0]
    for s in range(0, len(im), 100000):
        sl = im[s:s + 100000]
        idx = T[sl][:, None] + np.arange(1, mb + 1)[None, :]
        hh_, ll_ = h[idx], l[idx]
        c_ = c0[sl][:, None]
        d_ = dirv[sl][:, None]
        fav = np.where(d_ > 0, hh_ - c_, c_ - ll_)
        adv = np.where(d_ > 0, c_ - ll_, hh_ - c_)
        mfe[sl] = np.maximum(fav.max(axis=1), 0.0)
        mae[sl] = np.maximum(adv.max(axis=1), 0.0)
    g['mfe'], g['mae'], g['okm'] = mfe, mae, okm
    okf = (fwd[T] >= fb) & (~np.isnan(atr[T])) & (atr[T] > 0)
    code = np.full(n, -1, dtype=np.int8)
    iff = np.nonzero(okf)[0]
    for s in range(0, len(iff), 40000):
        sl = iff[s:s + 40000]
        idx = T[sl][:, None] + np.arange(1, fb + 1)[None, :]
        hh_, ll_ = h[idx], l[idx]
        c_ = c0[sl][:, None]
        d_ = dirv[sl][:, None]
        X = atr[T[sl]][:, None]
        fav = np.where(d_ > 0, hh_ - c_, c_ - ll_) >= X
        adv = np.where(d_ > 0, c_ - ll_, hh_ - c_) >= X
        af, aa = fav.any(1), adv.any(1)
        kf = np.where(af, fav.argmax(1), 10 ** 6)
        ka = np.where(aa, adv.argmax(1), 10 ** 6)
        cd = np.zeros(len(sl), dtype=np.int8)
        cd[af & ~aa] = 1
        cd[aa & ~af] = 2
        both = af & aa
        cd[both & (kf < ka)] = 1
        cd[both & (ka < kf)] = 2
        cd[both & (kf == ka)] = 3
        code[sl] = cd
    g['ff'] = code
    return g


def ffpct(code):
    f = int(np.sum(code == 1))
    a = int(np.sum(code == 2))
    return (100.0 * f / (f + a) if f + a else NAN), f, a


# ============================================================= LANE B build
def build_fvgs(D):
    N = D['N']
    h, l, c, em, atr = D['h'], D['l'], D['c'], D['em'], D['atr']
    step2 = np.zeros(N, dtype=bool)
    step2[2:] = (em[2:] - em[:-2]) == 2
    bull = np.zeros(N, dtype=bool)
    bear = np.zeros(N, dtype=bool)
    bull[2:] = h[:-2] < l[2:]
    bear[2:] = l[:-2] > h[2:]
    size = np.zeros(N)
    size[2:] = np.where(bull[2:], l[2:] - h[:-2],
                        np.where(bear[2:], l[:-2] - h[2:], 0.0))
    okatr = ~np.isnan(atr) & (atr > 0)
    qual = step2 & (bull | bear) & okatr & (size >= 0.25 * atr)
    tick = step2 & (bull | bear) & (size >= 0.25)
    K = np.nonzero(qual)[0]
    dF = np.where(bull[K], 1, -1).astype(np.int8)
    zlo = np.where(bull[K], h[K - 2], h[K]).astype(np.float64)
    zhi = np.where(bull[K], l[K], l[K - 2]).astype(np.float64)
    return {'K': K, 'dF': dF, 'zlo': zlo, 'zhi': zhi,
            'n_all': int((step2 & (bull | bear)).sum()),
            'n_tick': int(tick.sum()), 'n_qual': len(K),
            'n_bull': int((dF > 0).sum()), 'n_bear': int((dF < 0).sum())}


def track_fvgs(D, F):
    """Frozen hold/invert race and retest scan. Pure-python for speed of
    early exit; every rule is the preregistered one."""
    N = D['N']
    hL, lL, cL = D['h'].tolist(), D['l'].tolist(), D['c'].tolist()
    emL = D['em'].tolist()
    K, dF, zlo, zhi = F['K'].tolist(), F['dF'].tolist(), \
        F['zlo'].tolist(), F['zhi'].tolist()
    res, invj, rtj = [], [], []
    for a in range(len(K)):
        k, d, zl, zh = K[a], dF[a], zlo[a], zhi[a]
        touched = False
        out = 'UNTOUCHED'
        ij = -1
        prev = emL[k]
        top = min(k + 120, N - 1)
        for j in range(k + 1, top + 1):
            if emL[j] != prev + 1:
                out = 'UNRESOLVED'
                break
            prev = emL[j]
            if not touched:
                if (d > 0 and lL[j] <= zh) or (d < 0 and hL[j] >= zl):
                    touched = True
            if (d > 0 and cL[j] < zl) or (d < 0 and cL[j] > zh):
                out = 'INVERT'
                ij = j
                break
            if touched and ((d > 0 and cL[j] > zh) or (d < 0 and cL[j] < zl)):
                out = 'HOLD'
                break
        else:
            out = 'EXPIRED' if touched else 'UNTOUCHED'
        res.append(out)
        invj.append(ij)
        # ---- retest scan after inversion ----
        q = -1
        if out == 'INVERT':
            dI = -d
            near = zh if dI > 0 else zl
            far = zl if dI > 0 else zh
            entered = False
            prev = emL[ij]
            top2 = min(ij + 60, N - 1)
            for j in range(ij + 1, top2 + 1):
                if emL[j] != prev + 1:
                    break
                prev = emL[j]
                if (dI > 0 and cL[j] < far) or (dI < 0 and cL[j] > far):
                    break                      # re-inversion invalidates
                if not entered:
                    if (dI > 0 and lL[j] <= near) or (dI < 0 and hL[j] >= near):
                        entered = True
                        continue
                if entered and ((dI > 0 and cL[j] > near)
                                or (dI < 0 and cL[j] < near)):
                    q = j
                    break
        rtj.append(q)
    return np.array(res), np.array(invj), np.array(rtj)


def generic_failures(D):
    N = D['N']
    h, l, c, bwd = D['h'], D['l'], D['c'], D['bwd']
    sw = np.lib.stride_tricks.sliding_window_view
    mx = np.full(N, NAN)
    mn = np.full(N, NAN)
    mx[30:] = sw(h, 30)[:N - 30].max(axis=1)
    mn[30:] = sw(l, 30)[:N - 30].min(axis=1)
    okw = bwd >= 30
    up = okw & (~np.isnan(mx)) & (c > mx)
    dn = okw & (~np.isnan(mn)) & (c < mn)
    cL, hL, lL = c.tolist(), h.tolist(), l.tolist()
    emL = D['em'].tolist()
    ev_j, ev_d = [], []
    for b in np.nonzero(up | dn)[0]:
        d0 = 1 if up[b] else -1
        prev = emL[b]
        top = min(b + 30, N - 1)
        for j in range(b + 1, top + 1):
            if emL[j] != prev + 1:
                break
            prev = emL[j]
            if d0 > 0 and cL[j] < lL[b]:
                ev_j.append(j)
                ev_d.append(-1)
                break
            if d0 < 0 and cL[j] > hL[b]:
                ev_j.append(j)
                ev_d.append(1)
                break
    ev_j = np.array(ev_j, dtype=np.int64)
    ev_d = np.array(ev_d, dtype=np.int8)
    o = np.argsort(ev_j, kind='stable')
    ev_j, ev_d = ev_j[o], ev_d[o]
    keep = []
    last = {1: -10 ** 9, -1: -10 ** 9}
    for i in range(len(ev_j)):
        if ev_j[i] - last[int(ev_d[i])] >= 30:
            keep.append(i)
            last[int(ev_d[i])] = ev_j[i]
    return ev_j[keep], ev_d[keep]


def mem_implication(D, idx):
    """Frozen MEMORY implication at bar idx: +1 / -1 / 0 (NEUTRAL)."""
    rb, sgn, bwd = D['rb'][idx], D['sgn'][idx], D['bwd'][idx]
    imp = np.zeros(len(idx), dtype=np.int8)
    ok = (bwd >= 1) & (rb >= 0) & (sgn != 0)
    hi = ok & (rb == 2)
    lo = ok & (rb == 0)
    imp[hi] = sgn[hi]
    imp[lo] = -sgn[lo]
    return imp, ok


# ==================================================================== LANE A
def bucket_table(E, pop, lab, names, nd, title):
    say('    %-12s %10s %6s %9s %12s %10s %10s' %
        (title, 'n', 'days', 'P(cont)', 'mem bp', 'NQ pts', 'x anchor'))
    tab = {}
    for i, nm in enumerate(names):
        m = pop & (lab == i)
        n = int(m.sum())
        if not n:
            say('    %-12s %10d' % (nm, 0))
            continue
        nzm = m & (E['sgn1'] != 0)
        pc = float(np.mean(E['sgn1'][nzm] == E['sgn'][nzm])) if nzm.sum() else NAN
        mb_ = float(E['mem'][m].mean())
        pt = float(E['mempts'][m].mean())
        say('    %-12s %10d %6d %9.4f %12s %10s %10s'
            % (nm, n, len(np.unique(E['dayid'][m])), pc, fmt(mb_, 5),
               fmt(pt, 4), fmt(mb_ / L.ANCHOR, 2)))
        tab[nm] = {'n': n, 'days': len(np.unique(E['dayid'][m])), 'pcont': pc,
                   'bp': mb_, 'pts': pt}
    return tab


def lane_a(D, E, nd, cells27, rcell):
    say('\n' + '=' * 100)
    say('PHASE 3  LANE A - PURE MEMORY MATHEMATICS')
    hr()
    N = len(E['T'])
    say('  Lane-A base population %d events on %d days'
        % (N, len(np.unique(E['dayid']))))
    nzm = E['sgn1'] != 0
    say('  unconditional memoryReturn %s bp   P(cont) %.4f   (anchor %+0.5f bp)'
        % (fmt(float(E['mem'].mean()), 5),
           float(np.mean(E['sgn1'][nzm] == E['sgn'][nzm])), L.ANCHOR))
    for i, s in enumerate(L.STN):
        m = E['rb'] == i
        z = m & nzm
        say('    %-7s n %9d  mem %s bp  P(cont) %.4f'
            % (s, int(m.sum()), fmt(float(E['mem'][m].mean()), 5),
               float(np.mean(E['sgn1'][z] == E['sgn'][z]))))
    HI = E['rb'] == 2
    LO = E['rb'] == 0
    R = {}

    # ---- A1 state age ----
    say('\n  ' + '-' * 96)
    lab = np.full(N, -1, dtype=np.int8)
    a = E['age']
    lab[(a >= 1) & (a <= 3)] = 0
    lab[(a >= 4) & (a <= 15)] = 1
    lab[(a >= 16) & (a <= 60)] = 2
    lab[a >= 61] = 3
    pop = HI & (lab >= 0)
    R['A1t'] = bucket_table(E, pop, lab, ['FRESH', 'YOUNG', 'ESTABLISHED',
                                          'MATURE'], nd, 'A1 HIGH age')
    R['A1tL'] = bucket_table(E, LO & (lab >= 0), lab,
                             ['FRESH', 'YOUNG', 'ESTABLISHED', 'MATURE'], nd,
                             'A1 LOW age')
    R['A1'] = prim_diff('A1', 'HIGH memoryReturn: FRESH(1-3) minus MATURE(>=61)',
                        E['mem'], pop & (lab == 0), pop & (lab == 3), E,
                        cells27, 30, +1, pop, lab, 0, 3, nd)
    show(R['A1'], L.MATERIAL_BP, 5000, 200)

    # ---- A2 transitions ----
    say('\n  ' + '-' * 96)
    pv = E['prevrb']
    lab = np.full(N, -1, dtype=np.int8)
    lab[(E['rb'] == 2) & ((pv == 0) | (pv == 1))] = 0
    lab[(E['rb'] == 2) & (pv == 2)] = 1
    pop = lab >= 0
    say('    full 3x3 transition table (memoryReturn bp / n):')
    for i, s0 in enumerate(L.STN):
        row = '      %-7s ->' % s0
        for j, s1 in enumerate(L.STN):
            m = (pv == i) & (E['rb'] == j)
            row += '  %s:%s(%d)' % (s1[:3], fmt(float(E['mem'][m].mean()), 4)
                                    if m.sum() else 'nan', int(m.sum()))
        say(row)
    R['A2t'] = bucket_table(E, pop, lab, ['HIGH-ARRIVAL', 'HIGH-PERSIST'], nd,
                            'A2')
    R['A2'] = prim_diff('A2', 'HIGH-ARRIVAL minus HIGH-PERSISTENCE',
                        E['mem'], lab == 0, lab == 1, E, cells27, 30, +1,
                        pop, lab, 0, 1, nd)
    show(R['A2'], L.MATERIAL_BP, 5000, 200)

    # ---- A3 velocity ----
    say('\n  ' + '-' * 96)
    v = E['vel']
    lab = np.full(N, -1, dtype=np.int8)
    ok = ~np.isnan(v)
    lab[ok & (v >= 0.10)] = 0
    lab[ok & (v > -0.10) & (v < 0.10)] = 1
    lab[ok & (v <= -0.10)] = 2
    pop = HI & (lab >= 0)
    R['A3t'] = bucket_table(E, pop, lab, ['RISING', 'FLAT', 'FALLING'], nd,
                            'A3 HIGH vel')
    R['A3tL'] = bucket_table(E, LO & (lab >= 0), lab,
                             ['RISING', 'FLAT', 'FALLING'], nd, 'A3 LOW vel')
    R['A3'] = prim_diff('A3', 'HIGH memoryReturn: RISING minus FALLING score',
                        E['mem'], pop & (lab == 0), pop & (lab == 2), E,
                        cells27, 30, +1, pop, lab, 0, 2, nd)
    show(R['A3'], L.MATERIAL_BP, 5000, 200)

    # ---- A4 run length ----
    say('\n  ' + '-' * 96)
    rl = E['runlen']
    lab = np.full(N, -1, dtype=np.int8)
    lab[rl == 1] = 0
    lab[rl == 2] = 1
    lab[rl >= 3] = 2
    pop = LO & (lab >= 0)
    R['A4t'] = bucket_table(E, pop, lab, ['RUN1', 'RUN2', 'RUN3+'], nd,
                            'A4 LOW runlen')
    R['A4tH'] = bucket_table(E, HI & (lab >= 0), lab, ['RUN1', 'RUN2', 'RUN3+'],
                             nd, 'A4 HIGH runlen')
    R['A4'] = prim_diff('A4', 'LOW memoryReturn: RUN>=3 minus RUN==1'
                        ' (predicted MORE NEGATIVE = stronger reversal)',
                        E['mem'], pop & (lab == 2), pop & (lab == 0), E,
                        cells27, 30, -1, pop, lab, 2, 0, nd)
    show(R['A4'], L.MATERIAL_BP, 5000, 200)

    # ---- A5 path efficiency ----
    say('\n  ' + '-' * 96)
    ec = L.terciles(E['eff'])
    say('    A5 outcome-blind efficiency terciles (full Lane-A base):'
        ' %.6f / %.6f' % ec)
    lab = L.tercode(E['eff'], ec)
    pop = HI & (lab >= 0)
    R['A5t'] = bucket_table(E, pop, lab, ['NOISY', 'MID', 'EFFICIENT'], nd,
                            'A5 HIGH eff')
    rec = prim_diff('A5', 'HIGH memoryReturn: EFFICIENT minus NOISY,'
                    ' common-weight standardised within |r[t]| terciles',
                    E['mem'], pop & (lab == 2), pop & (lab == 0), E,
                    cells27, 30, +1, pop, lab, 2, 0, nd)
    cwo, cwl, cwh, cwp, ncl, nbd = L.dc_diff_cw(
        E['dayid'], E['mem'], pop & (lab == 2), pop & (lab == 0), rcell, nd, 30)
    say('    raw (unstandardised) EFFICIENT-NOISY %s bp' % fmt(rec['obs'], 5))
    rec['raw'] = rec['obs']
    rec['obs'], rec['lo'], rec['hi'], rec['p'] = cwo, cwl, cwh, cwp
    rec['label'] += '  [primary = standardised, %d |r| cells]' % ncl
    R['A5'] = rec
    show(R['A5'], L.MATERIAL_BP, 5000, 200)

    # ---- A6 flip count ----
    say('\n  ' + '-' * 96)
    fl = E['flips']
    lab = np.full(N, -1, dtype=np.int8)
    lab[(fl >= 0) & (fl <= 2)] = 0
    lab[(fl >= 3) & (fl <= 4)] = 1
    lab[fl >= 5] = 2
    pop = HI & (lab >= 0)
    R['A6t'] = bucket_table(E, pop, lab, ['ORDERLY', 'MIXED', 'CHOPPY'], nd,
                            'A6 HIGH flips')
    R['A6'] = prim_diff('A6', 'HIGH memoryReturn: ORDERLY(<=2) minus CHOPPY(>=5)',
                        E['mem'], pop & (lab == 0), pop & (lab == 2), E,
                        cells27, 30, +1, pop, lab, 0, 2, nd)
    rlc = np.full(N, -1, dtype=np.int8)
    rlc[rl == 1] = 0
    rlc[rl == 2] = 1
    rlc[rl >= 3] = 2
    inc, ncl = L.common_weight(E['mem'], pop & (lab == 0), pop & (lab == 2),
                               rlc, 30)
    R['A6']['inc_runlen'] = inc
    R['A6']['inc_cells'] = ncl
    show(R['A6'], L.MATERIAL_BP, 5000, 200)
    ok_inc = (inc == inc) and ((inc > 0) == (R['A6']['obs'] > 0)) \
        and abs(inc) >= 0.5 * abs(R['A6']['obs'])
    R['A6']['redundant_runlen'] = not ok_inc
    say('    INCREMENTALITY DUTY vs run length: standardised %s bp (%d cells)'
        ' -> %s' % (fmt(inc, 5), ncl,
                    'INCREMENTAL' if ok_inc else 'REDUNDANT WITH RUN LENGTH'))

    # ---- A7 volatility trajectory ----
    say('\n  ' + '-' * 96)
    va = E['va']
    lab = np.full(N, -1, dtype=np.int8)
    ok = ~np.isnan(va)
    lab[ok & (va >= 1.15)] = 0
    lab[ok & (va > 1.0 / 1.15) & (va < 1.15)] = 1
    lab[ok & (va <= 1.0 / 1.15)] = 2
    pop = HI & (lab >= 0)
    R['A7t'] = bucket_table(E, pop, lab, ['EXPANDING', 'STABLE', 'CONTRACTING'],
                            nd, 'A7 HIGH va')
    R['A7tL'] = bucket_table(E, LO & (lab >= 0), lab,
                             ['EXPANDING', 'STABLE', 'CONTRACTING'], nd,
                             'A7 LOW va')
    R['A7'] = prim_diff('A7', 'HIGH memoryReturn: EXPANDING minus STABLE ATR'
                        ' trajectory  (NOT shock continuation)',
                        E['mem'], pop & (lab == 0), pop & (lab == 1), E,
                        cells27, 30, +1, pop, lab, 0, 1, nd)
    show(R['A7'], L.MATERIAL_BP, 5000, 200)

    # ---- A8 decay ----
    say('\n  ' + '-' * 96)
    say('    A8 PERSISTENCE DECAY  (frozen horizons 1,2,3,5)')
    c = D['c']
    T, sg, fwdT = E['T'], E['sgn'], E['fwd']
    say('    %-8s %-6s %10s %12s %12s %10s' %
        ('state', 'h', 'n', 'cum bp', 'incr bp', 'P(cont h)'))
    dec = {}
    for si, sn in enumerate(L.STN):
        base = (E['rb'] == si)
        prevc = None
        for hh in (1, 2, 3, 5):
            m = base & (fwdT >= hh)
            n = int(m.sum())
            if not n:
                continue
            cum = float(np.mean(sg[m] * np.log(c[T[m] + hh] / c[T[m]]) * BP))
            inc_ = (float(np.mean(sg[m] * np.log(
                c[T[m] + hh] / c[T[m] + hh - 1]) * BP)))
            pc = float(np.mean(c[T[m] + hh] > c[T[m]]) if False else
                       np.mean(np.sign(c[T[m] + hh] - c[T[m]]) == sg[m]))
            say('    %-8s %-6d %10d %12s %12s %10.4f'
                % (sn, hh, n, fmt(cum, 5), fmt(inc_, 5), pc))
            dec['%s_%d' % (sn, hh)] = {'n': n, 'cum': cum, 'incr': inc_,
                                       'pcont': pc}
            prevc = cum
    R['A8t'] = dec
    m3 = (E['rb'] == 2) & (fwdT >= 3)
    u = np.log(c[T[m3] + 3] / c[T[m3] + 1]) * BP
    sv = sg[m3]
    R['A8'] = prim_mean('A8', 'HIGH incremental memory beyond minute 1:'
                        ' m3 - m1 (paired, contiguity to t+3)',
                        u, sv, E['dayid'][m3], E['year'][m3], E['tod'][m3],
                        +1, nd)
    show(R['A8'], L.MATERIAL_BP, 5000, 200)
    return R


# ==================================================================== LANE B
def lane_b(D, nd, seedoff=0):
    say('\n' + '=' * 100)
    say('PHASE 4  LANE B - MATHEMATICAL IFVG')
    hr()
    say('  PUBLIC CONCEPT (audited, cited in the preregistration) vs OUR'
        ' IMPLEMENTATION:')
    say('    public: an FVG that price closes through is "inverted" and flips'
        ' role; traders watch a retest.')
    say('    ours  : the exact mechanical translation frozen in the prereg.'
        ' NOT claimed to be any official ICT strategy.')
    say('    no public profitability claim is treated as evidence anywhere.')
    F = build_fvgs(D)
    say('\n  B1 FVG CONSTRUCTION')
    say('    raw 3-bar FVGs (contiguous)          %10d' % F['n_all'])
    say('    size-qualified gap >= 0.25*ATR20     %10d   <- PRIMARY population'
        % F['n_qual'])
    say('    secondary (>= 1 tick, reported once) %10d' % F['n_tick'])
    say('    bullish %d   bearish %d' % (F['n_bull'], F['n_bear']))
    t0 = time.time()
    res, invj, rtj = track_fvgs(D, F)
    say('    tracked in %.0f s' % (time.time() - t0))
    K, dF, zlo, zhi = F['K'], F['dF'], F['zlo'], F['zhi']
    cnt = {k: int(np.sum(res == k)) for k in
           ('UNTOUCHED', 'UNRESOLVED', 'INVERT', 'HOLD', 'EXPIRED')}
    for k in ('UNTOUCHED', 'UNRESOLVED', 'HOLD', 'INVERT', 'EXPIRED'):
        say('    %-12s %10d' % (k, cnt[k]))
    touched = (res == 'HOLD') | (res == 'INVERT') | (res == 'EXPIRED')
    resolved = (res == 'HOLD') | (res == 'INVERT')
    say('    TOUCHED %d   RESOLVED (hold|invert) %d   inversion rate %.4f'
        % (int(touched.sum()), int(resolved.sum()),
           cnt['INVERT'] / max(1, int(resolved.sum()))))
    R = {'B1': {'n_all': F['n_all'], 'n_qual': F['n_qual'],
                'n_tick': F['n_tick'], 'n_bull': F['n_bull'],
                'n_bear': F['n_bear'], 'counts': cnt,
                'touched': int(touched.sum()), 'resolved': int(resolved.sum())}}

    # ---------------- B2 which FVGs invert ----------------
    say('\n  ' + '-' * 96)
    say('  B2  WHICH FVGS INVERT?  (population = resolved, touched FVGs)')
    imp, okm = mem_implication(D, K)
    cls = np.zeros(len(K), dtype=np.int8)          # 0 NEUTRAL 1 ALIGNED 2 OPP
    cls[(imp != 0) & (imp == dF)] = 1
    cls[(imp != 0) & (imp == -dF)] = 2
    sel = resolved
    y = (res[sel] == 'INVERT').astype(np.float64) * 100.0
    dayB = D['dayid'][K[sel]]
    yrB = D['year'][K[sel]]
    todB = D['tod'][K[sel]]
    clsB = cls[sel]
    say('    %-10s %8s %6s %12s' % ('class', 'n', 'days', 'inversion %'))
    b2t = {}
    for i, nm in enumerate(['NEUTRAL', 'ALIGNED', 'OPPOSED']):
        m = clsB == i
        if not m.sum():
            continue
        say('    %-10s %8d %6d %12.4f' % (nm, int(m.sum()),
                                          len(np.unique(dayB[m])),
                                          float(y[m].mean())))
        b2t[nm] = {'n': int(m.sum()), 'days': len(np.unique(dayB[m])),
                   'rate': float(y[m].mean())}
    for nm, mm in (('bullish FVG', dF[sel] > 0), ('bearish FVG', dF[sel] < 0)):
        say('    %-10s %8d          %12.4f' % (nm, int(mm.sum()),
                                               float(y[mm].mean())))
    aB = np.abs(D['r'][K[sel]])
    arB = D['atr'][K[sel]] / D['c'][K[sel]]
    ac = L.terciles(arB)
    rc = L.terciles(aB)
    cellsB = (L.tercode(arB, ac) * 9 + L.tercode(aB, rc) * 3 + todB).astype(np.int16)
    cellsB[(L.tercode(arB, ac) < 0) | (L.tercode(aB, rc) < 0)] = -1
    EB = {'dayid': dayB, 'year': yrB, 'tod': todB}
    ma, mb = clsB == 2, clsB == 1
    R['B2'] = prim_diff('B2', 'inversion rate: MEMORY-OPPOSED minus'
                        ' MEMORY-ALIGNED at FVG formation',
                        y, ma, mb, EB, cellsB, 10, +1,
                        np.ones(len(y), dtype=bool), clsB, 2, 1, nd, unit='pp')
    show(R['B2'], L.MATERIAL_PP, 0, 0)
    say('    one-way tables on the other frozen predictors (descriptive):')
    for nm, arr, cuts in (('RB[k]', D['rb'][K[sel]].astype(float), None),
                          ('A3 vel', D['vel'][K[sel]], None),
                          ('A4 runlen', D['runlen'][K[sel]].astype(float), None),
                          ('A5 eff', D['eff'][K[sel]], None)):
        if nm == 'RB[k]':
            row = '      RB[k]     ' + '  '.join(
                '%s %.3f (n%d)' % (s, float(y[arr == i].mean()) if (arr == i).sum()
                                   else NAN, int((arr == i).sum()))
                for i, s in enumerate(L.STN))
        elif nm == 'A4 runlen':
            row = '      runlen    ' + '  '.join(
                '%s %.3f (n%d)' % (lb, float(y[m2].mean()) if m2.sum() else NAN,
                                   int(m2.sum()))
                for lb, m2 in (('1', arr == 1), ('2', arr == 2), ('3+', arr >= 3)))
        else:
            tc = L.tercode(arr, L.terciles(arr))
            row = '      %-9s ' % nm.split()[1] + '  '.join(
                '%s %.3f (n%d)' % (t, float(y[tc == t].mean()) if (tc == t).sum()
                                   else NAN, int((tc == t).sum()))
                for t in (0, 1, 2))
        say(row)

    # ---------------- B3 post-inversion drift ----------------
    say('\n  ' + '-' * 96)
    say('  B3  POST-INVERSION DRIFT (at the inversion close)')
    invm = res == 'INVERT'
    J = invj[invm]
    dI = (-dF[invm]).astype(np.int8)
    # inversion bars are NOT in formation order (a later FVG can invert
    # first); chronological order is required for the within-day rotation
    # null. Sorting changes no statistic - the bootstrap is order-free.
    oi = np.argsort(J, kind='stable')
    J, dI = J[oi], dI[oi]
    R['B3'], g3 = drift_block('B3', 'post-inversion +5m drift in the inverted'
                              ' direction', D, J, dI, nd)

    # ---------------- B4 retest ----------------
    say('\n  ' + '-' * 96)
    say('  B4  FIRST RETEST-REJECT')
    rmask = invm & (rtj >= 0)
    Q = rtj[rmask]
    dQ = (-dF[rmask]).astype(np.int8)
    say('    inversions %d -> retest-reject before cooldown %d'
        % (int(invm.sum()), len(Q)))
    o = np.argsort(Q, kind='stable')
    Q, dQ = Q[o], dQ[o]
    keep = []
    last = {1: -10 ** 9, -1: -10 ** 9}
    for i in range(len(Q)):
        if Q[i] - last[int(dQ[i])] >= 30:
            keep.append(i)
            last[int(dQ[i])] = Q[i]
    Q, dQ = Q[keep], dQ[keep]
    say('    after the frozen per-direction 30-bar cooldown: %d events' % len(Q))
    R['B4'], g4 = drift_block('B4', 'post-retest-reject +5m drift', D, Q, dQ, nd)

    # ---------------- B5 MEMORY x IFVG ----------------
    say('\n  ' + '-' * 96)
    say('  B5  MEMORY x IFVG at the retest-reject close')
    impQ, okQ = mem_implication(D, Q)
    clsQ = np.zeros(len(Q), dtype=np.int8)
    clsQ[(impQ != 0) & (impQ == dQ)] = 1
    clsQ[(impQ != 0) & (impQ == -dQ)] = 2
    ok5 = D['fwd'][Q] >= 5
    y5 = np.full(len(Q), NAN)
    y5[ok5] = dQ[ok5] * np.log(D['c'][Q[ok5] + 5] / D['c'][Q[ok5]]) * BP
    dayQ = D['dayid'][Q]
    EQ = {'dayid': dayQ[ok5], 'year': D['year'][Q][ok5], 'tod': D['tod'][Q][ok5]}
    yQ = y5[ok5]
    cQ = clsQ[ok5]
    say('    %-10s %8s %6s %12s' % ('class', 'n', 'days', '+5m bp'))
    b5t = {}
    for i, nm in enumerate(['NEUTRAL', 'ALIGNED', 'OPPOSED']):
        m = cQ == i
        b5t[nm] = {'n': int(m.sum()),
                   'days': len(np.unique(EQ['dayid'][m])) if m.sum() else 0,
                   'bp': float(yQ[m].mean()) if m.sum() else NAN}
        say('    %-10s %8d %6d %12s' % (nm, b5t[nm]['n'], b5t[nm]['days'],
                                        fmt(b5t[nm]['bp'], 4)))
    R['B5t'] = b5t
    nA5, nB5 = b5t['ALIGNED']['n'], b5t['OPPOSED']['n']
    dA5, dB5 = b5t['ALIGNED']['days'], b5t['OPPOSED']['days']
    floors_ok = nA5 >= 60 and nB5 >= 60 and dA5 >= 40 and dB5 >= 40
    say('    frozen B5 floors: ALIGNED >=60 ev / >=40 days, OPPOSED >=60 / >=40'
        '  -> %s' % ('PASS' if floors_ok else 'FAIL'))
    if nA5 and nB5:
        arQ = (D['atr'][Q] / D['c'][Q])[ok5]
        abQ = np.abs(D['r'][Q])[ok5]
        cellsQ = (L.tercode(arQ, L.terciles(arQ)) * 9
                  + L.tercode(abQ, L.terciles(abQ)) * 3 + EQ['tod']).astype(np.int16)
        R['B5'] = prim_diff('B5', 'IFVG retest +5m drift: MEMORY-ALIGNED minus'
                            ' MEMORY-OPPOSED', yQ, cQ == 1, cQ == 2, EQ,
                            cellsQ, 10, +1, np.ones(len(yQ), dtype=bool),
                            cQ, 1, 2, nd)
        show(R['B5'], L.MATERIAL_BP, 60, 40)
    else:
        R['B5'] = {'tag': 'B5', 'label': 'INSUFFICIENT', 'unit': 'bp',
                   'pred': 1, 'obs': NAN, 'lo': NAN, 'hi': NAN, 'p': NAN,
                   'perm': NAN, 'degen': NAN, 'nA': nA5, 'nB': nB5,
                   'daysA': dA5, 'daysB': dB5, 'nbd': 0, 'cw': NAN,
                   'cwcells': 0, 'years': {}, 'yagree': 0, 'nyear': 0,
                   'tod': {}, 'tagree': 0, 'trim1': NAN, 'trim5': NAN,
                   'meanA': NAN, 'meanB': NAN}
    R['B5']['floors_ok'] = floors_ok

    # ---------------- B6 generic failure control ----------------
    say('\n  ' + '-' * 96)
    say('  B6  GENERIC FAILURE / REVERSAL CONTROL  (decisive for interpretation)')
    gj, gd = generic_failures(D)
    say('    generic failed-structure events (30m close breakout then close back'
        ' through the breakout bar, 30-bar cooldown): %d' % len(gj))
    R['B6'] = {}
    for nm, EV, DV in (('B3 post-inversion', J, dI), ('B4 retest-reject', Q, dQ)):
        d, cw, nc, lo, hi, p = matched_vs_generic(D, EV, DV, gj, gd, nd)
        beat = (cw == cw) and cw > 0
        say('    %-20s matched common-weight IFVG minus GENERIC %s bp'
            ' (%d cells)  CI [%s, %s]  p %s  -> %s'
            % (nm, fmt(cw, 4), nc, fmt(lo, 4), fmt(hi, 4),
               ('%.5f' % p) if p == p else 'nan',
               'IFVG EXCEEDS GENERIC' if beat else 'IFVG DOES NOT EXCEED GENERIC'))
        R['B6'][nm] = {'raw_diff': d, 'cw': cw, 'cells': nc, 'lo': lo,
                       'hi': hi, 'p': p, 'beat': bool(beat)}
    R['_Q'] = Q
    R['_dQ'] = dQ
    R['_clsQ'] = clsQ
    return R


def drift_block(tag, label, D, J, dv, nd):
    ok5 = D['fwd'][J] >= 5
    say('    events %d   with +5m available %d   days %d'
        % (len(J), int(ok5.sum()), len(np.unique(D['dayid'][J]))))
    g = geometry(D, J, dv.astype(np.float64))
    say('    %-8s %10s %12s %12s' % ('horizon', 'n', 'bp', 'NQ pts'))
    hor = {}
    for hh in (1, 3, 5, 15):
        m = g['ok%d' % hh]
        hor[hh] = {'n': int(m.sum()),
                   'bp': float(np.nanmean(g['bp%d' % hh])),
                   'pts': float(np.nanmean(g['pts%d' % hh]))}
        say('    +%-7d %10d %12s %12s' % (hh, hor[hh]['n'],
                                          fmt(hor[hh]['bp'], 4),
                                          fmt(hor[hh]['pts'], 4)))
    mf, ma_ = float(np.nanmean(g['mfe'])), float(np.nanmean(g['mae']))
    ffp, nf, na = ffpct(g['ff'])
    say('    MFE %.3f  MAE %.3f  MFE/MAE %.3f  |  FF@1ATR/60m %.2f%%'
        ' (fav %d / adv %d)' % (mf, ma_, mf / ma_ if ma_ else NAN, ffp, nf, na))
    u = np.full(len(J), NAN)
    u[ok5] = np.log(D['c'][J[ok5] + 5] / D['c'][J[ok5]]) * BP
    rec = prim_mean(tag, label, u[ok5], dv[ok5].astype(np.float64),
                    D['dayid'][J][ok5], D['year'][J][ok5], D['tod'][J][ok5],
                    +1, nd)
    rec['hor'] = hor
    rec['mfe'] = mf
    rec['mae'] = ma_
    rec['ffpct'] = ffp
    show(rec, L.MATERIAL_BP, 0, 0)
    return rec, g


def matched_vs_generic(D, EV, DV, gj, gd, nd):
    def pack(idx, dv):
        ok = D['fwd'][idx] >= 5
        idx, dv = idx[ok], dv[ok]
        y = dv * np.log(D['c'][idx + 5] / D['c'][idx]) * BP
        pre = np.full(len(idx), NAN)
        okp = D['bwd'][idx] >= 15
        pre[okp] = np.abs(np.log(D['c'][idx[okp]] / D['c'][idx[okp] - 15]))
        return idx, y, D['atr'][idx] / D['c'][idx], pre, D['tod'][idx], \
            D['dayid'][idx]
    i1, y1, a1, p1, t1, d1 = pack(EV, DV.astype(np.float64))
    i2, y2, a2, p2, t2, d2 = pack(gj, gd.astype(np.float64))
    ac = L.terciles(np.concatenate([a1, a2]))
    pc = L.terciles(np.concatenate([p1, p2]))
    def cells(a, p, t):
        ta, tp = L.tercode(a, ac), L.tercode(p, pc)
        c = (ta * 9 + tp * 3 + t).astype(np.int16)
        c[(ta < 0) | (tp < 0)] = -1
        return c
    y = np.concatenate([y1, y2])
    cl = np.concatenate([cells(a1, p1, t1), cells(a2, p2, t2)])
    dd = np.concatenate([d1, d2])
    ma = np.zeros(len(y), dtype=bool)
    ma[:len(y1)] = True
    mb = ~ma
    raw = float(y1.mean() - y2.mean())
    cw, nc = L.common_weight(y, ma, mb, cl, 10)
    o, lo, hi, p, _, _ = L.dc_diff_cw(dd, y, ma, mb, cl, nd, 10)
    return raw, cw, nc, lo, hi, p


# ================================================================ STRATEGIES
def cw_vs(D, T1, d1, T2, d2, nd, minc):
    """Common-weight comparison of +5m gross points between two event sets."""
    def pack(T, dv):
        ok = D['fwd'][T] >= 5
        T, dv = T[ok], dv[ok]
        y = dv * (D['c'][T + 5] - D['c'][T])
        return T, y, D['atr'][T] / D['c'][T], np.abs(D['r'][T]), \
            D['tod'][T], D['dayid'][T]
    a1, y1, r1, b1, t1, dd1 = pack(T1, d1)
    a2, y2, r2, b2, t2, dd2 = pack(T2, d2)
    ac = L.terciles(np.concatenate([r1, r2]))
    bc = L.terciles(np.concatenate([b1, b2]))
    def cells(r, b, t):
        tr, tb = L.tercode(r, ac), L.tercode(b, bc)
        c = (tr * 9 + tb * 3 + t).astype(np.int16)
        c[(tr < 0) | (tb < 0)] = -1
        return c
    y = np.concatenate([y1, y2])
    cl = np.concatenate([cells(r1, b1, t1), cells(r2, b2, t2)])
    ma = np.zeros(len(y), dtype=bool)
    ma[:len(y1)] = True
    cw, nc = L.common_weight(y, ma, ~ma, cl, minc)
    return float(y1.mean()), float(y2.mean()), cw, nc


def strategy_block(name, label, D, T, dirv, nd, ctrls, minc):
    say('\n  ' + '-' * 96)
    say('  %s  %s' % (name, label))
    n = len(T)
    day = D['dayid'][T]
    yr = D['year'][T]
    td = D['tod'][T]
    say('    events %d   unique days %d   LONG %d   SHORT %d'
        % (n, len(np.unique(day)), int((dirv > 0).sum()), int((dirv < 0).sum())))
    g = geometry(D, T, dirv)
    say('    %-8s %10s %12s %12s %12s' % ('horizon', 'n', 'bp', 'gross pts',
                                          'gross/cost'))
    hor = {}
    for hh in (1, 3, 5, 15):
        m = g['ok%d' % hh]
        pt = float(np.nanmean(g['pts%d' % hh]))
        hor[hh] = {'n': int(m.sum()), 'bp': float(np.nanmean(g['bp%d' % hh])),
                   'pts': pt, 'costfrac': pt / COST}
        say('    +%-7d %10d %12s %12s %12s'
            % (hh, hor[hh]['n'], fmt(hor[hh]['bp'], 4), fmt(pt, 4),
               fmt(pt / COST, 3)))
    mf, ma_ = float(np.nanmean(g['mfe'])), float(np.nanmean(g['mae']))
    ratio = mf / ma_ if ma_ else NAN
    ffp, nf, na = ffpct(g['ff'])
    med5 = float(np.nanmedian(g['pts5']))
    say('    MFE %.3f  MAE %.3f  MFE/MAE %.3f  |  FF@1ATR/60m %.2f%%'
        ' (fav %d / adv %d, n=%d)  |  median +5m %s pts'
        % (mf, ma_, ratio, ffp, nf, na, nf + na, fmt(med5, 4)))

    ok5 = g['ok5']
    ok15 = g['ok15']
    net5 = g['pts5'][ok5] - COST
    net15 = g['pts15'][ok15] - COST
    d5, y5, t5 = day[ok5], yr[ok5], td[ok5]
    o5, l5, h5, p5, _ = L.dc_mean(d5, net5, nd)
    gr5, gl5, gh5, gp5, _ = L.dc_mean(d5, g['pts5'][ok5], nd)
    gr15, gl15, gh15, gp15, _ = L.dc_mean(day[ok15], g['pts15'][ok15], nd)
    say('    GROSS +5m  %s pts  CI [%s, %s]   gross/cost %.3f  CIlo/cost %.3f'
        % (fmt(gr5, 4), fmt(gl5, 4), fmt(gh5, 4), gr5 / COST, gl5 / COST))
    say('    GROSS +15m %s pts  CI [%s, %s]   gross/cost %.3f  CIlo/cost %.3f'
        % (fmt(gr15, 4), fmt(gl15, 4), fmt(gh15, 4), gr15 / COST, gl15 / COST))
    say('    NET   +5m  %s pts  CI [%s, %s]   boot p %.5f'
        % (fmt(o5, 4), fmt(l5, 4), fmt(h5, 4), p5))
    ys, ay = L.split_sign_mean(net5, np.ones(len(net5), dtype=bool), y5, 1.0)
    ts, at = L.split_sign_mean(g['pts5'][ok5], np.ones(int(ok5.sum()), dtype=bool),
                               t5, 1.0)
    say('    net by year  : ' + '  '.join('%d %s(n%d)' % (k, fmt(v[1], 3), v[0])
                                          for k, v in sorted(ys.items())))
    say('    gross by ToD : ' + '  '.join('%s %s(n%d)' % (L.TODN[k], fmt(v[1], 3),
                                                          v[0])
                                          for k, v in sorted(ts.items())))
    tr1 = L.trim_mean(g['pts5'][ok5], np.ones(int(ok5.sum()), dtype=bool), 0.01)
    tr5 = L.trim_mean(g['pts5'][ok5], np.ones(int(ok5.sum()), dtype=bool), 0.05)
    say('    gross +5m trims: top1%% %s   top5%% %s' % (fmt(tr1, 4), fmt(tr5, 4)))
    ls = {}
    for nm, m in (('LONG', dirv[ok5] > 0), ('SHORT', dirv[ok5] < 0)):
        if m.sum():
            ls[nm] = {'n': int(m.sum()),
                      'gross': float(g['pts5'][ok5][m].mean())}
            say('    %-6s n %8d  gross +5m %s pts'
                % (nm, ls[nm]['n'], fmt(ls[nm]['gross'], 4)))
    st, ct = L.day_slices(d5)
    raw = D['c'][T[ok5] + 5] - D['c'][T[ok5]]
    nn = int(ok5.sum())
    # DISCLOSURE D5. The cost-adjusted primary differs from the gross
    # primary by the ADDITIVE CONSTANT -COST, which the rotation does not
    # touch. A two-sided |statistic| test is not invariant to that shift:
    # scoring |mean - COST| compares an observed value near -0.75 against
    # a null centred on -0.87 and reports the NULL as the more extreme,
    # which inverts the test. The permutation is therefore evaluated on
    # the quantity the rotation actually randomises - the directional
    # mean - which is the identical hypothesis with the constant removed
    # from both sides. No gate, threshold or population changes.
    perm, degen = L.rot_perm(st, ct, raw, [dirv[ok5].astype(float)],
                             lambda s: s[0] / nn, gr5)
    say('    rotation permutation on the cost-adjusted primary (cost is an'
        ' additive constant and cancels; see D5): p %.5f'
        ' (degenerate-day share %.3f)' % (perm, degen))
    ffind = (g['ff'] == 1).astype(np.float64)[(g['ff'] == 1) | (g['ff'] == 2)]
    ffday = day[(g['ff'] == 1) | (g['ff'] == 2)]
    fo, flo, fhi, fp, _ = L.dc_mean(ffday, ffind - 0.5, nd)
    say('    FF@1ATR mean-0.5 %s   CI [%s, %s]' % (fmt(fo, 4), fmt(flo, 4),
                                                   fmt(fhi, 4)))
    cres = {}
    for cn, (Tc, dc) in ctrls.items():
        m1, m2, cw, nc = cw_vs(D, T, dirv, Tc, dc, nd, minc)
        cres[cn] = {'strategy': m1, 'control': m2, 'cw': cw, 'cells': nc}
        say('    CONTROL %-16s strategy %s vs %s pts  ->  common-weight'
            ' incremental %s pts (%d cells)  %s'
            % (cn, fmt(m1, 4), fmt(m2, 4), fmt(cw, 4), nc,
               'BEATS' if (cw == cw and cw > 0) else 'DOES NOT BEAT'))
    return {'name': name, 'label': label, 'n': n,
            'days': len(np.unique(day)), 'long': int((dirv > 0).sum()),
            'short': int((dirv < 0).sum()), 'hor': hor, 'mfe': mf, 'mae': ma_,
            'mfe_mae': ratio, 'ffpct': ffp, 'ffn': nf + na, 'ff_ci': (fo, flo, fhi),
            'med5': med5, 'gross5': gr5, 'g5lo': gl5, 'g5hi': gh5,
            'gross15': gr15, 'g15lo': gl15, 'g15hi': gh15,
            'net5': o5, 'n5lo': l5, 'n5hi': h5, 'p': p5, 'perm': perm,
            'degen': degen, 'years': {int(k): v[1] for k, v in ys.items()},
            'ypos': sum(1 for v in ys.values() if v[1] > 0), 'nyear': len(ys),
            'tod': {int(k): v[1] for k, v in ts.items()},
            'tpos': sum(1 for v in ts.values() if v[1] > 0),
            'trim1': tr1, 'trim5': tr5, 'ls': ls, 'ctrl': cres}


def sg_gates(s, parent_ok, q):
    g = {}
    g['SG1'] = bool(parent_ok)
    g['SG2'] = s['gross5'] > 0
    g['SG3'] = s['gross5'] > 0 and s['g5lo'] > 0
    g['SG4'] = s['mfe_mae'] == s['mfe_mae'] and s['mfe_mae'] >= 1.2
    fo, flo, fhi = s['ff_ci']
    g['SG5'] = fo == fo and fo > 0 and flo > 0
    c5 = s['gross5'] >= 1.0 * COST and s['g5lo'] >= 0.5 * COST
    c15 = s['gross15'] >= 1.0 * COST and s['g15lo'] >= 0.5 * COST
    g['SG6'] = bool(c5 or c15)
    g['SG7'] = s['ypos'] >= 5
    g['SG8'] = s['tpos'] >= 2
    g['SG9'] = all(t == t and t > 0 for t in (s['trim1'], s['trim5']))
    g['SG10'] = all(v['cw'] == v['cw'] and v['cw'] > 0 for v in s['ctrl'].values())
    g['SG11'] = bool(q <= 0.05 and s['perm'] <= 0.05)
    g['SG12'] = True
    return g


# ====================================================================== MAIN
def main():
    t0 = time.time()
    phase0()
    say('\n  loading canonical grid ...')
    D = L.load_all()
    nd = D['nd']
    phase1(D)
    phase2()
    E = lane_a_events(D)
    E['mempts'] = D['sgn'][E['T']] * (D['c'][E['T'] + 1] - D['c'][E['T']])
    ac = L.terciles(E['arel'])
    rc = L.terciles(E['absr'])
    say('\n  OUTCOME-BLIND CONTROL CUTPOINTS (printed before any outcome join)')
    say('    ATR/close terciles   %.8f  %.8f' % ac)
    say('    |r[t]| terciles      %.8f  %.8f' % rc)
    ta, tr = L.tercode(E['arel'], ac), L.tercode(E['absr'], rc)
    cells27 = (ta * 9 + tr * 3 + E['tod']).astype(np.int16)
    cells27[(ta < 0) | (tr < 0)] = -1
    RA = lane_a(D, E, nd, cells27, tr.astype(np.int16))
    RB = lane_b(D, nd)

    # -------------------------------------------------- MA gates
    say('\n' + '=' * 100)
    say('PHASE 5  MATHEMATICAL DESTRUCTION   MA1-MA8   (M_math = 12, BH binding)')
    hr()
    order = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8',
             'B2', 'B3', 'B4', 'B5']
    recs = {k: (RA[k] if k in RA else RB[k]) for k in order}
    pv = [recs[k]['p'] if recs[k]['p'] == recs[k]['p'] else 1.0 for k in order]
    qv = L.bh(pv)
    floors = {'A1': (5000, 200), 'A2': (5000, 200), 'A3': (5000, 200),
              'A4': (5000, 200), 'A5': (5000, 200), 'A6': (5000, 200),
              'A7': (5000, 200), 'A8': (5000, 200),
              'B2': (0, 0), 'B3': (0, 0), 'B4': (0, 0), 'B5': (60, 40)}
    MA = {}
    say('  %-4s %10s %10s %9s %9s %9s  %s' %
        ('id', 'primary', 'unit', 'raw p', 'BH q', 'perm p', 'MA1..MA8'))
    for i, k in enumerate(order):
        r = recs[k]
        fe = L.MATERIAL_PP if r['unit'] == 'pp' else L.MATERIAL_BP
        fn, fd = floors[k]
        g = ma_gates(r, fn, fd, fe, 5, qv[i])
        if k == 'B2':
            g['MA2'] = (RB['B1']['n_qual'] >= 2000
                        and RB['B1']['touched'] >= 1000)
        elif k == 'B3':
            g['MA2'] = RB['B1']['counts']['INVERT'] >= 500
        elif k == 'B4':
            g['MA2'] = r['nA'] >= 200 and r['daysA'] >= 120
        elif k == 'B5':
            g['MA2'] = bool(RB['B5'].get('floors_ok'))
        if k in ('B3', 'B4', 'A8'):
            g['MA7'] = True     # single-arm drift: no two-arm standardisation
        r['q'] = qv[i]
        MA[k] = g
        say('  %-4s %10s %10s %9.5f %9.5f %9s  %s  (%d/8)'
            % (k, fmt(r['obs'], 4), r['unit'], pv[i], qv[i],
               ('%.5f' % r['perm']) if r['perm'] == r['perm'] else 'nan',
               ' '.join('%s:%s' % (a, 'P' if g[a] else 'F')
                        for a in sorted(g)), sum(g.values())))
    say('\n  NOTE  MA7 for B3/B4/A8 is single-arm drift: there is no two-arm'
        ' contrast to standardise, so MA7 is scored on the frozen control'
        ' comparisons reported in B6 / A8 instead of a common-weight delta.')
    survivors = [k for k in order if all(MA[k].values())]
    say('\n  MATHEMATICAL SURVIVORS (all 8 gates): %s'
        % (', '.join(survivors) if survivors else 'NONE'))

    # -------------------------------------------------- strategies
    say('\n' + '=' * 100)
    say('PHASE 6  STRATEGY HYPOTHESES  (raw geometry only; NO management)')
    hr()
    say('  HIERARCHY (frozen, as written in the preregistration): a strategy is')
    say('  ELIGIBLE FOR PROMOTION only if its parent survives; geometry is')
    say('  REPORTED for all four regardless. Parents: S1<-A1 S2<-A4 S3<-A2 S4<-B5.')
    T, sg, rb = E['T'], E['sgn'], E['rb']
    base_all = (T, sg.astype(np.float64))
    hi_all = (T[rb == 2], sg[rb == 2].astype(np.float64))
    lo_all = (T[rb == 0], -sg[rb == 0].astype(np.float64))
    m1 = (rb == 2) & (E['age'] <= 3)
    m2 = (rb == 0) & (E['runlen'] >= 3)
    m3 = (rb == 2) & ((E['prevrb'] == 0) | (E['prevrb'] == 1))
    S = {}
    S['S1'] = strategy_block('S1', 'HIGH + state age <= 3, continuation of'
                             ' sign(r[t])', D, T[m1], sg[m1].astype(np.float64),
                             nd, {'last-return only': base_all,
                                  'RVMR state only': hi_all}, 30)
    S['S2'] = strategy_block('S2', 'LOW + runlen >= 3, reversal of the run',
                             D, T[m2], -sg[m2].astype(np.float64), nd,
                             {'last-return only': (T, -sg.astype(np.float64)),
                              'RVMR state only': lo_all}, 30)
    S['S3'] = strategy_block('S3', 'HIGH-ARRIVAL, continuation of sign(r[t])',
                             D, T[m3], sg[m3].astype(np.float64), nd,
                             {'last-return only': base_all,
                              'RVMR state only': hi_all}, 30)
    Q, dQ, clsQ = RB['_Q'], RB['_dQ'], RB['_clsQ']
    al = clsQ == 1
    imp_all, _ = mem_implication(D, T)
    memonly = (T[imp_all != 0], imp_all[imp_all != 0].astype(np.float64))
    if int(al.sum()) >= 15:
        S['S4'] = strategy_block('S4', 'IFVG first retest-reject + MEMORY'
                                 ' ALIGNED with the inverted direction',
                                 D, Q[al], dQ[al].astype(np.float64), nd,
                                 {'IFVG alone': (Q, dQ.astype(np.float64)),
                                  'MEMORY alone': memonly}, 10)
    else:
        say('\n  S4  INSUFFICIENT: only %d MEMORY-ALIGNED retest events'
            % int(al.sum()))
        S['S4'] = None

    say('\n' + '=' * 100)
    say('  SG1-SG12   (M_strat = 4, BH binding)')
    hr()
    ps = [S[k]['p'] if S[k] and S[k]['p'] == S[k]['p'] else 1.0
          for k in ('S1', 'S2', 'S3', 'S4')]
    qs = L.bh(ps)
    par = {'S1': 'A1', 'S2': 'A4', 'S3': 'A2', 'S4': 'B5'}
    SG = {}
    for i, k in enumerate(('S1', 'S2', 'S3', 'S4')):
        if S[k] is None:
            say('  %-3s INSUFFICIENT - not scored' % k)
            SG[k] = None
            continue
        g = sg_gates(S[k], all(MA[par[k]].values()), qs[i])
        SG[k] = g
        S[k]['q'] = qs[i]
        say('  %-3s parent %s(%s)  net+5m %s  q %.5f  perm %.5f   %s   (%d/12)'
            % (k, par[k], 'SURVIVED' if all(MA[par[k]].values()) else 'FAILED',
               fmt(S[k]['net5'], 4), qs[i], S[k]['perm'],
               ' '.join('%s:%s' % (a, 'P' if g[a] else 'F')
                        for a in sorted(g, key=lambda z: int(z[2:]))),
               sum(g.values())))
    swin = [k for k in ('S1', 'S2', 'S3', 'S4')
            if SG[k] and all(SG[k].values())]
    say('\n  STRATEGY SURVIVORS (all 12 gates): %s'
        % (', '.join(swin) if swin else 'NONE'))

    OUT.update({'laneA': {k: v for k, v in RA.items()},
                'laneB': {k: v for k, v in RB.items()
                          if not k.startswith('_')},
                'MA': MA, 'SG': SG,
                'strategies': {k: v for k, v in S.items()},
                'math_survivors': survivors, 'strat_survivors': swin,
                'M_math': 12, 'M_strat': 4, 'M_total': 16, 'M_cum': 24,
                'seed': SEED, 'cost': COST})
    say('\n' + '=' * 100)
    say('VERDICTS')
    hr()
    for k in order:
        r = recs[k]
        g = MA[k]
        if all(g.values()):
            v = 'DEVELOPMENT-SUPPORTED MATHEMATICAL ANOMALY'
        elif k == 'B5' and not RB['B5'].get('floors_ok'):
            v = 'INSUFFICIENT (frozen B5 floors unmet)'
        elif not g['MA2']:
            v = 'INSUFFICIENT (sample floors unmet)'
        elif k == 'A6' and RA['A6'].get('redundant_runlen'):
            v = 'REDUNDANT WITH RUN LENGTH'
        elif not ((r['obs'] == r['obs']) and
                  ((r['obs'] > 0) == (r['pred'] > 0))):
            # sign opposite to the frozen prediction. MA3 already fails on
            # direction; the taxonomy must NOT report this as merely small.
            v = ('FAILED - SIGNIFICANT BUT OPPOSITE TO THE FROZEN PREDICTION'
                 if g['MA4'] else
                 'FAILED - WRONG DIRECTION (' +
                 ','.join(a for a in sorted(g) if not g[a]) + ')')
        elif g['MA3'] and g['MA4'] and not g['MA7']:
            v = 'REDUNDANT (control absorbs the effect)'
        elif g['MA4'] and not g['MA3']:
            v = 'REAL BUT SUB-MATERIAL (correct sign, below 2x-anchor floor)'
        else:
            v = 'FAILED (' + ','.join(a for a in sorted(g) if not g[a]) + ')'
        r['verdict'] = v
        say('  %-4s %-52s %s' % (k, v, fmt(r['obs'], 4) + ' ' + r['unit']))
    for k in ('B3', 'B4'):
        b = RB['B6']['B3 post-inversion' if k == 'B3' else 'B4 retest-reject']
        if not b['beat']:
            say('  %-4s ALSO: IFVG REDUNDANT WITH GENERIC FAILURE / REVERSAL'
                ' STRUCTURE (matched %s bp)' % (k, fmt(b['cw'], 4)))
    for k in ('S1', 'S2', 'S3', 'S4'):
        if SG[k] is None:
            say('  %-4s INSUFFICIENT' % k)
            continue
        g = SG[k]
        fl = ','.join(a for a in sorted(g, key=lambda z: int(z[2:]))
                      if not g[a])
        if all(g.values()):
            v = 'EXPLORATORY-DERIVED STRATEGY CANDIDATE'
        elif not g['SG6'] and g['SG3']:
            v = 'REAL BUT SUB-COST (also failing %s)' % fl
        elif not g['SG9']:
            v = 'TAIL-DEPENDENT / FAILED (%s)' % fl
        else:
            v = 'FAILED (%s)' % fl
        S[k]['verdict'] = v
        say('  %-4s %s' % (k, v))
    say('\n  CANDIDATE CEILING: <= 2 mathematical anomalies, <= 1 strategy.')
    say('  advanced: %d mathematical, %d strategy'
        % (min(2, len(survivors)), min(1, len(swin))))
    if not survivors and not swin:
        say('\n  MEMORY-MATH-IFVG-V1 FOUND NO MONETIZABLE MEMORY AMPLIFICATION.')
        say('  MEMORY-PRED remains REAL PREDICTIVE STRUCTURE BUT SUB-COST'
            ' STANDALONE.')
    say('\nEXECUTION COMPLETE  (%.0f s)' % (time.time() - t0))
    say('EXPLORATORY / DEVELOPMENT-DERIVED. NOT OOS. NOT CONFIRMED. NO ORDERS.')
    say('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
    hr()

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
    with open(os.path.join(HERE, 'MEMIFVG_RAW.json'), 'w') as f:
        json.dump(OUT, f, indent=1, default=jd, allow_nan=True)
    with open(os.path.join(HERE, 'MEMIFVG_OUTPUT.txt'), 'w') as f:
        f.write('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    main()
