#!/usr/bin/env python3
# ======================================================================
# RVMR-AVOID-V1 - counter-movement trade-avoidance battery
# ======================================================================
# Frozen by docs/RVMR_AVOID_PREREGISTRATION.md. Strategies scored
# exactly as canonically registered; the only new variable is the RVMR
# state available at the decision-bar close. HISTORICAL RESEARCH ONLY.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, math, random, statistics, collections

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../rvmr', '../v41', '../mag', '../rvmr_strat'):
    sys.path.insert(0, os.path.join(HERE, p))
import rvmr_spec as S

SEED = 20260826
TOD = (('OPEN', 570, 630), ('MIDMORN', 630, 720),
       ('MIDDAY', 720, 810), ('AFTERNOON', 810, 900))
EFF_LO, EFF_HI = 0.119, 0.264


def med(x):
    return statistics.median(x) if x else float('nan')


def mean(x):
    return sum(x) / len(x) if x else float('nan')


def pctl(x, q):
    if not x:
        return float('nan')
    s = sorted(x)
    return s[min(len(s) - 1, int(q * len(s)))]


def day_boot_delta(rowsH, rowsO, iters=20000, seed=SEED):
    """Two-sided day-clustered bootstrap p for EV(HIGH)-EV(others)."""
    if len(rowsH) < 10 or len(rowsO) < 10:
        return float('nan'), (float('nan'),) * 2, float('nan')
    rnd = random.Random(seed)
    bh = collections.defaultdict(list)
    bo = collections.defaultdict(list)
    for r in rowsH: bh[r['day']].append(r['net'])
    for r in rowsO: bo[r['day']].append(r['net'])
    days = sorted(set(bh) | set(bo))
    ds = []
    for _ in range(iters):
        H, O = [], []
        for _ in days:
            d = days[rnd.randrange(len(days))]
            H.extend(bh.get(d, ())); O.extend(bo.get(d, ()))
        if H and O:
            ds.append(sum(H) / len(H) - sum(O) / len(O))
    ds.sort()
    obs = mean([r['net'] for r in rowsH]) - mean([r['net'] for r in rowsO])
    neg = sum(1 for x in ds if x <= 0) / len(ds)
    p = min(1.0, 2 * min(neg, 1 - neg) + 1.0 / (iters + 1))
    return obs, (ds[int(.025 * len(ds))], ds[int(.975 * len(ds))]), p


def bh_adjust(ps):
    idx = sorted(range(len(ps)), key=lambda i: (ps[i] != ps[i], ps[i]))
    m = len(ps); q = [None] * m; prev = 1.0
    for rank, i in enumerate(reversed(idx), 1):
        v = min(prev, (ps[i] if ps[i] == ps[i] else 1.0) * m / (m - rank + 1))
        q[i] = v; prev = v
    return q


def geometry(rows, label):
    if not rows:
        return
    maes = [r['mae'] / r['atr'] for r in rows]
    mfes = [r['mfe'] / r['atr'] for r in rows]
    ffp = [r for r in rows if r.get('ff25') in ('FAV', 'ADV')]
    print('      %-7s MAE med %4.2f mean %4.2f p75 %4.2f p90 %4.2f | '
          'MFE med %4.2f mean %4.2f p75 %4.2f p90 %4.2f | M/M %4.2f | '
          'ff25 %4.1f%% | stop %4.1f%%'
          % (label, med(maes), mean(maes), pctl(maes, .75), pctl(maes, .90),
             med(mfes), mean(mfes), pctl(mfes, .75), pctl(mfes, .90),
             med(mfes) / med(maes) if med(maes) else float('nan'),
             100.0 * sum(1 for r in ffp if r['ff25'] == 'FAV') / len(ffp)
             if ffp else float('nan'),
             100.0 * sum(1 for r in rows if r['reason'] == 'STOP') / len(rows)))
    rg = {}
    for x in (0.5, 1, 2, 3):
        n = sum(1 for r in rows if x in r.get('reach', {})
                and (r.get('t_stop') is None or r['reach'][x] <= r['t_stop']))
        rg[x] = 100.0 * n / len(rows)
    print('              P(+xR before stop): 0.5R %4.1f%%  1R %4.1f%%  '
          '2R %4.1f%%  3R %4.1f%%' % (rg[0.5], rg[1], rg[2], rg[3]))


