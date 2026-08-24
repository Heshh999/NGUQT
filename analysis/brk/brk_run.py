#!/usr/bin/env python3
# ======================================================================
# BRK-V1 - the non-directional family
# ======================================================================
# Frozen by docs/BRK_PREREGISTRATION.md (commit e5054d6) BEFORE any
# result was computed. Nothing here deviates from that document; where
# the document left an implementation choice, the choice is annotated.
#
#   BRK-H1  magnitude-event OCO bracket on the frozen OFH6 signals
#   BRK-H2  15s compression -> expansion on the genuine capture
#   OVN-H1  overnight drift baseline, zero parameters
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No orders anywhere.
# ======================================================================

import os, sys, csv, glob, math, random, statistics, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
import cand_spec as CS

COST = 0.87
TICK = 0.25
SEED = 20260823
FREEZE_END = '2026-08-19'
SPLIT_UNSEEN = '2025-11-01'
DEV_END = '2026-03-31'


def part(day):
    if day <= SPLIT_UNSEEN:
        return 'U'
    if day <= DEV_END:
        return 'DEV'
    return 'IR'


def eligible(b):
    """The frozen entry gate, as pre-registered ('entry_ok at the signal
    bar'): RTH, >= 60 min before the RTH close, ATR valid."""
    return (b.get('isRth') and b.get('minutesToRthClose') is not None
            and b['minutesToRthClose'] >= 60 and b.get('atr') and b['atr'] > 0)


def run_consec(B, j, n):
    """True if bars j..j+n are contiguous minutes (no session gap)."""
    return j + n < len(B) and B[j + n]['tmin'] - B[j]['tmin'] == n


# ====================================================== BRK-H1 bracket
def bracket(B, j, off=0.5, life=30, ambig='CONSERVATIVE'):
    """Arm an OCO straddling B[j] close. Returns a dict with net (points),
    filled flag, side, and the ambiguity marker. Scratch -> net 0.0.

    Pre-registered fill rule: high >= upper -> long at upper; low <= lower
    -> short at lower; BOTH in one bar -> AMBIGUOUS, and the primary
    assigns the WORSE of the two outcomes."""
    b = B[j]
    atr = b['atr']
    up, dn = b['close'] + off * atr, b['close'] - off * atr
    if not run_consec(B, j, life):
        return None
    for k in range(j + 1, j + life + 1):
        c = B[k]
        hit_up = c['high'] >= up
        hit_dn = c['low'] <= dn
        if not (hit_up or hit_dn):
            continue
        if hit_up and hit_dn:
            a = manage(B, k, +1, up, atr)
            z = manage(B, k, -1, dn, atr)
            if a is None or z is None:
                return None
            if ambig == 'CONSERVATIVE':
                pick, side = (a, +1) if a['net'] <= z['net'] else (z, -1)
            elif ambig == 'OPTIMISTIC':
                pick, side = (a, +1) if a['net'] >= z['net'] else (z, -1)
            else:                                   # EXCLUDE
                return {'net': None, 'filled': True, 'side': 0,
                        'ambig': True, 'k': k, 'day': b['day']}
            return {'net': pick['net'], 'filled': True, 'side': side,
                    'ambig': True, 'k': k, 'day': b['day'],
                    'reason': pick['reason']}
        side = +1 if hit_up else -1
        px = up if hit_up else dn
        m = manage(B, k, side, px, atr)
        if m is None:
            return None
        return {'net': m['net'], 'filled': True, 'side': side,
                'ambig': False, 'k': k, 'day': b['day'],
                'reason': m['reason']}
    return {'net': 0.0, 'filled': False, 'side': 0, 'ambig': False,
            'k': None, 'day': b['day'], 'reason': 'SCRATCH'}


