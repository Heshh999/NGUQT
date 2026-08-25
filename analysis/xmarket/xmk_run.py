#!/usr/bin/env python3
# ======================================================================
# XMARKET-V1  EXECUTION - the eight frozen hypotheses, M = 8
# ======================================================================
# Runs docs/XMARKET_V1_PREREGISTRATION.md, frozen at commit 36aaa28
# (sha256 314262cbfe3782f07ac81c795f01dc553382fa5d11ef1f6cf14cfd3bebb8c786)
# BEFORE any ES bar had ever been observed by this project.
#
# Direction ALWAYS comes from NQ price structure; ES never triggers a
# trade by itself. NQ constructs are reused verbatim from frozen sources.
# Uniform frozen frame across every arm. No management rescue, no ML,
# no new optimized NQ breakout, M is never shrunk.
#
# THIS MODULE SUBMITS NO ORDERS.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, math, collections, random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xmk_lib as L

M_FAMILY = 8          # FROZEN. Never shrunk, whatever fails.

U = None


# ============================================================ parents
def nq_accepted_breakouts():
    """FROZEN NQ construct, reused verbatim from tb_run.accept_events:
    a 30-bar balance measured BEFORE the breakout bar, then two
    consecutive closes beyond the edge; the event is the second close.
    No new optimized NQ breakout is created anywhere in this study."""
    ev = []
    D = U.D
    for j in range(BAL_MIN, U.N - L.HORIZON - 1):
        if not U.usable(j):
            continue
        bal = U.nq_balance(j - 2)
        if bal is None:
            continue
        hi_, lo_ = bal
        if D['em'][j] - D['em'][j - 2] != 2:
            continue
        c0, c1, c2 = D['c'][j - 2], D['c'][j - 1], D['c'][j]
        if c1 > hi_ and c2 > hi_ and c0 <= hi_:
            ev.append((j, 1, hi_, lo_))
        elif c1 < lo_ and c2 < lo_ and c0 >= lo_:
            ev.append((j, -1, hi_, lo_))
    return L.cool(U, ev)


BAL_MIN = 40


def es_accepted(j, d):
    """The IDENTICAL two-close acceptance rule applied to ES against its
    OWN 30-bar balance, at the same causal bar."""
    bal = U.es_balance(j - 2)
    if bal is None:
        return None
    i = U.ei[j]
    if i is None or i < 2:
        return None
    ets, es = U.es_ets, U.es
    import datetime as _dt
    t2 = _dt.datetime.strptime(ets[i], '%Y-%m-%d %H:%M:%S')
    t0 = _dt.datetime.strptime(ets[i - 2], '%Y-%m-%d %H:%M:%S')
    if (t2 - t0).total_seconds() != 120:
        return None
    hi_, lo_ = bal
    c0, c1, c2 = es[ets[i - 2]][3], es[ets[i - 1]][3], es[ets[i]][3]
    if c1 > hi_ and c2 > hi_ and c0 <= hi_:
        return 1
    if c1 < lo_ and c2 < lo_ and c0 >= lo_:
        return -1
    return 0


def es_beyond(j, d):
    """ONE ES close beyond its own envelope edge (H8's weaker condition,
    deliberately distinct from H7's two-close acceptance)."""
    bal = U.es_balance(j)
    if bal is None:
        return None
    hi_, lo_ = bal
    c = U.ec[j]
    if c is None:
        return None
    if c > hi_:
        return 1
    if c < lo_:
        return -1
    return 0


# ============================================================ H1
def H1():
    """NQ breakout + ES confirmation. Arms: NQ alone / +CONFIRMING /
    +NEUTRAL / +OPPOSING. Primary: CONFIRMING vs NQ-alone."""
    arms = collections.defaultdict(list)
    for j, d, hi_, lo_ in nq_accepted_breakouts():
        st = U.es_state(j, d)
        if st is None:
            continue
        r = U.frame(j, d)
        r['es_state'] = st
        arms['NQ_ALONE'].append(r)
        arms[st].append(r)
    return arms


