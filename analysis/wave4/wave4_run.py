#!/usr/bin/env python3
# ======================================================================
# ANOMALY WAVE 4 - MATHEMATICAL STRUCTURE MAPS  (EXPLORATORY)
# ======================================================================
# STATUS: all 2019-2026 data is EXPOSED development data. Everything
# here is hypothesis-generating knowledge. NOTHING is a confirmed edge,
# nothing may be promoted from this run, and any strategy derived from
# these maps requires its own preregistration + future-data evidence.
#
# Lineage (not re-tested here): daily TSMOM refuted; SHOCK-CONT failed;
# MEMORY-PRED real/sub-cost; A4 aged-run reversal real/sub-material;
# MOM-H2 30m trend real; F07 VWAP-fade HARMFUL (MGSD); F09 open gap-fade
# near-miss SPENT (MGSD - not rescued here; the anchor module measures
# the general field of which the open-gap is one already-spent cell).
#
# Modules (frozen before outcomes of this run):
#  A  minute-of-day drift decomposition        48 half-hour cells
#  B  variance-ratio / diffusion map           strata x q in {2,5,10,30}
#  C  anchor-attraction drift field            4 anchors x 10 bins + slope
#  D  first-passage barrier asymmetry          strata x conditioning
#  E  intraday ACF of 1m returns              lags 1..60 by stratum
# Multiplicity: BH within each module; all cells published.
# Seed 20260828. Day-clustered bootstrap B=4000.
# SUBMITS NO ORDERS. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import os, sys, json, time, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mgsd'))
import mgsd_lib as L

SEED = 20260828
B = 4000
rng = np.random.default_rng(SEED)
t0 = time.time()
G = L.load()
N = G['N']
mod, day, td = G['mod'], G['day'], G['tradedate']
o, h, l, c = G['o'], G['h'], G['l'], G['c']
em, step1 = G['em'], G['step1']
atr15, vwap = G['atr15'], G['vwap']
days_all = sorted(set(day))
OUT = {}
LOG = []
def say(s=''):
    print(s); LOG.append(s)

r1 = np.full(N, np.nan)
ok = step1.copy(); ok &= c > 0
ok[1:] &= c[:-1] > 0
idx = np.nonzero(ok)[0]; idx = idx[idx >= 1]
r1[idx] = np.log(c[idx] / c[idx - 1]) * 1e4        # bp

def dc_mean(vals, dlist, iters=B, seed=SEED):
    uds = sorted(set(dlist)); di = {d: k for k, d in enumerate(uds)}
    ds = np.zeros(len(uds)); dcnt = np.zeros(len(uds))
    for x, d0 in zip(vals, dlist):
        ds[di[d0]] += x; dcnt[di[d0]] += 1
    if len(uds) < 30:
        return float(np.mean(vals)), np.nan, np.nan, np.nan
    rg = np.random.default_rng(seed)
    ii = rg.integers(0, len(uds), size=(iters, len(uds)))
    bs = ds[ii].sum(1) / np.maximum(dcnt[ii].sum(1), 1)
    bs.sort()
    le = int((bs <= 0).sum()); ge = int((bs >= 0).sum())
    p = max(2 * min(le, ge) / iters, 1 / (iters + 1))
    return float(np.mean(vals)), float(bs[int(.025 * iters)]), \
        float(bs[int(.975 * iters)]), float(p)

def bh(ps):
    p = np.array([1.0 if x != x else x for x in ps])
    o_ = np.argsort(p); q = np.empty(len(p)); prev = 1.0
    for r_ in range(len(p) - 1, -1, -1):
        i = o_[r_]; prev = min(prev, len(p) * p[i] / (r_ + 1)); q[i] = prev
    return q

say('=' * 96)
say('ANOMALY WAVE 4  -  MATHEMATICAL STRUCTURE MAPS   (EXPLORATORY; all data exposed)')
say('=' * 96)

