#!/usr/bin/env python3
# WORKING WITHIN TEN MONTHS - what can this window actually certify?
#
# The order-flow capture is ten months and will stay ten months for now.
# That is a fixed constraint, so the right question is not "is it enough"
# but "what edge size is DETECTABLE here, and what protocol extracts the
# most evidence per month of data".
#
# Three jobs:
#
#  1. POWER. Given the observed per-trade dispersion and the day
#     clustering, what is the minimum detectable edge at 80% power for a
#     range of trade counts? This defines what is worth looking for.
#     Everything smaller than the MDE is undetectable here no matter how
#     clever the test, and claiming it would be dishonest.
#
#  2. BASELINE. The window 2025-11 .. 2026-08 has its own drift. A long
#     signal that beats zero has proved nothing if every long beat zero.
#     Every number below is reported as EXCESS over a side-matched,
#     split-matched baseline of all eligible bars.
#
#  3. DOSE-RESPONSE. The single most powerful technique available on a
#     short window: instead of one threshold and one p-value, sweep the
#     signal strength and ask whether the effect SCALES. A real effect
#     grows with dose; noise does not. This uses every bar in the window
#     and costs no extra data.
#
# SELECTION WARNING, stated once and applying to every OFH6 number here:
# OFH6 was chosen as the best of twelve on this same window. Nothing
# below can undo that. These statistics describe how OFH6 behaves; they
# are NOT a valid significance test for it, and the family-wise p=0.688
# from ofh2.py still stands as the honest verdict on its discovery. What
# these numbers ARE good for: deciding whether OFH6 is worth the cost of
# a pre-registered forward test, and calibrating what such a test needs.

import pickle, random, math
from collections import defaultdict

SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
CACHE = SCR + '/of_bars2.pkl'
COST = 0.87
HORIZON = 90
DEV_END = '2026-03-31'
random.seed(41)

with open(CACHE, 'rb') as fh:
    B = pickle.load(fh)
n = len(B)

for j in range(n):
    if j >= 15 and B[j]['tmin'] - B[j - 15]['tmin'] == 15:
        s = 0.0
        bad = False
        for k in range(j - 14, j + 1):
            v = B[k]['ofBarDelta']
            if v is None:
                bad = True
                break
            s += v
        B[j]['dsum15'] = None if bad else s
    else:
        B[j]['dsum15'] = None

ELIG = []
for j in range(n - HORIZON - 1):
    b = B[j]
    if not b['isRth']:
        continue
    if b['minutesFromRthOpen'] is None or b['minutesFromRthOpen'] < 30:
        continue
    if b['minutesToRthClose'] is None or b['minutesToRthClose'] < HORIZON:
        continue
    if b['atr'] is None or b['atr'] <= 0:
        continue
    if B[j + HORIZON]['tmin'] - b['tmin'] != HORIZON:
        continue
    if b['dsum15'] is None:
        continue
    ELIG.append(j)


def net60(j, side):
    return (B[j + 60]['close'] - B[j]['close']) * side


def split_of(day):
    return 'DEV' if day <= DEV_END else 'VAL'


MON = sorted(set(B[j]['day'][:7] for j in ELIG))
print('eligible bars %d over %d months  %s .. %s'
      % (len(ELIG), len(MON), MON[0], MON[-1]))

# ================================================================ 1. POWER
print('\n' + '=' * 100)
print('1.  WHAT IS DETECTABLE IN TEN MONTHS?')
print('=' * 100)

allret = [net60(j, +1) for j in ELIG]
mu_all = sum(allret) / len(allret)
sd = (sum((v - mu_all) ** 2 for v in allret) / (len(allret) - 1)) ** 0.5
print('  per-trade 60m return: mean %+0.3f pt   SD %0.2f pt' % (mu_all, sd))

# day clustering inflates the SE. measure the inflation factor directly:
# bootstrap by DAY vs by TRADE on a fixed random subsample.
byday = defaultdict(list)
for j in ELIG:
    byday[B[j]['day']].append(net60(j, +1))
days = list(byday.values())


def se_dayblock(day_pools, nb=400):
    ms = []
    for _ in range(nb):
        s = [x for dd in random.choices(day_pools, k=len(day_pools)) for x in dd]
        ms.append(sum(s) / len(s))
    m = sum(ms) / len(ms)
    return (sum((v - m) ** 2 for v in ms) / (len(ms) - 1)) ** 0.5