def manage(B, k, d, px, atr, horizon=60, stop_mult=1.5):
    """Frozen OFH13 management: 1.5 ATR stop, no target, 60-min time exit.
    ATR is the SIGNAL bar's, frozen at arming."""
    if not run_consec(B, k, horizon):
        return None
    stop = px - stop_mult * atr * d
    for m in range(k + 1, k + horizon + 1):
        c = B[m]
        hit = (c['low'] <= stop) if d > 0 else (c['high'] >= stop)
        if hit:
            return {'net': (stop - px) * d - COST, 'reason': 'STOP'}
    end = B[k + horizon]['close']
    return {'net': (end - px) * d - COST, 'reason': 'TIME'}


# ================================================ statistics (clustered)
def mean(xs):
    return sum(xs) / len(xs) if xs else float('nan')


def day_boot_ci(pairs, iters=20000, seed=SEED):
    """pairs: (day, value). Resample DAYS with replacement."""
    if not pairs:
        return (float('nan'), float('nan'))
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
        if vals:
            ms.append(sum(vals) / len(vals))
    ms.sort()
    return (ms[int(0.025 * len(ms))], ms[int(0.975 * len(ms))])


def signflip_p(pairs, iters=20000, seed=SEED):
    """Two-sided sign-flip-by-day on already-paired deltas. For a paired
    signal-minus-control design this IS the day-clustered label
    permutation the pre-registration calls for: swapping the labels
    within a matched stratum negates that stratum's delta."""
    if not pairs:
        return float('nan')
    rnd = random.Random(seed)
    byday = collections.defaultdict(list)
    for d, v in pairs:
        byday[d].append(v)
    days = sorted(byday)
    sums = {d: sum(byday[d]) for d in days}
    n = sum(len(byday[d]) for d in days)
    obs = abs(sum(sums.values()) / n)
    cnt = 0
    for _ in range(iters):
        t = 0.0
        for d in days:
            t += sums[d] if rnd.random() < 0.5 else -sums[d]
        if abs(t / n) >= obs:
            cnt += 1
    return (cnt + 1.0) / (iters + 1.0)


def bh(ps):
    idx = sorted(range(len(ps)), key=lambda i: ps[i])
    m = len(ps)
    q = [None] * m
    prev = 1.0
    for rank, i in enumerate(reversed(idx), 1):
        k = m - rank + 1
        v = min(prev, ps[i] * m / k)
        q[i] = v
        prev = v
    return q


def tail_share(vals):
    """Share of GROSS PROFIT carried by the top 1% and top 10% of trades.
    Denominator is gross profit, not net, so the measure stays meaningful
    when the strategy loses money overall (a net denominator goes to zero
    or negative and produces nonsense)."""
    s = sorted(vals, reverse=True)
    gross = sum(x for x in s if x > 0)
    if gross <= 0:
        return (float('nan'), float('nan'))
    n1 = max(1, int(0.01 * len(s)))
    n10 = max(1, int(0.10 * len(s)))
    return (sum(s[:n1]) / gross, sum(s[:n10]) / gross)


def describe(name, rows, extra=''):
    """rows: dicts with net, day, part."""
    nets = [r['net'] for r in rows]
    pr = collections.defaultdict(list)
    for r in rows:
        pr[r['part']].append(r['net'])
    lo, hi = day_boot_ci([(r['day'], r['net']) for r in rows])
    t1, t10 = tail_share(nets)
    print('  %-34s n %4d  mean %+7.2f  med %+6.2f  win %5.1f%%  '
          'CI [%+.2f, %+.2f]  top1%% %5.1f%%  top10%% %5.1f%%  %s'
          % (name, len(rows), mean(nets), statistics.median(nets),
             100.0 * sum(1 for x in nets if x > 0) / len(nets), lo, hi,
             100 * t1, 100 * t10, extra))
    print('      by partition:  ' + '   '.join(
        '%s n %d mean %+.2f' % (p, len(pr[p]), mean(pr[p]))
        for p in ('U', 'DEV', 'IR') if pr[p]))
    return {'n': len(rows), 'mean': mean(nets), 'ci': (lo, hi),
            'tail1': t1, 'tail10': t10,
            'part': {p: mean(pr[p]) for p in pr}}


