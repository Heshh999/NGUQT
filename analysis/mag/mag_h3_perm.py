#!/usr/bin/env python3
# MAG-H3 inference, day-clustered, computationally tractable.
# The full-sample Spearman permutation is infeasible (2,000 x 83,596-point
# rank correlations). Day-level clustering gives the same null - whole days
# of predictor are shuffled against whole days of outcome - at 315 units
# instead of 83,596, which is exactly the resolution the clustering assumes.
import os, sys, random, statistics, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
import mag_lib as M, cand_spec as CS
from mag_h3 import spearman, bucket, day_boot_ci

B = CS.load_merged(); M.build_features(B)
rows = []
for j, b in enumerate(B):
    if not M.eligible(b) or b['mag'] is None or not M.consec(B, j, 30):
        continue
    px = b['close']; hi = lo = px
    for k in range(1, 31):
        c = B[j + k]; hi = max(hi, c['high']); lo = min(lo, c['low'])
    rows.append({'day': b['day'], 'mag': b['mag'], 'rng': b['mag_rng'],
                 'vol': b['mag_vol'], 'abs30': abs(B[j + 30]['close'] - px),
                 'trng30': hi - lo})
print('n = %d bars, %d days' % (len(rows), len(set(r['day'] for r in rows))))

for key, lab in (('mag', 'MAG_SCORE'), ('rng', 'MAG_ALT_RNG'), ('vol', 'MAG_ALT_VOL')):
    use = [r for r in rows if r[key] is not None]
    byday = collections.defaultdict(list)
    for r in use:
        byday[r['day']].append(r)
    days = sorted(byday)
    dx = [statistics.median([r[key] for r in byday[d]]) for d in days]
    dy = [statistics.median([r['abs30'] for r in byday[d]]) for d in days]
    obs = spearman(dx, dy)
    rnd = random.Random(M.SEED); cnt = 0; N = 20000
    for _ in range(N):
        p = dy[:]; rnd.shuffle(p)
        if abs(spearman(dx, p)) >= abs(obs):
            cnt += 1
    print('  %-12s day-level Spearman %+0.4f  perm p %.5f  (%d days)'
          % (lab, obs, (cnt + 1.0) / (N + 1.0), len(days)))
    hi = [(r['day'], r['abs30']) for r in use if bucket(r[key]) == 'HIGH']
    lo = [(r['day'], r['abs30']) for r in use if bucket(r[key]) == 'LOW']
    d = [(a, b_) for a, b_ in hi] 
    ch, cl = day_boot_ci(hi), day_boot_ci(lo)
    print('       HIGH-LOW mean |ret|@30m  %+.2f   HIGH CI [%.2f,%.2f]  LOW CI [%.2f,%.2f]'
          % (sum(v for _, v in hi)/len(hi) - sum(v for _, v in lo)/len(lo),
             ch[0], ch[1], cl[0], cl[1]))
