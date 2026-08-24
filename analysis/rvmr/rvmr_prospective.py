#!/usr/bin/env python3
# ======================================================================
# RVMR-V1 - PROSPECTIVE CONTEXT LOGGER (companion module)
# ======================================================================
# ARCHITECTURE DECISION, per the freeze directive: RVMR is computed and
# logged OFFLINE from the 1m OHLCV the existing capture pipeline already
# produces. NOTHING is added to the NinjaTrader host. Reasons:
#   1. the prospective NT8 engine is parity-verified, frozen, and midway
#      through forward collection - any edit invalidates its hashes and
#      forces a full parity re-verification;
#   2. RVMR needs only completed 1m OHLCV, which the capture strategy
#      already writes monthly;
#   3. order safety becomes ARCHITECTURAL, not a boolean: this code
#      never runs inside NinjaTrader, so it has no possible path to
#      EnterLong/EnterShort/SubmitOrder/stop/target/size APIs.
#      (verified: zero occurrences of 'rvmr' in src/*.cs)
#
# RVMR IS OBSERVATIONAL CONTEXT ONLY. It never filters, blocks, grades,
# sizes, or directs anything. There is no trading-filter switch to turn
# on, deliberately.
#
#   python3 rvmr_prospective.py log --source <dir|v3> --mode <MODE> [--out F]
#   python3 rvmr_prospective.py parity          row-level old-vs-new gate
#   python3 rvmr_prospective.py snapshot        event context snapshots
#   python3 rvmr_prospective.py audit --ledger F --day YYYY-MM-DD
#   python3 rvmr_prospective.py selftest        idempotence + conflict FAIL-CLOSED
#
# Modes: LIVE_PROSPECTIVE_RVMR | RETROACTIVE_CONTEXT_BACKFILL |
#        CROSS_SOURCE_AUDIT
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, glob, hashlib, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
import rvmr_spec as S

RVMR_VERSION = 'RVMR-V1'
LOGGER_VERSION = '1.0'
SPEC_HASH = hashlib.sha256(
    open(os.path.join(HERE, 'rvmr_spec.py'), 'rb').read()).hexdigest()[:16]
SCR = ('/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce'
       '/scratchpad')
LEDGER_DIR = os.path.join(HERE, 'ledger')

HEADER = ('timestampEt,rvmrAvailableTimeEt,rvmrVersion,rangeScore,'
          'rangeRegime,volumeScore,volumeRegime,sourceBarTimestamp,'
          'sessionDate,dataSourceMode,instrument,inCertifiedUniverse,'
          'loggerVersion,specHash')


# ------------------------------------------------------------- loaders
def _norm_rows(rows, src):
    """(et,o,h,l,c,v) first-wins; CONFLICTING duplicates FAIL CLOSED."""
    seen, out, conf = {}, [], []
    for r in rows:
        k = r[0]
        if k in seen:
            if seen[k] != r[1:]:
                conf.append(k)
            continue
        seen[k] = r[1:]
        out.append(r)
    if conf:
        for k in conf[:5]:
            print('  CONFLICT %s in %s' % (k, src))
        raise SystemExit('FAIL CLOSED: %d conflicting duplicate bars in %s '
                         '- refusing to choose a value silently'
                         % (len(conf), src))
    out.sort(key=lambda r: r[0])
    return out


def load_source(spec):
    """spec = 'v3' (certified extract) or a directory holding capture
    monthly CSVs (f_* schema) and/or LTF capture files and/or rvmr_1m
    extracts. Returns normalized (et,o,h,l,c,v) list."""
    rows = []
    if spec == 'v3':
        for f in sorted(glob.glob(os.path.join(SCR, 'rvmr_1m', 'rvmr_1m_*.csv'))):
            for r in csv.reader(open(f)):
                if r[0] != 'et':
                    rows.append((r[0], float(r[1]), float(r[2]), float(r[3]),
                                 float(r[4]), float(r[5])))
        return _norm_rows(rows, 'v3-extract')
    for f in sorted(glob.glob(os.path.join(spec, '*.csv'))):
        with open(f, newline='') as fh:
            rd = csv.reader(fh)
            h = next(rd)
            i = {c: k for k, c in enumerate(h)}
            if 'f_barCloseEt' in i:                      # capture schema
                for r in rd:
                    if len(r) != len(h):
                        continue
                    rows.append((r[i['f_barCloseEt']], float(r[i['f_open']]),
                                 float(r[i['f_high']]), float(r[i['f_low']]),
                                 float(r[i['f_close']]), float(r[i['f_volume']])))
            elif 'timeframe' in i:                       # LTF capture schema
                for r in rd:
                    if len(r) != len(h) or r[i['timeframe']] != '1m':
                        continue
                    rows.append((r[i['timestampET']], float(r[i['open']]),
                                 float(r[i['high']]), float(r[i['low']]),
                                 float(r[i['close']]),
                                 float(r[i['volume']]) if r[i['volume']] else 0.0))
            elif 'et' in i:                              # extract schema
                for r in rd:
                    if len(r) == 6:
                        rows.append((r[0], float(r[1]), float(r[2]), float(r[3]),
                                     float(r[4]), float(r[5])))
    return _norm_rows(rows, spec)


