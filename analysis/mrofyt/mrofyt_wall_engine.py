#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01.1 — KEY-LEVEL WALL HOLD-VERSUS-FLUSH DECISION ENGINE
# Additive successor module. A state/forecast OVERLAY: armed states can
# never enter; confirmed states only authorize the matching frozen
# A1-A4/A6 rules at the first later executable quote. Probabilities are
# shadow-only. MBP wording enforced: REFILLING_LIQUIDITY_ESTIMATE only,
# never iceberg/participant/spoof labels.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
EPS = 1e-9
TICK = 0.25

STATES = ('NO_QUALIFYING_WALL', 'WALL_OBSERVED', 'HOLD_ARMED',
          'HOLD_CONFIRMED', 'FLUSH_ARMED_EXECUTION',
          'FLUSH_ARMED_WITHDRAWAL', 'FLUSH_CONFIRMED',
          'FAILED_FLUSH_RECLAIM', 'UNCERTAIN_NO_TRADE')

# which frozen family a state may authorize (entry authority stays with
# the A-family detectors; armed states authorize nothing)
AUTHORIZES = dict(HOLD_CONFIRMED='A1', FLUSH_ARMED_WITHDRAWAL='A3',
                  FLUSH_CONFIRMED='A2/A6', FAILED_FLUSH_RECLAIM='A4')
CAN_ENTER = ('HOLD_CONFIRMED', 'FLUSH_CONFIRMED', 'FAILED_FLUSH_RECLAIM')

RECON_TOLERANCE = 0.02       # frozen: |error| <= 2% of initial+added


# ---------------------------------------------------------------------
# wall selection (frozen per episode)
# ---------------------------------------------------------------------
def select_wall(levels, key_level_px, z_of_size):
    """levels: [(px, size)] on the BLOCKING side. Largest standardized
    display with z>=2.0 within 2 ticks of the key level; ties go to the
    price nearest the level. Returns (px, size, z) or None."""
    best = None
    for px, sz in levels:
        if abs(px - key_level_px) > 2 * TICK:
            continue
        z = z_of_size(sz)
        if z is None or z < 2.0:
            continue
        key = (sz, -abs(px - key_level_px))
        if best is None or key > best[0]:
            best = (key, (px, sz, z))
    return best[1] if best else None


# ---------------------------------------------------------------------
# episode accounting (feature 25/26)
# ---------------------------------------------------------------------
class WallEpisode:
    def __init__(self, wall_px, initial_display, wall_z, break_dir,
                 attempt=1):
        self.wall_px = wall_px
        self.initial = float(initial_display)
        self.wall_z = wall_z
        self.b = break_dir               # +1 up through resistance
        self.attempt = attempt
        self.added = 0.0
        self.executed = 0.0
        self.removed = 0.0               # non-trade removal (unmatched)
        self.remaining = float(initial_display)
        self.data_quality = 'OK'

    def on_add(self, q):
        self.added += q
        self.remaining += q

    def on_execute(self, q):
        self.executed += q
        self.remaining = max(self.remaining - q, 0.0)

    def on_nontrade_remove(self, q):
        self.removed += q
        self.remaining = max(self.remaining - q, 0.0)

    def reconciliation_error(self, observed_remaining):
        return observed_remaining - (self.initial + self.added -
                                     self.executed - self.removed)

    def reconcile(self, observed_remaining):
        err = self.reconciliation_error(observed_remaining)
        denom = self.initial + self.added + EPS
        if abs(err) > RECON_TOLERANCE * denom:
            self.data_quality = 'RECON_FAIL'
        return err

    # ---- clearance dynamics (feature 26) ----
    def v_exec(self, executed_w, added_w, w):
        return (executed_w - added_w) / w

    def v_all(self, executed_w, removed_w, added_w, w):
        return (executed_w + removed_w - added_w) / w

    def t_clear_exec(self, v_exec_w):
        """Right-censored when net execution clearance is nonpositive —
        never infinity, never a favorable value."""
        if v_exec_w <= 0:
            return dict(censored=True, seconds=None)
        return dict(censored=False, seconds=self.remaining / v_exec_w)

    def wall_burden_10(self, expected_break_dir_qty_10s):
        return self.remaining / (expected_break_dir_qty_10s + EPS)

    def display_label(self):
        """MBP honesty: repeated display after executions."""
        return 'REFILLING_LIQUIDITY_ESTIMATE'


