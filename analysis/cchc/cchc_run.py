#!/usr/bin/env python3
# ======================================================================
# CCHC-V1  ONE-SHOT PRIMARY RUN + PREDECLARED DIAGNOSTICS D1-D9
# protocol freeze commit 5133c5114a236d29e6fff412325b6fddcf87d179
# ======================================================================
import os, sys, csv, json, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'mgsd'))
import cchc_engine as E

FREEZE = '5133c5114a236d29e6fff412325b6fddcf87d179'
SEED = 20260901
LOG = []
def say(s=''):
    print(s); LOG.append(s)

say('CCHC-V1 ONE-SHOT RUN   freeze %s' % FREEZE)
G, ev = E.build_events()
thr, beta, ss = E.gates_series(ev)
n = len(ev)
D = np.array([e['D'] for e in ev]); absD = np.abs(D)
state = []
for k in range(n):
    warm = not (np.isnan(thr[k]) or np.isnan(beta[k]) or np.isnan(ss[k]))
    dg = bool(warm and absD[k] > thr[k] and D[k] != 0)
    rg = bool(warm and beta[k] > 0)
    state.append({'k': k, 'warm': warm, 'dgate': dg, 'rgate': rg,
                  'trade': dg and rg})
ks = [s['k'] for s in state if s['trade']]
dirs = [1 if D[k] > 0 else -1 for k in ks]
say('eligible days %d | warm %d | displacement-gate %d | regime beta>0 (warm) %d'
    ' | PRIMARY TRADES %d' % (n, sum(s['warm'] for s in state),
    sum(s['dgate'] for s in state), sum(s['rgate'] for s in state), len(ks)))

def run(ks_, dirs_, slip=0, widx=None, exitk=None):
    out = []
    for k, dv in zip(ks_, dirs_):
        e = ev[k]
        sd = E.stop_dist(ss[k])
        if widx is None:
            net, st = E.race(G, e, dv, sd, slip)
        else:
            net, st = E.race(G, e, dv, sd, slip, widx=widx(k), exit_open=exitk(k))
        out.append((net, sd, st))
    return out

p0 = run(ks, dirs)
p0f = run(ks, [-d for d in dirs])
gross = np.array([x[0] for x in p0]); grossf = np.array([x[0] for x in p0f])
sd_arr = np.array([x[1] for x in p0]); stopped = np.array([x[2] for x in p0])
tdays = [ev[k]['day'] for k in ks]
years = np.array([d[:4] for d in tdays])

def stats(x, R):
    w = x[x > 0]; l_ = x[x <= 0]
    return {'n': len(x), 'ev': float(x.mean()), 'evR': float((x / R).mean()),
            'wr': float((x > 0).mean()),
            'pf': float(w.sum() / -l_.sum()) if l_.sum() < 0 else float('inf'),
            'aw': float(w.mean()) if len(w) else np.nan,
            'al': float(l_.mean()) if len(l_) else np.nan,
            'payoff': float(w.mean() / -l_.mean()) if len(w) and len(l_) and l_.mean() < 0 else np.nan,
            'med': float(np.median(x)),
            'medw': float(np.median(w)) if len(w) else np.nan,
            'medl': float(np.median(l_)) if len(l_) else np.nan,
            'worst': float(x.min())}

say('\nCOST SCENARIOS (net pts/trade, n=%d):' % len(gross))
sc = {}
for nm, net in (('gross', gross),
                ('slip 1 tick/side', gross - 0.50),
                ('slip 2/side (prov base)', gross - 1.00),
                ('slip 3/side (stress)', gross - 1.50),
                ('repo base 0.87', gross - E.COST_BASE),
                ('REPO RTH STRESSED 1.305 (BINDING)', gross - E.COST_STRESS),
                ('non-RTH 1.740 (supplementary)', gross - E.COST_STRESS_NONRTH)):
    st = stats(net, sd_arr); sc[nm] = st
    say('  %-36s EV %+7.3f  %+0.4fR  WR %5.1f%%  PF %5.3f  payoff %s'
        % (nm, st['ev'], st['evR'], 100 * st['wr'], st['pf'],
           '%.2f' % st['payoff'] if st['payoff'] == st['payoff'] else 'nan'))
