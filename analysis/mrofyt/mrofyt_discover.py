#!/usr/bin/env python3
"""mrofyt_discover.py - MROF-YT-W4-DISCOVER-1.0

MROF_YT_WAVE4_DISCOVERY_REGISTRATION.md turned into running code: a
COUNTED search of the DEV tape for order-flow conditions that precede
25-point moves, and the checkpoint evaluator for whatever it nominates.

    search    736 rules (14 causal grid features; singles at decile
              tails, pairs at quintile tails; direction part of the
              rule) x 3 stops = 2 208 tests, each scored with wave
              three's path score against an hour-matched baseline,
              session-clustered t, Benjamini-Hochberg over all 2 208,
              replication in both chronological halves of DEV. At most
              five rules are NOMINATED, written out with numeric
              cut-points. Nothing found here is a result.
    evaluate  the nominated rules, frozen, scored once on the
              validation sessions (--unblind), Holm over the set.

The runner subclasses wave three's, which subclasses the pilot's; hooks
only. One read of the DEV tape also yields wave three's real-level
report (--w3-out).

    python3 mrofyt_discover.py "<capture>" --out w4.json \\
            --nominated-out w4_nominated.json --w3-out w3.json
    python3 mrofyt_discover.py "<capture>" --evaluate w4_nominated.json \\
            --out w4_eval_dev.json          # DEV only: reproduces search
    python3 mrofyt_discover.py "<capture>" --evaluate w4_nominated.json \\
            --unblind --out w4_eval.json    # CHECKPOINT ONLY

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import functools
import json
import math
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_levels as LV
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

W4_VERSION = 'MROF-YT-W4-DISCOVER-1.0'
REGISTRATION = 'MROF_YT_WAVE4_DISCOVERY_REGISTRATION.md'
DEV_END = BM.DEV_END

# registration 1: the feature set
SIGNED = ('z_delta', 'z_d60', 'z_d180', 'z_ofi', 'z_bi3', 'resp',
          'resp60', 'resp180', 'trend30', 'dist_vwap')
UNSIGNED = ('z_n10', 'spread', 'range30', 'dist_level')
FEATURES = SIGNED + UNSIGNED
RANGE30_MIN_TICKS = 171                      # of the 181 in 30 minutes

# registration 2: the grammar
DECILE = ('decile', 0.10)
QUINTILE = ('quintile', 0.20)
DEGENERATE_FACTOR = 1.5
N_RULES = 736
STOPS = BM.STOPS_TICKS                       # 40, 60, 80 ticks
K_TESTS = N_RULES * len(STOPS)               # 2 208

# registration 3-6
COOLDOWN_S = 300.0
FDR_Q = 0.10
MIN_EVENTS = 30
MIN_SESSIONS = 6
MIN_HALF = 10
NOMINATE_MAX = 5
NOMINATE_P = 0.05
OVERLAP_MAX = 0.5
HOLM_ALPHA = 0.05
FRICTION_POINTS = dict(NQ=0.09, MNQ=0.91)    # wave two's, pending sign-off
POINT = 4.0
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT        # NQ


# ---------------------------------------------------------------------
# statistics: Student t, Benjamini-Hochberg, Holm (stdlib only)
# ---------------------------------------------------------------------
def _betacf(a, b, x):
    fpmin = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > fpmin else fpmin)
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c
        c = c if abs(c) > fpmin else fpmin
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c
        c = c if abs(c) > fpmin else fpmin
        de = d * c
        h *= de
        if abs(de - 1.0) < 3e-14:
            break
    return h


def betai(a, b, x):
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) +
                  a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_p_two_sided(t, df):
    if df <= 0 or t is None:
        return None
    return betai(df / 2.0, 0.5, df / (df + t * t))


@functools.lru_cache(maxsize=None)
def t_crit(df, p=0.05):
    """t with two-sided tail p, by bisection (cached: df is small)."""
    lo, hi = 0.0, 1000.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_p_two_sided(mid, df) > p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def bh_q(pvals, m=None):
    """Benjamini-Hochberg q-values; None p stays None and counts in m."""
    m = len(pvals) if m is None else m
    order = sorted((i for i, p in enumerate(pvals) if p is not None),
                   key=lambda i: pvals[i])
    q = [None] * len(pvals)
    prev = 1.0
    for rank in range(len(order), 0, -1):
        i = order[rank - 1]
        prev = min(prev, pvals[i] * m / rank)
        q[i] = prev
    return q


holm = BM.holm


def cluster_stats(rows, df_min=1):
    """rows: [(session, obs 1/0, exp rate, value ticks)].
    Lift = hit - mean expectation; SE cluster-robust by session (ratio
    estimator), t on G-1 degrees of freedom, two-sided p."""
    n = len(rows)
    if not n:
        return dict(n=0, sessions=0)
    by = collections.defaultdict(lambda: [0, 0.0, 0.0])
    so = se_ = sv = 0.0
    for ses, o, e, v in rows:
        b = by[ses]
        b[0] += 1
        b[1] += o - e
        so += o
        se_ += e
        sv += v
    lift = (so - se_) / n
    G = len(by)
    out = dict(n=n, sessions=G, hit=round(so / n, 4),
               baseline=round(se_ / n, 4), lift=round(lift, 4),
               expectancy_ticks=round(sv / n, 2),
               expectancy_points=round(sv / n / POINT, 2))
    if G >= 2:
        ss = sum((b[1] - lift * b[0]) ** 2 for b in by.values())
        var = G / (G - 1.0) * ss / (n * n)
        se = math.sqrt(var)
        # sessions that agree to the last decimal (synthetic tape) give a
        # standard error of ~0 and an absurd t: no p rather than p = 1e-80
        if se > 1e-9:
            t = lift / se
            df = G - 1
            tc = t_crit(df)
            out.update(se=round(se, 5), t=round(t, 3), df=df,
                       p=t_p_two_sided(t, df),
                       ci95=(round(lift - tc * se, 4),
                             round(lift + tc * se, 4)))
    return out


# ---------------------------------------------------------------------
# the grammar (registration 2): 736 rules, enumerated in a fixed order
# ---------------------------------------------------------------------
def enumerate_rules():
    rules = []
    for f in SIGNED:
        for tail in ('top', 'bottom'):
            for dk in ('with', 'against'):
                rules.append(dict(family='S', parts=[(f, tail, 'decile')],
                                  dir_kind=dk, dir_ref=f))
    for u in UNSIGNED:
        for tail in ('top', 'bottom'):
            for dk in ('with', 'against'):
                rules.append(dict(family='U', parts=[(u, tail, 'decile')],
                                  dir_kind=dk, dir_ref='D60'))
    for i, f in enumerate(SIGNED):
        for g in SIGNED[i + 1:]:
            for tf in ('top', 'bottom'):
                for tg in ('top', 'bottom'):
                    for dk in ('with', 'against'):
                        rules.append(dict(
                            family='SS',
                            parts=[(f, tf, 'quintile'), (g, tg, 'quintile')],
                            dir_kind=dk, dir_ref=f))
    for u in UNSIGNED:
        for f in SIGNED:
            for tu in ('top', 'bottom'):
                for tf in ('top', 'bottom'):
                    for dk in ('with', 'against'):
                        rules.append(dict(
                            family='US',
                            parts=[(u, tu, 'quintile'), (f, tf, 'quintile')],
                            dir_kind=dk, dir_ref=f))
    for r in rules:
        r['id'] = '%s:%s:%s:%s' % (
            r['family'], '+'.join('%s.%s.%s' % (f, t, lv[0])
                                  for f, t, lv in r['parts']),
            r['dir_kind'], r['dir_ref'])
    return rules


def rule_text(r):
    """'z_d60 in its top 10% AND resp60 in its bottom 20% -> long with
    z_d60' in words, for the report."""
    bits = []
    for f, t, lv in r['parts']:
        bits.append('%s in its %s %s' % (f, t, '10%' if lv == 'decile'
                                          else '20%'))
    if r['dir_ref'] == 'D60':
        d = '%s the 60 s flow' % r['dir_kind']
    else:
        d = '%s %s' % (r['dir_kind'], r['dir_ref'])
    return '%s -> trade %s' % (' AND '.join(bits), d)


