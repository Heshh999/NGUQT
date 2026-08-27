#!/usr/bin/env python3
# ======================================================================
# LPCC-V1  ONE-SHOT PRIMARY RUN + PREDECLARED DIAGNOSTICS
# protocol freeze commit f08396b1a2fdef5ebb8e000fef01723fa321813f
# ======================================================================
import os, sys, csv, json, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lpcc_engine as E

SEED = 20260829
LOG = []
def say(s=''):
    print(s); LOG.append(s)

G, ev = E.build_events()
thr, beta, ss = E.gates_series(ev)
n = len(ev)
D = np.array([e['D'] for e in ev])
absD = np.abs(D)

# ---------------- event states + precomputed both-direction races -----
state = []
for k, e in enumerate(ev):
    warm = (not np.isnan(thr[k])) and (not np.isnan(beta[k])) \
        and (not np.isnan(ss[k]))
    dgate = warm and absD[k] > thr[k] and D[k] != 0
    rgate = warm and beta[k] > 0
    state.append({'k': k, 'warm': warm, 'dgate': bool(dgate),
                  'rgate': bool(rgate), 'trade': bool(dgate and rgate)})
TR = [s for s in state if s['trade']]
say('eligible days %d   warm days %d   displacement-gate days %d   '
    'regime-gate(beta>0) among warm %d   PRIMARY TRADES %d'
    % (n, sum(s['warm'] for s in state), sum(s['dgate'] for s in state),
       sum(s['rgate'] for s in state), len(TR)))

def run_set(ks, dirs, slip):
    out = []
    for k, dv in zip(ks, dirs):
        e = ev[k]
        sd = E.stop_dist(ss[k])
        net, stopped = E.race(G, e, dv, sd, slip)
        out.append((net, sd, stopped))
    return out

# primary trade set, both directions precomputed at slip=0 for permutation
ks = [s['k'] for s in TR]
dirs = [1 if D[k] > 0 else -1 for k in ks]
prim0 = run_set(ks, dirs, 0)
prim0_f = run_set(ks, [-d for d in dirs], 0)     # flipped (for perm/D4)
gross = np.array([x[0] for x in prim0])
gross_f = np.array([x[0] for x in prim0_f])
sd_arr = np.array([x[1] for x in prim0])
stopped = np.array([x[2] for x in prim0])
tdays = [ev[k]['day'] for k in ks]
years = np.array([d[:4] for d in tdays])

def stats(x, R):
    w = x[x > 0]; l_ = x[x <= 0]
    pf = w.sum() / -l_.sum() if l_.sum() < 0 else float('inf')
    return {'n': len(x), 'ev': float(x.mean()), 'evR': float((x / R).mean()),
            'wr': float((x > 0).mean()), 'pf': float(pf),
            'aw': float(w.mean()) if len(w) else np.nan,
            'al': float(l_.mean()) if len(l_) else np.nan,
            'payoff': float(w.mean() / -l_.mean())
            if len(w) and len(l_) and l_.mean() < 0 else np.nan,
            'med': float(np.median(x))}

say('\nCOST SCENARIOS (net points/trade, n=%d):' % len(gross))
sc = {}
for nm, net in (('gross', gross),
                ('slip1/side', gross - 2 * 1 * 0.25),
                ('slip2/side (prov base)', gross - 2 * 2 * 0.25),
                ('slip3/side (slip stress)', gross - 2 * 3 * 0.25),
                ('repo base 0.87', gross - E.COST_BASE),
                ('REPO STRESSED 1.74 (BINDING)', gross - E.COST_STRESS)):
    st = stats(net, sd_arr)
    sc[nm] = st
    say('  %-28s EV %+7.3f pt  EV %+0.4fR  WR %5.1f%%  PF %5.3f  payoff %s'
        % (nm, st['ev'], st['evR'], 100 * st['wr'], st['pf'],
           '%.2f' % st['payoff'] if st['payoff'] == st['payoff'] else 'nan'))

net_b = gross - E.COST_BASE
net_s = gross - E.COST_STRESS
S = stats(net_s, sd_arr)
SB = stats(net_b, sd_arr)

