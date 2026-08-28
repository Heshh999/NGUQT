#!/usr/bin/env python3
# Month-by-month P&L profile for OFH13, 1 MNQ contract, $2,500 start.
# Bootstrap of the 133 frozen trades. Sizing/expectation study only.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
import re, os, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
net = []
for ln in open(os.path.join(HERE, '..', 'ofh13mem', 'EVENT_LISTING.txt')):
    m = re.search(r'\s([+-]\d+\.\d\d)\s+(WIN|LOSS)', ln)
    if m: net.append(float(m.group(1)))
d = np.array(net) * 2.0
assert len(d) == 133

START = 2500.0
FLOOR = 100.0          # intraday margin; below this you cannot open a trade
B = 200000
TPM = 133 / 12.0       # ~11.1 trades per month

def sim(mult, seed):
    """12 months of trade counts drawn Poisson around 11.1/month."""
    rng = np.random.default_rng(seed)
    pool = np.where(d < 0, d * mult, d)
    counts = rng.poisson(TPM, size=(B, 12))
    monthly = np.zeros((B, 12))
    for m in range(12):
        mx = counts[:, m].max()
        draws = rng.choice(pool, size=(B, mx), replace=True)
        mask = np.arange(mx)[None, :] < counts[:, m][:, None]
        monthly[:, m] = (draws * mask).sum(axis=1)
    return monthly, counts

for label, mult, seed in (('AS-OBSERVED', 1.0, 21), ('STRESSED (losses x1.5)', 1.5, 22)):
    monthly, counts = sim(mult, seed)
    eq = START + np.cumsum(monthly, axis=1)
    print('=' * 74)
    print('%s   start $%.0f, 1 MNQ contract' % (label, START))
    print('=' * 74)
    print('ONE TYPICAL MONTH (~%.1f trades)' % TPM)
    flat = monthly.ravel()
    for p, lab in ((5, 'p5  bad month  '), (25, 'p25            '),
                   (50, 'p50  median    '), (75, 'p75            '),
                   (95, 'p95  good month')):
        print('   %s $%+8.0f' % (lab, np.percentile(flat, p)))
    print('   mean            $%+8.0f' % flat.mean())
    print('   P(losing month)  %.0f%%' % (100 * (flat < 0).mean()))
    print('   P(month < -$250) %.0f%%   P(month > +$500) %.0f%%'
          % (100 * (flat < -250).mean(), 100 * (flat > 500).mean()))
    print('   worst month seen in 200k sims  $%.0f' % flat.min())

    print('\nACCOUNT BALANCE AT EACH MONTH-END (percentiles)')
    print('   %-5s %10s %10s %10s %10s %10s' % ('month', 'p5', 'p25', 'median', 'p75', 'p95'))
    for m in (0, 1, 2, 5, 8, 11):
        row = eq[:, m]
        print('   %-5d %10.0f %10.0f %10.0f %10.0f %10.0f'
              % (m + 1, *[np.percentile(row, q) for q in (5, 25, 50, 75, 95)]))

    losing = (monthly < 0).sum(axis=1)
    # longest losing-month streak
    st = np.zeros(B, int); cur = np.zeros(B, int)
    for m in range(12):
        l = monthly[:, m] < 0
        cur = np.where(l, cur + 1, 0); st = np.maximum(st, cur)
    print('\nTHE YEAR')
    print('   losing months out of 12: median %d   p95 %d'
          % (np.median(losing), np.percentile(losing, 95)))
    print('   longest run of consecutive losing months: median %d  p95 %d'
          % (np.median(st), np.percentile(st, 95)))
    print('   year-end P&L: median $%+.0f   p5 $%+.0f   p95 $%+.0f'
          % (np.median(eq[:, 11] - START), np.percentile(eq[:, 11] - START, 5),
             np.percentile(eq[:, 11] - START, 95)))
    print('   P(year ends below start)  %.0f%%' % (100 * (eq[:, 11] < START).mean()))
    dd = (np.maximum.accumulate(np.c_[np.full(B, START), eq], axis=1)
          - np.c_[np.full(B, START), eq]).max(axis=1)
    print('   worst drawdown in the year: median $%.0f  p95 $%.0f  p99 $%.0f'
          % (np.median(dd), np.percentile(dd, 95), np.percentile(dd, 99)))
    print('   P(account ever below $%.0f margin floor) %.1f%%'
          % (FLOOR, 100 * (np.minimum.accumulate(eq, axis=1)[:, -1] <= FLOOR).mean()))
    print('   P(account ever down 50%% i.e. below $%.0f) %.1f%%'
          % (START / 2, 100 * (np.minimum.accumulate(eq, axis=1)[:, -1] <= START / 2).mean()))
    print()
