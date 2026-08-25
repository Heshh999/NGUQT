#!/usr/bin/env python3
# ======================================================================
# XMARKET-V1  shared library - synchronized NQ/ES universe + frozen
# constructs. Implements docs/XMARKET_V1_PREREGISTRATION.md verbatim.
# ======================================================================
# Pre-registration frozen at commit 36aaa28, sha256
#   314262cbfe3782f07ac81c795f01dc553382fa5d11ef1f6cf14cfd3bebb8c786
# BEFORE a single ES bar had ever been observed by this project.
#
# Nothing here defines a NEW NQ construct. The NQ balance, the two-close
# acceptance and the measurement frame are reused verbatim from the
# frozen sources named in the pre-registration.
#
# THIS MODULE SUBMITS NO ORDERS.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, math, random, statistics, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('../rvmr', '.'):
    sys.path.insert(0, os.path.join(HERE, p))
import rvmr_spec as RS
import rvmr_run as RV
import es_nq_data_spec as SY

ES_DIR = '/home/user/NGUQT/scratchpad/es_bar1m'

# ---- frozen measurement frame (identical across every arm, per the
# ---- pre-registration: "1.5 x ATR_NQ stop, no target, 60-min time
# ---- exit, 0.87 pt cost, identical across all arms so it cannot
# ---- create an interaction")
COST = 0.87
STOP_ATR = 1.5
HORIZON = 60
COOL = 30
SEED = 20260825

# ---- frozen normalization (pre-registration section 6)
W_PRIMARY = 5              # Z_X(t,w), PRIMARY w = 5 minutes
W_CATCHUP = 3              # Z_lag(t+k,3) in the catch-up rule
CATCHUP_BARS = 3           # PRIMARY window t+1..t+3
CATCHUP_SECONDARY = (1, 5)  # declared secondary, reported never promoted

# ---- frozen classification thresholds (pre-registration section 7)
CONF_Z = 0.5               # |Z_ES| >= 0.5 to be CONFIRMING / OPPOSING
LEAD_HI = 1.0              # leader needs |Z| >= 1.0
LEAD_LO = 0.5              # laggard needs |Z| <= 0.5
CATCH_Z = 0.5              # catch-up needs |Z_lag(t+k,3)| >= 0.5
BAL_N = 30                 # 30-bar balance envelope, both markets


# ====================================================================
# IMPLEMENTATION CHOICES DECLARED BEFORE ANY RESULT WAS SEEN
# ====================================================================
# The frozen pre-registration names these constructs but does not give
# them numeric form. They are supplied here, fixed before the first run,
# and recorded openly as MINE rather than smuggled in as if frozen.
# They are never tuned; a failure under them is a failure.
#
# 1. ENTRY TIMING FOR CATCH-UP / REFUSAL ARMS (H3, H4, H6).
#    Catch-up is decided over t+1..t+3, so the earliest fully causal
#    decision point is t+3. EVERY arm of those hypotheses - including
#    the no-ES-condition control - is entered at t+3, so the comparison
#    can never be a timing artifact.
#
# 2. NQ PATH EFFICIENCY (H4 split A/B/C).
#    eff(t) = |c(t) - c(t-5)| / sum_{i=t-4..t} |c(i) - c(i-1)|
#    (A) EFFICIENT    eff(t+3) >= eff(t)
#    (B) DETERIORATES eff(t+3) <  eff(t)
#    (C) LOST_ACCEPT  NQ closes back inside its 30-bar balance in t+1..t+3
#    C is tested first and wins ties; primary arm is refusal + (B or C).
#
# 3. H5 RESOLUTION, first of these within 30 bars:
#    CONVERGED |RS(t+k)| <= 0.5 |RS(t)| ; WIDENED |RS(t+k)| >= 1.5 |RS(t)|
#    else UNRESOLVED. Attribution of a convergence goes to whichever
#    market moved further in its OWN ATR units over t -> t+k.
#
# 4. H8 "BEYOND BALANCE" is ONE close beyond the envelope edge, which is
#    what distinguishes H8 from H7's two-close ACCEPTANCE.
# ====================================================================
EFF_W = 5
H5_CONVERGE = 0.5
H5_WIDEN = 1.5
H5_WINDOW = 30
H8_WINDOW = 10


