#!/usr/bin/env python3
# MROF-YT-OF-01.6 suite. The nineteen mandatory deterministic and
# adversarial proofs of Appendix B section 10, plus predecessor hash
# reverification.
#
# SYNTHETIC TESTS PROVE IMPLEMENTATION BEHAVIOR ONLY. Nothing here is
# evidence of profitability, prediction accuracy or positive EV.
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mrofyt_engine_v015 as V15      # noqa: E402
import mrofyt_engine_v016 as V16      # noqa: E402
import mrofyt_swings_v016 as SW       # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-74s %s' % (name[:74], 'PASS' if cond else 'FAIL'))


# US Eastern, fixed to EDT for these deterministic fixtures
def TZ(_t):
    return -4 * 3600


def bar(tf, t_open, o, h, l, c, minutes=1, contract='NQ SEP26',
        session='20260902', run='R001', complete=True, v=10.0):
    return SW.Bar(tf, t_open, t_open + 60.0 * minutes, o, h, l, c, v,
                  'NQ', contract, session, run, complete)


# 2026-09-02 13:30:00Z == 09:30 ET
T0 = 1788269400.0


def series(highs, lows, tf='5m', minutes=5, **kw):
    out = []
    for i, (h, l) in enumerate(zip(highs, lows)):
        out.append(bar(tf, T0 + i * 60.0 * minutes, l, h, l, (h + l) / 2.0,
                       minutes, **kw))
    return out


# ---------------------------------------------------------------------
# 1. A center high cannot become available until the SECOND right bar
#    closes.
# ---------------------------------------------------------------------
b = series([10, 11, 15, 12, 11], [1, 2, 3, 2, 1])
sw = SW.detect_swings(b)
hi = [s for s in sw if s.side == 'SWING_HIGH']
four = SW.detect_swings(b[:4])
t('B1: a confirmed swing exists only once the second right-hand bar has '
  'closed, and its availability time IS that close',
  len(hi) == 1 and hi[0].available_t == b[4].t_close and
  hi[0].center_t == b[2].t_close and hi[0].price == 15 and
  not hi[0].available_at(b[4].t_close - 1e-6) and
  hi[0].available_at(b[4].t_close) and len(four) == 0)

# ---------------------------------------------------------------------
# 2. Reversing callback arrival order cannot alter any identity.
# ---------------------------------------------------------------------
def run_engine(order, toggle=V16.PARENT_PLUS_SWINGS):
    q = [(T0 + 0.2 + i * 0.05, 100.0, 5, 100.25, 5) for i in range(80)]
    e = V16.ResearchEngineV016('NQ', 'NQ SEP26', '20260902',
                               {'PP': 100.0}, {'PP': 'PIVOT'}, 1.0,
                               lambda _t: q, toggle=toggle,
                               swing_levels={'SWING_5M_HIGH|x|1|400': 100.0},
                               swing_family_of={
                                   'SWING_5M_HIGH|x|1|400': SW.SWING_FAMILY})
    e.on_price(T0 - 1.0, 100.0)
    for cb in order:
        e.on_raw_callback(T0, cb[0], 1, 100.0, cb[1], T0 - 1.0)
    e.complete_timestamp()
    return e


a = run_engine([('A1', 'cbA'), ('A2', 'cbB')])
bb = run_engine([('A2', 'cbB'), ('A1', 'cbA')])
ka = sorted(a.ledger())
kb = sorted(bb.ledger())
t('B2: reversing callback arrival order changes no swing ID, cluster ID, '
  'approach ID or adjudication',
  ka == kb and ka and
  [a.ledger()[k]['cluster'] for k in ka] ==
  [bb.ledger()[k]['cluster'] for k in kb] and
  [a.ledger()[k]['approach'] for k in ka] ==
  [bb.ledger()[k]['approach'] for k in kb] and
  [a.ledger()[k]['reason'] for k in ka] ==
  [bb.ledger()[k]['reason'] for k in kb])

# ---------------------------------------------------------------------
# 3. The asymmetric plateau rule creates ONE deterministic swing.
# ---------------------------------------------------------------------
pl = series([10, 15, 15, 15, 12, 11], [1, 2, 2, 2, 1, 1])
sp = [s for s in SW.detect_swings(pl) if s.side == 'SWING_HIGH']
t('B3: an equal-price plateau yields exactly one swing, assigned to the '
  'LAST plateau bar before price departs, never a duplicate per bar',
  len(sp) == 1 and sp[0].center_t == pl[3].t_close and
  len({s.swing_id for s in sp}) == 1)