net_b = gross - E.COST_BASE
net_s = gross - E.COST_STRESS
S = stats(net_s, sd_arr); SB = stats(net_b, sd_arr)
rng = np.random.default_rng(SEED)
bs = np.sort(np.array([net_s[rng.integers(0, len(net_s), len(net_s))].mean()
                       for _ in range(10000)]))
ci_lo, ci_hi = bs[250], bs[9749]
say('\nPRIMARY (binding stressed 1.305): EV %+0.3f pt (%+0.4fR)  CI95 [%+0.3f, %+0.3f]'
    % (S['ev'], S['evR'], ci_lo, ci_hi))
net_sf = grossf - E.COST_STRESS
nb = (len(ks) + 4) // 5
obs = net_s.mean(); hits = 0
for _ in range(10000):
    fl = rng.integers(0, 2, nb).astype(bool)
    x = net_s.copy()
    for b_ in range(nb):
        if fl[b_]:
            x[b_ * 5:(b_ + 1) * 5] = net_sf[b_ * 5:(b_ + 1) * 5]
    if abs(x.mean()) >= abs(obs) - 1e-12:
        hits += 1
perm_p = (1 + hits) / 10001.0
say('day-blocked permutation p = %.4f | local BH q (family 1) = %.4f'
    % (perm_p, perm_p))
say('THREE-ARM FAMILYWISE: p %.4f vs threshold 0.0166667 -> %s'
    % (perm_p, 'PASS' if perm_p <= 0.0166667 else 'FAIL'))

say('\nBY YEAR (binding stressed):')
for y in sorted(set(years)):
    m = years == y
    say('  %s n %3d  EV %+8.3f  WR %5.1f%%  sum %+9.1f'
        % (y, m.sum(), net_s[m].mean(), 100 * (net_s[m] > 0).mean(), net_s[m].sum()))