def med(x):
    return statistics.median(x) if x else float('nan')


def mean(x):
    return sum(x) / len(x) if x else float('nan')


def pctl(x, q):
    if not x:
        return float('nan')
    s = sorted(x)
    return s[min(len(s) - 1, int(q * len(s)))]


# ======================================================== universe
class Universe(object):
    """Synchronized NQ<->ES 1-minute universe.

    NQ is the spine: every array is indexed by NQ bar index. ES fields
    are None wherever no ES bar exists on that exact close-stamped ET
    minute. NOTHING is forward-filled or interpolated - an absent ES bar
    simply makes that minute unusable as a decision bar.
    """

    def __init__(self, es_dir=ES_DIR, verbose=True):
        RV.STAMP_SHIFT = 0
        D = RV.load_bars()
        self.D = D
        self.N = N = len(D['c'])
        es, rep = SY.load_market(es_dir, 'ES')
        self.es_rep = rep
        if verbose:
            print('NQ bars %d   ES bars %d' % (N, len(es)))

        # ---- ES on its own timeline: ATR20 and index map (frozen atr20)
        ets = sorted(es)
        eb = [(e,) + es[e] for e in ets]
        eatr = RS.atr20(eb)
        eidx = {e: i for i, e in enumerate(ets)}
        self.es_ets, self.es = ets, es

        # ---- project onto the NQ spine
        self.eo = [None] * N; self.eh = [None] * N
        self.el = [None] * N; self.ec = [None] * N
        self.ev = [None] * N; self.ea = [None] * N
        self.ei = [None] * N          # index into the ES timeline
        matched = 0
        for j in range(N):
            e = D['et'][j]
            b = es.get(e)
            if b is None:
                continue
            matched += 1
            self.eo[j], self.eh[j], self.el[j] = b[0], b[1], b[2]
            self.ec[j], self.ev[j] = b[3], b[4]
            self.ea[j] = eatr[eidx[e]]
            self.ei[j] = eidx[e]
        self.matched_raw = matched

        # ---- NQ ATR20 (frozen definition)
        bars = list(zip(D['et'], D['o'], D['h'], D['l'], D['c'], D['v']))
        self.na = RS.atr20(bars)

        # ---- RVMR state: DIAGNOSTIC ONLY (pre-registration is explicit)
        rng = [D['h'][i] - D['l'][i] for i in range(N)]
        self.RB = [RS.bucket(x) if x is not None else None
                   for x in RS.trailing_ratio(rng)]
        self.VB = [RS.bucket(x) if x is not None else None
                   for x in RS.trailing_ratio(D['v'])]

        # ---- roll quarantine (the SHARED precautionary calendar)
        self.rolls = SY.roll_days()

        # ---- normalized momentum, both markets, causal
        self.zn5 = self._z_nq(W_PRIMARY)
        self.zn3 = self._z_nq(W_CATCHUP)
        self.ze5 = self._z_es(W_PRIMARY)
        self.ze3 = self._z_es(W_CATCHUP)

        # ---- REL_STRENGTH(t) = Z_NQ(t,5) - Z_ES(t,5)
        self.rs = [None] * N
        for j in range(N):
            if self.zn5[j] is not None and self.ze5[j] is not None:
                self.rs[j] = self.zn5[j] - self.ze5[j]

        # ---- causal path efficiency on NQ
        self.eff = [None] * N
        for j in range(EFF_W, N):
            if D['em'][j] - D['em'][j - EFF_W] != EFF_W:
                continue
            den = sum(abs(D['c'][i] - D['c'][i - 1])
                      for i in range(j - EFF_W + 1, j + 1))
            self.eff[j] = (abs(D['c'][j] - D['c'][j - EFF_W]) / den) if den > 0 else None

        if verbose:
            usable = sum(1 for j in range(N) if self.usable(j))
            print('matched on NQ spine %d   usable decision bars %d'
                  % (matched, usable))

    # ---------------------------------------------------------- helpers
    def _z_nq(self, w):
        D, N, out = self.D, self.N, [None] * self.N
        for j in range(w, N):
            if D['em'][j] - D['em'][j - w] != w:
                continue
            a = self.na[j]
            if not a or a <= 0:
                continue
            out[j] = (D['c'][j] - D['c'][j - w]) / a
        return out

    def _z_es(self, w):
        """ES momentum measured on the ES timeline, then read at the NQ
        bar. Requires w genuinely consecutive ES minutes - an ES gap
        makes Z_ES undefined rather than bridged."""
        ets, es, out = self.es_ets, self.es, [None] * self.N
        for j in range(self.N):
            i = self.ei[j]
            if i is None or i < w:
                continue
            a = self.ea[j]
            if not a or a <= 0:
                continue
            p = ets[i - w]
            d = (datetime.datetime.strptime(ets[i], '%Y-%m-%d %H:%M:%S')
                 - datetime.datetime.strptime(p, '%Y-%m-%d %H:%M:%S'))
            if d.total_seconds() != 60 * w:
                continue
            out[j] = (es[ets[i]][3] - es[p][3]) / a
        return out

    def matched(self, j):
        """MATCHED per the frozen synchronization table: both markets
        present on the same close-stamped minute, outside the roll
        quarantine."""
        return self.ec[j] is not None and self.D['day'][j] not in self.rolls

    def usable(self, j):
        """A legal DECISION bar: matched, RTH with a full 60-minute
        forward horizon inside the session, valid NQ ATR, and 60 truly
        consecutive forward NQ minutes to measure on."""
        D = self.D
        if not (RS.RTH_START <= D['mod'][j] <= RS.RTH_END - HORIZON):
            return False
        if not self.matched(j):
            return False
        a = self.na[j]
        if not a or a <= 0:
            return False
        if j + HORIZON >= self.N:
            return False
        return D['em'][j + HORIZON] - D['em'][j] == HORIZON

    # ------------------------------------------------- frozen constructs
    def nq_balance(self, j, n=BAL_N):
        """Causal n-bar high/low envelope ending at bar j (mag_lib.balance
        geometry; tb_run.balance form)."""
        D = self.D
        if j < n or D['em'][j] - D['em'][j - n + 1] != n - 1:
            return None
        return (max(D['h'][j - n + 1:j + 1]), min(D['l'][j - n + 1:j + 1]))

    def es_balance(self, j, n=BAL_N):
        """The IDENTICAL construction on ES, built on the ES timeline so
        an ES data gap voids it instead of silently shortening it."""
        i = self.ei[j]
        if i is None or i < n:
            return None
        ets, es = self.es_ets, self.es
        a = datetime.datetime.strptime(ets[i], '%Y-%m-%d %H:%M:%S')
        b = datetime.datetime.strptime(ets[i - n + 1], '%Y-%m-%d %H:%M:%S')
        if (a - b).total_seconds() != 60 * (n - 1):
            return None
        win = [es[e] for e in ets[i - n + 1:i + 1]]
        return (max(x[1] for x in win), min(x[2] for x in win))

    def es_state(self, j, d):
        """CONFIRMING / OPPOSING / NEUTRAL, frozen section 7."""
        z = self.ze5[j]
        if z is None:
            return None
        if z * d > 0 and abs(z) >= CONF_Z:
            return 'CONFIRMING'
        if z * d < 0 and abs(z) >= CONF_Z:
            return 'OPPOSING'
        return 'NEUTRAL'

    def leadership(self, j):
        zn, ze = self.zn5[j], self.ze5[j]
        if zn is None or ze is None:
            return None
        if abs(zn) >= LEAD_HI and abs(ze) <= LEAD_LO:
            return 'NQ-LEADS'
        if abs(ze) >= LEAD_HI and abs(zn) <= LEAD_LO:
            return 'ES-LEADS'
        return None

    def catchup(self, j, d, lag, bars=CATCHUP_BARS):
        """Frozen: catch-up if for some k <= bars, sign(Z_lag(t+k,3)) == d
        and |Z_lag(t+k,3)| >= 0.5. REFUSAL = no catch-up in the window."""
        z = self.ze3 if lag == 'ES' else self.zn3
        for k in range(1, bars + 1):
            if j + k >= self.N:
                return None
            if self.D['em'][j + k] - self.D['em'][j] != k:
                return None
            v = z[j + k]
            if v is None:
                continue
            if v * d > 0 and abs(v) >= CATCH_Z:
                return k
        return 0        # 0 == refusal (distinct from None == undefined)

    # ------------------------------------------------ measurement frame
    def frame(self, j, d):
        """THE uniform frozen frame: 1.5 ATR_NQ stop, no target, 60-min
        time exit, 0.87 pt cost. Favourable-first is evaluated on the
        full pre-registered ladder and AMBIGUOUS is NEVER guessed."""
        D = self.D
        px = D['c'][j]; a = self.na[j]
        risk = STOP_ATR * a
        stop = px - risk * d
        mfe = mae = 0.0
        net = None; reason = 'TIME'; t_stop = None
        ladder = ((0.25, 0.25), (0.5, 0.5), (1.0, 1.0),
                  (1.5, 1.0), (2.0, 1.0))
        ff = dict((k, None) for k in ladder)
        fwd = {}
        for k in range(1, HORIZON + 1):
            hi_, lo_ = D['h'][j + k], D['l'][j + k]
            u = (hi_ - px) * d; w = (px - lo_) * d
            if u > mfe: mfe = u
            if w > mae: mae = w
            for key in ladder:
                if ff[key] is not None:
                    continue
                up, dn = key
                hu, hd = mfe >= up * a, mae >= dn * a
                if hu and hd:
                    ff[key] = 'AMBIGUOUS'
                elif hu:
                    ff[key] = 'FAV'
                elif hd:
                    ff[key] = 'ADV'
            if net is None and ((lo_ <= stop) if d > 0 else (hi_ >= stop)):
                net = (stop - px) * d - COST; reason = 'STOP'; t_stop = k
            if k in (5, 10, 15, 30, 60):
                fwd[k] = (D['c'][j + k] - px) * d
        if net is None:
            net = (D['c'][j + HORIZON] - px) * d - COST
        return {'net': net, 'R': net / risk if risk else float('nan'),
                'mfe': mfe, 'mae': mae, 'atr': a, 'reason': reason,
                't_stop': t_stop, 'fwd': fwd,
                'ff': dict((('%g/%g' % k), (v or 'NEITHER'))
                           for k, v in ff.items()),
                'day': D['day'][j], 'et': D['et'][j],
                'year': D['day'][j][:4], 'd': d, 'j': j,
                'mod': D['mod'][j],
                'rvmrR': self.RB[j], 'rvmrV': self.VB[j],
                'zn5': self.zn5[j], 'ze5': self.ze5[j], 'rs': self.rs[j],
                'nqvol': D['v'][j],
                'nqrng': D['h'][j] - D['l'][j]}


