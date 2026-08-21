#!/usr/bin/env python3
# OFH6 - THE DECISIVE PASS INSIDE THE TEN-MONTH CONSTRAINT
#
# Established by power10b.py, under the CORRECT sign-flip null:
#   OFH6 excess +8.301 pt/trade, single-hypothesis p = 0.019,
#   FAMILY-WISE p = 0.129 (nine hypotheses searched).
#   Dose-response slope +32.0, null p = 0.019 (nested cells).
#
# Two things remain before OFH6 can be called anything at all:
#
#  A. THE HARD LIMIT. 205 sessions is the real sample - not 783 trades.
#     If the day is the independent unit, adding trades inside a day
#     cannot buy power past a floor. Measure that floor, because it says
#     what ten months can NEVER resolve, no matter how the test is built.
#
#  B. REALISTIC MANAGEMENT. The +8.3 was a pure 60-minute time exit with
#     NO STOP. In ofh.py the same rule with a 1.5 ATR stop scored -0.36
#     DEV / +3.89 VAL. An edge that exists only without a stop is not an
#     edge a $1,000 account can hold. Every management variant is scored
#     here against the same sign-flip null, plus the actual drawdown a
#     single MNQ contract would have carried.
#
# MNQ = $2.00 per index point per contract. No live trading is authorised
# by this project; these are research statistics only.

import pickle, random, math
from collections import defaultdict

SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
CACHE = SCR + '/of_bars2.pkl'
COST = 0.87
HORIZON = 90
DEV_END = '2026-03-31'
DOLLARS = 2.0
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
    if (not b['isRth'] or b['minutesFromRthOpen'] is None
            or b['minutesFromRthOpen'] < 30 or b['minutesToRthClose'] is None
            or b['minutesToRthClose'] < HORIZON or b['atr'] is None
            or b['atr'] <= 0 or b['dsum15'] is None):
        continue
    if B[j + HORIZON]['tmin'] - b['tmin'] != HORIZON:
        continue
    ELIG.append(j)


def net60(j, side):
    return (B[j + 60]['close'] - B[j]['close']) * side


def split_of(day):
    return 'DEV' if day <= DEV_END else 'VAL'


base = {}
for sp in ('DEV', 'VAL'):
    for side in (+1, -1):
        v = [net60(j, side) for j in ELIG if split_of(B[j]['day']) == sp]
        base[(sp, side)] = sum(v) / len(v)

DAYS = sorted(set(B[j]['day'] for j in ELIG))
dev_abs = sorted(abs(B[j]['dsum15']) for j in ELIG if B[j]['day'] <= DEV_END)
THR = dev_abs[int(len(dev_abs) * 0.90)]

rows = []
last = -10 ** 9
for j in ELIG:
    v = B[j]['dsum15']
    if abs(v) < THR or B[j]['tmin'] - last < 30:
        continue
    last = B[j]['tmin']
    rows.append((j, +1 if v > 0 else -1))
print('OFH6 trades: %d over %d sessions (%.1f/session)'
      % (len(rows), len(DAYS), len(rows) / float(len(DAYS))))

# ================================================= A. the hard limit
print('\n' + '=' * 100)
print('A.  THE HARD LIMIT OF 205 SESSIONS')
print('=' * 100)
print('  SE of mean excess vs trade count, trades drawn across all sessions.')
print('  If the SE stops falling, that floor is what ten months can resolve.')
print('  %10s %10s %14s' % ('trades', 'SE pt', 'MDE pt/trade'))
prev = None
for ntr in (200, 400, 800, 1600, 3200, 6400, 12800, 25600):
    ses = []
    for _ in range(5):
        pick = random.sample(ELIG, min(ntr, len(ELIG)))
        bd = defaultdict(list)
        for j in pick:
            d = +1 if random.random() < 0.5 else -1
            bd[B[j]['day']].append(net60(j, d) - base[(split_of(B[j]['day']), d)])
        pools = list(bd.values())
        ms = []
        for _ in range(250):
            s = [x for dd in random.choices(pools, k=len(pools)) for x in dd]
            ms.append(sum(s) / len(s))
        m = sum(ms) / len(ms)
        ses.append((sum((v - m) ** 2 for v in ms) / (len(ms) - 1)) ** 0.5)
    se = sum(ses) / len(ses)
    print('  %10d %10.3f %14.2f' % (ntr, se, 2.80 * se))
print('\n  CAUTION reading that table: it assigns each drawn trade a RANDOM')
print('  side, so trades inside a day partly cancel and the clustering')
print('  looks mild. A real rule holds the SAME side for most of a day.')
print('  The measured sign-flip SE for the ACTUAL OFH6 trade set is 3.979')
print('  at n=783, about 34%% above the 2.973 this table shows - so the')
print('  honest single-hypothesis MDE for OFH6 is 2.80 x 3.979 = %.1f pt.'
      % (2.80 * 3.979))
