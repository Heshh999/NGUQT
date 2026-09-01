#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01.1 — CAUSAL ONE-HOUR SUPPLY/DEMAND-ZONE CONTEXT MODULE
# Additive successor module; the predecessor engine never imports it.
# Context only — a zone can never create an entry, stop, or target.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections

TICK = 0.25
EPS = 1e-9
SPEC_VERSION = 'H1Z-1.0.0'

UNVERIFIED = 'H1_ZONE_UNVERIFIED_CONTEXT'


# ---------------------------------------------------------------------
# certification: exact contract identity, aligned completed hours
# ---------------------------------------------------------------------
def certify_bars(bars):
    """bars: [{t_open,t_close,o,h,l,c,contract,last_event_t}]. Returns
    'CERTIFIED' or H1_ZONE_UNVERIFIED_CONTEXT. Continuous/back-adjusted
    series (no true contract id) fail."""
    if not bars:
        return UNVERIFIED
    for b in bars:
        cid = b.get('contract', '')
        if not cid or 'CONT' in cid.upper():
            return UNVERIFIED
        if b['t_close'] - b['t_open'] != 3600:
            return UNVERIFIED
        if b.get('last_event_t') is None or b['last_event_t'] > b['t_close']:
            return UNVERIFIED
    return 'CERTIFIED'


def true_range(bar, prev_close):
    return max(bar['h'] - bar['l'], abs(bar['h'] - prev_close),
               abs(bar['l'] - prev_close))


def body_fraction(bar):
    return abs(bar['c'] - bar['o']) / (bar['h'] - bar['l'] + EPS)