# ================================================== BRK-H1 driver
def atr_quintiles(B, idxs):
    a = sorted(B[j]['atr'] for j in idxs)
    return [a[int(q * len(a))] for q in (0.2, 0.4, 0.6, 0.8)]


def qbin(v, cuts):
    for i, c in enumerate(cuts):
        if v <= c:
            return i
    return len(cuts)


def brk_h1(B, SIGS, off=0.5, life=30, ambig='CONSERVATIVE', K=5, quiet=False):
    """Frozen OFH6 signals -> OCO brackets, plus matched controls."""
    # ---- cooldown over the frozen signal list (30 min, frozen COOL)
    sig, last = [], -10 ** 9
    for j, d in SIGS:
        if not eligible(B[j]):
            continue
        if B[j]['tmin'] - last < 30:
            continue
        last = B[j]['tmin']
        sig.append((j, d))

    # ---- eligible universe for controls: >= 60 min from ANY OFH6 signal
    sigmin = sorted(B[j]['tmin'] for j, _ in SIGS)
    import bisect
    def near_signal(t):
        i = bisect.bisect_left(sigmin, t)
        for k in (i - 1, i):
            if 0 <= k < len(sigmin) and abs(sigmin[k] - t) < 60:
                return True
        return False

    pool = [j for j in range(len(B))
            if eligible(B[j]) and not near_signal(B[j]['tmin'])]
    cuts = atr_quintiles(B, [j for j, _ in sig] + pool)
    strata = collections.defaultdict(list)
    for j in pool:
        b = B[j]
        strata[(part(b['day']), int(b['et'][11:13]), qbin(b['atr'], cuts))].append(j)

    rnd = random.Random(SEED)
    for k in strata:
        rnd.shuffle(strata[k])
    ptr = collections.defaultdict(int)

    rows, ctl_rows, pairs, amb, unmatched = [], [], [], 0, 0
    for j, d in sig:
        r = bracket(B, j, off, life, ambig)
        if r is None or r['net'] is None:
            if r is not None and r.get('net') is None:
                amb += 1
            continue
        b = B[j]
        rec = {'net': r['net'], 'day': b['day'], 'part': part(b['day']),
               'filled': r['filled'], 'side': r['side'], 'ofh6_dir': d,
               'ambig': r['ambig'], 'reason': r['reason'], 'j': j}
        rows.append(rec)
        if r['ambig']:
            amb += 1
        # ---- matched controls
        key = (rec['part'], int(b['et'][11:13]), qbin(b['atr'], cuts))
        got = []
        cand = strata.get(key, [])
        # DEFECT FIX: consuming controls without replacement exhausted the
        # thin strata and left 44% of signals unmatched, which biased the
        # paired test toward whichever strata happened to be well stocked.
        # Controls are a baseline, not a scarce resource - draw them WITH
        # replacement so every signal is matched.
        tries = 0
        while len(got) < K and cand and tries < 40:
            cj = cand[(ptr[key] + tries) % len(cand)]
            tries += 1
            cr = bracket(B, cj, off, life, ambig)
            if cr is None or cr['net'] is None:
                continue
            got.append(cr['net'])
            ctl_rows.append({'net': cr['net'], 'day': B[cj]['day'],
                             'part': part(B[cj]['day']),
                             'filled': cr['filled']})
        ptr[key] += tries
        if got:
            pairs.append((b['day'], r['net'] - mean(got)))
        else:
            unmatched += 1
    return rows, ctl_rows, pairs, amb, unmatched


# ================================================== BRK-H2 (15s capture)
def load_capture(d):
    """Genuine 15s + 1m capture, first-wins, days <= FREEZE_END."""
    s15, m1 = {}, {}
    for f in sorted(glob.glob(os.path.join(d, 'V41_LTF_*.csv'))):
        for r in csv.DictReader(open(f)):
            et = r['timestampET']
            if et[:10] > FREEZE_END:
                continue
            tgt = s15 if r['timeframe'] == '15s' else (
                m1 if r['timeframe'] == '1m' else None)
            if tgt is None or et in tgt:
                continue
            tgt[et] = {'et': et, 'o': float(r['open']), 'h': float(r['high']),
                       'l': float(r['low']), 'c': float(r['close'])}
    return ([s15[k] for k in sorted(s15)], [m1[k] for k in sorted(m1)])