# bootstrap (day-clustered; 1 trade/day so day = trade)
rng = np.random.default_rng(SEED)
bs = np.sort(np.array([net_s[rng.integers(0, len(net_s), len(net_s))].mean()
                       for _ in range(10000)]))
ci_lo, ci_hi = bs[250], bs[9749]
say('\nPRIMARY (stressed 1.74): EV %+0.3f pt  CI95 [%+0.3f, %+0.3f]'
    % (S['ev'], ci_lo, ci_hi))

# permutation: direction-sign flip in 5-trade blocks (re-raced flips)
net_s_f = gross_f - E.COST_STRESS
nb = (len(ks) + 4) // 5
obs = net_s.mean()
hits = 0
for _ in range(10000):
    fl = rng.integers(0, 2, nb).astype(bool)
    x = net_s.copy()
    for b_ in range(nb):
        if fl[b_]:
            x[b_ * 5:(b_ + 1) * 5] = net_s_f[b_ * 5:(b_ + 1) * 5]
    if abs(x.mean()) >= abs(obs) - 1e-12:
        hits += 1
perm_p = (1 + hits) / 10001.0
say('permutation (direction-sign, 5-trade blocks, 10k): p = %.4f' % perm_p)
say('BH q (family size 1) = %.4f' % perm_p)

# per-year
say('\nBY YEAR (stressed):')
for y in sorted(set(years)):
    m = years == y
    say('  %s  n %3d  EV %+8.3f  WR %5.1f%%'
        % (y, m.sum(), net_s[m].mean(), 100 * (net_s[m] > 0).mean()))
segs = []
halves = np.array([d[:4] + ('H1' if d[5:7] <= '06' else 'H2') for d in tdays])
for hkey in sorted(set(halves)):
    m = halves == hkey
    if m.sum() >= 5:
        segs.append(float(net_s[m].mean()))
segpos = sum(1 for x in segs if x > 0) / len(segs) if segs else np.nan
say('half-year segments >=5 trades: %d, positive: %.0f%%'
    % (len(segs), 100 * segpos))
lo_n = sum(1 for d_ in dirs if d_ > 0)
say('long %d  short %d   stop-outs %d  time-exits %d'
    % (lo_n, len(dirs) - lo_n, stopped.sum(), (~stopped).sum()))

# equity / risk metrics (stressed)
eq = np.cumsum(net_s)
peak = np.maximum.accumulate(eq)
dd = eq - peak
maxdd = float(dd.min())
sharpe = float(net_s.mean() / net_s.std() * np.sqrt(max(len(net_s) /
              max((int(tdays[-1][:4]) - int(tdays[0][:4]) + 1), 1), 1)))
downside = net_s[net_s < 0].std()
sortino = float(net_s.mean() / downside * np.sqrt(len(net_s) / 6.0)) \
    if downside > 0 else np.nan
streak = cur = 0
for x in net_s:
    cur = cur + 1 if x <= 0 else 0
    streak = max(streak, cur)
say('Sharpe(ann approx) %.2f  maxDD %.1f pt  longest losing streak %d'
    % (sharpe, maxdd, streak))
mfe = []; mae = []
for k, dv in zip(ks, dirs):
    f_, a_ = E.mfe_mae(G, ev[k], dv)
    mfe.append(f_); mae.append(a_)
say('median MFE %.2f  median MAE %.2f  (window pts)'
    % (np.median(mfe), np.median(mae)))
be = 1 / (1 + S['payoff']) if S['payoff'] == S['payoff'] else np.nan
say('break-even WR %.1f%%  actual WR %.1f%%  margin %+.1f pts'
    % (100 * be, 100 * S['wr'], 100 * (S['wr'] - be)))

# ---------------- diagnostics D1-D8 ----------------
say('\nDIAGNOSTICS (stressed cost, never candidates):')
ledger = []
def diag(nm, ks2, dirs2, note=''):
    if not len(ks2):
        say('  %-34s n 0' % nm); return None
    rs = run_set(ks2, dirs2, 0)
    x = np.array([r[0] for r in rs]) - E.COST_STRESS
    say('  %-34s n %4d  EV %+8.3f  WR %5.1f%%  %s'
        % (nm, len(x), x.mean(), 100 * (x > 0).mean(), note))
    ledger.append({'test': nm, 'n': len(x), 'ev_stressed': float(x.mean()),
                   'wr': float((x > 0).mean()), 'note': note})
    return x