# ------------------------------------------------------------- states
def states(bars):
    """Frozen RVMR-V1 state for every RTH close stamp. A state is the
    score of the COMPLETED bar and is available exactly at that bar's
    close - never earlier. Missing state -> UNAVAILABLE + reason."""
    n = len(bars)
    et = [b[0] for b in bars]
    rng = [b[2] - b[3] for b in bars]
    vol = [b[5] for b in bars]
    rr = S.trailing_ratio(rng)
    vr = S.trailing_ratio(vol)
    out = []
    for j in range(n):
        hh, mm = int(et[j][11:13]), int(et[j][14:16])
        m = hh * 60 + mm
        if not (S.RTH_START <= m <= S.RTH_END):
            continue
        if rr[j] is None or vr[j] is None:
            out.append((et[j], None, 'UNAVAILABLE', None, 'UNAVAILABLE',
                        'INSUFFICIENT_WARMUP', m))
            continue
        out.append((et[j], rr[j], S.bucket(rr[j]), vr[j], S.bucket(vr[j]),
                    '', m))
    return out


# ------------------------------------------------------------- ledger
def write_ledger(st, mode, out_path, instrument='MNQ'):
    """Append-with-dedupe. Same key + identical values -> skip. Same key
    + DIFFERENT values -> FAIL CLOSED. Idempotent under re-runs."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    old = {}
    if os.path.exists(out_path):
        for r in csv.DictReader(open(out_path)):
            old[(r['timestampEt'], r['rvmrVersion'])] = (
                r['rangeScore'], r['rangeRegime'], r['volumeScore'],
                r['volumeRegime'], r['dataSourceMode'])
    added = skipped = 0
    conflicts = []
    fresh = not os.path.exists(out_path)
    with open(out_path, 'a', newline='') as fh:
        if fresh:
            fh.write(HEADER + '\n')
        for et, rs, rb, vs, vb, reason, m in st:
            rss = '%.10f' % rs if rs is not None else ''
            vss = '%.10f' % vs if vs is not None else ''
            key = (et, RVMR_VERSION)
            val = (rss, rb, vss, vb, mode)
            if key in old:
                if old[key][:4] != val[:4]:
                    conflicts.append(et)
                else:
                    skipped += 1
                continue
            cert = 'TRUE' if (S.RTH_END - m) >= 60 else 'FALSE'
            fh.write(','.join([et, et, RVMR_VERSION, rss, rb, vss, vb,
                               et, et[:10], mode, instrument, cert,
                               LOGGER_VERSION, SPEC_HASH]) + '\n')
            added += 1
    if conflicts:
        for c in conflicts[:5]:
            print('  LEDGER CONFLICT %s' % c)
        raise SystemExit('FAIL CLOSED: %d rows conflict with the existing '
                         'ledger - no value was silently replaced'
                         % len(conflicts))
    print('ledger %s  +%d rows, %d identical skipped, 0 conflicts'
          % (os.path.basename(out_path), added, skipped))
    return added, skipped


# ------------------------------------------------------------- parity
def parity():
    """Row-level parity: certified engine (rvmr_run.features on the V3
    extract) vs THIS logger's independent pipeline, same bars."""
    import rvmr_run as R
    R.STAMP_SHIFT = 0
    D = R.load_bars()
    U, _ = R.features(D)
    cert = {}
    for k in range(len(U['rr'])):
        j = U['i'][k]
        cert[D['et'][j]] = (U['rr'][k], U['rb'][k], U['vr'][k], U['vb'][k])
    bars = load_source('v3')
    st = states(bars)
    new = {et: (rs, rb, vs, vb) for et, rs, rb, vs, vb, reason, m in st
           if rb != 'UNAVAILABLE'}
    both = [t for t in cert if t in new]
    smis = rmis = 0
    for t in both:
        a, b = cert[t], new[t]
        if a[0] != b[0] or a[2] != b[2]:
            smis += 1
        if a[1] != b[1] or a[3] != b[3]:
            rmis += 1
    missing = len(cert) - len(both)
    print('ROW-LEVEL PARITY  certified rows %d   compared %d   missing %d'
          % (len(cert), len(both), missing))
    print('  score mismatches  %d' % smis)
    print('  regime mismatches %d' % rmis)
    print('  timestamp mismatches %d' % missing)
    ok = smis == 0 and rmis == 0 and missing == 0
    print('  PARITY: %s' % ('PASS (exact float equality, exact labels)'
                            if ok else 'FAIL'))
    return ok


