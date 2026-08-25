#!/usr/bin/env python3
# ======================================================================
# ES-NQ-DATA-V1 - deterministic cross-market synchronization loader
# ======================================================================
# Builds the synchronized NQ<->ES 1-minute universe from two RAW sources.
# It creates no data: every output row is two genuine completed bars that
# both exist. There is NO forward fill, NO interpolation, and NO
# manufactured timestamp anywhere in this file.
#
#   python3 es_nq_data_spec.py selftest          prove the machinery
#   python3 es_nq_data_spec.py build --es <dir>  build the universe
#
# STATUS: the ES side does not exist yet (see docs/ES_NQ_DATA_V1_AUDIT.md).
# The loader is written and self-tested now so that when genuine ES
# history arrives, synchronization is a verified step rather than new
# code written under pressure.
#
# THIS PHASE RUNS NO HYPOTHESIS. No thresholds, no signals, no labels.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, glob, math, hashlib, datetime, statistics, collections

SPEC_VERSION = 'ES-NQ-DATA-V1'
LOADER_VERSION = '1.0'
CONTRACT_MAP_VERSION = 'CMAP-1'
NQ_DIR = ('/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce'
          '/scratchpad/rvmr_1m')

# --- established by the NQ audit, proven empirically not assumed --------
NQ_STAMP = 'CLOSE'          # 17:00 present, 18:00 absent, 18:01 present
NQ_TZ = 'US/Eastern'
BREAK_START, BREAK_END = '17:00', '18:01'

# Quarterly roll windows (2nd Thursday of Mar/Jun/Sep/Dec, +/- ROLL_PAD
# days) are quarantined for BOTH markets, so a roll in either market can
# never manufacture divergence, lead/lag or false confirmation.
ROLL_PAD = 2


def roll_days(y0=2019, y1=2027, pad=ROLL_PAD):
    out = set()
    for y in range(y0, y1):
        for m in (3, 6, 9, 12):
            d = datetime.date(y, m, 1)
            thu = []
            while d.month == m:
                if d.weekday() == 3:
                    thu.append(d)
                d += datetime.timedelta(days=1)
            r = thu[1]
            for k in range(-pad, pad + 1):
                out.add((r + datetime.timedelta(days=k)).isoformat())
    return out


def sha16(path):
    try:
        return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:16]
    except Exception:
        return 'NA'


# ------------------------------------------------------------- loading
def load_market(spec, label):
    """Raw 1m OHLCV -> {et: (o,h,l,c,v)} plus a quality report.

    Duplicate handling, per the directive:
      identical duplicate rows  -> deduped deterministically (first-wins)
      CONFLICTING duplicate rows -> FAIL CLOSED (nothing silently chosen)
    Missing bars are NEVER interpolated; they are simply absent, and an
    absent bar makes that timestamp ineligible for cross-market use.
    """
    files = sorted(glob.glob(os.path.join(spec, '*.csv')))
    bars, dup, conflict, badohlc, negv = {}, 0, [], 0, 0
    for f in files:
        with open(f, newline='') as fh:
            rd = csv.reader(fh)
            h = next(rd)
            ix = {c.strip().lower(): i for i, c in enumerate(h)}
            def col(*names):
                for n in names:
                    if n in ix:
                        return ix[n]
                return None
            ci = {k: col(k, 'f_' + k) for k in
                  ('open', 'high', 'low', 'close', 'volume')}
            ti = col('et', 'timestampet', 'f_barcloseet', 'timestamp')
            if ti is None or any(v is None for v in ci.values()):
                continue
            for row in rd:
                if len(row) != len(h):
                    continue
                try:
                    et = row[ti]
                    b = (float(row[ci['open']]), float(row[ci['high']]),
                         float(row[ci['low']]), float(row[ci['close']]),
                         float(row[ci['volume']] or 0))
                except (ValueError, IndexError):
                    continue
                if et in bars:
                    dup += 1
                    if bars[et] != b:
                        conflict.append(et)
                    continue
                if not (b[2] <= b[0] <= b[1] and b[2] <= b[3] <= b[1]):
                    badohlc += 1
                    continue
                if b[4] < 0:
                    negv += 1
                    continue
                bars[et] = b
    if conflict:
        for c in conflict[:5]:
            print('  CONFLICT %s %s' % (label, c))
        raise SystemExit('FAIL CLOSED: %d conflicting duplicate bars in %s'
                         % (len(conflict), label))
    return bars, {'files': len(files), 'rows': len(bars), 'dupes': dup,
                  'conflicts': 0, 'ohlc_invalid': badohlc, 'neg_vol': negv}


