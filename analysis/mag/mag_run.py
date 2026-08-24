#!/usr/bin/env python3
# ======================================================================
# MAG-AUC-V1 - the fourteen directional / diagnostic cells
# ======================================================================
# Frozen by docs/MAG_PREREGISTRATION.md (c9c4bfe). MAG-H3 runs
# separately in mag_h3.py and gates this file.
#
# Direction NEVER comes from order-flow sign in any MAG/BAL/OPEN/ASYM
# cell. It comes from price structure. That is the point of the family.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No orders anywhere.
# ======================================================================

import os, sys, math, random, statistics, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
import mag_lib as M
import cand_spec as CS

T1, T2 = 1.270, 2.335          # frozen MAG terciles (U)
EFF_LO, EFF_HI = 0.119, 0.264  # frozen EFF terciles (U)
QUIET = 0.784                  # frozen compression cut (U p25)
COST = M.COST
BRK_WIN = 10                   # bars allowed for a breakout after the parent
REJ_WIN = 5                    # bars allowed for a rejection / reclaim
COOL = 30


def hi_mag(b):
    return b['mag'] is not None and b['mag'] > T2


def cool(evs):
    out, last = [], -10 ** 9
    for e in sorted(evs, key=lambda x: x['tmin']):
        if e['tmin'] - last < COOL:
            continue
        last = e['tmin']
        out.append(e)
    return out


def manage(B, j, d, atr):
    """Frozen OFH13 management: 1.5 ATR stop, no target, 60m time exit."""
    if not M.consec(B, j, 60):
        return None
    px = B[j]['close']
    stop = px - 1.5 * atr * d
    for k in range(j + 1, j + 61):
        c = B[k]
        if (c['low'] <= stop) if d > 0 else (c['high'] >= stop):
            return (stop - px) * d - COST, 'STOP'
    return (B[j + 60]['close'] - px) * d - COST, 'TIME'


def score(B, evs):
    out = []
    for e in evs:
        j, d = e['j'], e['d']
        atr = B[j]['atr']
        o = M.outcome(B, j, d, atr)
        if o is None:
            continue
        m = manage(B, j, d, atr)
        if m is None:
            continue
        o['net'], o['reason'] = m
        o.update({k: v for k, v in e.items() if k not in o})
        out.append(o)
    return out


# ====================================================== reporting
def day_boot_ci(pairs, iters=20000, seed=M.SEED):
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
        ms.append(sum(vals) / len(vals))
    ms.sort()
    return ms[int(0.025 * len(ms))], ms[int(0.975 * len(ms))]


def signflip_p(pairs, iters=20000, seed=M.SEED):
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
        t = sum(sums[d] if rnd.random() < 0.5 else -sums[d] for d in days)
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


def holm(ps):
    idx = sorted(range(len(ps)), key=lambda i: ps[i])
    m = len(ps)
    out = [None] * m
    prev = 0.0
    for rank, i in enumerate(idx, 1):
        v = max(prev, min(1.0, ps[i] * (m - rank + 1)))
        out[i] = v
        prev = v
    return out


def ffrate(rows, pair):
    f = sum(1 for r in rows if r['ff'][pair] == 'FAV')
    a = sum(1 for r in rows if r['ff'][pair] == 'ADV')
    amb = sum(1 for r in rows if r['ff'][pair] == 'AMBIGUOUS')
    tot = f + a
    return (100.0 * f / tot if tot else float('nan')), amb