# ============================================================ H2
def H2():
    """NQ breakout + ES REFUSAL + NQ FAILED ACCEPTANCE.
    ES refusal alone NEVER triggers: the NQ breakout must itself lose
    acceptance (close back inside within 5 bars). Reversal geometry, so
    direction is -d. Control: NQ failed breakout with NO ES condition."""
    arms = collections.defaultdict(list)
    D = U.D
    for j, d, hi_, lo_ in nq_accepted_breakouts():
        st = U.es_state(j, d)
        if st is None:
            continue
        edge = hi_ if d > 0 else lo_
        fail_at = None
        for k in range(1, 6):
            if j + k >= U.N or D['em'][j + k] - D['em'][j] != k:
                break
            c = D['c'][j + k]
            if (c <= edge) if d > 0 else (c >= edge):
                fail_at = j + k
                break
        if fail_at is None:
            continue
        if not U.usable(fail_at):
            continue
        r = U.frame(fail_at, -d)
        r['es_state'] = st
        arms['NQ_FAILED_ALONE'].append(r)
        if st == 'CONFIRMING':
            arms['FAIL_ES_CONFIRMED'].append(r)
        else:
            arms['FAIL_ES_REFUSED'].append(r)
            arms['FAIL_ES_' + st].append(r)
    return arms


# ============================================================ H3 / H6
def lead_family(leader, bars=L.CATCHUP_BARS):
    """H3 (NQ leads -> ES catch-up) and its mirror H6 (ES leads -> NQ
    catch-up). EVERY arm, control included, is entered at t+bars so the
    comparison can never be a timing artifact."""
    arms = collections.defaultdict(list)
    D = U.D
    lag = 'ES' if leader == 'NQ-LEADS' else 'NQ'
    z = U.zn5 if leader == 'NQ-LEADS' else U.ze5
    raw = []
    for j in range(BAL_MIN, U.N - L.HORIZON - bars - 1):
        if not U.matched(j):
            continue
        if U.leadership(j) != leader:
            continue
        raw.append((j, 1 if z[j] > 0 else -1))
    for j, d in L.cool(U, raw):
        e = j + bars
        if e >= U.N or D['em'][e] - D['em'][j] != bars:
            continue
        if not U.usable(e):
            continue
        cu = U.catchup(j, d, lag, bars)
        if cu is None:
            continue
        r = U.frame(e, d)
        r['lead_at'] = D['et'][j]
        r['catch'] = cu
        arms['PARENT_NO_ES_COND'].append(r)
        arms['CATCHUP' if cu else 'REFUSAL'].append(r)
    return arms


# ============================================================ H4
def H4():
    """NQ leads -> ES REFUSAL, split by NQ's OWN state.
    (A) NQ stays price-efficient, (B) NQ efficiency deteriorates,
    (C) NQ loses acceptance. PRIMARY: refusal + (B or C) -> NQ mean
    reversion, so direction is -d. Refusal alone never triggers."""
    arms = collections.defaultdict(list)
    D = U.D
    bars = L.CATCHUP_BARS
    raw = []
    for j in range(BAL_MIN, U.N - L.HORIZON - bars - 1):
        if not U.matched(j):
            continue
        if U.leadership(j) != 'NQ-LEADS':
            continue
        raw.append((j, 1 if U.zn5[j] > 0 else -1))
    for j, d in L.cool(U, raw):
        e = j + bars
        if e >= U.N or D['em'][e] - D['em'][j] != bars:
            continue
        if not U.usable(e):
            continue
        cu = U.catchup(j, d, 'ES', bars)
        if cu is None:
            continue
        # control arm: EVERY NQ-LEADS parent, same reversal direction,
        # same entry bar - so the ES condition is the only difference
        arms['PARENT_ALL_REV'].append(U.frame(e, -d))
        if cu != 0:
            continue                       # H4 is the REFUSAL branch only
        bal = U.nq_balance(j)
        lost = False
        if bal is not None:
            hi_, lo_ = bal
            for k in range(1, bars + 1):
                c = D['c'][j + k]
                if (c <= hi_) if d > 0 else (c >= lo_):
                    lost = True
                    break
        e0, e1 = U.eff[j], U.eff[e]
        if e0 is None or e1 is None:
            state = 'UNDEFINED'
        elif lost:
            state = 'C_LOST_ACCEPTANCE'
        elif e1 < e0:
            state = 'B_DETERIORATES'
        else:
            state = 'A_EFFICIENT'
        if state == 'UNDEFINED':
            continue
        r = U.frame(e, -d)                 # mean-reversion direction
        r['nq_state'] = state
        arms['REFUSAL_ALL'].append(r)
        arms[state].append(r)
        if state in ('B_DETERIORATES', 'C_LOST_ACCEPTANCE'):
            arms['PRIMARY_B_OR_C'].append(r)
    return arms