class SlotBaseline:
    """Median/MAD of TR per one-hour session slot over the previous 20
    completed sessions. Current session never contributes."""

    def __init__(self, n=20):
        self.hist = collections.defaultdict(lambda: collections.deque(maxlen=n))
        self.cur = {}

    def observe(self, slot, tr):
        self.cur[slot] = tr

    def close_session(self):
        for slot, tr in self.cur.items():
            self.hist[slot].append(tr)
        self.cur = {}

    def z(self, slot, tr):
        vals = sorted(self.hist[slot])
        if len(vals) < 5:
            return None
        med = vals[len(vals) // 2]
        mad = sorted(abs(v - med) for v in vals)[len(vals) // 2]
        if mad <= 0:
            return None
        return (tr - med) / (1.4826 * mad)


# ---------------------------------------------------------------------
# the ONE frozen base-and-displacement construction
# ---------------------------------------------------------------------
def find_zone_at(bars, trz, i):
    """Test bar i as the displacement bar. bars must be COMPLETED
    hourly bars in order; trz[i] = causal TR_z of bar i. Returns a zone
    dict or None. No alternative definitions may be tested."""
    b = bars[i]
    z = trz[i]
    if z is None or z < 2.0 or body_fraction(b) < 0.60:
        return None
    up = b['c'] > b['o']
    dn = b['c'] < b['o']
    if not (up or dn):
        return None
    # walk back through consecutive compact bars (>=1, most recent <=3)
    base = []
    j = i - 1
    run = 0
    while j >= 0:
        zj = trz[j]
        if zj is None or zj > 0.0 or body_fraction(bars[j]) > 0.60:
            break
        run += 1
        if len(base) < 3:
            base.insert(0, j)
        j -= 1
    if not base:
        return None
    first_base = base[0]
    if first_base - 5 < 0:
        return None
    swing = bars[first_base - 5:first_base]      # excludes base + displacement
    swing_high = max(x['h'] for x in swing)
    swing_low = min(x['l'] for x in swing)
    bb = [bars[k] for k in base]
    base_high = max(x['h'] for x in bb)
    base_low = min(x['l'] for x in bb)
    if up:
        if not (b['c'] >= base_high + TICK and b['c'] >= swing_high + TICK):
            return None
        distal = base_low
        proximal = max(max(x['o'], x['c']) for x in bb)
        direction = 'DEMAND'
    else:
        if not (b['c'] <= base_low - TICK and b['c'] <= swing_low - TICK):
            return None
        distal = base_high
        proximal = min(min(x['o'], x['c']) for x in bb)
        direction = 'SUPPLY'
    lo, hi = (distal, proximal) if direction == 'DEMAND' else (proximal, distal)
    if not hi - lo > 0:
        return None
    return dict(id='%s|%s|%d|%s|%.2f-%.2f|%d|%s'
                   % (b.get('instrument', 'NQ'), b['contract'],
                      bars[first_base]['t_open'], direction, lo, hi,
                      b['t_close'], SPEC_VERSION),
                direction=direction, lo=lo, hi=hi, width=hi - lo,
                distal=distal, proximal=proximal,
                available_from=b['t_close'], contract=b['contract'],
                base_run_total=run, base_used=len(base),
                trz=z, body=body_fraction(b),
                state='FRESH', touches=0, intrabar_breaches=0)


def scan_zones(bars, trz):
    out = []
    for i in range(len(bars)):
        zn = find_zone_at(bars, trz, i)
        if zn:
            out.append(zn)
    return out


# ---------------------------------------------------------------------
# lifecycle
# ---------------------------------------------------------------------
class ZoneTracker:
    def __init__(self, zone):
        self.z = zone
        self._inside = False
        self._away_extreme = None      # farthest distance since last exit

    def on_trade(self, t, px):
        z = self.z
        if t < z['available_from'] or z['state'] in ('INVALIDATED',
                                                     'ROLLED_OFF'):
            return
        inside = z['lo'] <= px <= z['hi']
        if inside:
            need = max(z['width'], 4 * TICK)
            if not self._inside and \
                    (z['touches'] == 0 or
                     (self._away_extreme is not None and
                      self._away_extreme >= need)):
                z['touches'] += 1
                z['state'] = 'TOUCHED'
            self._inside = True
            self._away_extreme = None
        else:
            d = min(abs(px - z['lo']), abs(px - z['hi']))
            if self._inside:
                self._away_extreme = d
            elif self._away_extreme is not None:
                self._away_extreme = max(self._away_extreme, d)
            self._inside = False
        # intrabar distal breach is recorded, never an invalidation
        if (z['direction'] == 'DEMAND' and px <= z['distal'] - TICK) or \
                (z['direction'] == 'SUPPLY' and px >= z['distal'] + TICK):
            z['intrabar_breaches'] += 1

    def on_hour_close(self, bar):
        z = self.z
        if bar['t_close'] <= z['available_from']:
            return
        if bar.get('contract') != z['contract']:
            z['state'] = 'ROLLED_OFF'
            return
        if (z['direction'] == 'DEMAND' and z['distal'] - bar['c'] >= TICK) or \
                (z['direction'] == 'SUPPLY' and bar['c'] - z['distal'] >= TICK):
            z['state'] = 'INVALIDATED'


# ---------------------------------------------------------------------
# event context labeling + clustering + diagnostic geometry
# ---------------------------------------------------------------------
def label_event(price, direction, zones, radius, now_t):
    """CONFLICT evaluated first; zones must be available and active."""
    act = [z for z in zones if z['state'] in ('FRESH', 'TOUCHED')
           and now_t >= z['available_from']]
    near = lambda z: (z['lo'] - radius) <= price <= (z['hi'] + radius)
    sup = any(near(z) for z in act if z['direction'] == 'SUPPLY')
    dem = any(near(z) for z in act if z['direction'] == 'DEMAND')
    if sup and dem:
        return 'H1_ZONE_CONFLICT'
    if (direction > 0 and dem) or (direction < 0 and sup):
        return 'ALIGNED_H1_ZONE'
    if (direction > 0 and sup) or (direction < 0 and dem):
        return 'OPPOSING_H1_ZONE'
    return 'NO_H1_ZONE'


def family_counts_v011(base_counts, price, zones, radius, now_t):
    """Extends the predecessor clustering result WITHOUT modifying it:
    H1 zones contribute one experimental flag, never a base count."""
    act = [z for z in zones if z['state'] in ('FRESH', 'TOUCHED')
           and now_t >= z['available_from']
           and (z['lo'] - radius) <= price <= (z['hi'] + radius)]
    out = dict(base_counts)
    out['h1_zone_experimental_present'] = bool(act)
    return out


def available_R_h1(entry, stop, direction, zones, now_t):
    """Diagnostic only: first PROXIMAL boundary of the nearest active
    opposing zone ahead of the trade. Base Available_R stays primary."""
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    opp = 'SUPPLY' if direction > 0 else 'DEMAND'
    cands = []
    for z in zones:
        if z['direction'] != opp or z['state'] not in ('FRESH', 'TOUCHED') \
                or now_t < z['available_from']:
            continue
        if (direction > 0 and z['proximal'] > entry) or \
                (direction < 0 and z['proximal'] < entry):
            cands.append(abs(z['proximal'] - entry))
    return (min(cands) / risk) if cands else None
