#!/usr/bin/env python3
# ======================================================================
# BRK-V1 promotion gate - conditions 3 and 4
# ======================================================================
# The pre-registration declares FOUR promotion conditions. brk_run.py
# reports (1) BH q and (2) the day-clustered CI. This file reports the
# two that actually decided BRK-V1:
#
#   3. sign STABLE across U / DEV / IR
#   4. NOT tail-dominated
#
# A cell clearing only q and the CI is NOT promoted.
# ======================================================================

import os, sys, collections, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
import brk_run as K
import cand_spec as CS


def gate(pairs, rows, ctl, label):
    print('\n%s' % label)
    print('  CONDITION 3 - sign stability of the paired delta')
    byp = collections.defaultdict(list)
    for d, v in pairs:
        byp[K.part(d)].append((d, v))
    signs = []
    for p in ('U', 'DEV', 'IR'):
        v = byp[p]
        if not v:
            continue
        vals = [x[1] for x in v]
        lo, hi = K.day_boot_ci(v, iters=8000)
        pv = K.signflip_p(v, iters=8000)
        signs.append(1 if K.mean(vals) > 0 else -1)
        print('    %-4s n %3d  mean %+7.2f  CI [%+.2f, %+.2f]  p %.4f'
              % (p, len(v), K.mean(vals), lo, hi, pv))
    c3 = len(set(signs)) == 1
    print('    -> %s' % ('STABLE' if c3 else
                         'NOT STABLE - the effect does not hold in every era'))

    print('  CONDITION 4 - tail domination of the paired delta')
    s = sorted([v for _, v in pairs], reverse=True)
    base = K.mean(s)
    c4 = True
    for cut in (0.01, 0.05, 0.10):
        n = max(1, int(cut * len(s)))
        m = K.mean(s[n:])
        if m <= 0:
            c4 = False
        print('    drop top %4.1f%% (%3d of %d) -> mean %+7.2f'
              % (100 * cut, n, len(s), m))
    print('    -> %s' % ('ROBUST' if c4 else
                         'TAIL-DOMINATED - a handful of trades carry it all'))

    print('  DIAGNOSTIC - is the effect in the signal or in the control?')
    for nm, rr in (('signal', rows), ('control', ctl)):
        pp = collections.defaultdict(list)
        for r in rr:
            pp[r['part']].append(r['net'])
        print('    %-8s ' % nm + '  '.join(
            '%s %+8.2f' % (p, K.mean(pp[p])) for p in ('U', 'DEV', 'IR') if pp[p]))
    print('\n  PROMOTION: %s' % ('PASS' if (c3 and c4) else
                                 'FAILED - NOT PROMOTED'))
    return c3, c4


if __name__ == '__main__':
    B = CS.load_merged()
    EV, SIGS, CTX = CS.generate(B)
    rows, ctl, pairs, amb, unm = K.brk_h1(B, SIGS)
    gate(pairs, rows, ctl, 'BRK-H1  magnitude-event bracket')