# ---------------------------------------------------------------------
# 4. Partial / gapped / mixed bars cannot form a swing.
# ---------------------------------------------------------------------
inc = series([10, 11, 15, 12, 11], [1, 2, 3, 2, 1])
inc[2].complete = False
mix = series([10, 11, 15, 12, 11], [1, 2, 3, 2, 1])
mix[1].contract = 'NQ DEC26'
mses = series([10, 11, 15, 12, 11], [1, 2, 3, 2, 1])
mses[4].session = '20260903'
mrun = series([10, 11, 15, 12, 11], [1, 2, 3, 2, 1])
mrun[0].run = 'R002'
t('B4: an uncertain, mixed-contract, mixed-session or mixed-run five-bar '
  'window forms no swing at all',
  not SW.detect_swings(inc) and not SW.detect_swings(mix) and
  not SW.detect_swings(mses) and not SW.detect_swings(mrun))

# ---------------------------------------------------------------------
# 5. Aggregation is exchange-calendar aligned and never crosses a roll.
# ---------------------------------------------------------------------
ag = SW.BarAggregator(TZ, ('5m',))
made = []
for i in range(10):
    made += ag.add_1m(bar('1m', T0 + i * 60.0, 100, 101, 99, 100))
made += ag.flush()
aligned = all(abs((x.t_open + TZ(x.t_open)) % 300) < 1e-6 for x in made)

ag2 = SW.BarAggregator(TZ, ('5m',))
out2 = []
for i in range(5):
    c = 'NQ SEP26' if i < 3 else 'NQ DEC26'
    out2 += ag2.add_1m(bar('1m', T0 + i * 60.0, 100, 101, 99, 100,
                           contract=c))
out2 += ag2.flush()

ag3 = SW.BarAggregator(TZ, ('5m',))
out3 = []
for i in (0, 1, 3, 4):                    # minute 2 missing
    out3 += ag3.add_1m(bar('1m', T0 + i * 60.0, 100, 101, 99, 100))
out3 += ag3.flush()
t('B5: 1m->5m aggregation is exchange-calendar aligned; a contract roll '
  'or a missing minute inside a bucket voids the bucket entirely',
  len(made) == 2 and aligned and not out2 and not out3 and
  ag2.suppressed and ag3.suppressed)

# ---------------------------------------------------------------------
# 6. 1m swings remain diagnostic.
# ---------------------------------------------------------------------
one = series([10, 11, 15, 12, 11], [1, 2, 3, 2, 1], tf='1m', minutes=1)
s1 = SW.detect_swings(one)[0]
lc = SW.SwingLifecycle(atr20=2.0)
lc.add(s1)
t('B6: a 1m swing is confirmed and recorded but is never eligible, so it '
  'cannot create entry eligibility or affect grade or geometry',
  s1.eligible_tf is False and s1.eligible(1e12) is False and
  lc.eligible(1e12) == [] and lc.levels(1e12) == {} and
  '1m' in SW.DIAGNOSTIC_TF and '1m' not in SW.ACTIVE_TF)

# ---------------------------------------------------------------------
# 7. Confirmed 5m/15m/60m swings create eligibility only AFTER
#    availability.
# ---------------------------------------------------------------------
s5 = [s for s in SW.detect_swings(b) if s.side == 'SWING_HIGH'][0]
lc7 = SW.SwingLifecycle(atr20=2.0)
lc7.add(s5)
t('B7: an active-timeframe swing is ineligible before its availability '
  'timestamp and eligible after it',
  not s5.eligible(s5.available_t - 1e-6) and
  s5.eligible(s5.available_t) and
  lc7.levels(s5.available_t) == {s5.swing_id: s5.price})

# ---------------------------------------------------------------------
# 8. Coincident timeframes = ONE family vote, all level IDs retained.
# ---------------------------------------------------------------------
mk = lambda tf, px, at: SW.Swing(  # noqa: E731
    SW.swing_id(tf, 'SWING_HIGH', 'NQ SEP26', at, px), 'NQ', 'NQ SEP26',
    '20260902', tf, 'SWING_HIGH', at, px, at, [])
co = [mk('60m', 100.0, T0), mk('15m', 100.25, T0 + 1),
      mk('5m', 100.0, T0 + 2)]
