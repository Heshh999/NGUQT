#!/usr/bin/env python3
# ======================================================================
# CANDIDATE SHELF - CANONICAL FROZEN DEFINITIONS
# Frozen 2026-08-21. Transcribed from the ORIGINAL SOURCE of each
# historical run, not from memory:
#   G1, G3, G4     <- analysis/v41/gen10_run.py  (verified by gen10_oos.py)
#   OFH13, OFH14   <- analysis/v41/offvg_run.py
#   OFH6 context   <- analysis/v41/ofh6_spec.py  (imported, untouched)
#
# These are FOUR SEPARATE COMPETING LINEAGES plus one execution overlay.
# They are never combined, never required to agree, and never stacked.
#
# ----------------------------------------------------------------------
# WRITTEN SPEC != IMPLEMENTED SPEC  (documented, NOT corrected)
# ----------------------------------------------------------------------
# D1. ofht_spec.entry_ok - used by every historical G/OFH run - does NOT
#     enforce the ">=30 minutes after RTH open" restriction that its own
#     header and several run headers describe. Only ofh6_spec.eligible()
#     (the OFH6 SIGNAL gate) enforces it. entry_ok below reproduces the
#     IMPLEMENTED behaviour exactly. Enforcing the written rule would
#     change the eligible population, refit every frozen quantile, and
#     create NEW versions that cannot inherit existing evidence.
# D2. offvg_run.py header states OFH13/OFH14 use "RTH, >=30 min after
#     open, >=60 min to close". Only the >=60-to-close half is enforced.
# D3. OFH13/OFH14 mitigation expiry is SIGNAL TIME + 30 min, not FVG
#     time + 30 min. The FVG can form at minute 29 and leave one minute.
# D4. G4 passes B[k]['close'] as the entry price - identical to the bar
#     close, so it is a market entry, not a limit.
# D5. G1's R is the ATR of the SIGNAL bar, not of the fill bar.
# D6. G3's R is 1.0 x ATR of the entry bar, so for G3 the "structural"
#     stop and the 1.0 ATR stop are the same object.
# D7. G1 historical fills assumed TOUCH (low <= limit). For a passive
#     limit that is optimistic; fill realism is measured separately and
#     is NOT part of the frozen definition.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, glob
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ofht_cache import NEED, load as load_old
from ofht_spec import TICK, attach_dsum15

SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'

# ---- FROZEN CONSTANTS -------------------------------------------------
COST = 0.87                 # index points, round turn, all-in
HORIZON = 60                # minutes, measurement/time-exit ceiling
LIFE = 30                   # OFH6 context lifetime, minutes
COOL = 30                   # per-candidate chronological cooldown, minutes
OFH6_THRESHOLD = 3380.0     # |15-bar cumulative delta|
OFH6_LOOKBACK = 15
OFH6_MIN_AFTER_OPEN = 30    # enforced ONLY on the signal gate (see D1)
OFH6_MIN_TO_CLOSE = 90
Q_BD75 = 511.0              # DEV p75 |barDelta|
DISP_ATR, DISP_BODY, DISP_CLR = 1.00, 0.50, 0.70
G1_DEPTH_ATR = 0.5
G3_DELAY_MIN = 20
G4_TREND_ATR = 0.5
G4_WINDOW = 3
SPLIT_UNSEEN = '2025-11-01'
SPLIT_DEV = '2026-03-31'
DOLLARS_PER_POINT = 2.0     # MNQ

CANDIDATES = ('OFH13', 'G4', 'G3', 'OFH14')
OVERLAY = 'G1'


def F(v):
    try:
        x = float(v)
        return x if x == x else None
    except Exception:
        return None