# ================================================================ A
say('\nMODULE A  MINUTE-OF-DAY DRIFT DECOMPOSITION  (48 half-hour cells, bp/half-hour)')
cells = []
for hstart in range(0, 1440, 30):
    m = (mod - 1) // 30 == hstart // 30
    m &= ~np.isnan(r1)
    v = r1[m]; dl = [td[i] for i in np.nonzero(m)[0]]
    if len(v) < 5000:
        continue
    tot_by_day = collections.defaultdict(float)
    for x, d0 in zip(v, dl):
        tot_by_day[d0] += x
    dv = np.array(list(tot_by_day.values()))
    dd = list(tot_by_day.keys())
    mean, lo, hi, p = dc_mean(dv, dd)
    cells.append({'win': '%02d:%02d-%02d:%02d' % (hstart // 60, hstart % 60,
                  ((hstart + 30) // 60) % 24, (hstart + 30) % 60),
                  'mod0': hstart, 'ndays': len(dd),
                  'bp_per_halfhour': mean, 'lo': lo, 'hi': hi, 'p': p})
q = bh([x['p'] for x in cells])
for x, qq in zip(cells, q):
    x['q'] = float(qq)
sig = [x for x in cells if x['q'] <= 0.05]
say('  %d cells; BH q<=0.05: %d' % (len(cells), len(sig)))
for x in sorted(sig, key=lambda x: x['mod0']):
    say('    %-12s  %+7.3f bp/half-hour  CI[%+.3f,%+.3f]  q %.4f'
        % (x['win'], x['bp_per_halfhour'], x['lo'], x['hi'], x['q']))
tot = sum(x['bp_per_halfhour'] for x in cells)
rth = sum(x['bp_per_halfhour'] for x in cells if 570 <= x['mod0'] < 960)
on_ = tot - rth
say('  cumulative drift: total %+.2f bp/day   RTH %+.2f   overnight %+.2f' % (tot, rth, on_))
OUT['A'] = cells

# ================================================================ B
say('\nMODULE B  VARIANCE-RATIO / DIFFUSION MAP  (VR(q)=Var(r_q)/(q Var(r_1)), non-overlapping)')
stratdef = {'S2night': (1081, 1440 + 120), 'S3earlyPM': (121, 480),
            'S4latePM': (481, 569), 'S5open': (571, 600),
            'S6morn': (601, 690), 'S7midday': (691, 840),
            'S8aft': (841, 930), 'S9close': (931, 960)}
def in_strat(mm, a, b_):
    if b_ > 1440:
        return (mm >= a) | (mm <= b_ - 1440)
    return (mm >= a) & (mm <= b_)
vrres = []
for snm, (a, b_) in stratdef.items():
    m = in_strat(mod, a, b_) & ~np.isnan(r1)
    ii = np.nonzero(m)[0]
    # group contiguous runs within (tradedate)
    byday = collections.defaultdict(list)
    for i in ii:
        byday[td[i]].append(i)
    for qq in (2, 5, 10, 30):
        # per-day: non-overlapping q-sums and 1-sums
        s1 = []; sq = []; dl1 = []; dlq = []
        for d0, lst in byday.items():
            arr = r1[np.array(lst)]
            s1.append(arr); dl1 += [d0] * len(arr)
            nb = len(arr) // qq
            if nb:
                sq.append(arr[:nb * qq].reshape(nb, qq).sum(1))
                dlq += [d0] * nb
        v1 = np.concatenate(s1); vq = np.concatenate(sq) if sq else np.array([])
        if len(vq) < 500:
            continue
        # day-bootstrap the ratio
        uds = sorted(byday)
        di = {d: k for k, d in enumerate(uds)}
        # day-level sums of squares & counts
        ss1 = np.zeros(len(uds)); n1 = np.zeros(len(uds))
        ssq = np.zeros(len(uds)); nq = np.zeros(len(uds))
        mu1 = v1.mean(); muq = vq.mean()
        for x, d0 in zip(v1, dl1):
            ss1[di[d0]] += (x - mu1) ** 2; n1[di[d0]] += 1
        for x, d0 in zip(vq, dlq):
            ssq[di[d0]] += (x - muq) ** 2; nq[di[d0]] += 1
        vr = (ssq.sum() / nq.sum()) / (qq * ss1.sum() / n1.sum())
        rg = np.random.default_rng(SEED + qq)
        iidx = rg.integers(0, len(uds), size=(2000, len(uds)))
        bs = (ssq[iidx].sum(1) / np.maximum(nq[iidx].sum(1), 1)) / \
             np.maximum(qq * ss1[iidx].sum(1) / np.maximum(n1[iidx].sum(1), 1), 1e-12)
        bs.sort()
        lo, hi = bs[int(.025 * 2000)], bs[int(.975 * 2000)]
        le = int((bs <= 1).sum()); ge = int((bs >= 1).sum())
        p = max(2 * min(le, ge) / 2000, 1 / 2001)
        vrres.append({'stratum': snm, 'q': qq, 'VR': float(vr),
                      'lo': float(lo), 'hi': float(hi), 'p': float(p),
                      'nq_windows': int(len(vq))})
q = bh([x['p'] for x in vrres])
for x, qq_ in zip(vrres, q):
    x['q_bh'] = float(qq_)
say('  %-10s %4s %8s %16s %9s  (VR<1 = mean-reverting, >1 = trending)'
    % ('stratum', 'q', 'VR', '95% CI', 'BH q'))
for x in vrres:
    flag = ' *' if x['q_bh'] <= 0.05 else ''
    say('  %-10s %4d %8.4f [%6.4f,%6.4f] %9.4f%s'
        % (x['stratum'], x['q'], x['VR'], x['lo'], x['hi'], x['q_bh'], flag))
OUT['B'] = vrres

# ================================================================ C
say('\nMODULE C  ANCHOR-ATTRACTION DRIFT FIELD  (forward 30m bp vs distance/ATR15)')
say('  NOTE: the open-gap/prior-close cell is SPENT (MGSD F09); field is knowledge only.')
# forward 30m return, sampled every 5 minutes in RTH to limit overlap
samp = np.nonzero((mod >= 601) & (mod <= 900) & (mod % 5 == 0)
                  & ~np.isnan(atr15) & (atr15 > 0))[0]
fok = samp + 30 < N
samp = samp[fok]
contig = (em[samp + 30] - em[samp]) == 30
samp = samp[contig]
fwd = np.log(c[samp + 30] / c[samp]) * 1e4
prior_close = np.array([G['prior_rth'].get(td[i], {}).get('close', np.nan)
                        for i in samp])
open_px = np.array([o[G['open_bar_by_td'].get(td[i], i)]
                    if td[i] in G.get('open_bar_by_td', {}) else np.nan
                    for i in samp]) if 'open_bar_by_td' in G else None
# build open_bar map (mgsd_lib.load doesn't add it)
obm = {}
for i in range(N):
    if mod[i] == 571 and day[i] not in obm:
        obm[day[i]] = i
open_px = np.array([o[obm[td[i]]] if td[i] in obm else np.nan for i in samp])
onmid = np.array([(G['overnight'][td[i]]['hi'] + G['overnight'][td[i]]['lo']) / 2
                  if td[i] in G['overnight'] and G['overnight'][td[i]]['n'] > 200
                  else np.nan for i in samp])
anchors = {'prior_close': prior_close, 'day_open': open_px,
           'on_mid': onmid, 'vwap': vwap[samp]}
cres = []
for anm, av in anchors.items():
    x = (c[samp] - av) / atr15[samp]
    m = ~np.isnan(x) & ~np.isnan(fwd)
    xv, yv = x[m], fwd[m]
    dl = [td[i] for i in samp[m]]
    # day-clustered OLS slope via day-level sufficient stats
    uds = sorted(set(dl)); di = {d: k for k, d in enumerate(uds)}
    sx = np.zeros(len(uds)); sy = np.zeros(len(uds))
    sxx = np.zeros(len(uds)); sxy = np.zeros(len(uds)); nn = np.zeros(len(uds))
    for xi, yi, d0 in zip(xv, yv, dl):
        k = di[d0]
        sx[k] += xi; sy[k] += yi; sxx[k] += xi * xi; sxy[k] += xi * yi
        nn[k] += 1
    def slope(sel):
        Sx, Sy, Sxx, Sxy, Nn = (sx[sel].sum(), sy[sel].sum(),
                                sxx[sel].sum(), sxy[sel].sum(), nn[sel].sum())
        den = Sxx - Sx * Sx / Nn
        return (Sxy - Sx * Sy / Nn) / den if den > 0 else np.nan
    beta = slope(np.arange(len(uds)))
    rg = np.random.default_rng(SEED + hash(anm) % 1000)
    ii = rg.integers(0, len(uds), size=(2000, len(uds)))
    bs = np.array([slope(ii[k]) for k in range(2000)])
    bs = np.sort(bs[~np.isnan(bs)])
    lo, hi = bs[int(.025 * len(bs))], bs[int(.975 * len(bs))]
    le = int((bs <= 0).sum()); ge = int((bs >= 0).sum())
    p = max(2 * min(le, ge) / len(bs), 1 / (len(bs) + 1))
    # decile field
    qs = np.quantile(xv, np.linspace(0, 1, 11))
    field = []
    for b_ in range(10):
        mm = (xv >= qs[b_]) & (xv <= qs[b_ + 1])
        field.append({'bin': b_, 'x_mid': float(np.median(xv[mm])),
                      'fwd30_bp': float(yv[mm].mean()), 'n': int(mm.sum())})
    cres.append({'anchor': anm, 'slope_bp_per_ATR': float(beta),
                 'lo': float(lo), 'hi': float(hi), 'p': float(p),
                 'n': int(m.sum()), 'field': field})
q = bh([x['p'] for x in cres])
for x, qq_ in zip(cres, q):
    x['q_bh'] = float(qq_)
    say('  %-12s slope %+8.4f bp/ATR  CI[%+.4f,%+.4f]  BH q %.4f  n %d %s'
        % (x['anchor'], x['slope_bp_per_ATR'], x['lo'], x['hi'], x['q_bh'],
           x['n'], '(negative = attraction)' if x['slope_bp_per_ATR'] < 0
           else '(positive = repulsion/trend)'))
    ff = x['field']
    say('     deciles: ' + ' '.join('%+.1f' % f['fwd30_bp'] for f in ff))
OUT['C'] = cres

# ================================================================ D
say('\nMODULE D  FIRST-PASSAGE BARRIER ASYMMETRY  P(+1 ATR15 before -1 ATR15), 120m cap')
sample_mods = [600, 660, 720, 780, 840, 900]
dres = []
for smod in sample_mods:
    ii = np.nonzero((mod == smod) & ~np.isnan(atr15) & (atr15 > 0))[0]
    ii = ii[ii + 120 < N]
    up = np.zeros(len(ii)); dn = np.zeros(len(ii)); und = np.zeros(len(ii))
    for k, i in enumerate(ii):
        a = atr15[i]
        hi_lv, lo_lv = c[i] + a, c[i] - a
        r_ = 0
        for j in range(i + 1, min(i + 121, N)):
            if em[j] - em[j - 1] != 1:
                break
            if h[j] >= hi_lv and l[j] <= lo_lv:
                r_ = 3; break
            if h[j] >= hi_lv:
                r_ = 1; break
            if l[j] <= lo_lv:
                r_ = 2; break
        up[k] = r_ == 1; dn[k] = r_ == 2; und[k] = r_ in (0, 3)
    dec = up + dn > 0
    pu = up[dec].mean() if dec.sum() else np.nan
    dl = [td[i] for i in ii[dec]]
    mean, lo, hi, p = dc_mean(up[dec] - 0.5, dl, iters=2000)
    dres.append({'sample_mod': '%02d:%02d' % (smod // 60, smod % 60),
                 'n_decided': int(dec.sum()), 'P_up_first': float(pu),
                 'edge_vs_half': mean, 'lo': lo, 'hi': hi, 'p': p,
                 'ambig_or_undecided': int(und.sum())})
# conditioned on prior 30m sign at 12:00 sample
i12 = np.nonzero((mod == 720) & ~np.isnan(atr15) & (atr15 > 0))[0]
i12 = i12[(i12 + 120 < N) & (i12 >= 30)]
prior = np.sign(c[i12] - c[i12 - 30])
for lab, msk in (('after +30m up', prior > 0), ('after -30m dn', prior < 0)):
    sel = i12[msk]
    upn = dnn = 0
    dl = []
    vals = []
    for i in sel:
        a = atr15[i]; hi_lv, lo_lv = c[i] + a, c[i] - a
        r_ = 0
        for j in range(i + 1, min(i + 121, N)):
            if em[j] - em[j - 1] != 1:
                break
            if h[j] >= hi_lv and l[j] <= lo_lv:
                r_ = 3; break
            if h[j] >= hi_lv:
                r_ = 1; break
            if l[j] <= lo_lv:
                r_ = 2; break
        if r_ in (1, 2):
            vals.append(1.0 if r_ == 1 else 0.0)
            dl.append(td[i])
    mean, lo, hi, p = dc_mean(np.array(vals) - 0.5, dl, iters=2000)
    dres.append({'sample_mod': '12:00 ' + lab, 'n_decided': len(vals),
                 'P_up_first': float(np.mean(vals)), 'edge_vs_half': mean,
                 'lo': lo, 'hi': hi, 'p': p, 'ambig_or_undecided': -1})
q = bh([x['p'] for x in dres])
for x, qq_ in zip(dres, q):
    x['q_bh'] = float(qq_)
    say('  %-22s P(up first) %.4f  edge %+.4f  CI[%+.4f,%+.4f]  BH q %.4f  n %d'
        % (x['sample_mod'], x['P_up_first'], x['edge_vs_half'], x['lo'],
           x['hi'], x['q_bh'], x['n_decided']))
OUT['D'] = dres

# ================================================================ E
say('\nMODULE E  INTRADAY ACF OF 1m RETURNS  (lags 1..60; pooled RTH vs overnight)')
eres = {}
for snm, msk in (('RTH', (mod >= 571) & (mod <= 960)),
                 ('OVERNIGHT', (mod >= 1081) | (mod <= 569))):
    ii = np.nonzero(msk & ~np.isnan(r1))[0]
    x = r1[ii]
    xm = x - x.mean()
    var = (xm ** 2).mean()
    acf = []
    for lag in range(1, 61):
        a = ii[:-lag]; b_ = ii[lag:]
        valid = (b_ - a) == lag
        aa = r1[a[valid]] - x.mean(); bb = r1[b_[valid]] - x.mean()
        acf.append(float((aa * bb).mean() / var))
    eres[snm] = acf
    neg = [k + 1 for k in range(20) if acf[k] < -0.005]
    say('  %-10s lag1 %+.4f  lag2 %+.4f  lag3 %+.4f  lag5 %+.4f  lag10 %+.4f'
        % (snm, acf[0], acf[1], acf[2], acf[4], acf[9]))
    say('             lags<=20 with acf < -0.005: %s' % neg)
OUT['E'] = eres

say('\nDONE (%.0fs).  Cells: A %d + B %d + C %d + D %d = %d BH-corrected; E descriptive.'
    % (time.time() - t0, len(cells), len(vrres), len(cres), len(dres),
       len(cells) + len(vrres) + len(cres) + len(dres)))
say('EXPLORATORY. All data exposed. Nothing here is a confirmed or tradable edge.')
json.dump(OUT, open(os.path.join(HERE, 'WAVE4_RAW.json'), 'w'), indent=0,
          default=float)
open(os.path.join(HERE, 'WAVE4_OUTPUT.txt'), 'w').write('\n'.join(LOG) + '\n')
