#!/usr/bin/env python3
# ======================================================================
# MGSD-V1  9B  30-SECOND ARM  (freeze v1.0 §8) - PROVISIONAL ONLY
# Admissible input: raw OHLCV of timeframe==30s ph2 rows.
# Families: S30-A opening momentum, S30-B 5m ORB. 20 variants, BH within.
# ======================================================================
import os, sys, csv, glob, json, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mgsd_lib as L

SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
bars = {}
for fn in sorted(glob.glob(os.path.join(SCR, 'ph2', 'V3_30s_*.csv'))):
    with open(fn, newline='') as fh:
        r = csv.reader(fh)
        hd = next(r)
        ix = {c: k for k, c in enumerate(hd)}
        for row in r:
            if len(row) != len(hd) or row[ix['timeframe']] != '30s':
                continue
            bars[(row[ix['date']], row[ix['timeEt']])] = (
                float(row[ix['open']]), float(row[ix['high']]),
                float(row[ix['low']]), float(row[ix['close']]),
                float(row[ix['volume']]))
days = sorted(set(k[0] for k in bars))
# slot order per day
slots = sorted(set(k[1] for k in bars))
S = len(slots)
sidx = {t: i for i, t in enumerate(slots)}
O = np.full((len(days), S), np.nan); H = np.full_like(O, np.nan)
Lo = np.full_like(O, np.nan); C = np.full_like(O, np.nan)
for (d, t), (o_, h_, l_, c_, v_) in bars.items():
    di = days.index(d)
    O[days.index(d), sidx[t]] = o_
    H[di, sidx[t]] = h_; Lo[di, sidx[t]] = l_; C[di, sidx[t]] = c_
# ATR28 on 30s bars (per day, causal within day; warm start after 28 slots)
TR = np.maximum(H - Lo, 0.0)
ATR = np.full_like(O, np.nan)
for di in range(len(days)):
    tr = TR[di]
    for s in range(28, S):
        w = tr[s - 27:s + 1]
        if not np.isnan(w).any():
            ATR[di, s] = w.mean()

COST = L.COST_BASE
STRESS = L.COST_RTH_STRESS
rng = np.random.default_rng(L.SEED)


def race(di, s_entry, dirv, stopd, exit_slots):
    """Entry at open of slot s_entry; stop-first; exit at close of
    s_entry+exit_slots-1 (or last slot)."""
    ent = O[di, s_entry]
    if np.isnan(ent) or np.isnan(stopd) or stopd <= 0:
        return None
    last = min(s_entry + exit_slots - 1, S - 1)
    lv = ent - dirv * stopd
    for s in range(s_entry, last + 1):
        if np.isnan(C[di, s]):
            last = s - 1
            break
        if (dirv > 0 and Lo[di, s] <= lv) or (dirv < 0 and H[di, s] >= lv):
            return -stopd
    if last < s_entry:
        return None
    return dirv * (C[di, last] - ent)


VAR = {}
# S30-A: first n bars net direction >= thr*ATR -> continuation
for n in (4, 10):
    for thr in (0.5, 1.0):
        for sm, ex in ((1.0, 10), (1.0, 30), (2.0, 10), (2.0, 30)):
            if (n, thr, sm, ex) in ((4, 0.5, 1.0, 30), (10, 1.0, 2.0, 10)):
                pass
            key = 'S30A_n%d_t%.1f_s%d_e%d' % (n, thr, int(sm * 10), ex)
            tr = []
            for di in range(len(days)):
                a = ATR[di, n - 1] if n - 1 >= 28 else ATR[di, 28] \
                    if not np.isnan(ATR[di, 28]) else np.nan
                # ATR warmup: use first available ATR (slot 28+); for n<28
                # use trailing ATR from the canonical prior day? frozen:
                # use day's slot-28 ATR as scale proxy computed AFTER n?
                # -> causal violation if n<28. Guard: only allow n>=?; use
                # scale = mean TR of first n bars instead (causal).
                scale = np.nanmean(TR[di, :n])
                mv = C[di, n - 1] - O[di, 0]
                if np.isnan(mv) or np.isnan(scale) or scale <= 0:
                    continue
                if abs(mv) >= thr * scale * n ** 0.5:
                    d_ = 1 if mv > 0 else -1
                    r = race(di, n, d_, sm * scale * n ** 0.5, ex * 2)
                    if r is not None:
                        tr.append((di, r))
            VAR[key] = tr