# ---------------------------------------------------------------------
# the runner: wave three's plus the wave-four grid features
# ---------------------------------------------------------------------
class _History(object):
    """Grid mids and flow of the current recording run, keyed by the
    10 s grid instant, for the features that need history."""

    def __init__(self):
        self.reset(None, None)

    def reset(self, run, session):
        self.run, self.session = run, session
        self.by_t = {}
        self.order = collections.deque()

    def add(self, key, mid, D):
        self.by_t[key] = (mid, D)
        self.order.append(key)
        while self.order and self.order[0] < key - 1800:
            del self.by_t[self.order.popleft()]

    def mid(self, key):
        x = self.by_t.get(key)
        return None if x is None else x[0]

    def sum_D(self, key, n):
        s = 0.0
        for k in range(n):
            x = self.by_t.get(key - 10 * k)
            if x is None or x[1] is None:
                return None
            s += x[1]
        return s

    def range_ticks(self, key):
        mids = [self.by_t[k][0] for k in self.order
                if k >= key - 1800 and self.by_t[k][0] is not None]
        if len(mids) < RANGE30_MIN_TICKS:
            return None
        return (max(mids) - min(mids)) / SIG.TICK


class DiscoverRunner(BM.BigMoveRunner):
    """Wave three's runner plus the wave-four features on every grid
    record. Hooks only; mode is always 'real' (levels are used for the
    dist_level feature only, never shifted)."""

    def __init__(self, capture_dir, unblind=False, **kw):
        BM.BigMoveRunner.__init__(self, capture_dir, mode='real',
                                  unblind=unblind, **kw)
        self.w4hist = {i: _History() for i in self.instruments}
        self.ledger['wave4'] = dict(version=W4_VERSION)

    def _close_session(self, st):
        BM.BigMoveRunner._close_session(self, st)
        self.w4hist[st.instrument].reset(None, None)

    def _observe_baselines(self, st, te):
        n0 = len(self.grid)
        BM.BigMoveRunner._observe_baselines(self, st, te)
        if len(self.grid) == n0:
            return                       # book not ready: no grid record
        g = self.grid[-1]
        h = self.w4hist[st.instrument]
        if h.run != g['run'] or h.session != st.session:
            h.reset(g['run'], st.session)
        key = int(round(te))
        mid = g.get('mid')
        h.add(key, mid, g.get('D'))
        sod = g['sod']
        z = st.baseline.z
        D60, D180 = h.sum_D(key, 6), h.sum_D(key, 18)
        if D60 is not None:
            st.baseline.observe('w4_d60', sod, D60)
        if D180 is not None:
            st.baseline.observe('w4_d180', sod, D180)
        g['D60'] = D60
        g['z_d60'] = None if D60 is None else z('w4_d60', sod, D60)
        g['z_d180'] = None if D180 is None else z('w4_d180', sod, D180)

        def back(sec):
            m0 = h.mid(key - sec)
            return None if (m0 is None or mid is None) else \
                (mid - m0) / SIG.TICK
        g['resp60'] = back(60)
        g['resp180'] = back(180)
        g['trend30'] = back(1800)
        g['range30'] = h.range_ticks(key) if mid is not None else None
        vw = st.vwap.state().get('SESSION_VWAP')
        g['dist_vwap'] = None if (vw is None or mid is None) else \
            (mid - vw) / SIG.TICK
        q = st.prev_q                    # the quote OFI is built from
        g['spread'] = None if not q else \
            (q['askPx'] - q['bidPx']) / SIG.TICK
        lv = [px for lid, px in st.levels.items()
              if lid in LV.ACTIVE_LEVEL_IDS and px is not None]
        g['dist_level'] = None if (not lv or mid is None) else \
            min(abs(mid - px) for px in lv) / SIG.TICK