cl = SW.cluster_swings(co, atr20=2.0)
one_cl = list(cl.values())[0]
t('B8: coincident 5m/15m/60m swings form one CAUSAL_SWING cluster with a '
  'single family vote while every timeframe level ID is retained',
  len(cl) == 1 and one_cl['family_votes'] == 1 and
  one_cl['family'] == SW.SWING_FAMILY and
  len(one_cl['members']) == 3 and
  sorted(one_cl['timeframes']) == ['15m', '5m', '60m'] and
  one_cl['anchor_swing_id'] == co[0].swing_id and
  all(s.family == SW.SWING_FAMILY for s in co))

# ---------------------------------------------------------------------
# 9. A later-confirmed overlapping swing cannot reset an approach in
#    progress.
# ---------------------------------------------------------------------
q9 = [(T0 + 0.2 + i * 0.05, 100.0, 5, 100.25, 5) for i in range(80)]
e9 = V16.ResearchEngineV016('NQ', 'NQ SEP26', '20260902', {'PP': 100.0},
                            {'PP': 'PIVOT'}, 1.0, lambda _t: q9,
                            toggle=V16.PARENT_PLUS_SWINGS,
                            swing_levels={'SWING_5M_HIGH|x|1|400': 100.0},
                            swing_family_of={
                                'SWING_5M_HIGH|x|1|400': SW.SWING_FAMILY})
e9.on_price(T0, 100.0)                     # approach begins, n == 1
n_before = e9.co._appr_state(round(100.0 / V16.TICK))['n']
e9.co.levels['SWING_15M_HIGH|x|9|400'] = 100.0     # later confirmation
e9.co.family_of['SWING_15M_HIGH|x|9|400'] = SW.SWING_FAMILY
e9.co.swing_levels['SWING_15M_HIGH|x|9|400'] = 100.0
e9.on_price(T0 + 1.0, 100.0)               # still inside the band
n_after = e9.co._appr_state(round(100.0 / V16.TICK))['n']
t('B9: adding a later-confirmed overlapping swing while price is still '
  'inside the band does not mint a new physical approach',
  n_before == 1 and n_after == 1)

# ---------------------------------------------------------------------
# 10. Two own-timeframe closes beyond -> ACCEPTED_BROKEN; a reclaim
#     before the second -> RECLAIMED_BEFORE_ACCEPTANCE.
# ---------------------------------------------------------------------
def lifecycle(closes):
    s = mk('5m', 100.0, T0)
    s.available_t = T0
    L = SW.SwingLifecycle(atr20=2.0)
    L.add(s)
    for i, c in enumerate(closes):
        L.on_tf_close(bar('5m', T0 + 300.0 * (i + 1), c, c, c, c, 5))
    return s


acc = lifecycle([101.0, 101.0])
rec = lifecycle([101.0, 99.0])
half = lifecycle([101.0])
other_tf = mk('5m', 100.0, T0)
other_tf.available_t = T0
L2 = SW.SwingLifecycle(atr20=2.0)
L2.add(other_tf)
for i in range(2):
    L2.on_tf_close(bar('15m', T0 + 900.0 * (i + 1), 101, 101, 101, 101, 15))
t('B10: two consecutive own-timeframe closes beyond give ACCEPTED_BROKEN; '
  'a reclaim before the second gives RECLAIMED_BEFORE_ACCEPTANCE; a '
  'different timeframe never advances acceptance',
  acc.state == SW.ACCEPTED_BROKEN and
  rec.state == SW.RECLAIMED_BEFORE and
  half.state == SW.BROKEN_PENDING and
  other_tf.state == SW.CONFIRMED_UNTOUCHED)

# ---------------------------------------------------------------------
# 11. An accepted-broken swing cannot flip polarity or trade again.
# ---------------------------------------------------------------------
L11 = SW.SwingLifecycle(atr20=2.0)
L11.add(acc)
side_before = acc.side
L11.on_price(T0 + 10000.0, 100.0, approach_id='ap9')
t('B11: an ACCEPTED_BROKEN swing keeps its side, is retired from the '
  'eligible pool, and a later touch generates no new eligibility',
  acc.state == SW.ACCEPTED_BROKEN and acc.side == side_before and
  not acc.eligible(T0 + 10000.0) and L11.eligible(T0 + 10000.0) == [] and
  SW.ACCEPTED_BROKEN in SW.RETIRED_STATES)

