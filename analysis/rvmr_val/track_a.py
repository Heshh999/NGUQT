#!/usr/bin/env python3
# ======================================================================
# RVMR-VALIDATION-V1  TRACK A - RVMR-ES-V1 OUT-OF-MARKET REPLICATION
# ======================================================================
# The EXACT frozen RVMR mechanism applied to ES with ZERO recalibration.
# Pre-registered at docs/RVMR_VALIDATION_V1_PREREGISTRATION.md
#   sha256 025598ad685e617ca8ea4d2d044be52e38343de22ac2db899a22958ea4b161c3
#
# THIS MODULE SUBMITS NO ORDERS. NO LIVE TRADING IS AUTHORIZED.
# ======================================================================

import os, sys, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import val_lib as L
import rvmr_spec as S
import rvmr_run as RV

TOOLS = (('rb', 'rr', 'RANGE-REGIME-V1'), ('vb', 'vr', 'VOLUME-REGIME-V1'))


def parity_gate():
    """Prove val_lib.features reproduces the FROZEN rvmr_run.features
    before a single ES number is computed. If this fails, nothing that
    follows can be trusted and the run stops."""
    print('=' * 78)
    print('PARITY GATE - val_lib.features vs FROZEN rvmr_run.features (NQ)')
    print('=' * 78)
    RV.STAMP_SHIFT = 0
    D = RV.load_bars(pre_discovery_only=True)
    Uf, _ = RV.features(D)
    Um = L.features(D, want_excursion=False)
    ok = True
    if len(Uf['rr']) != len(Um['rr']):
        print('  FAIL universe size %d vs %d' % (len(Uf['rr']), len(Um['rr'])))
        return False
    print('  universe size            %d  MATCH' % len(Uf['rr']))
    for k in ('i', 'day', 'mod', 'rb', 'vb'):
        bad = sum(1 for a, b in zip(Uf[k], Um[k]) if a != b)
        print('  column %-6s mismatches %d  %s' % (k, bad, 'MATCH' if not bad else 'FAIL'))
        ok = ok and not bad
    for k in ('rr', 'vr'):
        bad = sum(1 for a, b in zip(Uf[k], Um[k]) if abs(a - b) > 1e-12)
        print('  column %-6s mismatches %d  %s' % (k, bad, 'MATCH' if not bad else 'FAIL'))
        ok = ok and not bad
    for h in L.HOR:
        k = 'abs%d' % h
        bad = sum(1 for a, b in zip(Uf[k], Um[k]) if abs(a - b) > 1e-12)
        print('  column %-6s mismatches %d  %s' % (k, bad, 'MATCH' if not bad else 'FAIL'))
        ok = ok and not bad
    print('  PARITY GATE: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def bucket_shares(U, bkey):
    c = collections.Counter(U[bkey][i] for i in range(len(U['rr'])))
    n = float(sum(c.values()))
    return {b: (c[b], 100.0 * c[b] / n) for b in ('LOW', 'MEDIUM', 'HIGH')}, n


def internal_terciles(U, skey):
    """DECLARED DIAGNOSTIC ONLY - ES-internal terciles of the RAW score,
    used SOLELY to separate mechanism failure from calibration failure.
    These are never adopted as thresholds and create no new tool."""
    v = sorted(U[skey])
    t1, t2 = v[len(v) // 3], v[2 * len(v) // 3]
    lab = []
    for x in U[skey]:
        lab.append('LOW' if x < t1 else ('MEDIUM' if x <= t2 else 'HIGH'))
    return lab, t1, t2


def run():
    print('=' * 78)
    print('RVMR-VALIDATION-V1   TRACK A - RVMR-ES-V1')
    print('  OUT-OF-MARKET REPLICATION, ZERO RECALIBRATION')
    print('  frozen thresholds  LOW < %.3f <= MEDIUM <= %.3f < HIGH'
          % (S.T1, S.T2))
    print('  frozen lookback    W = %d bars, current bar EXCLUDED' % S.W)
    print('  frozen horizons    %s' % (L.HOR,))
    print('  frozen universe    RTH %d..%d, >=60m to close, ATR20>0,'
          % (S.RTH_START, S.RTH_END))
    print('                     both scores non-None, 60 contiguous fwd bars')
    print('  HISTORICAL RESEARCH - never relabelled prospective.')
    print('  THIS MODULE SUBMITS NO ORDERS.')
    print('=' * 78)

    if not parity_gate():
        raise SystemExit('PARITY GATE FAILED - Track A not run')

    print('\nloading ES ...')
    D = L.load_es()
    print('ES bars %d   %s .. %s' % (len(D['c']), D['et'][0], D['et'][-1]))
    U = L.features(D)
    nU = len(U['rr'])
    days = sorted(set(U['day']))
    print('ES eligible universe %d bars, %d days\n' % (nU, len(days)))
    if nU < 20000:
        print('INSUFFICIENT DATA')
        return

    # ---------------------------------------------------------- A7
    print('=' * 78)
    print('A7 - CALIBRATION TRANSPORT: do the frozen NQ cutoffs produce')
    print('     usable ES groups?  (each bucket must hold >= 5%)')
    print('=' * 78)
    shares = {}
    for bkey, skey, nm in TOOLS:
        sh, n = bucket_shares(U, bkey)
        shares[nm] = sh
        print('  %-18s ' % nm + '   '.join(
            '%s %7d (%5.2f%%)' % (b, sh[b][0], sh[b][1])
            for b in ('LOW', 'MEDIUM', 'HIGH')))
        worst = min(sh[b][1] for b in ('LOW', 'MEDIUM', 'HIGH'))
        print('      smallest bucket %.2f%%   A7 %s'
              % (worst, 'PASS' if worst >= 5.0 else 'FAIL'))
    print()

    # ---------------------------------------------------------- A1/A2/A3
    print('=' * 78)
    print('A1/A2/A3 - PRIMARY: monotonicity, separation, day-level stats')
    print('=' * 78)
    A = {}
    for bkey, skey, nm in TOOLS:
        print(nm)
        res, mono = L.monotone_table(U, bkey)
        if not all(k in res for k in ('LOW', 'MEDIUM', 'HIGH')):
            print('  bucket missing - cannot evaluate\n')
            A[nm] = None
            continue
        hl = [(U['day'][i], U['abs30'][i]) for i in res['HIGH']['ii']]
        ll = [(U['day'][i], U['abs30'][i]) for i in res['LOW']['ii']]
        d30, ci, p_boot = L.day_boot_delta(hl, ll, iters=20000)
        chi = L.day_boot_ci(hl, iters=5000)
        clo = L.day_boot_ci(ll, iters=5000)
        print('  mean|ret|@30  HIGH %.2f CI[%.2f,%.2f]  LOW %.2f CI[%.2f,%.2f]'
              % (res['HIGH']['mean30'], chi[0], chi[1],
                 res['LOW']['mean30'], clo[0], clo[1]))
        print('  HIGH-LOW %+.3f  day-clustered 95%% CI [%+.3f, %+.3f]  p %.4f'
              % (d30, ci[0], ci[1], p_boot))
        print('  H/L %.3fx   H/M %.3fx'
              % (res['HIGH']['mean30'] / res['LOW']['mean30'],
                 res['HIGH']['mean30'] / res['MEDIUM']['mean30']))
        ds, dx, dy = L.day_spearman(U['day'], U[skey], U['abs30'])
        rho = L.spearman(dx, dy)
        pp = L.day_perm_p(dx, dy, iters=20000)
        full = L.spearman(U[skey], U['abs30'])
        print('  full Spearman (point est only) %+0.4f' % full)
        print('  DAY-level Spearman %+0.4f over %d days   day-shuffle p %.5f'
              % (rho, len(ds), pp))
        A[nm] = {'res': res, 'mono': mono, 'd30': d30, 'ci': ci,
                 'p_boot': p_boot, 'rho': rho, 'p_perm': pp, 'full': full}
        print()

    # ---------------------------------------------------------- A5 years
    print('=' * 78)
    print('A5 - YEAR STABILITY (thresholds NEVER altered)')
    print('=' * 78)
    years = sorted(set(U['year']))
    for bkey, skey, nm in TOOLS:
        print(nm)
        pos = 0; tested = 0
        for y in years:
            mask = [i for i in range(nU) if U['year'][i] == y]
            res, mono = L.monotone_table(U, bkey, mask, quiet=True)
            if not all(k in res for k in ('LOW', 'MEDIUM', 'HIGH')):
                print('    %s  n %6d  bucket missing' % (y, len(mask)))
                continue
            tested += 1
            d = res['HIGH']['mean30'] - res['LOW']['mean30']
            if d > 0:
                pos += 1
            print('    %s  N L/M/H %6d/%6d/%6d  mean30 L/M/H %5.2f/%5.2f/%5.2f'
                  '  H-L %+6.2f  mono %d/5  %s'
                  % (y, res['LOW']['n'], res['MEDIUM']['n'], res['HIGH']['n'],
                     res['LOW']['mean30'], res['MEDIUM']['mean30'],
                     res['HIGH']['mean30'], d, sum(mono.values()),
                     'POS' if d > 0 else 'NEG'))
        if A.get(nm) is not None:
            A[nm]['years_pos'] = pos; A[nm]['years_tested'] = tested
        print('    -> %d of %d years positive   A5 %s\n'
              % (pos, tested, 'PASS' if tested and pos >= 6 else 'FAIL'))

    # ---------------------------------------------------------- A4 months
    print('=' * 78)
    print('A4 - MONTH STABILITY (inverted months shown, never hidden)')
    print('=' * 78)
    for bkey, skey, nm in TOOLS:
        eff = []
        for m in sorted(set(d[:7] for d in U['day'])):
            hi_ = [U['abs30'][i] for i in range(nU)
                   if U['day'][i][:7] == m and U[bkey][i] == 'HIGH']
            lo_ = [U['abs30'][i] for i in range(nU)
                   if U['day'][i][:7] == m and U[bkey][i] == 'LOW']
            if len(hi_) >= 20 and len(lo_) >= 20:
                eff.append((L.med(hi_) - L.med(lo_), m))
        if not eff:
            print('%s  no eligible months\n' % nm)
            continue
        pos = sum(1 for e, _ in eff if e > 0)
        eff.sort()
        pct = 100.0 * pos / len(eff)
        print('%s  months %d  positive %d (%.0f%%)  median %+0.2f'
              % (nm, len(eff), pos, pct, L.med([e for e, _ in eff])))
        print('    worst %+0.2f (%s)   best %+0.2f (%s)   A4 %s'
              % (eff[0][0], eff[0][1], eff[-1][0], eff[-1][1],
                 'PASS' if pct >= 70 else 'FAIL'))
        neg = [x for x in eff if x[0] <= 0]
        if neg:
            print('    inverted/flat months (%d): %s'
                  % (len(neg), ', '.join('%s %+0.2f' % (m, e) for e, m in neg[:12])))
        if A.get(nm) is not None:
            A[nm]['months_pct'] = pct
        print()

    # ---------------------------------------------------------- A6 ToD
    print('=' * 78)
    print('A6 - TIME OF DAY (frozen predeclared buckets) + ToD-matched')
    print('=' * 78)
    for bkey, skey, nm in TOOLS:
        print(nm)
        for lab, a, b in L.TOD:
            mask = [i for i in range(nU) if a <= U['mod'][i] < b]
            res, mono = L.monotone_table(U, bkey, mask, quiet=True)
            if not all(k in res for k in ('LOW', 'MEDIUM', 'HIGH')):
                continue
            print('  %-20s n %6d  med30 L/M/H %5.2f/%5.2f/%5.2f  mono %d/5'
                  % (lab, len(mask), res['LOW']['med'][30],
                     res['MEDIUM']['med'][30], res['HIGH']['med'][30],
                     sum(mono.values())))
        # per-minute ToD-matched separation (frozen TEST 15 construction)
        slots = collections.defaultdict(lambda: {'H': [], 'L': []})
        for i in range(nU):
            if U[bkey][i] == 'HIGH':
                slots[U['mod'][i]]['H'].append(U['abs30'][i])
            elif U[bkey][i] == 'LOW':
                slots[U['mod'][i]]['L'].append(U['abs30'][i])
        w = tot = 0.0
        for m2, g in slots.items():
            if len(g['H']) >= 10 and len(g['L']) >= 10:
                k = len(g['H']) + len(g['L'])
                w += (L.med(g['H']) - L.med(g['L'])) * k
                tot += k
        todm = w / tot if tot else float('nan')
        r = A.get(nm)
        pooled = (r['res']['HIGH']['med'][30] - r['res']['LOW']['med'][30]) if r else float('nan')
        ret = 100.0 * todm / pooled if pooled else float('nan')
        print('  pooled H-L median@30 %+0.3f   ToD-matched %+0.3f'
              '   retained %.0f%%   A6 %s'
              % (pooled, todm, ret, 'PASS' if ret >= 50 else 'FAIL'))
        if r is not None:
            r['tod_retained'] = ret
        # 3-trading-day-lagged label: slow regime vs local state
        bydm = {}
        for i in range(nU):
            bydm[(U['day'][i], U['mod'][i])] = U[bkey][i]
        dl = sorted(set(U['day'])); dp = {d: k for k, d in enumerate(dl)}
        lagH, lagL = [], []
        for i in range(nU):
            k = dp[U['day'][i]]
            if k < 3:
                continue
            lb = bydm.get((dl[k - 3], U['mod'][i]))
            if lb == 'HIGH':
                lagH.append(U['abs30'][i])
            elif lb == 'LOW':
                lagL.append(U['abs30'][i])
        print('  3-trading-day-lagged label H-L %+0.3f  (slow regime component)\n'
              % (L.med(lagH) - L.med(lagL)))

    # ---------------------------------------------------------- persistence
    print('=' * 78)
    print('PERSISTENCE (mean 1m range per minute AFTER the state)')
    print('=' * 78)
    rngall = [D['h'][i] - D['l'][i] for i in range(len(D['c']))]
    for bkey, skey, nm in TOOLS:
        print(nm)
        acc = collections.defaultdict(lambda: collections.defaultdict(list))
        for r_ in range(nU):
            j = U['i'][r_]
            b = U[bkey][r_]
            if b is None:
                continue
            for wnd in (3, 5, 10, 15, 30):
                if D['em'][j + wnd] - D['em'][j] != wnd:
                    continue
                acc[b][wnd].append(
                    sum(rngall[j + 1:j + wnd + 1]) / float(wnd))
        print('  %-7s ' % 'window' + '  '.join('%5d' % w for w in (3, 5, 10, 15, 30)))
        for b in ('LOW', 'MEDIUM', 'HIGH'):
            print('  %-7s ' % b + '  '.join(
                '%5.2f' % L.med(acc[b][w]) for w in (3, 5, 10, 15, 30)))
        print('  H/L     ' + '  '.join(
            '%5.2f' % (L.med(acc['HIGH'][w]) / L.med(acc['LOW'][w]))
            for w in (3, 5, 10, 15, 30)) + '\n')

    # ---------------------------------------------------------- symmetry
    print('=' * 78)
    print('SYMMETRY - does HIGH enlarge BOTH excursions together?')
    print('=' * 78)
    for bkey, skey, nm in TOOLS:
        print(nm)
        for b in ('LOW', 'MEDIUM', 'HIGH'):
            ii = [i for i in range(nU) if U[bkey][i] == b]
            if not ii:
                continue
            mf = L.med([U['mfe60'][i] for i in ii])
            ma = L.med([U['mae60'][i] for i in ii])
            print('  %-7s n %7d   med MFE60 %6.2f   med MAE60 %6.2f'
                  '   MFE/MAE %5.3f' % (b, len(ii), mf, ma,
                                        mf / ma if ma else float('nan')))
        print()

    # ---------------------------------------------------------- redundancy
    print('=' * 78)
    print('REDUNDANCY between the two ES tools (never combined)')
    print('=' * 78)
    print('  Spearman(range score, volume score) = %+0.4f\n'
          % L.spearman(U['rr'], U['vr']))

    # ---------------------------------------------------------- tails
    print('=' * 78)
    print('TAIL DESTRUCTION (robustness only - NOT the primary result)')
    print('=' * 78)
    order = sorted(range(nU), key=lambda i: U['abs30'][i])
    for cut, lab in ((0.99, 'drop top 1%'), (0.95, 'drop top 5%')):
        keep = set(order[:int(cut * nU)])
        for bkey, skey, nm in TOOLS:
            mask = [i for i in range(nU) if i in keep]
            res, mono = L.monotone_table(U, bkey, mask, quiet=True)
            if not all(k in res for k in ('LOW', 'MEDIUM', 'HIGH')):
                continue
            print('  %-12s %-18s H-L mean30 %+0.3f   mono %d/5'
                  % (lab, nm, res['HIGH']['mean30'] - res['LOW']['mean30'],
                     sum(mono.values())))
    print()

    # ------------------------------------------------- secondary slices
    print('=' * 78)
    print('DECLARED SECONDARY SLICES')
    print('=' * 78)
    import es_nq_data_spec as SY
    rolls = SY.roll_days()
    mask = [i for i in range(nU) if U['day'][i] not in rolls]
    print('  roll-quarantined slice: %d of %d bars retained' % (len(mask), nU))
    for bkey, skey, nm in TOOLS:
        res, mono = L.monotone_table(U, bkey, mask, quiet=True)
        if all(k in res for k in ('LOW', 'MEDIUM', 'HIGH')):
            print('    %-18s H-L mean30 %+0.3f  mono %d/5'
                  % (nm, res['HIGH']['mean30'] - res['LOW']['mean30'],
                     sum(mono.values())))
    mask = [i for i in range(nU) if U['day'][i] < S.DISCOVERY_START]
    print('  pre-discovery window (< %s): %d bars' % (S.DISCOVERY_START, len(mask)))
    for bkey, skey, nm in TOOLS:
        res, mono = L.monotone_table(U, bkey, mask, quiet=True)
        if all(k in res for k in ('LOW', 'MEDIUM', 'HIGH')):
            print('    %-18s H-L mean30 %+0.3f  mono %d/5'
                  % (nm, res['HIGH']['mean30'] - res['LOW']['mean30'],
                     sum(mono.values())))

    # ------------------- mechanism vs calibration diagnostic
    print('\n' + '=' * 78)
    print('MECHANISM-vs-CALIBRATION DIAGNOSTIC')
    print('  ES-internal terciles of the RAW score. Reported SOLELY to')
    print('  separate the two conclusions. NEVER adopted as thresholds,')
    print('  never used in any other test, creates no new tool.')
    print('=' * 78)
    for bkey, skey, nm in TOOLS:
        lab, t1, t2 = internal_terciles(U, skey)
        U['_int'] = lab
        print('  %s  ES-internal terciles at %.4f / %.4f' % (nm, t1, t2))
        res, mono = L.monotone_table(U, '_int', quiet=True)
        if all(k in res for k in ('LOW', 'MEDIUM', 'HIGH')):
            print('    med30 L/M/H %5.2f/%5.2f/%5.2f   H-L mean30 %+0.3f'
                  '   monotone %d/5'
                  % (res['LOW']['med'][30], res['MEDIUM']['med'][30],
                     res['HIGH']['med'][30],
                     res['HIGH']['mean30'] - res['LOW']['mean30'],
                     sum(mono.values())))
        del U['_int']
    print()

    # ---------------------------------------------------------- verdict
    print('=' * 78)
    print('TRACK A - DECLARED PASS RULES')
    print('=' * 78)
    verdicts = {}
    for bkey, skey, nm in TOOLS:
        r = A.get(nm)
        if r is None:
            verdicts[nm] = 'INSUFFICIENT DATA'
            continue
        sh = shares[nm]
        worst = min(sh[b][1] for b in ('LOW', 'MEDIUM', 'HIGH'))
        c = collections.OrderedDict()
        c['A1 monotone >=4 of 5 horizons'] = sum(r['mono'].values()) >= 4
        c['A2 HIGH-LOW mean30 CI excludes 0'] = r['ci'][0] > 0
        c['A3 day-level permutation p < 0.05'] = r['p_perm'] < 0.05
        c['A4 >=70% months positive'] = r.get('months_pct', 0) >= 70
        c['A5 >=6 of 8 years positive'] = r.get('years_pos', 0) >= 6
        c['A6 ToD-matched retains >=50%'] = r.get('tod_retained', 0) >= 50
        c['A7 every bucket >= 5% occupancy'] = worst >= 5.0
        print('\n  %s' % nm)
        for k, v in c.items():
            print('    %-40s %s' % (k, 'PASS' if v else 'FAIL'))
        mech = all(v for k, v in c.items() if not k.startswith('A7'))
        if all(c.values()):
            verdicts[nm] = 'FULL OUT-OF-MARKET REPLICATION'
        elif mech and not c['A7 every bucket >= 5% occupancy']:
            verdicts[nm] = 'PARTIAL REPLICATION - CALIBRATION DOES NOT TRANSPORT'
        elif not (c['A1 monotone >=4 of 5 horizons']
                  and c['A2 HIGH-LOW mean30 CI excludes 0']
                  and c['A3 day-level permutation p < 0.05']):
            verdicts[nm] = 'FAILED OUT-OF-MARKET REPLICATION'
        else:
            verdicts[nm] = 'PARTIAL REPLICATION'
        print('    ---> %s' % verdicts[nm])
    print('\n' + '=' * 78)
    print('TRACK A VERDICTS')
    for k, v in verdicts.items():
        print('  %-20s %s' % (k, v))
    print('=' * 78)
    print('HISTORICAL RESEARCH ONLY. NOTHING FROZEN WAS MODIFIED.')
    print('THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.')
    return A, verdicts


if __name__ == '__main__':
    run()