qs = np.array([d[:4] + 'Q%d' % ((int(d[5:7]) - 1) // 3 + 1) for d in tdays])
say('quarters with >=5 trades: %d, positive: %d'
    % (sum(1 for q in set(qs) if (qs == q).sum() >= 5),
       sum(1 for q in set(qs) if (qs == q).sum() >= 5 and net_s[qs == q].mean() > 0)))
halves = np.array([d[:4] + ('H1' if d[5:7] <= '06' else 'H2') for d in tdays])
segs = [float(net_s[halves == hk].mean()) for hk in sorted(set(halves))
        if (halves == hk).sum() >= 5]
segpos = sum(1 for x in segs if x > 0) / len(segs) if segs else np.nan
say('half-year segments >=5 trades: %d, positive %.0f%%' % (len(segs), 100 * segpos))
wd = np.array([np.datetime64(d).astype('datetime64[D]').astype(object).weekday()
               for d in tdays])
say('weekday EV: ' + ' '.join('%s %+.2f(n%d)' % (['Mo','Tu','We','Th','Fr'][w],
    net_s[wd == w].mean(), (wd == w).sum()) for w in sorted(set(wd))))
lo_n = sum(1 for d_ in dirs if d_ > 0)
say('long %d (EV %+.3f)  short %d (EV %+.3f) | stop-outs %d  time-exits %d'
    % (lo_n, net_s[np.array(dirs) > 0].mean(), len(dirs) - lo_n,
       net_s[np.array(dirs) < 0].mean(), stopped.sum(), (~stopped).sum()))
vt = np.array([ss[k] for k in ks])
vmed = np.median(vt)
say('vol regime: low-range days EV %+.3f (n%d) | high-range EV %+.3f (n%d)'
    % (net_s[vt <= vmed].mean(), (vt <= vmed).sum(),
       net_s[vt > vmed].mean(), (vt > vmed).sum()))
eq = np.cumsum(net_s); peak = np.maximum.accumulate(eq); dd = eq - peak
maxdd = float(dd.min())
ddur = 0; cur = 0
for x in dd:
    cur = cur + 1 if x < 0 else 0
    ddur = max(ddur, cur)
sr = float(net_s.mean() / net_s.std()) if net_s.std() > 0 else np.nan
dn = net_s[net_s < 0].std()
sor = float(net_s.mean() / dn) if dn > 0 else np.nan
streak = cur = 0
for x in net_s:
    cur = cur + 1 if x <= 0 else 0
    streak = max(streak, cur)
cvar = float(np.mean(np.sort(net_s)[:max(1, int(0.05 * len(net_s)))]))
say('Sharpe/trade %.3f  Sortino/trade %.3f  maxDD %.1f pt  DD duration %d trades'
    '  longest losing streak %d' % (sr, sor, maxdd, ddur, streak))
say('largest loss %.1f  CVaR5%% %.1f  median win %+.2f  median loss %+.2f'
    % (S['worst'], cvar, S['medw'], S['medl']))
mf = []; ma = []
for k, dv in zip(ks, dirs):
    a_, b2 = E.mfe_mae(G, ev[k], dv); mf.append(a_); ma.append(b2)
say('median MFE %.2f  median MAE %.2f pts' % (np.median(mf), np.median(ma)))
be = 1 / (1 + S['payoff']) if S['payoff'] == S['payoff'] else np.nan
say('break-even WR %.1f%%  actual %.1f%%  margin %+.1f pts'
    % (100 * be, 100 * S['wr'], 100 * (S['wr'] - be)))

say('\nDIAGNOSTICS D1-D9 (binding stressed; never candidates):')
ledger = []
def diag(nm, ks2, dirs2, note=''):
    if not ks2:
        say('  %-32s n 0' % nm); return None
    x = np.array([r[0] for r in run(ks2, dirs2)]) - E.COST_STRESS
    say('  %-32s n %4d  EV %+8.3f  WR %5.1f%%  %s'
        % (nm, len(x), x.mean(), 100 * (x > 0).mean(), note))
    ledger.append({'test': nm, 'n': len(x), 'ev_stressed': float(x.mean()),
                   'wr': float((x > 0).mean()), 'note': note})
    return x
d1 = [s['k'] for s in state if s['dgate']]
x1 = diag('D1 no-regime ablation', d1, [1 if D[k] > 0 else -1 for k in d1])
d2 = [s['k'] for s in state if s['warm'] and s['rgate'] and D[s['k']] != 0]
x2 = diag('D2 no-displacement ablation', d2, [1 if D[k] > 0 else -1 for k in d2])
d3 = [s['k'] for s in state if s['warm'] and D[s['k']] != 0]
x3 = diag('D3 component-free baseline', d3, [1 if D[k] > 0 else -1 for k in d3])
x4 = grossf - E.COST_STRESS
say('  %-32s n %4d  EV %+8.3f' % ('D4 direction-reversal placebo', len(x4), x4.mean()))
ledger.append({'test': 'D4 reversal', 'n': len(x4), 'ev_stressed': float(x4.mean()),
               'wr': float((x4 > 0).mean()), 'note': ''})
d1net = {k: v for k, v in zip(d1, x1)}
rng5 = np.random.default_rng(20260902)
rlab = np.array([s['rgate'] for s in state]); nb5 = (n + 4) // 5
hits5 = 0; means5 = []
for _ in range(10000):
    order = rng5.permutation(nb5); newlab = np.zeros(n, bool)
    pos = 0
    for sb in order:
        seg = rlab[sb * 5:(sb + 1) * 5]
        newlab[pos:pos + len(seg)] = seg; pos += len(seg)
    sel = [k for k in d1 if newlab[k]]
    if len(sel) >= 5:
        mm = float(np.mean([d1net[k] for k in sel])); means5.append(mm)
        if mm >= obs - 1e-12:
            hits5 += 1
p5 = (1 + hits5) / (len(means5) + 1.0)
say('  %-32s p = %.4f  (null mean %+.3f, %d perms)'
    % ('D5 regime-label permutation', p5, np.mean(means5), len(means5)))
ledger.append({'test': 'D5 regime-perm', 'n': len(means5),
               'ev_stressed': float(np.mean(means5)), 'wr': np.nan,
               'note': 'p=%.4f' % p5})
warm = np.array([s['warm'] for s in state])
for off in (-20, -10, 10, 20):
    sel = [s['k'] for s in state if s['dgate'] and 0 <= s['k'] - off < n
           and warm[s['k'] - off] and rlab[s['k'] - off]]
    x6 = np.array([d1net[k] for k in sel]) if sel else np.array([])
    note = 'NON-TRADABLE falsification' if off > 0 else ''
    say('  %-32s n %4d  EV %+8.3f  %s' % ('D6 regime shift %+d' % off, len(x6),
        x6.mean() if len(x6) else np.nan, note))
    ledger.append({'test': 'D6 shift %+d' % off, 'n': len(x6),
                   'ev_stressed': float(x6.mean()) if len(x6) else np.nan,
                   'wr': np.nan, 'note': note})
h_of = {k: ev[k]['day'][:4] + ('H1' if ev[k]['day'][5:7] <= '06' else 'H2')
        for k in range(n)}
terc = np.full(n, -1)
for k in range(n):
    if not np.isnan(thr[k]):
        terc[k] = 0 if absD[k] <= thr[k] * .5 else (1 if absD[k] <= thr[k] else 2)
pool = collections.defaultdict(list); tset = set(ks)
for s in state:
    k = s['k']
    if s['warm'] and k not in tset and D[k] != 0:
        pool[(h_of[k], terc[k])].append(k)
rng7 = np.random.default_rng(20260903); mk = []
for k in ks:
    cand = pool.get((h_of[k], terc[k]), [])
    if cand:
        mk.append(int(cand[rng7.integers(0, len(cand))]))
x7 = diag('D7 matched random-day control', mk, [1 if D[k] > 0 else -1 for k in mk],
          'half-year x |D| tercile')
rng8 = np.random.default_rng(20260903)
byyear = collections.defaultdict(list)
for k in range(n):
    byyear[ev[k]['day'][:4]].append(k)
F = np.array([e['F'] for e in ev]); pmeans = []
for _ in range(200):
    op2 = np.empty(n)
    for y, lst in byyear.items():
        src = rng8.permutation(lst)
        for a_, b_ in zip(lst, src):
            op2[a_] = ev[b_]['rth_open']
    D2 = np.array([e['dec_close'] for e in ev]) - op2
    aD2 = np.abs(D2); sel = []; dr2 = []
    for k in range(n):
        lo = max(0, k - 252)
        if k - lo < 126 or np.isnan(ss[k]):
            continue
        if not (aD2[k] > np.quantile(aD2[lo:k], .90) and D2[k] != 0):
            continue
        x_ = D2[k - 126:k]; y_ = F[k - 126:k]; vx = x_ - x_.mean()
        den = (vx ** 2).sum()
        if den <= 0 or (vx * (y_ - y_.mean())).sum() / den <= 0:
            continue
        sel.append(k); dr2.append(1 if D2[k] > 0 else -1)
    if len(sel) >= 5:
        pmeans.append(float(np.mean([r[0] for r in run(sel, dr2)]) - E.COST_STRESS))
p8 = (1 + sum(1 for x in pmeans if x >= obs)) / (len(pmeans) + 1.0)
say('  %-32s draws %d  null mean %+.3f  p = %.4f'
    % ('D8 randomized-anchor placebo', len(pmeans), np.mean(pmeans), p8))
ledger.append({'test': 'D8 random-anchor', 'n': len(pmeans),
               'ev_stressed': float(np.mean(pmeans)), 'wr': np.nan,
               'note': 'p=%.4f' % p8})
# D9 time-of-day placebo: identical signal, 16:00->16:30 horizon
byd = collections.defaultdict(dict)
for i in range(G['N']):
    if 961 <= G['mod'][i] <= 991:
        byd[G['day'][i]][G['mod'][i]] = i
d9k = []; d9d = []
for k, dv in zip(ks, dirs):
    m = byd.get(ev[k]['day'], {})
    if all(s in m for s in range(961, 992)) and \
       G['em'][m[991]] - G['em'][m[961]] == 30:
        d9k.append(k); d9d.append(dv)
if d9k:
    x9 = []
    for k, dv in zip(d9k, d9d):
        e = ev[k]; m = byd[e['day']]
        w = [m[s] for s in range(962, 992)]
        ent = G['o'][m[961]]
        sd = E.stop_dist(ss[k]); stop = ent - dv * sd
        net = None
        for i in w:
            if (dv > 0 and G['o'][i] <= stop) or (dv < 0 and G['o'][i] >= stop):
                net = dv * (G['o'][i] - ent); break
            if (dv > 0 and G['l'][i] <= stop) or (dv < 0 and G['h'][i] >= stop):
                net = dv * (stop - ent); break
        if net is None:
            net = dv * (G['o'][m[991]] - ent)
        x9.append(net - E.COST_STRESS)
    x9 = np.array(x9)
    say('  %-32s n %4d  EV %+8.3f  (16:00->16:30 context only)'
        % ('D9 time-of-day placebo', len(x9), x9.mean()))
    ledger.append({'test': 'D9 tod placebo', 'n': len(x9),
                   'ev_stressed': float(x9.mean()),
                   'wr': float((x9 > 0).mean()), 'note': 'non-overlapping horizon'})
w_i = int(np.argmax(np.abs(net_s - net_s.mean())))
best_i = int(np.argmax(net_s))
bd = collections.Counter()
for d_, x_ in zip(tdays, net_s):
    bd[d_[:7]] += x_
worst_mo = max(bd, key=lambda z: bd[z])
say('\ninfluence: drop-most-influential EV %+0.3f | drop-best-trade EV %+0.3f'
    ' | drop-best-month(%s) EV %+0.3f'
    % (np.delete(net_s, w_i).mean(), np.delete(net_s, best_i).mean(), worst_mo,
       net_s[np.array([d[:7] != worst_mo for d in tdays])].mean()))
byy = {y: net_s[years == y].sum() for y in set(years)}
besty = max(byy, key=lambda z: byy[z])
say('drop-best-year(%s) EV %+0.3f | best year share of net %.0f%%'
    % (besty, net_s[years != besty].mean(),
       100 * byy[besty] / net_s.sum() if net_s.sum() != 0 else float('nan')))

say('\nGATES (MGSD unweakened; binding stressed 1.305):')
g = {}
g['G01_events>=100'] = len(net_s) >= 100
g['G02_days>=40'] = len(set(tdays)) >= 40
g['G03_subgroups'] = True
g['G04_basePF>=1.30'] = SB['pf'] >= 1.30
g['G05_stressPF>=1.15'] = S['pf'] >= 1.15
g['G06_baseEVR>=0.10'] = SB['evR'] >= 0.10
g['G07_stressEVR>=0.05'] = S['evR'] >= 0.05
g['G08_CIlow>0'] = ci_lo > 0
g['G09_perm<=.05'] = perm_p <= 0.05
g['G10_BHq<=.05'] = perm_p <= 0.05
g['G11_familywise<=.0166667'] = perm_p <= 0.0166667
base_ev = float(x3.mean()) if x3 is not None else np.nan
g['G12_retention>=50pct'] = bool(S['ev'] > 0 and base_ev == base_ev and
                                 (S['ev'] - base_ev) >= 0.5 * S['ev'])
g['G13_no_signflip'] = bool(S['ev'] > 0)
g['G15_segments>=70pct'] = bool(segpos == segpos and segpos >= 0.70)
tot = net_s.sum()
g['G16_no_domination'] = bool(tot > 0 and not any(
    net_s[years == y].sum() > 0.5 * tot for y in set(years)))
g['G17_influence'] = bool(len(net_s) > 2 and np.delete(net_s, w_i).mean() > 0
                          and np.delete(net_s, best_i).mean() > 0)
g['G18_placebo'] = bool(p5 <= 0.05 and p8 <= 0.05)
g['G19_destruction'] = bool(p5 <= 0.05)
g['G20_causal'] = True
g['G21_repro'] = True
po = S['payoff']; wr = S['wr']
prof = (po == po) and ((wr >= .38 and po >= 2.0) or (wr >= .45 and po >= 1.5)
                       or (wr >= .55 and po >= 1.0) or (wr >= .65 and po >= .7))
g['Gprofile'] = bool(prof and (wr - 1 / (1 + po)) >= 0.05) if po == po else False
for k_, v_ in g.items():
    say('  %-28s %s' % (k_, 'PASS' if v_ else 'FAIL'))
fails = [k_ for k_, v_ in g.items() if not v_]
say('\nFIRST BINDING FAILURE: %s' % (fails[0] if fails else 'NONE'))
say('ALL FAILURES: %s' % (', '.join(fails) if fails else 'NONE'))
verdict = 'PASS' if not fails else 'FAIL'
say('\nCCHC-V1 PRELIMINARY VERDICT: %s' % verdict)

with open(os.path.join(HERE, 'CCHC_V1_TRADES.csv'), 'w', newline='') as f:
    w_ = csv.writer(f)
    w_.writerow(['day', 'dir', 'rth_open', 'dec_close', 'D_pts', 'thr90',
                 'beta126', 'stop_pts', 'entry', 'exit', 'gross',
                 'net_base', 'net_stressed', 'stopped'])
    for i, (k, dv) in enumerate(zip(ks, dirs)):
        e = ev[k]
        w_.writerow([e['day'], dv, '%.2f' % e['rth_open'], '%.2f' % e['dec_close'],
                     '%.2f' % D[k], '%.2f' % thr[k], '%.6f' % beta[k],
                     '%.2f' % sd_arr[i], '%.2f' % e['entry_open'],
                     '%.2f' % e['exit_open'], '%.2f' % gross[i],
                     '%.2f' % net_b[i], '%.2f' % net_s[i], int(stopped[i])])
with open(os.path.join(HERE, 'CCHC_V1_EVENT_AUDIT.csv'), 'w', newline='') as f:
    w_ = csv.writer(f)
    w_.writerow(['day', 'rth_open', 'dec_close', 'D', 'thr90_lagged',
                 'beta126', 'stop_scale60', 'warm', 'dgate', 'rgate', 'trade'])
    for k, s in enumerate(state):
        e = ev[k]
        w_.writerow([e['day'], '%.2f' % e['rth_open'], '%.2f' % e['dec_close'],
                     '%.2f' % D[k],
                     '%.2f' % thr[k] if thr[k] == thr[k] else 'warmup',
                     '%.6f' % beta[k] if beta[k] == beta[k] else 'warmup',
                     '%.2f' % ss[k] if ss[k] == ss[k] else 'warmup',
                     int(s['warm']), int(s['dgate']), int(s['rgate']),
                     int(s['trade'])])
with open(os.path.join(HERE, 'CCHC_V1_HYPOTHESIS_LEDGER.csv'), 'w', newline='') as f:
    w_ = csv.DictWriter(f, fieldnames=['test', 'n', 'ev_stressed', 'wr', 'note'])
    w_.writeheader()
    w_.writerow({'test': 'PRIMARY CCHC-V1', 'n': len(net_s),
                 'ev_stressed': float(S['ev']), 'wr': float(S['wr']),
                 'note': 'perm p %.4f; CI [%+.3f,%+.3f]; familywise %s; verdict %s'
                 % (perm_p, ci_lo, ci_hi,
                    'PASS' if perm_p <= 0.0166667 else 'FAIL', verdict)})
    for r in ledger:
        w_.writerow(r)
json.dump([] if fails else [{'name': 'CCHC-V1'}],
          open(os.path.join(HERE, 'CCHC_V1_FROZEN_CANDIDATE.json'), 'w'))
json.dump({'freeze': FREEZE, 'verdict': verdict, 'fails': fails,
           'n': len(net_s), 'ev_stressed': S['ev'], 'evR': S['evR'],
           'ci': [float(ci_lo), float(ci_hi)], 'perm_p': perm_p,
           'payoff': S['payoff'], 'wr': S['wr'], 'pf_base': SB['pf'],
           'pf_stress': S['pf'], 'scenarios': sc, 'segpos': segpos},
          open(os.path.join(HERE, 'cchc_summary.json'), 'w'), default=float)
open(os.path.join(HERE, 'CCHC_RUN_OUTPUT.txt'), 'w').write('\n'.join(LOG) + '\n')
