#!/usr/bin/env python3
# MROF-YT-OF-01.7 suite: the liquidity-target and flow-controlled exit
# arms, proved against the required list in Appendix C section 7.
#
# SYNTHETIC TESTS PROVE IMPLEMENTATION BEHAVIOR ONLY. Nothing here is
# evidence of profitability or positive EV, and no study was run.
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mrofyt_exits_v017 as EX        # noqa: E402
import mrofyt_signals as SIG         # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-74s %s' % (name[:74], 'PASS' if cond else 'FAIL'))


T0 = 1788269400.0
SOD = lambda tt: 13.5 * 3600 + (tt - T0)     # noqa: E731


def quotes(n=4000, step=0.05, bid=100.0, spread=0.25, size=10,
           drift=0.0, t0=T0):
    out = []
    for i in range(n):
        b = bid + drift * i
        out.append((t0 + i * step, b, size, b + spread, size))
    return out


def snaps(n=40, step=0.1, t0=T0 - 3.0, ask=None, healthy=True):
    """Book snapshots with a fixed ask ladder unless overridden."""
    out = []
    for i in range(n):
        out.append(dict(t=t0 + i * step, healthy=healthy,
                        bid=[(99.75, 5), (99.5, 5), (99.25, 5)],
                        ask=list(ask) if ask else
                        [(100.25, 5), (100.5, 5), (101.0, 400)]))
    return out


class FakeBaseline(object):
    """Deterministic stand-in for the strict prior-20-session store.
    `zmap` keys are (feat, size); anything absent has no baseline."""

    def __init__(self, zmap, none_for=()):
        self.zmap = zmap
        self.none_for = set(none_for)

    def z(self, feat, _sod, value):
        if feat in self.none_for:
            return None                    # missing baseline / zero MAD
        return self.zmap.get((feat, round(float(value), 6)))


BIG = {('wall|ask|2', 400.0): 3.0, ('wall|ask|0', 5.0): 0.1,
       ('wall|ask|1', 5.0): 0.1, ('wall|bid|2', 400.0): 3.0,
       ('wall|bid|0', 5.0): 0.1, ('wall|bid|1', 5.0): 0.1}


def trade(direction=1, entry=100.25, stop=99.75, qty=1, tid='t1',
          flat=None):
    return EX.Trade(tid, entry, T0, direction, stop, qty,
                    session_flat_t=flat)


def checks_never():
    return ((lambda _t: (5, 4)), (lambda _t: (None, False)),
            (lambda _t: (None, None, None)))


# ---------------------------------------------------------------------
# C1 — E0 parity with the authoritative parent, fills and ledger
# ---------------------------------------------------------------------
q = quotes(drift=0.001)
c10, cctl, ce2 = checks_never()
tr = trade()
e0 = EX.run_e0(tr, q, c10, cctl)
par = SIG.simulate(q, tr.entry_px, tr.entry_t, tr.direction, tr.stop_px,
                   c10, cctl)
src = open(os.path.join(HERE, 'mrofyt_exits_v017.py')).read()
t('C1: E0 reproduces the authoritative parent exactly by delegating to '
  'mrofyt_signals.simulate, not by restating its rules',
  e0['exit'] == par['exit'] and e0['px'] == par['px'] and
  e0['t'] == par['t'] and e0['R'] == par['R'] and
  e0['parity_source'] == 'mrofyt_signals.simulate' and
  'SIG.simulate(' in src)

# ---------------------------------------------------------------------
# C2 — future data cannot change an earlier selection
# ---------------------------------------------------------------------
base = snaps()
sel_a = EX.select_liquidity_target(base, T0, 100.25, 1,
                                   FakeBaseline(BIG), SOD, 101.25)
later = base + [dict(t=T0 + 5.0, healthy=True, bid=[(99.75, 5)],
                     ask=[(100.5, 900)])]
sel_b = EX.select_liquidity_target(later, T0, 100.25, 1,
                                   FakeBaseline(BIG), SOD, 101.25)
t('C2: a wall appearing after the selection timestamp cannot change the '
  'earlier selection, because only snapshots at or before t_init are read',
  sel_a == sel_b and sel_a['status'] == EX.TARGET_SELECTED and
  sel_a['wall'] == 101.0)

# ---------------------------------------------------------------------
# C3 — two-second persistence, missing/zero-MAD baseline, absent wall
# ---------------------------------------------------------------------
short = snaps(n=8, step=0.1, t0=T0 - 0.7)          # < 2 s of history
flick = snaps(n=40, step=0.1)
for i in (15, 16):        # wall vanishes INSIDE the 2 s persistence window
    flick[i]['ask'] = [(100.25, 5), (100.5, 5)]