# ------------------------------------------------------------- snapshot
def snapshot(mode='HISTORICAL_RECONSTRUCTION'):
    """Immutable context snapshot for strategy events. The joined state
    is the one available AT the event's decision bar close - the frozen
    engine decides on bar close, and the RVMR state of that same bar is
    fully determined at that instant (score uses the bar itself plus the
    1440 PRECEDING bars). rvmrAvailableTime == eventTime, never later
    data. The strategy itself never sees any of this."""
    import cand_spec as CS
    B = CS.load_merged()
    EV, SIGS, CTX = CS.generate(B)
    bars = [(b['et'], b['open'], b['high'], b['low'], b['close'],
             b['ofTotalVolume']) for b in B]
    st = {x[0]: x for x in states(bars)}
    out = os.path.join(LEDGER_DIR, 'RVMR_EVENT_SNAPSHOTS.csv')
    os.makedirs(LEDGER_DIR, exist_ok=True)
    n = miss = 0
    with open(out, 'w', newline='') as fh:
        fh.write('eventId,strategyId,eventTime,entryTime,rvmrAvailableTime,'
                 'rvmrRangeScore,rvmrRangeRegime,rvmrVolumeScore,'
                 'rvmrVolumeRegime,rvmrVersion,dataSourceMode\n')
        for cand in ('OFH13', 'OFH14', 'G4', 'G3', 'G1'):
            for e in EV[cand]:
                t = e['et']
                x = st.get(t)
                if x is None or x[2] == 'UNAVAILABLE':
                    miss += 1
                    fh.write('%s,%s,%s,%s,,,UNAVAILABLE,,UNAVAILABLE,%s,%s\n'
                             % (e['id'], cand, t, t, RVMR_VERSION, mode))
                    continue
                fh.write('%s,%s,%s,%s,%s,%.10f,%s,%.10f,%s,%s,%s\n'
                         % (e['id'], cand, t, t, x[0], x[1], x[2], x[3],
                            x[4], RVMR_VERSION, mode))
                n += 1
    print('event snapshots: %d written, %d UNAVAILABLE  -> %s' % (n, miss, out))
    print('  (labelled %s - these events predate the RVMR freeze; the' % mode)
    print('   strategy behaved identically with or without these values)')


# ------------------------------------------------------------- audits
def audit_day(ledger, day):
    rows = [r for r in csv.DictReader(open(ledger))
            if r['sessionDate'] == day]
    keys = [r['timestampEt'] for r in rows]
    dups = len(keys) - len(set(keys))
    unav = [r for r in rows if r['rangeRegime'] == 'UNAVAILABLE']
    causal = all(r['rvmrAvailableTimeEt'] == r['timestampEt'] for r in rows)
    stamps = sorted(int(k[11:13]) * 60 + int(k[14:16]) for k in keys)
    print('AUDIT %s  rows %d  dup %d  UNAVAILABLE %d  causal(avail==close) %s'
          % (day, len(rows), dups, len(unav), causal))
    if stamps:
        print('  first stamp %02d:%02d   last %02d:%02d   regimes %s'
              % (stamps[0] // 60, stamps[0] % 60, stamps[-1] // 60,
                 stamps[-1] % 60,
                 dict(collections.Counter(r['rangeRegime'] for r in rows))))
    return dups == 0 and causal


def selftest():
    """Restart safety: idempotence + conflict FAIL-CLOSED, on a scratch
    ledger with synthetic rows."""
    tmp = os.path.join(SCR, 'rvmr_selftest.csv')
    if os.path.exists(tmp):
        os.remove(tmp)
    st = [('2099-01-01 10:0%d:00' % i, 1.0 + i, 'LOW', 2.0 + i, 'MEDIUM', '',
           600 + i) for i in range(5)]
    a1, s1 = write_ledger(st, 'CROSS_SOURCE_AUDIT', tmp)
    a2, s2 = write_ledger(st, 'CROSS_SOURCE_AUDIT', tmp)   # restart replay
    ok = (a1, s1, a2, s2) == (5, 0, 0, 5)
    print('idempotence: first run +%d, replay +%d/%d skipped  %s'
          % (a1, a2, s2, 'PASS' if ok else 'FAIL'))
    bad = [('2099-01-01 10:00:00', 9.9, 'HIGH', 9.9, 'HIGH', '', 600)]
    try:
        write_ledger(bad, 'CROSS_SOURCE_AUDIT', tmp)
        print('conflict FAIL-CLOSED: FAIL (conflicting row was accepted)')
        ok = False
    except SystemExit:
        print('conflict FAIL-CLOSED: PASS (aborted, nothing replaced)')
    os.remove(tmp)
    return ok


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'parity'
    if cmd == 'parity':
        parity()
    elif cmd == 'snapshot':
        snapshot()
    elif cmd == 'selftest':
        selftest()
    elif cmd == 'log':
        src = sys.argv[sys.argv.index('--source') + 1]
        mode = sys.argv[sys.argv.index('--mode') + 1]
        outp = (sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv
                else os.path.join(LEDGER_DIR, 'RVMR_PROSPECTIVE.csv'))
        assert mode in ('LIVE_PROSPECTIVE_RVMR', 'RETROACTIVE_CONTEXT_BACKFILL',
                        'CROSS_SOURCE_AUDIT'), 'unknown mode'
        bars = load_source(src)
        print('source %s: %d bars  %s .. %s'
              % (src, len(bars), bars[0][0], bars[-1][0]))
        write_ledger(states(bars), mode, outp)
    elif cmd == 'audit':
        audit_day(sys.argv[sys.argv.index('--ledger') + 1],
                  sys.argv[sys.argv.index('--day') + 1])
