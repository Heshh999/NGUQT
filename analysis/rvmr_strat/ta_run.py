#!/usr/bin/env python3
# ======================================================================
# RVMR-STRAT-V1  TRACK A - existing strategies x RVMR interaction
# ======================================================================
# Frozen by docs/RVMR_STRAT_PREREGISTRATION.md. Every strategy is
# harvested from its canonical implementation, completely unchanged, and
# tagged with the causally available RVMR state of its decision bar.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, math, random, statistics, collections, pickle

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../rvmr', '../v41', '../mag'):
    sys.path.insert(0, os.path.join(HERE, p))
import rvmr_spec as RS
import cand_spec as CS
import mag_lib as ML
import mag_run as MG
import red_lib as R
import mrv_run as MRV

COST = 0.87
SEED = 20260825


def part(day):
    return 'U' if day <= '2025-11-01' else ('DEV' if day <= '2026-03-31' else 'IR')


# ------------------------------------------------- RVMR states (certified)
def rvmr_states(B):
    rng = [b['high'] - b['low'] for b in B]
    vol = [b['ofTotalVolume'] for b in B]
    rr = RS.trailing_ratio(rng)
    vr = RS.trailing_ratio(vol)
    return ({b['et']: RS.bucket(rr[i]) for i, b in enumerate(B) if rr[i] is not None},
            {b['et']: RS.bucket(vr[i]) for i, b in enumerate(B) if vr[i] is not None})


# ------------------------------------------------- outcome frame
def frame(B, j, d, atr, stop_px=None):
    """Frozen OFH13 frame: 1.5 ATR (or supplied structural stop), no
    target, 60m time exit. Rich diagnostics."""
    if j + 60 >= len(B) or B[j + 60]['tmin'] - B[j]['tmin'] != 60:
        return None
    px = B[j]['close']
    stop = stop_px if stop_px is not None else px - 1.5 * atr * d
    risk = abs(px - stop)
    if risk < 0.5:                       # degenerate structural stop
        return None
    mfe = mae = 0.0
    t_mfe = t_mae = 0
    net = None; reason = 'TIME'; t_stop = None
    reach = {}
    ff25 = ff1 = None
    for k in range(1, 61):
        c = B[j + k]
        u = (c['high'] - px) * d
        v = (px - c['low']) * d
        if u > mfe: mfe, t_mfe = u, k
        if v > mae: mae, t_mae = v, k
        for rmult in (0.25, 0.5, 1, 1.5, 2, 3, 4, 5):
            if rmult not in reach and mfe >= rmult * risk:
                reach[rmult] = k
        if ff25 is None:
            hu, hd = mfe >= 0.25 * atr, mae >= 0.25 * atr
            ff25 = 'AMBIG' if (hu and hd) else ('FAV' if hu else ('ADV' if hd else None))
        if ff1 is None:
            hu, hd = mfe >= atr, mae >= atr
            ff1 = 'AMBIG' if (hu and hd) else ('FAV' if hu else ('ADV' if hd else None))
        if net is None:
            hit = (c['low'] <= stop) if d > 0 else (c['high'] >= stop)
            if hit:
                net, reason, t_stop = (stop - px) * d - COST, 'STOP', k
    if net is None:
        net = (B[j + 60]['close'] - px) * d - COST
    return {'net': net, 'R': net / risk, 'risk': risk, 'reason': reason,
            'mfe': mfe, 'mae': mae, 'atr': atr, 't_mfe': t_mfe, 't_mae': t_mae,
            't_stop': t_stop, 'reach': reach, 'ff25': ff25 or 'NEITHER',
            'ff1': ff1 or 'NEITHER', 'day': B[j]['day'], 'et': B[j]['et'],
            'part': part(B[j]['day']), 'd': d, 'hour': int(B[j]['et'][11:13])}