# ---------------------------------------------------------------------
# 12. A contract roll retires prior-contract active swings.
# ---------------------------------------------------------------------
sr = mk('5m', 100.0, T0)
sr.available_t = T0
L12 = SW.SwingLifecycle(atr20=2.0)
L12.add(sr)
n12 = L12.on_contract_roll(T0 + 500.0, 'NQ DEC26')
t('B12: a contract roll retires every prior-contract swing to ROLLED_OFF '
  'and keeps it in the ledger for audit',
  n12 == 1 and sr.state == SW.ROLLED_OFF and
  not sr.eligible(T0 + 600.0) and sr.swing_id in L12.swings)

# ---------------------------------------------------------------------
# 13. Duplicate callbacks and stale signals cannot duplicate episodes.
# ---------------------------------------------------------------------
e13 = run_engine([('A1', 'cbSAME'), ('A1', 'cbSAME')])
dup = [x for x in e13.co.log if x['reason'] == 'DUPLICATE_CALLBACK']
opened = [x for x in e13.co.log if x['reason'] == 'TRADE_OPENED']
q13 = [(T0 + 0.2 + i * 0.05, 100.0, 5, 100.25, 5) for i in range(80)]
e13b = V16.ResearchEngineV016('NQ', 'NQ SEP26', '20260902', {'PP': 100.0},
                              {'PP': 'PIVOT'}, 1.0, lambda _t: q13,
                              toggle=V16.PARENT_PLUS_SWINGS)
e13b.on_price(T0 - 1.0, 100.0)
e13b.on_raw_callback(T0, 'A1', 1, 100.0, 'stale', T0 + 5.0)   # future data
e13b.complete_timestamp()
stale = [x for x in e13b.co.log if 'CAUSALITY_FAILURE' in x['reason']
         or x['reason'] == 'CAUSALITY_FAILURE']
t('B13: a duplicate callback ID is logged and dropped, and a signal '
  'formed from data later than its completion time is a causality '
  'failure - neither creates a second episode',
  len(dup) == 1 and len(opened) == 1 and
  any(e13b.ledger()[k]['reason'] == 'CAUSALITY_FAILURE'
      for k in e13b.ledger()))

# ---------------------------------------------------------------------
# 14. Opposing exact-time signals conflict with ZERO filled quantity.
# ---------------------------------------------------------------------
q14 = [(T0 + 0.2 + i * 0.05, 100.0, 5, 100.25, 5) for i in range(80)]
e14 = V16.ResearchEngineV016('NQ', 'NQ SEP26', '20260902', {'PP': 100.0},
                             {'PP': 'PIVOT'}, 1.0, lambda _t: q14,
                             toggle=V16.PARENT_PLUS_SWINGS)
e14.on_price(T0 - 1.0, 100.0)
e14.on_raw_callback(T0, 'A1', 1, 100.0, 'up', T0 - 1.0)
e14.on_raw_callback(T0, 'A2', -1, 100.0, 'dn', T0 - 1.0)
e14.complete_timestamp()
led14 = e14.ledger()
t('B14: opposing signals at the same exact timestamp conflict before any '
  'fill, producing zero filled quantity, no position and no TRADE_OPENED',
  len(led14) == 2 and
  all(r['reason'] == 'SIMULTANEOUS_DIRECTION_CONFLICT'
      for r in led14.values()) and
  sum(r['filled'] for r in led14.values()) == 0.0 and
  e14.co.position is None and
  not [x for x in e14.co.log if x['reason'] == 'TRADE_OPENED'])

# ---------------------------------------------------------------------
# 15. Every occurrence receives a complete ledger record.
# ---------------------------------------------------------------------
REQ = {'id', 'family', 'direction', 'trigger_px', 'instrument', 'contract',
       'session', 'cluster', 'approach', 'approach_minted', 'level_ids',
       'level_families', 'state', 'reason', 'filled', 'cancelled',
       'entry_vwap', 'partial'}
recs = list(led14.values()) + list(e13.ledger().values())
# walk one episode through every frozen observation point
q15 = [(T0 + 0.2 + i * 0.05, 100.0, 5, 100.25, 5) for i in range(400)]
e15 = V16.ResearchEngineV016('NQ', 'NQ SEP26', '20260902', {'PP': 100.0},
                             {'PP': 'PIVOT'}, 1.0, lambda _t: q15,
                             toggle=V16.PARENT_PLUS_SWINGS)