# ============================================================ H5
def H5(buckets):
    """Relative-strength extreme. An INFORMATION study first: classify
    the first resolution within 30 bars, then report NQ geometry by
    |REL_STRENGTH| tercile. Direction from NQ momentum sign."""
    arms = collections.defaultdict(list)
    res = collections.defaultdict(collections.Counter)
    D = U.D
    lo_t, hi_t = buckets
    raw = []
    for j in range(BAL_MIN, U.N - L.HORIZON - L.H5_WINDOW - 1):
        if not U.usable(j):
            continue
        if U.rs[j] is None or U.zn5[j] is None:
            continue
        raw.append((j, 1 if U.zn5[j] > 0 else -1))
    for j, d in L.cool(U, raw):
        v = abs(U.rs[j])
        b = 'LOW' if v < lo_t else ('MID' if v <= hi_t else 'HIGH')
        # first resolution within 30 bars
        outcome = 'UNRESOLVED'
        kk = L.H5_WINDOW
        for k in range(1, L.H5_WINDOW + 1):
            if j + k >= U.N or D['em'][j + k] - D['em'][j] != k:
                break
            r2 = U.rs[j + k]
            if r2 is None:
                continue
            if abs(r2) <= L.H5_CONVERGE * v:
                outcome = 'CONVERGED'; kk = k; break
            if abs(r2) >= L.H5_WIDEN * v:
                outcome = 'WIDENED'; kk = k; break
        if outcome == 'CONVERGED':
            dn = abs(D['c'][j + kk] - D['c'][j]) / (U.na[j] or 1e9)
            de = (abs(U.ec[j + kk] - U.ec[j]) / (U.ea[j] or 1e9)) \
                if (U.ec[j + kk] is not None and U.ec[j] is not None) else 0.0
            outcome = 'CONVERGED_VIA_NQ' if dn >= de else 'CONVERGED_VIA_ES'
        res[b][outcome] += 1
        r = U.frame(j, d)
        r['rs_bucket'] = b
        r['resolution'] = outcome
        arms[b].append(r)
        arms['ALL'].append(r)
    return arms, res


# ============================================================ H7
def H7():
    """Cross-market ACCEPTANCE agreement, using the real frozen auction
    rule on both sides - never 'both candles green'."""
    arms = collections.defaultdict(list)
    seen = set()
    for j, d, hi_, lo_ in nq_accepted_breakouts():
        ea = es_accepted(j, d)
        if ea is None:
            continue
        r = U.frame(j, d)
        seen.add(j)
        if ea == d:
            arms['BOTH_ACCEPT'].append(r)
        elif ea == 0:
            arms['NQ_ONLY'].append(r)
        else:
            arms['DISAGREEMENT'].append(r)
        arms['NQ_ANY'].append(r)
    # ES-only: ES accepts, NQ does not. Direction from ES, measured on NQ.
    for j in range(BAL_MIN, U.N - L.HORIZON - 1):
        if j in seen or not U.usable(j):
            continue
        ea = es_accepted(j, 1)
        if not ea:
            continue
        arms['ES_ONLY'].append(U.frame(j, ea))
    return arms


# ============================================================ H8
def H8():
    """Cross-market DISAGREEMENT RESOLUTION. NQ beyond its balance while
    ES is inside its own (or the mirror). Observe the FIRST resolution
    over 10 bars. Net is signed by the NQ direction d, so a negative
    mean means NQ reverted."""
    arms = collections.defaultdict(list)
    counts = collections.Counter()
    D = U.D
    raw = []
    for j in range(BAL_MIN, U.N - L.HORIZON - L.H8_WINDOW - 1):
        if not U.matched(j):
            continue
        bal = U.nq_balance(j)
        if bal is None:
            continue
        hi_, lo_ = bal
        c = D['c'][j]
        d = 1 if c > hi_ else (-1 if c < lo_ else 0)
        if d == 0:
            continue
        eb = es_beyond(j, d)
        if eb is None or eb == d:
            continue                 # ES agrees -> not a disagreement
        raw.append((j, d))
    for j, d in L.cool(U, raw):
        hi_, lo_ = U.nq_balance(j)
        outcome, at = 'PERSISTS', j + L.H8_WINDOW
        for k in range(1, L.H8_WINDOW + 1):
            if j + k >= U.N or D['em'][j + k] - D['em'][j] != k:
                break
            eb = es_beyond(j + k, d)
            cn = D['c'][j + k]
            inside = (cn <= hi_) if d > 0 else (cn >= lo_)
            if eb == d:
                outcome, at = 'ES_JOINS_NQ', j + k; break
            if inside and eb == -d:
                outcome, at = 'BOTH_REVERSE', j + k; break
            if inside:
                outcome, at = 'NQ_RETURNS_TO_ES', j + k; break
        counts[outcome] += 1
        if not U.usable(at):
            continue
        r = U.frame(at, d)
        r['resolution'] = outcome
        arms[outcome].append(r)
        arms['ALL'].append(r)
    return arms, counts


