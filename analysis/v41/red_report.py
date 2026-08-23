#!/usr/bin/env python3
# ======================================================================
# RED-* reporting: entry geometry first, points second
# ======================================================================
import os, sys, math, random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import red_lib as R

HZ = R.HORIZONS


def score(B, evs):
    out = []
    for e in evs:
        o = R.outcome(B, e['j'], e['d'])
        if o is None:
            continue
        o.update({k: v for k, v in e.items() if k not in o})
        out.append(o)
    return out


def med(xs):
    s = sorted(xs)
    return s[len(s) // 2] if s else float('nan')


def mean(xs):
    return sum(xs) / len(xs) if xs else float('nan')


def summarize(rows, name, horizon=60):
    """Geometry-first summary at one horizon."""
    if not rows:
        return {'name': name, 'n': 0}
    net = [r['net'][horizon] for r in rows]
    mfe = [r['mfe'][horizon] for r in rows]
    mae = [r['mae'][horizon] for r in rows]
    atr = [r['atr'] for r in rows]
    nmfe = [a / b for a, b in zip(mfe, atr)]
    nmae = [a / b for a, b in zip(mae, atr)]
    days = sorted(set(r['day'] for r in rows))
    span_days = max(1, (len(days)))
    wk = defaultdict(float)
    mo = defaultdict(float)
    for r in rows:
        y, m, dd = int(r['day'][:4]), int(r['day'][5:7]), int(r['day'][8:10])
        import datetime
        iso = datetime.date(y, m, dd).isocalendar()
        wk['%d-W%02d' % (iso[0], iso[1])] += r['net'][horizon]
        mo[r['day'][:7]] += r['net'][horizon]
    srt = sorted(net, reverse=True)
    tot = sum(net)
    top1 = sum(srt[:max(1, len(srt) // 100)])
    top5 = sum(srt[:max(1, len(srt) // 20)])
    ffk = 'ff_1_1'
    fav = sum(1 for r in rows if r['ff'][ffk] == 'FAV')
    adv = sum(1 for r in rows if r['ff'][ffk] == 'ADV')
    amb = sum(1 for r in rows if r['ff'][ffk] == 'AMBIGUOUS')
    # equity max drawdown
    eq = 0.0
    peak = 0.0
    dd_ = 0.0
    for r in sorted(rows, key=lambda x: x['et']):
        eq += r['net'][horizon]
        peak = max(peak, eq)
        dd_ = max(dd_, peak - eq)
    return {'name': name, 'n': len(rows),
            'mean': mean(net), 'median': med(net),
            'mfe': med(nmfe), 'mae': med(nmae),
            'ratio': (med(nmfe) / med(nmae)) if med(nmae) else float('nan'),
            'fav': fav, 'adv': adv, 'amb': amb,
            'favpct': 100.0 * fav / max(1, fav + adv),
            'pos_wk': 100.0 * sum(1 for v in wk.values() if v > 0) / max(1, len(wk)),
            'pos_mo': 100.0 * sum(1 for v in mo.values() if v > 0) / max(1, len(mo)),
            'nwk': len(wk), 'nmo': len(mo), 'ndays': len(days),
            'top1': 100.0 * top1 / tot if tot else float('nan'),
            'top5': 100.0 * top5 / tot if tot else float('nan'),
            'maxdd': dd_, 'total': tot}


def line(s):
    if s['n'] == 0:
        return '  %-34s n=0' % s['name']
    return ('  %-34s n=%4d  mean %+7.2f  med %+6.2f  MFE %.2f MAE %.2f  R %.2f  '
            'ff %4.1f%% (%d/%d amb %d)  wk+ %4.1f%%  mo+ %4.1f%%' %
            (s['name'], s['n'], s['mean'], s['median'], s['mfe'], s['mae'],
             s['ratio'], s['favpct'], s['fav'], s['adv'], s['amb'],
             s['pos_wk'], s['pos_mo']))


def by_part(rows, name, horizon=60):
    out = {}
    for p in ('U', 'DEV', 'IR'):
        sub = [r for r in rows if r['part'] == p]
        out[p] = summarize(sub, '%s [%s]' % (name, p), horizon)
    return out


def signflip_p(rows, horizon=60, iters=2000, seed=17):
    """Sign-flip-by-day null: the correct null for a DIRECTIONAL claim."""
    if not rows:
        return float('nan')
    rnd = random.Random(seed)
    byday = defaultdict(list)
    for r in rows:
        byday[r['day']].append(r)
    days = sorted(byday)
    obs = mean([r['net'][horizon] for r in rows])
    cnt = 0
    n = len(rows)
    for _ in range(iters):
        tot = 0.0
        for d in days:
            s = 1 if rnd.random() < 0.5 else -1
            for r in byday[d]:
                v = r['net'][horizon]
                tot += v if s > 0 else (-(v + R.COST) - R.COST)
        if tot / n >= obs:
            cnt += 1
    return (cnt + 1.0) / (iters + 1.0)


def day_boot_ci(rows, horizon=60, iters=2000, seed=23):
    if not rows:
        return (float('nan'), float('nan'))
    rnd = random.Random(seed)
    byday = defaultdict(list)
    for r in rows:
        byday[r['day']].append(r)
    days = sorted(byday)
    ms = []
    for _ in range(iters):
        pick = [days[rnd.randrange(len(days))] for _ in range(len(days))]
        vals = [r['net'][horizon] for d in pick for r in byday[d]]
        if vals:
            ms.append(mean(vals))
    ms.sort()
    return (ms[int(0.025 * len(ms))], ms[int(0.975 * len(ms))])


def bh(pvals):
    idx = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m = len(pvals)
    q = [None] * m
    prev = 1.0
    for rank, i in enumerate(reversed(idx), 1):
        k = m - rank + 1
        v = min(prev, pvals[i] * m / k)
        q[i] = v
        prev = v
    return q


def horizon_table(rows, name):
    print('    %-14s %s' % (name, '  '.join('%dm: MFE %.2f MAE %.2f R %.2f' %
          (h, med([r['mfe'][h] / r['atr'] for r in rows]),
           med([r['mae'][h] / r['atr'] for r in rows]),
           (med([r['mfe'][h] / r['atr'] for r in rows]) /
            med([r['mae'][h] / r['atr'] for r in rows]))
           if med([r['mae'][h] / r['atr'] for r in rows]) else float('nan'))
          for h in HZ)))


def ff_table(rows, name):
    ks = ['ff_0.25_0.25', 'ff_0.5_0.5', 'ff_1_1', 'ff_1.5_1', 'ff_2_1']
    parts = []
    for k in ks:
        f = sum(1 for r in rows if r['ff'][k] == 'FAV')
        a = sum(1 for r in rows if r['ff'][k] == 'ADV')
        am = sum(1 for r in rows if r['ff'][k] == 'AMBIGUOUS')
        parts.append('%s %4.1f%% (amb %d)' % (k.replace('ff_', ''),
                                              100.0 * f / max(1, f + a), am))
    print('    %-14s %s' % (name, '  '.join(parts)))