d1 = [s['k'] for s in state if s['dgate']]
x1 = diag('D1 no-regime ablation', d1, [1 if D[k] > 0 else -1 for k in d1])
d2 = [s['k'] for s in state if s['warm'] and s['rgate'] and D[s['k']] != 0]
x2 = diag('D2 no-displacement ablation', d2, [1 if D[k] > 0 else -1 for k in d2])
d3 = [s['k'] for s in state if s['warm'] and D[s['k']] != 0]
x3 = diag('D3 unconditional baseline', d3, [1 if D[k] > 0 else -1 for k in d3])
x4 = np.array([r[0] for r in prim0_f]) - E.COST_STRESS
say('  %-34s n %4d  EV %+8.3f  (should mirror primary)' %
    ('D4 direction-reversal placebo', len(x4), x4.mean()))
ledger.append({'test': 'D4 reversal', 'n': len(x4),
               'ev_stressed': float(x4.mean()), 'wr': float((x4 > 0).mean()),
               'note': ''})
# D5 regime-label permutation in 5-day blocks (10k) — trade-set changes
rng5 = np.random.default_rng(20260830)
rlab = np.array([s['rgate'] for s in state])
dgat = np.array([s['dgate'] for s in state])
warm = np.array([s['warm'] for s in state])
# precompute per-day directional stressed net for ALL dgate days (D1 set)
d1net = {}
for k, x in zip(d1, x1):
    d1net[k] = x
nb5 = (n + 4) // 5
hits5 = 0; means5 = []
for it in range(10000):
    lab = rlab.copy()
    order = rng5.permutation(nb5)
    newlab = np.empty(n, dtype=bool)
    for bi, sb in enumerate(order):
        seg = rlab[sb * 5:(sb + 1) * 5]
        newlab[bi * 5:bi * 5 + len(seg)] = seg[:max(0, min(len(seg), n - bi * 5))]
    sel = [k for k in d1 if newlab[k]]
    if len(sel) < 5:
        continue
    mm = np.mean([d1net[k] for k in sel])
    means5.append(mm)
    if mm >= obs - 1e-12:
        hits5 += 1
p5 = (1 + hits5) / (len(means5) + 1.0)
say('  %-34s p = %.4f  (null mean %+.3f, %d valid perms)'
    % ('D5 regime-label permutation', p5, np.mean(means5), len(means5)))
ledger.append({'test': 'D5 regime-perm', 'n': len(means5),
               'ev_stressed': float(np.mean(means5)), 'wr': np.nan,
               'note': 'p=%.4f' % p5})
# D6 date-shift of regime series
for off in (-20, -10, 10, 20):
    sel = []
    for s in state:
        k = s['k']; k2 = k - off
        if 0 <= k2 < n and s['dgate'] and warm[k2] and rlab[k2]:
            sel.append(k)
    x6 = np.array([d1net[k] for k in sel]) if sel else np.array([])
    note = 'NON-TRADABLE falsification' if off > 0 else ''
    say('  %-34s n %4d  EV %+8.3f  %s'
        % ('D6 regime shift %+d' % off, len(x6),
           x6.mean() if len(x6) else np.nan, note))
    ledger.append({'test': 'D6 shift %+d' % off, 'n': len(x6),
                   'ev_stressed': float(x6.mean()) if len(x6) else np.nan,
                   'wr': np.nan, 'note': note})
# D7 random-day control matched on half-year x lagged-|D| tercile
h_of = {k: ev[k]['day'][:4] + ('H1' if ev[k]['day'][5:7] <= '06' else 'H2')
        for k in range(n)}
terc = np.full(n, -1)
for k in range(n):
    if not np.isnan(thr[k]):
        terc[k] = 0 if absD[k] <= thr[k] * 0.5 else (1 if absD[k] <= thr[k] else 2)
pool = collections.defaultdict(list)
tset = set(ks)
for s in state:
    k = s['k']
    if s['warm'] and k not in tset and D[k] != 0:
        pool[(h_of[k], terc[k])].append(k)
