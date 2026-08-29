#!/usr/bin/env python3
# MROF-V1 engine test battery (spec section 13). Synthetic events are
# deterministic software fixtures ONLY — never market evidence.
import csv
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mrof_engine as E  # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-62s %s' % (name, 'PASS' if cond else 'FAIL'))


def Q(tr, b, bs, a, asz, seq=1, flags=''):
    return dict(schema=E.SCHEMA, stream='quotes', seq=str(seq),
                tExch=str(tr), tRecv=str(tr), bidPx=str(b), bidSz=str(bs),
                askPx=str(a), askSz=str(asz), flags=flags, contract='NQ 09-26')


def T(tr, px, sz, inf, conf, seq=1):
    return dict(schema=E.SCHEMA, stream='trades', seq=str(seq),
                tExch=str(tr), tRecv=str(tr), px=str(px), sz=str(sz),
                aggrRaw='', aggrInf=inf, aggrConf=conf, contract='NQ 09-26')


# 1. trade-sign classification incl. ambiguous ------------------------
t('BUY/HIGH -> +1', E.trade_sign(T(0, 100, 1, 'BUY', 'HIGH')) == 1)
t('SELL/LOW -> -1', E.trade_sign(T(0, 100, 1, 'SELL', 'LOW')) == -1)
t('conf NONE (exact mid) -> 0 (never forced to a side)',
  E.trade_sign(T(0, 100, 1, 'BUY', 'NONE')) == 0)
t('empty classification -> 0', E.trade_sign(T(0, 100, 1, '', '')) == 0)
d = E.trade_delta([T(0, 100, 5, 'BUY', 'HIGH'), T(1, 100, 3, 'SELL', 'HIGH'),
                   T(2, 100, 2, '', 'NONE')])
t('TD=+2 classified=8 unknown_share=0.2 NTD=0.25',
  d['TD'] == 2 and d['classified_vol'] == 8 and
  abs(d['unknown_share'] - 0.2) < 1e-12 and abs(d['NTD'] - 0.25) < 1e-12)

# 2. OFI sign/size for every price-change case ------------------------
p = Q(0, 100.00, 5, 100.25, 7)
t('OFI bid up  (+Qb_new)      ', E.ofi_increment(p, Q(1, 100.25, 4, 100.50, 7)) == 4 + 7)
t('OFI bid down (-Qb_old)     ', E.ofi_increment(p, Q(1, 99.75, 9, 100.25, 7)) == -5 + (-7 + 7))
t('OFI bid same (+Qb_new-Qb_old)', E.ofi_increment(p, Q(1, 100.00, 8, 100.25, 7)) == 8 - 5 + (-7 + 7))
t('OFI ask down (-Qa_new)     ', E.ofi_increment(p, Q(1, 100.00, 5, 100.00, 6)) == (5 - 5) + (-6))
t('OFI ask up   (+Qa_old)     ', E.ofi_increment(p, Q(1, 100.00, 5, 100.50, 9)) == (5 - 5) + 7)
t('OFI ask same (Qa_old-Qa_new)', E.ofi_increment(p, Q(1, 100.00, 5, 100.25, 2)) == (5 - 5) + (-2 + 7))
t('OFI both up   = +Qb_new+Qa_old',
  E.ofi_increment(p, Q(1, 100.25, 4, 100.50, 9)) == 4 + 7)
t('OFI both down = -Qb_old-Qa_new',
  E.ofi_increment(p, Q(1, 99.75, 4, 100.00, 9)) == -5 - 9)
t('OFI unchanged book = 0',
  E.ofi_increment(p, Q(1, 100.00, 5, 100.25, 7)) == 0)

# 3. depth imbalance + zero depth -------------------------------------
t('DI K=2: (8-4)/12', abs(E.depth_imbalance([5, 3], [2, 2], 2) - 1 / 3) < 1e-12)
t('DI zero depth -> None', E.depth_imbalance([0], [0], 1) is None)

# 4. microprice + locked/crossed --------------------------------------
st = E.quote_state(Q(0, 100.00, 5, 100.25, 7))
t('microprice fixture (100.25*5+100*7)/12',
  abs(st['microprice'] - (100.25 * 5 + 100.0 * 7) / 12) < 1e-12)
t('spread in ticks = 1', st['spread_ticks'] == 1)
t('locked market flagged', E.quote_state(Q(0, 100, 5, 100, 5))['state'] == 'LOCKED')
t('crossed market flagged', E.quote_state(Q(0, 100.25, 5, 100, 5))['state'] == 'CROSSED')
t('zero size -> INVALID', E.quote_state(Q(0, 100, 0, 100.25, 5))['state'] == 'INVALID')

# 5. ordering, duplicates, sequence gaps ------------------------------
def write_csv(rows):
    f = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False,
                                    newline='',
                                    dir=os.environ.get('TMPDIR', '/tmp'))
    w = csv.DictWriter(f, fieldnames=sorted(set().union(*[r.keys() for r in rows])))
    w.writeheader()
    [w.writerow(r) for r in rows]
    f.close()
    return f.name


rows = [T(0, 100, 1, 'BUY', 'HIGH', seq=1), T(1, 100, 1, 'BUY', 'HIGH', seq=2),
        T(0.5, 100, 1, 'BUY', 'HIGH', seq=4), T(2, 100, 1, 'BUY', 'HIGH', seq=4)]