# ---------------------------------------------------------------------
# per-tick path outcomes (wave three's scorer, every grid tick, both
# directions, all three stops)
# ---------------------------------------------------------------------
def tick_outcomes(r):
    """[{+1: [(outcome, value) per stop], -1: [...]} or None] aligned
    with r.grid."""
    paths = {}
    for key, (ts, ps) in r.series.items():
        if len(ts):
            paths[key] = BM.compress(ts, ps)
    want = collections.defaultdict(set)
    idx = []
    for g in r.grid:
        key = (g['instrument'], g['run'])
        if key not in paths:
            idx.append(None)
            continue
        i = bisect.bisect_right(paths[key][0], g['t']) - 1
        idx.append(i if i >= 0 else None)
        if i >= 0:
            want[key].add(i)
    index = {k: BM.PathIndex(paths[k][0], paths[k][1], w)
             for k, w in want.items()}
    out = []
    for g, i in zip(r.grid, idx):
        if i is None:
            out.append(None)
            continue
        px = index[(g['instrument'], g['run'])]
        rec = {}
        for d in (1, -1):
            row = []
            for s in STOPS:
                sc = px.score(i, d, s)
                row.append((sc['outcome'], sc['value_ticks']))
            rec[d] = row
        out.append(rec)
    return out


# ---------------------------------------------------------------------
# the engine: pure functions over (records, outcomes), so the suite can
# plant an effect and check it is found
# ---------------------------------------------------------------------
class Dataset(object):
    """One instrument's grid records and outcomes, with its hour cells
    and session order. `records` and `outcomes` are aligned lists."""

    def __init__(self, records, outcomes, sessions=None):
        self.recs = records
        self.outs = outcomes
        self.sessions = sorted(sessions if sessions is not None else
                               {r['session'] for r in records})
        half = (len(self.sessions) + 1) // 2
        self.half_of = {s: (0 if i < half else 1)
                        for i, s in enumerate(self.sessions)}
        self.cells = self._cells()

    def _cells(self):
        """{(hour, direction): [hit rate per stop]}. Direction-matched:
        a long rule is compared with every long at that hour, a short
        with every short, so a month that drifted up does not make every
        long rule look like an edge."""
        c = collections.defaultdict(lambda: [[0, 0] for _ in STOPS])
        for r, o in zip(self.recs, self.outs):
            if o is None:
                continue
            for d in (1, -1):
                cell = c[(r['hour'], d)]
                for j, (oc, _v) in enumerate(o[d]):
                    if oc == 'UNRESOLVED':
                        continue
                    cell[j][1] += 1
                    if oc == 'TARGET':
                        cell[j][0] += 1
        return {k: [(a / b if b else None) for a, b in per]
                for k, per in c.items()}


def quantile_cuts(ds, feats=FEATURES):
    """{feature: dict(n, decile=(lo, hi), quintile=(lo, hi))}."""
    cuts = {}
    for f in feats:
        vals = sorted(r[f] for r in ds.recs if r.get(f) is not None)
        n = len(vals)
        if n < 20:
            cuts[f] = dict(n=n)
            continue
        q = lambda p: vals[int(p * (n - 1))]     # noqa: E731
        cuts[f] = dict(n=n, decile=(q(0.10), q(0.90)),
                       quintile=(q(0.20), q(0.80)))
    return cuts


