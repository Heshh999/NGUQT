#!/usr/bin/env python3
# ======================================================================
# RVMR-V1 - five-year replication engine
# ======================================================================
#   python3 rvmr_run.py gateA    reproduce MAG_H3_OUTPUT exactly (canonical)
#   python3 rvmr_run.py gateB    pure-OHLCV path vs gateA (canonical year)
#   python3 rvmr_run.py audit    five-year data audit + overlap basis check
#   python3 rvmr_run.py run      full 15-test battery (pre-discovery window)
#
# Everything frozen by rvmr_spec.py. No recalibration anywhere.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, glob, math, random, statistics, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
sys.path.insert(0, os.path.join(HERE, '..', 'mag'))
import rvmr_spec as S

DATA = ('/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce'
        '/scratchpad/rvmr_1m')
HOR = S.HOR


# ---------------------------------------------------------------- stats
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


def day_spearman(days, xs, ys):
    bx = collections.defaultdict(list)
    by = collections.defaultdict(list)
    for d, x, y in zip(days, xs, ys):
        bx[d].append(x)
        by[d].append(y)
    dl = sorted(bx)
    return (dl,
            [statistics.median(bx[d]) for d in dl],
            [statistics.median(by[d]) for d in dl])


def day_perm_p(dx, dy, iters=20000, seed=S.SEED):
    obs = spearman(dx, dy)
    rnd = random.Random(seed)
    cnt = 0
    p = dy[:]
    for _ in range(iters):
        rnd.shuffle(p)
        if abs(spearman(dx, p)) >= abs(obs):
            cnt += 1
    return obs, (cnt + 1.0) / (iters + 1.0)


def day_boot_ci(pairs, iters=20000, seed=S.SEED):
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


def med(x):
    return statistics.median(x) if x else float('nan')


def mean(x):
    return sum(x) / len(x) if x else float('nan')