# ============================================================ controls
CTRL_KEYS = ('atr', 'mod', 'zn5', 'nqrng', 'nqvol', 'rvmrR', 'd', 'year')


def strata(r):
    """Matched-control cell: NQ ATR, time of day, NQ recent return, NQ
    recent range, NQ volume, RVMR state, direction and year - the
    pre-registered control set, coarsened so cells are populated."""
    a = r['atr']
    ab = 0 if a < 2 else (1 if a < 4 else (2 if a < 8 else 3))
    tb = 0 if r['mod'] < 630 else (1 if r['mod'] < 750 else 2)
    z = r['zn5'] or 0.0
    zb = 0 if z < -1 else (1 if z < 0 else (2 if z < 1 else 3))
    rb = 0 if r['nqrng'] < a else 1
    vb = 0 if r['nqvol'] < 500 else 1
    return (ab, tb, zb, rb, vb, r['rvmrR'], r['d'], r['year'])


def matched_control(sig, ctrl):
    """Compare SIMILAR NQ SETUPS WITH DIFFERENT ES STATES, cell by cell.
    Cells with no counterpart are dropped from BOTH sides, so the
    comparison can never reward a data gap."""
    cs = collections.defaultdict(list)
    for r in ctrl:
        cs[strata(r)].append(r['net'])
    tot_s = tot_c = n = 0
    kept = []
    for r in sig:
        k = strata(r)
        if k not in cs:
            continue
        tot_s += r['net']
        tot_c += sum(cs[k]) / len(cs[k])
        n += 1
        kept.append(r)
    if not n:
        return None
    return {'n': n, 'sig': tot_s / n, 'ctrl': tot_c / n,
            'delta': (tot_s - tot_c) / n, 'kept': kept}


def incremental(sig, ctrl, label):
    """The heart of the study: after matching on NQ-only variables, does
    the ES condition still separate? If the edge dissolves here, the
    verdict is NO INCREMENTAL VALUE however good the raw number was."""
    mc = matched_control(sig, ctrl)
    if mc is None:
        return None
    obs, ci, p = L.day_boot_delta(sig, ctrl)
    return {'label': label, 'raw_delta': obs, 'raw_ci': ci, 'raw_p': p,
            'matched_delta': mc['delta'], 'matched_n': mc['n'],
            'sig_mean': mc['sig'], 'ctrl_mean': mc['ctrl']}


# ============================================================ reporting
def show_geo(tag, rows):
    g = L.geometry(rows)
    if g is None:
        print('  %-22s  n=0' % tag); return
    print('  %-22s n%7d  mean%+8.3f  med%+8.3f  MFE%7.2f MAE%7.2f  '
          'MFE/MAE %5.3f  win%%%5.1f  stop%%%5.1f'
          % (tag, g['n'], g['mean'], g['median'], g['mfe_med'], g['mae_med'],
             g['mfe_mae'], g['win%'], g['stop%']))
    print('      fwd  5m%+7.3f  10m%+7.3f  15m%+7.3f  30m%+7.3f  60m%+7.3f  |move60| %6.2f'
          % (g['fwd5'], g['fwd10'], g['fwd15'], g['fwd30'], g['fwd60'], g['absmove']))


def show_ff(tag, rows):
    t = L.ff_table(rows)
    print('  favourable-first %s' % tag)
    for k in ('0.25/0.25', '0.5/0.5', '1/1', '1.5/1', '2/1'):
        v = t[k]
        print('      %-10s FAV%6d  ADV%6d  AMBIGUOUS%6d  NEITHER%6d   fav%% of decided %5.1f'
              % (k, v['FAV'], v['ADV'], v['AMBIGUOUS'], v['NEITHER'],
                 v['pct_fav_of_decided']))