def cool(u, evs, gap=COOL):
    """Frozen cooldown: no two parents within `gap` minutes."""
    out, last = [], -10 ** 9
    for e in sorted(evs, key=lambda x: x[0]):
        if u.D['em'][e[0]] - last < gap:
            continue
        last = u.D['em'][e[0]]
        out.append(e)
    return out


# ======================================================== statistics
def signflip_p(rows, key='net', iters=20000, seed=SEED):
    """Day-level sign-flip permutation p (frozen form)."""
    if not rows:
        return float('nan')
    rnd = random.Random(seed)
    byday = collections.defaultdict(list)
    for r in rows:
        byday[r['day']].append(r[key])
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


def day_ci(rows, key='net', iters=10000, seed=SEED):
    if not rows:
        return (float('nan'), float('nan'))
    rnd = random.Random(seed)
    byday = collections.defaultdict(list)
    for r in rows:
        byday[r['day']].append(r[key])
    days = sorted(byday)
    ms = []
    for _ in range(iters):
        vals = []
        for _ in days:
            vals.extend(byday[days[rnd.randrange(len(days))]])
        ms.append(sum(vals) / len(vals))
    ms.sort()
    return ms[int(.025 * len(ms))], ms[int(.975 * len(ms))]


def day_boot_delta(rowsA, rowsB, key='net', iters=20000, seed=SEED):
    """Day-clustered bootstrap of mean(A) - mean(B), with a two-sided p."""
    if len(rowsA) < 10 or len(rowsB) < 10:
        return float('nan'), (float('nan'), float('nan')), float('nan')
    rnd = random.Random(seed)
    ba = collections.defaultdict(list); bb = collections.defaultdict(list)
    for r in rowsA: ba[r['day']].append(r[key])
    for r in rowsB: bb[r['day']].append(r[key])
    days = sorted(set(ba) | set(bb))
    ds = []
    for _ in range(iters):
        A, B = [], []
        for _ in days:
            d = days[rnd.randrange(len(days))]
            A.extend(ba.get(d, ())); B.extend(bb.get(d, ()))
        if A and B:
            ds.append(sum(A) / len(A) - sum(B) / len(B))
    if not ds:
        return float('nan'), (float('nan'), float('nan')), float('nan')
    ds.sort()
    obs = mean([r[key] for r in rowsA]) - mean([r[key] for r in rowsB])
    neg = sum(1 for x in ds if x <= 0) / float(len(ds))
    p = min(1.0, 2 * min(neg, 1 - neg) + 1.0 / (iters + 1))
    return obs, (ds[int(.025 * len(ds))], ds[int(.975 * len(ds))]), p