_, integ = E.parse_stream(write_csv(rows), 'trades')
t('seq gap detected (2->4)', integ['seq_gaps'] == 1)
t('seq duplicate detected (4,4)', integ['seq_dups'] == 1)
t('tRecv reversal detected', integ['trecv_reversals'] == 1)
t('raw rows preserved (nothing dropped)', integ['rows'] == 4)

# 6. session reset behavior -------------------------------------------
cd = E.cum_session_delta({'2026-09-01': [T(0, 100, 5, 'BUY', 'HIGH')],
                          '2026-09-02': [T(0, 100, 3, 'SELL', 'HIGH')]})
t('cumulative delta resets at session boundary',
  cd['2026-09-01'][-1] == 5 and cd['2026-09-02'][-1] == -3)

# 7. contract roll: silent mixing refused -----------------------------
r2 = T(3, 100, 1, 'BUY', 'HIGH', seq=5)
r2['contract'] = 'NQ 12-26'
try:
    E.parse_stream(write_csv(rows + [r2]), 'trades')
    mixed_ok = False
except ValueError:
    mixed_ok = True
t('mixed contracts in one file raise (no silent roll)', mixed_ok)

# 8. aggregation close stamps -----------------------------------------
trs = [T(5, 100, 1, 'BUY', 'HIGH'), T(35, 101, 2, 'SELL', 'HIGH'),
       T(65, 102, 1, 'BUY', 'HIGH')]
bb = E.bars(trs, [], 30)
t('30s bars close-stamped at bucket end (30, 60)',
  30 in bb and 60 in bb and bb[30]['c'] == 100 and bb[60]['c'] == 101)
t('incomplete tail bar (close 90) NOT emitted without proof',
  90 not in bb)
bb2 = E.bars(trs, [], 30, end_of_stream_proof=90)
t('tail bar emitted once completion is proven (session end >= 90)',
  90 in bb2 and bb2[90]['c'] == 102)

# 9. no incomplete higher-timeframe leakage ---------------------------
all_bars = {'30s': E.bars(trs, [], 30, end_of_stream_proof=90),
            '1m': E.bars(trs, [], 60, end_of_stream_proof=90)}
vis = E.features_at(all_bars, 61)
t('features_at(61) hides the 30s bar closing at 90',
  90 not in vis['30s'] and 60 in vis['30s'])
t('features_at(61) shows only the completed 1m bar (close 60)',
  list(vis['1m']) == [60])

# 10. parent-event declustering across timeframes ---------------------
par = E.decluster([(0, '1m', 'a'), (10, '3m', 'b'), (400, '1m', 'c')], 300)
t('nested multi-resolution burst = ONE parent',
  len(par) == 2 and len(par[0][1]) == 2 and len(par[1][1]) == 1)

# 11. signal-observation -> next-executable-fill ordering -------------
qs = [Q(10, 100.00, 5, 100.25, 5, seq=1),
      Q(12, 100.00, 5, 100.25, 5, seq=2),
      Q(13, 100.25, 5, 100.50, 5, seq=3)]
px, ft = E.next_executable_fill(qs, 10, +1, 2)
t('fill strictly after decision+latency (never the signal event)',
  ft == 13 and px == 100.50)
qs_bad = [Q(11, 100.25, 5, 100.00, 5, seq=1), Q(12, 100.00, 5, 100.25, 5, seq=2)]
px2, ft2 = E.next_executable_fill(qs_bad, 10, +1, 0)
t('crossed quote skipped; fill on first VALID quote', ft2 == 12)
px3, _ = E.next_executable_fill(qs, 10, -1, 2, slippage_ticks=1)
t('short fills at bid minus slippage', px3 == 100.25 - E.TICK)

# 12. cost application ------------------------------------------------
t('round-trip cost base 0.87 + 2 ticks slippage',
  abs(E.round_trip_cost(0.87, None, 2) - (0.87 + 0.5)) < 1e-12)

# 13. partial/missing capture -----------------------------------------
rows3 = [T(0, 100, 1, 'BUY', 'HIGH', seq=1), T(1, 100, 1, 'BUY', 'HIGH', seq=9)]
_, integ3 = E.parse_stream(write_csv(rows3), 'trades')
t('capture gap surfaces in integrity report (invalidates windows)',
  integ3['seq_gaps'] == 1)

# 14. raw-to-derived reproducibility ----------------------------------
h1 = E.digest(E.bars(trs, [], 30, end_of_stream_proof=90))
h2 = E.digest(E.bars(list(trs), [], 30, end_of_stream_proof=90))
t('identical raw input -> identical derived digest', h1 == h2)

# 15. partition/outcome guard -----------------------------------------
banned = ('pnl', 'net', 'mfe', 'mae', 'forward_return', 'label',
          'signal_rank', 'win', 'profit')
t('engine module exposes NO outcome computation',
  not any(hasattr(E, b) for b in banned))
t('State-C research is LOCKED (no authorization file)',
  E.research_unlocked() is False)
t('depletion primitive never labels cancel vs execution',
  'cancel' not in open(os.path.join(HERE, 'mrof_engine.py')).read()
  .split('def best_level_depletion')[1].split('def ')[0].lower()
  .replace('cancel from execution', '').replace('cancel_ok', ''))

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