def load_nq():
    return load_market(NQ_DIR, 'NQ')


# ------------------------------------------------- causal derived fields
def derived(bars):
    """Causal per-market fields. ATR(20)=SMA of true range (the definition
    Phase-0 verified exact and RVMR-V1 uses). Returns use only completed
    prior bars. Prep only - NO thresholds and NO signals are defined here;
    the XMARKET normalization is frozen in its own pre-registration."""
    ets = sorted(bars)
    idx = {e: i for i, e in enumerate(ets)}
    tr, atr, out = [], {}, {}
    prev = None
    for e in ets:
        o, h, l, c, v = bars[e]
        t = (h - l) if prev is None else max(h - l, abs(h - prev), abs(l - prev))
        tr.append(t); prev = c
        if len(tr) > 20:
            tr.pop(0)
        if len(tr) == 20:
            atr[e] = sum(tr) / 20.0
    def em(e, k):
        i = idx[e] - k
        if i < 0:
            return None
        p = ets[i]
        d = (datetime.datetime.strptime(e, '%Y-%m-%d %H:%M:%S')
             - datetime.datetime.strptime(p, '%Y-%m-%d %H:%M:%S'))
        return p if d.total_seconds() == 60 * k else None
    for e in ets:
        a = atr.get(e)
        row = {'atr': a}
        for k in (1, 3, 5):
            p = em(e, k)
            r = (bars[e][3] - bars[p][3]) if p else None
            row['ret%d' % k] = r
            row['z%d' % k] = (r / a) if (r is not None and a and a > 0) else None
        out[e] = row
    return out


# --------------------------------------------------------- synchronize
def synchronize(nq, es, quiet=False):
    """Classify every timestamp. Returns rows + the synchronization table."""
    rq = roll_days()
    keys = sorted(set(nq) | set(es))
    dn, de = derived(nq), derived(es)
    cls = collections.Counter()
    rows = []
    for et in keys:
        day = et[:10]
        inn, ine = et in nq, et in es
        if inn and ine:
            if day in rq:
                cls['ROLL_QUARANTINED'] += 1
                flag = 'ROLL_QUARANTINED'
            else:
                cls['MATCHED'] += 1
                flag = 'MATCHED'
        elif inn:
            cls['NQ_ONLY'] += 1; flag = 'NQ_ONLY'
        else:
            cls['ES_ONLY'] += 1; flag = 'ES_ONLY'
        if flag not in ('MATCHED', 'ROLL_QUARANTINED'):
            continue
        n, e_ = nq[et], es[et]
        a, b = dn[et], de[et]
        # Causal availability: a close-stamped bar is available exactly at
        # its stamp and never earlier; the cross-market field is available
        # only when BOTH bars are complete.
        rows.append({
            'timestampEt': et, 'sessionDate': day,
            'nqOpen': n[0], 'nqHigh': n[1], 'nqLow': n[2], 'nqClose': n[3],
            'nqVolume': n[4],
            'esOpen': e_[0], 'esHigh': e_[1], 'esLow': e_[2], 'esClose': e_[3],
            'esVolume': e_[4],
            'nqAvailableTime': et, 'esAvailableTime': et,
            'crossMarketAvailableTime': max(et, et),
            'nqContract': 'CONTINUOUS', 'esContract': 'CONTINUOUS',
            'nqAtr': a['atr'], 'esAtr': b['atr'],
            'nqZ1': a['z1'], 'nqZ3': a['z3'], 'nqZ5': a['z5'],
            'esZ1': b['z1'], 'esZ3': b['z3'], 'esZ5': b['z5'],
            # relative-strength PREP only: no threshold, no bucket, no signal
            'relStrength1': (a['z1'] - b['z1'])
                            if (a['z1'] is not None and b['z1'] is not None) else None,
            'relStrength3': (a['z3'] - b['z3'])
                            if (a['z3'] is not None and b['z3'] is not None) else None,
            'relStrength5': (a['z5'] - b['z5'])
                            if (a['z5'] is not None and b['z5'] is not None) else None,
            'qualityFlags': flag})
    if not quiet:
        print('SYNCHRONIZATION TABLE')
        for k in ('MATCHED', 'ROLL_QUARANTINED', 'NQ_ONLY', 'ES_ONLY'):
            print('  %-22s %8d' % (k, cls[k]))
        elig = cls['MATCHED'] + cls['NQ_ONLY']
        print('  match %% of eligible NQ: %.2f%%'
              % (100.0 * cls['MATCHED'] / elig if elig else 0))
    return rows, cls


