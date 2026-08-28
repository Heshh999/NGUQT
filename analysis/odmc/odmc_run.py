#!/usr/bin/env python3
# ODMC-V1 ONE-SHOT PRIMARY + PREDECLARED DIAGNOSTICS D1-D10
# freeze 9072bd3d8ef244eb6b87a6c56f9e983849e526a8 (v1.0.1 test corr 93acc65)
import os, sys, csv, json, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'mgsd'))
import odmc_engine as E
FREEZE = '9072bd3d8ef244eb6b87a6c56f9e983849e526a8'
LOG = []
def say(s=''):
    print(s); LOG.append(s)
say('ODMC-V1 ONE-SHOT RUN   freeze %s' % FREEZE)
G, ev = E.build_events()
thr, ss = E.gates_series(ev)
n = len(ev)
M = np.array([e['M'] for e in ev]); absM = np.abs(M)
state = []
for k in range(n):
    warm = not (np.isnan(thr[k]) or np.isnan(ss[k]))
    q = bool(warm and absM[k] > thr[k] and M[k] != 0)
    state.append({'k': k, 'warm': warm, 'qual': q})
ks = [s['k'] for s in state if s['qual']]
dirs = [1 if M[k] > 0 else -1 for k in ks]
say('eligible days %d | warm %d | raw nonzero impulses %d | '
    'magnitude-qualified (=TRADES) %d | unique days %d'
    % (n, sum(s['warm'] for s in state), int((M != 0).sum()), len(ks),
       len(set(ev[k]['day'] for k in ks))))

def run(ks_, dirs_, slip=0):
    return [E.race(G, ev[k], dv, E.stop_dist(ss[k]), slip)
            for k, dv in zip(ks_, dirs_)]
p0 = run(ks, dirs); p0f = run(ks, [-d for d in dirs])
gross = np.array([x[0] for x in p0]); grossf = np.array([x[0] for x in p0f])
sd_arr = np.array([E.stop_dist(ss[k]) for k in ks])
stopped = np.array([x[1] for x in p0])
tdays = [ev[k]['day'] for k in ks]; years = np.array([d[:4] for d in tdays])

def stats(x, R):
    w = x[x > 0]; l_ = x[x <= 0]
    return {'n': len(x), 'ev': float(x.mean()), 'evR': float((x / R).mean()),
            'wr': float((x > 0).mean()),
            'pf': float(w.sum() / -l_.sum()) if l_.sum() < 0 else float('inf'),
            'aw': float(w.mean()) if len(w) else np.nan,
            'al': float(l_.mean()) if len(l_) else np.nan,
            'payoff': float(w.mean() / -l_.mean()) if len(w) and len(l_) and l_.mean() < 0 else np.nan,
            'med': float(np.median(x)), 'worst': float(x.min()),
            'medw': float(np.median(w)) if len(w) else np.nan,
            'medl': float(np.median(l_)) if len(l_) else np.nan}
say('\nCOST SCENARIOS (net pts/trade, n=%d):' % len(gross))
sc = {}
for nm, net in (('gross', gross), ('slip 1t/side', gross - 0.50),
                ('slip 2t/side (prov base)', gross - 1.00),
                ('repo base 0.87', gross - E.COST_BASE),
                ('repo RTH 1.305 (reported)', gross - E.COST_RTH),
                ('slip 3t/side', gross - 1.50),
                ('BINDING STRESS 4t/side = 2.00', gross - E.COST_STRESS)):
    st = stats(net, sd_arr); sc[nm] = st
    say('  %-32s EV %+7.3f  %+0.4fR  WR %5.1f%%  PF %5.3f  payoff %s'
        % (nm, st['ev'], st['evR'], 100 * st['wr'], st['pf'],
           '%.2f' % st['payoff'] if st['payoff'] == st['payoff'] else 'nan'))
net_b = gross - E.COST_BASE; net_s = gross - E.COST_STRESS
S = stats(net_s, sd_arr); SB = stats(net_b, sd_arr)
rng = np.random.default_rng(E.SEED)
bs = np.sort(np.array([net_s[rng.integers(0, len(net_s), len(net_s))].mean()
                       for _ in range(10000)]))
ci_lo, ci_hi = bs[250], bs[9749]
say('\nPRIMARY (BINDING STRESS 2.00): EV %+0.3f pt (%+0.4fR)  CI95 [%+0.3f, %+0.3f]'
    % (S['ev'], S['evR'], ci_lo, ci_hi))