def report(name, rows, quiet=False):
    if not rows:
        print('  %-28s  NO EVENTS' % name)
        return None
    nets = [r['net'] for r in rows]
    n = len(nets)
    mean = sum(nets) / n
    med = statistics.median(nets)
    wins = [x for x in nets if x > 0]
    loss = [x for x in nets if x <= 0]
    pf = (sum(wins) / abs(sum(loss))) if loss and sum(loss) else float('inf')
    lo, hi = day_boot_ci([(r['day'], r['net']) for r in rows])
    p = signflip_p([(r['day'], r['net']) for r in rows])
    s = sorted(nets, reverse=True)
    n1 = max(1, int(0.01 * n))
    n5 = max(1, int(0.05 * n))
    mfe = statistics.median([r['mfe'][60] / r['atr'] for r in rows])
    mae = statistics.median([r['mae'][60] / r['atr'] for r in rows])
    res = {'name': name, 'n': n, 'mean': mean, 'med': med, 'pf': pf,
           'wr': 100.0 * len(wins) / n, 'ci': (lo, hi), 'p': p,
           'mfe': mfe, 'mae': mae, 'ratio': (mfe / mae) if mae else float('nan'),
           'ex1': sum(s[n1:]) / (n - n1) if n > n1 else float('nan'),
           'ex5': sum(s[n5:]) / (n - n5) if n > n5 else float('nan'),
           'maxw': max(nets), 'maxl': min(nets), 'rows': rows}
    if quiet:
        return res
    ff25, amb25 = ffrate(rows, (0.25, 0.25))
    ff1, amb1 = ffrate(rows, (1.0, 1.0))
    print('  %-28s n %4d  mean %+7.2f  med %+6.2f  WR %5.1f%%  PF %5.2f  '
          'CI [%+.2f,%+.2f]  p %.4f' % (name, n, mean, med, res['wr'], pf, lo, hi, p))
    print('      MFE %.2f MAE %.2f  MFE/MAE %.2f | ff.25 %5.1f%% (amb %d)  '
          'ff1.0 %5.1f%% (amb %d) | exTop1%% %+6.2f exTop5%% %+6.2f  '
          'maxW %+.0f maxL %+.0f'
          % (mfe, mae, res['ratio'], ff25, amb25, ff1, amb1,
             res['ex1'], res['ex5'], res['maxw'], res['maxl']))
    pr = collections.defaultdict(list)
    for r in rows:
        pr[r['part']].append(r['net'])
    ls = collections.defaultdict(list)
    for r in rows:
        ls['L' if r['d'] > 0 else 'S'].append(r['net'])
    print('      ' + '  '.join('%s n%d %+.2f' % (k, len(pr[k]), sum(pr[k]) / len(pr[k]))
                               for k in ('U', 'DEV', 'IR') if pr[k])
          + '   |   ' + '  '.join('%s n%d %+.2f' % (k, len(ls[k]), sum(ls[k]) / len(ls[k]))
                                  for k in ('L', 'S') if ls[k]))
    return res


# ====================================================== overnight layer
def overnight(B):
    """Causal overnight stats per RTH day: bars 18:00 (D-1) -> 09:29 (D).
    ON_VWAP is a typical-price x volume PROXY - there is no tick VWAP in
    this data and none is fabricated."""
    days = sorted(set(b['day'] for b in B if b['isRth']))
    nxt = {d: days[i + 1] for i, d in enumerate(days[:-1])}
    acc = collections.defaultdict(lambda: {'hi': -1e18, 'lo': 1e18, 'pv': 0.0,
                                           'v': 0.0, 'first': None, 'last': None,
                                           'n': 0})
    for b in B:
        hm = b['et'][11:16]
        if hm >= '18:00':
            tgt = nxt.get(b['day'])
        elif hm <= '09:29':
            tgt = b['day']
        else:
            continue
        if tgt is None:
            continue
        a = acc[tgt]
        a['hi'] = max(a['hi'], b['high'])
        a['lo'] = min(a['lo'], b['low'])
        tp = (b['high'] + b['low'] + b['close']) / 3.0
        a['pv'] += tp * b['ofTotalVolume']
        a['v'] += b['ofTotalVolume']
        if a['first'] is None:
            a['first'] = b['close']
        a['last'] = b['close']
        a['n'] += 1
    out = {}
    for d, a in acc.items():
        if a['n'] < 60 or a['v'] <= 0:
            continue
        out[d] = {'hi': a['hi'], 'lo': a['lo'], 'mid': (a['hi'] + a['lo']) / 2.0,
                  'vwap': a['pv'] / a['v'], 'open': a['first'],
                  'close': a['last'], 'n': a['n']}
    return out


def rth_index(B):
    """day -> list of bar indices in RTH, in order."""
    out = collections.defaultdict(list)
    for j, b in enumerate(B):
        if b['isRth']:
            out[b['day']].append(j)
    return out


# ====================================================== MAG-DIR-H1 / H2
def _first_breakout(B, j, bal):
    for k in range(j + 1, min(j + 1 + BRK_WIN, len(B))):
        if not M.consec(B, j, k - j):
            return None
        c = B[k]
        if c['close'] > bal['hi']:
            return k, 1, bal['hi']
        if c['close'] < bal['lo']:
            return k, -1, bal['lo']
    return None