# ------------------------------------------------- harvest (canonical)
def harvest(B):
    """Events from canonical implementations, unchanged. Each: (j, d,
    optional struct stop px, struct ref dist)."""
    out = {}
    EV, SIGS, CTX = CS.generate(B)
    assert len(EV['OFH13']) == 133 and len(EV['OFH14']) == 462
    out['A1_OFH13'] = [{'j': e['j'], 'd': e['d'],
                        'sref': abs(e['entry_px'] - (e['meta']['zLo'] if e['d'] > 0
                                                     else e['meta']['zHi']))}
                       for e in EV['OFH13']]
    out['A2_OFH14'] = [{'j': e['j'], 'd': e['d'],
                        'stop_px': e['struct_ref'],
                        'sref': abs(e['entry_px'] - e['struct_ref'])}
                       for e in EV['OFH14']]
    out['A10_G4'] = [{'j': e['j'], 'd': e['d']} for e in EV['G4']]

    # mag-family detectors on the same canonical bars
    ML.build_features(B)
    a4 = MG.mag_dir_h1(B)
    out['A4_ACCEPT_BRK'] = [{'j': e['j'], 'd': e['d']} for e in a4['C_ACCEPT_ANY']]
    a5 = MG.mag_dir_h2(B)
    out['A5_REJECT_BRK'] = [{'j': e['j'], 'd': e['d']} for e in a5['C_REENTRY_ANY']]
    h2, h3, h4 = MG.ovn_family(B)
    out['A9_OVN_RECLAIM'] = [{'j': e['j'], 'd': e['d']} for e in h4['FULL_SWEEP_RECLAIM']]
    o1, o2 = MG.open_family(B)
    out['A8_OPEN_DRIVE'] = [{'j': e['j'], 'd': e['d']} for e in o1['C_DRIVE_ONLY']]

    # mrv-family detectors (their own canonical bar pickles)
    RB = pickle.load(open(R.SCR + '/red_bars.pkl', 'rb'))
    S_ = pickle.load(open(R.SCR + '/mrv_sess.pkl', 'rb'))
    consec = R.make_consec(RB)
    medabs = R.rolling_med_absdelta(RB)
    lows15, highs15 = R.build_swings(RB, 15)
    lo_at = R.level_lookup(lows15)
    hi_at = R.level_lookup(highs15)
    bmap = {b['et']: i for i, b in enumerate(B)}
    def remap(evs, sref_key=None):
        o = []
        for e in evs:
            j = bmap.get(RB[e['j']]['et'])
            if j is not None:
                r = {'j': j, 'd': e['d']}
                o.append(r)
        return o
    out['A3_SWEEP_RECLAIM'] = remap(
        MRV.mr_h3(RB, consec, medabs, lo_at, hi_at, arm='RECLAIM'))
    out['A6_V_RECOVERY'] = remap(MRV.v_h1(RB, consec, mode='FAST'))
    out['A7_MEAN_REV'] = remap(MRV.mr_h2(RB, consec, S_))
    return out