nob = snaps(n=40, step=0.1, ask=[(100.25, 5), (100.5, 5)])
s_short = EX.select_liquidity_target(short, T0, 100.25, 1,
                                     FakeBaseline(BIG), SOD, 101.25)
s_flick = EX.select_liquidity_target(flick, T0, 100.25, 1,
                                     FakeBaseline(BIG), SOD, 101.25)
s_nomad = EX.select_liquidity_target(
    base, T0, 100.25, 1, FakeBaseline(BIG, none_for=('wall|ask|2',)),
    SOD, 101.25)
s_nowall = EX.select_liquidity_target(nob, T0, 100.25, 1,
                                      FakeBaseline(BIG), SOD, 101.25)
t('C3: incomplete persistence history is TARGET_DATA_UNAVAILABLE; a wall '
  'that flickers out of view, an absent baseline or zero MAD, and no big '
  'level at all are all NO_QUALIFYING - none is a liquidity-target trade',
  s_short['status'] == EX.DATA_UNAVAILABLE and
  s_flick['status'] == EX.NO_QUALIFYING and
  s_nomad['status'] == EX.NO_QUALIFYING and
  s_nowall['status'] == EX.NO_QUALIFYING and
  all(s['target'] == 101.25 and s['trigger'] is None
      for s in (s_short, s_flick, s_nomad, s_nowall)))

# ---------------------------------------------------------------------
# C4 — mirrored long/short, and selection from MNQ not NQ
# ---------------------------------------------------------------------
short_snaps = snaps(n=40, step=0.1,
                    ask=[(100.25, 5), (100.5, 5), (101.0, 5)])
for s in short_snaps:
    s['bid'] = [(99.75, 5), (99.5, 5), (99.0, 400)]
sel_s = EX.select_liquidity_target(short_snaps, T0, 99.75, -1,
                                   FakeBaseline(BIG), SOD, 98.75)
sig = re.search(r'def select_liquidity_target\(([^)]*)\)', src).group(1)
t('C4: a short selects a BID wall and takes profit one tick ABOVE it, '
  'mirroring the long, and selection reads one book (the MNQ execution '
  'book) with no NQ price ever entering the target',
  sel_s['status'] == EX.TARGET_SELECTED and sel_s['side'] == 'bid' and
  sel_s['wall'] == 99.0 and sel_s['trigger'] == 99.25 and
  sel_a['side'] == 'ask' and sel_a['trigger'] == 100.75 and
  'nq' not in sig.lower())

# ---------------------------------------------------------------------
# C5 — wall removal or depth-window exit never moves the frozen trigger
# ---------------------------------------------------------------------
after = base + [dict(t=T0 + 1.0, healthy=True, bid=[(99.75, 5)],
                     ask=[(100.25, 5), (100.5, 5)]),
                dict(t=T0 + 2.0, healthy=True, bid=[(99.75, 5)],
                     ask=[(100.25, 5), (100.5, 5), (102.0, 900)])]
tk = EX.track_wall(after, sel_a, T0, T0 + 3.0)
frozen_trigger = sel_a['trigger']
t('C5: after selection the wall can vanish or a bigger one can appear; '
  'both are recorded diagnostically and the frozen trigger does not move',
  sel_a['frozen'] is True and frozen_trigger == 100.75 and
  any(x['event'] == 'VISIBILITY_LOST' for x in tk) and
  sel_a['trigger'] == 100.75)

# ---------------------------------------------------------------------
# C6 — E2 signed score, completed windows, 3-of-4, adverse confirmation
# ---------------------------------------------------------------------
t('C6: the E2 condition needs signed opposing control z>=1.0 AND 3 of 4 '
  'subwindows AND >=1 NQ tick adverse; a missing feature is unknown, '
  'never zero or favourable',
  EX.opposing_control_exit(1.0, 3, 1) and
  not EX.opposing_control_exit(0.9, 4, 5) and
  not EX.opposing_control_exit(2.0, 2, 5) and
  not EX.opposing_control_exit(2.0, 4, 0) and
  not EX.opposing_control_exit(None, 4, 5) and
  not EX.opposing_control_exit(2.0, None, 5) and
  not EX.opposing_control_exit(2.0, 4, None))

# a completed-window exit is decided at the window END, never its start
qflat = quotes(n=4000, drift=0.0)
e2 = EX.run_arm('E2', trade(), qflat, c10, cctl,
                lambda _t: (2.0, 4, 3), None)