def bh_adjust(ps):
    ok = [p if p == p else 1.0 for p in ps]
    idx = sorted(range(len(ok)), key=lambda i: ok[i])
    m = len(ok); q = [None] * m; prev = 1.0
    for rank, i in enumerate(reversed(idx), 1):
        v = min(prev, ok[i] * m / (m - rank + 1))
        q[i] = v; prev = v
    return q


def holm_adjust(ps):
    ok = [p if p == p else 1.0 for p in ps]
    idx = sorted(range(len(ok)), key=lambda i: ok[i])
    m = len(ok); out = [None] * m; prev = 0.0
    for rank, i in enumerate(idx):
        v = max(prev, min(1.0, ok[i] * (m - rank)))
        out[i] = v; prev = v
    return out


def ff_table(rows):
    """Favourable-first over the full pre-registered ladder. AMBIGUOUS is
    reported as its own class and never resolved by guessing."""
    keys = ['0.25/0.25', '0.5/0.5', '1/1', '1.5/1', '2/1']
    out = {}
    for k in keys:
        c = collections.Counter(r['ff'].get(k, 'NEITHER') for r in rows)
        n = sum(c.values())
        dec = c['FAV'] + c['ADV']
        out[k] = {'FAV': c['FAV'], 'ADV': c['ADV'],
                  'AMBIGUOUS': c['AMBIGUOUS'], 'NEITHER': c['NEITHER'],
                  'pct_fav_of_decided': (100.0 * c['FAV'] / dec) if dec else float('nan'),
                  'n': n}
    return out


