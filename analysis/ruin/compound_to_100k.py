#!/usr/bin/env python3
# ======================================================================
# OFH13 COMPOUNDING STUDY - size up every 6 months, target $100,000
# Bootstrap of the 133 frozen OFH13 trades. Sizing study only.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import re, os, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
net = []
for ln in open(os.path.join(HERE, '..', 'ofh13mem', 'EVENT_LISTING.txt')):
    m = re.search(r'\s([+-]\d+\.\d\d)\s+(WIN|LOSS)', ln)
    if m: net.append(float(m.group(1)))
pts = np.array(net)                      # points per trade, 1 contract
PV = 2.0                                 # MNQ $/pt
START, TARGET = 2500.0, 100000.0
MARGIN = 100.0                           # per contract intraday
TPM = 133 / 12.0
B = 100000
YEARS = 10
MONTHS = YEARS * 12


def run(cap_per_contract, mult, ratchet, seed):
    """cap_per_contract: $ of equity required per contract.
       mult: loss stress multiplier.
       ratchet: True = size never decreases (their stated rule);
                False = size recomputed both ways every 6 months."""
    rng = np.random.default_rng(seed)
    pool = np.where(pts < 0, pts * mult, pts) * PV
    eq = np.full(B, START)
    n = np.maximum(1, np.floor(eq / cap_per_contract)).astype(int)
    alive = np.ones(B, bool)
    hit = np.zeros(B, bool)
    hit_month = np.full(B, -1)
    peak = eq.copy()
    maxdd = np.zeros(B)
    for m in range(MONTHS):
        k = rng.poisson(TPM, B)
        mx = max(1, k.max())
        draws = rng.choice(pool, size=(B, mx), replace=True)
        mask = np.arange(mx)[None, :] < k[:, None]
        # apply trade by trade so an intra-month wipeout is caught
        for j in range(mx):
            step = draws[:, j] * mask[:, j] * n * alive
            eq = eq + step
            dead = alive & (eq < MARGIN * 1)      # cannot fund 1 contract
            alive &= ~dead
            eq = np.where(alive, eq, np.maximum(eq, 0.0))
        peak = np.maximum(peak, eq)
        maxdd = np.maximum(maxdd, (peak - eq) / np.maximum(peak, 1e-9))
        newly = alive & ~hit & (eq >= TARGET)
        hit_month = np.where(newly, m + 1, hit_month)
        hit |= newly
        if (m + 1) % 6 == 0:                      # resize every 6 months
            want = np.maximum(1, np.floor(eq / cap_per_contract)).astype(int)
            n = np.maximum(n, want) if ratchet else want
            n = np.where(alive, n, 1)
    return dict(hit=hit, hit_month=hit_month, eq=eq, alive=alive, maxdd=maxdd)


def show(tag, r):
    h = r['hit']
    med = np.median(r['hit_month'][h]) if h.any() else float('nan')
    p90 = np.percentile(r['hit_month'][h], 90) if h.any() else float('nan')
    print('  %-34s reach100k %5.1f%%  ruin %5.1f%%  medMonths %5s  '
          'medEq $%8.0f  medMaxDD %4.0f%%'
          % (tag, 100 * h.mean(), 100 * (~r['alive']).mean(),
             ('%.0f' % med) if h.any() else 'n/a',
             np.median(r['eq']), 100 * np.median(r['maxdd'])))


for mult, lab in ((1.0, 'AS-OBSERVED'), (1.5, 'STRESSED (losses x1.5)')):
    print('=' * 96)
    print('%s   start $2,500  ->  target $100,000   (10-year horizon)' % lab)
    print('=' * 96)
    print('  RATCHET-UP-ONLY (size never decreases - the stated plan)')
    for cap in (1250, 2500, 5000, 7500, 10000):
        show('  $%d equity per contract' % cap,
             run(cap, mult, True, 1000 + cap))
    print('  FULL REBALANCE (size also decreases after losses)')
    for cap in (1250, 2500, 5000, 7500, 10000):
        show('  $%d equity per contract' % cap,
             run(cap, mult, False, 2000 + cap))
    print()

print('FIXED 1 CONTRACT FOREVER (no compounding) - the baseline to beat')
for mult, lab in ((1.0, 'as-observed'), (1.5, 'stressed')):
    r = run(10 ** 9, mult, False, 77)
    print('  %-12s  reach100k %.1f%%   ruin %.1f%%   median equity after 10y $%.0f'
          % (lab, 100 * r['hit'].mean(), 100 * (~r['alive']).mean(),
             np.median(r['eq'])))
