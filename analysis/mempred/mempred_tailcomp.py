#!/usr/bin/env python3
# ======================================================================
# MEMORY-PRED-V1 - SUPPLEMENTARY TAIL-COMPOSITION DIAGNOSTIC
# ======================================================================
# Reports the COMPOSITION of the pooled tail trims already printed by
# mempred_run.py. It computes NO new endpoint, tests NO new hypothesis
# and changes NO gate: the MP10 gate is the within-state trim, which is
# already decided. This exists so the pooled figure can be interpreted
# honestly rather than left ambiguous.
# SUBMITS NO ORDERS. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, math, collections
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../rvmr'))
import rvmr_spec as RS
import rvmr_run as RV


def mean(x):
    return sum(x) / len(x) if x else float('nan')


def main():
    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    N = len(D['c'])
    h, l, c, em = D['h'], D['l'], D['c'], D['em']
    rr = RS.trailing_ratio([h[i] - l[i] for i in range(N)])
    RB = [RS.bucket(x) if x is not None else None for x in rr]
    mem = array('d'); st = array('b')
    for t in range(1, N - 1):
        if em[t] - em[t - 1] != 1 or em[t + 1] - em[t] != 1:
            continue
        if c[t - 1] <= 0 or c[t] <= 0 or c[t + 1] <= 0:
            continue
        rt = math.log(c[t] / c[t - 1])
        if rt == 0.0:
            continue
        bt, bn = RB[t], RB[t + 1]
        if bt is None or bn is None or bt != bn:
            continue
        if bt == 'MEDIUM':
            continue
        rn = math.log(c[t + 1] / c[t])
        mem.append(rn if rt > 0 else -rn)
        st.append(2 if bt == 'HIGH' else 0)
    n = len(mem)
    H = [i for i in range(n) if st[i] == 2]
    L = [i for i in range(n) if st[i] == 0]
    print('=' * 78)
    print('MEMORY-PRED-V1  POOLED-TRIM COMPOSITION (diagnostic only)')
    print('=' * 78)
    print('  HIGH u LOW population %d   (HIGH %d, LOW %d)' % (n, len(H), len(L)))
    order = sorted(range(n), key=lambda i: abs(mem[i]), reverse=True)
    for frac in (0.01, 0.05):
        k = max(1, int(round(frac * n)))
        cut = set(order[:k])
        remH = sum(1 for i in H if i in cut)
        remL = k - remH
        keepH = len(H) - remH
        keepL = len(L) - remL
        dd = (mean([mem[i] for i in H if i not in cut])
              - mean([mem[i] for i in L if i not in cut]))
        print('\n  POOLED trim top %4.1f%%  (%d events removed)'
              % (frac * 100, k))
        print('    removed from HIGH %7d  = %5.1f%% of all HIGH events'
              % (remH, 100.0 * remH / len(H)))
        print('    removed from LOW  %7d  = %5.1f%% of all LOW events'
              % (remL, 100.0 * remL / len(L)))
        print('    surviving HIGH %7d   surviving LOW %8d' % (keepH, keepL))
        print('    DELTA after pooled trim  %+0.5f bp' % (dd * 1e4))
    print('\n  For comparison, the WITHIN-STATE trim (the MP10 gate)'
          ' removes the same')
    print('  PERCENTAGE from each state, so both samples stay intact.')
    print('=' * 78)


if __name__ == '__main__':
    main()
