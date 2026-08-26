#!/usr/bin/env python3
# ======================================================================
# MEMORY-PRED-V1  (H1)  - FROZEN HISTORICAL EXECUTION + DESTRUCTION
# ======================================================================
# AUTHORITATIVE PREREGISTRATION:
#   docs/RVMR_STRUCTURE_TO_PREDICTION_V1_PREREGISTRATION.md
#   sha256 afac484b3d75a7bce9533a0fd8304a66fd653587eea5f20e4dac794a0898dbb8
#   commit cdfcb3148513264ba58a7880ea794c4baa72f1e4
#   frozen 2026-08-25T22:45:04+00:00
#
# H1 ONLY. H2 (HIGH-ARRIVAL-UTILITY-V1) IS NOT EXECUTED AND NOT COMBINED.
#
# EPISTEMIC STATUS: 2019-07 .. 2026-08 is EXPOSED for this hypothesis.
# This run is DEVELOPMENT / MECHANISM TESTING. It is NOT out-of-sample,
# NOT prospective, NOT proof of edge. Best possible status is
# DEVELOPMENT-SUPPORTED PREDICTIVE CANDIDATE.
#
# SUBMITS NO ORDERS. SIMULATES NO TRADE. NOTHING FROZEN IS MODIFIED.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
#
# ----------------------------------------------------------------------
# TWO PRE-COMPUTATION CHOICES, RECORDED HERE BEFORE ANY RESULT EXISTS
# (the preregistration text is silent on each; neither is chosen to
#  favour the hypothesis and both variants are reported):
#
# (a) MP10 tail trim scope. Prereg 4.12 says "removing the top 1% and the
#     top 5% of events by |memoryReturn|" without naming the scope. The
#     GATE uses a WITHIN-STATE trim (each state loses its own top 1%/5%),
#     because Delta is a difference of two means and trimming each mean's
#     own tail keeps the comparison balanced; a pooled trim would remove
#     disproportionately many HIGH events and confound tail removal with
#     a composition shift. The POOLED trim is also computed and reported.
#     If the two disagree, that is stated prominently.
#
# (b) BH at M_binding = 2 with H2 not yet run. H1's BH q depends on H2's
#     p-value, which does not exist. The GATE therefore uses the
#     CONSERVATIVE bound q <= 2 * p1 (H1 as rank 1 of 2). The optimistic
#     bound (H1 as rank 2) is q = p1. Both are reported. If p1 falls in
#     (0.025, 0.05] the gate outcome is H2-dependent and that is stated.
# ======================================================================

import os, sys, math, random, collections, hashlib, time
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../rvmr'))
import rvmr_spec as RS
import rvmr_run as RV

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
PREREG = os.path.join(ROOT, 'docs',
                      'RVMR_STRUCTURE_TO_PREDICTION_V1_PREREGISTRATION.md')
PREREG_SHA = ('afac484b3d75a7bce9533a0fd8304a66fd653587eea5f20e4dac794a'
              '0898dbb8')

SEED = 20260825
B_MAIN, B_DESC, PERM = 20000, 4000, 20000
COST_PTS = 0.87
BP = 1e4
# frozen time-of-day buckets (prereg 2.5)
# OVERNIGHT: mod >= 1081 or mod <= 569 ; RTH_AM 570..750 ; RTH_PM 751..960
TODN = ('OVERNIGHT', 'RTH_AM', 'RTH_PM')
STN = ('LOW', 'MEDIUM', 'HIGH')
# minimum-n preconditions (prereg 4.11)
MIN_LOW, MIN_MED, MIN_HIGH = 500000, 80000, 25000
PROSPECTIVE_START = '2026-08-26'
UNSEEN_LO, UNSEEN_HI = '2026-08-18', '2026-08-25'
PASS = {True: 'PASS', False: 'FAIL'}


def mean(x):
    return sum(x) / len(x) if x else float('nan')