se_day = se_dayblock(days)
ntot = len(ELIG)
se_iid = sd / math.sqrt(ntot)
infl = se_day / se_iid
print('  day-block SE %0.4f vs iid SE %0.4f  ->  clustering inflation x%0.2f'
      % (se_day, se_iid, infl))
print('  (trades on the same day share the same tape, so the effective')
print('   sample is smaller than the trade count suggests)')

print('\n  minimum detectable edge, 80%% power, two-sided alpha=0.05,')
print('  including the clustering inflation measured above:')
print('  %10s %14s %14s' % ('trades', 'MDE pt/trade', 'MDE $/trade'))
for nn in (250, 500, 1000, 2000, 5000, 10000, 20000):
    mde = 2.80 * infl * sd / math.sqrt(nn)
    print('  %10d %14.2f %14.2f' % (nn, mde, mde * 2.0))
print('\n  READ THIS AS THE BUDGET: at ~800 trades (what OFH6 generated)')
print('  only an edge bigger than ~%0.1f pt/trade is detectable. Anything'
      % (2.80 * infl * sd / math.sqrt(800)))
print('  smaller is real-or-not-indistinguishable HERE. The only lever we')
print('  control is TRADE COUNT - more events per month buys power that')
print('  more months would otherwise have to buy.')

# ============================================================= 2. BASELINE
print('\n' + '=' * 100)
print('2.  SIDE-MATCHED BASELINE (the window has its own drift)')
print('=' * 100)
base = {}
for sp in ('DEV', 'VAL', 'ALL'):
    for side in (+1, -1):
        v = [net60(j, side) for j in ELIG
             if sp == 'ALL' or split_of(B[j]['day']) == sp]
        base[(sp, side)] = sum(v) / len(v)
print('  mean 60m return of ALL eligible bars, before cost:')
for sp in ('DEV', 'VAL', 'ALL'):
    print('    %-4s  long %+0.3f pt   short %+0.3f pt' % (sp, base[(sp, +1)], base[(sp, -1)]))
print('  -> every OFH6 number below is EXCESS over the matching cell,')
print('     so window drift cannot masquerade as edge.')

# ======================================================== 3. DOSE-RESPONSE
print('\n' + '=' * 100)
print('3.  DOSE-RESPONSE: does the effect SCALE with cum-delta strength?')
print('=' * 100)
print('  OFH6 rule: |15-bar cum-delta sum| above a percentile of the DEV')
print('  distribution -> trade its sign. Sweeping the percentile turns one')
print('  p-value into a shape. A real effect rises with dose.')

dev_abs = sorted(abs(B[j]['dsum15']) for j in ELIG if B[j]['day'] <= DEV_END)


def q(p):
    return dev_abs[min(int(len(dev_abs) * p), len(dev_abs) - 1)]


def trades_at(pct, cooldown):
    thr = q(pct)
    out = []
    last = -10 ** 9
    for j in ELIG:
        v = B[j]['dsum15']
        if abs(v) < thr:
            continue
        if B[j]['tmin'] - last < cooldown:
            continue
        last = B[j]['tmin']
        d = +1 if v > 0 else -1
        out.append((j, d, net60(j, d) - base[(split_of(B[j]['day']), d)]))
    return out


def trimmed(vals, frac=0.05):
    v = sorted(vals)
    k = int(len(v) * frac)
    return sum(v[k:len(v) - k]) / max(len(v) - 2 * k, 1)


def dayboot(rows, nb=2000):
    bd = defaultdict(list)
    for j, _, v in rows:
        bd[B[j]['day']].append(v)
    pools = list(bd.values())
    ms = []
    for _ in range(nb):
        s = [x for dd in random.choices(pools, k=len(pools)) for x in dd]
        ms.append(sum(s) / len(s))
    ms.sort()
    return ms[int(nb * .025)], ms[int(nb * .975)], sum(1 for x in ms if x <= 0) / nb


print('\n  cooldown 30 min (as declared in ofh.py)')
print('  %6s %8s %10s %10s %10s %10s %18s'
      % ('pctile', 'trades', 'excessMU', 'excessMED', 'trim5%', 'net-cost', 'day-block 95% CI'))