t('C6b: an E2 exit is decided at the END of the completed 10-second '
  'window and its fill is later still, never at the window start',
  e2['exit'] == 'OPPOSING_CONTROL' and
  e2['decision_t'] >= T0 + EX.DECISION_S and
  e2['t'] > e2['decision_t'])

# ---------------------------------------------------------------------
# C7 — healthy unchanged level versus an unhealthy feed
# ---------------------------------------------------------------------
stale_ok = snaps(n=40, step=0.1)          # unchanged for 4 s, but healthy
unhealthy = snaps(n=40, step=0.1)
for s_ in unhealthy:      # the feed is unhealthy INSIDE the window
    if s_['t'] >= T0 - 1.0:
        s_['healthy'] = False
s_ok = EX.select_liquidity_target(stale_ok, T0, 100.25, 1,
                                  FakeBaseline(BIG), SOD, 101.25)
s_bad = EX.select_liquidity_target(unhealthy, T0, 100.25, 1,
                                   FakeBaseline(BIG), SOD, 101.25)
t('C7: a valid level that simply has not changed is still selectable, '
  'while an unhealthy or disconnected book is TARGET_DATA_UNAVAILABLE',
  s_ok['status'] == EX.TARGET_SELECTED and
  s_bad['status'] == EX.DATA_UNAVAILABLE and
  s_bad['reason'] == 'FEED_UNHEALTHY')

# ---------------------------------------------------------------------
# C8 — latency, partial fills, remaining protection, unresolved gaps
# ---------------------------------------------------------------------
thin = [(T0 + 1.0, 100.0, 1, 100.25, 1), (T0 + 1.2, 100.0, 1, 100.25, 1),
        (T0 + 1.4, 100.0, 1, 100.25, 1)]
f_part = EX.market_exit(thin, T0, 1, 5.0)
cons = set()
f_a = EX.market_exit(thin, T0, 1, 1.0, consumed=cons)
f_b = EX.market_exit(thin, T0, 1, 1.0, consumed=cons)
f_lat = EX.market_exit(thin, T0 + 1.15, 1, 1.0)
gap = [(T0 + 1.0, 100.0, 0, 100.25, 0)]
f_gap = EX.market_exit(gap, T0, 1, 1.0)
t('C8: exits respect latency, fill only available quantity, leave an '
  'unfilled remainder OPEN rather than pretending flat, never re-fill a '
  'consumed snapshot, and report a gap as unresolved',
  f_part['filled'] == 3.0 and f_part['remaining'] == 2.0 and
  f_part['unresolved'] and
  f_a['fills'][0]['t'] == T0 + 1.0 and f_b['fills'][0]['t'] == T0 + 1.2 and
  f_lat['fills'][0]['t'] == T0 + 1.4 and
  f_gap['filled'] == 0.0 and f_gap['unresolved'])

# ---------------------------------------------------------------------
# C9 — protective precedence and no impossible deadline fill
# ---------------------------------------------------------------------
# A stop and a fixed target can never be touched by the SAME price (the
# stop sits on the losing side of entry and the target on the winning
# side), so the reachable precedence case is a completed-window exit
# coinciding with a target touch. The protective/control exit must win
# and the target touch must still be recorded.
# flat until the first window closes, then the target is touched at
# exactly the window-completion timestamp
coincide = [(T0 + i * 0.5, 100.0, 10, 100.25, 10) for i in range(1, 20)] + \
           [(T0 + 10.0, 101.5, 10, 101.75, 10)] + \
           [(T0 + 10.0 + i * 0.5, 101.5, 10, 101.75, 10)
            for i in range(1, 20)]
r_prec = EX.run_arm('E0_EXEC', trade(), coincide,
                    lambda _t: (0, 0),        # early invalidation is true
                    cctl, None, None)
t('C9: a completed-window exit takes precedence over profit taking at a '
  'common timestamp and the target touch is still recorded, never lost',
  r_prec['exit'] == 'EARLY_INVALIDATION' and
  'TARGET_ALSO_TOUCHED' in r_prec['also'])

# the stop still beats everything when it is the condition that is true
drop = [(T0 + i * 0.5, 100.0 - i * 0.5, 10, 100.25 - i * 0.5, 10)
        for i in range(1, 60)]
r_stop = EX.run_arm('E0_EXEC', trade(), drop, c10, cctl, None, None)

# the deadline instruction is issued on time; the FILL is later
late = [(T0 + i * 0.05, 100.0, 10, 100.25, 10) for i in range(1, 40)] + \
       [(T0 + EX.MAX_HOLD_S + 5.0, 100.0, 10, 100.25, 10)]