e15.on_price(T0 - 1.0, 100.0)
e15.on_raw_callback(T0, 'A1', 1, 100.0, 'z1', T0 - 1.0)
r15 = e15.complete_timestamp()
e15.on_exit(r15['id'], T0 + 1.0, 100.5, early=True)
e15.co.observe('TERMINAL_EXIT', T0 + 2.0, 100.75, dict(episode=r15['id']))
pts = {o['point'] for o in e15.observations()}
t('B15: every suppression, conflict and trade record carries the complete '
  'field set, and level IDs/families are observed at each frozen point',
  all(REQ <= set(r) for r in recs) and recs and
  pts == set(V16.OBSERVE_POINTS) and
  all({'level_ids', 'level_families', 'toggle'} <= set(o)
      for o in e15.observations()))

# ---------------------------------------------------------------------
# 16. Four sequential re-armed setups produce four trades; no daily cap.
# ---------------------------------------------------------------------
q16 = [(T0 + i * 0.01, 100.0, 5, 100.25, 5) for i in range(20000)]
e16 = V16.ResearchEngineV016('NQ', 'NQ SEP26', '20260902', {'PP': 100.0},
                             {'PP': 'PIVOT'}, 1.0, lambda _t: q16,
                             toggle=V16.PARENT_PLUS_SWINGS)
trades = 0
for k in range(4):
    tt = T0 + k * 10.0
    e16.on_price(tt, 100.0)
    e16.on_raw_callback(tt, 'A1', 1, 100.0, 'cb%d' % k, tt - 0.5)
    r = e16.complete_timestamp()
    if r is not None:
        trades += 1
        e16.on_exit(r['id'], tt + 1.0, 100.5)
    e16.on_price(tt + 2.0, 110.0)          # retreat beyond the band
    e16.on_price(tt + 3.0, 100.0)          # independent re-approach
src16 = open(os.path.join(HERE, 'mrofyt_engine_v016.py')).read()
t('B16: four sequential, independently re-armed valid setups produce four '
  'trades and no daily or weekly trade counter exists in the engine',
  trades == 4 and
  not re.search(r'(daily|weekly)[_a-z]*(cap|limit|count)', src16, re.I))

# ---------------------------------------------------------------------
# 17. SWINGS_OFF_PARENT is bit-for-bit identical to v01.5.
# ---------------------------------------------------------------------
def fixture(engine):
    engine.on_price(T0 - 1.0, 100.0)
    engine.on_raw_callback(T0, 'A1', 1, 100.0, 'x1', T0 - 1.0)
    engine.on_raw_callback(T0, 'A2', 1, 100.0, 'x2', T0 - 1.0)
    engine.complete_timestamp()
    engine.on_price(T0 + 1.0, 110.0)
    engine.on_price(T0 + 2.0, 100.0)
    engine.on_raw_callback(T0 + 3.0, 'A4', -1, 100.0, 'x3', T0 + 2.0)
    engine.complete_timestamp()
    return engine


qf = [(T0 + 0.2 + i * 0.05, 100.0, 5, 100.25, 5) for i in range(400)]
args = ('NQ', 'NQ SEP26', '20260902', {'PP': 100.0, 'VWAP': 100.5},
        {'PP': 'PIVOT', 'VWAP': 'VWAP'}, 1.0)
p15 = fixture(V15.ResearchEngineV015(*args, quotes_fn=lambda _t: qf))
p16 = fixture(V16.ResearchEngineV016(
    *args, quotes_fn=lambda _t: qf, toggle=V16.SWINGS_OFF_PARENT,
    swing_levels={'SWING_5M_HIGH|x|1|400': 100.0}))
j15 = json.dumps(p15.ledger(), sort_keys=True, default=str)
j16 = json.dumps(p16.ledger(), sort_keys=True, default=str)
l15 = json.dumps(p15.co.log, sort_keys=True, default=str)
l16 = json.dumps(p16.co.log, sort_keys=True, default=str)
t('B17: SWINGS_OFF_PARENT is bit-for-bit identical to v01.5 on the same '
  'fixture - identical ledger bytes, identical log bytes, same code path',
  hashlib.sha256(j15.encode()).hexdigest() ==
  hashlib.sha256(j16.encode()).hexdigest() and
  hashlib.sha256(l15.encode()).hexdigest() ==
  hashlib.sha256(l16.encode()).hexdigest() and
  j15 == j16 and l15 == l16 and
  isinstance(p16.co, V15.CoordinatorV015) and
  type(p16.co) is V15.CoordinatorV015 and p16.parity is True and
  'MROF-YT-OF-01.5' in j16 and len(p15.ledger()) > 0)