# ---------------------------------------------------------------- data
def load_bars(pre_discovery_only=False, years=None):
    """Extracted V3 1m bars -> parallel arrays. Stamp convention is
    resolved by the audit; STAMP_SHIFT minutes are added to make the
    stamp a CLOSE stamp as the frozen session map expects."""
    rows = []
    for f in sorted(glob.glob(os.path.join(DATA, 'rvmr_1m_*.csv'))):
        y = os.path.basename(f)[8:12]
        if years and y not in years:
            continue
        for r in csv.reader(open(f)):
            if r[0] == 'et':
                continue
            rows.append(r)
    rows.sort(key=lambda r: r[0])
    out = {'et': [], 'day': [], 'mod': [], 'em': [], 'o': [], 'h': [],
           'l': [], 'c': [], 'v': []}
    epoch = datetime.datetime(2019, 1, 1)
    for r in rows:
        et = r[0]
        if pre_discovery_only and et[:10] >= S.DISCOVERY_START:
            continue
        t = datetime.datetime.strptime(et, '%Y-%m-%d %H:%M:%S') \
            + datetime.timedelta(minutes=STAMP_SHIFT)
        out['et'].append(t.strftime('%Y-%m-%d %H:%M:%S'))
        out['day'].append(t.strftime('%Y-%m-%d'))
        out['mod'].append(t.hour * 60 + t.minute)
        out['em'].append(int((t - epoch).total_seconds() // 60))
        out['o'].append(float(r[1]))
        out['h'].append(float(r[2]))
        out['l'].append(float(r[3]))
        out['c'].append(float(r[4]))
        out['v'].append(float(r[5]))
    return out


STAMP_SHIFT = 0     # set by resolve_stamp() / audit finding


def features(D):
    """Frozen scores + universe + labels on columnar bars."""
    n = len(D['c'])
    rng = [D['h'][i] - D['l'][i] for i in range(n)]
    rr = S.trailing_ratio(rng)
    vr = S.trailing_ratio(D['v'])
    bars = list(zip(D['et'], D['o'], D['h'], D['l'], D['c'], D['v']))
    atr = S.atr20(bars)
    U = {'i': [], 'day': [], 'year': [], 'mod': [], 'rr': [], 'vr': [],
         'rb': [], 'vb': []}
    for h in HOR:
        U['abs%d' % h] = []
        U['rng%d' % h] = []
        U['exc%d' % h] = []
    for j in range(n - 60):
        m = D['mod'][j]
        if not (S.RTH_START <= m <= S.RTH_END and (S.RTH_END - m) >= 60):
            continue
        if atr[j] is None or atr[j] <= 0:
            continue
        if rr[j] is None or vr[j] is None:
            continue
        if D['em'][j + 60] - D['em'][j] != 60:
            continue
        px = D['c'][j]
        hi = lo = px
        mfe = mae = 0.0
        for k in range(1, 61):
            ch, cl = D['h'][j + k], D['l'][j + k]
            if ch > hi:
                hi = ch
            if cl < lo:
                lo = cl
            u = ch - px
            d_ = px - cl
            if u > mfe:
                mfe = u
            if d_ > mae:
                mae = d_
            if k in (5, 10, 15, 30, 60):
                U['abs%d' % k].append(abs(D['c'][j + k] - px))
                U['rng%d' % k].append(hi - lo)
                U['exc%d' % k].append(mfe + mae)
        U['i'].append(j)
        U['day'].append(D['day'][j])
        U['year'].append(D['day'][j][:4])
        U['mod'].append(D['mod'][j])
        U['rr'].append(rr[j])
        U['vr'].append(vr[j])
        U['rb'].append(S.bucket(rr[j]))
        U['vb'].append(S.bucket(vr[j]))
    return U, rng


def sel(U, key, mask=None):
    if mask is None:
        return U[key]
    return [U[key][i] for i in mask]


def monotone_table(U, tool, mask=None, label='', quiet=False):
    """LOW/MED/HIGH medians of abs/rng/exc at all horizons + stats."""
    bk = sel(U, tool, mask)
    idx = collections.defaultdict(list)
    for i, b in enumerate(bk):
        idx[b].append(i if mask is None else mask[i])
    res = {}
    if not quiet:
        print('  %-7s %8s | %s' % ('bucket', 'n', '  '.join(
            '%6dm' % h for h in HOR)))
    for b in ('LOW', 'MEDIUM', 'HIGH'):
        ii = idx[b]
        if not ii:
            continue
        meds = [med([U['abs%d' % h][i] for i in ii]) for h in HOR]
        res[b] = {'n': len(ii), 'med': dict(zip(HOR, meds)),
                  'mean30': mean([U['abs30'][i] for i in ii]), 'ii': ii}
        if not quiet:
            print('  %-7s %8d | %s' % (b, len(ii),
                  '  '.join('%7.2f' % v for v in meds)))
    mono = {h: all(res[a]['med'][h] < res[b_]['med'][h]
                   for a, b_ in (('LOW', 'MEDIUM'), ('MEDIUM', 'HIGH')))
            for h in HOR if all(k in res for k in ('LOW', 'MEDIUM', 'HIGH'))}
    if not quiet and mono:
        print('  monotone LOW<MED<HIGH: %d of %d horizons  %s'
              % (sum(mono.values()), len(mono),
                 ' '.join('%dm:%s' % (h, 'Y' if mono[h] else 'n')
                          for h in HOR)))
    return res, mono


# ================================================================ audit
def audit():
    global STAMP_SHIFT
    print('=' * 78)
    print('RVMR FIVE-YEAR DATA AUDIT  (asset: V3 run151629, Phase-0 audited)')
    D = load_bars()
    n = len(D['c'])
    print('bars %d   first %s   last %s' % (n, D['et'][0], D['et'][-1]))
    dup = n - len(set(D['et']))
    print('duplicate timestamps: %d' % dup)
    mono = all(D['em'][i] < D['em'][i + 1] for i in range(n - 1))
    print('strictly monotonic: %s' % mono)
    # per-year coverage and volume basis
    print('\nper-year bars / median RTH volume / median RTH range:')
    by = collections.defaultdict(lambda: {'n': 0, 'v': [], 'r': []})
    for i in range(n):
        y = D['day'][i][:4]
        by[y]['n'] += 1
        if S.RTH_START <= D['mod'][i] <= S.RTH_END:
            by[y]['v'].append(D['v'][i])
            by[y]['r'].append(D['h'][i] - D['l'][i])
    for y in sorted(by):
        print('  %s  bars %7d   medVol %7.0f   medRng %5.2f'
              % (y, by[y]['n'], med(by[y]['v']), med(by[y]['r'])))
    # session-reopen jumps (roll / gap scan)
    print('\nlargest 18:00-reopen jumps (roll & event scan):')
    jumps = []
    for i in range(1, n):
        if D['em'][i] - D['em'][i - 1] > 60:
            jumps.append((abs(D['o'][i] - D['c'][i - 1]), D['et'][i]))
    for v, t in sorted(jumps, reverse=True)[:10]:
        print('  %8.2f pt   %s' % (v, t))
    print('  (RTH universe windows never span 18:00, so reopen jumps are')
    print('   structurally outside every label window; trailing ratios')
    print('   include them only as one bar of the 1440-bar normaliser)')
    # overlap basis check vs canonical
    print('\nOVERLAP BASIS CHECK vs canonical capture (close-stamped):')
    import cand_spec as CS
    B = CS.load_merged()
    can = {b['et']: b for b in B}
    ov = [i for i in range(n) if D['day'][i] >= S.DISCOVERY_START]
    for shift, nm in ((0, 'as-is'), (1, '+1 min'), (-1, '-1 min')):
        exact = tot = 0
        vr_ = []
        for i in ov[:120000]:
            t = (datetime.datetime.strptime(D['et'][i], '%Y-%m-%d %H:%M:%S')
                 + datetime.timedelta(minutes=shift)).strftime('%Y-%m-%d %H:%M:%S')
            b = can.get(t)
            if b is None:
                continue
            tot += 1
            if (abs(b['open'] - D['o'][i]) < 1e-9 and abs(b['high'] - D['h'][i]) < 1e-9
                    and abs(b['low'] - D['l'][i]) < 1e-9
                    and abs(b['close'] - D['c'][i]) < 1e-9):
                exact += 1
                if b['ofTotalVolume'] > 0:
                    vr_.append(D['v'][i] / b['ofTotalVolume'])
        print('  stamp %-7s matched %6d  exact OHLC %6d (%5.1f%%)  '
              'medVolRatio %s'
              % (nm, tot, exact, 100.0 * exact / max(1, tot),
                 '%.4f' % med(vr_) if vr_ else '-'))
    print('\n  -> pick the shift with ~100%% exact; volume ratio ~1 means the')
    print('     V3 volume basis matches ofTotalVolume on the same bars')


# ================================================================ gates
def gateA():
    """Reproduce MAG_H3_OUTPUT.txt ALT_RNG / ALT_VOL exactly, canonical
    fields + my table code. Exactness gate for the ported machinery."""
    import cand_spec as CS
    import mag_lib as M
    B = CS.load_merged()
    M.build_features(B)
    rows = {'day': [], 'mod': [], 'rr': [], 'vr': [], 'rb': [], 'vb': []}
    for h in HOR:
        rows['abs%d' % h] = []
        rows['rng%d' % h] = []
        rows['exc%d' % h] = []
    for j, b in enumerate(B):
        if not M.eligible(b) or b['mag'] is None:
            continue
        if not M.consec(B, j, 60):
            continue
        px = b['close']
        hi = lo = px
        mfe = mae = 0.0
        for k in range(1, 61):
            c = B[j + k]
            hi = max(hi, c['high'])
            lo = min(lo, c['low'])
            mfe = max(mfe, c['high'] - px)
            mae = max(mae, px - c['low'])
            if k in (5, 10, 15, 30, 60):
                rows['abs%d' % k].append(abs(c['close'] - px))
                rows['rng%d' % k].append(hi - lo)
                rows['exc%d' % k].append(mfe + mae)
        rows['day'].append(b['day'])
        rows['mod'].append(0)
        rows['rr'].append(b['mag_rng'])
        rows['vr'].append(b['mag_vol'])
        rows['rb'].append(S.bucket(b['mag_rng']))
        rows['vb'].append(S.bucket(b['mag_vol']))
    print('gateA universe: %d rows (archive: 83596)' % len(rows['rr']))
    ok = len(rows['rr']) == 83596
    # archive targets, parsed from MAG_H3_OUTPUT.txt
    import re
    arch = open(os.path.join(HERE, '..', 'mag', 'MAG_H3_OUTPUT.txt')).read()
    for tool, tag in (('rb', 'MAG_ALT_RNG'), ('vb', 'MAG_ALT_VOL')):
        blk = arch[arch.index(tag):]
        want = {}
        for bk in ('LOW', 'MEDIUM', 'HIGH'):
            m = re.search(r'%s\s+(\d+) \|\s+([\d.]+)' % bk, blk)
            want[bk] = (int(m.group(1)), float(m.group(2)))
        res, mono = monotone_table(rows, tool, label=tag, quiet=True)
        sp = spearman(rows['rr' if tool == 'rb' else 'vr'], rows['abs30'])
        m2 = re.search(r'Spearman\(\w+, \|ret\|@30m\) = ([+\-\d.]+)', blk)
        print('%s' % tag)
        for bk in ('LOW', 'MEDIUM', 'HIGH'):
            gn, g5 = res[bk]['n'], res[bk]['med'][5]
            wn, w5 = want[bk]
            # The archive printed medians at ONE decimal ('%5.1f'), so a
            # quarter-point median (9.75) appears as 9.8. Equality is
            # therefore tested in the archive's own print format - exact
            # string match at printed precision, no tolerance fudging.
            good = (gn == wn and ('%.1f' % g5) == ('%.1f' % w5))
            ok &= good
            print('  %-7s n %6d (archive %6d)   med|ret|5m %6.2f (archive %6.2f)  %s'
                  % (bk, gn, wn, g5, w5, 'PASS' if good else 'FAIL'))
        good = abs(sp - float(m2.group(1))) < 5e-4
        ok &= good
        print('  Spearman@30m %+.4f (archive %s)  %s'
              % (sp, m2.group(1), 'PASS' if good else 'FAIL'))
    print('GATE A: %s' % ('PASS - ported machinery is exact' if ok else
                          'FAIL - STOP, five-year replication not run'))
    return ok


def gateB():
    """Pure-OHLCV pipeline on the canonical year, compared to gateA's
    canonical-field universe. Quantifies the three basis translations."""
    import cand_spec as CS
    B = CS.load_merged()
    D = {'et': [], 'day': [], 'mod': [], 'em': [], 'o': [], 'h': [],
         'l': [], 'c': [], 'v': []}
    epoch = datetime.datetime(2019, 1, 1)
    bad_rng = 0
    for b in B:
        t = datetime.datetime.strptime(b['et'], '%Y-%m-%d %H:%M:%S')
        D['et'].append(b['et'])
        D['day'].append(b['day'])
        D['mod'].append(t.hour * 60 + t.minute)
        D['em'].append(int((t - epoch).total_seconds() // 60))
        D['o'].append(b['open'])
        D['h'].append(b['high'])
        D['l'].append(b['low'])
        D['c'].append(b['close'])
        D['v'].append(b['ofTotalVolume'])
        if abs((b['high'] - b['low']) - b['rng']) > 1e-6:
            bad_rng += 1
    print("gateB: canonical 'rng' equals high-low on all but %d bars" % bad_rng)
    U, _ = features(D)
    print('gateB universe: %d rows (gateA: 83596, delta %+d)'
          % (len(U['rr']), len(U['rr']) - 83596))
    for tool, tag in (('rb', 'RANGE'), ('vb', 'VOLUME')):
        res, mono = monotone_table(U, tool, quiet=True)
        sp = spearman(U['rr' if tool == 'rb' else 'vr'], U['abs30'])
        print('%s-REGIME-V1 pure-OHLCV: ' % tag + '  '.join(
            '%s n%d med5 %.2f' % (bk, res[bk]['n'], res[bk]['med'][5])
            for bk in ('LOW', 'MEDIUM', 'HIGH') if bk in res)
            + '   Spearman@30m %+.4f' % sp)
    print('(differences vs gateA quantify translations T1-T3 in the spec;')
    print(' medians within noise and Spearman within ~0.01 = OHLCV path OK)')


# ============================================================== battery
def run(shift):
    global STAMP_SHIFT
    STAMP_SHIFT = shift
    print('=' * 78)
    print('RVMR-V1 FIVE-YEAR BATTERY   stamp shift %+d min   window < %s'
          % (shift, S.DISCOVERY_START))
    print('MULTI-YEAR HISTORICAL REPLICATION (backward out-of-sample).')
    print('NOT prospective validation - the data PRECEDES the discovery.')
    print('=' * 78)
    D = load_bars(pre_discovery_only=True)
    print('bars %d   %s .. %s' % (len(D['c']), D['et'][0], D['et'][-1]))
    U, rngall = features(D)
    nU = len(U['rr'])
    days = sorted(set(U['day']))
    print('universe %d eligible bars, %d days\n' % (nU, len(days)))

    tools = (('rb', 'rr', 'RANGE-REGIME-V1'), ('vb', 'vr', 'VOLUME-REGIME-V1'))

    # ------------------------------------------------------- T1
    print('TEST 1 - FIVE-YEAR MONOTONICITY (median |ret|, points)')
    T1res = {}
    for bkey, skey, nm in tools:
        print(nm)
        res, mono = monotone_table(U, bkey)
        T1res[nm] = (res, mono)
        hl = [(U['day'][i], U['abs30'][i]) for i in res['HIGH']['ii']]
        ll = [(U['day'][i], U['abs30'][i]) for i in res['LOW']['ii']]
        chi = day_boot_ci(hl, iters=5000)
        clo = day_boot_ci(ll, iters=5000)
        d30 = res['HIGH']['mean30'] - res['LOW']['mean30']
        print('  mean|ret|@30  HIGH %.2f CI[%.2f,%.2f]  LOW %.2f CI[%.2f,%.2f]'
              '  HIGH-LOW %+.2f  H/L %.2fx  H/M %.2fx\n'
              % (res['HIGH']['mean30'], chi[0], chi[1],
                 res['LOW']['mean30'], clo[0], clo[1], d30,
                 res['HIGH']['mean30'] / res['LOW']['mean30'],
                 res['HIGH']['mean30'] / res['MEDIUM']['mean30']))

    # ------------------------------------------------------- T2
    print('TEST 2 - YEAR-BY-YEAR MONOTONE MATRIX (Y = LOW<MED<HIGH strict)')
    years = sorted(set(U['year']))
    for bkey, skey, nm in tools:
        print(nm)
        print('  year   ' + '  '.join('%3dm' % h for h in HOR)
              + '   n(H) medH30 medL30')
        for y in years:
            mask = [i for i in range(nU) if U['year'][i] == y]
            res, mono = monotone_table(U, bkey, mask, quiet=True)
            if not mono:
                print('  %s  insufficient buckets' % y)
                continue
            print('  %s   ' % y + '   '.join(
                ('Y' if mono[h] else 'n') for h in HOR)
                + '   %5d %6.2f %6.2f'
                % (res['HIGH']['n'], res['HIGH']['med'][30], res['LOW']['med'][30]))
        print()

    # ------------------------------------------------------- T3
    print('TEST 3 - SPEARMAN STABILITY (score vs |ret|@30m)')
    for bkey, skey, nm in tools:
        full = spearman(U[skey], U['abs30'])
        dl, dx, dy = day_spearman(U['day'], U[skey], U['abs30'])
        obs, p = day_perm_p(dx, dy, iters=20000)
        # day-bootstrap CI on the day-level Spearman
        rnd = random.Random(S.SEED)
        bs = []
        for _ in range(2000):
            ii = [rnd.randrange(len(dx)) for _ in range(len(dx))]
            bs.append(spearman([dx[k] for k in ii], [dy[k] for k in ii]))
        bs.sort()
        print('%s  full-sample %+0.4f   day-level %+0.4f  perm p %.5f  '
              'CI[%+.3f,%+.3f]' % (nm, full, obs, p,
                                   bs[int(.025 * len(bs))], bs[int(.975 * len(bs))]))
        for y in years:
            mask = [i for i in range(nU) if U['year'][i] == y]
            fy = spearman([U[skey][i] for i in mask], [U['abs30'][i] for i in mask])
            dl2, dx2, dy2 = day_spearman([U['day'][i] for i in mask],
                                         [U[skey][i] for i in mask],
                                         [U['abs30'][i] for i in mask])
            o2, p2 = day_perm_p(dx2, dy2, iters=5000)
            print('    %s  full %+0.4f   day %+0.4f  p %.4f  (%d days)'
                  % (y, fy, o2, p2, len(dl2)))
        print()

    # ------------------------------------------------------- T4
    print('TEST 4 - VOLATILITY-ERA ROBUSTNESS (months split by median')
    print('         daily RTH range, DIAGNOSTIC slicing only)')
    dayrng = {}
    byd = collections.defaultdict(lambda: [1e18, -1e18])
    for i in range(len(D['c'])):
        if S.RTH_START <= D['mod'][i] <= S.RTH_END:
            d = D['day'][i]
            byd[d][0] = min(byd[d][0], D['l'][i])
            byd[d][1] = max(byd[d][1], D['h'][i])
    for d, (lo, hi) in byd.items():
        dayrng[d] = hi - lo
    bym = collections.defaultdict(list)
    for d, r in dayrng.items():
        bym[d[:7]].append(r)
    mrank = sorted(bym, key=lambda m: med(bym[m]))
    n3 = len(mrank) // 3
    era = {}
    for k, m in enumerate(mrank):
        era[m] = 'QUIET' if k < n3 else ('MID' if k < 2 * n3 else 'VOLATILE')
    for bkey, skey, nm in tools:
        print(nm)
        for e in ('QUIET', 'MID', 'VOLATILE'):
            mask = [i for i in range(nU) if era.get(U['day'][i][:7]) == e]
            res, mono = monotone_table(U, bkey, mask, quiet=True)
            if 'HIGH' not in res or 'LOW' not in res:
                print('  %-8s no HIGH or LOW bars' % e)
                continue
            dl2, dx2, dy2 = day_spearman([U['day'][i] for i in mask],
                                         [U[skey][i] for i in mask],
                                         [U['abs30'][i] for i in mask])
            print('  %-8s n %6d  L/M/H %6d/%6d/%6d  med30 %5.2f/%5.2f/%5.2f'
                  '  monotone %d/5  daySp %+0.3f'
                  % (e, len(mask), res['LOW']['n'], res['MEDIUM']['n'],
                     res['HIGH']['n'], res['LOW']['med'][30],
                     res['MEDIUM']['med'][30], res['HIGH']['med'][30],
                     sum(mono.values()), spearman(dx2, dy2)))
        print()

    # ------------------------------------------------------- T5
    print('TEST 5 - TIME-OF-DAY ROBUSTNESS (predeclared buckets)')
    tod = (('OPEN 0930-1030', 570, 630), ('MIDMORN 1030-1200', 630, 720),
           ('MIDDAY 1200-1330', 720, 810), ('AFTERNOON 1330-1500', 810, 900))
    for bkey, skey, nm in tools:
        print(nm)
        for lab, a, b in tod:
            mask = [i for i in range(nU) if a <= U['mod'][i] < b]
            res, mono = monotone_table(U, bkey, mask, quiet=True)
            if 'HIGH' not in res or 'LOW' not in res:
                continue
            print('  %-18s n %6d  med30 L/M/H %5.2f/%5.2f/%5.2f  mono %d/5'
                  % (lab, len(mask), res['LOW']['med'][30],
                     res['MEDIUM']['med'][30], res['HIGH']['med'][30],
                     sum(mono.values())))
        print()

    # ------------------------------------------------------- T6
    print('TEST 6 - PERSISTENCE (mean 1m range per minute AFTER the state)')
    persist = {}
    for bkey, skey, nm in tools:
        print(nm)
        acc = collections.defaultdict(lambda: collections.defaultdict(list))
        for r_ in range(nU):
            j = U['i'][r_]
            for w in (3, 5, 10, 15, 30):
                acc[U[bkey][r_]][w].append(
                    sum(rngall[j + t] for t in range(1, w + 1)) / w)
        print('  %-7s ' % 'bucket' + '  '.join('+%-3dm' % w
                                               for w in (3, 5, 10, 15, 30)))
        for bk in ('LOW', 'MEDIUM', 'HIGH'):
            print('  %-7s ' % bk + '  '.join(
                '%5.2f' % med(acc[bk][w]) for w in (3, 5, 10, 15, 30)))
        ratio = {w: med(acc['HIGH'][w]) / med(acc['LOW'][w])
                 for w in (3, 5, 10, 15, 30)}
        persist[nm] = ratio
        print('  H/L ratio ' + '  '.join('%5.2f' % ratio[w]
                                         for w in (3, 5, 10, 15, 30)) + '\n')

    # ------------------------------------------------------- T7
    print('TEST 7 - HEAD-TO-HEAD (identical universe)')
    fr = spearman(U['rr'], U['abs30'])
    fv = spearman(U['vr'], U['abs30'])
    print('  full Spearman@30   RANGE %+0.4f   VOLUME %+0.4f' % (fr, fv))
    rA = T1res['RANGE-REGIME-V1'][0]
    rB = T1res['VOLUME-REGIME-V1'][0]
    print('  HIGH-LOW mean@30   RANGE %+0.2f    VOLUME %+0.2f'
          % (rA['HIGH']['mean30'] - rA['LOW']['mean30'],
             rB['HIGH']['mean30'] - rB['LOW']['mean30']))
    print('  H/L ratio @+30m persistence   RANGE %.2f   VOLUME %.2f\n'
          % (persist['RANGE-REGIME-V1'][30], persist['VOLUME-REGIME-V1'][30]))

    # ------------------------------------------------------- T8
    print('TEST 8 - REDUNDANCY')
    sc = spearman(U['rr'], U['vr'])
    agree = sum(1 for i in range(nU) if U['rb'][i] == U['vb'][i])
    hr = [i for i in range(nU) if U['rb'][i] == 'HIGH']
    hv = [i for i in range(nU) if U['vb'][i] == 'HIGH']
    hs = set(hv)
    pvh = sum(1 for i in hr if i in hs) / max(1, len(hr))
    hs2 = set(hr)
    prh = sum(1 for i in hv if i in hs2) / max(1, len(hv))
    print('  Spearman(range score, volume score) %+0.4f' % sc)
    print('  bucket agreement %.1f%%   P(VOL HIGH|RNG HIGH) %.1f%%   '
          'P(RNG HIGH|VOL HIGH) %.1f%%' % (100.0 * agree / nU,
                                           100 * pvh, 100 * prh))
    print('  cross-tab  n / median |ret|@30:')
    print('  %-12s %14s %14s %14s' % ('', 'VOL LOW', 'VOL MEDIUM', 'VOL HIGH'))
    for rb in ('LOW', 'MEDIUM', 'HIGH'):
        cells = []
        for vb in ('LOW', 'MEDIUM', 'HIGH'):
            ii = [i for i in range(nU) if U['rb'][i] == rb and U['vb'][i] == vb]
            cells.append('%6d %6.2f' % (len(ii),
                         med([U['abs30'][i] for i in ii])) if ii else '     -      -')
        print('  RNG %-8s %14s %14s %14s' % (rb, *cells))
    print()

    # ------------------------------------------------------- T9
    print('TEST 9 - INCREMENTAL VALUE (frozen classes, no new thresholds)')
    for a, b, nm in (('rb', 'vb', 'VOLUME within RANGE buckets'),
                     ('vb', 'rb', 'RANGE within VOLUME buckets')):
        print('  %s:' % nm)
        for outer in ('LOW', 'MEDIUM', 'HIGH'):
            meds = []
            for inner in ('LOW', 'MEDIUM', 'HIGH'):
                ii = [i for i in range(nU)
                      if U[a][i] == outer and U[b][i] == inner]
                meds.append(med([U['abs30'][i] for i in ii]) if ii else None)
            ok_ = (None not in meds and meds[0] < meds[1] < meds[2])
            print('    outer %-7s inner med30 %s   monotone %s'
                  % (outer, ' / '.join('%6.2f' % m if m else '     -'
                                       for m in meds),
                     'Y' if ok_ else 'n'))
    # rank regression, point estimate
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos
        return r
    zr, zv, zy = rank(U['rr']), rank(U['vr']), rank(U['abs30'])
    n_ = float(nU)
    mzr, mzv, mzy = sum(zr) / n_, sum(zv) / n_, sum(zy) / n_
    srr = sum((x - mzr) ** 2 for x in zr)
    svv = sum((x - mzv) ** 2 for x in zv)
    srv = sum((a2 - mzr) * (b2 - mzv) for a2, b2 in zip(zr, zv))
    sry = sum((a2 - mzr) * (b2 - mzy) for a2, b2 in zip(zr, zy))
    svy = sum((a2 - mzv) * (b2 - mzy) for a2, b2 in zip(zv, zy))
    det = srr * svv - srv * srv
    b_r = (svv * sry - srv * svy) / det
    b_v = (srr * svy - srv * sry) / det
    print('  bivariate rank regression |ret|@30 ~ range + volume:')
    print('    beta_range %+.4f   beta_volume %+.4f  '
          '(standardized rank OLS, point estimates)\n' % (b_r, b_v))

    # ------------------------------------------------------- T10
    print('TEST 10 - TRANSITIONS / HIGH persistence (diagnostic)')
    for bkey, skey, nm in tools:
        runs, stay1, stay3, stay5 = [], [], [], []
        enter, cont = [], []
        cur = 0
        for r_ in range(nU):
            prev_ok = (r_ > 0 and U['day'][r_ - 1] == U['day'][r_]
                       and U['mod'][r_] - U['mod'][r_ - 1] == 1)
            b = U[bkey][r_]
            pb = U[bkey][r_ - 1] if prev_ok else None
            if b == 'HIGH':
                if pb == 'HIGH':
                    cur += 1
                    cont.append(U['abs30'][r_])
                else:
                    if cur:
                        runs.append(cur)
                    cur = 1
                    enter.append(U['abs30'][r_])
            else:
                if cur:
                    runs.append(cur)
                cur = 0
            if prev_ok and pb == 'HIGH':
                stay1.append(1 if b == 'HIGH' else 0)
            if r_ >= 3 and all(U['day'][r_ - k] == U['day'][r_] for k in (1, 2, 3)) \
               and U['mod'][r_] - U['mod'][r_ - 3] == 3 and U[bkey][r_ - 3] == 'HIGH':
                stay3.append(1 if b == 'HIGH' else 0)
            if r_ >= 5 and all(U['day'][r_ - k] == U['day'][r_] for k in range(1, 6)) \
               and U['mod'][r_] - U['mod'][r_ - 5] == 5 and U[bkey][r_ - 5] == 'HIGH':
                stay5.append(1 if b == 'HIGH' else 0)
        if cur:
            runs.append(cur)
        print('%s  HIGH runs: median %s  mean %.1f bars   '
              'P(stay) 1bar %.1f%%  3bar %.1f%%  5bar %.1f%%'
              % (nm, med(runs), mean(runs), 100 * mean(stay1),
                 100 * mean(stay3), 100 * mean(stay5)))
        print('    |ret|@30 median: ENTERING HIGH %.2f (n %d)  '
              'STAYING HIGH %.2f (n %d)'
              % (med(enter), len(enter), med(cont), len(cont)))
    print()

    # ------------------------------------------------------- T11
    print('TEST 11 - SELECTIVITY / BASE RATES (share of eligible bars)')
    for bkey, skey, nm in tools:
        cnt = collections.Counter(U[bkey])
        print('%s  full: L %.1f%%  M %.1f%%  H %.1f%%'
              % (nm, 100.0 * cnt['LOW'] / nU, 100.0 * cnt['MEDIUM'] / nU,
                 100.0 * cnt['HIGH'] / nU))
        for y in years:
            cy = collections.Counter(U[bkey][i] for i in range(nU)
                                     if U['year'][i] == y)
            t = sum(cy.values())
            print('    %s  L %5.1f%%  M %5.1f%%  H %5.1f%%'
                  % (y, 100.0 * cy['LOW'] / t, 100.0 * cy['MEDIUM'] / t,
                     100.0 * cy['HIGH'] / t))
    print()

    # ------------------------------------------------------- T12
    print('TEST 12 - EXTREME YEARS (chosen by realized range, not by RVMR)')
    yr_rng = {y: med([dayrng[d] for d in dayrng if d[:4] == y])
              for y in years}
    hi_y = max(yr_rng, key=yr_rng.get)
    lo_y = min(yr_rng, key=yr_rng.get)
    print('  most volatile %s (med daily RTH range %.1f)   least %s (%.1f)'
          % (hi_y, yr_rng[hi_y], lo_y, yr_rng[lo_y]))
    for y in (hi_y, lo_y):
        for bkey, skey, nm in tools:
            mask = [i for i in range(nU) if U['year'][i] == y]
            res, mono = monotone_table(U, bkey, mask, quiet=True)
            print('    %s %-16s med30 L/M/H %5.2f/%5.2f/%5.2f  mono %d/5'
                  % (y, nm, res['LOW']['med'][30], res['MEDIUM']['med'][30],
                     res['HIGH']['med'][30], sum(mono.values())))
    print()

    # ------------------------------------------------------- T13
    print('TEST 13 - MONTH STABILITY (HIGH-LOW median |ret|@30 per month)')
    for bkey, skey, nm in tools:
        eff = []
        for m in sorted(set(d[:7] for d in U['day'])):
            hi_ = [U['abs30'][i] for i in range(nU)
                   if U['day'][i][:7] == m and U[bkey][i] == 'HIGH']
            lo_ = [U['abs30'][i] for i in range(nU)
                   if U['day'][i][:7] == m and U[bkey][i] == 'LOW']
            if len(hi_) >= 20 and len(lo_) >= 20:
                eff.append((med(hi_) - med(lo_), m))
        pos = sum(1 for e, _ in eff if e > 0)
        eff.sort()
        print('%s  months %d  positive %d (%.0f%%)  median %+0.2f  '
              'worst %+0.2f (%s)  best %+0.2f (%s)'
              % (nm, len(eff), pos, 100.0 * pos / len(eff),
                 med([e for e, _ in eff]), eff[0][0], eff[0][1],
                 eff[-1][0], eff[-1][1]))
    print()

    # ------------------------------------------------------- T14
    print('TEST 14 - LEAVE-ONE-YEAR-OUT (display, nothing refit)')
    for bkey, skey, nm in tools:
        print(nm)
        for y in years:
            inm = [i for i in range(nU) if U['year'][i] != y]
            outm = [i for i in range(nU) if U['year'][i] == y]
            ri, _ = monotone_table(U, bkey, inm, quiet=True)
            ro, _ = monotone_table(U, bkey, outm, quiet=True)
            print('  omit %s   rest H-L %+6.2f   omitted-year H-L %+6.2f'
                  % (y, ri['HIGH']['med'][30] - ri['LOW']['med'][30],
                     ro['HIGH']['med'][30] - ro['LOW']['med'][30]))
        print()

    # ------------------------------------------------------- T15
    print('TEST 15 - PLACEBO / ARTIFACT DECOMPOSITION')
    for bkey, skey, nm in tools:
        res = T1res[nm][0]
        pooled = res['HIGH']['med'][30] - res['LOW']['med'][30]
        # (a) within time-of-day-slot separation: kills a pure ToD artifact
        slots = collections.defaultdict(lambda: {'H': [], 'L': []})
        for i in range(nU):
            if U[bkey][i] == 'HIGH':
                slots[U['mod'][i]]['H'].append(U['abs30'][i])
            elif U[bkey][i] == 'LOW':
                slots[U['mod'][i]]['L'].append(U['abs30'][i])
        w, tot = 0.0, 0
        for m2, g in slots.items():
            if len(g['H']) >= 10 and len(g['L']) >= 10:
                k = len(g['H']) + len(g['L'])
                w += (med(g['H']) - med(g['L'])) * k
                tot += k
        todm = w / tot if tot else float('nan')
        # (b) 3-trading-day-lagged label
        bydm = {}
        for i in range(nU):
            bydm[(U['day'][i], U['mod'][i])] = U[bkey][i]
        dlist = sorted(set(U['day']))
        dpos = {d: k for k, d in enumerate(dlist)}
        lagH, lagL = [], []
        for i in range(nU):
            k = dpos[U['day'][i]]
            if k < 3:
                continue
            lb = bydm.get((dlist[k - 3], U['mod'][i]))
            if lb == 'HIGH':
                lagH.append(U['abs30'][i])
            elif lb == 'LOW':
                lagL.append(U['abs30'][i])
        print('%s  pooled H-L %+0.2f   ToD-matched %+0.2f (%.0f%% retained)'
              '   3-day-lag label %+0.2f'
              % (nm, pooled, todm, 100.0 * todm / pooled if pooled else 0,
                 med(lagH) - med(lagL)))
    print('  (day-shuffled permutation p is TEST 3; ToD-matched separation')
    print('   rules out a pure time-of-day artifact; the lagged label shows')
    print('   how much is slow multi-day volatility clustering vs local state)')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'audit'
    if cmd == 'audit':
        audit()
    elif cmd == 'gateA':
        gateA()
    elif cmd == 'gateB':
        gateB()
    elif cmd == 'run':
        run(int(sys.argv[sys.argv.index('--shift') + 1])
            if '--shift' in sys.argv else 0)