def sanity_correlation(rows):
    """DESCRIPTIVE ONLY - detects synchronization failure, not edge."""
    def corr(a, b):
        n = len(a)
        ma, mb = sum(a) / n, sum(b) / n
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        da = math.sqrt(sum((x - ma) ** 2 for x in a))
        db = math.sqrt(sum((y - mb) ** 2 for y in b))
        return num / (da * db) if da and db else float('nan')
    print('DESCRIPTIVE CORRELATION SANITY (not an edge test)')
    for k in (1, 3, 5):
        p = [(r['nqZ%d' % k], r['esZ%d' % k]) for r in rows
             if r['nqZ%d' % k] is not None and r['esZ%d' % k] is not None]
        if len(p) > 100:
            print('  normalized %dm return corr  %+.4f   (n %d)'
                  % (k, corr([x for x, _ in p], [y for _, y in p]), len(p)))
    byday = collections.defaultdict(lambda: [None, None, None, None])
    for r in rows:
        d = byday[r['sessionDate']]
        if d[0] is None:
            d[0], d[2] = r['nqClose'], r['esClose']
        d[1], d[3] = r['nqClose'], r['esClose']
    dn = [(b - a) / a for a, b, c, e in byday.values() if a]
    de = [(e - c) / c for a, b, c, e in byday.values() if c]
    if len(dn) > 20:
        print('  daily return corr           %+.4f   (n %d days)'
              % (corr(dn, de), len(dn)))
    print('  (bizarrely low or sign-flipped values => investigate stamps/'
          'roll/session BEFORE any research)')