def load_merged(extra_dirs=()):
    """New capture for <= SPLIT_UNSEEN, existing cache after. extra_dirs
    lets the prospective scorer append later months without touching
    anything historical."""
    B = []
    for f in sorted(glob.glob(SCR + '/ofnew/v4_1_orderflow_MNQ_v41of_*.csv')):
        with open(f, newline='') as fh:
            r = csv.reader(fh)
            h = next(r)
            i = {c: k for k, c in enumerate(h)}
            for row in r:
                if len(row) != len(h):
                    continue
                et = row[i['f_barCloseEt']]
                if et[:10] > SPLIT_UNSEEN:
                    continue
                B.append(_mk(row, i, et))
    B.extend(b for b in load_old() if b['day'] > SPLIT_UNSEEN)
    for d in extra_dirs:
        for f in sorted(glob.glob(os.path.join(d, '*.csv'))):
            with open(f, newline='') as fh:
                r = csv.reader(fh)
                h = next(r)
                i = {c: k for k, c in enumerate(h)}
                for row in r:
                    if len(row) != len(h):
                        continue
                    B.append(_mk(row, i, row[i['f_barCloseEt']]))
    B = [b for b in B if b is not None]
    B.sort(key=lambda b: b['et'])
    out = []
    seen = set()
    for b in B:                                  # de-duplicate by timestamp
        if b['et'] in seen:
            continue
        seen.add(b['et'])
        out.append(b)
    attach_dsum15(out, OFH6_LOOKBACK)
    _derive(out)
    return out


def _mk(row, i, et):
    d = {}
    for c in NEED:
        v = row[i[c]]
        d[c[2:]] = (v == 'TRUE') if v in ('TRUE', 'FALSE') else F(v)
    if d['high'] is None or d['atr'] is None or d['close'] is None:
        return None
    d['et'] = et
    d['day'] = et[:10]
    d['tmin'] = (int(et[:4]) * 527040 + int(et[5:7]) * 44640 + int(et[8:10]) * 1440
                 + int(et[11:13]) * 60 + int(et[14:16]))
    return d


def _derive(B):
    for j in range(len(B)):
        b = B[j]
        ok5 = j >= 5 and B[j]['tmin'] - B[j - 5]['tmin'] == 5
        b['disp5'] = (b['close'] - B[j - 5]['close']) if ok5 else None
        rng = b['high'] - b['low']
        b['rng'] = rng


def window_of(day):
    if day <= SPLIT_UNSEEN:
        return 'UNSEEN'
    if day <= SPLIT_DEV:
        return 'DEV'
    return 'IR'


def make_ctx(B):
    """entry_ok / consec closures bound to a bar list."""
    N = len(B)

    def consec(j, k):
        return B[j]['tmin'] - B[k]['tmin'] == j - k

    def entry_ok(j):
        # EXACT reproduction of ofht_spec.entry_ok - see discrepancy D1.
        b = B[j]
        if not b['isRth'] or b['atr'] is None or b['atr'] <= 0:
            return False
        if b['minutesToRthClose'] is None or b['minutesToRthClose'] < HORIZON:
            return False
        if j + HORIZON >= N:
            return False
        return B[j + HORIZON]['tmin'] - b['tmin'] == HORIZON

    return consec, entry_ok


def ofh6_signals(B):
    """Frozen OFH6 stream. Signal gate DOES enforce >=30 min after open
    (ofh6_spec.eligible); entry eligibility does not (D1)."""
    N = len(B)
    out = []
    last = -10 ** 9
    for j in range(N):
        b = B[j]
        if (not b['isRth'] or b['dsum15'] is None or b['atr'] is None or b['atr'] <= 0
                or b['minutesFromRthOpen'] is None
                or b['minutesFromRthOpen'] < OFH6_MIN_AFTER_OPEN
                or b['minutesToRthClose'] is None
                or b['minutesToRthClose'] < OFH6_MIN_TO_CLOSE):
            continue
        if j + 90 >= N or B[j + 90]['tmin'] - b['tmin'] != 90:
            continue
        if abs(b['dsum15']) < OFH6_THRESHOLD or b['tmin'] - last < COOL:
            continue
        last = b['tmin']
        out.append((j, 1 if b['dsum15'] > 0 else -1))
    return out


class Ctx(object):
    """OFH6 context queries - same semantics as ofht_spec.Context."""

    def __init__(self, sigs, B):
        import bisect
        self._b = bisect
        self.t = {1: [], -1: []}
        for j, d in sigs:
            self.t[d].append(B[j]['tmin'])

    def latest_le(self, d, te):
        lst = self.t[d]
        i = self._b.bisect_right(lst, te)
        return lst[i - 1] if i else None

    def opposite_in(self, d, ts, te):
        lst = self.t[-d]
        i = self._b.bisect_right(lst, ts)
        return i < len(lst) and lst[i] <= te

    def ok_at(self, d, te, life):
        ts = self.latest_le(d, te)
        if ts is None or te - ts > life:
            return False
        return not self.opposite_in(d, ts, te)