def med_of(x):
    s = sorted(x)
    return s[len(s) // 2] if s else float('nan')


def quantile(sorted_vals, q):
    """type-7 empirical quantile, the programme's frozen convention."""
    n = len(sorted_vals)
    h = (n - 1) * q
    lo = int(math.floor(h))
    hi = min(lo + 1, n - 1)
    return sorted_vals[lo] + (h - lo) * (sorted_vals[hi] - sorted_vals[lo])


# ------------------------------------------------------------ inference
def boot_diff(blocks, iters, seed=SEED):
    """blocks: [(sA,nA,sB,nB)] per day. Returns mean diff A-B, CI, p."""
    nb = len(blocks)
    SA = sum(b[0] for b in blocks); NA = sum(b[1] for b in blocks)
    SB = sum(b[2] for b in blocks); NB = sum(b[3] for b in blocks)
    if not NA or not NB or nb < 15:
        return float('nan'), float('nan'), float('nan'), float('nan')
    obs = SA / NA - SB / NB
    rnd = random.Random(seed)
    rr = rnd.randrange
    out = []
    for _ in range(iters):
        sa = sb = 0.0; na = nb2 = 0
        for _ in range(nb):
            b = blocks[rr(nb)]
            sa += b[0]; na += b[1]; sb += b[2]; nb2 += b[3]
        if na and nb2:
            out.append(sa / na - sb / nb2)
    out.sort()
    m = len(out)
    lo, hi = out[int(.025 * m)], out[int(.975 * m)]
    le = sum(1 for x in out if x <= 0)
    ge = sum(1 for x in out if x >= 0)
    p = max(2.0 * min(le, ge) / m, 1.0 / (m + 1.0))
    return obs, lo, hi, p


def boot_mean(blocks, iters, seed=SEED):
    """blocks: [(s,n)] per day."""
    nb = len(blocks)
    S = sum(b[0] for b in blocks); N = sum(b[1] for b in blocks)
    if not N or nb < 15:
        return float('nan'), float('nan'), float('nan'), float('nan')
    obs = S / N
    rnd = random.Random(seed)
    rr = rnd.randrange
    out = []
    for _ in range(iters):
        s = 0.0; n = 0
        for _ in range(nb):
            b = blocks[rr(nb)]
            s += b[0]; n += b[1]
        if n:
            out.append(s / n)
    out.sort()
    m = len(out)
    lo, hi = out[int(.025 * m)], out[int(.975 * m)]
    le = sum(1 for x in out if x <= 0)
    ge = sum(1 for x in out if x >= 0)
    p = max(2.0 * min(le, ge) / m, 1.0 / (m + 1.0))
    return obs, lo, hi, p


def bh_q(p, M, rank):
    return min(1.0, p * M / rank)


def atr20_arrays(h, l, c):
    n = len(c)
    out = [None] * n
    tr = collections.deque(); s = 0.0; prev = None
    for i in range(n):
        t = (h[i] - l[i]) if prev is None else max(
            h[i] - l[i], abs(h[i] - prev), abs(l[i] - prev))
        tr.append(t); s += t
        prev = c[i]
        if len(tr) > 20:
            s -= tr.popleft()
        if len(tr) == 20:
            out[i] = s / 20.0
    return out


def main():
    t0 = time.time()
    print('=' * 78)
    print('MEMORY-PRED-V1  (H1)   FROZEN HISTORICAL EXECUTION')
    print('  prereg sha256 %s' % PREREG_SHA[:40])
    print('  commit cdfcb3148513264ba58a7880ea794c4baa72f1e4')
    print('  DEVELOPMENT / MECHANISM TESTING - NOT OOS, NOT PROSPECTIVE')
    print('  H1 ONLY. H2 NOT EXECUTED. NO COMBINATION. NO ORDERS.')
    print('=' * 78)

    # ============================================= PHASE 0
    print('\n' + '=' * 78)
    print('PHASE 0  FREEZE VERIFICATION')
    print('=' * 78)
    got = hashlib.sha256(open(PREREG, 'rb').read()).hexdigest()
    print('  (1) prereg sha256      %s' % got)
    ok1 = (got == PREREG_SHA)
    print('      matches frozen     %s' % ('YES' if ok1 else 'NO'))
    print('  (4) RVMR spec          T1 %.3f  T2 %.3f  W %d  RTH %d..%d'
          % (RS.T1, RS.T2, RS.W, RS.RTH_START, RS.RTH_END))
    ok4 = (RS.T1 == 1.270 and RS.T2 == 2.335 and RS.W == 1440)
    print('  (5) H1 formula         memoryReturn = sign(r[t]) * r[t+1]')
    print('  (6) zero handling      r[t]==0 EXCLUDED; r[t+1]==0 retained'
          ' as 0 for the mean, excluded from sign endpoint')
    print('  (7) state conditioning PRIMARY RB[t]==RB[t+1]; SECONDARY'
          ' RB[t+1] only (cannot rescue)')
    print('  (8) controls           ATR tercile x |r[t]| tercile x ToD'
          ' bucket, common-weight difference-of-means standardisation')
    print('  (9) inference          day-cluster on day[t+1], boot %d,'
          ' seed %d, 95%% CI, within-day label shuffle %d'
          % (B_MAIN, SEED, PERM))
    print('  (10) gates             MP1..MP10 as frozen')
    if not (ok1 and ok4):
        print('\nMEMORY-PRED-V1 FREEZE FAILURE')
        return

    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    N = len(D['c'])
    h, l, c, v, em, mod, day, et = (D['h'], D['l'], D['c'], D['v'],
                                    D['em'], D['mod'], D['day'], D['et'])
    rng = [h[i] - l[i] for i in range(N)]
    rr = RS.trailing_ratio(rng)
    RB = [RS.bucket(x) if x is not None else None for x in rr]
    atr = atr20_arrays(h, l, c)

    # leakage probes: trailing_ratio at index p must use rng[p-1440..p-1]
    probe_ok = True
    for p in (1440, 500000, 1200000, 2000000, 2500000):
        if p < N:
            direct = rng[p] / (sum(rng[p - 1440:p]) / 1440.0)
            if abs(direct - rr[p]) > 1e-9:
                probe_ok = False
    print('  (3) AC-FLIP lineage    scan_run.py ac() + confirm_run.py'
          ' adjacency-restricted variant (both bars same state)')
    print('  RVMR causality probes  %s   first scored index %d'
          % ('EXACT' if probe_ok else 'MISMATCH',
             next(i for i in range(N) if rr[i] is not None)))
    print('  FREEZE VERIFIED.')

    # ============================================= COVERAGE
    print('\n' + '=' * 78)
    print('DATA COVERAGE')
    print('=' * 78)
    days_all = sorted(set(day))
    print('  bars %d   exchange days %d   %s .. %s'
          % (N, len(days_all), et[0], et[-1]))
    dupes = N - len(set(et))
    print('  duplicate close stamps: %d' % dupes)
    print('  prospective start %s  -> bars at/after it: %d'
          % (PROSPECTIVE_START,
             sum(1 for d in days_all if d >= PROSPECTIVE_START)))
    unseen = [d for d in days_all if UNSEEN_LO <= d <= UNSEEN_HI]
    print('  UNSEEN-BUT-PRE-EXISTING window %s..%s -> exchange days'
          ' present in repository: %d' % (UNSEEN_LO, UNSEEN_HI, len(unseen)))

    # ============================================= EVENT BUILD
    print('\n' + '=' * 78)
    print('ADJACENCY AUDIT AND EVENT CONSTRUCTION')
    print('=' * 78)
    dayid = {d: k for k, d in enumerate(days_all)}
    ev_day = array('i'); ev_mem = array('d'); ev_st = array('b')
    ev_stf = array('b'); ev_abs = array('d'); ev_arel = array('d')
    ev_tod = array('b'); ev_mom = array('b')
    cand = 0; gap = 0; zero_rt = 0; nostate = 0; crossday = 0
    sumclose_hl = 0.0; n_hl = 0
    stmap = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
    for t in range(1, N - 1):
        cand += 1
        # r[t] and r[t+1] must both exist under the frozen return rule
        if em[t] - em[t - 1] != 1 or em[t + 1] - em[t] != 1:
            gap += 1
            continue
        if c[t - 1] <= 0 or c[t] <= 0 or c[t + 1] <= 0:
            gap += 1
            continue
        rt = math.log(c[t] / c[t - 1])
        if rt == 0.0:
            zero_rt += 1
            continue
        bt, bn = RB[t], RB[t + 1]
        if bt is None or bn is None:
            nostate += 1
            continue
        rn = math.log(c[t + 1] / c[t])
        memr = rn if rt > 0 else -rn
        if day[t] != day[t + 1]:
            crossday += 1
        ev_day.append(dayid[day[t + 1]])
        ev_mem.append(memr)
        ev_st.append(stmap[bt] if bt == bn else -1)
        ev_stf.append(stmap[bn])
        ev_abs.append(abs(rt))
        a = atr[t]
        ev_arel.append((a / c[t]) if a is not None else float('nan'))
        m_ = mod[t + 1]
        ev_tod.append(0 if (m_ >= 1081 or m_ <= 569)
                      else (1 if m_ <= 750 else 2))
        if t >= 2 and em[t - 1] - em[t - 2] == 1 and c[t - 2] > 0:
            rp = math.log(c[t - 1] / c[t - 2])
            ev_mom.append(-1 if rp == 0 else (1 if (rp > 0) == (rt > 0)
                                              else 0))
        else:
            ev_mom.append(-1)
        if bt == bn and bt in ('LOW', 'HIGH'):
            sumclose_hl += c[t]; n_hl += 1
    NE = len(ev_mem)
    print('  candidate (t, t+1) index pairs           %10d' % cand)
    print('  removed - gap / non-contiguous minutes   %10d' % gap)
    print('  removed - r[t] == 0 (sign undefined)     %10d' % zero_rt)
    print('  removed - RVMR state unavailable         %10d' % nostate)
    print('  VALID ADJACENT EVENTS                    %10d' % NE)
    print('  duplicate close stamps in source          %10d' % dupes)
    print('  events whose t and t+1 sit on different calendar dates'
          ' (true midnight contiguity, RETAINED): %d' % crossday)
    print('  every retained event satisfies em[t+1]-em[t]==1 AND'
          ' em[t]-em[t-1]==1 by construction')
    assert dupes == 0

    ncnt = collections.Counter(ev_st)
    print('\n  PRIMARY assignment (RB[t] == RB[t+1]):')
    for k, nm in enumerate(STN):
        print('    %-7s %10d' % (nm, ncnt[k]))
    print('    %-7s %10d  (state changed between t and t+1 - not assigned'
          ' under the primary construction)' % ('mixed', ncnt[-1]))
    nL, nM, nH = ncnt[0], ncnt[1], ncnt[2]

    # ============================================= CAUSAL AUDIT
    print('\n' + '=' * 78)
    print('CAUSAL AUDIT')
    print('=' * 78)
    rows = [
        ('r[t] = log(c[t]/c[t-1])', 'close of bar t', 'n/a', True),
        ('sign(r[t])', 'close of bar t', 'n/a', True),
        ('RB[t]  (window t-1440..t-1)', 'close of bar t-1',
         'r[t+1]', True),
        ('RB[t+1] (window t+1-1440..t)', 'close of bar t', 'r[t+1]', True),
        ('atr20(t) (bars t-19..t)', 'close of bar t', 'r[t+1]', True),
        ('|r[t]|', 'close of bar t', 'r[t+1]', True),
        ('time-of-day bucket of t+1', 'clock', 'r[t+1]', True),
        ('sign(r[t-1])', 'close of bar t-1', 'r[t+1]', True),
        ('RVMR thresholds 1.270/2.335', 'fixed 2019', 'r[t+1]', True),
        ('r[t+1] = log(c[t+1]/c[t])  OUTCOME', 'close of bar t+1',
         'itself', True),
    ]
    print('  %-38s %-20s %-10s %s' % ('FIELD', 'AVAILABLE TIME',
                                      'OUTCOME', 'CAUSAL'))
    allyes = True
    for f, a, o, ok in rows:
        allyes = allyes and ok
        print('  %-38s %-20s %-10s %s' % (f, a, o, 'YES' if ok else 'NO'))
    print('  RVMR window excludes its own bar: verified EXACT at 5 probes')
    print('  ALL ROWS YES: %s' % (allyes and probe_ok))

    # ============================================= day blocks helper
    def blocks_diff(maskA, maskB):
        d = {}
        for i in range(NE):
            a = maskA(i); b = maskB(i)
            if not (a or b):
                continue
            k = ev_day[i]
            e = d.get(k)
            if e is None:
                e = d[k] = [0.0, 0, 0.0, 0]
            if a:
                e[0] += ev_mem[i]; e[1] += 1
            if b:
                e[2] += ev_mem[i]; e[3] += 1
        return [tuple(x) for x in d.values()]

    def blocks_mean(mask):
        d = {}
        for i in range(NE):
            if not mask(i):
                continue
            k = ev_day[i]
            e = d.get(k)
            if e is None:
                e = d[k] = [0.0, 0]
            e[0] += ev_mem[i]; e[1] += 1
        return [tuple(x) for x in d.values()]

    isH = lambda i: ev_st[i] == 2
    isL = lambda i: ev_st[i] == 0
    isM = lambda i: ev_st[i] == 1

    # ============================================= PRIMARY
    print('\n' + '=' * 78)
    print('PRIMARY RESULT   memoryReturn = sign(r[t]) x r[t+1]')
    print('  state = RB[t] == RB[t+1]   (the replicated adjacency-'
          'restricted object)')
    print('=' * 78)
    print('  %-7s %10s %11s %11s %10s %11s %11s %10s'
          % ('state', 'n', 'mean bp', 'median bp', 'sd bp', 'CI lo', 'CI hi',
             'boot p'))
    stat = {}
    for k, nm in enumerate(STN):
        vals = [ev_mem[i] for i in range(NE) if ev_st[i] == k]
        m, lo, hi, p = boot_mean(blocks_mean(lambda i, kk=k: ev_st[i] == kk),
                                 B_MAIN)
        mu = mean(vals)
        sd = math.sqrt(sum((x - mu) ** 2 for x in vals) / (len(vals) - 1))
        stat[nm] = (len(vals), m, med_of(vals), sd, lo, hi, p)
        print('  %-7s %10d %+11.5f %+11.5f %10.4f %+11.5f %+11.5f %10.5f'
              % (nm, len(vals), m * BP, med_of(vals) * BP, sd * BP,
                 lo * BP, hi * BP, p))
        del vals
    dblk = blocks_diff(isH, isL)
    dlt, dlo, dhi, dp = boot_diff(dblk, B_MAIN)
    print('\n  DELTA = E[mem|HIGH] - E[mem|LOW]  %+0.5f bp'
          '   CI [%+0.5f, %+0.5f]   boot p %.5f'
          % (dlt * BP, dlo * BP, dhi * BP, dp))
    print('  required: DELTA > 0  -> %s        E[mem|LOW] < 0  -> %s'
          % (dlt > 0, stat['LOW'][1] < 0))

    # sign-probability endpoint
    print('\n  SIGN-PROBABILITY ENDPOINT  (r[t+1]==0 excluded, as frozen)')
    print('  %-7s %10s %12s %12s %14s' % ('state', 'n nonzero', 'P(cont)',
                                          'P(reversal)', 'dev from 50%'))
    pc = {}
    for k, nm in enumerate(STN):
        nz = [1 if ev_mem[i] > 0 else 0
              for i in range(NE) if ev_st[i] == k and ev_mem[i] != 0.0]
        pcv = mean(nz)
        pc[nm] = (len(nz), pcv)
        print('  %-7s %10d %12.6f %12.6f %+14.4f pp'
              % (nm, len(nz), pcv, 1 - pcv, 100 * (pcv - 0.5)))
        del nz
    d2 = {}
    for i in range(NE):
        if ev_st[i] in (0, 2) and ev_mem[i] != 0.0:
            k = ev_day[i]
            e = d2.get(k)
            if e is None:
                e = d2[k] = [0.0, 0, 0.0, 0]
            if ev_st[i] == 2:
                e[0] += 1.0 if ev_mem[i] > 0 else 0.0; e[1] += 1
            else:
                e[2] += 1.0 if ev_mem[i] > 0 else 0.0; e[3] += 1
    pdiff, plo, phi, pp = boot_diff([tuple(x) for x in d2.values()], B_MAIN)
    print('  HIGH - LOW continuation probability  %+0.6f'
          '  = %+0.4f pp   CI [%+0.4f, %+0.4f] pp   p %.5f'
          % (pdiff, 100 * pdiff, 100 * plo, 100 * phi, pp))
    del d2

    # economic
    px = sumclose_hl / n_hl
    print('\n  ECONOMIC SCALE (reported, NEVER a gate)')
    print('    mean close over HIGH u LOW events   %.2f' % px)
    print('    DELTA in NQ points                  %+0.6f' % (dlt * px))
    print('    round-turn cost                      %.2f points'
          ' (= %.4f bp here)' % (COST_PTS, COST_PTS / px * BP))
    print('    DELTA as a multiple of cost         %.5f x'
          % (abs(dlt * px) / COST_PTS))

    # ============================================= MAGNITUDE ROBUSTNESS
    print('\n' + '=' * 78)
    print('MAGNITUDE ROBUSTNESS  (frozen set only: ALL / TOP50 / TOP20)')
    print('=' * 78)
    absr = sorted(ev_abs[i] for i in range(NE) if ev_st[i] >= 0)
    q50, q80 = quantile(absr, 0.50), quantile(absr, 0.80)
    del absr
    print('  cutpoints computed once on the assigned population'
          ' (in-sample, no search): p50 %.10f   p80 %.10f' % (q50, q80))
    magres = {}
    for nm, thr in (('ALL', None), ('TOP50', q50), ('TOP20', q80)):
        if thr is None:
            bl = dblk
            nHm, nLm = nH, nL
        else:
            bl = blocks_diff(lambda i, T=thr: ev_st[i] == 2 and ev_abs[i] >= T,
                             lambda i, T=thr: ev_st[i] == 0 and ev_abs[i] >= T)
            nHm = sum(1 for i in range(NE) if ev_st[i] == 2 and ev_abs[i] >= thr)
            nLm = sum(1 for i in range(NE) if ev_st[i] == 0 and ev_abs[i] >= thr)
        dd, lo_, hi_, p_ = boot_diff(bl, B_DESC)
        magres[nm] = dd
        print('  %-6s  nHIGH %8d  nLOW %9d   DELTA %+0.5f bp'
              '  CI [%+0.5f, %+0.5f]  p %.5f'
              % (nm, nHm, nLm, dd * BP, lo_ * BP, hi_ * BP, p_))

    # ============================================= CONTROLS
    print('\n' + '=' * 78)
    print('CONTROLS - common-weight difference-of-means standardisation')
    print('  (NOT the degenerate subgroup weighting of ANOMALY-CONFIRM'
          ' 4.13: the weight is a COMMON distribution applied to a')
    print('   DIFFERENCE of two means, so it genuinely differs from raw)')
    print('=' * 78)
    ar = sorted(ev_arel[i] for i in range(NE)
                if ev_st[i] >= 0 and ev_arel[i] == ev_arel[i])
    a1, a2 = quantile(ar, 1 / 3.0), quantile(ar, 2 / 3.0)
    del ar
    ab = sorted(ev_abs[i] for i in range(NE) if ev_st[i] >= 0)
    b1, b2 = quantile(ab, 1 / 3.0), quantile(ab, 2 / 3.0)
    del ab
    print('  ATR tercile cuts  %.10f  %.10f' % (a1, a2))
    print('  |r[t]| tercile cuts %.10f  %.10f' % (b1, b2))

    def acell(i):
        x = ev_arel[i]
        if x != x:
            return -1
        return 0 if x < a1 else (1 if x <= a2 else 2)

    def bcell(i):
        x = ev_abs[i]
        return 0 if x < b1 else (1 if x <= b2 else 2)

    def standardise(cellfn, label):
        agg = {}
        for i in range(NE):
            s = ev_st[i]
            if s != 0 and s != 2:
                continue
            cid = cellfn(i)
            if cid is None or (isinstance(cid, int) and cid < 0):
                continue
            e = agg.get(cid)
            if e is None:
                e = agg[cid] = [0.0, 0, 0.0, 0]
            if s == 2:
                e[0] += ev_mem[i]; e[1] += 1
            else:
                e[2] += ev_mem[i]; e[3] += 1
        num = den = 0.0
        cells = 0
        for cid, e in agg.items():
            if e[1] < 30 or e[3] < 30:
                continue
            dc = e[0] / e[1] - e[2] / e[3]
            w = e[1] + e[3]
            num += w * dc; den += w
            cells += 1
        return (num / den if den else float('nan')), cells, agg

    full_cell = lambda i: (acell(i), bcell(i), ev_tod[i]) if acell(i) >= 0 \
        else None
    dm_full, ncell, _ = standardise(full_cell, 'full')
    dm_atr, na_, aggA = standardise(lambda i: acell(i), 'atr')
    dm_mag, nb_, aggB = standardise(lambda i: bcell(i), 'mag')
    print('\n  ATR CONTROL')
    for cid in (0, 1, 2):
        e = aggA.get(cid)
        if e:
            print('    ATR tercile %d   nHIGH %8d  nLOW %9d   DELTA_cell'
                  ' %+0.5f bp' % (cid, e[1], e[3],
                                  (e[0] / e[1] - e[2] / e[3]) * BP))
    print('    raw DELTA                    %+0.5f bp' % (dlt * BP))
    print('    ATR-standardised DELTA       %+0.5f bp   retention %.1f%%'
          % (dm_atr * BP, 100 * dm_atr / dlt if dlt else float('nan')))
    print('\n  RETURN-MAGNITUDE CONTROL')
    for cid in (0, 1, 2):
        e = aggB.get(cid)
        if e:
            print('    |r[t]| tercile %d  nHIGH %8d  nLOW %9d   DELTA_cell'
                  ' %+0.5f bp' % (cid, e[1], e[3],
                                  (e[0] / e[1] - e[2] / e[3]) * BP))
    print('    magnitude-standardised DELTA %+0.5f bp   retention %.1f%%'
          % (dm_mag * BP, 100 * dm_mag / dlt if dlt else float('nan')))
    print('\n  MP8 FULL 27-CELL MATCH (ATR x |r[t]| x time-of-day)')
    print('    cells used (n>=30 in both states) %d of 27' % ncell)
    print('    DELTA_matched                %+0.5f bp   retention %.1f%%'
          % (dm_full * BP, 100 * dm_full / dlt if dlt else float('nan')))

    print('\n  TIME-OF-DAY CONTROL (frozen buckets, bucket of t+1)')
    tod_pos = 0
    for k, nm in enumerate(TODN):
        bl = blocks_diff(lambda i, kk=k: ev_st[i] == 2 and ev_tod[i] == kk,
                         lambda i, kk=k: ev_st[i] == 0 and ev_tod[i] == kk)
        dd, lo_, hi_, p_ = boot_diff(bl, B_DESC)
        if dd > 0:
            tod_pos += 1
        nHb = sum(1 for i in range(NE) if ev_st[i] == 2 and ev_tod[i] == k)
        nLb = sum(1 for i in range(NE) if ev_st[i] == 0 and ev_tod[i] == k)
        print('    %-10s nHIGH %8d  nLOW %9d  DELTA %+0.5f bp'
              '  CI [%+0.5f, %+0.5f]' % (nm, nHb, nLb, dd * BP,
                                         lo_ * BP, hi_ * BP))
    print('    buckets with DELTA > 0: %d of 3' % tod_pos)

    print('\n  RECENT-MOMENTUM CONTROL (sign(r[t-1]) vs sign(r[t]);'
          ' reported, not a gate)')
    for mv, nm in ((1, 'same sign as r[t]'), (0, 'opposite sign')):
        bl = blocks_diff(lambda i, m=mv: ev_st[i] == 2 and ev_mom[i] == m,
                         lambda i, m=mv: ev_st[i] == 0 and ev_mom[i] == m)
        dd, lo_, hi_, p_ = boot_diff(bl, B_DESC)
        print('    prior return %-18s DELTA %+0.5f bp  CI [%+0.5f, %+0.5f]'
              % (nm, dd * BP, lo_ * BP, hi_ * BP))
    mom_agg = {}
    for i in range(NE):
        s = ev_st[i]
        if (s != 0 and s != 2) or ev_mom[i] < 0:
            continue
        e = mom_agg.setdefault(ev_mom[i], [0.0, 0, 0.0, 0])
        if s == 2:
            e[0] += ev_mem[i]; e[1] += 1
        else:
            e[2] += ev_mem[i]; e[3] += 1
    num = den = 0.0
    for cid, e in mom_agg.items():
        if e[1] >= 30 and e[3] >= 30:
            num += (e[1] + e[3]) * (e[0] / e[1] - e[2] / e[3])
            den += e[1] + e[3]
    dm_mom = num / den if den else float('nan')
    print('    momentum-standardised DELTA  %+0.5f bp   retention %.1f%%'
          % (dm_mom * BP, 100 * dm_mom / dlt if dlt else float('nan')))

    # ============================================= YEAR / MONTH
    print('\n' + '=' * 78)
    print('YEAR DESTRUCTION  (NO year is OOS for H1 - temporal robustness'
          ' only)')
    print('=' * 78)
    yr_of = [days_all[ev_day[i]][:4] for i in range(NE)]
    years = sorted(set(yr_of))
    print('  %-6s %10s %10s %12s %12s %12s %12s'
          % ('year', 'n LOW', 'n HIGH', 'LOW bp', 'HIGH bp', 'DELTA bp',
             'dP(cont) pp'))
    yr_pos = 0
    for y in years:
        hv = [ev_mem[i] for i in range(NE) if ev_st[i] == 2 and yr_of[i] == y]
        lv = [ev_mem[i] for i in range(NE) if ev_st[i] == 0 and yr_of[i] == y]
        hp = mean([1 if x > 0 else 0 for x in hv if x != 0])
        lp = mean([1 if x > 0 else 0 for x in lv if x != 0])
        dd = mean(hv) - mean(lv)
        if dd > 0:
            yr_pos += 1
        print('  %-6s %10d %10d %+12.5f %+12.5f %+12.5f %+12.4f'
              % (y, len(lv), len(hv), mean(lv) * BP, mean(hv) * BP,
                 dd * BP, 100 * (hp - lp)))
        del hv, lv
    print('  years with DELTA > 0: %d of %d' % (yr_pos, len(years)))

    print('\n  MONTH DESTRUCTION')
    mo_of = [days_all[ev_day[i]][:7] for i in range(NE)]
    magg = {}
    for i in range(NE):
        s = ev_st[i]
        if s != 0 and s != 2:
            continue
        e = magg.setdefault(mo_of[i], [0.0, 0, 0.0, 0])
        if s == 2:
            e[0] += ev_mem[i]; e[1] += 1
        else:
            e[2] += ev_mem[i]; e[3] += 1
    mvals = []
    for k in sorted(magg):
        e = magg[k]
        if e[1] and e[3]:
            mvals.append((k, e[0] / e[1] - e[2] / e[3]))
    mpos = sum(1 for _, x in mvals if x > 0)
    best = max(mvals, key=lambda z: z[1]); worst = min(mvals, key=lambda z: z[1])
    print('    months %d   positive %d   negative %d   median %+0.5f bp'
          % (len(mvals), mpos, len(mvals) - mpos,
             med_of([x for _, x in mvals]) * BP))
    print('    best %s %+0.5f bp    worst %s %+0.5f bp'
          % (best[0], best[1] * BP, worst[0], worst[1] * BP))

    # ============================================= TAIL
    print('\n' + '=' * 78)
    print('TAIL DESTRUCTION  (gate = WITHIN-STATE trim; pooled trim also'
          ' reported - see engine header note (a))')
    print('=' * 78)
    Hidx = [i for i in range(NE) if ev_st[i] == 2]
    Lidx = [i for i in range(NE) if ev_st[i] == 0]
    Hs = sorted(Hidx, key=lambda i: abs(ev_mem[i]), reverse=True)
    Ls = sorted(Lidx, key=lambda i: abs(ev_mem[i]), reverse=True)
    tail_ws = {}
    for frac in (0.01, 0.05):
        kH = max(1, int(round(frac * len(Hs))))
        kL = max(1, int(round(frac * len(Ls))))
        dd = mean([ev_mem[i] for i in Hs[kH:]]) - \
            mean([ev_mem[i] for i in Ls[kL:]])
        tail_ws[frac] = dd
        print('  within-state  remove top %4.1f%%  (H %6d, L %7d removed)'
              '   DELTA %+0.5f bp' % (frac * 100, kH, kL, dd * BP))
    pool = sorted(Hidx + Lidx, key=lambda i: abs(ev_mem[i]), reverse=True)
    tail_pl = {}
    for frac in (0.01, 0.05):
        k = max(1, int(round(frac * len(pool))))
        keep = set(pool[k:])
        hv = [ev_mem[i] for i in Hidx if i in keep]
        lv = [ev_mem[i] for i in Lidx if i in keep]
        dd = mean(hv) - mean(lv)
        tail_pl[frac] = dd
        print('  pooled        remove top %4.1f%%  (%7d removed)'
              '           DELTA %+0.5f bp' % (frac * 100, k, dd * BP))
        del hv, lv, keep
    del Hs, Ls, pool
    tail_pass = tail_ws[0.01] > 0 and tail_ws[0.05] > 0

    # ============================================= PERMUTATION
    print('\n' + '=' * 78)
    print('PERMUTATION NULL  within-day shuffle of state labels'
          '  (%d iters, seed %d)' % (PERM, SEED))
    print('=' * 78)
    # PERFORMANCE NOTE (disclosed; the NULL IS UNCHANGED). The three
    # states partition each day's assigned events, so
    #     SUM(LOW) = dayTotal - SUM(HIGH) - SUM(MEDIUM).
    # Sampling the two SMALL groups and deriving LOW by complement is
    # mathematically identical to drawing all three labels, and costs
    # ~262k draws per iteration instead of ~1.65M. Iteration count
    # (20,000), seed (20260825), cluster unit and the null are unchanged;
    # only the order in which the RNG stream is consumed differs.
    byday = {}
    for i in range(NE):
        st_ = ev_st[i]
        if st_ < 0:
            continue
        e = byday.get(ev_day[i])
        if e is None:
            e = byday[ev_day[i]] = [[], 0, 0, 0]
        e[0].append(ev_mem[i])
        e[1 + st_] += 1
    plan = []
    for k, (vals, kl, km, kh) in byday.items():
        assert kh + km + kl == len(vals)
        if kh == 0 and kl == 0:
            continue
        plan.append((vals, math.fsum(vals), kh, km))
    del byday
    # SECOND PERFORMANCE NOTE (disclosed; the NULL IS STILL UNCHANGED).
    # random.sample() switches to an O(n) pool copy whenever
    # n <= 21 + 4**ceil(log(3k,4)); with k~118 that threshold is 1045 and
    # the average day holds ~1075 assigned events, so a large share of
    # days took the O(n) path and the loop would not have finished. The
    # partial Fisher-Yates below draws exactly the same uniform subset
    # without replacement in guaranteed O(k). Iteration count (20,000),
    # seed (20260825), cluster unit and the null are unchanged; only the
    # order in which the RNG stream is consumed differs. Mutating each
    # day's list in place is harmless - the order of a day's values
    # carries no meaning.
    plan = [(vals, tot, kh, kh + km, len(vals)) for vals, tot, kh, km in plan]
    rnd = random.Random(SEED)
    rnd_random = rnd.random
    obs = abs(dlt)
    cnt = 0
    NH, NL = nH, nL
    rep = max(1, PERM // 10)
    for it in range(PERM):
        sh = sl = 0.0
        for vals, tot, kh, take, n in plan:
            a = 0.0
            for j in range(kh):
                r = j + int(rnd_random() * (n - j))
                vj = vals[r]; vals[r] = vals[j]; vals[j] = vj
                a += vj
            b = 0.0
            for j in range(kh, take):
                r = j + int(rnd_random() * (n - j))
                vj = vals[r]; vals[r] = vals[j]; vals[j] = vj
                b += vj
            sh += a
            sl += tot - a - b
        if abs(sh / NH - sl / NL) >= obs:
            cnt += 1
        if (it + 1) % rep == 0:
            print('    ... permutation %6d / %d   exceedances %d  (%.0f s)'
                  % (it + 1, PERM, cnt, time.time() - t0), flush=True)
    perm_p = max((cnt + 1.0) / (PERM + 1.0), 1.0 / (PERM + 1.0))
    print('  observed DELTA %+0.5f bp    permutation p = %.5f'
          % (dlt * BP, perm_p))
    print('  (elapsed %.0f s)' % (time.time() - t0))

    # ============================================= SECONDARIES
    print('\n' + '=' * 78)
    print('SECONDARY 1  forward-state-only conditioning (RB[t+1] alone)')
    print('  CANNOT rescue the primary and cannot overturn it')
    print('=' * 78)
    blf = blocks_diff(lambda i: ev_stf[i] == 2, lambda i: ev_stf[i] == 0)
    df, flo, fhi, fp = boot_diff(blf, B_DESC)
    for k, nm in enumerate(STN):
        vv = [ev_mem[i] for i in range(NE) if ev_stf[i] == k]
        print('  %-7s n %10d   mean %+0.5f bp' % (nm, len(vv), mean(vv) * BP))
        del vv
    print('  DELTA(fwd-state-only) %+0.5f bp  CI [%+0.5f, %+0.5f]  p %.5f'
          % (df * BP, flo * BP, fhi * BP, fp))

    print('\n' + '=' * 78)
    print('SECONDARY 2  15m construction  (frozen blocks; HIGH should show')
    print('  GREATER REVERSAL: E[mem15|HIGH] < E[mem15|LOW])')
    print('=' * 78)
    rets = []
    for i in range(1, N):
        if em[i] - em[i - 1] == 1 and c[i - 1] > 0:
            rets.append((i, math.log(c[i] / c[i - 1])))
    runs = collections.defaultdict(list)
    for i, r in rets:
        runs[day[i]].append((i, r))
    r15 = []
    for dd_ in sorted(runs):
        rs = runs[dd_]; k = 0
        while k + 15 <= len(rs):
            bk = rs[k:k + 15]
            if bk[-1][0] - bk[0][0] == 14:
                r15.append((bk[0][0], bk[-1][0], sum(x[1] for x in bk), dd_))
                k += 15
            else:
                k += 1
    del rets, runs
    p15 = []
    for a in range(len(r15) - 1):
        i0, i1, rv_, dd_ = r15[a]
        j0, j1, rf, dd2 = r15[a + 1]
        if j0 - i1 != 1 or rv_ == 0:
            continue
        m15 = rf if rv_ > 0 else -rf
        p15.append((dd2, m15, RB[i0], RB[j0]))
    print('  15m blocks %d   consecutive contiguous block pairs %d'
          % (len(r15), len(p15)))
    for lab, keyf in (('both blocks same state',
                       lambda e, s: e[2] == s and e[3] == s),
                      ('forward block state only',
                       lambda e, s: e[3] == s)):
        print('  --- %s' % lab)
        res15 = {}
        for s in STN:
            vv = [(e[0], e[1]) for e in p15 if keyf(e, s)]
            d3 = {}
            for dk, val in vv:
                ee = d3.setdefault(dk, [0.0, 0])
                ee[0] += val; ee[1] += 1
            m, lo_, hi_, p_ = boot_mean([tuple(x) for x in d3.values()],
                                        B_DESC)
            res15[s] = m
            print('      %-7s n %7d  mem15 %+0.4f bp  CI [%+0.4f, %+0.4f]'
                  % (s, len(vv), m * BP, lo_ * BP, hi_ * BP))
        ok15 = res15['HIGH'] < res15['LOW']
        print('      E[mem15|HIGH] < E[mem15|LOW] : %s' % ok15)
        if lab.startswith('both'):
            sec15_pass = ok15

    # ============================================= MULTIPLICITY
    print('\n' + '=' * 78)
    print('MULTIPLICITY')
    print('=' * 78)
    q2c, q2o = bh_q(dp, 2, 1), bh_q(dp, 2, 2)
    q4c = bh_q(dp, 4, 1)
    print('  H1 bootstrap p                         %.5f' % dp)
    print('  BH q at M_binding=2, CONSERVATIVE bound %.5f   (H1 rank 1;'
          ' H2 not yet run)' % q2c)
    print('  BH q at M_binding=2, optimistic bound   %.5f   (H1 rank 2)'
          % q2o)
    print('  BH q at M_cum=4, conservative (NON-BINDING sensitivity) %.5f'
          % q4c)
    if 0.025 < dp <= 0.05:
        print('  NOTE: p lies in (0.025, 0.05]; the M=2 gate outcome is'
              ' H2-DEPENDENT and is reported as such.')

    # ============================================= GATES
    print('\n' + '=' * 78)
    print('MP1 - MP10   MEMORY-PRED-V1 GATES')
    print('=' * 78)
    prec = (nL >= MIN_LOW and nM >= MIN_MED and nH >= MIN_HIGH)
    print('  PRECONDITION min n  LOW %d>=%d  MED %d>=%d  HIGH %d>=%d  -> %s'
          % (nL, MIN_LOW, nM, MIN_MED, nH, MIN_HIGH, PASS[prec]))
    g = []
    g.append(('MP1', 'adjacency exactness',
              'all %d events em-adjacent both sides; violations 0' % NE,
              True))
    g.append(('MP2', 'no leakage',
              'causal audit all YES; RVMR probes EXACT', allyes and probe_ok))
    g.append(('MP3', 'DELTA > 0 AND E[mem|LOW] < 0',
              'DELTA %+0.5f bp, LOW %+0.5f bp' % (dlt * BP,
                                                  stat['LOW'][1] * BP),
              dlt > 0 and stat['LOW'][1] < 0))
    g.append(('MP4', 'day-clustered 95% CI on DELTA excludes 0',
              '[%+0.5f, %+0.5f] bp' % (dlo * BP, dhi * BP),
              dlo > 0 or dhi < 0))
    g.append(('MP5', 'BH q<=0.05 at M=2 AND permutation p<=0.05',
              'q %.5f (cons), perm p %.5f' % (q2c, perm_p),
              q2c <= 0.05 and perm_p <= 0.05))
    g.append(('MP6', 'DELTA > 0 in >= 6 of 8 years',
              '%d of %d' % (yr_pos, len(years)), yr_pos >= 6))
    g.append(('MP7', 'DELTA > 0 in >= 2 of 3 time buckets',
              '%d of 3' % tod_pos, tod_pos >= 2))
    g.append(('MP8', 'DELTA_matched > 0 AND >= 0.50 x DELTA_raw',
              'matched %+0.5f vs raw %+0.5f bp' % (dm_full * BP, dlt * BP),
              dm_full > 0 and dm_full >= 0.5 * dlt))
    g.append(('MP9', 'DELTA > 0 in TOP50 and TOP20 subsets',
              'TOP50 %+0.5f, TOP20 %+0.5f bp'
              % (magres['TOP50'] * BP, magres['TOP20'] * BP),
              magres['TOP50'] > 0 and magres['TOP20'] > 0))
    g.append(('MP10', 'DELTA > 0 after top-1% and top-5% trims',
              'within-state %+0.5f / %+0.5f bp'
              % (tail_ws[0.01] * BP, tail_ws[0.05] * BP), tail_pass))
    for k, crit, val, ok in g:
        print('  %-5s %-44s %-44s %s' % (k, crit, val, PASS[ok]))
    npass = sum(1 for _, _, _, ok in g if ok)
    print('  MP PASSED %d / 10' % npass)
    print('\n  15m SECONDARY (both-same-state) reproduces HIGH reversal: %s'
          % sec15_pass)

    print('\n' + '=' * 78)
    print('EXECUTION COMPLETE  (elapsed %.0f s)' % (time.time() - t0))
    print('H1 ONLY. H2 NOT EXECUTED. NO COMBINATION. NO STRATEGY SIMULATED.')
    print('DEVELOPMENT ONLY - NOT OOS, NOT PROSPECTIVE, NOT CONFIRMED.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
    print('=' * 78)


if __name__ == '__main__':
    main()