# the other toggles must genuinely differ, or "identical" means nothing
only_sw = V16.ResearchEngineV016(
    'NQ', 'NQ SEP26', '20260902', {'PP': 100.0}, {'PP': 'PIVOT'}, 1.0,
    lambda _t: qf, toggle=V16.SWINGS_ONLY)
only_sw.on_price(T0 - 1.0, 100.0)
only_sw.on_raw_callback(T0, 'A1', 1, 100.0, 'y1', T0 - 1.0)
only_sw.complete_timestamp()
ov = V16.ResearchEngineV016(
    'NQ', 'NQ SEP26', '20260902', {'PP': 100.0}, {'PP': 'PIVOT'}, 1.0,
    lambda _t: qf, toggle=V16.PARENT_AND_SWING_OVERLAP,
    swing_levels={'SWING_5M_HIGH|x|1|400': 100.0})
ov.on_price(T0 - 1.0, 100.0)
ov.on_raw_callback(T0, 'A1', 1, 100.0, 'y2', T0 - 1.0)
ov.complete_timestamp()
ov_no = V16.ResearchEngineV016(
    'NQ', 'NQ SEP26', '20260902', {'PP': 100.0}, {'PP': 'PIVOT'}, 1.0,
    lambda _t: qf, toggle=V16.PARENT_AND_SWING_OVERLAP)
ov_no.on_price(T0 - 1.0, 100.0)
ov_no.on_raw_callback(T0, 'A1', 1, 100.0, 'y3', T0 - 1.0)
ov_no.complete_timestamp()
t('B17b: SWINGS_ONLY refuses a parent-only location, '
  'PARENT_AND_SWING_OVERLAP requires both families in one cluster, and '
  'each rejection is recorded before any fill',
  not only_sw.ledger() and
  any(d['reason'] == 'NO_ACTIVE_SWING' for d in only_sw.branch_drops()) and
  len(ov.ledger()) == 1 and not ov_no.ledger() and
  any(d['reason'] == 'NO_PARENT_SWING_OVERLAP'
      for d in ov_no.branch_drops()))

# ---------------------------------------------------------------------
# 18. No source submits, modifies or cancels a live order.
# ---------------------------------------------------------------------
ORDER = re.compile(r'\b(SubmitOrder|ChangeOrder|CancelOrder|EnterLong|'
                   r'EnterShort|ExitLong|ExitShort|PlaceOrder)\s*\(')
files18 = ['mrofyt_swings_v016.py', 'mrofyt_engine_v016.py',
           'tests_mrofyt_v01_6.py', 'mrofyt_engine_v015.py']
hits = []
for f in files18:
    src = open(os.path.join(HERE, f)).read()
    src = re.sub(r'#.*', '', src)
    if ORDER.search(src):
        hits.append(f)
t('B18: no v01.6 or inherited research source submits, modifies or '
  'cancels a live order (comments stripped before scanning)',
  not hits)

# ---------------------------------------------------------------------
# 19. Predecessors unmodified; pinned hashes reverified.
# ---------------------------------------------------------------------
PINNED = {
    'MROF_YT_OF01_FINAL_SOURCE_PROMPT.md':
        '74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b',
    'MROF_YT_OF01_5_SUCCESSOR_FREEZE.md':
        'b753a09cc077267a935df37f9b531f2179d920b8f76dc6ee5788628c264f7194',
    'mrofyt_engine_v015.py':
        'e3da36cd63a18a22935124e852ce8f8b785e96df136d98944f7e88654b1c6847',
}
bad = []
for f, want in PINNED.items():
    got = hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest()
    if got != want:
        bad.append((f, got, want))
t('B19: every pinned predecessor hash reverifies, so no predecessor file '
  'was modified by this successor',
  not bad)

t('B19b: swing levels are a location hypothesis only - the module makes '
  'no directional or EV claim and computes no fill, stop, target or P&L',
  not re.search(r'\b(positive_ev|expectancy|pnl|profit)\b',
                open(os.path.join(HERE, 'mrofyt_swings_v016.py')).read(),
                re.I))

print('\nSYNTHETIC TESTS PROVE IMPLEMENTATION BEHAVIOR ONLY. Nothing here '
      'is evidence\nof profitability, prediction accuracy or positive EV.')
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