def tail_members(ds, f, tail, level, cut):
    """Sorted record indices in the tail, or None when the tail is
    degenerate (holds more than 1.5x its nominal share)."""
    if cut is None:
        return None
    nominal = DECILE[1] if level == 'decile' else QUINTILE[1]
    have = [k for k, r in enumerate(ds.recs) if r.get(f) is not None]
    if tail == 'top':
        mem = [k for k in have if ds.recs[k][f] >= cut]
    else:
        mem = [k for k in have if ds.recs[k][f] <= cut]
    if not have or len(mem) > DEGENERATE_FACTOR * nominal * len(have):
        return None
    return mem


def _cut_for(cuts, f, tail, level):
    c = cuts.get(f, {}).get(level)
    if c is None:
        return None
    return c[1] if tail == 'top' else c[0]


def rule_ticks(ds, rule, cuts, cache):
    """[(k, direction)] satisfying the rule, before de-duplication, or
    None when a part is untestable."""
    sets = []
    for f, tail, level in rule['parts']:
        key = (f, tail, level)
        if key not in cache:
            cache[key] = tail_members(ds, f, tail, level,
                                      _cut_for(cuts, f, tail, level))
        mem = cache[key]
        if mem is None:
            return None
        sets.append(mem)
    ks = sets[0] if len(sets) == 1 else sorted(set(sets[0]) &
                                               set(sets[1]))
    out = []
    if rule['dir_ref'] == 'D60':
        sgn = 1 if rule['dir_kind'] == 'with' else -1
        for k in ks:
            d60 = ds.recs[k].get('D60')
            if d60:
                out.append((k, sgn * (1 if d60 > 0 else -1)))
        return out
    ref_tail = [t for f, t, _l in rule['parts'] if f == rule['dir_ref']][0]
    d = 1 if ref_tail == 'top' else -1
    if rule['dir_kind'] == 'against':
        d = -d
    return [(k, d) for k in ks]


def dedup_ticks(ds, ticks, cooldown=COOLDOWN_S):
    """Anchored cooldown per (session, direction), in time order."""
    ticks = sorted(ticks, key=lambda kd: (ds.recs[kd[0]]['session'],
                                          ds.recs[kd[0]]['t']))
    anchor = {}
    out = []
    for k, d in ticks:
        r = ds.recs[k]
        key = (r['session'], d)
        a = anchor.get(key)
        if a is None or r['t'] - a > cooldown:
            anchor[key] = r['t']
            out.append((k, d))
    return out


def score_rows(ds, events, j):
    rows = []
    for k, d in events:
        o = ds.outs[k]
        if o is None:
            continue
        oc, v = o[d][j]
        if oc == 'UNRESOLVED':
            continue
        exp = ds.cells.get((ds.recs[k]['hour'], d), [None] * len(STOPS))[j]
        if exp is None:
            continue
        rows.append((ds.recs[k]['session'], 1.0 if oc == 'TARGET' else 0.0,
                     exp, v))
    return rows


def rule_stats(ds, events, j):
    rows = score_rows(ds, events, j)
    st = cluster_stats(rows)
    halves = []
    for h in (0, 1):
        hr = [x for x in rows if ds.half_of.get(x[0]) == h]
        hs = cluster_stats(hr)
        halves.append(dict(n=hs['n'], lift=hs.get('lift')))
    st['halves'] = halves
    st['both_halves_positive'] = all(
        x['n'] >= MIN_HALF and x['lift'] is not None and x['lift'] > 0
        for x in halves)
    return st


def _eligible(st):
    return (st.get('n', 0) >= MIN_EVENTS and
            st.get('sessions', 0) >= MIN_SESSIONS and
            st.get('lift', 0) > 0 and st['both_halves_positive'] and
            st.get('expectancy_ticks', 0) > 0)


def search(ds, rules=None, cuts=None):
    """Registration 2-5 on one instrument. Returns (tests, cuts) where
    tests is one dict per (rule, stop), in the fixed enumeration order,
    with p, q, status."""
    rules = enumerate_rules() if rules is None else rules
    cuts = quantile_cuts(ds) if cuts is None else cuts
    cache = {}
    tests = []
    events_of = {}
    for r in rules:
        ticks = rule_ticks(ds, r, cuts, cache)
        ev = None if ticks is None else dedup_ticks(ds, ticks)
        events_of[r['id']] = ev
        for j, s in enumerate(STOPS):
            if ev is None:
                tests.append(dict(rule=r['id'], stop_ticks=s, testable=False,
                                  p=None))
                continue
            st = rule_stats(ds, ev, j)
            st.update(rule=r['id'], stop_ticks=s, testable=True,
                      events_total=len(ev))
            tests.append(st)
    q = bh_q([t.get('p') for t in tests], m=len(tests))
    for t, qq in zip(tests, q):
        t['q'] = qq
        t['status'] = ('CANDIDATE' if (t.get('testable') and qq is not None
                                       and qq <= FDR_Q and _eligible(t))
                       else None)
    return tests, cuts, events_of