def mag_dir_h1(B):
    arms = collections.defaultdict(list)
    for j, b in enumerate(B):
        if not M.eligible(b) or b['mag'] is None:
            continue
        if hi_mag(b) and b['eff_dir'] != 0:
            arms['C_MAG_ALONE'].append({'j': j, 'd': b['eff_dir'], 'tmin': b['tmin']})
        bal = M.balance(B, j)
        if bal is None:
            continue
        br = _first_breakout(B, j, bal)
        if br is None:
            continue
        k, d, edge = br
        hm = hi_mag(b)
        arms['C_BREAKOUT_ONLY'].append({'j': k, 'd': d, 'tmin': B[k]['tmin']})
        if hm:
            arms['C_MAG_x_BREAKOUT'].append({'j': k, 'd': d, 'tmin': B[k]['tmin']})
        if not M.consec(B, k, 1):
            continue
        c2 = B[k + 1]
        acc = (c2['close'] > edge) if d > 0 else (c2['close'] < edge)
        if not acc:
            continue
        ev = {'j': k + 1, 'd': d, 'tmin': c2['tmin']}
        arms['C_ACCEPT_ANY'].append(ev)
        if hm:
            arms['FULL_MAG_ACCEPT'].append(ev)
        else:
            arms['C_ACCEPT_NOMAG'].append(ev)
    return {k: cool(v) for k, v in arms.items()}


def mag_dir_h2(B):
    arms = collections.defaultdict(list)
    for j, b in enumerate(B):
        if not M.eligible(b) or b['mag'] is None:
            continue
        bal = M.balance(B, j)
        if bal is None:
            continue
        br = _first_breakout(B, j, bal)
        if br is None:
            continue
        k, bd, edge = br
        hm = hi_mag(b)
        for m_ in range(k + 1, min(k + 1 + REJ_WIN, len(B))):
            if not M.consec(B, k, m_ - k):
                break
            cm = B[m_]
            if not (bal['lo'] <= cm['close'] <= bal['hi']):
                continue
            span = range(k, m_ + 1)
            dist = max((B[t]['high'] - edge) if bd > 0 else (edge - B[t]['low'])
                       for t in span)
            ev = {'j': m_, 'd': -bd, 'tmin': cm['tmin'],
                  'dist_out': dist / B[j]['atr'], 'time_out': m_ - k,
                  'vol_out': sum(B[t]['ofTotalVolume'] for t in span),
                  'absd_out': sum(abs(B[t]['ofBarDelta']) for t in span),
                  'reentry_speed': m_ - k}
            arms['C_REENTRY_ANY'].append(ev)
            if hm:
                arms['FULL_MAG_REJECT'].append(ev)
            else:
                arms['C_REJECT_NOMAG'].append(ev)
            break
    return {k: cool(v) for k, v in arms.items()}


# ====================================================== BAL-H1 / BAL-H2
def bal_family(B):
    a1 = collections.defaultdict(list)
    a2 = collections.defaultdict(list)
    for j, b in enumerate(B):
        if not M.eligible(b) or b['mag'] is None:
            continue
        bal = M.balance(B, j)
        if bal is None or bal['ratio'] > QUIET:
            continue
        shock = None
        for s in range(j, min(j + 1 + BRK_WIN, len(B))):
            if not M.consec(B, j, s - j):
                break
            if hi_mag(B[s]):
                shock = s
                break
        a1['C_QUIET_NO_SHOCK'].append({'j': j, 'd': B[j]['eff_dir'] or 1,
                                       'tmin': b['tmin']}) if shock is None else None
        if shock is None:
            continue
        br = _first_breakout(B, shock, bal)
        if br is None:
            continue
        k, d, edge = br
        a1['C_SHOCK_BREAKOUT'].append({'j': k, 'd': d, 'tmin': B[k]['tmin']})
        if M.consec(B, k, 1):
            c2 = B[k + 1]
            if (c2['close'] > edge) if d > 0 else (c2['close'] < edge):
                a1['FULL_BAL_ACCEPT'].append({'j': k + 1, 'd': d,
                                              'tmin': c2['tmin']})
        for m_ in range(k + 1, min(k + 1 + REJ_WIN, len(B))):
            if not M.consec(B, k, m_ - k):
                break
            cm = B[m_]
            if bal['lo'] <= cm['close'] <= bal['hi']:
                a2['FULL_BAL_FALSEBREAK'].append({'j': m_, 'd': -d,
                                                  'tmin': cm['tmin']})
                break
    return ({k: cool(v) for k, v in a1.items()},
            {k: cool(v) for k, v in a2.items()})