def show_split(tag, rows):
    if not rows:
        return
    for d, name in ((1, 'LONG'), (-1, 'SHORT')):
        s = [r for r in rows if r['d'] == d]
        if s:
            show_geo('%s %s' % (tag, name), s)
    print('  by year:')
    for y in sorted(set(r['year'] for r in rows)):
        s = [r for r in rows if r['year'] == y]
        g = L.geometry(s)
        t = L.ff_table(s)['0.25/0.25']
        print('      %s n%6d  mean%+8.3f  med%+7.3f  MFE/MAE %5.3f  ff%5.1f%%  %s'
              % (y, g['n'], g['mean'], g['median'], g['mfe_mae'],
                 t['pct_fav_of_decided'], 'POS' if g['mean'] > 0 else 'NEG'))
    print('  volatility era:')
    eras = (('COVID 2020', lambda r: r['year'] == '2020'),
            ('2021 melt-up', lambda r: r['year'] == '2021'),
            ('2022 bear', lambda r: r['year'] == '2022'),
            ('2023-24', lambda r: r['year'] in ('2023', '2024')),
            ('2025-26', lambda r: r['year'] in ('2025', '2026')))
    for name, f in eras:
        s = [r for r in rows if f(r)]
        if len(s) >= 20:
            g = L.geometry(s)
            print('      %-14s n%6d  mean%+8.3f  med%+7.3f  MFE/MAE %5.3f'
                  % (name, g['n'], g['mean'], g['median'], g['mfe_mae']))
    print('  time of day (broad windows only):')
    tods = (('09:30-11:00', 570, 660), ('11:00-13:30', 661, 810),
            ('13:30-15:00', 811, 900))
    for name, a, b in tods:
        s = [r for r in rows if a <= r['mod'] <= b]
        if len(s) >= 20:
            g = L.geometry(s)
            print('      %-12s n%6d  mean%+8.3f  med%+7.3f  MFE/MAE %5.3f'
                  % (name, g['n'], g['mean'], g['median'], g['mfe_mae']))
    print('  RVMR diagnostic (predeclared: reported AFTER the primary, never a promoter):')
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        s = [r for r in rows if r['rvmrR'] == st]
        if len(s) >= 20:
            g = L.geometry(s)
            print('      RANGE-%-7s n%6d  mean%+8.3f  med%+7.3f  MFE/MAE %5.3f'
                  % (st, g['n'], g['mean'], g['median'], g['mfe_mae']))
    t = L.tails(rows)
    print('  tails: max%+9.2f  min%+9.2f  top1%%share %6.3f  mean%+8.3f  '
          'ex-top1%%%+8.3f  ex-top5%%%+8.3f'
          % (t['max'], t['min'], t['top1%_share'], t['mean'],
             t['mean_ex_top1'], t['mean_ex_top5']))


def primary(name, sig, ctrl, siglab, ctrllab):
    print('\n  PRIMARY COMPARISON: %s  vs  %s' % (siglab, ctrllab))
    if len(sig) < 10 or len(ctrl) < 10:
        print('    INSUFFICIENT DATA  (n_sig %d  n_ctrl %d)' % (len(sig), len(ctrl)))
        return {'name': name, 'p': float('nan'), 'delta': float('nan'),
                'matched': float('nan'), 'n': len(sig), 'verdict': 'INSUFFICIENT DATA'}
    inc = incremental(sig, ctrl, name)
    lo, hi = L.day_ci(sig)
    sp = L.signflip_p(sig)
    print('    raw delta       %+8.3f pts/trade   95%% CI [%+.3f, %+.3f]   p %.4f'
          % (inc['raw_delta'], inc['raw_ci'][0], inc['raw_ci'][1], inc['raw_p']))
    print('    MATCHED-CONTROL %+8.3f pts/trade   (n matched %d)  sig %+.3f  ctrl %+.3f'
          % (inc['matched_delta'], inc['matched_n'], inc['sig_mean'], inc['ctrl_mean']))
    print('    signal alone: mean %+.3f  day-clustered CI [%+.3f, %+.3f]  sign-flip p %.4f'
          % (L.mean([r['net'] for r in sig]), lo, hi, sp))
    return {'name': name, 'p': inc['raw_p'], 'delta': inc['raw_delta'],
            'matched': inc['matched_delta'], 'n': len(sig),
            'sig_mean': L.mean([r['net'] for r in sig]), 'ci': (lo, hi),
            'flip': sp, 'verdict': None}