def _overlap(ds, ev_a, ev_b):
    """Share of ev_a's events that have an ev_b event within the
    cooldown on the same session."""
    if not ev_a:
        return 0.0
    by = collections.defaultdict(list)
    for k, _d in ev_b:
        by[ds.recs[k]['session']].append(ds.recs[k]['t'])
    for v in by.values():
        v.sort()
    hit = 0
    for k, _d in ev_a:
        r = ds.recs[k]
        ts = by.get(r['session'], [])
        i = bisect.bisect_left(ts, r['t'] - COOLDOWN_S)
        if i < len(ts) and ts[i] <= r['t'] + COOLDOWN_S:
            hit += 1
    return hit / len(ev_a)


def nominate(ds, tests, events_of, rules_by_id):
    """Registration 5: at most five, CANDIDATEs first then by t; one stop
    per rule (its highest t); skip a rule whose events overlap a
    nominated rule's by half or more."""
    best = {}
    for t in tests:
        if not t.get('testable') or t.get('p') is None:
            continue
        if t['p'] > NOMINATE_P or not _eligible(t):
            continue
        cur = best.get(t['rule'])
        if cur is None or t['t'] > cur['t']:
            best[t['rule']] = t
    ranked = sorted(best.values(),
                    key=lambda t: (t['status'] != 'CANDIDATE', -t['t'],
                                   t['rule']))
    chosen = []
    for t in ranked:
        if len(chosen) >= NOMINATE_MAX:
            break
        ev = events_of[t['rule']]
        if any(_overlap(ds, ev, events_of[c['rule']]) >= OVERLAP_MAX
               for c in chosen):
            continue
        chosen.append(t)
    return chosen


def frozen_rule(rule, test, cuts_by_inst):
    """The nominated rule as it is committed: exact cut-points."""
    parts = []
    for f, tail, level in rule['parts']:
        parts.append(dict(feature=f, tail=tail, level=level,
                          cut={inst: _cut_for(c, f, tail, level)
                               for inst, c in cuts_by_inst.items()}))
    return dict(rule=rule['id'], text=rule_text(rule),
                family=rule['family'], parts=parts,
                dir_kind=rule['dir_kind'], dir_ref=rule['dir_ref'],
                stop_ticks=test['stop_ticks'],
                target_ticks=BM.TARGET_TICKS, limit_s=BM.LIMIT_S,
                cooldown_s=COOLDOWN_S,
                dev=dict((k, test.get(k)) for k in
                         ('n', 'sessions', 'hit', 'baseline', 'lift', 't',
                          'p', 'q', 'ci95', 'expectancy_points', 'halves',
                          'status')))


def apply_frozen(ds, fr, inst):
    """Events of a frozen rule on a dataset, with ITS cut-points."""
    rule = dict(parts=[(p['feature'], p['tail'], p['level'])
                       for p in fr['parts']],
                dir_kind=fr['dir_kind'], dir_ref=fr['dir_ref'])
    cuts = {}
    for p in fr['parts']:
        c = p['cut'].get(inst)
        lo_hi = cuts.setdefault(p['feature'], {}).setdefault(
            p['level'], [None, None])
        lo_hi[1 if p['tail'] == 'top' else 0] = c
    cuts = {f: {lv: tuple(v) for lv, v in d.items()}
            for f, d in cuts.items()}
    ticks = rule_ticks(ds, rule, cuts, {})
    return [] if ticks is None else dedup_ticks(ds, ticks)


