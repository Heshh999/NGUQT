#!/usr/bin/env python3
# ======================================================================
# MROF-V1 — MULTI-RESOLUTION ORDER-FLOW FEATURE ENGINE
# ======================================================================
# Consumes the authoritative MLES-CAPTURE-1.0.0 raw event files
# (recorder: src/MlesV1CaptureHost.cs, Freeze A c40f39a). This module
# is STATE-A infrastructure: it parses raw events, audits integrity,
# aggregates causally at every frozen resolution, and computes the
# tier-limited feature library.
#
# THE ENGINE COMPUTES NO OUTCOME. There is no forward-return, label,
# PnL, or signal-ranking function in this module, and none may be added
# outside a committed State-C readiness freeze (research_unlocked()).
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import csv
import hashlib
import json
import os

SCHEMA = 'MLES-CAPTURE-1.0.0'
TICK = 0.25
RESOLUTIONS = {'30s': 30, '1m': 60, '3m': 180, '5m': 300,
               '10m': 600, '15m': 900, '60m': 3600, '4h': 14400}

# State-C authorization gate: outcome research requires this file to
# exist AND name a readiness-freeze commit. It does not exist in State A.
STATE_C_AUTH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'MROF_V1_STATE_C_AUTHORIZED.json')


def research_unlocked():
    """True only after a committed State-C readiness freeze."""
    if not os.path.exists(STATE_C_AUTH):
        return False
    try:
        a = json.load(open(STATE_C_AUTH))
        return bool(a.get('readiness_freeze_commit')) and \
            bool(a.get('all_gates_passed'))
    except Exception:
        return False


# ---------------------------------------------------------------------
# parsing + integrity (raw files are never modified; findings are
# reported in a derived integrity record with the raw file untouched)
# ---------------------------------------------------------------------
def avail_time(row):
    """Causal availability clock: the LATER of exchange and receive
    time governs any simulation (frozen MLES rule)."""
    ts = [float(row[k]) for k in ('tExch', 'tRecv')
          if row.get(k) not in (None, '', 'NaN')]
    return max(ts) if ts else None


def parse_stream(path, expect_stream):
    """Parse one raw CSV. Returns (rows, integrity dict). Raw order is
    preserved; nothing is dropped — duplicates/gaps are only counted."""
    rows = []
    integ = dict(rows=0, schema_bad=0, seq_gaps=0, seq_dups=0,
                 trecv_reversals=0, contracts=set(), flags=collections.Counter())
    last_seq = None
    last_recv = None
    with open(path, newline='') as fh:
        for r in csv.DictReader(fh):
            integ['rows'] += 1
            if r.get('schema') != SCHEMA:
                integ['schema_bad'] += 1
            if r.get('stream') and r['stream'] != expect_stream:
                raise ValueError('stream mismatch: %s in %s'
                                 % (r['stream'], path))
            if r.get('contract'):
                integ['contracts'].add(r['contract'])
            s = int(r['seq']) if r.get('seq') else None
            if s is not None and last_seq is not None:
                if s == last_seq:
                    integ['seq_dups'] += 1
                elif s > last_seq + 1:
                    integ['seq_gaps'] += 1
            last_seq = s if s is not None else last_seq
            tv = float(r['tRecv']) if r.get('tRecv') else None
            if tv is not None and last_recv is not None and tv < last_recv:
                integ['trecv_reversals'] += 1
            last_recv = tv if tv is not None else last_recv
            if r.get('flags'):
                integ['flags'][r['flags']] += 1
            rows.append(r)
    if len(integ['contracts']) > 1:
        raise ValueError('SILENT CONTRACT MIX in %s: %s'
                         % (path, sorted(integ['contracts'])))
    integ['contracts'] = sorted(integ['contracts'])
    integ['flags'] = dict(integ['flags'])
    return rows, integ


# ---------------------------------------------------------------------
# Tier-1 features: trade classification and delta
# ---------------------------------------------------------------------
def trade_sign(row):
    """Frozen QUOTE_TEST_v1 consumption: honest 0 for unclassifiable.
    aggrRaw is never used (recorded ABSENT by the feed)."""
    if row.get('aggrConf') in (None, '', 'NONE'):
        return 0
    a = row.get('aggrInf', '')
    return 1 if a == 'BUY' else -1 if a == 'SELL' else 0


def trade_delta(trades):
    """TD, classified volume, unknown share, NTD, count imbalance."""
    td = cv = uv = 0.0
    nb = ns = 0
    for r in trades:
        sz = float(r['sz'])
        s = trade_sign(r)
        if s == 0:
            uv += sz
            continue
        td += s * sz
        cv += sz
        nb += s > 0
        ns += s < 0
    tot = cv + uv
    return dict(TD=td, classified_vol=cv, unknown_share=uv / tot if tot else None,
                NTD=td / cv if cv else None,
                count_imbalance=(nb - ns) / (nb + ns) if nb + ns else None)