# ---------------------------------------------------------------------
# causal state machine (frozen thresholds; pure function of measured
# causal features + current state)
# ---------------------------------------------------------------------
def wall_state(cur, f):
    """f keys (all causal, break-direction signed where applicable):
    data_ok, wall_z, aggr_z, progress_ticks, rr, opp_control_z,
    retreat_ticks, exec_vs_display, persist_agree, cleared_held_5s,
    crossed_1tick, tgt_drop_2s, opp_drop_2s, withdrawal_classifiable,
    post_clear_done, opp_replenish_z, reclaimed_5s."""
    if not f.get('data_ok', False):
        return 'UNCERTAIN_NO_TRADE'
    if f.get('wall_z') is None or f['wall_z'] < 2.0:
        # A4 stays possible without a wall, but THIS engine has no wall
        return 'NO_QUALIFYING_WALL'
    # reclaim beats continuation once observed
    if f.get('reclaimed_5s') and f.get('opp_control_z', 0) is not None \
            and (f.get('opp_control_z') or 0) >= 1.0:
        return 'FAILED_FLUSH_RECLAIM'
    # confirmed flush requires completed 5s acceptance
    if f.get('crossed_1tick') and f.get('cleared_held_5s') and \
            f.get('post_clear_done') and \
            (f.get('persist_agree') or 0) >= 3 and \
            (f.get('same_control_z') or 0) >= 1.0 and \
            (f.get('opp_replenish_z') or 0) < 1.5:
        return 'FLUSH_CONFIRMED'
    # hold confirmation (A1 map)
    if cur == 'HOLD_ARMED' and (f.get('opp_control_z') or 0) >= 1.0 and \
            (f.get('retreat_ticks') or 0) >= 1:
        return 'HOLD_CONFIRMED'
    # armed states
    if (f.get('aggr_z') or 0) >= 2.0 and \
            (f.get('progress_ticks') is not None and
             f['progress_ticks'] <= 1) and (f.get('rr') or 0) >= 1.5:
        return 'HOLD_ARMED'
    if (f.get('exec_vs_display') or 0) >= 1.5 and \
            (f.get('rr') is not None and f['rr'] < 0.25) and \
            (f.get('persist_agree') or 0) >= 3:
        return 'FLUSH_ARMED_EXECUTION'
    if f.get('withdrawal_classifiable') and \
            (f.get('tgt_drop_2s') or 0) >= 0.60 and \
            (f.get('opp_drop_2s') if f.get('opp_drop_2s') is not None
             else 1.0) <= 0.20:
        return 'FLUSH_ARMED_WITHDRAWAL'
    return 'WALL_OBSERVED'


def can_enter(state):
    return state in CAN_ENTER


# ---------------------------------------------------------------------
# quote migration / chase score (feature 28) — exact mirror symmetry
# ---------------------------------------------------------------------
def classify_step(prev_q, cur_q, buyer_exec_at_old_ask,
                  seller_exec_at_old_bid):
    """prev_q/cur_q: (bid, ask). Handles one-tick spreads explicitly."""
    pb, pa = prev_q
    cb, ca = cur_q
    if ca > pa and cb > pb and buyer_exec_at_old_ask:
        return 'BUYER_LED_UP'
    if cb < pb and ca < pa and seller_exec_at_old_bid:
        return 'SELLER_LED_DOWN'
    if cb > pb and ca >= pa and not buyer_exec_at_old_ask:
        return 'BID_CHASE_UP'
    if ca < pa and cb <= pb and not seller_exec_at_old_bid:
        return 'ASK_CONCEDE_DOWN'
    return 'UNCLASSIFIED'