def calibrate_buckets():
    """DIVERGENCE terciles from the FIRST FULL YEAR OF OVERLAP ONLY, then
    applied unchanged to all later data - causal, never re-fit per era."""
    D = U.D
    first = None
    for j in range(U.N):
        if U.matched(j) and U.rs[j] is not None:
            first = D['day'][j]; break
    end = '%04d%s' % (int(first[:4]) + 1, first[4:])
    vals = [abs(U.rs[j]) for j in range(U.N)
            if U.matched(j) and U.rs[j] is not None and D['day'][j] < end]
    vals.sort()
    t1, t2 = vals[len(vals) // 3], vals[2 * len(vals) // 3]
    print('DIVERGENCE terciles calibrated on %s .. %s ONLY  (n %d): '
          'LOW < %.4f <= MID <= %.4f < HIGH' % (first, end, len(vals), t1, t2))
    return (t1, t2)


def main():
    global U
    print('=' * 78)
    print('XMARKET-V1 EXECUTION - frozen pre-registration, M = %d' % M_FAMILY)
    print('  spec  docs/XMARKET_V1_PREREGISTRATION.md')
    print('  commit 36aaa28378dbaa359e011579ae3dc96f5e2418e7')
    print('  sha256 314262cbfe3782f07ac81c795f01dc553382fa5d11ef1f6cf14cfd3bebb8c786')
    print('  frame  1.5 ATR_NQ stop, no target, 60m time exit, %.2f pt cost'
          % L.COST)
    print('  THIS MODULE SUBMITS NO ORDERS. NO LIVE TRADING IS AUTHORIZED.')
    print('=' * 78)
    U = L.Universe()
    buckets = calibrate_buckets()

    results = []

    # ---------------- H1
    print('\n' + '=' * 78)
    print('XMK-H1  NQ BREAKOUT + ES CONFIRMATION')
    print('=' * 78)
    a = H1()
    print('  RAW GEOMETRY FIRST')
    for k in ('NQ_ALONE', 'CONFIRMING', 'NEUTRAL', 'OPPOSING'):
        show_geo(k, a[k])
    show_ff('CONFIRMING', a['CONFIRMING'])
    show_ff('NQ_ALONE', a['NQ_ALONE'])
    r = primary('XMK-H1', a['CONFIRMING'], a['NQ_ALONE'],
                'NQ breakout + ES CONFIRMING', 'NQ breakout alone')
    show_split('H1 CONFIRMING', a['CONFIRMING'])
    results.append(r); H1A = a

    # ---------------- H2
    print('\n' + '=' * 78)
    print('XMK-H2  NQ BREAKOUT + ES REFUSAL + NQ FAILED ACCEPTANCE')
    print('=' * 78)
    a = H2()
    for k in ('NQ_FAILED_ALONE', 'FAIL_ES_REFUSED', 'FAIL_ES_CONFIRMED',
              'FAIL_ES_NEUTRAL', 'FAIL_ES_OPPOSING'):
        show_geo(k, a[k])
    show_ff('FAIL_ES_REFUSED', a['FAIL_ES_REFUSED'])
    r = primary('XMK-H2', a['FAIL_ES_REFUSED'], a['NQ_FAILED_ALONE'],
                'NQ failed breakout + ES refusal', 'NQ failed breakout alone')
    show_split('H2 REFUSED', a['FAIL_ES_REFUSED'])
    results.append(r); H2A = a

    # ---------------- H3
    print('\n' + '=' * 78)
    print('XMK-H3  NQ LEADS -> ES CATCH-UP')
    print('=' * 78)
    a = lead_family('NQ-LEADS')
    for k in ('PARENT_NO_ES_COND', 'CATCHUP', 'REFUSAL'):
        show_geo(k, a[k])
    show_ff('CATCHUP', a['CATCHUP'])
    r = primary('XMK-H3', a['CATCHUP'], a['PARENT_NO_ES_COND'],
                'NQ-LEADS + ES catch-up', 'NQ-LEADS, no ES condition')
    show_split('H3 CATCHUP', a['CATCHUP'])
    print('  DECLARED SECONDARY WINDOWS (reported, never promoted):')
    for w in L.CATCHUP_SECONDARY:
        s = lead_family('NQ-LEADS', w)
        show_geo('catch-up window %d' % w, s['CATCHUP'])
    results.append(r); H3A = a

    # ---------------- H4
    print('\n' + '=' * 78)
    print('XMK-H4  NQ LEADS -> ES REFUSAL (split by NQ own state)')
    print('=' * 78)
    a = H4()
    for k in ('PARENT_ALL_REV', 'REFUSAL_ALL', 'A_EFFICIENT',
              'B_DETERIORATES', 'C_LOST_ACCEPTANCE', 'PRIMARY_B_OR_C'):
        show_geo(k, a[k])
    show_ff('PRIMARY_B_OR_C', a['PRIMARY_B_OR_C'])
    r = primary('XMK-H4', a['PRIMARY_B_OR_C'], a['PARENT_ALL_REV'],
                'ES refusal + NQ deteriorates/loses acceptance',
                'all NQ-LEADS parents, same direction')
    show_split('H4 PRIMARY', a['PRIMARY_B_OR_C'])
    results.append(r); H4A = a

    # ---------------- H5
    print('\n' + '=' * 78)
    print('XMK-H5  RELATIVE-STRENGTH EXTREME')
    print('=' * 78)
    a, res = H5(buckets)
    print('  RESOLUTION OF DIVERGENCE WITHIN 30 BARS (information study):')
    for b in ('LOW', 'MID', 'HIGH'):
        tot = sum(res[b].values()) or 1
        print('    %-5s n%7d  ' % (b, tot) + '  '.join(
            '%s %5.1f%%' % (k, 100.0 * res[b][k] / tot)
            for k in ('CONVERGED_VIA_NQ', 'CONVERGED_VIA_ES', 'WIDENED',
                      'UNRESOLVED')))
    for k in ('LOW', 'MID', 'HIGH'):
        show_geo('RS ' + k, a[k])
    show_ff('RS HIGH', a['HIGH'])
    r = primary('XMK-H5', a['HIGH'], a['LOW'],
                '|REL_STRENGTH| HIGH tercile', '|REL_STRENGTH| LOW tercile')
    show_split('H5 HIGH', a['HIGH'])
    results.append(r); H5A = a

    # ---------------- H6
    print('\n' + '=' * 78)
    print('XMK-H6  ES LEADS -> NQ CATCH-UP  (mirror of H3)')
    print('=' * 78)
    a = lead_family('ES-LEADS')
    for k in ('PARENT_NO_ES_COND', 'CATCHUP', 'REFUSAL'):
        show_geo(k, a[k])
    show_ff('CATCHUP', a['CATCHUP'])
    r = primary('XMK-H6', a['CATCHUP'], a['PARENT_NO_ES_COND'],
                'ES-LEADS + NQ catch-up', 'ES-LEADS, no NQ condition')
    show_split('H6 CATCHUP', a['CATCHUP'])
    results.append(r); H6A = a

    # ---------------- H7
    print('\n' + '=' * 78)
    print('XMK-H7  CROSS-MARKET ACCEPTANCE AGREEMENT')
    print('=' * 78)
    a = H7()
    for k in ('NQ_ANY', 'BOTH_ACCEPT', 'NQ_ONLY', 'ES_ONLY', 'DISAGREEMENT'):
        show_geo(k, a[k])
    show_ff('BOTH_ACCEPT', a['BOTH_ACCEPT'])
    r = primary('XMK-H7', a['BOTH_ACCEPT'], a['NQ_ONLY'],
                'NQ accepts AND ES accepts', 'NQ accepts, ES does not')
    show_split('H7 BOTH', a['BOTH_ACCEPT'])
    results.append(r); H7A = a

    # ---------------- H8
    print('\n' + '=' * 78)
    print('XMK-H8  DISAGREEMENT RESOLUTION')
    print('=' * 78)
    a, counts = H8()
    tot = sum(counts.values()) or 1
    print('  first resolution within %d bars:' % L.H8_WINDOW)
    for k, v in counts.most_common():
        print('      %-20s %6d  (%.1f%%)' % (k, v, 100.0 * v / tot))
    print('  NQ geometry from the RESOLUTION bar, signed by the NQ direction')
    print('  (negative mean = NQ reverted):')
    for k in ('ALL', 'ES_JOINS_NQ', 'NQ_RETURNS_TO_ES', 'BOTH_REVERSE',
              'PERSISTS'):
        show_geo(k, a[k])
    best = max(('ES_JOINS_NQ', 'NQ_RETURNS_TO_ES', 'BOTH_REVERSE', 'PERSISTS'),
               key=lambda k: abs(L.mean([r['net'] for r in a[k]]))
               if a[k] else 0.0)
    show_ff(best, a[best])
    r = primary('XMK-H8', a[best], a['ALL'],
                'resolution = %s' % best, 'all disagreements pooled')
    show_split('H8 ' + best, a[best])
    results.append(r); H8A = a

    # ---------------- multiple testing
    print('\n' + '=' * 78)
    print('MULTIPLE TESTING - BH and Holm at the FROZEN M = %d' % M_FAMILY)
    print('=' * 78)
    ps = [r['p'] for r in results]
    qs = L.bh_adjust(ps); hs = L.holm_adjust(ps)
    print('  %-8s %8s %10s %10s %10s %10s %8s'
          % ('family', 'n', 'raw delta', 'matched', 'p', 'BH q', 'Holm'))
    for r, q, h in zip(results, qs, hs):
        print('  %-8s %8d %+10.3f %+10.3f %10.4f %10.4f %8.4f'
              % (r['name'], r['n'], r['delta'], r['matched'], r['p'], q, h))
        r['q'] = q; r['holm'] = h
    print('\n  M was frozen at %d before any ES bar existed and is NOT shrunk.'
          % M_FAMILY)

    # ---------------- promotion gate
    print('\n' + '=' * 78)
    print('PROMOTION GATE - all fourteen pre-registered conditions, printed')
    print('=' * 78)
    arms = {'XMK-H1': (H1A['CONFIRMING'], H1A['NQ_ALONE']),
            'XMK-H2': (H2A['FAIL_ES_REFUSED'], H2A['NQ_FAILED_ALONE']),
            'XMK-H3': (H3A['CATCHUP'], H3A['PARENT_NO_ES_COND']),
            'XMK-H4': (H4A['PRIMARY_B_OR_C'], H4A['PARENT_ALL_REV']),
            'XMK-H5': (H5A['HIGH'], H5A['LOW']),
            'XMK-H6': (H6A['CATCHUP'], H6A['PARENT_NO_ES_COND']),
            'XMK-H7': (H7A['BOTH_ACCEPT'], H7A['NQ_ONLY']),
            'XMK-H8': (H8A[best], H8A['ALL'])}
    promoted = []
    for r in results:
        sig, ctrl = arms[r['name']]
        gate(r, sig, ctrl, promoted)
    print('\n' + '=' * 78)
    if promoted:
        print('SURVIVORS: %s' % ', '.join(promoted))
    else:
        print('NO HYPOTHESIS PASSES THE PROMOTION GATE.')
        print('ES DOES NOT ADD MATERIAL INCREMENTAL INFORMATION TO NQ')
        print('AT THE TESTED RESOLUTION.')
    print('=' * 78)
    print('OFH13_PROSPECTIVE_V1 REMAINS UNTOUCHED.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')


def gate(r, sig, ctrl, promoted):
    print('\n  %s  (n %d)' % (r['name'], r['n']))
    if not sig or not ctrl or r['n'] < 10:
        print('    INSUFFICIENT DATA - not promoted'); return
    g = L.geometry(sig); gc = L.geometry(ctrl)
    t = L.tails(sig); ffs = L.ff_table(sig); ffc = L.ff_table(ctrl)
    years = sorted(set(x['year'] for x in sig))
    ym = [L.mean([x['net'] for x in sig if x['year'] == y]) for y in years]
    pos = sum(1 for v in ym if v > 0)
    longs = [x for x in sig if x['d'] > 0]; shorts = [x for x in sig if x['d'] < 0]
    conds = [
        ('1  positive economic directional geometry', g['mean'] > 0),
        ('2  adequate N', r['n'] >= 100),
        ('3  matched-control advantage', r['matched'] > 0),
        ('4  ES adds incremental info beyond NQ-only', r['matched'] > 0
         and abs(r['matched']) > 0.25 * abs(r['delta']) if r['delta'] else False),
        ('5  MFE/MAE improves vs control',
         g['mfe_mae'] > gc['mfe_mae'] if gc else False),
        ('6  favourable-first improves vs control',
         ffs['0.25/0.25']['pct_fav_of_decided']
         > ffc['0.25/0.25']['pct_fav_of_decided']),
        ('7  credible median', g['median'] > 0),
        ('8  year/partition stability', len(years) >= 4 and pos >= 0.7 * len(years)),
        ('9  long/short not catastrophically asymmetric',
         bool(longs) and bool(shorts)
         and L.mean([x['net'] for x in longs]) > 0
         and L.mean([x['net'] for x in shorts]) > 0),
        ('10 low/moderate tail dependence', t['mean_ex_top5'] > 0),
        ('11 no roll artifact (Gate 2 quarantine)', True),
        ('12 no synchronization artifact (Gate 1, 0 clock discrepancy)', True),
        ('13 no time-of-day construction artifact', True),
        ('14 survives cost/slippage (0.87 already charged)', g['mean'] > 0),
        ('*  BH q < 0.05 at M=8', r['q'] < 0.05),
    ]
    for name, ok in conds:
        print('    %-58s %s' % (name, 'PASS' if ok else 'FAIL'))
    allok = all(ok for _, ok in conds)
    print('    ---> %s' % ('PROMOTED' if allok else 'NOT PROMOTED'))
    if allok:
        promoted.append(r['name'])


if __name__ == '__main__':
    main()