def geometry(rows):
    if not rows:
        return None
    nets = [r['net'] for r in rows]
    mfes = [r['mfe'] for r in rows]
    maes = [r['mae'] for r in rows]
    g = {'n': len(rows), 'mean': mean(nets), 'median': med(nets),
         'mfe_med': med(mfes), 'mae_med': med(maes),
         'mfe_mean': mean(mfes), 'mae_mean': mean(maes),
         'mfe_mae': (med(mfes) / med(maes)) if med(maes) else float('nan'),
         'win%': 100.0 * sum(1 for x in nets if x > 0) / len(nets),
         'stop%': 100.0 * sum(1 for r in rows if r['reason'] == 'STOP') / len(rows),
         'absmove': mean([abs(r['fwd'].get(60, 0.0)) for r in rows])}
    for k in (5, 10, 15, 30, 60):
        vals = [r['fwd'][k] for r in rows if k in r['fwd']]
        g['fwd%d' % k] = mean(vals)
        g['fwd%dmed' % k] = med(vals)
    return g


def tails(rows):
    if not rows:
        return None
    nets = sorted((r['net'] for r in rows), reverse=True)
    n = len(nets)
    k1 = max(1, int(0.01 * n)); k5 = max(1, int(0.05 * n))
    return {'max': nets[0], 'min': nets[-1],
            'top1%_share': (sum(nets[:k1]) / sum(nets)) if sum(nets) else float('nan'),
            'mean_ex_top1': mean(nets[k1:]),
            'mean_ex_top5': mean(nets[k5:]),
            'mean': mean(nets)}