for p in (0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.98):
    rows = trades_at(p, 30)
    if len(rows) < 60:
        continue
    vals = [v for _, _, v in rows]
    mu = sum(vals) / len(vals)
    med = sorted(vals)[len(vals) // 2]
    lo, hi, pv = dayboot(rows)
    print('  %6.2f %8d %+10.3f %+10.3f %+10.3f %+10.3f   [%+0.2f, %+0.2f] p=%.3f'
          % (p, len(rows), mu, med, trimmed(vals), mu - COST, lo, hi, pv))

print('\n  cooldown 5 min (more trades = more power, same rule)')
print('  %6s %8s %10s %10s %10s %10s %18s'
      % ('pctile', 'trades', 'excessMU', 'excessMED', 'trim5%', 'net-cost', 'day-block 95% CI'))
for p in (0.50, 0.70, 0.80, 0.90, 0.95):
    rows = trades_at(p, 5)
    if len(rows) < 60:
        continue
    vals = [v for _, _, v in rows]
    mu = sum(vals) / len(vals)
    med = sorted(vals)[len(vals) // 2]
    lo, hi, pv = dayboot(rows)
    print('  %6.2f %8d %+10.3f %+10.3f %+10.3f %+10.3f   [%+0.2f, %+0.2f] p=%.3f'
          % (p, len(rows), mu, med, trimmed(vals), mu - COST, lo, hi, pv))

# ---- month-by-month at the declared setting, on EXCESS
print('\n  month-by-month EXCESS at the declared p90 / 30-min setting')
rows = trades_at(0.90, 30)
bymon = defaultdict(list)
byside = defaultdict(list)
for j, d, v in rows:
    bymon[B[j]['day'][:7]].append(v)
    byside[d].append(v)
for m, v in sorted(bymon.items()):
    print('    %s  n=%3d  excess %+8.3f' % (m, len(v), sum(v) / len(v)))
print('    LONG  n=%d excess %+0.3f     SHORT n=%d excess %+0.3f'
      % (len(byside[+1]), sum(byside[+1]) / len(byside[+1]),
         len(byside[-1]), sum(byside[-1]) / len(byside[-1])))

# ---- k=1 shuffled null for the declared setting (what a PRE-REGISTERED
#      test would have been worth - reported for calibration only)
print('\n  single-hypothesis shuffled null at p90/30min (CALIBRATION ONLY -')
print('  OFH6 was selected from twelve, so this is NOT its p-value)')
idx = [j for j, _, _ in rows]
pool = defaultdict(list)
for j in ELIG:
    pool[B[j]['day']].append(j)
sigs = {j: d for j, d, _ in rows}
real_mu = sum(v for _, _, v in rows) / len(rows)
NS = 1000
dist = []
cur = {j: net60(j, +1) for j in ELIG}
for _ in range(NS):
    for _, ii in pool.items():
        vv = [cur[j] for j in ii]
        random.shuffle(vv)
        for j, v in zip(ii, vv):
            cur[j] = v
    acc = []
    for j, d, _ in rows:
        acc.append(d * cur[j] - base[(split_of(B[j]['day']), d)])
    dist.append(sum(acc) / len(acc))
dist.sort()
ge = sum(1 for x in dist if x >= real_mu)
print('    real excess %+0.3f   noise median %+0.3f  p95 %+0.3f   p(k=1) = %.4f'
      % (real_mu, dist[NS // 2], dist[int(NS * .95)], ge / NS))
print('    family-wise p from ofh2.py (the honest one) = 0.688')

# =============================================== 4. BLOCK CROSS-VALIDATION
print('\n' + '=' * 100)
print('4.  BLOCK CV - all ten months used, one held out at a time')
print('=' * 100)
print('  Threshold refit on the nine training months, scored on the held-')
print('  out month. Uses the whole window for both roles instead of')
print('  spending half of it on a split.')
oos = []
for hm in MON:
    tr = [j for j in ELIG if B[j]['day'][:7] != hm]
    te = [j for j in ELIG if B[j]['day'][:7] == hm]
    if not tr or not te:
        continue
    tq = sorted(abs(B[j]['dsum15']) for j in tr)
    thr = tq[int(len(tq) * 0.90)]
    acc = []
    last = -10 ** 9
    for j in te:
        v = B[j]['dsum15']
        if abs(v) < thr or B[j]['tmin'] - last < 30:
            continue
        last = B[j]['tmin']
        d = +1 if v > 0 else -1
        acc.append(d * net60(j, d) - base[(split_of(B[j]['day']), d)])
    if acc:
        oos.append((hm, len(acc), sum(acc) / len(acc)))
for hm, k, v in oos:
    print('    %s  n=%3d  excess %+8.3f' % (hm, k, v))
tot = sum(v * k for _, k, v in oos) / sum(k for _, k, v in oos)
pos = sum(1 for _, _, v in oos if v > 0)
print('    pooled CV excess %+0.3f pt   positive months %d/%d' % (tot, pos, len(oos)))