def build_fvg(B, consec):
    """Displacement-qualified FVGs, exactly as offvg_run.py builds them."""
    N = len(B)
    at = defaultdict(list)
    for j in range(2, N):
        if not consec(j, j - 2):
            continue
        a, c2, c3 = B[j - 2], B[j - 1], B[j]
        atr = c2['atr']
        if not atr or atr <= 0:
            continue
        if a['high'] < c3['low']:
            d, zLo, zHi = 1, a['high'], c3['low']
        elif a['low'] > c3['high']:
            d, zLo, zHi = -1, c3['high'], a['low']
        else:
            continue
        rng = c2['high'] - c2['low']
        if rng <= 0:
            continue
        body = abs(c2['close'] - c2['open'])
        clr = (c2['close'] - c2['low']) / rng
        if not (rng >= DISP_ATR * atr and body / rng >= DISP_BODY
                and ((d > 0 and clr >= DISP_CLR and c3['close'] > a['open'])
                     or (d < 0 and clr <= 1.0 - DISP_CLR and c3['close'] < a['open']))):
            continue
        at[j].append({'j': j, 'd': d, 'zLo': zLo, 'zHi': zHi,
                      'mid': (zLo + zHi) / 2.0, 'atr': atr,
                      'sizeAtr': (zHi - zLo) / atr})
    return at


def _mitigate(B, f, start_j, expire_tmin):
    """Verbatim port of offvg_run.py mitigate() with hard_invalid=None,
    want_flow=False."""
    N = len(B)
    d, zLo, zHi, mid = f['d'], f['zLo'], f['zHi'], f['mid']
    touched = False
    ext = None
    flow_ok = False
    prev = None
    for k in range(start_j, N):
        if prev is not None and B[k]['tmin'] != prev + 1:
            return None
        prev = B[k]['tmin']
        if B[k]['tmin'] > expire_tmin:
            return None
        c = B[k]
        if (d > 0 and c['close'] < zLo) or (d < 0 and c['close'] > zHi):
            return None
        if not touched:
            if (d > 0 and c['low'] <= zHi) or (d < 0 and c['high'] >= zLo):
                touched = True
                ext = c['low'] if d > 0 else c['high']
        else:
            e = c['low'] if d > 0 else c['high']
            if (d > 0 and e < ext) or (d < 0 and e > ext):
                ext = e
        if not touched:
            continue
        bd = c['ofBarDelta']
        if bd is not None and abs(bd) >= Q_BD75 and bd * d < 0:
            flow_ok = True
        if (d > 0 and c['close'] > mid) or (d < 0 and c['close'] < mid):
            span = zHi - zLo
            depth = ((zHi - ext) / span) if d > 0 else ((ext - zLo) / span)
            return {'j': k, 'depth': depth, 'ext': ext, 'flow': flow_ok}
    return None