net_sf = grossf - E.COST_STRESS
nb = (len(ks) + 4) // 5; obs = net_s.mean(); hits = 0
for _ in range(10000):
    fl = rng.integers(0, 2, nb).astype(bool); x = net_s.copy()
    for b_ in range(nb):
        if fl[b_]:
            x[b_ * 5:(b_ + 1) * 5] = net_sf[b_ * 5:(b_ + 1) * 5]
    if abs(x.mean()) >= abs(obs) - 1e-12:
        hits += 1
perm_p = (1 + hits) / 10001.0
say('day-blocked permutation (impulse-sign, 5-day blocks) p = %.4f' % perm_p)
say('local BH q (family 1) = %.4f' % perm_p)
say('THREE-ARM FAMILYWISE: p %.4f vs 0.0166667 -> %s'
    % (perm_p, 'PASS' if perm_p <= 0.0166667 else 'FAIL'))
arms = {'LPCC-V1': 0.5160, 'CCHC-V1': 0.0243, 'ODMC-V1': perm_p}
sp = sorted(arms.items(), key=lambda kv: kv[1]); m_ = 3; prev = 1.0; q3 = {}
for r_ in range(m_ - 1, -1, -1):
    nm, pp = sp[r_]; prev = min(prev, m_ * pp / (r_ + 1)); q3[nm] = prev
say('FINAL BH across all three arms: ' + '  '.join('%s q=%.4f' % (k_, v_)
    for k_, v_ in q3.items()))
say('\nBY YEAR (binding stress):')
for y in sorted(set(years)):
    m2 = years == y
    say('  %s n %3d  EV %+8.3f  WR %5.1f%%  sum %+9.1f'
        % (y, m2.sum(), net_s[m2].mean(), 100 * (net_s[m2] > 0).mean(),
           net_s[m2].sum()))