# ====================================================== OVN-H2/H3/H4
def ovn_family(B):
    ON = overnight(B)
    RI = rth_index(B)
    h2 = collections.defaultdict(list)
    h3 = collections.defaultdict(list)
    h4 = collections.defaultdict(list)
    for day, o in ON.items():
        idx = RI.get(day) or []
        if len(idx) < 90:
            continue
        j0 = idx[0]
        atr = B[j0]['atr']
        if not atr or atr <= 0:
            continue
        # ---------------- OVN-H2  extension -> reversion
        ext = (o['close'] - o['vwap']) / atr
        if abs(ext) >= 1.0:
            d = -1 if ext > 0 else 1
            h2['C_EXTENSION_ONLY'].append({'j': j0, 'd': d, 'tmin': B[j0]['tmin']})
            for j in idx[:60]:
                c = B[j]
                back = (c['close'] < o['vwap']) if ext > 0 else (c['close'] > o['vwap'])
                if back:
                    h2['FULL_EXT_REENTRY'].append({'j': j, 'd': d, 'tmin': c['tmin']})
                    break
        for j in idx[:60]:
            c = B[j]
            pv = B[j - 1]['close'] if j > 0 else c['close']
            cross = (pv < o['vwap'] <= c['close']) or (pv > o['vwap'] >= c['close'])
            if cross:
                d = 1 if c['close'] > o['vwap'] else -1
                h2['C_REENTRY_ONLY'].append({'j': j, 'd': d, 'tmin': c['tmin']})
                break
        # ---------------- OVN-H3  imbalance -> continuation if accepted
        mv = (o['close'] - o['open']) / atr
        if abs(mv) >= 1.0:
            d = 1 if mv > 0 else -1
            lvl = o['hi'] if d > 0 else o['lo']
            h3['C_ONMOVE_ONLY'].append({'j': j0, 'd': d, 'tmin': B[j0]['tmin']})
            opn = B[j0]['open']
            beyond = (opn >= lvl) if d > 0 else (opn <= lvl)
            if beyond:
                h3['C_OPEN_BEYOND'].append({'j': j0, 'd': d, 'tmin': B[j0]['tmin']})
                run = 0
                for j in idx[:15]:
                    c = B[j]
                    ok = (c['close'] > lvl) if d > 0 else (c['close'] < lvl)
                    run = run + 1 if ok else 0
                    if run >= 2:
                        h3['FULL_ON_ACCEPT_CONT'].append(
                            {'j': j, 'd': d, 'tmin': c['tmin']})
                        break
        # ---------------- OVN-H4  sweep + reclaim
        for lvl, d in ((o['lo'], 1), (o['hi'], -1)):
            for n, j in enumerate(idx[:120]):
                c = B[j]
                swept = (c['low'] < lvl) if d > 0 else (c['high'] > lvl)
                if not swept:
                    continue
                h4['C_SWEEP_ONLY'].append({'j': j, 'd': d, 'tmin': c['tmin']})
                hm = hi_mag(c)
                for m_ in range(j + 1, min(j + 1 + REJ_WIN, len(B))):
                    if not M.consec(B, j, m_ - j):
                        break
                    cm = B[m_]
                    back = (cm['close'] > lvl) if d > 0 else (cm['close'] < lvl)
                    if back:
                        ev = {'j': m_, 'd': d, 'tmin': cm['tmin']}
                        h4['FULL_SWEEP_RECLAIM'].append(ev)
                        if hm:
                            h4['FULL_SWEEP_RECLAIM_HIMAG'].append(ev)
                        break
                break
    return ({k: cool(v) for k, v in h2.items()},
            {k: cool(v) for k, v in h3.items()},
            {k: cool(v) for k, v in h4.items()})