def avoidance(rows, key, family):
    """Baseline vs AVOID-HIGH economics, per-original-opportunity EV."""
    hi = [r for r in rows if r[key] == 'HIGH']
    keep = [r for r in rows if r[key] != 'HIGH']
    if not hi or not keep:
        print('    avoidance: not computable (empty cell)')
        return None
    N = len(rows)
    win_all = [r for r in rows if r['net'] > 0]
    win_rm = [r for r in hi if r['net'] > 0]
    los_rm = [r for r in hi if r['net'] <= 0]
    saved = -sum(r['net'] for r in los_rm)
    sacr = sum(r['net'] for r in win_rm)
    ev0 = mean([r['net'] for r in rows])
    ev1 = sum(r['net'] for r in keep) / N          # per ORIGINAL opportunity
    top10 = sorted(rows, key=lambda r: -r['net'])[:10]
    kept10 = sum(1 for r in top10 if r[key] != 'HIGH')
    w5 = sorted(win_all, key=lambda r: -r['net'])[:max(1, len(win_all) // 20)]
    w5keep = sum(r['net'] for r in w5 if r[key] != 'HIGH') / \
        max(1e-9, sum(r['net'] for r in w5))
    wkeep = sum(r['net'] for r in keep if r['net'] > 0) / \
        max(1e-9, sum(r['net'] for r in win_all))
    print('    AVOID-HIGH economics: N %d -> %d (removed %d = %dW + %dL)'
          % (N, len(keep), len(hi), len(win_rm), len(los_rm)))
    print('      loser P&L avoided %+10.1f   winner P&L sacrificed %+10.1f   '
          'saved/sacrificed %.2f'
          % (saved, sacr, saved / sacr if sacr > 0 else float('inf')))
    print('      per-ORIGINAL-opportunity EV %+7.3f -> %+7.3f  (delta %+.3f)'
          % (ev0, ev1, ev1 - ev0))
    print('      top-10 winners kept %d/10   top-5%% winner P&L kept %4.0f%%  '
          'total winner P&L kept %.0f%%   largest removed winner %+.1f'
          % (kept10, 100 * w5keep, 100 * wkeep,
             max((r['net'] for r in win_rm), default=0.0)))
    return {'ev0': ev0, 'ev1': ev1, 'saved': saved, 'sacr': sacr,
            'kept10': kept10, 'wkeep': wkeep}


# ---------------------------------------------------------------- family assembly
def build_families():
    """Harvest all seven families with uniform per-event row schema:
    net, R, mfe, mae, atr, reason, reach, t_stop, ff25, day, part/year,
    hour, rb, vb, prev_rb, ext, eff. Sources verbatim."""
    fams = {}

    # ---- 5y families via tb_run (loads data at import)
    import tb_run as TB
    D, RB, VB, atr = TB.D, TB.RB, TB.VB, TB.atr

    def av5(j, d):
        o = TB.frame(j, d)
        o['hour'] = int(D['et'][j][11:13])
        o['rb'] = RB[j]; o['vb'] = VB[j]
        # previous RTH-consecutive state for transitions
        o['prev_rb'] = RB[j - 1] if (j > 0 and D['em'][j] - D['em'][j - 1] == 1
                                     and 570 <= D['mod'][j - 1] <= 960) else None
        # uniform extension: 15-min pre-entry move / ATR
        if j >= 15 and D['em'][j] - D['em'][j - 15] == 15 and atr[j]:
            o['ext'] = abs(D['c'][j] - D['c'][j - 15]) / atr[j]
        else:
            o['ext'] = None
        # frozen efficiency: 5-bar net / path
        if j >= 5 and D['em'][j] - D['em'][j - 5] == 5:
            path = sum(D['h'][j - k] - D['l'][j - k] for k in range(5))
            o['eff'] = abs(D['c'][j] - D['c'][j - 5]) / path if path > 0 else None
        else:
            o['eff'] = None
        o['grp'] = o['year']
        return o

    acc, rej = TB.gap_events()
    fams['F1_GAP_FADE*'] = [av5(j, d) for j, d in rej]
    fams['F2_VWAP_REV'] = [av5(j, d) for j, d in TB.meanrev_events()]
    fams['F7_LEVEL_RECLAIM'] = [av5(j, d) for j, d in TB.reclaim_events()]

    # ---- canonical-year families via ta_run harvest
    import ta_run as TA
    import cand_spec as CS
    B = CS.load_merged()
    RRs, VRs = TA.rvmr_states(B)
    evs = TA.harvest(B)
    # per-bar previous-state map for transitions on canonical year
    ets = [b['et'] for b in B]
    ridx = {et: i for i, et in enumerate(ets)}

    def avc(e, name):
        j, d = e['j'], e['d']
        b = B[j]
        a = b.get('atr')
        if not a or a <= 0:
            return None
        o = TA.frame(B, j, d, a)
        if o is None:
            return None
        o['rb'] = RRs.get(b['et']); o['vb'] = VRs.get(b['et'])
        pj = j - 1
        o['prev_rb'] = RRs.get(B[pj]['et']) if pj >= 0 and \
            B[j]['tmin'] - B[pj]['tmin'] == 1 else None
        if j >= 15 and B[j]['tmin'] - B[j - 15]['tmin'] == 15:
            o['ext'] = abs(b['close'] - B[j - 15]['close']) / a
        else:
            o['ext'] = None
        o['eff'] = b.get('eff')
        o['grp'] = o['part']
        return o

    for fid, key in (('F3_SESSION_REV*', 'A7_MEAN_REV'),
                     ('F4_V_RECOVERY', 'A6_V_RECOVERY'),
                     ('F5_OVN_RECLAIM', 'A9_OVN_RECLAIM'),
                     ('F6_FAILED_BRK', 'A5_REJECT_BRK')):
        rows = [avc(e, fid) for e in evs[key]]
        fams[fid] = [r for r in rows if r]
    # replication echo for F7 on canonical year
    rows = [avc(e, 'echo') for e in evs['A3_SWEEP_RECLAIM']]
    fams['F7echo_15M_RECLAIM'] = [r for r in rows if r]
    return fams


# ---------------------------------------------------------------- main
if __name__ == '__main__':
    fams = build_families()
    print('RVMR-AVOID-V1  registered families (M = 7 + 1 echo):')
    for k in sorted(fams):
        print('  %-22s %6d events%s' % (k, len(fams[k]),
              '   (*MOTIVATING - seen in STRAT-V1, not confirmation)'
              if k.endswith('*') else ''))
    print()

    primary = [k for k in sorted(fams) if not k.startswith('F7echo')]
    results = {}
    for tool, key in (('RANGE', 'rb'), ('VOLUME', 'vb')):
        print('#' * 96)
        print('TOOL: %s' % tool)
        fam_stats = []
        for fid in primary:
            rows = [r for r in fams[fid] if r.get(key)]
            if len(rows) < 30:
                print('%s  n=%d  INSUFFICIENT DATA\n' % (fid, len(rows)))
                fam_stats.append((fid, float('nan'), float('nan'), 0, 0))
                continue
            print('=' * 96)
            print('%s   n=%d' % (fid, len(rows)))
            by = {st: [r for r in rows if r[key] == st]
                  for st in ('LOW', 'MEDIUM', 'HIGH')}
            for st in ('LOW', 'MEDIUM', 'HIGH'):
                g = by[st]
                if not g:
                    continue
                nets = [r['net'] for r in g]
                w = [x for x in nets if x > 0]; l = [x for x in nets if x <= 0]
                print('    %-6s n %5d  EV %+7.2f  WR %4.1f%%  PF %5.2f  '
                      'med %+7.2f  avgW %+7.1f  avgL %+7.1f'
                      % (st, len(g), mean(nets), 100.0 * len(w) / len(g),
                         (sum(w) / abs(sum(l))) if l and sum(l) else float('inf'),
                         med(nets), mean(w) if w else float('nan'),
                         mean(l) if l else float('nan')))
                geometry(g, st)
            H = by['HIGH']; O = by['LOW'] + by['MEDIUM']
            obs, ci, p = day_boot_delta(H, O)
            print('    PRIMARY Delta EV(HIGH)-EV(LOW+MED) %+7.2f  '
                  'CI[%+.2f,%+.2f]  p %.4f' % (obs, ci[0], ci[1], p))
            av = avoidance(rows, key, fid)
            # ATR strata
            atrs = sorted(r['atr'] for r in rows)
            t1_, t2_ = atrs[len(atrs) // 3], atrs[2 * len(atrs) // 3]
            wsum = wn = 0.0
            for lo_, hi_, lab in ((0, t1_, 'loATR'), (t1_, t2_, 'midATR'),
                                  (t2_, 1e9, 'hiATR')):
                Hs = [r for r in H if lo_ < r['atr'] <= hi_]
                Os = [r for r in O if lo_ < r['atr'] <= hi_]
                if len(Hs) >= 10 and len(Os) >= 10:
                    d_ = mean([r['net'] for r in Hs]) - mean([r['net'] for r in Os])
                    k_ = len(Hs) + len(Os)
                    wsum += d_ * k_; wn += k_
                    print('      ATR %-6s delta %+7.2f  (nH %d nO %d)'
                          % (lab, d_, len(Hs), len(Os)))
            atr_ctl = wsum / wn if wn else float('nan')
            # ToD strata
            wsum2 = wn2 = 0.0
            for lab, a_, b_ in TOD:
                Hs = [r for r in H if a_ <= r['hour'] * 60 < b_ or
                      (a_ <= r['hour'] * 60 + 30 < b_)]
                Hs = [r for r in H if a_ <= r['hour'] * 60 + 30 < b_]
                Os = [r for r in O if a_ <= r['hour'] * 60 + 30 < b_]
                if len(Hs) >= 10 and len(Os) >= 10:
                    d_ = mean([r['net'] for r in Hs]) - mean([r['net'] for r in Os])
                    k_ = len(Hs) + len(Os)
                    wsum2 += d_ * k_; wn2 += k_
                    print('      ToD %-9s delta %+7.2f  (nH %d nO %d)'
                          % (lab, d_, len(Hs), len(Os)))
            tod_ctl = wsum2 / wn2 if wn2 else float('nan')
            print('      CONTROLLED deltas: ATR-weighted %+0.2f   ToD-weighted %+0.2f'
                  % (atr_ctl, tod_ctl))
            # extension buckets
            er = [r for r in rows if r.get('ext') is not None]
            if len(er) >= 90:
                es = sorted(r['ext'] for r in er)
                e1, e2 = es[len(es) // 3], es[2 * len(es) // 3]
                for lo_, hi_, lab in ((0, e1, 'smallEXT'), (e1, e2, 'medEXT'),
                                      (e2, 1e9, 'largeEXT')):
                    g = [r for r in er if lo_ < r['ext'] <= hi_]
                    gh = [r for r in g if r[key] == 'HIGH']
                    go = [r for r in g if r[key] != 'HIGH']
                    if len(gh) >= 10 and len(go) >= 10:
                        print('      %-9s HIGH %+7.2f (n%d)  others %+7.2f (n%d)'
                              % (lab, mean([r['net'] for r in gh]), len(gh),
                                 mean([r['net'] for r in go]), len(go)))
            # temporal stability
            gr = collections.defaultdict(lambda: [[], []])
            for r in H: gr[r['grp']][0].append(r['net'])
            for r in O: gr[r['grp']][1].append(r['net'])
            cells = []
            for g2 in sorted(gr):
                hh, oo = gr[g2]
                if len(hh) >= 5 and len(oo) >= 5:
                    cells.append('%s %+0.1f' % (g2, mean(hh) - mean(oo)))
            print('      temporal delta(H-O): ' + '  '.join(cells))
            fam_stats.append((fid, obs, p, len(H), len(O)))
            results[(tool, fid)] = {'obs': obs, 'p': p, 'av': av,
                                    'by': {st: mean([r['net'] for r in by[st]])
                                           if by[st] else None
                                           for st in ('LOW', 'MEDIUM', 'HIGH')}}
            print()
        # pooled + family accounting
        pool = [r for fid in primary for r in fams[fid] if r.get(key)]
        H = [r for r in pool if r[key] == 'HIGH']
        O = [r for r in pool if r[key] != 'HIGH']
        obsP, ciP, pP = day_boot_delta(H, O)
        print('POOLED (%s, all seven families): delta %+0.2f  CI[%+.2f,%+.2f]  '
              'p %.4f   (nH %d, nO %d)' % (tool, obsP, ciP[0], ciP[1], pP,
                                           len(H), len(O)))
        ps = [p_ for _, _, p_, _, _ in fam_stats]
        qs = bh_adjust(ps)
        print('FAMILY ACCOUNTING (%s, BH at M=7):' % tool)
        for (fid, obs, p_, nH, nO), q in zip(fam_stats, qs):
            print('  %-22s delta %+8.2f  p %6.4f  q %6.4f  (nH %d nO %d)'
                  % (fid, obs, p_, q, nH, nO))
        print()

    # transitions diagnostic (RANGE, pooled)
    print('=' * 96)
    print('TRANSITIONS diagnostic (RANGE, pooled over all families):')
    pool = [r for fid in primary for r in fams[fid] if r.get('rb')]
    tr = collections.defaultdict(list)
    for r in pool:
        if r.get('prev_rb'):
            tr['%s->%s' % (r['prev_rb'][0], r['rb'][0])].append(r['net'])
    for k in sorted(tr, key=lambda k2: -len(tr[k2])):
        if len(tr[k]) >= 30:
            print('  %-6s n %5d  EV %+7.2f' % (k, len(tr[k]), mean(tr[k])))
    # efficiency diagnostic within HIGH
    print('\nEFFICIENCY diagnostic (RANGE-HIGH fades, frozen EFF bands):')
    hi = [r for r in pool if r['rb'] == 'HIGH' and r.get('eff') is not None]
    for lab, lo_, hi_ in (('loEFF', -1, EFF_LO), ('midEFF', EFF_LO, EFF_HI),
                          ('hiEFF', EFF_HI, 9)):
        g = [r for r in hi if lo_ < r['eff'] <= hi_]
        if len(g) >= 30:
            print('  %-6s n %5d  EV %+7.2f  medMAE %4.2f  medMFE %4.2f'
                  % (lab, len(g), mean([r['net'] for r in g]),
                     med([r['mae'] / r['atr'] for r in g]),
                     med([r['mfe'] / r['atr'] for r in g])))
    # echo family
    print('\nF7 replication echo (canonical-year 15m sweep-reclaim):')
    rows = fams['F7echo_15M_RECLAIM']
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        g = [r for r in rows if r.get('rb') == st]
        if g:
            print('  %-6s n %4d  EV %+7.2f' % (st, len(g),
                                               mean([r['net'] for r in g])))