def cum_session_delta(trades_by_session):
    """Cumulative delta with frozen reset at every ET session boundary
    (the capture's native 18:00 ET session roll)."""
    out = {}
    for ses in sorted(trades_by_session):
        c = 0.0
        path = []
        for r in trades_by_session[ses]:
            c += trade_sign(r) * float(r['sz'])
            path.append(c)
        out[ses] = path
    return out


# ---------------------------------------------------------------------
# Tier-2 features: OFI, microprice, spread state
# ---------------------------------------------------------------------
def ofi_increment(prev, cur):
    """Cont-Kukanov-Stoikov best-level OFI event increment:
    e = I(Pb>=Pb')Qb - I(Pb<=Pb')Qb' - I(Pa<=Pa')Qa + I(Pa>=Pa')Qa'."""
    pb0, qb0 = float(prev['bidPx']), float(prev['bidSz'])
    pa0, qa0 = float(prev['askPx']), float(prev['askSz'])
    pb1, qb1 = float(cur['bidPx']), float(cur['bidSz'])
    pa1, qa1 = float(cur['askPx']), float(cur['askSz'])
    e = 0.0
    e += qb1 if pb1 >= pb0 else 0.0
    e -= qb0 if pb1 <= pb0 else 0.0
    e -= qa1 if pa1 <= pa0 else 0.0
    e += qa0 if pa1 >= pa0 else 0.0
    return e


def ofi_sum(quotes):
    return sum(ofi_increment(quotes[i - 1], quotes[i])
               for i in range(1, len(quotes)))


def quote_state(row):
    """Spread in ticks + locked/crossed/invalid classification."""
    try:
        b, a = float(row['bidPx']), float(row['askPx'])
        bs, asz = float(row['bidSz']), float(row['askSz'])
    except (KeyError, TypeError, ValueError):
        return dict(state='INVALID', spread_ticks=None, microprice=None)
    if bs <= 0 or asz <= 0:
        return dict(state='INVALID', spread_ticks=None, microprice=None)
    if b > a:
        st = 'CROSSED'
    elif b == a:
        st = 'LOCKED'
    else:
        st = 'VALID'
    micro = (a * bs + b * asz) / (bs + asz) if st == 'VALID' else None
    return dict(state=st, spread_ticks=(a - b) / TICK,
                microprice=micro,
                micro_minus_mid=(micro - (a + b) / 2.0) if micro else None)


# ---------------------------------------------------------------------
# Tier-2/3 features: depth imbalance, depletion/replenishment
# ---------------------------------------------------------------------
def depth_imbalance(bid_sizes, ask_sizes, K):
    """DI over frozen level set K (list index 0 = best)."""
    b = sum(bid_sizes[:K])
    a = sum(ask_sizes[:K])
    if b + a <= 0:
        return None
    return (b - a) / (b + a)


def best_level_depletion(quotes, side, frac=0.5):
    """Primitive: episodes where displayed best-side size drops by
    >= frac of its running episode max at an unchanged price, and the
    time until size recovers to >= frac of that max. MBP data cannot
    distinguish cancel from execution removal; episodes carry no such
    label (frozen honesty rule)."""
    px_k, sz_k = ('bidPx', 'bidSz') if side == 'bid' else ('askPx', 'askSz')
    eps = []
    cur_px, mx, low, t0 = None, 0.0, None, None
    for q in quotes:
        px, sz = float(q[px_k]), float(q[sz_k])
        t = avail_time(q)
        if px != cur_px:
            cur_px, mx, low, t0 = px, sz, None, None
            continue
        mx = max(mx, sz)
        if low is None and mx > 0 and sz <= (1 - frac) * mx:
            low, t0 = sz, t
        elif low is not None and sz >= frac * mx:
            eps.append(dict(px=px, peak=mx, trough=low,
                            recover_s=(t - t0) if t and t0 else None))
            low, t0 = None, None
    return eps