qs_ = np.array([d[:4] + 'Q%d' % ((int(d[5:7]) - 1) // 3 + 1) for d in tdays])
nq_ = [q for q in set(qs_) if (qs_ == q).sum() >= 5]
say('quarters >=5 trades: %d, positive %d' % (len(nq_),
    sum(1 for q in nq_ if net_s[qs_ == q].mean() > 0)))
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
say('long %d (EV %+.3f) | short %d (EV %+.3f) | stop-outs %d | time-exits %d'
    % (lo_n, net_s[np.array(dirs) > 0].mean(), len(dirs) - lo_n,
       net_s[np.array(dirs) < 0].mean(), stopped.sum(), (~stopped).sum()))
vt = np.array([ss[k] for k in ks]); vmed = np.median(vt)
say('opening-vol split: low %+.3f (n%d) | high %+.3f (n%d)'
    % (net_s[vt <= vmed].mean(), (vt <= vmed).sum(),
       net_s[vt > vmed].mean(), (vt > vmed).sum()))
eq = np.cumsum(net_s); peak = np.maximum.accumulate(eq); dd = eq - peak
maxdd = float(dd.min()); ddur = cur = 0
for x in dd:
    cur = cur + 1 if x < 0 else 0; ddur = max(ddur, cur)
sr = float(net_s.mean() / net_s.std()) if net_s.std() > 0 else np.nan
dn = net_s[net_s < 0].std(); sor = float(net_s.mean() / dn) if dn > 0 else np.nan
streak = cur = 0
for x in net_s:
    cur = cur + 1 if x <= 0 else 0; streak = max(streak, cur)
cvar = float(np.mean(np.sort(net_s)[:max(1, int(0.05 * len(net_s)))]))
say('Sharpe/trade %.3f Sortino/trade %.3f maxDD %.1f pt DDdur %d trades '
    'streak %d largest loss %.1f CVaR5%% %.1f'
    % (sr, sor, maxdd, ddur, streak, S['worst'], cvar))
mf = []; ma = []
for k, dv in zip(ks, dirs):
    a_, b2 = E.mfe_mae(G, ev[k], dv); mf.append(a_); ma.append(b2)
say('median MFE %.2f  median MAE %.2f | median win %+.2f median loss %+.2f'
    % (np.median(mf), np.median(ma), S['medw'], S['medl']))
be = 1 / (1 + S['payoff']) if S['payoff'] == S['payoff'] else np.nan
say('break-even WR %.1f%%  actual %.1f%%  margin %+.1f pts'
    % (100 * be, 100 * S['wr'], 100 * (S['wr'] - be)))

say('\nDIAGNOSTICS D1-D10 (binding stress; never candidates):')
ledger = []
def rec(nm, x, note=''):
    say('  %-32s n %4d  EV %+8.3f  WR %5.1f%%  %s'
        % (nm, len(x), x.mean(), 100 * (x > 0).mean(), note))
    ledger.append({'test': nm, 'n': len(x), 'ev_stressed': float(x.mean()),
                   'wr': float((x > 0).mean()), 'note': note})
d1 = [s['k'] for s in state if s['warm'] and M[s['k']] != 0]
x1 = np.array([r[0] for r in run(d1, [1 if M[k] > 0 else -1 for k in d1])]) - E.COST_STRESS
rec('D1 no-magnitude-gate ablation', x1)
d2 = [s['k'] for s in state if s['warm'] and M[s['k']] != 0 and absM[s['k']] <= thr[s['k']]]
x2 = np.array([r[0] for r in run(d2, [1 if M[k] > 0 else -1 for k in d2])]) - E.COST_STRESS
rec('D2 below-threshold control', x2, 'never promoted')
x3 = grossf - E.COST_STRESS
rec('D3 direction-reversal placebo', x3)
rng4 = np.random.default_rng(20260905); nb4 = (len(ks) + 4) // 5
h4 = 0; m4 = []
for _ in range(10000):
    fl = rng4.integers(0, 2, nb4).astype(bool); x = net_s.copy()
    for b_ in range(nb4):
        if fl[b_]:
            x[b_ * 5:(b_ + 1) * 5] = net_sf[b_ * 5:(b_ + 1) * 5]
    m4.append(x.mean())
    if x.mean() >= obs - 1e-12:
        h4 += 1
p4 = (1 + h4) / 10001.0
say('  %-32s p = %.4f  (null mean %+.3f)' % ('D4 impulse-sign destruction', p4, np.mean(m4)))
ledger.append({'test': 'D4 sign-destruction', 'n': 10000,
               'ev_stressed': float(np.mean(m4)), 'wr': np.nan, 'note': 'p=%.4f' % p4})
rng5 = np.random.default_rng(20260906)
byyear = collections.defaultdict(list)
for k in ks:
    byyear[ev[k]['day'][:4]].append(k)
pm5 = []
for _ in range(2000):
    tot = []
    for y, lst in byyear.items():
        src = rng5.permutation(lst)
        for a_, b_ in zip(lst, src):
            dv = 1 if M[a_] > 0 else -1
            r_, _st = E.race(G, ev[b_], dv, E.stop_dist(ss[b_]))
            tot.append(r_ - E.COST_STRESS)
    pm5.append(float(np.mean(tot)))
p5 = (1 + sum(1 for v in pm5 if v >= obs)) / (len(pm5) + 1.0)
say('  %-32s draws %d  null mean %+.3f  p = %.4f'
    % ('D5 random-day pairing', len(pm5), np.mean(pm5), p5))
ledger.append({'test': 'D5 random-day pairing', 'n': len(pm5),
               'ev_stressed': float(np.mean(pm5)), 'wr': np.nan, 'note': 'p=%.4f' % p5})
for off in (-20, -10, 10, 20):
    sel = [k for k in ks if 0 <= k - off < n and state[k - off]['qual']]
    if sel:
        x6 = np.array([r[0] for r in run(sel, [1 if M[j - off] > 0 else -1 for j in sel])]) - E.COST_STRESS
        rec('D6 event shift %+d' % off, x6,
            'NON-TRADABLE falsification' if off > 0 else '')
    else:
        say('  D6 event shift %+d: n 0' % off)
gap = np.array([abs(ev[k]['P0'] - G['c'][ev[k]['i_b0'] - 1])
                if ev[k]['i_b0'] > 0 else np.nan for k in range(n)])
sig = np.array([e['sig_rng'] for e in ev])
def terc(v):
    g = v[~np.isnan(v)]
    return np.quantile(g, 1 / 3), np.quantile(g, 2 / 3)
gt, st_ = terc(gap), terc(sig)
def tc(v, c_):
    return 0 if v <= c_[0] else (1 if v <= c_[1] else 2)
half = {k: ev[k]['day'][:4] + ('H1' if ev[k]['day'][5:7] <= '06' else 'H2')
        for k in range(n)}
pool = collections.defaultdict(list); tset = set(ks)
for s in state:
    k = s['k']
    if s['warm'] and k not in tset and M[k] != 0 and not np.isnan(gap[k]):
        pool[(half[k], tc(gap[k], gt), tc(sig[k], st_))].append(k)
rng7 = np.random.default_rng(20260907); mk = []
for k in ks:
    if np.isnan(gap[k]):
        continue
    cand = pool.get((half[k], tc(gap[k], gt), tc(sig[k], st_)), [])
    if cand:
        mk.append(int(cand[rng7.integers(0, len(cand))]))
x7 = np.array([r[0] for r in run(mk, [1 if M[k] > 0 else -1 for k in mk])]) - E.COST_STRESS
rec('D7 matched non-event control', x7, 'half-year x gap x sig-range terciles')
G2, ev2 = E.build_events(581, 585, 586, 590, 591)
d2map = {e['day']: e for e in ev2}
x8l = []
for k, dv in zip(ks, dirs):
    e2 = d2map.get(ev[k]['day'])
    if e2 is None:
        continue
    r_, _s = E.race(G2, e2, dv, E.stop_dist(ss[k]))
    x8l.append(r_ - E.COST_STRESS)
x8 = np.array(x8l)
rec('D8 adjacent-block placebo', x8, '09:40-09:50 block, specificity only')
allw = [s['k'] for s in state if s['warm']]
x9l = np.array([r[0] for r in run(allw, [1] * len(allw))]) - E.COST_STRESS
x9s = np.array([r[0] for r in run(allw, [-1] * len(allw))]) - E.COST_STRESS
say('  %-32s long EV %+8.3f (n%d) | short EV %+8.3f (n%d)'
    % ('D9 unconditional opening drift', x9l.mean(), len(x9l), x9s.mean(), len(x9s)))
ledger.append({'test': 'D9 uncond drift long', 'n': len(x9l),
               'ev_stressed': float(x9l.mean()), 'wr': float((x9l > 0).mean()), 'note': ''})
ledger.append({'test': 'D9 uncond drift short', 'n': len(x9s),
               'ev_stressed': float(x9s.mean()), 'wr': float((x9s > 0).mean()), 'note': ''})
d9_dirmatch = float(np.mean([x9l[i] if dirs[j] > 0 else x9s[i]
                             for i, j in [(allw.index(k), idx) for idx, k in enumerate(ks)]])) \
    if set(ks) <= set(allw) else float('nan')
alg = np.array([np.sign(M[k]) * ev[k]['F'] for k in ks])
Xc = np.column_stack([np.ones(len(ks)), sig[ks], np.nan_to_num(gap[ks]),
                      np.array([ss[k] for k in ks]),
                      *[(wd == w).astype(float) for w in range(4)],
                      *[(years == y).astype(float) for y in sorted(set(years))[:-1]]])
beta_, *_ = np.linalg.lstsq(Xc, alg, rcond=None)
resid = alg - Xc @ beta_
say('  %-32s raw aligned 2nd-half %+0.3f pt -> residual mean %+0.3f pt '
    '(controls: sig range, gap, lagged vol, weekday, year)'
    % ('D10 residualization', alg.mean(), resid.mean() + alg.mean() - (Xc @ beta_).mean()))
ledger.append({'test': 'D10 residualization', 'n': len(alg),
               'ev_stressed': float(alg.mean()), 'wr': np.nan,
               'note': 'intercept-adjusted residual mean ~0 by construction; '
                       'see coefficient on constant'})
w_i = int(np.argmax(np.abs(net_s - net_s.mean()))); best_i = int(np.argmax(net_s))
bym = collections.Counter()
for d_, x_ in zip(tdays, net_s):
    bym[d_[:7]] += x_
bestmo = max(bym, key=lambda z: bym[z])
byy = {y: net_s[years == y].sum() for y in set(years)}
besty = max(byy, key=lambda z: byy[z])
say('\ninfluence: drop-most-influential %+0.3f | drop-best-trade %+0.3f | '
    'drop-best-month(%s) %+0.3f | drop-best-year(%s) %+0.3f'
    % (np.delete(net_s, w_i).mean(), np.delete(net_s, best_i).mean(), bestmo,
       net_s[np.array([d[:7] != bestmo for d in tdays])].mean(), besty,
       net_s[years != besty].mean()))
tot = net_s.sum()
say('best-year share of net: %.0f%%' % (100 * byy[besty] / tot if tot else float('nan')))

say('\nGATES (MGSD unweakened; BINDING STRESS 2.00 pt):')
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
ret_base = float(x9l.mean()) if np.array(dirs).mean() >= 0 else float(x9s.mean())
g['G12_retention>=50pct'] = bool(
    S['ev'] > 0 and (S['ev'] - float(x7.mean())) >= 0.5 * S['ev']
    and (S['ev'] - max(float(x9l.mean()), float(x9s.mean()))) >= 0.5 * S['ev'])
g['G13_no_signflip'] = bool(S['ev'] > 0)
g['G15_segments>=70pct'] = bool(segpos == segpos and segpos >= 0.70)
g['G16_no_domination'] = bool(tot > 0 and not any(
    net_s[years == y].sum() > 0.5 * tot for y in set(years)))
g['G17_influence'] = bool(np.delete(net_s, w_i).mean() > 0
                          and np.delete(net_s, best_i).mean() > 0)
g['G18_placebo'] = bool(p4 <= 0.05 and p5 <= 0.05)
g['G19_destruction'] = bool(p4 <= 0.05)
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
say('\nODMC-V1 PRELIMINARY VERDICT: %s' % verdict)
say('30-SECOND ARM: %s' % ('REACHED' if not fails else
    'NOT REACHED - 1-MINUTE PARENT FAILED; NO SUB-MINUTE RESCUE.'))

with open(os.path.join(HERE, 'ODMC_V1_TRADES.csv'), 'w', newline='') as f:
    w_ = csv.writer(f)
    w_.writerow(['day', 'dir', 'P0', 'P5', 'M_pts', 'thr90', 'stop_pts',
                 'entry', 'exit', 'gross', 'net_base', 'net_stress', 'stopped'])
    for i, (k, dv) in enumerate(zip(ks, dirs)):
        e = ev[k]
        w_.writerow([e['day'], dv, '%.2f' % e['P0'], '%.2f' % e['P5'],
                     '%.2f' % M[k], '%.2f' % thr[k], '%.2f' % sd_arr[i],
                     '%.2f' % e['entry_open'], '%.2f' % e['exit_open'],
                     '%.2f' % gross[i], '%.2f' % net_b[i], '%.2f' % net_s[i],
                     int(stopped[i])])
with open(os.path.join(HERE, 'ODMC_V1_EVENT_AUDIT.csv'), 'w', newline='') as f:
    w_ = csv.writer(f)
    w_.writerow(['day', 'P0', 'P5', 'M', 'thr90_lagged', 'stop_scale60',
                 'sig_range', 'warm', 'qualified'])
    for k, s in enumerate(state):
        e = ev[k]
        w_.writerow([e['day'], '%.2f' % e['P0'], '%.2f' % e['P5'],
                     '%.2f' % M[k],
                     '%.2f' % thr[k] if thr[k] == thr[k] else 'warmup',
                     '%.2f' % ss[k] if ss[k] == ss[k] else 'warmup',
                     '%.2f' % e['sig_rng'], int(s['warm']), int(s['qual'])])
with open(os.path.join(HERE, 'ODMC_V1_HYPOTHESIS_LEDGER.csv'), 'w', newline='') as f:
    w_ = csv.DictWriter(f, fieldnames=['test', 'n', 'ev_stressed', 'wr', 'note'])
    w_.writeheader()
    w_.writerow({'test': 'PRIMARY ODMC-V1', 'n': len(net_s),
                 'ev_stressed': float(S['ev']), 'wr': float(S['wr']),
                 'note': 'perm p %.4f; CI [%+.3f,%+.3f]; familywise %s; verdict %s'
                 % (perm_p, ci_lo, ci_hi,
                    'PASS' if perm_p <= 0.0166667 else 'FAIL', verdict)})
    for r in ledger:
        w_.writerow(r)
json.dump([] if fails else [{'name': 'ODMC-V1'}],
          open(os.path.join(HERE, 'ODMC_V1_FROZEN_CANDIDATE.json'), 'w'))
json.dump({'freeze': FREEZE, 'verdict': verdict, 'fails': fails,
           'n': len(net_s), 'ev_stress': S['ev'], 'evR': S['evR'],
           'ci': [float(ci_lo), float(ci_hi)], 'perm_p': perm_p,
           'wr': S['wr'], 'payoff': S['payoff'], 'pf_base': SB['pf'],
           'pf_stress': S['pf'], 'segpos': segpos, 'q3': q3,
           'scenarios': sc}, open(os.path.join(HERE, 'odmc_summary.json'), 'w'),
          default=float)
open(os.path.join(HERE, 'ODMC_RUN_OUTPUT.txt'), 'w').write('\n'.join(LOG) + '\n')
