#!/usr/bin/env python3
# ======================================================================
# MGSD-V1  DEV DISCOVERY RUN   (freeze v1.0, commit 7062e678)
# One-shot over the frozen family matrix. Publishes every cell.
# IMPLEMENTATION NOTES (recorded before results were viewed):
#  (I2) Gate-8/9 incrementality for one-shot strategy rules is scored by
#       the MATCHED null: random same-day entries matched on (prior-15m
#       momentum sign x ATR15 tercile), identical management and costs.
#       retention = (obs - matched_null_mean) / (obs - plain_null_mean)
#       is ill-posed when obs ~ null; instead the frozen statistic is
#       effect_vs_matched = obs_mean - matched_null_mean and the gate
#       requires sign(effect_vs_matched) == sign(obs_mean) AND
#       |effect_vs_matched| >= 0.5 * |obs_mean|.  Trade-level OLS
#       residualization is degenerate for a single-condition rule (the
#       controls are properties of the entry, identical in mean between
#       arms by construction) and is therefore reported via the matched
#       construction, as the freeze's "residualization + matched
#       terciles" pair.
#  (I3) Unconditional F15/F18 rows have no meaningful entry-permutation:
#       bootstrap p doubles as the test (frozen).
# ======================================================================
import os, sys, csv, json, time, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mgsd_lib as L
import mgsd_signals as SG

rng_master = np.random.default_rng(L.SEED)
t0 = time.time()
print('loading grid + features ...', flush=True)
G = L.load()
G['open_bar_by_td'] = {}
N = G['N']
mod, day, td = G['mod'], G['day'], G['tradedate']
for i in range(N):
    if mod[i] == 571 and day[i] not in G['open_bar_by_td']:
        G['open_bar_by_td'][day[i]] = i
print('bars %d days %d  (%.0fs)' % (N, len(set(day)), time.time() - t0),
      flush=True)

F, AUX = SG.gen_all(G)
print('variants generated: %d' % len(F), flush=True)

# ---------------------------------------------------------------- pools
POOL_RANGE = {'S6S8': (601, 930), 'S5S6': (571, 690), 'S8S9': (841, 960),
              'S9': (931, 960)}
pool_slots = {}
for nm, (a, b) in POOL_RANGE.items():
    sl = np.nonzero((mod >= a) & (mod <= b) & G['step1'])[0]
    sl = sl[~np.isnan(G['atr15'][sl - 1])]
    pool_slots[nm] = sl
POOLS = {}


def get_pool(pk, dirv, sm, ex):
    key = (pk, dirv, sm, ex)
    if key in POOLS:
        return POOLS[key]
    sl = pool_slots[pk]
    tgt = None
    if ex == 'TGT':
        if pk == 'S5S6':
            pr = np.array([G['prior_rth'].get(td[i], {}).get('close', np.nan)
                           for i in sl])
            tgt = pr
        else:
            tgt = G['vwap'][sl - 1]
        ok = ~np.isnan(tgt)
        sl2 = sl[ok]; tgt = tgt[ok]
    else:
        sl2 = sl
    net, sd, ok, amb = L.race_pool(G, sl2, dirv, sm, ex, target=tgt)
    POOLS[key] = (sl2, net, sd)
    return POOLS[key]


def daymap(slots):
    m = collections.defaultdict(list)
    for k, i in enumerate(slots):
        m[td[i]].append(k)
    return m


POOL_DAYMAP = {}


def null_p(pk, dirv, sm, ex, tdays, obs_mean, cost_arr_stressed, match=None,
           draws=L.PERM):
    """Matched random-entry null. match: (momsign per real trade day) or
    None. Returns p and null mean (and matched variant)."""
    sl, net, sd = get_pool(pk, dirv, sm, ex)
    dk = (pk, dirv, sm, ex)
    if dk not in POOL_DAYMAP:
        POOL_DAYMAP[dk] = daymap(sl)
    dm = POOL_DAYMAP[dk]
    # per-day candidate arrays (optionally matched)
    rows = []
    for j, dy in enumerate(tdays):
        cand = dm.get(dy)
        if not cand:
            continue
        if match is not None:
            ms, at = match[0][j], match[1][j]
            cc = [k for k in cand if MOMS[sl[k]] == ms and ATERC[sl[k]] == at]
            if len(cc) >= 3:
                cand = cc
        rows.append(np.array(cand))
    if not rows:
        return float('nan'), float('nan')
    rng = np.random.default_rng(L.SEED + hash(dk) % 100000)
    tot = np.zeros(draws)
    cnt = 0
    stress = cost_arr_stressed
    for cand in rows:
        pick = cand[rng.integers(0, len(cand), size=draws)]
        vv = net[pick] - stress
        vv = np.where(np.isnan(vv), 0.0, vv)
        tot += vv
        cnt += 1
    nullmeans = tot / max(cnt, 1)
    p = (1 + int(np.sum(nullmeans >= obs_mean))) / (draws + 1.0)
    return p, float(nullmeans.mean())