def anatomy(ds, feats=FEATURES):
    """Registration 7: deciles of each feature against the share of
    ticks reaching +100 before -40, long and short. Descriptive."""
    out = {}
    base = [0, 0, 0, 0]
    for o in ds.outs:
        if o is None:
            continue
        for di, d in enumerate((1, -1)):
            oc = o[d][0][0]
            if oc != 'UNRESOLVED':
                base[2 * di + 1] += 1
                base[2 * di] += oc == 'TARGET'
    out['base'] = dict(long=round(base[0] / base[1], 4) if base[1] else None,
                       short=round(base[2] / base[3], 4) if base[3] else None)
    for f in feats:
        rows = [(r[f], o) for r, o in zip(ds.recs, ds.outs)
                if r.get(f) is not None and o is not None]
        if len(rows) < 100:
            out[f] = dict(n=len(rows))
            continue
        rows.sort(key=lambda x: x[0])
        n = len(rows)
        dec = []
        for k in range(10):
            part = rows[k * n // 10:(k + 1) * n // 10]
            cnt = [0, 0, 0, 0]
            for _v, o in part:
                for di, d in enumerate((1, -1)):
                    oc = o[d][0][0]
                    if oc != 'UNRESOLVED':
                        cnt[2 * di + 1] += 1
                        cnt[2 * di] += oc == 'TARGET'
            dec.append(dict(decile=k + 1, lo=round(part[0][0], 3),
                            hi=round(part[-1][0], 3),
                            long=round(cnt[0] / cnt[1], 4) if cnt[1] else None,
                            short=round(cnt[2] / cnt[3], 4) if cnt[3]
                            else None))
        out[f] = dict(n=n, deciles=dec)
    out['note'] = ('descriptive only: "what came before the big moves". '
                   'Produces no verdict and no rule.')
    return out


# ---------------------------------------------------------------------
# the two modes
# ---------------------------------------------------------------------
def _datasets(r, outs, sessions_filter=None):
    by = collections.defaultdict(lambda: ([], []))
    for g, o in zip(r.grid, outs):
        if sessions_filter is not None and not sessions_filter(g['session']):
            continue
        by[g['instrument']][0].append(g)
        by[g['instrument']][1].append(o)
    return {inst: Dataset(recs, oo) for inst, (recs, oo) in by.items()}


def run_search(capture_dir, max_sessions=None):
    r = DiscoverRunner(capture_dir, max_sessions=max_sessions)
    led = r.run()
    w3 = BM.report_from_runner(r, led)
    outs = tick_outcomes(r)
    dss = _datasets(r, outs)
    rules = enumerate_rules()
    rules_by_id = {x['id']: x for x in rules}
    cuts_by_inst = {inst: quantile_cuts(ds) for inst, ds in dss.items()}
    rep = dict(wave4=W4_VERSION, registration=REGISTRATION, mode='search',
               dev_end=DEV_END, runner=led['runner'],
               outcomes_wave_one=led['outcomes'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               n_rules=len(rules), k_tests=len(rules) * len(STOPS),
               score_rule=w3['score_rule'], cooldown_s=COOLDOWN_S)
    ds = dss.get(PRIMARY)
    nominated = []
    if ds is None:
        rep['note'] = 'no %s grid ticks were read' % PRIMARY
        return rep, w3, nominated, r
    rep['grid_ticks'] = {inst: len(d.recs) for inst, d in dss.items()}
    rep['halves'] = [[s for s in ds.sessions if ds.half_of[s] == h]
                     for h in (0, 1)]
    rep['availability'] = {f: round(sum(1 for x in ds.recs
                                        if x.get(f) is not None) /
                                    max(len(ds.recs), 1), 4)
                           for f in FEATURES}
    rep['cuts'] = cuts_by_inst
    tests, _c, events_of = search(ds, rules, cuts_by_inst[PRIMARY])
    rep['tests_untestable'] = sum(1 for t in tests if not t.get('testable'))
    rep['candidates'] = [t for t in tests if t.get('status') == 'CANDIDATE']
    ranked = sorted((t for t in tests if t.get('t') is not None),
                    key=lambda t: -t['t'])
    rep['top_by_t'] = ranked[:25]
    rep['tests'] = [dict((k, t.get(k)) for k in
                         ('rule', 'stop_ticks', 'testable', 'n', 'sessions',
                          'hit', 'baseline', 'lift', 't', 'p', 'q',
                          'expectancy_points', 'both_halves_positive',
                          'status'))
                    for t in tests]
    chosen = nominate(ds, tests, events_of, rules_by_id)
    for t in chosen:
        fr = frozen_rule(rules_by_id[t['rule']], t, cuts_by_inst)
        diag = {}
        for inst, d in dss.items():
            if inst == PRIMARY:
                continue
            ev = apply_frozen(d, fr, inst)
            j = list(STOPS).index(fr['stop_ticks'])
            s = rule_stats(d, ev, j)
            diag[inst] = dict((k, s.get(k)) for k in
                              ('n', 'sessions', 'hit', 'baseline', 'lift',
                               'expectancy_points'))
        fr['other_instruments_dev'] = diag
        nominated.append(fr)
    rep['nominated'] = nominated
    rep['anatomy'] = anatomy(ds)
    return rep, w3, nominated, r


def run_evaluate(capture_dir, frozen, unblind=False, max_sessions=None):
    r = DiscoverRunner(capture_dir, unblind=unblind, max_sessions=max_sessions)
    led = r.run()
    outs = tick_outcomes(r)
    if unblind:
        keep = lambda s: s > DEV_END          # noqa: E731
        which = 'validation (> %s)' % DEV_END
    else:
        keep = lambda s: s <= DEV_END         # noqa: E731
        which = 'DEV (<= %s), a reproduction check' % DEV_END
    dss = _datasets(r, outs, keep)
    rep = dict(wave4=W4_VERSION, registration=REGISTRATION, mode='evaluate',
               unblind=unblind, evaluated_on=which, runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({g['session'] for g in r.grid
                                          if keep(g['session'])}),
               rules=[])
    for fr in frozen:
        j = list(STOPS).index(fr['stop_ticks'])
        per = {}
        for inst, ds in dss.items():
            ev = apply_frozen(ds, fr, inst)
            st = rule_stats(ds, ev, j)
            st['events_total'] = len(ev)
            fp = FRICTION_POINTS.get(inst)
            if st.get('expectancy_points') is not None and fp is not None:
                st['expectancy_points_after_costs'] = round(
                    st['expectancy_points'] - fp, 2)
            per[inst] = st
        rep['rules'].append(dict(rule=fr['rule'], text=fr.get('text'),
                                 stop_ticks=fr['stop_ticks'], result=per))
    ps = [x['result'].get(PRIMARY, {}).get('p') for x in rep['rules']]
    rej = holm(ps)
    for x, rj in zip(rep['rules'], rej):
        s = x['result'].get(PRIMARY, {})
        if s.get('n', 0) < MIN_EVENTS:
            v = 'NOT TESTED'
        elif rj and s.get('lift', 0) > 0 and s.get('ci95') and \
                s['ci95'][0] > 0 and s.get('expectancy_ticks', 0) > 0:
            v = 'PROMISING'
        else:
            v = 'NO SIGNAL'
        x['verdict'] = v if unblind else v + ' (DEV reproduction, not a ' \
                                             'verdict)'
    return rep, r


def write_exposure_on_unblind(rep, path):
    old = []
    if os.path.exists(path):
        try:
            old = json.load(open(path)).get('exposed_days', [])
        except Exception:
            old = []
    by = {d['session']: d for d in old}
    for s in rep['sessions_inspected']:
        cur = by.get(s)
        if cur is None:
            by[s] = dict(session=s, label=PI.EXPOSURE_LABEL,
                         exposed_by=W4_VERSION, bulk_csv_present=None)
        elif cur.get('label') != PI.EXPOSURE_LABEL:
            cur.update(label=PI.EXPOSURE_LABEL, exposed_by=W4_VERSION,
                       previously_blind=True)
        by[s].setdefault('also_exposed_by', [])
        if W4_VERSION not in by[s]['also_exposed_by']:
            by[s]['also_exposed_by'].append(W4_VERSION)
    days = sorted(by.values(), key=lambda d: d['session'])
    json.dump(dict(label=PI.EXPOSURE_LABEL, blind_label=PI.BLIND_LABEL,
                   rule='EXPOSED days may remain in later DEV/training where '
                        'the governing protocol permits; they can never '
                        'become untouched prospective validation. BLIND '
                        'days had fire counts read and markouts withheld; '
                        'they remain valid validation until explicitly '
                        'unblinded, which is permanent.',
                   exposed_days=days), open(path, 'w'), indent=1)
    return len(days)


# ---------------------------------------------------------------------
# text
# ---------------------------------------------------------------------
def _fmt_test(t):
    return ('%-62s stop %2g  n=%-4s ses=%-2s hit=%-6s base=%-6s lift=%-7s '
            't=%-6s p=%-8s q=%-6s exp=%s pts  halves=%s'
            % (t['rule'][:62], t['stop_ticks'] / POINT, t.get('n'),
               t.get('sessions'), t.get('hit'), t.get('baseline'),
               t.get('lift'), t.get('t'),
               ('%.2g' % t['p']) if t.get('p') is not None else '-',
               ('%.2g' % t['q']) if t.get('q') is not None else '-',
               t.get('expectancy_points'),
               '/'.join('%s' % (h['lift'],) for h in t.get('halves', []))))


def text_search(rep):
    L = ['%s  search  registration=%s' % (rep['wave4'], rep['registration']),
         'sessions read: %s' % ', '.join(rep['sessions_inspected']),
         'sessions REFUSED (validation, > %s): %s'
         % (rep['dev_end'], ', '.join(rep['sessions_refused']) or 'none'),
         'rules %d x stops %d = %d tests (fixed before the data); '
         'untestable (degenerate tails, no data): %s'
         % (rep['n_rules'], len(STOPS), rep['k_tests'],
            rep.get('tests_untestable')),
         'score: target 25 pts, stops 10/15/20 pts, 30 min, tie=STOP, '
         'mid-to-mid, no fill/costs; cooldown %g s' % rep['cooldown_s']]
    if 'grid_ticks' not in rep:
        L.append(rep.get('note', ''))
        return '\n'.join(L)
    L.append('grid ticks: %s   DEV halves: %s | %s'
             % (rep['grid_ticks'], ','.join(rep['halves'][0]),
                ','.join(rep['halves'][1])))
    L.append('feature availability (NQ): %s' % rep['availability'])
    L.append('')
    L.append('CANDIDATES (q <= %.2f, both halves positive, %d+ events on '
             '%d+ sessions, expectancy > 0): %d'
             % (FDR_Q, MIN_EVENTS, MIN_SESSIONS, len(rep['candidates'])))
    for t in rep['candidates'][:20]:
        L.append('  ' + _fmt_test(t))
    L.append('')
    L.append('TOP 25 BY t (most are luck; read q and the halves):')
    for t in rep['top_by_t']:
        L.append('  ' + _fmt_test(t))
    L.append('')
    L.append('NOMINATED for validation (max %d): %d'
             % (NOMINATE_MAX, len(rep['nominated'])))
    for fr in rep['nominated']:
        L.append('  [%s] %s' % (
            'CANDIDATE' if fr['dev'].get('status') == 'CANDIDATE' else
            'LEAD: did not pass the luck correction', fr['text']))
        L.append('     stop %g pts, target 25 pts, 30 min | DEV: n=%s '
                 'ses=%s hit=%s base=%s lift=%s t=%s q=%s exp=%s pts | '
                 'MNQ: %s'
                 % (fr['stop_ticks'] / POINT, fr['dev']['n'],
                    fr['dev']['sessions'], fr['dev']['hit'],
                    fr['dev']['baseline'], fr['dev']['lift'], fr['dev']['t'],
                    ('%.2g' % fr['dev']['q']) if fr['dev']['q'] is not None
                    else '-', fr['dev']['expectancy_points'],
                    fr.get('other_instruments_dev', {}).get('MNQ')))
        for p in fr['parts']:
            L.append('     %s %s %s: cut NQ=%s MNQ=%s'
                     % (p['feature'], p['tail'], p['level'],
                        p['cut'].get('NQ'), p['cut'].get('MNQ')))
    if not rep['nominated']:
        L.append('  nothing met the nomination bar; nothing goes to '
                 'validation from this search')
    an = rep.get('anatomy', {})
    if an.get('base'):
        L.append('')
        L.append('ANATOMY (descriptive): base rate of +25 pts before -10 '
                 'pts in 30 min: long %s short %s'
                 % (an['base']['long'], an['base']['short']))
        for f in FEATURES:
            x = an.get(f, {})
            if x.get('deciles'):
                lo, hi = x['deciles'][0], x['deciles'][-1]
                L.append('  %-10s bottom 10%% [%s..%s] long %s short %s | '
                         'top 10%% [%s..%s] long %s short %s'
                         % (f, lo['lo'], lo['hi'], lo['long'], lo['short'],
                            hi['lo'], hi['hi'], hi['long'], hi['short']))
    L.append('')
    L.append('Nothing here is a result. Nominated rules are hypotheses, '
             'judged once on the validation sessions. No order was placed.')
    return '\n'.join(L)


def text_evaluate(rep):
    L = ['%s  evaluate  unblind=%s  on %s'
         % (rep['wave4'], rep['unblind'], rep['evaluated_on']),
         'sessions evaluated: %s' % ', '.join(rep['sessions_evaluated']),
         'sessions refused: %s' % (', '.join(rep['sessions_refused'])
                                   or 'none')]
    for x in rep['rules']:
        s = x['result'].get(PRIMARY, {})
        L.append('  %-12s %s' % (x['verdict'], x['text']))
        L.append('     NQ n=%s ses=%s hit=%s base=%s lift=%s ci=%s p=%s '
                 'exp=%s pts (after costs %s)'
                 % (s.get('n'), s.get('sessions'), s.get('hit'),
                    s.get('baseline'), s.get('lift'), s.get('ci95'),
                    ('%.3g' % s['p']) if s.get('p') is not None else '-',
                    s.get('expectancy_points'),
                    s.get('expectancy_points_after_costs')))
    L.append('No order was placed. Expectancy is mid-to-mid.')
    return '\n'.join(L)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    d = argv[0]
    arg = lambda k: argv[argv.index(k) + 1] if k in argv else None  # noqa
    out = arg('--out')
    ms = int(arg('--max-sessions')) if arg('--max-sessions') else None
    unblind = '--unblind' in argv
    ev = arg('--evaluate')
    if unblind and not ev:
        print('REFUSED: --unblind is only for --evaluate at the checkpoint. '
              'The search reads DEV sessions only.')
        return 2
    try:
        if ev:
            frozen = json.load(open(ev))
            frozen = frozen.get('nominated', frozen) \
                if isinstance(frozen, dict) else frozen
            if unblind:
                print('*** UNBLIND: this read scores the nominated rules on '
                      'the validation sessions (> %s). Every session read '
                      'is labelled exposed, permanently. This is the '
                      'checkpoint read. ***\n' % DEV_END)
            rep, _r = run_evaluate(d, frozen, unblind=unblind,
                                   max_sessions=ms)
            print(text_evaluate(rep))
        else:
            rep, w3, nominated, _r = run_search(d, max_sessions=ms)
            print(text_search(rep))
            w3o = arg('--w3-out')
            if w3o:
                json.dump(w3, open(w3o, 'w'), indent=1, default=str)
                print('\nwave-three report (same read) -> %s' % w3o)
                print(BM.text_summary(w3))
            no = arg('--nominated-out')
            if no:
                json.dump(dict(wave4=W4_VERSION, registration=REGISTRATION,
                               nominated=nominated), open(no, 'w'),
                          indent=1, default=str)
                print('nominated rules -> %s (%d)' % (no, len(nominated)))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-four report -> %s' % out)
    if ev and unblind:
        led = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'MROF_EXPOSED_PILOT_DEV_DAYS.json')
        n = write_exposure_on_unblind(rep, led)
        print('exposure ledger -> %s (%d days)' % (led, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