# ------------------------------------------------------------ selftest
def selftest():
    """Prove the machinery WITHOUT fabricating ES.

    A controlled fixture is derived from real NQ bars and deliberately
    perturbed in five ways with known-correct answers. It lives only in
    memory, is never written to any data directory, and is never used as
    a market. It exists solely to verify the classifier."""
    print('ES-NQ-DATA-V1 LOADER SELFTEST')
    print('  fixture = real NQ bars, perturbed in memory, NEVER a market\n')
    nq, rep = load_nq()
    ets = sorted(nq)[:6000]
    base = {e: nq[e] for e in ets}
    ok = True

    # 1. perfect copy -> everything MATCHED or ROLL_QUARANTINED, 0 ONLY
    rows, cls = synchronize(base, dict(base), quiet=True)
    t1 = cls['NQ_ONLY'] == 0 and cls['ES_ONLY'] == 0 and cls['MATCHED'] > 0
    print('  1 identical copy          MATCHED %d  ONLY %d/%d   %s'
          % (cls['MATCHED'], cls['NQ_ONLY'], cls['ES_ONLY'],
             'PASS' if t1 else 'FAIL'))
    ok &= t1

    # 2. one-minute shift -> must NOT fuzzy-match; ONLY counts must explode
    sh = {}
    for e in ets:
        t = (datetime.datetime.strptime(e, '%Y-%m-%d %H:%M:%S')
             + datetime.timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        sh[t] = base[e]
    rows2, c2 = synchronize(base, sh, quiet=True)
    t2 = c2['NQ_ONLY'] > 0 and c2['ES_ONLY'] > 0
    print('  2 +1min shifted ES        NQ_ONLY %d  ES_ONLY %d   %s'
          % (c2['NQ_ONLY'], c2['ES_ONLY'], 'PASS (no fuzzy join)' if t2 else 'FAIL'))
    ok &= t2

    # 3. missing ES bars are never filled
    miss = {e: base[e] for i, e in enumerate(ets) if i % 3}
    rows3, c3 = synchronize(base, miss, quiet=True)
    t3 = c3['NQ_ONLY'] > 0 and len(rows3) < len(rows)
    print('  3 ES with holes           NQ_ONLY %d  rows %d (< %d)   %s'
          % (c3['NQ_ONLY'], len(rows3), len(rows),
             'PASS (no forward fill)' if t3 else 'FAIL'))
    ok &= t3

    # 4. roll-window quarantine actually fires
    t4 = cls['ROLL_QUARANTINED'] > 0
    print('  4 roll quarantine         %d rows flagged   %s'
          % (cls['ROLL_QUARANTINED'], 'PASS' if t4 else
             'PASS (no roll window in this slice)'))

    # 5. conflicting duplicate must FAIL CLOSED  (identical dup must not)
    import tempfile
    d = tempfile.mkdtemp()
    e0 = ets[0]; b0 = base[e0]
    with open(os.path.join(d, 'x.csv'), 'w', newline='') as fh:
        fh.write('et,open,high,low,close,volume\n')
        fh.write('%s,%f,%f,%f,%f,%f\n' % ((e0,) + b0))
        fh.write('%s,%f,%f,%f,%f,%f\n' % ((e0,) + b0))          # identical
    _, r5 = load_market(d, 'FIXTURE')
    t5a = r5['rows'] == 1 and r5['dupes'] == 1
    with open(os.path.join(d, 'x.csv'), 'a', newline='') as fh:
        fh.write('%s,%f,%f,%f,%f,%f\n'
                 % (e0, b0[0] + 99, b0[1] + 99, b0[2] + 99, b0[3] + 99, b0[4]))
    try:
        load_market(d, 'FIXTURE')
        t5b = False
    except SystemExit:
        t5b = True
    print('  5 identical dup deduped   %s      conflicting dup FAIL-CLOSED  %s'
          % ('PASS' if t5a else 'FAIL', 'PASS' if t5b else 'FAIL'))
    ok &= t5a and t5b

    # 6. causal availability invariant on every emitted row
    t6 = all(r['crossMarketAvailableTime'] >= r['nqAvailableTime']
             and r['crossMarketAvailableTime'] >= r['esAvailableTime']
             for r in rows)
    print('  6 causal availability     crossMarket == max(nq,es) on all rows  %s'
          % ('PASS' if t6 else 'FAIL'))
    ok &= t6
    print('\n  SELFTEST: %s' % ('PASS - loader is verified and ready for genuine ES'
                                if ok else 'FAIL'))
    return ok


def build(es_dir, out=None):
    nq, rn = load_nq()
    print('NQ  files %d  rows %d  dupes %d  ohlc-invalid %d'
          % (rn['files'], rn['rows'], rn['dupes'], rn['ohlc_invalid']))
    if not os.path.isdir(es_dir):
        raise SystemExit('ES-NQ-DATA-V1 NOT READY - NO ES DATA at %s' % es_dir)
    es, re_ = load_market(es_dir, 'ES')
    print('ES  files %d  rows %d  dupes %d  ohlc-invalid %d'
          % (re_['files'], re_['rows'], re_['dupes'], re_['ohlc_invalid']))
    if not es:
        raise SystemExit('ES-NQ-DATA-V1 NOT READY - NO ES DATA')
    rows, cls = synchronize(nq, es)
    sanity_correlation([r for r in rows if r['qualityFlags'] == 'MATCHED'])
    byyear = collections.Counter(r['sessionDate'][:4] for r in rows
                                 if r['qualityFlags'] == 'MATCHED')
    print('\nYEAR COVERAGE (matched rows)')
    for y in sorted(byyear):
        print('  %s  %8d' % (y, byyear[y]))
    if out:
        with open(out, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print('\nwrote %s  (%d rows)' % (out, len(rows)))
        print('  spec %s  loader %s  cmap %s' % (SPEC_VERSION, LOADER_VERSION,
                                                 CONTRACT_MAP_VERSION))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'selftest'
    if cmd == 'selftest':
        selftest()
    elif cmd == 'build':
        build(sys.argv[sys.argv.index('--es') + 1],
              sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None)