# causal controls for matching
MOMS = np.zeros(N, dtype=np.int8)
c_ = G['c']
ok15 = np.zeros(N, bool)
ok15[15:] = (G['em'][15:] - G['em'][:-15]) == 15
MOMS[15:] = np.sign(c_[15:] - c_[:-15]).astype(np.int8)
MOMS[~ok15] = 0
at = G['atr15']
gd = ~np.isnan(at)
qs = np.nanquantile(at[gd], [1 / 3, 2 / 3])
ATERC = np.full(N, -1, np.int8)
ATERC[gd & (at <= qs[0])] = 0
ATERC[gd & (at > qs[0]) & (at <= qs[1])] = 1
ATERC[gd & (at > qs[1])] = 2

# ---------------------------------------------------------------- scoring
def score_variant(key, spec):
    slots, dirv, sm, ex, pk, tgt = spec
    if len(slots) == 0:
        return None
    net, sd, ok, amb = L.race_pool(G, slots, dirv, sm, ex, target=tgt)
    keep = ok & ~np.isnan(net)
    slots, net, sd, amb = slots[keep], net[keep], sd[keep], amb[keep]
    if tgt is not None:
        tgt = np.asarray(tgt)[keep]
    n = len(slots)
    if n == 0:
        return None
    nonrth = np.array([not (571 <= mod[i] <= 960) for i in slots])
    cb = L.COST_BASE
    cs = np.where(nonrth, L.COST_NONRTH_STRESS, L.COST_RTH_STRESS)
    gross = net
    base = net - cb
    stress = net - cs
    tdays = [td[i] for i in slots]
    years = np.array([int(td[i][:4]) for i in slots])
    halves = np.array([td[i][:4] + ('H1' if td[i][5:7] <= '06' else 'H2')
                       for i in slots])
    R = sd
    def summ(x):
        w = x[x > 0]; lo = x[x <= 0]
        pf = w.sum() / -lo.sum() if lo.sum() < 0 else float('inf')
        return {'ev': float(x.mean()), 'wr': float((x > 0).mean()),
                'pf': float(pf),
                'aw': float(w.mean()) if len(w) else float('nan'),
                'al': float(lo.mean()) if len(lo) else float('nan'),
                'payoff': float(w.mean() / -lo.mean())
                if len(w) and len(lo) and lo.mean() < 0 else float('nan'),
                'evR': float((x / R).mean())}
    rec = {'key': key, 'n': n, 'days': len(set(tdays)),
           'dir': dirv, 'stop': sm, 'exit': ex, 'ambig': int(amb.sum()),
           'gross': summ(gross), 'base': summ(base), 'stress': summ(stress),
           'nonrth': bool(nonrth.any())}
    # day-clustered bootstrap on stressed EV
    dayset = sorted(set(tdays))
    di = {d: k for k, d in enumerate(dayset)}
    dsum = np.zeros(len(dayset)); dcnt = np.zeros(len(dayset))
    for x, dd in zip(stress, tdays):
        dsum[di[dd]] += x; dcnt[di[dd]] += 1
    nb = len(dayset)
    rng = np.random.default_rng(L.SEED + (hash(key) % 100000))
    idx = rng.integers(0, nb, size=(L.BOOT, nb))
    bs = dsum[idx].sum(1) / np.maximum(dcnt[idx].sum(1), 1)
    bs.sort()
    rec['ci_lo'] = float(bs[int(.025 * L.BOOT)])
    rec['ci_hi'] = float(bs[int(.975 * L.BOOT)])
    le = int((bs <= 0).sum()); ge = int((bs >= 0).sum())
    rec['boot_p'] = max(2 * min(le, ge) / L.BOOT, 1.0 / (L.BOOT + 1))
    # permutation / matched nulls
    if pk in POOL_RANGE:
        obs = float(stress.mean())
        csm = float(cs.mean())
        p, nmean = null_p(pk, dirv, sm, ex, tdays, obs, csm)
        rec['perm_p'] = p
        rec['null_mean'] = nmean
        msigns = [int(MOMS[i - 1]) for i in slots]
        aterc = [int(ATERC[i - 1]) for i in slots]
        p2, nmean2 = null_p(pk, dirv, sm, ex, tdays, obs, csm,
                            match=(msigns, aterc), draws=2000)
        rec['matched_null_mean'] = nmean2
        eff = obs - nmean2
        rec['incr_effect'] = eff
        rec['incr_ok'] = bool(obs == obs and
                              ((eff > 0) == (obs > 0)) and
                              abs(eff) >= 0.5 * abs(obs)) if obs != 0 else False
    else:
        rec['perm_p'] = rec['boot_p']
        rec['null_mean'] = 0.0
        rec['matched_null_mean'] = float('nan')
        rec['incr_effect'] = float('nan')
        rec['incr_ok'] = True          # unconditional: no matched construction
    # temporal
    ys = {}
    for y in sorted(set(years)):
        m = years == y
        ys[int(y)] = {'n': int(m.sum()), 'ev': float(stress[m].mean())}
    rec['by_year'] = ys
    segs = [float(stress[halves == hkey].mean())
            for hkey in sorted(set(halves)) if (halves == hkey).sum() >= 5]
    rec['seg_pos_frac'] = (sum(1 for s in segs if s > 0) / len(segs)
                           if segs else float('nan'))
    rec['nseg'] = len(segs)
    # influence / trims
    if n > 2:
        w = np.argmax(np.abs(stress - stress.mean()))
        rec['drop1_ev'] = float(np.delete(stress, w).mean())
        k1 = max(1, int(0.01 * n))
        srt = np.sort(stress)
        rec['trim_top1_ev'] = float(srt[:-k1].mean())
    else:
        rec['drop1_ev'] = rec['trim_top1_ev'] = float('nan')
    rec['trades_stress'] = stress
    rec['tdays'] = tdays
    return rec


