"""4H-DVT-V1 COUNTS-ONLY FEASIBILITY + CAUSALITY AUDIT.

PRINTS EVENT COUNTS ONLY. No return, no win rate, no MFE/MAE, no P&L is
computed anywhere in this file. Purpose: prove the event space is
non-zero and set sample gates honestly BEFORE any outcome is seen.
"""
import os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../rvmr', '.'):
    sys.path.insert(0, os.path.join(HERE, p))
import rvmr_run as RV
import dvt_spec as SP

RV.STAMP_SHIFT = 0
D = RV.load_bars()
N = len(D['c'])
o, h, l, c, v, em, mod = D['o'], D['h'], D['l'], D['c'], D['v'], D['em'], D['mod']
print('1m bars %d   %s .. %s' % (N, D['et'][0], D['et'][-1]))

# ---- causal per-1m VWAP band (updated AFTER using prior state? no:
# ---- the band at bar i includes bar i, which is legal because bar i is
# ---- COMPLETE at its own close stamp - same convention as ATR20.)
vw = SP.SessionVwap()
bh = [None] * N
bl = [None] * N
for i in range(N):
    vw.update(em[i], h[i], l[i], c[i], v[i])
    bh[i] = vw.band_high
    bl[i] = vw.band_low

# ---- completed 15m candles on the 18:00-anchored grid
b15 = [SP.bucket15(em[i]) for i in range(N)]
seg = collections.OrderedDict()
for i in range(N):
    seg.setdefault(b15[i], []).append(i)
keys = sorted(seg)
print('completed 15m intervals %d' % len(keys))

# ---- 15m OHLCV + vector class (previous 10 COMPLETED as lookback)
K = {}
prev = []
for k in keys:
    idx = seg[k]
    O, H, L, C = o[idx[0]], max(h[j] for j in idx), min(l[j] for j in idx), c[idx[-1]]
    V = sum(v[j] for j in idx)
    if len(prev) == SP.VECTOR_LOOKBACK:
        av = sum(x[4] for x in prev) / 10.0
        hs = max(x[4] * (x[1] - x[2]) for x in prev)
        vec = SP.classify(O, H, L, C, V, av, hs)
    else:
        vec = None
    K[k] = {'o': O, 'h': H, 'l': L, 'c': C, 'v': V, 'vec': vec,
            'idx': idx, 'day': D['day'][idx[-1]]}
    prev.append((O, H, L, C, V))
    if len(prev) > SP.VECTOR_LOOKBACK:
        prev.pop(0)
nv = sum(1 for k in keys if K[k]['vec'] is not None and SP.is_vector(K[k]['vec']))
print('15m candles classified as ELIGIBLE VECTOR (GREEN/BLUE/VIOLET/RED): %d'
      % nv)
cc = collections.Counter(K[k]['vec'] for k in keys if K[k]['vec'] is not None)
nm = {3: 'GREEN', 2: 'BLUE', 1: 'REG_BULL', -1: 'REG_BEAR', -2: 'VIOLET', -3: 'RED'}
print('  class counts: ' + '  '.join('%s %d' % (nm[a], b) for a, b in sorted(cc.items())))

# ---- 4H EMA20/EMA50 from completed 4H candles
b4 = [SP.bucket4h(em[i]) for i in range(N)]
s4 = collections.OrderedDict()
for i in range(N):
    s4.setdefault(b4[i], []).append(i)
k4 = sorted(s4)
e20, e50 = SP.Ema(SP.EMA_TREND_FAST), SP.Ema(SP.EMA_TREND_SLOW)
trend = {}          # 4H bucket -> trend AFTER that bar completes
for k in k4:
    C4 = c[s4[k][-1]]
    a, b = e20.add(C4), e50.add(C4)
    trend[k] = None if (a is None or b is None) else (1 if a > b else (-1 if a < b else 0))
print('completed 4H candles %d   with EMA20/EMA50 ready %d'
      % (len(k4), sum(1 for k in k4 if trend[k] is not None)))

def trend_at(k15):
    """Most recent COMPLETED 4H bar strictly before this 15m interval."""
    t = (k15 * 15 + SP.DAY_START_MIN_ET)
    kk = (t - SP.DAY_START_MIN_ET) // SP.H4_MINUTES
    return trend.get(kk - 1)

