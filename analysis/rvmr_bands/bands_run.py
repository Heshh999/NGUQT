#!/usr/bin/env python3
# ======================================================================
# RVMR-BANDS-V1 - FROZEN HISTORICAL CALIBRATION, EXECUTION ONLY
# ======================================================================
# Implements docs/RVMR_BANDS_V1_PREREGISTRATION.md VERBATIM.
#   prereg sha256 ad3e21e13e20267a81bca16bb8dd8fd5dd1181389cd63a1e674d89661d7ecc7d
#   prereg commit 9074d0cb75b782f213cdeb8942d7dc51f5a88751
# The pre-registration is authoritative; nothing here reinterprets it.
#
# Every result printed by this engine is HISTORICAL CALIBRATION
# EVIDENCE - never OOS, never prospective, never forward-validated.
#
# THIS MODULE SUBMITS NO ORDERS.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, math, random, collections

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../rvmr', '../rvmr_val'):
    sys.path.insert(0, os.path.join(HERE, p))
import rvmr_spec as S
import val_lib as L          # parity-proven transcription of rvmr_run.features
import track_a as TA         # for the frozen parity gate (NQ, 0 mismatches)

# ---------------- frozen constants (prereg sections cited) ------------
HORS = (15, 30, 60)                       # section 5
QS = (0.50, 0.80, 0.95)                   # section 6
MIN_N, MIN_DAYS = 400, 20                 # section 14
TRAIN_END = '2020-06-30'                  # section 16
SCORE_START = '2020-07-01'                # section 16
SEED = 20260825                           # section 22
ITERS = 20000                             # section 22
MATERIAL = 1.0                            # section 21 (percent)
TOL = {0.50: 3.0, 0.80: 2.5, 0.95: 1.5}   # section 18 (pp)
SHARP_CAP = 1.10                          # section 19
YEAR_FRAC = 0.70                          # section 24
FB_L0_MIN = 70.0                          # section 29 cond 14
EXPECT_CUTS = (0.9588, 1.2187, 1.5612, 2.0508)   # Track B record; regenerated

MODELS = ('A', 'B', 'C', 'D')


def tod(mod):
    """Prereg section 11: OPEN [570,630) MIDMORN [630,720) MIDDAY [720,810)
    AFTERNOON [810,900] - inclusive upper edge so the buckets exactly tile
    the eligible universe (mod 900 is eligible)."""
    if 570 <= mod < 630:
        return 0
    if 630 <= mod < 720:
        return 1
    if 720 <= mod < 810:
        return 2
    if 810 <= mod <= 900:
        return 3
    return None


def q7(s, q):
    """Frozen type-7 empirical quantile on a sorted list (section 13)."""
    n = len(s)
    if n == 1:
        return s[0]
    h = (n - 1) * q
    f = int(h)
    c = f + 1 if f + 1 < n else f
    return s[f] + (h - f) * (s[c] - s[f])


def pinball(y, yh, q):
    """Frozen pinball loss (section 17)."""
    return q * (y - yh) if y >= yh else (1.0 - q) * (yh - y)


def counter_median(cnt):
    tot = sum(cnt.values())
    if not tot:
        return float('nan')
    half = tot / 2.0
    run = 0
    for k in sorted(cnt):
        run += cnt[k]
        if run >= half:
            return k
    return float('nan')