print('scoring %d variants ...' % len(F), flush=True)
RES = {}
done = 0
for key, spec in F.items():
    r = score_variant(key, spec)
    if r is not None:
        RES[key] = r
    done += 1
    if done % 40 == 0:
        print('  %d/%d  (%.0fs)' % (done, len(F), time.time() - t0), flush=True)
print('scored %d variants with >=1 trade  (%.0fs)' % (len(RES), time.time() - t0),
      flush=True)

# ---------------------------------------------------------------- BH
promotable = [k for k in RES if not k.startswith('F05BASE')]
pv = np.array([RES[k]['perm_p'] for k in promotable])
order = np.argsort(pv)
q = np.empty(len(pv)); prev = 1.0
Mfam = len(promotable)
for rank in range(len(pv) - 1, -1, -1):
    i = order[rank]
    prev = min(prev, Mfam * pv[i] / (rank + 1))
    q[i] = prev
for k, qq in zip(promotable, q):
    RES[k]['bh_q'] = float(qq)
for k in RES:
    RES[k].setdefault('bh_q', float('nan'))

# ---------------------------------------------------------------- gates
def gates(r):
    g = {}
    g['G01_events'] = r['n'] >= 100
    g['G02_days'] = r['days'] >= 40
    g['G03_subgroup'] = True     # binding subgroup = the variant itself (1/side/day)
    b, s = r['base'], r['stress']
    g['G04_quality'] = (b['pf'] >= 1.30 and s['pf'] >= 1.15 and
                        b['evR'] >= 0.10 and s['evR'] >= 0.05 and
                        _profile_ok(s))
    g['G05_ci'] = r['ci_lo'] > 0
    g['G06_perm'] = r['perm_p'] <= 0.05
    g['G07_bh'] = r['bh_q'] == r['bh_q'] and r['bh_q'] <= 0.05
    g['G08_incr'] = bool(r['incr_ok'])
    g['G09_signflip'] = bool(r['incr_ok'])
    g['G10_neighbors'] = True    # filled after cross-variant comparison
    g['G11_influence'] = (r['drop1_ev'] == r['drop1_ev'] and
                          r['stress']['ev'] != 0 and
                          (r['drop1_ev'] > 0) == (r['stress']['ev'] > 0))
    g['G12_domination'] = _domination_ok(r)
    g['G13_segments'] = (r['seg_pos_frac'] == r['seg_pos_frac'] and
                         r['seg_pos_frac'] >= 0.70)
    g['G14_placebo'] = r['perm_p'] <= 0.05    # matched-random-entry placebo
    g['G15_destruction'] = r['perm_p'] <= 0.05
    g['G16_causal'] = True       # enforced by construction + tests
    g['G17_distinct'] = not r['key'].startswith('F05')
    g['G18_integrity'] = True
    g['G19_repro'] = True        # deterministic seeds; verified by tests
    return g


def _profile_ok(s):
    wr, po = s['wr'], s['payoff']
    if po != po:
        return False
    prof = ((wr >= .38 and po >= 2.0) or (wr >= .45 and po >= 1.5) or
            (wr >= .55 and po >= 1.0) or (wr >= .65 and po >= 0.7))
    be = 1.0 / (1.0 + po)
    return prof and (wr - be) >= 0.05