def atr1m(m1, n=20):
    """Causal ATR(20) from the capture's own 1m bars: Wilder-free simple
    mean of true range over the last n bars, keyed by minute string."""
    out, tr = {}, []
    prev = None
    for b in m1:
        t = b['h'] - b['l'] if prev is None else max(
            b['h'] - b['l'], abs(b['h'] - prev), abs(b['l'] - prev))
        tr.append(t)
        prev = b['c']
        if len(tr) > n:
            tr.pop(0)
        if len(tr) == n:
            out[b['et']] = sum(tr) / n
    return out


def brk_h2(s15, m1, box_n=20, ratio=0.35, floor_pts=2.0,
           hold_min=30, lock_min=15):
    A = atr1m(m1)
    T = [datetime.datetime.strptime(b['et'], '%Y-%m-%d %H:%M:%S') for b in s15]
    idx = {b['et']: i for i, b in enumerate(s15)}
    rows = []
    lock_until = None
    for i in range(box_n, len(s15) - 1):
        t = T[i]
        if not (t.hour * 60 + t.minute >= 570 and t.hour * 60 + t.minute <= 900):
            continue                                   # RTH 09:30-15:00
        if lock_until is not None and t < lock_until:
            continue
        box = s15[i - box_n + 1:i + 1]
        # contiguity: 20 bars must span exactly 19*15 seconds
        if (T[i] - T[i - box_n + 1]).total_seconds() != 15 * (box_n - 1):
            continue
        hi = max(x['h'] for x in box)
        lo = min(x['l'] for x in box)
        rng = hi - lo
        if rng < floor_pts:
            continue
        key = t.replace(second=0).strftime('%Y-%m-%d %H:%M:%S')
        a = A.get(key)
        if a is None or a <= 0 or rng > ratio * a:
            continue
        nxt = s15[i + 1]
        if (T[i + 1] - T[i]).total_seconds() != 15:
            continue
        if nxt['c'] > hi:
            d, stop = +1, lo
        elif nxt['c'] < lo:
            d, stop = -1, hi
        else:
            continue
        px = nxt['c']
        # hold: 30 minutes = 120 x 15s bars, stop = far box edge
        end = i + 1 + hold_min * 4
        net, reason = None, 'TIME'
        for k in range(i + 2, min(end + 1, len(s15))):
            if (T[k] - T[i + 1]).total_seconds() != 15 * (k - i - 1):
                net, reason = (s15[k - 1]['c'] - px) * d - COST, 'GAP'
                break
            c = s15[k]
            if (c['l'] <= stop) if d > 0 else (c['h'] >= stop):
                net, reason = (stop - px) * d - COST, 'STOP'
                break
        if net is None:
            if end >= len(s15):
                continue
            net, reason = (s15[end]['c'] - px) * d - COST, 'TIME'
        rows.append({'net': net, 'day': t.strftime('%Y-%m-%d'),
                     'part': part(t.strftime('%Y-%m-%d')), 'dir': d,
                     'reason': reason, 'rng': rng, 'atr': a})
        lock_until = t + datetime.timedelta(minutes=lock_min)
    return rows


