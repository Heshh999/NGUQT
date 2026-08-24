#!/usr/bin/env python3
# ======================================================================
# MAG-H3 - does MAG_SCORE predict FUTURE ABSOLUTE MOVEMENT?
# ======================================================================
# Runs FIRST and gates the rest of the family. No direction, no P&L.
# Frozen by docs/MAG_PREREGISTRATION.md (c9c4bfe).
# ======================================================================

import os, sys, math, random, statistics, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
import mag_lib as M
import cand_spec as CS

T1, T2 = 1.270, 2.335            # frozen U terciles
HOR = (5, 10, 15, 30, 60)


def bucket(v, t1=T1, t2=T2):
    if v is None:
        return None
    return 'LOW' if v < t1 else ('MEDIUM' if v <= t2 else 'HIGH')


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (dx * dy) if dx and dy else float('nan')


def day_perm_p(days, xs, ys, obs, iters=2000, seed=M.SEED):
    """Day-clustered permutation: shuffle whole DAYS of the predictor
    against the outcome, preserving within-day clustering. This is the
    correct null for a NON-directional association - a sign-flip null
    would be meaningless here because nothing has a sign."""
    rnd = random.Random(seed)
    byday = collections.defaultdict(list)
    for d, x, y in zip(days, xs, ys):
        byday[d].append((x, y))
    dl = sorted(byday)
    cnt = 0
    for _ in range(iters):
        perm = dl[:]
        rnd.shuffle(perm)
        X, Y = [], []
        for src, dst in zip(dl, perm):
            a = byday[src]
            b = byday[dst]
            n = min(len(a), len(b))
            X.extend(a[i][0] for i in range(n))
            Y.extend(b[i][1] for i in range(n))
        if abs(spearman(X, Y)) >= abs(obs):
            cnt += 1
    return (cnt + 1.0) / (iters + 1.0)


def day_boot_ci(pairs, iters=20000, seed=M.SEED):
    rnd = random.Random(seed)
    byday = collections.defaultdict(list)
    for d, v in pairs:
        byday[d].append(v)
    days = sorted(byday)
    ms = []
    for _ in range(iters):
        vals = []
        for _ in days:
            vals.extend(byday[days[rnd.randrange(len(days))]])
        ms.append(sum(vals) / len(vals))
    ms.sort()
    return ms[int(0.025 * len(ms))], ms[int(0.975 * len(ms))]


if __name__ == '__main__':
    B = CS.load_merged()
    M.build_features(B)
    EV, SIGS, CTX = CS.generate(B)
    assert len(B) == 355455 and len(SIGS) == 952 and len(EV['OFH13']) == 133
    print('canonical reproduction PASS\n')

    rows = []
    for j, b in enumerate(B):
        if not M.eligible(b) or b['mag'] is None:
            continue
        if not M.consec(B, j, 60):
            continue
        px = b['close']
        hi = lo = px
        rec = {'mag': b['mag'], 'alt_vol': b['mag_vol'], 'alt_rng': b['mag_rng'],
               'day': b['day'], 'part': M.part(b['day']), 'atr': b['atr']}
        mfe = mae = 0.0
        sq = 0.0
        prev = px
        for k in range(1, 61):
            c = B[j + k]
            hi = max(hi, c['high'])
            lo = min(lo, c['low'])
            mfe = max(mfe, c['high'] - px)
            mae = max(mae, px - c['low'])
            sq += (c['close'] - prev) ** 2
            prev = c['close']
            if k in HOR:
                rec['abs%d' % k] = abs(c['close'] - px)
                rec['rng%d' % k] = hi - lo
                rec['exc%d' % k] = mfe + mae
                rec['rv%d' % k] = math.sqrt(sq)
        rows.append(rec)
    print('MAG-H3 universe: %d eligible bars with full 60m forward window\n'
          % len(rows))

    for score, label in (('mag', 'MAG_SCORE (primary)'),
                         ('alt_rng', 'MAG_ALT_RNG (skeptical benchmark)'),
                         ('alt_vol', 'MAG_ALT_VOL (diagnostic)')):
        use = [r for r in rows if r[score] is not None]
        print('=' * 74)
        print('%s   n=%d' % (label, len(use)))
        by = collections.defaultdict(list)
        for r in use:
            by[bucket(r[score])].append(r)
        print('  %-7s %6s | %s' % ('bucket', 'n', '  '.join(
            '%5dm |ret| rng exc' % h for h in HOR)))
        for bk in ('LOW', 'MEDIUM', 'HIGH'):
            g = by[bk]
            if not g:
                continue
            cells = []
            for h in HOR:
                cells.append('%5.1f %5.1f %5.1f' % (
                    statistics.median([x['abs%d' % h] for x in g]),
                    statistics.median([x['rng%d' % h] for x in g]),
                    statistics.median([x['exc%d' % h] for x in g])))
            print('  %-7s %6d | %s' % (bk, len(g), '  '.join(cells)))
        mono = []
        for h in HOR:
            v = [statistics.median([x['abs%d' % h] for x in by[k]])
                 for k in ('LOW', 'MEDIUM', 'HIGH') if by[k]]
            mono.append(v == sorted(v))
        print('  monotone LOW<MED<HIGH in median |ret| at %d of %d horizons'
              % (sum(mono), len(mono)))
        for h in (30,):
            sp = spearman([r[score] for r in use], [r['abs%d' % h] for r in use])
            print('  Spearman(%s, |ret|@%dm) = %+.4f' % (score, h, sp))
            sp2 = spearman([r[score] for r in use], [r['rng%d' % h] for r in use])
            print('  Spearman(%s,  range@%dm) = %+.4f' % (score, h, sp2))
        hl = [(r['day'], r['abs30']) for r in use if bucket(r[score]) == 'HIGH']
        ll = [(r['day'], r['abs30']) for r in use if bucket(r[score]) == 'LOW']
        chi, clo = day_boot_ci(hl), day_boot_ci(ll)
        print('  mean |ret|@30m  HIGH %.2f CI [%.2f, %.2f]   LOW %.2f CI [%.2f, %.2f]'
              % (sum(v for _, v in hl) / len(hl), chi[0], chi[1],
                 sum(v for _, v in ll) / len(ll), clo[0], clo[1]))
        for p in ('U', 'DEV', 'IR'):
            g = [r for r in use if r['part'] == p]
            if not g:
                continue
            bb = collections.defaultdict(list)
            for r in g:
                bb[bucket(r[score])].append(r['abs30'])
            print('    %-4s ' % p + '  '.join(
                '%s %5.2f' % (k, statistics.median(bb[k]))
                for k in ('LOW', 'MEDIUM', 'HIGH') if bb[k]))
        print()

    use = [r for r in rows if r['mag'] is not None]
    obs = spearman([r['mag'] for r in use], [r['abs30'] for r in use])
    p = day_perm_p([r['day'] for r in use], [r['mag'] for r in use],
                   [r['abs30'] for r in use], obs, iters=2000)
    print('=' * 74)
    print('DAY-CLUSTERED PERMUTATION on Spearman(MAG_SCORE, |ret|@30m)')
    print('  observed %+.4f   p = %.4f' % (obs, p))
