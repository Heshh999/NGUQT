#!/usr/bin/env python3
# ======================================================================
# MOFAD-V1  -  FROZEN ONE-SHOT DEV RUN
# Runs the complete frozen search (5 confirmatory candidates + declared
# diagnostics + destruction battery), regardless of early results.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mofad_lib as M  # noqa: E402

CANDS = ['C-F12-1', 'C-F12-1b', 'C-F12-2', 'C-F08-1', 'C-F08-2']
LED = []


def led(cell, kind, n, value, note):
    LED.append(dict(cell=cell, kind=kind, n=n, value=value, note=note))


def build(days, byday, cand):
    if cand.startswith('C-F12'):
        return M.build_f12(days, byday, cand)
    return M.build_f08(days, byday, cand)


def seg_signs(ev, cost=M.COST_STRESS):
    qs = ['2025-08-18', '2025-11-18', '2026-02-18', '2026-05-18', '2026-08-18']
    out = []
    for lo, hi in zip(qs, qs[1:]):
        x = [e['gross'] - cost for e in ev if lo <= e['day'] < hi]
        out.append((len(x), float(np.mean(x)) if x else float('nan')))
    return out


def destruction(ev, days, byday, cand):
    """Frozen destruction battery. Returns dict of stressed means."""
    g = np.array([e['gross'] for e in ev])
    st = g - M.COST_STRESS
    out = {}
    # largest-day removal
    per_day = collections.defaultdict(float)
    for e in ev:
        per_day[e['day']] += e['gross'] - M.COST_STRESS
    best = max(per_day, key=per_day.get)
    out['drop_best_day'] = float(np.mean([e['gross'] - M.COST_STRESS
                                          for e in ev if e['day'] != best]))
    out['best_day_share'] = (per_day[best] / st.sum()) if st.sum() != 0 else float('nan')
    # top-1% trade removal
    k = max(1, int(round(0.01 * len(ev))))
    order = np.argsort(st)[::-1]
    out['drop_top1pct'] = float(st[order[k:]].mean())
    # day-pairing shift (defined for one-event-per-day F12 cells)
    if cand.startswith('C-F12'):
        by = sorted(ev, key=lambda e: e['day'])
        shifted = [(prev['dir'] * (e['gross'] * e['dir'])) - M.COST_STRESS
                   for prev, e in zip(by, by[1:])]
        out['day_pairing'] = float(np.mean(shifted))
    return out


def delay_variant(days, byday, cand):
    """+1-bar entry delay destruction: entry one bar later, same exit."""
    ev = build(days, byday, cand)
    out = []
    for e in ev:
        d, et = e['day'], e['et']
        bars = byday[d]
        mm = int(et[11:13]) * 60 + int(et[14:16])
        idx = {b['mm']: i for i, b in enumerate(bars)}
        j0 = idx.get(mm + 1)
        if j0 is None:
            continue
        H = {'C-F12-1': 30, 'C-F12-1b': 60, 'C-F12-2': 30,
             'C-F08-1': 15, 'C-F08-2': 30}[cand]
        exit_mm = mm + H if cand.startswith('C-F12') else mm + H
        jx, _ = M._exit_index(bars, j0, exit_mm)
        if jx is None:
            g = e['dir'] * (bars[-1]['close'] - bars[j0]['open'])
        else:
            g, _ = M.race(bars, j0, jx, e['dir'], e['stop'])
        out.append(g - M.COST_STRESS)
    return float(np.mean(out)) if out else float('nan')