# ------------------------------------------------- metrics
def cellstats(rows):
    if not rows:
        return None
    nets = [r['net'] for r in rows]
    Rs = [r['R'] for r in rows]
    w = [x for x in nets if x > 0]; l = [x for x in nets if x <= 0]
    mfe = statistics.median([r['mfe'] / r['atr'] for r in rows])
    mae = statistics.median([r['mae'] / r['atr'] for r in rows])
    f25 = [r for r in rows if r['ff25'] in ('FAV', 'ADV')]
    reach = {rm: 100.0 * sum(1 for r in rows
                             if rm in r['reach'] and (r['t_stop'] is None
                                                      or r['reach'][rm] <= r['t_stop']))
             / len(rows) for rm in (0.25, 0.5, 1, 1.5, 2, 3, 4, 5)}
    wr_rows = [r for r in rows if r['net'] > 0]
    return {'n': len(rows), 'ev': sum(nets) / len(nets),
            'evR': sum(Rs) / len(Rs), 'wr': 100.0 * len(w) / len(nets),
            'pf': (sum(w) / abs(sum(l))) if l and sum(l) else float('inf'),
            'medR': statistics.median(Rs),
            'aw': sum(w) / len(w) if w else float('nan'),
            'al': sum(l) / len(l) if l else float('nan'),
            'mfe': mfe, 'mae': mae, 'ratio': mfe / mae if mae else float('nan'),
            'ff25': 100.0 * sum(1 for r in f25 if r['ff25'] == 'FAV') / len(f25)
                    if f25 else float('nan'),
            'stop': 100.0 * sum(1 for r in rows if r['reason'] == 'STOP') / len(rows),
            'tmfe': statistics.median([r['t_mfe'] for r in rows]),
            'reach': reach,
            'maxw': max(nets), 'maxl': min(nets),
            'winMFE': statistics.median([r['mfe'] / r['atr'] for r in wr_rows])
                      if wr_rows else float('nan'),
            'winMFE95': sorted([r['mfe'] / r['atr'] for r in wr_rows])[
                int(0.95 * len(wr_rows))] if len(wr_rows) >= 20 else float('nan'),
            'rows': rows}


def day_boot_delta(rowsH, rowsL, iters=20000, seed=SEED):
    """Two-sided day-clustered bootstrap p for EV(H)-EV(L)."""
    if not rowsH or not rowsL:
        return float('nan'), (float('nan'), float('nan'))
    rnd = random.Random(seed)
    bh = collections.defaultdict(list); bl = collections.defaultdict(list)
    for r in rowsH: bh[r['day']].append(r['net'])
    for r in rowsL: bl[r['day']].append(r['net'])
    days = sorted(set(bh) | set(bl))
    ds = []
    for _ in range(iters):
        H, L = [], []
        for _ in days:
            d = days[rnd.randrange(len(days))]
            H.extend(bh.get(d, ())); L.extend(bl.get(d, ()))
        if H and L:
            ds.append(sum(H) / len(H) - sum(L) / len(L))
    ds.sort()
    obs = (sum(r['net'] for r in rowsH) / len(rowsH)
           - sum(r['net'] for r in rowsL) / len(rowsL))
    neg = sum(1 for x in ds if x <= 0) / len(ds)
    p = 2 * min(neg, 1 - neg) + 1.0 / (iters + 1)
    return min(p, 1.0), (ds[int(.025 * len(ds))], ds[int(.975 * len(ds))])


def bh_adjust(ps):
    idx = sorted(range(len(ps)), key=lambda i: (ps[i] != ps[i], ps[i]))
    m = len(ps); q = [None] * m; prev = 1.0
    for rank, i in enumerate(reversed(idx), 1):
        k = m - rank + 1
        v = min(prev, (ps[i] if ps[i] == ps[i] else 1.0) * m / k)
        q[i] = v; prev = v
    return q