print('  OFH6 measures +8.3, i.e. BELOW its own detection threshold. To')
print('  resolve an effect that size the SE must reach ~2.96, which needs')
print('  roughly (3.979/2.96)^2 = %.1fx this window - about 18 months.'
      % ((3.979 / 2.96) ** 2))


# ================================================= B. management variants
def race(j, side, stop_mult, cap):
    """exact 1m walk; stop in ATR multiples, time cap in minutes."""
    e = B[j]['close']
    a = B[j]['atr']
    stop_px = e - side * stop_mult * a if stop_mult else None
    mae = 0.0
    for k in range(1, cap + 1):
        c = B[j + k]
        adv = (e - c['low']) if side > 0 else (c['high'] - e)
        if adv > mae:
            mae = adv
        if stop_px is not None:
            if (side > 0 and c['low'] <= stop_px) or (side < 0 and c['high'] >= stop_px):
                return (stop_px - e) * side, mae
    return (B[j + cap]['close'] - e) * side, mae


def signflip_p(vals_by_row, NS=2000):
    """vals_by_row: list of (j, d, fn) -> recompute under flipped side."""
    real = sum(v for _, _, v in vals_by_row) / len(vals_by_row)
    daylist = sorted(set(B[j]['day'] for j, _, _ in vals_by_row))
    ge = 0
    dist = []
    for _ in range(NS):
        flip = {d: (1 if random.random() < 0.5 else -1) for d in daylist}
        acc = 0.0
        for j, d, _ in vals_by_row:
            dd = d * flip[B[j]['day']]
            acc += FLIPFN[(j, dd)]
        m = acc / len(vals_by_row)
        dist.append(m)
        if m >= real:
            ge += 1
    dist.sort()
    return real, dist[NS // 2], ge / float(NS)


print('\n' + '=' * 100)
print('B.  MANAGEMENT VARIANTS - each against the sign-flip null')
print('=' * 100)
print('  %-22s %8s %10s %10s %8s %10s %10s'
      % ('management', 'trades', 'excess', 'nullMed', 'p', 'medMAE', 'p95 MAE'))
VARIANTS = [('no stop, 60m exit', None, 60),
            ('no stop, 90m exit', None, 90),
            ('3.0 ATR stop, 60m', 3.0, 60),
            ('2.0 ATR stop, 60m', 2.0, 60),
            ('1.5 ATR stop, 90m', 1.5, 90),
            ('1.0 ATR stop, 60m', 1.0, 60)]
summary = {}
for name, sm, cap in VARIANTS:
    FLIPFN = {}
    vb = []
    maes = []
    for j, d in rows:
        for dd in (+1, -1):
            r, _m = race(j, dd, sm, cap)
            FLIPFN[(j, dd)] = r - base[(split_of(B[j]['day']), dd)]
        r, m = race(j, d, sm, cap)
        maes.append(m)
        vb.append((j, d, r - base[(split_of(B[j]['day']), d)]))
    real, nullmed, p = signflip_p(vb)
    maes.sort()
    summary[name] = (real, p, [v for _, _, v in vb])
    print('  %-22s %8d %+10.3f %+10.3f %8.3f %10.1f %10.1f'
          % (name, len(vb), real, nullmed, p,
             maes[len(maes) // 2], maes[int(len(maes) * .95)]))

print('\n  The stop columns are the verdict on tradability: MAE p95 shows')
print('  what a single contract actually had to sit through.')

# ================================================= C. daily series
print('\n' + '=' * 100)
print('C.  DAILY P&L, ONE MNQ CONTRACT, best surviving management')
print('=' * 100)
bestname = max(summary, key=lambda k: summary[k][0])
vals = summary[bestname][2]
print('  using: %s   (excess %+0.3f pt, sign-flip p %.3f)'
      % (bestname, summary[bestname][0], summary[bestname][1]))
byday = defaultdict(float)
for (j, d), v in zip(rows, vals):
    byday[B[j]['day']] += (v - COST) * DOLLARS
ser = [byday[d] for d in DAYS if d in byday]
tot = sum(ser)
eq = 0.0
peak = 0.0
mdd = 0.0
for v in ser:
    eq += v
    peak = max(peak, eq)
    mdd = min(mdd, eq - peak)
mu = tot / len(ser)
sd = (sum((v - mu) ** 2 for v in ser) / (len(ser) - 1)) ** 0.5
print('  sessions traded %d   total $%+0.0f   mean/session $%+0.2f   SD $%0.2f'
      % (len(ser), tot, mu, sd))
print('  max drawdown $%0.0f   annualised Sharpe-like %.2f'
      % (-mdd, mu / sd * math.sqrt(252) if sd else float('nan')))
print('  NOTE this is EXCESS over the side-matched baseline minus cost, on')
print('  the same window the rule was selected from. It is an upper bound,')
print('  not an expectation. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