def main():
    days, byday = M.load_dev()
    print('MOFAD-V1 frozen one-shot run  DEV %s..%s  days %d'
          % (days[0], days[-1], len(days)))
    results, all_ev = {}, {}
    for cand in CANDS:
        ev = build(days, byday, cand)
        all_ev[cand] = ev
        s = M.stats_cell(ev)
        results[cand] = s
        led(cand, 'primary', s['n'], s['stressed'], 'stressed mean pts')

    ps = [results[c]['perm_p'] for c in CANDS]
    qs = M.bh(ps)
    for c, q in zip(CANDS, qs):
        results[c]['bh_q'] = q

    # ---- diagnostics + destructions per candidate -------------------
    for cand in CANDS:
        ev = all_ev[cand]
        s = results[cand]
        g = np.array([e['gross'] for e in ev])
        st = g - M.COST_STRESS
        # long/short split
        for lab, sel in (('LONG', [e for e in ev if e['dir'] > 0]),
                         ('SHORT', [e for e in ev if e['dir'] < 0])):
            x = [e['gross'] - M.COST_STRESS for e in sel]
            s['%s_n' % lab], s['%s_mean' % lab] = len(x), float(np.mean(x)) if x else float('nan')
            led(cand, 'diag_dir_%s' % lab, len(x), s['%s_mean' % lab], 'stressed')
        # |signal| terciles
        sig = np.abs(np.array([e['sig'] for e in ev]))
        e1, e2 = np.quantile(sig, [1 / 3, 2 / 3])
        for lab, m_ in (('T1', sig <= e1), ('T2', (sig > e1) & (sig <= e2)),
                        ('T3', sig > e2)):
            s['ter_%s' % lab] = (int(m_.sum()), float(st[m_].mean()) if m_.any() else float('nan'))
            led(cand, 'diag_tercile_%s' % lab, int(m_.sum()), s['ter_%s' % lab][1], 'stressed')
        # chronological quarters
        s['quarters'] = seg_signs(ev)
        led(cand, 'diag_quarters', len(ev),
            sum(1 for n, v in s['quarters'] if n and v > 0), 'quarters positive')
        # destructions
        s['destruction'] = destruction(ev, days, byday, cand)
        s['delay1bar'] = delay_variant(days, byday, cand)
        led(cand, 'destr_delay1bar', s['n'], s['delay1bar'], 'stressed')
        # F12 price-twin ablation / residual
        if cand.startswith('C-F12'):
            tw = np.array([e['twin_dir'] for e in ev], float)
            dv = np.array([e['dir'] for e in ev], float)
            twin_g = np.where(tw != 0, g * tw * dv, np.nan)
            ok = ~np.isnan(twin_g)
            s['twin_mean'] = float(np.nanmean(twin_g) - M.COST_STRESS)
            X = np.c_[np.ones(ok.sum()), twin_g[ok]]
            beta = np.linalg.lstsq(X, g[ok], rcond=None)[0]
            s['resid_intercept'] = float(beta[0])
            s['retention'] = float(beta[0] / g.mean()) if g.mean() != 0 else float('nan')
            s['agree_frac'] = float((tw == dv).mean())
            div = [e for e in ev if e['diverg']]
            s['diverg'] = (len(div), float(np.mean([e['gross'] - M.COST_STRESS
                                                    for e in div])) if div else float('nan'))
            led(cand, 'diag_divergence', len(div), s['diverg'][1], 'stressed')
        # F08 single-side ablation
        if cand.startswith('C-F08'):
            lb = np.array([e['lam_b'] for e in ev])
            ls = np.array([e['lam_s'] for e in ev])
            for lab, arr in (('buy_only', lb - np.median(lb)),
                             ('sell_only', -(ls - np.median(ls)))):
                dd = np.sign(arr)
                gg = np.where(dd == 0, 0.0,
                              g * dd * np.array([e['dir'] for e in ev]))
                s['abl_%s' % lab] = float(gg.mean() - M.COST_STRESS)
                led(cand, 'abl_%s' % lab, s['n'], s['abl_%s' % lab], 'stressed')

    # ---- neighbor variants (diagnostics) ----------------------------
    NEIGH = {}
    import mofad_lib as ML

    def f08_neighbor(cand, qq):
        orig = ML.q7
        ML.q7 = lambda v, q: orig(v, qq)
        try:
            ev = ML.build_f08(days, byday, cand)
        finally:
            ML.q7 = orig
        x = [e['gross'] - M.COST_STRESS for e in ev]
        return len(x), float(np.mean(x)) if x else float('nan')

    for cand in ('C-F08-1', 'C-F08-2'):
        for qq in (0.70, 0.80):
            NEIGH['%s_Q%d' % (cand, qq * 100)] = f08_neighbor(cand, qq)
            led(cand, 'neigh_Q%d' % (qq * 100), NEIGH['%s_Q%d' % (cand, qq * 100)][0],
                NEIGH['%s_Q%d' % (cand, qq * 100)][1], 'stressed')

    def f12_neighbor(cand, need):
        H = {'C-F12-1': 30, 'C-F12-1b': 60, 'C-F12-2': 30}[cand]
        ev = []
        for k, d in enumerate(days):
            if k == 0:
                continue
            bars = byday[d]
            if cand != 'C-F12-2':
                prev = byday[days[k - 1]]
                win = ([b for b in prev if b['mm'] > 1080]
                       + [b for b in bars if 0 < b['mm'] <= 540])
            else:
                win = [b for b in bars if 480 < b['mm'] <= 569]
            if len(win) < need:
                continue
            r = M._flow_ratio(win)
            if not r:
                continue
            idx = {b['mm']: i for i, b in enumerate(bars)}
            j0 = idx.get(571)
            atr = M._atr_before(bars, 571)
            if j0 is None or not atr:
                continue
            dirv = 1 if r > 0 else -1
            jx, _ = M._exit_index(bars, j0, 571 + H)
            g = (dirv * (bars[-1]['close'] - bars[j0]['open']) if jx is None
                 else M.race(bars, j0, jx, dirv, 1.5 * atr)[0])
            ev.append(g - M.COST_STRESS)
        return len(ev), float(np.mean(ev)) if ev else float('nan')

    for cand, needs in (('C-F12-1', (250, 350)), ('C-F12-1b', (250, 350)),
                        ('C-F12-2', (50, 70))):
        for nd in needs:
            NEIGH['%s_need%d' % (cand, nd)] = f12_neighbor(cand, nd)
            led(cand, 'neigh_need%d' % nd, NEIGH['%s_need%d' % (cand, nd)][0],
                NEIGH['%s_need%d' % (cand, nd)][1], 'stressed')

    # ---- gates ------------------------------------------------------
    verdicts = {}
    for cand in CANDS:
        s = results[cand]
        fails = []
        if s['n'] < 200: fails.append('G01 n<200')
        if s['days'] < 60: fails.append('G02 days<60')
        if not (s['base'] > 0 and s['stressed'] > 0): fails.append('G05 not positive after costs')
        if s['pf_base'] < 1.30: fails.append('G06 base PF<1.30')
        if s['pf_stressed'] < 1.15: fails.append('G07 stressed PF<1.15')
        if s['base_R'] < 0.10: fails.append('G08 base EV<0.10R')
        if s['stressed_R'] < 0.05: fails.append('G09 stressed EV<0.05R')
        if s['ci_lo'] <= 0: fails.append('G10 CI lower bound<=0')
        if s['perm_p'] > 0.05: fails.append('G11 perm p>0.05')
        if s['bh_q'] > 0.05: fails.append('G12 BH q>0.05')
        if cand.startswith('C-F12') and not (s.get('retention', 0) >= 0.5):
            fails.append('G13 retention<50% vs price twin')
        qpos = sum(1 for n, v in s['quarters'] if n and v > 0)
        if qpos < 3: fails.append('G16 <3/4 quarters positive')
        prof = ((s['win_base'] >= 0.38 and s['payoff_stressed'] >= 2.00)
                or (s['win_base'] >= 0.45 and s['payoff_stressed'] >= 1.50)
                or (s['win_base'] >= 0.55 and s['payoff_stressed'] >= 1.00)
                or (s['win_base'] >= 0.65 and s['payoff_stressed'] >= 0.70))
        if not prof: fails.append('G-profile no trade-quality profile met')
        verdicts[cand] = fails
        s['gate_fails'] = fails

    # ---- outputs ----------------------------------------------------
    with open(os.path.join(HERE, 'MOFAD_V1_TRADES.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['cand', 'day', 'entry_et', 'dir', 'signal', 'stop_pts',
                    'gross_pts', 'base_pts', 'stressed_pts', 'exit_kind'])
        for cand in CANDS:
            for e in all_ev[cand]:
                w.writerow([cand, e['day'], e['et'], e['dir'],
                            '%.6g' % e['sig'], '%.4f' % e['stop'],
                            '%.2f' % e['gross'], '%.2f' % (e['gross'] - M.COST_BASE),
                            '%.2f' % (e['gross'] - M.COST_STRESS), e['exit']])
    with open(os.path.join(HERE, 'MOFAD_V1_EVENT_AUDIT.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['cand', 'day', 'entry_et', 'dir', 'signal', 'extra'])
        for cand in CANDS:
            for e in all_ev[cand]:
                extra = ('twin=%d div=%d' % (e['twin_dir'], e['diverg'])
                         if cand.startswith('C-F12')
                         else 'lb=%.5g ls=%.5g thr=%.5g' % (e['lam_b'], e['lam_s'], e['thr']))
                w.writerow([cand, e['day'], e['et'], e['dir'], '%.6g' % e['sig'], extra])
    with open(os.path.join(HERE, 'MOFAD_V1_ANOMALY_RESULTS.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        hdr = ['cand', 'n', 'days', 'gross', 'base', 'stressed', 'gross_R',
               'base_R', 'stressed_R', 'win_base', 'pf_base', 'pf_stressed',
               'payoff_stressed', 'ci_lo', 'ci_hi', 'perm_p', 'bh_q',
               'gate_fails']
        w.writerow(hdr)
        for cand in CANDS:
            s = results[cand]
            w.writerow([cand] + ['%.4f' % s[k] if isinstance(s[k], float) else s[k]
                                 for k in hdr[1:-1]] + ['; '.join(s['gate_fails'])])
    with open(os.path.join(HERE, 'MOFAD_V1_HYPOTHESIS_LEDGER.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['cell', 'kind', 'n', 'value', 'note'])
        w.writeheader()
        w.writerows(LED)
    json.dump({'results': results, 'neighbors': NEIGH},
              open(os.path.join(HERE, 'MOFAD_V1_RAW.json'), 'w'),
              indent=1, default=str)

    # ---- console summary --------------------------------------------
    print('\n%-10s %5s %5s %9s %9s %9s %7s %7s %8s %8s' %
          ('cand', 'n', 'days', 'gross', 'base', 'stressed', 'PFb', 'PFs',
           'perm_p', 'bh_q'))
    for cand in CANDS:
        s = results[cand]
        print('%-10s %5d %5d %9.3f %9.3f %9.3f %7.3f %7.3f %8.4f %8.4f' %
              (cand, s['n'], s['days'], s['gross'], s['base'], s['stressed'],
               s['pf_base'], s['pf_stressed'], s['perm_p'], s['bh_q']))
        print('    CI[%.3f,%.3f]  winB %.1f%%  payoffS %.2f  first-fails: %s' %
              (s['ci_lo'], s['ci_hi'], 100 * s['win_base'],
               s['payoff_stressed'],
               s['gate_fails'][0] if s['gate_fails'] else 'NONE'))
    n_pass = sum(1 for c in CANDS if not results[c]['gate_fails'])
    print('\ncandidates passing every runnable preliminary gate: %d / %d'
          % (n_pass, len(CANDS)))
    print('FIVE-YEAR MICROSTRUCTURE DURABILITY: INSUFFICIENT DATA.')
    return n_pass


if __name__ == '__main__':
    sys.exit(0 if main() >= 0 else 1)