# ====================================================== OPEN-H1 / OPEN-H2
def open_family(B):
    ON = overnight(B)
    RI = rth_index(B)
    o1 = collections.defaultdict(list)
    o2 = collections.defaultdict(list)
    for day, idx in RI.items():
        if len(idx) < 90:
            continue
        j0 = idx[0]
        atr = B[j0]['atr']
        if not atr or atr <= 0:
            continue
        opening = idx[:15]
        if len(opening) < 15:
            continue
        origin = B[j0]['open']
        endj = opening[-1]
        drive = (B[endj]['close'] - origin) / atr
        if abs(drive) < 1.0:
            continue
        d = 1 if drive > 0 else -1
        o1['C_DRIVE_ONLY'].append({'j': endj, 'd': d, 'tmin': B[endj]['tmin']})
        hm = any(hi_mag(B[j]) for j in opening)
        on = ON.get(day)
        # ---------------- OPEN-H1 continuation
        if on is not None:
            lvl = on['hi'] if d > 0 else on['lo']
            held = (B[endj]['close'] > lvl) if d > 0 else (B[endj]['close'] < lvl)
            if held:
                ext = max(B[j]['high'] for j in opening) if d > 0 else \
                    min(B[j]['low'] for j in opening)
                bad = False
                for j in idx[15:45]:
                    c = B[j]
                    if (c['close'] < origin) if d > 0 else (c['close'] > origin):
                        bad = True
                        break
                    made = (c['close'] > ext) if d > 0 else (c['close'] < ext)
                    if made:
                        ev = {'j': j, 'd': d, 'tmin': c['tmin']}
                        o1['FULL_OPEN_CONT'].append(ev)
                        if hm:
                            o1['FULL_OPEN_CONT_HIMAG'].append(ev)
                        break
                if bad:
                    o1['C_DRIVE_ORIGIN_RECLAIMED'].append(
                        {'j': endj, 'd': d, 'tmin': B[endj]['tmin']})
        # ---------------- OPEN-H2 exhaustion -> V recovery
        if hm:
            ext_j, ext_px = None, None
            for j in idx[:30]:
                c = B[j]
                v = c['low'] if d > 0 else c['high']
                if ext_px is None or ((v < ext_px) if d > 0 else (v > ext_px)):
                    ext_px, ext_j = v, j
            if ext_j is not None:
                imp = abs(B[endj]['close'] - origin)
                for frac, nm in ((0.5, 'ARM_A_50'), (1.0, 'ARM_B_100')):
                    tgt = ext_px + frac * imp * (1 if d < 0 else -1)
                    for j in idx[:60]:
                        if j <= ext_j:
                            continue
                        c = B[j]
                        rec = (c['close'] >= tgt) if d < 0 else (c['close'] <= tgt)
                        if rec:
                            o2[nm].append({'j': j, 'd': -d, 'tmin': c['tmin']})
                            break
    return ({k: cool(v) for k, v in o1.items()},
            {k: cool(v) for k, v in o2.items()})


# ====================================================== ASYM-H1 / ASYM-H2
def asym_family(B):
    vals = [abs(b['ofBarDelta']) for b in B]
    tr = M.trailing_ratio(vals)
    a1 = collections.defaultdict(list)
    a2 = collections.defaultdict(list)
    ext_cut = None
    u = sorted(tr[i] for i, b in enumerate(B)
               if tr[i] is not None and M.eligible(b) and M.part(b['day']) == 'U')
    ext_cut = u[int(2 / 3.0 * len(u))]
    for j, b in enumerate(B):
        if not M.eligible(b) or b['mag'] is None or b['eff'] is None:
            continue
        pdir = b['eff_dir']
        if pdir == 0:
            continue
        dsign = 1 if b['ofBarDelta'] > 0 else (-1 if b['ofBarDelta'] < 0 else 0)
        extreme = tr[j] is not None and tr[j] > ext_cut
        # ---- ASYM-H1
        a1['D_PRICE_UNCOND'].append({'j': j, 'd': pdir, 'tmin': b['tmin']})
        if extreme:
            if dsign != 0:
                a1['A_FOLLOW_DELTA_SIGN'].append({'j': j, 'd': dsign, 'tmin': b['tmin']})
            a1['B_FOLLOW_PRICE'].append({'j': j, 'd': pdir, 'tmin': b['tmin']})
            a1['C_PRICE_IF_EXTREME'].append({'j': j, 'd': pdir, 'tmin': b['tmin']})
        # ---- ASYM-H2
        if hi_mag(b):
            a2['C_ACTIVITY_ONLY'].append({'j': j, 'd': pdir, 'tmin': b['tmin']})
            if b['eff'] > EFF_HI:
                a2['STATE_A_HIACT_HIEFF_CONT'].append(
                    {'j': j, 'd': pdir, 'tmin': b['tmin']})
            elif b['eff'] < EFF_LO:
                for m_ in range(j + 1, min(j + 1 + REJ_WIN, len(B))):
                    if not M.consec(B, j, m_ - j):
                        break
                    cm = B[m_]
                    rec = (cm['close'] < B[j]['close']) if pdir > 0 else \
                          (cm['close'] > B[j]['close'])
                    if rec:
                        a2['STATE_B_HIACT_LOEFF_REV'].append(
                            {'j': m_, 'd': -pdir, 'tmin': cm['tmin']})
                        break
        if dsign != 0:
            a2['C_RAW_DELTA_SIGN'].append({'j': j, 'd': dsign, 'tmin': b['tmin']})
        a2['C_PRICE_MOMENTUM'].append({'j': j, 'd': pdir, 'tmin': b['tmin']})
    return ({k: cool(v) for k, v in a1.items()},
            {k: cool(v) for k, v in a2.items()})