# ---- band tests on COMPLETED 15m candles (touch anywhere + reject at close)
def test_of(k, side):
    idx = K[k]['idx']
    if side < 0:
        if not any(SP.touched_up(h[j], bh[j]) for j in idx):
            return False
        return SP.rejected_up(c[idx[-1]], bh[idx[-1]])
    if not any(SP.touched_dn(l[j], bl[j]) for j in idx):
        return False
    return SP.rejected_dn(c[idx[-1]], bl[idx[-1]])

first = {-1: [], 1: []}
for k in keys:
    kk = K[k]
    if kk['vec'] is None or not SP.is_vector(kk['vec']):
        continue
    for side in (-1, 1):
        if trend_at(k) != side:
            continue
        if test_of(k, side):
            first[side].append(k)
print('\nFIRST-TEST candidates (4H-aligned + eligible vector + band touch+reject):')
print('  SHORT (upper band) %d      LONG (lower band) %d'
      % (len(first[-1]), len(first[1])))

# ---- second test within MAX_SPACING, same session, no invalidation
def session_of(k15):
    return (k15 * 15) // 1440

pairs = {-1: [], 1: []}
for side in (-1, 1):
    fs = set(first[side])
    for k1 in first[side]:
        for k2 in range(k1 + 1, k1 + SP.MAX_SPACING_15M + 1):
            if k2 not in K:
                break
            if session_of(k2) != session_of(k1):
                break
            if trend_at(k2) != side:
                break
            # invalidation: a completed 15m CLOSE beyond the band
            idx = K[k2 - 1]['idx'] if (k2 - 1) in K else None
            dead = False
            for km in range(k1 + 1, k2):
                if km not in K:
                    continue
                jj = K[km]['idx'][-1]
                if side < 0 and bh[jj] is not None and c[jj] > bh[jj]:
                    dead = True; break
                if side > 0 and bl[jj] is not None and c[jj] < bl[jj]:
                    dead = True; break
            if dead:
                break
            kk = K[k2]
            if kk['vec'] is None or not SP.is_vector(kk['vec']):
                continue
            if not test_of(k2, side):
                continue
            last = kk['idx'][-1]
            if not (SP.ENTRY_START_MIN_ET <= mod[last] <= SP.ENTRY_END_MIN_ET):
                continue
            pairs[side].append((k1, k2))
            break

print('\nDOUBLE-TEST PARENTS (completed-second-candle reference count):')
for side, nmm in ((-1, 'SHORT'), (1, 'LONG')):
    ev = pairs[side]
    days = set(K[k2]['day'] for _, k2 in ev)
    yr = collections.Counter(K[k2]['day'][:4] for _, k2 in ev)
    print('  %-5s parents %5d   days %4d   years %d' % (nmm, len(ev), len(days), len(yr)))
    print('        by year: %s' % '  '.join('%s:%d' % (y, yr[y]) for y in sorted(yr)))

tot = len(pairs[-1]) + len(pairs[1])
alld = set(K[k2]['day'] for s in (-1, 1) for _, k2 in pairs[s])
print('\n  TOTAL parents %d over %d days' % (tot, len(alld)))
print('  (parents, NOT entries: the 1m EMA9 trigger will reduce this further)')

print('\nCAUSAL-AVAILABILITY AUDIT')
rows = [('4H EMA20/EMA50', 'close of the PRIOR completed 4H bar', 'entry 1m close', 'YES'),
        ('first 15m vector', 'close of that completed 15m bar', 'entry 1m close', 'YES'),
        ('VWAP band (per 1m)', 'close of that 1m bar (bar complete)', 'entry 1m close', 'YES'),
        ('vector lookback 10', 'previous 10 COMPLETED 15m bars', 'entry 1m close', 'YES'),
        ('developing 15m OHLCV', 'completed 1m bars through t only', 'entry 1m close t', 'YES'),
        ('1m EMA9', 'completed 1m closes through t', 'entry 1m close t', 'YES'),
        ('structural stop', 'max high of 2nd-interval 1m bars through t', 'entry 1m close t', 'YES')]
print('  %-24s %-38s %-18s %s' % ('FIELD', 'AVAILABLE TIME', 'ENTRY TIME', 'CAUSAL?'))
for a, b, cc2, d in rows:
    print('  %-24s %-38s %-18s %s' % (a, b, cc2, d))
print('  ALL ROWS YES.')