# ------------------------------------------------- main
if __name__ == '__main__':
    B = CS.load_merged()
    RRs, VRs = rvmr_states(B)
    ev_all = harvest(B)
    print('TRACK A - harvested (canonical, unchanged):')
    for k in sorted(ev_all):
        print('  %-18s %5d events' % (k, len(ev_all[k])))
    print()

    fam = []          # (label, p, delta, nH, nL)
    csvrows = []
    for name in sorted(ev_all):
        evs = ev_all[name]
        rows = []
        for e in evs:
            j, d = e['j'], e['d']
            b = B[j]
            atr = b.get('atr')
            if not atr or atr <= 0:
                continue
            o = frame(B, j, d, atr, e.get('stop_px'))
            if o is None:
                continue
            o['rb'] = RRs.get(b['et'])
            o['vb'] = VRs.get(b['et'])
            o['sref'] = e.get('sref')
            rows.append(o)
        if len(rows) < 30:
            print('%s  n=%d  INSUFFICIENT SAMPLE\n' % (name, len(rows)))
            continue
        print('=' * 96)
        print('%s   n=%d   (measurement frame identical across states)' % (name, len(rows)))
        allst = cellstats(rows)
        for tool, key in (('RANGE', 'rb'), ('VOLUME', 'vb')):
            by = collections.defaultdict(list)
            for r in rows:
                if r[key]:
                    by[r[key]].append(r)
            tot = sum(len(v) for v in by.values())
            sel = {k2: 100.0 * len(by[k2]) / tot for k2 in by}
            print('  %s  selectivity  L %.0f%%  M %.0f%%  H %.0f%%'
                  % (tool, sel.get('LOW', 0), sel.get('MEDIUM', 0), sel.get('HIGH', 0)))
            cs = {}
            for st in ('LOW', 'MEDIUM', 'HIGH'):
                c = cellstats(by.get(st, []))
                cs[st] = c
                if c:
                    print('    %-6s n %4d  EV %+7.2f  R %+6.3f  WR %4.1f%%  PF %5.2f  '
                          'medR %+6.3f  MFE %4.2f  MAE %4.2f  M/M %4.2f  ff %4.1f%%  '
                          'stop %4.1f%%  P1R %4.1f%%  P2R %4.1f%%  P3R %4.1f%%  wMFE %4.2f'
                          % (st, c['n'], c['ev'], c['evR'], c['wr'], c['pf'],
                             c['medR'], c['mfe'], c['mae'], c['ratio'], c['ff25'],
                             c['stop'], c['reach'][1], c['reach'][2], c['reach'][3],
                             c['winMFE']))
                    csvrows.append(dict(strategy=name, tool=tool, state=st, **{
                        k3: v for k3, v in c.items() if k3 != 'rows'}))
            H, L = by.get('HIGH', []), by.get('LOW', [])
            if len(H) >= 10 and len(L) >= 10:
                p, ci = day_boot_delta(H, L)
                dlt = cs['HIGH']['ev'] - cs['LOW']['ev']
                # controls: within ATR terciles and within hour strata
                def controlled(keyfn):
                    accs, n2 = 0.0, 0
                    groups = collections.defaultdict(lambda: ([], []))
                    for r in H: groups[keyfn(r)][0].append(r['net'])
                    for r in L: groups[keyfn(r)][1].append(r['net'])
                    for g, (hh, ll) in groups.items():
                        if len(hh) >= 5 and len(ll) >= 5:
                            k4 = len(hh) + len(ll)
                            accs += (sum(hh) / len(hh) - sum(ll) / len(ll)) * k4
                            n2 += k4
                    return accs / n2 if n2 else float('nan')
                atrs = sorted(r['atr'] for r in rows)
                t1_, t2_ = atrs[len(atrs) // 3], atrs[2 * len(atrs) // 3]
                c_atr = controlled(lambda r: 0 if r['atr'] <= t1_ else (1 if r['atr'] <= t2_ else 2))
                c_hr = controlled(lambda r: r['hour'])
                print('    HIGH-LOW EV %+7.2f  CI[%+.2f,%+.2f]  p %.4f  '
                      '| ATR-controlled %+6.2f  hour-controlled %+6.2f'
                      % (dlt, ci[0], ci[1], p, c_atr, c_hr))
                # winner-size and loser-severity by state
                for st in ('LOW', 'HIGH'):
                    c = cs[st]
                    if c:
                        wro = [r for r in c['rows'] if r['net'] > 0]
                        lro = [r for r in c['rows'] if r['net'] <= 0]
                        print('      %-4s winners n %3d avg %+7.2f  medMFE %4.2f  '
                              'p95MFE %4.2f | losers n %3d avg %+7.2f  '
                              'losing-MAE %4.2f  full-stop %4.1f%%'
                              % (st, len(wro),
                                 sum(r['net'] for r in wro) / len(wro) if wro else 0,
                                 statistics.median([r['mfe'] / r['atr'] for r in wro])
                                 if wro else float('nan'),
                                 sorted([r['mfe'] / r['atr'] for r in wro])[
                                     int(.95 * len(wro))] if len(wro) >= 20 else float('nan'),
                                 len(lro),
                                 sum(r['net'] for r in lro) / len(lro) if lro else 0,
                                 statistics.median([r['mae'] / r['atr'] for r in lro])
                                 if lro else float('nan'),
                                 100.0 * sum(1 for r in lro if r['reason'] == 'STOP')
                                 / len(lro) if lro else 0))
                # tail preservation of an implied "trade only BEST state" filter
                best = max(('LOW', 'MEDIUM', 'HIGH'),
                           key=lambda s2: cs[s2]['ev'] if cs[s2] else -1e9)
                top10 = sorted(rows, key=lambda r: -r['net'])[:10]
                kept = sum(1 for r in top10 if r[key] == best)
                w_all = sum(r['net'] for r in rows if r['net'] > 0)
                w_kept = sum(r['net'] for r in by.get(best, []) if r['net'] > 0)
                print('    best state %s: top-10 winners kept %d/10, winner P&L '
                      'kept %.0f%%, per-original-parent EV %+.2f (vs unfiltered %+.2f)'
                      % (best, kept, 100.0 * w_kept / w_all if w_all else 0,
                         sum(r['net'] for r in by.get(best, [])) / len(rows), allst['ev']))
                fam.append(('%s/%s' % (name, tool), p, dlt, len(H), len(L)))
        # 3x3 diagnostic
        print('  3x3 (N / EV / MFE-MAE ratio):')
        for rb_ in ('LOW', 'MEDIUM', 'HIGH'):
            cells = []
            for vb_ in ('LOW', 'MEDIUM', 'HIGH'):
                g = [r for r in rows if r['rb'] == rb_ and r['vb'] == vb_]
                c = cellstats(g)
                cells.append('%4d %+7.2f %4.2f' % (c['n'], c['ev'], c['ratio'])
                             if c else '   -       -    -')
            print('    R-%-6s | %s' % (rb_, ' | '.join(cells)))
        # structural geometry diagnostic
        gs = [r for r in rows if r.get('sref')]
        if len(gs) >= 30:
            for st in ('LOW', 'HIGH'):
                g = [r for r in gs if r['rb'] == st]
                if len(g) >= 10:
                    near_big = sum(1 for r in g if r['sref'] / r['atr'] <= 0.75
                                   and r['mfe'] >= 2 * r['atr'])
                    print('  geometry %-4s: med structDist %.2f ATR   '
                          'P(dist<=0.75ATR & MFE>=2ATR) %.1f%%'
                          % (st, statistics.median([r['sref'] / r['atr'] for r in g]),
                             100.0 * near_big / len(g)))
        print()

    print('=' * 96)
    print('TRACK A FAMILY ACCOUNTING  (M = %d interaction tests, BH)' % len(fam))
    qs = bh_adjust([p for _, p, _, _, _ in fam])
    for (lab, p, dlt, nH, nL), q in sorted(zip(fam, qs), key=lambda x: x[0][1]):
        print('  %-28s HIGH-LOW %+8.2f  nH %4d nL %4d  p %.4f  q %.4f%s'
              % (lab, dlt, nH, nL, p, q, '' if q > 0.05 else '  *'))
    with open(os.path.join(HERE, 'TA_CELLS.csv'), 'w', newline='') as fh:
        if csvrows:
            w = csv.DictWriter(fh, fieldnames=list(csvrows[0].keys()),
                               extrasaction='ignore')
            w.writeheader()
            for r in csvrows:
                w.writerow({k: (v if not isinstance(v, dict) else str(v))
                            for k, v in r.items()})
    print('full cell metrics -> TA_CELLS.csv')