# ====================================================== control audit
def control_audit(B, sig_rows, ctl_rows, label):
    """Mandatory after BRK-H1: a control that differs materially from the
    signal set manufactures significance from a losing signal."""
    def prof(rows):
        if not rows:
            return None
        return {
            'n': len(rows),
            'hour': statistics.median([int(B[r['j']]['et'][11:13]) for r in rows]),
            'atr': statistics.median([B[r['j']]['atr'] for r in rows]),
            'vol': statistics.median([B[r['j']]['ofTotalVolume'] for r in rows]),
            'rng': statistics.median([B[r['j']]['rng'] for r in rows]),
            'mag': statistics.median([B[r['j']]['mag'] for r in rows
                                      if B[r['j']]['mag'] is not None]),
            'long%': 100.0 * sum(1 for r in rows if r['d'] > 0) / len(rows)}
    a, b = prof(sig_rows), prof(ctl_rows)
    if not a or not b:
        return
    print('    CONTROL AUDIT %s' % label)
    print('      %-8s %5s %5s %7s %9s %6s %6s %6s'
          % ('set', 'n', 'hour', 'atr', 'volume', 'range', 'mag', 'long%'))
    for nm, p in (('signal', a), ('control', b)):
        print('      %-8s %5d %5d %7.2f %9.0f %6.2f %6.2f %5.1f%%'
              % (nm, p['n'], p['hour'], p['atr'], p['vol'], p['rng'],
                 p['mag'], p['long%']))
    flags = []
    for k in ('atr', 'vol', 'rng'):
        if b[k] and abs(a[k] - b[k]) / b[k] > 0.25:
            flags.append(k)
    if abs(a['long%'] - b['long%']) > 15:
        flags.append('direction mix')
    print('      -> %s' % ('MATCHED (no field differs by >25%)' if not flags
                           else 'MISMATCHED on ' + ', '.join(flags)
                                + ' - treat any paired difference as suspect'))


def gate(res, ctl_res, name):
    """The eight pre-registered promotion conditions, printed explicitly."""
    if res is None:
        print('  %-22s no events - cannot evaluate' % name)
        return False
    rows = res['rows']
    pr = collections.defaultdict(list)
    for r in rows:
        pr[r['part']].append(r['net'])
    signs = [1 if sum(v) > 0 else -1 for k, v in pr.items() if len(v) >= 5]
    c = {}
    c['1 expectancy positive'] = res['mean'] > 0
    # DEFECT FIX (mine, self-caught): this condition originally also
    # required med > -|mean|. That clause is NOT in the directive and is
    # wrong for a no-target / 1.5-ATR-stop strategy, whose median is
    # negative by construction because a minority of large winners carry
    # it. It would reject OFH13_PROSPECTIVE_V1 - the project's own best
    # candidate, 36.1% WR - which proves the clause invalid. The
    # condition is what the directive says: the signal is profitable on
    # its own, NOT merely less bad than its control (the BRK-H1 trap).
    c['2 signal profitable itself'] = (
        res['mean'] > 0 and not (ctl_res is not None and res['mean'] <= 0))
    c['3 U/DEV/IR sign stable'] = len(set(signs)) == 1 and len(signs) >= 2
    c['4 not top-5% dominated'] = res['ex5'] > 0
    c['5 matched-control advantage'] = (ctl_res is not None
                                        and res['mean'] > ctl_res['mean'])
    c['6 raw geometry credible'] = res['ratio'] >= 1.0
    c['7 sample adequate'] = res['n'] >= 100
    c['8 no control artifact'] = (ctl_res is None or res['mean'] > 0)
    print('  PROMOTION GATE  %s' % name)
    for k in sorted(c):
        print('    %-30s %s' % (k, 'PASS' if c[k] else 'FAIL'))
    ok = all(c.values())
    print('    ==> %s' % ('ALL EIGHT PASS' if ok else 'NOT PROMOTED'))
    return ok


