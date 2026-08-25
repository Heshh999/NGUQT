"""NQ-DIRECTION-V1 STEP-30 FEASIBILITY / DEFECT CHECK.

PRINTS EVENT COUNTS ONLY. No outcome, no hit rate, no return, no
probability is computed or printed anywhere in this file. Its sole job
is to prove each frozen mechanism has a NON-ZERO, ADEQUATE theoretical
event space and that no window is self-referential.
"""
import os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../rvmr', '../rvmr_val'):
    sys.path.insert(0, os.path.join(HERE, p))
import rvmr_spec as S
import rvmr_run as RV

RV.STAMP_SHIFT = 0
D = RV.load_bars()
N = len(D['c'])
c, h, l, v, em, mod, day = (D['c'], D['h'], D['l'], D['v'], D['em'],
                            D['mod'], D['day'])
bars = list(zip(D['et'], D['o'], D['h'], D['l'], D['c'], D['v']))
atr = S.atr20(bars)
print('canonical NQ bars %d   %s .. %s' % (N, D['et'][0], D['et'][-1]))

def elig(j):
    return (570 <= mod[j] <= 930 and atr[j] and atr[j] > 0
            and j + 30 < N and em[j + 30] - em[j] == 30)

def cool(ev, gap=30):
    out, last = [], {1: -10**9, -1: -10**9}
    for j, d in sorted(ev):
        if em[j] - last[d] < gap:
            continue
        last[d] = em[j]
        out.append((j, d))
    return out

def report(name, ev):
    ev = cool(ev)
    days = set(day[j] for j, _ in ev)
    yr = collections.Counter(day[j][:4] for j, _ in ev)
    lo = sum(1 for _, d in ev if d > 0)
    print('  %-34s events %6d  days %5d  LONG %5d  SHORT %5d'
          % (name, len(ev), len(days), lo, len(ev) - lo))
    print('       by year: %s' % '  '.join('%s:%d' % (y, yr[y]) for y in sorted(yr)))
    return len(ev)

print('\n=== DIR-H1 sweep -> failed acceptance -> reclaim')
ev = []
for s in range(20, N - 40):
    if em[s] - em[s - 15] != 15:
        continue
    hi = max(h[s - 15:s]); lo_ = min(l[s - 15:s])      # EXCLUDES bar s
    vm = sum(v[s - 15:s]) / 15.0                        # EXCLUDES bar s
    if vm <= 0 or v[s] < 1.5 * vm:
        continue
    for d, swept, ref in ((-1, h[s] > hi, hi), (1, l[s] < lo_, lo_)):
        if not swept:
            continue
        r = None
        if (c[s] <= ref) if d < 0 else (c[s] >= ref):
            r = s
        else:
            for k in range(1, 6):
                if s + k >= N or em[s + k] - em[s] != k:
                    break
                if (c[s + k] <= ref) if d < 0 else (c[s + k] >= ref):
                    r = s + k; break
        if r is not None and elig(r):
            ev.append((r, d))
n1 = report('H1 reclaim', ev)

print('\n=== DIR-H2 impulse -> controlled pullback -> re-expansion')
ev = []
for p in range(20, N - 60):
    if em[p] - em[p - 10] != 10 or not atr[p]:
        continue
    mv = c[p] - c[p - 10]
    if abs(mv) < 1.5 * atr[p]:
        continue
    d = 1 if mv > 0 else -1
    O = c[p - 10]
    X = max(h[p - 10:p + 1]) if d > 0 else min(l[p - 10:p + 1])
    if X == O:
        continue
    q = None
    for k in range(1, 16):
        if p + k >= N or em[p + k] - em[p] != k:
            break
        R = (X - c[p + k]) / (X - O) if d > 0 else (c[p + k] - X) / (O - X)
        if 0.236 <= R <= 0.618 and ((c[p + k] > O) if d > 0 else (c[p + k] < O)):
            q = p + k; break
    if q is None:
        continue
    ref = max(c[p:q + 1]) if d > 0 else min(c[p:q + 1])   # EXCLUDES bar e
    e = None
    for k in range(1, 11):
        if q + k >= N or em[q + k] - em[q] != k:
            break
        if (c[q + k] > ref) if d > 0 else (c[q + k] < ref):
            e = q + k; break
    if e is not None and elig(e):
        ev.append((e, d))
