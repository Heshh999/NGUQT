#!/usr/bin/env python3
# WAVE 4B - anchor-field incrementality + stability (EXPLORATORY)
# Q1: does position (distance/ATR from anchor) predict fwd 30m BEYOND
#     velocity (prior 30m return)?   day-clustered bivariate OLS
# Q2: per-year slope stability. Q3: top/bottom-decile economics in POINTS.
import os, sys, json, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mgsd'))
import mgsd_lib as L
SEED = 20260828
G = L.load()
N = G['N']
mod, day, td = G['mod'], G['day'], G['tradedate']
o, c, em = G['o'], G['c'], G['em']
atr15 = G['atr15']; vwap = G['vwap']
obm = {}
for i in range(N):
    if mod[i] == 571 and day[i] not in obm:
        obm[day[i]] = i
samp = np.nonzero((mod >= 631) & (mod <= 900) & (mod % 5 == 0)
                  & ~np.isnan(atr15) & (atr15 > 0))[0]
samp = samp[(samp + 30 < N) & (samp >= 30)]
samp = samp[(em[samp + 30] - em[samp]) == 30]
samp = samp[(em[samp] - em[samp - 30]) == 30]
fwd = np.log(c[samp + 30] / c[samp]) * 1e4
mom = np.log(c[samp] / c[samp - 30]) * 1e4          # prior 30m, bp
open_px = np.array([o[obm[td[i]]] if td[i] in obm else np.nan for i in samp])
x_open = (c[samp] - open_px) / atr15[samp]
x_vwap = (c[samp] - vwap[samp]) / atr15[samp]
fwd_pts = (c[samp + 30] - c[samp])
m = ~np.isnan(x_open) & ~np.isnan(fwd) & ~np.isnan(mom) & ~np.isnan(x_vwap)
S = samp[m]
X = np.column_stack([np.ones(m.sum()), x_open[m], mom[m], x_vwap[m]])
y = fwd[m]
dl = np.array([td[i] for i in S])
uds = sorted(set(dl)); di = {d: k for k, d in enumerate(uds)}
dix = np.array([di[d] for d in dl])
K = X.shape[1]
XtX = np.zeros((len(uds), K, K)); Xty = np.zeros((len(uds), K))
for k in range(len(uds)):
    sel = dix == k
    Xd = X[sel]; XtX[k] = Xd.T @ Xd; Xty[k] = Xd.T @ y[sel]
def beta(sel):
    A = XtX[sel].sum(0); b = Xty[sel].sum(0)
    try:
        return np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        return np.full(K, np.nan)
b0 = beta(np.arange(len(uds)))
rng = np.random.default_rng(SEED)
BS = np.array([beta(rng.integers(0, len(uds), len(uds))) for _ in range(2000)])
names = ['const', 'x_open (position)', 'prior30m (velocity)', 'x_vwap']
print('BIVARIATE FIELD  fwd30m_bp ~ x_open + prior30m + x_vwap  (day-clustered, n=%d, days=%d)' % (m.sum(), len(uds)))
for k in range(K):
    v = np.sort(BS[:, k])
    lo, hi = v[50], v[1949]
    p = max(2 * min((v <= 0).sum(), (v >= 0).sum()) / 2000, 1 / 2001)
    print('  %-22s %+8.4f  CI[%+8.4f,%+8.4f]  p %.4f' % (names[k], b0[k], lo, hi, p))
# per-year x_open partial slope
print('\nPER-YEAR partial slope of x_open (with controls):')
yr = np.array([d[:4] for d in uds])
for yy in sorted(set(yr)):
    sel = np.nonzero(yr == yy)[0]
    bb = beta(sel)
    print('  %s  x_open %+8.4f   prior30 %+8.4f' % (yy, bb[1], bb[2]))
# top/bottom decile economics in points, momentum-controlled via matching
qs = np.quantile(x_open[m], [0.1, 0.9])
top = m.copy(); top[m] = x_open[m] >= qs[1]
bot = m.copy(); bot[m] = x_open[m] <= qs[0]
def cell(sel, sign):
    pts = sign * fwd_pts[sel]
    dls = [td[i] for i in samp[sel]]
    ud = sorted(set(dls)); dd = {d: k for k, d in enumerate(ud)}
    s_ = np.zeros(len(ud)); n_ = np.zeros(len(ud))
    for x2, d2 in zip(pts, dls):
        s_[dd[d2]] += x2; n_[dd[d2]] += 1
    ii = rng.integers(0, len(ud), size=(2000, len(ud)))
    bs = s_[ii].sum(1) / np.maximum(n_[ii].sum(1), 1)
    bs.sort()
    return pts.mean(), bs[50], bs[1949], len(pts), len(ud)
for lab, sel, sg in (('TOP decile, LONG  (with displacement)', top, +1),
                     ('BOT decile, SHORT (with displacement)', bot, -1)):
    mn, lo, hi, n_, d_ = cell(sel, sg)
    print('\n%s: mean fwd30 %+0.3f pts  CI[%+0.3f,%+0.3f]  n %d  days %d  (cost RT 0.87)'
          % (lab, mn, lo, hi, n_, d_))
    print('   gross/cost per 30m hold: %.2fx' % (mn / 0.87))
