#!/usr/bin/env python3
# ======================================================================
# MGSD-V1  frozen family signal generators (freeze v1.0 §6)
# Each generator returns {variant_key: (slots, dirs, mgmt, stratum_pool,
#                                       target_or_None)}
# slots are ENTRY bar indices (bar after the completed signal bar),
# already deduplicated to one per (tradedate, direction) taking the first.
# ======================================================================
import numpy as np
import collections

MGMT = [(1.0, 'T30'), (1.0, 'T120'), (2.0, 'T30'), (2.0, 'T120')]


def _dedupe(G, sig):
    """sig: list of (signal_bar_i, dir). Entry slot = i+1 (contiguous).
    Keep first per (tradedate, dir)."""
    seen = set()
    out = []
    td = G['tradedate']
    st = G['step1']
    for i, d in sorted(sig):
        j = i + 1
        if j >= G['N'] or not st[j]:
            continue
        k = (td[j], d)
        if k in seen:
            continue
        seen.add(k)
        out.append((j, d))
    return out


def _split(pairs):
    lo = np.array([j for j, d in pairs if d > 0], dtype=np.int64)
    sh = np.array([j for j, d in pairs if d < 0], dtype=np.int64)
    return lo, sh


def fifteens(G):
    """Completed 15m bars in chronological order with last-1m index."""
    out = []
    for k, (op, hi, lo, cl, li, atr) in G['bar15'].items():
        out.append((li, op, hi, lo, cl, atr, k[0]))
    out.sort()
    return out