def quote_migration_score(steps):
    """steps: list of classify_step outputs. Signed, normalized; exact
    long/short mirror by construction."""
    up = steps.count('BUYER_LED_UP') + steps.count('BID_CHASE_UP')
    dn = steps.count('SELLER_LED_DOWN') + steps.count('ASK_CONCEDE_DOWN')
    n = up + dn
    return (up - dn) / n if n else 0.0


# ---------------------------------------------------------------------
# large-print polarity + equal-size clustering (feature 29)
# ---------------------------------------------------------------------
def adverse_large_print_share(trades, position_dir, z_of_size):
    """trades: [(t, px, sz, sign)]. Large = causal size z>=2.0 only."""
    num = den = 0.0
    n = 0
    for _, _, sz, s in trades:
        z = z_of_size(sz)
        if z is None or z < 2.0:
            continue
        num += -position_dir * s * sz
        den += sz
        n += 1
    return dict(share=num / (den + EPS), count=n)


def equal_size_cluster(trades):
    """Participant-NEUTRAL diagnostic: recurrence of identical sizes.
    Output never contains participant/iceberg/spoof language."""
    from collections import Counter
    sizes = Counter(sz for _, _, sz, _ in trades)
    top = sizes.most_common(1)
    if not top or top[0][1] < 3:
        return dict(cluster=False)
    sz, cnt = top[0]
    sides = [s for _, _, q, s in trades if q == sz]
    return dict(cluster=True, size=sz, count=cnt,
                side_consistency=abs(sum(sides)) / max(len(sides), 1),
                label='EQUAL_SIZE_PRINT_CLUSTER')


# ---------------------------------------------------------------------
# post-clear flow reserve (feature 27)
# ---------------------------------------------------------------------
def post_clear_reserve(clear_t, now_t, comps):
    """Equal-weight signed composite; unavailable until the 5s window
    completes. comps: dict of standardized break-direction components
    (delta_z, ofi_z, migration, opp_replenish_z NEGATED by caller,
    retained_depth_z, acceptance_ticks_z)."""
    if now_t < clear_t + 5.0:
        return dict(available=False, value=None)
    vals = list(comps.values())
    if not vals or any(v is None for v in vals):
        return dict(available=True, value=None)
    return dict(available=True, value=sum(vals) / len(vals))


# ---------------------------------------------------------------------
# probability snapshots (shadow-only; causality-guarded)
# ---------------------------------------------------------------------
def snapshot(kind, snap_t, features):
    """kind: PRECONTACT|CONTACT. Every feature is (value, feature_t);
    any feature timestamped after snap_t is a causality violation."""
    assert kind in ('PRECONTACT', 'CONTACT')
    clean = {}
    for k, (v, ft) in features.items():
        if ft > snap_t:
            raise ValueError('lookahead: feature %s at %.3f after '
                             'snapshot %.3f' % (k, ft, snap_t))
        clean[k] = v
    return dict(kind=kind, t=snap_t, features=clean)


def empirical_rates(outcomes):
    """Session-blocked empirical baseline. outcomes: list of labels in
    {FLUSH, HOLD_OR_RECLAIM, UNRESOLVED} from TRAINING data only.
    Probabilities sum to one."""
    n = len(outcomes)
    if n == 0:
        return None
    pf = outcomes.count('FLUSH') / n
    ph = outcomes.count('HOLD_OR_RECLAIM') / n
    return dict(P_FLUSH=pf, P_HOLD_OR_RECLAIM=ph,
                P_UNRESOLVED=1.0 - pf - ph)


def shadow_record(**kw):
    cols = ('LEVEL_ID', 'WALL_SIDE', 'WALL_Z', 'EXECUTED', 'ADDED',
            'NONTRADE_REMOVED', 'REMAINING', 'V_EXEC', 'T_CLEAR_EXEC',
            'WALL_BURDEN', 'ATTEMPT', 'QUOTE_MIGRATION',
            'POST_CLEAR_RESERVE', 'P_FLUSH_5/10/30', 'P_HOLD_5/10/30',
            'STATE', 'DATA_QUALITY', 'REASON')
    return ' | '.join(str(kw.get(c, '-')) for c in cols)