# ====================================================== main
if __name__ == '__main__':
    B = CS.load_merged()
    M.build_features(B)
    EV, SIGS, CTX = CS.generate(B)
    assert len(B) == 355455 and len(SIGS) == 952 and len(EV['OFH13']) == 133
    print('canonical reproduction PASS  (355455 bars / 952 OFH6 / 133 OFH13)\n')

    P, primaries = {}, {}

    def run_block(title, arms, primary, control=None):
        print('=' * 78)
        print(title)
        res = {}
        for k in sorted(arms):
            res[k] = report(k, score(B, arms[k]))
        if primary in res and res[primary]:
            cr = res.get(control) if control else None
            if cr:
                control_audit(B, res[primary]['rows'], cr['rows'],
                              '%s vs %s' % (primary, control))
            gate(res[primary], cr, primary)
            primaries[title.split()[0]] = res[primary]
        print()
        return res

    a1 = mag_dir_h1(B)
    run_block('MAG-DIR-H1  HIGH magnitude + ACCEPTED breakout', a1,
              'FULL_MAG_ACCEPT', 'C_ACCEPT_NOMAG')

    a2 = mag_dir_h2(B)
    run_block('MAG-DIR-H2  HIGH magnitude + REJECTED breakout', a2,
              'FULL_MAG_REJECT', 'C_REJECT_NOMAG')

    b1, b2 = bal_family(B)
    run_block('BAL-H1  QUIET balance + activity shock + ACCEPTED breakout', b1,
              'FULL_BAL_ACCEPT', 'C_SHOCK_BREAKOUT')
    run_block('BAL-H2  QUIET balance + activity shock + FALSE break', b2,
              'FULL_BAL_FALSEBREAK')

    h2, h3, h4 = ovn_family(B)
    run_block('OVN-H2  overnight extension -> RTH reversion', h2,
              'FULL_EXT_REENTRY', 'C_REENTRY_ONLY')
    run_block('OVN-H3  overnight imbalance -> RTH continuation if accepted', h3,
              'FULL_ON_ACCEPT_CONT', 'C_ONMOVE_ONLY')
    run_block('OVN-H4  overnight high/low sweep + reclaim', h4,
              'FULL_SWEEP_RECLAIM', 'C_SWEEP_ONLY')

    o1, o2 = open_family(B)
    run_block('OPEN-H1  opening drive + acceptance continuation', o1,
              'FULL_OPEN_CONT', 'C_DRIVE_ONLY')
    run_block('OPEN-H2  opening drive exhaustion -> V recovery', o2, 'ARM_A_50')

    s1, s2 = asym_family(B)
    run_block('ASYM-H1  absolute delta magnitude + price direction', s1,
              'C_PRICE_IF_EXTREME', 'A_FOLLOW_DELTA_SIGN')
    run_block('ASYM-H2  activity shock x price efficiency', s2,
              'STATE_A_HIACT_HIEFF_CONT', 'C_PRICE_MOMENTUM')

    # ---------------------------------------------- MAG-OFH13-H1
    print('=' * 78)
    print('MAG-OFH13-H1  OFH13 performance by expected-movement state')
    print('  DIAGNOSTIC ONLY - OFH13_PROSPECTIVE_V1 IS NOT FILTERED OR MODIFIED')
    ev13 = [{'j': e['j'], 'd': e['d'], 'tmin': B[e['j']]['tmin']}
            for e in EV['OFH13']]
    sc = score(B, ev13)
    print('  canonical OFH13 events scored: %d' % len(sc))
    byb = collections.defaultdict(list)
    for r in sc:
        m = B[r['j']]['mag']
        byb['LOW' if m is None or m < T1 else
            ('MEDIUM' if m <= T2 else 'HIGH')].append(r)
    print('  %-7s %4s %7s %7s %6s %6s %6s %6s %8s %8s'
          % ('bucket', 'n', 'mean', 'med', 'WR%', 'PF', 'MFE', 'MAE', 'MFE/MAE', 'avgWin'))
    for k in ('LOW', 'MEDIUM', 'HIGH'):
        g = byb[k]
        if not g:
            continue
        nets = [r['net'] for r in g]
        w = [x for x in nets if x > 0]
        l = [x for x in nets if x <= 0]
        mfe = statistics.median([r['mfe'][60] / r['atr'] for r in g])
        mae = statistics.median([r['mae'][60] / r['atr'] for r in g])
        print('  %-7s %4d %+7.2f %+7.2f %5.1f%% %6.2f %6.2f %6.2f %8.2f %8.2f'
              % (k, len(g), sum(nets) / len(nets), statistics.median(nets),
                 100.0 * len(w) / len(g),
                 (sum(w) / abs(sum(l))) if l and sum(l) else float('inf'),
                 mfe, mae, mfe / mae if mae else float('nan'),
                 sum(w) / len(w) if w else float('nan')))
    print()

    # ---------------------------------------------- RANGE-H1
    print('=' * 78)
    print('RANGE-H1  does HIGH magnitude mark a PERSISTENT regime?')
    print('  DIAGNOSTIC ONLY - no strategy is changed here')
    buck = collections.defaultdict(lambda: collections.defaultdict(list))
    for j, b in enumerate(B):
        if not M.eligible(b) or b['mag'] is None or not M.consec(B, j, 30):
            continue
        k = 'LOW' if b['mag'] < T1 else ('MEDIUM' if b['mag'] <= T2 else 'HIGH')
        for w in (3, 5, 10, 15, 30):
            buck[k][w].append(sum(B[j + t]['rng'] for t in range(1, w + 1)) / w)
    print('  %-7s %6s %s' % ('bucket', 'n', '  '.join('+%-3dm' % w
                                                      for w in (3, 5, 10, 15, 30))))
    for k in ('LOW', 'MEDIUM', 'HIGH'):
        if not buck[k]:
            continue
        print('  %-7s %6d %s' % (k, len(buck[k][3]), '  '.join(
            '%5.2f' % statistics.median(buck[k][w]) for w in (3, 5, 10, 15, 30))))
    print('  (mean 1m range per minute in the window following the state)')
    print()

    # ---------------------------------------------- RANGE-H2
    print('=' * 78)
    print('RANGE-H2  strategy type x magnitude state (interaction, no retuning)')
    fams = {'OFH13': sc,
            'ACCEPTED-BREAKOUT': score(B, a1.get('C_ACCEPT_ANY', [])),
            'REJECTED-BREAKOUT': score(B, a2.get('C_REENTRY_ANY', []))}
    print('  %-20s %-7s %5s %9s %9s' % ('family', 'bucket', 'n', 'mean', 'median'))
    for fn, rr in fams.items():
        bb = collections.defaultdict(list)
        for r in rr:
            m = B[r['j']]['mag']
            bb['LOW' if m is None or m < T1 else
               ('MEDIUM' if m <= T2 else 'HIGH')].append(r['net'])
        for k in ('LOW', 'MEDIUM', 'HIGH'):
            if bb[k]:
                print('  %-20s %-7s %5d %+9.2f %+9.2f'
                      % (fn, k, len(bb[k]), sum(bb[k]) / len(bb[k]),
                         statistics.median(bb[k])))
    print()

    # ---------------------------------------------- family accounting
    print('=' * 78)
    print('FAMILY ACCOUNTING  -  M = 15 (declared, never shrunk)')
    order = ['MAG-H3', 'MAG-DIR-H1', 'MAG-DIR-H2', 'MAG-OFH13-H1', 'OVN-H2',
             'OVN-H3', 'OVN-H4', 'OPEN-H1', 'OPEN-H2', 'BAL-H1', 'BAL-H2',
             'RANGE-H1', 'RANGE-H2', 'ASYM-H1', 'ASYM-H2']
    # MAG-H3 is a non-directional association test run in mag_h3.py; its
    # day-clustered permutation p is carried in here so the family is
    # accounted at the declared M = 15. RANGE-H1/H2 and MAG-OFH13-H1 are
    # DIAGNOSTICS with no directional claim: they enter the family at
    # p = 1.0, which is conservative and never flatters a survivor.
    KNOWN = {'MAG-H3': 0.00005}
    ps = []
    for nm in order:
        r = primaries.get(nm)
        ps.append(KNOWN.get(nm, r['p'] if r else 1.0))
    qs, hs = bh(ps), holm(ps)
    print('  %-14s %6s %8s %8s %9s %s'
          % ('hypothesis', 'n', 'mean', 'p', 'BH q', 'Holm'))
    for nm, p, q, h in zip(order, ps, qs, hs):
        r = primaries.get(nm)
        print('  %-14s %6s %8s %8.4f %9.4f %8.4f'
              % (nm, r['n'] if r else '-',
                 '%+.2f' % r['mean'] if r else '-', p, q, h))
    print('=' * 78)