def gen_all(G):
    N = G['N']
    mod, day, td = G['mod'], G['day'], G['tradedate']
    o, h, l, c = G['o'], G['h'], G['l'], G['c']
    atr15 = G['atr15']
    F = {}
    f15 = fifteens(G)

    # ---------------- F01/F02 displacement (15m bar move vs ATR) --------
    for k in (1.5, 2.5):
        mr, cont = [], []
        for li, op, hi, lo, cl, atr, dy in f15:
            if atr != atr or not (601 <= mod[li] <= 930):
                continue
            mv = cl - op
            if mv <= -k * atr:
                mr.append((li, +1)); cont.append((li, -1))
            elif mv >= k * atr:
                mr.append((li, -1)); cont.append((li, +1))
        for name, sig in (('F01', mr), ('F02', cont)):
            pairs = _dedupe(G, sig)
            for sm, ex in MGMT:
                for dd in (+1, -1):
                    ss = np.array([j for j, d in pairs if d == dd], np.int64)
                    F['%s_k%.1f_%s%d_%s' % (name, k, 'L' if dd > 0 else 'S',
                                            int(sm * 10), ex)] = \
                        (ss, dd, sm, ex, 'S6S8', None)

    # ---------------- F03 compression -> expansion ----------------------
    # 30m opening range vs trailing 20-day median of same
    or30 = {}
    for d in G['rth_days']:
        idx = [i for i in G['rth_idx'][d] if 571 <= mod[i] <= 600]
        if len(idx) >= 28:
            or30[d] = (max(h[i] for i in idx), min(l[i] for i in idx))
    hist = []
    med20 = {}
    for d in G['rth_days']:
        if len(hist) >= 20:
            med20[d] = float(np.median(hist[-20:]))
        if d in or30:
            hist.append(or30[d][0] - or30[d][1])
    for q in (0.6, 0.75):
        sig = []
        for d in G['rth_days']:
            if d not in or30 or d not in med20:
                continue
            hi30, lo30 = or30[d]
            if hi30 - lo30 > q * med20[d]:
                continue
            for i in G['rth_idx'][d]:
                if 601 <= mod[i] <= 689:
                    if c[i] > hi30:
                        sig.append((i, +1)); break
                    if c[i] < lo30:
                        sig.append((i, -1)); break
        pairs = _dedupe(G, sig)
        for sm, ex in MGMT:
            lo_, sh_ = _split(pairs)
            F['F03_q%.2f_L%d_%s' % (q, int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S6S8', None)
            F['F03_q%.2f_S%d_%s' % (q, int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S6S8', None)

    # ---------------- F04 expansion -> exhaustion fade -------------------
    for m in (2.5, 3.5):
        sig = []
        run = []
        for li, op, hi, lo, cl, atr, dy in f15:
            if atr != atr or not (601 <= mod[li] <= 930):
                run = []; continue
            d_ = 1 if cl > op else (-1 if cl < op else 0)
            if run and run[-1][0] == d_ and d_ != 0:
                run.append((d_, op, cl, li))
            else:
                run = [(d_, op, cl, li)] if d_ else []
            if len(run) >= 3:
                cum = abs(run[-1][2] - run[0][1])
                if cum >= m * atr:
                    sig.append((li, -d_))
        pairs = _dedupe(G, sig)
        for sm, ex in MGMT:
            lo_, sh_ = _split(pairs)
            F['F04_m%.1f_L%d_%s' % (m, int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S6S8', None)
            F['F04_m%.1f_S%d_%s' % (m, int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S6S8', None)

    # ---------------- F05 baseline: OR15 failed break fade (REFERENCE) ---
    or15 = {}
    for d in G['rth_days']:
        idx = [i for i in G['rth_idx'][d] if 571 <= mod[i] <= 585]
        if len(idx) >= 14:
            or15[d] = (max(h[i] for i in idx), min(l[i] for i in idx))
    sig = []
    for d, (hi15, lo15) in or15.items():
        brk = None
        for i in G['rth_idx'][d]:
            if not (586 <= mod[i] <= 690):
                continue
            if brk is None:
                if c[i] > hi15:
                    brk = (i, +1)
                elif c[i] < lo15:
                    brk = (i, -1)
            else:
                bi, bd = brk
                if mod[i] - mod[bi] > 15:
                    break
                if (bd > 0 and c[i] < hi15) or (bd < 0 and c[i] > lo15):
                    sig.append((i, -bd)); break
    pairs = _dedupe(G, sig)
    for ex in ('T30', 'T120'):
        lo_, sh_ = _split(pairs)
        F['F05BASE_L10_%s' % ex] = (lo_, +1, 1.0, ex, 'S6S8', None)
        F['F05BASE_S10_%s' % ex] = (sh_, -1, 1.0, ex, 'S6S8', None)

    # ---------------- F06 prior-day level acceptance ---------------------
    sig = []
    for li, op, hi, lo, cl, atr, dy in f15:
        if atr != atr or not (586 <= mod[li] <= 840):
            continue
        pr = G['prior_rth'].get(dy)
        if not pr:
            continue
        if cl > pr['hi'] + 0.25 * atr:
            sig.append((li, +1))
        elif cl < pr['lo'] - 0.25 * atr:
            sig.append((li, -1))
    pairs = _dedupe(G, sig)
    for sm, ex in MGMT:
        lo_, sh_ = _split(pairs)
        F['F06_L%d_%s' % (int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S6S8', None)
        F['F06_S%d_%s' % (int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S6S8', None)

    # ---------------- F07 VWAP stretch reversion -------------------------
    vwap = G['vwap']
    for k in (2.0, 3.0):
        sig = []
        for i in range(N):
            if not (601 <= mod[i] <= 930):
                continue
            a = atr15[i]
            if a != a or vwap[i] != vwap[i]:
                continue
            if c[i] - vwap[i] >= k * a:
                sig.append((i, -1))
            elif vwap[i] - c[i] >= k * a:
                sig.append((i, +1))
        pairs = _dedupe(G, sig)
        for sm in (1.0, 2.0):
            for ex in ('T30', 'TGT'):
                lo_, sh_ = _split(pairs)
                tgl = vwap[lo_ - 1] if ex == 'TGT' else None
                tgs = vwap[sh_ - 1] if ex == 'TGT' else None
                F['F07_k%.0f_L%d_%s' % (k, int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S6S8', tgl)
                F['F07_k%.0f_S%d_%s' % (k, int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S6S8', tgs)

    # ---------------- F08 VWAP reclaim trend -----------------------------
    sig = []
    side_since = {}
    for li, op, hi, lo, cl, atr, dy in f15:
        if not (571 <= mod[li] <= 930) or vwap[li] != vwap[li]:
            side_since.pop(dy, None); continue
        s = 1 if cl > vwap[li] else -1
        prev = side_since.get(dy)
        if prev is None:
            side_since[dy] = (s, mod[li]); continue
        ps, since = prev
        if s != ps:
            if mod[li] - since >= 60:
                sig.append((li, s))
            side_since[dy] = (s, mod[li])
    pairs = _dedupe(G, sig)
    for sm in (1.0, 2.0):
        for ex in ('T120', 'CLOSE'):
            lo_, sh_ = _split(pairs)
            F['F08_L%d_%s' % (int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S6S8', None)
            F['F08_S%d_%s' % (int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S6S8', None)

    # ---------------- F09/F10 gap fade / continuation --------------------
    open_bar = {}
    for d in G['rth_days']:
        idx = [i for i in G['rth_idx'][d] if mod[i] == 571]
        if idx:
            open_bar[d] = idx[0]
    for g in (0.3, 0.5):
        fade, go = [], []
        for d, ib in open_bar.items():
            pr = G['prior_rth'].get(d)
            if not pr or pr['rng'] <= 0:
                continue
            gap = o[ib] - pr['close']
            if abs(gap) < g * pr['rng']:
                continue
            dd = -1 if gap > 0 else +1          # fade direction
            # gap needs the 09:30 open PRINT -> signal completes with the
            # first RTH bar (stamp 571); entry = open of the next bar
            fade.append((ib, dd))
            go.append((ib, -dd))
        pf = _dedupe(G, fade)
        pg = _dedupe(G, go)
        for sm in (1.0, 2.0):
            lo_, sh_ = _split(pf)
            tgl = np.array([G['prior_rth'][td[j]]['close'] for j in lo_]) if len(lo_) else np.array([])
            tgs = np.array([G['prior_rth'][td[j]]['close'] for j in sh_]) if len(sh_) else np.array([])
            F['F09_g%.1f_L%d_T120' % (g, int(sm * 10))] = (lo_, +1, sm, 'T120', 'S5S6', None)
            F['F09_g%.1f_S%d_T120' % (g, int(sm * 10))] = (sh_, -1, sm, 'T120', 'S5S6', None)
            F['F09_g%.1f_L%d_TGT' % (g, int(sm * 10))] = (lo_, +1, sm, 'TGT', 'S5S6', tgl)
            F['F09_g%.1f_S%d_TGT' % (g, int(sm * 10))] = (sh_, -1, sm, 'TGT', 'S5S6', tgs)
        for sm, ex in MGMT:
            lo_, sh_ = _split(pg)
            F['F10_g%.1f_L%d_%s' % (g, int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S5S6', None)
            F['F10_g%.1f_S%d_%s' % (g, int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S5S6', None)

    # ---------------- F11 ORB15 continuation -----------------------------
    for cc in (0.0, 0.25):
        sig = []
        for d, (hi15, lo15) in or15.items():
            for i in G['rth_idx'][d]:
                if not (586 <= mod[i] <= 690):
                    continue
                a = atr15[i]
                if a != a:
                    continue
                if c[i] > hi15 + cc * a:
                    sig.append((i, +1)); break
                if c[i] < lo15 - cc * a:
                    sig.append((i, -1)); break
        pairs = _dedupe(G, sig)
        for sm, ex in MGMT:
            lo_, sh_ = _split(pairs)
            F['F11_c%.2f_L%d_%s' % (cc, int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S6S8', None)
            F['F11_c%.2f_S%d_%s' % (cc, int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S6S8', None)

    # ---------------- F12 overnight-range break at open ------------------
    for cc in (0.0, 0.25):
        sig = []
        for d in G['rth_days']:
            onf = G['overnight'].get(d)
            if not onf or onf['hi'] < onf['lo'] or onf['n'] < 200:
                continue
            for i in G['rth_idx'][d]:
                if not (571 <= mod[i] <= 690):
                    continue
                a = atr15[i]
                if a != a:
                    continue
                if c[i] > onf['hi'] + cc * a:
                    sig.append((i, +1)); break
                if c[i] < onf['lo'] - cc * a:
                    sig.append((i, -1)); break
        pairs = _dedupe(G, sig)
        for sm, ex in MGMT:
            lo_, sh_ = _split(pairs)
            F['F12_c%.2f_L%d_%s' % (cc, int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S6S8', None)
            F['F12_c%.2f_S%d_%s' % (cc, int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S6S8', None)

    # ---------------- F13 cross-TF alignment pullback --------------------
    sig = []
    last60 = {}
    for k, (op, hi, lo, cl, li) in sorted(G['bar60'].items(),
                                          key=lambda kv: kv[1][4]):
        last60[k[0]] = (li, 1 if cl > op else -1)
    b15dir = {}
    for li, op, hi, lo, cl, atr, dy in f15:
        b15dir[li] = 1 if cl > op else -1
    f15byday = collections.defaultdict(list)
    for li, op, hi, lo, cl, atr, dy in f15:
        f15byday[dy].append(li)
    b3 = sorted(G['bar3'].items(), key=lambda kv: kv[1][4])
    b3dir = [(kv[1][4], 1 if kv[1][3] > kv[1][0] else
              (-1 if kv[1][3] < kv[1][0] else 0), kv[0][0]) for kv in b3]
    for a in range(2, len(b3dir)):
        li, d3, dy = b3dir[a]
        if not (601 <= mod[li] <= 840):
            continue
        pli, pd3, pdy = b3dir[a - 1]
        if pdy != dy or d3 == 0 or pd3 == 0:
            continue
        l60 = last60.get(dy)
        lst15 = [x for x in f15byday.get(dy, []) if x < li]
        if not l60 or l60[0] > li or not lst15:
            continue
        d60 = l60[1]
        d15 = b15dir[lst15[-1]]
        if d60 == d15 and pd3 == -d60 and d3 == d60:
            sig.append((li, d60))
    pairs = _dedupe(G, sig)
    for sm, ex in MGMT:
        lo_, sh_ = _split(pairs)
        F['F13_L%d_%s' % (int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S6S8', None)
        F['F13_S%d_%s' % (int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S6S8', None)

    # ---------------- F14 volatility-regime transition -------------------
    sig = []
    atrhist = collections.deque(maxlen=21)
    sesshi = {}
    sesslo = {}
    for li, op, hi, lo, cl, atr, dy in f15:
        if atr == atr:
            atrhist.append((li, atr))
        if not (571 <= mod[li] <= 930):
            continue
        ph, pl = sesshi.get(dy, -1e18), sesslo.get(dy, 1e18)
        newhi, newlo = hi > ph, lo < pl
        sesshi[dy] = max(ph, hi); sesslo[dy] = min(pl, lo)
        if len(atrhist) < 21 or atr != atr:
            continue
        if atr >= 1.25 * atrhist[0][1] and 601 <= mod[li] <= 930:
            if newhi and cl > op:
                sig.append((li, +1))
            elif newlo and cl < op:
                sig.append((li, -1))
    pairs = _dedupe(G, sig)
    for sm, ex in MGMT:
        lo_, sh_ = _split(pairs)
        F['F14_L%d_%s' % (int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S6S8', None)
        F['F14_S%d_%s' % (int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S6S8', None)

    # ---------------- F15 session drift (unconditional) ------------------
    on_entry = []
    seen_td = set()
    for i in range(N):
        if mod[i] == 1081:                     # first bar after 18:00
            k = td[i]
            if k in seen_td:                   # holiday-eve double session:
                continue                       # one entry per tradedate (IC2)
            seen_td.add(k)
            on_entry.append(i)
    open_entries = [open_bar[d] for d in sorted(open_bar)]
    for sm in (2.0, 3.0):
        for nm, ent, ex in (('ON2OPEN', on_entry, 'OPEN'),
                            ('ON2CLOSE', on_entry, 'CLOSE'),
                            ('OPEN2CLOSE', open_entries, 'CLOSE')):
            for dd in (+1, -1):
                F['F15_%s_%s%d' % (nm, 'L' if dd > 0 else 'S', int(sm * 10))] = \
                    (np.array(ent, np.int64), dd, sm,
                     'CLOSE' if ex == 'CLOSE' else 'OPEN', 'UNCOND', None)

    # ---------------- F16 late-premarket trend -> open -------------------
    for p in (0.5, 1.0):
        sig = []
        for d, ib in open_bar.items():
            onf = G['overnight'].get(d)
            if not onf or onf['c0800'] is None or onf['c0929'] is None:
                continue
            a = atr15[ib - 1]
            if a != a:
                continue
            mv = onf['c0929'] - onf['c0800']
            if abs(mv) >= p * a:
                sig.append((ib - 1, 1 if mv > 0 else -1))
        pairs = _dedupe(G, sig)
        for sm, ex in MGMT:
            lo_, sh_ = _split(pairs)
            F['F16_p%.1f_L%d_%s' % (p, int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S5S6', None)
            F['F16_p%.1f_S%d_%s' % (p, int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S5S6', None)

    # ---------------- F17 midday-range break -----------------------------
    for cc in (0.0, 0.25):
        sig = []
        for d in G['rth_days']:
            idx = [i for i in G['rth_idx'][d] if 691 <= mod[i] <= 840]
            if len(idx) < 140:
                continue
            mh = max(h[i] for i in idx); ml = min(l[i] for i in idx)
            for li, op, hi15, lo15, cl, atr, dy in f15:
                if dy != d or not (841 <= mod[li] <= 930) or atr != atr:
                    continue
                if cl > mh + cc * atr:
                    sig.append((li, +1)); break
                if cl < ml - cc * atr:
                    sig.append((li, -1)); break
        pairs = _dedupe(G, sig)
        for sm, ex in MGMT:
            lo_, sh_ = _split(pairs)
            F['F17_c%.2f_L%d_%s' % (cc, int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S8S9', None)
            F['F17_c%.2f_S%d_%s' % (cc, int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S8S9', None)

    # ---------------- F18 closing momentum -------------------------------
    for p in (1.0, 1.5):
        sig = []
        for d in G['rth_days']:
            i1400 = [i for i in G['rth_idx'][d] if mod[i] == 840]
            i1530 = [i for i in G['rth_idx'][d] if mod[i] == 930]
            if not i1400 or not i1530:
                continue
            a = atr15[i1530[0]]
            if a != a:
                continue
            mv = c[i1530[0]] - c[i1400[0]]
            if abs(mv) >= p * a:
                sig.append((i1530[0], 1 if mv > 0 else -1))
        pairs = _dedupe(G, sig)
        lo_, sh_ = _split(pairs)
        F['F18_p%.1f_L15_CLOSE' % p] = (lo_, +1, 1.5, 'CLOSE', 'S9', None)
        F['F18_p%.1f_S15_CLOSE' % p] = (sh_, -1, 1.5, 'CLOSE', 'S9', None)

    # ---------------- F19 3m run reversal --------------------------------
    for r in (4, 6):
        sig = []
        runlen = 0; rdir = 0; lastdy = None
        for li, d3, dy in b3dir:
            if dy != lastdy:
                runlen = 0; rdir = 0; lastdy = dy
            if d3 == 0:
                pass
            elif d3 == rdir:
                runlen += 1
            else:
                if runlen >= r and rdir != 0 and 601 <= mod[li] <= 930:
                    sig.append((li, d3))       # reversal confirmed: trade d3
                rdir = d3; runlen = 1
        pairs = _dedupe(G, sig)
        for sm, ex in MGMT:
            lo_, sh_ = _split(pairs)
            F['F19_r%d_L%d_%s' % (r, int(sm * 10), ex)] = (lo_, +1, sm, ex, 'S6S8', None)
            F['F19_r%d_S%d_%s' % (r, int(sm * 10), ex)] = (sh_, -1, sm, ex, 'S6S8', None)
    return F, {'or15': or15, 'or30': or30, 'open_bar': open_bar}
