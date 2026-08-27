#!/usr/bin/env python3
# ======================================================================
# MGSD-V1  PHASE A  -  DATA + EXPOSURE AUDIT   (integrity facts only)
# Computes NO signal, NO candidate outcome, NO conditional statistic.
# ======================================================================
import os, sys, csv, glob, json, hashlib, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
import rvmr_run as RV

rep = {}

# ---------------------------------------------------------------- 1m grid
RV.STAMP_SHIFT = 0
D = RV.load_bars()
N = len(D['c'])
et, day, mod, em = D['et'], D['day'], D['mod'], D['em']
o, h, l, c, v = D['o'], D['h'], D['l'], D['c'], D['v']
days = sorted(set(day))
g = {'bars': N, 'first': et[0], 'last': et[-1], 'days': len(days),
     'dupes': N - len(set(et)),
     'missing_minutes': int(em[-1] - em[0] + 1 - N),
     'ohlc_violations': sum(1 for i in range(N)
                            if not (l[i] <= min(o[i], c[i]) and
                                    max(o[i], c[i]) <= h[i] and l[i] <= h[i])),
     'nonpos_price': sum(1 for i in range(N) if l[i] <= 0),
     'zero_vol_bars': sum(1 for i in range(N) if v[i] <= 0),
     'stamp': 'CLOSE-stamped ET (frozen RVMR-V1 audit, STAMP_SHIFT=0)',
     'tz': 'US/Eastern wall clock; DST implicit in ET stamps',
     'roll': 'V3 continuous MNQ series; stitching audited in RVMR-V1 Phase 0'}
g['days_by_year'] = dict(sorted(collections.Counter(d[:4] for d in days).items()))
g['complete_years'] = [y for y, n in g['days_by_year'].items() if n >= 240]

# session-stratum coverage (bars present per stratum per day, close stamps)
STRATA = [('S1_POSTCLOSE', 961, 1020), ('S2_GLOBEX_NIGHT', 1081, 1440 + 120),
          ('S3_EARLY_PM', 121, 480), ('S4_LATE_PM', 481, 569),
          ('S5_OPEN_DRIVE', 571, 600), ('S6_RTH_MORNING', 601, 690),
          ('S7_MIDDAY', 691, 840), ('S8_AFTERNOON', 841, 930),
          ('S9_CLOSE', 931, 960)]
def stratum_of(m):
    if 961 <= m <= 1020: return 'S1_POSTCLOSE'
    if m >= 1081 or m <= 120: return 'S2_GLOBEX_NIGHT'
    if 121 <= m <= 480: return 'S3_EARLY_PM'
    if 481 <= m <= 569: return 'S4_LATE_PM'
    if 571 <= m <= 600: return 'S5_OPEN_DRIVE'
    if 601 <= m <= 690: return 'S6_RTH_MORNING'
    if 691 <= m <= 840: return 'S7_MIDDAY'
    if 841 <= m <= 930: return 'S8_AFTERNOON'
    if 931 <= m <= 960: return 'S9_CLOSE'
    return None
cov = collections.defaultdict(lambda: collections.Counter())
for i in range(N):
    s = stratum_of(mod[i])
    if s:
        cov[day[i]][s] += 1
expected = {'S1_POSTCLOSE': 60, 'S2_GLOBEX_NIGHT': 480, 'S3_EARLY_PM': 360,
            'S4_LATE_PM': 89, 'S5_OPEN_DRIVE': 30, 'S6_RTH_MORNING': 90,
            'S7_MIDDAY': 150, 'S8_AFTERNOON': 90, 'S9_CLOSE': 30}
smat = []
for nm, e in expected.items():
    full = sum(1 for d in days if cov[d][nm] >= 0.95 * e)
    some = sum(1 for d in days if 0 < cov[d][nm] < 0.95 * e)
    none = sum(1 for d in days if cov[d][nm] == 0)
    smat.append({'stratum': nm, 'expected_bars': e, 'days_ge95pct': full,
                 'days_partial': some, 'days_absent': none})
g['stratum_coverage'] = smat