# ---------------------------------------------------------------------
# Tier-1 intensity / event time
# ---------------------------------------------------------------------
def intensity(trades, t0, t1):
    n = v = 0.0
    sv = 0.0
    gaps = []
    last = None
    for r in trades:
        t = avail_time(r)
        if t is None or not (t0 <= t < t1):
            continue
        n += 1
        v += float(r['sz'])
        sv += trade_sign(r) * float(r['sz'])
        if last is not None:
            gaps.append(t - last)
        last = t
    dt = t1 - t0
    return dict(trades_per_s=n / dt, contracts_per_s=v / dt,
                signed_per_s=sv / dt,
                median_intertrade_s=sorted(gaps)[len(gaps) // 2] if gaps else None)


# ---------------------------------------------------------------------
# causal multi-resolution aggregation (close-stamped, complete-only)
# ---------------------------------------------------------------------
def bars(trades, quotes, res_s, end_of_stream_proof=None):
    """Aggregate events into res_s-second bars keyed by close stamp
    (bucket end, epoch seconds). A bar is emitted ONLY when completion
    is proven: some later event has avail >= bucket end, or
    end_of_stream_proof (e.g. SESSION_END quality time) >= bucket end.
    Incomplete tail bars are never emitted."""
    ev = []
    for r in trades:
        t = avail_time(r)
        if t is not None:
            ev.append((t, 'T', r))
    for r in quotes:
        t = avail_time(r)
        if t is not None:
            ev.append((t, 'Q', r))
    ev.sort(key=lambda x: x[0])
    if not ev:
        return {}
    last_avail = ev[-1][0]
    proof = max(last_avail, end_of_stream_proof or last_avail)
    buckets = collections.defaultdict(lambda: dict(trades=[], quotes=[]))
    for t, k, r in ev:
        b = (int(t // res_s) + 1) * res_s      # close stamp
        buckets[b]['trades' if k == 'T' else 'quotes'].append(r)
    out = {}
    for close_stamp in sorted(buckets):
        if close_stamp > proof:
            continue                            # completion not proven
        tr = buckets[close_stamp]['trades']
        qs = buckets[close_stamp]['quotes']
        px = [float(r['px']) for r in tr]
        bar = dict(close_stamp=close_stamp, n_trades=len(tr),
                   n_quotes=len(qs),
                   o=px[0] if px else None, h=max(px) if px else None,
                   l=min(px) if px else None, c=px[-1] if px else None,
                   vol=sum(float(r['sz']) for r in tr))
        bar.update(trade_delta(tr))
        bar['OFI'] = ofi_sum(qs) if len(qs) >= 2 else 0.0
        out[close_stamp] = bar
    return out


def features_at(all_bars, t):
    """Leakage guard: only bars whose close stamp <= t are visible."""
    return {res: {cs: b for cs, b in bb.items() if cs <= t}
            for res, bb in all_bars.items()}


# ---------------------------------------------------------------------
# parent-event declustering
# ---------------------------------------------------------------------
def decluster(triggers, cooldown_s):
    """triggers: [(time, resolution, tag)]. The same burst seen at
    several resolutions is ONE causal event: a trigger within
    cooldown_s of the cluster START joins that cluster; otherwise it
    starts a new parent. Returns [(parent_id, [members...])]."""
    out = []
    cur, start = [], None
    for t in sorted(triggers, key=lambda x: x[0]):
        if start is not None and t[0] - start <= cooldown_s:
            cur.append(t)
        else:
            if cur:
                out.append(('P%06d' % int(start), cur))
            cur, start = [t], t[0]
    if cur:
        out.append(('P%06d' % int(start), cur))
    return out


# ---------------------------------------------------------------------
# execution model (non-colocated; marketable only; passive prohibited
# without a queue model this MBP feed cannot support)
# ---------------------------------------------------------------------
def next_executable_fill(quotes, decision_t, side, latency_s,
                         slippage_ticks=0.0):
    """First VALID quote with avail STRICTLY AFTER decision+latency;
    long fills at ask, short at bid, plus stressed slippage. The event
    that completed the signal can never be the fill event."""
    rel = decision_t + latency_s
    for q in quotes:
        t = avail_time(q)
        if t is None or t <= rel:
            continue
        st = quote_state(q)
        if st['state'] != 'VALID' or 'DISCONNECTED' in (q.get('flags') or ''):
            continue
        px = float(q['askPx']) if side > 0 else float(q['bidPx'])
        return px + side * slippage_ticks * TICK, t
    return None, None


def round_trip_cost(commission_pts=0.87, spread_ticks=None,
                    extra_slippage_ticks=0.0):
    """Cost per round trip in index points (commission convention is
    the house 0.87 base; spread is paid via bid/ask fill prices, so it
    is added only when fills were NOT taken from real quotes)."""
    c = commission_pts + extra_slippage_ticks * TICK
    if spread_ticks is not None:
        c += spread_ticks * TICK
    return c


# ---------------------------------------------------------------------
# reproducibility
# ---------------------------------------------------------------------
def digest(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


if __name__ == '__main__':
    print('MROF-V1 engine module. State-C research unlocked: %s'
          % research_unlocked())
    print('No outcome computation exists in this module by design.')