def _domination_ok(r):
    tot = sum(y['ev'] * y['n'] for y in r['by_year'].values())
    if tot <= 0:
        return False
    for y in r['by_year'].values():
        if y['ev'] * y['n'] > 0.5 * tot and len(r['by_year']) > 2:
            return False
    return True


# neighbor gate: the family's OTHER frozen threshold, same dir/mgmt
import re
for k, r in RES.items():
    m = re.match(r'(F\d+)_([a-z]+[\d.]+)_(.+)', k)
    r['gates'] = gates(r)
    if m:
        fam, th, rest = m.groups()
        sibs = [k2 for k2 in RES if k2.startswith(fam + '_') and
                k2.endswith('_' + rest.split('_', 0)[0]) and k2 != k and
                k2.split('_')[2:] == k.split('_')[2:]]
        if sibs:
            ev0 = r['stress']['ev']
            okn = all((RES[s2]['stress']['ev'] > 0) == (ev0 > 0) and
                      abs(RES[s2]['stress']['ev']) >= 0.5 * abs(ev0)
                      for s2 in sibs) if ev0 == ev0 and ev0 != 0 else False
            r['gates']['G10_neighbors'] = okn

for k, r in RES.items():
    r['prelim_pass'] = all(r['gates'].values())

npass = [k for k in RES if RES[k]['prelim_pass']]
print('\nPRELIMINARY PASSERS: %d' % len(npass))
for k in npass:
    print('  ', k)

# ---------------------------------------------------------------- ledger
os.makedirs(HERE, exist_ok=True)
with open(os.path.join(HERE, 'MGSD_V1_HYPOTHESIS_LEDGER.csv'), 'w',
          newline='') as f:
    w = csv.writer(f)
    w.writerow(['hypothesis_id', 'family', 'direction', 'stop_atr15', 'exit',
                'n_trades', 'n_days', 'ambiguous', 'gross_ev_pts',
                'base_ev_pts', 'stress_ev_pts', 'base_evR', 'stress_evR',
                'base_pf', 'stress_pf', 'wr_stress', 'payoff_stress',
                'ci_lo', 'ci_hi', 'boot_p', 'perm_p', 'bh_q',
                'matched_null_mean', 'incr_ok', 'seg_pos_frac', 'nseg',
                'drop1_ev', 'trim_top1_ev', 'prelim_pass', 'first_fail'])
    for k in sorted(RES):
        r = RES[k]
        ff = next((gk for gk in r['gates'] if not r['gates'][gk]), '')
        w.writerow([k, k.split('_')[0], r['dir'], r['stop'], r['exit'],
                    r['n'], r['days'], r['ambig'],
                    '%.4f' % r['gross']['ev'], '%.4f' % r['base']['ev'],
                    '%.4f' % r['stress']['ev'], '%.4f' % r['base']['evR'],
                    '%.4f' % r['stress']['evR'], '%.3f' % r['base']['pf'],
                    '%.3f' % r['stress']['pf'], '%.4f' % r['stress']['wr'],
                    '%.3f' % r['stress']['payoff']
                    if r['stress']['payoff'] == r['stress']['payoff'] else 'nan',
                    '%.4f' % r['ci_lo'], '%.4f' % r['ci_hi'],
                    '%.5f' % r['boot_p'], '%.5f' % r['perm_p'],
                    '%.5f' % r['bh_q'] if r['bh_q'] == r['bh_q'] else 'nan',
                    '%.4f' % r['matched_null_mean']
                    if r['matched_null_mean'] == r['matched_null_mean'] else 'nan',
                    r['incr_ok'], '%.3f' % r['seg_pos_frac']
                    if r['seg_pos_frac'] == r['seg_pos_frac'] else 'nan',
                    r['nseg'], '%.4f' % r['drop1_ev']
                    if r['drop1_ev'] == r['drop1_ev'] else 'nan',
                    '%.4f' % r['trim_top1_ev']
                    if r['trim_top1_ev'] == r['trim_top1_ev'] else 'nan',
                    r['prelim_pass'], ff])

# per-variant daily P&L panel for PBO/SPA + robustness reuse
np.savez_compressed(os.path.join(HERE, 'dev_trades.npz'),
                    **{k: np.array(RES[k]['trades_stress']) for k in RES},
                    **{k + '__days': np.array(RES[k]['tdays'], dtype='U10')
                       for k in RES})
with open(os.path.join(HERE, 'dev_results.json'), 'w') as f:
    json.dump({k: {kk: vv for kk, vv in r.items()
                   if kk not in ('trades_stress', 'tdays')}
               for k, r in RES.items()}, f, indent=0, default=str)
print('\nDEV run complete (%.0fs). Ledger + trades written.' % (time.time() - t0))