# aggregation determinism 1m -> 3m/15m/60m (close-stamp grouping (B-k, B])
def agg(step, sample=50000):
    grp = collections.defaultdict(list)
    for i in range(N):
        grp[(day[i], (mod[i] - 1) // step)].append(i)
    tot = ok = 0
    for k, idx in grp.items():
        if len(idx) != step:
            continue
        idx.sort(key=lambda i: em[i])
        if em[idx[-1]] - em[idx[0]] != step - 1:
            continue
        tot += 1
        hi, lo = max(h[i] for i in idx), min(l[i] for i in idx)
        if hi >= max(o[idx[0]], c[idx[-1]]) and lo <= min(o[idx[0]], c[idx[-1]]):
            ok += 1
        if tot >= sample:
            break
    return {'groups_tested': tot, 'consistent': ok}
g['agg_3m'] = agg(3); g['agg_15m'] = agg(15); g['agg_60m'] = agg(60)

files = sorted(glob.glob(os.path.join(RV.DATA, 'rvmr_1m_*.csv')))
g['source_files'] = [{'path': os.path.relpath(fn, ROOT),
                      'sha256': hashlib.sha256(open(fn, 'rb').read()).hexdigest()[:16],
                      'bytes': os.path.getsize(fn)} for fn in files]
rep['grid_1m'] = g

# ---------------------------------------------------------------- 30s arm
SCR = os.environ.get('MGSD_SCR',
    '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad')
ph2 = sorted(glob.glob(os.path.join(SCR, 'ph2', 'V3_30s_*.csv')))
bars30 = {}          # (date,timeEt) -> (o,h,l,c,v)  timeframe==30s only
bars1m_ph2 = {}      # 1m rows inside ph2 (for aggregation reconciliation)
per_month_30s = collections.Counter()
conflicts = 0
for fn in ph2:
    with open(fn, newline='') as fh:
        r = csv.reader(fh)
        hd = next(r)
        ix = {cn: k for k, cn in enumerate(hd)}
        for row in r:
            if len(row) != len(hd):
                continue
            tf = row[ix['timeframe']]
            key = (row[ix['date']], row[ix['timeEt']])
            try:
                vals = (float(row[ix['open']]), float(row[ix['high']]),
                        float(row[ix['low']]), float(row[ix['close']]),
                        float(row[ix['volume']]))
            except ValueError:
                continue
            if tf == '30s':
                if key in bars30 and bars30[key] != vals:
                    conflicts += 1
                bars30[key] = vals
                per_month_30s[key[0][:7]] += 1
            elif tf == '1m':
                bars1m_ph2[key] = vals
d30 = sorted(set(k[0] for k in bars30))
slots = collections.Counter()
for dte in d30:
    slots[sum(1 for k in bars30 if k[0] == dte)] += 1
tset = sorted(set(k[1] for k in bars30))
a = {'files': len(ph2),
     'file_hashes': [{'name': os.path.basename(fn),
                      'sha256': hashlib.sha256(open(fn, 'rb').read()).hexdigest()[:16]}
                     for fn in ph2],
     'unique_30s_bars': len(bars30), 'dup_conflicts': conflicts,
     'days_with_30s': len(d30),
     'coverage_months': sorted(set(dd[:7] for dd in d30)),
     'first_day': d30[0] if d30 else None, 'last_day': d30[-1] if d30 else None,
     'slot_grid': {'distinct_times': len(tset),
                   'first': tset[0] if tset else None,
                   'last': tset[-1] if tset else None},
     'days_by_slotcount': dict(sorted(slots.items())),
     'note': ('ph2 rows are EVENT exports with precomputed feature and '
              'outcome columns; ONLY raw OHLCV of timeframe==30s rows is '
              'admissible; all other columns are PROHIBITED (pre-exposed, '
              'non-causal provenance)')}

# 30s -> 1m aggregation reconciliation vs the canonical 1m grid
GI = {}
for i in range(N):
    GI[(day[i], '%02d:%02d:00' % (mod[i] // 60, mod[i] % 60))] = i
# both grids are CLOSE-stamped: canonical 1m bar stamped hh:mm:00 is the
# union of 30s bars stamped hh:mm-1:30 and hh:mm:00 (verified on raw rows)
match = tested = closemiss = volmatch = 0
for (dte, t), (o2, h2, l2, c2, v2) in list(bars30.items()):
    if not t.endswith(':00'):
        continue
    hh, mm = int(t[:2]), int(t[3:5])
    pm = (hh * 60 + mm - 1) % 1440
    k0 = (dte, '%02d:%02d:30' % (pm // 60, pm % 60))
    if k0 not in bars30:
        continue
    o1, h1, l1, c1, v1 = bars30[k0]
    gi = GI.get((dte, t))
    if gi is None:
        continue
    tested += 1
    if (abs(o[gi] - o1) < 1e-9 and abs(h[gi] - max(h1, h2)) < 1e-9
            and abs(l[gi] - min(l1, l2)) < 1e-9 and abs(c[gi] - c2) < 1e-9):
        match += 1
        if abs(v[gi] - (v1 + v2)) < 1e-6:
            volmatch += 1
    elif abs(c[gi] - c2) < 1e-9:
        closemiss += 1
a['agg_vs_canonical_1m'] = {'pairs_tested': tested, 'exact_ohlc': match,
                            'exact_ohlc_and_volume': volmatch,
                            'close_only_not_full': closemiss,
                            'stamp_rule': '1m[T] = 30s[T-30s] + 30s[T], all close-stamped'}
rep['arm_30s'] = a
rep['prohibited_datasets'] = [
    {'name': '5s/15s LTF capture (analysis/ltf_exec/data)',
     'reason': 'sub-30-second prohibited in MGSD-V1'},
    {'name': 'order-flow capture 2025-08..2026-08 (OFH lineage)',
     'reason': 'price-action first; order flow only as later incremental arm'},
    {'name': 'OFH13 133-trade table / outcome labels',
     'reason': 'prohibited discovery input (directive §1)'},
    {'name': 'ph2 non-OHLCV columns (features, MFE/MAE, barTo-R races)',
     'reason': 'pre-computed, pre-exposed, unknown causal provenance'}]
rep['dom_depth'] = 'NOT AVAILABLE anywhere'
rep['bid_ask_prints'] = 'NOT AVAILABLE on admissible grids'
rep['cross_market'] = ('NO synchronized genuine ES/YM/RTY/vol series exists in '
                       'the repository; cross-market arm = INSUFFICIENT DATA')

with open(os.path.join(HERE, 'MGSD_V1_DATA_MANIFEST.json'), 'w') as f:
    json.dump(rep, f, indent=1)
print(json.dumps({'grid_1m': {k: g[k] for k in
                              ('bars', 'first', 'last', 'days', 'dupes',
                               'missing_minutes', 'ohlc_violations',
                               'zero_vol_bars', 'complete_years',
                               'agg_3m', 'agg_15m', 'agg_60m',
                               'days_by_year')},
                  'arm_30s': {k: a[k] for k in
                              ('files', 'unique_30s_bars', 'days_with_30s',
                               'coverage_months', 'first_day', 'last_day',
                               'slot_grid', 'agg_vs_canonical_1m',
                               'dup_conflicts')}}, indent=1))