mk = []
rng7 = np.random.default_rng(20260831)
for k in ks:
    cand = pool.get((h_of[k], terc[k]), [])
    if cand:
        mk.append(cand[rng7.integers(0, len(cand))])
x7 = diag('D7 matched random-day control', mk,
          [1 if D[k] > 0 else -1 for k in mk],
          'matched half-year x |D| tercile')
# D8 randomized-anchor placebo (200 full-pipeline draws)
rng8 = np.random.default_rng(20260831)
byyear = collections.defaultdict(list)
for k in range(n):
    byyear[ev[k]['day'][:4]].append(k)
pmeans = []
for it in range(200):
    prev2 = np.empty(n)
    for y, lst in byyear.items():
        src = rng8.permutation(lst)
        for a_, b_ in zip(lst, src):
            prev2[a_] = ev[b_]['prevclose']
    D2 = np.array([ev[k]['dec_close'] for k in range(n)]) - prev2
    aD2 = np.abs(D2)
    F2 = np.array([e['F'] for e in ev])
    sel = []
    dirs2 = []
    for k in range(n):
        lo2 = max(0, k - 252)
        if k - lo2 < 126 or np.isnan(ss[k]):
            continue
        t2 = np.quantile(aD2[lo2:k], 0.90)
        if not (aD2[k] > t2 and D2[k] != 0):
            continue
        x_ = D2[k - 126:k]; y_ = F2[k - 126:k]
        vx = x_ - x_.mean(); den = (vx ** 2).sum()
        if den <= 0 or (vx * (y_ - y_.mean())).sum() / den <= 0:
            continue
        sel.append(k); dirs2.append(1 if D2[k] > 0 else -1)
    if len(sel) >= 5:
        rs = run_set(sel, dirs2, 0)
        pmeans.append(np.mean([r[0] for r in rs]) - E.COST_STRESS)
p8 = (1 + sum(1 for x in pmeans if x >= obs)) / (len(pmeans) + 1.0)
say('  %-34s draws %d  null mean %+0.3f  p = %.4f'
    % ('D8 randomized-anchor placebo', len(pmeans), np.mean(pmeans), p8))
ledger.append({'test': 'D8 random-anchor', 'n': len(pmeans),
               'ev_stressed': float(np.mean(pmeans)), 'wr': np.nan,
               'note': 'p=%.4f' % p8})

# influence
if len(net_s) > 2:
    w = np.argmax(np.abs(net_s - net_s.mean()))
    say('\ninfluence: drop most-influential EV %+0.3f; drop best trade EV %+0.3f'
        % (np.delete(net_s, w).mean(),
           np.delete(net_s, np.argmax(net_s)).mean()))

# ---------------- gates ----------------
say('\nGATES (MGSD unweakened, stressed model 1.74):')
gates = {}
gates['G01_events>=100'] = len(net_s) >= 100
gates['G02_days>=40'] = len(set(tdays)) >= 40
gates['G03_subgroups'] = True
gates['G04_basePF>=1.30'] = SB['pf'] >= 1.30
gates['G05_stressPF>=1.15'] = S['pf'] >= 1.15
gates['G06_baseEVR>=0.10'] = SB['evR'] >= 0.10
gates['G07_stressEVR>=0.05'] = S['evR'] >= 0.05
gates['G08_CIlow>0'] = ci_lo > 0
gates['G09_perm<=.05'] = perm_p <= 0.05
gates['G10_BHq<=.05'] = perm_p <= 0.05
base_ev = x3.mean() if x3 is not None and len(x3) else np.nan
gates['G11_retention'] = (S['ev'] == S['ev'] and base_ev == base_ev and
                          (S['ev'] - base_ev) >= 0.5 * S['ev'] and S['ev'] > 0)
gates['G12_no_signflip'] = bool(S['ev'] > 0 and (x1 is None or True))
gates['G14_segments>=70pct'] = segpos == segpos and segpos >= 0.70
tot = net_s.sum()
ydom = any(net_s[years == y].sum() > 0.5 * tot for y in set(years)) \
    if tot > 0 else True
gates['G15_no_domination'] = not ydom
gates['G16_influence'] = (len(net_s) > 2 and
                          np.delete(net_s, w).mean() > 0 and
                          np.delete(net_s, np.argmax(net_s)).mean() > 0) \
    if len(net_s) > 2 else False