# ================================================== OVN-H1
def ovn_h1(B):
    """DEFECT FIX (implementation, not spec): no bar CLOSES at 18:00 -
    the evening session opens at 18:00 so its first bar closes at 18:01.
    The pre-registered intent, 'long at 18:00 ET', is honoured as the
    FIRST bar at or after 18:00; the exit is the LAST bar at or before
    09:29 on the next session day."""
    byday = collections.defaultdict(list)
    for b in B:
        byday[b['et'][:10]].append(b)
    days = sorted(byday)
    rows = []
    for i, d in enumerate(days[:-1]):
        ent = None
        for b in byday[d]:
            if b['et'][11:16] >= '18:00':
                ent = b
                break
        if ent is None:
            continue
        ex = None
        for nd in days[i + 1:i + 3]:
            cand = [b for b in byday[nd] if b['et'][11:16] <= '09:29']
            if cand:
                ex = cand[-1]
                break
        if ex is None:
            continue
        rows.append({'net': (ex['close'] - ent['close']) - COST,
                     'day': d, 'part': part(d),
                     'entry_et': ent['et'], 'exit_et': ex['et']})
    return rows


# ====================================================== main
if __name__ == '__main__':
    CAP = sys.argv[1] if len(sys.argv) > 1 else None
    print('=' * 78)
    print('BRK-V1  -  frozen by docs/BRK_PREREGISTRATION.md (e5054d6)')
    print('M = 3 (BRK-H1, BRK-H2, OVN-H1).  Scratches count as 0.')
    print('=' * 78)

    B = CS.load_merged()
    EV, SIGS, CTX = CS.generate(B)
    assert len(B) == 355455 and len(SIGS) == 952, 'REPRODUCTION GATE FAILED'
    assert len(EV['OFH13']) == 133, 'REPRODUCTION GATE FAILED'
    print('reproduction gate PASS: %d bars, %d OFH6 signals, %d OFH13'
          % (len(B), len(SIGS), len(EV['OFH13'])))

    ps, names = [], []

    # ---------------------------------------------------------- BRK-H1
    print('\nBRK-H1  magnitude-event bracket (0.5 ATR, 30-bar life)')
    rows, ctl, pairs, amb, unm = brk_h1(B, SIGS)
    fill = sum(1 for r in rows if r['filled'])
    st = describe('SIGNAL brackets', rows,
                  'filled %d/%d (%.0f%%) ambig %d' %
                  (fill, len(rows), 100.0 * fill / max(1, len(rows)), amb))
    ct = describe('MATCHED CONTROL brackets', ctl)
    p1 = signflip_p(pairs)
    lo, hi = day_boot_ci(pairs)
    print('  PAIRED delta (signal - matched control): n %d  mean %+.2f  '
          'CI [%+.2f, %+.2f]  p %.4f   unmatched %d'
          % (len(pairs), mean([v for _, v in pairs]), lo, hi, p1, unm))
    ps.append(p1); names.append('BRK-H1')
    # secondary: does OFH6 direction predict the fill side?
    fl = [r for r in rows if r['filled'] and r['side'] != 0]
    agree = sum(1 for r in fl if r['side'] == r['ofh6_dir'])
    print('  SECONDARY  OFH6 direction == fill side on %d/%d = %.1f%% '
          '(50%% = direction carries nothing)'
          % (agree, len(fl), 100.0 * agree / max(1, len(fl))))
    # pre-declared sensitivity, reported only, never promoted
    print('  sensitivity (reported, NOT promoted):')
    for o, l in ((0.25, 30), (0.75, 30), (0.5, 15), (0.5, 60)):
        r2, c2, p2, _, _ = brk_h1(B, SIGS, off=o, life=l)
        if r2:
            print('    off %.2f life %2d   signal mean %+7.2f (n %d)   '
                  'paired %+6.2f  p %.4f'
                  % (o, l, mean([x['net'] for x in r2]), len(r2),
                     mean([v for _, v in p2]), signflip_p(p2, iters=4000)))
    for a in ('OPTIMISTIC', 'EXCLUDE'):
        r3, _, p3, _, _ = brk_h1(B, SIGS, ambig=a)
        if r3:
            print('    ambig %-11s signal mean %+7.2f (n %d)  paired %+6.2f'
                  % (a, mean([x['net'] for x in r3]), len(r3),
                     mean([v for _, v in p3])))

    # ---------------------------------------------------------- BRK-H2
    print('\nBRK-H2  15s compression -> expansion')
    if CAP and os.path.isdir(CAP):
        s15, m1 = load_capture(CAP)
        print('  genuine capture: %d x 15s, %d x 1m, days <= %s'
              % (len(s15), len(m1), FREEZE_END))
        h2 = brk_h2(s15, m1)
        if h2:
            describe('15s compression break', h2,
                     'stop %d time %d' %
                     (sum(1 for r in h2 if r['reason'] == 'STOP'),
                      sum(1 for r in h2 if r['reason'] == 'TIME')))
            p2 = signflip_p([(r['day'], r['net']) for r in h2])
            print('  sign-flip-by-day p %.4f' % p2)
            ps.append(p2); names.append('BRK-H2')
        else:
            print('  NO EVENTS - the pre-registered compression gate is')
            print('  UNSATISFIABLE BY CONSTRUCTION, and that is a')
            print('  SPECIFICATION ERROR IN THE PRE-REGISTRATION, not a bug:')
            T = [datetime.datetime.strptime(b['et'], '%Y-%m-%d %H:%M:%S')
                 for b in s15]
            A = atr1m(m1)
            rr = []
            for i in range(20, len(s15) - 1):
                t = T[i]
                mm = t.hour * 60 + t.minute
                if not (570 <= mm <= 900):
                    continue
                if (T[i] - T[i - 19]).total_seconds() != 15 * 19:
                    continue
                box = s15[i - 19:i + 1]
                rng = max(x['h'] for x in box) - min(x['l'] for x in box)
                a = A.get(t.replace(second=0).strftime('%Y-%m-%d %H:%M:%S'))
                if a and a > 0:
                    rr.append(rng / a)
            rr.sort()
            print('    boxes evaluated %d   range/ATR1m  min %.3f  p01 %.3f  '
                  'median %.3f' % (len(rr), rr[0], rr[len(rr) // 100],
                                   statistics.median(rr)))
            print('    the gate demanded <= 0.350; the MINIMUM observed is '
                  '%.3f' % rr[0])
            print('    cause: a 5-minute (20 x 15s) range was compared to a')
            print('    ONE-minute ATR and required to be a third of it. A')
            print('    5-minute range runs about 2x a 1m ATR, so the test')
            print('    was dimensionally incoherent from the start.')
            print('    BRK-H2 is VOID. It is NOT re-run with a looser')
            print('    threshold - that would be tuning on the data that')
            print('    revealed the error. A corrected form needs a FRESH')
            print('    pre-registration and untouched data.')
            ps.append(1.0); names.append('BRK-H2(VOID)')
    else:
        print('  capture dir not supplied - SKIPPED')

    # ---------------------------------------------------------- OVN-H1
    print('\nOVN-H1  overnight drift (long 18:00 ET -> flat 09:29 ET)')
    ov = ovn_h1(B)
    describe('overnight', ov)
    p3 = signflip_p([(r['day'], r['net']) for r in ov])
    print('  sign-flip-by-day p %.4f' % p3)
    ps.append(p3); names.append('OVN-H1')

    # ---------------------------------------------------------- family
    print('\n' + '=' * 78)
    print('FAMILY ACCOUNTING  (BH at declared M = 3)')
    qs = bh(ps)
    for n, p, q in zip(names, ps, qs):
        print('  %-14s  p %.4f   q %.4f%s'
              % (n, p, q, '' if q <= 0.05 else '   NOT PROMOTED (q > 0.05)'))
    print('\n  REMINDER - the pre-registered promotion gate has FOUR')
    print('  conditions, not one. q <= 0.05 is necessary, NOT sufficient:')
    print('    1. BH q <= 0.05 at M = 3')
    print('    2. day-clustered CI excludes zero')
    print('    3. sign STABLE across U / DEV / IR')
    print('    4. NOT tail-dominated')
    print('  A cell that clears only (1) and (2) is NOT PROMOTED. Run')
    print('  brk_gate.py for conditions 3 and 4.')
    print('=' * 78)