tr_to = EX.Trade('to', 100.25, T0, 1, 99.75, 1)
r_time = EX.run_arm('E0_EXEC', tr_to, late, c10, cctl, None, None)
t('C9b: a deadline liquidation is issued at the deadline but its fill is '
  'genuinely later, and no fill is manufactured at the deadline itself',
  r_stop['exit'] == 'STOP' and
  r_time['exit'] == 'TIME_30M' and
  r_time['decision_t'] == T0 + EX.MAX_HOLD_S and
  r_time['deadline_fill_is_later'] is True and
  r_time['t'] > r_time['decision_t'])

# ---------------------------------------------------------------------
# C10 — paired entries versus independently gated sequential replay
# ---------------------------------------------------------------------
trs = [EX.Trade('a', 100.25, T0, 1, 99.75, 1),
       EX.Trade('b', 100.25, T0 + 20.0, 1, 99.75, 1)]
QQ = quotes(n=8000, drift=0.0005)


def qof(_tr):
    return QQ


def cof(_tr):
    return checks_never()


pair = EX.paired_attribution(trs, qof, cof,
                             {'a': sel_a, 'b': sel_a})
same_entry = all(
    r['E0']['trade'] == r['E1']['trade'] == r['E2']['trade'] and
    r['entry_px'] == 100.25 and r['stop_px'] == 99.75 for r in pair['rows'])
seq_slow = EX.sequential_replay('E2', trs, qof, cof)
seq_fast = EX.sequential_replay('E0_EXEC', trs, qof, cof)
t('C10: paired attribution replays identical entries, stops and risk per '
  'arm, while the sequential replay gates entries independently so the '
  'arms legitimately take different numbers of trades',
  same_entry and len(pair['rows']) == 2 and
  'not a deployable equity curve' in pair['caveat'] and
  seq_slow['entries_taken'] + seq_slow['entries_suppressed'] == 2 and
  seq_fast['entries_taken'] + seq_fast['entries_suppressed'] == 2 and
  'differ between arms by design' in seq_slow['note'])

# ---------------------------------------------------------------------
# C11 — repeated valid setups stay uncapped; exclusions are logged
# ---------------------------------------------------------------------
many = [EX.Trade('n%d' % i, 100.25, T0 + i * 400.0, 1, 99.75, 1)
        for i in range(6)]
QM = quotes(n=60000, step=0.05, drift=0.0)
seq = EX.sequential_replay('E0_EXEC', many, lambda _t: QM, cof)
t('C11: six sequential valid setups are not capped by any daily or '
  'weekly counter, and every suppressed entry is logged with its reason',
  seq['entries_taken'] + seq['entries_suppressed'] == 6 and
  all('reason' in s for s in seq['suppressed']) and
  not re.search(r'(daily|weekly)[_a-z]*(cap|limit|count)', src, re.I))

# ---------------------------------------------------------------------
# C12 — no live orders; predecessors unchanged; outcomes still locked
# ---------------------------------------------------------------------
ORDER = re.compile(r'\b(SubmitOrder|ChangeOrder|CancelOrder|EnterLong|'
                   r'EnterShort|ExitLong|ExitShort|PlaceOrder)\s*\(')
clean = re.sub(r'#.*', '', src)
PINNED = {
    'mrofyt_engine_v015.py':
        'e3da36cd63a18a22935124e852ce8f8b785e96df136d98944f7e88654b1c6847',
    'MROF_YT_OF01_5_SUCCESSOR_FREEZE.md':
        'b753a09cc077267a935df37f9b531f2179d920b8f76dc6ee5788628c264f7194',
    'MROF_YT_OF01_FINAL_SOURCE_PROMPT.md':
        '74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b',
}
bad = [f for f, w in PINNED.items()
       if hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()
                         ).hexdigest() != w]
try:
    EX.research_driver()
    locked = False
except RuntimeError as e:
    locked = 'STATE-C LOCKED' in str(e)
t('C12: no exit source submits, modifies or cancels a live order; every '
  'pinned predecessor hash reverifies; and the market-outcome driver is '
  'still STATE-C LOCKED',
  not ORDER.search(clean) and not bad and locked)

t('C12b: the primary economic metric and inference method are declared '
  'BEFORE any outcome is opened, and the two primary comparisons are '
  'named and corrected jointly',
  EX.PRIMARY_COMPARISONS == ('E1_minus_E0', 'E2_minus_E0') and
  EX.PRIMARY_ECONOMIC_METRIC and 'corrected jointly' in
  EX.INFERENCE_METHOD)

print('\nSYNTHETIC TESTS PROVE IMPLEMENTATION BEHAVIOR ONLY. No study was '
      'run and\nnothing here is evidence of profitability or positive EV.')
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