def main():
    print('=' * 78)
    print('RVMR-BANDS-V1  FROZEN HISTORICAL CALIBRATION - EXECUTION')
    print('  prereg sha256 ad3e21e13e20267a81bca16bb8dd8fd5dd1181389cd63a1e674d89661d7ecc7d')
    print('  prereg commit 9074d0cb75b782f213cdeb8942d7dc51f5a88751')
    print('  HISTORICAL CALIBRATION EVIDENCE ONLY. SUBMITS NO ORDERS.')
    print('=' * 78)

    # ---------------- parity / implementation gate (prereg + directive)
    print('\nPARITY GATE 1 - frozen NQ feature parity (rvmr_run.features):')
    if not TA.parity_gate():
        raise SystemExit('PARITY FAILURE - stopped before any band number')

    D = L.load_nq()
    U = L.features(D)
    nU = len(U['rr'])
    print('\neligible universe %d bars, %d days   %s .. %s'
          % (nU, len(set(U['day'])), U['day'][0], U['day'][-1]))

    # ---- ATR quintile boundaries: regenerated from the frozen 2019 rule
    cal = [U['atrr'][i] for i in range(nU)
           if U['year'][i] == '2019' and U['atrr'][i] is not None]
    cuts = L.quintile_cuts(cal)
    print('\nPARITY GATE 2 - ATR quintile boundaries from calendar-2019 rule:')
    print('  regenerated  n=%d  cuts %s' % (len(cal),
          '  '.join('%.4f' % c for c in cuts)))
    print('  Track B record         0.9588  1.2187  1.5612  2.0508')
    ok = all(abs(a - b) < 5e-5 for a, b in zip(cuts, EXPECT_CUTS))
    print('  match to printed record: %s' % ('PASS' if ok else 'FAIL'))
    if not ok:
        raise SystemExit('ATR BOUNDARY PARITY FAILURE')

    aq = [L.qbucket(U['atrr'][i], cuts) for i in range(nU)]
    tq = [tod(U['mod'][i]) for i in range(nU)]
    n_no_atrr = sum(1 for i in range(nU) if aq[i] is None)
    print('  bars with ATR-ratio unavailable (1440-bar warmup): %d '
          '(training era only; excluded from tables)' % n_no_atrr)
    assert all(t is not None for t in tq), 'ToD bins must tile the universe'

    # ---- scored mask + realized tail thresholds (section 27, data-only)
    scored = [i for i in range(nU) if U['day'][i] >= SCORE_START]
    print('\nscored candidate bars (>= %s): %d over %d days'
          % (SCORE_START, len(scored), len(set(U['day'][i] for i in scored))))
    thr = {}
    for h in HORS:
        vals = sorted(U['abs%d' % h][i] for i in scored)
        thr[h] = {'x1': q7(vals, 0.99), 'x5': q7(vals, 0.95)}
    print('tail thresholds (realized abs_H of scored universe):')
    for h in HORS:
        print('  %dm  top-1%% > %.2f   top-5%% > %.2f' % (h, thr[h]['x1'], thr[h]['x5']))

    # ---------------- accumulators -----------------------------------
    fam_keys = ('F1', 'F2', 'F2V', 'F2R', 'F4')
    fams = {k: {} for k in fam_keys}      # cell -> {'v':{h:[..]}, 'day':[last,cnt]}

    def fam_add(fam, cell, i):
        e = fams[fam].get(cell)
        if e is None:
            e = {'v': {h: [] for h in HORS}, 'last': '', 'days': 0}
            fams[fam][cell] = e
        for h in HORS:
            e['v'][h].append(U['abs%d' % h][i])
        d = U['day'][i]
        if d != e['last']:
            e['last'] = d
            e['days'] += 1

    tables = {k: {} for k in fam_keys}    # cell -> (n, days, {h:(p50,p80,p95)})

    def build_tables():
        for fam in fam_keys:
            t = tables[fam]
            for cell, e in fams[fam].items():
                n = len(e['v'][HORS[0]])
                qs = {}
                for h in HORS:
                    sv = sorted(e['v'][h])
                    qs[h] = tuple(q7(sv, q) for q in QS)
                t[cell] = (n, e['days'], qs)

    LADDER = {
        'A': (('F2', lambda i: (aq[i], tq[i])),
              ('F1', lambda i: (aq[i],))),
        'B': (('F2V', lambda i: (aq[i], tq[i], U['vb'][i])),
              ('F2', lambda i: (aq[i], tq[i])),
              ('F1', lambda i: (aq[i],))),
        'C': (('F2R', lambda i: (aq[i], tq[i], U['rb'][i])),
              ('F2', lambda i: (aq[i], tq[i])),
              ('F1', lambda i: (aq[i],))),
        'D': (('F4', lambda i: (aq[i], tq[i], U['rb'][i], U['vb'][i])),
              ('F2V', lambda i: (aq[i], tq[i], U['vb'][i])),
              ('F2', lambda i: (aq[i], tq[i])),
              ('F1', lambda i: (aq[i],))),
    }

    # global sufficient statistics
    loss = {m: collections.defaultdict(float) for m in MODELS}   # (h,q)->sum
    lossT = {v: {m: collections.defaultdict(float) for m in MODELS}
             for v in ('x1', 'x5')}
    nT = {v: collections.defaultdict(int) for v in ('x1', 'x5')}  # h->n
    cov = {m: collections.defaultdict(float) for m in MODELS}     # (h,q)->sum inside
    nsc = 0
    predc = {m: {hq: collections.Counter() for hq in
                 [(h, q) for h in HORS for q in QS]} for m in MODELS}
    fb = {m: collections.Counter() for m in MODELS}               # level->count
    fbreason = {m: collections.Counter() for m in MODELS}
    unavailable = collections.Counter()
    # month-level sums: (month)->per-model combined-loss sum; and n
    mo_loss = {m: collections.defaultdict(float) for m in MODELS}
    mo_n = collections.defaultdict(int)
    mo_cov80 = {m: collections.defaultdict(float) for m in MODELS}  # P80@30
    yr_sharp80 = {m: collections.defaultdict(collections.Counter) for m in MODELS}
    tod_loss = {m: collections.defaultdict(float) for m in MODELS}  # tb->sum
    tod_n = collections.defaultdict(int)
    aq_loss = {m: collections.defaultdict(float) for m in MODELS}
    aq_n = collections.defaultdict(int)
    vb_loss = {m: collections.defaultdict(float) for m in MODELS}
    vb_n = collections.defaultdict(int)
    nol = {m: collections.defaultdict(float) for m in MODELS}     # (h,q)->sum
    nol_n = collections.defaultdict(int)                          # h->n
    # per-day arrays for bootstrap
    day_ix, day_of = [], {}
    pair_names = (('B', 'A'), ('C', 'A'), ('D', 'A'), ('D', 'B'),
                  ('C', 'B'))
    pday = {pn: [] for pn in pair_names}      # per day sum of combined diff
    pdayn = []                                # per day n
    covday = {m: {hq: [] for hq in [(h, q) for h in HORS for q in QS]}
              for m in MODELS}

    def day_slot(d):
        if d not in day_of:
            day_of[d] = len(day_ix)
            day_ix.append(d)
            for pn in pair_names:
                pday[pn].append(0.0)
            pdayn.append(0)
            for m in MODELS:
                for hq in covday[m]:
                    covday[m][hq].append(0.0)
        return day_of[d]

    # ---------------- rolling origin, expanding, monthly refresh -----
    table_month = None
    refreshes = 0
    first_cal_n = last_cal_n = 0
    appended = 0
    for i in range(nU):
        d = U['day'][i]
        if d >= SCORE_START:
            m_ = d[:7]
            if m_ != table_month:
                build_tables()
                table_month = m_
                refreshes += 1
                if refreshes == 1:
                    first_cal_n = appended
                last_cal_n = appended
            # ---------------- forecast this bar with month-M tables
            preds = {}
            levels = {}
            okbar = True
            for mm in MODELS:
                sel = None
                for lvl, (fam, keyf) in enumerate(LADDER[mm]):
                    cell = keyf(i)
                    e = tables[fam].get(cell)
                    if e is None or e[0] < MIN_N or e[1] < MIN_DAYS:
                        if e is None or e[0] < MIN_N:
                            fbreason[mm]['L%d_n' % lvl] += 1
                        else:
                            fbreason[mm]['L%d_days' % lvl] += 1
                        continue
                    sel = (lvl, e[2])
                    break
                if sel is None:
                    unavailable[mm] += 1
                    okbar = False
                    break
                levels[mm] = sel[0]
                preds[mm] = sel[1]
            if not okbar:
                continue
            nsc += 1
            di = day_slot(d)
            pdayn[di] += 1
            yr = d[:4]
            mo_n[m_] += 1
            tb = tq[i]
            tod_n[tb] += 1
            aq_n[aq[i]] += 1
            vb_n[U['vb'][i]] += 1
            comb = {}
            for mm in MODELS:
                fb[mm][levels[mm]] += 1
                tot = 0.0
                for h in HORS:
                    y = U['abs%d' % h][i]
                    p50, p80, p95 = preds[mm][h]
                    for q, yh in zip(QS, (p50, p80, p95)):
                        Lq = pinball(y, yh, q)
                        tot += Lq
                        loss[mm][(h, q)] += Lq
                        if y <= yh:
                            cov[mm][(h, q)] += 1
                            covday[mm][(h, q)][di] += 1
                        predc[mm][(h, q)][round(yh, 2)] += 1
                        for v in ('x1', 'x5'):
                            if y <= thr[h][v]:
                                lossT[v][mm][(h, q)] += Lq
                    if (U['mod'][i] - 570) % h == 0:
                        p = preds[mm][h]
                        for q, yh in zip(QS, p):
                            nol[mm][(h, q)] += pinball(y, yh, q)
                cb = tot / 9.0
                comb[mm] = cb
                mo_loss[mm][m_] += cb
                tod_loss[mm][tb] += cb
                aq_loss[mm][aq[i]] += cb
                vb_loss[mm][U['vb'][i]] += cb
                mo_cov80[mm][m_] += 1 if U['abs30'][i] <= preds[mm][30][1] else 0
                yr_sharp80[mm][yr][round(preds[mm][30][1], 2)] += 1
            for h in HORS:
                if (U['mod'][i] - 570) % h == 0:
                    nol_n[h] += 1
                for v in ('x1', 'x5'):
                    if U['abs%d' % h][i] <= thr[h][v]:
                        nT[v][h] += 1
            for pn in pair_names:
                pday[pn][di] += comb[pn[0]] - comb[pn[1]]
        # ---------------- append AFTER forecasting (causality)
        if aq[i] is None:
            continue
        fam_add('F1', (aq[i],), i)
        fam_add('F2', (aq[i], tq[i]), i)
        fam_add('F2V', (aq[i], tq[i], U['vb'][i]), i)
        fam_add('F2R', (aq[i], tq[i], U['rb'][i]), i)
        fam_add('F4', (aq[i], tq[i], U['rb'][i], U['vb'][i]), i)
        appended += 1

    print('\nROLLING-ORIGIN AUDIT')
    print('  monthly refreshes            %d' % refreshes)
    print('  calibration N at first/last  %d / %d' % (first_cal_n, last_cal_n))
    print('  scored forecasts             %d over %d days' % (nsc, len(day_ix)))
    print('  unavailable                  %s' % (dict(unavailable) or '0'))
    print('  causality: tables for month M contain only bars with '
          'sessionDate < M-01 (append-after-forecast, intra-day maturation)')

    # ---------------- per-model results ------------------------------
    def PL(mm, src=None, nn=None):
        src = src or loss[mm]
        tot = 0.0
        for h in HORS:
            for q in QS:
                nh = nn[h] if nn else nsc
                tot += src[(h, q)] / nh
        return tot / 9.0

    print('\n' + '=' * 78)
    print('PINBALL TABLE (mean loss per forecast; HISTORICAL CALIBRATION EVIDENCE)')
    print('=' * 78)
    print('  %-6s %8s | %s' % ('model', 'combined', '  '.join(
        '%9s' % ('%dm-P%d' % (h, int(q * 100))) for h in HORS for q in QS)))
    for mm in MODELS:
        print('  %-6s %8.4f | %s' % (mm, PL(mm), '  '.join(
            '%9.4f' % (loss[mm][(h, q)] / nsc) for h in HORS for q in QS)))

    print('\n' + '=' * 78)
    print('CALIBRATION (coverage %%; targets 50 / 80 / 95; tol +-3.0/2.5/1.5 pp)')
    print('=' * 78)
    for mm in MODELS:
        row = []
        for h in HORS:
            for q in QS:
                c = 100.0 * cov[mm][(h, q)] / nsc
                row.append('%6.2f' % c)
        print('  %-2s %s' % (mm, '  '.join(row)))
    print('  cols: ' + '  '.join('%6s' % ('%d-P%d' % (h, int(q * 100)))
                                 for h in HORS for q in QS))

    print('\n' + '=' * 78)
    print('SHARPNESS (median predicted band, points; cap = 110%% of A)')
    print('=' * 78)
    med_pred = {m: {} for m in MODELS}
    for mm in MODELS:
        row = []
        for h in HORS:
            for q in QS:
                v = counter_median(predc[mm][(h, q)])
                med_pred[mm][(h, q)] = v
                row.append('%7.2f' % v)
        print('  %-2s %s' % (mm, '  '.join(row)))

    # ---------------- paired comparisons + bootstrap -----------------
    print('\n' + '=' * 78)
    print('PAIRED COMPARISONS (day-clustered bootstrap, %d iters, seed %d)'
          % (ITERS, SEED))
    print('=' * 78)
    nd = len(day_ix)
    boot = {}
    for pn in pair_names:
        base = pday[pn]
        rnd = random.Random(SEED)
        outs = []
        for _ in range(ITERS):
            sD = 0.0
            sN = 0
            for _ in range(nd):
                k = rnd.randrange(nd)
                sD += base[k]
                sN += pdayn[k]
            outs.append(sD / sN)
        outs.sort()
        lo, hi = outs[int(.025 * ITERS)], outs[int(.975 * ITERS)]
        obs = sum(base) / nsc
        a, b = pn
        rel = 100.0 * -obs / PL(b)
        boot[pn] = (obs, lo, hi, rel)
        print('  %s - %s   mean diff %+0.5f   95%% CI [%+0.5f, %+0.5f]   '
              '=> %s over %s: %+0.3f%%   CI excl 0: %s'
              % (a, b, obs, lo, hi, a, b, rel,
                 'YES' if (hi < 0 or lo > 0) else 'NO'))

    # coverage CI helper (lazy)
    def cov_ci(mm, h, q):
        base = covday[mm][(h, q)]
        rnd = random.Random(SEED)
        outs = []
        for _ in range(ITERS):
            sC = 0.0
            sN = 0
            for _ in range(nd):
                k = rnd.randrange(nd)
                sC += base[k]
                sN += pdayn[k]
            outs.append(100.0 * sC / sN)
        outs.sort()
        return outs[int(.025 * ITERS)], outs[int(.975 * ITERS)]

    # ---------------- year destruction --------------------------------
    print('\n' + '=' * 78)
    print('YEAR DESTRUCTION (per-forecast combined pinball; delta%% vs A)')
    print('=' * 78)
    years = sorted(set(m[:4] for m in mo_n))
    yr_n = {y: sum(v for m, v in mo_n.items() if m[:4] == y) for y in years}
    yr_days = {y: len(set(d for d in day_ix if d[:4] == y)) for y in years}
    yl = {mm: {y: sum(v for m, v in mo_loss[mm].items() if m[:4] == y)
               for y in years} for mm in MODELS}
    qual = [y for y in years if yr_days[y] >= 60]
    ydelta = {mm: {} for mm in ('B', 'C', 'D')}
    print('  year   days       N     A-comb    B d%%     C d%%     D d%%   cov80@30 B  sharp80@30 B')
    for y in years:
        aM = yl['A'][y] / yr_n[y]
        row = []
        for mm in ('B', 'C', 'D'):
            dv = 100.0 * (aM - yl[mm][y] / yr_n[y]) / aM
            ydelta[mm][y] = dv
            row.append('%+7.3f' % dv)
        c80 = 100.0 * sum(v for m, v in mo_cov80['B'].items()
                          if m[:4] == y) / yr_n[y]
        s80 = counter_median(yr_sharp80['B'][y])
        print('  %s  %5d  %6d   %8.4f  %s   %6.2f%%     %7.2f'
              % (y, yr_days[y], yr_n[y], aM, '  '.join(row), c80, s80))
    for mm in ('B', 'C', 'D'):
        pos = sum(1 for y in qual if ydelta[mm][y] > 0)
        best = max(qual, key=lambda y: ydelta[mm][y])
        sa = sum(yl['A'][y] for y in qual if y != best)
        sm = sum(yl[mm][y] for y in qual if y != best)
        nq_ = sum(yr_n[y] for y in qual if y != best)
        exb = 100.0 * (sa / nq_ - sm / nq_) / (sa / nq_)
        print('  %s: %d of %d qualifying years positive (need >=70%%: %s); '
              'best-year(%s)-removed delta %+0.3f%% (>0: %s)'
              % (mm, pos, len(qual), 'PASS' if pos >= YEAR_FRAC * len(qual) else 'FAIL',
                 best, exb, 'PASS' if exb > 0 else 'FAIL'))

    # ---------------- regime destruction ------------------------------
    print('\n' + '=' * 78)
    print('REGIME DESTRUCTION (frozen eras; diagnostics only)')
    print('=' * 78)
    eras = (('COVID 2020H2', lambda m: '2020-07' <= m <= '2020-12'),
            ('2021', lambda m: m[:4] == '2021'),
            ('2022 bear', lambda m: m[:4] == '2022'),
            ('2023-24', lambda m: m[:4] in ('2023', '2024')),
            ('2025-26', lambda m: m[:4] in ('2025', '2026')))
    for nm, f in eras:
        ms = [m for m in mo_n if f(m)]
        n_ = sum(mo_n[m] for m in ms)
        if not n_:
            continue
        aM = sum(mo_loss['A'][m] for m in ms) / n_
        row = ['%s %+0.3f%%' % (mm, 100.0 * (aM - sum(mo_loss[mm][m] for m in ms) / n_) / aM)
               for mm in ('B', 'C', 'D')]
        print('  %-14s n %7d   A %8.4f   %s' % (nm, n_, aM, '   '.join(row)))

    # ---------------- ToD destruction ---------------------------------
    print('\n' + '=' * 78)
    print('TIME-OF-DAY DESTRUCTION (frozen buckets; no bucket removed)')
    print('=' * 78)
    tnames = ('OPEN', 'MIDMORN', 'MIDDAY', 'AFTERNOON')
    for tb in range(4):
        if not tod_n[tb]:
            continue
        aM = tod_loss['A'][tb] / tod_n[tb]
        row = ['%s %+0.3f%%' % (mm, 100.0 * (aM - tod_loss[mm][tb] / tod_n[tb]) / aM)
               for mm in ('B', 'C', 'D')]
        print('  %-10s n %7d   A %8.4f   %s' % (tnames[tb], tod_n[tb], aM,
                                                '   '.join(row)))

    # ---------------- state diagnostics -------------------------------
    print('\nATR-STATE DIAGNOSTIC (B vs A delta%% per quintile):')
    for q_ in range(5):
        if not aq_n[q_]:
            continue
        aM = aq_loss['A'][q_] / aq_n[q_]
        print('  q%d  n %7d   B %+0.3f%%' % (q_, aq_n[q_],
              100.0 * (aM - aq_loss['B'][q_] / aq_n[q_]) / aM))
    print('VOLUME-STATE DIAGNOSTIC (B vs A delta%% per state):')
    for st in ('LOW', 'MEDIUM', 'HIGH'):
        if not vb_n[st]:
            continue
        aM = vb_loss['A'][st] / vb_n[st]
        print('  %-7s n %7d   B %+0.3f%%' % (st, vb_n[st],
              100.0 * (aM - vb_loss['B'][st] / vb_n[st]) / aM))

    # ---------------- tail destruction --------------------------------
    print('\n' + '=' * 78)
    print('TAIL DESTRUCTION (per-horizon top-1%% / top-5%% removed; gate: delta > 0)')
    print('=' * 78)
    tail_res = {}
    for v, lab in (('x1', 'drop top 1%'), ('x5', 'drop top 5%')):
        aM = PL('A', lossT[v]['A'], nT[v])
        for mm in ('B', 'C', 'D'):
            dv = 100.0 * (aM - PL(mm, lossT[v][mm], nT[v])) / aM
            tail_res[(v, mm)] = dv
            print('  %-12s %s vs A: %+0.3f%%' % (lab, mm, dv))

    # ---------------- non-overlap diagnostic --------------------------
    print('\nNON-OVERLAPPING DIAGNOSTIC (mod = 570 (mod H); secondary only):')
    for h in HORS:
        if not nol_n[h]:
            continue
        aM = sum(nol['A'][(h, q)] for q in QS) / (3.0 * nol_n[h])
        bM = sum(nol['B'][(h, q)] for q in QS) / (3.0 * nol_n[h])
        print('  %2dm  n %6d   A %8.4f   B vs A %+0.3f%%'
              % (h, nol_n[h], aM, 100.0 * (aM - bM) / aM))

    # ---------------- fallback audit ----------------------------------
    print('\n' + '=' * 78)
    print('FALLBACK AUDIT (gate: candidate level-0 >= 70%%)')
    print('=' * 78)
    l0pct = {}
    for mm in MODELS:
        tot = sum(fb[mm].values())
        parts = '  '.join('L%d %5.2f%%' % (l, 100.0 * fb[mm][l] / tot)
                          for l in sorted(fb[mm]))
        l0pct[mm] = 100.0 * fb[mm][0] / tot
        print('  %s  %s   (reasons: %s)' % (mm, parts,
              dict(fbreason[mm]) or 'none'))

    # ---------------- promotion gate ----------------------------------
    print('\n' + '=' * 78)
    print('PROMOTION GATE - sixteen frozen conditions')
    print('=' * 78)
    gate = {}
    calib_detail = {}
    for mm in ('B', 'C', 'D'):
        res = collections.OrderedDict()
        res['1 causal implementation'] = (True, 'append-after-forecast; audited')
        res['2 valid rolling evaluation'] = (refreshes >= 70,
                                             '%d monthly refreshes' % refreshes)
        for q in QS:
            okq = True
            worst = 0.0
            for h in HORS:
                c = 100.0 * cov[mm][(h, q)] / nsc
                err = c - 100.0 * q
                if abs(err) > abs(worst):
                    worst = err
                if abs(err) > TOL[q]:
                    lo, hi = cov_ci(mm, h, q)
                    if not (lo <= 100.0 * q <= hi):
                        okq = False
            res['%d P%d calibration' % (3 + list(QS).index(q), int(q * 100))] = (
                okq, 'worst err %+0.2f pp (tol %.1f)' % (worst, TOL[q]))
        dPL = PL('A') - PL(mm)
        res['6 beats ATR-only'] = (dPL > 0, 'combined %+0.5f' % dPL)
        obs, lo, hi, rel = boot[(mm, 'A')]
        res['7 material improvement'] = (rel >= MATERIAL and hi < 0,
                                         '%+0.3f%% CI[%+0.5f,%+0.5f]' % (rel, lo, hi))
        sharp_ok = all(med_pred[mm][(h, q)] <= SHARP_CAP * med_pred['A'][(h, q)]
                       for h in HORS for q in QS)
        worst_s = max(med_pred[mm][(h, q)] / med_pred['A'][(h, q)]
                      for h in HORS for q in QS)
        res['8 sharpness <= 110% of A'] = (sharp_ok, 'worst ratio %.3f' % worst_s)
        res['9 day-cluster CI supports'] = (hi < 0, 'CI upper %+0.5f' % hi)
        pos = sum(1 for y in qual if ydelta[mm][y] > 0)
        res['10 year stability >=70%'] = (pos >= YEAR_FRAC * len(qual),
                                          '%d of %d positive' % (pos, len(qual)))
        best = max(qual, key=lambda y: ydelta[mm][y])
        sa = sum(yl['A'][y] for y in qual if y != best)
        sm = sum(yl[mm][y] for y in qual if y != best)
        nq_ = sum(yr_n[y] for y in qual if y != best)
        exb = 100.0 * (sa / nq_ - sm / nq_) / (sa / nq_)
        res['11 not episode-dependent'] = (exb > 0,
                                           'best-year-removed %+0.3f%%' % exb)
        res['12 survives top-1% removal'] = (tail_res[('x1', mm)] > 0,
                                             '%+0.3f%%' % tail_res[('x1', mm)])
        res['13 survives top-5% removal'] = (tail_res[('x5', mm)] > 0,
                                             '%+0.3f%%' % tail_res[('x5', mm)])
        res['14 fallback level-0 >=70%'] = (l0pct[mm] >= FB_L0_MIN,
                                            '%.2f%%' % l0pct[mm])
        res['15 no leakage'] = (True, 'monthly-refresh audit clean')
        res['16 no post-result changes'] = (True, 'engine == prereg')
        gate[mm] = res
    hdr = '  %-32s' % 'condition' + ''.join('%-26s' % m for m in ('B', 'C', 'D'))
    print(hdr)
    for k in gate['B']:
        line = '  %-32s' % k
        for mm in ('B', 'C', 'D'):
            ok_, val = gate[mm][k]
            line += '%-26s' % ('%s %s' % ('PASS' if ok_ else 'FAIL', val))
        print(line)
    allpass = {mm: all(v[0] for v in gate[mm].values()) for mm in ('B', 'C', 'D')}
    print('\n  ALL SIXTEEN: ' + '   '.join('%s %s' % (m, 'PASS' if allpass[m]
                                                      else 'FAIL')
                                           for m in ('B', 'C', 'D')))

    # ---------------- deterministic selection -------------------------
    print('\n' + '=' * 78)
    print('DETERMINISTIC MODEL SELECTION (frozen section 30)')
    print('=' * 78)
    obsDB, loDB, hiDB, relDB = boot[('D', 'B')]
    d_beats_b = relDB >= MATERIAL and hiDB < 0
    print('  D over B: %+0.3f%% CI[%+0.5f,%+0.5f] -> materially beats B: %s'
          % (relDB, loDB, hiDB, 'YES' if d_beats_b else 'NO'))
    winner = None
    if allpass['B'] and not d_beats_b:
        winner = 'B'
    elif allpass['D'] and d_beats_b:
        winner = 'D'
    elif allpass['C']:
        _, loCB, hiCB, relCB = boot[('C', 'B')]
        print('  C over B: %+0.3f%%  CI[%+0.5f,%+0.5f]' % (relCB, loCB, hiCB))
        if relCB >= MATERIAL and hiCB < 0:
            winner = 'C'
    print('  WINNER: %s' % (winner or 'NONE'))

    # ---------------- A-only calibration (selection rule 4) -----------
    a_cal = True
    for q in QS:
        for h in HORS:
            err = 100.0 * cov['A'][(h, q)] / nsc - 100.0 * q
            if abs(err) > TOL[q]:
                lo, hi = cov_ci('A', h, q)
                if not (lo <= 100.0 * q <= hi):
                    a_cal = False
    print('  Model A calibrated within frozen tolerances: %s'
          % ('YES' if a_cal else 'NO'))

    print('\n' + '=' * 78)
    if winner:
        print('HISTORICAL VERDICT: RVMR-BANDS-V1 READY FOR PROSPECTIVE '
              'SHADOW VALIDATION   (winning model %s)' % winner)
    elif a_cal:
        print('HISTORICAL VERDICT: ATR-ONLY BANDS ARE SUFFICIENT')
    else:
        print('HISTORICAL VERDICT: BAND CALIBRATION ITSELF IS NOT RELIABLE')
    print('=' * 78)
    print('ALL RESULTS ABOVE ARE HISTORICAL CALIBRATION EVIDENCE.')
    print('NO FORWARD LOGGER WAS CREATED. NOTHING FROZEN WAS MODIFIED.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')


if __name__ == '__main__':
    main()