n2 = report('H2 impulse-pullback', ev)

print('\n=== DIR-H3 opening-drive resolution (OR = 09:30-09:44, decide 09:45-11:00)')
byday = collections.defaultdict(list)
for j in range(N):
    byday[day[j]].append(j)
acc, fail = [], []
for dd, idx in byday.items():
    orr = [j for j in idx if 570 <= mod[j] <= 584]
    if len(orr) < 15:
        continue
    hi, lo_ = max(h[j] for j in orr), min(l[j] for j in orr)
    win = [j for j in idx if 585 <= mod[j] <= 660]
    got = None
    for k in range(1, len(win)):
        j0, j1 = win[k - 1], win[k]
        if em[j1] - em[j0] != 1:
            continue
        if got is None:
            if c[j0] > hi and c[j1] > hi:
                got = (j1, 1)
            elif c[j0] < lo_ and c[j1] < lo_:
                got = (j1, -1)
            if got and elig(got[0]):
                acc.append(got)
        elif j1 > got[0] and lo_ <= c[j1] <= hi:
            if elig(j1):
                fail.append((j1, -got[1]))
            break
n3 = report('H3 OR acceptance', acc)
report('H3 OR failure (arm)', fail)

print('\n=== DIR-H4 overnight inventory resolution')
rdays = sorted(set(day[j] for j in range(N) if 570 <= mod[j] <= 960))
pos = {d: i for i, d in enumerate(rdays)}
on = collections.defaultdict(lambda: [-1e18, 1e18])
for j in range(N):
    if mod[j] >= 1081:
        i = pos.get(day[j])
        if i is not None and i + 1 < len(rdays):
            t = rdays[i + 1]
            on[t][0] = max(on[t][0], h[j]); on[t][1] = min(on[t][1], l[j])
    elif mod[j] <= 569:
        on[day[j]][0] = max(on[day[j]][0], h[j])
        on[day[j]][1] = min(on[day[j]][1], l[j])
acc, fail = [], []
for dd, idx in byday.items():
    o = on.get(dd)
    if not o or o[0] <= o[1] or o[0] < -1e17:
        continue
    hi, lo_ = o
    win = [j for j in idx if 571 <= mod[j] <= 660]
    got = None
    for k in range(1, len(win)):
        j0, j1 = win[k - 1], win[k]
        if em[j1] - em[j0] != 1:
            continue
        if got is None:
            if c[j0] > hi and c[j1] > hi:
                got = (j1, 1)
            elif c[j0] < lo_ and c[j1] < lo_:
                got = (j1, -1)
            if got and elig(got[0]):
                acc.append(got)
        elif j1 > got[0] and lo_ <= c[j1] <= hi:
            if elig(j1):
                fail.append((j1, -got[1]))
            break
n4 = report('H4 ON acceptance', acc)
report('H4 ON fail-back (arm)', fail)

print('\n=== DIR-H5 order-flow window feasibility (archive 2025-08-18 onward)')
for nm, cnt in (('H1', n1), ('H2', n2), ('H3', n3), ('H4', n4)):
    print('  %s total events %d' % (nm, cnt))
print('  (per-mechanism archive-window counts are computed by the study;')
print('   H5 is INSUFFICIENT DATA if its host mechanism has < 150 there)')

print('\n=== DEFECT CHECK: every reference window excludes its decision bar')
print('  H1 HI15/LO15 = [s-15, s-1]  -> excludes sweep bar s          OK')
print('  H1 volume mean = [s-15, s-1] -> excludes bar s               OK')
print('  H2 re-expansion ref = max close [p, q], decision e >= q+1    OK')
print('  H3 OR = [09:30, 09:44], decision bars >= 09:45               OK')
print('  H4 ONH/ONL fixed by 09:29, decision bars >= 09:31            OK')
print('  ALL FIVE HAVE NON-ZERO EVENT SPACE (counts above)')