def generate(B):
    """Returns {candidate: [event, ...]} after the chronological cooldown.
    An event is a dict with: id, cand, j, d, entry_px, R, stop_ref kind,
    trigger-bar extreme, parent reference bar, and meta."""
    N = len(B)
    consec, entry_ok = make_ctx(B)
    SIGS = ofh6_signals(B)
    CTX = Ctx(SIGS, B)
    FVG_AT = build_fvg(B, consec)
    raw = defaultdict(list)

    def emit(cand, j, d, entry_px, R, parent_j, struct_ref, meta):
        if not entry_ok(j) or R is None or R <= 0:
            return
        raw[cand].append({'cand': cand, 'j': j, 'd': d, 'entry_px': entry_px,
                          'R': R, 'parent_j': parent_j, 'struct_ref': struct_ref,
                          'meta': meta})

    # ---- G1 (overlay lineage, also scored standalone) and G3 ----------
    for js, d in SIGS:
        if not entry_ok(js):
            continue
        e0, atr = B[js]['close'], B[js]['atr']
        lim = e0 - d * G1_DEPTH_ATR * atr
        for k in range(js + 1, min(js + LIFE + 1, N)):
            if not consec(k, js) or CTX.opposite_in(d, B[js]['tmin'], B[k]['tmin']):
                break
            c = B[k]
            if (d > 0 and c['low'] <= lim) or (d < 0 and c['high'] >= lim):
                emit('G1', k, d, lim, atr, js, None,
                     {'limit': lim, 'sig_j': js, 'through': (lim - c['low']) if d > 0
                      else (c['high'] - lim)})
                break
        k = js + G3_DELAY_MIN
        if k < N and consec(k, js) and not CTX.opposite_in(d, B[js]['tmin'], B[k]['tmin']):
            c = B[k]
            if (d > 0 and c['close'] < e0) or (d < 0 and c['close'] > e0):
                emit('G3', k, d, c['close'], B[k]['atr'], js, None,
                     {'sig_j': js, 'discount': (e0 - c['close']) * d})

    # ---- G4 -----------------------------------------------------------
    EB = [j for j in range(N) if entry_ok(j)]
    for j in EB:
        b = B[j]
        if b['disp5'] is None or not b['atr'] or abs(b['disp5']) < G4_TREND_ATR * b['atr']:
            continue
        t = 1 if b['disp5'] > 0 else -1
        bd = b['ofBarDelta']
        if bd is None or bd * t >= 0 or abs(bd) < Q_BD75:
            continue
        if not CTX.ok_at(t, b['tmin'], LIFE):
            continue
        for k in range(j + 1, min(j + G4_WINDOW + 1, N)):
            if not consec(k, j):
                break
            if (t > 0 and B[k]['low'] < b['low']) or (t < 0 and B[k]['high'] > b['high']):
                break
            if (t > 0 and B[k]['high'] > b['high']) or (t < 0 and B[k]['low'] < b['low']):
                ref = b['low'] if t > 0 else b['high']
                R = (B[k]['close'] - (ref - TICK)) if t > 0 else ((ref + TICK) - B[k]['close'])
                emit('G4', k, t, B[k]['close'], R, j, ref, {'attack_j': j})
                break

    # ---- OFH13 / OFH14 -------------------------------------------------
    for js, d in SIGS:
        ts = B[js]['tmin']
        prev = ts
        for k in range(js + 1, N):
            if B[k]['tmin'] != prev + 1:
                break
            prev = B[k]['tmin']
            if B[k]['tmin'] - ts > LIFE:
                break
            got = None
            for f in FVG_AT.get(k, ()):
                if f['d'] == d:
                    got = f
                    break
            if got is None:
                continue
            far = got['zLo'] if d > 0 else got['zHi']
            m = _mitigate(B, got, k + 1, ts + LIFE)
            if m is not None:
                te = B[m['j']]['tmin']
                if not CTX.opposite_in(d, ts, te):
                    e = B[m['j']]['close']
                    R = (e - (far - TICK)) if d > 0 else ((far + TICK) - e)
                    meta = {'depth': m['depth'], 'flow': m['flow'], 'fvg_j': got['j'],
                            'zLo': got['zLo'], 'zHi': got['zHi'], 'mid': got['mid'],
                            'sig_j': js}
                    emit('OFH14', m['j'], d, e, R, js, far, meta)
                    if m['flow'] and m['depth'] < 1.0:
                        emit('OFH13', m['j'], d, e, R, js, far, dict(meta))
            break

    out = {}
    for cand, lst in raw.items():
        lst.sort(key=lambda x: B[x['j']]['tmin'])
        keep = []
        last = -10 ** 9
        for ev in lst:
            if cand not in ('G1', 'G3'):      # per-signal families keep all
                if B[ev['j']]['tmin'] - last < COOL:
                    continue
                last = B[ev['j']]['tmin']
            ev['et'] = B[ev['j']]['et']
            ev['day'] = B[ev['j']]['day']
            ev['w'] = window_of(ev['day'])
            ev['atr'] = B[ev['j']]['atr']
            ev['id'] = '%s-%s-%s' % (cand, ev['et'].replace('-', '').replace(':', '')
                                     .replace(' ', ''), '+1' if ev['d'] > 0 else '-1')
            keep.append(ev)
        out[cand] = keep
    for c in list(CANDIDATES) + [OVERLAY]:
        out.setdefault(c, [])
    return out, SIGS, CTX


if __name__ == '__main__':
    B = load_merged()
    EV, SIGS, _ = generate(B)
    print('bars %d  %s .. %s' % (len(B), B[0]['et'], B[-1]['et']))
    print('OFH6 signals %d' % len(SIGS))
    for c in list(CANDIDATES) + [OVERLAY]:
        w = defaultdict(int)
        for e in EV[c]:
            w[e['w']] += 1
        print('  %-6s n=%4d   UNSEEN %3d  DEV %3d  IR %3d'
              % (c, len(EV[c]), w['UNSEEN'], w['DEV'], w['IR']))