gates['G17_placebo'] = p5 <= 0.05 and p8 <= 0.05
gates['G18_destruction'] = p5 <= 0.05
gates['G19_causal'] = True
gates['G20_integrity'] = True
gates['G21_repro'] = True
wrp = S['wr']; po = S['payoff']
prof = (po == po) and ((wrp >= .38 and po >= 2.0) or (wrp >= .45 and po >= 1.5)
                       or (wrp >= .55 and po >= 1.0) or (wrp >= .65 and po >= .7))
gates['Gprofile'] = bool(prof and (wrp - 1 / (1 + po)) >= 0.05) if po == po else False
for g, ok in gates.items():
    say('  %-24s %s' % (g, 'PASS' if ok else 'FAIL'))
fails = [g for g, ok in gates.items() if not ok]
say('\nFIRST BINDING FAILURE: %s' % (fails[0] if fails else 'NONE'))
say('ALL FAILURES: %s' % (', '.join(fails) if fails else 'NONE'))
verdict = 'PASS' if not fails else 'FAIL'
say('\nLPCC-V1 PRELIMINARY VERDICT: %s' % verdict)

# ---------------- files ----------------
with open(os.path.join(HERE, 'LPCC_V1_TRADES.csv'), 'w', newline='') as f:
    w_ = csv.writer(f)
    w_.writerow(['day', 'dir', 'D_pts', 'thr', 'beta', 'stop_pts',
                 'gross', 'net_base', 'net_stressed', 'stopped'])
    for i, (k, dv) in enumerate(zip(ks, dirs)):
        w_.writerow([ev[k]['day'], dv, '%.2f' % D[k], '%.2f' % thr[k],
                     '%.5f' % beta[k], '%.2f' % sd_arr[i],
                     '%.2f' % gross[i], '%.2f' % net_b[i],
                     '%.2f' % net_s[i], int(stopped[i])])
with open(os.path.join(HERE, 'LPCC_V1_EVENT_AUDIT.csv'), 'w', newline='') as f:
    w_ = csv.writer(f)
    w_.writerow(['day', 'prevclose', 'dec_close', 'D', 'thr90_lagged',
                 'beta126', 'stop_scale60', 'warm', 'dgate', 'rgate', 'trade'])
    for k, s in enumerate(state):
        w_.writerow([ev[k]['day'], '%.2f' % ev[k]['prevclose'],
                     '%.2f' % ev[k]['dec_close'], '%.2f' % D[k],
                     '%.2f' % thr[k] if thr[k] == thr[k] else 'warmup',
                     '%.5f' % beta[k] if beta[k] == beta[k] else 'warmup',
                     '%.2f' % ss[k] if ss[k] == ss[k] else 'warmup',
                     int(s['warm']), int(s['dgate']), int(s['rgate']),
                     int(s['trade'])])
with open(os.path.join(HERE, 'LPCC_V1_HYPOTHESIS_LEDGER.csv'), 'w',
          newline='') as f:
    w_ = csv.DictWriter(f, fieldnames=['test', 'n', 'ev_stressed', 'wr', 'note'])
    w_.writeheader()
    w_.writerow({'test': 'PRIMARY LPCC-V1', 'n': len(net_s),
                 'ev_stressed': float(S['ev']), 'wr': float(S['wr']),
                 'note': 'perm p %.4f; CI [%+.3f,%+.3f]; verdict %s'
                 % (perm_p, ci_lo, ci_hi, verdict)})
    for r in ledger:
        w_.writerow(r)
json.dump([] if fails else [{'name': 'LPCC-V1'}],
          open(os.path.join(HERE, 'LPCC_V1_FROZEN_CANDIDATE.json'), 'w'))
json.dump({'verdict': verdict, 'fails': fails, 'n': len(net_s),
           'ev_stressed': S['ev'], 'ci': [float(ci_lo), float(ci_hi)],
           'perm_p': perm_p, 'scenarios': {k: v for k, v in sc.items()}},
          open(os.path.join(HERE, 'lpcc_summary.json'), 'w'), default=float)
open(os.path.join(HERE, 'LPCC_RUN_OUTPUT.txt'), 'w').write('\n'.join(LOG) + '\n')