# S30-B: 5m ORB (slots 0..9), break close beyond +c*scale -> continuation
for cc in (0.0, 0.25):
    for sm, ex in ((1.0, 10), (2.0, 30)):
        key = 'S30B_c%.2f_s%d_e%d' % (cc, int(sm * 10), ex)
        tr = []
        for di in range(len(days)):
            hi5 = np.nanmax(H[di, :10]); lo5 = np.nanmin(Lo[di, :10])
            scale = np.nanmean(TR[di, :10])
            if np.isnan(hi5) or np.isnan(scale) or scale <= 0:
                continue
            for s in range(10, min(S - 1, 120)):
                if np.isnan(C[di, s]):
                    break
                d_ = 0
                if C[di, s] > hi5 + cc * scale * 3:
                    d_ = 1
                elif C[di, s] < lo5 - cc * scale * 3:
                    d_ = -1
                if d_:
                    r = race(di, s + 1, d_, sm * scale * 3.16, ex * 2)
                    if r is not None:
                        tr.append((di, r))
                    break
        VAR[key] = tr

# ---- stats + BH within arm ----
res = []
for key, tr in VAR.items():
    if len(tr) < 10:
        res.append({'key': key, 'n': len(tr), 'note': 'INSUFFICIENT'})
        continue
    x = np.array([t[1] for t in tr]) - STRESS
    dd = [t[0] for t in tr]
    uds = sorted(set(dd))
    di_ = {d: k for k, d in enumerate(uds)}
    dsum = np.zeros(len(uds)); dcnt = np.zeros(len(uds))
    for (d0, v0) in zip(dd, x):
        dsum[di_[d0]] += v0; dcnt[di_[d0]] += 1
    idx = rng.integers(0, len(uds), size=(5000, len(uds)))
    bs = dsum[idx].sum(1) / np.maximum(dcnt[idx].sum(1), 1)
    bs.sort()
    lo_ci, hi_ci = bs[int(.025 * 5000)], bs[int(.975 * 5000)]
    le = int((bs <= 0).sum()); ge = int((bs >= 0).sum())
    p = max(2 * min(le, ge) / 5000, 1 / 5001)
    w = x[x > 0]; l_ = x[x <= 0]
    res.append({'key': key, 'n': len(x), 'days': len(uds),
                'ev_stress': float(x.mean()),
                'wr': float((x > 0).mean()),
                'pf': float(w.sum() / -l_.sum()) if l_.sum() < 0 else float('inf'),
                'ci_lo': float(lo_ci), 'ci_hi': float(hi_ci), 'p': float(p)})
pv = np.array([r.get('p', 1.0) for r in res])
order = np.argsort(pv); qv = np.empty(len(pv)); prev = 1.0
for rank in range(len(pv) - 1, -1, -1):
    i = order[rank]; prev = min(prev, len(pv) * pv[i] / (rank + 1)); qv[i] = prev
for r, q_ in zip(res, qv):
    r['bh_q'] = float(q_)

with open(os.path.join(HERE, 'MGSD_V1_SUBMIN_30S_LEDGER.csv'), 'w',
          newline='') as f:
    cols = ['key', 'n', 'days', 'ev_stress', 'wr', 'pf', 'ci_lo', 'ci_hi',
            'p', 'bh_q', 'note']
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in res:
        w.writerow({k: ('%.4f' % v if isinstance(v, float) else v)
                    for k, v in r.items() if k in cols})
passers = [r for r in res if r.get('bh_q', 1) <= 0.05 and
           r.get('ci_lo', -1) > 0 and r.get('ev_stress', -1) > 0]
print('30s arm: %d variants, %d days coverage, provisional passers: %d'
      % (len(res), len(days), len(passers)))
for r in passers:
    print('  ', r['key'], 'ev %+.3f ci [%.3f,%.3f] q %.4f'
          % (r['ev_stress'], r['ci_lo'], r['ci_hi'], r['bh_q']))
json.dump({'variants': len(res), 'days': len(days),
           'passers': [r['key'] for r in passers]},
          open(os.path.join(HERE, 's30_summary.json'), 'w'))
